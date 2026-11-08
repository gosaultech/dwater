// damned_waters/engine/include/dw/mocap.hpp
// Purpose: his sneak, walk, run and idle as real people move: gait cycles from the 100STYLE motion
// capture dataset (CC BY 4.0, docs/motion_credits.md), baked onto this rig by tools/anim/bake_mocap.py
// into src/mocap_clips.inc. A clip is one loop starting with the left foot down: rows of the pelvis's
// offset (m) and the angles of the pelvis, spine, chest, neck, head and both legs, as the rig takes
// them. Played by his speed: the phase moves on as far as his feet have carried him, so they plant
// rather than slide; the loops for the speeds either side of his are mixed at the same phase; a
// speed past a loop's own lengthens its stride and quickens its step a little each. Pure,
// unit-tested (tests/test_mocap.cpp).
//
// ELI5: a flip-book of a real person walking, one for each pace. Walk faster and you flip faster and
// pick the faster person's book; between two paces, both books traced over each other.
#pragma once
#include <raylib.h>

namespace dw::mocap {

constexpr int NJ = 11;   // the joints a clip drives, in this order:
enum Slot : int { PELVIS, SPINE, CHEST, NECK, HEAD, HIP_L, KNE_L, ANK_L, HIP_R, KNE_R, ANK_R };
constexpr int ROW = 3 + 3 * NJ;   // floats a row: the pelvis's offset, then each joint's angles

struct Clip {
    const char* name;
    float stride;       // m a loop carries the captured actor (0: standing)
    float time;         // s a loop takes as captured
    float hip_height;   // m: the actor's hips above the floor standing straight
    float leg;          // m: the actor's hip to ankle
    int rows;
    const float* data;  // rows * ROW
};

struct Frame {
    Vector3 off{};          // the pelvis's offset (x across, y its height above the floor, z along), m
    Vector3 ang[NJ]{};      // radians, as the rig composes them (Ry * Rx * Rz)
};

extern const Clip SNEAK, WALK, RUN, IDLE;
extern const Clip DRAG, DRUNK, LURCH;   // the Drowned's shambles (one a variant), kept lopsided

// The loop at `phase` (in loops: any number, wraps), between rows.
Frame sample(const Clip& c, float phase);
// a to b by w (0..1).
Frame mix(const Frame& a, const Frame& b, float w);

// Which loops at this speed and how far between them; the stride (m, already scaled to his
// size) that one loop of the mix covers; and how much a speed past the loops' own stretches the
// stride (1: not at all; the legs swing that much further).
struct Pace {
    const Clip* a = &SNEAK;
    const Clip* b = &SNEAK;
    float w = 0;
    float stride = 1;
    float stretch = 1;
};
// scale: his hip height over the actor's (the rig's pelvis above the floor / Clip::hip_height).
// sneak, walk, run: the game's speeds for them (m/s).
Pace pace(float speed, float scale, float sneak, float walk, float run);

// One loop alone at `speed` (a Drowned's shamble): its stride at that size, stretched past its own speed.
Pace pace(const Clip& c, float speed, float scale);

// His legs, hips and spine moving at `speed`: the loops mixed, the stride stretched, and `still`
// (0..1) of the idle loop at `idle_phase` over it as he slows to a stop.
Frame at(const Pace& p, float phase, float still, float idle_phase);

}  // namespace dw::mocap
