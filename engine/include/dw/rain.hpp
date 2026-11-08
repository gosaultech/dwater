// damned_waters/engine/include/dw/rain.hpp
// Purpose: rain over the streets, everywhere the camera looks. Sheets of falling streaks stand
// square to the shot from a metre in front of the lens to the far end of the street; each is drawn
// against the painting's depth and the characters (game.cpp; the streaks are shaders.cpp RAIN_FS),
// so it rains all the way down the street, behind the houses and in front of him, never in a
// bubble round him (the old rain was a box of drops that followed him). Pure: where the sheets
// stand for a camera. Unit-tested (tests/test_rain.cpp).
//
// ELI5: a theatre's rain: curtains of falling water hung across the stage at different depths, so
// the whole stage is wet and the actors walk between them.
#pragma once
#include <array>

#include "dw/room_spec.hpp"

namespace dw::rain {

constexpr int SHEETS = 8;
// m from the camera along its level forward: spaced closer near the lens, where a sheet's streaks are
// big, and out to the far end of a street.
constexpr float DIST[SHEETS] = {1.2f, 2.0f, 3.2f, 5.0f, 8.0f, 13.0f, 21.0f, 34.0f};
constexpr float MARGIN = 0.5f;   // m: a sheet runs this far past the picture's edges

struct Sheet {
    V3 c[4];          // corners: bottom-left, bottom-right, top-right, top-left, as the camera sees them
    float u0, u1;     // metres across the sheet at its left and right edges (the streaks' pattern runs on these)
    float v0, v1;     // heights (m) of its bottom and top edges
    float dist;       // m
};

// The sheets for a camera at `pos` looking at `target`, with a vertical field of view of `fovy_deg`
// and a picture `aspect` wide: each a vertical plane square to the camera's level forward, a little
// bigger than the picture where it stands.
std::array<Sheet, SHEETS> sheets(V3 pos, V3 target, float fovy_deg, float aspect);

}  // namespace dw::rain
