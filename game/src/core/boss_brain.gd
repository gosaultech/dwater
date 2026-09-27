# damned_waters/game/src/core/boss_brain.gd
# Purpose: the Grachtenvorst's mind. A pure, deterministic boss state machine:
#   DORMANT -> EMERGE -> STALK -> (SLAM | SWEEP | CHARGE) -> RECOVER -> STALK ...
# Phase 2 at 50% HP: faster, shorter tells, summons one Verdronkene.
# Break mechanic: every `break_threshold` damage staggers it (rewards aggression).
# Charging into a pillar dazes it (rewards using the room).
# RNG rolls are injected so tests can replay exact fights.
class_name BossBrain
extends RefCounted

enum State { DORMANT, EMERGE, STALK, WINDUP, ACTIVE, RECOVER, STAGGER, DAZED, PHASE_SHIFT, DEAD }

const ATTACKS := {  # windup is the readable tell; active = hitbox live time
	"slam": {"windup": 1.0, "active": 0.2, "recover": 1.2, "damage": 35, "reach": 2.3, "arc_deg": 70.0},
	"sweep": {"windup": 0.8, "active": 0.25, "recover": 0.9, "damage": 25, "reach": 2.7, "arc_deg": 140.0},
	"charge": {"windup": 0.9, "active": 1.3, "recover": 1.0, "damage": 30, "reach": 1.4, "arc_deg": 90.0},
}

var max_hp := 40.0
var hp := 40.0
var phase := 1
var state: State = State.DORMANT
var attack := ""
var time_in_state := 0.0
var emerge_time := 2.4
var break_threshold := 8.0
var stagger_time := 1.4
var dazed_time := 2.2
var phase_shift_time := 1.6
var close_range := 2.6
var charge_min_range := 4.5
var _break_accum := 0.0
var _struck := false
var _last_close := ""


func _init(hit_points: float = 40.0) -> void:
	max_hp = hit_points
	hp = hit_points


func speed_scale() -> float:
	return 1.35 if phase == 2 else 1.0


func windup_scale() -> float:
	return 0.8 if phase == 2 else 1.0


func is_dead() -> bool:
	return state == State.DEAD


func is_vulnerable() -> bool:
	return state not in [State.DORMANT, State.EMERGE, State.PHASE_SHIFT, State.DEAD]


func _go(next: State) -> void:
	state = next
	time_in_state = 0.0
	_struck = false


func awaken() -> Array[StringName]:
	if state != State.DORMANT:
		return []
	_go(State.EMERGE)
	return [&"emerging"]


## roll: random 0..1 used to vary close-range attacks.
func update(delta: float, distance: float, roll: float) -> Array[StringName]:
	var ev: Array[StringName] = []
	time_in_state += delta
	match state:
		State.EMERGE:
			if time_in_state >= emerge_time:
				_go(State.STALK)
				ev.append(&"roar")
		State.STALK:
			if distance <= close_range:
				attack = _pick_close(roll)
				_go(State.WINDUP)
				ev.append(StringName("windup_" + attack))
			elif distance >= charge_min_range and time_in_state > 1.2:
				attack = "charge"
				_go(State.WINDUP)
				ev.append(&"windup_charge")
		State.WINDUP:
			if time_in_state >= float(ATTACKS[attack].windup) * windup_scale():
				_go(State.ACTIVE)
				ev.append(StringName("strike_" + attack))
		State.ACTIVE:
			if time_in_state >= float(ATTACKS[attack].active):
				_go(State.RECOVER)
				ev.append(&"recover")
		State.RECOVER:
			if time_in_state >= float(ATTACKS[attack].recover) * windup_scale():
				_go(State.STALK)
		State.STAGGER:
			if time_in_state >= stagger_time:
				_go(State.STALK)
		State.DAZED:
			if time_in_state >= dazed_time:
				_go(State.STALK)
				ev.append(&"roar")
		State.PHASE_SHIFT:
			if time_in_state >= phase_shift_time:
				_go(State.STALK)
				ev.append(&"summon")
	return ev


func _pick_close(roll: float) -> String:
	# Never the same close attack three times: players learn a rhythm, not a coin flip.
	var pick := "slam" if roll < 0.5 else "sweep"
	if pick == _last_close and roll > 0.25 and roll < 0.75:
		pick = "sweep" if pick == "slam" else "slam"
	_last_close = pick
	return pick


## The charge hit a pillar or wall: dazed, wide open.
func charge_blocked() -> Array[StringName]:
	if state == State.ACTIVE and attack == "charge":
		_go(State.DAZED)
		return [&"dazed"]
	return []


func take_damage(damage: float, weak_point: bool) -> Array[StringName]:
	if not is_vulnerable():
		return [&"deflected"]
	var dmg := damage * (2.5 if weak_point else 1.0)
	hp -= dmg
	if hp <= 0.0:
		hp = 0.0
		_go(State.DEAD)
		return [&"died"]
	if phase == 1 and hp <= max_hp * 0.5:
		phase = 2
		_break_accum = 0.0
		_go(State.PHASE_SHIFT)
		return [&"phase2"]
	_break_accum += dmg
	if _break_accum >= break_threshold and state in [State.STALK, State.WINDUP, State.RECOVER]:
		_break_accum = 0.0
		_go(State.STAGGER)
		return [&"staggered"]
	return [&"hurt"]
