// damned_waters/engine/tests/test_world_map.cpp
// Purpose: GoogleTest suite for the map's layout (world_map.hpp): two rooms joined by a doorway
// meet at it, a room off a stair goes on its own storey, and the real room files lay out with the
// parlour west of the hall and the cellar a storey down.
#include <gtest/gtest.h>

#include <cmath>

#include "dw/world_map.hpp"

using namespace dw;
using namespace dw::worldmap;

TEST(WorldMap, RoomsMeetAtTheirDoorway) {
    Room hall, parlour;
    hall.id = "hall";
    hall.bounds = {0, 0, 2, 10};
    hall.doors.push_back({0.15f, 6.8f, "parlour", "from_hall"});   // a door in the west wall
    parlour.id = "parlour";
    parlour.bounds = {0, 0, 5, 6};
    parlour.spawns["from_hall"] = {4.7f, 3.0f};                    // arriving a step inside its east wall
    std::vector<Room> rooms{hall, parlour};
    place(rooms, "hall");
    ASSERT_TRUE(rooms[1].placed);
    EXPECT_NEAR(rooms[1].ox, -5.0f, 1e-4f);   // its east wall on the hall's west wall
    EXPECT_NEAR(rooms[1].oz, 3.8f, 1e-4f);    // the doorways line up
}

TEST(WorldMap, EdgesSnapToTheNearestWall) {
    const Rect2 r{0, 0, 4, 8};
    const auto [x, z] = to_edge(r, 3.7f, 5.0f);
    EXPECT_FLOAT_EQ(x, 4.0f);
    EXPECT_FLOAT_EQ(z, 5.0f);
}

TEST(WorldMap, TheHouseLaysOut) {
    std::vector<Room> rooms = load_all(repo_root() + "/game/data/rooms");
    ASSERT_GE(rooms.size(), 3u);
    place(rooms, "gang");
    const Room *gang = nullptr, *voor = nullptr, *kelder = nullptr;
    for (const auto& r : rooms) {
        EXPECT_TRUE(r.placed) << r.id;
        if (r.id == "gang") gang = &r;
        if (r.id == "voorkamer") voor = &r;
        if (r.id == "kelder") kelder = &r;
    }
    ASSERT_TRUE(gang && voor && kelder);
    EXPECT_LT(voor->ox + voor->bounds.x1, gang->ox + 0.01f);   // the parlour is west of the hall
    EXPECT_EQ(kelder->storey, -1);
    const auto s = storeys(rooms);
    ASSERT_EQ(s.size(), 2u);
    EXPECT_EQ(s[0], 0);
    EXPECT_EQ(s[1], -1);
}
