# damned_waters/game/src/core/enemy_brain.gd
# Purpose: common enemy mind as a pure state machine (dev bible Part VI):
#   IDLE -> ALERT -> PURSUIT -> ATTACK -> RECOVERY (-> RETREAT) (+ STAGGER, FLOORED, DEAD)
# Nodes feed it senses and act on the events it returns. Tuning comes from
# EnemyDB, so a Verdronkene and a Kelderkind share one brain with different
# personalities (like two drivers with the same car but different habits).
class_name EnemyBrain
extends RefCounted

enum State { IDLE, ALERT, PURSUIT, ATTACK, RECOVERY, RETREAT, STAGGER, FLOORED, DEAD }

var max_hp := 6.0
var alert_time := 0.7
var attack_range := 1.25
var windup_time := 0.85
var strike_window := 0.25
var recovery_time := 1.1
var retreat_time := 0.0      # > 0: hit-and-run behaviour after each attack
var stagger_time := 0.4
var stagger_immunity := 1.2
var floor_time := 2.4
var give_up_time := 6.0

var state: State = State.IDLE
var hp := 6.0
var time_in_state := 0.0
var _stagger_cooldown := 0.0
var _lost_timer := 0.0
var _struck := false


func _init(hit_points: float = 6.0) -> void:
	max_hp = hit_points
	hp = hit_points


func is_dead() -> bool:
	return state == State.DEAD


func can_be_kicked() -> bool:
	return state == State.STAGGER


func _go(next: State) -> void:
	state = next
	time_in_state = 0.0
	if next == State.ATTACK:
		_struck = false


## sees: clear line of sight inside the view cone; heard: a noise reached us.
func update(delta: float, sees: bool, heard: bool, distance: float) -> Array[StringName]:
	var events: Array[StringName] = []
	time_in_state += delta
	_stagger_cooldown = maxf(0.0, _stagger_cooldown - delta)
	match state:
		State.IDLE:
			if sees or heard:
				_go(State.ALERT)
				events.append(&"alerted")
		State.ALERT:
			if time_in_state >= alert_time and (sees or heard or distance < attack_range * 3.0):
				_go(State.PURSUIT)
				events.append(&"pursue")
			elif time_in_state >= alert_time * 4.0:
				_go(State.IDLE)
				events.append(&"calmed")
		State.PURSUIT:
			_lost_timer = 0.0 if sees else _lost_timer + delta
			if distance <= attack_range:
				_go(State.ATTACK)
				events.append(&"windup")
			elif _lost_timer >= give_up_time:
				_go(State.IDLE)
				events.append(&"calmed")
		State.ATTACK:
			if not _struck and time_in_state >= windup_time:
				_struck = true
				events.append(&"strike")
			elif time_in_state >= windup_time + strike_window:
				_go(State.RECOVERY)
		State.RECOVERY:
			if time_in_state >= recovery_time:
				_go(State.RETREAT if retreat_time > 0.0 else State.PURSUIT)
				events.append(&"retreat" if retreat_time > 0.0 else &"pursue")
		State.RETREAT:
			if time_in_state >= retreat_time:
				_go(State.PURSUIT)
				events.append(&"pursue")
		State.STAGGER:
			if time_in_state >= stagger_time:
				_go(State.PURSUIT)
				events.append(&"pursue")
		State.FLOORED:
			if time_in_state >= floor_time:
				_go(State.PURSUIT)
				events.append(&"got_up")
	return events


## power 1 = normal hit; power >= 2 = heavy hit that ignores stagger immunity.
## knockdown = true floors the enemy (shotgun point blank, kicks).
func take_hit(damage: float, power: int = 1, knockdown: bool = false) -> Array[StringName]:
	if is_dead():
		return []
	hp -= damage
	if hp <= 0.0:
		_go(State.DEAD)
		return [&"died"]
	if knockdown and state != State.FLOORED:
		_go(State.FLOORED)
		return [&"floored"]
	if state == State.FLOORED:
		return [&"hurt"]
	if _stagger_cooldown <= 0.0 or power >= 2:
		_stagger_cooldown = stagger_immunity
		_go(State.STAGGER)
		return [&"staggered"]
	return [&"hurt"]
