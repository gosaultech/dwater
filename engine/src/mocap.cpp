// damned_waters/engine/src/mocap.cpp
// Purpose: see mocap.hpp: sampling, mixing and pacing the baked gait loops (the loops themselves are
// in mocap_clips.inc, written by tools/anim/bake_mocap.py).
#include "dw/mocap.hpp"

#include <algorithm>
#include <cmath>

namespace dw::mocap {

#include "mocap_clips.inc"

namespace {
Vector3 lerp3(Vector3 a, Vector3 b, float w) { return {a.x + (b.x - a.x) * w, a.y + (b.y - a.y) * w, a.z + (b.z - a.z) * w}; }
Vector3 at3(const float* r) { return {r[0], r[1], r[2]}; }
}  // namespace

Frame sample(const Clip& c, float phase) {
    Frame f;
    if (c.rows <= 0) return f;
    const float p = (phase - std::floor(phase)) * float(c.rows);
    const int i = std::min(int(p), c.rows - 1), j = (i + 1) % c.rows;
    const float w = p - float(i);
    const float* a = c.data + size_t(i) * ROW;
    const float* b = c.data + size_t(j) * ROW;
    // The loop was closed when baked: the last row runs into the first as smoothly as any two others.
    f.off = lerp3(at3(a), at3(b), w);
    for (int k = 0; k < NJ; ++k) f.ang[k] = lerp3(at3(a + 3 + 3 * k), at3(b + 3 + 3 * k), w);
    return f;
}

Frame mix(const Frame& a, const Frame& b, float w) {
    Frame f;
    f.off = lerp3(a.off, b.off, w);
    for (int k = 0; k < NJ; ++k) f.ang[k] = lerp3(a.ang[k], b.ang[k], w);
    return f;
}

Pace pace(float speed, float scale, float sneak, float walk, float run) {
    Pace p;
    if (speed <= walk) {
        p.a = &SNEAK;
        p.b = &WALK;
        p.w = std::clamp((speed - sneak) / std::max(walk - sneak, 1e-3f), 0.0f, 1.0f);
    } else {
        p.a = &WALK;
        p.b = &RUN;
        p.w = std::clamp((speed - walk) / std::max(run - walk, 1e-3f), 0.0f, 1.0f);
    }
    const float stride = (p.a->stride + (p.b->stride - p.a->stride) * p.w) * scale;
    const float own = stride / (p.a->time + (p.b->time - p.a->time) * p.w);   // the mix's own speed, at his size
    p.stretch = std::sqrt(std::max(1.0f, speed / std::max(own, 1e-3f)));      // faster than it: half in a longer stride
    p.stride = stride * p.stretch;                                             // (and half in a quicker step)
    return p;
}

Frame at(const Pace& p, float phase, float still, float idle_phase) {
    Frame f = mix(sample(*p.a, phase), sample(*p.b, phase), p.w);
    if (p.stretch > 1.0f) {   // a longer stride: the hips swing further about where they swing round
        for (int k : {HIP_L, HIP_R}) {
            float mean = 0;
            for (int i = 0; i < 8; ++i) mean += mix(sample(*p.a, float(i) / 8), sample(*p.b, float(i) / 8), p.w).ang[k].x / 8;
            f.ang[k].x = mean + (f.ang[k].x - mean) * p.stretch;
        }
    }
    if (still > 0) f = mix(f, sample(IDLE, idle_phase), std::clamp(still, 0.0f, 1.0f));
    return f;
}

}  // namespace dw::mocap
