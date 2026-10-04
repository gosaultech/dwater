// damned_waters/engine/include/dw/two_bone.hpp
// Purpose: an arm of two bones (upper arm, forearm) reaching for a point, solved outright rather
// than searched for: how far the elbow bends and how the upper arm turns so the wrist lands on the
// point. Character::arm_to uses it to keep the left hand on a gun held in both hands, and to move
// the hands through a reload.
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

// Two measures of an arm's look, for the aim fitters (shoulder, elbow and wrist joints, world).
// How far the elbow is from hanging down: the modern stances keep the elbows down under the gun,
// not winged out (the old shotgun "chicken wing") or up. From the line between shoulder and wrist
// the elbow should sit below it, within 35 degrees of straight down (world -y); 0 when it does,
// growing with how far off it is, weighted by how far off the line the elbow sits (a straight
// arm's elbow points nowhere).
float elbow_not_down(Vector3 shoulder, Vector3 elbow, Vector3 wrist);
// How far the arm is bent at the elbow (radians; 0 straight).
float elbow_bend(Vector3 shoulder, Vector3 elbow, Vector3 wrist);

// Part of the way from one joint turn to another, given as this rig's angles (x, y, z, applied z,
// then x, then y), turning the shortest way round (a slerp) rather than easing each angle on its
// own: blending the angles themselves can swing a finger out sideways halfway between two poses
// (like walking between two map pins along the lines of latitude rather than straight).
Vector3 slerp_angles(Vector3 a, Vector3 b, float k);

// A wrist's turn split in two (swing-twist): the twist about the forearm's own length (`axis`;
// the forearm's two bones roll round each other for that, up to about 80 degrees either way from
// the hand's rest), and the swing, how far the hand then tips off the forearm's line (a wrist
// bends about 40 degrees comfortably, 60 at a strain). Both radians; twist signed, swing >= 0.
void swing_twist(Quaternion q, Vector3 axis, float& swing, float& twist);

}  // namespace dw

#endif
