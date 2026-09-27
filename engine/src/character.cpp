// damned_waters/engine/src/character.cpp
// Purpose: the cast, built in C++ at startup (no external model files).
//   Survivor   : an ordinary man in a waxed jacket; sculpted face, real eyes, hair.
//   Verdronkene: stylised-grotesque drowned: oversized skull under the coroner's
//                sheet (blood where the mouth drags the cloth in), neck jutting
//                forward, arms too long, huge rotted hands, a gas-bloated belly
//                split open, a ragged waterlogged coat, leeches.
#include "dw/character.hpp"

#include <algorithm>
#include <cmath>

#include "dw/core.hpp"

namespace dw {
namespace {
constexpr int PARENT[J_COUNT] = {-1, J_PELVIS, J_SPINE, J_CHEST, J_NECK, J_CHEST, J_SHO_L, J_ELB_L, J_CHEST, J_SHO_R,
                                 J_ELB_R, J_PELVIS, J_HIP_L, J_KNE_L, J_PELVIS, J_HIP_R, J_KNE_R};

struct Feature { Vector3 dir; float sigma, amp; };
Bump features(std::vector<Feature> f) {
    for (auto& x : f) x.dir = Vector3Normalize(x.dir);
    return [f](Vector3 d) {
        float s = 0;
        for (const auto& x : f) {
            float q = Vector3LengthSqr(Vector3Subtract(d, x.dir));
            s += x.amp * std::exp(-q / (2 * x.sigma * x.sigma));
        }
        return s;
    };
}
Vector3 on_ellipsoid(Vector3 c, Vector3 r, Vector3 dir, float inset) {
    Vector3 d = Vector3Normalize(dir);
    return {c.x + d.x * (r.x - inset), c.y + d.y * (r.y - inset), c.z + d.z * (r.z - inset)};
}
const Color SKIN{198, 150, 122, 255}, HAIR{36, 27, 20, 255}, JACKET{74, 80, 52, 255}, DENIM{44, 56, 86, 255},
    BOOT{58, 40, 28, 255}, METAL{30, 30, 32, 255};
const Color DSKIN{120, 132, 108, 255}, SHEET{178, 170, 150, 255}, COAT{38, 40, 42, 255}, TROUSER{32, 32, 36, 255},
    FLESH{120, 26, 24, 255}, DRIED{66, 14, 12, 255}, LEECH{30, 22, 16, 255}, ROT{20, 16, 14, 255};

// Hand hanging from the wrist: palm faces the body, fingers point down (-Y), thumb forward (-Z).
void hand(MeshData& d, float side, Color skin, int mat, float scale, float finger_len, bool rotted) {
    MeshBuilder b(d);
    b.material(mat).color(skin);
    b.ellipsoid({0, -0.052f * scale, -0.004f}, {0.021f * scale, 0.05f * scale, 0.043f * scale}, 14, 10);
    for (int f = 0; f < 4; ++f) {
        float zf = (-0.03f + f * 0.019f) * scale, L = finger_len * (f == 3 ? 0.8f : (f == 1 ? 1.08f : 1.0f));
        Vector3 a{0, -0.092f * scale, zf}, m{-0.004f * side, -0.092f * scale - L * 0.55f, zf - 0.006f},
            t{-0.009f * side, -0.092f * scale - L, zf - 0.018f};
        b.chain({a, m, t}, {0.0095f * scale, 0.0085f * scale, 0.0068f * scale}, 7);
        if (rotted) {
            MeshBuilder r(d);
            r.material(MAT_ROT).color(ROT).ellipsoid(t, Vector3Scale(Vector3{0.009f, 0.013f, 0.009f}, scale), 8, 6);
        }
    }
    b.chain({{-0.01f * side, -0.042f * scale, -0.034f * scale}, {-0.017f * side, -0.074f * scale, -0.054f * scale},
             {-0.021f * side, -0.1f * scale, -0.062f * scale}},
            {0.011f * scale, 0.0095f * scale, 0.0078f * scale}, 7);
}

std::vector<std::pair<int, Vector3>> arm_points(float side, Vector3 clavicle) {
    return {{J_CHEST, {clavicle.x * side, clavicle.y, clavicle.z}},
            {side < 0 ? J_SHO_L : J_SHO_R, {}}, {side < 0 ? J_ELB_L : J_ELB_R, {}}, {side < 0 ? J_WRI_L : J_WRI_R, {}}};
}
std::vector<std::pair<int, Vector3>> leg_points(float side) {
    return {{J_PELVIS, {0.065f * side, -0.02f, 0}}, {side < 0 ? J_HIP_L : J_HIP_R, {}},
            {side < 0 ? J_KNE_L : J_KNE_R, {}}, {side < 0 ? J_ANK_L : J_ANK_R, {}}};
}
}  // namespace

void Character::add_sweep(Sweep s, std::vector<std::pair<int, Vector3>> pts) {
    Dyn d{std::move(s), std::move(pts), {}};
    d.mesh = upload(d.sweep.data, true);   // real positions arrive on the first animate()
    dyn_.push_back(std::move(d));
}

Character build_survivor() {
    Character c;
    c.kind = Kind::Survivor;
    c.pelvis_h_ = 0.95f;
    Vector3* o = c.off_;
    o[J_SPINE] = {0, 0.1f, 0};      o[J_CHEST] = {0, 0.2f, 0};      o[J_NECK] = {0, 0.24f, 0};
    o[J_HEAD] = {0, 0.09f, -0.005f};
    for (float s : {-1.0f, 1.0f}) {
        int sh = s < 0 ? J_SHO_L : J_SHO_R, el = s < 0 ? J_ELB_L : J_ELB_R, wr = s < 0 ? J_WRI_L : J_WRI_R;
        int hp = s < 0 ? J_HIP_L : J_HIP_R, kn = s < 0 ? J_KNE_L : J_KNE_R, an = s < 0 ? J_ANK_L : J_ANK_R;
        o[sh] = {0.19f * s, 0.19f, 0};   o[el] = {0.035f * s, -0.28f, 0};   o[wr] = {0.02f * s, -0.25f, -0.02f};
        o[hp] = {0.095f * s, -0.03f, 0}; o[kn] = {0, -0.42f, 0.01f};        o[an] = {0, -0.41f, -0.005f};
    }
    // Torso: jacket from below the belt to the collar; bare neck at the top.
    c.add_sweep(Sweep(26, 16, Profile{{{0.0f, 0.172f, 0.126f, 0}, {0.15f, 0.168f, 0.12f, 0}, {0.35f, 0.155f, 0.112f, 0.005f},
                                       {0.55f, 0.17f, 0.12f, 0.01f}, {0.7f, 0.18f, 0.122f, 0.012f}, {0.8f, 0.17f, 0.112f, 0.006f},
                                       {0.87f, 0.128f, 0.095f, 0}, {0.92f, 0.074f, 0.07f, 0}, {1.0f, 0.058f, 0.058f, 0}}},
                      MAT_CLOTH, JACKET, 0.8f).tail(0.935f, MAT_SKIN, SKIN),
                {{J_PELVIS, {0, -0.1f, 0}}, {J_PELVIS, {}}, {J_SPINE, {}}, {J_CHEST, {}}, {J_CHEST, {0, 0.19f, 0}}, {J_NECK, {0, 0.07f, 0}}});
    for (float s : {-1.0f, 1.0f}) {   // sleeves: deltoid, bicep, narrow elbow, forearm swell, cuff
        c.add_sweep(Sweep(22, 12, Profile{{{0.0f, 0.052f, 0.05f, 0}, {0.18f, 0.063f, 0.064f, 0}, {0.4f, 0.055f, 0.057f, 0},
                                           {0.58f, 0.047f, 0.048f, 0}, {0.7f, 0.05f, 0.047f, 0}, {0.95f, 0.043f, 0.041f, 0},
                                           {1.0f, 0.036f, 0.032f, 0}}},
                          MAT_CLOTH, JACKET, 0.62f), arm_points(s, {0.1f, 0.18f, 0}));
        c.add_sweep(Sweep(24, 12, Profile{{{0.0f, 0.1f, 0.1f, 0}, {0.12f, 0.092f, 0.095f, 0}, {0.3f, 0.08f, 0.083f, 0},
                                           {0.53f, 0.054f, 0.057f, 0}, {0.66f, 0.056f, 0.062f, -0.006f}, {0.86f, 0.044f, 0.046f, 0},
                                           {1.0f, 0.043f, 0.045f, 0}}},
                          MAT_DENIM, DENIM, 0.88f), leg_points(s));
    }
    MeshData d;
    MeshBuilder(d).material(MAT_DENIM).color(DENIM).ellipsoid({0, -0.03f, 0}, {0.158f, 0.1f, 0.112f}, 18, 10);
    c.add_rigid(J_PELVIS, d);
    d = {};   // collar band
    MeshBuilder(d).material(MAT_CLOTH).color(Color{60, 64, 42, 255}).drape({0, 0.225f, 0.01f}, {0.078f, 0.072f}, {0.104f, 0.094f}, 0.06f, 3, 24, 0, 0);
    c.add_rigid(J_CHEST, d);
    // Head: sculpted skull, eyes that catch light, brows, lips, ears, hair.
    const Vector3 hc{0, 0.105f, 0.005f}, hr{0.082f, 0.108f, 0.098f};
    d = {};
    MeshBuilder(d).material(MAT_SKIN).color(SKIN).ellipsoid(hc, hr, 36, 24, features({
        {{0, -0.05f, -1}, 0.12f, 0.028f}, {{0, 0.24f, -0.97f}, 0.22f, 0.01f}, {{0.34f, 0.1f, -0.93f}, 0.1f, -0.013f},
        {{-0.34f, 0.1f, -0.93f}, 0.1f, -0.013f}, {{0.55f, -0.1f, -0.8f}, 0.2f, 0.008f}, {{-0.55f, -0.1f, -0.8f}, 0.2f, 0.008f},
        {{0, -0.31f, -0.94f}, 0.07f, 0.006f}, {{0, -0.39f, -0.93f}, 0.07f, 0.008f}, {{0, -0.62f, -0.82f}, 0.16f, 0.014f},
        {{0.75f, -0.45f, -0.5f}, 0.2f, 0.006f}, {{-0.75f, -0.45f, -0.5f}, 0.2f, 0.006f}, {{0, 0.2f, 0.95f}, 0.5f, 0.008f}}));
    for (float s : {-1.0f, 1.0f}) {
        MeshBuilder b(d);
        b.material(MAT_EYE).color(Color{218, 210, 198, 255}).ellipsoid({0.028f * s, 0.116f, -0.071f}, {0.0118f, 0.0118f, 0.0118f}, 14, 10);
        b.material(MAT_IRIS).color(Color{62, 48, 34, 255}).ellipsoid({0.028f * s, 0.116f, -0.0815f}, {0.0068f, 0.0068f, 0.0026f}, 12, 6);
        b.material(MAT_HAIR).color(HAIR).ellipsoid({0.031f * s, 0.139f, -0.085f}, {0.02f, 0.0045f, 0.008f}, 10, 6);
        b.material(MAT_SKIN).color(SKIN).ellipsoid({0.083f * s, 0.103f, 0.005f}, {0.012f, 0.027f, 0.018f}, 10, 8);
    }
    MeshBuilder(d).material(MAT_SKIN).color(Color{150, 88, 80, 255}).ellipsoid({0, 0.067f, -0.093f}, {0.021f, 0.0065f, 0.008f}, 12, 6);
    {   // hair: a cap down to an uneven hairline, clumped
        const Vector3 c0{0, 0.114f, 0.006f}, r0{0.088f, 0.118f, 0.104f};
        const int rows = 12, cols = 32;
        Grid g(rows + 1, std::vector<Vector3>(cols));
        for (int j = 0; j < cols; ++j) {
            float th = 2 * PI * j / cols;   // 0 = front
            float thr = -0.1f + 0.56f * std::cos(th) + 0.06f * std::sin(th * 3 + 0.5f) + 0.025f * std::sin(th * 11 + 1.3f);
            float phi_max = PI / 2 - std::asin(std::clamp(thr, -0.95f, 0.95f));
            for (int i = 0; i <= rows; ++i) {
                float phi = phi_max * i / rows;
                Vector3 dd{std::sin(phi) * std::sin(th), std::cos(phi), -std::sin(phi) * std::cos(th)};
                float clump = 0.003f + 0.004f * (0.5f + 0.5f * std::sin(th * 17 + phi * 5) * std::sin(phi * 13));
                g[i][j] = {c0.x + dd.x * (r0.x + clump), c0.y + dd.y * (r0.y + clump), c0.z + dd.z * (r0.z + clump)};
            }
        }
        MeshBuilder(d).material(MAT_HAIR).color(HAIR).grid(g);
    }
    c.add_rigid(J_HEAD, d);
    for (float s : {-1.0f, 1.0f}) {
        d = {};
        hand(d, s, SKIN, MAT_SKIN, 1.0f, 0.075f, false);
        if (s > 0) {   // the pistol, held in the right hand
            MeshBuilder m(d);
            m.material(MAT_METAL).color(METAL).tube({0, -0.075f, -0.032f}, {0, -0.205f, -0.032f}, 0.015f, 0.014f, 6);
            m.tube({0, -0.08f, -0.03f}, {0, -0.066f, 0.03f}, 0.012f, 0.012f, 6);
        }
        c.add_rigid(s < 0 ? J_WRI_L : J_WRI_R, d);
        d = {};
        MeshBuilder b(d);
        b.material(MAT_LEATHER).color(BOOT).ellipsoid({0, -0.045f, -0.045f}, {0.05f, 0.047f, 0.12f}, 16, 10);
        b.color(Color{28, 20, 14, 255}).ellipsoid({0, -0.083f, -0.045f}, {0.053f, 0.012f, 0.123f}, 16, 6);
        c.add_rigid(s < 0 ? J_ANK_L : J_ANK_R, d);
    }
    return c;
}

Character build_drowned() {
    Character c;
    c.kind = Kind::Drowned;
    c.pelvis_h_ = 1.0f;
    Vector3* o = c.off_;
    o[J_SPINE] = {0, 0.12f, 0};  o[J_CHEST] = {0, 0.24f, 0};  o[J_NECK] = {0, 0.22f, -0.03f};  o[J_HEAD] = {0, 0.08f, -0.05f};
    for (float s : {-1.0f, 1.0f}) {   // arms far too long: the hands hang past the knees
        int sh = s < 0 ? J_SHO_L : J_SHO_R, el = s < 0 ? J_ELB_L : J_ELB_R, wr = s < 0 ? J_WRI_L : J_WRI_R;
        int hp = s < 0 ? J_HIP_L : J_HIP_R, kn = s < 0 ? J_KNE_L : J_KNE_R, an = s < 0 ? J_ANK_L : J_ANK_R;
        o[sh] = {0.23f * s, 0.2f, 0.02f}; o[el] = {0.05f * s, -0.36f, 0};  o[wr] = {0.02f * s, -0.35f, -0.01f};
        o[hp] = {0.11f * s, -0.03f, 0};   o[kn] = {0, -0.44f, 0.01f};      o[an] = {0, -0.43f, 0};
    }
    // Bloated torso in a waterlogged coat: the belly bulges FORWARD; bare neck on top.
    c.add_sweep(Sweep(28, 18, Profile{{{0.0f, 0.2f, 0.16f, 0}, {0.18f, 0.22f, 0.22f, 0.03f}, {0.34f, 0.235f, 0.25f, 0.055f},
                                       {0.55f, 0.22f, 0.19f, 0.02f}, {0.72f, 0.222f, 0.16f, 0}, {0.86f, 0.2f, 0.14f, 0},
                                       {0.93f, 0.1f, 0.09f, 0}, {1.0f, 0.08f, 0.08f, 0}}},
                      MAT_WOOL, COAT, 0.78f).tail(0.9f, MAT_DROWNED, DSKIN),
                {{J_PELVIS, {0, -0.12f, 0}}, {J_PELVIS, {}}, {J_SPINE, {}}, {J_CHEST, {}}, {J_CHEST, {0, 0.2f, 0}}, {J_NECK, {0, 0.07f, 0}}});
    for (float s : {-1.0f, 1.0f}) {
        c.add_sweep(Sweep(26, 12, Profile{{{0.0f, 0.075f, 0.07f, 0}, {0.2f, 0.08f, 0.08f, 0}, {0.45f, 0.068f, 0.07f, 0},
                                           {0.6f, 0.06f, 0.06f, 0}, {0.63f, 0.058f, 0.058f, 0}, {0.78f, 0.055f, 0.053f, 0},
                                           {1.0f, 0.045f, 0.04f, 0}}},
                          MAT_WOOL, COAT, 0.8f).tail(0.62f, MAT_DROWNED, DSKIN), arm_points(s, {0.11f, 0.18f, 0}));
        c.add_sweep(Sweep(24, 12, Profile{{{0.0f, 0.11f, 0.11f, 0}, {0.3f, 0.09f, 0.095f, 0}, {0.53f, 0.065f, 0.068f, 0},
                                           {0.66f, 0.07f, 0.075f, -0.006f}, {1.0f, 0.052f, 0.055f, 0}}},
                          MAT_WOOL, TROUSER, 0.93f), leg_points(s));
    }
    MeshData d;   // ragged coat skirt, hanging to the knees
    MeshBuilder(d).material(MAT_WOOL).color(COAT).drape({0, -0.02f, 0.01f}, {0.225f, 0.22f}, {0.33f, 0.32f}, 0.58f, 10, 44, 7, 0.08f,
        [](float th) { return 0.84f + 0.1f * std::sin(th * 13) + 0.06f * std::sin(th * 29 + 1.0f); }, 3);
    c.add_rigid(J_PELVIS, d);
    d = {};   // the belly, split open by gas; guts slipping out
    {
        MeshBuilder b(d);
        b.material(MAT_FLESH).color(FLESH).ellipsoid({0.015f, -0.01f, -0.28f}, {0.03f, 0.085f, 0.018f}, 14, 10);
        b.material(MAT_VOID).color(BLACK).ellipsoid({0.015f, -0.01f, -0.293f}, {0.014f, 0.07f, 0.011f}, 10, 8);
        b.material(MAT_FLESH).color(Color{150, 72, 68, 255});
        b.chain({{0.005f, -0.06f, -0.292f}, {0.02f, -0.13f, -0.305f}, {0.0f, -0.21f, -0.312f}, {0.018f, -0.3f, -0.305f},
                 {0.004f, -0.39f, -0.3f}}, {0.013f, 0.012f, 0.011f, 0.01f, 0.008f}, 8);
        b.chain({{0.028f, -0.07f, -0.29f}, {0.04f, -0.14f, -0.3f}, {0.03f, -0.2f, -0.306f}, {0.042f, -0.26f, -0.3f}},
                {0.011f, 0.01f, 0.009f, 0.007f}, 8);
        b.material(MAT_LEECH).color(LEECH).ellipsoid({-0.12f, 0.03f, -0.25f}, {0.014f, 0.036f, 0.013f}, 10, 6);
    }
    c.add_rigid(J_SPINE, d);
    d = {};
    MeshBuilder(d).material(MAT_LEECH).color(LEECH).ellipsoid({0.05f, 0.04f, -0.055f}, {0.013f, 0.034f, 0.013f}, 10, 6);
    c.add_rigid(J_NECK, d);
    // Oversized skull under the sheet: sunken sockets, the mouth dragging the cloth inward.
    const Vector3 hc{0, 0.13f, -0.03f}, hr{0.118f, 0.14f, 0.13f};
    d = {};
    {
        MeshBuilder b(d);
        b.material(MAT_SHEET).color(SHEET).ellipsoid(hc, hr, 40, 26, features({
            {{0, -0.05f, -1}, 0.13f, 0.03f}, {{0, 0.24f, -0.95f}, 0.2f, 0.012f}, {{0.33f, 0.1f, -0.93f}, 0.13f, -0.022f},
            {{-0.33f, 0.1f, -0.93f}, 0.13f, -0.022f}, {{0.55f, -0.08f, -0.78f}, 0.18f, 0.012f}, {{-0.55f, -0.08f, -0.78f}, 0.18f, 0.012f},
            {{0, -0.38f, -0.92f}, 0.12f, -0.035f}, {{0, -0.62f, -0.8f}, 0.16f, 0.02f}}));
        Vector3 mouth = on_ellipsoid(hc, hr, {0, -0.38f, -0.92f}, 0.035f);
        b.material(MAT_FLESH).color(DRIED).ellipsoid({mouth.x, mouth.y, mouth.z + 0.004f}, {0.042f, 0.034f, 0.009f}, 14, 8);
        b.material(MAT_VOID).color(BLACK).ellipsoid({mouth.x, mouth.y, mouth.z - 0.004f}, {0.022f, 0.016f, 0.009f}, 12, 8);
        b.material(MAT_LEECH).color(LEECH).ellipsoid(on_ellipsoid(hc, hr, {-0.6f, -0.1f, -0.75f}, -0.01f), {0.013f, 0.03f, 0.012f}, 10, 6);
        b.material(MAT_SHEET).color(SHEET).drape({0, 0.12f, -0.02f}, {0.124f, 0.136f}, {0.3f, 0.26f}, 0.5f, 10, 40, 9, 0.12f,
            [](float th) { return 0.32f + 0.68f * (1.0f - std::cos(th)) * 0.5f; }, 7);
    }
    c.add_rigid(J_HEAD, d);
    for (float s : {-1.0f, 1.0f}) {
        d = {};
        hand(d, s, DSKIN, MAT_DROWNED, 1.45f, 0.16f, true);
        c.add_rigid(s < 0 ? J_WRI_L : J_WRI_R, d);
        d = {};
        MeshBuilder(d).material(MAT_DROWNED).color(DSKIN).ellipsoid({0, -0.045f, -0.055f}, {0.058f, 0.052f, 0.135f}, 16, 10);
        c.add_rigid(s < 0 ? J_ANK_L : J_ANK_R, d);
    }
    d = {};
    MeshBuilder(d).material(MAT_LEECH).color(LEECH).ellipsoid({0, -0.22f, -0.05f}, {0.012f, 0.034f, 0.012f}, 10, 6);
    c.add_rigid(J_ELB_L, d);
    return c;
}

Character Character::make(Kind k) { return k == Kind::Survivor ? build_survivor() : build_drowned(); }

void Character::fk() {
    Matrix root = MatrixMultiply(MatrixMultiply(MatrixRotateX(std::pow(fall_, 2.2f) * PI / 2), MatrixRotateY(yaw_)),
                                 MatrixTranslate(pos_.x, pos_.y, pos_.z));
    for (int j = 0; j < J_COUNT; ++j) {
        const Vector3& a = ang_[j];
        Matrix R = MatrixMultiply(MatrixMultiply(MatrixRotateZ(a.z), MatrixRotateX(a.x)), MatrixRotateY(a.y));
        Vector3 o = off_[j];
        if (j == J_PELVIS) o = {0, pelvis_h_ + bob_, 0};
        Matrix L = MatrixMultiply(R, MatrixTranslate(o.x, o.y, o.z));
        W_[j] = MatrixMultiply(L, PARENT[j] < 0 ? root : W_[PARENT[j]]);
    }
}

void Character::animate(const std::string& pose, float speed, float dt, float aim_pitch) {
    t_ += dt;
    Vector3 T[J_COUNT]{};
    float bob = 0;
    targets(pose, speed, dt, aim_pitch, T, bob);
    bool sharp = pose == "windup" || pose == "strike" || pose == "hurt" || pose == "stagger";
    float k = smoothing(sharp ? 16.0f : 9.0f, dt);
    for (int j = 0; j < J_COUNT; ++j) ang_[j] = Vector3Lerp(ang_[j], T[j], k);
    bob_ = Lerp(bob_, bob, k);
    fall_ = pose == "dead" ? std::min(1.0f, fall_ + dt * 2.2f) : std::max(0.0f, fall_ - dt * 1.4f);
    fk();
    Vector3 right{std::cos(yaw_), 0, -std::sin(yaw_)};
    for (auto& d : dyn_) {
        std::vector<Vector3> pts;
        for (auto& [j, off] : d.pts) pts.push_back(Vector3Transform(off, W_[j]));
        d.sweep.build(pts, right);
        refresh(d.mesh, d.sweep.data);
    }
}

void Character::targets(const std::string& pose, float speed, float dt, float ap, Vector3* T, float& bob) {
    const bool drowned = kind == Kind::Drowned;
    for (float s : {-1.0f, 1.0f}) {   // relaxed baseline
        T[s < 0 ? J_SHO_L : J_SHO_R] = {0.05f, 0, -0.1f * s};
        T[s < 0 ? J_ELB_L : J_ELB_R] = {0.2f, 0, 0};
        T[s < 0 ? J_HIP_L : J_HIP_R] = {0.03f, 0, 0.02f * s};
        T[s < 0 ? J_KNE_L : J_KNE_R] = {-0.07f, 0, 0};
    }
    T[J_SPINE] = {-0.02f + std::sin(t_ * 1.6f) * 0.012f, 0, 0};
    T[J_CHEST] = {std::sin(t_ * 1.6f + 0.5f) * 0.01f, 0, 0};
    T[J_NECK] = {-0.05f, 0, 0};
    T[J_PELVIS] = {0, 0, std::sin(t_ * 0.5f) * 0.02f};
    if (drowned) {   // wrong even at rest: slumped, head lolling, one arm hanging forward
        T[J_SPINE] = {-0.3f, 0, 0.08f};
        T[J_CHEST] = {-0.12f, 0, 0};
        T[J_NECK] = {-0.12f, 0, 0};
        T[J_HEAD] = {0.14f, 0.1f, 0.4f + std::sin(t_ * 0.7f) * 0.08f};   // face lifted TOWARD you, tilted wrong
        T[J_SHO_R] = {0.28f, 0, -0.05f};
        T[J_SHO_L] = {0.12f, 0, 0.1f};
    }
    if (pose == "walk" || pose == "run") {
        bool run = pose == "run";
        phase_ += dt * std::max(speed, 0.4f) / (run ? 1.9f : 1.3f) * 2 * PI;
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
    } else if (pose == "shamble") {   // one leg drags, one arm reaches, the other swings dead
        phase_ += dt * std::max(speed, 0.3f) / 0.95f * 2 * PI;
        float s = std::sin(phase_);
        T[J_HIP_L] = {s * 0.22f, 0, -0.03f};
        T[J_KNE_L] = {-0.08f, 0, 0};
        T[J_HIP_R] = {-s * 0.36f, 0, 0.03f};
        T[J_KNE_R] = {-0.12f - std::max(0.0f, -std::cos(phase_)) * 0.7f, 0, 0};
        T[J_SHO_R] = {1.3f + std::sin(t_ * 1.3f) * 0.1f, 0, -0.08f};
        T[J_ELB_R] = {0.15f, 0, 0};
        T[J_SHO_L] = {0.3f + s * 0.25f, 0, 0.1f};
        T[J_ELB_L] = {0.1f, 0, 0};
        T[J_SPINE] = {-0.32f + s * 0.06f, s * 0.12f, 0.1f};
        T[J_CHEST] = {-0.1f, -s * 0.08f, 0};
        bob = -std::fabs(s) * 0.03f;
    } else if (pose == "aim") {   // two-handed pistol: strong arm straight, support arm crossing in
        T[J_SHO_R] = {PI / 2 + ap, 0, -0.14f};
        T[J_ELB_R] = {0.02f, 0, 0};
        T[J_SHO_L] = {PI / 2 + ap - 0.12f, 0, 0.62f};
        T[J_ELB_L] = {0.35f, 0, 0};
        T[J_SPINE] = {-0.06f, 0.08f, 0};
        T[J_CHEST] = {-0.03f, 0.08f, 0};
        T[J_NECK] = {-0.1f, -0.1f, 0};
        T[J_HIP_L] = {0.22f, 0, -0.04f};
        T[J_KNE_L] = {-0.2f, 0, 0};
        T[J_HIP_R] = {-0.2f, 0, 0.06f};
        T[J_KNE_R] = {-0.1f, 0, 0};
        bob = -0.02f;
    } else if (pose == "windup") {   // the readable tell: arms thrown up, spine arched, head back
        T[J_SHO_L] = {2.55f, 0, -0.25f};
        T[J_SHO_R] = {2.55f, 0, 0.25f};
        T[J_ELB_L] = T[J_ELB_R] = {0.35f, 0, 0};
        T[J_SPINE] = {0.22f, 0, 0};
        T[J_CHEST] = {0.12f, 0, 0};
        T[J_NECK] = {0.15f, 0, 0};
        T[J_HEAD] = {0.25f, 0, 0.1f};
        T[J_HIP_L] = {0.25f, 0, 0};
        T[J_KNE_L] = {-0.35f, 0, 0};
        T[J_HIP_R] = {-0.2f, 0, 0};
    } else if (pose == "strike") {
        T[J_SHO_L] = T[J_SHO_R] = {1.1f, 0, 0};
        T[J_ELB_L] = T[J_ELB_R] = {0.1f, 0, 0};
        T[J_SPINE] = {-0.45f, 0, 0};
        T[J_CHEST] = {-0.15f, 0, 0};
        T[J_HIP_L] = {0.55f, 0, 0};
        T[J_KNE_L] = {-0.45f, 0, 0};
        T[J_HIP_R] = {-0.35f, 0, 0};
        bob = -0.06f;
    } else if (pose == "hurt" || pose == "stagger") {
        T[J_SPINE] = {0.32f, 0, 0.1f};
        T[J_CHEST] = {0.15f, 0, 0};
        T[J_NECK] = {0.3f, 0, 0};
        T[J_SHO_L] = {0.5f, 0, -0.4f};
        T[J_SHO_R] = {0.4f, 0, 0.4f};
        T[J_HIP_R] = {-0.3f, 0, 0};
        T[J_KNE_R] = {-0.25f, 0, 0};
    }
    for (float s : {-1.0f, 1.0f}) {   // keep the soles flat
        int hp = s < 0 ? J_HIP_L : J_HIP_R, kn = s < 0 ? J_KNE_L : J_KNE_R;
        T[s < 0 ? J_ANK_L : J_ANK_R] = {-(T[hp].x + T[kn].x) * 0.9f, 0, 0};
    }
}

void Character::draw(const Material& m) const {
    for (const auto& r : rigid_) DrawMesh(r.mesh, m, W_[r.joint]);
    for (const auto& d : dyn_) DrawMesh(d.mesh, m, MatrixIdentity());
}

void Character::unload() {
    for (auto& r : rigid_) UnloadMesh(r.mesh);
    for (auto& d : dyn_) UnloadMesh(d.mesh);
    rigid_.clear();
    dyn_.clear();
}

}  // namespace dw
