// damned_waters/engine/tests/test_controls.cpp
// Purpose: GoogleTest suite for the controls (dw/controls.hpp): the three controller layouts, the
// keyboard layout, and the stick maths (dead zone, walk-to-run, weight, flicks, body aim).
#include <gtest/gtest.h>
#include <cmath>
#include <cstdio>
#include <set>
#include <string>

#include "dw/controls.hpp"
#include "dw/settings.hpp"

using namespace dw;

namespace {
float len(Vector2 v) { return std::sqrt(v.x * v.x + v.y * v.y); }
// The actions you use while playing (the menu ones may share buttons with them on purpose).
constexpr int GAMEPLAY[] = {ACT_AIM, ACT_FIRE, ACT_DODGE, ACT_KICK, ACT_QUICK_TURN, ACT_RELOAD, ACT_STATUS,
                            ACT_FLASHLIGHT, ACT_WEAPON_NEXT, ACT_WEAPON_1, ACT_WEAPON_2, ACT_PAUSE};
}  // namespace

// ── Layouts ───────────────────────────────────────────────────────────────────────
TEST(Layouts, EveryLayoutBindsEveryGameplayActionOnce) {
    for (int s = 0; s < int(Scheme::Count); ++s) {
        std::set<int> used;
        for (int a : GAMEPLAY) {
            const int b = pad_button(Scheme(s), a);
            EXPECT_NE(b, 0) << scheme_name(Scheme(s)) << " leaves " << act_name(a) << " unbound";
            EXPECT_TRUE(used.insert(b).second) << scheme_name(Scheme(s)) << ": two actions on one button (" << act_name(a) << ")";
        }
    }
}

TEST(Layouts, TypeAIsTheREMakeLayoutTheDirectorChose) {
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_AIM), GAMEPAD_BUTTON_LEFT_TRIGGER_2);       // L2
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_FIRE), GAMEPAD_BUTTON_RIGHT_TRIGGER_2);     // R2
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_DODGE), GAMEPAD_BUTTON_RIGHT_TRIGGER_1);    // R1
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_INTERACT), GAMEPAD_BUTTON_RIGHT_FACE_DOWN); // Cross
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_KICK), GAMEPAD_BUTTON_RIGHT_FACE_DOWN);     // Cross: what's in front of you
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_QUICK_TURN), GAMEPAD_BUTTON_RIGHT_FACE_RIGHT);   // Circle
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_RELOAD), GAMEPAD_BUTTON_RIGHT_FACE_LEFT);   // Square
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_STATUS), GAMEPAD_BUTTON_RIGHT_FACE_UP);     // Triangle
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_FLASHLIGHT), GAMEPAD_BUTTON_LEFT_TRIGGER_1);   // L1
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_WEAPON_1), GAMEPAD_BUTTON_LEFT_FACE_LEFT);  // D-pad
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_WEAPON_2), GAMEPAD_BUTTON_LEFT_FACE_RIGHT);
}

TEST(Layouts, TheKeyboardCoversEveryAction) {
    for (int a = 0; a < ACT_COUNT; ++a) {
        if (a == ACT_AIM || a == ACT_FIRE) continue;       // (also the mouse buttons)
        EXPECT_NE(key_binding(a).a, 0) << act_name(a);
    }
    EXPECT_EQ(key_binding(ACT_DODGE).a, KEY_SPACE);
}

// ── Sticks ────────────────────────────────────────────────────────────────────────
TEST(Sticks, ARestingStickIsStillAndAFullPushReachesOne) {
    EXPECT_EQ(len(radial_deadzone({0.1f, 0.1f})), 0.0f);  // drift inside the dead zone
    EXPECT_NEAR(len(radial_deadzone({0.96f, 0.0f})), 1.0f, 1e-5f);
    EXPECT_NEAR(len(radial_deadzone({0.7f, 0.7f})), 1.0f, 1e-5f);   // diagonals too
    const Vector2 v = radial_deadzone({0.0f, 0.5f});
    EXPECT_EQ(v.x, 0.0f);                                 // it keeps its direction
    EXPECT_GT(v.y, 0.0f);
    EXPECT_LT(len(radial_deadzone({0.2f, 0.0f})), 0.05f); // just past the dead zone starts near zero
}

TEST(Sticks, HalfATiltWalksAndAFullTiltRuns) {
    EXPECT_FLOAT_EQ(stick_speed(0.0f, 1.9f, 3.8f), 0.0f);
    EXPECT_FLOAT_EQ(stick_speed(0.6f, 1.9f, 3.8f), 1.9f);
    EXPECT_FLOAT_EQ(stick_speed(1.0f, 1.9f, 3.8f), 3.8f);
    EXPECT_GT(stick_speed(0.8f, 1.9f, 3.8f), 1.9f);
}

TEST(Sticks, VelocityGetsThereInAFewFramesNotAtOnce) {
    Vector2 v{0, 0};
    const Vector2 run{0, 3.8f};
    int frames = 0;
    while (len({run.x - v.x, run.y - v.y}) > 1e-4f && frames < 100) { v = approach(v, run, 24.0f / 60.0f); ++frames; }
    EXPECT_GE(frames, 8);                                  // weight...
    EXPECT_LE(frames, 12);                                 // ...but at full run within a fifth of a second
}

TEST(Sticks, AFlickSwitchesButAHeldPushDoesNot) {
    FlickDetector f;
    EXPECT_EQ(f.update({0.95f, 0.0f}, 1.0f / 60), 0);      // pushed hard right
    EXPECT_EQ(f.update({0.95f, 0.0f}, 1.0f / 60), 0);
    EXPECT_EQ(f.update({0.0f, 0.0f}, 1.0f / 60), 1);       // let go at once: a flick to the right
    FlickDetector g;
    for (int i = 0; i < 30; ++i) EXPECT_EQ(g.update({-0.95f, 0.0f}, 1.0f / 60), 0);   // held half a second: aiming at an arm
    EXPECT_EQ(g.update({0.0f, 0.0f}, 1.0f / 60), 0);
    FlickDetector h;
    EXPECT_EQ(h.update({0.0f, 0.95f}, 1.0f / 60), 0);      // straight up is the head, never a flick
    EXPECT_EQ(h.update({0.0f, 0.0f}, 1.0f / 60), 0);
}

TEST(Sticks, TheStickIsACursorOverTheBody) {
    EXPECT_EQ(body_aim({0.0f, 0.0f}).at, AimAt::Torso);
    EXPECT_EQ(body_aim({0.0f, 1.0f}).at, AimAt::Head);
    EXPECT_EQ(body_aim({-1.0f, 0.1f}).at, AimAt::ArmLeft);
    EXPECT_EQ(body_aim({1.0f, -0.2f}).at, AimAt::ArmRight);
    EXPECT_EQ(body_aim({-0.3f, -1.0f}).at, AimAt::LegLeft);
    EXPECT_EQ(body_aim({0.3f, -1.0f}).at, AimAt::LegRight);
    EXPECT_FLOAT_EQ(body_aim({0.0f, 1.0f}).k, 1.0f);       // all the way: the head itself
    EXPECT_LT(body_aim({0.0f, 0.5f}).k, 1.0f);             // half way: between chest and head
}

// ── Options ───────────────────────────────────────────────────────────────────────
TEST(Settings, TheyComeBackAfterARestart) {
    const std::string path = testing::TempDir() + "dw_settings_test.db";
    std::remove(path.c_str());
    EXPECT_EQ(Settings::load(path).scheme, Scheme::TypeA);   // nothing saved yet: the defaults
    EXPECT_FALSE(Settings::load(path).slowmo);
    Settings s;
    s.scheme = Scheme::TypeC;
    s.slowmo = true;
    EXPECT_TRUE(s.save(path));
    const Settings r = Settings::load(path);
    EXPECT_EQ(r.scheme, Scheme::TypeC);
    EXPECT_TRUE(r.slowmo);
    EXPECT_FALSE(r.tank);
    s.scheme = Scheme::TypeB;                              // saving again replaces, doesn't duplicate
    EXPECT_TRUE(s.save(path));
    EXPECT_EQ(Settings::load(path).scheme, Scheme::TypeB);
    std::remove(path.c_str());
}
