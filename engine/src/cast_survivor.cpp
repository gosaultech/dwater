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
    // Medium locs grown in sections all over the scalp, like the director's reference (portrait 3):
    // each root lifts off the scalp (locs have body), flows away from the crown, and falls once it
    // clears the skull's widest band. Locs rooted higher lie over the ones below, which gives the
    // head its volume. At the front they part to the sides and frame the face; three fall forward
    // over the forehead.
    Character::Strands locs;
    locs.joint = J_HEAD;
    locs.n = 14;
    locs.sides = 8;
    locs.mat = MAT_LOCS;
    locs.col = {46, 33, 24, 255};
    locs.tip = {98, 70, 46, 255};   // sun-bleached ends
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
    for (const auto& a : c.anchors_) {
        if (a.name.rfind("loc", 0) != 0) continue;
        const Vector3 n = Vector3Normalize(a.dir), p0 = a.pos;
        const float height = std::clamp((p0.y - skA.y) / skR, 0.0f, 1.0f);   // 1 at the crown, 0 at ear level
        const bool front = p0.z < -0.035f;
        const bool forelock = front && forelocks < 3 && p0.x > -0.012f && p0.x < 0.05f && p0.z < -0.055f;
        forelocks += forelock;
        const float side = p0.x < 0 ? -1.0f : 1.0f;
        // Which way the loc heads over the scalp from point p: away from the crown; at the front, out
        // to the sides (the face stays clear); forelocks forward and down over the brow.
        auto away = [&](Vector3 p) {
            if (forelock) return Vector3Normalize({0.8f * side, -0.6f, -0.45f});   // across the brow toward the temple
            Vector3 w = on_skull(p, Vector3Subtract(p, crown));
            if (front) w = on_skull(p, Vector3Add(Vector3Scale(w, 0.55f), {side * 1.0f, -0.25f, 0.2f}));
            return w;
        };
        const float len = forelock ? 0.1f + 0.03f * rnd() : 0.16f + 0.06f * rnd();   // the jaw at the front, the neck behind
        const float seg = len / float(locs.n - 1);
        const float radius = 0.0052f + 0.0018f * rnd();
        const float R = skR + radius + 0.003f + 0.011f * height;   // higher roots lie over lower ones
        Vector3 p = Vector3Subtract(p0, Vector3Scale(n, 0.003f));      // rooted in the scalp, no gap
        locs.anchor.push_back(p);
        locs.rest.push_back(p);
        Vector3 dir = Vector3Normalize(Vector3Add(Vector3Scale(n, 0.6f), Vector3Scale(away(p0), 0.6f)));   // the root lifts
        for (int i = 1; i < locs.n; ++i) {
            const Vector3 radial = Vector3Normalize(Vector3Subtract(p, axis_at(p)));
            const float leave = forelock ? 0.6f : std::clamp((0.3f - radial.y) / 0.4f, 0.0f, 1.0f);
            const Vector3 fall = Vector3Normalize({radial.x * 0.12f, -1.0f, radial.z * 0.1f});
            const Vector3 want = Vector3Normalize(Vector3Lerp(away(p), fall, leave));
            dir = Vector3Normalize(Vector3Lerp(dir, want, i == 1 ? 0.25f : 0.45f));
            p = Vector3Add(p, Vector3Scale(dir, seg));
            p = push_out(p, skA, skB, i < 2 ? skR : R);                 // never inside the skull (or the locs below)
            p = push_out(p, faceA, faceB, faceR + radius + 0.004f);      // nor the face
            locs.rest.push_back(p);
        }
        locs.seg.push_back(seg);
        locs.radius.push_back(radius);
        locs.stiff.push_back(forelock ? 0.28f : 0.22f);
    }
    c.add_strands(std::move(locs));
    MeshData d;
    // The guns (cast_guns.cpp), each in two parts: the one that moves when it's worked (the M92FS's
    // slide, the 870's fore-end) and the rest.
    cast::GunParts gun = cast::m92fs(Character::pistol_hold());   // held as --fitgrips fitted it
    c.add_rigid(J_WRI_R, R_FARM_R, gun.fixed, 1);   // shown while the M92FS is in hand
    c.add_rigid(J_WRI_R, R_FARM_R, gun.moving, 1, 1, gun.travel);
    gun = cast::r870(Character::shotgun_hold());
    c.add_rigid(J_WRI_R, R_FARM_R, gun.fixed, 2);   // ... or the Remington 870
    c.add_rigid(J_WRI_R, R_FARM_R, gun.moving, 2, 2, gun.travel);
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
