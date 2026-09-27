# damned_waters/tools/blender/render_characters.py
# Purpose: look-target renders for the cast.
#   studio: each character alone under horror key/rim lighting (key art)
#   frames: characters placed inside real rooms, seen through the game's own
#           camera shots = "what a finished in-game frame should look like"
#   python tools/blender/render_characters.py --mode studio --res 640x800
#   blender -b -P tools/blender/render_characters.py -- --mode frames --quality final --gpu
import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pipeline"))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import characters as C  # noqa: E402
import render_rooms as RR  # noqa: E402
import roomspec  # noqa: E402

REPO = HERE.parent.parent
STUDIO = {  # builder, framing target height, camera distance
    "protagonist": (lambda: C.protagonist((0, 0, 0), 25, "aim"), 1.0, 3.3),
    "verdronkene": (lambda: C.verdronkene((0, 0, 0), -20, "shamble", seed=3, long_hair=True), 1.0, 3.3),
    "kelderkind": (lambda: C.kelderkind((0, 0, 0), -30, "prowl"), 0.35, 2.0),
    "grachtenvorst": (lambda: C.grachtenvorst((0, 0, 0), -15, "slam"), 1.3, 5.6),
}
# room, shot, [(builder, godot pos, yaw_deg, extra kwargs)], label
FRAMES = [
    ("gang", "b", [(C.protagonist, (0.85, 0, 6.5), 180, {"pose": "aim"}),
                   (C.verdronkene, (1.05, 0, 8.7), 10, {"pose": "shamble", "seed": 3, "long_hair": True}),
                   (C.verdronkene, (1.55, 0, 9.35), -15, {"pose": "windup", "seed": 5})], "frame_gang_front_door"),
    ("voorkamer", "a", [(C.protagonist, (2.5, 0, 4.5), 47, {"pose": "aim"}),
                        (C.kelderkind, (0.95, 0, 3.05), -90, {"pose": "leap"})], "frame_voorkamer_fireplace"),
    ("kelder", "a", [(C.grachtenvorst, (2.2, 0, 1.5), 180, {"pose": "slam"}),
                     (C.protagonist, (2.6, 0, 5.1), 6, {"pose": "aim"})], "frame_kelder_boss"),
]


def studio_scene(res, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    C.reset()
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.render.resolution_x, s.render.resolution_y = res
    s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.cycles.max_bounces = 6
    s.view_settings.view_transform = "AgX"
    try:
        s.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    w = bpy.data.worlds.new("w")
    if w.node_tree is None:
        w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.007, 1)
    s.world = w
    me = bpy.data.meshes.new("floor")
    me.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("wet_floor")
    fm.use_nodes = True
    b = fm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.02, 0.022, 0.025, 1)
    b.inputs["Roughness"].default_value = 0.12
    me.materials.append(fm)
    s.collection.objects.link(bpy.data.objects.new("floor", me))
    for name, loc, look, color, power, size in (
            ("key", (-2.2, 2.5, 3.2), (0, 0, 1.0), (0.62, 0.74, 1.0), 550, 1.2),
            ("rim", (2.4, -2.6, 2.6), (0, 0, 1.2), (1.0, 0.55, 0.25), 1400, 0.8),
            ("fill", (2.5, 3.0, 0.6), (0, 0, 0.8), (0.3, 0.35, 0.45), 60, 2.0)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.color, ld.energy, ld.size = color, power, size
        ob = bpy.data.objects.new(name, ld)
        s.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return s


def studio_camera(s, target_h, dist):
    cd = bpy.data.cameras.new("cam")
    cd.lens = 55
    ob = bpy.data.objects.new("cam", cd)
    s.collection.objects.link(ob)
    ob.location = (0.35 * dist, dist, target_h + 0.35)
    ob.rotation_euler = (Vector((0, 0, target_h)) - ob.location).to_track_quat("-Z", "Y").to_euler()
    s.camera = ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["studio", "frames"], default="studio")
    ap.add_argument("--only", default="")
    ap.add_argument("--res", default="")
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--quality", default="ship")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--out", default=str(REPO / "docs" / "concept"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {x for x in a.only.split(",") if x}
    if a.mode == "studio":
        res = tuple(int(v) for v in (a.res or "640x800").split("x"))
        for name, (build, h, dist) in STUDIO.items():
            if only and name not in only:
                continue
            s = studio_scene(res, a.samples)
            if a.gpu and RR.enable_gpu():
                s.cycles.device = "GPU"
            build()
            studio_camera(s, h, dist)
            s.render.filepath = str(out / f"studio_{name}.png")
            bpy.ops.render.render(write_still=True)
            print(f"[concept] studio {name}")
        return
    specs = roomspec.load_all(REPO / "game" / "data" / "rooms")
    res = tuple(int(v) for v in (a.res or "960x540").split("x"))
    q = dict(RR.QUALITY[a.quality])
    q["samples"] = a.samples
    for room, shot_id, cast, label in FRAMES:
        if only and label not in only:
            continue
        spec = specs[room]
        s = RR.new_scene(spec, q, res)
        C.reset()
        if a.gpu and RR.enable_gpu():
            s.cycles.device = "GPU"
        RR.build_room(spec)
        for builder, pos, yaw, kw in cast:
            builder(pos, yaw, **kw)
        s.camera = RR.add_camera(next(x for x in spec["shots"] if x["id"] == shot_id))
        RR.render_beauty(s, q, out / f"{label}.png", spec.get("render", {}).get("exposure", 0.6))
        print(f"[concept] frame {label}")


if __name__ == "__main__":
    main()
