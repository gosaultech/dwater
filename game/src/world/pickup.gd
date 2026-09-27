# damned_waters/game/src/world/pickup.gd
# Purpose: a real-time item on top of the painted background, with a glint so
# the player can spot it. Items are never baked into plates: they must vanish
# when taken.
class_name Pickup
extends Node3D

var item_id := ""
var _glint: MeshInstance3D
var _t := 0.0


func setup(id_: String, at: Vector3) -> Pickup:
	item_id = id_
	position = at
	var body := MeshInstance3D.new()
	var box := BoxMesh.new()
	var mat := StandardMaterial3D.new()
	match id_:
		"cellar_key":
			box.size = Vector3(0.09, 0.015, 0.03)
			mat.albedo_color = Color(0.45, 0.5, 0.3)
			mat.metallic = 1.0
			mat.roughness = 0.35
		"handgun_ammo":
			box.size = Vector3(0.12, 0.06, 0.08)
			mat.albedo_color = Color(0.35, 0.28, 0.1)
		"shotgun":
			box.size = Vector3(0.9, 0.05, 0.1)
			mat.albedo_color = Color(0.2, 0.11, 0.05)
			mat.roughness = 0.4
		"shotgun_shells":
			box.size = Vector3(0.1, 0.05, 0.07)
			mat.albedo_color = Color(0.55, 0.08, 0.05)
		"first_aid":
			box.size = Vector3(0.22, 0.08, 0.14)
			mat.albedo_color = Color(0.85, 0.85, 0.82)
			var cross := MeshInstance3D.new()
			var cm := BoxMesh.new()
			cm.size = Vector3(0.1, 0.082, 0.03)
			var red := StandardMaterial3D.new()
			red.albedo_color = Color(0.7, 0.05, 0.05)
			cm.material = red
			cross.mesh = cm
			add_child(cross)
			var cross2 := cross.duplicate() as MeshInstance3D
			cross2.rotation.y = PI / 2
			add_child(cross2)
		_:
			box.size = Vector3(0.1, 0.1, 0.1)
	box.material = mat
	body.mesh = box
	body.position.y = box.size.y / 2
	add_child(body)
	_glint = MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(0.18, 0.18)
	var gm := StandardMaterial3D.new()
	gm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	gm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	gm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	gm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	gm.albedo_texture = _glint_texture()
	gm.albedo_color = Color(1.0, 0.95, 0.8)
	q.material = gm
	_glint.mesh = q
	_glint.position.y = 0.08
	add_child(_glint)
	return self


func _process(delta: float) -> void:
	_t += delta
	var pulse := pow(maxf(0.0, sin(_t * 2.2)), 6.0)
	_glint.scale = Vector3.ONE * (0.3 + pulse)
	_glint.visible = pulse > 0.02


static func _glint_texture() -> Texture2D:
	var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	for y in 32:
		for x in 32:
			var d := Vector2(x - 15.5, y - 15.5)
			var star := maxf(0.0, 1.0 - absf(d.x) / 1.5) * maxf(0.0, 1.0 - absf(d.y) / 16.0) \
				+ maxf(0.0, 1.0 - absf(d.y) / 1.5) * maxf(0.0, 1.0 - absf(d.x) / 16.0)
			var a := clampf(star + maxf(0.0, 1.0 - d.length() / 6.0), 0.0, 1.0)
			img.set_pixel(x, y, Color(1, 1, 1, a))
	return ImageTexture.create_from_image(img)
