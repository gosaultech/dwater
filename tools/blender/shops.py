# damned_waters/tools/blender/shops.py
# Purpose: the shop-interior kit (Blender side) for the rooms he can walk into off the street: shelving
# stocked with packets and bottles (gaps where they were grabbed, a few knocked to the floor),
# counters with a till, glass display cases, velvet ropes on brass posts, lit posters, a cinema's
# ticket booth, a cloakroom rail with the coats still on it, fluorescent strip lights, a gun shop's
# wall rack, a souvenir shop's clogs and cheeses, an exchange's rates board, its cashier's glass and
# its safe. Products are boxes and cylinders gathered into one mesh per colour (a shelf of a
# thousand packets costs a handful of objects). Coordinates as in street.py (Godot frame, metres;
# a prop's local +z is its front, its footprint centred on its spot).
#
# ELI5: a set dresser's van. The architect (builders.py) puts up the walls; this fills the shelves,
# so a shop looks like it was open until a moment ago.
import math
import random

import builders
import kit
import street
from street import Acc, M, lbox, rod, text, ball

PALETTES = {   # what a shop's packets look like from across the room
    "pharmacy": [(0.92, 0.92, 0.9), (0.55, 0.75, 0.92), (0.45, 0.8, 0.55), (0.92, 0.55, 0.7), (0.12, 0.2, 0.45), (0.95, 0.6, 0.15)],
    "candy": [(0.85, 0.08, 0.08), (0.95, 0.8, 0.1), (0.1, 0.3, 0.8), (0.5, 0.12, 0.55), (0.95, 0.45, 0.1), (0.9, 0.9, 0.88)],
    "grocery": [(0.8, 0.15, 0.1), (0.95, 0.85, 0.3), (0.2, 0.45, 0.2), (0.9, 0.9, 0.85), (0.35, 0.2, 0.1), (0.15, 0.3, 0.65)],
    "souvenir": [(0.95, 0.45, 0.05), (0.85, 0.1, 0.1), (0.1, 0.25, 0.75), (0.95, 0.95, 0.9), (0.95, 0.8, 0.15), (0.1, 0.1, 0.1)],
    "ammo": [(0.24, 0.28, 0.16), (0.62, 0.1, 0.07), (0.82, 0.66, 0.14), (0.12, 0.18, 0.36), (0.1, 0.1, 0.1), (0.8, 0.78, 0.72)],   # cartridge boxes
    "guns": [(0.06, 0.06, 0.065), (0.12, 0.12, 0.13), (0.3, 0.2, 0.12), (0.05, 0.05, 0.05), (0.4, 0.4, 0.42), (0.16, 0.12, 0.08)],  # pistols, scopes, knives
    "bar": [(0.45, 0.22, 0.05), (0.1, 0.25, 0.1), (0.75, 0.72, 0.6), (0.3, 0.12, 0.05), (0.55, 0.05, 0.08), (0.2, 0.2, 0.22)],     # bottles
}
METAL = {"color": [0.55, 0.56, 0.57], "rough": 0.35, "metal": 0.85, "noise": 0.1}
BRASS = {"color": [0.72, 0.52, 0.2], "rough": 0.25, "metal": 1.0, "noise": 0.08}
VELVET = {"color": [0.32, 0.02, 0.03], "rough": 0.85, "noise": 0.2}


def stock(accs, x0, x1, y, z0, z1, rng, empty=0.15, bottles=0.3):
    """Fill one shelf (x0..x1 at height y, depth z0..z1) with packets and bottles in the palette's
    colours (one accumulator per colour). `empty`: how much of it was grabbed; a few lie toppled."""
    x = x0 + 0.02
    while x < x1 - 0.05:
        wv = rng.uniform(0.05, 0.13)
        if x + wv > x1:
            break
        if rng.random() < empty:   # a gap where it was
            x += wv + rng.uniform(0.05, 0.25)
            continue
        acc = accs[rng.randrange(len(accs))]
        hv = rng.uniform(0.1, 0.27)
        depth = (z1 - z0) * rng.uniform(0.6, 0.95)
        n = max(1, int((z1 - z0) / max(depth, 0.05)))
        if rng.random() < bottles:   # a row of bottles front to back
            r = min(wv, 0.09) / 2
            for k in range(max(1, int((z1 - z0) / (2 * r + 0.01)))):
                zc = z1 - r - k * (2 * r + 0.01)
                acc.rod((x + r, y, zc), (x + r, y + hv, zc), r, r * 0.8, 8)
        elif rng.random() < 0.06:   # knocked over, lying on its side
            acc.box((x, y, z1 - hv), (x + wv, y + wv * 0.8, z1))
        else:
            for k in range(n):
                acc.box((x, y, z1 - depth * (k + 1) + 0.005), (x + wv, y + hv, z1 - depth * k))
        x += wv + 0.008


def _accs(n):
    return [Acc() for _ in range(n)]


def _build_accs(root, accs, palette, name="stock"):
    for acc, col in zip(accs, palette):
        acc.build(name, M({"color": [c * 0.85 for c in col], "rough": 0.45, "noise": 0.15}), root, smooth=False)


def shelving(root, p, w, h, d):
    """Shop shelving along local x: "double" for a gondola (stocked both sides, its back a pegboard),
    else against a wall (stocked toward +z). "palette": what's on it; "empty": how picked over."""
    rng = random.Random(p.get("seed", 7))
    pal = PALETTES[p.get("palette", "grocery")]
    accs = _accs(len(pal))
    frame = M(p.get("frame", METAL))
    double = p.get("double", False)
    shelves = p.get("shelves", 5)
    lbox(root, "shelf_plinth", (-w / 2, 0.0, -d / 2), (w / 2, 0.12, d / 2), M({"color": [0.08, 0.08, 0.09], "rough": 0.5}))
    lbox(root, "shelf_back", (-w / 2, 0.12, -0.02 if double else -d / 2), (w / 2, h, 0.02 if double else -d / 2 + 0.03), frame)
    for sx in (-1, 1):
        lbox(root, "shelf_upright", (sx * w / 2 - 0.03, 0.0, -d / 2), (sx * w / 2 + 0.03, h, d / 2), frame)
    for k in range(shelves):
        y = 0.12 + (h - 0.3) * k / (shelves - 1)
        zs = ((-d / 2, -0.03), (0.03, d / 2)) if double else ((-d / 2 + 0.04, d / 2),)
        for za, zb in zs:
            lbox(root, "shelf", (-w / 2 + 0.03, y - 0.02, za), (w / 2 - 0.03, y, zb), frame)
            if k < shelves - 1:   # (nothing on the very top)
                stock(accs, -w / 2 + 0.04, w / 2 - 0.04, y, za + 0.02, zb - 0.02, rng, p.get("empty", 0.15), p.get("bottles", 0.3))
        lbox(root, "price_rail", (-w / 2 + 0.03, y - 0.06, d / 2 - 0.01), (w / 2 - 0.03, y, d / 2 + 0.005), M({"color": [0.9, 0.9, 0.88], "rough": 0.5}))
    _build_accs(root, accs, pal)
    fallen = _accs(len(pal))   # what came off the shelves, on the floor in front
    for _ in range(p.get("fallen", 4)):
        a = fallen[rng.randrange(len(pal))]
        x, z = rng.uniform(-w / 2, w / 2), d / 2 + rng.uniform(0.1, 0.7)
        s = rng.uniform(0.06, 0.12)
        a.box((x, 0.0, z), (x + s * 1.6, s * 0.8, z + s))
    _build_accs(root, fallen, pal, "fallen_stock")


def counter(root, p, w, h, d):
    """A shop counter along local x, the customer's side +z: a laminate top, a panelled front, the
    till at one end (a CC0 cash register), a few things left on it."""
    top = M(p.get("top", {"color": [0.85, 0.84, 0.8], "rough": 0.3, "noise": 0.05}))
    body = M(p.get("material", {"ph": "dark_wood", "tint": [0.5, 0.4, 0.32], "scale": 0.5}))
    lbox(root, "counter_body", (-w / 2, 0.0, -d / 2 + 0.05), (w / 2, h - 0.04, d / 2), body)
    lbox(root, "counter_top", (-w / 2 - 0.03, h - 0.04, -d / 2), (w / 2 + 0.03, h, d / 2 + 0.04), top)
    lbox(root, "counter_kick", (-w / 2 + 0.02, 0.0, d / 2 - 0.06), (w / 2 - 0.02, 0.1, d / 2 + 0.005), M({"color": [0.03, 0.03, 0.03], "rough": 0.5}))
    if p.get("till", True):
        till = builders.empty_at("till", (0.0, 0.0, 0.0), 0.0)
        till.parent = root
        till.location = street.g2b((w / 2 - 0.4, h, 0.0))
        kit.model(till, {"model": "ph:CashRegister_01", "fit": [0.45, 0.4, 0.45]}, 0.45, 0.4, 0.45)


def display_case(root, p, w, h, d):
    """A glass-topped display counter (candy, watches, medicine): a lit case on a dark base, its
    goods on two glass shelves."""
    rng = random.Random(p.get("seed", 3))
    pal = PALETTES[p.get("palette", "candy")]
    base = M({"color": [0.05, 0.04, 0.04], "rough": 0.45})
    lbox(root, "case_base", (-w / 2, 0.0, -d / 2), (w / 2, 0.45, d / 2), base)
    glass = M("glass")
    lbox(root, "case_glass", (-w / 2, 0.45, -d / 2), (w / 2, h, d / 2), glass)
    lbox(root, "case_light", (-w / 2 + 0.05, h - 0.03, -d / 2 + 0.04), (w / 2 - 0.05, h - 0.01, -d / 2 + 0.1),   # a strip at the back: the top stays glass
         builders.emissive("case_light", (1.0, 0.95, 0.85), 1.5))
    accs = _accs(len(pal))
    for y in (0.47, 0.47 + (h - 0.47) * 0.5):
        lbox(root, "case_shelf", (-w / 2 + 0.03, y - 0.01, -d / 2 + 0.03), (w / 2 - 0.03, y, d / 2 - 0.03), glass)
        for _ in range(int(w * 14)):
            if rng.random() < p.get("empty", 0.3):
                continue
            x, z = rng.uniform(-w / 2 + 0.06, w / 2 - 0.06), rng.uniform(-d / 2 + 0.06, d / 2 - 0.06)
            s = rng.uniform(0.03, 0.06)
            accs[rng.randrange(len(pal))].box((x - s, y, z - s), (x + s, y + s * 1.2, z + s))
    _build_accs(root, accs, pal)


def stanchions(root, p, w, h, d):
    """Brass posts along local x with velvet ropes sagging between them (a cinema's queue)."""
    brass, velvet = M(BRASS), M(VELVET)
    n = max(1, int(w / 1.4))
    posts = Acc()
    ropes = Acc()
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        posts.rod((x, 0.0, 0.0), (x, 0.03, 0.0), 0.17, 0.17, 16)
        posts.rod((x, 0.03, 0.0), (x, h, 0.0), 0.028, 0.028, 10)
        if i < n:
            x1 = x + w / n
            seg = 8
            for k in range(seg):
                t0, t1 = k / seg, (k + 1) / seg
                s0, s1 = 4 * t0 * (1 - t0) * 0.18, 4 * t1 * (1 - t1) * 0.18
                ropes.rod((x + (x1 - x) * t0, h - 0.06 - s0, 0.0), (x + (x1 - x) * t1, h - 0.06 - s1, 0.0), 0.022, 0.022, 6)
    posts.build("stanchion", brass, root)
    ropes.build("rope", velvet, root)
    for i in range(n + 1):
        ball(root, "stanchion_top", (-w / 2 + w * i / n, h, 0.0), 0.04, brass, seg=10)


def poster(root, p, w, h, d):
    """A lit poster in a frame on the wall (facing +z): a colour, a title, a line under it."""
    col = p.get("color", (0.15, 0.25, 0.5))
    lbox(root, "poster_frame", (-w / 2, 0.0, 0.0), (w / 2, h, 0.05), M(p.get("frame", BRASS)))
    lbox(root, "poster_sheet", (-w / 2 + 0.06, 0.06, 0.05), (w / 2 - 0.06, h - 0.06, 0.055),
         builders.emissive("poster_" + p.get("title", "x")[:8], tuple(col), p.get("glow", 0.9)))
    ink = builders.emissive("poster_ink", (1.0, 0.93, 0.78), 1.8)
    text(root, p.get("title", ""), (0.0, h * 0.78, 0.06), min(0.16, 1.4 * w / max(len(p.get("title", "x")), 1)), ink,
         font="DejaVuSerif-Bold.ttf", depth=0.0)
    if p.get("line"):
        text(root, p["line"], (0.0, h * 0.14, 0.06), 0.06, ink, font="DejaVuSans-Bold.ttf", depth=0.0)


def ticket_booth(root, p, w, h, d):
    """A cinema's ticket booth: a bronze-trimmed box glazed above the counter, a lit KASSA sign,
    the window's little arch to speak through."""
    wood = M({"ph": "dark_wood", "tint": [0.55, 0.38, 0.28], "scale": 0.5})
    brass = M(BRASS)
    lbox(root, "booth_base", (-w / 2, 0.0, -d / 2), (w / 2, 1.05, d / 2), wood)
    lbox(root, "booth_ledge", (-w / 2 - 0.05, 1.05, -d / 2 - 0.05), (w / 2 + 0.05, 1.1, d / 2 + 0.12), brass)
    lbox(root, "booth_glass", (-w / 2 + 0.05, 1.1, d / 2 - 0.06), (w / 2 - 0.05, h - 0.4, d / 2 - 0.04), M("glass"))
    for sx in (-1, 1):
        lbox(root, "booth_post", (sx * w / 2 - 0.06, 1.1, -d / 2), (sx * w / 2 + 0.06, h - 0.4, d / 2), wood)
        lbox(root, "booth_side_glass", (sx * w / 2 - 0.02, 1.1, -d / 2 + 0.1), (sx * w / 2 + 0.02, h - 0.4, d / 2 - 0.1), M("glass"))
    lbox(root, "booth_top", (-w / 2 - 0.08, h - 0.4, -d / 2 - 0.08), (w / 2 + 0.08, h, d / 2 + 0.08), wood)
    lbox(root, "booth_sign", (-w / 2 + 0.1, h - 0.36, d / 2 + 0.08), (w / 2 - 0.1, h - 0.04, d / 2 + 0.1), M({"color": [0.05, 0.04, 0.03], "rough": 0.4}))
    text(root, p.get("name", "KASSA"), (0.0, h - 0.2, d / 2 + 0.11), 0.18, builders.emissive("booth_sign", (1.0, 0.8, 0.45), 4.0),
         font="DejaVuSerif-Bold.ttf", depth=0.0)
    lbox(root, "booth_inside", (-w / 2 + 0.1, 1.1, -d / 2 + 0.1), (w / 2 - 0.1, h - 0.45, -d / 2 + 0.12),
         builders.emissive("booth_inside", (1.0, 0.78, 0.5), 0.8))
    kit.model(root, {"model": "ph:CashRegister_01", "fit": [0.4, 0.35, 0.4]}, 0.4, 0.35, 0.4)
    for o in root.children:
        if o.name.startswith("model_"):
            o.location.z += 1.1


def coat_rack(root, p, w, h, d):
    """A cloakroom rail along local x with the coats still on it, numbered tags on the hooks."""
    rng = random.Random(p.get("seed", 5))
    rail = M(BRASS)
    rod(root, "coat_rail", (-w / 2, h, 0.0), (w / 2, h, 0.0), 0.02, 0.02, rail)
    for sx in (-1, 1):
        rod(root, "coat_rail_post", (sx * w / 2, 0.0, 0.0), (sx * w / 2, h, 0.0), 0.025, 0.025, rail)
    cols = [tuple(c) for c in p.get("colors", [(0.05, 0.05, 0.06), (0.18, 0.13, 0.08), (0.1, 0.12, 0.16), (0.3, 0.05, 0.05), (0.22, 0.2, 0.17)])]
    x = -w / 2 + 0.2
    while x < w / 2 - 0.2:
        if rng.random() < 0.75:
            ln = rng.uniform(0.9, 1.25)
            c = cols[rng.randrange(len(cols))]
            kit.soft(root, "coat", (x, h - 0.08 - ln / 2, 0.0), (0.12, ln, rng.uniform(0.42, 0.52)),
                     M({"color": list(c), "rough": 0.85, "noise": 0.25}), 0.05, 2)
            kit.soft(root, "coat_shoulders", (x, h - 0.12, 0.0), (0.16, 0.1, 0.46), M({"color": list(c), "rough": 0.85}), 0.04, 2)
        x += rng.uniform(0.16, 0.26)


def gun_rack(root, p, w, h, d):
    """A gun shop's wall rack along local x, its face +z: a cupboard below, a felt-lined ledge the
    butts stand on, a notched rail the barrels lean in, long guns upright in a row (a CC0 rifle).
    Most slots are empty (taken); the first "chained" from the left are still there, a steel cable
    through their trigger guards and a padlock on it. "slots": how many; "left": how many of the
    unchained slots still hold a gun."""
    rng = random.Random(p.get("seed", 13))
    wood = M({"ph": "dark_wood", "tint": [0.42, 0.3, 0.22], "scale": 0.5})
    felt = M({"color": [0.12, 0.2, 0.12], "rough": 0.95, "noise": 0.2})
    ledge = 0.95
    lbox(root, "rack_back", (-w / 2, 0.0, -d / 2), (w / 2, h, -d / 2 + 0.03), wood)
    lbox(root, "rack_cupboard", (-w / 2, 0.0, -d / 2 + 0.03), (w / 2, ledge - 0.04, d / 2), wood)
    lbox(root, "rack_kick", (-w / 2 + 0.02, 0.0, d / 2 - 0.04), (w / 2 - 0.02, 0.1, d / 2 + 0.005), M({"color": [0.03, 0.03, 0.03], "rough": 0.5}))
    for i in range(max(1, int(w / 0.9))):   # the cupboard's doors
        x0 = -w / 2 + w * i / max(1, int(w / 0.9))
        lbox(root, "rack_door_gap", (x0 - 0.004, 0.12, d / 2), (x0 + 0.004, ledge - 0.08, d / 2 + 0.004), M({"color": [0.02, 0.015, 0.01], "rough": 0.8}))
    lbox(root, "rack_ledge", (-w / 2, ledge - 0.04, -d / 2 + 0.03), (w / 2, ledge, d / 2), felt)
    rail_y = ledge + 0.95
    lbox(root, "rack_rail", (-w / 2, rail_y - 0.05, -d / 2 + 0.03), (w / 2, rail_y + 0.05, -d / 2 + 0.16), wood)
    lbox(root, "rack_crown", (-w / 2 - 0.03, h - 0.12, -d / 2), (w / 2 + 0.03, h, -d / 2 + 0.12), wood)
    slots = p.get("slots", max(2, int(w / 0.2)))
    chained = min(p.get("chained", 0), slots)
    left = p.get("left", 0)
    full = list(range(chained)) + rng.sample(range(chained, slots), min(left, slots - chained))
    steel = M(METAL)
    for i in range(slots):
        x = -w / 2 + w * (i + 0.5) / slots
        lbox(root, "rack_notch", (x - 0.025, rail_y - 0.051, -d / 2 + 0.1), (x + 0.025, rail_y + 0.051, -d / 2 + 0.161),
             M({"color": [0.02, 0.015, 0.01], "rough": 0.8}))
        if i not in full:
            continue
        gun = builders.empty_at("rack_gun", (0.0, 0.0, 0.0), 0.0, -90.0)   # stood on its butt: its length up
        gun.parent = root
        gun.location = street.g2b((x, ledge + 0.58, -d / 2 + 0.12))
        kit.model(gun, {"model": "ph:bolt_action_rifle_7_62", "fit": [1.15, 0.3, 0.3]}, 1.15, 0.3, 0.3)
    if chained:
        x1 = -w / 2 + w * (chained - 0.5) / slots + 0.12
        rod(root, "rack_cable", (-w / 2 + 0.04, ledge + 0.32, -d / 2 + 0.2), (x1, ledge + 0.32, -d / 2 + 0.2), 0.006, 0.006, steel)
        lbox(root, "rack_padlock", (x1, ledge + 0.24, -d / 2 + 0.17), (x1 + 0.05, ledge + 0.3, -d / 2 + 0.23), M(BRASS))


def clogs(root, p, w, h, d):
    """A souvenir shop's rack of clogs along local x (front +z): stepped shelves, pairs of wooden
    shoes in yellow and painted blue and red, a few pairs gone, one fallen."""
    rng = random.Random(p.get("seed", 17))
    wood = M({"ph": "dark_wood", "tint": [0.55, 0.42, 0.3], "scale": 0.5})
    paints = [Acc() for _ in range(3)]
    cols = [(0.88, 0.7, 0.12), (0.12, 0.25, 0.65), (0.75, 0.1, 0.08)]
    steps = p.get("steps", 4)
    for k in range(steps):
        y, z = 0.25 + k * (h - 0.3) / steps, d / 2 - 0.15 - k * (d - 0.3) / steps
        lbox(root, "clog_shelf", (-w / 2, y - 0.03, z - 0.18), (w / 2, y, z + 0.12), wood)
        x = -w / 2 + 0.12
        while x < w / 2 - 0.2:
            if rng.random() < p.get("empty", 0.2):
                x += 0.26
                continue
            acc = paints[rng.randrange(3)]
            for dx in (0.0, 0.11):   # a pair, toes out
                acc.box((x + dx, y, z - 0.14), (x + dx + 0.09, y + 0.08, z + 0.1))
                acc.box((x + dx + 0.01, y + 0.08, z - 0.14), (x + dx + 0.08, y + 0.11, z - 0.02))
            x += 0.26
    for acc, c in zip(paints, cols):
        acc.build("clogs", M({"color": list(c), "rough": 0.35, "noise": 0.1}), root, smooth=False)


def cheeses(root, p, w, h, d):
    """A cheese shop's stack: wheels of Gouda in their wax (yellow, red, black), the top one cut."""
    rng = random.Random(p.get("seed", 19))
    wax = [M({"color": list(c), "rough": 0.4}) for c in ((0.9, 0.62, 0.08), (0.6, 0.05, 0.04), (0.06, 0.06, 0.06))]
    r = min(w, d) / 2
    y = 0.0
    k = 0
    while y < h - 0.15:
        t = rng.uniform(0.11, 0.15)
        kit.lathe(root, "cheese", [(r * 0.9, 0.0), (r, t * 0.3), (r, t * 0.7), (r * 0.9, t), (0.0, t)], wax[rng.randrange(3)],
                  at=(rng.uniform(-0.02, 0.02), y, rng.uniform(-0.02, 0.02)), segments=24)
        y += t
        k += 1


def rates_board(root, p, w, h, d):
    """An exchange's board of rates: a black panel, the currencies' codes and two columns of
    numbers in orange LEDs, still lit."""
    lbox(root, "board", (-w / 2, 0.0, -d / 2), (w / 2, h, d / 2), M({"color": [0.01, 0.01, 0.012], "rough": 0.3}))
    led = builders.emissive("rates_led", (1.0, 0.45, 0.08), 3.0)
    codes = p.get("codes", ["EUR", "USD", "GBP", "CHF", "JPY", "CNY"])
    rng = random.Random(p.get("seed", 23))
    row = h / (len(codes) + 1)
    text(root, "WIJ KOPEN · WIJ VERKOPEN", (0.0, h - row * 0.55, d / 2 + 0.004), row * 0.35, led, font="DejaVuSans-Bold.ttf", depth=0.0)
    for k, c in enumerate(codes):
        y = h - row * (k + 1.5)
        text(root, c, (-w * 0.32, y, d / 2 + 0.004), row * 0.45, led, font="DejaVuSans-Bold.ttf", depth=0.0)
        for col, x in ((0, 0.05), (1, 0.3)):
            v = rng.uniform(0.6, 1.4) if c != "JPY" else rng.uniform(140, 170)
            text(root, f"{v:.4f}" if c != "JPY" else f"{v:.2f}", (w * x, y, d / 2 + 0.004), row * 0.42, led, font="DejaVuSansMono.ttf", depth=0.0)


def glass_partition(root, p, w, h, d):
    """The cashier's screen across a counter along local x: thick glass panes in a steel frame from
    the counter top (at 1.05) up to h, a steel pass-through tray under each pane, and ("gap": [x,
    width]) the staff door left open."""
    steel = M({"color": [0.5, 0.52, 0.55], "rough": 0.35, "metal": 0.9})
    glass = M("glass")
    gap = p.get("gap")
    top = 1.05
    x = -w / 2
    n = max(1, int(w / 1.2))
    for i in range(n):
        x0, x1 = -w / 2 + w * i / n, -w / 2 + w * (i + 1) / n
        if gap and x1 > gap[0] - gap[1] / 2 and x0 < gap[0] + gap[1] / 2:
            continue
        lbox(root, "pane", (x0 + 0.03, top + 0.12, -0.012), (x1 - 0.03, h, 0.012), glass)
        lbox(root, "tray", ((x0 + x1) / 2 - 0.2, top - 0.02, -0.25), ((x0 + x1) / 2 + 0.2, top + 0.02, 0.25), steel)
        for u in (x0, x1):
            lbox(root, "mullion", (u - 0.03, top, -0.03), (u + 0.03, h, 0.03), steel)
    lbox(root, "head", (-w / 2, h, -0.04), (w / 2, h + 0.08, 0.04), steel)
    for a, b in ((-w / 2, gap[0] - gap[1] / 2), (gap[0] + gap[1] / 2, w / 2)) if gap else ((-w / 2, w / 2),):
        if b - a > 0.05:
            lbox(root, "counter_base", (a, 0.0, -d / 2), (b, top, d / 2), M({"color": [0.12, 0.13, 0.15], "rough": 0.4}))
            lbox(root, "counter_top", (a, top - 0.03, -d / 2 - 0.03), (b, top, d / 2 + 0.03), M({"color": [0.8, 0.79, 0.76], "rough": 0.3}))


def safe(root, p, w, h, d):
    """A floor safe in grey steel, its door ("open") swung wide and the shelves inside bare."""
    steel = M({"color": [0.3, 0.32, 0.34], "rough": 0.35, "metal": 0.8})
    inside = M({"color": [0.05, 0.05, 0.055], "rough": 0.6})
    if p.get("open", True):
        lbox(root, "safe_back", (-w / 2, 0.0, -d / 2), (w / 2, h, -d / 2 + 0.08), steel)
        for s in (-1, 1):
            lbox(root, "safe_side", (s * w / 2 - (0.08 if s > 0 else 0.0), 0.0, -d / 2), (s * w / 2 + (0.08 if s < 0 else 0.0), h, d / 2), steel)
        lbox(root, "safe_top", (-w / 2, h - 0.08, -d / 2), (w / 2, h, d / 2), steel)
        lbox(root, "safe_floor", (-w / 2, 0.0, -d / 2), (w / 2, 0.08, d / 2), steel)
        lbox(root, "safe_shelf", (-w / 2 + 0.08, h / 2, -d / 2 + 0.08), (w / 2 - 0.08, h / 2 + 0.02, d / 2), inside)
        door = lbox(root, "safe_door", (0.0, 0.02, 0.0), (w - 0.02, h - 0.02, 0.1), steel)
        door.location = street.g2b((w / 2, 0.0, d / 2))
        door.rotation_euler[2] = math.radians(-100)   # swung wide on its hinge
        rod(root, "safe_dial", (w / 2 + 0.05, h * 0.6, d / 2 + 0.3), (w / 2 + 0.1, h * 0.6, d / 2 + 0.3), 0.06, 0.06, M(BRASS), seg=16)
    else:
        lbox(root, "safe_body", (-w / 2, 0.0, -d / 2), (w / 2, h, d / 2), steel)
        rod(root, "safe_dial", (0.0, h * 0.6, d / 2), (0.0, h * 0.6, d / 2 + 0.05), 0.06, 0.06, M(BRASS), seg=16)


def strip_light(root, p, w, h, d):
    """A fluorescent strip on the ceiling along local x (hung `h` below it): the tube lit, its
    diffuser and housing round it. The room's own lights do the lighting; this is what you see."""
    lbox(root, "strip_housing", (-w / 2, -0.04, -0.08), (w / 2, 0.0, 0.08), M({"color": [0.85, 0.85, 0.83], "rough": 0.4}))
    lbox(root, "strip_tube", (-w / 2 + 0.03, -0.06, -0.05), (w / 2 - 0.03, -0.04, 0.05),
         builders.emissive("strip_tube", tuple(p.get("color", (0.95, 0.98, 1.0))), p.get("glow", 6.0)))


def pilaster(root, p, w, h, d):
    """An art-deco pilaster against the wall (its face +z): fluted, a stepped gilt capital, a lamp
    of frosted glass on its face ("lamp": false for none)."""
    body = M(p.get("material", {"ph": "rosewood_veneer1", "tint": [0.6, 0.42, 0.32], "scale": 0.6}))
    gilt = M({"color": [0.75, 0.55, 0.22], "rough": 0.3, "metal": 0.9})
    lbox(root, "pilaster", (-w / 2, 0.0, -d), (w / 2, h, 0.0), body)
    flutes = Acc()
    for k in range(4):
        x = -w / 2 + w * (k + 0.5) / 4
        flutes.box((x - 0.012, 0.3, 0.0), (x + 0.012, h - 0.5, 0.012))
    flutes.build("flutes", gilt, root, smooth=False)
    for k, (a, b) in enumerate(((h - 0.5, h - 0.38), (h - 0.38, h - 0.24), (h - 0.24, h))):
        e = 0.03 * (k + 1)
        lbox(root, "capital", (-w / 2 - e, a, -d), (w / 2 + e, b, e), gilt)
    if p.get("lamp", True):   # a frosted glass shade, half a cylinder up the pilaster's face
        lbox(root, "sconce_back", (-0.09, 1.9, 0.0), (0.09, 2.5, 0.03), gilt)
        kit.soft(root, "sconce", (0.0, 2.2, 0.08), (0.16, 0.5, 0.1), builders.emissive("sconce", (1.0, 0.78, 0.5), 3.0), 0.04, 2)


def wall_sign(root, p, w, h, d):
    """A sign on the wall (facing +z): its words lit on a dark panel, or painted ("lit": false)."""
    lbox(root, "sign_panel", (-w / 2, 0.0, 0.0), (w / 2, h, 0.03), M(p.get("panel", {"color": [0.03, 0.04, 0.035], "rough": 0.4})))
    col = tuple(p.get("color", (0.3, 1.0, 0.45)))
    m = builders.emissive("wall_sign_%d_%d" % (int(col[0] * 100), int(col[1] * 100)), col, p.get("glow", 3.0)) if p.get("lit", True) \
        else M({"color": list(col), "rough": 0.4})
    text(root, p.get("text", ""), (0.0, h / 2, 0.035), min(h * 0.6, 1.5 * w / max(len(p.get("text", "x")), 1)), m,
         font=p.get("font", "DejaVuSans-Bold.ttf"), depth=0.0)


def ticket_machine(root, p, w, h, d):
    """A metro ticket machine: a steel cabinet, its screen still lit, the card slot, the coin cup."""
    steel = M({"color": [0.45, 0.47, 0.5], "rough": 0.3, "metal": 0.8})
    kit.soft(root, "machine", (0.0, h / 2, 0.0), (w, h, d), steel, 0.03, 2)
    lbox(root, "machine_screen", (-w * 0.35, h * 0.62, d / 2), (w * 0.35, h * 0.85, d / 2 + 0.01),
         builders.emissive("machine_screen", (0.4, 0.6, 0.95), 2.5))
    lbox(root, "machine_slot", (-0.08, h * 0.5, d / 2), (0.08, h * 0.52, d / 2 + 0.02), M({"color": [0.02, 0.02, 0.02], "rough": 0.4}))
    lbox(root, "machine_cup", (-0.12, h * 0.25, d / 2), (0.12, h * 0.33, d / 2 + 0.06), M({"color": [0.05, 0.05, 0.05], "rough": 0.4, "metal": 0.6}))


def ticket_gates(root, p, w, h, d):
    """A line of ticket gates along local x: steel cabinets with glass paddles shut, a green or red
    light on each (all red: the network is shut)."""
    steel = M({"color": [0.5, 0.52, 0.55], "rough": 0.3, "metal": 0.85})
    n = max(2, int(w / 0.9))
    red = builders.emissive("gate_red", (1.0, 0.05, 0.03), 4.0)
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        kit.soft(root, "gate_cabinet", (x, 0.5, 0.0), (0.22, 1.0, d), steel, 0.03, 2)
        lbox(root, "gate_light", (x - 0.05, 1.0, d / 2 - 0.15), (x + 0.05, 1.02, d / 2 - 0.05), red)
        if i < n:
            for sx in (-1, 1):
                lbox(root, "gate_paddle", (x + (w / n) / 2 + sx * 0.02 - (0.25 if sx < 0 else 0.0), 0.35, -0.01),
                     (x + (w / n) / 2 + sx * 0.02 + (0.25 if sx > 0 else 0.0), 1.05, 0.01), M("glass"))


def escalator(root, p, w, h, d):
    """A stopped escalator running down along local -z from the floor (at z = 0) through `h` metres
    over `d`: steps, steel sides, black handrails; at the bottom, the water it runs into ("water":
    how far down it has risen, from the top)."""
    steel = M({"color": [0.55, 0.57, 0.6], "rough": 0.3, "metal": 0.9})
    rail = M({"color": [0.02, 0.02, 0.02], "rough": 0.3})
    steps = Acc()
    n = int(d / 0.4)
    for k in range(n):
        z0, z1 = -k * d / n, -(k + 1) * d / n
        y = -h * k / n
        steps.box((-w / 2 + 0.12, y - 0.2, z1), (w / 2 - 0.12, y, z0))
    steps.build("escalator_steps", M({"color": [0.25, 0.26, 0.27], "rough": 0.4, "metal": 0.7}), root, smooth=False)
    for sx in (-1, 1):
        side = Acc()
        side.quad((sx * w / 2, 0.0, 0.0), (sx * w / 2, -h, -d), (sx * w / 2, -h + 1.0, -d), (sx * w / 2, 1.0, 0.0))
        side.build("escalator_side", steel, root, smooth=False)
        rod(root, "handrail", (sx * (w / 2 - 0.05), 1.0, 0.3), (sx * (w / 2 - 0.05), -h + 1.0, -d), 0.04, 0.04, rail)
    if p.get("water"):
        y = -p["water"]
        lbox(root, "flood", (-w / 2, y - 0.02, -d - 2.0), (w / 2, y, -d * p["water"] / h + 0.1), M("canal_water"))


def lockers(root, p, w, h, d):
    """A row of steel lockers along local x, numbered, one or two hanging open (and empty)."""
    rng = random.Random(p.get("seed", 29))
    steel = M({"color": [0.32, 0.36, 0.42], "rough": 0.4, "metal": 0.7, "noise": 0.15})
    n = max(1, int(w / 0.4))
    lbox(root, "locker_body", (-w / 2, 0.0, -d / 2), (w / 2, h, d / 2 - 0.02), steel)
    for i in range(n):
        x0 = -w / 2 + w * i / n + 0.01
        x1 = x0 + w / n - 0.02
        if rng.random() < p.get("open", 0.2):   # swung open: the dark inside, the door out
            lbox(root, "locker_inside", (x0, 0.05, d / 2 - 0.03), (x1, h - 0.05, d / 2 - 0.02), M({"color": [0.02, 0.02, 0.025], "rough": 0.6}))
            lbox(root, "locker_door", (x0, 0.05, d / 2), (x0 + 0.02, h - 0.05, d / 2 + (x1 - x0)), steel)
        else:
            lbox(root, "locker_door", (x0, 0.05, d / 2 - 0.02), (x1, h - 0.05, d / 2), steel)
            lbox(root, "locker_vent", (x0 + 0.08, h - 0.3, d / 2), (x1 - 0.08, h - 0.2, d / 2 + 0.003), M({"color": [0.05, 0.05, 0.06], "rough": 0.5}))


kit.PROPS.update({"ticket_machine": ticket_machine, "ticket_gates": ticket_gates, "escalator": escalator, "lockers": lockers,
                  "pilaster": pilaster, "wall_sign": wall_sign, "shelving": shelving, "counter": counter, "display_case": display_case, "stanchions": stanchions,
                  "poster": poster, "ticket_booth": ticket_booth, "coat_rack": coat_rack, "strip_light": strip_light,
                  "gun_rack": gun_rack, "clogs": clogs, "cheeses": cheeses, "rates_board": rates_board,
                  "glass_partition": glass_partition, "safe": safe})
