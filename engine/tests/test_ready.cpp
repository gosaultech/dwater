// damned_waters/engine/tests/test_ready.cpp
// Purpose: GoogleTest suite for trigger discipline (ready.hpp): the trigger finger stays off the
// trigger until he's aiming with the gun nearly up, comes off the moment he stops aiming (faster
// than it went on), stays off through anything that isn't aiming, and blends smoothly between its
// two places. Played frame by frame as the game plays it, at 60 frames a second.
#include <gtest/gtest.h>

#include "dw/core.hpp"
#include "dw/ready.hpp"

using namespace dw;

namespace {
constexpr float DT = 1.0f / 60;
// The arms ease at this sharpness (Character::animate, a pose that isn't a sharp one).
float k() { return smoothing(9.0f, DT); }
}  // namespace

TEST(Ready, TheRaiseFollowsTheArmsUpAndDown) {
    float r = 0;
    for (int f = 0; f < 60; ++f) r = ready::raise(r, true, k());
    EXPECT_GT(r, 0.99f);   // a second of aiming: up
    for (int f = 0; f < 60; ++f) r = ready::raise(r, false, k());
    EXPECT_LT(r, 0.01f);   // a second at the ready: down
    EXPECT_FLOAT_EQ(ready::raise(0.5f, true, 2.0f), 1.0f);   // (an ease past all the way is all the way)
}

// From the ready, the finger leaves the frame only once the gun is most of the way up, and is on
// the trigger within about a third of a second of starting to aim.
TEST(Ready, TheFingerGoesOnOnlyOnceTheGunIsUp) {
    float r = 0, finger = 0;
    int first_moved = -1, on_at = -1;
    for (int f = 0; f < 60; ++f) {
        r = ready::raise(r, true, k());
        finger = ready::finger(finger, true, r, DT);
        if (finger > 0 && first_moved < 0) {
            first_moved = f;
            EXPECT_GE(r, ready::FINGER_IN_AT);   // not before the gun's up
        }
        if (finger >= 1 && on_at < 0) on_at = f;
    }
    ASSERT_GE(first_moved, 0);
    ASSERT_GE(on_at, 0);
    EXPECT_GT(first_moved, 5);                   // not the moment he starts to aim
    EXPECT_LT(float(on_at + 1) * DT, 0.35f);      // on the trigger in about a third of a second
}

// Letting go of the aim, the finger is off the trigger before the gun is far down.
TEST(Ready, TheFingerComesOffFirst) {
    float r = 1, finger = 1;
    int off_at = -1;
    for (int f = 0; f < 60 && off_at < 0; ++f) {
        r = ready::raise(r, false, k());
        finger = ready::finger(finger, false, r, DT);
        if (finger <= 0) off_at = f;
    }
    ASSERT_GE(off_at, 0);
    EXPECT_LE(float(off_at + 1) * DT, ready::FINGER_OFF + DT);   // (to the frame)
    EXPECT_GT(r, 0.4f);   // the gun not yet halfway down
    EXPECT_LT(ready::FINGER_OFF, ready::FINGER_ON);
}

// Not aiming, however far up the gun is (a reload ends with it pushed out), the finger stays off.
TEST(Ready, NotAimingTheFingerStaysOff) {
    float finger = 0;
    for (int f = 0; f < 120; ++f) finger = ready::finger(finger, false, 1.0f, DT);
    EXPECT_EQ(finger, 0.0f);
    // Aiming with the gun still low (a dodge out of the aim, an aim just begun): still off.
    for (int f = 0; f < 120; ++f) finger = ready::finger(finger, true, ready::FINGER_IN_AT - 0.01f, DT);
    EXPECT_EQ(finger, 0.0f);
}

// The blend eases in and out: it starts and ends still, and never overshoots.
TEST(Ready, TheBlendEasesInAndOut) {
    EXPECT_FLOAT_EQ(ready::blend(0), 0.0f);
    EXPECT_FLOAT_EQ(ready::blend(1), 1.0f);
    EXPECT_FLOAT_EQ(ready::blend(0.5f), 0.5f);
    EXPECT_LT(ready::blend(0.05f), 0.05f);   // slow away from the frame
    EXPECT_GT(ready::blend(0.95f), 0.95f);   // and slow onto the trigger
    float last = 0;
    for (int i = 0; i <= 100; ++i) {
        const float b = ready::blend(float(i) / 100);
        EXPECT_GE(b, last);
        last = b;
    }
    EXPECT_FLOAT_EQ(ready::blend(-1), 0.0f);
    EXPECT_FLOAT_EQ(ready::blend(2), 1.0f);
}
