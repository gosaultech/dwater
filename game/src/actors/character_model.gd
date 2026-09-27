# damned_waters/game/src/actors/character_model.gd
# Purpose: a real rigged character (glTF) behind the ActorVisual contract.
# Configured by data/characters/<id>.json:
#   model        res:// path to the .glb (e.g. a MetaHuman/CC export)
#   height_m     uniform scale so the model's standing height matches
#   yaw_offset   glTF characters face +Z; gameplay faces -Z, so usually 180
#   clips        pose -> animation clip name (missing poses fall back)
#   clip_speed   authored m/s of walk/run clips (prevents foot sliding)
#   bones        head, right_hand, arm chains for the aim overlay
class_name CharacterModel
extends ActorVisual

const LOOPING := ["idle", "walk", "run", "shamble"]
const FALLBACK := {"shamble": "walk", "aim": "idle", "reload": "idle", "windup": "idle", "strike": "idle",
	"stagger": "idle", "hurt": "idle", "dodge": "run", "kick": "idle", "floored": "idle", "dead": "idle"}

var manifest := {}
var _anim: AnimationPlayer
var _skel: Skeleton3D
var _overlay: PoseOverlay
var _hand: BoneAttachment3D
var _gun: MeshInstance3D
var _current := ""
var _fall := 0.0
var _shadow: MeshInstance3D


func setup(m: Dictionary) -> CharacterModel:
	manifest = m
	return self


func build() -> ActorVisual:
	var holder := Node3D.new()
	holder.rotation.y = deg_to_rad(float(manifest.get("yaw_offset", 180.0)))
	add_child(holder)
	var inst: Node3D = load(manifest.model).instantiate()
	holder.add_child(inst)
	_skel = _find(inst, "Skeleton3D") as Skeleton3D
	_anim = _find(inst, "AnimationPlayer") as AnimationPlayer
	var facing := facing_yaw(inst)
	if facing != INF:  # heel->toe tells us which way the body faces, on any rig
		holder.rotation.y = -facing
	_merge_animation_sources(inst)
	if manifest.has("zombify"):
		zombify(inst, manifest.zombify)
	var box := _bounds(inst)
	if box.size.y > 0.01:
		holder.scale = Vector3.ONE * float(manifest.get("height_m", 1.78)) / box.size.y
		holder.position.y = -box.position.y * holder.scale.y
	var clips: Dictionary = manifest.get("clips", {})
	for p in LOOPING:
		if clips.has(p) and _anim and _anim.has_animation(clips[p]):
			_anim.get_animation(clips[p]).loop_mode = Animation.LOOP_LINEAR
	var bones: Dictionary = manifest.get("bones", {})
	if _skel:
		_overlay = PoseOverlay.new()
		var chains := {}
		for side in bones.get("arms", {}):
			chains[side] = bones.arms[side].map(func(n):
				var i := find_bone_flexible(_skel, n)
				return _skel.get_bone_name(i) if i >= 0 else n)
		_overlay.arm_chains = chains
		_skel.add_child(_overlay)
		head = _attach(bones.get("head", ""))
		_hand = _attach(bones.get("right_hand", ""))
	_shadow = MeshKit.blob_shadow()
	add_child(_shadow)
	return self


func _attach(bone: String) -> BoneAttachment3D:
	var ba := BoneAttachment3D.new()
	var i := find_bone_flexible(_skel, bone)
	ba.bone_name = _skel.get_bone_name(i) if i >= 0 else bone
	_skel.add_child(ba)
	return ba


func set_weapon(weapon_id: String) -> void:
	if _hand == null:
		return
	if _gun:
		_gun.queue_free()
	var long := weapon_id == "shotgun"
	var g: Dictionary = manifest.get("gun", {})
	_gun = MeshKit.box(Vector3(0.035, 0.8 if long else 0.19, 0.05), Color(0.04, 0.04, 0.045))
	_gun.top_level = false
	_hand.add_child(_gun)
	# Bone-space placement; tune per rig in the manifest ("gun": {"offset": [...], "rot_deg": [...]}).
	var off: Array = g.get("offset", [0.0, 0.1, 0.03])
	var rot: Array = g.get("rot_deg", [0.0, 0.0, 0.0])
	_gun.position = Vector3(off[0], off[1] + (0.25 if long else 0.0), off[2]) / _hand.global_transform.basis.get_scale().x \
		if _hand.is_inside_tree() else Vector3(off[0], off[1], off[2])
	_gun.rotation_degrees = Vector3(rot[0], rot[1], rot[2])


func _clip_for(p: String) -> String:
	var clips: Dictionary = manifest.get("clips", {})
	var key := p
	while not clips.has(key) and FALLBACK.has(key) and FALLBACK[key] != key:
		key = FALLBACK[key]
	return clips.get(key, clips.get("idle", ""))


func animate(delta: float) -> void:
	if _anim:
		var clip := _clip_for(pose)
		if clip != "" and clip != _current and _anim.has_animation(clip):
			_anim.play(clip, 0.2)
			_current = clip
		var refs: Dictionary = manifest.get("clip_speed", {})
		if pose in ["walk", "run", "shamble"] and refs.has(pose if pose != "shamble" else "walk"):
			_anim.speed_scale = clampf(speed / float(refs[pose if pose != "shamble" else "walk"]), 0.5, 1.8)
		else:
			_anim.speed_scale = 1.0
	if _overlay:
		# Arms: aim (converge on the gun), zombie reach (parallel, slightly down),
		# wind-up (raised high = the readable tell), strike (slammed forward-down).
		var arm_pitch := {"aim": aim_pitch, "shamble": -0.15, "windup": 1.15, "strike": -0.35}
		var want := 1.0 if arm_pitch.has(pose) else 0.0
		_overlay.aim_weight = lerpf(_overlay.aim_weight, want, MovementMath.smoothing_alpha(14.0, delta))
		var pitch: float = arm_pitch.get(pose, 0.0)
		var fwd := -global_transform.basis.z.normalized()
		_overlay.aim_dir_world = (fwd * cos(pitch) + Vector3.UP * sin(pitch)).normalized()
		_overlay.right_world = fwd.cross(Vector3.UP).normalized()
		_overlay.converge = pose == "aim"
	# No death clip yet: topple about the feet (same as the placeholder).
	_fall = minf(1.0, _fall + delta * 2.2) if pose in ["dead", "floored"] else maxf(0.0, _fall - delta * 1.4)
	rotation.x = ease(_fall, 2.2) * PI / 2
	_shadow.visible = _fall < 0.4


## Yaw the model faces in its own space (INF if the rig lacks foot/toe bones).
func facing_yaw(inst: Node3D) -> float:
	var bones: Dictionary = manifest.get("bones", {})
	if _skel == null or not bones.has("foot") or not bones.has("toe"):
		return INF
	var f := find_bone_flexible(_skel, bones.foot)
	var t := find_bone_flexible(_skel, bones.toe)
	if f < 0 or t < 0:
		return INF
	var xf := _rel(inst, _skel) if _skel != inst else Transform3D.IDENTITY
	var d := xf.basis * (_skel.get_bone_global_rest(t).origin - _skel.get_bone_global_rest(f).origin)
	d.y = 0.0
	return MovementMath.facing_from_direction(d, INF) if d.length_squared() > 1e-8 else INF


## Mixamo-style workflow: animations live in separate files (one clip per
## download). Copy them onto this character's skeleton, re-pointing each track
## at our Skeleton3D by bone name and rescaling hip motion to our proportions.
func _merge_animation_sources(inst: Node3D) -> void:
	var sources: Array = manifest.get("animation_sources", [])
	if sources.is_empty() or _skel == null:
		return
	if _anim == null:
		_anim = AnimationPlayer.new()
		inst.add_child(_anim)
	var root := _anim.get_node(_anim.root_node)
	var skel_path := String(root.get_path_to(_skel))
	if not _anim.has_animation_library(""):
		_anim.add_animation_library("", AnimationLibrary.new())
	var lib := _anim.get_animation_library("")
	var hips: String = manifest.get("bones", {}).get("hips", "")
	var hips_i := find_bone_flexible(_skel, hips)
	hips = _skel.get_bone_name(hips_i) if hips_i >= 0 else ""
	var our_hips := _skel.get_bone_global_rest(hips_i).origin.y if hips_i >= 0 else 1.0
	for src_path in sources:
		if not ResourceLoader.exists(src_path):
			continue
		var src: Node = load(src_path).instantiate()
		var src_anim := _find(src, "AnimationPlayer") as AnimationPlayer
		var src_skel := _find(src, "Skeleton3D") as Skeleton3D
		if src_anim == null or src_skel == null:
			src.free()
			continue
		var ratio := 1.0
		if hips != "" and find_bone_flexible(src_skel, hips) >= 0:
			var sh := src_skel.get_bone_global_rest(find_bone_flexible(src_skel, hips)).origin.y
			ratio = our_hips / sh if absf(sh) > 1e-5 else 1.0
		for clip in src_anim.get_animation_list():
			if lib.has_animation(clip) or clip == "RESET":
				continue
			var a: Animation = src_anim.get_animation(clip).duplicate(true)
			for i in range(a.get_track_count() - 1, -1, -1):
				var np := a.track_get_path(i)
				var bone := np.get_concatenated_subnames()
				var kind := a.track_get_type(i)
				if bone == "" or _skel.find_bone(bone) < 0 or kind == Animation.TYPE_SCALE_3D \
						or (kind == Animation.TYPE_POSITION_3D and bone != hips):
					a.remove_track(i)
					continue
				a.track_set_path(i, NodePath(skel_path + ":" + bone))
				if kind == Animation.TYPE_POSITION_3D:
					for k in a.track_get_key_count(i):
						a.track_set_key_value(i, k, a.track_get_key_value(i, k) * ratio)
			lib.add_animation(clip, a)
		src.free()


## Turn any human model into a Drowned: waterlogged grey-green skin tone,
## purple-brown marbling, a wet clearcoat film, some subsurface. Keeps the
## model's own textures and multiplies the look on top.
static func zombify(root: Node, cfg: Dictionary) -> void:
	var tint: Array = cfg.get("tint", [0.62, 0.72, 0.64])
	var marble := NoiseTexture2D.new()
	marble.seamless = true
	marble.width = 256
	marble.height = 256
	var fn := FastNoiseLite.new()
	fn.frequency = 0.02
	fn.fractal_octaves = 4
	marble.noise = fn
	var ramp := Gradient.new()
	ramp.set_color(0, Color(0.55, 0.45, 0.55))
	ramp.set_color(1, Color(1.0, 1.0, 0.95))
	marble.color_ramp = ramp
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var m3 := mi as MeshInstance3D
		for sidx in m3.mesh.get_surface_count():
			var src := m3.get_active_material(sidx)
			if not src is BaseMaterial3D:
				continue
			var m: BaseMaterial3D = src.duplicate()
			m.albedo_color = m.albedo_color * Color(tint[0], tint[1], tint[2])
			m.roughness = minf(m.roughness, float(cfg.get("roughness", 0.4)))
			m.clearcoat_enabled = true
			m.clearcoat = float(cfg.get("wet", 0.8))
			m.clearcoat_roughness = 0.08
			m.detail_enabled = true
			m.detail_blend_mode = BaseMaterial3D.BLEND_MODE_MUL
			m.detail_albedo = marble
			m.detail_mask = null
			m.uv1_scale = Vector3.ONE
			m.subsurf_scatter_enabled = true
			m.subsurf_scatter_strength = 0.25
			m3.set_surface_override_material(sidx, m)


## Importers rename bones (Godot turns "mixamorig:Hips" into "mixamorig_Hips"
## because ':' separates bone names in NodePaths). Accept either spelling.
static func find_bone_flexible(sk: Skeleton3D, bone_name: String) -> int:
	if sk == null or bone_name == "":
		return -1
	for candidate in [bone_name, bone_name.replace(":", "_"), bone_name.get_slice(":", 1)]:
		var i := sk.find_bone(candidate)
		if i >= 0:
			return i
	return -1


static func _find(n: Node, cls: String) -> Node:
	if n.is_class(cls):
		return n
	for c in n.get_children():
		var r := _find(c, cls)
		if r:
			return r
	return null


static func _bounds(root: Node3D) -> AABB:
	var box := AABB()
	var first := true
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var xf: Transform3D = root.global_transform.affine_inverse() * (mi as MeshInstance3D).global_transform \
			if root.is_inside_tree() else _rel(root, mi)
		var b := xf * (mi as MeshInstance3D).get_aabb()
		box = b if first else box.merge(b)
		first = false
	return box


static func _rel(root: Node3D, n: Node3D) -> Transform3D:
	var xf := Transform3D.IDENTITY
	var cur: Node = n
	while cur and cur != root:
		if cur is Node3D:
			xf = (cur as Node3D).transform * xf
		cur = cur.get_parent()
	return xf
