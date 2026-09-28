# damned_waters/tools/characters/cast.py
# Purpose: the cast as data + tailoring. Each character = MakeHuman macro settings,
# a skin palette, and an outfit of garments (garments.py) and extras (hair cap,
# beard, straps), plus anchors the engine hangs things on (locs, the backpack,
# the flashlight). Builders return a dwc.Character; build_characters.py writes it.
from __future__ import annotations

from pathlib import Path

import numpy as np

import body as bm
import dwc
import garments as gm
import mhdata
from body import J
from parts import MAT, part_from_quads, rgba


# ── Shared pieces ────────────────────────────────────────────────────────────────
def sphere(center, radius, paint, rings=12, segs=16):
    """UV sphere; paint(dir) -> (mat, rgb); dir (0,0,-1) = the front."""
    P, C, M = [], [], []
    for i in range(rings + 1):
        ph = np.pi * i / rings
        for j in range(segs):
            th = 2 * np.pi * j / segs
            d = np.array([np.sin(ph) * np.sin(th), np.cos(ph), -np.sin(ph) * np.cos(th)])
            P.append(center + d * radius)
            m, c = paint(d)
            M.append(m)
            C.append(rgba(c))
    tris = []
    for i in range(rings):
        for j in range(segs):
            a, b = i * segs + j, i * segs + (j + 1) % segs
            tris += [[a, b, b + segs], [a, b + segs, a + segs]]
    P = np.array(P)
    return P, (P - center) / radius, np.array(C), np.array(M, np.uint8), np.array(tris)


def rigid_part(name, P, N, C, M, tris, joint, region):
    n = len(P)
    jid = np.zeros((n, 4), np.uint8)
    jid[:, 0] = joint
    jw = np.zeros((n, 4), np.float32)
    jw[:, 0] = 1
    return dwc.Part(name, P.astype(np.float32), N.astype(np.float32), C, M, np.full(n, region, np.uint8), jid, jw, tris)


def eyes(b, sclera, iris, pupil=(10, 8, 8), iris_r=0.44, mat_eye=MAT["eye"], mat_iris=MAT["iris"]):
    out = []
    for side, grp in (("l", "helper-l-eye"), ("r", "helper-r-eye")):
        ids = np.unique(b.groups[grp])
        c = b.V[ids].mean(axis=0)
        r = float(np.linalg.norm(b.V[ids] - c, axis=1).mean()) * 0.98

        def paint(d):
            rr = np.hypot(d[0], d[1])
            if d[2] < -0.5 and rr < iris_r * 0.42:
                return mat_iris, pupil
            if d[2] < -0.5 and rr < iris_r:
                return mat_iris, iris
            return mat_eye, sclera
        P, N, C, M, T = sphere(c, r, paint)
        out.append(rigid_part(f"eye_{side}", P, N, C, M, T, J["head"], bm.R_HEAD))
    return out


def helper(b, name, group, mat, col, joint):
    p = part_from_quads(name, b, b.groups[group], mat=mat, col=col)
    p.joints[:] = 0
    p.joints[:, 0] = J[joint]
    p.weights[:] = 0
    p.weights[:, 0] = 1
    p.region[:] = bm.R_JAW if joint == "jaw" else bm.R_HEAD
    return p


class Face:
    """Landmarks measured on the morphed mesh, so features land on this face, not a template."""

    def __init__(self, b):
        V, ids = b.V, b.body_ids
        self.head = b.joints[J["head"]]
        m = ids[b.bone("oris")[ids] > 0.3]
        self.mouth = V[m].mean(axis=0)
        front = ids[(np.abs(V[ids, 0]) < 0.006) & (V[ids, 2] < self.head[2] - 0.03)]
        chin = front[(V[front, 1] < self.mouth[1] - 0.02) & (V[front, 1] > self.mouth[1] - 0.075)]
        self.chin = V[chin[np.argmin(V[chin, 2])]]
        nose = front[(V[front, 1] > self.mouth[1] + 0.015) & (V[front, 1] < self.mouth[1] + 0.07)]
        self.nose = V[nose[np.argmin(V[nose, 2])]]
        self.eyes = [V[np.unique(b.groups[g])].mean(axis=0) for g in ("helper-l-eye", "helper-r-eye")]
        self.top = V[ids].max(axis=0)[1]


def paint_face(b, part, ids, skin, lips, brows, palms=None, face=None):
    """Lips from the orbicularis-oris weights near the mouth line; brows as arcs over the eyes; lighter palms."""
    V = b.V[ids]
    f = face or Face(b)
    col = np.tile(np.array(skin[:3], float), (len(ids), 1))
    mat = part.mat.copy()
    oris = b.bone("oris")[ids]
    dy = V[:, 1] - f.mouth[1]
    ax = np.abs(V[:, 0])
    lip = np.clip((oris - 0.25) * 3, 0, 1) * np.clip(1 - np.abs(dy) / 0.013, 0, 1) * np.clip(1 - (ax - 0.022) / 0.01, 0, 1)
    lip *= (V[:, 2] < f.mouth[2] + 0.02)
    brow = np.zeros(len(ids))
    for e in f.eyes:   # an arc 1.5-2 cm above each eye, thicker toward the nose
        rel = V - e
        along = rel[:, 0] * np.sign(e[0])                     # 0 at the eye, + toward the temple
        yc = 0.017 + 0.004 * np.cos(np.clip(along / 0.03, -1.5, 1.5) * 1.2) - 0.004 * np.clip(along / 0.03, 0, 1)
        thick = 0.0045 - 0.0018 * np.clip(along / 0.03, 0, 1)
        inside = (along > -0.018) & (along < 0.034) & (rel[:, 2] < 0.01)
        brow = np.maximum(brow, inside * np.clip(1 - np.abs(rel[:, 1] - yc) / thick, 0, 1))
    for w, c in ((lip, lips), (np.clip(brow * 1.6, 0, 1), brows)):
        col = col * (1 - w[:, None]) + np.array(c[:3], float) * w[:, None]
    mat[lip > 0.5] = MAT["lips"]
    mat[brow > 0.55] = MAT["brow"]
    if palms is not None:
        hand = b.weight_of("wri_l", "wri_r", "fing1_l", "fing2_l", "thumb_l", "fing1_r", "fing2_r", "thumb_r")[ids]
        inward = -b.N[ids, 0] * np.sign(V[:, 0])
        pw = np.clip(hand * 1.5 - 0.5, 0, 1) * np.clip(inward * 1.6, 0, 1)
        col = col * (1 - pw[:, None]) + np.array(palms[:3], float) * pw[:, None]
    part.col = np.column_stack([np.clip(col, 0, 255), np.full(len(ids), 255)]).astype(np.uint8)
    part.mat = mat


SCALP_LEVELS = (0.108, 0.1, 0.062, 0.046, 0.012, -0.012)


def scalp_field(face, P, levels=SCALP_LEVELS):
    """Height above the hairline (m; > 0 on the scalp). The hairline runs high across the forehead,
    steps down past the temples to the tops of the ears, and down to the nape. Heights are above
    the head joint, at angles 0 (straight ahead), 0.7, 1.2, 1.6 (over the ear), 2.2 and pi (the back)."""
    rel = P - face.head
    ang = np.abs(np.arctan2(rel[:, 0], -(rel[:, 2] + 0.02)))
    return rel[:, 1] - np.interp(ang, [0, 0.7, 1.2, 1.6, 2.2, np.pi], levels)


def scalp_select(b, face, levels=SCALP_LEVELS, margin=0.0):
    """Head vertices above the hairline (see scalp_field), `margin` metres beyond it."""
    head_w = b.weight_of("head", "neck")
    return (head_w > 0.5) & (scalp_field(face, b.V, levels) > -margin) & (b.dominant != J["jaw"])


def hair_cap(b, face, name, color, levels=SCALP_LEVELS, offset=0.003, extra=None):
    """Short hair as a thin shell over the scalp, cut exactly along the hairline. extra(P) > 0 can
    carve it further (a slipped scalp, a parting)."""
    def trim(bb, ids, P):
        s = scalp_field(face, bb.V[ids], levels)
        return np.minimum(s, extra(bb.V[ids])) if extra else s
    return gm.build(b, gm.Garment(name, MAT["hair"], color, lambda bb: scalp_select(bb, face, levels, 0.012), offset, 1, None, None,
                                  hem=0.0015, hides_skin=False, trim=trim))[0]


def scalp_anchors(b, sel, count, seed=1):
    """Farthest-point samples over the scalp: evenly spread roots for locs."""
    ids = np.nonzero(sel & np.isin(np.arange(len(b.V)), b.body_ids))[0]
    rng = np.random.default_rng(seed)
    chosen = [int(rng.choice(ids))]
    d = np.linalg.norm(b.V[ids] - b.V[chosen[0]], axis=1)
    for _ in range(count - 1):
        k = int(np.argmax(d))
        chosen.append(int(ids[k]))
        d = np.minimum(d, np.linalg.norm(b.V[ids] - b.V[ids[k]], axis=1))
    head = b.joints[J["head"]]
    return [dwc.Anchor(f"loc{i}", J["head"], (b.V[v] - head).astype(np.float32), b.N[v].astype(np.float32))
            for i, v in enumerate(chosen)]


def lift(ch: dwc.Character, dy: float):
    """Raise everything (the soles of shoes lift the body)."""
    ch.joints = ch.joints + np.array([0, dy, 0], np.float32)
    for p in ch.parts:
        p.pos = (p.pos + np.array([0, dy, 0], np.float32)).astype(np.float32)


# ── The survivor ─────────────────────────────────────────────────────────────────
def survivor(data: Path) -> dwc.Character:
    """A young man from Amsterdam-Noord trying to get home (director's references: medium locs,
    goatee; a boxy black leather jacket over a cream chunky-knit hoodie, dark jeans, black boots,
    a backpack with the flashlight clipped to its left strap)."""
    macro = mhdata.Macro(gender=1.0, age_years=26, muscle=0.62, weight=0.45, height=0.5, proportions=0.7, african=1.0, caucasian=0.0)
    b = bm.build(data, macro)
    f = Face(b)
    V = b.V
    jp = {n: b.joints[i] for n, i in J.items()}
    skin, lips, brows = (74, 50, 38), (58, 38, 34), (18, 14, 12)
    dom = b.dominant
    arm = np.isin(dom, [J[n] for n in ("sho_l", "elb_l", "sho_r", "elb_r")])
    hand = np.isin(dom, [J[n] for n in ("wri_l", "wri_r", "fing1_l", "fing2_l", "thumb_l", "fing1_r", "fing2_r", "thumb_r")])
    torso = np.isin(dom, [J[n] for n in ("pelvis", "spine", "chest", "neck")])
    legs = np.isin(dom, [J[n] for n in ("hip_l", "kne_l", "ank_l", "hip_r", "kne_r", "ank_r")])
    armhand = arm | hand
    waist_y = jp["pelvis"][1] + 0.05
    hem_hoodie = jp["pelvis"][1] - 0.075
    hem_jacket = jp["pelvis"][1] - 0.085
    collar_y = jp["neck"][1] + 0.035
    cuff_hoodie, cuff_jacket = jp["wri_l"][1] + 0.02, jp["wri_l"][1] + 0.065
    # Upper-body garments are cut by height, not by which joint owns the skin: the skin over the
    # hips and buttocks belongs to the hip joints, and a jacket must cover it all the same.
    upper_to = lambda bb, hem, cuff: (~armhand & (bb.V[:, 1] > hem)) | (armhand & (bb.V[:, 1] > cuff))

    def straight_leg(bb, ids, P):   # straight-cut jeans: the legs fall straight from thigh to ankle
        out = P.copy()
        for s in ("l", "r"):
            side = (bb.V[ids, 0] < 0) if s == "l" else (bb.V[ids, 0] >= 0)
            sel = side & (bb.V[ids, 1] < jp[f"hip_{s}"][1] - 0.04)
            out[sel] = gm.radial_min(bb, ids[sel], out[sel], jp[f"hip_{s}"], jp[f"ank_{s}"] + np.array([0, 0.05, 0]),
                                     lambda t: 0.085 - 0.018 * t)
        return out

    def denim_folds(bb, ids, P, N):
        y = bb.V[ids, 1]
        stack = np.clip((0.2 - y) / 0.12, 0, 1) * 0.0045 * np.sin(y * 95.0 + np.sin(bb.V[ids, 0] * 60) * 1.5)
        knees = np.zeros(len(ids))
        for s in ("l", "r"):
            k = jp[f"kne_{s}"]
            dk = np.abs(y - k[1])
            back = bb.V[ids, 2] > k[2]
            knees += back * np.clip(1 - dk / 0.06, 0, 1) * 0.003 * np.sin(y * 150.0)
        return stack + knees

    torso_c = np.array([0.0, jp["chest"][2] + 0.005])
    torso_ids = lambda bb, ids: ~armhand[ids]   # garment vertices on the body rather than on a sleeve

    def open_w(y):   # half-width of the jacket's open front: narrow at the collar, wider at the hem
        return 0.045 + 0.05 * np.clip((jp["chest"][1] + 0.06 - y) / 0.35, 0, 1)

    def jacket_hang(bb, ids, P):   # boxy: falls straight from the chest, spanning every hollow of the back
        out = P.copy()
        t = torso_ids(bb, ids)
        out[t] = gm.hang_straight(out[t], bb.V[ids][t, 1], jp["chest"][1] - 0.03, torso_c, taper=0.015)
        out[t] = gm.convex_slices(out[t], bb.V[ids][t, 1], torso_c)
        return out

    # Edges are cut, not snapped: each garment is selected a little beyond its lines, then trimmed
    # exactly along them (garments.clip), so hems, cuffs and necklines are clean curves.
    def neck_curve(P, y_back, y_front):
        """A line round the neck, higher at the back than the front, at P's angle round the neck."""
        d = P[:, [0, 2]] - np.array([0.0, jp["neck"][2]])
        c = d[:, 1] / np.maximum(np.linalg.norm(d, axis=1), 1e-6)       # +1 at the back, -1 at the front
        return y_front + (y_back - y_front) * (0.5 + 0.5 * c)

    def hem_and_cuffs(ids, P, hem, cuff):   # > 0 above the hem on the body, above the cuff on the sleeves
        return np.where(armhand[ids], P[:, 1] - cuff, P[:, 1] - hem)

    def hoodie_trim(bb, ids, P):
        return np.minimum(hem_and_cuffs(ids, P, hem_hoodie, cuff_hoodie), neck_curve(P, collar_y + 0.004, collar_y - 0.012) - P[:, 1])

    def jacket_trim(bb, ids, P):
        front = ~armhand[ids] & (P[:, 2] < torso_c[1] - 0.04)
        opening = np.where(front, np.abs(P[:, 0]) - open_w(P[:, 1]), 1.0)
        neckline = neck_curve(P, jp["neck"][1] + 0.012, jp["neck"][1] - 0.03) - P[:, 1]   # sits at the base of the neck
        return np.minimum(np.minimum(hem_and_cuffs(ids, P, hem_jacket, cuff_jacket), neckline), opening)

    # The hood lies on the back, seen from behind as a U: wide at the collar, a rounded point below.
    # It hangs from the neckline, so its top edge curves down round the neck instead of sitting
    # level across the shoulders.
    hood_top, hood_bot = jp["neck"][1] + 0.045, jp["chest"][1] - 0.035
    hood_w = lambda y: 0.09 * np.sqrt(np.clip((y - hood_bot) / (hood_top - hood_bot) * 1.7, 0, 1))
    hood_line = lambda x: hood_top - 3.2 * x ** 2
    hood_trim = lambda bb, ids, P: np.minimum(hood_line(P[:, 0]) + 0.004 - P[:, 1], hood_w(P[:, 1]) + 0.004 - np.abs(P[:, 0]))

    def jeans_trim(bb, ids, P):   # a clean waistband and hems that break over the boots
        return np.minimum(P[:, 1] - 0.105, np.where(legs[ids], 1.0, waist_y - P[:, 1]))

    strap_x = lambda y: 0.088 + 0.05 * np.clip((jp["chest"][1] + 0.1 - y) / 0.23, 0, 1) ** 2   # strap centre, out toward the armpit

    def by_arm(torso_off, arm_off):   # per-vertex offset: sleeves sit closer to the arm than the body panels
        return lambda bb, ids: torso_off + (arm_off - torso_off) * bb.weight_of("sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r")[ids]

    def leather_creases(bb, ids, P, N):
        out = np.zeros(len(ids))
        for s in ("l", "r"):
            e = jp[f"elb_{s}"]
            d = np.linalg.norm(bb.V[ids] - e, axis=1)
            out += np.clip(1 - d / 0.1, 0, 1) * 0.004 * np.sin(bb.V[ids, 1] * 160.0 + bb.V[ids, 2] * 40)
            sh = jp[f"sho_{s}"]
            d = np.linalg.norm(bb.V[ids] - sh, axis=1)
            out += np.clip(1 - d / 0.12, 0, 1) * 0.002 * np.sin(bb.V[ids, 0] * 120.0)
        back = (bb.V[ids, 2] > torso_c[1]) * np.clip(1 - np.abs(bb.V[ids, 0]) / 0.16, 0, 1)   # wrinkles across the small of the back
        out += back * np.clip(1 - np.abs(bb.V[ids, 1] - hem_jacket - 0.12) / 0.07, 0, 1) * 0.002 * np.sin(bb.V[ids, 1] * 95)
        return out

    def knit_bulk(bb, ids, P, N):
        y = bb.V[ids, 1]
        out = gm.knit_rib(bb.V[ids], hem_hoodie - 0.01, hem_hoodie + 0.05, 0.003)                          # ribbed hem
        out += 0.003 * np.sin(y * 110.0) * np.clip((y - hem_hoodie - 0.06) / 0.1, 0, 1) * (bb.V[ids, 2] < torso_c[1])
        for s in ("l", "r"):
            w = jp[f"wri_{s}"]
            forearm = armhand[ids] & (np.sign(bb.V[ids, 0]) == np.sign(w[0])) & (y < jp[f"elb_{s}"][1])
            cuff = forearm & (np.abs(y - (w[1] + 0.045)) < 0.035)
            out -= cuff * 0.005
            out += forearm * 0.002 * np.sin(y * 140.0)                                                     # pushed-up sleeves
        neck = np.clip(1 - np.abs(y - (jp["neck"][1] + 0.0)) / 0.05, 0, 1)
        out += neck * 0.008
        return out

    def hood_puff(bb, ids, P, N):   # the hood lies folded on the back: fullest in the middle
        rel = bb.V[ids] - np.array([0, jp["chest"][1] + 0.1, 0])
        return 0.022 * np.clip(1 - (rel[:, 0] / 0.13) ** 2 - (rel[:, 1] / 0.12) ** 2, 0, 1)

    def boot_shape(bb, ids, P):
        out = P.copy()
        low = bb.V[ids, 1] < 0.02
        out[low, 1] = -0.022                                   # flat sole, as thick as the lift
        heel = low & (bb.V[ids, 2] > jp["ank_l"][2] + 0.02)
        out[heel, 2] += 0.006
        return out

    front_open = lambda P: (P[:, 2] < torso_c[1] - 0.02) & (np.abs(P[:, 0]) < open_w(P[:, 1]) - 0.03)   # well inside the trim line
    garments = [
        gm.Garment("jeans", MAT["denim"], (34, 40, 54), lambda bb: (legs | (torso & (bb.V[:, 1] < waist_y + 0.03))) & ~hand & (bb.V[:, 1] > 0.07),
                   0.006, 3, straight_leg, denim_folds, trim=jeans_trim),
        gm.Garment("hoodie", MAT["knit"], (214, 202, 176), lambda bb: upper_to(bb, hem_hoodie - 0.03, cuff_hoodie - 0.03) & (bb.V[:, 1] < collar_y + 0.03),
                   by_arm(0.013, 0.0105), 4, None, knit_bulk, hem=0.005, tension=12, trim=hoodie_trim),
        gm.Garment("jacket", MAT["leather"], (20, 19, 20), lambda bb: upper_to(bb, hem_jacket - 0.03, cuff_jacket - 0.03) & (bb.V[:, 1] < collar_y + 0.01)
                   & ~front_open(bb.V), by_arm(0.034, 0.021), 6, jacket_hang, leather_creases, hem=0.007, tension=45, trim=jacket_trim),
        gm.Garment("hood", MAT["knit"], (208, 196, 170), lambda bb: (torso | np.isin(bb.dominant, [J["neck"]])) & (bb.V[:, 2] > jp["neck"][2] + 0.025)
                   & (bb.V[:, 1] > hood_bot - 0.02) & (bb.V[:, 1] < hood_line(bb.V[:, 0]) + 0.03) & (np.abs(bb.V[:, 0]) < hood_w(bb.V[:, 1]) + 0.03),
                   0.047, 5, None, hood_puff, hem=0.012, hides_skin=False, trim=hood_trim),
    ]
    hidden = np.zeros(len(b.body_quads), bool)
    parts = []
    for g in garments:
        p, h = gm.build(b, g)
        parts.append(p)
        hidden |= h
    # Backpack straps, laid on the jacket itself: over the top of each shoulder and down the chest,
    # curving out toward the armpits (where they'd run back under the arms to the pack).
    jacket = next(p for p in parts if p.name == "jacket")
    strap_lo, strap_w = jp["chest"][1] - 0.13, 0.024
    strap_in = lambda P: np.minimum(strap_w - np.abs(np.abs(P[:, 0]) - strap_x(P[:, 1])), P[:, 1] - strap_lo)   # > 0 on the webbing
    parts.append(gm.clip_overlay(b, jacket, "straps", MAT["cloth"], (66, 68, 54), strap_in, lift=0.008, hem=0.005))
    for sd in ("l", "r"):   # boots, and the feet they hide
        parts.append(gm.shoe(b, sd, f"boot_{sd}", MAT["leather"], (26, 24, 24), MAT["rubber"], (16, 15, 15)))
        feet = np.isin(b.dominant[b.body_quads], [J[f"ank_{sd}"]]).all(axis=1) & (V[b.body_quads][:, :, 1].max(axis=1) < 0.12)
        hidden |= feet
    # The body, minus skin that clothes cover (no poke-through, less to draw).
    body_quads = b.body_quads[~hidden]
    bodyp = part_from_quads("body", b, body_quads, mat=MAT["skin"], col=skin)
    paint_face(b, bodyp, np.unique(body_quads), skin, lips, brows, palms=(140, 102, 82), face=f)
    bid = np.unique(body_quads)   # stubble: a shadow along the jaw and chin
    relj = V[bid] - f.mouth
    stub = (b.weight_of("jaw")[bid] > 0.3) & (relj[:, 1] < -0.004) & (relj[:, 2] < 0.07)
    bodyp.col[stub, :3] = (bodyp.col[stub, :3] * 0.72).astype(np.uint8)
    parts.insert(0, bodyp)
    # Hair: a short dark cap between the locs, and a goatee, both cut along smooth lines.
    scalp = scalp_select(b, f)
    parts.append(hair_cap(b, f, "hair_cap", (20, 16, 13)))

    def beard_field(P):   # > 0 on the goatee: the chin, a short moustache, joined at the corners of the mouth (m)
        rel = P - f.mouth
        ax, y, z = np.abs(rel[:, 0]), rel[:, 1], rel[:, 2]
        chin = np.minimum.reduce([0.024 + 0.006 * np.clip(-y / 0.03, 0, 1) - ax, -0.009 - y, y - (f.chin[1] - f.mouth[1] - 0.022), 0.02 - z])
        stache = np.minimum.reduce([0.024 - ax, y - 0.008, 0.016 - y, 0.004 - z])
        sides = np.minimum.reduce([ax - 0.019, 0.028 - ax, y + 0.02, 0.012 - y, 0.012 - z])
        return np.maximum.reduce([chin, stache, sides])
    face_skin = np.isin(np.arange(len(V)), b.body_ids) & (b.weight_of("head", "jaw") > 0.5)
    parts.append(gm.build(b, gm.Garment("goatee", MAT["hair"], (14, 11, 10), lambda bb: face_skin & (beard_field(bb.V) > -0.006), 0.0025, 1,
                                        None, None, hem=0.0015, hides_skin=False, trim=lambda bb, ids, P: beard_field(bb.V[ids])))[0])
    parts += eyes(b, sclera=(196, 186, 172), iris=(40, 24, 16), iris_r=0.5)
    parts.append(helper(b, "teeth_up", "helper-upper-teeth", MAT["tooth"], (230, 224, 206), "head"))
    parts.append(helper(b, "teeth_lo", "helper-lower-teeth", MAT["tooth"], (230, 224, 206), "jaw"))
    parts.append(helper(b, "tongue", "helper-tongue", MAT["tongue"], (150, 80, 82), "jaw"))
    anchors = scalp_anchors(b, scalp, 84, seed=7)
    for sx in (-1, 1):   # hoodie drawstrings hang from the neckline
        at = np.array([0.028 * sx, jp["neck"][1] - 0.035, 0])
        near = b.body_ids[np.argmin(np.linalg.norm(V[b.body_ids][:, [0, 1]] - at[[0, 1]], axis=1) + (V[b.body_ids][:, 2] > 0) * 9)]
        at[2] = V[near, 2] - 0.026   # on the outside of the knit
        anchors.append(dwc.Anchor(f"drawstring{sx}", J["chest"], (at - jp["chest"]).astype(np.float32), np.array([0, -1, 0], np.float32)))
    chest = b.joints[J["chest"]]
    back = V[b.body_ids][np.argmax(V[b.body_ids, 2] * (np.abs(V[b.body_ids, 0]) < 0.03) * (np.abs(V[b.body_ids, 1] - (chest[1] + 0.03)) < 0.03))]
    anchors.append(dwc.Anchor("backpack", J["chest"], (back - chest).astype(np.float32), np.array([0, 0, 1], np.float32)))
    strap = np.array([-0.095, chest[1] + 0.02, 0])
    strap[2] = V[b.body_ids][np.argmin(np.linalg.norm(V[b.body_ids][:, [0, 1]] - strap[[0, 1]], axis=1) + (V[b.body_ids][:, 2] > 0) * 9), 2]
    anchors.append(dwc.Anchor("flashlight", J["chest"], (strap - chest + np.array([0, 0, -0.045])).astype(np.float32),
                              np.array([0, 0, -1], np.float32)))
    ch = dwc.Character(b.joints.astype(np.float32), parts, anchors)
    lift(ch, 0.022)   # boot soles
    return ch


CAST = {"survivor": survivor}
