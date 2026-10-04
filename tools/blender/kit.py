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
            soft(root, "panel", (cx, py, fz + 0.032), (pw, ph, 0.025), paint, 0.018, 3, profile=0.35)
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


PROPS = {"sofa": sofa, "armchair": armchair, "coffee_table": coffee_table, "kast": kast, "chest": chest,
         "beam": beam, "block": block, "candlestick": candlestick, "jar_candle": jar_candle, "curtain": curtain,
         "fireplace_classic": fireplace_classic, "model": model}


def build_prop(p, room_h):
    """A kit prop at its spot (pos = bottom-centre of its footprint, yaw about up)."""
    size = p.get("size", [0.5, 0.5, 0.5])
    root = builders.empty_at(f"prop_{p['type']}", p["pos"], p.get("yaw", 0.0))
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
    """{"side": "north", "canal": 12, "facades": true}: water, a quay, and a row of gabled canal
    houses across it, a few windows lit."""
    ext = spec["exterior"]
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    side = ext.get("side", "north")
    t = builders.WALL_T
    width = ext.get("canal", 12.0)
    water = builders.material("water")
    stone = builders.material(ext.get("quay", {"color": [0.12, 0.12, 0.12], "rough": 0.8, "noise": 0.3}))
    brick_keys = ext.get("bricks", ["ph:brick_wall_003"])
    lit = builders.emissive("window", (1.0, 0.55, 0.25), 3.0)
    dark_glass = builders.material({"color": [0.01, 0.012, 0.016], "rough": 0.08, "noise": 0.0})
    if side != "north":
        raise NotImplementedError("exterior side " + side)
    zq = z0 - t - ext.get("pavement", 2.5)   # our side's quay edge
    builders.box_aabb("street", (x0 - 40, -0.25, zq), (x1 + 40, 0.0, z0 - t), stone)
    builders.box_aabb("canal", (x0 - 40, -1.6, zq - width), (x1 + 40, -1.58, zq), water)
    builders.box_aabb("quay_wall", (x0 - 40, -1.6, zq - 0.3), (x1 + 40, 0.0, zq), builders.material(brick_keys[0]))
    zf = zq - width - 3.0   # the far quay, then the far houses' fronts
    builders.box_aabb("far_quay", (x0 - 40, -1.6, zf), (x1 + 40, 0.0, zq - width), stone)
    x = x0 - 30
    while x < x1 + 30:
        w = rng.uniform(5.0, 7.0)
        hh = rng.uniform(12.0, 16.0)
        m = builders.material({"ph": rng.choice(brick_keys)[3:], "tint": [rng.uniform(0.18, 0.32)] * 3})
        f = builders.box_aabb("house", (x, 0, zf - 10), (x + w - 0.08, hh, zf), m)
        f.visible_shadow = False
        g = builders.box_aabb("gable", (x + w * 0.2, hh, zf - 10), (x + w * 0.8, hh + 2.6, zf), m)
        g.visible_shadow = False
        for fl in range(4):
            for k in range(3):
                wx = x + 0.9 + k * (w - 1.8) / 2
                y0 = 1.0 + fl * 3.1
                if y0 + 2 > hh:
                    continue
                win = builders.box_aabb("win", (wx - 0.42, y0, zf + 0.001), (wx + 0.42, y0 + 1.9, zf + 0.02),
                                        lit if rng.random() < ext.get("lit", 0.06) else dark_glass)
                win.visible_shadow = False
        x += w
