// damned_waters/engine/src/cast_survivor.cpp
// Purpose: the survivor. His body, clothes, face and hair cap come from
// engine/assets/characters/survivor.dwc (built from MakeHuman's CC0 human by
// tools/characters); here we add what moves or is held: physics locs, the
// backpack, the flashlight on its strap, and his guns (cast_guns.cpp).
#include <cmath>

#include "cast_common.hpp"
#include "cast_guns.hpp"
#include "dw/room_spec.hpp"

namespace dw {
using namespace cast;
namespace {
const Color BLACK_PARTS{22, 22, 24, 255}, PACK{30, 32, 32, 255}, TRIM{46, 48, 46, 255};

void backpack(MeshData& d, Vector3 at) {
    MeshBuilder b(d);
    const Vector3 c = Vector3Add(at, {0, -0.1f, 0.13f});
    b.material(MAT_CLOTH).color(PACK).box(c, {0.155f, 0.2f, 0.075f}, 0.45f, 24, 16);   // waxed canvas
    b.color(TRIM).box(Vector3Add(c, {0, -0.07f, 0.062f}), {0.11f, 0.08f, 0.03f}, 0.4f, 20, 12);   // front pocket
    b.material(MAT_METAL).color(BLACK_PARTS).tube(Vector3Add(c, {-0.1f, 0.15f, 0.05f}), Vector3Add(c, {0.1f, 0.15f, 0.05f}), 0.0035f, 0.0035f, 6);
    b.material(MAT_CLOTH).color(TRIM).chain({Vector3Add(c, {-0.04f, 0.2f, -0.01f}), Vector3Add(c, {0, 0.235f, -0.005f}),
                                             Vector3Add(c, {0.04f, 0.2f, -0.01f})}, {0.008f, 0.008f, 0.008f}, 6, 0.4f);   // top handle
}

// An angle-head flashlight clipped upright to the backpack strap, its head bent forward so the
// beam goes where he faces. `at` is in front of the strap (chest space: -Z is forward).
void flashlight(MeshData& d, Vector3 at) {
    MeshBuilder b(d);
    const Color OLIVE{64, 68, 52, 255};
    auto p = [&at](float x, float y, float z) { return Vector3Add(at, {x, y, z}); };
    b.material(MAT_METAL).color(OLIVE).tube(p(0, -0.06f, 0.004f), p(0, 0.03f, 0.004f), 0.0135f, 0.0135f, 14);   // the body
    b.material(MAT_RUBBER).color(BLACK_PARTS).tube(p(0, -0.066f, 0.004f), p(0, -0.058f, 0.004f), 0.0142f, 0.0142f, 14);   // tail cap
    b.material(MAT_METAL).color(OLIVE).box(p(0, 0.044f, -0.008f), {0.017f, 0.017f, 0.024f}, 0.35f, 12, 10);        // the angled head
    b.material(MAT_METAL).color(BLACK_PARTS).tube(p(0, 0.044f, -0.03f), p(0, 0.044f, -0.036f), 0.0185f, 0.0185f, 16);   // bezel
    b.material(MAT_LAMP).color(Color{255, 238, 204, 255}).ellipsoid(p(0, 0.044f, -0.0365f), {0.0155f, 0.0155f, 0.002f}, 14, 6);
    b.material(MAT_RUBBER).color(BLACK_PARTS).box(p(0.0145f, 0.018f, 0.004f), {0.0035f, 0.007f, 0.006f}, 0.4f, 8, 6);   // switch
    b.material(MAT_METAL).color(BLACK_PARTS).box(p(0, -0.01f, 0.021f), {0.009f, 0.035f, 0.0025f}, 0.4f, 8, 8);   // clip on the strap
}
}  // namespace

Character build_survivor() {
    Character c;
    c.kind = Kind::Survivor;
    c.thickness_ = 0.12f;
    if (!c.load_body(repo_root() + "/engine/assets/characters/survivor.dwc")) return c;
    c.head_c_ = {0, 0.075f, -0.02f};
    // The skull, fitted to this scalp (tools/characters measures it): a short capsule running front
    // to back, since a head is longer than it is wide. The locs hug it and collide with it, along
    // with the neck, shoulders and upper back.
    const Vector3 skA{0, 0.07f, -0.01f}, skB{0, 0.07f, 0.02f};
    const float skR = 0.08f;
    c.colliders_ = {{J_HEAD, J_HEAD, skA, skB, skR},
                    {J_NECK, J_HEAD, {0, 0, 0.005f}, {0, 0, 0.01f}, 0.058f},
                    {J_SHO_L, J_SHO_R, {0, 0.035f, 0.02f}, {0, 0.035f, 0.02f}, 0.075f},
                    {J_CHEST, J_CHEST, {0, 0.06f, 0.07f}, {0, 0.06f, 0.07f}, 0.14f},
                    {J_CHEST, J_CHEST, {-0.07f, 0.03f, -0.1f}, {0.07f, 0.03f, -0.1f}, 0.11f},   // the front of the hoodie
                    {J_HEAD, J_HEAD, {0, 0.0f, -0.035f}, {0, 0.1f, -0.035f}, 0.08f}};          // the face
    auto axis_at = [&](Vector3 p) { return Vector3{0, skA.y, std::clamp(p.z, skA.z, skB.z)}; };   // nearest point on the skull's axis
    // Medium locs grown in sections all over the scalp, like the director's reference (portrait 3),
    // worn swept back: off the brow, up over the top and down the back of the head, fanning out to
    // the sides as they go, so the face stays clear and from above (where the game's cameras sit)
    // they lie over one another like thatch rather than standing out round the crown like spokes.
    // Each root lifts a little off the scalp (locs have body); a loc falls once it clears the
    // skull's widest band; the ones rooted further forward lie over the ones behind. At the temples
    // they hang down and frame the face; two fall forward across the brow. No two keep quite to the
    // flow, or are quite the same length or thickness.
    Character::Strands locs;
    locs.joint = J_HEAD;
    locs.n = 14;
    locs.sides = 8;
    locs.mat = MAT_LOCS;
    locs.sub = 2;          // a smooth curve through the points
    locs.aux_along = true;
    locs.sides = 10;
    locs.lump = 0.13f;     // palm-rolled: it swells and thins
    locs.wave = 0.0013f;   // and wanders a little off its line
    locs.root = 0.78f;     // slimmer new growth at the scalp
    locs.fluff = 1.3f;     // the margin the shader frays into loose hairs
    locs.taper = 0.26f;
    locs.col = {37, 30, 25, 255};
    locs.tip = {70, 52, 38, 255};   // sun-bleached ends
    unsigned h = 0x2545F491u;
    auto rnd = [&h]() { h ^= h << 13; h ^= h >> 17; h ^= h << 5; return float(h & 0xFFFF) / 65535.0f; };
    const Vector3 crown{0.0f, skA.y + skR * 0.95f, 0.018f};
    const Vector3 faceA{0, 0.0f, -0.035f}, faceB{0, 0.1f, -0.035f};   // the face, for the forelocks to lie over
    const float faceR = 0.08f;
    auto on_skull = [&](Vector3 p, Vector3 w) {   // w laid along the skull's surface at p
        const Vector3 radial = Vector3Normalize(Vector3Subtract(p, axis_at(p)));
        w = Vector3Subtract(w, Vector3Scale(radial, Vector3DotProduct(w, radial)));
        return Vector3LengthSqr(w) > 1e-8f ? Vector3Normalize(w) : Vector3{0, -1.0f, 0};
    };
    auto push_out = [](Vector3 p, Vector3 a, Vector3 b, float r) {   // p moved out of the capsule a-b of radius r
        const Vector3 ab = Vector3Subtract(b, a);
        const float t = std::clamp(Vector3DotProduct(Vector3Subtract(p, a), ab) / std::max(Vector3LengthSqr(ab), 1e-8f), 0.0f, 1.0f);
        const Vector3 q = Vector3Add(a, Vector3Scale(ab, t)), d = Vector3Subtract(p, q);
        const float l = Vector3Length(d);
        return l < r ? Vector3Add(q, Vector3Scale(d, r / std::max(l, 1e-5f))) : p;
    };
    int forelocks = 0;
    auto frontness = [](Vector3 p) { return std::clamp((0.095f - p.z) / 0.175f, 0.0f, 1.0f); };   // 1 over the brow, 0 at the nape
    for (const auto& a : c.anchors_) {
        if (a.name.rfind("loc", 0) != 0) continue;
        const Vector3 n = Vector3Normalize(a.dir), p0 = a.pos;
        const float height = std::clamp((p0.y - skA.y) / skR, 0.0f, 1.0f);   // 1 at the crown, 0 at ear level
        const bool front = p0.z < -0.035f;
        const bool forelock = front && forelocks < 2 && p0.x > 0.0f && p0.x < 0.05f && p0.z < -0.055f;
        forelocks += forelock;
        const float side = p0.x < 0 ? -1.0f : 1.0f;
        const float turn = (rnd() - 0.5f) * 0.7f;   // how far this one strays from the flow (radians)
        // Which way the loc heads over the scalp from point p: back (and, on the brow, up first),
        // out to its own side, a little away from the crown; forelocks across the brow to the temple.
        auto away = [&](Vector3 p) {
            if (forelock) return Vector3Normalize({0.9f * side, -0.55f, -0.3f});
            const Vector3 radial = Vector3Normalize(Vector3Subtract(p, axis_at(p)));
            const float f = frontness(p);
            Vector3 flow = Vector3Scale(Vector3Normalize(Vector3Subtract(p, crown)), 0.45f * (1.0f - f));
            flow = Vector3Add(flow, {side * (0.25f + 0.55f * (1.0f - height)), 0.85f * f * (1.0f - std::max(radial.y, 0.0f)) - 0.2f * (1.0f - f), 0.9f});
            return Vector3RotateByAxisAngle(on_skull(p, flow), radial, turn);
        };
        // The ones off the brow have the whole head to cross before they hang.
        const float len = forelock ? 0.1f + 0.03f * rnd() : 0.18f + 0.09f * rnd() + 0.08f * frontness(p0) * height;
        const float seg = len / float(locs.n - 1);
        const float radius = 0.0054f + 0.0022f * rnd();
        const float upstream = std::clamp(0.35f * height + 0.65f * frontness(p0), 0.0f, 1.0f);
        const float R = skR + radius + 0.003f + 0.015f * upstream;   // rooted further forward: over the ones behind
        Vector3 p = Vector3Subtract(p0, Vector3Scale(n, 0.003f));      // rooted in the scalp, no gap
        locs.anchor.push_back(p);
        locs.rest.push_back(p);
        Vector3 dir = Vector3Normalize(Vector3Add(Vector3Scale(n, 0.4f), Vector3Scale(away(p0), 0.8f)));   // the root lifts
        for (int i = 1; i < locs.n; ++i) {
            const Vector3 radial = Vector3Normalize(Vector3Subtract(p, axis_at(p)));
            const float leave = forelock ? 0.6f : std::clamp((0.3f - radial.y) / 0.4f, 0.0f, 1.0f);
            const Vector3 fall = Vector3Normalize({radial.x * 0.12f, -1.0f, radial.z * 0.1f});
            const Vector3 want = Vector3Normalize(Vector3Lerp(away(p), fall, leave));
            dir = Vector3Normalize(Vector3Lerp(dir, want, i == 1 ? 0.25f : 0.45f));
            p = Vector3Add(p, Vector3Scale(dir, seg));
            if (!forelock) {   // over the skull it lies on the hair beneath it, it doesn't stand off the head
                const Vector3 ax = axis_at(p), off = Vector3Subtract(p, ax);
                const float d = Vector3Length(off), most = R + 0.004f + 0.05f * leave;
                if (d > most) {
                    p = Vector3Add(ax, Vector3Scale(off, most / d));
                    dir = Vector3Normalize(Vector3Subtract(p, locs.rest.back()));
                }
            }
            p = push_out(p, skA, skB, i < 2 ? skR : R);                 // never inside the skull (or the locs below)
            p = push_out(p, faceA, faceB, faceR + radius + 0.004f);      // nor the face
            locs.rest.push_back(p);
        }
        locs.seg.push_back(seg);
        locs.radius.push_back(radius);
        locs.stiff.push_back(forelock ? 0.28f : 0.22f);
        locs.shade.push_back(0.66f + 0.34f * upstream);   // under the ones that lie over it: in their shade
    }
    c.add_strands(std::move(locs));
    MeshData d;
    // The guns (cast_guns.cpp), each in two parts: the one that moves when it's worked (the M92FS's
    // slide, the 870's fore-end) and the rest.
    cast::GunParts gun = cast::m92fs(Character::pistol_hold());   // held as --fitgrips fitted it
    c.add_rigid(J_WRI_R, R_FARM_R, gun.fixed, 1);   // shown while the M92FS is in hand
    c.add_rigid(J_WRI_R, R_FARM_R, gun.moving, 1, 1, gun.travel);
    c.add_rigid(J_WRI_R, R_FARM_R, gun.load, 1, 3);   // its magazine (out and in again when he reloads)
    gun = cast::r870(Character::shotgun_hold());
    c.add_rigid(J_WRI_R, R_FARM_R, gun.fixed, 2);   // ... or the Remington 870
    c.add_rigid(J_WRI_R, R_FARM_R, gun.moving, 2, 2, gun.travel);
    c.add_rigid(J_WRI_R, R_FARM_R, gun.load, 2, 3);   // a shell for it, while he loads one
    if (const auto* a = c.anchor("backpack")) { d = {}; backpack(d, a->pos); c.add_rigid(a->joint, R_BODY, d); }
    if (const auto* a = c.anchor("flashlight")) {
        d = {};
        flashlight(d, a->pos);
        c.add_rigid(a->joint, R_BODY, d);
        c.lamp_joint_ = a->joint;
        c.lamp_off_ = Vector3Add(a->pos, {0, 0.044f, -0.04f});   // just in front of the lens
    }
    for (const char* name : {"drawstring-1", "drawstring1"})   // the hoodie's cords, swinging; thicker aglets at the ends
        if (const auto* a = c.anchor(name))
            c.add_dangle(a->joint, R_BODY, a->pos, {0, -1, -0.15f}, 8, 0.027f,
                         Profile{{{0, 0.0034f, 0.0034f, 0}, {0.86f, 0.0032f, 0.0032f, 0}, {0.9f, 0.0042f, 0.0042f, 0}, {1, 0.0042f, 0.0042f, 0}}},
                         MAT_COTTON, Color{196, 186, 166, 255}, 0.93f, 0.02f);
    return c;
}

}  // namespace dw
