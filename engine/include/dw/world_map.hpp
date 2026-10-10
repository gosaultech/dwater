// damned_waters/engine/include/dw/world_map.hpp
// Purpose: the map on the status screen, worked out from the room files themselves: each room's
// floor plan (its bounds), its doors and where they lead, and which storey it's on. Rooms are
// placed against each other by their doors: a door in one room and the spot it brings you to in
// the next are the same doorway, so the two rooms meet there. Nobody has to draw the map; a new
// room joins it by its doors. Pure layout, unit-tested (tests/test_world_map.cpp).
//
// Like laying out a jigsaw from its tabs: each room's doors say which piece fits there, and the
// first piece down decides where the rest go.
#ifndef DW_WORLD_MAP_HPP
#define DW_WORLD_MAP_HPP
#include <map>
#include <string>
#include <vector>

#include "dw/core.hpp"
#include "dw/room_spec.hpp"

namespace dw::worldmap {

struct Door {
    float x = 0, z = 0;                     // where it is in its room (m)
    std::string to, to_spawn, lock, id;     // the room it opens on, where you arrive there, the key it wants
    bool stairs = false;                    // to another storey
};
struct Room {
    std::string id, name;
    int storey = 0;
    Rect2 bounds{};
    std::map<std::string, std::pair<float, float>> spawns;   // name -> (x, z)
    std::vector<Door> doors;
    float ox = 0, oz = 0;                   // where its origin lies on the map (m)
    bool placed = false;
};

Room from_spec(const RoomSpec& s);
// Every room file in `dir` (game/data/rooms).
std::vector<Room> load_all(const std::string& dir);
// Place every room that can be reached from `start` (which sits at the origin, unless the room
// files give origins: then those stand) through doors.
void place(std::vector<Room>& rooms, const std::string& start);
// The storeys there are, top first (0 before -1).
std::vector<int> storeys(const std::vector<Room>& rooms);
// A point snapped onto the nearest edge of a rectangle (a door sits in a wall).
std::pair<float, float> to_edge(const Rect2& r, float x, float z);

}  // namespace dw::worldmap
#endif
