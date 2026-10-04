// damned_waters/engine/src/cast_items.cpp
// Purpose: the things in the case as 3D models, for the status screen (turning in the preview,
// large when examined) and for the world (lying where they're found). The guns are cast_guns.cpp's
// own; the rest are built here at their real size: a box of 9 mm rounds, a box of shells with a
// few loose, a field dressing, the EHBO kit and case, the cellar key on its paper tag.
// Each is built standing as it's best shown: upright, its face toward +z (the camera), centred.
#include "cast_items.hpp"

#include <cmath>

#include "cast_guns.hpp"

namespace dw::cast {
namespace {
constexpr float MM = 0.001f;
const Color CARD{132, 92, 54, 255}, CARD_LIGHT{196, 170, 120, 255}, PRINT_RED{150, 30, 26, 255}, BRASS{190, 150, 70, 255},
    COPPER{168, 96, 58, 255}, HULL{150, 24, 22, 255}, PAPER{222, 210, 182, 255}, KIT_GREEN{36, 112, 62, 255},
    CROSS_WHITE{236, 236, 230, 255}, IRON{70, 74, 70, 255}, VERDIGRIS{78, 118, 100, 255}, STRING{170, 150, 110, 255};

// A cartridge standing up: brass case, copper-jacketed round nose.
void round_9mm(MeshBuilder& b, Vector3 at) {
    b.material(MAT_STEEL).color(BRASS).tube(at, {at.x, at.y + 19 * MM, at.z}, 4.9f * MM, 4.8f * MM, 14);
    b.ellipsoid({at.x, at.y, at.z}, {4.9f * MM, 0.6f * MM, 4.9f * MM}, 14, 4);   // the base
    b.material(MAT_METAL).color(COPPER).ellipsoid({at.x, at.y + 20 * MM, at.z}, {4.5f * MM, 9 * MM, 4.5f * MM}, 14, 8);
}

// A 12-gauge shell lying along x: red hull, brass head.
void shell(MeshBuilder& b, Vector3 at, float yaw) {
    const Vector3 d{std::cos(yaw), 0, std::sin(yaw)};
    auto p = [&](float s) { return Vector3{at.x + d.x * s, at.y, at.z + d.z * s}; };
    b.material(MAT_STEEL).color(BRASS).tube(p(0), p(13 * MM), 11 * MM, 11 * MM, 20);
    b.ellipsoid(p(0), {std::fabs(d.x) * 0.6f * MM + std::fabs(d.z) * 11 * MM, 11 * MM, std::fabs(d.z) * 0.6f * MM + std::fabs(d.x) * 11 * MM}, 16, 4);
    b.material(MAT_NYLON).color(HULL).tube(p(13 * MM), p(70 * MM), 10.5f * MM, 10.5f * MM, 20);
    b.color(Color{110, 18, 16, 255}).ellipsoid(p(70 * MM), {std::fabs(d.x) * 1.5f * MM + std::fabs(d.z) * 10.5f * MM, 10.5f * MM,
                                                          std::fabs(d.z) * 1.5f * MM + std::fabs(d.x) * 10.5f * MM}, 16, 4);
}

// A gun as one mesh, side-on (muzzle to +x, top up, its right side toward the camera), centred.
ItemModel gun(const GunParts& g, float size) {
    Matrix lay = MatrixIdentity();   // wrist space -> side-on (as Game::gun_view lays it)
    lay.m0 = 0; lay.m4 = -1; lay.m8 = 0;
    lay.m1 = 0; lay.m5 = 0; lay.m9 = -1;
    lay.m2 = 1; lay.m6 = 0; lay.m10 = 0;
    const Matrix M = MatrixMultiply(MatrixTranslate(-g.centre.x, -g.centre.y, -g.centre.z), lay);
    ItemModel m;
    m.mesh.append(g.fixed, M);
    m.mesh.append(g.moving, M);
    m.size = size;
    return m;
}
}  // namespace

ItemModel item_model(int item) {
    ItemModel m;
    MeshBuilder b(m.mesh);
    switch (item) {
        case I_HANDGUN: return gun(m92fs(), 0.22f);
        case I_SHOTGUN: return gun(r870(MatrixIdentity()), 1.06f);
        case I_HANDGUN_AMMO: {   // a 50-round box of 9 mm Parabellum, a few rounds out beside it
            b.material(MAT_CLOTH).color(CARD).box({-0.012f, 0.02f, 0}, {0.048f, 0.02f, 0.034f}, 0.12f, 16, 8);
            b.color(CARD_LIGHT).box({-0.012f, 0.022f, 0.0335f}, {0.042f, 0.012f, 0.0012f}, 0.1f, 12, 6);   // the label
            b.color(PRINT_RED).box({-0.012f, 0.03f, 0.0345f}, {0.042f, 0.0025f, 0.0008f}, 0.1f, 12, 4);    // its stripe
            for (int i = 0; i < 3; ++i) round_9mm(b, {0.05f + 0.012f * float(i), 0, 0.02f - 0.013f * float(i % 2)});
            m.size = 0.13f;
            break;
        }
        case I_SHELLS: {   // a carton of buckshot and three loose, lying in front
            b.material(MAT_CLOTH).color(Color{176, 40, 30, 255}).box({0, 0.036f, -0.02f}, {0.055f, 0.036f, 0.03f}, 0.1f, 16, 8);
            b.color(Color{230, 196, 70, 255}).box({0, 0.044f, 0.0105f}, {0.05f, 0.014f, 0.0012f}, 0.1f, 12, 6);   // the label
            for (int i = 0; i < 3; ++i) shell(b, {-0.04f + 0.01f * float(i), 0.0108f, 0.03f + 0.024f * float(i)}, 0.12f * float(i - 1));
            m.size = 0.14f;
            break;
        }
        case I_MED_S: {   // a field dressing in its paper wrapper
            b.material(MAT_CLOTH).color(PAPER).box({0, 0.012f, 0}, {0.055f, 0.012f, 0.04f}, 0.25f, 16, 8);
            b.color(PRINT_RED).box({0, 0.012f, 0.0395f}, {0.055f, 0.0018f, 0.001f}, 0.1f, 12, 4);
            b.color(Color{150, 140, 120, 255}).box({0, 0.0243f, 0}, {0.03f, 0.0004f, 0.018f}, 0.2f, 8, 4);   // the printed panel
            m.size = 0.12f;
            break;
        }
        case I_MED_M: {   // the EHBO kit: a soft green pouch, a white cross, a zip round it
            b.material(MAT_NYLON).color(KIT_GREEN).box({0, 0.065f, 0}, {0.095f, 0.065f, 0.035f}, 0.35f, 24, 14);
            b.material(MAT_CLOTH).color(CROSS_WHITE);
            b.box({0, 0.065f, 0.034f}, {0.012f, 0.038f, 0.0025f}, 0.15f, 10, 6);
            b.box({0, 0.065f, 0.034f}, {0.038f, 0.012f, 0.0025f}, 0.15f, 10, 6);
            b.material(MAT_METAL).color(Color{40, 40, 40, 255}).tube({-0.09f, 0.128f, 0}, {0.09f, 0.128f, 0}, 0.0025f, 0.0025f, 6);   // the zip
            m.size = 0.2f;
            break;
        }
        case I_MED_L: {   // the EHBO case: hard green plastic, a handle, two latches, the cross
            b.material(MAT_POLYMER).color(Color{30, 104, 56, 255}).box({0, 0.11f, 0}, {0.16f, 0.11f, 0.055f}, 0.18f, 24, 14);
            b.material(MAT_CLOTH).color(CROSS_WHITE);
            b.box({0, 0.11f, 0.055f}, {0.018f, 0.06f, 0.003f}, 0.12f, 10, 6);
            b.box({0, 0.11f, 0.055f}, {0.06f, 0.018f, 0.003f}, 0.12f, 10, 6);
            b.material(MAT_POLYMER).color(Color{24, 70, 40, 255}).chain({{-0.05f, 0.22f, 0}, {-0.04f, 0.25f, 0}, {0.04f, 0.25f, 0}, {0.05f, 0.22f, 0}},
                                                                      {0.008f, 0.008f, 0.008f, 0.008f}, 8);
            b.material(MAT_STEEL).color(Color{170, 170, 166, 255});
            for (float x : {-0.11f, 0.11f}) b.box({x, 0.2f, 0.05f}, {0.012f, 0.012f, 0.008f}, 0.3f, 8, 6);
            m.size = 0.36f;
            break;
        }
        case I_CELLAR_KEY: {   // a heavy iron key, green with verdigris, the paper tag on a string
            std::vector<Vector3> bow;
            std::vector<float> rr;
            for (int i = 0; i <= 24; ++i) {
                const float a = 2 * PI * float(i) / 24.0f;
                bow.push_back({-0.045f + 0.016f * std::cos(a), 0.016f * std::sin(a), 0});
                rr.push_back(0.004f);
            }
            b.material(MAT_METAL).color(VERDIGRIS).chain(bow, rr, 8);
            b.color(IRON).tube({-0.029f, 0, 0}, {0.06f, 0, 0}, 0.004f, 0.0035f, 10);   // the shank
            b.box({0.05f, -0.011f, 0}, {0.005f, 0.008f, 0.003f}, 0.2f, 8, 6);          // the bit's wards
            b.box({0.039f, -0.009f, 0}, {0.004f, 0.006f, 0.003f}, 0.2f, 8, 6);
            b.material(MAT_CLOTH).color(STRING).chain({{-0.058f, -0.008f, 0}, {-0.07f, -0.03f, 0.004f}, {-0.075f, -0.045f, 0.004f}},
                                                      {0.0012f, 0.0012f, 0.0012f}, 5);
            b.color(PAPER).box({-0.078f, -0.062f, 0.004f}, {0.016f, 0.022f, 0.0008f}, 0.15f, 8, 6);   // KELDER, in ink
            b.color(Color{60, 50, 40, 255}).box({-0.078f, -0.058f, 0.005f}, {0.01f, 0.0018f, 0.0003f}, 0.1f, 6, 4);
            m.size = 0.15f;
            break;
        }
        default: break;
    }
    // Centre it on its bounds (the preview turns it about its middle).
    if (m.mesh.count() > 0) {
        Vector3 lo{1e9f, 1e9f, 1e9f}, hi{-1e9f, -1e9f, -1e9f};
        for (size_t i = 0; i < m.mesh.count(); ++i) {
            const Vector3 p{m.mesh.pos[i * 3], m.mesh.pos[i * 3 + 1], m.mesh.pos[i * 3 + 2]};
            lo = Vector3Min(lo, p);
            hi = Vector3Max(hi, p);
        }
        m.centre = Vector3Scale(Vector3Add(lo, hi), 0.5f);
    }
    return m;
}

}  // namespace dw::cast
