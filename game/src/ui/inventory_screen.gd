# damned_waters/game/src/ui/inventory_screen.gd
# Purpose: the classic 8-slot inventory with an ECG condition monitor.
# Opening it pauses the world (you are safe while you rummage, like RE).
class_name InventoryScreen
extends CanvasLayer

signal closed

const COND_COLORS := {"fine": Color(0.3, 0.9, 0.4), "caution": Color(0.95, 0.7, 0.15), "danger": Color(0.95, 0.15, 0.1)}
const COND_BPM := {"fine": 70.0, "caution": 100.0, "danger": 135.0}

var _slots: Array[Label] = []
var _sel := 0
var _desc: Label
var _cond: Label
var _ecg: Line2D
var _t := 0.0
var _root: Control


func _init() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false


func _ready() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = Theme.new()
	_root.theme.default_font = Hud.serif()
	add_child(_root)
	var bg := ColorRect.new()
	bg.color = Color(0, 0, 0, 0.82)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(bg)
	var grid := GridContainer.new()
	grid.columns = 4
	grid.position = Vector2(170, 170)
	grid.add_theme_constant_override("h_separation", 14)
	grid.add_theme_constant_override("v_separation", 14)
	_root.add_child(grid)
	for i in 8:
		var p := PanelContainer.new()
		p.custom_minimum_size = Vector2(170, 100)
		var l := Label.new()
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.add_theme_font_size_override("font_size", 18)
		p.add_child(l)
		grid.add_child(p)
		_slots.append(l)
	_desc = Label.new()
	_desc.position = Vector2(170, 430)
	_desc.size = Vector2(940, 150)
	_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc.add_theme_font_size_override("font_size", 21)
	_root.add_child(_desc)
	var head := Label.new()
	head.text = "INVENTORY"
	head.position = Vector2(170, 110)
	head.add_theme_font_size_override("font_size", 30)
	head.add_theme_color_override("font_color", Color(0.75, 0.62, 0.4))
	_root.add_child(head)
	_cond = Label.new()
	_cond.position = Vector2(930, 110)
	_cond.add_theme_font_size_override("font_size", 26)
	_root.add_child(_cond)
	_ecg = Line2D.new()
	_ecg.width = 2.5
	_ecg.position = Vector2(930, 170)
	_root.add_child(_ecg)
	var help := Label.new()
	help.text = "WASD select    E use    Tab / Esc close"
	help.position = Vector2(170, 620)
	help.add_theme_font_size_override("font_size", 16)
	help.add_theme_color_override("font_color", Color(0.6, 0.55, 0.45))
	_root.add_child(help)


func open() -> void:
	visible = true
	get_tree().paused = true
	_refresh()


func close() -> void:
	visible = false
	get_tree().paused = false
	closed.emit()


func _refresh() -> void:
	var inv := GameState.inventory
	for i in 8:
		var s: Dictionary = inv.slots[i]
		var p := _slots[i].get_parent() as PanelContainer
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0.07, 0.07, 0.08) if i != _sel else Color(0.2, 0.16, 0.1)
		sb.border_color = Color(0.5, 0.42, 0.28) if i == _sel else Color(0.2, 0.2, 0.22)
		sb.set_border_width_all(2)
		p.add_theme_stylebox_override("panel", sb)
		if s.is_empty():
			_slots[i].text = ""
		else:
			var item := ItemDB.get_item(s.id)
			var qty := ("\n%d" % s.count) if item.get("kind") == "ammo" else ""
			for w in WeaponDB.ORDER:
				if WeaponDB.get_weapon(w).item == s.id:
					qty = "\n%d / %d%s" % [GameState.mags.get(w, 0), WeaponDB.get_weapon(w).mag_size,
						"  (equipped)" if GameState.equipped == w else ""]
			_slots[i].text = item.get("name", s.id) + qty
	var cur: Dictionary = inv.slots[_sel]
	_desc.text = "" if cur.is_empty() else ItemDB.get_item(cur.id).get("desc", "")
	var c := GameState.condition()
	_cond.text = c.to_upper()
	_cond.add_theme_color_override("font_color", COND_COLORS[c])
	_ecg.default_color = COND_COLORS[c]


func _process(delta: float) -> void:
	if not visible:
		return
	_t += delta
	var c := GameState.condition()
	var beat: float = 60.0 / COND_BPM[c]
	var pts := PackedVector2Array()
	for i in 90:
		var x := float(i) / 89.0
		var ph := fposmod(_t - (1.0 - x) * 1.5, beat) / beat
		var y := 0.0
		if ph < 0.06:
			y = -sin(ph / 0.06 * PI) * 38.0
		elif ph < 0.1:
			y = sin((ph - 0.06) / 0.04 * PI) * 12.0
		elif ph > 0.3 and ph < 0.42:
			y = -sin((ph - 0.3) / 0.12 * PI) * 7.0
		pts.append(Vector2(x * 220.0, y))
	_ecg.points = pts


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	get_viewport().set_input_as_handled()
	if event.is_action_pressed("inventory") or event.is_action_pressed("pause"):
		close()
		return
	var moved := false
	if event.is_action_pressed("move_right"):
		_sel = (_sel + 1) % 8
		moved = true
	elif event.is_action_pressed("move_left"):
		_sel = (_sel + 7) % 8
		moved = true
	elif event.is_action_pressed("move_back") or event.is_action_pressed("move_forward"):
		_sel = (_sel + 4) % 8
		moved = true
	elif event.is_action_pressed("interact"):
		_use(GameState.inventory.slots[_sel])
	if moved:
		AudioDirector.play("ui_move")
	_refresh()


func _use(s: Dictionary) -> void:
	if s.is_empty():
		return
	var item := ItemDB.get_item(s.id)
	if item.get("kind") == "weapon":
		for w in WeaponDB.ORDER:
			if WeaponDB.get_weapon(w).item == s.id:
				var p := get_tree().get_first_node_in_group("player")
				if p:
					p.equip(w)
		return
	if item.get("kind") == "heal" and GameState.health < GameState.max_health:
		GameState.inventory.remove(s.id, 1)
		GameState.health = mini(GameState.max_health, GameState.health + int(item.heal))
		GameState.bump("heals")
		AudioDirector.play("pickup")
	else:
		AudioDirector.play("ui_confirm")
