// damned_waters/engine/src/cast_drowned.cpp
// Purpose: the Verdronkene (the Drowned), built in C++ at startup. A bloated
// corpse, drawn from how drowned bodies actually look, with canal details:
//   head   swollen and bare; the scalp has slid back off the skull and hangs in
//          a wet flap; milky bulging eyes in bruised sockets; the nose rotted to
//          a hole; lips gone so the teeth stand proud; one cheek torn through to
//          the molars; the jaw dislocated and hanging open, a swollen tongue lolling
//   body   gas-bloated, marbled and blistered; the belly split open, guts hanging;
//          a torn coat hanging open off the shoulders
//   limbs  arms far too long; a forearm snapped with the bone through the skin;
//          one hand degloved (the skin sliding off like a glove), the other white
//          and wrinkled ("washerwoman" hands); bare, livid feet
//   canal  zebra mussels grown in clusters, weed caught on the coat, leeches
// Asymmetric details swap sides with `variant`, so no two Drowned match.
#include <cmath>

#include "cast_common.hpp"

namespace dw {
using namespace cast;
namespace {
const Color DSKIN{152, 157, 138, 255}, BRUISE{70, 50, 68, 255}, LIVID{100, 80, 98, 255}, DERMIS{150, 92, 86, 255},
    SLOUGH{188, 184, 160, 255}, FLESH{104, 24, 22, 255}, GUM{80, 24, 26, 255}, DRIED{58, 14, 12, 255},
    GUTS{170, 124, 118, 255}, TONGUE{64, 32, 50, 255}, TOOTH{198, 178, 130, 255}, TOOTH_BAD{110, 86, 58, 255},
    BONE{216, 206, 180, 255}, EYE{206, 214, 214, 255}, IRIS_GHOST{150, 162, 168, 255}, HAIR{24, 22, 18, 255},
    COAT{42, 45, 43, 255}, TROUSER{31, 31, 35, 255}, SHELL_DARK{36, 28, 20, 255}, SHELL_LIGHT{198, 184, 148, 255},
    WEED{44, 60, 26, 255}, LEECH{30, 22, 16, 255}, ROT{20, 16, 14, 255};

// A cluster of zebra mussels on a surface: small striped shells, packed and half-buried.
void mussels(MeshData& d, Vector3 at, Vector3 normal, int count, float spread, unsigned seed) {
    unsigned s = seed * 2654435761u + 1u;
    auto rnd = [&s]() { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return float(s & 0xFFFF) / 65535.0f; };
    const Matrix frame = align_y(normal, 0.0f);
    const Painter stripes = [](Vector3 q) {   // the zigzag bands that give zebra mussels their name
        if (q.y < -0.35f) return Paint{MAT_MUSSEL, SHELL_DARK};
        float z = std::sin(q.z * 16.0f + 3.0f * std::fabs(std::sin(q.x * 5.0f)));
        return Paint{MAT_MUSSEL, z > -0.1f ? SHELL_LIGHT : SHELL_DARK};
    };
    for (int i = 0; i < count; ++i) {
        float a = rnd() * 2 * PI, r = std::sqrt(rnd()) * spread, len = 0.013f + rnd() * 0.007f;
        Vector3 local{std::cos(a) * r, -0.002f, std::sin(a) * r};
        Matrix m = MatrixMultiply(MatrixMultiply(MatrixRotateX((rnd() - 0.5f) * 0.9f), MatrixRotateY(rnd() * 2 * PI)),
                                  MatrixTranslate(local.x, local.y, local.z));
        m = MatrixMultiply(m, MatrixMultiply(frame, MatrixTranslate(at.x, at.y, at.z)));
        MeshBuilder(d).transform(m).ellipsoid({0, 0.004f, 0}, {len * 0.5f, len * 0.42f, len}, 10, 7, {}, stripes);
    }
}

// Teeth along an arc (a = angle from the front); some broken, some rotted dark, some gone.
void teeth(MeshData& d, Vector3 centre, float rx, float rz, float a0, float a1, int n, bool upper, unsigned seed) {
    unsigned s = seed * 747796405u + 3u;
    auto rnd = [&s]() { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return float(s & 0xFFFF) / 65535.0f; };
    for (int i = 0; i < n; ++i) {
        float a = a0 + (a1 - a0) * float(i) / float(n - 1), side = std::fabs(a);
        if (rnd() < 0.16f) continue;   // missing
        Vector3 p{centre.x + std::sin(a) * rx, centre.y, centre.z - std::cos(a) * rz};
        float w = side > 0.55f ? 0.0072f : 0.0058f, h = (side > 0.3f && side < 0.55f ? 0.0115f : 0.0095f) * (0.55f + rnd() * 0.6f);
        p.y += (upper ? -h : h) * 0.45f;
        const float r = rnd();
        const Color col = r < 0.2f ? Color{58, 44, 30, 255} : r < 0.45f ? TOOTH_BAD : TOOTH;   // some rotted black
        Matrix tilt = MatrixMultiply(MatrixMultiply(MatrixRotateZ((rnd() - 0.5f) * 0.5f), MatrixRotateX((rnd() - 0.5f) * 0.4f)),
                                     MatrixTranslate(p.x, p.y, p.z));
        MeshBuilder(d).transform(tilt).material(MAT_TOOTH).color(col).ellipsoid({0, 0, 0}, {w, h, 0.0034f}, 8, 6);
    }
}

float ragged(float th, float a, float b, float phase) {   // an uneven hem: 1 +- a few centimetres of tear
    return 1.0f + a * std::sin(th * 13.0f + phase) + b * std::sin(th * 29.0f + phase * 2.1f);
}
}  // namespace

Character build_drowned(int variant) {
    Character c;
    c.kind = Kind::Drowned;
    c.pelvis_h_ = 1.0f;
    c.thickness_ = 0.2f;   // bloated: lies high off the floor
    c.rng_ = 0x9E3779B9u ^ unsigned(variant * 7919 + 17);
    const float F = (variant % 2 == 0) ? -1.0f : 1.0f;   // the side with the broken arm and torn cheek
    const float M = -F;                                   // the side with the mussels and the degloved hand
    const int ELB_F = F < 0 ? J_ELB_L : J_ELB_R, WRI_F = F < 0 ? J_WRI_L : J_WRI_R, WRI_M = M < 0 ? J_WRI_L : J_WRI_R;
    const int HIP_F = F < 0 ? J_HIP_L : J_HIP_R, SHO_F = F < 0 ? J_SHO_L : J_SHO_R, KNE_M = M < 0 ? J_KNE_L : J_KNE_R;
    const Region FARM_F = F < 0 ? R_FARM_L : R_FARM_R, FARM_M = M < 0 ? R_FARM_L : R_FARM_R, UARM_F = F < 0 ? R_UARM_L : R_UARM_R;
    const Region THIGH_F = F < 0 ? R_THIGH_L : R_THIGH_R, SHIN_M = M < 0 ? R_SHIN_L : R_SHIN_R;

    Vector3* o = c.off_;
    o[J_SPINE] = {0, 0.12f, 0};  o[J_CHEST] = {0, 0.24f, 0};  o[J_NECK] = {0, 0.22f, -0.03f};  o[J_HEAD] = {0, 0.085f, -0.04f};
    o[J_JAW] = {0, 0.052f, -0.012f};
    for (float s : {-1.0f, 1.0f}) {   // arms far too long: the hands hang past the knees
        int sh = s < 0 ? J_SHO_L : J_SHO_R, el = s < 0 ? J_ELB_L : J_ELB_R, wr = s < 0 ? J_WRI_L : J_WRI_R;
        int hp = s < 0 ? J_HIP_L : J_HIP_R, kn = s < 0 ? J_KNE_L : J_KNE_R, an = s < 0 ? J_ANK_L : J_ANK_R;
        o[sh] = {0.23f * s, 0.2f, 0.02f}; o[el] = {0.05f * s, -0.36f, 0};  o[wr] = {0.02f * s, -0.35f, -0.01f};
        o[hp] = {0.11f * s, -0.03f, 0};   o[kn] = {0, -0.44f, 0.01f};      o[an] = {0, -0.43f, 0};
    }

    // ── Torso: bare, gas-bloated skin above a sodden waistband; the belly bulges FORWARD ──
    const Profile torso{{{0.0f, 0.195f, 0.155f, 0}, {0.16f, 0.225f, 0.21f, 0.035f}, {0.33f, 0.252f, 0.28f, 0.075f},
                         {0.52f, 0.222f, 0.2f, 0.03f}, {0.7f, 0.205f, 0.155f, 0}, {0.84f, 0.192f, 0.135f, 0},
                         {0.92f, 0.1f, 0.09f, 0}, {1.0f, 0.075f, 0.075f, 0}}};
    const std::vector<Character::Pt> spine_pts = {{J_PELVIS, {0, -0.12f, 0}, R_BODY}, {J_PELVIS, {}, R_BODY}, {J_SPINE, {}, R_BODY},
                                                  {J_CHEST, {}, R_BODY}, {J_CHEST, {0, 0.2f, 0}, R_BODY}, {J_NECK, {0, 0.08f, 0}, R_BODY}, {J_HEAD, {0, 0.07f, -0.02f}, R_BODY}};
    // Anatomy under the bloat: collarbones, a sagging chest, shoulder blades, the belly rolling
    // over the waistband. Sweep theta: 0 = the back, pi = the front, pi/2 = the right side.
    const SculptFn torso_sculpt = [](float s, float th) {
        const float f = wrap_angle(th - PI), b = wrap_angle(th);
        float d = -0.013f * gauss(s, 0.125f, 0.02f) * gauss(f, 0, 0.9f);
        for (float side : {-1.0f, 1.0f}) {
            d += 0.016f * gauss(s, 0.745f, 0.035f) * gauss(f, 0.52f * side, 0.3f);    // sagging chest
            d -= 0.009f * gauss(s, 0.69f, 0.014f) * gauss(f, 0.55f * side, 0.36f);    // the fold under it
            d += 0.008f * gauss(s, 0.875f, 0.012f) * gauss(f, 0.62f * side, 0.38f);   // collarbones
            d += 0.012f * gauss(s, 0.78f, 0.05f) * gauss(b, 0.62f * side, 0.26f);     // shoulder blades
            d += 0.012f * gauss(s, 0.22f, 0.05f) * gauss(f, 1.45f * side, 0.35f);     // bloated flanks
        }
        d -= 0.012f * gauss(s, 0.905f, 0.02f) * gauss(f, 0, 0.14f);                    // the notch at the throat
        d -= 0.008f * gauss(b, 0, 0.12f) * smooth01(0.15f, 0.3f, s) * (1 - smooth01(0.8f, 0.9f, s));   // spine
        return d;
    };
    // Blood drooled from the hanging mouth: down the throat and chest, drips running off it;
    // old blood round the belly split; canal mud dried on the waist.
    const PaintFn torso_paint = [](float s, float th, Color base) {
        if (s < 0.1f) return base;
        const float f = wrap_angle(th - PI);
        const float wob = 0.06f * std::sin(s * 23.0f) + 0.04f * std::sin(s * 51.0f + 1.0f);
        float blood = gauss(f, 0.08f + wob, 0.06f + 0.06f * (s - 0.45f)) * smooth01(0.45f, 0.62f, s);
        for (int k = 0; k < 4; ++k) {
            const float fx = -0.3f + 0.2f * k + 0.05f * std::sin(k * 7.0f), end = 0.5f - 0.1f * std::fabs(std::sin(k * 3.3f));
            blood += gauss(f, fx, 0.016f) * smooth01(end, end + 0.05f, s) * (1 - smooth01(0.8f, 0.9f, s));
        }
        blood = std::max(std::min(blood, 1.0f), 0.75f * gauss(s, 0.35f, 0.07f) * gauss(f, 0, 0.28f));
        Color c = mix(base, DRIED, blood * 0.9f);
        const float mud = (1 - smooth01(0.1f, 0.3f, s)) * (0.3f + 0.4f * vnoise({th * 3.0f, s * 9.0f, 0.5f}));
        return mix(c, Color{72, 60, 42, 255}, mud);
    };
    c.add_sweep(Sweep(30, 24, torso, MAT_WOOL, TROUSER, 0.8f).tail(0.1f, MAT_DROWNED, DSKIN).sculpt(torso_sculpt).paint(torso_paint),
                spine_pts);
    // The coat: the same spine, a size larger, torn open down the front (sweep theta 0 = the back).
    c.add_sweep(Sweep(26, 22, Profile{{{0.0f, 0.225f, 0.185f, 0}, {0.16f, 0.253f, 0.238f, 0.035f}, {0.33f, 0.28f, 0.308f, 0.075f},
                                       {0.52f, 0.25f, 0.228f, 0.03f}, {0.7f, 0.235f, 0.185f, 0}, {0.84f, 0.225f, 0.167f, 0},
                                       {0.92f, 0.15f, 0.132f, 0}, {1.0f, 0.12f, 0.115f, 0}}},
                      MAT_WOOL, COAT, 0.8f).arc(PI + 0.95f, 3 * PI - 0.95f),
                spine_pts);

    // ── Arms: bare and bloated ──
    for (float s : {-1.0f, 1.0f}) {
        const bool L = s < 0;
        c.add_sweep(Sweep(26, 12, Profile{{{0.0f, 0.078f, 0.074f, 0}, {0.2f, 0.082f, 0.08f, 0}, {0.45f, 0.07f, 0.07f, 0},
                                           {0.6f, 0.06f, 0.06f, 0}, {0.63f, 0.059f, 0.059f, 0}, {0.78f, 0.058f, 0.055f, 0},
                                           {1.0f, 0.046f, 0.041f, 0}}},
                          MAT_DROWNED, DSKIN, 0.8f)
                        .sculpt([](float sa, float th) {   // arm theta: 0 = front, pi = the point of the elbow
                            return 0.009f * gauss(sa, 0.6f, 0.025f) * gauss(wrap_angle(th - PI), 0, 0.45f) +
                                   0.006f * gauss(sa, 0.72f, 0.06f) * gauss(wrap_angle(th), 0, 1.0f) + 0.005f * gauss(sa, 0.25f, 0.06f);
                        })
                        .paint([](float sa, float th, Color base) {   // blood run down toward the hands
                            float st = 0;
                            for (int k = 0; k < 3; ++k) st += gauss(wrap_angle(th - (1.1f + 2.0f * k)), 0, 0.07f) * smooth01(0.5f + 0.1f * k, 0.72f, sa);
                            return mix(base, DRIED, std::min(1.0f, st) * 0.7f);
                        }),
                    {{J_CHEST, {0.11f * s, 0.18f, 0}, R_BODY}, {L ? J_SHO_L : J_SHO_R, {}, R_BODY},
                     {L ? J_ELB_L : J_ELB_R, {}, L ? R_UARM_L : R_UARM_R}, {L ? J_WRI_L : J_WRI_R, {}, L ? R_FARM_L : R_FARM_R}});
    }
    // ── Legs: sodden trousers; one leg torn off below the knee ──
    for (float s : {-1.0f, 1.0f}) {
        const bool L = s < 0, torn = (s == M);
        Sweep leg(24, 12, Profile{{{0.0f, 0.112f, 0.112f, 0}, {0.3f, 0.096f, 0.1f, 0}, {0.53f, 0.068f, 0.07f, 0},
                                   {0.66f, 0.078f, 0.082f, -0.006f}, {1.0f, 0.054f, 0.057f, 0}}},
                  MAT_WOOL, TROUSER, 0.93f);
        if (torn) leg.tail(0.6f, MAT_DROWNED, LIVID);
        c.add_sweep(std::move(leg), {{J_PELVIS, {0.065f * s, -0.02f, 0}, R_BODY}, {L ? J_HIP_L : J_HIP_R, {}, R_BODY},
                                     {L ? J_KNE_L : J_KNE_R, {}, L ? R_THIGH_L : R_THIGH_R},
                                     {L ? J_ANK_L : J_ANK_R, {}, L ? R_SHIN_L : R_SHIN_R}});
    }
    MeshData d;
    MeshBuilder(d).material(MAT_WOOL).color(TROUSER).drape({0, -0.035f, 0}, {0.082f, 0.086f}, {0.094f, 0.1f}, 0.075f, 3, 16, 4, 0.08f,
        [](float th) { return ragged(th, 0.25f, 0.15f, 0.4f); }, 11);
    c.add_rigid(KNE_M, SHIN_M, d);

    // ── Coat skirt, open at the front, ragged hem with a tear up the back ──
    d = {};
    MeshBuilder(d).material(MAT_WOOL).color(COAT).drape({0, 0.02f, 0.012f}, {0.25f, 0.235f}, {0.34f, 0.325f}, 0.62f, 10, 34, 7, 0.09f,
        [](float th) {
            float tear = 0.3f * std::exp(-std::pow(th - PI - 0.35f, 2.0f) / 0.012f);
            return 0.8f * ragged(th, 0.1f, 0.07f, 1.0f) - tear;
        }, 3, 0.8f, 2 * PI - 0.8f);
    c.add_rigid(J_PELVIS, R_BODY, d);

    // ── The belly, split open by gas; guts pushing out and hanging ──
    {
        auto front = [&](float s) {   // the belly surface at arc fraction s, in spine space (rest pose)
            auto p = torso.at(s);
            return Vector3{0, s * 0.78f - 0.24f, -(p[2] + p[1]) + 0.004f};
        };
        const Vector3 top = front(0.43f), mid = front(0.35f), bot = front(0.27f);
        MeshBuilder b(d = {});
        for (float side : {-1.0f, 1.0f})   // the split's rolled lips
            b.material(MAT_FLESH).color(FLESH).chain({{0.006f * side, top.y + 0.01f, top.z + 0.012f}, {0.028f * side, mid.y, mid.z - 0.004f},
                                                      {0.012f * side, bot.y - 0.01f, bot.z + 0.01f}}, {0.008f, 0.014f, 0.007f}, 8);
        b.material(MAT_VOID).color(BLACK).ellipsoid({0, mid.y, mid.z + 0.006f}, {0.022f, 0.07f, 0.012f}, 12, 10);
        b.material(MAT_GUTS).color(GUTS);
        for (int i = 0; i < 4; ++i)   // loops bulging out of the split
            b.ellipsoid({(i % 2 ? 0.012f : -0.01f), mid.y - 0.035f + i * 0.022f, mid.z - 0.012f}, {0.02f, 0.016f, 0.017f}, 10, 8);
        b.material(MAT_LEECH).color(LEECH).ellipsoid({0.12f * F, mid.y + 0.07f, mid.z + 0.05f}, {0.014f, 0.036f, 0.013f}, 10, 6);
        c.add_rigid(J_SPINE, R_BODY, d);
        c.add_dangle(J_SPINE, R_BODY, {0.004f, bot.y + 0.02f, bot.z - 0.014f}, {0.1f, -1, -0.25f}, 9, 0.048f,
                     Profile{{{0, 0.015f, 0.015f, 0}, {1, 0.01f, 0.01f, 0}}}, MAT_GUTS, GUTS, 0.975f);
        c.add_dangle(J_SPINE, R_BODY, {0.024f, bot.y + 0.035f, bot.z - 0.012f}, {-0.2f, -1, -0.2f}, 7, 0.045f,
                     Profile{{{0, 0.013f, 0.013f, 0}, {1, 0.009f, 0.009f, 0}}}, MAT_GUTS, Color{150, 100, 98, 255}, 0.97f);
    }
    // Neck: a torn gash and a leech.
    d = {};
    {
        MeshBuilder b(d);
        b.material(MAT_FLESH).color(FLESH).ellipsoid({0.056f * F, 0.05f, -0.02f}, {0.012f, 0.032f, 0.016f}, 10, 8);
        b.material(MAT_VOID).color(BLACK).ellipsoid({0.062f * F, 0.05f, -0.022f}, {0.006f, 0.024f, 0.01f}, 8, 6);
        b.material(MAT_LEECH).color(LEECH).ellipsoid({0.05f * M, 0.045f, -0.055f}, {0.013f, 0.034f, 0.013f}, 10, 6);
    }
    c.add_rigid(J_NECK, R_BODY, d);

    // ── The head ──
    const Vector3 hc{0, 0.1f, -0.02f}, hr{0.093f, 0.112f, 0.103f};
    c.head_c_ = hc;
    const Vector3 eyeL = dirn(-0.36f, 0.1f, -0.93f), eyeR = dirn(0.36f, 0.1f, -0.93f), cheek = dirn(0.66f * F, -0.3f, -0.69f);
    d = {};
    {
        MeshBuilder b(d);
        const Bump skull = features({
            {{0, 0.3f, -0.95f}, 0.2f, 0.01f},                                           // brow swelling
            {eyeR, 0.11f, -0.024f}, {eyeL, 0.11f, -0.024f},                             // deep sockets
            {{0.36f, 0.22f, -0.9f}, 0.065f, 0.02f}, {{-0.36f, 0.22f, -0.9f}, 0.065f, 0.02f},   // swollen upper lids
            {{0.36f, -0.02f, -0.93f}, 0.06f, 0.013f}, {{-0.36f, -0.02f, -0.93f}, 0.06f, 0.013f},  // puffy lower lids
            {{0.38f * M, 0.17f, -0.91f}, 0.05f, 0.012f},                                // one lid drooping further
            {{0, -0.02f, -1}, 0.07f, -0.018f},                                          // the nose rotted to a hollow
            {{0.62f, -0.22f, -0.76f}, 0.2f, 0.015f}, {{-0.62f, -0.22f, -0.76f}, 0.2f, 0.015f},   // bloated cheeks
            {{0, -0.5f, -0.86f}, 0.14f, -0.02f},                                        // lips gone: teeth stand proud
            {{0.85f * M, 0.25f, -0.2f}, 0.3f, 0.016f},                                  // one side more swollen
            {{0, -0.82f, -0.52f}, 0.24f, -0.035f},                                      // the palate, open when the jaw hangs
            {cheek, 0.075f, -0.016f},                                                   // the cheek torn through
        });
        b.material(MAT_DROWNED).color(DSKIN).ellipsoid(hc, hr, 48, 32, skull, [&](Vector3 dd) {
            // The scalp slid back: bare skull from the brow to the crown, ragged where it tore.
            float edge = 0.4f + 0.07f * std::sin(dd.x * 17.0f + 1.3f) + 0.05f * std::sin(dd.z * 23.0f + dd.x * 9.0f);
            if (dd.z < 0.3f && dd.y > edge)
                return Paint{MAT_BONE, mix(BONE, Color{118, 98, 74, 255}, vnoise(Vector3Scale(dd, 9)) * 0.75f)};   // stained skull
            if (dd.y < -0.6f && dd.z < 0.1f) return Paint{MAT_FLESH, Color{44, 13, 15, 255}};                   // inside the mouth
            const float ch = Vector3Distance(dd, cheek);
            if (ch < 0.07f) return Paint{MAT_FLESH, Color{76, 20, 20, 255}};                                    // raw edges of the tear
            float e = std::min(Vector3Distance(dd, eyeL), Vector3Distance(dd, eyeR));
            Color col = mix(Color{40, 28, 40, 255}, DSKIN, smooth01(0.08f, 0.34f, e));                          // bruised sockets
            float m = Vector3Distance(dd, dirn(0, -0.52f, -0.85f));                                                // lips rotted away
            col = mix(col, Color{68, 34, 36, 255}, (1 - smooth01(0.1f, 0.26f, m)) * 0.85f);
            col = mix(col, Color{70, 22, 22, 255}, (1 - smooth01(0.07f, 0.13f, ch)) * 0.9f);                   // bruised round the tear
            if (dd.z < 0.3f) col = mix(col, Color{64, 20, 20, 255}, (1 - smooth01(0.0f, 0.1f, edge - dd.y)) * 0.9f);   // torn scalp margin
            return Paint{MAT_DROWNED, col};
        });
        // Milky, bulging eyes; a ghost of the iris; swollen lids.
        for (float s : {-1.0f, 1.0f}) {
            const Vector3 ec{0.0335f * s, 0.109f, -0.093f};
            b.material(MAT_DEAD_EYE).color(EYE).ellipsoid(ec, {0.0158f, 0.0158f, 0.0158f}, 16, 12, {}, [](Vector3 q) {
                float r = std::sqrt(q.x * q.x + q.y * q.y);
                return Paint{MAT_DEAD_EYE, (q.z < -0.8f && r > 0.28f && r < 0.5f) ? IRIS_GHOST : EYE};
            });
        }
        // The nose: a rotted hole with a bony bridge.
        b.material(MAT_FLESH).color(DRIED).ellipsoid({0, 0.083f, -0.111f}, {0.017f, 0.02f, 0.008f}, 12, 8);
        for (float s : {-1.0f, 1.0f})
            b.material(MAT_VOID).color(BLACK).ellipsoid({0.0055f * s, 0.079f, -0.1155f}, {0.0068f, 0.0115f, 0.006f}, 10, 8);
        b.material(MAT_BONE).color(BONE).ellipsoid({0, 0.104f, -0.118f}, {0.006f, 0.013f, 0.005f}, 8, 6);
        // Upper jaw: raw gums and teeth, lips long gone; the throat behind them.
        b.material(MAT_FLESH).color(Color{66, 22, 24, 255}).ellipsoid({0, 0.054f, -0.088f}, {0.04f, 0.0095f, 0.021f}, 14, 8);
        b.material(MAT_VOID).color(BLACK).ellipsoid({0, 0.028f, -0.05f}, {0.022f, 0.015f, 0.028f}, 12, 8);
        teeth(d, {0, 0.046f, -0.064f}, 0.04f, 0.044f, -0.95f, 0.95f, 11, true, unsigned(variant) + 1);
        // The cheek torn through: you can see the molars.
        MeshBuilder(d).material(MAT_VOID).color(BLACK).ellipsoid(on_ellipsoid(hc, hr, cheek, 0.024f), {0.015f, 0.011f, 0.011f}, 12, 8);
        teeth(d, {0.047f * F, 0.047f, -0.066f}, 0.0f, 0.0f, 0.0f, 0.0f, 1, true, 9);
        teeth(d, {0.05f * F, 0.047f, -0.058f}, 0.0f, 0.0f, 0.0f, 0.0f, 1, true, 12);
        // The scalp: slid back off the skull, bunched and sagging over the nape.
        b.material(MAT_HAIR).color(HAIR).ellipsoid(hc, Vector3AddValue(hr, 0.008f), 40, 26,
            [](Vector3 q) {   // sagging toward the nape, lumpy with wet clumps
                return 0.003f + 0.026f * std::max(0.0f, -q.y) + 0.006f * vnoise(Vector3Scale(q, 11.0f));
            },
            [](Vector3 q) {
                float edge = 0.38f + 0.14f * std::sin(q.x * 11.0f + 0.7f) + 0.08f * std::sin(q.y * 19.0f);
                return Paint{(q.z > edge && q.y > -0.66f) ? MAT_HAIR : -1, HAIR};
            });
    }
    mussels(d, on_ellipsoid(hc, hr, {0.88f * M, 0.3f, -0.12f}, -0.006f), dirn(0.88f * M, 0.3f, -0.12f), 9, 0.026f, 5u + unsigned(variant));
    c.add_rigid(J_HEAD, R_HEAD, d);
    // Wet hair hanging from the scalp flap, two strands falling across the face.
    for (int i = 0; i < 11; ++i) {
        float th = PI + (float(i) - 5.0f) * 0.27f;   // round the back of the head (0 = front)
        Vector3 dir{std::sin(th), -0.3f - 0.1f * float(i % 2), -std::cos(th)};
        Vector3 at = on_ellipsoid(hc, Vector3AddValue(hr, 0.02f), dir, 0.0f);
        c.add_dangle(J_HEAD, R_HEAD, at, {dir.x * 0.15f, -1, dir.z * 0.15f}, 5 + (i % 4), 0.045f,
                     Profile{{{0, 0.0065f, 0.0022f, 0}, {1, 0.0025f, 0.0015f, 0}}}, MAT_HAIR, HAIR, 0.94f, 0.015f);
    }
    for (float k : {0.0f, 1.0f})   // two strands plastered across the face
        c.add_dangle(J_HEAD, R_HEAD, {(0.052f + 0.014f * k) * M, 0.19f, -0.045f + 0.02f * k}, {0.1f * M, -1, -0.25f}, 7, 0.038f,
                     Profile{{{0, 0.0055f, 0.002f, 0}, {1, 0.0022f, 0.0015f, 0}}}, MAT_HAIR, HAIR, 0.94f, 0.02f);

    // ── The jaw: dislocated, hanging; lower teeth; the tongue lolls over them ──
    d = {};
    {
        MeshBuilder b(d);
        b.material(MAT_DROWNED).color(DSKIN).ellipsoid({0, -0.034f, -0.052f}, {0.066f, 0.042f, 0.064f}, 24, 14,
            features({{{0, -0.6f, -0.8f}, 0.2f, 0.008f}}),
            [](Vector3 q) {
                Color col = mix(DSKIN, Color{60, 36, 36, 255}, smooth01(-0.1f, 0.3f, q.y));
                float run = std::max(gauss(q.x, 0.34f, 0.07f), gauss(q.x, -0.28f, 0.05f)) * smooth01(-0.7f, 0.1f, q.y);
                return Paint{q.y < 0.3f ? MAT_DROWNED : -1, mix(col, DRIED, run * 0.85f)};
            });
        b.material(MAT_FLESH).color(Color{30, 10, 12, 255}).ellipsoid({0, -0.022f, -0.052f}, {0.064f, 0.011f, 0.062f}, 16, 6);   // the floor of the mouth
        b.material(MAT_FLESH).color(Color{66, 22, 24, 255}).ellipsoid({0, -0.012f, -0.092f}, {0.038f, 0.008f, 0.017f}, 12, 6);   // lower gums
        teeth(d, {0, -0.004f, -0.052f}, 0.042f, 0.046f, -0.85f, 0.85f, 9, false, unsigned(variant) + 21);
    }
    c.add_rigid(J_JAW, R_JAW, d);
    c.add_dangle(J_JAW, R_JAW, {0.004f, -0.01f, -0.07f}, {0.1f, -0.35f, -1}, 5, 0.024f,
                 Profile{{{0, 0.021f, 0.011f, 0}, {0.6f, 0.019f, 0.01f, 0}, {1, 0.011f, 0.007f, 0}}}, MAT_TONGUE, TONGUE, 0.9f, 0.08f);
    for (float s : {-1.0f, 1.0f})   // skin and tendon stretched between skull and hanging jaw
        c.add_dangle(J_HEAD, R_JAW, {0.066f * s, 0.058f, -0.066f}, {0, -1, 0}, 5, 0.02f,
                     Profile{{{0, 0.006f, 0.004f, 0}, {0.5f, 0.0035f, 0.0025f, 0}, {1, 0.006f, 0.004f, 0}}}, MAT_DERMIS, DERMIS,
                     0.9f, 0.0f, J_JAW, {0.05f * s, -0.018f, -0.06f});

    // ── Hands: one degloved (raw beneath, the skin hanging off in a torn cuff), one bleached and wrinkled ──
    for (float s : {-1.0f, 1.0f}) {
        const bool L = s < 0, degloved = (s == M);
        d = {};
        HandStyle h;
        h.scale = 1.45f; h.finger_len = 0.155f; h.curl = degloved ? 0.25f : 0.4f;
        h.mat = degloved ? MAT_DERMIS : MAT_SLOUGH; h.skin = degloved ? DERMIS : SLOUGH;
        h.tip_mat = MAT_ROT; h.tip = ROT;
        hand(d, s, h);
        if (degloved)
            MeshBuilder(d).material(MAT_SLOUGH).color(SLOUGH).drape({0, 0.02f, -0.004f}, {0.05f, 0.047f}, {0.058f, 0.055f}, 0.075f, 4, 16, 4, 0.12f,
                [](float th) { return ragged(th, 0.3f, 0.2f, 2.0f); }, 13);
        c.add_rigid(L ? J_WRI_L : J_WRI_R, L ? R_FARM_L : R_FARM_R, d);
    }
    for (float x : {-0.024f, 0.026f})   // the loose skin hangs past the fingers
        c.add_dangle(WRI_M, FARM_M, {x, -0.055f, 0.004f}, {0, -1, 0.1f}, 5, 0.034f,
                     Profile{{{0, 0.019f, 0.0025f, 0}, {1, 0.008f, 0.002f, 0}}}, MAT_SLOUGH, SLOUGH, 0.93f);
    (void)WRI_F;
    // Compound fracture: the forearm bone through the skin.
    d = {};
    {
        MeshBuilder b(d);
        b.material(MAT_FLESH).color(FLESH).ellipsoid({0.045f * F, -0.163f, -0.019f}, {0.026f, 0.021f, 0.023f}, 12, 8);
        b.material(MAT_BONE).color(BONE).chain({{0.012f * F, -0.13f, 0.0f}, {0.05f * F, -0.168f, -0.022f}, {0.08f * F, -0.2f, -0.037f}},
                                               {0.013f, 0.0105f, 0.0035f}, 8);
    }
    c.add_rigid(ELB_F, FARM_F, d);

    // ── Feet: bare, swollen, livid ──
    for (float s : {-1.0f, 1.0f}) {
        d = {};
        MeshBuilder b(d);
        b.material(MAT_DROWNED).color(LIVID).ellipsoid({0, -0.045f, -0.055f}, {0.058f, 0.05f, 0.132f}, 16, 10);
        for (int t = 0; t < 5; ++t) {
            float x = (-0.036f + t * 0.018f) * -s, big = t == 0 ? 1.35f : 1.0f - t * 0.06f;
            Vector3 tp{x, -0.073f, -0.176f + t * 0.006f};
            b.material(MAT_DROWNED).color(LIVID).ellipsoid(tp, Vector3Scale({0.0105f, 0.0105f, 0.017f}, big), 8, 6);
            b.material(MAT_ROT).color(ROT).ellipsoid(Vector3Add(tp, {0, 0.006f * big, -0.008f * big}), Vector3Scale({0.0075f, 0.003f, 0.007f}, big), 8, 4);
        }
        c.add_rigid(s < 0 ? J_ANK_L : J_ANK_R, s < 0 ? R_SHIN_L : R_SHIN_R, d);
    }

    // ── Canal growth: mussels, leeches, weed ──
    d = {};
    mussels(d, {0.19f * M, 0.215f, 0.05f}, dirn(0.5f * M, 0.8f, 0.3f), 14, 0.05f, 31u + unsigned(variant));
    c.add_rigid(J_CHEST, R_BODY, d);
    d = {};
    mussels(d, {0.02f * F, -0.17f, -0.1f}, dirn(0.25f * F, 0, -1), 8, 0.035f, 47u + unsigned(variant));
    c.add_rigid(HIP_F, THIGH_F, d);
    d = {};
    MeshBuilder(d).material(MAT_LEECH).color(LEECH).ellipsoid({0.07f * F, -0.16f, -0.035f}, {0.012f, 0.034f, 0.012f}, 10, 6);
    c.add_rigid(SHO_F, UARM_F, d);
    for (int i = 0; i < 3; ++i)   // weed caught on the coat's hem at the back
        c.add_dangle(J_PELVIS, R_BODY, {(-0.14f + 0.13f * i), -0.5f + 0.04f * (i % 2), 0.28f}, {0, -1, 0.3f}, 6, 0.042f,
                     Profile{{{0, 0.013f, 0.0025f, 0}, {1, 0.004f, 0.002f, 0}}}, MAT_WEED, WEED, 0.95f);
    c.add_dangle(ELB_F, FARM_F, {0.04f * F, -0.1f, -0.045f}, {0.2f * F, -1, -0.2f}, 6, 0.04f,
                 Profile{{{0, 0.012f, 0.0025f, 0}, {1, 0.004f, 0.002f, 0}}}, MAT_WEED, WEED, 0.95f);

    // Colliders keep the guts, hair and weed outside the body.
    c.colliders_ = {{J_PELVIS, J_CHEST, {0, 0.02f, 0}, {0, 0.12f, 0.02f}, 0.18f},
                    {J_HIP_L, J_KNE_L, {}, {}, 0.1f}, {J_HIP_R, J_KNE_R, {}, {}, 0.1f},
                    {J_HEAD, J_HEAD, hc, hc, 0.113f}, {J_NECK, J_HEAD, {}, {}, 0.075f}};
    return c;
}

}  // namespace dw
