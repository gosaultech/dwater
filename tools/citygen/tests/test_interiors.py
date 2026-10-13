# damned_waters/tools/citygen/tests/test_interiors.py
# Purpose: the interior pass (interiors.py) gives each shop's shelves photographed stock, adds its
# fixtures without burying a door or a spawn, and run twice gives the same room.
import copy
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import interiors  # noqa: E402

ROOMS = Path(__file__).resolve().parents[3] / "game" / "data" / "rooms"


def room(rid):
    return json.loads((ROOMS / f"{rid}.json").read_text())


class InteriorPassTests(unittest.TestCase):
    def test_runs_twice_to_the_same_room(self):
        for rid in interiors.ROOMS:
            a = room(rid)
            interiors.apply(a)
            b = copy.deepcopy(a)
            interiors.apply(b)
            self.assertEqual(a, b, rid)

    def test_every_shelf_is_stocked_from_a_photo(self):
        for rid in interiors.ROOMS:
            s = room(rid)
            interiors.apply(s)
            for p in s["props"]:
                if p["type"] == "shelving":
                    self.assertIsInstance(p.get("photo"), str, rid)

    def test_new_fixtures_keep_clear_of_doors_and_spawns(self):
        for rid in interiors.ROOMS:
            s = room(rid)
            interiors.apply(s)
            W, D = s["bounds"]["max"]
            keep = [(v["pos"][0], v["pos"][2]) for v in s["spawns"].values()]
            for side, w in s.get("walls", {}).items():
                for o in w.get("openings", []):
                    if o.get("kind", "door") in ("door", "passage"):
                        c = o["center"]
                        keep.append({"north": (c, 0.0), "south": (c, D), "west": (0.0, c), "east": (W, c)}[side])
            for p in s["props"]:
                if not p.get("interior") or p.get("collide") is False or "size" not in p:
                    continue
                fp = interiors._footprint(p)
                for x, z in keep:
                    self.assertFalse(interiors._inside(x, z, fp, 0.4), f"{rid}: {p['type']} at {p['pos']} on ({x:.1f}, {z:.1f})")


if __name__ == "__main__":
    unittest.main()
