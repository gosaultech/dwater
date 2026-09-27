# damned_waters/game/tests/visual/bestiary_v2.gd
# Purpose: real-time (in-engine) key art of every creature model, posed.
#   godot --path game -s res://tests/visual/bestiary_v2.gd -- --out=docs/bestiary
extends SceneTree

# model id, species, pose, speed, camera eye, look-at, label
const SHOTS := [
	["survivor", "humanoid", "walk", 1.6, Vector3(2.2, 1.45, -1.3), Vector3(0.0, 1.0, 0), "survivor_walk"],
	["survivor", "humanoid", "aim", 0.0, Vector3(1.5, 1.55, -2.3), Vector3(0.05, 1.2, 0), "survivor"],
	["verdronkene_veiled", "humanoid", "shamble", 0.8, Vector3(1.3, 1.5, -2.4), Vector3(0, 1.15, 0), "verdronkene_veiled"],
	["verdronkene_netted", "humanoid", "windup", 0.0, Vector3(-1.4, 1.5, -2.5), Vector3(0, 1.25, 0), "verdronkene_netted"],
	["kelderkind", "crawler", "idle", 1.4, Vector3(1.0, 0.75, -1.5), Vector3(0, 0.4, 0), "kelderkind"],
	["grachtenvorst", "boss", "idle", 0.0, Vector3(2.4, 1.9, -4.2), Vector3(0, 1.35, 0), "grachtenvorst"],
	["pestmeester", "stalker", "idle", 0.0, Vector3(1.3, 1.9, -2.7), Vector3(0, 1.45, 0), "pestmeester"],
	["fietser", "bike", "idle", 3.0, Vector3(2.4, 1.3, -2.0), Vector3(0, 0.8, 0.0), "fietser"],
]


func _initialize() -> void:
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _light(kind: String, pos: Vector3, look: Vector3, color: Color, energy: float, rng: float = 12.0) -> void:
	var l: Light3D
	if kind == "spot":
		var s := SpotLight3D.new()
		s.spot_range = rng
		s.spot_angle = 40.0
		l = s
	else:
		var o := OmniLight3D.new()
		o.omni_range = rng
		l = o
	root.add_child(l)
	l.look_at_from_position(pos, look, Vector3.UP)
	l.light_color = color
	l.light_energy = energy
	l.shadow_enabled = true


func _run() -> void:
	var out := "res://../docs/bestiary"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	DirAccess.make_dir_recursive_absolute(out)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.012, 0.014, 0.018)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.1, 0.12, 0.14)
	env.ambient_light_energy = 0.5
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.05, 0.07, 0.08)
	env.fog_density = 0.06
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var floor_mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(30, 30)
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.03, 0.035, 0.04)
	fm.roughness = 0.12
	pm.material = fm
	floor_mi.mesh = pm
	root.add_child(floor_mi)
	_light("spot", Vector3(-2.5, 3.5, -3.0), Vector3(0, 1.0, 0), Color(0.65, 0.78, 1.0), 9.0)   # cool key
	_light("spot", Vector3(2.5, 2.8, 2.8), Vector3(0, 1.2, 0), Color(1.0, 0.55, 0.25), 12.0)   # warm rim
	_light("omni", Vector3(1.5, 0.6, -2.0), Vector3.ZERO, Color(0.25, 0.3, 0.4), 0.4, 5.0)      # fill
	var cam := Camera3D.new()
	cam.fov = 40
	root.add_child(cam)
	cam.current = true
	var factory: Script = load("res://src/actors/character_factory.gd")  # same routing as the game
	for s in SHOTS:
		var m: Node3D = factory.creature(s[0], s[1])
		root.add_child(m.build())
		m.rotation.y = atan2(-(s[4].x), -(s[4].z)) * 0.55  # turn most of the way toward camera
		m.pose = s[2]
		m.speed = s[3]
		if s[0] == "grachtenvorst":  # raised for the slam tell
			for j in ["shoulder_l", "shoulder_r"]:
				m.joint(j).rotation.x = 2.3
		cam.look_at_from_position(s[4], s[5], Vector3.UP)
		for i in (47 if s[3] > 0.0 else 50):
			m.animate(1.0 / 60.0)
			await process_frame
		root.get_texture().get_image().save_png("%s/%s.png" % [out, s[6]])
		print("[bestiary] ", s[6])
		m.queue_free()
		await _frames(2)
	quit()
