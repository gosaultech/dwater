# damned_waters/tools/characters/body.py
# Purpose: one MakeHuman body, ready for dressing: morphed from its macro settings,
# re-posed to the engine's rest pose, in engine space (metres, facing -Z, soles on
# y = 0), with normals, engine joint weights, body regions, and MakeHuman's own bone
# weights kept for painting faces (lips = the orbicularis oris bones, and so on).
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

import mhdata
import rig

# dw::Region for each engine joint (see engine/include/dw/anatomy.hpp).
R_BODY, R_HEAD, R_JAW, R_UARM_L, R_FARM_L, R_UARM_R, R_FARM_R, R_THIGH_L, R_SHIN_L, R_THIGH_R, R_SHIN_R = range(11)
JOINT_REGION = [R_BODY, R_BODY, R_BODY, R_BODY, R_HEAD, R_JAW, R_UARM_L, R_FARM_L, R_FARM_L, R_UARM_R, R_FARM_R, R_FARM_R,
                R_THIGH_L, R_SHIN_L, R_SHIN_L, R_THIGH_R, R_SHIN_R, R_SHIN_R, R_FARM_L, R_FARM_L, R_FARM_L, R_FARM_R, R_FARM_R, R_FARM_R]
J = {n: i for i, n in enumerate(rig.ENGINE_JOINTS)}


def quad_normals(V: np.ndarray, quads: np.ndarray) -> np.ndarray:
    """Smooth vertex normals from quads (area-weighted, via the diagonals' cross product)."""
    a, b, c, d = (V[quads[:, i]] for i in range(4))
    fn = np.cross(c - a, d - b)
    N = np.zeros_like(V)
    for i in range(4):
        np.add.at(N, quads[:, i], fn)
    L = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(L, 1e-12)


def tri_normals(V: np.ndarray, tris: np.ndarray) -> np.ndarray:
    fn = np.cross(V[tris[:, 1]] - V[tris[:, 0]], V[tris[:, 2]] - V[tris[:, 0]])
    N = np.zeros_like(V)
    for i in range(3):
        np.add.at(N, tris[:, i], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


@dataclass
class Body:
    V: np.ndarray             # (N,3) every base-mesh vertex (body + helpers), engine space, rest pose
    N: np.ndarray             # (N,3) normals (body faces only for body vertices)
    body_quads: np.ndarray    # (F,4)
    groups: dict              # helper group -> (G,4) quads (global vertex ids)
    jid: np.ndarray           # (N,4) engine joint ids
    jw: np.ndarray            # (N,4) weights
    joints: np.ndarray        # (18,3) engine joint rest positions
    bone_w: dict              # MakeHuman bone -> (N,) weight, for painting
    body_ids: np.ndarray      # vertex ids used by the body group

    @property
    def dominant(self) -> np.ndarray:
        return self.jid[:, 0]

    @property
    def region(self) -> np.ndarray:
        return np.array(JOINT_REGION, dtype=np.uint8)[self.dominant]

    def weight_of(self, *joints: str) -> np.ndarray:
        """Total skin weight each vertex gives to the named engine joints."""
        ids = [J[j] for j in joints]
        return np.sum(np.where(np.isin(self.jid, ids), self.jw, 0.0), axis=1)

    def bone(self, *prefixes: str) -> np.ndarray:
        """Total MakeHuman weight of all bones whose name starts with one of the prefixes."""
        out = np.zeros(len(self.V))
        for name, w in self.bone_w.items():
            if name.startswith(prefixes):
                out += w
        return out


def normals(V: np.ndarray, body_quads: np.ndarray, groups: dict) -> np.ndarray:
    """Vertex normals: the body's from its faces; each helper's from its own (so they don't bleed into the skin)."""
    N = quad_normals(V, body_quads)
    for g, q in groups.items():
        if g == "body":
            continue
        ids = np.unique(q)
        N[ids] = quad_normals(V, q)[ids]
    return N


def build(data: Path, macro: mhdata.Macro, extra: dict[str, float] | None = None) -> Body:
    mesh = mhdata.load_obj(data / "3dobjs" / "base.obj")
    skel = mhdata.load_skeleton(data / "rigs" / "default.mhskel")
    weights = mhdata.load_weights(data / "rigs" / "default_weights.mhw")
    targets = mhdata.macro_targets(data, macro)
    targets += [(data / "targets" / rel, w) for rel, w in (extra or {}).items()]
    mesh.verts = mhdata.apply_targets(mesh.verts, targets)
    rest, posed = rig.rest_pose(mesh, skel, weights)
    V = rig.to_engine(rest)
    joints = rig.to_engine(rig.engine_joints(skel, rest, posed))
    body_ids = mesh.group_verts("body")
    floor = V[body_ids, 1].min()
    V[:, 1] -= floor
    joints[:, 1] -= floor
    body_quads = np.array(mesh.group_faces("body"), dtype=np.int64)
    groups = {}
    for g in {f[0] for f in mesh.faces}:
        if g.startswith("helper-") or g in ("body",):
            fs = [f[1] for f in mesh.faces if f[0] == g]
            if all(len(f) == 4 for f in fs):
                groups[g] = np.array(fs, dtype=np.int64)
    N = normals(V, body_quads, groups)
    jid, jw = rig.fold_weights(skel, weights, len(V))
    bone_w = {}
    for b, (idx, w) in weights.items():
        a = np.zeros(len(V))
        a[idx] = w
        bone_w[b] = a
    return Body(V, N, body_quads, groups, jid, jw, joints, bone_w, body_ids)
