# damned_waters/game/src/actors/verdronkene.gd
# Purpose: Verdronkene (The Drowned). Bloated, waterlogged townsfolk.
# Design: slow, turns slowly, readable 0.85 s arms-up tell, dangerous in pairs
# in narrow Amsterdam halls. Silhouette: hunched, arms forward, head lolling.
# Counterplay: shoot to stagger, kick when staggered, or walk around it.
class_name Verdronkene
extends Enemy

var body: ActorVisual
var _gurgle_t := 3.0
var _drips: CPUParticles3D


func _init() -> void:
	kind = "verdronkene"


func _body_node() -> Node3D:
	return body


func _build_body() -> void:
	_drips = _make_drips()
	var variant := "verdronkene_netted" if enemy_id.hash() % 2 else "verdronkene_veiled"
	body = CharacterFactory.creature(variant, "humanoid")
	if body == null:
		body = CharacterFactory.create("verdronkene")  # else an installed rigged model
	if body != null:
		add_child(body.build())
		if body.head:
			body.head.add_child(_drips)
		return
	var m := Mannequin.new()
	body = m
	m.bulk = 1.25
	m.wet = true
	var tint := randf_range(-0.03, 0.03)
	m.palette = {"skin": Color(0.46 + tint, 0.53, 0.45 + tint), "top": Color(0.2, 0.24, 0.2),
		"legs": Color(0.08, 0.09, 0.09), "hair": Color(0.1, 0.13, 0.08), "shoes": Color(0.02, 0.02, 0.02)}
	add_child(body.build())
	# Slack jaw, milky eyes, algae growth: the face reads even at fixed-camera distance.
	var mouth := _blob(Vector3(0.07, 0.06, 0.03), Color(0.02, 0.01, 0.01))
	mouth.position = Vector3(0, -0.05, -0.09)
	body.head.add_child(mouth)
	for side in [-1, 1]:
		var eye := _blob(Vector3(0.025, 0.02, 0.01), Color(0.75, 0.8, 0.7))
		eye.position = Vector3(0.035 * side, 0.02, -0.095)
		body.head.add_child(eye)
	for i in 5:
		var algae := _blob(Vector3(randf_range(0.08, 0.16), randf_range(0.06, 0.12), 0.03), Color(0.06, 0.12, 0.04))
		algae.position = Vector3(randf_range(-0.15, 0.15), randf_range(0.1, 0.55), -0.13 if i % 2 == 0 else 0.13)
		m.torso.add_child(algae)
	body.head.add_child(_drips)


func _make_drips() -> CPUParticles3D:
	var _drips := CPUParticles3D.new()
	_drips.amount = 10
	_drips.lifetime = 0.8
	_drips.position = Vector3(0, -0.08, -0.08)
	_drips.direction = Vector3.DOWN
	_drips.spread = 12.0
	_drips.initial_velocity_min = 0.1
	_drips.initial_velocity_max = 0.3
	var sm := SphereMesh.new()
	sm.radius = 0.008
	sm.height = 0.02
	sm.material = StandardMaterial3D.new()
	sm.material.albedo_color = Color(0.1, 0.16, 0.12)
	_drips.mesh = sm
	return _drips


func _blob(size: Vector3, c: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 0.3
	bm.material = m
	mi.mesh = bm
	return mi


func aim_point() -> Vector3:
	return global_position + Vector3.UP * 1.25


func _pose(delta: float) -> void:
	match brain.state:
		EnemyBrain.State.PURSUIT, EnemyBrain.State.RETREAT:
			body.pose = "shamble"
		EnemyBrain.State.ATTACK:
			body.pose = "strike" if brain.time_in_state >= brain.windup_time else "windup"
		EnemyBrain.State.STAGGER:
			body.pose = "stagger"
		EnemyBrain.State.FLOORED:
			body.pose = "floored"
		EnemyBrain.State.DEAD:
			body.pose = "dead"
			_drips.emitting = false
		_:
			body.pose = "idle"
	body.speed = Vector2(velocity.x, velocity.z).length()
	body.animate(delta)
	if not brain.is_dead() and not _submerged:
		_gurgle_t -= delta
		if _gurgle_t <= 0.0:
			_gurgle_t = randf_range(3.0, 7.0)
			say("enemy_gurgle")
