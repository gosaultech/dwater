// damned_waters/engine/tests/test_mocap.cpp
// Purpose: GoogleTest suite for the motion-captured gait (dw/mocap.hpp): every loop runs into itself
// without a jump, starts with the left foot down and the legs a half-step apart, the pace picks the
// loops either side of his speed and stretches the stride past them, and standing still fades into
// the idle loop.
#include <gtest/gtest.h>

#include <cmath>

#include "dw/mocap.hpp"

using namespace dw::mocap;

namespace {
float worst_gap(const Frame& a, const Frame& b) {
    float w = 0;
    for (int k = 0; k < NJ; ++k)
        w = std::max({w, std::fabs(a.ang[k].x - b.ang[k].x), std::fabs(a.ang[k].y - b.ang[k].y), std::fabs(a.ang[k].z - b.ang[k].z)});
    return w;
}
const Clip* const ALL[] = {&SNEAK, &WALK, &RUN, &IDLE};
}  // namespace

TEST(Mocap, EveryLoopRunsIntoItselfWithoutAJump) {
    for (const Clip* c : ALL) {
        const float step = 1.0f / float(c->rows);
        float worst_step = 0;
        for (int i = 0; i < c->rows; ++i) worst_step = std::max(worst_step, worst_gap(sample(*c, i * step), sample(*c, (i + 1) * step)));
        // The seam (last row into the first) is no bigger a step than the loop's biggest between rows.
        EXPECT_LE(worst_gap(sample(*c, 1.0f - step), sample(*c, 0.0f)), worst_step * 1.05f + 1e-4f) << c->name;
        EXPECT_LT(worst_step, 0.35f) << c->name;   // (no row is a jump: about 20 degrees at most)
    }
}

TEST(Mocap, ALoopStartsWithTheLeftFootDownAndTheLegsAHalfStepApart) {
    for (const Clip* c : {&SNEAK, &WALK, &RUN}) {
        // The left knee nearly straight on the ground at the start; well bent swinging through.
        float bent = 0;
        for (int i = 0; i < 16; ++i) bent = std::max(bent, std::fabs(sample(*c, i / 16.0f).ang[KNE_L].x));
        EXPECT_LT(std::fabs(sample(*c, 0).ang[KNE_L].x), 0.6f * bent) << c->name;
        // The right leg does what the left did half a loop before.
        float diff = 0;
        for (int i = 0; i < 16; ++i) {
            const float t = i / 16.0f;
            diff += std::fabs(sample(*c, t).ang[HIP_L].x - sample(*c, t + 0.5f).ang[HIP_R].x) / 16;
        }
        EXPECT_LT(diff, 0.12f) << c->name;
    }
}

TEST(Mocap, ThePaceIsTheLoopsEitherSideOfHisSpeed) {
    const float sneak = 0.8f, walk = 1.9f, run = 3.8f;
    Pace p = pace(walk, 1.0f, sneak, walk, run);
    EXPECT_EQ(p.b, &WALK);
    EXPECT_NEAR(p.w, 1.0f, 1e-6f);
    p = pace(1.3f, 1.0f, sneak, walk, run);
    EXPECT_EQ(p.a, &SNEAK);
    EXPECT_EQ(p.b, &WALK);
    EXPECT_GT(p.w, 0.0f);
    EXPECT_LT(p.w, 1.0f);
    p = pace(run, 1.0f, sneak, walk, run);
    EXPECT_EQ(p.b, &RUN);
    EXPECT_GT(p.stretch, 1.0f);   // faster than the captured run: a longer stride, a quicker step
    EXPECT_LT(p.stretch, 1.4f);
    EXPECT_GT(pace(run, 1.0f, sneak, walk, run).stride, pace(walk, 1.0f, sneak, walk, run).stride);
    EXPECT_NEAR(pace(walk, 0.5f, sneak, walk, run).stride, 0.5f * pace(walk, 1.0f, sneak, walk, run).stride, 0.5f);   // (a smaller man, a shorter stride)
}

TEST(Mocap, StandingStillIsTheIdleLoop) {
    const Pace p = pace(0, 1.0f, 0.8f, 1.9f, 3.8f);
    const Frame f = at(p, 0.37f, 1.0f, 0.2f), idle = sample(IDLE, 0.2f);
    EXPECT_LT(worst_gap(f, idle), 1e-5f);
    EXPECT_GT(IDLE.time, 3.0f);   // (long enough that its sway doesn't read as a loop)
}
