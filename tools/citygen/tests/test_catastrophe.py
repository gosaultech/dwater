# damned_waters/tools/citygen/tests/test_catastrophe.py
# Purpose: the catastrophe pass (catastrophe.py) tells each street's story without getting in his
# way: the derailed tram stays off the lanes he walks, the big debris too, everything stands on open
# floor, nothing by a lens hides him from any shot; it runs twice to the same street and leaves the
# streets with no story yet alone; every decal it names is the one decals.py will draw.
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets"))
import barricades  # noqa: E402
import cameras  # noqa: E402
import catastrophe  # noqa: E402
import decals  # noqa: E402

ROOMS = Path(__file__).resolve().parents[3] / "game" / "data" / "rooms"
FX = {"fire", "smoke", "sparks", "strobe", "flicker"}


def room(rid):
    return json.loads((ROOMS / f"{rid}.json").read_text())


def in_lane(x, z, rid, grow=0.0):
    return any(x0 - grow < x < x1 + grow and z0 - grow < z < z1 + grow for x0, z0, x1, z1 in barricades.LANES.get(rid, []))


class Catastrophe(unittest.TestCase):
    def test_it_runs_twice_to_the_same_street_and_leaves_the_others(self):
        for rid in catastrophe.STORIES:
            spec = room(rid)
            again = catastrophe.foreground(cameras.apply(catastrophe.leavings(barricades.apply(catastrophe.apply(copy.deepcopy(spec))))))
            self.assertEqual(json.dumps(spec, sort_keys=True), json.dumps(again, sort_keys=True), rid)
        other = room("muntplein")
        self.assertEqual(json.dumps(catastrophe.apply(copy.deepcopy(other)), sort_keys=True), json.dumps(other, sort_keys=True))
        self.assertNotIn("fx", other)

    def test_the_derailed_tram_stays_off_the_lanes(self):
        spec = room("rokin_zuid")
        tram = next(p for p in spec["props"] if p["type"] == "tram")
        self.assertFalse(tram.get("collide", True))   # (its sections stand in for it)
        secs = catastrophe.tram_sections(tram)
        self.assertEqual(len(secs), 3)
        self.assertAlmostEqual(secs[0][0], tram["pos"][0], places=3)   # the back still on the rails
        for x, z, yaw, seg in secs[1:]:   # (the back section is where the tram always stood)
            a = math.radians(yaw)
            for sx in (-0.5, 0.5):
                for sz in (-0.5, 0.5):
                    cx = x + sx * seg * math.cos(a) + sz * 2.4 * math.sin(a)
                    cz = z - sx * seg * math.sin(a) + sz * 2.4 * math.cos(a)
                    self.assertFalse(in_lane(cx, cz, "rokin_zuid", grow=-0.05), (x, z, cx, cz))
        sections = [p for p in spec["props"] if p["type"] == "tram_section" and p.get("catastrophe")]
        self.assertEqual(len(sections), 3)
        self.assertTrue(all(p.get("collide", True) for p in sections))

    def test_debris_lies_on_open_floor_and_the_big_pieces_off_the_lanes(self):
        big = {ref for ref, _, b in catastrophe.DEBRIS if b}
        for rid in catastrophe.STORIES:
            spec = room(rid)
            xs, zs, ok = cameras.open_floor({**spec, "props": [p for p in spec["props"] if not p.get("catastrophe")]})
            x0, z0 = xs[0], zs[0]
            n = 0
            for p in spec["props"]:
                if not p.get("catastrophe") or p["type"] != "model" or p["pos"][1] < -0.5:   # (what floats in the basin)
                    continue
                x, _, z = p["pos"]
                i = min(max(int(round((x - x0) / cameras.CELL)), 0), len(xs) - 1)
                k = min(max(int(round((z - z0) / cameras.CELL)), 0), len(zs) - 1)
                if p.get("model") in big and p.get("catastrophe_fg") is None:
                    self.assertFalse(in_lane(x, z, rid, grow=-0.1), (rid, p))
                n += 1
            self.assertGreater(n, 80, rid)

    def test_nothing_by_a_lens_hides_him(self):
        for rid in catastrophe.STORIES:
            spec = room(rid)
            fg = [p for p in spec["props"] if p.get("catastrophe_fg")]
            for p in fg:
                self.assertFalse(in_lane(p["pos"][0], p["pos"][2], rid), p)
            box = [(p["pos"][0], p["pos"][2], 0.45, 0.45, 0.0, 0.0, 1.0, "fg") for p in fg]
            fx_, fz_, floor = cameras.floor_grid(spec)
            FX, FZ = np.meshgrid(fx_, fz_, indexing="ij")
            for s in spec["shots"]:
                (a, b), (c, d) = s["zone"]["min"], s["zone"]["max"]
                sel = floor & (FX >= a) & (FX <= c) & (FZ >= b) & (FZ <= d)
                pts = np.stack([FX[sel], np.full(sel.sum(), 1.45), FZ[sel]], axis=1)
                if len(pts) and box:
                    self.assertLessEqual(cameras._segment_hits(np.array(s["pos"], float), pts, box).mean(), 0.02, (rid, s["id"]))

    def test_the_dead_lie_in_the_street_not_in_a_wall(self):
        for rid in catastrophe.STORIES:
            spec = room(rid)
            self.assertTrue(spec.get("dead"), rid)
            xs, zs, ok = cameras.open_floor(spec)
            (bx0, bz0), (bx1, bz1) = spec["bounds"]["min"], spec["bounds"]["max"]
            for b in spec["dead"]:
                x, y, z = b["pos"]
                if y < -0.5:   # (afloat: over the water, west of the quay)
                    self.assertLess(x, bx0 + 0.5, b)
                    continue
                self.assertTrue(bx0 < x < bx1 and bz0 < z < bz1, b)
                i = int(np.argmin(np.abs(xs - x)))
                k = int(np.argmin(np.abs(zs - z)))
                self.assertTrue(ok[max(i - 1, 0):i + 2, max(k - 1, 0):k + 2].any(), (rid, b))

    def test_its_decals_and_its_fx_are_ones_the_tools_know(self):
        for rid in catastrophe.STORIES:
            spec = room(rid)
            for p in spec["props"]:
                if "decal" in p:
                    self.assertEqual(p["decal"]["id"], decals.decal_id(p["decal"]))
                    self.assertIn(p["decal"]["style"], decals.STYLES)
            kinds = [f["kind"] for f in spec.get("fx", [])]
            self.assertTrue(kinds)
            self.assertTrue(set(kinds) <= FX, kinds)


if __name__ == "__main__":
    unittest.main()
