# damned_waters/tools/blender/builders.py
# Purpose: the Blender-side "set builder". Turns RoomSpec data into geometry,
# procedural materials and a small kit of Dutch canal-house props. Everything
# is built with bpy.data (no bpy.ops), so it is fast and context-free.
#
# Conventions (match the Godot side exactly):
#   * Spec coordinates are Godot metres (Y up, north = -Z). g2b() converts.
#   * Prop "pos" = bottom-centre of its footprint; "size" = [w, h, d] local.
#   * Prop front faces local +Z at yaw 0 (glTF/Godot model convention).
import math
import random

import bpy

import surfaces
from roomspec import g2b, wall_segments

WALL_T = 0.3  # wall thickness, grows outward from the room bounds


# ───────────────────────────── mesh primitives ──────────────────────────────
_BOX_FACES = [  # CCW from outside; corner index = ix*4 + iy*2 + iz
    (0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
_FACE_UV_AXES = [(1, 2), (1, 2), (0, 2), (0, 2), (0, 1), (0, 1)]


def _link(ob, parent=None):
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def _mesh_object(name, verts, faces, face_uvs, mat, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = face_uvs[poly.index][k]
    me.materials.append(mat)
    return _link(bpy.data.objects.new(name, me), parent)


def box_b(name, center_b, size_b, mat, parent=None, rot_b=(0.0, 0.0, 0.0), world_uv=True):
    """Axis box in Blender space. UVs are metre-scaled and, for unrotated boxes,
    offset by world position so textures flow seamlessly across segments."""
    sx, sy, sz = size_b
    verts = [((ix - .5) * sx, (iy - .5) * sy, (iz - .5) * sz)
             for ix in (0, 1) for iy in (0, 1) for iz in (0, 1)]
    off = center_b if (world_uv and parent is None and rot_b == (0.0, 0.0, 0.0)) else (0, 0, 0)
    uvs = []
    for f, (a, b) in zip(_BOX_FACES, _FACE_UV_AXES):
        uvs.append([(verts[i][a] + off[a], verts[i][b] + off[b]) for i in f])
    ob = _mesh_object(name, verts, _BOX_FACES, uvs, mat, parent)
    ob.location = center_b
    ob.rotation_euler = rot_b
    return ob


def box_aabb(name, gmin, gmax, mat):
    """World AABB given in Godot coordinates."""
    c = [(a + b) / 2 for a, b in zip(gmin, gmax)]
    s = [b - a for a, b in zip(gmin, gmax)]
    return box_b(name, g2b(c), (s[0], s[2], s[1]), mat)


def frustum_b(name, center_b, r_bottom, r_top, height, mat, parent=None, segments=20, rot_b=(0, 0, 0)):
    """Cylinder / cone section along local Z (Blender up), centred at center_b."""
    verts, faces, uvs = [], [], []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        verts.append((r_bottom * math.cos(a), r_bottom * math.sin(a), -height / 2))
        verts.append((r_top * math.cos(a), r_top * math.sin(a), height / 2))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
        u0, u1 = i / segments * 2 * math.pi * r_bottom, (i + 1) / segments * 2 * math.pi * r_bottom
        uvs.append([(u0, 0), (u1, 0), (u1, height), (u0, height)])
    faces.append(tuple(2 * i for i in reversed(range(segments))))
    uvs.append([(verts[2 * i][0], verts[2 * i][1]) for i in reversed(range(segments))])
    faces.append(tuple(2 * i + 1 for i in range(segments)))
    uvs.append([(verts[2 * i + 1][0], verts[2 * i + 1][1]) for i in range(segments)])
    ob = _mesh_object(name, verts, faces, uvs, mat, parent)
    ob.location = center_b
    ob.rotation_euler = rot_b
    return ob


def empty_at(name, pos_g, yaw_deg=0.0, tip_deg=0.0):
    ob = _link(bpy.data.objects.new(name, None))
    ob.location = g2b(pos_g)
    ob.rotation_euler = (0.0, math.radians(tip_deg), math.radians(yaw_deg))
    return ob


def part(parent, name, center_g, size_g, mat, rot_x_deg=0.0):
    """Child box in the prop's local Godot frame (x right, y up, z front)."""
    w, h, d = size_g
    return box_b(name, g2b(center_g), (w, d, h), mat, parent,
                 rot_b=(math.radians(rot_x_deg), 0.0, 0.0), world_uv=False)


def cyl(parent, name, center_g, radius, height, mat, r_top=None, horizontal=False):
    rot = (math.radians(90), 0, 0) if horizontal else (0, 0, 0)
    return frustum_b(name, g2b(center_g), radius, radius if r_top is None else r_top,
                     height, mat, parent, rot_b=rot)


# ───────────────────────────── materials ────────────────────────────────────
_MATS = {}


def _new_mat(name):
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def _uv(nt, scale=1.0):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    return mp.outputs["Vector"]


def _ramp(nt, fac_socket, c0, c1, p0=0.0, p1=1.0):
    r = nt.nodes.new("ShaderNodeValToRGB")
    e = r.color_ramp.elements
    e[0].position, e[0].color = p0, (*c0, 1)
    e[1].position, e[1].color = p1, (*c1, 1)
    nt.links.new(fac_socket, r.inputs["Fac"])
    return r.outputs["Color"]


def _noise(nt, vec, scale, detail=4.0, rough=0.55):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(vec, n.inputs["Vector"])
    return n.outputs["Fac"]


def _bsdf(nt, out, color=None, rough=0.5, metal=0.0, color_socket=None, bump_socket=None, bump=0.1):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if color_socket is not None:
        nt.links.new(color_socket, b.inputs["Base Color"])
    elif color is not None:
        b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if bump_socket is not None:
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        nt.links.new(bump_socket, bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return b


def _brick(nt, vec, c1, c2, mortar, width, row, mortar_size, offset=0.5, bias=0.0):
    t = nt.nodes.new("ShaderNodeTexBrick")
    t.offset = offset
    t.inputs["Color1"].default_value = (*c1, 1)
    t.inputs["Color2"].default_value = (*c2, 1)
    t.inputs["Mortar"].default_value = (*mortar, 1)
    t.inputs["Scale"].default_value = 1.0
    t.inputs["Mortar Size"].default_value = mortar_size
    t.inputs["Brick Width"].default_value = width
    t.inputs["Row Height"].default_value = row
    t.inputs["Bias"].default_value = bias
    nt.links.new(vec, t.inputs["Vector"])
    return t


def material(key):
    """Material library keyed by the names used in RoomSpec JSON. A Poly Haven reference
    ("ph:<id>" or {"ph": ...}) or a painted surface ({"color": ...}) goes to surfaces.py."""
    if surfaces.is_ref(key):
        ck = surfaces.cache_key(key)
        if ck not in _MATS:
            m, nt, out = _new_mat(ck[:60])
            surfaces.build(nt, out, key)
            _MATS[ck] = m
        return _MATS[ck]
    if key in _MATS:
        return _MATS[key]
    m, nt, out = _new_mat(key)
    if key == "plaster":
        v = _uv(nt)
        n = _noise(nt, v, 2.5, 6)
        _bsdf(nt, out, color_socket=_ramp(nt, n, (0.22, 0.20, 0.18), (0.42, 0.40, 0.36), 0.35, 0.7),
              rough=0.92, bump_socket=n, bump=0.08)
    elif key == "damask_green":
        v = _uv(nt, 5.0)
        mg = nt.nodes.new("ShaderNodeTexMagic")
        mg.turbulence_depth = 3
        nt.links.new(v, mg.inputs["Vector"])
        _bsdf(nt, out, color_socket=_ramp(nt, mg.outputs["Fac"], (0.020, 0.045, 0.032), (0.05, 0.10, 0.07)), rough=0.6)
    elif key == "delft_tiles":
        t = _brick(nt, _uv(nt), (0.72, 0.72, 0.68), (0.55, 0.62, 0.80), (0.25, 0.25, 0.23), 0.13, 0.13, 0.004, offset=0.0)
        _bsdf(nt, out, color_socket=t.outputs["Color"], rough=0.12, bump_socket=t.outputs["Fac"], bump=0.2)
    elif key == "marble_checker":
        v = _uv(nt)
        c = nt.nodes.new("ShaderNodeTexChecker")
        c.inputs["Scale"].default_value = 2.5
        c.inputs["Color1"].default_value = (0.55, 0.54, 0.50, 1)
        c.inputs["Color2"].default_value = (0.012, 0.012, 0.014, 1)
        nt.links.new(v, c.inputs["Vector"])
        _bsdf(nt, out, color_socket=c.outputs["Color"], rough=0.1)
    elif key == "oak_planks":
        t = _brick(nt, _uv(nt), (0.16, 0.085, 0.04), (0.11, 0.06, 0.03), (0.015, 0.008, 0.004), 1.8, 0.16, 0.004)
        _bsdf(nt, out, color_socket=t.outputs["Color"], rough=0.42, bump_socket=t.outputs["Fac"], bump=0.15)
    elif key == "dark_wood":
        v = _uv(nt)
        n = _noise(nt, v, 9.0, 3)
        _bsdf(nt, out, color_socket=_ramp(nt, n, (0.035, 0.018, 0.009), (0.09, 0.045, 0.022)), rough=0.38)
    elif key == "brick":
        t = _brick(nt, _uv(nt), (0.19, 0.075, 0.045), (0.12, 0.05, 0.03), (0.10, 0.095, 0.085), 0.22, 0.075, 0.012)
        _bsdf(nt, out, color_socket=t.outputs["Color"], rough=0.75, bump_socket=t.outputs["Fac"], bump=0.35)
    elif key == "stone_floor":
        t = _brick(nt, _uv(nt), (0.16, 0.16, 0.15), (0.11, 0.115, 0.11), (0.04, 0.04, 0.04), 0.6, 0.45, 0.01)
        _bsdf(nt, out, color_socket=t.outputs["Color"], rough=0.6)
    elif key == "water":
        n = _noise(nt, _uv(nt), 3.0, 2)
        b = _bsdf(nt, out, color=(0.01, 0.018, 0.012), rough=0.03, bump_socket=n, bump=0.04)
        b.inputs["IOR"].default_value = 1.33
    elif key == "glass":
        g = nt.nodes.new("ShaderNodeBsdfPrincipled")
        g.inputs["Base Color"].default_value = (0.6, 0.65, 0.7, 1)
        g.inputs["Roughness"].default_value = 0.05
        g.inputs["Transmission Weight"].default_value = 1.0
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        lp = nt.nodes.new("ShaderNodeLightPath")
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Shadow Ray"], mx.inputs[0])
        nt.links.new(g.outputs[0], mx.inputs[1])
        nt.links.new(tr.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    elif key == "rug":
        mg = nt.nodes.new("ShaderNodeTexMagic")
        nt.links.new(_uv(nt, 3.0), mg.inputs["Vector"])
        _bsdf(nt, out, color_socket=_ramp(nt, mg.outputs["Fac"], (0.08, 0.01, 0.01), (0.25, 0.08, 0.03)), rough=0.95)
    elif key == "painting":
        n = _noise(nt, _uv(nt, 2.0), 3.0, 8, 0.7)
        _bsdf(nt, out, color_socket=_ramp(nt, n, (0.01, 0.008, 0.005), (0.22, 0.14, 0.06), 0.4, 0.75), rough=0.35)
    else:
        flat = {  # key: (color, roughness, metallic)
            "brass": ((0.55, 0.40, 0.16), 0.3, 1.0), "iron": ((0.05, 0.05, 0.05), 0.55, 1.0),
            "velvet": ((0.10, 0.012, 0.018), 0.95, 0.0), "paper": ((0.62, 0.60, 0.52), 0.9, 0.0),
            "soot": ((0.008, 0.008, 0.008), 1.0, 0.0), "marble_white": ((0.6, 0.58, 0.55), 0.2, 0.0),
            "cream": ((0.7, 0.66, 0.55), 0.4, 0.0), "coat": ((0.02, 0.02, 0.025), 0.9, 0.0),
            "bottle": ((0.01, 0.04, 0.015), 0.1, 0.0), "wax": ((0.7, 0.66, 0.55), 0.6, 0.0),
            "lampshade": ((0.03, 0.12, 0.05), 0.2, 0.0), "facade": ((0.05, 0.035, 0.03), 0.9, 0.0),
            "typewriter": ((0.015, 0.015, 0.015), 0.35, 0.3), "plaster_raw": ((0.35, 0.33, 0.3), 0.95, 0.0),
        }.get(key, ((0.5, 0.0, 0.5), 0.5, 0.0))  # magenta = missing material, obvious on purpose
        _bsdf(nt, out, color=flat[0], rough=flat[1], metal=flat[2])
    _MATS[key] = m
    return m


def emissive(key, color, strength):
    k = f"emit_{key}"
    if k not in _MATS:
        m, nt, out = _new_mat(k)
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*color, 1)
        e.inputs["Strength"].default_value = strength
        nt.links.new(e.outputs[0], out.inputs["Surface"])
        _MATS[k] = m
    return _MATS[k]


def reset_material_cache():
    _MATS.clear()


# ───────────────────────────── room shell ───────────────────────────────────
def _wall_box(spec, side, u0, u1, v0, v1, d0, d1, mat, name):
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    if side == "north":
        gmin, gmax = (x0 + u0, v0, z0 - d1), (x0 + u1, v1, z0 - d0)
    elif side == "south":
        gmin, gmax = (x0 + u0, v0, z1 + d0), (x0 + u1, v1, z1 + d1)
    elif side == "west":
        gmin, gmax = (x0 - d1, v0, z0 + u0), (x0 - d0, v1, z0 + u1)
    else:
        gmin, gmax = (x1 + d0, v0, z0 + u0), (x1 + d1, v1, z0 + u1)
    return box_aabb(name, gmin, gmax, mat)


def _opening_span(op):
    bottom = op.get("sill", 0.0)
    return op["center"] - op["width"] / 2, op["center"] + op["width"] / 2, bottom, bottom + op["height"]


def build_shell(spec):
    """Floor, ceiling, beams, walls with openings, wainscot, doors, windows, gates."""
    mats = spec["materials"]
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    h, t = spec["height"], WALL_T
    box_aabb("floor", (x0 - t, -0.2, z0 - t), (x1 + t, 0.0, z1 + t), material(mats["floor"]))
    box_aabb("ceiling", (x0 - t, h, z0 - t), (x1 + t, h + 0.2, z1 + t), material(mats["ceiling"]))
    beams = spec.get("ceiling_beams")
    if beams:
        wood = material("dark_wood")
        if beams["axis"] == "x":
            z = z0 + beams["spacing"] / 2
            while z < z1:
                box_aabb("beam", (x0, h - 0.22, z - 0.09), (x1, h, z + 0.09), wood)
                z += beams["spacing"]
        else:
            x = x0 + beams["spacing"] / 2
            while x < x1:
                box_aabb("beam", (x - 0.09, h - 0.22, z0), (x + 0.09, h, z1), wood)
                x += beams["spacing"]

    wall_mat = material(mats["wall"])
    wain_key, wain_h = mats.get("wainscot", ""), mats.get("wainscot_height", 0.0)
    for side, wall in wall_segments(spec).items():
        (ax, az), (bx, bz) = wall["line"]
        length = abs(bx - ax) + abs(bz - az)
        ops = sorted(wall["openings"], key=lambda o: o["center"])
        # Solid spans between openings (full height), extended past corners.
        cursor = -t
        for op in ops:
            ou0, ou1, ov0, ov1 = _opening_span(op)
            if ou0 > cursor:
                _wall_box(spec, side, cursor, ou0, 0, h, 0, t, wall_mat, f"wall_{side}")
            _wall_box(spec, side, ou0, ou1, ov1, h, 0, t, wall_mat, f"lintel_{side}")
            if ov0 > 0:
                _wall_box(spec, side, ou0, ou1, 0, ov0, 0, t, wall_mat, f"sill_{side}")
            cursor = max(cursor, ou1)
            _build_opening(spec, side, op)
        if cursor < length + t:
            _wall_box(spec, side, cursor, length + t, 0, h, 0, t, wall_mat, f"wall_{side}")
        # Wainscot / skirting: thin layer on the interior face, skipping doorways.
        doors = [_opening_span(o) for o in ops if o["kind"] in ("door", "gate") or o.get("sill", 1.0) < 0.05]
        spans, c = [], 0.0
        for du0, du1, _, _ in sorted(doors):
            spans.append((c, du0))
            c = du1
        spans.append((c, length))
        for su0, su1 in spans:
            if su1 - su0 < 0.02:
                continue
            if wain_key and wain_h > 0:
                _wall_box(spec, side, su0, su1, 0, wain_h, -0.025, 0, material(wain_key), "wainscot")
                _wall_box(spec, side, su0, su1, wain_h - 0.03, wain_h + 0.03, -0.045, 0, material("dark_wood"), "rail")
            sk = mats.get("skirting", "dark_wood")
            if sk:
                _wall_box(spec, side, su0, su1, 0, mats.get("skirting_height", 0.14), -0.02, 0, material(sk), "skirting")


def _build_opening(spec, side, op):
    if op.get("arch"):   # round-headed, steel-framed (kit.py)
        import kit
        kit.arch_opening(spec, side, op)
        return
    u0, u1, v0, v1 = _opening_span(op)
    wood, dark = material("dark_wood"), material("soot")
    # Interior casing around every opening.
    for (a, b, c, d) in ((u0 - 0.08, u0, v0, v1 + 0.08), (u1, u1 + 0.08, v0, v1 + 0.08), (u0, u1, v1, v1 + 0.08)):
        _wall_box(spec, side, a, b, c, d, -0.03, 0.0, wood, "casing")
    if op["kind"] == "door":
        _wall_box(spec, side, u0, u1, v0, v1, 0.06, 0.11, wood, "door_leaf")
        w, hh = u1 - u0, v1 - v0
        for (pu, pv, pw, ph) in ((0.5, 0.72, 0.7, 0.4), (0.5, 0.28, 0.7, 0.36)):
            cu, cv = u0 + w * pu, v0 + hh * pv
            _wall_box(spec, side, cu - w * pw / 2, cu + w * pw / 2, cv - hh * ph / 2, cv + hh * ph / 2,
                      0.04, 0.06, wood, "door_panel")
        _wall_box(spec, side, u1 - 0.13, u1 - 0.08, v0 + 1.0, v0 + 1.06, 0.0, 0.06, material("brass"), "knob")
    elif op["kind"] == "window":
        _wall_box(spec, side, u0, u1, v0, v1, 0.14, 0.15, material("glass"), "glass")
        paint = material("cream")
        _wall_box(spec, side, (u0 + u1) / 2 - 0.03, (u0 + u1) / 2 + 0.03, v0, v1, 0.1, 0.19, paint, "mullion")
        for f in (0.33, 0.66):
            vv = v0 + (v1 - v0) * f
            _wall_box(spec, side, u0, u1, vv - 0.025, vv + 0.025, 0.1, 0.19, paint, "transom")
        _wall_box(spec, side, u0 - 0.05, u1 + 0.05, v0 - 0.04, v0, -0.12, 0.0, wood, "sill_board")
    elif op["kind"] == "gate":
        iron = material("iron")
        u = u0 + 0.06
        while u < u0 + (u1 - u0) * 0.4:
            _wall_box(spec, side, u - 0.015, u + 0.015, v0, v1, 0.1, 0.13, iron, "bar")
            u += 0.17
        _wall_box(spec, side, u0, u0 + (u1 - u0) * 0.42, v1 - 0.12, v1 - 0.08, 0.09, 0.14, iron, "bar_rail")
        _wall_box(spec, side, u0 - 0.1, u1 + 0.1, v1, v1 + 0.3, -0.05, 0.3, material("stone_floor"), "gate_arch")


def build_water(spec):
    w = spec.get("water")
    if not w:
        return
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    z_far = z0 - 9.0 if spec.get("exterior") == "north_canal" else z0
    box_aabb("water", (x0, w["y"] - 0.02, z_far), (x1, w["y"], z1), material("water"))


def build_exterior(spec, rng):
    """Cheap, atmospheric outside world visible through windows/gates."""
    ext = spec.get("exterior")
    if isinstance(ext, dict):   # the canal and the houses across it (kit.py)
        import kit
        kit.build_exterior(spec, rng)
        return
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    if ext == "south":
        box_aabb("canal", (x0 - 30, -1.4, z1 + 0.5), (x1 + 30, -1.38, z1 + 13), material("water"))
        box_aabb("quay", (x0 - 30, -1.4, z1 + 13), (x1 + 30, 0.0, z1 + 16), material("stone_floor"))
        x = x0 - 24
        while x < x1 + 24:
            w, hgt = rng.uniform(4.5, 6.5), rng.uniform(11, 15)
            zf = z1 + 16
            o = box_aabb("facade", (x, 0, zf), (x + w - 0.05, hgt, zf + 8), material("facade"))
            o.visible_shadow = False
            o2 = box_aabb("gable", (x + w * 0.25, hgt, zf), (x + w * 0.75, hgt + 2.2, zf + 8), material("facade"))
            o2.visible_shadow = False
            for fl in range(1, int(hgt // 3)):
                for k in range(3):
                    if rng.random() < 0.05:
                        wx = x + 0.8 + k * (w - 1.6) / 2
                        win = box_aabb("lit_window", (wx - 0.4, fl * 3 + 0.8, zf - 0.02), (wx + 0.4, fl * 3 + 2.4, zf),
                                       emissive("window", (1.0, 0.55, 0.25), 3.0))
                        win.visible_shadow = False
            x += w
    elif ext == "north_canal":
        box_aabb("tunnel_l", (x0 - 0.5, 0, z0 - 9), (x0 + 1.2, 2.2, z0), material("brick"))
        box_aabb("tunnel_r", (x1 - 1.2, 0, z0 - 9), (x1 + 0.5, 2.2, z0), material("brick"))
        box_aabb("tunnel_top", (x0 - 0.5, 1.9, z0 - 9), (x1 + 0.5, 2.3, z0), material("brick"))
        glow = box_aabb("canal_glow", (x0, 0, z0 - 9.2), (x1, 2.2, z0 - 9.0), emissive("canal", (0.2, 0.7, 0.55), 0.6))
        glow.visible_shadow = False


# ───────────────────────────── prop kit ─────────────────────────────────────
def build_prop(p, room_h):
    t = p["type"]
    import kit
    if t in kit.PROPS:   # the detailed kit: sofas, kasten, the marble mantel, models...
        return kit.build_prop(p, room_h)
    size = p.get("size", [0.45, 0.95, 0.45])
    w, h, d = size
    yaw, tip = p.get("yaw", 0.0), 0.0
    pos = list(p["pos"])
    if p.get("tipped"):  # lying on its side, centred on the footprint
        tip = 90.0
        cw, ch = 0.45, 0.95
        yr = math.radians(yaw)
        off = (-ch / 2, cw / 2)  # local x shift, lift
        pos = [pos[0] + off[0] * math.cos(yr), pos[1] + off[1], pos[2] - off[0] * math.sin(yr)]
        w, h, d = cw, ch, 0.45
    root = empty_at(f"prop_{t}", pos, yaw, tip)
    wood, dark = material("dark_wood"), material("soot")
    if t == "table":
        part(root, "top", (0, h - 0.02, 0), (w, 0.04, d), wood)
        part(root, "apron", (0, h - 0.1, 0), (w - 0.1, 0.12, d - 0.1), wood)
        for sx in (-1, 1):
            for sz in (-1, 1):
                part(root, "leg", (sx * (w / 2 - 0.06), (h - 0.04) / 2, sz * (d / 2 - 0.06)), (0.07, h - 0.04, 0.07), wood)
    elif t == "chair":
        part(root, "seat", (0, 0.46, 0), (w, 0.045, d), material("rug"))
        for sx in (-1, 1):
            for sz in (-1, 1):
                part(root, "leg", (sx * (w / 2 - 0.03), 0.22, sz * (d / 2 - 0.03)), (0.04, 0.44, 0.04), wood)
            part(root, "post", (sx * (w / 2 - 0.03), 0.72, -d / 2 + 0.03), (0.045, 0.5, 0.045), wood)
        part(root, "back", (0, 0.78, -d / 2 + 0.03), (w - 0.06, 0.3, 0.025), wood)
    elif t in ("cabinet", "side_table", "desk"):
        body_h = h - (0.2 if t == "cabinet" else 0.04)
        if t == "cabinet":
            part(root, "plinth", (0, 0.05, 0), (w + 0.04, 0.1, d + 0.04), wood)
            part(root, "body", (0, 0.1 + body_h / 2 - 0.05, 0), (w, body_h - 0.1, d), wood)
            part(root, "cornice", (0, h - 0.08, 0), (w + 0.12, 0.16, d + 0.1), wood)
            for sx in (-1, 1):
                part(root, "panel", (sx * w / 4, h * 0.46, d / 2 + 0.01), (w / 2 - 0.14, h * 0.62, 0.02), dark)
                part(root, "knob", (sx * 0.06, h * 0.46, d / 2 + 0.03), (0.03, 0.03, 0.03), material("brass"))
        else:
            part(root, "top", (0, h - 0.02, 0), (w, 0.04, d), wood)
            for sx in (-1, 1):
                for sz in (-1, 1):
                    part(root, "leg", (sx * (w / 2 - 0.04), (h - 0.04) / 2, sz * (d / 2 - 0.04)), (0.05, h - 0.04, 0.05), wood)
            part(root, "drawer", (0, h - 0.12, d / 2 - 0.02), (w - 0.1, 0.12, 0.03), wood)
            if t == "desk":
                part(root, "drawers", (w / 2 - 0.22, (h - 0.04) / 2, 0), (0.4, h - 0.04, d - 0.04), wood)
            if p.get("typewriter"):
                tw = material("typewriter")
                part(root, "tw_body", (-0.1, h + 0.06, 0.02), (0.38, 0.12, 0.3), tw)
                part(root, "tw_carriage", (-0.1, h + 0.14, -0.08), (0.46, 0.05, 0.07), tw)
                part(root, "tw_paper", (-0.1, h + 0.24, -0.1), (0.21, 0.18, 0.004), material("paper"))
                part(root, "lamp_base", (0.4, h + 0.015, -0.1), (0.14, 0.03, 0.1), material("brass"))
                part(root, "lamp_stem", (0.4, h + 0.17, -0.12), (0.02, 0.3, 0.02), material("brass"))
                part(root, "lamp_shade", (0.4, h + 0.34, -0.05), (0.3, 0.08, 0.13), material("lampshade"))
    elif t == "fireplace":
        stone = material("marble_white")
        part(root, "hearth", (0, 0.025, 0.1), (w + 0.2, 0.05, d + 0.3), stone)
        for sx in (-1, 1):
            part(root, "jamb", (sx * (w / 2 - 0.13), (h - 0.1) / 2, 0), (0.26, h - 0.1, d), stone)
        part(root, "lintel", (0, h - 0.28, 0), (w - 0.5, 0.36, d), stone)
        part(root, "mantel", (0, h - 0.04, 0.03), (w + 0.16, 0.08, d + 0.12), stone)
        part(root, "firebox", (0, (h - 0.46) / 2, -d / 2 + 0.03), (w - 0.5, h - 0.46, 0.05), dark)
        part(root, "embers", (0, 0.08, -0.05), (0.45, 0.05, 0.2), emissive("embers", (1.0, 0.25, 0.05), 4.0))
        part(root, "grate", (0, 0.15, 0.0), (0.6, 0.04, 0.25), material("iron"))
    elif t == "stairs":
        n = max(3, round(h / 0.225))
        run = d / n
        for i in range(n):
            top = (i + 1) * h / n
            zc = d / 2 - (i + 0.5) * run
            part(root, "step", (0, top / 2, zc), (w, top, run), wood)
            part(root, "nosing", (0, top - 0.015, zc + run / 2), (w + 0.02, 0.03, 0.04), wood)
        ang = math.degrees(math.atan2(h, d))
        L = math.hypot(h, d)
        part(root, "handrail", (-w / 2 + 0.03, h / 2 + 0.9, 0), (0.05, 0.05, L), wood, rot_x_deg=ang)
        part(root, "stringer", (-w / 2 - 0.02, h / 2, 0), (0.04, 0.3, L), wood, rot_x_deg=ang)
        for i in range(0, n, 2):
            top = (i + 1) * h / n
            part(root, "baluster", (-w / 2 + 0.03, top + 0.45, d / 2 - (i + 0.5) * run), (0.03, 0.9, 0.03), wood)
    elif t == "clock":
        part(root, "case", (0, (h - 0.35) / 2, 0), (w * 0.85, h - 0.35, d * 0.85), wood)
        part(root, "hood", (0, h - 0.18, 0), (w, 0.36, d), wood)
        part(root, "dial", (0, h - 0.19, d / 2 + 0.005), (w * 0.62, w * 0.62, 0.01), material("cream"))
        part(root, "window", (0, h * 0.45, d * 0.43), (w * 0.35, h * 0.3, 0.01), material("glass"))
    elif t == "vase":
        cyl(root, "vase", (0, 0.13, 0), 0.07, 0.26, material("delft_tiles"), r_top=0.045)
    elif t == "coat_rack":
        cyl(root, "pole", (0, h / 2, 0), 0.025, h, wood)
        cyl(root, "base", (0, 0.03, 0), 0.2, 0.06, wood)
        part(root, "coat", (0.05, h - 0.55, 0.04), (0.42, 0.9, 0.2), material("coat"))
    elif t == "painting":
        part(root, "canvas", (0, 0, 0), (w - 0.1, h - 0.1, d * 0.5), material("painting"))
        gold = material("brass")
        for (cx, cy, sw, sh) in ((0, h / 2 - 0.04, w, 0.08), (0, -h / 2 + 0.04, w, 0.08),
                                 (w / 2 - 0.04, 0, 0.08, h), (-w / 2 + 0.04, 0, 0.08, h)):
            part(root, "frame", (cx, cy, 0.01), (sw, sh, d), gold)
    elif t == "pendant_lamp":
        cord = room_h - pos[1]
        part(root, "cord", (0, cord / 2, 0), (0.012, cord, 0.012), material("soot"))
        cyl(root, "shade", (0, 0.1, 0), 0.24, 0.16, material("brass"), r_top=0.05)
        cyl(root, "bulb", (0, 0.0, 0), 0.04, 0.07, emissive("bulb", (1.0, 0.6, 0.3), 12.0))
    elif t == "rug":
        part(root, "rug", (0, 0.004, 0), (w, 0.008, d), material(p.get("material", "rug")))
    elif t == "paper":
        part(root, "paper", (0, 0.001, 0), (0.21, 0.002, 0.297), material("paper"))
    elif t == "candle":
        cyl(root, "holder", (0, 0.01, 0), 0.05, 0.02, material("brass"))
        cyl(root, "candle", (0, 0.09, 0), 0.018, 0.14, material("wax"))
        cyl(root, "flame", (0, 0.18, 0), 0.008, 0.035, emissive("flame", (1.0, 0.5, 0.15), 30.0), r_top=0.001)
    elif t == "curtain":
        for i in range(4):
            part(root, "fold", (-w / 2 + (i + 0.5) * w / 4, h / 2, 0.03 * (i % 2)), (w / 4 + 0.01, h, d * 0.6), material("velvet"))
    elif t == "pillar":
        part(root, "pillar", (0, h / 2, 0), (w, h, d), material("brick"))
    elif t == "wine_rack":
        for sx in (-1, 0, 1):
            part(root, "upright", (sx * (w / 2 - 0.03), h / 2, 0), (0.05, h, d), wood)
        for row in range(4):
            y = 0.25 + row * (h - 0.3) / 3.5
            part(root, "shelf", (0, y - 0.07, 0), (w, 0.03, d), wood)
            for k in range(7):
                cyl(root, "bottle", (-w / 2 + 0.15 + k * (w - 0.3) / 6, y + 0.02, 0.0), 0.04, d * 0.9,
                    material("bottle"), horizontal=True)
    elif t == "barrel":
        cyl(root, "barrel", (0, h / 2, 0), w / 2 * 0.9, h, wood)
        for y in (0.15, h - 0.15):
            cyl(root, "hoop", (0, y, 0), w / 2 * 0.93, 0.05, material("iron"))
    elif t == "crate":
        part(root, "crate", (0, h / 2, 0), (w, h, d), wood)
        for y in (0.2, 0.5):
            part(root, "slat", (0, h * y + 0.05, d / 2 + 0.01), (w, 0.08, 0.02), material("plaster_raw"))
    return root
