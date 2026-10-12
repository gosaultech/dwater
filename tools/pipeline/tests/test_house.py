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

    def test_streets_meet_at_a_passage(self):   # an open way between two street sets: one doorway, live
        quay = dict(room("quay", (0, 0), (20, 8), {"east": {"openings": [{"kind": "passage", "center": 4.0, "width": 6.0}]}}), outdoor=True)
        square = dict(room("square", (20.3, -2), (30, 12), {"west": {"openings": [{"kind": "passage", "center": 6.0, "width": 6.0}]}}),
                      outdoor=True)
        ds = house.doorways({"quay": quay, "square": square})
        self.assertEqual(len(ds), 1)
        self.assertTrue(ds[0]["live"] and ds[0]["passage"])
        self.assertEqual((ds[0]["a"], ds[0]["b"]), ("quay", "square"))

    def test_a_street_shares_no_walls(self):   # the street outside the front: the house keeps its whole wall
        specs = three()
        specs["street"] = dict(room("street", (-4.3, 6.3), (8, 6), {}), outdoor=True)
        self.assertNotIn("south", house.shared_sides(specs, "hall"))
        self.assertEqual(house.shared_sides(specs, "street"), set())

    def test_the_next_district_s_streets_are_seen(self):   # built for the picture, only if near enough
        specs = {"square": dict(room("square", (0, 0), (40, 30), {}, storey=10), outdoor=True),
                 "shop": room("shop", (-10, 0), (10, 8), {}, storey=10),
                 "street": dict(room("street", (-70, 0), (70, 10), {}, storey=11), outdoor=True),
                 "far": dict(room("far", (500, 0), (20, 20), {}, storey=12), outdoor=True),
                 "lobby": room("lobby", (-40, 10), (12, 12), {}, storey=11),
                 "hall": room("hall", (0, 0), (2, 6), {})}
        self.assertEqual(house.neighbour_streets(specs, "square"), ["street"])   # not its shops, not the far one
        self.assertEqual(house.neighbour_streets(specs, "lobby"), ["square"])
        self.assertEqual(house.neighbour_streets(specs, "hall"), [])             # the house sees no districts

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
