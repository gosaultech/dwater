# damned_waters/tools/anim/bake_mocap.py
# Purpose: bake motion-captured gait cycles (the 100STYLE dataset, CC BY 4.0) onto the game's rig:
# for each gait (sneak, walk, run, idle) the real cycles nearest its speed are found in a style's
# capture, averaged into one seamless loop, re-expressed in the rig's joint angles, and written to
# engine/src/mocap_clips.inc, which the engine plays by speed (include/dw/mocap.hpp).
#
#   python3 tools/anim/bake_mocap.py --src <dir holding 100STYLE/>     (writes the .inc and a report)
#
# The capture faces +z and the rig -z; both rotate a joint Y then X then Z, so a captured joint's
# rotation re-expressed for the rig is the same turn seen from behind: its X and Z angles change sign.
# The capture's five-piece spine folds into the rig's pelvis, spine and chest; legs map one to one.
# ELI5: a dancer's moves written down from one side of the stage, read out for a dancer facing the
# other way: lefts and rights stay, forward and back swap.
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

import bvh

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "engine" / "src" / "mocap_clips.inc"
SAMPLES = 64                      # a cycle, resampled
A = np.diag([-1.0, 1.0, -1.0])    # the capture's world seen from the rig's (a half turn about y)

# The rig's joints the clips drive (include/dw/mocap.hpp keeps this order), and how each is made
# from the capture's: a product of its local rotations.
JOINTS = [
    ("J_PELVIS", None),   # (from the hips, its heading taken out)
    ("J_SPINE", ["Chest", "Chest2"]),
    ("J_CHEST", ["Chest3", "Chest4"]),
    ("J_NECK", ["Neck"]),
    ("J_HEAD", ["Head"]),
    ("J_HIP_L", ["LeftHip"]),
    ("J_KNE_L", ["LeftKnee"]),
    ("J_ANK_L", ["LeftAnkle"]),
    ("J_HIP_R", ["RightHip"]),
    ("J_KNE_R", ["RightKnee"]),
    ("J_ANK_R", ["RightAnkle"]),
]

# Each gait: the style it's taken from, the capture (FW forward walk, FR forward run, ID idle), the
# speed wanted (m/s; the game's: dw/controls.hpp), how many cycles to average.
GAITS = {
    "sneak": {"style": "Swat", "take": "FW", "speed": 0.85, "average": 8, "trunk": -14, "gaze": -10},
    "walk": {"style": "Rushed", "take": "FW", "speed": 1.9, "average": 8, "trunk": -8, "gaze": -8},
    "run": {"style": "Rushed", "take": "FR", "speed": 2.6, "average": 8, "trunk": -16, "gaze": -10},
    "idle": {"style": "Neutral", "take": "ID", "seconds": 6.0, "trunk": -5, "gaze": -6},
    # The Drowned, one gait each (their variant): kept lopsided (not mirrored), hunched; their neck and
    # head stay the game's own (lolling, twitching).
    "drag": {"style": "DragRightLeg", "take": "FW", "speed": 0.8, "average": 6, "trunk": -22, "gaze": -10, "mirror": False},
    "drunk": {"style": "Drunk", "take": "FW", "speed": 0.85, "average": 6, "trunk": -18, "gaze": -10, "mirror": False},
    "lurch": {"style": "BentForward", "take": "FW", "speed": 0.85, "average": 6, "trunk": -26, "gaze": -10, "mirror": False},
}
# trunk: degrees he leans forward on average (pelvis, spine and chest together); gaze: where his face
# points on average (degrees below level). The actors leaned into hurrying and crouching, and the
# capture's neck sits 20 degrees further forward than this rig's: carried over as they were, with
# the gun held low, he walked bent over looking at his feet. Only the averages move: the motion
# about them is the actors'.


def euler_yxz(M: np.ndarray) -> np.ndarray:
    """(…, 3, 3) rotations -> (…, 3) angles (x, y, z) with M = Ry(y) @ Rx(x) @ Rz(z), as the rig
    composes them (character.cpp fk())."""
    x = np.arcsin(np.clip(-M[..., 1, 2], -1, 1))
    y = np.arctan2(M[..., 0, 2], M[..., 2, 2])
    z = np.arctan2(M[..., 1, 0], M[..., 1, 1])
    return np.stack([x, y, z], -1)


def from_euler_yxz(e: np.ndarray) -> np.ndarray:
    return bvh.ry(e[..., 1]) @ bvh.rx(e[..., 0]) @ bvh.rz(e[..., 2])


def orthonormal(M: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(M)
    R = u @ vt
    if np.linalg.det(R) < 0:
        u[:, -1] *= -1
        R = u @ vt
    return R


def rest_hip_height(m: bvh.Motion) -> float:
    """cm: the hips above the ground standing straight (the zero pose: the toes' tips on the floor)."""
    zero = np.tile(np.eye(3), (1, len(m.joints), 1, 1))
    one = bvh.Motion(m.joints, m.frame_time, m.data[:1].copy(), m.index)
    one.data[:, :3] = 0
    _, P = bvh.forward_kinematics(one, zero)
    lowest = P[0, :, 1].min()
    toe = P[0, m.joint("LeftToe")]
    sole = toe[1] - 1.3   # the end site's drop below the toe joint (100STYLE: 1.29 cm)
    return float(-min(lowest, sole))


def leg_length(m: bvh.Motion) -> float:
    return float(np.linalg.norm(m.joints[m.joint("LeftKnee")].offset) + np.linalg.norm(m.joints[m.joint("LeftAnkle")].offset))


def gait_cycles(m: bvh.Motion, P: np.ndarray) -> list[tuple[int, int]]:
    """Each stride (left foot down to left foot down again) as (first frame, last frame)."""
    a = P[:, m.joint("LeftAnkle"), 1]
    a = np.convolve(a, np.ones(5) / 5, mode="same")
    w = 10
    lows = [i for i in range(w, len(a) - w) if a[i] == a[i - w:i + w + 1].min()]
    return [(i0, i1) for i0, i1 in zip(lows, lows[1:]) if 0.45 < (i1 - i0) * m.frame_time < 1.8]


def joint_rotations(m: bvh.Motion, local: np.ndarray) -> dict[str, np.ndarray]:
    """The rig's joints (but the pelvis) as (frames, 3, 3), still in the capture's axes."""
    out = {}
    for name, parts in JOINTS:
        if parts is None:
            continue
        R = np.tile(np.eye(3), (local.shape[0], 1, 1))
        for p in parts:
            R = R @ local[:, m.joint(p)]
        out[name] = R
    return out


def resample(x: np.ndarray, n: int) -> np.ndarray:
    """(frames, …) -> (n, …), evenly over [0, 1) of the cycle (the last frame is the next's first)."""
    t = np.linspace(0, x.shape[0] - 1, n, endpoint=False)
    i = np.floor(t).astype(int)
    f = (t - i).reshape((-1,) + (1,) * (x.ndim - 1))
    j = np.minimum(i + 1, x.shape[0] - 1)
    return x[i] * (1 - f) + x[j] * f


def cycle(m: bvh.Motion, local, G, P, i0: int, i1: int) -> dict:
    """One stride as the rig sees it: per sample, the pelvis's offset from his steady path (m, the
    rig's axes) and the rig's joints' rotations (3x3, the rig's axes); its stride (m) and speed."""
    frames = np.arange(i0, i1 + 1)
    root = P[frames, 0] / 100.0
    d = root[-1] - root[0]
    heading = math.atan2(d[0], d[2])                     # the way he went (the capture faces +z)
    H = bvh.ry(np.array(heading))
    T = (i1 - i0) * m.frame_time
    t = (frames - i0) * m.frame_time
    path = root[0] + np.outer(t / T, d)
    off = (root - path) @ H                               # into his own frame: across, up, along
    off[:, 1] = root[:, 1]                                # (height kept absolute: the pelvis above the floor)
    off = off @ A                                         # (x and z turned round for the rig)
    rots = joint_rotations(m, local)
    out = {n: A @ R[frames] @ A for n, R in rots.items()}
    out["J_PELVIS"] = A @ (H.T @ G[frames, 0]) @ A        # the hips, his heading taken out
    return {"off": off, "rot": out, "stride": float(np.hypot(d[0], d[2])), "time": T, "heading_turn": 0.0}


def straightness(P: np.ndarray, i0: int, i1: int) -> float:
    """Degrees the path bends over the stride (between its two halves)."""
    r = P[i0:i1 + 1, 0, [0, 2]]
    h = len(r) // 2
    a, b = r[h] - r[0], r[-1] - r[h]
    return abs(math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a @ b)))


def average_cycle(cycles: list[dict]) -> dict:
    """The cycles resampled to SAMPLES and averaged (rotations by their mean, made a rotation again),
    then closed into a loop: what's left between the last sample and the first is spread over it."""
    off = np.mean([resample(c["off"], SAMPLES) for c in cycles], axis=0)
    rot = {}
    for name, _ in JOINTS:
        mean = np.mean([resample(c["rot"][name], SAMPLES) for c in cycles], axis=0)
        rot[name] = np.array([orthonormal(M) for M in mean])
    stride = float(np.mean([c["stride"] for c in cycles]))
    time = float(np.mean([c["time"] for c in cycles]))
    return {"off": off, "rot": rot, "stride": stride, "time": time}


def symmetric(rows: np.ndarray) -> np.ndarray:
    """The loop (as angles(): closed, unwrapped) averaged with its own mirror image half a loop on:
    each leg does what the other did half a step before, turned left for right, so one actor's
    favoured side (a capture run in arcs) doesn't make him limp. Mirrored across his middle, a
    rotation keeps its x angle and its y and z change sign; the offset's x changes sign."""
    names = [n for n, _ in JOINTS]
    swap = {"J_HIP_L": "J_HIP_R", "J_KNE_L": "J_KNE_R", "J_ANK_L": "J_ANK_R", "J_HIP_R": "J_HIP_L", "J_KNE_R": "J_KNE_L", "J_ANK_R": "J_ANK_L"}
    half = np.roll(rows, -(len(rows) // 2), axis=0)
    mirror = np.empty_like(rows)
    mirror[:, 0:3] = half[:, 0:3] * [-1, 1, 1]
    for k, n in enumerate(names):
        o = names.index(swap.get(n, n))
        mirror[:, 3 + 3 * k:6 + 3 * k] = half[:, 3 + 3 * o:6 + 3 * o] * [1, -1, -1]
    return (rows + mirror) / 2


def posture(rows: np.ndarray, trunk_deg: float, gaze_deg: float) -> np.ndarray:
    """Set the loop's average lean and gaze (see GAITS), keeping its motion: the pelvis, spine and
    chest share the change in lean (the hips take back the pelvis's share, so the legs swing where
    they did), and the neck takes what's left to bring the face to its gaze."""
    r = rows.copy()
    col = {n: 3 + 3 * k for k, (n, _) in enumerate(JOINTS)}
    pelvis, spine, chest, neck, head = (col[n] for n in ("J_PELVIS", "J_SPINE", "J_CHEST", "J_NECK", "J_HEAD"))
    d = math.radians(trunk_deg) - (r[:, pelvis] + r[:, spine] + r[:, chest]).mean()
    r[:, pelvis] += 0.35 * d
    r[:, spine] += 0.4 * d
    r[:, chest] += 0.25 * d
    for hip in ("J_HIP_L", "J_HIP_R"):
        r[:, col[hip]] -= 0.35 * d
    e = math.radians(gaze_deg) - (r[:, pelvis] + r[:, spine] + r[:, chest] + r[:, neck] + r[:, head]).mean()
    r[:, neck] += e
    return r


def angles(clip: dict) -> np.ndarray:
    """(SAMPLES, 3 + 3 * len(JOINTS)): the pelvis's offset, then each joint's (x, y, z), unwrapped
    along the loop and closed (the last sample runs smoothly into the first)."""
    cols = [clip["off"]]
    for name, _ in JOINTS:
        e = euler_yxz(clip["rot"][name])
        e = np.unwrap(e, axis=0)
        cols.append(e)
    x = np.concatenate(cols, axis=1)
    gap = x[0] - (2 * x[-1] - x[-2])                      # where the loop would land vs where it starts
    ramp = np.linspace(0, 1, len(x), endpoint=False)[:, None]
    return x + gap * ramp


def bake_gait(src: Path, g: dict) -> dict:
    m = bvh.read(src / "100STYLE" / g["style"] / f"{g['style']}_{g['take']}.bvh")
    local = bvh.local_rotations(m)
    G, P = bvh.forward_kinematics(m, local)
    if g["take"] == "ID":   # idle: a stretch of standing, looped
        n = int(g["seconds"] / m.frame_time)
        start = len(P) // 3
        frames = np.arange(start, start + n)
        root = P[frames, 0] / 100.0
        heading = float(np.arctan2(*np.mean([(G[f, 0] @ [0, 0, 1])[[0, 2]] for f in frames], axis=0)))
        H = bvh.ry(np.array(heading))
        off = (root - root.mean(axis=0)) @ H
        off[:, 1] = root[:, 1]
        off = off @ A
        rots = joint_rotations(m, local)
        rot = {n_: A @ R[frames] @ A for n_, R in rots.items()}
        rot["J_PELVIS"] = A @ (H.T @ G[frames, 0]) @ A
        clip = {"off": resample(off, SAMPLES * 3), "rot": {k: resample(v, SAMPLES * 3) for k, v in rot.items()},
                "stride": 0.0, "time": float(n * m.frame_time)}
        for k in clip["rot"]:
            clip["rot"][k] = np.array([orthonormal(M) for M in clip["rot"][k]])
        return {"clip": clip, "source": m, "cycles": 1}
    spans = [(i0, i1) for i0, i1 in gait_cycles(m, P) if straightness(P, i0, i1) < 10]
    speeds = np.array([np.hypot(*(P[i1, 0, [0, 2]] - P[i0, 0, [0, 2]])) / 100 / ((i1 - i0) * m.frame_time) for i0, i1 in spans])
    order = np.argsort(np.abs(speeds - g["speed"]))
    near = [k for k in order if abs(speeds[k] - g["speed"]) <= 0.15 * g["speed"]]
    order = (near if len(near) >= 3 else list(order[:3]))[: g["average"]]   # (cycles far off the speed would blur it)
    cycles = [cycle(m, local, G, P, *spans[k]) for k in order]
    return {"clip": average_cycle(cycles), "source": m, "cycles": len(cycles), "speeds": speeds[order].tolist(),
            "symmetric": g.get("mirror", True)}


def write_inc(baked: dict, path: Path = OUT) -> None:
    lines = ["// damned_waters/engine/src/mocap_clips.inc",
             "// Purpose: motion-captured gait cycles baked onto the rig by tools/anim/bake_mocap.py (do not edit:",
             "// re-bake). From the 100STYLE dataset (Mason, Starke, Komura 2022; CC BY 4.0, docs/motion_credits.md).",
             "// Per clip: its stride (m) and time (s) as captured, the capture's standing hip height and leg length",
             "// (m: the engine scales by the rig's), and SAMPLES rows of: the pelvis's offset (x, y, z: m, y the height",
             "// above the floor) and the joints of mocap::JOINTS as the rig's angles (x, y, z: radians).", ""]
    for name, b in baked.items():
        clip, m = b["clip"], b["source"]
        rows = angles(clip)
        if b.get("symmetric"):
            rows = symmetric(rows)
        rows = posture(rows, b["gait"]["trunk"], b["gait"]["gaze"])
        lines.append(f"const float CLIP_{name.upper()}[] = {{")
        for r in rows:
            lines.append("    " + ", ".join(f"{v:.5f}f" for v in r) + ",")
        lines.append("};")
        lines.append(f"const Clip {name.upper()}{{\"{name}\", {clip['stride']:.4f}f, {clip['time']:.4f}f, "
                     f"{rest_hip_height(m) / 100:.4f}f, {leg_length(m) / 100:.4f}f, {len(rows)}, CLIP_{name.upper()}}};")
        lines.append("")
    path.write_text("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="the directory holding 100STYLE/ (unzipped from Zenodo record 8127870)")
    a = ap.parse_args(argv)
    baked, report = {}, {}
    for name, g in GAITS.items():
        b = bake_gait(Path(a.src), g)
        b["gait"] = g
        baked[name] = b
        c = b["clip"]
        report[name] = {"style": g["style"], "take": g["take"], "cycles averaged": b["cycles"], "stride_m": round(c["stride"], 3),
                        "time_s": round(c["time"], 3), "speed_mps": round(c["stride"] / c["time"], 3) if c["stride"] else 0,
                        "speeds": [round(v, 2) for v in b.get("speeds", [])]}
    write_inc(baked)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
