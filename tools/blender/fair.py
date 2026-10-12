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
STALLS = {   # name on the front, awning colours, what's on the counter
    "oliebollen": ("OLIEBOLLEN", ((0.92, 0.88, 0.75), (0.6, 0.08, 0.06)), "food"),
    "schiettent": ("SCHIETTENT", ((0.1, 0.12, 0.35), (0.85, 0.75, 0.1)), "prizes"),
    "suikerspin": ("SUIKERSPIN · POPCORN", ((0.95, 0.6, 0.75), (0.95, 0.95, 0.92)), "food"),
    "grijper": ("GRIJPERS", ((0.1, 0.45, 0.2), (0.92, 0.9, 0.85)), "prizes"),
    "kassa": ("KASSA", ((0.15, 0.15, 0.17), (0.85, 0.65, 0.25)), "none"),
}


def stall(root, p, w, h, d):
    """A fairground stall: a trailer-box w wide with its front flap up as an awning (striped), its
    counter lit, its name in bulbs along the fascia, and on show: food, or rows of prizes (stuffed
    toys as bright soft lumps)."""
    rng = random.Random(p.get("seed", 9))
    name, (ca, cb), show = STALLS.get(p.get("kind", "oliebollen"), STALLS["oliebollen"])
    name = p.get("name", name)
    body = M({"color": [0.88, 0.86, 0.8], "rough": 0.4, "noise": 0.05})
    f = d / 2   # (its footprint centred on its spot, as the game's collider is: the front at +d/2)
    lbox(root, "stall_body", (-w / 2, 0.0, -d / 2), (w / 2, h, f - 0.05), body)
    lbox(root, "stall_inside", (-w / 2 + 0.1, 1.0, f - 0.05), (w / 2 - 0.1, h - 0.5, f - 0.03), builders.emissive("stall_inside", (1.0, 0.85, 0.6), 1.2))
    lbox(root, "stall_counter", (-w / 2, 0.95, f - 0.1), (w / 2, 1.05, f + 0.5), M({"color": [0.5, 0.06, 0.05], "rough": 0.4}))
    flap = Acc()
    flap_b = Acc()
    n = max(2, int(w / 0.4))
    for k in range(n):   # the awning, striped
        x0, x1 = -w / 2 + w * k / n, -w / 2 + w * (k + 1) / n
        (flap if k % 2 == 0 else flap_b).quad((x0, h - 0.4, f), (x1, h - 0.4, f), (x1, h - 0.1, f + 1.4), (x0, h - 0.1, f + 1.4))
    flap.build("stall_awning", M({"color": list(ca), "rough": 0.6}), root, smooth=False)
    flap_b.build("stall_awning", M({"color": list(cb), "rough": 0.6}), root, smooth=False)
    lbox(root, "stall_fascia", (-w / 2, h - 0.05, f - 0.05), (w / 2, h + 0.55, f + 0.05), M({"color": list(cb), "rough": 0.4}))
    text(root, name, (0.0, h + 0.25, f + 0.06), min(0.36, 1.4 * w / max(len(name), 1)), bulbs_mat("warm", 6.0), font="DejaVuSans-Bold.ttf", depth=0.0)
    edge = Acc()
    bulb_line(edge, (-w / 2, h - 0.12, f + 1.42), (w / 2, h - 0.12, f + 1.42), gap=0.3, r=0.035)
    edge.build("stall_bulbs", bulbs_mat("warm", 8.0), root)
    if show == "prizes":   # rows of soft toys up the back, bright
        toys = {c: Acc() for c in ("red", "blue", "green", "pink", "warm")}
        for row in range(3):
            y = 1.4 + row * 0.45
            x = -w / 2 + 0.25
            while x < w / 2 - 0.25:
                c = rng.choice(list(toys))
                s = rng.uniform(0.12, 0.18)
                toys[c].box((x - s, y, f - 0.6), (x + s, y + s * 2.2, f - 0.6 + s * 1.4))
                x += 0.38
        for c, acc in toys.items():
            acc.build("prizes", M({"color": [v * 0.8 for v in BULB_COLOURS[c]], "rough": 0.9}), root, smooth=False)
    elif show == "food":   # trays on the counter, a sugar shaker, a pile of paper bags
        lbox(root, "food_tray", (-w / 4, 1.05, f), (w / 4, 1.12, f + 0.4), M({"color": [0.45, 0.28, 0.1], "rough": 0.6}))
    import landmarks
    landmarks.point(root, (0.0, h - 0.6, f + 0.8), p.get("power", 40.0), (1.0, 0.82, 0.55), radius=0.5)


kit.PROPS.update({"ferris_wheel": ferris_wheel, "drop_tower": drop_tower, "carousel": carousel, "fair_stall": stall})
