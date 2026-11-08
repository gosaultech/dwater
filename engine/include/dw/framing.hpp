// damned_waters/engine/include/dw/framing.hpp
// Purpose: the following view. Every shot is a fixed camera's picture (the background); the screen
// shows a window of it that follows him: he stands about TARGET of its height, no smaller than MIN
// while it can still zoom, no bigger than FIT (it widens as he walks up to the lens), with room
// ahead of him and a still middle so it doesn't twitch. It opens wide on a big space the first
// time (the establishing view), takes in whatever else matters (what he aims at, what's on him,
// the thing he's about to pick up) and pushes in for a hit or a death. The camera itself never
// moves, so the controls never change within a shot. Pure, unit-tested (tests/test_framing.cpp).
//
// ELI5: a photographer standing still on a balcony with a zoom lens, keeping you in the picture as
// you cross the square below: zoomed in while you walk, wide for a moment when you first arrive.
#pragma once
#include <raylib.h>

namespace dw::framing {

constexpr float TARGET = 0.38f;   // his height, as a share of the window's, as a rule
constexpr float MIN = 0.22f;      // never smaller, while the window can zoom further
constexpr float FIT = 0.78f;      // never bigger: the window widens first
constexpr float ZMAX = 2.0f;      // the most a background is enlarged as he walks about
constexpr float ZPUSH = 2.6f;     // ... and for a moment's push-in
constexpr float LEAD = 0.15f;     // room ahead of him, a share of the window's width
constexpr float DEAD = 0.05f;     // how far he may drift off his mark (a share of the width) before it follows
constexpr float PAN_T = 0.45f;    // s: how long the window takes to catch up with him (a smooth, not a snap)
constexpr float ZOOM_T = 0.8f;    // s: ... to change its size
constexpr float SETTLE_T = 0.7f;  // s: ... to close in on him after the establishing view
constexpr float HOLD = 0.6f;      // s: the establishing view, held before it closes in
constexpr float BIG = 450.0f;     // m2: a room this big opens wide the first time he walks in
constexpr float LOST_T = 0.35f;   // s: hidden behind something this long, the window opens wide (and back)

// A window over the background: its centre (u across 0..1, v down 0..1) and its height as a share
// of the background's. Its width is the same share of the background's width: the shape is kept.
struct Window {
    float cx = 0.5f, cy = 0.5f, h = 1.0f;
    float x0() const { return cx - h * 0.5f; }
    float y0() const { return cy - h * 0.5f; }
};

// The fixed camera: where a point in the room falls on its background.
struct Lens {
    Vector3 pos{}, f{0, 0, -1}, r{1, 0, 0}, u{0, 1, 0};
    float tan_v = 1, aspect = 16.0f / 9.0f;
    static Lens from(Vector3 pos, Vector3 target, float fovy_deg, float aspect);
    // (u across 0..1, v down 0..1, depth along the view; depth <= 0: behind the camera)
    Vector3 project(Vector3 p) const;
};

// A point on the background, on the screen (0..1 across, 0..1 down) through the window.
Vector2 to_screen(const Window& w, Vector2 uv);

// The frustum for the window: left, right, bottom, top at one metre in front of the lens (multiply
// by the near plane's distance). The full window gives the camera's own symmetric frustum.
struct Frustum { float l, r, b, t; };
Frustum frustum(const Lens& lens, const Window& w);

// Him, on the background: his feet and the top of his head (u, v), and which way he faces across
// the picture (-1 left .. 1 right; 0 toward or away from the lens).
struct Subject {
    Vector2 feet{}, head{};
    float lead = 0;
    bool seen = true;     // false: behind the camera (keep the window where it is)
    bool hidden = false;  // behind something in the painting (a tent, a bus): the whole picture, to see round him
};
// Anything else the window should hold with him: a box on the background (u, v).
struct Extra {
    bool on = false;
    Vector2 lo{}, hi{};
    void add(Vector2 a, Vector2 b);   // grow to hold this box too
};

// The window's size a shot starts from: him at TARGET where he typically stands in it (the median of
// his height over the floor the shot covers, a share of the background's).
float base_zoom(float median_height);

// Where the window wants to be for him (no smoothing): the size from the shot's zoom, kept between
// MIN and FIT of him and wide enough for the extra box; room ahead of him; his feet low in the
// picture and the top of his head clear; all inside the background. `mark` is the dead zone's
// centre (in and out: it only moves when he leaves the still middle).
Window aim(const Subject& s, const Extra& also, float zoom, float& mark);

class Operator {
public:
    // A cut to a new shot: straight onto him (or, the first time in a big space, the whole picture,
    // held, then closing in).
    void cut(const Subject& s, const Extra& also, float zoom, bool establish);
    // A frame: follow him. push (>= 1) pushes in on him at once, about where he stands (a hit, a death).
    Window update(const Subject& s, const Extra& also, float push, float dt);
    const Window& shown() const { return shown_; }
    bool establishing() const { return hold_ > 0 || settle_; }

private:
    Window w_, shown_;
    float vx_ = 0, vy_ = 0, vh_ = 0, zoom_ = 1, mark_ = 0.5f, hold_ = 0, settle_t_ = 0;
    float hid_t_ = 0, vis_t_ = 0;   // how long he's been hidden, or in sight
    bool settle_ = false, lost_ = false;   // lost: hidden long enough to open wide
};

}  // namespace dw::framing
