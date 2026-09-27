# damned_waters/game/src/actors/skeletal_creature.gd
# Purpose: skinned characters (tools/blender/skinned.py) animated procedurally
# by rotating BONES. One continuous mesh bends smoothly at every joint.
# Rotations are given in CHARACTER axes, not bone axes, so the same numbers
# mean the same motion on every bone regardless of how the rig was exported:
#   x = pitch about the character's right axis
#       bones pointing DOWN (limbs): +x swings forward   (knee flexion = -x)
#       bones pointing UP (spine, neck): +x leans BACK   (forward lean = -x)
#       feet (pointing forward): +x lifts the toes
#   y = yaw about up: +y turns toward the character's left
#   z = roll about back: DOWN bones' tips move toward the character's right
class_name SkeletalCreature
extends ActorVisual

const DIR := "res://assets/characters/enemies/%s.glb"

var model_id := ""
var species := "humanoid"   # humanoid | crawler
var skel: Skeleton3D
var _idx := {}
var _rest := {}             # bone -> local rest rotation (Quaternion)
var _gc := {}               # bone -> global rest basis in character space
var _to_skel := Basis.IDENTITY
var _pelvis_rest := Vector3.ZERO
var _attach := {}
var _t := 0.0
var _phase := 0.0
var _fall := 0.0
var _shadow: MeshInstance3D


func setup(id: String, kind: String) -> SkeletalCreature:
	model_id = id
	species = kind
	return self


func build() -> ActorVisual:
	var inst: Node3D = load(DIR % model_id).instantiate()
	add_child(inst)
	skel = inst.find_children("*", "Skeleton3D", true, false)[0]
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var m3 := mi as MeshInstance3D
		for s in m3.mesh.get_surface_count():
			var src := m3.mesh.surface_get_material(s)
			m3.set_surface_override_material(s, MaterialLib.get_material(src.resource_name if src else ""))
	var to_char := _relative(inst, skel).basis  # skeleton space -> character space
	_to_skel = to_char.inverse()
	for i in skel.get_bone_count():
		var n := skel.get_bone_name(i)
		_idx[n] = i
		_rest[n] = skel.get_bone_rest(i).basis.get_rotation_quaternion()
		_gc[n] = (to_char * skel.get_bone_global_rest(i).basis).orthonormalized()
	if _idx.has("pelvis"):
		_pelvis_rest = skel.get_bone_rest(_idx.pelvis).origin
	head = joint("head")
	_shadow = MeshKit.blob_shadow(1.1 if species == "crawler" else 0.75)
	add_child(_shadow)
	return self


func joint(n: String) -> Node3D:
	var bone: String = {"neck": "head"}.get(n, n)
	if not _idx.has(bone):
		return null
	if not _attach.has(bone):
		var ba := BoneAttachment3D.new()
		ba.bone_name = bone
		skel.add_child(ba)
		_attach[bone] = ba
	return _attach[bone]


## Ease `bone` toward a rotation given in character axes (see header).
func _pose_bone(bone: String, e: Vector3, k: float) -> void:
	if not _idx.has(bone):
		return
	var rc := Basis(Vector3.UP, e.y) * Basis(Vector3.RIGHT, e.x) * Basis(Vector3.BACK, e.z)
	var g: Basis = _gc[bone]
	var target: Quaternion = _rest[bone] * (g.inverse() * rc * g).get_rotation_quaternion()
	var i: int = _idx[bone]
	skel.set_bone_pose_rotation(i, skel.get_bone_pose_rotation(i).slerp(target, k))


func animate(delta: float) -> void:
	_t += delta
	var k := MovementMath.smoothing_alpha(16.0 if pose in ["strike", "windup", "stagger", "hurt", "kick", "dodge"] else 9.0, delta)
	if species == "crawler":
		_crawler(delta, k)
	else:
		_humanoid(delta, k)
	var down := pose in ["dead", "floored"]
	_fall = minf(1.0, _fall + delta * 2.2) if down else maxf(0.0, _fall - delta * 1.4)
	if species == "crawler":
		rotation.z = ease(_fall, 2.0) * PI * 0.9
	else:
		rotation.x = ease(_fall, 2.2) * PI / 2
	_shadow.visible = _fall < 0.4


func _humanoid(delta: float, k: float) -> void:
	var drowned := model_id.begins_with("verdronkene")
	var P := {}
	# Relaxed stance: arms hang in from the A-pose, elbows and knees soft.
	for s in ["l", "r"]:
		var sg := -1.0 if s == "l" else 1.0
		P["upper_arm_" + s] = Vector3(0.05, 0, -0.14 * sg)
		P["forearm_" + s] = Vector3(0.2, 0, 0)
		P["thigh_" + s] = Vector3(0.03, 0, 0.02 * sg)
		P["shin_" + s] = Vector3(-0.07, 0, 0)
	P["spine"] = Vector3(-0.02 + sin(_t * 1.6) * 0.012, 0, 0)
	P["chest"] = Vector3(sin(_t * 1.6 + 0.5) * 0.01, 0, 0)
	P["neck"] = Vector3(-0.05, 0, 0)
	P["head"] = Vector3(0.0, 0, 0)
	P["pelvis"] = Vector3(0, 0, sin(_t * 0.5) * 0.02)
	var bob := 0.0
	if drowned:  # the Drowned stand wrong even at rest: slumped, head lolled
		P["spine"] = Vector3(-0.18, 0, 0.08)
		P["neck"] = Vector3(-0.25, 0, 0)
		P["head"] = Vector3(-0.15, 0.1, 0.35 + sin(_t * 0.7) * 0.08)
		P["upper_arm_r"] = Vector3(0.25, 0, -0.05)
	match pose:
		"walk", "run":
			var run := pose == "run"
			_phase += delta * maxf(speed, 0.4) / (1.9 if run else 1.3) * TAU
			var s := sin(_phase)
			var c := cos(_phase)
			var amp := 0.62 if run else 0.42
			P["thigh_l"] = Vector3(s * amp, 0, -0.02)
			P["thigh_r"] = Vector3(-s * amp, 0, 0.02)
			P["shin_l"] = Vector3(-0.1 - maxf(0.0, c) * (1.3 if run else 0.8), 0, 0)   # flex on the swing-through
			P["shin_r"] = Vector3(-0.1 - maxf(0.0, -c) * (1.3 if run else 0.8), 0, 0)
			P["upper_arm_l"] = Vector3(-s * amp * 0.7, 0, 0.12)
			P["upper_arm_r"] = Vector3(s * amp * 0.7, 0, -0.12)
			P["forearm_l"] = Vector3((1.3 if run else 0.3) + maxf(0.0, -s) * 0.3, 0, 0)
			P["forearm_r"] = Vector3((1.3 if run else 0.3) + maxf(0.0, s) * 0.3, 0, 0)
			P["spine"] = Vector3(-0.22 if run else -0.05, s * 0.1, 0)             # torso counter-rotates
			P["chest"] = Vector3(0, -s * 0.06, 0)
			P["pelvis"] = Vector3(0, -s * 0.08, 0)
			bob = -absf(s) * (0.045 if run else 0.022)
		"shamble":  # one leg drags, one arm reaches, the other swings dead
			_phase += delta * maxf(speed, 0.3) / 0.95 * TAU
			var s := sin(_phase)
			P["thigh_l"] = Vector3(s * 0.22, 0, -0.03)
			P["shin_l"] = Vector3(-0.08, 0, 0)                                      # stiff, dragged
			P["thigh_r"] = Vector3(-s * 0.36, 0, 0.03)
			P["shin_r"] = Vector3(-0.12 - maxf(0.0, -cos(_phase)) * 0.7, 0, 0)
			P["upper_arm_r"] = Vector3(1.3 + sin(_t * 1.3) * 0.1, 0, -0.08)         # reaching
			P["forearm_r"] = Vector3(0.15, 0, 0)
			P["upper_arm_l"] = Vector3(0.3 + s * 0.25, 0, -0.1)                     # limp
			P["forearm_l"] = Vector3(0.1, 0, 0)
			P["spine"] = Vector3(-0.28 + s * 0.06, s * 0.12, 0.1)                    # hunched lurch
			P["chest"] = Vector3(-0.08, -s * 0.08, 0)
			bob = -absf(s) * 0.03
		"aim":  # two-handed pistol: strong arm straight, support arm crossing in
			P["upper_arm_r"] = Vector3(PI / 2 + aim_pitch, 0, -0.14)
			P["forearm_r"] = Vector3(0.02, 0, 0)
			P["upper_arm_l"] = Vector3(PI / 2 + aim_pitch - 0.12, 0, 0.62)
			P["forearm_l"] = Vector3(0.35, 0, 0)
			P["spine"] = Vector3(-0.06, 0.08, 0)
			P["chest"] = Vector3(-0.03, 0.08, 0)
			P["neck"] = Vector3(-0.1, -0.1, 0)
			P["thigh_l"] = Vector3(0.22, 0, -0.04)
			P["shin_l"] = Vector3(-0.2, 0, 0)
			P["thigh_r"] = Vector3(-0.2, 0, 0.06)
			P["shin_r"] = Vector3(-0.1, 0, 0)
			bob = -0.02
		"reload":
			P["upper_arm_r"] = Vector3(0.95, 0, -0.25)
			P["forearm_r"] = Vector3(1.25, 0, 0)
			P["upper_arm_l"] = Vector3(0.85, 0, 0.45)
			P["forearm_l"] = Vector3(1.35, 0, 0)
			P["neck"] = Vector3(-0.35, 0, 0)
		"windup":  # the readable tell: arms thrown up and back, spine arched
			for s2 in ["l", "r"]:
				var sg := -1.0 if s2 == "l" else 1.0
				P["upper_arm_" + s2] = Vector3(2.55, 0, 0.25 * sg)
				P["forearm_" + s2] = Vector3(0.35, 0, 0)
			P["spine"] = Vector3(0.22, 0, 0)
			P["chest"] = Vector3(0.12, 0, 0)
			P["neck"] = Vector3(0.2, 0, 0)
			P["head"] = Vector3(0.25, 0, 0.1)
			P["thigh_l"] = Vector3(0.25, 0, 0)
			P["shin_l"] = Vector3(-0.35, 0, 0)
			P["thigh_r"] = Vector3(-0.2, 0, 0)
		"strike":  # lunge: arms slam down, whole body follows
			for s2 in ["l", "r"]:
				P["upper_arm_" + s2] = Vector3(1.1, 0, 0)
				P["forearm_" + s2] = Vector3(0.1, 0, 0)
			P["spine"] = Vector3(-0.45, 0, 0)
			P["chest"] = Vector3(-0.15, 0, 0)
			P["thigh_l"] = Vector3(0.55, 0, 0)
			P["shin_l"] = Vector3(-0.45, 0, 0)
			P["thigh_r"] = Vector3(-0.35, 0, 0)
			bob = -0.06
		"stagger", "hurt":
			P["spine"] = Vector3(0.32, 0, 0.1)
			P["chest"] = Vector3(0.15, 0, 0)
			P["neck"] = Vector3(0.3, 0, 0)
			P["head"] = Vector3(0.2, 0, 0.15)
			P["upper_arm_l"] = Vector3(0.5, 0, -0.4)
			P["upper_arm_r"] = Vector3(0.4, 0, 0.4)
			P["thigh_r"] = Vector3(-0.3, 0, 0)
			P["shin_r"] = Vector3(-0.25, 0, 0)
		"dodge":
			P["spine"] = Vector3(-0.4, 0, 0)
			P["thigh_l"] = Vector3(0.95, 0, 0)
			P["shin_l"] = Vector3(-1.5, 0, 0)
			P["thigh_r"] = Vector3(0.4, 0, 0)
			P["shin_r"] = Vector3(-1.1, 0, 0)
			P["upper_arm_l"] = Vector3(0.6, 0, -0.2)
			P["upper_arm_r"] = Vector3(0.6, 0, 0.2)
			bob = -0.24
		"kick":
			P["thigh_r"] = Vector3(1.45, 0, 0)
			P["shin_r"] = Vector3(-0.3, 0, 0)
			P["thigh_l"] = Vector3(-0.05, 0, 0)
			P["shin_l"] = Vector3(-0.2, 0, 0)
			P["spine"] = Vector3(0.28, 0, 0)
			P["upper_arm_l"] = Vector3(0.35, 0, -0.45)
			P["upper_arm_r"] = Vector3(-0.2, 0, 0.45)
	# Keep the soles flat: the foot cancels the leg's accumulated pitch.
	for s in ["l", "r"]:
		P["foot_" + s] = Vector3(-(P["thigh_" + s].x + P["shin_" + s].x) * 0.9, 0, 0)
	for b in P:
		_pose_bone(b, P[b], k)
	if _idx.has("pelvis"):
		var i: int = _idx.pelvis
		var want := _pelvis_rest + _to_skel * Vector3(0, bob, 0)
		skel.set_bone_pose_position(i, skel.get_bone_pose_position(i).lerp(want, k))


func _crawler(delta: float, k: float) -> void:
	var moving := speed > 0.2
	_phase += delta * (3.0 + speed * 4.5)
	var s := sin(_phase)
	var amp := 0.45 if moving else 0.04
	# The spine points forward, so +x lifts the FRONT: rear up for the leap tell.
	var rear: float = {"windup": 0.35, "strike": -0.25, "stagger": 0.45}.get(pose, 0.0)
	_pose_bone("spine", Vector3(rear, 0, s * 0.05 * amp), k)
	# Diagonal pairs move together (left arm with right leg), like a quadruped.
	_pose_bone("upper_arm_l", Vector3(0, s * amp, 0), k)
	_pose_bone("thigh_r", Vector3(0, s * amp, 0), k)
	_pose_bone("upper_arm_r", Vector3(0, -s * amp, 0), k)
	_pose_bone("thigh_l", Vector3(0, -s * amp, 0), k)
	_pose_bone("neck", Vector3(0, 0, sin(_t * (9.0 if moving else 23.0)) * (0.1 if moving else 0.06)), k)


static func _relative(root: Node, n: Node) -> Transform3D:
	var xf := Transform3D.IDENTITY
	var cur: Node = n
	while cur and cur != root:
		if cur is Node3D:
			xf = (cur as Node3D).transform * xf
		cur = cur.get_parent()
	return xf
