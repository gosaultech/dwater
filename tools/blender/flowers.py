# damned_waters/tools/blender/flowers.py
# Tulips in their buckets: each bloom a cup of six tepals (three outside, three in between, their
# tips scalloped), green where it meets the stem, a little light through the petals; stems bending
# out of the bucket into a domed bunch; broad grey-green leaves. One mesh per colour, so a stall of
# a thousand blooms builds in a blink.
import math

import bpy

import kit
from street import Acc, M

PROFILE = [(0.0, 0.004), (0.08, 0.012), (0.25, 0.021), (0.5, 0.026), (0.75, 0.024), (0.9, 0.02), (1.0, 0.017)]   # (height share, radius m)
HEIGHT, RINGS, SEGS = 0.062, 10, 24


def _radius(t):
    for (t0, r0), (t1, r1) in zip(PROFILE, PROFILE[1:]):
        if t <= t1:
            return r0 + (r1 - r0) * (t - t0) / (t1 - t0)
    return PROFILE[-1][1]


def _cup(phase, scale):
    """One layer of three tepals (tips at `phase` + 0, 120, 240 degrees), as (x, y, z, t) points."""
    pts = []
    for k in range(RINGS + 1):
        t = k / RINGS
        top = max(0.0, (t - 0.55) / 0.45)
        for j in range(SEGS):
            a = 2 * math.pi * j / SEGS
            c = math.cos(3 * (a - phase))
            r = _radius(t) * scale * (1 + 0.07 * c * top * top)
            y = HEIGHT * scale * (t + 0.16 * c * top ** 1.5)
            pts.append((r * math.cos(a), y, r * math.sin(a), t))
    return pts


HEAD = [_cup(0.0, 1.0), _cup(math.pi / 3, 0.93)]   # (outer, inner)


def _faces(base):
    f = []
    for k in range(RINGS):
        for j in range(SEGS):
            i0, i1 = base + k * SEGS + j, base + k * SEGS + (j + 1) % SEGS
            f.append((i0, i1, i1 + SEGS, i0 + SEGS))
    return f


def _material(col):
    name = "tulip_%d_%d_%d" % tuple(int(c * 100) for c in col)
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeAttribute")
    t.attribute_name = "t"
    v = nt.nodes.new("ShaderNodeAttribute")
    v.attribute_name = "v"
    ramp = nt.nodes.new("ShaderNodeValToRGB")   # green at the stem, the petal's colour by a third of the way up
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.0, (0.2, 0.32, 0.08, 1.0)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.32, (*col, 1.0)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(t.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mul.inputs["A"])
    nt.links.new(v.outputs["Color"], mul.inputs["B"])
    nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.42
    bsdf.inputs["Subsurface Weight"].default_value = 0.35
    bsdf.inputs["Subsurface Scale"].default_value = 0.006
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = 0.2
    return m


def _place(p, up, at, s):
    """A head point (x, y, z) scaled by s, its axis turned from +y to `up`, moved to `at`."""
    x, y, z = p[0] * s, p[1] * s, p[2] * s
    ux, uy, uz = up
    ax, az = uz, -ux   # rotation axis: y cross up (horizontal)
    sin_a = math.hypot(ax, az)
    if sin_a > 1e-6:
        ax, az = ax / sin_a, az / sin_a
        cos_a = uy
        dot = ax * x + az * z
        cx, cy, cz = -az * y, az * x - ax * z, ax * y   # axis (ax, 0, az) cross p
        x, y, z = (x * cos_a + cx * sin_a + ax * dot * (1 - cos_a), y * cos_a + cy * sin_a, z * cos_a + cz * sin_a + az * dot * (1 - cos_a))
    return (at[0] + x, at[1] + y, at[2] + z)


def bunches(root, pots, rng, colours):
    """Tulips in each pot [(x, y_rim, z, radius, colour index)]: stems out of the water bending into a
    dome, a bloom on each, leaves over the rim."""
    heads = {}
    stems, leaves = Acc(), Acc()
    for x, y, z, rad, k in pots:
        n = rng.randint(12, 18)
        for _ in range(n):
            a, d = rng.uniform(0, 2 * math.pi), rad * 0.75 * math.sqrt(rng.random())
            fx, fz = x + math.cos(a) * d * 0.5, z + math.sin(a) * d * 0.5    # where it leaves the water
            hx, hz = x + math.cos(a) * d * 1.5, z + math.sin(a) * d * 1.5    # where it opens, out over the rim
            hy = y + rng.uniform(0.2, 0.27) - 0.25 * d
            mx, my, mz = (fx + hx) / 2, (y + hy) / 2 + 0.02, (fz + hz) / 2
            stems.rod((fx, y - 0.08, fz), (mx, my, mz), 0.0028, 0.0028, 5)
            stems.rod((mx, my, mz), (hx, hy, hz), 0.0028, 0.0025, 5)
            ux, uy, uz = hx - mx, hy - my, hz - mz
            L = math.sqrt(ux * ux + uy * uy + uz * uz)
            up = (ux / L, uy / L, uz / L)
            verts, faces, ts, vs = heads.setdefault(k, ([], [], [], []))
            s, bright = rng.uniform(0.85, 1.1), rng.uniform(0.8, 1.0)
            for layer in HEAD:
                base = len(verts)
                for p in layer:
                    verts.append(_place(p, up, (hx, hy - 0.004, hz), s))
                    ts.append(p[3])
                    vs.append(bright)
                faces.extend(_faces(base))
            if rng.random() < 0.6:   # a broad leaf from low on the stem, out over the rim
                la = a + rng.uniform(-0.6, 0.6)
                ca, sa = math.cos(la), math.sin(la)
                L0, w = rng.uniform(0.14, 0.2), rng.uniform(0.016, 0.024)
                prev = None
                for q in range(4):
                    f = q / 3
                    px, pz = fx + ca * (0.02 + L0 * 0.7 * f), fz + sa * (0.02 + L0 * 0.7 * f)
                    py = y - 0.02 + L0 * (0.9 * f - 0.45 * f * f)
                    hw = w * math.sin(math.pi * (0.15 + 0.7 * f)) if q < 3 else 0.001
                    pair = ((px - sa * hw, py, pz + ca * hw), (px + sa * hw, py, pz - ca * hw))
                    if prev:
                        leaves.quad(prev[0], prev[1], pair[1], pair[0])
                    prev = pair
    stems.build("tulip_stems", M({"color": [0.16, 0.32, 0.1], "rough": 0.5, "bevel": 0}), root)
    leaves.build("tulip_leaves", M({"color": [0.24, 0.36, 0.2], "rough": 0.5, "noise": 0.15, "bevel": 0}), root, smooth=True)
    for k, (verts, faces, ts, vs) in heads.items():
        ob = kit.mesh("tulips", verts, faces, _material(colours[k]), root, smooth=True)
        me = ob.data
        at = me.attributes.new("t", "FLOAT", "POINT")
        av = me.attributes.new("v", "FLOAT_COLOR", "POINT")
        for i, (tv, bv) in enumerate(zip(ts, vs)):
            at.data[i].value = tv
            av.data[i].color = (bv, bv, bv, 1.0)
