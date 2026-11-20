// damned_waters/engine/include/dw/core.hpp
// Purpose: pure game logic with no rendering: depth codec, camera shot
// selection, movement maths, 2D collision, the enemy brain. Header-only and
// allocation-free, so it is trivially unit-testable and costs nothing per frame.
// Axes: Y up, character forward = -Z at yaw 0 (same as the RoomSpec data).
#ifndef DW_CORE_HPP
#define DW_CORE_HPP
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

namespace dw {

constexpr float kPi = 3.14159265358979f;  // (raylib defines a PI macro)

// ── Depth codec: 16-bit planar depth split across R (hi) and G (lo) bytes ──────
namespace depth {
constexpr float MAX_M = 32.0f;
inline void encode(float metres, int& hi, int& lo) {
    int v = std::clamp(static_cast<int>(std::lround(metres / MAX_M * 65535.0f)), 0, 65535);
    hi = v >> 8;
    lo = v & 0xFF;
}
inline float decode(int hi, int lo) { return float(hi * 256 + lo) / 65535.0f * MAX_M; }
}  // namespace depth

// ── Camera shots ───────────────────────────────────────────────────────────────
struct Rect2 {  // XZ rectangle, inclusive edges
    float x0, z0, x1, z1;
    bool has(float x, float z) const { return x >= x0 && x <= x1 && z >= z0 && z <= z1; }
};
struct ShotZone { std::string id; Rect2 zone; int priority = 0; };

// Stay on the current shot while inside its zone (hysteresis at thresholds);
// otherwise the highest-priority zone containing the player; else keep current.
inline std::string select_shot(const std::vector<ShotZone>& shots, const std::string& current, float x, float z) {
    for (const auto& s : shots)
        if (s.id == current && s.zone.has(x, z)) return current;
    const ShotZone* best = nullptr;
    for (const auto& s : shots)
        if (s.zone.has(x, z) && (!best || s.priority > best->priority)) best = &s;
    if (best) return best->id;
    if (current.empty() && !shots.empty()) return shots.front().id;
    return current;
}

// ── Movement ───────────────────────────────────────────────────────────────────
struct V2 { float x, z; };
inline V2 forward_from_yaw(float yaw) { return {-std::sin(yaw), -std::cos(yaw)}; }
inline float yaw_towards(float fx, float fz, float tx, float tz) { return std::atan2(-(tx - fx), -(tz - fz)); }
inline float wrap_pi(float a) {
    while (a > kPi) a -= 2 * kPi;
    while (a < -kPi) a += 2 * kPi;
    return a;
}
inline float step_yaw(float cur, float target, float max_step) {
    return cur + std::clamp(wrap_pi(target - cur), -max_step, max_step);
}
inline float smoothing(float sharpness, float dt) { return 1.0f - std::exp(-sharpness * dt); }

// ── 2D collision: circles against yawed boxes on the floor plane ───────────────
struct Obb2 { float cx, cz, hx, hz, yaw; };

// Push a circle out of a box; returns true if it moved.
inline bool resolve_circle_obb(float& x, float& z, float r, const Obb2& b) {
    float c = std::cos(b.yaw), s = std::sin(b.yaw);
    float dx = x - b.cx, dz = z - b.cz;
    float lx = dx * c - dz * s, lz = dx * s + dz * c;   // into box space
    float px = std::clamp(lx, -b.hx, b.hx), pz = std::clamp(lz, -b.hz, b.hz);
    float ox = lx - px, oz = lz - pz;
    float d2 = ox * ox + oz * oz;
    if (d2 >= r * r) return false;
    if (d2 > 1e-10f) {
        float d = std::sqrt(d2), k = (r - d) / d;
        lx += ox * k;
        lz += oz * k;
    } else {  // centre inside: exit through the nearest face
        float ex = b.hx - std::fabs(lx), ez = b.hz - std::fabs(lz);
        if (ex < ez) lx = (lx < 0 ? -1.0f : 1.0f) * (b.hx + r); else lz = (lz < 0 ? -1.0f : 1.0f) * (b.hz + r);
    }
    x = b.cx + lx * c + lz * s;
    z = b.cz - lx * s + lz * c;
    return true;
}

// ── Enemy brain ─────────────────────────────────────────────────────────────────
//   IDLE -> ALERT -> PURSUIT -> ATTACK -> RECOVERY (-> RETREAT) -> PURSUIT
//   plus STAGGER (a hit), FLOORED (a kick or a heavy blast) and DEAD.
// A pure state machine (ported from the Godot demo's EnemyBrain): the game feeds it senses and
// hits and acts on the events it returns. Tuning comes from the fields, so a Drowned and a
// crawler share one brain with different numbers (two drivers, one car, different habits).
enum class EState { Idle, Alert, Pursuit, Attack, Recovery, Retreat, Stagger, Floored, Dead };
enum class EEvent { None, Alerted, Pursue, Windup, Strike, Calmed, GotUp };
enum class EHit { Ignored, Hurt, Staggered, Floored, Died };

struct EnemyBrain {
    float hp = 60, alert_time = 0.7f, attack_range = 1.25f, windup = 0.85f, strike_window = 0.25f;
    float recovery = 1.1f, retreat_time = 0.0f, stagger_time = 0.4f, stagger_immunity = 1.2f, floor_time = 2.4f;
    float give_up = 6.0f;
    EState state = EState::Idle;
    float t = 0, lost = 0, immune = 0;
    float hold = 0;              // a longer stagger than usual (overbalanced by a perfect dodge)
    bool struck = false;

    bool dead() const { return state == EState::Dead; }
    bool kickable() const { return state == EState::Stagger; }
    void go(EState s) { state = s; t = 0; if (s == EState::Attack) struck = false; }
    // sees: in its view and nothing in between; heard: a noise reached it. At most one event per tick.
    EEvent update(float dt, bool sees, bool heard, float dist) {
        t += dt;
        immune = std::max(0.0f, immune - dt);
        switch (state) {
            case EState::Idle:
                if (sees || heard) { go(EState::Alert); return EEvent::Alerted; }
                break;
            case EState::Alert:
                if (t >= alert_time && (sees || heard || dist < attack_range * 3)) { go(EState::Pursuit); return EEvent::Pursue; }
                if (t >= alert_time * 4) { go(EState::Idle); return EEvent::Calmed; }
                break;
            case EState::Pursuit:
                lost = sees ? 0 : lost + dt;
                if (dist <= attack_range) { go(EState::Attack); return EEvent::Windup; }
                if (lost >= give_up) { go(EState::Idle); return EEvent::Calmed; }
                break;
            case EState::Attack:
                if (!struck && t >= windup) { struck = true; return EEvent::Strike; }
                if (t >= windup + strike_window) go(EState::Recovery);
                break;
            case EState::Recovery:
                if (t >= recovery) { go(retreat_time > 0 ? EState::Retreat : EState::Pursuit); return EEvent::Pursue; }
                break;
            case EState::Retreat:
                if (t >= retreat_time) { go(EState::Pursuit); return EEvent::Pursue; }
                break;
            case EState::Stagger:
                if (t >= std::max(stagger_time, hold)) { hold = 0; go(EState::Pursuit); return EEvent::Pursue; }
                break;
            case EState::Floored:
                if (t >= floor_time) { go(EState::Pursuit); return EEvent::GotUp; }
                break;
            case EState::Dead: break;
        }
        return EEvent::None;
    }
    // A hit. power 1: a bullet; 2: a heavy hit (shotgun, kick) that staggers through the immunity
    // a fresh stagger gives. knockdown: floors it (a kick, or enough pellets in one blast).
    EHit take_hit(float damage, int power = 1, bool knockdown = false) {
        if (dead()) return EHit::Ignored;
        hp -= damage;
        if (hp <= 0) { go(EState::Dead); return EHit::Died; }
        if (knockdown && state != EState::Floored) { go(EState::Floored); return EHit::Floored; }
        if (state == EState::Floored) return EHit::Hurt;
        if (immune <= 0 || power >= 2) { immune = stagger_immunity; go(EState::Stagger); return EHit::Staggered; }
        return EHit::Hurt;
    }
    void kill() { if (!dead()) { hp = 0; go(EState::Dead); } }   // a burst head needs no arithmetic
    // Driven back by the force of the shots: reeling for `seconds`, whatever its stagger immunity
    // (it can't come on while it's being pushed back). Not when it's down or dead.
    void knock_back(float seconds) {
        if (dead() || state == EState::Floored) return;
        go(EState::Stagger);
        hold = seconds;
        immune = stagger_immunity;
    }
    // Its lunge met nothing: it stumbles on past, wide open (and kickable) for `seconds`.
    void overbalance(float seconds) { if (!dead()) { go(EState::Stagger); hold = seconds; immune = 0; } }
    // Seconds until its bite lands (-1: it isn't lunging at anything right now).
    float time_to_strike() const { return state == EState::Attack && !struck ? std::max(0.0f, windup - t) : -1.0f; }
};

// A Drowned on its own, not yet onto him: it shuffles about the place it was left, a few steps at
// a time (a point within RADIUS of home, walked to slowly, then a stand of a few seconds), the way
// RE's zombies wander a street. The game picks the points (it knows the walls) and walks it there;
// this keeps the rhythm and says where to go next. ELI5: a dog on a long lead round its post.
struct Wander {
    static constexpr float RADIUS = 3.5f;   // m from home
    static constexpr float SPEED = 0.4f;    // m/s: a shuffle
    static constexpr float ARRIVE = 0.35f;  // m: there
    float home_x = 0, home_z = 0, to_x = 0, to_z = 0;
    float pause = 0;       // s left standing still
    float stuck = 0;       // s it has made no headway (a wall, a car): give up on that point
    unsigned seed = 1;
    bool walking = false;
    float rnd() { seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return float(seed & 0xFFFF) / 65535.0f; }
    // A candidate next point: somewhere within RADIUS of home, not too near where it is.
    void propose(float x, float z, float& px, float& pz) {
        for (int k = 0; k < 4; ++k) {
            const float a = rnd() * 6.2831853f, r = RADIUS * (0.35f + 0.65f * rnd());
            px = home_x + std::cos(a) * r;
            pz = home_z + std::sin(a) * r;
            if (std::hypot(px - x, pz - z) > 1.0f) return;
        }
    }
    // Each frame, standing at (x, z), having moved `moved` metres since the last: true while it
    // should walk on toward (to_x, to_z). needs_point: it wants a new point (the game proposes one
    // with propose() and accepts it with go_to() if the way is clear).
    bool update(float dt, float x, float z, float moved, bool& needs_point) {
        needs_point = false;
        if (!walking) {
            pause -= dt;
            if (pause <= 0) needs_point = true;
            return false;
        }
        stuck = moved < SPEED * dt * 0.3f ? stuck + dt : 0.0f;
        if (std::hypot(to_x - x, to_z - z) < ARRIVE || stuck > 1.0f) {   // there (or can't get there): stand a while
            walking = false;
            stuck = 0;
            pause = 1.5f + 3.0f * rnd();
            return false;
        }
        return true;
    }
    void go_to(float px, float pz) { to_x = px; to_z = pz; walking = true; stuck = 0; }
    void rest() { pause = 1.0f + 2.0f * rnd(); }   // (a point it couldn't reach: try again in a moment)
};

// The force of the shots it has taken, as RE2 does it: each round jolts it, and two or three in
// quick succession drive it back a step, reeling. Each hit adds its force; the force drains away
// with time, so shots spread out never add up. ELI5: pushing a swing; push in rhythm and it goes
// higher, push now and then and it never gets going.
struct Impact {
    static constexpr float DRAIN = 0.6f;   // force lost a second
    static constexpr float KNOCK = 2.4f;   // force that drives it back: 3 pistol rounds at the chest in quick succession, 2 at the head
    float force = 0;
    void tick(float dt) { force = std::max(0.0f, force - DRAIN * dt); }
    // A hit of force `f` (a pistol round: 1, at the head 1.4; a shotgun pellet 0.35). True when it
    // drives it back (and the force starts again from nothing).
    bool hit(float f) {
        force += f;
        if (force < KNOCK) return false;
        force = 0;
        return true;
    }
};

}  // namespace dw
#endif
