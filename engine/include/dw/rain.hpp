// damned_waters/engine/include/dw/rain.hpp
// Purpose: rain over the streets: a fixed pool of drops falling through a box that follows him,
// slanted by the wind; drawn as short streaks against the painting's depth (game.cpp).
#pragma once
#include <cstdint>
#include <vector>

#include "dw/room_spec.hpp"

namespace dw {

class Rain {
public:
    static constexpr int N = 1400;             // drops in the box
    static constexpr float HALF = 9.0f;        // m: the box's half width round him
    static constexpr float TOP = 9.0f;         // m: where a drop starts
    static constexpr float FALL = 9.5f;        // m/s
    static constexpr float STREAK = 0.035f;    // s: a streak is how far a drop falls in this long (motion blur)
    V3 wind{0.9f, 0.0f, 0.4f};                 // m/s

    void reset(float cx, float cz, uint32_t seed = 7);
    void update(float dt, float cx, float cz);   // fall; respawn at the top; keep the box round (cx, cz)
    const std::vector<V3>& drops() const { return drops_; }
    V3 velocity() const { return {wind.x, -FALL, wind.z}; }

private:
    float unit();   // 0..1
    std::vector<V3> drops_;
    uint32_t s_ = 7;
};

}  // namespace dw
