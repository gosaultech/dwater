# damned_waters/game/src/core/enemy_db.gd
# Purpose: enemy tuning table (see docs/enemy_design.md for the design intent).
# Every wind-up stays >= 0.5 s: the bible's readability rule is a hard floor.
class_name EnemyDB
extends RefCounted

const ENEMIES := {
	"verdronkene": {"name": "Verdronkene", "hp": 6.0, "speed": 0.85, "turn_rate": 2.2,
		"sight": 9.0, "attack_range": 1.25, "reach": 1.7, "windup": 0.85, "recovery": 1.1,
		"damage": 20, "alert_time": 0.7, "stagger_time": 0.4, "stagger_immunity": 1.2,
		"floor_time": 2.4, "retreat_time": 0.0, "weak_height": 1.5},
	"kelderkind": {"name": "Kelderkind", "hp": 3.0, "speed": 2.7, "turn_rate": 7.0,
		"sight": 11.0, "attack_range": 2.4, "reach": 2.2, "windup": 0.5, "recovery": 0.7,
		"damage": 12, "alert_time": 0.35, "stagger_time": 0.5, "stagger_immunity": 0.8,
		"floor_time": 1.6, "retreat_time": 1.3, "weak_height": 0.3},
}


static func get_enemy(kind: String) -> Dictionary:
	return ENEMIES.get(kind, ENEMIES.verdronkene)


static func brain_for(kind: String) -> EnemyBrain:
	var d := get_enemy(kind)
	var b := EnemyBrain.new(d.hp)
	b.alert_time = d.alert_time
	b.attack_range = d.attack_range
	b.windup_time = d.windup
	b.recovery_time = d.recovery
	b.stagger_time = d.stagger_time
	b.stagger_immunity = d.stagger_immunity
	b.floor_time = d.floor_time
	b.retreat_time = d.retreat_time
	return b
