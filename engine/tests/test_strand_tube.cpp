// damned_waters/engine/tests/test_strand_tube.cpp
// Purpose: a loc's shape (dw/strand_tube.hpp): a smooth curve through the simulated points, rings
// square to it that never twist, a rope that swells and thins but stays within its bounds, slimmer
// at the scalp, rounded off at its end.
#include <gtest/gtest.h>

#include <cmath>
#include <vector>

#include "dw/strand_tube.hpp"

using namespace dw;

namespace {
// A strand hanging in a quarter circle: out from the scalp, then down.
std::vector<Vector3> arc(int n, float seg) {
    std::vector<Vector3> p;
    const float radius = seg * float(n - 1) / (PI / 2);
    for (int i = 0; i < n; ++i) {
        const float a = PI / 2 * float(i) / float(n - 1);
        p.push_back({radius * std::sin(a), radius * std::cos(a), 0});
    }
    return p;
}
strand::Shape shape(int n, int sub) {
    strand::Shape s;
    s.n = n;
    s.sub = sub;
    s.seg = 0.015f;
    s.radius = 0.006f;
    return s;
}
}  // namespace

TEST(StrandTube, TheCurvePassesThroughEverySimulatedPoint) {
    const auto p = arc(8, 0.015f);
    const strand::Shape s = shape(8, 3);
    std::vector<strand::Ring> r(size_t(strand::rings(s.n, s.sub)));
    strand::build(p.data(), s, {0, 0, 1}, r.data());
    EXPECT_EQ(int(r.size()), 7 * 3 + 1 + strand::CAP);
    for (int i = 0; i < s.n; ++i) EXPECT_LT(Vector3Distance(r[size_t(i * s.sub)].c, p[size_t(i)]), 1e-5f);
}

TEST(StrandTube, SubdividingRoundsTheBends) {
    // The sharpest turn between neighbouring rings: a third gentler (or better) with two rings a segment.
    auto sharpest = [](int sub) {
        const auto p = arc(6, 0.03f);
        const strand::Shape s = shape(6, sub);
        std::vector<strand::Ring> r(size_t(strand::rings(s.n, s.sub)));
        strand::build(p.data(), s, {0, 0, 1}, r.data());
        float worst = 0;
        const int curve = int(r.size()) - strand::CAP;
        for (int m = 1; m + 1 < curve; ++m) {
            const Vector3 a = Vector3Normalize(Vector3Subtract(r[size_t(m)].c, r[size_t(m) - 1].c));
            const Vector3 b = Vector3Normalize(Vector3Subtract(r[size_t(m) + 1].c, r[size_t(m)].c));
            worst = std::max(worst, std::acos(std::min(1.0f, Vector3DotProduct(a, b))));
        }
        return worst;
    };
    EXPECT_LT(sharpest(2), sharpest(1) * 0.7f);
}

TEST(StrandTube, RingsAreSquareToTheStrandAndNeverTwist) {
    const auto p = arc(10, 0.02f);
    const strand::Shape s = shape(10, 2);
    std::vector<strand::Ring> r(size_t(strand::rings(s.n, s.sub)));
    strand::build(p.data(), s, {0.3f, 0.2f, 1}, r.data());
    for (size_t m = 0; m < r.size(); ++m) {
        EXPECT_NEAR(Vector3Length(r[m].x), 1, 1e-4f);
        EXPECT_NEAR(Vector3Length(r[m].y), 1, 1e-4f);
        EXPECT_NEAR(Vector3DotProduct(r[m].x, r[m].y), 0, 1e-4f);
        if (m > 0) EXPECT_GT(Vector3DotProduct(r[m].x, r[m - 1].x), 0.9f);   // carried down, not spun
    }
}

TEST(StrandTube, TheRopeSwellsWithinBoundsThinsAtTheScalpAndRoundsOffAtTheTip) {
    strand::Shape s = shape(12, 2);
    s.lump = 0.13f;
    s.taper = 0.25f;
    s.root = 0.75f;
    const auto p = arc(12, s.seg);
    std::vector<strand::Ring> r(size_t(strand::rings(s.n, s.sub)));
    const Vector3 tip = strand::build(p.data(), s, {0, 0, 1}, r.data());
    const int curve = int(r.size()) - strand::CAP;
    for (int m = 0; m < curve; ++m) {
        EXPECT_LE(r[size_t(m)].r, s.radius * (1 + s.lump) + 1e-6f);
        EXPECT_GE(r[size_t(m)].r, s.radius * (1 - s.taper) * (1 - s.lump) * s.root - 1e-6f);
    }
    EXPECT_LT(r[0].r, s.radius * (1 + s.lump) * s.root + 1e-6f);   // new growth: slimmer
    // The cap: each ring narrower than the last, each further out, the tip beyond them all.
    const strand::Ring& end = r[size_t(curve) - 1];
    float reach = 0, width = end.r;
    for (int k = 0; k < strand::CAP; ++k) {
        const strand::Ring& c = r[size_t(curve + k)];
        EXPECT_LT(c.r, width);
        EXPECT_GT(Vector3Distance(c.c, end.c), reach);
        width = c.r;
        reach = Vector3Distance(c.c, end.c);
    }
    EXPECT_GT(Vector3Distance(tip, end.c), reach);
    EXPECT_NEAR(Vector3Distance(tip, end.c), end.r, 1e-5f);   // a dome: as long as it is wide
}

TEST(StrandTube, TheWanderLeavesTheRootWhereItGrows) {
    strand::Shape s = shape(10, 2);
    const auto p = arc(10, s.seg);
    std::vector<strand::Ring> straight(size_t(strand::rings(s.n, s.sub))), wavy(straight.size());
    strand::build(p.data(), s, {0, 0, 1}, straight.data());
    s.wave = 0.0015f;
    strand::build(p.data(), s, {0, 0, 1}, wavy.data());
    EXPECT_LT(Vector3Distance(straight[0].c, wavy[0].c), 1e-6f);
    float most = 0;
    for (size_t m = 0; m < wavy.size(); ++m) most = std::max(most, Vector3Distance(straight[m].c, wavy[m].c));
    EXPECT_GT(most, 0.0005f);
    EXPECT_LE(most, s.wave * 1.42f);   // (both axes at once: at most sqrt 2 of it)
}
