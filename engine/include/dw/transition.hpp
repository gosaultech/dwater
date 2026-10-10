// damned_waters/engine/include/dw/transition.hpp
// Purpose: the short beat between storeys (down the cellar stairs, back up): the picture fades to
// black, a moment of dark with his steps on the stairs while the other floor is put in place,
// then it fades up on the far side. Doors between rooms on one floor need none of this (they're
// seamless); only a change of floor does. Pure timing, unit-tested (tests/test_doors.cpp).
//
// ELI5: a stage blackout between scenes: lights down, the set is changed in the dark, lights up.
#ifndef DW_TRANSITION_HPP
#define DW_TRANSITION_HPP
#include <algorithm>

namespace dw {

struct Beat {
    enum class Phase { Idle, Out, Hold, In };
    enum class Event { None, Swap, Done };
    static constexpr float OUT = 0.4f, HOLD = 0.8f, IN = 0.45f;
    Phase phase = Phase::Idle;
    float t = 0;
    bool busy() const { return phase != Phase::Idle; }
    void start() { phase = Phase::Out; t = 0; }
    // Swap: the moment to put the other floor in place (fully dark); Done: back in control.
    Event update(float dt) {
        if (phase == Phase::Idle) return Event::None;
        t += dt;
        if (phase == Phase::Out && t >= OUT) { phase = Phase::Hold; t = 0; return Event::Swap; }
        if (phase == Phase::Hold && t >= HOLD) { phase = Phase::In; t = 0; }
        if (phase == Phase::In && t >= IN) { phase = Phase::Idle; t = 0; return Event::Done; }
        return Event::None;
    }
    // How dark the picture is, 0..1.
    float black() const {
        switch (phase) {
            case Phase::Out: return std::clamp(t / OUT, 0.0f, 1.0f);
            case Phase::Hold: return 1.0f;
            case Phase::In: return 1.0f - std::clamp(t / IN, 0.0f, 1.0f);
            default: return 0.0f;
        }
    }
};

}  // namespace dw
#endif
