# damned_waters/game/src/world/room.gd
# Purpose: build a playable room from a RoomSpec: invisible collision, the
# real-time lights that light characters to match the plate, pickups, enemies,
# and a debug overlay (F1) that shows collision boxes over the painting.
class_name Room
extends Node3D

var spec: RoomSpec
var interactables: Array = []   # live list for InteractionQuery
var enemies: Array = []
var _pickups := {}              # interactable id -> Pickup node
var _flicker: Array = []        # [light, base_energy, phase]
var _debug: Node3D
var _t := 0.0


func build(s: RoomSpec) -> void:
	spec = s
	name = "Room_" + s.id
	_build_collision()
	_build_lights()
	for it in s.interactables:
		if it.kind == "pickup" and GameState.has_flag("picked:" + it.id):
			continue
		interactables.append(it)
		if it.kind == "pickup":
			var p := Pickup.new().setup(it.item, it.pos)
			add_child(p)
			_pickups[it.id] = p
	for e in s.enemies:
		if not e.has("requires_flag") or GameState.has_flag(e.requires_flag):
			spawn_enemy(e)
	GameEvents.debug_overlay_toggled.connect(_on_debug)
	GameEvents.flag_set.connect(_on_flag)


## Spawn one enemy from spec data (pos: Vector3, yaw: radians). Dead ones stay dead.
func spawn_enemy(e: Dictionary, force: bool = false) -> Enemy:
	if GameState.dead_enemies.has(e.id) and not force:
		return null
	for existing in enemies:
		if is_instance_valid(existing) and existing.enemy_id == e.id and not force:
			return null
	var v: Enemy
	match String(e.get("kind", "verdronkene")):
		"kelderkind":
			v = Kelderkind.new()
		"grachtenvorst":
			v = Grachtenvorst.new()
		_:
			v = Verdronkene.new()
	v.configure(e, spec)
	add_child(v)
	enemies.append(v)
	return v


## Story flags can release enemies while you're in the room (ambushes, the boss).
func _on_flag(flag: String) -> void:
	for e in spec.enemies:
		if e.get("requires_flag", "") == flag:
			var v := spawn_enemy(e)
			if v is Grachtenvorst:
				v.awaken.call_deferred()


func boss() -> Grachtenvorst:
	for e in enemies:
		if is_instance_valid(e) and e is Grachtenvorst:
			return e
	return null


func remove_pickup(interactable_id: String) -> void:
	interactables = interactables.filter(func(it): return it.id != interactable_id)
	if _pickups.has(interactable_id):
		_pickups[interactable_id].queue_free()
		_pickups.erase(interactable_id)


func _build_collision() -> void:
	var body := StaticBody3D.new()
	body.name = "Collision"
	body.collision_layer = 1
	body.collision_mask = 0
	add_child(body)
	_debug = Node3D.new()
	_debug.visible = false
	add_child(_debug)
	var dm := StandardMaterial3D.new()
	dm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	dm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dm.albedo_color = Color(0.1, 1.0, 0.4, 0.25)
	dm.no_depth_test = true
	for b in spec.collision_boxes():
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = b.size
		cs.shape = shape
		cs.position = b.center
		cs.rotation.y = b.yaw
		body.add_child(cs)
		var mi := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = b.size
		bm.material = dm
		mi.mesh = bm
		mi.position = b.center
		mi.rotation.y = b.yaw
		_debug.add_child(mi)


func _build_lights() -> void:
	for l in spec.lights:
		var light: Light3D
		match String(l.kind):
			"sun":
				var dl := DirectionalLight3D.new()
				var from := RoomSpec.v3(l.dir_from).normalized()
				dl.look_at_from_position(Vector3.ZERO, -from, Vector3.UP if absf(from.y) < 0.99 else Vector3.FORWARD)
				light = dl
			"spot", "area":
				var sl := SpotLight3D.new()
				sl.spot_range = float(l.get("range", 8.0))
				sl.spot_angle = float(l.get("spot_angle", 70.0)) * 0.5
				light = sl
			_:
				var ol := OmniLight3D.new()
				ol.omni_range = float(l.get("range", 6.0))
				light = ol
		if l.has("pos"):
			light.position = RoomSpec.v3(l.pos)
		if l.has("look_at") and l.has("pos"):
			light.look_at_from_position(RoomSpec.v3(l.pos), RoomSpec.v3(l.look_at), Vector3.UP)
		light.light_color = Color(l.color[0], l.color[1], l.color[2])
		light.light_energy = float(l.get("godot_energy", 1.0))
		light.shadow_enabled = false  # nothing real-time to receive shadows
		add_child(light)
		if l.get("flicker", false):
			_flicker.append([light, light.light_energy, randf() * 100.0])


func _process(delta: float) -> void:
	_t += delta
	for f in _flicker:
		var n := sin(_t * 13.0 + f[2]) * 0.5 + sin(_t * 31.0 + f[2] * 2.0) * 0.3 + sin(_t * 3.1 + f[2]) * 0.2
		f[0].light_energy = f[1] * (0.9 + 0.1 * n)


func _on_debug(v: bool) -> void:
	_debug.visible = v
