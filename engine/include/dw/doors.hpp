// damned_waters/engine/include/dw/doors.hpp
// Purpose: a door you open the way the modern Resident Evils let you: no loading screen, the
// leaf is a real thing in the room. Walk into it gently and it eases ajar (lean on it to look
// through the crack); press it, or run into it, and it swings open away from you; press at an
// open door and you shut it, with a bang the Drowned hear. A Drowned that reaches a shut door
// shoves it open. A double-acting leaf: it swings away from whoever pushes it.
// Pure: the leaf's swing, its collider, and what it says (a creak, a slam). Unit-tested
// (tests/test_doors.cpp).
//
// ELI5: a saloon door with a temper. Lean on it and it gives a little; shove it and it flies
// open; pull it to and it slams.
#ifndef DW_DOORS_HPP
#define DW_DOORS_HPP
#include <algorithm>
#include <cmath>

#include "dw/core.hpp"

namespace dw::doors {

constexpr float AJAR = 0.42f;        // rad (24 degrees): a crack you can see through
constexpr float OPEN = 1.62f;        // rad (93 degrees): wide open
constexpr float PASSABLE = 1.2f;     // rad: open enough to walk through
constexpr float EASE_RATE = 0.55f;   // rad/s while he leans on it
constexpr float OPEN_TIME = 0.5f;    // s, a push
constexpr float CLOSE_TIME = 0.32f;  // s, pulled shut
constexpr float THICK = 0.05f;       // m

enum class Event { None, Creak, Opened, Slam };

struct Leaf {
    float hx = 0, hz = 0;     // the hinge (house coordinates)
    float ux = 1, uz = 0;     // shut: the way from the hinge to the latch (unit)
    float nx = 0, nz = 1;     // the doorway's normal: + swings the latch that way
    float width = 0.9f;
    float angle = 0;          // + toward n, - against it
    float target = 0;
    float rate = 0;           // rad/s toward the target
    bool locked = false;      // a locked door doesn't move
    bool moving = false;
    bool closing = false;
    float lean = 0;           // still being leant on for this long (s): stop leaning and it stays put

    // Where the leaf points now (unit), and its latch end.
    V2 dir() const { const float c = std::cos(angle), s = std::sin(angle); return {ux * c + nx * s, uz * c + nz * s}; }
    V2 latch() const { const V2 d = dir(); return {hx + d.x * width, hz + d.z * width}; }
    bool shut() const { return std::fabs(angle) < 0.03f; }
    bool ajar() const { return std::fabs(angle) >= 0.15f && std::fabs(angle) <= AJAR + 0.06f; }
    bool passable() const { return std::fabs(angle) >= PASSABLE; }
    // Which side of the doorway a point is on: +1 the side n points away from (room a), -1 the far side.
    int side_of(float x, float z) const {
        const float mx = hx + ux * width / 2, mz = hz + uz * width / 2;
        return (x - mx) * nx + (z - mz) * nz <= 0 ? 1 : -1;
    }
    // The leaf as a thin box on the floor plane (resolve_circle_obb's frame: local x along the leaf).
    Obb2 collider() const {
        const V2 d = dir();
        return {hx + d.x * width / 2, hz + d.z * width / 2, width / 2, THICK / 2, std::atan2(-d.z, d.x)};
    }
    // Pushed from `side` (+1: from room a's side, so it swings toward b): wide open.
    void push(int side) {
        if (locked) return;
        target = float(side) * OPEN;
        rate = OPEN / OPEN_TIME;
        closing = false;
    }
    // Leant on from `side` while the stick holds him against it (call it every frame he does): it
    // creeps toward ajar and stops there; let go and it stays where it got to.
    void ease(int side, float dt) {
        if (locked || std::fabs(angle) >= AJAR || (angle != 0 && (angle > 0) != (side > 0))) return;
        target = float(side) * AJAR;
        rate = EASE_RATE;
        closing = false;
        lean = dt * 1.5f;
    }
    void shut_it() {
        if (locked || shut()) return;
        target = 0;
        rate = OPEN / CLOSE_TIME;
        closing = true;
    }
    Event update(float dt) {
        if (rate == EASE_RATE && !closing) {   // leaning: it moves only while he leans
            if (lean <= 0) target = angle;
            lean -= dt;
        }
        const float gap = target - angle;
        if (std::fabs(gap) < 1e-4f) {
            const bool was = moving;
            moving = false;
            angle = target;
            if (was && closing && shut()) { closing = false; return Event::Slam; }
            if (was && std::fabs(angle) >= OPEN - 1e-3f) return Event::Opened;
            return Event::None;
        }
        // A swing eases out over the last few degrees, so it settles rather than stops dead; a lean
        // is a steady creep.
        const float k = rate == EASE_RATE ? 1.0f : std::clamp(std::fabs(gap) / 0.25f, 0.3f, 1.0f);
        const float step = std::min(std::fabs(gap), rate * k * dt);
        angle += gap > 0 ? step : -step;
        const bool started = !moving;
        moving = true;
        return started && !closing ? Event::Creak : Event::None;
    }
};

// A leaf hung in a doorway whose ends are (ax, az)-(bx, bz) with normal (nx, nz).
inline Leaf hang(float ax, float az, float bx, float bz, float nx, float nz, bool hinge_at_a) {
    Leaf l;
    const float w = std::hypot(bx - ax, bz - az);
    l.width = w;
    l.hx = hinge_at_a ? ax : bx;
    l.hz = hinge_at_a ? az : bz;
    l.ux = (hinge_at_a ? bx - ax : ax - bx) / w;
    l.uz = (hinge_at_a ? bz - az : az - bz) / w;
    l.nx = nx;
    l.nz = nz;
    return l;
}

}  // namespace dw::doors
#endif
