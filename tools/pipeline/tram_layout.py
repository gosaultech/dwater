# damned_waters/tools/pipeline/tram_layout.py
# Purpose: how long each of an Amsterdam tram's five sections is and where they stand when the night
# has thrown them off the rails. One source for both sides of the pipeline: the Blender model
# (tools/blender/combino.py) and the city generator's colliders and cameras (tools/citygen), so the
# tram you see is the tram you bump into. Pure Python, no Blender.
#
# ELI5: a tram is a row of five boxes on hinges. This file is the tape measure and the hinge maths.
import math

MODULES = (6.2, 6.6, 3.6, 6.6, 6.2)   # m: cab, doors, centre (the pantograph's), doors, cab; 29.2 m in all
GAP = 0.30                            # m: the bellows between two sections
OLD = {0: (0, 1), 1: (2,), 2: (3, 4)}  # a room written for three sections: which of the five each one meant


def lengths(w):
    """The five sections' lengths for a tram `w` metres long over all (the gaps stay as they are)."""
    k = (w - GAP * (len(MODULES) - 1)) / sum(MODULES)
    return [m * k for m in MODULES]


def resample(values, n=len(MODULES)):
    """A per-section list written for any number of sections, read off for `n` (in between: a straight
    line from one to the next); nothing given: zeros."""
    v = list(values or [])
    if not v:
        return [0.0] * n
    if len(v) == n:
        return [float(x) for x in v]
    out = []
    for i in range(n):
        t = i * (len(v) - 1) / (n - 1) if n > 1 else 0.0
        a = min(int(t), len(v) - 2) if len(v) > 1 else 0
        f = t - a
        out.append(float(v[a]) if len(v) == 1 else v[a] * (1 - f) + v[a + 1] * f)
    return out


def spread(indices):
    """Section numbers written for three sections ("dark", "smashed"), as the five's."""
    return sorted({m for i in indices or [] for m in OLD.get(i, ())})


def chain(w, yaws_deg=None):
    """Each section's centre and turn in the tram's own frame (x along it, z across): (x, z, yaw in
    radians, length), the first at the back; every section hinged to the one before at the middle of
    the bellows between them."""
    ls, yaws = lengths(w), resample(yaws_deg)
    cx, cz, joint, out = -w / 2 + ls[0] / 2, 0.0, None, []
    for i, seg in enumerate(ls):
        a = math.radians(yaws[i])
        if joint is not None:
            cx, cz = joint[0] + math.cos(a) * (GAP / 2 + seg / 2), joint[1] - math.sin(a) * (GAP / 2 + seg / 2)
        out.append((cx, cz, a, seg))
        joint = (cx + math.cos(a) * (seg / 2 + GAP / 2), cz - math.sin(a) * (seg / 2 + GAP / 2))
    return out
