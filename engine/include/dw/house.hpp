// damned_waters/engine/include/dw/house.hpp
// Purpose: the house as one floor plan per storey. Each room sits at its "origin", so the rooms
// of a storey share coordinates and a doorway in one room's wall is the same hole as the doorway
// in the next room's wall (they're paired here). From that: which room a point is in, whether a
// line of sight is blocked by a wall or a shut door, and which doorway leads on toward another
// room (for a Drowned following him through the house). Pure, unit-tested (tests/test_house.cpp).
//
// ELI5: a building plan on one big sheet. Every room is drawn where it really is, so you can rule
// a line across the sheet and see which walls it crosses, or trace a way out through the doors.
#ifndef DW_HOUSE_HPP
#define DW_HOUSE_HPP
#include <string>
#include <vector>

#include "dw/core.hpp"
#include "dw/room_spec.hpp"

namespace dw::house {

// A hole in a wall that a door hangs in. Paired: the same doorway as seen from the room on each
// side (a and b). Unpaired (b = -1): the front door, or a door to another storey.
struct Doorway {
    int a = -1, b = -1;                 // rooms either side (indices into the room list); b = -1: none on this storey
    int open_a = -1, open_b = -1;       // the opening in each room's list
    std::string door_a, door_b;         // the "door" interactable on each side ("" if none)
    float ax = 0, az = 0, bx = 0, bz = 0;   // its two ends on the wall's centre line (house coordinates)
    float nx = 0, nz = 0;               // unit normal, from room a's side to room b's side
    float height = 2.1f;
    bool hinge_at_a = true;             // the leaf turns on the (ax, az) end
    bool live = false;                  // the game hangs and swings its leaf (else the picture shows it shut)
    float mid_x() const { return (ax + bx) / 2; }
    float mid_z() const { return (az + bz) / 2; }
    float width() const;
};

// All the doorways of all the rooms (rooms already moved to their origins). Doorways pair up only
// within a storey. A door is live when it has a room behind it or its door leads somewhere
// (another storey): those are the ones he can open.
std::vector<Doorway> doorways(const std::vector<RoomSpec>& rooms);

// The room on `storey` whose floor holds (x, z); `prefer` wins where two touch. -1: none (in a
// doorway, inside a wall).
int room_at(const std::vector<RoomSpec>& rooms, int storey, float x, float z, int prefer = -1);

// Does the segment a-b cross any of these boxes? (Walls and shut doors block sight; props don't.)
bool crosses(const std::vector<Obb2>& boxes, float ax, float az, float bx, float bz);
// How far along a-b (0..1) the segment first meets one of the boxes; 1 or more: it doesn't.
float first_cross(const std::vector<Obb2>& boxes, float ax, float az, float bx, float bz);

// The doorway to go through next, from room `from` toward room `to`, through live paired doorways
// (breadth first: fewest doors). -1: same room, or no way through.
int next_doorway(const std::vector<Doorway>& doors, int from, int to);

}  // namespace dw::house
#endif
