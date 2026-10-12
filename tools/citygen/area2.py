# damned_waters/tools/citygen/area2.py
# Generates game/data/rooms/thorbeckeplein.json and rembrandtplein.json (area 2), then they are data.
from pathlib import Path
import json, random
R = str(Path(__file__).resolve().parents[2] / "game" / "data" / "rooms") + "/"
SKY = {"hdri": "kloppenheim_07_puresky", "strength": 0.045, "camera": 0.1, "tint": [1.0, 0.76, 0.55]}
ROOMS = ["warm_bar", "fireplace", "small_empty_room_2", "christmas_photo_studio_04", "warm_restaurant_night", "unfinished_office_night"]
WET = lambda ph, tint, wet=0.7, pud=0.3: {"ph": ph, "tint": tint, "wet": wet, "puddles": pud * 0.6, "puddle_scale": 0.9}
LOOK = {   # sign, frame, font, awning
    "cafe": ([1.0, 0.8, 0.5], [0.2, 0.05, 0.035], "DejaVuSerif-BoldItalic.ttf", None),
    "coffeeshop": ([0.35, 1.0, 0.4], [0.03, 0.12, 0.05], "DejaVuSans-Bold.ttf", [[0.05, 0.3, 0.08], [0.85, 0.75, 0.1]]),
    "restaurant": ([1.0, 0.3, 0.18], [0.06, 0.05, 0.05], "DejaVuSerif-Bold.ttf", [[0.45, 0.06, 0.05], [0.78, 0.74, 0.66]]),
    "bar": ([1.0, 0.2, 0.6], [0.03, 0.03, 0.04], "DejaVuSans-Bold.ttf", None),
    "hotel": ([0.95, 0.9, 0.8], [0.12, 0.1, 0.08], "DejaVuSerif-Bold.ttf", None),
}
ROOM_OF = {"cafe": "warm_bar", "coffeeshop": "warm_bar", "restaurant": "warm_restaurant_night", "bar": "warm_bar", "hotel": "fireplace"}


def shop(name, kind, blade=None, door_bay=1, power=85.0, awning=True):
    sign, frame, font, aw = LOOK[kind]
    s = {"name": name, "kind": kind, "room": ROOM_OF[kind], "sign": sign, "frame": frame, "font": font, "glow": 0.3,
         "power": power * 0.32, "door_bay": door_bay, "blade": blade or name.split()[-1], "neon": kind in ("bar", "coffeeshop")}
    if aw and awning:
        s["awning"] = aw
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


def table_group(props, x, z, rng, n=2, fallen=0):
    for i in range(n):
        p = {"type": "model", "model": "ph:outdoor_table_chair_set_01", "pos": [round(x + i * 1.6 + rng.uniform(-0.2, 0.2), 2), 0.0,
             round(z + rng.uniform(-0.25, 0.25), 2)], "yaw": rng.choice([0, 10, -10, 90, 80]), "scale": 1.0, "size": [1.0, 0.8, 1.0]}
        if i < fallen:
            p.update({"roll": 84, "pos": [p["pos"][0], 0.0, p["pos"][2]]})
        props.append(p)


# ── Thorbeckeplein: the bar street, terraces under the trees down the middle ───────────
rng = random.Random(7)
T = {"_file": "damned_waters/game/data/rooms/thorbeckeplein.json — RoomSpec for Thorbeckeplein (the city storey): the short wide street of bars, clubs, a coffeeshop and restaurants running from the Herengracht up to Rembrandtplein, its middle a strip of plane trees hung with strings of bulbs over the terraces. Modelled after openly licensed night photos; every business name is made up. The power is still on; nobody is there. Outdoor: no walls or roof of its own (street.py and city.py build it). Single source of truth for Blender (render) and the engine (collision, cameras, things).",
     "id": "thorbeckeplein", "display_name": "Thorbeckeplein", "storey": 10, "origin": [1000.0, 0.0],
     "bounds": {"min": [0.0, 0.0], "max": [24.0, 64.0]}, "height": 8.0,
     "materials": {"floor": {"color": [0.2, 0.2, 0.2]}, "wall": {"color": [0.2, 0.2, 0.2]}, "ceiling": {"color": [0.2, 0.2, 0.2]}},
     "footsteps": "marble", "ambience": "amb_cellar", "move_scale": 1.0, "world": {"color": [0.014, 0.019, 0.036], "strength": 1.0},
     "sky": SKY, "render": {"exposure": 0.85, "bloom": {"threshold": 0.9, "strength": 0.4, "size": 0.55}}}
o = {"window_rooms": ROOMS, "lamp_power": 360.0, "lamp_energy": 1.0,
     "ground": [{"name": "pavement_w", "min": [-40.0, 0.0], "max": [3.0, 64.0], "y": 0.0, "material": WET("square_concrete_pavers", [0.75, 0.74, 0.72], 0.55, 0.2)},
                {"name": "road_w", "min": [3.0, 0.0], "max": [7.5, 64.0], "y": -0.1, "material": WET("herringbone_brick", [0.8, 0.72, 0.66], 0.8, 0.45)},
                {"name": "strip", "min": [7.5, 0.0], "max": [16.5, 64.0], "y": 0.05, "material": WET("brick_pavement_02", [0.72, 0.68, 0.64], 0.65, 0.3)},
                {"name": "road_e", "min": [16.5, 0.0], "max": [21.0, 64.0], "y": -0.1, "material": WET("herringbone_brick", [0.8, 0.72, 0.66], 0.8, 0.45)},
                {"name": "pavement_e", "min": [21.0, 0.0], "max": [60.0, 64.0], "y": 0.0, "material": WET("square_concrete_pavers", [0.75, 0.74, 0.72], 0.55, 0.2)},
                {"name": "quay", "min": [-40.0, 64.0], "max": [60.0, 66.0], "y": 0.0, "material": WET("brick_pavement_02", [0.72, 0.68, 0.64], 0.7, 0.4)}],
     "canal": {"z": 66.0, "width": 25.0, "water": -1.6, "x": [-60.0, 90.0], "far_quay": 6.0, "lit": 0.25},
     "lamps": [[7.8, 6.0], [16.2, 14.0], [7.8, 22.0], [16.2, 30.0], [7.8, 38.0], [16.2, 46.0], [7.8, 54.0], [16.2, 62.0], [2.0, 63.2]]}
o["facades"] = [
    front("east", 0.0, 9.5, 0.0, [4.2, 3.4, 3.2, 3.0], 3, "cornice", 101, shop("CAFÉ DE KROONLUCHTER", "cafe", "CAFÉ")),
    front("east", 9.55, 18.5, 0.0, [4.0, 3.3, 3.1, 2.9], 3, "neck", 102, shop("CLUB NACHTVLINDER", "bar", "CLUB"), gable_h=3.8),
    front("east", 18.55, 27.5, 0.0, [4.0, 3.2, 3.0, 2.8], 3, "bell", 103, shop("COFFEESHOP GROENE VLINDER", "coffeeshop", "COFFEESHOP"), gable_h=3.6),
    front("east", 27.55, 37.0, 0.0, [3.8, 3.3, 3.1, 2.9, 2.6], 4, "cornice", 104, door_bay=2, stoop=0.75),
    front("east", 37.05, 47.5, 0.0, [4.0, 3.3, 3.1, 2.9], 4, "step", 105, shop("RISTORANTE DA PIETRO", "restaurant", "DA PIETRO"), gable_h=3.8),
    front("east", 47.55, 58.0, 0.0, [4.2, 3.4, 3.2, 3.0, 2.7], 5, "cornice", 106, shop("HOTEL DE NACHTEGAAL", "hotel", "HOTEL", awning=False), lit=0.55),
    front("west", 0.0, 9.0, 24.0, [4.0, 3.2, 3.0, 2.8], 3, "spout", 111, shop("KARAOKE", "bar"), gable_h=3.4),
    front("west", 9.05, 18.0, 24.0, [4.0, 3.3, 3.1, 2.9], 3, "neck", 112, shop("STEAKHOUSE PAMPA", "restaurant", "PAMPA"), gable_h=4.0),
    front("west", 18.05, 27.0, 24.0, [4.0, 3.2, 3.0, 2.8], 3, "bell", 113, shop("BAR ZEVEN", "bar", "7"), gable_h=3.6),
    front("west", 27.05, 36.0, 24.0, [3.8, 3.3, 3.1, 2.9], 3, "neck", 114, door_bay=1, stoop=0.5, gable_h=3.8),
    front("west", 36.05, 46.0, 24.0, [4.0, 3.3, 3.1, 2.9], 4, "cornice", 115, shop("THE LAZY OWL COFFEESHOP", "coffeeshop", "COFFEESHOP")),
    front("west", 46.05, 55.0, 24.0, [4.0, 3.2, 3.0, 2.8], 3, "step", 116, shop("PANNENKOEKENHUIS", "restaurant", "PANNENKOEKEN"), gable_h=3.6),
    front("west", 55.05, 64.0, 24.0, [4.0, 3.3, 3.1, 2.9], 3, "bell", 117, shop("CAFÉ 'T HOEKJE", "cafe", "CAFÉ"), gable_h=3.6),
    # the Herengracht's fronts running on west and east from the corners
    front("south", -30.0, -0.05, 64.0 - 64.0 - 0.0001, [3.9, 3.3, 3.1, 2.9], 5, "cornice", 120, door_bay=2, stoop=0.75),
]
o["facades"].pop()   # (the canal's other houses come with the canal's far bank)
strings, props = [], []
for k, z in enumerate(range(4, 62, 8)):   # two rows of plane trees, bulbs strung across and along
    for x in (9.5, 14.5):
        props.append({"type": "plane_tree", "pos": [x, 0.05, float(z)], "size": [0.45, 12.0, 0.45], "seed": 300 + k * 2 + int(x), "depth": 6,
                      "leaves": 3, "leaf_color": [0.45, 0.33, 0.08]})
    strings.append([[9.5, 4.2, float(z)], [14.5, 4.2, float(z)], 0.5, 0.45])
    if z + 8 < 62:
        strings.append([[9.5, 4.2, float(z)], [14.5, 4.2, float(z + 8)], 0.7, 0.5])
        strings.append([[14.5, 4.2, float(z)], [9.5, 4.2, float(z + 8)], 0.7, 0.5])
o["strings"] = strings
for z in (8.0, 24.0, 40.0, 50.0):   # terraces under the trees, some chairs knocked over
    table_group(props, 10.4, z, rng, n=2, fallen=1 if z in (24.0, 50.0) else 0)
    props.append({"type": "heater", "pos": [12.0, 0.05, z + 2.4], "size": [0.5, 2.2, 0.5], "power": 50.0})
    props.append({"type": "windbreak", "pos": [12.0, 0.05, z - 1.6], "size": [5.0, 1.5, 0.1], "collide": False})
for z in (4.0, 20.0, 36.0, 52.0):   # the pavement terraces in front of the cafés
    table_group(props, 0.8, z, rng, n=1)
    table_group(props, 22.0, z + 4.0, rng, n=1, fallen=1 if z == 36.0 else 0)
props += [{"type": "kiosk", "pos": [12.0, 0.05, 1.8], "size": [2.6, 3.2, 2.6], "name": "TABAK · KRANTEN"},
          {"type": "bollard", "pos": [3.2, 0.0, 63.0], "size": [0.2, 0.9, 0.2]},
          {"type": "bike", "pos": [6.0, 0.0, 63.2], "yaw": 0, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 31},
          {"type": "bike", "pos": [1.6, 0.05, 30.0], "yaw": 95, "roll": 85, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 32},
          {"type": "model", "model": "ph:standing_chalkboard_01", "pos": [2.6, 0.0, 13.0], "yaw": 120, "scale": 0.8, "collide": False},
          {"type": "model", "model": "ph:standing_chalkboard_01", "pos": [21.2, 0.0, 49.0], "yaw": -60, "scale": 0.8, "collide": False},
          {"type": "model", "model": "ph:trashbag", "pos": [1.2, 0.0, 44.5], "yaw": 30, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:street_rat", "pos": [12.8, 0.05, 25.0], "yaw": 40, "scale": 1.0, "collide": False}]
T["outdoor"] = o
T["props"] = props
T["walls"] = {"north": {"openings": [{"kind": "passage", "center": 12.0, "width": 24.0, "height": 8.0}]},
              "west": {"openings": [{"kind": "passage", "center": 61.0, "width": 5.0, "height": 6.0}]}}
T["lights"] = [{"kind": "sun", "dir_from": [-0.35, 0.55, 1.0], "color": [0.55, 0.66, 1.0], "blender_power": 0.12, "godot_energy": 0.25, "angle": 2.0},
               {"kind": "point", "pos": [12.0, 3.8, 24.0], "color": [1.0, 0.72, 0.38], "blender_power": 0, "godot_energy": 0.5, "range": 10.0},
               {"kind": "point", "pos": [12.0, 3.8, 48.0], "color": [1.0, 0.72, 0.38], "blender_power": 0, "godot_energy": 0.5, "range": 10.0}]
T["shots"] = [
    {"id": "a", "pos": [3.5, 2.6, 62.5], "look_at": [14.0, 1.8, 30.0], "fov": 58, "zone": {"min": [0.0, 46.0], "max": [24.0, 64.0]}, "priority": 1},
    {"id": "b", "pos": [19.0, 2.8, 52.0], "look_at": [7.0, 1.4, 32.0], "fov": 58, "zone": {"min": [0.0, 30.0], "max": [24.0, 46.0]}, "priority": 1},
    {"id": "c", "pos": [5.0, 2.8, 10.0], "look_at": [18.0, 1.4, 28.0], "fov": 58, "zone": {"min": [0.0, 14.0], "max": [24.0, 30.0]}, "priority": 1},
    {"id": "d", "pos": [18.8, 3.0, 26.0], "look_at": [9.0, 2.8, 0.0], "fov": 60, "zone": {"min": [0.0, 0.0], "max": [24.0, 14.0]}, "priority": 1}]
T["spawns"] = {"from_herengracht": {"pos": [4.0, 0.0, 57.0], "yaw": -45}, "from_rembrandtplein": {"pos": [12.0, 0.0, 1.5], "yaw": 180}}
T["interactables"] = [
    {"id": "to_herengracht", "kind": "door", "pos": [0.2, 1.0, 61.0], "radius": 1.6, "target_room": "herengracht", "target_spawn": "from_thorbeckeplein"},
    {"id": "terraces", "kind": "examine", "pos": [11.2, 1.0, 24.0], "radius": 1.6, "text": "Glasses half full, a jacket on a chair. The heaters are still burning for nobody."},
    {"id": "groene_vlinder", "kind": "examine", "pos": [0.6, 1.0, 23.0], "radius": 1.4, "text": "Coffeeshop Groene Vlinder. The door's open; the menu board still says what's in today."},
    {"id": "hotel", "kind": "examine", "pos": [0.6, 1.0, 52.8], "radius": 1.4, "text": "Hotel de Nachtegaal. Every light in the lobby is on. The bell on the desk is wet."},
    {"id": "shells_terrace", "kind": "pickup", "item": "shotgun_shells", "count": 4, "pos": [10.6, 0.82, 40.2], "radius": 0.9},
    {"id": "ammo_kiosk", "kind": "pickup", "item": "handgun_ammo", "count": 10, "pos": [12.0, 0.05, 3.4], "radius": 0.9}]
T["enemies"] = [{"id": "op_het_terras", "kind": "verdronkene", "pos": [13.0, 0.05, 26.0], "yaw": 200},
                {"id": "bij_de_club", "kind": "verdronkene", "pos": [2.5, 0.0, 14.0], "yaw": 90},
                {"id": "in_de_deur", "kind": "verdronkene", "pos": [22.6, 0.0, 22.5], "yaw": -90}]
json.dump(T, open(R + "thorbeckeplein.json", "w"), indent=2, ensure_ascii=True)
open(R + "thorbeckeplein.json", "a").write("\n")
print("thorbeckeplein", len(props), "props")

# the quay's houses running west and east from the corners, a few of them shops
T["outdoor"]["rows"] = [{"from": -40.0, "to": -0.05, "line": 64.0, "facing": "south", "lit": 0.3, "shops": 0.25},
                        {"from": 24.05, "to": 64.0, "line": 64.0, "facing": "south", "lit": 0.3, "shops": 0.25}]
json.dump(T, open(R + "thorbeckeplein.json", "w"), indent=2, ensure_ascii=True)
open(R + "thorbeckeplein.json", "a").write("\n")

# ── Rembrandtplein: the square, its park, its statue, its neon, a tram at the stop ──────
rng = random.Random(11)
P = {"_file": "damned_waters/game/data/rooms/rembrandtplein.json — RoomSpec for Rembrandtplein (the city storey): the square of big cafés and clubs round a park, the painter on his plinth in the middle, neon on the roofs, a tram stopped at the stop with its lights on and its doors open. Modelled after openly licensed night photos; every business name is made up. The power is still on; nobody is there. Outdoor (street.py and city.py build it). Single source of truth for Blender (render) and the engine (collision, cameras, things).",
     "id": "rembrandtplein", "display_name": "Rembrandtplein", "storey": 10, "origin": [980.0, -50.3],
     "bounds": {"min": [0.0, 0.0], "max": [60.0, 50.0]}, "height": 10.0,
     "materials": {"floor": {"color": [0.2, 0.2, 0.2]}, "wall": {"color": [0.2, 0.2, 0.2]}, "ceiling": {"color": [0.2, 0.2, 0.2]}},
     "footsteps": "marble", "ambience": "amb_cellar", "move_scale": 1.0, "world": {"color": [0.014, 0.019, 0.036], "strength": 1.0},
     "sky": SKY, "render": {"exposure": 0.85, "bloom": {"threshold": 0.85, "strength": 0.45, "size": 0.6}}}
o = {"window_rooms": ROOMS, "lamp_power": 380.0, "lamp_energy": 1.0,
     "ground": [{"name": "square", "min": [0.0, -30.0], "max": [90.0, 50.3], "y": 0.0, "material": WET("herringbone_brick", [0.8, 0.72, 0.66], 0.75, 0.4)},
                {"name": "pavement_w", "min": [0.0, -30.0], "max": [5.0, 50.3], "y": 0.06, "material": WET("square_concrete_pavers", [0.75, 0.74, 0.72], 0.55, 0.2)},
                {"name": "pavement_e", "min": [55.0, -30.0], "max": [90.0, 50.3], "y": 0.06, "material": WET("square_concrete_pavers", [0.75, 0.74, 0.72], 0.55, 0.2)},
                {"name": "pavement_n", "min": [5.0, -30.0], "max": [55.0, 3.5], "y": 0.06, "material": WET("square_concrete_pavers", [0.75, 0.74, 0.72], 0.55, 0.2)}],
     "parks": [{"min": [15.0, 13.0], "max": [45.0, 39.0], "paths": [[28.5, 13.0, 31.5, 39.0], [15.0, 24.5, 45.0, 27.5]]}],
     "tracks": [{"from": [0.0, 7.0], "to": [90.0, 7.0], "y": 0.0}],
     "lamps": [[13.5, 12.0], [46.5, 12.0], [13.5, 40.0], [46.5, 40.0], [30.0, 11.5], [13.5, 26.0], [46.5, 26.0], [6.0, 22.0], [54.0, 30.0]],
     "rooftop_signs": [{"at": [62.5, 15.4, 18.0], "text": "ZILVERMEEUW BIER", "color": [1.0, 0.18, 0.12], "size": 1.4, "yaw": -90.0},
                       {"at": [30.0, 16.6, -1.5], "text": "GRAND CAFÉ", "color": [1.0, 0.75, 0.3], "size": 1.4, "yaw": 0.0}],
     "strings": [[[1.5, 3.4, 4.0 + 6 * i], [1.5, 3.4, 10.0 + 6 * i], 0.35, 0.45] for i in range(1, 7)]}
o["facades"] = [
    # the west side: the big cafés with their terraces
    # (z 0 to 10: Reguliersbreestraat runs off west, to the Munt)
    front("east", 10.05, 22.0, 0.0, [4.6, 3.6, 3.4, 3.2], 5, "cornice", 201, shop("GRAND CAFÉ DE LANTAARN", "cafe", "CAFÉ", door_bay=2, power=100.0)),
    front("east", 22.05, 31.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 202, shop("CAFÉ DE SCHUTTERIJ", "cafe", "CAFÉ"), gable_h=4.0),
    front("east", 31.05, 40.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "cornice", 203, shop("EETCAFÉ HET SCHILDERIJ", "restaurant", "EETCAFÉ")),
    front("east", 40.05, 50.0, 0.0, [4.4, 3.3, 3.1, 2.9], 4, "bell", 204, shop("COFFEESHOP HAZE", "coffeeshop", "COFFEESHOP"), gable_h=3.6),
    # the east side: clubs and bars, the neon on the roof above
    front("west", 0.0, 10.0, 60.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 211, shop("CLUB NEONZAAL", "bar", "CLUB")),
    front("west", 10.05, 19.0, 60.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 212, shop("KARAOKE BAR DE STER", "bar", "KARAOKE"), gable_h=3.8),
    front("west", 19.05, 29.0, 60.0, [4.4, 3.4, 3.2, 3.0], 4, "cornice", 213, shop("STEAKHOUSE TORO", "restaurant", "STEAKS")),
    front("west", 29.05, 38.0, 60.0, [4.4, 3.4, 3.2, 3.0], 3, "spout", 214, shop("BAR HET GOUDEN KALF", "bar", "BAR"), gable_h=3.4),
    front("west", 38.05, 50.0, 60.0, [4.6, 3.6, 3.4, 3.2], 5, "cornice", 215, shop("DISCOTHEEK MAANLICHT", "bar", "DISCO", power=110.0)),
    # the north side, behind the tram: a hotel and cafés
    front("south", 0.0, 14.0, 0.0, [4.8, 3.6, 3.4, 3.2, 3.0, 2.8], 6, "cornice", 221, shop("HOTEL RIJNZICHT", "hotel", "HOTEL", door_bay=3, awning=False), lit=0.55),
    front("south", 14.05, 23.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 222, shop("IJSSALON NAPOLI", "restaurant", "GELATO"), gable_h=3.8),
    front("south", 23.05, 37.0, 0.0, [4.8, 3.8, 3.6, 3.4], 5, "cornice", 223, shop("GRAND CAFÉ DE KROON", "cafe", "GRAND CAFÉ", door_bay=2, power=110.0)),
    front("south", 37.05, 46.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "bell", 224, shop("PIZZERIA DA ROSA", "restaurant", "PIZZA"), gable_h=3.6),
    front("south", 46.05, 60.0, 0.0, [4.6, 3.6, 3.4, 3.2], 5, "cornice", 225, shop("CAFÉ HOLLANDIA", "cafe", "CAFÉ")),
    # the south side either side of Thorbeckeplein
    front("north", 0.0, 9.5, 50.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 231, shop("FRITES · SNACKS", "restaurant", "FRITES"), gable_h=3.8),
    front("north", 9.55, 19.95, 50.0, [4.4, 3.4, 3.2, 3.0], 4, "cornice", 232, door_bay=1, stoop=0.5),
    front("north", 44.05, 52.0, 50.0, [4.4, 3.4, 3.2, 3.0], 3, "step", 233, shop("CAFÉ DE OUDE WACHT", "cafe", "CAFÉ"), gable_h=3.8),
    front("north", 52.05, 60.0, 50.0, [4.4, 3.4, 3.2, 3.0], 3, "bell", 234, shop("SOUVENIRS", "bar", "SOUVENIRS"), gable_h=3.6),
]
props = []
for k, (x, z) in enumerate([(18, 16), (25, 16), (35, 16), (42, 16), (18, 36), (25, 36), (35, 36), (42, 36), (18, 21), (42, 31)]):
    props.append({"type": "plane_tree", "pos": [float(x), 0.04, float(z)], "size": [0.6, 15.0, 0.6], "seed": 400 + k, "depth": 6,
                  "leaves": 4, "leaf_color": [0.42, 0.34, 0.08]})
props += [{"type": "statue", "pos": [30.0, 0.04, 26.0], "size": [1.8, 4.0, 1.8], "name": "REMBRANDT", "plinth": 4.2, "figure": 3.2},
          {"type": "tram", "pos": [36.0, 0.0, 7.0], "yaw": 0, "size": [30.0, 3.4, 2.4], "board": "NIET INSTAPPEN"},
          {"type": "tram_stop", "pos": [34.0, 0.0, 10.4], "yaw": 180, "size": [24.0, 0.25, 2.6], "collide": False},
          {"type": "kiosk", "pos": [50.0, 0.0, 44.0], "size": [2.6, 3.2, 2.6], "name": "BLOEMEN"}]
for x, z in ((20.0, 13.0), (40.0, 13.0), (20.0, 39.0), (40.0, 39.0)):
    props.append({"type": "bench", "pos": [x, 0.04, z + (0.6 if z < 20 else -0.6)], "yaw": 0 if z < 20 else 180, "size": [1.8, 0.85, 0.5]})
for z in (15.0, 27.0, 39.0):   # the west terraces under their strings of bulbs, behind windbreaks
    table_group(props, 1.6, z, rng, n=2, fallen=1 if z == 27.0 else 0)
    table_group(props, 1.6, z + 3.2, rng, n=2)
    props.append({"type": "heater", "pos": [4.6, 0.06, z + 1.6], "size": [0.5, 2.2, 0.5], "power": 50.0})
    props.append({"type": "windbreak", "pos": [5.2, 0.06, z + 2.8], "yaw": 90, "size": [6.0, 1.5, 0.1], "collide": False, "name": "GRAND CAFÉ DE LANTAARN"})
for x in (8.0, 26.0, 50.0):   # the north terraces in front of the hotel and the cafés
    table_group(props, x, 2.2, rng, n=2, fallen=1 if x == 26.0 else 0)
props += [{"type": "bike", "pos": [57.5, 0.06, 22.0 + 0.7 * i], "yaw": 0 if i % 2 else 8, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 50 + i}
          for i in range(5)]
props += [{"type": "bike", "pos": [12.0, 0.05, 45.5], "yaw": 40, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 60},
          {"type": "model", "model": "ph:trashbag", "pos": [55.6, 0.06, 4.0], "yaw": 10, "scale": 1.0, "collide": False},
          {"type": "model", "model": "ph:trashbag", "pos": [56.1, 0.06, 4.6], "yaw": 100, "scale": 0.9, "collide": False},
          {"type": "model", "model": "ph:standing_chalkboard_01", "pos": [4.6, 0.06, 13.6], "yaw": 70, "scale": 0.8, "collide": False}]
P["outdoor"] = o
P["props"] = props
P["walls"] = {"south": {"openings": [{"kind": "passage", "center": 32.0, "width": 24.0, "height": 10.0}]}}
P["lights"] = [{"kind": "sun", "dir_from": [-0.35, 0.55, 1.0], "color": [0.55, 0.66, 1.0], "blender_power": 0.12, "godot_energy": 0.25, "angle": 2.0},
               {"kind": "point", "pos": [36.0, 2.0, 9.0], "color": [1.0, 0.92, 0.8], "blender_power": 0, "godot_energy": 0.8, "range": 8.0},
               {"kind": "point", "pos": [3.0, 3.3, 21.0], "color": [1.0, 0.72, 0.38], "blender_power": 0, "godot_energy": 0.6, "range": 12.0},
               {"kind": "point", "pos": [57.0, 3.0, 25.0], "color": [1.0, 0.3, 0.6], "blender_power": 0, "godot_energy": 0.5, "range": 10.0}]
P["shots"] = [
    {"id": "a", "pos": [32.0, 3.2, 48.5], "look_at": [30.0, 3.4, 18.0], "fov": 62, "zone": {"min": [14.0, 40.0], "max": [46.0, 50.0]}, "priority": 1},
    {"id": "b", "pos": [9.0, 3.2, 46.0], "look_at": [3.0, 1.6, 6.0], "fov": 58, "zone": {"min": [0.0, 0.0], "max": [14.0, 50.0]}, "priority": 1},
    {"id": "c", "pos": [52.0, 3.4, 12.5], "look_at": [55.0, 2.2, 44.0], "fov": 60, "zone": {"min": [46.0, 0.0], "max": [60.0, 50.0]}, "priority": 1},
    {"id": "d", "pos": [6.0, 3.0, 11.0], "look_at": [44.0, 2.0, 6.0], "fov": 58, "zone": {"min": [14.0, 0.0], "max": [46.0, 13.0]}, "priority": 1},
    {"id": "e", "pos": [21.0, 3.4, 37.0], "look_at": [30.0, 4.5, 26.0], "fov": 58, "zone": {"min": [14.0, 13.0], "max": [46.0, 40.0]}, "priority": 1}]
P["spawns"] = {"from_thorbeckeplein": {"pos": [32.0, 0.0, 48.5], "yaw": 0}}
P["interactables"] = [
    {"id": "statue", "kind": "examine", "pos": [30.0, 1.0, 28.6], "radius": 1.6, "text": "Rembrandt, in bronze, looking down at the square. Somebody has hung a bicycle lock round his ankle."},
    {"id": "tram", "kind": "examine", "pos": [36.0, 1.0, 9.0], "radius": 2.0, "text": "Tram 4 to Centraal. The doors stand open and the lights are on. The driver's seat is wet."},
    {"id": "lantaarn", "kind": "examine", "pos": [1.2, 1.0, 16.0], "radius": 1.6, "text": "Grand Café de Lantaarn. Every table set; a birthday cake on one, its candles burned to stubs."},
    {"id": "first_aid_kiosk", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [50.0, 0.9, 45.4], "radius": 1.0},
    {"id": "shells_tram", "kind": "pickup", "item": "shotgun_shells", "count": 6, "pos": [33.0, 0.3, 9.8], "radius": 1.0}]
P["enemies"] = [{"id": "op_het_plein", "kind": "verdronkene", "pos": [26.0, 0.04, 30.0], "yaw": 160},
                {"id": "bij_de_tram", "kind": "verdronkene", "pos": [40.0, 0.0, 9.6], "yaw": 180},
                {"id": "op_het_terras_2", "kind": "verdronkene", "pos": [3.2, 0.06, 30.0], "yaw": 90},
                {"id": "voor_de_club", "kind": "verdronkene", "pos": [56.0, 0.06, 6.0], "yaw": -90}]
json.dump(P, open(R + "rembrandtplein.json", "w"), indent=2, ensure_ascii=True)
open(R + "rembrandtplein.json", "a").write("\n")
print("rembrandtplein", len(props), "props")

# ── The Herengracht runs on east past the bridge into Thorbeckeplein ─────────────────
H = json.load(open(R + "herengracht.json"))
H["walls"]["east"] = {"openings": [{"kind": "passage", "center": 4.2, "width": 4.4, "height": 6.0}]}
H["interactables"] = [i for i in H["interactables"] if i["id"] not in ("bridge", "to_thorbeckeplein")]
H["interactables"].append({"id": "to_thorbeckeplein", "kind": "door", "pos": [39.8, 1.0, 4.2], "radius": 1.6, "target_room": "thorbeckeplein",
                           "target_spawn": "from_herengracht"})
H["interactables"].append({"id": "bridge", "kind": "examine", "pos": [39.4, 1.0, 7.6], "radius": 1.2,
                           "text": "The bridge over the Herengracht. The street runs on east, toward the lights of Thorbeckeplein."})
H["spawns"]["from_thorbeckeplein"] = {"pos": [38.4, 0.0, 4.2], "yaw": 90}
json.dump(H, open(R + "herengracht.json", "w"), indent=2, ensure_ascii=True)
open(R + "herengracht.json", "a").write("\n")
