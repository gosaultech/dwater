# damned_waters/game/src/ui/screens.gd
# Purpose: full-screen menus: title, pause, game over, end-of-demo results.
# Each returns the chosen action string, so main.gd reads like a script:
#   var action := await screens.title(SaveSystem.has_save())
class_name Screens
extends CanvasLayer

signal _picked(action: String)

var _root: Control


func _init() -> void:
	layer = 30
	process_mode = Node.PROCESS_MODE_ALWAYS


func title(has_save: bool) -> String:
	AudioDirector.play_music("title_drone")
	while true:
		var opts := [["New Game", "new"]]
		if has_save:
			opts.append(["Continue", "continue"])
		opts.append(["Controls: %s" % GameState.control_scheme.capitalize(), "toggle"])
		opts.append(["Quit", "quit"])
		var a := await _menu("DAMNED WATERS", "Demo  ·  Het Grachtenpand", opts,
			"Amsterdam is drowning. Home is north.", 72)
		if a != "toggle":
			return a
		GameState.control_scheme = "tank" if GameState.control_scheme == "modern" else "modern"
	return "quit"


func pause_menu() -> String:
	var a := await _menu("PAUSED", "", [["Resume", "resume"],
		["Controls: %s" % GameState.control_scheme.capitalize(), "toggle"], ["Quit to Title", "title"]], "", 48, 0.6)
	if a == "toggle":
		GameState.control_scheme = "tank" if GameState.control_scheme == "modern" else "modern"
		GameEvents.control_scheme_changed.emit(GameState.control_scheme)
	return a


func game_over(has_save: bool) -> String:
	var opts := [["Continue from last save", "continue"]] if has_save else [["Try again", "new"]]
	opts.append(["Quit to Title", "title"])
	return await _menu("YOU DIED", "", opts, "", 64, 0.9, Color(0.6, 0.05, 0.03))


func results(stats: Dictionary, play_time: float) -> void:
	var acc: float = 0.0 if int(stats.get("shots", 0)) == 0 else 100.0 * stats.hits / stats.shots
	var body := "Time  %02d:%02d\nShots fired  %d\nAccuracy  %.0f%%\nDrowned put down  %d\nSaves  %d\nDamage taken  %d" % [
		int(play_time) / 60, int(play_time) % 60, stats.get("shots", 0), acc, stats.get("kills", 0),
		stats.get("saves", 0), stats.get("damage_taken", 0)]
	await _menu("END OF DEMO", "The canals are patient.", [["Return to Title", "title"]], body, 56)


func _menu(heading: String, sub: String, options: Array, body: String, size: int,
		dim: float = 1.0, color: Color = Color(0.82, 0.78, 0.68)) -> String:
	get_tree().paused = true
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = Theme.new()
	_root.theme.default_font = Hud.serif()
	add_child(_root)
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, dim)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(bg)
	var v := VBoxContainer.new()
	v.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	v.grow_horizontal = Control.GROW_DIRECTION_BOTH
	v.grow_vertical = Control.GROW_DIRECTION_BOTH
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.add_theme_constant_override("separation", 14)
	_root.add_child(v)
	_add_label(v, heading, size, color)
	if sub != "":
		_add_label(v, sub, 22, Color(0.6, 0.55, 0.45))
	if body != "":
		_add_label(v, body, 22, Color(0.85, 0.82, 0.75))
	var spacer := Control.new()
	spacer.custom_minimum_size.y = 24
	v.add_child(spacer)
	var first: Button
	for o in options:
		var b := Button.new()
		b.text = o[0]
		b.flat = true
		b.add_theme_font_size_override("font_size", 26)
		b.add_theme_color_override("font_color", Color(0.6, 0.57, 0.5))
		b.add_theme_color_override("font_focus_color", Color(1.0, 0.92, 0.75))
		b.add_theme_color_override("font_hover_color", Color(1.0, 0.92, 0.75))
		b.pressed.connect(func(): AudioDirector.play("ui_confirm"); _picked.emit(o[1]))
		b.focus_entered.connect(func(): AudioDirector.play("ui_move"))
		v.add_child(b)
		if first == null:
			first = b
	first.call_deferred("grab_focus")
	var action: String = await _picked
	_root.queue_free()
	get_tree().paused = false
	return action


func _add_label(parent: Node, text: String, size: int, color: Color) -> void:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	parent.add_child(l)
