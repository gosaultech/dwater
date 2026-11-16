// damned_waters/engine/src/cast_items.cpp
// Purpose: the things in the case as 3D models, for the status screen (turning in the preview,
// large when examined) and for the world (lying where they're found). The guns are cast_guns.cpp's
// own; the rest are built here at their real size: a box of 9 mm rounds, a box of shells with a
// few loose, a field dressing, the EHBO kit and case, the cellar key on its paper tag.
// Each is built standing as it's best shown: upright, its face toward +z (the camera), centred.
#include "cast_items.hpp"

#include <algorithm>
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

// A box with every edge eased by `r`, the way card folds and moulded plastic comes: flat faces
// that catch the light whole, not the pillow a rounded ellipsoid makes. Centre c, half sizes h.
void crate(MeshBuilder& b, Vector3 c, Vector3 h, float r) {
    r = std::min({r, h.x, h.y, h.z});
    Outline o;
    o.arc(c.y + h.y - r, c.z + h.z - r, r, 0, PI / 2, 3)
        .arc(c.y - h.y + r, c.z + h.z - r, r, PI / 2, PI, 3)
        .arc(c.y - h.y + r, c.z - h.z + r, r, PI, 3 * PI / 2, 3)
        .arc(c.y + h.y - r, c.z - h.z + r, r, 3 * PI / 2, 2 * PI, 3);
    b.slab(o.p, c.x, h.x, r, 2);
}
const Vector3 RIGHT{1, 0, 0}, UP{0, 1, 0}, BACK{0, 0, -1};   // (print on a front face: RIGHT, UP; on a top face: RIGHT, BACK)

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
        case I_HANDGUN_AMMO: {   // a 50-round carton of 9 mm, lying flat: grey card, a navy band, the lid's edge; a few rounds out beside it
            const Vector3 c{-0.014f, 0.016f, 0}, h{0.05f, 0.016f, 0.029f};
            b.material(MAT_CARD).color(Color{176, 170, 152, 255});
            crate(b, c, h, 0.0012f);
            b.color(Color{28, 40, 78, 255});
            crate(b, {c.x, c.y - 0.004f, c.z}, {h.x + 0.00015f, 0.007f, h.z + 0.00015f}, 0.0006f);    // the band, printed right round
            b.color(Color{70, 64, 54, 255});
            crate(b, {c.x, c.y + 0.0085f, c.z}, {h.x + 0.0001f, 0.0002f, h.z + 0.0001f}, 0.0001f);    // where the lid tucks in
            b.material(MAT_DEFAULT).color(Color{224, 220, 204, 255});
            print_text(b, "9mm PARABELLUM", {c.x, c.y - 0.004f, c.z + h.z + 0.0002f}, RIGHT, UP, 0.0058f, 0.00042f);
            b.color(Color{40, 38, 36, 255});
            print_text(b, "50 CARTRIDGES", {c.x, c.y + h.y + 0.0001f, c.z + 0.008f}, RIGHT, BACK, 0.0062f, 0.00045f);
            print_text(b, "VOS MUNITIE", {c.x, c.y + h.y + 0.0001f, c.z - 0.008f}, RIGHT, BACK, 0.0048f, 0.00036f);
            for (int i = 0; i < 3; ++i) round_9mm(b, {0.05f + 0.012f * float(i), 0, 0.02f - 0.013f * float(i % 2)});
            m.size = 0.14f;
            break;
        }
        case I_SHELLS: {   // a carton of buckshot, dull red with a black band, and three shells loose in front
            const Vector3 c{0, 0.034f, -0.022f}, h{0.054f, 0.034f, 0.03f};
            b.material(MAT_CARD).color(Color{124, 34, 28, 255});
            crate(b, c, h, 0.0012f);
            b.color(Color{24, 22, 22, 255});
            crate(b, {c.x, c.y - 0.012f, c.z}, {h.x + 0.00015f, 0.009f, h.z + 0.00015f}, 0.0006f);
            b.color(Color{60, 16, 14, 255});
            crate(b, {c.x, c.y + 0.024f, c.z}, {h.x + 0.0001f, 0.0002f, h.z + 0.0001f}, 0.0001f);
            b.material(MAT_DEFAULT).color(Color{226, 214, 176, 255});
            print_text(b, "12 GA", {c.x, c.y + 0.011f, c.z + h.z + 0.0002f}, RIGHT, UP, 0.014f, 0.0011f);
            print_text(b, "BUCKSHOT", {c.x, c.y - 0.012f, c.z + h.z + 0.0002f}, RIGHT, UP, 0.0066f, 0.0005f);
            for (int i = 0; i < 3; ++i) shell(b, {-0.04f + 0.01f * float(i), 0.0108f, 0.03f + 0.024f * float(i)}, 0.12f * float(i - 1));
            m.size = 0.15f;
            break;
        }
        case I_MED_S: {   // a field dressing sealed in waxed paper: a soft pack, a red cross and VERBAND printed on it
            b.material(MAT_CARD).color(PAPER).box({0, 0.012f, 0}, {0.055f, 0.012f, 0.04f}, 0.16f, 20, 10);
            b.color(Color{196, 184, 156, 255});
            crate(b, {0.049f, 0.012f, 0}, {0.0045f, 0.0122f, 0.0402f}, 0.001f);          // the crimped end where it tears open
            b.material(MAT_DEFAULT).color(PRINT_RED);
            crate(b, {-0.03f, 0.0241f, 0}, {0.0035f, 0.0002f, 0.011f}, 0.0001f);          // the cross
            crate(b, {-0.03f, 0.0241f, 0}, {0.011f, 0.0002f, 0.0035f}, 0.0001f);
            b.color(Color{52, 48, 44, 255});
            print_text(b, "VERBAND", {0.008f, 0.0243f, 0.004f}, RIGHT, BACK, 0.0075f, 0.00055f);
            print_text(b, "EHBO - 1", {0.008f, 0.0243f, -0.012f}, RIGHT, BACK, 0.0042f, 0.00032f);
            m.size = 0.12f;
            break;
        }
        case I_MED_M: {   // the EHBO kit: a soft green pouch, the white cross, a zip round its top with a pull
            b.material(MAT_NYLON).color(KIT_GREEN).box({0, 0.065f, 0}, {0.095f, 0.065f, 0.035f}, 0.22f, 28, 16);
            b.material(MAT_POLYMER).color(CROSS_WHITE);
            crate(b, {0, 0.07f, 0.0345f}, {0.011f, 0.034f, 0.0012f}, 0.0006f);
            crate(b, {0, 0.07f, 0.0345f}, {0.034f, 0.011f, 0.0012f}, 0.0006f);
            b.material(MAT_DEFAULT).color(CROSS_WHITE);
            print_text(b, "EHBO", {0, 0.022f, 0.0352f}, RIGHT, UP, 0.011f, 0.0009f);
            b.material(MAT_NYLON).color(Color{20, 66, 36, 255});                           // the zip's tape, and its teeth
            crate(b, {0, 0.112f, 0.0f}, {0.0935f, 0.004f, 0.0358f}, 0.002f);
            b.material(MAT_METAL).color(Color{52, 52, 54, 255});
            crate(b, {0, 0.112f, 0.0f}, {0.092f, 0.0012f, 0.0362f}, 0.0006f);
            b.material(MAT_STEEL).color(Color{170, 170, 166, 255});
            crate(b, {0.07f, 0.112f, 0.0375f}, {0.004f, 0.003f, 0.0015f}, 0.0008f);       // the slider
            crate(b, {0.07f, 0.1f, 0.0385f}, {0.003f, 0.009f, 0.0007f}, 0.0006f);         // its pull
            m.size = 0.2f;
            break;
        }
        case I_MED_L: {   // the EHBO case: hard green plastic in two halves, a handle, two latches over the seam, the cross
            const Vector3 c{0, 0.11f, 0}, h{0.16f, 0.11f, 0.055f};
            b.material(MAT_POLYMER).color(Color{28, 96, 54, 255});
            crate(b, c, h, 0.014f);
            b.color(Color{12, 40, 24, 255});
            crate(b, c, {h.x + 0.0004f, h.y + 0.0004f, 0.0012f}, 0.001f);                 // the seam between lid and base
            b.color(Color{24, 84, 48, 255});                                              // a raised panel on the lid
            crate(b, {0, 0.11f, 0.055f}, {0.125f, 0.08f, 0.0015f}, 0.0012f);
            b.color(CROSS_WHITE);
            crate(b, {0, 0.122f, 0.0568f}, {0.016f, 0.05f, 0.0012f}, 0.0008f);
            crate(b, {0, 0.122f, 0.0568f}, {0.05f, 0.016f, 0.0012f}, 0.0008f);
            b.material(MAT_DEFAULT).color(CROSS_WHITE);
            print_text(b, "EHBO", {0, 0.05f, 0.0568f}, RIGHT, UP, 0.016f, 0.0013f);
            b.material(MAT_POLYMER).color(Color{18, 58, 34, 255});
            b.chain({{-0.055f, 0.22f, 0}, {-0.05f, 0.248f, 0}, {-0.03f, 0.256f, 0}, {0.03f, 0.256f, 0}, {0.05f, 0.248f, 0}, {0.055f, 0.22f, 0}},
                    {0.008f, 0.008f, 0.0085f, 0.0085f, 0.008f, 0.008f}, 10, 0.7f);
            b.material(MAT_STEEL).color(Color{170, 170, 166, 255});
            for (float x : {-0.105f, 0.105f}) {                                             // latches: a plate either side of the seam, a lever over it
                crate(b, {x, 0.2205f, 0}, {0.012f, 0.0012f, 0.016f}, 0.0008f);
                crate(b, {x, 0.2225f, 0.003f}, {0.008f, 0.0016f, 0.011f}, 0.001f);
            }
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
            b.material(MAT_METAL).color(VERDIGRIS).chain(bow, rr, 10, 0.6f);          // a flat-sided ring, as forged
            b.color(IRON).tube({-0.029f, 0, 0}, {0.06f, 0, 0}, 0.004f, 0.0035f, 12);   // the shank
            b.tube({-0.031f, 0, 0}, {-0.026f, 0, 0}, 0.0055f, 0.0055f, 12);            // its collar at the bow
            b.tube({0.058f, 0, 0}, {0.0625f, 0, 0}, 0.0042f, 0.0042f, 12);             // and its tip
            crate(b, {0.05f, -0.011f, 0}, {0.005f, 0.008f, 0.0022f}, 0.0006f);         // the bit's wards
            crate(b, {0.039f, -0.009f, 0}, {0.004f, 0.006f, 0.0022f}, 0.0006f);
            b.material(MAT_COTTON).color(STRING).chain({{-0.058f, -0.008f, 0}, {-0.07f, -0.03f, 0.004f}, {-0.075f, -0.045f, 0.004f}},
                                                       {0.0012f, 0.0012f, 0.0012f}, 5);
            b.material(MAT_CARD).color(PAPER);
            crate(b, {-0.078f, -0.062f, 0.004f}, {0.016f, 0.022f, 0.0005f}, 0.0004f);
            b.material(MAT_DEFAULT).color(Color{44, 40, 62, 255});                       // KELDER, in ink
            print_text(b, "KELDER", {-0.078f, -0.066f, 0.0047f}, RIGHT, UP, 0.0046f, 0.00045f);
            m.size = 0.15f;
            break;
        }
        case I_STAFF_PASS: {   // a keycard on a red lanyard: white, the store's blue band, a photo, the clip
            b.material(MAT_POLYMER).color(Color{232, 232, 228, 255});
            crate(b, {0, 0, 0}, {0.043f, 0.027f, 0.0005f}, 0.0004f);
            b.color(Color{28, 52, 120, 255});
            crate(b, {0, 0.017f, 0.0003f}, {0.043f, 0.009f, 0.0004f}, 0.0003f);         // DE ZWERM's band
            b.color(Color{120, 110, 100, 255});
            crate(b, {-0.026f, -0.007f, 0.0004f}, {0.011f, 0.014f, 0.0003f}, 0.0002f);  // the photo
            b.material(MAT_DEFAULT).color(Color{236, 236, 232, 255});
            print_text(b, "DE ZWERM", {0.004f, 0.017f, 0.0008f}, RIGHT, UP, 0.0064f, 0.0006f);
            b.color(Color{40, 40, 44, 255});
            print_text(b, "PERSONEEL", {0.012f, -0.001f, 0.0006f}, RIGHT, UP, 0.0038f, 0.00034f);
            for (int k = 1; k < 3; ++k)   // the number, the department
                crate(b, {0.012f, -0.002f - 0.008f * float(k), 0.0004f}, {0.02f - 0.004f * float(k), 0.0011f, 0.0002f}, 0.0001f);
            b.material(MAT_STEEL).color(Color{170, 170, 166, 255});
            crate(b, {0, 0.03f, 0}, {0.006f, 0.004f, 0.0015f}, 0.0006f);                 // the clip
            std::vector<Vector3> loop;   // the lanyard: a ribbon hanging in a long loop
            std::vector<float> lr;
            for (int i = 0; i <= 28; ++i) {
                const float a = 2 * PI * float(i) / 28.0f, up = 0.5f - 0.5f * std::cos(a);   // 0 at the clip, 1 at the top
                loop.push_back({0.028f * std::sin(a) * std::sqrt(up), 0.034f + 0.118f * up, 0.003f * std::sin(a)});
                lr.push_back(0.0032f);
            }
            b.material(MAT_NYLON).color(Color{150, 28, 30, 255}).chain(loop, lr, 6, 0.35f);
            m.size = 0.2f;
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
