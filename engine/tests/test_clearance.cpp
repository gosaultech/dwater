// damned_waters/engine/tests/test_clearance.cpp
// Purpose: GoogleTest suite for the clearance check (clearance.hpp): a point inside a sphere of
// surface points reads as inside by how far, one outside or far away reads as clear, and the
// worst of a set is the deepest of them.
#include <gtest/gtest.h>

#include <cmath>

#include "dw/clearance.hpp"

using namespace dw::clearance;

namespace {
// A sphere of radius r about the origin, as points with outward normals.
Cloud sphere(float r) {
    Cloud c(0.02f);
    for (int i = 0; i < 40; ++i)
        for (int j = 0; j < 80; ++j) {
            const float th = 3.14159265f * (float(i) + 0.5f) / 40.0f, ph = 6.2831853f * float(j) / 80.0f;
            const V3 n{std::sin(th) * std::cos(ph), std::cos(th), std::sin(th) * std::sin(ph)};
            c.add({n.x * r, n.y * r, n.z * r}, n);
        }
    return c;
}
}  // namespace

TEST(Clearance, InsideReadsHowDeep) {
    const Cloud c = sphere(0.1f);
    EXPECT_NEAR(c.depth({0.08f, 0, 0}, 0.05f), 0.02f, 0.002f);
    EXPECT_NEAR(c.depth({0, -0.07f, 0}, 0.05f), 0.03f, 0.002f);
}

TEST(Clearance, OutsideOrFarIsClear) {
    const Cloud c = sphere(0.1f);
    EXPECT_FLOAT_EQ(c.depth({0.12f, 0, 0}, 0.05f), 0.0f);
    EXPECT_FLOAT_EQ(c.depth({0.5f, 0, 0}, 0.05f), 0.0f);   // nothing within reach
    EXPECT_EQ(c.nearest({0.5f, 0, 0}, 0.05f), -1);
}

TEST(Clearance, WorstIsTheDeepest) {
    const Cloud c = sphere(0.1f);
    const Worst w = worst({{0.12f, 0, 0}, {0.095f, 0, 0}, {0, 0, 0.07f}}, c, 0.05f, 0.004f);
    EXPECT_EQ(w.at, 2);
    EXPECT_NEAR(w.depth, 0.03f, 0.002f);
    EXPECT_EQ(w.count, 2);
}

TEST(Clearance, TorsoSlicesHoldTheShape) {
    Torso t(-0.2f, 0.2f, 0.02f);
    for (int i = 0; i < 1600; ++i) {   // an oval column: 0.17 wide each side, 0.12 front to back, about z = 0.02
        const float a = 6.2831853f * float(i % 40) / 40.0f, y = -0.19f + 0.38f * float(i / 40) / 39.0f;
        t.add({0.17f * std::cos(a), y, 0.02f + 0.12f * std::sin(a)});
    }
    t.finish(1.0f);
    EXPECT_GT(t.depth({0, 0, 0.02f}, 0.0f), 0.1f);                 // the middle: deep in
    EXPECT_NEAR(t.depth({0.17f, 0, 0.02f}, 0.0f), 0.0f, 0.01f);    // on its side: just touching
    EXPECT_LT(t.depth({0, 0, -0.2f}, 0.04f), 0.0f);                 // a ball in front: clear
    EXPECT_GT(t.depth({0, 0, -0.12f}, 0.04f), 0.0f);                // ... until it's within its radius
    EXPECT_LT(t.depth({0, 0.5f, 0}, 0.04f), 0.0f);                  // above it all: clear
}

TEST(Clearance, TorsoIgnoresStrayPoints) {
    Torso t(-0.1f, 0.1f, 0.02f);
    for (int i = 0; i < 400; ++i) {   // a round column of radius 0.15 ...
        const float a = 6.2831853f * float(i % 40) / 40.0f, y = -0.09f + 0.18f * float(i / 40) / 9.0f;
        t.add({0.15f * std::cos(a), y, 0.15f * std::sin(a)});
    }
    for (int i = 0; i < 10; ++i) t.add({0.3f, -0.09f + 0.018f * float(i), 0});   // ... and a few strays far out (a flap)
    t.finish();
    EXPECT_LT(t.depth({0.2f, 0, 0}, 0.0f), 0.0f);   // the strays don't widen it
    EXPECT_GT(t.depth({0.1f, 0, 0}, 0.0f), 0.0f);
}
