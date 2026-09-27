// damned_waters/engine/include/dw/room_spec.hpp
// Purpose: the RoomSpec JSON (game/data/rooms/<id>.json) as C++ data. The SAME
// file drives the Blender background renders, so collision, cameras and
// pictures always agree.
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

struct RoomSpec {
    std::string id, display_name;
    Rect2 bounds{};
    float height = 3;
    std::vector<Shot> shots;
    std::map<std::string, Spawn> spawns;
    std::vector<Light> lights;
    std::vector<EnemySpawn> enemies;
    std::vector<Obb2> colliders;   // walls + solid props, on the floor plane
    std::vector<std::string> errors;

    static RoomSpec load(const std::string& path);
    std::vector<ShotZone> zones() const;
    bool ok() const { return errors.empty(); }
};

std::string repo_root();

}  // namespace dw
#endif
