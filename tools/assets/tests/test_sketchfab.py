# damned_waters/tools/assets/tests/test_sketchfab.py
# Purpose: the model ledger's gate and bookkeeping (sketchfab.py), with no network: only CC0 and
# CC BY pass, the glTF download is the one taken, unpacking cannot escape its directory, every
# model is credited, and each run is logged.
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sketchfab as sf  # noqa: E402

MODEL = {"uid": "abc123", "name": "A Van", "license": {"label": "CC Attribution"}, "faceCount": 21000,
         "user": {"username": "maker", "displayName": "The Maker", "profileUrl": "https://sketchfab.com/maker"},
         "viewerUrl": "https://sketchfab.com/3d-models/a-van-abc123"}


class SketchfabTests(unittest.TestCase):
    def test_only_cc0_and_cc_by_pass_the_gate(self):
        self.assertEqual(sf.licence_of(MODEL), "CC BY 4.0")
        self.assertEqual(sf.licence_of({"license": {"label": "CC0 Public Domain"}}), "CC0 1.0")
        for label in ("CC Attribution-NonCommercial", "CC Attribution-ShareAlike", "CC Attribution-NoDerivs", "Free Standard", "Standard", ""):
            self.assertIsNone(sf.licence_of({"license": {"label": label}}), label)
        self.assertIsNone(sf.licence_of({}))
        with self.assertRaises(ValueError):
            sf.entry("van", dict(MODEL, license={"label": "CC Attribution-NonCommercial"}))

    def test_the_gltf_is_taken_never_the_source(self):
        both = {"source": {"url": "s"}, "gltf": {"url": "g"}, "glb": {"url": "b"}, "usdz": {"url": "u"}}
        self.assertEqual(sf.pick_archive(both), ("glb", "b"))
        self.assertEqual(sf.pick_archive({"source": {"url": "s"}, "gltf": {"url": "g"}}), ("gltf", "g"))
        with self.assertRaises(ValueError):
            sf.pick_archive({"source": {"url": "s"}})

    def test_unpacking_stays_in_its_directory(self):
        names = ["scene.gltf", "textures/a.png", "../evil.py", "/etc/passwd", "C:\\x", "a/../../b"]
        self.assertEqual(sf.safe_members(names), ["scene.gltf", "textures/a.png"])

    def test_every_model_is_credited(self):
        ledger = {"_file": "x", "van": sf.entry("van", MODEL, "a delivery van")}
        text = "\n".join(sf.credit_lines(ledger))
        self.assertIn("[A Van](https://sketchfab.com/3d-models/a-van-abc123)", text)
        self.assertIn("[The Maker](https://sketchfab.com/maker)", text)
        self.assertIn("CC BY 4.0", text)
        self.assertIn("a delivery van", text)
        self.assertNotIn("_file", text)

    def test_a_run_is_logged(self):
        with tempfile.TemporaryDirectory() as d:
            sf._log(Path(d), "fetch", "van", 1, time.time() - 0.5, "ok")
            rows = sqlite3.connect(Path(d) / "usage.db").execute("SELECT command, detail, models, exit_status FROM runs").fetchall()
            self.assertEqual(rows, [("fetch", "van", 1, "ok")])
            self.assertIsNone(sf.model_path("van", Path(d)))
            (Path(d) / "van").mkdir()
            (Path(d) / "van" / "abc.glb").write_bytes(b"x")
            self.assertEqual(sf.model_path("van", Path(d)).name, "abc.glb")


if __name__ == "__main__":
    unittest.main()
