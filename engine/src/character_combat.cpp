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
#include <string>

#include "cast_common.hpp"
#include "dw/character.hpp"

namespace dw {
using cast::align_y;
namespace {
P3 p3(Vector3 v) { return {v.x, v.y, v.z}; }
Vector3 rotate_only(Vector3 v, const Matrix& m) { return {m.m0 * v.x + m.m4 * v.y + m.m8 * v.z, m.m1 * v.x + m.m5 * v.y + m.m9 * v.z,
                                                         m.m2 * v.x + m.m6 * v.y + m.m10 * v.z}; }
const Color RAW{110, 22, 20, 255}, CRUST{52, 10, 9, 255}, MARROW{168, 150, 118, 255};

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
    switch (j) {
        case J_HEAD: return R_HEAD;
        case J_JAW: return R_JAW;
        case J_SHO_L: return R_UARM_L;
        case J_SHO_R: return R_UARM_R;
        case J_ELB_L: case J_WRI_L: case J_FING1_L: case J_FING2_L: case J_THUMB_L: return R_FARM_L;
        case J_ELB_R: case J_WRI_R: case J_FING1_R: case J_FING2_R: case J_THUMB_R: return R_FARM_R;
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
        add(s ? R_FARM_R : R_FARM_L, joint(s ? J_ELB_R : J_ELB_L), joint(s ? J_FING1_R : J_FING1_L), 0.048f * fat);
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

// Guns are built in wrist space: the barrel runs down the hand (-y) above the web of the thumb (-z);
// the shotgun is turned in the hand by shotgun_hold().
Matrix Character::gun_frame() const {
    return weapon_ == 1 ? MatrixMultiply(shotgun_hold(), W_[J_WRI_R]) : W_[J_WRI_R];
}

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

// ── A tool: fitting the shotgun hold ─────────────────────────────────────────────
std::string Character::fit_shotgun(const ShotgunFit& goal) {
    weapon_ = 1;
    Vector3 T[J_COUNT]{};
    float bob = 0;
    targets(Pose::Aim, 0, 0, 0, T, bob);
    bob_ = bob;
    pitch_ = pivot_ = lift_ = 0;
    pos_ = {};
    yaw_ = 0;
    for (auto& t : twitch_) t = {};
    const Vector3 aim = Vector3Normalize(goal.aim);
    const bool cheek = goal.cheek;
    // Points on the gun (cast_guns.cpp's rifle_at, before the hold): the middle of the butt pad, the
    // fore-end's belly toward its back (where a hand pumps it), the top of the comb.
    const Vector3 butt{0, 0.2323f, 0.0512f}, belly = goal.left, comb{0, 0.0553f, -0.0268f};
    constexpr int K = 17;   // SHO_R xyz, ELB_R, WRI_R xyz, SHO_L xyz, ELB_L, WRI_L x z, NECK xyz, grip tilt
    // (the wrist, in its joint's axes: x tips the hand sideways in the plane of the palm, 30 degrees
    // at most; y twists it; z bends it toward the palm or its back, 75 degrees. The grip in the fist
    // is fixed: fingers round the front of the stock's wrist, thumb over it.)
    const float lo[K] = {-0.6f, -1.2f, -1.4f, 0.0f, -0.55f, -1.6f, -1.3f, -0.3f, -1.2f, -1.4f, 0.0f, -1.2f, -1.2f, -0.6f, -0.5f, -0.5f, GRIP_TILT};
    const float hi[K] = {2.6f, 1.2f, 1.4f, 2.6f, 0.55f, 1.6f, 1.3f, 2.8f, 1.2f, 1.4f, 2.4f, 1.2f, 1.2f, 0.3f, 0.5f, 0.5f, GRIP_TILT};
    float gaps[3]{};   // how far off the butt, the left hand and the cheek end up (m)
    float parts[6]{};
    auto eval = [&](const float* q) {
        for (int j = 0; j < J_COUNT; ++j) ang_[j] = T[j];
        ang_[J_SHO_R] = {q[0], q[1], q[2]};
        ang_[J_ELB_R] = {q[3], 0, 0};
        ang_[J_WRI_R] = {q[4], q[5], q[6]};   // the hand bends with the gun in it
        ang_[J_SHO_L] = {q[7], q[8], q[9]};
        ang_[J_ELB_L] = {q[10], 0, 0};
        ang_[J_WRI_L] = {q[11], 0, q[12]};
        ang_[J_NECK] = {q[13], q[14], q[15]};
        fk();
        const Matrix G = MatrixMultiply(shotgun_hold(q[16]), W_[J_WRI_R]);
        const Vector3 bore = Vector3Normalize(rotate_only({0, -1, 0}, G));
        const Vector3 pocket = Vector3Add(joint(J_SHO_R), goal.pocket);
        const Vector3 palm = Vector3Lerp(joint(J_WRI_L), joint(J_FING1_L), 0.5f);
        gaps[0] = Vector3Distance(Vector3Transform(butt, G), pocket);
        gaps[1] = Vector3Distance(palm, Vector3Add(Vector3Transform(belly, G), {0, -0.025f, 0}));
        gaps[2] = Vector3Distance(Vector3Transform(comb, G), Vector3Add(joint(J_JAW), {0, -0.03f, 0}));
        parts[0] = 600.0f * (1.0f - Vector3DotProduct(bore, aim));
        parts[1] = 4000.0f * gaps[0] * gaps[0];
        parts[2] = 1000.0f * gaps[1] * gaps[1];
        parts[3] = cheek ? 40.0f * gaps[2] * gaps[2] : 0.0f;
        const float over = joint(J_ELB_R).y - (joint(J_SHO_R).y + 0.04f);   // the elbow out, but not above the shoulder
        parts[4] = over > 0 ? 200.0f * over * over : 0.0f;
        parts[5] = 0.05f * (3.0f * q[4] * q[4] + 0.5f * q[5] * q[5] + q[6] * q[6]);   // a wrist bent no further than it must
        return parts[0] + parts[1] + parts[2] + parts[3] + parts[4] + parts[5];
    };
    unsigned rng = 0x2545F491u;
    auto rnd = [&rng]() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return float(rng & 0xFFFFFF) / 16777215.0f; };
    const float start[K] = {0.5f, 0.25f, 0.0f, 1.2f, 0.0f, 0.0f, 0.0f, 1.1f, 0.0f, 0.45f, 0.5f, 0.0f, 0.0f, T[J_NECK].x, T[J_NECK].y, T[J_NECK].z,
                            GRIP_TILT};
    float bestq[K];
    std::copy(start, start + K, bestq);
    float best = eval(bestq);
    for (int restart = 0; restart < 12; ++restart) {   // several starts: the arms have more than one way to hold a gun
        float q[K];
        for (int k = 0; k < K; ++k) q[k] = restart == 0 ? start[k] : lo[k] + (hi[k] - lo[k]) * rnd();
        float cur = eval(q), step = 0.8f;
        for (int it = 0; it < 40000; ++it) {
            float t[K];
            std::copy(q, q + K, t);
            const int n = 1 + int(rnd() * 2.99f);
            for (int m = 0; m < n; ++m) {
                const int k = std::min(K - 1, int(rnd() * float(K)));
                t[k] = std::clamp(t[k] + (rnd() * 2 - 1) * step, lo[k], hi[k]);
            }
            const float c = eval(t);
            if (c < cur) { cur = c; std::copy(t, t + K, q); }
            if (it % 4000 == 3999) step *= 0.65f;
        }
        if (cur < best) { best = cur; std::copy(q, q + K, bestq); }
    }
    eval(bestq);
    const float* q = bestq;
    char buf[800];
    std::snprintf(buf, sizeof(buf),
                  "cost %.4f (bore %.4f butt %.4f hand %.4f cheek %.4f elbow %.4f wrist %.4f)\n"
                  "  gaps: butt %.1f cm, left hand %.1f cm, cheek %.1f cm; grip tilt %.3f\n"
                  "  SHO_R {%.3f, %.3f, %.3f} ELB_R %.3f WRI_R {%.3f, %.3f, %.3f}\n"
                  "  SHO_L {%.3f, %.3f, %.3f} ELB_L %.3f WRI_L {%.3f, 0, %.3f} NECK {%.3f, %.3f, %.3f}",
                  best, parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], gaps[0] * 100, gaps[1] * 100, gaps[2] * 100, q[16],
                  q[0], q[1], q[2], q[3], q[4], q[5], q[6], q[7], q[8], q[9], q[10], q[11], q[12], q[13], q[14], q[15]);
    return buf;
}

}  // namespace dw
