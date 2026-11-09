# damned_waters/tools/blender/fair.py
# Purpose: the November funfair on the Dam (Blender side), still lit and stopped mid-ride the night the
# city was emptied: a Ferris wheel with its gondolas and its spokes ringed in bulbs, a drop tower with
# its seats stopped halfway up, a carousel under its striped canopy, and the stalls (oliebollen, a
# shooting gallery, sweets) with their shutters up and their signs on. Built from a few measurements
# each, in the street kit's way (lots of small lights gathered into one mesh per colour). Every name on
# a sign is made up. Coordinates as in street.py (Godot frame, metres; a prop's local +z its front).
#
# ELI5: a fairground is mostly light bulbs on steel. Draw the steel thin and dark, the bulbs bright and
# many, and the eye does the rest; that's how they look in the photographs at night.
import math
import random

import builders
import kit
import street
from roomspec import g2b
from street import Acc, M, lbox, rod, text, ball

STEEL = {"color": [0.75, 0.76, 0.78], "rough": 0.35, "metal": 0.9, "noise": 0.1}
WHITE = {"color": [0.85, 0.85, 0.83], "rough": 0.35, "noise": 0.05}
BULB_COLOURS = {"warm": (1.0, 0.82, 0.5), "white": (0.9, 0.95, 1.0), "red": (1.0, 0.15, 0.1), "blue": (0.15, 0.35, 1.0),
                "green": (0.2, 1.0, 0.35), "pink": (1.0, 0.25, 0.65)}


def bulbs_mat(colour, strength=9.0):
    c = BULB_COLOURS.get(colour, colour)
    return builders.emissive("fair_bulb_%d_%d_%d_%d" % (int(c[0] * 100), int(c[1] * 100), int(c[2] * 100), int(strength)), tuple(c), strength)


def bulb_line(acc, a, b, gap=0.35, r=0.045):
    """Bulbs every `gap` metres from a to b (small spheres as 6-sided rods: cheap, and at night only
    their glow is seen)."""
    L = math.dist(a, b)
    n = int(L / gap)
    for i in range(n + 1):
        t = i / n if n else 0.0
        p = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        acc.rod((p[0], p[1] - r, p[2]), (p[0], p[1] + r, p[2]), r, r, 6)


def truss(acc, a, b, w=0.5, r=0.05):
    """A square lattice truss from a to b, w across: four chords and zigzag bracing (the fairground's
    steel, light and strong)."""
    ax, ay, az = a
    bx, by, bz = b
    d = [bx - ax, by - ay, bz - az]
    L = math.sqrt(sum(c * c for c in d))
    d = [c / L for c in d]
    up = [0.0, 1.0, 0.0] if abs(d[1]) < 0.9 else [1.0, 0.0, 0.0]
    s = [d[1] * up[2] - d[2] * up[1], d[2] * up[0] - d[0] * up[2], d[0] * up[1] - d[1] * up[0]]
    sl = math.sqrt(sum(c * c for c in s))
    s = [c / sl for c in s]
    t = [d[1] * s[2] - d[2] * s[1], d[2] * s[0] - d[0] * s[2], d[0] * s[1] - d[1] * s[0]]
    corners = [(+1, +1), (+1, -1), (-1, -1), (-1, +1)]

    def at(k, u):
        cs, ct = corners[k]
        return tuple(a[i] + d[i] * u * L + (s[i] * cs + t[i] * ct) * w / 2 for i in range(3))
    for k in range(4):
        acc.rod(at(k, 0.0), at(k, 1.0), r, r, 6)
    n = max(1, int(L / w))
    for j in range(n):
        u0, u1 = j / n, (j + 1) / n
        for k in range(4):
            acc.rod(at(k, u0), at((k + 1) % 4, u1), r * 0.5, r * 0.5, 4)


# ── The Ferris wheel ────────────────────────────────────────────────────────────────────
def ferris_wheel(root, p, w, h, d):
    """A transportable Ferris wheel (reuzenrad) facing +z, the wheel `h` across: two A-frame legs of
    truss to the hub, twin rims joined by spokes ringed in bulbs, gondolas hanging from the rim (a
    few swinging, one with its door open), the boarding platform and the ticket booth lit. Stopped."""
    rng = random.Random(p.get("seed", 3))
    R = h / 2
    hub = (0.0, R + p.get("clearance", 2.5), 0.0)
    steel = M(p.get("steel", STEEL))
    legs = Acc()
    for sz in (-1, 1):   # the two A-frames, one each side of the wheel
        z = sz * (d / 2)
        for sx in (-1, 1):
            truss(legs, (sx * R * 0.55, 0.0, z * 1.6), (0.0, hub[1], z), w=0.7, r=0.06)
    legs.rod((0.0, hub[1], -d / 2 - 0.4), (0.0, hub[1], d / 2 + 0.4), 0.45, 0.45, 16)   # the axle
    legs.build("wheel_legs", steel, root)
    rims = Acc()
    seg = 48
    n_spokes = p.get("spokes", 24)
    for sz in (-1, 1):
        z = sz * d * 0.3
        for k in range(seg):
            a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
            for rr in (R, R - 0.7):
                rims.rod((rr * math.cos(a0), hub[1] + rr * math.sin(a0), z), (rr * math.cos(a1), hub[1] + rr * math.sin(a1), z), 0.07, 0.07, 6)
        for k in range(n_spokes):
            a = 2 * math.pi * k / n_spokes
            rims.rod((0.0, hub[1], z), (R * math.cos(a), hub[1] + R * math.sin(a), z), 0.06, 0.06, 6)
    for k in range(n_spokes):   # cross ties between the twin rims
        a = 2 * math.pi * k / n_spokes
        rims.rod((R * math.cos(a), hub[1] + R * math.sin(a), -d * 0.3), (R * math.cos(a), hub[1] + R * math.sin(a), d * 0.3), 0.06, 0.06, 6)
    rims.build("wheel_rims", steel, root)
    # the lights: every spoke and both rims in bulbs, in two colours turn and turn about
    lights = {c: Acc() for c in p.get("colours", ("white", "blue"))}
    cols = list(lights)
    for sz in (-1, 1):
        z = sz * d * 0.3 + sz * 0.1
        for k in range(n_spokes):
            a = 2 * math.pi * k / n_spokes
            bulb_line(lights[cols[k % len(cols)]], (1.0 * math.cos(a), hub[1] + 1.0 * math.sin(a), z),
                      (R * math.cos(a), hub[1] + R * math.sin(a), z), gap=0.6)
        for k in range(seg * 2):
            a = 2 * math.pi * k / (seg * 2)
            bulb_line(lights[cols[(k // 6) % len(cols)]], (R * math.cos(a), hub[1] + R * math.sin(a), z),
                      (R * math.cos(a), hub[1] + R * math.sin(a), z), gap=1.0)
    for c, acc in lights.items():
        acc.build("wheel_bulbs", bulbs_mat(c, p.get("glow", 9.0)), root)
    # the gondolas, hanging from the rim, each a little cabin with its lamp on
    cab_m = M({"color": list(p.get("cabin", (0.75, 0.08, 0.06))), "rough": 0.35, "metal": 0.3})
    glass = M("glass")
    lamp_m = builders.emissive("gondola_lamp", (1.0, 0.85, 0.6), 2.5)
    for k in range(n_spokes):
        a = 2 * math.pi * k / n_spokes + math.pi / n_spokes
        px, py = R * math.cos(a), hub[1] + R * math.sin(a)
        sw = rng.uniform(-8, 8) if rng.random() < 0.3 else 0.0   # some still swinging a little
        g = builders.empty_at("gondola", (0.0, 0.0, 0.0), 0.0)
        g.parent = root
        g.location = g2b((px, py, 0.0))
        g.rotation_euler[1] = math.radians(sw)
        rod(g, "gondola_hanger", (0.0, 0.0, -0.5), (0.0, -0.8, 0.0), 0.04, 0.04, steel)
        rod(g, "gondola_hanger", (0.0, 0.0, 0.5), (0.0, -0.8, 0.0), 0.04, 0.04, steel)
        lbox(g, "gondola_floor", (-0.8, -2.4, -0.7), (0.8, -2.25, 0.7), cab_m)
        lbox(g, "gondola_roof", (-0.85, -0.95, -0.75), (0.85, -0.8, 0.75), cab_m)
        lbox(g, "gondola_skirt", (-0.8, -2.25, -0.7), (0.8, -1.75, 0.7), cab_m)
        for sx in (-1, 1):
            lbox(g, "gondola_post", (sx * 0.8 - 0.03, -2.25, -0.03), (sx * 0.8 + 0.03, -0.95, 0.03), cab_m)
        lbox(g, "gondola_glass", (-0.78, -1.75, -0.68), (0.78, -0.95, 0.68), glass)
        lbox(g, "gondola_lamp", (-0.2, -1.0, -0.2), (0.2, -0.96, 0.2), lamp_m)
    # the platform and the ticket booth
    lbox(root, "wheel_platform", (-R * 0.6, 0.0, -d), (R * 0.6, 0.6, d), M({"color": [0.1, 0.1, 0.11], "rough": 0.5, "metal": 0.6}))
    for k in range(int(R * 1.2 / 0.6)):   # its steps
        x = -R * 0.6 + k * 0.6
        lbox(root, "platform_tread", (x, 0.58, d - 0.4), (x + 0.5, 0.62, d + 0.6), M({"color": [0.3, 0.3, 0.3], "rough": 0.5, "metal": 0.7}))
    booth = builders.empty_at("wheel_booth", (0.0, 0.0, 0.0), 0.0)
    booth.parent = root
    booth.location = g2b((R * 0.6 + 2.0, 0.0, d + 1.0))
    stall(booth, {"name": p.get("name", "REUZENRAD"), "kind": "kassa", "seed": 7}, 2.4, 2.8, 2.0)
    import landmarks
    landmarks.point(root, (0.0, hub[1], d), p.get("glow_light", 400.0), (0.8, 0.85, 1.0), radius=4.0)


# ── The drop tower ──────────────────────────────────────────────────────────────────────
def drop_tower(root, p, w, h, d):
    """A free-fall tower: a mast h high of square truss lit from top to bottom in running colours, a
    ring of seats around it stopped part way up ("stopped": 0..1 of the way), the crown at the top
    with its sign, a fenced base. Seats empty, harnesses down."""
    steel = M(p.get("steel", STEEL))
    m = Acc()
    truss(m, (0.0, 0.0, 0.0), (0.0, h, 0.0), w=w, r=0.08)
    m.build("tower_mast", steel, root)
    lights = {c: Acc() for c in p.get("colours", ("red", "white", "blue"))}
    cols = list(lights)
    for k, (sx, sz) in enumerate(((1, 1), (1, -1), (-1, -1), (-1, 1))):   # bulbs up all four chords
        x, z = sx * (w / 2 + 0.1), sz * (w / 2 + 0.1)
        for j in range(int(h / 2.0)):
            bulb_line(lights[cols[j % len(cols)]], (x, j * 2.0, z), (x, j * 2.0 + 1.8, z), gap=0.45)
    for c, acc in lights.items():
        acc.build("tower_bulbs", bulbs_mat(c, p.get("glow", 10.0)), root)
    crown = Acc()
    crown.box((-w, h, -w), (w, h + 2.0, w))
    crown.build("tower_crown", M({"color": [0.08, 0.08, 0.09], "rough": 0.4, "metal": 0.6}), root, smooth=False)
    import city
    for k in range(4):   # the name on all four sides of the crown
        a = 90 * k
        ax, az = math.sin(math.radians(a)) * (w + 0.05), math.cos(math.radians(a)) * (w + 0.05)
        city.neon_text(root, p.get("name", "FREE FALL"), (ax, h + 1.0, az), 0.9, BULB_COLOURS["pink"], 6.0, yaw=a,
                       font="DejaVuSans-Bold.ttf", tube=0.03)
    y = h * p.get("stopped", 0.45)   # the ring of seats, stopped part way up: whoever ran it ran
    seat_m = M({"color": [0.9, 0.75, 0.05], "rough": 0.4})
    ring = Acc()
    n = 12
    rr = w / 2 + 1.0
    for k in range(n):
        a = 2 * math.pi * k / n
        x, z = rr * math.cos(a), rr * math.sin(a)
        nx, nz = math.cos(a), math.sin(a)
        ring.box((x - 0.3, y, z - 0.3), (x + 0.3, y + 0.15, z + 0.3))
        ring.box((x - 0.3 * nz - 0.05 * nx, y, z + 0.3 * nx - 0.05 * nz), (x + 0.3 * nz + 0.05 * nx, y + 1.1, z - 0.3 * nx + 0.05 * nz))
    ring.build("tower_seats", seat_m, root, smooth=False)
    lbox(root, "seat_carriage", (-rr + 0.3, y - 0.4, -rr + 0.3), (rr - 0.3, y, rr - 0.3), steel)
    lbox(root, "tower_base", (-rr - 2.0, 0.0, -rr - 2.0), (rr + 2.0, 0.5, rr + 2.0), M({"color": [0.1, 0.1, 0.11], "rough": 0.5, "metal": 0.6}))
    import landmarks
    landmarks.spot(root, (0.0, 0.5, rr + 6.0), (0.0, y, 0.0), p.get("flood", 900.0), (1.0, 0.4, 0.75), size=30.0)


# ── The carousel ────────────────────────────────────────────────────────────────────────
def carousel(root, p, w, h, d):
    """A carousel w across: a round platform, a mirrored centre column, horses on twisted brass poles
    (CC0 horse figures, painted), a striped canopy with its rim ringed in bulbs and the name round
    its valance. Stopped mid-turn, the organ music still going (the sound's the game's)."""
    rng = random.Random(p.get("seed", 5))
    R = w / 2
    brass = M({"color": [0.85, 0.65, 0.25], "rough": 0.25, "metal": 1.0})
    kit.lathe(root, "carousel_platform", [(R, 0.0), (R, 0.45), (0.0, 0.45)], M({"ph": "dark_wood", "tint": [0.6, 0.45, 0.3], "scale": 0.5}),
              at=(0.0, 0.0, 0.0), segments=32)
    kit.lathe(root, "carousel_column", [(1.0, 0.0), (1.0, h - 1.2), (0.0, h - 1.2)], M({"color": [0.05, 0.05, 0.06], "rough": 0.05, "metal": 1.0}),
              at=(0.0, 0.45, 0.0), segments=12, smooth=False)
    canopy = Acc()   # striped canopy: alternate panels in two colours
    canopy_b = Acc()
    seg = 24
    for k in range(seg):
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        acc = canopy if k % 2 == 0 else canopy_b
        acc.quad((R * math.cos(a0), h - 1.0, R * math.sin(a0)), (R * math.cos(a1), h - 1.0, R * math.sin(a1)), (0.0, h + 1.2, 0.0), (0.0, h + 1.2, 0.0))
        acc.quad((R * math.cos(a0), h - 1.0, R * math.sin(a0)), (R * math.cos(a1), h - 1.0, R * math.sin(a1)),
                 (R * math.cos(a1), h - 1.6, R * math.sin(a1)), (R * math.cos(a0), h - 1.6, R * math.sin(a0)))
    canopy.build("carousel_canopy", M({"color": list(p.get("colour_a", (0.75, 0.05, 0.05))), "rough": 0.6}), root, smooth=False)
    canopy_b.build("carousel_canopy", M({"color": list(p.get("colour_b", (0.92, 0.85, 0.6))), "rough": 0.6}), root, smooth=False)
    bulbs = Acc()
    for k in range(seg * 4):
        a = 2 * math.pi * k / (seg * 4)
        for y in (h - 1.62, h - 1.0):
            bulb_line(bulbs, (R * math.cos(a), y, R * math.sin(a)), (R * math.cos(a), y, R * math.sin(a)), gap=1.0, r=0.05)
    bulbs.build("carousel_bulbs", bulbs_mat("warm", 9.0), root)
    poles = Acc()
    for ring, rr in enumerate((R * 0.55, R * 0.82)):   # two rings of horses
        n = int(2 * math.pi * rr / 1.9)
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * ring) / n
            x, z = rr * math.cos(a), rr * math.sin(a)
            poles.rod((x, 0.45, z), (x, h - 1.0, z), 0.035, 0.035, 8)
            hy = 0.9 + 0.5 * math.sin(k * 1.7 + ring)   # up and down, where they stopped
            horse = builders.empty_at("carousel_horse", (0.0, 0.0, 0.0), 0.0)
            horse.parent = root
            horse.location = g2b((x, hy, z))
            horse.rotation_euler[2] = math.radians(-math.degrees(a))
            kit.model(horse, {"model": "ph:horse_statue_01", "fit": [0.5, 1.2, 1.4],
                              "tint": [0.95, 0.9, 0.82] if (k + ring) % 3 else [0.75, 0.55, 0.3]}, 0, 0, 0)
    poles.build("carousel_poles", brass, root)
    import city
    for k in range(4):
        a = 90 * k + 45
        ax, az = math.sin(math.radians(a)) * (R + 0.05), math.cos(math.radians(a)) * (R + 0.05)
        city.neon_text(root, p.get("name", "DRAAIMOLEN"), (ax, h - 1.3, az), 0.32, BULB_COLOURS["warm"], 5.0, yaw=a, font="DejaVuSerif-Bold.ttf", tube=0.012)
    import landmarks
    landmarks.point(root, (0.0, h - 1.8, 0.0), p.get("power", 350.0), (1.0, 0.8, 0.5), radius=1.5)


# ── Stalls ─────────────────────────────────────────────────────────────────────────────
LIVERY = {   # the trailer's paint: its body and the band round it (a white box from behind is a hole in the picture)
    "oliebollen": ((0.42, 0.05, 0.04), (0.92, 0.88, 0.75)),
    "schiettent": ((0.05, 0.07, 0.22), (0.85, 0.75, 0.1)),
    "suikerspin": ((0.62, 0.22, 0.4), (0.95, 0.95, 0.92)),
    "grijper": ((0.04, 0.26, 0.11), (0.92, 0.9, 0.85)),
    "kassa": ((0.09, 0.09, 0.1), (0.85, 0.65, 0.25)),
}
STALLS = {   # name on the front, awning colours, what's on the counter
    "oliebollen": ("OLIEBOLLEN", ((0.92, 0.88, 0.75), (0.6, 0.08, 0.06)), "food"),
    "schiettent": ("SCHIETTENT", ((0.1, 0.12, 0.35), (0.85, 0.75, 0.1)), "prizes"),
    "suikerspin": ("SUIKERSPIN · POPCORN", ((0.95, 0.6, 0.75), (0.95, 0.95, 0.92)), "food"),
    "grijper": ("GRIJPERS", ((0.1, 0.45, 0.2), (0.92, 0.9, 0.85)), "prizes"),
    "kassa": ("KASSA", ((0.15, 0.15, 0.17), (0.85, 0.65, 0.25)), "none"),
}


def _blob(acc, c, rx, ry, rz, seg=8, rings=5):
    """An ellipsoid into an accumulator (a soft toy's body, its head, its ears)."""
    cx, cy, cz = c
    rows = [[(cx + rx * math.sin(math.pi * i / rings) * math.cos(2 * math.pi * k / seg), cy - ry * math.cos(math.pi * i / rings),
              cz + rz * math.sin(math.pi * i / rings) * math.sin(2 * math.pi * k / seg)) for k in range(seg)] for i in range(rings + 1)]
    for i in range(rings):
        for k in range(seg):
            acc.quad(rows[i][k], rows[i + 1][k], rows[i + 1][(k + 1) % seg], rows[i][(k + 1) % seg])


def _teddy(acc, x, y, z, s, sit=False):
    """A soft toy s high-ish, facing +z: a body, a head with its ears and muzzle, arms (and legs out if
    it sits on a shelf)."""
    _blob(acc, (x, y, z), s * 0.5, s * 0.58, s * 0.42)
    _blob(acc, (x, y + s * 0.8, z + s * 0.04), s * 0.4, s * 0.38, s * 0.36)
    _blob(acc, (x, y + s * 0.74, z + s * 0.38), s * 0.15, s * 0.11, s * 0.1, seg=6, rings=4)
    for ex in (-1, 1):
        _blob(acc, (x + ex * s * 0.3, y + s * 1.12, z), s * 0.14, s * 0.14, s * 0.07, seg=6, rings=4)
        _blob(acc, (x + ex * s * 0.46, y + s * 0.12, z + s * 0.12), s * 0.16, s * 0.3, s * 0.16, seg=6, rings=4)
        if sit:
            _blob(acc, (x + ex * s * 0.24, y - s * 0.45, z + s * 0.32), s * 0.17, s * 0.15, s * 0.3, seg=6, rings=4)


def _bulbs(lit, dead, a, b, rng, gap=0.3, r=0.035, gone=0.12):
    """bulb_line, with a share of the bulbs blown (the stall has been burning since the city emptied)."""
    L = math.dist(a, b)
    n = max(1, int(L / gap))
    for i in range(n + 1):
        t = i / n
        q = tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
        (dead if rng.random() < gone else lit).rod((q[0], q[1] - r, q[2]), (q[0], q[1] + r, q[2]), r, r, 6)


TOY_COLOURS = [(0.75, 0.12, 0.1), (0.15, 0.3, 0.75), (0.2, 0.6, 0.25), (0.85, 0.4, 0.6), (0.85, 0.7, 0.2), (0.55, 0.38, 0.22),
               (0.85, 0.83, 0.8), (0.5, 0.2, 0.6)]


def stall(root, p, w, h, d):
    """A kermis stall: a trailer-box w wide in its livery (sanded edges, chrome at its corners, a band
    round it, a chrome skirt), its front flap up as a striped awning with a scalloped valance (one
    scallop torn off), an arched crest over it with the name in bulbs and bulbs round its edge,
    pilasters of bulbs beside the hatch, some bulbs blown; the counter lit. On show: food (a glass
    case, the fryers, the menu), a shooting gallery (rows of targets, rifles on the counter, soft
    toys hung in a row), or claw machines lit inside, a heap of toys in each."""
    rng = random.Random(p.get("seed", 9))
    kind = p.get("kind", "oliebollen")
    name, (ca, cb), show = STALLS.get(kind, STALLS["oliebollen"])
    name = p.get("name", name)
    paint, trim = LIVERY.get(kind, LIVERY["oliebollen"])
    body = M({"color": list(paint), "rough": 0.3, "noise": 0.05, "coat": 0.6, "grime": 1.0, "streaks": 0.4})
    trim_m = M({"color": list(trim), "rough": 0.35})
    chrome = M({"color": [0.75, 0.76, 0.78], "rough": 0.12, "metal": 1.0, "noise": 0.08})
    f = d / 2   # (its footprint centred on its spot, as the game's collider is: the front at +d/2)
    kit.soft(root, "stall_back", (0.0, h / 2, -f + 0.03), (w, h, 0.06), body, 0.025, 2)
    for sx in (-1, 1):
        kit.soft(root, "stall_side", (sx * (w / 2 - 0.03), h / 2, -0.025), (0.06, h, d - 0.05), body, 0.025, 2)
        for zz in (-f, f - 0.05):
            rod(root, "stall_corner", (sx * w / 2, 0.3, zz), (sx * w / 2, h, zz), 0.03, 0.03, chrome, seg=8)
        kit.soft(root, "stall_pilaster", (sx * (w / 2 - 0.1), (1.05 + h - 0.5) / 2, f - 0.02), (0.2, h - 1.55, 0.06), trim_m, 0.02, 2)
    kit.soft(root, "stall_roof", (0.0, h - 0.03, -0.025), (w + 0.04, 0.06, d - 0.05), body, 0.02, 2)
    kit.soft(root, "stall_front_lo", (0.0, 0.5, f - 0.085), (w, 1.0, 0.07), body, 0.02, 2)
    kit.soft(root, "stall_front_hi", (0.0, h - 0.25, f - 0.085), (w, 0.5, 0.07), body, 0.02, 2)
    lbox(root, "stall_panel", (-w / 2 + 0.25, 0.38, f - 0.05), (w / 2 - 0.25, 0.86, f - 0.04), trim_m)
    lbox(root, "stall_panel_in", (-w / 2 + 0.3, 0.43, f - 0.04), (w / 2 - 0.3, 0.81, f - 0.035), body)
    lbox(root, "stall_floor", (-w / 2, 0.88, -d / 2), (w / 2, 0.92, f - 0.1), M({"color": [0.2, 0.2, 0.21], "rough": 0.6}))
    lbox(root, "stall_band", (-w / 2 - 0.01, 0.92, -d / 2 - 0.01), (w / 2 + 0.01, 1.0, f - 0.06), trim_m)
    lbox(root, "stall_skirt", (-w / 2 - 0.01, 0.0, -d / 2 - 0.01), (w / 2 + 0.01, 0.3, f - 0.06), M({"color": [0.7, 0.72, 0.74], "rough": 0.2, "metal": 0.9}))
    lbox(root, "stall_inside", (-w / 2 + 0.1, 1.0, f - 1.2), (w / 2 - 0.1, h - 0.5, f - 1.18), M({"ph": "dirty_tiles", "tint": [0.9, 0.88, 0.84], "scale": 0.5}))
    for sx in (-1, 1):   # the box's insides, lit by its own lamp
        lbox(root, "stall_cheek", (sx * (w / 2 - 0.1) - 0.02, 1.0, f - 1.2), (sx * (w / 2 - 0.1) + 0.02, h - 0.5, f - 0.05), body)
    lbox(root, "stall_ceiling", (-w / 2 + 0.1, h - 0.52, f - 1.2), (w / 2 - 0.1, h - 0.5, f - 0.05), M({"color": [0.75, 0.73, 0.7], "rough": 0.6}))
    rod(root, "stall_tube", (-w / 2 + 0.4, h - 0.56, f - 0.5), (w / 2 - 0.4, h - 0.56, f - 0.5), 0.02, 0.02, builders.emissive("stall_tube", (0.95, 0.97, 1.0), 6.0), seg=6)
    lbox(root, "stall_counter", (-w / 2, 0.95, f - 0.1), (w / 2, 1.05, f + 0.5), M({"color": [0.5, 0.06, 0.05], "rough": 0.4}))
    lbox(root, "stall_counter_edge", (-w / 2, 0.94, f + 0.5), (w / 2, 1.06, f + 0.52), chrome)
    # the awning: the flap propped up, sagging a little between its stays, a scalloped valance
    stripes = (Acc(), Acc())
    n = max(2, int(w / 0.4))
    ye, ze = h - 0.12, f + 1.4

    def aw(t):
        return (h - 0.45 + 0.33 * t - 0.05 * math.sin(math.pi * t), f + 1.4 * t)
    torn = rng.randrange(n)
    for k in range(n):
        x0, x1 = -w / 2 + w * k / n, -w / 2 + w * (k + 1) / n
        acc = stripes[k % 2]
        for j in range(3):
            (ya, za), (yb, zb) = aw(j / 3), aw((j + 1) / 3)
            acc.quad((x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb))
        if k == torn:
            continue
        xc, rx, drop = (x0 + x1) / 2, (x1 - x0) / 2, 0.2
        for j in range(6):
            a0, a1 = math.pi * j / 6, math.pi * (j + 1) / 6
            acc.quad((xc, ye, ze), (xc - rx * math.cos(a0), ye - drop * math.sin(a0), ze), (xc - rx * math.cos(a1), ye - drop * math.sin(a1), ze), (xc, ye, ze))
    stripes[0].build("stall_awning", M({"color": list(ca), "rough": 0.6}), root, smooth=False)
    stripes[1].build("stall_awning", M({"color": list(cb), "rough": 0.6}), root, smooth=False)
    for sx in (-1, 1):   # its stays
        rod(root, "stall_stay", (sx * (w / 2 - 0.05), 1.05, f + 0.02), (sx * (w / 2 - 0.05), ye - 0.02, ze - 0.05), 0.018, 0.018, chrome)
    # the crest: an arch over the front in the stall's colours, its name in bulbs, bulbs round it
    crest, inset = Acc(), Acc()
    nk = 16
    top = [(-w / 2 + w * k / nk, h + 0.45 + 0.4 * math.sin(math.pi * k / nk) ** 0.8) for k in range(nk + 1)]
    for (xa, ya), (xb, yb) in zip(top, top[1:]):
        crest.quad((xa, h - 0.05, f + 0.05), (xb, h - 0.05, f + 0.05), (xb, yb, f + 0.05), (xa, ya, f + 0.05))
        crest.quad((xb, h - 0.05, f - 0.05), (xa, h - 0.05, f - 0.05), (xa, ya, f - 0.05), (xb, yb, f - 0.05))
        crest.quad((xa, ya, f + 0.05), (xb, yb, f + 0.05), (xb, yb, f - 0.05), (xa, ya, f - 0.05))
        ia, ib = max(-w / 2 + 0.12, min(w / 2 - 0.12, xa)), max(-w / 2 + 0.12, min(w / 2 - 0.12, xb))
        if ib > ia:
            inset.quad((ia, h + 0.05, f + 0.055), (ib, h + 0.05, f + 0.055), (ib, yb - 0.12, f + 0.055), (ia, ya - 0.12, f + 0.055))
    crest.build("stall_crest", M({"color": list(cb), "rough": 0.4}), root, smooth=False)
    inset.build("stall_crest_in", body, root, smooth=False)
    text(root, name, (0.0, h + 0.38, f + 0.06), min(0.36, 1.4 * w / max(len(name), 1)), bulbs_mat("warm", 6.0), font="DejaVuSans-Bold.ttf", depth=0.0)
    lit, dead = Acc(), Acc()
    for (xa, ya), (xb, yb) in zip(top, top[1:]):
        _bulbs(lit, dead, (xa, ya - 0.05, f + 0.08), (xb, yb - 0.05, f + 0.08), rng, gap=0.22, r=0.03)
    _bulbs(lit, dead, (-w / 2, h - 0.12, ze + 0.02), (w / 2, h - 0.12, ze + 0.02), rng, gap=0.3)
    for sx in (-1, 1):
        _bulbs(lit, dead, (sx * (w / 2 - 0.1), 1.15, f + 0.02), (sx * (w / 2 - 0.1), h - 0.6, f + 0.02), rng, gap=0.2, r=0.03)
    lit.build("stall_bulbs", bulbs_mat("warm", 8.0), root)
    dead.build("stall_bulbs_dead", M({"color": [0.5, 0.45, 0.38], "rough": 0.2}), root)
    if show == "prizes":
        toys = [Acc() for _ in TOY_COLOURS]
        x, strings = -w / 2 + 0.45, Acc()
        while x < w / 2 - 0.4:   # hung in a row under the crest, each on its string
            s_ = rng.uniform(0.17, 0.24)
            y = h - 0.75 - s_ * 0.6
            _teddy(toys[rng.randrange(len(toys))], x, y, f - 0.25, s_)
            strings.rod((x, h - 0.52, f - 0.25), (x, y + s_ * 1.15, f - 0.23), 0.004, 0.004, 4)
            x += rng.uniform(0.4, 0.5)
        strings.build("strings", M({"color": [0.8, 0.78, 0.7], "rough": 0.8}), root)
        if kind == "grijper":   # claw machines: a lit glass box each, a heap of toys, the claw stopped
            glass, frame = M("glass"), M({"color": [0.04, 0.04, 0.045], "rough": 0.4, "metal": 0.6})
            k_n = max(2, int((w - 0.4) / 1.05))
            for k in range(k_n):
                cx = -w / 2 + 0.2 + (w - 0.4) * (k + 0.5) / k_n
                cz = f - 0.75
                kit.soft(root, "claw_base", (cx, 1.2, cz), (0.86, 0.56, 0.74), M({"color": list(BULB_COLOURS[["pink", "blue", "red", "green"][k % 4]]), "rough": 0.35}), 0.03, 2)
                lbox(root, "claw_glass", (cx - 0.42, 1.48, cz - 0.35), (cx + 0.42, 2.12, cz + 0.35), glass)
                lbox(root, "claw_top", (cx - 0.43, 2.12, cz - 0.36), (cx + 0.43, 2.26, cz + 0.36), builders.emissive("claw_%d" % (k % 4), BULB_COLOURS[["pink", "blue", "red", "green"][k % 4]], 4.0))
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        rod(root, "claw_post", (cx + sx * 0.42, 1.48, cz + sz * 0.35), (cx + sx * 0.42, 2.12, cz + sz * 0.35), 0.012, 0.012, frame, seg=6)
                for _ in range(16):
                    _blob(toys[rng.randrange(len(toys))], (cx + rng.uniform(-0.32, 0.32), 1.55 + rng.uniform(0.0, 0.08), cz + rng.uniform(-0.25, 0.25)), 0.07, 0.06, 0.07, seg=6, rings=4)
                rod(root, "claw_wire", (cx, 2.12, cz), (cx, 1.85, cz), 0.004, 0.004, frame, seg=4)
                for j in range(3):
                    a = 2 * math.pi * j / 3
                    rod(root, "claw", (cx, 1.85, cz), (cx + 0.06 * math.cos(a), 1.75, cz + 0.06 * math.sin(a)), 0.008, 0.006, M({"color": [0.7, 0.7, 0.72], "rough": 0.2, "metal": 1.0}), seg=4)
        else:   # a shooting gallery: tin targets in rows on the back, toys up on shelves, rifles on the counter
            red, white = Acc(), Acc()
            for row in range(3):
                y = 1.35 + row * 0.22
                for k in range(int((w - 0.6) / 0.24)):
                    x = -w / 2 + 0.4 + k * 0.24
                    (red if (k + row) % 2 else white).rod((x, y, f - 1.175), (x, y, f - 1.15), 0.07, 0.07, 12)
            red.build("targets", M({"color": [0.7, 0.08, 0.06], "rough": 0.5, "metal": 0.4}), root, smooth=False)
            white.build("targets", M({"color": [0.85, 0.85, 0.8], "rough": 0.5, "metal": 0.4}), root, smooth=False)
            lbox(root, "shelf", (-w / 2 + 0.15, 2.0, f - 1.18), (w / 2 - 0.15, 2.03, f - 0.95), M({"color": [0.3, 0.2, 0.12], "rough": 0.7}))
            x = -w / 2 + 0.35
            while x < w / 2 - 0.3:
                _teddy(toys[rng.randrange(len(toys))], x, 2.03 + 0.11, f - 1.05, 0.15, sit=True)
                x += 0.32
            gun = M({"color": [0.03, 0.03, 0.03], "rough": 0.35, "metal": 0.8})
            stock = M({"color": [0.25, 0.12, 0.05], "rough": 0.5})
            for k in range(3):
                gx = -w / 4 + k * w / 4 + rng.uniform(-0.15, 0.15)
                yaw_ = rng.uniform(-0.25, 0.25)
                ax_, az_ = math.sin(yaw_), math.cos(yaw_)
                rod(root, "rifle", (gx, 1.075, f + 0.22), (gx + ax_ * 0.45, 1.075, f + 0.22 - az_ * 0.45), 0.012, 0.012, gun, seg=6)
                rod(root, "rifle_stock", (gx, 1.07, f + 0.22), (gx - ax_ * 0.35, 1.08, f + 0.22 + az_ * 0.35), 0.03, 0.022, stock, seg=6)
        for c, acc in zip(TOY_COLOURS, toys):
            acc.build("prizes", M({"color": list(c), "rough": 0.95}), root)
    elif show == "food":   # a glass case of what was fried, the fryers behind, the prices up on a board
        steel = M({"color": [0.62, 0.63, 0.64], "rough": 0.3, "metal": 1.0, "noise": 0.15})
        lbox(root, "food_case", (-w / 3, 1.05, f + 0.02), (w / 3, 1.08, f + 0.42), steel)
        lbox(root, "food_glass", (-w / 3, 1.08, f + 0.4), (w / 3, 1.4, f + 0.42), M("glass"))
        balls, sugar = Acc(), Acc()
        for _ in range(int(w * 9)):
            x, z = rng.uniform(-w / 3 + 0.06, w / 3 - 0.06), rng.uniform(f + 0.08, f + 0.36)
            r = rng.uniform(0.035, 0.045)
            balls.rod((x, 1.08, z), (x, 1.08 + r * 1.6, z), r, r * 0.7, 8)
            sugar.rod((x, 1.08 + r * 1.55, z), (x, 1.08 + r * 1.75, z), r * 0.72, r * 0.2, 8)
        balls.build("oliebollen", M({"color": [0.32, 0.17, 0.06], "rough": 0.55, "noise": 0.3}), root)
        sugar.build("poedersuiker", M({"color": [0.85, 0.84, 0.8], "rough": 0.9}), root)
        for x in (-w / 4, w / 4):
            lbox(root, "fryer", (x - 0.4, 0.95, f - 1.15), (x + 0.4, 1.2, f - 0.7), steel)
            lbox(root, "fryer_oil", (x - 0.34, 1.19, f - 1.1), (x + 0.34, 1.205, f - 0.75), M({"color": [0.12, 0.07, 0.01], "rough": 0.05}))
        lbox(root, "menu_board", (-w / 2 + 0.4, 1.6, f - 1.17), (w / 2 - 0.4, h - 0.65, f - 1.15), M({"color": [0.03, 0.03, 0.035], "rough": 0.5}))
        chalk = M({"color": [0.85, 0.84, 0.78], "rough": 0.8})
        for k, line in enumerate(p.get("menu", [name, "3 STUKS  4,50", "6 STUKS  8,00", "MET ROZIJNEN +0,50"])):
            text(root, line, (0.0, h - 0.85 - k * 0.24, f - 1.14), 0.13 if k else 0.18, chalk, font="DejaVuSans-Bold.ttf", depth=0.0)
        cups = Acc()
        for _ in range(5):   # paper trays left on the counter, one on its side
            x, z = rng.uniform(-w / 2 + 0.3, w / 2 - 0.3), rng.uniform(f + 0.05, f + 0.45)
            if abs(x) < w / 3 + 0.1 and z > f + 0.0:
                x = math.copysign(w / 3 + 0.25, x)
            cups.rod((x, 1.05, z), (x, 1.11, z), 0.045, 0.06, 10)
        cups.build("trays", M({"color": [0.88, 0.86, 0.8], "rough": 0.8}), root)
    import landmarks
    landmarks.point(root, (0.0, h - 0.6, f + 0.8), p.get("power", 40.0), (1.0, 0.82, 0.55), radius=0.5)


kit.PROPS.update({"ferris_wheel": ferris_wheel, "drop_tower": drop_tower, "carousel": carousel, "fair_stall": stall})
