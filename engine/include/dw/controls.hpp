// damned_waters/engine/include/dw/controls.hpp
// Purpose: the player's hands as pure rules. The game asks for ACTIONS ("dodge", "aim"),
// never for keys, so a controller layout (Type A, B, C), the keyboard and mouse, or a console's
// own pad API only decide which button that is. Here: the actions, the three controller
// layouts, the keyboard/mouse layout, and the stick maths that make an analog stick feel right
// (dead zones, sneak / walk / run by how hard it's pushed and the run options, a flick to switch
// targets, the stick as a cursor over a body, stick back + the right face button to turn round).
// No window, no polling: input.cpp reads the hardware and feeds these. Unit-tested in
// tests/test_controls.cpp.
// Think of a layout as a keyboard layout for your thumbs: the letters (actions) don't change,
// only where they sit.
#ifndef DW_CONTROLS_HPP
#define DW_CONTROLS_HPP
#include <raylib.h>
#include <algorithm>
#include <cmath>

namespace dw {

enum Act : int {
    ACT_AIM, ACT_FIRE, ACT_DODGE, ACT_INTERACT, ACT_KICK, ACT_QUICK_TURN, ACT_RELOAD, ACT_STATUS,
    ACT_FLASHLIGHT, ACT_WEAPON_NEXT, ACT_WEAPON_1, ACT_WEAPON_2, ACT_RUN, ACT_PAUSE, ACT_CONFIRM, ACT_BACK,
    ACT_SNEAK,        // the keys' sneak (a pad sneaks with a light touch of the stick)
    ACT_RUN_HOLD,     // run while held (the "hold a button" run option); ACT_RUN is the stick click
    ACT_BACK_TURN,    // with the stick pulled back: a quick turn (an option; the button may also dodge)
    ACT_COUNT
};
enum class Scheme : int { TypeA, TypeB, TypeC, Count };

inline const char* act_name(int a) {
    static const char* N[ACT_COUNT] = {"Aim", "Fire", "Dodge", "Interact", "Kick", "Quick turn", "Reload", "Status",
                                       "Flashlight", "Next weapon", "M92FS", "Remington 870", "Run", "Pause", "Confirm", "Back",
                                       "Sneak", "Run (hold)", "Back + turn"};
    return a >= 0 && a < ACT_COUNT ? N[a] : "";
}
inline const char* scheme_name(Scheme s) {
    switch (s) {
        case Scheme::TypeA: return "Type A (RE Remake)";
        case Scheme::TypeB: return "Type B (Souls)";
        case Scheme::TypeC: return "Type C (Shooter)";
        default: return "";
    }
}

// Pad buttons by POSITION (raylib's names): the bottom face button is Cross on PlayStation, A on
// Xbox and B on Switch, the same spot under the thumb on every pad. 0 = not bound.
inline int pad_button(Scheme s, int act) {
    constexpr int L1 = GAMEPAD_BUTTON_LEFT_TRIGGER_1, L2 = GAMEPAD_BUTTON_LEFT_TRIGGER_2, R1 = GAMEPAD_BUTTON_RIGHT_TRIGGER_1,
                  R2 = GAMEPAD_BUTTON_RIGHT_TRIGGER_2, CROSS = GAMEPAD_BUTTON_RIGHT_FACE_DOWN, CIRCLE = GAMEPAD_BUTTON_RIGHT_FACE_RIGHT,
                  SQUARE = GAMEPAD_BUTTON_RIGHT_FACE_LEFT, TRIANGLE = GAMEPAD_BUTTON_RIGHT_FACE_UP, UP = GAMEPAD_BUTTON_LEFT_FACE_UP,
                  DOWN = GAMEPAD_BUTTON_LEFT_FACE_DOWN, LEFT = GAMEPAD_BUTTON_LEFT_FACE_LEFT, RIGHT = GAMEPAD_BUTTON_LEFT_FACE_RIGHT,
                  SELECT = GAMEPAD_BUTTON_MIDDLE_LEFT, START = GAMEPAD_BUTTON_MIDDLE_RIGHT, L3 = GAMEPAD_BUTTON_LEFT_THUMB;
    // Aim Fire Dodge Interact Kick QuickTurn Reload Status Flashlight WeaponNext Weapon1 Weapon2 Run Pause Confirm Back,
    // then Sneak RunHold BackTurn. Every comfortable button is already taken in every layout, so the
    // hold-to-run button is the one that fires: it fires only while aiming, and aiming stops him, so
    // running and firing never want it at the same time. Back + turn is the right face button
    // (Circle / B) on every pad.
    static const int T[int(Scheme::Count)][ACT_COUNT] = {
        // Type A, RE Remake: triggers aim and fire, R1 dodges, Cross does what's in front of you.
        {L2, R2, R1, CROSS, CROSS, CIRCLE, SQUARE, TRIANGLE, L1, UP, LEFT, RIGHT, L3, START, CROSS, CIRCLE, 0, R2, CIRCLE},
        // Type B, Souls: a roll on Circle, shoulders aim and fire, Square kicks.
        {L1, R1, CIRCLE, CROSS, SQUARE, R2, TRIANGLE, SELECT, L2, UP, LEFT, RIGHT, L3, START, CROSS, CIRCLE, 0, R1, CIRCLE},
        // Type C, shooter (The Last of Us): triggers aim and fire, R1 reloads, Circle dodges, Square kicks.
        {L2, R2, CIRCLE, CROSS, SQUARE, L1, R1, SELECT, DOWN, TRIANGLE, LEFT, RIGHT, L3, START, CROSS, CIRCLE, 0, R2, CIRCLE},
    };
    return (int(s) >= 0 && s < Scheme::Count && act >= 0 && act < ACT_COUNT) ? T[int(s)][act] : 0;
}

// A pad button's name for on-screen help, PlayStation first (Xbox letter after the face buttons).
inline const char* pad_button_name(int b) {
    switch (b) {
        case GAMEPAD_BUTTON_RIGHT_FACE_DOWN: return "Cross/A";
        case GAMEPAD_BUTTON_RIGHT_FACE_RIGHT: return "Circle/B";
        case GAMEPAD_BUTTON_RIGHT_FACE_LEFT: return "Square/X";
        case GAMEPAD_BUTTON_RIGHT_FACE_UP: return "Triangle/Y";
        case GAMEPAD_BUTTON_LEFT_TRIGGER_1: return "L1";
        case GAMEPAD_BUTTON_LEFT_TRIGGER_2: return "L2";
        case GAMEPAD_BUTTON_RIGHT_TRIGGER_1: return "R1";
        case GAMEPAD_BUTTON_RIGHT_TRIGGER_2: return "R2";
        case GAMEPAD_BUTTON_LEFT_FACE_UP: return "D-pad up";
        case GAMEPAD_BUTTON_LEFT_FACE_DOWN: return "D-pad down";
        case GAMEPAD_BUTTON_LEFT_FACE_LEFT: return "D-pad left";
        case GAMEPAD_BUTTON_LEFT_FACE_RIGHT: return "D-pad right";
        case GAMEPAD_BUTTON_MIDDLE_LEFT: return "Share/View";
        case GAMEPAD_BUTTON_MIDDLE_RIGHT: return "Options/Menu";
        case GAMEPAD_BUTTON_LEFT_THUMB: return "L3";
        case GAMEPAD_BUTTON_RIGHT_THUMB: return "R3";
        default: return "-";
    }
}

// Keyboard and mouse: one layout, whatever the pad scheme. Two keys each (0: none); the mouse
// buttons aim and fire.
struct KeyPair { int a, b; };
inline KeyPair key_binding(int act) {
    static const KeyPair T[ACT_COUNT] = {
        {KEY_K, 0},                      // aim (and the right mouse button)
        {KEY_J, 0},                      // fire (and the left mouse button)
        {KEY_SPACE, KEY_C},              // dodge
        {KEY_E, KEY_ENTER},              // interact
        {KEY_E, 0},                      // kick (E does what's in front of you)
        {KEY_Q, 0},                      // quick turn
        {KEY_R, 0},                      // reload
        {KEY_TAB, KEY_I},                // status screen
        {KEY_L, 0},                      // flashlight
        {KEY_F, 0},                      // next weapon
        {KEY_ONE, 0},                    // M92FS
        {KEY_TWO, 0},                    // Remington 870
        {KEY_LEFT_SHIFT, KEY_RIGHT_SHIFT},   // run (hold)
        {KEY_ESCAPE, KEY_P},             // pause
        {KEY_ENTER, KEY_E},              // confirm (menus)
        {KEY_ESCAPE, KEY_BACKSPACE},     // back (menus)
        {KEY_LEFT_CONTROL, KEY_RIGHT_CONTROL},   // sneak (hold)
        {KEY_LEFT_SHIFT, KEY_RIGHT_SHIFT},   // run (hold): the keys walk unless told, whatever the run option
        {0, 0},                          // back + turn: a pad's (the keys have Q)
    };
    return act >= 0 && act < ACT_COUNT ? T[act] : KeyPair{0, 0};
}

// The keys have no pressure, so they hand the game the tilt of the gait they ask for: Ctrl sneaks,
// Shift runs (Shift wins if both are down: fleeing comes first), neither walks.
constexpr float KEY_TILT_SNEAK = 0.25f, KEY_TILT_WALK = 0.6f, KEY_TILT_RUN = 1.0f;

// ── Sticks ───────────────────────────────────────────────────────────────────────
// A radial dead zone: nothing inside `inner` (a resting stick drifts), then rescaled so the
// stick's full throw still reaches 1 and a gentle push starts from zero, not from a jump.
inline Vector2 radial_deadzone(Vector2 v, float inner = 0.18f, float outer = 0.95f) {
    const float m = std::sqrt(v.x * v.x + v.y * v.y);
    if (m <= inner) return {0, 0};
    const float k = std::clamp((m - inner) / (outer - inner), 0.0f, 1.0f) / m;
    return {v.x * k, v.y * k};
}

// ── Gaits: sneak, walk, run ──────────────────────────────────────────────────────
// Think of a dimmer with three clicks instead of a slide: a light touch of the stick sneaks (slow,
// and so quiet a Drowned has to be at arm's length to hear him), half way walks, all the way runs.
enum class Gait : int { Still, Sneak, Walk, Run };
constexpr float SNEAK_SPEED = 0.8f, WALK_SPEED = 1.9f, RUN_SPEED = 3.8f;   // m/s
inline float gait_speed(Gait g) {
    return g == Gait::Sneak ? SNEAK_SPEED : g == Gait::Walk ? WALK_SPEED : g == Gait::Run ? RUN_SPEED : 0.0f;
}

// A footstep at each gait: one every `stride` metres, this loud (0..1), heard by every Drowned
// within `radius` metres. Standing still gets the walk's (the last step of a stop).
struct Footfall { float stride, volume, radius; };
inline Footfall footfall(Gait g) {
    switch (g) {
        case Gait::Sneak: return {0.45f, 0.15f, 1.0f};   // short steps, placed: all but silent
        case Gait::Run: return {0.85f, 0.8f, 6.0f};      // carries across the hall
        default: return {0.62f, 0.5f, 2.5f};
    }
}

// The gait a tilt asks for (the tilt after the dead zone, 0..1). A boundary is crossed going up at
// its threshold and going down only BAND below it (hysteresis), so a thumb resting on a boundary
// doesn't flicker between two gaits. Over the stick's raw throw that's a sneak from about a quarter
// of the way, a walk from about half, and a run from about seven-eighths (which a thumb pushing
// "all the way" always reaches).
struct TiltTiers {
    static constexpr float SNEAK = 0.08f, WALK = 0.40f, RUN = 0.88f, BAND = 0.06f;
    Gait g = Gait::Still;
    Gait update(float tilt) {
        const float up[3] = {SNEAK, WALK, RUN};   // into Sneak, Walk, Run
        int t = int(g);
        while (t < 3 && tilt >= up[t]) ++t;
        while (t > 0 && tilt < up[t - 1] - BAND) --t;
        return g = Gait(t);
    }
};

// How running is asked for (an option). Analog: by the tilt alone. The others walk at full tilt and
// run on a button: the stick clicked in (L3) and held; clicked once, running until the stick comes
// back to centre (or it's clicked again); or the layout's hold-to-run button (ACT_RUN_HOLD) held.
// In every one a light touch still sneaks. The keys ignore the option: they walk, Shift runs.
enum class RunMode : int { Analog, StickHold, StickToggle, HoldButton, Count };
inline const char* run_mode_name(RunMode m) {   // (the menu adds the hold-to-run button's name)
    switch (m) {
        case RunMode::Analog: return "Push the stick all the way";
        case RunMode::StickHold: return "Walk; hold the stick in (L3)";
        case RunMode::StickToggle: return "Walk; click the stick (L3) on and off";
        case RunMode::HoldButton: return "Walk; hold";
        default: return "";
    }
}

struct GaitPicker {
    TiltTiers tiers;
    bool latched = false;   // StickToggle: clicked into a run
    // tilt: how far the stick is pushed (0..1, after the dead zone; the keys give KEY_TILT_*).
    // keys: it's the keys moving him. click: the stick clicked in this frame; click_held: held in;
    // button: the hold-to-run button held. Called every frame, whatever he's doing.
    Gait update(float tilt, bool keys, RunMode mode, bool click, bool click_held, bool button) {
        const Gait was = tiers.g, felt = tiers.update(tilt);
        if (mode == RunMode::StickToggle && click) latched = !latched;
        if (felt == Gait::Still && was != Gait::Still) latched = false;   // the stick back at centre: the run ends
        if (keys || mode == RunMode::Analog || felt <= Gait::Sneak) return felt;
        const bool run = mode == RunMode::StickHold ? click_held : mode == RunMode::StickToggle ? latched : button;
        return run ? Gait::Run : Gait::Walk;
    }
};

// Moving a velocity toward a target by at most `step` (m/s): speeding up and slowing down take a
// few frames, not zero, so he has weight without feeling sluggish.
inline Vector2 approach(Vector2 v, Vector2 target, float step) {
    const float dx = target.x - v.x, dz = target.y - v.y, d = std::sqrt(dx * dx + dz * dz);
    if (d <= step || d < 1e-6f) return target;
    return {v.x + dx / d * step, v.y + dz / d * step};
}

// A flick of the right stick while locked on: pushed hard sideways and let go at once. Returns
// -1 (left) or +1 (right) on the frame it's released, else 0. Held longer, it isn't a flick: the
// stick is aiming at an arm.
struct FlickDetector {
    static constexpr float HARD = 0.85f, RELEASED = 0.3f, QUICK = 0.22f;
    bool armed = false;
    float t = 0, dir = 0;
    int update(Vector2 look, float dt) {
        const float m = std::sqrt(look.x * look.x + look.y * look.y);
        if (!armed) {
            if (m > HARD && std::fabs(look.x) > 0.7f * m) { armed = true; t = 0; dir = look.x < 0 ? -1.0f : 1.0f; }
            return 0;
        }
        t += dt;
        if (m >= RELEASED) return 0;
        armed = false;
        return t <= QUICK ? int(dir) : 0;
    }
};

// Where on a locked-on body the gun points: the stick is a cursor over it. Centred: the chest.
// Up: the head. Sideways: the arm on that side of the screen. Down: the leg on that side.
// k: how far from the chest toward it (0..1), so a half push aims at the shoulder, not the hand.
enum class AimAt { Torso, Head, ArmLeft, ArmRight, LegLeft, LegRight };
struct BodyAim { AimAt at; float k; };
inline BodyAim body_aim(Vector2 look) {
    const float m = std::sqrt(look.x * look.x + look.y * look.y);
    if (m < 0.2f) return {AimAt::Torso, 0.0f};
    const float k = std::clamp((m - 0.2f) / 0.6f, 0.0f, 1.0f);
    const float up = look.y / m;                                     // +1 straight up, -1 straight down
    if (up > 0.7071f) return {AimAt::Head, k};
    if (up < -0.7071f) return {look.x < 0 ? AimAt::LegLeft : AimAt::LegRight, k};
    return {look.x < 0 ? AimAt::ArmLeft : AimAt::ArmRight, k};
}

// ── Stick back + the right face button: a quick turn ─────────────────────────────
// RE3's quick turn (an option): the stick pulled back, behind him, and the right face button
// (Circle / B). In Type B and C that button also dodges: alone, or with the stick pushed any other
// way, it still dodges; with the stick back it turns him round instead. Two thumbs never land on
// the same frame, so there's a grace window either way: the stick back a moment before the press
// (BEFORE), or getting there a moment after it (AFTER). In that second case the press waits, at
// most AFTER, and only while the stick is centred or on its way back; pushed any other way, it
// dodges at once. Like a doorbell that waits a beat to hear whether you're also knocking.
struct BackTurnChord {
    static constexpr float BEFORE = 0.10f, AFTER = 0.05f;   // seconds
    static constexpr float BACK = 0.35f;                     // how far back counts (tilt, after the dead zone)
    enum Out : int { NONE, DODGE, TURN };
    float since_back = 1e3f;   // seconds since the stick was last back
    float waiting = -1;        // a press waiting to see if the stick comes back: for how long (-1: none)
    // In his frame (x his right, y ahead of him): within 45 degrees of straight behind him.
    static bool back(Vector2 s) { return s.y <= -BACK && std::fabs(s.x) <= -s.y; }
    static bool might_go_back(Vector2 s) { return s.x * s.x + s.y * s.y < BACK * BACK || (s.y < 0 && std::fabs(s.x) <= -s.y); }
    // stick: in his frame (stick_in_his_frame). pressed: the button went down this frame. active:
    // the chord applies right now (the option on, the button shared with the dodge, him free to
    // act); while it doesn't, a waiting press is dropped. Called every frame.
    int update(float dt, Vector2 stick, bool pressed, bool active) {
        const bool is_back = back(stick);
        since_back = is_back ? 0.0f : since_back + dt;
        if (!active) { waiting = -1; return NONE; }
        if (waiting >= 0) {
            waiting += dt;
            if (is_back) { waiting = -1; return TURN; }
            if (!might_go_back(stick) || waiting >= AFTER - 1e-4f) { waiting = -1; return DODGE; }
            return NONE;
        }
        if (!pressed) return NONE;
        if (since_back <= BEFORE) return TURN;
        if (might_go_back(stick)) { waiting = 0; return NONE; }
        return DODGE;
    }
};

// The stick as he feels it: x to his right, y ahead of him. Modern controls point the stick on the
// screen, so it's turned through the camera's forward on the floor (cam: x, z) into his facing
// (ahead: x, z); tank controls are his already. "Back" is then behind him whichever way he faces
// the camera, so after a quick turn the stick points where he now faces and he walks on.
inline Vector2 stick_in_his_frame(Vector2 stick, Vector2 cam, Vector2 ahead) {
    const float cl = std::sqrt(cam.x * cam.x + cam.y * cam.y), al = std::sqrt(ahead.x * ahead.x + ahead.y * ahead.y);
    if (cl < 1e-6f || al < 1e-6f) return stick;
    cam = {cam.x / cl, cam.y / cl};
    ahead = {ahead.x / al, ahead.y / al};
    const Vector2 d{-cam.y * stick.x + cam.x * stick.y, cam.x * stick.x + cam.y * stick.y};   // screen right * x + forward * y
    return {-ahead.y * d.x + ahead.x * d.y, ahead.x * d.x + ahead.y * d.y};
}

// The layout's dodge is the back-turn button (Type B, C), so the chord has to tell them apart. In
// Type A that button quick-turns on its own already.
inline bool back_turn_shares_dodge(Scheme s) { return pad_button(s, ACT_DODGE) == pad_button(s, ACT_BACK_TURN); }

}  // namespace dw
#endif
