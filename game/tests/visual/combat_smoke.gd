# damned_waters/game/tests/visual/combat_smoke.gd
# Purpose: drive the REAL game with simulated input to prove the combat loop
# works end to end (runs headless, ~20 s):
#   godot --headless --path game -s res://tests/visual/combat_smoke.gd -- --autostart
# 1) pistol the first Drowned until it staggers, kick it, finish it
# 2) wake the Grachtenvorst and fight it with the shotgun (god mode on so the
#    script can't lose), dodging whenever it winds up
# Prints a verdict line; exit code 0 = pass, 1 = fail.
extends SceneTree

var main: Node
var gs: Node
var log_lines := PackedStringArray()


func _initialize() -> void:
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await physics_frame


func _tap(action: String, hold_frames: int = 2) -> void:
	Input.action_press(action)
	await _frames(hold_frames)
	Input.action_release(action)
	await _frames(1)


func _face(target: Node3D) -> void:
	var p: Node3D = main.player
	var to := target.global_position - p.global_position
	p.rotation.y = atan2(-to.x, -to.z)


func _run() -> void:
	main = load("res://src/main/main.tscn").instantiate()
	root.add_child(main)
	gs = root.get_node("GameState")
	await _frames(120)
	var ok := true
	# ── Round 1: the wanderer in the hall ──
	await main._enter_room("gang", "", Vector3(0.6, 0, 4.4), 0.0)
	await _frames(30)
	var zwerver: Node = null
	for e in main.room.enemies:
		if e.enemy_id == "zwerver":
			zwerver = e
	var kicked := false
	for i in 40:
		if zwerver.is_dead():
			break
		_face(zwerver)
		Input.action_press("aim")
		await _frames(12)
		await _tap("fire")
		Input.action_release("aim")
		await _frames(3)
		if zwerver.can_be_kicked() and main.player.global_position.distance_to(zwerver.global_position) < 1.8:
			_face(zwerver)
			await _tap("interact")
			await _frames(30)
			kicked = kicked or zwerver.brain.state == 7  # FLOORED
		if gs.inventory.count_of("handgun_ammo") == 0 and main.player.weapon.mag == 0:
			break
	log_lines.append("round1: zwerver dead=%s kicked=%s hp=%.1f shots=%d health=%d" % [
		zwerver.is_dead(), kicked, zwerver.brain.hp, gs.stats.shots, gs.health])
	ok = ok and zwerver.is_dead()
	# ── Round 2: the Grachtenvorst ──
	gs.inventory.add("shotgun", 1)
	gs.inventory.add("shotgun_shells", 30)
	gs.health = 100
	await main._enter_room("kelder", "", Vector3(2.2, 0, 4.8), 0.0)
	for e in main.room.enemies:  # clear the emergers so the duel is readable
		if e.enemy_id.begins_with("kelder_drowned"):
			gs.dead_enemies[e.enemy_id] = true
			e.queue_free()
	main.room.enemies = main.room.enemies.filter(func(e): return is_instance_valid(e) and not e.is_queued_for_deletion())
	await _frames(5)
	main.player.equip("shotgun")
	gs.set_flag("boss_awake")
	await _frames(10)
	var boss: Node = main.room.boss()
	var events_seen := {}
	var dodges := 0
	for i in 900:
		if boss == null or boss.is_dead():
			break
		gs.health = 100  # god mode: this test checks systems, not skill
		events_seen[boss.boss.state] = true
		var d: float = main.player.global_position.distance_to(boss.global_position)
		if boss.boss.state == 3 and boss.boss.time_in_state > 0.45 and randf() < 0.5:  # WINDUP -> dodge sideways
			Input.action_press("move_left")
			await _tap("dodge")
			Input.action_release("move_left")
			dodges += 1
			await _frames(20)
			continue
		if boss.is_targetable() and d < 5.0:
			_face(boss)
			Input.action_press("aim")
			await _frames(8)
			await _tap("fire")
			Input.action_release("aim")
		await _frames(6)
	await _frames(240)
	log_lines.append("round2: boss dead=%s hp=%.1f phase=%d states_seen=%s dodges=%d perfect=%d kills=%d" % [
		boss.is_dead(), boss.boss.hp, boss.boss.phase, events_seen.keys(), dodges,
		gs.stats.get("perfect_dodges", 0), gs.stats.kills])
	ok = ok and boss.is_dead() and boss.boss.phase == 2
	for l in log_lines:
		print("[combat] " + l)
	print("[combat] VERDICT: %s" % ("PASS" if ok else "FAIL"))
	quit(0 if ok else 1)
