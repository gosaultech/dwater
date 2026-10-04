# damned_waters/tools/blender/surfaces.py
# Purpose: materials for the room sets beyond the procedural ones in builders.py:
#   * Poly Haven PBR textures (CC0, fetched by tools/assets/polyhaven.py into pipeline_out/), at
#     their true size in metres, tinted, rougher or smoother as a RoomSpec asks:
#       "ph:herringbone_parquet"  or  {"ph": "plastered_wall", "tint": [0.9, 0.9, 0.95], "scale": 1.0,
#                                      "rough": 1.0, "bump": 1.0, "rot": 90, "value": 1.0}
#   * a plain painted or stained surface with a little life in it:
#       {"color": [0.08, 0.08, 0.09], "rough": 0.5, "metal": 0.0, "noise": 0.15}
# Box UVs in builders.py are in metres, so a texture's real size (from Poly Haven's metadata) maps
# straight on: a 3.4 m parquet scan covers 3.4 m of floor.
#
# ELI5: wallpaper sold by the metre. The roll says how wide one repeat is; we hang it at that size.
import json
import math
import os
from pathlib import Path

import bpy

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "pipeline_out" / "assets" / "polyhaven"


def asset(asset_id):
    """The cached asset.json (with "_dir"), preferring DW_ASSET_RES, else the sharpest there is."""
    pref = os.environ.get("DW_ASSET_RES", "")
    for res in [r for r in (pref, "4k", "2k", "1k") if r]:
        p = CACHE / asset_id / res / "asset.json"
        if p.exists():
            m = json.loads(p.read_text())
            m["_dir"] = str(p.parent)
            return m
    raise FileNotFoundError(f"Poly Haven asset '{asset_id}' is not fetched: run tools/assets/polyhaven.py fetch")


def _image(path, colour):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def _tex(nt, vec, img):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Smart"
    nt.links.new(vec, t.inputs["Vector"])
    return t


def pbr(nt, out, ref):
    """Wire a Poly Haven texture set into a Principled BSDF."""
    if isinstance(ref, str):
        ref = {"ph": ref[3:]}
    a = asset(ref["ph"])
    d = Path(a["_dir"])
    dims = a.get("dimensions_mm") or [1000, 1000]
    size_u = dims[0] / 1000.0 * ref.get("scale", 1.0)
    size_v = dims[1] / 1000.0 * ref.get("scale", 1.0)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / size_u, 1.0 / size_v, 1.0)
    mp.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(ref.get("rot", 0.0)))
    mp.inputs["Location"].default_value = (*ref.get("offset", (0.0, 0.0)), 0.0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    vec = mp.outputs["Vector"]
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    maps = a["maps"]
    col = _tex(nt, vec, _image(d / maps["diff"], True)).outputs["Color"]
    tint = ref.get("tint")
    value = ref.get("value", 1.0)
    if tint or value != 1.0:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        t = tint or (1.0, 1.0, 1.0)
        mix.inputs["B"].default_value = (t[0] * value, t[1] * value, t[2] * value, 1.0)
        nt.links.new(col, mix.inputs["A"])
        col = mix.outputs["Result"]
    nt.links.new(col, b.inputs["Base Color"])
    rough_src = None
    if "rough" in maps:
        rough_src = _tex(nt, vec, _image(d / maps["rough"], False)).outputs["Color"]
    elif "arm" in maps:
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(_tex(nt, vec, _image(d / maps["arm"], False)).outputs["Color"], sep.inputs["Color"])
        rough_src = sep.outputs["Green"]
    if rough_src is not None:
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.use_clamp = True
        mul.inputs[1].default_value = ref.get("rough", 1.0)
        nt.links.new(rough_src, mul.inputs[0])
        nt.links.new(mul.outputs[0], b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = ref.get("rough", 0.6)
    if "nor_gl" in maps:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = ref.get("bump", 1.0)
        nt.links.new(_tex(nt, vec, _image(d / maps["nor_gl"], False)).outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = ref.get("metal", 0.0)
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def painted(nt, out, ref):
    """A plain surface (paint, stain, steel) with a faint mottle so it never looks like plastic."""
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    c = ref.get("color", [0.5, 0.5, 0.5])
    k = ref.get("noise", 0.12)
    if k > 0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = ref.get("noise_scale", 6.0)
        n.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
        r = nt.nodes.new("ShaderNodeValToRGB")
        e = r.color_ramp.elements
        e[0].color = (c[0] * (1 - k), c[1] * (1 - k), c[2] * (1 - k), 1)
        e[1].color = (min(1, c[0] * (1 + k)), min(1, c[1] * (1 + k)), min(1, c[2] * (1 + k)), 1)
        nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
        nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = ref.get("bump", 0.05)
        nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    else:
        b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Roughness"].default_value = ref.get("rough", 0.5)
    b.inputs["Metallic"].default_value = ref.get("metal", 0.0)
    if "transmission" in ref:
        b.inputs["Transmission Weight"].default_value = ref["transmission"]
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def is_ref(key):
    return isinstance(key, dict) or (isinstance(key, str) and key.startswith("ph:"))


def build(nt, out, key):
    if isinstance(key, str) or "ph" in key:
        return pbr(nt, out, key)
    return painted(nt, out, key)


def cache_key(key):
    return key if isinstance(key, str) else json.dumps(key, sort_keys=True)
