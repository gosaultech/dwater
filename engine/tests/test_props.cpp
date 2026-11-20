// damned_waters/engine/tests/test_props.cpp
// Purpose: what stands in his way (dw::solid_footprint, room_spec.cpp). The play-test's "he walks
// through gates and bins": things the set builder left without a footprint, or let him through,
// must block him when a person couldn't walk through them; what lies flat, is small or soft, sits
// up on something, or is walked into, must not.
#include <gtest/gtest.h>

#include <nlohmann/json.hpp>

#include "dw/room_spec.hpp"

using namespace dw;
using json = nlohmann::json;

namespace {
const std::map<std::string, V3> SIZES = {{"cardboard_box_01", {0.387f, 0.516f, 0.342f}}, {"can_rusted", {0.08f, 0.08f, 0.12f}},
                                         {"wine_barrel_01", {0.6f, 0.6f, 0.9f}}, {"trashbag", {0.53f, 0.46f, 0.58f}}};
bool solid(const char* text, Obb2* out = nullptr) {
    Obb2 c{};
    const bool s = solid_footprint(json::parse(text), SIZES, c);
    if (out) *out = c;
    return s;
}
}  // namespace

TEST(Props, WhatTheSetBuilderMadeSolidStaysSolid) {
    Obb2 c{};
    ASSERT_TRUE(solid(R"({"type": "block", "pos": [1, 0, 2], "size": [2, 1, 0.5], "yaw": 90})", &c));
    EXPECT_FLOAT_EQ(c.hx, 1.0f);
    EXPECT_FLOAT_EQ(c.hz, 0.25f);
    EXPECT_NEAR(c.yaw, kPi / 2, 1e-5f);
}

TEST(Props, BinsAndBoxesBlockHimStandingOrKnockedOver) {
    Obb2 c{};
    ASSERT_TRUE(solid(R"({"type": "model", "model": "sf:bin_green", "pos": [3, 0, 4], "collide": false})", &c));   // a wheelie bin
    EXPECT_NEAR(c.hx * 2, 0.58f, 1e-4f);
    ASSERT_TRUE(solid(R"({"type": "model", "model": "sf:bin_green", "pos": [3, 0, 4], "collide": false, "tip": 90})", &c));
    EXPECT_NEAR(c.hz * 2, 1.07f, 1e-4f);   // on its side: as long as it was tall
    EXPECT_TRUE(solid(R"({"type": "model", "model": "ph:cardboard_box_01", "pos": [0, 0, 0], "scale": 1.0, "collide": false})"));
    EXPECT_TRUE(solid(R"({"type": "model", "model": "ph:wine_barrel_01", "pos": [0, 0, 0], "scale": 0.9})"));
    EXPECT_TRUE(solid(R"({"type": "model", "model": "ph:whatever", "pos": [0, 0, 0], "fit": [3.0, 1.0, 0.7]})"));   // (a road block, fitted)
}

TEST(Props, StreetRailingsAndStandingBikesBlockHim) {
    Obb2 c{};
    ASSERT_TRUE(solid(R"({"type": "railing", "pos": [10, 0, 3], "size": [20, 1, 0.05], "collide": false})", &c));
    EXPECT_GE(c.hz, 0.12f);   // thick enough that a step can't jump it
    EXPECT_TRUE(solid(R"({"type": "bike", "pos": [0, 0, 0], "size": [1.8, 1.1, 0.5], "collide": false})"));
    EXPECT_TRUE(solid(R"({"type": "windbreak", "pos": [0, 0, 0], "size": [6, 1.5, 0.1], "collide": false})"));
}

TEST(Props, WhatLiesFlatIsSmallOrSoftSitsUpHighOrIsWalkedIntoDoesNot) {
    EXPECT_FALSE(solid(R"({"type": "bike", "pos": [0, 0, 0], "roll": 84, "size": [1.8, 1.1, 0.5], "collide": false})"));       // fallen
    EXPECT_FALSE(solid(R"({"type": "crowd_barrier", "pos": [0, 0, 0], "size": [5, 2.2, 0.1], "collide": false})"));            // a gate left open
    EXPECT_FALSE(solid(R"({"type": "model", "model": "ph:can_rusted", "pos": [0, 0, 0], "collide": false})"));                 // small
    EXPECT_FALSE(solid(R"({"type": "model", "model": "ph:trashbag", "pos": [0, 0, 0], "collide": false})"));                   // soft
    EXPECT_FALSE(solid(R"({"type": "model", "model": "ph:cardboard_box_01", "pos": [0, 0.9, 0], "collide": false})"));         // on a counter
    EXPECT_FALSE(solid(R"({"type": "flower_stall", "pos": [0, 0, 0], "size": [7, 4, 4.5], "collide": false})"));               // walked into
    EXPECT_FALSE(solid(R"({"type": "luggage", "pos": [0, 0, 0], "size": [3, 0, 2], "collide": false})"));                      // spilled about
    EXPECT_FALSE(solid(R"({"type": "model", "model": "ph:not_in_the_ledger", "pos": [0, 0, 0]})"));                             // unknown size
}

TEST(Props, TheRoomsBlockTheirBinsButNeverAWayIn) {
    // Every room as shipped: a spawn or an enemy is never inside something solid that the set
    // builder didn't put there to be solid (room_spec.cpp drops such a footprint).
    for (const char* id : {"kalversteeg", "bloemenmarkt", "rokin_noord", "dam", "rondvaartboot", "waterpoort", "thorbeckeplein"}) {
        const RoomSpec r = RoomSpec::load(repo_root() + "/game/data/rooms/" + id + ".json");
        ASSERT_TRUE(r.ok()) << id;
        EXPECT_GT(r.colliders.size(), r.wall_count) << id;
        for (size_t i = r.wall_count; i < r.colliders.size(); ++i)
            for (const auto& [k, s] : r.spawns) {
                float x = s.pos.x, z = s.pos.z;
                EXPECT_FALSE(resolve_circle_obb(x, z, 0.28f, r.colliders[i]) && std::hypot(x - s.pos.x, z - s.pos.z) > 0.12f) << id << " spawn " << k;
            }
    }
}
