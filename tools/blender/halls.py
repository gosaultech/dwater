# damned_waters/tools/blender/halls.py
# Purpose: the great-hall kit (Blender side) for the city's big interiors, first of them the Beurs van
# Berlage's exchange hall, which the army made a mortuary the night the city was emptied: brick
# arcades down the long walls (round arches on square piers, a gallery over them behind a parapet,
# smaller arches above), the steel trusses and the glazed roof; and what the army brought in: body
# bags in rows (some on trestles, one unzipped and empty), a wooden ammunition crate, work lights on
# tripods, hospital screens, trestle tables with the registration's laptops and clipboards, and the
# refrigerated container at the gate. Coordinates as in street.py (Godot frame, metres; a prop's
# local +z its front, its footprint centred on its spot).
#
# ELI5: Berlage built the exchange like a railway station for money: a long brick box with a glass
# roof on steel. Build one bay (a pier, an arch, a truss) and repeat it down the hall; then fill the
# floor the way the army did, in rows, because rows are how you count.
import math
import random

import builders
import kit
import street
from street import Acc, M, lbox, rod, text

BRICK = {"ph": "red_bricks_04", "tint": [0.78, 0.56, 0.44], "scale": 1.0}
STONE = {"ph": "large_sandstone_blocks", "tint": [0.86, 0.8, 0.68], "scale": 0.8}
STEEL = {"color": [0.16, 0.18, 0.2], "rough": 0.45, "metal": 0.7, "noise": 0.15}
VINYL = {"color": [0.02, 0.022, 0.025], "rough": 0.22, "metal": 0.0, "noise": 0.1}   # a body bag: black, glossy, creased
OLIVE = {"color": [0.17, 0.2, 0.11], "rough": 0.8, "noise": 0.25}


def _round_head(y, spring, span):
    """How far a round (semicircular) arch's opening reaches either side of its middle at height y."""
    if y < spring:
        return span / 2
    t = y - spring
    return math.sqrt(max((span / 2) ** 2 - t * t, 0.0))


def beurs_arcade(root, p, w, h, d):
    """One long wall of the exchange hall along local x (w long, d thick, its hall side +z): square
    brick piers every "bay" metres with round arches between them springing at "spring" (dark
    beyond: the aisles; "open_bays": the arches that are a way through), stone imposts and keystones;
    a gallery behind a brick parapet at "gallery" with smaller round arches over it, two to a bay; the
    plain wall up to h; stone string courses."""
    brick, stone = M(p.get("brick", BRICK)), M(p.get("stone", STONE))
    dark = builders.emissive("aisle_dark", (0.008, 0.008, 0.01), 0.2)
    bay, spring = p.get("bay", 4.4), p.get("spring", 4.2)
    gal = p.get("gallery", 7.2)
    n = max(1, int(round(w / bay)))
    bay = w / n
    pier = p.get("pier", 1.1)
    span = bay - pier
    course = 0.25

    def arch_wall(cx, y0, y1, sp, span_):   # the brick round a round-headed opening, in courses
        y = y0
        while y < y1 - 0.01:
            yt = min(y + course, y1)
            ho = _round_head((y + yt) / 2, sp, span_) if (y + yt) / 2 < sp + span_ / 2 else 0.0
            for lo, hi in ((cx - bay / 2, cx - ho), (cx + ho, cx + bay / 2)) if ho > 0 else ((cx - bay / 2, cx + bay / 2),):
                if hi - lo > 0.02:
                    lbox(root, "arcade_brick", (lo, y, -d / 2), (hi, yt, d / 2), brick)
            y = yt

    for i in range(n):
        cx = -w / 2 + bay * (i + 0.5)
        arch_wall(cx, 0.0, gal, spring, span)                                   # the ground arcade
        if i not in p.get("open_bays", []):
            lbox(root, "aisle", (cx - span / 2, 0.0, -d / 2 - 0.02), (cx + span / 2, spring + span / 2, -d / 2), dark)
        for s in (-1, 1):   # the imposts the arch springs from: a stone block at each pier's edge
            x0, x1 = sorted((cx + s * (span / 2 - 0.15), cx + s * (span / 2 + 0.35)))
            lbox(root, "impost", (x0, spring - 0.25, -d / 2 - 0.05), (x1, spring, d / 2 + 0.06), stone)
        lbox(root, "keystone", (cx - 0.22, spring + span / 2 - 0.15, d / 2), (cx + 0.22, spring + span / 2 + 0.35, d / 2 + 0.08), stone)
        for k in (-1, 1):   # the gallery's arches, two to a bay
            gx, gspan = cx + k * bay / 4, bay / 2 - 0.55
            gsp = gal + 1.6
            y = gal + 1.0
            while y < h - 0.01:
                yt = min(y + course, h)
                ho = _round_head((y + yt) / 2, gsp, gspan) if (y + yt) / 2 < gsp + gspan / 2 else 0.0
                for lo, hi in ((gx - bay / 4, gx - ho), (gx + ho, gx + bay / 4)) if ho > 0 else ((gx - bay / 4, gx + bay / 4),):
                    if hi - lo > 0.02:
                        lbox(root, "gallery_brick", (lo, y, -d / 2), (hi, yt, d / 2), brick)
                y = yt
            lbox(root, "gallery_dark", (gx - gspan / 2, gal + 1.0, -d / 2 - 0.02), (gx + gspan / 2, gsp + gspan / 2, -d / 2), dark)
    lbox(root, "gallery_floor", (-w / 2, gal, -d / 2), (w / 2, gal + 0.2, d / 2 + 0.25), stone)
    lbox(root, "parapet", (-w / 2, gal + 0.2, d / 2 - 0.05), (w / 2, gal + 1.0, d / 2 + 0.2), brick)
    lbox(root, "parapet_coping", (-w / 2, gal + 1.0, d / 2 - 0.1), (w / 2, gal + 1.1, d / 2 + 0.28), stone)
    lbox(root, "string_course", (-w / 2, h - 0.3, -d / 2), (w / 2, h, d / 2 + 0.15), stone)
    lbox(root, "plinth", (-w / 2, 0.0, d / 2), (w / 2, 0.5, d / 2 + 0.06), stone)


def glass_roof(root, p, w, h, d):
    """A glazed roof on steel: trusses across local x (w span) every "bay" metres down local z (d
    long), the root at the eaves, the ridge h over them; purlins along it; the glazing between,
    the night sky dark behind it."""
    steel = M(p.get("steel", STEEL))
    glass = M({"color": [0.02, 0.025, 0.035], "rough": 0.08, "metal": 0.6})
    bay = p.get("bay", 4.4)
    n = max(1, int(round(d / bay)))
    a = Acc()
    for i in range(n + 1):   # the trusses: a bowstring of rafters, a tie, the struts between
        z = -d / 2 + d * i / n
        a.rod((-w / 2, 0.0, z), (0.0, h, z), 0.09, 0.09, 6)
        a.rod((0.0, h, z), (w / 2, 0.0, z), 0.09, 0.09, 6)
        a.rod((-w / 2, 0.0, z), (w / 2, 0.0, z), 0.05, 0.05, 6)
        for k in range(1, 6):
            x = -w / 2 + w * k / 6
            y = h * (1.0 - abs(x) / (w / 2))
            a.rod((x, 0.0, z), (x, y, z), 0.035, 0.035, 5)
            if k < 5:
                x2 = -w / 2 + w * (k + 1) / 6
                a.rod((x, 0.0, z), (x2, h * (1.0 - abs(x2) / (w / 2)), z), 0.03, 0.03, 5)
    for k in range(9):   # the purlins down each slope
        t = k / 8
        for s in (-1, 1):
            x, y = s * w / 2 * (1 - t), h * t
            a.rod((x, y + 0.08, -d / 2), (x, y + 0.08, d / 2), 0.04, 0.04, 5)
    a.build("roof_steel", steel, root)
    g = Acc()
    for s in (-1, 1):
        g.quad((s * w / 2, 0.12, -d / 2), (0.0, h + 0.12, -d / 2), (0.0, h + 0.12, d / 2), (s * w / 2, 0.12, d / 2))
    g.build("roof_glass", glass, root, smooth=False)


def body_bags(root, p, w, h, d):
    """The dead, counted: black body bags in rows across the footprint (w by d), "rows" by "cols",
    each with its white tag on the zip; some laid on trestles ("trestles": a fraction), a few gaps,
    and ("open": n, or "open_cells": [[row, col], ...]) bags unzipped and empty, flat on the floor,
    the way they are when what was in them got up."""
    rng = random.Random(p.get("seed", 3))
    vinyl, tag = M(VINYL), M({"color": [0.9, 0.9, 0.86], "rough": 0.7})
    steel = M({"color": [0.6, 0.6, 0.62], "rough": 0.35, "metal": 0.9})
    rows, cols = p.get("rows", 4), p.get("cols", 6)
    dx, dz = w / cols, d / rows
    empty = set(rng.sample(range(rows * cols), min(p.get("open", 0), rows * cols)))
    empty |= {r * cols + c for r, c in p.get("open_cells", [])}
    tags = Acc()
    legs = Acc()
    for r in range(rows):
        for c in range(cols):
            k = r * cols + c
            if rng.random() < p.get("gaps", 0.08) and k not in empty:
                continue
            x = -w / 2 + dx * (c + 0.5) + rng.uniform(-0.08, 0.08)
            z = -d / 2 + dz * (r + 0.5) + rng.uniform(-0.1, 0.1)
            y = 0.0
            if k not in empty and rng.random() < p.get("trestles", 0.25):   # on a pair of trestles
                y = 0.72
                for zz in (z - 0.6, z + 0.6):
                    lbox(root, "trestle_bar", (x - 0.36, y - 0.05, zz - 0.04), (x + 0.36, y, zz + 0.04), steel)
                    for sx in (-1, 1):
                        legs.rod((x + sx * 0.32, 0.0, zz - 0.12), (x + sx * 0.3, y - 0.05, zz), 0.015, 0.015, 4)
                        legs.rod((x + sx * 0.32, 0.0, zz + 0.12), (x + sx * 0.3, y - 0.05, zz), 0.015, 0.015, 4)
            if k in empty:   # unzipped, flat, the flaps thrown back
                lbox(root, "bag_empty", (x - 0.34, 0.0, z - 1.0), (x + 0.34, 0.02, z + 1.0), vinyl)
                for sx in (-1, 1):
                    flap = kit.soft(root, "bag_flap", (x + sx * 0.5, 0.02, z), (0.3, 0.03, 1.9), vinyl, 0.01, 2)
                    flap.rotation_euler[1] = math.radians(sx * 8)
                continue
            body = kit.soft(root, "body_bag", (x, y + 0.13, z), (0.6, 0.26, 1.95), vinyl, 0.12, 3)
            body.rotation_euler[2] = math.radians(rng.uniform(-4.0, 4.0))
            kit.soft(root, "bag_head", (x, y + 0.16, z - 0.75), (0.42, 0.22, 0.32), vinyl, 0.1, 2)   # the shape says enough
            tags.box((x - 0.05, y + 0.27, z - 0.5), (x + 0.05, y + 0.28, z - 0.36))
    legs.build("trestle_legs", steel, root)
    if tags.v:
        tags.build("bag_tags", tag, root, smooth=False)


def army_crate(root, p, w, h, d):
    """A wooden ammunition crate in army olive: rope handles, a stencilled load ("text"), the lid
    ("open": propped up against it) and the cardboard boxes of rounds inside."""
    wood = M(p.get("material", OLIVE))
    paint = M({"color": [0.85, 0.82, 0.6], "rough": 0.8})
    lbox(root, "crate", (-w / 2, 0.0, -d / 2), (w / 2, h - 0.03, d / 2), wood)
    for s in (-1, 1):   # the battens and the rope handles at the ends
        lbox(root, "batten", (s * w / 2 - 0.03, 0.05, -d / 2 - 0.01), (s * w / 2 + 0.03, h - 0.06, d / 2 + 0.01), wood)
        rod(root, "handle", (s * (w / 2 + 0.03), h * 0.6, -0.12), (s * (w / 2 + 0.03), h * 0.6, 0.12), 0.012, 0.012,
            M({"color": [0.55, 0.48, 0.32], "rough": 0.9}))
    text(root, p.get("text", "MUNITIE"), (0.0, h * 0.55, d / 2 + 0.005), min(0.09, 1.2 * w / max(len(p.get("text", "MUNITIE")), 1)), paint,
         font="DejaVuSans-Bold.ttf", depth=0.0)
    if p.get("open", True):
        lid = lbox(root, "crate_lid", (-w / 2, 0.0, 0.0), (w / 2, 0.03, d), wood)
        lid.location = street.g2b((0.0, h - 0.03, -d / 2))
        lid.rotation_euler[0] = math.radians(-70)   # propped back
        boxes = Acc()
        for i in range(3):
            x = -w / 2 + 0.06 + i * (w - 0.12) / 3
            boxes.box((x, h - 0.12, -d / 2 + 0.05), (x + (w - 0.16) / 3, h - 0.03, d / 2 - 0.05))
        boxes.build("crate_rounds", M({"color": [0.55, 0.42, 0.25], "rough": 0.8}), root, smooth=False)
    else:
        lbox(root, "crate_lid", (-w / 2, h - 0.03, -d / 2), (w / 2, h, d / 2), wood)


def work_light(root, p, w, h, d):
    """A builder's floodlight on a tripod: two heads at the top, blazing cold white, a real light
    aimed where it was set ("aim", in its frame), the cable away along the floor."""
    steel = M({"color": [0.85, 0.65, 0.08], "rough": 0.4, "metal": 0.3})
    a = Acc()
    for k in range(3):
        ang = 2 * math.pi * k / 3
        a.rod((0.45 * math.cos(ang), 0.0, 0.45 * math.sin(ang)), (0.0, h * 0.45, 0.0), 0.015, 0.015, 4)
    a.rod((0.0, h * 0.45, 0.0), (0.0, h, 0.0), 0.02, 0.018, 5)
    a.rod((-0.3, h, 0.0), (0.3, h, 0.0), 0.015, 0.015, 4)
    a.build("tripod", steel, root)
    head = builders.emissive("work_head", (0.92, 0.96, 1.0), 18.0)
    for sx in (-0.2, 0.2):
        lbox(root, "work_head", (sx - 0.13, h - 0.12, 0.0), (sx + 0.13, h + 0.1, 0.08), head)
    import landmarks
    landmarks.spot(root, (0.0, h, 0.2), tuple(p.get("aim", [0.0, 0.0, 6.0])), p.get("power", 900.0), (0.9, 0.95, 1.0), size=80.0)


def screen(root, p, w, h, d):
    """A hospital screen along local x: a steel frame on castors, three panels of pale green cloth."""
    steel = M({"color": [0.75, 0.76, 0.77], "rough": 0.3, "metal": 0.9})
    cloth = M({"color": [0.62, 0.7, 0.62], "rough": 0.9, "noise": 0.15})
    a = Acc()
    for k in range(4):
        x = -w / 2 + w * k / 3
        a.rod((x, 0.08, 0.0), (x, h, 0.0), 0.012, 0.012, 5)
        a.rod((x - 0.12, 0.08, 0.0), (x + 0.12, 0.08, 0.0), 0.01, 0.01, 4)
    a.rod((-w / 2, h, 0.0), (w / 2, h, 0.0), 0.01, 0.01, 4)
    a.build("screen_frame", steel, root)
    for k in range(3):
        x0 = -w / 2 + w * k / 3
        lbox(root, "screen_cloth", (x0 + 0.03, 0.35, -0.004), (x0 + w / 3 - 0.03, h - 0.08, 0.004), cloth)


def trestle_table(root, p, w, h, d):
    """A folding table along local x, its working side +z: a white top on steel legs, and on it
    what the registration left ("laptops": n, their screens still on; clipboards; a box of the
    dead's effects in clear bags)."""
    rng = random.Random(p.get("seed", 5))
    steel = M({"color": [0.55, 0.56, 0.58], "rough": 0.35, "metal": 0.9})
    lbox(root, "table_top", (-w / 2, h - 0.04, -d / 2), (w / 2, h, d / 2), M({"color": [0.86, 0.86, 0.84], "rough": 0.5}))
    a = Acc()
    for sx in (-1, 1):
        for sz in (-1, 1):
            a.rod((sx * (w / 2 - 0.1), 0.0, sz * (d / 2 - 0.08)), (sx * (w / 2 - 0.1), h - 0.04, sz * (d / 2 - 0.08)), 0.015, 0.015, 4)
    a.build("table_legs", steel, root)
    for i in range(p.get("laptops", 1)):   # open, the screen still lit with the list
        x = -w / 2 + w * (i + 0.5) / max(p.get("laptops", 1), 1)
        lbox(root, "laptop_base", (x - 0.17, h, -0.12), (x + 0.17, h + 0.02, 0.12), M({"color": [0.08, 0.08, 0.09], "rough": 0.4}))
        scr = lbox(root, "laptop_lid", (-0.17, 0.0, -0.01), (0.17, 0.24, 0.0), builders.emissive("laptop_screen", (0.55, 0.65, 0.85), 1.4))
        scr.location = street.g2b((x, h + 0.02, -0.12))
        scr.rotation_euler[0] = math.radians(-12)
    if p.get("effects", True):   # the dead's things, bagged and numbered
        bags = Acc()
        for k in range(rng.randint(3, 6)):
            x, z = rng.uniform(-w / 2 + 0.2, w / 2 - 0.2), rng.uniform(-d / 2 + 0.1, d / 2 - 0.1)
            bags.box((x - 0.08, h, z - 0.06), (x + 0.08, h + 0.03, z + 0.06))
        bags.build("effects", M({"color": [0.8, 0.82, 0.85], "rough": 0.15, "noise": 0.2}), root, smooth=False)


def reefer(root, p, w, h, d):
    """A refrigerated container along local x (w long, the cold unit at its +x end): ribbed white
    steel, the unit's grille and its status display lit green, the doors at the -x end shut."""
    body = M(p.get("material", {"color": [0.55, 0.56, 0.53], "rough": 0.55, "metal": 0.3, "noise": 0.3, "noise_scale": 1.2, "grime": 1.4}))
    lbox(root, "reefer_box", (-w / 2, 0.0, -d / 2), (w / 2 - 0.25, h, d / 2), body)
    ribs = Acc()
    x = -w / 2 + 0.3
    while x < w / 2 - 0.6:   # the corrugation, as ribs on the long sides
        for s in (-1, 1):
            ribs.box((x, 0.1, s * d / 2 - 0.02), (x + 0.12, h - 0.1, s * d / 2 + 0.02))
        x += 0.3
    ribs.build("reefer_ribs", body, root, smooth=False)
    unit = M({"color": [0.25, 0.27, 0.28], "rough": 0.5, "metal": 0.5})
    lbox(root, "reefer_unit", (w / 2 - 0.25, 0.0, -d / 2), (w / 2, h, d / 2), unit)
    lbox(root, "reefer_grille", (w / 2 + 0.001, 0.5, -d / 2 + 0.3), (w / 2 + 0.01, h - 0.8, d / 2 - 0.3), M({"color": [0.04, 0.04, 0.045], "rough": 0.6}))
    lbox(root, "reefer_display", (w / 2 + 0.011, h - 0.6, -0.15), (w / 2 + 0.02, h - 0.45, 0.15), builders.emissive("reefer_lcd", (0.3, 1.0, 0.45), 3.0))
    text(root, p.get("text", "DEFENSIE"), (0.0, h * 0.7, d / 2 + 0.03), 0.32, M({"color": [0.12, 0.14, 0.1], "rough": 0.6}), font="DejaVuSans-Bold.ttf", depth=0.0)


kit.PROPS.update({"beurs_arcade": beurs_arcade, "glass_roof": glass_roof, "body_bags": body_bags, "army_crate": army_crate,
                  "work_light": work_light, "screen": screen, "trestle_table": trestle_table, "reefer": reefer})
