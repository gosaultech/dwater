# damned_waters/tools/characters/drowned.py
# Purpose: what days in an Amsterdam canal do to a body, shared by every Drowned
# citizen (cast_drowned.py dresses the people; this module ruins them). Forensic, not
# fantasy:
#   bloat    gas swells the belly, face, neck and hands (MakeHuman's own morph targets)
#   skin     washed-out grey; the shader adds marbling, lividity, blisters and slippage;
#            blood settles purple in the hands and feet
#   face     milky eyes in bruised sockets, blue-black lips, one cheek torn through
#   belly    split open by the gas (the engine pushes the guts out through the hole)
#   hands    one degloved (raw beneath), one bleached and wrinkled ("washerwoman" hands)
#   scalp    hair slipping off with the skin at the front, bare scalp behind the tear
#   clothes  waterlogged (darker), canal mud climbing from the hems, torn over the split,
#            blood run down the front from the hanging mouth
# Holes are real holes in the mesh: seen from inside, a body renders as meat (the
# shader's "inside is flesh" rule), so a tear has depth without modelling what's inside.
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import dwc
import garments as gm
import rig
from body import Body
from parts import MAT

# MakeHuman targets and how far each goes at full bloat (1.0).
BLOAT = {
    "stomach/stomach-pregnant-incr.target": 0.85,
    "head/head-fat-incr.target": 0.8,
    "neck/neck-double-incr.target": 0.7,
    "neck/neck-scale-horiz-incr.target": 0.35,
    "cheek/l-cheek-volume-incr.target": 0.7, "cheek/r-cheek-volume-incr.target": 0.7,
    "eyes/l-eye-bag-incr.target": 1.0, "eyes/r-eye-bag-incr.target": 1.0,
    "armslegs/l-hand-scale-incr.target": 0.3, "armslegs/r-hand-scale-incr.target": 0.3,
    "armslegs/l-hand-fingers-diameter-incr.target": 1.0, "armslegs/r-hand-fingers-diameter-incr.target": 1.0,
}
BRUISE, CYANOSIS, LIVID = (66, 46, 64), (60, 46, 62), (98, 76, 96)
RAW, DRIED, MUD = (104, 24, 22), (58, 14, 12), (72, 60, 42)
DERMIS, SLOUGH = (126, 94, 88), (164, 162, 146)
PUTRID, BLOTCH, MOUTH = (88, 106, 66), (84, 62, 74), (22, 12, 14)   # green rot, purple-brown marks, the mouth's lining
SOCKET = (30, 22, 28)                                                 # the hollows round the eyes


# The death mask: every one of them died screaming, and the face stayed that way. MakeHuman's
# expression units (FACS-style morph targets: brows, lids, mouth, neck) set to a scream of terror,
# pushed past what a living face can do. Per unit: (left, right) weights; the crooked side screams
# harder, so the mouth drags off to one side.
SCREAM = {
    "eyebrows-{s}-inner-up": (1.4, 1.4), "eyebrows-{s}-up": (0.5, 0.5),
    "eye-{s}-opened-up": (1.5, 1.5),
    "nose-{s}-dilatation": (0.9, 0.9), "nose-{s}-elevation": (0.5, 0.5),
}
SCREAM_MID = {"mouth-open": 0.7, "mouth-depression-retraction": 1.3, "mouth-retraction": 0.35,   # a tall O, not a wide
              "neck-platysma": 1.4}                                                                  # grin; the jaw drops in the engine


def death_mask(amount: float = 1.0, crooked: float = 0.0, ethnicity: str = "caucasian") -> dict[str, float]:
    """Target weights for the frozen scream: amount 0..1 (and a little past), crooked -1..1 (which
    side it drags toward, and how far)."""
    base = f"expression/units/{ethnicity}/"
    out = {}
    for unit, (l, r) in SCREAM.items():
        out[base + unit.format(s="left") + ".target"] = l * amount * (1 + 0.35 * max(crooked, 0))
        out[base + unit.format(s="right") + ".target"] = r * amount * (1 + 0.35 * max(-crooked, 0))
    for unit, w in SCREAM_MID.items():
        out[base + unit + ".target"] = w * amount
    return out


def distort(b: Body, face, crooked: float = 0.0, stretch: float = 0.32, sink: float = 0.005) -> None:
    """Warp the face the way the scream left it: the lower face drawn down longer than a face can
    go, dragged off toward the crooked side (-1..1) more and more toward the chin, and the eye
    sockets sunk deep. In place, before anything is built on the body; normals are rebuilt.
    Rebuild the Face landmarks afterwards (the mouth has moved)."""
    import body as bm
    V = b.V
    head = b.weight_of("head", "jaw")
    rel = V - face.head
    w = head * np.clip(-rel[:, 2] / 0.06, 0, 1)                     # the face, not the back of the skull
    below = np.clip(np.mean([e[1] for e in face.eyes]) - V[:, 1], 0, None)   # metres below the eyes
    V[:, 1] -= w * stretch * below
    V[:, 0] += w * crooked * 1.6 * below ** 2
    for e in face.eyes:                                              # the sockets (and the eyes in them) sink
        k = np.clip(1 - np.linalg.norm(V - e, axis=1) / 0.026, 0, 1) ** 1.5 * head
        V[:, 2] += k * sink
    b.N = bm.normals(V, b.body_quads, b.groups)


def bloat(amount: float, extra: dict[str, float] | None = None) -> dict[str, float]:
    """Target weights for a body `amount` of the way to fully gas-bloated, plus any extra targets."""
    out = {k: v * amount for k, v in BLOAT.items()}
    for k, v in (extra or {}).items():
        out[k] = out.get(k, 0.0) + v
    return out


def value_noise(p: np.ndarray, seed: int = 0) -> np.ndarray:
    """Smooth 3D value noise in 0..1 for (n,3) points: stains, ragged edges, patches."""
    p = np.asarray(p, float)
    i = np.floor(p).astype(np.int64)
    f = p - i
    f = f * f * (3 - 2 * f)

    def h(dx, dy, dz):
        n = ((i[:, 0] + dx) * 73856093) ^ ((i[:, 1] + dy) * 19349663) ^ ((i[:, 2] + dz) * 83492791) ^ (seed * 2654435761)
        n = (n ^ (n >> 13)) * 1274126177
        return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

    x0 = h(0, 0, 0) * (1 - f[:, 0]) + h(1, 0, 0) * f[:, 0]
    x1 = h(0, 1, 0) * (1 - f[:, 0]) + h(1, 1, 0) * f[:, 0]
    x2 = h(0, 0, 1) * (1 - f[:, 0]) + h(1, 0, 1) * f[:, 0]
    x3 = h(0, 1, 1) * (1 - f[:, 0]) + h(1, 1, 1) * f[:, 0]
    y0 = x0 * (1 - f[:, 1]) + x1 * f[:, 1]
    y1 = x2 * (1 - f[:, 1]) + x3 * f[:, 1]
    return y0 * (1 - f[:, 2]) + y1 * f[:, 2]


def mix(a, b, t):
    """Blend colour arrays a -> b by t (per row)."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    t = np.asarray(t, float)
    return a * (1 - t[..., None]) + b * t[..., None] if t.ndim else a * (1 - t) + b * t


@dataclass
class Wounds:
    """Holes the canal tore in one body. `side` is the torn side: -1 = the character's left, +1 = right."""
    side: float
    cheek_dist: np.ndarray      # per body vertex: normalised distance from the tear's centre (1 = its edge)
    cheek_rim: np.ndarray       # 0..1 per body vertex: raw flesh at the edge (1 inside the tear)
    belly_dist: np.ndarray      # the same for the split belly
    belly_rim: np.ndarray
    belly_centre: np.ndarray    # (3,) on the skin, engine space
    belly_shape: tuple = ()     # (half width, half height, seed, front z limit) for belly_field

    def cloth_tear(self, margin: float = 0.35) -> np.ndarray:
        """Cloth over the split tears wider than the skin (bool per body vertex)."""
        return self.belly_dist < 1.0 + margin

    def belly_field(self, P: np.ndarray) -> np.ndarray:
        """Normalised distance from the belly split for any points (1 = the skin's edge): cloth is
        trimmed where this is above 1 + a margin, so the tear's edge is as ragged as the wound."""
        half_w, half_h, seed, front_z = self.belly_shape
        rel = np.asarray(P, float) - self.belly_centre
        ang = np.arctan2(rel[:, 1], rel[:, 0])
        rag = 1 + 0.18 * np.sin(ang * 7 + seed * 1.7) + 0.1 * np.sin(ang * 13 + seed)
        d = np.sqrt((rel[:, 0] / half_w) ** 2 + (rel[:, 1] / half_h) ** 2) / rag
        return np.where(np.asarray(P)[:, 2] < front_z, d, 99.0)


def _nearest(b: Body, target: np.ndarray, mask: np.ndarray) -> np.ndarray:
    ids = np.nonzero(mask)[0]
    return b.V[ids[np.argmin(np.linalg.norm(b.V[ids] - target, axis=1))]]


def mouth_back(b: Body, face) -> np.ndarray:
    """Body quads at the back of MakeHuman's mouth pocket (per quad). A jaw hanging open stretches
    them into a membrane across the scream; cut them, and a void behind them reads as the throat."""
    rel = b.V[b.body_quads].mean(axis=1) - face.mouth
    return ((np.linalg.norm(rel, axis=1) < 0.05) & (np.abs(rel[:, 0]) < 0.03) & (rel[:, 2] > 0.012)
            & (rel[:, 1] > -0.034) & (rel[:, 1] < 0.02))


def wounds(b: Body, face, side: float, seed: int = 1, belly: float = 1.0, cheek: bool = True,
           cheek_at=(0.034, 0.004, 0.02), cheek_size=(0.014, 0.021)) -> Wounds:
    """Tear one cheek through to the teeth (unless cheek is False) and split the belly (belly = size,
    0 for none). cheek_at: the tear's centre from the mouth (x toward `side`); cheek_size: its half
    height and half length. The default sits over the back teeth; a long, low one splits the corner
    of the mouth back along the cheek, so the jaw hangs open further on that side."""
    from body import J
    V = b.V
    on_body = np.isin(np.arange(len(V)), b.body_ids)
    head = on_body & (b.weight_of("head", "jaw") > 0.5)
    c = _nearest(b, face.mouth + np.array([cheek_at[0] * side, cheek_at[1], cheek_at[2]]), head)
    rel = V - c
    ang = np.arctan2(rel[:, 1], rel[:, 2])
    rag = 1 + 0.22 * np.sin(ang * 5 + seed) + 0.12 * np.sin(ang * 11 + seed * 2.3)
    d = np.sqrt((rel[:, 1] / cheek_size[0]) ** 2 + (np.hypot(rel[:, 0], rel[:, 2]) / cheek_size[1]) ** 2) / rag
    cheek_dist = np.where(head & cheek, d, 99.0)
    cheek_rim = head * cheek * np.clip(1 - (d - 1.0) / 0.9, 0, 1)
    # Belly: a vertical split beside the navel, where the gas burst the skin.
    pelvis = b.joints[J["pelvis"]]
    torso = on_body & np.isin(b.dominant, [J["pelvis"], J["spine"], J["chest"]])
    front = torso & (V[:, 2] < pelvis[2] - 0.04)
    bc = _nearest(b, np.array([0.014 * side, pelvis[1] + 0.1, V[front, 2].min() - 0.05]), front)
    rel = V - bc
    ang = np.arctan2(rel[:, 1], rel[:, 0])
    rag = 1 + 0.18 * np.sin(ang * 7 + seed * 1.7) + 0.1 * np.sin(ang * 13 + seed)
    half_h, half_w = 0.085 * belly + 1e-6, 0.026 * belly + 1e-6
    bd = np.sqrt((rel[:, 0] / half_w) ** 2 + (rel[:, 1] / half_h) ** 2 + (np.maximum(rel[:, 2], 0) / 0.03) ** 2) / rag
    bd = np.where(front & (belly > 0), bd, 99.0)
    belly_rim = front * np.clip(1 - (bd - 1.0) / 0.7, 0, 1) * (belly > 0)
    return Wounds(side, cheek_dist, cheek_rim, bd, belly_rim, bc, (half_w, half_h, seed, pelvis[2] - 0.02))


def skin(b: Body, quads: np.ndarray, w: Wounds, walls: tuple = (0.006, 0.012)) -> tuple:
    """The body's skin with the wounds cut out along their ragged outlines (exact curves, like the
    garments' trims, not the stairs of the mesh), each tear given a wall of flesh `walls` metres deep
    (cheek, belly) so it reads as torn through, not painted on. Returns (part, src, wall): src maps
    each vertex to the body vertex it came from; wall marks the flesh inside the tears."""
    ids, local = np.unique(quads, return_inverse=True)
    local = local.reshape(quads.shape)
    tris = np.concatenate([local[:, [0, 1, 2]], local[:, [0, 2, 3]]])
    s = np.minimum(w.cheek_dist[ids], w.belly_dist[ids]) - 1.0
    P, N, src, T, W, on_cut = gm.clip(b.V[ids], b.N[ids], ids, tris, s, gm.dense_weights(b, ids))
    rim = gm.rim_edges(T)
    rim = rim[on_cut[rim].all(axis=1)]                      # the tears' edges, not the garments' borders
    depth = np.where(w.cheek_dist[src] < w.belly_dist[src], walls[0], walls[1])
    P, N, T, (src, W), wall = gm.fold_edges(P, N, T, depth, rim, carry=(src, W))
    jid, jw = gm.top4(W)
    n = len(P)
    part = dwc.Part("body", P.astype(np.float32), N.astype(np.float32), np.full((n, 4), 255, np.uint8),
                    np.full(n, MAT["drowned"], np.uint8), b.region[src].astype(np.uint8), jid, jw, T.astype(np.int64))
    return part, src, wall


def paint_body(b: Body, part, ids: np.ndarray, face, skin, w: Wounds, degloved: float, seed: int = 0,
               lividity: float = 1.0, wall: np.ndarray | None = None, empty_socket: int | None = None) -> None:
    """Colour and material for drowned skin: bruised sockets, cyanotic lips, livid extremities,
    raw wound edges, one degloved hand and one bleached one. `degloved` = the side (-1/+1).
    ids: the body vertex behind each of the part's vertices; wall: the flesh inside the tears;
    empty_socket: 0 or 1, an eye the canal took (its lids raw and crusted)."""
    V = b.V[ids]
    n = value_noise(V * 40.0, seed)
    col = np.tile(np.array(skin[:3], float), (len(ids), 1)) * (0.9 + 0.16 * n[:, None])
    mat = np.full(len(ids), MAT["drowned"], np.uint8)
    # Rot shows in patches: green where the gut's bacteria spread (strongest over the belly), purple-
    # brown blotches where vessels burst.
    belly = np.clip(1 - np.abs(V[:, 1] - w.belly_centre[1]) / 0.25, 0, 1) * (V[:, 2] < w.belly_centre[2] + 0.12)
    face_w = b.weight_of("head", "jaw")[ids]
    col = mix(col, PUTRID, np.clip((value_noise(V * 7.0, seed + 3) - 0.52) * 3 + belly * 0.35, 0, 1) * 0.5 * (1 - 0.8 * face_w))
    col = mix(col, BLOTCH, np.clip((value_noise(V * 11.0, seed + 11) - 0.6) * 4, 0, 1) * 0.55)
    # Blood settles low once the heart stops: hands, feet, earlobes go purple.
    ext = b.weight_of(*rig.hand_joints("l", "r"), "ank_l", "ank_r")[ids]
    col = mix(col, LIVID, np.clip(ext * 1.3 - 0.2, 0, 1) * 0.55 * lividity)
    for k, e in enumerate(face.eyes):   # hollow sockets: bruised almost black at the lids
        d = np.linalg.norm(V - e, axis=1)
        col = mix(col, BRUISE, np.clip(1 - (d - 0.012) / 0.03, 0, 1) ** 1.2 * 0.9)
        col = mix(col, SOCKET, np.clip(1 - (d - 0.011) / 0.012, 0, 1) * 0.85)
        if k == empty_socket:          # eaten out: raw, crusted lids
            col = mix(col, mix(np.tile(np.array(RAW, float), (len(ids), 1)), DRIED, value_noise(V * 150.0, seed + 13)),
                      np.clip(1 - (d - 0.014) / 0.008, 0, 1))
    oris = b.bone("oris")[ids]   # blue-black lips
    lip = np.clip((oris - 0.25) * 3, 0, 1) * np.clip(1 - np.abs(V[:, 1] - face.mouth[1]) / 0.016, 0, 1)
    col = mix(col, CYANOSIS, lip * 0.9)
    # Inside the hanging mouth: dark, wet lining, darker deeper in. MakeHuman's mouth is a pocket:
    # the lips' inner faces turn back into the head, and its back wall (which the open jaw
    # stretches into view) lies a couple of centimetres behind the lips.
    rel = V - face.mouth
    lining = ((np.linalg.norm(rel, axis=1) < 0.05) & (np.abs(rel[:, 0]) < 0.03)
              & (((b.N[ids][:, 2] > 0.2) & (rel[:, 2] > -0.006)) | (rel[:, 2] > 0.012)))
    col[lining] = mix(col[lining], MOUTH, np.clip(0.7 + (rel[lining, 2] + 0.006) / 0.02, 0, 1))
    mat[lining] = MAT["tongue"]
    # Wound edges: raw at the lip of each tear, crusted dark in places, a bruised halo outside. Colour
    # only: materials change per triangle, so a material edge on the skin would show as jagged
    # shards; the flesh material is kept for the walls inside the tears (skin()).
    wound = mix(np.tile(np.array(RAW, float), (len(ids), 1)), DRIED, value_noise(V * 90.0, seed + 5) * 0.7)
    for rim in (w.cheek_rim[ids], w.belly_rim[ids]):
        col = mix(col, BRUISE, np.clip(rim * 1.6, 0, 1) * 0.7)
        col = mix(col, wound, np.clip((rim - 0.55) * 3.0, 0, 1))
    # Hands: one degloved to the wrist (raw dermis), the other bleached and wrinkled.
    for s in (-1.0, 1.0):
        sd = "l" if s < 0 else "r"
        hw = b.weight_of(*rig.hand_joints(sd))[ids]
        hand = np.clip(hw * 2 - 0.6, 0, 1)
        if s == degloved:
            ragged = hand * (0.75 + 0.5 * value_noise(V * 60.0, seed + 7)) > 0.55
            col[ragged] = mix(np.array(DERMIS, float), RAW, 0.3 * n[ragged])
            mat[ragged] = MAT["dermis"]
        else:
            wash = hand > 0.4
            col[wash] = mix(np.array(SLOUGH, float), col[wash], 0.25)
            mat[wash] = MAT["slough"]
    if wall is not None:   # deep in a tear: dark, wet meat
        col[wall] = mix(np.array(RAW, float) * 0.7, DRIED, value_noise(V[wall] * 120.0, seed + 9) * 0.6)
        mat[wall] = MAT["flesh"]
    part.col = np.column_stack([np.clip(col, 0, 255), np.full(len(ids), 255)]).astype(np.uint8)
    part.mat = mat
    # Where the forehead furrows (the shader reads it from aux): above the brows the scream raised.
    rel = V - face.head
    brow_y = np.mean([e[1] for e in face.eyes]) + 0.02
    forehead = np.clip((V[:, 1] - brow_y) / 0.01, 0, 1) * np.clip((brow_y + 0.06 - V[:, 1]) / 0.02, 0, 1) * np.clip(-rel[:, 2] / 0.05, 0, 1)
    part.aux = np.clip(forehead * face_w, 0, 1).astype(np.float32)


def canal_tint(color, mud_top: float = 0.55, wet: float = 0.8, blood: list | None = None, seed: int = 0):
    """Garment tint: waterlogged (darker), water stains, canal mud from the hems up to about
    `mud_top` metres, and blood around the given (point, radius) pairs."""
    base = np.array(color[:3], float) * wet

    def tint(bb, ids, P):
        n = value_noise(P * 9.0, seed)
        col = np.tile(base, (len(P), 1)) * (0.92 + 0.14 * n[:, None])
        stain = np.clip((value_noise(P * 3.2, seed + 5) - 0.55) * 4, 0, 1)
        col = col * (1 - stain[:, None] * 0.28)
        m = np.clip((mud_top - P[:, 1]) / max(mud_top, 1e-3), 0, 1) * (0.3 + 0.55 * value_noise(P * 5.0, seed + 9))
        col = mix(col, MUD, np.clip(m, 0, 1))
        for at, r in blood or []:
            d = np.linalg.norm(P - np.asarray(at, float), axis=1)
            bl = np.clip(1 - d / r, 0, 1) ** 1.2 * (0.55 + 0.45 * n)
            col = mix(col, DRIED, np.clip(bl, 0, 1))
        return col
    return tint


def soaked(seed: int = 0, dry_top: float = 1.9):
    """Garment aux: how wet the cloth is (the shader darkens it and gives it a dull sheen). Soaked
    through, wettest low down where the water runs to, drying a little in patches up top."""
    def aux(bb, ids, P):
        n = value_noise(P * 6.0, seed + 21)
        return np.clip(0.75 + 0.25 * np.clip((dry_top - P[:, 1]) / dry_top, 0, 1) - 0.25 * n, 0.4, 1.0)
    return aux


def drool(face, length: float = 0.3, width: float = 0.05):
    """Blood run from the hanging mouth down the front: a list of (point, radius) stains."""
    top = face.mouth + np.array([0.0, -0.06, -0.01])
    return [(top + np.array([0.01 * np.sin(k * 2.1), -length * k / 5, 0.012 * k]), width * (1 - 0.1 * k)) for k in range(6)]
