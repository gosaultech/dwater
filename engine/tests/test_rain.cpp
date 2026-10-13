// damned_waters/engine/tests/test_rain.cpp
// Purpose: the rain stays round him, falls, and comes down again from the top.
#include <gtest/gtest.h>
#include <algorithm>
#include <cmath>

#include "dw/rain.hpp"

using namespace dw;

TEST(Rain, StaysInTheBoxRoundHimAsHeWalks) {
    Rain r;
    r.reset(0, 0);
    float cx = 0, cz = 0;
    for (int f = 0; f < 600; ++f) {
        cx += 0.05f;   // 3 m/s east
        cz -= 0.02f;
        r.update(1.0f / 60, cx, cz);
    }
    for (const auto& d : r.drops()) {
        EXPECT_LE(std::abs(d.x - cx), Rain::HALF + 1e-3f);
        EXPECT_LE(std::abs(d.z - cz), Rain::HALF + 1e-3f);
        EXPECT_GE(d.y, 0.0f);
        EXPECT_LE(d.y, Rain::TOP);
    }
}

TEST(Rain, FallsAndComesBackFromTheTop) {
    Rain r;
    r.reset(0, 0);
    const V3 before = r.drops()[0];
    r.update(0.01f, 0, 0);
    const V3 after = r.drops()[0];
    if (before.y > Rain::FALL * 0.01f) EXPECT_NEAR(after.y, before.y - Rain::FALL * 0.01f, 1e-4f);
    float lowest = Rain::TOP;
    for (int f = 0; f < 120; ++f) r.update(1.0f / 60, 0, 0);   // two seconds: every drop has landed at least once
    for (const auto& d : r.drops()) lowest = std::min(lowest, d.y);
    EXPECT_GE(lowest, 0.0f);
    EXPECT_EQ(int(r.drops().size()), Rain::N);
}

TEST(Rain, SameSeedSameRain) {
    Rain a, b;
    a.reset(3, 4, 11);
    b.reset(3, 4, 11);
    for (int f = 0; f < 30; ++f) { a.update(0.016f, 3, 4); b.update(0.016f, 3, 4); }
    for (int i = 0; i < Rain::N; ++i) EXPECT_FLOAT_EQ(a.drops()[i].y, b.drops()[i].y);
}
