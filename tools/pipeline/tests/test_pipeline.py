# damned_waters/tools/pipeline/tests/test_pipeline.py
# Purpose: depth packing is lossless and matches the GDScript/shader codec;
# coordinate conversion is a proper rotation; every shipped RoomSpec validates.
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import depth_pack  # noqa: E402
import roomspec  # noqa: E402

ROOMS = HERE.parents[2] / "game" / "data" / "rooms"


class DepthPackTests(unittest.TestCase):
    def test_round_trip_is_lossless(self):
        d = np.random.default_rng(0).integers(0, 65536, size=(64, 96), dtype=np.uint16)
        np.testing.assert_array_equal(depth_pack.unpack_rg8(depth_pack.pack_depth16(d)), d)

    def test_vectors_match_gdscript_codec(self):  # same table as tests/unit/test_depth_codec.gd
        for metres, hi, lo in [(0.0, 0, 0), (5.0, 40, 0), (32.0, 255, 255), (1.2345, 9, 224)]:
            v = np.array([[round(metres / roomspec.DEPTH_MAX_M * 65535)]], dtype=np.uint16)
            self.assertEqual(tuple(depth_pack.pack_depth16(v)[0, 0, :2]), (hi, lo))

    def test_import_file_disables_compression(self):
        t = depth_pack.import_text("res://x.png")
        self.assertIn("compress/mode=0", t)
        self.assertIn("detect_3d/compress_to=0", t)
        self.assertIn("mipmaps/generate=false", t)


class RoomSpecTests(unittest.TestCase):
    def test_g2b_maps_axes(self):
        self.assertEqual(roomspec.g2b((1, 2, 3)), (1, -3, 2))

    def test_all_rooms_validate(self):
        specs = roomspec.load_all(ROOMS)
        self.assertEqual(set(specs), {"gang", "voorkamer", "kelder"})

    def test_bad_opening_is_caught(self):
        spec = {"id": "x", "bounds": {"min": [0, 0], "max": [2, 2]}, "height": 3, "shots": [], "spawns": {},
                "walls": {"north": {"openings": [{"kind": "door", "center": 1.9, "width": 1.0, "height": 2}]}}}
        self.assertTrue(any("exceeds" in p for p in roomspec.validate(spec)))


if __name__ == "__main__":
    unittest.main()
