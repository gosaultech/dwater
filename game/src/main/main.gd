# damned_waters/game/src/main/main.gd
# Purpose: the director of the whole demo. Builds the camera + background
# plate, runs the title / new game / continue flow, performs RE-style door
# transitions, and resolves every interaction (doors, locks, pickups, notes,
# the typewriter, the water gate). Game rules live in the core classes; this
# file only sequences them.
extends Node3D

var camera: Camera3D
var plate: BackgroundPlate
var player: Player
var room: Room
var hud: Hud
var inventory_screen: InventoryScreen
var screens: Screens
var _transitioning := false
var _debug := false


func _ready() -> void:
	_build_world()
	hud = Hud.new()
	add_child(hud)
	inventory_screen = InventoryScreen.new()
	add_child(inventory_screen)
	screens = Screens.new()
	add_child(screens)
	GameEvents.interaction_requested.connect(_on_interaction)
	GameEvents.player_died.connect(_on_player_died)
	GameEvents.enemy_hit.connect(_on_enemy_hit)
	GameEvents.perfect_dodge.connect(func(): _time_fx(0.3, 0.9))
	GameEvents.boss_started.connect(func(_n, _m): AudioDirector.play_music("boss_theme"))
	GameEvents.boss_defeated.connect(_on_boss_defeated)
	hud.set_black(true)
	if OS.get_cmdline_user_args().has("--autostart"):
		_new_game.call_deferred()  # used by automated smoke tests
	else:
		_title_flow.call_deferred()


func _build_world() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color.BLACK
	# Linear tonemap at 1.0 = identity: the plate's pixels reach the screen
	# exactly as Blender graded them.
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 1.0
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.13, 0.14, 0.17)
	env.ambient_light_energy = 0.7
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)
	camera = Camera3D.new()
	camera.near = 0.05
	camera.far = 100.0
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	add_child(camera)
	camera.current = true
	plate = BackgroundPlate.new()
	camera.add_child(plate)
	CameraDirector.attach(camera, plate)


# ─────────────────────────── flow ───────────────────────────
func _title_flow() -> void:
	GameState.in_game = false
	_transitioning = true
	_clear_room()
	_reset_player()
	AudioDirector.stop_ambience()
	hud.set_black(true)
	var action := await screens.title(SaveSystem.has_save())
	AudioDirector.stop_music()
	match action:
		"new":
			await _new_game()
		"continue":
			await _continue_game()
		_:
			Telemetry.end_session("quit")
			get_tree().quit()


func _new_game() -> void:
	GameState.reset_new_game()
	Telemetry.log_event("new_game", {"scheme": GameState.control_scheme})
	if not OS.get_cmdline_user_args().has("--autostart"):
		await hud.message("Amsterdam. 02:14.\nThe water rose through the streets in under an hour. The phones died soon after.")
		await hud.message("You forced your way into a canal house on the Herengracht to get off the street.\nHome is twenty kilometres north. Your family is waiting.")
	await _enter_room(GameState.START_ROOM, GameState.START_SPAWN)


func _continue_game() -> void:
	var d := SaveSystem.load_slot()
	if d.is_empty():
		await _new_game()
		return
	GameState.from_dict(d)
	Telemetry.log_event("continue", {"room": GameState.room_id})
	await _enter_room(GameState.room_id, "", GameState.player_pos, GameState.player_yaw)


func _enter_room(room_id: String, spawn_id: String, pos := Vector3.ZERO, yaw := 0.0) -> void:
	_transitioning = true
	hud.hide_prompt()
	var spec := RoomSpec.load_room(room_id)
	if not spec.is_valid():
		push_error("Room %s invalid: %s" % [room_id, spec.errors])
		return
	_clear_room()
	room = Room.new()
	add_child(room)
	room.build(spec)
	if player == null:
		player = Player.new()
		add_child(player)
	player.room = room
	player.surface = spec.footsteps
	player.move_scale = spec.move_scale
	if spawn_id != "":
		pos = spec.spawns[spawn_id].pos
		yaw = spec.spawns[spawn_id].yaw
	player.place(pos, yaw)
	GameState.room_id = room_id
	GameState.in_game = true
	CameraDirector.load_room(spec)
	CameraDirector.update_for(pos, true)
	AudioDirector.set_room(room_id, spec.ambience)
	GameEvents.room_entered.emit(room_id)
	if _debug:
		GameEvents.debug_overlay_toggled.emit(true)
	player.block_input(0.3)
	await hud.fade_in()
	if not GameState.has_flag("visited:" + room_id):
		GameState.set_flag("visited:" + room_id)
		hud.area_title(spec.display_name)
	_transitioning = false


func _clear_room() -> void:
	if room:
		room.queue_free()
		room = null


func _reset_player() -> void:
	if player:
		player.queue_free()
		player = null


func _physics_process(_delta: float) -> void:
	if room and player and not _transitioning:
		CameraDirector.update_for(player.global_position)


func _unhandled_input(event: InputEvent) -> void:
	if not GameState.in_game or _transitioning or hud.is_busy() or inventory_screen.visible:
		return
	if player == null or player.is_dead():
		return
	if event.is_action_pressed("inventory"):
		get_viewport().set_input_as_handled()
		inventory_screen.open()
	elif event.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		_pause()
	elif event.is_action_pressed("toggle_controls"):
		GameState.control_scheme = "tank" if GameState.control_scheme == "modern" else "modern"
		GameEvents.control_scheme_changed.emit(GameState.control_scheme)
		hud.area_title("Controls: " + GameState.control_scheme.capitalize())
	elif event.is_action_pressed("debug_overlay"):
		_debug = not _debug
		GameEvents.debug_overlay_toggled.emit(_debug)


func _pause() -> void:
	if await screens.pause_menu() == "title":
		await hud.fade_out()
		_title_flow()


# ─────────────────────────── interactions ───────────────────────────
func _say(text: String, title: String = "") -> void:
	await hud.message(text, title)
	if player:
		player.block_input(0.3)


func _on_interaction(it: Dictionary) -> void:
	if _transitioning or hud.is_busy():
		return
	match String(it.kind):
		"examine":
			await _say(it.text)
		"note":
			GameState.set_flag("read:" + it.id)
			await _say(it.text, it.get("title", ""))
		"pickup":
			await _pickup(it)
		"save":
			await _save(it)
		"door":
			await _door(it)
		"end":
			await _end(it)


func _pickup(it: Dictionary) -> void:
	var count := int(it.count)
	var left := GameState.inventory.add(it.item, count)
	if left == count:
		await _say("You can't carry any more.")
		return
	room.remove_pickup(it.id)
	GameState.set_flag("picked:" + it.id)
	AudioDirector.play("pickup")
	GameEvents.item_picked.emit(it.item, count - left)
	if player:
		player._emit_ammo()
	var item_name: String = ItemDB.get_item(it.item).get("name", it.item)
	await _say("You took the %s." % item_name if count == 1 else "You took %d %s." % [count - left, item_name])
	if it.has("sets_flag"):
		GameState.set_flag(it.sets_flag)
	if it.item == "shotgun":
		await _say("Press 2 (or F) to switch weapons. At close range it knocks them flat. Kick staggered enemies with E.")
	if it.has("then_text"):
		AudioDirector.play("door_bang")
		await get_tree().create_timer(0.7).timeout
		await _say(it.then_text)


func _save(it: Dictionary) -> void:
	var pick := await hud.choice(it.text, ["Yes", "No"])
	player.block_input(0.3)
	if pick != 0:
		return
	AudioDirector.play("save")
	GameState.bump("saves")
	var err := SaveSystem.save(GameState.to_dict())
	GameEvents.game_saved.emit()
	await _say("Progress recorded." if err == OK else "The ribbon jammed. Save failed (%s)." % error_string(err))


func _door(it: Dictionary) -> void:
	if GameState.boss_active:
		await _say("Black water surges over the stairs. You can't turn your back on it.")
		return
	if it.has("lock") and not GameState.has_flag("unlocked:" + it.id):
		AudioDirector.play("door_locked")
		if not GameState.inventory.has(it.lock):
			await _say(it.locked_text)
			return
		GameState.inventory.remove(it.lock, 1)
		GameState.set_flag("unlocked:" + it.id)
		await _say(it.unlock_text)
	_transitioning = true
	hud.hide_prompt()
	AudioDirector.play("door_open")
	await hud.fade_out(0.45)
	await get_tree().create_timer(0.9).timeout  # the RE door beat: anticipation
	await _enter_room(it.target_room, it.target_spawn)


func _end(it: Dictionary) -> void:
	var boss_id: String = it.get("requires_dead", "")
	if boss_id != "" and not GameState.dead_enemies.has(boss_id):
		if GameState.boss_active:
			return
		await _say(it.wake_text)
		GameState.set_flag(it.wake_flag)  # Room spawns and awakens the boss
		return
	await _say(it.text)
	_transitioning = true
	await hud.fade_out(1.2)
	GameState.in_game = false
	var stats: Dictionary = GameState.stats.duplicate()
	stats["play_time_s"] = snappedf(GameState.play_time, 0.1)
	GameEvents.demo_completed.emit(stats)
	Telemetry.flush()
	await screens.results(GameState.stats, GameState.play_time)
	_title_flow()


# ─────────────────────────── combat feel ───────────────────────────
## Hit-stop: freeze a few frames on heavy hits so impacts register physically.
func _on_enemy_hit(_id: String, _damage: float, heavy: bool) -> void:
	if heavy and Engine.time_scale >= 1.0:
		_time_fx(0.05, 0.055)


## Temporarily scale time; real-time timer so the restore isn't slowed too.
func _time_fx(scale: float, real_seconds: float) -> void:
	Engine.time_scale = scale
	await get_tree().create_timer(real_seconds, true, false, true).timeout
	Engine.time_scale = 1.0


func _on_boss_defeated() -> void:
	AudioDirector.stop_music(3.0)
	await get_tree().create_timer(3.5).timeout
	await _say("The thing sinks into the black water. The canal gate stands open.")


func _on_player_died() -> void:
	AudioDirector.stop_music(1.0)
	Engine.time_scale = 1.0
	GameState.bump("deaths")
	await get_tree().create_timer(2.2).timeout
	await hud.fade_out(1.0)
	GameState.in_game = false
	_transitioning = true
	var action := await screens.game_over(SaveSystem.has_save())
	_reset_player()
	match action:
		"continue":
			await _continue_game()
		"new":
			await _new_game()
		_:
			_title_flow()
