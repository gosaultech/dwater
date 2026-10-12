# damned_waters/tools/pipeline/tests/test_house.py
# Purpose: the set builder's floor plan agrees with the engine's (house.hpp): doorways pair across
# rooms placed at their origins, live doors are the ones the game swings, shared walls are found,
# and the real house (hall, parlour, cellar) fits together. And the room files themselves: every
# way on in the city is where its gap is, a model's collider lies the way the model does, every
# pickup can be reached, no two rooms on a storey overlap.
import json
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import house  # noqa: E402

ROOMS = HERE.parents[2] / "game" / "data" / "rooms"
MANIFEST = HERE.parents[2] / "tools" / "assets" / "manifest.json"
PLAYER_R, REACH = 0.28, 1.0   # the engine's: his body on the floor plane, how far he reaches for a thing


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

    def test_every_city_beat_stands_in_its_gap(self):   # a beat no opening owns never fires: the way on is a wall
        owned = {(d["a"], d["door_a"]) for d in house.doorways(self.specs)}
        for rid, s in self.specs.items():
            if s.get("storey", 0) < house.CITY:
                continue
            for it in s.get("interactables", []):
                if it.get("kind") == "door" and it.get("target_room"):
                    self.assertIn((rid, it["id"]), owned, f"{rid}/{it['id']}: not within {house.DOOR_REACH} m of an opening")

    def test_a_model_s_collider_lies_along_it(self):   # not an invisible wall across the quay beside a parked car
        sizes = {k: v["dimensions_mm"] for k, v in json.loads(MANIFEST.read_text())["assets"].items() if "dimensions_mm" in v}
        for rid, s in self.specs.items():
            for p in s.get("props", []):
                if p["type"] != "model" or p.get("collide", True) is False or "size" not in p or p.get("yaw_model", 0) % 180:
                    continue
                ref = p["model"][3:] if isinstance(p["model"], str) else p["model"]["ph"]
                mx, my, mz = sizes.get(ref, (1, 1, 1))   # along its x, its depth, its height
                if p.get("tip", 0) % 180:   # on its side: its height now lies along x
                    mx = mz
                sx, sz = p["size"][0], p["size"][2]
                if max(mx, my) > 1.3 * min(mx, my) and max(sx, sz) > 1.3 * min(sx, sz):
                    self.assertEqual(mx > my, sx > sz, f"{rid}: {ref} at {p['pos']}: its collider runs across it")

    def test_rooms_on_a_storey_never_overlap(self):   # two sets built in one place: walls through each other's floors
        def rect(s):
            ox, oz = s.get("origin", [0.0, 0.0])
            (x0, z0), (x1, z1) = s["bounds"]["min"], s["bounds"]["max"]
            return ox + x0, oz + z0, ox + x1, oz + z1
        ids = sorted(self.specs)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if self.specs[a].get("storey", 0) != self.specs[b].get("storey", 0):
                    continue
                A, B = rect(self.specs[a]), rect(self.specs[b])
                ox, oz = min(A[2], B[2]) - max(A[0], B[0]), min(A[3], B[3]) - max(A[1], B[1])
                self.assertFalse(ox > 0.01 and oz > 0.01, f"{a} and {b} overlap {ox:.2f} x {oz:.2f} m")

    def test_every_pickup_can_be_reached(self):   # somewhere to stand within reach of it, clear of every solid thing
        for rid, s in self.specs.items():
            boxes = [(p["pos"][0], p["pos"][2], p["size"][0] / 2, p["size"][2] / 2, math.radians(p.get("yaw", 0.0)))
                     for p in s.get("props", []) if p.get("collide", True) is not False and "size" in p]
            (x0, z0), (x1, z1) = s["bounds"]["min"], s["bounds"]["max"]

            def clear(x, z):
                if not (x0 + PLAYER_R <= x <= x1 - PLAYER_R and z0 + PLAYER_R <= z <= z1 - PLAYER_R):
                    return False
                for cx, cz, hx, hz, t in boxes:   # into each box's frame, as the engine's resolve_circle_obb
                    dx, dz = x - cx, z - cz
                    lx, lz = dx * math.cos(t) - dz * math.sin(t), dx * math.sin(t) + dz * math.cos(t)
                    if math.hypot(lx - max(-hx, min(hx, lx)), lz - max(-hz, min(hz, lz))) < PLAYER_R:
                        return False
                return True
            for it in s.get("interactables", []):
                if it.get("kind") != "pickup":
                    continue
                x, z = it["pos"][0], it["pos"][2]
                spots = [(x + REACH * a / 10 * math.cos(k * math.pi / 12), z + REACH * a / 10 * math.sin(k * math.pi / 12))
                         for a in range(10) for k in range(24)]
                self.assertTrue(any(clear(*q) for q in spots), f"{rid}/{it['id']}: nowhere to stand within reach of it")

    def test_peeks_are_shots(self):
        ids = [s["id"] for s in house.peek_shots(self.specs["voorkamer"])]
        self.assertEqual(ids, ["peek_door_gang"])


if __name__ == "__main__":
    unittest.main()
