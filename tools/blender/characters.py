# damned_waters/tools/blender/characters.py
# Purpose: procedural "sculpt" kit for the cast. Bodies are skeletons of points
# wrapped by Blender's Skin modifier + Subdivision (a classic fast way to block
# organic base meshes), then dressed: faces, hair, clothes, wet materials.
# These are LOOK TARGETS (concept renders + target frames), and the base meshes
# you'd refine in sculpt mode before rigging for the game.
#
# Coordinates: Blender, Z up, character front = +Y (Godot -Z). place() takes
# Godot positions/yaw so characters drop straight into RoomSpec scenes.
import math
import random

import bpy
from mathutils import Vector

from roomspec import g2b

_MATS = {}
SIDES = {"l": -1.0, "r": 1.0}


# ───────────────────────────── materials ────────────────────────────────────
def _pbsdf(name):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m, nt, b


def _noise_ramp(nt, scale, stops, detail=6.0, coord="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for e, (pos, col) in zip(els, stops):
        e.position, e.color = pos, (*col, 1)
    nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
    return r.outputs["Color"], n.outputs["Fac"]


def _bump(nt, b, height_socket, strength):
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = strength
    nt.links.new(height_socket, bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])


def mat(key):
    if key in _MATS:
        return _MATS[key]
    m, nt, b = _pbsdf(key)
    if key == "skin_living":
        col, fac = _noise_ramp(nt, 40, [(0.3, (0.55, 0.38, 0.3)), (0.7, (0.66, 0.47, 0.38))])
        nt.links.new(col, b.inputs["Base Color"])
        b.inputs["Subsurface Weight"].default_value = 0.25
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.25, 0.12)
        b.inputs["Subsurface Scale"].default_value = 0.03
        b.inputs["Roughness"].default_value = 0.42
        _bump(nt, b, fac, 0.08)
    elif key == "skin_drowned":
        # Waterlogged corpse: grey-green base, purple-brown marbling, glossy wet film.
        col, fac = _noise_ramp(nt, 9, [(0.25, (0.33, 0.37, 0.31)), (0.5, (0.47, 0.5, 0.43)),
                                       (0.68, (0.36, 0.28, 0.33)), (0.85, (0.2, 0.24, 0.16))])
        nt.links.new(col, b.inputs["Base Color"])
        b.inputs["Subsurface Weight"].default_value = 0.2
        b.inputs["Subsurface Radius"].default_value = (0.6, 0.5, 0.35)
        b.inputs["Subsurface Scale"].default_value = 0.04
        b.inputs["Roughness"].default_value = 0.35
        b.inputs["Coat Weight"].default_value = 0.8
        b.inputs["Coat Roughness"].default_value = 0.06
        _bump(nt, b, fac, 0.7)
    elif key == "skin_pale":
        col, fac = _noise_ramp(nt, 25, [(0.35, (0.72, 0.72, 0.68)), (0.62, (0.82, 0.8, 0.76)), (0.8, (0.5, 0.55, 0.62))])
        nt.links.new(col, b.inputs["Base Color"])
        b.inputs["Subsurface Weight"].default_value = 0.45
        b.inputs["Subsurface Radius"].default_value = (0.9, 0.5, 0.45)
        b.inputs["Subsurface Scale"].default_value = 0.05
        b.inputs["Roughness"].default_value = 0.5
        _bump(nt, b, fac, 0.6)
    elif key == "flesh_mass":
        col, fac = _noise_ramp(nt, 6, [(0.2, (0.04, 0.05, 0.035)), (0.5, (0.13, 0.14, 0.1)),
                                       (0.7, (0.26, 0.16, 0.18)), (0.9, (0.1, 0.13, 0.07))])
        nt.links.new(col, b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.3
        b.inputs["Coat Weight"].default_value = 0.9
        b.inputs["Coat Roughness"].default_value = 0.05
        b.inputs["Subsurface Weight"].default_value = 0.1
        _bump(nt, b, fac, 1.0)
    elif key == "heart":
        b.inputs["Base Color"].default_value = (0.2, 1.0, 0.6, 1)
        b.inputs["Emission Color"].default_value = (0.25, 1.0, 0.62, 1)
        b.inputs["Emission Strength"].default_value = 10.0
    else:
        flat = {  # base color, roughness, extra
            "jacket": ((0.07, 0.085, 0.06), 0.45, "coat"), "denim": ((0.035, 0.045, 0.08), 0.8, ""),
            "leather": ((0.03, 0.02, 0.015), 0.4, "coat"), "hair_dark": ((0.025, 0.017, 0.012), 0.45, ""),
            "hair_wet": ((0.01, 0.012, 0.01), 0.15, "coat"), "shirt_sodden": ((0.14, 0.16, 0.16), 0.4, "coat"),
            "trousers_sodden": ((0.05, 0.05, 0.06), 0.45, "coat"), "eye_white": ((0.8, 0.78, 0.74), 0.1, "coat"),
            "eye_clouded": ((0.7, 0.74, 0.72), 0.25, ""), "iris": ((0.12, 0.08, 0.04), 0.1, "coat"),
            "mouth": ((0.03, 0.005, 0.006), 0.3, "coat"), "teeth": ((0.62, 0.58, 0.45), 0.35, ""),
            "gunmetal": ((0.03, 0.03, 0.032), 0.3, "metal"), "kelp": ((0.03, 0.07, 0.02), 0.25, "coat"),
            "lips_blue": ((0.22, 0.2, 0.3), 0.3, "coat"),
        }[key]
        b.inputs["Base Color"].default_value = (*flat[0], 1)
        b.inputs["Roughness"].default_value = flat[1]
        if flat[2] == "coat":
            b.inputs["Coat Weight"].default_value = 0.5
        if flat[2] == "metal":
            b.inputs["Metallic"].default_value = 1.0
        if key in ("jacket", "denim"):
            _, fac = _noise_ramp(nt, 180, [(0.4, (0, 0, 0)), (0.6, (1, 1, 1))], detail=2)
            _bump(nt, b, fac, 0.15)
    _MATS[key] = m
    return m


def reset():
    _MATS.clear()


# ───────────────────────────── geometry helpers ─────────────────────────────
def _link(ob, parent):
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    return ob


def skin(name, points, edges, radii, material, parent, subsurf=2, displace=0.0, disp_scale=0.12):
    """Skin-modifier body part. points: list of Vector; radii: list of (x, y)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in points], edges, [])
    ob = _link(bpy.data.objects.new(name, me), parent)
    sk = ob.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.6
    if len(me.skin_vertices) == 0:
        me.skin_vertices.new()
    data = me.skin_vertices[0].data
    for i, r in enumerate(radii):
        data[i].radius = r
    data[0].use_root = True
    sub = ob.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = sub.render_levels = subsurf
    if displace > 0:
        tex = bpy.data.textures.new(name + "_lumps", "CLOUDS")
        tex.noise_scale = disp_scale
        d = ob.modifiers.new("Lumps", "DISPLACE")
        d.texture = tex
        d.strength = displace
        d.mid_level = 0.5
    me.materials.append(mat(material))
    for p in me.polygons:
        p.use_smooth = True
    return ob


def chain(name, pts, rads, material, parent, **kw):
    return skin(name, pts, [(i, i + 1) for i in range(len(pts) - 1)], rads, material, parent, **kw)


def ball(name, center, radius, material, parent, scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=radius)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat(material))
    ob = _link(bpy.data.objects.new(name, me), parent)
    ob.location = center
    ob.scale = scale
    return ob


def rod(name, a, b, radius, material, parent):
    """Straight cylinder from a to b (used for teeth, strands, the pistol)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    d = Vector(b) - Vector(a)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=radius, radius2=radius * 0.6, depth=d.length)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat(material))
    ob = _link(bpy.data.objects.new(name, me), parent)
    ob.location = (Vector(a) + Vector(b)) / 2
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return ob


def root_at(name, pos_g, yaw_deg):
    ob = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = g2b(pos_g)
    ob.rotation_euler = (0, 0, math.radians(yaw_deg))
    return ob


# ───────────────────────────── humanoid skeleton ────────────────────────────
BASE = {
    "pelvis": (0, 0, 0.95), "spine": (0, 0.01, 1.15), "chest": (0, 0.02, 1.36), "neck": (0, 0.02, 1.54),
    "head": (0, 0.03, 1.66), "crown": (0, 0.02, 1.79),
    "l_sh": (-0.19, 0, 1.45), "l_el": (-0.25, 0, 1.17), "l_wr": (-0.27, 0.03, 0.93), "l_hd": (-0.27, 0.05, 0.84),
    "r_sh": (0.19, 0, 1.45), "r_el": (0.25, 0, 1.17), "r_wr": (0.27, 0.03, 0.93), "r_hd": (0.27, 0.05, 0.84),
    "l_hip": (-0.1, 0, 0.93), "l_kn": (-0.11, 0.03, 0.51), "l_an": (-0.11, 0, 0.09), "l_toe": (-0.11, 0.15, 0.03),
    "r_hip": (0.1, 0, 0.93), "r_kn": (0.11, 0.03, 0.51), "r_an": (0.11, 0, 0.09), "r_toe": (0.11, 0.15, 0.03),
}
POSES = {
    "aim": {"head": (0, 0.07, 1.66), "crown": (0, 0.06, 1.79), "neck": (0, 0.04, 1.54),
            "r_sh": (0.18, 0.03, 1.45), "r_el": (0.14, 0.28, 1.37), "r_wr": (0.05, 0.5, 1.42), "r_hd": (0.03, 0.57, 1.43),
            "l_sh": (-0.19, 0.03, 1.45), "l_el": (-0.13, 0.25, 1.32), "l_wr": (-0.01, 0.47, 1.4), "l_hd": (0.01, 0.54, 1.41),
            "l_kn": (-0.15, 0.13, 0.52), "l_an": (-0.16, 0.12, 0.09), "l_toe": (-0.18, 0.27, 0.03),
            "r_kn": (0.13, -0.08, 0.5), "r_an": (0.15, -0.2, 0.09), "r_toe": (0.17, -0.06, 0.03)},
    "shamble": {"pelvis": (0, 0, 0.92), "spine": (0, 0.05, 1.11), "chest": (0, 0.12, 1.31), "neck": (0, 0.18, 1.46),
                "head": (0.05, 0.24, 1.55), "crown": (0.09, 0.26, 1.67),
                "r_sh": (0.21, 0.11, 1.4), "r_el": (0.25, 0.39, 1.3), "r_wr": (0.22, 0.63, 1.27), "r_hd": (0.2, 0.72, 1.26),
                "l_sh": (-0.21, 0.11, 1.4), "l_el": (-0.29, 0.3, 1.18), "l_wr": (-0.31, 0.5, 1.03), "l_hd": (-0.31, 0.57, 0.98),
                "l_kn": (-0.13, 0.2, 0.5), "l_an": (-0.14, 0.12, 0.09), "l_toe": (-0.15, 0.27, 0.03),
                "r_kn": (0.12, -0.1, 0.49), "r_an": (0.14, -0.3, 0.1), "r_toe": (0.15, -0.2, 0.02)},
    "windup": {"pelvis": (0, 0, 0.93), "spine": (0, -0.02, 1.14), "chest": (0, -0.03, 1.36), "neck": (0, 0.0, 1.54),
               "head": (0.03, 0.05, 1.65), "crown": (0.05, 0.02, 1.78),
               "r_sh": (0.21, -0.02, 1.46), "r_el": (0.3, 0.02, 1.72), "r_wr": (0.26, 0.12, 1.96), "r_hd": (0.24, 0.16, 2.04),
               "l_sh": (-0.21, -0.02, 1.46), "l_el": (-0.3, 0.04, 1.73), "l_wr": (-0.25, 0.15, 1.95), "l_hd": (-0.23, 0.19, 2.02)},
}
TORSO = ["pelvis", "spine", "chest", "neck", "head", "crown"]
LIMBS = [["chest", "{s}_sh", "{s}_el", "{s}_wr", "{s}_hd"], ["pelvis", "{s}_hip", "{s}_kn", "{s}_an", "{s}_toe"]]
R_BODY = {"pelvis": (0.15, 0.11), "spine": (0.13, 0.095), "chest": (0.16, 0.105), "neck": (0.05, 0.05),
          "head": (0.085, 0.095), "crown": (0.055, 0.06), "sh": (0.06, 0.06), "el": (0.042, 0.042),
          "wr": (0.032, 0.03), "hd": (0.045, 0.018), "hip": (0.095, 0.095), "kn": (0.06, 0.06),
          "an": (0.043, 0.043), "toe": (0.04, 0.028)}


def joints(pose, scale=1.0):
    j = dict(BASE)
    j.update(POSES.get(pose, {}))
    return {k: Vector(v) * scale for k, v in j.items()}


def _body_graph(j, names, radius_fn):
    """Build one skin graph (torso + limbs) so joints fuse cleanly."""
    idx, pts, rads, edges = {}, [], [], []

    def add(n):
        if n not in idx:
            idx[n] = len(pts)
            pts.append(j[n])
            rads.append(radius_fn(n))
        return idx[n]
    for a, b in zip(names["torso"][:-1], names["torso"][1:]):
        edges.append((add(a), add(b)))
    for limb in names["limbs"]:
        for a, b in zip(limb[:-1], limb[1:]):
            edges.append((add(a), add(b)))
    return pts, edges, rads


def humanoid(name, parent, pose, skin_mat, bloat=1.0, scale=1.0, with_head=True, displace=0.0):
    j = joints(pose, scale)
    limbs = [[p.format(s=s) for p in limb] for s in ("l", "r") for limb in LIMBS]
    torso = TORSO if with_head else TORSO[:4]

    def rad(n):
        key = n.split("_")[-1] if "_" in n else n
        r = R_BODY[key]
        k = bloat if key in ("pelvis", "spine", "chest", "neck", "el", "kn", "hip", "sh") else (1 + (bloat - 1) * 0.5)
        return (r[0] * k * scale, r[1] * k * scale)
    pts, edges, rads = _body_graph(j, {"torso": torso, "limbs": limbs}, rad)
    body = skin(name + "_body", pts, edges, rads, skin_mat, parent, displace=displace)
    return body, j


def clothes(name, parent, j, parts, material, pad=0.018, bloat=1.0):
    """A garment = the same skeleton segments, a little fatter."""
    for seg in parts:
        pts = [j[n] for n in seg]
        rads = []
        for n in seg:
            key = n.split("_")[-1] if "_" in n else n
            r = R_BODY[key]
            rads.append((r[0] * bloat + pad, r[1] * bloat + pad))
        chain(f"{name}_{seg[0]}_{seg[-1]}", pts, rads, material, parent)


def face(parent, j, style, scale=1.0):
    h = j["head"]
    fwd = Vector((0, 1, 0))
    for s in (-1, 1):
        eye = h + Vector((0.032 * s, 0.078, 0.018)) * scale
        if style == "eyeless":
            ball(f"socket{s}", eye - fwd * 0.012, 0.016 * scale, "skin_pale", parent, (1.2, 0.5, 0.7))
            continue
        ball(f"eye{s}", eye, 0.0125 * scale, "eye_clouded" if style == "drowned" else "eye_white", parent)
        if style == "living":
            ball(f"iris{s}", eye + fwd * 0.009 * scale, 0.006 * scale, "iris", parent)
        ball(f"ear{s}", h + Vector((0.083 * s, 0.0, 0.0)) * scale, 0.02 * scale, "skin_drowned" if style == "drowned" else "skin_living", parent, (0.4, 1.0, 1.3))
    ball("nose", h + Vector((0, 0.094, -0.012)) * scale, 0.016 * scale,
         {"living": "skin_living", "drowned": "skin_drowned"}.get(style, "skin_pale"), parent, (0.8, 1.0, 1.3))
    if style == "living":
        ball("mouth", h + Vector((0, 0.083, -0.052)) * scale, 0.02 * scale, "mouth", parent, (1.3, 0.3, 0.25))
    elif style == "drowned":  # slack, open jaw with blue lips
        ball("lips", h + Vector((0, 0.08, -0.06)) * scale, 0.027 * scale, "lips_blue", parent, (1.1, 0.5, 0.9))
        ball("mouth", h + Vector((0, 0.088, -0.062)) * scale, 0.022 * scale, "mouth", parent, (1.0, 0.5, 0.95))
    else:  # eyeless crawler: a wide lipless slit full of teeth
        ball("mouth", h + Vector((0, 0.07, -0.045)) * scale, 0.05 * scale, "mouth", parent, (1.0, 0.45, 0.45))
        for k in range(9):
            x = (k - 4) * 0.011 * scale
            for top in (1, -1):
                base = h + Vector((x, 0.088, -0.045 + 0.016 * top)) * scale
                rod(f"tooth{k}{top}", base, base + Vector((0, 0.004, -0.014 * top)) * scale, 0.0035 * scale, "teeth", parent)


def hair(parent, j, style, rng):
    h, c = j["head"], j["crown"]
    if style == "short":
        ball("hair", h + Vector((0, -0.028, 0.05)), 0.09, "hair_dark", parent, (1.02, 1.05, 0.8))
        ball("hair_back", h + Vector((0, -0.05, 0.0)), 0.085, "hair_dark", parent, (1.0, 0.7, 1.0))
    else:  # long, lank, wet strands hanging over the face (The Ring silhouette)
        for i in range(26):
            a = rng.uniform(-2.6, 2.6)
            start = c + Vector((math.sin(a) * 0.07, math.cos(a) * 0.06, -0.01))
            drop = rng.uniform(0.28, 0.5)
            fwd_bias = 0.1 if abs(a) < 0.9 else 0.02
            pts = [start, start + Vector((math.sin(a) * 0.035, math.cos(a) * 0.05 + fwd_bias, -drop * 0.4)),
                   start + Vector((math.sin(a) * 0.04, math.cos(a) * 0.06 + fwd_bias, -drop))]
            chain(f"strand{i}", pts, [(0.012, 0.004), (0.01, 0.003), (0.004, 0.002)], "hair_wet", parent, subsurf=1)


# ───────────────────────────── the cast ─────────────────────────────────────
def protagonist(pos_g, yaw_deg, pose="aim"):
    root = root_at("protagonist", pos_g, yaw_deg)
    _, j = humanoid("hero", root, pose, "skin_living")
    torso = ["pelvis", "spine", "chest", "neck"]
    arms = [["chest", f"{s}_sh", f"{s}_el", f"{s}_wr"] for s in ("l", "r")]
    clothes("jacket", root, j, [torso] + arms, "jacket", pad=0.03)
    ball("collar", j["neck"] + Vector((0, -0.01, -0.02)), 0.075, "jacket", root, (1.25, 1.1, 0.6))
    legs = [["pelvis", f"{s}_hip", f"{s}_kn", f"{s}_an"] for s in ("l", "r")]
    clothes("jeans", root, j, legs, "denim", pad=0.014)
    clothes("boot", root, j, [[f"{s}_an", f"{s}_toe"] for s in ("l", "r")], "leather", pad=0.022)
    face(root, j, "living")
    hair(root, j, "short", random.Random(1))
    if pose == "aim":  # compact 9 mm in a two-handed grip
        g = (j["r_hd"] + j["l_hd"]) / 2
        rod("slide", g + Vector((0, -0.02, 0.035)), g + Vector((0, 0.17, 0.035)), 0.014, "gunmetal", root)
        rod("grip", g + Vector((0, 0.0, 0.03)), g + Vector((0, -0.02, -0.07)), 0.013, "gunmetal", root)
    return root


def verdronkene(pos_g, yaw_deg, pose="shamble", seed=0, long_hair=False):
    rng = random.Random(seed)
    root = root_at(f"verdronkene_{seed}", pos_g, yaw_deg)
    _, j = humanoid("drowned", root, pose, "skin_drowned", bloat=1.28, displace=0.012)
    torso = ["pelvis", "spine", "chest", "neck"]
    # A sodden shirt, torn open: only the lower torso and one sleeve survive.
    clothes("shirt", root, j, [torso[:3], ["chest", "l_sh", "l_el"]], "shirt_sodden", pad=0.02, bloat=1.28)
    clothes("trousers", root, j, [["pelvis", f"{s}_hip", f"{s}_kn", f"{s}_an"] for s in ("l", "r")], "trousers_sodden", pad=0.016, bloat=1.1)
    face(root, j, "drowned")
    hair(root, j, "long" if long_hair else "short", rng)
    for i in range(10):  # water weed caught on the body
        a = j[rng.choice(["chest", "spine", "l_sh", "r_el", "pelvis"])] + Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.05, 0.12), 0))
        chain(f"weed{i}", [a, a + Vector((rng.uniform(-0.03, 0.03), 0.02, -rng.uniform(0.12, 0.3)))],
              [(0.012, 0.003), (0.006, 0.002)], "kelp", root, subsurf=1)
    return root


def kelderkind(pos_g, yaw_deg, pose="prowl", seed=0):
    root = root_at(f"kelderkind_{seed}", pos_g, yaw_deg)
    rear = 0.12 if pose == "leap" else 0.0
    P = {"pelvis": (0, -0.24, 0.42), "spine": (0, -0.02, 0.46 + rear), "chest": (0, 0.2, 0.5 + rear * 2),
         "neck": (0, 0.36, 0.5 + rear * 2.2), "head": (0, 0.48, 0.47 + rear * 2.3), "crown": (0, 0.56, 0.47 + rear * 2.3)}
    for s, sx in SIDES.items():
        P[f"{s}_sh"] = (0.11 * sx, 0.24, 0.5 + rear * 2)
        P[f"{s}_el"] = (0.29 * sx, 0.28, 0.6 + rear)            # elbows ride high: spider silhouette
        P[f"{s}_wr"] = (0.33 * sx, 0.47, 0.06)
        P[f"{s}_hd"] = (0.35 * sx, 0.55, 0.02)
        P[f"{s}_hip"] = (0.1 * sx, -0.26, 0.42)
        P[f"{s}_kn"] = (0.3 * sx, -0.12, 0.56)
        P[f"{s}_an"] = (0.29 * sx, -0.38, 0.06)
        P[f"{s}_toe"] = (0.35 * sx, -0.3, 0.02)
    j = {k: Vector(v) for k, v in P.items()}
    radii = {"pelvis": (0.1, 0.085), "spine": (0.075, 0.062), "chest": (0.125, 0.1), "neck": (0.042, 0.042),
             "head": (0.085, 0.11), "crown": (0.055, 0.065), "sh": (0.046, 0.046), "el": (0.03, 0.03),
             "wr": (0.02, 0.02), "hd": (0.034, 0.012), "hip": (0.05, 0.05), "kn": (0.032, 0.032),
             "an": (0.018, 0.018), "toe": (0.028, 0.012)}
    limbs = [[p.format(s=s) for p in limb] for s in ("l", "r") for limb in LIMBS]
    pts, edges, rads = _body_graph(j, {"torso": TORSO, "limbs": limbs},
                                   lambda n: radii[n.split("_")[-1] if "_" in n else n])
    skin("crawler_body", pts, edges, rads, "skin_pale", root, displace=0.006, disp_scale=0.05)
    for k in range(9):  # vertebrae ridge
        t = k / 8
        p = j["pelvis"].lerp(j["chest"], t) + Vector((0, 0, 0.07 - abs(t - 0.5) * 0.03))
        ball(f"vertebra{k}", p, 0.018, "skin_pale", root, (0.8, 1.2, 0.7))
    for s, sx in SIDES.items():  # long fingers splayed on the floor
        for f in range(4):
            base = j[f"{s}_hd"]
            a = math.radians(-35 + f * 22) * sx
            rod(f"finger{s}{f}", base, base + Vector((math.sin(a) * 0.15, math.cos(a) * 0.15, -0.01)), 0.006, "skin_pale", root)
    face(root, j, "eyeless")
    return root


def grachtenvorst(pos_g, yaw_deg, pose="stalk", seed=7):
    rng = random.Random(seed)
    root = root_at("grachtenvorst", pos_g, yaw_deg)
    s = 0.86
    raise_arms = pose == "slam"
    core = [Vector((0, 0, 0.25)), Vector((0, 0.02, 0.9)), Vector((0, 0.06, 1.5)), Vector((0, 0.1, 1.95)), Vector((0, 0.12, 2.25))]
    j = {}
    pts = [p * s for p in core]
    rads = [(0.5 * s, 0.42 * s), (0.66 * s, 0.52 * s), (0.7 * s, 0.55 * s), (0.55 * s, 0.45 * s), (0.3 * s, 0.28 * s)]
    edges = [(i, i + 1) for i in range(4)]
    for side in (-1, 1):  # two huge arms
        sh = Vector((0.62 * side, 0.08, 1.85)) * s
        el = Vector((0.95 * side, 0.35, 2.35 if raise_arms else 1.3)) * s
        fist = Vector((0.8 * side, 0.5, 2.7 if raise_arms else 0.55)) * s
        base = len(pts)
        pts += [sh, el, fist]
        rads += [(0.2 * s, 0.2 * s), (0.15 * s, 0.15 * s), (0.27 * s, 0.24 * s)]
        edges += [(2, base), (base, base + 1), (base + 1, base + 2)]
        j[f"fist{side}"] = fist
    skin("mass", pts, edges, rads, "flesh_mass", root, subsurf=3, displace=0.07, disp_scale=0.22)
    # Drowned bodies fused into the mass: half-buried torsos, arms and heads.
    for i in range(7):
        a = rng.uniform(-2.4, 2.4)
        h = rng.uniform(0.5, 1.9) * s
        sub = bpy.data.objects.new(f"fused{i}", None)
        _link(sub, root)
        # Anchor each body's pelvis inside the mass and tilt it outward, so it looks
        # like it's being pulled into (or clawing out of) the flesh.
        sub.location = (math.sin(a) * 0.22 * s, math.cos(a) * 0.18 * s + 0.05, h - 0.95 * 0.72)
        sub.rotation_euler = (rng.uniform(0.5, 1.2) * (1 if math.cos(a) > 0 else -1), rng.uniform(-0.6, 0.6), -a)
        sub.scale = (0.9, 0.9, 0.9)
        humanoid(f"fused{i}", sub, rng.choice(["shamble", "windup", ""]), "skin_drowned", bloat=1.1, scale=0.8,
                 displace=0.01)
        jj = joints("shamble", 0.8)
        face(sub, jj, "drowned", 0.8)
    heart = ball("heart", Vector((0, 0.52, 1.52)) * s, 0.2 * s, "heart", root)
    ball("heart_rim", Vector((0, 0.44, 1.52)) * s, 0.27 * s, "mouth", root, (1.0, 0.4, 1.0))
    light = bpy.data.lights.new("heart_light", "POINT")
    light.color = (0.3, 1.0, 0.65)
    light.energy = 6
    light.shadow_soft_size = 0.15
    lo = _link(bpy.data.objects.new("heart_light", light), root)
    lo.location = Vector((0, 0.8, 1.52)) * s
    for i in range(22):  # kelp and long hair trailing from the whole mass
        a = rng.uniform(-3.0, 3.0)
        top = Vector((math.sin(a) * 0.55, math.cos(a) * 0.45, rng.uniform(1.2, 2.1))) * s
        chain(f"kelp{i}", [top, top + Vector((0, 0.05, -0.4)), top + Vector((rng.uniform(-0.1, 0.1), 0.08, -rng.uniform(0.7, 1.2)))],
              [(0.02, 0.004), (0.016, 0.003), (0.006, 0.002)], "kelp" if i % 3 else "hair_wet", root, subsurf=1)
    return root
