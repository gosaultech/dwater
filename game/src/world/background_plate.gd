# damned_waters/game/src/world/background_plate.gd
# Purpose: a quad parented to the camera that exactly fills the view frustum
# and displays the current shot's plate (color + depth) via plate.gdshader.
class_name BackgroundPlate
extends MeshInstance3D

const DISTANCE := 1.0
const ASPECT := 16.0 / 9.0

var _mat := ShaderMaterial.new()


func _init() -> void:
	name = "BackgroundPlate"
	_mat.shader = preload("res://src/world/plate.gdshader")
	material_override = _mat
	mesh = QuadMesh.new()
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	position = Vector3(0, 0, -DISTANCE)
	extra_cull_margin = 1.0


func fit(fov_deg: float) -> void:
	var h := 2.0 * DISTANCE * tan(deg_to_rad(fov_deg) * 0.5) * 1.002
	(mesh as QuadMesh).size = Vector2(h * ASPECT, h)


func show_shot(color: Texture2D, depth: Texture2D) -> void:
	_mat.set_shader_parameter("color_tex", color)
	_mat.set_shader_parameter("depth_tex", depth)
	_mat.set_shader_parameter("use_depth", depth != null)
	_mat.set_shader_parameter("depth_max", DepthCodec.DEPTH_MAX_M)
