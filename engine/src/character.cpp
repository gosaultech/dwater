// damned_waters/engine/src/character.cpp
// Purpose: the rig shared by the whole cast: joint forward kinematics, a root
// that can topple (falls, knock-downs) or go prone (crawling), eased pose tables,
// involuntary twitches, and "dangles": verlet rope simulations for anything that
// should swing. The cast itself is built in cast_survivor.cpp and cast_drowned.cpp.
#include "dw/character.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>

#include "dw/character_file.hpp"
#include "dw/core.hpp"
#include "dw/room_spec.hpp"
#include "cast_guns.hpp"
#include "grips.hpp"

namespace dw {
namespace {
constexpr std::array<int, J_COUNT> make_parents() {
    std::array<int, J_COUNT> p{-1,      J_PELVIS, J_SPINE, J_CHEST, J_NECK,   J_HEAD,  J_CHEST, J_SHO_L, J_ELB_L,
                               J_CHEST, J_SHO_R,  J_ELB_R, J_PELVIS, J_HIP_L, J_KNE_L, J_PELVIS, J_HIP_R, J_KNE_R};
    for (int side = 0; side < 2; ++side)   // each finger hangs off the wrist, segment after segment
        for (int f = 0; f < 5; ++f)
            for (int k = 0; k < 3; ++k) {
                const int j = finger_joint(side == 1, f, k);
                p[size_t(j)] = k == 0 ? (side ? J_WRI_R : J_WRI_L) : j - 1;
            }
    return p;
}
constexpr std::array<int, J_COUNT> PARENT = make_parents();
enum RootMode { STAND = 0, BACK = 1, PRONE = 2 };

float frand(unsigned& s) {   // xorshift: deterministic per character, no global RNG state
    s ^= s << 13; s ^= s >> 17; s ^= s << 5;
    return float(s & 0xFFFFFF) / float(0xFFFFFF);
}
Vector3 closest_on_segment(Vector3 p, Vector3 a, Vector3 b) {
    Vector3 ab = Vector3Subtract(b, a);
    float t = std::clamp(Vector3DotProduct(Vector3Subtract(p, a), ab) / std::max(Vector3LengthSqr(ab), 1e-8f), 0.0f, 1.0f);
    return Vector3Add(a, Vector3Scale(ab, t));
}
}  // namespace

Character build_survivor();
Character build_drowned(int variant);
Character build_citizen(const std::string& id, int variant);
// The Drowned are townspeople built by tools/characters (.dwc files); until one is built, the
// procedural corpse stands in for it.
Character Character::make(Kind k, int variant) {
    if (k == Kind::Survivor) return build_survivor();
    static const char* const CITIZENS[] = {"office_worker", "woman_dress", "pieter"};
    const std::string id = CITIZENS[((variant % 3) + 3) % 3];
    if (FileExists((repo_root() + "/engine/assets/characters/" + id + ".dwc").c_str())) return build_citizen(id, variant);
    return build_drowned(variant);
}

// Procedural detail is sampled in each part's own space; without an offset every part (both
// hands, both feet...) would start at the same spot in the pattern and share its blotches.
Vector3 Character::pattern_offset() {
    unsigned h = (++parts_) * 2654435761u ^ 0x5bd1e995u;
    auto f = [&h]() { h ^= h << 13; h ^= h >> 17; h ^= h << 5; return float(h % 10000) / 10000.0f * 40.0f - 20.0f; };
    float x = f(), y = f(), z = f();
    return {x, y, z};
}

void Character::add_rigid(int joint, int region, MeshData& d, int tag, int drive, Vector3 travel) {
    if (!d.count()) return;
    const Vector3 o = pattern_offset();
    for (size_t i = 0; i < d.count(); ++i) { d.tan[i * 4] += o.x; d.tan[i * 4 + 1] += o.y; d.tan[i * 4 + 2] += o.z; }
    rigid_.push_back({joint, region, upload(d), tag, drive, travel});
}

void Character::add_sweep(Sweep s, std::vector<Pt> pts) {
    s.surface(pattern_offset());
    Dyn d{std::move(s), std::move(pts), {}};
    d.mesh = upload(d.sweep.data, true);   // real positions arrive on the first animate()
    dyn_.push_back(std::move(d));
}

void Character::add_dangle(int joint, int region, Vector3 anchor, Vector3 rest, int n, float seg, Profile prof, int mat, Color c,
                           float drag, float stiff, int pin_joint, Vector3 pin) {
    Dangle d{joint, region, anchor, Vector3Normalize(rest), pin_joint, pin, n, seg, drag, stiff, {}, {},
             Sweep(std::max(6, (n - 1) * 3 + 1), 6, std::move(prof), mat, c, seg * (n - 1)), {}, false};
    d.sweep.surface(pattern_offset());
    d.p.assign(n, {});
    d.prev.assign(n, {});
    d.mesh = upload(d.sweep.data, true);
    dangles_.push_back(std::move(d));
}

// Each finger joint bends about the line across its finger and along the palm (the finger's
// direction crossed with the way the palm faces): a hinge, like a knuckle. The palm faces across
// the knuckle line, away from the back of the hand; the thumb bends toward the palm the same way.
void Character::find_hinges() {
    for (int side = 0; side < 2; ++side) {
        const bool right = side == 1;
        const Vector3 wrist = rest_[right ? J_WRI_R : J_WRI_L];
        const Vector3 index = Vector3Subtract(rest_[finger_joint(right, F_INDEX, 0)], wrist);
        const Vector3 little = Vector3Subtract(rest_[finger_joint(right, F_LITTLE, 0)], wrist);
        Vector3 palm = Vector3Normalize(Vector3CrossProduct(index, little));   // (the right hand's; the left is its mirror)
        if (!right) palm = Vector3Negate(palm);
        for (int f = 0; f < 5; ++f)
            for (int k = 0; k < 3; ++k) {
                const int j = finger_joint(right, f, k);
                const Vector3 along = k < 2 ? Vector3Subtract(rest_[j + 1], rest_[j]) : Vector3Subtract(rest_[j], rest_[j - 1]);
                hinge_[j] = Vector3Normalize(Vector3CrossProduct(Vector3Normalize(along), palm));
            }
    }
}

void Character::curl(Vector3* T, bool right, int finger, float k0, float k1, float k2, float together) const {
    const float a[3] = {k0, k1, k2};
    // Brought in toward the middle finger at the knuckle (`together` of the way): the rest pose's
    // hand is splayed, and a flat hand with its fingers apart looks like a starfish, not a hand.
    Matrix in = MatrixIdentity();
    if (together != 0 && finger != F_THUMB && finger != F_MIDDLE) {
        const int j0 = finger_joint(right, finger, 0), m0 = finger_joint(right, F_MIDDLE, 0);
        const Vector3 d = Vector3Normalize(Vector3Subtract(rest_[j0 + 1], rest_[j0]));
        const Vector3 dm = Vector3Normalize(Vector3Subtract(rest_[m0 + 1], rest_[m0]));
        const Vector3 axis = Vector3CrossProduct(d, dm);
        const float len = Vector3Length(axis);
        if (len > 1e-4f) in = MatrixRotate(Vector3Scale(axis, 1.0f / len), together * std::atan2(len, Vector3DotProduct(d, dm)));
    }
    for (int k = 0; k < 3; ++k) {
        const int j = finger_joint(right, finger, k);
        // The bend as this rig's three angles (z, then x, then y): R = Ry Rx Rz.
        const Matrix m = k == 0 ? MatrixMultiply(in, MatrixRotate(hinge_[j], a[k])) : MatrixRotate(hinge_[j], a[k]);
        T[j] = {std::asin(std::clamp(-m.m9, -1.0f, 1.0f)), std::atan2(m.m8, m.m10), std::atan2(m.m1, m.m5)};
    }
}

bool Character::load_body(const std::string& path) {
    const CharacterFile f = CharacterFile::load(path);
    if (!f.ok() || f.joints.size() != size_t(J_COUNT)) {
        TraceLog(LOG_ERROR, "character: %s", f.ok() ? "joint count mismatch" : f.error.c_str());
        return false;
    }
    for (int j = 0; j < J_COUNT; ++j) {
        rest_[j] = {f.joints[j][0], f.joints[j][1], f.joints[j][2]};
        off_[j] = PARENT[j] < 0 ? rest_[j] : Vector3Subtract(rest_[j], rest_[PARENT[j]]);
    }
    find_hinges();
    pelvis_h_ = rest_[J_PELVIS].y;
    for (const auto& p : f.parts) add_skinned(p);
    // The torso's shape, for keeping the elbows and forearms out of it (arm_to): the body's own
    // vertices (torso, coat), each in the frame of the joint that carries it most, the chest's
    // for the upper half and the pelvis's for the lower.
    for (const auto& p : f.parts)
        for (size_t v = 0; v < p.vertices(); ++v) {
            if (v < p.region.size() && p.region[v] != R_BODY) continue;
            int top = 0;
            for (int k = 1; k < 4; ++k)
                if (p.weight[v * 4 + k] > p.weight[v * 4 + top]) top = k;
            const int j = p.joint[v * 4 + top];
            const Vector3 at{p.pos[v * 3], p.pos[v * 3 + 1], p.pos[v * 3 + 2]};
            auto in = [&](int frame) { const Vector3 l = Vector3Subtract(at, rest_[frame]); return clearance::V3{l.x, l.y, l.z}; };
            if (j == J_CHEST || j == J_SPINE) torso_[0].add(in(J_CHEST));
            if (j == J_PELVIS || j == J_SPINE) torso_[1].add(in(J_PELVIS));
        }
    for (auto& t : torso_) t.finish();
    for (const auto& a : f.anchors)
        anchors_.push_back({a.name, a.joint, {a.pos[0], a.pos[1], a.pos[2]}, {a.dir[0], a.dir[1], a.dir[2]}});
    return true;
}

const Character::Anchor* Character::anchor(const std::string& name) const {
    for (const auto& a : anchors_)
        if (a.name == name) return &a;
    return nullptr;
}

// Each strand is a tube: n rings of (sides + 1) vertices (the last repeats the first, so the
// pattern coordinate "around" can run 0..1 without jumping back at a seam), plus a tip vertex.
// Pattern space for strands (read by the shader's locs material): x = around (0..1, plus a
// per-strand phase), y = metres along the strand, z = a per-strand seed.
void Character::add_strands(Strands s) {
    if (s.ribbon) s.sides = 2;   // three vertices across: edge, middle, edge
    const int count = int(s.anchor.size()), ring = s.sides, row = ring + 1, per = s.n * row + (s.ribbon ? 0 : 1);
    s.p.assign(size_t(count) * s.n, {});
    s.prev = s.p;
    Mesh m{};
    m.vertexCount = count * per;
    m.triangleCount = count * ((s.n - 1) * ring * 2 + (s.ribbon ? 0 : ring));
    m.vertices = static_cast<float*>(MemAlloc(unsigned(m.vertexCount * 3 * sizeof(float))));
    m.normals = static_cast<float*>(MemAlloc(unsigned(m.vertexCount * 3 * sizeof(float))));
    m.texcoords = static_cast<float*>(MemAlloc(unsigned(m.vertexCount * 2 * sizeof(float))));
    m.tangents = static_cast<float*>(MemAlloc(unsigned(m.vertexCount * 4 * sizeof(float))));
    m.colors = static_cast<unsigned char*>(MemAlloc(unsigned(m.vertexCount * 4)));
    m.indices = static_cast<unsigned short*>(MemAlloc(unsigned(m.triangleCount * 3 * sizeof(unsigned short))));
    unsigned short* ix = m.indices;
    for (int k = 0; k < count; ++k) {
        const int base = k * per;
        for (int i = 0; i + 1 < s.n; ++i)
            for (int j = 0; j < ring; ++j) {
                const int a = base + i * row + j, b = a + 1, c = a + row, d = b + row;
                *ix++ = (unsigned short)a; *ix++ = (unsigned short)c; *ix++ = (unsigned short)b;
                *ix++ = (unsigned short)b; *ix++ = (unsigned short)c; *ix++ = (unsigned short)d;
            }
        const int tip = base + s.n * row, last = base + (s.n - 1) * row;
        for (int j = 0; j < ring && !s.ribbon; ++j) {
            *ix++ = (unsigned short)(last + j); *ix++ = (unsigned short)tip; *ix++ = (unsigned short)(last + j + 1);
        }
        Vector3 o = pattern_offset();
        if (s.ribbon) o.x = std::floor(o.x);   // so the shader finds "across" (0..1) as the fraction
        const float shade = 0.88f + 0.24f * (o.x + 20.0f) / 40.0f;   // no two strands quite the same colour
        for (int v = 0; v < per; ++v) {
            const int idx = base + v, ringi = std::min(v / row, s.n - 1), j = v == per - 1 ? 0 : v % row;
            const float along = v == per - 1 ? float(s.n - 1) * s.seg[k] + s.radius[k] : float(ringi) * s.seg[k];
            m.texcoords[idx * 2] = float(s.mat);
            m.texcoords[idx * 2 + 1] = 0.6f + 0.4f * std::min(1.0f, along / 0.06f);   // shadowed where they leave the scalp
            m.tangents[idx * 4] = o.x + float(j) / float(ring) * (s.ribbon ? 0.999f : 1.0f);
            m.tangents[idx * 4 + 1] = o.y + along;
            m.tangents[idx * 4 + 2] = o.z;
            // Ribbons: how far toward a thinned-out edge or end (0 in the middle, 1 at the edge).
            m.tangents[idx * 4 + 3] = s.ribbon ? std::max(std::fabs(float(j) - 1.0f),
                                                          std::clamp((float(ringi) / float(s.n - 1) - 0.55f) / 0.45f, 0.0f, 1.0f))
                                               : 0.0f;
            float t = std::clamp((float(ringi) / float(s.n - 1) - 0.45f) / 0.55f, 0.0f, 1.0f);   // the last half fades
            t = s.tip.a > 0 ? t * t * (3 - 2 * t) : 0.0f;
            auto ch = [&](unsigned char a, unsigned char b) {
                return (unsigned char)std::clamp((float(a) + (float(b) - float(a)) * t) * shade, 0.0f, 255.0f);
            };
            m.colors[idx * 4] = ch(s.col.r, s.tip.r); m.colors[idx * 4 + 1] = ch(s.col.g, s.tip.g);
            m.colors[idx * 4 + 2] = ch(s.col.b, s.tip.b); m.colors[idx * 4 + 3] = 255;
        }
    }
    UploadMesh(&m, true);
    s.mesh = m;
    strands_.push_back(std::move(s));
}

void Character::step_strands(float dt) {
    const float h = std::clamp(dt, 1e-4f, 1.0f / 20.0f);
    const Vector3 grav{0, -9.8f * h * h, 0};
    struct Seg { Vector3 a, b; float r; };
    std::vector<Seg> caps;
    for (const auto& c : colliders_) caps.push_back({Vector3Transform(c.oa, W_[c.a]), Vector3Transform(c.ob, W_[c.b]), c.r});
    for (auto& s : strands_) {
        const Matrix& W = W_[s.joint];
        const int count = int(s.anchor.size());
        for (int k = 0; k < count; ++k) {
            Vector3* p = &s.p[size_t(k) * s.n];
            Vector3* q = &s.prev[size_t(k) * s.n];
            auto rest_at = [&](int i) { return Vector3Transform(s.rest[size_t(k) * s.n + i], W); };
            if (!s.live)
                for (int i = 0; i < s.n; ++i) p[i] = q[i] = rest_at(i);
            p[0] = q[0] = rest_at(0);
            for (int i = 1; i < s.n; ++i) {
                const Vector3 v = Vector3Scale(Vector3Subtract(p[i], q[i]), 0.95f);
                q[i] = p[i];
                p[i] = Vector3Add(p[i], Vector3Add(v, grav));
                p[i] = Vector3Lerp(p[i], rest_at(i), s.stiff[k] * (1.0f - 0.45f * float(i) / float(s.n - 1)));   // firm at the root
            }
            for (int it = 0; it < 3; ++it) {
                for (int i = 0; i + 1 < s.n; ++i) {
                    Vector3 d = Vector3Subtract(p[i + 1], p[i]);
                    const float L = Vector3Length(d);
                    if (L < 1e-6f) continue;
                    const Vector3 corr = Vector3Scale(d, (L - s.seg[k]) / L);
                    if (i == 0) p[1] = Vector3Subtract(p[1], corr);
                    else { p[i] = Vector3Add(p[i], Vector3Scale(corr, 0.5f)); p[i + 1] = Vector3Subtract(p[i + 1], Vector3Scale(corr, 0.5f)); }
                }
                for (int i = 1; i < s.n; ++i)
                    for (const auto& c : caps) {
                        const Vector3 cq = closest_on_segment(p[i], c.a, c.b), off = Vector3Subtract(p[i], cq);
                        const float l = Vector3Length(off), r = c.r + (s.ribbon ? 0.003f : s.radius[k]);
                        if (l < r && l > 1e-6f) p[i] = Vector3Add(cq, Vector3Scale(off, r / l));
                    }
            }
        }
        s.live = true;
        const int ring = s.sides, row = ring + 1, per = s.n * row + (s.ribbon ? 0 : 1);
        if (s.ribbon) {
            // Ribbons: across each point, perpendicular to the strand and to the way out from the
            // skull, so they lie flat against the head and hang flat down the back.
            const Vector3 A = Vector3Transform(s.axisA, W), B = Vector3Transform(s.axisB, W);
            for (int k = 0; k < count; ++k) {
                const Vector3* p = &s.p[size_t(k) * s.n];
                for (int i = 0; i < s.n; ++i) {
                    const Vector3 t = Vector3Normalize(Vector3Subtract(p[std::min(i + 1, s.n - 1)], p[std::max(i - 1, 0)]));
                    Vector3 out = Vector3Subtract(p[i], closest_on_segment(p[i], A, B));
                    out = Vector3Subtract(out, Vector3Scale(t, Vector3DotProduct(out, t)));
                    if (Vector3LengthSqr(out) < 1e-10f) out = {0, 0, 1};
                    out = Vector3Normalize(out);
                    const Vector3 across = Vector3CrossProduct(t, out);
                    const float half = s.radius[k] * 0.5f * (1.0f - s.taper * float(i) / float(s.n - 1));
                    for (int j = 0; j <= ring; ++j) {
                        const float u = float(j) - 1.0f;   // -1, 0, 1
                        const Vector3 pos = Vector3Add(Vector3Add(p[i], Vector3Scale(across, u * half)),
                                                       Vector3Scale(out, (1.0f - u * u) * half * 0.2f));   // cupped a little
                        const int idx = k * per + i * row + j;
                        std::memcpy(&s.mesh.vertices[idx * 3], &pos, 12);
                        std::memcpy(&s.mesh.normals[idx * 3], &out, 12);
                    }
                }
            }
            UpdateMeshBuffer(s.mesh, 0, s.mesh.vertices, s.mesh.vertexCount * 12, 0);
            UpdateMeshBuffer(s.mesh, 2, s.mesh.normals, s.mesh.vertexCount * 12, 0);
            continue;
        }
        // Rebuild the tubes: a ring per point, slightly lumpy (palm-rolled, not machined), tapering a
        // little to a rounded tip.
        for (int k = 0; k < count; ++k) {
            const Vector3* p = &s.p[size_t(k) * s.n];
            Vector3 x{W.m0, W.m1, W.m2};
            for (int i = 0; i < s.n; ++i) {
                const Vector3 t = Vector3Normalize(Vector3Subtract(p[std::min(i + 1, s.n - 1)], p[std::max(i - 1, 0)]));
                // Parallel transport: carry the previous ring's x down the strand, minus its component along t.
                x = Vector3Subtract(x, Vector3Scale(t, Vector3DotProduct(x, t)));
                if (Vector3LengthSqr(x) < 1e-8f) x = Vector3CrossProduct(t, {0, 0, 1});
                x = Vector3Normalize(x);
                const Vector3 y = Vector3CrossProduct(t, x);
                const float lump = 1.0f + s.lump * std::sin(float(i) * 2.3f + float(k) * 1.7f);
                const float r = s.radius[k] * lump * (1.0f - s.taper * float(i) / float(s.n - 1));
                for (int j = 0; j <= ring; ++j) {
                    const float a = 2.0f * PI * float(j % ring) / float(ring);
                    const Vector3 nrm = Vector3Add(Vector3Scale(x, std::cos(a)), Vector3Scale(y, std::sin(a)));
                    const int idx = k * per + i * row + j;
                    const Vector3 pos = Vector3Add(p[i], Vector3Scale(nrm, r));
                    std::memcpy(&s.mesh.vertices[idx * 3], &pos, 12);
                    std::memcpy(&s.mesh.normals[idx * 3], &nrm, 12);
                }
            }
            const Vector3 dir = Vector3Normalize(Vector3Subtract(p[s.n - 1], p[s.n - 2]));
            const Vector3 tip = Vector3Add(p[s.n - 1], Vector3Scale(dir, s.radius[k] * 0.4f));   // a blunt, rounded end
            const int idx = k * per + s.n * row;
            std::memcpy(&s.mesh.vertices[idx * 3], &tip, 12);
            std::memcpy(&s.mesh.normals[idx * 3], &dir, 12);
        }
        UpdateMeshBuffer(s.mesh, 0, s.mesh.vertices, s.mesh.vertexCount * 12, 0);
        UpdateMeshBuffer(s.mesh, 2, s.mesh.normals, s.mesh.vertexCount * 12, 0);
    }
}

// How much of the wrist's turn a sleeve's very end takes (add_skinned).
constexpr float CUFF_FOLLOWS = 0.55f;

// Upload one skinned part. Vertex layout as the character shader expects (see mesh_builder.hpp),
// plus four joint ids and weights; the shader blends the joints' matrices (GPU skinning).
void Character::add_skinned(const FilePart& p) {
    const int n = int(p.vertices());
    auto alloc = [](size_t bytes) { return MemAlloc(static_cast<unsigned int>(bytes)); };
    Mesh m{};
    m.vertexCount = n;
    m.triangleCount = int(p.index.size() / 3);
    m.vertices = static_cast<float*>(alloc(p.pos.size() * sizeof(float)));
    m.normals = static_cast<float*>(alloc(p.nrm.size() * sizeof(float)));
    m.texcoords = static_cast<float*>(alloc(size_t(n) * 2 * sizeof(float)));
    m.tangents = static_cast<float*>(alloc(size_t(n) * 4 * sizeof(float)));
    m.colors = static_cast<unsigned char*>(alloc(p.col.size()));
    m.indices = static_cast<unsigned short*>(alloc(p.index.size() * sizeof(unsigned short)));
    m.boneIds = static_cast<unsigned char*>(alloc(p.joint.size()));
    m.boneWeights = static_cast<float*>(alloc(p.weight.size() * sizeof(float)));
    static_assert(J_COUNT == 48, "the skinning shader (shaders.cpp, CHAR_VS) holds boneMatrices[48]: one per joint");
    m.boneCount = J_COUNT;
    m.boneMatrices = static_cast<Matrix*>(alloc(sizeof(Matrix) * J_COUNT));
    m.texcoords2 = static_cast<float*>(alloc(size_t(n) * 2 * sizeof(float)));   // x: the body region (cut-off ones aren't drawn)
    std::vector<std::vector<int>> by_region(R_COUNT);
    std::memcpy(m.vertices, p.pos.data(), p.pos.size() * sizeof(float));
    std::memcpy(m.normals, p.nrm.data(), p.nrm.size() * sizeof(float));
    std::memcpy(m.colors, p.col.data(), p.col.size());
    std::memcpy(m.indices, p.index.data(), p.index.size() * sizeof(unsigned short));
    std::memcpy(m.boneIds, p.joint.data(), p.joint.size());
    std::memcpy(m.boneWeights, p.weight.data(), p.weight.size() * sizeof(float));
    const Vector3 o = pattern_offset();
    for (int i = 0; i < n; ++i) {
        m.texcoords[i * 2] = float(p.mat[i]);
        m.texcoords[i * 2 + 1] = float(p.col[i * 4 + 3]) / 255.0f;   // baked occlusion rides in the colour's alpha
        m.tangents[i * 4] = p.pos[i * 3] + o.x;   // pattern space: the rest pose, so detail sticks to the skin
        m.tangents[i * 4 + 1] = p.pos[i * 3 + 1] + o.y;
        m.tangents[i * 4 + 2] = p.pos[i * 3 + 2] + o.z;
        m.tangents[i * 4 + 3] = i < int(p.aux.size()) ? p.aux[i] : 0.0f;   // the material's spare value (see dwc.py)
        const int reg = i < int(p.region.size()) ? std::min(int(p.region[i]), int(R_COUNT) - 1) : int(R_BODY);
        m.texcoords2[i * 2] = float(reg);
        m.texcoords2[i * 2 + 1] = 0;
        by_region[size_t(reg)].push_back(i);
    }
    // A sleeve's cuff follows the hand a little as the wrist bends, the way cloth gathered round a
    // wrist does: skinned to the forearm alone, a bent wrist's skin pokes out through it.
    if (p.name != "body")
        for (int i = 0; i < n; ++i) {
            if (m.texcoords2[i * 2] != float(R_FARM_L) && m.texcoords2[i * 2] != float(R_FARM_R)) continue;
            const int wrist = m.texcoords2[i * 2] == float(R_FARM_L) ? J_WRI_L : J_WRI_R;
            const float d = Vector3Distance({p.pos[size_t(i) * 3], p.pos[size_t(i) * 3 + 1], p.pos[size_t(i) * 3 + 2]}, rest_[wrist]);
            constexpr float REACH = 0.06f;
            if (d >= REACH) continue;
            float* w = &m.boneWeights[i * 4];
            unsigned char* id = &m.boneIds[i * 4];
            const float share = CUFF_FOLLOWS * (1.0f - d / REACH);
            int slot = -1;
            for (int k = 0; k < 4; ++k) if (id[k] == wrist) slot = k;
            if (slot < 0) {   // (the slot with the least weight makes room)
                slot = 0;
                for (int k = 1; k < 4; ++k) if (w[k] < w[slot]) slot = k;
                const float freed = w[slot];
                w[slot] = 0;
                id[slot] = static_cast<unsigned char>(wrist);
                const float rest = 1.0f - freed;
                if (rest > 1e-5f) for (int k = 0; k < 4; ++k) w[k] /= rest;
            }
            for (int k = 0; k < 4; ++k) w[k] *= 1.0f - share;
            w[slot] += share;
        }
    for (int j = 0; j < J_COUNT; ++j) m.boneMatrices[j] = MatrixIdentity();
    UploadMesh(&m, false);
    skinned_.push_back({p.name, m, std::move(by_region)});
}

void Character::fk() {
    // Root: (pitch about a pivot height, then lift) -> yaw -> position. Pitch +x topples the body
    // backward about the pivot; -x pitches it face-down.
    Matrix root = MatrixMultiply(MatrixMultiply(MatrixTranslate(0, -pivot_, 0), MatrixRotateX(pitch_)),
                                 MatrixTranslate(0, pivot_ + lift_, 0));
    root = MatrixMultiply(MatrixMultiply(root, MatrixRotateY(yaw_)), MatrixTranslate(pos_.x, pos_.y, pos_.z));
    for (int j = 0; j < J_COUNT; ++j) {
        const Vector3 a = Vector3Add(ang_[j], twitch_[j]);
        Matrix R = MatrixMultiply(MatrixMultiply(MatrixRotateZ(a.z), MatrixRotateX(a.x)), MatrixRotateY(a.y));
        Vector3 o = off_[j];
        if (j == J_PELVIS) o = {off_[j].x, pelvis_h_ + bob_, off_[j].z};
        Matrix L = MatrixMultiply(R, MatrixTranslate(o.x, o.y, o.z));
        W_[j] = MatrixMultiply(L, PARENT[j] < 0 ? root : W_[PARENT[j]]);
    }
}

// An arm reaching for a place, solved outright (no searching, the same every frame):
//  1. the elbow bends until shoulder-to-wrist is as long as shoulder-to-goal;
//  2. the upper arm swings to point the wrist at the goal, keeping the elbow's hinge as near as it
//     can to where the pose had it (so the elbow stays down and out, the way the pose was made);
//  3. the wrist turns the hand onto the place, and the fingers ride along.
// `w` blends it in from where the pose put the hand (the goal slides from there to the place).
Vector3 Character::arm_to(bool right, const Matrix& want, float w, bool free) {
    const int sho = right ? J_SHO_R : J_SHO_L, elb = right ? J_ELB_R : J_ELB_L, wri = right ? J_WRI_R : J_WRI_L;
    const Matrix now = W_[wri];
    const Vector3 goal = Vector3Lerp({now.m12, now.m13, now.m14}, {want.m12, want.m13, want.m14}, w);
    const Quaternion turn = QuaternionSlerp(QuaternionFromMatrix(now), QuaternionFromMatrix(want), w);
    // 1 and 2: the elbow and the upper arm.
    const Vector3 oe = off_[elb], ow = off_[wri];
    const Matrix S = MatrixMultiply(MatrixTranslate(off_[sho].x, off_[sho].y, off_[sho].z), W_[PARENT[sho]]);   // the shoulder, unturned
    const Matrix Si = MatrixInvert(S);
    const Vector3 hinge = Vector3Subtract(Vector3Transform({W_[sho].m0, W_[sho].m1, W_[sho].m2}, Si), Vector3Transform({0, 0, 0}, Si));
    const TwoBone arm = solve_two_bone(oe, ow, Vector3Transform(goal, Si), hinge);
    W_[sho] = MatrixMultiply(arm.turn, S);
    W_[elb] = MatrixMultiply(MatrixMultiply(MatrixRotateX(arm.elbow), MatrixTranslate(oe.x, oe.y, oe.z)), W_[sho]);
    // ... and then the elbow swung round the shoulder-to-wrist line (the hand stays put) to where
    // the arm is out of his body and, when `free` (working a reload, where nothing fitted says
    // where the elbow goes), the wrist is least bent and twisted: an elbow finds its own way, the
    // way you lift it off your ribs or turn it out to bring a hand round. Eased, so it never snaps.
    const int side = right ? 1 : 0;
    float want_swivel = 0;
    if (!torso_[0].empty()) {
        const Vector3 s0 = joint(sho), e0 = joint(elb);
        const Vector3 axis = Vector3Normalize(Vector3Subtract(goal, s0));
        const Matrix T = QuaternionToMatrix(turn);
        auto about = [&](float a) {
            return MatrixMultiply(MatrixMultiply(MatrixTranslate(-s0.x, -s0.y, -s0.z), MatrixRotate(axis, a)), MatrixTranslate(s0.x, s0.y, s0.z));
        };
        auto into = [&](float a) {   // how far the arm, swivelled by a, is in the body (m)
            const Vector3 e = Vector3Add(s0, Vector3RotateByAxisAngle(Vector3Subtract(e0, s0), axis, a));
            float d = -1;
            for (float k : {0.6f, 1.0f}) d = std::max(d, torso_in(Vector3Lerp(s0, e, k), 0.05f));   // the upper arm, the elbow
            for (float k : {0.3f, 0.6f}) d = std::max(d, torso_in(Vector3Lerp(e, goal, k), 0.042f));   // the forearm
            return d;
        };
        auto strain = [&](float a) {   // how far past comfortable the wrist would be (radians)
            Matrix X = MatrixMultiply(MatrixTranslate(ow.x, ow.y, ow.z), MatrixMultiply(W_[elb], about(a)));
            X.m12 = X.m13 = X.m14 = 0;
            float sw = 0, tw = 0;
            swing_twist(QuaternionFromMatrix(MatrixMultiply(T, MatrixInvert(X))), ow, sw, tw);
            return std::max(sw - 40.0f * DEG2RAD, 0.0f) + 0.6f * std::max(std::fabs(tw) - 75.0f * DEG2RAD, 0.0f);
        };
        // The cost of a swivel: being in the body above all, then a strained wrist, then lifting
        // the elbow (people keep their elbows down), then how far it swings.
        auto cost = [&](float a) {
            const Vector3 e = Vector3RotateByAxisAngle(Vector3Subtract(e0, s0), axis, a);   // (from the shoulder)
            const float lift = e.y - (e0.y - s0.y);
            const float wing = std::max(e.y + 0.08f, 0.0f);   // the elbow up near the shoulder's height or over it: a chicken wing
            return std::max(into(a), 0.0f) * 60.0f + (free ? strain(a) * 0.8f : 0.0f) + std::max(lift, 0.0f) * 1.5f +
                   wing * 25.0f + std::fabs(a) * 0.01f;
        };
        if (free || into(0) > 0) {
            float best = cost(0);
            for (int i = -17; i <= 18; ++i) {   // every 10 degrees round
                const float a = float(i) * (10.0f * DEG2RAD), c = cost(a);
                if (c < best) { best = c; want_swivel = a; }
            }
        }
    }
    // (eased the short way round)
    const float gap = std::remainder(want_swivel * w - swivel_[side], 2 * PI);
    swivel_[side] = std::remainder(swivel_[side] + gap * smoothing(18.0f, dt_), 2 * PI);
    if (std::fabs(swivel_[side]) > 1e-4f) {
        const Vector3 s0 = joint(sho);
        const Vector3 axis = Vector3Normalize(Vector3Subtract(goal, s0));
        const Matrix about = MatrixMultiply(MatrixMultiply(MatrixTranslate(-s0.x, -s0.y, -s0.z), MatrixRotate(axis, swivel_[side])),
                                            MatrixTranslate(s0.x, s0.y, s0.z));
        W_[sho] = MatrixMultiply(W_[sho], about);
        W_[elb] = MatrixMultiply(W_[elb], about);
    }
    // 3. The wrist: whatever turn takes the forearm's end to the place's.
    const Matrix X = MatrixMultiply(MatrixTranslate(ow.x, ow.y, ow.z), W_[elb]);
    Matrix Xr = X;
    Xr.m12 = Xr.m13 = Xr.m14 = 0;
    const Matrix bend = MatrixMultiply(QuaternionToMatrix(turn), MatrixInvert(Xr));   // the wrist's own turn
    W_[wri] = MatrixMultiply(bend, X);
    const int f0 = right ? J_THUMB1_R : J_THUMB1_L;
    for (int j = f0; j < f0 + 15; ++j) {   // the fingers ride the wrist
        const Vector3 a = Vector3Add(ang_[j], twitch_[j]);
        const Matrix Rj = MatrixMultiply(MatrixMultiply(MatrixRotateZ(a.z), MatrixRotateX(a.x)), MatrixRotateY(a.y));
        W_[j] = MatrixMultiply(MatrixMultiply(Rj, MatrixTranslate(off_[j].x, off_[j].y, off_[j].z)), W_[PARENT[j]]);
    }
    return {std::asin(std::clamp(-bend.m9, -1.0f, 1.0f)), std::atan2(bend.m8, bend.m10), std::atan2(bend.m1, bend.m5)};
}

// How far a ball at `p` (world) of radius `r` is into his torso (m; <= 0: clear), by the shape
// load_body took of it.
float Character::torso_in(Vector3 p, float r) const {
    float d = -1;
    for (int i = 0; i < 2; ++i) {
        if (torso_[i].empty()) continue;
        const Vector3 l = Vector3Transform(p, MatrixInvert(W_[i == 0 ? J_CHEST : J_PELVIS]));
        d = std::max(d, torso_[i].depth({l.x, l.y, l.z}, r));
    }
    return d;
}

namespace {
// Between two wrist places: the position along a curve, the turn the shortest way round.
Matrix blend_frames(const Matrix& a, const Matrix& b, Vector3 at, float k) {
    Matrix m = QuaternionToMatrix(QuaternionSlerp(QuaternionFromMatrix(a), QuaternionFromMatrix(b), k));
    m.m12 = at.x; m.m13 = at.y; m.m14 = at.z;
    return m;
}
Vector3 origin(const Matrix& m) { return {m.m12, m.m13, m.m14}; }
}  // namespace

Matrix Character::reload_place(const reload::Step& s, const Matrix& G) const {
    switch (s.place) {
        case reload::Place::Grip: {   // on the gun (the 870's fore-end where the pump has it)
            Matrix at = G;
            if (weapon_ == 1)
                for (const Rigid& r : rigid_)
                    if (r.drive == 2 && r.tag == 2) {
                        const Vector3 t = Vector3Transform(Vector3Scale(r.travel, pump), MatrixTranspose(shotgun_hold()));   // (wrist -> built: the hold's turn undone)
                        at = MatrixMultiply(MatrixTranslate(t.x, t.y, t.z), G);
                    }
            return MatrixMultiply(MatrixInvert(support_ ? support_->hold : MatrixIdentity()), at);
        }
        case reload::Place::Pocket: {
            const ReloadShape& r = reload_shape;
            const Matrix in = MatrixMultiply(MatrixMultiply(MatrixRotateX(r.pocket_tilt), MatrixRotateY(r.pocket_turn)),
                                             MatrixTranslate(r.pocket_at.x, r.pocket_at.y, r.pocket_at.z));
            return MatrixMultiply(in, W_[J_PELVIS]);
        }
        case reload::Place::Load:
        default:
            if (weapon_ == 1) return MatrixMultiply(MatrixInvert(grips::SHELL_LEFT.hold), MatrixMultiply(cast::shell_in(s.along), G));
            const Vector3 out = Vector3Scale(cast::m92fs_well_out(), s.along * 0.001f);   // (mm out of the grip)
            return MatrixMultiply(MatrixInvert(grips::MAG_LEFT.hold), MatrixMultiply(MatrixTranslate(out.x, out.y, out.z), G));
    }
}

void Character::reload_fingers(reload::Hand h, Vector3* f) const {
    const Grip& held = weapon_ == 1 ? grips::SHELL_LEFT : grips::MAG_LEFT;
    const Grip* grip = want_support_ ? want_support_ : support_;
    Vector3 T[J_COUNT]{};
    for (int k = F_INDEX; k <= F_LITTLE; ++k) {   // an open hand, the fingers a little curled
        const float more = 0.05f * float(k - F_INDEX);
        curl(T, false, k, 0.12f + more, 0.2f + more, 0.1f);
    }
    curl(T, false, F_THUMB, 0, 0.1f, 0.05f);
    Vector3 flat[J_COUNT]{};   // the heel of the hand: the fingers nearly straight, close together, the thumb along them
    for (int k = F_INDEX; k <= F_LITTLE; ++k) curl(flat, false, k, 0.05f, 0.08f, 0.04f, 1.2f);
    curl(flat, false, F_THUMB, 0.6f, 0.4f, 0.05f);
    // Holding the magazine: the forefinger up its front and the thumb along its side as fitted
    // (MAG_LEFT); the last three fingers wrapped loosely under the plate as a hand rests, not
    // clenched as tight as the fit pulls them (a fist's worth of bend at every joint folds the
    // fingers into the palm).
    Vector3 mag[J_COUNT]{};
    for (int k = F_MIDDLE; k <= F_LITTLE; ++k) {
        const float more = 0.08f * float(k - F_MIDDLE);
        curl(mag, false, k, 0.95f + more, 1.05f + more, 0.55f, 0.5f);
    }
    for (int k = 0; k < 15; ++k) {
        const Vector3 open = T[J_THUMB1_L + k];
        switch (h) {
            case reload::Hand::Grip: f[k] = grip ? grip->fingers[k] : open; break;
            case reload::Hand::Open: f[k] = open; break;
            case reload::Hand::Hold: f[k] = weapon_ == 0 && k >= 6 ? mag[J_THUMB1_L + k] : held.fingers[k]; break;
            case reload::Hand::Push: f[k] = k < 3 ? held.fingers[k] : Vector3Lerp(held.fingers[k], open, 0.7f); break;   // the thumb stays
            case reload::Hand::Slap: f[k] = flat[J_THUMB1_L + k]; break;
        }
    }
}

Matrix Character::load_frame() const { return W_[J_WRI_R]; }

// The hands, after the pose: each arm that has somewhere to be is bent there (arm_to), blended in
// by a weight that eases as the pose changes, so a hand slides onto the gun rather than jumping.
//  * Reloading the pistol, the right arm brings it in close (close_w_).
//  * The left hand: on the gun where its grip holds it, wherever the right hand has taken the gun
//    (aimed up or down, bucking from a shot, the 870's fore-end racked back under it); or through a
//    reload's steps (reload.hpp), curving through them; when what it follows changes, it eases
//    over from where it was (lh_fade_), held on the gun meanwhile (support_w_ eases it on and off).
void Character::hands(float dt) {
    ik_[0] = ik_[1] = false;
    // What's in the gun, what's in the hand.
    reload::Step st[reload::MAX_STEPS];
    int n = 0, seg = 0;
    float f = 0;
    if (reloading.on) {
        n = reload::steps(reloading.kind, reloading.from_grip, st);
        seg = reload::segment(st, n, reloading.t, f);
    }
    load_at_ = weapon_ == 1 ? 1 : 0;
    if (reloading.on && weapon_ == 0 && reloading.kind == reload::Kind::Magazine) {
        const float t = reloading.t;
        load_at_ = t < reload::MAG_DROP ? 0 : t < reload::MAG_GRAB ? 1 : t < reload::MAG_HOME ? 2 : 0;
    } else if (reloading.on && weapon_ == 1 && reloading.kind != reload::Kind::Magazine) {
        const float u = reload::shell_time(reloading.kind, reloading.t);
        load_at_ = u < reload::SHELL_GRAB ? 1 : u < reload::SHELL_LET_GO ? 2 : u < 0.99f ? 3 : 1;
        if (load_at_ == 3) {
            const float k = f * f * (3 - 2 * f);
            load_along_ = Lerp(st[seg].along, st[seg + 1].along, k);
        }
    }
    // 1. The pistol brought in close.
    if (close_w_ > 1e-3f && weapon_ == 0) {
        float cant = reload_shape.cant, lift = 0;
        const Vector3 CLOSE_AT = reload_shape.close_at;
        const float CLOSE_PITCH = reload_shape.pitch, CLOSE_YAW = reload_shape.yaw;
        if (reloading.on && reloading.kind == reload::Kind::Magazine) {   // a flick as the empty one drops; the slap lifts it
            const float t = reloading.t;
            cant += 0.12f * std::max(0.0f, 1.0f - std::fabs(t - 0.1f) / 0.06f);
            lift = 0.012f * std::max(0.0f, 1.0f - std::fabs(t - (reload::MAG_HOME + 0.02f)) / 0.04f);
        }
        const Matrix turn = MatrixMultiply(MatrixMultiply(MatrixMultiply(MatrixRotateX(PI / 2), MatrixRotateZ(cant)), MatrixRotateX(CLOSE_PITCH)),
                                           MatrixRotateY(CLOSE_YAW));
        const Vector3 grip = Vector3Transform(cast::m92fs_at(20, -75), turn);
        const Matrix G = MatrixMultiply(MatrixMultiply(turn, MatrixTranslate(CLOSE_AT.x - grip.x, CLOSE_AT.y + lift - grip.y, CLOSE_AT.z - grip.z)),
                                        W_[J_CHEST]);
        ik_wrist_[1] = arm_to(true, MatrixMultiply(MatrixInvert(pistol_hold()), G), close_w_, reloading.on);
        ik_[1] = true;
    }
    // 2. The left hand.
    if (!support_ || support_w_ < 1e-3f) { lh_source_ = 0; return; }
    const Matrix G = gun_frame();   // the gun's built space -> world
    Matrix want;
    int source;
    if (steps_ && reloading.on && n >= 2) {   // through the steps: a curve through their places, stopping where they stop
        source = 2 + 4 * weapon_;
        const int i0 = std::max(seg - 1, 0), i3 = std::min(seg + 2, n - 1);
        const Matrix A = reload_place(st[seg], G), B = reload_place(st[seg + 1], G);
        const Vector3 p0 = origin(reload_place(st[i0], G)), p1 = origin(A), p2 = origin(B), p3 = origin(reload_place(st[i3], G));
        const float h = st[seg + 1].t - st[seg].t;
        const Vector3 m1 = st[seg].stop || seg == 0 ? Vector3{} : Vector3Scale(Vector3Subtract(p2, p0), h / std::max(st[seg + 1].t - st[i0].t, 1e-4f));
        const Vector3 m2 = st[seg + 1].stop || seg + 1 == n - 1 ? Vector3{} : Vector3Scale(Vector3Subtract(p3, p1), h / std::max(st[i3].t - st[seg].t, 1e-4f));
        const float f2 = f * f, f3 = f2 * f;
        const Vector3 at = Vector3Add(Vector3Add(Vector3Scale(p1, 2 * f3 - 3 * f2 + 1), Vector3Scale(m1, f3 - 2 * f2 + f)),
                                      Vector3Add(Vector3Scale(p2, -2 * f3 + 3 * f2), Vector3Scale(m2, f3 - f2)));
        // The turn eases in and out where the hand stops, and runs on through where it doesn't.
        const float s0 = st[seg].stop ? 0.0f : 1.0f, s1 = st[seg + 1].stop ? 0.0f : 1.0f;
        const float k = std::clamp((f3 - 2 * f2 + f) * s0 + (-2 * f3 + 3 * f2) + (f3 - f2) * s1, 0.0f, 1.0f);
        want = blend_frames(A, B, at, k);
    } else {   // on the gun where its grip holds it
        source = 1 + 4 * weapon_;
        const reload::Step grip{0, reload::Place::Grip, 0, reload::Hand::Grip, true};
        want = reload_place(grip, G);
    }
    // What it follows has changed: ease over from where it was (held on the gun).
    if (source != lh_source_) {
        if (lh_source_ != 0) { lh_from_ = lh_last_; lh_fade_ = 0; }
        lh_source_ = source;
    }
    if (lh_fade_ < 1) {
        lh_fade_ = std::min(1.0f, lh_fade_ + dt / 0.22f);
        const float k = lh_fade_ * lh_fade_ * (3 - 2 * lh_fade_);
        const Matrix from = MatrixMultiply(lh_from_, G);
        want = blend_frames(from, want, Vector3Lerp(origin(from), origin(want), k), k);
    }
    lh_last_ = MatrixMultiply(want, MatrixInvert(G));
    ik_wrist_[0] = arm_to(false, want, support_w_, steps_ && reloading.on);
    ik_[0] = true;
}

void Character::animate(Pose pose, float speed, float dt, float aim_pitch) {
    t_ += dt;
    dt_ = dt;
    Vector3 T[J_COUNT]{};
    float bob = 0;
    targets(pose, speed, dt, aim_pitch, T, bob);
    const bool sharp = pose == Pose::Windup || pose == Pose::Strike || pose == Pose::Hurt || pose == Pose::Stagger ||
                       pose == Pose::CrawlStrike || pose == Pose::Kick || pose == Pose::Dodge;
    const float k = smoothing(sharp ? 16.0f : 9.0f, dt);
    for (int j = 0; j < J_COUNT; ++j)   // (the fingers turn the shortest way: their poses differ a lot)
        ang_[j] = j >= J_THUMB1_L ? slerp_angles(ang_[j], T[j], k) : Vector3Lerp(ang_[j], T[j], k);
    if (steps_)   // a reload's steps time the fingers themselves: they follow closely
        for (int j = J_THUMB1_L; j < J_THUMB1_R; ++j) ang_[j] = slerp_angles(ang_[j], T[j], smoothing(40.0f, dt));
    bob_ = Lerp(bob_, bob, k);
    if (want_support_) support_ = want_support_;   // (letting go, the hand eases off the grip it had)
    support_w_ = Lerp(support_w_, want_support_ ? 1.0f : 0.0f, k);
    const bool out = reloading.on && reloading.kind == reload::Kind::Magazine && reloading.t >= reload::DRIVE_OUT;   // (targets(): pushed back out)
    close_w_ = Lerp(close_w_, pose == Pose::Reload && weapon_ == 0 && kind == Kind::Survivor && !out ? 1.0f : 0.0f, k);

    // Twitches: the Drowned's nerves still fire. A joint snaps, then drifts back.
    const float decay = std::exp(-dt * 6.0f);
    for (auto& tw : twitch_) tw = Vector3Scale(tw, decay);
    if (kind == Kind::Drowned && pose != Pose::Dead) {
        twitch_in_ -= dt;
        if (twitch_in_ <= 0) {
            twitch_in_ = 1.2f + frand(rng_) * 3.0f;
            const float sgn = frand(rng_) < 0.5f ? -1.0f : 1.0f, r = frand(rng_);
            if (r < 0.55f) twitch_[J_HEAD] = Vector3Add(twitch_[J_HEAD], {0.25f * (frand(rng_) - 0.3f), 0.3f * sgn, 0.55f * sgn});
            else if (r < 0.8f) twitch_[J_NECK] = Vector3Add(twitch_[J_NECK], {-0.3f, 0.0f, 0.3f * sgn});
            else twitch_[sgn < 0 ? J_SHO_L : J_SHO_R] = Vector3Add(twitch_[sgn < 0 ? J_SHO_L : J_SHO_R], {0.5f, 0, 0.3f * sgn});
            twitch_[J_JAW].x -= 0.25f * frand(rng_);
        }
    }

    // Root: stand, lie on the back (knocked down / dead) or go prone (crawling).
    const bool prone_pose = pose == Pose::Crawl || pose == Pose::CrawlWindup || pose == Pose::CrawlStrike;
    int mode = prone_pose ? PRONE : (pose == Pose::Floored || pose == Pose::Dead) ? BACK : STAND;
    if (pose == Pose::Dead && root_mode_ == PRONE) mode = PRONE;   // a crawler dies face-down
    if (mode != root_mode_) {
        root_mode_ = mode;
        from_pitch_ = pitch_; from_pivot_ = pivot_; from_lift_ = lift_;
        root_k_ = 0;
    }
    float tp = 0, tv = 0, tl = 0;
    if (mode == BACK) { tp = kPi / 2; tv = 0; tl = thickness_; }
    if (mode == PRONE) { tp = -kPi / 2 + 0.12f; tv = pelvis_h_; tl = -(pelvis_h_ - thickness_ - 0.04f); }
    root_k_ = std::min(1.0f, root_k_ + dt * (mode == STAND ? 1.25f : 2.1f));
    const float e = mode == STAND ? root_k_ * root_k_ * (3 - 2 * root_k_) : std::pow(root_k_, 2.2f);   // falls accelerate
    pitch_ = Lerp(from_pitch_, tp, e);
    pivot_ = Lerp(from_pivot_, tv, e);
    lift_ = Lerp(from_lift_, tl, e);

    fk();
    hands(dt);
    for (int j = 0; j < J_COUNT; ++j)   // skinning: rest-pose vertex -> joint space -> where the joint is now
        bones_[j] = MatrixMultiply(MatrixTranslate(-rest_[j].x, -rest_[j].y, -rest_[j].z), W_[j]);
    // A forearm turns the hand by twisting along its length (the radius rolling round the ulna);
    // this rig has no joint for it, so the wrist does the turning. The forearm's skin takes half the
    // wrist's twist about its bone, so the skin wrings by half at the wrist and half at the elbow
    // instead of all of it at the wrist (a shotgun's grip turns the palm a long way).
    for (int side = 0; side < 2; ++side) {
        const int elbow = side ? J_ELB_R : J_ELB_L, wrist = side ? J_WRI_R : J_WRI_L;
        const float twist = ik_[side] ? ik_wrist_[side].y : ang_[wrist].y + twitch_[wrist].y;
        if (std::fabs(twist) < 1e-3f) continue;
        bones_[elbow] = MatrixMultiply(MatrixMultiply(MatrixTranslate(-rest_[elbow].x, -rest_[elbow].y, -rest_[elbow].z),
                                                      MatrixRotate(Vector3Normalize(off_[wrist]), 0.5f * twist)),
                                       W_[elbow]);
    }
    for (auto& s : skinned_) std::memcpy(s.mesh.boneMatrices, bones_, sizeof(bones_));
    const Vector3 right{std::cos(yaw_), 0, -std::sin(yaw_)};
    for (auto& d : dyn_) {
        std::vector<Vector3> pts;
        pts.reserve(d.pts.size());
        for (const auto& p : d.pts) pts.push_back(Vector3Transform(p.off, W_[p.joint]));
        d.sweep.build(pts, right);
        refresh(d.mesh, d.sweep.data);
    }
    step_dangles(dt);
    step_strands(dt);
    step_drips(dt);
}

void Character::add_drip_source(int joint, Vector3 off, bool blood, int region) {
    if (drip_mesh_.vertexCount == 0) {   // one small drop of each, shared by every drip this character sheds
        MeshData d;
        MeshBuilder(d).material(MAT_WATER).color(Color{120, 128, 130, 255}).ellipsoid({}, {0.003f, 0.0045f, 0.003f}, 8, 6);
        drip_mesh_ = upload(d);
        d = {};
        MeshBuilder(d).material(MAT_WATER).color(Color{96, 10, 10, 255}).ellipsoid({}, {0.0032f, 0.0048f, 0.0032f}, 8, 6);
        blood_drip_mesh_ = upload(d);
    }
    if (drip_src_.size() < 40) drip_src_.push_back({joint, off, 0.3f + 1.5f * frand(rng_), blood, region});
}

void Character::step_drips(float dt) {
    if (drip_src_.empty()) return;
    const float h = std::clamp(dt, 0.0f, 0.05f);
    for (auto& d : drips_) {
        d.v.y -= 9.8f * h;
        d.p = Vector3Add(d.p, Vector3Scale(d.v, h));
    }
    drips_.erase(std::remove_if(drips_.begin(), drips_.end(), [](const Drip& d) { return d.p.y < 0.003f; }), drips_.end());
    for (auto& src : drip_src_) {
        if ((src.next -= dt) > 0 || severed(src.region)) continue;
        src.next = (src.blood ? 0.2f : 0.35f) + 1.6f * frand(rng_);   // a drop gathers, falls; the next one takes a while
        Vector3 at;
        if (src.joint >= 0) {
            at = Vector3Transform(src.off, W_[src.joint]);
        } else {
            const Strands& st = strands_.front();
            const size_t k = size_t(src.off.x);
            if (!st.live || (k + 1) * size_t(st.n) > st.p.size()) continue;
            at = st.p[(k + 1) * size_t(st.n) - 1];
        }
        if (drips_.size() < 64) drips_.push_back({at, {0, -0.25f, 0}, src.blood});
    }
}

void Character::step_dangles(float dt) {
    const float h = std::clamp(dt, 1e-4f, 1.0f / 20.0f);
    const Vector3 grav{0, -9.8f * h * h, 0};
    struct Seg { Vector3 a, b; float r; };
    std::vector<Seg> caps;
    caps.reserve(colliders_.size());
    for (const auto& c : colliders_)
        caps.push_back({Vector3Transform(c.oa, W_[c.a]), Vector3Transform(c.ob, W_[c.b]), c.r});
    for (auto& d : dangles_) {
        const Matrix& W = W_[d.joint];
        const bool pinned = d.pin_joint >= 0;
        if (!d.live) {   // first frame: lay the strand out along its rest direction (or straight to its pin)
            Vector3 a = Vector3Transform(d.anchor, W);
            Vector3 b = pinned ? Vector3Transform(d.pin, W_[d.pin_joint]) : Vector3Transform(Vector3Add(d.anchor, Vector3Scale(d.rest, d.seg * (d.n - 1))), W);
            if (pinned) d.seg = Vector3Distance(a, b) * 1.12f / float(d.n - 1);   // a little slack: it sags
            for (int i = 0; i < d.n; ++i) d.p[i] = d.prev[i] = Vector3Lerp(a, b, float(i) / float(d.n - 1));
            d.live = true;
        }
        d.p[0] = d.prev[0] = Vector3Transform(d.anchor, W);
        const int last = pinned ? d.n - 1 : d.n;
        for (int i = 1; i < last; ++i) {
            Vector3 v = Vector3Scale(Vector3Subtract(d.p[i], d.prev[i]), d.drag);
            d.prev[i] = d.p[i];
            d.p[i] = Vector3Add(d.p[i], Vector3Add(v, grav));
            if (d.stiff > 0) {   // some strands hold a shape (hair plastered down, a stiff tongue)
                Vector3 rest = Vector3Transform(Vector3Add(d.anchor, Vector3Scale(d.rest, d.seg * i)), W);
                d.p[i] = Vector3Lerp(d.p[i], rest, d.stiff);
            }
        }
        if (pinned) d.p[d.n - 1] = d.prev[d.n - 1] = Vector3Transform(d.pin, W_[d.pin_joint]);
        for (int it = 0; it < 4; ++it) {
            for (int i = 0; i + 1 < d.n; ++i) {
                Vector3 dd = Vector3Subtract(d.p[i + 1], d.p[i]);
                float L = Vector3Length(dd);
                if (L < 1e-6f) continue;
                Vector3 corr = Vector3Scale(dd, (L - d.seg) / L);
                const bool fa = i == 0, fb = pinned && i + 1 == d.n - 1;
                if (fa && fb) continue;
                if (fa) d.p[i + 1] = Vector3Subtract(d.p[i + 1], corr);
                else if (fb) d.p[i] = Vector3Add(d.p[i], corr);
                else {
                    d.p[i] = Vector3Add(d.p[i], Vector3Scale(corr, 0.5f));
                    d.p[i + 1] = Vector3Subtract(d.p[i + 1], Vector3Scale(corr, 0.5f));
                }
            }
            for (int i = 1; i < last; ++i)
                for (const auto& c : caps) {
                    Vector3 q = closest_on_segment(d.p[i], c.a, c.b), off = Vector3Subtract(d.p[i], q);
                    float l = Vector3Length(off);
                    if (l < c.r && l > 1e-6f) d.p[i] = Vector3Add(q, Vector3Scale(off, c.r / l));
                }
            for (int i = 1; i < last; ++i) d.p[i].y = std::max(d.p[i].y, 0.004f);   // the floor
        }
        d.sweep.build(d.p, {W.m0, W.m1, W.m2});
        refresh(d.mesh, d.sweep.data);
    }
}

void Character::targets(Pose pose, float speed, float dt, float ap, Vector3* T, float& bob) {
    const bool drowned = kind == Kind::Drowned;
    for (float s : {-1.0f, 1.0f}) {   // relaxed baseline
        T[s < 0 ? J_SHO_L : J_SHO_R] = {0.05f, 0, -0.1f * s};
        T[s < 0 ? J_ELB_L : J_ELB_R] = {0.2f, 0, 0};
        T[s < 0 ? J_HIP_L : J_HIP_R] = {0.03f, 0, 0.02f * s};
        T[s < 0 ? J_KNE_L : J_KNE_R] = {-0.07f, 0, 0};
    }
    for (bool right : {false, true}) {   // hands: fingers loosely curled toward the palm (palms face the body)
        for (int f = F_INDEX; f <= F_LITTLE; ++f) {
            const float more = 0.05f * float(f - F_INDEX);   // the little finger curls furthest
            curl(T, right, f, (drowned ? 0.5f : 0.25f) + more, (drowned ? 0.8f : 0.35f) + more, drowned ? 0.45f : 0.2f);
        }
        curl(T, right, F_THUMB, 0, 0.15f, 0.1f);
    }
    if (!drowned) {   // the right hand round whichever gun is in it (--fitgrips)
        const Grip& g = weapon_ == 1 ? grips::SHOTGUN_RIGHT : grips::PISTOL_RIGHT;
        for (int k = 0; k < 15; ++k) T[J_THUMB1_R + k] = g.fingers[k];
    }
    T[J_SPINE] = {-0.02f + std::sin(t_ * 1.6f) * 0.012f, 0, 0};
    T[J_CHEST] = {std::sin(t_ * 1.6f + 0.5f) * 0.01f, 0, 0};
    T[J_NECK] = {-0.05f, 0, 0};
    T[J_PELVIS] = {0, 0, std::sin(t_ * 0.5f) * 0.02f};
    if (drowned) {
        // Wrong even at rest: hunched, the neck juts forward then bends the face up at you, the head
        // hangs off to one side and the dislocated jaw hangs open, working slowly as if gasping.
        const float gasp = std::sin(t_ * 1.15f), sway = std::sin(t_ * 0.7f);
        T[J_SPINE] = {-0.3f + gasp * 0.015f, 0.04f, 0.08f};
        T[J_CHEST] = {-0.1f - gasp * 0.03f, 0.05f, 0};
        T[J_NECK] = {0.02f, 0, 0.14f};
        T[J_HEAD] = {0.3f - 0.95f * bow_ + sway * 0.05f, 0.12f, (0.42f + sway * 0.08f) * (1.0f - 0.6f * bow_)};
        T[J_JAW] = {-0.95f + gasp * 0.12f, 0.2f, 0.09f};   // crooked: it hangs off to one side
        T[J_SHO_R] = {0.3f, 0, -0.06f};
        T[J_ELB_R] = {0.3f, 0, 0};
        T[J_SHO_L] = {0.12f, 0, 0.12f};
        T[J_ELB_L] = {0.4f, 0, 0};
        T[J_HIP_L] = {0.1f, 0, -0.03f};
        T[J_KNE_L] = {-0.16f, 0, 0};
        T[J_HIP_R] = {-0.04f, 0, 0.04f};
    }
    // The pistol's magazine in: the gun pushed back out to the aim, the support hand joining it on
    // the way (its wrist sits easy there, not bent round a gun held in at the chest).
    const bool driving_out = !drowned && weapon_ == 0 && pose == Pose::Reload && reloading.on && reloading.kind == reload::Kind::Magazine &&
                             reloading.t >= reload::DRIVE_OUT;
    switch (driving_out ? Pose::Aim : pose) {
        case Pose::Walk:
        case Pose::Run: {
            const bool run = pose == Pose::Run;
            // Sneaking (his walk at a sneak's pace, about 0.8 m/s): shorter steps placed carefully,
            // knees bent, a little hunched, arms drawn in, the head kept up. Eased in by the speed.
            const float sn = !drowned && !run ? std::clamp((1.15f - speed) / 0.3f, 0.0f, 1.0f) : 0.0f;
            phase_ += dt * std::max(speed, 0.4f) / (run ? 1.9f : 1.3f - 0.4f * sn) * 2 * kPi;
            float s = std::sin(phase_), c = std::cos(phase_), amp = run ? 0.62f : 0.42f - 0.12f * sn;
            const float knee = run ? 1.3f : 0.8f - 0.1f * sn, swing = amp * 0.7f * (1.0f - 0.5f * sn);
            T[J_HIP_L] = {s * amp + 0.12f * sn, 0, -0.02f};
            T[J_HIP_R] = {-s * amp + 0.12f * sn, 0, 0.02f};
            T[J_KNE_L] = {-0.1f - 0.25f * sn - std::max(0.0f, c) * knee, 0, 0};   // flex on the swing-through
            T[J_KNE_R] = {-0.1f - 0.25f * sn - std::max(0.0f, -c) * knee, 0, 0};
            T[J_SHO_L] = {-s * swing, 0, 0.12f};
            T[J_SHO_R] = {s * swing, 0, -0.12f};
            T[J_ELB_L] = {(run ? 1.3f : 0.3f + 0.4f * sn) + std::max(0.0f, -s) * 0.3f, 0, 0};
            T[J_ELB_R] = {(run ? 1.3f : 0.3f + 0.4f * sn) + std::max(0.0f, s) * 0.3f, 0, 0};
            T[J_SPINE] = {run ? -0.22f : -0.05f - 0.15f * sn, s * 0.1f, 0};
            T[J_CHEST] = {0, -s * 0.06f, 0};
            T[J_PELVIS] = {0, -s * 0.08f, 0};
            T[J_NECK].x += 0.1f * sn;
            bob = -std::fabs(s) * (run ? 0.045f : 0.022f - 0.01f * sn) - 0.013f * sn;
            break;
        }
        case Pose::Shamble: {   // the reach: both arms up at you, one leg dragging, the head rolling
            phase_ += dt * std::max(speed, 0.3f) / 0.95f * 2 * kPi;
            float s = std::sin(phase_), c = std::cos(phase_);
            T[J_HIP_L] = {s * 0.26f, 0, -0.03f};
            T[J_KNE_L] = {-0.1f - std::max(0.0f, c) * 0.55f, 0, 0};
            T[J_HIP_R] = {-s * 0.3f, 0, 0.05f};
            T[J_KNE_R] = {-0.12f - std::max(0.0f, -c) * 0.25f, 0, 0};   // the stiff, dragged leg
            T[J_SHO_R] = {1.3f + std::sin(t_ * 1.3f) * 0.12f, 0, -0.12f};
            T[J_ELB_R] = {0.3f, 0, 0};
            T[J_SHO_L] = {1.05f + s * 0.15f, 0, 0.16f};
            T[J_ELB_L] = {0.45f, 0, 0};
            T[J_SPINE] = {-0.34f + s * 0.05f, s * 0.12f, 0.1f};
            T[J_CHEST] = {-0.08f, -s * 0.08f, 0};
            T[J_HEAD] = {0.34f + c * 0.06f, 0.1f - s * 0.1f, 0.38f + s * 0.1f};
            T[J_PELVIS] = {0, 0, s * 0.06f};   // lurching from hip to hip
            bob = -std::fabs(s) * 0.035f;
            break;
        }
        case Pose::Aim: {   // both hands on the gun, elbows down: the pistol in the modern isosceles, or the shotgun shouldered
            if (weapon_ == 1) {   // the shotgun at the shoulder: bladed, the head down, the cheek on the comb
                // (fitted with --fit870: the butt in the shoulder, the bore level, the right eye over
                // it just above the receiver). The elbows down, the modern way: the right one dropped
                // under the stock, the hand wrapped round the stock's wrist and the wrist cocked; the
                // left hand stays on the fore-end by hands(). He aims up or down from the
                // waist, all of a piece.
                T[J_SHO_R] = {0.629f, 1.116f, 1.064f};
                T[J_ELB_R] = {1.809f, 0, 0};
                T[J_WRI_R] = {-0.850f, -0.941f, 0.217f};
                T[J_SHO_L] = {3.065f, -1.296f, -1.078f};
                T[J_ELB_L] = {0.000f, 0, 0};
                T[J_WRI_L] = {-0.237f, 0.029f, 0.022f};
                T[J_NECK] = {-0.611f, 0.221f, -0.450f};
                T[J_HEAD] = {0.350f, 0.500f, 0.314f};
                T[J_SPINE] = pitched({-0.08f, -0.500f, 0}, ap);
                T[J_CHEST] = {-0.300f, -0.228f, 0};
                T[J_HIP_L] = {0.25f, 0, -0.05f};
                T[J_KNE_L] = {-0.22f, 0, 0};
                T[J_HIP_R] = {-0.2f, 0, 0.06f};
                T[J_KNE_R] = {-0.1f, 0, 0};
                bob = -0.025f;
                break;
            }
            // The modern isosceles, thumbs forward (--fitpistol): both arms out but bent, the elbows
            // hanging down under the gun, the strong wrist tipped toward the little finger, the support
            // wrist cammed down; the gun brought up to the eye, the right eye on the sights; the
            // shoulders squared to the target, the chest leaning in.
            // Aiming up or down, the arms swing at the shoulders and the head goes with them, and he
            // bends a little at the waist; the left hand stays on the gun by hands().
            const float arms = 0.6f * ap, waist = 0.4f * ap;
            T[J_SHO_R] = pitched({1.433f, 0.853f, 0.469f}, arms);
            T[J_ELB_R] = {0.759f, 0, 0};
            T[J_WRI_R] = {-0.591f, -0.211f, 0.564f};
            T[J_SHO_L] = pitched({0.979f, -1.670f, -1.382f}, arms);
            T[J_ELB_L] = {0.691f, 0, 0};
            T[J_WRI_L] = {-0.572f, 0.204f, -0.177f};
            T[J_SPINE] = pitched({-0.06f, 0.289f, 0}, waist);
            T[J_CHEST] = {0.050f, -0.255f, 0};
            T[J_NECK] = pitched({-0.302f, -0.033f, -0.116f}, 0.5f * arms);
            T[J_HEAD] = pitched({0.107f, 0.039f, -0.011f}, 0.5f * arms);
            T[J_HIP_L] = {0.22f, 0, -0.04f};
            T[J_KNE_L] = {-0.2f, 0, 0};
            T[J_HIP_R] = {-0.2f, 0, 0.06f};
            T[J_KNE_R] = {-0.1f, 0, 0};
            bob = -0.02f;
            break;
        }
        case Pose::Kick: {   // a front kick to floor it: weight back, the right leg driving out
            T[J_HIP_R] = {1.35f, 0, 0.04f};
            T[J_KNE_R] = {-0.12f, 0, 0};
            T[J_HIP_L] = {-0.12f, 0, -0.03f};
            T[J_KNE_L] = {-0.3f, 0, 0};
            T[J_SPINE] = {0.22f, 0, 0};
            T[J_CHEST] = {0.1f, 0, 0};
            T[J_NECK] = {-0.15f, 0, 0};
            T[J_SHO_L] = {0.5f, 0, 0.45f};
            T[J_ELB_L] = {0.6f, 0, 0};
            T[J_SHO_R] = {0.35f, 0, -0.3f};
            T[J_ELB_R] = {0.9f, 0, 0};
            bob = -0.04f;
            break;
        }
        case Pose::Dodge: {   // a low hop out of the way: knees bent, leaning into it, arms tucked
            T[J_HIP_L] = {0.55f, 0, -0.12f - 0.25f * lean};
            T[J_HIP_R] = {0.5f, 0, 0.12f - 0.25f * lean};
            T[J_KNE_L] = T[J_KNE_R] = {-0.95f, 0, 0};
            T[J_SPINE] = {-0.38f, 0, -0.3f * lean};
            T[J_CHEST] = {-0.12f, 0, -0.1f * lean};
            T[J_NECK] = {0.15f, 0, 0};
            T[J_SHO_L] = {0.7f, 0, 0.35f};
            T[J_ELB_L] = {1.2f, 0, 0};
            T[J_SHO_R] = {0.6f, 0, -0.25f};
            T[J_ELB_R] = {1.1f, 0, 0};
            bob = -0.16f;
            break;
        }
        case Pose::Reload: {   // head down over the gun; the hands do the work (hands(), reload.hpp)
            T[J_NECK] = {-0.3f, 0, 0};
            T[J_SPINE] = {-0.08f, 0, 0};
            if (weapon_ == 1) {   // under the arm, the left hand at the loading port (--fit870); an empty gun is racked right
                                  // there, the hand sliding forward from the port onto the fore-end (no turning away to rack it)
                T[J_SHO_R] = {-0.179f, 0.944f, 0.262f};
                T[J_ELB_R] = {1.754f, 0, 0};
                T[J_WRI_R] = {0.164f, 0.008f, 0.232f};
                T[J_SHO_L] = {0.576f, 0.094f, 0.392f};
                T[J_ELB_L] = {1.249f, 0, 0};
                T[J_WRI_L] = {1.200f, 0.000f, 1.200f};
                T[J_SPINE].y = -0.500f;
                T[J_CHEST].y = 0.353f;
            } else {   // the pistol in close (where hands() takes it), the left hand low, toward the pocket
                T[J_SHO_R] = {0.6f, 0, -0.08f};
                T[J_ELB_R] = {1.35f, 0, 0};
                T[J_SHO_L] = {0.3f, 0, 0.12f};
                T[J_ELB_L] = {0.7f, 0, 0};
                T[J_NECK] = {-0.42f, 0, 0};   // eyes down on the magazine well
            }
            break;
        }
        case Pose::Windup: {   // the readable tell: arms flung up and wide, spine arched, jaw gaping
            const float shiver = std::sin(t_ * 38.0f) * 0.035f;
            T[J_SHO_L] = {2.5f + shiver, 0, -0.38f};
            T[J_SHO_R] = {2.6f - shiver, 0, 0.38f};
            T[J_ELB_L] = T[J_ELB_R] = {0.4f, 0, 0};
            T[J_SPINE] = {0.18f, 0, 0};
            T[J_CHEST] = {0.14f, 0, 0};
            T[J_NECK] = {0.12f, 0, 0};
            T[J_HEAD] = {0.3f + shiver, 0, 0.12f};
            T[J_JAW] = {-1.35f + shiver * 2.0f, 0, 0.05f};
            T[J_HIP_L] = {0.25f, 0, 0};
            T[J_KNE_L] = {-0.35f, 0, 0};
            T[J_HIP_R] = {-0.22f, 0, 0};
            break;
        }
        case Pose::Strike: {   // lunge and bite: arms clamp down, the jaw snaps shut
            T[J_SHO_L] = T[J_SHO_R] = {1.15f, 0, 0};
            T[J_SHO_L].z = 0.25f; T[J_SHO_R].z = -0.25f;
            T[J_ELB_L] = T[J_ELB_R] = {0.25f, 0, 0};
            T[J_SPINE] = {-0.5f, 0, 0};
            T[J_CHEST] = {-0.15f, 0, 0};
            T[J_HEAD] = {0.1f, 0, 0};
            T[J_JAW] = {-0.3f, 0, 0};
            T[J_HIP_L] = {0.55f, 0, 0};
            T[J_KNE_L] = {-0.45f, 0, 0};
            T[J_HIP_R] = {-0.35f, 0, 0};
            bob = -0.06f;
            break;
        }
        case Pose::Hurt:
        case Pose::Stagger: {
            T[J_SPINE] = {0.32f, 0, 0.1f};
            T[J_CHEST] = {0.15f, 0, 0};
            T[J_NECK] = {0.3f, 0, 0};
            T[J_HEAD] = {drowned ? 0.4f : 0.1f, 0, drowned ? -0.3f : 0.0f};
            T[J_JAW] = {-1.2f, 0, 0};
            T[J_SHO_L] = {0.5f, 0, -0.5f};
            T[J_SHO_R] = {0.4f, 0, 0.5f};
            T[J_HIP_R] = {-0.3f, 0, 0};
            T[J_KNE_R] = {-0.25f, 0, 0};
            break;
        }
        case Pose::Floored:
        case Pose::Dead: {   // on its back: arms flung out, knees fallen apart, head rolled to one side
            const float writhe = pose == Pose::Floored ? std::sin(t_ * 5.0f) : 0.0f;
            T[J_SPINE] = {0.05f, 0, 0.05f};
            T[J_CHEST] = {0.05f, 0, 0};
            T[J_NECK] = {0.1f, 0, 0};
            T[J_HEAD] = {0.2f, 0.7f, 0.2f};
            T[J_JAW] = {-1.3f, 0.1f, 0};
            T[J_SHO_L] = {0.6f + writhe * 0.3f, 0, -1.2f};
            T[J_SHO_R] = {0.4f - writhe * 0.2f, 0, 1.0f};
            T[J_ELB_L] = {0.8f, 0, 0};
            T[J_ELB_R] = {0.5f + writhe * 0.3f, 0, 0};
            T[J_HIP_L] = {0.15f, 0, -0.25f};
            T[J_HIP_R] = {0.25f + writhe * 0.15f, 0, 0.2f};
            T[J_KNE_L] = {-0.35f, 0, 0};
            T[J_KNE_R] = {-0.6f, 0, 0};
            break;
        }
        case Pose::Crawl:
        case Pose::CrawlWindup:
        case Pose::CrawlStrike: {   // prone: arms overhead are arms reaching along the floor
            phase_ += dt * std::max(speed, 0.2f) / 0.55f * 2 * kPi;
            float s = std::sin(phase_);
            T[J_SPINE] = {0.18f, 0, s * 0.08f};
            T[J_CHEST] = {0.12f, s * 0.1f, 0};
            T[J_NECK] = {0.35f, 0, 0};
            T[J_HEAD] = {0.45f, 0, 0.3f};
            T[J_SHO_L] = {2.6f + s * 0.45f, 0, -0.35f};
            T[J_SHO_R] = {2.6f - s * 0.45f, 0, 0.35f};
            T[J_ELB_L] = {0.3f + std::max(0.0f, s) * 0.9f, 0, 0};
            T[J_ELB_R] = {0.3f + std::max(0.0f, -s) * 0.9f, 0, 0};
            T[J_HIP_L] = T[J_HIP_R] = {-0.05f, 0, 0};
            T[J_KNE_L] = {-0.2f - std::max(0.0f, s) * 0.3f, 0, 0};
            T[J_KNE_R] = {-0.2f - std::max(0.0f, -s) * 0.3f, 0, 0};
            if (pose == Pose::CrawlWindup) {   // rears up on its arms, head back, jaw wide
                T[J_SPINE] = {0.45f, 0, 0};
                T[J_CHEST] = {0.3f, 0, 0};
                T[J_SHO_L] = T[J_SHO_R] = {1.9f, 0, 0};
                T[J_ELB_L] = T[J_ELB_R] = {0.1f, 0, 0};
                T[J_JAW] = {-1.4f, 0, 0};
            } else if (pose == Pose::CrawlStrike) {
                T[J_SPINE] = {0.1f, 0, 0};
                T[J_SHO_L] = T[J_SHO_R] = {2.9f, 0, 0};
                T[J_JAW] = {-0.3f, 0, 0};
            }
            break;
        }
        default: break;
    }
    if (!drowned && weapon_ == 1 && (pose == Pose::Idle || pose == Pose::Walk || pose == Pose::Run || pose == Pose::Hurt)) {
        // The shotgun carried at the low ready: the butt still in the shoulder, both hands on it, the
        // muzzle 40 degrees down ahead (--fit870).
        T[J_SHO_R] = {0.142f, 0.787f, 0.444f};
        T[J_ELB_R] = {1.850f, 0, 0};
        T[J_WRI_R] = {-0.850f, -1.859f, 0.876f};
        T[J_SHO_L] = {0.206f, 1.598f, 1.092f};
        T[J_ELB_L] = {0.000f, 0, 0};
        T[J_WRI_L] = {-0.316f, 0.037f, -0.313f};
        T[J_SPINE].y += -0.475f;   // turned, the gun side back
        T[J_CHEST].y += -0.368f;
    }
    // Both hands on the gun: the left one round the 870's fore-end, or over the right on the
    // pistol's grip (--fitgrips), hands() bending the arm to put it there; reloading, it goes
    // through the reload's steps from there (reload.hpp).
    want_support_ = nullptr;
    steps_ = false;
    if (!drowned && weapon_ == 1 && (pose == Pose::Aim || pose == Pose::Reload || pose == Pose::Idle || pose == Pose::Walk ||
                                     pose == Pose::Run || pose == Pose::Hurt))
        want_support_ = &grips::SHOTGUN_LEFT;
    if (!drowned && weapon_ == 0 && (pose == Pose::Aim || pose == Pose::Reload)) want_support_ = &grips::PISTOL_LEFT;
    if (!drowned && pose == Pose::Reload && reloading.on) steps_ = true;
    if (!drowned && limp > 0 && pose != Pose::Dead) {
        // Hurt: he favours the right leg (it barely bends and drags), dips as it takes his weight,
        // and when it's bad, his free hand holds his ribs.
        const float s = std::sin(phase_), moving = (pose == Pose::Walk || pose == Pose::Run) ? 1.0f : 0.0f;
        T[J_KNE_R].x *= 1.0f - 0.75f * limp * moving;
        T[J_HIP_R].x *= 1.0f - 0.35f * limp * moving;
        T[J_SPINE] = Vector3Add(T[J_SPINE], {-0.1f * limp, 0, 0.12f * limp * std::max(0.0f, -s) * moving});
        bob -= 0.035f * limp * std::max(0.0f, -s) * moving;
        if (limp > 0.7f && weapon_ == 0 && pose != Pose::Aim && pose != Pose::Reload && pose != Pose::Kick && pose != Pose::Dodge) {
            T[J_SHO_L] = {0.05f, -1.3f, 0.3f};
            T[J_ELB_L] = {1.75f, 0, 0};
        }
    }
    for (float s : {-1.0f, 1.0f}) {   // keep the soles flat
        int hp = s < 0 ? J_HIP_L : J_HIP_R, kn = s < 0 ? J_KNE_L : J_KNE_R;
        T[s < 0 ? J_ANK_L : J_ANK_R] = {-(T[hp].x + T[kn].x) * 0.9f, 0, 0};
    }
    if (grip_view >= 0) {   // debugging a grip: that hand on its gun, held out in front, clear of the body
        for (int j : {J_SHO_L, J_ELB_L, J_WRI_L, J_SHO_R, J_ELB_R, J_WRI_R}) T[j] = {};
        const bool left = r_gun_on_left();
        T[left ? J_SHO_L : J_SHO_R] = {1.4f, 0, left ? 0.35f : -0.35f};
        for (int k = 0; k < 15; ++k) T[(left ? J_THUMB1_L : J_THUMB1_R) + k] = view_grip().fingers[k];
        want_support_ = nullptr;
        steps_ = false;
        if (grip_view == 3) {   // the left hand reaching across onto the pistol (hands())
            T[J_SHO_L] = {1.3f, 0, 0.6f};
            T[J_ELB_L] = {0.5f, 0, 0};
            want_support_ = &grips::PISTOL_LEFT;
        }
    }
    if (want_support_)
        for (int k = 0; k < 15; ++k) T[J_THUMB1_L + k] = want_support_->fingers[k];
    if (steps_) {   // the fingers as the reload's steps have them, from one step's to the next
        reload::Step st[reload::MAX_STEPS];
        const int n = reload::steps(reloading.kind, reloading.from_grip, st);
        float f = 0;
        const int i = reload::segment(st, n, reloading.t, f);
        Vector3 a[15], b[15];
        reload_fingers(st[i].hand, a);
        reload_fingers(st[std::min(i + 1, n - 1)].hand, b);
        const float k = f * f * (3 - 2 * f);
        for (int j = 0; j < 15; ++j) T[J_THUMB1_L + j] = slerp_angles(a[j], b[j], k);
    }
}

const Grip& Character::view_grip() const {
    static const Grip* const g[6] = {&grips::PISTOL_RIGHT, &grips::SHOTGUN_RIGHT, &grips::SHOTGUN_LEFT, &grips::PISTOL_RIGHT,
                                     &grips::MAG_LEFT, &grips::SHELL_LEFT};
    return *g[std::clamp(grip_view, 0, 5)];
}

void Character::draw(const Material& m, bool shadow_caster) const {
    static unsigned shader = 0;
    static int skin_loc = -1, hidden_loc = -1;
    if (shader != m.shader.id) {
        shader = m.shader.id;
        skin_loc = GetShaderLocation(m.shader, "u_skin");
        hidden_loc = GetShaderLocation(m.shader, "u_hidden");
    }
    const int hidden = int(hidden_), none = 0;
    if (!skinned_.empty()) {
        const int on = 1, off = 0;
        SetShaderValue(m.shader, skin_loc, &on, SHADER_UNIFORM_INT);
        SetShaderValue(m.shader, hidden_loc, &hidden, SHADER_UNIFORM_INT);
        for (const auto& s : skinned_) DrawMesh(s.mesh, m, MatrixIdentity());
        SetShaderValue(m.shader, hidden_loc, &none, SHADER_UNIFORM_INT);
        SetShaderValue(m.shader, skin_loc, &off, SHADER_UNIFORM_INT);
    }
    // (Debugging a left-hand grip: the gun, built into the right hand's grip, moved to the left's.)
    const bool on_left = r_gun_on_left();
    const Matrix to_left = on_left ? MatrixMultiply(MatrixMultiply(MatrixInvert(weapon_ == 1 ? shotgun_hold() : pistol_hold()),
                                                                   view_grip().hold), W_[J_WRI_L])
                                   : MatrixIdentity();
    const Matrix hold = weapon_ == 1 ? shotgun_hold() : pistol_hold();
    for (const auto& r : rigid_) {
        if (severed(r.region) || (r.tag != 0 && r.tag != weapon_ + 1)) continue;
        if (grip_view >= 4 && r.tag != 0 && r.drive != 3) continue;   // (a magazine or a shell in the hand: just that)
        if (r.drive == 3) {   // what it's loaded with: in the gun, in the left hand, on its way in, or nowhere
            Matrix at = W_[r.joint];
            if (grip_view >= 4) at = to_left;
            else if (load_at_ == 1) continue;
            else if (load_at_ == 2)
                at = MatrixMultiply(MatrixMultiply(MatrixInvert(hold), (weapon_ == 1 ? grips::SHELL_LEFT : grips::MAG_LEFT).hold), W_[J_WRI_L]);
            else if (load_at_ == 3)
                at = MatrixMultiply(MatrixMultiply(MatrixMultiply(MatrixInvert(hold), cast::shell_in(load_along_)), hold), W_[r.joint]);
            DrawMesh(r.mesh, m, at);
            continue;
        }
        const float k = r.drive == 1 ? slide : r.drive == 2 ? pump : 0.0f;   // the slide or the fore-end, worked back
        const Matrix at = r.tag != 0 && on_left ? to_left : W_[r.joint];
        DrawMesh(r.mesh, m, k > 0 ? MatrixMultiply(MatrixTranslate(r.travel.x * k, r.travel.y * k, r.travel.z * k), at) : at);
    }
    for (const auto& d : dyn_) DrawMesh(d.mesh, m, MatrixIdentity());
    for (const auto& d : dangles_)
        if (!severed(d.region)) DrawMesh(d.mesh, m, MatrixIdentity());
    if (shadow_caster) return;   // hair lets light through: its shadow would black out the face
    if (!severed(R_HEAD))
        for (const auto& s : strands_) DrawMesh(s.mesh, m, MatrixIdentity());
    for (const auto& d : drips_)   // stretched by their fall
        DrawMesh(d.blood ? blood_drip_mesh_ : drip_mesh_, m,
                 MatrixMultiply(MatrixScale(1, 1 + 0.5f * std::fabs(d.v.y), 1), MatrixTranslate(d.p.x, d.p.y, d.p.z)));
}

void Character::unload() {
    for (auto& r : rigid_) UnloadMesh(r.mesh);
    for (auto& d : dyn_) UnloadMesh(d.mesh);
    for (auto& d : dangles_) UnloadMesh(d.mesh);
    for (auto& s : skinned_) UnloadMesh(s.mesh);
    for (auto& s : strands_) UnloadMesh(s.mesh);
    if (drip_mesh_.vertexCount) UnloadMesh(drip_mesh_);
    if (blood_drip_mesh_.vertexCount) UnloadMesh(blood_drip_mesh_);
    drip_mesh_ = blood_drip_mesh_ = {};
    hidden_ = 0;
    wounds_ = 0;
    drip_src_.clear();
    drips_.clear();
    skinned_.clear();
    strands_.clear();
    rigid_.clear();
    dyn_.clear();
    dangles_.clear();
}

}  // namespace dw
