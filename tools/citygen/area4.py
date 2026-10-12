# damned_waters/tools/citygen/area4.py
# Generates area 4 (storey 12, district 3: Rokin): rokin_zuid, rokin_noord (streets), hotel_lobby,
# politiepost, metro_rokin (shops he walks into); and opens Muntplein's way north (a gap in the
# barriers), handing Rokin's stand-ins over to these rooms. Dressed as the evacuation left it
# (docs/city_aftermath.md).
from pathlib import Path
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import front, shop, shop_doorway, glass_door, street_room, shop_room, write, table_group, PAVERS, BRICKS, SUN, ROOMS, R  # noqa: E402

C.DISTRICT.update({"storey": 12, "name": "district 3: Rokin"})
T = 0.3
ZO = [883.4, -64.3 - 80.0]        # rokin_zuid: the quay at x 0 (the water west of it), the fronts at x 26
NO = [883.4, ZO[1] - T - 80.0]    # rokin_noord, north of it up to the Dam
QUAY = WETQ = C.WET("square_concrete_pavers", [0.7, 0.69, 0.66], 0.75, 0.45)


def lamps(z0, z1, step=12.0):
    return [[1.4, float(z)] for z in range(int(z0) + 4, int(z1), int(step))] + [[24.6, float(z) + 6] for z in range(int(z0) + 4, int(z1) - 6, int(step))]


def ground():
    return [{"name": "quay", "min": [0.0, 0.0], "max": [6.0, 80.0], "y": 0.06, "material": QUAY, "kerb": False},
            {"name": "road", "min": [6.0, 0.0], "max": [22.0, 80.0], "y": 0.0, "material": BRICKS},
            {"name": "pavement_e", "min": [22.0, 0.0], "max": [26.0, 80.0], "y": 0.06, "material": PAVERS}]


def street_shots(specs):
    return [{"id": i, "pos": p, "look_at": l, "fov": f, "zone": {"min": [0.0, z0], "max": [26.0, z1]}, "priority": 1}
            for i, p, l, f, z0, z1 in specs]


# ════════════════════════════════════════════════════════════════════════════════════
# Rokin south: the basin, the tour boats at their piers, the hotel, the museum
# ════════════════════════════════════════════════════════════════════════════════════
rng = random.Random(71)
Z = street_room("rokin_zuid", "Rokin", ZO, (26.0, 80.0), 10.0,
                "the south half of Rokin, the main road north to the Dam and Centraal: the basin along its west side with the "
                "glass-roofed tour boats at their piers (one heeled over, taking water), the trams' rails, a grand hotel, the "
                "Allard Pierson museum in its old bank; dropped luggage, a taxi left with its door open, leaflets everywhere.")
HOTEL = front("west", 19.05, 34.0, 26.0, [4.6, 3.8, 3.6, 3.4, 3.2], 6, "cornice", 701,
              shop("GRAND HOTEL DE KEIZERSKROON", "hotel", "HOTEL", door_bay=5, power=110.0, awning=False, enter=True), lean=0.0, lit=0.6, flags=3)
o = {"window_rooms": ROOMS, "lamp_power": 380.0, "lamp_energy": 1.0, "tide": 0.7,
     "ground": ground(),
     "canals": [{"axis": "z", "x": 0.0, "side": -1, "width": 16.0, "along": [-0.3, 80.3], "ends": "b", "far_quay": 5.0, "lit": 0.3,
                 "shops": 0.3, "far_span": [-0.3, 80.3]}],
     "tracks": [{"from": [14.0, 80.0], "to": [14.0, 0.0], "y": 0.0}],
     "lamps": lamps(0, 80)}
o["facades"] = [
    front("west", 0.0, 10.0, 26.0, [4.4, 3.4, 3.2, 3.0, 2.8], 4, "cornice", 702, shop("RONDVAARTEN · TICKETS", "souvenir", "TICKETS")),
    front("west", 10.05, 19.0, 26.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 703, shop("DIAMANTSLIJPERIJ DE KROON", "jeweller", "DIAMANT", smashed=[1, 3]), gable_h=3.8),
    HOTEL,
    front("west", 34.05, 42.0, 26.0, [4.2, 3.3, 3.1, 2.9], 3, "neck", 704, door_bay=1, stoop=0.5, gable_h=3.8),
    front("west", 42.05, 50.0, 26.0, [4.4, 3.4, 3.2, 3.0], 3, "step", 705, shop("CAFÉ HET BASSIN", "cafe", "CAFÉ"), gable_h=3.6),
    front("west", 50.05, 57.95, 26.0, [4.2, 3.3, 3.1, 2.9], 3, "bell", 706, door_bay=1, stoop=0.75, gable_h=3.6),
    front("west", 58.0, 80.0, 26.0, [5.0, 4.0, 4.0], 5, "cornice", 707, lean=0.0,
          classic={"height": 17.0, "name": "ALLARD PIERSON", "bays": 5, "ground": 5.0,
                   "banners": [("GODEN", (0.45, 0.06, 0.05)), ("MUMMIES", (0.06, 0.1, 0.3))]})]
hc, hw, hh = shop_doorway(HOTEL)
props = []
for k, (z, boat) in enumerate(((22.0, True), (40.0, True), (58.0, False))):   # piers out into the basin, boats along them
    props.append({"type": "pier", "pos": [0.0, 0.0, z], "yaw": 90, "size": [8.0, 0.4, 2.2], "sign": "RONDVAARTEN · CANAL CRUISES" if k == 0 else "",
                  "collide": False})
    if boat:
        props.append({"type": "canal_boat", "pos": [-4.6, -0.95, z + (12.0 if k == 0 else 11.0)], "yaw": 90, "size": [22.0, 2.4, 4.2],
                      "name": "RONDVAART %d" % (3 + k * 4), "collide": False})
props.append({"type": "canal_boat", "pos": [-5.0, -0.95, 70.0], "yaw": 95, "size": [20.0, 2.4, 4.2], "name": "RONDVAART 2",
              "list": 14.0, "sunk": 0.7, "glow": 0.6, "collide": False})   # taking water, heeled over, its lights still on
props += [
    {"type": "railing", "pos": [0.25, 0.0, 40.0], "yaw": 90, "size": [80.0, 1.0, 0.1], "collide": False},
    {"type": "tram", "pos": [14.0, 0.0, 59.3], "yaw": 90, "size": [30.0, 3.4, 2.4], "board": "NIET INSTAPPEN", "power": 260.0},   # the last tram, stopped
    {"type": "evac_board", "pos": [9.0, 0.0, 76.0], "yaw": 0, "size": [1.8, 1.9, 0.6], "arrow": "up", "to": "CENTRAAL", "collide": False},
    {"type": "vehicle", "pos": [19.5, 0.0, 44.0], "yaw": 84, "size": [4.6, 1.5, 1.85], "livery": "taxi", "door_open": "left"},
    {"type": "luggage", "pos": [10.0, 0.0, 68.0], "size": [4.0, 0.0, 3.0], "seed": 1, "cases": 3, "bags": 3, "pushchair": True, "collide": False},
    {"type": "luggage", "pos": [20.0, 0.06, 31.0], "size": [3.0, 0.0, 3.0], "seed": 2, "cases": 4, "bags": 2, "chair": True, "collide": False},
    {"type": "leaflets", "pos": [12.0, 0.0, 40.0], "size": [24.0, 0.0, 76.0], "seed": 3, "count": 260, "collide": False},
    {"type": "fire_pump", "pos": [2.6, 0.06, 50.0], "yaw": 90, "size": [0.9, 0.8, 0.6], "to": [0.0, -3.2]},
    {"type": "sandbags", "pos": [25.3, 0.06, hc - 3.3], "yaw": 90, "size": [4.6, 0.6, 0.45], "seed": 4},
    {"type": "sandbags", "pos": [25.3, 0.06, hc + 3.5], "yaw": 90, "size": [4.6, 0.6, 0.45], "seed": 5},
    {"type": "model", "model": "ph:lifebuoy", "pos": [0.35, 0.55, 33.0], "yaw": 90, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:life_jacket", "pos": [3.4, 0.06, 47.5], "yaw": 30, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:trashbag", "pos": [23.4, 0.06, 8.0], "yaw": 40, "scale": 1.0, "collide": False},
    {"type": "bike", "pos": [23.0, 0.06, 12.0], "yaw": 70, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 140},
    {"type": "bike", "pos": [23.6, 0.06, 13.0], "yaw": 100, "roll": 80, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 141},
    {"type": "bike", "pos": [22.8, 0.06, 13.6], "yaw": 60, "roll": -84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 142}]
Z["outdoor"] = o
Z["props"] = props
Z["walls"] = {"south": {"openings": [{"kind": "passage", "center": 13.0, "width": 26.0, "height": 10.0}]},
              "north": {"openings": [{"kind": "passage", "center": 13.0, "width": 26.0, "height": 10.0}]},
              "east": {"openings": [glass_door(hc, hw, hh)]}}
Z["lights"] = [SUN, {"kind": "point", "pos": [14.0, 2.6, 59.3], "color": [1.0, 0.9, 0.75], "blender_power": 0, "godot_energy": 0.6, "range": 8.0},
               {"kind": "point", "pos": [19.5, 1.0, 46.5], "color": [1.0, 0.95, 0.85], "blender_power": 0, "godot_energy": 0.4, "range": 5.0}]
Z["shots"] = street_shots([
    ("a", [21.5, 3.4, 57.0], [7.0, 2.0, 79.0], 62, 60.0, 80.0),
    ("b", [2.0, 3.6, 63.0], [12.0, 1.0, 40.0], 62, 40.0, 60.0),
    ("c", [21.5, 3.4, 18.0], [5.0, 1.6, 40.0], 62, 20.0, 40.0),
    ("d", [4.0, 3.4, 23.0], [18.0, 3.0, -12.0], 60, 0.0, 20.0)])
Z["spawns"] = {"from_muntplein": {"pos": [13.0, 0.0, 78.4], "yaw": 0}, "from_hotel": {"pos": [24.6, 0.06, hc], "yaw": 90}}
Z["interactables"] = [
    {"id": "to_muntplein", "kind": "door", "pos": [13.0, 1.0, 79.8], "radius": 1.6, "target_room": "muntplein", "target_spawn": "from_rokin"},
    {"id": "door_hotel", "kind": "door", "pos": [25.55, 1.0, hc], "radius": 1.0},
    {"id": "boats", "kind": "examine", "pos": [1.0, 1.0, 34.0], "radius": 1.6,
     "text": "The tour boats, moored for the night. One of them is heeling over, slowly filling. Its lights are still on inside."},
    {"id": "taxi", "kind": "examine", "pos": [20.5, 1.0, 46.6], "radius": 1.2, "text": "The meter's still running. The keys are in it. The driver's door is open; the seat is soaked."},
    {"id": "ammo_taxi", "kind": "pickup", "item": "handgun_ammo", "count": 8, "pos": [21.0, 0.06, 47.2], "radius": 0.9},
    {"id": "museum", "kind": "examine", "pos": [25.0, 1.0, 69.0], "radius": 1.6, "text": "The Allard Pierson. Its doors are shut and chained."},
    {"id": "evac_board", "kind": "examine", "pos": [9.0, 1.0, 75.0], "radius": 1.4,
     "text": "EVACUATIEROUTE. CENTRAAL. Sprayed in a hurry, the paint run down the board. They were sending everyone north."}]
Z["enemies"] = [{"id": "bij_de_boten", "kind": "verdronkene", "pos": [3.0, 0.06, 26.0], "yaw": 70},
                {"id": "bij_de_tram", "kind": "verdronkene", "pos": [11.0, 0.0, 52.0], "yaw": 200}]
write(Z)

# ── The hotel's lobby: marble and gilt, the guests' luggage by the door, the porter still here ─────
HO = [ZO[0] + 26.0 + T, ZO[1] + HOTEL["z0"]]
Wh = HOTEL["z1"] - HOTEL["z0"]
uh = hc - HOTEL["z0"]
H = shop_room("hotel_lobby", "Grand Hotel de Keizerskroon", HO, (12.0, Wh), 4.6,
              "the lobby of a grand hotel on Rokin: marble floor, gilt pilasters, the reception desk with the keys still on their "
              "hooks, armchairs, the lift's brass doors; by the door, the guests' luggage, left when the buses came.",
              {"floor": "ph:marble_01", "wall": {"color": [0.62, 0.55, 0.44], "rough": 0.6, "noise": 0.08},
               "ceiling": {"color": [0.75, 0.7, 0.62], "rough": 0.6}, "skirting": {"color": [0.2, 0.15, 0.1], "rough": 0.4}, "skirting_height": 0.15},
              exposure=1.0)
H["walls"] = {"west": {"facade": True, "openings": [glass_door(uh, hw, hh)]},
              "north": {"openings": [{"kind": "door", "center": 8.0, "width": 1.6, "height": 2.4}]}}
H["props"] = [
    {"type": "counter", "pos": [10.4, 0.0, Wh / 2], "size": [4.4, 1.1, 0.7], "yaw": -90, "material": {"ph": "rosewood_veneer1", "tint": [0.6, 0.42, 0.32], "scale": 0.6}},
    {"type": "shelving", "pos": [11.7, 0.0, Wh / 2], "size": [3.0, 2.2, 0.35], "yaw": -90, "palette": "souvenir", "empty": 0.5, "seed": 11, "shelves": 5,
     "frame": {"ph": "rosewood_veneer1", "tint": [0.55, 0.38, 0.28], "scale": 0.6}, "fallen": 0},
    {"type": "wall_sign", "pos": [11.96, 2.9, Wh / 2], "size": [2.6, 0.45, 0.03], "yaw": -90, "text": "RECEPTIE", "color": [1.0, 0.8, 0.45], "glow": 2.5, "collide": False},
    {"type": "model", "model": "ph:ArmChair_01", "pos": [3.0, 0.0, 3.0], "yaw": 60, "scale": 1.0, "size": [0.8, 0.9, 0.8]},
    {"type": "model", "model": "ph:ArmChair_01", "pos": [5.0, 0.0, 2.6], "yaw": -20, "scale": 1.0, "size": [0.8, 0.9, 0.8]},
    {"type": "model", "model": "ph:ArmChair_01", "pos": [3.4, 0.0, Wh - 3.0], "yaw": 130, "scale": 1.0, "size": [0.8, 0.9, 0.8]},
    {"type": "model", "model": "ph:CoffeeTable_01", "pos": [4.0, 0.0, 4.0], "yaw": 10, "scale": 1.0, "size": [1.0, 0.5, 0.6]},
    {"type": "model", "model": "ph:Chandelier_01", "pos": [6.0, 3.3, Wh / 2 - 3.5], "yaw": 0, "fit": [1.4, 1.3, 1.4], "collide": False},
    {"type": "model", "model": "ph:Chandelier_01", "pos": [6.0, 3.3, Wh / 2 + 3.5], "yaw": 0, "fit": [1.4, 1.3, 1.4], "collide": False},
    {"type": "model", "model": "ph:potted_plant_01", "pos": [0.8, 0.0, 0.8], "yaw": 0, "scale": 1.2, "collide": False},
    {"type": "model", "model": "ph:potted_plant_01", "pos": [0.8, 0.0, Wh - 0.8], "yaw": 90, "scale": 1.2, "collide": False},
    {"type": "luggage", "pos": [2.6, 0.0, uh + 2.4], "size": [2.4, 0.0, 2.6], "seed": 7, "cases": 5, "bags": 2, "umbrella": False, "collide": False},
    # the lounge: real furniture (CC0 scans), a clock, pictures; a coat left over a sofa's arm
    {"type": "model", "model": "ph:Sofa_01", "pos": [2.6, 0.0, Wh - 5.0], "yaw": 90, "scale": 1.0, "size": [1.6, 0.8, 0.8]},
    {"type": "model", "model": "ph:sofa_02", "pos": [5.6, 0.0, Wh - 2.4], "yaw": 180, "scale": 1.0, "size": [1.8, 0.8, 0.7]},
    {"type": "model", "model": "ph:coffee_table_round_01", "pos": [4.4, 0.0, Wh - 4.6], "yaw": 0, "scale": 1.0, "size": [0.8, 0.45, 0.8]},
    {"type": "model", "model": "ph:side_table_01", "pos": [2.6, 0.0, Wh - 2.7], "yaw": 0, "scale": 1.0, "size": [0.55, 0.45, 0.55]},
    {"type": "model", "model": "ph:modern_arm_chair_01", "pos": [6.4, 0.0, Wh - 5.4], "yaw": -110, "scale": 1.0, "size": [0.8, 0.9, 0.8]},
    {"type": "model", "model": "ph:potted_plant_01", "pos": [11.3, 0.0, Wh - 0.8], "yaw": 40, "scale": 1.1, "collide": False},
    {"type": "model", "model": "ph:hanging_picture_frame_01", "pos": [4.0, 1.7, Wh - 0.03], "yaw": 180, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:hanging_picture_frame_03", "pos": [8.0, 1.7, Wh - 0.03], "yaw": 180, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:hanging_picture_frame_02", "pos": [5.0, 1.7, 0.03], "yaw": 0, "scale": 1.0, "collide": False},
    {"type": "wall_sign", "pos": [8.0, 2.65, 0.04], "size": [1.4, 0.35, 0.03], "text": "LIFT", "color": [0.8, 0.62, 0.3], "lit": False,
     "panel": {"color": [0.55, 0.4, 0.18], "rough": 0.3, "metal": 0.9}, "collide": False}]
for z in (1.5, Wh / 2 - 3.0, Wh / 2 + 3.0, Wh - 1.5):
    H["props"].append({"type": "pilaster", "pos": [11.97, 0.0, z], "yaw": -90, "size": [0.45, 4.6, 0.18], "material": {"color": [0.85, 0.82, 0.75], "rough": 0.3},
                       "lamp": True, "collide": False})
H["lights"] = [{"kind": "point", "pos": [6.0, 3.2, Wh / 2 - 3.5], "color": [1.0, 0.8, 0.55], "blender_power": 300, "godot_energy": 0.8, "range": 9.0, "radius": 0.3},
               {"kind": "point", "pos": [6.0, 3.2, Wh / 2 + 3.5], "color": [1.0, 0.8, 0.55], "blender_power": 260, "godot_energy": 0.8, "range": 9.0, "radius": 0.3},
               {"kind": "point", "pos": [11.0, 2.4, Wh / 2], "color": [1.0, 0.75, 0.45], "blender_power": 40, "godot_energy": 0.3, "range": 4.0, "radius": 0.1}]
H["shots"] = [
    {"id": "a", "pos": [1.0, 3.4, Wh - 0.8], "look_at": [11.0, 1.0, Wh / 2 - 2.0], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [6.0, Wh]}, "priority": 1},
    {"id": "b", "pos": [11.2, 3.4, 0.8], "look_at": [1.0, 1.2, Wh - 3.0], "fov": 64, "zone": {"min": [6.0, 0.0], "max": [12.0, Wh]}, "priority": 1}]
H["spawns"] = {"from_street": {"pos": [0.8, 0.0, uh], "yaw": -90}}
H["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [0.45, 1.0, uh], "radius": 1.0},
    {"id": "first_aid_reception", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [10.4, 1.12, Wh / 2 + 1.4], "radius": 0.9},
    {"id": "keys", "kind": "examine", "pos": [10.0, 1.0, Wh / 2 - 1.0], "radius": 1.3,
     "text": "Every key still on its hook. The register is open at tonight's page; the last guest signed in at 22:51."},
    {"id": "lift", "kind": "examine", "pos": [8.0, 1.0, 0.5], "radius": 1.1, "text": "The lift is stuck between floors. Something inside it is knocking, slowly."},
    {"id": "luggage", "kind": "examine", "pos": [2.6, 1.0, uh + 2.4], "radius": 1.4,
     "text": "Labels from Osaka, Lyon, Leeds. They left it all by the door when the buses came, meaning to come back for it."}]
H["enemies"] = [{"id": "de_portier", "kind": "verdronkene", "pos": [9.0, 0.0, Wh / 2 - 2.4], "yaw": -90}]
write(H)

# ════════════════════════════════════════════════════════════════════════════════════
# Rokin north: the queen on her horse at the head of the basin, the metro, the police, the Dam
# ════════════════════════════════════════════════════════════════════════════════════
rng = random.Random(81)
N = street_room("rokin_noord", "Rokin", NO, (26.0, 80.0), 10.0,
                "the north half of Rokin: the head of the basin and Queen Wilhelmina on her horse, the metro's way in (shut: the "
                "station has flooded), the police post, an aid post in the road with an ambulance and a police van left by it, and "
                "across the end of the street, at the Dam, an army checkpoint, abandoned.")
POL = front("west", 30.05, 40.0, 26.0, [4.2, 3.3, 3.1, 2.9], 4, "cornice", 801,
            shop("POLITIE", "police", "POLITIE", door_bay=1, power=90.0, awning=False, enter=True), lean=0.0, lit=0.5)
MET = front("west", 12.05, 22.0, 26.0, [5.0, 3.4, 3.2, 3.0], 4, "cornice", 802,
            shop("METRO", "metro", False, door_bay=2, power=120.0, awning=False, enter=True, top=3.8), lean=0.0, metro={"name": "ROKIN"})
o = {"window_rooms": ROOMS, "lamp_power": 380.0, "lamp_energy": 1.0, "tide": 0.7,
     "ground": ground() + [{"name": "west_pavement", "min": [-6.0, 0.0], "max": [0.0, 40.0], "y": 0.06, "material": PAVERS},
                           {"name": "dam_ahead", "min": [-30.0, -70.0], "max": [56.0, 0.0], "y": 0.0, "material": C.WET("cobblestone_floor_04", [0.75, 0.72, 0.68], 0.7, 0.4)}],
     "canals": [{"axis": "z", "x": 0.0, "side": -1, "width": 16.0, "along": [40.0, 80.0], "ends": "a", "far_quay": 5.0, "lit": 0.3,
                 "shops": 0.3, "far_span": [40.0, 80.0]}],
     "tracks": [{"from": [14.0, 80.0], "to": [14.0, -40.0], "y": 0.0}],
     "lamps": lamps(0, 80),
     "rows": [{"from": 0.05, "to": 38.0, "line": -6.0, "facing": "east", "lit": 0.3, "shops": 0.6, "row_ends": "end"},
              {"from": -60.0, "to": -10.0, "line": 50.0, "facing": "west", "lit": 0.35, "shops": 0.5}]}
o["facades"] = [
    front("west", 0.0, 12.0, 26.0, [4.6, 3.6, 3.4, 3.2, 3.0], 5, "cornice", 803, shop("MODEHUIS DE GRACHT", "souvenir", "MODE", smashed=[0, 2, 4])),
    MET,
    front("west", 22.05, 30.0, 26.0, [4.2, 3.3, 3.1, 2.9], 3, "neck", 804, shop("BOEKHANDEL ROKIN", "books", "BOEKEN"), gable_h=3.8),
    POL,
    front("west", 40.05, 48.0, 26.0, [4.2, 3.3, 3.1, 2.9], 3, "bell", 805, door_bay=1, stoop=0.5, gable_h=3.6),
    front("west", 48.05, 58.0, 26.0, [4.4, 3.4, 3.2, 3.0], 4, "cornice", 806, shop("CAFÉ DE KONINGIN", "cafe", "CAFÉ")),
    front("west", 58.05, 66.0, 26.0, [4.2, 3.2, 3.0, 2.8], 3, "step", 807, shop("SIGARENMAGAZIJN", "snack", "SIGAREN"), gable_h=3.6),
    front("west", 66.05, 80.0, 26.0, [4.6, 3.6, 3.4, 3.2], 5, "cornice", 808, shop("WISSELKANTOOR · EXCHANGE", "hotel", "EXCHANGE", awning=False)),
    # ahead, across the Dam (until the Dam is built): the palace's long stone front
    front("east", -75.0, -12.0, -24.0, [6.0, 6.0, 6.0], 11, "cornice", 809, lean=0.0,
          classic={"height": 24.0, "name": "", "bays": 11, "ground": 6.0})]
pc, pw, ph = shop_doorway(POL)
mc, mw, mh = shop_doorway(MET)
props = [
    {"type": "railing", "pos": [0.25, 0.0, 60.0], "yaw": 90, "size": [40.0, 1.0, 0.1], "collide": False},
    {"type": "railing", "pos": [-8.0, 0.0, 40.25], "yaw": 0, "size": [16.0, 1.0, 0.1], "collide": False},
    {"type": "equestrian", "pos": [3.2, 0.06, 42.6], "yaw": 180, "size": [2.2, 3.4, 3.4], "name": "WILHELMINA"},
    {"type": "aid_post", "pos": [17.5, 0.0, 30.0], "yaw": 90, "size": [4.0, 2.9, 4.0], "covered": 1, "seed": 3},
    {"type": "vehicle", "pos": [11.0, 0.0, 24.0], "yaw": 95, "size": [6.0, 2.6, 2.1], "livery": "ambulance", "van": True, "door_open": "right"},
    {"type": "vehicle", "pos": [22.0, 0.0, 46.0], "yaw": 85, "size": [5.4, 2.3, 2.0], "livery": "police", "van": True, "door_open": "left"},
    {"type": "vehicle", "pos": [8.0, 0.0, 5.5], "yaw": 10, "size": [6.4, 2.8, 2.3], "livery": "army", "van": True},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [3.0, 0.0, 1.2], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [13.0, 0.0, 1.2], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [16.2, 0.0, 1.2], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [19.4, 0.0, 1.2], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [22.6, 0.0, 1.2], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "sandbags", "pos": [24.5, 0.06, 2.5], "yaw": 0, "size": [3.0, 1.1, 0.5], "seed": 8},
    {"type": "evac_board", "pos": [5.5, 0.0, 7.5], "yaw": 0, "size": [1.8, 1.9, 0.6], "arrow": "up", "text": "EVACUATIE VIA DAM", "to": "CENTRAAL", "collide": False},
    {"type": "model", "model": "ph:Megaphone_01", "pos": [14.5, 0.0, 6.5], "yaw": 70, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:old_gas_mask", "pos": [16.4, 0.0, 8.6], "yaw": 200, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:metal_jerrycan_green", "pos": [11.6, 0.0, 3.6], "yaw": 30, "scale": 1.0, "collide": False},
    {"type": "luggage", "pos": [21.5, 0.06, mc], "size": [3.0, 0.0, 4.5], "seed": 9, "cases": 4, "bags": 3, "chair": True, "crutches": True, "collide": False},
    {"type": "luggage", "pos": [9.0, 0.0, 38.0], "size": [5.0, 0.0, 4.0], "seed": 10, "cases": 2, "bags": 3, "pushchair": False, "collide": False},
    {"type": "leaflets", "pos": [12.0, 0.0, 40.0], "size": [26.0, 0.0, 76.0], "seed": 11, "count": 300, "collide": False},
    {"type": "sandbags", "pos": [25.3, 0.06, pc - 3.0], "yaw": 90, "size": [3.6, 0.6, 0.45], "seed": 12},
    {"type": "sandbags", "pos": [25.3, 0.06, pc + 3.2], "yaw": 90, "size": [3.0, 0.6, 0.45], "seed": 13},
    {"type": "model", "model": "ph:lifebuoy", "pos": [0.35, 0.55, 64.0], "yaw": 90, "scale": 1.0, "collide": False},
    {"type": "bike", "pos": [1.0, 0.06, 20.0], "yaw": 10, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 150},
    {"type": "bike", "pos": [1.6, 0.06, 21.0], "yaw": 160, "roll": -82, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 151}]
N["outdoor"] = o
N["props"] = props
N["walls"] = {"south": {"openings": [{"kind": "passage", "center": 13.0, "width": 26.0, "height": 10.0}]},
              "east": {"openings": [glass_door(mc, mw, mh), glass_door(pc, pw, ph)]}}
N["lights"] = [SUN, {"kind": "point", "pos": [17.5, 2.0, 30.0], "color": [0.95, 0.97, 1.0], "blender_power": 0, "godot_energy": 0.9, "range": 9.0},
               {"kind": "point", "pos": [22.0, 2.6, 46.0], "color": [0.15, 0.3, 1.0], "blender_power": 0, "godot_energy": 0.8, "range": 7.0, "flicker": True},
               {"kind": "point", "pos": [11.0, 2.9, 24.0], "color": [0.15, 0.3, 1.0], "blender_power": 0, "godot_energy": 0.7, "range": 7.0, "flicker": True}]
N["shots"] = street_shots([
    ("a", [3.2, 3.2, 79.0], [20.0, 2.0, 56.0], 60, 60.0, 80.0),
    ("b", [20.5, 3.0, 63.0], [4.0, 3.6, 41.0], 60, 40.0, 60.0),
    ("c", [6.5, 3.4, 39.0], [24.0, 1.6, 22.0], 62, 20.0, 40.0),
    ("d", [21.0, 3.6, 24.5], [9.0, 4.0, -14.0], 62, 0.0, 20.0)])
N["spawns"] = {"from_rokin_zuid": {"pos": [13.0, 0.0, 78.5], "yaw": 0}, "from_politiepost": {"pos": [24.6, 0.06, pc], "yaw": 90},
               "from_metro": {"pos": [24.6, 0.06, mc], "yaw": 90}}
N["interactables"] = [
    {"id": "door_politie", "kind": "door", "pos": [25.55, 1.0, pc], "radius": 1.0},
    {"id": "door_metro", "kind": "door", "pos": [25.55, 1.0, mc], "radius": 1.0},
    {"id": "wilhelmina", "kind": "examine", "pos": [3.2, 1.0, 45.4], "radius": 1.8,
     "text": "Queen Wilhelmina on her horse, looking north up Rokin. Someone has tied a child's balloon to her stirrup."},
    {"id": "checkpoint", "kind": "examine", "pos": [12.0, 1.0, 2.6], "radius": 2.6,
     "text": "An army checkpoint across the end of Rokin, abandoned: the barriers still up, a megaphone in the road. The Dam is beyond it."},
    {"id": "aid_post", "kind": "examine", "pos": [15.0, 1.0, 30.0], "radius": 1.6,
     "text": "A first aid post. They were checking everyone here before the trams. Under the sheet is someone they couldn't help."},
    {"id": "shells_van", "kind": "pickup", "item": "shotgun_shells", "count": 4, "pos": [21.0, 0.0, 48.6], "radius": 0.9},
    {"id": "dressing_aid", "kind": "pickup", "item": "med_small", "count": 1, "pos": [16.4, 0.78, 28.6], "radius": 0.9}]
N["enemies"] = [{"id": "bij_de_koningin", "kind": "verdronkene", "pos": [6.0, 0.06, 50.0], "yaw": 160},
                {"id": "bij_de_ambulance", "kind": "verdronkene", "pos": [13.0, 0.0, 27.0], "yaw": 20}]
write(N)

# ── The police post: the counter, the waiting room, the armoury cage stood open ─────────────
PO = [NO[0] + 26.0 + T, NO[1] + POL["z0"]]
Wp = POL["z1"] - POL["z0"]
up = pc - POL["z0"]
Pp = shop_room("politiepost", "Politiepost Rokin", PO, (10.0, Wp), 3.6,
               "the police post on Rokin: a waiting room with its plastic chairs, the front counter behind its glass, desks, "
               "lockers, and in the corner the armoury cage, stood open and nearly empty.",
               {"floor": {"ph": "old_linoleum_flooring_01", "tint": [0.6, 0.62, 0.65], "rough": 0.5}, "wall": {"color": [0.72, 0.74, 0.76], "rough": 0.7, "noise": 0.05},
                "ceiling": {"color": [0.8, 0.8, 0.8], "rough": 0.8}, "wainscot": {"color": [0.08, 0.12, 0.3], "rough": 0.4}, "wainscot_height": 1.0,
                "skirting": {"color": [0.05, 0.06, 0.1], "rough": 0.4}, "skirting_height": 0.1}, exposure=0.85)
Pp["walls"] = {"west": {"facade": True, "openings": [glass_door(up, pw, ph)]},
               "east": {"openings": [{"kind": "door", "center": 2.0, "width": 0.9, "height": 2.1}]}}
Pp["props"] = [
    {"type": "counter", "pos": [4.2, 0.0, 3.4], "size": [5.2, 1.05, 0.7], "yaw": -90, "till": False, "material": {"color": [0.08, 0.12, 0.3], "rough": 0.4}},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [0.8, 0.0, 6.0], "yaw": 90, "scale": 1.0, "size": [0.5, 0.8, 0.5]},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [0.8, 0.0, 7.0], "yaw": 90, "scale": 1.0, "size": [0.5, 0.8, 0.5]},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [1.6, 0.0, 8.8], "yaw": 200, "roll": 88, "scale": 1.0, "collide": False},
    {"type": "wall_sign", "pos": [0.05, 1.6, 8.2], "size": [1.6, 1.0, 0.03], "yaw": 90, "text": "GEZOCHT", "lit": False, "color": [0.1, 0.1, 0.1],
     "panel": {"color": [0.7, 0.62, 0.45], "rough": 0.8}, "collide": False},
    {"type": "model", "model": "ph:metal_office_desk", "pos": [6.6, 0.0, 2.0], "yaw": -90, "scale": 1.0, "size": [1.4, 0.75, 0.7]},
    {"type": "model", "model": "ph:metal_office_desk", "pos": [6.6, 0.0, 5.0], "yaw": -90, "scale": 1.0, "size": [1.4, 0.75, 0.7]},
    {"type": "lockers", "pos": [9.75, 0.0, 4.6], "yaw": -90, "size": [3.6, 1.9, 0.5], "seed": 3, "open": 0.35},
    {"type": "model", "model": "ph:steel_frame_shelves_01", "pos": [9.5, 0.0, 8.6], "yaw": -90, "fit": [1.8, 2.0, 0.5]},
    {"type": "crowd_barrier", "pos": [7.4, 0.0, 7.6], "yaw": 0, "size": [5.0, 2.2, 0.1], "tape": False, "seed": 2, "collide": False},
    {"type": "model", "model": "ph:security_camera_01", "pos": [0.3, 3.0, 0.4], "yaw": 135, "scale": 1.0, "collide": False},
    {"type": "strip_light", "pos": [2.2, 3.6, Wp / 2], "size": [3.0, 0.1, 0.2], "yaw": 90, "collide": False},
    {"type": "strip_light", "pos": [7.0, 3.6, Wp / 2], "size": [3.0, 0.1, 0.2], "yaw": 90, "collide": False}]
Pp["lights"] = [{"kind": "area", "pos": [2.2, 3.5, Wp / 2], "look_at": [2.2, 0.0, Wp / 2], "size": 1.4, "color": [0.92, 0.96, 1.0], "blender_power": 90, "godot_energy": 0.5, "range": 7.0},
                {"kind": "area", "pos": [7.0, 3.5, Wp / 2], "look_at": [7.0, 0.0, Wp / 2], "size": 1.4, "color": [0.92, 0.96, 1.0], "blender_power": 60, "godot_energy": 0.4, "range": 7.0, "flicker": True}]
Pp["shots"] = [
    {"id": "a", "pos": [0.6, 2.9, 0.6], "look_at": [8.5, 1.0, 7.5], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [4.2, Wp]}, "priority": 1},
    {"id": "b", "pos": [9.4, 2.9, 1.0], "look_at": [2.0, 1.0, 8.5], "fov": 64, "zone": {"min": [4.2, 0.0], "max": [10.0, Wp]}, "priority": 1}]
Pp["spawns"] = {"from_street": {"pos": [0.8, 0.0, up], "yaw": -90}}
Pp["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [0.45, 1.0, up], "radius": 1.0},
    {"id": "armoury", "kind": "examine", "pos": [8.4, 1.0, 7.4], "radius": 1.4,
     "text": "The armoury cage stands open. The rifles are gone; whoever took them left in a hurry, and left these."},
    {"id": "shells_armoury", "kind": "pickup", "item": "shotgun_shells", "count": 8, "pos": [9.3, 1.05, 8.2], "radius": 0.9},
    {"id": "ammo_armoury", "kind": "pickup", "item": "handgun_ammo", "count": 20, "pos": [9.3, 1.05, 9.1], "radius": 0.9},
    {"id": "back_office", "kind": "examine", "pos": [9.6, 1.0, 2.0], "radius": 1.0, "text": "The cells. Locked. Something in there is breathing water."}]
Pp["enemies"] = [{"id": "de_agent", "kind": "verdronkene", "pos": [6.0, 0.0, 3.6], "yaw": -90}]
write(Pp)

# ── The metro's ticket hall: machines, gates shut, the escalators down into the water ──────────
MO_ = [NO[0] + 26.0 + T, NO[1] + MET["z0"]]
Wm = MET["z1"] - MET["z0"]
um = mc - MET["z0"]
Mm = shop_room("metro_rokin", "Metrostation Rokin", MO_, (16.0, Wm), 5.0,
               "the way down to the metro under Rokin: ticket machines, the gate line shut on red, and beyond it the escalators, "
               "stopped, running down into black water that has risen to the third step. Not this way: Centraal.",
               {"floor": {"ph": "granite_tile", "tint": [0.55, 0.55, 0.56], "rough": 0.35}, "wall": {"color": [0.16, 0.17, 0.18], "rough": 0.4, "metal": 0.3},
                "ceiling": {"color": [0.5, 0.52, 0.55], "rough": 0.4, "metal": 0.5}, "skirting": None}, exposure=0.9)
Mm["floor_holes"] = [[8.0, 1.2, 16.0, 4.4], [8.0, 5.6, 16.0, 8.8]]
Mm["walls"] = {"west": {"facade": True, "openings": [glass_door(um, mw, mh)]}}
Mm["props"] = [
    {"type": "ticket_machine", "pos": [2.0, 0.0, 0.45], "yaw": 0, "size": [0.8, 1.7, 0.5]},
    {"type": "ticket_machine", "pos": [3.2, 0.0, 0.45], "yaw": 0, "size": [0.8, 1.7, 0.5]},
    {"type": "ticket_machine", "pos": [4.4, 0.0, 0.45], "yaw": 0, "size": [0.8, 1.7, 0.5]},
    {"type": "ticket_gates", "pos": [6.6, 0.0, Wm / 2], "yaw": 90, "size": [Wm, 1.1, 0.3]},
    {"type": "escalator", "pos": [8.0, 0.0, 2.8], "yaw": -90, "size": [1.4, 5.0, 8.0], "water": 3.4, "collide": False},
    {"type": "escalator", "pos": [8.0, 0.0, 7.2], "yaw": -90, "size": [1.4, 5.0, 8.0], "water": 3.4, "collide": False},
    {"type": "wall_sign", "pos": [7.4, 3.6, 0.04], "size": [3.0, 0.5, 0.03], "text": "PERRONS · NOORD / ZUID", "color": [1.0, 1.0, 1.0], "glow": 2.5, "collide": False},
    {"type": "wall_sign", "pos": [15.96, 3.3, Wm / 2], "size": [3.4, 0.6, 0.03], "yaw": -90, "text": "BUITEN DIENST", "color": [1.0, 0.15, 0.08], "glow": 3.0, "collide": False},
    {"type": "luggage", "pos": [4.0, 0.0, Wm - 2.0], "size": [3.0, 0.0, 2.6], "seed": 21, "cases": 3, "bags": 2, "collide": False},
    {"type": "leaflets", "pos": [4.0, 0.0, Wm / 2], "size": [6.0, 0.0, Wm - 1.0], "seed": 22, "count": 40, "collide": False},
    {"type": "strip_light", "pos": [3.5, 5.0, Wm / 2], "size": [5.0, 0.1, 0.2], "yaw": 90, "collide": False},
    {"type": "strip_light", "pos": [11.5, 5.0, Wm / 2], "size": [6.0, 0.1, 0.2], "collide": False}]
Mm["lights"] = [{"kind": "area", "pos": [3.5, 4.9, Wm / 2], "look_at": [3.5, 0.0, Wm / 2], "size": 2.0, "color": [0.9, 0.95, 1.0], "blender_power": 140, "godot_energy": 0.6, "range": 8.0},
                {"kind": "area", "pos": [11.5, 4.9, Wm / 2], "look_at": [11.5, 0.0, Wm / 2], "size": 2.0, "color": [0.9, 0.95, 1.0], "blender_power": 90, "godot_energy": 0.4, "range": 8.0, "flicker": True}]
Mm["shots"] = [
    {"id": "a", "pos": [0.7, 3.6, Wm - 0.6], "look_at": [12.0, -0.5, 3.0], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [16.0, Wm]}, "priority": 1}]
Mm["spawns"] = {"from_street": {"pos": [0.8, 0.0, um], "yaw": -90}}
Mm["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [0.45, 1.0, um], "radius": 1.0},
    {"id": "escalators", "kind": "examine", "pos": [6.0, 1.0, Wm / 2], "radius": 1.6,
     "text": "The escalators run down into black water. It's up to the third step, and still coming up. Not this way. Centraal."},
    {"id": "dressing_machines", "kind": "pickup", "item": "med_small", "count": 1, "pos": [3.8, 0.0, 1.3], "radius": 0.9}]
Mm["enemies"] = [{"id": "op_de_roltrap", "kind": "verdronkene", "pos": [5.2, 0.0, Wm - 1.4], "yaw": 160}]
write(Mm)

# ── Muntplein: its stand-ins for Rokin handed over; a gap in the barriers; the beat north ──────────
M = json.load(open(R + "muntplein.json"))
o = M["outdoor"]
o["ground"] = [g for g in o["ground"] if g["name"] not in ("rokin_road", "rokin_pavement")]
o.pop("canals", None)
o["rows"] = [r for r in o["rows"] if r.get("line") != 50.0]
o["tracks"] = [{"from": [44.0, 20.7], "to": [37.0, 20.7], "y": 0.0}, {"from": [37.0, 20.7], "to": [32.0, 15.7], "y": 0.0},
               {"from": [32.0, 15.7], "to": [32.0, 0.0], "y": 0.0}]
o["lamps"] = [l for l in o["lamps"] if l[1] >= 0.0]
M["props"] = [p for p in M["props"] if p["type"] not in ("tram", "crowd_barrier")]
M["props"] += [{"type": "crowd_barrier", "pos": [23.75, 0.0, 0.6], "size": [11.5, 1.1, 0.7], "yaw": 0, "seed": 3},
               {"type": "crowd_barrier", "pos": [38.25, 0.0, 0.6], "size": [11.5, 1.1, 0.7], "yaw": 0, "seed": 4},
               {"type": "crowd_barrier", "pos": [31.0, 0.0, 2.2], "size": [2.6, 1.1, 0.7], "yaw": 35, "seed": 5, "roll": 80, "collide": False}]   # knocked flat: the way through
M["walls"]["north"] = {"openings": [{"kind": "passage", "center": 31.0, "width": 26.0, "height": 10.0}]}
M["interactables"] = [i for i in M["interactables"] if i["id"] not in ("rokin", "to_rokin")]
M["interactables"] += [{"id": "to_rokin", "kind": "door", "pos": [31.0, 1.0, 0.2], "radius": 1.6, "target_room": "rokin_zuid", "target_spawn": "from_muntplein"},
                       {"id": "rokin", "kind": "examine", "pos": [27.0, 1.0, 1.6], "radius": 1.6,
                        "text": "Rokin. Crowd barriers across it, one pushed flat. Beyond them, the long road to Centraal."}]
M["spawns"]["from_rokin"] = {"pos": [31.0, 0.0, 1.8], "yaw": 180}
json.dump(M, open(R + "muntplein.json", "w"), indent=2, ensure_ascii=True)
open(R + "muntplein.json", "a").write("\n")
print("doors: hotel", round(hc, 3), "politie", round(pc, 3), "metro", round(mc, 3))
