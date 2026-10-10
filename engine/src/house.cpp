// damned_waters/engine/src/house.cpp
// Purpose: the house's floor plan per storey (house.hpp): pairing doorways, which room a point is
// in, sight lines across walls, and the way through the doors.
#include "dw/house.hpp"

#include <algorithm>
#include <cmath>
#include <deque>

namespace dw::house {
namespace {
constexpr float PAIR_TOL = 0.06f;   // two rooms' doorway ends this close are the same hole (m)
constexpr float DOOR_REACH = 1.6f;  // a door interactable this near an opening belongs to it

void normal_of(const std::string& side, float& nx, float& nz) {
    nx = side == "west" ? -1.0f : side == "east" ? 1.0f : 0.0f;
    nz = side == "north" ? -1.0f : side == "south" ? 1.0f : 0.0f;
}

// Which end the hinge is on: "left"/"right" as seen from inside the room, facing the wall.
bool hinge_on_low_end(const Opening& o) {
    const bool left = o.hinge != "right";
    const bool low_is_left = o.side == "north" || o.side == "east";
    return left == low_is_left;
}

std::string door_near(const RoomSpec& r, float x, float z) {
    std::string best;
    float bd = DOOR_REACH;
    for (const auto& i : r.interactables) {
        if (i.kind != "door") continue;
        const float d = std::hypot(i.pos.x - x, i.pos.z - z);
        if (d < bd) { bd = d; best = i.id; }
    }
    return best;
}

const Interactable* find(const RoomSpec& r, const std::string& id) {
    for (const auto& i : r.interactables)
        if (i.id == id) return &i;
    return nullptr;
}
}  // namespace

float Doorway::width() const { return std::hypot(bx - ax, bz - az); }

std::vector<Doorway> doorways(const std::vector<RoomSpec>& rooms) {
    std::vector<Doorway> out;
    std::vector<std::vector<bool>> used(rooms.size());
    for (size_t r = 0; r < rooms.size(); ++r) used[r].assign(rooms[r].openings.size(), false);
    for (size_t r = 0; r < rooms.size(); ++r) {
        const RoomSpec& A = rooms[r];
        for (size_t k = 0; k < A.openings.size(); ++k) {
            const Opening& o = A.openings[k];
            if (o.kind != "door" || used[r][k]) continue;
            used[r][k] = true;
            Doorway d;
            d.a = int(r);
            d.open_a = int(k);
            A.opening_ends(o, d.ax, d.az, d.bx, d.bz);
            normal_of(o.side, d.nx, d.nz);
            d.height = o.height;
            d.hinge_at_a = hinge_on_low_end(o);
            d.door_a = door_near(A, d.mid_x(), d.mid_z());
            for (size_t s = 0; s < rooms.size() && d.b < 0; ++s) {   // the same hole in a neighbour's wall
                if (s == r || rooms[s].floor != A.floor) continue;
                const RoomSpec& B = rooms[s];
                for (size_t m = 0; m < B.openings.size(); ++m) {
                    const Opening& p = B.openings[m];
                    if (p.kind != "door" || used[s][m]) continue;
                    float px0, pz0, px1, pz1;
                    B.opening_ends(p, px0, pz0, px1, pz1);
                    if (std::hypot(px0 - d.ax, pz0 - d.az) < PAIR_TOL && std::hypot(px1 - d.bx, pz1 - d.bz) < PAIR_TOL) {
                        used[s][m] = true;
                        d.b = int(s);
                        d.open_b = int(m);
                        d.door_b = door_near(B, d.mid_x(), d.mid_z());
                        break;
                    }
                }
            }
            const Interactable* da = d.door_a.empty() ? nullptr : find(A, d.door_a);
            d.live = d.b >= 0 || (da && !da->target_room.empty());
            out.push_back(d);
        }
    }
    return out;
}

int room_at(const std::vector<RoomSpec>& rooms, int storey, float x, float z, int prefer) {
    if (prefer >= 0 && prefer < int(rooms.size()) && rooms[size_t(prefer)].floor == storey && rooms[size_t(prefer)].bounds.has(x, z))
        return prefer;
    for (size_t i = 0; i < rooms.size(); ++i)
        if (rooms[i].floor == storey && rooms[i].bounds.has(x, z)) return int(i);
    return -1;
}

bool crosses(const std::vector<Obb2>& boxes, float ax, float az, float bx, float bz) {
    return first_cross(boxes, ax, az, bx, bz) < 1.0f;
}

float first_cross(const std::vector<Obb2>& boxes, float ax, float az, float bx, float bz) {
    float first = 2.0f;
    for (const Obb2& b : boxes) {
        // Into the box's frame (as resolve_circle_obb), then a slab test on the segment.
        const float c = std::cos(b.yaw), s = std::sin(b.yaw);
        auto local = [&](float x, float z, float& lx, float& lz) {
            const float dx = x - b.cx, dz = z - b.cz;
            lx = dx * c - dz * s;
            lz = dx * s + dz * c;
        };
        float p0x, p0z, p1x, p1z;
        local(ax, az, p0x, p0z);
        local(bx, bz, p1x, p1z);
        float t0 = 0, t1 = 1;
        auto slab = [&](float p0, float p1, float h) {
            const float dv = p1 - p0;
            if (std::fabs(dv) < 1e-9f) return p0 >= -h && p0 <= h;
            float u0 = (-h - p0) / dv, u1 = (h - p0) / dv;
            if (u0 > u1) std::swap(u0, u1);
            t0 = std::max(t0, u0);
            t1 = std::min(t1, u1);
            return t0 <= t1;
        };
        if (slab(p0x, p1x, b.hx) && slab(p0z, p1z, b.hz)) first = std::min(first, t0);
    }
    return first;
}

int next_doorway(const std::vector<Doorway>& doors, int from, int to) {
    if (from < 0 || to < 0 || from == to) return -1;
    // Breadth first over rooms, remembering the first doorway taken out of `from`.
    std::deque<std::pair<int, int>> todo{{from, -1}};   // room, first doorway on the way there
    std::vector<int> seen{from};
    while (!todo.empty()) {
        const auto [room, first] = todo.front();
        todo.pop_front();
        for (size_t i = 0; i < doors.size(); ++i) {
            const Doorway& d = doors[i];
            if (!d.live || d.b < 0) continue;
            const int other = d.a == room ? d.b : d.b == room ? d.a : -1;
            if (other < 0 || std::find(seen.begin(), seen.end(), other) != seen.end()) continue;
            const int via = first < 0 ? int(i) : first;
            if (other == to) return via;
            seen.push_back(other);
            todo.push_back({other, via});
        }
    }
    return -1;
}

}  // namespace dw::house
