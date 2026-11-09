# damned_waters/tools/blender/vehicle_studio.py
# Purpose: a look-development stage for the street's things on their own (vehicles.py's cars, vans
# and trams; a street's trams): each set on a wet road under a night street's light (a lamp, the
# moon, a little sky), the flood's line on everything, rendered from a few angles in seconds rather
# than the minutes a whole street takes. A tool for judging and iterating a model, not a game asset.
#
#   blender -b --factory-startup -P tools/blender/vehicle_studio.py -- --out DIR [--set vehicles|trams|dead]
#
# ELI5: the photo booth at a car show: one car at a time under the same lights, so you judge the car,
# not the street it's parked in.
import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pipeline"))

import bpy  # noqa: E402

import builders  # noqa: E402
from roomspec import g2b  # noqa: E402

SETS = {
    "vehicles": [
        {"type": "vehicle", "pos": [0.0, 0.0, 0.0], "yaw": 25, "size": [4.3, 1.48, 1.8], "livery": "car", "color": [0.45, 0.06, 0.05]},
        {"type": "vehicle", "pos": [6.0, 0.0, 0.0], "yaw": 25, "size": [4.6, 1.5, 1.85], "livery": "taxi", "door_open": "left"},
        {"type": "vehicle", "pos": [12.5, 0.0, 0.0], "yaw": 25, "size": [5.4, 2.3, 2.0], "livery": "police"},
        {"type": "vehicle", "pos": [19.0, 0.0, 0.0], "yaw": 25, "size": [6.0, 2.6, 2.1], "livery": "ambulance"},
        {"type": "vehicle", "pos": [25.0, 0.0, 0.0], "yaw": 25, "size": [4.4, 1.45, 1.8], "livery": "car", "burnt": True},
    ],
    "heavy": [
        {"type": "vehicle", "pos": [0.0, 0.0, 0.0], "yaw": 25, "size": [6.4, 2.8, 2.3], "livery": "army", "van": True, "door_open": "left"},
        {"type": "bus", "pos": [12.0, 0.0, 2.0], "yaw": 25, "size": [12.0, 3.2, 2.6], "seed": 82},
        {"type": "bus", "pos": [26.0, 0.0, 4.0], "yaw": 25, "size": [18.0, 3.1, 2.55], "board": "EVACUATIE · CENTRAAL"},
    ],
    "trams": [
        {"type": "tram", "pos": [0.0, 0.0, 0.0], "yaw": 0, "size": [30.0, 3.4, 2.4], "board": "CENTRAAL", "power": 300.0},
        {"type": "tram", "pos": [0.0, 0.0, 9.0], "yaw": 0, "size": [30.0, 3.4, 2.4], "board": "", "power": 170.0, "pantograph": False,
         "derail": {"yaw": [0.0, 9.0, 24.0], "roll": [0.0, 2.0, 6.5], "lift": [0.0, 0.0, 0.1]}, "dark": [2], "smashed": [1, 2]},
    ],
    "plant": [   # the site's things: a lighting tower, the fair's stalls
        {"type": "light_tower", "pos": [0.0, 0.0, 0.0], "yaw": 20, "size": [2.2, 8.5, 1.4], "aim": [4.0, 0.0, 14.0], "power": 1500.0, "seed": 7},
        {"type": "fair_stall", "pos": [7.0, 0.0, 1.0], "yaw": -10, "size": [5.0, 2.8, 2.6], "kind": "oliebollen", "seed": 1},
        {"type": "fair_stall", "pos": [14.0, 0.0, 0.0], "yaw": -20, "size": [5.0, 2.8, 2.6], "kind": "grijper", "seed": 4},
        {"type": "fair_stall", "pos": [21.0, 0.0, -1.0], "yaw": -30, "size": [5.0, 2.8, 2.6], "kind": "schiettent", "seed": 2},
    ],
}
VIEWS = {   # (camera position, look at) in the Godot frame
    "vehicles": [((9.0, 2.4, -8.0), (4.0, 0.8, 0.0)), ((24.0, 3.0, -9.0), (16.0, 1.0, 0.0)), ((26.5, 2.2, 6.0), (25.0, 0.6, 0.0)), ((-4.0, 2.6, 9.0), (8.0, 0.8, 0.0))],
    "heavy": [((7.0, 2.8, -9.0), (1.0, 1.2, 0.0)), ((22.0, 3.5, -11.0), (14.0, 1.4, 2.0)), ((-6.0, 2.6, 9.0), (4.0, 1.2, 2.0))],
    "trams": [((-22.0, 3.0, 12.0), (-4.0, 1.6, 3.0)), ((20.0, 4.5, 17.0), (6.0, 1.4, 5.0)), ((2.0, 2.4, 15.5), (6.0, 1.6, 9.0))],
    "plant": [((8.0, 4.5, 16.0), (-0.5, 4.2, 0.0)), ((3.2, 1.6, 4.0), (0.0, 1.0, 0.0)), ((10.0, 2.6, 10.0), (11.0, 2.0, 0.0)),
              ((21.0, 2.0, 8.0), (20.5, 1.8, 0.0))],
}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", default="vehicles", choices=list(SETS))
    ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    builders.reset_material_cache()
    builders.FLOOD, builders.OUTDOOR, builders.WEAR = 0.7, True, 1.0
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.render.resolution_x, s.render.resolution_y = (int(v) for v in a.res.split("x"))
    s.cycles.samples = a.samples
    s.cycles.use_denoising = True
    s.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in s.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.025, 0.035, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    s.world = world
    ground = builders.material({"ph": "herringbone_brick", "tint": [0.55, 0.42, 0.42], "wet": 0.8, "puddles": 0.4})
    builders.box_aabb("ground", (-40.0, -0.4, -30.0), (60.0, 0.0, 30.0), ground)
    for pos, power, col in (((4.0, 6.5, 6.0), 2500.0, (1.0, 0.75, 0.5)), ((18.0, 6.5, 7.0), 2500.0, (1.0, 0.75, 0.5)), ((-6.0, 6.5, 6.0), 1500.0, (1.0, 0.75, 0.5))):
        ld = bpy.data.lights.new("lamp", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = power, col, 0.3
        ob = bpy.data.objects.new("lamp", ld)
        s.collection.objects.link(ob)
        ob.location = g2b(pos)
    sun = bpy.data.lights.new("moon", "SUN")
    sun.energy, sun.color = 0.25, (0.6, 0.7, 1.0)
    so = bpy.data.objects.new("moon", sun)
    s.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), 0.0, math.radians(30))
    for p in SETS[a.set]:
        builders.build_prop(p, 10.0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for i, (eye, look) in enumerate(VIEWS.get(a.set, [])):
        cd = bpy.data.cameras.new("cam")
        cd.lens_unit, cd.angle = "FOV", math.radians(48)
        cam = bpy.data.objects.new("cam", cd)
        s.collection.objects.link(cam)
        cam.location = g2b(eye)
        from mathutils import Vector
        d = Vector(g2b(look)) - Vector(g2b(eye))
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        s.camera = cam
        s.render.filepath = str(out / f"{a.set}_{i}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
