# damned_waters/tools/citygen/tests/test_cameras.py
# Purpose: the camera pass (cameras.py) films every spot of the wide rooms he can stand on, holds him
# big enough to read in every shot (the old wide shots held him at 5 to 10 percent of the picture),
# stands no camera in a tree, a lamp or a prop, uses the game's lenses, and plans the same shots
# from the same room every time. Reads the committed room files (build_city.py writes them).
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cameras  # noqa: E402

ROOMS = Path(__file__).resolve().parents[3] / "game" / "data" / "rooms"


def room(rid):
    return json.loads((ROOMS / f"{rid}.json").read_text())


class CameraPassTests(unittest.TestCase):
    def test_every_spot_he_can_reach_is_in_a_shot(self):
        for rid in cameras.ROOMS:
            spec = room(rid)
            xs, zs, mask = cameras.floor_grid(spec)
            X, Z = np.meshgrid(xs, zs, indexing="ij")
            covered = np.zeros_like(mask)
            for s in spec["shots"]:
                (a, b), (c, d) = s["zone"]["min"], s["zone"]["max"]
                covered |= (X >= a) & (X <= c) & (Z >= b) & (Z <= d)
            self.assertEqual(int((mask & ~covered).sum()), 0, rid)

    def test_he_stands_big_enough_in_every_shot(self):
        for rid in cameras.ROOMS:
            spec = room(rid)
            xs, zs, mask = cameras.floor_grid(spec)
            X, Z = np.meshgrid(xs, zs, indexing="ij")
            for s in spec["shots"]:
                (a, b), (c, d) = s["zone"]["min"], s["zone"]["max"]
                sel = mask & (X >= a) & (X <= c) & (Z >= b) & (Z <= d)
                fx, fz = X[sel], Z[sel]
                feet = np.stack([fx, np.full_like(fx, cameras.FEET), fz], axis=1)
                heads = np.stack([fx, np.full_like(fx, cameras.HEAD), fz], axis=1)
                cam = np.array(s["pos"], float)
                f = np.array(s["look_at"], float) - cam
                f /= np.linalg.norm(f)
                r = np.cross(f, [0.0, 1.0, 0.0])
                r /= np.linalg.norm(r)
                u = np.cross(r, f)
                th = math.tan(math.radians(s["fov"]) / 2)

                def proj(p):
                    v = p - cam
                    depth = v @ f
                    return (v @ r) / depth / (th * cameras.ASPECT), (v @ u) / depth / th

                (fxn, fyn), (_, hyn) = proj(feet), proj(heads)
                tall = (hyn - fyn) / 2
                with self.subTest(room=rid, shot=s["id"]):
                    self.assertGreaterEqual(float(np.quantile(tall, 0.05)), cameras.STANDARD["p05"] - 0.005)
                    self.assertGreaterEqual(float(np.median(tall)), cameras.STANDARD["floor"] - 0.02)   # (the old shots: 0.05 to 0.12)
                    self.assertLessEqual(float(np.abs(fxn).max()), 1.0)      # all of him in the picture, everywhere in the zone
                    self.assertGreaterEqual(float(fyn.min()), -1.0)
                    self.assertLessEqual(float(hyn.max()), 1.0)
                    lens = (cameras.HALL if cameras.ROOMS[rid].get("hall") else cameras.OUT)["lens"]
                    self.assertTrue(lens[0] - 0.1 <= s["fov"] <= lens[1] + 0.1)

    def test_no_camera_stands_in_anything(self):
        for rid in cameras.ROOMS:
            spec = room(rid)
            circles, boxes, things = cameras._avoid(spec, cameras.HALL if cameras.ROOMS[rid].get("hall") else cameras.OUT)
            for s in spec["shots"]:
                x, y, z = s["pos"]
                with self.subTest(room=rid, shot=s["id"]):
                    for b in boxes:
                        if b[6] > y - 0.6:
                            self.assertFalse(bool(cameras._in_box(np.array(x), np.array(z), b, 0.45)), b[7])
                    for b, grow in things:
                        if b[5] - 1.0 < y < b[6] + 2.0:
                            self.assertFalse(bool(cameras._in_box(np.array(x), np.array(z), b, grow - 0.05)), b[7])
                    for cx, cz, rad, below in circles:
                        if y > below:
                            self.assertGreater(math.hypot(x - cx, z - cz), rad - 0.05)
                    self.assertLess(y, spec.get("height", 3.0))

    def test_the_same_room_gets_the_same_shots(self):
        for rid in ("rokin_zuid", "apotheek"):
            spec = room(rid)
            before = json.dumps(spec["shots"])
            cameras.apply(spec)
            self.assertEqual(json.dumps(spec["shots"]), before, rid)


if __name__ == "__main__":
    unittest.main()
