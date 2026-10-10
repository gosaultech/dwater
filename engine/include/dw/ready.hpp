// damned_waters/engine/include/dw/ready.hpp
// Purpose: trigger discipline as rules. While he holds a gun without aiming it, it's carried at the
// ready (low in front of him in both hands, the muzzle at the floor ahead) and his trigger finger
// lies straight along the side of the frame, outside the trigger guard. Aiming raises the gun, and
// only once it's nearly up does the finger go to the trigger; it comes off the moment he stops
// aiming, before the gun is down. Character turns these numbers into the arms and the finger each
// frame (character.cpp); the timing is unit-tested without a window (tests/test_ready.cpp).
//
// Like a car's handbrake and clutch: the gun comes up first, and only when it's there does the
// finger go in; letting go, the finger is out first.
#ifndef DW_READY_HPP
#define DW_READY_HPP
#include <algorithm>

namespace dw::ready {

// How far up the gun must be (0 at the ready, 1 aimed) before the finger may go to the trigger:
// the sights nearly on.
constexpr float FINGER_IN_AT = 0.8f;
// Seconds for the finger to go from the frame to the trigger, and to come off it again (faster:
// off is the safe way).
constexpr float FINGER_ON = 0.12f;
constexpr float FINGER_OFF = 0.08f;

// The raise, 0 at the ready to 1 aimed, eased by `k` (0..1 this frame) the same way the arms ease
// toward their pose, so it says how far the arms have got.
inline float raise(float now, bool aiming, float k) { return now + ((aiming ? 1.0f : 0.0f) - now) * std::clamp(k, 0.0f, 1.0f); }

// Where the trigger finger is, 0 indexed along the frame to 1 on the trigger, a frame of `dt`
// seconds later: toward the trigger only while aiming with the gun up (`raise` at least
// FINGER_IN_AT), otherwise off it.
inline float finger(float now, bool aiming, float raise, float dt) {
    const bool on = aiming && raise >= FINGER_IN_AT;
    return on ? std::min(1.0f, now + dt / FINGER_ON) : std::max(0.0f, now - dt / FINGER_OFF);
}

// The finger's blend between its two places (eased in and out, so it settles on the trigger
// rather than striking it).
inline float blend(float finger) {
    const float f = std::clamp(finger, 0.0f, 1.0f);
    return f * f * (3 - 2 * f);
}

}  // namespace dw::ready

#endif
