// damned_waters/engine/include/dw/streaming.hpp
// Purpose: which painted plates to keep on the GPU. A wide room is filmed in many short shots now
// (tools/citygen/cameras.py), so a room and its neighbours together hold dozens of plates; keeping
// them all would fill the GPU, and loading a room's all at once would hitch at the door. Instead:
// every shot whose zone he could reach within a couple of seconds is decoded in the background,
// and a shot is let go only once he's well away from it (two radii, so one standing on the line
// never loads and drops the same plate over and over). Pure, unit-tested (tests/test_streaming.cpp).
//
// ELI5: a stage crew that keeps the backdrops of the next few scenes in the wings, not the whole
// play's, and only strikes one once the actors have moved well on.
#ifndef DW_STREAMING_HPP
#define DW_STREAMING_HPP
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "dw/core.hpp"

namespace dw::streaming {

constexpr float WANT = 14.0f;   // m: decode a shot's plate once he's this near its zone (about 4 s at a run)
constexpr float KEEP = 22.0f;   // m: let it go once he's this far from it
constexpr float RESTREAM = 1.5f;   // m: think about it again after he's moved this far

// How far (x, z) is from the rectangle (0 inside it).
inline float to_rect(const Rect2& r, float x, float z) {
    const float dx = std::max({r.x0 - x, 0.0f, x - r.x1}), dz = std::max({r.z0 - z, 0.0f, z - r.z1});
    return std::hypot(dx, dz);
}

// A plate that might be wanted: the shot's zone on the floor plan (for a door's view through the
// crack, a small square round the door).
struct Candidate {
    std::string room, shot;
    Rect2 zone;
};

// The plates to decode (within `radius` of where he is) or keep (within KEEP): their keys,
// "room/shot". `always` (the shot on screen now) is in both whatever the distance.
inline std::vector<std::string> within(const std::vector<Candidate>& c, float x, float z, float radius, const std::string& always = "") {
    std::vector<std::string> out;
    if (!always.empty()) out.push_back(always);
    for (const auto& k : c) {
        const std::string key = k.room + "/" + k.shot;
        if (key != always && to_rect(k.zone, x, z) <= radius) out.push_back(key);
    }
    return out;
}

}  // namespace dw::streaming
#endif
