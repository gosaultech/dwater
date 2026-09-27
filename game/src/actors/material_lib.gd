# damned_waters/game/src/actors/material_lib.gd
# Purpose: creature surface library. Blender exports material NAMES only; this
# maps each name to a PBR material built from tools/art/materials.py textures,
# projected triplanar (so models need no UV unwrapping).
class_name MaterialLib
extends RefCounted

const DIR := "res://assets/materials/%s_%s.png"
const SPEC := {  # tex/normal = texture set; color multiplies albedo
	"shroud": {"tex": "shroud", "scale": 3.0, "rough": 0.5, "coat": 0.35},
	"skin_drowned": {"tex": "skin_drowned", "scale": 4.0, "rough": 0.35, "coat": 0.6},
	"skin_pale": {"tex": "skin_pale", "scale": 5.0, "rough": 0.55, "rim": 0.35},
	"coat_wet": {"tex": "coat_wet", "scale": 3.0, "rough": 0.45, "coat": 0.3},
	"rust": {"tex": "rust", "scale": 6.0, "rough": 0.8, "metal": 0.35},
	"rope": {"tex": "rope", "scale": 10.0, "rough": 0.9},
	"flesh": {"tex": "flesh", "scale": 2.0, "rough": 0.3, "coat": 0.8},
	"waxcoat": {"tex": "waxcoat", "scale": 2.5, "rough": 0.35, "coat": 0.5},
	"leather": {"tex": "leather", "scale": 4.0, "rough": 0.5},
	"kelp": {"tex": "kelp", "scale": 6.0, "rough": 0.3, "coat": 0.6},
	"poncho": {"tex": "shroud", "color": Color(0.95, 0.72, 0.18), "scale": 3.0, "rough": 0.2, "coat": 0.9},
	"jacket": {"normal": "coat_wet", "color": Color(0.13, 0.2, 0.14), "scale": 3.0, "rough": 0.45, "coat": 0.25},
	"denim": {"normal": "coat_wet", "color": Color(0.09, 0.12, 0.19), "scale": 6.0, "rough": 0.8},
	"skin": {"tex": "skin_pale", "color": Color(1.0, 0.8, 0.66), "scale": 5.0, "rough": 0.5},
	"backpack": {"tex": "leather", "color": Color(0.5, 0.5, 0.5), "scale": 4.0, "rough": 0.7},
	"gunmetal": {"color": Color(0.05, 0.05, 0.055), "rough": 0.35, "metal": 0.8},
	"teeth": {"color": Color(0.72, 0.66, 0.5), "rough": 0.4},
	"tire": {"color": Color(0.03, 0.03, 0.03), "rough": 0.85},
	"brass": {"color": Color(0.6, 0.45, 0.2), "rough": 0.35, "metal": 0.9},
	"hair_wet": {"color": Color(0.015, 0.015, 0.015), "rough": 0.2, "coat": 0.8},
	"void": {"unshaded": true, "color": Color(0, 0, 0)},
	"heart": {"color": Color(0.2, 1.0, 0.6), "emit": Color(0.25, 1.0, 0.62), "energy": 3.0},
	"lens": {"color": Color(0.1, 0.2, 0.18), "emit": Color(0.35, 0.9, 0.7), "energy": 0.6, "rough": 0.05},
}

static var _cache := {}


static func get_material(mat_name: String) -> StandardMaterial3D:
	var key := mat_name.get_slice(".", 0)  # Blender duplicates arrive as "shroud.001"
	if _cache.has(key):
		return _cache[key]
	var s: Dictionary = SPEC.get(key, {"color": Color(1, 0, 1)})  # magenta = unmapped, on purpose
	var m := StandardMaterial3D.new()
	m.resource_name = key
	m.albedo_color = s.get("color", Color.WHITE)
	if s.get("unshaded", false):
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	if s.has("tex"):
		m.albedo_texture = load(DIR % [s.tex, "albedo"])
	var normal: String = s.get("normal", s.get("tex", ""))
	if normal != "":
		m.normal_enabled = true
		m.normal_texture = load(DIR % [normal, "normal"])
		m.normal_scale = 1.2
	if s.has("tex") or s.has("normal"):
		m.uv1_triplanar = true
		m.uv1_scale = Vector3.ONE * float(s.get("scale", 3.0))
	m.roughness = float(s.get("rough", 0.6))
	m.metallic = float(s.get("metal", 0.0))
	if s.has("coat"):
		m.clearcoat_enabled = true
		m.clearcoat = float(s.coat)
		m.clearcoat_roughness = 0.1
	if s.has("rim"):
		m.rim_enabled = true
		m.rim = float(s.rim)
		m.rim_tint = 0.3
	if s.has("emit"):
		m.emission_enabled = true
		m.emission = s.emit
		m.emission_energy_multiplier = float(s.get("energy", 1.0))
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	_cache[key] = m
	return m
