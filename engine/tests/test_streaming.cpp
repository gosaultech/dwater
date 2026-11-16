// damned_waters/engine/tests/test_streaming.cpp
// Purpose: GoogleTest suite for which plates are kept on the GPU (dw/streaming.hpp): the shots near
// him are wanted, far ones are let go, the gap between the two radii stops a plate bouncing, and the
// shot on screen is always kept.
#include <gtest/gtest.h>

#include <algorithm>

#include "dw/streaming.hpp"

using namespace dw;
using namespace dw::streaming;

namespace {
bool has(const std::vector<std::string>& v, const std::string& k) { return std::find(v.begin(), v.end(), k) != v.end(); }
const std::vector<Candidate> STREET = {   // a street filmed in 10 m pieces along z
    {"street", "a", {0, 0, 10, 10}}, {"street", "b", {0, 10, 10, 20}}, {"street", "c", {0, 20, 10, 30}},
    {"street", "d", {0, 30, 10, 40}}, {"street", "e", {0, 40, 10, 50}}, {"next", "a", {0, 50, 10, 60}}};
}  // namespace

TEST(Streaming, DistanceToAZoneIsZeroInsideIt) {
    EXPECT_FLOAT_EQ(to_rect({0, 0, 10, 10}, 5, 5), 0.0f);
    EXPECT_FLOAT_EQ(to_rect({0, 0, 10, 10}, 13, 5), 3.0f);
    EXPECT_FLOAT_EQ(to_rect({0, 0, 10, 10}, 13, 14), 5.0f);
}

TEST(Streaming, TheShotsNearHimAreWantedAndTheFarOnesNot) {
    const auto w = within(STREET, 5, 5, WANT, "street/a");
    EXPECT_TRUE(has(w, "street/a"));
    EXPECT_TRUE(has(w, "street/b"));      // 5 m on: he could be in it in two seconds
    EXPECT_FALSE(has(w, "street/c"));     // 15 m on
    EXPECT_FALSE(has(w, "street/e"));     // 35 m on
    EXPECT_FALSE(has(w, "next/a"));
}

TEST(Streaming, TheNextRoomsFirstShotIsReadyBeforeHeReachesTheDoor) {
    const auto w = within(STREET, 5, 45, WANT, "street/e");
    EXPECT_TRUE(has(w, "next/a"));
}

TEST(Streaming, APlateWantedIsKeptAWhileAfterHeLeavesIt) {
    // Wanted at 14 m, kept to 22: walking back and forth over the 14 m line never drops it.
    EXPECT_TRUE(has(within(STREET, 5, 17, WANT), "street/d"));    // 13 m off: wanted
    EXPECT_FALSE(has(within(STREET, 5, 10, WANT), "street/d"));   // 20 m off: not wanted now...
    EXPECT_TRUE(has(within(STREET, 5, 10, KEEP), "street/d"));    // ... but kept
    EXPECT_FALSE(has(within(STREET, 5, 5, KEEP), "street/d"));    // 25 m off: let go
}

TEST(Streaming, TheShotOnScreenIsAlwaysKept) {
    const auto k = within(STREET, 5, 5, KEEP, "elsewhere/z");
    EXPECT_TRUE(has(k, "elsewhere/z"));
    EXPECT_EQ(std::count(k.begin(), k.end(), "elsewhere/z"), 1);
}
