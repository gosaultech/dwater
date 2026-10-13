# damned_waters/tools/citygen/tests/test_dress.py
# Purpose: the dressers keep to their rules: a shop gets its ceiling and exit signs, nothing lands in
# a doorway or on a spawn, and dressing a street twice adds nothing the second time.
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aftermath13  # noqa: E402
import common  # noqa: E402


def shop(rid="drogist"):
    return {"id": rid, "bounds": {"min": [0.0, 0.0], "max": [9.0, 8.0]}, "height": 3.4, "materials": {},
            "walls": {"east": {"facade": True, "openings": [{"kind": "door", "center": 4.0, "width": 1.5, "height": 2.25}]},
                      "north": {"openings": [{"kind": "passage", "center": 2.0, "width": 1.2, "height": 2.2}]}},
            "lights": [{"kind": "area", "pos": [4.5, 3.39, 4.0], "size": 0.8, "color": [1, 1, 1]}],
            "props": [], "spawns": {"in": {"pos": [8.0, 0.0, 4.0]}}, "interactables": [], "enemies": []}


def street():
    return {"id": "straat", "bounds": {"min": [0.0, 0.0], "max": [8.0, 60.0]}, "height": 10.0,
            "outdoor": {"lamps": [[0.6, 12.0]], "facades": [{"facing": "east", "x": 0.0, "z0": 0.0, "z1": 60.0, "bays": 3, "door_bay": 1},
                                                            {"facing": "west", "x": 8.0, "z0": 0.0, "z1": 60.0, "shop": {"name": "X"}}]},
            "walls": {"east": {"openings": [{"kind": "door", "center": 30.0, "width": 1.5, "height": 2.25}]}},
            "props": [], "spawns": {"from_noord": {"pos": [4.0, 0.0, 1.2]}},
            "interactables": [{"id": "door_x", "kind": "door", "pos": [7.55, 1.0, 30.0]}], "enemies": []}


class DressTests(unittest.TestCase):
    def test_a_shop_gets_a_ceiling_and_a_sign_over_each_way_out(self):
        s = shop()
        common.finish_indoors(s)
        types = [p["type"] for p in s["props"]]
        self.assertEqual(types.count("drop_ceiling"), 1)
        self.assertEqual(types.count("exit_sign"), 2)
        self.assertTrue(all(L["pos"][1] < s["height"] - 0.05 for L in s["lights"]), "a light left above the tiles")

    def test_nothing_is_put_down_in_a_doorway(self):
        s = shop()
        common.finish_indoors(s)
        for p in s["props"]:
            if p["type"] == "model" and p["pos"][1] < 0.5:
                self.assertGreater(math.hypot(p["pos"][0] - 9.0, p["pos"][2] - 4.0), 1.0, p)

    def test_a_church_is_left_alone(self):
        s = shop("nieuwe_kerk")
        common.finish_indoors(s)
        self.assertNotIn("drop_ceiling", [p["type"] for p in s["props"]])

    def test_street_junk_keeps_off_doors_spawns_and_lamps(self):
        s = street()
        common.dress_street(s)
        junk = [p for p in s["props"] if p.get("junk")]
        self.assertGreater(len(junk), 5)
        for p in junk:
            x, z = p["pos"][0], p["pos"][2]
            self.assertGreater(math.hypot(x - 7.55, z - 30.0), 1.5, p)
            self.assertGreater(math.hypot(x - 4.0, z - 1.2), 1.5, p)
            self.assertGreater(math.hypot(x - 0.6, z - 12.0), 0.6, p)

    def test_dressing_a_street_twice_adds_nothing(self):
        s = street()
        common.dress_street(s)
        once = copy.deepcopy(s)
        common.dress_street(s)
        self.assertEqual(s, once)

    def test_a_street_s_story_is_put_down_once(self):
        s = {"id": "reguliersbreestraat", "props": [], "outdoor": {"facades": [
            {"facing": "south", "x0": 34.05, "x1": 44.0, "shop": {"name": "X"}}]}}
        aftermath13.apply(s)
        once = copy.deepcopy(s)
        aftermath13.apply(s)
        self.assertEqual(s, once)
        self.assertTrue(all(p["after"] for p in s["props"]))
        self.assertEqual(s["outdoor"]["facades"][0]["shop"]["smashed"], [1])
        self.assertTrue(all(p.get("collide") is False for p in s["props"] if p["type"] in ("luggage", "leaflets")))


if __name__ == "__main__":
    unittest.main()
