// damned_waters/engine/src/game_walk.cpp
// Purpose: the walk-through (--walkthrough REPORT), a tool and a test: it holds the stick through
// every doorway, passage and staircase of the game, both ways, walking and running, and writes where
// he came out. OK: on into the next room the way he was pushed. BOUNCED: back where he came from.
// STUCK: never through, or no headway past it. JITTER: the picture cut to and fro (more than four
// cuts on one way through). A held stick must never turn him round at a cut.
// Also noted (not a failure): FLIP, where letting go and pushing the same way again on the new
// camera walks him back (the cameras either side face each other).
// ELI5: a crash-test dummy walked through every door of the building with its foot on the gas.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>

#include "game.hpp"

namespace dw {

namespace {
constexpr float DT = 1.0f / 60;

// The stick that walks him along (wx, wz) on this camera.
Vector2 stick_for(const Camera3D& cam, float wx, float wz, float tilt) {
    Vector3 f = Vector3Subtract(cam.target, cam.position);
    f.y = 0;
    f = Vector3Normalize(f);
    const float l = std::hypot(wx, wz);
    return {(wx * -f.z + wz * f.x) / l * tilt, (wx * f.x + wz * f.z) / l * tilt};
}

float angle_deg(float ax, float az, float bx, float bz) {
    const float la = std::hypot(ax, az), lb = std::hypot(bx, bz);
    if (la < 1e-4f || lb < 1e-4f) return 0;
    return std::acos(std::clamp((ax * bx + az * bz) / (la * lb), -1.0f, 1.0f)) * RAD2DEG;
}
}  // namespace

int Game::walkthrough(const std::string& report) {
    std::ofstream out(report);
    title_ = paused_ = false;
    end_t_ = -1;
    banner_t_ = 0;
    text_queue_.clear();
    reset_fight();
    int fails = 0, flips = 0, trials = 0;

    // The doors as the game starts them (shut, unlocked), nobody about: the test is the camera's
    // directions, not the locks or a fight. The doorway under test stands open away from him.
    int open_door = -1, open_side = 1;
    auto ready = [&](int room) {
        if (rooms_[size_t(room)].floor != storey_) build_storey(rooms_[size_t(room)].floor);
        shut_doors();
        for (size_t i = 0; i < leaves_.size(); ++i) {
            if (doorways_[i].live) leaves_[i].locked = false;
            if (int(i) == open_door && !doorways_[i].passage) leaves_[i].angle = leaves_[i].target = float(open_side) * doors::OPEN;
        }
        for (auto& e : enemies_) e.active = false;
        wake_t_ = -1;
        text_queue_.clear();
        status_.close();
        beat_ = {};
    };
    // He stands at (x, z) in `from`, the stick held toward (dx, dz); `to` is where that leads.
    // steer: a quarter second after the cut, the thumb corrects by 40 degrees (lining up with
    // what's ahead), as players do; he must still go on, not turn back.
    auto trial = [&](const char* what, int from, float x, float z, float dx, float dz, float tilt, int to, bool stairs,
                     const Interactable* door, bool steer, const Interactable* press) {
        ready(from);
        player_ = {x, z, yaw_towards(0, 0, dx, dz)};
        vel_ = {};
        frame_ = {};
        set_pmode(PMode::Normal);
        enter_room(from);
        hero_.settle();
        const std::string shot0 = rooms_[size_t(from)].id + "/" + shot_;
        const Vector3 f0 = Vector3Subtract(cam_.target, cam_.position);
        const Vector2 stick = stick_for(cam_, dx, dz, tilt);
        if (door) { staged_in_ = stick; update(DT); start_beat(door->target_room, door->target_spawn); }
        bool crossed = false, bounced = false;
        float ax = 0, az = 0, adx = dx, adz = dz;   // where he came into `to`, and the way on from there
        std::string shot1;
        Vector3 f1{};
        int after = 0;
        const float c40 = std::cos(40 * DEG2RAD), s40 = std::sin(40 * DEG2RAD);
        const Vector2 steered{stick.x * c40 - stick.y * s40, stick.x * s40 + stick.y * c40};
        bool pressed = false;
        int cuts = 0;   // the picture cutting (room or shot): more than a few on one way through is it cutting to and fro
        std::string was = rooms_[size_t(room_)].id + "/" + shot_;
        for (int f = 0; f < 60 * 8 && after < 60 * 2; ++f) {
            staged_in_ = steer && after > 15 ? steered : stick;
            if (!crossed && !pressed && f == 60 * 3 && press) {   // not through by now: a door that wants Cross
                pressed = true;
                use_door(from, *press);
                text_queue_.clear();
            }
            update(DT);
            for (auto& e : enemies_) e.active = false;   // (the far side of the stairs has its own)
            if (beat_.busy()) continue;
            if (!crossed && room_ == to) {
                crossed = true;
                ax = player_.x;
                az = player_.z;
                if (stairs) { const V2 fw = forward_from_yaw(player_.yaw); adx = fw.x; adz = fw.z; }
                shot1 = rooms_[size_t(to)].id + "/" + shot_;
                f1 = Vector3Subtract(cam_.target, cam_.position);
            }
            if (crossed) ++after;
            if (std::getenv("DW_WALK_TRACE") && rooms_[size_t(from)].id == std::getenv("DW_WALK_TRACE") && f % 6 == 0)
                TraceLog(LOG_INFO, "TRACE %s f%d room %s at %.2f,%.2f vel %.2f,%.2f frame %.2f,%.2f hold %d stick %.2f,%.2f beat %d",
                         what, f, rooms_[size_t(room_)].id.c_str(), player_.x - rooms_[size_t(room_)].bounds.x0, player_.z - rooms_[size_t(room_)].bounds.z0,
                         vel_.x, vel_.y, frame_fwd_.x, frame_fwd_.y, int(frame_.holding), staged_in_.x, staged_in_.y, int(beat_.busy()));
            if (crossed && room_ == from) bounced = true;
            const std::string now = rooms_[size_t(room_)].id + "/" + shot_;
            cuts += now != was;
            was = now;
        }
        const float progress = crossed ? ((player_.x - ax) * adx + (player_.z - az) * adz) / std::hypot(adx, adz) : 0;
        const float heading = angle_deg(vel_.x, vel_.y, adx, adz) - (steer ? 40.0f : 0.0f);
        // Let go, then push the same way again: the new camera's directions now.
        float repress = 0;
        if (crossed && !bounced) {
            for (int f = 0; f < 15; ++f) { staged_in_ = {}; update(DT); }
            const float bx = player_.x, bz = player_.z;
            for (int f = 0; f < 30; ++f) { staged_in_ = steer ? steered : stick; update(DT); }
            repress = angle_deg(player_.x - bx, player_.z - bz, adx, adz);
        }
        staged_in_ = {};
        const char* verdict = bounced ? "BOUNCED" : !crossed || progress < (steer ? 0.75f : 1.0f) || heading > 100 ? "STUCK" : cuts > 4 ? "JITTER" : "OK";
        const bool flip = crossed && !bounced && repress > (steer ? 160.0f : 120.0f);
        ++trials;
        fails += std::string(verdict) != "OK";
        flips += flip;
        char line[640];
        const RoomSpec& at = rooms_[size_t(room_ >= 0 ? room_ : from)];
        std::snprintf(line, sizeof line, "%-7s %-4s %-22s -> %-22s %-5s progress %5.1f m heading %5.1f  cams %-26s -> %-26s turn %5.1f  repress %5.1f cuts %d%s  [from %.2f,%.2f; ends in %s at %.2f,%.2f]",
                      verdict, flip ? "FLIP" : "", rooms_[size_t(from)].id.c_str(), rooms_[size_t(to)].id.c_str(), what, progress, heading,
                      shot0.c_str(), shot1.c_str(), crossed ? angle_deg(f0.x, f0.z, f1.x, f1.z) : 0.0f, repress, cuts, stairs ? "  (stairs)" : "",
                      x - rooms_[size_t(from)].bounds.x0, z - rooms_[size_t(from)].bounds.z0, at.id.c_str(), player_.x - at.bounds.x0, player_.z - at.bounds.z0);
        out << line << "\n";
    };
    auto both_gaits = [&](int from, float x, float z, float dx, float dz, int to, bool stairs, const Interactable* door,
                          const Interactable* press = nullptr) {
        trial("walk", from, x, z, dx, dz, 0.6f, to, stairs, door, false, press);
        trial("run", from, x, z, dx, dz, 1.0f, to, stairs, door, false, press);
        trial("steer", from, x, z, dx, dz, 0.6f, to, stairs, door, true, press);
    };
    // A start this far back from the doorway (ends a, b), in `room` (nearer if that's outside it),
    // on a line through it that nothing stands across (a street's middle may have a kiosk in it).
    auto start = [&](int room, float ax, float az, float bx, float bz, float dx, float dz, float& x, float& z) {
        ready(room);
        constexpr float R = 0.3f;
        for (float t : {0.5f, 0.38f, 0.62f, 0.25f, 0.75f, 0.15f, 0.85f})
            for (float back : {2.2f, 1.5f, 1.0f, 0.6f}) {
                const float mx = ax + (bx - ax) * t, mz = az + (bz - az) * t;
                x = mx - dx * back;
                z = mz - dz * back;
                if (house::room_at(rooms_, rooms_[size_t(room)].floor, x, z, room) != room) continue;
                bool clear = true;
                for (float side : {-R, 0.0f, R}) {
                    const float ox = -dz * side, oz = dx * side;
                    clear = clear && house::first_cross(statics_, x + ox, z + oz, mx + dx * 2.5f + ox, mz + dz * 2.5f + oz) >= 1.0f;
                }
                if (clear) return true;
            }
        const float mx = (ax + bx) / 2, mz = (az + bz) / 2;   // nothing clear: the middle, and it'll say STUCK
        x = mx - dx * 1.0f;
        z = mz - dz * 1.0f;
        return house::room_at(rooms_, rooms_[size_t(room)].floor, x, z, room) == room;
    };

    std::vector<const Interactable*> covered;
    for (size_t i = 0; i < doorways_.size(); ++i) {
        const house::Doorway d = doorways_[i];   // (a copy: build_storey leaves the list alone, but be safe)
        if (!d.live && !d.passage) continue;
        float x, z;
        if (d.b >= 0) {   // two rooms on one storey: through it both ways
            open_door = int(i);
            open_side = 1;
            if (start(d.a, d.ax, d.az, d.bx, d.bz, d.nx, d.nz, x, z)) both_gaits(d.a, x, z, d.nx, d.nz, d.b, false, nullptr);
            open_side = -1;
            if (start(d.b, d.ax, d.az, d.bx, d.bz, -d.nx, -d.nz, x, z)) both_gaits(d.b, x, z, -d.nx, -d.nz, d.a, false, nullptr);
            open_door = -1;
            continue;
        }
        for (const auto& it : rooms_[size_t(d.a)].interactables) {   // out of the storey: through, then on from the stairs' far end
            if (it.id != d.door_a || it.target_room.empty()) continue;
            const int t = room_index(it.target_room);
            open_door = int(i);
            open_side = 1;
            if (t < 0 || !start(d.a, d.ax, d.az, d.bx, d.bz, d.nx, d.nz, x, z)) continue;
            covered.push_back(&it);
            open_door = int(i);
            open_side = 1;
            both_gaits(d.a, x, z, d.nx, d.nz, t, true, nullptr, d.live ? nullptr : &it);   // (open: walking through starts the stairs)
            open_door = -1;
        }
    }
    for (size_t r = 0; r < rooms_.size(); ++r)   // stairs and boarding with no doorway: Cross with the stick held
        for (const auto& it : rooms_[r].interactables) {
            if (it.kind != "door" || it.target_room.empty() || std::find(covered.begin(), covered.end(), &it) != covered.end()) continue;
            const int t = room_index(it.target_room);
            if (t < 0 || rooms_[size_t(t)].floor == rooms_[r].floor) continue;
            const RoomSpec& rs = rooms_[r];
            const float cx = (rs.bounds.x0 + rs.bounds.x1) / 2, cz = (rs.bounds.z0 + rs.bounds.z1) / 2;
            const float dx = it.pos.x - cx, dz = it.pos.z - cz, l = std::max(std::hypot(dx, dz), 1e-3f);
            both_gaits(int(r), it.pos.x - dx / l * 0.8f, it.pos.z - dz / l * 0.8f, dx / l, dz / l, t, true, &it);
        }
    char tail[160];
    std::snprintf(tail, sizeof tail, "%d trials, %d failed, %d flip on a re-press", trials, fails, flips);
    out << tail << "\n";
    TraceLog(LOG_INFO, "walkthrough: %s (%s)", tail, report.c_str());
    return fails;
}

// The doors (--doortest REPORT): at every door in the game he walks up to it the way players do
// (straight at it and from 35 degrees either side, from 1.5 m and 3 m back) and, the stick still
// held, presses the button (through the same input a pad's press takes). The door must answer:
// swing, say it's locked, or take him up or down the stairs. NO SPOT: the press found nothing in
// reach (something kept him off it, or he wasn't facing it); OTHER: it found something else first;
// DEAD: it found the door and nothing happened.
int Game::doortest(const std::string& report) {
    std::ofstream out(report);
    title_ = paused_ = false;
    end_t_ = -1;
    banner_t_ = 0;
    reset_fight();
    int fails = 0, n = 0;
    for (size_t r = 0; r < rooms_.size(); ++r) {
        for (size_t i = 0; i < rooms_[r].interactables.size(); ++i) {
            const Interactable it = rooms_[r].interactables[i];
            if (it.kind != "door") continue;
            for (const float back : {1.5f, 3.0f})
            for (const float turn : {0.0f, 35.0f, -35.0f}) {
                if (rooms_[r].floor != storey_) build_storey(rooms_[r].floor);
                shut_doors();
                const bool with_them = std::getenv("DW_DOOR_ENEMIES") != nullptr;   // (leave the Drowned where they are, shuffling about)
                if (!with_them) for (auto& e : enemies_) e.active = false;
                text_queue_.clear();
                status_.close();
                beat_ = {};
                // Which way the door is from its spot: the doorway's middle, else away from the room's middle.
                const int di = doorway_of(int(r), it.id);
                float fx, fz;
                if (di >= 0) { fx = doorways_[size_t(di)].mid_x() - it.pos.x; fz = doorways_[size_t(di)].mid_z() - it.pos.z; }
                else { const Rect2& b = rooms_[r].bounds; fx = it.pos.x - (b.x0 + b.x1) / 2; fz = it.pos.z - (b.z0 + b.z1) / 2; }
                float l = std::hypot(fx, fz);
                if (l < 1e-3f) { fx = 0; fz = -1; l = 1; }
                fx /= l; fz /= l;
                const float c = std::cos(turn * DEG2RAD), s = std::sin(turn * DEG2RAD);
                const float ax = fx * c - fz * s, az = fx * s + fz * c;
                float sx = it.pos.x - ax * back, sz = it.pos.z - az * back;
                if (house::room_at(rooms_, rooms_[r].floor, sx, sz, int(r)) != int(r)) continue;   // (that start is outside the room)
                bool clear = true;
                { float x = sx, z = sz; collide(x, z, 0.28f); clear = std::hypot(x - sx, z - sz) < 1e-3f; }
                if (!clear) continue;   // (that start is inside the furniture)
                player_ = {sx, sz, yaw_towards(sx, sz, it.pos.x, it.pos.z)};
                vel_ = {};
                frame_ = {};
                set_pmode(PMode::Normal);
                enter_room(int(r));
                hero_.settle();
                // Walk at the spot, then on at the door itself, until he's at it or something stops him.
                float best = 1e9f;
                int still = 0;
                const float tx = it.pos.x + fx * 0.6f, tz = it.pos.z + fz * 0.6f;
                for (int f = 0; f < 60 * 5; ++f) {
                    const bool near = std::hypot(it.pos.x - player_.x, it.pos.z - player_.z) < 0.35f;
                    const float dx = (near ? tx : it.pos.x) - player_.x, dz = (near ? tz : it.pos.z) - player_.z, d = std::hypot(it.pos.x - player_.x, it.pos.z - player_.z);
                    if (d < best - 0.01f) { best = d; still = 0; } else if (++still > 20) break;
                    staged_in_ = stick_for(cam_, dx, dz, 1.0f);
                    update(DT);
                    if (std::getenv("DW_DOOR_TRACE") && it.id == std::getenv("DW_DOOR_TRACE") && f % 4 == 0)
                        TraceLog(LOG_INFO, "DOOR f%d %s/%s at %.2f,%.2f yaw %.0f vel %.2f,%.2f stick %.2f,%.2f pmode %d", f, rooms_[size_t(room_)].id.c_str(),
                                 shot_.c_str(), player_.x, player_.z, player_.yaw * RAD2DEG, vel_.x, vel_.y, staged_in_.x, staged_in_.y, int(pmode_));
                    if (beat_.busy() || (di >= 0 && leaves_[size_t(di)].target != 0)) break;   // (walking into it opened it)
                }
                const float leaf0 = di >= 0 ? leaves_[size_t(di)].target : 0;
                const bool by_walking = leaf0 != 0 || beat_.busy();
                const auto [sr, ss] = spot_in_reach();
                staged_hit_ = ACT_INTERACT;
                update(DT);
                for (int f = 0; f < 5; ++f) update(DT);
                staged_in_ = {};
                const bool answered = by_walking || beat_.busy() || !text_queue_.empty() || (di >= 0 && leaves_[size_t(di)].target != leaf0);
                // Opened: then on through it, the stick held at the far side, as a player does.
                bool through = true;
                std::string stuck_at;
                if (answered && di >= 0 && !beat_.busy() && !leaves_[size_t(di)].locked && text_queue_.empty()) {
                    const auto& dw = doorways_[size_t(di)];
                    const int far = dw.a == int(r) ? dw.b : dw.a;
                    const float sgn = dw.a == int(r) ? 1.0f : -1.0f;
                    const float gx = dw.mid_x() + dw.nx * sgn * 1.5f, gz = dw.mid_z() + dw.nz * sgn * 1.5f;
                    const bool keys = std::getenv("DW_DOOR_KEYS") != nullptr;
                    Vector2 held{};
                    int gap = 0;
                    for (int f = 0; f < 60 * 3 && room_ != far; ++f) {
                        if (f < 50) { staged_in_ = {}; update(DT); continue; }   // (it swings open)
                        const bool before = std::hypot(dw.mid_x() - player_.x, dw.mid_z() - player_.z) > 0.3f &&
                                            ((player_.x - dw.mid_x()) * dw.nx + (player_.z - dw.mid_z()) * dw.nz) * sgn < 0;
                        const float aimx = before ? dw.mid_x() : gx, aimz = before ? dw.mid_z() : gz;
                        Vector2 want = stick_for(cam_, aimx - player_.x, aimz - player_.z, 1.0f);
                        if (keys) {   // a keyboard: the nearest of eight directions, and a beat with no key down to change key
                            const float a = std::round(std::atan2(want.y, want.x) / (kPi / 4)) * (kPi / 4);
                            want = {std::round(std::cos(a)), std::round(std::sin(a))};
                            if (gap > 0) { --gap; want = {}; }
                            else if (held.x != want.x || held.y != want.y) { if (held.x != 0 || held.y != 0) { gap = 6; held = {}; want = {}; } else held = want; }
                        }
                        staged_in_ = want;
                        update(DT);
                    }
                    staged_in_ = {};
                    through = far < 0 || room_ == far;
                    if (!through) {
                        char b[120];
                        std::snprintf(b, sizeof b, " STUCK at %.2f,%.2f in %s, leaf %.2f", player_.x, player_.z, rooms_[size_t(room_)].id.c_str(),
                                      leaves_[size_t(di)].angle);
                        stuck_at = b;
                        for (const auto& e : enemies_)
                            if (e.active && std::hypot(e.a.x - player_.x, e.a.z - player_.z) < 1.5f) {
                                std::snprintf(b, sizeof b, "; %s %.2f m away, state %d, wanders %d", e.id.c_str(),
                                              std::hypot(e.a.x - player_.x, e.a.z - player_.z), int(e.brain.state), int(e.wanders));
                                stuck_at += b;
                            }
                    }
                }
                const char* verdict = !answered ? (sr < 0 ? "NO SPOT" : (sr != int(r) || ss != int(i)) ? "OTHER" : "DEAD") : through ? "OK" : "NO WAY";
                const bool ok = answered && through;
                fails += !ok;
                ++n;
                char line[360];
                std::snprintf(line, sizeof line, "%-8s %-22s %-18s from %.1f m at %+3.0f deg: got to %.2f m of it, facing it by %.0f deg%s",
                              verdict, rooms_[r].id.c_str(), it.id.c_str(), back, turn,
                              std::hypot(it.pos.x - player_.x, it.pos.z - player_.z),
                              std::fabs(wrap_pi(yaw_towards(player_.x, player_.z, it.pos.x, it.pos.z) - player_.yaw)) * RAD2DEG,
                              by_walking ? " (opened walking into it)" : "");
                out << line << stuck_at;
                if (sr >= 0 && !ok) out << "  (found " << rooms_[size_t(sr)].id << "/" << rooms_[size_t(sr)].interactables[size_t(ss)].id << ")";
                out << "\n";
                text_queue_.clear();
                status_.close();
                beat_ = {};
            }
        }
    }
    out << n << " tries, " << fails << " failed\n";
    std::printf("%d tries, %d failed\n", n, fails);
    return fails;
}

}  // namespace dw
