# damned_waters/tools/blender/kit.py
# Purpose: the detailed set kit, built from RoomSpec props the way builders.py builds the simple
# ones, but closer to real furniture: soft (bevelled) edges, cushions that look stuffed, panelled
# Amsterdam cabinets (kasten), a carved marble mantel with a cast-iron insert, turned brass
# candlesticks, gathered curtains, arched steel-framed windows with a brick arch, beams, and any
# Poly Haven model by name. Coordinates are a prop's local Godot frame (x right, y up, z front),
# as in builders.part().
#
# ELI5: builders.py makes furniture out of shoeboxes; this sands the edges, stuffs the cushions and
# fits the panels, so the camera reads "sofa", not "box".
import math

import bpy

import builders
import surfaces
from roomspec import g2b

DEFAULT_FABRIC = {"color": [0.42, 0.40, 0.37], "rough": 0.95, "noise": 0.08}
DEFAULT_PAINT = {"color": [0.11, 0.11, 0.12], "rough": 0.45, "noise": 0.1}
STEEL = {"color": [0.02, 0.02, 0.022], "rough": 0.4, "metal": 0.6, "noise": 0.05}
BRASS = {"color": [0.62, 0.45, 0.2], "rough": 0.28, "metal": 1.0, "noise": 0.15}


def mat(key, fallback):
    return builders.material(key if key is not None else fallback)


# ── Mesh helpers ─────────────────────────────────────────────────────────────────
def mesh(name, verts_g, faces, m, parent, smooth=False):
    """A mesh from local Godot-frame vertices, UVs box-projected in metres."""
    verts = [g2b(v) for v in verts_g]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[a], co[b])
        poly.use_smooth = smooth
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    return ob


def bevel(ob, width, segments=3, profile=0.5, harden=True):
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.profile = profile
    m.limit_method = "NONE"
    m.harden_normals = harden
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def soft(parent, name, center, size, m, r=0.02, segs=3, rot_x=0.0, profile=0.5):
    """builders.part() with sanded edges."""
    ob = builders.part(parent, name, center, size, m, rot_x_deg=rot_x)
    r = min(r, min(size) * 0.45)
    return bevel(ob, r, segs, profile)


def lathe(parent, name, profile, m, at=(0, 0, 0), segments=32, smooth=True):
    """A turned piece (candlestick, baluster, vase): profile [(radius, height)] bottom to top."""
    verts, faces = [], []
    n = len(profile)
    for i in range(segments):
        a = 2 * math.pi * i / segments
        for r, y in profile:
            verts.append((at[0] + r * math.cos(a), at[1] + y, at[2] + r * math.sin(a)))
    for i in range(segments):
        j = (i + 1) % segments
        for k in range(n - 1):
            faces.append((i * n + k, i * n + k + 1, j * n + k + 1, j * n + k))
    verts.append((at[0], at[1] + profile[0][1], at[2]))
    verts.append((at[0], at[1] + profile[-1][1], at[2]))
    b, t = len(verts) - 2, len(verts) - 1
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i * n, j * n, b))
        faces.append((j * n + n - 1, i * n + n - 1, t))
    return mesh(name, verts, faces, m, parent, smooth)


def prism(parent, name, poly_uv, depth, m, frame):
    """A flat polygon (u, v) swept along `depth`: frame = (origin, u_axis, v_axis, w_axis) in the
    prop's local Godot frame. Triangulated as a fan from the polygon's first point (fine for the
    star-shaped spandrels and arch rings built here)."""
    o, U, V, W = frame
    def at(u, v, w):
        return tuple(o[i] + U[i] * u + V[i] * v + W[i] * w for i in range(3))
    n = len(poly_uv)
    verts = [at(u, v, 0) for u, v in poly_uv] + [at(u, v, depth) for u, v in poly_uv]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh(name, verts, faces, m, parent)


# ── Furniture ────────────────────────────────────────────────────────────────────
def sofa(root, p, w, h, d):
    fab = mat(p.get("material"), DEFAULT_FABRIC)
    base = mat(p.get("base"), {"color": [0.03, 0.025, 0.02], "rough": 0.6})
    pillow = mat(p.get("pillows"), {"color": [0.16, 0.16, 0.17], "rough": 0.9, "noise": 0.1})
    arm_w, seat_h, arm_h = 0.2, 0.42, min(0.64, h - 0.12)
    builders.part(root, "plinth", (0, 0.04, 0.02), (w - 0.1, 0.08, d - 0.12), base)
    soft(root, "frame", (0, 0.08 + (seat_h - 0.2) / 2, 0.02), (w, seat_h - 0.2, d - 0.04), fab, 0.03)
    n = max(2, round((w - 2 * arm_w) / 0.8))
    cw = (w - 2 * arm_w) / n
    for i in range(n):
        x = -w / 2 + arm_w + cw * (i + 0.5)
        soft(root, "seat", (x, seat_h - 0.05, 0.08), (cw - 0.012, 0.17, d - 0.3), fab, 0.06, 4, profile=0.7)
        soft(root, "back_cushion", (x, seat_h + (h - seat_h) / 2 - 0.02, -d / 2 + 0.27), (cw - 0.012, h - seat_h - 0.06, 0.2),
             fab, 0.07, 4, rot_x=-9, profile=0.7)
    soft(root, "back", (0, (0.08 + h) / 2, -d / 2 + 0.09), (w, h - 0.08, 0.18), fab, 0.035)
    for s in (-1, 1):
        soft(root, "arm", (s * (w / 2 - arm_w / 2), (0.08 + arm_h) / 2, 0.02), (arm_w, arm_h - 0.08, d - 0.04), fab, 0.04)
    for i, (x, rot) in enumerate(((-w / 2 + arm_w + 0.3, 12), (-w / 2 + arm_w + 0.75, -6), (w / 2 - arm_w - 0.35, 8))):
        if i == 2 and w < 2.2:
            continue
        pl = soft(root, "pillow", (x, seat_h + 0.26, -d / 2 + 0.42), (0.46, 0.44, 0.14), pillow, 0.06, 4, rot_x=-14, profile=0.75)
        pl.rotation_euler[2] = math.radians(rot)


def armchair(root, p, w, h, d):
    fab = mat(p.get("material"), DEFAULT_FABRIC)
    wood = mat(p.get("legs"), {"color": [0.03, 0.022, 0.016], "rough": 0.4})
    leg_h, seat_h, arm_h, arm_w = 0.11, 0.45, 0.66, 0.16
    for sx in (-1, 1):
        for sz in (-1, 1):
            lathe(root, "leg", [(0.022, 0), (0.016, 0.0), (0.02, leg_h - 0.01), (0.024, leg_h)], wood,
                  at=(sx * (w / 2 - 0.06), 0, sz * (d / 2 - 0.06)), segments=12)
    soft(root, "base", (0, leg_h + (seat_h - leg_h - 0.12) / 2, 0), (w, seat_h - leg_h - 0.12, d), fab, 0.03)
    soft(root, "seat", (0, seat_h - 0.06, 0.06), (w - 2 * arm_w + 0.01, 0.15, d - 0.22), fab, 0.06, 4, profile=0.7)
    soft(root, "back", (0, (leg_h + h) / 2, -d / 2 + 0.08), (w, h - leg_h, 0.16), fab, 0.035)
    soft(root, "back_cushion", (0, seat_h + (h - seat_h) / 2, -d / 2 + 0.23), (w - 2 * arm_w, h - seat_h - 0.04, 0.16),
         fab, 0.06, 4, rot_x=-10, profile=0.7)
    for s in (-1, 1):
        soft(root, "arm", (s * (w / 2 - arm_w / 2), (leg_h + arm_h) / 2, 0), (arm_w, arm_h - leg_h, d), fab, 0.04)


def coffee_table(root, p, w, h, d):
    wood = mat(p.get("material"), {"ph": "dark_wood", "tint": [0.55, 0.42, 0.33]})
    glass = builders.material("glass")
    b = 0.055
    for sx in (-1, 1):   # two sled-shaped ends and long rails, like the photo's
        x = sx * (w / 2 - b / 2)
        for sz in (-1, 1):
            soft(root, "leg", (x, h / 2, sz * (d / 2 - b / 2)), (b, h, b), wood, 0.006, 2)
        soft(root, "foot", (x, b / 2, 0), (b, b, d), wood, 0.006, 2)
        soft(root, "top_end", (x, h - b / 2, 0), (b, b, d), wood, 0.006, 2)
    for sz in (-1, 1):
        soft(root, "rail", (0, h - b / 2, sz * (d / 2 - b / 2)), (w - 2 * b, b, b), wood, 0.006, 2)
        soft(root, "low_rail", (0, 0.14, sz * (d / 2 - b / 2)), (w - 2 * b, 0.035, b), wood, 0.005, 2)
    builders.part(root, "top_glass", (0, h + 0.006, 0), (w + 0.02, 0.012, d + 0.02), glass)
    builders.part(root, "shelf_glass", (0, 0.16, 0), (w - 2 * b, 0.01, d - 2 * b), glass)


def kast(root, p, w, h, d):
    """An Amsterdam kast: plinth, a base with two drawers, two tall panelled doors, a stepped cornice."""
    paint = mat(p.get("material"), DEFAULT_PAINT)
    panel_m = mat(p["panels"], None) if p.get("panels") else paint   # (painted panels: Hindeloopen work)
    brass = builders.material(BRASS)
    plinth_h, cornice_h, base_h = 0.12, 0.24, 0.42
    soft(root, "plinth", (0, plinth_h / 2, 0), (w + 0.05, plinth_h, d + 0.03), paint, 0.01)
    body_h = h - plinth_h - cornice_h
    soft(root, "body", (0, plinth_h + body_h / 2, -0.01), (w, body_h, d - 0.02), paint, 0.006, 2)
    y = h - cornice_h
    for k, (dw, dh) in enumerate(((0.03, 0.05), (0.08, 0.06), (0.13, 0.05), (0.17, 0.08))):
        soft(root, "cornice", (0, y + dh / 2, 0.0), (w + dw, dh, d + dw * 0.6), paint, 0.008, 2)
        y += dh
    fz = d / 2 - 0.01
    by = plinth_h + 0.02
    for s in (-1, 1):   # drawers in the base
        soft(root, "drawer", (s * w / 4, by + base_h / 2, fz + 0.012), (w / 2 - 0.05, base_h - 0.05, 0.025), paint, 0.006, 2)
        builders.part(root, "pull", (s * w / 4, by + base_h / 2, fz + 0.03), (0.09, 0.02, 0.02), brass)
    dy0 = by + base_h + 0.02
    dh = h - cornice_h - dy0 - 0.03
    for s in (-1, 1):   # doors, each with three raised panels in a frame
        cx = s * w / 4
        soft(root, "door", (cx, dy0 + dh / 2, fz + 0.012), (w / 2 - 0.035, dh, 0.025), paint, 0.006, 2)
        pw = w / 2 - 0.2
        for k, frac in enumerate((0.42, 0.33, 0.25)):
            ph = (dh - 0.24) * frac
            py = dy0 + 0.08 + sum((dh - 0.24) * f for f in (0.42, 0.33, 0.25)[:k]) + 0.04 * k + ph / 2
            soft(root, "panel", (cx, py, fz + 0.032), (pw, ph, 0.025), panel_m, 0.018, 3, profile=0.35)
    builders.part(root, "stile", (0, dy0 + dh / 2, fz + 0.03), (0.035, dh, 0.02), paint)
    builders.part(root, "escutcheon", (0.03, dy0 + dh * 0.45, fz + 0.042), (0.02, 0.05, 0.006), brass)


def chest(root, p, w, h, d):
    wood = mat(p.get("material"), {"ph": "dark_wood", "tint": [0.35, 0.3, 0.27]})
    soft(root, "top", (0, h - 0.02, 0), (w + 0.03, 0.04, d + 0.03), wood, 0.008, 2)
    soft(root, "body", (0, (h - 0.04) / 2 + 0.04, 0), (w, h - 0.08, d), wood, 0.006, 2)
    soft(root, "drawer", (0, h * 0.62, d / 2 + 0.01), (w - 0.08, h * 0.3, 0.02), wood, 0.005, 2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            builders.part(root, "foot", (sx * (w / 2 - 0.04), 0.02, sz * (d / 2 - 0.04)), (0.06, 0.04, 0.06), wood)


def beam(root, p, w, h, d):
    soft(root, "beam", (0, h / 2, 0), (w, h, d), mat(p.get("material"), {"ph": "dark_wood", "tint": [0.3, 0.24, 0.2]}),
         0.015, 2)


def block(root, p, w, h, d):
    ob = builders.part(root, "block", (0, h / 2, 0), (w, h, d), mat(p.get("material"), "plaster"))
    if p.get("bevel"):
        bevel(ob, p["bevel"], 2)


def candlestick(root, p, w, h, d):
    """A turned brass candlestick with its candle (lit: a flame; the light itself is a RoomSpec light)."""
    brass = builders.material(p.get("material", BRASS))
    s = h / 0.62   # the profile is drawn for a 62 cm stick (candle included)
    prof = [(0.0, 0.0), (0.075, 0.0), (0.078, 0.012), (0.06, 0.03), (0.03, 0.05), (0.024, 0.07), (0.036, 0.09),
            (0.03, 0.11), (0.017, 0.13), (0.017, 0.2), (0.03, 0.215), (0.022, 0.23), (0.015, 0.25), (0.015, 0.3),
            (0.026, 0.31), (0.05, 0.325), (0.052, 0.335), (0.03, 0.34), (0.017, 0.36)]
    lathe(root, "stick", [(r * s, y * s) for r, y in prof], brass, segments=28)
    top = 0.36 * s
    wax = builders.material({"color": [0.82, 0.74, 0.62], "rough": 0.55, "noise": 0.05})
    candle_h = h - top
    builders.cyl(root, "candle", (0, top + candle_h / 2, 0), 0.016 * s, candle_h, wax)
    if p.get("lit", True):
        builders.cyl(root, "flame", (0, h + 0.022, 0), 0.007, 0.04,
                     builders.emissive("flame", (1.0, 0.55, 0.2), 40.0), r_top=0.001)


def jar_candle(root, p, w, h, d):
    glass = builders.material({"color": [0.5, 0.42, 0.3], "rough": 0.08, "transmission": 0.9, "noise": 0.0})
    wax = builders.material({"color": [0.8, 0.72, 0.6], "rough": 0.6, "noise": 0.0})
    builders.cyl(root, "jar", (0, h / 2, 0), w / 2, h, glass)
    builders.cyl(root, "wax", (0, h * 0.3, 0), w / 2 - 0.006, h * 0.6, wax)
    builders.cyl(root, "flame", (0, h * 0.6 + 0.02, 0), 0.006, 0.03, builders.emissive("flame", (1.0, 0.55, 0.2), 40.0),
                 r_top=0.001)


def curtain(root, p, w, h, d):
    """A gathered drape on a rod: folds across the width, pulled to one side at a tieback."""
    fab = mat(p.get("material"), {"color": [0.3, 0.29, 0.27], "rough": 0.9, "noise": 0.1})
    tie_y, side = p.get("tieback", 1.0), p.get("side", "left")
    cols, rows, amp = 64, 40, d * 0.45
    sgn = -1 if side == "left" else 1
    verts, faces = [], []
    for j in range(rows + 1):
        y = h * j / rows
        # how much of its width the drape keeps at this height: gathered at the tieback
        if y >= tie_y:
            keep = 0.35 + 0.65 * min(1.0, (y - tie_y) / max(0.3, (h - tie_y) * 0.6))
        else:
            keep = 0.35 + 0.25 * (1 - y / tie_y)
        for i in range(cols + 1):
            t = i / cols
            x0 = (t - 0.5) * w
            # pulled toward the tied side
            x = sgn * w / 2 + (x0 - sgn * w / 2) * keep
            folds = math.sin(t * math.pi * 2 * max(3, w / 0.16)) * amp * (0.6 + 0.4 * keep)
            verts.append((x, y, folds))
    for j in range(rows):
        for i in range(cols):
            a = j * (cols + 1) + i
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    ob = mesh("curtain", verts, faces, fab, root, smooth=True)
    sol = ob.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.008
    builders.cyl(root, "rod", (sgn * w * 0.0, h + 0.03, 0), 0.014, w * 1.2, builders.material(STEEL), horizontal=False).rotation_euler = (0, math.radians(90), 0)


def fireplace_classic(root, p, w, h, d):
    """A carved marble surround (fluted pilasters, frieze, a stepped mantel shelf), a cast-iron
    insert with an arched fire opening, and a few logs gone to embers."""
    stone = mat(p.get("material"), {"ph": "marble_01", "tint": [0.95, 0.88, 0.76]})
    iron = builders.material({"color": [0.015, 0.015, 0.016], "rough": 0.55, "metal": 0.7, "noise": 0.3, "noise_scale": 40.0, "bump": 0.3})
    soot = builders.material("soot")
    pil = 0.26
    soft(root, "hearth", (0, 0.02, 0.18), (w + 0.25, 0.04, d + 0.42), stone, 0.01)
    for s in (-1, 1):
        x = s * (w / 2 - pil / 2)
        soft(root, "plinth", (x, 0.04 + 0.1, 0.01), (pil + 0.04, 0.2, d + 0.02), stone, 0.01)
        soft(root, "pilaster", (x, 0.24 + (h - 0.6) / 2, 0), (pil, h - 0.6, d), stone, 0.012)
        for k in (-1, 0, 1):   # flutes
            builders.part(root, "flute", (x + k * 0.06, 0.24 + (h - 0.6) / 2, d / 2 + 0.002), (0.022, h - 0.75, 0.004), builders.material({"color": [0.5, 0.45, 0.38], "rough": 0.4}))
        soft(root, "capital", (x, h - 0.36 + 0.06, 0.01), (pil + 0.05, 0.12, d + 0.03), stone, 0.012)
    soft(root, "frieze", (0, h - 0.24, 0), (w - 2 * pil, 0.3, d - 0.02), stone, 0.01)
    soft(root, "tablet", (0, h - 0.24, d / 2), (0.36, 0.2, 0.03), stone, 0.012, 3)
    y = h - 0.09
    for dw, dh, dd in ((0.06, 0.035, 0.06), (0.12, 0.03, 0.1), (0.16, 0.055, 0.14)):
        soft(root, "shelf", (0, y + dh / 2, dd / 2 - 0.01), (w + dw, dh, d + dd), stone, 0.01, 2)
        y += dh
    ow, oh = w - 2 * pil, h - 0.6 - 0.12   # the opening between the pilasters, under the frieze
    oz = -d / 2 + 0.03
    builders.part(root, "back", (0, 0.04 + oh / 2, oz - 0.02), (ow, oh, 0.02), soot)
    # the iron insert: a panel filling the opening with an arched hole for the fire
    r = ow * 0.3
    spring = 0.04 + oh * 0.55
    arch = [(-r, 0.04)] + [(r * math.cos(a), spring + r * math.sin(a)) for a in
                           [math.pi - math.pi * i / 16 for i in range(17)]] + [(r, 0.04)]
    outer_l = [(-ow / 2, 0.04), (-ow / 2, 0.04 + oh), (0.0, 0.04 + oh)] + [pt for pt in reversed(arch[:9])]
    outer_r = [(0.0, 0.04 + oh), (ow / 2, 0.04 + oh), (ow / 2, 0.04)] + list(reversed(arch[8:]))
    frame = ((0, 0, d / 2 - 0.06), (1, 0, 0), (0, 1, 0), (0, 0, -1))
    for nm, poly in (("insert_l", outer_l), ("insert_r", outer_r)):
        ob = prism(root, nm, poly, 0.04, iron, frame)
        bevel(ob, 0.004, 1)
    builders.part(root, "firebox", (0, 0.04 + oh * 0.4, -0.02), (r * 2, oh * 0.8, d - 0.12), soot)
    builders.part(root, "grate", (0, 0.12, 0.0), (r * 1.6, 0.03, 0.25), iron)
    emb = builders.emissive("embers", (1.0, 0.28, 0.06), p.get("embers", 6.0))
    for k, (x, rot) in enumerate(((-0.08, 10), (0.07, -14), (0.0, 80))):
        lg = builders.cyl(root, "log", (x, 0.17 + 0.03 * (k == 2), 0.0), 0.045, 0.42, soot, horizontal=True)
        lg.rotation_euler[2] = math.radians(rot)
    builders.part(root, "embers", (0, 0.145, 0.0), (r * 1.4, 0.02, 0.2), emb)


def model(root, p, w, h, d):
    """A Poly Haven model (glTF), standing on the prop's spot, facing its front; "scale" or "fit"."""
    ref = p["model"]
    a = surfaces.asset(ref[3:] if isinstance(ref, str) else ref["ph"])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(surfaces.Path(a["_dir"]) / a["gltf"]))
    new = [o for o in bpy.data.objects if o not in before]
    tops = [o for o in new if o.parent is None]
    # measure in the prop's own (unrotated) frame
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    bpy.context.view_layer.update()
    for o in new:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            wc = o.matrix_world @ surfaces_vec(c)
            for i in range(3):
                lo[i], hi[i] = min(lo[i], wc[i]), max(hi[i], wc[i])
    size_b = [hi[i] - lo[i] for i in range(3)]   # Blender x, y (depth), z (height)
    k = p.get("scale", 1.0)
    if "fit" in p:   # fit inside [w, h, d] keeping proportions
        fw, fh, fd = p["fit"]
        k = min(fw / max(size_b[0], 1e-6), fh / max(size_b[2], 1e-6), fd / max(size_b[1], 1e-6))
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    holder = bpy.data.objects.new("model_" + a["id"], None)
    bpy.context.scene.collection.objects.link(holder)
    holder.parent = root
    holder.scale = (k, k, k)
    holder.location = (-cx * k, -cy * k, -lo[2] * k)
    if p.get("yaw_model"):
        holder.rotation_euler[2] = math.radians(p["yaw_model"])
    for o in tops:
        o.parent = holder
    if p.get("shadow", True) is False:   # a lamp's own glass and frame must not swallow its light
        for o in new:
            o.visible_shadow = False
    tint = p.get("tint")
    if tint:
        for o in new:
            for slot in getattr(o, "material_slots", []):
                m = slot.material
                if m and m.node_tree:
                    for n in m.node_tree.nodes:
                        if n.type == "BSDF_PRINCIPLED":
                            _tint_input(m.node_tree, n.inputs["Base Color"], tint)


def surfaces_vec(c):
    from mathutils import Vector
    return Vector(c)


def _tint_input(nt, sock, tint):
    if sock.is_linked:
        src = sock.links[0].from_socket
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = (*tint, 1)
        nt.links.new(src, mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], sock)
    else:
        c = sock.default_value
        sock.default_value = (c[0] * tint[0], c[1] * tint[1], c[2] * tint[2], 1)


def stair_open(root, p, w, h, d):
    """A carved open-tread stair (the staircase photo): thick oak treads with no risers between two
    stringers, wrought-iron balusters on the open side (every other one with a scroll), an oak
    handrail, and a turned newel at the foot. It rises toward local -z, as builders' stairs do;
    "rail_side" -1 puts the open side at local -x."""
    oak = mat(p.get("material"), {"ph": "dark_wood", "tint": [0.7, 0.5, 0.33], "scale": 0.5})
    iron = builders.material({"color": [0.02, 0.02, 0.022], "rough": 0.5, "metal": 0.6, "noise": 0.2})
    n = max(3, round(h / 0.2))
    run, rise = d / n, h / n
    side = p.get("rail_side", -1)
    for i in range(n):
        top = (i + 1) * rise
        zc = d / 2 - (i + 0.5) * run
        wide = 0.16 if i == 0 else 0.0   # the first step swells out under the newel
        soft(root, "tread", (side * wide / 2, top - 0.03, zc), (w + wide, 0.06, run + 0.035), oak, 0.01, 2)
    ang = math.degrees(math.atan2(h, d))
    L = math.hypot(h, d)
    for sx in (-1, 1):
        soft(root, "stringer", (sx * (w / 2 + 0.03), h / 2 - 0.08, 0), (0.05, 0.3, L), oak, 0.012, 2, rot_x=ang)
    xb = side * (w / 2 - 0.02)
    if p.get("solid"):   # the modern way (the concrete-hall photo): oak risers, and a plastered half wall for a rail
        for i in range(n):
            top = (i + 1) * rise
            zc = d / 2 - (i + 0.5) * run
            soft(root, "riser", (0, top - rise / 2 - 0.03, zc + run / 2 - 0.01), (w, rise - 0.05, 0.025), oak, 0.004, 1)
        wall_m = mat(p.get("wall"), {"color": [0.78, 0.77, 0.74], "rough": 0.9, "noise": 0.05})
        ob = soft(root, "half_wall", (xb, h / 2 + 0.45, 0), (0.1, 1.05, L), wall_m, 0.01, 2, rot_x=ang)
        soft(root, "capping", (xb, h / 2 + 0.98, 0), (0.14, 0.04, L), oak, 0.008, 2, rot_x=ang)
        return
    for i in range(1, n):
        top = (i + 1) * rise
        for k in (0.25, 0.75):
            zc = d / 2 - (i + k) * run
            hb = 0.9 - (k - 0.5) * run * h / d
            builders.cyl(root, "baluster", (xb, top + hb / 2, zc), 0.008, hb, iron)
            if (i * 2 + int(k > 0.5)) % 2 == 0:
                builders.cyl(root, "scroll", (xb, top + hb * 0.55, zc), 0.024, 0.07, iron, r_top=0.012)
    soft(root, "handrail", (xb, h / 2 + 0.92, 0), (0.065, 0.075, L), oak, 0.025, 3, rot_x=ang)
    zb = d / 2 - run * 0.5
    lathe(root, "newel", [(0.075, 0.0), (0.075, 0.12), (0.052, 0.18), (0.044, 0.55), (0.058, 0.62), (0.04, 0.72),
                          (0.05, 0.86), (0.068, 0.98), (0.07, 1.05), (0.0, 1.08)], oak, at=(xb, 0.0, zb), segments=22)


def runner(root, p, w, h, d):
    """A long woven runner (the Persian one in the staircase photo) lying on the floor."""
    m = mat(p.get("material"), {"pattern": "persian", "width": w})
    soft(root, "runner", (0, 0.006, 0), (w, 0.012, d), m, 0.004, 1)


def bookcase(root, p, w, h, d):
    """Built-in shelves to the ceiling, packed with books: one mesh per run of shelves (a few
    thousand spines cost nothing that way). Books lean, stand taller and shorter, and keep to a
    worn palette of cloth and leather; here and there a gap, a stack lying flat."""
    import random
    rng = random.Random(p.get("seed", 7))
    frame_m = mat(p.get("material"), {"color": [0.06, 0.065, 0.07], "rough": 0.5, "noise": 0.1})
    pitch = p.get("shelf_pitch", 0.36)
    n = max(2, int(h / pitch))
    t = 0.035
    soft(root, "back", (0, h / 2, -d / 2 + 0.01), (w, h, 0.02), frame_m, 0.003, 1)
    for sx in (-1, 1):
        soft(root, "side", (sx * (w / 2 - t / 2), h / 2, 0), (t, h, d), frame_m, 0.004, 1)
    uprights = max(1, int(w / 0.9))
    bay = w / uprights
    for k in range(1, uprights):
        soft(root, "upright", (-w / 2 + k * bay, h / 2, 0), (t, h, d), frame_m, 0.004, 1)
    palette = [(0.18, 0.05, 0.04), (0.06, 0.09, 0.07), (0.05, 0.06, 0.12), (0.22, 0.15, 0.08), (0.12, 0.1, 0.08),
               (0.3, 0.26, 0.2), (0.08, 0.04, 0.05), (0.03, 0.03, 0.03), (0.35, 0.3, 0.22), (0.14, 0.12, 0.05)]
    mats = [builders.material({"color": list(c), "rough": 0.75, "noise": 0.25, "noise_scale": 30.0}) for c in palette]
    for i in range(n + 1):
        y = i * h / n
        soft(root, "shelf", (0, y + t / 2, 0), (w, t, d), frame_m, 0.004, 1)
        if i == n or rng.random() < p.get("empty", 0.04):
            continue
        # one mesh per colour for this shelf row
        verts = {m: [] for m in range(len(mats))}
        faces = {m: [] for m in range(len(mats))}
        for b in range(uprights):
            x = -w / 2 + b * bay + t + 0.01
            end = -w / 2 + (b + 1) * bay - t / 2 - 0.01
            while x < end - 0.02:
                bw = rng.uniform(0.018, 0.055)
                if x + bw > end:
                    break
                bh = min(pitch - t - 0.03, rng.uniform(0.18, 0.3))
                bd = min(d - 0.04, rng.uniform(0.14, 0.24))
                lean = rng.random() < 0.05
                m = rng.randrange(len(mats))
                if rng.random() < 0.04:   # a gap
                    x += rng.uniform(0.05, 0.15)
                    continue
                y0 = y + t
                corners = [(x, y0, d / 2 - 0.02 - bd), (x + bw, y0, d / 2 - 0.02 - bd), (x + bw, y0, d / 2 - 0.02), (x, y0, d / 2 - 0.02)]
                tilt = bh * 0.25 if lean else 0.0
                top = [(cx + tilt, y0 + bh, cz) for cx, _, cz in corners]
                base = len(verts[m])
                verts[m] += corners + top
                faces[m] += [(base + 0, base + 1, base + 2, base + 3)[::-1], (base + 4, base + 5, base + 6, base + 7),
                             (base + 0, base + 1, base + 5, base + 4), (base + 1, base + 2, base + 6, base + 5),
                             (base + 2, base + 3, base + 7, base + 6), (base + 3, base + 0, base + 4, base + 7)]
                x += bw + (bh * 0.25 if lean else 0.0) + rng.uniform(0.0, 0.004)
        for m in verts:
            if verts[m]:
                mesh("books", verts[m], faces[m], mats[m], root)


def ladder(root, p, w, h, d):
    """A library ladder leaning on its rail: two oak stiles, round rungs, hooked over the top."""
    oak = mat(p.get("material"), {"ph": "dark_wood", "tint": [0.75, 0.55, 0.36], "scale": 0.4})
    lean = math.atan2(d, h)
    L = math.hypot(h, d)
    for sx in (-1, 1):
        ob = soft(root, "stile", (sx * (w / 2 - 0.025), h / 2, 0), (0.045, L, 0.06), oak, 0.008, 2)
        ob.rotation_euler[0] = lean
    for i in range(1, int(L / 0.3)):
        f = i * 0.3 / L
        y, z = f * h, d / 2 - f * d
        r = builders.cyl(root, "rung", (0, y, z), 0.016, w - 0.05, oak, horizontal=False)
        r.rotation_euler = (0, math.radians(90), 0)


def birdcage(root, p, w, h, d):
    """A tall brass bird cage hanging on a chain, full of stuffed parrots on their perches."""
    import random
    rng = random.Random(3)
    brass = builders.material(BRASS)
    r = w / 2
    lathe(root, "cage_base", [(0.0, 0.0), (r, 0.0), (r, 0.04), (r * 0.95, 0.06), (0.0, 0.06)], brass, segments=32)
    lathe(root, "cage_dome", [(r, h * 0.82), (r * 0.9, h * 0.9), (r * 0.6, h * 0.97), (0.08, h), (0.0, h)], brass, segments=32)
    for i in range(28):
        a = 2 * math.pi * i / 28
        builders.cyl(root, "bar", (r * math.cos(a), h * 0.42, r * math.sin(a)), 0.004, h * 0.82, brass)
    for k in range(3):
        y = 0.04 + k * (h * 0.78) / 3
        builders.cyl(root, "hoop", (0, y, 0), r * 1.01, 0.012, brass)
    builders.cyl(root, "chain", (0, h + p.get("chain", 1.5) / 2, 0), 0.008, p.get("chain", 1.5), brass)
    feathers = [(0.1, 0.32, 0.06), (0.45, 0.05, 0.03), (0.05, 0.12, 0.35), (0.55, 0.45, 0.05), (0.12, 0.35, 0.3)]
    for k in range(int(p.get("birds", 9))):
        y = 0.25 + rng.uniform(0, h * 0.6)
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.05, r * 0.7)
        c = rng.choice(feathers)
        m = builders.material({"color": list(c), "rough": 0.7, "noise": 0.4, "noise_scale": 60.0})
        bx, bz = rr * math.cos(a), rr * math.sin(a)
        body = lathe(root, "bird", [(0.0, 0.0), (0.03, 0.02), (0.045, 0.08), (0.04, 0.13), (0.025, 0.16), (0.032, 0.19),
                                     (0.02, 0.22), (0.0, 0.225)], m, at=(bx, y, bz), segments=10)
        tail = builders.cyl(root, "tail", (bx, y - 0.06, bz), 0.012, 0.14, m, r_top=0.003)
        builders.cyl(root, "perch", (bx, y - 0.005, bz), 0.006, 0.01, brass)


def round_table(root, p, w, h, d):
    """A round pedestal dining table: a dark top on a turned column and a spreading foot."""
    wood = mat(p.get("material"), {"ph": "dark_wood", "tint": [0.32, 0.24, 0.18], "scale": 0.5})
    r = w / 2
    lathe(root, "pedestal", [(0.3, 0.0), (0.3, 0.03), (0.12, 0.08), (0.07, 0.2), (0.06, h - 0.12), (0.12, h - 0.05),
                             (0.12, h - 0.04), (0.0, h - 0.04)], wood, segments=28)
    lathe(root, "top", [(0.0, h - 0.04), (r, h - 0.04), (r + 0.01, h - 0.02), (r, h), (0.0, h)], wood, segments=48)


def _superellipse(a, b, n=48, e=2.6):
    """A rounded-rectangle ring in the xz plane, half-lengths a (x) and b (z)."""
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2 / e), c), b * math.copysign(abs(s) ** (2 / e), s)))
    return out


def _loft(parent, name, rings, m, cap_first=False, cap_last=False, smooth=True):
    """Rings [(scale, y)] of one superellipse plan stacked into a skin (bottom to top or any order)."""
    plan = rings[0][2]
    n = len(plan)
    verts, faces = [], []
    for sc, y, _ in rings:
        verts += [(px * sc, y, pz * sc) for px, pz in plan]
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    if cap_first:
        faces.append(tuple(range(n))[::-1])
    if cap_last:
        last = (len(rings) - 1) * n
        faces.append(tuple(last + i for i in range(n)))
    return mesh(name, verts, faces, m, parent, smooth)


def bathtub(root, p, w, h, d):
    """A freestanding roll-top bath on four claw feet: cast iron painted outside, white enamel
    inside, its length along local x. "water": true fills it (dark, still)."""
    outside = mat(p.get("material"), {"color": [0.05, 0.07, 0.07], "rough": 0.35, "noise": 0.15})
    enamel = builders.material({"color": [0.78, 0.77, 0.73], "rough": 0.12, "noise": 0.12})
    iron = builders.material("iron")
    plan = _superellipse(w / 2 - 0.02, d / 2 - 0.02)
    foot = 0.11
    _loft(root, "tub_out", [(0.86, foot, plan), (0.95, foot + 0.12, plan), (0.99, h * 0.7, plan), (1.0, h - 0.05, plan),
                             (1.03, h - 0.03, plan), (1.02, h, plan), (0.95, h, plan)], outside, cap_first=True)
    _loft(root, "tub_in", [(0.95, h, plan), (0.92, h - 0.03, plan), (0.9, h * 0.6, plan), (0.8, foot + 0.1, plan)],
          enamel, cap_last=True)
    if p.get("water"):
        _loft(root, "tub_water", [(0.905, h - 0.13, plan)], builders.material("water"), cap_last=True, smooth=False)
    for sx in (-1, 1):
        for sz in (-1, 1):
            at = (sx * (w / 2 - 0.2), 0, sz * (d / 2 - 0.15))
            lathe(root, "claw", [(0.0, 0.0), (0.045, 0.0), (0.05, 0.02), (0.03, 0.05), (0.022, 0.08), (0.035, foot + 0.02),
                                 (0.0, foot + 0.02)], iron, at=at, segments=12)
    brass = builders.material(BRASS)
    builders.cyl(root, "spout", (-(w / 2 - 0.12), h + 0.12, 0), 0.016, 0.24, brass)
    builders.cyl(root, "spout_neck", (-(w / 2 - 0.2), h + 0.24, 0), 0.014, 0.16, brass, horizontal=True)


def basin(root, p, w, h, d):
    """A pedestal wash basin: a turned column and a deep round bowl, a brass tap at the back."""
    china = mat(p.get("material"), {"color": [0.8, 0.79, 0.75], "rough": 0.15, "noise": 0.1})
    r = w / 2
    lathe(root, "basin", [(0.13, 0.0), (0.13, 0.02), (0.09, 0.06), (0.065, 0.14), (0.06, h - 0.3), (0.08, h - 0.22),
                          (r * 0.7, h - 0.1), (r * 0.95, h - 0.03), (r, h), (r * 0.93, h + 0.005), (r * 0.82, h - 0.04),
                          (r * 0.5, h - 0.14), (0.0, h - 0.16)], china, at=(0, 0, 0), segments=36)
    brass = builders.material(BRASS)
    builders.cyl(root, "tap", (0, h + 0.07, -r * 0.82), 0.012, 0.14, brass)
    builders.cyl(root, "tap_spout", (0, h + 0.13, -r * 0.72), 0.01, 0.12, brass, horizontal=True)


def towel_rail(root, p, w, h, d):
    """A wooden towel horse: two splayed ends, two rails, a towel thrown over the top one."""
    wood = mat(p.get("material"), {"ph": "dark_wood", "tint": [0.55, 0.42, 0.3], "scale": 0.4})
    cloth = mat(p.get("cloth"), {"color": [0.55, 0.52, 0.47], "rough": 0.95, "noise": 0.25, "noise_scale": 40.0})
    for sx in (-1, 1):
        for sz in (-1, 1):
            leg = soft(root, "leg", (sx * w / 2, h / 2, sz * d / 4), (0.035, h * 1.02, 0.035), wood, 0.006, 2)
            leg.rotation_euler[0] = math.radians(-sz * 6)
        builders.part(root, "foot", (sx * w / 2, 0.02, 0), (0.04, 0.04, d), wood)
    for y in (h - 0.02, h * 0.45):
        r = builders.cyl(root, "rail", (0, y, 0), 0.014, w, wood, horizontal=True)
        r.rotation_euler = (0, 0, math.radians(90))
    tw = w * 0.62
    for sz in (-1, 1):   # the towel hangs down both sides of the top rail
        soft(root, "towel", (0.04, h - 0.32, sz * 0.03), (tw, 0.6, 0.02), cloth, 0.008, 2)
    soft(root, "towel_fold", (0.04, h, 0), (tw, 0.03, 0.07), cloth, 0.012, 2)


# ── A pitched roof (the attic) ────────────────────────────────────────────────────
def roof_frames(spec):
    """The two slopes of a gabled roof: for each, (eave side, origin, U along the ridge, S up the
    slope, N out of the room, length along U, length up the slope, slope's start at the knee wall).
    roof.axis is the ridge's direction ("z": the gables are the north and south walls)."""
    r = spec["roof"]
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    h, eave, t = spec["height"], r["eave"], builders.WALL_T
    out = []
    if r.get("axis", "z") == "z":
        half = (x1 - x0) / 2
        k = (h - eave) / half
        for side, xe, sx in (("west", x0, -1.0), ("east", x1, 1.0)):
            o = (xe + sx * t, eave - k * t, z0 - t)
            run, rise = half + t, h - (eave - k * t)
            L = math.hypot(run, rise)
            S = (-sx * run / L, rise / L, 0.0)
            N = (sx * rise / L, run / L, 0.0)
            out.append((side, o, (0.0, 0.0, 1.0), S, N, (z1 - z0) + 2 * t, L, t * L / run))
    else:
        half = (z1 - z0) / 2
        k = (h - eave) / half
        for side, ze, sz in (("north", z0, -1.0), ("south", z1, 1.0)):
            o = (x0 - t, eave - k * t, ze + sz * t)
            run, rise = half + t, h - (eave - k * t)
            L = math.hypot(run, rise)
            S = (0.0, rise / L, -sz * run / L)
            N = (0.0, run / L, sz * rise / L)
            out.append((side, o, (1.0, 0.0, 0.0), S, N, (x1 - x0) + 2 * t, L, t * L / run))
    return out


def _slab(name, frame, u0, u1, s0, s1, n0, n1, m):
    """A box in a slope's frame (u along the ridge, s up the slope, n out of the room), UVs in metres
    along u and s so planks run true on the slope."""
    o, U, S, N = frame
    def at(u, s, n):
        return g2b(tuple(o[i] + U[i] * u + S[i] * s + N[i] * n for i in range(3)))
    c = [(u, s, n) for u in (u0, u1) for s in (s0, s1) for n in (n0, n1)]
    verts = [at(*q) for q in c]
    faces = [(0, 2, 6, 4), (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6), (0, 1, 3, 2), (4, 6, 7, 5)]
    uvs = []
    for f in faces:
        uvs.append([(c[i][0], c[i][1] + c[i][2]) for i in f])
    return builders._mesh_object(name, verts, faces, uvs, m)


def roof(spec):
    """The attic's roof, seen from inside: two sloping slabs of boards from the knee walls up to the
    ridge (with holes for roof lights, glazed), and the timber that carries them: a pair of rafters
    and a collar tie at each truss, a king post up to the ridge beam, a purlin halfway up each
    slope and a wall plate on each knee wall. Spec: "roof": {"axis": "z", "eave": 1.1,
    "material": ..., "timber": ..., "trusses": [z, ...] or {"spacing": s}, "collar": 2.4,
    "skylights": [{"side": "east", "center": 2.0, "width": 0.8, "from": 0.9, "to": 2.0}]}."""
    r = spec["roof"]
    boards = builders.material(r.get("material", "dark_wood"))
    timber = builders.material(r.get("timber", "dark_wood"))
    glass = builders.material("glass")
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    h, eave, t = spec["height"], r["eave"], builders.WALL_T
    axis_z = r.get("axis", "z") == "z"
    lo, hi = (z0, z1) if axis_z else (x0, x1)
    tr = r.get("trusses", {"spacing": 1.5})
    if isinstance(tr, dict):
        n = max(1, int((hi - lo) / tr["spacing"]))
        trusses = [(hi - lo) * (i + 0.5) / n for i in range(n)]
    else:
        trusses = list(tr)
    thick = 0.18
    for side, o, U, S, N, Lu, Ls, s_knee in roof_frames(spec):
        frame = (o, U, S, N)
        holes = [(sk["center"] + t - sk["width"] / 2, sk["center"] + t + sk["width"] / 2,
                  s_knee + sk["from"], s_knee + sk["to"]) for sk in r.get("skylights", []) if sk["side"] == side]
        cuts = sorted({0.0, Lu} | {v for hh in holes for v in hh[:2]})
        for ua, ub in zip(cuts, cuts[1:]):
            mid = (ua + ub) / 2
            gaps = sorted((hh[2], hh[3]) for hh in holes if hh[0] <= mid <= hh[1])
            s = 0.0
            for ga, gb in gaps + [(Ls + 0.02, Ls + 0.02)]:
                if ga > s:
                    _slab("roof_" + side, frame, ua, ub, s, min(ga, Ls + 0.02), 0.0, thick, boards)
                s = gb
        for ua, ub, sa, sb in holes:   # the roof light: a glazed pane in a timber lining
            _slab("skylight_glass", frame, ua, ub, sa, sb, thick * 0.6, thick * 0.6 + 0.01, glass)
            for (a, b, c, e) in ((ua - 0.06, ua, sa - 0.06, sb + 0.06), (ub, ub + 0.06, sa - 0.06, sb + 0.06),
                                 (ua, ub, sa - 0.06, sa), (ua, ub, sb, sb + 0.06)):
                _slab("skylight_lining", frame, a, b, c, e, -0.1, thick, timber)
        sm = (s_knee + Ls) / 2
        _slab("purlin", frame, 0.0, Lu, sm - 0.08, sm + 0.08, -0.4, -0.2, timber)
        for u in trusses:
            _slab("rafter", frame, u + t - 0.07, u + t + 0.07, s_knee - 0.1, Ls, -0.2, 0.0, timber)
    # wall plates, the ridge beam, the collar ties and king posts, in room coordinates
    half = (x1 - x0) / 2 if axis_z else (z1 - z0) / 2
    k = (h - eave) / half
    collar = r.get("collar", h - 1.5)
    reach = half - (collar - eave) / k + 0.1    # where the collar meets the rafters, from the mid line
    def box(name, a0, a1, y0, y1, b0, b1):
        """a: across the ridge, b: along it (room coordinates, mid line at a = 0)."""
        if axis_z:
            mx = (x0 + x1) / 2
            return builders.box_aabb(name, (mx + a0, y0, b0), (mx + a1, y1, b1), timber)
        mz = (z0 + z1) / 2
        return builders.box_aabb(name, (b0, y0, mz + a0), (b1, y1, mz + a1), timber)
    box("ridge", -0.08, 0.08, h - 0.32, h + 0.02, lo - t, hi + t)
    box("wall_plate", -half, -half + 0.16, eave - 0.16, eave + 0.02, lo, hi)
    box("wall_plate", half - 0.16, half, eave - 0.16, eave + 0.02, lo, hi)
    for u in trusses:
        b = lo + u
        box("collar", -reach, reach, collar, collar + 0.2, b - 0.07, b + 0.07)
        box("king_post", -0.07, 0.07, collar + 0.2, h - 0.3, b - 0.07, b + 0.07)


PROPS = {"bookcase": bookcase, "ladder": ladder, "birdcage": birdcage, "round_table": round_table,
         "stair_open": stair_open, "runner": runner, "sofa": sofa, "armchair": armchair, "coffee_table": coffee_table, "kast": kast, "chest": chest,
         "beam": beam, "block": block, "candlestick": candlestick, "jar_candle": jar_candle, "curtain": curtain,
         "fireplace_classic": fireplace_classic, "model": model,
         "bathtub": bathtub, "basin": basin, "towel_rail": towel_rail}


def build_prop(p, room_h):
    """A kit prop at its spot (pos = bottom-centre of its footprint, yaw about up)."""
    size = p.get("size", [0.5, 0.5, 0.5])
    root = builders.empty_at(f"prop_{p['type']}", p["pos"], p.get("yaw", 0.0))
    if p.get("pitch") or p.get("roll"):   # knocked over: tipped about its own x (pitch) and front-to-back axis (roll)
        root.rotation_euler = (math.radians(p.get("pitch", 0.0)), math.radians(-p.get("roll", 0.0)), math.radians(p.get("yaw", 0.0)))
    PROPS[p["type"]](root, p, *size)
    return root


# ── Arched openings ──────────────────────────────────────────────────────────────
def arch_opening(spec, side, op):
    """A round-headed window or glazed door: the wall above the arc filled back in (spandrels),
    a black steel frame and glazing bars, and a brick arch ring on the inside face."""
    u0, u1, v0, v1 = builders._opening_span(op)
    t = builders.WALL_T
    r = (u1 - u0) / 2
    uc, ys = (u0 + u1) / 2, v1 - r
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    # wall frame: u along the wall from its min corner, v up, w outward (into the wall)
    frames = {"north": ((x0, 0, z0), (1, 0, 0), (0, 1, 0), (0, 0, -1)),
              "south": ((x0, 0, z1), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
              "west": ((x0, 0, z0), (0, 0, 1), (0, 1, 0), (-1, 0, 0)),
              "east": ((x1, 0, z0), (0, 0, 1), (0, 1, 0), (1, 0, 0))}
    frame = frames[side]
    root = bpy.data.objects.new("arch_" + side, None)
    bpy.context.scene.collection.objects.link(root)
    wall = builders.material(spec["materials"]["wall"])
    seg = 24
    arc = [(uc + r * math.cos(math.pi - math.pi * i / seg), ys + r * math.sin(math.pi - math.pi * i / seg)) for i in range(seg + 1)]
    # spandrels: the wall between the arc and the opening's square top (two pieces, each star-shaped)
    left = [(u0, v1), (u0, ys)] + arc[: seg // 2 + 1]
    right = [(uc, v1)] + arc[seg // 2:] + [(u1, v1)]
    prism(root, "spandrel_l", left, t, wall, frame)
    prism(root, "spandrel_r", right, t, wall, frame)
    steel = builders.material(op.get("frame", STEEL))
    glass = builders.material("glass")
    gw = op.get("glass_at", 0.12)   # how deep in the wall the glass sits
    fw = 0.05   # frame member width
    # glass: rectangle below the springing line plus the half disc
    glass_poly = [(u0, v0), (u1, v0)] + [(uc + r * math.cos(math.pi * i / seg), ys + r * math.sin(math.pi * i / seg)) for i in range(seg + 1)]
    prism(root, "glass", glass_poly, 0.01, glass, (tuple(frame[0][i] + frame[3][i] * gw for i in range(3)), frame[1], frame[2], frame[3]))
    def bar(name, a, b, width=0.035, depth=0.05):
        # a straight glazing bar from a to b (u, v), centred on the glass plane
        du, dv = b[0] - a[0], b[1] - a[1]
        L = math.hypot(du, dv)
        nu, nv = -dv / L * width / 2, du / L * width / 2
        poly = [(a[0] + nu, a[1] + nv), (a[0] - nu, a[1] - nv), (b[0] - nu, b[1] - nv), (b[0] + nu, b[1] + nv)]
        o = tuple(frame[0][i] + frame[3][i] * (gw - depth / 2) for i in range(3))
        prism(root, name, poly, depth, steel, (o, frame[1], frame[2], frame[3]))
    # the outer frame: jambs, sill, and the arc
    bar("jamb_l", (u0 + fw / 2, v0), (u0 + fw / 2, ys), fw, 0.07)
    bar("jamb_r", (u1 - fw / 2, v0), (u1 - fw / 2, ys), fw, 0.07)
    bar("sill", (u0, v0 + fw / 2), (u1, v0 + fw / 2), fw, 0.07)
    rr = r - fw / 2
    for i in range(seg):
        a0, a1 = math.pi * i / seg, math.pi * (i + 1) / seg
        bar("arc", (uc + rr * math.cos(a0), ys + rr * math.sin(a0)), (uc + rr * math.cos(a1), ys + rr * math.sin(a1)), fw, 0.07)
    # glazing bars: mullions, a transom at the springing line, and spokes in the fanlight
    n_mull = op.get("mullions", 1)
    for k in range(1, n_mull + 1):
        u = u0 + (u1 - u0) * k / (n_mull + 1)
        bar("mullion", (u, v0), (u, ys + math.sqrt(max(0.0, r * r - (u - uc) ** 2)) - fw / 2), 0.04, 0.06)
    bar("transom", (u0, ys), (u1, ys), 0.04, 0.06)
    for k in range(op.get("transoms", 2)):
        v = v0 + (ys - v0) * (k + 1) / (op.get("transoms", 2) + 1)
        bar("transom_low", (u0, v), (u1, v), 0.025, 0.04)
    for a in (math.radians(45), math.radians(135)):
        bar("spoke", (uc, ys), (uc + rr * math.cos(a), ys + rr * math.sin(a)), 0.025, 0.04)
    if op.get("brick_arch"):
        brick = builders.material(op["brick_arch"])
        ring = []
        R0, R1 = r + 0.0, r + 0.14
        for i in range(seg + 1):
            a = math.pi * i / seg
            ring.append((uc + R1 * math.cos(a), ys + R1 * math.sin(a)))
        for i in range(seg, -1, -1):
            a = math.pi * i / seg
            ring.append((uc + R0 * math.cos(a), ys + R0 * math.sin(a)))
        # the ring is not star-shaped from one point: build it as quads
        for i in range(seg):
            a0, a1 = math.pi * i / seg, math.pi * (i + 1) / seg
            q = [(uc + R0 * math.cos(a0), ys + R0 * math.sin(a0)), (uc + R1 * math.cos(a0), ys + R1 * math.sin(a0)),
                 (uc + R1 * math.cos(a1), ys + R1 * math.sin(a1)), (uc + R0 * math.cos(a1), ys + R0 * math.sin(a1))]
            prism(root, "voussoir", q, 0.03, brick, (frame[0], frame[1], frame[2], tuple(-x for x in frame[3])))
        for uu in (u0 - 0.14, u1):
            prism(root, "brick_jamb", [(uu, v0), (uu + 0.14, v0), (uu + 0.14, ys), (uu, ys)], 0.03, brick,
                  (frame[0], frame[1], frame[2], tuple(-x for x in frame[3])))
    return root


# ── Outside: the canal and the houses across it ──────────────────────────────────
def build_exterior(spec, rng):
    """{"side": "south", "canal": 12, "bricks": [...], "lit": 0.06, "drop": 0}: outside that wall, a
    pavement, the canal, the far quay, and a row of gabled canal houses facing us, a few windows lit
    ("drop": the street that far below the room's floor, for a room upstairs)."""
    ext = spec["exterior"]
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    side = ext.get("side", "north")
    if ext.get("lightwell"):
        return _lightwell(spec, rng, ext, side)
    if side not in ("north", "south"):
        raise NotImplementedError("exterior side " + side)
    if ext.get("garden"):
        return _garden(spec, rng, ext, side)
    sgn = -1.0 if side == "north" else 1.0   # away from the house
    wall = z0 if side == "north" else z1
    t = builders.WALL_T
    width = ext.get("canal", 12.0)
    water = builders.material("water")
    stone = builders.material(ext.get("quay", {"color": [0.12, 0.12, 0.12], "rough": 0.8, "noise": 0.3}))
    brick_keys = ext.get("bricks", ["ph:brick_wall_003"])
    lit = builders.emissive("window", (1.0, 0.55, 0.25), 3.0)
    dark_glass = builders.material({"color": [0.01, 0.012, 0.016], "rough": 0.08, "noise": 0.0})

    drop = ext.get("drop", 0.0)   # the street this far below the room's floor (an attic looks down on it)

    def slab(name, za, zb, y0, y1, m, xa=x0 - 40, xb=x1 + 40):
        o = builders.box_aabb(name, (xa, y0 - drop, min(za, zb)), (xb, y1 - drop, max(za, zb)), m)
        return o

    zw = wall + sgn * t                          # the house's outer face
    zq = zw + sgn * ext.get("pavement", 2.5)     # our quay's edge
    slab("street", zw, zq, -0.25, 0.0, stone)
    slab("canal", zq, zq + sgn * width, -1.6, -1.58, water)
    slab("quay_wall", zq, zq + sgn * 0.3, -1.6, 0.0, builders.material(brick_keys[0]))
    zf = zq + sgn * (width + 3.0)                # the far houses' fronts
    slab("far_quay", zq + sgn * width, zf, -1.6, 0.0, stone)
    x = x0 - 30
    while x < x1 + 30:
        w = rng.uniform(5.0, 7.0)
        hh = rng.uniform(12.0, 16.0)
        m = builders.material({"ph": rng.choice(brick_keys)[3:], "tint": [rng.uniform(0.18, 0.32)] * 3})
        f = slab("house", zf, zf + sgn * 10, 0, hh, m, x, x + w - 0.08)
        f.visible_shadow = False
        g = slab("gable", zf, zf + sgn * 10, hh, hh + 2.6, m, x + w * 0.2, x + w * 0.8)
        g.visible_shadow = False
        for fl in range(4):
            for k in range(3):
                wx = x + 0.9 + k * (w - 1.8) / 2
                y0 = 1.0 + fl * 3.1
                if y0 + 2 > hh:
                    continue
                win = slab("win", zf - sgn * 0.001, zf - sgn * 0.02, y0, y0 + 1.9,
                           lit if rng.random() < ext.get("lit", 0.06) else dark_glass, wx - 0.42, wx + 0.42)
                win.visible_shadow = False
        x += w


def _garden(spec, rng, ext, side):
    """Behind the house: a walled back garden under the moon, a few bare trees, and the backs of
    the next street's houses beyond, a window or two lit."""
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    sgn = -1.0 if side == "north" else 1.0
    zw = (z0 if side == "north" else z1) + sgn * builders.WALL_T
    depth = ext.get("depth", 9.0)
    ground = builders.material({"color": [0.02, 0.025, 0.018], "rough": 0.95, "noise": 0.5, "noise_scale": 3.0})
    brick = builders.material({"ph": ext.get("brick", "red_brick_03"), "tint": [0.35, 0.3, 0.28]})
    bark = builders.material({"color": [0.03, 0.025, 0.02], "rough": 0.9, "noise": 0.4, "noise_scale": 12.0})

    def box(name, za, zb, y0, y1, m, xa=x0 - 12, xb=x1 + 12):
        return builders.box_aabb(name, (xa, y0, min(za, zb)), (xb, y1, max(za, zb)), m)

    box("lawn", zw, zw + sgn * depth, -0.2, 0.0, ground)
    box("garden_wall", zw + sgn * depth, zw + sgn * (depth + 0.3), 0.0, 3.2, brick)
    for k in range(int(ext.get("trees", 4))):
        tx = rng.uniform(x0 - 4, x1 + 4)
        tz = zw + sgn * rng.uniform(2.5, depth - 1.0)
        th = rng.uniform(5.0, 8.0)
        trunk = builders.box_aabb("trunk", (tx - 0.14, 0.0, tz - 0.14), (tx + 0.14, th, tz + 0.14), bark)
        trunk.visible_shadow = True
        for b in range(5):   # bare limbs
            a = rng.uniform(0, 2 * math.pi)
            y = rng.uniform(th * 0.45, th * 0.9)
            L = rng.uniform(1.0, 2.2)
            lb = builders.box_aabb("limb", (tx - 0.05, y, tz - 0.05), (tx + 0.05, y + L, tz + 0.05), bark)
            lb.rotation_euler = (rng.uniform(-0.7, 0.7), rng.uniform(-0.7, 0.7), a)
    zb = zw + sgn * (depth + 6.0)
    lit = builders.emissive("window", (1.0, 0.55, 0.25), 2.5)
    dark = builders.material({"color": [0.01, 0.012, 0.016], "rough": 0.1, "noise": 0.0})
    x = x0 - 14
    while x < x1 + 14:
        w = rng.uniform(5.0, 7.0)
        hh = rng.uniform(11.0, 14.0)
        m = builders.material({"ph": ext.get("brick", "red_brick_03"), "tint": [rng.uniform(0.12, 0.2)] * 3})
        h_ = box("back_house", zb, zb + sgn * 8, 0, hh, m, x, x + w - 0.1)
        h_.visible_shadow = False
        for fl in range(3):
            for kk in range(2):
                wx = x + 1.2 + kk * (w - 2.4)
                win = box("win", zb - sgn * 0.01, zb - sgn * 0.03, 1.2 + fl * 3.2, 3.0 + fl * 3.2,
                          lit if rng.random() < ext.get("lit", 0.08) else dark, wx - 0.45, wx + 0.45)
                win.visible_shadow = False
        x += w


def _lightwell(spec, rng, ext, side):
    """Outside a basement window: a narrow shaft open to the sky, wet tiles at the bottom, brick
    climbing to street level, a few plants in pots, rain running down the far wall."""
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    t = builders.WALL_T
    depth = ext.get("depth", 1.6)
    top = ext.get("top", 6.0)
    brick = builders.material({"ph": ext.get("brick", "red_brick_03"), "tint": [0.4, 0.34, 0.3]})
    tiles = builders.material({"color": [0.08, 0.085, 0.09], "rough": 0.15, "noise": 0.3, "noise_scale": 5.0})
    if side == "west":
        xa, xb = x0 - t - depth, x0 - t
        builders.box_aabb("well_floor", (xa, -0.3, z0), (xb, -0.05, z1), tiles)
        builders.box_aabb("well_wall", (xa - 0.3, -0.3, z0 - 0.3), (xa, top, z1 + 0.3), brick)
        builders.box_aabb("well_end_n", (xa, -0.3, z0 - 0.3), (xb, top, z0), brick)
        builders.box_aabb("well_end_s", (xa, -0.3, z1), (xb, top, z1 + 0.3), brick)
        spots = [(xa + depth * 0.4, z0 + (z1 - z0) * f) for f in (0.2, 0.55, 0.85)]
    elif side == "east":
        xa, xb = x1 + t, x1 + t + depth
        builders.box_aabb("well_floor", (xa, -0.3, z0), (xb, -0.05, z1), tiles)
        builders.box_aabb("well_wall", (xb, -0.3, z0 - 0.3), (xb + 0.3, top, z1 + 0.3), brick)
        builders.box_aabb("well_end_n", (xa, -0.3, z0 - 0.3), (xb, top, z0), brick)
        builders.box_aabb("well_end_s", (xa, -0.3, z1), (xb, top, z1 + 0.3), brick)
        spots = [(xb - depth * 0.4, z0 + (z1 - z0) * f) for f in (0.2, 0.55, 0.85)]
    else:
        raise NotImplementedError("light well on " + side)
    for (px, pz), kind in zip(spots, ext.get("plants", ["potted_plant_02", "potted_plant_01", "potted_plant_02"])):
        try:
            ref = kind if kind.startswith("ph:") else "ph:" + kind
            model(builders.empty_at("plant", (px, -0.05, pz), rng.uniform(0, 360)), {"model": ref, "scale": 0.8}, 0, 0, 0)
        except FileNotFoundError:
            pass


def stair_stub(spec, side, op):
    """Beyond a door that leads down (the cellar door): a short landing and a flight of worn steps
    going down into the dark, walled in brick, so the open doorway shows where it goes."""
    u0, u1, v0, v1 = builders._opening_span(op)
    t = builders.WALL_T
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    frames = {"north": ((x0, 0, z0), (1, 0, 0), (0, 0, -1)), "south": ((x0, 0, z1), (1, 0, 0), (0, 0, 1)),
              "west": ((x0, 0, z0), (0, 0, 1), (-1, 0, 0)), "east": ((x1, 0, z0), (0, 0, 1), (1, 0, 0))}
    o, U, Wd = frames[side]

    def box(name, ua, ub, ya, yb, wa, wb, m):
        pts = [tuple(o[i] + U[i] * u + Wd[i] * w for i in range(3)) for u in (ua, ub) for w in (wa, wb)]
        lo = (min(p[0] for p in pts), ya, min(p[2] for p in pts))
        hi = (max(p[0] for p in pts), yb, max(p[2] for p in pts))
        return builders.box_aabb(name, lo, hi, m)

    brick = builders.material("brick")
    step_m = builders.material({"color": [0.07, 0.05, 0.035], "rough": 0.7, "noise": 0.3})
    landing = 0.35
    n, rise, run = 12, 0.21, 0.27
    end = t + landing + n * run + 0.3
    box("landing", u0 - 0.05, u1 + 0.05, -0.2, 0.0, t, t + landing, step_m)
    for i in range(n):
        top = -(i + 1) * rise
        wa = t + landing + i * run
        box("step", u0 - 0.05, u1 + 0.05, top - 0.2, top, wa, wa + run + 0.02, step_m)
    for ua, ub in ((u0 - 0.35, u0 - 0.05), (u1 + 0.05, u1 + 0.35)):
        box("stair_wall", ua, ub, -n * rise - 0.5, v1 + 0.4, t, end, brick)
    box("stair_end", u0 - 0.35, u1 + 0.35, -n * rise - 0.5, v1 + 0.4, end, end + 0.3, brick)
    box("stair_ceiling", u0 - 0.35, u1 + 0.35, v1 + 0.1, v1 + 0.4, t, end + 0.3, brick)
    # the cellar's water, come up the stairs: a black sheet catching a little cold light from below
    box("stair_water", u0 - 0.05, u1 + 0.05, -n * rise * 0.55, -n * rise * 0.55 + 0.01, t + landing + n * run * 0.45, end,
        builders.material("water"))
    ld = bpy.data.lights.new("stair_glow", "POINT")
    ld.color = (0.45, 0.75, 0.68)
    ld.energy = 6.0
    ld.shadow_soft_size = 0.4
    glow = bpy.data.objects.new("stair_glow", ld)
    bpy.context.scene.collection.objects.link(glow)
    c = tuple(o[i] + U[i] * (u0 + u1) / 2 + Wd[i] * (end - 0.6) for i in range(3))
    glow.location = g2b((c[0], -n * rise * 0.55 + 0.35, c[2]))
