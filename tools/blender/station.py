# damned_waters/tools/blender/station.py
# Centraal and the metro: the hall's shop units and departure boards, a trackbed, a platform's canopy.
import random

import bpy

import builders
import kit
from street import Acc, M, lbox, rod, text

STEEL = {"color": [0.16, 0.17, 0.18], "rough": 0.35, "metal": 0.8, "noise": 0.15}
BLUE = {"color": [0.012, 0.03, 0.09], "rough": 0.35}


def shop_unit(root, p, w, h, d):
    """A shop in the station's arcade, its front along local x facing +z, d deep (the prop's middle
    is the unit's): a steel frame, its name lit on the fascia, the shutter down ("open": how far it's
    up, 0..1; a little light left on inside under it)."""
    frame = M(STEEL)
    fh, f = 0.6, d / 2
    lbox(root, "unit_post", (-w / 2, 0.0, f - 0.1), (-w / 2 + 0.12, h, f), frame)
    lbox(root, "unit_post", (w / 2 - 0.12, 0.0, f - 0.1), (w / 2, h, f), frame)
    lbox(root, "unit_fascia", (-w / 2, h - fh, f - 0.1), (w / 2, h, f + 0.01), M({"color": [0.02, 0.022, 0.025], "rough": 0.4}))
    col = tuple(p.get("sign", (1.0, 0.92, 0.75)))
    name = p.get("name", "")
    text(root, name, (0.0, h - fh / 2, f + 0.015), min(fh * 0.5, 1.4 * (w - 0.4) / max(len(name), 1)),
         builders.emissive("unit_sign_%d_%d" % (int(col[0] * 100), int(col[2] * 100)), col, p.get("glow", 2.5)), depth=0.0)
    top = h - fh
    lift = top * p.get("open", 0.0)
    lbox(root, "unit_back", (-w / 2, 0.0, -f), (w / 2, top, -f + 0.05), M({"color": [0.03, 0.03, 0.032], "rough": 0.7}))
    if lift > 0.05:
        lbox(root, "unit_glow", (-w / 2 + 0.3, top - 0.08, -f + 0.4), (w / 2 - 0.3, top - 0.05, -f + 0.6),
             builders.emissive("unit_glow", (1.0, 0.85, 0.65), 2.0))
        lbox(root, "unit_floor", (-w / 2 + 0.12, 0.0, -f), (w / 2 - 0.12, 0.01, f), M({"color": [0.08, 0.08, 0.08], "rough": 0.5}))
    lbox(root, "shutter", (-w / 2 + 0.12, lift, f - 0.09), (w / 2 - 0.12, top, f - 0.07),
         M({"ph": p.get("look", "painted_metal_shutter"), "tint": [0.75, 0.77, 0.8], "scale": 1.0}))
    lbox(root, "shutter_bar", (-w / 2 + 0.12, lift, f - 0.1), (w / 2 - 0.12, lift + 0.06, f - 0.06), frame)
    for sx in (-1, 1):   # its sides, back to the wall
        lbox(root, "unit_side", (sx * w / 2 - (0.05 if sx > 0 else 0.0), 0.0, -f), (sx * w / 2 + (0.0 if sx > 0 else 0.05), h, f - 0.1), frame)


def departure_board(root, p, w, h, d):
    """A departures board hung from the roof (rods up "hang" metres), facing +z ("both": the back
    too): a dark blue case, the header, rows of time, destination, platform, and what's become of
    each train, all still lit."""
    lbox(root, "board_case", (-w / 2, 0.0, -d / 2), (w / 2, h, d / 2), M(BLUE))
    white = builders.emissive("board_white", (0.92, 0.95, 1.0), 2.2)
    amber = builders.emissive("board_amber", (1.0, 0.42, 0.06), 3.0)
    rows = p.get("rows", [["23:41", "SCHIPHOL", "4", "RIJDT NIET"], ["23:47", "UTRECHT", "7", "RIJDT NIET"]])
    n = len(rows) + 1.4
    r = h / n
    for face in ([1, -1] if p.get("both") else [1]):
        z = face * (d / 2 + 0.004)
        yaw = 0.0 if face > 0 else 180.0
        s = face
        text(root, p.get("title", "VERTREK"), (s * (-w / 2 + 0.12), h - r * 0.6, z), r * 0.5, white, depth=0.0, yaw=yaw, align="LEFT" if s > 0 else "RIGHT")
        lbox(root, "board_rule", (-w / 2 + 0.1, h - r * 1.15, z - 0.002), (w / 2 - 0.1, h - r * 1.12, z + 0.002), white)
        for k, (t, dest, spoor, state) in enumerate(rows):
            y = h - r * (k + 1.9)
            text(root, t, (s * (-w / 2 + 0.12), y, z), r * 0.42, white, font="DejaVuSansMono-Bold.ttf", depth=0.0, yaw=yaw, align="LEFT" if s > 0 else "RIGHT")
            text(root, dest, (s * (-w / 2 + 0.2 + w * 0.14), y, z), r * 0.42, white, depth=0.0, yaw=yaw, align="LEFT" if s > 0 else "RIGHT")
            text(root, spoor, (s * (w * 0.12), y, z), r * 0.42, white, font="DejaVuSansMono-Bold.ttf", depth=0.0, yaw=yaw)
            text(root, state, (s * (w / 2 - 0.12), y, z), r * 0.36, amber, depth=0.0, yaw=yaw, align="RIGHT" if s > 0 else "LEFT")
    a = Acc()
    for sx in (-1, 1):
        a.rod((sx * (w / 2 - 0.3), h, 0.0), (sx * (w / 2 - 0.3), h + p.get("hang", 1.5), 0.0), 0.012, 0.012, 5)
    a.build("board_rods", M(STEEL), root)


def trackbed(root, p, w, h, d):
    """A metro track along local x in its trough, its floor at the prop's height: concrete, the
    sleepers, two rails and the third on its insulators; "water": how deep it stands, black."""
    lbox(root, "trough", (-w / 2, -0.1, -d / 2), (w / 2, 0.0, d / 2),
         M({"color": [0.2, 0.2, 0.2], "rough": 0.85, "noise": 0.4, "noise_scale": 3.0, "grime": 1.5}))
    sl = Acc()
    for k in range(int(w / 0.75)):
        x = -w / 2 + 0.375 + k * 0.75
        sl.box((x - 0.12, 0.0, -0.95), (x + 0.12, 0.16, 0.95))
    sl.build("sleepers", M({"color": [0.32, 0.31, 0.29], "rough": 0.9, "noise": 0.3, "grime": 1.2}), root, smooth=False)
    rail = M({"color": [0.42, 0.4, 0.38], "rough": 0.3, "metal": 1.0, "noise": 0.3, "noise_scale": 4.0})
    for z in (-0.72, 0.72):
        lbox(root, "rail", (-w / 2, 0.16, z - 0.035), (w / 2, 0.32, z + 0.035), rail)
    lbox(root, "third_rail", (-w / 2, 0.36, d / 2 - 0.42), (w / 2, 0.44, d / 2 - 0.3), rail)
    lbox(root, "third_rail_cover", (-w / 2, 0.46, d / 2 - 0.46), (w / 2, 0.5, d / 2 - 0.26), M({"color": [0.75, 0.6, 0.1], "rough": 0.5}))
    if p.get("water"):
        lbox(root, "flood", (-w / 2, p["water"] - 0.01, -d / 2), (w / 2, p["water"], d / 2), M("canal_water"))


def platform_edge(root, p, w, h, d):
    """A platform's edge along local x, the drop toward +z: the coping stone, the white line, the
    studded strip for the blind."""
    lbox(root, "coping", (-w / 2, -0.02, d / 2 - 0.35), (w / 2, 0.005, d / 2), M({"color": [0.55, 0.55, 0.53], "rough": 0.6, "noise": 0.3, "grime": 1.0}))
    lbox(root, "edge_line", (-w / 2, 0.0, d / 2 - 0.5), (w / 2, 0.007, d / 2 - 0.4), M({"color": [0.85, 0.85, 0.8], "rough": 0.5, "noise": 0.25, "grime": 1.2}))
    lbox(root, "tactile", (-w / 2, 0.0, d / 2 - 0.95), (w / 2, 0.009, d / 2 - 0.6), M({"color": [0.42, 0.42, 0.42], "rough": 0.7, "noise": 0.4, "noise_scale": 40.0, "bump": 0.6}))


def canopy(root, p, w, h, d):
    """A platform's canopy along local x: a flat roof on a line of steel columns down the middle,
    strip lights under it (a few dead)."""
    rng = random.Random(p.get("seed", 3))
    lbox(root, "canopy_roof", (-w / 2, h, -d / 2), (w / 2, h + 0.35, d / 2), M({"color": [0.5, 0.5, 0.49], "rough": 0.6, "noise": 0.3, "grime": 1.5}))
    cols = Acc()
    n = max(2, int(w / 9.0))
    for k in range(n + 1):
        x = -w / 2 + 1.0 + (w - 2.0) * k / n
        cols.box((x - 0.15, 0.0, -0.15), (x + 0.15, h, 0.15))
    cols.build("canopy_columns", M(STEEL), root, smooth=False)
    on = builders.emissive("canopy_strip", (0.85, 0.92, 1.0), 5.0)
    off = M({"color": [0.6, 0.6, 0.6], "rough": 0.3})
    for k in range(int(w / 3.0)):
        x = -w / 2 + 1.5 + k * 3.0
        for z in (-d / 4, d / 4):
            lbox(root, "canopy_strip", (x - 1.1, h - 0.05, z - 0.06), (x + 1.1, h, z + 0.06), off if rng.random() < 0.2 else on)
    if p.get("light", 0.0):
        ld = bpy.data.lights.new("canopy_glow", "AREA")
        ld.shape, ld.size, ld.size_y = "RECTANGLE", w * 0.9, d * 0.6
        ld.energy, ld.color = p["light"], (0.85, 0.92, 1.0)
        ob = bpy.data.objects.new("canopy_glow", ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
        ob.location = builders.g2b((0.0, h - 0.1, 0.0))
        import street
        street.hide_panel(ob)


kit.PROPS.update({"shop_unit": shop_unit, "departure_board": departure_board, "trackbed": trackbed,
                  "platform_edge": platform_edge, "canopy": canopy})
