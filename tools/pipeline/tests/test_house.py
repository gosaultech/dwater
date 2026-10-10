# damned_waters/tools/pipeline/tests/test_house.py
# Purpose: the set builder's floor plan agrees with the engine's (house.hpp): doorways pair across
# rooms placed at their origins, live doors are the ones the game swings, shared walls are found,
# and the real house (hall, parlour, cellar) fits together.
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import house  # noqa: E402

ROOMS = HERE.parents[2] / "game" / "data" / "rooms"


def room(rid, origin, size, walls, interactables=(), storey=0):
    return {"id": rid, "origin": list(origin), "storey": storey, "bounds": {"min": [0, 0], "max": list(size)},
            "walls": walls, "interactables": list(interactables)}


def three():
    hall = room("hall", (0, 0), (2, 6), {"west": {"openings": [{"kind": "door", "center": 4.0, "width": 0.9}]},
                                         "south": {"openings": [{"kind": "door", "center": 1.0, "width": 1.0}]}},
                [{"id": "to_parlour", "kind": "door", "pos": [0.15, 1, 4.0], "target_room": "parlour"},
                 {"id": "front", "kind": "examine", "pos": [1, 1, 5.8]}])
    parlour = room("parlour", (-4.3, 1.0), (4, 5), {"east": {"openings": [{"kind": "door", "center": 3.0, "width": 0.9}]}},
                   [{"id": "to_hall", "kind": "door", "pos": [3.85, 1, 3.0], "target_room": "hall"}])
    cellar = room("cellar", (0, 0), (2, 6), {"north": {"openings": [{"kind": "door", "center": 1.0, "width": 0.8}]}},
                  storey=-1)
    return {"hall": hall, "parlour": parlour, "cellar": cellar}


class DoorwayTests(unittest.TestCase):
    def test_paired_and_live(self):
        ds = house.doorways(three())
        pair = [d for d in ds if d["b"]]
        self.assertEqual(len(pair), 1)
        self.assertEqual({pair[0]["a"], pair[0]["b"]}, {"hall", "parlour"})
        self.assertTrue(pair[0]["live"])
        ax, az, bx, bz = pair[0]["ends"]
        self.assertAlmostEqual((ax + bx) / 2, -0.15)
        self.assertAlmostEqual((az + bz) / 2, 4.0)

    def test_front_door_stays_painted(self):
        ds = house.doorways(three())
        front = [d for d in ds if d["a"] == "hall" and d["side_a"] == "south"][0]
        self.assertFalse(front["live"])
        self.assertEqual(house.live_openings(three(), "hall"), {("west", 0)})

    def test_storeys_do_not_pair(self):
        self.assertEqual(house.live_openings(three(), "cellar"), set())   # a door with no door behind it

    def test_shared_walls(self):
        s = three()
        self.assertEqual(house.shared_sides(s, "hall"), {"west"})
        self.assertEqual(house.shared_sides(s, "parlour"), {"east"})
        self.assertEqual(house.shared_sides(s, "cellar"), set())


class RealHouseTests(unittest.TestCase):
    def setUp(self):
        self.specs = {p.stem: json.loads(p.read_text()) for p in ROOMS.glob("*.json")}

    def test_hall_and_parlour_share_a_door(self):
        ds = house.doorways(self.specs)
        self.assertTrue(any({d["a"], d["b"]} == {"gang", "voorkamer"} and d["live"] for d in ds))
        self.assertIn("west", house.shared_sides(self.specs, "gang"))
        self.assertIn("east", house.shared_sides(self.specs, "voorkamer"))

    def test_the_cellar_door_leads_down_stairs(self):
        self.assertIn(("north", 0), house.stair_openings(self.specs, "gang"))

    def test_facade_is_flush(self):   # the canal front of the hall and the parlour is one plane
        g, v = house.house_bounds(self.specs["gang"]), house.house_bounds(self.specs["voorkamer"])
        self.assertAlmostEqual(g[3], v[3])

    def test_peeks_are_shots(self):
        ids = [s["id"] for s in house.peek_shots(self.specs["voorkamer"])]
        self.assertEqual(ids, ["peek_door_gang"])


if __name__ == "__main__":
    unittest.main()
