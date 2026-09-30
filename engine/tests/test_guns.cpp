// damned_waters/engine/tests/test_guns.cpp
// Purpose: GoogleTest suite for the survivor's guns (cast_guns.cpp): they come out the size of the
// real ones (a Beretta M92FS, a Remington 870 Express Tactical), their moving parts travel the
// right way, and every part is a closed surface facing outward.
#include <gtest/gtest.h>

#include "../src/cast_guns.hpp"   // (brings raylib and raymath)

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
    const Box b = bounds(g.moving, bounds(g.fixed));
    EXPECT_GT(b.hi.y - b.lo.y, 0.225f);   // 217 mm, plus the lanyard loop and the tang behind the slide
    EXPECT_LT(b.hi.y - b.lo.y, 0.245f);
    EXPECT_GT(b.hi.z - b.lo.z, 0.135f);   // 137 mm from the sights to the magazine's base
    EXPECT_LT(b.hi.z - b.lo.z, 0.148f);
    EXPECT_GT(b.hi.x - b.lo.x, 0.030f);   // 38 mm across the safety levers; the grips a little less
    EXPECT_LT(b.hi.x - b.lo.x, 0.040f);
}

TEST(Guns, The870IsTheSizeOfAnExpressTactical) {
    const cast::GunParts g = cast::r870(MatrixIdentity());
    const Box b = bounds(g.moving, bounds(g.fixed));
    EXPECT_GT(b.hi.y - b.lo.y, 0.95f);    // 38.5 inches overall
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
    for (const cast::GunParts& g : {cast::m92fs(), cast::r870(MatrixIdentity()), cast::r870(MatrixIdentity(), cast::Stock::Walnut)}) {
        EXPECT_GT(volume(g.fixed), 0.0);
        EXPECT_GT(volume(g.moving), 0.0);
    }
}
