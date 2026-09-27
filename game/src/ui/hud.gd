# damned_waters/game/src/ui/hud.gd
# Purpose: everything drawn over the game world. Messages and choices are
# awaitable (`await hud.message("...")`), which keeps story scripting linear
# and readable in main.gd. While a box is open the game tree is paused.
class_name Hud
extends CanvasLayer

signal _closed(index: int)

const TYPE_SPEED := 55.0  # characters per second

var theme_ := Theme.new()
var _prompt: Label
var _box: PanelContainer
var _title: Label
var _text: Label
var _options: HBoxContainer
var _hint: Label
var _ammo: Label
var _area: Label
var _fade: ColorRect
var _flash: ColorRect
var _boss_box: VBoxContainer
var _boss_bar: ProgressBar
var _perfect: Label
var _weapon_name := "Pistol"
var _open := false
var _choice_labels: Array[Label] = []
var _choice_idx := 0
var _chars := 0.0


func _init() -> void:
	layer = 10
	process_mode = Node.PROCESS_MODE_ALWAYS
	name = "Hud"


static func serif(size: int = 22) -> Font:
	var f := SystemFont.new()
	f.font_names = PackedStringArray(["Georgia", "Times New Roman", "Liberation Serif", "DejaVu Serif", "serif"])
	var fv := FontVariation.new()
	fv.base_font = f
	return fv


func _ready() -> void:
	theme_.default_font = serif()
	theme_.default_font_size = 22
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = theme_
	add_child(root)
	var grain := ColorRect.new()
	grain.set_anchors_preset(Control.PRESET_FULL_RECT)
	grain.mouse_filter = Control.MOUSE_FILTER_IGNORE
	grain.material = ShaderMaterial.new()
	grain.material.shader = preload("res://src/ui/film_grain.gdshader")
	root.add_child(grain)
	_flash = _rect(root, Color(0.5, 0, 0, 0))
	_prompt = _label(root, "", 20, Color(0.85, 0.82, 0.7))
	_prompt.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt.offset_top = -70
	_prompt.offset_bottom = -40
	_prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_ammo = _label(root, "", 26, Color(0.9, 0.88, 0.8))
	_ammo.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	_ammo.offset_left = -220
	_ammo.offset_top = -64
	_ammo.offset_right = -32
	_ammo.offset_bottom = -28
	_ammo.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_ammo.visible = false
	_area = _label(root, "", 26, Color(0.8, 0.78, 0.7))
	_area.modulate.a = 0.0
	_area.position = Vector2(48, 40)
	_build_box(root)
	_build_boss_bar(root)
	_perfect = _label(root, "PERFECT DODGE", 34, Color(0.95, 0.85, 0.55))
	_perfect.modulate.a = 0.0
	_perfect.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_perfect.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_perfect.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_perfect.offset_top = -160
	_fade = _rect(root, Color(0, 0, 0, 1))
	GameEvents.prompt_changed.connect(func(t): _prompt.text = ("[ %s ]" % t) if t != "" else "")
	GameEvents.ammo_changed.connect(func(m, r): _ammo.text = "%s   %d  |  %d" % [_weapon_name, m, r])
	GameEvents.weapon_changed.connect(func(w): _weapon_name = WeaponDB.get_weapon(w).get("name", w))
	GameEvents.perfect_dodge.connect(_on_perfect)
	GameEvents.boss_started.connect(func(n, mx):
		_boss_box.get_child(0).text = n
		_boss_bar.max_value = mx
		_boss_bar.value = mx
		_boss_box.visible = true)
	GameEvents.boss_health_changed.connect(func(hp, _mx): create_tween().tween_property(_boss_bar, "value", hp, 0.15))
	GameEvents.boss_defeated.connect(func(): _boss_box.visible = false)
	GameEvents.aiming_changed.connect(func(on): _ammo.visible = on)
	GameEvents.player_damaged.connect(func(_a, _h): damage_flash())


func _build_box(root: Control) -> void:
	_box = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.02, 0.02, 0.025, 0.88)
	sb.border_color = Color(0.45, 0.4, 0.3, 0.6)
	sb.set_border_width_all(1)
	sb.set_content_margin_all(22)
	_box.add_theme_stylebox_override("panel", sb)
	_box.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_box.offset_left = -520
	_box.offset_right = 520
	_box.offset_top = -250
	_box.offset_bottom = -36
	_box.visible = false
	root.add_child(_box)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	_box.add_child(v)
	_title = _label(v, "", 20, Color(0.75, 0.62, 0.4))
	_text = _label(v, "", 22, Color(0.9, 0.88, 0.82))
	_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_options = HBoxContainer.new()
	_options.alignment = BoxContainer.ALIGNMENT_CENTER
	_options.add_theme_constant_override("separation", 60)
	v.add_child(_options)
	_hint = _label(v, "E  ▸", 16, Color(0.6, 0.55, 0.45))
	_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT


func _label(parent: Node, text: String, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(l)
	return l


func _rect(parent: Node, c: Color) -> ColorRect:
	var r := ColorRect.new()
	r.color = c
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(r)
	return r


func _build_boss_bar(root: Control) -> void:
	_boss_box = VBoxContainer.new()
	_boss_box.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_boss_box.offset_left = -330
	_boss_box.offset_right = 330
	_boss_box.offset_top = 36
	_boss_box.visible = false
	root.add_child(_boss_box)
	var n := _label(_boss_box, "", 22, Color(0.8, 0.9, 0.8))
	n.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_boss_bar = ProgressBar.new()
	_boss_bar.show_percentage = false
	_boss_bar.custom_minimum_size = Vector2(660, 10)
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.05, 0.05, 0.05, 0.8)
	var fg := StyleBoxFlat.new()
	fg.bg_color = Color(0.25, 0.8, 0.55)
	_boss_bar.add_theme_stylebox_override("background", bg)
	_boss_bar.add_theme_stylebox_override("fill", fg)
	_boss_box.add_child(_boss_bar)


func _on_perfect() -> void:
	_perfect.modulate.a = 1.0
	var tw := create_tween()
	tw.set_ignore_time_scale(true)
	tw.tween_interval(0.5)
	tw.tween_property(_perfect, "modulate:a", 0.0, 0.5)


func is_busy() -> bool:
	return _open


## Show text and wait for the player to dismiss it.
func message(text: String, title: String = "") -> void:
	await choice(text, [], title)


## Show text with options; returns the chosen index (0 when no options).
func choice(text: String, options: Array, title: String = "") -> int:
	_open = true
	get_tree().paused = true
	_title.text = title
	_title.visible = title != ""
	_text.text = text
	_text.visible_characters = 0
	_chars = 0.0
	for c in _options.get_children():
		c.queue_free()
	_choice_labels.clear()
	for o in options:
		_choice_labels.append(_label(_options, o, 22, Color(0.9, 0.88, 0.82)))
	_choice_idx = 0
	_options.visible = not options.is_empty()
	_refresh_choice()
	_box.visible = true
	var idx: int = await _closed
	_box.visible = false
	_open = false
	get_tree().paused = false
	return idx


func _refresh_choice() -> void:
	for i in _choice_labels.size():
		_choice_labels[i].text = ("▸ " if i == _choice_idx else "   ") + _choice_labels[i].text.trim_prefix("▸ ").strip_edges()


func _process(delta: float) -> void:
	if _open and _text.visible_characters < _text.text.length():
		_chars += delta * TYPE_SPEED
		_text.visible_characters = int(_chars)


func _unhandled_input(event: InputEvent) -> void:
	if not _open:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("fire"):
		get_viewport().set_input_as_handled()
		if _text.visible_characters < _text.text.length() and _text.visible_characters >= 0:
			_text.visible_characters = -1
			return
		AudioDirector.play("ui_confirm")
		_closed.emit(_choice_idx)
	elif not _choice_labels.is_empty() and (event.is_action_pressed("move_left") or event.is_action_pressed("move_right")):
		get_viewport().set_input_as_handled()
		_choice_idx = (_choice_idx + (1 if event.is_action_pressed("move_right") else -1) + _choice_labels.size()) % _choice_labels.size()
		AudioDirector.play("ui_move")
		_refresh_choice()


func fade_out(seconds: float = 0.5) -> void:
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 1.0, seconds)
	await tw.finished


func fade_in(seconds: float = 0.6) -> void:
	var tw := create_tween()
	tw.tween_property(_fade, "color:a", 0.0, seconds)
	await tw.finished


func set_black(on: bool) -> void:
	_fade.color.a = 1.0 if on else 0.0


func area_title(text: String) -> void:
	_area.text = text
	# Fade via modulate so the drop shadow fades with the text.
	var tw := create_tween()
	tw.tween_property(_area, "modulate:a", 1.0, 0.8)
	tw.tween_interval(2.0)
	tw.tween_property(_area, "modulate:a", 0.0, 1.2)


func damage_flash() -> void:
	_flash.color.a = 0.45
	var tw := create_tween()
	tw.tween_property(_flash, "color:a", 0.0, 0.5)


func hide_prompt() -> void:
	_prompt.text = ""
