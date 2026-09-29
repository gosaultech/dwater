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

namespace dw {
namespace {
constexpr int PARENT[J_COUNT] = {-1,      J_PELVIS, J_SPINE, J_CHEST, J_NECK,   J_HEAD,  J_CHEST, J_SHO_L, J_ELB_L,
                                 J_CHEST, J_SHO_R,  J_ELB_R, J_PELVIS, J_HIP_L, J_KNE_L, J_PELVIS, J_HIP_R, J_KNE_R,
                                 J_WRI_L, J_FING1_L, J_WRI_L, J_WRI_R, J_FING1_R, J_WRI_R};
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

void Character::add_rigid(int joint, int region, MeshData& d) {
    if (!d.count()) return;
    const Vector3 o = pattern_offset();
    for (size_t i = 0; i < d.count(); ++i) { d.tan[i * 4] += o.x; d.tan[i * 4 + 1] += o.y; d.tan[i * 4 + 2] += o.z; }
    rigid_.push_back({joint, region, upload(d)});
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
    pelvis_h_ = rest_[J_PELVIS].y;
    for (const auto& p : f.parts) add_skinned(p);
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
    m.boneCount = J_COUNT;
    m.boneMatrices = static_cast<Matrix*>(alloc(sizeof(Matrix) * J_COUNT));
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
    }
    for (int j = 0; j < J_COUNT; ++j) m.boneMatrices[j] = MatrixIdentity();
    UploadMesh(&m, false);
    skinned_.push_back({p.name, m});
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

void Character::animate(Pose pose, float speed, float dt, float aim_pitch) {
    t_ += dt;
    Vector3 T[J_COUNT]{};
    float bob = 0;
    targets(pose, speed, dt, aim_pitch, T, bob);
    const bool sharp = pose == Pose::Windup || pose == Pose::Strike || pose == Pose::Hurt || pose == Pose::Stagger ||
                       pose == Pose::CrawlStrike;
    const float k = smoothing(sharp ? 16.0f : 9.0f, dt);
    for (int j = 0; j < J_COUNT; ++j) ang_[j] = Vector3Lerp(ang_[j], T[j], k);
    bob_ = Lerp(bob_, bob, k);

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
    for (int j = 0; j < J_COUNT; ++j)   // skinning: rest-pose vertex -> joint space -> where the joint is now
        bones_[j] = MatrixMultiply(MatrixTranslate(-rest_[j].x, -rest_[j].y, -rest_[j].z), W_[j]);
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

void Character::add_drip_source(int joint, Vector3 off) {
    if (drip_mesh_.vertexCount == 0) {   // one small drop, shared by every drip this character sheds
        MeshData d;
        MeshBuilder(d).material(MAT_WATER).color(Color{120, 128, 130, 255}).ellipsoid({}, {0.003f, 0.0045f, 0.003f}, 8, 6);
        drip_mesh_ = upload(d);
    }
    drip_src_.push_back({joint, off, 0.3f + 1.5f * frand(rng_)});
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
        if ((src.next -= dt) > 0) continue;
        src.next = 0.35f + 1.6f * frand(rng_);   // a drop gathers, falls; the next one takes a while
        Vector3 at;
        if (src.joint >= 0) {
            at = Vector3Transform(src.off, W_[src.joint]);
        } else {
            const Strands& st = strands_.front();
            const size_t k = size_t(src.off.x);
            if (!st.live || (k + 1) * size_t(st.n) > st.p.size()) continue;
            at = st.p[(k + 1) * size_t(st.n) - 1];
        }
        if (drips_.size() < 48) drips_.push_back({at, {0, -0.25f, 0}});
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
    for (float s : {-1.0f, 1.0f}) {   // hands: fingers loosely curled toward the palm (palms face the body)
        const bool L = s < 0;
        const float in = L ? 1.0f : -1.0f;
        T[L ? J_FING1_L : J_FING1_R] = {0, 0, (drowned ? 0.5f : 0.25f) * in};
        T[L ? J_FING2_L : J_FING2_R] = {0, 0, (drowned ? 0.8f : 0.35f) * in};
        T[L ? J_THUMB_L : J_THUMB_R] = {0, 0, 0.15f * in};
    }
    if (!drowned) {   // the right hand grips the pistol
        T[J_FING1_R] = {0, 0, -1.25f};
        T[J_FING2_R] = {0, 0, -1.35f};
        T[J_THUMB_R] = {0, 0, -0.45f};
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
    switch (pose) {
        case Pose::Walk:
        case Pose::Run: {
            const bool run = pose == Pose::Run;
            phase_ += dt * std::max(speed, 0.4f) / (run ? 1.9f : 1.3f) * 2 * kPi;
            float s = std::sin(phase_), c = std::cos(phase_), amp = run ? 0.62f : 0.42f;
            T[J_HIP_L] = {s * amp, 0, -0.02f};
            T[J_HIP_R] = {-s * amp, 0, 0.02f};
            T[J_KNE_L] = {-0.1f - std::max(0.0f, c) * (run ? 1.3f : 0.8f), 0, 0};   // flex on the swing-through
            T[J_KNE_R] = {-0.1f - std::max(0.0f, -c) * (run ? 1.3f : 0.8f), 0, 0};
            T[J_SHO_L] = {-s * amp * 0.7f, 0, 0.12f};
            T[J_SHO_R] = {s * amp * 0.7f, 0, -0.12f};
            T[J_ELB_L] = {(run ? 1.3f : 0.3f) + std::max(0.0f, -s) * 0.3f, 0, 0};
            T[J_ELB_R] = {(run ? 1.3f : 0.3f) + std::max(0.0f, s) * 0.3f, 0, 0};
            T[J_SPINE] = {run ? -0.22f : -0.05f, s * 0.1f, 0};
            T[J_CHEST] = {0, -s * 0.06f, 0};
            T[J_PELVIS] = {0, -s * 0.08f, 0};
            bob = -std::fabs(s) * (run ? 0.045f : 0.022f);
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
        case Pose::Aim: {   // two-handed pistol: strong arm straight, support arm crossing in
            T[J_SHO_R] = {kPi / 2 + ap, 0, -0.14f};
            T[J_ELB_R] = {0.02f, 0, 0};
            T[J_SHO_L] = {kPi / 2 + ap - 0.12f, 0, 0.62f};
            T[J_ELB_L] = {0.35f, 0, 0};
            T[J_SPINE] = {-0.06f, 0.08f, 0};
            T[J_CHEST] = {-0.03f, 0.08f, 0};
            T[J_NECK] = {-0.1f, -0.1f, 0};
            T[J_HIP_L] = {0.22f, 0, -0.04f};
            T[J_KNE_L] = {-0.2f, 0, 0};
            T[J_HIP_R] = {-0.2f, 0, 0.06f};
            T[J_KNE_R] = {-0.1f, 0, 0};
            bob = -0.02f;
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
    for (float s : {-1.0f, 1.0f}) {   // keep the soles flat
        int hp = s < 0 ? J_HIP_L : J_HIP_R, kn = s < 0 ? J_KNE_L : J_KNE_R;
        T[s < 0 ? J_ANK_L : J_ANK_R] = {-(T[hp].x + T[kn].x) * 0.9f, 0, 0};
    }
}

void Character::draw(const Material& m, bool shadow_caster) const {
    static unsigned shader = 0;
    static int skin_loc = -1;
    if (shader != m.shader.id) { shader = m.shader.id; skin_loc = GetShaderLocation(m.shader, "u_skin"); }
    if (!skinned_.empty()) {
        const int on = 1, off = 0;
        SetShaderValue(m.shader, skin_loc, &on, SHADER_UNIFORM_INT);
        for (const auto& s : skinned_) DrawMesh(s.mesh, m, MatrixIdentity());
        SetShaderValue(m.shader, skin_loc, &off, SHADER_UNIFORM_INT);
    }
    for (const auto& r : rigid_) DrawMesh(r.mesh, m, W_[r.joint]);
    for (const auto& d : dyn_) DrawMesh(d.mesh, m, MatrixIdentity());
    for (const auto& d : dangles_) DrawMesh(d.mesh, m, MatrixIdentity());
    if (shadow_caster) return;   // hair lets light through: its shadow would black out the face
    for (const auto& s : strands_) DrawMesh(s.mesh, m, MatrixIdentity());
    for (const auto& d : drips_)   // stretched by their fall
        DrawMesh(drip_mesh_, m, MatrixMultiply(MatrixScale(1, 1 + 0.5f * std::fabs(d.v.y), 1), MatrixTranslate(d.p.x, d.p.y, d.p.z)));
}

void Character::unload() {
    for (auto& r : rigid_) UnloadMesh(r.mesh);
    for (auto& d : dyn_) UnloadMesh(d.mesh);
    for (auto& d : dangles_) UnloadMesh(d.mesh);
    for (auto& s : skinned_) UnloadMesh(s.mesh);
    for (auto& s : strands_) UnloadMesh(s.mesh);
    if (drip_mesh_.vertexCount) UnloadMesh(drip_mesh_);
    drip_mesh_ = {};
    drip_src_.clear();
    drips_.clear();
    skinned_.clear();
    strands_.clear();
    rigid_.clear();
    dyn_.clear();
    dangles_.clear();
}

}  // namespace dw
