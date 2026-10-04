// damned_waters/engine/tests/test_status.cpp
// Purpose: GoogleTest suite for the status screen's rules (status.hpp): the condition read from
// health, what each item offers, loading a gun from the case, what the world remembers, and the
// screen walked through as a player would (browse, act, combine, discard, pick up, make room).
#include <gtest/gtest.h>

#include "dw/status.hpp"

using namespace dw;
using namespace dw::status;

namespace {
Pad press(int dx = 0, int dy = 0) { Pad p; p.dx = dx; p.dy = dy; return p; }
Pad confirm() { Pad p; p.confirm = true; return p; }
Pad back() { Pad p; p.back = true; return p; }
Inventory kit() {   // the case as he starts: both guns, rounds for each
    Inventory inv;
    inv.add(I_HANDGUN, 1);
    inv.add(I_SHOTGUN, 1);
    inv.add(I_HANDGUN_AMMO, 30);
    inv.add(I_SHELLS, 4);
    return inv;
}
}  // namespace

TEST(Status, ConditionFollowsHealthAndThePulseRises) {
    EXPECT_STREQ(condition_name(condition(100)), "FINE");
    EXPECT_STREQ(condition_name(condition(50)), "CAUTION");
    EXPECT_STREQ(condition_name(condition(10)), "DANGER");
    EXPECT_LT(heart_rate(100), heart_rate(50));
    EXPECT_LT(heart_rate(50), heart_rate(5));
    EXPECT_NEAR(heart_rate(100), 70.0f, 0.5f);
}

TEST(Status, EachItemOffersWhatItCanDo) {
    Action a[MAX_ACTIONS];
    int n = actions_for(I_HANDGUN, false, a);
    ASSERT_EQ(n, 3);
    EXPECT_EQ(a[0], Action::Equip);
    EXPECT_EQ(actions_for(I_HANDGUN, true, a), 2);   // in hand already: no Equip
    EXPECT_EQ(a[0], Action::Combine);
    n = actions_for(I_MED_M, false, a);
    EXPECT_EQ(a[0], Action::Use);
    EXPECT_EQ(a[n - 1], Action::Discard);
    EXPECT_EQ(actions_for(I_CELLAR_KEY, false, a), 1);   // a key: only examined (it's used at its door)
    EXPECT_FALSE(can_discard(I_SHOTGUN));
    EXPECT_FALSE(can_discard(I_CELLAR_KEY));
    EXPECT_TRUE(can_discard(I_SHELLS));
}

TEST(Status, RoundsCombineOnlyWithTheirGun) {
    EXPECT_TRUE(can_combine(I_HANDGUN_AMMO, I_HANDGUN));
    EXPECT_TRUE(can_combine(I_HANDGUN, I_HANDGUN_AMMO));
    EXPECT_TRUE(can_combine(I_SHELLS, I_SHOTGUN));
    EXPECT_FALSE(can_combine(I_SHELLS, I_HANDGUN));
    EXPECT_FALSE(can_combine(I_MED_S, I_HANDGUN));
}

TEST(Status, LoadingFromTheCaseTakesWhatTheGunHolds) {
    Inventory inv = kit();
    Firearm pistol{Weapon::Pistol, 3};
    EXPECT_EQ(load_from_case(inv, pistol), 12);
    EXPECT_EQ(pistol.mag, 15);
    EXPECT_EQ(inv.count_of(I_HANDGUN_AMMO), 18);
    EXPECT_EQ(load_from_case(inv, pistol), 0);   // full
    Firearm shotgun{Weapon::Shotgun, 0};
    EXPECT_EQ(load_from_case(inv, shotgun), 4);   // only 4 shells to give
    EXPECT_EQ(shotgun.mag, 4);
    EXPECT_FALSE(inv.has(I_SHELLS));
}

TEST(Status, TheWorldRemembersWhatsLeft) {
    WorldState w;
    const std::string k = WorldState::key("gang", "shells_gang");
    EXPECT_EQ(w.remaining(k, 6), 6);
    w.set_remaining(k, 2);
    EXPECT_EQ(w.remaining(k, 6), 2);
    w.set_remaining(k, 0);
    EXPECT_EQ(w.remaining(k, 6), 0);
    EXPECT_TRUE(w.taken.count(k));
}

TEST(Status, BrowsingMovesRoundTheCaseAndTabsCycle) {
    const Inventory inv = kit();
    Screen s;
    s.open();
    s.update(press(1), inv, 0, 0, 1);
    EXPECT_EQ(s.slot(), 1);
    s.update(press(0, -1), inv, 0, 0, 1);   // down a row
    EXPECT_EQ(s.slot(), 5);
    s.update(press(-1), inv, 0, 0, 1);
    s.update(press(-1), inv, 0, 0, 1);
    EXPECT_EQ(s.slot(), 3);   // wraps back round
    Pad tab;
    tab.tab = -1;
    s.update(tab, inv, 0, 0, 1);
    EXPECT_EQ(s.tab(), Tab::Map);
    EXPECT_EQ(s.update(back(), inv, 0, 0, 1).kind, Command::Close);
}

TEST(Status, EquipAndCombineGoThroughTheActionList) {
    const Inventory inv = kit();
    Screen s;
    s.open();
    s.update(press(1), inv, 0, 0, 1);   // the 870 (the pistol is in hand)
    s.update(confirm(), inv, 0, 0, 1);
    ASSERT_EQ(s.mode(), Mode::Actions);
    const Command eq = s.update(confirm(), inv, 0, 0, 1);   // Equip is first
    EXPECT_EQ(eq.kind, Command::Equip);
    EXPECT_EQ(eq.a, 1);
    // Rounds into the pistol: slot 2 (9mm) -> Combine -> slot 0.
    s.update(press(1), inv, 0, 0, 1);
    Pad x;
    x.combine = true;
    s.update(x, inv, 0, 0, 1);
    ASSERT_EQ(s.mode(), Mode::Combine);
    s.update(press(1), inv, 0, 0, 1);   // onto the shells: won't work
    EXPECT_EQ(s.update(confirm(), inv, 0, 0, 1).kind, Command::None);
    EXPECT_EQ(s.sound(), Sound::Deny);
    s.update(press(-1), inv, 0, 0, 1);
    s.update(press(-1), inv, 0, 0, 1);
    s.update(press(-1), inv, 0, 0, 1);   // the pistol
    const Command ld = s.update(confirm(), inv, 0, 0, 1);
    EXPECT_EQ(ld.kind, Command::Load);
    EXPECT_EQ(ld.a, 2);
    EXPECT_EQ(ld.b, 0);
}

TEST(Status, DiscardAsksFirstAndDefaultsToNo) {
    const Inventory inv = kit();
    Screen s;
    s.open();
    s.update(press(3), inv, 0, 0, 1);   // the shells
    s.update(confirm(), inv, 0, 0, 1);
    s.update(press(0, 1), inv, 0, 0, 1);   // up from Combine wraps to Discard
    s.update(confirm(), inv, 0, 0, 1);
    ASSERT_EQ(s.mode(), Mode::Discard);
    EXPECT_EQ(s.update(confirm(), inv, 0, 0, 1).kind, Command::None);   // "No"
    EXPECT_EQ(s.mode(), Mode::Browse);
}

TEST(Status, AFullCaseOffersToMakeRoom) {
    Inventory inv;
    for (int i = 0; i < 8; ++i) inv.add(i % 2 ? I_MED_S : I_MED_M, 1);   // eight med kits, no room
    Screen s;
    s.open_pickup(I_SHELLS, 6, 0);
    EXPECT_EQ(s.update(confirm(), inv, 0, 0, 1).kind, Command::None);   // Take: no room
    ASSERT_EQ(s.mode(), Mode::NoRoom);
    s.update(confirm(), inv, 0, 0, 1);   // Make room
    ASSERT_EQ(s.mode(), Mode::MakeRoom);
    s.update(confirm(), inv, 0, 0, 1);   // slot 0: discard it?
    ASSERT_EQ(s.mode(), Mode::Discard);
    s.update(press(1), inv, 0, 0, 1);    // to "Yes"
    const Command d = s.update(confirm(), inv, 0, 0, 1);
    EXPECT_EQ(d.kind, Command::Discard);
    EXPECT_EQ(s.mode(), Mode::Pickup);   // back to what he found
    s.pickup_fits(6);
    EXPECT_EQ(s.update(confirm(), inv, 0, 0, 1).kind, Command::Take);
}

TEST(Status, LeavingItIsAlwaysAnOption) {
    const Inventory inv = kit();
    Screen s;
    s.open_pickup(I_SHELLS, 6, 6);
    EXPECT_EQ(s.update(back(), inv, 0, 0, 1).kind, Command::Leave);
    s.open_pickup(I_SHELLS, 6, 6);
    s.update(press(1), inv, 0, 0, 1);
    EXPECT_EQ(s.update(confirm(), inv, 0, 0, 1).kind, Command::Leave);
}
