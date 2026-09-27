# damned_waters/game/tests/visual/model_check.gd
# Purpose: visual check for installed real character models: the survivor
# must FACE the enemy it aims at, the Drowned must reach toward its target.
#   godot --path game -s res://tests/visual/model_check.gd -- --autostart --out=/tmp/models
extends SceneTree

const SETUPS := [  # room, player [x, z, yaw], hide player, enemy [x, z, yaw], label, aim
	["gang", [0.8, 3.0, 180], false, [1.0, 6.3, 0], "survivor_aims_at_drowned", true],
	["voorkamer", [3.2, 5.5, 0], true, [4.3, 2.2, 140], "drowned_approaches", false],
]


func _initialize() -> void:
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _run() -> void:
	var out := "/tmp/models"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out = a.trim_prefix("--out=")
	DirAccess.make_dir_recursive_absolute(out)
	var main: Node = load("res://src/main/main.tscn").instantiate()
	root.add_child(main)
	var gs := root.get_node("GameState")
	await _frames(90)
	for s in SETUPS:
		gs.health = 100
		gs.dead_enemies = {"zwerver": true}
		print("[models] entering ", s[0])
		await main._enter_room(s[0], "", Vector3(s[1][0], 0, s[1][1]), deg_to_rad(s[1][2]))
		main.player.visible = not s[2]
		var e: Node3D = main.room.spawn_enemy({"id": "check_" + s[4], "kind": "verdronkene",
			"pos": Vector3(s[3][0], 0, s[3][1]), "yaw": deg_to_rad(s[3][2])}, true)
		if s[5]:
			Input.action_press("aim")
		await _frames(70)
		root.get_texture().get_image().save_png("%s/%s.png" % [out, s[4]])
		Input.action_release("aim")
		print("[models] %s player_yaw=%.0f enemy_state=%d" % [s[4], rad_to_deg(main.player.rotation.y), e.brain.state])
	quit()
