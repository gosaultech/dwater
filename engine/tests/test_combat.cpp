// damned_waters/engine/tests/test_combat.cpp
// Purpose: GoogleTest suite for the combat rules (combat.hpp) and the enemy brain (core.hpp).
// Ported from the Godot demo's unit tests (test_firearm, test_inventory, test_enemy_brain), plus
// the parts that are new here: dismemberment, shot rays, auto-aim, the hall encounter.
#include <gtest/gtest.h>
#include <cmath>

#include "dw/combat.hpp"

using namespace dw;

namespace {
constexpr float DT = 1.0f / 60;
// Run the brain for `seconds`; returns how many times `ev` came out.
int run(EnemyBrain& b, float seconds, bool sees, float dist, EEvent ev) {
    int n = 0;
    for (float t = 0; t < seconds; t += DT) n += b.update(DT, sees, false, dist) == ev;
    return n;
}
}  // namespace

// ── Firearms ─────────────────────────────────────────────────────────────────────
TEST(Firearm, FireConsumesARoundAndRespectsTheCooldown) {
    Firearm g{Weapon::Pistol, weapon_spec(Weapon::Pistol).mag};
    EXPECT_TRUE(g.fire());
    EXPECT_FALSE(g.fire());                               // the cooldown blocks the next shot
    g.tick(g.spec().fire_interval);
    EXPECT_TRUE(g.fire());
    EXPECT_EQ(g.mag, g.spec().mag - 2);
}

TEST(Firearm, ReloadTakesOnlyWhatIsNeededAndAvailable) {
    Firearm g{Weapon::Pistol, 3};
    EXPECT_EQ(g.reload(4), 4);
    EXPECT_EQ(g.mag, 7);
    EXPECT_FALSE(g.can_fire());                           // not while reloading
    g.tick(g.spec().reload_time);
    EXPECT_EQ(g.reload(100), g.spec().mag - 7);
}

TEST(Firearm, TheM92FSHoldsFifteenAndCritsOnlyOnTheHead) {
    Firearm g{Weapon::Pistol, 15};
    EXPECT_EQ(g.spec().mag, 15);
    bool crit = false;
    EXPECT_FLOAT_EQ(g.damage_for(true, 0.0f, 3.0f, &crit), 4.0f);
    EXPECT_TRUE(crit);
    EXPECT_FLOAT_EQ(g.damage_for(true, 0.99f, 3.0f, &crit), 1.0f);
    EXPECT_FALSE(crit);
    EXPECT_FLOAT_EQ(g.damage_for(false, 0.0f, 3.0f), 1.0f);
}

TEST(Firearm, TheShotgunIsTwoShellsAndFallsOff) {
    Firearm g{Weapon::Shotgun, weapon_spec(Weapon::Shotgun).mag};
    EXPECT_EQ(g.mag, 2);
    EXPECT_FLOAT_EQ(g.damage_for(false, 0.5f, 2.0f), 0.8f);
    EXPECT_FLOAT_EQ(g.damage_for(false, 0.5f, 6.0f), 0.4f);
    EXPECT_FLOAT_EQ(g.damage_for(false, 0.5f, 20.0f), 0.0f);
}

TEST(Firearm, OnePointBlankBlastDropsADrowned) {
    const Firearm g{Weapon::Shotgun, 2};
    EXPECT_GE(float(g.spec().pellets) * g.damage_for(false, 0.5f, 1.5f), EnemyBrain{}.hp);
}

// ── The case ─────────────────────────────────────────────────────────────────────
TEST(Inventory, AmmoStacksToItsCapThenSpills) {
    Inventory inv;
    EXPECT_EQ(inv.add(I_HANDGUN_AMMO, 50), 0);
    EXPECT_EQ(inv.add(I_HANDGUN_AMMO, 20), 0);
    EXPECT_EQ(inv.count_of(I_HANDGUN_AMMO), 70);
    EXPECT_EQ(inv.free_slots(), 6);                       // a 60 cap: the rest took a second slot
}

TEST(Inventory, AFullCaseReportsWhatDidNotFit) {
    Inventory inv;
    for (int i = 0; i < 8; ++i) inv.add(I_FIRST_AID, 1);
    EXPECT_EQ(inv.add(I_CELLAR_KEY, 1), 1);
    EXPECT_EQ(inv.remove(I_FIRST_AID, 1), 1);
    EXPECT_EQ(inv.add(I_CELLAR_KEY, 1), 0);
}

TEST(Inventory, RemovingTheLastOneFreesTheSlot) {
    Inventory inv;
    inv.add(I_SHELLS, 6);
    EXPECT_EQ(inv.remove(I_SHELLS, 10), 6);
    EXPECT_FALSE(inv.has(I_SHELLS));
    EXPECT_EQ(inv.free_slots(), 8);
    EXPECT_EQ(item_by_key("shotgun_shells"), I_SHELLS);   // the room data's names
    EXPECT_EQ(item_by_key("nonsense"), I_NONE);
}

// ── The brain ────────────────────────────────────────────────────────────────────
TEST(EnemyBrain, EveryWindupIsReadable) {
    EXPECT_GE(EnemyBrain{}.windup, 0.5f);                 // the design bible's hard floor
}

TEST(EnemyBrain, StaggerImmunityButHeavyHitsAlwaysStagger) {
    EnemyBrain b;
    EXPECT_EQ(b.take_hit(1.0f), EHit::Staggered);
    EXPECT_EQ(b.take_hit(1.0f), EHit::Hurt);              // inside the immunity window
    EXPECT_EQ(b.take_hit(1.0f, 2), EHit::Staggered);      // shotgun and kick go through it
}

TEST(EnemyBrain, AStaggeredDrownedIsKickableAndAKickFloorsIt) {
    EnemyBrain b;
    b.take_hit(1.0f);
    EXPECT_TRUE(b.kickable());
    EXPECT_EQ(b.take_hit(2.0f, 2, true), EHit::Floored);
    EXPECT_FALSE(b.kickable());
    EXPECT_EQ(run(b, b.floor_time + 0.05f, true, 3.0f, EEvent::GotUp), 1);
}

TEST(EnemyBrain, DeathIsFinal) {
    EnemyBrain b;
    b.hp = 2;
    b.take_hit(1.0f);
    EXPECT_EQ(b.take_hit(1.0f), EHit::Died);
    EXPECT_EQ(b.take_hit(1.0f), EHit::Ignored);
    run(b, 1.0f, true, 0.5f, EEvent::None);
    EXPECT_EQ(b.state, EState::Dead);
}

TEST(EnemyBrain, StrikesOnceAfterTheTellThenRecovers) {
    EnemyBrain b;
    b.state = EState::Pursuit;
    EXPECT_EQ(b.update(DT, true, false, 1.0f), EEvent::Windup);
    EXPECT_EQ(run(b, b.windup - 0.05f, true, 1.0f, EEvent::Strike), 0);
    EXPECT_EQ(run(b, b.strike_window + 0.2f, true, 1.0f, EEvent::Strike), 1);
    EXPECT_EQ(b.state, EState::Recovery);
}

// ── Dismemberment ────────────────────────────────────────────────────────────────
TEST(BodyDamage, AnArmComesOffAtTheShoulderWithItsForearm) {
    BodyDamage d;
    int off = -1;
    for (int i = 0; i < 3; ++i) EXPECT_EQ(d.hit(R_UARM_L, 1.0f), -1);   // three bullets hold
    off = d.hit(R_UARM_L, 1.0f);
    EXPECT_EQ(off, R_UARM_L);
    EXPECT_TRUE(d.off[R_FARM_L]);                         // the forearm hangs from it
    EXPECT_FALSE(d.off[R_FARM_R]);
    EXPECT_EQ(d.hands(), 1);
    EXPECT_EQ(d.hit(R_FARM_L, 5.0f), -1);                 // nothing left there to hit
}

TEST(BodyDamage, AForearmComesOffAtTheElbow) {
    BodyDamage d;
    d.hit(R_FARM_R, 1.0f);
    d.hit(R_FARM_R, 1.0f);
    EXPECT_EQ(d.hit(R_FARM_R, 1.0f), R_FARM_R);
    EXPECT_FALSE(d.off[R_UARM_R]);
}

TEST(BodyDamage, LosingALegMakesItACrawler) {
    BodyDamage d;
    EXPECT_FALSE(d.lost_leg());
    d.hit(R_SHIN_L, 3.0f);
    EXPECT_TRUE(d.lost_leg());
    EXPECT_FALSE(d.off[R_THIGH_L]);
}

TEST(BodyDamage, ACritBurstsTheHeadAndTheJawCanBeShotAway) {
    BodyDamage a;
    EXPECT_EQ(a.hit(R_HEAD, 4.0f, true), R_HEAD);
    EXPECT_TRUE(a.head_gone());
    EXPECT_TRUE(a.off[R_JAW]);                            // the jaw hangs from the head
    BodyDamage b;
    EXPECT_EQ(b.hit(R_JAW, 1.0f), -1);
    EXPECT_EQ(b.hit(R_JAW, 1.0f), R_JAW);
    EXPECT_FALSE(b.head_gone());
    BodyDamage c;
    EXPECT_EQ(c.hit(R_BODY, 100.0f), -1);                 // the torso never comes off
}

TEST(BodyDamage, LimbsSoakDamageAndTheHeadDoesNot) {
    EXPECT_LT(BodyDamage::LIFE[R_FARM_L], BodyDamage::LIFE[R_BODY]);
    EXPECT_GT(BodyDamage::LIFE[R_HEAD], BodyDamage::LIFE[R_BODY]);
}

// ── Shots ────────────────────────────────────────────────────────────────────────
TEST(Ray, HitsACapsuleFromTheSideAndItsCaps) {
    const P3 a{0, 1, 0}, b{0, 2, 0};
    EXPECT_NEAR(ray_capsule({-5, 1.5f, 0}, {1, 0, 0}, a, b, 0.25f), 4.75f, 1e-4f);
    EXPECT_NEAR(ray_capsule({0, 5, 0}, {0, -1, 0}, a, b, 0.25f), 2.75f, 1e-4f);   // down the axis onto the top cap
    EXPECT_LT(ray_capsule({-5, 1.5f, 1}, {1, 0, 0}, a, b, 0.25f), 0.0f);          // passes behind
    EXPECT_LT(ray_capsule({5, 1.5f, 0}, {1, 0, 0}, a, b, 0.25f), 0.0f);           // pointing away
    EXPECT_FLOAT_EQ(ray_capsule({0, 1.5f, 0.1f}, {1, 0, 0}, a, b, 0.25f), 0.0f);  // starts inside
}

TEST(Ray, TheNearestVolumeTakesTheShot) {
    const HitVolume v[] = {{0, R_BODY, {0, 1, -3}, {0, 1.5f, -3}, 0.2f}, {1, R_HEAD, {0, 1.2f, -6}, {0, 1.2f, -6}, 0.12f}};
    const RayHit h = first_hit({0, 1.2f, 0}, {0, 0, -1}, 25.0f, v, 2);
    EXPECT_EQ(h.owner, 0);
    EXPECT_NEAR(h.t, 2.8f, 1e-4f);
    EXPECT_EQ(first_hit({0, 1.2f, 0}, {0, 0, -1}, 2.0f, v, 2).owner, -1);   // out of range
}

TEST(AutoAim, TakesTheNearestInFrontAndIgnoresTheDead) {
    const AimCandidate c[] = {{0, -4, true}, {0, -2, false}, {0, 3, true}, {0.5f, -6, true}};
    EXPECT_EQ(pick_target(0, 0, 0, c, 4), 0);            // yaw 0 looks down -Z
    EXPECT_EQ(pick_target(0, 0, kPi, c, 4), 2);          // turned round
    const AimCandidate far[] = {{0, -20, true}};
    EXPECT_EQ(pick_target(0, 0, 0, far, 1), -1);
}

// ── The player's condition ───────────────────────────────────────────────────────
TEST(Condition, BandsAndLimp) {
    EXPECT_EQ(condition(100), Condition::Fine);
    EXPECT_EQ(condition(50), Condition::Caution);
    EXPECT_EQ(condition(20), Condition::Danger);
    EXPECT_EQ(condition(0), Condition::Dead);
    EXPECT_EQ(limp_of(Condition::Fine), 0.0f);
    EXPECT_GT(limp_of(Condition::Danger), limp_of(Condition::Caution));
    EXPECT_LT(limp_speed(Condition::Danger), 1.0f);
}

// ── The hall ─────────────────────────────────────────────────────────────────────
TEST(HallEncounter, TheDoorBangsAfterTheFirstDiesThenTwoMoreComeIn) {
    HallEncounter e;
    EXPECT_EQ(e.update(1.0f, 1), HallEncounter::Event::None);
    EXPECT_EQ(e.update(0.1f, 0), HallEncounter::Event::None);   // it died: a quiet beat first
    int bangs = 0, waves = 0, cleared = 0;
    for (float t = 0; t < 10; t += DT) {
        const auto ev = e.update(DT, e.phase == HallEncounter::Phase::Second ? 2 : 0);
        bangs += ev == HallEncounter::Event::DoorBang;
        waves += ev == HallEncounter::Event::SecondWave;
    }
    EXPECT_EQ(bangs, 1);
    EXPECT_EQ(waves, 1);
    for (float t = 0; t < 2; t += DT) cleared += e.update(DT, 0) == HallEncounter::Event::Cleared;
    EXPECT_EQ(cleared, 1);
}
