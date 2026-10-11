# damned_waters/tools/blender/street.py
# Purpose: the outdoor set kit (Blender side), for RoomSpecs marked "outdoor": the street and quay
# under him, the canal, the houses on both banks (fronts laid out by tools/pipeline/facade.py:
# brick, white sash windows, stone sills, cornices and gables, a few windows lit), and the things
# of an Amsterdam canal at night: Amsterdammertjes (the brown bollards with three crosses), black
# bikes, bare elms, a hump bridge with lamps along its arches, a houseboat, a rowing boat.
# Coordinates are a prop's local Godot frame (x right, y up, z front), as in builders.part().
#
# ELI5: kit.py furnishes rooms; this furnishes a street. The far bank is real houses, not a painted
# backdrop, so a window across the water can be lit and its light can wobble in the canal.
import math
import random

import bpy

import builders
import facade as layout
import kit
from roomspec import g2b

BRICK = ["ph:brick_wall_003", "ph:red_brick_03"]
STONE = {"color": [0.22, 0.21, 0.19], "rough": 0.75, "noise": 0.3}
TRIM = {"color": [0.58, 0.56, 0.52], "rough": 0.5, "noise": 0.1}
IRON = {"color": [0.02, 0.02, 0.022], "rough": 0.45, "metal": 0.7, "noise": 0.1}


def M(key):
    return builders.material(key)


# ── Mesh helpers (all in a parent's local Godot frame) ─────────────────────────────
def lbox(parent, name, lo, hi, m):
    """A box from local min to max corners; UVs from local coordinates, so bricks run on across boxes."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return kit.mesh(name, v, f, m, parent)


def rod(parent, name, a, b, r0, r1, m, seg=8):
    """A tapered round bar from a to b (radius r0 at a, r1 at b)."""
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
    return kit.mesh(name, verts, faces, m, parent, smooth=True)


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


# ── Canal-house fronts ──────────────────────────────────────────────────────────────
def facade(f, rng, parent=None):
    """One house front. f: {"x0", "x1", "z", "facing": "south"|"north", "storeys": [m, ...] bottom
    up, "bays", "gable": kind, "gable_h", "brick", "lit", "door_bay", "stoop", "skin_below", "holes",
    "paint"}. Facing south it stands on z with its front toward +z (the street). "skin_below": up
    to that height only a thin brick skin goes on (a house the game walks in: its rooms have the real
    walls and windows), with "holes" [{"u0", "u1", "v0", "v1", "arch"}] where they are."""
    W = f["x1"] - f["x0"]
    south = f.get("facing", "south") == "south"
    root = builders.empty_at("facade", (f["x0"] if south else f["x1"], f.get("y", 0.0), f["z"]), 0.0 if south else 180.0)
    if parent is not None:
        root.parent = parent
    T = 0.3
    brick_key = f.get("brick") or rng.choice(BRICK)
    tint = f.get("tint", [rng.uniform(0.22, 0.38)] * 3)
    brick = M(f["paint"]) if f.get("paint") else M({"ph": brick_key[3:], "tint": tint, "scale": 1.0})
    trim, stone, glass = M(TRIM), M(STONE), M({"color": [0.008, 0.01, 0.014], "rough": 0.04, "noise": 0.0})
    lit = builders.emissive("house_window", (1.0, 0.58, 0.28), rng.uniform(2.0, 4.5))
    dark_room = M({"color": [0.012, 0.012, 0.016], "rough": 0.9, "noise": 0.2})
    curtain = M({"color": rng.choice([[0.3, 0.06, 0.05], [0.12, 0.16, 0.1], [0.5, 0.45, 0.35]]), "rough": 0.95, "noise": 0.3})
    storeys = f["storeys"]
    stoop = f.get("stoop", 0.0)
    g = layout.window_grid(W, storeys, f.get("bays", 3), f.get("win_w", 1.05), f.get("door_bay"))
    H = g["height"]
    skin = f.get("skin_below", 0.0)
    wins = [w for w in g["windows"] if w[2] >= skin]
    door = g["door"] if skin <= 0 else None
    if door and stoop:
        door = (door[0], door[1], stoop, stoop + 2.4)
    holes = [w for w in wins] + ([door] if door else [])
    # the brick: full thickness above the skin line, cut around the windows
    for u0, u1, v0, v1 in layout.cut_rects(W, H - skin, [(a, b, c - skin, d - skin) for a, b, c, d in holes]):
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
                    # from the top corner: down the jamb to the spring line, then round to the crown
                    arc = [(uc + sgn * r * math.cos(math.pi / 2 * k / 8), ys + r * math.sin(math.pi / 2 * k / 8)) for k in range(9)]
                    kit.prism(root, "skin_arch", [(corner, h["v1"])] + arc, 0.025, brick, ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
            if h["v0"] > 0.2:   # a stone sill under the house's own window, so it reads from the street
                lbox(root, "sill", (h["u0"] - 0.06, h["v0"] - 0.07, 0.0), (h["u1"] + 0.06, h["v0"], 0.09), stone)
    # windows: a white sash frame set back in the reveal, glazing bars, glass, the room behind
    for k, (u0, u1, v0, v1) in enumerate(wins):
        d0 = -0.11
        for a, b, c, e in ((u0, u0 + 0.07, v0, v1), (u1 - 0.07, u1, v0, v1), (u0, u1, v0, v0 + 0.07), (u0, u1, v1 - 0.07, v1),
                           (u0, u1, v0 + (v1 - v0) * 0.52, v0 + (v1 - v0) * 0.52 + 0.05),
                           ((u0 + u1) / 2 - 0.018, (u0 + u1) / 2 + 0.018, v0, v1)):
            lbox(root, "sash", (a, c, d0 - 0.05), (b, e, d0), trim)
        for fr in (0.26, 0.78):
            vv = v0 + (v1 - v0) * fr
            lbox(root, "bar", (u0, vv - 0.012, d0 - 0.04), (u1, vv + 0.012, d0 - 0.01), trim)
        lbox(root, "glass", (u0, v0, d0 - 0.035), (u1, v1, d0 - 0.03), glass)
        on = rng.random() < f.get("lit", 0.08)
        lbox(root, "room", (u0 - 0.2, v0 - 0.2, -T - 0.45), (u1 + 0.2, v1 + 0.2, -T - 0.44), lit if on else dark_room)
        if rng.random() < 0.5:   # curtains, half drawn
            cw = (u1 - u0) * rng.uniform(0.18, 0.4)
            lbox(root, "curtain", (u0, v0, -T - 0.2), (u0 + cw, v1, -T - 0.17), curtain)
            lbox(root, "curtain", (u1 - cw, v0, -T - 0.2), (u1, v1, -T - 0.17), curtain)
        lbox(root, "sill", (u0 - 0.06, v0 - 0.08, -0.04), (u1 + 0.06, v0, 0.07), stone)
        lbox(root, "lintel", (u0 - 0.04, v1, -0.01), (u1 + 0.04, v1 + 0.1, 0.015), stone)
    if door:   # a panelled front door set back, a fanlight above it, a stone stoop
        u0, u1, v0, v1 = door
        lbox(root, "door", (u0, v0, -0.22), (u1, v1, -0.18), M({"color": [0.02, 0.05, 0.035], "rough": 0.35, "noise": 0.15}))
        for a, b, c, e in ((u0 - 0.08, u0, v0, v1 + 0.1), (u1, u1 + 0.08, v0, v1 + 0.1), (u0, u1, v1, v1 + 0.1)):
            lbox(root, "door_frame", (a, c, -0.02), (b, e, 0.03), trim)
        if stoop:
            for s in range(3):
                h0 = stoop * s / 3
                lbox(root, "stoop", (u0 - 0.5, h0, 0.0), (u1 + 0.5, h0 + stoop / 3, 1.0 - s * 0.3), stone)
            for sx in (u0 - 0.5, u1 + 0.5):
                rod(root, "stoop_rail", (sx, stoop, 0.95), (sx, stoop + 0.9, 0.95), 0.015, 0.015, M(IRON))
    # the top: a cornice, or a gable with stone coping, a hoist beam, the roof behind
    kind = f.get("gable", "cornice")
    lbox(root, "string_course", (-0.05, H - 0.12, -T), (W + 0.05, H, 0.06), trim)
    if kind == "cornice":
        lbox(root, "cornice", (-0.15, H, -T), (W + 0.15, H + 0.4, 0.38), trim)
        lbox(root, "cornice_fascia", (-0.1, H + 0.4, -T), (W + 0.1, H + 0.75, 0.0), brick)
        roof = [(-W / 2, 0.0), (W / 2, 0.0), (0.0, 3.2)]
        fan_prism(root, "roof", roof, (0.0, 0.5), -9.0, M({"color": [0.05, 0.05, 0.055], "rough": 0.7, "noise": 0.3}),
                  ((W / 2, H + 0.75, -T - 0.4), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    else:
        hg = f.get("gable_h", rng.uniform(3.0, 4.2))
        poly = layout.gable_outline(kind, W, hg)
        fan_prism(root, "gable", poly, (0.0, 0.2), -T, brick, ((W / 2, H, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
        coping = [(u * 1.0 + (0.06 if u > 0 else -0.06 if u < 0 else 0.0), v + 0.07) for u, v in poly]
        coping[0], coping[-1] = (poly[0][0] - 0.06, 0.0), (poly[-1][0] + 0.06, 0.0)
        fan_prism(root, "coping", coping, (0.0, 0.2), -T + 0.05, M(TRIM), ((W / 2, H, -0.04), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
        lbox(root, "gable_window", (W / 2 - 0.35, H + hg * 0.32, 0.0), (W / 2 + 0.35, H + hg * 0.32 + 0.9, 0.02), glass)
        for a, b, c, e in ((-0.4, -0.33, 0.0, 0.9), (0.33, 0.4, 0.0, 0.9), (-0.4, 0.4, -0.07, 0.0), (-0.4, 0.4, 0.9, 0.97)):
            lbox(root, "gable_frame", (W / 2 + a, H + hg * 0.32 + c, 0.0), (W / 2 + b, H + hg * 0.32 + e, 0.04), trim)
        wood = M({"ph": "dark_wood", "tint": [0.3, 0.24, 0.2]})
        hb = H + hg * 0.68
        lbox(root, "hoist_beam", (W / 2 - 0.09, hb, -0.2), (W / 2 + 0.09, hb + 0.2, 0.85), wood)
        rod(root, "hoist_hook", (W / 2, hb, 0.75), (W / 2, hb - 0.35, 0.75), 0.012, 0.012, M(IRON))
        roof = [(-W / 2 + 0.2, 0.0), (W / 2 - 0.2, 0.0), (0.0, hg * 0.8)]
        fan_prism(root, "roof", roof, (0.0, 0.3), -10.0, M({"color": [0.05, 0.05, 0.055], "rough": 0.7, "noise": 0.3}),
                  ((W / 2, H, -T - 0.05), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    return root


def facade_row(x_from, x_to, z, facing, rng, spec_row=None, y=0.0):
    """A row of canal houses along z from x_from to x_to, random widths, heights and gables, their
    street at height y."""
    x = x_from
    while x < x_to:
        w = rng.uniform(5.0, 9.5)
        kind = rng.choice(["neck", "neck", "bell", "step", "cornice", "spout", "cornice"]) if w < 8.5 else "cornice"
        n = rng.choice([4, 4, 5, 3])
        storeys = [rng.uniform(3.3, 3.9)] + [rng.uniform(2.8, 3.3) for _ in range(n - 1)]
        bays = 3 if w < 7.5 else 5 if w > 8.6 else 4
        f = {"x0": x, "x1": x + w - 0.04, "z": z, "y": y, "facing": facing, "storeys": storeys, "bays": bays, "gable": kind,
             "door_bay": rng.randrange(bays), "stoop": rng.choice([0.0, 0.5, 0.75]), "lit": (spec_row or {}).get("lit", 0.08)}
        if rng.random() < 0.15:
            f["paint"] = {"color": rng.choice([[0.6, 0.58, 0.54], [0.25, 0.27, 0.28], [0.45, 0.42, 0.36]]), "rough": 0.8, "noise": 0.15}
        facade(f, rng)
        x += w


# ── Street furniture ────────────────────────────────────────────────────────────────
def bollard(root, p, w, h, d):
    """An Amsterdammertje: a cast-iron post in Amsterdam's brown-red, with the city's three white
    St Andrew's crosses down its front."""
    iron = M(p.get("material", {"color": [0.17, 0.05, 0.035], "rough": 0.45, "metal": 0.4, "noise": 0.2}))
    r = w / 2
    kit.lathe(root, "post", [(0.0, 0.0), (r * 1.1, 0.0), (r, 0.05), (r * 0.92, h * 0.85), (r * 1.02, h * 0.88), (r * 0.8, h * 0.95),
                             (r * 0.3, h), (0.0, h)], iron, segments=16)
    white = M({"color": [0.75, 0.74, 0.7], "rough": 0.5, "noise": 0.05})
    for k in range(3):
        y = h * (0.64 - k * 0.15)
        for sgn in (-1, 1):
            a, b = (-0.035, y - sgn * 0.035), (0.035, y + sgn * 0.035)
            ob = rod(root, "cross", (a[0], a[1], r * 0.93), (b[0], b[1], r * 0.93), 0.008, 0.008, white, seg=4)


def bike(root, p, w, h, d):
    """A black Dutch upright bike (an omafiets): two wheels, the frame, a rear rack, mudguards, a
    saddle and swept-back bars. Its length runs along local x."""
    black = M(p.get("material", {"color": [0.015, 0.015, 0.017], "rough": 0.35, "metal": 0.5, "noise": 0.1}))
    rubber = M({"color": [0.01, 0.01, 0.01], "rough": 0.8, "noise": 0.05})
    R = 0.34
    wb = 1.12
    rear, front = (-wb / 2, R, 0.0), (wb / 2, R, 0.0)
    for c in (rear, front):
        ring = 20
        for k in range(ring):
            a0, a1 = 2 * math.pi * k / ring, 2 * math.pi * (k + 1) / ring
            p0 = (c[0] + R * math.cos(a0), c[1] + R * math.sin(a0), 0.0)
            p1 = (c[0] + R * math.cos(a1), c[1] + R * math.sin(a1), 0.0)
            rod(root, "tyre", p0, p1, 0.022, 0.022, rubber, seg=5)
        for k in range(6):
            a = math.pi * k / 6
            rod(root, "spoke", (c[0] - R * 0.95 * math.cos(a), c[1] - R * 0.95 * math.sin(a), 0.0),
                (c[0] + R * 0.95 * math.cos(a), c[1] + R * 0.95 * math.sin(a), 0.0), 0.002, 0.002, black, seg=3)
    crank = (-0.05, R - 0.02, 0.0)
    seat = (-0.2, 0.95, 0.0)
    head = (0.4, 0.98, 0.0)
    for a, b in ((rear, crank), (crank, seat), (seat, rear), (crank, head), (head, front), (seat, (0.38, 0.86, 0.0))):
        rod(root, "frame", a, b, 0.016, 0.016, black, seg=6)
    rod(root, "seat_post", seat, (seat[0] - 0.03, 1.05, 0.0), 0.012, 0.012, black, seg=6)
    kit.soft(root, "saddle", (seat[0] - 0.04, 1.08, 0.0), (0.26, 0.06, 0.16), M({"color": [0.05, 0.03, 0.02], "rough": 0.6}), 0.02, 2)
    rod(root, "stem", head, (0.36, 1.12, 0.0), 0.014, 0.014, black, seg=6)
    for sz in (-1, 1):
        rod(root, "bar", (0.36, 1.12, 0.0), (0.2, 1.1, sz * 0.27), 0.011, 0.011, black, seg=6)
    for c in (rear, front):   # mudguards: half rings over each wheel
        for k in range(9):
            a0, a1 = math.pi * (0.1 + 0.8 * k / 9), math.pi * (0.1 + 0.8 * (k + 1) / 9)
            rod(root, "guard", (c[0] + 0.39 * math.cos(a0), c[1] + 0.39 * math.sin(a0), 0.0),
                (c[0] + 0.39 * math.cos(a1), c[1] + 0.39 * math.sin(a1), 0.0), 0.03, 0.03, black, seg=4)
    builders.part(root, "rack", (rear[0] + 0.05, 0.78, 0.0), (0.42, 0.02, 0.16), black)


def elm(root, p, w, h, d):
    """A bare elm, as the canals' trees stand in October's dark: a leaning trunk forking into
    limbs, the limbs into branches, thinning to twigs (random but fixed by "seed")."""
    rng = random.Random(p.get("seed", 7))
    bark = M(p.get("material", {"color": [0.035, 0.032, 0.03], "rough": 0.85, "noise": 0.4, "noise_scale": 18.0}))
    trunk_h = h * 0.38
    lean = (rng.uniform(-0.25, 0.25), trunk_h, rng.uniform(-0.25, 0.25))
    rod(root, "trunk", (0.0, -0.05, 0.0), lean, w / 2, w / 2 * 0.75, bark, seg=10)

    def grow(a, direction, length, r, depth):
        b = tuple(a[i] + direction[i] * length for i in range(3))
        rod(root, "limb", a, b, r, r * 0.68, bark, seg=max(4, 8 - 2 * (4 - depth)))
        if depth == 0:
            return
        for _ in range(2 if depth < 2 else rng.choice([2, 3])):
            yaw = rng.uniform(0, 2 * math.pi)
            spread = rng.uniform(0.35, 0.7)
            nd = [direction[0] + math.cos(yaw) * spread, direction[1] + rng.uniform(-0.05, 0.25), direction[2] + math.sin(yaw) * spread]
            nl = math.sqrt(sum(c * c for c in nd))
            grow(b, [c / nl for c in nd], length * rng.uniform(0.62, 0.8), r * 0.62, depth - 1)

    for k in range(3):
        yaw = 2 * math.pi * k / 3 + rng.uniform(-0.4, 0.4)
        dn = [math.cos(yaw) * 0.45, 1.0, math.sin(yaw) * 0.45]
        nl = math.sqrt(sum(c * c for c in dn))
        grow(lean, [c / nl for c in dn], h * 0.22, w / 2 * 0.6, 4)
    kit.lathe(root, "tree_pit", [(0.0, 0.0), (0.55, 0.0), (0.55, 0.03), (0.0, 0.03)], M({"color": [0.02, 0.018, 0.015], "rough": 1.0}), segments=4)


def railing(root, p, w, h, d):
    """A low iron quay railing along local x: posts every metre, a top rail and a mid rail."""
    iron = M(p.get("material", IRON))
    n = max(1, int(round(w / 1.0)))
    for k in range(n + 1):
        x = -w / 2 + w * k / n
        rod(root, "post", (x, 0.0, 0.0), (x, h, 0.0), 0.022, 0.02, iron, seg=6)
    for y in (h, h * 0.45):
        rod(root, "rail", (-w / 2, y, 0.0), (w / 2, y, 0.0), 0.02, 0.02, iron, seg=6)


def hull(root, name, L, Wd, D, m, rng=None, open_top=True):
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
    paint = M({"color": [0.08, 0.16, 0.14], "rough": 0.6, "noise": 0.3})
    hull(root, "hull", w, d, h, paint)
    for x in (-w * 0.2, w * 0.12):
        builders.part(root, "thwart", (x, h * 0.72, 0.0), (0.22, 0.03, d * 0.85), wood)
    builders.part(root, "gunwale_l", (0.0, h, -d / 2 + 0.03), (w * 0.85, 0.04, 0.05), wood)
    builders.part(root, "gunwale_r", (0.0, h, d / 2 - 0.03), (w * 0.85, 0.04, 0.05), wood)
    if p.get("swamped", True):
        builders.part(root, "bilge", (0.0, h * 0.55, 0.0), (w * 0.8, 0.01, d * 0.72), M("water"))
    rod(root, "oar", (-w * 0.3, h * 0.8, -d * 0.2), (w * 0.35, h * 0.95, d * 0.35), 0.022, 0.022, wood, seg=6)


def houseboat(root, p, w, h, d):
    """A converted barge: a black steel hull, a long timber cabin with square windows (one lit),
    a deck with pots and a bike, a plank to the quay. Length along local x."""
    rng = random.Random(p.get("seed", 3))
    steel = M({"color": [0.02, 0.022, 0.025], "rough": 0.5, "metal": 0.4, "noise": 0.25})
    hull(root, "hull", w, d, 1.0, steel)
    builders.part(root, "deck", (0.0, 1.0, 0.0), (w * 0.94, 0.06, d * 0.9), M({"ph": "dark_wood", "tint": [0.25, 0.22, 0.2]}))
    cl = w * 0.62
    cab = M(p.get("cabin", {"color": [0.16, 0.2, 0.17], "rough": 0.7, "noise": 0.25}))
    lbox(root, "cabin", (-cl / 2 - w * 0.08, 1.0, -d * 0.38), (cl / 2 - w * 0.08, 1.0 + h - 1.0, d * 0.38), cab)
    lbox(root, "cabin_roof", (-cl / 2 - w * 0.1, h, -d * 0.42), (cl / 2 - w * 0.06, h + 0.08, d * 0.42), M({"color": [0.04, 0.04, 0.045], "rough": 0.8}))
    glass = M({"color": [0.01, 0.012, 0.016], "rough": 0.05})
    lit = builders.emissive("boat_window", (1.0, 0.55, 0.26), 3.0)
    n = int(cl / 1.3)
    for k in range(n):
        x = -cl / 2 - w * 0.08 + cl * (k + 0.5) / n
        for sz in (-1, 1):
            on = p.get("lit_window", -1) == k and sz > 0
            lbox(root, "porthole", (x - 0.35, 1.45, sz * d * 0.38 - 0.01), (x + 0.35, 1.95, sz * d * 0.38 + 0.01), lit if on else glass)
    for k in range(4):
        x = cl / 2 + rng.uniform(0.0, w * 0.15) - w * 0.05
        kit.lathe(root, "pot", [(0.0, 0.0), (0.16, 0.0), (0.2, 0.3), (0.0, 0.3)], M({"color": [0.25, 0.12, 0.07], "rough": 0.8}),
                  at=(x, 1.03, rng.uniform(-d * 0.3, d * 0.3)), segments=10)
        ball(root, "shrub", (x, 1.45, rng.uniform(-d * 0.3, d * 0.3)), 0.22, M({"color": [0.03, 0.05, 0.02], "rough": 0.9, "noise": 0.5}), seg=8)
    if p.get("plank"):
        lbox(root, "plank", (p["plank"] - 0.3, 1.02, d / 2 - 0.1), (p["plank"] + 0.3, 1.08, d / 2 + 1.6), M({"ph": "dark_wood"}))


# ── The bridge ──────────────────────────────────────────────────────────────────────
def hump_bridge(spec, b):
    """A brick hump bridge over the canal along z: arches to the water with a lamp bulb every 40 cm
    round each arch on both faces, a cobbled deck rising to the middle, iron railings.
    b: {"x0", "x1", "z0", "z1", "hump", "water", "deck": material, "arches": [[z_centre, span, rise], ...]}."""
    x0, x1, z0, z1 = b["x0"], b["x1"], b["z0"], b["z1"]
    water, hump = b.get("water", -1.6), b.get("hump", 1.3)
    brick = M({"ph": "red_brick_03", "tint": [0.3, 0.2, 0.17]})
    deck_m = M(b["deck"]) if b.get("deck") else M(STONE)
    bulb = builders.emissive("bridge_bulb", (1.0, 0.62, 0.25), 9.0)
    arches = b.get("arches", [])

    def top(z):
        t = (z - z0) / (z1 - z0)
        return hump * math.sin(math.pi * min(1.0, max(0.0, t)))

    def soffit(z):   # the underside: an arch's curve over its span, else down to the water
        for zc, span, rise in arches:
            if abs(z - zc) < span / 2:
                return water + 0.0 + (rise + 0.0) * math.sqrt(max(0.0, 1 - ((z - zc) / (span / 2)) ** 2)) + 0.6
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
    for zc, span, rise in arches:   # the bulbs round each arch, both faces
        n = int(math.pi * span / 2 / 0.4)
        for k in range(n + 1):
            a = math.pi * k / n
            zz = zc - math.cos(a) * span / 2 * 1.04
            yy = water + 0.6 + rise * math.sin(a) * 1.04 + 0.05
            for xe in (x0 - 0.04, x1 + 0.04):
                builders.box_aabb("bulb", (xe - 0.035, yy - 0.035, zz - 0.035), (xe + 0.035, yy + 0.035, zz + 0.035), bulb)
    railing_m = M(IRON)
    for xe in (x0 + 0.12, x1 - 0.12):   # railings following the hump
        root = builders.empty_at("bridge_rail", (0.0, 0.0, 0.0))
        n = int((z1 - z0) / 1.0)
        pts = [(xe, top(z0 + (z1 - z0) * k / n) + 0.12, z0 + (z1 - z0) * k / n) for k in range(n + 1)]
        for k, pt in enumerate(pts):
            rod(root, "post", pt, (pt[0], pt[1] + 0.95, pt[2]), 0.02, 0.018, railing_m, seg=6)
            if k:
                q = pts[k - 1]
                for dy in (0.95, 0.45):
                    rod(root, "rail", (q[0], q[1] + dy, q[2]), (pt[0], pt[1] + dy, pt[2]), 0.018, 0.018, railing_m, seg=6)


# ── The ground, the quay, the canal, the far bank ─────────────────────────────────────
def outdoor(spec):
    """Everything an "outdoor" RoomSpec stands in: its ground slabs, the quay wall and the canal,
    the far quay and the houses on it, the fronts on its own side, the bridge (built whichever room
    is being rendered: it's the world outside every window)."""
    o = spec["outdoor"]
    rng = random.Random(spec["id"])
    for g in o.get("ground", []):
        (gx0, gz0), (gx1, gz1) = g["min"], g["max"]
        y = g.get("y", 0.0)
        builders.box_aabb(g.get("name", "ground"), (gx0, y - 0.4, gz0), (gx1, y, gz1), M(g.get("material", STONE)))
    c = o.get("canal")
    if c:
        zq, width, water = c["z"], c["width"], c.get("water", -1.6)
        xa, xb = c.get("x", [-60.0, 100.0])
        quay = M({"ph": "brick_wall_003", "tint": [0.22, 0.2, 0.19]})
        builders.box_aabb("canal", (xa, water - 0.02, zq), (xb, water, zq + width), M("water"))
        builders.box_aabb("canal_bed", (xa, water - 3.0, zq), (xb, water - 2.9, zq + width), M({"color": [0.01, 0.012, 0.01], "rough": 1.0}))
        for k, (za, zb) in enumerate(((zq - 0.3, zq), (zq + width, zq + width + 0.3))):
            gaps = [gp for gp in c.get("gaps", []) if k == 0]
            xs = [xa] + [v for gp in sorted(gaps) for v in gp] + [xb]
            for u0, u1 in zip(xs[::2], xs[1::2]):
                builders.box_aabb("quay_wall", (u0, water - 3.0, za), (u1, 0.0, zb), quay)
        builders.box_aabb("far_quay", (xa, -0.4, zq + width + 0.3), (xb, 0.0, zq + width + c.get("far_quay", 6.0)), M(STONE))
        if c.get("far_houses", True):
            facade_row(xa + 20, xb - 20, zq + width + c.get("far_quay", 6.0), "north", rng, c)
    for f in o.get("facades", []):
        facade(f, random.Random(f.get("seed", 1)))
    for b in o.get("bridges", []):
        hump_bridge(spec, b)


PROPS = {"bollard": bollard, "bike": bike, "elm": elm, "railing": railing, "rowboat": rowboat, "houseboat": houseboat}
kit.PROPS.update(PROPS)
