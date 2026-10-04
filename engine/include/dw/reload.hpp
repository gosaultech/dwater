// damned_waters/engine/include/dw/reload.hpp
// Purpose: what the hands do in a reload, as numbers: where the support hand goes, what it holds,
// and when things happen, against how far the reload has got (0..1). The gun's rules (combat.hpp)
// say how long a reload takes and when the rounds count as in; this fits the hands' work into that
// time, so the magazine reaches the grip just as the gun counts it loaded and the shell is pushed
// home when the gun takes it. Character turns each moment into a pose (character.cpp); the timing
// is unit-tested without a window (tests/test_reload.cpp).
//
// Like dance notation: a list of steps, each a place for the hand and the moment it gets there;
// between steps the hand travels smoothly from one to the next, stopping only where a step says
// (reaching into the pocket, closing on what's in it, slapping the magazine home).
#ifndef DW_RELOAD_HPP
#define DW_RELOAD_HPP

namespace dw::reload {

// Where the support hand can be.
enum class Place : int {
    Grip,     // on the gun as it holds it to shoot: over the strong hand on the pistol, the 870's fore-end
    Pocket,   // in the left-hand pocket of his coat, where the spare magazine and the shells are
    Load,     // holding what it loads on its way in, `along` that way: the magazine, mm still out of
              // the grip (0: home); a shell, cast::shell_in's 0..1 (0.75: level in the port, 1: in the tube)
};
// What the fingers are doing.
enum class Hand : int {
    Grip,   // round the gun, as its grip has them
    Open,   // open, reaching
    Hold,   // closed on the magazine or the shell
    Push,   // the thumb pushing the shell home, the fingers coming off it
    Slap,   // flat, the fingers straight out: the heel of the hand seating the magazine (the fingers
            // come off it as it goes in, so they never run into the strong hand round the grip)
};
struct Step {
    float t;        // 0..1: when the hand gets there
    Place place;
    float along;    // (Load) how far along the way in
    Hand hand;
    bool stop;      // it stops there (to grab, to slap a magazine home); otherwise it carries on through
};

enum class Kind : int {
    Magazine,    // the M92FS: the empty magazine dropped, a fresh one from the pocket into the grip
    Shell,       // the 870: one shell from the pocket pushed up into the tube
    ShellRack,   // ... into an empty gun: then the hand goes to the fore-end and racks it into the chamber
};
constexpr int MAX_STEPS = 12;
// The steps of a reload. A shell's start from the fore-end (`from_grip`: the first shell, or the one
// after a rack) or from the loading port, where the shell before it left the hand. Returns how many.
int steps(Kind kind, bool from_grip, Step* out);
// Which pair of steps `t` falls between (out[i] to out[i + 1]) and how far from one to the other
// (`f`, 0..1, not eased).
int segment(const Step* s, int n, float t, float& f);

// When things happen, as fractions of the reload.
constexpr float MAG_DROP = 0.08f;      // the strong thumb on the release: the empty magazine falls
constexpr float MAG_GRAB = 0.335f;     // the hand closes on the fresh one in the pocket
constexpr float MAG_HOME = 0.645f;     // the heel of the hand slaps it home
constexpr float SLIDE_HOME = 0.8f;     // locked open (it was empty): the support thumb drops the slide stop
constexpr float DRIVE_OUT = 0.8f;      // from here the gun is pushed back out to the aim, the support hand rejoining it on the way
constexpr float SHELL_GRAB = 0.34f;    // (of a shell's own time) the fingers close on a shell in the pocket
constexpr float SHELL_LET_GO = 0.88f;  // level in the port: the fingers come off, the thumb pushes
constexpr float SHELL_HOME = 0.95f;    // it clicks past the shell latch into the tube
// An empty 870: the shell takes the first part of the time, then the hand racks the fore-end
// (back, a beat, and home), in step with the pump's sound (two clacks, 0.155 s apart).
constexpr float RACK_SHELL = 0.511f;
constexpr float RACK_BACK0 = 0.622f, RACK_BACK1 = 0.717f, RACK_HOME0 = 0.811f, RACK_HOME1 = 0.889f;
// (Kind::ShellRack) how far into the shell's own time the reload is at `t` (1 once it's in).
float shell_time(Kind kind, float t);
// (Kind::ShellRack) the fore-end's travel, 0 forward to 1 racked back, at `t`.
float pump(Kind kind, float t);

}  // namespace dw::reload

#endif
