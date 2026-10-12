# damned_waters/tools/blender/aftermath.py
# Purpose: the evacuation's aftermath kit (Blender side), so the city reads as emptied in a hurry, not
# never lived in (docs/city_aftermath.md): hand-painted evacuation-route boards, an aid post (a tent,
# stretchers, a floodlight on a generator, a covered body), dropped luggage and leaflets, abandoned
# vehicles with their doors open and lights on (a car, a taxi, a police van, an ambulance), sandbag
# walls, a fire pump with its hoses down into the canal, smashed shop glass. CC0 scans where they
# exist (suitcases, the searchlight, the generator, a wheelchair, crutches, boots, a megaphone);
# built where they don't. Coordinates as in street.py (Godot frame, metres; a prop's +z its front).
#
# ELI5: what a film crew's props department puts down after the extras have run off the set: the
# story of everyone who was here, told by what they dropped.
import math
import random

import builders
import kit
import street
from roomspec import g2b
from street import Acc, M, lbox, rod, text, ball

PLY = {"color": [0.55, 0.45, 0.32], "rough": 0.8, "noise": 0.3}
SPRAY_RED = {"color": [0.6, 0.03, 0.02], "rough": 0.6}
SPRAY_BLACK = {"color": [0.02, 0.02, 0.02], "rough": 0.6}
CANVAS = {"color": [0.78, 0.78, 0.74], "rough": 0.85, "noise": 0.15}


def _model(root, ref, at, yaw=0.0, fit=None, scale=None, roll=0.0):
    """A CC0 scan put down at `at` (root's frame), turned and maybe tipped over."""
    sub = builders.empty_at("dropped", (0.0, 0.0, 0.0), 0.0)
    sub.parent = root
    sub.location = g2b(at)
    sub.rotation_euler = (0.0, math.radians(-roll), math.radians(yaw))
    p = {"model": ref}
    if fit:
        p["fit"] = fit
    if scale:
        p["scale"] = scale
    kit.model(sub, p, 0, 0, 0)
    return sub


# ── Signs of the evacuation ─────────────────────────────────────────────────────────────
def evac_board(root, p, w, h, d):
    """A sheet of plywood on two trestle legs, sprayed by hand: EVACUATIEROUTE, an arrow, where to
    ("to": CENTRAAL), the arrow pointing "left" or "right" (as you read it)."""
    ply, red, black = M(PLY), M(SPRAY_RED), M(SPRAY_BLACK)
    lbox(root, "board", (-w / 2, h - 1.1, -0.01), (w / 2, h, 0.01), ply)
    for sx in (-1, 1):
        rod(root, "trestle", (sx * (w / 2 - 0.15), 0.0, -0.35), (sx * (w / 2 - 0.15), h - 0.6, 0.0), 0.025, 0.025, ply)
        rod(root, "trestle", (sx * (w / 2 - 0.15), 0.0, 0.35), (sx * (w / 2 - 0.15), h - 0.6, 0.0), 0.025, 0.025, ply)
    for face in (1, -1):
        z = 0.012 * face
        text(root, p.get("text", "EVACUATIEROUTE"), (0.0, h - 0.25, z), 0.16, red, font="DejaVuSans-Bold.ttf", depth=0.0,
             yaw=0.0 if face > 0 else 180.0)
        text(root, p.get("to", "CENTRAAL"), (0.0, h - 0.85, z), 0.2, black, font="DejaVuSans-Bold.ttf", depth=0.0,
             yaw=0.0 if face > 0 else 180.0)
        a = Acc()   # the arrow, sprayed in one go
        y = h - 0.55
        if p.get("arrow") == "up":   # straight on
            a.quad((-0.05, y - 0.2, z), (0.05, y - 0.2, z), (0.05, y + 0.05, z), (-0.05, y + 0.05, z))
            a.quad((-0.16, y + 0.05, z), (0.16, y + 0.05, z), (0.0, y + 0.2, z), (0.0, y + 0.2, z))
        else:
            right = (p.get("arrow", "right") == "right") == (face > 0)
            sx = 1 if right else -1
            a.quad((-0.6 * sx, y - 0.05, z), (0.35 * sx, y - 0.05, z), (0.35 * sx, y + 0.05, z), (-0.6 * sx, y + 0.05, z))
            a.quad((0.35 * sx, y - 0.16, z), (0.6 * sx, y, z), (0.6 * sx, y, z), (0.35 * sx, y + 0.16, z))
        a.build("arrow", red, root, smooth=False)


def leaflets(root, p, w, h, d):
    """Evacuation notices blown over the ground (w by d about the spot): white and yellow sheets,
    a printed band on each, some caught against the kerb."""
    rng = random.Random(p.get("seed", 11))
    sheets, bands = Acc(), Acc()
    for _ in range(p.get("count", int(w * d * 1.2))):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        a = rng.uniform(0, math.pi)
        c, s = math.cos(a), math.sin(a)
        hw, hd = 0.105, 0.148

        def at(u, v, y=0.004):
            return (x + u * c - v * s, y + rng.uniform(0, 0.003), z + u * s + v * c)
        sheets.quad(at(-hw, -hd), at(hw, -hd), at(hw, hd), at(-hw, hd))
        bands.quad(at(-hw * 0.8, hd * 0.55, 0.008), at(hw * 0.8, hd * 0.55, 0.008), at(hw * 0.8, hd * 0.8, 0.008), at(-hw * 0.8, hd * 0.8, 0.008))
    sheets.build("leaflets", M({"color": [0.82, 0.8, 0.72], "rough": 0.7, "noise": 0.2}), root, smooth=False)
    bands.build("leaflet_print", M({"color": [0.7, 0.32, 0.02], "rough": 0.6}), root, smooth=False)


def luggage(root, p, w, h, d):
    """What people dropped running for the trams, scattered over w by d about the spot: suitcases
    (CC0 scans, some on their sides), holdalls, a pushchair, an umbrella, shoes, a wheelchair or
    crutches ("chair": true)."""
    rng = random.Random(p.get("seed", 13))
    for _ in range(p.get("cases", 3)):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        _model(root, "ph:vintage_suitcase", (x, 0.0, z), rng.uniform(0, 360), fit=[0.7, 0.5, 0.3], roll=rng.choice([0, 0, 90]))
    cols = [(0.08, 0.08, 0.1), (0.25, 0.08, 0.05), (0.06, 0.16, 0.25), (0.3, 0.26, 0.2)]
    for _ in range(p.get("bags", 3)):   # holdalls and rucksacks
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        sub = builders.empty_at("bag", (x, 0.0, z), rng.uniform(0, 360))
        sub.parent = root
        sub.location = g2b((x, 0.0, z))
        kit.soft(sub, "holdall", (0.0, 0.15, 0.0), (0.6, 0.3, 0.32), M({"color": list(rng.choice(cols)), "rough": 0.8, "noise": 0.2}), 0.1, 3)
    shoes = Acc()
    for _ in range(p.get("shoes", 4)):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        a = rng.uniform(0, math.pi)
        dx, dz = 0.13 * math.cos(a), 0.13 * math.sin(a)
        shoes.rod((x - dx, 0.04, z - dz), (x + dx, 0.04, z + dz), 0.045, 0.04, 6)
    shoes.build("shoes", M({"color": [0.04, 0.035, 0.03], "rough": 0.4}), root)
    if p.get("umbrella", True):   # an umbrella blown open, upside down
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        kit.lathe(root, "umbrella", [(0.0, 0.0), (0.5, 0.3), (0.52, 0.32), (0.0, 0.33)], M({"color": [0.05, 0.05, 0.08], "rough": 0.5}),
                  at=(x, 0.02, z), segments=8, smooth=False)
        rod(root, "umbrella_shaft", (x, 0.05, z), (x + 0.3, 0.75, z + 0.2), 0.012, 0.012, M({"color": [0.3, 0.3, 0.3], "metal": 0.8, "rough": 0.3}))
    if p.get("pushchair"):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        sub = builders.empty_at("pushchair", (x, 0.0, z), rng.uniform(0, 360))
        sub.parent = root
        sub.location = g2b((x, 0.0, z))
        frame = M({"color": [0.12, 0.12, 0.13], "rough": 0.4, "metal": 0.6})
        for sx in (-1, 1):
            for wz in (-0.32, 0.32):
                kit.lathe(sub, "pram_wheel", [(0.0, -0.02), (0.13, -0.02), (0.13, 0.02), (0.0, 0.02)], frame, at=(sx * 0.28, 0.13, wz), segments=12).rotation_euler[1] = math.radians(90)
        kit.soft(sub, "pram_seat", (0.0, 0.55, 0.0), (0.5, 0.35, 0.7), M({"color": [0.08, 0.15, 0.3], "rough": 0.8}), 0.08, 3)
        rod(sub, "pram_handle", (-0.25, 0.6, -0.35), (-0.25, 1.05, -0.55), 0.015, 0.015, frame)
        rod(sub, "pram_handle", (0.25, 0.6, -0.35), (0.25, 1.05, -0.55), 0.015, 0.015, frame)
        rod(sub, "pram_bar", (-0.25, 1.05, -0.55), (0.25, 1.05, -0.55), 0.015, 0.015, frame)
    if p.get("chair"):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        _model(root, "ph:wheelchair_01", (x, 0.0, z), rng.uniform(0, 360))
    if p.get("crutches"):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2)
        _model(root, "ph:vintage_crutches_01", (x, 0.0, z), rng.uniform(0, 360), roll=90)


def broken_glass(root, p, w, h, d):
    """A shop window's glass in shards on the pavement in front of it (w along the front, d out)."""
    rng = random.Random(p.get("seed", 17))
    a = Acc()
    for _ in range(int(w * d * 40)):
        x, z = rng.uniform(-w / 2, w / 2), rng.uniform(0.0, d) * rng.random()
        s = rng.uniform(0.02, 0.09)
        t = rng.uniform(0, math.pi)
        a.quad((x, 0.008, z), (x + s * math.cos(t), 0.008, z + s * math.sin(t)),
               (x + s * math.cos(t + 2.1), 0.009, z + s * math.sin(t + 2.1)), (x, 0.008, z))
    a.build("glass_shards", M("glass"), root, smooth=False)


# ── The aid post ────────────────────────────────────────────────────────────────────────
def aid_post(root, p, w, h, d):
    """Where people were checked before the trams: a white gazebo tent (w by d), a folding table with
    its clipboards, stretchers, a floodlight on a stand fed by a generator, lit, and ("covered": n)
    a body or two under sheets."""
    rng = random.Random(p.get("seed", 19))
    canvas, steel = M(CANVAS), M({"color": [0.6, 0.6, 0.62], "rough": 0.35, "metal": 0.9})
    for sx in (-1, 1):
        for sz in (-1, 1):
            rod(root, "tent_leg", (sx * w / 2, 0.0, sz * d / 2), (sx * w / 2, 2.1, sz * d / 2), 0.025, 0.025, steel)
    roof = Acc()
    peak = (0.0, h, 0.0)
    for (ax, az), (bx, bz) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        roof.quad((ax * w / 2, 2.1, az * d / 2), (bx * w / 2, 2.1, bz * d / 2), peak, peak)
    roof.build("tent_roof", canvas, root, smooth=False)
    for sz in (-1,):   # a valance with the cross on it, on the back
        lbox(root, "tent_valance", (-w / 2, 1.85, sz * d / 2 - 0.01), (w / 2, 2.1, sz * d / 2 + 0.01), canvas)
    text(root, p.get("name", "EHBO · HULPPOST"), (0.0, 1.97, d / 2 + 0.02), 0.13, M({"color": [0.05, 0.3, 0.12], "rough": 0.6}),
         font="DejaVuSans-Bold.ttf", depth=0.0)
    lbox(root, "aid_table", (-0.9, 0.72, -d / 2 + 0.3), (0.9, 0.76, -d / 2 + 1.0), M({"color": [0.85, 0.85, 0.82], "rough": 0.5}))
    for sx in (-1, 1):
        rod(root, "table_leg", (sx * 0.85, 0.0, -d / 2 + 0.65), (sx * 0.85, 0.72, -d / 2 + 0.65), 0.02, 0.02, steel)
    _model(root, "ph:clipboard", (-0.4, 0.76, -d / 2 + 0.6), 20.0, scale=1.0)
    for k in range(p.get("stretchers", 2)):
        x = -w / 2 + 0.6 + k * 1.0
        lbox(root, "stretcher", (x - 0.28, 0.22, -0.95), (x + 0.28, 0.25, 0.95), M({"color": [0.12, 0.2, 0.42], "rough": 0.8}))
        for sz in (-1, 1):
            rod(root, "stretcher_pole", (x - 0.3, 0.25, sz * 1.1), (x - 0.3, 0.25, -sz * 1.1), 0.016, 0.016, steel)
            rod(root, "stretcher_pole", (x + 0.3, 0.25, sz * 1.1), (x + 0.3, 0.25, -sz * 1.1), 0.016, 0.016, steel)
            for sx in (-1, 1):
                rod(root, "stretcher_foot", (x + sx * 0.3, 0.0, sz * 0.8), (x + sx * 0.3, 0.25, sz * 0.8), 0.014, 0.014, steel)
    for k in range(p.get("covered", 1)):   # under a sheet: the shape says enough
        x = w / 2 - 0.7 - k * 0.9
        sub = builders.empty_at("covered", (x, 0.0, 0.2), 0.0)
        sub.parent = root
        sub.location = g2b((x, 0.0, 0.2))
        sheet = M({"color": [0.75, 0.75, 0.72], "rough": 0.9, "noise": 0.2})
        kit.soft(sub, "covered_body", (0.0, 0.14, 0.0), (0.55, 0.28, 1.75), sheet, 0.12, 4)
        kit.soft(sub, "covered_head", (0.0, 0.16, -0.75), (0.32, 0.3, 0.3), sheet, 0.12, 3)
        kit.soft(sub, "covered_feet", (0.0, 0.2, 0.82), (0.36, 0.3, 0.16), sheet, 0.06, 3)
    gx, gz = -w / 2 - 1.2, d / 2 - 0.6   # the generator and the floodlight on its stand
    _model(root, "ph:portable_generator", (gx, 0.0, gz), 30.0, fit=[0.7, 0.55, 0.5])
    _model(root, "ph:portable_searchlight", (gx + 0.2, 0.0, gz - 1.2), 140.0, fit=[0.6, 1.8, 0.6])
    import landmarks
    landmarks.spot(root, (gx + 0.2, 1.8, gz - 1.2), (0.0, 0.3, 0.0), p.get("flood", 700.0), (0.95, 0.97, 1.0), size=55.0)
    cable = Acc()
    cable.rod((gx, 0.02, gz), (gx + 0.2, 0.02, gz - 1.2), 0.012, 0.012, 4)
    cable.build("cable", M({"color": [0.02, 0.02, 0.02], "rough": 0.5}), root)


# ── Abandoned vehicles ──────────────────────────────────────────────────────────────────
LIVERY = {   # body, stripe a, stripe b, word, roof light
    "car": ((0.12, 0.13, 0.15), None, None, "", None),
    "taxi": ((0.02, 0.02, 0.025), None, None, "TAXI", (1.0, 0.85, 0.4)),
    "police": ((0.9, 0.9, 0.9), (0.08, 0.15, 0.55), (0.9, 0.35, 0.05), "POLITIE", (0.1, 0.25, 1.0)),
    "ambulance": ((0.92, 0.8, 0.05), (0.1, 0.45, 0.15), (0.92, 0.8, 0.05), "AMBULANCE", (0.1, 0.25, 1.0)),
    "army": ((0.16, 0.18, 0.12), None, None, "", None),
}


def vehicle(root, p, w, h, d):
    """A car or van left where it stopped, along local x (front +x), w long: a bevelled body, glass,
    four wheels, its headlights on, a door ("door_open": "left" | "right") swung wide, a livery
    ("livery": car | taxi | police | ambulance) with its stripes and roof lights lit."""
    body_c, sa, sb, word, roof = LIVERY[p.get("livery", "car")]
    body = M({"color": list(body_c), "rough": 0.25, "metal": 0.5, "noise": 0.05})
    glass, dark = M("glass"), M({"color": [0.02, 0.02, 0.02], "rough": 0.5})
    van = p.get("van", h > 1.8)
    belt = 0.95 if not van else 1.15
    kit.soft(root, "car_body", (0.0, 0.25 + (belt - 0.25) / 2, 0.0), (w, belt - 0.25, d), body, 0.12, 3)
    cab0, cab1 = (-w / 2 + 0.3, w / 2 - 0.9) if van else (-w / 2 + 0.9, w / 2 - 1.2)
    kit.soft(root, "car_cabin", ((cab0 + cab1) / 2, belt + (h - belt) / 2, 0.0), (cab1 - cab0, h - belt, d - 0.1), body, 0.1, 3)
    for sz in (-1, 1):   # the side windows: the front ones on a van, all along on a car
        x0, x1 = (cab1 - 1.0, cab1 - 0.1) if van else (cab0 + 0.1, cab1 - 0.1)
        lbox(root, "car_window", (x0, belt + 0.08, sz * (d / 2 - 0.04) - 0.01), (x1, h - 0.1, sz * (d / 2 - 0.04) + 0.01), glass)
    lbox(root, "windscreen", (cab1 - 0.02, belt + 0.06, -d / 2 + 0.15), (cab1 + 0.01, h - 0.08, d / 2 - 0.15), glass)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = sx * (w / 2 - 0.7)
            wh = kit.lathe(root, "tyre", [(0.0, -0.11), (0.33, -0.11), (0.33, 0.11), (0.0, 0.11)], dark, at=(0.0, 0.0, 0.0), segments=16)
            wh.rotation_euler[0] = math.radians(90)
            wh.location = g2b((x, 0.33, sz * (d / 2 - 0.08)))
    head = builders.emissive("headlight", (1.0, 0.95, 0.85), 12.0)
    tail = builders.emissive("taillight", (1.0, 0.05, 0.03), 4.0)
    for sz in (-1, 1):
        lbox(root, "headlight", (w / 2 - 0.02, 0.62, sz * (d / 2 - 0.3) - 0.12), (w / 2 + 0.02, 0.74, sz * (d / 2 - 0.3) + 0.12), head)
        lbox(root, "taillight", (-w / 2 - 0.02, 0.72, sz * (d / 2 - 0.2) - 0.1), (-w / 2 + 0.02, 0.86, sz * (d / 2 - 0.2) + 0.1), tail)
    if sa:   # the striping down each side (Battenburg blocks on an ambulance, two bands on police)
        for sz in (-1, 1):
            z = sz * (d / 2 + 0.005)
            n = int(w / 0.5)
            for i in range(n):
                c = sa if (i % 2 == 0 or p.get("livery") == "police") else sb
                if p.get("livery") == "police":
                    lbox(root, "stripe", (-w / 2 + 0.2 + i * 0.5, 0.55, z - 0.004), (-w / 2 + 0.7 + i * 0.5, 0.72, z + 0.004), M({"color": list(sa), "rough": 0.3}))
                    lbox(root, "stripe", (-w / 2 + 0.2 + i * 0.5, 0.48, z - 0.004), (-w / 2 + 0.7 + i * 0.5, 0.55, z + 0.004), M({"color": list(sb), "rough": 0.3}))
                else:
                    lbox(root, "stripe", (-w / 2 + 0.2 + i * 0.5, 0.45, z - 0.004), (-w / 2 + 0.7 + i * 0.5, 0.75, z + 0.004), M({"color": list(c), "rough": 0.3}))
            text(root, word, (0.0, belt + 0.25 if van else 0.85, z + sz * 0.006), 0.22, M({"color": [0.05, 0.08, 0.3] if p.get("livery") == "police" else [0.1, 0.4, 0.15], "rough": 0.4}),
                 font="DejaVuSans-Bold.ttf", depth=0.0, yaw=0.0 if sz > 0 else 180.0)
    if roof:   # the roof light, lit (a taxi's sign, or the blue bar left flashing)
        lbox(root, "roof_light", ((cab0 + cab1) / 2 - 0.5, h, -0.35), ((cab0 + cab1) / 2 + 0.5, h + 0.12, 0.35),
             builders.emissive("roof_light_%d" % int(roof[2] * 100), roof, 8.0))
        if word == "TAXI":
            text(root, "TAXI", ((cab0 + cab1) / 2, h + 0.06, 0.36), 0.1, dark, font="DejaVuSans-Bold.ttf", depth=0.0)
    if p.get("door_open"):   # the driver's door swung wide
        sz = 1 if p["door_open"] == "left" else -1
        hinge_x = cab1 - 0.05
        door = builders.empty_at("car_door", (0.0, 0.0, 0.0), 0.0)
        door.parent = root
        door.location = g2b((hinge_x, 0.0, sz * d / 2))
        door.rotation_euler[2] = math.radians(-65 * sz)
        lbox(door, "door_panel", (-1.1, 0.3, -0.04), (0.0, belt, 0.04), body)
        lbox(door, "door_glass", (-1.0, belt, -0.01), (-0.1, h - 0.1, 0.01), glass)


# ── Flood defences and the fire brigade ─────────────────────────────────────────────────
def sandbags(root, p, w, h, d):
    """A wall of sandbags along local x, `h` high (courses of 0.14 m), laid stretcher bond."""
    rng = random.Random(p.get("seed", 23))
    bag = M({"color": [0.42, 0.36, 0.25], "rough": 0.95, "noise": 0.35})
    y, k = 0.0, 0
    while y < h - 0.05:
        x = -w / 2 + (0.3 if k % 2 else 0.0)
        while x < w / 2 - 0.2:
            L = min(0.6, w / 2 - x)
            kit.soft(root, "sandbag", (x + L / 2, y + 0.07, rng.uniform(-0.03, 0.03)), (L - 0.02, 0.15, d), bag, 0.06, 2)
            x += 0.6
        y += 0.14
        k += 1


def fire_pump(root, p, w, h, d):
    """A fire brigade's portable pump on its frame, its hoses snaking off: one down over the quay
    into the canal ("to": [x, z] in the prop's frame), one along the street."""
    red = M({"color": [0.55, 0.04, 0.03], "rough": 0.35, "metal": 0.3})
    steel = M({"color": [0.5, 0.5, 0.52], "rough": 0.35, "metal": 0.9})
    kit.soft(root, "pump", (0.0, 0.35, 0.0), (w, 0.5, d), red, 0.05, 2)
    for sx in (-1, 1):
        rod(root, "pump_frame", (sx * w / 2, 0.0, -d / 2), (sx * w / 2, 0.75, -d / 2), 0.02, 0.02, steel)
        rod(root, "pump_frame", (sx * w / 2, 0.0, d / 2), (sx * w / 2, 0.75, d / 2), 0.02, 0.02, steel)
    hose = Acc()
    tx, tz = p.get("to", [0.0, -3.0])
    pts = [(w / 2, 0.3, 0.0)]
    for k in range(1, 9):   # a slack curve over the ground to the quay edge, then down
        t = k / 8
        pts.append((w / 2 + (tx - w / 2) * t + math.sin(t * 6) * 0.3, 0.06, tz * t))
    pts.append((tx, -2.0, tz - 0.3))
    for a, b in zip(pts, pts[1:]):
        hose.rod(a, b, 0.045, 0.045, 8)
    hose.build("hose", M({"color": [0.75, 0.68, 0.5], "rough": 0.7}), root)


kit.PROPS.update({"evac_board": evac_board, "leaflets": leaflets, "luggage": luggage, "broken_glass": broken_glass,
                  "aid_post": aid_post, "vehicle": vehicle, "sandbags": sandbags, "fire_pump": fire_pump})
