# damned_waters/game/src/actors/mannequin.gd
# Purpose: a primitive-built humanoid with procedural animation. It is the
# stand-in until you model and rig real characters in Blender (bible Tier 3).
# Poses are *targets*; each frame every joint eases toward its target, so pose
# changes blend smoothly (like a crossfade between two takes, not a hard cut).
class_name Mannequin
extends ActorVisual

var palette := {"skin": Color(0.72, 0.58, 0.48), "top": Color(0.08, 0.1, 0.16),
	"legs": Color(0.1, 0.12, 0.2), "hair": Color(0.08, 0.05, 0.03), "shoes": Color(0.03, 0.03, 0.03)}
var bulk := 1.0          # torso girth (the Drowned are bloated)
var wet := false         # glossy skin
var with_gun := false


var torso: Node3D
var hips: Array[Node3D] = []
var shoulders: Array[Node3D] = []
var _phase := 0.0
var _t := 0.0
var _fall := 0.0
var _gun: MeshInstance3D


func build() -> ActorVisual:
	add_child(_blob_shadow())
	var pelvis := Node3D.new()
	pelvis.position.y = 0.92
	add_child(pelvis)
	torso = Node3D.new()
	pelvis.add_child(torso)
	var chest := _capsule(0.17 * bulk, 0.64, palette.top)
	chest.position.y = 0.3
	chest.scale = Vector3(1.15, 1.0, 0.72 * bulk)
	torso.add_child(chest)
	head = Node3D.new()
	head.position.y = 0.74
	torso.add_child(head)
	head.add_child(_sphere(0.105, palette.skin))
	var hair := _sphere(0.112, palette.hair)
	hair.position = Vector3(0, 0.03, 0.025)
	hair.scale = Vector3(1, 0.85, 1)
	head.add_child(hair)
	for side in [-1, 1]:
		var sh := Node3D.new()
		sh.position = Vector3(0.22 * side * bulk, 0.55, 0)
		torso.add_child(sh)
		var arm := _capsule(0.05, 0.62, palette.top)
		arm.position.y = -0.3
		sh.add_child(arm)
		var hand := _sphere(0.045, palette.skin)
		hand.position.y = -0.62
		sh.add_child(hand)
		shoulders.append(sh)
		var hip := Node3D.new()
		hip.position = Vector3(0.1 * side, 0, 0)
		pelvis.add_child(hip)
		var leg := _capsule(0.075, 0.9, palette.legs)
		leg.position.y = -0.45
		hip.add_child(leg)
		var shoe := _box(Vector3(0.1, 0.07, 0.22), palette.shoes)
		shoe.position = Vector3(0, -0.88, -0.04)
		hip.add_child(shoe)
		hips.append(hip)
	if with_gun:
		set_weapon("pistol")
	return self


func animate(delta: float) -> void:
	_t += delta
	var tgt := {"lean": 0.0, "head_tilt": 0.0, "arm_l": 0.0, "arm_r": 0.0, "arm_out": 0.06, "legs": 0.0, "bob": 0.0}
	match pose:
		"walk", "run":
			var stride := 1.25 if pose == "walk" else 1.9
			_phase += delta * speed / stride * TAU
			var amp := 0.45 if pose == "walk" else 0.75
			tgt.legs = sin(_phase) * amp
			tgt.arm_l = sin(_phase) * amp * 0.6
			tgt.arm_r = -sin(_phase) * amp * 0.6
			tgt.bob = absf(sin(_phase)) * (0.025 if pose == "walk" else 0.05)
			tgt.lean = 0.05 if pose == "walk" else 0.15
		"aim":
			tgt.arm_l = PI / 2 + aim_pitch
			tgt.arm_r = PI / 2 + aim_pitch
			tgt.arm_out = -0.18
		"reload":
			tgt.arm_l = 0.9
			tgt.arm_r = 1.1
			tgt.arm_out = -0.3
			tgt.head_tilt = 0.25
		"shamble":
			_phase += delta * maxf(speed, 0.3) / 1.1 * TAU
			tgt.legs = sin(_phase) * 0.3
			tgt.arm_l = 1.15 + sin(_t * 1.7) * 0.12
			tgt.arm_r = 1.05 + sin(_t * 1.3 + 1.0) * 0.12
			tgt.lean = 0.18 + sin(_phase) * 0.05
			tgt.head_tilt = 0.35
		"windup":
			tgt.arm_l = 2.6
			tgt.arm_r = 2.5
			tgt.lean = -0.22
			tgt.head_tilt = -0.2
		"strike":
			tgt.arm_l = 0.9
			tgt.arm_r = 0.8
			tgt.lean = 0.45
		"stagger", "hurt":
			tgt.lean = -0.35
			tgt.arm_l = 0.4
			tgt.arm_r = 0.5
			tgt.head_tilt = -0.3
		"dodge":
			tgt.lean = 0.35
			tgt.arm_l = 0.6
			tgt.arm_r = 0.6
			tgt.bob = -0.18
		"kick":
			tgt.lean = -0.25
			tgt.legs = -1.3  # right leg drives forward
			tgt.arm_l = 0.5
			tgt.arm_r = -0.3
		_:
			tgt.bob = sin(_t * 1.6) * 0.006
			tgt.head_tilt = 0.25 if bulk > 1.0 else 0.0
	var k := MovementMath.smoothing_alpha(14.0 if pose in ["strike", "windup", "stagger", "hurt"] else 9.0, delta)
	torso.rotation.x = lerpf(torso.rotation.x, -tgt.lean, k)
	head.rotation.z = lerpf(head.rotation.z, tgt.head_tilt * (0.6 if bulk > 1.0 else 0.0), k)
	head.rotation.x = lerpf(head.rotation.x, -tgt.head_tilt * 0.4, k)
	shoulders[0].rotation.x = lerpf(shoulders[0].rotation.x, tgt.arm_l, k)
	shoulders[1].rotation.x = lerpf(shoulders[1].rotation.x, tgt.arm_r, k)
	shoulders[0].rotation.z = lerpf(shoulders[0].rotation.z, -tgt.arm_out, k)
	shoulders[1].rotation.z = lerpf(shoulders[1].rotation.z, tgt.arm_out, k)
	hips[0].rotation.x = lerpf(hips[0].rotation.x, tgt.legs, k)
	hips[1].rotation.x = lerpf(hips[1].rotation.x, -tgt.legs, k)
	torso.get_parent().position.y = 0.92 + tgt.bob
	# Falling backwards (dead or floored) and getting back up: rotate about the feet.
	if pose in ["dead", "floored"]:
		_fall = minf(1.0, _fall + delta * 2.2)
	else:
		_fall = maxf(0.0, _fall - delta * 1.4)
	rotation.x = ease(_fall, 2.2) * PI / 2
	$BlobShadow.visible = _fall < 0.4


func _capsule(r: float, h: float, c: Color) -> MeshInstance3D:
	return MeshKit.capsule(r, h, c, wet)


func _sphere(r: float, c: Color) -> MeshInstance3D:
	return MeshKit.sphere(r, c, wet)


func _box(s: Vector3, c: Color) -> MeshInstance3D:
	return MeshKit.box(s, c, wet)


func _blob_shadow() -> MeshInstance3D:
	return MeshKit.blob_shadow()


## Swap the prop in the right hand: short pistol or long double-barrel.
func set_weapon(weapon_id: String) -> void:
	if _gun:
		_gun.queue_free()
	var long := weapon_id == "shotgun"
	_gun = _box(Vector3(0.045, 0.78 if long else 0.19, 0.06), Color(0.04, 0.04, 0.045) if not long else Color(0.12, 0.07, 0.03))
	_gun.position = Vector3(0, -0.9 if long else -0.72, -0.02)
	shoulders[1].add_child(_gun)
