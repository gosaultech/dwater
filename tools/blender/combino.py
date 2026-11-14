# damned_waters/tools/blender/combino.py
# Purpose: Amsterdam's tram as it runs on the Rokin and the Damrak: the five-section low-floor car
# (a Siemens Combino in all but its maker's plate), built hard and square the way the real one is:
# flat white sides, a blue skirt, the blue line under the roof that steps up to a blue cap over the
# cab, one black band of flush glass you can see the saloon through, plug doors, grey bellows, a
# raked nose with broad white corner pillars, its lamps, wipers and mirrors, the amber destination
# display behind the windscreen, the roof's gear behind its fairings and the pantograph on the
# centre section. Proportions and livery are measured off CC BY photographs of the real cars
# (docs/photo_credits.md, "Reference"); the operator's name and emblem are invented (no real marks).
# Options as the old tram's: "board", "line", "derail", "dark", "smashed", "doors_open",
# "pantograph", "power", "fleet". Frame as vehicles.py (x along the tram, y up, z across).
#
# ELI5: the old tram was a bar of soap with windows painted on. This one is built like the real
# thing: flat sheets, sharp corners, real glass with a room behind it. Flat and sharp reads as
# metal; round and soft reads as rubber.
import math
import random
from collections import defaultdict

import bpy
from mathutils import Vector

import builders
import city
import street
import tram_layout
from roomspec import g2b
from street import Acc, M, text

# The body's section, bottom to top: heights (for a 3.4 m car) and how far each is set in from the side.
ROWS = [0.20, 0.27, 0.62, 0.72, 0.78, 1.00, 1.20, 1.27, 2.66, 2.74, 2.86, 3.10, 3.16, 3.27, 3.35, 3.38, 3.38, 3.12]
INSET = [0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.04, 0.12, 0.22, 0.30, 0.30]
NOSE_ROWS = 16            # (the nose stops at the roof's edge: no fairing, a flat cap)
W, B, G, K, R, ROOF, BUMP = range(7)   # white, blue, glass, black glass, the joints' grey seal, the roof's grey, the bumper
NOSE, EXP = 1.0, 4.5      # the nose's length (m); how square its plan is (2: an ellipse; more: squarer)
T_GLASS = math.asin(0.86 ** (EXP / 2))   # the windscreen's edge, as an angle round the nose
T_CAB = math.acos(0.33 ** (EXP / 2))     # the cab side window's front edge
LAYOUT = {   # along a section, back to front: (what, width, stretches to fit)
    "cab": [("end", 0.08, 0), ("window", 1.40, 1), ("pillar", 0.06, 0), ("window", 1.40, 1), ("wall", 0.14, 0),
            ("door", 0.85, 0), ("wall", 0.22, 0), ("cabwin", 0.95, 1)],
    "doors": [("end", 0.08, 0), ("window", 0.90, 1), ("wall", 0.12, 0), ("door", 1.35, 0), ("wall", 0.12, 0), ("window", 1.30, 1),
              ("wall", 0.12, 0), ("door", 1.35, 0), ("wall", 0.12, 0), ("window", 0.90, 1), ("end", 0.08, 0)],
    "mid": [("end", 0.08, 0), ("window", 1.60, 1), ("pillar", 0.06, 0), ("window", 1.60, 1), ("end", 0.08, 0)],
}
KINDS = ("cab", "doors", "mid", "doors", "cab")
OPERATOR = "SVA"          # invented: "Stadsvervoer Amsterdam"


def _glass(name, tint, dirt):
    """A pane you see through and see yourself in: light goes straight through, tinted; the street
    mirrors in it more the flatter you look; where the rain ran, a film of dirt."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    new, link = nt.nodes.new, nt.links.new
    out = new("ShaderNodeOutputMaterial")
    tr = new("ShaderNodeBsdfTransparent")
    tr.inputs["Color"].default_value = (*tint, 1)
    gl = new("ShaderNodeBsdfPrincipled")
    gl.inputs["Base Color"].default_value = (0.9, 0.92, 0.95, 1)
    gl.inputs["Metallic"].default_value = 1.0
    gl.inputs["Roughness"].default_value = 0.02
    fr = new("ShaderNodeFresnel")
    fr.inputs["IOR"].default_value = 1.6
    lift = new("ShaderNodeMath")
    lift.operation, lift.use_clamp = "ADD", True
    lift.inputs[1].default_value = 0.04
    link(fr.outputs[0], lift.inputs[0])
    pane = new("ShaderNodeMixShader")
    link(lift.outputs[0], pane.inputs[0])
    link(tr.outputs[0], pane.inputs[1])
    link(gl.outputs[0], pane.inputs[2])
    tc = new("ShaderNodeTexCoord")
    mp = new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (3.0, 3.0, 0.5)   # stretched down the pane: where the rain ran
    link(tc.outputs["Object"], mp.inputs["Vector"])
    nz = new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 6.0
    link(mp.outputs[0], nz.inputs["Vector"])
    ramp = new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = 0.35, 0.95
    ramp.inputs["To Min"].default_value, ramp.inputs["To Max"].default_value = 0.0, dirt
    link(nz.outputs["Fac"], ramp.inputs["Value"])
    df = new("ShaderNodeBsdfDiffuse")
    df.inputs["Color"].default_value = (0.2, 0.18, 0.15, 1)
    mx = new("ShaderNodeMixShader")
    link(ramp.outputs[0], mx.inputs[0])
    link(pane.outputs[0], mx.inputs[1])
    link(df.outputs[0], mx.inputs[2])
    link(mx.outputs[0], out.inputs["Surface"])
    return m


class Skin:
    """Sheets of quads that share their corners (so a curve shades as a curve), each face its own paint."""

    def __init__(self):
        self.v, self.f, self.i = [], [], []

    def sheet(self, pts, paint, flip=False):
        """pts[column][row]; paint(column, row) -> a material's number, or None for no face."""
        n0, rows = len(self.v), len(pts[0])
        for col in pts:
            self.v += col
        for c in range(len(pts) - 1):
            for r in range(rows - 1):
                m = paint(c, r)
                if m is None:
                    continue
                a, b, cc, d = n0 + c * rows + r, n0 + (c + 1) * rows + r, n0 + (c + 1) * rows + r + 1, n0 + c * rows + r + 1
                self.f.append((a, d, cc, b) if flip else (a, b, cc, d))
                self.i.append(m)

    def face(self, pts, m):
        n0 = len(self.v)
        self.v += pts
        self.f.append(tuple(range(n0, n0 + len(pts))))
        self.i.append(m)

    def build(self, name, mats, parent, smooth=True, blender_space=False):
        if not self.f:
            return None
        me = bpy.data.meshes.new(name)
        me.from_pydata([v if blender_space else g2b(v) for v in self.v], [], self.f)
        uv = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            n = poly.normal
            ax = max(range(3), key=lambda k: abs(n[k]))
            a, b = [(1, 2), (0, 2), (0, 1)][ax]
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (co[a], co[b])
            poly.use_smooth = smooth
            poly.material_index = self.i[poly.index]
        for m in mats:
            me.materials.append(m)
        if smooth:
            me.set_sharp_from_angle(angle=math.radians(35))
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = parent
        return ob


def _fit(layout, length):
    """A section's panels laid out along it: [(what, x from, x to)], the stretchy ones sized to fill."""
    fixed = sum(w for _, w, s in layout if not s)
    k = (length - fixed) / sum(w for _, w, s in layout if s)
    out, x = [], 0.0
    for what, w, s in layout:
        w = w * k if s else w
        out.append((what, x, x + w))
        x += w
    return out


def _disc(acc, c, r, n=18):
    """A disc facing +x (a lamp's lens)."""
    for q in range(n):
        a0, a1 = 2 * math.pi * q / n, 2 * math.pi * (q + 1) / n
        p0 = (c[0], c[1] + r * math.sin(a0), c[2] + r * math.cos(a0))
        p1 = (c[0], c[1] + r * math.sin(a1), c[2] + r * math.cos(a1))
        acc.quad(c, p0, p1, p1)


def _paints(p):
    """The car's paints and stuffs ("silt": gloss paint and glass shed most of what the flood left)."""
    paint = {"rough": 0.28, "coat": 0.9, "grime": 1.25, "streaks": 0.45, "silt": 0.45, "bevel": 0.0}
    return {
        "white": M(dict(paint, color=[0.80, 0.81, 0.82])),
        "blue": M(dict(paint, color=[0.004, 0.075, 0.30])),
        "glass": _glass("combino_glass", (0.11, 0.125, 0.13), 0.13),
        "black": M({"color": [0.012, 0.013, 0.015], "rough": 0.06, "coat": 1.0, "grime": 0.9, "streaks": 0.3, "silt": 0.4, "bevel": 0.0}),
        "rubber": M({"color": [0.05, 0.05, 0.052], "rough": 0.72, "noise": 0.15, "noise_scale": 40.0, "grime": 1.3, "bevel": 0.004}),
        "seal": M({"color": [0.16, 0.165, 0.17], "rough": 0.8, "noise": 0.2, "noise_scale": 30.0, "grime": 1.4, "bevel": 0.0}),
        "roof": M({"color": [0.33, 0.34, 0.35], "rough": 0.6, "noise": 0.25, "noise_scale": 12.0, "grime": 1.6, "streaks": 0.3, "bevel": 0.006}),
        "steel": M({"color": [0.42, 0.42, 0.43], "rough": 0.4, "metal": 1.0, "grime": 1.4, "bevel": 0.004}),
        "chrome": M({"color": [0.75, 0.76, 0.78], "rough": 0.12, "metal": 1.0, "grime": 0.8, "bevel": 0.0}),
        "dark": M({"color": [0.022, 0.022, 0.024], "rough": 0.55, "grime": 1.1, "bevel": 0.004}),
        "floor": M({"color": [0.12, 0.125, 0.13], "rough": 0.5, "noise": 0.5, "noise_scale": 60.0, "grime": 1.3, "bevel": 0.0}),
        "lining": M({"color": [0.55, 0.55, 0.52], "rough": 0.55, "grime": 0.9, "bevel": 0.004}),
        "seat": M({"color": [0.03, 0.06, 0.2], "rough": 0.9, "noise": 0.45, "noise_scale": 90.0, "grime": 1.0, "bevel": 0.012}),
        "yellow": M({"color": [0.85, 0.6, 0.03], "rough": 0.3, "coat": 0.5, "grime": 0.8, "bevel": 0.0}),
        "red": M({"color": [0.5, 0.02, 0.02], "rough": 0.2, "coat": 0.8, "bevel": 0.0}),
    }


def _section(sr, kind, L, k, hw, mats, rng, o):
    """One section in its own frame: x from its back end (0) to its front (L; a cab's nose tip)."""
    y = [r * k for r in ROWS]
    Ls = L - NOSE if kind == "cab" else L
    panels = _fit(LAYOUT[kind], Ls)
    skin_mats = [mats["white"], mats["blue"], mats["glass"], mats["black"], mats["seal"], mats["roof"], mats["rubber"]]
    skin = Skin()
    parts = defaultdict(Acc)       # flat things, by stuff
    rods = defaultdict(Acc)        # round things, by stuff
    gone = set()                   # panes put in

    def band(what, r, cap):
        if what == "end":
            return R
        if what == "door" and 1 <= r <= 7:
            return None
        glass_rows = (5, 6, 7) if what == "cabwin" else (6, 7)
        if what in ("window", "cabwin") and r in glass_rows:
            return G
        if what in ("pillar", "wall") and r in (6, 7):   # (the band runs black from cab to tail: glass over the posts)
            return K
        if r <= 2 or r == 9 or (cap and 9 <= r <= 14):
            return B
        return ROOF if r >= 15 else W

    for sz in (1, -1):
        xs = [panels[0][1]] + [b for _, _, b in panels]
        pts = [[(x, y[r], sz * (hw - INSET[r])) for r in range(len(ROWS))] for x in xs]

        def paint(c, r, sz=sz):
            what = panels[c][0]
            if what == "window" and o["smashed"] and r in (6, 7) and ((c, sz) in gone or (r == 6 and rng.random() < 0.8)):
                gone.add((c, sz))
                return None
            return band(what, r, what == "cabwin")
        skin.sheet(pts, paint, flip=sz < 0)
        zf = sz * (hw + 0.003)
        for c, (what, xa, xb) in enumerate(panels):
            if (c, sz) in gone:   # what is left in the frame: small teeth of glass along its edges
                for _ in range(rng.randint(7, 12)):
                    e = rng.random()
                    bx, by = (rng.uniform(xa, xb), y[6]) if e < 0.5 else ((xa if e < 0.75 else xb), rng.uniform(y[6], y[8]))
                    up = (rng.uniform(-0.05, 0.05), rng.uniform(0.04, 0.17)) if e < 0.5 else ((1 if e < 0.75 else -1) * rng.uniform(0.03, 0.13), rng.uniform(-0.05, 0.05))
                    wdt = rng.uniform(0.02, 0.07)
                    a_, b_ = ((bx - wdt, by), (bx + wdt, by)) if e < 0.5 else ((bx, by - wdt), (bx, by + wdt))
                    zs = zf - sz * 0.004
                    parts["glass"].quad((a_[0], a_[1], zs), (b_[0], b_[1], zs), (bx + up[0], by + up[1], zs), (bx + up[0], by + up[1], zs))
            if what != "door" and c > 0 and panels[c - 1][0] != "door":   # the seam between two panels
                parts["dark"].box((xa - 0.003, y[1], zf - 0.004), (xa + 0.003, y[6] if what != "cabwin" else y[5], zf - 0.0005))
                parts["dark"].box((xa - 0.003, y[8], zf - 0.004), (xa + 0.003, y[12], zf - 0.0005))
            if what == "window" and xb - xa > 1.1:   # a hatch in the skirt under it: a thin dark outline
                ha, hb = xa + 0.18, xa + 0.18 + min(0.9, xb - xa - 0.36)
                for lo, hi in (((ha, 0.33), (hb, 0.336)), ((ha, 0.60), (hb, 0.606)), ((ha, 0.33), (ha + 0.006, 0.606)), ((hb - 0.006, 0.33), (hb, 0.606))):
                    parts["dark"].box((lo[0], lo[1] * k, zf - 0.004), (hi[0], hi[1] * k, zf - 0.0005))
            if what == "window" and (c, sz) not in gone and xb - xa > 1.1:   # the tilting light at its top
                parts["dark"].box((xa + 0.02, y[8] - 0.36 * k, zf - 0.004), (xb - 0.02, y[8] - 0.335 * k, zf + 0.001))
            if what == "door":
                leaves = 2 if xb - xa > 1.0 else 1
                wl = (xb - xa) / leaves
                is_open = o["doors_open"] and sz == o["side"]
                for q in range(leaves):
                    la = xa + q * wl
                    slide = (0.0 if not is_open else (-(wl - 0.03) if (q == 0) else (wl - 0.03)))
                    zo = sz * (hw - 0.004 + (0.07 if is_open else 0.0))
                    a0, a1 = la + slide + 0.006, la + wl + slide - 0.006
                    y0, y1, st = y[1] + 0.02, y[8] - 0.01, 0.055
                    for lo, hi in (((a0, y0), (a1, y0 + 0.24 * k)), ((a0, y1 - 0.07), (a1, y1)), ((a0, y0), (a0 + st, y1)), ((a1 - st, y0), (a1, y1))):
                        parts["blue"].box((lo[0], lo[1], min(zo, zo - sz * 0.035)), (hi[0], hi[1], max(zo, zo - sz * 0.035)))
                    parts["glass"].quad((a0 + st, y0 + 0.24 * k, zo - sz * 0.012), (a1 - st, y0 + 0.24 * k, zo - sz * 0.012),
                                        (a1 - st, y1 - 0.07, zo - sz * 0.012), (a0 + st, y1 - 0.07, zo - sz * 0.012))
                    parts["rubber"].box((a0 - 0.006, y0, min(zo, zo - sz * 0.03)), (a0 + 0.004, y1, max(zo, zo - sz * 0.03)))
                    parts["rubber"].box((a1 - 0.004, y0, min(zo, zo - sz * 0.03)), (a1 + 0.006, y1, max(zo, zo - sz * 0.03)))
                    rods["steel"].rod((a0 + st + 0.05, y0 + 0.75 * k, zo - sz * 0.06), (a0 + st + 0.05, y0 + 1.25 * k, zo - sz * 0.06), 0.014, 0.014, 6)
                parts["yellow"].box((xa, y[1], sz * (hw - 0.16) if sz > 0 else -hw + 0.005), (xb, y[1] + 0.045, hw - 0.005 if sz > 0 else sz * (hw - 0.16)))
                bx_ = xb + 0.06   # its button, on the wall beside it
                parts["dark"].box((bx_ - 0.035, 1.02 * k, zf - 0.004), (bx_ + 0.035, 1.16 * k, zf + 0.004))
                parts["button" if o["lit"] else "dark"].box((bx_ - 0.016, 1.07 * k, zf), (bx_ + 0.016, 1.11 * k, zf + 0.006))
        if kind == "cab":   # the blue line steps up to the cab's cap; the car's number
            xk = panels[-1][1]
            parts["blue"].quad((xk - 0.42, y[10], zf), (xk + 0.001, y[10], zf), (xk + 0.001, y[12], zf), (xk - 0.2, y[12], zf))
            text(sr, o["fleet"], (xk - 0.75, 0.47 * k, zf), 0.085, mats["white"], depth=0.0, yaw=0.0 if sz > 0 else 180.0)
        if kind in ("cab", "mid"):   # the operator's mark, and the city's three crosses beside it
            wx = (panels[1][1] + panels[1][2]) / 2
            text(sr, OPERATOR, (wx + sz * 0.22, 0.975 * k, zf), 0.15, mats["blue"], depth=0.0, yaw=0.0 if sz > 0 else 180.0)
            for q in range(3):
                cx_ = wx - sz * (0.36 + q * 0.14)
                for s_ in (1, -1):
                    parts["blue"].quad((cx_ - 0.05, 0.975 * k - s_ * 0.05, zf), (cx_ - 0.028, 0.975 * k - s_ * 0.05, zf),
                                       (cx_ + 0.05, 0.975 * k + s_ * 0.05, zf), (cx_ + 0.028, 0.975 * k + s_ * 0.05, zf))

    # The roof between its fairings, and what stands on it.
    zr = hw - INSET[17]
    parts["roof"].box((0.0, y[17] - 0.04, -zr), (Ls, y[17], zr))
    _roof_gear(kind, Ls, y[17], k, zr, parts, rods, rng, o)

    # The saloon: floor, ceiling and its lights, seats where there are windows, poles at the doors.
    xin = Ls + (0.45 if kind == "cab" else 0.0)
    parts["floor"].box((0.02, y[1] - 0.01, -hw + 0.02), (xin, y[1] + 0.03, hw - 0.02))
    parts["dark"].box((0.25, 0.09 * k, -hw + 0.16), (Ls - 0.1, y[1] - 0.01, hw - 0.16))
    parts["lining"].box((0.02, y[8] + 0.03, -hw + 0.02), (xin, y[8] + 0.07, hw - 0.02))
    for sz in (1, -1):
        parts["strip_on" if o["lit"] else "dark"].box((0.3, y[8] + 0.015, sz * 0.42 - 0.05), (Ls - 0.3, y[8] + 0.031, sz * 0.42 + 0.05))
        rods["yellow"].rod((0.15, 2.05 * k, sz * 0.36), (Ls - 0.15, 2.05 * k, sz * 0.36), 0.016, 0.016, 6)
    for what, xa, xb in panels:
        if what == "window":
            n = max(1, int((xb - xa) / 0.78))
            for q in range(n):
                xx = xa + (q + 0.5) * (xb - xa) / n
                for zc in (hw - 0.3, hw - 0.76, -(hw - 0.3)):
                    parts["seat"].box((xx - 0.2, 0.68 * k, zc - 0.21), (xx + 0.22, 0.78 * k, zc + 0.21))
                    parts["seat"].box((xx - 0.26, 0.74 * k, zc - 0.21), (xx - 0.18, 1.32 * k, zc + 0.21))
                    parts["dark"].box((xx - 0.14, y[1] + 0.03, zc - 0.03), (xx + 0.1, 0.68 * k, zc + 0.03))
                    rods["yellow"].rod((xx - 0.22, 1.32 * k, zc - 0.17), (xx - 0.22, 1.32 * k, zc + 0.17), 0.014, 0.014, 6)
        if what == "door":
            for xx in (xa - 0.03, xb + 0.03):
                for sz in (1, -1):
                    rods["yellow"].rod((xx, y[1], sz * (hw - 0.42)), (xx, y[8] + 0.03, sz * (hw - 0.42)), 0.017, 0.017, 6)
    if kind in ("cab", "mid"):   # the wheels, what shows of them under the skirt
        for bx in ((Ls * 0.42, Ls * 0.42 + 1.8) if kind == "cab" else (L / 2 - 0.9, L / 2 + 0.9)):
            for sz in (1, -1):
                rods["steel"].rod((bx, 0.3 * k, sz * 0.66), (bx, 0.3 * k, sz * 0.8), 0.3 * k, 0.3 * k, 18)
            parts["dark"].box((bx - 0.12, 0.2 * k, -0.66), (bx + 0.12, 0.4 * k, 0.66))
    if kind == "cab":
        _nose(sr, Ls, k, hw, y, skin, parts, rods, mats, o)
        parts["lining"].box((panels[-1][1] - 0.05, y[1], -hw + 0.03), (panels[-1][1] - 0.01, y[8] + 0.03, hw - 0.03))   # the cab's back wall
        parts["dark"].box((Ls + 0.18, y[1], -0.75), (Ls + 0.62, 1.12 * k, 0.75))    # the desk
        parts["seat"].box((Ls - 0.5, 0.72 * k, -0.24), (Ls - 0.05, 0.84 * k, 0.24))
        parts["seat"].box((Ls - 0.58, 0.8 * k, -0.24), (Ls - 0.48, 1.55 * k, 0.24))
    skin.build("tram_skin", skin_mats, sr)
    stuff = dict(mats, strip_on=city.emit((1.0, 0.93, 0.8), 7.0, "tram_strip"), button=city.emit((0.2, 1.0, 0.3), 3.0, "tram_button"),
                 head=city.emit((1.0, 0.95, 0.85), 40.0, "tram_head"), tail=city.emit((1.0, 0.05, 0.02), 6.0, "tram_tail"))
    for key, acc in parts.items():
        acc.build("tram_" + key, stuff[key], sr, smooth=False)
    for key, acc in rods.items():
        acc.build("tram_round_" + key, stuff[key], sr, smooth=True)


def _roof_gear(kind, Ls, yd, k, zr, parts, rods, rng, o):
    """What a low-floor tram carries on its roof because there is no room under the floor: the air
    units and their fans, the resistor and converter boxes, the cable runs; the pantograph."""
    def unit(x0, x1, hh, zz, fans=0, slats=0):
        parts["roof"].box((x0, yd, -zz), (x1, yd + hh, zz))
        for q in range(fans):
            cx = x0 + (q + 0.5) * (x1 - x0) / fans
            rr = min(zz, (x1 - x0) / fans / 2) * 0.72
            rods["dark"].rod((cx, yd + hh - 0.002, 0.0), (cx, yd + hh + 0.006, 0.0), rr, rr, 20)
        for q in range(slats):
            for sz in (1, -1):
                yy = yd + 0.05 + q * (hh - 0.1) / max(1, slats - 1)
                parts["dark"].box((x0 + 0.08, yy, sz * zz - 0.004), (x1 - 0.08, yy + 0.018, sz * zz + 0.004))
    if kind == "cab":
        unit(0.9, min(3.3, Ls - 1.6), 0.3 * k, 0.6, fans=2, slats=4)
        unit(Ls - 1.4, Ls - 0.5, 0.2 * k, 0.45, fans=1)
    elif kind == "doors":
        unit(0.5, 2.5, 0.27 * k, 0.55, slats=5)
        unit(3.3, Ls - 0.6, 0.24 * k, 0.6, fans=2, slats=3)
    else:
        xc, y0 = Ls / 2, yd + 0.15
        up = 1.0 if o["pantograph"] else 0.1
        for sx in (-0.55, 0.55):
            for sz in (-0.42, 0.42):
                rods["lining"].rod((xc + sx, yd, sz), (xc + sx, y0, sz), 0.05, 0.035, 8)
            rods["steel"].rod((xc + sx, y0, -0.46), (xc + sx, y0, 0.46), 0.025, 0.025, 6)
        for sz in (-0.42, 0.42):
            rods["steel"].rod((xc - 0.55, y0, sz), (xc + 0.55, y0, sz), 0.025, 0.025, 6)
        knee, head = (xc + 0.5, y0 + 0.85 * up + 0.04, 0.0), (xc - 0.3, y0 + 1.72 * up + 0.08, 0.0)
        rods["steel"].rod((xc - 0.5, y0 + 0.03, 0.0), knee, 0.032, 0.028, 8)
        for sz in (-1, 1):
            rods["steel"].rod((knee[0], knee[1], sz * 0.05), (head[0], head[1], sz * 0.3), 0.018, 0.016, 6)
        rods["steel"].rod((xc - 0.15, y0 + 0.03, 0.0), (knee[0] - 0.12, knee[1] - 0.05, 0.0), 0.012, 0.012, 5)
        for sx in (-0.13, 0.13):   # the head: two carbon strips, their horns turned down
            rods["dark"].rod((head[0] + sx, head[1], -0.6), (head[0] + sx, head[1], 0.6), 0.02, 0.02, 6)
            for sz in (-1, 1):
                rods["steel"].rod((head[0] + sx, head[1], sz * 0.6), (head[0] + sx, head[1] - 0.14, sz * 0.86), 0.014, 0.012, 5)
        rods["steel"].rod((head[0] - 0.13, head[1] - 0.03, 0.0), (head[0] + 0.13, head[1] - 0.03, 0.0), 0.014, 0.014, 5)
    for sz in (-0.25, 0.25):   # the cables from section to section
        rods["dark"].rod((0.0, yd + 0.03, sz), (Ls if kind != "cab" else Ls - 1.5, yd + 0.03, sz), 0.028, 0.028, 6)


def _nose(sr, x0, k, hw, y, skin, parts, rods, mats, o):
    """A cab's front: square in plan with rounded corners, leaning back from the bumper to the roof;
    the windscreen and the destination display one sheet of black glass between broad white corner
    pillars, blue below the bumper and over the top."""
    def reach(yy, ins):
        rake = max(0.0, yy - 0.78 * k) * math.tan(math.radians(8.0))
        tuck = max(0.0, 0.62 * k - yy) * 0.18
        return NOSE - rake - tuck - ins

    def P(t, yy, ins, off=0.0):
        c, s = math.cos(t), math.sin(t)
        return (x0 + (reach(yy, ins) + off) * abs(c) ** (2 / EXP), yy, math.copysign((hw - ins + off) * abs(s) ** (2 / EXP), s))

    def front(yy, z):   # the skin's x at a height and a place across
        return x0 + reach(yy, 0.0) * (1 - min(0.999, abs(z) / hw) ** EXP) ** (1 / EXP)

    half = [math.asin(f ** (EXP / 2)) for f in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.78, 0.86, 0.91)] + \
           [math.acos(f ** (EXP / 2)) for f in (0.7, 0.6, 0.5, 0.42, 0.33, 0.2, 0.1, 0.0)]
    ts = [-t for t in reversed(half[1:])] + half
    pts = [[P(t, y[r], INSET[r]) for r in range(NOSE_ROWS)] for t in ts]

    def paint(c, r):
        a = abs((ts[c] + ts[c + 1]) / 2)
        screen, cab = a < T_GLASS, a > T_CAB
        if r <= 1:
            return B
        if r in (2, 3):
            return (B if r == 2 else W) if cab else BUMP
        if r == 4:
            return W
        if r in (5, 6):
            return G if cab else W
        if r == 7:
            return (None if o["smashed"] and screen else G) if (screen or cab) else W
        if r == 8:
            return G if screen else W
        if r in (9, 10):
            return G if screen else B
        return B
    skin.sheet(pts, paint, flip=True)
    top = NOSE_ROWS - 1
    c0 = (x0 + 0.45 * reach(y[top], INSET[top]), y[top], 0.0)
    for c in range(len(ts) - 1):
        skin.face([c0, pts[c + 1][top], pts[c][top]], B)
    skin.face([c0, pts[0][top], pts[-1][top]], B)
    zr = hw - INSET[17]
    skin.face([(x0, y[17], -zr), (x0, y[17], zr), (x0, y[top], zr), (x0, y[top], -zr)], B)
    lip = [t for t in ts if abs(t) <= T_CAB + 1e-6]   # the bumper: a rubber lip standing proud of the skin
    yb0, yb1 = y[2] + 0.012, y[4] - 0.012
    skin.sheet([[P(t, yb0, 0.0), P(t, yb0 + 0.012, 0.0, 0.04), P(t, yb1 - 0.012, 0.0, 0.04), P(t, yb1, 0.0)] for t in lip], lambda c, r: BUMP, flip=True)
    for sz in (1, -1):
        for key, yy, zz, r in (("head", 1.045 * k, 0.8, 0.085), ("tail", 0.9 * k, 0.62, 0.058)):
            z = sz * zz * hw / 1.2
            x = front(yy, z)
            rods["chrome"].rod((x - 0.03, yy, z), (x + 0.014, yy, z), r + 0.014, r + 0.014, 18)
            on = o["lit"] and (key == "head") == o["front"]   # the front cab shows white, the back one red
            _disc(parts[key if on else ("chrome" if key == "head" else "red")], (x + 0.016, yy, z), r)
        # the mirror: an arm out from the corner pillar's top, the glass hung under it
        zm = sz * (hw + 0.27)
        rods["dark"].rod((x0 + 0.5, 2.7 * k, sz * (hw - 0.02)), (x0 + 0.8, 2.56 * k, zm), 0.022, 0.018, 6)
        rods["dark"].rod((x0 + 0.8, 2.56 * k, zm), (x0 + 0.8, 2.34 * k, zm), 0.018, 0.018, 6)
        parts["dark"].box((x0 + 0.745, 1.98 * k, zm - 0.09), (x0 + 0.855, 2.36 * k, zm + 0.09))
        parts["chrome"].quad((x0 + 0.743, 2.0 * k, zm - 0.075), (x0 + 0.743, 2.0 * k, zm + 0.075), (x0 + 0.743, 2.34 * k, zm + 0.075), (x0 + 0.743, 2.34 * k, zm - 0.075))
    for za, zb, yb in ((0.28, -0.3, 2.05), (-0.42, -0.96, 1.95)):   # the wipers, parked
        a_, b_ = (front(1.31 * k, za) + 0.03, 1.31 * k, za), (front(yb * k, zb) + 0.03, yb * k, zb)
        rods["dark"].rod(a_, b_, 0.012, 0.009, 5)
        m_ = tuple(a_[q] + (b_[q] - a_[q]) * 0.45 for q in range(3))
        rods["dark"].rod((m_[0] - 0.012, m_[1], m_[2]), (b_[0] - 0.012, b_[1] + 0.03, b_[2]), 0.011, 0.011, 4)
    xh = front(0.43 * k, 0.0) + 0.002   # the coupler's hatch in the apron
    for lo, hi in (((0.30, -0.3), (0.308, 0.3)), ((0.552, -0.3), (0.56, 0.3)), ((0.30, -0.3), (0.56, -0.292)), ((0.30, 0.292), (0.56, 0.3))):
        parts["dark"].box((xh - 0.01, lo[0] * k, lo[1]), (xh, hi[0] * k, hi[1]))
    text(sr, o["fleet"], (front(0.9 * k, -0.34) + 0.004, 0.9 * k, -0.34), 0.07, mats["blue"], depth=0.0, yaw=90.0)
    text(sr, OPERATOR, (front(1.1 * k, 0.0) + 0.004, 1.1 * k, 0.0), 0.1, mats["blue"], depth=0.0, yaw=90.0)
    xd = front(2.88 * k, 0.0) - 0.13   # the destination display, behind the glass
    parts["dark"].box((xd - 0.05, 2.7 * k, -0.84 * hw), (xd - 0.012, 3.07 * k, 0.84 * hw))
    if o["lit"] and o["board"]:
        text(sr, o["board"], (xd, 2.885 * k, -0.14), 0.19 * k, city.emit((1.0, 0.55, 0.06), 9.0, "tram_board"), font="DejaVuSansMono-Bold.ttf", depth=0.0, yaw=90.0)
        text(sr, o["line"], (xd, 2.885 * k, 0.66 * hw), 0.24 * k, city.emit((1.0, 0.95, 0.85), 7.0, "tram_line"), font="DejaVuSans-Bold.ttf", depth=0.0, yaw=90.0)


def build(root, p, w, h, d):
    """The "tram" prop: five sections on their hinges (tram_layout.chain), each built in its own
    frame and stood where the night left it; bellows between them; each lit section's light."""
    k, hw = h / 3.4, d / 2
    mats = _paints(p)
    rng = random.Random(p.get("seed", 7))
    der = p.get("derail", {})
    roll, lift, pitch = (tram_layout.resample(der.get(key)) for key in ("roll", "lift", "pitch"))
    dark, smashed = set(tram_layout.spread(p.get("dark"))), set(tram_layout.spread(p.get("smashed")))
    fleet = str(p.get("fleet", 2001 + rng.randrange(130)))
    stood = []
    for i, (cx, cz, a, L) in enumerate(tram_layout.chain(w, der.get("yaw"))):
        sr = builders.empty_at("tram_section", (0.0, 0.0, 0.0), 0.0)
        sr.parent = root
        sr.location = g2b((cx, lift[i], cz))
        sr.rotation_euler = (math.radians(roll[i]), math.radians(-pitch[i]), a)
        back = i == 0   # (the back cab: the front one, turned round)
        mr = builders.empty_at("tram_module", (L / 2 if back else -L / 2, 0.0, 0.0), 180.0 if back else 0.0)
        mr.parent = sr
        lit = i not in dark
        o = {"lit": lit, "smashed": i in smashed, "doors_open": p.get("doors_open") == "all", "side": -1 if back else 1, "front": i == len(KINDS) - 1,
             "fleet": fleet, "board": p.get("board", "CENTRAAL"), "line": str(p.get("line", "24")), "pantograph": p.get("pantograph", True)}
        _section(mr, KINDS[i], L, k, hw, mats, rng, o)
        if lit:   # its light, through the glass
            ld = bpy.data.lights.new("tram_glow", "AREA")
            ld.shape, ld.size, ld.size_y = "RECTANGLE", L * 0.8, d * 0.55
            ld.energy, ld.color = p.get("power", 300.0) * L / w, (1.0, 0.92, 0.8)
            ob = bpy.data.objects.new("tram_glow", ld)
            bpy.context.scene.collection.objects.link(ob)
            ob.parent = sr
            ob.location = g2b((0.0, 2.6 * k, 0.0))
            street.hide_panel(ob)
        stood.append((sr, L))
    ring = [(0.3 * k, hw - 0.07, 0), (3.0 * k, hw - 0.07, 0), (3.25 * k, hw - 0.3, 1), (3.25 * k, -(hw - 0.3), 1), (3.0 * k, -(hw - 0.07), 0), (0.3 * k, -(hw - 0.07), 0)]
    for (sa, la), (sb, lb) in zip(stood, stood[1:]):   # the bellows: pleats from one section's end to the next's
        bel, pleats, cols = Skin(), 9, []
        for q in range(pleats):
            t, pinch = q / (pleats - 1), (0.0 if q % 2 == 0 else 0.06)
            col = []
            for yy, zz, on_top in ring:
                pt = (yy - pinch if on_top else yy, zz - math.copysign(pinch, zz) * (0 if on_top else 1))
                va = sa.matrix_basis @ Vector(g2b((la / 2, pt[0], pt[1])))
                vb = sb.matrix_basis @ Vector(g2b((-lb / 2, pt[0], pt[1])))
                col.append(tuple(va.lerp(vb, t)))
            cols.append(col)
        bel.sheet(cols, lambda c, r: 0)
        bel.build("tram_bellows", [mats["rubber"]], root, smooth=False, blender_space=True)
    return root
