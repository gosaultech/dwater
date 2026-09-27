# damned_waters/game/src/core/interaction_query.gd
# Purpose: pick the interactable the player is facing, RE-style: it must be in
# reach (radius, measured on the floor plane) and roughly in front of you.
class_name InteractionQuery
extends RefCounted

const MAX_ANGLE_DEG := 70.0
const POINT_BLANK := 0.35  # this close, facing doesn't matter


## items: Array of Dictionary with pos: Vector3 and radius: float.
static func best(items: Array, pos: Vector3, facing: Vector3) -> Dictionary:
	var best_item := {}
	var best_dist := INF
	var f := Vector2(facing.x, facing.z).normalized()
	for it in items:
		var to := Vector2(it.pos.x - pos.x, it.pos.z - pos.z)
		var d := to.length()
		if d > float(it.radius) or d >= best_dist:
			continue
		if d > POINT_BLANK and rad_to_deg(absf(f.angle_to(to))) > MAX_ANGLE_DEG:
			continue
		best_item = it
		best_dist = d
	return best_item
