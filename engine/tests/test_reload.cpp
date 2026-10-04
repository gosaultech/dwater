// damned_waters/engine/tests/test_reload.cpp
// Purpose: GoogleTest suite for the reloads' choreography (reload.hpp): the steps run in order
// from the start of the reload to its end, the hand is where the work is when the work happens (in
// the pocket when it closes on the magazine, the magazine at the grip when it goes home, the hand
// on the fore-end when it racks), one shell's end is the next one's start, and it all fits in the
// time the gun's rules give it (combat.hpp), the pump's travel in step with its sound.
#include <gtest/gtest.h>

#include "dw/combat.hpp"
#include "dw/reload.hpp"

using namespace dw;
using namespace dw::reload;

namespace {
struct Steps {
    Step s[MAX_STEPS];
    int n;
    Steps(Kind k, bool from_grip) { n = steps(k, from_grip, s); }
    // The pair of steps at `t`.
    const Step& from(float t) const { float f; return s[segment(s, n, t, f)]; }
    const Step& to(float t) const { float f; return s[segment(s, n, t, f) + 1]; }
};
const Kind KINDS[] = {Kind::Magazine, Kind::Shell, Kind::ShellRack};
}  // namespace

TEST(Reload, StepsRunInOrderFromStartToEnd) {
    for (Kind k : KINDS)
        for (bool g : {true, false}) {
            const Steps st(k, g);
            ASSERT_GE(st.n, 2);
            ASSERT_LE(st.n, MAX_STEPS);
            EXPECT_FLOAT_EQ(st.s[0].t, 0.0f);
            EXPECT_FLOAT_EQ(st.s[st.n - 1].t, 1.0f);
            for (int i = 1; i < st.n; ++i) EXPECT_GT(st.s[i].t, st.s[i - 1].t);
            EXPECT_TRUE(st.s[0].stop);            // it sets off from rest...
            EXPECT_TRUE(st.s[st.n - 1].stop);     // ... and ends at rest
        }
}

TEST(Reload, SegmentFindsTheStepsEitherSide) {
    const Steps st(Kind::Magazine, true);
    for (int i = 0; i + 1 < st.n; ++i) {
        const float mid = (st.s[i].t + st.s[i + 1].t) / 2;
        float f = -1;
        EXPECT_EQ(segment(st.s, st.n, mid, f), i);
        EXPECT_NEAR(f, 0.5f, 1e-5f);
    }
    float f = -1;
    EXPECT_EQ(segment(st.s, st.n, -0.5f, f), 0);   // before the start: at the first step
    EXPECT_FLOAT_EQ(f, 0.0f);
    EXPECT_EQ(segment(st.s, st.n, 1.5f, f), st.n - 2);   // after the end: at the last
    EXPECT_FLOAT_EQ(f, 1.0f);
}

// The magazine change: off the gun, into the pocket, the fresh magazine up into the grip and home,
// back onto the gun.
TEST(Reload, TheMagazineGoesFromThePocketIntoTheGrip) {
    const Steps st(Kind::Magazine, true);
    EXPECT_EQ(st.s[0].place, Place::Grip);
    EXPECT_EQ(st.s[st.n - 1].place, Place::Grip);
    EXPECT_LT(MAG_DROP, MAG_GRAB);   // the empty one's gone before the hand has the fresh one
    EXPECT_LT(MAG_GRAB, MAG_HOME);
    EXPECT_LT(MAG_HOME, SLIDE_HOME);
    EXPECT_LT(SLIDE_HOME, 1.0f);
    // It closes on the magazine with the hand in the pocket, open to closed.
    EXPECT_EQ(st.from(MAG_GRAB).place, Place::Pocket);
    EXPECT_EQ(st.to(MAG_GRAB).place, Place::Pocket);
    EXPECT_EQ(st.from(MAG_GRAB).hand, Hand::Open);
    EXPECT_EQ(st.to(MAG_GRAB).hand, Hand::Hold);
    // From then until it's home the hand holds it (the last of the way, as the magazine goes into
    // the grip, the fingers open off it and the heel of the hand seats it), and it's home exactly
    // when a step says so.
    for (float t = MAG_GRAB + 0.02f; t < MAG_HOME; t += 0.01f) {
        const Hand h = st.to(t).hand;
        EXPECT_TRUE(h == Hand::Hold || (h == Hand::Slap && st.to(t).place == Place::Load)) << t;
    }
    EXPECT_EQ(st.to(MAG_HOME).hand, Hand::Slap);   // seated with the heel of the hand, the fingers clear of the strong hand
    bool home = false;
    for (int i = 0; i < st.n; ++i)
        if (st.s[i].place == Place::Load && st.s[i].along == 0.0f) {
            home = true;
            EXPECT_FLOAT_EQ(st.s[i].t, MAG_HOME);
            EXPECT_TRUE(st.s[i].stop);   // slapped home: the hand stops there
        }
    EXPECT_TRUE(home);
    // On its way in it only ever goes further in.
    float out = 1e9f;
    for (int i = 0; i < st.n; ++i)
        if (st.s[i].place == Place::Load) { EXPECT_LE(st.s[i].along, out); out = st.s[i].along; }
    // The slide stop is dropped as the hand comes back onto the gun.
    EXPECT_EQ(st.to(SLIDE_HOME).place, Place::Grip);
}

TEST(Reload, AShellGoesFromThePocketIntoTheTube) {
    for (bool g : {true, false}) {
        const Steps st(Kind::Shell, g);
        EXPECT_EQ(st.s[0].place, g ? Place::Grip : Place::Load);
        EXPECT_EQ(st.from(SHELL_GRAB).place, Place::Pocket);
        EXPECT_EQ(st.to(SHELL_GRAB).hand, Hand::Hold);
        // It clicks home as the thumb pushes it the last of the way, and it ends there, pushed in.
        EXPECT_GT(SHELL_HOME, SHELL_LET_GO);
        EXPECT_EQ(st.from(SHELL_HOME).place, Place::Load);
        EXPECT_EQ(st.to(SHELL_HOME).hand, Hand::Push);
        const Step& end = st.s[st.n - 1];
        EXPECT_EQ(end.place, Place::Load);
        EXPECT_FLOAT_EQ(end.along, 1.0f);
        EXPECT_EQ(end.hand, Hand::Push);
        // Along its way in it only goes on, never back.
        float along = -1;
        for (int i = 1; i < st.n; ++i)
            if (st.s[i].place == Place::Load) { EXPECT_GE(st.s[i].along, along); along = st.s[i].along; }
    }
}

// Shell after shell, the hand carries on from where it was: the end of one is the start of the next.
TEST(Reload, OneShellEndsWhereTheNextBegins) {
    const Steps a(Kind::Shell, true), b(Kind::Shell, false);
    const Step &end = a.s[a.n - 1], &start = b.s[0];
    EXPECT_EQ(end.place, start.place);
    EXPECT_FLOAT_EQ(end.along, start.along);
    EXPECT_EQ(end.hand, start.hand);
    // After racking, the hand's on the fore-end: the next shell starts from there.
    const Steps r(Kind::ShellRack, true), next(Kind::Shell, true);
    EXPECT_EQ(r.s[r.n - 1].place, Place::Grip);
    EXPECT_EQ(next.s[0].place, Place::Grip);
}

// An empty 870: the shell first, then the hand on the fore-end racks it, back and home, in step
// with the pump's sound (its clacks at 0.085 s and 0.24 s), all in the time the gun allows.
TEST(Reload, AnEmpty870IsRackedWithTheHandOnTheForeEnd) {
    const Steps st(Kind::ShellRack, true);
    EXPECT_FLOAT_EQ(shell_time(Kind::ShellRack, RACK_SHELL), 1.0f);   // the shell's in before the rack
    EXPECT_FLOAT_EQ(shell_time(Kind::Shell, 0.4f), 0.4f);
    EXPECT_LT(RACK_SHELL, RACK_BACK0);
    for (float t = RACK_BACK0 + 0.005f; t <= 1.0f; t += 0.01f) EXPECT_EQ(st.from(t).place, Place::Grip) << t;
    EXPECT_FLOAT_EQ(pump(Kind::ShellRack, RACK_BACK0 - 0.01f), 0.0f);
    EXPECT_FLOAT_EQ(pump(Kind::ShellRack, (RACK_BACK1 + RACK_HOME0) / 2), 1.0f);
    EXPECT_FLOAT_EQ(pump(Kind::ShellRack, 1.0f), 0.0f);
    for (float t = 0; t <= 1.0f; t += 0.01f) EXPECT_FLOAT_EQ(pump(Kind::Shell, t), 0.0f);   // only racking moves it
    const WeaponSpec& s = weapon_spec(Weapon::Shotgun);
    const float period = s.reload_time + s.rack_time;   // an empty gun's first shell (combat.hpp)
    EXPECT_NEAR((RACK_BACK1 - RACK_BACK0) * period, 0.085f, 0.01f);   // back on the first clack
    EXPECT_NEAR((RACK_HOME1 - RACK_BACK0) * period, 0.24f, 0.01f);    // home on the second
    EXPECT_GT(RACK_SHELL * period, 0.4f);   // the shell's own steps keep most of their time
}

// The hands' work fits the gun's time: the magazine change takes the M92FS's reload time, the
// shell the 870's, and each beat is long enough for a hand to get there (no teleporting): the
// fastest step moves a hand at most from the gun to the pocket in a tenth of a second.
TEST(Reload, EveryStepGivesTheHandTimeToGetThere) {
    const float times[] = {weapon_spec(Weapon::Pistol).reload_time, weapon_spec(Weapon::Shotgun).reload_time,
                           weapon_spec(Weapon::Shotgun).reload_time + weapon_spec(Weapon::Shotgun).rack_time};
    for (int k = 0; k < 3; ++k)
        for (bool g : {true, false}) {
            const Steps st(KINDS[k], g);
            for (int i = 1; i < st.n; ++i) {
                const bool far = st.s[i].place != st.s[i - 1].place;   // from one place to another
                if (far) EXPECT_GE((st.s[i].t - st.s[i - 1].t) * times[k], 0.09f) << int(KINDS[k]) << " step " << i;
            }
        }
}
