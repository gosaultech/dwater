# damned_waters/game/tests/visual/capture.gd
# Purpose: automated visual check of the plate + depth compositing. Boots the
# real game, stages the player and a Drowned behind specific props in each
# shot, and saves screenshots. Needs a real renderer (not --headless):
#   godot --path game -s res://tests/visual/capture.gd -- --autostart --out=/tmp/caps
# (Linux CI: wrap in xvfb-run.) Look for: legs hidden by the table, bodies
# cut by the clock / pillar, shins vanishing under the cellar water.
extends SceneTree

# room, player [x, z, yaw_deg], enemy [x, z, yaw_deg] or [], label
const SETUPS := [  # room, player [x, z, yaw_deg], enemy kind, enemy [x, z, yaw_deg], label
	["gang", [0.7, 4.3, 180], "verdronkene", [0.6, 1.9, 0], "gang_a_drowned"],
	["gang", [1.0, 7.4, 0], "verdronkene", [1.1, 8.9, 180], "gang_b_front_door"],
	["gang", [0.6, 2.2, 180], "kelderkind", [0.55, 0.9, 0], "gang_c_crawler"],
	["voorkamer", [2.1, 3.95, -40], "kelderkind", [1.0, 2.9, 90], "voorkamer_a_crawler"],
	["voorkamer", [4.2, 1.5, -120], "verdronkene", [3.2, 2.6, 60], "voorkamer_b_desk"],
	["kelder", [2.4, 5.6, 0], "boss", [], "kelder_a_boss"],
	["kelder", [2.9, 3.3, 170], "boss", [], "kelder_b_boss"],
]


func _initialize() -> void:
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _run() -> void:
	var out := "/tmp/caps"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	DirAccess.make_dir_recursive_absolute(out)
	var main: Node = load("res://src/main/main.tscn").instantiate()
	root.add_child(main)
	await _frames(90)
	var only := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--only="):
			only = a.trim_prefix("--only=")
	for s in SETUPS:
		if only != "" and not String(s[4]).begins_with(only):
			continue
		root.get_node("GameState").health = 100
		root.get_node("GameState").dead_enemies.clear()
		await main._enter_room(s[0], "", Vector3(s[1][0], 0, s[1][1]), deg_to_rad(s[1][2]))
		var wait := 45
		if s[2] == "boss":
			root.get_node("GameState").health = 1000000  # harness only: survive the boss long enough to frame it
			root.get_node("GameState").set_flag("boss_awake")
			wait = 230
		elif s[2] != "":
			main.room.spawn_enemy({"id": "capture_" + s[4], "kind": s[2],
				"pos": Vector3(s[3][0], 0, s[3][1]), "yaw": deg_to_rad(s[3][2])}, true)
		var director: Node = root.get_node("CameraDirector")  # autoloads aren't compile-time names in -s scripts
		director.update_for(main.player.global_position, true)
		if s[2] != "" and s[2] != "boss":  # face the enemy and hold aim so the aim pose is visible
			var tgt := Vector3(s[3][0], 0, s[3][1])
			var pp: Vector3 = main.player.global_position
			main.player.rotation.y = atan2(-(tgt.x - pp.x), -(tgt.z - pp.z))
			Input.action_press("aim")
		await _frames(wait)
		var img := root.get_texture().get_image()
		img.save_png("%s/%s.png" % [out, s[4]])
		Input.action_release("aim")
		print("[capture] %s shot=%s" % [s[4], director.current_id])
	quit()
