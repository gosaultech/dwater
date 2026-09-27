# damned_waters/game/src/actors/kelderkind.gd
# Purpose: Kelderkind (Cellar Child). Small, pale, eyeless, all fours, long
# fingers. Design: the ambusher. Fast (2.7 m/s, faster than you walk), low to
# the ground (aim DOWN, or let auto-aim do it), 0.5 s crouch-and-leap tell, then
# it runs away and circles back: hit-and-run instead of a slow grind.
# Silhouette: a horizontal white shape skittering where nothing should move.
# Audio: dry skittering, a high screech on alert. Counterplay: track it,
# shoot during the crouch, or dodge the leap and punish the landing.
class_name Kelderkind
extends Enemy

var root: Node3D
var _limbs: Array[Node3D] = []
var _head: Node3D
var _phase := 0.0
var _t := 0.0
var _fall := 0.0
var _skitter_t := 0.0


func _init() -> void:
	kind = "kelderkind"


func _collision_size() -> Vector2:
	return Vector2(0.26, 0.6)


func _hidden_offset() -> float:
	return -1.0


func _body_node() -> Node3D:
	return root


func aim_point() -> Vector3:
	return global_position + Vector3.UP * 0.38


func is_weak_hit(hit_pos: Vector3) -> bool:
	return _head.global_position.distance_to(hit_pos) < 0.16


var model: ActorVisual


func _build_body() -> void:
	if CreatureModel.available("kelderkind"):
		model = CharacterFactory.creature("kelderkind", "crawler")
		add_child(model.build())
		root = model
		_head = model.joint("neck")
		return
	root = Node3D.new()
	add_child(root)
	var skin := Color(0.78, 0.8, 0.8)
	var torso := _capsule(0.1, 0.72, skin)
	torso.rotation.x = PI / 2
	torso.position = Vector3(0, 0.3, 0.05)
	var spine := _capsule(0.04, 0.5, Color(0.7, 0.72, 0.72))  # ridge of vertebrae
	spine.rotation.x = PI / 2
	spine.position = Vector3(0, 0.39, 0.08)
	root.add_child(spine)
	root.add_child(torso)
	_head = Node3D.new()
	_head.position = Vector3(0, 0.34, -0.44)
	root.add_child(_head)
	var skull := _sphere(0.1, skin)
	skull.scale = Vector3(1, 0.9, 1.15)
	_head.add_child(skull)
	var mouth := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.12, 0.035, 0.03)
	bm.material = StandardMaterial3D.new()
	bm.material.albedo_color = Color(0.03, 0.0, 0.0)
	mouth.mesh = bm
	mouth.position = Vector3(0, -0.035, -0.105)
	_head.add_child(mouth)  # no eyes: that is the point
	for i in 4:
		var front := i < 2
		var side := -1 if i % 2 == 0 else 1
		var hip := Node3D.new()
		hip.position = Vector3(0.09 * side, 0.32, -0.22 if front else 0.3)
		hip.rotation.z = 1.05 * side  # splay outward, like a spider
		root.add_child(hip)
		var upper := _capsule(0.025, 0.34, skin)
		upper.position.y = -0.15
		hip.add_child(upper)
		var knee := Node3D.new()
		knee.position.y = -0.3
		knee.rotation.z = -1.7 * side  # bend back down to the floor
		hip.add_child(knee)
		var lower := _capsule(0.02, 0.38, skin)
		lower.position.y = -0.17
		knee.add_child(lower)
		if front:  # long fingers splayed at the end of the arms
			for f in 3:
				var finger := _capsule(0.007, 0.17, skin)
				finger.position = Vector3((f - 1) * 0.03, -0.36, -0.07)
				finger.rotation.x = -1.3
				knee.add_child(finger)
		_limbs.append(hip)
	var shadow := MeshKit.blob_shadow()
	shadow.scale = Vector3(0.9, 0.9, 1.3)
	add_child(shadow)


func _capsule(r: float, h: float, c: Color) -> MeshInstance3D:
	return MeshKit.capsule(r, h, c)


func _sphere(r: float, c: Color) -> MeshInstance3D:
	return MeshKit.sphere(r, c)


func _lunge_speed() -> float:
	return 5.0 if brain.time_in_state < brain.windup_time + 0.22 else 0.0


func _say_alert() -> void:
	say("crawler_screech")


func _say_windup() -> void:
	say("crawler_screech")


func _pose(delta: float) -> void:
	if model:
		var st := brain.state
		model.pose = {EnemyBrain.State.ATTACK: "strike" if brain.time_in_state >= brain.windup_time else "windup",
			EnemyBrain.State.STAGGER: "stagger", EnemyBrain.State.DEAD: "dead", EnemyBrain.State.FLOORED: "floored"}.get(st, "idle")
		model.speed = Vector2(velocity.x, velocity.z).length()
		model.animate(delta)
		if model.speed > 0.5 and not brain.is_dead():
			_skitter_t -= delta
			if _skitter_t <= 0.0:
				_skitter_t = 0.35
				say("crawler_skitter")
		return
	_t += delta
	var speed := Vector2(velocity.x, velocity.z).length()
	_phase += delta * (4.0 + speed * 5.0)
	var k := MovementMath.smoothing_alpha(16.0, delta)
	var rear := 0.0
	var crouch := 0.0
	match brain.state:
		EnemyBrain.State.ATTACK:
			if brain.time_in_state < brain.windup_time:
				crouch = 0.12
				rear = -0.25
			else:
				rear = 0.35
		EnemyBrain.State.STAGGER:
			rear = -0.5
	if brain.state in [EnemyBrain.State.DEAD, EnemyBrain.State.FLOORED]:
		_fall = minf(1.0, _fall + delta * 3.0)
	else:
		_fall = maxf(0.0, _fall - delta * 2.0)
	for i in 4:
		var swing := sin(_phase + (PI if i in [1, 2] else 0.0)) * (0.6 if speed > 0.2 else 0.08)
		_limbs[i].rotation.x = lerpf(_limbs[i].rotation.x, swing + (0.5 if i < 2 else -0.3), k)
	root.rotation.x = lerpf(root.rotation.x, rear, k)
	root.position.y = lerpf(root.position.y, -crouch, k) if not _submerged else root.position.y
	root.rotation.z = _fall * PI * 0.9  # flips onto its back
	_head.rotation.z = sin(_t * 23.0) * 0.12 if brain.state == EnemyBrain.State.IDLE else sin(_t * 9.0) * 0.05
	if speed > 0.5 and not brain.is_dead():
		_skitter_t -= delta
		if _skitter_t <= 0.0:
			_skitter_t = 0.35
			say("crawler_skitter")
