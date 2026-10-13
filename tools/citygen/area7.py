# damned_waters/tools/citygen/area7.py
# Generates area 7 (storey 15, district 6: Damrak), the last street before the station: damrak_zuid
# (the Beurs van Berlage along its east side, the shops and hotels opposite) and damrak_noord (the
# basin with its tour boats, the leaning houses across the water, the station ahead); and the places
# off it he can search: the Beurs's hall, made the army's mortuary (beurs_zaal), a tour boat at its
# pier (rondvaartboot), a currency exchange (wisselkantoor), a souvenir shop and its stockroom
# (souvenirwinkel, magazijn), a hotel's bar (hotel_bar). The army closed Damrak at the Dam; the way
# on is the department store's staff exit (warenhuis, the guards' pass in beveiliging), which lets
# out on Damrak behind the barriers. Dressed as the evacuation left it (docs/city_aftermath.md).
from pathlib import Path
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import front, shop, shop_doorway, glass_door, street_room, shop_room, write, PAVERS, BRICKS, SUN, ROOMS, R  # noqa: E402

C.DISTRICT.update({"storey": 15, "name": "district 6: Damrak"})
T = 0.3
W = 20.0                                  # the street: the Dam's north-east gap (x 912..932), north to the station
ZO = [912.0, -294.9 - T - 70.0]           # damrak_zuid: 20 x 70, its south edge a wall's thickness north of the Dam's
NO = [912.0, ZO[1] - T - 90.0]            # damrak_noord: 20 x 90, on to the Prins Hendrikkade
WATER = -0.8                              # the basin is high: the flood came up it
QUAY = C.WET("square_concrete_pavers", [0.7, 0.69, 0.66], 0.75, 0.45)


def lamps(L, step=14):
    return [[1.2, float(z)] for z in range(6, int(L), step)] + [[18.8, float(z) + 7] for z in range(6, int(L) - 7, step)]


def shots(specs):
    return [{"id": i, "pos": p, "look_at": l, "fov": f, "zone": {"min": [0.0, z0], "max": [W, z1]}, "priority": 1}
            for i, p, l, f, z0, z1 in specs]


def house_door(f):
    """The front door of a (not shop) front: its centre along the street's wall, width, height."""
    s0 = f["storeys"][0]
    Wf = f["z1"] - f["z0"]
    g = C.fz.window_grid(Wf, f["storeys"], f["bays"], 1.05, f["door_bay"])
    u0, u1, v0, v1 = g["door"]
    return C.fz.along_wall(f, (u0 + u1) / 2), u1 - u0, v1 - v0


# ════════════════════════════════════════════════════════════════════════════════════
# Damrak south: the Beurs, the shops and hotels across from it, the barriers at the Dam
# ════════════════════════════════════════════════════════════════════════════════════
rng = random.Random(171)
L = 70.0
Z = street_room("damrak_zuid", "Damrak", ZO, (W, L), 12.0,
                "the south half of Damrak, from the Dam to the basin: the long brick flank of the Beurs van Berlage on the "
                "east side, its clock tower over the Dam and its gate open (the army's mortuary is inside), the shops and "
                "hotels opposite, the tram rails down the middle. The army closed it at the Dam: the barriers are chained "
                "across the end. The crowds walked this way to the trains.")
SOUV = front("east", 9.05, 17.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 1702,
             shop("SOUVENIRS · KLOMPEN", "souvenir", "SOUVENIRS", door_bay=1, power=95.0, enter=True), gable_h=3.8)
EXCH = front("east", 17.05, 25.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "cornice", 1703,
             shop("WISSELKANTOOR · CHANGE", "hotel", "CHANGE", door_bay=1, power=90.0, awning=False, enter=True, smashed=[0]), lean=0.0)
ZWERM = front("east", 58.05, 70.0, 0.0, [5.0, 4.0, 3.8, 3.6, 3.4], 5, "cornice", 1708, door_bay=2, stoop=0.0, lean=0.0, lit=0.4, sides=True)
o = {"window_rooms": ROOMS, "lamp_power": 400.0, "lamp_energy": 1.0, "tide": 0.6,
     "ground": [{"name": "pavement_w", "min": [0.0, 0.0], "max": [4.0, L], "y": 0.06, "material": PAVERS},
                {"name": "road", "min": [4.0, 0.0], "max": [16.0, L], "y": 0.0, "material": BRICKS},
                {"name": "pavement_e", "min": [16.0, 0.0], "max": [W, L], "y": 0.06, "material": PAVERS}],
     "tracks": [{"from": [8.5, L], "to": [8.5, 0.0], "y": 0.0}, {"from": [11.5, L], "to": [11.5, 0.0], "y": 0.0}],
     "lamps": lamps(L)}
o["facades"] = [
    front("east", 0.0, 9.0, 0.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 1701, shop("HOTEL DE HAVEN", "hotel", "HOTEL", awning=False), lean=0.0, lit=0.55),
    SOUV, EXCH,
    front("east", 25.05, 33.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "step", 1704, shop("FRIETEN · VLAAMSE FRIETJES", "snack", "FRIET"), gable_h=3.6),
    front("east", 33.05, 42.0, 0.0, [4.4, 3.4, 3.2, 3.0, 2.8], 4, "bell", 1705, shop("COFFEESHOP BLAUWE NEVEL", "coffeeshop", "COFFEESHOP"), gable_h=3.8),
    front("east", 42.05, 50.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "spout", 1706, shop("KAASHUIS DAMRAK", "souvenir", "KAAS"), gable_h=3.6),
    front("east", 50.05, 58.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 1707, shop("PANNENKOEKENHUIS", "restaurant", "PANNENKOEKEN"), gable_h=3.8),
    ZWERM,   # the department store's wing on Damrak: its staff door
    front("west", 59.55, 70.0, W, [4.6, 3.6, 3.4, 3.2, 3.0], 3, "cornice", 1709, shop("CAFÉ DE DAM", "cafe", "CAFÉ", awning=False), lean=0.0, sides=True)]
Z["outdoor"] = o
sc_, sw_, sh_ = shop_doorway(SOUV)
ec_, ew_, eh_ = shop_doorway(EXCH)
zc_, zw_, zh_ = house_door(ZWERM)
GATE = 53.5   # the Beurs's gate, at the tower's foot (landmarks.beurs: the tower's last 12 m, its gate 4 m wide)
props = [
    {"type": "beurs", "pos": [W, 0.0, 0.0], "yaw": -90, "size": [59.5, 17.0, 26.0], "gate_open": True, "encloses": ["beurs_zaal"], "collide": False},
    {"type": "wall_sign", "pos": [0.04, 4.6, zc_], "size": [3.0, 0.5, 0.03], "yaw": 90, "text": "DE ZWERM", "color": [1.0, 0.82, 0.4], "glow": 2.5, "collide": False},
    {"type": "wall_sign", "pos": [0.04, 2.75, zc_], "size": [1.2, 0.22, 0.03], "yaw": 90, "text": "PERSONEEL", "color": [0.9, 0.95, 1.0], "glow": 1.2, "collide": False},
    # the army's barriers across the Dam end (the other side of the Dam's), chained
    {"type": "crowd_barrier", "pos": [10.0, 0.0, L - 1.0], "yaw": 0, "size": [20.0, 1.1, 0.7], "seed": 71},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [6.0, 0.0, L - 2.6], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [14.0, 0.0, L - 2.6], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "light_tower", "pos": [3.0, 0.06, L - 5.0], "yaw": 180, "size": [2.2, 8.5, 1.4], "aim": [-7.0, 0.0, 14.0]},
    # at the Beurs's gate: sandbags, the refrigerated container, the army's truck
    {"type": "sandbags", "pos": [18.9, 0.06, GATE - 3.0], "yaw": 90, "size": [1.6, 0.9, 0.5], "seed": 72},
    {"type": "sandbags", "pos": [18.9, 0.06, GATE + 3.0], "yaw": 90, "size": [1.6, 0.9, 0.5], "seed": 73},
    {"type": "reefer", "pos": [17.6, 0.06, 42.0], "yaw": 90, "size": [6.0, 2.6, 2.4], "text": "DEFENSIE"},
    {"type": "vehicle", "pos": [12.8, 0.0, 44.0], "yaw": 92, "size": [6.4, 2.8, 2.3], "livery": "army", "van": True},
    {"type": "wall_sign", "pos": [19.8, 6.4, GATE], "size": [3.6, 0.5, 0.03], "yaw": -90, "text": "MORTUARIUM · DEFENSIE", "color": [0.95, 0.95, 0.9], "glow": 1.4,
     "collide": False},
    # the trams: the last one north, stopped with its doors open
    {"type": "tram", "pos": [11.5, 0.0, 22.0], "yaw": 90, "size": [30.0, 3.4, 2.4], "board": "CENTRAAL", "power": 260.0},
    {"type": "evac_board", "pos": [3.0, 0.06, 54.0], "yaw": 0, "size": [1.8, 1.9, 0.6], "text": "EVACUATIEROUTE", "to": "CENTRAAL", "arrow": "up", "collide": False},
    {"type": "vehicle", "pos": [5.6, 0.0, 47.0], "yaw": 95, "size": [4.6, 1.5, 1.85], "livery": "taxi", "door_open": "right"},
    {"type": "luggage", "pos": [9.0, 0.0, 60.0], "size": [8.0, 0.0, 6.0], "seed": 73, "cases": 4, "bags": 6, "pushchair": True, "collide": False},
    {"type": "luggage", "pos": [3.0, 0.06, 30.0], "size": [3.0, 0.0, 6.0], "seed": 74, "cases": 2, "bags": 4, "chair": True, "collide": False},
    {"type": "luggage", "pos": [17.0, 0.06, 30.0], "size": [3.0, 0.0, 8.0], "seed": 75, "cases": 3, "bags": 3, "umbrella": True, "collide": False},
    {"type": "leaflets", "pos": [10.0, 0.0, L / 2], "size": [W, 0.0, L], "seed": 76, "count": 320, "collide": False},
    {"type": "broken_glass", "pos": [0.0, 0.06, ec_ - 2.0], "yaw": 90, "size": [3.0, 0.0, 1.6], "seed": 77, "collide": False},
    {"type": "bike", "pos": [1.0, 0.06, 36.0], "yaw": 10, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 178},
    {"type": "bike", "pos": [1.4, 0.06, 37.2], "yaw": 170, "roll": -84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 179},
    {"type": "model", "model": "ph:trashbag", "pos": [3.4, 0.06, 44.0], "yaw": 30, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:Megaphone_01", "pos": [8.0, 0.0, L - 4.4], "yaw": 70, "scale": 1.0, "collide": False}]
Z["props"] = props
Z["walls"] = {"south": {"openings": [{"kind": "passage", "center": W / 2, "width": W, "height": 12.0}]},   # (barred: the Dam)
              "north": {"openings": [{"kind": "passage", "center": W / 2, "width": W, "height": 12.0}]},
              "west": {"openings": [glass_door(sc_, sw_, sh_), glass_door(ec_, ew_, eh_),
                                    {"kind": "door", "center": round(zc_, 4), "width": round(zw_, 4), "height": round(zh_, 4), "hinge": "left"}]},
              "east": {"openings": [{"kind": "passage", "center": GATE, "width": 4.0, "height": 5.5}]}}
Z["lights"] = [SUN, {"kind": "point", "pos": [11.5, 2.6, 22.0], "color": [1.0, 0.9, 0.75], "blender_power": 0, "godot_energy": 0.6, "range": 8.0},
               {"kind": "point", "pos": [3.0, 6.5, L - 5.0], "color": [0.95, 0.97, 1.0], "blender_power": 0, "godot_energy": 0.9, "range": 14.0},
               {"kind": "point", "pos": [18.5, 3.0, GATE], "color": [0.85, 0.92, 1.0], "blender_power": 0, "godot_energy": 0.6, "range": 7.0}]
Z["shots"] = shots([
    ("a", [3.0, 4.2, 48.5], [16.0, 3.0, 72.0], 62, 52.5, 70.0),     # toward the Beurs's tower and the barriers, the Dam lit beyond
    ("b", [17.0, 4.2, 56.0], [4.0, 1.4, 32.0], 60, 35.0, 52.5),     # north-west along the shops; the gate behind
    ("c", [3.0, 4.2, 14.0], [17.0, 3.0, 40.0], 60, 17.5, 35.0),     # south-east down the Beurs's flank
    ("d", [16.5, 4.4, 21.0], [6.0, 3.0, -16.0], 60, 0.0, 17.5)])    # north: the basin, the station ahead
Z["spawns"] = {"from_warenhuis": {"pos": [1.0, 0.06, zc_], "yaw": 270}, "from_souvenirwinkel": {"pos": [1.0, 0.06, sc_], "yaw": 270},
               "from_wisselkantoor": {"pos": [1.0, 0.06, ec_], "yaw": 270}}
Z["interactables"] = [
    {"id": "to_warenhuis", "kind": "door", "pos": [0.45, 1.0, zc_], "radius": 1.0, "target_room": "warenhuis", "target_spawn": "from_damrak"},
    {"id": "door_souvenirwinkel", "kind": "door", "pos": [0.45, 1.0, sc_], "radius": 1.0},
    {"id": "door_wisselkantoor", "kind": "door", "pos": [0.45, 1.0, ec_], "radius": 1.0},
    {"id": "barriers", "kind": "examine", "pos": [10.0, 1.0, L - 3.6], "radius": 2.6,
     "text": "The barriers, chained together, the padlock on the Dam's side. Beyond them the funfair turns its lights over the square."},
    {"id": "beurs", "kind": "examine", "pos": [18.0, 1.0, GATE - 4.6], "radius": 1.8,
     "text": "MORTUARIUM. The Beurs's gate stands open, sandbagged. A cold draught comes out of it, and a hum."},
    {"id": "tram", "kind": "examine", "pos": [9.4, 1.0, 22.0], "radius": 1.6,
     "text": "The tram to Centraal, its doors open, its lights on. Coats on the seats. A child's shoe on the step."},
    {"id": "ammo_taxi", "kind": "pickup", "item": "handgun_ammo", "count": 8, "pos": [7.0, 0.0, 48.6], "radius": 0.9}]
Z["enemies"] = [{"id": "bij_de_tram", "kind": "verdronkene", "pos": [7.0, 0.0, 30.0], "yaw": 150},
                {"id": "bij_de_hekken", "kind": "verdronkene", "pos": [12.0, 0.0, 62.0], "yaw": 10}]
write(Z)

# ── The Beurs's hall: the army's mortuary ─────────────────────────────────────────────────
BZ = [ZO[0] + W + T, ZO[1] + 12.25]   # 22 x 44, its gate in the west wall at 41.25 (the arcade's first bay from the south)
BW, BD, BH = 22.0, 44.0, 16.5
GZ = GATE - 12.25
Bz = shop_room("beurs_zaal", "Beurs van Berlage", BZ, (BW, BD), BH,
               "the exchange hall of the Beurs van Berlage: brick arcades down both sides with the gallery over them, the steel "
               "and glass of the roof, night through it. The army made it a mortuary: body bags in rows down the floor, some on "
               "trestles, the registration's tables by the gate, work lights on tripods. Not all of the bags are full.",
               {"floor": {"ph": "large_floor_tiles_02", "tint": [0.62, 0.58, 0.52], "rough": 0.45}, "wall": {"ph": "red_bricks_04", "tint": [0.78, 0.56, 0.44], "scale": 1.0},
                "ceiling": {"color": [0.004, 0.005, 0.009], "rough": 1.0}, "skirting": None}, exposure=1.25)
Bz["walls"] = {"west": {"openings": [{"kind": "passage", "center": GZ, "width": 4.0, "height": 5.5}]}}
bags = []
cells_w = {"rows": 9, "cols": 5}
for k, (x0, x1) in enumerate(((3.5, 10.0), (12.0, 18.5))):   # two blocks of rows, an aisle down the middle
    bp = {"type": "body_bags", "pos": [(x0 + x1) / 2, 0.0, 19.0], "size": [x1 - x0, 0.3, 27.0], "rows": 9, "cols": 5, "trestles": 0.22,
          "seed": 31 + k, "collide": False, "open_cells": [[3, 2]] if k == 0 else [[6, 1]]}
    bags.append(bp)
    for c in range(5):   # each column of bags a strip he can't walk through; the gaps between them he can
        bags.append({"type": "collider", "pos": [round(x0 + (x1 - x0) * (c + 0.5) / 5, 3), 0.0, 19.0], "size": [0.62, 0.3, 27.0]})
LYING = [[3.5 + 6.5 * 2.5 / 5, 5.5 + 27.0 * 3.5 / 9], [12.0 + 6.5 * 1.5 / 5, 5.5 + 27.0 * 6.5 / 9]]   # the cells left open
Bz["props"] = bags + [
    {"type": "beurs_arcade", "pos": [0.6, 0.0, BD / 2], "yaw": 90, "size": [BD, 13.5, 1.2], "bay": 5.5, "spring": 4.2, "gallery": 7.2, "pier": 1.1,
     "open_bays": [0], "collide": False},
    {"type": "beurs_arcade", "pos": [BW - 0.6, 0.0, BD / 2], "yaw": -90, "size": [BD, 13.5, 1.2], "bay": 5.5, "spring": 4.2, "gallery": 7.2, "pier": 1.1,
     "collide": False},
    {"type": "collider", "pos": [0.6, 0.0, (GZ - 2.2) / 2], "size": [1.2, 1.0, GZ - 2.2]},          # the arcades: he walks the floor, not the aisles
    {"type": "collider", "pos": [0.6, 0.0, (GZ + 2.2 + BD) / 2], "size": [1.2, 1.0, BD - GZ - 2.2]},
    {"type": "collider", "pos": [BW - 0.6, 0.0, BD / 2], "size": [1.2, 1.0, BD]},
    {"type": "glass_roof", "pos": [BW / 2, 13.5, BD / 2], "yaw": 0, "size": [BW, 2.8, BD], "bay": 5.5, "collide": False},
    {"type": "wall_sign", "pos": [BW / 2, 9.5, 0.06], "size": [6.0, 0.9, 0.04], "text": "MORTUARIUM · NIET BETREDEN", "color": [0.95, 0.95, 0.9],
     "glow": 1.2, "collide": False},
    # the registration by the gate
    {"type": "trestle_table", "pos": [3.4, 0.0, 34.5], "yaw": 90, "size": [1.8, 0.76, 0.8], "laptops": 1, "seed": 41},
    {"type": "trestle_table", "pos": [3.4, 0.0, 37.0], "yaw": 90, "size": [1.8, 0.76, 0.8], "laptops": 1, "seed": 42},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [2.3, 0.0, 34.6], "yaw": -80, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:clipboard", "pos": [3.6, 0.76, 36.6], "yaw": 20, "scale": 1.0, "collide": False},
    {"type": "screen", "pos": [6.2, 0.0, 39.5], "yaw": 0, "size": [2.4, 1.8, 0.4]},
    {"type": "army_crate", "pos": [2.2, 0.0, 30.6], "yaw": 90, "size": [1.0, 0.5, 0.6], "text": "MUNITIE · 9 MM", "open": True},
    {"type": "model", "model": "ph:portable_generator", "pos": [BW - 2.8, 0.0, 41.5], "yaw": 200, "fit": [0.8, 0.6, 0.55]},
    # the work lights on their tripods, at the corners of the rows
    {"type": "work_light", "pos": [2.4, 0.0, 4.0], "yaw": 45, "size": [0.9, 2.6, 0.9], "aim": [0.0, 0.0, 9.0], "collide": False},
    {"type": "work_light", "pos": [BW - 2.4, 0.0, 4.0], "yaw": -45, "size": [0.9, 2.6, 0.9], "aim": [0.0, 0.0, 9.0], "collide": False},
    {"type": "work_light", "pos": [11.0, 0.0, 34.5], "yaw": 180, "size": [0.9, 2.6, 0.9], "aim": [0.0, 0.0, 12.0], "collide": False},
    {"type": "work_light", "pos": [BW - 2.4, 0.0, 36.0], "yaw": -135, "size": [0.9, 2.6, 0.9], "aim": [0.0, 0.0, 9.0], "collide": False},
    {"type": "luggage", "pos": [7.0, 0.0, 41.0], "size": [3.0, 0.0, 2.0], "seed": 43, "cases": 2, "bags": 4, "collide": False},
    {"type": "leaflets", "pos": [BW / 2, 0.0, 38.0], "size": [BW - 4.0, 0.0, 10.0], "seed": 44, "count": 40, "collide": False}]
Bz["lights"] = [{"kind": "spot", "pos": [2.4, 2.6, 4.0], "look_at": [8.0, 0.0, 12.0], "color": [0.9, 0.95, 1.0], "blender_power": 0, "godot_energy": 1.0, "range": 16.0},
                {"kind": "spot", "pos": [BW - 2.4, 2.6, 4.0], "look_at": [14.0, 0.0, 12.0], "color": [0.9, 0.95, 1.0], "blender_power": 0, "godot_energy": 1.0, "range": 16.0},
                {"kind": "spot", "pos": [11.0, 2.6, 34.5], "look_at": [11.0, 0.0, 22.0], "color": [0.9, 0.95, 1.0], "blender_power": 0, "godot_energy": 1.0, "range": 16.0},
                {"kind": "area", "pos": [BW / 2, 12.0, BD / 2], "look_at": [BW / 2, 0.0, BD / 2], "size": 12.0, "color": [0.55, 0.65, 0.85], "blender_power": 1100,
                 "godot_energy": 0.25, "range": 30.0}]   # the night through the glass, faint
Bz["shots"] = [
    {"id": "a", "pos": [4.2, 5.4, 42.6], "look_at": [15.0, 0.4, 8.0], "fov": 62, "zone": {"min": [0.0, 22.0], "max": [BW, BD]}, "priority": 1},
    {"id": "b", "pos": [17.6, 6.2, 1.4], "look_at": [6.0, 0.4, 36.0], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [BW, 22.0]}, "priority": 1}]
Bz["spawns"] = {"from_damrak": {"pos": [1.6, 0.0, GZ], "yaw": 270}}
Bz["interactables"] = [
    {"id": "bags", "kind": "examine", "pos": [11.0, 1.0, 20.0], "radius": 2.0,
     "text": "Body bags, in rows, each with its tag: a number, a date, a name where they had one. Hundreds. Some of the tags just say ONBEKEND."},
    {"id": "open_bag", "kind": "examine", "pos": [LYING[0][0] + 0.7, 1.0, LYING[0][1]], "radius": 1.0,
     "text": "This one's open. Unzipped from the inside."},
    {"id": "registration", "kind": "examine", "pos": [4.4, 1.0, 35.7], "radius": 1.4,
     "text": "The registration: a list on the laptop, still open. The last entry is at 03:12. After that, nothing."},
    {"id": "ammo_crate", "kind": "pickup", "item": "handgun_ammo", "count": 20, "pos": [2.2, 0.45, 30.6], "radius": 0.9},
    {"id": "first_aid_desk", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [3.4, 0.76, 37.4], "radius": 0.9}]
Bz["enemies"] = [{"id": "in_de_rij", "kind": "verdronkene", "pos": [round(LYING[0][0], 3), 0.0, round(LYING[0][1], 3)], "yaw": 0, "lying": True},
                 {"id": "op_de_schragen", "kind": "verdronkene", "pos": [round(LYING[1][0], 3), 0.0, round(LYING[1][1], 3)], "yaw": 180, "lying": True}]
write(Bz)

# ── The currency exchange: the cashier's glass, the rates board, the safe ───────────────────
EO = [ZO[0] - T - 7.0, ZO[1] + EXCH["z0"]]
Ed = EXCH["z1"] - EXCH["z0"]
ue = ec_ - EXCH["z0"]
Ex = shop_room("wisselkantoor", "Wisselkantoor", EO, (7.0, Ed), 3.2,
               "a currency exchange on Damrak: a waiting area in front of the cashiers' bullet-proof glass, the board of rates "
               "still lit, and behind the glass the tills pulled out, the safe open. The money went with someone.",
               {"floor": {"ph": "large_floor_tiles_02", "tint": [0.75, 0.75, 0.74], "rough": 0.35}, "wall": {"color": [0.86, 0.85, 0.82], "rough": 0.6},
                "ceiling": {"color": [0.85, 0.85, 0.84], "rough": 0.8}, "skirting": {"color": [0.12, 0.13, 0.15], "rough": 0.4}, "skirting_height": 0.1},
               exposure=0.9)
Ex["walls"] = {"east": {"facade": True, "openings": [glass_door(ue, ew_, eh_)]}}
Ex["props"] = [
    {"type": "glass_partition", "pos": [3.0, 0.0, Ed / 2], "yaw": 90, "size": [Ed, 2.4, 0.7], "gap": [-Ed / 2 + 0.6, 0.9], "collide": False},
    {"type": "collider", "pos": [3.0, 0.0, (Ed - 1.05) / 2], "size": [0.7, 1.0, Ed - 1.05]},   # the counter, but for its staff door at the end
    {"type": "collider", "pos": [3.0, 0.0, Ed - 0.075], "size": [0.7, 1.0, 0.15]},
    {"type": "rates_board", "pos": [0.06, 1.6, Ed / 2], "yaw": 90, "size": [2.6, 1.3, 0.06], "seed": 51, "collide": False},
    {"type": "safe", "pos": [0.55, 0.0, 0.8], "yaw": 90, "size": [0.8, 1.2, 0.7], "open": True},
    {"type": "model", "model": "ph:metal_office_desk", "pos": [1.0, 0.0, Ed - 1.4], "yaw": 90, "scale": 1.0, "size": [1.4, 0.75, 0.7]},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [5.6, 0.0, 1.0], "yaw": 200, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [5.6, 0.0, 1.8], "yaw": 160, "scale": 1.0, "collide": False},
    {"type": "leaflets", "pos": [1.6, 0.0, Ed / 2], "size": [2.6, 0.0, Ed - 1.0], "seed": 52, "count": 25, "collide": False},
    {"type": "strip_light", "pos": [3.5, 3.2, Ed / 2], "size": [3.0, 0.1, 0.2], "yaw": 90, "collide": False}]
Ex["lights"] = [{"kind": "area", "pos": [3.5, 3.1, Ed / 2], "look_at": [3.5, 0.0, Ed / 2], "size": 1.4, "color": [0.95, 0.97, 1.0], "blender_power": 90,
                 "godot_energy": 0.5, "range": 6.0}]
Ex["shots"] = [{"id": "a", "pos": [6.5, 2.5, 0.5], "look_at": [0.6, 1.2, Ed - 1.2], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [7.0, Ed]}, "priority": 1}]
Ex["spawns"] = {"from_street": {"pos": [6.2, 0.0, ue], "yaw": 90}}
Ex["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [6.55, 1.0, ue], "radius": 1.0},
    {"id": "safe", "kind": "examine", "pos": [1.2, 1.0, 1.0], "radius": 1.2, "text": "The safe stands open. Rubber bands on the floor of it; nothing they held."},
    {"id": "rates", "kind": "examine", "pos": [4.0, 1.0, Ed / 2], "radius": 1.4,
     "text": "WIJ KOPEN · WIJ VERKOPEN. The rates still change on the board every few seconds. Somewhere, the markets are open."},
    {"id": "ammo_guard", "kind": "pickup", "item": "handgun_ammo", "count": 6, "pos": [1.0, 0.75, Ed - 1.4], "radius": 0.9}]
Ex["enemies"] = []
write(Ex)

# ── The souvenir shop and its stockroom ─────────────────────────────────────────────────────
SO = [ZO[0] - T - 9.0, ZO[1] + SOUV["z0"]]
Sd = SOUV["z1"] - SOUV["z0"]
us = sc_ - SOUV["z0"]
Sv = shop_room("souvenirwinkel", "Souvenirs · Klompen", SO, (9.0, Sd), 3.4,
               "a souvenir shop on Damrak: clogs in racks, wheels of cheese, tulip bulbs in packets, Delft blue, T-shirts, the "
               "till by the door; the stockroom at the back.",
               {"floor": {"ph": "wood_floor_worn", "tint": [0.62, 0.52, 0.42], "rough": 0.6}, "wall": {"color": [0.92, 0.88, 0.8], "rough": 0.6},
                "ceiling": {"color": [0.9, 0.88, 0.84], "rough": 0.8}, "skirting": {"color": [0.15, 0.2, 0.45], "rough": 0.4}, "skirting_height": 0.12},
               exposure=0.9)
Sv["footsteps"] = "wood"
Sv["walls"] = {"east": {"facade": True, "openings": [glass_door(us, sw_, sh_)]},
               "west": {"openings": [{"kind": "door", "center": 1.4, "width": 0.9, "height": 2.1, "hinge": "right"}]}}
Sv["props"] = [
    {"type": "clogs", "pos": [4.0, 0.0, 0.45], "yaw": 0, "size": [4.0, 1.8, 0.7], "seed": 61, "empty": 0.25},
    {"type": "shelving", "pos": [4.6, 0.0, Sd - 0.3], "yaw": 180, "size": [6.0, 2.2, 0.45], "palette": "souvenir", "empty": 0.3, "seed": 62, "fallen": 6},
    {"type": "shelving", "pos": [3.4, 0.0, Sd / 2], "yaw": 90, "size": [3.2, 1.5, 0.9], "double": True, "palette": "souvenir", "empty": 0.35, "seed": 63, "shelves": 4},
    {"type": "cheeses", "pos": [6.6, 0.0, 1.0], "size": [0.5, 0.9, 0.5], "seed": 64},
    {"type": "cheeses", "pos": [7.2, 0.0, 1.1], "size": [0.45, 0.6, 0.45], "seed": 65},
    {"type": "coat_rack", "pos": [1.0, 0.0, Sd - 2.2], "yaw": 90, "size": [2.0, 1.7, 0.6], "seed": 66,
     "colors": [[0.85, 0.1, 0.1], [0.95, 0.5, 0.05], [0.95, 0.95, 0.92], [0.1, 0.2, 0.6], [0.1, 0.1, 0.1]]},   # I ♥ AMSTERDAM T-shirts
    {"type": "counter", "pos": [7.4, 0.0, Sd - 1.6], "yaw": -90, "size": [2.0, 1.0, 0.6], "till": True},
    {"type": "wall_sign", "pos": [0.04, 2.6, Sd / 2 + 1.0], "size": [2.4, 0.4, 0.03], "yaw": 90, "text": "I ♥ AMSTERDAM", "color": [1.0, 0.3, 0.3], "glow": 2.0,
     "collide": False},
    {"type": "strip_light", "pos": [4.5, 3.4, Sd / 2], "size": [5.0, 0.1, 0.2], "yaw": 90, "collide": False}]
Sv["lights"] = [{"kind": "area", "pos": [4.5, 3.3, Sd / 2], "look_at": [4.5, 0.0, Sd / 2], "size": 1.6, "color": [1.0, 0.95, 0.85], "blender_power": 95,
                 "godot_energy": 0.5, "range": 7.0}]
Sv["shots"] = [{"id": "a", "pos": [8.4, 2.7, Sd - 0.5], "look_at": [1.0, 1.0, 1.0], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [9.0, Sd]}, "priority": 1}]
Sv["spawns"] = {"from_street": {"pos": [8.2, 0.0, us], "yaw": 90}, "from_magazijn": {"pos": [0.8, 0.0, 1.4], "yaw": 270}}
Sv["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [8.55, 1.0, us], "radius": 1.0},
    {"id": "door_magazijn", "kind": "door", "pos": [0.45, 1.0, 1.4], "radius": 1.0},
    {"id": "clogs", "kind": "examine", "pos": [4.0, 1.0, 1.4], "radius": 1.4, "text": "Clogs, in every size, painted with windmills. A child's pair is missing from the end."},
    {"id": "dressing_till", "kind": "pickup", "item": "med_small", "count": 1, "pos": [7.2, 1.0, Sd - 1.6], "radius": 0.9}]
Sv["enemies"] = []
write(Sv)

MO = [SO[0] - T - 4.0, SO[1]]
Mg = shop_room("magazijn", "Magazijn", MO, (4.0, Sd), 3.0,
               "the souvenir shop's stockroom: steel shelving to the ceiling, cartons of stock, a first aid box on the wall.",
               {"floor": {"ph": "concrete_floor_painted", "tint": [0.55, 0.56, 0.58], "rough": 0.7}, "wall": {"color": [0.7, 0.7, 0.68], "rough": 0.8},
                "ceiling": {"color": [0.7, 0.7, 0.7], "rough": 0.9}, "skirting": None}, exposure=0.9)
Mg["walls"] = {"east": {"openings": [{"kind": "door", "center": 1.4, "width": 0.9, "height": 2.1, "hinge": "left"}]}}
Mg["props"] = [
    {"type": "shelving", "pos": [0.3, 0.0, Sd / 2], "yaw": 90, "size": [6.4, 2.8, 0.55], "palette": "grocery", "empty": 0.2, "seed": 71, "fallen": 3,
     "frame": {"color": [0.3, 0.33, 0.36], "rough": 0.4, "metal": 0.8}},
    {"type": "shelving", "pos": [2.2, 0.0, Sd - 0.3], "yaw": 180, "size": [3.0, 2.8, 0.55], "palette": "souvenir", "empty": 0.25, "seed": 72,
     "frame": {"color": [0.3, 0.33, 0.36], "rough": 0.4, "metal": 0.8}},
    {"type": "model", "model": "ph:cardboard_box_01", "pos": [2.6, 0.0, 3.0], "yaw": 20, "scale": 1.0, "size": [0.5, 0.4, 0.5]},
    {"type": "model", "model": "ph:cardboard_box_01", "pos": [2.9, 0.0, 3.8], "yaw": 70, "scale": 0.8, "collide": False},
    {"type": "model", "model": "ph:plastic_crate_02", "pos": [3.2, 0.0, 5.6], "yaw": 10, "scale": 1.0, "collide": False},
    {"type": "strip_light", "pos": [2.0, 3.0, Sd / 2], "size": [3.0, 0.1, 0.2], "yaw": 90, "collide": False}]
Mg["lights"] = [{"kind": "area", "pos": [2.0, 2.9, Sd / 2], "look_at": [2.0, 0.0, Sd / 2], "size": 1.0, "color": [0.95, 0.97, 1.0], "blender_power": 45,
                 "godot_energy": 0.4, "range": 5.0}]
Mg["shots"] = [{"id": "a", "pos": [3.6, 2.5, Sd - 0.4], "look_at": [0.6, 1.0, 1.0], "fov": 68, "zone": {"min": [0.0, 0.0], "max": [4.0, Sd]}, "priority": 1}]
Mg["spawns"] = {"from_winkel": {"pos": [3.2, 0.0, 1.4], "yaw": 90}}
Mg["interactables"] = [
    {"id": "door_winkel", "kind": "door", "pos": [3.55, 1.0, 1.4], "radius": 1.0},
    {"id": "first_aid_box", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [0.5, 1.1, Sd - 1.2], "radius": 0.9}]
Mg["enemies"] = []
write(Mg)

# ════════════════════════════════════════════════════════════════════════════════════
# Damrak north: the basin, the boats, the leaning houses across the water, the station ahead
# ════════════════════════════════════════════════════════════════════════════════════
rng = random.Random(181)
L = 90.0
BOAT_Z = 46.0   # the boat he boards, at its pier
N = street_room("damrak_noord", "Damrak", NO, (W, L), 12.0,
                "the north half of Damrak, along the basin: the tour boats tied up at their pontoons (the water high, the flood "
                "came up it), across the water the old houses that have settled every way on their piles, their windows lit; "
                "the hotels and shops on the street side; and ahead, over the Prins Hendrikkade, Centraal Station, floodlit.")
HOTEL = front("east", 26.05, 36.0, 0.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 1804,
              shop("HOTEL DE IJ", "hotel", "HOTEL", door_bay=2, power=100.0, awning=False, enter=True), lean=0.0, lit=0.5)
o = {"window_rooms": ROOMS, "lamp_power": 400.0, "lamp_energy": 1.0, "tide": 0.6,
     "ground": [{"name": "pavement_w", "min": [0.0, 0.0], "max": [4.0, L], "y": 0.06, "material": PAVERS},
                {"name": "road", "min": [4.0, 0.0], "max": [14.0, L], "y": 0.0, "material": BRICKS},
                {"name": "quay", "min": [14.0, 0.0], "max": [W, L], "y": 0.06, "material": QUAY},
                {"name": "hendrikkade", "min": [-30.0, -24.0], "max": [70.0, 0.0], "y": 0.0, "material": BRICKS},
                {"name": "stationsplein", "min": [-40.0, -70.0], "max": [80.0, -24.0], "y": 0.06, "material": PAVERS}],
     "canals": [{"axis": "z", "x": W, "side": 1, "width": 26.0, "water": WATER, "along": [-24.0, L + 0.3], "ends": "b", "far_quay": 0.4,
                 "far_furniture": False, "lit": 0.5, "shops": 0.15, "far_span": [-24.0, L + 0.3], "lean": [1.2, 3.2], "tilt": 1.4, "row_ends": "both"}],
     "tracks": [{"from": [8.5, L], "to": [8.5, -40.0], "y": 0.0}, {"from": [11.5, L], "to": [11.5, -40.0], "y": 0.0}],
     "lamps": [[1.2, float(z)] for z in range(6, int(L), 14)] + [[15.0, float(z) + 7] for z in range(6, int(L) - 7, 14)]}
o["facades"] = [
    front("east", 0.0, 10.0, 0.0, [5.0, 3.8, 3.6, 3.4, 3.2], 4, "cornice", 1801, shop("HOTEL CENTRAAL", "hotel", "HOTEL", awning=False), lean=0.0, lit=0.6, flags=2),
    front("east", 10.05, 18.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 1802, shop("SOUVENIRS", "souvenir", "SOUVENIRS"), gable_h=3.8),
    front("east", 18.05, 26.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "step", 1803, shop("T-SHIRTS · PETTEN", "souvenir", "T-SHIRTS"), gable_h=3.6),
    HOTEL,
    front("east", 36.05, 44.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "bell", 1805, shop("STEAKHOUSE DE OSSEKOP", "restaurant", "STEAKHOUSE"), gable_h=3.8),
    front("east", 44.05, 52.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 1806, shop("CAFÉ DE ZEEMAN", "cafe", "CAFÉ"), gable_h=3.6),
    front("east", 52.05, 60.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "cornice", 1807, shop("RONDVAARTEN · TICKETS", "souvenir", "TICKETS")),
    front("east", 60.05, 70.0, 0.0, [4.4, 3.4, 3.2, 3.0, 2.8], 4, "step", 1808, shop("COFFEESHOP DE KADE", "coffeeshop", "COFFEESHOP"), gable_h=3.8),
    front("east", 70.05, 80.0, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "cornice", 1809, shop("WISSELKANTOOR", "hotel", "EXCHANGE", awning=False)),
    front("east", 80.05, 90.0, 0.0, [4.4, 3.4, 3.2, 3.0], 4, "neck", 1810, shop("SNACKBAR DAMRAK", "snack", "SNACKBAR"), gable_h=3.8)]
N["outdoor"] = o
hc_, hw_, hh_ = shop_doorway(HOTEL)
props = []
for k, z in enumerate((22.0, 70.0)):   # the other pontoons out into the basin, a boat along each (the one he boards is a room's)
    props.append({"type": "pier", "pos": [W, 0.0, z], "yaw": -90, "size": [8.0, 0.4, 2.2], "collide": False})
    props.append({"type": "canal_boat", "pos": [W + 4.6, -0.55, z - 11.0], "yaw": -90, "size": [22.0, 2.4, 4.2],
                  "name": "RONDVAART %d" % (11 + k * 6), "collide": False, "glow": 0.25})
props += [
    {"type": "railing", "pos": [W - 0.25, 0.0, 19.0], "yaw": 90, "size": [38.0, 1.0, 0.1], "collide": False},     # (a gap at the pier he boards from)
    {"type": "railing", "pos": [W - 0.25, 0.0, 70.0], "yaw": 90, "size": [40.0, 1.0, 0.1], "collide": False},
    {"type": "station", "pos": [-45.0, 0.0, -66.0], "yaw": 0, "size": [110.0, 18.0, 40.0], "collide": False},   # (until the station is built)
    {"type": "crowd_barrier", "pos": [10.0, 0.0, 1.0], "yaw": 0, "size": [20.0, 1.1, 0.7], "seed": 81},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [5.0, 0.0, 2.6], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "model", "model": "ph:concrete_road_barrier", "pos": [15.0, 0.0, 2.6], "yaw": 0, "fit": [3.0, 1.0, 0.7]},
    {"type": "bus", "pos": [-8.0, 0.0, -12.0], "yaw": 0, "size": [12.0, 3.2, 2.6], "seed": 82},
    {"type": "bus", "pos": [30.0, 0.0, -14.0], "yaw": 180, "size": [12.0, 3.2, 2.6], "seed": 83},
    {"type": "evac_board", "pos": [3.0, 0.06, 8.0], "yaw": 0, "size": [1.8, 1.9, 0.6], "text": "TREINEN", "to": "CENTRAAL", "arrow": "up", "collide": False},
    {"type": "evac_board", "pos": [16.8, 0.06, BOAT_Z - 3.0], "yaw": -90, "size": [1.8, 1.9, 0.6], "text": "RONDVAART", "to": "GESLOTEN", "arrow": "right", "collide": False},
    {"type": "luggage", "pos": [10.0, 0.0, 12.0], "size": [12.0, 0.0, 10.0], "seed": 84, "cases": 6, "bags": 8, "pushchair": True, "collide": False},
    {"type": "luggage", "pos": [16.5, 0.06, 56.0], "size": [3.0, 0.0, 6.0], "seed": 85, "cases": 2, "bags": 3, "collide": False},
    {"type": "luggage", "pos": [2.5, 0.06, 64.0], "size": [3.0, 0.0, 6.0], "seed": 86, "cases": 2, "bags": 2, "chair": True, "collide": False},
    {"type": "leaflets", "pos": [10.0, 0.0, L / 2], "size": [W, 0.0, L], "seed": 87, "count": 380, "collide": False},
    {"type": "vehicle", "pos": [7.0, 0.0, 30.0], "yaw": 100, "size": [5.4, 2.3, 2.0], "livery": "police", "van": True, "door_open": "left"},
    {"type": "vehicle", "pos": [11.0, 0.0, 74.0], "yaw": 80, "size": [4.6, 1.5, 1.85], "livery": "car", "door_open": "right"},
    {"type": "model", "model": "ph:lifebuoy", "pos": [W - 0.35, 0.6, 58.0], "yaw": -90, "scale": 1.0, "collide": False},
    {"type": "bike", "pos": [1.0, 0.06, 50.0], "yaw": 10, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 188},
    {"type": "bike", "pos": [1.6, 0.06, 51.2], "yaw": 160, "roll": -82, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 189}]
N["props"] = props
N["walls"] = {"south": {"openings": [{"kind": "passage", "center": W / 2, "width": W, "height": 12.0}]},
              "north": {"openings": [{"kind": "passage", "center": W / 2, "width": W, "height": 12.0}]},   # (barred, until the station)
              "east": {"openings": [{"kind": "passage", "center": BOAT_Z, "width": 2.0, "height": 3.0}]},
              "west": {"openings": [glass_door(hc_, hw_, hh_)]}}
N["lights"] = [SUN]
N["shots"] = shots([
    ("a", [3.0, 4.2, 70.0], [17.0, 3.0, 93.0], 60, 72.0, 90.0),      # south-east: the Beurs's end, the basin's head
    ("b", [16.5, 4.2, 75.0], [4.0, 1.4, 52.0], 60, 54.0, 72.0),      # north-west along the shops
    ("c", [4.0, 4.6, 41.0], [42.0, 7.0, 52.0], 58, 36.0, 54.0),      # east across the water: the leaning houses, the boats
    ("d", [16.5, 4.2, 38.5], [5.0, 1.4, 16.0], 60, 18.0, 36.0),      # north-west
    ("e", [5.0, 4.8, 21.0], [14.0, 7.0, -40.0], 60, 0.0, 18.0)])     # north: the barriers, the station floodlit beyond
N["spawns"] = {"from_hotel": {"pos": [1.0, 0.06, hc_], "yaw": 270}}
N["interactables"] = [
    {"id": "door_hotel", "kind": "door", "pos": [0.45, 1.0, hc_], "radius": 1.0},
    {"id": "houses", "kind": "examine", "pos": [18.8, 1.0, 30.0], "radius": 1.8,
     "text": "The old houses across the water, leaning on each other like drunks at closing time. Lights on in half the windows."},
    {"id": "station", "kind": "examine", "pos": [10.0, 1.0, 3.6], "radius": 2.6,
     "text": "Centraal, across the Prins Hendrikkade. Floodlit. Buses abandoned in front of it. The barriers here are welded."},
    {"id": "shells_police", "kind": "pickup", "item": "shotgun_shells", "count": 4, "pos": [5.2, 0.0, 31.6], "radius": 0.9}]
N["enemies"] = [{"id": "op_de_kade", "kind": "verdronkene", "pos": [16.0, 0.06, 30.0], "yaw": 200},
                {"id": "bij_de_bagage", "kind": "verdronkene", "pos": [8.0, 0.0, 14.0], "yaw": 20}]
write(N)

# ── The tour boat at its pier: the gangway, the saloon ───────────────────────────────────────
RB = [NO[0] + W + T, NO[1] + BOAT_Z - 10.0]   # 6.2 x 18.6: the pier (x 0..1.9), the boat's saloon (x 2.4..6.2), along z
Rb = street_room("rondvaartboot", "Rondvaart 14", RB, (6.2, 18.6), 4.0,
                 "a glass-roofed tour boat tied up at its pier on the Damrak basin, the water high under it: the gangway, the "
                 "saloon's rows of seats with the life jackets on them, the skipper's console at the bow. Its lights are on. "
                 "It was the last trip of the night.")
Rb["outdoor"] = {"window_rooms": ROOMS, "lamp_power": 0.0, "lamp_energy": 0.0, "ground": [], "lamps": [], "rain": False}
Rb["walls"] = {"west": {"openings": [{"kind": "passage", "center": 10.0, "width": 2.0, "height": 3.0}]}}   # the gap in the quay's railing
Rb["footsteps"] = "wood"   # (the pier's planks, the boat's deck)
Rb["props"] = [
    {"type": "pier", "pos": [-0.3, 0.0, 10.0], "yaw": -90, "size": [8.0, 0.4, 2.2], "sign": "RONDVAARTEN · CANAL CRUISES", "collide": False},
    {"type": "canal_boat", "pos": [4.3, -0.35, 10.0], "yaw": -90, "size": [22.0, 3.2, 4.2], "name": "RONDVAART 14", "collide": False,
     "door": [0.0, 1.6], "aisle": 0.45, "glow": 1.4},
    {"type": "model", "model": "ph:lifebuoy", "pos": [0.4, 0.6, 6.4], "yaw": -90, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:life_jacket", "pos": [5.4, 0.5, 4.0], "yaw": 40, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:life_jacket", "pos": [3.2, 0.5, 14.5], "yaw": 160, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:life_jacket", "pos": [4.3, 0.0, 12.6], "yaw": 80, "scale": 1.0, "collide": False},
    {"type": "counter", "pos": [4.3, 0.0, 18.0], "yaw": 180, "size": [0.8, 1.0, 0.4], "till": False,
     "top": {"color": [0.08, 0.09, 0.1], "rough": 0.3}, "material": {"color": [0.82, 0.82, 0.8], "rough": 0.4}},   # the skipper's console, at the bow
    {"type": "wall_sign", "pos": [4.3, 1.3, 17.78], "size": [0.7, 0.16, 0.02], "yaw": 180, "text": "STUURHUT", "color": [0.4, 1.0, 0.5], "glow": 2.0, "collide": False},
    # what he can't walk through: the water either side of the pier, the boat's sides and seats
    {"type": "collider", "pos": [1.15, 0.0, 3.0], "size": [2.3, 1.0, 6.0]},
    {"type": "collider", "pos": [1.15, 0.0, 16.3], "size": [2.3, 1.0, 4.6]},
    {"type": "collider", "pos": [2.3, 0.0, 4.6], "size": [0.2, 1.0, 9.2]},
    {"type": "collider", "pos": [2.3, 0.0, 14.7], "size": [0.2, 1.0, 7.8]},
    {"type": "collider", "pos": [5.4, 0.0, 9.3], "size": [1.3, 1.0, 17.4]},                  # the port seats
    {"type": "collider", "pos": [3.2, 0.0, 4.7], "size": [1.3, 1.0, 8.2]},                   # the starboard seats, either side of the door
    {"type": "collider", "pos": [3.2, 0.0, 14.6], "size": [1.3, 1.0, 6.8]}]
Rb["lights"] = [{"kind": "area", "pos": [4.3, 2.2, 6.0], "look_at": [4.3, 0.0, 6.0], "size": 1.2, "color": [1.0, 0.88, 0.7], "blender_power": 60,
                 "godot_energy": 0.6, "range": 6.0},
                {"kind": "area", "pos": [4.3, 2.2, 13.0], "look_at": [4.3, 0.0, 13.0], "size": 1.2, "color": [1.0, 0.88, 0.7], "blender_power": 60,
                 "godot_energy": 0.6, "range": 6.0},
                {"kind": "point", "pos": [0.8, 2.6, 10.0], "color": [1.0, 0.7, 0.4], "blender_power": 40, "godot_energy": 0.4, "range": 5.0, "radius": 0.2}]
Rb["shots"] = [
    {"id": "a", "pos": [4.3, 2.0, 0.6], "look_at": [4.3, 0.9, 18.0], "fov": 64, "zone": {"min": [2.4, 0.0], "max": [6.2, 18.6]}, "priority": 2},
    {"id": "b", "pos": [0.5, 2.8, 15.5], "look_at": [3.6, 0.8, 8.6], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [2.4, 18.6]}, "priority": 1}]
Rb["spawns"] = {"from_damrak": {"pos": [0.6, 0.0, 10.0], "yaw": 270}}
Rb["interactables"] = [
    {"id": "boat", "kind": "examine", "pos": [2.0, 1.0, 10.0], "radius": 1.2,
     "text": "RONDVAART 14. Its engine's still warm. A ticket stub on the gangway: the 00:30 trip, the last of the night."},
    {"id": "first_aid_boat", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [4.3, 1.0, 18.0], "radius": 0.9}]
Rb["enemies"] = [{"id": "de_schipper", "kind": "verdronkene", "pos": [4.3, 0.0, 15.0], "yaw": 0}]
write(Rb)

# ── The hotel's bar, off its lobby ────────────────────────────────────────────────────────────
HO = [NO[0] - T - 12.0, NO[1] + HOTEL["z0"]]
Hd = HOTEL["z1"] - HOTEL["z0"]
uh = hc_ - HOTEL["z0"]
Hb = shop_room("hotel_bar", "Hotel de IJ · Bar", HO, (12.0, Hd), 3.6,
               "the bar of a hotel on Damrak: the long counter, the bottles lit along the back, stools, the booths by the window, a "
               "chandelier; glasses still on the tables. The night porter kept a gun behind the bar. It's gone.",
               {"floor": {"ph": "wood_floor_worn", "tint": [0.42, 0.3, 0.22], "rough": 0.5}, "wall": {"color": [0.32, 0.12, 0.1], "rough": 0.6},
                "ceiling": {"color": [0.5, 0.42, 0.34], "rough": 0.7}, "wainscot": {"ph": "dark_wood", "tint": [0.5, 0.36, 0.26], "scale": 0.5},
                "wainscot_height": 1.1, "skirting": None}, exposure=0.95)
Hb["walls"] = {"east": {"facade": True, "openings": [glass_door(uh, hw_, hh_)]}}
Hb["footsteps"] = "wood"
Hb["props"] = [
    {"type": "counter", "pos": [5.5, 0.0, 1.5], "yaw": 0, "size": [7.0, 1.1, 0.7], "till": True,
     "material": {"ph": "dark_wood", "tint": [0.45, 0.3, 0.2], "scale": 0.5}, "top": {"color": [0.12, 0.08, 0.06], "rough": 0.25}},
    {"type": "shelving", "pos": [5.5, 0.0, 0.3], "yaw": 0, "size": [7.0, 2.4, 0.4], "palette": "bar", "bottles": 0.95, "empty": 0.3, "seed": 81, "fallen": 2,
     "frame": {"ph": "dark_wood", "tint": [0.4, 0.28, 0.2], "scale": 0.5}},
    {"type": "model", "model": "ph:Chandelier_03", "pos": [6.0, 2.8, 5.0], "yaw": 0, "fit": [1.2, 0.8, 1.2], "collide": False},
    {"type": "model", "model": "ph:sofa_02", "pos": [3.0, 0.0, Hd - 0.5], "yaw": 180, "scale": 1.0, "size": [1.8, 0.8, 0.7]},
    {"type": "model", "model": "ph:Sofa_01", "pos": [7.0, 0.0, Hd - 0.5], "yaw": 180, "scale": 1.0, "size": [1.6, 0.8, 0.7]},
    {"type": "model", "model": "ph:CoffeeTable_01", "pos": [3.0, 0.0, Hd - 1.6], "yaw": 4, "scale": 0.8, "size": [1.25, 0.45, 0.6]},
    {"type": "model", "model": "ph:coffee_table_round_01", "pos": [7.0, 0.0, Hd - 1.6], "yaw": 0, "scale": 0.7, "size": [0.9, 0.35, 0.9]},
    {"type": "strip_light", "pos": [5.5, 2.5, 0.5], "size": [6.8, 0.06, 0.1], "collide": False}]
for k, x in enumerate((3.0, 4.2, 5.4, 6.6, 7.8)):   # the stools along the bar, one knocked over
    Hb["props"].append({"type": "model", "model": "ph:wooden_stool_01", "pos": [x, 0.0, 2.4 + (0.3 if k == 3 else 0.0)], "yaw": 15 * k,
                        "tip": 90 if k == 3 else 0, "scale": 1.0, "collide": False})
for k, (x, z) in enumerate(((2.6, 5.2), (5.8, 6.1), (8.6, 4.9))):   # the tables in the middle, left as they were
    Hb["props"].append({"type": "model", "model": "ph:round_wooden_table_01", "pos": [x, 0.0, z], "yaw": 20 * k, "fit": [1.05, 0.75, 1.05],
                        "size": [1.05, 0.75, 1.05]})
    for j, (dx, dz, yaw) in enumerate(((0.0, -0.85, 0), (0.0, 0.85, 180), (0.85, 0.0, -90))):
        if j == 2 and k != 1:
            continue
        down = k == 2 and j == 1
        Hb["props"].append({"type": "model", "model": "ph:dining_chair_02", "pos": [round(x + dx, 2), 0.0, round(z + dz + (0.35 if down else 0.0), 2)],
                            "yaw": yaw + 12 * (j - 1), "scale": 1.0, "size": [0.45, 0.9, 0.5], **({"tip": 90} if down else {})})
Hb["lights"] = [{"kind": "area", "pos": [6.0, 3.5, 5.0], "look_at": [6.0, 0.0, 5.0], "size": 2.0, "color": [1.0, 0.8, 0.55], "blender_power": 110,
                 "godot_energy": 0.5, "range": 8.0},
                {"kind": "point", "pos": [5.5, 1.8, 0.7], "color": [1.0, 0.7, 0.4], "blender_power": 30, "godot_energy": 0.3, "range": 4.0, "radius": 0.3}]
Hb["shots"] = [{"id": "a", "pos": [11.4, 2.8, Hd - 0.5], "look_at": [2.0, 1.0, 1.2], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [12.0, Hd]}, "priority": 1}]
Hb["spawns"] = {"from_street": {"pos": [11.2, 0.0, uh], "yaw": 90}}
Hb["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [11.55, 1.0, uh], "radius": 1.0},
    {"id": "glasses", "kind": "examine", "pos": [3.0, 1.0, Hd - 2.4], "radius": 1.2, "text": "Two glasses, half full. A room key between them: 214."},
    {"id": "porter", "kind": "examine", "pos": [8.6, 1.0, 0.9], "radius": 1.0,
     "text": "Under the bar, a holster screwed to the woodwork. The night porter's gun is gone. Its rounds are still in the ice bin, of all places."},
    {"id": "rounds_ice_bin", "kind": "pickup", "item": "handgun_ammo", "count": 10, "pos": [8.6, 0.9, 1.0], "radius": 0.9}]
Hb["enemies"] = [{"id": "de_barman", "kind": "verdronkene", "pos": [4.2, 0.0, 0.9], "yaw": 180}]
write(Hb)

# ── The store's staff exit: the guards' pass opens it; it lets out on Damrak, behind the barriers ──
Wh = json.load(open(R + "warenhuis.json"))
Ww = Wh["bounds"]["max"][0]
STAFF = 2.0   # along the store's east wall, behind the escalators
Wh["walls"]["east"] = {"openings": [{"kind": "door", "center": STAFF, "width": 1.0, "height": 2.2, "hinge": "left"}]}
Wh["interactables"] = [i for i in Wh["interactables"] if i["id"] != "door_damrak"] + [
    {"id": "door_damrak", "kind": "door", "pos": [Ww - 0.45, 1.0, STAFF], "radius": 1.0, "target_room": "damrak_zuid", "target_spawn": "from_warenhuis",
     "lock": "staff_pass", "locked_text": "A steel door: PERSONEEL. The card reader by it shows red.",
     "unlock_text": "You hold the pass to the reader. It beeps, green; the lock clacks back."}]
Wh["props"] = [p for p in Wh["props"] if p.get("id") != "staff_sign"] + [
    {"type": "wall_sign", "id": "staff_sign", "pos": [Ww - 0.04, 2.75, STAFF], "size": [1.0, 0.2, 0.03], "yaw": -90, "text": "PERSONEEL",
     "color": [0.9, 0.95, 1.0], "glow": 1.2, "collide": False}]
Wh["spawns"]["from_damrak"] = {"pos": [Ww - 0.9, 0.0, STAFF], "yaw": 90}
Wh["props"] = [p for p in Wh["props"] if p["pos"][1] > 1.0 or ((p["pos"][0] - Ww) ** 2 + (p["pos"][2] - STAFF) ** 2) ** 0.5 > 1.8]
Wh["props"].append({"type": "exit_sign", "pos": [Ww - 0.08, 2.4, STAFF], "size": [0.42, 0.17, 0.07], "yaw": -90, "collide": False})
json.dump(Wh, open(R + "warenhuis.json", "w"), indent=2, ensure_ascii=True)
open(R + "warenhuis.json", "a").write("\n")
Bv = json.load(open(R + "beveiliging.json"))
Bv["interactables"] = [i for i in Bv["interactables"] if i["id"] != "staff_pass"] + [
    {"id": "staff_pass", "kind": "pickup", "item": "staff_pass", "count": 1, "pos": [2.0, 0.76, 0.85], "radius": 0.9}]
json.dump(Bv, open(R + "beveiliging.json", "w"), indent=2, ensure_ascii=True)
open(R + "beveiliging.json", "a").write("\n")
print("damrak: zuid", ZO, "noord", NO, "gate", GATE, "staff door", round(zc_, 3), "hotel door", round(hc_, 3))
