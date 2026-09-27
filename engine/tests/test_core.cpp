// damned_waters/engine/tests/test_core.cpp
// Purpose: GoogleTest suite for the pure core and data (no window needed).
#include <gtest/gtest.h>
#include <cmath>

#include "dw/core.hpp"
#include "dw/mesh_builder.hpp"
#include "dw/room_spec.hpp"

using namespace dw;

TEST(DepthCodec, MatchesPythonAndGodotVectors) {   // same table as tools/pipeline/tests
    const struct { float m; int hi, lo; } v[] = {{0.0f, 0, 0}, {5.0f, 40, 0}, {32.0f, 255, 255}, {1.2345f, 9, 224}};
    for (auto& x : v) { int hi, lo; depth::encode(x.m, hi, lo); EXPECT_EQ(hi, x.hi); EXPECT_EQ(lo, x.lo); }
    int hi, lo;
    depth::encode(7.77f, hi, lo);
    EXPECT_NEAR(depth::decode(hi, lo), 7.77f, 0.0005f);
}

TEST(ShotSelector, HysteresisAndPriority) {
    std::vector<ShotZone> z = {{"a", {0, 0, 2, 5.7f}, 0}, {"b", {0, 5.3f, 2, 10}, 0}, {"close", {0, 0, 2, 1}, 5}};
    EXPECT_EQ(select_shot(z, "", 1, 8), "b");
    EXPECT_EQ(select_shot(z, "a", 1, 5.5f), "a");
    EXPECT_EQ(select_shot(z, "b", 1, 5.5f), "b");
    EXPECT_EQ(select_shot(z, "b", 1, 0.5f), "close");
    EXPECT_EQ(select_shot(z, "a", 50, 50), "a");
}

TEST(Collision, CirclePushedOutOfYawedBox) {
    Obb2 b{0, 0, 1, 0.5f, 0.6f};
    float x = 0.2f, z = 0.1f;
    ASSERT_TRUE(resolve_circle_obb(x, z, 0.3f, b));
    EXPECT_FALSE(resolve_circle_obb(x, z, 0.29f, b));
}

TEST(Movement, ForwardIsMinusZAtZeroYaw) {
    V2 f = forward_from_yaw(0);
    EXPECT_NEAR(f.x, 0, 1e-6);
    EXPECT_NEAR(f.z, -1, 1e-6);
    EXPECT_NEAR(step_yaw(3.0f, -3.0f, 0.1f), 3.1f, 1e-5);   // shortest way round
}

TEST(EnemyBrain, WindupIsReadableAndStrikesOnce) {
    EnemyBrain b;
    b.state = EState::Pursuit;
    EXPECT_EQ(b.update(1.0f / 60, true, false, 1.0f), EEvent::Windup);
    EXPECT_GE(b.windup, 0.5f);
    int strikes = 0;
    float t = 0;
    while (t < b.windup + b.strike_window + 0.1f) {
        if (b.update(1.0f / 60, true, false, 1.0f) == EEvent::Strike) { strikes++; EXPECT_GE(t, b.windup - 0.05f); }
        t += 1.0f / 60;
    }
    EXPECT_EQ(strikes, 1);
    EXPECT_EQ(b.state, EState::Recovery);
}

TEST(RoomSpec, GangLoadsAndSpawnsAreCovered) {
    RoomSpec r = RoomSpec::load(repo_root() + "/game/data/rooms/gang.json");
    ASSERT_TRUE(r.ok());
    EXPECT_EQ(r.shots.size(), 3u);
    EXPECT_GE(r.colliders.size(), 5u);
    for (auto& [id, s] : r.spawns) {
        bool covered = false;
        for (auto& sh : r.shots) covered |= sh.zone.has(s.pos.x, s.pos.z);
        EXPECT_TRUE(covered) << id;
    }
}

TEST(Sweep, BentLimbIsContinuousAndFinite) {
    Sweep s(20, 10, Profile{{{0, 0.06f, 0.06f, 0}, {0.5f, 0.045f, 0.045f, 0}, {1, 0.04f, 0.04f, 0}}}, MAT_CLOTH, WHITE, 0.6f);
    s.build({{0, 1.4f, 0}, {0, 1.1f, -0.15f}, {0, 1.0f, -0.4f}}, {1, 0, 0});   // an elbow bent 70 degrees
    ASSERT_EQ(s.data.count(), size_t(19 * 10 * 6));
    for (float v : s.data.pos) ASSERT_TRUE(std::isfinite(v));
    for (float v : s.data.nrm) ASSERT_TRUE(std::isfinite(v));
}
