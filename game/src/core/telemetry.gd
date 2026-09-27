# damned_waters/game/src/core/telemetry.gd
# Purpose: session telemetry (autoload "Telemetry"). Appends JSON lines to
# user://telemetry/<session>.jsonl; tools/telemetry/ingest.py loads them into
# SQLite for analysis. Hot path cost: one string append into a RAM buffer.
# Disk I/O happens every FLUSH_SECONDS, never inside gameplay code.
extends Node

const DIR := "user://telemetry"
const FLUSH_SECONDS := 2.0
const PERF_SECONDS := 10.0

var session_id := ""
var _buf := PackedStringArray()
var _seq := 0
var _path := ""
var _flush_t := 0.0
var _perf_t := 0.0
var _frames := 0
var _worst_ms := 0.0
var _started_ms := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_started_ms = Time.get_ticks_msec()
	session_id = "%d_%06x" % [int(Time.get_unix_time_from_system()), randi() & 0xFFFFFF]
	DirAccess.make_dir_recursive_absolute(DIR)
	_path = "%s/%s.jsonl" % [DIR, session_id]
	log_event("session_start", {
		"godot": Engine.get_version_info().string, "os": OS.get_name(),
		"renderer": str(ProjectSettings.get_setting("rendering/renderer/rendering_method")),
		"build": "demo-0.1", "debug": OS.is_debug_build()})
	GameEvents.room_entered.connect(func(r): log_event("room_enter", {"room": r}))
	GameEvents.camera_cut.connect(func(r, s): log_event("camera_cut", {"room": r, "shot": s}))
	GameEvents.shot_fired.connect(func(h, e): log_event("shot", {"hit": h, "enemy": e}))
	GameEvents.enemy_killed.connect(func(e): log_event("enemy_killed", {"enemy": e}))
	GameEvents.player_damaged.connect(func(a, hp): log_event("damage", {"amount": a, "health": hp}))
	GameEvents.player_died.connect(func(): log_event("death", {"room": GameState.room_id}))
	GameEvents.item_picked.connect(func(i, c): log_event("pickup", {"item": i, "count": c}))
	GameEvents.game_saved.connect(func(): log_event("save", {"room": GameState.room_id}))
	GameEvents.demo_completed.connect(func(s): log_event("demo_complete", s))


func log_event(event: String, data: Dictionary = {}) -> void:
	_seq += 1
	_buf.append(JSON.stringify({
		"v": 1, "session": session_id, "seq": _seq,
		"ts": Time.get_unix_time_from_system(), "t_ms": Time.get_ticks_msec() - _started_ms,
		"event": event, "data": data}))


func _process(delta: float) -> void:
	_frames += 1
	_worst_ms = maxf(_worst_ms, delta * 1000.0)
	_perf_t += delta
	if _perf_t >= PERF_SECONDS:
		log_event("perf", {"fps": snappedf(_frames / _perf_t, 0.1), "worst_frame_ms": snappedf(_worst_ms, 0.01),
			"room": GameState.room_id})
		_perf_t = 0.0
		_frames = 0
		_worst_ms = 0.0
	_flush_t += delta
	if _flush_t >= FLUSH_SECONDS:
		flush()


func flush() -> void:
	_flush_t = 0.0
	if _buf.is_empty():
		return
	var f := FileAccess.open(_path, FileAccess.READ_WRITE if FileAccess.file_exists(_path) else FileAccess.WRITE)
	if f == null:
		return
	f.seek_end()
	f.store_string("\n".join(_buf) + "\n")
	f.close()
	_buf.clear()


func end_session(status: String = "clean") -> void:
	log_event("session_end", {"status": status, "runtime_s": (Time.get_ticks_msec() - _started_ms) / 1000.0})
	flush()


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		if not _buf.is_empty() or what == NOTIFICATION_WM_CLOSE_REQUEST:
			end_session("closed" if what == NOTIFICATION_WM_CLOSE_REQUEST else "shutdown")
