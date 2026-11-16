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


class OccluderTests(unittest.TestCase):
    """What hides him is judged by its shape: a tent by its roof, the monument by its pillar, lions and wall."""

    def test_a_tent_hides_him_only_by_its_roof(self):
        tent = (0.0, 0.0, 3.0, 3.0, 0.0, 0.0, 3.4, "aid_post")
        boxes = cameras._occluders(tent)
        under = np.array([[0.0, 1.45, 0.0]])   # his chest and head, under the middle of it
        self.assertFalse(cameras._segment_hits(np.array([0.0, 1.7, 9.0]), under, boxes)[0])   # seen from low, outside
        self.assertTrue(cameras._segment_hits(np.array([0.0, 9.0, 1.0]), under, boxes)[0])    # not through the roof

    def test_the_monument_hides_him_by_its_pillar_not_its_steps(self):
        mon = (0.0, 0.0, 8.0, 8.0, 0.0, 0.0, 22.0, "monument")
        boxes = cameras._occluders(mon)
        cam = np.array([0.0, 3.0, 14.0])   # in front of it (the wall is behind, at -z)
        on_steps = np.array([[5.0, 1.45, 5.0]])
        behind = np.array([[0.0, 1.45, -4.0]])
        self.assertFalse(cameras._segment_hits(cam, on_steps, boxes)[0])
        self.assertTrue(cameras._segment_hits(cam, behind, boxes)[0])
        beyond_wall = np.array([[0.0, 1.45, -11.0]])
        self.assertTrue(cameras._segment_hits(np.array([0.0, 1.7, -6.0]), beyond_wall, boxes)[0])   # the curved wall

    def test_a_garland_hides_nothing_below_its_lights(self):
        garland = (4.0, 20.0, 4.0, 0.05, 0.0, 0.0, 6.4, "garland")   # 8 m across the street, hung at 6.4 m
        beyond = np.array([[4.0, 1.45, 14.0]])
        self.assertFalse(cameras._segment_hits(np.array([4.0, 3.5, 26.0]), beyond, cameras._occluders(garland))[0])

    def test_a_flower_stall_stands_behind_its_spot(self):
        stall = (0.0, 0.0, 3.5, 2.25, 0.0, 0.0, 4.0, "flower_stall")   # its open front on its spot, facing +z
        on_quay = np.array([[0.0, 1.45, 1.0]])
        self.assertFalse(cameras._segment_hits(np.array([-8.0, 2.5, 1.5]), on_quay, cameras._occluders(stall))[0])
        inside = np.array([[0.0, 1.45, -2.0]])
        self.assertTrue(cameras._segment_hits(np.array([-8.0, 2.5, -2.0]), inside, cameras._occluders(stall))[0])


if __name__ == "__main__":
    unittest.main()
