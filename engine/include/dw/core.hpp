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

// ── Enemy brain: IDLE -> ALERT -> PURSUIT -> ATTACK -> RECOVERY (+STAGGER, DEAD) ──
enum class EState { Idle, Alert, Pursuit, Attack, Recovery, Stagger, Dead };
enum class EEvent { None, Alerted, Pursue, Windup, Strike, Calmed };

struct EnemyBrain {
    float hp = 6, alert_time = 0.7f, attack_range = 1.25f, windup = 0.85f, strike_window = 0.25f;
    float recovery = 1.1f, stagger_time = 0.4f, give_up = 6.0f;
    EState state = EState::Idle;
    float t = 0, lost = 0;
    bool struck = false;

    void go(EState s) { state = s; t = 0; if (s == EState::Attack) struck = false; }
    // Returns at most one event per tick (the game reacts to it).
    EEvent update(float dt, bool sees, bool heard, float dist) {
        t += dt;
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
                if (t >= recovery) { go(EState::Pursuit); return EEvent::Pursue; }
                break;
            case EState::Stagger:
                if (t >= stagger_time) { go(EState::Pursuit); return EEvent::Pursue; }
                break;
            case EState::Dead: break;
        }
        return EEvent::None;
    }
};

}  // namespace dw
#endif
