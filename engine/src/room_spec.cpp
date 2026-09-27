// damned_waters/engine/src/room_spec.cpp
// Purpose: parse RoomSpec JSON with nlohmann/json and derive floor colliders
// (walls as slabs outside the bounds, props from their footprint size + yaw).
#include "dw/room_spec.hpp"

#include <fstream>
#include <nlohmann/json.hpp>

namespace dw {
namespace {
using json = nlohmann::json;
constexpr float WALL_T = 0.3f;
constexpr float DEG = kPi / 180.0f;

V3 v3(const json& a) { return {a.at(0).get<float>(), a.at(1).get<float>(), a.at(2).get<float>()}; }
Rect2 rect(const json& lo, const json& hi) { return {lo[0].get<float>(), lo[1].get<float>(), hi[0].get<float>(), hi[1].get<float>()}; }
}  // namespace

std::string repo_root() {
#ifdef DW_REPO_ROOT
    return DW_REPO_ROOT;
#else
    return "..";
#endif
}

RoomSpec RoomSpec::load(const std::string& path) {
    RoomSpec r;
    std::ifstream f(path);
    if (!f) { r.errors.push_back("cannot open " + path); return r; }
    json d;
    try { d = json::parse(f); } catch (const std::exception& e) { r.errors.push_back(e.what()); return r; }
    for (const char* k : {"id", "bounds", "height", "shots", "spawns"})
        if (!d.contains(k)) r.errors.push_back(std::string("missing ") + k);
    if (!r.errors.empty()) return r;
    r.id = d["id"];
    r.display_name = d.value("display_name", r.id);
    r.bounds = rect(d["bounds"]["min"], d["bounds"]["max"]);
    r.height = d["height"];
    for (const auto& s : d["shots"])
        r.shots.push_back({s["id"], v3(s["pos"]), v3(s["look_at"]), s["fov"], rect(s["zone"]["min"], s["zone"]["max"]), s.value("priority", 0)});
    for (const auto& [k, s] : d["spawns"].items()) r.spawns[k] = {v3(s["pos"]), s.value("yaw", 0.0f) * DEG};
    for (const auto& l : d.value("lights", json::array())) {
        Light L;
        L.kind = l["kind"];
        if (l.contains("pos")) L.pos = v3(l["pos"]);
        if (l.contains("look_at")) L.look_at = v3(l["look_at"]);
        if (l.contains("dir_from")) L.dir_from = v3(l["dir_from"]);
        L.color = v3(l["color"]);
        L.energy = l.value("godot_energy", 1.0f);
        L.range = l.value("range", 6.0f);
        L.spot_angle = l.value("spot_angle", 70.0f);
        L.flicker = l.value("flicker", false);
        r.lights.push_back(L);
    }
    for (const auto& e : d.value("enemies", json::array()))
        r.enemies.push_back({e["id"], e.value("kind", "verdronkene"), e.value("requires_flag", ""), v3(e["pos"]),
                             e.value("yaw", 0.0f) * DEG, e.value("emerge", false)});
    const Rect2& b = r.bounds;
    const float w = b.x1 - b.x0, dz = b.z1 - b.z0, t = WALL_T;
    r.colliders.push_back({(b.x0 + b.x1) / 2, b.z0 - t / 2, w / 2 + t, t / 2, 0});   // north
    r.colliders.push_back({(b.x0 + b.x1) / 2, b.z1 + t / 2, w / 2 + t, t / 2, 0});   // south
    r.colliders.push_back({b.x0 - t / 2, (b.z0 + b.z1) / 2, t / 2, dz / 2, 0});      // west
    r.colliders.push_back({b.x1 + t / 2, (b.z0 + b.z1) / 2, t / 2, dz / 2, 0});      // east
    for (const auto& p : d.value("props", json::array())) {
        if (!p.value("collide", true) || !p.contains("size")) continue;
        V3 pos = v3(p["pos"]), sz = v3(p["size"]);
        r.colliders.push_back({pos.x, pos.z, sz.x / 2, sz.z / 2, p.value("yaw", 0.0f) * DEG});
    }
    return r;
}

std::vector<ShotZone> RoomSpec::zones() const {
    std::vector<ShotZone> z;
    for (const auto& s : shots) z.push_back({s.id, s.zone, s.priority});
    return z;
}

}  // namespace dw
