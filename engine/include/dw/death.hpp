// damned_waters/engine/include/dw/death.hpp
// Purpose: the death screen's timing, as pure numbers (Game::draw_death draws it). He falls; the
// picture drains into a deep red-black, blood seeping in from the edges; YOU DIED comes up out of
// the dark in a blood-red serif, settling as it comes; drops of blood gather under the letters
// and run; then, once it's had its moment, the choice: try again or quit. Unit-tested
// (tests/test_death.cpp).
//
// Like a stage curtain coming down in a slow, set order: lights, then the words, then the house
// lights for the audience to choose.
#ifndef DW_DEATH_HPP
#define DW_DEATH_HPP
#include <algorithm>

namespace dw::death {

constexpr float DARK_FROM = 0.8f, DARK_TO = 2.6f;      // the picture drains (seconds after he falls)
constexpr float TITLE_FROM = 1.6f, TITLE_TO = 3.4f;    // the words come up
constexpr float DRIPS_FROM = 2.6f, DRIP_TIME = 3.0f;   // blood gathers under the letters and runs
constexpr float CHOICE_AT = 3.6f;                      // try again / quit
constexpr int DRIPS = 7;

inline float smooth(float a, float b, float t) {
    const float k = std::clamp((t - a) / (b - a), 0.0f, 1.0f);
    return k * k * (3 - 2 * k);
}
inline float darkness(float t) { return smooth(DARK_FROM, DARK_TO, t); }
inline float title(float t) { return smooth(TITLE_FROM, TITLE_TO, t); }
// The words settle as they come: a little larger at first, then their size.
inline float title_scale(float t) { return 1.07f - 0.07f * title(t); }
// Drop i (0..DRIPS-1): which letter of "YOU DIED" it runs from (never the space), where under it
// (-0.5..0.5 of the letter's width from its middle), and how far it has run (0..1 of its own
// length, which `drip_length` gives as a share of the letters' height). Each starts on its own
// beat and slows as it goes, the way a drop thins.
inline int drip_letter(int i) { static const int C[DRIPS] = {0, 1, 2, 4, 5, 6, 7}; return C[std::clamp(i, 0, DRIPS - 1)]; }
inline float drip_offset(int i) { static const float O[DRIPS] = {0.05f, -0.18f, 0.28f, -0.3f, 0.0f, 0.22f, -0.12f}; return O[std::clamp(i, 0, DRIPS - 1)]; }
inline float drip_length(int i) { static const float L[DRIPS] = {0.55f, 1.1f, 0.35f, 0.8f, 1.4f, 0.5f, 0.9f}; return L[std::clamp(i, 0, DRIPS - 1)]; }
inline float drip(int i, float t) {
    static const float D[DRIPS] = {0.0f, 0.5f, 1.1f, 0.25f, 0.8f, 1.4f, 0.6f};
    const float k = std::clamp((t - DRIPS_FROM - D[std::clamp(i, 0, DRIPS - 1)]) / DRIP_TIME, 0.0f, 1.0f);
    return 1.0f - (1.0f - k) * (1.0f - k) * (1.0f - k);   // fast, then slowing
}
inline bool choosing(float t) { return t >= CHOICE_AT; }

}  // namespace dw::death
#endif
