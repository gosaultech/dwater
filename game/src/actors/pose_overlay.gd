# damned_waters/game/src/actors/pose_overlay.gd
# Purpose: procedural bone overrides layered on top of whatever clip is
# playing. Used for aiming: both arms swing to point along the aim direction,
# with the support hand converging on the gun. Direction is measured bone ->
# child bone, so it works regardless of a rig's bone-axis convention.
class_name PoseOverlay
extends SkeletonModifier3D

var arm_chains := {}          # "right"/"left" -> [upper, fore, hand] bone names
var aim_weight := 0.0
var aim_dir_world := Vector3.FORWARD
var right_world := Vector3.RIGHT
var converge := true  # true: support hand meets the gun; false: arms reach in parallel
var _ids := {}


func _resolve() -> void:
	var sk := get_skeleton()
	for side in arm_chains:
		_ids[side] = arm_chains[side].map(func(n): return sk.find_bone(n))


func _process_modification_with_delta(_delta: float) -> void:
	_apply()


func _process_modification() -> void:
	_apply()


func _apply() -> void:
	var sk := get_skeleton()
	if sk == null or aim_weight <= 0.001:
		return
	if _ids.is_empty():
		_resolve()
	var to_sk := sk.global_transform.basis.inverse()
	for side in _ids:
		var off := (0.32 if side == "left" else -0.06) if converge else (-0.12 if side == "left" else 0.12)
		var target := aim_dir_world + right_world * off
		var dir_sk := (to_sk * target).normalized()
		var chain: Array = _ids[side]
		for i in chain.size() - 1:
			var b: int = chain[i]
			var child: int = chain[i + 1]
			if b < 0 or child < 0:
				continue
			var gp := sk.get_bone_global_pose(b)
			var cur := (sk.get_bone_global_pose(child).origin - gp.origin).normalized()
			if cur.length_squared() < 1e-6:
				continue
			var q := Quaternion.IDENTITY.slerp(Quaternion(cur, dir_sk), aim_weight)
			var new_basis := Basis(q) * gp.basis
			var parent := sk.get_bone_parent(b)
			var pb := sk.get_bone_global_pose(parent).basis if parent >= 0 else Basis.IDENTITY
			sk.set_bone_pose_rotation(b, (pb.inverse() * new_basis).get_rotation_quaternion())
