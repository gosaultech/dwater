// damned_waters/engine/include/dw/room_spec.hpp
// Purpose: the RoomSpec JSON (game/data/rooms/<id>.json) as C++ data. The SAME
// file drives the Blender background renders, so collision, cameras and
// pictures always agree. A room is written in its own coordinates (its corner at 0, 0); its
// "origin" says where that corner lies in the house, and translate() moves it there, so rooms
// on a storey share one floor plan (house.hpp).
#ifndef DW_ROOM_SPEC_HPP
#define DW_ROOM_SPEC_HPP
#include <map>
#include <string>
#include <vector>
#include "dw/core.hpp"

namespace dw {

struct V3 { float x = 0, y = 0, z = 0; };
struct Shot { std::string id; V3 pos, look_at; float fov = 55; Rect2 zone{}; int priority = 0; };
struct Spawn { V3 pos; float yaw = 0; };
struct Light { std::string kind; V3 pos, look_at, dir_from; V3 color{1, 1, 1}; float energy = 1, range = 6, spot_angle = 60; bool flicker = false; };
struct EnemySpawn { std::string id, kind, requires_flag; V3 pos; float yaw = 0; bool emerge = false; };
// Something to walk up to and press Interact at. kind: "pickup" (item, count), "note" (title,
// text), "examine" (text), "door" (target_room, target_spawn; lock: the key it needs), "save",
// "end". Text fields hold what that kind shows.
struct Interactable {
    std::string id, kind, item, title, text, target_room, target_spawn, lock, locked_text, unlock_text, sets_flag, then_text;
    V3 pos;
    float radius = 1;
    int count = 1;
    Shot peek;              // a door: the view through the crack when it's eased ajar (peek.id empty: none)
};
// A hole in a wall: "door", "window", "gate". side: north (the -z wall), south, west (-x), east.
// center: along the wall from its low corner (x for north/south, z for west/east).
struct Opening {
    std::string side, kind, hinge;   // hinge: "left" / "right" as seen from inside this room (doors)
    float center = 0, width = 1, height = 2, sill = 0;
};

struct RoomSpec {
    std::string id, display_name;
    std::string footsteps = "wood", ambience;   // which step_*.wav the floor makes; the looping amb_*.wav
    Rect2 bounds{};
    float height = 3;
    std::vector<Shot> shots;
    std::map<std::string, Spawn> spawns;
    std::vector<Light> lights;
    std::vector<EnemySpawn> enemies;
    std::vector<Interactable> interactables;
    int floor = 0;                 // which storey it's on ("storey": 0 the ground floor, -1 a cellar): for the map
    float origin_x = 0, origin_z = 0;   // where the room's corner lies in the house ("origin": [x, z])
    bool has_origin = false;
    std::vector<Opening> openings;
    std::vector<Obb2> colliders;   // walls (with gaps at the doors) + solid props, on the floor plane
    size_t wall_count = 0;         // the first wall_count colliders are the walls (they block sight; props don't)
    std::vector<std::string> errors;

    static RoomSpec load(const std::string& path);
    std::vector<ShotZone> zones() const;
    bool ok() const { return errors.empty(); }
    // Move everything (bounds, shots, spawns, lights, things, colliders) by (dx, dz).
    void translate(float dx, float dz);
    // An opening's ends on the wall's centre line, in this room's current coordinates.
    void opening_ends(const Opening& o, float& ax, float& az, float& bx, float& bz) const;
};

constexpr float WALL_T = 0.3f;   // wall thickness: walls grow outward from a room's bounds (as Blender builds them)

std::string repo_root();

}  // namespace dw
#endif
