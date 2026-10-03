// damned_waters/engine/src/character_combat.cpp
// Purpose: the parts of a Character that combat touches. Where it can be hit (a capsule round
// each body region), where a shot really meets its skin, wounds that stay where they were made,
// limbs coming away (the piece that falls, the raw stump that stays on the body), and the
// survivor's guns: which one is in hand, where the muzzle is, how it kicks.
// The rules (how much it takes to cut an arm off) live in combat.hpp; this is the anatomy
// lesson: what a cut looks like on this particular body, posed as it is this frame.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

#include "cast_common.hpp"
#include "dw/character.hpp"
#include "grips.hpp"

namespace dw {
using cast::align_y;
namespace {
P3 p3(Vector3 v) { return {v.x, v.y, v.z}; }
Vector3 rotate_only(Vector3 v, const Matrix& m) { return {m.m0 * v.x + m.m4 * v.y + m.m8 * v.z, m.m1 * v.x + m.m5 * v.y + m.m9 * v.z,
                                                         m.m2 * v.x + m.m6 * v.y + m.m10 * v.z}; }
const Color RAW{110, 22, 20, 255}, CRUST{52, 10, 9, 255}, MARROW{168, 150, 118, 255};

// For the aim fitters. A joint's turn as this rig's angles (z, then x, then y); of the two sets
// that make the same turn, the one with less yaw and roll, which eases best from other poses.
Vector3 rig_angles(const Matrix& m) {
    const Vector3 a{std::asin(std::clamp(-m.m9, -1.0f, 1.0f)), std::atan2(m.m8, m.m10), std::atan2(m.m1, m.m5)};
    const Vector3 b{PI - a.x, a.y > 0 ? a.y - PI : a.y + PI, a.z > 0 ? a.z - PI : a.z + PI};
    return std::fabs(b.y) + std::fabs(b.z) < std::fabs(a.y) + std::fabs(a.z) ? b : a;
}
// A joint's own turn, from where it and its parent are: world = R T(off) parent.
Matrix own_turn(const Matrix& joint, const Matrix& parent, Vector3 off) {
    return MatrixMultiply(joint, MatrixInvert(MatrixMultiply(MatrixTranslate(off.x, off.y, off.z), parent)));
}
// How far a wrist is bent past what it does without strain: 30 degrees toward the little finger
// (-x on either hand: at rest the thumbs point forward), 15 toward the thumb; 50 toward the palm,
// `back` radians back (45 degrees; a long gun's grip cocks the wrist further, 60 back and 40
// toward the little finger) (+z bends
// the right hand back, the left toward its palm); and barely any twist, which is the forearm's job
// (this rig has none). Plus a little for any bend at all.
float wrist_strain(Vector3 w, bool right, float back = 0.79f, float ulnar = 0.52f) {
    const float flex = right ? -w.z : w.z;
    const float x = std::max(0.0f, std::max(-w.x - ulnar, w.x - 0.26f)), z = std::max(0.0f, std::max(flex - 0.87f, -flex - back));
    const float y = std::max(0.0f, std::fabs(w.y) - 0.2f);
    return 0.05f * (w.x * w.x + w.y * w.y + w.z * w.z) + 4.0f * (x * x + 2 * y * y + z * z);
}

// Where each region is cut from the body: the joint it hangs from (the stump rides its parent),
// and the joint its bone runs toward.
struct Cut { int at, parent, toward; };
Cut cut_of(int region) {
    switch (region) {
        case R_HEAD: return {J_HEAD, J_NECK, J_HEAD};
        case R_JAW: return {J_JAW, J_HEAD, J_JAW};
        case R_UARM_L: return {J_SHO_L, J_CHEST, J_ELB_L};
        case R_UARM_R: return {J_SHO_R, J_CHEST, J_ELB_R};
        case R_FARM_L: return {J_ELB_L, J_SHO_L, J_WRI_L};
        case R_FARM_R: return {J_ELB_R, J_SHO_R, J_WRI_R};
        case R_THIGH_L: return {J_HIP_L, J_PELVIS, J_KNE_L};
        case R_THIGH_R: return {J_HIP_R, J_PELVIS, J_KNE_R};
        case R_SHIN_L: return {J_KNE_L, J_HIP_L, J_ANK_L};
        case R_SHIN_R: return {J_KNE_R, J_HIP_R, J_ANK_R};
        default: return {J_PELVIS, J_PELVIS, J_PELVIS};
    }
}
int region_of_joint(int j) {
    if (const int h = hand_of(j)) return h == 1 ? R_FARM_L : R_FARM_R;   // a hand goes with its forearm
    switch (j) {
        case J_HEAD: return R_HEAD;
        case J_JAW: return R_JAW;
        case J_SHO_L: return R_UARM_L;
        case J_SHO_R: return R_UARM_R;
        case J_ELB_L: return R_FARM_L;
        case J_ELB_R: return R_FARM_R;
        case J_HIP_L: return R_THIGH_L;
        case J_HIP_R: return R_THIGH_R;
        case J_KNE_L: case J_ANK_L: return R_SHIN_L;
        case J_KNE_R: case J_ANK_R: return R_SHIN_R;
        default: return R_BODY;
    }
}
}  // namespace

Vector3 Character::skin_point(const Skinned& s, int v) const {
    const Mesh& m = s.mesh;
    const Vector3 p{m.vertices[v * 3], m.vertices[v * 3 + 1], m.vertices[v * 3 + 2]};
    Vector3 out{};
    for (int k = 0; k < 4; ++k) {
        const float w = m.boneWeights[v * 4 + k];
        if (w > 0) out = Vector3Add(out, Vector3Scale(Vector3Transform(p, bones_[m.boneIds[v * 4 + k]]), w));
    }
    return out;
}

Vector3 Character::skin_normal(const Skinned& s, int v) const {
    const Mesh& m = s.mesh;
    const Vector3 n{m.normals[v * 3], m.normals[v * 3 + 1], m.normals[v * 3 + 2]};
    Vector3 out{};
    for (int k = 0; k < 4; ++k) {
        const float w = m.boneWeights[v * 4 + k];
        if (w > 0) out = Vector3Add(out, Vector3Scale(rotate_only(n, bones_[m.boneIds[v * 4 + k]]), w));
    }
    return Vector3Normalize(out);
}

int Character::hit_volumes(int owner, HitVolume* out, int max) const {
    int n = 0;
    auto add = [&](int region, Vector3 a, Vector3 b, float r) {
        if (n < max && !severed(region)) out[n++] = {owner, region, p3(a), p3(b), r};
    };
    const float fat = kind == Kind::Drowned ? 1.15f : 1.0f;   // bloated: they fill more of the doorway
    add(R_BODY, joint(J_PELVIS), joint(J_CHEST), 0.165f * fat);
    add(R_BODY, joint(J_CHEST), joint(J_NECK), 0.12f * fat);
    add(R_HEAD, head_point(), head_point(), 0.098f * fat);
    add(R_JAW, joint(J_JAW), Vector3Transform(chin_, W_[J_JAW]), 0.042f);
    for (int s = 0; s < 2; ++s) {
        add(s ? R_UARM_R : R_UARM_L, joint(s ? J_SHO_R : J_SHO_L), joint(s ? J_ELB_R : J_ELB_L), 0.056f * fat);
        add(s ? R_FARM_R : R_FARM_L, joint(s ? J_ELB_R : J_ELB_L), joint(s ? J_MIDDLE1_R : J_MIDDLE1_L), 0.048f * fat);
        add(s ? R_THIGH_R : R_THIGH_L, joint(s ? J_HIP_R : J_HIP_L), joint(s ? J_KNE_R : J_KNE_L), 0.085f * fat);
        add(s ? R_SHIN_R : R_SHIN_L, joint(s ? J_KNE_R : J_KNE_L), joint(s ? J_ANK_R : J_ANK_L), 0.062f * fat);
    }
    return n;
}

bool Character::surface_hit(int region, Vector3 ro, Vector3 rd, Vector3& at, Vector3& n, int& jnt) const {
    // The nearest skinned vertex of that region within a finger's width of the ray: the skin (or the
    // cloth over it) is where the bullet goes in.
    constexpr float TOL2 = 0.016f * 0.016f;
    float best = 1e9f;
    const Skinned* bs = nullptr;
    int bv = -1;
    for (const auto& s : skinned_) {
        if (region >= int(s.by_region.size())) continue;
        for (int v : s.by_region[size_t(region)]) {
            const Vector3 d = Vector3Subtract(skin_point(s, v), ro);
            const float t = Vector3DotProduct(d, rd);
            if (t < 0 || t >= best) continue;
            if (Vector3LengthSqr(d) - t * t < TOL2) { best = t; bs = &s; bv = v; }
        }
    }
    if (!bs) return false;
    at = skin_point(*bs, bv);
    n = skin_normal(*bs, bv);
    if (Vector3DotProduct(n, rd) > 0) n = Vector3Negate(n);   // facing the shot
    jnt = bs->mesh.boneIds[bv * 4];
    return true;
}

void Character::add_wound(int j, Vector3 at, Vector3 n, float size) {
    if (wounds_ >= 48) return;   // enough is enough: the oldest stay, new ones stop
    ++wounds_;
    const Matrix inv = MatrixInvert(W_[j]);
    const Vector3 lp = Vector3Transform(at, inv);
    const Vector3 ln = Vector3Normalize(rotate_only(n, inv));
    const float spin = float(wounds_) * 2.39996f;
    MeshData d;
    MeshBuilder b(d);
    b.transform(MatrixMultiply(align_y(ln, spin), MatrixTranslate(lp.x - ln.x * size * 0.15f, lp.y - ln.y * size * 0.15f,
                                                                  lp.z - ln.z * size * 0.15f)));
    // A crater: black in the middle, raw at the lip, a crust round the edge; the middle sunk in.
    const Bump crater = [size](Vector3 dir) { return dir.y > 0 ? -size * 0.25f * std::max(0.0f, 1.0f - 2.2f * std::hypot(dir.x, dir.z)) : 0.0f; };
    const Painter paint = [](Vector3 dir) {
        const float r = std::hypot(dir.x, dir.z);
        return Paint{MAT_FLESH, r < 0.35f ? Color{16, 3, 3, 255} : r < 0.75f ? RAW : CRUST};
    };
    b.material(MAT_FLESH).ellipsoid({}, {size, size * 0.4f, size}, 10, 6, crater, paint);
    add_rigid(j, region_of_joint(j), d);
    if (wounds_ % 3 == 1) add_drip_source(j, lp, true, region_of_joint(j));   // some of them keep bleeding
}

void Character::sever(int root, MeshData& piece, Vector3& centre) {
    unsigned bits = 0;
    for (int r = 0; r < R_COUNT; ++r)
        if (region_within(r, root)) bits |= 1u << r;
    const unsigned fresh = bits & ~hidden_;
    piece = {};
    centre = {};
    if (!fresh) return;
    auto push = [&piece](Vector3 p, Vector3 n, const unsigned char* c, float mat, float ao, const float* tan) {
        piece.pos.insert(piece.pos.end(), {p.x, p.y, p.z});
        piece.nrm.insert(piece.nrm.end(), {n.x, n.y, n.z});
        piece.uv.insert(piece.uv.end(), {mat, ao});
        piece.tan.insert(piece.tan.end(), {tan[0], tan[1], tan[2], tan[3]});
        piece.col.insert(piece.col.end(), {c[0], c[1], c[2], c[3]});
    };
    // The piece: every skinned triangle whose corners all lie in the cut regions, posed as it is now.
    for (const auto& s : skinned_) {
        const Mesh& m = s.mesh;
        for (int t = 0; t < m.triangleCount; ++t) {
            const int v[3] = {m.indices[t * 3], m.indices[t * 3 + 1], m.indices[t * 3 + 2]};
            bool in = true;
            for (int k : v) in = in && ((fresh >> int(m.texcoords2[k * 2] + 0.5f)) & 1u);
            if (!in) continue;
            for (int k : v) push(skin_point(s, k), skin_normal(s, k), &m.colors[k * 4], m.texcoords[k * 2], m.texcoords[k * 2 + 1], &m.tangents[k * 4]);
        }
    }
    // Rigid parts riding those regions go with it (a mussel cluster, a wound, a staff pass).
    for (const auto& r : rigid_) {
        if (!((fresh >> r.region) & 1u)) continue;
        const Mesh& m = r.mesh;
        for (int k = 0; k < m.vertexCount; ++k)
            push(Vector3Transform({m.vertices[k * 3], m.vertices[k * 3 + 1], m.vertices[k * 3 + 2]}, W_[r.joint]),
                 rotate_only({m.normals[k * 3], m.normals[k * 3 + 1], m.normals[k * 3 + 2]}, W_[r.joint]), &m.colors[k * 4],
                 m.texcoords[k * 2], m.texcoords[k * 2 + 1], &m.tangents[k * 4]);
    }
    hidden_ |= bits;
    const Cut cut = cut_of(root);
    // The piece's torn end: meat and a splinter of bone, where it came away.
    {
        const Vector3 at = root == R_HEAD ? Vector3Lerp(joint(J_NECK), joint(J_HEAD), 0.9f) : joint(cut.at);
        MeshBuilder b(piece);
        b.material(MAT_FLESH).color(RAW).ellipsoid(at, {0.032f, 0.032f, 0.032f}, 8, 6);
    }
    if (!piece.pos.empty()) {
        Vector3 sum{};
        const size_t n = piece.pos.size() / 3;
        for (size_t i = 0; i < n; ++i) sum = Vector3Add(sum, {piece.pos[i * 3], piece.pos[i * 3 + 1], piece.pos[i * 3 + 2]});
        centre = Vector3Scale(sum, 1.0f / float(n));
        for (size_t i = 0; i < n; ++i) { piece.pos[i * 3] -= centre.x; piece.pos[i * 3 + 1] -= centre.y; piece.pos[i * 3 + 2] -= centre.z; }
    }
    // The stump on the body: raw meat round a stub of bone, on the joint the lost part hung from.
    // Offsets are in joint space, which is the rest pose's orientation.
    const Vector3 off = Vector3Subtract(rest_[cut.at], rest_[cut.parent]);
    Vector3 along = Vector3Subtract(rest_[cut.toward], rest_[cut.at]);
    if (root == R_HEAD) along = {0, 1, 0};
    if (root == R_JAW) along = Vector3Add(chin_, {0, 0, 0});
    along = Vector3LengthSqr(along) > 1e-8f ? Vector3Normalize(along) : Vector3{0, -1, 0};
    const Vector3 base = root == R_JAW ? Vector3Add(off, Vector3Scale(chin_, 0.45f)) : off;
    MeshData d;
    MeshBuilder b(d);
    const float r = root == R_HEAD ? 0.05f : root == R_JAW ? 0.035f : (root == R_THIGH_L || root == R_THIGH_R) ? 0.07f : 0.045f;
    b.transform(MatrixMultiply(align_y(along, 0.7f), MatrixTranslate(base.x, base.y, base.z)));
    b.material(MAT_FLESH).color(RAW).ellipsoid({0, 0.0f, 0}, {r, r * 0.55f, r}, 12, 8);
    b.color(CRUST).ellipsoid({0, -r * 0.2f, 0}, {r * 1.1f, r * 0.35f, r * 1.1f}, 12, 6);   // torn skin round it
    if (root != R_JAW) b.material(MAT_BONE).color(MARROW).tube({0, 0, 0}, {0, r * 0.9f, 0}, r * 0.26f, r * 0.2f, 8);
    add_rigid(cut.parent, region_of_joint(cut.parent), d);
    add_drip_source(cut.parent, Vector3Add(base, Vector3Scale(along, r * 0.5f)), true, region_of_joint(cut.parent));
}

void Character::recoil(float k) {   // added to the twitch offsets, which ease back by themselves
    twitch_[J_SHO_R].x += 0.3f * k;
    twitch_[J_SHO_L].x += 0.24f * k;
    twitch_[J_ELB_R].x += 0.18f * k;
    twitch_[J_CHEST].x += 0.07f * k;
    twitch_[J_HEAD].x += 0.05f * k;
}

void Character::set_weapon(int w) { weapon_ = w; }

// Guns are built in their own space, then held in the right hand as --fitgrips placed them.
Matrix Character::pistol_hold() { return grips::PISTOL_RIGHT.hold; }
Matrix Character::shotgun_hold() { return grips::SHOTGUN_RIGHT.hold; }
Matrix Character::gun_frame() const { return MatrixMultiply(weapon_ == 1 ? shotgun_hold() : pistol_hold(), W_[J_WRI_R]); }

Vector3 Character::muzzle() const {   // (cast_guns.cpp: the end of the 870's choke; the M92FS's muzzle)
    return Vector3Transform(weapon_ == 1 ? Vector3{0, -0.7387f, -0.0518f} : Vector3{0, -0.2401f, -0.066f}, gun_frame());
}

Vector3 Character::barrel_dir() const {
    return Vector3Normalize(rotate_only({0, -1, 0}, gun_frame()));
}

Vector3 Character::lamp() const { return has_lamp() ? Vector3Transform(lamp_off_, W_[lamp_joint_]) : joint(J_CHEST); }

Vector3 Character::lamp_dir() const {   // the head is bent forward, a little down: the floor ahead and whatever's on it
    return Vector3Normalize(rotate_only(Vector3Normalize({0, -0.18f, -1}), W_[has_lamp() ? lamp_joint_ : int(J_CHEST)]));
}

Vector3 Character::ejection_port() const {   // the pistol's port behind the muzzle; the shotgun's open breech
    return Vector3Transform(weapon_ == 1 ? Vector3{0.016f, -0.2477f, -0.0548f} : Vector3{0.012f, -0.137f, -0.066f}, gun_frame());
}

// The right eye, head space: the middle of the eyeball in his .dwc (in its rest pose the head's
// frame is the model's, moved to the joint).
Vector3 Character::right_eye() const {
    for (const Skinned& s : skinned_) {
        if (s.name != "eye_r" || s.mesh.vertexCount == 0) continue;
        Vector3 sum{};
        for (int v = 0; v < s.mesh.vertexCount; ++v)
            sum = Vector3Add(sum, {s.mesh.vertices[v * 3], s.mesh.vertices[v * 3 + 1], s.mesh.vertices[v * 3 + 2]});
        return Vector3Subtract(Vector3Scale(sum, 1.0f / float(s.mesh.vertexCount)), rest_[J_HEAD]);
    }
    return {0.0293f, 0.0405f, -0.0873f};
}

// ── A tool: fitting the shotgun hold ─────────────────────────────────────────────
std::string Character::fit_shotgun(const ShotgunFit& goal) {
    weapon_ = 1;
    Vector3 T[J_COUNT]{};
    float bob = 0;
    targets(goal.pose, 0, 0, 0, T, bob);
    bob_ = bob;
    pitch_ = pivot_ = lift_ = 0;
    pos_ = {};
    yaw_ = 0;
    for (auto& t : twitch_) t = {};
    const Vector3 aim = Vector3Normalize(goal.aim);
    const bool cheek = goal.cheek;
    // Points on the gun (cast_guns.cpp's rifle_at, before the hold): the middle of the butt pad, the
    // fore-end's belly toward its back (where a hand pumps it).
    const Vector3 butt{0, 0.2323f, 0.0512f}, belly = goal.left;
    // Where the right eye may be, in the gun's own measure (mm, as rifle_at: u along the gun from the
    // receiver's back face, v up from the bore, w to its right): over the bore, from just above the
    // receiver's top (17) to 4 cm over it, head up a little as police shooters are taught; 100-200 mm
    // behind the receiver, the nose a thumb's width or two behind the thumb on the stock's wrist.
    struct Band {
        float lo, hi;
        float off(float x) const { return x < lo ? lo - x : (x > hi ? x - hi : 0.0f); }
    };
    const Band eye_u{-200, -100}, eye_v{20, 60}, eye_w{-12, 12};
    auto gun_mm = [](Vector3 p) { return Vector3{(-0.0947f - p.y) * 1000, (-0.0518f - p.z) * 1000, p.x * 1000}; };   // u v w
    const Vector3 eye = right_eye();
    // The search: SHO_R xyz, ELB_R, WRI_R xyz, SHO_L xyz, ELB_L, WRI_L x z, NECK xyz, grip tilt,
    // HEAD xyz, SPINE y, CHEST x y.
    // - The wrist, in its joint's axes: x tips the hand sideways in the plane of the palm, 30 degrees
    //   at most; y twists it; z bends it toward the palm or its back, 75 degrees. The grip in the
    //   fist is fixed: fingers round the front of the stock's wrist, thumb over it.
    // - The neck and the head, within what a neck does without strain: 40 degrees forward, 25 to the
    //   side, the head nodding 20 back on top of it.
    // - SPINE y and CHEST y turn his back (+: the gun shoulder forward, squared up to the target;
    //   -: bladed, the gun side back); CHEST x leans him in.
    // Without `cheek`, the neck, the head and the lean stay as `goal.pose` has them; the turn is
    // still his to find.
    constexpr int K = 23;
    float lo[K] = {-0.6f, -1.6f, -1.6f, 0.0f, -0.85f, -2.4f, -1.3f, -0.3f, -1.2f, -1.4f, 0.0f, -1.2f, -1.2f,
                   -0.7f, -0.6f, -0.45f, 0.0f, -0.4f, -0.5f, -0.35f, -0.5f, -0.3f, -0.7f};
    float hi[K] = {2.6f, 1.6f, 2.4f, 2.6f, 0.55f, 2.4f, 1.3f, 2.8f, 1.2f, 1.4f, 2.4f, 1.2f, 1.2f,
                   0.3f, 0.6f, 0.45f, 0.0f, 0.35f, 0.5f, 0.35f, 0.5f, 0.05f, 0.5f};
    const int head_k[6] = {13, 14, 15, 17, 18, 19};   // NECK xyz, HEAD xyz
    const float body[6] = {T[J_NECK].x, T[J_NECK].y, T[J_NECK].z, T[J_HEAD].x, T[J_HEAD].y, T[J_HEAD].z};
    if (!cheek) {
        for (int i = 0; i < 6; ++i) lo[head_k[i]] = hi[head_k[i]] = body[i];
        lo[21] = hi[21] = T[J_CHEST].x;
    }
    // The left hand: round the fore-end by hands() when this pose holds the gun in both hands
    // (aiming, carrying it at the low ready), and then the search only picks which way its elbow
    // points (the left shoulder: where the IK starts the arm), so its wrist bends no further than it
    // must; loading, the search takes it to `goal.left` (a shell at the port).
    support_ = goal.pose == Pose::Reload ? nullptr : want_support_;   // (in the game, a reload's steps move the hand from there)
    support_w_ = support_ ? 1.0f : 0.0f;
    reloading.on = false;
    close_w_ = 0;
    pump = 0;
    float gaps[3]{};   // how far off the butt, the left hand and the eye end up (m)
    Vector3 eye_g{};   // the eye in the gun's measure: u v w (mm)
    float look = 0, roll = 0;   // the face: how far it turns from the aim, and how far it tips over
    float parts[8]{};
    auto eval = [&](const float* q) {
        for (int j = 0; j < J_COUNT; ++j) ang_[j] = T[j];
        ang_[J_SHO_R] = {q[0], q[1], q[2]};
        ang_[J_ELB_R] = {q[3], 0, 0};
        ang_[J_WRI_R] = {q[4], q[5], q[6]};   // the hand bends with the gun in it
        ang_[J_SHO_L] = {q[7], q[8], q[9]};
        ang_[J_ELB_L] = {q[10], 0, 0};
        ang_[J_WRI_L] = {q[11], 0, q[12]};
        ang_[J_NECK] = {q[13], q[14], q[15]};
        ang_[J_HEAD] = {q[17], q[18], q[19]};
        ang_[J_SPINE].y = q[20];
        ang_[J_CHEST] = {q[21], q[22], T[J_CHEST].z};
        fk();
        hands(0);
        const Matrix G = MatrixMultiply(shotgun_hold(), W_[J_WRI_R]);
        const Vector3 bore = Vector3Normalize(rotate_only({0, -1, 0}, G));
        // The pocket rides the chest: it's the hollow inside the shoulder, wherever he's turned.
        const Vector3 pocket = Vector3Add(joint(J_SHO_R), rotate_only(goal.pocket, W_[J_CHEST]));
        eye_g = gun_mm(Vector3Transform(Vector3Transform(eye, W_[J_HEAD]), MatrixInvert(G)));
        gaps[0] = Vector3Distance(Vector3Transform(butt, G), pocket);
        if (support_) {   // the left hand short of its grip (the arm can't reach)
            const Matrix want = MatrixMultiply(MatrixInvert(support_->hold), G);
            gaps[1] = Vector3Distance(joint(J_WRI_L), {want.m12, want.m13, want.m14});
        } else {
            const Vector3 palm = Vector3Lerp(joint(J_WRI_L), joint(J_MIDDLE1_L), 0.5f);
            gaps[1] = Vector3Distance(palm, Vector3Add(Vector3Transform(belly, G), {0, -0.025f, 0}));
        }
        gaps[2] = 0.001f * Vector3Length({eye_u.off(eye_g.x), eye_v.off(eye_g.y), eye_w.off(eye_g.z)});
        parts[0] = 600.0f * (1.0f - Vector3DotProduct(bore, aim));
        parts[1] = 4000.0f * gaps[0] * gaps[0];
        parts[2] = (support_ ? 4000.0f : 1000.0f) * gaps[1] * gaps[1];
        parts[3] = cheek ? 3000.0f * gaps[2] * gaps[2] : 0.0f;
        // The elbows down, the modern way: the right one dropped under the stock rather than winged
        // out to make a pocket, the left one under the fore-end.
        parts[4] = elbow_not_down(joint(J_SHO_R), joint(J_ELB_R), joint(J_WRI_R));
        if (support_) parts[4] += elbow_not_down(joint(J_SHO_L), joint(J_ELB_L), joint(J_WRI_L));
        // The wrists bent no further than they must (the left one as the IK turned it, or as searched).
        // (The right wrist may twist: on a shotgun's stock the forearm turns the palm onto it, and this
        // rig, without a forearm twist, lets the wrist do it; the skin shares it along the forearm.)
        const Vector3 rw{q[4], 0.25f * q[5], q[6]};
        parts[5] = wrist_strain(rw, true, 1.05f, 0.7f) + (support_ ? wrist_strain(ik_wrist_[0], false) : 0.0f);
        // The neck, the head and the back turned no further than they must: a shooter's head comes
        // down to the stock, but a strained one looks wrong.
        float strain = 0;
        for (int k : head_k) strain += q[k] * q[k];
        parts[6] = (cheek ? 0.2f * strain : 0.0f) + 0.1f * (q[20] * q[20] + q[21] * q[21] + q[22] * q[22]);
        // He looks down the barrel, so his face points along it, give or take the 25 degrees his
        // eyes can roll up under his brows; and the head tips toward the stock, but not over.
        const Matrix& H = W_[J_HEAD];
        look = std::acos(std::clamp(Vector3DotProduct(Vector3Normalize({-H.m8, -H.m9, -H.m10}), aim), -1.0f, 1.0f));
        roll = std::asin(std::clamp(Vector3Normalize({H.m0, H.m1, H.m2}).y, -1.0f, 1.0f));
        const float over_look = std::max(0.0f, look - 0.44f), over_roll = std::max(0.0f, std::fabs(roll) - 0.44f);
        parts[7] = cheek ? 300.0f * (over_look * over_look + over_roll * over_roll) : 0.0f;
        return parts[0] + parts[1] + parts[2] + parts[3] + parts[4] + parts[5] + parts[6] + parts[7];
    };
    unsigned rng = 0x2545F491u;
    auto rnd = [&rng]() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return float(rng & 0xFFFFFF) / 16777215.0f; };
    // The first start is fixed (never the pose tables, which hold the last fit), so the tool gives
    // the same answer every time it's run.
    float start[K] = {0.5f, 0.25f, 0.0f, 1.2f, 0.0f, 0.0f, 0.0f, 1.1f, 0.0f, 0.45f, 0.5f, 0.0f, 0.0f,
                      -0.45f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
    for (int k = 0; k < K; ++k) start[k] = std::clamp(start[k], lo[k], hi[k]);
    float bestq[K];
    std::copy(start, start + K, bestq);
    float best = eval(bestq);
    const int iters = cheek ? 60000 : 40000;
    // A second fixed start: the right elbow raised out to the side, the way a shotgun is shouldered
    // (it lifts the shoulder into a pocket for the butt).
    float elbow_out[K];
    std::copy(start, start + K, elbow_out);
    elbow_out[0] = 0.5f; elbow_out[1] = 0.5f; elbow_out[2] = 1.1f; elbow_out[3] = 1.6f;
    for (int restart = 0; restart < 14; ++restart) {   // several starts: the arms have more than one way to hold a gun
        float q[K];
        for (int k = 0; k < K; ++k)
            q[k] = restart == 0 ? start[k] : restart == 1 ? std::clamp(elbow_out[k], lo[k], hi[k]) : lo[k] + (hi[k] - lo[k]) * rnd();
        float cur = eval(q), step = 0.8f;
        for (int it = 0; it < iters; ++it) {
            float t[K];
            std::copy(q, q + K, t);
            const int n = 1 + int(rnd() * 2.99f);
            for (int m = 0; m < n; ++m) {
                const int k = std::min(K - 1, int(rnd() * float(K)));
                t[k] = std::clamp(t[k] + (rnd() * 2 - 1) * step, lo[k], hi[k]);
            }
            const float c = eval(t);
            if (c < cur) { cur = c; std::copy(t, t + K, q); }
            if (it % (iters / 10) == iters / 10 - 1) step *= 0.65f;
        }
        if (cur < best) { best = cur; std::copy(q, q + K, bestq); }
    }
    eval(bestq);
    const float* q = bestq;
    // The left arm for the pose table: as the IK left it (so it eases in from close by), or as searched.
    Vector3 sho_l{q[7], q[8], q[9]}, wri_l{q[11], 0, q[12]};
    float elb_l = q[10];
    if (support_) {
        sho_l = rig_angles(own_turn(W_[J_SHO_L], W_[J_CHEST], off_[J_SHO_L]));
        elb_l = rig_angles(own_turn(W_[J_ELB_L], W_[J_SHO_L], off_[J_ELB_L])).x;
        wri_l = ik_wrist_[0];
    }
    char buf[1200];
    std::snprintf(buf, sizeof(buf),
                  "cost %.4f (bore %.4f butt %.4f hand %.4f eye %.4f elbow %.4f wrist %.4f strain %.4f face %.4f)\n"
                  "  gaps: butt %.1f cm, left hand %.1f cm, eye %.1f cm (u %.0f v %.0f w %.0f mm); face %.0f deg off the aim,"
                  " tipped %.0f deg\n"
                  "  SHO_R {%.3f, %.3f, %.3f} ELB_R %.3f WRI_R {%.3f, %.3f, %.3f}\n"
                  "  SHO_L {%.3f, %.3f, %.3f} ELB_L %.3f WRI_L {%.3f, %.3f, %.3f}%s\n"
                  "  NECK {%.3f, %.3f, %.3f} HEAD {%.3f, %.3f, %.3f} SPINE.y %.3f CHEST {%.3f, %.3f}",
                  best, parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7],   //
                  gaps[0] * 100, gaps[1] * 100, gaps[2] * 100, eye_g.x, eye_g.y, eye_g.z, look * RAD2DEG, roll * RAD2DEG,
                  q[0], q[1], q[2], q[3], q[4], q[5], q[6],                                             // the right arm
                  sho_l.x, sho_l.y, sho_l.z, elb_l, wri_l.x, wri_l.y, wri_l.z, support_ ? " (as the IK left it)" : "",
                  q[13], q[14], q[15], q[17], q[18], q[19], q[20], q[21], q[22]);                       // the head and back
    return buf;
}

// ── A tool: fitting the two-handed pistol aim ────────────────────────────────────
// The isosceles stance, thumbs forward: both arms out, the strong one straight but not locked; the
// gun up in front of the eye rather than the head down to the gun; the head upright, looking along
// the sights. The search moves the right arm, its wrist, the neck and the head; the left hand goes
// on by hands(), and the search only picks which way its elbow points (the left shoulder's
// angles: the pose the IK starts from), so its wrist bends no further than it must.
std::string Character::fit_pistol(Vector3 aim_dir) {
    weapon_ = 0;
    Vector3 T[J_COUNT]{};
    float bob = 0;
    targets(Pose::Aim, 0, 0, 0, T, bob);
    bob_ = bob;
    pitch_ = pivot_ = lift_ = 0;
    pos_ = {};
    yaw_ = 0;
    for (auto& t : twitch_) t = {};
    support_ = want_support_;
    support_w_ = 1;
    reloading.on = false;
    close_w_ = 0;
    const Vector3 aim = Vector3Normalize(aim_dir), eye = right_eye();
    struct Band {
        float lo, hi;
        float off(float x) const { return x < lo ? lo - x : (x > hi ? x - hi : 0.0f); }
    };
    // The right eye on the sight line (the front sight's top and the rear sight's ears, 17-19 mm
    // over the bore), 28-44 cm behind the rear sight: the modern isosceles, the arms out but well
    // bent, nobody's locked straight.
    const Band eye_u{-440, -280}, eye_v{15.5f, 20.5f}, eye_w{-2.5f, 2.5f};
    auto gun_mm = [](Vector3 p) { return Vector3{(-0.0315f - p.y) * 1000, (-0.066f - p.z) * 1000, p.x * 1000}; };   // u v w
    // SHO_R xyz, ELB_R, WRI_R xyz, NECK xyz, HEAD xyz, then SHO_L xyz: where the IK starts the left
    // arm (only which way its elbow points matters), held near the elbow-down pose it was drawn in.
    // The wrists: x tips the hand in the plane of the palm (ulnar or radial), y twists it (which a
    // wrist barely does: the forearm turns the hand, and this rig has no forearm twist), z bends it
    // toward the palm or its back.
    // Then SPINE y and CHEST x y: his shoulders squared to the target (the isosceles stance), the
    // chest leaning in over the hips the way it's taught (the recoil goes into the body).
    constexpr int K = 19;
    const float lo[K] = {1.0f, -0.9f, -0.9f, 0.0f, -0.8f, -0.5f, -0.9f, -0.45f, -0.35f, -0.3f, -0.3f, -0.35f, -0.3f, 0.6f, -1.2f, -0.6f,
                         -0.3f, -0.25f, -0.3f};
    const float hi[K] = {2.1f, 0.9f, 0.9f, 1.0f, 0.3f, 0.5f, 0.9f, 0.2f, 0.35f, 0.3f, 0.3f, 0.35f, 0.3f, 2.4f, 1.2f, 1.4f,
                         0.3f, 0.05f, 0.3f};
    float parts[7]{}, eye_gap = 0, reach = 0, look = 0, roll = 0;
    Vector3 eye_g{};
    auto eval = [&](const float* q) {
        for (int j = 0; j < J_COUNT; ++j) ang_[j] = T[j];
        ang_[J_SHO_R] = {q[0], q[1], q[2]};
        ang_[J_ELB_R] = {q[3], 0, 0};
        ang_[J_WRI_R] = {q[4], q[5], q[6]};
        ang_[J_NECK] = {q[7], q[8], q[9]};
        ang_[J_HEAD] = {q[10], q[11], q[12]};
        ang_[J_SHO_L] = {q[13], q[14], q[15]};
        ang_[J_ELB_L] = {0.4f, 0, 0};
        ang_[J_SPINE].y = q[16];
        ang_[J_CHEST] = {q[17], q[18], T[J_CHEST].z};
        fk();
        hands(0);
        const Matrix G = gun_frame();
        const Vector3 bore = Vector3Normalize(rotate_only({0, -1, 0}, G));
        eye_g = gun_mm(Vector3Transform(Vector3Transform(eye, W_[J_HEAD]), MatrixInvert(G)));
        eye_gap = 0.001f * Vector3Length({eye_u.off(eye_g.x), eye_v.off(eye_g.y), eye_w.off(eye_g.z)});
        const Matrix want = MatrixMultiply(MatrixInvert(grips::PISTOL_LEFT.hold), G);
        reach = Vector3Distance(joint(J_WRI_L), {want.m12, want.m13, want.m14});   // the left hand short of the grip
        parts[0] = 600.0f * (1.0f - Vector3DotProduct(bore, aim));
        parts[1] = 4000.0f * eye_gap * eye_gap;
        parts[2] = 4000.0f * reach * reach;
        // Both wrists bent no further than they must (x tips the hand in the plane of the palm, y
        // twists it, z bends it toward the palm or its back); the strong elbow a touch bent.
        const Vector3 lw = ik_wrist_[0];
        parts[3] = wrist_strain({q[4], q[5], q[6]}, true) + wrist_strain(lw, false);
        float strain = 0;
        for (int k = 7; k < 13; ++k) strain += q[k] * q[k];
        parts[4] = 0.2f * strain + 0.1f * (q[16] * q[16] + q[17] * q[17] + q[18] * q[18]);
        // He looks along the sights: his face points down them, give or take the 12 degrees his eyes
        // turn without effort, and the head stays level.
        const Matrix& H = W_[J_HEAD];
        look = std::acos(std::clamp(Vector3DotProduct(Vector3Normalize({-H.m8, -H.m9, -H.m10}), aim), -1.0f, 1.0f));
        roll = std::asin(std::clamp(Vector3Normalize({H.m0, H.m1, H.m2}).y, -1.0f, 1.0f));
        const float over_look = std::max(0.0f, look - 0.2f), over_roll = std::max(0.0f, std::fabs(roll) - 0.12f);
        parts[5] = 300.0f * (over_look * over_look + over_roll * over_roll);
        // Both arms bent about 40 degrees, never locked, the elbows hanging down under the gun.
        parts[6] = 0;
        for (int side = 0; side < 2; ++side) {
            const Vector3 sh = joint(side ? J_SHO_R : J_SHO_L), el = joint(side ? J_ELB_R : J_ELB_L), wr = joint(side ? J_WRI_R : J_WRI_L);
            const float bend = elbow_bend(sh, el, wr) - 0.7f;
            parts[6] += elbow_not_down(sh, el, wr) + 8.0f * bend * bend;
        }
        return parts[0] + parts[1] + parts[2] + parts[3] + parts[4] + parts[5] + parts[6];
    };
    unsigned rng = 0x51ED270Bu;
    auto rnd = [&rng]() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return float(rng & 0xFFFFFF) / 16777215.0f; };
    const float start[K] = {1.57f, 0, 0.08f, 0.05f, 0, 0, 0, -0.1f, 0, 0, 0, 0, 0, 1.45f, 0, 0.6f, 0, -0.03f, 0};   // fixed: the same answer every run
    float bestq[K];
    std::copy(start, start + K, bestq);
    float best = eval(bestq);
    const int iters = 40000;
    for (int restart = 0; restart < 10; ++restart) {
        float q[K];
        for (int k = 0; k < K; ++k) q[k] = restart == 0 ? start[k] : lo[k] + (hi[k] - lo[k]) * rnd();
        float cur = eval(q), step = 0.8f;
        for (int it = 0; it < iters; ++it) {
            float t[K];
            std::copy(q, q + K, t);
            const int n = 1 + int(rnd() * 2.99f);
            for (int m = 0; m < n; ++m) {
                const int k = std::min(K - 1, int(rnd() * float(K)));
                t[k] = std::clamp(t[k] + (rnd() * 2 - 1) * step, lo[k], hi[k]);
            }
            const float c = eval(t);
            if (c < cur) { cur = c; std::copy(t, t + K, q); }
            if (it % (iters / 10) == iters / 10 - 1) step *= 0.65f;
        }
        if (cur < best) { best = cur; std::copy(q, q + K, bestq); }
    }
    eval(bestq);
    const float* q = bestq;
    // The left arm as the IK left it, for the pose table (so it eases in from close by).
    const Vector3 sho_l = rig_angles(own_turn(W_[J_SHO_L], W_[J_CHEST], off_[J_SHO_L]));
    const float elb_l = rig_angles(own_turn(W_[J_ELB_L], W_[J_SHO_L], off_[J_ELB_L])).x;
    if (std::getenv("DW_FIT_TRACE")) {   // where things are (cm, his frame: x his left, y up, z behind him)
        const Matrix w = MatrixMultiply(MatrixInvert(grips::PISTOL_LEFT.hold), gun_frame());
        const Vector3 pts[] = {joint(J_SHO_L), joint(J_SHO_R), Vector3Transform(eye, W_[J_HEAD]), {w.m12, w.m13, w.m14}, joint(J_WRI_R),
                               joint(J_ELB_L), joint(J_ELB_R), joint(J_CHEST), joint(J_NECK)};
        const char* nm[] = {"left shoulder", "right shoulder", "right eye", "left grip wrist", "right wrist", "left elbow", "right elbow", "chest", "neck"};
        for (int i = 0; i < 9; ++i) TraceLog(LOG_INFO, "  %-16s %6.1f %6.1f %6.1f", nm[i], pts[i].x * 100, pts[i].y * 100, pts[i].z * 100);
    }
    char buf[1200];
    std::snprintf(buf, sizeof(buf),
                  "cost %.4f (bore %.4f eye %.4f reach %.4f wrists %.4f strain %.4f face %.4f elbow %.4f)\n"
                  "  eye %.1f cm off the sight line (u %.0f v %.1f w %.1f mm); face %.0f deg off the aim, tipped %.0f deg;"
                  " left hand %.1f mm short\n"
                  "  SHO_R {%.3f, %.3f, %.3f} ELB_R %.3f WRI_R {%.3f, %.3f, %.3f}\n"
                  "  SHO_L {%.3f, %.3f, %.3f} ELB_L %.3f WRI_L {%.3f, %.3f, %.3f} (as the IK left it)\n"
                  "  NECK {%.3f, %.3f, %.3f} HEAD {%.3f, %.3f, %.3f} SPINE.y %.3f CHEST {%.3f, %.3f}\n"
                  "  (left arm %.0f + %.0f mm; shoulder to the grip's wrist %.0f mm)",
                  best, parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6],   //
                  eye_gap * 100, eye_g.x, eye_g.y, eye_g.z, look * RAD2DEG, roll * RAD2DEG, reach * 1000,   //
                  q[0], q[1], q[2], q[3], q[4], q[5], q[6],                                                    //
                  sho_l.x, sho_l.y, sho_l.z, elb_l, ik_wrist_[0].x, ik_wrist_[0].y, ik_wrist_[0].z,       //
                  q[7], q[8], q[9], q[10], q[11], q[12], q[16], q[17], q[18],   //
                  Vector3Length(off_[J_ELB_L]) * 1000, Vector3Length(off_[J_WRI_L]) * 1000,
                  Vector3Distance(joint(J_SHO_L), [&] {
                      const Matrix w = MatrixMultiply(MatrixInvert(grips::PISTOL_LEFT.hold), gun_frame());
                      return Vector3{w.m12, w.m13, w.m14};
                  }()) * 1000);
    return buf;
}

}  // namespace dw
