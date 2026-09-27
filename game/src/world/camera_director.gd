# damned_waters/game/src/world/camera_director.gd
# Purpose: owns the one Camera3D and swaps between fixed shots (autoload
# "CameraDirector"). All plates for a room are loaded on room entry, so a cut
# is just a transform + two texture handles: no disk I/O, no hitch.
extends Node

var camera: Camera3D
var plate: BackgroundPlate
var room_id := ""
var current_id := ""
var _shots: Array = []
var _plates := {}  # shot_id -> [color, depth]


func attach(cam: Camera3D, bg: BackgroundPlate) -> void:
	camera = cam
	plate = bg


func load_room(spec: RoomSpec) -> void:
	room_id = spec.id
	_shots = spec.shots
	_plates.clear()
	current_id = ""
	for s in _shots:
		var c_path := RoomSpec.plate_path(spec.id, s.id, "color")
		var d_path := RoomSpec.plate_path(spec.id, s.id, "depth")
		var color: Texture2D = load(c_path) if ResourceLoader.exists(c_path) else null
		var depth: Texture2D = load(d_path) if ResourceLoader.exists(d_path) else null
		if color == null:
			push_warning("CameraDirector: missing plate %s (run tools/pipeline/build_backgrounds.py)" % c_path)
		_plates[s.id] = [color, depth]


func update_for(world_pos: Vector3, force: bool = false) -> void:
	var next := ShotSelector.select(_shots, "" if force else current_id, Vector2(world_pos.x, world_pos.z))
	if next != current_id or force:
		cut_to(next)


func cut_to(shot_id: String) -> void:
	for s in _shots:
		if s.id != shot_id:
			continue
		current_id = shot_id
		camera.fov = s.fov
		camera.look_at_from_position(s.pos, s.look_at, Vector3.UP)
		plate.fit(s.fov)
		var p: Array = _plates.get(shot_id, [null, null])
		plate.show_shot(p[0], p[1])
		GameEvents.camera_cut.emit(room_id, shot_id)
		return


func live_basis() -> Basis:
	return camera.global_transform.basis if camera else Basis.IDENTITY
