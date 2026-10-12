# damned_waters/tools/blender/shops.py
# Purpose: the shop-interior kit (Blender side) for the rooms he can walk into off the street: shelving
# stocked with packets and bottles (gaps where they were grabbed, a few knocked to the floor),
# counters with a till, glass display cases, velvet ropes on brass posts, lit posters, a cinema's
# ticket booth, a cloakroom rail with the coats still on it, fluorescent strip lights. Products are
# boxes and cylinders gathered into one mesh per colour (a shelf of a thousand packets costs a
# handful of objects). Coordinates as in street.py (Godot frame, metres; a prop's local +z is its
# front, its footprint centred on its spot).
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
    lbox(root, "case_light", (-w / 2 + 0.05, h - 0.03, -d / 2 + 0.05), (w / 2 - 0.05, h - 0.01, d / 2 - 0.05),
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
    cols = [(0.05, 0.05, 0.06), (0.18, 0.13, 0.08), (0.1, 0.12, 0.16), (0.3, 0.05, 0.05), (0.22, 0.2, 0.17)]
    x = -w / 2 + 0.2
    while x < w / 2 - 0.2:
        if rng.random() < 0.75:
            ln = rng.uniform(0.9, 1.25)
            c = cols[rng.randrange(len(cols))]
            kit.soft(root, "coat", (x, h - 0.08 - ln / 2, 0.0), (0.12, ln, rng.uniform(0.42, 0.52)),
                     M({"color": list(c), "rough": 0.85, "noise": 0.25}), 0.05, 2)
            kit.soft(root, "coat_shoulders", (x, h - 0.12, 0.0), (0.16, 0.1, 0.46), M({"color": list(c), "rough": 0.85}), 0.04, 2)
        x += rng.uniform(0.16, 0.26)


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
                  "poster": poster, "ticket_booth": ticket_booth, "coat_rack": coat_rack, "strip_light": strip_light})
