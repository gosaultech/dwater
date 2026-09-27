# damned_waters/tools/blender/skinned.py
# Purpose: build the humanoid cast and the Kelderkind as CONTINUOUS skinned
# meshes on a real skeleton (no seams at elbows/knees), with anatomical
# cross-sections, and export to game/assets/characters/enemies/<name>.glb.
#   python3 tools/blender/skinned.py [--only survivor,...]
# Pipeline per character:
#   1. armature: bones placed from joint positions (A-pose rest)
#   2. meshes: Skin modifier over a skeleton graph whose radii follow real
#      anatomy (deltoid, bicep, narrow elbow, forearm swell, calf, ankle...),
#      then applied to plain geometry
#   3. weights: each vertex blends the nearest bone with its parent/children
#      by inverse distance^5, restricted per garment so limbs never bleed into
#      each other. Smooth bends, no seams.
# Godot animates the bones procedurally (src/actors/skeletal_creature.gd).
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pipeline"))

import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import enemies_v2 as E  # noqa: E402  (materials + bmesh helpers)

OUT = E.OUT


# ───────────────────────────── skeleton ─────────────────────────────────────
def humanoid_bones(h=1.0, arm_out=1.0):
    """(name, head, tail, parent). A-pose: arms angled ~12 deg away from the body."""
    B = [("pelvis", (0, 0, 0.9), (0, 0, 1.03), None), ("spine", (0, 0, 1.03), (0, 0.01, 1.24), "pelvis"),
         ("chest", (0, 0.01, 1.24), (0, 0.0, 1.48), "spine"), ("neck", (0, 0.0, 1.48), (0, 0.015, 1.58), "chest"),
         ("head", (0, 0.015, 1.58), (0, 0.015, 1.8), "neck")]
    for s, x in (("l", -1), ("r", 1)):
        sh, el = (0.2 * x, 0, 1.435), (0.26 * x * arm_out, 0.0, 1.17)
        wr, hd = (0.3 * x * arm_out, 0.03, 0.93), (0.315 * x * arm_out, 0.045, 0.8)
        B += [(f"upper_arm_{s}", sh, el, "chest"), (f"forearm_{s}", el, wr, f"upper_arm_{s}"),
              (f"hand_{s}", wr, hd, f"forearm_{s}"),
              (f"thigh_{s}", (0.095 * x, 0, 0.915), (0.105 * x, 0.015, 0.5), "pelvis"),
              (f"shin_{s}", (0.105 * x, 0.015, 0.5), (0.105 * x, -0.005, 0.085), f"thigh_{s}"),
              (f"foot_{s}", (0.105 * x, -0.005, 0.085), (0.105 * x, 0.17, 0.02), f"shin_{s}")]
    return [(n, tuple(Vector(a) * h), tuple(Vector(b) * h), p) for n, a, b, p in B]


def crawler_bones():
    B = [("spine", (0, -0.3, 0.52), (0, 0.24, 0.57), None), ("neck", (0, 0.24, 0.57), (0, 0.36, 0.5), "spine"),
         ("head", (0, 0.36, 0.5), (0, 0.42, 0.3), "neck")]
    for s, x in (("l", -1), ("r", 1)):
        B += [(f"upper_arm_{s}", (0.14 * x, 0.24, 0.56), (0.29 * x, 0.34, 0.66), "spine"),
              (f"forearm_{s}", (0.29 * x, 0.34, 0.66), (0.31 * x, 0.5, 0.05), f"upper_arm_{s}"),
              (f"hand_{s}", (0.31 * x, 0.5, 0.05), (0.33 * x, 0.64, 0.02), f"forearm_{s}"),
              (f"thigh_{s}", (0.12 * x, -0.3, 0.52), (0.29 * x, -0.22, 0.72), "spine"),
              (f"shin_{s}", (0.29 * x, -0.22, 0.72), (0.28 * x, -0.44, 0.05), f"thigh_{s}"),
              (f"foot_{s}", (0.28 * x, -0.44, 0.05), (0.29 * x, -0.56, 0.02), f"shin_{s}")]
    return B


def make_armature(name, bones):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for n, a, b, p in bones:
        eb = arm.edit_bones.new(n)
        eb.head, eb.tail = a, b
        if p:
            eb.parent = arm.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


# ───────────────────────────── meshes ───────────────────────────────────────
def skin_graph(name, pts, edges, radii, material, subsurf=2, displace=0.0, dscale=0.2):
    """Skin-modifier mesh, modifiers applied, returned as plain geometry at world origin."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], edges, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.5
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
    me.materials.append(E.mat(material))
    return bake(ob)


def bake(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    ob.data = me
    for p in me.polygons:
        p.use_smooth = True
    return ob


def bm_object(name, bm, material, solidify=0.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(E.mat(material))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if solidify:
        ob.modifiers.new("Solid", "SOLIDIFY").thickness = solidify
    return bake(ob)


class Graph:
    """Skin-graph builder: chains of (point, radius) sharing named junctions."""

    def __init__(self):
        self.pts, self.rad, self.edges, self.names = [], [], [], {}

    def add(self, p, r, name=None):
        self.pts.append(Vector(p))
        self.rad.append(r if isinstance(r, tuple) else (r, r))
        if name:
            self.names[name] = len(self.pts) - 1
        return len(self.pts) - 1

    def chain(self, start, items):
        """start: index or junction name; items: [(point, radius[, name]), ...]."""
        prev = self.names[start] if isinstance(start, str) else start
        for it in items:
            i = self.add(it[0], it[1], it[2] if len(it) > 2 else None)
            self.edges.append((prev, i))
            prev = i
        return prev

    def build(self, name, material, **kw):
        return skin_graph(name, self.pts, self.edges, self.rad, material, **kw)


def scale_r(r, k):
    return (r[0] * k, r[1] * k) if isinstance(r, tuple) else r * k


# ───────────────────────────── weights ──────────────────────────────────────
def bind(ob, arm_ob, bones, allowed=None, sharp=5.0):
    """Blend each vertex between its nearest bone and that bone's parent/children."""
    names = [b[0] for b in bones if (allowed is None or b[0] in allowed)]
    idx = {n: i for i, n in enumerate(names)}
    info = {b[0]: b for b in bones}
    A = np.array([info[n][1] for n in names])
    Bt = np.array([info[n][2] for n in names])
    V = np.array([v.co[:] for v in ob.data.vertices])
    AB = Bt - A
    t = np.clip(np.einsum("vbk,bk->vb", V[:, None, :] - A[None], AB) / np.einsum("bk,bk->b", AB, AB)[None], 0, 1)
    D = np.linalg.norm(V[:, None, :] - (A[None] + t[..., None] * AB[None]), axis=-1) + 1e-4
    M = np.eye(len(names), dtype=bool)
    for n in names:
        p = info[n][3]
        if p in idx:
            M[idx[n], idx[p]] = M[idx[p], idx[n]] = True
    W = np.where(M[D.argmin(1)], D ** -sharp, 0.0)
    W /= W.sum(1, keepdims=True)
    W[W < 0.03] = 0
    W /= W.sum(1, keepdims=True)
    for j, n in enumerate(names):
        vg = ob.vertex_groups.new(name=n)
        for i in np.nonzero(W[:, j])[0]:
            vg.add([int(i)], float(W[i, j]), "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_ob
    ob.parent = arm_ob


def rigid(ob, arm_ob, bone):
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_ob
    ob.parent = arm_ob


# ───────────────────────────── anatomy ──────────────────────────────────────
def torso_arms(g, k_torso=1.0, k_arm=1.0, belly=1.0, arm_out=1.0, sleeve_end=True):
    """Torso + both arms in ONE graph (a jacket/coat with sleeves, or bare skin).
    Starts below the belt line so it always overlaps the trousers (no floating torso)."""
    kt, ka = k_torso, k_arm
    g.chain(g.add((0, 0, 0.86), scale_r((0.176, 0.126), kt), "hem"), [((0, 0, 0.98), scale_r((0.168, 0.118), kt), "hips")])
    g.chain("hips", [
        ((0, 0.01, 1.06), scale_r((0.155, 0.11 * belly), kt)),
        ((0, 0.02 * belly, 1.14), scale_r((0.15, 0.107 * belly), kt)),
        ((0, 0.02, 1.24), scale_r((0.162, 0.112), kt)),
        ((0, 0.02, 1.34), scale_r((0.175, 0.118), kt)),
        ((0, 0.01, 1.43), scale_r((0.17, 0.105), kt), "shoulders"),
        ((0, 0.0, 1.5), scale_r((0.075, 0.07), kt), "collar")])
    for x in (-1, 1):
        end = [((0.3 * x * arm_out, 0.03, 0.935), scale_r((0.045, 0.042), ka))] if sleeve_end else []
        g.chain("shoulders", [
            ((0.11 * x, 0.0, 1.455), scale_r((0.06, 0.055), ka)),
            ((0.2 * x, 0.0, 1.435), scale_r((0.068, 0.07), ka)),                 # deltoid
            ((0.23 * x * arm_out, 0.0, 1.3), scale_r((0.056, 0.06), ka)),        # bicep
            ((0.26 * x * arm_out, 0.0, 1.17), scale_r((0.046, 0.048), ka)),      # elbow: narrow
            ((0.275 * x * arm_out, 0.012, 1.07), scale_r((0.05, 0.047), ka)),    # forearm swell
        ] + end)


def legs(g, k=1.0, top=(0, 0, 1.02), ankle_z=0.12):
    # Waistband sits INSIDE the jacket/coat hem (smaller radius, higher top).
    g.chain(g.add(top, scale_r((0.148, 0.102), k), "waist"), [((0, 0, 0.9), scale_r((0.16, 0.112), k), "crotch")])
    for x in (-1, 1):
        g.chain("crotch", [
            ((0.095 * x, 0, 0.9), scale_r((0.092, 0.095), k)),
            ((0.1 * x, 0.008, 0.75), scale_r((0.08, 0.083), k)),       # quadriceps
            ((0.105 * x, 0.012, 0.6), scale_r((0.062, 0.066), k)),
            ((0.105 * x, 0.015, 0.5), scale_r((0.054, 0.057), k)),     # knee: narrow
            ((0.105 * x, 0.0, 0.37), scale_r((0.055, 0.062), k)),      # calf bulge (rear)
            ((0.105 * x, -0.003, 0.2), scale_r((0.043, 0.045), k)),
            ((0.105 * x, -0.005, ankle_z), scale_r((0.04, 0.042), k))])


def hand(g, wrist, x, material_k=1.0, long_fingers=False, rng=None):
    w = Vector(wrist)
    start = g.add(w, (0.028 * material_k, 0.022 * material_k))
    palm = g.chain(start, [(w + Vector((0.006 * x, 0.006, -0.06)), (0.042 * material_k, 0.017 * material_k))])
    if long_fingers:  # drowned: swollen, over-long fingers
        for f in range(4):
            base = w + Vector(((0.004 + (f - 1.5) * 0.013) * x, 0.01 + (f - 1.5) * 0.004, -0.085))
            g.chain(palm, [(base, 0.011 * material_k), (base + Vector((0.004 * x, 0.02, -0.06)), 0.01 * material_k),
                           (base + Vector((0.006 * x, 0.045, -0.1)), 0.008 * material_k),
                           (base + Vector((0.007 * x, 0.06, -0.13)), 0.005 * material_k)])
    else:
        g.chain(palm, [(w + Vector((0.008 * x, 0.012, -0.115)), (0.043, 0.015)), (w + Vector((0.01 * x, 0.025, -0.17)), (0.035, 0.012))])
    g.chain(palm, [(w + Vector((-0.012 * x, 0.022, -0.045)), 0.015 * material_k),
                   (w + Vector((-0.024 * x, 0.045, -0.08)), 0.012 * material_k),
                   (w + Vector((-0.03 * x, 0.06, -0.105)), 0.009 * material_k)])  # thumb


# ───────────────────────────── characters ───────────────────────────────────
def export(name):
    E.bake_ao()  # crevice shadow into vertex colours (bind pose)
    E.gltf_export(OUT / f"{name}.glb")


def face_sculpt():
    """A human face (not a veil impression): nose, brow, sockets, cheekbones, lips, chin, jaw."""
    feats = [((0, 1, -0.05), 0.12, 0.028), ((0, 0.97, 0.22), 0.22, 0.01), ((0.34, 0.93, 0.1), 0.1, -0.013),
             ((-0.34, 0.93, 0.1), 0.1, -0.013), ((0.55, 0.8, -0.1), 0.2, 0.008), ((-0.55, 0.8, -0.1), 0.2, 0.008),
             ((0, 0.94, -0.31), 0.07, 0.006), ((0, 0.93, -0.39), 0.07, 0.008), ((0, 0.82, -0.62), 0.16, 0.014),
             ((0.75, 0.5, -0.45), 0.2, 0.006), ((-0.75, 0.5, -0.45), 0.2, 0.006)]
    feats = [(Vector(d).normalized(), s, a) for d, s, a in feats]
    return lambda d: sum(a * math.exp(-((d - fd).length ** 2) / (2 * s * s)) for fd, s, a in feats)


def hair_cap(center, radii, rng):
    """Short, damp, messy hair: a shell above an uneven hairline, clumped."""
    bm = bmesh.new()
    E.add_sphere(bm, center, radii, 28, 18)
    c = Vector(center)
    doomed = []
    for v in bm.verts:
        d = Vector(((v.co.x - c.x) / radii[0], (v.co.y - c.y) / radii[1], (v.co.z - c.z) / radii[2])).normalized()
        th = math.atan2(d.x, d.y)
        line = -0.05 + 0.5 * math.cos(th) + 0.05 * math.sin(th * 7 + 1.3)
        if d.z < line:
            doomed.append(v)
        else:
            v.co += d * (0.004 + 0.006 * (math.sin(th * 11) * math.sin(d.z * 9) * 0.5 + 0.5))
    bmesh.ops.delete(bm, geom=doomed, context="VERTS")
    return bm


def survivor():
    rng = random.Random(9)
    bones = humanoid_bones()
    arm = make_armature("survivor", bones)
    upper = ["pelvis", "spine", "chest", "neck", "upper_arm_l", "upper_arm_r", "forearm_l", "forearm_r"]
    g = Graph()
    torso_arms(g, 1.0, 1.0)
    bind(g.build("jacket", "jacket", displace=0.006), arm, bones, upper)
    bm = bmesh.new()
    E.add_drape(bm, (0, 0.0, 0.93), (0.178, 0.128), 0.1, (0.186, 0.134), folds=7, fold_amp=0.01, rings=3, segs=28, rng=rng)
    bind(bm_object("jacket_hem", bm, "jacket", solidify=0.01), arm, bones, ["pelvis", "thigh_l", "thigh_r"])
    g = Graph()
    legs(g)
    bind(g.build("jeans", "denim"), arm, bones, ["pelvis", "spine", "thigh_l", "thigh_r", "shin_l", "shin_r"])
    for x, s in ((-1, "l"), (1, "r")):
        g = Graph()
        g.chain(g.add((0.105 * x, -0.005, 0.17), (0.05, 0.052)), [((0.105 * x, 0.0, 0.07), (0.05, 0.056), "ankle"),
                ((0.105 * x, 0.12, 0.035), (0.047, 0.03)), ((0.105 * x, 0.185, 0.03), (0.042, 0.026))])
        g.chain("ankle", [((0.105 * x, -0.048, 0.035), (0.042, 0.03))])
        bind(g.build(f"boot_{s}", "leather", subsurf=1), arm, bones, [f"shin_{s}", f"foot_{s}"])
        g = Graph()
        hand(g, (0.3 * x, 0.03, 0.935), x)
        bind(g.build(f"hand_{s}", "skin", subsurf=1), arm, bones, [f"forearm_{s}", f"hand_{s}"])
    g = Graph()
    g.chain(g.add((0, 0.0, 1.48), 0.068), [((0, 0.012, 1.6), 0.061)])
    bind(g.build("neck", "skin", subsurf=1), arm, bones, ["chest", "neck", "head"])
    head = Vector((0, 0.038, 1.665))
    bm = bmesh.new()  # painted face on a sculpted head (UVs match tools/art/materials.py paint_face)
    E.add_sphere(bm, head, (0.08, 0.095, 0.108), 40, 26, face_sculpt(), uv=True)
    rigid(bm_object("face", bm, "face_survivor"), arm, "head")
    bm = bmesh.new()
    for x in (-1, 1):
        E.add_sphere(bm, head + Vector((0.082 * x, -0.004, 0.0)), (0.012, 0.024, 0.031), 10, 8)
    rigid(bm_object("ears", bm, "skin"), arm, "head")
    rigid(bm_object("hair", hair_cap(head + Vector((0, -0.004, 0.006)), (0.086, 0.101, 0.114), rng), "hair", solidify=0.008), arm, "head")
    bm = bmesh.new()
    E.add_torus(bm, (0, 0.01, 1.5), (0, 0.25, 1), 0.08, 0.028, 20, 6)
    bind(bm_object("collar", bm, "jacket"), arm, bones, ["chest", "neck"])
    g = Graph()
    g.chain(g.add((0, -0.16, 1.12), (0.12, 0.055)), [((0, -0.175, 1.38), (0.115, 0.05))])
    rigid(g.build("backpack", "backpack", subsurf=1), arm, "chest")
    bm = bmesh.new()  # pistol along the right hand
    w = Vector((0.3, 0.03, 0.935))
    E.add_tube(bm, w + Vector((0.005, 0.0, -0.08)), w + Vector((0.02, 0.0, -0.24)), 0.016, 0.016, 4)
    E.add_tube(bm, w + Vector((0.005, 0.0, -0.08)), w + Vector((0.005, 0.07, -0.09)), 0.014, 0.014, 4)
    rigid(bm_object("pistol", bm, "gunmetal"), arm, "hand_r")
    return "survivor"


def verdronkene(variant):
    rng = random.Random(1 if variant == "veiled" else 3)
    bones = humanoid_bones(arm_out=1.08)
    name = f"verdronkene_{variant}"
    arm = make_armature(name, bones)
    upper = ["pelvis", "spine", "chest", "neck", "upper_arm_l", "upper_arm_r", "forearm_l", "forearm_r"]
    g = Graph()  # bloated body under a waterlogged overcoat
    torso_arms(g, 1.2, 1.15, belly=1.35, arm_out=1.08)
    bind(g.build("coat", "coat_wet", displace=0.014), arm, bones, upper)
    bm = bmesh.new()  # the coat skirt follows the thighs
    E.add_drape(bm, (0, 0.012, 1.02), (0.2, 0.17), 0.56, (0.3, 0.27), folds=6, fold_amp=0.02, rng=rng,
                hem=lambda th: 1.0 - 0.15 * math.cos(th))
    bind(bm_object("coat_skirt", bm, "coat_wet", solidify=0.012), arm, bones, ["pelvis", "thigh_l", "thigh_r"])
    g = Graph()
    legs(g, 1.1, ankle_z=0.11)
    bind(g.build("trousers", "coat_wet"), arm, bones, ["pelvis", "spine", "thigh_l", "thigh_r", "shin_l", "shin_r"])
    for x, s in ((-1, "l"), (1, "r")):
        g = Graph()  # bare, swollen feet
        g.chain(g.add((0.105 * x, -0.005, 0.13), (0.045, 0.047)), [((0.105 * x, 0.0, 0.06), (0.05, 0.055), "ankle"),
                ((0.105 * x, 0.12, 0.03), (0.052, 0.028)), ((0.105 * x, 0.19, 0.025), (0.044, 0.022))])
        g.chain("ankle", [((0.105 * x, -0.045, 0.03), (0.04, 0.03))])
        bind(g.build(f"foot_{s}", "skin_drowned", subsurf=1), arm, bones, [f"shin_{s}", f"foot_{s}"])
        g = Graph()
        hand(g, (0.3 * x * 1.08, 0.03, 0.935), x, 1.15, long_fingers=True, rng=rng)
        bind(g.build(f"hand_{s}", "skin_drowned", subsurf=1), arm, bones, [f"forearm_{s}", f"hand_{s}"])
    g = Graph()
    g.chain(g.add((0, 0.0, 1.48), 0.075), [((0, 0.015, 1.6), 0.065)])
    bind(g.build("neck", "skin_drowned", subsurf=1), arm, bones, ["chest", "neck", "head"])
    head = Vector((0, 0.04, 1.665))
    bm = bmesh.new()
    E.add_sphere(bm, head, (0.098, 0.112, 0.125), 32, 20, E.face_impression())
    rigid(bm_object("veil_face", bm, "shroud"), arm, "head")
    bm = bmesh.new()
    E.add_sphere(bm, head + Vector((0, 0.1, -0.05)), (0.018, 0.012, 0.012), 10, 6)
    rigid(bm_object("mouth", bm, "void"), arm, "head")
    bm = bmesh.new()
    E.add_drape(bm, head + Vector((0, -0.01, 0.02)), (0.105, 0.12), 0.42, (0.26, 0.21), folds=9, fold_amp=0.03,
                rings=8, segs=32, hem=lambda th: 0.35 + 0.65 * (1 - math.cos(th)) / 2, rng=rng)
    bind(bm_object("veil", bm, "shroud", solidify=0.006), arm, bones, ["head", "neck", "chest"], sharp=3.0)
    # Gas-bloated belly split open through the coat, guts slipping out.
    bc = Vector((0, 0.19, 1.13))
    trunk = ["pelvis", "spine", "chest"]
    bm = bmesh.new()
    E.add_sphere(bm, bc, (0.13, 0.08, 0.12), 20, 12)
    bind(bm_object("belly", bm, "skin_drowned"), arm, bones, trunk)
    bm = bmesh.new()
    E.add_sphere(bm, bc + Vector((0.01, 0.07, -0.01)), (0.03, 0.017, 0.078), 12, 8)
    bind(bm_object("wound_rim", bm, "flesh_raw"), arm, bones, trunk)
    bm = bmesh.new()
    E.add_sphere(bm, bc + Vector((0.01, 0.079, -0.01)), (0.017, 0.011, 0.064), 10, 6)
    bind(bm_object("wound", bm, "void"), arm, bones, trunk)
    for i in range(3):
        top = bc + Vector((0.01 + (i - 1) * 0.012, 0.078, -0.055))
        g = Graph()
        g.chain(g.add(top, 0.013), [(top + Vector((rng.uniform(-0.03, 0.03), 0.03, -0.12)), 0.011),
                                     (top + Vector((rng.uniform(-0.04, 0.04), 0.02, -0.24 - i * 0.05)), 0.008)])
        bind(g.build(f"gut_{i}", "flesh_raw", subsurf=1), arm, bones, ["pelvis", "spine"])
    # Leeches feeding: neck, veiled cheek, forearm, belly.
    for p, bone, ax in [((0.05, 0.06, 1.52), "neck", (0.012, 0.012, 0.032)), ((-0.07, 0.1, 1.6), "head", (0.012, 0.012, 0.03)),
                        ((0.31, 0.06, 1.0), "forearm_r", (0.011, 0.011, 0.03)), ((-0.08, 0.245, 1.08), "spine", (0.013, 0.011, 0.034)),
                        ((0.09, 0.235, 1.19), "spine", (0.012, 0.01, 0.03))]:
        bm = bmesh.new()
        E.add_sphere(bm, p, ax, 10, 6)
        rigid(bm_object("leech", bm, "leech"), arm, bone)
    bm = bmesh.new()  # blood and drool soaking through the veil at the mouth
    E.add_sphere(bm, head + Vector((0, 0.104, -0.05)), (0.034, 0.009, 0.028), 12, 6)
    rigid(bm_object("mouth_blood", bm, "flesh_raw"), arm, "head")
    for x, s in ((-1, "l"), (1, "r")):  # rotted black fingertips
        w = Vector((0.3 * x * 1.08, 0.03, 0.935))
        bm = bmesh.new()
        for f in range(4):
            tip = w + Vector(((0.004 + (f - 1.5) * 0.013) * x, 0.01 + (f - 1.5) * 0.004, -0.085)) + Vector((0.007 * x, 0.06, -0.13))
            E.add_sphere(bm, tip, (0.009, 0.009, 0.012), 8, 6)
        rigid(bm_object(f"rot_{s}", bm, "leech"), arm, f"hand_{s}")
    if variant == "netted":
        bm = bmesh.new()
        for kk in range(14):
            a0 = kk * 2 * math.pi / 14
            pts = [(math.sin(a0 + t * 0.45 * (1 if kk % 2 else -1)) * 0.3, math.cos(a0 + t * 0.45 * (1 if kk % 2 else -1)) * 0.25 + 0.03, 0.92 + t * 0.048)
                   for t in range(13)]
            E.add_polyline(bm, pts, 0.006, 4)
        bind(bm_object("net", bm, "rope"), arm, bones, ["pelvis", "spine", "chest"])
    for i in range(8):
        a = rng.uniform(-2.8, 2.8)
        top = Vector((math.sin(a) * 0.24, math.cos(a) * 0.2, rng.uniform(1.0, 1.4)))
        g = Graph()
        g.chain(g.add(top, (0.02, 0.004)), [(top + Vector((0, 0.03, -0.25)), (0.015, 0.003)),
                                             (top + Vector((rng.uniform(-0.05, 0.05), 0.04, -0.45)), (0.004, 0.002))])
        rigid(g.build(f"weed_{i}", "kelp", subsurf=1), arm, "spine")
    return name


def kelderkind():
    rng = random.Random(2)
    bones = crawler_bones()
    arm = make_armature("kelderkind", bones)
    g = Graph()  # one continuous pale body: torso, limbs, fingers, toes
    g.chain(g.add((0, -0.32, 0.5), (0.13, 0.1), "pelvis"), [
        ((0, -0.08, 0.6), (0.1, 0.085)), ((0, 0.18, 0.6), (0.15, 0.12), "chest"), ((0, 0.3, 0.55), (0.06, 0.06), "neck")])
    for x in (-1, 1):
        wr = g.chain("chest", [((0.14 * x, 0.24, 0.56), 0.045), ((0.22 * x, 0.29, 0.62), 0.038),
                               ((0.29 * x, 0.34, 0.66), 0.028), ((0.3 * x, 0.42, 0.35), 0.026),
                               ((0.31 * x, 0.5, 0.05), 0.019)])
        for f in range(4):
            a = math.radians(-30 + f * 20) * x
            g.chain(wr, [(Vector((0.31 * x, 0.5, 0.05)) + Vector((math.sin(a) * 0.08, math.cos(a) * 0.08, -0.03)), 0.008),
                         (Vector((0.31 * x, 0.5, 0.05)) + Vector((math.sin(a) * 0.16, math.cos(a) * 0.16, -0.045)), 0.005)])
        an = g.chain("pelvis", [((0.12 * x, -0.3, 0.52), 0.052), ((0.21 * x, -0.26, 0.64), 0.042),
                                ((0.29 * x, -0.22, 0.72), 0.032), ((0.285 * x, -0.33, 0.38), 0.03),
                                ((0.28 * x, -0.44, 0.05), 0.021)])
        for f in range(3):
            a = math.radians(160 + (f - 1) * 18) * x
            g.chain(an, [(Vector((0.28 * x, -0.44, 0.05)) + Vector((math.sin(a) * 0.1, math.cos(a) * 0.1, -0.035)), 0.007)])
    bind(g.build("body", "skin_pale", displace=0.005, dscale=0.05), arm, bones, [b[0] for b in bones if b[0] != "head"])
    for x, s in ((-1, "l"), (1, "r")):  # long black nails
        bm = bmesh.new()
        for f in range(4):
            a = math.radians(-30 + f * 20) * x
            tip = Vector((0.31 * x, 0.5, 0.05)) + Vector((math.sin(a) * 0.16, math.cos(a) * 0.16, -0.045))
            E.add_tube(bm, tip, tip + Vector((math.sin(a) * 0.035, math.cos(a) * 0.035, -0.008)), 0.005, 0.0008, 5)
        rigid(bm_object(f"nails_{s}", bm, "leech"), arm, f"hand_{s}")
    bm = bmesh.new()  # ribs pressed through the skin of the upturned chest
    for kk in range(6):
        y = 0.06 + kk * 0.035
        pts = [(math.sin(a) * 0.14, y, 0.62 + math.cos(a) * 0.06) for a in [(-1.3 + t * 0.325) for t in range(9)]]
        E.add_polyline(bm, pts, 0.007, 5)
    bind(bm_object("ribs", bm, "skin_pale"), arm, bones, ["spine"])
    hc = Vector((0, 0.4, 0.4))
    bm = bmesh.new()

    def eyeless(d):
        return 0.018 * math.exp(-((d - Vector((0, 0.9, -0.1)).normalized()).length ** 2) / 0.05) \
            - 0.01 * math.exp(-((d - Vector((0.3, 0.9, 0.12)).normalized()).length ** 2) / 0.02) \
            - 0.01 * math.exp(-((d - Vector((-0.3, 0.9, 0.12)).normalized()).length ** 2) / 0.02)
    E.add_sphere(bm, (0, 0, 0), (0.078, 0.092, 0.1), 24, 16, eyeless)
    for v in bm.verts:
        v.co = Vector((v.co.x, v.co.y, -v.co.z)) + hc
    rigid(bm_object("head", bm, "skin_pale"), arm, "head")
    bm = bmesh.new()
    E.add_sphere(bm, hc + Vector((0, 0.085, 0.05)), (0.05, 0.02, 0.014), 12, 6)
    rigid(bm_object("mouth", bm, "void"), arm, "head")
    bm = bmesh.new()
    E.add_sphere(bm, hc + Vector((0, 0.08, 0.05)), (0.056, 0.02, 0.026), 12, 6)
    rigid(bm_object("gums", bm, "flesh_raw"), arm, "head")
    bm = bmesh.new()  # eyelids sewn shut: a crude slit crossed by stitches
    for sx in (-1, 1):
        eye = hc + Vector((0.0245 * sx, 0.089, -0.0126))
        E.add_sphere(bm, eye, (0.017, 0.004, 0.003), 8, 4)
        for k2 in range(5):
            xx = eye.x + (k2 - 2) * 0.0065
            E.add_tube(bm, Vector((xx, eye.y + 0.003, eye.z - 0.007)), Vector((xx + 0.002, eye.y + 0.003, eye.z + 0.007)), 0.0012, 0.0012, 4)
    rigid(bm_object("sutures", bm, "void"), arm, "head")
    bm = bmesh.new()
    for kk in range(9):
        xx = (kk - 4) * 0.009
        for up in (1, -1):
            base = hc + Vector((xx, 0.098, 0.05 + 0.012 * up))
            E.add_tube(bm, base, base + Vector((0, 0.003, -0.012 * up)), 0.003, 0.0005, 4)
    rigid(bm_object("teeth", bm, "teeth"), arm, "head")
    for i in range(18):
        a = rng.uniform(0, 2 * math.pi)
        root = hc + Vector((math.sin(a) * 0.07, -0.02 + math.cos(a) * 0.06, -0.08))
        end = Vector((root.x + rng.uniform(-0.06, 0.06), root.y + rng.uniform(-0.02, 0.08), 0.0))
        g = Graph()
        g.chain(g.add(root, 0.006), [(root.lerp(end, 0.5) + Vector((0, 0.02, 0)), 0.005), (end, 0.003)])
        rigid(g.build(f"hair_{i}", "hair_wet", subsurf=1), arm, "head")
    return "kelderkind"


BUILDERS = {"survivor": survivor, "verdronkene_veiled": lambda: verdronkene("veiled"),
            "verdronkene_netted": lambda: verdronkene("netted"), "kelderkind": kelderkind}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else set(BUILDERS)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, build in BUILDERS.items():
        if name not in only:
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        E._mats.clear()
        build()
        export(name)
        verts = sum(len(o.data.vertices) for o in bpy.context.scene.objects if o.type == "MESH")
        print(f"[skinned] {name}: {verts} verts, {len([o for o in bpy.context.scene.objects if o.type == 'MESH'])} meshes")


if __name__ == "__main__":
    main()
