# damned_waters/game/src/core/weapon_db.gd
# Purpose: weapon tuning table. Balance lives here, not in code paths.
# stagger_power 2 ignores an enemy's stagger immunity (heavy hits always land).
class_name WeaponDB
extends RefCounted

const WEAPONS := {
	"pistol": {"name": "Pistol", "item": "handgun", "ammo": "handgun_ammo", "mag_size": 10,
		"fire_interval": 0.42, "reload_time": 1.4, "damage": 1.0, "pellets": 1, "spread_deg": 0.0,
		"range": 25.0, "crit_chance": 0.12, "crit_multiplier": 4.0, "stagger_power": 1,
		"knockdown_hits": 0, "noise": 16.0, "sfx": "gunshot"},
	"shotgun": {"name": "Jachtgeweer", "item": "shotgun", "ammo": "shotgun_shells", "mag_size": 2,
		"fire_interval": 0.75, "reload_time": 2.1, "damage": 0.8, "pellets": 8, "spread_deg": 6.5,
		"range": 12.0, "crit_chance": 0.0, "crit_multiplier": 1.0, "stagger_power": 2,
		"knockdown_hits": 5, "noise": 22.0, "sfx": "shotgun"},
}
const ORDER := ["pistol", "shotgun"]


static func get_weapon(id: String) -> Dictionary:
	return WEAPONS.get(id, {})


## Pellet damage falls off with distance (full to 4 m, half to 8 m, none beyond range).
static func falloff(id: String, distance: float) -> float:
	var w := get_weapon(id)
	if int(w.get("pellets", 1)) == 1:
		return 1.0 if distance <= float(w.range) else 0.0
	if distance <= 4.0:
		return 1.0
	if distance <= 8.0:
		return 0.5
	return 0.0 if distance > float(w.range) else 0.25
