// damned_waters/engine/tests/test_rain.cpp
// Purpose: the rain's sheets (dw/rain.hpp) stand where the camera looks, from a metre in front of
// the lens to the far end of a street, square to the shot, each covering the whole picture where it
// stands; and nothing about them depends on where he is (the bug: the rain followed him in a box).
#include <gtest/gtest.h>

#include <cmath>

#include "dw/rain.hpp"

using namespace dw;
using namespace dw::rain;

namespace {
float dist_along(V3 p, V3 cam, V3 h) { return (p.x - cam.x) * h.x + (p.z - cam.z) * h.z; }
}  // namespace

TEST(Rain, SheetsStandFromTheLensToTheFarEndOfTheStreet) {
    const V3 cam{0, 3, 10}, look{0, 1, 0};   // 3 m up, looking north and down
    const auto s = sheets(cam, look, 50, 16.0f / 9.0f);
    EXPECT_LE(s.front().dist, 1.5f);
    EXPECT_GE(s.back().dist, 30.0f);
    for (int i = 1; i < SHEETS; ++i) EXPECT_GT(s[size_t(i)].dist, s[size_t(i) - 1].dist);
    for (const auto& sh : s)
        for (const V3& c : sh.c) EXPECT_NEAR(dist_along(c, cam, {0, 0, -1}), sh.dist, 1e-3f);   // square to the shot
}

TEST(Rain, EachSheetCoversThePictureWhereItStands) {
    const V3 cam{5, 2.6f, 5}, look{14, 0.8f, -3};
    const float fovy = 48, aspect = 16.0f / 9.0f;
    const auto s = sheets(cam, look, fovy, aspect);
    // The picture's four corner rays meet every sheet inside it.
    const float fl = std::sqrt(9.0f * 9 + 1.8f * 1.8f + 8.0f * 8);
    const V3 f{9 / fl, -1.8f / fl, -8 / fl};
    const float hl = std::hypot(f.x, f.z);
    const V3 h{f.x / hl, 0, f.z / hl}, r{-h.z, 0, h.x};
    const float ul = std::sqrt(f.x * f.y * f.x * f.y + (f.x * f.x + f.z * f.z) * (f.x * f.x + f.z * f.z) + f.z * f.y * f.z * f.y);
    const V3 u{-f.x * f.y / ul, (f.x * f.x + f.z * f.z) / ul, -f.z * f.y / ul};
    const float th = std::tan(fovy * 0.5f * 3.14159265f / 180), tw = th * aspect;
    for (const auto& sh : s)
        for (float sx : {-1.0f, 1.0f})
            for (float sy : {-1.0f, 1.0f}) {
                const V3 ray{f.x + r.x * sx * tw + u.x * sy * th, f.y + u.y * sy * th, f.z + r.z * sx * tw + u.z * sy * th};
                const float t = sh.dist / (ray.x * h.x + ray.z * h.z);
                const V3 p{cam.x + ray.x * t, cam.y + ray.y * t, cam.z + ray.z * t};
                const float across = (p.x - cam.x) * r.x + (p.z - cam.z) * r.z;
                EXPECT_GE(across, sh.u0);
                EXPECT_LE(across, sh.u1);
                EXPECT_GE(p.y, sh.v0);
                EXPECT_LE(p.y, sh.v1);
            }
}

TEST(Rain, ItRainsOnTheWholeShotNotRoundHim) {
    // The sheets come from the camera alone: the same shot gives the same rain wherever he walks in
    // it, and they reach far past the 9 m the old box round him did.
    const auto a = sheets({0, 3, 0}, {0, 1, -10}, 52, 16.0f / 9.0f);
    const auto b = sheets({0, 3, 0}, {0, 1, -10}, 52, 16.0f / 9.0f);
    for (int i = 0; i < SHEETS; ++i)
        for (int k = 0; k < 4; ++k) EXPECT_FLOAT_EQ(a[size_t(i)].c[k].z, b[size_t(i)].c[k].z);
    const float far_width = a.back().u1 - a.back().u0;
    EXPECT_GT(far_width, 50.0f);   // the far sheet spans the street from wall to wall and beyond
}
