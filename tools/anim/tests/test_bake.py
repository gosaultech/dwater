# damned_waters/tools/anim/tests/test_bake.py
# Purpose: the motion-capture bake (tools/anim): a BVH is read and posed as written, angles come back
# from the rig's rotations exactly, the capture's turns read correctly for a rig facing the other
# way, the mirrored loop is symmetric, and setting the average lean leaves the legs swinging as
# they did. Synthetic data: no dataset needed.
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bake_mocap  # noqa: E402
import bvh  # noqa: E402

TINY = """HIERARCHY
ROOT Hips
{
 OFFSET 0 0 0
 CHANNELS 6 Xposition Yposition Zposition Yrotation Xrotation Zrotation
 JOINT LeftHip
 {
  OFFSET 10 0 0
  CHANNELS 3 Yrotation Xrotation Zrotation
  JOINT LeftKnee
  {
   OFFSET 0 -40 0
   CHANNELS 3 Yrotation Xrotation Zrotation
   End Site
   {
    OFFSET 0 -40 0
   }
  }
 }
}
MOTION
Frames: 2
Frame Time: 0.5
0 90 0 0 0 0 0 0 0 0 0 0
0 90 10 0 0 0 0 30 0 0 0 0
"""


class BakeTests(unittest.TestCase):
    def test_a_bvh_is_read_and_posed_as_written(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tiny.bvh"
            p.write_text(TINY)
            m = bvh.read(p)
            self.assertEqual([j.name for j in m.joints], ["Hips", "LeftHip", "LeftKnee"])
            self.assertAlmostEqual(m.frame_time, 0.5)
            G, P = bvh.forward_kinematics(m)
            np.testing.assert_allclose(P[0, 2], [10, 50, 0], atol=1e-9)        # standing: the knee 40 below the hip
            # frame 2: the hip turned 30 degrees about +x, which swings a hanging leg toward -z (back,
            # for the capture facing +z: the rig, facing -z, reads it as forward with x flipped)
            np.testing.assert_allclose(P[1, 2], [10, 90 - 40 * math.cos(math.radians(30)), 10 - 40 * math.sin(math.radians(30))], atol=1e-9)

    def test_angles_come_back_from_the_rigs_rotation(self):
        rng = np.random.default_rng(3)
        e = rng.uniform(-1.2, 1.2, size=(50, 3))
        np.testing.assert_allclose(bake_mocap.euler_yxz(bake_mocap.from_euler_yxz(e)), e, atol=1e-9)

    def test_a_turn_seen_from_the_rig_facing_the_other_way(self):
        # Seen from behind (a half turn about y), a swing about x or z is the opposite one; about y the same.
        A = bake_mocap.A
        for axis, e_src, e_rig in ((bvh.rx, [0.3, 0, 0], [-0.3, 0, 0]), (bvh.ry, [0, 0.3, 0], [0, 0.3, 0]), (bvh.rz, [0, 0, 0.3], [0, 0, -0.3])):
            R = bake_mocap.from_euler_yxz(np.array(e_src))
            np.testing.assert_allclose(bake_mocap.euler_yxz(A @ R @ A), e_rig, atol=1e-9)

    def test_the_mirrored_loop_is_symmetric(self):
        n, cols = 64, 3 + 3 * len(bake_mocap.JOINTS)
        rng = np.random.default_rng(5)
        rows = rng.normal(0, 0.2, size=(n, cols))
        sym = bake_mocap.symmetric(rows)
        names = [j for j, _ in bake_mocap.JOINTS]
        hl, hr = 3 + 3 * names.index("J_HIP_L"), 3 + 3 * names.index("J_HIP_R")
        # The right hip now does what the left did half a loop before, its y and z turned round.
        np.testing.assert_allclose(sym[:, hr:hr + 3], np.roll(sym[:, hl:hl + 3], -n // 2, axis=0) * [1, -1, -1], atol=1e-12)
        np.testing.assert_allclose(sym[:, 0], -np.roll(sym[:, 0], -n // 2), atol=1e-12)   # the pelvis sways one way, then the other

    def test_setting_the_lean_leaves_the_legs_where_they_swing(self):
        n, cols = 64, 3 + 3 * len(bake_mocap.JOINTS)
        rng = np.random.default_rng(7)
        rows = rng.normal(0, 0.2, size=(n, cols))
        out = bake_mocap.posture(rows, -8, -6)
        names = [j for j, _ in bake_mocap.JOINTS]
        c = {k: 3 + 3 * names.index(k) for k in names}
        trunk = out[:, c["J_PELVIS"]] + out[:, c["J_SPINE"]] + out[:, c["J_CHEST"]]
        self.assertAlmostEqual(float(trunk.mean()), math.radians(-8), places=9)
        gaze = trunk + out[:, c["J_NECK"]] + out[:, c["J_HEAD"]]
        self.assertAlmostEqual(float(gaze.mean()), math.radians(-6), places=9)
        for hip in ("J_HIP_L", "J_HIP_R"):   # pelvis + hip (the leg's swing in the world) unchanged
            np.testing.assert_allclose(out[:, c["J_PELVIS"]] + out[:, c[hip]], rows[:, c["J_PELVIS"]] + rows[:, c[hip]], atol=1e-12)
        np.testing.assert_allclose(np.diff(out, axis=0), np.diff(rows, axis=0), atol=1e-12)   # the motion itself untouched


if __name__ == "__main__":
    unittest.main()
