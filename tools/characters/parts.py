# damned_waters/tools/characters/parts.py
# Purpose: cut dw Parts (separately drawn, skinned meshes) out of a Body, and the
# small material vocabulary shared with the engine shader (dw::Mat).
from __future__ import annotations

import numpy as np

import dwc
from body import Body, quad_normals

# dw::Mat ids (engine/include/dw/mesh_builder.hpp)
MAT = dict(skin=1, drowned=2, wool=4, cloth=5, denim=6, leather=7, hair=8, eye=9, iris=10, metal=11, flesh=12, void=13,
           leech=14, rot=15, dead_eye=16, tooth=17, bone=18, tongue=19, guts=20, mussel=21, weed=22, slough=23, dermis=24,
           steel=25, grip=26, wax=27, knit=28, lips=29, brow=30, rubber=31, nylon=32, cotton=33, print=34, locs=35, lamp=36)


def rgba(c) -> np.ndarray:
    c = list(c)
    return np.array(c + [255] * (4 - len(c)), dtype=np.uint8)


def part_from_quads(name: str, body: Body, quads: np.ndarray, pos: np.ndarray | None = None, mat=MAT["skin"],
                    col=(200, 200, 200), normals: np.ndarray | None = None, flip: bool = False) -> dwc.Part:
    """A part from global-vertex quads of the body. pos overrides positions (e.g. an offset clothing shell)."""
    ids, local = np.unique(quads, return_inverse=True)
    local = local.reshape(quads.shape)
    P = (body.V if pos is None else pos)[ids].astype(np.float32)
    N = normals[ids] if normals is not None else quad_normals(P.astype(np.float64), local)
    tris = np.concatenate([local[:, [0, 1, 2]], local[:, [0, 2, 3]]])
    if flip:
        tris = tris[:, ::-1]
        N = -N
    n = len(ids)
    return dwc.Part(name, P, N.astype(np.float32), np.tile(rgba(col), (n, 1)), np.full(n, mat, np.uint8),
                    body.region[ids].astype(np.uint8), body.jid[ids].astype(np.uint8), body.jw[ids].astype(np.float32),
                    tris.astype(np.int64))
