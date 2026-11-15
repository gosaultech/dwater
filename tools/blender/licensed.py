# damned_waters/tools/blender/licensed.py
# Purpose: stand the licensed models (tools/assets/models.json: CC BY cars, vans, an army truck,
# burnt wrecks, bicycles, bins, barriers, body bags) on the set. The street's "vehicle" props keep
# their RoomSpec as it is (size, "livery", "burnt", "color"): vehicle() picks a model for each, turns
# its nose to the prop's front, scales it to the prop's footprint, sets it on its wheels, repaints
# its body, swaps its windows for the set's own dirty glass and lays the set's weather over its
# materials (grime, streaks, the flood's silt line), so a borrowed car stands in the same rain as
# the street. "licensed" props name a model or one piece of a pack ({"type": "licensed", "model":
# "crowd_barrier"}). If a model is not in the cache the caller falls back to its own (vehicles.py).
#
# ELI5: hired cars for a film. Each arrives clean, in its own colour, facing any which way; the
# crew parks it on its mark, resprays it, and dirties it down to match the street.
import math
import random
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

import builders

CACHE = Path(__file__).resolve().parents[2] / "pipeline_out" / "assets" / "sketchfab"
# A model as it comes: which way its length runs ("x"/"y") and which end is its nose (+1/-1); the
# body paint's material ("paint": named, or found as the biggest painted surface); its real length;
# where its maker's marks are, read off flat elevations: (end, metres across from the middle, metres
# up from the road, radius in metres).
MODELS = {
    "car_punto": {"axis": "y", "front": -1, "paint": ["gt_body"], "length": 3.76,
                  "badges": [("front", 0.0, 0.62, 0.065), ("rear", 0.44, 0.90, 0.1), ("rear", -0.44, 0.90, 0.1)]},
    "car_focus": {"axis": "y", "front": -1, "length": 4.38,
                  "badges": [("front", 0.0, 0.66, 0.07), ("rear", 0.0, 1.01, 0.07), ("rear", 0.44, 0.93, 0.1), ("rear", -0.44, 0.93, 0.1)]},
    "car_octavia": {"axis": "y", "front": -1, "paint": ["primary"], "length": 4.51,
                    "badges": [("front", 0.0, 0.72, 0.06), ("rear", 0.0, 0.99, 0.06), ("rear", 0.38, 0.95, 0.09), ("rear", -0.38, 0.95, 0.09)]},
    "car_yaris": {"axis": "y", "front": -1, "paint": ["WCCARBODY"], "length": 3.61, "badges": [("front", 0.0, 0.79, 0.065), ("rear", 0.0, 0.935, 0.065)]},
    "car_v70": {"axis": "x", "front": 1, "paint": ["green"], "length": 4.71, "badges": [("front", 0.0, 0.66, 0.055)]},
    "van_sprinter": {"axis": "y", "front": -1, "paint": ["Carrosserie"], "length": 5.91,
                     "badges": [("front", 0.0, 0.865, 0.11), ("rear", 0.0, 1.28, 0.09)]},
    "van_euro": {"axis": "y", "front": -1, "paint": ["van_european_delivery_body_shd"], "length": 5.3},
    "truck_army": {"axis": "y", "front": -1, "paint": []},
    "wreck_crashed": {"axis": "y", "front": -1, "paint": []},
    "wreck_gutted": {"axis": "x", "front": 1, "paint": []},
    "wrecks_burnt": {"pca": True, "paint": []},
    "bike_classic": {"axis": "y", "front": -1, "paint": []},
    "moped": {"axis": "y", "front": -1, "paint": []},
    "bodybags": {"axis": "x", "front": 1, "paint": [], "loose": True},
    "sandbags": {"axis": "x", "front": 1, "paint": []},
    "street_props": {"axis": "x", "front": 1, "paint": []},
    "street_pack": {"axis": "x", "front": 1, "paint": []},
    "barriers": {"axis": "x", "front": 1, "paint": []},
}
# One thing out of a pack: (model, the materials that mark it, which of the things so marked).
PIECES = {
    "bin_blue": ("street_props", ["Bin_Body_Blue"], 0), "bin_green": ("street_props", ["Bin_Body_Green"], 0),
    "bin_orange": ("street_props", ["Bin_Body_Orange"], 0), "bin_yellow": ("street_props", ["Bin_Body_Yellow"], 0),
    "bin_red": ("street_props", ["Bin_Body_Red"], 0), "dumpster": ("street_props", ["Big_Bin"], 0),
    "bench": ("street_props", ["Wood"], 0), "box_large": ("street_props", ["Large_CardBoard_Box"], 0),
    "box_medium": ("street_props", ["Medium_Cardboard_Box"], 0), "box_small": ("street_props", ["Small_Cardboard_Box"], 0),
    "rubbish_bag": ("street_props", ["Trash_Bag_2nd"], 0), "cone": ("street_props", ["Orange_Cone"], 0),
    "crowd_barrier": ("street_pack", ["Metal_Barrier1"], 0), "crowd_barrier_bent": ("street_pack", ["Metal_Barrier1_Damaged"], 0),
    "crowd_barrier_b": ("street_pack", ["Metal_Barrier2"], 0), "water_barrier": ("street_pack", ["Barrier"], 0),
    "oil_barrel": ("street_pack", ["Barrel"], 0), "concrete_barrier": ("street_pack", ["Concrete_Barrier"], 0),
    "jersey": ("barriers", ["barrier"], 0), "jersey_painted": ("barriers", ["barrier_painted"], 0),
    "jersey_short": ("barriers", ["short_barrier"], 0), "fence_panel": ("barriers", ["fenced_barrier"], 0),
    "burnt_car_a": ("wrecks_burnt", None, 0), "burnt_car_b": ("wrecks_burnt", None, 1),
    "bodybag_a": ("bodybags", None, 0), "bodybag_b": ("bodybags", None, 1), "bodybag_c": ("bodybags", None, 2),
    "bodybag_d": ("bodybags", None, 3), "bodybag_e": ("bodybags", None, 4),
}
NOT_PAINT = ("glass", "window", "vitre", "black", "rubber", "tire", "tyre", "reifen", "interior", "interrieur", "chrome", "shadow", "wheel", "rim",
             "light", "phare", "amber", "grey", "gray", "default", "material", "sitze", "plastik", "schwarz", "chassis", "trim", "undercarriage")
GLASS = ("glass", "window", "vitre")
THROW = ("shadow",)   # a painted-on shadow under a car: thrown away if it is a flat sheet (the set casts its own)
CARS = ["car_punto", "car_focus", "car_octavia", "car_yaris", "car_v70"]
COLOURS = [(0.012, 0.012, 0.014), (0.30, 0.31, 0.32), (0.55, 0.56, 0.57), (0.02, 0.04, 0.12), (0.22, 0.02, 0.02), (0.02, 0.08, 0.05),
           (0.12, 0.13, 0.15), (0.45, 0.40, 0.30), (0.03, 0.10, 0.14)]   # what a Dutch street is parked full of: black, greys, silver, dark blue, a red, a green
_LIB = {}       # model -> its meshes as imported (kept out of the picture; every car on the set is a copy)
_TINTED = {}    # (material, colour) -> the repainted copy


def available(key):
    model = PIECES[key][0] if key in PIECES else key
    return model in MODELS and any((CACHE / model).glob("*.glb"))


def reset():
    _LIB.clear()
    _TINTED.clear()
    _TREES.clear()


def _base(name):
    return name.rsplit(".", 1)[0] if name.rsplit(".", 1)[-1].isdigit() else name


def _is(name, words):
    return any(w in name.lower() for w in words)


def _hole():
    m = bpy.data.materials.get("licensed_hole")
    if m is None:
        m = bpy.data.materials.new("licensed_hole")
        m.use_nodes = True
        m.node_tree.nodes.clear()
        out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        m.node_tree.links.new(m.node_tree.nodes.new("ShaderNodeBsdfTransparent").outputs[0], out.inputs["Surface"])
    return m


def _load(model):
    """The model's meshes, imported once: its windows swapped for the set's glass, its fake shadow
    thrown away, the set's weather laid over every material."""
    if model in _LIB:
        return _LIB[model]
    import combino
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(sorted((CACHE / model).glob("*.glb"))[0]))
    new = [o for o in bpy.data.objects if o not in before]
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == "MESH"]
    if MODELS[model].get("loose") and len(meshes) == 1:   # one mesh of several things: cut it at the gaps
        bpy.ops.object.select_all(action="DESELECT")
        meshes[0].select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.mesh.separate(type="LOOSE")
        meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        bpy.context.view_layer.update()
    glass = combino._glass("licensed_glass", (0.16, 0.18, 0.19), 0.2)
    done, keep = set(), []
    for o in meshes:
        lo, hi = _bounds([o])
        names = [s.material.name for s in o.material_slots if s.material]
        if names and all(_is(n, THROW) for n in names) and hi.z - lo.z < 0.03 * max(hi.x - lo.x, hi.y - lo.y):
            o.hide_render = True
            continue   # (left out of the library: not even its outline for the ground's silt to drift against)
        keep.append(o)
        for s in o.material_slots:
            m = s.material
            if m is None:
                continue
            if _is(m.name, GLASS):
                s.material = glass
            elif m.name not in done:
                done.add(m.name)
                _tint_node(m)
                builders.weather(m, {"grime": 1.1, "streaks": 0.5, "silt": 0.5, "rust": 0.2, "bevel": 0.0})
        o.hide_render = True
        o.hide_viewport = True
    meshes = keep
    if MODELS[model].get("badges"):
        meshes = meshes + _debadge(model, meshes)
    for o in new:
        o.hide_render = True
    _LIB[model] = meshes
    return meshes


_TREES = {}     # a mesh -> its faces as a search tree, in the library's space (for dropping points onto it)


def _strike(meshes, origin, direction):
    """The first surface a ray meets among the meshes (all in the library's space): (distance, where,
    the mesh, the face), or None."""
    from mathutils.bvhtree import BVHTree
    best = None
    for o in meshes:
        tree = _TREES.get(o.name)
        if tree is None:
            tree = _TREES[o.name] = BVHTree.FromPolygons([o.matrix_world @ v.co for v in o.data.vertices], [tuple(p.vertices) for p in o.data.polygons])
        loc, _n, face, dist = tree.ray_cast(origin, direction.normalized())
        if loc is not None and (best is None or dist < best[0]):
            best = (dist, loc, o, face)
    return best


def _debadge(model, meshes):
    """A maker's badge is not ours to show: over each one a small flat cap, its rim pressed onto the
    body (dropped onto the surface along the car's length), in the paint of the panel beside it -
    what a de-badged car looks like. Returns the caps, to travel with the model's meshes."""
    spec = MODELS[model]
    lo, hi = _bounds(meshes)
    ax = 0 if spec["axis"] == "x" else 1
    side = 1 - ax
    unit = (hi[ax] - lo[ax]) / spec["length"]           # the library's units per metre
    mid = (lo[side] + hi[side]) / 2
    paint = _paint_of(model, meshes)
    caps = []
    for end, across, height, radius in spec["badges"]:
        sign = spec["front"] if end == "front" else -spec["front"]   # which way out of the car this end faces
        aim = Vector((0.0, 0.0, 0.0))
        aim[ax] = -sign

        def start(da, dz):
            p = Vector((0.0, 0.0, lo.z + (height + dz) * unit))
            p[ax] = (hi[ax] if sign > 0 else lo[ax]) + sign * 0.5 * unit
            p[side] = mid + (across + da) * unit
            return p
        seg = 14
        ring = [(math.cos(2 * math.pi * q / seg), math.sin(2 * math.pi * q / seg)) for q in range(seg)]
        hits = [_strike(meshes, start(c * radius, s_ * radius), aim) for c, s_ in ring]
        inner = [_strike(meshes, start(c * radius * f_, s_ * radius * f_), aim) for f_ in (0.0, 0.5) for c, s_ in ring[::2]]
        found = [h for h in hits + inner if h]
        if not found:
            continue
        proud = min(h[0] for h in found)                 # the nearest any of it comes: the badge's own face
        # the cap's paint: the body's if any of the rim stands on it, else what most of the rim stands on
        mats = []
        for h in [h for h in hits if h]:
            o, poly = h[2], h[2].data.polygons[h[3]]
            m = o.material_slots[poly.material_index].material if o.material_slots else None
            uv = o.data.uv_layers.active.data[poly.loop_indices[0]].uv[:] if o.data.uv_layers.active else (0.0, 0.0)
            mats.append((m, uv))
        on_paint = [mu for mu in mats if mu[0] is not None and _base(mu[0].name) in paint]
        names = [mu[0].name for mu in mats if mu[0] is not None]
        mat, uv = on_paint[0] if on_paint else next((mu for mu in mats if mu[0] is not None and mu[0].name == max(set(names), key=names.count)), (None, (0.0, 0.0)))

        def at(c, s_, f_, depth):
            p = start(c * radius * f_, s_ * radius * f_)
            return p + aim.normalized() * depth
        verts = [at(0.0, 0.0, 0.0, proud - 0.005 * unit)]
        verts += [at(c, s_, 0.8, proud - 0.005 * unit) for c, s_ in ring]
        verts += [at(c, s_, 1.0, min(h[0] if h else proud, proud + 0.03 * unit) - 0.002 * unit) for (c, s_), h in zip(ring, hits)]
        faces = []
        for q in range(seg):
            faces.append((0, 1 + q, 1 + (q + 1) % seg))
            faces.append((1 + q, 1 + seg + q, 1 + seg + (q + 1) % seg, 1 + (q + 1) % seg))
        me = bpy.data.meshes.new("debadge")
        me.from_pydata(verts, [], faces)
        layer = me.uv_layers.new(name="UVMap")
        for l in layer.data:
            l.uv = uv
        if mat is not None:
            me.materials.append(mat)
        cap = bpy.data.objects.new("debadge", me)
        bpy.context.scene.collection.objects.link(cap)
        cap.hide_render = cap.hide_viewport = True
        caps.append(cap)
    bpy.context.view_layer.update()
    return caps


def _bounds(objs):
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return lo, hi


def _things(meshes, marks):
    """The separate things among a pack's meshes (touching meshes are one thing), left to right;
    with `marks`, only the things one of whose materials is so named."""
    boxes = [(_bounds([o]), o) for o in meshes]
    groups = []
    for (lo, hi), o in boxes:
        near = [g for g in groups if all(lo[i] <= g["hi"][i] + 0.02 and hi[i] >= g["lo"][i] - 0.02 for i in range(3))]
        g = {"lo": lo.copy(), "hi": hi.copy(), "objs": [o]}
        for n in near:
            g["lo"], g["hi"] = Vector(map(min, g["lo"], n["lo"])), Vector(map(max, g["hi"], n["hi"]))
            g["objs"] += n["objs"]
            groups.remove(n)
        groups.append(g)
    if marks:
        groups = [g for g in groups if any(s.material and _base(s.material.name) in marks for o in g["objs"] for s in o.material_slots)]
    return [g["objs"] for g in sorted(groups, key=lambda g: (round(g["lo"][0], 2), round(g["lo"][1], 2)))]


def _points(objs, most=400):
    """A few hundred of the meshes' points, where they stand in the library."""
    out = []
    for o in objs:
        vs = o.data.vertices
        out += [o.matrix_world @ vs[i].co for i in range(0, len(vs), max(1, len(vs) // most))]
    return out


def _nose(model, objs):
    """The angle (about up) that turns the model's nose to +x."""
    spec = MODELS[model]
    if spec.get("pca"):   # a scan lying any which way: its long axis, from where its points are
        pts = _points(objs)
        cx, cy = sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts)
        sxx = sum((p.x - cx) ** 2 for p in pts)
        syy = sum((p.y - cy) ** 2 for p in pts)
        sxy = sum((p.x - cx) * (p.y - cy) for p in pts)
        return -0.5 * math.atan2(2 * sxy, sxx - syy)
    f = (spec["front"], 0.0) if spec["axis"] == "x" else (0.0, spec["front"])
    return -math.atan2(f[1], f[0])


def _paint_of(model, objs):
    """The body paint's materials: named in MODELS, else the biggest surface that is not glass, tyre or trim."""
    named = MODELS[model].get("paint")
    if named is not None:
        return set(named)
    area = {}
    for o in objs:
        for poly in o.data.polygons:
            s = o.material_slots[poly.material_index].material if o.material_slots else None
            if s is not None and not _is(s.name, NOT_PAINT + GLASS + THROW):
                area[_base(s.name)] = area.get(_base(s.name), 0.0) + poly.area
    return {max(area, key=area.get)} if area else set()


def _tint_node(m):
    """A respray point in a material, put in before the weather: a mix node between the paint's own
    colour (or texture) and the surface, passing it straight through until a copy is tinted."""
    nt = m.node_tree
    for b in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        bc = b.inputs["Base Color"]
        mx = nt.nodes.new("ShaderNodeMixRGB")
        mx.name, mx.blend_type = "dw_tint", "MIX"
        mx.inputs["Fac"].default_value = 0.0
        if bc.is_linked:
            nt.links.new(bc.links[0].from_socket, mx.inputs["Color1"])
            mx["textured"] = 1
        else:
            mx.inputs["Color1"].default_value = bc.default_value[:]
            mx["textured"] = 0
        nt.links.new(mx.outputs["Color"], bc)
        return


def _brightness(sock, depth=0):
    """How bright the picture feeding a socket is on average (0..1), or None if no picture does."""
    if not sock.is_linked or depth > 6:
        return None
    n = sock.links[0].from_node
    if n.type == "TEX_IMAGE" and n.image is not None and n.image.size[0] > 0:
        import numpy as np
        px = np.empty(n.image.size[0] * n.image.size[1] * 4, dtype=np.float32)
        n.image.pixels.foreach_get(px)
        rgb = px.reshape(-1, 4)[::97, :3]
        return float((rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).mean())
    for inp in n.inputs:
        v = _brightness(inp, depth + 1)
        if v is not None:
            return v
    return None


def _tinted(m, color):
    """A copy of a paint in another colour: a plain paint takes the colour; a painted texture keeps
    its lights and darks (its dirt, its panel lines) and takes the hue."""
    key = (m.name, tuple(round(c, 3) for c in color))
    if key in _TINTED:
        return _TINTED[key]
    c = m.copy()
    nt = c.node_tree
    mx = nt.nodes.get("dw_tint")
    if mx is not None:
        lum = _brightness(mx.inputs["Color1"]) if mx.get("textured") else None
        if lum is None:   # a plain paint (or one coloured by its vertices): the new colour outright
            mx.inputs["Fac"].default_value = 1.0
            mx.inputs["Color2"].default_value = (*color, 1.0)
        else:             # a texture: its grey, times the colour, brought back up to the colour's own brightness
            bw = nt.nodes.new("ShaderNodeRGBToBW")
            nt.links.new(mx.inputs["Color1"].links[0].from_socket, bw.inputs[0])
            nt.links.new(bw.outputs[0], mx.inputs["Color1"])
            mx.blend_type = "MULTIPLY"
            mx.inputs["Fac"].default_value = 1.0
            g = 1.0 / max(lum, 0.15)
            mx.inputs["Color2"].default_value = (*(v * g for v in color), 1.0)
    _TINTED[key] = c
    return c


def place(root, key, length, width=None, color=None, yaw=0.0, lift=0.0):
    """A model (or one piece of a pack) under `root`: its nose to the root's +x, scaled to `length`
    (and no wider than `width`), standing on the ground; `color`: its body resprayed."""
    model, marks, which = PIECES[key] if key in PIECES else (key, None, None)
    meshes = _load(model)
    if which is not None:
        things = _things(meshes, marks)
        meshes = things[min(which, len(things) - 1)]
    lo, hi = _bounds(meshes)
    turn = _nose(model, meshes) + math.radians(yaw)
    rot = Matrix.Rotation(turn, 4, "Z")
    corners = [rot @ Vector((x, y, 0.0)) for x in (lo.x, hi.x) for y in (lo.y, hi.y)]
    if MODELS[model].get("pca"):   # (a turned scan's box is measured after the turn)
        pts = [rot @ q for q in _points(meshes)]
        ex, ey = max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts)
        centre = Vector(((max(p.x for p in pts) + min(p.x for p in pts)) / 2, (max(p.y for p in pts) + min(p.y for p in pts)) / 2, 0.0))
        if ey > ex:   # (its long axis came out across: a quarter turn more)
            rot = Matrix.Rotation(math.pi / 2, 4, "Z") @ rot
            centre = Matrix.Rotation(math.pi / 2, 4, "Z") @ centre
            ex, ey = ey, ex
    else:
        ex, ey = max(c.x for c in corners) - min(c.x for c in corners), max(c.y for c in corners) - min(c.y for c in corners)
        centre = rot @ Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0.0))
    k = length / max(ex, 1e-6)
    if width:
        k = min(k, width / max(ey, 1e-6))
    holder = bpy.data.objects.new("licensed_" + key, None)
    bpy.context.scene.collection.objects.link(holder)
    holder.parent = root
    holder.matrix_basis = Matrix.Translation((0.0, 0.0, lift)) @ Matrix.Scale(k, 4) @ Matrix.Translation((-centre.x, -centre.y, -lo.z)) @ rot
    paint = _paint_of(model, meshes) if color is not None else set()
    for o in meshes:
        c = o.copy()   # (the mesh is shared: forty parked cars are five cars, eight times)
        bpy.context.scene.collection.objects.link(c)
        c.hide_render = c.hide_viewport = False
        c.parent = holder
        c.matrix_parent_inverse.identity()
        c.matrix_basis = o.matrix_world.copy()
        if paint and any(s.material and _base(s.material.name) in paint for s in c.material_slots):
            c.data = o.data.copy()
            for i, s in enumerate(c.material_slots):
                if s.material and _base(s.material.name) in paint:
                    c.material_slots[i].material = _tinted(s.material, color)
    return holder, (ex * k, (hi.z - lo.z) * k, ey * k)


def vehicle(root, p, w, h, d):
    """A "vehicle" prop as a licensed model, if the cache has one for it: returns True when placed."""
    rng = random.Random(int(p["pos"][0] * 100) * 7919 + int(p["pos"][2] * 100))   # (the same car on the same spot, every render)
    liv = p.get("livery", "car")
    color = p.get("color")
    if p.get("model"):
        key = p["model"]
    elif p.get("burnt"):
        key = rng.choice(["burnt_car_a", "burnt_car_b", "wreck_gutted"])
        color = None
    elif liv == "army":
        key, color = "truck_army", None
    elif liv == "ambulance":
        key, color = "van_sprinter", (0.85, 0.62, 0.02)
    elif p.get("van") or h >= 1.9:
        key = "van_sprinter" if liv == "police" or rng.random() < 0.5 else "van_euro"
        color = (0.72, 0.73, 0.74) if liv == "police" else (color or rng.choice([(0.7, 0.7, 0.7), (0.5, 0.42, 0.3), (0.05, 0.06, 0.08)]))
    elif liv == "police":
        key, color = "car_v70", (0.72, 0.73, 0.74)
    elif liv == "taxi":
        key, color = "car_octavia", (0.012, 0.012, 0.014)
    else:
        key = rng.choice(CARS)
        color = color or rng.choice(COLOURS)
    if not available(key):
        return False
    place(root, key, w, d * 1.04, color=color)
    return True


def prop(root, p, w, h, d):
    """A "licensed" prop: {"model": a MODELS or PIECES name}; sized by its "size"[0] along its length."""
    if available(p["model"]):
        place(root, p["model"], w, None, color=p.get("color"), yaw=p.get("yaw_model", 0.0))


import kit  # noqa: E402
kit.PROPS["licensed"] = prop
