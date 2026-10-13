// damned_waters/engine/tests/test_two_bone.cpp
// Purpose: the two-bone arm solve (two_bone.hpp) that keeps the survivor's left hand on a gun held
// in both hands: the wrist lands on the goal whenever it can, the elbow stays on the side the pose
// put it, the turn is a true rotation, and a goal out of reach gets the arm pointed straight at it.
// And the aim fitters' arm measures: an elbow hanging down costs nothing, a winged one does.
#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>

#include "dw/two_bone.hpp"

using namespace dw;

namespace {
// His left arm as the rig builds it: hanging, a little out from the body (7 degrees), the forearm
// a touch forward.
const Vector3 UPPER{0.035f, -0.285f, 0.004f}, FORE{0.03f, -0.255f, -0.012f};

// Where the solved arm puts the wrist (the shoulder's unturned frame).
Vector3 wrist_of(const TwoBone& s, Vector3 oe, Vector3 ow) {
    return Vector3Transform(Vector3Add(oe, Vector3Transform(ow, MatrixRotateX(s.elbow))), s.turn);
}

unsigned rng = 12345u;
float rnd() {   // 0..1, the same sequence every run
    rng ^= rng << 13;
    rng ^= rng >> 17;
    rng ^= rng << 5;
    return float(rng & 0xFFFFFF) / 16777215.0f;
}
Vector3 random_dir() {
    for (;;) {
        const Vector3 v{rnd() * 2 - 1, rnd() * 2 - 1, rnd() * 2 - 1};
        if (Vector3Length(v) > 0.2f && Vector3Length(v) < 1) return Vector3Normalize(v);
    }
}
}  // namespace

TEST(TwoBone, PutsTheWristOnAnyGoalWithinReach) {
    const float a = Vector3Length(UPPER), b = Vector3Length(FORE);
    for (int i = 0; i < 500; ++i) {
        // Anywhere from a sharply bent arm to nearly straight (the elbow stops at 2.6 radians).
        const float reach = Lerp(0.6f * (a + b), 0.995f * (a + b), rnd());
        const Vector3 goal = Vector3Scale(random_dir(), reach);
        const TwoBone s = solve_two_bone(UPPER, FORE, goal, random_dir());
        const Vector3 w = wrist_of(s, UPPER, FORE);
        EXPECT_LT(Vector3Distance(w, goal), 1e-4f) << "goal " << goal.x << " " << goal.y << " " << goal.z;
        EXPECT_GE(s.elbow, 0.0f);   // elbows bend one way
    }
}

TEST(TwoBone, KeepsTheElbowWhereThePoseHadIt) {
    for (int i = 0; i < 200; ++i) {
        const Vector3 goal = Vector3Scale(random_dir(), 0.4f);
        const Vector3 hint = random_dir();
        const TwoBone s = solve_two_bone(UPPER, FORE, goal, hint);
        // The arm's hinge, squared to shoulder-to-wrist, lies along the hint squared to the goal's
        // direction: of all the ways round the goal the elbow could go, the one nearest the pose.
        const Vector3 v = Vector3Add(UPPER, Vector3Transform(FORE, MatrixRotateX(s.elbow)));
        const Vector3 vn = Vector3Normalize(v), gn = Vector3Normalize(goal);
        const Vector3 x{1, 0, 0};
        const Vector3 built = Vector3Normalize(Vector3Subtract(x, Vector3Scale(vn, Vector3DotProduct(x, vn))));
        const Vector3 want = Vector3Normalize(Vector3Subtract(hint, Vector3Scale(gn, Vector3DotProduct(hint, gn))));
        const Vector3 got = Vector3Transform(built, s.turn);
        EXPECT_GT(Vector3DotProduct(got, want), 0.9999f);
    }
}

TEST(TwoBone, TheTurnIsARotation) {
    for (int i = 0; i < 100; ++i) {
        const TwoBone s = solve_two_bone(UPPER, FORE, Vector3Scale(random_dir(), 0.35f), random_dir());
        const Matrix& m = s.turn;
        const Vector3 c0{m.m0, m.m1, m.m2}, c1{m.m4, m.m5, m.m6}, c2{m.m8, m.m9, m.m10};
        EXPECT_NEAR(Vector3Length(c0), 1.0f, 1e-5f);
        EXPECT_NEAR(Vector3Length(c1), 1.0f, 1e-5f);
        EXPECT_NEAR(Vector3DotProduct(c0, c1), 0.0f, 1e-5f);
        EXPECT_NEAR(Vector3DotProduct(c1, c2), 0.0f, 1e-5f);
        EXPECT_NEAR(Vector3DotProduct(Vector3CrossProduct(c0, c1), c2), 1.0f, 1e-5f);   // not a mirror
        EXPECT_FLOAT_EQ(m.m12, 0.0f);   // and no shift
    }
}

TEST(TwoBone, AGoalOutOfReachGetsTheArmPointedStraightAtIt) {
    const Vector3 goal{0.1f, 0.2f, -1.4f};   // well past his fingertips
    const TwoBone s = solve_two_bone(UPPER, FORE, goal, {1, 0, 0});
    const Vector3 w = wrist_of(s, UPPER, FORE);
    EXPECT_GT(Vector3DotProduct(Vector3Normalize(w), Vector3Normalize(goal)), 0.9999f);
    EXPECT_LT(s.elbow, 0.1f);   // as straight as this arm goes
}

TEST(TwoBone, ReachingForwardBendsTheElbowForward) {
    // A hand brought up in front of the chest, half the arm's length out: the forearm swings
    // forward (-z, where he faces) of the elbow, as elbows do.
    const Vector3 goal{0.05f, -0.15f, -0.3f};
    const TwoBone s = solve_two_bone(UPPER, FORE, goal, {1, 0, 0});
    const Vector3 elbow = Vector3Transform(UPPER, s.turn), w = wrist_of(s, UPPER, FORE);
    EXPECT_GT(s.elbow, 0.5f);
    EXPECT_LT(w.z, elbow.z);
    EXPECT_LT(elbow.y, 0.0f);   // the elbow down, below the shoulder, with the hinge across the body
}

// The aim fitters' elbow measures. Shoulder at the origin, the hand out in front (-z) at shoulder
// height: the elbow below the line hangs down, out to the side or above it doesn't.
TEST(ArmLook, AnElbowHangingDownCostsNothingAWingedOneDoes) {
    const Vector3 sh{0, 0, 0}, wr{0, 0, -0.5f};
    EXPECT_FLOAT_EQ(elbow_not_down(sh, {0, -0.08f, -0.25f}, wr), 0.0f);           // straight down
    EXPECT_FLOAT_EQ(elbow_not_down(sh, {0.04f, -0.08f, -0.25f}, wr), 0.0f);       // down and a little out
    EXPECT_GT(elbow_not_down(sh, {0.08f, 0, -0.25f}, wr), 5.0f);                   // winged out level
    EXPECT_GT(elbow_not_down(sh, {0, 0.08f, -0.25f}, wr), elbow_not_down(sh, {0.08f, 0, -0.25f}, wr));   // up is worse
    EXPECT_FLOAT_EQ(elbow_not_down(sh, {0, 0, -0.25f}, wr), 0.0f);                 // a straight arm points nowhere
}

TEST(ArmLook, BendIsTheAngleBetweenUpperArmAndForearm) {
    EXPECT_NEAR(elbow_bend({0, 0, 0}, {0, 0, -0.3f}, {0, 0, -0.6f}), 0.0f, 1e-3f);       // straight
    EXPECT_NEAR(elbow_bend({0, 0, 0}, {0, -0.3f, 0}, {0, -0.3f, -0.3f}), PI / 2, 1e-5f);  // a right angle
}

// Blending two joint turns goes the short way round and lands on each end.
TEST(SlerpAngles, EndsAndMiddle) {
    const Vector3 a{0.3f, -0.2f, 0.1f}, b{1.1f, 0.4f, -0.5f};
    const Vector3 a0 = slerp_angles(a, b, 0), b1 = slerp_angles(a, b, 1);
    EXPECT_NEAR(a0.x, a.x, 1e-4f); EXPECT_NEAR(a0.y, a.y, 1e-4f); EXPECT_NEAR(a0.z, a.z, 1e-4f);
    EXPECT_NEAR(b1.x, b.x, 1e-4f); EXPECT_NEAR(b1.y, b.y, 1e-4f); EXPECT_NEAR(b1.z, b.z, 1e-4f);
    // A bend about one axis blends to half that bend about the same axis.
    const Vector3 h = slerp_angles({0, 0, 0}, {0.8f, 0, 0}, 0.5f);
    EXPECT_NEAR(h.x, 0.4f, 1e-4f); EXPECT_NEAR(h.y, 0.0f, 1e-4f); EXPECT_NEAR(h.z, 0.0f, 1e-4f);
}

// The same turn, written the way nearest the one asked for: the 870 aim's left shoulder is written
// with its arm swung right over (x near pi), and the slerp writes it the other way; angles_near
// gives it back as the table has it, so the easing that follows goes the short way.
TEST(AnglesNear, TheSameTurnWrittenTheNearestWay) {
    auto turn = [](Vector3 e) { return MatrixMultiply(MatrixMultiply(MatrixRotateZ(e.z), MatrixRotateX(e.x)), MatrixRotateY(e.y)); };
    auto same = [&](Vector3 a, Vector3 b) {
        const Matrix m = turn(a), n = turn(b);
        const float* p = &m.m0;
        const float* q = &n.m0;
        float worst = 0;
        for (int i = 0; i < 16; ++i) worst = std::max(worst, std::fabs(p[i] - q[i]));
        return worst;
    };
    const Vector3 table{3.065f, -1.296f, -1.078f};
    const Vector3 slerped = slerp_angles(table, table, 1);   // (the first way: x within +-90 degrees)
    EXPECT_LT(same(slerped, table), 1e-4f);
    EXPECT_GT(std::fabs(slerped.x - table.x), 2.0f);
    const Vector3 back = angles_near(slerped, table);
    EXPECT_NEAR(back.x, table.x, 1e-4f);
    EXPECT_NEAR(back.y, table.y, 1e-4f);
    EXPECT_NEAR(back.z, table.z, 1e-4f);
    // Any turn, put near any other: still the same turn, and never further than it was.
    const Vector3 turns[] = {{0.3f, -0.2f, 0.1f}, {1.4f, 2.9f, -3.0f}, {-1.2f, 0.4f, 2.5f}, {2.8f, -2.6f, 0.9f}};
    for (const Vector3& e : turns)
        for (const Vector3& like : turns) {
            const Vector3 n = angles_near(e, like);
            EXPECT_LT(same(n, e), 1e-4f);
            EXPECT_LE(Vector3Distance(n, like), Vector3Distance(e, like) + 1e-4f);
        }
    // Whole turns are taken off too: 350 degrees near 0 is -10.
    EXPECT_NEAR(angles_near({0.1f, 0, 6.1f}, {0, 0, 0}).z, 6.1f - 2 * PI, 1e-4f);
}

// A turn about the forearm's line is all twist; one across it all swing; and a mix splits back
// into the two it was made of.
TEST(SwingTwist, SplitsAWristTurn) {
    float sw = 0, tw = 0;
    swing_twist(QuaternionFromAxisAngle({0, 1, 0}, 0.7f), {0, 1, 0}, sw, tw);
    EXPECT_NEAR(tw, 0.7f, 1e-4f);
    EXPECT_NEAR(sw, 0.0f, 1e-3f);
    swing_twist(QuaternionFromAxisAngle({1, 0, 0}, 0.5f), {0, 1, 0}, sw, tw);
    EXPECT_NEAR(tw, 0.0f, 1e-4f);
    EXPECT_NEAR(sw, 0.5f, 1e-4f);
    const Quaternion mix = QuaternionMultiply(QuaternionFromAxisAngle({0, 0, 1}, 0.4f), QuaternionFromAxisAngle({0, 1, 0}, -1.2f));   // twist, then swing
    swing_twist(mix, {0, 1, 0}, sw, tw);
    EXPECT_NEAR(sw, 0.4f, 1e-3f);
    EXPECT_NEAR(tw, -1.2f, 1e-3f);
}
