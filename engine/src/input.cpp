// damned_waters/engine/src/input.cpp
// Purpose: see input.hpp. raylib names pad buttons by position and maps DualSense, Xbox and
// Switch Pro controllers through its bundled SDL controller database, so one table fits them all.
#include "input.hpp"

#include <cmath>
#include <string>

namespace dw {

InputFrame Input::poll() {
    InputFrame f;
    pad_ = -1;
    for (int i = 0; i < 4; ++i)
        if (IsGamepadAvailable(i)) { pad_ = i; break; }

    // Keyboard and mouse.
    bool kb_touched = false;
    Vector2 keys{float(IsKeyDown(KEY_D) || IsKeyDown(KEY_RIGHT)) - float(IsKeyDown(KEY_A) || IsKeyDown(KEY_LEFT)),
                 float(IsKeyDown(KEY_W) || IsKeyDown(KEY_UP)) - float(IsKeyDown(KEY_S) || IsKeyDown(KEY_DOWN))};
    const float kl = std::sqrt(keys.x * keys.x + keys.y * keys.y);
    if (kl > 0) {
        const bool run = IsKeyDown(KEY_LEFT_SHIFT) || IsKeyDown(KEY_RIGHT_SHIFT);
        keys = {keys.x / kl * (run ? 1.0f : 0.6f), keys.y / kl * (run ? 1.0f : 0.6f)};
        kb_touched = true;
    }
    for (int a = 0; a < ACT_COUNT; ++a) {
        const KeyPair k = key_binding(a);
        for (int key : {k.a, k.b}) {
            if (key == 0) continue;
            f.down[a] = f.down[a] || IsKeyDown(key);
            f.pressed[a] = f.pressed[a] || IsKeyPressed(key);
        }
    }
    f.down[ACT_AIM] = f.down[ACT_AIM] || IsMouseButtonDown(MOUSE_BUTTON_RIGHT);
    f.pressed[ACT_AIM] = f.pressed[ACT_AIM] || IsMouseButtonPressed(MOUSE_BUTTON_RIGHT);
    f.down[ACT_FIRE] = f.down[ACT_FIRE] || IsMouseButtonDown(MOUSE_BUTTON_LEFT);
    f.pressed[ACT_FIRE] = f.pressed[ACT_FIRE] || IsMouseButtonPressed(MOUSE_BUTTON_LEFT);
    f.mouse = GetMouseDelta();
    f.wheel = GetMouseWheelMove();
    for (int a = 0; a < ACT_COUNT; ++a) kb_touched = kb_touched || f.pressed[a];
    kb_touched = kb_touched || f.mouse.x * f.mouse.x + f.mouse.y * f.mouse.y > 4.0f;

    // The controller, in the chosen layout.
    bool pad_touched = false;
    Vector2 stick{};
    if (pad_ >= 0) {
        for (int a = 0; a < ACT_COUNT; ++a) {
            const int b = pad_button(scheme, a);
            if (b == 0) continue;
            const bool d = IsGamepadButtonDown(pad_, b), p = IsGamepadButtonPressed(pad_, b);
            f.down[a] = f.down[a] || d;
            f.pressed[a] = f.pressed[a] || p;
            pad_touched = pad_touched || p;
        }
        // Stick Y is down-positive in raylib: flip it so up is forward.
        stick = radial_deadzone({GetGamepadAxisMovement(pad_, GAMEPAD_AXIS_LEFT_X), -GetGamepadAxisMovement(pad_, GAMEPAD_AXIS_LEFT_Y)});
        f.look = radial_deadzone({GetGamepadAxisMovement(pad_, GAMEPAD_AXIS_RIGHT_X), -GetGamepadAxisMovement(pad_, GAMEPAD_AXIS_RIGHT_Y)});
        pad_touched = pad_touched || stick.x != 0 || stick.y != 0 || f.look.x != 0 || f.look.y != 0;
    }
    if (pad_touched) pad_active_ = true;
    else if (kb_touched) pad_active_ = false;
    f.pad = pad_active_ && pad_ >= 0;
    // Whichever is pushed further moves him (so a resting stick never fights the keys).
    f.move = (stick.x * stick.x + stick.y * stick.y) >= (keys.x * keys.x + keys.y * keys.y) ? stick : keys;

    // Menus: arrows, WASD, the d-pad, or the stick pushed past halfway (repeating while held).
    f.nav_y = int(IsKeyPressed(KEY_UP) || IsKeyPressed(KEY_W)) - int(IsKeyPressed(KEY_DOWN) || IsKeyPressed(KEY_S));
    f.nav_x = int(IsKeyPressed(KEY_RIGHT) || IsKeyPressed(KEY_D)) - int(IsKeyPressed(KEY_LEFT) || IsKeyPressed(KEY_A));
    if (pad_ >= 0) {
        f.nav_y += int(IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_LEFT_FACE_UP)) - int(IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_LEFT_FACE_DOWN));
        f.nav_x += int(IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_LEFT_FACE_RIGHT)) - int(IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_LEFT_FACE_LEFT));
    }
    const int sx = stick.x > 0.6f ? 1 : stick.x < -0.6f ? -1 : 0, sy = stick.y > 0.6f ? 1 : stick.y < -0.6f ? -1 : 0;
    if (sx != stick_x_ || sy != stick_y_) {
        if (sy != stick_y_ && sy) f.nav_y += sy;
        if (sx != stick_x_ && sx) f.nav_x += sx;
        repeat_ = 0.4f;
    } else if ((sx || sy) && (repeat_ -= GetFrameTime()) <= 0) {
        f.nav_y += sy;
        f.nav_x += sx;
        repeat_ = 0.13f;
    }
    stick_x_ = sx;
    stick_y_ = sy;
    f.ui_tab = int(IsKeyPressed(KEY_R)) - int(IsKeyPressed(KEY_Q));
    f.ui_combine = IsKeyPressed(KEY_C);
    f.ui_examine = IsKeyPressed(KEY_X);
    if (pad_ >= 0) {
        f.ui_tab += int(IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_RIGHT_TRIGGER_1)) - int(IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_LEFT_TRIGGER_1));
        f.ui_combine = f.ui_combine || IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_RIGHT_FACE_LEFT);
        f.ui_examine = f.ui_examine || IsGamepadButtonPressed(pad_, GAMEPAD_BUTTON_RIGHT_FACE_UP);
    }
    if (f.pad) {   // PlayStation pads name themselves; anything else gets Xbox letters
        const std::string name = GetGamepadName(pad_);
        const bool ps = name.find("PS") != std::string::npos || name.find("Sony") != std::string::npos || name.find("DualSense") != std::string::npos ||
                        name.find("DualShock") != std::string::npos || name.find("Wireless Controller") != std::string::npos;
        f.glyphs = ps ? 1 : 2;
    }
    f.nav_x = f.nav_x > 0 ? 1 : f.nav_x < 0 ? -1 : 0;
    f.nav_y = f.nav_y > 0 ? 1 : f.nav_y < 0 ? -1 : 0;
    return f;
}

void Input::rumble(float low, float high, float seconds) const {
#ifdef DW_RUMBLE   // defined once the desktop build runs on raylib's SDL backend
    if (pad_ >= 0) SetGamepadVibration(pad_, low, high, seconds);
#else
    (void)low; (void)high; (void)seconds;
#endif
}

}  // namespace dw
