# damned_waters/game/tests/visual/bestiary.gd
# Purpose: studio renders of every enemy design (and the player for scale),
# posed in their key frames: idle and wind-up tells. Output feeds
# docs/enemy_design.md. Needs a renderer:
#   godot --path game -s res://tests/visual/bestiary.gd -- --out=/tmp/bestiary
extends SceneTree


func _initialize() -> void:
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _studio() -> Camera3D:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.045, 0.05, 0.055)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.2, 0.22, 0.26)
	env.ambient_light_energy = 0.6
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	for l in [[Vector3(-35, 40, 0), Color(1.0, 0.85, 0.7), 1.6], [Vector3(-20, 160, 0), Color(0.5, 0.8, 1.0), 2.0], [Vector3(-60, -60, 0), Color(0.4, 0.4, 0.5), 0.3]]:
		var d := DirectionalLight3D.new()
		d.rotation_degrees = l[0]
		d.light_color = l[1]
		d.light_energy = l[2]
		root.add_child(d)
	var floor_mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(40, 40)
	var fm := StandardMaterial3D.new()
	fm.albedo_color = Color(0.07, 0.075, 0.08)
	pm.material = fm
	floor_mi.mesh = pm
	root.add_child(floor_mi)
	var cam := Camera3D.new()
	cam.fov = 38
	root.add_child(cam)
	cam.current = true
	return cam


func _snap(cam: Camera3D, node: Node3D, eye: Vector3, target: Vector3, out: String) -> void:
	cam.look_at_from_position(eye, target, Vector3.UP)
	await _frames(20)
	root.get_texture().get_image().save_png(out)
	node.queue_free()
	await _frames(2)


func _run() -> void:
	var out := "/tmp/bestiary"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	DirAccess.make_dir_recursive_absolute(out)
	var cam := _studio()
	var mm: Script = load("res://src/actors/mannequin.gd")
	var face := atan2(-1.6, -2.6)  # three-quarter view, facing the camera
	# Player for scale
	var p: Node3D = mm.new()
	p.with_gun = true
	root.add_child(p.build())
	p.rotation.y = face
	await _snap(cam, p, Vector3(1.6, 1.3, 2.6), Vector3(0, 0.95, 0), out + "/0_player.png")
	# Verdronkene idle + wind-up tell
	for pose in ["idle", "windup"]:
		var v: Node3D = load("res://src/actors/verdronkene.gd").new()
		v.configure({"id": "b_" + pose, "pos": Vector3.ZERO, "yaw": face})
		root.add_child(v)
		v.set_physics_process(false)
		v.body.pose = "shamble" if pose == "idle" else "windup"
		for i in 40:
			v.body.animate(1.0 / 60.0)
		await _snap(cam, v, Vector3(1.6, 1.4, 2.6), Vector3(0, 1.0, 0), "%s/1_verdronkene_%s.png" % [out, pose])
	# Kelderkind scuttling + crouch-to-leap tell
	for pose in ["run", "windup"]:
		var k: Node3D = load("res://src/actors/kelderkind.gd").new()
		k.configure({"id": "k_" + pose, "pos": Vector3.ZERO, "yaw": face})
		root.add_child(k)
		k.set_physics_process(false)
		if pose == "windup":
			k.brain.state = 3  # ATTACK, inside the wind-up
		k.velocity = Vector3(1.5, 0, 0) if pose == "run" else Vector3.ZERO
		for i in 30:
			k._pose(1.0 / 60.0)
		await _snap(cam, k, Vector3(1.0, 0.75, 1.5), Vector3(0, 0.3, 0), "%s/2_kelderkind_%s.png" % [out, pose])
	# Grachtenvorst stalking + slam tell
	for attack in ["", "slam"]:
		var g: Node3D = load("res://src/actors/grachtenvorst.gd").new()
		g.configure({"id": "g_" + attack, "pos": Vector3.ZERO, "yaw": face})
		root.add_child(g)
		g.set_physics_process(false)
		g.root.position.y = 0.0
		g.boss.state = 3 if attack != "" else 2
		g.boss.attack = attack
		for i in 60:
			g._boss_pose(1.0 / 60.0)
		await _snap(cam, g, Vector3(3.0, 2.0, 4.6), Vector3(0, 1.2, 0), "%s/3_grachtenvorst_%s.png" % [out, "slam" if attack != "" else "stalk"])
	print("[bestiary] done")
	quit()
