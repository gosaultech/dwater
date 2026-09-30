// damned_waters/engine/include/dw/combat.hpp
// Purpose: combat as pure rules, with no rendering, input or sound, ported from the Godot demo
// (WeaponDB, Firearm, ItemDB, Inventory, EnemyBrain.take_hit) and extended with RE2-Remake-style
// dismemberment: a Drowned comes apart region by region (anatomy.hpp).
// Health is one scale for everybody: the survivor has 100, a Drowned 60, a 9 mm round does 10.
// Everything here is header-only and allocation-free, so it's unit-tested without a window
// (tests/test_combat.cpp) and costs nothing per frame.
// Think of it as the rulebook of a board game: the game loop moves the pieces and draws them,
// this file only says what a move does.
#ifndef DW_COMBAT_HPP
#define DW_COMBAT_HPP
#include <algorithm>
#include <array>
#include <cmath>

#include "dw/anatomy.hpp"
#include "dw/core.hpp"

namespace dw {

// ── Items: what fits in the case, and how much of it stacks ────────────────────
enum Item : int { I_NONE, I_HANDGUN, I_HANDGUN_AMMO, I_SHOTGUN, I_SHELLS, I_MED_S, I_MED_M, I_MED_L, I_CELLAR_KEY, I_COUNT };
struct ItemSpec {
    const char* key;    // the id the room data uses ("shotgun_shells")
    const char* name;   // what the status screen shows
    int max_stack;
    int heal;           // health restored when used (0: not a medicine; 100 = back to full)
    const char* desc;
};
inline const ItemSpec& item_spec(int i) {
    static const ItemSpec T[I_COUNT] = {
        {"", "", 0, 0, ""},
        {"handgun", "M92FS", 1, 0,
         "A Beretta M92FS Inox, stainless steel. Police issue: you took it from an officer on the Herengracht. She won't need it."},
        {"handgun_ammo", "9mm Rounds", 60, 0, "Pistol ammunition. Make every one count."},
        {"shotgun", "Remington 870", 1, 0,
         "An old Remington 870 police gun, walnut and blued steel: pump action, six in the tube and one in the chamber. "
         "From the rack of a police van nose-down in the Prinsengracht."},
        {"shotgun_shells", "Shotgun Shells", 30, 0, "12-gauge buckshot. At close range it puts anything down."},
        // Med kits: one to a slot, used from the case (time stands still). Nothing else heals.
        {"med_small", "Field Dressing", 1, 30, "A pressure bandage in a paper wrapper. Stops the worst of it. Restores some health."},
        {"first_aid", "EHBO Kit", 1, 60, "A Dutch first aid kit: bandages, antiseptic, a foil blanket. Restores a lot of health."},
        {"med_large", "EHBO Case", 1, 100,
         "The big green case off a pharmacy wall: splints, sutures, painkillers. Restores all of your health."},
        {"cellar_key", "Cellar Key", 1, 0, "A heavy iron key, green with verdigris. The paper tag reads 'KELDER'."},
    };
    return T[(i > I_NONE && i < I_COUNT) ? i : I_NONE];
}

// ── Health ───────────────────────────────────────────────────────────────────────
// The survivor's tank holds 100. It never refills by itself: only med kits heal (S 30, M 60, L all).
constexpr float MAX_HEALTH = 100.0f;
inline bool is_medicine(int item) { return item_spec(item).heal > 0; }
inline float healed(float hp, int item) { return std::min(MAX_HEALTH, hp + float(item_spec(item).heal)); }
inline int item_by_key(const char* key) {   // the room data names items by key
    for (int i = I_NONE + 1; i < I_COUNT; ++i) {
        const char *a = item_spec(i).key, *b = key;
        while (*a && *a == *b) { ++a; ++b; }
        if (*a == *b) return i;
    }
    return I_NONE;
}

// Eight slots, one stack each. Scarce slots are a design lever of classic survival horror, so the
// model enforces them.
struct Slot { int item = I_NONE, count = 0; };
struct Inventory {
    std::array<Slot, 8> slots{};
    int add(int item, int count) {   // returns how many did NOT fit
        const int cap = item_spec(item).max_stack;
        for (auto& s : slots)
            if (count > 0 && s.item == item && s.count < cap) { const int put = std::min(cap - s.count, count); s.count += put; count -= put; }
        for (auto& s : slots)
            if (count > 0 && s.item == I_NONE) { const int put = std::min(cap, count); s = {item, put}; count -= put; }
        return count;
    }
    int remove(int item, int count) {   // returns how many were taken, from the last stacks first
        int taken = 0;
        for (int i = int(slots.size()) - 1; i >= 0 && taken < count; --i) {
            Slot& s = slots[size_t(i)];
            if (s.item != item) continue;
            const int t = std::min(s.count, count - taken);
            s.count -= t;
            taken += t;
            if (s.count <= 0) s = {};
        }
        return taken;
    }
    int count_of(int item) const {
        int n = 0;
        for (const auto& s : slots) n += s.item == item ? s.count : 0;
        return n;
    }
    bool has(int item) const { return count_of(item) > 0; }
    int free_slots() const { return int(std::count_if(slots.begin(), slots.end(), [](const Slot& s) { return s.item == I_NONE; })); }
};

// ── Weapons ────────────────────────────────────────────────────────────────────
enum class Weapon : int { Pistol, Shotgun, Count };
struct WeaponSpec {
    const char* name;
    int item, ammo;              // the gun itself and what it eats (Item ids)
    int mag;                     // rounds a full magazine (or both barrels) holds
    float fire_interval, reload_time, damage;
    int pellets;                 // > 1: a spread of pellets, each hitting on its own
    float spread_deg, range;
    float crit_chance, crit_mult;   // on the head only; a pistol crit bursts it (RE2 style)
    int stagger_power;           // 2 staggers through a Drowned's stagger immunity
    int knockdown_hits;          // this many pellets in one blast floor it (0: never)
    float noise;                 // how far away a Drowned hears it (m)
    bool single_load;            // a tube: shells go in one at a time (reload_time each) and firing stops the loading
    float rack_time;             // an empty pump gun: the first shell also has to be racked into the chamber
};
inline const WeaponSpec& weapon_spec(Weapon w) {
    // The balance table. The M92FS holds 15 like the real one. The Remington 870 holds 6 in its
    // extended tube and 1 in the chamber; fire_interval includes pumping the next one in.
    static const WeaponSpec T[int(Weapon::Count)] = {
        {"M92FS", I_HANDGUN, I_HANDGUN_AMMO, 15, 0.42f, 1.4f, 10.0f, 1, 0.0f, 25.0f, 0.12f, 4.0f, 1, 0, 16.0f, false, 0.0f},
        {"Remington 870", I_SHOTGUN, I_SHELLS, 7, 0.8f, 0.5f, 8.0f, 8, 6.5f, 12.0f, 0.0f, 1.0f, 2, 5, 22.0f, true, 0.4f},
    };
    return T[std::clamp(int(w), 0, int(Weapon::Count) - 1)];
}
// Pellets lose their bite with distance: full to 4 m, half to 8 m, a quarter to the range. A
// bullet hits at full strength anywhere in range.
inline float falloff(Weapon w, float dist) {
    const WeaponSpec& s = weapon_spec(w);
    if (dist > s.range) return 0.0f;
    if (s.pellets == 1) return 1.0f;
    return dist <= 4.0f ? 1.0f : dist <= 8.0f ? 0.5f : 0.25f;
}

// One gun: magazine (or tube), rate of fire, reloading. Reserve ammo lives in the Inventory.
// A pistol reloads a whole magazine at once; a pump gun takes its shells one at a time, and you
// can stop to fire (like a tube you top up between Drowned).
struct Firearm {
    Weapon id = Weapon::Pistol;
    int mag = 0;
    float cooldown = 0, reloading = 0;
    int to_load = 0;             // a tube gun: shells still to go in
    const WeaponSpec& spec() const { return weapon_spec(id); }
    // Time passes. Returns how many rounds went into the gun just now: a tube gun hands its shells
    // over one by one, and the caller takes each out of the case.
    int tick(float dt) {
        cooldown = std::max(0.0f, cooldown - dt);
        if (reloading <= 0) return 0;
        reloading -= dt;
        if (reloading > 0) return 0;
        reloading = 0;
        if (!spec().single_load || to_load <= 0) return 0;
        ++mag;
        if (--to_load > 0) reloading = spec().reload_time;   // the next shell
        return 1;
    }
    bool is_reloading() const { return reloading > 0; }
    bool can_fire() const { return mag > 0 && cooldown <= 0 && (!is_reloading() || spec().single_load); }
    bool fire() {
        if (!can_fire()) return false;
        stop_loading();   // a tube gun fires straight out of a reload
        --mag;
        cooldown = spec().fire_interval;
        return true;
    }
    void stop_loading() { if (spec().single_load) { reloading = 0; to_load = 0; } }
    // Start reloading from `available` rounds. A magazine goes in at once: returns how many it took.
    // A tube only starts (returns 0): the shells follow through tick(). Into an empty pump gun the
    // first shell takes a rack as well.
    int reload(int available) {
        const int want = std::min(spec().mag - mag, available);
        if (want <= 0 || is_reloading()) return 0;
        if (spec().single_load) {
            to_load = want;
            reloading = spec().reload_time + (mag == 0 ? spec().rack_time : 0.0f);
            return 0;
        }
        mag += want;
        reloading = spec().reload_time;
        return want;
    }
    // One bullet's (or pellet's) damage. roll: 0..1, injected so tests are deterministic; crit is
    // set when it was a critical hit (only possible on the head).
    float damage_for(bool head, float roll, float dist, bool* crit = nullptr) const {
        const bool c = head && roll < spec().crit_chance;
        if (crit) *crit = c;
        return spec().damage * falloff(id, dist) * (c ? spec().crit_mult : 1.0f);
    }
};

// ── A body coming apart ────────────────────────────────────────────────────────
// Every region has its own damage tally. When a region's tally passes its limit it comes off,
// along with everything that hangs from it (anatomy.hpp: the forearm goes with the upper arm).
// The Drowned's life (EnemyBrain::hp) takes a share of every hit: limbs soak damage, the head
// doesn't. Crits on the head burst it outright.
struct BodyDamage {
    // How much each part takes before it comes off: a jaw two 9 mm rounds, a forearm or a shin
    // three, an upper arm or a thigh four; a head only bursts (a crit, or a face full of buckshot).
    static constexpr float LIMIT[R_COUNT] = {1e9f, 45.0f, 12.0f, 32.0f, 22.0f, 32.0f, 22.0f, 38.0f, 26.0f, 38.0f, 26.0f};
    static constexpr float LIFE[R_COUNT] = {1.0f, 1.5f, 1.2f, 0.6f, 0.5f, 0.6f, 0.5f, 0.6f, 0.5f, 0.6f, 0.5f};
    float hurt[R_COUNT]{};
    bool off[R_COUNT]{};

    // Damage to one region. Returns the root of what came off (a region), or -1.
    int hit(int region, float dmg, bool burst = false) {
        if (region < 0 || region >= R_COUNT || off[region]) return -1;
        hurt[region] += dmg;
        if (region == R_BODY) return -1;
        if (!burst && hurt[region] < LIMIT[region]) return -1;
        const int root = region == R_JAW && burst ? R_HEAD : region;   // a crit on the jaw takes the head
        for (int r = 0; r < R_COUNT; ++r)
            if (region_within(r, root)) off[r] = true;
        return root;
    }
    bool head_gone() const { return off[R_HEAD]; }
    bool lost_leg() const { return off[R_THIGH_L] || off[R_SHIN_L] || off[R_THIGH_R] || off[R_SHIN_R]; }
    int hands() const { return int(!off[R_FARM_L]) + int(!off[R_FARM_R]); }   // hands left to grab with
};

// ── The player's condition: RE-style bands instead of a health bar ───────────────
enum class Condition { Fine, Caution, Danger, Dead };
inline Condition condition(float hp, float max_hp = 100.0f) {
    if (hp <= 0) return Condition::Dead;
    const float r = hp / max_hp;
    return r > 0.66f ? Condition::Fine : r > 0.33f ? Condition::Caution : Condition::Danger;
}
// How badly the survivor limps (0..1): the only on-screen sign of how hurt you are.
inline float limp_of(Condition c) { return c == Condition::Fine ? 0.0f : c == Condition::Caution ? 0.45f : 1.0f; }
// Walking speed multiplier for the limp.
inline float limp_speed(Condition c) { return c == Condition::Danger ? 0.7f : c == Condition::Caution ? 0.9f : 1.0f; }

// ── Player verbs: timings (seconds) and reach (metres), from the Godot demo ─────
namespace verbs {
constexpr float DODGE_TIME = 0.42f, DODGE_IFRAMES = 0.3f, DODGE_SPEED = 6.2f, DODGE_COOLDOWN = 0.35f;
constexpr float KICK_TIME = 0.5f, KICK_AT = 0.18f, KICK_RANGE = 1.8f, KICK_DAMAGE = 20.0f;
constexpr float HURT_TIME = 0.45f, HURT_INVULN = 0.9f;
constexpr float AIM_RANGE = 14.0f, AIM_CONE_DEG = 100.0f, AIM_TURN = 110.0f * kPi / 180.0f;
constexpr float QUICK_TURN_TIME = 0.3f;
// Skill: a dodge started in the last PERFECT_WINDOW before a bite lands is a perfect dodge (the
// Drowned overbalances past, and the next shot within FOCUS_TIME does FOCUS_MULT damage); a kick
// in the last COUNTER_WINDOW before it lands is a counter (it's thrown back and floored).
constexpr float PERFECT_WINDOW = 0.25f, OVERBALANCE_TIME = 1.2f, FOCUS_TIME = 1.5f, FOCUS_MULT = 2.0f;
constexpr float COUNTER_WINDOW = 0.25f;
}  // namespace verbs

// A dodge that began `dodge_age` seconds before the bite landed: was it perfect?
inline bool perfect_dodge(float dodge_age) { return dodge_age >= 0 && dodge_age <= verbs::PERFECT_WINDOW; }
// Is this Drowned in the last moment of its lunge, where a kick counters it?
inline bool counterable(const EnemyBrain& b) {
    const float s = b.time_to_strike();
    return s >= 0 && s <= verbs::COUNTER_WINDOW;
}

// Auto-aim: the nearest target in front, within reach and the aim cone.
struct AimCandidate { float x, z; bool alive; };
inline int pick_target(float px, float pz, float yaw, const AimCandidate* c, int n) {
    const V2 f = forward_from_yaw(yaw);
    int best = -1;
    float best_d = verbs::AIM_RANGE;
    for (int i = 0; i < n; ++i) {
        if (!c[i].alive) continue;
        const float dx = c[i].x - px, dz = c[i].z - pz, d = std::sqrt(dx * dx + dz * dz);
        const float cosang = d > 1e-4f ? (dx * f.x + dz * f.z) / d : 1.0f;
        if (d < best_d && cosang > std::cos(verbs::AIM_CONE_DEG * kPi / 180.0f)) { best = i; best_d = d; }
    }
    return best;
}

// ── Where a shot lands: rays against capsules ─────────────────────────────────
struct P3 { float x, y, z; };
inline P3 operator-(P3 a, P3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
inline float dot(P3 a, P3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
// Distance along a unit ray to where it enters the capsule a-b of radius r; -1 on a miss, 0 if it
// starts inside (a point-blank muzzle inside a body still hits it). Inigo Quilez's closed form.
inline float ray_capsule(P3 ro, P3 rd, P3 pa, P3 pb, float r) {
    const P3 ba = pb - pa, oa = ro - pa;
    const float baba = dot(ba, ba), bard = dot(ba, rd), baoa = dot(ba, oa), rdoa = dot(rd, oa), oaoa = dot(oa, oa);
    {   // inside already?
        const float t = baba > 1e-12f ? std::clamp(baoa / baba, 0.0f, 1.0f) : 0.0f;
        const P3 q{oa.x - ba.x * t, oa.y - ba.y * t, oa.z - ba.z * t};
        if (dot(q, q) <= r * r) return 0.0f;
    }
    const float a = baba - bard * bard, b = baba * rdoa - baoa * bard, c = baba * oaoa - baoa * baoa - r * r * baba;
    float h = b * b - a * c;
    if (a > 1e-9f && h >= 0.0f) {
        const float t = (-b - std::sqrt(h)) / a, y = baoa + t * bard;
        if (y > 0.0f && y < baba) return t >= 0.0f ? t : -1.0f;
    }
    float best = -1.0f;   // the end caps: spheres at a and b
    for (const P3& e : {pa, pb}) {
        const P3 oc = ro - e;
        const float bb = dot(rd, oc), cc = dot(oc, oc) - r * r;
        h = bb * bb - cc;
        if (h < 0.0f) continue;
        const float t = -bb - std::sqrt(h);
        if (t >= 0.0f && (best < 0.0f || t < best)) best = t;
    }
    return best;
}
struct HitVolume { int owner, region; P3 a, b; float r; };
struct RayHit { int owner = -1, region = -1; float t = -1; };
inline RayHit first_hit(P3 ro, P3 rd, float range, const HitVolume* v, int n) {
    RayHit best;
    for (int i = 0; i < n; ++i) {
        const float t = ray_capsule(ro, rd, v[i].a, v[i].b, v[i].r);
        if (t >= 0.0f && t <= range && (best.t < 0.0f || t < best.t)) best = {v[i].owner, v[i].region, t};
    }
    return best;
}

// ── The hall: one Drowned, then two more through the front door ────────────────
// The script of the first encounter. Feed it time and how many are left standing; it says when
// the door bangs and the second wave comes in.
struct HallEncounter {
    enum class Phase { First, Quiet, Bang, Second, Clear };
    Phase phase = Phase::First;
    float t = 0;
    static constexpr float QUIET = 2.5f, BANG_TO_ENTRY = 1.4f;
    enum class Event { None, DoorBang, SecondWave, Cleared };
    Event update(float dt, int alive) {
        t += dt;
        switch (phase) {
            case Phase::First:  if (alive == 0) { phase = Phase::Quiet; t = 0; } break;
            case Phase::Quiet:  if (t >= QUIET) { phase = Phase::Bang; t = 0; return Event::DoorBang; } break;
            case Phase::Bang:   if (t >= BANG_TO_ENTRY) { phase = Phase::Second; t = 0; return Event::SecondWave; } break;
            case Phase::Second: if (alive == 0 && t > 0.5f) { phase = Phase::Clear; t = 0; return Event::Cleared; } break;
            case Phase::Clear:  break;
        }
        return Event::None;
    }
};

}  // namespace dw
#endif
