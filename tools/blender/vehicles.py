# damned_waters/tools/blender/vehicles.py
# Purpose: the city's cars, vans and trams, modelled the way a car designer's clay is: a cage of
# cross-sections along the body (the sill, the shoulder, the window line, the roof's turn), lofted
# and smoothed (subdivision), with the glass, the pillars, the doors and the livery laid on the
# cage's own faces by where they fall; wheels turned on a lathe and set in arches cut out of the
# body (booleans), lights, plates, mirrors, a roof sign or a light bar. Replaces the boxes the
# "vehicle" and "tram" props were built from (aftermath.py, city.py): same props, same options
# ("livery", "door_open", "burnt"; a tram's "derail", "dark", "smashed", "pantograph").
# Coordinates as in street.py (Godot frame, metres; a vehicle's front is +x, its left side +z).
#
# ELI5: instead of building a car from shoeboxes, we cut slices of its shape like a loaf of bread,
# line them up, and stretch a skin over them; then we paint the windows on the skin and cut holes
# for the wheels.
import math

import bpy

import builders
import kit
import street
from roomspec import g2b
from street import Acc, M, lbox, text

# ── The loft: a cage of sections, skinned and smoothed ─────────────────────────────────────────
def loft(name, root, stations, mats, face_mat, subd=2, creases=None, ends=(0.06, 0.06)):
    """stations: [(x, [(z, y), ...]), ...], each loop the same length (round the body, closed);
    face_mat(i, k) -> index into mats for the face between station i and i+1, loop points k and k+1.
    creases {k: 0..1}: the lines along the body through loop point k held sharp (a shoulder, a
    window line, a roof's edge). The ends are rounded off (each end's last loop shrunk toward its
    middle over `ends` metres, then capped small). Returns the object (Subdivision on it)."""
    def shrink(loop, k):
        cz = sum(z for z, _ in loop) / len(loop)
        cy = sum(y for _, y in loop) / len(loop)
        return [(cz + (z - cz) * k, cy + (y - cy) * k) for z, y in loop]
    (x0, l0), (x1, l1) = stations[0], stations[-1]
    rounded = ((1.0, 0.08), (0.92, 0.35), (0.7, 0.68), (0.4, 0.9))   # (how far out, how big): a nose, capped small
    flat = ((1.0, 0.9),)                                                 # a flat back with its edge turned
    s0 = flat if ends[0] < 0 else rounded
    s1 = flat if ends[1] < 0 else rounded
    pre = [(x0 - abs(ends[0]) * f, shrink(l0, k)) for f, k in s0] if ends[0] else []
    post = [(x1 + abs(ends[1]) * f, shrink(l1, k)) for f, k in reversed(s1)] if ends[1] else []
    base_mat, np_, last_face = face_mat, len(pre), len(stations) - 2   # (the ends' faces: the caps' colour)
    face_mat = lambda i, k: base_mat(i - np_, k) if 0 <= i - np_ <= last_face else base_mat(-1 if i < np_ else -2, k)
    stations = pre + list(stations) + post
    n = len(stations[0][1])
    verts, faces, idx = [], [], []
    for x, loop in stations:
        for z, y in loop:
            verts.append(g2b((x, y, z)))
    for i in range(len(stations) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
            idx.append(face_mat(i, k))
    first, last = list(range(n)), list(range((len(stations) - 1) * n, len(stations) * n))
    faces.append(tuple(reversed(first)))
    idx.append(face_mat(-1, 0))
    faces.append(tuple(last))
    idx.append(face_mat(-2, 0))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        nrm = poly.normal
        ax = max(range(3), key=lambda q: abs(nrm[q]))
        u_, v_ = [(1, 2), (0, 2), (0, 1)][ax]
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co[u_], co[v_])
        poly.use_smooth = True
    for m in mats:
        me.materials.append(m)
    for poly, mi in zip(me.polygons, idx):
        poly.material_index = mi
    if creases:   # hold the body's lines: the edges along it through those loop points
        at = {}
        for e in me.edges:
            a, b = sorted(e.vertices)
            at[(a, b)] = e.index
        cr = me.attributes.new("crease_edge", "FLOAT", "EDGE")
        for i in range(len(stations) - 1):
            for k, c in creases.items():
                e = at.get((i * n + k, (i + 1) * n + k))
                if e is not None:
                    cr.data[e].value = c
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = root
    if subd:
        sd = ob.modifiers.new("subd", "SUBSURF")
        sd.levels = sd.render_levels = subd
    return ob


def _lerp_keys(keys, t):
    """Linear between key stations: keys [(t, {param: value}), ...] -> the params at t."""
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return {k: a[k] + (b[k] - a[k]) * u for k in a}
    return dict(keys[-1][1] if t > keys[-1][0] else keys[0][1])


def _profile(hw, y0, yb, yt, rhw, glass_from):
    """One section round the body (z across, y up), from the bottom's middle up the right side, over
    the top and down the left: sill, side, shoulder, window line, roof edge, crown. 20 points."""
    right = [(hw * 0.8, y0), (hw * 0.97, y0 + 0.08), (hw, y0 + 0.28 * (yb - y0)), (hw, y0 + 0.72 * (yb - y0)),
             (hw * 0.99, yb), (hw * 0.965, glass_from), (rhw * 1.02, yt - 0.11), (rhw * 0.9, yt - 0.025), (rhw * 0.45, yt)]
    return [(0.0, y0 - 0.02)] + right + [(0.0, yt + 0.008)] + [(-z, y) for z, y in reversed(right)]


# Points round a section (_profile): 0 bottom, 1 sill, 2 rocker, 3 lower side, 4 upper side, 5 shoulder,
# 6 window line, 7 roof side, 8 roof edge, 9 crown side, 10 top; then 11..19 the other side, mirrored.
SIDE_GLASS = {6, 12}           # faces from point 6 to 7 (and 12 to 13 on the other side): the side windows
TOP = {7, 8, 9, 10, 11}        # faces over the top: roof, or windscreen / back window
LOW = {2, 16}                  # the lower side (a stripe's lower row)
HIGH = {3, 15}                 # the upper side (a stripe's upper row)
DOORS = {1, 2, 3, 4, 5, 15, 16, 17, 18}   # the door's panel, under its window

CAR = {   # t along the car (0 the back, 1 the front): heights as shares of its height, half-widths of its half-width
    "hatch": [(0.0, dict(top=0.6, belt=0.5, hw=0.86, rh=0.75, cab=0.0)), (0.035, dict(top=0.72, belt=0.58, hw=0.95, rh=0.8, cab=0.0)),
              (0.08, dict(top=0.88, belt=0.6, hw=0.98, rh=0.8, cab=1.0)), (0.2, dict(top=0.985, belt=0.62, hw=1.0, rh=0.82, cab=1.0)),
              (0.56, dict(top=1.0, belt=0.62, hw=1.0, rh=0.82, cab=1.0)), (0.68, dict(top=0.94, belt=0.61, hw=0.99, rh=0.8, cab=1.0)),
              (0.78, dict(top=0.66, belt=0.6, hw=0.98, rh=0.86, cab=0.0)), (0.9, dict(top=0.6, belt=0.56, hw=0.96, rh=0.84, cab=0.0)),
              (0.97, dict(top=0.55, belt=0.5, hw=0.9, rh=0.8, cab=0.0)), (1.0, dict(top=0.46, belt=0.42, hw=0.8, rh=0.7, cab=0.0))],
    "sedan": [(0.0, dict(top=0.66, belt=0.58, hw=0.86, rh=0.76, cab=0.0)), (0.04, dict(top=0.72, belt=0.62, hw=0.95, rh=0.84, cab=0.0)),
              (0.17, dict(top=0.72, belt=0.63, hw=0.98, rh=0.86, cab=0.0)), (0.27, dict(top=0.96, belt=0.63, hw=1.0, rh=0.8, cab=1.0)),
              (0.57, dict(top=1.0, belt=0.63, hw=1.0, rh=0.8, cab=1.0)), (0.67, dict(top=0.93, belt=0.62, hw=0.99, rh=0.8, cab=1.0)),
              (0.77, dict(top=0.66, belt=0.61, hw=0.98, rh=0.86, cab=0.0)), (0.9, dict(top=0.62, belt=0.57, hw=0.96, rh=0.84, cab=0.0)),
              (0.97, dict(top=0.56, belt=0.51, hw=0.9, rh=0.8, cab=0.0)), (1.0, dict(top=0.47, belt=0.43, hw=0.8, rh=0.7, cab=0.0))],
    "van": [(0.0, dict(top=0.94, belt=0.42, hw=0.92, rh=0.9, cab=1.0)), (0.025, dict(top=0.99, belt=0.44, hw=0.98, rh=0.94, cab=1.0)),
            (0.5, dict(top=1.0, belt=0.45, hw=1.0, rh=0.94, cab=1.0)), (0.74, dict(top=1.0, belt=0.45, hw=1.0, rh=0.94, cab=1.0)),
            (0.8, dict(top=0.9, belt=0.45, hw=0.99, rh=0.9, cab=1.0)), (0.87, dict(top=0.55, belt=0.44, hw=0.97, rh=0.9, cab=0.0)),
            (0.95, dict(top=0.47, belt=0.4, hw=0.94, rh=0.86, cab=0.0)), (1.0, dict(top=0.38, belt=0.33, hw=0.84, rh=0.76, cab=0.0))],
}
# Where the glass is, by t: (back window from, to), (side windows from, to), (windscreen from, to), pillars
GLASS = {"hatch": ((0.035, 0.12), (0.12, 0.66), (0.66, 0.79), [0.21, 0.42]),
         "sedan": ((0.2, 0.29), (0.29, 0.66), (0.66, 0.78), [0.47]),
         "van": ((0.0, 0.0), (0.7, 0.8), (0.8, 0.875), [])}


def car(root, p, w, h, d):
    """A car or van ("van": true, or taller than 1.8 m), front along +x: its body lofted and smoothed,
    glass where its windows are, wheels in cut arches, lights (lit, unless "burnt"), the plates, the
    mirrors; a taxi's roof sign, a police van's or an ambulance's stripes and light bar; a door
    swung wide ("door_open": "left" | "right"); burned out ("burnt": scorched steel, sooted glass,
    no tyres, sat down on its rims)."""
    import aftermath
    liv = p.get("livery", "car")
    if liv == "army" and h > 2.5:
        return aftermath.army_truck(root, p, w, h, d)
    body_c, sa, sb, word, roof = aftermath.LIVERY.get(liv, aftermath.LIVERY["car"])
    van = p.get("van", h > 1.8)
    shape = "van" if van else ("sedan" if liv in ("taxi", "police") else "hatch")
    burnt = p.get("burnt", False)
    if p.get("color"):
        body_c = p["color"]
    paint = M({"color": [c * 0.9 for c in body_c], "rough": 0.28, "coat": 1.0, "grime": 1.1, "bevel": 0.0, "streaks": 0.3})
    glass = M({"color": [0.012, 0.016, 0.02], "rough": 0.04, "metal": 0.85, "grime": 0.5, "bevel": 0.0})
    trim = M({"color": [0.025, 0.025, 0.027], "rough": 0.55, "grime": 1.0, "bevel": 0.0})
    inside = M({"color": [0.02, 0.019, 0.018], "rough": 0.8, "bevel": 0.0})
    hole = _hole()
    if burnt:   # (the fire came after the water: no tide line on it, soot and rust instead)
        paint = M({"ph": "rusty_metal_02", "tint": [0.24, 0.21, 0.19], "value": 0.38, "rough": 0.92, "bevel": 0.0, "dry": True})
        glass = M({"color": [0.006, 0.006, 0.006], "rough": 0.95, "bevel": 0.0, "dry": True})
        inside = M({"color": [0.012, 0.011, 0.01], "rough": 0.95, "bevel": 0.0, "dry": True})
        trim = inside
    stripe_a = M({"color": list(sa), "rough": 0.3, "coat": 1.0, "bevel": 0.0}) if sa and not burnt else paint
    stripe_b = M({"color": list(sb), "rough": 0.3, "coat": 1.0, "bevel": 0.0}) if sb and not burnt else paint
    mats = [paint, glass, trim, stripe_a, stripe_b, inside, hole]
    PAINT, GLASS_, TRIM, SA, SB, INSIDE, HOLE = range(7)
    keys = CAR[shape]
    clear = 0.16 if van else 0.13   # the sill's height
    step = 0.18
    n = max(8, int(w / step))
    ts = [i / n for i in range(n + 1)]
    stations = []
    params = []
    for t in ts:
        k = _lerp_keys(keys, t)
        x = -w / 2 + t * w
        hw = d / 2 * k["hw"]
        yt = h * k["top"]
        yb = h * k["belt"]
        glass_from = yb + 0.03
        loop = _profile(hw, clear + (0.02 if t in (0.0, 1.0) else 0.0), yb, yt, d / 2 * k["rh"], glass_from)
        stations.append((x, loop))
        params.append((t, k))
    (bw0, bw1), (sw0, sw1), (ws0, ws1), pillars = GLASS[shape]
    open_side = {"left": 1, "right": -1}.get(p.get("door_open", ""), 0)
    door_t = (sw0 + 0.02, sw0 + 0.26) if not van else (0.72, 0.85)

    def face_mat(i, k):
        if i < 0:
            return PAINT
        t0, t1 = ts[i], ts[i + 1]
        tm = (t0 + t1) / 2
        side = 1 if k < 10 else -1
        if open_side and side == open_side and door_t[0] <= tm <= door_t[1] and (k in DOORS or k in SIDE_GLASS):
            return INSIDE   # the door's gone wide: its opening, the cab's dark inside
        win = HOLE if burnt else GLASS_   # (burned out: the glass gone, the shell's inside seen through)
        if k in SIDE_GLASS and sw0 <= tm <= sw1 and not any(abs(tm - pp) < 0.022 for pp in pillars):
            return win
        if k in TOP and ws0 <= tm <= ws1:
            return win
        if k in TOP and bw0 <= tm <= bw1 and bw1 > bw0:
            return win
        if sa and van and k in LOW | HIGH:   # Battenburg blocks (an ambulance) or two bands (police)
            if liv == "police":
                return SA if k in HIGH else SB
            block = int((tm * w) / 0.6)
            return SA if (block + (k in HIGH)) % 2 == 0 else SB
        if k in (0, 19) or k == 1 or k == 18:
            return TRIM if k in (0, 19) else PAINT
        return PAINT
    hold = builders.empty_at("vehicle_body", (0.0, 0.0, 0.0), 0.0)
    hold.parent = root
    hold.location = g2b((0.0, -0.09 if burnt else 0.0, 0.0))
    sharp = {5: 0.7, 14: 0.7, 6: 0.85, 13: 0.85, 8: 0.6 if not van else 0.85, 11: 0.6 if not van else 0.85, 2: 0.5, 17: 0.5}
    body = loft("car_body", hold, stations, mats, face_mat, creases=sharp, ends=(-0.05 if van else 0.09, 0.08))
    # Wheels in their arches: the arches cut out of the body, a dark liner inside each, the wheel.
    r = 0.37 if van else 0.31
    wb = w * (0.6 if van else 0.62)
    xs = (-wb / 2 - w * 0.02, wb / 2 + w * (0.06 if van else 0.03))
    cut = Acc()
    for x in xs:
        _cyl(cut, (x, r + 0.01, 0.0), r + 0.07, d + 0.6, 24)
    cutter = cut.build("arch_cutter", trim, hold, smooth=False)
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    bo = body.modifiers.new("arches", "BOOLEAN")
    bo.operation, bo.solver, bo.object = "DIFFERENCE", "EXACT", cutter
    liner = Acc()
    for x in xs:
        _cyl(liner, (x, r + 0.01, 0.0), r + 0.065, d - 0.12, 20, open_ends=True)
    liner.build("arch_liner", inside, hold, smooth=True)
    for x in xs:
        for sz in (-1, 1):
            _wheel(hold, (x, r, sz * (d / 2 - 0.13)), r, sz, burnt)
    if burnt:   # what's left inside: the seats' springs and frames, charred
        for sx in (-0.2, 0.25):
            kit.soft(hold, "burnt_seat", (w * sx, 0.55, 0.0), (0.55, 0.35, d * 0.7), inside, 0.05, 2)
    elif van:   # the rear doors' seam and handles
        lbox(hold, "rear_seam", (-w / 2 - 0.096, 0.4, -0.008), (-w / 2 - 0.08, h * 0.9, 0.008), trim)
    # Lights, grille, plates, mirrors, wipers.
    head = trim if burnt else builders.emissive("headlight", (1.0, 0.95, 0.85), 14.0)
    tail = trim if burnt else builders.emissive("taillight", (1.0, 0.04, 0.02), 4.0)
    kf = _lerp_keys(keys, 0.985)
    fy = h * kf["belt"] - 0.06
    for sz in (-1, 1):
        kit.soft(hold, "headlight", (w / 2 - 0.05, fy, sz * (d / 2 * kf["hw"] - 0.24)), (0.09, 0.11, 0.3), head, 0.03, 2)
        kit.soft(hold, "taillight", (-w / 2 + 0.04, h * _lerp_keys(keys, 0.02)["belt"] - 0.02, sz * (d / 2 * 0.86 - 0.12)), (0.07, 0.16, 0.2), tail, 0.03, 2)
    kit.soft(hold, "grille", (w / 2 - 0.03, fy - 0.05, 0.0), (0.06, 0.13, d * 0.36), trim, 0.02, 2)
    plate = M({"color": [0.85, 0.66, 0.04], "rough": 0.35, "bevel": 0.0})   # Dutch yellow
    pid = p.get("plate", "%02d-%s-%d" % (11 + int(abs(p["pos"][0] * 7)) % 80, "GXTKRZ"[int(abs(p["pos"][2])) % 6] + "HP"[int(abs(p["pos"][0])) % 2], int(abs(p["pos"][2] * 13)) % 9 + 1))
    for sx, y in ((1, 0.33), (-1, 0.42)):
        xe = sx * (w / 2 + 0.005)
        lbox(hold, "plate", (xe - 0.012, y - 0.055, -0.25), (xe + 0.012, y + 0.055, 0.25), plate)
        text(hold, pid, (xe + sx * 0.016, y, 0.0), 0.075, trim, font="DejaVuSansMono-Bold.ttf", depth=0.0, yaw=90.0 * sx)
    kg = _lerp_keys(keys, sw1)
    for sz in (-1, 1):   # the mirrors, on the doors' front corners
        kit.soft(hold, "mirror", (w * (sw1 - 0.5) - 0.12, h * kg["belt"] + 0.12, sz * (d / 2 * kg["hw"] + 0.1)), (0.12, 0.11, 0.17), paint, 0.03, 2)
    if not burnt:
        kw = _lerp_keys(keys, ws1)
        wipers = Acc()   # parked at the windscreen's foot
        for sz in (-1, 1):
            wipers.rod((w * (ws1 - 0.5) - 0.02, h * kw["top"] + 0.025, sz * 0.05), (w * (ws1 - 0.5) - 0.05, h * kw["top"] + 0.035, sz * 0.05 - sz * d * 0.33), 0.009, 0.007, 4)
        wipers.build("wipers", trim, hold)
    if word and sa and van and not burnt:   # POLITIE / AMBULANCE along each side
        for sz in (-1, 1):
            text(hold, word, (-w * 0.05, h * 0.62, sz * (d / 2 + 0.012)), 0.24, M({"color": [0.03, 0.06, 0.25] if liv == "police" else [0.06, 0.32, 0.12], "rough": 0.35}),
                 font="DejaVuSans-Bold.ttf", depth=0.0, yaw=0.0 if sz > 0 else 180.0)
    if roof and not burnt:
        ky = _lerp_keys(keys, 0.62 if not van else 0.75)["top"] * h
        if word == "TAXI":
            kit.soft(hold, "taxi_sign", (w * 0.08, ky + 0.07, 0.0), (0.28, 0.13, 0.62), builders.emissive("taxi_sign", roof, 6.0), 0.03, 2)
            text(hold, "TAXI", (w * 0.08 + 0.145, ky + 0.07, 0.0), 0.09, trim, font="DejaVuSans-Bold.ttf", depth=0.0, yaw=90.0)
        else:   # a light bar: blue lenses on a dark base
            kit.soft(hold, "lightbar", (w * 0.25, ky + 0.06, 0.0), (0.32, 0.1, d * 0.62), trim, 0.03, 2)
            for sz in (-1, 1):
                kit.soft(hold, "beacon", (w * 0.25, ky + 0.12, sz * d * 0.18), (0.26, 0.08, d * 0.2), builders.emissive("beacon_%d" % int(roof[2] * 100), roof, 9.0), 0.03, 2)
    if open_side:   # the door itself, swung out on its hinge
        sz = open_side
        kd = _lerp_keys(keys, door_t[1])
        dw = w * (door_t[1] - door_t[0])
        hinge = builders.empty_at("car_door", (0.0, 0.0, 0.0), 0.0)
        hinge.parent = hold
        hinge.location = g2b((w * (door_t[1] - 0.5), 0.0, sz * d / 2 * kd["hw"]))
        hinge.rotation_euler[2] = math.radians(-62 * sz)
        kit.soft(hinge, "door_panel", (-dw / 2, (clear + h * kd["belt"]) / 2 + 0.04, sz * 0.02), (dw, h * kd["belt"] - clear - 0.04, 0.07), paint, 0.025, 2)
        if not burnt:
            lbox(hinge, "door_glass", (-dw + 0.08, h * kd["belt"] + 0.02, sz * 0.02 - 0.006), (-0.08, h * kd["top"] - 0.1, sz * 0.02 + 0.006), glass)


def _hole():
    """See-through (a smashed window's empty frame)."""
    m = bpy.data.materials.get("vehicle_hole")
    if m is None:
        m = bpy.data.materials.new("vehicle_hole")
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        nt.links.new(tr.outputs[0], out.inputs["Surface"])
    return m


def _cyl(acc, c, r, length, seg, open_ends=False):
    """A cylinder along z into an accumulator (an arch's cutter, its liner)."""
    cx, cy, cz = c
    ring = [(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
    z0, z1 = cz - length / 2, cz + length / 2
    for k in range(seg):
        (ax, ay), (bx, by) = ring[k], ring[(k + 1) % seg]
        acc.quad((ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1))
    if not open_ends:
        for z, rev in ((z0, True), (z1, False)):
            for k in range(seg):
                (ax, ay), (bx, by) = ring[k], ring[(k + 1) % seg]
                tri = [(cx, cy, z), (ax, ay, z), (bx, by, z)]
                if rev:
                    tri = tri[::-1]
                acc.quad(tri[0], tri[1], tri[2], tri[2])


def _wheel(parent, at, r, side, burnt):
    """A tyre (its tread and shoulders), a five-spoke rim with the brake behind; burned: the rim alone."""
    x, y, z = at
    rubber = M({"color": [0.022, 0.022, 0.024], "rough": 0.75, "noise": 0.2, "noise_scale": 30.0, "grime": 1.3, "bevel": 0.0})
    alloy = M({"color": [0.5, 0.51, 0.53], "rough": 0.3, "metal": 1.0, "grime": 1.2, "bevel": 0.0}) if not burnt else \
        M({"ph": "rusty_metal_02", "tint": [0.45, 0.4, 0.35], "rough": 0.85, "bevel": 0.0})
    dark = M({"color": [0.03, 0.03, 0.03], "rough": 0.6, "bevel": 0.0})
    rr = r * 0.62
    if not burnt:
        tyre = kit.lathe(parent, "tyre", [(rr, -0.1), (r * 0.94, -0.105), (r, -0.07), (r, 0.07), (r * 0.94, 0.105), (rr, 0.1)], rubber, at=(0, 0, 0), segments=28)
        tyre.rotation_euler[0] = math.radians(90)
        tyre.location = g2b((x, y, z))
    disc = kit.lathe(parent, "brake", [(0.0, -0.01), (rr * 0.8, -0.01), (rr * 0.8, 0.01), (0.0, 0.01)], dark, at=(0, 0, 0), segments=16)
    disc.rotation_euler[0] = math.radians(90)
    disc.location = g2b((x, y if not burnt else rr, z - side * 0.02))
    yy = y if not burnt else rr + 0.005
    rim = kit.lathe(parent, "rim", [(rr * 0.98, -0.085), (rr, -0.06), (rr * 0.98, 0.06), (rr * 0.8, 0.075), (rr * 0.78, 0.07)], alloy, at=(0, 0, 0), segments=24)
    rim.rotation_euler[0] = math.radians(90)
    rim.location = g2b((x, yy, z))
    hub = kit.lathe(parent, "hub", [(0.0, 0.07), (0.07, 0.07), (0.08, 0.05), (0.08, 0.0)], alloy, at=(0, 0, 0), segments=12)
    hub.rotation_euler[0] = math.radians(90 if side > 0 else -90)
    hub.location = g2b((x, yy, z))
    spokes = Acc()
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        ca, sa_ = math.cos(a), math.sin(a)
        w0, w1 = 0.045, 0.03
        p0 = (x + ca * 0.07, yy + sa_ * 0.07)
        p1 = (x + ca * rr * 0.8, yy + sa_ * rr * 0.8)
        nx, ny = -sa_, ca
        zf = z + side * 0.06
        spokes.quad((p0[0] - nx * w0, p0[1] - ny * w0, zf), (p0[0] + nx * w0, p0[1] + ny * w0, zf),
                    (p1[0] + nx * w1, p1[1] + ny * w1, zf), (p1[0] - nx * w1, p1[1] - ny * w1, zf))
    spokes.build("spokes", alloy, parent, smooth=False)


# ── The tram ─────────────────────────────────────────────────────────────────────────────────
def _tram_profile(hw, h, y0=0.3):
    """A tram's section (z across, y up): the skirt, the side's slight turn under the windows, the
    window band, the tumblehome above it, the roof's rounded edge. 20 points, as _profile."""
    right = [(hw * 0.92, y0), (hw, y0 + 0.12), (hw, 0.62), (hw, 0.98), (hw, 1.06), (hw * 0.985, 2.36),
             (hw * 0.955, 2.56), (hw * 0.86, h - 0.07), (hw * 0.55, h)]
    return [(0.0, y0 - 0.01)] + right + [(0.0, h + 0.01)] + [(-z, y) for z, y in reversed(right)]


def bus(root, p, w, h, d):
    """A city bus (one body, or "bendy": two and the bellows): the tram's body on wheels in cut arches,
    white over grey, a tall windscreen, its saloon lit, the doors, the destination display saying
    where everyone was sent ("board")."""
    q = dict(p)
    q.setdefault("board", "EVACUATIE")
    return tram(root, q, w, h, d, as_bus=True)


def tram(root, p, w, h, d, as_bus=False):
    """A low-floor city tram in three sections, length along local x: white, a blue skirt, a band of
    glass with dark pillars and doors, a sloped nose with its windscreen at each end, the roof's
    equipment, a pantograph; the saloon inside (seats, poles, its lights lit or out). "derail": each
    section turned ("yaw"), tipped ("roll"), lifted ("lift") off the one before (city.py's chain);
    "dark": sections whose lights are out; "smashed": sections whose windows are gone."""
    import city
    white = M({"color": [0.78, 0.79, 0.8], "rough": 0.34, "coat": 0.8, "grime": 1.2, "bevel": 0.0, "streaks": 0.25})
    blue = M({"color": [0.04, 0.1, 0.32], "rough": 0.35, "coat": 0.6, "grime": 1.2, "bevel": 0.0, "streaks": 0.25})
    glass = M({"color": [0.012, 0.016, 0.02], "rough": 0.04, "metal": 0.85, "grime": 0.6, "bevel": 0.0})
    dark = M({"color": [0.02, 0.02, 0.022], "rough": 0.45, "grime": 1.0, "bevel": 0.0})
    door = M({"color": [0.05, 0.06, 0.07], "rough": 0.35, "grime": 1.2, "bevel": 0.0})
    hole = _hole()
    inside = city.emit((1.0, 0.86, 0.68), p.get("inside", 0.12), "tram_inside2_%d" % int(p.get("inside", 0.12) * 100))
    unlit = M({"color": [0.03, 0.028, 0.026], "rough": 0.7})
    seat = M({"color": [0.05, 0.08, 0.2], "rough": 0.8, "noise": 0.15, "grime": 1.0})
    pole = M({"color": [0.85, 0.65, 0.05], "rough": 0.3, "metal": 0.4})
    strip = city.emit((1.0, 0.95, 0.85), 6.0, "tram_strip")
    n, gap = (2 if (w > 14 or p.get("bendy")) else 1, 0.5) if as_bus else (3, 0.25)
    seg = (w - gap * (n - 1)) / n
    if as_bus:   # white over a grey skirt, and lit the cool white of a bus
        blue = M({"color": [0.12, 0.13, 0.15], "rough": 0.4, "coat": 0.5, "grime": 1.2, "bevel": 0.0, "streaks": 0.25})
        inside = builders.emissive("bus_inside2", (0.95, 0.97, 1.0), 0.1)
        strip = builders.emissive("bus_strip2", (0.95, 0.97, 1.0), 5.0)
    der = p.get("derail", {})
    at = lambda key, i: (der.get(key) or [0.0] * n)[i] if i < len(der.get(key) or []) else 0.0
    dark_secs, smashed = set(p.get("dark", [])), set(p.get("smashed", []))
    cx, cz, joint, centres = -w / 2 + seg / 2, 0.0, None, []
    for i in range(n):
        a = math.radians(at("yaw", i))
        if joint is not None:
            cx, cz = joint[0] + math.cos(a) * (gap / 2 + seg / 2), joint[1] - math.sin(a) * (gap / 2 + seg / 2)
        centres.append((cx, cz, a))
        joint = (cx + math.cos(a) * (seg / 2 + gap / 2), cz - math.sin(a) * (seg / 2 + gap / 2))
    hw = d / 2
    for i in range(n):
        cx, cz, a = centres[i]
        sr = builders.empty_at("tram_section", (0.0, 0.0, 0.0), 0.0)
        sr.parent = root
        sr.location = g2b((cx, at("lift", i), cz))
        sr.rotation_euler = (math.radians(at("roll", i)), math.radians(-at("pitch", i)), a)
        lit = i not in dark_secs
        broken = i in smashed
        nose_b, nose_f = i == 0, i == n - 1   # (a cab at the section's back end, or its front)
        # The stations along the section: the nose's slope at a cab end, straight between.
        xs = [-seg / 2 + seg * k / 40 for k in range(41)]
        stations, kinds = [], []
        for x in xs:
            k = 1.0
            to_end = min(x + seg / 2 if nose_b else 9.0, seg / 2 - x if nose_f else 9.0)
            if to_end < 0.75:   # the nose: narrower, the roof sloping down to the windscreen
                u = to_end / 0.75
                k = 0.86 + 0.14 * math.sqrt(u)
                hh = h - 0.28 * (1 - u) ** 2
            else:
                hh = h
            stations.append((x, _tram_profile(hw * k, hh)))
            kinds.append(to_end)
        door_x = [x0 for x0 in (-seg * 0.22, seg * 0.26)]
        pillars = [x for x in xs if abs((x + seg / 2) % 1.3) < 0.07]

        def face_mat(fi, kk, xs=xs, kinds=kinds, door_x=door_x, broken=broken):
            if fi < 0:
                return 2   # the ends: dark
            xm = (xs[fi] + xs[fi + 1]) / 2
            end = (kinds[fi] + kinds[fi + 1]) / 2
            band = kk in (5, 13)          # the window band (points 5 to 6, both sides)
            above = kk in (6, 7, 8, 9, 10, 11, 12)
            if end < 0.75 and (band or (above and kk in (7, 8, 9, 10, 11, 12) and end < 0.55)):
                return 1 if not broken else 4   # the windscreen, wrapped round the nose
            if any(abs(xm - dx) < 0.66 for dx in door_x) and kk in (1, 2, 3, 4, 5, 13, 14, 15, 16, 17):
                return (1 if not broken else 4) if kk in (5, 13) else 3   # a door: glass above, its dark leaf below
            if band:
                if any(abs(xm - px) < 0.05 for px in pillars):
                    return 2
                return 1 if not broken else 4
            if kk in (1, 2, 17, 18, 0, 19):
                return 5   # the skirt: blue
            return 0
        def mat_ends(fi, kk, fm=face_mat):
            return 0 if fi < 0 else fm(fi, kk)   # (the section's ends: white, the cab's glass laid over below)
        loft("tram_body", sr, stations, [white, glass, dark, door, hole, blue], mat_ends, subd=2,
             creases={4: 0.6, 15: 0.6, 5: 0.6, 14: 0.6, 7: 0.5, 12: 0.5, 2: 0.6, 17: 0.6}, ends=(-0.06, -0.06))
        if i < n - 1:   # the bellows to the next section
            lbox(sr, "tram_bellows", (seg / 2, 0.38, -hw + 0.14), (seg / 2 + gap + 0.04, h - 0.12, hw - 0.14), dark)
        for end, sx in ((nose_b, -1), (nose_f, 1)):   # a cab's face: the wrapped windscreen, the dark bumper under it
            if not end:
                continue
            if as_bus and sx < 0:   # a bus's back: its engine's grille, the lights
                xe = sx * (seg / 2 + 0.065)
                lbox(sr, "bus_grille", (xe - 0.02, 0.5, -hw + 0.25), (xe + 0.04, 1.3, hw - 0.25), dark)
                continue
            xe = sx * (seg / 2 + 0.115)   # (in front of the body's flat end)
            ws = Acc()
            segs = 10
            top = h - (0.32 if as_bus else 0.5)
            for q in range(segs):   # across the front, curving back a little at its corners
                za, zb = -hw * 0.9 + 1.8 * hw * q / segs, -hw * 0.9 + 1.8 * hw * (q + 1) / segs
                ba, bb = 0.04 * (za / hw) ** 2, 0.04 * (zb / hw) ** 2
                ws.quad((xe - sx * ba, 0.98 if as_bus else 1.08, za), (xe - sx * bb, 0.98 if as_bus else 1.08, zb), (xe - sx * bb, top, zb), (xe - sx * ba, top, za))
            ws.build("tram_windscreen", glass if not broken else hole, sr, smooth=True)
            lbox(sr, "tram_bumper", (xe - 0.06 if sx > 0 else xe - 0.02, 0.3, -hw + 0.1), (xe + 0.02 if sx > 0 else xe + 0.06, 0.92, hw - 0.1), dark)
        # The saloon: the floor, rows of seats, grab poles, the ceiling's lights (lit or out).
        lbox(sr, "tram_floor", (-seg / 2 + 0.3, 0.36, -hw + 0.12), (seg / 2 - 0.3, 0.4, hw - 0.12), dark)
        lbox(sr, "tram_ceiling", (-seg / 2 + 0.4, 2.62, -hw + 0.2), (seg / 2 - 0.4, 2.66, hw - 0.2), inside if lit else unlit)
        lbox(sr, "tram_strip", (-seg / 2 + 0.5, 2.58, -0.12), (seg / 2 - 0.5, 2.62, 0.12), strip if lit else dark)
        for k in range(int((seg - 1.4) / 0.85)):
            xx = -seg / 2 + 0.9 + k * 0.85
            if any(abs(xx - dx) < 0.8 for dx in door_x):
                continue
            for sz in (-1, 1):
                kit.soft(sr, "seat", (xx, 0.68, sz * 0.62), (0.45, 0.12, 0.46), seat, 0.04, 2)
                kit.soft(sr, "seat_back", (xx - 0.2, 1.0, sz * 0.62), (0.08, 0.6, 0.46), seat, 0.03, 2)
        pa = Acc()
        for dx in door_x:
            for sz in (-1, 1):
                pa.rod((dx, 0.4, sz * 0.45), (dx, 2.6, sz * 0.45), 0.018, 0.018, 6)
        pa.build("tram_poles_inside", pole, sr)
        if lit:   # its light, through the glass
            ld = bpy.data.lights.new("tram_glow", "AREA")
            ld.shape, ld.size, ld.size_y = "RECTANGLE", seg * 0.8, d * 0.6
            ld.energy, ld.color = p.get("power", 300.0) / n, (1.0, 0.92, 0.8)
            ob = bpy.data.objects.new("tram_glow", ld)
            bpy.context.scene.collection.objects.link(ob)
            ob.parent = sr
            ob.location = g2b((0.0, 2.5, 0.0))
            street.hide_panel(ob)
        # Under it: the bogies (a bus: wheels in arches cut from the skirt); on it: the roof's equipment,
        # the pantograph on a tram's middle section.
        if as_bus:
            axles = ([seg * 0.32] if nose_f else []) + [-seg * 0.18] if n > 1 else [seg * 0.3, -seg * 0.22]
            if n > 1 and nose_b:
                axles = [-seg * 0.2]
            cut, liner = Acc(), Acc()
            for ax in axles:
                _cyl(cut, (ax, 0.52, 0.0), 0.56, d + 0.6, 24)
                _cyl(liner, (ax, 0.52, 0.0), 0.55, d - 0.14, 20, open_ends=True)
            cutter = cut.build("arch_cutter", dark, sr, smooth=False)
            cutter.hide_render = True
            cutter.display_type = "WIRE"
            body_ob = [o for o in sr.children if o.name.startswith("tram_body")][-1]
            bo = body_ob.modifiers.new("arches", "BOOLEAN")
            bo.operation, bo.solver, bo.object = "DIFFERENCE", "EXACT", cutter
            liner.build("arch_liner", dark, sr, smooth=True)
            for ax in axles:
                for sz in (-1, 1):
                    _wheel(sr, (ax, 0.5, sz * (hw - 0.16)), 0.5, sz, False)
        else:
            for bx in (-seg * 0.3, seg * 0.3):
                lbox(sr, "bogie", (bx - 0.9, 0.05, -hw + 0.3), (bx + 0.9, 0.32, hw - 0.3), dark)
        kit.soft(sr, "roof_unit", (seg * (0.1 if i == 1 else -0.15), h + 0.14, 0.0), (min(3.2, seg * 0.45), 0.28, d * 0.62),
                 M({"color": [0.6, 0.61, 0.62], "rough": 0.5, "metal": 0.3, "grime": 1.4}), 0.06, 2)
        if i == 1 and not as_bus:
            arm = Acc()
            up = 1.0 if p.get("pantograph", True) else 0.3
            arm.rod((-0.6, h + 0.12, 0.0), (0.0, h + 0.12 + up * 0.55, 0.0), 0.025, 0.02, 5)
            arm.rod((0.0, h + 0.12 + up * 0.55, 0.0), (0.45, h + 0.12 + up, 0.0), 0.02, 0.02, 5)
            arm.rod((0.45, h + 0.12 + up, -0.6), (0.45, h + 0.12 + up, 0.6), 0.025, 0.025, 4)
            arm.build("pantograph", M({"color": [0.5, 0.5, 0.52], "rough": 0.35, "metal": 0.9}), sr)
        for end, sx in ((nose_b, -1), (nose_f, 1)):   # the cab's lights and its destination board
            if not end:
                continue
            xe = sx * (seg / 2 - 0.03)
            lbox(sr, "dest_board", (xe - 0.04, h - 0.42, -hw * 0.5), (xe + 0.04, h - 0.24, hw * 0.5), dark)
            if lit and p.get("board"):
                text(sr, p["board"], (xe + sx * 0.05, h - 0.33, 0.0), 0.12, city.emit((1.0, 0.6, 0.1), 8.0, "tram_board"),
                     font="DejaVuSansMono-Bold.ttf", depth=0.0, yaw=90.0 * sx)
            for sz in (-1, 1):
                kit.soft(sr, "headlight", (xe, 0.72, sz * (hw - 0.32)), (0.06, 0.12, 0.26),
                         city.emit((1.0, 0.95, 0.85), 30.0, "tram_head") if lit else dark, 0.03, 2)


def army_truck(root, p, w, h, d):
    """An army truck along local x (front +x): a squared cab (lofted, its edges held), a ladder chassis,
    a cargo bed under a canvas tilt over its hoops, big tyres (twin at the back) in their guards, a
    spare wheel and jerrycans, olive drab worn through to the steel; the tailgate down."""
    olive = M({"color": [0.12, 0.135, 0.08], "rough": 0.62, "grime": 1.4, "bevel": 0.0, "streaks": 0.5})
    canvas = M({"ph": "rough_linen", "mono": 1.5, "tint": [0.3, 0.31, 0.2], "scale": 0.7, "grime": 1.4})
    dark = M({"color": [0.02, 0.02, 0.02], "rough": 0.6, "bevel": 0.0})
    glass = M({"color": [0.012, 0.016, 0.02], "rough": 0.05, "metal": 0.8, "bevel": 0.0})
    cab_l = 2.1
    x_cab = w / 2 - cab_l / 2
    # the cab: upright, a short nose, a flat windscreen, square shoulders
    keys = [(0.0, dict(top=0.97, belt=0.55, hw=0.94, rh=0.9, cab=1.0)), (0.08, dict(top=1.0, belt=0.55, hw=1.0, rh=0.95, cab=1.0)),
            (0.55, dict(top=1.0, belt=0.55, hw=1.0, rh=0.95, cab=1.0)), (0.62, dict(top=0.94, belt=0.55, hw=1.0, rh=0.95, cab=1.0)),
            (0.68, dict(top=0.62, belt=0.52, hw=0.98, rh=0.92, cab=0.0)), (1.0, dict(top=0.55, belt=0.48, hw=0.92, rh=0.86, cab=0.0))]
    ts = [k / 16 for k in range(17)]
    stations = []
    ch = h * 0.98
    for t in ts:
        k = _lerp_keys(keys, t)
        stations.append((x_cab - cab_l / 2 + t * cab_l, _profile(d / 2 * k["hw"], 0.62, ch * k["belt"], ch * k["top"], d / 2 * k["rh"], ch * k["belt"] + 0.03)))

    def cab_mat(i, k):
        if i < 0:
            return 0
        tm = (ts[i] + ts[i + 1]) / 2
        if k in SIDE_GLASS and 0.12 < tm < 0.6:
            return 1
        if k in TOP and 0.55 < tm < 0.66:
            return 1
        return 0
    loft("truck_cab", root, stations, [olive, glass], cab_mat, creases={5: 0.9, 14: 0.9, 6: 0.9, 13: 0.9, 8: 0.85, 11: 0.85}, ends=(-0.04, 0.05))
    # chassis, bed, the tilt over its hoops
    lbox(root, "chassis", (-w / 2 + 0.3, 0.55, -d * 0.32), (w / 2 - 0.2, 0.78, d * 0.32), dark)
    bed0, bed1 = -w / 2 + 0.05, w / 2 - cab_l - 0.12
    lbox(root, "bed_floor", (bed0, 0.85, -d / 2), (bed1, 0.98, d / 2), olive)
    for sz in (-1, 1):
        lbox(root, "bed_side", (bed0, 0.98, sz * d / 2 - 0.04), (bed1, 1.45, sz * d / 2 + 0.02), olive)
    tilt = []
    for k in range(9):
        x = bed0 + (bed1 - bed0) * k / 8
        sag = 0.035 * math.sin(k * 1.7)
        loop = [(0.0, 1.42)] + [(d / 2 * 1.01, 1.42), (d / 2 * 1.02, 2.1), (d / 2 * 0.98, h - 0.25 - sag), (d / 2 * 0.75, h - 0.04 - sag),
                                (d / 2 * 0.35, h - sag)] + [(0.0, h + 0.01 - sag)] + [(-d / 2 * 0.35, h - sag), (-d / 2 * 0.75, h - 0.04 - sag),
                                (-d / 2 * 0.98, h - 0.25 - sag), (-d / 2 * 1.02, 2.1), (-d / 2 * 1.01, 1.42)]
        tilt.append((x, loop))
    loft("tilt", root, tilt, [canvas], lambda i, k: 0, subd=2, ends=(-0.03, -0.03))
    lbox(root, "tailgate", (bed0 - 0.45, 0.62, -d / 2 + 0.05), (bed0 - 0.02, 0.7, d / 2 - 0.05), olive)
    # wheels: single at the front, twin at the back, in their guards
    r = 0.52
    for x, twin in ((x_cab + 0.25, False), (bed0 + (bed1 - bed0) * 0.35, True)):
        for sz in (-1, 1):
            _wheel(root, (x, r, sz * (d / 2 - 0.12)), r, sz, False)
            if twin:
                _wheel(root, (x, r, sz * (d / 2 - 0.42)), r, sz, False)
            kit.soft(root, "guard", (x, r + 0.58, sz * (d / 2 - 0.15)), (1.25, 0.08, 0.5), olive, 0.03, 2)
    kit.soft(root, "spare", (bed1 + 0.06, 1.1, d / 2 - 0.25), (0.2, 0.9, 0.9), dark, 0.2, 2)
    for k in range(3):
        kit.soft(root, "jerrycan", (bed1 - 0.25 - k * 0.3, 1.25, -d / 2 - 0.12), (0.18, 0.46, 0.34), M({"color": [0.15, 0.17, 0.1], "rough": 0.6}), 0.02, 2)
    head = builders.emissive("truck_head", (1.0, 0.95, 0.85), 10.0)
    for sz in (-1, 1):
        kit.soft(root, "headlight", (w / 2 - 0.02, 1.05, sz * (d / 2 - 0.3)), (0.1, 0.2, 0.2), head, 0.05, 2)
    if p.get("door_open"):
        sz = 1 if p["door_open"] == "left" else -1
        hinge = builders.empty_at("cab_door", (0.0, 0.0, 0.0), 0.0)
        hinge.parent = root
        hinge.location = g2b((x_cab + 0.45, 0.0, sz * d / 2))
        hinge.rotation_euler[2] = math.radians(-60 * sz)
        kit.soft(hinge, "cab_door", (-0.55, 1.45, sz * 0.03), (1.1, 1.2, 0.07), olive, 0.03, 2)


def _car_or_truck(root, p, w, h, d):
    if p.get("livery") == "army" and h > 2.5:
        return army_truck(root, p, w, h, d)
    return car(root, p, w, h, d)


kit.PROPS.update({"vehicle": _car_or_truck, "tram": tram, "bus": bus})
