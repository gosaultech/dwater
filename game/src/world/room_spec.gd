# damned_waters/game/src/world/room_spec.gd
# Purpose: parse + validate a RoomSpec JSON (game/data/rooms/<id>.json) into
# typed Godot values. Blender reads the same file (tools/pipeline/roomspec.py),
# which is why collision and pictures always line up.
class_name RoomSpec
extends RefCounted

const ROOMS_DIR := "res://data/rooms"
const PLATES_DIR := "res://assets/rooms"
const WALL_T := 0.3

var id := ""
var display_name := ""
var bounds := Rect2()          # XZ floor rectangle
var height := 3.0
var props: Array = []
var lights: Array = []
var shots: Array = []          # {id, pos, look_at, fov, zone: Rect2, priority}
var spawns := {}               # id -> {pos: Vector3, yaw: float (radians)}
var interactables: Array = []  # dicts with pos: Vector3, radius: float, kind...
var enemies: Array = []
var footsteps := "wood"
var ambience := ""
var move_scale := 1.0
var water_y := -INF
var errors := PackedStringArray()


static func path_for(room_id: String) -> String:
	return "%s/%s.json" % [ROOMS_DIR, room_id]


static func plate_path(room_id: String, shot_id: String, layer: String) -> String:
	return "%s/%s/%s_%s.png" % [PLATES_DIR, room_id, shot_id, layer]


static func v3(a) -> Vector3:
	return Vector3(float(a[0]), float(a[1]), float(a[2]))


static func rect_xz(zmin, zmax) -> Rect2:
	var p := Vector2(float(zmin[0]), float(zmin[1]))
	return Rect2(p, Vector2(float(zmax[0]), float(zmax[1])) - p)


static func load_room(room_id: String) -> RoomSpec:
	var text := FileAccess.get_file_as_string(path_for(room_id))
	var parsed = JSON.parse_string(text)
	var spec := RoomSpec.new()
	if typeof(parsed) != TYPE_DICTIONARY:
		spec.errors.append("cannot parse %s" % path_for(room_id))
		return spec
	spec._from_dict(parsed)
	return spec


func is_valid() -> bool:
	return errors.is_empty()


func _from_dict(d: Dictionary) -> void:
	for key in ["id", "bounds", "height", "shots", "spawns"]:
		if not d.has(key):
			errors.append("missing '%s'" % key)
	if not errors.is_empty():
		return
	id = d.id
	display_name = d.get("display_name", id)
	bounds = rect_xz(d.bounds.min, d.bounds.max)
	height = float(d.height)
	props = d.get("props", [])
	lights = d.get("lights", [])
	footsteps = d.get("footsteps", "wood")
	ambience = d.get("ambience", "")
	move_scale = float(d.get("move_scale", 1.0))
	if d.has("water"):
		water_y = float(d.water.y)
	for s in d.shots:
		shots.append({"id": String(s.id), "pos": v3(s.pos), "look_at": v3(s.look_at), "fov": float(s.fov),
			"zone": rect_xz(s.zone.min, s.zone.max), "priority": int(s.get("priority", 0))})
	for k in d.spawns:
		spawns[k] = {"pos": v3(d.spawns[k].pos), "yaw": deg_to_rad(float(d.spawns[k].get("yaw", 0)))}
	for it in d.get("interactables", []):
		var c: Dictionary = it.duplicate(true)
		c.pos = v3(it.pos)
		c.radius = float(it.get("radius", 1.0))
		interactables.append(c)
	for e in d.get("enemies", []):
		var c: Dictionary = e.duplicate(true)
		c.pos = v3(e.pos)
		c.yaw = deg_to_rad(float(e.get("yaw", 0)))
		enemies.append(c)
	_validate()


func _validate() -> void:
	var ids := {}
	for s in shots:
		if ids.has(s.id):
			errors.append("duplicate shot id %s" % s.id)
		ids[s.id] = true
		if not bounds.grow(0.01).has_point(Vector2(s.zone.position.x, s.zone.position.y)):
			errors.append("shot %s zone starts outside room bounds" % s.id)
	for sp in spawns.values():
		if not bounds.has_point(Vector2(sp.pos.x, sp.pos.z)):
			errors.append("spawn outside bounds at %s" % sp.pos)
	for it in interactables:
		if it.get("kind", "") == "door" and not (it.has("target_room") and it.has("target_spawn")):
			errors.append("door %s needs target_room + target_spawn" % it.get("id", "?"))


## Collision boxes as {center: Vector3, size: Vector3, yaw: float}. Walls are
## solid slabs outside the bounds (doors/windows are interactions, not holes).
func collision_boxes() -> Array:
	var out: Array = []
	var x0 := bounds.position.x
	var z0 := bounds.position.y
	var x1 := bounds.end.x
	var z1 := bounds.end.y
	var t := WALL_T
	var h := height
	out.append({"center": Vector3((x0 + x1) / 2, -0.1, (z0 + z1) / 2), "size": Vector3(x1 - x0 + 2 * t, 0.2, z1 - z0 + 2 * t), "yaw": 0.0})
	out.append({"center": Vector3((x0 + x1) / 2, h / 2, z0 - t / 2), "size": Vector3(x1 - x0 + 2 * t, h, t), "yaw": 0.0})
	out.append({"center": Vector3((x0 + x1) / 2, h / 2, z1 + t / 2), "size": Vector3(x1 - x0 + 2 * t, h, t), "yaw": 0.0})
	out.append({"center": Vector3(x0 - t / 2, h / 2, (z0 + z1) / 2), "size": Vector3(t, h, z1 - z0), "yaw": 0.0})
	out.append({"center": Vector3(x1 + t / 2, h / 2, (z0 + z1) / 2), "size": Vector3(t, h, z1 - z0), "yaw": 0.0})
	for p in props:
		if not p.get("collide", true) or not p.has("size"):
			continue
		var s := v3(p.size)
		var pos := v3(p.pos)
		out.append({"center": pos + Vector3(0, s.y / 2, 0), "size": s, "yaw": deg_to_rad(float(p.get("yaw", 0)))})
	return out
