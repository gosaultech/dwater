# damned_waters/tools/blender/church.py
# Purpose: the church-interior kit (Blender side) for the Nieuwe Kerk, made an emergency shelter the
# night the city was emptied: clustered gothic piers, the pointed arcades between nave and aisles with
# the clerestory over them, the wooden barrel vault with its ribs, the great organ on its gallery, a
# pulpit under its sounding board, and pointed windows of tracery (dark: it is night outside). The
# shelter itself (camp beds, the first aid post, the luggage) is aftermath.py's. Coordinates as in
# street.py (Godot frame, metres; a prop's local +z its front).
#
# ELI5: a gothic church is a forest of stone trees: the piers are trunks, the arches their branches
# meeting overhead. Build a few kinds of trunk and branch and repeat them down the nave.
import math

import builders
import kit
import street
from street import Acc, M, lbox, rod, text, ball

STONE = {"ph": "large_sandstone_blocks", "tint": [0.85, 0.8, 0.7], "scale": 0.7}
WHITEWASH = {"color": [0.78, 0.76, 0.7], "rough": 0.9, "noise": 0.12}
OAK = {"ph": "dark_wood", "tint": [0.6, 0.45, 0.32], "scale": 0.5}
GILT = {"color": [0.8, 0.6, 0.25], "rough": 0.3, "metal": 0.9}
TIN = {"color": [0.7, 0.72, 0.74], "rough": 0.2, "metal": 1.0}


def pointed_half_open(y, spring, span):
    """How far a pointed (equilateral) arch's opening reaches either side of its middle at height y."""
    if y < spring:
        return span / 2
    t = y - spring
    return math.sqrt(max(span * span - t * t, 0.0)) - span / 2 if t < span * math.sin(math.radians(60)) else 0.0


def gothic_pier(root, p, w, h, d):
    """A clustered pier: an octagonal core with slender shafts round it, a moulded base, a capital
    ring at the springing (h), the shafts going on up as ribs ("rib": metres more)."""
    stone = M(p.get("material", STONE))
    r = w / 2
    lbox(root, "pier_plinth", (-r - 0.15, 0.0, -r - 0.15), (r + 0.15, 0.45, r + 0.15), stone)
    core = kit.lathe(root, "pier_core", [(r * 0.75, 0.0), (r * 0.75, h), (0.0, h)], stone, at=(0.0, 0.45, 0.0), segments=8, smooth=False)
    core.rotation_euler[2] = math.radians(22.5)
    shafts = Acc()
    top = h + p.get("rib", 0.0)
    for k in range(8):
        a = 2 * math.pi * k / 8
        x, z = r * 0.82 * math.cos(a), r * 0.82 * math.sin(a)
        shafts.rod((x, 0.45, z), (x, top + 0.45, z), r * 0.2, r * 0.2, 8)
    shafts.build("pier_shafts", stone, root)
    kit.lathe(root, "pier_capital", [(r * 0.95, 0.0), (r * 1.15, 0.25), (r * 1.15, 0.4), (0.0, 0.4)], stone, at=(0.0, h + 0.45, 0.0), segments=16)


def arcade(root, p, w, h, d):
    """The wall over an arcade along local x (w long, d thick): pointed arches between the piers
    (every "bay" metres, springing at "spring"), the wall over them up to h, a clerestory window
    over each arch (dark glass), a string course under the windows."""
    stone = M(p.get("material", STONE))
    wash = M(p.get("wall", WHITEWASH))
    bay, spring = p.get("bay", 6.0), p.get("spring", 7.0)
    pier = p.get("pier", 1.4)
    n = max(1, int(round(w / bay)))
    bay = w / n
    span = bay - pier
    course = 0.3
    for i in range(n):   # each bay: the wall above the arch, in courses cut round its pointed head
        cx = -w / 2 + bay * (i + 0.5)
        y = spring
        while y < h - 0.01:
            yt = min(y + course, h)
            ho = pointed_half_open((y + yt) / 2, spring, span)
            for lo, hi in ((cx - bay / 2, cx - ho), (cx + ho, cx + bay / 2)):
                if hi - lo > 0.02:
                    lbox(root, "arcade_wall", (lo, y, -d / 2), (hi, yt, d / 2), wash)
            y = yt
        # the arch's moulding: a stone band round the head
        ring = Acc()
        seg = 12
        for side in (-1, 1):
            cxa = cx - side * span / 2
            for k in range(seg):
                a0, a1 = math.radians(60.0 * k / seg), math.radians(60.0 * (k + 1) / seg)
                p0 = (cxa + side * span * math.cos(a0), spring + span * math.sin(a0))
                p1 = (cxa + side * span * math.cos(a1), spring + span * math.sin(a1))
                ring.rod((p0[0], p0[1], d / 2 + 0.02), (p1[0], p1[1], d / 2 + 0.02), 0.12, 0.12, 6)
                ring.rod((p0[0], p0[1], -d / 2 - 0.02), (p1[0], p1[1], -d / 2 - 0.02), 0.12, 0.12, 6)
        ring.build("arch_moulding", stone, root)
        top_of_arch = spring + span * math.sin(math.radians(60))
        win_b, win_t = top_of_arch + 1.0, h - 0.8   # the clerestory window over it
        if win_t - win_b > 1.0:
            lbox(root, "clerestory", (cx - bay * 0.22, win_b, d / 2 + 0.01), (cx + bay * 0.22, win_t, d / 2 + 0.03),
                 builders.emissive("clerestory_night", (0.12, 0.16, 0.3), 0.15))
    lbox(root, "string_course", (-w / 2, spring + span * 0.9 + 0.4, -d / 2 - 0.08), (w / 2, spring + span * 0.9 + 0.6, d / 2 + 0.08), stone)


def nave_vault(root, p, w, h, d):
    """A wooden barrel vault along local z (d long), w across, its crown h over the root (put the
    root at the springing): boards painted with age, transverse ribs every "bay" metres, tie beams
    across at the springing."""
    wood = M(p.get("material", {"ph": "wood_planks_grey", "tint": [0.62, 0.55, 0.45], "scale": 1.0}))
    rib_m = M(p.get("ribs", OAK))
    seg = 20
    shell = Acc()
    pts = []
    for k in range(seg + 1):   # a pointed barrel: two arcs meeting at the crown
        t = k / seg
        a = math.pi * t
        x = -w / 2 * math.cos(a)
        y = h * math.sin(a) ** 0.85
        pts.append((x, y))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        shell.quad((x0, y0, -d / 2), (x1, y1, -d / 2), (x1, y1, d / 2), (x0, y0, d / 2))
    shell.build("vault_boards", wood, root, smooth=True)
    ribs = Acc()
    bay = p.get("bay", 6.0)
    n = max(1, int(d / bay))
    for i in range(n + 1):
        z = -d / 2 + d * i / n
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            ribs.rod((x0, y0 - 0.05, z), (x1, y1 - 0.05, z), 0.14, 0.14, 6)
        ribs.rod((-w / 2, 0.0, z), (w / 2, 0.0, z), 0.16, 0.16, 6)   # the tie beam
    ribs.rod((0.0, h - 0.08, -d / 2), (0.0, h - 0.08, d / 2), 0.12, 0.12, 6)   # the ridge
    ribs.build("vault_ribs", rib_m, root)


def organ(root, p, w, h, d):
    """The great organ on its gallery against the wall (facing +z): a gallery front on columns, the
    case of dark oak with gilded carving, its pipes in towers (the tallest in the middle) and flats
    between, shutters folded open, painted."""
    oak, gilt, tin = M(OAK), M(GILT), M(TIN)
    g = p.get("gallery", 4.0)
    lbox(root, "organ_gallery", (-w / 2 - 1.0, g - 0.5, -d), (w / 2 + 1.0, g, 1.2), oak)
    lbox(root, "organ_gallery_front", (-w / 2 - 1.0, g, 1.0), (w / 2 + 1.0, g + 1.1, 1.2), oak)
    cols = Acc()
    for k in range(5):
        x = -w / 2 - 1.0 + (w + 2.0) * k / 4
        cols.rod((x, 0.0, 0.9), (x, g - 0.5, 0.9), 0.22, 0.2, 12)
    cols.build("gallery_columns", M(STONE), root)
    lbox(root, "organ_case", (-w / 2, g, -d), (w / 2, h, -0.2), oak)
    towers = [(-w / 2 + w * 0.12, 0.7, 0.75), (-w / 2 + w * 0.32, 0.45, 0.6), (0.0, 1.0, 1.0), (w / 2 - w * 0.32, 0.45, 0.6), (w / 2 - w * 0.12, 0.7, 0.75)]
    pipes = Acc()
    for cx, tw, th in towers:   # each tower: a fan of pipes, longest in the middle, their mouths a row
        span = w * 0.16 * tw
        n = max(3, int(span / 0.22))
        top = g + 1.6 + (h - g - 2.6) * th
        for k in range(n):
            x = cx - span / 2 + span * (k + 0.5) / n
            length = (top - g - 1.6) * (1.0 - 0.35 * abs(k - (n - 1) / 2) / max((n - 1) / 2, 1))
            r = 0.07 + 0.05 * th
            pipes.rod((x, g + 1.6, 0.0), (x, g + 1.6 + length, 0.0), r, r, 10)
            pipes.box((x - r * 0.6, g + 1.9, r * 0.9), (x + r * 0.6, g + 2.05, r + 0.01))   # its mouth
        kit.soft(root, "tower_crown", (cx, top + 0.3, 0.0), (span + 0.3, 0.6, 0.6), gilt, 0.05, 2)
        lbox(root, "tower_base", (cx - span / 2 - 0.15, g + 1.1, -0.2), (cx + span / 2 + 0.15, g + 1.6, 0.45), oak)
    pipes.build("organ_pipes", tin, root, smooth=True)
    kit.soft(root, "organ_crest", (0.0, h + 0.5, -0.1), (w * 0.3, 1.2, 0.4), gilt, 0.1, 3)


def pulpit(root, p, w, h, d):
    """A carved oak pulpit: a six-sided tub on a column, its stair, a sounding board above."""
    oak, gilt = M(OAK), M(GILT)
    rod(root, "pulpit_column", (0.0, 0.0, 0.0), (0.0, 2.0, 0.0), 0.2, 0.25, oak)
    tub = kit.lathe(root, "pulpit_tub", [(0.5, 0.0), (0.75, 0.3), (0.8, 1.2), (0.85, 1.3), (0.0, 1.3)], oak, at=(0.0, 1.9, 0.0), segments=6, smooth=False)
    tub.rotation_euler[2] = math.radians(30)
    kit.lathe(root, "sounding_board", [(1.1, 0.0), (1.1, 0.25), (0.6, 0.6), (0.0, 0.9)], oak, at=(0.0, h, 0.0), segments=6, smooth=False)
    ball(root, "sounding_finial", (0.0, h + 1.0, 0.0), 0.15, gilt, seg=10)
    rod(root, "pulpit_back", (0.0, 3.2, -0.7), (0.0, h, -0.7), 0.15, 0.15, oak)
    steps = Acc()
    for k in range(10):
        steps.box((0.6 + k * 0.25, 0.0, -0.4), (0.85 + k * 0.25, 0.2 * (k + 1), 0.4))
    steps.build("pulpit_stair", oak, root, smooth=False)


def gothic_window(root, p, w, h, d):
    """A tall pointed window on the wall (its inside face; facing +z): a stone frame, mullions and
    transoms of tracery, the glass dark blue with the night (a faint glow from the floodlights out
    on the square)."""
    stone = M(p.get("material", STONE))
    span = w
    spring = h - span * math.sin(math.radians(60))
    glass = builders.emissive("church_glass_night", tuple(p.get("glow_colour", (0.16, 0.2, 0.36))), p.get("glow", 0.25))
    y = 0.0
    course = 0.25
    while y < h - 0.01:   # the glass, in courses following the pointed head
        yt = min(y + course, h)
        ho = pointed_half_open((y + yt) / 2, spring, span)
        if ho > 0.03:
            lbox(root, "window_glass", (-ho, y, -0.02), (ho, yt, 0.0), glass)
        y = yt
    tr = Acc()
    n = p.get("lights", 3)
    for i in range(1, n):
        x = -span / 2 + span * i / n
        top = spring + math.sqrt(max(span * span - (abs(x) + span / 2) ** 2, 0.0))
        tr.box((x - 0.05, 0.0, 0.0), (x + 0.05, top - 0.05, 0.06))
    for k in range(1, int(spring / 2.0) + 1):
        tr.box((-span / 2, k * 2.0 - 0.04, 0.0), (span / 2, k * 2.0 + 0.04, 0.06))
    seg = 10
    for side in (-1, 1):   # the frame up each side and round the head
        tr.box((side * span / 2 - 0.12, 0.0, 0.0), (side * span / 2 + 0.12, spring, 0.1))
        cxa = -side * span / 2
        for k in range(seg):
            a0, a1 = math.radians(60.0 * k / seg), math.radians(60.0 * (k + 1) / seg)
            tr.rod((cxa + side * span * math.cos(a0), spring + span * math.sin(a0), 0.05),
                   (cxa + side * span * math.cos(a1), spring + span * math.sin(a1), 0.05), 0.12, 0.12, 6)
    tr.build("window_tracery", stone, root, smooth=False)
    lbox(root, "window_sill", (-span / 2 - 0.2, -0.25, -0.05), (span / 2 + 0.2, 0.0, 0.35), stone)


def chandelier(root, p, w, h, d):
    """A brass church chandelier (a Dutch "kroon"): a ball and stem, two tiers of curved arms, a
    candle bulb on each, hung by a long chain from the vault ("chain" metres)."""
    brass = M({"color": [0.8, 0.6, 0.25], "rough": 0.2, "metal": 1.0})
    flame = builders.emissive("candle_bulb", (1.0, 0.75, 0.45), 8.0)
    rod(root, "kroon_chain", (0.0, 0.0, 0.0), (0.0, p.get("chain", 4.0), 0.0), 0.012, 0.012, brass)
    rod(root, "kroon_stem", (0.0, -1.2, 0.0), (0.0, 0.0, 0.0), 0.04, 0.03, brass)
    ball(root, "kroon_ball", (0.0, -1.3, 0.0), 0.22, brass, seg=14)
    arms, bulbs = Acc(), Acc()
    for tier, (y, r, n) in enumerate(((-1.15, w / 2, 12), (-0.6, w / 3, 8))):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * tier) / n
            x, z = r * math.cos(a), r * math.sin(a)
            arms.rod((0.0, y, 0.0), (x * 0.5, y - 0.15, z * 0.5), 0.015, 0.015, 4)
            arms.rod((x * 0.5, y - 0.15, z * 0.5), (x, y + 0.05, z), 0.015, 0.015, 4)
            bulbs.rod((x, y + 0.08, z), (x, y + 0.2, z), 0.02, 0.012, 6)
    arms.build("kroon_arms", brass, root)
    bulbs.build("kroon_candles", flame, root)
    import landmarks
    landmarks.point(root, (0.0, -0.9, 0.0), p.get("power", 60.0), (1.0, 0.72, 0.42), radius=0.4)


kit.PROPS.update({"gothic_pier": gothic_pier, "arcade": arcade, "nave_vault": nave_vault, "organ": organ, "pulpit": pulpit,
                  "gothic_window": gothic_window, "chandelier": chandelier})
