// damned_waters/engine/tests/test_framing.cpp
// Purpose: the following view (dw/framing.hpp): the window over a fixed shot's background puts him
// at the size it should, stays on the background, keeps him in it as he walks without jumping or
// twitching, leaves room ahead of him, opens wide on a big space and closes in, holds what he aims
// at, and pushes in about where he stands; and the 3D drawn through its frustum lands exactly where
// the cropped background has it.
#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>

#include "dw/framing.hpp"

using namespace dw::framing;

namespace {
// Him standing at u across the background, his feet at v, `a` tall (shares of the background).
Subject him(float u, float v, float a, float lead = 0) {
    Subject s;
    s.feet = {u, v};
    s.head = {u, v - a};
    s.lead = lead;
    return s;
}
bool inside(const Window& w, Vector2 p, float tol = 1e-4f) {
    const Vector2 q = to_screen(w, p);
    return q.x >= -tol && q.x <= 1 + tol && q.y >= -tol && q.y <= 1 + tol;
}
bool on_background(const Window& w) {
    return w.x0() >= -1e-5f && w.y0() >= -1e-5f && w.x0() + w.h <= 1 + 1e-5f && w.y0() + w.h <= 1 + 1e-5f;
}
}  // namespace

TEST(Framing, TheLensPutsWhatItLooksAtInTheMiddle) {
    const Lens L = Lens::from({0, 2, 10}, {0, 1, 0}, 50, 16.0f / 9.0f);
    const Vector3 c = L.project({0, 1, 0});
    EXPECT_NEAR(c.x, 0.5f, 1e-5f);
    EXPECT_NEAR(c.y, 0.5f, 1e-5f);
    EXPECT_GT(c.z, 0);
    // A point on the top edge of the picture, and one on its right edge.
    const Vector3 top{L.pos.x + (L.f.x + L.u.x * L.tan_v) * 5, L.pos.y + (L.f.y + L.u.y * L.tan_v) * 5, L.pos.z + (L.f.z + L.u.z * L.tan_v) * 5};
    EXPECT_NEAR(L.project(top).y, 0.0f, 1e-4f);
    const float tx = L.tan_v * L.aspect;
    const Vector3 right{L.pos.x + (L.f.x + L.r.x * tx) * 5, L.pos.y + (L.f.y + L.r.y * tx) * 5, L.pos.z + (L.f.z + L.r.z * tx) * 5};
    EXPECT_NEAR(L.project(right).x, 1.0f, 1e-4f);
}

TEST(Framing, TheWindowsFrustumDrawsWhereTheCroppedBackgroundIs) {
    const Lens L = Lens::from({3, 2.6f, 9}, {1, 0.8f, -2}, 46, 16.0f / 9.0f);
    const Window w{0.31f, 0.62f, 0.5f};
    const Frustum f = frustum(L, w);
    for (const Vector3 p : {Vector3{1, 0, -1}, Vector3{2.5f, 1.7f, 0}, Vector3{-1, 0.3f, -4}, Vector3{1.4f, 1.0f, 2}}) {
        // Through the off-axis frustum (as the characters are drawn)...
        const Vector3 d{p.x - L.pos.x, p.y - L.pos.y, p.z - L.pos.z};
        const float D = d.x * L.f.x + d.y * L.f.y + d.z * L.f.z;
        const float X = (d.x * L.r.x + d.y * L.r.y + d.z * L.r.z) / D, Y = (d.x * L.u.x + d.y * L.u.y + d.z * L.u.z) / D;
        const Vector2 drawn{(X - f.l) / (f.r - f.l), (f.t - Y) / (f.t - f.b)};
        // ... and on the background, through the window (as the painting is cropped).
        const Vector3 uv = L.project(p);
        const Vector2 cropped = to_screen(w, {uv.x, uv.y});
        EXPECT_NEAR(drawn.x, cropped.x, 1e-4f);
        EXPECT_NEAR(drawn.y, cropped.y, 1e-4f);
    }
    // The whole picture's window is the camera's own frustum.
    const Frustum all = frustum(L, Window{});
    EXPECT_NEAR(all.l, -all.r, 1e-6f);
    EXPECT_NEAR(all.t, L.tan_v, 1e-6f);
}

TEST(Framing, BaseZoomPutsHimAtTheTargetWhereHeTypicallyStands) {
    EXPECT_NEAR(base_zoom(0.19f), 2.0f, 1e-5f);
    EXPECT_NEAR(base_zoom(TARGET), 1.0f, 1e-5f);
    EXPECT_FLOAT_EQ(base_zoom(0.6f), 1.0f);    // already big: the whole picture
    EXPECT_FLOAT_EQ(base_zoom(0.05f), ZMAX);   // tiny: as far as the background allows
    EXPECT_FLOAT_EQ(base_zoom(0.0f), 1.0f);    // (no floor in the shot)
}

TEST(Framing, ACutPutsHimAtTheTargetSizeLowInThePicture) {
    Operator op;
    const Subject s = him(0.4f, 0.7f, 0.2f);
    op.cut(s, {}, base_zoom(0.2f), false);
    const Window& w = op.shown();
    EXPECT_NEAR(0.2f / w.h, TARGET, 0.01f);
    EXPECT_TRUE(inside(w, s.feet));
    EXPECT_TRUE(inside(w, s.head));
    EXPECT_GT(to_screen(w, s.feet).y, 0.75f);   // his feet low in the picture, what's ahead above him
}

TEST(Framing, ItNeverLetsHimGrowPastTheFrameNorShrinkPastTheLimit) {
    float mark = 0.5f;
    const Window near = aim(him(0.5f, 0.95f, 0.7f), {}, 2.0f, mark);   // walking up to the lens
    EXPECT_LE(0.7f / near.h, FIT + 1e-4f);
    mark = 0.5f;
    const Window far = aim(him(0.5f, 0.45f, 0.08f), {}, 1.0f, mark);   // far off: zoom as far as it may
    EXPECT_NEAR(far.h, 1.0f / ZMAX, 1e-5f);
    mark = 0.5f;
    const Window mid = aim(him(0.5f, 0.6f, 0.15f), {}, 1.0f, mark);   // small: pulled up to MIN
    EXPECT_NEAR(0.15f / mid.h, MIN, 1e-4f);
}

TEST(Framing, TheWindowNeverLeavesTheBackground) {
    unsigned seed = 12345u;
    auto rnd = [&seed] { seed = seed * 1664525u + 1013904223u; return float(seed >> 8) / float(1u << 24); };
    Operator op;
    op.cut(him(0.5f, 0.7f, 0.2f), {}, 1.9f, false);
    for (int i = 0; i < 2000; ++i) {
        const Subject s = him(rnd() * 1.2f - 0.1f, 0.2f + rnd() * 0.9f, 0.05f + rnd() * 0.6f, rnd() * 2 - 1);
        Extra x;
        if (i % 3 == 0) x.add({rnd(), rnd()}, {rnd(), rnd()});
        const Window w = op.update(s, x, 1.0f + (i % 5 == 0 ? rnd() : 0.0f), 1.0f / 60);
        ASSERT_TRUE(on_background(w)) << i;
        ASSERT_GE(w.h, 1.0f / ZPUSH - 1e-5f);
    }
}

TEST(Framing, HeStaysInThePictureWalkingAcrossItAndItNeverJumps) {
    Operator op;
    const float a = 0.2f, v = 0.72f;
    float u = 0.12f;
    op.cut(him(u, v, a, 1), {}, base_zoom(a), false);
    Window prev = op.shown();
    for (int f = 0; f < 60 * 8; ++f) {   // 8 s across the square at a walk (a tenth of the picture a second)
        u = std::min(u + 0.1f / 60, 0.9f);
        const Subject s = him(u, v, a, 1);
        const Window w = op.update(s, {}, 1.0f, 1.0f / 60);
        ASSERT_TRUE(inside(w, s.feet)) << f;
        ASSERT_TRUE(inside(w, s.head)) << f;
        ASSERT_LT(std::fabs(w.cx - prev.cx), 0.006f) << f;   // glides: no jump from one frame to the next
        ASSERT_LT(std::fabs(w.h - prev.h), 0.006f) << f;
        prev = w;
    }
}

TEST(Framing, AStepOrATurnInTheStillMiddleDoesntSwingThePicture) {
    Operator op;
    op.cut(him(0.5f, 0.7f, 0.2f), {}, 1.9f, false);
    for (int i = 0; i < 120; ++i) op.update(him(0.5f, 0.7f, 0.2f), {}, 1.0f, 1.0f / 60);
    const float still = op.shown().cx;
    for (int i = 0; i < 240; ++i) {   // shifting his weight, a little to and fro
        const float u = 0.5f + 0.02f * std::sin(float(i) * 0.2f);
        op.update(him(u, 0.7f, 0.2f), {}, 1.0f, 1.0f / 60);
        EXPECT_NEAR(op.shown().cx, still, 1e-3f) << i;
    }
}

TEST(Framing, ThereIsRoomAheadOfHim) {
    Operator op;
    const Subject right = him(0.5f, 0.7f, 0.2f, 1), left = him(0.5f, 0.7f, 0.2f, -1);
    op.cut(right, {}, 1.9f, false);
    for (int i = 0; i < 180; ++i) op.update(right, {}, 1.0f, 1.0f / 60);
    EXPECT_LT(to_screen(op.shown(), right.feet).x, 0.45f);   // facing right: the space is on the right
    for (int i = 0; i < 180; ++i) op.update(left, {}, 1.0f, 1.0f / 60);
    EXPECT_GT(to_screen(op.shown(), left.feet).x, 0.55f);
}

TEST(Framing, ABigSpaceOpensWideThenClosesInOnHim) {
    Operator op;
    const Subject s = him(0.3f, 0.75f, 0.19f);
    op.cut(s, {}, base_zoom(0.19f), true);
    EXPECT_FLOAT_EQ(op.shown().h, 1.0f);
    for (float t = 0; t < HOLD - 0.05f; t += 1.0f / 60) op.update(s, {}, 1.0f, 1.0f / 60);
    EXPECT_FLOAT_EQ(op.shown().h, 1.0f);   // held
    EXPECT_TRUE(op.establishing());
    for (float t = 0; t < 3.0f; t += 1.0f / 60) op.update(s, {}, 1.0f, 1.0f / 60);
    EXPECT_NEAR(op.shown().h, 0.5f, 0.02f);   // in on him
    EXPECT_FALSE(op.establishing());
}

TEST(Framing, ItHoldsWhatHeAimsAtWithHim) {
    Operator op;
    const Subject s = him(0.3f, 0.75f, 0.19f, 1);
    Extra target;
    target.add({0.74f, 0.5f}, {0.8f, 0.7f});   // a Drowned across the square
    op.cut(s, target, 2.0f, false);
    for (int i = 0; i < 240; ++i) op.update(s, target, 1.0f, 1.0f / 60);
    const Window& w = op.shown();
    EXPECT_TRUE(inside(w, s.feet) && inside(w, s.head));
    EXPECT_TRUE(inside(w, target.lo) && inside(w, target.hi));
}

TEST(Framing, APushInClosesInAboutWhereHeStands) {
    Operator op;
    const Subject s = him(0.45f, 0.7f, 0.2f);
    op.cut(s, {}, 1.5f, false);
    for (int i = 0; i < 120; ++i) op.update(s, {}, 1.0f, 1.0f / 60);
    const Window before = op.shown();
    const Vector2 mid{0.45f, 0.6f};
    const Window pushed = op.update(s, {}, 1.3f, 1.0f / 60);
    EXPECT_NEAR(pushed.h, before.h / 1.3f, 2e-3f);
    EXPECT_NEAR(to_screen(pushed, mid).x, to_screen(before, mid).x, 3e-3f);   // he stays put on the screen
    EXPECT_NEAR(to_screen(pushed, mid).y, to_screen(before, mid).y, 3e-3f);
    EXPECT_GE(op.update(s, {}, 9.0f, 1.0f / 60).h, 1.0f / ZPUSH - 1e-5f);   // never past the push limit
}

TEST(Framing, BehindSomethingForAWhileItOpensToTheWholePicture) {
    Operator op;
    Subject s = him(0.4f, 0.7f, 0.19f);
    op.cut(s, {}, 2.0f, false);
    const float tight = op.shown().h;
    s.hidden = true;   // walking past a lamp post: a blink, nothing changes
    for (int i = 0; i < 12; ++i) op.update(s, {}, 1.0f, 1.0f / 60);
    s.hidden = false;
    for (int i = 0; i < 60; ++i) op.update(s, {}, 1.0f, 1.0f / 60);
    EXPECT_NEAR(op.shown().h, tight, 1e-3f);
    s.hidden = true;   // behind the tent: the whole picture
    for (int i = 0; i < 60 * 4; ++i) op.update(s, {}, 1.0f, 1.0f / 60);
    EXPECT_NEAR(op.shown().h, 1.0f, 0.01f);
    s.hidden = false;  // out again: back in on him
    for (int i = 0; i < 60 * 4; ++i) op.update(s, {}, 1.0f, 1.0f / 60);
    EXPECT_NEAR(op.shown().h, tight, 0.01f);
    // Cut to a shot where he's hidden: the whole picture at once.
    s.hidden = true;
    op.cut(s, {}, 2.0f, false);
    EXPECT_FLOAT_EQ(op.shown().h, 1.0f);
}
