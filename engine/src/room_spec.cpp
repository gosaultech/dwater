// damned_waters/engine/src/room_spec.cpp
// Purpose: parse RoomSpec JSON with nlohmann/json and derive floor colliders
// (walls as slabs outside the bounds, props from their footprint size + yaw).
#include "dw/room_spec.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>

#include <fstream>
#include <nlohmann/json.hpp>

namespace dw {
namespace {
using json = nlohmann::json;
constexpr float DEG = kPi / 180.0f;

V3 v3(const json& a) { return {a.at(0).get<float>(), a.at(1).get<float>(), a.at(2).get<float>()}; }

// The real size (m: across, deep, high) of each Poly Haven model the sets use, from the asset ledger
// (tools/assets/manifest.json, written by tools/assets/polyhaven.py), read once.
const std::map<std::string, V3>& ledger_sizes() {
    static const std::map<std::string, V3> sizes = [] {
        std::map<std::string, V3> m;
        std::ifstream f(repo_root() + "/tools/assets/manifest.json");
        if (!f) return m;
        try {
            const json d = json::parse(f);
            for (const auto& [id, a] : d.value("assets", json::object()).items())
                if (a.contains("dimensions_mm") && a["dimensions_mm"].size() == 3)
                    m[id] = {a["dimensions_mm"][0].get<float>() / 1000, a["dimensions_mm"][1].get<float>() / 1000,
                             a["dimensions_mm"][2].get<float>() / 1000};
        } catch (const std::exception&) {}
        return m;
    }();
    return sizes;
}
Rect2 rect(const json& lo, const json& hi) { return {lo[0].get<float>(), lo[1].get<float>(), hi[0].get<float>(), hi[1].get<float>()}; }
}  // namespace

std::string repo_root() {
    if (const char* e = std::getenv("DW_ROOT"); e && *e) return e;   // (a test tree elsewhere: rooms, plates, audio)
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
    r.footsteps = d.value("footsteps", r.footsteps);
    r.ambience = d.value("ambience", r.ambience);
    r.bounds = rect(d["bounds"]["min"], d["bounds"]["max"]);
    r.height = d["height"];
    for (const auto& s : d["shots"])
        r.shots.push_back({s["id"], v3(s["pos"]), v3(s["look_at"]), s["fov"], rect(s["zone"]["min"], s["zone"]["max"]), s.value("priority", 0)});
    if (d.contains("origin")) {
        r.origin_x = d["origin"][0].get<float>();
        r.origin_z = d["origin"][1].get<float>();
        r.has_origin = true;
    }
    const json walls = d.value("walls", json::object());   // (kept: items() must not outlive what it walks)
    for (const auto& [side, w] : walls.items())
        for (const auto& o : w.value("openings", json::array()))
            r.openings.push_back({side, o.value("kind", "door"), o.value("hinge", "left"), o.value("center", 0.0f), o.value("width", 1.0f),
                                  o.value("height", 2.0f), o.value("sill", 0.0f), o.value("style", "")});
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
    // A street's lamps (the set builder plants the lamp posts; the game lights him by them).
    const json outdoor = d.value("outdoor", json::object());
    r.rain = d.contains("outdoor") && outdoor.value("rain", true);
    for (const auto& l : outdoor.value("lamps", json::array())) {
        Light L;
        L.kind = "point";
        L.pos = {l[0].get<float>(), LAMP_HEAD, l[1].get<float>()};
        L.color = {1.0f, 0.66f, 0.36f};
        L.energy = outdoor.value("lamp_energy", 1.1f);
        L.range = 11.0f;
        r.lights.push_back(L);
    }
    for (const auto& f : d.value("fx", json::array())) {
        Fx F;
        F.kind = f.value("kind", "");
        if (f.contains("pos")) F.pos = v3(f["pos"]);
        if (f.contains("color")) F.color = v3(f["color"]);
        F.size = f.value("size", 1.0f);
        F.radius = f.value("radius", 5.0f);
        F.amount = f.value("amount", 0.4f);
        F.rate = f.value("rate", 2.0f);
        F.every = f.value("every", 2.5f);
        F.seed = f.value("seed", 0);
        r.fx.push_back(F);
    }
    for (const auto& b : d.value("dead", json::array())) {
        DeadSpawn D;
        if (b.contains("pos")) D.pos = v3(b["pos"]);
        D.yaw = b.value("yaw", 0.0f) * DEG;
        D.variant = b.value("variant", 0);
        D.prone = b.value("prone", false);
        D.sitting = b.value("sitting", false);
        D.blood = b.value("blood", 0.55f);
        r.dead.push_back(D);
    }
    for (const auto& e : d.value("enemies", json::array()))
        r.enemies.push_back({e["id"], e.value("kind", "verdronkene"), e.value("requires_flag", ""), v3(e["pos"]),
                             e.value("yaw", 0.0f) * DEG, e.value("emerge", false), e.value("lying", false)});
    for (const auto& i : d.value("interactables", json::array())) {
        Interactable I;
        I.id = i.value("id", "");
        I.kind = i.value("kind", "");
        if (i.contains("pos")) I.pos = v3(i["pos"]);
        I.radius = i.value("radius", 1.0f);
        I.count = i.value("count", 1);
        for (auto [field, key] : {std::pair{&I.item, "item"}, {&I.title, "title"}, {&I.text, "text"}, {&I.target_room, "target_room"},
                                  {&I.target_spawn, "target_spawn"}, {&I.lock, "lock"}, {&I.locked_text, "locked_text"},
                                  {&I.unlock_text, "unlock_text"}, {&I.sets_flag, "sets_flag"}, {&I.then_text, "then_text"}})
            *field = i.value(key, "");
        if (i.contains("peek")) {
            const auto& p = i["peek"];
            I.peek = {"peek_" + I.id, v3(p["pos"]), v3(p["look_at"]), p.value("fov", 50.0f), {}, 0};
        }
        r.interactables.push_back(I);
    }
    r.floor = d.value("storey", 0);
    // The walls, as slabs just outside the bounds, broken where a door stands in them (a doorway
    // with its leaf open can be walked through; the leaf itself is a collider of its own).
    const Rect2& b = r.bounds;
    const float t = WALL_T;
    for (const char* side : {"north", "south", "west", "east"}) {
        const bool along_x = std::string(side) == "north" || std::string(side) == "south";
        const float lo = (along_x ? b.x0 : b.z0) - t, hi = (along_x ? b.x1 : b.z1) + t;
        std::vector<std::pair<float, float>> gaps;
        for (const auto& o : r.openings)
            if (o.side == side && (o.kind == "door" || o.kind == "passage")) {
                const float base = along_x ? b.x0 : b.z0;
                gaps.push_back({base + o.center - o.width / 2, base + o.center + o.width / 2});
            }
        std::sort(gaps.begin(), gaps.end());
        float at = lo;
        auto slab = [&](float u0, float u1) {
            if (u1 - u0 < 1e-3f) return;
            const float mid = (u0 + u1) / 2, half = (u1 - u0) / 2;
            if (std::string(side) == "north") r.colliders.push_back({mid, b.z0 - t / 2, half, t / 2, 0});
            else if (std::string(side) == "south") r.colliders.push_back({mid, b.z1 + t / 2, half, t / 2, 0});
            else if (std::string(side) == "west") r.colliders.push_back({b.x0 - t / 2, mid, t / 2, half, 0});
            else r.colliders.push_back({b.x1 + t / 2, mid, t / 2, half, 0});
        };
        for (const auto& [g0, g1] : gaps) { slab(at, g0); at = std::max(at, g1); }
        slab(at, hi);
    }
    r.wall_count = r.colliders.size();
    for (const auto& p : d.value("props", json::array())) {
        Obb2 c{};
        if (!solid_footprint(p, ledger_sizes(), c)) continue;
        // Something the set builder didn't make solid never shuts him (or one of them) out of where
        // he comes in or they stand.
        const bool inferred = !(p.value("collide", true) && p.contains("size"));
        bool in_way = false;
        for (const auto& [k, s] : r.spawns) { float x = s.pos.x, z = s.pos.z; in_way = in_way || resolve_circle_obb(x, z, 0.4f, c); }
        for (const auto& e : r.enemies) { float x = e.pos.x, z = e.pos.z; in_way = in_way || resolve_circle_obb(x, z, 0.4f, c); }
        if (inferred && in_way) continue;
        r.colliders.push_back(c);
    }
    return r;
}

// Whether a prop stands in his way, and its footprint. A prop with a "size" that says it collides
// does, as the set builder meant. Beyond those, what the set builder left without a footprint or
// marked to let him through, but a person can't walk through: anything standing on the floor
// knee-high or more and a hand or more across (a bin, a box, a crate, a bag of rubbish, a table, a
// road block, knocked over or not: a model's size comes from the ledger, or its "fit"), and street
// railings, windbreaks, a floodlight's base and bicycles still standing. Left to step over or
// through: what lies flat (a fallen bike, spilled luggage, a body bag), what's small or soft
// (bottles, cans, branches, bags of rubbish), what hangs off a wall or stands on a table, what you
// walk into (a stall, an aid tent), and a crowd barrier the set builder opened (a gate).
bool solid_footprint(const nlohmann::json& p, const std::map<std::string, V3>& sizes, Obb2& out) {
    if (!p.contains("pos")) return false;
    const std::string type = p.value("type", "");
    const V3 pos = v3(p["pos"]);
    const float yaw = p.value("yaw", 0.0f) * DEG;
    const bool says_solid = p.value("collide", true) && p.contains("size");
    if (says_solid && type != "model") {
        const V3 sz = v3(p["size"]);
        out = {pos.x, pos.z, sz.x / 2, sz.z / 2, yaw};
        return true;
    }
    if (pos.y > 0.3f) return false;                                    // up on something, or on a wall
    const float roll = std::fabs(p.value("roll", 0.0f));
    const bool lying = roll > 45.0f;
    if (type == "railing" || type == "windbreak" || type == "light_tower" || (type == "bike" && !lying)) {
        if (!p.contains("size")) return false;
        const V3 sz = v3(p["size"]);
        out = {pos.x, pos.z, sz.x / 2, std::max(sz.z / 2, 0.12f), yaw};   // (a railing is a few centimetres: no slipping between frames)
        return true;
    }
    if (type != "model") return false;
    // A model: its size as placed (a "size" or "fit" says it outright; else the ledger's, scaled).
    V3 sz{};
    if (p.contains("size")) sz = v3(p["size"]);
    else if (p.contains("fit")) sz = v3(p["fit"]);
    else {
        const std::string model = p.value("model", "");
        for (const char* soft : {"branches", "bark", "debris", "trashbag", "boots", "rat", "leaves"})   // (brushed aside, or underfoot)
            if (model.find(soft) != std::string::npos) return false;
        const float k = p.value("scale", 1.0f);
        if (model.rfind("sf:bin_", 0) == 0) sz = {0.58f * k, 1.07f * k, 0.73f * k};   // a wheelie bin (tools/blender/licensed.py: REAL)
        else if (model.rfind("ph:", 0) == 0) {
            const auto it = sizes.find(model.substr(3));
            if (it == sizes.end()) return false;
            sz = {it->second.x * k, it->second.z * k, it->second.y * k};   // (the ledger's: across, deep, high)
        } else {
            return false;
        }
    }
    float w = sz.x, h = sz.y, dpt = sz.z;                             // across, high, deep
    if (std::fabs(p.value("tip", 0.0f)) > 45.0f) std::swap(h, dpt);   // knocked over: what was its height lies along the floor
    if (h < 0.3f || std::min(w, dpt) < 0.2f || w * dpt < 0.06f) return false;
    out = {pos.x, pos.z, w / 2, dpt / 2, yaw};
    return true;
}

void RoomSpec::translate(float dx, float dz) {
    auto mv = [&](V3& v) { v.x += dx; v.z += dz; };
    auto mr = [&](Rect2& q) { q.x0 += dx; q.x1 += dx; q.z0 += dz; q.z1 += dz; };
    mr(bounds);
    for (auto& s : shots) { mv(s.pos); mv(s.look_at); mr(s.zone); }
    for (auto& [k, s] : spawns) mv(s.pos);
    for (auto& l : lights) { mv(l.pos); mv(l.look_at); }
    for (auto& f : fx) mv(f.pos);
    for (auto& b : dead) mv(b.pos);
    for (auto& e : enemies) mv(e.pos);
    for (auto& i : interactables) { mv(i.pos); mv(i.peek.pos); mv(i.peek.look_at); }
    for (auto& c : colliders) { c.cx += dx; c.cz += dz; }
}

void RoomSpec::opening_ends(const Opening& o, float& ax, float& az, float& bx, float& bz) const {
    const float t = WALL_T / 2, h = o.width / 2;
    if (o.side == "north" || o.side == "south") {
        const float z = o.side == "north" ? bounds.z0 - t : bounds.z1 + t;
        ax = bounds.x0 + o.center - h; bx = bounds.x0 + o.center + h; az = bz = z;
    } else {
        const float x = o.side == "west" ? bounds.x0 - t : bounds.x1 + t;
        az = bounds.z0 + o.center - h; bz = bounds.z0 + o.center + h; ax = bx = x;
    }
}

std::vector<ShotZone> RoomSpec::zones() const {
    std::vector<ShotZone> z;
    for (const auto& s : shots) z.push_back({s.id, s.zone, s.priority});
    return z;
}

}  // namespace dw
