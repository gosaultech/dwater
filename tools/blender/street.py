# damned_waters/tools/blender/street.py
# Purpose: the outdoor set kit (Blender side), for RoomSpecs marked "outdoor": the street and quay
# under him, the canal, the houses on both banks and the shops in them, and the things of an
# Amsterdam canal at night. Built like the rooms: matched to reference photos, dressed in CC0
# scans from Poly Haven (old Dutch brick, painted window frames, bluestone sills, wet brick
# pavers, roof tiles, plane-tree bark), lit by its street lamps, its lit windows and its shops.
#   * house fronts laid out by tools/pipeline/facade.py: brick (leaning forward a little, as
#     Amsterdam's do), white sash windows with glass that reflects the sky, real rooms behind the
#     lit ones (patches of CC0 interior panoramas), moulded cornices on brackets, gables with stone
#     coping, a finial and a hoist beam, chimneys, painted doors on stone stoops;
#   * shopfronts on the ground floor: a glazed front, a lit sign, an awning, a blade sign, the shop
#     inside, and its light spilling onto the pavement (the power is still on; nobody is there);
#   * street lamps with their lanterns alight, Amsterdammertjes (the brown bollards with three
#     crosses), black upright bikes, plane trees (bare, or with October's last leaves), railings,
#     patio heaters, a houseboat, a rowing boat, a hump bridge with bulbs round its arches.
# Coordinates are a prop's local Godot frame (x right, y up, z front), as in builders.part().
#
# ELI5: kit.py furnishes rooms; this furnishes a street. The far bank is real houses, not a painted
# backdrop, so a window across the water can be lit and its light can wobble in the canal.
import math
import random
from pathlib import Path

import bpy

import builders
import facade as layout
import kit
from roomspec import g2b

FONTS = Path("/usr/share/fonts/truetype/dejavu")   # DejaVu (free licence): the shop signs' lettering
BRICKS = ["medieval_red_brick", "red_bricks_04", "brick_wall_09", "brick_wall_10", "dark_brick_wall"]
TRIM = {"ph": "distressed_painted_planks", "tint": [0.95, 0.94, 0.9], "scale": 0.4}
STONE = {"ph": "large_sandstone_blocks", "tint": [0.5, 0.52, 0.55], "scale": 0.5}
ROOF = {"ph": "grey_roof_tiles", "tint": [0.5, 0.5, 0.53]}
IRON = {"color": [0.02, 0.02, 0.022], "rough": 0.45, "metal": 0.7, "noise": 0.1}
DOORS = [[0.05, 0.16, 0.11], [0.05, 0.05, 0.055], [0.32, 0.05, 0.04], [0.07, 0.1, 0.22], [0.55, 0.52, 0.46]]
CURTAINS = [[0.32, 0.07, 0.05], [0.12, 0.17, 0.1], [0.55, 0.5, 0.4], [0.4, 0.33, 0.22]]
_ROOMS = ["warm_bar"]   # the interiors lit windows may show (set per set from "window_rooms")


def M(key):
    return builders.material(key)


# ── Mesh helpers (all in a parent's local Godot frame) ─────────────────────────────
def lbox(parent, name, lo, hi, m):
    """A box from local min to max corners; UVs from local coordinates, so bricks run on across boxes."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return kit.mesh(name, v, f, m, parent)


def _rod(a, b, r0, r1, seg):
    """Vertices and faces (from 0) of a tapered round bar from a to b."""
    d = [b[i] - a[i] for i in range(3)]
    L = math.sqrt(sum(c * c for c in d)) or 1e-6
    d = [c / L for c in d]
    up = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0)
    s = [d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0]]
    sl = math.sqrt(sum(c * c for c in s))
    s = [c / sl for c in s]
    t = [d[1] * s[2] - d[2] * s[1], d[2] * s[0] - d[0] * s[2], d[0] * s[1] - d[1] * s[0]]
    verts, faces = [], []
    for p, r in ((a, r0), (b, r1)):
        for k in range(seg):
            ang = 2 * math.pi * k / seg
            c, sn = math.cos(ang) * r, math.sin(ang) * r
            verts.append(tuple(p[i] + s[i] * c + t[i] * sn for i in range(3)))
    for k in range(seg):
        j = (k + 1) % seg
        faces.append((k, j, seg + j, seg + k))
    faces.append(tuple(range(seg))[::-1])
    faces.append(tuple(range(seg, 2 * seg)))
    return verts, faces


def rod(parent, name, a, b, r0, r1, m, seg=8):
    """A tapered round bar from a to b (radius r0 at a, r1 at b)."""
    v, f = _rod(a, b, r0, r1, seg)
    return kit.mesh(name, v, f, m, parent, smooth=True)


class Acc:
    """Many bars and panels gathered into one mesh (a tree's thousand branches are one object, not a
    thousand: Blender builds it in a blink and Cycles traces it fast)."""

    def __init__(self):
        self.v, self.f = [], []

    def rod(self, a, b, r0, r1, seg=6):
        v, f = _rod(a, b, r0, r1, seg)
        n = len(self.v)
        self.v += v
        self.f += [tuple(i + n for i in face) for face in f]

    def quad(self, p0, p1, p2, p3):
        n = len(self.v)
        self.v += [p0, p1, p2, p3]
        self.f.append((n, n + 1, n + 2, n + 3))

    def build(self, name, m, parent, smooth=True):
        return kit.mesh(name, self.v, self.f, m, parent, smooth=smooth) if self.f else None


def fan_prism(parent, name, poly, c, depth, m, frame):
    """A flat polygon (u, v) swept `depth` along the frame's third axis, filled as a fan from c
    (the polygon must be star-shaped about c: facade.is_star_shaped)."""
    o, U, V, W = frame
    def at(u, v, w):
        return tuple(o[i] + U[i] * u + V[i] * v + W[i] * w for i in range(3))
    n = len(poly)
    verts = [at(u, v, 0) for u, v in poly] + [at(u, v, depth) for u, v in poly] + [at(c[0], c[1], 0), at(c[0], c[1], depth)]
    cb, cf = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [(cb, j, i), (cf, n + i, n + j), (i, j, n + j, n + i)]
    return kit.mesh(name, verts, faces, m, parent)


def ball(parent, name, c, r, m, seg=8):
    prof = [(r * math.sin(math.pi * k / 6), -r * math.cos(math.pi * k / 6)) for k in range(7)]
    return kit.lathe(parent, name, prof, m, at=c, segments=seg)


def room_card(parent, u0, u1, v0, v1, n, room, strength, rng, span_u=0.08, span_v=0.3):
    """The room behind a window: a card with a patch of a CC0 interior panorama on it (see
    surfaces.room_card), a different patch for every window."""
    corners = [(u0, v0, n), (u1, v0, n), (u1, v1, n), (u0, v1, n)]
    ob = builders._mesh_object("room", [g2b(c) for c in corners], [(0, 1, 2, 3)], [[(0, 0), (1, 0), (1, 1), (0, 1)]],
                               M({"room": room, "strength": strength, "span_u": span_u, "span_v": span_v}), parent)
    ob["room_u"] = rng.random()
    ob["room_v"] = rng.uniform(0.32, 0.4)
    return ob


def text(parent, body, at, size, m, font="DejaVuSans-Bold.ttf", depth=0.01, yaw=0.0, align="CENTER"):
    """Lettering standing up on the facade (facing local +z, or turned `yaw` degrees about up)."""
    cu = bpy.data.curves.new("sign", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.extrude = depth
    p = FONTS / font
    if p.exists():
        cu.font = bpy.data.fonts.load(str(p), check_existing=True)
    cu.materials.append(m)
    ob = bpy.data.objects.new("sign", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = g2b(at)
    ob.rotation_euler = (math.radians(90), 0.0, math.radians(yaw))
    return ob


def area_light(parent, at, size_x, size_y, power, color, name="spill"):
    """A soft rectangular light in a parent's frame, shining out along its local +z (a shop's
    light falling out of its window onto the pavement)."""
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size_x, size_y
    ld.energy = power
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = g2b(at)
    ob.rotation_euler = (math.radians(-90), 0.0, 0.0)
    ob.visible_camera = False
    return ob


# ── Canal-house fronts ──────────────────────────────────────────────────────────────
def facade(f, rng):
    """One house front. f: {"x0", "x1", "z", "facing": "south"|"north", "storeys": [m, ...] bottom
    up, "bays", "gable": kind, "gable_h", "brick", "lit", "door_bay", "stoop", "lean", "plinth",
    "shop": {...}, "skin_below", "holes"}. Facing south it stands on z with its front toward +z (the
    street). "skin_below": up to that height only a thin brick skin goes on (a house the game walks
    in: its rooms have the real walls and windows), with "holes" [{"u0", "u1", "v0", "v1", "arch"}]."""
    W = f["x1"] - f["x0"]
    south = f.get("facing", "south") == "south"
    root = builders.empty_at("facade", (f["x0"] if south else f["x1"], f.get("y", 0.0), f["z"]), 0.0 if south else 180.0)
    skin = f.get("skin_below", 0.0)
    lean = f.get("lean", 0.0 if skin else rng.uniform(0.25, 1.1))
    root.rotation_euler[0] = math.radians(lean)   # Amsterdam's fronts lean out over the street
    T = 0.3
    k = rng.uniform(0.78, 1.0)
    tint = f.get("tint", [k, k * rng.uniform(0.94, 1.0), k * rng.uniform(0.9, 1.0)])
    brick = M(f["paint"]) if f.get("paint") else M({"ph": f.get("brick") or rng.choice(BRICKS), "tint": tint, "scale": 1.0})
    trim, stone, glass = M(TRIM), M(STONE), M("glass")
    storeys = f["storeys"]
    stoop = f.get("stoop", 0.0)
    shop = f.get("shop")
    g = layout.window_grid(W, storeys, f.get("bays", 3), f.get("win_w", 1.05), None if shop else f.get("door_bay"))
    H = g["height"]
    wins = [w for w in g["windows"] if w[2] >= max(skin, storeys[0] if shop else 0.0)]
    door = g["door"] if not skin and not shop else None
    if door and stoop:
        door = (door[0], door[1], stoop, stoop + 2.4)
    holes = list(wins) + ([door] if door else [])
    if shop:
        holes.append((0.3, W - 0.3, 0.0, min(storeys[0] - 0.7, shop.get("top", 2.8))))
    # the brick: full thickness above the skin line, cut round the windows, the door and the shop
    for u0, u1, v0, v1 in layout.cut_rects(W, H - skin, [(a, b, max(c - skin, 0.0), d - skin) for a, b, c, d in holes]):
        lbox(root, "brick", (u0, v0 + skin, -T), (u1, v1 + skin, 0.0), brick)
    if skin > 0:   # the thin skin over the rooms' own wall, around their openings
        sh = [(h["u0"], h["u1"], h["v0"], h["v1"]) for h in f.get("holes", [])]
        for u0, u1, v0, v1 in layout.cut_rects(W, skin, sh):
            lbox(root, "skin", (u0, v0, 0.0), (u1, v1, 0.025), brick)
        for h in f.get("holes", []):
            if h.get("arch"):   # fill the corners above the arch, as the room's spandrels are
                r = (h["u1"] - h["u0"]) / 2
                uc, ys = (h["u0"] + h["u1"]) / 2, h["v1"] - r
                for sgn, corner in ((-1, h["u0"]), (1, h["u1"])):
                    arc = [(uc + sgn * r * math.cos(math.pi / 2 * i / 8), ys + r * math.sin(math.pi / 2 * i / 8)) for i in range(9)]
                    kit.prism(root, "skin_arch", [(corner, h["v1"])] + arc, 0.025, brick, ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
            if h["v0"] > 0.2:   # a stone sill under the house's own window, so it reads from the street
                lbox(root, "sill", (h["u0"] - 0.06, h["v0"] - 0.07, 0.0), (h["u1"] + 0.06, h["v0"], 0.09), stone)
    elif f.get("plinth", rng.random() < 0.35) and not shop:   # the bottom metre tarred black against the wet
        for u0, u1, v0, v1 in layout.cut_rects(W, 0.85, [(a, b, c, d) for a, b, c, d in holes if c < 0.85]):
            lbox(root, "plinth", (u0, v0, 0.0), (u1, v1, 0.01), M({"color": [0.02, 0.02, 0.022], "rough": 0.55, "noise": 0.25}))
    for u0, u1, v0, v1 in wins:
        window(root, u0, u1, v0, v1, T, trim, stone, glass, rng, f.get("lit", 0.2), f.get("shutters", False))
    if door:
        front_door(root, door, stoop, trim, stone, glass, rng, f.get("lit", 0.2))
    if shop:
        shopfront(root, f, W, storeys[0], rng)
    if f.get("street_sign"):   # the city's red name plate: white letters and three white crosses
        ss = f["street_sign"]
        u, v = ss.get("u", 0.8), ss.get("v", 2.9)
        lbox(root, "street_sign", (u - 0.62, v - 0.13, 0.0), (u + 0.62, v + 0.13, 0.025), M({"color": [0.42, 0.025, 0.025], "rough": 0.35, "noise": 0.05}))
        white = M({"color": [0.85, 0.85, 0.82], "rough": 0.4, "noise": 0.02})
        text(root, ss["text"], (u + 0.1, v, 0.026), 0.15, white, depth=0.002)
        text(root, "XXX", (u - 0.48, v, 0.026), 0.07, white, depth=0.002)
    top(root, f, W, H, T, brick, trim, stone, rng)
    return root


def window(root, u0, u1, v0, v1, T, trim, stone, glass, rng, lit, shutters):
    """A sash window: the white frame set back in the brick, glazing bars, the glass, the room
    behind (lit or dark), maybe curtains, a stone sill and lintel, maybe shutters."""
    d0 = -0.11
    for a, b, c, e in ((u0, u0 + 0.06, v0, v1), (u1 - 0.06, u1, v0, v1), (u0, u1, v0, v0 + 0.07), (u0, u1, v1 - 0.06, v1),
                       (u0, u1, v0 + (v1 - v0) * 0.52, v0 + (v1 - v0) * 0.52 + 0.045),
                       ((u0 + u1) / 2 - 0.016, (u0 + u1) / 2 + 0.016, v0, v1)):
        lbox(root, "sash", (a, c, d0 - 0.05), (b, e, d0), trim)
    for fr in (0.26, 0.78):
        vv = v0 + (v1 - v0) * fr
        lbox(root, "bar", (u0, vv - 0.01, d0 - 0.04), (u1, vv + 0.01, d0 - 0.015), trim)
    lbox(root, "glass", (u0, v0, d0 - 0.032), (u1, v1, d0 - 0.028), glass)
    on = rng.random() < lit
    room_card(root, u0 - 0.15, u1 + 0.15, v0 - 0.15, v1 + 0.15, -T - 0.7, rng.choice(_ROOMS), rng.uniform(0.9, 1.8) if on else 0.03, rng)
    if rng.random() < 0.55:   # curtains, half drawn
        cw = (u1 - u0) * rng.uniform(0.16, 0.38)
        cm = M({"color": rng.choice(CURTAINS), "rough": 0.95, "noise": 0.3})
        lbox(root, "curtain", (u0, v0, -T - 0.25), (u0 + cw, v1, -T - 0.22), cm)
        lbox(root, "curtain", (u1 - cw, v0, -T - 0.25), (u1, v1, -T - 0.22), cm)
    kit.soft(root, "sill", ((u0 + u1) / 2, v0 - 0.045, 0.01), (u1 - u0 + 0.14, 0.09, 0.16), stone, 0.015, 2)
    lbox(root, "lintel", (u0 - 0.04, v1, -0.01), (u1 + 0.04, v1 + 0.11, 0.015), stone)
    if shutters:   # wooden shutters, open against the brick (the warehouses' kind)
        sm = M({"ph": "distressed_painted_planks", "tint": rng.choice([[0.08, 0.2, 0.12], [0.35, 0.06, 0.04], [0.06, 0.06, 0.07]])})
        sw = (u1 - u0) / 2
        for a in (u0 - sw - 0.03, u1 + 0.03):
            lbox(root, "shutter", (a, v0, 0.0), (a + sw, v1, 0.04), sm)


def front_door(root, door, stoop, trim, stone, glass, rng, lit):
    """A panelled front door set back in a white frame, a fanlight above it, a stone stoop."""
    u0, u1, v0, v1 = door
    paint = M({"ph": "distressed_painted_planks", "tint": rng.choice(DOORS), "scale": 0.5})
    lbox(root, "door", (u0, v0, -0.22), (u1, v1 - 0.55, -0.18), paint)
    for pv in (0.25, 0.62):   # raised panels
        cy = v0 + (v1 - 0.55 - v0) * pv
        kit.soft(root, "door_panel", ((u0 + u1) / 2, cy, -0.17), ((u1 - u0) * 0.66, (v1 - v0) * 0.26, 0.03), paint, 0.01, 2)
    lbox(root, "fanlight", (u0, v1 - 0.55, -0.2), (u1, v1, -0.19), glass)
    room_card(root, u0, u1, v1 - 0.55, v1, -0.6, rng.choice(_ROOMS), 1.2 if rng.random() < lit * 2 else 0.03, rng)
    for i in range(1, 4):
        uu = u0 + (u1 - u0) * i / 4
        lbox(root, "fan_bar", (uu - 0.012, v1 - 0.55, -0.2), (uu + 0.012, v1, -0.17), trim)
    for a, b, c, e in ((u0 - 0.1, u0, v0, v1 + 0.12), (u1, u1 + 0.1, v0, v1 + 0.12), (u0, u1, v1, v1 + 0.12), (u0, u1, v1 - 0.6, v1 - 0.55)):
        lbox(root, "door_frame", (a, c, -0.18), (b, e, 0.03), trim)
    rod(root, "door_knob", ((u0 + u1) / 2, v0 + 1.05, -0.17), ((u0 + u1) / 2, v0 + 1.05, -0.1), 0.03, 0.035, M("brass"))
    if stoop:
        for s in range(3):
            h0 = stoop * s / 3
            kit.soft(root, "stoop", ((u0 + u1) / 2, h0 + stoop / 6, (1.0 - s * 0.3) / 2), (u1 - u0 + 1.0, stoop / 3, 1.0 - s * 0.3),
                     stone, 0.012, 2)
        for sx in (u0 - 0.5, u1 + 0.5):
            rod(root, "stoop_rail", (sx, stoop, 0.95), (sx, stoop + 0.9, 0.95), 0.015, 0.015, M(IRON))
            rod(root, "stoop_rail", (sx, stoop + 0.9, 0.95), (sx, stoop + 0.9, 0.05), 0.015, 0.015, M(IRON))


def top(root, f, W, H, T, brick, trim, stone, rng):
    """The top of the front: a moulded cornice on brackets with a roof and chimneys behind, or a
    gable with stone coping, a round window, a hoist beam and a finial."""
    kind = f.get("gable", "cornice")
    roof_m = M(ROOF)
    if kind == "cornice":
        for name, v0, v1, n1, r in (("fascia", H - 0.2, H, 0.05, 0.01), ("bed_mould", H, H + 0.09, 0.13, 0.02),
                                    ("corona", H + 0.09, H + 0.3, 0.42, 0.03), ("cyma", H + 0.3, H + 0.38, 0.46, 0.04)):
            kit.soft(root, name, (W / 2, (v0 + v1) / 2, (n1 - T) / 2), (W + 0.2, v1 - v0, n1 + T), trim, r, 3)
        n = max(2, int(W / 0.75))
        for i in range(n + 1):   # the brackets under the corona
            u = 0.12 + (W - 0.24) * i / n
            kit.soft(root, "console", (u, H - 0.02, 0.17), (0.09, 0.2, 0.26), trim, 0.02, 2)
        lbox(root, "attic", (0.0, H + 0.38, -T), (W, H + 0.95, 0.0), brick)
        fan_prism(root, "roof", [(-W / 2, 0.0), (W / 2, 0.0), (0.0, 3.0)], (0.0, 0.5), -9.0, roof_m,
                  ((W / 2, H + 0.95, -T - 0.4), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
        for i in range(rng.choice([1, 2])):   # chimneys on the roof
            u = W * rng.uniform(0.2, 0.8)
            lbox(root, "chimney", (u - 0.35, H + 1.5, -3.5), (u + 0.35, H + 4.3, -2.8), brick)
            lbox(root, "chimney_cap", (u - 0.42, H + 4.3, -3.57), (u + 0.42, H + 4.42, -2.73), stone)
        return
    hg = f.get("gable_h", rng.uniform(3.0, 4.2))
    lbox(root, "string_course", (-0.04, H - 0.12, -T), (W + 0.04, H, 0.07), stone)
    poly = layout.gable_outline(kind, W, hg)
    fan_prism(root, "gable", poly, (0.0, 0.2), -T, brick, ((W / 2, H, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    coping = [(u + (0.07 if u > 0 else -0.07 if u < 0 else 0.0), v + 0.08) for u, v in poly]
    coping[0], coping[-1] = (poly[0][0] - 0.07, 0.0), (poly[-1][0] + 0.07, 0.0)
    fan_prism(root, "coping", coping, (0.0, 0.2), -T + 0.05, stone, ((W / 2, H, -0.03), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    gw, gy = 0.75, H + hg * 0.3
    lbox(root, "gable_window", (W / 2 - gw / 2, gy, 0.0), (W / 2 + gw / 2, gy + 1.0, 0.012), M("glass"))
    lbox(root, "gable_window_back", (W / 2 - gw / 2, gy, -0.01), (W / 2 + gw / 2, gy + 1.0, 0.0), M({"color": [0.01, 0.01, 0.012], "rough": 0.9}))
    for a, b, c, e in ((-gw / 2 - 0.07, -gw / 2, 0.0, 1.0), (gw / 2, gw / 2 + 0.07, 0.0, 1.0),
                       (-gw / 2 - 0.07, gw / 2 + 0.07, -0.08, 0.0), (-gw / 2 - 0.07, gw / 2 + 0.07, 1.0, 1.07), (-0.015, 0.015, 0.0, 1.0)):
        lbox(root, "gable_frame", (W / 2 + a, gy + c, 0.0), (W / 2 + b, gy + e, 0.04), trim)
    wood = M({"ph": "dark_wood", "tint": [0.3, 0.24, 0.2]})
    hb = H + hg * 0.7
    lbox(root, "hoist_beam", (W / 2 - 0.09, hb, -0.2), (W / 2 + 0.09, hb + 0.2, 0.85), wood)
    rod(root, "hoist_hook", (W / 2, hb, 0.75), (W / 2, hb - 0.35, 0.75), 0.012, 0.012, M(IRON))
    apex = max(v for _, v in poly)
    kit.lathe(root, "finial", [(0.0, 0.0), (0.12, 0.0), (0.12, 0.05), (0.06, 0.1), (0.14, 0.25), (0.1, 0.38), (0.04, 0.42),
                               (0.06, 0.48), (0.0, 0.56)], stone, at=(W / 2, H + apex + 0.08, -0.15), segments=12)
    fan_prism(root, "roof", [(-W / 2 + 0.2, 0.0), (W / 2 - 0.2, 0.0), (0.0, hg * 0.8)], (0.0, 0.3), -10.0, roof_m,
              ((W / 2, H, -T - 0.05), (1, 0, 0), (0, 1, 0), (0, 0, 1)))


def shopfront(root, f, W, s0, rng):
    """The ground floor as a shop, a café or a coffeeshop: a glazed front in a painted frame on a
    stall riser, a glass door, the shop inside (a CC0 interior panorama), its name lit on the fascia,
    a blade sign, maybe an awning; and its light falling out onto the pavement.
    f["shop"]: {"name", "kind", "room", "frame": rgb, "sign": rgb, "awning": [rgb, rgb], "blade": text,
    "door_bay", "power"}."""
    sh = f["shop"]
    top_v = min(s0 - 0.7, sh.get("top", 2.8))
    u0, u1, riser = 0.3, W - 0.3, 0.42
    frame = M({"color": sh.get("frame", [0.03, 0.045, 0.035]), "rough": 0.35, "noise": 0.12})
    glass = M("glass")
    lbox(root, "riser", (u0, 0.0, -0.2), (u1, riser, -0.12), frame)
    n = max(2, int((u1 - u0) / 1.4))
    door_i = sh.get("door_bay", n // 2)
    for i in range(n + 1):   # posts
        uu = u0 + (u1 - u0) * i / n
        lbox(root, "shop_post", (uu - 0.05, 0.0, -0.2), (uu + 0.05, top_v, -0.08), frame)
    lbox(root, "shop_head", (u0, top_v - 0.1, -0.2), (u1, top_v, -0.06), frame)
    lbox(root, "transom_bar", (u0, top_v - 0.55, -0.2), (u1, top_v - 0.5, -0.1), frame)
    for i in range(n):
        a, b = u0 + (u1 - u0) * i / n + 0.05, u0 + (u1 - u0) * (i + 1) / n - 0.05
        bottom = 0.0 if i == door_i else riser
        lbox(root, "shop_glass", (a, bottom, -0.165), (b, top_v - 0.1, -0.16), glass)
        if i == door_i:   # the glass door: a frame and a long brass push bar
            for c, e in ((a, a + 0.08), (b - 0.08, b)):
                lbox(root, "door_stile", (c, 0.0, -0.17), (e, top_v - 0.55, -0.14), frame)
            lbox(root, "door_rail", (a, 0.0, -0.17), (b, 0.12, -0.14), frame)
            rod(root, "push_bar", (b - 0.16, 0.8, -0.11), (b - 0.16, 1.5, -0.11), 0.015, 0.015, M("brass"))
    room_card(root, u0 - 0.2, u1 + 0.2, -0.1, top_v + 0.2, -1.6, sh.get("room", "warm_bar"), sh.get("glow", 1.6), rng,
              span_u=0.06 * W, span_v=0.32)
    # the shop's light out through its window, warm, onto the pavement and whatever stands there
    area_light(root, (W / 2, top_v * 0.55, -0.5), u1 - u0 - 0.2, top_v * 0.8, sh.get("power", 90.0) * W,
               tuple(sh.get("light", (1.0, 0.72, 0.45))))
    # the fascia board with the name lit on it
    lbox(root, "fascia", (0.15, top_v, -0.05), (W - 0.15, top_v + 0.55, 0.08), frame)
    sign_m = builders.emissive("sign_" + sh.get("name", "shop")[:12], tuple(sh.get("sign", (1.0, 0.85, 0.6))), sh.get("sign_strength", 6.0))
    text(root, sh.get("name", "CAFÉ"), (W / 2, top_v + 0.275, 0.09), min(0.36, 1.6 * (W - 0.6) / max(len(sh.get("name", "x")), 1)),
         sign_m, font=sh.get("font", "DejaVuSerif-Bold.ttf"))
    if sh.get("blade"):   # a blade sign out over the pavement, lit, both faces
        bu = W - 0.2
        rod(root, "blade_arm", (bu, top_v + 1.25, 0.0), (bu, top_v + 1.25, 0.95), 0.02, 0.02, M(IRON))
        lbox(root, "blade", (bu - 0.04, top_v + 0.45, 0.2), (bu + 0.04, top_v + 1.2, 0.9), frame)
        for sgn in (-1, 1):
            text(root, sh["blade"], (bu + sgn * 0.045, top_v + 0.82, 0.55), 0.13, sign_m, yaw=90 * sgn,
                 font=sh.get("font", "DejaVuSerif-Bold.ttf"))
    if sh.get("awning"):   # a striped canvas awning, wound out
        c_a, c_b = sh["awning"]
        cloth = M({"pattern": "stripes", "colors": [c_a, c_b], "width": 0.24})
        a = Acc()
        out, drop = sh.get("awning_out", 1.4), 0.55
        a.quad((u0, top_v + 0.05, 0.02), (u1, top_v + 0.05, 0.02), (u1, top_v + 0.05 - drop, out), (u0, top_v + 0.05 - drop, out))
        a.quad((u0, top_v + 0.05 - drop, out), (u1, top_v + 0.05 - drop, out), (u1, top_v - drop - 0.2, out), (u0, top_v - drop - 0.2, out))
        a.build("awning", cloth, root, smooth=False)
        for uu in (u0 + 0.05, u1 - 0.05):
            rod(root, "awning_arm", (uu, top_v - 0.6, 0.0), (uu, top_v + 0.05 - drop, out - 0.05), 0.012, 0.012, M(IRON))


def facade_row(x_from, x_to, z, facing, rng, row=None, y=0.0):
    """A row of canal houses along z from x_from to x_to, random widths, heights and gables, their
    street at height y."""
    row = row or {}
    x = x_from
    while x < x_to:
        w = rng.uniform(5.0, 9.5)
        kind = rng.choice(["neck", "neck", "bell", "step", "cornice", "spout", "cornice"]) if w < 8.5 else "cornice"
        n = rng.choice([4, 4, 5, 3])
        storeys = [rng.uniform(3.4, 3.9)] + [rng.uniform(2.9, 3.3) for _ in range(n - 1)]
        bays = 3 if w < 7.5 else 5 if w > 8.6 else 4
        f = {"x0": x, "x1": x + w - 0.04, "z": z, "y": y, "facing": facing, "storeys": storeys, "bays": bays, "gable": kind,
             "door_bay": rng.randrange(bays), "stoop": rng.choice([0.0, 0.5, 0.75]), "lit": row.get("lit", 0.2)}
        if rng.random() < 0.12:
            f["paint"] = {"color": rng.choice([[0.6, 0.58, 0.54], [0.18, 0.2, 0.21], [0.42, 0.4, 0.34]]), "rough": 0.8, "noise": 0.15}
        facade(f, rng)
        x += w


# ── Street furniture ────────────────────────────────────────────────────────────────
def bollard(root, p, w, h, d):
    """An Amsterdammertje: a cast-iron post in Amsterdam's brown-red, with the city's three white
    St Andrew's crosses down its front."""
    iron = M(p.get("material", {"color": [0.11, 0.035, 0.025], "rough": 0.4, "metal": 0.35, "noise": 0.25}))
    r = w / 2
    kit.lathe(root, "post", [(0.0, 0.0), (r * 1.1, 0.0), (r, 0.05), (r * 0.92, h * 0.85), (r * 1.02, h * 0.88), (r * 0.8, h * 0.95),
                             (r * 0.3, h), (0.0, h)], iron, segments=16)
    white = M({"color": [0.75, 0.74, 0.7], "rough": 0.5, "noise": 0.05})
    a = Acc()
    for i in range(3):
        y = h * (0.64 - i * 0.15)
        for sgn in (-1, 1):
            a.rod((-0.035, y - sgn * 0.035, r * 0.93), (0.035, y + sgn * 0.035, r * 0.93), 0.008, 0.008, 4)
    a.build("crosses", white, root)


def bike(root, p, w, h, d):
    """A black Dutch upright bike (an omafiets): two wheels, the frame, a rear rack, mudguards, a
    saddle and swept-back bars. Its length runs along local x."""
    rng = random.Random(p.get("seed", 5))
    paint = M(p.get("material", {"color": rng.choice([[0.015, 0.015, 0.017], [0.015, 0.015, 0.017], [0.05, 0.08, 0.12],
                                                       [0.25, 0.04, 0.03]]), "rough": 0.35, "metal": 0.5, "noise": 0.1}))
    rubber = M({"color": [0.01, 0.01, 0.01], "rough": 0.8, "noise": 0.05})
    steel = M({"color": [0.5, 0.5, 0.52], "rough": 0.25, "metal": 1.0, "noise": 0.2})
    R, wb = 0.34, 1.12
    rear, front = (-wb / 2, R, 0.0), (wb / 2, R, 0.0)
    tyres, spokes, frame = Acc(), Acc(), Acc()
    for c in (rear, front):
        ring = 24
        for i in range(ring):
            a0, a1 = 2 * math.pi * i / ring, 2 * math.pi * (i + 1) / ring
            tyres.rod((c[0] + R * math.cos(a0), c[1] + R * math.sin(a0), 0.0), (c[0] + R * math.cos(a1), c[1] + R * math.sin(a1), 0.0), 0.022, 0.022, 6)
            spokes.rod((c[0] + 0.3 * math.cos(a0), c[1] + 0.3 * math.sin(a0), 0.0), (c[0] + 0.3 * math.cos(a1), c[1] + 0.3 * math.sin(a1), 0.0), 0.008, 0.008, 4)
        for i in range(9):
            a = math.pi * i / 9
            spokes.rod((c[0] - 0.29 * math.cos(a), c[1] - 0.29 * math.sin(a), 0.0), (c[0] + 0.29 * math.cos(a), c[1] + 0.29 * math.sin(a), 0.0), 0.0015, 0.0015, 3)
        for i in range(9):   # the mudguard: half a ring over the wheel
            a0, a1 = math.pi * (0.1 + 0.8 * i / 9), math.pi * (0.1 + 0.8 * (i + 1) / 9)
            frame.rod((c[0] + 0.39 * math.cos(a0), c[1] + 0.39 * math.sin(a0), 0.0), (c[0] + 0.39 * math.cos(a1), c[1] + 0.39 * math.sin(a1), 0.0), 0.03, 0.03, 4)
    crank, seat, head = (-0.05, R - 0.02, 0.0), (-0.2, 0.95, 0.0), (0.4, 0.98, 0.0)
    for a, b in ((rear, crank), (crank, seat), (seat, rear), (crank, head), (head, front), (seat, (0.38, 0.86, 0.0)),
                 (seat, (seat[0] - 0.03, 1.05, 0.0)), (head, (0.36, 1.12, 0.0))):
        frame.rod(a, b, 0.016, 0.016, 6)
    for sz in (-1, 1):
        frame.rod((0.36, 1.12, 0.0), (0.2, 1.1, sz * 0.27), 0.011, 0.011, 6)
    tyres.build("tyres", rubber, root)
    spokes.build("spokes", steel, root)
    frame.build("frame", paint, root)
    kit.soft(root, "saddle", (seat[0] - 0.04, 1.08, 0.0), (0.26, 0.06, 0.16), M({"color": [0.05, 0.03, 0.02], "rough": 0.6}), 0.02, 2)
    builders.part(root, "rack", (rear[0] + 0.05, 0.78, 0.0), (0.42, 0.02, 0.16), paint)
    if rng.random() < 0.4:   # a crate on the front
        lbox(root, "crate", (0.42, 0.88, -0.18), (0.78, 1.15, 0.18), M({"ph": "dark_wood", "tint": [0.6, 0.5, 0.4]}))


def plane_tree(root, p, w, h, d):
    """A canal tree (elm or plane): a leaning trunk in mottled plane-tree bark forking into limbs,
    the limbs into branches, thinning to fine twigs against the sky; with "leaves" a scatter of
    October's last leaves near the tips (lamplight shines through them)."""
    rng = random.Random(p.get("seed", 7))
    bark = M(p.get("material", {"ph": "bark_platanus", "tint": [0.7, 0.68, 0.64], "scale": 0.6}))
    wood, twigs = Acc(), Acc()
    trunk_h = h * rng.uniform(0.32, 0.4)
    pts = [(0.0, -0.05, 0.0)]
    for i in range(1, 4):   # the trunk in three slightly crooked lengths
        t = i / 3
        pts.append((rng.uniform(-0.2, 0.2) * t, trunk_h * t, rng.uniform(-0.2, 0.2) * t))
    for i in range(3):
        wood.rod(pts[i], pts[i + 1], w / 2 * (1 - 0.12 * i), w / 2 * (1 - 0.12 * (i + 1)), 12)
    tips = []

    def grow(a, direction, length, r, depth):
        mid = tuple(a[i] + direction[i] * length * 0.5 + rng.uniform(-0.08, 0.08) * length for i in range(3))
        b = tuple(a[i] + direction[i] * length for i in range(3))
        acc = wood if r > 0.012 else twigs
        acc.rod(a, mid, r, r * 0.85, 6 if r > 0.03 else 4)
        acc.rod(mid, b, r * 0.85, r * 0.7, 6 if r > 0.03 else 4)
        if depth == 0:
            tips.append(b)
            for _ in range(3):   # the last twigs
                tw = [direction[0] + rng.uniform(-0.6, 0.6), direction[1] + rng.uniform(-0.1, 0.5), direction[2] + rng.uniform(-0.6, 0.6)]
                tl = math.sqrt(sum(c * c for c in tw))
                twigs.rod(b, tuple(b[i] + tw[i] / tl * length * 0.6 for i in range(3)), max(r * 0.5, 0.006), 0.003, 3)
            return
        for _ in range(2 if depth < 3 else rng.choice([2, 3])):
            yaw = rng.uniform(0, 2 * math.pi)
            spread = rng.uniform(0.4, 0.8)
            nd = [direction[0] + math.cos(yaw) * spread, direction[1] + rng.uniform(-0.15, 0.3), direction[2] + math.sin(yaw) * spread]
            nl = math.sqrt(sum(c * c for c in nd))
            grow(b, [c / nl for c in nd], length * rng.uniform(0.66, 0.82), r * 0.66, depth - 1)

    for i in range(rng.choice([3, 4])):
        yaw = 2 * math.pi * i / 3 + rng.uniform(-0.5, 0.5)
        dn = [math.cos(yaw) * 0.5, 1.0, math.sin(yaw) * 0.5]
        nl = math.sqrt(sum(c * c for c in dn))
        grow(pts[-1], [c / nl for c in dn], h * 0.2, w / 2 * 0.6, p.get("depth", 6))
    wood.build("tree", bark, root)
    twigs.build("twigs", M({"color": [0.03, 0.026, 0.022], "rough": 0.8, "noise": 0.2}), root)
    if p.get("leaves"):   # small cards near the tips, autumn colours, lit through
        lv = Acc()
        for tip in tips:
            for _ in range(int(p["leaves"])):
                c = [tip[i] + rng.uniform(-0.6, 0.6) for i in range(3)]
                s = rng.uniform(0.05, 0.08)
                a = rng.uniform(0, math.pi)
                dx, dz = math.cos(a) * s, math.sin(a) * s
                lv.quad((c[0] - dx, c[1] - s * 0.5, c[2] - dz), (c[0] + dx, c[1] - s * 0.5, c[2] + dz),
                        (c[0] + dx, c[1] + s * 0.5, c[2] + dz), (c[0] - dx, c[1] + s * 0.5, c[2] - dz))
        lv.build("leaves", M({"color": p.get("leaf_color", [0.42, 0.3, 0.06]), "rough": 0.7, "noise": 0.5, "noise_scale": 3.0}), root, smooth=False)
    kit.lathe(root, "tree_pit", [(0.0, 0.0), (0.6, 0.0), (0.6, 0.03), (0.0, 0.03)], M({"color": [0.02, 0.018, 0.015], "rough": 1.0}), segments=4)


def railing(root, p, w, h, d):
    """A low iron quay railing along local x: posts every metre, a top rail and a mid rail."""
    a = Acc()
    n = max(1, int(round(w / 1.0)))
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        a.rod((x, 0.0, 0.0), (x, h, 0.0), 0.022, 0.02, 6)
    for y in (h, h * 0.45):
        a.rod((-w / 2, y, 0.0), (w / 2, y, 0.0), 0.02, 0.02, 6)
    a.build("railing", M(p.get("material", IRON)), root)


def heater(root, p, w, h, d):
    """A terrace's patio heater, still burning: a steel pole, a reflector hood, a glowing grille."""
    steel = M({"color": [0.35, 0.35, 0.37], "rough": 0.3, "metal": 1.0, "noise": 0.1})
    kit.lathe(root, "heater", [(0.0, 0.0), (0.25, 0.0), (0.25, 0.04), (0.05, 0.12), (0.04, h - 0.35), (0.12, h - 0.3),
                               (0.1, h - 0.15), (0.42, h - 0.05), (0.44, h), (0.0, h)], steel, segments=16)
    glow = builders.emissive("heater_glow", (1.0, 0.32, 0.08), 12.0)
    kit.lathe(root, "heater_grille", [(0.0, h - 0.33), (0.11, h - 0.33), (0.11, h - 0.16), (0.0, h - 0.16)], glow, segments=12)
    ld = bpy.data.lights.new("heater", "POINT")
    ld.color, ld.energy, ld.shadow_soft_size = (1.0, 0.38, 0.12), p.get("power", 60.0), 0.1
    ob = bpy.data.objects.new("heater", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.location = g2b((0.0, h - 0.28, 0.0))


def hull(root, name, L, Wd, D, m):
    """A boat's hull along local x: U-shaped sections, full amidships, pinched to a point at the bow
    (+x) and a narrower transom at the stern (-x)."""
    nx, nu = 18, 9
    verts, faces = [], []
    for i in range(nx + 1):
        t = i / nx
        x = -L / 2 + L * t
        half = Wd / 2 * (math.sin(math.pi * min(1.0, t * 1.15 + 0.12)) ** 0.6)
        if t > 0.92:
            half *= (1 - t) / 0.08
        dep = D * (0.82 + 0.18 * math.sin(math.pi * t))
        for k in range(nu):
            a = math.pi * k / (nu - 1)   # from the left gunwale, under the keel, to the right gunwale
            verts.append((x, D - dep * math.sin(a) ** 0.7 if 0 < k < nu - 1 else D, -half * math.cos(a)))
    for i in range(nx):
        for k in range(nu - 1):
            a, b = i * nu + k, (i + 1) * nu + k
            faces.append((a, b, b + 1, a + 1))
    return kit.mesh(name, verts, faces, m, root, smooth=True)


def rowboat(root, p, w, h, d):
    """A wooden rowing boat, length along local x, swamped: water in her to the thwarts."""
    wood = M(p.get("material", {"ph": "dark_wood", "tint": [0.32, 0.27, 0.22], "scale": 0.5}))
    paint = M({"ph": "wood_peeling_paint_weathered", "tint": [0.7, 0.8, 0.75], "scale": 0.6})
    hull(root, "hull", w, d, h, paint)
    for x in (-w * 0.2, w * 0.12):
        builders.part(root, "thwart", (x, h * 0.72, 0.0), (0.22, 0.03, d * 0.85), wood)
    builders.part(root, "gunwale_l", (0.0, h, -d / 2 + 0.03), (w * 0.85, 0.04, 0.05), wood)
    builders.part(root, "gunwale_r", (0.0, h, d / 2 - 0.03), (w * 0.85, 0.04, 0.05), wood)
    if p.get("swamped", True):
        builders.part(root, "bilge", (0.0, h * 0.55, 0.0), (w * 0.8, 0.01, d * 0.72), M("canal_water"))
    rod(root, "oar", (-w * 0.3, h * 0.8, -d * 0.2), (w * 0.35, h * 0.95, d * 0.35), 0.022, 0.022, wood, seg=6)


def houseboat(root, p, w, h, d):
    """A converted barge: a black steel hull, a long timber cabin with square windows (one lit, a
    real room inside), a deck with pots, a plank to the quay. Length along local x."""
    rng = random.Random(p.get("seed", 3))
    steel = M({"ph": "rusty_painted_metal", "tint": [0.12, 0.13, 0.14], "scale": 0.5})
    hull(root, "hull", w, d, 1.0, steel)
    builders.part(root, "deck", (0.0, 1.0, 0.0), (w * 0.94, 0.06, d * 0.9), M({"ph": "dark_wood", "tint": [0.35, 0.3, 0.26]}))
    cl = w * 0.62
    cab = M(p.get("cabin", {"ph": "distressed_painted_planks", "tint": [0.25, 0.42, 0.33], "scale": 0.5}))
    x0c, x1c = -cl / 2 - w * 0.08, cl / 2 - w * 0.08
    lbox(root, "cabin", (x0c, 1.0, -d * 0.38), (x1c, h, d * 0.38), cab)
    lbox(root, "cabin_roof", (x0c - 0.1, h, -d * 0.42), (x1c + 0.1, h + 0.08, d * 0.42), M({"color": [0.04, 0.04, 0.045], "rough": 0.8}))
    glass = M("glass")
    n = int(cl / 1.3)
    for i in range(n):
        x = x0c + cl * (i + 0.5) / n
        for sz in (-1, 1):
            zz = sz * (d * 0.38 + 0.012)
            lbox(root, "porthole", (x - 0.35, 1.45, zz - 0.004), (x + 0.35, 1.95, zz + 0.004), glass)
            on = i in p.get("lit_windows", [p.get("lit_window", -1)])
            room_card(root, x - 0.4, x + 0.4, 1.4, 2.0, sz * (d * 0.38 - 0.3), rng.choice(_ROOMS), 1.4 if on else 0.03, rng)
    for i in range(4):
        x = cl / 2 + rng.uniform(0.0, w * 0.15) - w * 0.05
        kit.lathe(root, "pot", [(0.0, 0.0), (0.16, 0.0), (0.2, 0.3), (0.0, 0.3)], M({"color": [0.25, 0.12, 0.07], "rough": 0.8}),
                  at=(x, 1.03, rng.uniform(-d * 0.3, d * 0.3)), segments=10)
        ball(root, "shrub", (x, 1.45, rng.uniform(-d * 0.3, d * 0.3)), 0.22, M({"color": [0.03, 0.05, 0.02], "rough": 0.9, "noise": 0.5}), seg=8)
    for i in range(3):   # on the roof: a skylight with the room's light coming up, a stove pipe, pots
        sx = x0c + cl * (0.2 + 0.3 * i)
        if i == 1:
            lbox(root, "skylight_glow", (sx - 0.45, h + 0.07, -0.4), (sx + 0.45, h + 0.09, 0.4), builders.emissive("skylight", (1.0, 0.6, 0.3), 1.5))
            lbox(root, "skylight", (sx - 0.5, h + 0.08, -0.45), (sx + 0.5, h + 0.3, 0.45), M("glass"))
        else:
            kit.lathe(root, "roof_pot", [(0.0, 0.0), (0.18, 0.0), (0.22, 0.32), (0.0, 0.32)], M({"color": [0.22, 0.1, 0.06], "rough": 0.8}),
                      at=(sx, h + 0.08, rng.uniform(-0.8, 0.8)), segments=10)
            ball(root, "roof_shrub", (sx, h + 0.55, 0.0), 0.3, M({"color": [0.03, 0.06, 0.025], "rough": 0.9, "noise": 0.5}), seg=8)
    rod(root, "stove_pipe", (x1c - 0.5, h, 0.6), (x1c - 0.5, h + 0.9, 0.6), 0.07, 0.07, M(IRON))
    if p.get("plank"):
        lbox(root, "plank", (p["plank"] - 0.3, 1.02, d / 2 - 0.1), (p["plank"] + 0.3, 1.08, d / 2 + 1.6), M({"ph": "dark_wood"}))


# ── Lamps ────────────────────────────────────────────────────────────────────────────
LAMP_HEAD = 3.27   # the lantern's bulb on the CC0 street lamp (street_lamp_01), metres up


def lamp(x, z, y=0.0, power=380.0, color=(1.0, 0.66, 0.36), light=True):
    """A street lamp on its post, its lantern alight (the bulb and glass glow), and its light."""
    root = builders.build_prop({"type": "model", "model": "ph:street_lamp_01", "pos": [x, y, z], "scale": 1.0, "shadow": False,
                                "emit": [{"match": "bulb", "color": color, "strength": 60.0},
                                         {"match": "glass", "color": color, "strength": 3.0}]}, 6.0)
    if light:
        ld = bpy.data.lights.new("street_lamp", "POINT")
        ld.color, ld.energy, ld.shadow_soft_size = color, power, 0.08
        ob = bpy.data.objects.new("street_lamp", ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = g2b((x, y + LAMP_HEAD, z))
    return root


# ── The bridge ──────────────────────────────────────────────────────────────────────
def hump_bridge(spec, b):
    """A brick hump bridge over the canal along z: arches to the water with a lamp bulb every 40 cm
    round each arch on both faces, a cobbled deck rising to the middle, iron railings.
    b: {"x0", "x1", "z0", "z1", "hump", "water", "deck": material, "arches": [[z_centre, span, rise], ...]}."""
    x0, x1, z0, z1 = b["x0"], b["x1"], b["z0"], b["z1"]
    water, hump = b.get("water", -1.6), b.get("hump", 1.3)
    brick = M({"ph": "medieval_red_brick", "tint": [0.8, 0.72, 0.68]})
    deck_m = M(b["deck"]) if b.get("deck") else M(STONE)
    bulb = builders.emissive("bridge_bulb", (1.0, 0.7, 0.34), 22.0)
    arches = b.get("arches", [])

    def top(z):
        t = (z - z0) / (z1 - z0)
        return hump * math.sin(math.pi * min(1.0, max(0.0, t)))

    def soffit(z):   # the underside: an arch's curve over its span, else down to the water
        for zc, span, rise in arches:
            if abs(z - zc) < span / 2:
                return water + rise * math.sqrt(max(0.0, 1 - ((z - zc) / (span / 2)) ** 2)) + 0.6
        return water - 0.3

    step = 0.2
    z = z0
    while z < z1 - 1e-6:
        za, zb = z, min(z1, z + step)
        zm = (za + zb) / 2
        t, s = top(zm), soffit(zm)
        if t - s > 0.05:
            builders.box_aabb("bridge", (x0, s, za), (x1, t - 0.12, zb), brick)
        builders.box_aabb("bridge_deck", (x0 + 0.25, t - 0.12, za), (x1 - 0.25, t, zb), deck_m)
        for xe in (x0, x1 - 0.25):   # the parapet's stone kerb
            builders.box_aabb("bridge_kerb", (xe, t - 0.12, za), (xe + 0.25, t + 0.12, zb), M(STONE))
        z = zb
    bulbs = Acc()
    for zc, span, rise in arches:   # the bulbs round each arch, both faces
        n = int(math.pi * span / 2 / 0.4)
        for k in range(n + 1):
            a = math.pi * k / n
            zz = zc - math.cos(a) * span / 2 * 1.04
            yy = water + 0.6 + rise * math.sin(a) * 1.04 + 0.05
            for xe in (x0 - 0.05, x1 + 0.05):
                bulbs.rod((xe, yy - 0.035, zz), (xe, yy + 0.035, zz), 0.035, 0.035, 6)
    bulbs.build("bulbs", bulb, None)
    rail = Acc()
    for xe in (x0 + 0.12, x1 - 0.12):   # railings following the hump
        n = int((z1 - z0) / 1.0)
        pts = [(xe, top(z0 + (z1 - z0) * k / n) + 0.12, z0 + (z1 - z0) * k / n) for k in range(n + 1)]
        for k, pt in enumerate(pts):
            rail.rod(pt, (pt[0], pt[1] + 0.95, pt[2]), 0.02, 0.018, 6)
            if k:
                q = pts[k - 1]
                for dy in (0.95, 0.45):
                    rail.rod((q[0], q[1] + dy, q[2]), (pt[0], pt[1] + dy, pt[2]), 0.018, 0.018, 6)
    rail.build("bridge_rail", M(IRON), None)
    for zz in (z0 + 1.0, z1 - 1.0):   # lamps at the bridge's four corners
        for xe in (x0 + 0.3, x1 - 0.3):
            lamp(xe, zz, top(zz) + 0.12, power=300.0)


# ── The ground, the quay, the canal, the far bank ─────────────────────────────────────
def outdoor(spec):
    """Everything an "outdoor" RoomSpec stands in: its ground slabs, the quay wall and the canal,
    the far quay with its lamps, trees and houses, the fronts on its own side, its lamps, the bridge
    (built whichever room is being rendered: it's the world outside every window)."""
    global _ROOMS
    o = spec["outdoor"]
    _ROOMS = o.get("window_rooms", _ROOMS)
    rng = random.Random(spec["id"])
    for g in o.get("ground", []):
        (gx0, gz0), (gx1, gz1) = g["min"], g["max"]
        y = g.get("y", 0.0)
        builders.box_aabb(g.get("name", "ground"), (gx0, y - 0.4, gz0), (gx1, y, gz1), M(g.get("material", STONE)))
        if g.get("kerb"):   # a granite kerb along the ground's far edge
            builders.box_aabb("kerb", (gx0, y - 0.4, gz1 - 0.18), (gx1, y + 0.03, gz1), M(STONE))
    c = o.get("canal")
    if c:
        zq, width, water = c["z"], c["width"], c.get("water", -1.6)
        xa, xb = c.get("x", [-60.0, 100.0])
        quay = M({"ph": "mossy_brick", "scale": 1.0})
        builders.box_aabb("canal", (xa, water - 0.02, zq), (xb, water, zq + width), M("canal_water"))
        builders.box_aabb("canal_bed", (xa, water - 3.0, zq), (xb, water - 2.9, zq + width), M({"color": [0.01, 0.012, 0.01], "rough": 1.0}))
        for k, (za, zb) in enumerate(((zq - 0.3, zq), (zq + width, zq + width + 0.3))):
            gaps = c.get("gaps", []) if k == 0 else []
            xs = [xa] + [v for gp in sorted(gaps) for v in gp] + [xb]
            for u0, u1 in zip(xs[::2], xs[1::2]):
                builders.box_aabb("quay_wall", (u0, water - 3.0, za), (u1, 0.0, zb), quay)
                builders.box_aabb("quay_edge", (u0, -0.08, za - 0.05), (u1, 0.04, zb + 0.05), M(STONE))
        fq = c.get("far_quay", 6.0)
        builders.box_aabb("far_quay", (xa, -0.4, zq + width + 0.3), (xb, 0.0, zq + width + fq),
                          M(c.get("far_ground", {"ph": "herringbone_brick", "tint": [0.7, 0.65, 0.6], "wet": 0.6})))
        zf = zq + width + fq
        x = xa + 24
        while x < xb - 24:   # the far quay: lamps, trees, parked cars, nobody
            lamp(x, zq + width + 1.0, power=c.get("far_lamp_power", 420.0))
            builders.build_prop({"type": "plane_tree", "pos": [x + 7.0, 0.0, zq + width + 1.2], "size": [0.45, 12.0, 0.45],
                                 "seed": int(x * 7) % 997, "depth": 5}, 12.0)
            x += 14.0
        if c.get("far_houses", True):
            facade_row(xa + 20, xb - 20, zf, "north", rng, c)
    for f in o.get("facades", []):
        facade(f, random.Random(f.get("seed", 1)))
    for lx, lz in o.get("lamps", []):
        lamp(lx, lz, power=o.get("lamp_power", 380.0))
    for b in o.get("bridges", []):
        hump_bridge(spec, b)


PROPS = {"bollard": bollard, "bike": bike, "elm": plane_tree, "plane_tree": plane_tree, "railing": railing,
         "rowboat": rowboat, "houseboat": houseboat, "heater": heater}
kit.PROPS.update(PROPS)
