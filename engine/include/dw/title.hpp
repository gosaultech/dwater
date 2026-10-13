// damned_waters/engine/include/dw/title.hpp
// Purpose: the title screen's timing and its menu, as pure numbers and rules (Game::update_title
// runs it, Game::draw_title draws it). Black; the name comes up out of the dark, as it does at the
// route's end; then the choice under it: New Game or Quit. New Game brings the dark down before he
// wakes in the house. Unit-tested (tests/test_title.cpp).
//
// Like a theatre before the play: the house lights down, the play's name on the curtain, then the
// usher's question.
#ifndef DW_TITLE_HPP
#define DW_TITLE_HPP
#include "dw/death.hpp"

namespace dw::title {

enum Item { NEW_GAME, QUIT, ITEMS };

constexpr float NAME_FROM = 0.5f, NAME_TO = 3.0f;   // the name comes up out of the dark
constexpr float MENU_FROM = 2.5f, MENU_TO = 3.3f;   // then the choice under it
constexpr float LEAVE = 1.2f;                       // New Game: the dark comes down, then the house

inline float name(float t) { return death::smooth(NAME_FROM, NAME_TO, t); }
inline float menu(float t) { return death::smooth(MENU_FROM, MENU_TO, t); }
// A press before the choice is up picks nothing (a button still held from the last screen).
inline bool choosing(float t) { return t >= MENU_FROM; }
// The cursor after a push of the stick or the d-pad (nav_y +1: up), round the ends.
inline int next(int sel, int nav_y) { return ((sel - nav_y) % ITEMS + ITEMS) % ITEMS; }
inline float leaving(float t) { return death::smooth(0.0f, LEAVE, t); }
inline bool gone(float t) { return t >= LEAVE; }

}  // namespace dw::title
#endif
