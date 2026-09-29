// damned_waters/engine/include/dw/controls.hpp
// Purpose: the player's hands as pure rules. The game asks for ACTIONS ("dodge", "aim"),
// never for keys, so a controller layout (Type A, B, C), the keyboard and mouse, or a console's
// own pad API only decide which button that is. Here: the actions, the three controller
// layouts, the keyboard/mouse layout, and the stick maths that make an analog stick feel right
// (dead zones, walk-to-run, a flick to switch targets, the stick as a cursor over a body).
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
    ACT_COUNT
};
enum class Scheme : int { TypeA, TypeB, TypeC, Count };

inline const char* act_name(int a) {
    static const char* N[ACT_COUNT] = {"Aim", "Fire", "Dodge", "Interact", "Kick", "Quick turn", "Reload", "Status",
                                       "Flashlight", "Next weapon", "M92FS", "Remington 870", "Run", "Pause", "Confirm", "Back"};
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
    // Aim Fire Dodge Interact Kick QuickTurn Reload Status Flashlight WeaponNext Weapon1 Weapon2 Run Pause Confirm Back
    static const int T[int(Scheme::Count)][ACT_COUNT] = {
        // Type A, RE Remake: triggers aim and fire, R1 dodges, Cross does what's in front of you.
        {L2, R2, R1, CROSS, CROSS, CIRCLE, SQUARE, TRIANGLE, L1, UP, LEFT, RIGHT, L3, START, CROSS, CIRCLE},
        // Type B, Souls: a roll on Circle, shoulders aim and fire, Square kicks.
        {L1, R1, CIRCLE, CROSS, SQUARE, R2, TRIANGLE, SELECT, L2, UP, LEFT, RIGHT, L3, START, CROSS, CIRCLE},
        // Type C, shooter (The Last of Us): triggers aim and fire, R1 reloads, Circle dodges, Square kicks.
        {L2, R2, CIRCLE, CROSS, SQUARE, L1, R1, SELECT, DOWN, TRIANGLE, LEFT, RIGHT, L3, START, CROSS, CIRCLE},
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
    };
    return act >= 0 && act < ACT_COUNT ? T[act] : KeyPair{0, 0};
}

// ── Sticks ───────────────────────────────────────────────────────────────────────
// A radial dead zone: nothing inside `inner` (a resting stick drifts), then rescaled so the
// stick's full throw still reaches 1 and a gentle push starts from zero, not from a jump.
inline Vector2 radial_deadzone(Vector2 v, float inner = 0.18f, float outer = 0.95f) {
    const float m = std::sqrt(v.x * v.x + v.y * v.y);
    if (m <= inner) return {0, 0};
    const float k = std::clamp((m - inner) / (outer - inner), 0.0f, 1.0f) / m;
    return {v.x * k, v.y * k};
}

// How fast a stick tilt moves him: a creep to a walk over the first 60% of the throw, walk to
// run over the rest (so you can walk without a button, and run by pushing all the way).
inline float stick_speed(float tilt, float walk, float run) {
    tilt = std::clamp(tilt, 0.0f, 1.0f);
    return tilt <= 0.6f ? walk * tilt / 0.6f : walk + (run - walk) * (tilt - 0.6f) / 0.4f;
}

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

}  // namespace dw
#endif
