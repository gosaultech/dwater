# damned_waters/game/src/core/movement_math.gd
# Purpose: pure movement maths for tank + modern controls. No nodes, no input,
# no physics: numbers in, numbers out, so every rule is unit-testable.
# Godot convention: a body's forward is -Z; yaw is rotation about +Y.
class_name MovementMath
extends RefCounted

const BACKPEDAL_SCALE := 0.6  # walking backwards is slower, like every RE


static func forward_from_yaw(yaw: float) -> Vector3:
	return Vector3(-sin(yaw), 0.0, -cos(yaw))


## Tank: right input turns clockwise seen from above (negative yaw).
static func tank_turn_delta(turn_input: float, turn_speed_rad: float, delta: float) -> float:
	return -turn_input * turn_speed_rad * delta


static func tank_velocity(forward_input: float, yaw: float, speed: float) -> Vector3:
	var scale := forward_input if forward_input >= 0.0 else forward_input * BACKPEDAL_SCALE
	return forward_from_yaw(yaw) * scale * speed


## Modern: stick direction is relative to the camera, flattened onto the floor.
static func camera_relative_direction(input: Vector2, cam_basis: Basis) -> Vector3:
	var fwd := -cam_basis.z
	fwd.y = 0.0
	var right := cam_basis.x
	right.y = 0.0
	if fwd.length_squared() < 1e-6 or right.length_squared() < 1e-6:
		return Vector3.ZERO
	var dir := right.normalized() * input.x + fwd.normalized() * input.y
	return dir.limit_length(1.0)


static func facing_from_direction(dir: Vector3, current_yaw: float) -> float:
	if dir.length_squared() < 1e-6:
		return current_yaw
	return atan2(-dir.x, -dir.z)


## Frame-rate independent exponential smoothing factor (0..1).
static func smoothing_alpha(sharpness: float, delta: float) -> float:
	return 1.0 - exp(-sharpness * delta)


## Yaw that turns a body to face `target` from `from` (XZ plane).
static func yaw_towards(from: Vector3, target: Vector3, current_yaw: float) -> float:
	return facing_from_direction(target - from, current_yaw)


## Rotate `current` toward `target` by at most max_step radians (shortest way).
static func step_yaw(current: float, target: float, max_step: float) -> float:
	var diff := wrapf(target - current, -PI, PI)
	return current + clampf(diff, -max_step, max_step)
