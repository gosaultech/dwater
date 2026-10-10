// damned_waters/engine/tests/test_doors.cpp
// Purpose: GoogleTest suite for the door leaf (doors.hpp) and the beat between storeys
// (transition.hpp): a push swings it away from the pusher and it creaks; leaning eases it to a
// crack and no further; shut, it slams; locked, it won't budge; its collider follows the swing;
// the beat goes dark, swaps the floor in the dark, and comes back up.
#include <gtest/gtest.h>

#include <cmath>

#include "dw/doors.hpp"
#include "dw/transition.hpp"

using namespace dw;
using namespace dw::doors;

namespace {
// A doorway in a wall along x at z = 0, from x = 0 to 0.9; normal +z (room a is the -z side).
Leaf door() { return hang(0.0f, 0.0f, 0.9f, 0.0f, 0.0f, 1.0f, true); }
Event run(Leaf& l, float seconds, Event want = Event::None) {
    Event got = Event::None;
    for (float t = 0; t < seconds; t += 1.0f / 60) {
        const Event e = l.update(1.0f / 60);
        if (e != Event::None && (want == Event::None || e == want)) got = e;
    }
    return got;
}
}  // namespace

TEST(Doors, HangsOnItsHinge) {
    const Leaf l = door();
    EXPECT_FLOAT_EQ(l.width, 0.9f);
    EXPECT_NEAR(l.latch().x, 0.9f, 1e-5f);
    EXPECT_TRUE(l.shut());
    EXPECT_EQ(l.side_of(0.45f, -1.0f), 1);    // room a's side
    EXPECT_EQ(l.side_of(0.45f, 1.0f), -1);
}

TEST(Doors, APushSwingsItAwayAndItCreaks) {
    Leaf l = door();
    l.push(1);                                  // from room a: it swings into room b (+z)
    EXPECT_EQ(l.update(1.0f / 60), Event::Creak);
    EXPECT_EQ(run(l, 0.7f, Event::Opened), Event::Opened);
    EXPECT_NEAR(l.angle, OPEN, 1e-3f);
    EXPECT_TRUE(l.passable());
    EXPECT_GT(l.latch().z, 0.8f);               // the latch end is well into room b
    Leaf m = door();
    m.push(-1);                                 // from room b: it swings into room a
    run(m, 0.7f);
    EXPECT_LT(m.latch().z, -0.8f);
}

TEST(Doors, LeaningEasesItToACrackAndNoFurther) {
    Leaf l = door();
    for (int f = 0; f < 60; ++f) { l.ease(1, 1.0f / 60); l.update(1.0f / 60); }   // a second of leaning: a crack
    EXPECT_GT(l.angle, 0.4f);
    for (int f = 0; f < 180; ++f) { l.ease(1, 1.0f / 60); l.update(1.0f / 60); }   // three more: no further
    EXPECT_NEAR(l.angle, AJAR, 0.02f);
    EXPECT_TRUE(l.ajar());
    EXPECT_FALSE(l.passable());
    const float held = l.angle;
    run(l, 1.0f);                               // stops leaning: it stays where it is
    EXPECT_NEAR(l.angle, held, 1e-3f);
}

TEST(Doors, ALeanLetGoHalfwayStaysThere) {
    Leaf l = door();
    for (int f = 0; f < 18; ++f) { l.ease(1, 1.0f / 60); l.update(1.0f / 60); }   // 0.3 s
    const float at = l.angle;
    EXPECT_GT(at, 0.1f);
    EXPECT_LT(at, AJAR - 0.1f);
    run(l, 1.0f);
    EXPECT_NEAR(l.angle, at, 0.01f);
}

TEST(Doors, ShutItSlams) {
    Leaf l = door();
    l.push(1);
    run(l, 0.8f);
    l.shut_it();
    EXPECT_EQ(run(l, 0.6f, Event::Slam), Event::Slam);
    EXPECT_TRUE(l.shut());
}

TEST(Doors, LockedWontBudge) {
    Leaf l = door();
    l.locked = true;
    l.push(1);
    l.ease(1, 0.5f);
    run(l, 1.0f);
    EXPECT_TRUE(l.shut());
}

TEST(Doors, ColliderFollowsTheSwing) {
    Leaf l = door();
    Obb2 c = l.collider();
    EXPECT_NEAR(c.cx, 0.45f, 1e-5f);
    EXPECT_NEAR(c.cz, 0.0f, 1e-5f);
    float x = 0.45f, z = 0.01f;                 // standing in the shut doorway: pushed out
    EXPECT_TRUE(resolve_circle_obb(x, z, 0.2f, c));
    l.push(1);
    run(l, 0.8f);
    c = l.collider();                           // open: the leaf lies along +z from the hinge
    EXPECT_NEAR(c.cx, 0.0f + 0.45f * std::cos(OPEN), 0.02f);
    EXPECT_NEAR(c.cz, 0.45f * std::sin(OPEN), 0.02f);
    x = 0.5f; z = 0.0f;                         // the doorway is clear
    EXPECT_FALSE(resolve_circle_obb(x, z, 0.2f, c));
}

TEST(Beat, DarkSwapBack) {
    Beat b;
    EXPECT_FALSE(b.busy());
    b.start();
    EXPECT_TRUE(b.busy());
    EXPECT_FLOAT_EQ(b.black(), 0.0f);
    Beat::Event swap = Beat::Event::None, done = Beat::Event::None;
    float swapped_at = -1, t = 0;
    for (; t < 3.0f && b.busy(); t += 1.0f / 60) {
        const Beat::Event e = b.update(1.0f / 60);
        if (e == Beat::Event::Swap) { swap = e; swapped_at = t; EXPECT_FLOAT_EQ(b.black(), 1.0f); }
        if (e == Beat::Event::Done) done = e;
    }
    EXPECT_EQ(swap, Beat::Event::Swap);
    EXPECT_EQ(done, Beat::Event::Done);
    EXPECT_NEAR(swapped_at, Beat::OUT, 0.03f);
    EXPECT_NEAR(t, Beat::OUT + Beat::HOLD + Beat::IN, 0.05f);
    EXPECT_FLOAT_EQ(b.black(), 0.0f);
}
