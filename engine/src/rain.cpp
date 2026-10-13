// damned_waters/engine/src/rain.cpp
// Purpose: the rain's drops: fall, respawn above, and wrap to stay in the box round him.
#include "dw/rain.hpp"

#include <cmath>

namespace dw {

float Rain::unit() {
    s_ = s_ * 1664525u + 1013904223u;
    return float(s_ >> 8) / float(1u << 24);
}

void Rain::reset(float cx, float cz, uint32_t seed) {
    s_ = seed;
    drops_.resize(N);
    for (auto& d : drops_) d = {cx + (unit() * 2 - 1) * HALF, unit() * TOP, cz + (unit() * 2 - 1) * HALF};
}

void Rain::update(float dt, float cx, float cz) {
    if (drops_.empty()) reset(cx, cz);
    const float span = 2 * HALF;
    for (auto& d : drops_) {
        d.x += wind.x * dt;
        d.y -= FALL * dt;
        d.z += wind.z * dt;
        if (d.y < 0) {
            d.y += TOP;
            d.x = cx + (unit() * 2 - 1) * HALF;
            d.z = cz + (unit() * 2 - 1) * HALF;
        }
        if (std::abs(d.x - cx) > 2 * span || std::abs(d.z - cz) > 2 * span) {   // (he's come a long way: a beat)
            d.x = cx + (unit() * 2 - 1) * HALF;
            d.z = cz + (unit() * 2 - 1) * HALF;
        }
        if (d.x < cx - HALF) d.x += span; else if (d.x > cx + HALF) d.x -= span;
        if (d.z < cz - HALF) d.z += span; else if (d.z > cz + HALF) d.z -= span;
    }
}

}  // namespace dw
