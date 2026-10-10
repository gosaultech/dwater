// damned_waters/engine/tests/test_house.cpp
// Purpose: GoogleTest suite for the house's floor plan (house.hpp, room_spec origins and wall
// gaps): two rooms written in their own coordinates, moved to their origins, share one doorway;
// the wall has a gap there; sight is blocked by walls but not through the doorway; a point is in
// the right room; the way from one room to another goes through the right doors.
#include <gtest/gtest.h>

#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>

#include "dw/house.hpp"

using namespace dw;
namespace fs = std::filesystem;

namespace {
// A hall 2 wide, 6 deep, a door in its west wall at z = 4; a parlour 4 wide, 5 deep, west of it,
// its door in its east wall at z = 3 (so its origin is z = 1 to line them up), a back room north
// of the parlour through a door in the parlour's north wall.
const char* HALL = R"({"id": "hall", "origin": [0, 0], "bounds": {"min": [0, 0], "max": [2, 6]}, "height": 3,
  "walls": {"west": {"openings": [{"kind": "door", "center": 4.0, "width": 0.9, "height": 2.2}]},
            "south": {"openings": [{"kind": "door", "center": 1.0, "width": 1.0, "height": 2.4}]}},
  "shots": [{"id": "a", "pos": [1, 2, 5], "look_at": [1, 1, 0], "fov": 50, "zone": {"min": [0, 0], "max": [2, 6]}}],
  "spawns": {"start": {"pos": [1, 0, 5]}},
  "interactables": [{"id": "to_parlour", "kind": "door", "pos": [0.15, 1, 4.0], "target_room": "parlour", "target_spawn": "from_hall"},
                    {"id": "front", "kind": "examine", "pos": [1, 1, 5.8], "text": "Locked."}]})";
const char* PARLOUR = R"({"id": "parlour", "origin": [-4.3, 1.0], "bounds": {"min": [0, 0], "max": [4, 5]}, "height": 3,
  "walls": {"east": {"openings": [{"kind": "door", "center": 3.0, "width": 0.9, "height": 2.2, "hinge": "right"}]},
            "north": {"openings": [{"kind": "door", "center": 2.0, "width": 0.8, "height": 2.1}]}},
  "props": [{"type": "table", "pos": [2, 0, 2.5], "size": [1, 0.8, 1]}],
  "shots": [{"id": "a", "pos": [3.5, 2, 4.5], "look_at": [1, 1, 1], "fov": 50, "zone": {"min": [0, 0], "max": [4, 5]}}],
  "spawns": {"from_hall": {"pos": [3.6, 0, 3.0], "yaw": 90}},
  "interactables": [{"id": "to_hall", "kind": "door", "pos": [3.85, 1, 3.0], "target_room": "hall", "target_spawn": "start"},
                    {"id": "to_back", "kind": "door", "pos": [2.0, 1, 0.15], "target_room": "back", "target_spawn": "s"}]})";
const char* BACK = R"({"id": "back", "origin": [-4.3, -3.3], "bounds": {"min": [0, 0], "max": [4, 4]}, "height": 3,
  "walls": {"south": {"openings": [{"kind": "door", "center": 2.0, "width": 0.8, "height": 2.1}]}},
  "shots": [{"id": "a", "pos": [2, 2, 3.5], "look_at": [2, 1, 0], "fov": 50, "zone": {"min": [0, 0], "max": [4, 4]}}],
  "spawns": {"s": {"pos": [2, 0, 3.6]}},
  "interactables": [{"id": "to_parlour", "kind": "door", "pos": [2.0, 1, 3.85], "target_room": "parlour", "target_spawn": "from_hall"}]})";

RoomSpec load_text(const std::string& name, const char* text) {
    const fs::path p = fs::temp_directory_path() / ("dw_house_" + name + ".json");
    std::ofstream(p) << text;
    RoomSpec r = RoomSpec::load(p.string());
    fs::remove(p);
    r.translate(r.origin_x, r.origin_z);
    return r;
}

std::vector<RoomSpec> three_rooms() { return {load_text("hall", HALL), load_text("parlour", PARLOUR), load_text("back", BACK)}; }

bool in_walls(const RoomSpec& r, float x, float z) {
    for (size_t i = 0; i < r.wall_count; ++i) {
        float px = x, pz = z;
        if (resolve_circle_obb(px, pz, 0.01f, r.colliders[i])) return true;
    }
    return false;
}
}  // namespace

TEST(House, OriginsMoveEverything) {
    const auto rooms = three_rooms();
    ASSERT_TRUE(rooms[1].ok());
    EXPECT_FLOAT_EQ(rooms[1].bounds.x0, -4.3f);
    EXPECT_FLOAT_EQ(rooms[1].bounds.z1, 6.0f);
    EXPECT_NEAR(rooms[1].spawns.at("from_hall").pos.x, -0.7f, 1e-5f);
    EXPECT_NEAR(rooms[1].shots[0].zone.x1, -0.3f, 1e-5f);
}

TEST(House, PairedDoorwayIsOneHole) {
    const auto rooms = three_rooms();
    const auto doors = house::doorways(rooms);
    ASSERT_EQ(doors.size(), 3u);   // hall-parlour, the hall's front door, parlour-back
    const house::Doorway* hp = nullptr;
    for (const auto& d : doors)
        if ((d.a == 0 && d.b == 1) || (d.a == 1 && d.b == 0)) hp = &d;
    ASSERT_NE(hp, nullptr);
    EXPECT_TRUE(hp->live);
    EXPECT_NEAR(hp->mid_x(), -0.15f, 1e-4f);   // the middle of the 0.3 m wall between them
    EXPECT_NEAR(hp->mid_z(), 4.0f, 1e-4f);
    EXPECT_NEAR(hp->width(), 0.9f, 1e-4f);
    EXPECT_EQ(hp->door_a, "to_parlour");
    EXPECT_EQ(hp->door_b, "to_hall");
}

TEST(House, FrontDoorIsPaintedShut) {
    const auto doors = house::doorways(three_rooms());
    for (const auto& d : doors)
        if (d.a == 0 && d.b < 0) EXPECT_FALSE(d.live);   // an "examine" door leads nowhere: the picture keeps it shut
}

TEST(House, WallsHaveGapsAtDoors) {
    const auto rooms = three_rooms();
    EXPECT_FALSE(in_walls(rooms[0], -0.15f, 4.0f));   // the hall's west wall, in the doorway
    EXPECT_TRUE(in_walls(rooms[0], -0.15f, 2.0f));    // ... and beside it
    EXPECT_FALSE(in_walls(rooms[1], -0.15f, 4.0f));   // the parlour's east wall has the same gap
    EXPECT_FALSE(in_walls(rooms[0], 1.0f, 6.15f));    // the front door's gap (its leaf blocks it)
}

TEST(House, RoomAtPrefersWhereHeIs) {
    const auto rooms = three_rooms();
    EXPECT_EQ(house::room_at(rooms, 0, 1.0f, 3.0f), 0);
    EXPECT_EQ(house::room_at(rooms, 0, -2.0f, 3.0f), 1);
    EXPECT_EQ(house::room_at(rooms, 0, -0.15f, 4.0f), -1);   // in the doorway itself
    EXPECT_EQ(house::room_at(rooms, -1, 1.0f, 3.0f), -1);    // not on that storey
}

TEST(House, SightStopsAtWallsButNotDoorways) {
    const auto rooms = three_rooms();
    std::vector<Obb2> walls;
    for (const auto& r : rooms) walls.insert(walls.end(), r.colliders.begin(), r.colliders.begin() + long(r.wall_count));
    EXPECT_FALSE(house::crosses(walls, 1.0f, 4.0f, -2.0f, 4.0f));   // straight through the doorway
    EXPECT_TRUE(house::crosses(walls, 1.0f, 2.0f, -2.0f, 2.0f));    // through the wall beside it
    // a shot from the hall west across the wall stops at its inner face (x = 0, a third of the way)
    EXPECT_NEAR(house::first_cross(walls, 1.0f, 2.0f, -2.0f, 2.0f), 1.0f / 3.0f, 1e-4f);
    EXPECT_GE(house::first_cross(walls, 1.0f, 4.0f, -2.0f, 4.0f), 1.0f);
}

TEST(House, TheWayThroughTheDoors) {
    const auto rooms = three_rooms();
    const auto doors = house::doorways(rooms);
    const int first = house::next_doorway(doors, 0, 2);   // hall -> back room: via the parlour
    ASSERT_GE(first, 0);
    EXPECT_TRUE((doors[size_t(first)].a == 0 && doors[size_t(first)].b == 1) || (doors[size_t(first)].a == 1 && doors[size_t(first)].b == 0));
    EXPECT_EQ(house::next_doorway(doors, 1, 1), -1);
}

TEST(House, HingeSideFollowsTheSpec) {
    const auto rooms = three_rooms();
    const auto doors = house::doorways(rooms);
    for (const auto& d : doors)
        if (d.a == 1 && d.b == 0) {   // the parlour's east door, hinged on the right seen from inside: its south end
            EXPECT_FALSE(d.hinge_at_a);
        }
}

// The real house: the hall and the parlour share one doorway the game swings; the cellar door is a
// live door with no room behind it on that floor (the stairs down); the canal fronts are flush.
TEST(House, TheRealHouseFitsTogether) {
    std::vector<RoomSpec> rooms;
    for (const char* id : {"gang", "kelder", "voorkamer"}) {   // (name order, as the game loads them)
        RoomSpec r = RoomSpec::load(repo_root() + "/game/data/rooms/" + id + ".json");
        ASSERT_TRUE(r.ok()) << id;
        ASSERT_TRUE(r.has_origin) << id;
        r.translate(r.origin_x, r.origin_z);
        rooms.push_back(r);
    }
    const auto doors = house::doorways(rooms);
    int shared = 0, stairs = 0;
    for (const auto& d : doors) {
        if (d.live && d.b >= 0 && rooms[size_t(d.a)].id == "gang" && rooms[size_t(d.b)].id == "voorkamer") ++shared;
        if (d.live && d.b < 0 && rooms[size_t(d.a)].id == "gang" && d.door_a == "door_kelder") ++stairs;
    }
    EXPECT_EQ(shared, 1);
    EXPECT_EQ(stairs, 1);
    EXPECT_NEAR(rooms[0].bounds.z1, rooms[2].bounds.z1, 1e-4f);
    EXPECT_EQ(rooms[1].floor, -1);
}
