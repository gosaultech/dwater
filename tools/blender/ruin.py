# damned_waters/tools/blender/ruin.py
# Purpose: the catastrophe kit (Blender side; the brief is docs/city_aftermath.md): what the water,
# the panic and the survivors left on the streets. Paint and paper on the walls ("spray": decals
# drawn by tools/assets/decals.py), windows and doors boarded with plywood ("boards"), the dead in
# bags ("body_bag"), a tram's wire down across the road ("wire_down"), soot where something burned
# ("scorch"), and the flood's silt over the street, real scanned mud laid in patches and drifted
# thick against whatever stands ("silt"). Coordinates as in street.py (Godot frame, metres; a
# prop's +z its front, away from the wall it's on).
#
# ELI5: the art department's "breakdown" crew, sent in after the set is built: they paint the
# messages, nail the boards up, and shovel the mud in where the water would have left it.
import math
import random
from pathlib import Path

import bpy

import builders
import kit
from roomspec import g2b
from street import Acc, M, ball, lbox

DECALS = Path(__file__).resolve().parents[2] / "pipeline_out" / "assets" / "decals"
_DECAL_MATS = {}


def _decal_material(dc):
    """The decal's picture on a sheet: its colour, its alpha cut round the paint; paint is a little
    glossy in the rain, paper isn't."""
    key = dc["id"]
    if key in _DECAL_MATS:
        return _DECAL_MATS[key]
    m = bpy.data.materials.new("decal_" + key)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    path = DECALS / f"{key}.png"
    if path.exists():
        tex.image = bpy.data.images.load(str(path), check_existing=True)
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
        nt.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
    else:
        print(f"[ruin] missing decal {path} (run tools/assets/decals.py make)")
        b.inputs["Alpha"].default_value = 0.0
    b.inputs["Roughness"].default_value = 0.8 if dc.get("style") == "poster" else 0.38
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    _DECAL_MATS[key] = m
    return m


def spray(root, p, w, h, d):
    """A decal on a wall or a board: a sheet w x h, its foot at the prop's spot, a hair out from the
    surface it's on (+z)."""
    a = Acc()
    z = p.get("out", 0.012)
    a.quad((-w / 2, 0.0, z), (w / 2, 0.0, z), (w / 2, h, z), (-w / 2, h, z))
    ob = a.build("decal", _decal_material(p["decal"]), root, smooth=False)
    if ob is not None and ob.data.uv_layers:
        uv = ob.data.uv_layers.active.data   # (the quad's corners: the whole picture)
        for i, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
            if i < len(uv):
                uv[i].uv = (u, v)


def boards(root, p, w, h, d):
    """Plywood nailed over a window or a door, w x h, its foot at the prop's spot: planks across with
    gaps between them, none quite straight, and ("x": true) two more nailed corner to corner."""
    rng = random.Random(p.get("seed", 9))
    ply = M(p.get("material", {"ph": "plywood", "tint": [0.78, 0.74, 0.68], "rough": 0.85}))
    nail = M({"color": [0.3, 0.3, 0.32], "rough": 0.4, "metal": 0.9})
    t = 0.022
    z0 = p.get("out", 0.02)
    y = 0.0
    while y < h - 0.05:
        ph = min(rng.uniform(0.22, 0.42), h - y)
        hold = builders.empty_at("plank", (rng.uniform(-0.04, 0.04), y + ph / 2, z0 + t / 2), 0.0)
        hold.parent = root
        hold.location = g2b((rng.uniform(-0.04, 0.04), y + ph / 2, z0 + t / 2))
        hold.rotation_euler[1] = math.radians(rng.uniform(-2.5, 2.5))   # (about the wall's normal)
        ext = rng.uniform(0.05, 0.16)
        lbox(hold, "plank", (-w / 2 - ext, -ph / 2 + 0.01, -t / 2), (w / 2 + ext * rng.uniform(0.2, 1.0), ph / 2 - 0.01, t / 2), ply)
        for sx in (-1, 1):
            lbox(hold, "nail", (sx * w * 0.44 - 0.008, -0.008, t / 2), (sx * w * 0.44 + 0.008, 0.008, t / 2 + 0.006), nail)
        y += ph + rng.uniform(0.01, 0.07)
    if p.get("x"):
        L = math.hypot(w, h)
        for sgn in (-1, 1):
            hold = builders.empty_at("brace", (0.0, h / 2, z0 + t * 1.6), 0.0)
            hold.parent = root
            hold.location = g2b((0.0, h / 2, z0 + t * 1.6))
            hold.rotation_euler[1] = sgn * math.atan2(h, w)
            lbox(hold, "brace", (-L / 2, -0.1, -t / 2), (L / 2, 0.1, t / 2), ply)


def body_bag(root, p, w, h, d):
    """Someone in a black bag on the ground, w long: the shape says enough; a zip down its length."""
    bag = M({"color": [0.018, 0.019, 0.021], "rough": 0.32, "noise": 0.15, "noise_scale": 6.0, "grime": 1.2})
    kit.soft(root, "bag", (0.0, h / 2, 0.0), (w, h, d), bag, min(h, d) * 0.45, 4)
    kit.soft(root, "bag_head", (w / 2 - 0.28, h * 0.55, 0.0), (0.42, h * 1.12, d * 0.8), bag, min(h, d) * 0.4, 4)
    lbox(root, "zip", (-w / 2 + 0.1, h - 0.004, -0.012), (w / 2 - 0.08, h + 0.008, 0.012), M({"color": [0.5, 0.5, 0.52], "rough": 0.35, "metal": 0.8}))


def wire_down(root, p, w, h, d):
    """A tram's overhead wire, snapped: hanging from where it still holds ("from", relative to the
    prop's spot, up at the wire's height) in a sag to the road at the prop's spot, then lying in loose
    loops ("slack" m of it) where it fell. The engine sparks at its end (the room's "fx")."""
    wire = Acc()
    fx, fy, fz = p.get("from", [0.0, 5.8, -6.0])
    n = 28
    pts = []
    for i in range(n + 1):   # a hanging chain's curve, near enough a parabola
        t = i / n
        sag = 4.0 * p.get("sag", 0.9) * t * (1 - t)
        pts.append((fx * (1 - t), fy * (1 - t) - sag * fy * 0.25, fz * (1 - t)))
    rng = random.Random(p.get("seed", 3))
    slack = p.get("slack", 3.0)
    a, x, z = rng.uniform(0, math.tau), 0.0, 0.0
    for i in range(int(slack / 0.15)):   # the loose end, coiled where it dropped
        a += rng.uniform(-0.6, 0.9)
        x, z = x + 0.15 * math.cos(a), z + 0.15 * math.sin(a)
        pts.append((x, 0.02, z))
    for (ax, ay, az), (bx, by, bz) in zip(pts, pts[1:]):
        wire.rod((ax, ay, az), (bx, by, bz), 0.011, 0.011, 6)
    wire.build("wire_down", M({"color": [0.06, 0.05, 0.04], "rough": 0.45, "metal": 0.7}), root)
    if p.get("glow", True):   # its end, white-hot where it touches the wet road
        ball(root, "wire_end", (x, 0.03, z), 0.035, builders.emissive("wire_hot", (0.75, 0.85, 1.0), 40.0), seg=8)


def scorch(root, p, w, h, d):
    """Soot on the ground round something that burned: black at the heart, ragged at its edge."""
    m = bpy.data.materials.new("scorch")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.012, 0.011, 0.01, 1.0)
    b.inputs["Roughness"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (2.0 / w, 2.0 / max(d, 1e-3), 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(grad.outputs["Fac"], mul.inputs[0])
    nt.links.new(nz.outputs["Fac"], mul.inputs[1])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.interpolation_type = "SMOOTHSTEP"
    rr.inputs["From Min"].default_value, rr.inputs["From Max"].default_value = 0.05, 0.4
    nt.links.new(mul.outputs[0], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Alpha"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    a = Acc()
    a.quad((-w / 2, 0.012, -d / 2), (-w / 2, 0.012, d / 2), (w / 2, 0.012, d / 2), (w / 2, 0.012, -d / 2))
    a.build("scorch", m, root, smooth=False)


def silt(root, p, w, h, d):
    """The flood's silt over a stretch of street, w x d: a scanned mud ("material", wet in the rain)
    laid in patches, thickest against walls, kerbs and anything standing (where the water slowed and
    dropped it), thin and broken out in the open where feet and wheels went through."""
    base = builders.material(p.get("material", {"ph": "brown_mud_02", "wet": 0.7, "puddles": 0.25}))
    m = base.copy()
    m.name = "silt_%s" % p.get("seed", 0)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = p.get("patch", 0.32)
    nz.inputs["Detail"].default_value = 5.0
    nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 7.0
    fine.inputs["Detail"].default_value = 10.0
    nt.links.new(geo.outputs["Position"], fine.inputs["Vector"])
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 4
    ao.inputs["Distance"].default_value = p.get("reach", 1.6)

    def math_(op, x, y):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for i, v in enumerate((x, y)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]
    cover = p.get("cover", 0.5)
    near = math_("MULTIPLY", math_("SUBTRACT", 1.0, ao.outputs["AO"]), 2.2)
    patches = math_("SUBTRACT", nz.outputs["Fac"], 0.62 - cover * 0.3)
    amount = math_("ADD", math_("MULTIPLY", patches, 4.0), near)
    ragged = math_("ADD", amount, math_("MULTIPLY", math_("SUBTRACT", fine.outputs["Fac"], 0.5), 0.9))
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.interpolation_type = "SMOOTHSTEP"
    rr.inputs["From Min"].default_value, rr.inputs["From Max"].default_value = 0.15, 0.45
    nt.links.new(ragged, rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Alpha"])
    a = Acc()
    y = p.get("lift", 0.006)
    a.quad((-w / 2, y, -d / 2), (-w / 2, y, d / 2), (w / 2, y, d / 2), (w / 2, y, -d / 2))
    ob = a.build("silt", m, root, smooth=False)
    if ob is not None:
        ob.visible_shadow = False   # (a skin of mud: it shades nothing)


kit.PROPS.update({"spray": spray, "boards": boards, "body_bag": body_bag, "wire_down": wire_down, "scorch": scorch, "silt": silt})
