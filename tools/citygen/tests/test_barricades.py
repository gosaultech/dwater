# damned_waters/tools/citygen/tests/test_barricades.py
# Purpose: the cordons (barricades.py) leave every door, spawn, item, note and Drowned of a room on
# one walkable network, let nobody walk outside the lanes, line up across the seamless passages
# between rooms, and run twice to the same room.
import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import barricades  # noqa: E402
import cameras  # noqa: E402

ROOMS = Path(__file__).resolve().parents[3] / "game" / "data" / "rooms"
REACH = 1.0   # m: how near he must get to a thing to use it (or to a Drowned's spot for it to reach him)


def room(rid):
    spec = json.loads((ROOMS / f"{rid}.json").read_text())
    return barricades.apply(spec)


def reachable(spec, seed):
    xs, zs, m = cameras.floor_grid(spec, [seed])
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    return X[m], Z[m]


class CordonTests(unittest.TestCase):
    def test_runs_twice_to_the_same_room(self):
        for rid in barricades.LANES:
            a = room(rid)
            b = barricades.apply(copy.deepcopy(a))
            self.assertEqual(a, b, rid)

    def test_everything_is_on_one_walkable_network(self):
        for rid in barricades.LANES:
            spec = room(rid)
            first = next(iter(spec["spawns"].values()))["pos"]
            fx, fz = reachable(spec, first)
            things = [("spawn " + k, s["pos"]) for k, s in spec["spawns"].items()]
            things += [(f"{i['kind']} {i['id']}", i["pos"]) for i in spec.get("interactables", [])]
            things += [("enemy " + e["id"], e["pos"]) for e in spec.get("enemies", [])]
            for what, (x, _, z) in things:
                with self.subTest(room=rid, thing=what):
                    self.assertLess(float(np.min(np.hypot(fx - x, fz - z))), REACH)

    def test_nobody_walks_outside_the_lanes(self):
        for rid in barricades.LANES:
            spec = room(rid)
            xs, zs, m = cameras.floor_grid(spec)
            X, Z = np.meshgrid(xs, zs, indexing="ij")
            outside = m & ~barricades.in_lanes(barricades.LANES[rid], X, Z)
            self.assertEqual(int(outside.sum()), 0, rid)

    def test_the_big_rooms_lose_most_of_their_open_floor(self):
        for rid in ("dam", "stationsplein", "rembrandtplein"):
            open_square = json.loads((ROOMS / f"{rid}.json").read_text())
            open_square["props"] = [p for p in open_square["props"] if not p.get("barricade")]
            before = cameras.floor_grid(open_square)[2].sum()
            after = cameras.floor_grid(room(rid))[2].sum()
            self.assertLess(after, 0.5 * before, rid)

    def test_lanes_line_up_across_seamless_passages(self):
        # Rooms on one storey are one floor plan: walking out of one room's lane through a passage
        # must land in the next room's lane (or anywhere in a room with no cordons), and back.
        specs = {p.stem: json.loads(p.read_text()) for p in ROOMS.glob("*.json")}
        g = 0.45   # m: past the wall's thickness (0.3) between rooms on a floor plan
        checked = 0
        for rid in barricades.LANES:
            a = specs[rid]
            ox, oz = a.get("origin", [0, 0])
            (x0, z0), (x1, z1) = a["bounds"]["min"], a["bounds"]["max"]
            for side, wall in a.get("walls", {}).items():
                for o in wall.get("openings", []):
                    if o.get("kind") != "passage":
                        continue
                    for t in np.arange(o["center"] - o["width"] / 2 + 0.25, o["center"] + o["width"] / 2, 0.5):
                        x, z, dx, dz = {"north": (x0 + t, z0, 0, -1), "south": (x0 + t, z1, 0, 1),
                                        "west": (x0, z0 + t, -1, 0), "east": (x1, z0 + t, 1, 0)}[side]
                        hx, hz = x + ox + dx * g, z + oz + dz * g
                        for other in specs.values():
                            if other["id"] == rid or other.get("storey") != a.get("storey"):
                                continue
                            px, pz = other.get("origin", [0, 0])
                            (u0, w0), (u1, w1) = other["bounds"]["min"], other["bounds"]["max"]
                            bx, bz = hx - px, hz - pz
                            if not (u0 < bx < u1 and w0 < bz < w1):
                                continue
                            checked += 1
                            mine = bool(barricades.in_lanes(barricades.LANES[rid], np.array(x - dx * 0.25), np.array(z - dz * 0.25)))
                            theirs = other["id"] not in barricades.LANES or bool(
                                barricades.in_lanes(barricades.LANES[other["id"]], np.array(bx), np.array(bz)))
                            with self.subTest(a=rid, b=other["id"], at=(round(x, 2), round(z, 2))):
                                self.assertEqual(mine, theirs)
        self.assertGreater(checked, 100)


if __name__ == "__main__":
    unittest.main()
