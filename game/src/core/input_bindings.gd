# damned_waters/game/src/core/input_bindings.gd
# Purpose: register every input action in code (autoload "InputBindings").
# One readable table instead of hundreds of serialized lines in project.godot.
# Keys use physical keycodes, so WASD stays WASD on any keyboard layout.
extends Node

const BINDINGS := {
	"move_forward": [{"key": KEY_W}, {"key": KEY_UP}, {"axis": JOY_AXIS_LEFT_Y, "dir": -1.0}, {"joy": JOY_BUTTON_DPAD_UP}],
	"move_back": [{"key": KEY_S}, {"key": KEY_DOWN}, {"axis": JOY_AXIS_LEFT_Y, "dir": 1.0}, {"joy": JOY_BUTTON_DPAD_DOWN}],
	"move_left": [{"key": KEY_A}, {"key": KEY_LEFT}, {"axis": JOY_AXIS_LEFT_X, "dir": -1.0}, {"joy": JOY_BUTTON_DPAD_LEFT}],
	"move_right": [{"key": KEY_D}, {"key": KEY_RIGHT}, {"axis": JOY_AXIS_LEFT_X, "dir": 1.0}, {"joy": JOY_BUTTON_DPAD_RIGHT}],
	"run": [{"key": KEY_SHIFT}, {"joy": JOY_BUTTON_B}],
	"interact": [{"key": KEY_E}, {"key": KEY_ENTER}, {"joy": JOY_BUTTON_A}],
	"aim": [{"mouse": MOUSE_BUTTON_RIGHT}, {"key": KEY_K}, {"axis": JOY_AXIS_TRIGGER_LEFT, "dir": 1.0}],
	"fire": [{"mouse": MOUSE_BUTTON_LEFT}, {"key": KEY_J}, {"key": KEY_SPACE}, {"axis": JOY_AXIS_TRIGGER_RIGHT, "dir": 1.0}],
	"reload": [{"key": KEY_R}, {"joy": JOY_BUTTON_X}],
	"quick_turn": [{"key": KEY_Q}, {"joy": JOY_BUTTON_LEFT_SHOULDER}],
	"dodge": [{"key": KEY_C}, {"key": KEY_ALT}, {"joy": JOY_BUTTON_RIGHT_SHOULDER}],
	"weapon_cycle": [{"key": KEY_F}, {"joy": JOY_BUTTON_RIGHT_STICK}],
	"weapon_1": [{"key": KEY_1}],
	"weapon_2": [{"key": KEY_2}],
	"inventory": [{"key": KEY_TAB}, {"key": KEY_I}, {"joy": JOY_BUTTON_Y}],
	"pause": [{"key": KEY_ESCAPE}, {"joy": JOY_BUTTON_START}],
	"toggle_controls": [{"key": KEY_T}, {"joy": JOY_BUTTON_BACK}],
	"debug_overlay": [{"key": KEY_F1}],
}


func _enter_tree() -> void:
	install()


static func install() -> void:
	# Menus use Godot's built-in ui_* actions; add WASD/E so one hand suffices.
	for extra in [["ui_up", KEY_W], ["ui_down", KEY_S], ["ui_accept", KEY_E]]:
		var ev := InputEventKey.new()
		ev.physical_keycode = extra[1]
		if not InputMap.action_has_event(extra[0], ev):
			InputMap.action_add_event(extra[0], ev)
	for action in BINDINGS:
		if InputMap.has_action(action):
			continue
		InputMap.add_action(action, 0.25)
		for b in BINDINGS[action]:
			InputMap.action_add_event(action, _event_for(b))


static func _event_for(b: Dictionary) -> InputEvent:
	if b.has("key"):
		var k := InputEventKey.new()
		k.physical_keycode = b.key
		return k
	if b.has("mouse"):
		var m := InputEventMouseButton.new()
		m.button_index = b.mouse
		return m
	if b.has("axis"):
		var a := InputEventJoypadMotion.new()
		a.axis = b.axis
		a.axis_value = b.dir
		return a
	var j := InputEventJoypadButton.new()
	j.button_index = b.joy
	return j
