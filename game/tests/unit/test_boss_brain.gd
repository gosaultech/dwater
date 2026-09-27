# damned_waters/game/tests/unit/test_boss_brain.gd
# Purpose: the Grachtenvorst fight as a replayable script (injected rolls).
extends GutTest

const DT := 1.0 / 60.0


func _run(b: BossBrain, seconds: float, dist: float, roll: float = 0.1) -> Array:
	var all := []
	var t := 0.0
	while t < seconds:
		all.append_array(b.update(DT, dist, roll))
		t += DT
	return all


func _awake() -> BossBrain:
	var b := BossBrain.new(40.0)
	b.awaken()
	_run(b, b.emerge_time + 0.05, 6.0)
	return b


func test_invulnerable_while_emerging():
	var b := BossBrain.new()
	b.awaken()
	assert_has(b.take_damage(10.0, true), &"deflected")
	assert_eq(b.hp, 40.0)


func test_close_range_picks_slam_or_sweep_and_telegraphs():
	var b := _awake()
	var ev := _run(b, 0.05, 2.0, 0.1)
	assert_has(ev, &"windup_slam")
	assert_does_not_have(_run(b, 0.9, 2.0), &"strike_slam", "1.0 s tell")
	assert_has(_run(b, 0.2, 2.0), &"strike_slam")


func test_no_three_identical_close_attacks_in_a_row_on_mid_rolls():
	var b := _awake()
	var picks := []
	for i in 6:
		picks.append(b._pick_close(0.4))
	for i in range(2, picks.size()):
		assert_false(picks[i] == picks[i - 1] and picks[i - 1] == picks[i - 2])


func test_charge_into_pillar_dazes():
	var b := _awake()
	var ev := _run(b, 1.5, 6.0)
	assert_has(ev, &"windup_charge")
	_run(b, 0.95, 6.0)
	assert_eq(b.state, BossBrain.State.ACTIVE)
	assert_has(b.charge_blocked(), &"dazed")


func test_weak_point_multiplier_and_break_stagger():
	var b := _awake()
	b.take_damage(2.0, true)
	assert_eq(b.hp, 35.0, "2.5x on the heart")
	assert_has(b.take_damage(3.0, false), &"staggered", "8 damage accumulated breaks its stance")


func test_phase_two_then_summon_then_death():
	var b := _awake()
	assert_has(b.take_damage(20.0, false), &"phase2")
	assert_eq(b.phase, 2)
	assert_gt(b.speed_scale(), 1.0)
	assert_has(_run(b, b.phase_shift_time + 0.05, 6.0), &"summon")
	assert_has(b.take_damage(50.0, false), &"died")
	assert_true(b.is_dead())
