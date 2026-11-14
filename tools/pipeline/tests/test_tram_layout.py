# damned_waters/tools/pipeline/tests/test_tram_layout.py
# Purpose: the tram's tape measure and hinge maths (tram_layout.py): the five sections fill the
# length they were given, a straight tram stays on its line, and old three-section rooms still read.
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tram_layout as tl  # noqa: E402


class TramLayoutTests(unittest.TestCase):
    def test_sections_fill_the_length(self):
        ls = tl.lengths(30.0)
        self.assertEqual(len(ls), 5)
        self.assertAlmostEqual(sum(ls) + 4 * tl.GAP, 30.0)
        self.assertAlmostEqual(ls[0], ls[4])
        self.assertLess(ls[2], ls[1])   # the centre section is the short one

    def test_straight_tram_stays_on_its_line(self):
        secs = tl.chain(30.0)
        self.assertTrue(all(abs(z) < 1e-9 and a == 0.0 for _, z, a, _ in secs))
        self.assertAlmostEqual(secs[0][0] - secs[0][3] / 2, -15.0)
        self.assertAlmostEqual(secs[-1][0] + secs[-1][3] / 2, 15.0)

    def test_derailed_sections_stay_hinged(self):
        secs = tl.chain(30.0, [0.0, 9.0, 24.0])
        for (x0, z0, a0, l0), (x1, z1, a1, l1) in zip(secs, secs[1:]):
            j0 = (x0 + math.cos(a0) * (l0 + tl.GAP) / 2, z0 - math.sin(a0) * (l0 + tl.GAP) / 2)
            j1 = (x1 - math.cos(a1) * (l1 + tl.GAP) / 2, z1 + math.sin(a1) * (l1 + tl.GAP) / 2)
            self.assertAlmostEqual(j0[0], j1[0])
            self.assertAlmostEqual(j0[1], j1[1])

    def test_old_three_section_lists_still_read(self):
        self.assertEqual(tl.resample([0.0, 9.0, 24.0]), [0.0, 4.5, 9.0, 16.5, 24.0])
        self.assertEqual(tl.resample([]), [0.0] * 5)
        self.assertEqual(tl.resample([3.0]), [3.0] * 5)
        self.assertEqual(tl.spread([1, 2]), [2, 3, 4])
        self.assertEqual(tl.spread([0]), [0, 1])


if __name__ == "__main__":
    unittest.main()
