# damned_waters/game/src/actors/creature_model.gd
# Purpose: a jointed creature from tools/blender/enemies_v2.py (glTF) driven by
# procedural animation, one gait per species. Joints are plain nodes (shoulder_l,
# knee_r, wheel_front...), so animation is just rotations toward pose targets,
# eased every frame, like the placeholder but on real models.
# Axis conventions (joints are unrotated at rest; limbs hang down):
#   +x rotation swings a limb forward; knees bend with -x; elbows with +x.
class_name CreatureModel
extends ActorVisual

const DIR := "res://assets/characters/enemies/%s.glb"

var model_id := ""
var species := "humanoid"   # humanoid | crawler | boss | stalker | bike
var joints := {}
var _t := 0.0
var _phase := 0.0
var _fall := 0.0
var _shadow: MeshInstance3D


static func available(id: String) -> bool:
	return ResourceLoader.exists(DIR % id)


func setup(id: String, kind: String) -> CreatureModel:
	model_id = id
	species = kind
	return self


func build() -> ActorVisual:
	var inst: Node3D = load(DIR % model_id).instantiate()
	add_child(inst)
	for n in inst.find_children("*", "Node3D", true, false):
		joints[String(n.name)] = n
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var m3 := mi as MeshInstance3D
		for s in m3.mesh.get_surface_count():
			var src := m3.mesh.surface_get_material(s)
			m3.set_surface_override_material(s, MaterialLib.get_material(src.resource_name if src else ""))
	head = joints.get("neck")
	_shadow = MeshKit.blob_shadow({"boss": 2.2, "crawler": 1.1, "bike": 1.6}.get(species, 0.75))
	add_child(_shadow)
	return self


func joint(n: String) -> Node3D:  # overrides ActorVisual.joint
	return joints.get(n)


func _ease_joint(j: String, rot: Vector3, k: float) -> void:
	var n: Node3D = joints.get(j)
	if n:
		n.rotation = n.rotation.lerp(rot, k)


func animate(delta: float) -> void:
	_t += delta
	var k := MovementMath.smoothing_alpha(16.0 if pose in ["strike", "windup", "stagger", "hurt", "kick", "dodge"] else 9.0, delta)
	match species:
		"humanoid":
			_humanoid(delta, k)
		"crawler":
			_crawler(delta, k)
		"stalker":
			_stalker(k)
		"bike":
			_bike(delta, k)
	var down := pose in ["dead", "floored"]
	_fall = minf(1.0, _fall + delta * 2.2) if down else maxf(0.0, _fall - delta * 1.4)
	if species == "crawler":
		rotation.z = ease(_fall, 2.0) * PI * 0.9  # flips onto its back
	elif species != "boss":
		rotation.x = ease(_fall, 2.2) * PI / 2    # topples backwards about the feet
	_shadow.visible = _fall < 0.4


func _humanoid(delta: float, k: float) -> void:
	var z := Vector3.ZERO
	var T := {"spine": z, "neck": z, "shoulder_l": Vector3(0, 0, -0.08), "shoulder_r": Vector3(0, 0, 0.08),
		"elbow_l": Vector3(0.15, 0, 0), "elbow_r": Vector3(0.15, 0, 0), "hip_l": z, "hip_r": z,
		"knee_l": Vector3(-0.05, 0, 0), "knee_r": Vector3(-0.05, 0, 0), "pelvis": z}
	var bob := 0.0
	match pose:
		"walk", "run", "shamble":
			var run := pose == "run"
			var stride := 1.9 if run else (0.9 if pose == "shamble" else 1.3)
			_phase += delta * maxf(speed, 0.4) / stride * TAU
			var s := sin(_phase)
			var amp := 0.7 if run else (0.3 if pose == "shamble" else 0.45)
			T.hip_l = Vector3(s * amp, 0, 0)
			T.hip_r = Vector3(-s * amp, 0, 0)
			T.knee_l = Vector3(-0.1 - maxf(0.0, -s) * (1.1 if run else 0.7), 0, 0)
			T.knee_r = Vector3(-0.1 - maxf(0.0, s) * (1.1 if run else 0.7), 0, 0)
			bob = -absf(s) * (0.05 if run else 0.025)
			if pose == "shamble":  # arms out, head lolling, a dragging lurch
				T.shoulder_l = Vector3(1.25 + sin(_t * 1.7) * 0.12, 0, 0.12)
				T.shoulder_r = Vector3(1.1 + sin(_t * 1.3 + 1.0) * 0.12, 0, -0.1)
				T.elbow_l = Vector3(0.25, 0, 0)
				T.elbow_r = Vector3(0.35, 0, 0)
				T.spine = Vector3(0.18 + s * 0.04, 0, s * 0.08)
				T.neck = Vector3(0.25, 0, 0.35 + sin(_t * 0.9) * 0.1)
			else:
				T.shoulder_l = Vector3(-s * amp * 0.6, 0, -0.08)
				T.shoulder_r = Vector3(s * amp * 0.6, 0, 0.08)
				T.elbow_l = Vector3(1.1 if run else 0.3, 0, 0)
				T.elbow_r = Vector3(1.1 if run else 0.3, 0, 0)
				T.spine = Vector3(0.2 if run else 0.05, 0, 0)
		"aim":
			T.shoulder_r = Vector3(PI / 2 + aim_pitch, 0, 0.05)
			T.shoulder_l = Vector3(PI / 2 + aim_pitch, 0, 0.42)
			T.elbow_l = Vector3(0.15, 0, 0)
			T.elbow_r = Vector3(0.0, 0, 0)
			T.spine = Vector3(0.06, 0, 0)
			T.hip_l = Vector3(0.18, 0, 0)
			T.hip_r = Vector3(-0.18, 0, 0)
			T.knee_l = Vector3(-0.15, 0, 0)
			T.knee_r = Vector3(-0.2, 0, 0)
		"reload":
			T.shoulder_r = Vector3(0.9, 0, 0.1)
			T.shoulder_l = Vector3(0.8, 0, 0.35)
			T.elbow_r = Vector3(1.2, 0, 0)
			T.elbow_l = Vector3(1.3, 0, 0)
			T.neck = Vector3(0.35, 0, 0)
		"windup":  # the readable tell: both arms high
			T.shoulder_l = Vector3(2.6, 0, 0.15)
			T.shoulder_r = Vector3(2.5, 0, -0.15)
			T.spine = Vector3(-0.22, 0, 0)
			T.neck = Vector3(-0.3, 0, 0.2)
		"strike":
			T.shoulder_l = Vector3(1.0, 0, 0.1)
			T.shoulder_r = Vector3(0.9, 0, -0.1)
			T.spine = Vector3(0.45, 0, 0)
		"stagger", "hurt":
			T.spine = Vector3(-0.35, 0, 0.1)
			T.neck = Vector3(-0.35, 0, 0)
			T.shoulder_l = Vector3(0.5, 0, -0.3)
			T.shoulder_r = Vector3(0.4, 0, 0.3)
		"dodge":
			T.spine = Vector3(0.4, 0, 0)
			T.hip_l = Vector3(0.7, 0, 0)
			T.hip_r = Vector3(0.3, 0, 0)
			T.knee_l = Vector3(-1.2, 0, 0)
			T.knee_r = Vector3(-1.0, 0, 0)
			bob = -0.22
		"kick":
			T.hip_r = Vector3(1.35, 0, 0)
			T.knee_r = Vector3(-0.2, 0, 0)
			T.spine = Vector3(-0.25, 0, 0)
			T.shoulder_l = Vector3(0.5, 0, -0.4)
			T.shoulder_r = Vector3(-0.3, 0, 0.3)
		_:
			T.spine = Vector3(sin(_t * 1.6) * 0.015, 0, 0)
			if model_id.begins_with("verdronkene"):
				T.neck = Vector3(0.35, 0, 0.3)
				T.shoulder_l = Vector3(0.2, 0, -0.05)
	for j in T:
		_ease_joint(j, T[j], k)
	var pel: Node3D = joints.get("pelvis")
	if pel:
		pel.position.y = lerpf(pel.position.y, 0.96 + bob, k)


func _crawler(delta: float, k: float) -> void:
	var body: Node3D = joints.get("body")
	var moving := speed > 0.2
	_phase += delta * (3.0 + speed * 4.5)
	var s := sin(_phase)
	var rear := 0.0
	match pose:
		"windup":
			rear = -0.35
		"strike":
			rear = 0.25
		"stagger":
			rear = -0.5
	var amp := 0.45 if moving else 0.05
	# Diagonal pairs move together, like an animal: left arm with right leg.
	_ease_joint("shoulder_l", Vector3(0, s * amp, s * 0.15 * amp), k)
	_ease_joint("hip_r", Vector3(0, s * amp, -s * 0.15 * amp), k)
	_ease_joint("shoulder_r", Vector3(0, -s * amp, -s * 0.15 * amp), k)
	_ease_joint("hip_l", Vector3(0, -s * amp, s * 0.15 * amp), k)
	_ease_joint("neck", Vector3(sin(_t * 23.0) * 0.08 if not moving else 0.0, 0, sin(_t * 9.0) * 0.12), k)
	if body:
		body.rotation = body.rotation.lerp(Vector3(rear, 0, s * 0.06 * amp), k)
		body.position.y = lerpf(body.position.y, 0.56 + absf(s) * 0.03 * amp, k)


func _stalker(k: float) -> void:
	# It glides: the coat sways, the head tilts as if listening, the cane taps.
	_ease_joint("spine", Vector3(0.05 + sin(_t * 0.8) * 0.03, 0, sin(_t * 0.6) * 0.03), k)
	_ease_joint("neck", Vector3(0.1, sin(_t * 0.35) * 0.4, 0.3 * sin(_t * 0.23)), k)
	_ease_joint("shoulder_r", Vector3(0.1 + maxf(0.0, sin(_t * 2.4)) * 0.12, 0, 0), k)
	_ease_joint("shoulder_l", Vector3(0.25, 0, -0.1), k)


func _bike(delta: float, k: float) -> void:
	var spin := maxf(speed, 1.2) / 0.36
	for w in ["wheel_front", "wheel_rear"]:
		var n: Node3D = joints.get(w)
		if n:
			n.rotate_x(-spin * delta)
	var crank: Node3D = joints.get("crank")
	if crank:
		crank.rotate_x(-spin * 0.35 * delta)
	_ease_joint("rider", Vector3(sin(_t * 3.0) * 0.05, 0, sin(_t * 1.5) * 0.06), k)
	_ease_joint("neck", Vector3(-0.5 + sin(_t * 7.0) * 0.08, 0, sin(_t * 11.0) * 0.1), k)
