# damned_waters/tools/blender/landmarks.py
# Purpose: the city's landmarks (Blender side), built from a few measurements each, as the street
# kit builds a canal house: the Munttoren (the mint tower on Muntplein: a medieval brick gate tower
# with Hendrick de Keyser's octagonal top, its clock, its open bell lantern and spire), an art-deco
# cinema front (twin tiled towers with copper domes, a stained-glass window, a marquee lined with
# bulbs), the Bloemenmarkt's floating flower stalls, and a pharmacy's green neon cross. Landmarks
# keep their real names; every business on a sign is made up. Coordinates as in street.py (Godot
# frame, metres; a prop's local +z is its front).
#
# ELI5: the city's famous faces. A street of houses can be made from one recipe with the numbers
# changed; a landmark needs its own recipe, because everyone knows what it should look like.
import math

import bpy
from mathutils import Vector

import builders
import facade as layout
import kit
import street
from roomspec import g2b
from street import Acc, M, lbox, rod, text, ball

BRICK = {"ph": "medieval_red_brick", "tint": [0.78, 0.6, 0.52], "scale": 1.0}
SANDSTONE = {"ph": "large_sandstone_blocks", "tint": [0.86, 0.8, 0.7], "scale": 0.8}
LEAD = {"color": [0.1, 0.11, 0.12], "rough": 0.35, "metal": 0.7, "noise": 0.1}
GOLD = {"color": [0.9, 0.66, 0.22], "rough": 0.22, "metal": 1.0}
PAINT = {"color": [0.86, 0.84, 0.78], "rough": 0.5, "noise": 0.08}
COPPER = {"color": [0.22, 0.44, 0.36], "rough": 0.5, "metal": 0.35, "noise": 0.25}   # green with age
BRONZE = {"color": [0.33, 0.22, 0.11], "rough": 0.3, "metal": 0.9, "noise": 0.1}


def emit(color, strength, key=None):
    return builders.emissive(key or "lm_%d_%d_%d_%d" % (*(int(c * 100) for c in color), int(strength * 10)), tuple(color), strength)


def spot(root, at, aim, power, color=(1.0, 0.85, 0.65), size=28.0):
    """A floodlight at `at` aimed at `aim` (both in the root's frame); its fitting is never seen."""
    ld = bpy.data.lights.new("flood", "SPOT")
    ld.energy, ld.color, ld.spot_size, ld.spot_blend = power, color, math.radians(size), 0.6
    ob = bpy.data.objects.new("flood", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.location = g2b(at)
    ob.rotation_euler = (Vector(g2b(aim)) - ob.location).to_track_quat("-Z", "Y").to_euler()
    street.hide_panel(ob)
    return ob


def point(root, at, power, color=(1.0, 0.75, 0.45), radius=0.1):
    ld = bpy.data.lights.new("glow", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = power, color, radius
    ob = bpy.data.objects.new("glow", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.location = g2b(at)
    street.hide_panel(ob)
    return ob


def octagon(root, name, profile, m, y0):
    """A turned octagon with its flat faces to the four points of the compass (as the tower's are)."""
    ob = kit.lathe(root, name, profile, m, at=(0.0, y0, 0.0), segments=8, smooth=False)
    ob.rotation_euler[2] = math.radians(22.5)
    return ob


# ── The Munttoren ────────────────────────────────────────────────────────────────────
def munttoren(root, p, w, h, d):
    """The mint tower: a square brick base (the old city gate's, 1480) with sandstone quoins, a
    lit doorway and lancet windows; on it, behind a balustrade, de Keyser's octagon (1620) with a
    clock on four faces, the open lantern where the carillon hangs, a lead ogee dome and a spire
    with a gilded ball. Floodlit from below, its clock faces glowing. Size: [w, h, d], h to the
    spire's tip (about 36 m)."""
    brick, stone, lead, gold, paint = M(p.get("brick", BRICK)), M(SANDSTONE), M(LEAD), M(GOLD), M(PAINT)
    base = h * 0.36
    kit.soft(root, "tower_plinth", (0.0, 0.45, 0.0), (w + 0.3, 0.9, d + 0.3), stone, 0.04, 2)
    kit.soft(root, "tower_body", (0.0, base / 2, 0.0), (w, base, d), brick, 0.03, 2)
    q = Acc()
    for sx in (-1, 1):   # quoins: long and short stones in turn up each corner
        for sz in (-1, 1):
            y, k = 0.9, 0
            while y < base - 0.9:
                L = 0.85 if k % 2 == 0 else 0.45
                cx, cz = sx * w / 2, sz * d / 2
                xs = sorted((cx - sx * L, cx + sx * 0.03))
                zs = sorted((cz - sz * 0.45, cz + sz * 0.03))
                q.box((xs[0], y, zs[0]), (xs[1], y + 0.34, zs[1]))
                xs = sorted((cx - sx * 0.45, cx + sx * 0.03))
                zs = sorted((cz - sz * L, cz + sz * 0.03))
                q.box((xs[0], y, zs[0]), (xs[1], y + 0.34, zs[1]))
                y += 0.36
                k += 1
    q.build("quoins", stone, root, smooth=False)
    # the doorway on the square (+z): a shop's warm light behind its glass, in a stone surround
    lbox(root, "door_surround", (-1.15, 0.9, d / 2 - 0.02), (1.15, 3.8, d / 2 + 0.06), stone)
    lbox(root, "door_glass", (-0.85, 0.9, d / 2 + 0.06), (0.85, 3.5, d / 2 + 0.08), emit((1.0, 0.72, 0.42), 1.6, "munt_door"))
    for n_out in ((0, 1), (1, 0), (0, -1), (-1, 0)):   # lancet windows, two up each face
        nx, nz = n_out
        rx, rz = nz, -nx
        for y0, lit in ((5.6, n_out == (1, 0)), (9.0, False)):
            c = (nx * (w / 2 + 0.01), y0, nz * (d / 2 + 0.01))
            m = emit((1.0, 0.7, 0.4), 0.8, "munt_lancet") if lit else M({"color": [0.02, 0.025, 0.03], "rough": 0.1, "metal": 0.3})
            lo = (c[0] - rx * 0.35 - nx * 0.05, c[1], c[2] - rz * 0.35 - nz * 0.05)
            hi = (c[0] + rx * 0.35 + nx * 0.02, c[1] + 1.8, c[2] + rz * 0.35 + nz * 0.02)
            lbox(root, "lancet", tuple(map(min, lo, hi)), tuple(map(max, lo, hi)), m)
            lo = (c[0] - rx * 0.5, c[1] - 0.12, c[2] - rz * 0.5)
            hi = (c[0] + rx * 0.5 + nx * 0.12, c[1], c[2] + rz * 0.5 + nz * 0.12)
            lbox(root, "lancet_sill", tuple(map(min, lo, hi)), tuple(map(max, lo, hi)), stone)
    kit.soft(root, "tower_cornice", (0.0, base + 0.25, 0.0), (w + 0.6, 0.5, d + 0.6), stone, 0.05, 2)
    bal = Acc()   # the balustrade round the terrace on top of the base
    for sx, sz, along_x in ((0, 1, True), (0, -1, True), (1, 0, False), (-1, 0, False)):
        n = 16
        for i in range(n + 1):
            t = -0.5 + i / n
            x = t * (w + 0.4) if along_x else sx * (w / 2 + 0.15)
            z = sz * (d / 2 + 0.15) if along_x else t * (d + 0.4)
            bal.rod((x, base + 0.5, z), (x, base + 1.3, z), 0.06, 0.05, 6)
    bal.build("balusters", stone, root)
    for sz in (-1, 1):
        lbox(root, "balustrade_rail", (-w / 2 - 0.3, base + 1.3, sz * (d / 2 + 0.15) - 0.12), (w / 2 + 0.3, base + 1.42, sz * (d / 2 + 0.15) + 0.12), stone)
        lbox(root, "balustrade_rail", (sz * (w / 2 + 0.15) - 0.12, base + 1.3, -d / 2 - 0.3), (sz * (w / 2 + 0.15) + 0.12, base + 1.42, d / 2 + 0.3), stone)
    # the octagon: sandstone, a clock on four faces
    R2 = w * 0.39
    y2 = base + 0.5
    octagon(root, "octagon", [(R2 + 0.18, 0.0), (R2 + 0.18, 0.45), (R2, 0.45), (R2, 5.6), (R2 + 0.28, 5.8), (R2 + 0.28, 6.2), (0.0, 6.2)], stone, y2)
    ap = R2 * math.cos(math.radians(22.5))
    dial = emit((1.0, 0.93, 0.78), 1.4, "munt_dial")
    dark = M({"color": [0.02, 0.02, 0.022], "rough": 0.35, "metal": 0.5})
    hour, minute = (11 + 47 / 60) / 12 * 2 * math.pi, 47 / 60 * 2 * math.pi   # stopped at 11:47
    for nx, nz in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        n = Vector((nx, 0, nz))
        rt = Vector((nz, 0, -nx))   # the viewer's right, facing this dial
        up = Vector((0, 1, 0))
        c = Vector((0, y2 + 3.1, 0)) + n * (ap + 0.02)
        rod(root, "clock_ring", tuple(c - n * 0.02), tuple(c + n * 0.08), 1.18, 1.18, M(GOLD), seg=32)
        rod(root, "clock_dial", tuple(c + n * 0.08), tuple(c + n * 0.1), 1.05, 1.05, dial, seg=32)
        ticks = Acc()
        for k in range(12):
            a = 2 * math.pi * k / 12
            pt = c + n * 0.11 + rt * (math.sin(a) * 0.88) + up * (math.cos(a) * 0.88)
            ticks.rod(tuple(pt - (rt * math.sin(a) + up * math.cos(a)) * 0.12), tuple(pt), 0.035, 0.035, 4)
        for a, L, r in ((hour, 0.55, 0.045), (minute, 0.85, 0.03)):
            tip = c + n * 0.14 + rt * (math.sin(a) * L) + up * (math.cos(a) * L)
            ticks.rod(tuple(c + n * 0.14), tuple(tip), r, r * 0.6, 4)
        ticks.build("clock_hands", dark, root)
    # the open lantern: eight white columns round the bells, lit inside
    R3 = R2 * 0.8
    y3 = y2 + 6.2
    cols = Acc()
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        x, z = R3 * math.cos(a), R3 * math.sin(a)
        cols.rod((x, y3, z), (x, y3 + 4.6, z), 0.17, 0.14, 10)
    cols.build("lantern_columns", paint, root)
    octagon(root, "lantern_floor", [(R3 + 0.3, 0.0), (R3 + 0.3, 0.25), (0.0, 0.25)], stone, y3 - 0.25)
    octagon(root, "lantern_entablature", [(R3 + 0.35, 0.0), (R3 + 0.35, 0.55), (R3 + 0.5, 0.7), (0.0, 0.7)], paint, y3 + 4.6)
    bronze = M(BRONZE)
    for k, (bx, by, bz, br) in enumerate(((0.0, 2.6, 0.0, 0.75), (0.5, 1.2, 0.4, 0.45), (-0.55, 1.4, -0.3, 0.4))):
        kit.lathe(root, "bell", [(br * 1.05, 0.0), (br, 0.08), (br * 0.62, br * 0.6), (br * 0.5, br * 1.05), (0.0, br * 1.12)],
                  bronze, at=(bx, y3 + by, bz), segments=16)
    point(root, (0.0, y3 + 2.4, 0.0), p.get("lantern", 260.0))
    # the ogee dome in lead, the spire, the gilded ball and the vane
    y4 = y3 + 5.3
    ogee = [(R3 + 0.4, 0.0), (R3 + 0.45, 0.25), (R3 * 0.98, 0.9), (R3 * 0.78, 1.6), (R3 * 0.5, 2.2), (R3 * 0.36, 2.7), (0.5, 3.2),
            (0.34, 3.7), (0.0, 3.71)]
    octagon(root, "dome", ogee, lead, y4)
    y5 = y4 + 3.7
    kit.lathe(root, "spire", [(0.32, 0.0), (0.2, 1.2), (0.07, h - y5 - 0.5), (0.0, h - y5)], lead, at=(0.0, y5, 0.0), segments=12)
    ball(root, "gilded_ball", (0.0, y5 + 1.5, 0.0), 0.34, gold, seg=16)
    rod(root, "vane_rod", (0.0, h - 0.6, 0.0), (0.0, h + 0.4, 0.0), 0.03, 0.03, gold)
    lbox(root, "vane", (0.0, h - 0.1, -0.02), (0.9, h + 0.3, 0.02), gold)
    # the floodlights in the square, up at the octagon and the lantern
    fl = p.get("flood", 2600.0)
    for ax, az in ((0.0, 9.0), (9.0, 0.0), (-6.0, 6.0)):
        spot(root, (ax, 0.4, az), (0.0, y2 + 4.5, 0.0), fl, size=26.0)
    spot(root, (0.0, 0.4, 7.0), (0.0, base * 0.5, d / 2), fl * 0.25, size=40.0)


# ── An art-deco cinema front ─────────────────────────────────────────────────────────
POSTERS = [("DE STILLE STAD", (0.15, 0.25, 0.5)), ("NACHTWACHT", (0.5, 0.12, 0.08)), ("HET WATER KOMT", (0.06, 0.32, 0.3)),
           ("LAATSTE TRAM", (0.45, 0.32, 0.08))]


def deco_front(root, f, W, s0, rng):
    """A cinema's front in the style of the 1920s picture palaces: two towers of glazed tiles with
    bronze ribs and copper domes, between them a tiled wall round a great stained-glass window, a
    marquee over the doors lined with bulbs and the theatre's name in neon, a vertical sign down
    one tower, and lit poster cases either side of the doors. The glazed doors themselves are the
    shopfront's (street.shopfront, between the towers). f["deco"]: {"height", "tower_w", "tiles",
    "name", "sign"}."""
    dc = f["deco"]
    H, tw = dc.get("height", 16.0), dc.get("tower_w", 3.2)
    tiles = M(dc.get("tiles", {"color": [0.62, 0.66, 0.56], "rough": 0.35, "noise": 0.1}))
    stone = M({"color": [0.74, 0.68, 0.56], "rough": 0.5, "noise": 0.12})
    bronze, copper, gold = M(BRONZE), M(COPPER), M(GOLD)
    # the wall between the towers, from the ground floor's head up, round the great window
    win = (tw + 1.2, W - tw - 1.2, s0 + 1.8, H - 2.2)
    for u0, u1, v0, v1 in layout.cut_rects(W - 2 * tw, H - s0, [(win[0] - tw, win[1] - tw, win[2] - s0, win[3] - s0)]):
        lbox(root, "deco_wall", (u0 + tw, v0 + s0, -0.4), (u1 + tw, v1 + s0, 0.0), tiles)
    sg = Acc(), Acc(), Acc(), Acc()   # stained glass in a deco pattern: an amber spine, green chevrons, ruby, dark glass
    cols, rows = 8, 12
    for i in range(cols):
        for j in range(rows):
            u0 = win[0] + (win[1] - win[0]) * i / cols
            v0 = win[2] + (win[3] - win[2]) * j / rows
            u1 = u0 + (win[1] - win[0]) / cols
            v1 = v0 + (win[3] - win[2]) / rows
            off = abs(i - (cols - 1) / 2)
            k = 0 if off < 1 else 1 if (j + int(off)) % 4 == 0 else 2 if j % 6 == 3 else 3
            sg[k].quad((u0, v0, -0.3), (u1, v0, -0.3), (u1, v1, -0.3), (u0, v1, -0.3))
    for acc, col, s in zip(sg, ((0.95, 0.5, 0.1), (0.1, 0.55, 0.22), (0.65, 0.05, 0.05), (0.05, 0.12, 0.14)), (0.7, 0.5, 0.5, 0.15)):
        acc.build("stained_glass", emit(col, s, "deco_glass_%d_%d" % (int(col[0] * 100), int(col[1] * 100))), root, smooth=False)
    grid = Acc()
    for i in range(cols + 1):
        u = win[0] + (win[1] - win[0]) * i / cols
        grid.box((u - 0.04, win[2], -0.32), (u + 0.04, win[3], -0.22))
    for j in range(rows + 1):
        v = win[2] + (win[3] - win[2]) * j / rows
        grid.box((win[0], v - 0.04, -0.32), (win[1], v + 0.04, -0.22))
    grid.build("window_bars", bronze, root, smooth=False)
    lbox(root, "deco_cornice", (tw - 0.1, H - 0.1, -0.45), (W - tw + 0.1, H + 0.5, 0.15), stone)
    text(root, "THEATER", (W / 2, H - 1.2, 0.02), 0.95, M({"color": [0.8, 0.62, 0.25], "rough": 0.3, "metal": 0.9}),
         font="DejaVuSerif-Bold.ttf", depth=0.05)
    # the towers: tiles, bronze ribs, little windows, an octagonal drum and a copper dome
    for t0 in (0.0, W - tw):
        lbox(root, "deco_tower", (t0, 0.0, -0.4), (t0 + tw, H + 4.0, 0.5), tiles)
        ribs = Acc()
        for k in (0.25, 0.5, 0.75):
            u = t0 + tw * k
            ribs.box((u - 0.05, s0, 0.5), (u + 0.05, H + 3.6, 0.6))
        for y in (s0 + 1.5, s0 + 5.0, s0 + 8.5):
            ribs.box((t0 + 0.6, y, 0.48), (t0 + tw - 0.6, y + 0.12, 0.62))
        ribs.build("tower_ribs", bronze, root, smooth=False)
        for y in (s0 + 2.2, s0 + 5.7, s0 + 9.2):
            lbox(root, "tower_window", (t0 + 0.9, y, 0.49), (t0 + tw - 0.9, y + 1.8, 0.52), emit((1.0, 0.68, 0.35), 0.5, "deco_tower_win"))
        cx = t0 + tw / 2
        drum = kit.lathe(root, "tower_drum", [(tw * 0.48, 0.0), (tw * 0.48, 1.6), (tw * 0.52, 1.75), (0.0, 1.75)], stone,
                         at=(cx, H + 4.0, 0.05), segments=8, smooth=False)
        drum.rotation_euler[2] = math.radians(22.5)
        kit.lathe(root, "tower_dome", [(tw * 0.5, 0.0), (tw * 0.47, 0.6), (tw * 0.36, 1.4), (tw * 0.18, 2.1), (0.12, 2.5), (0.0, 2.55)],
                  copper, at=(cx, H + 5.75, 0.05), segments=24)
        rod(root, "finial", (cx, H + 8.2, 0.05), (cx, H + 9.6, 0.05), 0.05, 0.02, gold)
        ball(root, "finial_ball", (cx, H + 8.6, 0.05), 0.16, gold, seg=12)
        # poster cases either side of the doors, lit from inside
        title, col = POSTERS[int(t0 > 0) * 2 + rng.randrange(2)]
        lbox(root, "poster_case", (t0 + 0.45, 0.55, 0.5), (t0 + tw - 0.45, 2.55, 0.62), bronze)
        lbox(root, "poster", (t0 + 0.55, 0.65, 0.62), (t0 + tw - 0.55, 2.45, 0.63), emit(col, 1.1, "poster_%s" % title[:6]))
        text(root, title, (cx, 2.15, 0.64), 0.16, emit((1.0, 0.92, 0.75), 2.0, "poster_title"), font="DejaVuSerif-Bold.ttf", depth=0.0)
        text(root, "VANAVOND", (cx, 0.95, 0.64), 0.11, emit((1.0, 0.92, 0.75), 2.0, "poster_title"), font="DejaVuSans-Bold.ttf", depth=0.0)
    # the marquee over the doors: its name in neon, bulbs all round, light pouring down
    import city
    y0, y1, out = s0 - 0.75, s0 - 0.05, dc.get("marquee_out", 2.6)
    lbox(root, "marquee", (tw - 0.2, y0, 0.0), (W - tw + 0.2, y1, out), M({"color": [0.08, 0.06, 0.05], "rough": 0.4, "metal": 0.6}))
    lbox(root, "marquee_soffit", (tw - 0.1, y0 - 0.01, 0.1), (W - tw + 0.1, y0, out - 0.1), emit((1.0, 0.85, 0.6), 1.2, "marquee_soffit"))
    city.neon_text(root, dc.get("name", "CINEMA"), (W / 2, (y0 + y1) / 2, out + 0.04), 0.42, dc.get("sign", (1.0, 0.75, 0.3)), 5.0,
                   font="DejaVuSerif-Bold.ttf", tube=0.012)
    bulbs = Acc()
    n = int((W - 2 * tw + 0.4) / 0.22)
    for i in range(n + 1):
        x = tw - 0.2 + (W - 2 * tw + 0.4) * i / n
        for y in (y0 - 0.02, y1 + 0.02):
            bulbs.rod((x, y, out + 0.02), (x, y, out + 0.08), 0.035, 0.035, 6)
    for x in (tw - 0.2, W - tw + 0.2):
        for k in range(int(out / 0.22)):
            bulbs.rod((x, y0 - 0.02, 0.1 + k * 0.22), (x, y0 - 0.08, 0.1 + k * 0.22), 0.035, 0.035, 6)
    bulbs.build("marquee_bulbs", emit((1.0, 0.86, 0.6), 9.0, "marquee_bulb"), root)
    street.area_light(root, (W / 2, y0 - 0.05, out / 2), W - 2 * tw, out - 0.2, dc.get("power", 400.0), (1.0, 0.8, 0.55), name="marquee_light")
    # floodlit, as the picture palaces were: from the marquee's top up the towers and the window
    for u in (tw / 2, W - tw / 2, W / 2):
        spot(root, (u, s0 + 0.1, out - 0.3), (u, H - 1.0 if u == W / 2 else H + 2.0, 0.0), dc.get("flood", 900.0), size=34.0)
    # the vertical sign down the left tower: THEATER, letter by letter, on both faces
    word = dc.get("vertical", "THEATER")
    top, step = H + 1.5, 1.05
    lbox(root, "vsign", (tw * 0.5 - 0.09, top - step * len(word) - 0.2, 0.6), (tw * 0.5 + 0.09, top + 0.6, 1.9), M({"color": [0.05, 0.04, 0.035], "rough": 0.4, "metal": 0.6}))
    for k, ch in enumerate(word):
        for sgn in (-1, 1):
            city.neon_text(root, ch, (tw * 0.5 + sgn * 0.1, top - step * k, 1.25), 0.8, dc.get("vsign", (1.0, 0.25, 0.2)), 5.0, yaw=90 * sgn,
                           font="DejaVuSans-Bold.ttf", tube=0.02)


# ── The Bloemenmarkt's floating stalls ──────────────────────────────────────────────────
FLOWERS = [(0.75, 0.04, 0.05), (0.95, 0.75, 0.05), (0.92, 0.9, 0.85), (0.9, 0.35, 0.55), (0.95, 0.42, 0.06), (0.4, 0.12, 0.5)]


def buckets(root, rows, rng):
    """Galvanised buckets of tulips, roses and the like on stepped staging: rows [(x0, x1, y, z), ...]."""
    tin, stems = Acc(), Acc()
    heads = [Acc() for _ in FLOWERS]
    for x0, x1, y, z in rows:
        x = x0 + 0.17
        while x < x1 - 0.17:
            tin.rod((x, y, z), (x, y + 0.32, z), 0.15, 0.17, 10)
            k = rng.randrange(len(FLOWERS))
            for _ in range(rng.randint(7, 12)):   # a bunch: stems up out of the water, a head on each
                hx, hz = x + rng.uniform(-0.11, 0.11), z + rng.uniform(-0.11, 0.11)
                hy = y + rng.uniform(0.55, 0.8)
                stems.rod((x + (hx - x) * 0.3, y + 0.3, z + (hz - z) * 0.3), (hx, hy, hz), 0.006, 0.006, 3)
                b = rng.uniform(0.035, 0.05)
                heads[k].box((hx - b, hy, hz - b), (hx + b, hy + b * 2.2, hz + b))
            x += 0.36
    tin.build("buckets", M({"color": [0.5, 0.52, 0.52], "rough": 0.35, "metal": 0.9, "noise": 0.25}), root)
    stems.build("stems", M({"color": [0.08, 0.22, 0.05], "rough": 0.6}), root)
    for acc, col in zip(heads, FLOWERS):
        acc.build("blooms", M({"color": list(col), "rough": 0.55}), root, smooth=False)


def bulb_packets(root, x0, x1, y0, y1, z, rng, facing=1):
    """A board hung with packets of bulbs and seeds, their photos bright (a stall's side wall)."""
    lbox(root, "packet_board", (x0, y0, z - 0.02 * facing), (x1, y1, z), M({"color": [0.06, 0.12, 0.06], "rough": 0.7}))
    packs = [Acc() for _ in FLOWERS]
    y = y0 + 0.05
    while y < y1 - 0.25:
        x = x0 + 0.05
        while x < x1 - 0.16:
            if rng.random() > 0.12:   # (some hooks empty: grabbed on the way out)
                packs[rng.randrange(len(FLOWERS))].box((x, y, min(z, z + 0.02 * facing)), (x + 0.13, y + 0.2, max(z, z + 0.02 * facing)))
            x += 0.16
        y += 0.24
    for acc, col in zip(packs, FLOWERS):
        acc.build("packets", M({"color": [c * 0.9 + 0.08 for c in col], "rough": 0.3}), root, smooth=False)


def flower_stall(root, p, w, h, d):
    """A Bloemenmarkt stall: a glasshouse on a pontoon in the Singel, its open front to the quay
    (+z), staging stepped with buckets of flowers, boards of bulb packets down its sides, a sign
    along its eaves, a string of bulbs, roller shutters part way down ("shutter": 0..1). A stall
    he can walk into ("enter") is a room of its own: here only its roof, sign and front."""
    rng = __import__("random").Random(p.get("seed", 1))
    green = M({"color": [0.04, 0.16, 0.08], "rough": 0.5, "noise": 0.15})
    planks = M({"ph": "wood_peeling_paint_weathered", "tint": [0.35, 0.6, 0.4], "scale": 1.0})
    enter = p.get("enter")
    eave = h - 1.0
    if not enter:
        lbox(root, "pontoon", (-w / 2 - 0.1, -0.7, -d), (w / 2 + 0.1, 0.0, 0.0), M({"ph": "dark_wood", "tint": [0.4, 0.33, 0.28], "scale": 0.6}))
        lbox(root, "stall_back", (-w / 2, 0.0, -d), (w / 2, eave, -d + 0.08), planks)
        for sx in (-1, 1):
            lbox(root, "stall_side", (sx * w / 2 - 0.04, 0.0, -d), (sx * w / 2 + 0.04, eave, 0.0), planks)
        for sx in (-1, 1):   # the packet boards along the side walls, facing in
            xs = sx * (w / 2 - 0.07)
            sub = builders.empty_at("packets", (0.0, 0.0, 0.0), 0.0)
            sub.parent = root
            sub.rotation_euler[2] = math.radians(-90 * sx)
            sub.location = g2b((xs, 0.0, -d / 2))
            bulb_packets(sub, -d / 2 + 0.3, d / 2 - 0.3, 0.5, 2.2, 0.0, rng)
        rows = [(-w / 2 + 0.2, w / 2 - 0.2, 0.0, -0.45), (-w / 2 + 0.2, w / 2 - 0.2, 0.3, -0.85), (-w / 2 + 0.2, w / 2 - 0.2, 0.6, -1.25)]
        for x0, x1, y, z in rows[1:]:   # the staging under the buckets
            lbox(root, "staging", (x0, 0.0, z - 0.2), (x1, y, z + 0.2), M({"ph": "dark_wood", "tint": [0.45, 0.35, 0.28], "scale": 0.5}))
        buckets(root, rows, rng)
        point(root, (0.0, eave - 0.3, -d * 0.4), p.get("power", 70.0), (1.0, 0.86, 0.66), radius=0.5)
    # the roof: glass on green iron, pitched to a ridge over the middle
    frame = Acc()
    n = max(2, int(w / 1.0))
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        frame.rod((x, eave, 0.0), (x, h, -d / 2), 0.03, 0.03, 4)
        frame.rod((x, h, -d / 2), (x, eave, -d), 0.03, 0.03, 4)
    frame.rod((-w / 2, h, -d / 2), (w / 2, h, -d / 2), 0.05, 0.05, 6)
    frame.build("roof_frame", green, root)
    roof = Acc()
    roof.quad((-w / 2, eave, 0.0), (w / 2, eave, 0.0), (w / 2, h, -d / 2), (-w / 2, h, -d / 2))
    roof.quad((-w / 2, h, -d / 2), (w / 2, h, -d / 2), (w / 2, eave, -d), (-w / 2, eave, -d))
    roof.build("roof_glass", M("glass"), root, smooth=False)
    # the sign along the eaves, and the bulbs under it
    lbox(root, "stall_fascia", (-w / 2, eave - 0.45, -0.02), (w / 2, eave, 0.08), green)
    text(root, p.get("name", "BLOEMEN · BOLLEN"), (0.0, eave - 0.22, 0.09), 0.24, M({"color": [0.92, 0.85, 0.6], "rough": 0.4}),
         font="DejaVuSerif-Bold.ttf", depth=0.005)
    bl = Acc()
    for i in range(int(w / 0.4) + 1):
        x = -w / 2 + 0.2 + i * 0.4
        if x < w / 2:
            bl.rod((x, eave - 0.5, 0.06), (x, eave - 0.58, 0.06), 0.03, 0.03, 6)
    bl.build("stall_bulbs", emit((1.0, 0.85, 0.6), 8.0, "stall_bulb"), root)
    # roller shutters, part way down, either side of a way in
    s = p.get("shutter", 0.0)
    gap = p.get("gap")
    if s > 0 or gap:
        shutter = M({"color": [0.12, 0.17, 0.14], "rough": 0.5, "metal": 0.5, "noise": 0.35})
        rib_m = M({"color": [0.05, 0.07, 0.06], "rough": 0.5, "metal": 0.5, "noise": 0.2})
        spans = [(-w / 2, gap[0]), (gap[1], w / 2)] if gap else [(-w / 2, w / 2)]
        for x0, x1 in spans:
            bottom = 0.0 if gap else (eave - 0.45) * (1.0 - s)
            if x1 - x0 < 0.05:
                continue
            lbox(root, "shutter", (x0, bottom, 0.02), (x1, eave - 0.45, 0.06), shutter)
            ribs = Acc()
            y = bottom + 0.1
            while y < eave - 0.5:
                ribs.box((x0, y, 0.06), (x1, y + 0.02, 0.075))
                y += 0.1
            ribs.build("shutter_ribs", rib_m, root, smooth=False)


def flower_buckets(root, p, w, h, d):
    """Staging along local x, three steps up toward the back, every step lined with buckets of
    flowers (a stall's inside)."""
    rng = __import__("random").Random(p.get("seed", 3))
    wood = M({"ph": "dark_wood", "tint": [0.45, 0.35, 0.28], "scale": 0.5})
    rows = []
    for k in range(3):
        y, z = 0.25 * k, d / 2 - 0.15 - k * (d - 0.3) / 2
        if k:
            lbox(root, "staging", (-w / 2, 0.0, z - 0.2), (w / 2, y, z + 0.2), wood)
        rows.append((-w / 2, w / 2, y, z))
    buckets(root, rows, rng)


# ── A pharmacy's green cross ────────────────────────────────────────────────────────────
def green_cross(root, at, size=0.75):
    """The green neon cross a Dutch apotheek hangs over the pavement, lit on both faces."""
    x, y, z = at
    g = emit((0.15, 1.0, 0.3), 4.0, "green_cross")
    a = size / 2
    b = size / 6
    lbox(root, "cross_v", (x - 0.05, y - a, z - b), (x + 0.05, y + a, z + b), g)
    lbox(root, "cross_h", (x - 0.05, y - b, z - a), (x + 0.05, y + b, z + a), g)
    rod(root, "cross_arm", (x, y + a + 0.15, 0.0), (x, y + a + 0.15, z + 0.1), 0.02, 0.02, M(street.IRON))
    rod(root, "cross_hanger", (x, y + a, z), (x, y + a + 0.15, z), 0.012, 0.012, M(street.IRON))


# ── Rokin: the tour boats, their piers, the queen on her horse ───────────────────────────
def canal_boat(root, p, w, h, d):
    """A glass-roofed canal cruise boat along local x (bow at +x): a low dark steel hull, glazed
    sides under a curved roof, rows of seats inside with their lights still on, its name on the
    bow. "list": degrees it heels over (a boat that has taken water); "sunk": metres it sits low."""
    hull_m = M(p.get("hull", {"color": [0.03, 0.05, 0.09], "rough": 0.35, "metal": 0.5, "noise": 0.2}))
    white = M({"color": [0.82, 0.82, 0.8], "rough": 0.4, "noise": 0.08})
    seat = M({"color": [0.32, 0.05, 0.05], "rough": 0.8})
    if p.get("list"):
        root.rotation_euler[0] += math.radians(p["list"])
    if p.get("sunk"):
        root.location.z -= p["sunk"]
    L, Wd = w, d
    bow = 2.2
    hull = Acc()   # a box hull with a pointed bow and a rounded stern
    y0, y1 = -0.75, 0.35
    xs = -L / 2
    xb = L / 2 - bow
    hull.box((xs, y0, -Wd / 2), (xb, y1, Wd / 2))
    hull.quad((xb, y0, -Wd / 2), (L / 2, y0 + 0.4, 0.0), (L / 2, y1 + 0.15, 0.0), (xb, y1, -Wd / 2))
    hull.quad((xb, y0, Wd / 2), (xb, y1, Wd / 2), (L / 2, y1 + 0.15, 0.0), (L / 2, y0 + 0.4, 0.0))
    hull.quad((xb, y1, -Wd / 2), (L / 2, y1 + 0.15, 0.0), (L / 2, y1 + 0.15, 0.0), (xb, y1, Wd / 2))
    hull.build("boat_hull", hull_m, root, smooth=False)
    lbox(root, "boat_rubbing_strake", (xs - 0.05, y1 - 0.08, -Wd / 2 - 0.06), (xb, y1, Wd / 2 + 0.06), M({"color": [0.25, 0.15, 0.08], "rough": 0.5}))
    # the cabin: glazed sides, white posts, a roof of glass curving over
    c0, c1, ch = xs + 1.2, xb - 0.4, h
    lbox(root, "cabin_floor", (c0, y1, -Wd / 2 + 0.15), (c1, y1 + 0.05, Wd / 2 - 0.15), M({"color": [0.12, 0.1, 0.09], "rough": 0.6}))
    posts = Acc()
    n = max(2, int((c1 - c0) / 1.3))
    for i in range(n + 1):
        x = c0 + (c1 - c0) * i / n
        for sz in (-1, 1):
            posts.box((x - 0.04, y1, sz * (Wd / 2 - 0.2) - 0.03), (x + 0.04, y1 + ch * 0.62, sz * (Wd / 2 - 0.2) + 0.03))
    posts.build("cabin_posts", white, root, smooth=False)
    for sz in (-1, 1):
        lbox(root, "cabin_glass", (c0, y1 + 0.45, sz * (Wd / 2 - 0.2) - 0.01), (c1, y1 + ch * 0.62, sz * (Wd / 2 - 0.2) + 0.01), M("glass"))
        lbox(root, "cabin_side", (c0, y1, sz * (Wd / 2 - 0.2) - 0.03), (c1, y1 + 0.45, sz * (Wd / 2 - 0.2) + 0.03), white)
    roof = Acc()
    seg = 8
    for k in range(seg):
        a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
        r = Wd / 2 - 0.2
        za, zb = -r * math.cos(a0), -r * math.cos(a1)
        ya, yb = y1 + ch * 0.62 + 0.45 * math.sin(a0), y1 + ch * 0.62 + 0.45 * math.sin(a1)
        roof.quad((c0, ya, za), (c1, ya, za), (c1, yb, zb), (c0, yb, zb))
    roof.build("cabin_roof", M({"color": [0.04, 0.06, 0.07], "rough": 0.04, "metal": 0.7}), root, smooth=True)   # tinted glass: it mirrors the lamps
    seats = Acc()
    x = c0 + 0.5
    while x < c1 - 0.5:
        for sz in (-1, 1):
            seats.box((x, y1 + 0.05, sz * 0.25), (x + 0.5, y1 + 0.5, sz * (Wd / 2 - 0.35)))
            seats.box((x, y1 + 0.5, sz * 0.25), (x + 0.08, y1 + 1.0, sz * (Wd / 2 - 0.35)))
        x += 1.0
    seats.build("boat_seats", seat, root, smooth=False)
    lbox(root, "cabin_light", (c0 + 0.3, y1 + ch * 0.62 + 0.3, -0.25), (c1 - 0.3, y1 + ch * 0.62 + 0.33, 0.25),
         emit((1.0, 0.85, 0.65), p.get("glow", 2.5), "boat_light"))
    text(root, p.get("name", "RONDVAART 7"), (xs + 2.5, y1 - 0.35, Wd / 2 + 0.01), 0.28, white, font="DejaVuSans-Bold.ttf", depth=0.005)


def pier(root, p, w, h, d):
    """A tour-boat pier along local x, out from the quay over the water (toward -z): planks on
    piles, a rail, a lit sign for the cruises."""
    wood = M({"ph": "dark_wood", "tint": [0.45, 0.35, 0.28], "scale": 0.6})
    lbox(root, "pier_deck", (-w / 2, -0.15, -d), (w / 2, 0.0, 0.0), wood)
    piles = Acc()
    for i in range(int(w / 2.5) + 1):
        x = -w / 2 + i * 2.5
        for z in (-d + 0.15, -0.15):
            piles.rod((x, -2.5, z), (x, 0.4, z), 0.12, 0.12, 8)
    piles.build("pier_piles", wood, root)
    rail = Acc()
    for i in range(int(w / 1.5) + 1):
        x = -w / 2 + i * 1.5
        rail.rod((x, 0.0, -d + 0.05), (x, 1.0, -d + 0.05), 0.025, 0.025, 6)
    rail.rod((-w / 2, 1.0, -d + 0.05), (w / 2, 1.0, -d + 0.05), 0.03, 0.03, 6)
    rail.build("pier_rail", M(street.IRON), root)
    if p.get("sign"):
        rod(root, "pier_sign_post", (w / 2 - 0.3, 0.0, -0.3), (w / 2 - 0.3, 2.6, -0.3), 0.05, 0.05, M(street.IRON))
        lbox(root, "pier_sign", (w / 2 - 1.6, 2.0, -0.33), (w / 2 + 1.0, 2.7, -0.27), M({"color": [0.03, 0.06, 0.15], "rough": 0.4}))
        text(root, p["sign"], (w / 2 - 0.3, 2.35, -0.26), 0.17, emit((1.0, 0.9, 0.7), 3.0, "pier_sign"), font="DejaVuSans-Bold.ttf", depth=0.0)


def equestrian(root, p, w, h, d):
    """A bronze rider on a horse on a tall granite plinth, the name cut in it, floodlit. (The
    horse is a CC0 scan stood in bronze; the rider is built: a long riding habit over the saddle,
    the body upright, a hat.) Size: the plinth's [w, h, d]."""
    granite = M({"color": [0.32, 0.31, 0.3], "rough": 0.45, "noise": 0.3})
    bronze = M({"color": [0.13, 0.17, 0.12], "rough": 0.4, "metal": 0.8, "noise": 0.25})
    kit.soft(root, "plinth_step", (0.0, 0.25, 0.0), (w + 1.0, 0.5, d + 1.0), granite, 0.04, 2)
    kit.soft(root, "plinth", (0.0, 0.5 + (h - 0.8) / 2, 0.0), (w, h - 0.8, d), granite, 0.04, 2)
    kit.soft(root, "plinth_cap", (0.0, h - 0.15, 0.0), (w + 0.25, 0.3, d + 0.25), granite, 0.04, 2)
    text(root, p.get("name", "WILHELMINA"), (0.0, h * 0.55, d / 2 + 0.005), 0.3, M({"color": [0.7, 0.6, 0.35], "rough": 0.3, "metal": 0.8}),
         font="DejaVuSerif-Bold.ttf", depth=0.01)
    horse = builders.empty_at("horse", (0.0, 0.0, 0.0), 0.0)
    horse.parent = root
    horse.location = g2b((0.0, h, 0.0))
    kit.model(horse, {"model": p.get("model", "ph:horse_statue_01"), "fit": [p.get("horse_w", 1.4), p.get("horse_h", 2.6), p.get("horse_l", 3.0)],
                      "tint": [0.13, 0.17, 0.12]}, 0, 0, 0)
    y = h + p.get("saddle", 1.55)
    kit.lathe(root, "rider_habit", [(0.55, 0.0), (0.42, 0.35), (0.24, 0.75), (0.2, 1.0), (0.0, 1.02)], bronze, at=(0.0, y - 0.55, 0.0), segments=14)
    kit.lathe(root, "rider_body", [(0.2, 0.0), (0.22, 0.25), (0.17, 0.55), (0.08, 0.62), (0.0, 0.63)], bronze, at=(0.0, y + 0.45, 0.0), segments=12)
    ball(root, "rider_head", (0.0, y + 1.2, 0.0), 0.12, bronze, seg=12)
    kit.lathe(root, "rider_hat", [(0.2, 0.0), (0.2, 0.03), (0.1, 0.05), (0.09, 0.16), (0.0, 0.17)], bronze, at=(0.0, y + 1.28, 0.0), segments=14)
    for sz in (-1, 1):
        spot(root, (sz * 4.0, 0.4, 4.0), (0.0, h + 1.6, 0.0), p.get("flood", 900.0), size=26.0)


# ── Fronts: a museum's stone, a hotel's flags, the metro's glass ──────────────────────────
def classic_front(root, f, W, rng):
    """A neo-renaissance stone front (a museum in an old bank): a rusticated ground floor round
    arched doors, giant pilasters up two floors between tall windows, a deep cornice, the name on
    the attic, banners hung between the pilasters. f["classic"]: {"height", "name", "banners"}."""
    c = f["classic"]
    H = c.get("height", 17.0)
    stone = M({"ph": "large_sandstone_blocks", "tint": [0.78, 0.74, 0.66], "scale": 0.8})
    dark = M({"color": [0.02, 0.025, 0.03], "rough": 0.15, "metal": 0.3})
    n = c.get("bays", 5)
    bay = W / n
    g0 = c.get("ground", 5.0)
    holes = []
    for i in range(n):   # arched doors and windows below, tall windows above
        u = bay * (i + 0.5)
        holes.append((u - bay * 0.22, u + bay * 0.22, 0.6 if i != n // 2 else 0.0, g0 - 0.9))
        holes.append((u - bay * 0.2, u + bay * 0.2, g0 + 0.9, g0 + 4.6))
        holes.append((u - bay * 0.2, u + bay * 0.2, g0 + 6.0, H - 3.2))
    for u0, u1, v0, v1 in layout.cut_rects(W, H, holes):
        lbox(root, "stone", (u0, v0, -0.5), (u1, v1, 0.0), stone)
    for u0, u1, v0, v1 in holes:
        lit = rng.random() < 0.3
        m = emit((1.0, 0.75, 0.45), 0.6, "museum_lit") if lit else dark
        lbox(root, "museum_window", (u0, v0, -0.42), (u1, v1, -0.38), m)
    bands = Acc()   # rustication on the ground floor; a band at each floor; the pilasters
    for k in range(int(g0 / 0.5)):
        bands.box((0.0, k * 0.5, 0.0), (W, k * 0.5 + 0.04, 0.03))
    for y in (g0, g0 + 5.4):
        bands.box((-0.1, y - 0.15, 0.0), (W + 0.1, y + 0.15, 0.25))
    for i in range(n + 1):
        u = bay * i
        bands.box((u - 0.32, g0 + 0.15, 0.0), (u + 0.32, H - 2.4, 0.3))
        bands.box((u - 0.42, H - 2.7, 0.0), (u + 0.42, H - 2.4, 0.4))
    bands.build("museum_order", stone, root, smooth=False)
    lbox(root, "museum_cornice", (-0.3, H - 2.4, -0.5), (W + 0.3, H - 1.6, 0.7), stone)
    lbox(root, "museum_attic", (0.0, H - 1.6, -0.5), (W, H, 0.1), stone)
    text(root, c.get("name", "MUSEUM"), (W / 2, H - 0.8, 0.12), 0.7, M({"color": [0.25, 0.2, 0.15], "rough": 0.6}), font="DejaVuSerif-Bold.ttf", depth=0.02)
    for k, (title, col) in enumerate(c.get("banners", [])):   # long cloth banners between the pilasters
        u = bay * (1 + k * 2) if 1 + k * 2 < n else bay * (k + 0.5)
        lbox(root, "banner", (u - 0.45, g0 + 1.0, 0.32), (u + 0.45, g0 + 6.8, 0.34), M({"color": list(col), "rough": 0.8}))
        for j, ch in enumerate(title[:10]):
            text(root, ch, (u, g0 + 6.3 - j * 0.55, 0.35), 0.42, M({"color": [0.95, 0.92, 0.85], "rough": 0.6}), font="DejaVuSans-Bold.ttf", depth=0.0)
    for sx in (-1, 1):   # lamps either side of the door
        u = W / 2 + sx * bay * 0.4
        lbox(root, "museum_lamp", (u - 0.12, 2.4, 0.2), (u + 0.12, 2.9, 0.44), emit((1.0, 0.8, 0.55), 6.0, "museum_lamp"))


def hotel_flags(root, W, y, n=3, colors=None):
    """Flagpoles out over the street from a grand hotel's first floor, their flags hanging."""
    colors = colors or [(0.6, 0.05, 0.05), (0.05, 0.1, 0.35), (0.85, 0.8, 0.7)]
    for k in range(n):
        u = W * (k + 1) / (n + 1)
        rod(root, "flagpole", (u, y, 0.05), (u, y + 1.6, 1.8), 0.035, 0.03, M(GOLD))
        a = Acc()
        a.quad((u, y + 1.55, 1.75), (u, y + 1.0, 1.15), (u, y - 0.2, 1.15), (u, y + 0.35, 1.75))
        a.build("flag", M({"color": list(colors[k % len(colors)]), "rough": 0.8}), root, smooth=False)


def metro_front(root, f, W, s0, rng):
    """A metro station's way in, set into a building: a full-height glass front in thin steel, the
    ticket hall lit behind it, a steel canopy, the station's name, and out on the pavement the
    metro's sign on its pole. (The doors are the shopfront's.)"""
    m = f["metro"]
    steel = M({"color": [0.42, 0.44, 0.46], "rough": 0.3, "metal": 0.9})
    lbox(root, "metro_canopy", (0.2, s0 - 0.35, 0.0), (W - 0.2, s0 - 0.1, 2.2), steel)
    lbox(root, "metro_canopy_light", (0.4, s0 - 0.36, 0.2), (W - 0.4, s0 - 0.35, 2.0), emit((0.9, 0.95, 1.0), 2.5, "metro_canopy"))
    text(root, m.get("name", "ROKIN"), (W / 2, s0 - 0.22, 2.21), 0.22, emit((1.0, 1.0, 1.0), 4.0, "metro_name"), font="DejaVuSans-Bold.ttf", depth=0.0)
    x = m.get("pole_u", W - 0.6)
    rod(root, "metro_pole", (x, 0.0, 2.6), (x, 3.6, 2.6), 0.06, 0.06, steel)
    lbox(root, "metro_sign", (x - 0.45, 3.6, 2.5), (x + 0.45, 4.5, 2.7), emit((0.85, 0.05, 0.05), 3.0, "metro_sign_red"))
    for sgn in (-1, 1):
        text(root, "M", (x, 4.05, 2.6 + sgn * 0.105), 0.62, emit((1.0, 1.0, 1.0), 5.0, "metro_m"), font="DejaVuSans-Bold.ttf", depth=0.0,
             yaw=0.0 if sgn > 0 else 180.0)


# ── Police lines ─────────────────────────────────────────────────────────────────────
def crowd_barrier(root, p, w, h, d):
    """A row of galvanised crowd barriers (dranghekken) along local x, hooked end to end on their
    flat feet, police tape tied along the top ("tape": false for none). Some knocked askew."""
    rng = __import__("random").Random(p.get("seed", 9))
    steel = M({"color": [0.55, 0.57, 0.58], "rough": 0.35, "metal": 0.9, "noise": 0.3})
    n = max(1, int(w / 2.3))
    bars = Acc()
    for i in range(n):
        x0 = -w / 2 + w * i / n + 0.05
        x1 = -w / 2 + w * (i + 1) / n - 0.05
        dz = rng.uniform(-0.25, 0.25) if i % 3 == 2 else 0.0
        for x in (x0, x1):
            bars.rod((x, 0.0, dz), (x, h, dz), 0.022, 0.022, 6)
            bars.rod((x, 0.02, dz - 0.35), (x, 0.02, dz + 0.35), 0.02, 0.02, 4)   # its foot
        for y in (0.12, h):
            bars.rod((x0, y, dz), (x1, y, dz), 0.022, 0.022, 6)
        k = max(2, int((x1 - x0) / 0.12))
        for j in range(1, k):
            x = x0 + (x1 - x0) * j / k
            bars.rod((x, 0.12, dz), (x, h, dz), 0.008, 0.008, 4)
    bars.build("crowd_barrier", steel, root)
    if p.get("tape", True):
        lbox(root, "police_tape", (-w / 2, h - 0.08, -0.004), (w / 2, h - 0.01, 0.004),
             M({"pattern": "stripes", "colors": [[0.8, 0.05, 0.04], [0.92, 0.92, 0.9]], "width": 0.18}))


kit.PROPS.update({"munttoren": munttoren, "flower_stall": flower_stall, "crowd_barrier": crowd_barrier, "flower_buckets": flower_buckets,
                  "canal_boat": canal_boat, "pier": pier, "equestrian": equestrian})
