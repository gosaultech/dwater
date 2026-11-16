// damned_waters/engine/include/dw/strand_tube.hpp
// Purpose: the shape of one rope of hair (a loc), from the handful of points its physics moves.
// Like stringing beads on a bent wire: the wire is a smooth curve through the simulated points,
// and each bead is a ring whose size says how thick the rope is there. Hand-rolled locs are not
// extruded pipe: they swell and thin along their length, wander a little off their line, start
// slimmer where the new growth leaves the scalp and end in a rounded tip.
// Pure maths (no OpenGL): Character::step_strands turns the rings into triangles every frame.
#ifndef DW_STRAND_TUBE_HPP
#define DW_STRAND_TUBE_HPP
#include <raylib.h>
#include <raymath.h>

namespace dw::strand {

constexpr int CAP = 2;   // extra rings past the last point, rounding the end off

struct Shape {
    int n = 8;              // simulated points along the strand
    int sub = 1;            // rings drawn per simulated segment (2: a smooth curve, not a bent straw)
    float seg = 0.02f;      // metres between simulated points
    float radius = 0.005f;  // metres, the body of the rope
    float taper = 0.22f;    // how much thinner the end is than the body (0..1)
    float lump = 0.09f;     // how uneven the thickness is along it (0..1)
    float wave = 0.0f;      // metres the rope wanders off its smooth line
    float root = 1.0f;      // thickness where it leaves the scalp, relative to the body
    float phase = 0.0f;     // per strand, so no two swell in the same places
};

struct Ring {
    Vector3 c;        // centre
    Vector3 x, y;     // the ring's plane (unit, perpendicular to the strand and each other)
    float r;          // radius (m)
    float along;      // metres from the root
};

// Rings drawn for a strand of n points: the curve's, plus the cap's.
inline int rings(int n, int sub) { return (n - 1) * sub + 1 + CAP; }

// The rope's radius `along` metres from the root (before the cap rounds it off).
float radius_at(const Shape& s, float along);

// Fill out[rings(s.n, s.sub)] from the strand's points p[s.n]. `x_hint` starts the frame (any
// direction not along the strand); the frame is carried down the strand without twisting.
// Returns the tip: the point that closes the rounded end.
Vector3 build(const Vector3* p, const Shape& s, Vector3 x_hint, Ring* out);

}  // namespace dw::strand
#endif
