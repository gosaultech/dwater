# damned_waters/game/src/core/item_db.gd
# Purpose: static item definitions. Adding an item = adding a row here.
class_name ItemDB
extends RefCounted

const ITEMS := {
	"handgun": {"name": "Pistol", "kind": "weapon", "max_stack": 1,
		"desc": "A police-issue 9mm. You took it from an officer on the Herengracht. She won't need it."},
	"handgun_ammo": {"name": "9mm Rounds", "kind": "ammo", "max_stack": 60,
		"desc": "Pistol ammunition. Make every one count."},
	"first_aid": {"name": "EHBO Kit", "kind": "heal", "heal": 60, "max_stack": 1,
		"desc": "A Dutch first aid kit. Bandages, antiseptic, a foil blanket. Restores a lot of health."},
	"shotgun": {"name": "Jachtgeweer", "kind": "weapon", "max_stack": 1,
		"desc": "A double-barrelled hunting shotgun. Pieter's, from before. Two shells, then pray."},
	"shotgun_shells": {"name": "Shotgun Shells", "kind": "ammo", "max_stack": 30,
		"desc": "12-gauge shells. At close range they put anything down."},
	"cellar_key": {"name": "Cellar Key", "kind": "key", "max_stack": 1,
		"desc": "A heavy iron key, green with verdigris. The paper tag reads 'KELDER'."},
}


static func get_item(id: String) -> Dictionary:
	return ITEMS.get(id, {})


static func max_stack(id: String) -> int:
	return int(ITEMS.get(id, {}).get("max_stack", 1))
