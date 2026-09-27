# damned_waters/tools/blender/render_rooms.py
# Purpose: render every camera shot of every room into two images:
#   <shot>_color.png    the pre-rendered background (Cycles, AgX)
#   <shot>_depth16.png  planar camera depth / DEPTH_MAX_M, 16-bit grayscale
# Godot composites the 3D characters against the depth image, so a character
# walking behind a table is hidden by the *painted* table.
#
# Run (Blender app):   blender -b -P tools/blender/render_rooms.py -- --quality final
# Run (bpy module):    python tools/blender/render_rooms.py --quality preview
# Normally you run tools/pipeline/build_backgrounds.py, which calls this.
import argparse
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "pipeline"))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import builders  # noqa: E402
import roomspec  # noqa: E402
from roomspec import g2b  # noqa: E402

REPO = HERE.parent.parent
QUALITY = {  # samples, bounces, volumetric density
    "preview": dict(samples=12, bounces=4, volume=0.0),
    "ship": dict(samples=20, bounces=6, volume=0.0),
    "final": dict(samples=256, bounces=8, volume=0.012),
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rooms", default="", help="comma list; default = all")
    ap.add_argument("--shots", default="", help="comma list of shot ids; default = all")
    ap.add_argument("--quality", choices=QUALITY, default="preview")
    ap.add_argument("--res", default="1280x720", help="must be 16:9")
    ap.add_argument("--out", default=str(REPO / "pipeline_out" / "renders"))
    ap.add_argument("--specs", default=str(REPO / "game" / "data" / "rooms"))
    ap.add_argument("--gpu", action="store_true", help="try Metal/OptiX/CUDA/HIP")
    return ap.parse_args(argv)


def enable_gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            if any(d.type == backend for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                print(f"[render] GPU backend: {backend}")
                return True
        except TypeError:
            continue
    print("[render] no GPU backend found, using CPU")
    return False


def new_scene(spec, q, res):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    builders.reset_material_cache()
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.render.resolution_x, s.render.resolution_y = res
    s.render.resolution_percentage = 100
    s.cycles.max_bounces = q["bounces"]
    s.cycles.caustics_reflective = False
    s.cycles.caustics_refractive = False
    s.cycles.blur_glossy = 1.0
    world = bpy.data.worlds.new("world")
    if world.node_tree is None:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
    wc = spec.get("world", {"color": [0.01, 0.01, 0.015], "strength": 0.5})
    bg.inputs["Color"].default_value = (*wc["color"], 1)
    bg.inputs["Strength"].default_value = wc["strength"]
    out = world.node_tree.nodes.get("World Output") or world.node_tree.nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(bg.outputs[0], out.inputs["Surface"])
    if q["volume"] > 0:
        vs = world.node_tree.nodes.new("ShaderNodeVolumeScatter")
        vs.inputs["Density"].default_value = q["volume"]
        world.node_tree.links.new(vs.outputs[0], out.inputs["Volume"])
    s.world = world
    return s


def add_light(spec_light, i):
    kind = spec_light["kind"]
    ld = bpy.data.lights.new(f"light_{i}", {"point": "POINT", "spot": "SPOT", "area": "AREA", "sun": "SUN"}[kind])
    ld.color = spec_light["color"]
    ld.energy = spec_light["blender_power"]
    ob = bpy.data.objects.new(f"light_{i}", ld)
    bpy.context.scene.collection.objects.link(ob)
    if kind == "sun":
        d = Vector(g2b(spec_light["dir_from"])).normalized()
        ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        ld.angle = math.radians(spec_light.get("angle", 1.0))
        return ob
    ob.location = g2b(spec_light["pos"])
    if kind == "point":
        ld.shadow_soft_size = spec_light.get("radius", 0.05)
    if kind == "area":
        ld.size = spec_light.get("size", 1.0)
    if kind == "spot":
        ld.spot_size = math.radians(spec_light.get("spot_angle", 60))
        ld.spot_blend = 0.4
    if "look_at" in spec_light:
        d = Vector(g2b(spec_light["look_at"])) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def add_camera(shot):
    """Vertical sensor fit + lens from vertical FOV == Godot Camera3D KEEP_HEIGHT."""
    cd = bpy.data.cameras.new(f"cam_{shot['id']}")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cd.lens = cd.sensor_height / (2.0 * math.tan(math.radians(shot["fov"]) / 2.0))
    cd.clip_start, cd.clip_end = 0.05, 200.0
    ob = bpy.data.objects.new(f"cam_{shot['id']}", cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = g2b(shot["pos"])
    d = Vector(g2b(shot["look_at"])) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def depth_material():
    """Emission = planar view depth / DEPTH_MAX. With the Raw view transform the
    number lands in the PNG untouched: this *is* a measuring tape, not a picture."""
    m = bpy.data.materials.new("depth_override")
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    cd = nt.nodes.new("ShaderNodeCameraData")
    dv = nt.nodes.new("ShaderNodeMath")
    dv.operation, dv.use_clamp = "DIVIDE", True
    dv.inputs[1].default_value = roomspec.DEPTH_MAX_M
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(cd.outputs["View Z Depth"], dv.inputs[0])
    nt.links.new(dv.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def render_beauty(s, q, path, exposure=0.6):
    s.view_layers[0].material_override = None
    s.cycles.samples = q["samples"]
    s.cycles.use_denoising = True
    s.cycles.denoiser = "OPENIMAGEDENOISE"
    s.cycles.filter_width = 1.5
    s.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            s.view_settings.look = look
            break
        except TypeError:
            continue
    s.view_settings.exposure = exposure
    s.render.dither_intensity = 1.0
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"
    s.render.image_settings.color_depth = "8"
    s.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def render_depth(s, path, depth_mat, world_white):
    keep_world = s.world
    s.world = world_white
    s.view_layers[0].material_override = depth_mat
    s.cycles.samples = 1
    s.cycles.use_denoising = False
    s.cycles.filter_width = 0.01  # no anti-aliasing: edges must not blend depths
    s.view_settings.view_transform = "Raw"
    s.view_settings.look = "None"
    s.view_settings.exposure = 0.0
    s.render.dither_intensity = 0.0
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "BW"
    s.render.image_settings.color_depth = "16"
    s.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    s.world = keep_world
    s.view_layers[0].material_override = None


def white_world():
    w = bpy.data.worlds.new("depth_world")
    if w.node_tree is None:
        w.use_nodes = True
    bg = w.node_tree.nodes.get("Background") or w.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bg.inputs["Strength"].default_value = 1.0
    out = w.node_tree.nodes.get("World Output") or w.node_tree.nodes.new("ShaderNodeOutputWorld")
    w.node_tree.links.new(bg.outputs[0], out.inputs["Surface"])
    return w


def build_room(spec):
    builders.build_shell(spec)
    builders.build_water(spec)
    builders.build_exterior(spec, random.Random(spec["id"]))
    for p in spec.get("props", []):
        builders.build_prop(p, spec["height"])
    for i, light in enumerate(spec.get("lights", [])):
        add_light(light, i)


def main():
    a = parse_args()
    q = QUALITY[a.quality]
    res = tuple(int(v) for v in a.res.lower().split("x"))
    assert abs(res[0] / res[1] - 16 / 9) < 1e-3, "backgrounds must be 16:9 (Godot viewport is 16:9)"
    specs = roomspec.load_all(a.specs)
    wanted = [r for r in a.rooms.split(",") if r] or list(specs)
    shots_wanted = {s for s in a.shots.split(",") if s}
    for room_id in wanted:
        spec = specs[room_id]
        s = new_scene(spec, q, res)
        if a.gpu and enable_gpu():
            s.cycles.device = "GPU"
        build_room(spec)
        dmat, wworld = depth_material(), white_world()
        out_dir = Path(a.out) / room_id
        out_dir.mkdir(parents=True, exist_ok=True)
        for shot in spec["shots"]:
            if shots_wanted and shot["id"] not in shots_wanted:
                continue
            s.camera = add_camera(shot)
            t0 = time.time()
            render_beauty(s, q, out_dir / f"{shot['id']}_color.png", spec.get("render", {}).get("exposure", 0.6))
            render_depth(s, out_dir / f"{shot['id']}_depth16.png", dmat, wworld)
            print(f"[render] {room_id}/{shot['id']} {a.quality} {res[0]}x{res[1]} in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
