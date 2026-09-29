# damned_waters/tools/characters/tests/test_drowned.py
# Purpose: unit tests for the Drowned citizens: the cutting and layering geometry they rely on
# (exact trims that blend skin weights, subdivision for narrow pieces, folded edges and tear
# walls, the neckline walk collars are built along) on small synthetic meshes, plus sanity checks
# of the shipped citizen files (rig, skinning, height, the anchors the engine hangs gore and hair on).
#   python3 -m unittest discover -s tools/characters/tests
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dwc  # noqa: E402
import garments as gm  # noqa: E402
import rig  # noqa: E402
from parts import MAT  # noqa: E402

CHARACTERS = HERE.parents[2] / "engine" / "assets" / "characters"
CITIZENS = ("office_worker", "pieter", "woman_dress")


def one_hot(joints, count=24):
    W = np.zeros((len(joints), count))
    W[np.arange(len(joints)), joints] = 1.0
    return W


def grid(n):
    """An n x n vertex grid in the XY plane (normals +Z), as triangles."""
    P = np.array([[x, y, 0.0] for y in range(n) for x in range(n)], float)
    tris = []
    for y in range(n - 1):
        for x in range(n - 1):
            a, b, c, d = y * n + x, y * n + x + 1, (y + 1) * n + x + 1, (y + 1) * n + x
            tris += [[a, b, c], [a, c, d]]
    return P, np.tile([0.0, 0.0, 1.0], (len(P), 1)), np.array(tris)


class WeightTests(unittest.TestCase):
    def test_top4_keeps_the_strongest_four_and_renormalises(self):
        W = np.array([[0.05, 0.3, 0.1, 0.2, 0.25, 0.1] + [0.0] * 18])
        jid, jw = gm.top4(W)
        self.assertEqual(sorted(jid[0].tolist()), [1, 2, 3, 4] if W[0, 2] >= W[0, 5] else [1, 3, 4, 5])
        self.assertAlmostEqual(float(jw.sum()), 1.0, places=6)
        self.assertEqual(int(jid[0, 0]), 1)                               # strongest first


class ClipTests(unittest.TestCase):
    def test_cut_vertices_blend_the_skin_weights_of_both_ends(self):
        # One triangle: its first corner (joint 1) kept, the other two (joint 2) cut away halfway.
        P = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
        s = np.array([1.0, -1.0, -1.0])
        Pc, Nc, src, T, W, on_cut = gm.clip(P, np.tile([0, 0, 1.0], (3, 1)), np.arange(3), np.array([[0, 1, 2]]), s,
                                            one_hot([1, 2, 2]))
        self.assertEqual(len(T), 1)
        self.assertEqual(int(on_cut.sum()), 2)
        np.testing.assert_allclose(W[on_cut][:, [1, 2]], 0.5)            # half one joint, half the other: no tearing
        self.assertEqual(sorted(tuple(np.round(q, 6)) for q in Pc[on_cut]), [(0.0, 0.5, 0.0), (0.5, 0.0, 0.0)])

    def test_only_the_kept_side_survives_and_edges_are_shared(self):
        P, N, tris = grid(6)
        s = 2.3 - P[:, 0]                                                 # keep x <= 2.3
        Pc, _, _, T, _, on_cut = gm.clip(P, N, np.arange(len(P)), tris, s, one_hot(np.zeros(len(P), int)))
        self.assertTrue(np.all(Pc[:, 0] <= 2.3 + 1e-9))
        np.testing.assert_allclose(Pc[on_cut, 0], 2.3)
        self.assertEqual(int(on_cut.sum()), 6 + 5)                       # one vertex per cut edge: 6 rows + 5 diagonals
        self.assertEqual(len(np.unique(T)), len(Pc))                      # nothing left dangling


class SubdivideTests(unittest.TestCase):
    def test_picked_triangles_split_in_four_with_averaged_weights(self):
        P, N, tris = grid(2)                                              # two triangles
        Ps, _, _, Ts, Ws = gm.subdivide(P, N, np.arange(4), tris, one_hot([0, 1, 1, 0]), np.array([True, False]))
        self.assertEqual(len(Ts), 4 + 1)
        self.assertEqual(len(Ps), 4 + 3)
        mid = np.nonzero(np.all(np.isclose(Ps, [0.5, 0, 0]), axis=1))[0][0]
        np.testing.assert_allclose(Ws[mid, :2], [0.5, 0.5])


class FoldTests(unittest.TestCase):
    def test_edges_fold_back_along_the_normal_by_their_depth(self):
        P, N, tris = grid(4)
        P2, N2, T2, (tag,), folded = gm.fold_edges(P, N, tris, 0.01, carry=(np.arange(len(P)),))
        rim = np.unique(gm.rim_edges(tris))
        self.assertEqual(int(folded.sum()), len(rim))
        np.testing.assert_allclose(P2[folded, 2], -0.01)                 # behind the surface, into the body
        np.testing.assert_array_equal(tag[folded], rim)                  # carried values follow their vertex
        self.assertEqual(len(T2), len(tris) + 2 * len(gm.rim_edges(tris)))

    def test_only_the_chosen_edges_fold(self):
        P, N, tris = grid(4)
        rim = gm.rim_edges(tris)
        left = rim[(P[rim[:, 0], 0] == 0) & (P[rim[:, 1], 0] == 0)]
        _, _, _, _, folded = gm.fold_edges(P, N, tris, 0.01, edges=left)
        self.assertEqual(int(folded.sum()), 4)                            # the 4 vertices down the left side


class NecklineTests(unittest.TestCase):
    def test_walks_the_neck_loop_in_order_and_ignores_strays(self):
        # A tube (a garment round the neck) open at the top, and a stray sliver above it.
        k, rings = 16, 3
        ang = 2 * np.pi * np.arange(k) / k
        P = np.array([[np.sin(a), y, -np.cos(a)] for y in range(rings) for a in ang], float)
        tris = []
        for r in range(rings - 1):
            for j in range(k):
                a, b = r * k + j, r * k + (j + 1) % k
                tris += [[a, b + k, b], [a, a + k, b + k]]
        stray = len(P)
        P = np.vstack([P, [[0, 5, 0], [0.1, 5, 0], [0, 5.1, 0]]])
        tris.append([stray, stray + 1, stray + 2])
        rim = gm.rim_edges(np.array(tris))
        chain = gm.neckline(rim, P, above=rings - 1.5)
        self.assertEqual(sorted(chain.tolist()), list(range((rings - 1) * k, rings * k)))   # the top ring, nothing else
        edges = {tuple(sorted(e)) for e in rim.tolist()}
        for a, b in zip(chain[:-1], chain[1:]):
            self.assertIn(tuple(sorted((int(a), int(b)))), edges)        # each step follows an edge
        self.assertLess(P[chain[len(chain) // 4], 0], P[chain[3 * len(chain) // 4], 0])   # front left first


@unittest.skipUnless(all((CHARACTERS / f"{c}.dwc").exists() for c in CITIZENS), "citizens not built")
class ShippedCitizenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cast = {c: dwc.read(CHARACTERS / f"{c}.dwc") for c in CITIZENS}

    def test_rig_skinning_and_height(self):
        for name, ch in self.cast.items():
            self.assertEqual(len(ch.joints), len(rig.ENGINE_JOINTS), name)
            for p in ch.parts:
                np.testing.assert_allclose(p.weights.sum(axis=1), 1.0, atol=1e-4, err_msg=f"{name}/{p.name}")
                self.assertLess(int(p.joints.max()), len(ch.joints), f"{name}/{p.name}")
                self.assertTrue(np.all(np.isfinite(p.pos)) and np.all(np.isfinite(p.nrm)), f"{name}/{p.name}")
            lo = min(float(p.pos[:, 1].min()) for p in ch.parts)
            hi = max(float(p.pos[:, 1].max()) for p in ch.parts)
            self.assertGreater(lo, -0.02, name)
            self.assertTrue(1.45 < hi - lo < 1.95, (name, hi - lo))

    def test_tears_have_flesh_walls_and_the_skin_stays_skin(self):
        for name, ch in self.cast.items():
            body = next(p for p in ch.parts if p.name == "body")
            walls = int(np.sum(body.mat == MAT["flesh"]))
            if name == "woman_dress":                                    # no tear in her: no walls
                self.assertEqual(walls, 0)
            else:
                self.assertGreater(walls, 20, name)                      # inside the split belly (and Pieter's mouth)
            self.assertGreater(int(np.sum(body.mat == MAT["drowned"])), len(body.mat) // 2, name)

    def test_they_all_died_screaming(self):
        for name, ch in self.cast.items():
            throat = next((p for p in ch.parts if p.name == "throat"), None)
            self.assertIsNotNone(throat, name)                           # the black hollow behind the scream
            self.assertTrue(np.all(throat.mat == MAT["void"]), name)
            self.assertNotIn("tongue", [a.name for a in ch.anchors], name)   # a scream doesn't loll its tongue

    def test_anchors_for_gore_hair_and_water(self):
        names = {c: [a.name for a in ch.anchors] for c, ch in self.cast.items()}
        for c in CITIZENS:
            self.assertIn("loose_skin", names[c])
            for d in ("drip_hand_l", "drip_hand_r", "drip_chin"):
                self.assertIn(d, names[c])
            self.assertGreaterEqual(sum(n.startswith("drip_") for n in names[c]), 6, c)   # and round the hems
        self.assertIn("guts", names["office_worker"])
        self.assertIn("guts", names["pieter"])
        self.assertNotIn("guts", names["woman_dress"])                  # her belly is whole
        self.assertIn("tie", names["office_worker"])
        self.assertIn("badge", names["office_worker"])
        self.assertGreater(sum(n.startswith("hair") for n in names["woman_dress"]), 100)

    def test_pieter_lost_an_eye(self):
        eyes = {p.name: p for p in self.cast["pieter"].parts if p.name.startswith("eye_")}
        self.assertTrue(np.all(eyes["eye_r"].mat == MAT["void"]))
        self.assertFalse(np.any(eyes["eye_l"].mat == MAT["void"]))


if __name__ == "__main__":
    unittest.main()
