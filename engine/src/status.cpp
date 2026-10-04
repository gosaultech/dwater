// damned_waters/engine/src/status.cpp
// Purpose: the status screen's rules (status.hpp says what each part is for).
#include "dw/status.hpp"

#include <algorithm>
#include <cmath>

namespace dw::status {

const char* condition_name(Condition c) {
    switch (c) {
        case Condition::Fine: return "FINE";
        case Condition::Caution: return "CAUTION";
        default: return "DANGER";
    }
}

float heart_rate(float hp) {
    const float k = 1.0f - std::clamp(hp / MAX_HEALTH, 0.0f, 1.0f);   // 0 whole .. 1 nearly gone
    return 70.0f + 70.0f * k * k * (3.0f - 2.0f * k);                   // 70 at rest, 140 at the end
}

const char* action_name(Action a) {
    switch (a) {
        case Action::Equip: return "Equip";
        case Action::Use: return "Use";
        case Action::Combine: return "Combine";
        case Action::Examine: return "Examine";
        default: return "Discard";
    }
}

const char* tab_name(Tab t) {
    switch (t) {
        case Tab::Items: return "ITEMS";
        case Tab::Files: return "FILES";
        default: return "MAP";
    }
}

namespace {
bool is_gun(int item) { return item == I_HANDGUN || item == I_SHOTGUN; }
int weapon_of(int item) { return item == I_HANDGUN ? int(Weapon::Pistol) : item == I_SHOTGUN ? int(Weapon::Shotgun) : -1; }
}  // namespace

int gun_for_ammo(int item) {
    for (int w = 0; w < int(Weapon::Count); ++w)
        if (weapon_spec(Weapon(w)).ammo == item) return w;
    return -1;
}

bool can_discard(int item) { return item != I_NONE && !is_gun(item) && item != I_CELLAR_KEY; }

bool can_combine(int a, int b) {
    auto fits = [](int ammo, int gun) { return is_gun(gun) && gun_for_ammo(ammo) == weapon_of(gun); };
    return fits(a, b) || fits(b, a);
}

int actions_for(int item, bool in_hand, Action* out) {
    int n = 0;
    auto add = [&](Action a) { if (n < MAX_ACTIONS) out[n++] = a; };
    if (item == I_NONE) return 0;
    if (is_gun(item)) {
        if (!in_hand) add(Action::Equip);
        add(Action::Combine);
        add(Action::Examine);
    } else if (gun_for_ammo(item) >= 0) {
        add(Action::Combine);
        add(Action::Examine);
        add(Action::Discard);
    } else if (is_medicine(item)) {
        add(Action::Use);
        add(Action::Examine);
        add(Action::Discard);
    } else {
        add(Action::Examine);
        if (can_discard(item)) add(Action::Discard);
    }
    return n;
}

int load_from_case(Inventory& inv, Firearm& gun) {
    const WeaponSpec& s = gun.spec();
    const int want = std::min(s.mag - gun.mag, inv.count_of(s.ammo));
    if (want <= 0) return 0;
    gun.stop_loading();   // (a tube that was being fed: it's full now)
    gun.reloading = 0;
    const int got = inv.remove(s.ammo, want);
    gun.mag += got;
    return got;
}

// ── What the world remembers ──────────────────────────────────────────────────
bool WorldState::has_note(const std::string& k) const { return std::find(notes.begin(), notes.end(), k) != notes.end(); }

int WorldState::remaining(const std::string& k, int count) const {
    if (taken.count(k)) return 0;
    for (const auto& [id, n] : left)
        if (id == k) return n;
    return count;
}

void WorldState::set_remaining(const std::string& k, int n) {
    if (n <= 0) {
        taken.insert(k);
        left.erase(std::remove_if(left.begin(), left.end(), [&](const auto& e) { return e.first == k; }), left.end());
        return;
    }
    for (auto& e : left)
        if (e.first == k) { e.second = n; return; }
    left.emplace_back(k, n);
}

// ── The screen ──────────────────────────────────────────────────────────────────
void Screen::open(Tab t) {
    open_ = true;
    tab_ = t;
    mode_ = Mode::Browse;
    from_ = -1;
    note_.clear();
}

void Screen::open_pickup(int item, int count, int fits) {
    open_ = true;
    tab_ = Tab::Items;
    mode_ = Mode::Pickup;
    choice_ = 0;
    pick_item_ = item;
    pick_count_ = count;
    fits_ = fits;
    note_.clear();
}

void Screen::refresh_actions(const Inventory& inv, int in_hand) {
    const int item = inv.slots[size_t(slot_)].item;
    const bool held = in_hand >= 0 && weapon_spec(Weapon(in_hand)).item == item;
    n_acts_ = actions_for(item, held, acts_);
    act_ = 0;
}

Command Screen::update(const Pad& p, const Inventory& inv, int in_hand, int files, int floors) {
    sound_ = Sound::None;
    Command c;
    if (!open_) return c;
    const int SLOTS = int(inv.slots.size());
    auto item_at = [&](int s) { return inv.slots[size_t(s)].item; };
    auto move_slot = [&] {   // the cursor over the case (dy +1 is up a row); true if it moved
        if (!p.dx && !p.dy) return false;
        slot_ = ((slot_ + p.dx - p.dy * COLS) % SLOTS + SLOTS) % SLOTS;
        sound_ = Sound::Move;
        note_.clear();
        return true;
    };
    auto toggle = [&] {   // a two-way choice: any direction flips it
        if (p.dx || p.dy) { choice_ ^= 1; sound_ = Sound::Move; }
    };
    auto deny = [&](const char* why) { sound_ = Sound::Deny; if (why) note_ = why; };

    switch (mode_) {
        case Mode::Browse:
            if (p.back) { sound_ = Sound::Back; c.kind = Command::Close; return c; }
            if (p.tab) {
                tab_ = Tab(((int(tab_) + p.tab) % TABS + TABS) % TABS);
                sound_ = Sound::Move;
                note_.clear();
                return c;
            }
            if (tab_ == Tab::Items) {
                if (move_slot()) return c;
                const int item = item_at(slot_);
                if (p.confirm) {
                    if (item == I_NONE) { deny(nullptr); return c; }
                    refresh_actions(inv, in_hand);
                    mode_ = Mode::Actions;
                    sound_ = Sound::Confirm;
                } else if (p.combine && item != I_NONE) {
                    from_ = slot_;
                    mode_ = Mode::Combine;
                    sound_ = Sound::Confirm;
                } else if (p.examine && item != I_NONE) {
                    mode_ = Mode::Examine;
                    sound_ = Sound::Confirm;
                }
            } else if (tab_ == Tab::Files) {
                if (p.dy && files > 0) {
                    const int f = std::clamp(file_ - p.dy, 0, files - 1);
                    if (f != file_) { file_ = f; sound_ = Sound::Move; }
                }
                if (p.confirm) {
                    if (files > 0) { mode_ = Mode::Read; sound_ = Sound::Confirm; }
                    else deny(nullptr);
                }
            } else {   // the map: up and down go between floors
                const int d = p.dy ? p.dy : p.dx;
                if (d && floors > 0) {
                    const int f = std::clamp(floor_ + d, 0, floors - 1);
                    if (f != floor_) { floor_ = f; sound_ = Sound::Move; }
                }
            }
            return c;

        case Mode::Actions:
            if (p.back) { mode_ = Mode::Browse; sound_ = Sound::Back; return c; }
            if (p.dy && n_acts_ > 0) { act_ = ((act_ - p.dy) % n_acts_ + n_acts_) % n_acts_; sound_ = Sound::Move; return c; }
            if (!p.confirm || n_acts_ == 0) return c;
            sound_ = Sound::Confirm;
            switch (acts_[act_]) {
                case Action::Equip: c = {Command::Equip, slot_}; mode_ = Mode::Browse; break;
                case Action::Use: c = {Command::Use, slot_}; mode_ = Mode::Browse; break;
                case Action::Combine: from_ = slot_; mode_ = Mode::Combine; break;
                case Action::Examine: mode_ = Mode::Examine; break;
                case Action::Discard: choice_ = 1; mode_ = Mode::Discard; break;   // "No" first: a slip of the thumb loses nothing
            }
            return c;

        case Mode::Combine:
            if (p.back) { slot_ = from_; mode_ = Mode::Browse; sound_ = Sound::Back; return c; }
            if (move_slot()) return c;
            if (!p.confirm) return c;
            if (slot_ != from_ && can_combine(item_at(from_), item_at(slot_))) {
                c = {Command::Load, from_, slot_};
                mode_ = Mode::Browse;
                sound_ = Sound::Confirm;
            } else {
                deny("That won't work.");
            }
            return c;

        case Mode::Examine:
        case Mode::Read:
            if (p.back || p.confirm) { mode_ = Mode::Browse; sound_ = Sound::Back; }
            return c;

        case Mode::Discard:
            if (p.back) { mode_ = pick_item_ != I_NONE ? Mode::MakeRoom : Mode::Browse; sound_ = Sound::Back; return c; }
            toggle();
            if (!p.confirm) return c;
            if (choice_ == 0) {
                c = {Command::Discard, slot_};
                sound_ = Sound::Confirm;
                mode_ = pick_item_ != I_NONE ? Mode::Pickup : Mode::Browse;   // made room: back to what he found
                choice_ = 0;
            } else {
                mode_ = pick_item_ != I_NONE ? Mode::MakeRoom : Mode::Browse;
                sound_ = Sound::Back;
            }
            return c;

        case Mode::Pickup:
            if (p.back) { c.kind = Command::Leave; sound_ = Sound::Back; pick_item_ = I_NONE; return c; }
            toggle();
            if (!p.confirm) return c;
            if (choice_ == 1) { c.kind = Command::Leave; sound_ = Sound::Back; pick_item_ = I_NONE; return c; }
            if (fits_ > 0) { c.kind = Command::Take; sound_ = Sound::Confirm; pick_item_ = I_NONE; return c; }
            mode_ = Mode::NoRoom;   // nowhere to put it
            choice_ = 0;
            sound_ = Sound::Deny;
            return c;

        case Mode::NoRoom:
            if (p.back) { mode_ = Mode::Pickup; choice_ = 0; sound_ = Sound::Back; return c; }
            toggle();
            if (!p.confirm) return c;
            if (choice_ == 1) { c.kind = Command::Leave; sound_ = Sound::Back; pick_item_ = I_NONE; return c; }
            mode_ = Mode::MakeRoom;
            tab_ = Tab::Items;
            sound_ = Sound::Confirm;
            return c;

        case Mode::MakeRoom:
            if (p.back) { mode_ = Mode::Pickup; choice_ = 0; sound_ = Sound::Back; return c; }
            if (move_slot()) return c;
            if (!p.confirm) return c;
            if (can_discard(item_at(slot_))) { choice_ = 1; mode_ = Mode::Discard; sound_ = Sound::Confirm; }
            else deny(item_at(slot_) == I_NONE ? nullptr : "You can't leave that behind.");
            return c;
    }
    return c;
}

}  // namespace dw::status
