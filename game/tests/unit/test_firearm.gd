# damned_waters/game/tests/unit/test_firearm.gd
# Purpose: magazine, fire rate, reload, crits and shotgun falloff rules.
extends GutTest


func test_fire_consumes_round_and_respects_cooldown():
	var g := Firearm.new("pistol")
	assert_true(g.fire())
	assert_false(g.fire(), "cooldown blocks the next shot")
	g.tick(float(g.cfg.fire_interval))
	assert_true(g.fire())
	assert_eq(g.mag, 8)


func test_reload_takes_only_what_is_needed_and_available():
	var g := Firearm.new("pistol", 3)
	assert_eq(g.reload(4), 4)
	assert_eq(g.mag, 7)
	g.tick(float(g.cfg.reload_time))
	assert_eq(g.reload(100), 3)


func test_cannot_fire_while_reloading():
	var g := Firearm.new("pistol", 5)
	g.reload(10)
	assert_false(g.can_fire())


func test_pistol_crit_only_on_weak_point():
	var g := Firearm.new("pistol")
	assert_eq(g.damage_for(true, 0.0), 4.0)
	assert_eq(g.damage_for(true, 0.99), 1.0)
	assert_eq(g.damage_for(false, 0.0), 1.0)


func test_shotgun_is_two_shells_and_falls_off():
	var g := Firearm.new("shotgun")
	assert_eq(g.mag, 2)
	assert_eq(g.damage_for(false, 0.5, 2.0), 0.8)
	assert_eq(g.damage_for(false, 0.5, 6.0), 0.4)
	assert_eq(g.damage_for(false, 0.5, 20.0), 0.0)


func test_point_blank_blast_kills_a_drowned():
	var total := float(WeaponDB.get_weapon("shotgun").pellets) * Firearm.new("shotgun").damage_for(false, 0.5, 1.5)
	assert_gte(total, float(EnemyDB.get_enemy("verdronkene").hp), "one close blast should drop a Verdronkene")
