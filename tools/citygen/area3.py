# damned_waters/tools/citygen/area3.py
# Generates area 3 (storey 11): reguliersbreestraat, muntplein, bloemenmarkt (streets) and apotheek,
# bioscoop, bloemenkraam (shops he walks into). Doors between a street and a shop are worked out with
# tools/pipeline/facade.py, the same arithmetic the renderer uses.
from pathlib import Path
import os
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import facade as fz  # noqa: E402

R = os.environ.get("DW_ROOMS", str(Path(__file__).resolve().parents[2] / "game" / "data" / "rooms") + "/")
STOREY = 11
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
}
ROOM_OF = {"cafe": "warm_bar", "coffeeshop": "warm_bar", "restaurant": "warm_restaurant_night", "bar": "warm_bar", "hotel": "fireplace",
           "pharmacy": "unfinished_office_night", "souvenir": "christmas_photo_studio_04", "snack": "warm_restaurant_night",
           "books": "fireplace", "cinema": "warm_bar"}


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


def street_room(rid, name, origin, size, height, desc):
    return {"_file": f"damned_waters/game/data/rooms/{rid}.json — RoomSpec for {name} (the city, district 2: the Munt): {desc} "
                     "Modelled after openly licensed photographs; every business name is made up, the landmarks keep theirs. "
                     "The power is still on; nobody is there. Outdoor (street.py, city.py and landmarks.py build it). Single source "
                     "of truth for Blender (render) and the engine (collision, cameras, things).",
            "id": rid, "display_name": name, "storey": STOREY, "origin": origin,
            "bounds": {"min": [0.0, 0.0], "max": list(size)}, "height": height,
            "materials": {"floor": {"color": [0.2, 0.2, 0.2]}, "wall": {"color": [0.2, 0.2, 0.2]}, "ceiling": {"color": [0.2, 0.2, 0.2]}},
            "footsteps": "marble", "ambience": "amb_street_rain", "move_scale": 1.0, "world": {"color": [0.014, 0.019, 0.036], "strength": 1.0},
            "sky": SKY, "render": {"exposure": 0.85, "bloom": {"threshold": 0.9, "strength": 0.4, "size": 0.55}}}


def shop_room(rid, name, origin, size, height, desc, materials, exposure=1.0):
    return {"_file": f"damned_waters/game/data/rooms/{rid}.json — RoomSpec for {name} (the city, district 2: the Munt): {desc} "
                     "Its front wall is the street's shopfront (\"facade\": the street builds it); its door is the street's. Every "
                     "business name is made up. Single source of truth for Blender (render) and the engine (collision, cameras, things).",
            "id": rid, "display_name": name, "storey": STOREY, "origin": origin,
            "bounds": {"min": [0.0, 0.0], "max": list(size)}, "height": height, "materials": materials,
            "footsteps": "marble", "ambience": "amb_cellar", "move_scale": 1.0, "world": {"color": [0.01, 0.012, 0.016], "strength": 0.5},
            "render": {"exposure": exposure, "bloom": {"threshold": 0.95, "strength": 0.25, "size": 0.5}}}


def write(spec):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import common   # (the interiors' finish: real plaster, pools of light, clutter)
    common.finish_indoors(spec)
    common.dress_street(spec)
    with open(R + spec["id"] + ".json", "w") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=True)
        fh.write("\n")
    print(spec["id"], len(spec.get("props", [])), "props")


def glass_door(center, width, height, hinge="left"):
    return {"kind": "door", "style": "glass", "center": round(center, 4), "width": round(width, 4), "height": round(height, 4), "hinge": hinge}


# ════════════════════════════════════════════════════════════════════════════════════
# Reguliersbreestraat: the narrow street from Rembrandtplein to the Munt, trams down the middle
# ════════════════════════════════════════════════════════════════════════════════════
T = 0.3   # rooms that share a wall stand a wall's thickness apart (room_spec.hpp WALL_T); a shop's is its street's front
RO = [909.7, -50.3]
rng = random.Random(21)
G = street_room("reguliersbreestraat", "Reguliersbreestraat", RO, (70.0, 10.0), 10.0,
                "the narrow street of shops, snack bars and clubs from Rembrandtplein to the Munt, a tram line down its middle, "
                "lights strung across it; on its south side the art-deco picture palace, on its north an apotheek with its green cross.")
o = {"window_rooms": ROOMS, "lamp_power": 340.0, "lamp_energy": 1.0,
     "ground": [{"name": "pavement_n", "min": [0.0, 0.0], "max": [70.0, 2.2], "y": 0.06, "material": PAVERS, "kerb": True},
                {"name": "road", "min": [0.0, 2.2], "max": [70.0, 7.8], "y": 0.0, "material": BRICKS},
                {"name": "pavement_s", "min": [0.0, 7.8], "max": [70.0, 10.0], "y": 0.06, "material": PAVERS}],
     "tracks": [{"from": [0.0, 7.0], "to": [70.0, 7.0], "y": 0.0}],
     "lamps": [[6.0, 1.4], [30.0, 1.4], [54.0, 1.4], [18.0, 8.6], [42.0, 8.6], [66.0, 8.6]],
     "strings": [[[x, 7.2, 0.4], [x, 7.2, 9.6], 0.7, 0.4] for x in (9.0, 21.0, 33.0, 45.0, 57.0)]}
APO = front("south", 16.55, 26.0, 0.0, [4.2, 3.3, 3.1, 2.9], 4, "cornice", 302,
            shop("APOTHEEK DE ZWARTE KAT", "pharmacy", False, door_bay=3, power=95.0, enter=True, cross=True), lean=0.0)
CINEMA = front("north", 14.05, 30.0, 10.0, [4.6, 3.6, 3.4, 3.2], 4, "cornice", 313,
               shop("ENTREE · KASSA", "cinema", False, door_bay=3, power=120.0, enter=True), lean=0.0,
               deco={"height": 15.5, "tower_w": 3.2, "name": "THEATER DE ZILVERMAAN", "vertical": "THEATER",
                     "tiles": {"ph": "rectangular_facade_tiles", "tint": [0.78, 0.82, 0.7], "scale": 1.0}, "power": 420.0})
o["facades"] = [
    front("south", 0.0, 8.5, 0.0, [4.4, 3.4, 3.2, 3.0, 2.8], 4, "cornice", 300, shop("CAFÉ DE MUNT", "cafe", "CAFÉ")),
    front("south", 8.55, 16.5, 0.0, [4.2, 3.3, 3.1, 2.9], 3, "neck", 301, shop("SOUVENIRS · KLOMPEN", "souvenir", "SOUVENIRS"), gable_h=3.8),
    APO,
    front("south", 26.05, 34.0, 0.0, [4.2, 3.2, 3.0, 2.8], 3, "step", 303, shop("SNACKBAR DE GOUDEN FRIET", "snack", "FRIET"), gable_h=3.6),
    front("south", 34.05, 44.0, 0.0, [4.2, 3.3, 3.1, 2.9], 4, "cornice", 304, shop("COFFEESHOP DE ROOKWOLK", "coffeeshop", "COFFEESHOP")),
    front("south", 44.05, 52.0, 0.0, [4.0, 3.3, 3.1, 2.9], 3, "bell", 305, door_bay=1, stoop=0.5, gable_h=3.6),
    front("south", 52.05, 61.0, 0.0, [4.4, 3.4, 3.2, 3.0, 2.8], 4, "cornice", 306, shop("HOTEL HET WAPEN", "hotel", "HOTEL", awning=False), lit=0.55),
    front("south", 61.05, 70.0, 0.0, [4.2, 3.3, 3.1, 2.9], 3, "neck", 307, shop("IJSSALON NAPOLI", "restaurant", "GELATO"), gable_h=3.8),
    front("north", 0.0, 8.0, 10.0, [4.4, 3.4, 3.2, 3.0, 2.8], 4, "cornice", 310, shop("BOEKHANDEL DE ZWAAN", "books", "BOEKEN")),
    front("north", 8.05, 14.0, 10.0, [4.0, 3.2, 3.0, 2.8], 3, "neck", 311, door_bay=1, stoop=0.5, gable_h=3.4),
    CINEMA,
    front("north", 30.05, 38.0, 10.0, [4.2, 3.2, 3.0, 2.8], 3, "step", 314, shop("FRITES · SNACKS", "snack", "FRITES"), gable_h=3.6),
    front("north", 38.05, 47.0, 10.0, [4.4, 3.4, 3.2, 3.0], 4, "cornice", 315, shop("CLUB DE KELDER", "bar", "CLUB")),
    front("north", 47.05, 55.0, 10.0, [4.2, 3.3, 3.1, 2.9], 3, "neck", 316, shop("PIZZERIA BELLA", "restaurant", "PIZZA"), gable_h=3.8),
    front("north", 55.05, 63.0, 10.0, [4.2, 3.2, 3.0, 2.8], 3, "bell", 317, shop("WISSELKANTOOR", "hotel", "EXCHANGE", awning=False), gable_h=3.6),
    front("north", 63.05, 70.0, 10.0, [4.2, 3.3, 3.1, 2.9], 3, "spout", 318, shop("SMARTSHOP", "coffeeshop", "SMART"), gable_h=3.4),
]
apo_c, apo_w, apo_h = shop_doorway(APO)
cin_c, cin_w, cin_h = shop_doorway(CINEMA, offset=3.2)
props = []
for x in [3.0 + 2.4 * i for i in range(29)]:   # Amsterdammertjes along both kerbs, broken at the doors and the cinema
    if abs(x - apo_c) > 1.6 and abs(x - cin_c) > 3.0:
        props.append({"type": "bollard", "pos": [round(x, 2), 0.06, 2.05], "size": [0.2, 0.9, 0.2]})
    if not 13.0 < x < 31.0:
        props.append({"type": "bollard", "pos": [round(x, 2), 0.06, 7.95], "size": [0.2, 0.9, 0.2]})
props += [{"type": "bike", "pos": [48.0 + 0.7 * i, 0.06, 1.0], "yaw": 90 + (8 if i % 2 else 0), "size": [1.8, 1.1, 0.5], "collide": False, "seed": 70 + i}
          for i in range(4)]
props += [{"type": "bike", "pos": [11.0, 0.0, 4.6], "yaw": 20, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 80},
          {"type": "model", "model": "ph:trashbag", "pos": [27.5, 0.06, 1.0], "yaw": 30, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:trashbag", "pos": [28.1, 0.06, 1.3], "yaw": 110, "scale": 0.9, "collide": False},
          {"type": "model", "model": "ph:standing_chalkboard_01", "pos": [37.0, 0.06, 1.2], "yaw": 160, "scale": 0.8, "collide": False},
          {"type": "model", "model": "ph:standing_chalkboard_01", "pos": [49.5, 0.06, 8.9], "yaw": 20, "scale": 0.8, "collide": False},
          {"type": "model", "model": "ph:WetFloorSign_01", "pos": [cin_c - 2.6, 0.06, 8.6], "yaw": 40, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:street_rat", "pos": [33.0, 0.0, 3.0], "yaw": 70, "scale": 1.0, "collide": False}]
G["outdoor"] = o
G["props"] = props
G["walls"] = {"east": {"openings": [{"kind": "passage", "center": 5.0, "width": 10.0, "height": 10.0}]},
              "west": {"openings": [{"kind": "passage", "center": 5.0, "width": 10.0, "height": 10.0}]},
              "north": {"openings": [glass_door(apo_c, apo_w, apo_h)]},
              "south": {"openings": [glass_door(cin_c, cin_w, cin_h)]}}
G["lights"] = [SUN, {"kind": "point", "pos": [cin_c, 3.6, 8.4], "color": [1.0, 0.82, 0.55], "blender_power": 0, "godot_energy": 0.9, "range": 9.0},
               {"kind": "point", "pos": [apo_c, 2.4, 1.0], "color": [0.5, 1.0, 0.6], "blender_power": 0, "godot_energy": 0.4, "range": 6.0}]
G["shots"] = [
    {"id": "a", "pos": [67.5, 3.2, 3.2], "look_at": [20.0, 5.0, 5.5], "fov": 55, "zone": {"min": [46.0, 0.0], "max": [70.0, 10.0]}, "priority": 1},
    {"id": "b", "pos": [41.0, 3.6, 3.4], "look_at": [22.0, 3.8, 9.5], "fov": 60, "zone": {"min": [28.0, 0.0], "max": [46.0, 10.0]}, "priority": 1},
    {"id": "c", "pos": [10.0, 3.4, 7.8], "look_at": [26.0, 1.8, 0.5], "fov": 60, "zone": {"min": [12.0, 0.0], "max": [28.0, 10.0]}, "priority": 1},
    {"id": "d", "pos": [2.5, 3.0, 1.6], "look_at": [30.0, 2.6, 7.5], "fov": 58, "zone": {"min": [0.0, 0.0], "max": [12.0, 10.0]}, "priority": 1}]
G["spawns"] = {"from_rembrandtplein": {"pos": [63.5, 0.0, 5.0], "yaw": 90}, "from_muntplein": {"pos": [1.5, 0.0, 5.0], "yaw": -90},
               "from_apotheek": {"pos": [apo_c, 0.0, 1.2], "yaw": 180}, "from_bioscoop": {"pos": [cin_c, 0.0, 8.8], "yaw": 0}}
G["interactables"] = [
    {"id": "to_rembrandtplein", "kind": "door", "pos": [69.8, 1.0, 5.0], "radius": 1.6, "target_room": "rembrandtplein",
     "target_spawn": "from_reguliersbreestraat"},
    {"id": "door_apotheek", "kind": "door", "pos": [apo_c, 1.0, 0.45], "radius": 1.0},
    {"id": "door_bioscoop", "kind": "door", "pos": [cin_c, 1.0, 9.55], "radius": 1.0},
    {"id": "zilvermaan", "kind": "examine", "pos": [cin_c - 2.4, 1.0, 9.4], "radius": 1.4,
     "text": "Theater de Zilvermaan. Tonight's showing started at nine. The doors are open; the marquee is still burning."},
    {"id": "green_cross", "kind": "examine", "pos": [apo_c + 2.2, 1.0, 0.6], "radius": 1.2,
     "text": "An apotheek, the green cross still lit over the door. If there's anything left to patch yourself up with, it's in there."},
    {"id": "shells_snackbar", "kind": "pickup", "item": "shotgun_shells", "count": 3, "pos": [30.4, 0.06, 1.1], "radius": 0.9}]
G["enemies"] = [{"id": "in_de_straat", "kind": "verdronkene", "pos": [40.0, 0.0, 5.5], "yaw": 80},
                {"id": "bij_de_snackbar", "kind": "verdronkene", "pos": [29.0, 0.06, 1.4], "yaw": 200}]
write(G)

# ── The apotheek: white tiles, shelves of medicine, the big green EHBO case on the wall ──────
AO = [RO[0] + APO["x0"], RO[1] - T - 9.0]
W_apo = APO["x1"] - APO["x0"]
u_apo = apo_c - APO["x0"]
A = shop_room("apotheek", "Apotheek de Zwarte Kat", AO, (W_apo, 9.0), 4.0,
              "a chemist's off Reguliersbreestraat: shelving of packets and bottles, picked over, the counter at the back with the "
              "dispensary shelves behind it, and on the wall the big green EHBO case.",
              {"floor": {"ph": "terrazzo_tiles", "tint": [0.8, 0.8, 0.78], "rough": 0.3}, "wall": {"color": [0.86, 0.88, 0.86], "rough": 0.6, "noise": 0.05},
               "ceiling": {"color": [0.8, 0.8, 0.8], "rough": 0.7},
               "wainscot": {"color": [0.06, 0.24, 0.14], "rough": 0.25, "noise": 0.06}, "wainscot_height": 1.1,
               "skirting": {"color": [0.03, 0.1, 0.06], "rough": 0.4}, "skirting_height": 0.1},
              exposure=0.75)
rng = random.Random(31)
A["walls"] = {"south": {"facade": True, "openings": [glass_door(u_apo, apo_w, apo_h)]},
              "north": {"openings": [{"kind": "door", "center": 0.9, "width": 0.9, "height": 2.1, "hinge": "right"}]}}
A["props"] = [
    {"type": "counter", "pos": [4.4, 0.0, 2.6], "size": [4.4, 1.0, 0.7], "yaw": 0},
    {"type": "shelving", "pos": [4.4, 0.0, 0.3], "size": [5.2, 2.4, 0.45], "yaw": 0, "palette": "pharmacy", "empty": 0.45, "seed": 1, "fallen": 0},
    {"type": "shelving", "pos": [2.6, 0.0, 5.9], "size": [2.6, 1.6, 0.9], "yaw": 0, "double": True, "palette": "pharmacy", "empty": 0.3, "seed": 2, "shelves": 4},
    {"type": "shelving", "pos": [7.6, 0.0, 5.9], "size": [2.6, 1.6, 0.9], "yaw": 0, "double": True, "palette": "pharmacy", "empty": 0.25, "seed": 3, "shelves": 4},
    {"type": "shelving", "pos": [0.3, 0.0, 6.0], "size": [4.6, 2.2, 0.45], "yaw": 90, "palette": "pharmacy", "empty": 0.2, "seed": 4},
    {"type": "wall_sign", "pos": [8.3, 1.85, 0.04], "size": [0.9, 0.22, 0.03], "text": "EHBO", "color": [0.3, 1.0, 0.45], "glow": 2.0, "collide": False},   # (the case under it is the game's)
    {"type": "model", "model": "ph:WetFloorSign_01", "pos": [5.0, 0.0, 4.4], "yaw": 30, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:korean_fire_extinguisher_01", "pos": [0.25, 0.0, 8.6], "yaw": 90, "scale": 1.0, "collide": False},
    {"type": "wall_sign", "pos": [4.4, 2.75, 0.04], "size": [3.6, 0.55, 0.03], "text": "APOTHEEK", "color": [0.3, 1.0, 0.45], "glow": 2.5, "collide": False},
    {"type": "wall_sign", "pos": [0.04, 2.3, 6.0], "size": [2.4, 0.4, 0.03], "yaw": 90, "text": "VERZORGING", "lit": False, "color": [0.85, 0.88, 0.85],
     "panel": {"color": [0.06, 0.24, 0.14], "rough": 0.4}, "collide": False}]
for x in (2.6, 7.6):
    A["props"].append({"type": "strip_light", "pos": [x, 4.0, 4.5], "size": [3.0, 0.1, 0.2], "collide": False})
A["props"].append({"type": "strip_light", "pos": [4.4, 4.0, 1.6], "size": [4.4, 0.1, 0.2], "collide": False})
A["lights"] = [{"kind": "area", "pos": [2.6, 3.9, 4.5], "look_at": [2.6, 0.0, 4.5], "size": 1.6, "color": [0.92, 0.97, 1.0], "blender_power": 120, "godot_energy": 0.5, "range": 8.0},
               {"kind": "area", "pos": [7.6, 3.9, 4.5], "look_at": [7.6, 0.0, 4.5], "size": 1.6, "color": [0.92, 0.97, 1.0], "blender_power": 70, "godot_energy": 0.4, "range": 8.0},
               {"kind": "area", "pos": [4.4, 3.9, 1.6], "look_at": [4.4, 0.0, 1.6], "size": 1.4, "color": [0.92, 0.97, 1.0], "blender_power": 90, "godot_energy": 0.4, "range": 6.0},
               {"kind": "point", "pos": [u_apo, 2.6, 8.6], "color": [0.4, 1.0, 0.55], "blender_power": 12, "godot_energy": 0.3, "range": 4.0, "radius": 0.2}]
A["shots"] = [
    {"id": "a", "pos": [W_apo - 0.5, 2.8, 8.5], "look_at": [3.0, 1.0, 1.8], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [W_apo, 5.0]}, "priority": 1},
    {"id": "b", "pos": [0.6, 2.9, 3.6], "look_at": [W_apo - 1.5, 0.9, 8.6], "fov": 62, "zone": {"min": [0.0, 5.0], "max": [W_apo, 9.0]}, "priority": 1}]
A["spawns"] = {"from_street": {"pos": [u_apo, 0.0, 8.3], "yaw": 0}}
A["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [u_apo, 1.0, 8.55], "radius": 1.0},
    {"id": "ehbo_case", "kind": "pickup", "item": "med_large", "count": 1, "pos": [8.3, 1.3, 0.4], "radius": 1.0},
    {"id": "first_aid_counter", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [3.0, 1.02, 2.6], "radius": 0.9},
    {"id": "dispensary", "kind": "examine", "pos": [4.4, 1.0, 1.4], "radius": 1.4,
     "text": "The dispensary shelves are bare where the painkillers were. Someone came for those first."},
    {"id": "back_door", "kind": "examine", "pos": [0.9, 1.0, 0.35], "radius": 1.0, "text": "The back room. Bolted from the other side."}]
A["enemies"] = [{"id": "de_apotheker", "kind": "verdronkene", "pos": [5.6, 0.0, 1.5], "yaw": 180}]
write(A)

# ── The picture palace's lobby: red carpet, brass and velvet, the booth, the cloakroom ────────
BO = [RO[0] + CINEMA["x0"], RO[1] + 10.0 + T]
W_cin = CINEMA["x1"] - CINEMA["x0"]
u_cin = cin_c - CINEMA["x0"]
B = shop_room("bioscoop", "Theater de Zilvermaan", BO, (W_cin, 14.0), 4.4,
              "the art-deco picture palace's lobby: red carpet, brass and velvet ropes, the ticket booth, the sweets counter, the "
              "cloakroom with the coats still on their hooks, the posters for tonight; the doors to the auditorium chained shut.",
              {"floor": {"ph": "dirty_carpet", "tint": [0.95, 0.22, 0.16], "rough": 0.9},
               "wall": {"color": [0.32, 0.06, 0.05], "rough": 0.55, "noise": 0.12},
               "ceiling": {"color": [0.28, 0.2, 0.09], "rough": 0.45, "metal": 0.4, "noise": 0.1},
               "wainscot": {"ph": "rosewood_veneer1", "tint": [0.7, 0.5, 0.4], "scale": 0.6}, "wainscot_height": 1.2,
               "skirting": {"color": [0.33, 0.22, 0.11], "rough": 0.3, "metal": 0.8}, "skirting_height": 0.12},
              exposure=1.1)
B["walls"] = {"north": {"facade": True, "openings": [glass_door(u_cin, cin_w, cin_h)]},
              "south": {"openings": [{"kind": "door", "center": 5.0, "width": 1.8, "height": 2.4}, {"kind": "door", "center": 11.0, "width": 1.8, "height": 2.4}]}}
B["props"] = [
    {"type": "ticket_booth", "pos": [8.0, 0.0, 9.6], "size": [2.4, 2.8, 1.6], "yaw": 180},
    {"type": "stanchions", "pos": [8.6, 0.0, 7.4], "size": [5.6, 0.95, 0.1], "yaw": 0},
    {"type": "stanchions", "pos": [7.4, 0.0, 6.0], "size": [5.6, 0.95, 0.1], "yaw": 0},
    {"type": "display_case", "pos": [W_cin - 0.6, 0.0, 6.5], "size": [3.0, 1.0, 0.7], "yaw": -90, "palette": "candy", "empty": 0.35, "seed": 6},
    {"type": "counter", "pos": [2.3, 0.0, 11.6], "size": [3.6, 1.05, 0.6], "yaw": 90, "till": False},
    {"type": "coat_rack", "pos": [0.9, 0.0, 11.6], "size": [3.6, 1.8, 0.5], "yaw": 90, "seed": 41, "collide": False},
    {"type": "poster", "pos": [0.03, 0.9, 3.0], "size": [1.1, 1.6, 0.05], "yaw": 90, "title": "DE STILLE STAD", "line": "VANAVOND 21:00", "color": [0.12, 0.2, 0.45], "collide": False},
    {"type": "poster", "pos": [0.03, 0.9, 5.4], "size": [1.1, 1.6, 0.05], "yaw": 90, "title": "NACHTWACHT", "line": "UITVERKOCHT", "color": [0.45, 0.1, 0.06], "collide": False},
    {"type": "poster", "pos": [0.03, 0.9, 7.8], "size": [1.1, 1.6, 0.05], "yaw": 90, "title": "HET WATER KOMT", "line": "BINNENKORT", "color": [0.05, 0.28, 0.26], "collide": False},
    {"type": "model", "model": "ph:Chandelier_02", "pos": [W_cin / 2, 3.2, 4.5], "yaw": 0, "fit": [1.4, 1.2, 1.4], "collide": False},
    {"type": "model", "model": "ph:Chandelier_02", "pos": [W_cin / 2, 3.2, 10.0], "yaw": 0, "fit": [1.4, 1.2, 1.4], "collide": False},
    {"type": "model", "model": "ph:ArmChair_01", "pos": [W_cin - 1.0, 0.0, 11.4], "yaw": -110, "scale": 1.0, "size": [0.8, 0.9, 0.8]},
    {"type": "model", "model": "ph:ArmChair_01", "pos": [W_cin - 2.3, 0.0, 12.8], "yaw": 200, "scale": 1.0, "size": [0.8, 0.9, 0.8]},
    {"type": "wall_sign", "pos": [5.0, 2.65, 13.96], "size": [1.6, 0.4, 0.03], "yaw": 180, "text": "ZAAL 1", "color": [1.0, 0.78, 0.4], "glow": 3.0, "collide": False},
    {"type": "wall_sign", "pos": [11.0, 2.65, 13.96], "size": [1.6, 0.4, 0.03], "yaw": 180, "text": "ZAAL 2", "color": [1.0, 0.78, 0.4], "glow": 3.0, "collide": False},
    {"type": "model", "model": "ph:filmstrip_projector_8mm", "pos": [W_cin - 0.6, 1.0, 5.5], "yaw": -90, "scale": 1.6, "collide": False}]
for z in (2.5, 6.0, 9.5, 13.0):   # pilasters down both long walls, a sconce on each
    B["props"].append({"type": "pilaster", "pos": [0.03, 0.0, z], "yaw": 90, "size": [0.45, 4.4, 0.18], "lamp": z < 13, "collide": False})
    B["props"].append({"type": "pilaster", "pos": [W_cin - 0.03, 0.0, z], "yaw": -90, "size": [0.45, 4.4, 0.18], "lamp": z < 13, "collide": False})
B["lights"] = [{"kind": "point", "pos": [W_cin / 2, 3.0, 4.5], "color": [1.0, 0.78, 0.5], "blender_power": 380, "godot_energy": 0.9, "range": 9.0, "radius": 0.3},
               {"kind": "point", "pos": [W_cin / 2, 3.0, 10.0], "color": [1.0, 0.78, 0.5], "blender_power": 340, "godot_energy": 0.8, "range": 9.0, "radius": 0.3},
               {"kind": "point", "pos": [0.5, 2.2, 6.0], "color": [1.0, 0.75, 0.45], "blender_power": 40, "godot_energy": 0.3, "range": 4.0, "radius": 0.1},
               {"kind": "point", "pos": [W_cin - 0.5, 2.2, 9.5], "color": [1.0, 0.75, 0.45], "blender_power": 40, "godot_energy": 0.3, "range": 4.0, "radius": 0.1},
               {"kind": "point", "pos": [8.0, 2.2, 9.4], "color": [1.0, 0.75, 0.45], "blender_power": 25, "godot_energy": 0.3, "range": 3.0, "radius": 0.1},
               {"kind": "point", "pos": [1.6, 2.6, 11.6], "color": [1.0, 0.7, 0.4], "blender_power": 30, "godot_energy": 0.3, "range": 4.0, "radius": 0.15}]
B["shots"] = [
    {"id": "a", "pos": [W_cin - 1.2, 3.3, 1.0], "look_at": [5.0, 1.0, 11.0], "fov": 64, "zone": {"min": [0.0, 6.0], "max": [W_cin, 14.0]}, "priority": 1},
    {"id": "b", "pos": [1.0, 3.2, 13.2], "look_at": [W_cin - 4.0, 1.2, 1.5], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [W_cin, 6.0]}, "priority": 1}]
B["spawns"] = {"from_street": {"pos": [u_cin, 0.0, 0.8], "yaw": 180}}
B["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [u_cin, 1.0, 0.45], "radius": 1.0},
    {"id": "cloakroom", "kind": "examine", "pos": [2.9, 1.0, 11.0], "radius": 1.2,
     "text": "Ticket 41 still on its hook. In the coat's pocket, a box of nine-millimetre. Somebody didn't come here for the film."},
    {"id": "ammo_cloakroom", "kind": "pickup", "item": "handgun_ammo", "count": 15, "pos": [2.35, 1.07, 12.4], "radius": 0.9},
    {"id": "zaal", "kind": "examine", "pos": [5.0, 1.0, 13.6], "radius": 1.3,
     "text": "Zaal 1. Chained shut from the inside. Behind the doors, the film is still running; you can hear the music."},
    {"id": "booth", "kind": "examine", "pos": [8.0, 1.0, 8.5], "radius": 1.2,
     "text": "The till drawer is open. Nobody took the money."}]
B["enemies"] = [{"id": "de_suppoost", "kind": "verdronkene", "pos": [11.5, 0.0, 4.0], "yaw": 20}]
write(B)

# ════════════════════════════════════════════════════════════════════════════════════
# Muntplein: the square over the water where the Singel and the Amstel meet, the tower on its corner
# ════════════════════════════════════════════════════════════════════════════════════
MO = [RO[0] - T - 44.0, -64.0]
rng = random.Random(51)
P = street_room("muntplein", "Muntplein", MO, (44.0, 36.0), 12.0,
                "the square over the water where the Singel begins and Rokin runs north, the Munttoren on its corner with its clock "
                "stopped at 11:47, the trams' rails curving through it, crowd barriers across the way up Rokin.")
o = {"window_rooms": ROOMS, "lamp_power": 400.0, "lamp_energy": 1.0,
     "ground": [{"name": "square", "min": [0.0, 0.0], "max": [44.0, 36.0], "y": 0.0, "material": BRICKS},
                {"name": "rokin_road", "min": [18.0, -62.0], "max": [44.0, -0.0], "y": 0.0, "material": BRICKS},
                {"name": "rokin_pavement", "min": [44.0, -62.0], "max": [50.0, 0.0], "y": 0.06, "material": PAVERS},
],
     "canals": [{"axis": "z", "x": 18.0, "side": -1, "width": 16.0, "along": [-70.0, 0.0], "ends": True, "far_quay": 5.0, "lit": 0.3,
                 "shops": 0.35}],
     "tracks": [{"from": [44.0, 20.7], "to": [37.0, 20.7], "y": 0.0}, {"from": [37.0, 20.7], "to": [32.0, 15.7], "y": 0.0},
                {"from": [32.0, 15.7], "to": [32.0, -60.0], "y": 0.0}],
     "lamps": [[12.0, 10.0], [14.0, 30.0], [26.0, 34.5], [43.0, 16.0], [40.0, 29.0], [19.0, 2.0], [43.0, 1.0], [20.0, -20.0], [20.0, -40.0], [43.0, -20.0]],
     "rows": [{"from": -62.0, "to": -0.05, "line": 50.0, "facing": "west", "lit": 0.35, "shops": 0.5},
              {"from": 0.0, "to": 44.0, "line": 36.0, "facing": "north", "lit": 0.3, "shops": 0.5}]}
o["facades"] = [   # the corners of the square: between Rokin and Reguliersbreestraat, south of it, the Singel's corner
    front("west", 0.05, 13.65, 44.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 401, shop("GRAND CAFÉ DE MUNT", "cafe", "CAFÉ", door_bay=2, power=100.0)),
    front("west", 23.75, 36.0, 44.0, [4.4, 3.4, 3.2, 3.0], 4, "cornice", 402, shop("SOUVENIRS · DELFTS BLAUW", "souvenir", "SOUVENIRS"))]
P["outdoor"] = o
P["props"] = [
    {"type": "munttoren", "pos": [5.0, 0.0, 17.0], "size": [7.0, 36.0, 7.0], "yaw": 0},   # on the Singel's corner, at the end of Reguliersbreestraat
    {"type": "crowd_barrier", "pos": [31.0, 0.0, 0.6], "size": [26.0, 1.1, 0.7], "yaw": 0, "seed": 3},
    {"type": "tram", "pos": [32.0, 0.0, -21.0], "yaw": 90, "size": [30.0, 3.4, 2.4], "board": "NIET INSTAPPEN", "power": 260.0, "collide": False},   # the last tram, stopped at the barrier
    {"type": "bench", "pos": [14.0, 0.0, 12.0], "yaw": 90, "size": [1.8, 0.85, 0.5]},
    {"type": "bench", "pos": [14.0, 0.0, 26.0], "yaw": 90, "size": [1.8, 0.85, 0.5]},
    {"type": "kiosk", "pos": [24.0, 0.0, 31.5], "size": [2.6, 3.2, 2.6], "name": "TABAK · LOTTO"},
    {"type": "railing", "pos": [0.25, 0.0, 17.0], "yaw": 90, "size": [14.0, 1.0, 0.1], "collide": False},
    {"type": "railing", "pos": [9.0, 0.0, 0.25], "yaw": 0, "size": [18.0, 1.0, 0.1], "collide": False}]
props = P["props"]
for z in (3.5, 8.0):   # the Grand Café's terrace along the east side, a chair or two over
    table_group(props, 39.4, z, rng, n=2, fallen=1 if z == 8.0 else 0)
props += [{"type": "bike", "pos": [40.5, 0.0, 3.0 + 0.7 * i], "yaw": 0 if i % 2 else 8, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 90 + i}
          for i in range(5)]
props += [{"type": "bike", "pos": [26.0, 0.0, 14.0], "yaw": 60, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 99},
          {"type": "bollard", "pos": [18.4, 0.0, 1.2], "size": [0.2, 0.9, 0.2]},
          {"type": "bollard", "pos": [18.4, 0.0, 4.0], "size": [0.2, 0.9, 0.2]},
          {"type": "model", "model": "ph:trashbag", "pos": [42.8, 0.0, 9.0], "yaw": 30, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:metal_trash_can", "pos": [24.0, 0.0, 12.0], "yaw": 0, "scale": 1.0, "size": [0.5, 1.0, 0.5]}]
P["walls"] = {"east": {"openings": [{"kind": "passage", "center": 18.7, "width": 10.0, "height": 10.0}]},
              "west": {"openings": [{"kind": "passage", "center": 30.0, "width": 12.0, "height": 10.0}]}}
P["lights"] = [SUN, {"kind": "point", "pos": [5.0, 6.0, 23.0], "color": [1.0, 0.85, 0.65], "blender_power": 0, "godot_energy": 1.0, "range": 12.0}]
P["shots"] = [
    {"id": "a", "pos": [42.5, 3.0, 27.0], "look_at": [5.0, 12.0, 17.0], "fov": 62, "zone": {"min": [30.0, 10.0], "max": [44.0, 36.0]}, "priority": 1},
    {"id": "b", "pos": [16.0, 2.8, 35.0], "look_at": [8.0, 10.0, 12.0], "fov": 64, "zone": {"min": [0.0, 22.0], "max": [30.0, 36.0]}, "priority": 1},
    {"id": "c", "pos": [24.0, 3.4, 3.5], "look_at": [4.0, 5.0, 24.0], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [30.0, 22.0]}, "priority": 1},
    {"id": "d", "pos": [40.0, 3.4, 13.0], "look_at": [26.0, 3.0, -24.0], "fov": 60, "zone": {"min": [30.0, 0.0], "max": [44.0, 10.0]}, "priority": 1}]
P["spawns"] = {"from_reguliersbreestraat": {"pos": [42.5, 0.0, 18.7], "yaw": 90}, "from_bloemenmarkt": {"pos": [1.5, 0.0, 30.0], "yaw": -90}}
P["interactables"] = [
    {"id": "munttoren", "kind": "examine", "pos": [5.0, 1.0, 21.2], "radius": 1.6,
     "text": "The Munttoren. Its clock stopped at 11:47. Up in the lantern the carillon still plays a few bars every quarter hour, to nobody."},
    {"id": "rokin", "kind": "examine", "pos": [31.0, 1.0, 1.5], "radius": 2.6,
     "text": "Rokin. Crowd barriers across it, police tape snapping in the wind. Beyond them, the long road to Centraal."},
    {"id": "police_belt", "kind": "pickup", "item": "shotgun_shells", "count": 5, "pos": [27.0, 0.05, 2.2], "radius": 1.0},
    {"id": "singel", "kind": "examine", "pos": [0.8, 1.0, 11.0], "radius": 1.4,
     "text": "The Singel. Something under the water is moving the boats against the quay, slowly, like breathing."}]
P["enemies"] = [{"id": "op_de_munt", "kind": "verdronkene", "pos": [20.0, 0.0, 18.0], "yaw": 120},
                {"id": "bij_de_toren", "kind": "verdronkene", "pos": [11.0, 0.0, 24.0], "yaw": 60}]
write(P)

# ════════════════════════════════════════════════════════════════════════════════════
# Bloemenmarkt: the flower stalls floating on the Singel, shops across the quay
# ════════════════════════════════════════════════════════════════════════════════════
FO = [MO[0] - T - 70.0, -40.0]
rng = random.Random(61)
F = street_room("bloemenmarkt", "Bloemenmarkt", FO, (70.0, 12.0), 8.0,
                "the quay along the Singel where the flower market floats: glasshouse stalls on their pontoons full of tulips and "
                "packets of bulbs, some shuttered, one open; souvenir and cheese shops across the street; the Munttoren at the end.")
o = {"window_rooms": ROOMS, "lamp_power": 360.0, "lamp_energy": 1.0,
     "ground": [{"name": "quay", "min": [0.0, 0.0], "max": [70.0, 3.6], "y": 0.06, "material": PAVERS},
                {"name": "street", "min": [0.0, 3.6], "max": [70.0, 8.6], "y": 0.0, "material": BRICKS},
                {"name": "pavement_s", "min": [0.0, 8.6], "max": [70.0, 12.0], "y": 0.06, "material": PAVERS},
                {"name": "street_on", "min": [-40.0, 0.0], "max": [0.0, 12.0], "y": 0.0, "material": BRICKS}],
     "canal": {"z": 0.0, "side": -1, "width": 14.0, "x": [-40.0, 70.0], "ends": True, "far_quay": 6.0, "lit": 0.3, "shops": 0.25},
     "lamps": [[8.0, 9.4], [24.0, 9.4], [40.0, 9.4], [56.0, 9.4], [16.0, 3.2], [48.0, 3.2], [66.0, 3.2]],
     "rows": [{"from": -40.0, "to": -0.05, "line": 12.0, "facing": "north", "lit": 0.3, "shops": 0.4}]}
o["facades"] = [
    front("north", 0.0, 8.5, 12.0, [4.2, 3.3, 3.1, 2.9], 3, "neck", 501, shop("KAASHANDEL DE KOE", "snack", "KAAS"), gable_h=3.8),
    front("north", 8.55, 17.0, 12.0, [4.2, 3.3, 3.1, 2.9, 2.7], 4, "cornice", 502, shop("SOUVENIRS · TULPEN", "souvenir", "SOUVENIRS")),
    front("north", 17.05, 24.0, 12.0, [4.0, 3.2, 3.0, 2.8], 3, "bell", 503, door_bay=1, stoop=0.5, gable_h=3.6),
    front("north", 24.05, 33.0, 12.0, [4.2, 3.3, 3.1, 2.9], 3, "step", 504, shop("BOLLENHUIS", "books", "BOLLEN"), gable_h=3.8),
    front("north", 33.05, 42.0, 12.0, [4.2, 3.3, 3.1, 2.9], 4, "cornice", 505, shop("CAFÉ HET BLOEMPJE", "cafe", "CAFÉ")),
    front("north", 42.05, 50.0, 12.0, [4.0, 3.3, 3.1, 2.9], 3, "neck", 506, shop("COFFEESHOP TULP", "coffeeshop", "COFFEESHOP"), gable_h=3.8),
    front("north", 50.05, 58.0, 12.0, [4.2, 3.2, 3.0, 2.8], 3, "spout", 507, door_bay=1, stoop=0.5, gable_h=3.4),
    front("north", 58.05, 70.0, 12.0, [4.4, 3.4, 3.2, 3.0, 2.8], 5, "cornice", 508, shop("HOTEL DE MUNT", "hotel", "HOTEL", awning=False), lit=0.55)]
F["outdoor"] = o
STALL_X = [4.0, 11.5, 19.0, 30.5, 38.0, 45.5, 53.0, 60.5]   # stall centres along the quay; the one at 30.5 is open
ENTER = 30.5
props = []
names = ["BLOEMEN · BOLLEN", "TULPEN", "BOLLEN · ZADEN", "BLOEMENKRAAM 4", "TULPEN · ROZEN", "BLOEMEN", "CACTUSSEN", "BOLLEN"]
for k, x in enumerate(STALL_X):
    p = {"type": "flower_stall", "pos": [x, 0.0, 0.0], "yaw": 0, "size": [7.0, 4.0, 4.5], "seed": 600 + k, "name": names[k], "collide": False}
    if x == ENTER:
        p.update({"enter": True, "gap": [-0.9, 0.9], "size": [7.0, 4.0, 4.5 + 2 * T]})
    elif k in (1, 5, 7):
        p["shutter"] = 0.85 if k != 5 else 0.5
    props.append(p)
for x in (8.0, 15.5, 23.0, 34.5, 42.0, 49.5, 57.0):   # a few buckets out on the quay, a cart, a bike
    props.append({"type": "model", "model": "ph:planter_box_01", "pos": [x, 0.06, 1.0], "yaw": 0, "scale": 1.0, "collide": False})
props += [{"type": "bike", "pos": [20.0, 0.06, 10.6], "yaw": 2, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 120},
          {"type": "bike", "pos": [44.0, 0.0, 6.4], "yaw": 70, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 121},
          {"type": "model", "model": "ph:watering_can_metal_01", "pos": [27.0, 0.06, 1.4], "yaw": 40, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:garden_gnome", "pos": [34.2, 0.06, 0.9], "yaw": 160, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:hand_truck", "pos": [55.5, 0.06, 1.6], "yaw": 80, "scale": 1.0, "collide": False},
          {"type": "crowd_barrier", "pos": [0.6, 0.0, 6.0], "yaw": 90, "size": [11.0, 1.1, 0.7], "seed": 5, "tape": True}]
F["props"] = props
F["walls"] = {"east": {"openings": [{"kind": "passage", "center": 6.0, "width": 12.0, "height": 10.0}]},
              "north": {"openings": [{"kind": "passage", "center": ENTER, "width": 1.8, "height": 2.2}]}}
F["lights"] = [SUN, {"kind": "point", "pos": [ENTER, 2.6, 0.5], "color": [1.0, 0.85, 0.65], "blender_power": 0, "godot_energy": 0.6, "range": 7.0}]
F["shots"] = [
    {"id": "a", "pos": [68.5, 3.5, 9.0], "look_at": [40.0, 1.6, 2.5], "fov": 58, "zone": {"min": [50.0, 0.0], "max": [70.0, 12.0]}, "priority": 1},
    {"id": "b", "pos": [53.0, 3.5, 9.2], "look_at": [24.0, 1.6, 2.0], "fov": 58, "zone": {"min": [30.0, 0.0], "max": [50.0, 12.0]}, "priority": 1},
    {"id": "c", "pos": [36.0, 3.5, 9.2], "look_at": [8.0, 1.6, 2.0], "fov": 58, "zone": {"min": [12.0, 0.0], "max": [30.0, 12.0]}, "priority": 1},
    {"id": "d", "pos": [3.5, 3.6, 8.8], "look_at": [44.0, 6.5, 3.0], "fov": 58, "zone": {"min": [0.0, 0.0], "max": [12.0, 12.0]}, "priority": 1}]
F["spawns"] = {"from_muntplein": {"pos": [68.5, 0.0, 6.0], "yaw": 90}, "from_bloemenkraam": {"pos": [ENTER, 0.06, 1.0], "yaw": 180}}
F["interactables"] = [
    {"id": "stalls", "kind": "examine", "pos": [12.0, 1.0, 0.6], "radius": 1.6,
     "text": "Tulips in their buckets, still fresh. The stalls rock on their pontoons, though there's no wind."},
    {"id": "koningsplein", "kind": "examine", "pos": [1.0, 1.0, 6.0], "radius": 1.8,
     "text": "Barriers across the street toward Koningsplein. Something has been pushing against them from the other side."},
    {"id": "kraam", "kind": "examine", "pos": [ENTER + 1.6, 1.0, 0.5], "radius": 1.0, "text": "Stall four. Its shutter is up, the light still on inside."}]
F["enemies"] = [{"id": "tussen_de_kramen", "kind": "verdronkene", "pos": [46.0, 0.06, 1.8], "yaw": 250},
                {"id": "op_de_kade", "kind": "verdronkene", "pos": [16.0, 0.0, 6.0], "yaw": 100}]
write(F)

# ── Stall four: inside the glasshouse, buckets and packets and the till ───────────────────
KO = [FO[0] + ENTER - 3.5, FO[1] - T - 4.5]
K = shop_room("bloemenkraam", "Bloemenkraam 4", KO, (7.0, 4.5), 2.8,
              "a stall of the floating flower market, inside: staging of buckets of tulips, boards of bulb packets, the till at the "
              "front; through the glass at the back, the black water of the Singel.",
              {"floor": {"ph": "wood_floor_worn", "tint": [0.55, 0.45, 0.38], "rough": 0.6},
               "wall": {"ph": "wood_peeling_paint_weathered", "tint": [0.35, 0.6, 0.4], "scale": 1.0},
               "ceiling": {"color": [0.8, 0.82, 0.78], "rough": 0.6}, "skirting": None}, exposure=0.95)
K["walls"] = {"south": {"facade": True, "openings": [{"kind": "passage", "center": 3.5, "width": 1.8, "height": 2.2}]},
              "north": {"openings": [{"kind": "window", "center": 1.8, "width": 2.4, "sill": 0.9, "height": 1.5},
                                     {"kind": "window", "center": 5.2, "width": 2.4, "sill": 0.9, "height": 1.5}]}}
K["props"] = [
    {"type": "counter", "pos": [5.6, 0.0, 3.4], "size": [1.6, 0.95, 0.6], "yaw": -90},
    {"type": "shelving", "pos": [0.3, 0.0, 2.2], "size": [3.6, 2.0, 0.45], "yaw": 90, "palette": "souvenir", "empty": 0.3, "seed": 7, "shelves": 4},
    {"type": "model", "model": "ph:seeding_tray_01", "pos": [2.0, 0.9, 0.6], "yaw": 0, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:garden_gnome", "pos": [6.5, 0.0, 0.5], "yaw": 220, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:watering_can_metal_01", "pos": [1.2, 0.0, 3.9], "yaw": 70, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:wicker_basket_01", "pos": [3.4, 0.0, 0.6], "yaw": 10, "scale": 1.0, "collide": False},
    {"type": "strip_light", "pos": [3.5, 2.8, 2.2], "size": [4.0, 0.1, 0.2], "collide": False, "color": [1.0, 0.95, 0.85]},
    {"type": "flower_buckets", "pos": [3.5, 0.0, 1.0], "size": [5.6, 0.6, 0.9], "yaw": 0, "seed": 77, "collide": True}]
K["lights"] = [{"kind": "area", "pos": [3.5, 2.75, 2.2], "look_at": [3.5, 0.0, 2.2], "size": 2.0, "color": [1.0, 0.92, 0.8], "blender_power": 140, "godot_energy": 0.7, "range": 6.0}]
K["shots"] = [
    {"id": "a", "pos": [6.6, 2.3, 4.2], "look_at": [1.2, 0.9, 0.8], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [3.5, 4.5]}, "priority": 1},
    {"id": "b", "pos": [0.4, 2.3, 4.1], "look_at": [6.0, 0.9, 0.8], "fov": 64, "zone": {"min": [3.5, 0.0], "max": [7.0, 4.5]}, "priority": 1}]
K["spawns"] = {"from_street": {"pos": [3.5, 0.0, 4.0], "yaw": 0}}
K["interactables"] = [
    {"id": "dressing", "kind": "pickup", "item": "med_small", "count": 1, "pos": [5.6, 0.97, 3.0], "radius": 0.9},
    {"id": "tin", "kind": "examine", "pos": [5.2, 1.0, 3.8], "radius": 0.9,
     "text": "A first aid tin under the till, the kind every stall keeps for thorns and cut fingers."},
    {"id": "window", "kind": "examine", "pos": [3.5, 1.0, 0.4], "radius": 1.7,
     "text": "Through the glass, the Singel. Something pale turns over under the surface and is gone."}]
K["enemies"] = []
write(K)

# ── Rembrandtplein: the way west into Reguliersbreestraat ─────────────────────────────────
H = json.load(open(R + "rembrandtplein.json"))
H["walls"]["west"] = {"openings": [{"kind": "passage", "center": 5.0, "width": 10.0, "height": 10.0}]}
H["interactables"] = [i for i in H["interactables"] if i["id"] != "to_reguliersbreestraat"]
H["interactables"].append({"id": "to_reguliersbreestraat", "kind": "door", "pos": [0.2, 1.0, 5.0], "radius": 1.6,
                           "target_room": "reguliersbreestraat", "target_spawn": "from_rembrandtplein"})
H["spawns"]["from_reguliersbreestraat"] = {"pos": [2.5, 0.0, 5.0], "yaw": -90}
json.dump(H, open(R + "rembrandtplein.json", "w"), indent=2, ensure_ascii=True)
open(R + "rembrandtplein.json", "a").write("\n")
print("doors: apotheek", round(apo_c, 3), round(apo_w, 3), round(apo_h, 3), "bioscoop", round(cin_c, 3), round(cin_w, 3), round(cin_h, 3))
