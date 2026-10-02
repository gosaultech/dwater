// damned_waters/engine/tests/test_grips.cpp
// Purpose: GoogleTest suite for the fitted grips (grips_fitted.inc, written by --fitgrips): each one
// places the gun by a true rotation and shift (no stretch, no mirror), puts the gun in the hand
// rather than somewhere near it, keeps each hand on its own side of the pistol, and bends the
// fingers within what finger joints do. A refit that went wrong shows up here before it shows up
// on screen.
#include <gtest/gtest.h>

#include <cmath>

#include "../src/cast_guns.hpp"
#include "../src/grips.hpp"

using namespace dw;

namespace {
struct Named { const char* name; const Grip* grip; };
const Named ALL[] = {{"PISTOL_RIGHT", &grips::PISTOL_RIGHT}, {"PISTOL_LEFT", &grips::PISTOL_LEFT},
                     {"SHOTGUN_RIGHT", &grips::SHOTGUN_RIGHT}, {"SHOTGUN_LEFT", &grips::SHOTGUN_LEFT}};
// Where a hold puts its wrist, in the gun's own measure (mm: u forward, v up, w right).
Vector3 wrist_in_gun(const Grip& g, bool pistol) {
    const Vector3 at = Vector3Transform({0, 0, 0}, MatrixInvert(g.hold));   // the wrist, built space
    const Vector3 o = pistol ? cast::m92fs_at(0, 0, 0) : cast::r870_at(0, 0, 0);
    return {(o.y - at.y) * 1000, (o.z - at.z) * 1000, at.x * 1000};
}
}  // namespace

TEST(Grips, EachHoldIsATrueTurnAndShift) {
    for (const Named& n : ALL) {
        const Matrix& m = n.grip->hold;
        const Vector3 c0{m.m0, m.m1, m.m2}, c1{m.m4, m.m5, m.m6}, c2{m.m8, m.m9, m.m10};
        EXPECT_NEAR(Vector3Length(c0), 1.0f, 1e-4f) << n.name;
        EXPECT_NEAR(Vector3Length(c1), 1.0f, 1e-4f) << n.name;
        EXPECT_NEAR(Vector3Length(c2), 1.0f, 1e-4f) << n.name;
        EXPECT_NEAR(Vector3DotProduct(c0, c1), 0.0f, 1e-4f) << n.name;
        EXPECT_NEAR(Vector3DotProduct(Vector3CrossProduct(c0, c1), c2), 1.0f, 1e-4f) << n.name;   // not a mirror
        EXPECT_FLOAT_EQ(m.m15, 1.0f);
    }
}

// The middle of each gripped part, in its wrist's space, is a hand's breadth away at most: the gun
// is in the hand, not floating beside it.
TEST(Grips, TheGunIsInTheHand) {
    const Vector3 pistol_grip = cast::m92fs_at(20, -75, 0), stock_wrist = cast::r870_at(-35, -60, 0), fore_end = cast::r870_at(335, -33, 0);
    const struct { const Grip* g; Vector3 part; } held[] = {
        {&grips::PISTOL_RIGHT, pistol_grip}, {&grips::PISTOL_LEFT, pistol_grip}, {&grips::SHOTGUN_RIGHT, stock_wrist}, {&grips::SHOTGUN_LEFT, fore_end}};
    for (const auto& h : held) {
        const float d = Vector3Length(Vector3Transform(h.part, h.g->hold));
        EXPECT_GT(d, 0.03f);   // past the wrist joint, in the palm
        EXPECT_LT(d, 0.13f);
    }
}

// Thumbs forward: the strong hand's wrist behind the grip on the right, the support hand's beside
// it on the left, both behind the gun and below the bore.
TEST(Grips, EachHandIsOnItsOwnSideOfThePistol) {
    const Vector3 r = wrist_in_gun(grips::PISTOL_RIGHT, true), l = wrist_in_gun(grips::PISTOL_LEFT, true);
    EXPECT_GT(r.z, 0.0f);
    EXPECT_LT(l.z, 0.0f);
    EXPECT_LT(r.x, 0.0f);   // behind the back of the slide
    EXPECT_LT(l.x, 0.0f);
    EXPECT_LT(r.y, 0.0f);   // below the bore
    EXPECT_LT(l.y, 0.0f);
    EXPECT_LT(Vector3Distance(r, l), 140.0f);   // side by side, not a forearm apart
}

// Finger joints bend one way, and not past what a hand does: the knuckles and the middle joints
// curl up to about 110 degrees and barely bend back; the thumb's root swings much further.
TEST(Grips, FingersBendWithinWhatFingersDo) {
    for (const Named& n : ALL)
        for (int k = 3; k < 15; ++k) {   // index to little (the thumb's root is a ball joint)
            const Vector3 e = n.grip->fingers[k];
            const float bend = std::sqrt(e.x * e.x + e.y * e.y + e.z * e.z);
            EXPECT_LT(bend, 2.0f) << n.name << " joint " << k;
        }
}
