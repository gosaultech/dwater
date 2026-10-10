// damned_waters/engine/include/dw/status.hpp
// Purpose: the status screen (Tab / the View button) as pure rules: how he's doing (his condition,
// read from his health but never shown as a number), what each item in the case can be made to
// do, loading spare rounds from the case into a gun, what the world remembers (pickups taken,
// items dropped, notes read, rooms seen), and the screen itself as a small state machine: tabs,
// the cursor over the case, the action list, combining, examining, discarding, reading, picking
// something up and making room for it. No drawing and no input polling: the game feeds it a
// frame's buttons and carries out what it asks for (status_view.cpp draws it). Unit-tested in
// tests/test_status.cpp.
//
// Like a waiter taking an order: it only writes down what you asked for (equip this, use that,
// take it); the kitchen (Game) cooks it and tells it how it went.
#ifndef DW_STATUS_HPP
#define DW_STATUS_HPP
#include <set>
#include <string>
#include <vector>

#include "dw/combat.hpp"

namespace dw::status {

// ── How he's doing ───────────────────────────────────────────────────────────
// The bands are combat.hpp's (dw::condition, the same ones his limp follows), shown as the
// classics show them: a trace on a heart monitor, its colour and a word. The thresholds stay
// inside the game: the player reads his state, not a number.
const char* condition_name(Condition c);
// His pulse (beats a minute) for the monitor's trace: calm when he's whole, racing when he's not.
float heart_rate(float hp);

// ── What an item can do ────────────────────────────────────────────────────────
enum class Action { Equip, Use, Combine, Examine, Discard };
const char* action_name(Action a);
constexpr int MAX_ACTIONS = 5;
// The actions offered for `item` (in the order shown). `in_hand`: it's the gun he's holding (no
// Equip). Guns: Equip, Combine (with their rounds), Examine. Rounds: Combine, Examine, Discard.
// Medicine: Use, Examine, Discard. A key: Examine (it's used at its door). Returns how many.
int actions_for(int item, bool in_hand, Action* out);
// Guns and keys stay in the case: dropping either could leave the game unwinnable.
bool can_discard(int item);
// Which gun (Weapon) a box of rounds feeds, or -1.
int gun_for_ammo(int item);
// Can these two be combined (either way round): rounds into the gun they fit.
bool can_combine(int a, int b);
// Load the gun from the case, as far as it takes and the case has: returns how many went in (the
// case gives them up). A tube gun is topped up at once here; time stands still in the case.
int load_from_case(Inventory& inv, Firearm& gun);

// ── What the world remembers ──────────────────────────────────────────────────
struct Dropped { std::string room; int item, count; float x, z; };   // left on the floor, to make room
struct WorldState {
    std::set<std::string> taken;      // "room/id": picked up for good (the rest of a stack stays in `left`)
    std::vector<std::pair<std::string, int>> left;   // "room/id" -> how many are still there, after taking some
    std::vector<Dropped> dropped;
    std::vector<std::string> notes;   // the notes read, in order found ("room/id")
    std::set<std::string> visited;    // rooms he's been in
    std::set<std::string> unlocked;   // "room/id" doors opened with their key
    std::set<std::string> flags;      // what has happened ("heard_thud": the key taken, the bang at the door)
    std::set<std::string> dead;       // "room/id": the Drowned put down for good
    static std::string key(const std::string& room, const std::string& id) { return room + "/" + id; }
    bool has_flag(const std::string& f) const { return flags.count(f) > 0; }
    bool has_note(const std::string& k) const;
    // How many of a room's pickup are still there (it started with `count`).
    int remaining(const std::string& k, int count) const;
    void set_remaining(const std::string& k, int n);
};

// ── The screen ──────────────────────────────────────────────────────────────────
enum class Tab { Items, Files, Map };
constexpr int TABS = 3;
const char* tab_name(Tab t);
enum class Mode {
    Browse,     // the cursor over the tab's contents
    Actions,    // the action list open on an item
    Combine,    // choosing what to combine the item with
    Examine,    // the item turning big on screen, its description
    Discard,    // "Leave it here?"
    Read,       // a note full screen
    Pickup,     // something found: "Take it? / Leave it"
    NoRoom,     // the case is full: "Make room / Leave it"
    MakeRoom,   // the case open to drop something for it
};
// One frame's buttons, as the screen reads them.
struct Pad {
    int dx = 0, dy = 0;          // the d-pad or the stick: -1/+1 on the frame it's pushed (dy +1 is up)
    bool confirm = false, back = false;
    bool combine = false;        // straight to combining (Square / X)
    bool examine = false;        // straight to examining (Triangle / Y)
    int tab = 0;                 // L1 / R1: -1 / +1
};
// What the screen asks the game to do. `a`, `b`: case slots.
struct Command {
    enum Kind { None, Close, Equip, Use, Load, Discard, Take, Leave } kind = None;
    int a = -1, b = -1;
};
// What the screen wants heard: a click as the cursor moves, a confirmation, a step back, a refusal.
enum class Sound { None, Move, Confirm, Back, Deny };

class Screen {
public:
    static constexpr int COLS = 4;
    // Open on a tab, the cursor where it was.
    void open(Tab t = Tab::Items);
    // Something to pick up: `fits` how many of `count` the case would take.
    void open_pickup(int item, int count, int fits);
    void show_floor(int f) { floor_ = f; }   // the map's floor (as the game knows where he is)
    // A note just picked up: open on it, in Files, to read.
    void read(int file) { open_ = true; tab_ = Tab::Files; mode_ = Mode::Read; file_ = file; note_.clear(); }
    // The game tells it the case changed under it (after a Take or a Discard while making room).
    void pickup_fits(int fits) { fits_ = fits; }
    bool is_open() const { return open_; }
    // One frame. `in_hand`: the gun he holds (a Weapon), so it isn't offered to Equip; `files`:
    // how many notes there are; `floors`: how many floors the map has.
    Command update(const Pad& p, const Inventory& inv, int in_hand, int files, int floors);
    // Close at once (the game does this after Close, Take or Leave).
    void close() { open_ = false; mode_ = Mode::Browse; }

    Tab tab() const { return tab_; }
    Mode mode() const { return mode_; }
    int slot() const { return slot_; }              // the case slot under the cursor
    int action() const { return act_; }             // the highlighted action (Actions)
    int actions(Action* out) const { return n_acts_ ? (std::copy(acts_, acts_ + n_acts_, out), n_acts_) : 0; }
    int combine_from() const { return from_; }      // the item being combined (Combine)
    int file() const { return file_; }              // the note under the cursor (Files)
    int floor() const { return floor_; }            // the floor shown (Map)
    int choice() const { return choice_; }          // Pickup / NoRoom / Discard: 0 the first answer, 1 the second
    int pickup_item() const { return pick_item_; }
    int pickup_count() const { return pick_count_; }
    int pickup_fits() const { return fits_; }
    Sound sound() const { return sound_; }          // this frame's
    const std::string& note() const { return note_; }   // a line to show under the case ("That won't work.")

private:
    void refresh_actions(const Inventory& inv, int in_hand);
    void say(const std::string& s) { note_ = s; }
    bool open_ = false;
    Tab tab_ = Tab::Items;
    Mode mode_ = Mode::Browse;
    int slot_ = 0, act_ = 0, from_ = -1, file_ = 0, floor_ = 0, choice_ = 0;
    int pick_item_ = I_NONE, pick_count_ = 0, fits_ = 0;
    Action acts_[MAX_ACTIONS]{};
    int n_acts_ = 0;
    Sound sound_ = Sound::None;
    std::string note_;
};

}  // namespace dw::status
#endif
