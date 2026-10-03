// damned_waters/engine/tests/test_guns.cpp
// Purpose: GoogleTest suite for the survivor's guns (cast_guns.cpp): they come out the size of the
// real ones (a Beretta M92FS, a Remington 870 with an 18.5-inch barrel), their moving parts travel the
// right way, every part is a closed surface facing outward, and aiming the 870 up or down bends him
// at the waist without breaking his hold.
#include <gtest/gtest.h>

#include "../src/cast_guns.hpp"   // (brings raylib and raymath)
#include "dw/character.hpp"       // Character::pitched (inline: no need to link the character)

using namespace dw;

namespace {
struct Box { Vector3 lo{1e9f, 1e9f, 1e9f}, hi{-1e9f, -1e9f, -1e9f}; };
Box bounds(const MeshData& d, Box b = {}) {
    for (size_t i = 0; i < d.count(); ++i) {
        const Vector3 p{d.pos[i * 3], d.pos[i * 3 + 1], d.pos[i * 3 + 2]};
        b.lo = Vector3Min(b.lo, p);
        b.hi = Vector3Max(b.hi, p);
    }
    return b;
}
// Signed volume (divergence theorem): positive when the parts are closed and face outward.
double volume(const MeshData& d) {
    double v = 0;
    for (size_t t = 0; t + 2 < d.count(); t += 3) {
        const Vector3 a{d.pos[t * 3], d.pos[t * 3 + 1], d.pos[t * 3 + 2]}, b{d.pos[t * 3 + 3], d.pos[t * 3 + 4], d.pos[t * 3 + 5]},
                      c{d.pos[t * 3 + 6], d.pos[t * 3 + 7], d.pos[t * 3 + 8]};
        v += double(Vector3DotProduct(a, Vector3CrossProduct(b, c))) / 6.0;
    }
    return v;
}
}  // namespace

// Wrist space: the barrel runs along -y (length), the gun's up is -z (height), its right +x (width).
TEST(Guns, TheBerettaIsTheSizeOfAnM92FS) {
    const cast::GunParts g = cast::m92fs();
    const Box b = bounds(g.load, bounds(g.moving, bounds(g.fixed)));   // (with its magazine in)
    EXPECT_GT(b.hi.y - b.lo.y, 0.225f);   // 217 mm, plus the lanyard loop and the tang behind the slide
    EXPECT_LT(b.hi.y - b.lo.y, 0.245f);
    EXPECT_GT(b.hi.z - b.lo.z, 0.135f);   // 137 mm from the sights to the magazine's base
    EXPECT_LT(b.hi.z - b.lo.z, 0.148f);
    EXPECT_GT(b.hi.x - b.lo.x, 0.030f);   // 38 mm across the safety levers; the grips a little less
    EXPECT_LT(b.hi.x - b.lo.x, 0.040f);
}

TEST(Guns, The870IsTheSizeOfTheRealOne) {
    const cast::GunParts g = cast::r870(MatrixIdentity());
    const Box b = bounds(g.moving, bounds(g.fixed));
    EXPECT_GT(b.hi.y - b.lo.y, 0.95f);    // 38 to 39 inches overall with an 18.5-inch barrel
    EXPECT_LT(b.hi.y - b.lo.y, 0.99f);
    EXPECT_GT(b.hi.x - b.lo.x, 0.040f);   // the fore-end and the butt pad are the widest
    EXPECT_LT(b.hi.x - b.lo.x, 0.056f);
}

TEST(Guns, TheSlideAndTheForeEndWorkBackTowardTheShooter) {
    const cast::GunParts p = cast::m92fs(), s = cast::r870(MatrixIdentity());
    EXPECT_NEAR(p.travel.y, 0.045f, 1e-4f);   // +y is back toward the wrist
    EXPECT_NEAR(s.travel.y, 0.089f, 1e-4f);
    EXPECT_NEAR(Vector3Length(p.travel), 0.045f, 1e-4f);
    // Held tipped in the hand, the fore-end still runs straight along the gun, however it's turned.
    const Matrix held = MatrixMultiply(MatrixMultiply(MatrixTranslate(0.01f, 0.02f, 0.03f), MatrixRotateX(0.6f)), MatrixTranslate(0.1f, 0.2f, 0.3f));
    EXPECT_NEAR(Vector3Length(cast::r870(held).travel), 0.089f, 1e-4f);
}

TEST(Guns, EveryPartIsClosedAndFacesOutward) {
    for (const cast::GunParts& g : {cast::m92fs(), cast::r870(MatrixIdentity()), cast::r870(MatrixIdentity(), cast::Stock::Synthetic)}) {
        EXPECT_GT(volume(g.fixed), 0.0);
        EXPECT_GT(volume(g.moving), 0.0);
        EXPECT_GT(volume(g.load), 0.0);
    }
}

// The magazine: as long as a 15-round M92FS magazine, inside the grip but for its base plate, and
// it slides out down the grip's rake. (Wrist space: up the gun is -z, back toward the wrist +y.)
TEST(Guns, TheMagazineSitsInTheGripAndSlidesOutDownIt) {
    const cast::GunParts g = cast::m92fs();
    const Box m = bounds(g.load), f = bounds(g.fixed);
    EXPECT_GT(m.hi.z - m.lo.z, 0.095f);   // the base plate to the top round: about 100 mm
    EXPECT_LT(m.hi.z - m.lo.z, 0.110f);
    EXPECT_LT(m.hi.x - m.lo.x, f.hi.x - f.lo.x);   // narrower than the grip it goes into
    const float plate_top = cast::m92fs_at(0, cast::MAG_PLATE_TOP).z;
    int below = 0;
    for (size_t i = 0; i < g.load.count(); ++i) below += g.load.pos[i * 3 + 2] > plate_top;
    EXPECT_GT(below, 50);                     // the base plate, under the grip
    EXPECT_GT(m.hi.z, f.hi.z - 0.002f);       // which is the bottom of the gun
    const Vector3 out = cast::m92fs_well_out();
    EXPECT_NEAR(Vector3Length(out), 1.0f, 1e-5f);
    EXPECT_GT(out.z, 0.95f);                  // down...
    EXPECT_GT(out.y, 0.2f);                   // ... and back with the grip's rake (14 degrees)
    EXPECT_LT(out.y, 0.3f);
}

// A 2 3/4-inch 12-gauge shell, and its way in: up from under the loading port, level in the port at
// 0.75 (where it's built), then forward into the tube.
TEST(Guns, TheShellGoesUpThroughThePortAndForwardIntoTheTube) {
    const cast::GunParts g = cast::r870(MatrixIdentity());
    const Box s = bounds(g.load);
    EXPECT_NEAR(s.hi.y - s.lo.y, 0.070f, 0.0015f);   // 70 mm long
    EXPECT_NEAR(s.hi.x - s.lo.x, 0.0224f, 0.001f);   // 22 mm across the rim
    const Vector3 head = cast::r870_at(135, -27);    // its brass
    const Vector3 in_port = Vector3Transform(head, cast::shell_in(0.75f));
    EXPECT_NEAR(Vector3Distance(in_port, head), 0.0f, 1e-4f);
    const Vector3 in_tube = Vector3Transform(head, cast::shell_in(1.0f));
    EXPECT_NEAR(in_tube.y - head.y, -0.030f, 1e-4f);   // pushed 30 mm forward (-y)
    const Vector3 below = Vector3Transform(head, cast::shell_in(0.0f));
    EXPECT_GT(below.z, cast::r870_at(0, -39).z + 0.03f);   // it starts well under the receiver
    // Nose up on the way in, level at the end.
    const Vector3 nose0 = Vector3Transform(cast::r870_at(205, -27), cast::shell_in(0.0f));
    EXPECT_LT(nose0.z, below.z - 0.03f);   // (up is -z)
    for (float k = 0; k <= 1.0f; k += 0.05f) {   // never a jump along the way
        const Vector3 a = Vector3Transform(head, cast::shell_in(k)), b = Vector3Transform(head, cast::shell_in(k + 0.05f));
        EXPECT_LT(Vector3Distance(a, b), 0.02f) << k;
    }
}

// A triangle wound against its own normals is culled from the side it should be seen from: the
// renderer shows the inside of the far wall instead (the 870's stock once looked like a flat grey
// plank that way). Reversed means facing more than 120 degrees away from its normals; slivers under
// a square millimetre, at the ends of the smallest rounded boxes, can't be seen and don't count.
TEST(Guns, EveryTriangleIsWoundTheWayItsNormalsFace) {
    const cast::GunParts parts[] = {cast::m92fs(), cast::r870(MatrixIdentity()), cast::r870(MatrixIdentity(), cast::Stock::Synthetic),
                                    cast::r870(MatrixRotateX(-0.6f))};   // held: tipped in the hand
    for (const cast::GunParts& g : parts)
        for (const MeshData* d : {&g.fixed, &g.moving}) {
            int wrong = 0;
            for (size_t t = 0; t + 2 < d->count(); t += 3) {
                Vector3 p[3], n{};
                for (size_t k = 0; k < 3; ++k) {
                    p[k] = {d->pos[(t + k) * 3], d->pos[(t + k) * 3 + 1], d->pos[(t + k) * 3 + 2]};
                    n = Vector3Add(n, {d->nrm[(t + k) * 3], d->nrm[(t + k) * 3 + 1], d->nrm[(t + k) * 3 + 2]});
                }
                const Vector3 f = Vector3CrossProduct(Vector3Subtract(p[1], p[0]), Vector3Subtract(p[2], p[0]));
                if (Vector3Length(f) * 0.5f > 1e-6f && Vector3DotProduct(Vector3Normalize(f), Vector3Normalize(n)) < -0.5f) ++wrong;
            }
            EXPECT_EQ(wrong, 0);
        }
}

// Aiming the 870 up or down, he bends at the waist: the spine keeps its own lean and turn, and the
// aim's pitch goes on top about the hips' level axis, so the gun, both arms and the cheek on the
// stock move as one. Character::pitched folds that into the spine's three angles.
TEST(Guns, AimingUpOrDownPitchesTheWholeUpperBody) {
    auto rig = [](Vector3 e) {   // this rig's joint order: z, then x, then y
        return MatrixMultiply(MatrixMultiply(MatrixRotateZ(e.z), MatrixRotateX(e.x)), MatrixRotateY(e.y));
    };
    const Vector3 spine{-0.08f, -0.263f, 0.05f};
    for (float a : {-0.8f, -0.3f, 0.0f, 0.25f, 0.55f}) {   // the game's whole range of aim
        const Matrix want = MatrixMultiply(rig(spine), MatrixRotateX(a)), got = rig(Character::pitched(spine, a));
        for (Vector3 v : {Vector3{1, 0, 0}, Vector3{0, 1, 0}, Vector3{0, 0, -1}}) {
            const Vector3 w = Vector3Transform(v, want), g = Vector3Transform(v, got);
            EXPECT_NEAR(w.x, g.x, 1e-5f);
            EXPECT_NEAR(w.y, g.y, 1e-5f);
            EXPECT_NEAR(w.z, g.z, 1e-5f);
        }
    }
    const Vector3 level = Character::pitched(spine, 0);   // a level aim leaves him as he was
    EXPECT_NEAR(level.x, spine.x, 1e-6f);
    EXPECT_NEAR(level.y, spine.y, 1e-6f);
    EXPECT_NEAR(level.z, spine.z, 1e-6f);
    const Vector3 ahead = Vector3Transform({0, 0, -1}, rig(Character::pitched({}, 0.3f)));   // up is up
    EXPECT_NEAR(ahead.y, std::sin(0.3f), 1e-5f);
    EXPECT_NEAR(ahead.z, -std::cos(0.3f), 1e-5f);
}
