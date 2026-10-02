// damned_waters/engine/src/cast_guns.cpp
// Purpose: the survivor's guns, modelled from the real ones as hard-surface parts: each part's
// side view is drawn as an outline in millimetres and extruded to its width with rounded edges
// (MeshBuilder::slab), the way a gun is blocked out in CAD.
//  * Beretta M92FS Inox: 202 mm of slide over a 125 mm barrel, 142 mm high, 38 mm across the
//    safety levers. Its side view was matched to reference photos: a camera was fitted to each
//    photo and the silhouettes compared until they agreed. Satin stainless slide and barrel, a
//    slightly greyer alloy frame, black controls and sights with three white dots, dark grey
//    stippled rubber grips with two screws and the medallion.
//  * Remington 870, the classic police gun of the reference photos: an 18.5-inch plain barrel with
//    a bead at the muzzle, 38 inches overall, a 14-inch length of pull, six in the extended tube
//    and one in the chamber. Blued steel with the bolt bright in the ejection port and a gold
//    trigger, an oiled walnut stock and fore-end, a black recoil pad. (Its trigger group sits at
//    the back of the receiver, the ejection port in the front half, as in the photos.)
// Gun space: u runs forward along the bore (the pistol's from the rear of the frame's rails, 6 mm
// behind the slide; the shotgun's from the back of the receiver), v up from the bore's
// centreline, w across to the gun's right (all mm). It's placed in the right hand's wrist space,
// where the barrel runs down the hand (-y) above the web of the thumb (-z), the grip through the
// fist.
#include "cast_guns.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <vector>

namespace dw::cast {
namespace {
constexpr float MM = 0.001f;

// ── Beretta M92FS Inox ──────────────────────────────────────────────────────────
// The bore 66 mm above the wrist, the back of the slide 37.5 mm ahead of it (the muzzle lands
// 240 mm down the hand).
constexpr float P_Y0 = -0.0315f, P_Z0 = -0.066f;
Outline pistol(const Outline& o) { return o.scaled(-MM, P_Y0, P_Z0); }
Vector3 pistol_at(float u, float v, float w = 0) { return {w * MM, P_Y0 - u * MM, P_Z0 - v * MM}; }
// Satin stainless slide and barrel; the frame's alloy a shade greyer; black oxide on the controls
// and sights; dark grey rubber grips.
const Color INOX{206, 207, 209, 255}, ALLOY{190, 190, 192, 255}, OXIDE{24, 24, 26, 255}, RUBBER{74, 74, 78, 255},
    STIPPLE{86, 86, 90, 255}, GROOVE{96, 96, 100, 255}, BORE{8, 8, 10, 255}, DOT{236, 234, 226, 255}, FIRE_DOT{196, 22, 20, 255}, GAP{14, 14, 15, 255},
    MAG{26, 26, 28, 255};
// ── Roll marks ──────────────────────────────────────────────────────────────────
// Lettering stamped into steel, in a plain stroke font: each glyph a few pen strokes on a grid 4
// wide and 6 tall (the capitals' height; m, the one lower-case letter, is 4). Each stroke is laid
// into the metal as a thin dark bar, a hair proud of the surface and sunk into it below, a closed
// little block, so the part stays a closed surface (the grip fitter's distance field counts on
// that). Like letters cut with a fine engraving pen.
struct Glyph { char c; float advance; const char* strokes; };   // strokes: "x,y x,y ...|x,y ..." (grid units)
const Glyph FONT[] = {
    {'A', 5.4f, "0,0 2,6 4,0|0.75,2.2 3.25,2.2"},
    {'B', 5.4f, "0,0 0,6 3,6 3.9,5.1 3.9,3.9 3,3 0,3|3,3 4,2 4,0.9 3.1,0 0,0"},
    {'C', 5.4f, "4,5 3,6 1,6 0,5 0,1 1,0 3,0 4,1"},
    {'D', 5.4f, "0,0 0,6 2.4,6 4,4.4 4,1.6 2.4,0 0,0"},
    {'E', 5.2f, "4,6 0,6 0,0 4,0|0,3 3,3"},
    {'F', 5.2f, "4,6 0,6 0,0|0,3 3,3"},
    {'G', 5.4f, "4,5 3,6 1,6 0,5 0,1 1,0 3,0 4,1 4,2.8 2.3,2.8"},
    {'I', 2.6f, "0.6,0 0.6,6"},
    {'L', 5.0f, "0,6 0,0 3.8,0"},
    {'M', 6.0f, "0,0 0,6 2.25,2.4 4.5,6 4.5,0"},
    {'N', 5.4f, "0,0 0,6 4,0 4,6"},
    {'O', 5.6f, "1.1,0 0,1.1 0,4.9 1.1,6 2.9,6 4,4.9 4,1.1 2.9,0 1.1,0"},
    {'P', 5.2f, "0,0 0,6 3,6 4,5 4,4 3,3 0,3"},
    {'R', 5.4f, "0,0 0,6 3,6 4,5 4,4 3,3 0,3|2.2,3 4,0"},
    {'S', 5.4f, "4,5 3,6 1,6 0,5 0,4 1,3 3,3 4,2 4,1 3,0 1,0 0,1"},
    {'T', 5.2f, "0,6 4,6|2,6 2,0"},
    {'U', 5.4f, "0,6 0,1 1,0 3,0 4,1 4,6"},
    {'V', 5.4f, "0,6 2,0 4,6"},
    {'Y', 5.4f, "0,6 2,3 4,6|2,3 2,0"},
    {'2', 5.4f, "0,5 1,6 3,6 4,5 4,4 0,0 4,0"},
    {'9', 5.4f, "4,4 3,3 1,3 0,4 0,5 1,6 3,6 4,5 4,1 3,0 1,0 0,1"},
    {'m', 5.4f, "0,0 0,4|0,3 1,4 1.6,4 2,3 2,0|2,3 2.6,4 3.4,4 4,3 4,0"},
    {'.', 2.4f, "0.4,0 0.9,0 0.9,0.5 0.4,0.5 0.4,0"},
    {'-', 4.6f, "0.6,3 3.4,3"},
    {' ', 3.6f, ""},
};

// One stroke from a to b (gun mm, on the face at w = `w`), `half` mm either side of the line: a
// block from a hair proud of the face to a little inside it, square-ended so strokes meet cleanly.
void cut_stroke(MeshBuilder& b, Vector2 a, Vector2 c, float w, float half) {
    Vector2 d = Vector2Subtract(c, a);
    const float len = Vector2Length(d);
    d = len > 1e-6f ? Vector2Scale(d, half / len) : Vector2{half, 0};
    const Vector2 n{-d.y, d.x};
    Outline bar;
    bar.to(a.x - d.x - n.x, a.y - d.y - n.y).to(c.x + d.x - n.x, c.y + d.y - n.y).to(c.x + d.x + n.x, c.y + d.y + n.y)
        .to(a.x - d.x + n.x, a.y - d.y + n.y);
    const float out = w < 0 ? -1.0f : 1.0f, proud = 0.04f, sunk = 0.15f;   // mm
    b.slab(pistol(bar).p, (w + out * (proud - sunk) / 2) * MM, (proud + sunk) / 2 * MM, 0, 0);
}

// `text` on a flat side of the pistol: its first letter's bottom left (as you read it) at gun
// (u0, v0), letters `h` mm tall, reading toward the muzzle (`along` +1, the right side) or the
// back (-1, the left side: seen from there the muzzle points left).
void engrave(MeshBuilder& b, const char* text, float u0, float v0, float w, float h, float along) {
    const float s = h / 6, half = 0.12f;
    float pen = 0;
    for (const char* ch = text; *ch; ++ch) {
        const Glyph* g = nullptr;
        for (const Glyph& f : FONT)
            if (f.c == *ch) g = &f;
        if (!g) continue;
        const char* p = g->strokes;
        while (*p) {   // each stroke: points until '|' or the end
            Vector2 last{};
            bool have = false;
            while (*p && *p != '|') {
                char* e;
                const float x = std::strtof(p, &e);
                const float y = std::strtof(e + 1, &e);
                const Vector2 at{u0 + along * (pen + x) * s, v0 + y * s};
                if (have) cut_stroke(b, last, at, w, half);
                last = at;
                have = true;
                p = e;
                while (*p == ' ') ++p;
            }
            if (*p == '|') ++p;
        }
        pen += g->advance;
    }
}
float text_width(const char* text, float h) {   // mm, as engrave() lays it
    float pen = 0;
    for (const char* ch = text; *ch; ++ch)
        for (const Glyph& f : FONT)
            if (f.c == *ch) pen += f.advance;
    return pen * h / 6;
}

// ── Remington 870 ───────────────────────────────────────────────────────────────
// u from the back of the receiver: the trigger at 27, the breech face at 174, the muzzle at 644
// (18.5 inches of barrel), the butt at -327 (14 inches from the trigger). The right hand holds the
// wrist of the stock: the middle of that grip, (-47, -69), sits where the pistol's grip does in
// the fist (Character::shotgun_hold then tilts it to lie along the fingers). The fore-end is where
// the left hand pumps.
constexpr float R_Y0 = -0.0947f, R_Z0 = -0.0518f;
Outline rifle(const Outline& o) { return o.scaled(-MM, R_Y0, R_Z0); }
Vector3 rifle_at(float u, float v, float w = 0) { return {w * MM, R_Y0 - u * MM, R_Z0 - v * MM}; }
// Blued steel, a gold trigger, the bolt bright in its port; the furniture oiled walnut (or black
// synthetic).
const Color BLUED{24, 26, 32, 255}, GILT{178, 140, 64, 255}, POLY{27, 27, 29, 255}, WALNUT{104, 54, 30, 255}, PAD{16, 16, 17, 255},
    SLOT{12, 12, 13, 255}, BOLT{196, 198, 200, 255}, BEAD{232, 222, 190, 255};
}  // namespace

Vector3 m92fs_at(float u, float v, float w) { return pistol_at(u, v, w); }
Vector3 r870_at(float u, float v, float w) { return rifle_at(u, v, w); }

GunParts m92fs(const Matrix& hold) {
    GunParts g;
    Matrix turn = hold;   // (the hold turns the travel; its shift doesn't move a direction)
    turn.m12 = turn.m13 = turn.m14 = 0;
    g.travel = Vector3Transform({0, 0.045f, 0}, turn);   // the slide runs 45 mm back toward the wrist
    g.centre = Vector3Transform(pistol_at(95, -52), hold);
    // Built in the gun's own frame, then turned into the hand (MeshData::append), so the surface
    // patterns keep to the gun however it's held.
    MeshData moving, fixed;

    // ── The slide (it moves) ─────────────────────────────────────────────────────
    MeshBuilder s(moving);
    s.material(MAT_STEEL).color(INOX);
    // Its side view: the full-height breech block at the back, a scoop down to the low walls either
    // side of the barrel (the open top the Beretta is known by), running on to the muzzle. The nose
    // rounds off underneath, over the recoil spring.
    Outline side;
    side.to(6, -17.5f).to(6, 8.5f).curve(6, 12.5f, 10, 12.5f, 4).to(79, 12.5f)
        .curve(86, 12.5f, 88, 6.5f, 4).curve(90, 0, 96, 0, 4).to(206.5f, 0).curve(208, 0, 208, -1.5f, 2)
        .to(208, -9).curve(208, -17.5f, 199, -17.5f, 5);
    s.slab(pistol(side).p, 0, 12 * MM, 2.2f * MM, 3);
    // The bridge over the muzzle: a round hood hugging the barrel, swelling out of it at the back.
    {
        std::vector<Vector3> pts;
        std::vector<float> rr;
        const float us[] = {177, 180, 183, 186, 189, 192, 195, 206.8f, 207.6f, 208};
        const float rs[] = {7.2f, 7.5f, 8.2f, 9.2f, 10.2f, 10.9f, 11.3f, 11.3f, 11.0f, 10.4f};
        for (int i = 0; i < 10; ++i) { pts.push_back(pistol_at(us[i], 0)); rr.push_back(rs[i] * MM); }
        s.chain(pts, rr, 32);
    }
    // The barrel sits in a channel a little wider than itself: a dark slit either side of it.
    s.material(MAT_VOID).color(GAP);
    Outline channel;
    channel.to(91, -9).to(91, 0.15f).to(183, 0.15f).to(183, -9);
    s.slab(pistol(channel).p, 0, 7.8f * MM, 0, 0);
    // The ejection port, on the right: the wall cut down beside the chamber.
    Outline port;
    port.to(89, -3.5f).to(119, -3.5f).curve(125, -3.5f, 125, 0.2f, 3).to(89, 0.2f);
    s.slab(pistol(port).p, 9.9f * MM, 2.25f * MM, 0.3f * MM, 1);
    // Cocking serrations: eleven ridges across the back of each side, the grooves between them in
    // shadow.
    s.material(MAT_STEEL).color(GROOVE);
    Outline grooves;
    grooves.to(39, -16.5f).to(39, 5.2f).to(64.5f, 5.2f).to(64.5f, -16.5f);
    for (float side_w : {-1.0f, 1.0f}) s.slab(pistol(grooves).p, side_w * 12.05f * MM, 0.1f * MM, 0, 0);
    s.color(INOX);
    for (int i = 0; i < 11; ++i) {
        Outline r;
        const float u0 = 39.5f + 2.3f * float(i);
        r.to(u0, -16.3f).to(u0, 5).to(u0 + 1.2f, 5).to(u0 + 1.2f, -16.3f);
        for (float side_w : {-1.0f, 1.0f}) s.slab(pistol(r).p, side_w * 12.2f * MM, 0.3f * MM, 0.25f * MM, 1);
    }
    // The front sight, machined into the bridge, with its white dot.
    Outline blade;
    blade.to(194, 10.5f).to(195.5f, 17.3f).to(200.5f, 17.3f).curve(202, 17.3f, 202.5f, 15.5f, 2).to(203.5f, 10.5f);
    s.slab(pistol(blade).p, 0, 1.6f * MM, 0.5f * MM, 2);
    // The safety/decocker levers, black, either side at the back: a round hub, a paddle forward.
    s.material(MAT_METAL).color(OXIDE);
    Outline lever;
    lever.arc(18, 5.5f, 4.8f, -PI / 2, -3 * PI / 2, 10).to(31, 9.8f).curve(37.5f, 9.5f, 37.5f, 6.2f, 3).curve(37.5f, 3, 31, 2.8f, 3)
        .to(23, 1.5f);
    for (float side_w : {-1.0f, 1.0f}) s.slab(pistol(lever).p, side_w * 13.1f * MM, 1.1f * MM, 0.5f * MM, 2);
    for (float side_w : {-1.0f, 1.0f})   // the grooves across the paddle's thumb pad
        for (int k = 0; k < 3; ++k) s.box(pistol_at(31.5f + 1.8f * float(k), 6.3f, side_w * 14.25f), {0.12f * MM, 0.35f * MM, 3 * MM}, 0.5f, 6, 4);
    // The rear sight, black, dovetailed across the top: two ears either side of a square notch.
    Outline ear;
    ear.to(16, 12).to(16.6f, 18.8f).to(25, 18.8f).to(26.5f, 12);
    for (float side_w : {-1.0f, 1.0f}) s.slab(pistol(ear).p, side_w * 4.35f * MM, 2.55f * MM, 0.5f * MM, 2);
    Outline notch_base;
    notch_base.to(16, 12).to(16.3f, 16.3f).to(25.8f, 16.3f).to(26.5f, 12);
    s.slab(pistol(notch_base).p, 0, 2.2f * MM, 0.3f * MM, 1);
    // White dots, facing the shooter: two on the rear sight, one on the front.
    s.material(MAT_DEFAULT).color(DOT);
    for (float side_w : {-1.0f, 1.0f}) s.ellipsoid(pistol_at(16.45f, 16.6f, side_w * 4.35f), {1.05f * MM, 0.25f * MM, 1.05f * MM}, 10, 4);
    s.ellipsoid(pistol_at(194.9f, 15.4f), {1.0f * MM, 0.25f * MM, 1.0f * MM}, 10, 4);
    // The red dot under the right-hand lever: showing means ready to fire.
    s.color(FIRE_DOT).ellipsoid(pistol_at(21.5f, -4, 12.02f), {0.25f * MM, 1.3f * MM, 1.3f * MM}, 10, 4);
    // The roll marks, on the flats ahead of the serrations. Left (read with the muzzle to your
    // left): the maker and the town, and under them PB in an oval. Right, under the ejection port:
    // the model and the calibre.
    {
        const char* maker = "PIETRO BERETTA GARDONE V.T. - MADE IN ITALY";
        const char* model = "MOD. 92FS - CAL. 9mm PARABELLUM - PATENTED";
        s.material(MAT_METAL).color(Color{70, 71, 75, 255});   // the cuts catch the shadow
        const float h = 2.2f, mid = 124;
        engrave(s, maker, mid + text_width(maker, h) / 2, -7.0f, -12, h, -1);
        engrave(s, model, mid - text_width(model, h) / 2, -9.5f, 12, h, 1);
        const float ou = mid, ov = -12.1f, ra = 4.6f, rb = 2.7f;   // the oval
        for (int i = 0; i < 28; ++i) {
            const float a0 = 2 * PI * float(i) / 28, a1 = 2 * PI * float(i + 1) / 28;
            cut_stroke(s, {ou + ra * std::cos(a0), ov + rb * std::sin(a0)}, {ou + ra * std::cos(a1), ov + rb * std::sin(a1)}, -12, 0.12f);
        }
        engrave(s, "PB", ou + text_width("PB", 2.6f) / 2 - 0.25f, ov - 1.3f, -12, 2.6f, -1);
    }

    // ── The rest (it stays put) ──────────────────────────────────────────────────
    MeshBuilder f(fixed);
    // The barrel: the chamber block showing in the port, then the bare barrel along the open top,
    // just proud of the bridge at the muzzle.
    f.material(MAT_STEEL).color(INOX);
    f.tube(pistol_at(88, 0), pistol_at(117, 0), 8.2f * MM, 8.2f * MM, 28);
    f.tube(pistol_at(117, 0), pistol_at(121, 0), 8.2f * MM, 7.3f * MM, 28);
    f.tube(pistol_at(121, 0), pistol_at(208.5f, 0), 7.3f * MM, 7.3f * MM, 28);
    f.material(MAT_METAL).color(BORE).tube(pistol_at(208.5f, 0), pistol_at(208.6f, 0), 4.5f * MM, 4.5f * MM, 20);   // the bore
    f.tube(pistol_at(207.9f, -12), pistol_at(208.1f, -12), 3.3f * MM, 3.3f * MM, 16);                               // the spring's hole...
    f.material(MAT_STEEL).color(ALLOY).tube(pistol_at(207.5f, -12), pistol_at(208.15f, -12), 2 * MM, 2 * MM, 12);  // ... and the guide rod's end

    // The frame, satin alloy. Above: the rails under the slide and the dust cover out front.
    f.material(MAT_STEEL).color(ALLOY);
    Outline upper;
    upper.to(-4, -17.2f).to(192, -17.2f).curve(194, -17.2f, 194, -19.2f, 2).to(194, -24.5f).curve(194, -28.5f, 189.5f, -28.5f, 3)
        .to(56, -28.5f).to(54, -33).to(0, -33).to(-4, -26);
    f.slab(pistol(upper).p, 0, 11 * MM, 1.6f * MM, 2);
    // The grip: raked about 20 degrees; the backstrap sweeps up into a tang that sits in the web of
    // the hand under the hammer.
    Outline grip;
    grip.to(56, -24).to(56, -38).curve(55.5f, -50, 48, -58, 3).to(35.5f, -108).curve(34.3f, -114, 37, -117.5f, 3).to(-16.5f, -117.5f)
        .curve(-21.5f, -117.5f, -22, -113.5f, 3).to(-1.5f, -53).curve(1.5f, -38, -4, -28, 4).to(-2, -24);
    f.slab(pistol(grip).p, 0, 12.8f * MM, 3.5f * MM, 3);
    Outline tang;
    tang.to(2, -18).to(-6, -17.6f).to(-15, -17.8f).curve(-21.5f, -18.2f, -22, -21, 3).curve(-22.5f, -24, -17.5f, -24, 3)
        .curve(-11, -24, -5, -29.5f, 3).to(2, -33);
    f.slab(pistol(tang).p, 0, 11 * MM, 4.5f * MM, 4);
    // The trigger guard: big and round-bottomed, its front almost straight.
    Outline guard;
    guard.to(115, -26).to(115, -40).curve(115, -56.5f, 99, -56.5f, 5).to(71, -56.5f).curve(56.5f, -56.5f, 56, -42, 5).to(56, -28)
        .to(47, -47).to(49, -59.5f).curve(53, -61.5f, 63, -61.5f, 3).to(98, -61.5f).curve(118.5f, -61.5f, 119.5f, -45, 6).to(120, -35)
        .curve(120.5f, -29.5f, 123.5f, -28.5f, 2).to(123.5f, -26);
    f.slab(pistol(guard).p, 0, 5 * MM, 2 * MM, 3);
    // Grooves down the front strap.
    f.color(Color{150, 151, 154, 255});
    for (int k = -3; k <= 3; ++k) {
        const float w = 2.5f * float(k);
        const Vector2 a{46.8f, -62.0f}, b{36.3f, -104.0f};   // on the strap, sunk in so a thin line stands proud
        f.tube(pistol_at(a.x, a.y, w), pistol_at(b.x, b.y, w), 0.5f * MM, 0.5f * MM, 6);
    }
    // The trigger, stainless, raked forward in double action, its face curved for the finger.
    f.color(INOX);
    Outline trig;
    trig.to(72, -28).to(78, -28).curve(81, -37.5f, 86.5f, -47.5f, 4).curve(87.5f, -50, 85.5f, -51.3f, 2).to(84, -51.5f)
        .curve(73.5f, -46, 71.5f, -33.5f, 4);
    f.slab(pistol(trig).p, 0, 2.8f * MM, 1.1f * MM, 2);
    // The hammer, black: a round spur with a hole through it, down to its neck in the frame's tang.
    f.material(MAT_METAL).color(OXIDE);
    Outline neck;
    neck.to(-6, 1).to(0, 2).to(3, -8).to(3.5f, -17.5f).to(-1, -20.5f).to(-6.5f, -14).to(-7, -5);
    f.slab(pistol(neck).p, 0, 3.2f * MM, 1 * MM, 2);
    {
        std::vector<Vector3> ring;
        std::vector<float> rr;
        for (int i = 0; i <= 20; ++i) {
            const float a = 2 * PI * float(i) / 20;
            ring.push_back(pistol_at(-1 + 4.3f * std::cos(a), 6.5f + 4.3f * std::sin(a)));
            rr.push_back(1.9f * MM);
        }
        f.chain(ring, rr, 10, 1.7f);
    }
    // The controls, black. Left: the slide stop (its thumb tab over the grip) and the takedown
    // lever ahead of it; the magazine release behind the trigger guard. Right: the takedown
    // button, the trigger bar in its recess, and the release's far end.
    f.material(MAT_METAL).color(OXIDE);
    Outline stop;
    stop.to(40, -18.2f).to(80, -18.2f).curve(82.5f, -18.2f, 82.5f, -21, 2).to(82, -23).to(45, -23.5f).to(40, -22);
    f.slab(pistol(stop).p, -11.8f * MM, 0.8f * MM, 0.4f * MM, 1);
    Outline tab;
    tab.to(41, -17.4f).to(53, -17.4f).to(54, -19.5f).to(53, -24).to(41, -23.5f);
    f.slab(pistol(tab).p, -12.6f * MM, 1.2f * MM, 0.5f * MM, 2);
    for (int k = 0; k < 4; ++k) f.box(pistol_at(43.5f + 2.3f * float(k), -20.5f, -13.85f), {0.12f * MM, 0.5f * MM, 2.6f * MM}, 0.5f, 6, 4);
    Outline takedown;
    takedown.to(93, -18.5f).to(113, -18.5f).curve(118, -18.5f, 118, -23, 3).curve(118, -27.3f, 111, -27.3f, 3).to(97, -27.3f)
        .curve(93, -27.3f, 93, -23, 2);
    f.slab(pistol(takedown).p, -11.9f * MM, 0.9f * MM, 0.4f * MM, 2);
    f.ellipsoid(pistol_at(111, -22, -12.9f), {0.7f * MM, 2.2f * MM, 2.2f * MM}, 12, 5);
    Outline disc;   // a round button seen side-on
    disc.arc(0, 0, 1, 0, 2 * PI * 23 / 24, 23);
    f.slab(pistol(disc.scaled(4.6f, 48, -52)).p, -14.3f * MM, 1.6f * MM, 0.9f * MM, 3);   // magazine release, left
    f.slab(pistol(disc.scaled(4.4f, 48, -52)).p, 13.5f * MM, 0.9f * MM, 0.6f * MM, 2);    // its far end, right
    f.slab(pistol(disc.scaled(3.8f, 111, -22)).p, 11.3f * MM, 0.6f * MM, 0.4f * MM, 2);       // takedown button, right
    f.ellipsoid(pistol_at(119, -25, 11.1f), {0.5f * MM, 4.5f * MM, 2.8f * MM}, 16, 5);          // the stop's pin
    Outline bar;
    bar.to(64, -19).to(86, -19).curve(89, -19, 89, -22, 2).curve(89, -26.5f, 86, -26.5f, 2).to(64, -26.5f);
    f.slab(pistol(bar).p, 11.05f * MM, 0.45f * MM, 0.3f * MM, 1);

    // The grips: dark grey rubber, a smooth border round a stippled field, two screws and the
    // Beretta medallion between them, toward the front of the grip.
    Outline panel;
    panel.to(2.5f, -25.5f).to(48, -25.5f).to(47.5f, -42).to(43.2f, -56.8f).to(30.7f, -106.5f)
        .curve(29.7f, -112, 25.5f, -112, 2).to(-15, -112).curve(-18, -112, -17.7f, -108.5f, 2).to(3, -53)
        .curve(5.5f, -40, 2, -30, 3);
    Outline field;
    field.to(6, -29).to(44, -29).to(43.5f, -42).to(39.5f, -54).to(27.5f, -102.5f).to(-13, -108).to(6.5f, -52).curve(8.5f, -40, 5.5f, -31, 3);
    for (float side_w : {-1.0f, 1.0f}) {
        f.material(MAT_RUBBER).color(RUBBER);
        f.slab(pistol(panel).p, side_w * 14.4f * MM, 1.9f * MM, 1.5f * MM, 3);
        f.material(MAT_GRIP).color(STIPPLE);
        f.slab(pistol(field).p, side_w * 14.6f * MM, 1.9f * MM, 1.0f * MM, 2);
        f.material(MAT_RUBBER).color(RUBBER);   // the medallion, moulded in
        f.slab(pistol(disc.scaled(6.2f, 29, -55)).p, side_w * 16.4f * MM, 0.35f * MM, 0.3f * MM, 2);
        f.slab(pistol(disc.scaled(4.4f, 29, -55)).p, side_w * 16.75f * MM, 0.12f * MM, 0.1f * MM, 1);
        f.material(MAT_STEEL).color(INOX);      // the screws, a hex socket in each
        for (const Vector2 at : {Vector2{34, -40.5f}, Vector2{18, -101.5f}}) {
            f.ellipsoid(pistol_at(at.x, at.y, side_w * 16.4f), {0.9f * MM, 3.6f * MM, 3.6f * MM}, 20, 6);
            f.material(MAT_METAL).color(BORE).ellipsoid(pistol_at(at.x, at.y, side_w * 17.25f), {0.12f * MM, 1.1f * MM, 1.1f * MM}, 6, 3);
            f.material(MAT_STEEL).color(INOX);
        }
    }
    // The magazine's black base plate under the grip, and the lanyard loop at the heel.
    f.material(MAT_POLYMER).color(MAG);
    Outline base;
    base.to(-18.5f, -117).to(38, -117).curve(40.5f, -117, 40.5f, -120, 2).curve(40.5f, -123, 37, -123, 2).to(-17, -123)
        .curve(-20, -123, -20, -120, 2);
    f.slab(pistol(base).p, 0, 11.5f * MM, 1.5f * MM, 2);
    f.material(MAT_STEEL).color(INOX);
    std::vector<Vector3> loop;
    std::vector<float> radii;
    for (int i = 0; i <= 14; ++i) {
        const float a = 2 * PI * float(i) / 14;
        loop.push_back(pistol_at(-21 + 3.2f * std::cos(a), -115.5f + 3.2f * std::sin(a)));
        radii.push_back(0.9f * MM);
    }
    f.chain(loop, radii, 6);
    g.moving.append(moving, hold);
    g.fixed.append(fixed, hold);
    return g;
}

GunParts r870(const Matrix& hold, Stock stock) {
    GunParts g;
    const Matrix tip = hold;
    Matrix turn = tip;   // (the hold turns the travel; its shift doesn't move a direction)
    turn.m12 = turn.m13 = turn.m14 = 0;
    g.travel = Vector3Transform({0, 0.089f, 0}, turn);   // the fore-end racks 89 mm back, to the receiver
    g.centre = Vector3Transform(rifle_at(160, -50), tip);
    const bool wood = stock == Stock::Walnut;
    const int FURN = wood ? MAT_WOOD : MAT_POLYMER;
    const Color furn = wood ? WALNUT : POLY;

    // Built in the gun's own frame, then turned into the hand (MeshData::append), so the wood's grain
    // keeps to the gun however it's held.
    MeshData moving, fixed;

    // ── The fore-end and its action bars (they move) ─────────────────────────────
    MeshBuilder m(moving);
    m.material(FURN).color(furn);
    Outline fore;   // long and round-bellied, wrapped round the magazine tube under the barrel
    fore.to(252, -11).to(428, -11).curve(445, -11, 445, -27, 5).curve(445, -55, 423, -55, 6).to(264, -55)
        .curve(238, -55, 238, -32, 6).curve(238, -11, 252, -11, 5);
    m.slab(rifle(fore).p, 0, 25 * MM, 12 * MM, 5);
    m.color(wood ? Color{70, 36, 18, 255} : SLOT);   // grip grooves along its sides
    for (int k = 0; k < 6; ++k)
        for (float side : {-1.0f, 1.0f})
            m.box(rifle_at(325, -21.0f - 5.0f * float(k), side * 25.05f), {0.35f * MM, 72 * MM, 1.1f * MM}, 0.5f, 8, 4);
    m.material(MAT_METAL).color(Color{150, 152, 155, 255});   // action bars, back into the receiver
    for (float side : {-1.0f, 1.0f}) m.box(rifle_at(222, -21, side * 12.5f), {0.9f * MM, 26 * MM, 2.6f * MM}, 0.35f, 8, 6);

    // ── The rest (it stays put) ──────────────────────────────────────────────────
    MeshBuilder f(fixed);
    // The receiver: a long, flat-sided box, its back sweeping round and down into the stock.
    f.material(MAT_METAL).color(BLUED);
    Outline recv;
    recv.to(0, -39).to(0, 0).curve(0, 17, 26, 17, 6).to(209, 17).curve(212, 17, 212, 14, 2).to(212, -36).curve(212, -39, 209, -39, 2);
    f.slab(rifle(recv).p, 0, 16 * MM, 3.5f * MM, 3);
    // The ejection port in the front half on the right, the bright bolt showing in it; the loading
    // port underneath; the two pins that hold the trigger group in.
    f.color(SLOT);
    Outline eport;
    eport.to(123, -5).to(183, -5).curve(188, -5, 188, 0, 2).to(188, 6).curve(188, 11, 183, 11, 2).to(123, 11).curve(118, 11, 118, 6, 2)
        .to(118, 0).curve(118, -5, 123, -5, 2);
    f.slab(rifle(eport).p, 15.2f * MM, 1 * MM, 0.4f * MM, 1);
    f.material(MAT_STEEL).color(BOLT);
    Outline bolt;
    bolt.to(123, -2.5f).to(182, -2.5f).curve(185, -2.5f, 185, 3, 2).curve(185, 8.5f, 182, 8.5f, 2).to(123, 8.5f).curve(120.5f, 8.5f, 120.5f, 3, 2)
        .curve(120.5f, -2.5f, 123, -2.5f, 2);
    f.slab(rifle(bolt).p, 14.5f * MM, 1.9f * MM, 1.8f * MM, 3);
    f.material(MAT_METAL).color(SLOT);
    f.box(rifle_at(150, -39.2f), {10.5f * MM, 38 * MM, 0.4f * MM}, 0.25f, 8, 6);
    Outline pin;
    pin.arc(0, 0, 2.4f, 0, 2 * PI * 15 / 16, 15);
    f.color(Color{58, 60, 66, 255});
    for (const float u : {14.0f, 98.0f}) f.slab(rifle(pin.scaled(1, u, -30)).p, 0, 16.2f * MM, 0.3f * MM, 1);
    // The trigger group under the back of the receiver: the plate, the guard, the gold trigger, the
    // cross-bolt safety behind it, and the action release lever ahead of the guard on the left.
    f.color(BLUED);
    Outline plate;
    plate.to(4, -37).to(108, -37).curve(110, -37, 110, -40, 2).to(108, -47).to(8, -47).curve(4, -47, 4, -43, 2);
    f.slab(rifle(plate).p, 0, 11 * MM, 2 * MM, 2);
    Outline tguard;
    tguard.to(8, -45).curve(10, -80, 28, -80, 5).to(76, -80).curve(93, -80, 95, -45, 5).to(86, -45).curve(84, -72.5f, 73, -72.5f, 5)
        .to(31, -72.5f).curve(17.5f, -72.5f, 16.5f, -45, 5);
    f.slab(rifle(tguard).p, 0, 4.5f * MM, 1.8f * MM, 2);
    f.color(GILT);
    Outline trig;
    trig.to(24, -45).to(30, -45).curve(33.5f, -57, 31, -68, 3).to(28.5f, -69).curve(29, -57, 24, -46, 3);
    f.slab(rifle(trig).p, 0, 3.5f * MM, 1.2f * MM, 2);
    f.color(BLUED).tube(rifle_at(12, -53, -12.5f), rifle_at(12, -53, 12.5f), 3.6f * MM, 3.6f * MM, 16);   // cross-bolt safety
    f.material(MAT_DEFAULT).color(Color{170, 30, 26, 255});                                               // its red ring: ready to fire
    f.tube(rifle_at(12, -53, -12.5f), rifle_at(12, -53, -12.9f), 3.7f * MM, 3.7f * MM, 16);
    f.material(MAT_METAL).color(BLUED);
    Outline release;
    release.to(100, -42).to(110, -42).curve(113, -42, 113, -45, 2).to(111, -50).to(102, -49);
    f.slab(rifle(release).p, -11.8f * MM, 1 * MM, 0.4f * MM, 1);
    // The plain barrel, 18.5 inches from the breech, with a bead at the muzzle.
    f.tube(rifle_at(190, 0), rifle_at(644, 0), 10.3f * MM, 9.6f * MM, 24);
    f.color(SLOT).tube(rifle_at(644, 0), rifle_at(644.4f, 0), 8.6f * MM, 8.6f * MM, 16);   // the bore
    f.color(BLUED).tube(rifle_at(636, 9), rifle_at(636, 11.2f), 1.1f * MM, 1.1f * MM, 8);
    f.material(MAT_DEFAULT).color(BEAD).ellipsoid(rifle_at(636, 11.8f), {1.7f * MM, 1.7f * MM, 1.7f * MM}, 10, 6);
    // The magazine tube under the barrel, lengthened by an extension to seven shells: the barrel's
    // ring where the standard tube ended, the extension's cap, and a clamp tying tube to barrel.
    f.material(MAT_METAL).color(BLUED);
    f.tube(rifle_at(205, -27), rifle_at(610, -27), 11 * MM, 11 * MM, 20);
    f.tube(rifle_at(610, -27), rifle_at(624, -27), 12.5f * MM, 12.5f * MM, 20);
    Outline lug;
    lug.to(452, 9).to(466, 9).to(466, -39).to(452, -39);
    f.slab(rifle(lug).p, 0, 12 * MM, 5 * MM, 3);
    Outline clamp;
    clamp.to(582, 11).to(598, 11).to(598, -40).to(582, -40);
    f.slab(rifle(clamp).p, 0, 13.5f * MM, 4 * MM, 3);
    f.tube(rifle_at(590, -14, -14.5f), rifle_at(590, -14, 14.5f), 2.2f * MM, 2.2f * MM, 10);   // the clamp's bolt
    {
        std::vector<Vector3> swivel;   // a sling swivel hanging under the cap
        std::vector<float> rr;
        for (int i = 0; i <= 14; ++i) {
            const float a = 2 * PI * float(i) / 14;
            swivel.push_back(rifle_at(617 + 7 * std::cos(a), -46 + 5 * std::sin(a)));
            rr.push_back(1.2f * MM);
        }
        f.chain(swivel, rr, 6);
    }
    // The stock: a sporter's, dropping away from the receiver to a comb well below the line of the
    // barrel, its wrist curving down into a half pistol grip. Lofted, so it can be slim at the wrist
    // where the hand closes round it and broad at the butt: its top and bottom lines come from the
    // side view, its width and roundness change along it.
    f.material(FURN).color(furn);
    {
        Outline top, bottom;   // both run back to front
        top.to(-302, -32).to(-110, -14).curve(-60, -11, -30, -4, 5).curve(-12, 0, 1, 4, 4);   // the comb, then the wrist rising
        bottom.to(-302, -166).curve(-220, -130, -150, -118, 8).to(-109, -114)                 // the belly, rising...
            .curve(-92, -121, -79, -119, 4)                                                     // ... to dip into the grip
            .curve(-55, -114, -39, -97, 4).curve(-20, -75, 4, -57, 5).to(8, -49).to(10, -44);  // and up its front to the guard
        auto along = [](const std::vector<Vector2>& line, float u) {   // v on a polyline at u
            if (u <= line.front().x) return line.front().y;
            for (size_t i = 1; i < line.size(); ++i)
                if (u <= line[i].x) return Lerp(line[i - 1].y, line[i].y, (u - line[i - 1].x) / std::max(line[i].x - line[i - 1].x, 1e-4f));
            return line.back().y;
        };
        constexpr int ROWS = 52, SEGS = 28;
        Grid loft;
        for (int i = 0; i < ROWS; ++i) {
            const float u = -302 + 312 * float(i) / float(ROWS - 1);
            const float hi = u > 1 ? -38.0f : along(top.p, u), lo = along(bottom.p, u);   // (ahead of the receiver's back: under it)
            const float k = std::clamp((u + 302) / 262, 0.0f, 1.0f);                      // 0 at the butt, 1 at the wrist
            // Half width, and squareness: an oval that fills out toward the butt (flat-sided, it
            // would catch the light all at once, like a plank).
            const float hw = Lerp(21, 15.5f, k * k * (3 - 2 * k)), n = Lerp(2.7f, 2.2f, k);
            std::vector<Vector3> ring(SEGS);
            for (int j = 0; j < SEGS; ++j) {   // (round clockwise seen from the butt, so the skin faces out)
                const float a = -2 * PI * float(j) / SEGS, c = std::cos(a), sn = std::sin(a);
                const float x = hw * std::copysign(std::pow(std::fabs(c), 2 / n), c);
                const float y = (hi + lo) / 2 + (hi - lo) / 2 * std::copysign(std::pow(std::fabs(sn), 2 / n), sn);
                ring[size_t(j)] = rifle_at(u, y, x);
            }
            loft.push_back(ring);
        }
        f.grid(loft, true, true);
    }
    f.material(MAT_RUBBER).color(PAD);
    Outline pad;
    pad.to(-300, -32).to(-322, -31).curve(-327, -31, -327, -36, 2).to(-327, -165).curve(-327, -170, -322, -170, 2).to(-300, -170);
    f.slab(rifle(pad).p, 0, 22 * MM, 7 * MM, 3);
    f.material(MAT_METAL).color(BLUED).tube(rifle_at(-250, -146, 0), rifle_at(-252, -154, 0), 3 * MM, 3 * MM, 10);   // sling stud
    g.moving.append(moving, tip);
    g.fixed.append(fixed, tip);
    return g;
}

}  // namespace dw::cast
