# damned_waters/tools/photo/camera_match.py
# Purpose: find the camera that took a photo, so a Blender set (and the engine's fixed shot) can be
# framed exactly like it. Straight edges in the photo (beams, window frames, skirting boards) are
# found, grouped by the vanishing point they run to, and the three vanishing points of a room's
# three directions give the lens (focal length) and which way the camera points.
#
# ELI5: stand on a long straight road and the kerbs meet at one point on the horizon. Where that
# point sits in the picture says which way you were looking; how far apart two such points are
# (for two roads at right angles) says how wide your lens was.
#
#   python3 tools/photo/camera_match.py photo.jpg --overlay out.png   # lines coloured by direction
#
# Conventions: pixels x right, y down; camera coordinates x right, y down, z forward (OpenCV).
# World (RoomSpec/Godot) axes: X east, Y up, Z south (north = -Z): the depth direction of the photo
# is north, the image's right is east.
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import numpy as np


# ── Lines and vanishing points (pure numpy) ──────────────────────────────────────
def line_of(seg: np.ndarray) -> np.ndarray:
    """Homogeneous line through a segment (x1, y1, x2, y2), scaled so (a, b) is a unit normal."""
    p = np.array([seg[0], seg[1], 1.0])
    q = np.array([seg[2], seg[3], 1.0])
    l = np.cross(p, q)
    return l / (np.hypot(l[0], l[1]) + 1e-12)


def agrees(seg: np.ndarray, vp: np.ndarray, max_deg: float) -> bool:
    """Does the segment point at the vanishing point (finite or at infinity) within max_deg?"""
    mid = np.array([(seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2])
    d_seg = np.array([seg[2] - seg[0], seg[3] - seg[1]])
    if abs(vp[2]) < 1e-9:
        d_vp = vp[:2]
    else:
        d_vp = vp[:2] / vp[2] - mid
    n1, n2 = np.linalg.norm(d_seg), np.linalg.norm(d_vp)
    if n1 < 1e-9 or n2 < 1e-9:
        return False
    c = abs(float(d_seg @ d_vp)) / (n1 * n2)
    return c >= math.cos(math.radians(max_deg))


def refine_vp(segs: np.ndarray) -> np.ndarray:
    """The point closest to all the segments' lines (least squares, weighted by length); unit
    homogeneous vector, so a point at infinity (parallel lines) comes out with w ~ 0."""
    m = np.zeros((3, 3))
    for s in segs:
        l = line_of(s)
        w = math.hypot(s[2] - s[0], s[3] - s[1])
        m += w * np.outer(l, l)
    _, vecs = np.linalg.eigh(m)
    v = vecs[:, 0]
    return v / np.linalg.norm(v)


def find_vps(segs: np.ndarray, n: int = 3, iters: int = 3000, max_deg: float = 1.5, seed: int = 0):
    """RANSAC: the n vanishing points most of the (long) edges run to, strongest first.
    Returns [(vp, inlier_segments)]."""
    rng = np.random.default_rng(seed)
    left = segs.copy()
    found = []
    for _ in range(n):
        if len(left) < 2:
            break
        lengths = np.hypot(left[:, 2] - left[:, 0], left[:, 3] - left[:, 1])
        prob = lengths / lengths.sum()
        best, best_score = None, -1.0
        for _ in range(iters):
            i, j = rng.choice(len(left), 2, replace=False, p=prob)
            vp = np.cross(line_of(left[i]), line_of(left[j]))
            if np.linalg.norm(vp) < 1e-12:
                continue
            vp = vp / np.linalg.norm(vp)
            mask = np.array([agrees(s, vp, max_deg) for s in left])
            score = float(lengths[mask].sum())
            if score > best_score:
                best, best_score = mask, score
        inl = left[best]
        found.append((refine_vp(inl), inl))
        left = left[~best]
    return found


# ── The camera from vanishing points ─────────────────────────────────────────────
def focal_from(v1: np.ndarray, v2: np.ndarray, c: np.ndarray) -> float:
    """Focal length (pixels) from the vanishing points of two directions at right angles, with the
    principal point c: (v1 - c).(v2 - c) = -f^2. NaN if they can't be at right angles."""
    a, b = v1[:2] / v1[2] - c, v2[:2] / v2[2] - c
    d = -float(a @ b)
    return math.sqrt(d) if d > 0 else float("nan")


def direction(vp: np.ndarray, c: np.ndarray, f: float) -> np.ndarray:
    """The 3D direction (camera coordinates) whose vanishing point is vp."""
    if abs(vp[2]) < 1e-9:
        d = np.array([vp[0], vp[1], 0.0])
    else:
        d = np.array([vp[0] / vp[2] - c[0], vp[1] / vp[2] - c[1], f])
    return d / np.linalg.norm(d)


@dataclass
class Camera:
    f: float                 # focal length, pixels
    c: np.ndarray            # principal point, pixels
    R: np.ndarray            # world -> camera rotation (columns: east, up, south in camera coords)
    size: tuple              # image (width, height)

    @property
    def forward(self) -> np.ndarray:   # where it looks, in world coordinates
        return self.R.T @ np.array([0.0, 0.0, 1.0])

    @property
    def up(self) -> np.ndarray:
        return self.R.T @ np.array([0.0, -1.0, 0.0])

    def vfov_deg(self, height: float | None = None) -> float:
        h = self.size[1] if height is None else height
        return math.degrees(2 * math.atan(h / 2 / self.f))

    def yaw_pitch_roll(self) -> tuple:
        """Degrees: yaw east of north, pitch up from level, roll clockwise as seen."""
        fw, up = self.forward, self.up
        yaw = math.degrees(math.atan2(fw[0], -fw[2]))
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, fw[1]))))
        right = np.cross(fw, np.array([0.0, 1.0, 0.0]))
        right /= np.linalg.norm(right)
        level_up = np.cross(right, fw)
        roll = math.degrees(math.atan2(float(np.cross(level_up, up) @ fw), float(level_up @ up)))
        return yaw, pitch, roll

    def project(self, X: np.ndarray, pos: np.ndarray) -> np.ndarray:
        """World point(s) -> pixels, for a camera standing at pos."""
        P = (self.R @ (np.atleast_2d(X) - pos).T).T
        return np.column_stack([self.f * P[:, 0] / P[:, 2] + self.c[0], self.f * P[:, 1] / P[:, 2] + self.c[1]])

    def ray(self, px: np.ndarray) -> np.ndarray:
        """The world direction through a pixel."""
        d = np.array([px[0] - self.c[0], px[1] - self.c[1], self.f])
        d = self.R.T @ d
        return d / np.linalg.norm(d)


def orthonormal(m: np.ndarray) -> np.ndarray:
    u, _, vt = np.linalg.svd(m)
    r = u @ vt
    if np.linalg.det(r) < 0:
        u[:, -1] *= -1
        r = u @ vt
    return r


def solve(vps: dict, size: tuple, f: float | None = None) -> Camera:
    """vps: {'north': vp, 'east': vp, 'up': vp} (any two are enough; a third refines). The principal
    point is the image centre. f: a known focal length (pixels), else from two finite VPs."""
    c = np.array([size[0] / 2.0, size[1] / 2.0])
    if f is None:
        # Only vanishing points within reach of the picture fix the lens: one far off (lines that
        # are nearly parallel in the photo) says almost nothing about it.
        reach = 8.0 * max(size)
        def near(vp):
            return abs(vp[2]) > 1e-9 and np.linalg.norm(vp[:2] / vp[2] - c) < reach
        cands = []
        names = [k for k in vps if near(vps[k])]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                fi = focal_from(vps[names[i]], vps[names[j]], c)
                if not math.isnan(fi):
                    cands.append(fi)
        if not cands:
            raise ValueError("need two finite vanishing points at right angles (or pass f)")
        f = float(np.median(cands))
    dirs = {}
    for k, vp in vps.items():
        d = direction(vp, c, f)
        if k == "north" and d[2] < 0:
            d = -d                       # the depth direction lies ahead
        if k == "east" and d[0] < 0:
            d = -d                       # east is to the right
        if k == "up" and d[1] > 0:
            d = -d                       # up is up the picture (pixels y down)
        dirs[k] = d
    if "up" not in dirs:
        dirs["up"] = np.cross(dirs["north"], dirs["east"]) * -1.0
    if "east" not in dirs:
        dirs["east"] = np.cross(dirs["north"], dirs["up"])
    if "north" not in dirs:
        dirs["north"] = np.cross(dirs["up"], dirs["east"])
    R = orthonormal(np.column_stack([dirs["east"], dirs["up"], -dirs["north"]]))
    return Camera(f, c, R, size)


def place(cam: Camera, floor_px: np.ndarray, eye_height: float) -> np.ndarray:
    """Where a pixel on the floor lies (world x, z), for a camera eye_height above the floor at
    (0, eye_height, 0)."""
    d = cam.ray(floor_px)
    if d[1] >= 0:
        raise ValueError("that pixel is above the horizon")
    t = eye_height / -d[1]
    return np.array([d[0] * t, d[2] * t])


# ── Detection (OpenCV) and the overlay ───────────────────────────────────────────
def detect_segments(img_gray: np.ndarray, min_len: float = 25.0) -> np.ndarray:
    import cv2
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    lines = lsd.detect(img_gray)[0]
    if lines is None:
        return np.zeros((0, 4))
    s = lines.reshape(-1, 4).astype(float)
    keep = np.hypot(s[:, 2] - s[:, 0], s[:, 3] - s[:, 1]) >= min_len
    return s[keep]


def main():
    import cv2
    ap = argparse.ArgumentParser(description="Match a camera to a photo of a room.")
    ap.add_argument("photo")
    ap.add_argument("--overlay", default="")
    ap.add_argument("--scale", type=float, default=2.0, help="upscale before detecting (small photos)")
    a = ap.parse_args()
    img = cv2.imread(a.photo)
    big = cv2.resize(img, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_CUBIC)
    segs = detect_segments(cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)) / a.scale
    found = find_vps(segs)
    h, w = img.shape[:2]
    for k, (vp, inl) in enumerate(found):
        where = "infinity" if abs(vp[2]) < 1e-6 else f"({vp[0] / vp[2]:.0f}, {vp[1] / vp[2]:.0f})"
        print(f"vp{k}: {where}  {len(inl)} edges")
    if a.overlay:
        colours = [(40, 40, 230), (40, 200, 40), (230, 120, 30)]
        out = big.copy()
        for k, (_, inl) in enumerate(found):
            for s in inl * a.scale:
                cv2.line(out, (int(s[0]), int(s[1])), (int(s[2]), int(s[3])), colours[k % 3], 2)
        cv2.imwrite(a.overlay, out)
    print(f"image {w}x{h}")


if __name__ == "__main__":
    main()
