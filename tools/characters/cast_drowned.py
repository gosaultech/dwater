# damned_waters/tools/characters/cast_drowned.py
# Purpose: the Drowned, ordinary Amsterdammers the canals gave back. Each one is a
# person first (what they had on the day they went into the water: an office shirt, a
# dress, a sweater, a rain jacket) and a corpse second (drowned.py does the ruin). The
# engine adds what hangs or grows (engine/src/cast_citizens.cpp): guts, the tongue, the
# tie, loose skin, mussels, weed, wet hair; it finds them by the anchors made here.
from __future__ import annotations

from pathlib import Path

import numpy as np

import body as bm
import drowned as dr
import dwc
import garments as gm
import mhdata
from body import J
from cast import Face, brow_field, eyeball, eyes, hair_cap, helper, lift, rigid_part, scalp_anchors, scalp_field, scalp_select
from parts import MAT


# ── Shared ───────────────────────────────────────────────────────────────────────
def landmarks(b: bm.Body):
    """Joint positions by name, and body masks by what the skin belongs to."""
    jp = {n: b.joints[i] for n, i in J.items()}
    dom = b.dominant
    return jp, dict(
        arm=np.isin(dom, [J[n] for n in ("sho_l", "elb_l", "sho_r", "elb_r")]),
        hand=np.isin(dom, [J[n] for n in ("wri_l", "wri_r", "fing1_l", "fing2_l", "thumb_l", "fing1_r", "fing2_r", "thumb_r")]),
        torso=np.isin(dom, [J[n] for n in ("pelvis", "spine", "chest", "neck")]),
        legs=np.isin(dom, [J[n] for n in ("hip_l", "kne_l", "ank_l", "hip_r", "kne_r", "ank_r")]),
    )


def surface_anchor(b: bm.Body, name: str, target, lift: float = 0.0, joint: str | None = None) -> dwc.Anchor:
    """An anchor on the skin nearest `target`, lifted `lift` metres off it (over clothes), in its joint's space."""
    ids = b.body_ids
    v = ids[np.argmin(np.linalg.norm(b.V[ids] - np.asarray(target, float), axis=1))]
    j = J[joint] if joint else int(b.dominant[v])
    p = b.V[v] + b.N[v] * lift
    return dwc.Anchor(name, j, (p - b.joints[j]).astype(np.float32), b.N[v].astype(np.float32))


def on_garment(b: bm.Body, part: dwc.Part, name: str, x: float, y: float, lift: float) -> dwc.Anchor:
    """An anchor lying on a garment's front at (x, y), lifted `lift` off it (a tie knot, a staff
    pass), riding the joint that moves the skin beneath."""
    src, _, P, N, _ = part.shell
    near = np.nonzero((np.abs(P[:, 0] - x) < 0.012) & (np.abs(P[:, 1] - y) < 0.012))[0]
    k = near[np.argmin(P[near, 2])]                       # the frontmost point there
    j = int(b.dominant[src[k]])
    return dwc.Anchor(name, j, (P[k] + N[k] * lift - b.joints[j]).astype(np.float32), N[k].astype(np.float32))


def corpse(b: bm.Body, f: Face, w: dr.Wounds, garments: list, skin, degloved: float, shoes=(), seed: int = 0,
           hair: list | None = None, repaint=None, missing_eye: str | None = None, scream: bool = False) -> list[dwc.Part]:
    """Dress the body, cut its wounds, paint it drowned; add the dead eyes, teeth and tongue.
    garments: gm.Garment specs, or finished parts (a skirt from a helper mesh) that hide no skin.
    shoes: (side, gm.shoe keyword args) pairs; the feet inside are hidden.
    repaint(part, ids): a last pass over the skin (a slipped scalp, a tattoo).
    missing_eye: "l" or "r": the canal took that eye; the socket is left empty.
    scream: the death mask (built with dr.death_mask): the mouth's back is cut open onto a black
    throat, and the eyes roll up and sink."""
    hidden = np.zeros(len(b.body_quads), bool)
    parts = []
    for g in garments:
        if isinstance(g, dwc.Part):
            parts.append(g)
            continue
        p, h = gm.build(b, g)
        parts.append(p)
        hidden |= h
    for sd, spec in shoes:
        spec = dict(spec)
        top = spec.get("shaft_top", 0.15)
        parts.append(gm.shoe(b, sd, f"shoe_{sd}", **spec))
        foot = np.isin(b.dominant[b.body_quads], [J[f"ank_{sd}"]]).all(axis=1)
        hidden |= foot & (b.V[b.body_quads][:, :, 1].max(axis=1) < top - 0.01)
    if scream:
        hidden |= dr.mouth_back(b, f)
    bodyp, src, wall = dr.skin(b, b.body_quads[~hidden], w)
    empty = None if missing_eye is None else "lr".index(missing_eye)
    dr.paint_body(b, bodyp, src, f, skin, w, degloved, seed, wall=wall, empty_socket=empty)
    if repaint:
        repaint(bodyp, src)
    parts.insert(0, bodyp)
    parts += hair or []
    # Clouded eyes: a yellowed white, the iris a grey-blue ghost under a milky film. An empty
    # socket gets a small black ball set deep behind the lids, so it reads as a hole.
    for e in eyes(b, sclera=(46, 40, 38), iris=(128, 134, 134), pupil=(150, 156, 154), iris_r=0.5,
                  mat_eye=MAT["dead_eye"], mat_iris=MAT["dead_eye"], limbus=(90, 96, 98), veins=(52, 30, 30),
                  look_up=10.0 if scream else 0.0, sink=0.006 if scream else 0.0):
        if e.name == f"eye_{missing_eye}":
            c = e.pos.mean(axis=0)
            e.pos = (c + (e.pos - c) * 0.8 + np.array([0, 0, 0.008])).astype(np.float32)
            e.col[:, :3] = 0
            e.mat[:] = MAT["void"]
        parts.append(e)
    parts.append(helper(b, "teeth_up", "helper-upper-teeth", MAT["tooth"], (160, 140, 100), "head"))   # stained
    parts.append(helper(b, "teeth_lo", "helper-lower-teeth", MAT["tooth"], (142, 122, 88), "jaw"))
    parts.append(helper(b, "tongue", "helper-tongue", MAT["tongue"], (70, 34, 52), "jaw"))
    if scream:   # the throat: a black hollow behind the lips, so the scream is a hole
        c = f.mouth + np.array([0.0, -0.01, 0.052])
        P, N, C, M, T = eyeball(np.zeros(3), 1.0, lambda d: (MAT["void"], (0, 0, 0)), [0, 30, 60, 90, 120, 150, 180], segs=16)
        parts.append(rigid_part("throat", c + P * np.array([0.03, 0.036, 0.024]), N, C, M, T, J["head"], bm.R_HEAD))
    return parts


def gore_anchors(b: bm.Body, f: Face, w: dr.Wounds, degloved: float, tongue: bool = True) -> list[dwc.Anchor]:
    """Where the engine hangs the guts, the lolling tongue (not in a scream) and the loose skin of
    the degloved hand."""
    out = []
    spine = b.joints[J["spine"]]
    if w.belly_shape[0] > 1e-3:   # only a split belly lets the guts out
        out.append(dwc.Anchor("guts", J["spine"], (w.belly_centre + np.array([0, -0.01, 0.025]) - spine).astype(np.float32),
                              np.array([0, -0.3, -1], np.float32)))
    if tongue:
        t = np.unique(b.groups["helper-tongue"])
        tip = b.V[t[np.argmin(b.V[t, 2])]]
        out.append(dwc.Anchor("tongue", J["jaw"], (tip - b.joints[J["jaw"]]).astype(np.float32), np.array([0, -0.3, -1], np.float32)))
    sd = "l" if degloved < 0 else "r"
    out.append(dwc.Anchor("loose_skin", J[f"wri_{sd}"], np.array([0, -0.05, 0], np.float32), np.array([0, -1, 0], np.float32)))
    return out


def drip_anchors(b: bm.Body, f: Face, parts: list, hems: tuple = ()) -> list[dwc.Anchor]:
    """Where water still runs off the body (the engine drops a drip from each now and then): the
    lowest point of each hand, the chin, and three points spread round the bottom of each named
    garment's hem."""
    out = []
    body_v = np.zeros(len(b.V), bool)
    body_v[b.body_ids] = True
    for sd in ("l", "r"):
        hand = body_v & np.isin(b.dominant, [J[f"{n}_{sd}"] for n in ("wri", "fing1", "fing2", "thumb")])
        v = np.nonzero(hand)[0][np.argmin(b.V[hand, 1])]
        j = int(b.dominant[v])
        out.append(dwc.Anchor(f"drip_hand_{sd}", j, (b.V[v] - b.joints[j]).astype(np.float32), np.array([0, -1, 0], np.float32)))
    out.append(dwc.Anchor("drip_chin", J["jaw"], (f.chin - b.joints[J["jaw"]]).astype(np.float32), np.array([0, -1, 0], np.float32)))
    for name in hems:
        p = next(q for q in parts if q.name == name)
        low = np.nonzero(p.pos[:, 1] < p.pos[:, 1].min() + 0.012)[0]
        ang = np.arctan2(p.pos[low, 0], p.pos[low, 2])
        for k, a in enumerate((-2.2, 0.0, 2.2)):   # front-left, back, front-right
            v = low[np.argmin(np.abs(np.angle(np.exp(1j * (ang - a)))))]
            j = int(p.joints[v, 0])
            out.append(dwc.Anchor(f"drip_{name}{k}", j, (p.pos[v] - b.joints[j]).astype(np.float32), np.array([0, -1, 0], np.float32)))
    return out


# ── Jeroen, the office worker ────────────────────────────────────────────────────
def neck_curve(jp, P, y_back, y_front):
    """A line round the neck, higher at the back than the front, at P's angle round the neck."""
    d = P[:, [0, 2]] - np.array([0.0, jp["neck"][2]])
    c = d[:, 1] / np.maximum(np.linalg.norm(d, axis=1), 1e-6)       # +1 at the back, -1 at the front
    return y_front + (y_back - y_front) * (0.5 + 0.5 * c)


def office_worker(data: Path) -> dwc.Character:
    """Jeroen, 48, a civil servant: a pale blue office shirt with the collar open and the tie
    pulled loose, charcoal suit trousers and a belt, a lanyard with his pass, one black shoe (the
    canal kept the other). Torn on his right side; his left hand degloved."""
    side, seed = 1.0, 3
    b = bm.build(data, mhdata.Macro(gender=1.0, age_years=48, muscle=0.35, weight=0.72, height=0.55, proportions=0.4,
                                    caucasian=1.0), dr.bloat(1.0, dr.death_mask(1.0, crooked=side)))
    dr.distort(b, Face(b), crooked=side)
    f = Face(b)
    jp, G = landmarks(b)
    armhand = G["arm"] | G["hand"]
    w = dr.wounds(b, f, side, seed, cheek=False)
    skin = (80, 86, 94)
    waist_y = jp["pelvis"][1] + 0.035
    collar_y = jp["neck"][1] + 0.028
    vee_y = jp["neck"][1] - 0.075          # the second button: the collar hangs open to here
    front_z = jp["chest"][2]
    badge_y = jp["chest"][1] - 0.07
    cuff_y = jp["wri_l"][1] + 0.012
    blood = dr.drool(f, 0.34) + [(w.belly_centre, 0.14)]
    tear = lambda P, margin: w.belly_field(P) - (1.0 + margin)       # > 0 where the cloth survived

    def shirt_trim(bb, ids, P):
        cuffs = np.where(armhand[ids], P[:, 1] - cuff_y, 1.0)
        neckline = neck_curve(jp, P, collar_y, collar_y - 0.012) - P[:, 1]
        vee = np.where((P[:, 2] < front_z - 0.02) & (P[:, 1] > vee_y), np.abs(P[:, 0]) - (0.006 + 0.5 * (P[:, 1] - vee_y)), 1.0)
        tucked = np.where(armhand[ids], 1.0, P[:, 1] - (waist_y - 0.02))   # ends under the belt, never through the trousers
        return np.minimum.reduce([cuffs, neckline, vee, tucked, tear(P, 0.45)])

    def trouser_trim(bb, ids, P):
        waist = np.where(G["legs"][ids], 1.0, waist_y - P[:, 1])
        return np.minimum.reduce([P[:, 1] - 0.045, waist, tear(P, 0.3)])

    def shirt_folds(bb, ids, P, N):   # wet cotton clings, bunching where it's tucked in and at the elbows
        y = bb.V[ids, 1]
        out = 0.004 * np.sin(y * 70 + np.sin(bb.V[ids, 0] * 40) * 2) * np.clip((waist_y + 0.08 - y) / 0.08, 0, 1)
        for s_ in ("l", "r"):
            d = np.linalg.norm(bb.V[ids] - jp[f"elb_{s_}"], axis=1)
            out += np.clip(1 - d / 0.07, 0, 1) * 0.003 * np.sin(y * 180)
        return out

    garments = [
        gm.Garment("trousers", MAT["wool"], (52, 54, 60),
                   lambda bb: (G["legs"] | (G["torso"] & (bb.V[:, 1] < waist_y + 0.03))) & ~G["hand"] & (bb.V[:, 1] > 0.02),
                   0.011, 3, gm.straight_legs(jp, 0.088, 0.07), None, hem=0.004,
                   tint=dr.canal_tint((52, 54, 60), mud_top=0.75, seed=seed), aux=dr.soaked(seed + 1), trim=trouser_trim),
        gm.Garment("shirt", MAT["cotton"], (160, 184, 204),
                   lambda bb: ((~armhand & (bb.V[:, 1] > waist_y - 0.06)) | (armhand & (bb.V[:, 1] > cuff_y - 0.03)))
                   & (bb.V[:, 1] < collar_y + 0.03),
                   gm.per_arm(0.009, 0.008), 2, None, shirt_folds, hem=0.003, tension=8,
                   tint=dr.canal_tint((160, 184, 204), mud_top=0.9, blood=blood, seed=seed + 1), aux=dr.soaked(seed + 2), trim=shirt_trim),
        gm.Garment("belt", MAT["leather"], (24, 22, 20),
                   lambda bb: ~armhand & (np.abs(bb.V[:, 1] - (waist_y - 0.013)) < 0.03),
                   0.016, 2, None, None, hem=0.004, hides_skin=False,
                   aux=dr.soaked(seed + 3), trim=lambda bb, ids, P: np.minimum(0.016 - np.abs(P[:, 1] - (waist_y - 0.013)), tear(P, 0.3))),
    ]
    # Short thinning hair, the front of the scalp slid away with the skin.
    levels = (0.112, 0.104, 0.066, 0.05, 0.016, -0.008)
    slip = lambda P: -((P - f.head)[:, 2] + 0.03 + 0.012 * np.sin((P - f.head)[:, 0] * 90 + seed))   # > 0 behind the tear
    hair = [hair_cap(b, f, "hair_cap", (62, 56, 48), levels, offset=0.003, extra=slip, fade=0.012, thin=0.3)]
    bare_field = lambda P: np.minimum(scalp_field(f, P, levels), -slip(P))   # > 0 on the bare scalp

    def repaint(part, ids):   # the bare scalp: bleached and blotched; raw along the tear
        V = b.V[ids]
        bare = np.clip(bare_field(V) / 0.006, 0, 1)
        edge = np.clip(1 - np.abs(slip(V)) / 0.008, 0, 1) * (scalp_field(f, V, levels) > -0.004)
        col = part.col[:, :3].astype(float)
        col = dr.mix(col, dr.mix(np.array(dr.SLOUGH, float) * 0.92, col, 0.3), bare * 0.85)
        col = dr.mix(col, dr.mix(np.array(dr.RAW, float), dr.DRIED, 0.5), np.clip(edge * 1.3, 0, 1) * 0.85)
        brow = np.clip(brow_field(f, V) / 0.002 + 0.5, 0, 1) * (dr.value_noise(V * 300.0, seed) > 0.4)
        col = dr.mix(col, np.array([66, 60, 52], float), brow * 0.75)   # brows washed thin and patchy
        part.col[:, :3] = np.clip(col, 0, 255).astype(np.uint8)

    shoes = [("r", dict(mat=MAT["leather"], color=(22, 20, 20), sole_mat=MAT["rubber"], sole_color=(18, 16, 16), sole=0.014,
                        margin=0.007, shaft_top=0.075))]
    parts = corpse(b, f, w, garments, skin, degloved=-side, shoes=shoes, seed=seed, hair=hair, repaint=repaint, scream=True)
    shirt = next(p for p in parts if p.name == "shirt")
    # An open shirt collar (its points either side of the V) and a lanyard lying on the shirt.
    parts.append(gm.collar(b, shirt, "collar", MAT["cotton"], (150, 172, 192), jp["neck"], above=vee_y + 0.03,
                           stand=0.026, fall=0.038, point=0.05))
    # The tie, pulled loose: its knot at the second button, the blade lying on the shirt and slewed
    # to his left, off the split belly, the tip down at his belt. Wet burgundy polyester.
    knot_y = vee_y + 0.006
    tie_len = knot_y - (waist_y + 0.02)

    def tie(P):
        t = np.clip((knot_y - P[:, 1]) / tie_len, 0, 1.2)
        dx = np.abs(P[:, 0] + 0.07 * side * t ** 1.6)
        hw = 0.016 + 0.022 * np.clip(t, 0, 1)                               # widening toward the blade
        point = (P[:, 1] - (knot_y - tie_len) + 0.034) - dx * 0.9          # ...which ends in a point
        return np.where(P[:, 2] < front_z, np.minimum.reduce([hw - dx, point, knot_y - P[:, 1]]), -1.0)

    tie_col = lambda P: np.array([80, 20, 30], float) * (0.8 + 0.3 * dr.value_noise(P * 25.0, seed + 4))[:, None]
    parts.append(gm.clip_overlay(b, shirt, "tie", MAT["nylon"], (80, 20, 30), tie, lift=0.0035, hem=0.002, detail=1, tint=tie_col,
                                 wet=0.9))
    # The lanyard round his neck, over the tie, to the staff pass on his chest.
    lan_x = lambda y: 0.058 * np.clip((y - badge_y) / (jp["neck"][1] - badge_y), 0, 1)
    lanyard = lambda P: np.where(P[:, 2] < front_z, np.minimum.reduce([0.0065 - np.abs(np.abs(P[:, 0]) - lan_x(P[:, 1])),
                                                                     P[:, 1] - badge_y, jp["neck"][1] - 0.01 - P[:, 1]]), -1.0)
    parts.append(gm.clip_overlay(b, shirt, "lanyard", MAT["cloth"], (36, 58, 116), lanyard, lift=0.006, hem=0.0015, detail=2,
                                 wet=0.9))
    anchors = gore_anchors(b, f, w, -side, tongue=False) + drip_anchors(b, f, parts, ("trousers",))
    anchors += [
        on_garment(b, shirt, "tie", 0.0, knot_y + 0.004, lift=0.007),
        on_garment(b, shirt, "badge", 0.0, badge_y - 0.046, lift=0.009),
        surface_anchor(b, "mussels0", jp["sho_l"] + np.array([-0.02, 0.05, 0.0]), lift=0.014),
        surface_anchor(b, "mussels1", jp["hip_r"] + np.array([0.04, -0.14, -0.05]), lift=0.013),
        surface_anchor(b, "mussels2", jp["head"] + np.array([-0.075, 0.07, 0.035])),
        surface_anchor(b, "weed0", jp["ank_l"] + np.array([0, 0.07, 0.05]), lift=0.013),
        surface_anchor(b, "weed1", jp["pelvis"] + np.array([0.08, 0.0, 0.1]), lift=0.02),
    ]
    return dwc.Character(b.joints.astype(np.float32), parts, anchors)


# ── Pieter, the pensioner in his sweater ─────────────────────────────────────────
def pieter(data: Path) -> dwc.Character:
    """Pieter, 67, heavy, retired: a navy cable-knit sweater, faded jeans and a brown belt, white
    trainers. Bald with a grey fringe. The canal has had one eye; his scream tore the corner of his
    mouth back along the cheek; his belly split through the sweater, his right hand degloved."""
    side, seed = -1.0, 11
    b = bm.build(data, mhdata.Macro(gender=1.0, age_years=67, muscle=0.3, weight=0.85, height=0.45, proportions=0.3,
                                    caucasian=1.0), dr.bloat(1.15, dr.death_mask(1.0, crooked=side)))
    dr.distort(b, Face(b), crooked=side)
    f = Face(b)
    jp, G = landmarks(b)
    armhand = G["arm"] | G["hand"]
    w = dr.wounds(b, f, side, seed, belly=0.8, cheek_at=(0.03, -0.002, 0.012), cheek_size=(0.008, 0.026))   # the scream tore the corner
    skin = (84, 88, 92)
    waist_y = jp["pelvis"][1] + 0.04
    hem_y = jp["pelvis"][1] - 0.07
    collar_y = jp["neck"][1] + 0.03
    cuff_y = jp["wri_l"][1] + 0.02
    sole = 0.022
    blood = dr.drool(f, 0.3) + [(w.belly_centre, 0.16)]
    tear = lambda P, margin: w.belly_field(P) - (1.0 + margin)

    def sweater_trim(bb, ids, P):
        hem_cuff = np.where(armhand[ids], P[:, 1] - cuff_y, P[:, 1] - hem_y)
        crew = neck_curve(jp, P, collar_y + 0.004, collar_y - 0.022) - P[:, 1]
        return np.minimum.reduce([hem_cuff, crew, tear(P, 0.5)])

    def knit_bulk(bb, ids, P, N):   # ribbed hem, cuffs and neck hug; the body of the knit bags a little
        y = bb.V[ids, 1]
        out = gm.knit_rib(bb.V[ids], hem_y - 0.01, hem_y + 0.045, 0.004)
        for sd in ("l", "r"):
            wr = jp[f"wri_{sd}"]
            forearm = armhand[ids] & (np.sign(bb.V[ids, 0]) == np.sign(wr[0])) & (y < jp[f"elb_{sd}"][1])
            out -= (forearm & (np.abs(y - (wr[1] + 0.04)) < 0.03)) * 0.004
            out += forearm * 0.002 * np.sin(y * 130.0)
        return out + np.clip(1 - np.abs(y - collar_y + 0.01) / 0.03, 0, 1) * 0.005

    def jeans_trim(bb, ids, P):
        return np.minimum.reduce([P[:, 1] - 0.08, np.where(G["legs"][ids], 1.0, waist_y - P[:, 1])])

    def jeans_tint(bb, ids, P):   # faded pale down the thighs and at the knees, canal mud from the hems
        base = dr.canal_tint((84, 104, 132), mud_top=0.6, wet=0.78, seed=seed)(bb, ids, P)
        fade = np.zeros(len(ids))
        for sd in ("l", "r"):
            h, k = jp[f"hip_{sd}"], jp[f"kne_{sd}"]
            thigh = np.exp(-((P[:, 0] - h[0]) / 0.06) ** 2 - ((P[:, 1] - (h[1] + k[1]) / 2) / 0.13) ** 2)
            fade += (P[:, 2] < h[2]) * (0.35 * thigh + 0.25 * np.exp(-((P[:, 1] - k[1]) / 0.05) ** 2))
        return base * (1 + fade[:, None])

    garments = [
        gm.Garment("jeans", MAT["denim"], (84, 104, 132),
                   lambda bb: (G["legs"] | (G["torso"] & (bb.V[:, 1] < waist_y + 0.03))) & ~G["hand"] & (bb.V[:, 1] > 0.05),
                   0.009, 3, gm.straight_legs(jp, 0.1, 0.078), None, hem=0.004, tint=jeans_tint, aux=dr.soaked(seed + 4), trim=jeans_trim),
        gm.Garment("sweater", MAT["knit"], (38, 46, 70),
                   lambda bb: ((~armhand & (bb.V[:, 1] > hem_y - 0.03)) | (armhand & (bb.V[:, 1] > cuff_y - 0.03)))
                   & (bb.V[:, 1] < collar_y + 0.03),
                   gm.per_arm(0.015, 0.012), 4, None, knit_bulk, hem=0.005, tension=12,
                   tint=dr.canal_tint((38, 46, 70), mud_top=0.85, blood=blood, seed=seed + 1), aux=dr.soaked(seed + 5), trim=sweater_trim),
        gm.Garment("belt", MAT["leather"], (64, 42, 28),
                   lambda bb: ~armhand & (np.abs(bb.V[:, 1] - (waist_y - 0.013)) < 0.03),
                   0.017, 2, None, None, hem=0.004, hides_skin=False,
                   aux=dr.soaked(seed + 6), trim=lambda bb, ids, P: np.minimum(0.016 - np.abs(P[:, 1] - (waist_y - 0.013)), tear(P, 0.3))),
    ]
    # Bald on top: a grey fringe round the sides and the back of his head.
    levels = (0.112, 0.104, 0.07, 0.05, 0.012, -0.012)
    fringe = lambda P: 0.085 - (P - f.head)[:, 1]
    hair = [hair_cap(b, f, "fringe", (150, 146, 138), levels, offset=0.0025, extra=fringe, fade=0.012, thin=0.3)]

    def repaint(part, ids):   # brows: grey and bushy, even now
        V = b.V[ids]
        brow = np.clip(brow_field(f, V) / 0.002 + 0.7, 0, 1) * (dr.value_noise(V * 300.0, seed) > 0.35)
        col = dr.mix(part.col[:, :3].astype(float), np.array([150, 146, 138], float), brow * 0.7)
        part.col[:, :3] = np.clip(col, 0, 255).astype(np.uint8)

    trainer = dict(mat=MAT["leather"], color=(188, 188, 182), sole_mat=MAT["rubber"], sole_color=(196, 194, 186), sole=sole,
                   margin=0.01, shaft_top=0.085)
    parts = corpse(b, f, w, garments, skin, degloved=-side, shoes=[("l", trainer), ("r", trainer)], seed=seed, hair=hair,
                   repaint=repaint, missing_eye="r", scream=True)
    anchors = gore_anchors(b, f, w, -side, tongue=False) + drip_anchors(b, f, parts, ("sweater", "jeans"))
    anchors += [
        surface_anchor(b, "mussels0", jp["sho_r"] + np.array([0.01, 0.05, 0.03]), lift=0.02),
        surface_anchor(b, "mussels1", jp["kne_l"] + np.array([-0.03, 0.02, -0.06]), lift=0.013),
        surface_anchor(b, "weed0", jp["ank_r"] + np.array([0, 0.09, 0.05]), lift=0.013),
        surface_anchor(b, "weed1", jp["pelvis"] + np.array([-0.1, -0.02, 0.08]), lift=0.02),
        surface_anchor(b, "weed2", jp["sho_l"] + np.array([0.0, 0.02, 0.06]), lift=0.02),
    ]
    ch = dwc.Character(b.joints.astype(np.float32), parts, anchors)
    lift(ch, sole)
    return ch


# ── Sanne, in her summer dress ───────────────────────────────────────────────────
def woman_dress(data: Path) -> dwc.Character:
    """Sanne, 34: a teal midi dress printed with small flowers, a mustard cardigan, barefoot (her
    sandals are somewhere in the Prinsengracht). Long dark hair, wet, hanging over her face (the
    engine grows it from the "hair" anchors). Her right cheek is torn; her left hand degloved."""
    side, seed = 1.0, 23
    b = bm.build(data, mhdata.Macro(gender=0.0, age_years=34, muscle=0.4, weight=0.5, height=0.5, proportions=0.6,
                                    caucasian=1.0), dr.bloat(0.7, dr.death_mask(1.0, crooked=side)))
    dr.distort(b, Face(b), crooked=side)
    f = Face(b)
    jp, G = landmarks(b)
    armhand = G["arm"] | G["hand"]
    w = dr.wounds(b, f, side, seed, belly=0.0, cheek=False)
    skin = (88, 92, 98)
    waist_y = jp["pelvis"][1] + 0.1
    collar_y = jp["neck"][1] + 0.02
    sleeve_y = jp["elb_l"][1] + 0.09        # short sleeves: halfway down the upper arm
    cuff_y = jp["wri_l"][1] + 0.03
    hem_y = jp["kne_l"][1] - 0.16           # midi: mid-calf
    teal = (62, 98, 104)
    blood = dr.drool(f, 0.28)

    def bodice_trim(bb, ids, P):
        sleeves = np.where(armhand[ids], P[:, 1] - sleeve_y, 1.0)
        scoop = neck_curve(jp, P, collar_y, jp["chest"][1] + 0.035) - P[:, 1]
        return np.minimum.reduce([sleeves, scoop, np.where(armhand[ids], 1.0, P[:, 1] - (waist_y - 0.05))])

    def open_w(y):   # the cardigan hangs open: narrow at the neck, wider below
        return 0.05 + 0.04 * np.clip((jp["chest"][1] + 0.08 - y) / 0.3, 0, 1)

    def cardigan_trim(bb, ids, P):   # cropped: it ends above the skirt, a band of the dress between
        front = ~armhand[ids] & (P[:, 2] < jp["chest"][2] - 0.02)
        opening = np.where(front, np.abs(P[:, 0]) - open_w(P[:, 1]), 1.0)
        neckline = neck_curve(jp, P, collar_y + 0.006, collar_y - 0.02) - P[:, 1]
        hem = np.where(armhand[ids], P[:, 1] - cuff_y, P[:, 1] - (waist_y + 0.04))
        return np.minimum.reduce([opening, neckline, hem])

    def cardigan_knit(bb, ids, P, N):   # ribbed cuffs and hem; the sleeves ruck up at the wrists
        y = bb.V[ids, 1]
        out = gm.knit_rib(bb.V[ids], waist_y + 0.03, waist_y + 0.07, 0.003)
        for sd in ("l", "r"):
            wr = jp[f"wri_{sd}"]
            forearm = armhand[ids] & (np.sign(bb.V[ids, 0]) == np.sign(wr[0])) & (y < jp[f"elb_{sd}"][1])
            out += forearm * 0.0025 * np.sin(y * 150.0)
        return out

    garments = [
        gm.Garment("bodice", MAT["print"], teal,
                   lambda bb: ((~armhand & (bb.V[:, 1] > waist_y - 0.08)) | (armhand & (bb.V[:, 1] > sleeve_y - 0.03)))
                   & (bb.V[:, 1] < collar_y + 0.03),
                   gm.per_arm(0.006, 0.007), 2, None, None, hem=0.002, tension=6,
                   tint=dr.canal_tint(teal, mud_top=0.7, blood=blood, seed=seed), aux=dr.soaked(seed + 7), trim=bodice_trim),
        gm.Garment("cardigan", MAT["wool"], (150, 112, 44),
                   lambda bb: ((~armhand & (bb.V[:, 1] > waist_y + 0.01)) | (armhand & (bb.V[:, 1] > cuff_y - 0.03)))
                   & (bb.V[:, 1] < collar_y + 0.03),
                   gm.per_arm(0.014, 0.012), 3, None, cardigan_knit, hem=0.004, tension=10,
                   tint=dr.canal_tint((150, 112, 44), mud_top=0.9, blood=blood, seed=seed + 1), aux=dr.soaked(seed + 8), trim=cardigan_trim),
    ]
    # The skirt hangs from MakeHuman's skirt proxy (a body shell can't bridge the legs), flaring a
    # little toward the hem, its waist seam under the bodice's.
    def flare(bb, ids, P):
        out = P.copy()
        t = np.clip((waist_y - P[:, 1]) / (waist_y - hem_y), 0, 1) ** 1.4
        rad = P[:, [0, 2]] - np.array([0.0, jp["pelvis"][2]])
        rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-6)
        out[:, [0, 2]] += rad * (0.05 * t)[:, None]
        return out

    skirt = gm.build_helper(b, "helper-skirt", "skirt", MAT["print"], teal, 0.008,
                            trim=lambda bb, ids, P: np.minimum(P[:, 1] - hem_y, waist_y - P[:, 1]),
                            tint=dr.canal_tint(teal, mud_top=0.8, seed=seed + 2), hem=0.003, loosen=flare,
                            aux=dr.soaked(seed + 9))
    garments.append(skirt)
    hair = [hair_cap(b, f, "hair_cap", (26, 20, 16), offset=0.0015, mat=MAT["wethair"])]

    def repaint(part, ids):   # her own brows, dark
        V = b.V[ids]
        brow = np.clip(brow_field(f, V) / 0.002 + 0.5, 0, 1) * (dr.value_noise(V * 300.0, seed) > 0.3)
        col = dr.mix(part.col[:, :3].astype(float), np.array([48, 38, 32], float), brow * 0.75)
        part.col[:, :3] = np.clip(col, 0, 255).astype(np.uint8)

    parts = corpse(b, f, w, garments, skin, degloved=-side, seed=seed, hair=hair, repaint=repaint, scream=True)
    anchors = gore_anchors(b, f, w, -side, tongue=False) + drip_anchors(b, f, parts, ("skirt", "cardigan"))
    # Roots for her hair (the engine lays a flat ribbon of wet hair from each): all over the scalp;
    # the ones along the front hairline become the curtain over her face.
    anchors += scalp_anchors(b, scalp_select(b, f, margin=-0.004), 220, seed, prefix="hair")
    anchors += [
        surface_anchor(b, "mussels0", jp["sho_l"] + np.array([-0.01, 0.04, 0.04]), lift=0.02),
        surface_anchor(b, "weed0", jp["kne_r"] + np.array([0.02, -0.1, 0.04]), lift=0.01),
        surface_anchor(b, "weed1", jp["ank_l"] + np.array([0, 0.05, 0.03]), lift=0.008),
    ]
    return dwc.Character(b.joints.astype(np.float32), parts, anchors)


CAST = {"office_worker": office_worker, "pieter": pieter, "woman_dress": woman_dress}
