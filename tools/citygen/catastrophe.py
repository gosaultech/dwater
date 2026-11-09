# damned_waters/tools/citygen/catastrophe.py
# Purpose: the catastrophe pass (docs/city_aftermath.md): what the night did to each street, on top
# of what the evacuation left. Each street in STORIES gets its set pieces (the tram that derailed,
# the car that burned, the dead by the ambulance, the boards and the paint on the walls) and its
# live effects for the engine (the room's "fx": fire, smoke, sparks, flashing lights, a flicker);
# then the flood's leavings drift where water and panic would have dropped them, thick against the
# walls, the kerbs and the railing (drift); and, once the cameras are planned, each shot gets
# something close to its lens to look past (foreground), never where it would hide him.
# Idempotent: everything it adds is marked "catastrophe" and replaced on every run.
#
# ELI5: the night's story, told by the props: a crime-scene photographer's list of what's where, and
# why, laid out street by street before the cameras roll.
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "assets"))
import barricades  # noqa: E402
import cameras  # noqa: E402
import decals  # noqa: E402

MARK = "catastrophe"
# What the water left: (model, tip degrees or None for upright/random, big). Big things only off the
# lanes he walks (he'd walk through them: they're dressing, not walls).
DEBRIS = [("ph:can_rusted", 90, False), ("ph:plastic_bottle_gallon", 90, False), ("ph:bleach_bottle", 90, False),
          ("ph:plastic_container", None, False), ("ph:trashbag", None, False), ("ph:trashbag", None, False),
          ("ph:cardboard_box_01", 90, False), ("ph:bark_debris_01", None, False), ("ph:dry_branches_medium_01", None, False),
          ("ph:rubber_boots", 90, False), ("ph:compost_bag_02", None, False), ("ph:plastic_crate_01", 90, False),
          ("ph:plastic_jerrycan", 90, False), ("ph:metal_jerrycan", 90, False), ("ph:cement_bag", None, False),
          ("ph:old_tyre", 90, True), ("ph:wooden_crate_02", 20, True), ("ph:plastic_monobloc_chair_01", 90, True),
          ("ph:metal_trash_can", 90, True), ("ph:plastic_crate_03", None, True), ("ph:wooden_military_crate", None, True)]
# What can stand close to a lens without telling a different story from the street's.
FOREGROUND = [("ph:trashbag", None), ("ph:old_tyre", 90), ("ph:plastic_crate_02", None), ("ph:metal_trash_can", 90),
              ("ph:wooden_crate_02", 20), ("ph:compost_bags", None), ("ph:plastic_monobloc_chair_01", 90)]
SILT = {"ph": "brown_mud_02", "wet": 0.75, "puddles": 0.3}


def _decal(**spec):
    spec = dict(spec)
    spec["id"] = decals.decal_id(spec)
    return spec


def spray(x, y, z, yaw, w, h, text, color=(0.72, 0.04, 0.03), seed=1, out=0.012):
    """Words sprayed on a wall: the decal's foot at (x, y, z), facing yaw."""
    return {"type": "spray", "pos": [x, y, z], "yaw": yaw, "size": [w, h, 0.01], "collide": False, "out": out,
            "decal": _decal(style="spray", text=text, color=list(color), aspect=round(w / h, 2), seed=seed)}


def xcode(x, y, z, yaw, s, top, left, right, bottom, seed=2, out=0.012):
    return {"type": "spray", "pos": [x, y, z], "yaw": yaw, "size": [s, s, 0.01], "collide": False, "out": out,
            "decal": _decal(style="xcode", top=top, left=left, right=right, bottom=bottom, color=[0.95, 0.45, 0.02], seed=seed)}


def poster(x, y, z, yaw, text, photo=True, seed=3, w=0.42):
    return {"type": "spray", "pos": [x, y, z], "yaw": yaw, "size": [w, w / 0.71, 0.01], "collide": False, "out": 0.006,
            "decal": _decal(style="poster", text=text, photo=photo, seed=seed)}


def boards(x, z, yaw, w, h, y=0.3, x_brace=False, seed=9):
    return {"type": "boards", "pos": [x, y, z], "yaw": yaw, "size": [w, h, 0.05], "collide": False, "x": x_brace, "seed": seed}


def dead(x, z, yaw, variant=0, prone=False, blood=0.6, y=0.0):
    """One of the dead where they fell (the engine poses the cast's bodies: never rising)."""
    return {"pos": [x, y, z], "yaw": yaw, "variant": variant, "prone": prone, "blood": blood}


def drag(x0, z0, x1, z1, width=0.4):
    """A drag mark in blood from (x0, z0) to (x1, z1) (a decal on the street)."""
    L = math.hypot(x1 - x0, z1 - z0)
    return {"type": "blood", "pos": [round((x0 + x1) / 2, 2), 0.0, round((z0 + z1) / 2, 2)], "yaw": round(math.degrees(math.atan2(-(z1 - z0), x1 - x0)), 1),
            "size": [round(L, 2), 0.0, width], "smear": True, "collide": False}


def model(ref, x, z, yaw, y=0.0, tip=None, collide=False, scale=None):
    p = {"type": "model", "model": ref, "pos": [round(x, 2), round(y, 3), round(z, 2)], "yaw": round(yaw, 1), "collide": collide}
    if tip is not None:
        p["tip"] = tip
    if scale is not None:
        p["scale"] = scale
    return p


def tram_sections(tram):
    """Where a derailed tram's sections stand (city.tram's chain, in the room's frame): (x, z, yaw
    degrees, length) each; the engine's colliders and the camera planner go by these."""
    w, h, d = tram["size"]
    n, gap = 3, 0.25
    seg = (w - gap * (n - 1)) / n
    der = tram.get("derail", {})
    yaws = der.get("yaw", [0.0] * n)
    cx, cz, joint, out = -w / 2 + seg / 2, 0.0, None, []
    ty = math.radians(tram.get("yaw", 0.0))
    for i in range(n):
        a = math.radians(yaws[i] if i < len(yaws) else 0.0)
        if joint is not None:
            cx, cz = joint[0] + math.cos(a) * (gap / 2 + seg / 2), joint[1] - math.sin(a) * (gap / 2 + seg / 2)
        joint = (cx + math.cos(a) * (seg / 2 + gap / 2), cz - math.sin(a) * (seg / 2 + gap / 2))
        # the prop's own turn: local (x, z) -> room (x cos + z sin, -x sin + z cos)
        X = tram["pos"][0] + cx * math.cos(ty) + cz * math.sin(ty)
        Z = tram["pos"][2] - cx * math.sin(ty) + cz * math.cos(ty)
        out.append((X, Z, tram.get("yaw", 0.0) + math.degrees(a), seg))
    return out


# ── The streets' stories ────────────────────────────────────────────────────────────────────
def rokin_zuid(spec):
    """The last tram north derailed when the power went: its back still on the rails, the rest slewed
    across the road toward the water, windows gone, its wire down and arcing on the wet road. The water
    came up the basin and over the quay to the hips and left its line on everything; one boat tore
    loose. The shops are boarded and written on; the search team's marks are on the doors."""
    props, fx = [], []
    for p in spec["props"]:
        if p["type"] == "tram":
            p.update({"derail": {"yaw": [0.0, 9.0, 24.0], "roll": [0.0, 2.0, 6.5], "lift": [0.0, 0.0, 0.1]},
                      "dark": [2], "smashed": [1, 2], "pantograph": False, "board": "", "collide": False, "power": 170.0})
            for k, (x, z, yaw, seg) in enumerate(tram_sections(p)):   # (solid, and something the cameras keep clear of and show)
                props.append({"type": "tram_section", "pos": [round(x, 2), 0.0, round(z, 2)], "yaw": round(yaw, 1), "size": [round(seg, 2), 3.4, 2.4],
                              "hero": k > 0})
                if k == 1:
                    fx.append({"kind": "flicker", "pos": [round(x, 2), 1.8, round(z, 2)], "radius": 4.5, "amount": 0.45, "seed": 3})
        elif p["type"] == "canal_boat" and p.get("name") == "RONDVAART 7":
            p.update({"yaw": 78, "list": 5.0, "pos": [-3.9, -0.95, p["pos"][2]]})   # torn off its pier against the quay
    W = -90   # the fronts at x 26 face west: a decal's +z is -x
    props += [
        # the wire down across the road, arcing where it touches
        {"type": "wire_down", "pos": [10.2, 0.0, 41.8], "yaw": 0, "from": [3.8, 5.8, 4.6], "sag": 0.7, "slack": 3.2, "seed": 4, "collide": False, "hero": True},
        # the café: its windows boarded, its chairs piled against its door
        boards(25.9, 43.4, W, 2.3, 2.3, seed=11), boards(25.9, 48.7, W, 2.3, 2.3, seed=12),
        spray(25.86, 1.0, 43.4, W, 2.1, 0.8, "GEEN ETEN", (0.92, 0.9, 0.86), seed=13),
        spray(25.86, 1.1, 48.7, W, 2.1, 0.75, "GEEN WATER", (0.92, 0.9, 0.86), seed=14),
        # the hotel: its ground floor boarded, the survivors upstairs saying so
        boards(25.9, 20.3, W, 2.2, 2.4, seed=21), boards(25.9, 22.8, W, 2.2, 2.4, seed=22), boards(25.9, 25.3, W, 2.2, 2.4, seed=23),
        boards(25.9, 27.8, W, 2.2, 2.4, seed=24), boards(25.9, 30.3, W, 2.2, 2.4, seed=25),
        spray(25.86, 0.9, 25.3, W, 6.2, 1.7, "HOTEL VOL\n14 LEVEND · 2e VERD.", seed=26),
        # the houses: their doors searched and marked
        boards(25.9, 38.0, W, 1.3, 2.3, x_brace=True, seed=31),
        xcode(25.85, 0.9, 38.0, W, 1.15, "8/11 04:10", "BRW-3", "WATER", "2 DOOD", seed=32),
        xcode(25.95, 0.8, 54.0, W, 1.1, "8/11 04:40", "BRW-3", "GAS", "0", seed=33),
        # the museum's plinth, and the ticket office shuttered
        spray(25.95, 0.7, 66.0, W, 6.5, 0.9, "ZE KOMEN UIT HET WATER", (0.88, 0.88, 0.84), seed=41),
        model("ph:rollershutter_window_02", 25.75, 6.3, W),
        poster(25.6, 1.25, 5.7, W, "VERMIST\nSANNE DE VRIES · 9 JAAR\nLAATST GEZIEN: ROKIN\nZIE CENTRAAL", seed=42),
        poster(25.95, 1.3, 34.3, W, "VERMIST\nJOOST BAKKER · 71 JAAR\nIN PYJAMA, BLOTE VOETEN\nBEL 112", seed=43),
        poster(25.95, 1.35, 50.1, W, "MEDEDELING\nEVACUATIE\nVERLAAT DE STAD VIA CENTRAAL\nNEEM NIETS MEE\nDRINK GEEN KRAANWATER", photo=False, seed=44),
        # the bikes the water left wound into the railing, the rubbish against it
        {"type": "bike", "pos": [0.55, 0.0, 31.2], "yaw": 95, "roll": 70, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 150},
        {"type": "bike", "pos": [0.5, 0.25, 32.1], "yaw": 80, "roll": -60, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 151},
        {"type": "bike", "pos": [0.6, 0.0, 36.4], "yaw": 100, "roll": 82, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 152},
        # what floats in the basin
        model("ph:plastic_crate_01", -1.6, 33.5, 40, y=-1.02, tip=20), model("ph:old_tyre", -2.4, 35.2, 0, y=-1.05, tip=90),
        model("ph:wooden_crate_02", -1.2, 37.0, 70, y=-1.08, tip=10), model("ph:plastic_bottle_gallon", -0.8, 34.4, 10, y=-1.0, tip=90),
        model("ph:trashbag", -3.0, 31.0, 120, y=-1.06), model("ph:dry_branches_medium_01", -1.8, 29.0, 30, y=-1.0),
        # the flood's silt over the whole street
        {"type": "silt", "pos": [13.0, 0.0, 40.0], "size": [26.0, 0.0, 80.0], "material": dict(SILT), "cover": 0.5, "seed": 71, "collide": False},
    ]
    fx.append({"kind": "sparks", "pos": [10.2, 0.05, 41.8], "every": 2.4, "seed": 5})
    props.append(drag(8.1, 44.9, 7.4, 43.5))
    the_dead = [dead(7.2, 43.1, 160, 0, prone=True, blood=0.7),     # thrown through the tram's windscreen, crawled a metre
                dead(11.0, 56.6, 75, 1, blood=0.55),                # by the derailed sections
                dead(24.7, 21.0, 250, 2, prone=True, blood=0.8),    # under the hotel's boarded windows
                dead(3.1, 24.2, 20, 0, blood=0.0),                  # pulled out of the water onto the quay
                dead(20.9, 46.3, 300, 1, prone=True, blood=0.6),    # the taxi's driver, by his door
                dead(-2.6, 43.5, 120, 2, prone=True, blood=0.0, y=-1.06)]   # face down in the basin
    return props, fx, the_dead


def rokin_noord(spec):
    """The army's checkpoint at the Dam end, overrun; a car run into the quay and burned, still burning;
    the ambulance crew's dead lined up by their van, which still flashes, like the police van up the
    road; the police post papered with the missing; the metro's way in written over."""
    props, fx = [], []
    for p in spec["props"]:
        if p["type"] == "aid_post":
            p["covered"] = 2
    W = -90
    props += [
        {"type": "vehicle", "pos": [5.6, 0.0, 16.4], "yaw": 35, "size": [4.4, 1.45, 1.8], "livery": "car", "burnt": True, "collide": True, "hero": True},
        {"type": "glow", "pos": [5.6, 0.9, 16.4], "color": [1.0, 0.45, 0.12], "power": 700.0, "radius": 0.6, "collide": False},   # the fire's light, as the painting has it
        {"type": "scorch", "pos": [5.6, 0.0, 16.4], "yaw": 35, "size": [7.0, 0.0, 5.5], "collide": False},
        {"type": "body_bag", "pos": [8.2, 0.0, 26.3], "yaw": 0, "size": [1.85, 0.3, 0.62], "collide": False, "hero": True},
        {"type": "body_bag", "pos": [8.2, 0.0, 27.1], "yaw": 3, "size": [1.85, 0.3, 0.62], "collide": False},
        spray(25.95, 0.85, 17.0, W, 4.2, 0.9, "NIET NAAR BENEDEN", (0.92, 0.9, 0.86), seed=51),
        spray(25.95, 1.85, 17.4, W, 3.2, 0.55, "ZE ZITTEN IN HET WATER", (0.72, 0.04, 0.03), seed=52),
        poster(25.95, 1.3, 36.2, W, "VERMIST\nAYLA YILMAZ · 16 JAAR\nGROENE JAS\nLAATST GEZIEN: DAM", seed=53),
        poster(25.95, 1.62, 36.75, W, "VERMIST\nPIETER EN ROOS\nWIJ ZIJN IN NOORD\n— MAMA", photo=False, seed=54),
        poster(25.95, 1.15, 37.3, W, "VERMIST\nTHEO · 4 JAAR\nBLAUW REGENJASJE", seed=55),
        poster(25.95, 1.55, 37.85, W, "WIE HEEFT HAAR GEZIEN?\nMARIEKE · 34\nVERPLEEGKUNDIGE", seed=56),
        poster(25.95, 1.25, 38.4, W, "VERMIST\nOPA HENK · 88\nDEMENTEREND", seed=57),
        spray(13.2, 0.2, 1.75, 180, 2.6, 0.6, "DAM = DOOD", (0.72, 0.04, 0.03), seed=58, out=0.33),
        {"type": "silt", "pos": [13.0, 0.0, 40.0], "size": [26.0, 0.0, 80.0], "material": dict(SILT), "cover": 0.5, "seed": 72, "collide": False},
    ]
    fx += [{"kind": "fire", "pos": [5.6, 0.75, 16.4], "size": 1.3, "seed": 1},
           {"kind": "smoke", "pos": [5.6, 1.8, 16.4], "size": 2.2, "seed": 2},
           {"kind": "strobe", "pos": [22.3, 2.45, 46.0], "color": [0.15, 0.35, 1.0], "rate": 1.7, "seed": 3},
           {"kind": "strobe", "pos": [11.0, 2.75, 24.0], "color": [0.15, 0.35, 1.0], "rate": 2.1, "seed": 4}]
    the_dead = [dead(4.6, 9.4, 30, 0, blood=0.65),                   # at the checkpoint, where it was overrun
                dead(21.4, 6.2, 210, 2, prone=True, blood=0.75),
                dead(7.8, 18.7, 120, 1, prone=True, blood=0.5),      # by the car that burned
                dead(25.0, 37.2, 260, 2, blood=0.45),                # under the missing, at the police post
                dead(13.6, 22.4, 340, 0, prone=True, blood=0.85)]    # in the road by the ambulance
    return props, fx, the_dead


STORIES = {"rokin_zuid": rokin_zuid, "rokin_noord": rokin_noord}


def drift(spec, rng, n):
    """The flood's leavings: n things from DEBRIS dropped where the water slowed, against whatever
    stands (most within a metre of a wall, a kerb, the railing, a car), some out in the open; the big
    ones only off the lanes he walks."""
    xs, zs, ok = cameras.open_floor(spec)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    # how far each open cell is from anything solid or the room's edge (cells; 4-neighbour steps)
    dist = np.where(ok, 99, 0).astype(np.int32)
    for _ in range(8):
        d2 = dist.copy()
        d2[1:, :] = np.minimum(d2[1:, :], dist[:-1, :] + 1)
        d2[:-1, :] = np.minimum(d2[:-1, :], dist[1:, :] + 1)
        d2[:, 1:] = np.minimum(d2[:, 1:], dist[:, :-1] + 1)
        d2[:, :-1] = np.minimum(d2[:, :-1], dist[:, 1:] + 1)
        dist = np.where(ok, d2, 0)
    lanes = barricades.in_lanes(barricades.LANES.get(spec["id"], []), X, Z)
    w = np.where(ok, np.exp(-dist * cameras.CELL / 0.7) + 0.06, 0.0).ravel()
    if w.sum() <= 0:
        return []
    picks = rng.choice(len(w), size=min(n, int((w > 0).sum())), replace=False, p=w / w.sum())
    out = []
    for k in picks:
        i, j = divmod(int(k), len(zs))
        x, z = float(xs[i]) + rng.uniform(-0.1, 0.1), float(zs[j]) + rng.uniform(-0.1, 0.1)
        choices = [d for d in DEBRIS if not (d[2] and lanes[i, j])]
        ref, tip, _ = choices[rng.integers(len(choices))]
        out.append(model(ref, x, z, float(rng.uniform(0, 360)), tip=tip if tip is None or rng.random() < 0.8 else None))
    return out


def apply(spec):
    """The street's story: its set pieces and its live effects (before the cordons, so their barriers
    fence what now stands where, and before the cameras, which plan round it)."""
    tell = STORIES.get(spec["id"])
    if tell is None:   # (a street with no story yet: untouched)
        return spec
    spec["props"] = [p for p in spec.get("props", []) if not p.get(MARK)]
    spec["fx"] = [f for f in spec.get("fx", []) if not f.get(MARK)]
    spec["dead"] = [b for b in spec.get("dead", []) if not b.get(MARK)]
    props, fx, the_dead = tell(spec)
    for x in props + fx + the_dead:
        x[MARK] = True
    spec["props"] += props
    spec["fx"] += fx
    spec["dead"] += the_dead
    return spec


def leavings(spec, n=180):
    """The flood's leavings, drifted (after the cordons: round their barriers too)."""
    if spec["id"] not in STORIES:
        return spec
    spec["props"] = [p for p in spec["props"] if not p.get(MARK + "_drift")]
    rng = np.random.default_rng(sum(map(ord, spec["id"])))   # (the same street, the same mess, every run)
    for p in drift(spec, rng, n):
        p[MARK] = p[MARK + "_drift"] = True
        spec["props"].append(p)
    return spec


def foreground(spec, per_shot=1):
    """Something close to each shot's lens to look past (RE's cameras almost always have it): low in
    a bottom corner of the picture, 1.5-3.5 m from the lens, on floor he can't walk (off the lanes),
    and only where it hides him from no shot of the room."""
    if spec["id"] not in STORIES:
        return spec
    spec["props"] = [p for p in spec["props"] if not p.get(MARK + "_fg")]
    xs, zs, ok = cameras.open_floor(spec)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    lanes = barricades.in_lanes(barricades.LANES.get(spec["id"], []), X, Z)
    floor_x, floor_z, floor = cameras.floor_grid(spec)
    FX, FZ = np.meshgrid(floor_x, floor_z, indexing="ij")
    targets = []   # every shot's floor, at his chest, as each camera sees it
    for s in spec["shots"]:
        (zx0, zz0), (zx1, zz1) = s["zone"]["min"], s["zone"]["max"]
        sel = floor & (FX >= zx0) & (FX <= zx1) & (FZ >= zz0) & (FZ <= zz1)
        pts = np.stack([FX[sel], np.full(sel.sum(), 1.45), FZ[sel]], axis=1)
        targets.append((np.array(s["pos"], float), pts[:: max(1, len(pts) // 150)]))
    rng = random.Random(spec["id"] + "fg")
    added = []
    for s in spec["shots"]:
        c = np.array(s["pos"], float)
        f = np.array(s["look_at"], float) - c
        f /= np.linalg.norm(f)
        r = np.cross(f, [0.0, 1.0, 0.0])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        tv = math.tan(math.radians(s["fov"]) / 2)
        cand = []
        for x, z in zip(X[ok & ~lanes], Z[ok & ~lanes]):
            d = np.array([x, 0.25, z]) - c
            depth = d @ f
            if not 1.5 < np.hypot(x - c[0], z - c[2]) < 3.6 or depth <= 0.5:
                continue
            px, py = (d @ r) / depth / (tv * 16 / 9), (d @ u) / depth / tv
            if 0.45 < abs(px) < 0.95 and -0.98 < py < -0.45:   # low in a bottom corner
                cand.append((abs(abs(px) - 0.72) + abs(py + 0.75), float(x), float(z)))
        cand.sort()
        placed = 0
        for _, x, z in cand[:40]:
            ref, tip = FOREGROUND[rng.randrange(len(FOREGROUND))]
            box = [(x, z, 0.45, 0.45, 0.0, 0.0, 1.0, "fg")]   # a man-high-ish lump, to test sight against
            hides = any(cameras._segment_hits(cam, pts, box).mean() > 0.01 for cam, pts in targets if len(pts))
            if hides or any(math.hypot(x - a["pos"][0], z - a["pos"][2]) < 1.2 for a in added):
                continue
            p = model(ref, x, z, rng.uniform(0, 360), tip=tip)
            p[MARK + "_fg"] = True
            added.append(p)
            placed += 1
            if placed >= per_shot:
                break
    spec["props"] += added
    return spec
