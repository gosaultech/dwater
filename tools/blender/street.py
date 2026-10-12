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
FAR = False   # building a street of the next district over, only to be seen in the distance (render_rooms)
TIDE = 0.0    # how high the flood came up the house fronts (m; set per street from "outdoor": {"tide"})


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

    def box(self, lo, hi):
        """An axis-aligned box from its min to its max corner (a shop's thousand packets: one mesh)."""
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        n = len(self.v)
        self.v += [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        self.f += [tuple(n + i for i in q) for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]

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
    hide_panel(ob)
    return ob


def hide_panel(ob):
    """A light lights the set, but its panel is never in the picture: not straight to the lens, nor
    through the glass it stands behind (a shop window, a tram's), nor mirrored in wet stone."""
    ob.visible_camera = False
    ob.visible_transmission = False
    ob.visible_glossy = False


# ── Canal-house fronts ──────────────────────────────────────────────────────────────
FACING = {"south": 0.0, "north": 180.0, "east": 90.0, "west": -90.0}


def facade_frame(f):
    """Where a front stands and how wide it is. Facing south or north it runs along x from "x0" to
    "x1" on the line z = "z"; facing east or west it runs along z from "z0" to "z1" on x = "x". The
    root is at its left-hand end as you face it, so u (along it) runs to the right."""
    facing = f.get("facing", "south")
    y = f.get("y", 0.0)
    if facing in ("south", "north"):
        return f["x1"] - f["x0"], ((f["x0"] if facing == "south" else f["x1"]), y, f["z"]), FACING[facing]
    return f["z1"] - f["z0"], (f["x"], y, (f["z1"] if facing == "east" else f["z0"])), FACING[facing]


def facade(f, rng):
    """One house front. f: {"x0", "x1", "z" | "z0", "z1", "x", "facing": "south"|"north"|"east"|"west", "storeys": [m, ...] bottom
    up, "bays", "gable": kind, "gable_h", "brick", "lit", "door_bay", "stoop", "lean", "tilt", "plinth",
    "shop": {...}, "skin_below", "holes"}. Facing south it stands on z with its front toward +z (the
    street). "skin_below": up to that height only a thin brick skin goes on (a house the game walks
    in: its rooms have the real walls and windows), with "holes" [{"u0", "u1", "v0", "v1", "arch"}].
    "sides": the house is the end of its row, so its side and back walls go up under its roof (else
    only the front stands, the neighbours hiding the rest; at a corner a side wall would stand in the
    next front's windows)."""
    W, at, yaw = facade_frame(f)
    root = builders.empty_at("facade", at, yaw)
    skin = f.get("skin_below", 0.0)
    lean = f.get("lean", 0.0 if skin else rng.uniform(0.25, 1.1))
    root.rotation_euler[0] = math.radians(lean)   # Amsterdam's fronts lean out over the street
    root.rotation_euler[1] = math.radians(f.get("tilt", 0.0))   # and some on their neighbours, sideways
    T = 0.3
    k = rng.uniform(0.78, 1.0)
    tint = f.get("tint", [k, k * rng.uniform(0.94, 1.0), k * rng.uniform(0.9, 1.0)])
    brick_spec = f["paint"] if f.get("paint") else {"ph": f.get("brick") or rng.choice(BRICKS), "tint": tint, "scale": 1.0}
    brick = M(brick_spec)
    tide = f.get("tide", TIDE)
    if tide > 0:   # below the tide line the brick is dark and still wet, the way the water left it
        wet_spec = dict(brick_spec, wet=0.95)
        if "tint" in wet_spec:
            wet_spec["tint"] = [c * 0.5 for c in wet_spec["tint"]]
        if "color" in wet_spec:
            wet_spec["color"] = [c * 0.5 for c in wet_spec["color"]]
        wet_brick = M(wet_spec)
    trim, stone, glass = M(TRIM), M(STONE), M("glass")
    storeys = f["storeys"]
    if f.get("deco"):   # a picture palace, not a canal house (landmarks.deco_front)
        return deco(root, f, W, storeys[0], rng)
    if f.get("classic"):   # a museum's stone front (landmarks.classic_front)
        import landmarks
        landmarks.classic_front(root, f, W, rng)
        return root
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
        a, b = v0 + skin, v1 + skin
        if tide > a:   # (split at the tide line)
            lbox(root, "brick_wet", (u0, a, -T), (u1, min(b, tide), 0.0), wet_brick)
            a = tide
        if b > a:
            lbox(root, "brick", (u0, a, -T), (u1, b, 0.0), brick)
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
    if f.get("metro"):   # a metro station's way in: canopy, name, the sign on its pole
        import landmarks
        landmarks.metro_front(root, f, W, storeys[0], rng)
    if f.get("flags"):   # a grand hotel's flags out over the street
        import landmarks
        landmarks.hotel_flags(root, W, storeys[0] + 0.5, f["flags"])
    if f.get("street_sign"):   # the city's red name plate: white letters and three white crosses
        ss = f["street_sign"]
        u, v = ss.get("u", 0.8), ss.get("v", 2.9)
        lbox(root, "street_sign", (u - 0.62, v - 0.13, 0.0), (u + 0.62, v + 0.13, 0.025), M({"color": [0.42, 0.025, 0.025], "rough": 0.35, "noise": 0.05}))
        white = M({"color": [0.85, 0.85, 0.82], "rough": 0.4, "noise": 0.02})
        text(root, ss["text"], (u + 0.1, v, 0.026), 0.15, white, depth=0.002)
        text(root, "XXX", (u - 0.48, v, 0.026), 0.07, white, depth=0.002)
    top(root, f, W, H, T, brick, trim, stone, rng)
    if f.get("sides") and not skin:   # a house at the end of its row: its own walls back under its roof
        kind = f.get("gable", "cornice")
        hs = H + 0.95 if kind == "cornice" else H
        depth = 9.7
        lbox(root, "side_wall", (0.0, 0.0, -depth), (0.3, hs, -T), brick)
        lbox(root, "side_wall", (W - 0.3, 0.0, -depth), (W, hs, -T), brick)
        lbox(root, "back_wall", (0.0, 0.0, -depth), (W, hs, -depth + 0.3), brick)
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
    u0, u1, n, top_v = layout.shop_bays(W, s0, sh.get("top", 2.8))
    riser = 0.42
    frame = M({"color": sh.get("frame", [0.03, 0.045, 0.035]), "rough": 0.35, "noise": 0.12})
    glass = M("glass")
    door_i = min(sh.get("door_bay", n // 2), n - 1)
    # A shop he can walk into ("enter"): the real room is built behind the glass (its own RoomSpec),
    # and the door bay is left open for the game's glass door. Seen from the next district over
    # (FAR), where that room isn't built, it is a shop like any other.
    enter = sh.get("enter") and not FAR
    da, db = u0 + (u1 - u0) * door_i / n, u0 + (u1 - u0) * (door_i + 1) / n
    for a, b in ((u0, da), (db, u1)) if enter else ((u0, u1),):
        if b - a > 0.02:
            lbox(root, "riser", (a, 0.0, -0.2), (b, riser, -0.12), frame)
    for i in range(n + 1):   # posts
        uu = u0 + (u1 - u0) * i / n
        lbox(root, "shop_post", (uu - 0.05, 0.0, -0.2), (uu + 0.05, top_v, -0.08), frame)
    lbox(root, "shop_head", (u0, top_v - 0.1, -0.2), (u1, top_v, -0.06), frame)
    lbox(root, "transom_bar", (u0, top_v - 0.55, -0.2), (u1, top_v - 0.5, -0.1), frame)
    for i in range(n):
        a, b = u0 + (u1 - u0) * i / n + 0.05, u0 + (u1 - u0) * (i + 1) / n - 0.05
        bottom = 0.0 if i == door_i else riser
        if enter and i == door_i:   # the transom light over the open door only; the game hangs the door
            lbox(root, "shop_glass", (a, top_v - 0.5, -0.165), (b, top_v - 0.1, -0.16), glass)
            continue
        if i in sh.get("smashed", []):   # put in by looters: a jagged corner left, the rest on the pavement
            left = Acc()
            left.quad((a, bottom, -0.163), (a + (b - a) * 0.35, bottom, -0.163), (a, bottom + (top_v - bottom) * 0.4, -0.163), (a, bottom, -0.163))
            left.quad((b, top_v - 0.1, -0.163), (b - (b - a) * 0.5, top_v - 0.1, -0.163), (b, top_v - 0.1 - (top_v - bottom) * 0.3, -0.163), (b, top_v - 0.1, -0.163))
            left.build("shop_glass_left", glass, root, smooth=False)
            import aftermath
            shards = builders.empty_at("shards", (0.0, 0.0, 0.0), 0.0)
            shards.parent = root
            shards.location = g2b(((a + b) / 2, 0.0, 0.0))
            aftermath.broken_glass(shards, {"seed": i + 31}, b - a + 0.6, 0.0, 1.4)
            continue
        lbox(root, "shop_glass", (a, bottom, -0.165), (b, top_v - 0.1, -0.16), glass)
        if i == door_i:   # the glass door: a frame and a long brass push bar
            for c, e in ((a, a + 0.08), (b - 0.08, b)):
                lbox(root, "door_stile", (c, 0.0, -0.17), (e, top_v - 0.55, -0.14), frame)
            lbox(root, "door_rail", (a, 0.0, -0.17), (b, 0.12, -0.14), frame)
            rod(root, "push_bar", (b - 0.16, 0.8, -0.11), (b - 0.16, 1.5, -0.11), 0.015, 0.015, M("brass"))
    if not enter:
        room_card(root, u0 - 0.2, u1 + 0.2, -0.1, top_v + 0.2, -1.6, sh.get("room", "warm_bar"), sh.get("glow", 1.6), rng,
                  span_u=0.06 * W, span_v=0.32)
    # the shop's light out through its window, warm, onto the pavement and whatever stands there
    area_light(root, (W / 2, top_v * 0.55, -0.5), u1 - u0 - 0.2, top_v * 0.8, sh.get("power", 90.0) * W,
               tuple(sh.get("light", (1.0, 0.72, 0.45))))
    # the fascia board with the name lit on it: big enough to read across the square, and lit no
    # brighter than a real one (brighter, the bloom smears the letters into a bar)
    fh = min(0.8, s0 - top_v - 0.15)
    lbox(root, "fascia", (0.15, top_v, -0.05), (W - 0.15, top_v + fh, 0.08), frame)
    sign_m = builders.emissive("sign_" + sh.get("name", "shop")[:12], tuple(sh.get("sign", (1.0, 0.85, 0.6))), sh.get("sign_strength", 2.6))
    size = min(fh * 0.72, 1.55 * (W - 0.6) / max(len(sh.get("name", "x")), 1))
    import city
    if sh.get("neon"):   # bent glass tube, the way the bars and clubs do it
        city.neon_text(root, sh["name"], (W / 2, top_v + fh * 0.5, 0.12), size, sh.get("sign", (1.0, 0.3, 0.6)), sh.get("sign_strength", 5.0),
                       font=sh.get("font", "DejaVuSans-Bold.ttf"), tube=size * 0.03)
    else:
        text(root, sh.get("name", "CAFÉ"), (W / 2, top_v + fh * 0.5, 0.09), size, sign_m, font=sh.get("font", "DejaVuSerif-Bold.ttf"))
    pane = (door_i + 1) % n if n > 1 else 0   # a little neon hung in a window that isn't the door
    if sh.get("window_neon", True):
        word = sh.get("window_word") or {"coffeeshop": "OPEN", "bar": "BIER", "restaurant": "OPEN", "hotel": ""}.get(sh.get("kind"), "OPEN")
        if word:
            a = u0 + (u1 - u0) * (pane + 0.5) / n
            col = sh.get("window_color") or ((1.0, 0.15, 0.1) if word == "OPEN" else (1.0, 0.55, 0.12))
            city.neon_text(root, word, (a, top_v - 1.05, -0.32), 0.24, col, 5.0, font="DejaVuSans-Bold.ttf", tube=0.008)
    if sh.get("blade"):   # a blade sign out over the pavement, lit, both faces
        bu = W - 0.2
        rod(root, "blade_arm", (bu, top_v + 1.25, 0.0), (bu, top_v + 1.25, 0.95), 0.02, 0.02, M(IRON))
        lbox(root, "blade", (bu - 0.04, top_v + 0.45, 0.2), (bu + 0.04, top_v + 1.2, 0.9), frame)
        for sgn in (-1, 1):
            text(root, sh["blade"], (bu + sgn * 0.045, top_v + 0.82, 0.55), 0.13, sign_m, yaw=90 * sgn,
                 font=sh.get("font", "DejaVuSerif-Bold.ttf"))
    if sh.get("shutter"):   # the roller shutter pulled down over the glass ("shutter": how far, 0..1), ribbed steel
        drop = sh["shutter"]
        steel = M({"color": [0.42, 0.44, 0.46], "rough": 0.45, "metal": 0.7, "noise": 0.35})
        y0 = top_v - (top_v - 0.0) * drop
        lbox(root, "shutter_box", (u0 - 0.05, top_v - 0.05, -0.12), (u1 + 0.05, top_v + 0.25, 0.1), steel)
        lbox(root, "shutter", (u0, y0, -0.06), (u1, top_v, -0.04), steel)
        ribs = Acc()
        y = y0 + 0.08
        while y < top_v - 0.05:
            ribs.box((u0, y, -0.04), (u1, y + 0.02, -0.025))
            y += 0.1
        ribs.build("shutter_ribs", M({"color": [0.3, 0.32, 0.34], "rough": 0.5, "metal": 0.6}), root, smooth=False)
        if sh.get("tag"):   # sprayed on it
            text(root, sh["tag"], ((u0 + u1) / 2, (y0 + top_v) / 2, -0.02), 0.32, M({"color": list(sh.get("tag_color", (0.75, 0.05, 0.05))), "rough": 0.6}),
                 font="DejaVuSans-Bold.ttf", depth=0.0)
    if sh.get("cross"):   # an apotheek: the green neon cross out over the pavement
        import landmarks
        landmarks.green_cross(root, (W - 0.2, top_v + 1.0, 0.75))
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


def deco(root, f, W, s0, rng):
    """A cinema front: its glazed doors between two towers (the shopfront's, set in by the towers'
    width, so its door bay is facade.shop_door(W - 2 * tower_w) along from the first tower), the tiled
    wall round them up to the marquee, the rest landmarks.deco_front."""
    import landmarks
    tw = f["deco"].get("tower_w", 3.2)
    tiles = M(f["deco"].get("tiles", {"color": [0.62, 0.66, 0.56], "rough": 0.35, "noise": 0.1}))
    top_v = layout.shop_bays(W - 2 * tw, s0, f["shop"].get("top", 2.8))[3]
    lbox(root, "deco_band", (tw, top_v, -0.4), (W - tw, s0, -0.05), tiles)
    for u0, u1 in ((tw, tw + 0.3), (W - tw - 0.3, W - tw)):
        lbox(root, "deco_pier", (u0, 0.0, -0.4), (u1, top_v, 0.0), tiles)
    doors = builders.empty_at("cinema_doors", (0.0, 0.0, 0.0), 0.0)
    doors.parent = root
    doors.location = g2b((tw, 0.0, 0.0))
    shopfront(doors, f, W - 2 * tw, s0, rng)
    landmarks.deco_front(root, f, W, s0, rng)
    return root


def facade_row(x_from, x_to, z, facing, rng, row=None, y=0.0):
    """A row of canal houses from x_from to x_to on the line z (facing south or north), or from z
    x_from to x_to on the line x = z (facing east or west): random widths, heights and gables, their
    street at height y. row: {"lit", "shops": fraction of ground floors that are shops, "shop_kinds",
    "row_ends": "start" | "end" | "both": close that end house's walls (a row ending in open space),
    "lean": [lo, hi] degrees out over the street and "tilt": up to that many sideways (houses on
    piles that have settled every way, as along the Damrak)}."""
    row = row or {}
    along_z = facing in ("east", "west")
    ends = row.get("row_ends", "")
    x = x_from
    while x < x_to:
        w = rng.uniform(5.0, 9.5)
        kind = rng.choice(["neck", "neck", "bell", "step", "cornice", "spout", "cornice"]) if w < 8.5 else "cornice"
        n = rng.choice([4, 4, 5, 3])
        storeys = [rng.uniform(3.4, 3.9)] + [rng.uniform(2.9, 3.3) for _ in range(n - 1)]
        bays = 3 if w < 7.5 else 5 if w > 8.6 else 4
        f = {"y": y, "facing": facing, "storeys": storeys, "bays": bays, "gable": kind,
             "door_bay": rng.randrange(bays), "stoop": rng.choice([0.0, 0.5, 0.75]), "lit": row.get("lit", 0.2)}
        span, last = layout.row_span(x, w, x_to)   # the last house ends where the row does, not out in the street
        if span < w:   # (cut short: fewer windows across)
            f["bays"] = min(bays, max(2, int(span / 1.6)))
            f["door_bay"] = min(f["door_bay"], f["bays"] - 1)
        f.update({"z0": x, "z1": x + span - 0.04, "x": z} if along_z else {"x0": x, "x1": x + span - 0.04, "z": z})
        if rng.random() < row.get("shops", 0.0):
            f["stoop"] = 0.0
            f["shop"] = shop_for(rng, row.get("shop_kinds"))
        if rng.random() < 0.12:
            f["paint"] = {"color": rng.choice([[0.6, 0.58, 0.54], [0.18, 0.2, 0.21], [0.42, 0.4, 0.34]]), "rough": 0.8, "noise": 0.15}
        if (x == x_from and ends in ("start", "both")) or (last and ends in ("end", "both")):
            f["sides"] = True
        if row.get("lean"):   # a row that has settled every way: forward ([lo, hi] degrees) and sideways (+/- tilt)
            f["lean"] = rng.uniform(*row["lean"])
            f["tilt"] = rng.uniform(-1.0, 1.0) * row.get("tilt", 0.0)
        facade(f, rng)
        if last:
            break
        x += span


SHOPS = {   # what a city ground floor might be, with names made up for the game (no real business)
    "cafe": [("CAFÉ DE KROONLUCHTER", "warm_bar"), ("CAFÉ 'T HOEKJE", "warm_bar"), ("EETCAFÉ DE ZWAAN", "warm_restaurant_night")],
    "coffeeshop": [("COFFEESHOP GROENE VLINDER", "warm_bar"), ("COFFEESHOP HAZE", "warm_bar"), ("THE LAZY OWL COFFEESHOP", "warm_bar")],
    "restaurant": [("RISTORANTE DA PIETRO", "warm_restaurant_night"), ("STEAKHOUSE EL GAUCHO", "warm_restaurant_night"),
                   ("PANNENKOEKENHUIS", "warm_restaurant_night")],
    "bar": [("CLUB NACHTVLINDER", "warm_bar"), ("BAR ZEVEN", "warm_bar"), ("KARAOKE", "warm_bar")],
}
SHOP_LOOK = {   # sign colour, frame colour, font, awning
    "cafe": ((1.0, 0.8, 0.5), (0.2, 0.05, 0.035), "DejaVuSerif-BoldItalic.ttf", None),
    "coffeeshop": ((0.35, 1.0, 0.4), (0.03, 0.12, 0.05), "DejaVuSans-Bold.ttf", [[0.05, 0.3, 0.08], [0.85, 0.75, 0.1]]),
    "restaurant": ((1.0, 0.25, 0.15), (0.06, 0.05, 0.05), "DejaVuSerif-Bold.ttf", [[0.45, 0.06, 0.05], [0.78, 0.74, 0.66]]),
    "bar": ((1.0, 0.2, 0.6), (0.03, 0.03, 0.04), "DejaVuSans-Bold.ttf", None),
}


def shop_for(rng, kinds=None):
    """A made-up shop for a ground floor: its name, the room inside, its colours."""
    kind = rng.choice(kinds or list(SHOPS))
    name, room = rng.choice(SHOPS[kind])
    sign, frame, font, awning = SHOP_LOOK[kind]
    s = {"name": name, "kind": kind, "room": room, "sign": list(sign), "frame": list(frame), "font": font,
         "blade": name.split()[-1] if len(name) > 12 else name, "glow": 0.6, "power": rng.uniform(60.0, 95.0)}
    if awning:
        s["awning"] = awning
    return s


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
def canal(c, rng):
    """A canal beside the street: the water between two quay walls, and across it the far quay with
    its lamps, trees and houses. It runs along x on the line z = "z" ("axis": "x", the default) or
    along z on the line x = "x" ("axis": "z", with "along": [z0, z1]); the water lies on the far
    side of the line ("side": 1, +z or +x) or the near ("side": -1). "ends": quay walls across the
    water at both ends too (a canal that stops at a bridge), or only at "a" (its start) or "b" (its
    end). "far_span": [from, to] along it for the far bank's houses (default: short of both ends);
    "far_furniture": False when they stand straight up out of the water (no lamps or trees on the
    far quay)."""
    along_x = c.get("axis", "x") == "x"
    line = c["z"] if along_x else c["x"]
    a0, a1 = c.get("x", [-60.0, 100.0]) if along_x else c["along"]
    sd = c.get("side", 1)
    width, water, fq = c["width"], c.get("water", -1.6), c.get("far_quay", 6.0)
    far = line + sd * width

    def box(name, u0, u1, y0, y1, w0, w1, m):   # u along the canal, w across it
        w0, w1 = min(w0, w1), max(w0, w1)
        if along_x:
            builders.box_aabb(name, (u0, y0, w0), (u1, y1, w1), m)
        else:
            builders.box_aabb(name, (w0, y0, u0), (w1, y1, u1), m)

    def at(u, w):
        return (u, w) if along_x else (w, u)

    quay = M({"ph": "mossy_brick", "scale": 1.0})
    box("canal", a0, a1, water - 0.02, water, line, far, M("canal_water"))
    box("canal_bed", a0, a1, water - 3.0, water - 2.9, line, far, M({"color": [0.01, 0.012, 0.01], "rough": 1.0}))
    for k, (wa, wb) in enumerate(((line - sd * 0.3, line), (far, far + sd * 0.3))):
        gaps = c.get("gaps", []) if k == 0 else []
        us = [a0] + [v for gp in sorted(gaps) for v in gp] + [a1]
        for u0, u1 in zip(us[::2], us[1::2]):
            box("quay_wall", u0, u1, water - 3.0, 0.0, wa, wb, quay)
            box("quay_edge", u0, u1, -0.08, 0.04, wa - 0.05, wb + 0.05, M(STONE))
    ends = c.get("ends")
    for which, (u0, u1) in (("a", (a0 - 0.3, a0)), ("b", (a1, a1 + 0.3))):
        if ends is True or ends == which:
            box("quay_wall", u0, u1, water - 3.0, 0.0, line, far, quay)
    box("far_quay", a0, a1, -0.4, 0.0, far + sd * 0.3, far + sd * fq,
        M(c.get("far_ground", {"ph": "herringbone_brick", "tint": [0.7, 0.65, 0.6], "wet": 0.6})))
    u = a0 + 24
    while c.get("far_furniture", True) and u < a1 - 24:   # the far quay: lamps, trees, parked cars, nobody
        lamp(*at(u, far + sd * 1.0), power=c.get("far_lamp_power", 420.0))
        tx, tz = at(u + 7.0, far + sd * 1.2)
        builders.build_prop({"type": "plane_tree", "pos": [tx, 0.0, tz], "size": [0.45, 12.0, 0.45],
                             "seed": int(u * 7) % 997, "depth": 5}, 12.0)
        u += 14.0
    if c.get("far_houses", True):
        facing = ("north" if sd > 0 else "south") if along_x else ("west" if sd > 0 else "east")
        f0, f1 = c.get("far_span", [a0 + 20, a1 - 20])
        facade_row(f0, f1, far + sd * fq, facing, rng, dict(c, row_ends=c.get("row_ends", "both")))


def outdoor(spec):
    """Everything an "outdoor" RoomSpec stands in: its ground slabs, the quay wall and the canal,
    the far quay with its lamps, trees and houses, the fronts on its own side, its lamps, the bridge
    (built whichever room is being rendered: it's the world outside every window)."""
    global _ROOMS, FAR, TIDE
    o = spec["outdoor"]
    FAR = bool(spec.get("_far"))
    TIDE = o.get("tide", 0.0)
    _ROOMS = o.get("window_rooms", _ROOMS)
    rng = random.Random(spec["id"])
    for g in o.get("ground", []):
        (gx0, gz0), (gx1, gz1) = g["min"], g["max"]
        y = g.get("y", 0.0)
        builders.box_aabb(g.get("name", "ground"), (gx0, y - 0.4, gz0), (gx1, y, gz1), M(g.get("material", STONE)))
        if g.get("kerb"):   # a granite kerb along the ground's far edge
            builders.box_aabb("kerb", (gx0, y - 0.4, gz1 - 0.18), (gx1, y + 0.03, gz1), M(STONE))
    for c in ([o["canal"]] if o.get("canal") else []) + o.get("canals", []):
        canal(c, rng)
    for f in o.get("facades", []):
        facade(f, random.Random(f.get("seed", 1)))
    for i, row in enumerate(o.get("rows", [])):   # streets running on out of the set: rows of houses (some shops)
        facade_row(row["from"], row["to"], row["line"], row["facing"], random.Random(f"{spec['id']}{i}"), row)
    for lx, lz in o.get("lamps", []):
        lamp(lx, lz, power=o.get("lamp_power", 380.0))
    for b in o.get("bridges", []):
        hump_bridge(spec, b)
    import city   # the squares' pieces: strings of lights, trams, parks, rooftop neon
    city.extras(spec)


PROPS = {"bollard": bollard, "bike": bike, "elm": plane_tree, "plane_tree": plane_tree, "railing": railing,
         "rowboat": rowboat, "houseboat": houseboat, "heater": heater}
kit.PROPS.update(PROPS)
