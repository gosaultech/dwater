// damned_waters/engine/src/framing.cpp
// Purpose: see framing.hpp: the window over a fixed shot's background that follows him (where he
// falls on the background, where the window wants to be, and the smoothing that gets it there).
#include "dw/framing.hpp"

#include <algorithm>
#include <cmath>

namespace dw::framing {

namespace {
Vector3 sub(Vector3 a, Vector3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
float dot(Vector3 a, Vector3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
Vector3 cross(Vector3 a, Vector3 b) { return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x}; }
Vector3 unit(Vector3 a) {
    const float l = std::sqrt(dot(a, a));
    return l > 1e-9f ? Vector3{a.x / l, a.y / l, a.z / l} : Vector3{0, 0, -1};
}
// A critically damped spring toward a moving target: eases off the mark and into it, never past it
// by much (Game Programming Gems 4, "critically damped ease-in/ease-out smoothing").
float damp(float x, float target, float& v, float smooth_t, float dt) {
    const float omega = 2.0f / std::max(smooth_t, 1e-4f), k = omega * dt;
    const float e = 1.0f / (1.0f + k + 0.48f * k * k + 0.235f * k * k * k);
    const float change = x - target, temp = (v + omega * change) * dt;
    v = (v - omega * temp) * e;
    return target + (change + temp) * e;
}
void keep_inside(Window& w) {
    w.h = std::clamp(w.h, 1e-3f, 1.0f);
    w.cx = std::clamp(w.cx, w.h * 0.5f, 1.0f - w.h * 0.5f);
    w.cy = std::clamp(w.cy, w.h * 0.5f, 1.0f - w.h * 0.5f);
}
}  // namespace

Lens Lens::from(Vector3 pos, Vector3 target, float fovy_deg, float aspect) {
    Lens L;
    L.pos = pos;
    L.f = unit(sub(target, pos));
    L.r = unit(cross(L.f, {0, 1, 0}));
    L.u = cross(L.r, L.f);
    L.tan_v = std::tan(fovy_deg * 0.5f * 3.14159265f / 180.0f);
    L.aspect = aspect;
    return L;
}

Vector3 Lens::project(Vector3 p) const {
    const Vector3 d = sub(p, pos);
    const float depth = dot(d, f), z = std::max(std::fabs(depth), 1e-4f);
    const float x = dot(d, r) / z / (tan_v * aspect), y = dot(d, u) / z / tan_v;
    return {(x + 1) * 0.5f, (1 - y) * 0.5f, depth};
}

Vector2 to_screen(const Window& w, Vector2 uv) { return {(uv.x - w.x0()) / w.h, (uv.y - w.y0()) / w.h}; }

Frustum frustum(const Lens& lens, const Window& w) {
    const float tx = lens.tan_v * lens.aspect, ty = lens.tan_v;
    return {(2 * w.x0() - 1) * tx, (2 * (w.x0() + w.h) - 1) * tx, (1 - 2 * (w.y0() + w.h)) * ty, (1 - 2 * w.y0()) * ty};
}

void Extra::add(Vector2 a, Vector2 b) {
    const Vector2 l{std::min(a.x, b.x), std::min(a.y, b.y)}, h{std::max(a.x, b.x), std::max(a.y, b.y)};
    if (!on) { lo = l; hi = h; on = true; return; }
    lo = {std::min(lo.x, l.x), std::min(lo.y, l.y)};
    hi = {std::max(hi.x, h.x), std::max(hi.y, h.y)};
}

float base_zoom(float median_height) {
    if (!(median_height > 1e-4f)) return 1.0f;
    return std::clamp(TARGET / median_height, 1.0f, ZMAX);
}

Window aim(const Subject& s, const Extra& also, float zoom, float& mark) {
    const float a = std::max(s.feet.y - s.head.y, 1e-3f);   // his height, a share of the background's
    float z = std::min(std::max(zoom, MIN / a), ZMAX);
    z = std::min(z, FIT / a);
    // Whatever else it should hold, with him (and a margin): the window no tighter than that.
    const float half = 0.18f * a;   // (his shoulders, either side of him)
    Vector2 lo{std::min(s.feet.x, s.head.x) - half, s.head.y}, hi{std::max(s.feet.x, s.head.x) + half, s.feet.y};
    if (also.on) {
        lo = {std::min(lo.x, also.lo.x), std::min(lo.y, also.lo.y)};
        hi = {std::max(hi.x, also.hi.x), std::max(hi.y, also.hi.y)};
        const float need = std::max((hi.y - lo.y) / 0.84f, (hi.x - lo.x) / 0.88f);
        z = std::min(z, 1.0f / std::max(need, 1e-3f));
    }
    if (s.hidden) z = 1.0f;   // behind something: the whole picture, so the player can see round him
    Window w;
    w.h = 1.0f / std::max(z, 1.0f);
    // Across: room ahead of him; a still middle, so a step or a turn doesn't swing the picture.
    const float want = (s.feet.x + s.head.x) * 0.5f + LEAD * std::clamp(s.lead, -1.0f, 1.0f) * w.h;
    const float dz = DEAD * w.h;
    if (want > mark + dz) mark = want - dz;
    else if (want < mark - dz) mark = want + dz;
    mark = std::clamp(mark, w.h * 0.5f, 1.0f - w.h * 0.5f);
    w.cx = mark;
    // Up and down: his feet low in the picture (lower still, with more ahead, when he's small in it),
    // the top of his head clear of the top.
    const float share = std::min(a / w.h, 1.0f), foot = 0.08f + 0.12f * (1.0f - share);
    w.cy = std::min(s.feet.y - (0.5f - foot) * w.h, s.head.y + 0.44f * w.h);
    if (also.on) {   // the box inside it, if it fits (else centred on it)
        const float mx = 0.06f * w.h, my = 0.08f * w.h;
        const float x_lo = hi.x - w.h * 0.5f + mx, x_hi = lo.x + w.h * 0.5f - mx;
        const float y_lo = hi.y - w.h * 0.5f + my, y_hi = lo.y + w.h * 0.5f - my;
        w.cx = x_lo <= x_hi ? std::clamp(w.cx, x_lo, x_hi) : (lo.x + hi.x) * 0.5f;
        w.cy = y_lo <= y_hi ? std::clamp(w.cy, y_lo, y_hi) : (lo.y + hi.y) * 0.5f;
    }
    keep_inside(w);
    return w;
}

void Operator::cut(const Subject& s, const Extra& also, float zoom, bool establish) {
    zoom_ = zoom;
    vx_ = vy_ = vh_ = 0;
    hold_ = 0;
    settle_ = false;
    settle_t_ = 0;
    mark_ = s.seen ? (s.feet.x + s.head.x) * 0.5f : 0.5f;
    lost_ = s.hidden;   // (at a cut, at once: no picture of a tent with him behind it)
    hid_t_ = vis_t_ = 0;
    w_ = s.seen ? aim(s, also, zoom, mark_) : Window{};
    if (establish) {   // the whole picture first, held, then closing in on him
        w_ = Window{};
        hold_ = HOLD;
        settle_ = true;
    }
    shown_ = w_;
}

Window Operator::update(const Subject& s, const Extra& also, float push, float dt) {
    if (!s.seen) return shown_;   // (behind the camera: stay put)
    // Hidden for a moment (a lamp post, a tree he walks past) changes nothing; hidden for a while,
    // the window opens to the whole picture, and closes in again once he's been in sight a while.
    hid_t_ = s.hidden ? hid_t_ + dt : 0;
    vis_t_ = s.hidden ? 0 : vis_t_ + dt;
    if (!lost_ && hid_t_ >= LOST_T) lost_ = true;
    if (lost_ && vis_t_ >= LOST_T) lost_ = false;
    Subject held = s;
    held.hidden = lost_;
    const Window t = aim(held, also, zoom_, mark_);
    if (hold_ > 0) {
        hold_ -= dt;
    } else {
        const float tp = settle_ ? SETTLE_T : PAN_T, th = settle_ ? SETTLE_T : ZOOM_T;
        w_.cx = damp(w_.cx, t.cx, vx_, tp, dt);
        w_.cy = damp(w_.cy, t.cy, vy_, tp, dt);
        w_.h = damp(w_.h, t.h, vh_, th, dt);
        if (settle_) {
            settle_t_ += dt;
            const bool there = std::fabs(w_.h - t.h) < 0.01f && std::fabs(w_.cx - t.cx) < 0.01f && std::fabs(w_.cy - t.cy) < 0.01f;
            if (there || settle_t_ > 2.5f) settle_ = false;
        }
    }
    w_.h = std::clamp(w_.h, 1.0f / ZMAX, 1.0f);
    keep_inside(w_);
    shown_ = w_;
    if (push > 1.0001f) {   // in on him at once, about where he is on the screen (he stays put on it)
        const float a = std::max(s.feet.y - s.head.y, 1e-3f);
        const float h = std::min(w_.h, std::max({w_.h / push, 1.0f / ZPUSH, a / 0.95f}));
        const float k = 1.0f - h / w_.h;
        const Vector2 c{(s.feet.x + s.head.x) * 0.5f, (s.feet.y + s.head.y) * 0.5f};
        shown_ = {w_.cx + (c.x - w_.cx) * k, w_.cy + (c.y - w_.cy) * k, h};
        keep_inside(shown_);
    }
    return shown_;
}

}  // namespace dw::framing
