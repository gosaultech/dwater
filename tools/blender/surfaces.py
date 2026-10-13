# damned_waters/tools/blender/surfaces.py
# Purpose: materials for the room sets beyond the procedural ones in builders.py:
#   * Poly Haven PBR textures (CC0, fetched by tools/assets/polyhaven.py into pipeline_out/), at
#     their true size in metres, tinted, rougher or smoother as a RoomSpec asks:
#       "ph:herringbone_parquet"  or  {"ph": "plastered_wall", "tint": [0.9, 0.9, 0.95], "scale": 1.0,
#                                      "rough": 1.0, "bump": 1.0, "rot": 90, "value": 1.0}
#   * a plain painted or stained surface with a little life in it:
#       {"color": [0.08, 0.08, 0.09], "rough": 0.5, "metal": 0.0, "noise": 0.15}
#   * two hand-made patterns: {"pattern": "persian", "width": 0.8} (a woven runner) and
#     {"pattern": "folk", "color": [...]} (Hindeloopen painting on a cupboard's panels)
#   * a scan laid as a two-colour checkerboard: {"ph": "marble_01", "checker": 2.5, "tint_a": .., "tint_b": ..}
#   * any scan rained on: {"ph": "herringbone_brick", "wet": 0.8, "puddles": 0.5}: darker and glossier
#     all over, with still puddles (mirror-smooth, flat) where the ground dips
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


def _grey(nt, col, gain=1.0):
    """A photo's light and shade without its dye (a blue linen's weave, made any cloth's)."""
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    nt.links.new(col, bw.inputs["Color"])
    return _math(nt, "MULTIPLY", bw.outputs["Val"], gain, clamp=True)


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
    if ref.get("mono"):
        col = _grey(nt, col, ref["mono"] if not isinstance(ref["mono"], bool) else 1.0)
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
    if "checker" in ref:   # tiles laid in two colours (a marble checkerboard): the scan's veins in both
        ck = nt.nodes.new("ShaderNodeTexChecker")
        ck.inputs["Scale"].default_value = ref["checker"]
        ck.inputs["Color1"].default_value = (*ref.get("tint_a", (0.9, 0.88, 0.84)), 1)
        ck.inputs["Color2"].default_value = (*ref.get("tint_b", (0.02, 0.02, 0.024)), 1)
        nt.links.new(tc.outputs["UV"], ck.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(col, mix.inputs["A"])
        nt.links.new(ck.outputs["Color"], mix.inputs["B"])
        col = mix.outputs["Result"]
    wet, mask = ref.get("wet", 0.0), None
    if wet > 0:   # rain: the whole surface darker, and a puddle mask from noise in metres
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = ref.get("puddle_scale", 0.45)
        nz.inputs["Detail"].default_value = 5.0
        nz.inputs["Roughness"].default_value = 0.6
        nt.links.new(tc.outputs["UV"], nz.inputs["Vector"])
        rp = nt.nodes.new("ShaderNodeValToRGB")
        lo = 0.66 - 0.22 * ref.get("puddles", 0.4)
        rp.color_ramp.elements[0].position, rp.color_ramp.elements[1].position = lo, lo + 0.05
        nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
        mask = rp.outputs["Color"]
        dk = nt.nodes.new("ShaderNodeMix")
        dk.data_type = "RGBA"
        dk.blend_type = "MULTIPLY"
        dk.inputs["Factor"].default_value = 1.0
        dk.inputs["B"].default_value = (1 - 0.35 * wet, 1 - 0.35 * wet, 1 - 0.35 * wet, 1.0)
        nt.links.new(col, dk.inputs["A"])
        pd = nt.nodes.new("ShaderNodeMix")   # under a puddle: darker still
        pd.data_type = "RGBA"
        pd.blend_type = "MULTIPLY"
        nt.links.new(mask, pd.inputs["Factor"])
        nt.links.new(dk.outputs["Result"], pd.inputs["A"])
        pd.inputs["B"].default_value = (0.8, 0.8, 0.8, 1.0)
        col = pd.outputs["Result"]
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
        mul.inputs[1].default_value = ref.get("rough", 1.0) * (1 - 0.55 * wet)
        nt.links.new(rough_src, mul.inputs[0])
        r_out = mul.outputs[0]
        if mask is not None:   # a puddle is a mirror
            mr = nt.nodes.new("ShaderNodeMix")
            mr.data_type = "FLOAT"
            nt.links.new(mask, mr.inputs["Factor"])
            nt.links.new(r_out, mr.inputs["A"])
            mr.inputs["B"].default_value = 0.03
            r_out = mr.outputs["Result"]
        nt.links.new(r_out, b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = ref.get("rough", 0.6)
    if "nor_gl" in maps:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = ref.get("bump", 1.0)
        if mask is not None:   # and flat: the water fills the joints
            fl = nt.nodes.new("ShaderNodeMath")
            fl.operation = "MULTIPLY_ADD"
            nt.links.new(mask, fl.inputs[0])
            fl.inputs[1].default_value = -ref.get("bump", 1.0) * 0.9
            fl.inputs[2].default_value = ref.get("bump", 1.0)
            nt.links.new(fl.outputs[0], nm.inputs["Strength"])
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
    if "coat" in ref:   # car paint: a clear lacquer over the colour
        b.inputs["Coat Weight"].default_value = ref["coat"]
        b.inputs["Coat Roughness"].default_value = ref.get("coat_rough", 0.05)
    if "transmission" in ref:
        b.inputs["Transmission Weight"].default_value = ref["transmission"]
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def _mix(nt, a, b, fac):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    nt.links.new(fac, m.inputs["Factor"])
    for sock, v in (("A", a), ("B", b)):
        if isinstance(v, tuple):
            m.inputs[sock].default_value = (*v, 1)
        else:
            nt.links.new(v, m.inputs[sock])
    return m.outputs["Result"]


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def persian(nt, out, ref):
    """A Persian runner, woven: a madder-red field of small repeating lozenges, a dark navy border
    band between thin cream guard stripes, worn paler down the middle where feet go. UVs in metres,
    centred across (u) the rug and along it (v); ref "width" is the rug's width (m)."""
    w = ref.get("width", 0.8)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    u, v = sep.outputs["X"], sep.outputs["Y"]
    # distance in from the nearest long edge (0 at the edge; the rug's UVs are centred across it)
    edge = _math(nt, "SUBTRACT", w / 2, _math(nt, "ABSOLUTE", u))
    border = _math(nt, "LESS_THAN", edge, 0.11)
    guard = _math(nt, "MULTIPLY", _math(nt, "GREATER_THAN", edge, 0.085), border)
    rot = nt.nodes.new("ShaderNodeMapping")   # the field's lozenges: a checker turned 45 degrees
    rot.inputs["Rotation"].default_value = (0, 0, math.radians(45))
    nt.links.new(tc.outputs["UV"], rot.inputs["Vector"])
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 9.0
    ck.inputs["Color1"].default_value = (0.24, 0.035, 0.03, 1)
    ck.inputs["Color2"].default_value = (0.16, 0.02, 0.025, 1)
    nt.links.new(rot.outputs["Vector"], ck.inputs["Vector"])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")   # small cream knots at the lozenges' corners
    vor.inputs["Scale"].default_value = 26.0
    nt.links.new(tc.outputs["UV"], vor.inputs["Vector"])
    knot = _math(nt, "LESS_THAN", vor.outputs["Distance"], 0.12)
    field = _mix(nt, ck.outputs["Color"], (0.55, 0.45, 0.3), knot)
    band = _mix(nt, (0.035, 0.045, 0.1), (0.62, 0.55, 0.42), guard)
    col = _mix(nt, field, band, border)
    wear = nt.nodes.new("ShaderNodeTexNoise")
    wear.inputs["Scale"].default_value = 3.0
    nt.links.new(tc.outputs["UV"], wear.inputs["Vector"])
    mid = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, _math(nt, "MINIMUM", _math(nt, "MULTIPLY", edge, 4.0), 1.0)), -1.0)
    worn = _math(nt, "MULTIPLY", _math(nt, "ADD", mid, 1.0), wear.outputs["Fac"], clamp=True)
    col = _mix(nt, col, (0.32, 0.22, 0.17), _math(nt, "MULTIPLY", worn, 0.45))
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.97
    b.inputs["Sheen Weight"].default_value = 0.4
    fibre = nt.nodes.new("ShaderNodeTexNoise")
    fibre.inputs["Scale"].default_value = 180.0
    nt.links.new(tc.outputs["UV"], fibre.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    nt.links.new(fibre.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def folk(nt, out, ref):
    """Hindeloopen folk painting on a cupboard's panels: a deep blue-green ground with red-and-cream
    flowers and leafy scrolls, the varnish gone amber and crazed. Object coordinates (the panel's
    own), so each panel carries its own posy."""
    ground = tuple(ref.get("color", (0.05, 0.16, 0.17)))
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (6.0, 6.0, 6.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")   # flower heads
    vor.inputs["Scale"].default_value = 1.6
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    d = vor.outputs["Distance"]
    petal = _math(nt, "LESS_THAN", d, 0.22)
    heart = _math(nt, "LESS_THAN", d, 0.08)
    wave = nt.nodes.new("ShaderNodeTexWave")     # the leafy scrolls between them
    wave.wave_type = "RINGS"
    wave.inputs["Scale"].default_value = 3.2
    wave.inputs["Distortion"].default_value = 6.0
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])
    leaf = _math(nt, "GREATER_THAN", wave.outputs["Fac"], 0.86)
    col = _mix(nt, ground, (0.16, 0.22, 0.09), leaf)
    col = _mix(nt, col, (0.42, 0.05, 0.04), petal)
    col = _mix(nt, col, (0.7, 0.62, 0.45), heart)
    varnish = nt.nodes.new("ShaderNodeTexNoise")
    varnish.inputs["Scale"].default_value = 40.0
    nt.links.new(tc.outputs["Object"], varnish.inputs["Vector"])
    col = _mix(nt, col, (0.3, 0.2, 0.08), _math(nt, "MULTIPLY", varnish.outputs["Fac"], 0.35))
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(col, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.38
    b.inputs["Coat Weight"].default_value = 0.4
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def is_ref(key):
    return isinstance(key, dict) or (isinstance(key, str) and key.startswith("ph:"))


def room_card(nt, out, ref):
    """A real room behind a lit window ({"room": hdri id, "strength": s}): a patch of a CC0 interior
    panorama, at its own light levels. Which patch is the card object's own "room_u"/"room_v"
    (custom properties), so one material serves every window that shows that room."""
    a = asset(ref["room"])
    img = bpy.data.images.load(str(Path(a["_dir"]) / a["hdr"]), check_existing=True)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["UV"], sep.inputs["Vector"])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    for axis, prop, span in (("X", "room_u", ref.get("span_u", 0.14)), ("Y", "room_v", ref.get("span_v", 0.3))):
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_type = "OBJECT"
        at.attribute_name = prop
        ma = nt.nodes.new("ShaderNodeMath")
        ma.operation = "MULTIPLY_ADD"
        nt.links.new(sep.outputs[axis], ma.inputs[0])
        ma.inputs[1].default_value = span
        nt.links.new(at.outputs["Fac"], ma.inputs[2])
        nt.links.new(ma.outputs[0], comb.inputs[axis])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "REPEAT"
    nt.links.new(comb.outputs["Vector"], tex.inputs["Vector"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = ref.get("strength", 1.0)
    nt.links.new(tex.outputs["Color"], e.inputs["Color"])
    nt.links.new(e.outputs[0], out.inputs["Surface"])
    return e


def stripes(nt, out, ref):
    """Awning canvas: two colours in stripes ref["width"] wide, across the UV's x (metres); with
    "canvas", over a real canvas's weave (a CC0 photo, "weave": its id), washed out and stained."""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave")
    wv.wave_type = "BANDS"
    wv.bands_direction = "X"
    wv.inputs["Scale"].default_value = 1.0 / (2 * ref.get("width", 0.25))
    wv.inputs["Distortion"].default_value = 0.0
    nt.links.new(tc.outputs["UV"], wv.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.interpolation = "CONSTANT"
    a, b = ref["colors"]
    r.color_ramp.elements[0].color = (*a, 1)
    r.color_ramp.elements[1].position = 0.5
    r.color_ramp.elements[1].color = (*b, 1)
    nt.links.new(wv.outputs["Color"], r.inputs["Fac"])
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.85
    col = r.outputs["Color"]
    if ref.get("canvas"):   # a real canvas's weave (a CC0 photo: its shading and its bumps), washed out, stained
        a_ = asset(ref.get("weave", "rough_linen"))
        d = Path(a_["_dir"])
        dims = a_.get("dimensions_mm") or [1000, 1000]
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1000.0 / dims[0] * 2.0, 1000.0 / dims[1] * 2.0, 1.0)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        maps = a_.get("maps", {})
        weave = _tex(nt, mp.outputs["Vector"], _image(d / maps["diff"], True))
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 0.85
        nt.links.new(col, mul.inputs["A"])
        nt.links.new(_grey(nt, weave.outputs["Color"], 1.9), mul.inputs["B"])
        lift = nt.nodes.new("ShaderNodeMix")   # (the photo is a pale linen: lift it back to the stripe's colour)
        lift.data_type = "RGBA"
        lift.blend_type = "MIX"
        lift.inputs["Factor"].default_value = 0.35
        nt.links.new(mul.outputs["Result"], lift.inputs["A"])
        nt.links.new(col, lift.inputs["B"])
        nz = nt.nodes.new("ShaderNodeTexNoise")   # rain stains, the grime of the street
        nz.inputs["Scale"].default_value = 2.2
        nz.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["UV"], nz.inputs["Vector"])
        rp = nt.nodes.new("ShaderNodeValToRGB")
        rp.color_ramp.elements[0].position, rp.color_ramp.elements[1].position = 0.45, 0.75
        nt.links.new(nz.outputs["Fac"], rp.inputs["Fac"])
        dirt = nt.nodes.new("ShaderNodeMix")
        dirt.data_type = "RGBA"
        dirt.blend_type = "MULTIPLY"
        nt.links.new(rp.outputs["Color"], dirt.inputs["Factor"])
        nt.links.new(lift.outputs["Result"], dirt.inputs["A"])
        dirt.inputs["B"].default_value = (0.55, 0.5, 0.42, 1.0)
        col = dirt.outputs["Result"]
        if "nor_gl" in maps:
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = 1.2
            nt.links.new(_tex(nt, mp.outputs["Vector"], _image(d / maps["nor_gl"], False)).outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    nt.links.new(col, bs.inputs["Base Color"])
    nt.links.new(bs.outputs[0], out.inputs["Surface"])
    return bs


def build(nt, out, key):
    if isinstance(key, str) or "ph" in key:
        return pbr(nt, out, key)
    if "room" in key:
        return room_card(nt, out, key)
    if key.get("pattern") == "stripes":
        return stripes(nt, out, key)
    if "emit" in key:   # a lit sign, a pilot light: light of its own
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*key["emit"], 1)
        e.inputs["Strength"].default_value = key.get("strength", 5.0)
        nt.links.new(e.outputs[0], out.inputs["Surface"])
        return e
    if key.get("pattern") == "persian":
        return persian(nt, out, key)
    if key.get("pattern") == "folk":
        return folk(nt, out, key)
    return painted(nt, out, key)


def cache_key(key):
    return key if isinstance(key, str) else json.dumps(key, sort_keys=True)
