# damned_waters/game/src/actors/grachtenvorst.gd
# Purpose: Grachtenvorst ("Canal Prince"), the demo's mini-boss. Many drowned
# bodies fused into one 2.8 m mass that rises from the canal behind the water
# gate. Its heart glows green through the flesh: hits there do 2.5x damage.
# Attacks (all telegraphed, see BossBrain.ATTACKS):
#   SLAM   both arms overhead (1.0 s), crushes a narrow cone in front
#   SWEEP  one arm drawn back (0.8 s), wide 140 degree arc
#   CHARGE hunches low (0.9 s), then barrels forward; hitting a pillar DAZES it
# Phase 2 (50% HP): roars, moves 35% faster, calls a Verdronkene from the water.
class_name Grachtenvorst
extends Enemy

const HIDDEN_Y := -3.2

var boss: BossBrain
var root: Node3D
var core: MeshInstance3D
var _core_light: OmniLight3D
var _arms: Array[Node3D] = []
var _heads: Array[Node3D] = []
var _t := 0.0
var _hit_this_attack := false
var _charge_dir := Vector3.ZERO
var _sinking := false


func _init() -> void:
	kind = "grachtenvorst"


func _collision_size() -> Vector2:
	return Vector2(0.72, 2.4)  # hunched: the cellar ceiling is 2.5 m


func _body_node() -> Node3D:
	return root


func _ready() -> void:
	super._ready()
	boss = BossBrain.new(40.0)
	root.position.y = HIDDEN_Y
	collision_layer = 0
	collision_mask = 1


func is_dead() -> bool:
	return boss != null and boss.is_dead()


func is_targetable() -> bool:
	return boss != null and boss.is_vulnerable()


func can_be_kicked() -> bool:
	return false


func aim_point() -> Vector3:
	return global_position + Vector3.UP * 1.15  # centre mass: aim UP for the heart


func is_weak_hit(hit_pos: Vector3) -> bool:
	return core.global_position.distance_to(hit_pos) < 0.4


func awaken() -> void:
	for ev in boss.awaken():
		_on_boss_event(ev, 99.0)
	GameState.boss_active = true
	GameEvents.boss_started.emit("GRACHTENVORST", boss.max_hp)


var _core_mat: StandardMaterial3D


func _build_body() -> void:
	if CreatureModel.available("grachtenvorst"):
		var m := CharacterFactory.creature("grachtenvorst", "boss") as CreatureModel
		add_child(m.build())
		root = m
		for mi in m.find_children("heart_core*", "MeshInstance3D", true, false):
			core = mi
		if core == null:
			core = MeshKit.sphere(0.2, Color(0.2, 1, 0.6))
			m.joint("heart").add_child(core)
		_core_mat = MaterialLib.get_material("heart").duplicate()
		core.set_surface_override_material(0, _core_mat)
		_core_light = OmniLight3D.new()
		_core_light.light_color = Color(0.3, 1.0, 0.7)
		_core_light.omni_range = 3.5
		core.add_child(_core_light)
		_arms = [m.joint("shoulder_l"), m.joint("shoulder_r")]
		return
	root = Node3D.new()
	root.scale = Vector3.ONE * 0.86
	add_child(root)
	var skin := Color(0.11, 0.15, 0.12)
	var mass := MeshKit.capsule(0.62, 2.3, skin, true)
	mass.position.y = 1.35
	mass.scale = Vector3(1.35, 1.0, 0.9)
	root.add_child(mass)
	for i in 6:  # drowned bodies fused into the mass, each with its own head
		var a := TAU * i / 6.0 + 0.3
		var limb := Node3D.new()
		limb.position = Vector3(cos(a) * 0.62, 0.45 + (i % 3) * 0.45, sin(a) * 0.5)
		limb.rotation = Vector3(0.9 * cos(a * 2.0), -a, 1.1 * sin(a))
		root.add_child(limb)
		var torso := MeshKit.capsule(0.19, 0.8, Color(0.42, 0.48, 0.42), true)
		torso.position.y = 0.3
		limb.add_child(torso)
		var head := MeshKit.sphere(0.11, Color(0.5, 0.55, 0.5), true)
		head.position.y = 0.78
		limb.add_child(head)
	for i in 3:  # three heads, none looking the same way
		var h := Node3D.new()
		h.position = Vector3((i - 1) * 0.32, 2.45 - absf(i - 1) * 0.15, -0.05)
		h.rotation = Vector3(0.3, (i - 1) * 0.5, (i - 1) * 0.4)
		root.add_child(h)
		h.add_child(MeshKit.sphere(0.13 + 0.03 * (1 - absf(i - 1)), Color(0.45, 0.5, 0.44), true))
		var jaw := MeshKit.box(Vector3(0.08, 0.07, 0.04), Color(0.02, 0.01, 0.01))
		jaw.position = Vector3(0, -0.07, -0.12)
		h.add_child(jaw)
		_heads.append(h)
	for side in [-1, 1]:  # two huge slamming arms
		var sh := Node3D.new()
		sh.position = Vector3(0.78 * side, 2.05, 0)
		root.add_child(sh)
		var arm := MeshKit.capsule(0.16, 1.45, skin, true)
		arm.position.y = -0.7
		sh.add_child(arm)
		var fist := MeshKit.sphere(0.26, Color(0.16, 0.2, 0.16), true)
		fist.position.y = -1.45
		sh.add_child(fist)
		_arms.append(sh)
		var small := MeshKit.capsule(0.05, 0.6, Color(0.4, 0.45, 0.4), true)  # a withered human arm
		small.position = Vector3(0.28 * side, 1.1, -0.5)
		small.rotation.x = 0.5
		root.add_child(small)
	for i in 8:  # kelp strands
		var kelp := MeshKit.box(Vector3(0.04, randf_range(0.6, 1.3), 0.01), Color(0.05, 0.12, 0.04), true)
		kelp.position = Vector3(randf_range(-0.7, 0.7), randf_range(1.2, 2.0), randf_range(-0.5, 0.5))
		root.add_child(kelp)
	core = MeshKit.sphere(0.22, Color(0.2, 1.0, 0.6))
	var cm := core.mesh.material as StandardMaterial3D
	cm.emission_enabled = true
	cm.emission = Color(0.25, 1.0, 0.65)
	cm.emission_energy_multiplier = 2.5
	core.position = Vector3(0, 1.75, -0.52)
	root.add_child(core)
	_core_light = OmniLight3D.new()
	_core_light.light_color = Color(0.3, 1.0, 0.7)
	_core_light.omni_range = 3.5
	_core_light.light_energy = 1.2
	core.add_child(_core_light)
	var shadow := MeshKit.blob_shadow(2.2)
	add_child(shadow)


func _physics_process(delta: float) -> void:
	_t += delta
	if boss == null or boss.state == BossBrain.State.DORMANT:
		return
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group("player") as Player
	var dist := 99.0
	if _player and not _player.is_dead():
		dist = Vector2(_player.global_position.x - global_position.x, _player.global_position.z - global_position.z).length()
	if not boss.is_dead():
		for ev in boss.update(delta, dist, randf()):
			_on_boss_event(ev, dist)
		_boss_act(delta, dist)
	else:
		velocity = Vector3.ZERO
	velocity.y = 0.0
	move_and_slide()
	if boss.state == BossBrain.State.ACTIVE and boss.attack == "charge" and get_slide_collision_count() > 0:
		for i in get_slide_collision_count():
			if get_slide_collision(i).get_collider() is StaticBody3D and boss.time_in_state > 0.15:
				for ev in boss.charge_blocked():
					_on_boss_event(ev, dist)
				break
	_boss_pose(delta)


func _boss_act(delta: float, dist: float) -> void:
	var fwd := MovementMath.forward_from_yaw(rotation.y)
	var want := rotation.y
	if _player:
		want = MovementMath.yaw_towards(global_position, _player.global_position, rotation.y)
	var v := Vector3.ZERO
	match boss.state:
		BossBrain.State.STALK:
			rotation.y = MovementMath.step_yaw(rotation.y, want, 1.6 * boss.speed_scale() * delta)
			v = fwd * 0.95 * boss.speed_scale()
		BossBrain.State.WINDUP:
			var track := 0.9 if boss.attack != "charge" else (2.0 if boss.time_in_state < 0.6 else 0.0)
			rotation.y = MovementMath.step_yaw(rotation.y, want, track * delta)
			_charge_dir = fwd
		BossBrain.State.ACTIVE:
			if boss.attack == "charge":
				v = _charge_dir * 4.6 * boss.speed_scale()
				if not _hit_this_attack and _player and dist < 1.6 and _facing_player(deg_to_rad(70.0)):
					_hit_this_attack = true
					_player.take_damage(30, global_position)
	velocity.x = v.x
	velocity.z = v.z


func _on_boss_event(ev: StringName, dist: float) -> void:
	match ev:
		&"emerging":
			AudioDirector.play("boss_emerge")
			var tw := create_tween()
			tw.tween_property(root, "position:y", 0.0, boss.emerge_time).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		&"roar":
			collision_layer = 4
			collision_mask = 1 | 2
			AudioDirector.play("boss_roar")
		&"windup_slam", &"windup_sweep", &"windup_charge":
			_hit_this_attack = false
			say("enemy_windup")
		&"strike_slam", &"strike_sweep":
			var a: Dictionary = BossBrain.ATTACKS[boss.attack]
			AudioDirector.play("boss_slam", -2.0 if boss.attack == "sweep" else 0.0, 0.05)
			if _player and not _player.is_dead() and dist <= float(a.reach) and _facing_player(deg_to_rad(float(a.arc_deg) / 2.0)):
				_player.take_damage(int(a.damage), global_position)
		&"strike_charge":
			AudioDirector.play("boss_roar", -6.0)
		&"dazed":
			AudioDirector.play("boss_slam")
			burst(global_position + Vector3.UP * 2.0 + MovementMath.forward_from_yaw(rotation.y) * 0.6, 30, Color(0.2, 0.2, 0.18))
		&"phase2":
			AudioDirector.play("boss_roar")
		&"summon":
			var r := get_parent()
			if r is Room:
				r.spawn_enemy({"id": "boss_summon", "kind": "verdronkene", "pos": Vector3(1.2, 0, 6.8), "yaw": PI, "emerge": true}, true)


func take_hit(damage: float, is_weak: bool, at: Vector3, _power: int = 1, _knockdown: bool = false) -> void:
	if boss.is_dead():
		return
	var evs := boss.take_damage(damage, is_weak)
	if evs.has(&"deflected"):
		return
	burst(at, 26 if is_weak else 14, Color(0.1, 0.35, 0.2) if is_weak else Color(0.12, 0.08, 0.05))
	AudioDirector.play("enemy_hit", 0.0, 0.1)
	GameEvents.enemy_hit.emit(enemy_id, damage, is_weak)
	GameEvents.boss_health_changed.emit(boss.hp, boss.max_hp)
	for ev in evs:
		if ev == &"died":
			_boss_die()
		elif ev == &"staggered":
			AudioDirector.play("boss_roar", -4.0)


func _boss_die() -> void:
	collision_layer = 0
	remove_from_group("enemies")
	AudioDirector.play("boss_roar")
	GameState.dead_enemies[enemy_id] = true
	GameState.boss_active = false
	GameState.bump("kills")
	GameEvents.enemy_killed.emit(enemy_id)
	GameEvents.boss_defeated.emit()
	var tw := create_tween()
	tw.tween_interval(1.0)
	tw.tween_callback(func(): AudioDirector.play("splash"))
	tw.tween_property(root, "position:y", HIDDEN_Y, 3.5).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


func _boss_pose(delta: float) -> void:
	var k := MovementMath.smoothing_alpha(10.0, delta)
	var arm := [0.3, 0.3]
	var lean := 0.0
	var tsec := boss.time_in_state
	match boss.state:
		BossBrain.State.STALK:
			arm = [0.35 + sin(_t * 2.0) * 0.2, 0.35 - sin(_t * 2.0) * 0.2]
			lean = 0.1
		BossBrain.State.WINDUP:
			match boss.attack:
				"slam":
					arm = [2.45, 2.45]
					lean = -0.25
				"sweep":
					arm = [0.4, 2.2]
					lean = -0.1
				"charge":
					arm = [0.9, 0.9]
					lean = 0.45
		BossBrain.State.ACTIVE:
			match boss.attack:
				"slam":
					arm = [0.9, 0.9]
					lean = 0.4
				"sweep":
					arm = [0.4, 1.2]
					root.rotation.y = lerpf(root.rotation.y, -1.2, k * 2.0)
				"charge":
					arm = [1.3, 1.3]
					lean = 0.5
		BossBrain.State.STAGGER, BossBrain.State.DAZED:
			arm = [-0.3, -0.2]
			lean = -0.3 + sin(tsec * 6.0) * 0.08
		BossBrain.State.PHASE_SHIFT:
			arm = [2.4, 2.4]
			lean = -0.4
	if boss.state != BossBrain.State.ACTIVE:
		root.rotation.y = lerpf(root.rotation.y, 0.0, k)
	_arms[0].rotation.x = lerpf(_arms[0].rotation.x, arm[0], k)
	_arms[1].rotation.x = lerpf(_arms[1].rotation.x, arm[1], k)
	root.rotation.x = lerpf(root.rotation.x, -lean, k)
	for i in _heads.size():
		_heads[i].rotation.z = sin(_t * (1.3 + i * 0.7) + i) * 0.35
	var pulse := 1.0 + sin(_t * (9.0 if boss.phase == 2 else 4.5)) * 0.5
	var cm: StandardMaterial3D = _core_mat if _core_mat else core.mesh.material
	cm.emission_energy_multiplier = 1.8 * pulse
	_core_light.light_energy = 0.8 * pulse
