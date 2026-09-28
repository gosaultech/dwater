# damned_waters/tools/characters/garments.py
# Purpose: clothes as shells of the body. A garment is a patch of the body's own
# surface (chosen by a rule: "legs from the waist to the ankle"), pushed outward,
# smoothed so it drapes over the anatomy instead of clinging to it, loosened into
# its cut (straight jeans, a boxy jacket), creased where cloth creases, and given a
# hem so its edges have thickness. It inherits the body's joint weights, so it moves
# with the body. Think of it as tailoring by inflation: start from a skin-tight suit
# of the right patch of body, then let it out where the pattern says.
# Layers are measured from the skin, so outer garments always clear inner ones.
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

import dwc
from body import Body, quad_normals
from parts import rgba

Vec = np.ndarray


def adjacency(quads: np.ndarray, n: int) -> list[np.ndarray]:
    nb = [set() for _ in range(n)]
    for q in quads:
        for i in range(4):
            a, b = q[i], q[(i + 1) % 4]
            nb[a].add(b)
            nb[b].add(a)
    return [np.fromiter(s, dtype=np.int64) if s else np.zeros(0, np.int64) for s in nb]


def membrane(P: Vec, P0: Vec, N0: Vec, quads: np.ndarray, floor: np.ndarray, iters: int, k: float = 0.6) -> Vec:
    """Cloth under tension: repeatedly pull every point toward its neighbours' average (which
    flattens bumps and bridges hollows), then push anything closer to the skin than `floor` back
    out along the skin normal. The result spans the body like a drum skin: over the chest, not
    into the cleavage between the muscles."""
    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    e = np.unique(np.sort(e, axis=1), axis=0)
    i, j = np.concatenate([e[:, 0], e[:, 1]]), np.concatenate([e[:, 1], e[:, 0]])
    deg = np.bincount(i, minlength=len(P)).astype(float)[:, None]
    move = (deg > 0).astype(float)
    rim = [v for edge in boundary_loops(quads) for v in edge]
    move[rim] = 0.0                                   # hems and openings keep their place (their snaps come later)
    P = P.copy()
    for _ in range(iters):
        avg = np.zeros_like(P)
        np.add.at(avg, i, P[j])
        P += (avg / np.maximum(deg, 1) - P) * k * move
        P = keep_off_skin(P, P0, N0, quads, floor)
    return P


def keep_off_skin(P: Vec, P0: Vec, N0: Vec, quads: np.ndarray, floor: np.ndarray) -> Vec:
    """Push cloth that came closer to the skin than `floor` back out. Measured along the cloth's own
    normal where the cloth faces the same way as the skin, so cloth bridging a hollow (whose skin
    faces sideways into it) isn't prised apart along those sideways normals."""
    Ng = quad_normals(P, quads)
    n = np.where((np.einsum("ij,ij->i", Ng, N0) > 0.3)[:, None], Ng, N0)
    d = np.einsum("ij,ij->i", P - P0, n)
    under = d < floor
    P = P.copy()
    P[under] += n[under] * (floor[under] - d[under])[:, None]
    return P


def taubin(P: Vec, nbrs: list[np.ndarray], iters: int, lam: float = 0.5, mu: float = -0.53, fixed: np.ndarray | None = None) -> Vec:
    """Smoothing that doesn't shrink (Taubin): a smooth step, then a slight un-smooth step."""
    P = P.copy()
    for _ in range(iters):
        for k in (lam, mu):
            avg = np.array([P[n].mean(axis=0) if len(n) else P[i] for i, n in enumerate(nbrs)])
            step = (avg - P) * k
            if fixed is not None:
                step[fixed] = 0
            P += step
    return P


def boundary_loops(quads: np.ndarray) -> list[tuple[int, int]]:
    """Edges used by exactly one quad, oriented as in that quad (so the hem faces outward)."""
    count, orient = {}, {}
    for q in quads:
        for i in range(4):
            a, b = int(q[i]), int(q[(i + 1) % 4])
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
            orient[key] = (a, b)
    return [orient[k] for k, c in count.items() if c == 1]


@dataclass
class Garment:
    name: str
    mat: int
    color: tuple
    select: Callable[[Body], np.ndarray]          # -> bool per body vertex; a quad is taken if all 4 corners are
    offset: float | Callable[[Body, np.ndarray], np.ndarray]   # metres from the skin, or (body, ids) -> per vertex
    smooth: int = 3                               # Taubin passes: more = drapes over more detail
    loosen: Callable[[Body, np.ndarray, Vec], Vec] | None = None   # (body, ids, P) -> P
    fold: Callable[[Body, np.ndarray, Vec, Vec], Vec] | None = None  # (body, ids, P, N) -> offset along N
    tint: Callable[[Body, np.ndarray, Vec], Vec] | None = None       # (body, ids, P) -> (n,3) colours
    hem: float = 0.006                            # edge thickness
    hides_skin: bool = True                       # drop body faces fully under this garment
    snap: Callable[[Body, np.ndarray, Vec, np.ndarray], Vec] | None = None   # (body, ids, P, on_edge) -> P: clean edges
    mats: Callable[[Body, np.ndarray, Vec], np.ndarray] | None = None       # per-vertex material override
    smooth_base: int = 0                          # smooth the skin itself first (boots: no toes under the leather)
    tension: int = 0                              # membrane passes: > 0 stretches the cloth across hollows (see membrane)
    trim: Callable[[Body, np.ndarray, Vec], np.ndarray] | None = None   # (body, ids, P) -> keep where >= 0, cut exactly
    #   along 0: hems, cuffs, necklines and openings become smooth curves (select a little beyond them)


def fill_holes(b: Body, sel: np.ndarray, iters: int = 2) -> np.ndarray:
    """Close pinholes and notches in a vertex selection: a vertex whose neighbours are (nearly) all
    selected joins it. Without this, a stray vertex owned by another joint leaves a hole in the cloth."""
    q = b.body_quads
    e = np.concatenate([q[:, [0, 1]], q[:, [1, 2]], q[:, [2, 3]], q[:, [3, 0]]])
    i, j = np.concatenate([e[:, 0], e[:, 1]]), np.concatenate([e[:, 1], e[:, 0]])
    deg = np.bincount(i, minlength=len(b.V))
    sel = sel.copy()
    for _ in range(iters):
        cnt = np.bincount(i, weights=sel[j].astype(float), minlength=len(b.V))
        sel |= (deg > 0) & (cnt >= deg * 0.74)
    return sel


def _offsets(b: Body, g: Garment, ids: np.ndarray) -> np.ndarray:
    return np.asarray(g.offset(b, ids), float) if callable(g.offset) else np.full(len(ids), float(g.offset))


def clip(P: Vec, N: Vec, src: np.ndarray, tris: np.ndarray, s: np.ndarray):
    """Keep the part of a triangle mesh where the field s >= 0, cutting triangles exactly along s = 0.
    New vertices on the cut take the interpolated position and normal and the nearer end's body vertex
    (for its joint weights); a cut edge shared by two triangles gets one vertex. Returns (P, N, src, tris)."""
    P, N, src = list(P), list(N), list(src)
    out, cache = [], {}

    def cut(a, c):
        key = (min(a, c), max(a, c))
        if key not in cache:
            t = s[a] / (s[a] - s[c])
            n = N[a] + (N[c] - N[a]) * t
            cache[key] = len(P)
            P.append(P[a] + (P[c] - P[a]) * t)
            N.append(n / max(np.linalg.norm(n), 1e-9))
            src.append(src[a] if t < 0.5 else src[c])
        return cache[key]

    keep = s >= 0
    for tri in tris:
        k3 = keep[tri]
        if k3.all():
            out.append([int(tri[0]), int(tri[1]), int(tri[2])])
            continue
        if not k3.any():
            continue
        poly = []
        for k in range(3):
            a, c = int(tri[k]), int(tri[(k + 1) % 3])
            if keep[a]:
                poly.append(a)
            if keep[a] != keep[c]:
                poly.append(cut(a, c))
        out += [[poly[0], poly[k], poly[k + 1]] for k in range(1, len(poly) - 1)]
    out = np.array(out, np.int64).reshape(-1, 3)
    used, T = np.unique(out, return_inverse=True)
    return np.array(P)[used], np.array(N)[used], np.array(src)[used], T.reshape(out.shape)


def rim_edges(tris: np.ndarray) -> np.ndarray:
    """Open edges of a triangle mesh (used by one triangle), oriented as in their triangle."""
    e = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    _, first, counts = np.unique(np.sort(e, axis=1), axis=0, return_index=True, return_counts=True)
    return e[first[counts == 1]]


def hem_strip(P: Vec, N: Vec, src: np.ndarray, col: np.ndarray, tris: np.ndarray, depth: float):
    """Fold every open edge back toward the body by `depth`, so edges read as cloth, not paper."""
    rim = rim_edges(tris)
    if depth <= 0 or not len(rim):
        return P, N, src, col, tris
    rv = np.unique(rim)
    inner = np.full(len(P), -1, np.int64)
    inner[rv] = len(P) + np.arange(len(rv))
    a, c = rim[:, 0], rim[:, 1]
    strip = np.concatenate([np.stack([c, a, inner[a]], 1), np.stack([c, inner[a], inner[c]], 1)])
    return (np.vstack([P, P[rv] - N[rv] * depth]), np.vstack([N, -N[rv]]), np.concatenate([src, src[rv]]),
            np.vstack([col, col[rv]]), np.vstack([tris, strip]))


def _finish(b: Body, name: str, mat: int, P: Vec, N: Vec, src: np.ndarray, col: np.ndarray, tris: np.ndarray, hem: float,
            mats: Callable | None = None) -> dwc.Part:
    shell = (src.copy(), tris.copy(), P.copy(), N.copy())
    P, N, src, col, tris = hem_strip(P, N, src, col, tris, hem)
    m = mats(b, src, P).astype(np.uint8) if mats else np.full(len(P), mat, np.uint8)
    part = dwc.Part(name, P.astype(np.float32), N.astype(np.float32), col.astype(np.uint8), m,
                    b.region[src].astype(np.uint8), b.jid[src].astype(np.uint8), b.jw[src].astype(np.float32), tris.astype(np.int64))
    part.shell = shell   # the outer surface before the hem: other cloth can be laid on it (clip_overlay)
    return part


def clip_overlay(b: Body, base: dwc.Part, name: str, mat: int, color: tuple, inside: Callable[[Vec], np.ndarray],
                 lift: float, hem: float = 0.004) -> dwc.Part:
    """A piece cut from another garment's surface along a smooth boundary (webbing straps, a patch):
    inside(P) is positive inside the piece and crosses zero at its edge, so the edges are exact
    curves instead of the stairs of the body's mesh. The piece is lifted `lift` off its base."""
    src0, tris0, P0, N0 = base.shell
    P, N, src, T = clip(P0, N0, src0, tris0, inside(P0))
    return _finish(b, name, mat, P + N * lift, N, src, np.tile(rgba(color), (len(P), 1)), T, hem)


def build(b: Body, g: Garment) -> tuple[dwc.Part, np.ndarray]:
    """Returns the garment part and the body quads (mask) it hides."""
    sel_v = fill_holes(b, g.select(b))
    qmask = sel_v[b.body_quads].all(axis=1)
    quads = b.body_quads[qmask]
    ids, local = np.unique(quads, return_inverse=True)
    local = local.reshape(quads.shape)
    P0, N0 = b.V[ids], b.N[ids]
    if g.smooth_base:
        nb0 = adjacency(local, len(ids))
        P0 = taubin(P0, nb0, g.smooth_base, lam=0.6, mu=-0.62)
        N0 = quad_normals(P0, local)
    off = _offsets(b, g, ids)
    P = P0 + N0 * off[:, None]
    if g.tension:
        P = membrane(P, P0, N0, local, off * 0.92, g.tension)
    if g.loosen:
        P = g.loosen(b, ids, P)
    nbrs = adjacency(local, len(ids))
    P = taubin(P, nbrs, g.smooth)
    P = keep_off_skin(P, P0, N0, local, off * 0.7)   # never inside the skin: at least 70% of the intended offset
    if g.snap:
        on_edge = np.zeros(len(ids), bool)
        for a, bb in boundary_loops(local):
            on_edge[a] = on_edge[bb] = True
        P = g.snap(b, ids, P, on_edge)
    N = quad_normals(P, local)
    if g.fold:
        P = P + N * g.fold(b, ids, P, N)[:, None]
        N = quad_normals(P, local)
    tris = np.concatenate([local[:, [0, 1, 2]], local[:, [0, 2, 3]]])
    s = g.trim(b, ids, P) if g.trim else np.ones(len(ids))
    Pc, Nc, src, T = clip(P, N, ids, tris, s) if g.trim else (P, N, ids, tris)
    col = np.tile(rgba(g.color), (len(Pc), 1))
    if g.tint:
        col[:, :3] = np.clip(g.tint(b, src, Pc), 0, 255).astype(np.uint8)
    part = _finish(b, g.name, g.mat, Pc, Nc, src, col, T, g.hem, g.mats)
    hidden = np.zeros(len(b.body_quads), bool)
    if g.hides_skin:
        # Hide skin only well inside the finished garment: every corner selected, at least 1.2 cm
        # inside any trim line, and not on the open edge (plus a one-ring margin).
        inside = sel_v.copy()
        inside[ids[s < 0.012]] = False
        inside[src[np.unique(rim_edges(T))]] = False
        margin = inside.copy()
        q = b.body_quads[qmask]
        bad = ~inside[q].all(axis=1)
        margin[np.unique(q[bad])] = False
        hidden = margin[b.body_quads].all(axis=1) & qmask
    return part, hidden


# ── Shaping helpers ──────────────────────────────────────────────────────────────
def radial_min(b: Body, ids: np.ndarray, P: Vec, a: Vec, c: Vec, r_of_t: Callable[[np.ndarray], np.ndarray]) -> Vec:
    """Push points out from the segment a->c to at least r(t) (t = 0 at a, 1 at c): straight legs, boxy sleeves."""
    ax = c - a
    L2 = ax @ ax
    t = np.clip(((P - a) @ ax) / L2, 0, 1)
    foot = a + t[:, None] * ax
    off = P - foot
    r = np.linalg.norm(off, axis=1)
    want = r_of_t(t)
    grow = r < want
    P = P.copy()
    P[grow] = foot[grow] + off[grow] / np.maximum(r[grow], 1e-6)[:, None] * want[grow][:, None]
    return P


def hang_straight(P: Vec, ids_y: np.ndarray, below: float, centre_xz: Vec, bins: int = 48, taper: float = 0.03) -> Vec:
    """Cloth falls straight from the widest band above `below` (a boxy jacket, a sweater over a belly):
    in cylindrical coordinates round the body, no point below may sit inside that band's outline."""
    P = P.copy()
    d = P[:, [0, 2]] - centre_xz
    ang = np.arctan2(d[:, 0], d[:, 1])
    r = np.linalg.norm(d, axis=1)
    k = ((ang + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    band = (ids_y > below) & (ids_y < below + 0.06)
    prof = np.zeros(bins)
    for i in range(bins):
        m = band & (k == i)
        if m.any():
            prof[i] = r[m].max()
    for _ in range(3):   # fill empty bins from neighbours
        empty = prof == 0
        prof[empty] = np.maximum(np.roll(prof, 1), np.roll(prof, -1))[empty]
    drop = np.clip((below - ids_y) / 0.4, 0, 1)
    want = prof[k] * (1 - taper * drop)
    grow = (ids_y < below) & (r < want) & (r > 1e-6)
    P[grow, 0] = centre_xz[0] + d[grow, 0] / r[grow] * want[grow]
    P[grow, 2] = centre_xz[1] + d[grow, 1] / r[grow] * want[grow]
    return P


def convex_slices(P: Vec, ids_y: np.ndarray, centre_xz: Vec, bins: int = 72, step: float = 0.02) -> Vec:
    """Stiff cloth spans hollows in every horizontal slice (the small of the back, the cleft of the
    buttocks, between the shoulder blades): per height band, the outline round the body is pushed
    out to its convex hull, measured in polar bins round `centre_xz`."""
    P = P.copy()
    d = P[:, [0, 2]] - centre_xz
    ang = np.arctan2(d[:, 0], d[:, 1])
    r = np.linalg.norm(d, axis=1)
    k = ((ang + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    band = np.floor((ids_y - ids_y.min()) / step).astype(int)
    shrink = np.cos(np.pi / bins)
    for bi in np.unique(band):
        m = band == bi
        prof = np.zeros(bins)
        np.maximum.at(prof, k[m], r[m])
        filled = prof > 0
        if filled.sum() < bins // 2:
            continue
        for _ in range(bins):   # relax toward the hull: a bin is at least its neighbours' chord
            prof = np.where(filled, np.maximum(prof, 0.5 * (np.roll(prof, 1) + np.roll(prof, -1)) * shrink), prof)
        grow = m & (r < prof[k]) & (r > 1e-6)
        P[grow, 0] = centre_xz[0] + d[grow, 0] / r[grow] * prof[k[grow]]
        P[grow, 2] = centre_xz[1] + d[grow, 1] / r[grow] * prof[k[grow]]
    return P


def knit_rib(P: Vec, y0: float, y1: float, depth: float) -> np.ndarray:
    """Pull a band (cuffs, hem) in toward the body: ribbed knit hugs."""
    return np.where((P[:, 1] > y0) & (P[:, 1] < y1), -depth, 0.0)


# ── Reusable tailoring: offsets, legs, and clean edges ───────────────────────────
def per_arm(torso_off: float, arm_off: float) -> Callable[[Body, np.ndarray], np.ndarray]:
    """A garment offset that sits closer on the arms than on the body panels (no puffer sleeves)."""
    return lambda b, ids: torso_off + (arm_off - torso_off) * b.weight_of("sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r")[ids]


def straight_legs(joints: dict, r_top: float = 0.085, r_bottom: float = 0.067) -> Callable:
    """Loosen: trouser legs fall straight from the thigh to the ankle instead of hugging the calf."""
    def loosen(b, ids, P):
        out = P.copy()
        for s in ("l", "r"):
            side = (b.V[ids, 0] < 0) if s == "l" else (b.V[ids, 0] >= 0)
            sel = side & (b.V[ids, 1] < joints[f"hip_{s}"][1] - 0.04)
            out[sel] = radial_min(b, ids[sel], out[sel], joints[f"hip_{s}"], joints[f"ank_{s}"] + np.array([0, 0.05, 0]),
                                  lambda t: r_top + (r_bottom - r_top) * t)
        return out
    return loosen


def snap_hem(y: float, band: float = 0.035, where: Callable[[Body, np.ndarray], np.ndarray] | None = None) -> Callable:
    """Snap an edge that runs round the body (a hem, a cuff) onto a clean horizontal line."""
    def snap(b, ids, P, on_edge):
        out = P.copy()
        t = on_edge & (np.abs(b.V[ids, 1] - y) < band)
        if where is not None:
            t &= where(b, ids)
        out[t, 1] = y + (out[t, 1] - b.V[ids][t, 1]) * 0.3
        return out
    return snap


def snap_neck(y_at: float, y_back: float, y_front: float, neck_z: float, band: float = 0.03) -> Callable:
    """Snap the edge round the neck (at skin height y_at) onto a smooth line, higher at the back."""
    def snap(b, ids, P, on_edge):
        out = P.copy()
        t = on_edge & (np.abs(b.V[ids, 1] - y_at) < band)
        d = out[t][:, [0, 2]] - np.array([0.0, neck_z])
        c = d[:, 1] / np.maximum(np.linalg.norm(d, axis=1), 1e-6)       # +1 at the back, -1 at the front
        out[t, 1] = y_front + (y_back - y_front) * (0.5 + 0.5 * c)
        return out
    return snap


def chain(*snaps: Callable) -> Callable:
    """Apply several edge snaps in order."""
    def snap(b, ids, P, on_edge):
        for s in snaps:
            P = s(b, ids, P, on_edge)
        return P
    return snap


def shoe(b: Body, side: str, name: str, mat: int, color: tuple, sole_mat: int, sole_color: tuple, sole: float = 0.022,
         margin: float = 0.009, shaft_top: float = 0.15, toe_round: float = 1.0) -> dwc.Part:
    """A boot built like a cobbler's last: the foot's footprint (rounded, with a margin) becomes the
    sole; a blurred height map of the foot becomes the upper, so toes merge into one toe box; the
    shaft closes round the ankle. Rigidly skinned to the ankle (feet don't bend at the toes here)."""
    from body import J
    ank = J[f"ank_{side}"]
    foot = np.nonzero(np.isin(b.dominant, [ank]) & (b.V[:, 1] < 0.13) & np.isin(np.arange(len(b.V)), b.body_ids))[0]
    F = b.V[foot]
    c = np.array([F[:, 0].mean(), F[:, 2].mean()])
    # Outline: furthest footprint point per angle, smoothed round the loop.
    bins = 48
    d = F[:, [0, 2]] - c
    ang = np.arctan2(d[:, 0], -d[:, 1])                      # 0 = the toe (-Z)
    k = ((ang + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    r = np.zeros(bins)
    for i in range(bins):
        m = k == i
        r[i] = np.linalg.norm(d[m], axis=1).max() if m.any() else 0
    for _ in range(4):
        r = np.maximum(r, 0.5 * (np.roll(r, 1) + np.roll(r, -1)) * 0.98)
    r = np.convolve(np.r_[r[-3:], r, r[:3]], np.ones(7) / 7, mode="valid") + margin
    # Height map of the foot's top, blurred (merges the toes), plus the leather's thickness.
    res = 0.008
    x0, z0 = F[:, 0].min() - 0.03, F[:, 2].min() - 0.03
    nx, nz = int((F[:, 0].max() + 0.03 - x0) / res) + 1, int((F[:, 2].max() + 0.03 - z0) / res) + 1
    H = np.zeros((nx, nz))
    ix = ((F[:, 0] - x0) / res).astype(int)
    iz = ((F[:, 2] - z0) / res).astype(int)
    np.maximum.at(H, (ix, iz), F[:, 1])
    for _ in range(4):   # dilate then blur
        H = np.maximum(H, np.maximum(np.roll(H, 1, 0), np.roll(H, -1, 0)))
        H = np.maximum(H, np.maximum(np.roll(H, 1, 1), np.roll(H, -1, 1)))
    for _ in range(6):
        H = (H + np.roll(H, 1, 0) + np.roll(H, -1, 0) + np.roll(H, 1, 1) + np.roll(H, -1, 1)) / 5
    height = lambda x, z: np.clip(H[np.clip(((x - x0) / res).astype(int), 0, nx - 1), np.clip(((z - z0) / res).astype(int), 0, nz - 1)] + margin * 0.8,
                                  0.035, shaft_top)
    rings_top = 10
    th = (np.arange(bins) + 0.5) / bins * 2 * np.pi - np.pi
    dirs = np.stack([np.sin(th), -np.cos(th)], axis=1)
    rows = []
    # sole bottom (centre -> outline), sole edge, welt, then the upper from the outline in to the ankle opening
    rows.append(np.tile([c[0], -sole, c[1]], (bins, 1)))
    for u in (0.6, 1.0):
        xz = c + dirs * (r[:, None] * u)
        rows.append(np.column_stack([xz[:, 0], np.full(bins, -sole), xz[:, 1]]))
    xz = c + dirs * r[:, None]
    rows.append(np.column_stack([xz[:, 0], np.full(bins, 0.004), xz[:, 1]]))
    ank_p = b.joints[ank]
    open_r = 0.058
    for i in range(1, rings_top + 1):
        u = 1 - i / rings_top                               # 1 = outline, 0 = the ankle opening
        tgt = np.array([ank_p[0], ank_p[2] + 0.005])
        xz_i = tgt + (c + dirs * r[:, None] - tgt) * u + dirs * open_r * (1 - u)
        y = np.maximum(height(xz_i[:, 0], xz_i[:, 1]) * (u ** 0.35), 0.004) if i < rings_top else np.full(bins, shaft_top)
        y = np.where(i == rings_top, shaft_top, np.maximum(y, 0.004 + (shaft_top - 0.004) * (1 - u) ** 2.2))
        rows.append(np.column_stack([xz_i[:, 0], y, xz_i[:, 1]]))
    G = np.array(rows)                                        # (rows, bins, 3)
    R_ = len(G)
    P = G.reshape(-1, 3)
    tris = []
    for i in range(R_ - 1):
        for j in range(bins):
            a, b2 = i * bins + j, i * bins + (j + 1) % bins
            c2, d2 = a + bins, b2 + bins
            tris += [[a, c2, b2], [b2, c2, d2]]
    tris = np.array(tris)
    from body import tri_normals
    N = tri_normals(P, tris)
    # orient outward: the sole faces down, walls face away from the centre line
    probe = P - np.array([c[0], 0.05, c[1]])
    if np.mean(np.einsum("ij,ij->i", N, probe)) < 0:
        tris = tris[:, ::-1]
        N = -N
    n = len(P)
    col = np.tile(rgba(color), (n, 1))
    mats = np.full(n, mat, np.uint8)
    low = P[:, 1] < 0.0
    col[low] = rgba(sole_color)
    mats[low] = sole_mat
    jid = np.zeros((n, 4), np.uint8)
    jid[:, 0] = ank
    jw = np.zeros((n, 4), np.float32)
    jw[:, 0] = 1
    from body import JOINT_REGION
    return dwc.Part(name, P.astype(np.float32), N.astype(np.float32), col, mats, np.full(n, JOINT_REGION[ank], np.uint8), jid, jw,
                    tris.astype(np.int64))
