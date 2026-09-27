# damned_waters/tools/blender/enemies_v2.py
# Purpose: build the enemy roster as jointed low/mid-poly models (PS2-era
# budget) and export each to game/assets/characters/enemies/<name>.glb.
# Geometry lives here; surfaces are applied in Godot by material NAME from the
# procedural PBR library (tools/art/materials.py), mapped triplanar (no UVs).
#   python3 tools/blender/enemies_v2.py [--only verdronkene_veiled,...]
# Conventions: Blender Z up, creature faces +Y (== Godot -Z after glTF export).
# Joints are unrotated Empties; mesh parts are parented to the joint they move with.
import math
import random
import sys
from pathlib import Path

import bpy  # must load before bmesh/mathutils when running as the bpy module
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "game" / "assets" / "characters" / "enemies"
MAT_COLORS = {  # viewport fallback colours; Godot swaps in the real materials by name
    "shroud": (0.7, 0.68, 0.6), "skin_drowned": (0.5, 0.55, 0.48), "skin_pale": (0.8, 0.8, 0.78),
    "coat_wet": (0.15, 0.15, 0.16), "rust": (0.45, 0.25, 0.12), "rope": (0.4, 0.35, 0.25),
    "flesh": (0.25, 0.2, 0.18), "waxcoat": (0.05, 0.05, 0.05), "leather": (0.3, 0.2, 0.12),
    "kelp": (0.1, 0.2, 0.05), "void": (0, 0, 0), "teeth": (0.7, 0.66, 0.5), "heart": (0.3, 1, 0.6),
    "tire": (0.03, 0.03, 0.03), "brass": (0.6, 0.45, 0.2), "lens": (0.3, 0.6, 0.5),
    "poncho": (0.8, 0.65, 0.15), "hair_wet": (0.02, 0.02, 0.02), "jacket": (0.12, 0.16, 0.12),
    "denim": (0.1, 0.12, 0.18), "skin": (0.7, 0.55, 0.45), "backpack": (0.15, 0.12, 0.1), "gunmetal": (0.05, 0.05, 0.05),
}
_mats = {}


def mat(name):
    if name not in _mats:
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*MAT_COLORS.get(name, (1, 0, 1)), 1)
        _mats[name] = m
    return _mats[name]


# ───────────────────────────── scene graph ──────────────────────────────────
class Rig:
    """Joints are Empties placed in WORLD coords; parts are built in world
    coords and stored relative to their joint."""

    def __init__(self, name):
        self.name = name
        self.world = {}
        self.nodes = {}
        self.root = self.joint("root", (0, 0, 0), None)

    def joint(self, name, loc, parent="root"):
        e = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(e)
        e.empty_display_size = 0.05
        loc = Vector(loc)
        if parent:
            e.parent = self.nodes[parent]
            e.location = loc - self.world[parent]
        else:
            e.location = loc
        self.world[name], self.nodes[name] = loc, e
        return e

    def part(self, name, joint, bm, material, rot=None, pivot=None):
        """Attach a bmesh (built in world coords) to a joint."""
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(mat(material))
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = self.nodes[joint]
        origin = self.world[joint]
        me.transform(__import__("mathutils").Matrix.Translation(-origin))
        return ob

    def skin(self, name, joint, pts, radii, material, subsurf=2, displace=0.0, dscale=0.2, edges=None):
        me = bpy.data.meshes.new(name)
        origin = self.world[joint]
        me.from_pydata([tuple(Vector(p) - origin) for p in pts],
                       edges or [(i, i + 1) for i in range(len(pts) - 1)], [])
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = self.nodes[joint]
        sk = ob.modifiers.new("Skin", "SKIN")
        sk.use_smooth_shade = True
        if len(me.skin_vertices) == 0:
            me.skin_vertices.new()
        for i, r in enumerate(radii):
            me.skin_vertices[0].data[i].radius = r if isinstance(r, tuple) else (r, r)
        me.skin_vertices[0].data[0].use_root = True
        sub = ob.modifiers.new("Sub", "SUBSURF")
        sub.levels = sub.render_levels = subsurf
        if displace:
            tex = bpy.data.textures.new(name + "_n", "CLOUDS")
            tex.noise_scale = dscale
            d = ob.modifiers.new("Disp", "DISPLACE")
            d.texture, d.strength, d.mid_level = tex, displace, 0.5
        me.materials.append(mat(material))
        return ob


# ───────────────────────────── bmesh builders ───────────────────────────────
def _frame(axis):
    axis = Vector(axis).normalized()
    helper = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(helper).normalized()
    return axis, u, axis.cross(u).normalized()


def add_tube(bm, a, b, r0, r1=None, sides=8):
    """Capped tube segment a->b (rigid parts: bike tubes, spokes, canes, ribs)."""
    a, b = Vector(a), Vector(b)
    axis, u, v = _frame(b - a)
    r1 = r0 if r1 is None else r1
    ring_a, ring_b = [], []
    for i in range(sides):
        t = 2 * math.pi * i / sides
        d = u * math.cos(t) + v * math.sin(t)
        ring_a.append(bm.verts.new(a + d * r0))
        ring_b.append(bm.verts.new(b + d * r1))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((ring_a[i], ring_a[j], ring_b[j], ring_b[i]))
    bm.faces.new(list(reversed(ring_a)))
    bm.faces.new(ring_b)


def add_polyline(bm, pts, r, sides=8):
    for a, b in zip(pts[:-1], pts[1:]):
        add_tube(bm, a, b, r, r, sides)


def add_torus(bm, center, axis, R, r, segs=32, rsegs=6):
    c = Vector(center)
    ax, u, v = _frame(axis)
    rings = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        d = u * math.cos(t) + v * math.sin(t)
        ring = []
        for k in range(rsegs):
            s = 2 * math.pi * k / rsegs
            ring.append(bm.verts.new(c + d * (R + r * math.cos(s)) + ax * (r * math.sin(s))))
        rings.append(ring)
    for i in range(segs):
        a, b = rings[i], rings[(i + 1) % segs]
        for k in range(rsegs):
            m = (k + 1) % rsegs
            bm.faces.new((a[k], a[m], b[m], b[k]))


def add_sphere(bm, center, radii, segs=16, rings=10, bump=None, uv=False, mirror_z=False):
    """UV ellipsoid; bump(direction)->radial offset in metres (face impressions).
    uv=True writes equirect UVs from the direction (u = 0.5 + theta/2pi, v = 0.5 + phi/pi),
    matching the painted textures in tools/art/materials.py."""
    c = Vector(center)
    verts = []
    dirs = {}
    for i in range(rings + 1):
        phi = math.pi * i / rings
        row = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            d = Vector((math.sin(phi) * math.sin(th), math.sin(phi) * math.cos(th), math.cos(phi)))
            off = bump(d) if bump else 0.0
            p = Vector((d.x * (radii[0] + off), d.y * (radii[1] + off), d.z * (radii[2] + off)))
            if mirror_z:
                p.z = -p.z
            vert = bm.verts.new(c + p)
            dirs[vert] = d
            row.append(vert)
        verts.append(row)
    for i in range(rings):
        for j in range(segs):
            k = (j + 1) % segs
            a, b, cc, dd = verts[i][j], verts[i][k], verts[i + 1][k], verts[i + 1][j]
            if i == 0:
                bm.faces.new((a, cc, dd)) if a != cc else None
            elif i == rings - 1:
                bm.faces.new((a, b, dd))
            else:
                bm.faces.new((a, b, cc, dd))
    if uv:
        layer = bm.loops.layers.uv.verify()
        for f in bm.faces:
            us = []
            for loop in f.loops:
                d = dirs.get(loop.vert, Vector((0, 1, 0)))
                us.append([0.5 + math.atan2(d.x, d.y) / (2 * math.pi), 0.5 + math.asin(max(-1, min(1, d.z))) / math.pi])
            if max(u[0] for u in us) - min(u[0] for u in us) > 0.5:  # face straddles the back seam
                for u in us:
                    u[0] += 1.0 if u[0] < 0.5 else 0.0
            for loop, u in zip(f.loops, us):
                loop[layer].uv = u
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)


def bake_ao(distance=0.35, samples=24):
    """Crevice shadow baked into vertex colours (Cycles). Armpits, fingers, folds and
    the underside of coats darken, which is most of what stops a model looking like clay."""
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.light_settings.distance = distance
    sc.render.bake.target = "VERTEX_COLORS"
    meshes = [o for o in sc.objects if o.type == "MESH" and len(o.data.vertices) > 0]
    for o in meshes:
        ca = o.data.color_attributes.get("AO") or o.data.color_attributes.new("AO", "BYTE_COLOR", "CORNER")
        o.data.color_attributes.active_color = ca
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.bake(type="AO")
    import numpy as np
    for o in meshes:  # remap: keep it a shadow, never black
        ca = o.data.color_attributes["AO"]
        buf = np.empty(len(ca.data) * 4, dtype=np.float32)
        ca.data.foreach_get("color", buf)
        buf = buf.reshape(-1, 4)
        buf[:, :3] = 0.28 + 0.72 * np.power(np.clip(buf[:, :3], 0, 1), 0.85)
        ca.data.foreach_set("color", buf.ravel())


def gltf_export(path):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in bpy.context.scene.objects:
        ob.select_set(True)
    kw = dict(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
              export_materials="EXPORT", export_apply=False, export_skins=True)
    try:
        bpy.ops.export_scene.gltf(**kw, export_vertex_color="ACTIVE")
    except TypeError:
        bpy.ops.export_scene.gltf(**kw, export_colors=True)


def add_drape(bm, top, top_r, length, bottom_r, folds=7, fold_amp=0.025, rings=9, segs=28,
              hem=lambda th: 1.0, rng=None, flare_front=1.0):
    """Hanging cloth tube (open both ends): coats, veils, cloaks. hem(theta) scales
    the length per direction (theta 0 = front)."""
    rng = rng or random.Random(0)
    top = Vector(top)
    phase = [rng.uniform(0, 6.28) for _ in range(3)]
    grid = []
    for i in range(rings + 1):
        t = i / rings
        row = []
        for j in range(segs):
            th = 2 * math.pi * j / segs
            L = length * hem(th)
            ease = t ** 0.8
            rx = top_r[0] + (bottom_r[0] - top_r[0]) * ease
            ry = top_r[1] + (bottom_r[1] - top_r[1]) * ease * (flare_front if math.cos(th) > 0 else 1)
            fold = 1 + fold_amp * t * 8 * (math.sin(th * folds + phase[0]) * 0.6 + math.sin(th * folds * 2.3 + phase[1]) * 0.4)
            z = top.z - t * L + (rng.uniform(-0.02, 0.02) if i == rings else 0)
            row.append(bm.verts.new((top.x + math.sin(th) * rx * fold, top.y + math.cos(th) * ry * fold, z)))
        grid.append(row)
    for i in range(rings):
        for j in range(segs):
            k = (j + 1) % segs
            bm.faces.new((grid[i][j], grid[i][k], grid[i + 1][k], grid[i + 1][j]))


def face_impression(style="veil"):
    """Radial offsets that press a face into a sheet pulled over a skull."""
    feats = [((0, 1, -0.05), 0.13, 0.03), ((0, 0.95, 0.24), 0.2, 0.012),
             ((0.33, 0.9, 0.1), 0.13, -0.016), ((-0.33, 0.9, 0.1), 0.13, -0.016),
             ((0.55, 0.78, -0.08), 0.18, 0.01), ((-0.55, 0.78, -0.08), 0.18, 0.01),
             ((0, 0.92, -0.38), 0.12, -0.028), ((0, 0.8, -0.62), 0.16, 0.018)]
    feats = [(Vector(d).normalized(), s, a) for d, s, a in feats]

    def bump(d):
        return sum(a * math.exp(-((d - fd).length ** 2) / (2 * s * s)) for fd, s, a in feats)
    return bump


def veiled_head(rig, joint, center, scale=1.0, material="shroud", veil_len=0.42, rng=None, name="head"):
    """A skull under a wet sheet, the sheet then hanging to the shoulders/back."""
    c = Vector(center)
    bm = bmesh.new()
    add_sphere(bm, c, (0.098 * scale, 0.112 * scale, 0.125 * scale), 32, 20, face_impression())
    rig.part(f"{name}_veil_face", joint, bm, material)
    bm = bmesh.new()  # the dark hole where the mouth drags the cloth in
    add_sphere(bm, c + Vector((0, 0.1, -0.05)) * scale, (0.018 * scale, 0.012 * scale, 0.012 * scale), 10, 6)
    rig.part(f"{name}_mouth", joint, bm, "void")
    bm = bmesh.new()
    add_drape(bm, c + Vector((0, -0.01, 0.02)) * scale, (0.105 * scale, 0.12 * scale), veil_len * scale,
              (0.24 * scale, 0.2 * scale), folds=9, fold_amp=0.03, rings=8, segs=32,
              hem=lambda th: 0.35 + 0.65 * (1 - math.cos(th)) / 2, rng=rng)
    ob = rig.part(f"{name}_veil_drape", joint, bm, material)
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.006


def long_hand(rig, joint, wrist, direction, material, length=0.13, splay=0.5, curl=0.25, scale=1.0):
    w, d = Vector(wrist), Vector(direction).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 0.1:
        side = Vector((1, 0, 0))
    side.normalize()
    palm = w + d * 0.05 * scale
    bm = bmesh.new()
    add_sphere(bm, palm, (0.04 * scale, 0.045 * scale, 0.02 * scale), 10, 6)
    rig.part(f"palm_{joint}", joint, bm, material)
    for f in range(4):
        base = palm + side * (f - 1.5) * 0.018 * scale + d * 0.035 * scale
        fd = (d + side * (f - 1.5) * splay * 0.3).normalized()
        p1 = base + fd * length * 0.45 * scale
        p2 = p1 + (fd - Vector((0, 0, curl))).normalized() * length * 0.35 * scale
        p3 = p2 + (fd - Vector((0, 0, curl * 2))).normalized() * length * 0.25 * scale
        rig.skin(f"finger_{joint}_{f}", joint, [base, p1, p2, p3], [0.009 * scale, 0.008 * scale, 0.007 * scale, 0.004 * scale],
                 material, subsurf=1)


def wheel(rig, joint, center, axis, R=0.33, spokes=24, name="wheel"):
    c = Vector(center)
    bm = bmesh.new()
    add_torus(bm, c, axis, R, 0.012, 40, 5)
    ax, u, v = _frame(axis)
    for i in range(spokes):
        t = 2 * math.pi * i / spokes
        d = u * math.cos(t) + v * math.sin(t)
        off = ax * (0.018 if i % 2 else -0.018)
        add_tube(bm, c + off, c + d * (R - 0.01), 0.0022, 0.0022, 3)
    add_tube(bm, c - ax * 0.05, c + ax * 0.05, 0.02, 0.02, 8)
    rig.part(f"{name}_rim", joint, bm, "rust")
    bm = bmesh.new()
    add_torus(bm, c, axis, R + 0.02, 0.022, 40, 6)
    rig.part(f"{name}_tire", joint, bm, "tire")


# ───────────────────────────── the roster ───────────────────────────────────
def verdronkene(variant="veiled", seed=1):
    rng = random.Random(seed)
    rig = Rig(f"verdronkene_{variant}")
    J = rig.joint
    J("pelvis", (0, 0, 0.95))
    J("spine", (0, 0.01, 1.12), "pelvis")
    J("neck", (0, 0.05, 1.5), "spine")
    for s, x in (("l", -1), ("r", 1)):
        J(f"shoulder_{s}", (0.24 * x, 0.02, 1.42), "spine")
        J(f"elbow_{s}", (0.29 * x, 0.06, 1.14), f"shoulder_{s}")
        J(f"hip_{s}", (0.1 * x, 0, 0.93), "pelvis")
        J(f"knee_{s}", (0.11 * x, 0.03, 0.5), f"hip_{s}")
    # Bloated torso in a waterlogged overcoat, coat skirt hanging to the knees.
    rig.skin("torso", "spine", [(0, 0, 0.9), (0, 0.02, 1.13), (0, 0.04, 1.36), (0, 0.05, 1.5)],
             [(0.2, 0.16), (0.23, 0.19), (0.23, 0.16), (0.075, 0.075)], "coat_wet", displace=0.015)
    bm = bmesh.new()
    add_drape(bm, (0, 0.01, 1.02), (0.21, 0.18), 0.55, (0.3, 0.27), folds=6, fold_amp=0.02, rng=rng,
              hem=lambda th: 1.0 - 0.15 * math.cos(th))
    ob = rig.part("coat_skirt", "pelvis", bm, "coat_wet")
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.012
    veiled_head(rig, "neck", (0, 0.07, 1.63), 1.0, rng=rng)
    for s, x in (("l", -1), ("r", 1)):
        rig.skin(f"upper_arm_{s}", f"shoulder_{s}", [rig.world[f"shoulder_{s}"], rig.world[f"elbow_{s}"]],
                 [0.08, 0.068], "coat_wet")
        wrist = rig.world[f"elbow_{s}"] + Vector((0.02 * x, 0.04, -0.27))
        rig.skin(f"forearm_{s}", f"elbow_{s}", [rig.world[f"elbow_{s}"], wrist], [0.066, 0.05], "coat_wet")
        rig.skin(f"wrist_{s}", f"elbow_{s}", [wrist + Vector((0, 0, 0.03)), wrist], [0.035, 0.03], "skin_drowned", subsurf=1)
        long_hand(rig, f"elbow_{s}", wrist, (0.1 * x, 0.2, -1), "skin_drowned", 0.14)
        rig.skin(f"thigh_{s}", f"hip_{s}", [rig.world[f"hip_{s}"], rig.world[f"knee_{s}"]], [0.095, 0.07], "coat_wet")
        ankle = rig.world[f"knee_{s}"] + Vector((0, -0.02, -0.42))
        rig.skin(f"shin_{s}", f"knee_{s}", [rig.world[f"knee_{s}"], ankle], [0.068, 0.05], "coat_wet")
        bm = bmesh.new()  # bare, swollen feet
        add_sphere(bm, ankle + Vector((0, 0.06, -0.04)), (0.05, 0.11, 0.04), 12, 8)
        rig.part(f"foot_{s}", f"knee_{s}", bm, "skin_drowned")
    if variant == "netted":  # bound in a fishing net: cords spiral round the body, pinning the left arm
        bm = bmesh.new()
        for k in range(14):
            a0 = k * 2 * math.pi / 14
            pts = []
            for t in range(13):
                a = a0 + t * 0.45 * (1 if k % 2 else -1)
                z = 0.9 + t * 0.05
                pts.append((math.sin(a) * 0.3, math.cos(a) * 0.23 + 0.02, z))
            add_polyline(bm, pts, 0.006, 4)
        rig.part("net", "spine", bm, "rope")
    for i in range(8):  # kelp caught on the body
        a = rng.uniform(-2.8, 2.8)
        top = Vector((math.sin(a) * 0.22, math.cos(a) * 0.18, rng.uniform(1.0, 1.4)))
        rig.skin(f"weed_{i}", "spine", [top, top + Vector((0, 0.03, -0.25)), top + Vector((rng.uniform(-0.05, 0.05), 0.04, -0.45))],
                 [(0.02, 0.004), (0.015, 0.003), (0.004, 0.002)], "kelp", subsurf=1)
    return rig


def kelderkind(seed=2):
    rng = random.Random(seed)
    rig = Rig("kelderkind")
    J = rig.joint
    J("body", (0, 0, 0.56))
    J("neck", (0, 0.3, 0.55), "body")
    for s, x in (("l", -1), ("r", 1)):
        J(f"shoulder_{s}", (0.14 * x, 0.24, 0.56), "body")
        J(f"elbow_{s}", (0.29 * x, 0.34, 0.66), f"shoulder_{s}")
        J(f"hip_{s}", (0.12 * x, -0.3, 0.52), "body")
        J(f"knee_{s}", (0.29 * x, -0.22, 0.72), f"hip_{s}")
    # Arched belly-up torso: ribs pressed through thin skin.
    rig.skin("torso", "body", [(0, -0.32, 0.5), (0, -0.08, 0.6), (0, 0.18, 0.6), (0, 0.3, 0.55)],
             [(0.13, 0.1), (0.1, 0.085), (0.15, 0.12), (0.06, 0.06)], "skin_pale", displace=0.006, dscale=0.05)
    bm = bmesh.new()
    for k in range(6):  # ribs arc over the chest (which faces the ceiling)
        y = 0.06 + k * 0.035
        pts = [(math.sin(a) * 0.12, y, 0.6 + math.cos(a) * 0.05) for a in [(-1.3 + t * 0.325) for t in range(9)]]
        add_polyline(bm, pts, 0.007, 5)
    rig.part("ribs", "body", bm, "skin_pale")
    # The head hangs upside down under the chest, face forward, mouth where the brow should be.
    hc = Vector((0, 0.4, 0.4))
    bm = bmesh.new()

    def eyeless(d):
        # smooth skin over the eyes, mouth split low (which is HIGH when inverted)
        return 0.018 * math.exp(-((d - Vector((0, 0.9, -0.1)).normalized()).length ** 2) / 0.05) \
            - 0.01 * math.exp(-((d - Vector((0.3, 0.9, 0.12)).normalized()).length ** 2) / 0.02) \
            - 0.01 * math.exp(-((d - Vector((-0.3, 0.9, 0.12)).normalized()).length ** 2) / 0.02)
    add_sphere(bm, (0, 0, 0), (0.078, 0.092, 0.1), 24, 16, eyeless)
    for v in bm.verts:  # flip upside down, then place
        v.co = Vector((v.co.x, v.co.y, -v.co.z)) + hc
    rig.part("head", "neck", bm, "skin_pale")
    bm = bmesh.new()
    add_sphere(bm, hc + Vector((0, 0.085, 0.05)), (0.045, 0.02, 0.012), 12, 6)
    rig.part("mouth", "neck", bm, "void")
    bm = bmesh.new()
    for k in range(9):
        x = (k - 4) * 0.009
        for up in (1, -1):
            base = hc + Vector((x, 0.098, 0.05 + 0.012 * up))
            add_tube(bm, base, base + Vector((0, 0.003, -0.012 * up)), 0.003, 0.0005, 4)
    rig.part("teeth", "neck", bm, "teeth")
    for i in range(18):  # wet hair hanging from the inverted scalp to the floor
        a = rng.uniform(0, 2 * math.pi)
        root = hc + Vector((math.sin(a) * 0.07, -0.02 + math.cos(a) * 0.06, -0.08))
        end = Vector((root.x + rng.uniform(-0.06, 0.06), root.y + rng.uniform(-0.02, 0.08), 0.0))
        rig.skin(f"hair_{i}", "neck", [root, root.lerp(end, 0.5) + Vector((0, 0.02, 0)), end],
                 [0.006, 0.005, 0.003], "hair_wet", subsurf=1)
    for s, x in (("l", -1), ("r", 1)):
        sh, el = rig.world[f"shoulder_{s}"], rig.world[f"elbow_{s}"]
        wrist = Vector((0.31 * x, 0.5, 0.05))
        rig.skin(f"upper_arm_{s}", f"shoulder_{s}", [sh, el], [0.04, 0.028], "skin_pale")
        rig.skin(f"forearm_{s}", f"elbow_{s}", [el, wrist], [0.028, 0.02], "skin_pale")
        long_hand(rig, f"elbow_{s}", wrist, (0.2 * x, 1, -0.05), "skin_pale", 0.16, curl=0.05)
        hp, kn = rig.world[f"hip_{s}"], rig.world[f"knee_{s}"]
        ankle = Vector((0.28 * x, -0.44, 0.05))
        rig.skin(f"thigh_{s}", f"hip_{s}", [hp, kn], [0.05, 0.03], "skin_pale")
        rig.skin(f"shin_{s}", f"knee_{s}", [kn, ankle], [0.03, 0.022], "skin_pale")
        long_hand(rig, f"knee_{s}", ankle, (0.1 * x, -1, -0.05), "skin_pale", 0.1, curl=0.05)
    return rig


def grachtenvorst(seed=7):
    rng = random.Random(seed)
    rig = Rig("grachtenvorst")
    J = rig.joint
    J("body", (0, 0, 0))
    J("heart", (0, 0.46, 1.42), "body")
    for s, x in (("l", -1), ("r", 1)):
        J(f"shoulder_{s}", (0.72 * x, 0.1, 1.8), "body")
        J(f"elbow_{s}", (1.0 * x, 0.35, 1.2), f"shoulder_{s}")
    rig.skin("mass", "body", [(0, 0, 0.15), (0, 0.02, 0.8), (0, 0.06, 1.4), (0, 0.1, 1.85), (0, 0.14, 2.15)],
             [(0.55, 0.45), (0.7, 0.56), (0.72, 0.56), (0.56, 0.46), (0.3, 0.28)], "flesh", subsurf=3, displace=0.09, dscale=0.25)
    # Veiled drowned fused into the flesh: shrouded heads and reaching arms.
    for i, (a, h) in enumerate([(-0.9, 1.7), (0.7, 1.55), (-0.3, 1.05), (1.2, 0.95), (-1.4, 1.15), (0.2, 2.0)]):
        c = Vector((math.sin(a) * 0.62, math.cos(a) * 0.5 + 0.05, h))
        veiled_head(rig, "body", c, 0.85, veil_len=0.25, rng=rng, name=f"fused{i}")
        arm_dir = Vector((math.sin(a), math.cos(a), rng.uniform(-0.3, 0.4))).normalized()
        base = c + Vector((0, 0, -0.2))
        tip = base + arm_dir * 0.38 + Vector((0, 0, rng.uniform(-0.2, 0.1)))
        rig.skin(f"fused_arm{i}", "body", [base, base.lerp(tip, 0.5), tip], [0.055, 0.045, 0.035], "skin_drowned")
        long_hand(rig, "body", tip, arm_dir, "skin_drowned", 0.13)
    # Canal bicycles grown into its back: a halo of wheels and broken frames.
    for i, (a, h, tilt) in enumerate([(-2.5, 1.9, 0.4), (2.6, 1.7, -0.5), (3.1, 2.25, 0.1)]):
        c = Vector((math.sin(a) * 0.55, math.cos(a) * 0.45, h))
        J(f"wheel_{i}", c, "body")
        wheel(rig, f"wheel_{i}", c, (math.cos(a) + tilt, -math.sin(a), 0.3), 0.32, name=f"wheel_{i}")
    bm = bmesh.new()
    for i in range(7):  # frame tubes jutting like broken ribs/spines
        a = rng.uniform(1.8, 4.5)
        base = Vector((math.sin(a) * 0.5, math.cos(a) * 0.4, rng.uniform(0.9, 2.0)))
        tip = base + Vector((math.sin(a) * rng.uniform(0.3, 0.6), math.cos(a) * rng.uniform(0.3, 0.6), rng.uniform(-0.1, 0.4)))
        add_tube(bm, base, tip, 0.02, 0.018, 8)
    # Ribcage of bent frame tubes around the heart.
    hc = rig.world["heart"]
    for k in range(6):
        a = -1.0 + k * 0.4
        pts = [hc + Vector((math.sin(a) * r, 0.08 + math.cos(a) * 0.06, z)) for r, z in ((0.14, 0.26), (0.26, 0.05), (0.2, -0.18), (0.08, -0.3))]
        add_polyline(bm, pts, 0.014, 6)
    rig.part("frames", "body", bm, "rust")
    bm = bmesh.new()
    add_sphere(bm, hc, (0.17, 0.14, 0.2), 16, 10)
    rig.part("heart_core", "heart", bm, "heart")
    bm = bmesh.new()  # mooring rope wound round the mass
    pts = [Vector((math.sin(t) * (0.74 - 0.12 * abs(math.sin(t * 0.3))), math.cos(t) * 0.6, 0.35 + t * 0.07)) for t in [i * 0.35 for i in range(58)]]
    add_polyline(bm, pts, 0.028, 6)
    rig.part("rope", "body", bm, "rope")
    for s, x in (("l", -1), ("r", 1)):
        sh, el = rig.world[f"shoulder_{s}"], rig.world[f"elbow_{s}"]
        fist = Vector((0.92 * x, 0.62, 0.55))
        # One continuous club arm (no elbow seam); it swings from the shoulder.
        rig.skin(f"arm_{s}", f"shoulder_{s}", [sh, el, el.lerp(fist, 0.6), fist],
                 [(0.2, 0.18), (0.15, 0.14), (0.17, 0.16), (0.26, 0.23)], "flesh", displace=0.04)
        bm = bmesh.new()  # a bicycle sprocket fused into each fist: a grinding knuckle
        add_torus(bm, fist + Vector((0, 0.12, 0)), (1, 0, 0), 0.19, 0.018, 36, 5)
        for k in range(24):
            t = 2 * math.pi * k / 24
            d = Vector((0, math.cos(t), math.sin(t)))
            p = fist + Vector((0, 0.12, 0)) + d * 0.21
            add_tube(bm, p - d * 0.01, p + d * 0.035, 0.012, 0.004, 4)
        add_torus(bm, el.lerp(fist, 0.55), (fist - el), 0.2, 0.03, 24, 6)  # a tyre stretched round the forearm
        rig.part(f"sprocket_{s}", f"shoulder_{s}", bm, "rust")
    for i in range(20):
        a = rng.uniform(-3.1, 3.1)
        top = Vector((math.sin(a) * 0.6, math.cos(a) * 0.5, rng.uniform(0.9, 2.0)))
        rig.skin(f"kelp_{i}", "body", [top, top + Vector((0, 0.05, -0.4)), top + Vector((rng.uniform(-0.1, 0.1), 0.08, -rng.uniform(0.7, 1.1)))],
                 [(0.025, 0.005), (0.02, 0.004), (0.006, 0.002)], "kelp", subsurf=1)
    return rig


def pestmeester(seed=4):
    """The Plague Master. 2.35 m, hunched, the head craned forward on a neck too long;
    arms that hang past its knees; a tattered oilcloth coat dragging on the floor.
    The mask is stitched, cracked leather; the beak hangs open over HUMAN teeth;
    a real, bloodshot eye is pressed against the cracked left lens."""
    rng = random.Random(seed)
    rig = Rig("pestmeester")
    J = rig.joint
    J("body", (0, 0, 0))
    J("spine", (0, 0, 1.2), "body")
    J("neck", (0, 0.2, 1.86), "spine")
    for s_, x in (("l", -1), ("r", 1)):
        J(f"shoulder_{s_}", (0.27 * x, 0.1, 1.74), "spine")
    # Hunched torso with a hump under the cape.
    rig.skin("torso", "spine", [(0, 0, 1.15), (0, 0.04, 1.45), (0, 0.1, 1.72), (0, 0.18, 1.84)],
             [(0.2, 0.15), (0.24, 0.17), (0.26, 0.19), (0.07, 0.07)], "canvas_black", displace=0.01)
    bm = bmesh.new()
    add_sphere(bm, (0, -0.1, 1.68), (0.2, 0.14, 0.16), 16, 10)
    rig.part("hump", "spine", bm, "canvas_black")
    # Floor-length coat whose hem has rotted into dragging strips.
    bm = bmesh.new()
    add_drape(bm, (0, 0.04, 1.62), (0.22, 0.17), 1.28, (0.44, 0.38), folds=9, fold_amp=0.03, rings=12, segs=40, rng=rng)
    for k in range(34):  # tatters
        th = 2 * math.pi * k / 34 + rng.uniform(-0.05, 0.05)
        top = Vector((math.sin(th) * 0.45, 0.04 + math.cos(th) * 0.39, 0.36))
        w = rng.uniform(0.03, 0.06)
        side = Vector((math.cos(th), -math.sin(th), 0)) * w
        bot_z = rng.uniform(-0.02, 0.1)
        vs = [bm.verts.new(top - side), bm.verts.new(top + side),
              bm.verts.new(Vector((top.x * 1.05, top.y * 1.05, bot_z)) + side * 0.6),
              bm.verts.new(Vector((top.x * 1.05, top.y * 1.05, bot_z)) - side * 0.6)]
        bm.faces.new(vs)
    ob = rig.part("coat", "spine", bm, "canvas_black")
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.012
    bm = bmesh.new()  # short tattered cape over the hump and shoulders
    add_drape(bm, (0, 0.12, 1.84), (0.12, 0.12), 0.55, (0.42, 0.36), folds=11, fold_amp=0.035, rings=7, segs=40,
              hem=lambda th: 0.75 + 0.25 * abs(math.sin(th * 6.0)), rng=rng)
    ob = rig.part("cape", "spine", bm, "canvas_black")
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.01
    rig.skin("collar", "neck", [(0, 0.16, 1.8), (0, 0.22, 1.92)], [(0.09, 0.08), (0.075, 0.07)], "leather")
    # The mask: cracked leather, stitched down the middle, riveted.
    head = Vector((0, 0.26, 1.97))
    bm = bmesh.new()
    add_sphere(bm, head, (0.1, 0.115, 0.125), 24, 14)
    rig.part("mask", "neck", bm, "leather")
    bm = bmesh.new()
    add_polyline(bm, [head + Vector((0, math.cos(a) * 0.118, math.sin(a) * 0.128)) for a in [0.3 + i * 0.25 for i in range(9)]], 0.004, 4)
    for sx in (-1, 1):
        add_polyline(bm, [head + Vector((sx * math.sin(a) * 0.102, math.cos(a) * 0.1, 0.05 - a * 0.08)) for a in [0.2 + i * 0.2 for i in range(7)]], 0.003, 4)
    rig.part("stitches", "neck", bm, "rope")
    bm = bmesh.new()
    for a in range(10):
        t = a / 10 * 2 * math.pi
        add_sphere(bm, head + Vector((math.sin(t) * 0.1, math.cos(t) * 0.02 - 0.02, -0.06 + math.cos(t) * 0.01)), (0.007, 0.007, 0.007), 6, 4)
    rig.part("rivets", "neck", bm, "brass")
    # Beak: long, curved down, bound with twine; the lower half hangs open.
    rig.skin("beak_upper", "neck", [head + Vector((0, 0.09, -0.015)), head + Vector((0, 0.24, -0.05)), head + Vector((0, 0.38, -0.12)), head + Vector((0, 0.5, -0.24))],
             [(0.065, 0.045), (0.05, 0.034), (0.03, 0.022), (0.005, 0.004)], "leather")
    rig.skin("beak_lower", "neck", [head + Vector((0, 0.09, -0.075)), head + Vector((0, 0.19, -0.16)), head + Vector((0, 0.28, -0.25))],
             [(0.05, 0.022), (0.034, 0.016), (0.008, 0.005)], "leather")
    bm = bmesh.new()
    for k in range(3):
        c = head + Vector((0, 0.15 + k * 0.05, -0.035 - k * 0.012))
        add_torus(bm, c, (0, 1, -0.2), 0.052 - k * 0.006, 0.004, 16, 4)
    rig.part("twine", "neck", bm, "rope")
    bm = bmesh.new()  # inside the beak: a human mouth
    add_sphere(bm, head + Vector((0, 0.12, -0.075)), (0.045, 0.05, 0.03), 12, 8)
    rig.part("maw", "neck", bm, "void")
    bm = bmesh.new()
    for k in range(10):
        xx = (k - 4.5) * 0.008
        for up in (1, -1):
            base = head + Vector((xx, 0.105 + abs(xx) * -0.4, -0.06 if up > 0 else -0.095))
            add_tube(bm, base, base + Vector((0, 0.002, -0.011 * up)), 0.0035, 0.002, 4)
    rig.part("teeth", "neck", bm, "teeth")
    rig.skin("tongue", "neck", [head + Vector((0, 0.1, -0.085)), head + Vector((0, 0.19, -0.13)), head + Vector((0, 0.24, -0.2))],
             [0.02, 0.014, 0.007], "flesh_raw", subsurf=1)
    # Lenses: brass rims; the left one cracked, a bloodshot human eye pressed behind it.
    bm = bmesh.new()
    for x in (-1, 1):
        add_torus(bm, head + Vector((0.047 * x, 0.1, 0.02)), (0.3 * x, 1, 0), 0.03, 0.008, 16, 5)
    rig.part("lens_rims", "neck", bm, "brass")
    bm = bmesh.new()
    add_sphere(bm, head + Vector((-0.047, 0.098, 0.02)), (0.029, 0.022, 0.029), 20, 12, uv=True)
    rig.part("eye", "neck", bm, "eye_bloodshot")
    bm = bmesh.new()
    add_sphere(bm, head + Vector((0.047, 0.108, 0.02)), (0.027, 0.006, 0.027), 12, 6)
    rig.part("lens_dark", "neck", bm, "lens")
    bm = bmesh.new()
    for k in range(4):  # cracks across the left glass
        a = rng.uniform(0, math.pi)
        p0 = head + Vector((-0.047, 0.121, 0.02))
        add_tube(bm, p0 + Vector((math.cos(a) * 0.026, 0, math.sin(a) * 0.026)), p0 - Vector((math.cos(a) * 0.022, 0, math.sin(a) * 0.022)), 0.0012, 0.0012, 3)
    rig.part("cracks", "neck", bm, "bone")
    bm = bmesh.new()  # warped wide-brimmed hat
    add_torus(bm, head + Vector((0, -0.01, 0.12)), (0, 0.15, 1), 0.21, 0.1, 36, 4)
    add_tube(bm, head + Vector((0, -0.01, 0.1)), head + Vector((0, -0.03, 0.34)), 0.12, 0.1, 20)
    rig.part("hat", "neck", bm, "canvas_black")
    for s_, x in (("l", -1), ("r", 1)):
        sh = rig.world[f"shoulder_{s_}"]
        el, wr = sh + Vector((0.07 * x, 0.08, -0.44)), sh + Vector((0.1 * x, 0.2, -0.95))
        rig.skin(f"sleeve_{s_}", f"shoulder_{s_}", [sh, el, wr + Vector((0, 0, 0.06))], [0.08, 0.06, 0.055], "canvas_black")
        rig.skin(f"glove_{s_}", f"shoulder_{s_}", [wr + Vector((0, 0, 0.07)), wr], [0.045, 0.042], "leather")
        long_hand(rig, f"shoulder_{s_}", wr, (0.1 * x, 0.35, -1), "leather", 0.2, curl=0.35)
        bm = bmesh.new()  # glove fingertips torn open: grey claws
        for f in range(4):
            tip = wr + Vector(((f - 1.5) * 0.018 * x, 0.07, -0.21))
            add_tube(bm, tip, tip + Vector((0, 0.03, -0.04)), 0.007, 0.001, 5)
        rig.part(f"claws_{s_}", f"shoulder_{s_}", bm, "skin_drowned")
    # Gnarled cane crowned with a bird skull; a bell hangs under it.
    wr = rig.world["shoulder_r"] + Vector((0.1, 0.2, -0.95))
    pts = [Vector((wr.x + 0.02, wr.y + 0.05 + t * 0.2, 1.05 - t * 1.05)) + Vector((rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012), 0)) for t in [i / 8 for i in range(9)]]
    bm = bmesh.new()
    add_polyline(bm, pts, 0.013, 7)
    rig.part("cane", "shoulder_r", bm, "leather")
    bm = bmesh.new()
    add_sphere(bm, pts[0] + Vector((0, 0.02, 0.06)), (0.03, 0.045, 0.028), 12, 8)
    add_tube(bm, pts[0] + Vector((0, 0.06, 0.055)), pts[0] + Vector((0, 0.14, 0.035)), 0.012, 0.002, 6)
    rig.part("skull", "shoulder_r", bm, "bone")
    bm = bmesh.new()
    add_sphere(bm, pts[0] + Vector((0, 0.0, -0.03)), (0.025, 0.025, 0.03), 10, 8)
    rig.part("bell", "shoulder_r", bm, "brass")
    bm = bmesh.new()  # belt of glass vials and dead herbs
    for k in range(5):
        a = -0.7 + k * 0.35
        p = Vector((math.sin(a) * 0.25, 0.06 + math.cos(a) * 0.2, 1.18))
        add_tube(bm, p, p + Vector((0, 0, -0.08)), 0.012, 0.012, 6)
    rig.part("vials", "spine", bm, "lens")
    return rig


def fietser(seed=5):
    rng = random.Random(seed)
    rig = Rig("fietser")
    J = rig.joint
    J("frame", (0, 0, 0))
    J("wheel_rear", (0, -0.56, 0.36), "frame")
    J("wheel_front", (0, 0.58, 0.36), "frame")
    J("crank", (0, -0.02, 0.3), "frame")
    J("rider", (0, -0.22, 0.98), "frame")
    J("neck", (0, 0.02, 1.4), "rider")
    wheel(rig, "wheel_rear", rig.world["wheel_rear"], (1, 0, 0), 0.34, name="rear")
    wheel(rig, "wheel_front", rig.world["wheel_front"], (1, 0, 0), 0.34, name="front")
    bb, rear, front = rig.world["crank"], rig.world["wheel_rear"], rig.world["wheel_front"]
    seat, head_t, head_b = Vector((0, -0.24, 0.95)), Vector((0, 0.42, 0.98)), Vector((0, 0.46, 0.76))
    bm = bmesh.new()  # Dutch granny bike: step-through frame, swept bars, mudguards, rack
    add_tube(bm, bb, seat, 0.019)
    add_tube(bm, bb, head_b, 0.022)
    add_polyline(bm, [seat.lerp(bb, 0.35), Vector((0, 0.05, 0.62)), Vector((0, 0.3, 0.72)), head_b.lerp(head_t, 0.3)], 0.019)
    add_tube(bm, head_b, head_t, 0.024)
    for x in (-0.05, 0.05):
        add_tube(bm, bb + Vector((x, 0, 0)), rear + Vector((x, 0, 0)), 0.011)
        add_tube(bm, seat + Vector((x, 0, -0.05)), rear + Vector((x, 0, 0)), 0.01)
        add_tube(bm, head_b + Vector((x, 0, 0)), front + Vector((x, 0.02, 0)), 0.012)
    add_polyline(bm, [head_t, head_t + Vector((0, -0.02, 0.14)), Vector((0, 0.32, 1.13))], 0.014)
    add_polyline(bm, [Vector((-0.3, 0.14, 1.1)), Vector((-0.22, 0.3, 1.13)), Vector((0.22, 0.3, 1.13)), Vector((0.3, 0.14, 1.1))], 0.012)
    for c in (rear, front):  # mudguards: arcs over the wheels
        pts = [c + Vector((0, math.cos(a) * 0.4, math.sin(a) * 0.4)) for a in [0.2 + i * 0.3 for i in range(9)]]
        add_polyline(bm, pts, 0.03, 4)
    for x in (-0.09, 0.09):  # rear rack
        add_tube(bm, Vector((x, -0.25, 0.8)), Vector((x, -0.8, 0.8)), 0.009)
    rig.part("bike_frame", "frame", bm, "rust")
    bm = bmesh.new()
    add_torus(bm, bb + Vector((0.07, 0, 0)), (1, 0, 0), 0.1, 0.01, 24, 4)
    for side in (-1, 1):
        crank_end = bb + Vector((0.09 * side, 0, 0.17 * side))
        add_tube(bm, bb + Vector((0.08 * side, 0, 0)), crank_end, 0.012)
        add_tube(bm, crank_end, crank_end + Vector((0.08 * side, 0, 0)), 0.02, 0.02, 4)
    rig.part("chainring", "crank", bm, "rust")
    # The rider grown into the bike: legs fused to the pedals, hands melted onto the bars.
    rig.skin("rider_torso", "rider", [seat, Vector((0, -0.14, 1.12)), Vector((0, -0.02, 1.3)), Vector((0, 0.02, 1.42))],
             [(0.14, 0.12), (0.17, 0.13), (0.2, 0.14), (0.07, 0.07)], "skin_drowned", displace=0.012)
    bm = bmesh.new()  # a yellow rain poncho clinging to everything
    add_drape(bm, (0, -0.02, 1.44), (0.12, 0.1), 0.62, (0.34, 0.3), folds=8, fold_amp=0.03, rng=rng,
              hem=lambda th: 0.8 + 0.2 * math.cos(th))
    ob = rig.part("poncho", "rider", bm, "poncho")
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.008
    veiled_head(rig, "neck", (0, -0.02, 1.55), 1.0, material="poncho", veil_len=0.3, rng=rng)
    bm = bmesh.new()  # the bicycle bell, lodged in the mouth
    add_sphere(bm, (0, 0.1, 1.49), (0.035, 0.03, 0.03), 12, 8)
    rig.part("bell", "neck", bm, "brass")
    for x in (-1, 1):
        rig.skin(f"arm_{x}", "rider", [Vector((0.2 * x, -0.02, 1.36)), Vector((0.3 * x, 0.1, 1.2)), Vector((0.3 * x, 0.14, 1.11)), Vector((0.24 * x, 0.25, 1.12))],
                 [0.06, 0.045, 0.035, 0.03], "poncho")
        pedal = bb + Vector((0.13 * x, 0, 0.17 * x))
        knee = Vector((0.18 * x, 0.12, 0.72 + 0.1 * x))
        rig.skin(f"leg_{x}", "rider", [seat + Vector((0.08 * x, 0, 0)), knee, pedal], [0.08, 0.06, 0.045], "skin_drowned", displace=0.01)
    return rig


def survivor(seed=9):
    """An ordinary expat parent: rain jacket with the hood up, jeans, boots,
    a small backpack. Face in the hood's shadow: planes, not detail."""
    rng = random.Random(seed)
    rig = Rig("survivor")
    J = rig.joint
    J("pelvis", (0, 0, 0.96))
    J("spine", (0, 0, 1.12), "pelvis")
    J("neck", (0, 0.02, 1.52), "spine")
    for s_, x in (("l", -1), ("r", 1)):
        J(f"shoulder_{s_}", (0.2 * x, 0.0, 1.44), "spine")
        J(f"elbow_{s_}", (0.23 * x, 0.0, 1.16), f"shoulder_{s_}")
        J(f"hip_{s_}", (0.095 * x, 0, 0.94), "pelvis")
        J(f"knee_{s_}", (0.1 * x, 0.02, 0.51), f"hip_{s_}")
    rig.skin("torso", "spine", [(0, 0, 0.93), (0, 0.01, 1.14), (0, 0.02, 1.38), (0, 0.02, 1.52)],
             [(0.17, 0.12), (0.18, 0.12), (0.2, 0.13), (0.07, 0.07)], "jacket", displace=0.008)
    bm = bmesh.new()  # jacket hem over the hips
    add_drape(bm, (0, 0.0, 1.06), (0.18, 0.13), 0.2, (0.2, 0.15), folds=6, fold_amp=0.012, rings=4, segs=24, rng=rng)
    ob = rig.part("jacket_hem", "pelvis", bm, "jacket")
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.01
    rig.skin("hips", "pelvis", [(0, 0, 0.98), (0, 0, 0.86)], [(0.16, 0.11), (0.14, 0.1)], "denim")
    head = Vector((0, 0.035, 1.64))
    bm = bmesh.new()
    add_sphere(bm, head, (0.085, 0.1, 0.112), 28, 18, face_impression())
    rig.part("face", "neck", bm, "skin")
    bm = bmesh.new()
    for x in (-1, 1):  # eyes: dark glints deep in the sockets
        add_sphere(bm, head + Vector((0.032 * x, 0.085, 0.012)), (0.011, 0.006, 0.008), 8, 6)
    rig.part("eyes", "neck", bm, "hair_wet")
    bm = bmesh.new()  # the hood, up: a shell around the head, open at the face
    c = head + Vector((0, -0.015, 0.01))
    verts = []
    for i in range(11):
        phi = math.pi * i / 10
        row = []
        for j in range(21):
            th = math.radians(-150 + 300 * j / 20) + math.pi  # leaves a ~60 degree opening at the front
            d = Vector((math.sin(phi) * math.sin(th), math.sin(phi) * math.cos(th), math.cos(phi)))
            row.append(bm.verts.new(c + Vector((d.x * 0.118, d.y * 0.13, d.z * 0.14))))
        verts.append(row)
    for i in range(10):
        for j in range(20):
            bm.faces.new((verts[i][j], verts[i][j + 1], verts[i + 1][j + 1], verts[i + 1][j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    ob = rig.part("hood", "neck", bm, "jacket")
    ob.modifiers.new("Solid", "SOLIDIFY").thickness = 0.012
    bm = bmesh.new()
    add_torus(bm, head + Vector((0, 0.02, -0.12)), (0, 0.3, 1), 0.085, 0.03, 20, 6)  # collar
    rig.part("collar", "neck", bm, "jacket")
    rig.skin("backpack", "spine", [(0, -0.17, 1.12), (0, -0.19, 1.38)], [(0.13, 0.06), (0.12, 0.05)], "backpack")
    for s_, x in (("l", -1), ("r", 1)):
        sh, el = rig.world[f"shoulder_{s_}"], rig.world[f"elbow_{s_}"]
        wrist = el + Vector((0.01 * x, 0.02, -0.26))
        rig.skin(f"sleeve_{s_}", f"shoulder_{s_}", [sh, el], [0.068, 0.058], "jacket")
        rig.skin(f"forearm_{s_}", f"elbow_{s_}", [el, wrist + Vector((0, 0, 0.03))], [0.058, 0.05], "jacket")
        long_hand(rig, f"elbow_{s_}", wrist, (0.05 * x, 0.1, -1), "skin", 0.085, curl=0.35)
        kn = rig.world[f"knee_{s_}"]
        ankle = kn + Vector((0, -0.02, -0.41))
        rig.skin(f"thigh_{s_}", f"hip_{s_}", [rig.world[f"hip_{s_}"], kn], [0.08, 0.058], "denim")
        rig.skin(f"shin_{s_}", f"knee_{s_}", [kn, ankle + Vector((0, 0, 0.06))], [0.055, 0.047], "denim")
        rig.skin(f"boot_{s_}", f"knee_{s_}", [ankle + Vector((0, -0.02, 0.08)), ankle + Vector((0, 0.0, 0.0)), ankle + Vector((0, 0.15, -0.03))],
                 [0.052, 0.055, (0.045, 0.035)], "leather")
    bm = bmesh.new()  # the pistol, in the right hand
    w = rig.world["elbow_r"] + Vector((0.01, 0.06, -0.3))
    add_tube(bm, w + Vector((0, -0.02, 0.0)), w + Vector((0, 0.15, 0.0)), 0.016, 0.016, 4)
    add_tube(bm, w + Vector((0, 0.0, 0.0)), w + Vector((0, -0.02, -0.09)), 0.014, 0.014, 4)
    rig.part("pistol", "elbow_r", bm, "gunmetal")
    return rig


# Humanoids + Kelderkind are built as skinned meshes by skinned.py; these stay jointed-rigid.
BUILDERS = {
    "grachtenvorst": grachtenvorst,
    "pestmeester": pestmeester, "fietser": fietser,
}


def export(rig, path):
    # Apply every modifier first (skin/subsurf/solidify), bake AO onto the final geometry, export.
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in [o for o in bpy.context.scene.objects if o.type == "MESH" and o.modifiers]:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = me
    bake_ao()
    gltf_export(path)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else set(BUILDERS)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in BUILDERS.items():
        if name not in only:
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        _mats.clear()
        rig = build()
        export(rig, OUT / f"{name}.glb")
        dg = bpy.context.evaluated_depsgraph_get()
        tris = 0
        for o in bpy.context.scene.objects:
            if o.type == "MESH":
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                me.calc_loop_triangles()
                tris += len(me.loop_triangles)
                ev.to_mesh_clear()
        print(f"[enemy] {name}: {tris} triangles")


if __name__ == "__main__":
    main()
