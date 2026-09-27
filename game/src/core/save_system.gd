# damned_waters/game/src/core/save_system.gd
# Purpose: persist GameState snapshots as JSON in user://saves/.
# Writes go to a temp file first, then rename: a crash mid-save can never
# corrupt the slot (same trick databases use for atomic commits).
class_name SaveSystem
extends RefCounted

const DIR := "user://saves"
const VERSION := 1


static func slot_path(slot: int = 0) -> String:
	return "%s/slot_%d.json" % [DIR, slot]


static func has_save(slot: int = 0) -> bool:
	return FileAccess.file_exists(slot_path(slot))


static func save(data: Dictionary, slot: int = 0) -> Error:
	DirAccess.make_dir_recursive_absolute(DIR)
	var payload := data.duplicate(true)
	payload["version"] = VERSION
	payload["saved_at"] = Time.get_datetime_string_from_system(true)
	var tmp := slot_path(slot) + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string(JSON.stringify(payload, "\t"))
	f.close()
	return DirAccess.rename_absolute(tmp, slot_path(slot))


static func load_slot(slot: int = 0) -> Dictionary:
	if not has_save(slot):
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(slot_path(slot)))
	if typeof(parsed) != TYPE_DICTIONARY or int(parsed.get("version", 0)) != VERSION:
		push_warning("SaveSystem: unreadable or outdated save in slot %d" % slot)
		return {}
	return parsed


static func delete_slot(slot: int = 0) -> void:
	if has_save(slot):
		DirAccess.remove_absolute(slot_path(slot))
