// damned_waters/engine/include/dw/two_bone.hpp
// Purpose: an arm of two bones (upper arm, forearm) reaching for a point, solved outright rather
// than searched for: how far the elbow bends and how the upper arm turns so the wrist lands on the
// point. Character::support_hand uses it to keep the left hand on a gun held in both hands.
//
// Like reaching for a cup: how far you open your elbow is fixed by how far away the cup is (the
// two bones and the gap make a triangle); what's left is which way the elbow points, and you keep
// it where it was (down and out) rather than winging it up.
#ifndef DW_TWO_BONE_HPP
#define DW_TWO_BONE_HPP
#include <raylib.h>
#include <raymath.h>

namespace dw {

// The elbow's bend (radians, about its own x axis, as this rig bends elbows; 0 straight) and the
// upper arm's turn that put the wrist on `goal`.
//   oe: shoulder to elbow, ow: elbow to wrist, as the arm is built (unbent, unturned);
//   goal, hinge: in the shoulder's unturned frame (the turn is applied there).
// Of the turns that reach, the one whose elbow hinge (its x axis) lies nearest `hinge`, so the
// elbow points where the pose had it. A goal out of reach gets the arm pointed straight at it.
struct TwoBone {
    float elbow;
    Matrix turn;
};
TwoBone solve_two_bone(Vector3 oe, Vector3 ow, Vector3 goal, Vector3 hinge);

}  // namespace dw

#endif
