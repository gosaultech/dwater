# damned_waters/game/src/core/inventory.gd
# Purpose: a fixed number of slots, each holding one stack. Scarcity of slots
# is a design lever (classic survival horror), so the model enforces it.
class_name Inventory
extends RefCounted

var slots: Array = []  # each: {} (empty) or {"id": String, "count": int}


func _init(size: int = 8) -> void:
	slots.resize(size)
	for i in size:
		slots[i] = {}


## Returns the amount that did NOT fit.
func add(id: String, count: int) -> int:
	var left := count
	var cap := ItemDB.max_stack(id)
	for s in slots:
		if left > 0 and not s.is_empty() and s.id == id and s.count < cap:
			var put := mini(cap - s.count, left)
			s.count += put
			left -= put
	for i in slots.size():
		if left <= 0:
			break
		if slots[i].is_empty():
			var put := mini(cap, left)
			slots[i] = {"id": id, "count": put}
			left -= put
	return left


## Returns the amount actually removed.
func remove(id: String, count: int) -> int:
	var removed := 0
	for i in range(slots.size() - 1, -1, -1):
		var s: Dictionary = slots[i]
		if removed >= count or s.is_empty() or s.id != id:
			continue
		var take := mini(s.count, count - removed)
		s.count -= take
		removed += take
		if s.count <= 0:
			slots[i] = {}
	return removed


func count_of(id: String) -> int:
	var n := 0
	for s in slots:
		if not s.is_empty() and s.id == id:
			n += s.count
	return n


func has(id: String) -> bool:
	return count_of(id) > 0


func free_slots() -> int:
	return slots.filter(func(s): return s.is_empty()).size()


func to_array() -> Array:
	return slots.duplicate(true)


static func from_array(data: Array) -> Inventory:
	var inv := Inventory.new(data.size())
	for i in data.size():
		var s: Dictionary = data[i]
		inv.slots[i] = {} if s.is_empty() else {"id": String(s.id), "count": int(s.count)}
	return inv
