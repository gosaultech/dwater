# damned_waters/game/src/actors/mesh_kit.gd
# Purpose: static primitive builders shared by every procedural body.
class_name MeshKit
extends RefCounted


static func mat(c: Color, wet: bool = false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 0.38 if wet else 0.8
	if wet:
		m.metallic_specular = 0.65
	return m


static func capsule(r: float, h: float, c: Color, wet: bool = false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = r
	cm.height = maxf(h, 2.0 * r)
	cm.radial_segments = 12
	cm.rings = 4
	cm.material = mat(c, wet)
	mi.mesh = cm
	return mi


static func sphere(r: float, c: Color, wet: bool = false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = r
	sm.height = 2.0 * r
	sm.radial_segments = 12
	sm.rings = 6
	sm.material = mat(c, wet)
	mi.mesh = sm
	return mi


static func box(s: Vector3, c: Color, wet: bool = false) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = s
	bm.material = mat(c, wet)
	mi.mesh = bm
	return mi


static func blob_shadow(size: float = 0.75) -> MeshInstance3D:
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	for y in 64:
		for x in 64:
			var d := Vector2(x - 31.5, y - 31.5).length() / 32.0
			img.set_pixel(x, y, Color(0, 0, 0, clampf(1.0 - d, 0.0, 1.0) * 0.65))
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_texture = ImageTexture.create_from_image(img)
	var q := QuadMesh.new()
	q.size = Vector2(size, size)
	q.material = m
	var mi := MeshInstance3D.new()
	mi.mesh = q
	mi.rotation.x = -PI / 2
	mi.position.y = 0.015
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.name = "BlobShadow"
	return mi
