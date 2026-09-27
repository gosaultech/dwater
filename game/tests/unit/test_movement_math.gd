# damned_waters/game/tests/unit/test_movement_math.gd
# Purpose: pin down movement rules (tank, modern, facing, smoothing, cut-stable input).
extends GutTest

const EPS := 1e-4


func test_forward_at_zero_yaw_is_minus_z():
	assert_almost_eq(MovementMath.forward_from_yaw(0.0), Vector3(0, 0, -1), Vector3.ONE * EPS)


func test_tank_turn_right_is_clockwise():
	assert_lt(MovementMath.tank_turn_delta(1.0, PI, 0.1), 0.0)


func test_tank_backpedal_is_slower():
	var fwd := MovementMath.tank_velocity(1.0, 0.0, 2.0).length()
	var back := MovementMath.tank_velocity(-1.0, 0.0, 2.0).length()
	assert_almost_eq(back, fwd * MovementMath.BACKPEDAL_SCALE, EPS)


func test_camera_relative_up_moves_away_from_camera():
	var cam := Basis.looking_at(Vector3(0, -0.5, -1).normalized())  # camera looks north and down
	var dir := MovementMath.camera_relative_direction(Vector2(0, 1), cam)
	assert_almost_eq(dir, Vector3(0, 0, -1), Vector3.ONE * EPS)


func test_camera_relative_is_clamped_to_unit_length():
	var dir := MovementMath.camera_relative_direction(Vector2(1, 1), Basis.IDENTITY)
	assert_almost_eq(dir.length(), 1.0, EPS)


func test_facing_keeps_yaw_when_idle():
	assert_eq(MovementMath.facing_from_direction(Vector3.ZERO, 1.23), 1.23)


func test_facing_matches_forward():
	var yaw := MovementMath.facing_from_direction(Vector3(1, 0, 0), 0.0)
	assert_almost_eq(MovementMath.forward_from_yaw(yaw), Vector3(1, 0, 0), Vector3.ONE * EPS)


func test_smoothing_alpha_is_frame_rate_independent():
	var one := MovementMath.smoothing_alpha(10.0, 1.0 / 30.0)
	var half := MovementMath.smoothing_alpha(10.0, 1.0 / 60.0)
	assert_almost_eq(1.0 - one, pow(1.0 - half, 2), EPS)


func test_step_yaw_takes_shortest_way_and_clamps():
	var r := MovementMath.step_yaw(deg_to_rad(170), deg_to_rad(-170), deg_to_rad(5))
	assert_almost_eq(r, deg_to_rad(175), EPS)


func test_cut_stable_input_holds_basis_through_a_cut():
	var c := CutStableInput.new()
	var before := Basis.IDENTITY
	var after := Basis(Vector3.UP, PI)
	c.basis_for(Vector2(0, 1), before)
	assert_eq(c.basis_for(Vector2(0, 1), after), before, "same stick direction keeps the old camera basis")


func test_cut_stable_input_rebases_on_release_or_big_change():
	var c := CutStableInput.new()
	var after := Basis(Vector3.UP, PI)
	c.basis_for(Vector2(0, 1), Basis.IDENTITY)
	assert_eq(c.basis_for(Vector2(1, 0), after), after, "90 degree change adopts the live camera")
	c.basis_for(Vector2.ZERO, Basis.IDENTITY)
	assert_eq(c.basis_for(Vector2(0, 1), after), after, "release then press adopts the live camera")
