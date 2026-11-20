// damned_waters/engine/src/game_shoot.cpp
// Purpose: the shooting range (--shoottest REPORT), a tool and a test: a Drowned is stood at many
// distances and bearings round him in an open street, he raises the gun and fires the way players
// do (at once, or after a moment's aim; at the chest, the head, the legs), and it writes how many
// shots hit. A shot aimed at a Drowned he can see in front of him must hit it, every time (the
// play-test's "shots aimed directly at enemies do not register": 38 percent hit before the fix).
// ELI5: a coach at a firing range, ticking off every round that lands on the target.
#include <cmath>
#include <cstdio>
#include <fstream>

#include "game.hpp"

namespace dw {

int Game::shoottest(const std::string& report, const std::string& room_id) {
    std::ofstream out(report);
    constexpr float DT = 1.0f / 60;
    title_ = paused_ = false;
    end_t_ = -1;
    banner_t_ = 0;
    text_queue_.clear();
    reset_fight();
    const int r = room_index(room_id);
    if (r < 0) { out << "no room " << room_id << "\n"; return 1; }
    beat_room_ = room_id;
    beat_spawn_ = "";
    finish_beat();
    const RoomSpec& rs = rooms_[size_t(room_)];
    // An open spot: the middle of the room's widest clear space near its middle.
    const float cx = (rs.bounds.x0 + rs.bounds.x1) / 2, cz = (rs.bounds.z0 + rs.bounds.z1) / 2;
    int shots = 0, hits = 0, tried = 0;
    for (float dist : {2.0f, 4.0f, 7.0f, 11.0f, 16.0f, 22.0f})
        for (float bearing : {0.0f, 25.0f, -50.0f, 90.0f, 160.0f})
            for (float delay : {0.0f, 0.12f, 0.35f})
                for (int look : {0, 1, -1}) {   // chest, head (W / stick up), legs
                    // Find a place where he and the Drowned both stand clear, in the room, with a clear line.
                    bool placed = false;
                    float px = 0, pz = 0, ex = 0, ez = 0, yaw = 0;
                    for (int k = 0; k < 40 && !placed; ++k) {
                        const float a = float(k) * 2.39996f, rr = 0.6f * float(k);
                        px = cx + std::cos(a) * rr;
                        pz = cz + std::sin(a) * rr;
                        yaw = float(k) * 0.7f;
                        const V2 f = forward_from_yaw(yaw + bearing * DEG2RAD);
                        ex = px + f.x * dist;
                        ez = pz + f.z * dist;
                        if (house::room_at(rooms_, storey_, px, pz, room_) != room_ || house::room_at(rooms_, storey_, ex, ez, room_) != room_) continue;
                        if (!sight_clear(px, pz, ex, ez) || house::first_cross(statics_, px, pz, ex, ez) < 1.0f) continue;
                        float tx = px, tz = pz, ux = ex, uz = ez;
                        bool clear = true;
                        for (const auto& b : statics_) clear = clear && !resolve_circle_obb(tx, tz, 0.35f, b) && !resolve_circle_obb(ux, uz, 0.4f, b);
                        placed = clear;
                    }
                    if (!placed) continue;
                    ++tried;
                    for (auto& e : enemies_) e.active = false;
                    Enemy& e = enemies_.front();
                    e.active = true;
                    e.a = {ex, ez, yaw_towards(ex, ez, px, pz)};
                    e.brain.go(EState::Idle);
                    e.brain.hp = 1000;   // (it must stand there for every shot)
                    e.rise = -1;
                    e.damage = {};
                    player_ = {px, pz, yaw};
                    vel_ = {};
                    frame_ = {};
                    aim_target_ = -1;
                    set_pmode(PMode::Normal);
                    for (auto& g : guns_) { g.mag = g.spec().mag; g.cooldown = 0; }
                    hero_.settle();
                    for (int f = 0; f < 10; ++f) { staged_in_ = {}; update(DT); }
                    // Raise the gun, the head or legs held as asked, then fire.
                    staged_aim_ = true;
                    staged_in_ = {0, float(look)};
                    const int h0 = stats_.hits, s0 = stats_.shots;
                    for (float t = 0; t <= delay; t += DT) update(DT);
                    fire_wait_ = 0.5f;   // (as a pull of the trigger does: game_combat.cpp, aim)
                    for (int f = 0; f < 45; ++f) update(DT);
                    staged_aim_ = false;
                    staged_in_ = {};
                    const int got = stats_.hits - h0, fired = stats_.shots - s0;
                    // One behind him isn't aimed at: the gun locks onto what's in front (a quick turn
                    // first), as in the games it follows. Listed, not counted.
                    const bool behind = std::fabs(bearing) > verbs::AIM_CONE_DEG;
                    if (!behind) { shots += fired; hits += got; }
                    char line[200];
                    std::snprintf(line, sizeof line, "%-6s dist %5.1f bearing %6.1f delay %.2f aim %-5s fired %d hit %d",
                                  behind ? "BEHIND" : got > 0 ? "HIT" : "MISS", dist,
                                  bearing, delay, look == 0 ? "chest" : look > 0 ? "head" : "legs", fired, got);
                    out << line << "\n";
                    e.active = false;
                }
    char tail[160];
    std::snprintf(tail, sizeof tail, "%s: %d setups, %d shots, %d hit (%.0f%%)", rs.id.c_str(), tried, shots, hits, shots > 0 ? 100.0f * float(hits) / float(shots) : 0.0f);
    out << tail << "\n";
    TraceLog(LOG_INFO, "shoottest: %s", tail);
    return shots - hits;
}

}  // namespace dw
