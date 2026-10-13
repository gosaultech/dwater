# damned_waters/tools/assets/tests/test_photos.py
# Purpose: the set photos' ledger (tools/assets/photos.json): only licences that may go into a
# picture, every photo a RoomSpec names listed, crops inside their photos, every photo credited.
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import photos  # noqa: E402

ROOMS = HERE.parents[2] / "game" / "data" / "rooms"


class PhotoLedgerTests(unittest.TestCase):
    def setUp(self):
        self.m = photos.manifest()

    def test_only_licences_that_may_go_into_a_picture(self):
        for pid, e in self.m.items():
            self.assertIn(e["license"], photos.ALLOWED, pid)
            self.assertTrue(e["landing"] and e["url"], pid)

    def test_every_photo_a_room_names_is_listed(self):
        for f in sorted(ROOMS.glob("*.json")):
            for pid in photos.references(json.loads(f.read_text())):
                self.assertIn(pid, self.m, f"{f.name}: {pid}")

    def test_crops_lie_inside_their_photos(self):
        for pid, e in self.m.items():
            for c in e.get("rows", []) + ([e["panel"]] if "panel" in e else []):
                self.assertTrue(0.0 <= c[0] < c[2] <= 1.0 and 0.0 <= c[1] < c[3] <= 1.0, f"{pid}: {c}")
            self.assertTrue(e.get("rows") or e.get("panel"), pid)

    def test_every_photo_is_credited(self):
        md = photos.credits_md(self.m)
        for pid, e in self.m.items():
            self.assertIn(f"**{pid}**", md)
            self.assertIn(e["landing"], md)


if __name__ == "__main__":
    unittest.main()
