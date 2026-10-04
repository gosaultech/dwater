// damned_waters/engine/src/world_map.cpp
// Purpose: laying the rooms out against each other by their doors (world_map.hpp).
#include "dw/world_map.hpp"

#include <algorithm>
#include <cmath>
#include <deque>
#include <filesystem>

namespace dw::worldmap {

Room from_spec(const RoomSpec& s) {
    Room r;
    r.id = s.id;
    r.name = s.display_name;
    r.storey = s.floor;
    r.bounds = s.bounds;
    for (const auto& [k, sp] : s.spawns) r.spawns[k] = {sp.pos.x, sp.pos.z};
    for (const auto& i : s.interactables)
        if (i.kind == "door" && !i.target_room.empty()) r.doors.push_back({i.pos.x, i.pos.z, i.target_room, i.target_spawn, i.lock, i.id, false});
    return r;
}

std::vector<Room> load_all(const std::string& dir) {
    std::vector<std::string> files;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(dir, ec))
        if (e.path().extension() == ".json") files.push_back(e.path().string());
    std::sort(files.begin(), files.end());   // (the same order on every machine)
    std::vector<Room> rooms;
    for (const auto& f : files) {
        const RoomSpec s = RoomSpec::load(f);
        if (s.ok()) rooms.push_back(from_spec(s));
    }
    for (auto& r : rooms)   // a door to another storey is a stair
        for (auto& d : r.doors)
            for (const auto& o : rooms)
                if (o.id == d.to) d.stairs = o.storey != r.storey;
    return rooms;
}

std::pair<float, float> to_edge(const Rect2& r, float x, float z) {
    const float dx0 = std::fabs(x - r.x0), dx1 = std::fabs(r.x1 - x), dz0 = std::fabs(z - r.z0), dz1 = std::fabs(r.z1 - z);
    const float m = std::min({dx0, dx1, dz0, dz1});
    if (m == dx0) return {r.x0, std::clamp(z, r.z0, r.z1)};
    if (m == dx1) return {r.x1, std::clamp(z, r.z0, r.z1)};
    if (m == dz0) return {std::clamp(x, r.x0, r.x1), r.z0};
    return {std::clamp(x, r.x0, r.x1), r.z1};
}

void place(std::vector<Room>& rooms, const std::string& start) {
    auto find = [&](const std::string& id) -> Room* {
        for (auto& r : rooms)
            if (r.id == id) return &r;
        return nullptr;
    };
    Room* s = find(start);
    if (!s) return;
    s->ox = s->oz = 0;
    s->placed = true;
    std::deque<Room*> todo{s};
    while (!todo.empty()) {
        Room* a = todo.front();
        todo.pop_front();
        for (const Door& d : a->doors) {
            Room* b = find(d.to);
            if (!b || b->placed) continue;
            const auto sp = b->spawns.find(d.to_spawn);
            const auto [bx, bz] = sp != b->spawns.end() ? sp->second : std::pair{(b->bounds.x0 + b->bounds.x1) / 2, (b->bounds.z0 + b->bounds.z1) / 2};
            // The doorway, in each room's own walls (the arrival spot stands a step inside).
            const auto [ax, az] = d.stairs ? std::pair{d.x, d.z} : to_edge(a->bounds, d.x, d.z);
            const auto [ex, ez] = d.stairs ? std::pair{bx, bz} : to_edge(b->bounds, bx, bz);
            b->ox = a->ox + ax - ex;
            b->oz = a->oz + az - ez;
            b->placed = true;
            todo.push_back(b);
        }
    }
}

std::vector<int> storeys(const std::vector<Room>& rooms) {
    std::vector<int> s;
    for (const auto& r : rooms)
        if (std::find(s.begin(), s.end(), r.storey) == s.end()) s.push_back(r.storey);
    std::sort(s.begin(), s.end(), std::greater<int>());
    return s;
}

}  // namespace dw::worldmap
