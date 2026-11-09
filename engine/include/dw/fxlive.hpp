// damned_waters/engine/include/dw/fxlive.hpp
// Purpose: the life drawn over the painted streets (a room's "fx", written by the catastrophe pass,
// tools/citygen/catastrophe.py): how bright a fire burns from moment to moment, a beacon's flashes,
// a failing tube's flicker, and a snapped wire's sparks (each spark thrown up, falling, bouncing
// once or twice on the wet road, cooling from white to orange). The painting was rendered with each
// light at its average; the engine adds the difference (dw: game_fx.cpp). Pure, unit-tested
// (tests/test_fxlive.cpp).
//
// ELI5: the stagehands behind a painted backdrop: one waving a torch behind the cut-out flames, one
// working the blue lamp, one flicking a dodgy light switch, one striking sparks off a grinder.
#pragma once
#include <raylib.h>

#include <array>

namespace dw::fxlive {

// A fire's brightness now: around 1 (0.7..1.3), slow swells and quick licks, its own rhythm per seed.
float fire(float t, int seed);
// A beacon: 0 dark .. 1 lit; two quick flashes each turn, `rate` turns a second.
float strobe(float t, float rate, int seed);
// A tube that's failing: mostly on (1), buzzing, now and then out for a moment (near 0).
float flicker(float t, int seed);

struct Spark {
    Vector3 p{}, v{};
    float age = 0, life = 0;   // life 0: not in use
    float heat() const { return life > 0 ? 1.0f - age / life : 0.0f; }   // 1 white-hot .. 0 out
};

// A snapped wire arcing on the road: a burst of sparks every `every` seconds or so (and crackles in
// between), each thrown up and out, falling, bouncing on the floor at the wire's height.
class Sparks {
public:
    static constexpr int MAX = 96;
    void update(float dt, float t, Vector3 at, float every, int seed);
    const std::array<Spark, MAX>& all() const { return s_; }
    int alive() const;
    float flash() const { return flash_; }   // the arc's light now (0..1): bright at a burst, fading

private:
    void burst(Vector3 at, int n, float speed);
    float rnd();
    std::array<Spark, MAX> s_{};
    unsigned rng_ = 0;
    float next_ = -1, crackle_ = -1, flash_ = 0;
};

}  // namespace dw::fxlive
