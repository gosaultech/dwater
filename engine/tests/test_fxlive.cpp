// damned_waters/engine/tests/test_fxlive.cpp
// Purpose: the live effects over the painted streets (dw/fxlive.hpp): a fire breathes round its
// average and never jumps; a beacon flashes twice a turn and is dark between; a failing tube is
// mostly on but does go out; sparks burst, fall, never go through the road, and burn out.
#include <gtest/gtest.h>

#include <cmath>

#include "dw/fxlive.hpp"

using namespace dw::fxlive;

TEST(FxLive, AFireBreathesRoundItsAverageWithoutJumping) {
    float lo = 9, hi = -9, sum = 0, prev = fire(0, 3), worst = 0;
    const int n = 60 * 20;
    for (int i = 1; i <= n; ++i) {
        const float f = fire(float(i) / 60, 3);
        lo = std::min(lo, f), hi = std::max(hi, f), sum += f;
        worst = std::max(worst, std::fabs(f - prev));
        prev = f;
    }
    EXPECT_GE(lo, 0.7f);
    EXPECT_LE(hi, 1.3f);
    EXPECT_GT(hi - lo, 0.15f);              // it does move
    EXPECT_NEAR(sum / n, 1.0f, 0.06f);      // round the light the painting was rendered with
    EXPECT_LT(worst, 0.12f);                // a flicker, not a strobe
    EXPECT_NE(fire(5.0f, 1), fire(5.0f, 2));   // two fires keep their own time
}

TEST(FxLive, ABeaconFlashesTwiceATurnAndIsDarkBetween) {
    int flashes = 0;
    bool on = false;
    float dark_time = 0;
    for (int i = 0; i < 1000; ++i) {   // one turn at 1 Hz, sampled finely
        const float s = strobe(float(i) / 1000, 1.0f, 0);
        if (s > 0.5f && !on) ++flashes;
        on = s > 0.5f;
        dark_time += s < 0.05f ? 0.001f : 0.0f;
    }
    EXPECT_EQ(flashes, 2);
    EXPECT_GT(dark_time, 0.6f);
    EXPECT_LE(strobe(0.08f, 1.0f, 0), 1.0f);
}

TEST(FxLive, AFailingTubeIsMostlyOnButGoesOut) {
    int out = 0, on = 0;
    for (int i = 0; i < 60 * 60; ++i) {
        const float f = flicker(float(i) / 60, 7);
        ASSERT_GE(f, 0.0f);
        ASSERT_LE(f, 1.0f);
        out += f < 0.3f, on += f > 0.8f;
    }
    EXPECT_GT(on, 60 * 60 * 6 / 10);
    EXPECT_GT(out, 30);
}

TEST(FxLive, SparksBurstFallNeverThroughTheRoadAndBurnOut) {
    Sparks s;
    const Vector3 at{3, 0.05f, -2};
    int most = 0;
    float flash = 0;
    for (int i = 0; i < 60 * 8; ++i) {
        s.update(1.0f / 60, float(i) / 60, at, 2.0f, 4);
        most = std::max(most, s.alive());
        flash = std::max(flash, s.flash());
        for (const auto& k : s.all())
            if (k.life > 0) {
                ASSERT_GE(k.p.y, at.y - 1e-4f);
                ASSERT_LT(std::hypot(k.p.x - at.x, k.p.z - at.z), 4.0f);   // a spark doesn't fly off down the street
            }
    }
    EXPECT_GT(most, 15);
    EXPECT_GT(flash, 0.9f);
    EXPECT_LE(most, Sparks::MAX);
    Sparks quiet;   // and a burst dies away: once one has gone up, hold the clock (no more come)
    float t = 0;
    while (quiet.alive() == 0 && t < 10) quiet.update(1.0f / 60, t += 1.0f / 60, at, 2.0f, 4);
    ASSERT_GT(quiet.alive(), 0);
    for (int i = 0; i < 60 * 2; ++i) quiet.update(1.0f / 60, t, at, 2.0f, 4);
    EXPECT_EQ(quiet.alive(), 0);
}
