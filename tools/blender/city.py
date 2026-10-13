# damned_waters/tools/blender/city.py
# Purpose: the city kit (Blender side) for the squares and nightlife streets beyond the canal:
# neon in glass tubes (shop fronts, rooftop signs), strings of bulbs slung between the trees, a
# tram stopped at its stop with its lights still on (rails in the road, wires overhead), a statue
# on its plinth, a park (lawn with fallen leaves, gravel paths, a low fence, benches), a kiosk, and
# the glass windbreaks round a terrace. Used by tools/blender/street.py's outdoor sets; every name on
# a sign is made up for the game. Coordinates as in street.py (Godot frame, metres).
#
# ELI5: street.py builds a quiet canal; this switches the city on. The power is still running,
# so the neon buzzes and the tram's lights are on; there's just nobody left to see them.
import math
import random

import bpy
from mathutils import Vector

import builders
import kit
import street
from roomspec import g2b
from street import Acc, M, lbox, rod, text, ball

STEEL = {"color": [0.22, 0.23, 0.24], "rough": 0.35, "metal": 0.9, "noise": 0.15}
POLE = {"color": [0.12, 0.14, 0.13], "rough": 0.5, "metal": 0.6, "noise": 0.2}


def emit(color, strength, key=None):
    return builders.emissive(key or "neon_%d_%d_%d_%d" % (*(int(c * 100) for c in color), int(strength)), tuple(color), strength)


# ── Neon ─────────────────────────────────────────────────────────────────────────────
def neon_text(parent, body, at, size, color, strength=12.0, yaw=0.0, font="DejaVuSans-Bold.ttf", tube=0.012):
    """Lettering bent in glass tube: the letters' outlines only, round in section, glowing (the
    compositor's bloom gives them their haze)."""
    ob = text(parent, body, at, size, emit(color, strength), font=font, depth=0.0, yaw=yaw)
    ob.data.fill_mode = "NONE"
    ob.data.bevel_depth = tube
    ob.data.bevel_resolution = 2
    return ob


def rooftop_sign(spec, s):
    """A big sign on a roof, its letters on a steel lattice ({"at": [x, y, z], "text", "color", "size",
    "yaw"}): the kind that has lit the square every night for sixty years."""
    root = builders.empty_at("rooftop_sign", s["at"], s.get("yaw", 0.0))
    size = s.get("size", 1.6)
    width = len(s["text"]) * size * 0.66
    frame = Acc()
    for i in range(int(width / 1.2) + 2):   # the lattice behind the letters
        x = -width / 2 + width * i / (int(width / 1.2) + 1)
        frame.rod((x, -0.6, -0.4), (x, size + 0.4, -0.4), 0.04, 0.04, 6)
        frame.rod((x, -0.6, -0.4), (x, -0.6, -1.6), 0.04, 0.04, 6)
        frame.rod((x, size + 0.4, -0.4), (x, -0.6, -1.6), 0.03, 0.03, 6)
    for y in (-0.6, size * 0.5, size + 0.4):
        frame.rod((-width / 2, y, -0.4), (width / 2, y, -0.4), 0.035, 0.035, 6)
    frame.build("sign_frame", M(STEEL), root)
    lbox(root, "sign_back", (-width / 2 - 0.2, -0.3, -0.36), (width / 2 + 0.2, size + 0.2, -0.3), M({"color": [0.02, 0.02, 0.025], "rough": 0.6}))
    neon_text(root, s["text"], (0.0, size * 0.45, -0.2), size, s.get("color", (1.0, 0.25, 0.2)), s.get("strength", 6.0),
              font=s.get("font", "DejaVuSans-Bold.ttf"), tube=size * 0.025)


# ── Strings of lights ────────────────────────────────────────────────────────────────
def string_lights(strings):
    """Bulbs on a sagging wire between pairs of points (the trees of a terrace square):
    [[[x, y, z], [x, y, z], sag, spacing], ...]."""
    wire, bulbs = Acc(), Acc()
    for a, b, sag, gap in strings:
        L = math.dist(a, b)
        n = max(2, int(L / gap))
        pts = []
        for i in range(n + 1):
            t = i / n
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - sag * 4 * t * (1 - t), a[2] + (b[2] - a[2]) * t))
        for p, q in zip(pts, pts[1:]):
            wire.rod(p, q, 0.006, 0.006, 4)
        for p in pts[1:-1]:
            bulbs.rod((p[0], p[1] - 0.02, p[2]), (p[0], p[1] - 0.09, p[2]), 0.028, 0.02, 6)
    wire.build("light_wire", M({"color": [0.02, 0.02, 0.02], "rough": 0.6}), None)
    bulbs.build("light_bulbs", emit((1.0, 0.72, 0.38), 9.0, "string_bulb"), None)


# ── Trams ────────────────────────────────────────────────────────────────────────────
def tracks(lines):
    """Tram rails let into the road and the wire overhead on poles: [{"from": [x, z], "to": [x, z],
    "y": road height}, ...] (straight runs)."""
    rails, wires, poles = Acc(), Acc(), Acc()
    for ln in lines:
        (x0, z0), (x1, z1) = ln["from"], ln["to"]
        y = ln.get("y", 0.0)
        L = math.hypot(x1 - x0, z1 - z0)
        ux, uz = (x1 - x0) / L, (z1 - z0) / L
        nx, nz = -uz, ux
        for off in (-0.72, 0.72):   # the two rails, standard gauge apart, flush with the road
            rails.rod((x0 + nx * off, y + 0.005, z0 + nz * off), (x1 + nx * off, y + 0.005, z1 + nz * off), 0.035, 0.035, 4)
        wires.rod((x0, y + 5.8, z0), (x1, y + 5.8, z1), 0.008, 0.008, 4)
        n = max(1, int(L / 24.0))
        for i in range(n + 1):
            t = i / n
            px, pz = x0 + (x1 - x0) * t + nx * 4.2, z0 + (z1 - z0) * t + nz * 4.2
            poles.rod((px, y, pz), (px, y + 6.6, pz), 0.11, 0.08, 10)
            wires.rod((px, y + 6.3, pz), (x0 + (x1 - x0) * t, y + 5.85, z0 + (z1 - z0) * t), 0.01, 0.01, 4)
    rails.build("rails", M({"color": [0.45, 0.45, 0.47], "rough": 0.15, "metal": 1.0, "noise": 0.2}), None)
    wires.build("tram_wire", M({"color": [0.05, 0.04, 0.03], "rough": 0.5, "metal": 0.8}), None)
    poles.build("tram_poles", M(POLE), None)


def tram(root, p, w, h, d):
    """A city tram in three sections, length along local x, stopped with its lights on: the saloon
    lit inside, the headlights and the destination board (it says it isn't in service), a door open
    on the platform side (+z), the pantograph up to the wire."""
    body = M(p.get("material", {"color": [0.3, 0.31, 0.31], "rough": 0.45, "noise": 0.1, "noise_scale": 1.5, "coat": 1.0, "grime": 1.0}))
    band = M({"color": [0.05, 0.12, 0.35], "rough": 0.35, "noise": 0.05})
    dark = M({"color": [0.015, 0.015, 0.018], "rough": 0.4})
    glass = M("glass")
    inside = emit((1.0, 0.86, 0.68), 0.16, "tram_inside")   # the far wall of the saloon, lit
    strip = emit((1.0, 0.95, 0.85), 6.0, "tram_strip")      # the ceiling lights
    seat = M({"color": [0.05, 0.09, 0.2], "rough": 0.8, "noise": 0.1})
    pole = M({"color": [0.85, 0.65, 0.05], "rough": 0.3, "metal": 0.4})
    seats, poles = Acc(), Acc()
    n, gap = 3, 0.25
    seg = (w - gap * (n - 1)) / n
    for i in range(n):
        x0 = -w / 2 + i * (seg + gap)
        x1 = x0 + seg
        # the body in three: below the windows, the roof over them, and the ends; the window band
        # between is open, glazed, so the lit saloon shows through
        cx = (x0 + x1) / 2
        kit.soft(root, "tram_body", (cx, 0.35 + (1.05 - 0.35) / 2, 0.0), (seg, 1.05 - 0.35, d), body, 0.08, 3)
        kit.soft(root, "tram_roof", (cx, 2.4 + (h - 2.4) / 2, 0.0), (seg, h - 2.4, d), body, 0.12, 3)
        for xa, xb, cab in ((x0, x0 + 0.25, i == 0), (x1 - 0.25, x1, i == n - 1)):
            if cab:   # the driver's end: corner posts round the windscreen
                for za, zb in ((-d / 2, -d / 2 + 0.15), (d / 2 - 0.15, d / 2)):
                    lbox(root, "tram_end", (xa, 1.0, za), (xb, 2.45, zb), body)
            else:
                lbox(root, "tram_end", (xa, 1.0, -d / 2), (xb, 2.45, d / 2), body)
        lbox(root, "tram_skirt", (x0 + 0.05, 0.25, -d / 2 - 0.005), (x1 - 0.05, 0.6, d / 2 + 0.005), band)
        # the saloon: a lit wall down the middle (each side's window looks into its half), the
        # floor, a strip of lights in the ceiling, rows of seats, yellow grab poles
        lbox(root, "tram_inside", (x0 + (1.6 if i == 0 else 0.3), 0.9, -0.02), (x1 - (1.6 if i == n - 1 else 0.3), 2.5, 0.02), inside)
        lbox(root, "tram_floor", (x0 + 0.2, 0.36, -d / 2 + 0.08), (x1 - 0.2, 0.4, d / 2 - 0.08), dark)
        lbox(root, "tram_strip", (x0 + 0.4, 2.5, -0.15), (x1 - 0.4, 2.54, 0.15), strip)
        for k in range(int((seg - 1.0) / 0.9)):
            xx = x0 + 0.7 + k * 0.9
            for sz in (-1, 1):
                seats.quad((xx, 0.85, sz * 0.45), (xx, 0.85, sz * 0.95), (xx + 0.08, 1.45, sz * 0.95), (xx + 0.08, 1.45, sz * 0.45))
                seats.quad((xx, 0.85, sz * 0.45), (xx + 0.45, 0.85, sz * 0.45), (xx + 0.45, 0.85, sz * 0.95), (xx, 0.85, sz * 0.95))
        for k in range(int(seg / 2.0)):
            xx = x0 + 1.0 + k * 2.0
            for sz in (-1, 1):
                poles.rod((xx, 0.4, sz * 0.4), (xx, 2.5, sz * 0.4), 0.018, 0.018, 6)
        for sz in (-1, 1):
            lbox(root, "tram_windows", (x0 + 0.25, 1.05, sz * d / 2 - 0.01), (x1 - 0.25, 2.4, sz * d / 2 + 0.01), glass)
            for k in range(int(seg / 1.2) + 1):   # the posts between the windows
                xx = x0 + 0.25 + (seg - 0.5) * k / int(seg / 1.2)
                lbox(root, "tram_pillar", (xx - 0.04, 1.05, sz * d / 2 - 0.012), (xx + 0.04, 2.4, sz * d / 2 + 0.012), dark)
        if i < n - 1:   # the bellows between sections
            lbox(root, "tram_bellows", (x1, 0.4, -d / 2 + 0.12), (x1 + gap, h - 0.15, d / 2 - 0.12), dark)
        if i == 1:   # the pantograph
            pa = Acc()
            for sx in (-0.5, 0.5):
                pa.rod(((x0 + x1) / 2 + sx, h + 0.1, -0.4), ((x0 + x1) / 2, h + 1.0, 0.0), 0.02, 0.02, 4)
                pa.rod(((x0 + x1) / 2 + sx, h + 0.1, 0.4), ((x0 + x1) / 2, h + 1.0, 0.0), 0.02, 0.02, 4)
            pa.rod(((x0 + x1) / 2, h + 1.0, -0.6), ((x0 + x1) / 2, h + 1.0, 0.6), 0.025, 0.025, 4)
            pa.build("pantograph", M(STEEL), root)
    seats.build("tram_seats", seat, root, smooth=False)
    poles.build("tram_poles_inside", pole, root)
    lbox(root, "door_open", (-w / 2 + seg * 0.4, 0.35, d / 2 - 0.02), (-w / 2 + seg * 0.4 + 1.3, h - 0.5, d / 2 + 0.01), inside)
    for sx in (-1, 1):   # the cabs: windscreen, headlights, the board over it
        xe = sx * (w / 2 - 0.02)
        lbox(root, "windscreen", (xe - 0.03, 1.05, -d / 2 + 0.15), (xe + 0.03, 2.5, d / 2 - 0.15), glass)
        lbox(root, "dest_board", (xe - 0.03, 2.55, -d / 2 + 0.3), (xe + 0.03, 2.85, d / 2 - 0.3), dark)
        text(root, p.get("board", "NIET INSTAPPEN"), (xe + sx * 0.04, 2.7, 0.0), 0.16, emit((1.0, 0.6, 0.1), 8.0, "tram_board"),
             font="DejaVuSansMono-Bold.ttf", depth=0.0, yaw=90.0 * sx)
        for sz in (-1, 1):
            ball(root, "headlight", (xe + sx * 0.02, 0.8, sz * (d / 2 - 0.35)), 0.08, emit((1.0, 0.95, 0.85), 30.0, "tram_head"), seg=10)
    ld = bpy.data.lights.new("tram_glow", "AREA")
    ld.shape, ld.size, ld.size_y = "RECTANGLE", w * 0.8, 1.2
    ld.energy, ld.color = p.get("power", 300.0), (1.0, 0.92, 0.8)
    ob = bpy.data.objects.new("tram_glow", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    ob.location = g2b((0.0, 1.7, d / 2 + 0.05))
    ob.rotation_euler = (math.radians(-90), 0.0, 0.0)
    street.hide_panel(ob)


ADS = [("MUSEUMNACHT", "ZATERDAG 7 NOV", (0.08, 0.1, 0.25), (1.0, 0.8, 0.2)),
       ("EVACUATIE", "VOLG DE BORDEN", (0.75, 0.42, 0.02), (0.05, 0.05, 0.05)),
       ("ZOMERFESTIVAL", "VONDELPARK", (0.6, 0.08, 0.3), (1.0, 1.0, 0.9)),
       ("BLIJF BINNEN", "LUISTER NAAR DE RADIO", (0.85, 0.85, 0.82), (0.7, 0.05, 0.03)),
       ("DE STORM", "NU IN DE BIOSCOOP", (0.02, 0.03, 0.04), (0.85, 0.9, 1.0))]


def ad_face(root, u0, u1, v0, v1, at_w, axis="z", glow=0.9, k=None):
    """A backlit poster: a printed sheet (a colour, a title, a line under it, a band), all made up.
    axis "z" / "-z": the sheet faces +z / -z at z = at_w; "x" / "-x": +x / -x at x = at_w (u along z)."""
    title, line, bg, ink = ADS[k % len(ADS)] if k is not None else ADS[0]
    yaw = {"x": 90.0, "-x": -90.0, "-z": 180.0}.get(axis, 0.0)
    sg = -1.0 if axis in ("-x", "-z") else 1.0
    w, h = u1 - u0, v1 - v0
    uc = (u0 + u1) / 2

    def P(u, v, e=0.0):
        return (at_w + e * sg, v, u) if axis in ("x", "-x") else (u, v, at_w + e * sg)
    a = Acc()
    lo, hi = P(u0, v0), P(u1, v1)
    a.quad(lo, P(u1, v0), hi, P(u0, v1))
    a.build("ad_sheet", emit(bg, glow, "ad_%s" % title[:6]), root, smooth=False)
    b = Acc()
    b.quad(P(u0, v0 + h * 0.08, 0.002), P(u1, v0 + h * 0.08, 0.002), P(u1, v0 + h * 0.16, 0.002), P(u0, v0 + h * 0.16, 0.002))
    b.build("ad_band", emit(ink, glow * 1.2, "ad_band_%s" % title[:6]), root, smooth=False)
    ink_m = emit(ink, glow * 1.4, "ad_ink_%s" % title[:6])
    text(root, title, P(uc, v0 + h * 0.72, 0.003), min(0.2, 1.3 * w / len(title)), ink_m, font="DejaVuSans-Bold.ttf", depth=0.0, yaw=yaw)
    text(root, line, P(uc, v0 + h * 0.3, 0.003), min(0.07, 1.4 * w / len(line)), ink_m, font="DejaVuSans.ttf", depth=0.0, yaw=yaw)


def tram_stop(root, p, w, h, d):
    """A tram stop: a raised platform kerb, a glass shelter with a lit timetable panel, a bench."""
    stone = M(street.STONE)
    lbox(root, "platform", (-w / 2, 0.0, -d / 2), (w / 2, 0.25, d / 2), stone)
    frame = M(POLE)
    glass = M("glass")
    sx0, sx1 = -1.6, 1.6
    for x in (sx0, 0.0, sx1):
        lbox(root, "shelter_post", (x - 0.04, 0.25, -d / 2 + 0.1), (x + 0.04, 2.7, -d / 2 + 0.18), frame)
    lbox(root, "shelter_roof", (sx0 - 0.2, 2.7, -d / 2 + 0.05), (sx1 + 0.2, 2.8, d / 2 - 0.2), frame)
    lbox(root, "shelter_back", (sx0, 0.5, -d / 2 + 0.12), (sx1, 2.6, -d / 2 + 0.13), glass)
    lbox(root, "ad_box", (sx1 - 0.05, 0.8, -d / 2 + 0.2), (sx1 + 0.03, 2.2, -d / 2 + 1.0), frame)
    for sgn, k in ((1, p.get("ad", 0)), (-1, p.get("ad", 0) + 1)):
        ad_face(root, -d / 2 + 0.25, -d / 2 + 0.95, 0.85, 2.15, sx1 + (0.031 if sgn > 0 else -0.051), "x" if sgn > 0 else "-x", 0.8, k)
    bench(root, {"material": STEEL}, 1.8, 0.45, 0.4, at=(-0.6, 0.25, -d / 2 + 0.5))


# ── The square's furniture ───────────────────────────────────────────────────────────
def bench(root, p, w, h, d, at=(0.0, 0.0, 0.0)):
    """A park bench: wooden slats on two cast-iron ends."""
    wood = M({"ph": "dark_wood", "tint": [0.55, 0.42, 0.3], "scale": 0.4})
    iron = M(p.get("material", street.IRON))
    x, y, z = at
    for sx in (-1, 1):
        lbox(root, "bench_end", (x + sx * w / 2 - 0.03, y, z - d / 2), (x + sx * w / 2 + 0.03, y + 0.82, z + d / 2), iron)
    for k in range(4):
        lbox(root, "bench_slat", (x - w / 2, y + 0.42, z - d / 2 + k * d / 4), (x + w / 2, y + 0.45, z - d / 2 + k * d / 4 + d / 5), wood)
    for k in range(2):
        lbox(root, "bench_back", (x - w / 2, y + 0.55 + k * 0.14, z - d / 2 - 0.02), (x + w / 2, y + 0.65 + k * 0.14, z - d / 2 + 0.02), wood)


def statue(root, p, w, h, d):
    """A bronze figure on a stone plinth, its name cut in the stone, lit from below."""
    stone = M({"ph": "large_sandstone_blocks", "tint": [0.62, 0.6, 0.56], "scale": 0.8})
    ph = p.get("plinth", 4.0)
    kit.soft(root, "plinth_base", (0.0, 0.3, 0.0), (w + 1.2, 0.6, d + 1.2), stone, 0.04, 2)
    kit.soft(root, "plinth", (0.0, 0.6 + (ph - 1.2) / 2, 0.0), (w, ph - 1.2, d), stone, 0.03, 2)
    kit.soft(root, "plinth_cap", (0.0, ph - 0.3, 0.0), (w + 0.4, 0.6, d + 0.4), stone, 0.05, 3)
    text(root, p.get("name", "REMBRANDT"), (0.0, ph * 0.55, d / 2 + 0.005), 0.32, M({"color": [0.75, 0.62, 0.3], "rough": 0.3, "metal": 0.8}),
         font="DejaVuSerif-Bold.ttf", depth=0.01)
    kit.model(root, {"model": p.get("model", "ph:gothic_statue"), "fit": [w * 1.6, p.get("figure", 3.0), d * 1.6],
                     "tint": p.get("tint", [0.16, 0.2, 0.15])}, 0, 0, 0)
    for o in root.children:   # the figure stands on the plinth
        if o.name.startswith("model_"):
            o.location.z += ph
    for sz in (-1, 1):   # floodlights in the base, up at the bronze
        ld = bpy.data.lights.new("statue_flood", "SPOT")
        ld.energy, ld.color, ld.spot_size, ld.spot_blend = p.get("flood", 260.0), (1.0, 0.85, 0.65), math.radians(32), 0.5
        ob = bpy.data.objects.new("statue_flood", ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
        ob.location = g2b((0.0, 0.62, sz * (d / 2 + 2.2)))
        aim = Vector(g2b((0.0, ph + p.get("figure", 3.0) * 0.55, 0.0))) - ob.location
        ob.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()


def kiosk(root, p, w, h, d):
    """An eight-sided kiosk, its hatch open and lit, its name round the top."""
    green = M({"color": [0.05, 0.14, 0.09], "rough": 0.45, "noise": 0.15})
    r = w / 2
    prof = [(0.0, 0.0), (r, 0.0), (r, h * 0.8), (r * 1.15, h * 0.82), (r * 0.2, h), (0.0, h)]
    kit.lathe(root, "kiosk", prof, green, segments=8, smooth=False).rotation_euler[2] = math.radians(22.5)   # a face to the front
    z = r * math.cos(math.pi / 8) + 0.012
    lbox(root, "hatch", (-0.6, 1.0, z - 0.012), (0.6, 1.9, z - 0.006), emit((1.0, 0.82, 0.55), 1.2, "kiosk_hatch"))
    lbox(root, "hatch_ledge", (-0.62, 0.98, z - 0.02), (0.62, 1.02, z + 0.12), green)
    rng = random.Random(p.get("seed", 4))
    mags = [Acc() for _ in ADS]
    for row, y in enumerate((1.08, 1.4)):   # the papers and magazines racked in the hatch
        x = -0.56
        while x < 0.5:
            mw = rng.uniform(0.13, 0.2)
            mags[rng.randrange(len(ADS))].box((x, y, z - 0.005), (x + mw, y + rng.uniform(0.2, 0.27), z + 0.012 - row * 0.004))
            x += mw + 0.015
    for acc, (_, _, bg, ink) in zip(mags, ADS):
        acc.build("magazines", M({"color": [c * 0.8 + 0.08 for c in bg], "rough": 0.35}), root, smooth=False)
    ad_face(root, -0.55, 0.55, 1.0, 2.1, -z, "-z", 0.6, p.get("ad", 2))
    neon_text(root, p.get("name", "KIOSK"), (0.0, h * 0.74, r + 0.02), 0.28, (1.0, 0.85, 0.5), 10.0, font="DejaVuSerif-Bold.ttf")


def windbreak(root, p, w, h, d):
    """A terrace's glass windbreak along local x: panes in dark frames, the café's name on a band."""
    frame = M(p.get("frame", {"color": [0.04, 0.04, 0.045], "rough": 0.4, "metal": 0.5}))
    n = max(1, int(w / 1.5))
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        lbox(root, "screen_post", (x - 0.03, 0.0, -0.03), (x + 0.03, h, 0.03), frame)
    lbox(root, "screen_glass", (-w / 2, 0.1, -0.01), (w / 2, h - 0.05, 0.01), M("glass"))
    lbox(root, "screen_band", (-w / 2, 0.6, -0.015), (w / 2, 0.85, 0.015), frame)
    if p.get("name"):
        text(root, p["name"], (0.0, 0.725, 0.02), 0.16, M({"color": [0.8, 0.75, 0.6], "rough": 0.4}), depth=0.001)


def fence(root, p, w, h, d):
    """A park's low iron fence of hoops along local x."""
    a = Acc()
    n = max(1, int(w / 0.9))
    for i in range(n):
        x0 = -w / 2 + w * i / n
        x1 = x0 + w / n
        for k in range(7):   # a hoop
            t0, t1 = math.pi * k / 7, math.pi * (k + 1) / 7
            a.rod((x0 + (x1 - x0) * (1 - math.cos(t0)) / 2, h * math.sin(t0), 0.0),
                  (x0 + (x1 - x0) * (1 - math.cos(t1)) / 2, h * math.sin(t1), 0.0), 0.012, 0.012, 4)
    a.build("fence", M(p.get("material", street.IRON)), root)


def park(spec, pk):
    """A square's green: a lawn with the leaves on it, gravel paths across it, a low fence round it.
    pk: {"min": [x, z], "max": [x, z], "paths": [[x0, z0, x1, z1], ...]}."""
    (x0, z0), (x1, z1) = pk["min"], pk["max"]
    builders.box_aabb("lawn", (x0, -0.4, z0), (x1, 0.04, z1), M({"ph": "leafy_grass", "tint": [0.75, 0.75, 0.7], "wet": 0.4}))
    for px0, pz0, px1, pz1 in pk.get("paths", []):
        builders.box_aabb("path", (px0, -0.4, pz0), (px1, 0.06, pz1), M({"ph": "gravel_floor", "tint": [0.7, 0.68, 0.64], "wet": 0.5}))
    for (ax, az), (bx, bz) in (((x0, z0), (x1, z0)), ((x0, z1), (x1, z1)), ((x0, z0), (x0, z1)), ((x1, z0), (x1, z1))):
        L = math.hypot(bx - ax, bz - az)
        root = builders.empty_at("fence", ((ax + bx) / 2, 0.04, (az + bz) / 2), 0.0 if az == bz else 90.0)
        fence(root, {}, L, 0.45, 0.05)


def extras(spec):
    """The city pieces an outdoor RoomSpec names: "strings", "tracks", "parks", "rooftop_signs"."""
    o = spec["outdoor"]
    if o.get("strings"):
        string_lights(o["strings"])
    if o.get("tracks"):
        tracks(o["tracks"])
    for pk in o.get("parks", []):
        park(spec, pk)
    for s in o.get("rooftop_signs", []):
        rooftop_sign(spec, s)


kit.PROPS.update({"tram": tram, "tram_stop": tram_stop, "statue": statue, "kiosk": kiosk, "windbreak": windbreak,
                  "fence": fence, "bench": lambda root, p, w, h, d: bench(root, p, w, h, d)})
