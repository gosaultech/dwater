# damned_waters/game/src/actors/enemy.gd
# Purpose: everything enemies share. Subclasses only decide how they LOOK
# (_build_body, _pose) and a few quirks (_on_strike, _move_speed). Tuning comes
# from EnemyDB, behaviour from EnemyBrain.
# Analogy: one engine block, different bodywork: a Verdronkene and a Kelderkind
# run the same brain with different numbers and different silhouettes.
class_name Enemy
extends CharacterBody3D

var enemy_id := ""
var kind := "verdronkene"
var def := {}
var brain: EnemyBrain
var emerge := false

var _player: Player
var _heard := false
var _submerged := false
var _voice: AudioStreamPlayer3D
var _push := Vector3.ZERO
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")


func configure(e: Dictionary, _spec: RoomSpec = null) -> void:
	enemy_id = e.id
	kind = e.get("kind", kind)
	position = e.pos
	rotation.y = e.yaw
	emerge = e.get("emerge", false)


# ── virtual hooks ─────────────────────────────────────────────
func _collision_size() -> Vector2:  # radius, height
	return Vector2(0.32, 1.8)


func _build_body() -> void:
	pass


func _pose(_delta: float) -> void:
	pass


func _hidden_offset() -> float:  # how far below the water line we lurk
	return -1.9


func aim_point() -> Vector3:
	return global_position + Vector3.UP * 1.2


func is_weak_hit(hit_pos: Vector3) -> bool:
	return hit_pos.y > global_position.y + float(def.weak_height)


func _on_strike(dist: float) -> void:
	if _player and not _player.is_dead() and dist <= float(def.reach) and _facing_player(deg_to_rad(55.0)):
		_player.take_damage(int(def.damage), global_position)


func _body_node() -> Node3D:
	return null


# ── lifecycle ─────────────────────────────────────────────────
func _ready() -> void:
	add_to_group("enemies")
	def = EnemyDB.get_enemy(kind)
	brain = EnemyDB.brain_for(kind)
	var size := _collision_size()
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = size.x
	cap.height = size.y
	cs.shape = cap
	cs.position.y = size.y / 2.0
	add_child(cs)
	_build_body()
	_voice = AudioStreamPlayer3D.new()
	_voice.unit_size = 4.0
	_voice.bus = "SFX"
	add_child(_voice)
	GameEvents.noise_emitted.connect(_on_noise)
	if emerge:
		_submerged = true
		brain.alert_time = maxf(brain.alert_time, 1.7)
		_body_node().position.y = _hidden_offset()
		collision_layer = 0
		collision_mask = 1
	else:
		collision_layer = 4
		collision_mask = 1 | 2 | 4


func is_dead() -> bool:
	return brain.is_dead()


func is_targetable() -> bool:
	return not _submerged and not is_dead()


func can_be_kicked() -> bool:
	return brain.can_be_kicked()


func _on_noise(at: Vector3, radius: float) -> void:
	if global_position.distance_to(at) <= radius:
		_heard = true


func _physics_process(delta: float) -> void:
	if brain.is_dead():
		_pose(delta)
		velocity = Vector3(0, velocity.y - _gravity * delta, 0) if not is_on_floor() else Vector3.ZERO
		move_and_slide()
		return
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group("player") as Player
	var dist := 99.0
	var sees := false
	if _player and not _player.is_dead():
		var to := _player.global_position - global_position
		to.y = 0.0
		dist = to.length()
		sees = _can_see(to, dist)
	var events := brain.update(delta, sees, _heard, dist)
	_heard = false
	for ev in events:
		_on_brain_event(ev, dist)
	_act(delta)
	_push = _push.move_toward(Vector3.ZERO, 6.0 * delta)
	velocity += _push
	velocity.y = 0.0 if is_on_floor() else velocity.y - _gravity * delta
	move_and_slide()
	_pose(delta)


func _can_see(to: Vector3, dist: float) -> bool:
	if _submerged:
		return dist < 3.2
	if dist > float(def.sight):
		return false
	var fwd := MovementMath.forward_from_yaw(rotation.y)
	if absf(Vector2(fwd.x, fwd.z).angle_to(Vector2(to.x, to.z))) > deg_to_rad(60.0) and dist > 1.5:
		return false
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 1.0,
		_player.global_position + Vector3.UP * 1.3, 1)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _on_brain_event(ev: StringName, dist: float) -> void:
	match ev:
		&"alerted":
			_say_alert()
			if _submerged:
				rise()
		&"windup":
			_say_windup()
		&"strike":
			_on_strike(dist)


func _say_alert() -> void:
	say("enemy_alert")


func _say_windup() -> void:
	say("enemy_windup")


func _act(delta: float) -> void:
	var fwd := MovementMath.forward_from_yaw(rotation.y)
	var want := rotation.y
	if _player:
		want = MovementMath.yaw_towards(global_position, _player.global_position, rotation.y)
	var turn := float(def.turn_rate)
	var v := Vector3.ZERO
	match brain.state:
		EnemyBrain.State.PURSUIT:
			rotation.y = MovementMath.step_yaw(rotation.y, want, turn * delta)
			var align := clampf(cos(wrapf(want - rotation.y, -PI, PI)), 0.2, 1.0)
			v = fwd * float(def.speed) * align
		EnemyBrain.State.ATTACK:
			var striking := brain.time_in_state >= brain.windup_time
			rotation.y = MovementMath.step_yaw(rotation.y, want, (0.0 if striking else turn * 0.6) * delta)
			v = fwd * (_lunge_speed() if striking else 0.0)
		EnemyBrain.State.RETREAT:
			rotation.y = MovementMath.step_yaw(rotation.y, want + PI, turn * delta)
			v = fwd * float(def.speed) * 0.9
		EnemyBrain.State.STAGGER:
			v = -fwd * 0.9
		EnemyBrain.State.ALERT:
			rotation.y = MovementMath.step_yaw(rotation.y, want, turn * 0.5 * delta)
	velocity.x = v.x
	velocity.z = v.z


func _lunge_speed() -> float:
	return 2.2


func _facing_player(max_angle: float) -> bool:
	var to := _player.global_position - global_position
	var fwd := MovementMath.forward_from_yaw(rotation.y)
	return absf(Vector2(fwd.x, fwd.z).angle_to(Vector2(to.x, to.z))) <= max_angle


func rise() -> void:
	_submerged = false
	AudioDirector.play("splash", 0.0, 0.05)
	var tw := create_tween()
	tw.tween_property(_body_node(), "position:y", 0.0, 1.6).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func():
		collision_layer = 4
		collision_mask = 1 | 2 | 4)


## Entry point for every bullet / pellet batch / kick.
func take_hit(damage: float, is_weak: bool, at: Vector3, power: int = 1, knockdown: bool = false) -> void:
	if brain.is_dead():
		return
	if _submerged:
		rise()
	burst(at, 22 if is_weak else 12)
	AudioDirector.play("enemy_hit", -2.0, 0.08)
	GameEvents.enemy_hit.emit(enemy_id, damage, power >= 2 or is_weak)
	for ev in brain.take_hit(damage, power, knockdown):
		match ev:
			&"died":
				_die()
			&"staggered", &"floored":
				_say_alert()
				if _player:
					var away := global_position - _player.global_position
					away.y = 0.0
					_push = away.normalized() * (3.0 if ev == &"floored" else 1.2)


func kick(from: Vector3) -> void:
	var away := global_position - from
	away.y = 0.0
	take_hit(2.0, false, global_position + Vector3.UP * 1.0, 2, true)
	_push = away.normalized() * 4.0
	GameState.bump("kicks")


func _die() -> void:
	collision_layer = 0
	collision_mask = 1
	remove_from_group("enemies")
	say("enemy_death")
	GameState.dead_enemies[enemy_id] = true
	GameState.bump("kills")
	GameEvents.enemy_killed.emit(enemy_id)


func say(sfx: String) -> void:
	var s := AudioDirector.stream(sfx)
	if s:
		_voice.stream = s
		_voice.pitch_scale = randf_range(0.9, 1.05)
		_voice.play()


func burst(at: Vector3, amount: int, color := Color(0.16, 0.05, 0.03)) -> void:
	var p := CPUParticles3D.new()
	p.one_shot = true
	p.explosiveness = 1.0
	p.amount = amount
	p.lifetime = 0.6
	p.spread = 55.0
	p.direction = Vector3.UP
	p.initial_velocity_min = 1.0
	p.initial_velocity_max = 2.8
	var sm := SphereMesh.new()
	sm.radius = 0.015
	sm.height = 0.03
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	sm.material = m
	p.mesh = sm
	p.top_level = true
	add_child(p)
	p.global_position = at
	p.emitting = true
	get_tree().create_timer(1.0).timeout.connect(p.queue_free)
