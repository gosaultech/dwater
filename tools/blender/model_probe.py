# damned_waters/tools/blender/model_probe.py
# Purpose: look at a downloaded model before the sets use it: what it is made of (its top-level
# pieces and their sizes, faces, materials, textures) and what it looks like (two views under a
# plain sky), so its scale, which way it faces, and which pieces to keep can be written down in
# licensed.py rather than guessed. A tool for the set builder, not a game asset.
#
#   blender -b --factory-startup -P tools/blender/model_probe.py -- --model FILE.glb --out DIR [--name KEY]
#
# ELI5: before a hired prop goes on stage, someone unpacks the crate, measures it, and takes a
# photo for the prop list.
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def bounds(objs):
    lo, hi = Vector((1e9, 1e9, 1e9)), Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo, hi = Vector(map(min, lo, w)), Vector(map(max, hi, w))
    return lo, hi


def family(o):
    return [o] + [d for c in o.children for d in family(c)]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--res", default="640x360")
    a = ap.parse_args(argv)
    name = a.name or Path(a.model).stem
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=a.model)
    bpy.context.view_layer.update()
    objs = list(bpy.data.objects)
    meshes = [o for o in objs if o.type == "MESH"]
    lo, hi = bounds(meshes)
    report = {"name": name, "size": [round(v, 3) for v in (hi - lo)], "lo": [round(v, 3) for v in lo], "objects": len(objs), "meshes": len(meshes),
              "faces": sum(len(o.data.polygons) for o in meshes), "materials": sorted({s.material.name for o in meshes for s in o.material_slots if s.material})[:40],
              "images": sorted({i.name + " %dx%d" % tuple(i.size) for i in bpy.data.images})[:40], "pieces": []}

    def walk(o, depth):   # the tree down to where it branches into things worth naming
        fam = [m for m in family(o) if m.type == "MESH"]
        if not fam:
            return
        l, h = bounds(fam)
        report["pieces"].append({"depth": depth, "name": o.name, "type": o.type, "size": [round(v, 2) for v in (h - l)], "at": [round(v, 2) for v in (l + h) / 2],
                                 "faces": sum(len(m.data.polygons) for m in fam)})
        if depth < 3 and len(o.children) > 1:
            for c in sorted(o.children, key=lambda c: c.name)[:40]:
                walk(c, depth + 1)
    for o in [o for o in objs if o.parent is None]:
        walk(o, 0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(report, indent=1))
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples, s.cycles.use_denoising = 8, True
    s.render.resolution_x, s.render.resolution_y = (int(v) for v in a.res.split("x"))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.86, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    s.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(35))
    s.collection.objects.link(sun)
    c = (lo + hi) / 2
    r = max((hi - lo).length, 1e-3)
    for i, az in enumerate((35, 215)):
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        s.collection.objects.link(cam)
        d = Vector((math.cos(math.radians(az)), math.sin(math.radians(az)), 0.42)).normalized()
        cam.location = c + d * r * 1.25
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.data.clip_start, cam.data.clip_end = r / 500, r * 10
        s.camera = cam
        s.render.filepath = str(out / f"{name}_{i}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
