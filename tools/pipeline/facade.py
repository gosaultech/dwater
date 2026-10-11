# damned_waters/tools/pipeline/facade.py
# Purpose: the arithmetic of a canal-house front, kept out of Blender so it can be unit-tested
# (tools/pipeline/tests/test_facade.py): the outline of each kind of gable, the grid of windows and
# the front door, and a wall cut into solid rectangles around its holes. tools/blender/street.py
# turns these into bricks, sashes and glass.
#
# ELI5: the architect's elevation drawing. Before anyone lays a brick, the drawing says where every
# window goes and what shape the top of the house has; the builder (Blender) just follows it.
from __future__ import annotations

import math

GABLES = ("cornice", "neck", "bell", "step", "spout")


def gable_outline(kind: str, w: float, hg: float) -> list[tuple[float, float]]:
    """The gable above the cornice line as a polygon (u across, centred; v up from the line),
    counter-clockwise from the base's left corner (-w/2, 0) over the top to its right corner.
    Symmetric, never wider than the house, and star-shaped about (0, 0.2) (see is_star_shaped)."""
    h = w / 2
    if kind == "cornice":   # a flat top behind a deep cornice: just a low parapet
        half = [(-h, 0.0), (-h, 0.55)]
    elif kind == "spout":   # a plain triangle with a small square spout at the top
        half = [(-h, 0.0), (-0.22 * h, hg * 0.86), (-0.22 * h, hg)]
    elif kind == "step":    # stepped: equal steps up each side to a square top
        n = 4
        tw = 0.28 * h
        half = [(-h, 0.0)]
        for k in range(n):
            u = -h + (h - tw) * k / n
            v = hg * (k + 1) / (n + 1)
            half += [(u, v), (u + (h - tw) / n, v)]
        half += [(-tw, hg)]
    elif kind == "neck":    # shoulders, then a tall narrow neck with a pediment
        nw = 0.42 * h
        sh = hg * 0.32
        half = [(-h, 0.0), (-h, sh * 0.35)]
        for k in range(1, 7):   # the claw piece: a quarter curve from the shoulder into the neck
            a = k / 6 * math.pi / 2
            half.append((-h + (h - nw) * math.sin(a), sh * 0.35 + (sh * 0.65) * (1 - math.cos(a))))
        half += [(-nw, hg * 0.86), (-nw * 0.35, hg * 0.96)]
    elif kind == "bell":    # an S-curve from the full width in to a narrow rounded cap
        nw = 0.36 * h
        half = []
        for k in range(10):
            t = k / 9
            s = t * t * (3 - 2 * t)   # smoothstep: out at the base, in at the top
            half.append((-h + (h - nw) * s, hg * 0.85 * t))
        half += [(-nw * 0.8, hg * 0.93), (-nw * 0.4, hg * 0.99)]
    else:
        raise ValueError(f"unknown gable '{kind}' (one of {', '.join(GABLES)})")
    top = [] if kind == "cornice" else [(0.0, hg)]
    right = [(-u, v) for u, v in reversed(half)]
    return half + top + right


def is_star_shaped(poly: list[tuple[float, float]], c: tuple[float, float]) -> bool:
    """Every edge of the polygon is seen from c on its inside: a fan of triangles from c fills it."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sign = 1 if area > 0 else -1
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        if (ax - bx) ** 2 + (ay - by) ** 2 < 1e-12:
            continue
        cross = (bx - ax) * (c[1] - ay) - (by - ay) * (c[0] - ax)
        if cross * sign < -1e-9:
            return False
    return True


def window_grid(w: float, storeys: list[float], bays: int, win_w: float = 1.05, door_bay: int | None = None,
                door_w: float = 1.1, door_h: float = 2.5) -> dict:
    """Where the windows and the door go on a front `w` wide with these storey heights (bottom up):
    `bays` columns, evenly spaced; each window tall in its storey (sill 0.75 m on the ground floor,
    0.55 m above it; taller below, shorter at the top, as canal houses are). The door takes the
    ground-floor window's place in `door_bay`. Rectangles are (u0, u1, v0, v1), u from the front's
    left edge, v up from the street."""
    pitch = w / bays
    wins, door = [], None
    base = 0.0
    for s, sh in enumerate(storeys):
        sill = 0.75 if s == 0 else 0.55
        top_gap = 0.45 if s == 0 else 0.4
        for b in range(bays):
            c = pitch * (b + 0.5)
            if s == 0 and door_bay is not None and b == door_bay:
                door = (c - door_w / 2, c + door_w / 2, 0.0, min(door_h, sh - 0.3))
                continue
            wins.append((c - win_w / 2, c + win_w / 2, base + sill, base + sh - top_gap))
        base += sh
    return {"windows": wins, "door": door, "height": base}


def cut_rects(W: float, H: float, holes: list[tuple[float, float, float, float]]) -> list[tuple[float, float, float, float]]:
    """The wall [0, W] x [0, H] as solid rectangles (u0, u1, v0, v1) around the holes (which must
    not overlap): cut into vertical strips at every hole's sides, each strip broken around the holes
    that cross it. Like cutting a sheet of plywood around window frames with a straight saw."""
    cuts = sorted({0.0, W} | {min(max(v, 0.0), W) for h in holes for v in h[:2]})
    out = []
    for ua, ub in zip(cuts, cuts[1:]):
        if ub - ua < 1e-6:
            continue
        mid = (ua + ub) / 2
        gaps = sorted((max(h[2], 0.0), min(h[3], H)) for h in holes if h[0] <= mid <= h[1])
        v = 0.0
        for ga, gb in gaps + [(H, H)]:
            if ga - v > 1e-6:
                out.append((ua, ub, v, ga))
            v = max(v, gb)
    return out
