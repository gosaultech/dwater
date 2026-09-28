# damned_waters/tools/characters/tests/test_characters.py
# Purpose: unit tests for the character pipeline that need no MakeHuman download:
# macro blending weights, rotations and the MakeHuman -> engine axis change, weight
# folding onto engine joints, mesh helpers (adjacency, smoothing, hems), the .dwc
# format round trip, and a sanity check of the shipped survivor.dwc.
#   python3 -m unittest discover -s tools/characters/tests
import itertools
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dwc  # noqa: E402
import garments  # noqa: E402
import mhdata  # noqa: E402
import rig  # noqa: E402

ROOT = HERE.parents[2]
SURVIVOR = ROOT / "engine" / "assets" / "characters" / "survivor.dwc"


class MacroTests(unittest.TestCase):
    def test_corner_weights_sum_to_one(self):
        # Every body is a mix of box corners (gender x age x muscle x weight); the mix must total 100%.
        for m in (mhdata.Macro(), mhdata.Macro(gender=0.3, age_years=8, muscle=0.9, weight=0.2),
                  mhdata.Macro(gender=0.0, age_years=70, muscle=0.1, weight=0.75), mhdata.Macro(age_years=1)):
            f = mhdata.macro_factors(m)
            total = sum(f[g] * f[a] * f[mu + "muscle"] * f[w + "weight"]
                        for g, a, mu, w in itertools.product(("male", "female"), ("baby", "child", "young", "old"),
                                                             ("min", "average", "max"), ("min", "average", "max")))
            self.assertAlmostEqual(total, 1.0, places=6, msg=m)

    def test_ages_hit_their_corners(self):
        self.assertAlmostEqual(mhdata.macro_factors(mhdata.Macro(age_years=25))["young"], 1.0)
        self.assertAlmostEqual(mhdata.macro_factors(mhdata.Macro(age_years=90))["old"], 1.0)
        self.assertAlmostEqual(mhdata.macro_factors(mhdata.Macro(age_years=1))["baby"], 1.0)

    def test_average_sliders_pick_the_average_targets(self):
        f = mhdata.macro_factors(mhdata.Macro(muscle=0.5, weight=0.5, height=0.5, proportions=0.5))
        self.assertEqual((f["averagemuscle"], f["maxmuscle"], f["minmuscle"]), (1.0, 0.0, 0.0))
        self.assertEqual((f["maxheight"], f["minheight"], f["idealproportions"]), (0.0, 0.0, 0.0))

    def test_ethnicity_is_normalised(self):
        f = mhdata.macro_factors(mhdata.Macro(african=2.0, asian=1.0, caucasian=1.0))
        self.assertAlmostEqual(f["african"] + f["asian"] + f["caucasian"], 1.0)
        self.assertAlmostEqual(f["african"], 0.5)


class RigTests(unittest.TestCase):
    def test_rot_is_a_proper_rotation(self):
        R = rig.rot(np.array([1.0, 2.0, 3.0]), 0.7)
        np.testing.assert_allclose(R @ R.T, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(np.linalg.det(R), 1.0)

    def test_arc_takes_u_onto_v(self):
        u, v = np.array([1.0, 0.2, -0.3]), np.array([-0.1, -1.0, 0.4])
        np.testing.assert_allclose(rig.arc(u, v) @ (u / np.linalg.norm(u)), v / np.linalg.norm(v), atol=1e-12)

    def test_to_engine_turns_and_scales(self):
        # MakeHuman: decimetres, +Z front, +X the body's left. Engine: metres, -Z front, -X left.
        np.testing.assert_allclose(rig.to_engine([10.0, 17.0, 2.0]), [-1.0, 1.7, -0.2])

    def test_joint_tables_agree(self):
        self.assertEqual(len(rig.ENGINE_JOINTS), len(rig.ENGINE_PARENT))
        for i, p in enumerate(rig.ENGINE_PARENT):
            self.assertLess(p, i, "parents come before children")
        self.assertTrue(set(rig.FOLD.values()) <= set(rig.ENGINE_JOINTS))

    def test_fold_weights_join_nearest_mapped_ancestor(self):
        bones = {"root": {"parent": None}, "spine05": {"parent": "root"}, "belly": {"parent": "spine05"},
                 "head": {"parent": None}, "jaw": {"parent": "head"}}
        skel = mhdata.Skeleton(bones, {}, list(bones))
        weights = {"belly": (np.array([0]), np.array([1.0])),          # unmapped: joins spine05 -> pelvis
                   "head": (np.array([1]), np.array([0.25])), "jaw": (np.array([1]), np.array([0.75]))}
        ids, ws = rig.fold_weights(skel, weights, 3)
        J = {n: i for i, n in enumerate(rig.ENGINE_JOINTS)}
        self.assertEqual(ids[0, 0], J["pelvis"])
        self.assertEqual((ids[1, 0], ids[1, 1]), (J["jaw"], J["head"]))
        np.testing.assert_allclose(ws[1, :2], [0.75, 0.25])
        np.testing.assert_allclose(ws[2], [1, 0, 0, 0])                 # unweighted: fully on the pelvis
        np.testing.assert_allclose(ws.sum(axis=1), 1.0, atol=1e-6)


class MeshHelperTests(unittest.TestCase):
    @staticmethod
    def grid(n):
        """An n x n vertex grid in the XY plane, as quads."""
        P = np.array([[x, y, 0.0] for y in range(n) for x in range(n)])
        quads = np.array([[y * n + x, y * n + x + 1, (y + 1) * n + x + 1, (y + 1) * n + x]
                          for y in range(n - 1) for x in range(n - 1)])
        return P, quads

    def test_boundary_is_the_rim(self):
        P, quads = self.grid(3)
        edges = garments.boundary_loops(quads)
        self.assertEqual(len(edges), 8)                                  # 4 sides x 2 edges
        self.assertNotIn(4, {v for e in edges for v in e})               # the middle vertex is interior

    def test_adjacency_is_symmetric(self):
        P, quads = self.grid(4)
        nb = garments.adjacency(quads, len(P))
        for i, n in enumerate(nb):
            for j in n:
                self.assertIn(i, nb[j])
        self.assertEqual(len(nb[5]), 4)

    def test_taubin_flattens_a_bump_and_respects_fixed(self):
        P, quads = self.grid(7)
        P[24, 2] = 1.0                                                   # a spike in the middle
        nb = garments.adjacency(quads, len(P))
        fixed = np.array([0, 6])
        S = garments.taubin(P, nb, 8, fixed=fixed)
        self.assertLess(S[24, 2], 0.5)
        np.testing.assert_array_equal(S[fixed], P[fixed])
        self.assertTrue(np.all(np.isfinite(S)))


def toy_character():
    rng = np.random.default_rng(3)
    V = 5
    w = rng.random((V, 4)).astype(np.float32)
    part = dwc.Part("jeans", rng.random((V, 3)).astype(np.float32), rng.random((V, 3)).astype(np.float32),
                    rng.integers(0, 256, (V, 4), dtype=np.uint8), np.full(V, 7, np.uint8), np.arange(V, dtype=np.uint8),
                    rng.integers(0, 24, (V, 4), dtype=np.uint8), w / w.sum(axis=1, keepdims=True),
                    np.array([[0, 1, 2], [2, 3, 4]]), np.linspace(0, 1, V).astype(np.float32))
    anchor = dwc.Anchor("loc7", 4, np.array([0.1, 0.2, 0.3], np.float32), np.array([0, 1, 0], np.float32))
    return dwc.Character(rng.random((24, 3)).astype(np.float32), [part], [anchor])


class DwcTests(unittest.TestCase):
    def test_round_trip(self):
        ch = toy_character()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toy.dwc"
            dwc.write(path, ch)
            back = dwc.read(path)
        np.testing.assert_array_equal(back.joints, ch.joints)
        a, b = ch.parts[0], back.parts[0]
        self.assertEqual(b.name, "jeans")
        for field in ("pos", "nrm", "col", "mat", "region", "joints", "weights", "tris", "aux"):
            np.testing.assert_array_equal(getattr(b, field), getattr(a, field), err_msg=field)
        self.assertEqual((back.anchors[0].name, back.anchors[0].joint), ("loc7", 4))
        np.testing.assert_array_equal(back.anchors[0].pos, ch.anchors[0].pos)

    def test_validate_rejects_an_index_past_the_end(self):
        ch = toy_character()
        ch.parts[0].tris = np.array([[0, 1, 5]])
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(AssertionError):
            dwc.write(Path(tmp) / "bad.dwc", ch)


@unittest.skipUnless(SURVIVOR.exists(), "survivor.dwc not built")
class ShippedSurvivorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ch = dwc.read(SURVIVOR)

    def test_rig_and_parts(self):
        self.assertEqual(len(self.ch.joints), len(rig.ENGINE_JOINTS))
        names = {p.name for p in self.ch.parts}
        self.assertTrue({"body", "jeans", "hoodie", "jacket", "boot_l", "boot_r"} <= names, names)

    def test_every_vertex_is_skinned_to_real_joints(self):
        for p in self.ch.parts:
            np.testing.assert_allclose(p.weights.sum(axis=1), 1.0, atol=1e-4, err_msg=p.name)
            self.assertLess(int(p.joints.max()), len(self.ch.joints), p.name)
            self.assertTrue(np.all(np.isfinite(p.pos)), p.name)

    def test_standing_on_the_floor_at_a_human_height(self):
        lo = min(float(p.pos[:, 1].min()) for p in self.ch.parts)
        hi = max(float(p.pos[:, 1].max()) for p in self.ch.parts)
        self.assertGreater(lo, -0.01)
        self.assertLess(lo, 0.03)
        self.assertTrue(1.7 < hi - lo < 1.95, hi - lo)

    def test_anchors_for_locs_and_gear(self):
        names = [a.name for a in self.ch.anchors]
        self.assertGreater(sum(n.startswith("loc") for n in names), 50)
        for n in ("backpack", "flashlight"):
            self.assertIn(n, names)


if __name__ == "__main__":
    unittest.main()
