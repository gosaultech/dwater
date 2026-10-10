// damned_waters/engine/tests/test_grips.cpp
// Purpose: GoogleTest suite for the fitted grips (grips_fitted.inc, written by --fitgrips): each one
// places the gun (or the magazine, or the shell, the left hand loads) by a true rotation and shift
// (no stretch, no mirror), puts it in the hand rather than somewhere near it, keeps each hand on its
// own side of the pistol, and bends the fingers within what finger joints do. And trigger
// discipline: off the trigger, the forefinger lies straight along the side of the frame (or the
// 870's receiver) above the trigger guard, never inside it, the rest of the hand as it holds the
// gun to shoot. A refit that went wrong shows up here before it shows up on screen.
#include <gtest/gtest.h>

#include <cmath>

#include "../src/cast_guns.hpp"
#include "../src/grips.hpp"
#include "dw/character_file.hpp"
#include "dw/room_spec.hpp"

using namespace dw;

namespace {
struct Named { const char* name; const Grip* grip; };
const Named ALL[] = {{"PISTOL_RIGHT", &grips::PISTOL_RIGHT}, {"PISTOL_LEFT", &grips::PISTOL_LEFT},
                     {"SHOTGUN_RIGHT", &grips::SHOTGUN_RIGHT}, {"SHOTGUN_LEFT", &grips::SHOTGUN_LEFT},
                     {"MAG_LEFT", &grips::MAG_LEFT}, {"SHELL_LEFT", &grips::SHELL_LEFT},
                     {"PISTOL_RIGHT_INDEXED", &grips::PISTOL_RIGHT_INDEXED}, {"SHOTGUN_RIGHT_INDEXED", &grips::SHOTGUN_RIGHT_INDEXED}};
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
// (the magazine, the shell) is in the hand, not floating beside it.
TEST(Grips, TheGunIsInTheHand) {
    const Vector3 pistol_grip = cast::m92fs_at(20, -75, 0), stock_wrist = cast::r870_at(-35, -60, 0), fore_end = cast::r870_at(335, -33, 0);
    const Vector3 magazine = cast::m92fs_at(10, -118), shell = cast::r870_at(140, -27);   // (a magazine's base; a shell's brass, at the thumb)
    const struct { const Grip* g; Vector3 part; } held[] = {
        {&grips::PISTOL_RIGHT, pistol_grip}, {&grips::PISTOL_LEFT, pistol_grip}, {&grips::SHOTGUN_RIGHT, stock_wrist}, {&grips::SHOTGUN_LEFT, fore_end},
        {&grips::MAG_LEFT, magazine}, {&grips::SHELL_LEFT, shell}};
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

namespace {
// The right forefinger as a grip bends it, in the gun's own measure (mm: u forward, v up, w to its
// right): its three joints and its tip, on his own skeleton (the survivor's .dwc), the way the
// rig poses a finger (each joint turned, then carried along from the wrist).
struct FingerAt { Vector3 at[4]; };
FingerAt forefinger(const Grip& g, bool pistol) {
    const CharacterFile f = CharacterFile::load(repo_root() + "/engine/assets/characters/survivor.dwc");
    FingerAt out{};
    if (!f.ok() || f.joints.size() != size_t(J_COUNT)) return out;
    auto rest = [&](int j) { return Vector3{f.joints[size_t(j)][0], f.joints[size_t(j)][1], f.joints[size_t(j)][2]}; };
    Matrix L = MatrixIdentity();   // the wrist's frame
    Vector3 p[3];
    for (int k = 0; k < 3; ++k) {
        const int j = finger_joint(true, F_INDEX, k), parent = k == 0 ? J_WRI_R : j - 1;
        const Vector3 off = Vector3Subtract(rest(j), rest(parent)), e = g.fingers[F_INDEX * 3 + k];
        const Matrix R = MatrixMultiply(MatrixMultiply(MatrixRotateZ(e.z), MatrixRotateX(e.x)), MatrixRotateY(e.y));
        L = MatrixMultiply(MatrixMultiply(R, MatrixTranslate(off.x, off.y, off.z)), L);
        p[k] = Vector3Transform({0, 0, 0}, L);
    }
    // The tip: past the last joint by about as far as the middle segment is long.
    const Vector3 last = Vector3Subtract(rest(finger_joint(true, F_INDEX, 2)), rest(finger_joint(true, F_INDEX, 1)));
    const Vector3 tip = Vector3Transform(Vector3Scale(last, 0.9f), L);
    const Vector3 o = pistol ? cast::m92fs_at(0, 0, 0) : cast::r870_at(0, 0, 0);
    const Matrix to_gun = MatrixInvert(g.hold);
    const Vector3 pts[4] = {p[0], p[1], p[2], tip};
    for (int i = 0; i < 4; ++i) {
        const Vector3 q = Vector3Transform(pts[i], to_gun);
        out.at[i] = {(o.y - q.y) * 1000, (o.z - q.z) * 1000, q.x * 1000};
    }
    return out;
}
// Inside the trigger guard: between its sides, below the frame, within its loop (cast_guns.cpp).
bool in_guard(Vector3 p, bool pistol) {
    if (std::fabs(p.z) > 6) return false;
    return pistol ? p.x > 56 && p.x < 116 && p.y < -28 && p.y > -57 : p.x > 16 && p.x < 87 && p.y < -45 && p.y > -73;
}
}  // namespace

// Off the trigger, the hand doesn't move on the gun: the same hold, the same thumb and the same
// three gripping fingers; only the forefinger is different.
TEST(Grips, OffTheTriggerOnlyTheForefingerMoves) {
    const struct { const Grip* shoot; const Grip* off; } pairs[] = {{&grips::PISTOL_RIGHT, &grips::PISTOL_RIGHT_INDEXED},
                                                                 {&grips::SHOTGUN_RIGHT, &grips::SHOTGUN_RIGHT_INDEXED}};
    for (const auto& pr : pairs) {
        const float* a = &pr.shoot->hold.m0;
        const float* b = &pr.off->hold.m0;
        for (int i = 0; i < 16; ++i) EXPECT_FLOAT_EQ(a[i], b[i]);
        float moved = 0;
        for (int k = 0; k < 15; ++k) {
            const Vector3 d = Vector3Subtract(pr.shoot->fingers[k], pr.off->fingers[k]);
            if (k / 3 == F_INDEX) moved += Vector3Length(d);
            else EXPECT_LT(Vector3Length(d), 1e-6f) << "joint " << k;
        }
        EXPECT_GT(moved, 0.3f);   // (and the forefinger really has come off the trigger)
    }
}

// Indexed: straight out (its last two joints barely bent), along the right side of the frame, its
// tip above the trigger guard and forward of the trigger, no part of it inside the guard. On the
// trigger (the grip he shoots with), its tip is inside the guard: the test can tell the two apart.
TEST(Grips, TheForefingerLiesAlongTheFrameOutsideTheGuard) {
    for (bool pistol : {true, false}) {
        const Grip& off = pistol ? grips::PISTOL_RIGHT_INDEXED : grips::SHOTGUN_RIGHT_INDEXED;
        const Grip& shoot = pistol ? grips::PISTOL_RIGHT : grips::SHOTGUN_RIGHT;
        const FingerAt f = forefinger(off, pistol), on = forefinger(shoot, pistol);
        ASSERT_NE(Vector3Length(f.at[3]), 0.0f) << "survivor.dwc";
        for (int k = 1; k < 3; ++k) EXPECT_LT(Vector3Length(off.fingers[F_INDEX * 3 + k]), 0.3f) << "joint " << k;   // straight
        for (int i = 0; i < 4; ++i) EXPECT_FALSE(in_guard(f.at[i], pistol)) << (pistol ? "M92FS" : "870") << " point " << i;
        const Vector3 tip = f.at[3];
        const float trigger_u = pistol ? 80.0f : 30.0f, guard_top = pistol ? -28.0f : -45.0f, side = pistol ? 11.0f : 16.0f;
        EXPECT_GT(tip.x, trigger_u) << (pistol ? "M92FS" : "870");   // forward of the trigger
        EXPECT_GT(tip.y, guard_top) << (pistol ? "M92FS" : "870");   // above the guard
        EXPECT_GT(tip.z, side - 3) << (pistol ? "M92FS" : "870");    // against the right side, not in the frame
        EXPECT_LT(tip.z, side + 20) << (pistol ? "M92FS" : "870");   //   nor off in the air beside it
        EXPECT_TRUE(in_guard(on.at[3], pistol) || in_guard(on.at[2], pistol)) << (pistol ? "M92FS" : "870");
    }
}
