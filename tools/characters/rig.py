# damned_waters/tools/characters/rig.py
# Purpose: turn a morphed MakeHuman body into an engine-ready one.
#   1. re-pose it from MakeHuman's A-pose to the engine's rest pose (arms hanging,
#      legs straight), skinning with MakeHuman's own 163 bones so the shoulders keep
#      their shape: the rotation is spread over clavicle, shoulder and upper arm;
#   2. convert to engine space: metres, facing -Z, soles on the floor;
#   3. fold the 163 bones onto the engine's 18 joints (every bone joins its nearest
#      mapped ancestor), keeping the four strongest influences per vertex.
# Engine joints, in the order of dw::Joint (engine/include/dw/character.hpp):
from __future__ import annotations

import numpy as np

from mhdata import BaseMesh, Skeleton

ENGINE_JOINTS = ["pelvis", "spine", "chest", "neck", "head", "jaw", "sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r",
                 "hip_l", "kne_l", "ank_l", "hip_r", "kne_r", "ank_r",
                 "fing1_l", "fing2_l", "thumb_l", "fing1_r", "fing2_r", "thumb_r"]
ENGINE_PARENT = [-1, 0, 1, 2, 3, 4, 2, 6, 7, 2, 9, 10, 0, 12, 13, 0, 15, 16, 8, 18, 8, 11, 21, 11]
# Which MakeHuman bone head each engine joint sits on, and which bones fold into it.
# (MakeHuman ".L" is the body's left; the engine's left is "_l".)
JOINT_BONE = {"pelvis": "spine05", "spine": "spine03", "chest": "spine01", "neck": "neck01", "head": "head", "jaw": "jaw",
              "sho_l": "upperarm01.L", "elb_l": "lowerarm01.L", "wri_l": "wrist.L",
              "sho_r": "upperarm01.R", "elb_r": "lowerarm01.R", "wri_r": "wrist.R",
              "hip_l": "upperleg01.L", "kne_l": "lowerleg01.L", "ank_l": "foot.L",
              "hip_r": "upperleg01.R", "kne_r": "lowerleg01.R", "ank_r": "foot.R",
              "thumb_l": "finger1-2.L", "thumb_r": "finger1-2.R"}
# Finger joints pivot on the whole knuckle line: the mean of the four fingers' segment heads.
KNUCKLES = {"fing1_l": ("L", 1), "fing2_l": ("L", 2), "fing1_r": ("R", 1), "fing2_r": ("R", 2)}
FOLD = {"root": "pelvis", "spine05": "pelvis", "pelvis.L": "pelvis", "pelvis.R": "pelvis",
        "spine04": "spine", "spine03": "spine", "spine02": "chest", "spine01": "chest",
        "neck01": "neck", "neck02": "neck", "neck03": "neck", "head": "head", "jaw": "jaw",
        "shoulder01.L": "sho_l", "upperarm01.L": "sho_l", "upperarm02.L": "sho_l",
        "lowerarm01.L": "elb_l", "lowerarm02.L": "elb_l", "wrist.L": "wri_l",
        "shoulder01.R": "sho_r", "upperarm01.R": "sho_r", "upperarm02.R": "sho_r",
        "lowerarm01.R": "elb_r", "lowerarm02.R": "elb_r", "wrist.R": "wri_r",
        "upperleg01.L": "hip_l", "upperleg02.L": "hip_l", "lowerleg01.L": "kne_l", "lowerleg02.L": "kne_l", "foot.L": "ank_l",
        "upperleg01.R": "hip_r", "upperleg02.R": "hip_r", "lowerleg01.R": "kne_r", "lowerleg02.R": "kne_r", "foot.R": "ank_r"}
for _s in ("L", "R"):
    for _f in range(2, 6):   # index..little: base segment curls at the knuckles, the rest at the middle joints
        FOLD[f"finger{_f}-1.{_s}"] = f"fing1_{_s.lower()}"
        FOLD[f"finger{_f}-2.{_s}"] = f"fing2_{_s.lower()}"
        FOLD[f"finger{_f}-3.{_s}"] = f"fing2_{_s.lower()}"
    FOLD[f"finger1-2.{_s}"] = f"thumb_{_s.lower()}"
    FOLD[f"finger1-3.{_s}"] = f"thumb_{_s.lower()}"
DM_TO_M = 0.1


def rot(axis: np.ndarray, angle: float) -> np.ndarray:
    """3x3 rotation about a unit axis (Rodrigues)."""
    a = axis / np.linalg.norm(axis)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * (k @ k)


def arc(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Shortest rotation taking direction u onto direction v."""
    u, v = u / np.linalg.norm(u), v / np.linalg.norm(v)
    c = float(np.clip(u @ v, -1, 1))
    ax = np.cross(u, v)
    if np.linalg.norm(ax) < 1e-9:
        return np.eye(3)
    return rot(ax, np.arccos(c))


class Posed:
    """Bone transforms for one pose: each bone = rotation about its head, stacked on its parent."""

    def __init__(self, skel: Skeleton, verts: np.ndarray):
        self.skel, self.verts = skel, verts
        self.local = {}          # bone -> 3x3 world-space rotation applied at that bone
        self.R, self.t = {}, {}  # bone -> composed transform x -> R x + t

    def compose(self):
        for b in self.skel.order:
            p = self.skel.bones[b]["parent"]
            Rp, tp = (self.R[p], self.t[p]) if p else (np.eye(3), np.zeros(3))
            h = Rp @ self.skel.head(self.verts, b) + tp          # where this bone's head has moved to
            L = self.local.get(b, np.eye(3))
            self.R[b] = L @ Rp
            self.t[b] = L @ (tp - h) + h
        return self

    def point(self, bone: str, x: np.ndarray) -> np.ndarray:
        return self.R[bone] @ x + self.t[bone]


def skin(verts: np.ndarray, weights: dict, posed: Posed) -> np.ndarray:
    """Linear blend skinning of all vertices with MakeHuman's full weight set."""
    out = np.zeros_like(verts)
    total = np.zeros(len(verts))
    for bone, (idx, w) in weights.items():
        if bone not in posed.R:
            continue
        moved = verts[idx] @ posed.R[bone].T + posed.t[bone]
        np.add.at(out, idx, moved * w[:, None])
        np.add.at(total, idx, w)
    unweighted = total < 1e-6
    out[unweighted] = verts[unweighted]
    out[~unweighted] /= total[~unweighted, None]
    return out


def rest_pose(mesh: BaseMesh, skel: Skeleton, weights: dict, arm_out_deg: float = 7.0, leg_out_deg: float = 2.0) -> tuple[np.ndarray, Posed]:
    """Arms down (a few degrees out from the hips), forearms straight with thumbs forward, legs straight."""
    V = mesh.verts
    P = Posed(skel, V)
    for side, s in (("L", 1.0), ("R", -1.0)):   # MakeHuman left is +x
        up = skel.head(V, f"upperarm01.{side}")
        el = skel.head(V, f"lowerarm01.{side}")
        cur = np.degrees(np.arctan2(abs(el[0] - up[0]), up[1] - el[1]))       # degrees out from straight down
        total = np.radians(cur - arm_out_deg)
        for bone, share in ((f"clavicle.{side}", 0.15), (f"shoulder01.{side}", 0.25), (f"upperarm01.{side}", 0.6)):
            P.local[bone] = rot(np.array([0, 0, 1.0]), -s * total * share)
        P.compose()
        # Forearm: in line with the upper arm, then twisted so the thumb points forward (+Z here).
        wr = skel.head(V, f"wrist.{side}")
        up_dir = P.point(f"upperarm01.{side}", el) - P.point(f"upperarm01.{side}", up)
        fore = P.point(f"upperarm02.{side}", wr) - P.point(f"upperarm02.{side}", el)
        straight = arc(fore, up_dir)
        P.local[f"lowerarm01.{side}"] = straight
        P.compose()
        axis = up_dir / np.linalg.norm(up_dir)
        thumb = P.point(f"lowerarm02.{side}", skel.head(V, f"finger1-1.{side}")) - P.point(f"lowerarm02.{side}", wr)
        thumb -= axis * (thumb @ axis)
        fwd = np.array([0, 0, 1.0]) - axis * axis[2]
        ang = np.arctan2(np.cross(thumb, fwd) @ axis, thumb @ fwd)
        P.local[f"lowerarm01.{side}"] = rot(axis, ang * 0.5) @ straight
        P.local[f"lowerarm02.{side}"] = rot(axis, ang * 0.5)
        P.compose()
        # Legs: thigh and shin straight down, a touch apart.
        hp, kn, an = (skel.head(V, f"{b}.{side}") for b in ("upperleg01", "lowerleg01", "foot"))
        want = np.array([s * np.sin(np.radians(leg_out_deg)), -np.cos(np.radians(leg_out_deg)), 0.0])
        P.local[f"upperleg01.{side}"] = arc(kn - hp, want)
        P.compose()
        shin = P.point(f"upperleg02.{side}", an) - P.point(f"upperleg02.{side}", kn)
        P.local[f"lowerleg01.{side}"] = arc(shin, want)
        P.compose()
    return skin(V, weights, P), P


def to_engine(p: np.ndarray) -> np.ndarray:
    """MakeHuman (dm, +Z front, +X left) -> engine (m, -Z front, -X left): turn 180 degrees about Y."""
    q = np.asarray(p, dtype=np.float64) * DM_TO_M
    return q * np.array([-1.0, 1.0, -1.0])


def engine_joints(skel: Skeleton, rest_verts: np.ndarray, posed: Posed) -> np.ndarray:
    """Engine joint positions in the rest pose (MakeHuman space; convert with to_engine)."""
    out = []
    for name in ENGINE_JOINTS:
        if name in KNUCKLES:
            side, seg = KNUCKLES[name]
            bones = [f"finger{f}-{seg}.{side}" for f in range(2, 6)]
            out.append(np.mean([posed.point(b, skel.head(posed.verts, b)) for b in bones], axis=0))
            continue
        bone = JOINT_BONE[name]
        out.append(posed.point(bone, skel.head(posed.verts, bone)))
    return np.array(out)


def fold_weights(skel: Skeleton, weights: dict, n_verts: int) -> tuple[np.ndarray, np.ndarray]:
    """Collapse MakeHuman bone weights onto engine joints; returns (ids (N,4) uint8, weights (N,4) float32)."""
    jidx = {n: i for i, n in enumerate(ENGINE_JOINTS)}
    acc = np.zeros((n_verts, len(ENGINE_JOINTS)))

    def target(bone):
        for b in skel.ancestors(bone):
            if b in FOLD:
                return FOLD[b]
            if b == "jaw":
                return "jaw"
        return "pelvis"

    for bone, (idx, w) in weights.items():
        np.add.at(acc[:, jidx[target(bone)]], idx, w)
    order = np.argsort(-acc, axis=1)[:, :4]
    ids = order.astype(np.uint8)
    ws = np.take_along_axis(acc, order, axis=1)
    s = ws.sum(axis=1, keepdims=True)
    ws = np.where(s > 1e-9, ws / np.maximum(s, 1e-9), np.array([[1.0, 0, 0, 0]]))
    ids[s[:, 0] <= 1e-9] = 0
    return ids, ws.astype(np.float32)
