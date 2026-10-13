# damned_waters/tools/citygen/common.py
# Shared helpers for the area generators (RoomSpec JSON for the city's districts).
from pathlib import Path
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import facade as fz  # noqa: E402

import os
R = os.environ.get("DW_ROOMS", str(Path(__file__).resolve().parents[2] / "game" / "data" / "rooms") + "/")
SKY = {"hdri": "kloppenheim_07_puresky", "strength": 0.045, "camera": 0.1, "tint": [1.0, 0.76, 0.55]}
ROOMS = ["warm_bar", "fireplace", "small_empty_room_2", "christmas_photo_studio_04", "warm_restaurant_night", "unfinished_office_night"]
SUN = {"kind": "sun", "dir_from": [-0.35, 0.55, 1.0], "color": [0.55, 0.66, 1.0], "blender_power": 0.12, "godot_energy": 0.25, "angle": 2.0}
WET = lambda ph, tint, wet=0.7, pud=0.3: {"ph": ph, "tint": tint, "wet": wet, "puddles": pud * 0.6, "puddle_scale": 0.9}
PAVERS = WET("square_concrete_pavers", [0.75, 0.74, 0.72], 0.55, 0.2)
BRICKS = WET("herringbone_brick", [0.8, 0.72, 0.66], 0.8, 0.45)
LOOK = {   # sign, frame, font, awning
    "cafe": ([1.0, 0.8, 0.5], [0.2, 0.05, 0.035], "DejaVuSerif-BoldItalic.ttf", None),
    "coffeeshop": ([0.35, 1.0, 0.4], [0.03, 0.12, 0.05], "DejaVuSans-Bold.ttf", [[0.05, 0.3, 0.08], [0.85, 0.75, 0.1]]),
    "restaurant": ([1.0, 0.3, 0.18], [0.06, 0.05, 0.05], "DejaVuSerif-Bold.ttf", [[0.45, 0.06, 0.05], [0.78, 0.74, 0.66]]),
    "bar": ([1.0, 0.2, 0.6], [0.03, 0.03, 0.04], "DejaVuSans-Bold.ttf", None),
    "hotel": ([0.95, 0.9, 0.8], [0.12, 0.1, 0.08], "DejaVuSerif-Bold.ttf", None),
    "pharmacy": ([0.85, 1.0, 0.9], [0.02, 0.2, 0.1], "DejaVuSans-Bold.ttf", None),
    "souvenir": ([1.0, 0.55, 0.1], [0.05, 0.08, 0.25], "DejaVuSans-Bold.ttf", [[0.9, 0.4, 0.05], [0.92, 0.9, 0.85]]),
    "snack": ([1.0, 0.85, 0.2], [0.35, 0.04, 0.03], "DejaVuSans-Bold.ttf", [[0.75, 0.05, 0.04], [0.95, 0.85, 0.2]]),
    "books": ([0.95, 0.88, 0.7], [0.06, 0.12, 0.1], "DejaVuSerif-Bold.ttf", [[0.05, 0.2, 0.15], [0.8, 0.75, 0.62]]),
    "cinema": ([1.0, 0.78, 0.35], [0.33, 0.22, 0.11], "DejaVuSerif-Bold.ttf", None),
    "police": ([0.95, 0.97, 1.0], [0.02, 0.06, 0.25], "DejaVuSans-Bold.ttf", None),
    "metro": ([1.0, 1.0, 1.0], [0.3, 0.32, 0.35], "DejaVuSans-Bold.ttf", None),
    "jeweller": ([1.0, 0.85, 0.5], [0.05, 0.05, 0.06], "DejaVuSerif-Bold.ttf", None),
}
ROOM_OF = {"cafe": "warm_bar", "coffeeshop": "warm_bar", "restaurant": "warm_restaurant_night", "bar": "warm_bar", "hotel": "fireplace",
           "pharmacy": "unfinished_office_night", "souvenir": "christmas_photo_studio_04", "snack": "warm_restaurant_night",
           "books": "fireplace", "cinema": "warm_bar", "police": "unfinished_office_night", "metro": "unfinished_office_night",
           "jeweller": "fireplace"}


def shop(name, kind, blade=None, door_bay=1, power=85.0, awning=True, **kw):
    sign, frame, font, aw = LOOK[kind]
    s = {"name": name, "kind": kind, "room": ROOM_OF[kind], "sign": sign, "frame": frame, "font": font, "glow": 0.3,
         "power": power * 0.32, "door_bay": door_bay, "neon": kind in ("bar", "coffeeshop")}
    if blade is not False:
        s["blade"] = blade or name.split()[-1]
    if aw and awning:
        s["awning"] = aw
    s.update(kw)
    return s


def front(facing, a, b, line, storeys, bays, gable, seed, shp=None, **kw):
    f = {"facing": facing, "storeys": storeys, "bays": bays, "gable": gable, "seed": seed, "lit": 0.3}
    f.update({"z0": a, "z1": b, "x": line} if facing in ("east", "west") else {"x0": a, "x1": b, "z": line})
    if shp:
        f["shop"] = shp
        f["stoop"] = 0.0
    else:
        f.update({"door_bay": kw.pop("door_bay", 1), "stoop": kw.pop("stoop", 0.5)})
    f.update(kw)
    return f


def shop_doorway(f, offset=0.0):
    """The door of an enterable shop on front f: (centre along the street's wall, width, height, u)."""
    s0 = f["storeys"][0]
    W = (f["x1"] - f["x0"]) if f["facing"] in ("south", "north") else (f["z1"] - f["z0"])
    sub = W - 2 * offset
    uc, wd, hd = fz.shop_door(sub, s0, f["shop"].get("door_bay"), f["shop"].get("top", 2.8))
    return fz.along_wall(f, offset + uc), wd, hd


def table_group(props, x, z, rng, n=2, fallen=0, yaw_choices=(0, 10, -10, 90, 80)):
    for i in range(n):
        p = {"type": "model", "model": "ph:outdoor_table_chair_set_01", "pos": [round(x + i * 1.6 + rng.uniform(-0.2, 0.2), 2), 0.0,
             round(z + rng.uniform(-0.25, 0.25), 2)], "yaw": rng.choice(yaw_choices), "scale": 1.0, "size": [1.0, 0.8, 1.0]}
        if i < fallen:
            p["roll"] = 84
        props.append(p)


DISTRICT = {"storey": 11, "name": "district 2: the Munt"}


def street_room(rid, name, origin, size, height, desc):
    STOREY = DISTRICT["storey"]
    return {"_file": f"damned_waters/game/data/rooms/{rid}.json — RoomSpec for {name} (the city, {DISTRICT['name']}): {desc} "
                     "Modelled after openly licensed photographs; every business name is made up, the landmarks keep theirs. "
                     "The power is still on; nobody is there. Outdoor (street.py, city.py and landmarks.py build it). Single source "
                     "of truth for Blender (render) and the engine (collision, cameras, things).",
            "id": rid, "display_name": name, "storey": STOREY, "origin": origin,
            "bounds": {"min": [0.0, 0.0], "max": list(size)}, "height": height,
            "materials": {"floor": {"color": [0.2, 0.2, 0.2]}, "wall": {"color": [0.2, 0.2, 0.2]}, "ceiling": {"color": [0.2, 0.2, 0.2]}},
            "footsteps": "marble", "ambience": "amb_street_rain", "move_scale": 1.0, "world": {"color": [0.014, 0.019, 0.036], "strength": 1.0},
            "sky": SKY, "render": {"exposure": 0.85, "bloom": {"threshold": 0.9, "strength": 0.4, "size": 0.55,
                                                            "haze": {"color": [0.045, 0.052, 0.068], "start": 12.0, "depth": 85.0, "strength": 0.5}}}}


def shop_room(rid, name, origin, size, height, desc, materials, exposure=1.0):
    STOREY = DISTRICT["storey"]
    return {"_file": f"damned_waters/game/data/rooms/{rid}.json — RoomSpec for {name} (the city, {DISTRICT['name']}): {desc} "
                     "Its front wall is the street's shopfront (\"facade\": the street builds it); its door is the street's. Every "
                     "business name is made up. Single source of truth for Blender (render) and the engine (collision, cameras, things).",
            "id": rid, "display_name": name, "storey": STOREY, "origin": origin,
            "bounds": {"min": [0.0, 0.0], "max": list(size)}, "height": height, "materials": materials,
            "footsteps": "marble", "ambience": "amb_cellar", "move_scale": 1.0, "world": {"color": [0.01, 0.012, 0.016], "strength": 0.5},
            "render": {"exposure": exposure, "bloom": {"threshold": 0.95, "strength": 0.25, "size": 0.5}}}


def walk_in(props):
    """An aid post is a tent to walk into: what stands in it is solid (the table, the stretchers,
    whoever lies under a sheet, the generator outside), not the tent's whole footprint."""
    import math
    out = []
    for p in props:
        if p["type"] != "aid_post" or p.get("collide") is False:
            continue
        p["collide"] = False
        w, d = p["size"][0], p["size"][2]
        n, cov = p.get("stretchers", 2), p.get("covered", 1)
        parts = [(0.0, -d / 2 + 0.65, 1.8, 0.7)]                       # the table
        if n:
            x0, x1 = -w / 2 + 0.3, -w / 2 + 0.9 + (n - 1) * 1.0
            parts.append(((x0 + x1) / 2, 0.0, x1 - x0, 2.2))           # the stretchers
        if cov:
            x0, x1 = w / 2 - 0.7 - (cov - 1) * 0.9 - 0.3, w / 2 - 0.4
            parts.append(((x0 + x1) / 2, 0.2, x1 - x0, 1.9))           # under the sheets
        parts.append((-w / 2 - 1.2, d / 2 - 0.6, 0.7, 0.5))            # the generator
        t = math.radians(p.get("yaw", 0.0))
        for lx, lz, sw, sd in parts:
            out.append({"type": "collider", "pos": [round(p["pos"][0] + lx * math.cos(t) + lz * math.sin(t), 3), 0.0,
                                                     round(p["pos"][2] - lx * math.sin(t) + lz * math.cos(t), 3)],
                        "yaw": p.get("yaw", 0.0), "size": [round(sw, 3), 1.0, round(sd, 3)]})
    props.extend(out)


FINISH = {"wall": "beige_wall_001", "ceiling": "ceiling_interior"}   # real plaster, a real office ceiling (CC0 photos)
CLUTTER = ["ph:cardboard_box_01", "ph:plastic_crate_03", "ph:trashbag", "ph:cardboard_box_01", "ph:potted_plant_04", "ph:plastic_crate_02"]
ON_WALLS = [("ph:wall_clock", 2.15), ("ph:hanging_picture_frame_02", 1.75)]


def finish_indoors(spec):
    """An interior as photographed, not modelled: its painted walls and ceiling a real plaster's and a
    real ceiling's (tinted as the room asks), its lights smaller and its exposure lower (pools of
    light in a dim shop at night, not a lit box), and the clutter of a place left in a hurry."""
    import math
    if spec.get("outdoor"):
        return
    m = spec.get("materials", {})
    for k, ph in FINISH.items():
        v = m.get(k)
        if isinstance(v, dict) and "color" in v and "ph" not in v:
            m[k] = {"ph": ph, "tint": [round(min(1.0, c / 0.78), 3) for c in v["color"]], "rough": v.get("rough", 0.8)}
    r = spec.setdefault("render", {})
    r["exposure"] = round(r.get("exposure", 1.0) * 0.82, 3)
    for L in spec.get("lights", []):
        if L.get("kind") == "area" and L.get("size", 1.0) > 0.7:
            L["size"] = round(L["size"] * 0.55, 3)
    rng = random.Random("clutter " + spec["id"])
    (bx0, bz0), (bx1, bz1) = spec["bounds"]["min"], spec["bounds"]["max"]
    W, D = bx1 - bx0, bz1 - bz0
    doors = []
    for side, w in spec.get("walls", {}).items():
        for o in w.get("openings", []):
            c = o.get("center", 0.0)
            doors.append({"north": (c, 0.0), "south": (c, D), "west": (0.0, c), "east": (W, c)}[side])
    keep = [(i["pos"][0], i["pos"][2]) for i in spec.get("interactables", [])] + [(e["pos"][0], e["pos"][2]) for e in spec.get("enemies", [])]
    boxes = []
    for p in spec.get("props", []):
        if "size" in p and p["type"] not in ("leaflets", "luggage", "broken_glass", "strip_light", "wall_sign", "poster"):
            boxes.append((p["pos"][0], p["pos"][2], p["size"][0] / 2, p["size"][-1] / 2, math.radians(p.get("yaw", 0.0))))

    def free(x, z, r):
        if any(math.hypot(x - a, z - b) < 1.7 for a, b in doors) or any(math.hypot(x - a, z - b) < 1.3 for a, b in keep):
            return False
        for cx, cz, hx, hz, t in boxes:
            dx, dz = x - cx, z - cz
            lx, lz = dx * math.cos(t) - dz * math.sin(t), dx * math.sin(t) + dz * math.cos(t)
            if abs(lx) < hx + r and abs(lz) < hz + r:
                return False
        return True
    fronts = {s_ for s_, w in spec.get("walls", {}).items() if w.get("facade")}
    sides = [s_ for s_ in ("north", "south", "east", "west") if s_ not in fronts]
    big = W * D > 200   # (a hall gets its junk in heaps, not lined round the walls)
    n, added = (min(16, int(W * D / 25)) if big else max(3, int(W * D / 9))), 0
    heap = None
    for _ in range(n * 10):
        if added >= n or not sides:
            break
        if big and heap and rng.random() < 0.7:
            side, u = heap[0], heap[1] + rng.uniform(-0.9, 0.9)
        else:
            side = rng.choice(sides)
            u = rng.uniform(0.7, (W if side in ("north", "south") else D) - 0.7)
            heap = (side, u)
        if not 0.7 < u < (W if side in ("north", "south") else D) - 0.7:
            continue
        x, z, yaw = {"north": (u, 0.42, 0), "south": (u, D - 0.42, 180), "west": (0.42, u, 90), "east": (W - 0.42, u, -90)}[side]
        if not free(x, z, 0.35):
            continue
        spec["props"].append({"type": "model", "model": rng.choice(CLUTTER), "pos": [round(x, 2), 0.0, round(z, 2)],
                              "yaw": round(yaw + rng.uniform(-30, 30)), "scale": round(rng.uniform(0.8, 1.0), 2), "collide": False})
        boxes.append((x, z, 0.35, 0.35, 0.0))
        added += 1
    for ref, y in ON_WALLS if KINDS.get(spec["id"]) != "church" else []:   # a clock, a picture, on walls with nothing against them
        for _ in range(20):
            side = rng.choice(sides) if sides else None
            if side is None:
                break
            u = rng.uniform(1.0, (W if side in ("north", "south") else D) - 1.0)
            x, z, yaw = {"north": (u, 0.03, 0), "south": (u, D - 0.03, 180), "west": (0.03, u, 90), "east": (W - 0.03, u, -90)}[side]
            if any(math.hypot(x - a, z - b) < 1.6 for a, b in doors) or not free(x, z, 0.5):
                continue
            spec["props"].append({"type": "model", "model": ref, "pos": [round(x, 2), y, round(z, 2)], "yaw": yaw, "scale": 1.0, "collide": False})
            boxes.append((x, z, 0.5, 0.5, 0.0))
            break
    dress(spec, rng, free, boxes, W, D, sides, fronts)


KINDS = {"apotheek": "shop", "drogist": "shop", "juwelier": "shop", "wapenhandel": "shop", "warenhuis": "shop",
         "souvenirwinkel": "shop", "wisselkantoor": "shop", "politiepost": "office", "beveiliging": "office",
         "magazijn": "store", "bioscoop": "lobby", "hotel_lobby": "lobby", "hotel_bar": "lobby", "metro_rokin": "hall",
         "beurs_zaal": "hall", "bloemenkraam": "kiosk", "nieuwe_kerk": "church", "rondvaartboot": "boat"}
FACING = {"north": 0, "south": 180, "west": 90, "east": -90}


def dress(spec, rng, free, boxes, W, D, sides, fronts):
    """What every public interior has and a modelled one forgets: a suspended ceiling, exit signs over
    the doors, an extinguisher by the way in, a camera in a corner, paper underfoot, a chair knocked over."""
    import math
    kind = KINDS.get(spec["id"])
    if kind in (None, "church", "boat"):
        return
    H = spec["height"]
    P = spec["props"]

    def wall_at(side, u, off):
        return {"north": (u, off), "south": (u, D - off), "west": (off, u), "east": (W - off, u)}[side]
    if kind in ("shop", "office"):
        P.append({"type": "drop_ceiling", "pos": [round(W / 2, 3), round(H - 0.012, 3), round(D / 2, 3)], "size": [round(W, 3), 0.02, round(D, 3)],
                  "seed": rng.randrange(999), "collide": False})
        for L in spec.get("lights", []):
            if L.get("pos") and L["pos"][1] > H - 0.06:
                L["pos"][1] = round(H - 0.08, 3)
    elif kind in ("store", "hall"):
        along = W >= D
        L = (W if along else D) - 1.0
        x, z = (W / 2, D * 0.35) if along else (W * 0.35, D / 2)
        P.append({"type": "duct", "pos": [round(x, 3), round(H - 0.45, 3), round(z, 3)], "size": [round(L, 3), 0.32, 0.5],
                  "yaw": 0 if along else 90, "collide": False})
    ways = []
    for side, w in spec.get("walls", {}).items():
        for o in w.get("openings", []):
            if o.get("kind", "door") in ("door", "passage"):
                ways.append((side in fronts, side, o))
    ways.sort(key=lambda t: not t[0])
    for _, side, o in ways[:3]:
        y = min(o.get("height", 2.1) + 0.18, H - 0.3)
        x, z = wall_at(side, o["center"], 0.08)
        P.append({"type": "exit_sign", "pos": [round(x, 3), round(y, 3), round(z, 3)], "size": [0.42, 0.17, 0.07], "yaw": FACING[side], "collide": False})
    if ways:
        _, side, o = ways[0]
        for du in (o["width"] / 2 + 0.55, -o["width"] / 2 - 0.55):
            x, z = wall_at(side, o["center"] + du, 0.2)
            if 0.3 < x < W - 0.3 and 0.3 < z < D - 0.3 and free(x, z, 0.2):
                P.append({"type": "model", "model": "ph:korean_fire_extinguisher_01", "pos": [round(x, 3), 0.0, round(z, 3)],
                          "yaw": FACING[side], "scale": 1.0, "collide": False})
                boxes.append((x, z, 0.2, 0.2, 0.0))
                break
    if kind in ("shop", "office", "lobby", "hall", "store"):
        corners = [((0.2, 0.2), 45), ((W - 0.2, 0.2), -45), ((0.2, D - 0.2), 135), ((W - 0.2, D - 0.2), -135)]
        rng.shuffle(corners)
        for (x, z), yaw in corners[:1 if W * D < 150 else 2]:
            P.append({"type": "model", "model": "ph:security_camera_01", "pos": [round(x, 3), round(H - 0.5, 3), round(z, 3)],
                      "yaw": yaw, "scale": 1.0, "collide": False})
    for _ in range(2 if W * D > 60 else 1):
        x, z = rng.uniform(1.2, W - 1.2), rng.uniform(1.2, D - 1.2)
        P.append({"type": "leaflets", "pos": [round(x, 2), 0.0, round(z, 2)], "size": [round(min(4.0, W * 0.4), 2), 0.01, round(min(3.0, D * 0.4), 2)],
                  "seed": rng.randrange(999), "count": int(min(4.0, W * 0.4) * min(3.0, D * 0.4) * 0.5),
                  "paper": [0.5, 0.48, 0.44], "rough": 0.7, "lift": 0.5, "collide": False})
    if kind in ("office", "lobby", "store"):
        for _ in range(40):
            x, z = rng.uniform(1.0, W - 1.0), rng.uniform(1.0, D - 1.0)
            if free(x, z, 0.6):
                P.append({"type": "model", "model": rng.choice(["ph:plastic_monobloc_chair_01", "ph:dining_chair_02"]), "pos": [round(x, 2), 0.0, round(z, 2)],
                          "yaw": rng.randrange(360), "tip": 90, "scale": 1.0, "size": [0.9, 0.5, 0.6]})
                boxes.append((x, z, 0.45, 0.3, 0.0))
                break
    if kind in ("office", "store"):
        for _ in range(30):
            side = rng.choice(sides) if sides else None
            if side is None:
                break
            u = rng.uniform(1.0, (W if side in ("north", "south") else D) - 1.0)
            x, z = wall_at(side, u, 0.3)
            if not free(x, z, 0.6):
                continue
            P.append({"type": "model", "model": "ph:steel_frame_shelves_01", "pos": [round(x, 3), 0.0, round(z, 3)], "yaw": FACING[side],
                      "scale": 1.0, "size": [1.1, 2.14, 0.5]})
            ux, uz = (1, 0) if side in ("north", "south") else (0, 1)
            bx, bz = x + ux * 0.85, z + uz * 0.85
            if free(bx, bz, 0.3):
                P.append({"type": "model", "model": "ph:cardboard_box_01", "pos": [round(bx, 3), 0.0, round(bz, 3)],
                          "yaw": FACING[side] + rng.randrange(-20, 20), "scale": 1.0, "collide": False})
            boxes.append((x, z, 0.6, 0.3, 0.0))
            break


STREET_JUNK = [   # (models, footprint w x d for a collider or None, how often)
    (["ph:trashbag", "ph:trashbag", "ph:trashbag"], None, 4),
    (["ph:metal_trash_can"], (1.85, 0.56), 2),
    (["ph:cardboard_box_01", "ph:cardboard_box_01", "ph:wooden_crate_01"], None, 2),
    (["ph:plastic_crate_02", "ph:plastic_crate_01"], None, 1),
    (["ph:planter_box_01"], (0.92, 0.42), 1),
    (["bike"], (1.8, 0.5), 3),
]


def dress_street(spec):
    """A street's pavements as a city leaves them: bin bags heaped by the doors, wheelie bins, boxes
    put out, bikes chained to the house fronts, planters; kept off the doors, the lamps and the way through."""
    import math
    o = spec.get("outdoor") or {}
    if not o.get("facades") or spec.get("no_junk") or any(q.get("junk") for q in spec.get("props", [])):
        return
    rng = random.Random("junk " + spec["id"])
    (bx0, bz0), (bx1, bz1) = spec["bounds"]["min"], spec["bounds"]["max"]
    keep = [(i["pos"][0], i["pos"][2], 2.0) for i in spec.get("interactables", [])]
    keep += [(e["pos"][0], e["pos"][2], 1.5) for e in spec.get("enemies", [])]
    keep += [(v["pos"][0], v["pos"][2], 2.0) for v in spec.get("spawns", {}).values()]
    keep += [(l[0], l[1], 0.8) for l in o.get("lamps", [])]
    for side, w in spec.get("walls", {}).items():
        for op in w.get("openings", []):
            c, hw = op.get("center", 0.0), op.get("width", 1.0) / 2 + 1.2
            for t in (c - hw, c, c + hw):
                x, z = {"north": (bx0 + t, bz0), "south": (bx0 + t, bz1), "west": (bx0, bz0 + t), "east": (bx1, bz0 + t)}[side]
                keep.append((x, z, hw if t == c else 1.2))
    boxes = []
    for q in spec.get("props", []):
        if "size" in q and q.get("collide", True) is not False:
            boxes.append((q["pos"][0], q["pos"][2], q["size"][0] / 2, q["size"][-1] / 2, math.radians(q.get("yaw", 0.0))))
        elif q["type"] in ("model", "bike", "luggage"):
            boxes.append((q["pos"][0], q["pos"][2], 0.6, 0.6, 0.0))

    def free(x, z, r):
        if not (bx0 + 0.3 < x < bx1 - 0.3 and bz0 + 0.3 < z < bz1 - 0.3):
            return False
        if any(math.hypot(x - a, z - b) < rr + r for a, b, rr in keep):
            return False
        for cx, cz, hx, hz, t in boxes:
            dx, dz = x - cx, z - cz
            lx, lz = dx * math.cos(t) - dz * math.sin(t), dx * math.sin(t) + dz * math.cos(t)
            if abs(lx) < hx + r and abs(lz) < hz + r:
                return False
        return True
    bag = [k for k, (_, _, n) in enumerate(STREET_JUNK) for _ in range(n)]
    out = []
    for f in o["facades"]:
        along_z = f.get("facing") in ("east", "west")
        a0, a1 = (f.get("z0"), f.get("z1")) if along_z else (f.get("x0"), f.get("x1"))
        line = f.get("x") if along_z else f.get("z")
        if a0 is None or a1 is None or line is None:
            continue
        out_dir = {"east": 1, "west": -1, "south": 1, "north": -1}.get(f.get("facing"), 1)
        nb = max(1, f.get("bays", 3))
        du = (a0 + (f.get("door_bay", 0) + 0.5) * (a1 - a0) / nb) if not f.get("shop") else None
        u = a0 + rng.uniform(1.0, 3.0)
        while u < a1 - 0.8:
            k = rng.choice(bag)
            models, foot, _ = STREET_JUNK[k]
            off = 0.45 if foot is None else foot[1] / 2 + 0.12
            x, z = (line + out_dir * off, u) if along_z else (u, line + out_dir * off)
            if (du is None or abs(u - du) > 1.3) and free(x, z, 0.55 if foot is None else max(foot) / 2):
                yaw = (90 if along_z else 0) + (0 if out_dir > 0 else 180)
                if models == ["bike"]:
                    out.append({"type": "bike", "pos": [round(x, 2), 0.0, round(z, 2)], "size": [1.8, 1.1, 0.5], "yaw": yaw,
                                "seed": rng.randrange(999)})
                elif foot:
                    out.append({"type": "model", "model": models[0], "pos": [round(x, 2), 0.0, round(z, 2)], "yaw": yaw + rng.choice([0, 180]),
                                "scale": 1.0, "size": [foot[0], 1.0, foot[1]]})
                else:
                    for m in models[:rng.randint(1, len(models))]:
                        dx, dz = rng.uniform(-0.35, 0.35), rng.uniform(-0.2, 0.2)
                        px, pz = (x + dz, z + dx) if along_z else (x + dx, z + dz)
                        out.append({"type": "model", "model": m, "pos": [round(px, 2), 0.0, round(pz, 2)], "yaw": rng.randrange(360),
                                    "scale": round(rng.uniform(0.85, 1.0), 2), "collide": False})
                boxes.append((x, z, 0.7, 0.7, 0.0))
            u += rng.uniform(3.5, 7.0)
    for q in out:
        q["junk"] = True
    spec["props"].extend(out)


def write(spec):
    walk_in(spec.get("props", []))
    finish_indoors(spec)
    dress_street(spec)
    with open(R + spec["id"] + ".json", "w") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=True)
        fh.write("\n")
    print(spec["id"], len(spec.get("props", [])), "props")


def glass_door(center, width, height, hinge="left"):
    return {"kind": "door", "style": "glass", "center": round(center, 4), "width": round(width, 4), "height": round(height, 4), "hinge": hinge}


