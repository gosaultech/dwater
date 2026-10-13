# damned_waters/tools/photo/tests/test_camera_match.py
# Purpose: the camera matcher recovers a known camera. A synthetic room's edges are projected
# through a camera we chose; the matcher must find the same lens and the same way of looking from
# the vanishing points alone, and floor pixels must land back where they came from.
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import camera_match as cm  # noqa: E402


def rot(yaw_deg, pitch_deg):
    """World -> camera for a camera turned yaw east of north and pitched up (no roll)."""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    fw = np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])
    right = np.cross(fw, [0, 1, 0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fw)
    return np.vstack([right, -up, fw])   # rows: camera x (right), y (down), z (forward)


class Synthetic:
    def __init__(self, f=420.0, yaw=20.0, pitch=-6.0, size=(800, 600), eye=1.4):
        self.f, self.size, self.pos = f, size, np.array([0.0, eye, 0.0])
        self.c = np.array([size[0] / 2, size[1] / 2])
        self.R = rot(yaw, pitch)

    def px(self, X):
        P = self.R @ (np.asarray(X, float) - self.pos)
        return np.array([self.f * P[0] / P[2] + self.c[0], self.f * P[1] / P[2] + self.c[1]])

    def vp(self, d):
        q = self.R @ np.asarray(d, float)
        return np.array([self.f * q[0] + self.c[0] * q[2], self.f * q[1] + self.c[1] * q[2], q[2]])

    def segments(self):
        """A box room's edges, cut into pieces (as a line detector would find them)."""
        segs = []
        for x in np.linspace(-2.0, 3.0, 6):          # lines running north (the depth direction)
            for y in (0.0, 3.0):
                segs.append((x, y, -2.0, x, y, -7.0))
        for z in np.linspace(-2.5, -7.0, 6):         # lines running east
            for y in (0.0, 3.0):
                segs.append((-2.0, y, z, 3.0, y, z))
        for x in (-2.0, 0.0, 3.0):                   # verticals
            for z in (-3.0, -5.0, -7.0):
                segs.append((x, 0.2, z, x, 2.8, z))
        out = []
        for s in segs:
            a, b = self.px(s[:3]), self.px(s[3:])
            out.append([a[0], a[1], b[0], b[1]])
        return np.array(out)


class VanishingPointTests(unittest.TestCase):
    def test_three_directions_are_found(self):
        s = Synthetic()
        found = cm.find_vps(s.segments(), n=3, iters=600, max_deg=0.5)
        self.assertEqual(len(found), 3)
        truth = [s.vp(d) for d in ([0, 0, -1], [1, 0, 0], [0, 1, 0])]
        for t in truth:   # each true vanishing point matches one found (as directions from the centre)
            best = max(abs(float(cm.direction(v, s.c, s.f) @ cm.direction(t, s.c, s.f))) for v, _ in found)
            self.assertGreater(best, 0.9999)


class SolveTests(unittest.TestCase):
    def test_lens_and_angles_come_back(self):
        s = Synthetic(f=420.0, yaw=20.0, pitch=-6.0)
        cam = cm.solve({"north": s.vp([0, 0, -1]), "east": s.vp([1, 0, 0]), "up": s.vp([0, 1, 0])}, s.size)
        self.assertAlmostEqual(cam.f, 420.0, delta=0.5)
        yaw, pitch, roll = cam.yaw_pitch_roll()
        self.assertAlmostEqual(yaw, 20.0, delta=0.05)
        self.assertAlmostEqual(pitch, -6.0, delta=0.05)
        self.assertAlmostEqual(roll, 0.0, delta=0.05)

    def test_a_far_vanishing_point_does_not_spoil_the_lens(self):
        s = Synthetic(f=300.0, yaw=25.0, pitch=0.0)     # level: the verticals never meet
        up = np.array([s.c[0], 1e6, 1.0])               # as a detector reports nearly parallel lines
        cam = cm.solve({"north": s.vp([0, 0, -1]), "east": s.vp([1, 0, 0]), "up": up}, s.size)
        self.assertAlmostEqual(cam.f, 300.0, delta=0.5)

    def test_floor_pixels_land_where_they_came_from(self):
        s = Synthetic()
        cam = cm.solve({"north": s.vp([0, 0, -1]), "east": s.vp([1, 0, 0]), "up": s.vp([0, 1, 0])}, s.size)
        for X in ([1.0, 0.0, -4.0], [-1.5, 0.0, -6.0], [2.5, 0.0, -2.5]):
            xz = cm.place(cam, s.px(X), eye_height=1.4)
            self.assertAlmostEqual(xz[0], X[0], delta=0.01)
            self.assertAlmostEqual(xz[1], X[2], delta=0.01)

    def test_projection_round_trip(self):
        s = Synthetic()
        cam = cm.solve({"north": s.vp([0, 0, -1]), "east": s.vp([1, 0, 0]), "up": s.vp([0, 1, 0])}, s.size)
        X = np.array([[0.5, 2.0, -5.0]])
        np.testing.assert_allclose(cam.project(X, s.pos)[0], s.px(X[0]), atol=0.05)


if __name__ == "__main__":
    unittest.main()
