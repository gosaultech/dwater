# damned_waters/tools/characters/mhdata.py
# Purpose: read MakeHuman's CC0 data (base mesh, morph targets, default rig and
# skin weights) and blend a body from "macro" settings exactly the way MakeHuman
# does: every macro target is a corner of a box (gender x age x muscle x weight),
# and a body is a weighted mix of the corners around its settings, like mixing
# paint from a few base colours.
#
# The data is not vendored (the macro targets alone are ~100 MB). fetch() makes a
# sparse, blob-less clone of one pinned MakeHuman commit into a local cache, so a
# build is reproducible and only downloads the ~130 MB it needs, once.
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MH_REPO = "https://github.com/makehumancommunity/makehuman.git"
MH_COMMIT = "a8bc2d54ff0ac92e78ff71431b1023eda42bf482"   # pinned: data changes must be deliberate
SPARSE_PATHS = [
    "/makehuman/data/3dobjs/", "/makehuman/data/rigs/", "/makehuman/data/targets/macrodetails/",
    "/makehuman/data/targets/stomach/", "/makehuman/data/targets/armslegs/", "/makehuman/data/targets/expression/",
    "/makehuman/data/targets/head/", "/makehuman/data/targets/nose/", "/makehuman/data/targets/mouth/",
    "/makehuman/data/targets/chin/", "/makehuman/data/targets/cheek/", "/makehuman/data/targets/eyes/",
    "/makehuman/data/targets/neck/", "/makehuman/data/targets/torso/", "/makehuman/data/targets/breast/",
    "/makehuman/data/targets/bodyshapes/", "/makehuman/data/targets/measure/", "/LICENSE*",
]
DEFAULT_CACHE = Path(__file__).resolve().parent / ".cache" / "makehuman"


def fetch(cache: Path = DEFAULT_CACHE) -> Path:
    """Clone (once) the pinned MakeHuman commit's data into `cache`; returns makehuman/data."""
    data = cache / "makehuman" / "data"
    if (data / "3dobjs" / "base.obj").exists():
        return data
    cache.parent.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, check=True, capture_output=True, text=True)
    if not (cache / ".git").exists():
        run("git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", MH_REPO, str(cache))
    run("git", "-C", str(cache), "config", "core.sparseCheckout", "true")
    (cache / ".git" / "info").mkdir(exist_ok=True)
    (cache / ".git" / "info" / "sparse-checkout").write_text("\n".join(SPARSE_PATHS) + "\n")
    run("git", "-C", str(cache), "checkout", "--quiet", MH_COMMIT)
    return data


# ── Base mesh ────────────────────────────────────────────────────────────────────
@dataclass
class BaseMesh:
    verts: np.ndarray                      # (N, 3) decimetres, MakeHuman axes (+Z = the body's front)
    uvs: np.ndarray                        # (T, 2)
    faces: list[tuple[str, list[int], list[int]]] = field(default_factory=list)   # (group, vertex ids, uv ids)

    def group_faces(self, name: str) -> list[list[int]]:
        return [f[1] for f in self.faces if f[0] == name]

    def group_verts(self, name: str) -> np.ndarray:
        return np.array(sorted({i for f in self.faces if f[0] == name for i in f[1]}), dtype=np.int64)


def load_obj(path: Path) -> BaseMesh:
    verts, uvs, faces, group = [], [], [], ""
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                verts.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                uvs.append([float(x) for x in line.split()[1:3]])
            elif line.startswith("g "):
                group = line.split()[1]
            elif line.startswith("f "):
                vi, ti = [], []
                for tok in line.split()[1:]:
                    parts = tok.split("/")
                    vi.append(int(parts[0]) - 1)
                    ti.append(int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1)
                faces.append((group, vi, ti))
    return BaseMesh(np.array(verts, dtype=np.float64), np.array(uvs, dtype=np.float64), faces)


# ── Targets (morphs) ─────────────────────────────────────────────────────────────
def load_target(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """A target is a sparse list of 'vertex dx dy dz' lines: which vertices move, and by how much."""
    idx, delta = [], []
    with open(path) as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split()
            idx.append(int(p[0]))
            delta.append([float(p[1]), float(p[2]), float(p[3])])
    return np.array(idx, dtype=np.int64), np.array(delta, dtype=np.float64).reshape(-1, 3)


def apply_targets(verts: np.ndarray, targets: list[tuple[Path, float]]) -> np.ndarray:
    out = verts.copy()
    for path, w in targets:
        if abs(w) < 1e-6:
            continue
        idx, delta = load_target(path)
        np.add.at(out, idx, delta * w)
    return out


@dataclass
class Macro:
    """MakeHuman's macro sliders. Ages are in years; everything else runs 0..1 (0.5 = average)."""
    gender: float = 1.0          # 0 female .. 1 male
    age_years: float = 25.0
    muscle: float = 0.5
    weight: float = 0.5
    height: float = 0.5
    proportions: float = 0.5     # 0 uncommon .. 0.5 regular .. 1 ideal
    african: float = 0.0
    asian: float = 0.0
    caucasian: float = 1.0


def macro_factors(m: Macro) -> dict[str, float]:
    """Per-value weights, as in MakeHuman's human.py (_setGenderVals, _setAgeVals, ...)."""
    f: dict[str, float] = {"male": m.gender, "female": 1.0 - m.gender}
    age = (m.age_years - 1.0) / ((25.0 - 1.0) * 2) if m.age_years < 25.0 else (m.age_years - 25.0) / ((90.0 - 25.0) * 2) + 0.5
    age = min(max(age, 0.0), 1.0)
    if age < 0.5:
        f["old"] = 0.0
        f["baby"] = max(0.0, 1 - age * 5.333)
        f["young"] = max(0.0, (age - 0.1875) * 3.2)
        f["child"] = max(0.0, min(1.0, 5.333 * age) - f["young"])
    else:
        f["child"] = f["baby"] = 0.0
        f["old"] = max(0.0, age * 2 - 1)
        f["young"] = 1 - f["old"]
    for name, v in (("muscle", m.muscle), ("weight", m.weight)):
        f["max" + name] = max(0.0, v * 2 - 1)
        f["min" + name] = max(0.0, 1 - v * 2)
        f["average" + name] = 1 - (f["max" + name] + f["min" + name])
    f["maxheight"] = max(0.0, m.height * 2 - 1)
    f["minheight"] = max(0.0, 1 - m.height * 2)
    f["idealproportions"] = max(0.0, m.proportions * 2 - 1)
    f["uncommonproportions"] = max(0.0, 1 - m.proportions * 2)
    total = m.african + m.asian + m.caucasian
    for race in ("african", "asian", "caucasian"):
        f[race] = getattr(m, race) / total if total > 0 else 1.0 / 3
    return f


def macro_targets(data: Path, m: Macro) -> list[tuple[Path, float]]:
    """Every macro target file with its weight: the product of the factors named in its file name."""
    f = macro_factors(m)
    out = []
    root = data / "targets" / "macrodetails"
    for path in sorted(root.rglob("*.target")):
        w = 1.0
        for part in path.stem.split("-"):
            if part in f:
                w *= f[part]
        if w > 1e-5:
            out.append((path, w))
    return out


# ── Skeleton and skin weights ────────────────────────────────────────────────────
@dataclass
class Skeleton:
    bones: dict        # name -> {"head": joint, "tail": joint, "parent": name|None}
    joints: dict       # joint name -> list of helper vertex ids (the joint sits at their mean)
    order: list        # bone names, parents before children

    def joint_pos(self, verts: np.ndarray, joint: str) -> np.ndarray:
        return verts[self.joints[joint]].mean(axis=0)

    def head(self, verts: np.ndarray, bone: str) -> np.ndarray:
        return self.joint_pos(verts, self.bones[bone]["head"])

    def tail(self, verts: np.ndarray, bone: str) -> np.ndarray:
        return self.joint_pos(verts, self.bones[bone]["tail"])

    def ancestors(self, bone: str):
        b = bone
        while b is not None:
            yield b
            b = self.bones[b]["parent"]


def load_skeleton(path: Path) -> Skeleton:
    s = json.loads(path.read_text())
    bones = s["bones"]
    order, seen = [], set()

    def visit(n):
        if n in seen:
            return
        p = bones[n]["parent"]
        if p:
            visit(p)
        seen.add(n)
        order.append(n)

    for n in bones:
        visit(n)
    return Skeleton(bones, s["joints"], order)


def load_weights(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    w = json.loads(path.read_text())["weights"]
    return {bone: (np.array([p[0] for p in pairs], dtype=np.int64), np.array([p[1] for p in pairs], dtype=np.float64))
            for bone, pairs in w.items()}
