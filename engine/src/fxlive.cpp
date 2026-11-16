// damned_waters/engine/src/fxlive.cpp
// Purpose: see fxlive.hpp: a fire's breath, a beacon, a failing tube, a wire's sparks.
#include "dw/fxlive.hpp"

#include <algorithm>
#include <cmath>

namespace dw::fxlive {

namespace {
// A smooth random wander (0..1) at about `hz`, from hashed knots eased between.
float wander(float t, float hz, int seed) {
    const float x = t * hz;
    const float i = std::floor(x), f = x - i;
    auto h = [seed](float k) {
        const float s = std::sin(k * 127.1f + float(seed) * 311.7f) * 43758.5453f;
        return s - std::floor(s);
    };
    const float e = f * f * (3 - 2 * f);
    return h(i) + (h(i + 1) - h(i)) * e;
}
}  // namespace

float fire(float t, int seed) {
    const float swell = wander(t, 1.3f, seed) - 0.5f;          // slow
    const float lick = wander(t, 7.0f, seed + 17) - 0.5f;      // quick
    const float spit = wander(t, 19.0f, seed + 31) - 0.5f;     // quicker still, smaller
    return std::clamp(1.0f + swell * 0.36f + lick * 0.18f + spit * 0.08f, 0.7f, 1.3f);
}

float strobe(float t, float rate, int seed) {
    const float ph = t * std::max(rate, 0.01f) + float(seed) * 0.37f;
    const float f = ph - std::floor(ph);   // where in its turn
    auto pulse = [](float x, float at) { const float d = (x - at) / 0.045f; return std::exp(-d * d); };
    return std::min(1.0f, pulse(f, 0.08f) + pulse(f, 0.26f));
}

float flicker(float t, int seed) {
    const float buzz = 0.93f + 0.07f * std::sin(t * 2.0f * 3.14159265f * 50.0f);   // the mains in it
    const float w = wander(t, 3.0f, seed);
    const float out = w > 0.82f ? std::clamp((w - 0.82f) / 0.04f, 0.0f, 1.0f) : 0.0f;   // now and then it dies...
    const float stutter = wander(t, 23.0f, seed + 5) > 0.5f ? 1.0f : 0.35f;            // ...stuttering as it goes
    return std::clamp(buzz * (1.0f - out * (out < 1.0f ? stutter : 1.0f) * 0.92f), 0.0f, 1.0f);
}

float Sparks::rnd() {
    rng_ = rng_ * 1664525u + 1013904223u;
    return float(rng_ >> 8) / float(1u << 24);
}

void Sparks::burst(Vector3 at, int n, float speed) {
    for (int k = 0; k < n; ++k) {
        Spark* free = nullptr;
        for (auto& s : s_)
            if (s.life <= 0) { free = &s; break; }
        if (!free) return;
        const float a = rnd() * 6.2831853f, out = (0.3f + rnd() * 1.0f) * speed;
        free->p = at;
        free->v = {std::cos(a) * out, (0.6f + rnd() * 1.6f) * speed, std::sin(a) * out};
        free->age = 0;
        free->life = 0.3f + rnd() * 0.8f;
    }
}

void Sparks::update(float dt, float t, Vector3 at, float every, int seed) {
    if (next_ < 0) {   // (first frame: its own rhythm)
        rng_ = 0x9E3779B9u ^ unsigned(seed * 2654435761u);
        next_ = t + rnd() * every;
        crackle_ = t + 0.3f + rnd();
    }
    flash_ = std::max(0.0f, flash_ - dt * 6.0f);   // (the arc fades; a burst this frame lights it full)
    if (t >= next_) {
        burst(at, 22 + int(rnd() * 18), 1.8f);
        flash_ = 1.0f;
        next_ = t + every * (0.6f + 0.8f * rnd());
    }
    if (t >= crackle_) {
        burst(at, 3 + int(rnd() * 4), 1.0f);
        flash_ = std::max(flash_, 0.45f);
        crackle_ = t + 0.15f + rnd() * 0.9f;
    }
    for (auto& s : s_) {
        if (s.life <= 0) continue;
        s.age += dt;
        if (s.age >= s.life) { s.life = 0; continue; }
        s.v.y -= 9.81f * dt;
        s.p = {s.p.x + s.v.x * dt, s.p.y + s.v.y * dt, s.p.z + s.v.z * dt};
        if (s.p.y < at.y) {   // the wet road: a skip, losing most of it
            s.p.y = at.y;
            s.v = {s.v.x * 0.55f, -s.v.y * 0.3f, s.v.z * 0.55f};
        }
    }
}

int Sparks::alive() const {
    int n = 0;
    for (const auto& s : s_) n += s.life > 0;
    return n;
}

}  // namespace dw::fxlive
