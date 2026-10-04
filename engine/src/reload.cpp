// damned_waters/engine/src/reload.cpp
// Purpose: the steps of each reload (reload.hpp says what they mean). The M92FS's magazine change
// is the one taught for a fast reload: the support hand leaves the gun as the strong thumb drops
// the empty magazine, goes straight to the spare (his coat pocket), brings it up with the
// forefinger along its front, slides it up into the grip and slaps it home with the heel of the
// hand, then comes back onto the gun, its thumb sweeping the slide stop down on the way if the
// slide was locked open. The 870 is loaded a shell at a time from the same pocket: each pushed up
// through the loading port and thumbed home into the tube.
#include "dw/reload.hpp"

#include <algorithm>

namespace dw::reload {

int steps(Kind kind, bool from_grip, Step* out) {
    int n = 0;
    auto put = [&](float t, Place p, float along, Hand h, bool stop = true) { if (n < MAX_STEPS) out[n++] = {t, p, along, h, stop}; };
    if (kind == Kind::Magazine) {
        put(0.0f, Place::Grip, 0, Hand::Grip);
        put(0.3f, Place::Pocket, 0, Hand::Open);       // (the empty one falls at MAG_DROP, the hand already on its way)
        put(0.37f, Place::Pocket, 0, Hand::Hold);      // closed on the fresh one: out it comes
        put(0.45f, Place::Load, 170, Hand::Hold, false);  // out and turned upright on the way, lined up below the grip
        put(0.52f, Place::Load, 60, Hand::Hold, false);   // up under the grip
        put(0.6f, Place::Load, 12, Hand::Slap, false);    // in, the fingers opening off it
        put(MAG_HOME, Place::Load, 0, Hand::Slap);     // home, under the heel of the hand
        put(0.86f, Place::Grip, 0, Hand::Grip);        // back on the gun (the slide stop on the way)
        put(1.0f, Place::Grip, 0, Hand::Grip);
        return n;
    }
    // A shell: its own steps, squeezed into the first part of an empty gun's time.
    const float k = kind == Kind::ShellRack ? RACK_SHELL : 1.0f;
    if (from_grip) put(0.0f, Place::Grip, 0, Hand::Grip);
    else put(0.0f, Place::Load, 1, Hand::Push);           // where the last shell left it: the thumb in the port
    put(0.3f * k, Place::Pocket, 0, Hand::Open);
    put(0.38f * k, Place::Pocket, 0, Hand::Hold);
    put(0.66f * k, Place::Load, 0, Hand::Hold, false);    // under the port, nose up
    put(0.8f * k, Place::Load, 0.6f, Hand::Hold, false);  // the nose in, rising
    put(SHELL_LET_GO * k, Place::Load, 0.75f, Hand::Hold, false);   // level in the port
    put(1.0f * k, Place::Load, 1, Hand::Push);            // thumbed home
    if (kind == Kind::ShellRack) {
        put(RACK_BACK0, Place::Grip, 0, Hand::Grip);      // onto the fore-end (it racks under the hand)
        put(1.0f, Place::Grip, 0, Hand::Grip);
    }
    return n;
}

int segment(const Step* s, int n, float t, float& f) {
    if (n < 2) { f = 0; return 0; }
    t = std::clamp(t, s[0].t, s[n - 1].t);
    int i = 0;
    while (i < n - 2 && t > s[i + 1].t) ++i;
    const float span = s[i + 1].t - s[i].t;
    f = span > 1e-6f ? std::clamp((t - s[i].t) / span, 0.0f, 1.0f) : 1.0f;
    return i;
}

float shell_time(Kind kind, float t) {
    if (kind != Kind::ShellRack) return std::clamp(t, 0.0f, 1.0f);
    return std::min(1.0f, std::max(0.0f, t) / RACK_SHELL);
}

float pump(Kind kind, float t) {
    if (kind != Kind::ShellRack) return 0;
    auto ease = [](float a, float b, float x) {
        const float k = std::clamp((x - a) / (b - a), 0.0f, 1.0f);
        return k * k * (3 - 2 * k);
    };
    return t < RACK_HOME0 ? ease(RACK_BACK0, RACK_BACK1, t) : 1.0f - ease(RACK_HOME0, RACK_HOME1, t);
}

}  // namespace dw::reload
