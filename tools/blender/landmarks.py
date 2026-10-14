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


def octagon(root, name, profile, m, y0, x=0.0, z=0.0):
    """A turned octagon standing at (x, y0, z) with its flat faces to the four points of the compass
    (as the tower's are): turned about its own axis, then put in place."""
    ob = kit.lathe(root, name, profile, m, at=(0.0, y0, 0.0), segments=8, smooth=False)
    ob.rotation_euler[2] = math.radians(22.5)
    ob.location = g2b((x, 0.0, z))
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
    lbox(root, "door_glass", (-0.85, 0.9, d / 2 + 0.06), (0.85, 3.5, d / 2 + 0.08), emit((1.0, 0.62, 0.3), 0.45, "munt_door"))
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
        lbox(root, "poster", (t0 + 0.55, 0.65, 0.62), (t0 + tw - 0.55, 2.45, 0.63), emit(col, 0.5, "poster_%s" % title[:6]))
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
    """Galvanised buckets of tulips on stepped staging: rows [(x0, x1, y, z), ...] (flowers.py)."""
    import flowers
    tin, water = Acc(), Acc()
    pots = []
    for x0, x1, y, z in rows:
        x = x0 + 0.17
        while x < x1 - 0.17:
            tin.rod((x, y, z), (x, y + 0.32, z), 0.15, 0.17, 10)
            water.rod((x, y + 0.26, z), (x, y + 0.27, z), 0.155, 0.155, 10)
            pots.append((x, y + 0.3, z, 0.15, rng.randrange(len(FLOWERS))))
            x += 0.36
    tin.build("buckets", M({"color": [0.5, 0.52, 0.52], "rough": 0.35, "metal": 0.9, "noise": 0.25}), root)
    water.build("bucket_water", M({"color": [0.02, 0.025, 0.02], "rough": 0.05}), root)
    flowers.bunches(root, pots, rng, FLOWERS)


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
    bow. "list": degrees it heels over (a boat that has taken water); "sunk": metres it sits low.
    For one he boards: "draught" (the hull's depth under the cabin floor), "aisle" (half the gangway
    between the seats), "door": [x, width] on its +z side (where the pier is: no glass, no seats)."""
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
    y1 = 0.35
    y0 = y1 - p.get("draught", 1.1)
    door = p.get("door")
    aisle = p.get("aisle", 0.25)

    def spans(sz, a, b):   # the stretches of the +z side either side of the door, or all of it
        if not door or sz < 0:
            return [(a, b)]
        return [(u, v) for u, v in ((a, door[0] - door[1] / 2), (door[0] + door[1] / 2, b)) if v - u > 0.05]
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
            if sz > 0 and door and abs(x - door[0]) < door[1] / 2:
                continue
            posts.box((x - 0.04, y1, sz * (Wd / 2 - 0.2) - 0.03), (x + 0.04, y1 + ch * 0.62, sz * (Wd / 2 - 0.2) + 0.03))
    posts.build("cabin_posts", white, root, smooth=False)
    for sz in (-1, 1):
        for a, b in spans(sz, c0, c1):
            lbox(root, "cabin_glass", (a, y1 + 0.45, sz * (Wd / 2 - 0.2) - 0.01), (b, y1 + ch * 0.62, sz * (Wd / 2 - 0.2) + 0.01), M("glass"))
            lbox(root, "cabin_side", (a, y1, sz * (Wd / 2 - 0.2) - 0.03), (b, y1 + 0.45, sz * (Wd / 2 - 0.2) + 0.03), white)
    if door:   # the door's frame and the step down onto the deck
        for u in (door[0] - door[1] / 2, door[0] + door[1] / 2):
            lbox(root, "door_post", (u - 0.05, y1, Wd / 2 - 0.25), (u + 0.05, y1 + ch * 0.62, Wd / 2 - 0.15), white)
    roof = Acc()
    seg = 8
    for k in range(seg):
        a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
        r = Wd / 2 - 0.2
        za, zb = -r * math.cos(a0), -r * math.cos(a1)
        ya, yb = y1 + ch * 0.62 + 0.45 * math.sin(a0), y1 + ch * 0.62 + 0.45 * math.sin(a1)
        roof.quad((c0, ya, za), (c1, ya, za), (c1, yb, zb), (c0, yb, zb))
    roof.build("cabin_roof", M({"color": [0.015, 0.02, 0.025], "rough": 0.08, "grime": 0, "bevel": 0}), root, smooth=True)   # tinted glass
    ribs = Acc()   # the roof's aluminium ribs, one over each pair of posts
    for i in range(n + 1):
        x = c0 + (c1 - c0) * i / n
        for k in range(seg):
            a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
            r = Wd / 2 - 0.2
            ribs.rod((x, y1 + ch * 0.62 + 0.45 * math.sin(a0) - 0.02, -r * math.cos(a0)), (x, y1 + ch * 0.62 + 0.45 * math.sin(a1) - 0.02, -r * math.cos(a1)), 0.03, 0.03, 4)
    ribs.build("roof_ribs", white, root, smooth=False)
    seats = Acc()
    x = c0 + 0.5
    while x < c1 - 0.5:
        for sz in (-1, 1):
            if sz > 0 and door and abs(x + 0.25 - door[0]) < door[1] / 2 + 0.3:
                continue
            seats.box((x, y1 + 0.05, sz * aisle), (x + 0.5, y1 + 0.5, sz * (Wd / 2 - 0.35)))
            seats.box((x, y1 + 0.5, sz * aisle), (x + 0.08, y1 + 1.0, sz * (Wd / 2 - 0.35)))
        x += 1.0
    seats.build("boat_seats", seat, root, smooth=False)
    lamps = Acc()   # small fittings down the roof's middle, still on; the light itself is a hidden panel
    yl = y1 + ch * 0.62 + 0.4
    for i in range(n):
        x = c0 + (c1 - c0) * (i + 0.5) / n
        lamps.box((x - 0.16, yl, -0.07), (x + 0.16, yl + 0.03, 0.07))
    lamps.build("cabin_lamps", emit((1.0, 0.86, 0.68), p.get("glow", 9.0), "boat_light"), root, smooth=False)
    ld = bpy.data.lights.new("cabin_glow", "AREA")
    ld.shape, ld.size, ld.size_y = "RECTANGLE", (c1 - c0) * 0.85, 0.9
    ld.energy, ld.color = p.get("power", 180.0), (1.0, 0.86, 0.68)
    ob = bpy.data.objects.new("cabin_glow", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.location = g2b(((c0 + c1) / 2, yl - 0.05, 0.0))
    street.hide_panel(ob)
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
    granite = M({"color": [0.16, 0.155, 0.15], "rough": 0.45, "noise": 0.3})   # dark polished granite (floodlit, pale stone burns out)
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
        spot(root, (sz * 4.0, 0.4, 4.0), (0.0, h + 1.8, 0.0), p.get("flood", 260.0), size=18.0)


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


# ── The Dam: the palace, the Nieuwe Kerk, the National Monument ─────────────────────────────
def palace(root, p, w, h, d):
    """The Royal Palace on the Dam (Jacob van Campen's town hall, 1665), its front along local x
    facing +z, w wide: a rusticated ground floor with seven small arched doors in the middle, two
    storeys of tall windows between pilasters, an attic, the middle seven bays standing forward
    under a pediment full of carving, and on the roof the cupola: a square base, an open drum, a
    copper dome, a lantern, a ship for a vane. Floodlit gold from the square, as it is every night.
    h: the cornice's height (the cupola rises above it)."""
    stone = M(p.get("stone", {"ph": "large_sandstone_blocks", "tint": [0.86, 0.76, 0.58], "scale": 1.2}))
    dark = M({"color": [0.015, 0.018, 0.02], "rough": 0.12, "metal": 0.3})
    lit = emit((1.0, 0.72, 0.4), 0.7, "palace_lit")
    copper = M(COPPER)
    gold = M(GOLD)
    rng = __import__("random").Random(p.get("seed", 5))
    n = p.get("bays", 23)
    bay = w / n
    g0 = h * 0.2   # the ground floor
    s1 = g0 + (h - g0) * 0.42
    mid0, mid1 = (n - 7) // 2, (n - 7) // 2 + 7
    out = 0.9   # how far the middle bays stand forward
    holes = []
    for i in range(n):
        u = bay * (i + 0.5)
        if mid0 <= i < mid1:   # the seven small arched doors of the middle (for the seven provinces)
            holes.append((u - bay * 0.22, u + bay * 0.22, 0.0, g0 * 0.72))
        else:
            holes.append((u - bay * 0.18, u + bay * 0.18, g0 * 0.25, g0 * 0.8))
        holes.append((u - bay * 0.2, u + bay * 0.2, g0 + 1.0, s1 - 1.4))
        holes.append((u - bay * 0.2, u + bay * 0.2, s1 + 0.9, h - 2.6))
    for u0, u1, v0, v1 in layout.cut_rects(w, h, holes):   # the front, cut round its windows
        zf = out if mid0 * bay <= (u0 + u1) / 2 < mid1 * bay else 0.0
        lbox(root, "palace_front", (u0, v0, zf - 1.0), (u1, v1, zf), stone)
    bars = Acc()   # the sashes' glazing bars: small panes, as the 17th century glazed
    for u0, u1, v0, v1 in holes:
        zf = out if mid0 * bay <= (u0 + u1) / 2 < mid1 * bay else 0.0
        lbox(root, "palace_window", (u0, v0, zf - 0.85), (u1, v1, zf - 0.8), lit if rng.random() < p.get("lit", 0.18) else dark)
        um = (u0 + u1) / 2
        bars.box((um - 0.03, v0, zf - 0.8), (um + 0.03, v1, zf - 0.76))
        for k in range(1, int((v1 - v0) / 0.5)):
            v = v0 + (v1 - v0) * k / int((v1 - v0) / 0.5)
            bars.box((u0, v - 0.025, zf - 0.8), (u1, v + 0.025, zf - 0.76))
        for uu in (u0, u1):
            bars.box((uu - 0.05, v0, zf - 0.8), (uu + 0.05, v1, zf - 0.74))
    bars.build("palace_glazing_bars", M({"color": [0.06, 0.055, 0.05], "rough": 0.5}), root, smooth=False)
    for k in (mid0, mid1):   # the returns where the middle stands forward
        lbox(root, "palace_return", (k * bay - 0.5, 0.0, 0.0), (k * bay + 0.5, h, out), stone)
    order = Acc()   # rustication, the floor bands, the pilasters and their capitals
    for k in range(int(g0 / 0.6)):
        order.box((0.0, k * 0.6, 0.0), (w, k * 0.6 + 0.05, 0.03))
    for y in (g0, s1, h - 1.6):
        order.box((-0.2, y - 0.25, 0.0), (w + 0.2, y + 0.2, 0.35 + out))
    for i in range(n + 1):
        u = bay * i
        zf = out if mid0 <= i <= mid1 else 0.0
        for y0, y1 in ((g0 + 0.2, s1 - 0.25), (s1 + 0.2, h - 1.85)):
            order.box((u - 0.4, y0, zf), (u + 0.4, y1, zf + 0.3))
            order.box((u - 0.55, y1 - 0.5, zf), (u + 0.55, y1, zf + 0.45))
    order.build("palace_order", stone, root, smooth=False)
    lbox(root, "palace_cornice", (-0.4, h - 1.6, -1.0), (w + 0.4, h - 0.6, 1.2 + out), stone)
    lbox(root, "palace_attic", (0.0, h - 0.6, -1.0), (w, h + 1.2, 0.2), stone)
    # the pediment over the middle seven bays, its tympanum carved (dark recesses for the figures)
    pw = (mid1 - mid0) * bay
    ph = pw * 0.22
    pc = (mid0 * bay + mid1 * bay) / 2
    fan_prism = street.fan_prism
    fan_prism(root, "pediment", [(-pw / 2 - 0.6, 0.0), (pw / 2 + 0.6, 0.0), (0.0, ph + 0.5)], (0.0, 0.5), -1.2, stone,
              ((pc, h - 0.6, out + 0.6), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    fan_prism(root, "tympanum", [(-pw / 2 + 0.6, 0.0), (pw / 2 - 0.6, 0.0), (0.0, ph - 0.6)], (0.0, 0.4), 0.05, M({"color": [0.5, 0.42, 0.3], "rough": 0.7, "noise": 0.4}),
              ((pc, h - 0.4, out + 0.65), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    figs = Acc()
    for k in range(15):   # the carving: figures in the tympanum, more at the middle
        t = (k + 0.5) / 15
        u = pc - pw / 2 + 1.2 + (pw - 2.4) * t
        top = (ph - 0.9) * (1 - abs(2 * t - 1))
        if top > 0.6:
            figs.box((u - 0.25, h - 0.3, out + 0.7), (u + 0.25, h - 0.3 + top * rng.uniform(0.6, 0.95), out + 1.0))
    figs.build("pediment_figures", stone, root, smooth=False)
    # its sides, d deep (it's seen end-on from the corners of the square): stone, a grid of windows,
    # the attic and cornice going round; a lead roof over the whole block
    for u in (0.0, w):
        side = [(t0, t1, v0, v1) for t0, t1, v0, v1 in
                [(d * (k + 0.5) / 8 - 1.0, d * (k + 0.5) / 8 + 1.0, y0, y1) for k in range(8)
                 for y0, y1 in ((g0 * 0.25, g0 * 0.8), (g0 + 1.0, s1 - 1.4), (s1 + 0.9, h - 2.6))]]
        for a, b, c, e in layout.cut_rects(d, h, side):
            lo, hi = (u - 1.0, c, -b), (u, e, -a)
            if u > 0:
                lo, hi = (u, c, -b), (u + 1.0, e, -a)
            lbox(root, "palace_side", lo, hi, stone)
        for a, b, c, e in side:
            x0, x1 = (u - 0.85, u - 0.8) if u == 0.0 else (u + 0.8, u + 0.85)
            lbox(root, "palace_side_window", (x0, c, -b), (x1, e, -a), dark)
        lbox(root, "palace_side_cornice", (u - 1.4 if u == 0.0 else u - 0.4, h - 1.6, -d), (u + 0.4 if u == 0.0 else u + 1.4, h - 0.6, 0.0), stone)
        lbox(root, "palace_side_attic", (u - 1.0 if u == 0.0 else u, h - 0.6, -d), (u if u == 0.0 else u + 1.0, h + 1.2, 0.0), stone)
    lbox(root, "palace_back", (0.0, 0.0, -d - 1.0), (w, h + 1.2, -d), stone)
    lbox(root, "palace_roof", (0.0, h + 0.6, -d), (w, h + 1.0, 0.0), M(LEAD))
    # the cupola: a square base, an open drum of columns, a copper dome, a lantern, the ship
    cx, cz = w / 2, -d / 2
    base = h + 1.2
    lbox(root, "cupola_base", (cx - 6.0, base, cz - 6.0), (cx + 6.0, base + 4.0, cz + 6.0), stone)
    lbox(root, "cupola_base_cornice", (cx - 6.4, base + 4.0, cz - 6.4), (cx + 6.4, base + 4.6, cz + 6.4), stone)
    rod(root, "palace_clock", (cx, base + 2.0, cz + 6.0), (cx, base + 2.0, cz + 6.12), 1.3, 1.3, emit((1.0, 0.92, 0.75), 0.9, "palace_clock"), seg=32)
    cols = Acc()
    R = 4.6
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        cols.rod((cx + R * math.cos(a), base + 4.6, cz + R * math.sin(a)), (cx + R * math.cos(a), base + 10.0, cz + R * math.sin(a)), 0.4, 0.34, 10)
    cols.build("drum_columns", stone, root)
    point(root, (cx, base + 7.0, cz), p.get("cupola_light", 900.0), (1.0, 0.75, 0.45), radius=0.8)
    octagon(root, "drum_entablature", [(R + 0.7, 0.0), (R + 0.7, 1.0), (0.0, 1.0)], stone, base + 10.0, cx, cz)
    dome = [(R + 0.5, 0.0), (R + 0.3, 1.2), (R * 0.8, 2.8), (R * 0.45, 4.0), (1.2, 4.6), (0.0, 4.65)]
    kit.lathe(root, "palace_dome", dome, copper, at=(cx, base + 11.0, cz), segments=24)
    lant = base + 15.6
    lc = Acc()
    for k in range(8):
        a = math.radians(22.5 + 45 * k)
        lc.rod((cx + 1.1 * math.cos(a), lant, cz + 1.1 * math.sin(a)), (cx + 1.1 * math.cos(a), lant + 2.6, cz + 1.1 * math.sin(a)), 0.12, 0.1, 6)
    lc.build("lantern_columns", stone, root)
    point(root, (cx, lant + 1.3, cz), 120.0, (1.0, 0.75, 0.45), radius=0.3)
    kit.lathe(root, "lantern_cap", [(1.5, 0.0), (1.2, 0.6), (0.4, 1.4), (0.1, 2.4), (0.0, 2.45)], copper, at=(cx, lant + 2.6, cz), segments=16)
    ball(root, "vane_ball", (cx, lant + 5.3, cz), 0.35, gold, seg=14)
    ship = Acc()   # the cog on the vane: a hull, a mast, a sail
    ship.quad((cx - 1.0, lant + 5.8, cz), (cx + 1.0, lant + 5.8, cz), (cx + 0.7, lant + 5.4, cz), (cx - 0.7, lant + 5.4, cz))
    ship.quad((cx - 0.05, lant + 5.8, cz), (cx + 0.05, lant + 5.8, cz), (cx + 0.05, lant + 7.4, cz), (cx - 0.05, lant + 7.4, cz))
    ship.quad((cx + 0.1, lant + 6.0, cz), (cx + 0.9, lant + 6.1, cz), (cx + 0.8, lant + 7.1, cz), (cx + 0.1, lant + 7.2, cz))
    ship.build("vane_ship", gold, root, smooth=False)
    # floodlit from the square: a row of warm uplights along the foot, and two up at the cupola
    for k in range(5):
        u = w * (k + 0.5) / 5
        spot(root, (u, 0.3, 9.0), (u, h * 0.6, 0.0), p.get("flood", 1600.0), (1.0, 0.78, 0.48), size=48.0)
    for sx in (-1, 1):
        spot(root, (cx + sx * 14.0, 0.3, 16.0), (cx, base + 9.0, cz), p.get("flood", 1600.0) * 1.5, (1.0, 0.8, 0.5), size=22.0)


def gothic_front(root, p, w, h, d):
    """A gothic church's transept front (the Nieuwe Kerk's on the Dam) along local x facing +z: brick
    walls with sandstone dressings, a huge pointed window of tracery lit from inside, buttresses with
    pinnacles either side, the gable over it, the steep roof running back d, and a slender ridge
    turret (a dakruiter) with its spire. h: the eaves; the gable rises above."""
    brick = M(p.get("brick", {"ph": "medieval_red_brick", "tint": [0.7, 0.55, 0.46], "scale": 1.0}))
    stone = M({"ph": "large_sandstone_blocks", "tint": [0.8, 0.74, 0.62], "scale": 0.8})
    lead = M(LEAD)
    import church
    glass = church.leaded_glass((1.0, 0.72, 0.42), p.get("glow", 0.55) * 1.4)   # lit from inside: the lead shows dark against it
    gh = w * 0.75                          # the gable's height over the eaves
    span = w * 0.56                        # the window's width
    sill = h * 0.18
    rise = span * math.sin(math.radians(60))   # an equilateral pointed arch: each side an arc of radius = span
    u0, u1 = w / 2 - span / 2, w / 2 + span / 2

    def half_open(y):   # how far the window's opening reaches either side of the middle at height y
        if y < h:
            return span / 2
        t = y - h
        return math.sqrt(max(span * span - t * t, 0.0)) - span / 2 if t < rise else 0.0

    holes = [(u0, u1, sill, h)]
    door = p.get("door")   # (u centre, width, height): the way in under the window, its leaf the game's
    if door:
        du, dw, dh = door
        holes.append((du - dw / 2, du + dw / 2, 0.0, dh))
        arch_m = stone
        lbox(root, "door_lintel", (du - dw / 2 - 0.4, dh, -1.2), (du + dw / 2 + 0.4, dh + 0.5, 0.15), arch_m)
        for sgn in (-1, 1):
            lbox(root, "door_jamb", (du + sgn * dw / 2 - (0.4 if sgn < 0 else 0.0), 0.0, -1.2),
                 (du + sgn * dw / 2 + (0.4 if sgn > 0 else 0.0), dh, 0.15), arch_m)
        lbox(root, "door_tympanum", (du - dw / 2, dh, -1.0), (du + dw / 2, min(dh + 1.6, sill - 0.4), -0.9), stone)
    for a, b, c, e in layout.cut_rects(w, h, holes):   # the wall up to the eaves
        lbox(root, "church_wall", (a, c, -1.2), (b, e, 0.0), brick)
    course = 0.25   # the gable in courses, each cut round the window's pointed head
    y = h
    while y < h + gh - 0.01:
        yt = min(y + course, h + gh)
        half_g = (w / 2) * (1 - (y + yt - 2 * h) / 2 / gh)
        ho = half_open((y + yt) / 2)
        if ho > 0.05:
            for sgn in (-1, 1):
                lo, hi = sorted((w / 2 + sgn * ho, w / 2 + sgn * half_g))
                if hi - lo > 0.02:
                    lbox(root, "church_gable", (lo, y, -1.2), (hi, yt, 0.0), brick)
            lbox(root, "church_window_head", (w / 2 - ho, y, -1.0), (w / 2 + ho, yt, -0.95), glass)
        else:
            lbox(root, "church_gable", (w / 2 - half_g, y, -1.2), (w / 2 + half_g, yt, 0.0), brick)
        y = yt
    lbox(root, "church_window_light", (u0, sill, -1.0), (u1, h, -0.95), glass)
    tr = Acc()   # tracery: mullions up into the head, transoms across
    n = 6
    for i in range(1, n):
        u = u0 + span * i / n
        top = h + math.sqrt(max(span * span - (abs(u - w / 2) + span / 2) ** 2, 0.0)) if abs(u - w / 2) < span / 2 else h
        tr.box((u - 0.09, sill, -0.95), (u + 0.09, top - 0.1, -0.75))
    for k in range(1, 4):
        yy = sill + (h - sill) * k / 4
        tr.box((u0, yy - 0.07, -0.95), (u1, yy + 0.07, -0.75))
    tr.build("tracery", stone, root, smooth=False)
    lbox(root, "window_sill", (u0 - 0.3, sill - 0.3, -1.2), (u1 + 0.3, sill, 0.25), stone)
    for u in (0.0, w):   # buttresses stepping back, pinnacles on top
        for y0, y1, dz in ((0.0, h * 0.5, 2.2), (h * 0.5, h * 0.85, 1.4), (h * 0.85, h + 1.5, 0.8)):
            lbox(root, "buttress", (u - 0.9, y0, -0.5), (u + 0.9, y1, dz), brick)
            lbox(root, "buttress_cap", (u - 1.0, y1 - 0.2, -0.5), (u + 1.0, y1, dz + 0.15), stone)
        kit.lathe(root, "pinnacle", [(0.55, 0.0), (0.5, 0.2), (0.0, 3.2)], stone, at=(u, h + 1.5, 0.15), segments=4, smooth=False)
    # the roof back from the gable, and the ridge turret with its spire
    street.fan_prism(root, "church_roof", [(-w / 2 - 0.3, 0.0), (w / 2 + 0.3, 0.0), (0.0, gh + 0.4)], (0.0, 0.5), -d,
                     M({"color": [0.12, 0.12, 0.13], "rough": 0.4, "metal": 0.6}), ((w / 2, h, -1.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    tz, ty = -d * 0.55, h + gh + 0.2
    spire = p.get("spire", 12.0)
    octagon(root, "turret", [(1.4, 0.0), (1.4, 3.6), (1.7, 3.8), (1.7, 4.1), (0.0, 4.1)], lead, ty, w / 2, tz)
    kit.lathe(root, "turret_spire", [(1.5, 0.0), (0.12, spire), (0.0, spire + 0.1)], lead, at=(w / 2, ty + 4.1, tz), segments=8, smooth=False)
    ball(root, "spire_ball", (w / 2, ty + 4.1 + spire * 0.6, tz), 0.3, M(GOLD), seg=12)
    point(root, (w / 2, h * 0.6, -3.0), p.get("inside", 700.0), (1.0, 0.72, 0.42), radius=2.0)   # the light inside, out through the glass
    spot(root, (w / 2, 0.3, 12.0), (w / 2, h + gh * 0.5, 0.0), p.get("flood", 1400.0), (1.0, 0.8, 0.55), size=40.0)


def monument(root, p, w, h, d):
    """The National Monument on the Dam: a white stone pillar 22 m high (h) on a round stepped
    platform (w across), the figures of the war's suffering on its front (here: their blocks and
    shadows), two lions on pedestals either side, the curved wall behind. Floodlit white."""
    travertine = M({"color": [0.78, 0.76, 0.7], "rough": 0.7, "noise": 0.3})
    r = w / 2
    steps = [(r, 0.0), (r, 0.3), (r - 0.6, 0.3), (r - 0.6, 0.6), (r - 1.2, 0.6), (r - 1.2, 0.9), (0.0, 0.9)]
    kit.lathe(root, "monument_steps", steps, travertine, at=(0.0, 0.0, 0.0), segments=48)
    base = 0.9
    sq = Acc()
    s0, s1 = 2.2, 1.0
    sq.box((-s0, base, -s0), (s0, base + 2.0, s0))
    sq.build("pillar_base", travertine, root, smooth=False)
    shaft = kit.lathe(root, "pillar", [(s0 * 1.2, 0.0), (s1 * 1.35, h - base - 2.0), (s1 * 1.5, h - base - 1.6), (0.0, h - base - 1.6)],
                      travertine, at=(0.0, base + 2.0, 0.0), segments=4, smooth=False)
    shaft.rotation_euler[2] = math.radians(45)
    figs = Acc()   # the reliefs on the front: figures in high relief, men in chains, a woman with a child
    rng = __import__("random").Random(3)
    for k in range(9):
        y = base + 2.2 + k * 0.9
        wdt = s0 * 1.6 * (1 - k / 14)
        figs.box((-wdt / 2 + rng.uniform(-0.1, 0.1), y, s0 * 0.85 - k * 0.02), (wdt / 2 + rng.uniform(-0.1, 0.1), y + 0.8, s0 * 0.85 + 0.35 - k * 0.02))
    figs.build("reliefs", travertine, root, smooth=False)
    for sx in (-1, 1):   # the lions on their pedestals
        lbox(root, "lion_pedestal", (sx * (r - 2.0) - 0.8, base, -0.8), (sx * (r - 2.0) + 0.8, base + 1.6, 0.8), travertine)
        lion = builders.empty_at("lion", (0.0, 0.0, 0.0), 0.0)
        lion.parent = root
        lion.location = g2b((sx * (r - 2.0), base + 1.6, 0.0))
        kit.model(lion, {"model": "ph:lion_head", "fit": [1.2, 1.3, 1.2], "tint": [0.85, 0.82, 0.75]}, 0, 0, 0)
    wall = Acc()   # the curved wall behind
    seg = 24
    for k in range(seg):
        a0 = math.pi * (0.15 + 0.7 * k / seg)
        a1 = math.pi * (0.15 + 0.7 * (k + 1) / seg)
        R = r + 1.0
        wall.quad((R * math.cos(a0), 0.0, -R * math.sin(a0)), (R * math.cos(a1), 0.0, -R * math.sin(a1)),
                  (R * math.cos(a1), 2.6, -R * math.sin(a1)), (R * math.cos(a0), 2.6, -R * math.sin(a0)))
    wall.build("monument_wall", travertine, root, smooth=False)
    for k, (ax, az) in enumerate(((0.0, r + 6.0), (r + 5.0, 3.0), (-r - 5.0, 3.0))):
        spot(root, (ax, 0.3, az), (0.0, h * 0.55, 0.0), p.get("flood", 1500.0), (0.92, 0.95, 1.0), size=26.0)


# ── The Kalverstraat's light garlands ───────────────────────────────────────────────────
def garland(root, p, w, h, d):
    """A garland of lights slung across a shopping street (along local x, w wide, hung at h): a
    swag of bulbs, and from its middle a lit shape hanging (a chandelier of bulbs on a frame)."""
    bulbs, wire = Acc(), Acc()
    n = int(w / 0.25)
    pts = []
    for i in range(n + 1):
        t = i / n
        x = -w / 2 + w * t
        y = h - 4 * t * (1 - t) * p.get("sag", 0.9)
        pts.append((x, y, 0.0))
        bulbs.rod((x, y - 0.02, 0.0), (x, y - 0.09, 0.0), 0.03, 0.03, 6)
    for a, b in zip(pts, pts[1:]):
        wire.rod(a, b, 0.006, 0.006, 3)
    cy = h - p.get("sag", 0.9) - 0.1
    for k in range(3):   # the hanging shape: three rings of bulbs, wider toward the bottom
        ry = cy - 0.35 - k * 0.45
        rr = 0.35 + k * 0.25
        m = int(rr * 2 * math.pi / 0.18)
        for j in range(m):
            a = 2 * math.pi * j / m
            bulbs.rod((rr * math.cos(a), ry, rr * math.sin(a)), (rr * math.cos(a), ry - 0.07, rr * math.sin(a)), 0.028, 0.028, 6)
        wire.rod((0.0, cy, 0.0), (rr, ry, 0.0), 0.008, 0.008, 3)
        wire.rod((0.0, cy, 0.0), (-rr, ry, 0.0), 0.008, 0.008, 3)
    wire.build("garland_wire", M({"color": [0.05, 0.05, 0.05], "rough": 0.5}), root)
    bulbs.build("garland_bulbs", emit(tuple(p.get("color", (1.0, 0.85, 0.55))), p.get("glow", 8.0), "garland_bulb"), root)
    point(root, (0.0, cy - 0.6, 0.0), p.get("power", 60.0), tuple(p.get("color", (1.0, 0.8, 0.5))), radius=0.5)


# ── Damrak and Centraal: the Beurs, the station ────────────────────────────────────────────
STONE_BEURS = {"ph": "large_sandstone_blocks", "tint": [0.8, 0.74, 0.62], "scale": 0.8}


def beurs(root, p, w, h, d):
    """The Beurs van Berlage, the old exchange (1903), its long side along local x facing +z (w long,
    h to the eaves): plain brick walls with a stone base, rows of small round-arched windows, buttresses
    flat on the wall, a steep roof; at its +x end the square clock tower (twice the height), its clock
    lit, a pyramid cap, an arched gate at its foot ("gate_open": a way through it into the hall)."""
    brick = M(p.get("brick", {"ph": "red_bricks_04", "tint": [0.75, 0.55, 0.45], "scale": 1.0}))
    stone = M(STONE_BEURS)
    dark = M({"color": [0.02, 0.02, 0.025], "rough": 0.15, "metal": 0.3})
    lit = emit((1.0, 0.75, 0.45), 0.6, "beurs_lit")
    rng = __import__("random").Random(p.get("seed", 7))
    bay = 3.6
    n = int((w - 12.0) / bay)
    holes = []
    for i in range(n):   # small round-headed windows in three rows (the heads are suggested by the mesh above)
        u = 1.8 + bay * (i + 0.5)
        for v0, v1 in ((1.8, 4.0), (5.6, 8.2), (10.0, h - 1.8)):
            holes.append((u - 0.7, u + 0.7, v0, v1))
    for a, b, c, e in layout.cut_rects(w - 12.0, h, holes):
        lbox(root, "beurs_wall", (a, c, -0.8), (b, e, 0.0), brick)
    for a, b, c, e in holes:
        lbox(root, "beurs_window", (a, c, -0.7), (b, e, -0.65), lit if rng.random() < 0.15 else dark)
        lbox(root, "beurs_sill", (a - 0.1, c - 0.15, -0.8), (b + 0.1, c, 0.12), stone)
    lbox(root, "beurs_base", (0.0, 0.0, -0.8), (w - 12.0, 1.2, 0.15), stone)
    flat = Acc()
    for i in range(n + 1):   # the flat buttresses between the bays
        u = 1.8 + bay * i
        flat.box((u - 0.35, 1.2, 0.0), (u + 0.35, h - 0.6, 0.25))
    flat.build("beurs_piers", brick, root, smooth=False)
    lbox(root, "beurs_eaves", (-0.2, h - 0.6, -0.8), (w - 12.0 + 0.2, h, 0.5), stone)
    street.fan_prism(root, "beurs_roof", [(-d / 2 - 0.3, 0.0), (d / 2 + 0.3, 0.0), (0.0, d * 0.45)], (0.0, 0.5), w - 12.0,
                     M({"color": [0.14, 0.15, 0.16], "rough": 0.5, "metal": 0.4}), ((0.0, h, -d / 2), (0, 0, 1), (0, 1, 0), (1, 0, 0)))
    lbox(root, "beurs_end", (0.0, 0.0, -d), (0.8, h, -0.8), brick)               # the block closed: its far end, its back,
    lbox(root, "beurs_back", (0.0, 0.0, -d), (w - 12.0, h, -d + 0.8), brick)     # behind the tower
    lbox(root, "beurs_end", (w - 12.8, 0.0, -d), (w - 12.0, h, -12.0), brick)
    lbox(root, "beurs_end_base", (-0.15, 0.0, -d), (0.0, 1.2, -0.8), stone)
    # the tower at the +x end: 12 m square, twice the eaves' height, a clock on its front
    tx0, tx1 = w - 12.0, w
    th = h * 2.1
    holes = [(tx0 + 4.0, tx1 - 4.0, 0.0, 5.5)]   # the gate
    for v0 in (8.0, 13.0, 18.0):
        holes.append((tx0 + 5.0, tx1 - 5.0, v0, v0 + 3.0))
    for a, b, c, e in layout.cut_rects(tx1 - tx0, th, [(a - tx0, b - tx0, c, e) for a, b, c, e in holes]):
        lbox(root, "tower_wall", (tx0 + a, c, -1.0), (tx0 + b, e, 0.3), brick)
    for a, b, c, e in holes[1:]:
        lbox(root, "tower_window", (a, c, -0.9), (b, e, -0.85), dark)
    if not p.get("gate_open"):   # (open: the gate is a way in, the hall behind it a room of its own)
        lbox(root, "tower_gate", (holes[0][0], 0.0, -0.9), (holes[0][1], 5.5, -0.85), emit((1.0, 0.7, 0.4), 0.4, "beurs_gate"))
    for side in (tx0, tx1):
        lbox(root, "tower_side", (side - (0.0 if side == tx0 else 1.0), 0.0, -12.0), (side + (1.0 if side == tx0 else 0.0), th, -1.0), brick)
    cx = (tx0 + tx1) / 2
    rod(root, "beurs_clock", (cx, th - 5.0, 0.3), (cx, th - 5.0, 0.42), 1.6, 1.6, emit((1.0, 0.92, 0.72), 1.0, "beurs_clock"), seg=32)
    lbox(root, "tower_parapet", (tx0 - 0.3, th, -12.3), (tx1 + 0.3, th + 1.0, 0.6), stone)
    kit.lathe(root, "tower_cap", [(5.6, 0.0), (0.4, 7.0), (0.0, 7.2)], M({"color": [0.12, 0.13, 0.14], "rough": 0.4, "metal": 0.5}),
              at=(cx, th + 1.0, -6.0), segments=4, smooth=False).rotation_euler[2] = math.radians(45)
    for k in range(3):
        spot(root, (tx0 + 4.0 * k + 2.0, 0.3, 8.0), (cx, th * 0.6, 0.0), p.get("flood", 900.0), (1.0, 0.8, 0.55), size=30.0)



def _arch_head(acc, x0, x1, ys, z0, z1, n=10):
    """The round head of an opening x0..x1 springing at ys: the wall between the arc and the
    opening's square top, and the arc's soffit from z0 to z1."""
    r, cx = (x1 - x0) / 2, (x0 + x1) / 2
    top = ys + r
    for k in range(n):
        a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
        p0 = (cx - r * math.cos(a0), ys + r * math.sin(a0))
        p1 = (cx - r * math.cos(a1), ys + r * math.sin(a1))
        for z in (z0, z1):
            acc.quad((p0[0], p0[1], z), (p1[0], p1[1], z), (p1[0], top, z), (p0[0], top, z))
        acc.quad((p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1))


def _arch_ring(acc, x0, x1, ys, z, t=0.3, n=12):
    """A sandstone ring round an arched head, proud of the wall at z; its jambs down to the sill."""
    r, cx = (x1 - x0) / 2, (x0 + x1) / 2
    for k in range(n):
        a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        acc.quad((cx - r * c0, ys + r * s0, z), (cx - r * c1, ys + r * s1, z),
                 (cx - (r + t) * c1, ys + (r + t) * s1, z), (cx - (r + t) * c0, ys + (r + t) * s0, z))


def _glazed(root, x0, x1, y0, y1, z, inside, bars=3, pane=0.9):
    """An arched opening's glazing at depth z: the glass, its bars, the room behind (lit or dark)."""
    lbox(root, "station_inside", (x0, y0, z - 0.3), (x1, y1, z - 0.28), inside)
    lbox(root, "station_glass", (x0, y0, z - 0.01), (x1, y1, z + 0.01), M("glass"))
    a = Acc()
    for k in range(1, bars):
        x = x0 + (x1 - x0) * k / bars
        a.box((x - 0.03, y0, z + 0.01), (x + 0.03, y1, z + 0.05))
    y = y0 + pane
    while y < y1 - 0.2:
        a.box((x0, y - 0.03, z + 0.01), (x1, y + 0.03, z + 0.05))
        y += pane
    a.build("station_bars", M({"color": [0.05, 0.06, 0.06], "rough": 0.4, "metal": 0.6}), root, smooth=False)


def station(root, p, w, h, d):
    """Amsterdam Centraal's front (Cuypers, 1889) along local x facing +z, w wide: red brick banded
    with sandstone, two storeys of round-arched windows between brick pilasters, a stone cornice,
    dormers in the slate roof; in the middle a projecting front with three great arched doorways
    ("arch_open": the middle one a way into the hall), a tall arched window over them under a gable
    with the city's arms, and the two towers by it (a clock on the west one, a wind dial on the
    east); behind it all the train shed's arched roof. Floodlit, as at night, a few windows lit."""
    brick = M(p.get("brick", {"ph": "red_bricks_04", "tint": [0.8, 0.52, 0.42], "scale": 1.0}))
    stone = M({"ph": "large_sandstone_blocks", "tint": [0.86, 0.8, 0.68], "scale": 0.8})
    slate = M({"color": [0.13, 0.13, 0.14], "rough": 0.45, "metal": 0.2, "noise": 0.2, "grime": 1.0})
    dark = M({"color": [0.012, 0.012, 0.014], "rough": 0.6})
    lit = [emit((1.0, 0.76, 0.48), s, "station_room_%d" % k) for k, s in enumerate((0.1, 0.18, 0.28))]
    rng = __import__("random").Random(p.get("seed", 9))
    bay = 4.2
    n = int(w / bay)
    mid0, mid1 = w / 2 - 14.0, w / 2 + 14.0
    rows = ((1.6, 5.9), (7.8, h - 2.6))
    holes = []
    for i in range(n):
        u = bay * (i + 0.5)
        if u + 1.2 < mid0 or u - 1.2 > mid1:
            for v0, v1 in rows:
                holes.append((u - 1.0, u + 1.0, v0, v1))
    way = [(w / 2 - 2.6, w / 2 + 2.6, 0.0, 8.5)] if p.get("arch_open") else []
    for a, b, c, e in layout.cut_rects(w, h, holes + way):
        lbox(root, "station_wall", (a, c, -1.0), (b, e, 0.0), brick)
    heads, rings = Acc(), Acc()
    for a, b, c, e in holes:
        ys = e - (b - a) / 2
        _arch_head(heads, a, b, ys, -1.0, 0.0)
        _arch_ring(rings, a, b, ys, 0.06)
        for x in (a - 0.22, b):
            rings.box((x, c, 0.0), (x + 0.22, ys, 0.06))
        lbox(root, "station_sill", (a - 0.3, c - 0.18, -0.2), (b + 0.3, c, 0.16), stone)
        r = rng.random()
        _glazed(root, a, b, c, e, -0.55, lit[rng.randrange(3)] if r < 0.3 else dark, bars=3, pane=1.0)
    heads.build("station_heads", brick, root, smooth=False)
    rings.build("station_rings", stone, root, smooth=False)
    piers = Acc()
    for i in range(n + 1):
        u = bay * i
        if u < mid0 - 0.4 or u > mid1 + 0.4:
            piers.box((u - 0.32, 1.2, 0.0), (u + 0.32, h - 0.7, 0.22))
    piers.build("station_piers", brick, root, smooth=False)
    bands = Acc()
    for y, t in ((0.0, 1.2), (6.5, 0.4)):   # the plinth, the string course between the floors
        for a, b in ([(0.0, w / 2 - 2.6), (w / 2 + 2.6, w)] if way else [(0.0, w)]):
            bands.box((a, y, 0.0), (b, y + t, 0.18 if y == 0.0 else 0.26))
    bands.box((0.0, h - 0.7, -1.0), (w, h, 0.5))           # the cornice
    bands.box((0.0, h, -1.0), (w, h + 0.3, 0.25))
    bands.build("station_bands", stone, root, smooth=False)
    lbox(root, "station_roof", (0.0, h + 0.3, -d), (w, h + 0.6, -0.2), slate)
    street.fan_prism(root, "station_roof_ridge", [(-d / 2, 0.0), (d / 2, 0.0), (0.0, 6.0)], (0.0, 0.5), w,
                     slate, ((0.0, h + 0.6, -d / 2), (0, 0, 1), (0, 1, 0), (1, 0, 0)))
    for i in range(1, n, 2):   # dormers on the roof's front slope
        u = bay * (i + 0.5)
        if mid0 - 2.0 < u < mid1 + 2.0:
            continue
        lbox(root, "dormer", (u - 0.9, h + 0.5, -2.6), (u + 0.9, h + 2.7, -1.2), brick)
        street.fan_prism(root, "dormer_cap", [(-1.1, 0.0), (1.1, 0.0), (0.0, 0.9)], (0.0, 0.5), 1.6, slate,
                         ((u, h + 2.7, -2.7), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
        _glazed(root, u - 0.5, u + 0.5, h + 0.9, h + 2.3, -1.15, lit[0] if rng.random() < 0.25 else dark, bars=2, pane=0.7)
    # the middle: a projecting front, its three great arches (the middle one open), a tall window
    # over them, a gable with the arms
    mh = h + 8.0
    doors = [(mid0 + 6.0 + 8.0 * k - 2.6, mid0 + 6.0 + 8.0 * k + 2.6, 0.0, 8.5) for k in range(3)]
    big = [(w / 2 - 3.0, w / 2 + 3.0, 10.5, 20.5), (w / 2 - 10.7, w / 2 - 8.3, 11.0, 18.0), (w / 2 + 8.3, w / 2 + 10.7, 11.0, 18.0)]
    loc = lambda rects: [(a - mid0, b - mid0, c, e) for a, b, c, e in rects]
    for a, b, c, e in layout.cut_rects(mid1 - mid0, mh, loc(doors + big)):
        lbox(root, "station_mid", (mid0 + a, c, 0.3), (mid0 + b, e, 1.5), brick)
    for a, b, c, e in layout.cut_rects(mid1 - mid0, mh, loc(way)):
        lbox(root, "station_mid", (mid0 + a, c, -1.0), (mid0 + b, e, 0.3), brick)
    heads, rings = Acc(), Acc()
    for k, (a, b, c, e) in enumerate(doors + big):
        ys = e - (b - a) / 2
        _arch_head(heads, a, b, ys, 0.3 if not (way and k == 1) else -1.0, 1.5)
        _arch_ring(rings, a, b, ys, 1.56, t=0.5 if k < 3 else 0.35)
        for x in (a - (0.5 if k < 3 else 0.35), b):
            rings.box((x, c, 1.5), (x + (0.5 if k < 3 else 0.35), ys, 1.56))
    heads.build("station_mid_heads", brick, root, smooth=False)
    rings.build("station_mid_rings", stone, root, smooth=False)
    for k, (a, b, c, e) in enumerate(doors):
        if way and k == 1:
            continue
        lbox(root, "door_glow", (a, 0.0, 0.31), (b, e, 0.33), emit((1.0, 0.8, 0.55), 0.3, "station_door_glow"))
        lbox(root, "door_frame", (a, 0.0, 0.33), (b, 0.15, 0.45), dark)
        lbox(root, "door_transom", (a, 3.4, 0.33), (b, 3.6, 0.45), dark)
        for x in (a, (a + b) / 2 - 0.06, b - 0.12):
            lbox(root, "door_post", (x, 0.0, 0.33), (x + 0.12, e, 0.45), dark)
        lbox(root, "door_glass", (a, 0.0, 0.38), (b, e, 0.4), M("glass"))
    for a, b, c, e in big:
        _glazed(root, a, b, c, e, 0.6, lit[2], bars=4 if b - a > 4 else 2, pane=1.2)
    bands = Acc()
    for y, t in ((8.9, 0.45), (mh - 0.8, 0.8)):
        bands.box((mid0, y, 1.5), (mid1, y + t, 1.75))
    bands.build("station_mid_bands", stone, root, smooth=False)
    street.fan_prism(root, "station_gable", [(-14.0, 0.0), (14.0, 0.0), (0.0, 9.0)], (0.0, 0.5), 2.5, brick,
                     ((w / 2, mh, -1.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)))
    kit.soft(root, "station_arms", (w / 2, mh + 3.0, 1.6), (4.0, 3.2, 0.3), M({"color": [0.75, 0.08, 0.06], "rough": 0.4}), 0.1, 2)
    text(root, "XXX", (w / 2, mh + 3.0, 1.78), 0.9, M({"color": [0.92, 0.92, 0.9], "rough": 0.4}), font="DejaVuSans-Bold.ttf", depth=0.02)
    for side, dial in ((-1, "clock"), (1, "wind")):   # the two towers
        tx = w / 2 + side * 16.5
        tw = 6.0
        th = mh + 14.0
        lbox(root, "station_tower", (tx - tw / 2, 0.0, -1.0), (tx + tw / 2, th, 2.0), brick)
        q = Acc()
        for x0 in (tx - tw / 2 - 0.06, tx + tw / 2 - 0.34):   # stone quoins up its corners
            for y in range(0, int(th), 2):
                q.box((x0, float(y), 1.95), (x0 + 0.4, y + 1.0, 2.06))
        for y in (1.2, 9.0, th - 6.0):
            q.box((tx - tw / 2 - 0.1, y, -1.1), (tx + tw / 2 + 0.1, y + 0.45, 2.12))
        q.build("station_quoins", stone, root, smooth=False)
        masks, tr = Acc(), Acc()
        for y0, y1 in ((11.0, 15.5), (17.5, 22.0), (th - 13.5, th - 8.0)):
            lbox(root, "tower_window", (tx - 0.8, y0, 2.0), (tx + 0.8, y1, 2.02), dark)
            _arch_head(masks, tx - 0.8, tx + 0.8, y1 - 0.8, 2.02, 2.05)
            _arch_ring(tr, tx - 0.8, tx + 0.8, y1 - 0.8, 2.07, t=0.25)
        masks.build("tower_heads", brick, root, smooth=False)
        tr.build("tower_rings", stone, root, smooth=False)
        rod(root, "station_dial", (tx, th - 3.2, 2.0), (tx, th - 3.2, 2.12), 2.0, 2.0, emit((1.0, 0.94, 0.78), 0.9, "station_dial") if dial == "clock" else
            M({"color": [0.85, 0.65, 0.22], "rough": 0.3, "metal": 0.9}), seg=32)
        kit.lathe(root, "station_tower_cap", [(4.4, 0.0), (3.0, 2.0), (0.6, 7.5), (0.0, 7.6)], M({"color": [0.2, 0.3, 0.27], "rough": 0.4, "metal": 0.4}),
                  at=(tx, th, 0.5), segments=8, smooth=False)
        ball(root, "station_finial", (tx, th + 8.0, 0.5), 0.4, M(GOLD), seg=12)
    seg = 18   # the train shed's arch rising behind
    shed = Acc()
    R = p.get("shed", 22.0)
    for k in range(seg):
        a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
        shed.quad((w / 2 - R * math.cos(a0) * 2.2, h + R * math.sin(a0) * 0.6, -d - 2.0), (w / 2 - R * math.cos(a1) * 2.2, h + R * math.sin(a1) * 0.6, -d - 2.0),
                  (w / 2 - R * math.cos(a1) * 2.2, h + R * math.sin(a1) * 0.6, -d - 60.0), (w / 2 - R * math.cos(a0) * 2.2, h + R * math.sin(a0) * 0.6, -d - 60.0))
    shed.build("train_shed", M({"color": [0.1, 0.12, 0.13], "rough": 0.3, "metal": 0.6}), root, smooth=True)
    for k in range(6):   # floodlit from the square
        u = w * (k + 0.5) / 6
        spot(root, (u, 0.3, 14.0), (u, h * 0.7, 0.0), p.get("flood", 1300.0), (1.0, 0.8, 0.52), size=44.0)


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
                  "canal_boat": canal_boat, "pier": pier, "equestrian": equestrian, "palace": palace, "gothic_front": gothic_front,
                  "monument": monument, "garland": garland, "beurs": beurs, "station": station})
