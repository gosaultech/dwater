// damned_waters/engine/src/cast_survivor.cpp
// Purpose: the survivor, built in C++ at startup (no external model files):
// an ordinary man in a waxed jacket; sculpted face, real eyes, hair, a pistol.
#include <cmath>

#include "cast_common.hpp"

namespace dw {
using namespace cast;
namespace {
const Color SKIN{198, 150, 122, 255}, HAIR{36, 27, 20, 255}, JACKET{74, 80, 52, 255}, DENIM{44, 56, 86, 255},
    BOOT{58, 40, 28, 255}, METAL{30, 30, 32, 255};
}  // namespace

Character build_survivor() {
    Character c;
    c.kind = Kind::Survivor;
    c.pelvis_h_ = 0.95f;
    c.thickness_ = 0.12f;
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
                {{J_PELVIS, {0, -0.1f, 0}, R_BODY}, {J_PELVIS, {}, R_BODY}, {J_SPINE, {}, R_BODY}, {J_CHEST, {}, R_BODY},
                 {J_CHEST, {0, 0.19f, 0}, R_BODY}, {J_NECK, {0, 0.07f, 0}, R_BODY}});
    for (float s : {-1.0f, 1.0f}) {   // sleeves: deltoid, bicep, narrow elbow, forearm swell, cuff
        const bool L = s < 0;
        c.add_sweep(Sweep(22, 12, Profile{{{0.0f, 0.052f, 0.05f, 0}, {0.18f, 0.063f, 0.064f, 0}, {0.4f, 0.055f, 0.057f, 0},
                                           {0.58f, 0.047f, 0.048f, 0}, {0.7f, 0.05f, 0.047f, 0}, {0.95f, 0.043f, 0.041f, 0},
                                           {1.0f, 0.036f, 0.032f, 0}}},
                          MAT_CLOTH, JACKET, 0.62f),
                    {{J_CHEST, {0.1f * s, 0.18f, 0}, R_BODY}, {L ? J_SHO_L : J_SHO_R, {}, R_BODY},
                     {L ? J_ELB_L : J_ELB_R, {}, L ? R_UARM_L : R_UARM_R}, {L ? J_WRI_L : J_WRI_R, {}, L ? R_FARM_L : R_FARM_R}});
        c.add_sweep(Sweep(24, 12, Profile{{{0.0f, 0.1f, 0.1f, 0}, {0.12f, 0.092f, 0.095f, 0}, {0.3f, 0.08f, 0.083f, 0},
                                           {0.53f, 0.054f, 0.057f, 0}, {0.66f, 0.056f, 0.062f, -0.006f}, {0.86f, 0.044f, 0.046f, 0},
                                           {1.0f, 0.043f, 0.045f, 0}}},
                          MAT_DENIM, DENIM, 0.88f),
                    {{J_PELVIS, {0.065f * s, -0.02f, 0}, R_BODY}, {L ? J_HIP_L : J_HIP_R, {}, R_BODY},
                     {L ? J_KNE_L : J_KNE_R, {}, L ? R_THIGH_L : R_THIGH_R}, {L ? J_ANK_L : J_ANK_R, {}, L ? R_SHIN_L : R_SHIN_R}});
    }
    MeshData d;
    MeshBuilder(d).material(MAT_DENIM).color(DENIM).ellipsoid({0, -0.03f, 0}, {0.158f, 0.1f, 0.112f}, 18, 10);
    c.add_rigid(J_PELVIS, R_BODY, d);
    d = {};   // collar band
    MeshBuilder(d).material(MAT_CLOTH).color(Color{60, 64, 42, 255}).drape({0, 0.225f, 0.01f}, {0.078f, 0.072f}, {0.104f, 0.094f}, 0.06f, 3, 24, 0, 0);
    c.add_rigid(J_CHEST, R_BODY, d);
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
    c.add_rigid(J_HEAD, R_HEAD, d);
    for (float s : {-1.0f, 1.0f}) {
        d = {};
        hand(d, s, HandStyle{});
        if (s > 0) {   // the pistol, held in the right hand
            MeshBuilder m(d);
            m.material(MAT_METAL).color(METAL).tube({0, -0.075f, -0.032f}, {0, -0.205f, -0.032f}, 0.015f, 0.014f, 6);
            m.tube({0, -0.08f, -0.03f}, {0, -0.066f, 0.03f}, 0.012f, 0.012f, 6);
        }
        c.add_rigid(s < 0 ? J_WRI_L : J_WRI_R, s < 0 ? R_FARM_L : R_FARM_R, d);
        d = {};
        MeshBuilder b(d);
        b.material(MAT_LEATHER).color(BOOT).ellipsoid({0, -0.045f, -0.045f}, {0.05f, 0.047f, 0.12f}, 16, 10);
        b.color(Color{28, 20, 14, 255}).ellipsoid({0, -0.083f, -0.045f}, {0.053f, 0.012f, 0.123f}, 16, 6);
        c.add_rigid(s < 0 ? J_ANK_L : J_ANK_R, s < 0 ? R_SHIN_L : R_SHIN_R, d);
    }
    return c;
}

}  // namespace dw
