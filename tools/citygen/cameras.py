# damned_waters/tools/citygen/cameras.py
# Purpose: the camera pass. Plans the fixed camera shots of the wide rooms (the streets, the squares,
# the big halls) the way the PlayStation survival-horror games framed their cities: many shots, each
# holding a small stretch of ground, so the survivor, the Drowned and what lies about are always big
# enough to read. Rules, not taste: every spot he can stand on is in some shot's zone, and from that
# shot he stands at least STANDARD["p10"] of the picture's height (a 1.75 m man; the old wide shots
# held him at 5 to 10 percent); the cameras look the way he travels through the room (so a cut keeps
# "forward" forward on the stick), from alternate sides, from a little above, never from inside a
# tree, a lamp or an awning, and with a clear view of the ground they hold.
# Idempotent: it replaces a room's "shots" (doors' peeks are the doors' own). Run by build_city.py;
# `python3 tools/citygen/cameras.py report` prints how big he stands in every shot of every room.
#
# ELI5: a camera crew blocking a long walk-and-talk. They don't film the street from one rooftop; they
# set up a camera every ten metres, each one looking the way the actor walks, and cut as he passes.
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOMS_DIR = Path(os.environ["DW_ROOMS"]) if os.environ.get("DW_ROOMS") else HERE.parents[1] / "game" / "data" / "rooms"

ASPECT = 16 / 9
FIGURE = 1.75          # m: the man the shots are framed for
FEET, HEAD = 0.05, 1.82   # m: the bottom and top of what must be in the picture where he stands
PLAYER_R = 0.3         # m: the floor he can stand on keeps this far from anything solid
CELL = 0.25            # m: the floor grid (fine enough to find an aisle he can just squeeze along)

# How big he stands, as a share of the picture's height, over the floor a shot holds.
STANDARD = {"p10": 0.13, "p05": 0.095, "median": 0.27, "floor": 0.17, "max": 0.85}   # floor: no shot's typical size below it
LENS = (40.0, 60.0)    # degrees, vertical: the game's lenses (a long lens from far off flattens the street into a CCTV feed)

# Each planned room: the way he travels through it (x, z on its floor plan: -z is north), and
# whether it's under the sky (bigger zones, higher cameras) or a hall.
ROOMS = {
    "herengracht": {"travel": (1, 0)},
    "thorbeckeplein": {"travel": (0, -1)},
    "rembrandtplein": {"travel": (-0.55, -0.84)},
    "reguliersbreestraat": {"travel": (-1, 0)},
    "muntplein": {"travel": (-0.35, -0.94)},
    "bloemenmarkt": {"travel": (-1, 0)},
    "kalversteeg": {"travel": (-1, 0)},
    "rokin_zuid": {"travel": (0, -1)},
    "rokin_noord": {"travel": (0, -1)},
    "dam": {"travel": (0.3, -0.95)},
    "kalverstraat": {"travel": (0, -1)},
    "kalverstraat_noord": {"travel": (0.35, -0.94)},
    "damrak_zuid": {"travel": (0, -1)},
    "damrak_noord": {"travel": (0, -1)},
    "rondvaartboot": {"travel": (0, -1), "hall": True,   # inside the tour boat: the boat is the set, the cameras under its glass roof
                      "ignore": ["canal_boat"], "on_floor": True, "kind": {"heights": (1.5, 1.75), "lens": (40.0, 70.0)}},
    "stationsplein": {"travel": (0, -1)},
    "station_noord": {"travel": (0, -1)},
    "nieuwe_kerk": {"travel": (0, -1), "hall": True},
    "beurs_zaal": {"travel": (0, -1), "hall": True},
    "centraal_hal": {"travel": (0, -1), "hall": True},
    "metro_centraal": {"travel": (0, -1), "hall": True},
    "metro_rokin": {"travel": (1, 0), "hall": True},
    "warenhuis": {"travel": (0.5, -0.87), "hall": True},
    "bioscoop": {"travel": (0, 1), "hall": True},
    "hotel_lobby": {"travel": (1, 0), "hall": True},
    "hotel_bar": {"travel": (-1, 0), "hall": True},
    "apotheek": {"travel": (0, -1), "hall": True},
}

OUT = {"zone_area": 120.0, "zone_side": 11.0, "heights": (2.4, 3.1, 4.0, 5.2), "reach": 14.0, "step": 1.0, "edge": 2.2,
       "lens": (40.0, 60.0), "clear": 1.2}
HALL = {"zone_area": 80.0, "zone_side": 9.0, "heights": (2.1, 2.7, 3.4, 4.4), "reach": 10.0, "step": 0.75, "edge": 0.45,
        "lens": (40.0, 66.0), "clear": 0.6}   # (indoors is close quarters: a wider lens, nearer the furniture)
OVERLAP = 0.75         # m: neighbouring zones overlap this much, so walking the line between them never flickers
PASSAGE_REACH = 3.5    # m: how far out through a passage, into the next street, a camera may stand
TREES = {"plane_tree", "elm"}
TREE_CLEAR = 4.5       # m: from a tree's trunk, a camera above its first limbs is among the branches
TALL = 1.2             # m: a prop this tall hides him (lower ones he's seen over)
CLEAR = 1.2            # m: a camera keeps this far from anything standing (more from a canopy, a light)
CANOPIES = {"fair_stall", "aid_post", "kiosk", "tram_stop", "market_stall", "flower_stall", "tent", "schiettent", "carousel", "terrace"}
NOT_THINGS = {"leaflets", "palace", "gothic_front", "beurs", "station", "munttoren", "runner", "rug", "puddle",
              "collider"}   # (no footprint on this floor, or nothing to see)
LIGHT_CLEAR = 3.0      # m: from a light (a lamp in the lens blows the picture out)
LAMP_HEAD = 3.27       # m: a street lamp's lantern (tools/blender/street.py)
LAMP_CLEAR = 4.0       # m: from a lantern, in 3D
GLARE = {"vehicle", "bus", "tram", "light_tower", "work_light"}   # headlights, floodlights: keep GLARE_CLEAR off them
GLARE_CLEAR = 3.0
# Spots a render showed to be bad (a dark wall filling half the picture, poles across it): (x, z, radius).
AVOID = {
    "dam": [(12.0, 11.4, 4.0), (19.0, 11.3, 4.0)],               # the Nieuwe Kerk's unlit flank across half the frame
    "stationsplein": [(27.6, 58.6, 3.5), (40.7, 66.2, 3.5)],      # tram poles and the square's darkest corner
    "rembrandtplein": [(30.4, 53.4, 3.5)],                       # out through the passage, over Thorbeckeplein's kiosk
    "metro_centraal": [(12.25, 11.87, 3.5)],                     # looking into the platform's unlit end: him a shadow in it
}


# ── The room as the planner sees it ───────────────────────────────────────────────────────────────

def _boxes(spec):
    """Solid props as (cx, cz, hx, hz, yaw radians, y0, y1, type): the engine's colliders, with heights."""
    out = []
    for p in spec.get("props", []):
        if not p.get("collide", True) or "size" not in p:
            continue
        x, y, z = p["pos"]
        w, h, d = p["size"]
        out.append((x, z, w / 2, d / 2, math.radians(p.get("yaw", 0.0)), y, y + h, p["type"]))
    return out


def _in_box(px, pz, b, grow=0.0):
    """Which points (arrays) lie inside box b grown by `grow` (the engine's resolve_circle_obb frame)."""
    cx, cz, hx, hz, a = b[:5]
    c, s = math.cos(a), math.sin(a)
    dx, dz = px - cx, pz - cz
    lx, lz = dx * c - dz * s, dx * s + dz * c
    return (np.abs(lx) <= hx + grow) & (np.abs(lz) <= hz + grow)


def open_floor(spec):
    """Every cell of the floor nothing solid stands on (reachable or not): cell centres (xs, zs) and a mask."""
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    xs = np.arange(x0 + CELL / 2, x1, CELL)
    zs = np.arange(z0 + CELL / 2, z1, CELL)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    ok = (X > x0 + PLAYER_R) & (X < x1 - PLAYER_R) & (Z > z0 + PLAYER_R) & (Z < z1 - PLAYER_R)
    for b in _boxes(spec):
        ok &= ~_in_box(X, Z, b, PLAYER_R)
    return xs, zs, ok


_FLOOR = {}


def floor_grid(spec, seeds=None):
    """The floor he can stand on: cell centres (xs, zs) and a mask, flood-filled from where he comes in
    (the room's spawns, or the given (x, y, z) points). Remembered for the same room and seeds."""
    key = (json.dumps(spec.get("bounds")), json.dumps(spec.get("props")), json.dumps(spec.get("spawns")), json.dumps(seeds))
    if key not in _FLOOR:
        _FLOOR.clear()   # (one room at a time)
        _FLOOR[key] = _floor_grid(spec, seeds)
    return _FLOOR[key]


def _floor_grid(spec, seeds=None):
    xs, zs, ok = open_floor(spec)
    (x0, z0) = spec["bounds"]["min"]
    seeds = seeds if seeds is not None else [s["pos"] for s in spec.get("spawns", {}).values()]
    seen = np.zeros_like(ok)
    stack = []
    for sx, _, sz in seeds:
        i, k = int((sx - x0) / CELL), int((sz - z0) / CELL)
        i, k = min(max(i, 0), len(xs) - 1), min(max(k, 0), len(zs) - 1)
        best = None   # (a spawn right against something: the nearest free cell)
        for di in range(-6, 7):
            for dk in range(-6, 7):
                a, c = i + di, k + dk
                if 0 <= a < len(xs) and 0 <= c < len(zs) and ok[a, c] and (best is None or di * di + dk * dk < best[0]):
                    best = (di * di + dk * dk, a, c)
        if best:
            stack.append(best[1:])
    while stack:
        i, k = stack.pop()
        if seen[i, k]:
            continue
        seen[i, k] = True
        for a, c in ((i + 1, k), (i - 1, k), (i, k + 1), (i, k - 1)):
            if 0 <= a < len(xs) and 0 <= c < len(zs) and ok[a, c] and not seen[a, c]:
                stack.append((a, c))
    return xs, zs, seen if seen.any() else ok


def lane_zones(spec, kind, lanes):
    """A cordoned room's zones: each lane (barricades.LANES) cut along its length into pieces no longer
    than kind's side, each shrunk to the floor it holds and grown by OVERLAP. A lane is a corridor, and
    a corridor is filmed along its length."""
    xs, zs, mask = floor_grid(spec)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    side = kind["zone_side"]
    out = []
    for x0, z0, x1, z1 in lanes:
        nx, nz = max(1, math.ceil((x1 - x0) / side - 0.15)), max(1, math.ceil((z1 - z0) / side - 0.15))
        for i in range(nx):
            for k in range(nz):
                a, b = x0 + (x1 - x0) * i / nx, z0 + (z1 - z0) * k / nz
                c, d = x0 + (x1 - x0) * (i + 1) / nx, z0 + (z1 - z0) * (k + 1) / nz
                m = mask & (X > a) & (X < c) & (Z > b) & (Z < d)
                if m.sum() * CELL * CELL < 6.0:
                    continue
                out.append((X[m].min() - CELL / 2, Z[m].min() - CELL / 2, X[m].max() + CELL / 2, Z[m].max() + CELL / 2))
    (bx0, bz0), (bx1, bz1) = spec["bounds"]["min"], spec["bounds"]["max"]
    out = [(max(bx0, a - OVERLAP), max(bz0, b - OVERLAP), min(bx1, c + OVERLAP), min(bz1, d + OVERLAP)) for a, b, c, d in out]
    keep = []   # (a piece whose floor all lies in a bigger one's is filmed by that one)
    for z in sorted(out, key=lambda z: -(z[2] - z[0]) * (z[3] - z[1])):
        if not any(o[0] <= z[0] and o[1] <= z[1] and o[2] >= z[2] and o[3] >= z[3] for o in keep):
            keep.append(z)
    return keep


def zones(spec, kind):
    """Split the floor into zones no bigger than kind's area and side: halve the longer side, at the
    middle of the floor on it, until every piece is small enough; then each piece shrinks to the floor
    it holds and grows by OVERLAP. Returns [(x0, z0, x1, z1)] on the room's floor plan. (A zone no
    camera can frame whole is halved again by plan_room.)"""
    import barricades   # (here: it imports this module)
    if spec["id"] in barricades.LANES:
        return lane_zones(spec, kind, barricades.LANES[spec["id"]])
    xs, zs, mask = floor_grid(spec)
    out = []

    def split(i0, i1, k0, k1):
        m = mask[i0:i1, k0:k1]
        if not m.any():
            return
        ii, kk = np.nonzero(m)
        i0, i1, k0, k1 = i0 + ii.min(), i0 + ii.max() + 1, k0 + kk.min(), k0 + kk.max() + 1   # shrink to the floor
        w, d = (i1 - i0) * CELL, (k1 - k0) * CELL
        area = m.sum() * CELL * CELL
        if area <= kind["zone_area"] and max(w, d) <= kind["zone_side"] * 1.5:
            out.append((xs[i0] - CELL / 2, zs[k0] - CELL / 2, xs[i1 - 1] + CELL / 2, zs[k1 - 1] + CELL / 2))
            return
        if w >= d:   # cut across the longer side, where it halves the floor
            col = mask[i0:i1, k0:k1].sum(axis=1).cumsum()
            cut = i0 + max(1, min(i1 - i0 - 1, int(np.searchsorted(col, col[-1] / 2)) + 1))
            split(i0, cut, k0, k1)
            split(cut, i1, k0, k1)
        else:
            row = mask[i0:i1, k0:k1].sum(axis=0).cumsum()
            cut = k0 + max(1, min(k1 - k0 - 1, int(np.searchsorted(row, row[-1] / 2)) + 1))
            split(i0, i1, k0, cut)
            split(i0, i1, cut, k1)

    split(0, len(xs), 0, len(zs))
    (bx0, bz0), (bx1, bz1) = spec["bounds"]["min"], spec["bounds"]["max"]
    return [(max(bx0, a - OVERLAP), max(bz0, b - OVERLAP), min(bx1, c + OVERLAP), min(bz1, d + OVERLAP)) for a, b, c, d in out]


def _avoid(spec, kind):
    """Where a camera may not stand: (x, z, radius, below) circles and (box, grow) boxes. A circle
    with `below` set only matters for a camera higher than that (a tree's limbs, a lamp's head)."""
    circles = []
    o = spec.get("outdoor", {})
    for x, z in o.get("lamps", []):
        circles.append((x, z, 0.9, 0.0))
    for ln in o.get("tracks", []):   # the tram wire's poles: every 24 m, 4.2 m to the left of the line
        (x0, z0), (x1, z1) = ln["from"], ln["to"]
        L = math.hypot(x1 - x0, z1 - z0)
        if L < 1e-6:
            continue
        nx, nz = -(z1 - z0) / L, (x1 - x0) / L
        n = max(1, int(L / 24.0))
        for i in range(n + 1):
            t = i / n
            circles.append((x0 + (x1 - x0) * t + nx * 4.2, z0 + (z1 - z0) * t + nz * 4.2, 1.5, 0.0))
    for x, z, r in AVOID.get(spec["id"], []):
        circles.append((x, z, r, 0.0))
    for a, b, *_ in o.get("strings", []):   # strings of bulbs: keep off the wire
        for t in np.linspace(0, 1, 6):
            circles.append((a[0] + (b[0] - a[0]) * t, a[2] + (b[2] - a[2]) * t, 1.0, min(a[1], b[1]) - 1.2))
    boxes = []
    for b in _boxes(spec):
        if b[7] in TREES:
            circles.append((b[0], b[1], 1.0, 0.0))
            circles.append((b[0], b[1], TREE_CLEAR, 2.6))
        else:
            boxes.append(b)
    things = []   # (box, grow): everything standing, solid or not
    ignore = set(ROOMS.get(spec["id"], {}).get("ignore", ()))   # (a room inside a thing: the thing is its set)
    for p in spec.get("props", []):
        if "size" not in p or p["type"] in NOT_THINGS or p["type"] in TREES or p["type"] in ignore or p["size"][1] < 0.8:
            continue
        x, y, z = p["pos"]
        w, h, d = p["size"]
        grow = kind.get("clear", CLEAR) * (2.0 if p["type"] in CANOPIES else 1.0) + (0.5 if p["type"] in CANOPIES else 0.0)
        if p["type"] in GLARE:
            grow = max(grow, GLARE_CLEAR)
        things.append(((x, z, w / 2, d / 2, math.radians(p.get("yaw", 0.0)), y, y + h, p["type"]), grow))
    return circles, boxes, things


def _segment_hits(cam, pts, boxes, step=0.35):
    """For each target point, does the line from the camera to it pass through a tall box? cam (3,),
    pts (N, 3). Sampled along the line (fine enough for things a man's size)."""
    n = len(pts)
    hit = np.zeros(n, bool)
    if not boxes:
        return hit
    L = np.linalg.norm(pts - cam, axis=1)
    m = int(np.ceil(L.max() / step)) + 1
    t = np.linspace(0.04, 0.97, m)[None, :, None]
    P = cam[None, None, :] + (pts - cam)[:, None, :] * t   # (n, m, 3)
    for b in boxes:
        if b[6] < TALL:
            continue
        inside = _in_box(P[..., 0], P[..., 2], b) & (P[..., 1] >= b[5]) & (P[..., 1] <= b[6])
        hit |= inside.any(axis=1)
    return hit


# ── One shot ──────────────────────────────────────────────────────────────────────────────────────

def _frame(cams, feet, heads):
    """Aim each candidate camera so the zone's floor (feet to heads) sits in the middle of the picture,
    and find the vertical field of view that just holds it. cams (C, 3); feet, heads (N, 3).
    Returns forward (C, 3), tan of half the vertical fov (C,), and how tall he stands (C, N)."""
    np.seterr(invalid="ignore", divide="ignore")   # (a camera straight over a point has no "right": its cost comes out NaN, and it's dropped)
    pts = np.concatenate([feet, heads])[None, :, :]               # (1, 2N, 3)
    v = pts - cams[:, None, :]
    f = v.mean(axis=1)
    f /= np.linalg.norm(f, axis=1, keepdims=True)
    for _ in range(4):   # re-aim at the middle of what it sees, in the picture's own terms
        r = np.cross(f, [0.0, 1.0, 0.0])
        r /= np.linalg.norm(r, axis=1, keepdims=True)
        u = np.cross(r, f)
        depth = np.einsum("cnk,ck->cn", v, f)
        depth = np.maximum(depth, 1e-3)
        px = np.einsum("cnk,ck->cn", v, r) / depth
        py = np.einsum("cnk,ck->cn", v, u) / depth
        cx = (px.max(axis=1) + px.min(axis=1)) / 2
        cy = (py.max(axis=1) + py.min(axis=1)) / 2
        f = f + r * cx[:, None] + u * cy[:, None]
        f /= np.linalg.norm(f, axis=1, keepdims=True)
    for k in range(3):   # the floor at the foot of the picture: any room to spare goes above it, to what lies ahead
        r = np.cross(f, [0.0, 1.0, 0.0])
        r /= np.linalg.norm(r, axis=1, keepdims=True)
        u = np.cross(r, f)
        depth = np.einsum("cnk,ck->cn", v, f)
        behind = (depth < 0.3).any(axis=1)
        depth = np.maximum(depth, 1e-3)
        px = np.einsum("cnk,ck->cn", v, r) / depth
        py = np.einsum("cnk,ck->cn", v, u) / depth
        half_w = np.abs(px).max(axis=1) / 0.92          # (the picture's edges keep a margin)
        half_h = np.maximum(py.max(axis=1) / 0.9, -py.min(axis=1) / 0.94)
        tan_v = np.maximum(half_h, half_w / ASPECT)
        if k == 2:
            break
        spare = py.min(axis=1) + 0.94 * tan_v             # how far the floor's foot sits above the picture's foot
        lift = np.where(np.isfinite(spare), np.clip(spare, 0, None) * 0.9, 0)
        f = f + u * lift[:, None]
        f /= np.linalg.norm(f, axis=1, keepdims=True)
    tan_v[behind] = np.inf
    n = feet.shape[0]
    tall = (py[:, n:] - py[:, :n]) / (2 * tan_v[:, None])
    return f, tan_v, tall


def plan_shot(spec, zone, kind, travel, prefer_side=0):
    """The best camera for one zone. Returns (shot, stats) or (None, reason)."""
    xs, zs, mask = floor_grid(spec)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    x0, z0, x1, z1 = zone
    sel = mask & (X >= x0) & (X <= x1) & (Z >= z0) & (Z <= z1)
    # All of the floor's edge (what must be in the picture) and a fair sample of its middle.
    inner = sel.copy()
    inner[1:-1, 1:-1] = sel[1:-1, 1:-1] & sel[:-2, 1:-1] & sel[2:, 1:-1] & sel[1:-1, :-2] & sel[1:-1, 2:]
    inner[0, :] = inner[-1, :] = inner[:, 0] = inner[:, -1] = False
    edge = sel & ~inner
    ix, iz = X[inner], Z[inner]
    if len(ix) > 140:
        keep = np.linspace(0, len(ix) - 1, 140).astype(int)
        ix, iz = ix[keep], iz[keep]
    fx, fz = np.concatenate([X[edge], ix]), np.concatenate([Z[edge], iz])
    feet = np.stack([fx, np.full_like(fx, FEET), fz], axis=1)
    heads = np.stack([fx, np.full_like(fx, HEAD), fz], axis=1)
    cx, cz = fx.mean(), fz.mean()
    # Where he comes in (a spawn in this zone: a door, the stairs, the next street), the camera keeps
    # close to the room's way through: the rooms along his route look the same way, so the cameras
    # either side of a threshold agree and a cut there never turns the stick round (either way).
    entry = any(x0 <= sp["pos"][0] <= x1 and z0 <= sp["pos"][2] <= z1 for sp in spec.get("spawns", {}).values())
    tl = math.hypot(*travel)
    tx, tz = travel[0] / tl, travel[1] / tl

    # Candidate stands: a grid round the zone, inside the room, clear of what's in the way: off the
    # walls and shop fronts (their awnings and signs reach out), except where a wide passage runs on
    # into the next street.
    (bx0, bz0), (bx1, bz1) = spec["bounds"]["min"], spec["bounds"]["max"]
    e = min(kind["edge"], min(bx1 - bx0, bz1 - bz0) / 2 - 0.4)   # (an alley keeps its cameras down the middle)
    g = np.arange(-kind["reach"], kind["reach"] + 1e-6, kind["step"])
    GX, GZ = np.meshgrid(cx + g, cz + g, indexing="ij")
    GX, GZ = GX.ravel(), GZ.ravel()
    inside = (GX >= bx0 + 0.3) & (GX <= bx1 - 0.3) & (GZ >= bz0 + 0.3) & (GZ <= bz1 - 0.3)
    ok = inside.copy()
    beyond = np.zeros_like(ok)   # a little way out through a passage, in the next street, looking in at the gateway
    for side, (dist, along, base) in {"west": (GX - bx0, GZ, bz0), "east": (bx1 - GX, GZ, bz0),
                                      "north": (GZ - bz0, GX, bx0), "south": (bz1 - GZ, GX, bx0)}.items():
        open_run = np.zeros_like(ok)
        for o in spec.get("walls", {}).get(side, {}).get("openings", []):
            if o.get("kind") != "passage" or o.get("width", 0) < 3.0:
                continue
            m = min(e, o["width"] / 2 - 0.6)
            span = (along >= base + o["center"] - o["width"] / 2 + m) & (along <= base + o["center"] + o["width"] / 2 - m)
            open_run |= span
            beyond |= span & (dist <= -0.3) & (dist >= -PASSAGE_REACH)
        ok &= (dist >= e) | open_run
    ok = (ok & inside) | beyond
    ok &= np.hypot(GX - cx, GZ - cz) <= kind["reach"]
    if ROOMS.get(spec["id"], {}).get("on_floor"):   # (the seats are the set's own: stand only over the aisle he walks)
        fi = np.clip(((GX - xs[0]) / CELL).round().astype(int), 0, len(xs) - 1)
        fk = np.clip(((GZ - zs[0]) / CELL).round().astype(int), 0, len(zs) - 1)
        ok &= mask[fi, fk]
    circles, boxes, things = _avoid(spec, kind)
    cams = []
    ceiling = spec.get("height", 3.0)
    for h in kind["heights"]:
        if h > ceiling - 0.35:
            continue
        good = ok.copy()
        for b in boxes:
            if b[6] > h - 0.6:   # a camera may hang over low things, not in or under tall ones
                good &= ~_in_box(GX, GZ, b, 0.5)
        for x, z, rad, below in circles:
            if h > below:
                good &= np.hypot(GX - x, GZ - z) > rad
        for b, grow in things:
            if b[5] - 1.0 < h < b[6] + 2.0:   # (two metres over a thing's top, or well under a roof, a camera is clear of it)
                good &= ~_in_box(GX, GZ, b, grow)
        for lx, lz in spec.get("outdoor", {}).get("lamps", []):   # nor a street lamp's lantern
            good &= np.sqrt((GX - lx) ** 2 + (GZ - lz) ** 2 + (h - LAMP_HEAD) ** 2) > LAMP_CLEAR
        for L in spec.get("lights", []):   # a lamp in the lens blows the picture out
            if "pos" in L:
                lx, ly, lz = L["pos"]
                good &= np.sqrt((GX - lx) ** 2 + (GZ - lz) ** 2 + (h - ly) ** 2) > LIGHT_CLEAR
        cams.append(np.stack([GX[good], np.full(good.sum(), h), GZ[good]], axis=1))
    cams = np.concatenate(cams) if cams else np.zeros((0, 3))
    if len(cams) == 0:
        return None, "nowhere to stand a camera"

    f, tan_v, tall = _frame(cams, feet, heads)
    fov = np.degrees(2 * np.arctan(tan_v))
    p05, p10, med, mx = (np.quantile(tall, q, axis=1) for q in (0.05, 0.10, 0.5, 1.0))
    hf = f[:, [0, 2]] / np.linalg.norm(f[:, [0, 2]], axis=1, keepdims=True)
    off_travel = np.degrees(np.arccos(np.clip(hf[:, 0] * tx + hf[:, 1] * tz, -1, 1)))
    pitch = np.degrees(np.arcsin(np.clip(f[:, 1], -1, 1)))
    side = np.sign((cams[:, 0] - cx) * tz - (cams[:, 2] - cz) * tx)   # left or right of his way through
    S = STANDARD
    cost = (np.maximum(0, S["p10"] - p10) * 25 + np.maximum(0, S["median"] - med) * 20 + np.abs(med - 0.3) * 2
            + np.maximum(0, mx - S["max"]) * 6
            + np.maximum(0, off_travel - 30) / 30 * (3.0 if entry else 1.2) + (off_travel > 62) * 3.0   # (looking back at him: only where nothing else will do)
            + np.abs(pitch + 15) / 20
            + np.maximum(0, fov - 56) / 8 + np.maximum(0, 46 - fov) / 6
            + (side == -prefer_side) * (0.3 if prefer_side else 0))
    lens = kind.get("lens", LENS)
    bad = ((fov > lens[1]) | (fov < lens[0]) | (p05 < S["p05"]) | (med < S["floor"]) | (pitch > 2) | (pitch < -48)
           | ~np.isfinite(cost))
    cost[bad] = np.inf
    order = np.argsort(cost)[:60]
    best, best_cost, best_seen = None, np.inf, 0.0
    targets = np.stack([fx, np.full_like(fx, 1.45), fz], axis=1)   # his chest and head, seen from the camera
    boxes = boxes + [b for b, _ in things if b[6] >= TALL]          # (anything standing hides him, solid or not)
    for c in order:
        if not np.isfinite(cost[c]):
            break
        seen = 1.0 - _segment_hits(cams[c], targets, boxes).mean()
        total = cost[c] + (1 - seen) * 12 + (1e9 if seen < 0.82 else 0)
        if total < best_cost:
            best, best_cost, best_seen = c, total, seen
    if best is None or not np.isfinite(best_cost):
        return None, "no camera frames it within the standard"
    c = best
    look = cams[c] + f[c] * 6.0
    shot = {"pos": [round(float(v), 2) for v in cams[c]], "look_at": [round(float(v), 2) for v in look],
            "fov": round(float(fov[c]), 1), "zone": {"min": [round(zone[0], 2), round(zone[1], 2)], "max": [round(zone[2], 2), round(zone[3], 2)]},
            "priority": 1}
    stats = {"p05": float(p05[c]), "p10": float(p10[c]), "median": float(med[c]), "max": float(mx[c]), "seen": best_seen,
             "off_travel": float(off_travel[c]), "pitch": float(pitch[c]), "side": int(side[c]), "fov": float(fov[c])}
    return shot, stats


def _shot_id(i):
    letters = "abcdefghijklmnopqrstuvwxyz"
    return letters[i] if i < 26 else letters[i // 26 - 1] + letters[i % 26]


def plan_room(spec):
    """Every zone of the room and its shot, in the order he meets them going his way through."""
    cfg = ROOMS[spec["id"]]
    kind = dict(HALL if cfg.get("hall") else OUT, **cfg.get("kind", {}))
    travel = cfg["travel"]
    zs = zones(spec, kind)
    zs.sort(key=lambda z: -(((z[0] + z[2]) / 2) * travel[0] + ((z[1] + z[3]) / 2) * travel[1]))   # entry first
    shots, stats, side = [], [], 0
    while zs:
        z = zs.pop(0)
        shot, st = plan_shot(spec, z, kind, travel, 1 if len(shots) % 2 == 0 else -1)
        if shot is None:   # nothing frames it all: film its two halves
            if max(z[2] - z[0], z[3] - z[1]) < 3.0:
                raise RuntimeError(f"{spec['id']}: zone {z}: {st}")
            if z[2] - z[0] >= z[3] - z[1]:
                m = (z[0] + z[2]) / 2
                halves = [(z[0], z[1], m + OVERLAP, z[3]), (m - OVERLAP, z[1], z[2], z[3])]
            else:
                m = (z[1] + z[3]) / 2
                halves = [(z[0], z[1], z[2], m + OVERLAP), (z[0], m - OVERLAP, z[2], z[3])]
            halves.sort(key=lambda h: -(((h[0] + h[2]) / 2) * travel[0] + ((h[1] + h[3]) / 2) * travel[1]))
            zs = halves + zs
            continue
        shot["id"] = _shot_id(len(shots))
        shots.append(shot)
        stats.append(st)
    return shots, stats


def apply(spec):
    """Re-plan a room's shots if it's one of ROOMS (idempotent: the plan depends only on the room)."""
    if spec["id"] not in ROOMS:
        return spec
    spec["shots"], _ = plan_room(spec)
    return spec


def report(rooms=None):
    for rid in rooms or ROOMS:
        spec = json.loads((ROOMS_DIR / f"{rid}.json").read_text())
        shots, stats = plan_room(spec)
        print(f"{rid}: {len(shots)} shots")
        for s, st in zip(shots, stats):
            print(f"  {s['id']:>3} fov {st['fov']:4.1f} pitch {st['pitch']:5.1f} off {st['off_travel']:4.0f}  he stands "
                  f"p05 {st['p05']:.2f} p10 {st['p10']:.2f} median {st['median']:.2f} max {st['max']:.2f}  seen {st['seen']:.2f}  cam {s['pos']}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["report"]:
        report(sys.argv[2:] or None)
