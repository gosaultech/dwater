# damned_waters/game/src/core/shot_selector.gd
# Purpose: decide which fixed camera shot is live for a player position.
# Rules: (1) stay on the current shot while still inside its zone (hysteresis:
# overlapping zones at thresholds stop ping-pong cutting); (2) otherwise take
# the highest-priority zone containing the player; (3) outside every zone, keep
# the current shot. Cost: a handful of rectangle checks per physics tick.
class_name ShotSelector
extends RefCounted


static func zone_has(zone: Rect2, p: Vector2) -> bool:
	return p.x >= zone.position.x and p.y >= zone.position.y \
		and p.x <= zone.end.x and p.y <= zone.end.y


## shots: Array of Dictionary {id: String, zone: Rect2 (XZ), priority: int}
static func select(shots: Array, current_id: String, pos_xz: Vector2) -> String:
	for s in shots:
		if s.id == current_id and zone_has(s.zone, pos_xz):
			return current_id
	var best := ""
	var best_priority := -1000000
	for s in shots:
		var pri := int(s.get("priority", 0))
		if zone_has(s.zone, pos_xz) and pri > best_priority:
			best = String(s.id)
			best_priority = pri
	if best != "":
		return best
	if current_id == "" and not shots.is_empty():
		return String(shots[0].id)
	return current_id
