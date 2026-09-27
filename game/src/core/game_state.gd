# damned_waters/game/src/core/game_state.gd
# Purpose: the single source of truth for "where is the player in the story"
# (autoload "GameState"): health, inventory, magazine, flags, dead enemies,
# stats. Everything a save file needs, and nothing a save file doesn't.
extends Node

const START_ROOM := "gang"
const START_SPAWN := "start"

var health := 100
var max_health := 100
var inventory := Inventory.new(8)
var mags := {"pistol": 10, "shotgun": 2}  # rounds in each magazine
var equipped := "pistol"
var flags := {}          # String -> true   (story switches, picked items, unlocked doors)
var dead_enemies := {}   # String -> true
var room_id := START_ROOM
var player_pos := Vector3.ZERO
var player_yaw := 0.0
var play_time := 0.0
var stats := {}
var boss_active := false
var control_scheme := "modern"  # a setting: survives New Game
var in_game := false


func reset_new_game() -> void:
	health = max_health
	inventory = Inventory.new(8)
	inventory.add("handgun", 1)
	inventory.add("handgun_ammo", 15)
	mags = {"pistol": 10, "shotgun": 2}
	equipped = "pistol"
	flags = {}
	dead_enemies = {}
	room_id = START_ROOM
	play_time = 0.0
	stats = {"shots": 0, "hits": 0, "kills": 0, "saves": 0, "deaths": 0, "damage_taken": 0, "heals": 0,
		"perfect_dodges": 0, "kicks": 0}
	boss_active = false


func _process(delta: float) -> void:
	if in_game and not get_tree().paused:
		play_time += delta


func has_flag(f: String) -> bool:
	return flags.has(f)


func set_flag(f: String) -> void:
	if not flags.has(f):
		flags[f] = true
		GameEvents.flag_set.emit(f)


## Weapons you actually carry, in cycle order.
func owned_weapons() -> Array:
	return WeaponDB.ORDER.filter(func(w): return inventory.has(WeaponDB.get_weapon(w).item))


func bump(stat: String, by: int = 1) -> void:
	stats[stat] = int(stats.get(stat, 0)) + by


## RE-style health bands: shown in the inventory, and "danger" slows you down.
func condition() -> String:
	var r := float(health) / float(max_health)
	if r > 0.66:
		return "fine"
	if r > 0.33:
		return "caution"
	return "danger"


func to_dict() -> Dictionary:
	return {
		"health": health, "inventory": inventory.to_array(), "mags": mags.duplicate(), "equipped": equipped,
		"flags": flags.duplicate(), "dead_enemies": dead_enemies.duplicate(),
		"room_id": room_id, "player_pos": [player_pos.x, player_pos.y, player_pos.z],
		"player_yaw": player_yaw, "play_time": play_time, "stats": stats.duplicate(),
	}


func from_dict(d: Dictionary) -> void:
	health = int(d.get("health", max_health))
	inventory = Inventory.from_array(d.get("inventory", []))
	mags = d.get("mags", {"pistol": 10, "shotgun": 2})
	for k in mags:
		mags[k] = int(mags[k])
	equipped = String(d.get("equipped", "pistol"))
	flags = d.get("flags", {})
	dead_enemies = d.get("dead_enemies", {})
	room_id = String(d.get("room_id", START_ROOM))
	var p: Array = d.get("player_pos", [0, 0, 0])
	player_pos = Vector3(p[0], p[1], p[2])
	player_yaw = float(d.get("player_yaw", 0.0))
	play_time = float(d.get("play_time", 0.0))
	stats = d.get("stats", {})
	boss_active = false
