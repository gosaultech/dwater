# damned_waters/tools/assets/tests/test_detail_maps.py
# Purpose: the detail maps (tools/assets/detail_maps.py): slopes survive packing into bytes, the
# generated maps tile and are the same on every build, a scan keeps its relief but gives up its
# colour, and the files and tile sizes in git agree with the engine's table (dw/detail.hpp).
import re
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import detail_maps as dm  # noqa: E402


class Packing(unittest.TestCase):
    def test_slopes_come_back_out_of_the_bytes(self):
        du, dv = np.meshgrid(np.linspace(-0.8, 0.8, 9), np.linspace(-0.8, 0.8, 9))
        rgba = dm.pack(du, dv, np.ones_like(du), np.full_like(du, 0.5))
        bu, bv = dm.unpack_slopes(rgba)
        self.assertLess(np.abs(bu - du).max(), 0.03)
        self.assertLess(np.abs(bv - dv).max(), 0.03)
        self.assertTrue((rgba[..., 2] == 128).all())   # tone 1: the material's own colour

    def test_a_slope_rising_to_the_right_and_up_the_image(self):
        n = 16
        x = np.arange(n) / n
        ramp = np.sin(2 * np.pi * x)[None, :].repeat(n, axis=0) * 0.001     # rises to the right at x = 0
        du, dv = dm.slopes(ramp, 0.1)
        self.assertGreater(du[0, 0], 0)
        self.assertAlmostEqual(float(np.abs(dv).max()), 0)
        rise = np.sin(2 * np.pi * x)[::-1, None].repeat(n, axis=1) * 0.001  # rises up the image at its foot
        _, dv = dm.slopes(rise, 0.1)
        self.assertGreater(dv[-1, 0], 0)


class Generated(unittest.TestCase):
    def test_noise_and_cells_wrap_round(self):
        self.assertLess(dm.seam(dm.tiling_noise(64, 1.5, 3)), 1.6)
        edge, centre = dm.cell_edges(64, 40, 3, warp=0.02)
        self.assertLess(dm.seam(edge), 1.6)
        self.assertTrue((edge >= 0).all() and (centre >= 0).all())

    def test_skin_and_metal_tile_and_repeat_exactly(self):
        for make in (dm.skin, dm.metal):
            a = make(128, 0.03)
            self.assertEqual(a.shape, (128, 128, 4))
            for ch in range(4):
                self.assertLess(dm.seam(a[..., ch]), 1.7, f"{make.__name__} channel {ch}")
            self.assertAlmostEqual(a[..., 2].mean() / 255, 0.5, delta=0.02)   # no lighter or darker overall
            self.assertTrue((a == make(128, 0.03)).all())                     # the same on every build


class Scans(unittest.TestCase):
    def test_a_scan_keeps_its_relief_and_gives_up_its_colour(self):
        rng = np.random.default_rng(1)
        diff = rng.random((8, 8, 3)) * np.array([1.0, 0.3, 0.1])   # a strongly coloured scan
        nor = rng.random((8, 8, 3))
        rough = rng.random((8, 8))
        a = dm.from_scan(diff, nor, rough)
        self.assertTrue((np.abs(a[..., 0] / 255 - nor[..., 0]) < 0.003).all())
        self.assertTrue((np.abs(a[..., 3] / 255 - (1 - rough)) < 0.003).all())   # rough turned over into gloss
        self.assertAlmostEqual(a[..., 2].mean() / 255, 0.5, delta=0.06)


class Shipped(unittest.TestCase):
    def test_the_files_and_tiles_match_the_engines_table(self):
        hpp = (dm.REPO / "engine" / "include" / "dw" / "detail.hpp").read_text()
        table = re.findall(r'\{"(\w+)", "u_d\w+", ([0-9.]+)f\}', hpp)
        self.assertEqual([n for n, _ in table], list(dm.MAPS))   # the same maps, in the same order
        for name, tile in table:
            self.assertAlmostEqual(float(tile), dm.MAPS[name]["tile"])
            im = Image.open(dm.OUT / f"{name}.png")
            self.assertEqual(im.mode, "RGBA")
            self.assertEqual(im.size, (dm.MAPS[name]["size"],) * 2)
            a = np.asarray(im)
            for ch in range(3):
                self.assertLess(dm.seam(a[..., ch]), 1.7, f"{name} channel {ch}")


if __name__ == "__main__":
    unittest.main()
