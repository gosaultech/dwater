# damned_waters/tools/blender/photos.py
# The sets' photographs (tools/assets/photos.py): a cropped photo on a flat card, lit by the scene. Set
# just behind a shelf's edge it reads as the stock on it (shops.shelving's "photo"); on its own it's
# a "photo_layer" prop (a wall of bottles, a shop window's display).
import json
import math
from pathlib import Path

import bpy

import kit

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "pipeline_out" / "assets" / "photos"
_MANIFEST = None


def manifest():
    global _MANIFEST
    if _MANIFEST is None:
        raw = json.loads((REPO / "tools" / "assets" / "photos.json").read_text())
        _MANIFEST = {k: v for k, v in raw.items() if not k.startswith("_")}
    return _MANIFEST


def aspect(pid, crop):
    """Width over height of a crop, in the photo's pixels."""
    w, h = manifest()[pid]["size"]
    return (crop[2] - crop[0]) * w / max((crop[3] - crop[1]) * h, 1e-6)


def material(pid, rough=0.55, emit=0.0, bump=0.15):
    name = "photo_%s_%d_%d_%d" % (pid, int(rough * 100), int(emit * 100), int(bump * 100))
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    path = CACHE / f"{pid}.jpg"
    if not path.exists():
        raise FileNotFoundError(f"{path}: run python3 tools/assets/photos.py fetch")
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tex.image.colorspace_settings.name = "sRGB"
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    if emit > 0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit
    if bump > 0:   # the picture's light and dark as a little relief, so the scene's light catches it
        bw = nt.nodes.new("ShaderNodeRGBToBW")
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        bn.inputs["Distance"].default_value = 0.01
        nt.links.new(tex.outputs["Color"], bw.inputs[0])
        nt.links.new(bw.outputs[0], bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def card(root, name, x0, y0, x1, y1, z, pid, crop, tiles=1, facing=1, lie=False, tilt=0.0, **kw):
    """A photo card from (x0, y0) to (x1, y1) at depth z in the parent's frame, facing +z (facing=-1:
    -z; lie: lying face up at height z, y0..y1 then running back to front), the crop (u0, v0, u1, v1
    from the photo's top-left) repeated `tiles` times across it."""
    u0, v0, u1, v1 = crop
    verts, faces, uvs = [], [], []
    for t in range(tiles):
        a = x0 + (x1 - x0) * t / tiles
        b = x0 + (x1 - x0) * (t + 1) / tiles
        if facing < 0:
            a, b = b, a
        i = len(verts)
        if lie:
            verts += [(a, z, y1), (b, z, y1), (b, z, y0), (a, z, y0)]
        else:   # (tilt: leaning back from its foot, in radians)
            yt, zt = y0 + (y1 - y0) * math.cos(tilt), z - facing * (y1 - y0) * math.sin(tilt)
            verts += [(a, y0, z), (b, y0, z), (b, yt, zt), (a, yt, zt)]
        faces.append((i, i + 1, i + 2, i + 3))
        uvs += [(u0, 1 - v1), (u1, 1 - v1), (u1, 1 - v0), (u0, 1 - v0)]
    ob = kit.mesh(name, verts, faces, material(pid, **kw), root)
    uv = ob.data.uv_layers["UVMap"]
    for poly in ob.data.polygons:
        for li in poly.loop_indices:
            uv.data[li].uv = uvs[ob.data.loops[li].vertex_index]
    return ob


def row_card(root, pid, k, x0, x1, y0, y1, z, facing=1, **kw):
    """Shelf level k's stock: one of the photo's rows (its panel if it has none), repeated to fill."""
    e = manifest()[pid]
    rows = e.get("rows") or [e["panel"]]
    crop = rows[k % len(rows)]
    tiles = max(1, round((x1 - x0) / max((y1 - y0) * aspect(pid, crop), 0.05)))
    return card(root, "shelf_photo", x0, y0, x1, y1, z, pid, crop, tiles, facing, **kw)


def photo_layer(root, p, w, h, d):
    """A photo standing on the prop's spot, w by h, facing +z ("lie": flat, w by d, at the prop's
    height): "photo", "crop" (else the photo's panel), "tiles" across, "emit" (backlit), "rough"."""
    e = manifest()[p["photo"]]
    crop = p.get("crop") or e.get("panel") or [0.0, 0.0, 1.0, 1.0]
    kw = {"rough": p.get("rough", 0.55), "emit": p.get("emit", 0.0), "bump": p.get("bump", 0.15)}
    if p.get("lie"):
        card(root, "photo_layer", -w / 2, -d / 2, w / 2, d / 2, 0.0, p["photo"], crop, p.get("tiles", 1), lie=True, **kw)
    else:
        card(root, "photo_layer", -w / 2, 0.0, w / 2, h, 0.0, p["photo"], crop, p.get("tiles", 1), **kw)


def clothes_rail(root, p, w, h, d):
    """A chrome clothes rail on two T-feet, the clothes on it a photo of real ones (both sides)."""
    from street import Acc, M
    a = Acc()
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.03)
        a.rod((x, 0.02, 0.0), (x, h, 0.0), 0.014, 0.014, 8)
        a.rod((x, 0.02, -d / 2), (x, 0.02, d / 2), 0.014, 0.014, 6)
    a.rod((-w / 2, h, 0.0), (w / 2, h, 0.0), 0.013, 0.013, 8)
    a.build("rail", M({"color": [0.75, 0.76, 0.78], "rough": 0.25, "metal": 1.0}), root)
    pid = p.get("photo", "clothes_closet")
    crop = manifest()[pid].get("panel") or [0.0, 0.0, 1.0, 1.0]
    for f in (1, -1):
        card(root, "clothes", -w / 2 + 0.06, max(0.2, h - 1.2), w / 2 - 0.06, h - 0.03, 0.05 * f, pid, crop, facing=f, rough=0.85, bump=0.3)


kit.PROPS["photo_layer"] = photo_layer
kit.PROPS["clothes_rail"] = clothes_rail
