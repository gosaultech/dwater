# damned_waters/tools/assets/tests/test_decals.py
# Purpose: the decals (decals.py): the same words always make the same file; each style draws paint
# on a transparent ground; sprayed words fit their sheet (no letter cut off at its edges).
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decals  # noqa: E402


class Decals(unittest.TestCase):
    def test_the_same_words_make_the_same_file(self):
        a = {"style": "spray", "text": "GEEN WATER", "color": [0.9, 0.9, 0.9], "seed": 3}
        self.assertEqual(decals.decal_id(a), decals.decal_id(dict(a)))
        self.assertEqual(decals.decal_id(a), decals.decal_id(dict(a, id="whatever")))
        self.assertNotEqual(decals.decal_id(a), decals.decal_id(dict(a, text="GEEN ETEN")))

    def test_each_style_paints_on_a_clear_ground(self):
        for spec in ({"style": "spray", "text": "HOTEL VOL\n14 LEVEND", "aspect": 2.2},
                     {"style": "xcode", "top": "8/11", "left": "BRW-3", "right": "WATER", "bottom": "0"},
                     {"style": "poster", "text": "VERMIST\nTHEO · 4 JAAR", "photo": True}):
            im = np.asarray(decals.draw(spec))
            self.assertEqual(im.shape[2], 4, spec["style"])
            a = im[:, :, 3]
            self.assertGreater((a > 200).mean(), 0.01, spec["style"])   # paint
            if spec["style"] != "poster":
                self.assertGreater((a < 10).mean(), 0.4, spec["style"])   # and clear round it

    def test_sprayed_words_fit_their_sheet(self):
        for text, aspect in (("NIET NAAR BENEDEN", 4.0), ("ZE KOMEN UIT HET WATER", 7.2), ("DAM = DOOD", 4.3)):
            a = np.asarray(decals.draw({"style": "spray", "text": text, "aspect": aspect, "seed": 1}))[:, :, 3]
            self.assertLess(a[:, :3].max(), 140, text)    # nothing solid against the left edge
            self.assertLess(a[:, -3:].max(), 140, text)   # or the right


if __name__ == "__main__":
    unittest.main()
