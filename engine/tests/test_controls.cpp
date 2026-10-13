// damned_waters/engine/tests/test_controls.cpp
// Purpose: GoogleTest suite for the controls (dw/controls.hpp): the three controller layouts, the
// keyboard layout, the stick maths (dead zone, weight, flicks, body aim), the gaits (sneak, walk,
// run by tilt with hysteresis, and the run options), and the stick-back quick turn's chord.
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
        if (a == ACT_BACK_TURN) continue;                  // a pad's chord: the keys have Q
        EXPECT_NE(key_binding(a).a, 0) << act_name(a);
    }
    EXPECT_EQ(key_binding(ACT_DODGE).a, KEY_SPACE);
}

TEST(Layouts, TheSneakKeyIsCtrlAndCollidesWithNothing) {
    EXPECT_EQ(key_binding(ACT_SNEAK).a, KEY_LEFT_CONTROL);
    const KeyPair sneak = key_binding(ACT_SNEAK);
    for (int a = 0; a < ACT_COUNT; ++a) {
        if (a == ACT_SNEAK) continue;
        const KeyPair k = key_binding(a);
        for (int key : {k.a, k.b})
            if (key) EXPECT_TRUE(key != sneak.a && key != sneak.b) << act_name(a) << " shares the sneak key";
    }
    for (int key : {KEY_W, KEY_A, KEY_S, KEY_D, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_T, KEY_F3})   // movement, tank, debug
        EXPECT_TRUE(key != sneak.a && key != sneak.b);
    EXPECT_EQ(key_binding(ACT_RUN_HOLD).a, KEY_LEFT_SHIFT);   // Shift still runs
    EXPECT_LT(KEY_TILT_SNEAK, TiltTiers::WALK - TiltTiers::BAND);   // the keys' tilts sit well inside their gaits
    EXPECT_GT(KEY_TILT_SNEAK, TiltTiers::SNEAK);
    EXPECT_GT(KEY_TILT_WALK, TiltTiers::WALK);
    EXPECT_LT(KEY_TILT_WALK, TiltTiers::RUN - TiltTiers::BAND);
    EXPECT_GE(KEY_TILT_RUN, TiltTiers::RUN);
}

TEST(Layouts, TheHoldToRunButtonIsOneThatDoesNothingOutsideTheAim) {
    // Every action you can use while moving about, which the run button must never be.
    const int moving_about[] = {ACT_AIM, ACT_DODGE, ACT_INTERACT, ACT_KICK, ACT_QUICK_TURN, ACT_RELOAD, ACT_STATUS, ACT_FLASHLIGHT,
                                ACT_WEAPON_NEXT, ACT_WEAPON_1, ACT_WEAPON_2, ACT_RUN, ACT_PAUSE, ACT_BACK_TURN};
    for (int s = 0; s < int(Scheme::Count); ++s) {
        const int run = pad_button(Scheme(s), ACT_RUN_HOLD);
        EXPECT_NE(run, 0);
        EXPECT_EQ(run, pad_button(Scheme(s), ACT_FIRE)) << scheme_name(Scheme(s));   // it fires only while aiming
        for (int a : moving_about) EXPECT_NE(run, pad_button(Scheme(s), a)) << scheme_name(Scheme(s)) << ": " << act_name(a);
        EXPECT_EQ(pad_button(Scheme(s), ACT_RUN), GAMEPAD_BUTTON_LEFT_THUMB);          // the click is L3
        EXPECT_EQ(pad_button(Scheme(s), ACT_SNEAK), 0);                               // a pad sneaks by touch
    }
    EXPECT_EQ(pad_button(Scheme::TypeA, ACT_RUN_HOLD), GAMEPAD_BUTTON_RIGHT_TRIGGER_2);   // R2
    EXPECT_EQ(pad_button(Scheme::TypeB, ACT_RUN_HOLD), GAMEPAD_BUTTON_RIGHT_TRIGGER_1);   // R1
    EXPECT_EQ(pad_button(Scheme::TypeC, ACT_RUN_HOLD), GAMEPAD_BUTTON_RIGHT_TRIGGER_2);   // R2
}

TEST(Layouts, BackPlusTheRightFaceButtonOnEveryPad) {
    for (int s = 0; s < int(Scheme::Count); ++s) EXPECT_EQ(pad_button(Scheme(s), ACT_BACK_TURN), GAMEPAD_BUTTON_RIGHT_FACE_RIGHT);
    EXPECT_FALSE(back_turn_shares_dodge(Scheme::TypeA));   // Circle turns on its own there
    EXPECT_TRUE(back_turn_shares_dodge(Scheme::TypeB));    // Circle dodges: the chord tells them apart
    EXPECT_TRUE(back_turn_shares_dodge(Scheme::TypeC));
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

// ── Gaits ─────────────────────────────────────────────────────────────────────────
namespace {
Gait tier_of(float tilt) { TiltTiers t; return t.update(tilt); }   // from rest
}  // namespace

TEST(Gaits, ALightTouchSneaksHalfWalksAllTheWayRuns) {
    EXPECT_EQ(tier_of(0.0f), Gait::Still);
    EXPECT_EQ(tier_of(0.05f), Gait::Still);
    EXPECT_EQ(tier_of(0.2f), Gait::Sneak);
    EXPECT_EQ(tier_of(0.6f), Gait::Walk);
    EXPECT_EQ(tier_of(1.0f), Gait::Run);   // straight there from rest, in one frame
    // On the raw stick (through the dead zone): a quarter of the way sneaks, two thirds walks, all of it runs.
    EXPECT_EQ(tier_of(len(radial_deadzone({0.0f, 0.3f}))), Gait::Sneak);
    EXPECT_EQ(tier_of(len(radial_deadzone({0.0f, 0.65f}))), Gait::Walk);
    EXPECT_EQ(tier_of(len(radial_deadzone({0.0f, 1.0f}))), Gait::Run);
    EXPECT_EQ(tier_of(len(radial_deadzone({0.66f, 0.66f}))), Gait::Run);   // a diagonal all the way too
    EXPECT_EQ(tier_of(len(radial_deadzone({0.0f, 0.15f}))), Gait::Still);  // resting drift
}

TEST(Gaits, AThumbOnABoundaryDoesNotFlicker) {
    TiltTiers t;
    EXPECT_EQ(t.update(0.6f), Gait::Walk);
    // Wobbling just either side of the walk/sneak boundary: it stays a walk...
    for (int i = 0; i < 60; ++i) EXPECT_EQ(t.update(TiltTiers::WALK + (i % 2 ? 0.02f : -0.03f)), Gait::Walk);
    // ...until the thumb clearly eases off; then wobbling there stays a sneak.
    EXPECT_EQ(t.update(TiltTiers::WALK - TiltTiers::BAND - 0.01f), Gait::Sneak);
    for (int i = 0; i < 60; ++i) EXPECT_EQ(t.update(TiltTiers::WALK + (i % 2 ? -0.03f : -0.01f)), Gait::Sneak);
    EXPECT_EQ(t.update(TiltTiers::WALK), Gait::Walk);
    // The same at the run boundary.
    EXPECT_EQ(t.update(1.0f), Gait::Run);
    for (int i = 0; i < 60; ++i) EXPECT_EQ(t.update(TiltTiers::RUN - 0.04f), Gait::Run);
    EXPECT_EQ(t.update(0.7f), Gait::Walk);
    EXPECT_EQ(t.update(0.0f), Gait::Still);   // let go: straight to a stop
}

TEST(Gaits, SneakingIsSlowAndQuietRunningFastAndLoud) {
    EXPECT_FLOAT_EQ(gait_speed(Gait::Still), 0.0f);
    EXPECT_FLOAT_EQ(gait_speed(Gait::Sneak), 0.8f);
    EXPECT_FLOAT_EQ(gait_speed(Gait::Walk), 1.9f);
    EXPECT_FLOAT_EQ(gait_speed(Gait::Run), 3.8f);
    const Footfall s = footfall(Gait::Sneak), w = footfall(Gait::Walk), r = footfall(Gait::Run);
    EXPECT_LT(s.volume, w.volume);
    EXPECT_LT(w.volume, r.volume);
    EXPECT_LT(s.radius, w.radius);
    EXPECT_LT(w.radius, r.radius);
    EXPECT_LE(s.radius, 1.0f);              // only a Drowned at arm's length hears a sneak
    EXPECT_LT(s.stride, w.stride);           // shorter, placed steps
    EXPECT_FLOAT_EQ(footfall(Gait::Still).radius, w.radius);   // the last step of a stop
}

TEST(Gaits, AnalogRunsByTiltAndIgnoresTheButtons) {
    GaitPicker g;
    EXPECT_EQ(g.update(0.6f, false, RunMode::Analog, true, true, true), Gait::Walk);   // buttons do nothing
    EXPECT_EQ(g.update(1.0f, false, RunMode::Analog, false, false, false), Gait::Run);
    EXPECT_EQ(g.update(0.2f, false, RunMode::Analog, false, false, false), Gait::Sneak);
}

TEST(Gaits, HoldTheStickInToRun) {
    GaitPicker g;
    EXPECT_EQ(g.update(1.0f, false, RunMode::StickHold, false, false, false), Gait::Walk);   // all the way: still a walk
    EXPECT_EQ(g.update(1.0f, false, RunMode::StickHold, true, true, false), Gait::Run);
    EXPECT_EQ(g.update(1.0f, false, RunMode::StickHold, false, true, false), Gait::Run);
    EXPECT_EQ(g.update(1.0f, false, RunMode::StickHold, false, false, false), Gait::Walk);   // let go: walking
    EXPECT_EQ(g.update(0.2f, false, RunMode::StickHold, false, true, false), Gait::Sneak);   // a light touch still sneaks
}

TEST(Gaits, ClickTheStickToRunUntilItComesBack) {
    GaitPicker g;
    EXPECT_EQ(g.update(0.7f, false, RunMode::StickToggle, false, false, false), Gait::Walk);
    EXPECT_EQ(g.update(0.7f, false, RunMode::StickToggle, true, true, false), Gait::Run);    // clicked
    for (int i = 0; i < 30; ++i) EXPECT_EQ(g.update(0.9f, false, RunMode::StickToggle, false, false, false), Gait::Run);
    EXPECT_EQ(g.update(0.2f, false, RunMode::StickToggle, false, false, false), Gait::Sneak);   // eased off: a sneak
    EXPECT_EQ(g.update(0.7f, false, RunMode::StickToggle, false, false, false), Gait::Run);     // still toggled on
    EXPECT_EQ(g.update(0.0f, false, RunMode::StickToggle, false, false, false), Gait::Still);   // back to centre...
    EXPECT_EQ(g.update(0.7f, false, RunMode::StickToggle, false, false, false), Gait::Walk);    // ...ended it
    EXPECT_EQ(g.update(0.7f, false, RunMode::StickToggle, true, true, false), Gait::Run);
    EXPECT_EQ(g.update(0.7f, false, RunMode::StickToggle, true, true, false), Gait::Walk);      // clicked again: off
    GaitPicker h;   // clicked standing still, then pushed: it runs
    EXPECT_EQ(h.update(0.0f, false, RunMode::StickToggle, true, true, false), Gait::Still);
    EXPECT_EQ(h.update(0.8f, false, RunMode::StickToggle, false, false, false), Gait::Run);
}

TEST(Gaits, HoldAButtonToRun) {
    GaitPicker g;
    EXPECT_EQ(g.update(1.0f, false, RunMode::HoldButton, false, false, false), Gait::Walk);
    EXPECT_EQ(g.update(0.6f, false, RunMode::HoldButton, false, false, true), Gait::Run);    // half way + the button
    EXPECT_EQ(g.update(0.2f, false, RunMode::HoldButton, false, false, true), Gait::Sneak);  // a light touch still sneaks
    EXPECT_EQ(g.update(1.0f, false, RunMode::HoldButton, true, true, false), Gait::Walk);    // L3 does nothing here
}

TEST(Gaits, TheKeysSayTheirGaitWhateverTheOption) {
    for (int m = 0; m < int(RunMode::Count); ++m) {
        GaitPicker g;
        EXPECT_EQ(g.update(KEY_TILT_WALK, true, RunMode(m), false, false, false), Gait::Walk);
        EXPECT_EQ(g.update(KEY_TILT_RUN, true, RunMode(m), false, false, false), Gait::Run);     // Shift
        EXPECT_EQ(g.update(KEY_TILT_SNEAK, true, RunMode(m), false, false, false), Gait::Sneak); // Ctrl
        EXPECT_EQ(g.update(0.0f, true, RunMode(m), false, false, false), Gait::Still);
    }
}

// ── Stick back + the right face button ────────────────────────────────────────────
namespace {
constexpr float F = 1.0f / 60;
constexpr Vector2 CENTRE{0, 0}, BACK{0, -1}, SIDE{1, 0}, AHEAD{0, 1};
}  // namespace

TEST(BackTurn, StickBackAndTheButtonTurnsHimAtOnce) {
    BackTurnChord c;
    EXPECT_EQ(c.update(F, BACK, false, true), BackTurnChord::NONE);
    EXPECT_EQ(c.update(F, BACK, true, true), BackTurnChord::TURN);
    BackTurnChord d;   // back and the button on the same frame
    EXPECT_EQ(d.update(F, {0.2f, -0.8f}, true, true), BackTurnChord::TURN);
}

TEST(BackTurn, TheButtonAloneStillDodges) {
    BackTurnChord c;
    EXPECT_EQ(c.update(F, SIDE, true, true), BackTurnChord::DODGE);    // pushed another way: at once
    EXPECT_EQ(c.update(F, AHEAD, true, true), BackTurnChord::DODGE);
    BackTurnChord d;   // centred: it waits a moment for the stick, then dodges (a hop back)
    EXPECT_EQ(d.update(F, CENTRE, true, true), BackTurnChord::NONE);
    int waited = 0, out = BackTurnChord::NONE;
    while (out == BackTurnChord::NONE && waited < 30) { out = d.update(F, CENTRE, false, true); ++waited; }
    EXPECT_EQ(out, BackTurnChord::DODGE);
    EXPECT_EQ(waited, 3);   // the grace and no more: 3 frames at 60 Hz
    for (int i = 0; i < 30; ++i) EXPECT_EQ(d.update(F, CENTRE, false, true), BackTurnChord::NONE);   // once
}

TEST(BackTurn, GraceWindowEitherWay) {
    BackTurnChord c;   // the stick back just before, already coming off it at the press
    c.update(F, BACK, false, true);
    for (int i = 0; i < 4; ++i) c.update(F, CENTRE, false, true);
    EXPECT_EQ(c.update(F, CENTRE, true, true), BackTurnChord::TURN);
    BackTurnChord d;   // the button a moment before the stick gets back
    EXPECT_EQ(d.update(F, CENTRE, true, true), BackTurnChord::NONE);
    EXPECT_EQ(d.update(F, {0, -0.2f}, false, true), BackTurnChord::NONE);   // on its way
    EXPECT_EQ(d.update(F, BACK, false, true), BackTurnChord::TURN);
    BackTurnChord e;   // the stick back long before: that was walking back, not the chord
    e.update(F, BACK, false, true);
    for (int i = 0; i < 30; ++i) e.update(F, CENTRE, false, true);
    EXPECT_EQ(e.update(F, SIDE, true, true), BackTurnChord::DODGE);
    BackTurnChord g;   // the button, then the stick another way within the grace: a dodge at once
    EXPECT_EQ(g.update(F, CENTRE, true, true), BackTurnChord::NONE);
    EXPECT_EQ(g.update(F, SIDE, false, true), BackTurnChord::DODGE);
}

TEST(BackTurn, OnlyBehindHimAndOnlyWhenItApplies) {
    EXPECT_TRUE(BackTurnChord::back({0.3f, -0.5f}));
    EXPECT_FALSE(BackTurnChord::back({0.7f, -0.5f}));    // more sideways than back
    EXPECT_FALSE(BackTurnChord::back({0.0f, -0.2f}));    // too slight
    BackTurnChord c;   // not active (aiming, the option off, Type A): nothing, and a waiting press is dropped
    EXPECT_EQ(c.update(F, BACK, true, false), BackTurnChord::NONE);
    EXPECT_EQ(c.update(F, CENTRE, true, true), BackTurnChord::TURN);   // (the stick was back a frame ago)
    BackTurnChord d;
    EXPECT_EQ(d.update(F, CENTRE, true, true), BackTurnChord::NONE);
    EXPECT_EQ(d.update(F, CENTRE, false, false), BackTurnChord::NONE);
    for (int i = 0; i < 10; ++i) EXPECT_EQ(d.update(F, CENTRE, false, true), BackTurnChord::NONE);
}

TEST(BackTurn, BackIsBehindHimWhicheverWayHeFacesTheCamera) {
    const Vector2 cam{0, -1};   // the camera looks along -z
    const auto same = [](Vector2 a, Vector2 b) { return std::fabs(a.x - b.x) < 1e-5f && std::fabs(a.y - b.y) < 1e-5f; };
    // Facing into the picture (the way the camera looks): the stick down is behind him.
    EXPECT_TRUE(same(stick_in_his_frame({0, -1}, cam, {0, -1}), {0, -1}));
    EXPECT_TRUE(same(stick_in_his_frame({1, 0}, cam, {0, -1}), {1, 0}));
    // Facing the camera: the stick down is ahead of him, up is behind him.
    EXPECT_TRUE(same(stick_in_his_frame({0, -1}, cam, {0, 1}), {0, 1}));
    EXPECT_TRUE(same(stick_in_his_frame({0, 1}, cam, {0, 1}), {0, -1}));
    EXPECT_TRUE(same(stick_in_his_frame({1, 0}, cam, {0, 1}), {-1, 0}));   // screen right is his left
    // Facing screen right: the stick left is behind him; lengths are kept (a light pull stays light).
    EXPECT_TRUE(same(stick_in_his_frame({-0.5f, 0}, cam, {1, 0}), {0, -0.5f}));
    EXPECT_TRUE(same(stick_in_his_frame({0.3f, 0.4f}, {0, 0}, {0, 1}), {0.3f, 0.4f}));   // no camera direction: as it is
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

TEST(Settings, TheRunOptionAndTheBackTurnComeBackToo) {
    const std::string path = testing::TempDir() + "dw_settings_run_test.db";
    std::remove(path.c_str());
    EXPECT_EQ(Settings::load(path).run, RunMode::Analog);   // the defaults: by the tilt, back + Circle on
    EXPECT_TRUE(Settings::load(path).back_turn);
    for (int m = 0; m < int(RunMode::Count); ++m) {
        Settings s;
        s.run = RunMode(m);
        s.back_turn = m % 2 == 0;
        EXPECT_TRUE(s.save(path));
        const Settings r = Settings::load(path);
        EXPECT_EQ(r.run, RunMode(m));
        EXPECT_EQ(r.back_turn, m % 2 == 0);
    }
    Settings bad;
    bad.run = RunMode(int(RunMode::Count) + 3);             // a value from some future version: the default
    EXPECT_TRUE(bad.save(path));
    EXPECT_EQ(Settings::load(path).run, RunMode::Analog);
    std::remove(path.c_str());
}
