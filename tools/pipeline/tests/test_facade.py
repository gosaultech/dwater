# damned_waters/tools/pipeline/tests/test_facade.py
# Purpose: unit tests for the canal-house front's arithmetic (tools/pipeline/facade.py): every
# gable is symmetric, inside the house's width and fillable as a fan; windows sit inside their
# storeys without overlapping; a wall cut around its holes covers exactly the rest.
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import facade  # noqa: E402


def area(rects):
    return sum((u1 - u0) * (v1 - v0) for u0, u1, v0, v1 in rects)


def overlaps(a, b):
    return min(a[1], b[1]) - max(a[0], b[0]) > 1e-9 and min(a[3], b[3]) - max(a[2], b[2]) > 1e-9


class GableTest(unittest.TestCase):
    def test_every_gable_is_symmetric_and_inside_the_width(self):
        for kind in facade.GABLES:
            for w in (5.0, 7.5, 9.7):
                poly = facade.gable_outline(kind, w, 3.6)
                self.assertEqual(poly[0], (-w / 2, 0.0), kind)
                self.assertEqual(poly[-1], (w / 2, 0.0), kind)
                for (u, v), (u2, v2) in zip(poly, reversed(poly)):
                    self.assertAlmostEqual(u, -u2, places=9, msg=kind)
                    self.assertAlmostEqual(v, v2, places=9, msg=kind)
                self.assertTrue(all(abs(u) <= w / 2 + 1e-9 and v >= 0 for u, v in poly), kind)

    def test_every_gable_fills_as_a_fan(self):
        for kind in facade.GABLES:
            for w in (5.0, 9.7):
                self.assertTrue(facade.is_star_shaped(facade.gable_outline(kind, w, 3.6), (0.0, 0.2)), kind)

    def test_gables_reach_their_height(self):
        for kind in ("neck", "bell", "step", "spout"):
            self.assertAlmostEqual(max(v for _, v in facade.gable_outline(kind, 7.0, 4.0)), 4.0, msg=kind)
        self.assertLess(max(v for _, v in facade.gable_outline("cornice", 7.0, 4.0)), 1.0)

    def test_unknown_gable_says_which_exist(self):
        with self.assertRaisesRegex(ValueError, "neck"):
            facade.gable_outline("onion", 6.0, 3.0)

    def test_a_dent_is_not_star_shaped(self):
        dent = [(-1, 0), (1, 0), (1, 1), (0.1, 1), (0.1, 0.1), (-0.1, 0.1), (-0.1, 1), (-1, 1)]
        self.assertFalse(facade.is_star_shaped(dent, (0.0, 0.05)))


class WindowTest(unittest.TestCase):
    def test_windows_sit_in_their_storeys_and_never_overlap(self):
        storeys = [3.8, 3.4, 3.1, 2.8]
        g = facade.window_grid(9.0, storeys, 3, door_bay=1)
        self.assertAlmostEqual(g["height"], sum(storeys))
        self.assertEqual(len(g["windows"]), 3 * 4 - 1)   # the door takes one ground-floor window
        for i, a in enumerate(g["windows"]):
            self.assertTrue(0 <= a[0] < a[1] <= 9.0)
            self.assertTrue(0 < a[2] < a[3] <= g["height"])
            for b in g["windows"][i + 1:]:
                self.assertFalse(overlaps(a, b))
            self.assertFalse(overlaps(a, g["door"]))
        u0, u1, v0, v1 = g["door"]
        self.assertAlmostEqual((u0 + u1) / 2, 4.5)
        self.assertEqual(v0, 0.0)

    def test_no_door_means_a_full_ground_floor(self):
        g = facade.window_grid(6.0, [3.5, 3.0], 2)
        self.assertIsNone(g["door"])
        self.assertEqual(len(g["windows"]), 4)


class CutTest(unittest.TestCase):
    def test_the_cut_wall_covers_all_but_the_holes(self):
        holes = [(1.0, 2.0, 0.8, 2.6), (3.0, 4.1, 0.0, 2.5), (1.0, 2.0, 3.5, 5.0), (5.5, 6.5, 1.0, 2.0)]
        rects = facade.cut_rects(8.0, 6.0, holes)
        self.assertAlmostEqual(area(rects), 8.0 * 6.0 - area(holes))
        for r in rects:
            for h in holes:
                self.assertFalse(overlaps(r, h))
        for i, a in enumerate(rects):
            for b in rects[i + 1:]:
                self.assertFalse(overlaps(a, b))

    def test_no_holes_is_one_piece(self):
        self.assertEqual(facade.cut_rects(4.0, 3.0, []), [(0.0, 4.0, 0.0, 3.0)])


if __name__ == "__main__":
    unittest.main()


class ShopTest(unittest.TestCase):
    def test_the_door_is_the_hole_between_two_posts(self):
        for W in (6.0, 8.95, 12.0):
            u0, u1, n, top_v = facade.shop_bays(W, 4.2)
            for bay in range(n):
                uc, width, height = facade.shop_door(W, 4.2, bay)
                left, right = u0 + (u1 - u0) * bay / n, u0 + (u1 - u0) * (bay + 1) / n   # the posts' centres
                self.assertAlmostEqual(uc - width / 2, left + 0.05, places=9)               # 5 cm half a post
                self.assertAlmostEqual(uc + width / 2, right - 0.05, places=9)
                self.assertAlmostEqual(height, top_v - 0.55, places=9)
                self.assertGreater(width, 1.0)   # wide enough to walk through

    def test_a_door_bay_past_the_end_is_the_last(self):
        n = facade.shop_bays(9.0, 4.2)[2]
        self.assertEqual(facade.shop_door(9.0, 4.2, 99), facade.shop_door(9.0, 4.2, n - 1))

    def test_along_the_wall_runs_from_each_front_s_left_hand_end(self):
        self.assertEqual(facade.along_wall({"facing": "south", "x0": 10.0, "x1": 19.0}, 2.0), 12.0)
        self.assertEqual(facade.along_wall({"facing": "north", "x0": 10.0, "x1": 19.0}, 2.0), 17.0)
        self.assertEqual(facade.along_wall({"facing": "east", "z0": 3.0, "z1": 12.0}, 2.0), 10.0)
        self.assertEqual(facade.along_wall({"facing": "west", "z0": 3.0, "z1": 12.0}, 2.0), 5.0)
