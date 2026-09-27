# damned_waters/game/tests/unit/test_enemy_brain.gd
# Purpose: the shared enemy state machine, tick by tick, per EnemyDB tuning.
extends GutTest

const DT := 1.0 / 60.0


func _run(b: EnemyBrain, seconds: float, sees: bool, heard: bool, dist: float) -> Array:
	var all := []
	var t := 0.0
	while t < seconds:
		all.append_array(b.update(DT, sees, heard, dist))
		t += DT
	return all


func test_idle_until_stimulus():
	var b := EnemyDB.brain_for("verdronkene")
	_run(b, 2.0, false, false, 20.0)
	assert_eq(b.state, EnemyBrain.State.IDLE)


func test_sight_alerts_then_pursues():
	var b := EnemyDB.brain_for("verdronkene")
	var ev := _run(b, b.alert_time + 0.1, true, false, 5.0)
	assert_has(ev, &"alerted")
	assert_has(ev, &"pursue")


func test_every_enemy_windup_is_readable():
	for kind in EnemyDB.ENEMIES:
		assert_between(float(EnemyDB.get_enemy(kind).windup), 0.5, 1.0, "%s wind-up" % kind)
	for atk in BossBrain.ATTACKS:
		assert_gte(float(BossBrain.ATTACKS[atk].windup) * 0.8, 0.5, "boss %s stays readable in phase 2" % atk)


func test_strike_only_after_telegraph_then_recovery():
	var b := EnemyDB.brain_for("verdronkene")
	b.state = EnemyBrain.State.PURSUIT
	assert_has(b.update(DT, true, false, 1.0), &"windup")
	assert_does_not_have(_run(b, b.windup_time - 0.05, true, false, 1.0), &"strike")
	var rest := _run(b, b.strike_window + 0.2, true, false, 1.0)
	assert_eq(rest.count(&"strike"), 1)
	assert_eq(b.state, EnemyBrain.State.RECOVERY)


func test_stagger_immunity_but_heavy_hits_always_stagger():
	var b := EnemyDB.brain_for("verdronkene")
	assert_has(b.take_hit(1.0), &"staggered")
	assert_has(b.take_hit(1.0), &"hurt", "immunity window")
	assert_has(b.take_hit(1.0, 2), &"staggered", "shotgun / kick ignore immunity")


func test_staggered_enemy_is_kickable_and_knockdown_floors_it():
	var b := EnemyDB.brain_for("verdronkene")
	b.take_hit(1.0)
	assert_true(b.can_be_kicked())
	assert_has(b.take_hit(2.0, 2, true), &"floored")
	assert_false(b.can_be_kicked())
	assert_has(_run(b, b.floor_time + 0.05, true, false, 3.0), &"got_up")


func test_kelderkind_hits_and_runs():
	var b := EnemyDB.brain_for("kelderkind")
	b.state = EnemyBrain.State.PURSUIT
	_run(b, b.windup_time + b.strike_window + b.recovery_time + 0.1, true, false, 1.0)
	assert_eq(b.state, EnemyBrain.State.RETREAT)
	assert_has(_run(b, b.retreat_time + 0.05, true, false, 6.0), &"pursue")


func test_death_is_final():
	var b := EnemyBrain.new(2.0)
	b.take_hit(1.0)
	assert_has(b.take_hit(1.0), &"died")
	assert_eq(b.take_hit(1.0), [])
	_run(b, 1.0, true, true, 0.5)
	assert_eq(b.state, EnemyBrain.State.DEAD)
