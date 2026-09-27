# damned_waters/game/src/core/firearm.gd
# Purpose: one firearm as a pure model (magazine, fire rate, reload, crits),
# configured from a WeaponDB row. Reserve ammo lives in the Inventory.
class_name Firearm
extends RefCounted

var id := ""
var cfg := {}
var mag := 0
var _cooldown := 0.0
var _reloading := 0.0


func _init(weapon_id: String = "pistol", loaded: int = -1) -> void:
	id = weapon_id
	cfg = WeaponDB.get_weapon(weapon_id)
	mag = int(cfg.mag_size) if loaded < 0 else loaded


func tick(delta: float) -> void:
	_cooldown = maxf(0.0, _cooldown - delta)
	_reloading = maxf(0.0, _reloading - delta)


func is_reloading() -> bool:
	return _reloading > 0.0


func can_fire() -> bool:
	return mag > 0 and _cooldown <= 0.0 and not is_reloading()


func fire() -> bool:
	if not can_fire():
		return false
	mag -= 1
	_cooldown = float(cfg.fire_interval)
	return true


## Takes rounds from `available` reserve; returns how many were used.
func reload(available: int) -> int:
	var taken := mini(int(cfg.mag_size) - mag, available)
	if taken <= 0 or is_reloading():
		return 0
	mag += taken
	_reloading = float(cfg.reload_time)
	return taken


## roll: random 0..1 injected so tests are deterministic.
func damage_for(is_weak: bool, roll: float, distance: float = 0.0) -> float:
	var dmg := float(cfg.damage) * WeaponDB.falloff(id, distance)
	if is_weak and roll < float(cfg.crit_chance):
		dmg *= float(cfg.crit_multiplier)
	return dmg
