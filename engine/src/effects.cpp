// damned_waters/engine/src/effects.cpp
// Purpose: see effects.hpp. Simple ballistic physics: gravity, a floor at y = 0, a little bounce
// and friction, then everything rests where it fell. The room's walls are the rectangle given by
// set_bounds (the hall is a corridor, so that's enough).
#include "effects.hpp"

#include <algorithm>
#include <cmath>

namespace dw {
namespace {
constexpr size_t MAX_DROPS = 500, MAX_SPLATS = 260, MAX_BRASS = 48, MAX_GIBS = 16, MAX_CHIPS = 80;
constexpr float G = 9.8f;
const Color BLOOD{88, 6, 6, 255}, BLOOD_DARK{48, 3, 3, 255}, BRASS{176, 136, 62, 255}, HULL{128, 22, 20, 255}, BONE{190, 174, 140, 255};
}  // namespace

float Effects::rnd() { rng_ ^= rng_ << 13; rng_ ^= rng_ >> 17; rng_ ^= rng_ << 5; return float(rng_ & 0xFFFF) / 65535.0f; }

namespace {
// A spatter: a flat disc with a ragged edge, lying in the floor plane and facing up; darker (and
// thicker-looking) in the middle.
void splat_disc(MeshData& d, float ph) {
    constexpr int N = 28;
    auto edge = [ph](float a) { return 1.0f + 0.22f * std::sin(a * 5 + ph) + 0.12f * std::sin(a * 11 + ph * 2.3f); };
    auto put = [&d](Vector3 p, Color c) {
        d.pos.insert(d.pos.end(), {p.x, p.y, p.z});
        d.nrm.insert(d.nrm.end(), {0.0f, 1.0f, 0.0f});
        d.uv.insert(d.uv.end(), {float(MAT_BLOOD), 1.0f});
        d.tan.insert(d.tan.end(), {p.x * 3, 0.0f, p.z * 3, 0.0f});
        d.col.insert(d.col.end(), {c.r, c.g, c.b, c.a});
    };
    for (int i = 0; i < N; ++i) {
        const float a0 = 2 * PI * float(i) / N, a1 = 2 * PI * float(i + 1) / N;
        put({0, 0, 0}, BLOOD_DARK);   // counter-clockwise from above: centre, the next edge point, this one
        put({std::cos(a1) * edge(a1), 0, std::sin(a1) * edge(a1)}, BLOOD);
        put({std::cos(a0) * edge(a0), 0, std::sin(a0) * edge(a0)}, BLOOD);
    }
}

// The muzzle flash, down -Z: a white-hot tongue along the barrel's line and a star of thin
// flames round it, the way a flash looks in a photograph at 1/1000 s. Drawn additively.
void flash_star(MeshData& d, float sz, int spikes, float ph) {
    MeshBuilder f(d);
    f.material(MAT_LAMP).color(Color{255, 236, 190, 255}).ellipsoid({0, 0, -0.055f * sz}, {0.016f * sz, 0.016f * sz, 0.06f * sz}, 10, 6);
    f.color(Color{255, 190, 110, 255}).ellipsoid({0, 0, -0.02f * sz}, {0.03f * sz, 0.03f * sz, 0.018f * sz}, 10, 5);
    for (int i = 0; i < spikes; ++i) {
        const float a = ph + 2 * PI * float(i) / float(spikes), len = (0.045f + 0.035f * std::fabs(std::sin(a * 3.7f + ph))) * sz;
        const Vector3 dir = Vector3Normalize({std::cos(a), std::sin(a), -0.7f});
        const Matrix r = QuaternionToMatrix(QuaternionFromVector3ToVector3({0, 1, 0}, dir));
        MeshBuilder sp(d);
        sp.transform(MatrixMultiply(r, MatrixTranslate(dir.x * len * 0.8f, dir.y * len * 0.8f, dir.z * len * 0.8f)));
        sp.material(MAT_LAMP).color(Color{255, 150, 60, 255}).ellipsoid({}, {0.0055f * sz, len, 0.0055f * sz}, 6, 5);
    }
}
}  // namespace

void Effects::init() {
    MeshData d;
    MeshBuilder(d).material(MAT_BLOOD).color(BLOOD).ellipsoid({}, {1, 1, 1}, 6, 4);
    drop_mesh_ = upload(d);
    d = {};
    MeshBuilder(d).material(MAT_BONE).color(BONE).box({}, {0.006f, 0.003f, 0.004f}, 0.6f, 6, 4);
    chip_mesh_ = upload(d);
    d = {};   // a spent 9 mm case, along y
    MeshBuilder(d).material(MAT_METAL).color(BRASS).tube({0, -0.0095f, 0}, {0, 0.0095f, 0}, 0.0048f, 0.0048f, 8);
    casing_mesh_ = upload(d);
    d = {};   // a spent 12-gauge shell: red hull, brass head
    MeshBuilder s(d);
    s.material(MAT_NYLON).color(HULL).tube({0, -0.03f, 0}, {0, 0.035f, 0}, 0.0105f, 0.0105f, 10);
    s.material(MAT_METAL).color(BRASS).tube({0, -0.035f, 0}, {0, -0.02f, 0}, 0.011f, 0.011f, 10);
    shell_mesh_ = upload(d);
    for (int k = 0; k < 2; ++k) {   // the flash: the pistol's small, the shotgun's big
        d = {};
        flash_star(d, k ? 1.9f : 1.0f, k ? 7 : 5, float(k) * 0.9f);
        flash_mesh_[k] = upload(d);
    }
    for (int k = 0; k < 3; ++k) {   // spatters: three shapes, turned and scaled as they land
        d = {};
        splat_disc(d, float(k) * 1.7f);
        splat_mesh_[k] = upload(d);
    }
}

void Effects::shutdown() {
    clear();
    for (Mesh* m : {&drop_mesh_, &chip_mesh_, &casing_mesh_, &shell_mesh_, &flash_mesh_[0], &flash_mesh_[1], &splat_mesh_[0], &splat_mesh_[1], &splat_mesh_[2]})
        if (m->vertexCount) { UnloadMesh(*m); *m = {}; }
}

void Effects::clear() {
    for (auto& g : gibs_) UnloadMesh(g.mesh);
    gibs_.clear();
    drops_.clear();
    splats_.clear();
    brass_.clear();
    chips_.clear();
    flash_t_ = 0;
}

void Effects::blood_spray(Vector3 at, Vector3 dir, int count, float speed) {
    for (int i = 0; i < count && drops_.size() < MAX_DROPS; ++i) {
        const Vector3 j{rnd() - 0.5f, rnd() * 0.8f - 0.2f, rnd() - 0.5f};
        const Vector3 v = Vector3Scale(Vector3Normalize(Vector3Add(dir, Vector3Scale(j, 1.1f))), speed * (0.35f + 0.8f * rnd()));
        drops_.push_back({at, v, 0.003f + 0.005f * rnd()});
    }
}

void Effects::blood_burst(Vector3 at, int count) {
    for (int i = 0; i < count && drops_.size() < MAX_DROPS; ++i) {
        const Vector3 dir = Vector3Normalize({rnd() - 0.5f, rnd() * 0.9f - 0.1f, rnd() - 0.5f});
        drops_.push_back({at, Vector3Scale(dir, 1.2f + 3.2f * rnd()), 0.004f + 0.007f * rnd()});
    }
}

void Effects::chips(Vector3 at, int count) {
    for (int i = 0; i < count; ++i) {
        const Vector3 dir = Vector3Normalize({rnd() - 0.5f, rnd() * 0.8f, rnd() - 0.5f});
        if (chips_.size() >= MAX_CHIPS) chips_.erase(chips_.begin());
        chips_.push_back({at, Vector3Scale(dir, 1.0f + 2.5f * rnd()), 0.6f + rnd()});   // r: size
    }
}

void Effects::casing(Vector3 at, Vector3 right, bool shell) {
    if (brass_.size() >= MAX_BRASS) brass_.erase(brass_.begin());
    const Vector3 v = shell ? Vector3{(rnd() - 0.5f) * 0.4f, -0.3f, (rnd() - 0.5f) * 0.4f}   // shells drop out of the breech
                            : Vector3Add(Vector3Scale(right, 1.4f + 0.6f * rnd()), {0, 1.8f + 0.6f * rnd(), 0});
    brass_.push_back({at, v, Vector3Normalize({rnd() - 0.5f, rnd() - 0.5f, rnd() - 0.5f}), 0, 12 + 10 * rnd(), rnd() * 2 * PI, shell, false});
}

void Effects::gib(const MeshData& piece, Vector3 centre, Vector3 push) {
    if (piece.count() < 3) return;
    if (gibs_.size() >= MAX_GIBS) { UnloadMesh(gibs_.front().mesh); gibs_.erase(gibs_.begin()); }
    Gib g;
    g.mesh = upload(piece);
    g.p = centre;
    g.v = Vector3Add(push, {0, 1.0f + rnd(), 0});
    g.axis = Vector3Normalize({rnd() - 0.5f, rnd() - 0.5f, rnd() - 0.5f});
    g.angle = 0;
    g.spin = 5 + 6 * rnd();
    g.rest_h = 0;
    g.spun = MatrixIdentity();
    g.rest = false;
    gibs_.push_back(g);
}

void Effects::pool(Vector3 at, float radius) {
    if (splats_.size() >= MAX_SPLATS) splats_.erase(splats_.begin());
    splats_.push_back({{at.x, 0, at.z}, 0.05f, rnd() * 2 * PI, int(rnd() * 2.99f), radius});
}

void Effects::flash(Vector3 at, Vector3 dir, bool shotgun) {
    flash_at_ = at;
    flash_dir_ = Vector3Normalize(dir);
    flash_shotgun_ = shotgun;
    flash_len_ = flash_t_ = shotgun ? 0.07f : 0.05f;
    flash_power_ = shotgun ? 7.0f : 4.5f;
    flash_roll_ = rnd() * 2 * PI;
}

void Effects::update(float dt) {
    flash_t_ = std::max(0.0f, flash_t_ - dt);
    for (auto& d : drops_) {
        d.v.y -= G * dt;
        d.p = inside(Vector3Add(d.p, Vector3Scale(d.v, dt)));
    }
    for (const auto& d : drops_)   // what reaches the floor stays as a spatter
        if (d.p.y <= 0.004f) {
            if (splats_.size() >= MAX_SPLATS) splats_.erase(splats_.begin());
            splats_.push_back({{d.p.x, 0, d.p.z}, d.r * (2.5f + 3.0f * rnd()), rnd() * 2 * PI, int(rnd() * 2.99f), 0});
        }
    drops_.erase(std::remove_if(drops_.begin(), drops_.end(), [](const Drop& d) { return d.p.y <= 0.004f; }), drops_.end());
    for (auto& s : splats_)
        if (s.grow_to > s.r) s.r = std::min(s.grow_to, s.r + dt * 0.035f);   // pools creep outward
    for (auto& c : chips_) {
        if (c.p.y <= 0.003f && std::fabs(c.v.y) < 0.01f) continue;
        c.v.y -= G * dt;
        c.p = inside(Vector3Add(c.p, Vector3Scale(c.v, dt)));
        if (c.p.y < 0.003f) { c.p.y = 0.003f; c.v = {0, 0, 0}; }
    }
    for (auto& b : brass_) {
        if (b.rest) continue;
        b.v.y -= G * dt;
        b.p = inside(Vector3Add(b.p, Vector3Scale(b.v, dt)));
        b.angle += b.spin * dt;
        const float h = b.shell ? 0.0105f : 0.0048f;   // lying on its side
        if (b.p.y < h) {
            b.p.y = h;
            b.v = {b.v.x * 0.45f, -b.v.y * 0.35f, b.v.z * 0.45f};
            b.spin *= 0.5f;
            if (std::fabs(b.v.y) < 0.25f) { b.rest = true; b.axis = {0, 0, 1}; b.angle = PI / 2; }   // tink, tink... still
        }
    }
    for (auto& g : gibs_) {
        if (g.rest) continue;
        g.v.y -= G * dt;
        g.p = inside(Vector3Add(g.p, Vector3Scale(g.v, dt)));
        g.angle += g.spin * dt;
        g.spun = MatrixRotate(g.axis, g.angle);
        float low = 1e9f;   // the lowest point of the piece as it's turned now
        for (int i = 0; i < g.mesh.vertexCount; i += 7)
            low = std::min(low, Vector3Transform({g.mesh.vertices[i * 3], g.mesh.vertices[i * 3 + 1], g.mesh.vertices[i * 3 + 2]}, g.spun).y);
        if (g.p.y + low < 0.002f) {
            g.p.y = 0.002f - low;
            if (g.v.y < 0) g.v.y = -g.v.y * 0.25f;
            g.v.x *= 0.55f;
            g.v.z *= 0.55f;
            g.spin *= 0.45f;
            if (Vector3Length(g.v) < 0.35f && g.spin < 1.2f) { g.rest = true; g.v = {}; }
        }
    }
}

void Effects::draw(const Material& m) const {
    for (const auto& s : splats_)
        DrawMesh(splat_mesh_[s.shape], m, MatrixMultiply(MatrixMultiply(MatrixScale(s.r, 1, s.r), MatrixRotateY(s.yaw)),
                                                        MatrixTranslate(s.p.x, 0.0035f + s.r * 0.004f, s.p.z)));
    for (const auto& d : drops_) {
        const float stretch = 1 + 0.35f * Vector3Length(d.v);
        DrawMesh(drop_mesh_, m, MatrixMultiply(MatrixScale(d.r, d.r * stretch, d.r), MatrixTranslate(d.p.x, d.p.y, d.p.z)));
    }
    for (const auto& c : chips_)
        DrawMesh(chip_mesh_, m, MatrixMultiply(MatrixMultiply(MatrixScale(c.r, c.r, c.r), MatrixRotateY(c.p.x * 40)),
                                               MatrixTranslate(c.p.x, c.p.y, c.p.z)));
    for (const auto& b : brass_)
        DrawMesh(b.shell ? shell_mesh_ : casing_mesh_, m,
                 MatrixMultiply(MatrixMultiply(MatrixRotate(b.axis, b.angle), MatrixRotateY(b.yaw)), MatrixTranslate(b.p.x, b.p.y, b.p.z)));
    for (const auto& g : gibs_) DrawMesh(g.mesh, m, MatrixMultiply(g.spun, MatrixTranslate(g.p.x, g.p.y, g.p.z)));
}

void Effects::draw_flash(const Material& m) const {
    if (flash_t_ > 0) {   // flame along the barrel: -Z of the flash mesh onto the barrel's direction
        const Vector3 f = Vector3Negate(flash_dir_);
        const Vector3 x = Vector3Normalize(Vector3CrossProduct({0, 1, 0}, f)), y = Vector3CrossProduct(f, x);
        Matrix r = MatrixIdentity();
        r.m0 = x.x; r.m1 = x.y; r.m2 = x.z;
        r.m4 = y.x; r.m5 = y.y; r.m6 = y.z;
        r.m8 = f.x; r.m9 = f.y; r.m10 = f.z;
        const float k = 0.7f + 0.3f * flash_t_ / flash_len_;
        DrawMesh(flash_mesh_[flash_shotgun_ ? 1 : 0], m,
                 MatrixMultiply(MatrixMultiply(MatrixMultiply(MatrixScale(k, k, k), MatrixRotateZ(flash_roll_)), r),
                                MatrixTranslate(flash_at_.x, flash_at_.y, flash_at_.z)));
    }
}

}  // namespace dw
