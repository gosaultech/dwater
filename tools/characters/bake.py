# damned_waters/tools/characters/bake.py
# Purpose: bake ambient occlusion into a character, per vertex. Light that reaches a
# point from the sky of its surroundings is blocked by nearby geometry: an armpit, the
# skin just under a collar, the fold where a jacket meets a hoodie. Those places should
# be darker, and without that darkening a character looks pasted onto the scene (the
# "CG look"). The engine multiplies lighting by this value (it rides in the colour's
# alpha channel, see Character::add_skinned).
#
# How (ELI5): fill a box of 1 cm cubes with "is there cloth or skin here?", then from
# every vertex throw a couple of dozen short rays outward over its hemisphere. The more
# rays that bump into something within a hand's width, the darker the vertex.
from __future__ import annotations

import numpy as np

import dwc

# Barycentric sample points per triangle (a 5 x 5 grid over the triangle).
_K = 5
_BARY = np.array([(i / _K, j / _K) for i in range(_K + 1) for j in range(_K + 1 - i)])


def _voxelize(parts: list[dwc.Part], cell: float, pad: float) -> tuple[np.ndarray, np.ndarray]:
    """Occupancy grid of every triangle of every part: (grid bool[x, y, z], origin)."""
    pts = []
    for p in parts:
        if not len(p.tris):
            continue
        a, b, c = (p.pos[p.tris[:, k]].astype(np.float64) for k in range(3))
        u, v = _BARY[:, 0][None, :, None], _BARY[:, 1][None, :, None]
        pts.append((a[:, None] + (b - a)[:, None] * u + (c - a)[:, None] * v).reshape(-1, 3))
    P = np.concatenate(pts)
    lo = P.min(axis=0) - pad
    dims = np.ceil((P.max(axis=0) + pad - lo) / cell).astype(int) + 1
    grid = np.zeros(dims, bool)
    ix = ((P - lo) / cell).astype(int)
    grid[ix[:, 0], ix[:, 1], ix[:, 2]] = True
    return grid, lo


def _hemisphere(count: int, seed: int) -> np.ndarray:
    """Cosine-weighted directions over the +Z hemisphere (a golden-angle spiral, jittered once)."""
    rng = np.random.default_rng(seed)
    i = np.arange(count) + rng.random(count) * 0.5
    r = np.sqrt(i / count)
    phi = i * np.pi * (3 - np.sqrt(5))
    return np.stack([r * np.cos(phi), r * np.sin(phi), np.sqrt(np.maximum(0.0, 1 - r * r))], axis=1)


def occlusion(parts: list[dwc.Part], cell: float = 0.01, rays: int = 24, reach: float = 0.14, start: float = 0.014,
              seed: int = 3) -> list[np.ndarray]:
    """Per-vertex occlusion (0 = open sky, 1 = buried) for each part, against all parts."""
    grid, lo = _voxelize(parts, cell, reach + start + cell)
    dirs = _hemisphere(rays, seed)
    steps = np.arange(start, reach + 1e-9, cell * 0.9)
    fall = 1.0 - (steps - start) / (reach - start + 1e-9)       # a hit close by blocks more than a far one
    out = []
    for p in parts:
        N = p.nrm.astype(np.float64)
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        helper = np.where(np.abs(N[:, 1:2]) > 0.9, np.array([[1.0, 0, 0]]), np.array([[0, 1.0, 0]]))
        T = np.cross(helper, N)
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        B = np.cross(N, T)
        occ = np.zeros(len(N))
        for c0 in range(0, len(N), 2048):                      # in chunks, to bound memory
            sl = slice(c0, c0 + 2048)
            D = T[sl, None] * dirs[None, :, 0:1] + B[sl, None] * dirs[None, :, 1:2] + N[sl, None] * dirs[None, :, 2:3]
            base = p.pos[sl].astype(np.float64) + N[sl] * cell * 0.6
            S = base[:, None, None] + D[:, :, None] * steps[None, None, :, None]     # (v, rays, steps, 3)
            ix = np.clip(((S - lo) / cell).astype(int), 0, np.array(grid.shape) - 1)
            hit = grid[ix[..., 0], ix[..., 1], ix[..., 2]]                              # (v, rays, steps)
            first = np.where(hit.any(axis=2), hit.argmax(axis=2), -1)
            block = np.where(first >= 0, fall[np.maximum(first, 0)], 0.0)
            occ[sl] = block.mean(axis=1)
        out.append(occ)
    return out


def bake_ao(ch: dwc.Character, strength: float = 0.8, skip=("eye_l", "eye_r", "teeth_up", "teeth_lo", "tongue")) -> None:
    """Write occlusion into every part's colour alpha (255 = unoccluded). Eyes, teeth and tongue
    sit inside the head and would read as fully buried, so they keep full light (they have their
    own dark surroundings modelled)."""
    parts = [p for p in ch.parts if p.name not in skip]
    for p, occ in zip(parts, occlusion(parts)):
        ao = np.clip(1.0 - strength * occ, 0.15, 1.0)
        p.col = p.col.copy()
        p.col[:, 3] = np.round(ao * 255).astype(np.uint8)
