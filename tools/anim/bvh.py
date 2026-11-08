# damned_waters/tools/anim/bvh.py
# Purpose: read a BVH motion capture (100STYLE's: centimetres, Y-up, the actor facing +z, every joint
# rotated Y then X then Z as its channels list them) into arrays, and pose it (forward kinematics).
# ELI5: a BVH file is a puppet's string plan: the puppet's bones, then, frame by frame, how far to
# pull each string. This reads the plan and works out where every bone ends up.
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Joint:
    name: str
    parent: int
    offset: np.ndarray            # from the parent, in the parent's frame (as written: centimetres)
    channels: list[str] = field(default_factory=list)


@dataclass
class Motion:
    joints: list[Joint]
    frame_time: float
    data: np.ndarray              # (frames, channels)
    index: dict[str, int] = field(default_factory=dict)

    def joint(self, name: str) -> int:
        return self.index[name]


def read(path: str | Path) -> Motion:
    tokens = Path(path).read_text().split()
    joints: list[Joint] = []
    stack: list[int] = []
    i = tokens.index("HIERARCHY") + 1
    pending = None
    while tokens[i] != "MOTION":
        t = tokens[i]
        if t in ("ROOT", "JOINT"):
            pending = tokens[i + 1]
            i += 2
        elif t == "End":   # End Site: no channels; skip its block
            depth = 0
            i += 2
            while True:
                if tokens[i] == "{":
                    depth += 1
                elif tokens[i] == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
        elif t == "{":
            joints.append(Joint(pending, stack[-1] if stack else -1, np.zeros(3)))
            stack.append(len(joints) - 1)
            i += 1
        elif t == "}":
            stack.pop()
            i += 1
        elif t == "OFFSET":
            joints[stack[-1]].offset = np.array([float(v) for v in tokens[i + 1:i + 4]])
            i += 4
        elif t == "CHANNELS":
            n = int(tokens[i + 1])
            joints[stack[-1]].channels = tokens[i + 2:i + 2 + n]
            i += 2 + n
        else:
            i += 1
    i += 1
    frames = int(tokens[i + 1])
    frame_time = float(tokens[i + 4])
    i += 5
    ncol = sum(len(j.channels) for j in joints)
    data = np.array(tokens[i:i + frames * ncol], dtype=float).reshape(frames, ncol)
    return Motion(joints, frame_time, data, {j.name: k for k, j in enumerate(joints)})


def rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([np.stack([np.ones_like(a), 0 * a, 0 * a], -1), np.stack([0 * a, c, -s], -1), np.stack([0 * a, s, c], -1)], -2)


def ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([np.stack([c, 0 * a, s], -1), np.stack([0 * a, np.ones_like(a), 0 * a], -1), np.stack([-s, 0 * a, c], -1)], -2)


def rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.stack([np.stack([c, -s, 0 * a], -1), np.stack([s, c, 0 * a], -1), np.stack([0 * a, 0 * a, np.ones_like(a)], -1)], -2)


AXIS = {"X": rx, "Y": ry, "Z": rz}


def local_rotations(m: Motion) -> np.ndarray:
    """(frames, joints, 3, 3): each joint's rotation in its parent's frame, its channels applied in
    the order written (the first channel outermost: Y X Z gives Ry @ Rx @ Rz)."""
    F = m.data.shape[0]
    out = np.tile(np.eye(3), (F, len(m.joints), 1, 1))
    col = 0
    for k, j in enumerate(m.joints):
        R = np.tile(np.eye(3), (F, 1, 1))
        for ch in j.channels:
            if ch.endswith("rotation"):
                R = R @ AXIS[ch[0]](np.radians(m.data[:, col]))
            col += 1
        out[:, k] = R
    return out


def root_positions(m: Motion) -> np.ndarray:
    """(frames, 3): the root's position channels (centimetres)."""
    j = m.joints[0]
    cols = [j.channels.index(c) for c in ("Xposition", "Yposition", "Zposition")]
    return m.data[:, cols]


def forward_kinematics(m: Motion, local: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """World rotations (frames, joints, 3, 3) and positions (frames, joints, 3), centimetres."""
    local = local_rotations(m) if local is None else local
    F, J = local.shape[:2]
    G = np.zeros_like(local)
    P = np.zeros((F, J, 3))
    root = root_positions(m)
    for k, j in enumerate(m.joints):
        if j.parent < 0:
            G[:, k] = local[:, k]
            P[:, k] = root + j.offset
        else:
            G[:, k] = G[:, j.parent] @ local[:, k]
            P[:, k] = P[:, j.parent] + np.einsum("fij,j->fi", G[:, j.parent], j.offset)
    return G, P
