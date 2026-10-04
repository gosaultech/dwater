# damned_waters/tools/assets/tests/test_polyhaven.py
# Purpose: the asset fetcher's pure parts: which assets a RoomSpec names, which files serve a
# texture or a model, the cache's checksum rule, and the ledger. No network.
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import polyhaven  # noqa: E402

FILES_TEXTURE = {
    "Diffuse": {"1k": {"jpg": {"url": "https://x/t_diff_1k.jpg", "md5": "a"}, "png": {"url": "https://x/t_diff_1k.png"}}},
    "Rough": {"1k": {"jpg": {"url": "https://x/t_rough_1k.jpg", "md5": "b"}}},
    "nor_gl": {"1k": {"jpg": {"url": "https://x/t_nor_gl_1k.jpg", "md5": "c"}}, "2k": {}},
    "nor_dx": {"1k": {"jpg": {"url": "https://x/t_nor_dx_1k.jpg"}}},
}
FILES_MODEL = {"gltf": {"1k": {"gltf": {"url": "https://x/sofa.gltf", "md5": "g",
                                         "include": {"textures/sofa_diff_1k.jpg": {"url": "https://x/sofa_diff.jpg", "md5": "d"},
                                                     "sofa.bin": {"url": "https://x/sofa.bin", "md5": "e"}}}}}}


class ReferenceTests(unittest.TestCase):
    def test_strings_dicts_and_models(self):
        spec = {"materials": {"floor": "ph:herringbone_parquet", "wall": {"ph": "plastered_wall", "tint": [1, 1, 1]},
                              "ceiling": "plaster"},
                "props": [{"type": "model", "model": "ph:sofa_02"}, {"type": "sofa", "material": "ph:hessian_230"}],
                "walls": {"north": {"material": "ph:brick_wall_003"}}}
        self.assertEqual(polyhaven.references(spec), {"herringbone_parquet": "texture", "plastered_wall": "texture",
                                                      "sofa_02": "model", "hessian_230": "texture",
                                                      "brick_wall_003": "texture"})

    def test_exterior_bricks_are_found(self):
        spec = {"exterior": {"side": "north", "bricks": ["ph:red_brick_03"], "quay": {"ph": "cobblestone_01"}}}
        self.assertEqual(polyhaven.references(spec), {"red_brick_03": "texture", "cobblestone_01": "texture"})

    def test_plain_keys_are_not_assets(self):
        self.assertIsNone(polyhaven.ref_id("plaster"))
        self.assertIsNone(polyhaven.ref_id({"tint": [1, 1, 1]}))

    def test_shipped_rooms_parse(self):  # every RoomSpec in the game can be scanned
        for f in (HERE.parents[2] / "game" / "data" / "rooms").glob("*.json"):
            polyhaven.references(json.loads(f.read_text()))


class PickTests(unittest.TestCase):
    def test_texture_maps_prefer_jpg_and_skip_missing(self):
        p = polyhaven.pick_texture(FILES_TEXTURE, "1k")
        self.assertEqual(p["diff"]["url"], "https://x/t_diff_1k.jpg")
        self.assertEqual(p["nor_gl"]["md5"], "c")
        self.assertNotIn("disp", p)
        self.assertEqual(polyhaven.pick_texture(FILES_TEXTURE, "2k"), {})

    def test_model_brings_its_files(self):
        m = polyhaven.pick_model(FILES_MODEL, "1k")
        self.assertEqual(m["gltf"]["url"], "https://x/sofa.gltf")
        self.assertEqual(set(m["include"]), {"textures/sofa_diff_1k.jpg", "sofa.bin"})
        with self.assertRaises(KeyError):
            polyhaven.pick_model(FILES_MODEL, "4k")


class CacheTests(unittest.TestCase):
    def test_existing_file_with_right_checksum_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.jpg"
            f.write_bytes(b"hello")
            # A matching checksum never touches the network (the URL is unreachable on purpose).
            self.assertEqual(polyhaven.fetch("http://invalid.invalid/a.jpg", f, polyhaven.md5_of(f)), f)

    def test_manifest_is_sorted_and_keeps_old_entries(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "manifest.json"
            base = {"license": "CC0", "authors": ["A"], "kind": "texture"}
            polyhaven.update_manifest([dict(base, id="zz", name="Z", source="s")], p)
            m = polyhaven.update_manifest([dict(base, id="aa", name="A", source="s")], p)
            self.assertEqual(list(m["assets"]), ["aa", "zz"])
            self.assertEqual(json.loads(p.read_text())["assets"]["zz"]["license"], "CC0")


if __name__ == "__main__":
    unittest.main()
