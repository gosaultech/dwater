# damned_waters/tools/citygen/barricades.py
# Purpose: the evacuation's cordons. The city's big squares and boulevards were too open to film: a
# camera that holds 90 x 70 m of the Dam holds the survivor as a speck. So, as the PlayStation-era
# survival horrors walled their streets with wrecks and barricades, the police and the army left
# lanes of crowd barriers (dranghekken, police tape tied along them) through each wide room: the way
# he can walk is a lane ten or so metres wide, past what matters (every door, spawn, item, note and
# Drowned is in one), and the rest of the square is seen through the bars but not walked.
# Each room's LANES are rectangles on its floor plan (x0, z0, x1, z1); wherever a lane's edge crosses
# open floor, a line of barriers stands on it. MOVES puts the Drowned and the things to find that
# stood outside the lanes inside them. Idempotent: what it adds is marked "barricade" and replaced on
# every run. Run by build_city.py before the camera pass (cameras.py), which films the lanes.
#
# ELI5: the stewards' fences at a festival. The field is still there and you can see across it, but
# you walk where the fences let you, and so the cameras know where to point.
import math

import numpy as np

import cameras

LANES = {
    "rokin_zuid": [(6, 74, 22, 80), (15.5, 40, 26, 74), (0, 30, 26, 40), (0, 0, 12, 30), (18, 22, 26, 30)],
    "rokin_noord": [(0, 50, 12, 80), (0, 38, 14, 50), (14, 36, 26, 50), (13, 12, 26, 36), (6, 0, 20, 12)],
    "damrak_zuid": [(0, 56, 12, 70), (0, 47, 20, 56), (0, 0, 11, 47)],
    "damrak_noord": [(0, 50, 11, 90), (0, 42, 20, 50), (0, 34, 11, 42), (0, 26, 20, 34), (2, 0, 16, 26)],
    "thorbeckeplein": [(0, 0, 8.5, 64), (8.5, 36, 16, 44), (8.5, 20, 16, 28), (0, 0, 24, 8)],
    "rembrandtplein": [(20, 39, 52, 50), (27.5, 13, 32.5, 39), (8, 23.5, 28, 28.5), (0, 0, 8, 40), (8, 8.5, 40, 13)],
    "muntplein": [(9, 12, 44, 24), (24, 0, 36, 13), (0, 21, 14, 36), (0, 0, 12, 13)],
    "stationsplein": [(29, 15, 41, 64), (20, 49, 29, 57), (41, 22, 63, 33), (13, 15, 29, 22), (13, 10, 22, 15), (22, 0, 48, 15)],
    "dam": [(46, 44, 58, 70), (46, 28, 67, 44), (38, 0, 52, 28), (12, 0, 38, 9), (52, 2, 62, 20), (62, 40, 79, 47),
            (0, 60, 46, 70), (0, 50, 8, 70)],
}

# Into the lanes: {"enemies": {id: [x, z]}, "interactables": {id: [x, z]}, "spawns": {name: [x, z]}} (heights kept).
MOVES = {
    "rokin_zuid": {"enemies": {"bij_de_tram": [18.5, 56.0]}},
    "rokin_noord": {"enemies": {"bij_de_ambulance": [15.0, 24.0]}, "spawns": {"from_rokin_zuid": [6.0, 78.5]}},
    "damrak_zuid": {"enemies": {"bij_de_hekken": [8.5, 60.0]}},
    "thorbeckeplein": {"enemies": {"in_de_deur": [1.2, 33.0]}},
    "rembrandtplein": {"enemies": {"op_het_plein": [24.0, 26.0], "bij_de_tram": [37.0, 11.0], "voor_de_club": [5.0, 8.0]}},
    "stationsplein": {"enemies": {"bij_de_tram": [21.0, 18.0], "bij_de_poort": [35.0, 9.0]}},
    "dam": {"enemies": {"bij_het_rad": [28.0, 6.0], "in_de_rij": [66.0, 43.0], "bij_de_bus": [76.0, 45.5], "bij_de_draaimolen": [48.0, 42.0]},
            "interactables": {"palace": [1.2, 56.0], "wheel": [24.0, 8.4], "carousel": [46.6, 50.0], "buses": [78.5, 41.0],
                              "damrak": [61.0, 3.0], "shells_truck": [61.0, 10.0], "ammo_bus": [78.6, 44.5]}},
}

HEIGHT, DEPTH = 1.1, 0.6   # m: a dranghek, and its feet
REACH = 0.35               # m: each line runs on this far at both ends, into whatever it meets
LONGEST = 11.5             # m: one prop's line at most (five barriers)


def in_lanes(rects, X, Z):
    m = np.zeros(X.shape, bool)
    for x0, z0, x1, z1 in rects:
        m |= (X > x0) & (X < x1) & (Z > z0) & (Z < z1)
    return m


def cordon_lines(spec, rects):
    """The barrier lines: ((ax, az), (bx, bz)) wherever open floor in a lane meets open floor outside."""
    xs, zs, ok = cameras.open_floor(spec)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    lane = in_lanes(rects, X, Z)
    a, b = ok & lane, ok & ~lane
    h = cameras.CELL / 2
    lines = []
    # Between neighbours along x: a line along z at the cells' shared edge.
    edge = (a[:-1, :] & b[1:, :]) | (b[:-1, :] & a[1:, :])
    for i in range(edge.shape[0]):
        k = 0
        while k < edge.shape[1]:
            if not edge[i, k]:
                k += 1
                continue
            k0 = k
            while k < edge.shape[1] and edge[i, k]:
                k += 1
            x = xs[i] + h
            lines.append(((x, zs[k0] - h), (x, zs[k - 1] + h)))
    edge = (a[:, :-1] & b[:, 1:]) | (b[:, :-1] & a[:, 1:])
    for k in range(edge.shape[1]):
        i = 0
        while i < edge.shape[0]:
            if not edge[i, k]:
                i += 1
                continue
            i0 = i
            while i < edge.shape[0] and edge[i, k]:
                i += 1
            z = zs[k] + h
            lines.append(((xs[i0] - h, z), (xs[i - 1] + h, z)))
    return lines


def barriers(lines, seed0=700):
    """Crowd-barrier props along the lines (yaw 0 runs along x, 90 along z), long ones in pieces."""
    props = []
    for (ax, az), (bx, bz) in lines:
        along_x = abs(bz - az) < 1e-6
        lo, hi = (min(ax, bx), max(ax, bx)) if along_x else (min(az, bz), max(az, bz))
        lo, hi = lo - REACH, hi + REACH
        n = max(1, math.ceil((hi - lo) / LONGEST))
        for j in range(n):
            u0, u1 = lo + (hi - lo) * j / n, lo + (hi - lo) * (j + 1) / n
            mid = (u0 + u1) / 2
            pos = [round(mid, 3), 0.0, round(az, 3)] if along_x else [round(ax, 3), 0.0, round(mid, 3)]
            props.append({"type": "crowd_barrier", "pos": pos, "yaw": 0 if along_x else 90, "size": [round(u1 - u0, 3), HEIGHT, DEPTH],
                          "seed": seed0 + len(props), "tape": len(props) % 4 != 3, "barricade": True})
    return props


def apply(spec):
    """Cordon a room's lanes (idempotent)."""
    rid = spec["id"]
    if rid not in LANES:
        return spec
    spec["props"] = [p for p in spec.get("props", []) if not p.get("barricade")]
    for kind, moves in MOVES.get(rid, {}).items():
        things = spec.get(kind, {})
        for key, item in (things.items() if isinstance(things, dict) else ((t["id"], t) for t in things)):
            if key in moves:
                x, z = moves[key]
                item.setdefault("pos0", list(item["pos"]))   # (where it stood before the cordon: the story's rules go by that)
                item["pos"] = [x, item["pos"][1], z]
    spec["props"] += barriers(cordon_lines(spec, LANES[rid]))
    return spec
