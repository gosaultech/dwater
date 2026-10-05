// damned_waters/engine/src/input.hpp
// Purpose: the hardware, read once a frame and turned into actions (dw/controls.hpp). The first
// connected controller, in the chosen layout (Type A, B or C), and the keyboard and mouse work
// at the same time; whichever was touched last is "active". The game never sees a button or a
// key, only actions, so a console port replaces this file and nothing else.
#ifndef DW_INPUT_HPP
#define DW_INPUT_HPP
#include <raylib.h>

#include "dw/controls.hpp"

namespace dw {

struct InputFrame {
    Vector2 move{};                          // left stick or WASD: x right, y forward; length 0..1
                                             // (the keys give the tilt of their gait: 0.6 walks, Ctrl 0.25 sneaks, Shift 1 runs)
    bool move_keys = false;                  // ... and it's the keys moving him (no pressure: the run option doesn't apply)
    Vector2 look{};                          // right stick: x right, y up; where it's held, 0..1
    Vector2 mouse{};                         // mouse movement this frame (pixels)
    float wheel = 0;                         // mouse wheel this frame
    bool down[ACT_COUNT]{}, pressed[ACT_COUNT]{};
    bool pad = false;                        // the controller is what's being played with right now
    int nav_x = 0, nav_y = 0;                // menus: -1/+1 on the frame a direction is pushed (repeats while held)
    // The status screen's own buttons, by position on any pad (and their keys): the shoulders
    // change tab (L1 / R1; Q / R), the left face button combines (Square / X; C), the top one
    // examines (Triangle / Y; X).
    int ui_tab = 0;
    bool ui_combine = false, ui_examine = false;
    // Which buttons to draw for help: 0 the keyboard, 1 a PlayStation pad, 2 an Xbox (or any other) pad.
    int glyphs = 0;
    bool held(int a) const { return down[a]; }
    bool hit(int a) const { return pressed[a]; }
};

class Input {
public:
    InputFrame poll();                       // once a frame, before anything reads input
    // A buzz in the controller's two motors (0..1), for shots, bites and a perfect dodge. The
    // GLFW desktop backend has no rumble, so this does nothing until the SDL3 switch.
    void rumble(float low, float high, float seconds) const;
    Scheme scheme = Scheme::TypeA;
    bool has_pad() const { return pad_ >= 0; }

private:
    int pad_ = -1;                           // which controller (-1: none connected)
    bool pad_active_ = false;
    int stick_x_ = 0, stick_y_ = 0;          // the left stick as a menu direction last frame
    float repeat_ = 0;                       // time to the next repeat while it's held
};

}  // namespace dw
#endif
