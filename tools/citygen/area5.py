# damned_waters/tools/citygen/area5.py
# Generates area 5 (storey 14, district 4: the Dam): dam (the square), nieuwe_kerk (the church made a
# shelter), warenhuis (the department store's ground floor), beveiliging (its security office); and
# opens Rokin noord onto it. The November funfair stands among the evacuation point (buses, army
# trucks, a field hospital), as the night left them (docs/city_aftermath.md).
from pathlib import Path
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import front, shop, shop_doorway, glass_door, street_room, shop_room, write, PAVERS, SUN, ROOMS, R  # noqa: E402

C.DISTRICT.update({"storey": 14, "name": "district 4: the Dam"})
T = 0.3
NO = [883.4, -224.6]                  # rokin_noord's corner (its north edge at z -224.6)
DO = [850.0, NO[1] - T - 70.0]        # the Dam: 90 x 70, its south edge a wall's thickness north of Rokin's
COBBLES = C.WET("cobblestone_floor_04", [0.78, 0.74, 0.7], 0.7, 0.35)
rng = random.Random(91)

D = street_room("dam", "De Dam", DO, (90.0, 70.0), 14.0,
                "the Dam: the Royal Palace along its west side, the Nieuwe Kerk at its north-west corner, the National "
                "Monument on the east, the department store on the north by the way into Damrak. The November funfair "
                "was up when it happened, and the army made the square the evacuation point around it: the Ferris wheel "
                "and the rides still lit and stopped, buses lined up with their doors open, army trucks, a field hospital, "
                "and the luggage of thousands left where the queues were.")
STORE = front("south", 33.0, 56.0, 0.0, [5.0, 4.0, 3.8, 3.6, 3.4], 9, "cornice", 901,
              shop("WARENHUIS DE ZWERM", "hotel", False, door_bay=7, power=130.0, awning=False, enter=True), lean=0.0, lit=0.7, flags=4)
o = {"window_rooms": ROOMS, "lamp_power": 420.0, "lamp_energy": 1.0, "tide": 0.5,
     "ground": [{"name": "dam", "min": [0.0, 0.0], "max": [90.0, 70.0], "y": 0.0, "material": COBBLES}],
     "tracks": [{"from": [46.4, 70.0], "to": [46.4, 40.0], "y": 0.0}, {"from": [46.4, 40.0], "to": [72.0, 12.0], "y": 0.0},
                {"from": [72.0, 12.0], "to": [72.0, 0.0], "y": 0.0}],
     "lamps": [[4.0, 4.0], [30.0, 2.0], [58.0, 2.0], [86.0, 4.0], [87.0, 34.0], [86.0, 66.0], [60.0, 68.0], [32.0, 68.0], [4.0, 66.0], [3.0, 35.0]],
     "rooftop_signs": [{"at": [44.5, 22.6, -1.5], "text": "DE ZWERM", "color": [1.0, 0.82, 0.4], "size": 2.0, "yaw": 0.0}]}
o["facades"] = [
    # the north side: the church (a prop, with its own front), a lane, the store, a narrow house, Damrak, the corner
    front("south", 26.05, 32.95, 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 902, shop("SOUVENIRS", "souvenir", "SOUVENIRS"), gable_h=3.8),
    STORE,
    front("south", 56.05, 61.95, 0.0, [5.0, 4.0, 3.8, 3.6], 3, "bell", 903, door_bay=1, stoop=0.0, gable_h=3.6),
    front("south", 82.05, 90.0, 0.0, [4.6, 3.6, 3.4, 3.2, 3.0], 3, "cornice", 904, shop("CAFÉ DE DAM", "cafe", "CAFÉ")),
    # the east side: the grand hotel behind the monument, Damstraat
    front("west", 0.0, 3.95, 90.0, [4.6, 3.6, 3.4, 3.2, 3.0], 2, "cornice", 905),
    front("west", 4.0, 56.0, 90.0, [5.4, 4.2, 4.0, 3.8, 3.6, 3.4], 16, "cornice", 906,
          shop("GRAND HOTEL DE WITTE ZWAAN", "hotel", "HOTEL", door_bay=7, power=120.0, awning=False), lean=0.0, lit=0.55, flags=5),
    front("west", 66.05, 70.0, 90.0, [4.6, 3.6, 3.4, 3.2], 2, "cornice", 907),
    # the south side: either side of Rokin, the Kalverstraat's mouth
    front("north", 8.05, 15.95, 70.0, [4.6, 3.6, 3.4, 3.2], 3, "cornice", 908, shop("WISSELKANTOOR", "hotel", "EXCHANGE", awning=False), sides=True),
    front("north", 16.05, 24.5, 70.0, [4.4, 3.4, 3.2, 3.0], 3, "step", 909, shop("FRIETWINKEL", "snack", "FRIET"), gable_h=3.8),
    front("north", 24.55, 33.1, 70.0, [4.6, 3.6, 3.4, 3.2], 4, "cornice", 910, shop("SIGARENMAGAZIJN DE DAM", "snack", "SIGAREN")),
    front("north", 59.7, 70.0, 70.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 911, shop("BANKETBAKKERIJ", "cafe", "TAART")),
    front("north", 70.05, 80.0, 70.0, [4.6, 3.6, 3.4, 3.2], 3, "neck", 912, shop("SOUVENIRS · KAAS", "souvenir", "KAAS"), gable_h=3.8),
    front("north", 80.05, 90.0, 70.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 913, door_bay=2, stoop=0.0)]
sc, sw, sh = shop_doorway(STORE)
KERK_DOOR = 16.0   # the church's door along the Dam's north edge (x)
props = [
    {"type": "palace", "pos": [0.0, 0.0, 64.0], "yaw": 90, "size": [58.0, 24.0, 40.0], "collide": False},
    {"type": "gothic_front", "pos": [6.0, 0.0, 0.0], "yaw": 0, "size": [20.0, 22.0, 36.0], "door": [KERK_DOOR - 6.0, 1.8, 2.6], "spire": 14.0, "glow": 0.32,
     "collide": False},
    {"type": "monument", "pos": [74.0, 0.0, 36.0], "yaw": -90, "size": [16.0, 22.0, 16.0], "collide": False},
    {"type": "lbox_collider", "pos": [74.0, 0.0, 36.0], "size": [6.0, 3.0, 6.0]},
    # the funfair: the wheel by the palace, the drop tower, the carousel, the stalls
    {"type": "ferris_wheel", "pos": [20.0, 0.0, 22.0], "yaw": 35, "size": [18.0, 32.0, 5.0], "seed": 3, "colours": ["white", "blue"], "name": "REUZENRAD",
     "collide": False},
    {"type": "drop_tower", "pos": [14.0, 0.0, 55.0], "yaw": 20, "size": [2.6, 46.0, 2.6], "stopped": 0.62, "name": "FREE FALL", "collide": False},
    {"type": "carousel", "pos": [40.0, 0.0, 47.0], "yaw": 0, "size": [11.0, 6.4, 11.0], "name": "DRAAIMOLEN"},
    {"type": "fair_stall", "pos": [30.0, 0.0, 33.0], "yaw": 0, "size": [5.0, 2.8, 2.6], "kind": "oliebollen", "seed": 1},
    {"type": "fair_stall", "pos": [36.0, 0.0, 33.0], "yaw": 0, "size": [5.0, 2.8, 2.6], "kind": "schiettent", "seed": 2},
    {"type": "fair_stall", "pos": [36.0, 0.0, 61.0], "yaw": -30, "size": [5.0, 2.8, 2.6], "kind": "suikerspin", "seed": 3},
    {"type": "fair_stall", "pos": [46.0, 0.0, 22.0], "yaw": -90, "size": [5.0, 2.8, 2.6], "kind": "grijper", "seed": 4},
    # the evacuation point: buses at the hotel's kerb, army trucks by Damrak, the field hospital, the lights
    {"type": "bus", "pos": [81.0, 0.0, 19.0], "yaw": 90, "size": [18.0, 3.1, 2.55], "board": "EVACUATIE · CENTRAAL"},
    {"type": "bus", "pos": [81.0, 0.0, 39.5], "yaw": 90, "size": [18.0, 3.1, 2.55], "board": "EVACUATIE · CENTRAAL"},
    {"type": "bus", "pos": [81.0, 0.0, 60.0], "yaw": 95, "size": [18.0, 3.1, 2.55], "board": "NIET INSTAPPEN"},
    {"type": "vehicle", "pos": [66.0, 0.0, 9.0], "yaw": 100, "size": [7.0, 3.0, 2.4], "livery": "army", "van": True, "door_open": "left"},
    {"type": "vehicle", "pos": [57.0, 0.0, 14.0], "yaw": 70, "size": [7.0, 3.0, 2.4], "livery": "army", "van": True},
    {"type": "vehicle", "pos": [56.0, 0.0, 24.0], "yaw": 160, "size": [6.0, 2.6, 2.1], "livery": "ambulance", "van": True, "door_open": "right"},
    {"type": "aid_post", "pos": [56.0, 0.0, 34.0], "yaw": 0, "size": [6.0, 3.4, 6.0], "military": True, "covered": 2, "stretchers": 3, "seed": 5},
    {"type": "aid_post", "pos": [63.5, 0.0, 34.0], "yaw": 0, "size": [6.0, 3.4, 6.0], "military": True, "covered": 0, "stretchers": 3, "seed": 6},
    {"type": "light_tower", "pos": [8.0, 0.0, 64.0], "yaw": 40, "size": [2.2, 8.5, 1.4], "aim": [12.0, 0.0, 20.0], "collide": False},
    {"type": "light_tower", "pos": [48.0, 0.0, 6.0], "yaw": 180, "size": [2.2, 8.5, 1.4], "aim": [0.0, 0.0, 22.0], "collide": False},
    {"type": "light_tower", "pos": [76.0, 0.0, 66.0], "yaw": 200, "size": [2.2, 8.5, 1.4], "aim": [0.0, 0.0, 24.0], "collide": False}]
for k, z in enumerate((48.0, 51.0, 54.0)):   # the queue lanes for the buses, empty now
    props.append({"type": "crowd_barrier", "pos": [70.0, 0.0, z], "yaw": 0, "size": [12.0, 1.1, 0.7], "seed": 20 + k, "tape": k == 0})
props += [
    {"type": "crowd_barrier", "pos": [4.0, 0.0, 69.0], "yaw": 0, "size": [8.0, 1.1, 0.7], "seed": 30},       # the Kalverstraat's mouth, by the palace
    {"type": "crowd_barrier", "pos": [72.0, 0.0, 1.0], "yaw": 0, "size": [20.0, 1.1, 0.7], "seed": 31},      # Damrak: not yet
    {"type": "crowd_barrier", "pos": [89.0, 0.0, 61.0], "yaw": 90, "size": [10.0, 1.1, 0.7], "seed": 32},    # Damstraat
    {"type": "crowd_barrier", "pos": [3.0, 0.0, 3.0], "yaw": 45, "size": [6.0, 1.1, 0.7], "seed": 33},
    {"type": "evac_board", "pos": [74.0, 0.0, 46.0], "yaw": 180, "size": [1.8, 1.9, 0.6], "text": "EVACUATIE · BUSSEN", "to": "RIJ HIER", "arrow": "right", "collide": False},
    {"type": "evac_board", "pos": [70.0, 0.0, 4.5], "yaw": 180, "size": [1.8, 1.9, 0.6], "text": "EVACUATIEROUTE", "to": "CENTRAAL", "arrow": "up", "collide": False},
    {"type": "luggage", "pos": [62.0, 0.0, 46.0], "size": [8.0, 0.0, 6.0], "seed": 41, "cases": 9, "bags": 7, "pushchair": True, "chair": True, "collide": False},
    {"type": "luggage", "pos": [76.0, 0.0, 28.0], "size": [6.0, 0.0, 10.0], "seed": 42, "cases": 7, "bags": 5, "crutches": True, "collide": False},
    {"type": "luggage", "pos": [47.0, 0.0, 62.0], "size": [6.0, 0.0, 5.0], "seed": 43, "cases": 4, "bags": 4, "collide": False},
    {"type": "luggage", "pos": [30.0, 0.0, 44.0], "size": [6.0, 0.0, 5.0], "seed": 44, "cases": 3, "bags": 4, "umbrella": True, "collide": False},
    {"type": "leaflets", "pos": [45.0, 0.0, 35.0], "size": [88.0, 0.0, 68.0], "seed": 45, "count": 520, "collide": False},
    {"type": "fire_pump", "pos": [20.0, 0.0, 66.0], "yaw": 0, "size": [0.9, 0.8, 0.6], "to": [3.0, 2.0]},
    {"type": "model", "model": "ph:portable_generator", "pos": [26.0, 0.0, 26.0], "yaw": 20, "fit": [0.8, 0.6, 0.55], "collide": False},
    {"type": "model", "model": "ph:Megaphone_01", "pos": [65.0, 0.0, 49.5], "yaw": 70, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:old_gas_mask", "pos": [44.0, 0.0, 20.0], "yaw": 200, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:metal_jerrycan_green", "pos": [64.5, 0.0, 8.2], "yaw": 30, "scale": 1.0, "collide": False},
    {"type": "bike", "pos": [5.0, 0.0, 30.0], "yaw": 10, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 160},
    {"type": "bike", "pos": [6.0, 0.0, 31.4], "yaw": 160, "roll": -82, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 161}]
props = [p for p in props if p["type"] != "lbox_collider"]
props += [{"type": "collider", "pos": [74.0, 0.0, 36.0], "size": [7.0, 1.0, 7.0]},                  # the monument's pillar and steps
          {"type": "collider", "pos": [20.0, 0.0, 22.0], "yaw": 35, "size": [19.2, 2.0, 10.0]},    # the wheel's platform and legs
          {"type": "collider", "pos": [14.0, 0.0, 55.0], "yaw": 20, "size": [8.6, 1.0, 8.6]}]      # the drop tower's base
D["outdoor"] = o
D["props"] = props
D["walls"] = {"south": {"openings": [{"kind": "passage", "center": 46.4, "width": 26.0, "height": 12.0},
                                     {"kind": "passage", "center": 4.0, "width": 8.0, "height": 10.0}]},
              "north": {"openings": [{"kind": "door", "center": KERK_DOOR, "width": 1.8, "height": 2.6, "hinge": "left"},
                                     glass_door(sc, sw, sh),
                                     {"kind": "passage", "center": 72.0, "width": 20.0, "height": 12.0}]},
              "east": {"openings": [{"kind": "passage", "center": 61.0, "width": 10.0, "height": 10.0}]}}
D["lights"] = [SUN, {"kind": "point", "pos": [20.0, 8.0, 22.0], "color": [0.85, 0.9, 1.0], "blender_power": 0, "godot_energy": 0.9, "range": 18.0},
               {"kind": "point", "pos": [40.0, 4.0, 47.0], "color": [1.0, 0.8, 0.5], "blender_power": 0, "godot_energy": 0.8, "range": 10.0},
               {"kind": "point", "pos": [59.0, 2.6, 34.0], "color": [0.95, 0.97, 1.0], "blender_power": 0, "godot_energy": 0.7, "range": 9.0},
               {"kind": "point", "pos": [14.0, 6.0, 55.0], "color": [1.0, 0.4, 0.75], "blender_power": 0, "godot_energy": 0.5, "range": 10.0}]
D["shots"] = [
    {"id": "a", "pos": [29.0, 3.6, 68.0], "look_at": [8.0, 10.0, 28.0], "fov": 64, "zone": {"min": [0.0, 35.0], "max": [30.0, 70.0]}, "priority": 1},
    {"id": "b", "pos": [47.0, 3.6, 69.0], "look_at": [22.0, 10.0, 26.0], "fov": 64, "zone": {"min": [30.0, 35.0], "max": [60.0, 70.0]}, "priority": 1},
    {"id": "c", "pos": [61.0, 3.6, 68.5], "look_at": [84.0, 4.0, 26.0], "fov": 62, "zone": {"min": [60.0, 35.0], "max": [90.0, 70.0]}, "priority": 1},
    {"id": "d", "pos": [2.6, 3.8, 34.0], "look_at": [17.0, 5.0, 2.0], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [30.0, 35.0]}, "priority": 1},
    {"id": "e", "pos": [44.0, 3.4, 20.0], "look_at": [46.0, 6.0, 0.0], "fov": 62, "zone": {"min": [30.0, 0.0], "max": [60.0, 15.0]}, "priority": 1},
    {"id": "g", "pos": [60.0, 4.0, 27.0], "look_at": [0.0, 12.0, 33.0], "fov": 64, "zone": {"min": [30.0, 15.0], "max": [60.0, 35.0]}, "priority": 1},
    {"id": "f", "pos": [61.0, 3.6, 21.0], "look_at": [76.0, 9.0, 38.0], "fov": 62, "zone": {"min": [60.0, 0.0], "max": [90.0, 35.0]}, "priority": 1}]
D["spawns"] = {"from_rokin": {"pos": [46.4, 0.0, 67.0], "yaw": 0}, "from_kerk": {"pos": [KERK_DOOR, 0.0, 1.2], "yaw": 180},
               "from_warenhuis": {"pos": [sc, 0.0, 1.2], "yaw": 180}}
D["interactables"] = [
    {"id": "to_rokin", "kind": "door", "pos": [46.4, 1.0, 69.8], "radius": 1.6, "target_room": "rokin_noord", "target_spawn": "from_dam"},
    {"id": "door_kerk", "kind": "door", "pos": [KERK_DOOR, 1.0, 0.45], "radius": 1.0},
    {"id": "door_warenhuis", "kind": "door", "pos": [sc, 1.0, 0.45], "radius": 1.0},
    {"id": "palace", "kind": "examine", "pos": [1.0, 1.0, 35.0], "radius": 2.0,
     "text": "The Royal Palace. Every window lit, every door shut. Over the balcony someone has hung a bedsheet: EVACUATIEPUNT DAM."},
    {"id": "wheel", "kind": "examine", "pos": [24.0, 1.0, 26.0], "radius": 2.4,
     "text": "The Ferris wheel, stopped, its lights still running round. High up, one gondola's door swings open in the wind."},
    {"id": "carousel", "kind": "examine", "pos": [40.0, 1.0, 53.0], "radius": 2.0,
     "text": "The carousel's organ is still playing. The horses have stopped halfway up their poles."},
    {"id": "buses", "kind": "examine", "pos": [78.5, 1.0, 39.5], "radius": 2.0,
     "text": "The buses never left. Their doors are open, their engines off, the seats full of bags."},
    {"id": "monument", "kind": "examine", "pos": [65.5, 1.0, 36.0], "radius": 2.0,
     "text": "The National Monument. On its steps, hundreds of candles, burned down. Names written in chalk round the base."},
    {"id": "damrak", "kind": "examine", "pos": [72.0, 1.0, 2.4], "radius": 2.6,
     "text": "Damrak, straight to Centraal. The barriers are chained together here; the army closed it. There has to be another way round."},
    {"id": "kalverstraat", "kind": "examine", "pos": [4.0, 1.0, 67.6], "radius": 2.0, "text": "The Kalverstraat. Barred, the shutters down all along it."},
    {"id": "shells_truck", "kind": "pickup", "item": "shotgun_shells", "count": 6, "pos": [64.6, 0.0, 11.2], "radius": 1.0},
    {"id": "first_aid_field", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [55.4, 0.78, 31.6], "radius": 0.9},
    {"id": "ammo_bus", "kind": "pickup", "item": "handgun_ammo", "count": 10, "pos": [79.7, 0.0, 33.0], "radius": 0.9}]
D["enemies"] = [{"id": "bij_het_rad", "kind": "verdronkene", "pos": [26.0, 0.0, 30.0], "yaw": 120},
                {"id": "in_de_rij", "kind": "verdronkene", "pos": [66.0, 0.0, 52.5], "yaw": 250},
                {"id": "bij_de_bus", "kind": "verdronkene", "pos": [78.0, 0.0, 22.0], "yaw": 270},
                {"id": "in_het_veldhospitaal", "kind": "verdronkene", "pos": [60.0, 0.0, 37.0], "yaw": 30},
                {"id": "bij_de_draaimolen", "kind": "verdronkene", "pos": [44.0, 0.0, 40.0], "yaw": 160}]
write(D)

# ── The Nieuwe Kerk inside: the church made a shelter ──────────────────────────────────────
KO = [DO[0] + 6.0, DO[1] - T - 36.0]
K = shop_room("nieuwe_kerk", "De Nieuwe Kerk", KO, (20.0, 36.0), 22.0,
              "the Nieuwe Kerk inside, made an emergency shelter: rows of camp beds down the nave and the aisles under the "
              "gothic arcades and the wooden vault, the first aid post by the door, the great organ on its gallery at the far "
              "end; most of the beds empty, some not.",
              {"floor": {"ph": "stone_tiles_02", "tint": [0.72, 0.7, 0.66], "rough": 0.55},
               "wall": {"color": [0.78, 0.76, 0.7], "rough": 0.9, "noise": 0.12},
               "ceiling": {"color": [0.12, 0.09, 0.07], "rough": 0.8}, "skirting": None}, exposure=1.0)
K["walls"] = {"south": {"facade": True, "openings": [{"kind": "door", "center": KERK_DOOR - 6.0, "width": 1.8, "height": 2.6, "hinge": "right"}]}}
kp = [
    {"type": "arcade", "pos": [5.0, 0.0, 18.0], "yaw": 90, "size": [36.0, 22.0, 1.2], "bay": 6.0, "spring": 8.0, "pier": 1.4, "collide": False},
    {"type": "arcade", "pos": [15.0, 0.0, 18.0], "yaw": 90, "size": [36.0, 22.0, 1.2], "bay": 6.0, "spring": 8.0, "pier": 1.4, "collide": False},
    {"type": "nave_vault", "pos": [10.0, 16.0, 18.0], "yaw": 0, "size": [9.0, 5.5, 36.0], "bay": 6.0, "collide": False},
    {"type": "organ", "pos": [10.0, 0.0, 1.6], "yaw": 0, "size": [8.0, 19.0, 1.4], "gallery": 4.5, "collide": False},
    {"type": "collider", "pos": [10.0, 0.0, 1.0], "size": [10.0, 4.5, 2.0]},   # the organ gallery's foot
    {"type": "pulpit", "pos": [14.0, 0.0, 15.0], "yaw": -90, "size": [1.6, 5.2, 1.6]},
    {"type": "counter", "pos": [3.0, 0.0, 31.0], "size": [2.4, 0.9, 0.8], "yaw": 90, "till": False, "top": {"color": [0.9, 0.9, 0.9], "rough": 0.4}},
    {"type": "counter", "pos": [3.0, 0.0, 27.0], "size": [2.4, 0.9, 0.8], "yaw": 90, "till": False, "top": {"color": [0.9, 0.9, 0.9], "rough": 0.4}},
    {"type": "model", "model": "ph:medical_box", "pos": [3.0, 0.9, 31.6], "yaw": 90, "fit": [0.5, 0.35, 0.3], "collide": False},
    {"type": "model", "model": "ph:clipboard", "pos": [3.1, 0.9, 27.6], "yaw": 70, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:plastic_crate_01", "pos": [1.0, 0.0, 34.5], "yaw": 10, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:plastic_crate_01", "pos": [1.6, 0.0, 34.6], "yaw": -5, "scale": 1.0, "collide": False},
    {"type": "luggage", "pos": [18.0, 0.0, 31.0], "size": [2.6, 0.0, 6.0], "seed": 51, "cases": 4, "bags": 5, "umbrella": False, "collide": False}]
for z in (6.0, 12.0, 18.0, 24.0, 30.0):   # the piers
    for x in (5.0, 15.0):
        kp.append({"type": "gothic_pier", "pos": [x, 0.0, z], "size": [1.4, 7.6, 1.4], "rib": 0.0})
for z in (3.0, 9.0, 15.0, 21.0, 27.0, 33.0):   # the windows down both sides
    kp.append({"type": "gothic_window", "pos": [0.06, 3.2, z], "yaw": 90, "size": [2.6, 10.0, 0.1], "collide": False})
    kp.append({"type": "gothic_window", "pos": [19.94, 3.2, z], "yaw": -90, "size": [2.6, 10.0, 0.1], "collide": False})
for z in (9.0, 18.0, 27.0):   # the brass crowns hanging in the nave
    kp.append({"type": "chandelier", "pos": [10.0, 13.0, z], "size": [2.2, 1.5, 2.2], "chain": 8.0, "power": 80.0, "collide": False})
rng_k = random.Random(57)
for x in (8.2, 11.8):   # camp beds down the nave, a few with somebody still in them
    for z in [7.0 + 2.6 * k for k in range(8)]:
        kp.append({"type": "camp_bed", "pos": [x, 0.0, z], "yaw": 90 if x < 10 else -90, "size": [0.7, 0.42, 1.9],
                   "occupied": rng_k.random() < 0.2, "seed": int(x * 100 + z)})
for x in (2.3, 17.7):   # and down the aisles
    for z in [7.5 + 3.0 * k for k in range(6)]:
        kp.append({"type": "camp_bed", "pos": [x, 0.0, z], "yaw": 0, "size": [0.7, 0.42, 1.9], "occupied": rng_k.random() < 0.15,
                   "seed": int(x * 100 + z)})
K["props"] = kp
K["lights"] = [{"kind": "area", "pos": [10.0, 15.0, 10.0], "look_at": [10.0, 0.0, 10.0], "size": 4.0, "color": [1.0, 0.82, 0.6], "blender_power": 900, "godot_energy": 0.7, "range": 16.0},
               {"kind": "area", "pos": [10.0, 15.0, 26.0], "look_at": [10.0, 0.0, 26.0], "size": 4.0, "color": [1.0, 0.82, 0.6], "blender_power": 900, "godot_energy": 0.7, "range": 16.0},
               {"kind": "point", "pos": [3.0, 2.6, 29.0], "color": [0.95, 0.97, 1.0], "blender_power": 120, "godot_energy": 0.6, "range": 6.0, "radius": 0.2},
               {"kind": "point", "pos": [10.0, 6.5, 2.5], "color": [1.0, 0.75, 0.45], "blender_power": 160, "godot_energy": 0.4, "range": 8.0, "radius": 0.5}]
K["shots"] = [
    {"id": "a", "pos": [10.0, 3.4, 35.0], "look_at": [10.0, 8.0, 2.0], "fov": 62, "zone": {"min": [6.0, 18.0], "max": [14.0, 36.0]}, "priority": 1},
    {"id": "b", "pos": [13.0, 5.0, 2.8], "look_at": [7.0, 1.0, 30.0], "fov": 62, "zone": {"min": [6.0, 0.0], "max": [14.0, 18.0]}, "priority": 1},
    {"id": "c", "pos": [0.9, 3.2, 34.4], "look_at": [3.0, 3.0, 6.0], "fov": 60, "zone": {"min": [0.0, 0.0], "max": [6.0, 36.0]}, "priority": 1},
    {"id": "d", "pos": [19.1, 3.2, 1.0], "look_at": [17.0, 2.0, 32.0], "fov": 60, "zone": {"min": [14.0, 0.0], "max": [20.0, 36.0]}, "priority": 1}]
K["spawns"] = {"from_dam": {"pos": [KERK_DOOR - 6.0, 0.0, 34.8], "yaw": 0}}
K["interactables"] = [
    {"id": "door_dam", "kind": "door", "pos": [KERK_DOOR - 6.0, 1.0, 35.55], "radius": 1.0},
    {"id": "first_aid_post", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [3.0, 0.92, 30.2], "radius": 0.9},
    {"id": "dressing_bed", "kind": "pickup", "item": "med_small", "count": 1, "pos": [17.7, 0.48, 16.5], "radius": 0.9},
    {"id": "register", "kind": "examine", "pos": [3.4, 1.0, 27.0], "radius": 1.2,
     "text": "The register of everyone who slept here. Four hundred names. The last page is all one word, written over and over: WATER."},
    {"id": "organ", "kind": "examine", "pos": [10.0, 1.0, 4.4], "radius": 1.8,
     "text": "The great organ. Someone's left the bellows running; it breathes, softly, without a note."},
    {"id": "beds", "kind": "examine", "pos": [10.0, 1.0, 20.0], "radius": 1.6,
     "text": "Most of the beds are empty, the blankets thrown back. Some aren't empty. Don't lift the blankets."}]
K["enemies"] = [{"id": "in_het_schip", "kind": "verdronkene", "pos": [10.0, 0.0, 14.0], "yaw": 180},
                {"id": "in_de_zijbeuk", "kind": "verdronkene", "pos": [17.6, 0.0, 6.0], "yaw": 160}]
write(K)

# ── The department store's ground floor: perfume, handbags, the escalators up ─────────────────
WO = [DO[0] + STORE["x0"], DO[1] - T - 20.0]
Ww = STORE["x1"] - STORE["x0"]
uw = sc - STORE["x0"]
Wh = shop_room("warenhuis", "Warenhuis de Zwerm", WO, (Ww, 20.0), 5.5,
               "the department store's ground floor: glass counters of perfume and make-up under the chandeliers, handbags on "
               "the walls, the escalators up, stopped; at the back the door to the security office.",
               {"floor": {"ph": "marble_01", "tint": [0.95, 0.93, 0.9], "rough": 0.15}, "wall": {"color": [0.9, 0.88, 0.84], "rough": 0.5},
                "ceiling": {"color": [0.92, 0.9, 0.86], "rough": 0.6}, "skirting": {"color": [0.2, 0.18, 0.16], "rough": 0.3}, "skirting_height": 0.12},
               exposure=0.9)
Wh["walls"] = {"south": {"facade": True, "openings": [glass_door(uw, sw, sh)]},
               "north": {"openings": [{"kind": "door", "center": 20.5, "width": 0.9, "height": 2.1, "hinge": "left"}]}}
wp = []
for x in (4.0, 9.0, 14.0, 19.0):   # the cosmetics counters, a grid of glass
    for z in (12.0, 7.0):
        wp.append({"type": "display_case", "pos": [x, 0.0, z], "yaw": 0, "size": [2.8, 1.05, 0.7], "palette": "pharmacy", "empty": 0.4,
                   "seed": int(x * 10 + z)})
for z in (2.0, 10.0, 18.0):   # handbags and shoes up the west wall
    wp.append({"type": "shelving", "pos": [0.3, 0.0, z], "yaw": 90, "size": [5.5, 2.4, 0.45], "palette": "souvenir", "empty": 0.35, "seed": int(z), "fallen": 3})
wp += [
    {"type": "escalator", "pos": [Ww - 2.6, 5.5, 4.0], "yaw": 180, "size": [1.4, 5.5, 8.0], "collide": False},
    {"type": "escalator", "pos": [Ww - 4.4, 5.5, 4.0], "yaw": 180, "size": [1.4, 5.5, 8.0], "collide": False},
    {"type": "collider", "pos": [Ww - 3.5, 0.0, 8.0], "size": [3.8, 2.0, 8.0]},   # (they run up from z 12 to the ceiling at z 4)
    {"type": "wall_sign", "pos": [Ww / 2, 4.3, 0.05], "size": [5.0, 0.6, 0.03], "text": "PARFUMERIE · COSMETICA", "color": [1.0, 0.85, 0.6], "glow": 2.0, "collide": False},
    {"type": "model", "model": "ph:Chandelier_03", "pos": [7.0, 4.2, 9.5], "yaw": 0, "fit": [1.4, 1.0, 1.4], "collide": False},
    {"type": "model", "model": "ph:Chandelier_03", "pos": [15.0, 4.2, 9.5], "yaw": 0, "fit": [1.4, 1.0, 1.4], "collide": False},
    {"type": "luggage", "pos": [uw, 0.0, 17.0], "size": [3.0, 0.0, 2.6], "seed": 61, "cases": 2, "bags": 3, "umbrella": True, "collide": False},
    {"type": "leaflets", "pos": [Ww / 2, 0.0, 10.0], "size": [Ww - 2, 0.0, 18.0], "seed": 62, "count": 30, "collide": False}]
Wh["props"] = wp
Wh["lights"] = [{"kind": "area", "pos": [7.0, 5.4, 9.5], "look_at": [7.0, 0.0, 9.5], "size": 3.0, "color": [1.0, 0.92, 0.82], "blender_power": 220, "godot_energy": 0.6, "range": 9.0},
                {"kind": "area", "pos": [16.0, 5.4, 9.5], "look_at": [16.0, 0.0, 9.5], "size": 3.0, "color": [1.0, 0.92, 0.82], "blender_power": 180, "godot_energy": 0.5, "range": 9.0}]
Wh["shots"] = [
    {"id": "a", "pos": [1.0, 3.6, 19.2], "look_at": [Ww - 4.0, 1.0, 3.0], "fov": 64, "zone": {"min": [0.0, 10.0], "max": [Ww, 20.0]}, "priority": 1},
    {"id": "b", "pos": [Ww - 1.0, 3.6, 1.0], "look_at": [3.0, 1.0, 17.0], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [Ww, 10.0]}, "priority": 1}]
Wh["spawns"] = {"from_dam": {"pos": [uw, 0.0, 19.2], "yaw": 0}, "from_beveiliging": {"pos": [20.5, 0.0, 0.9], "yaw": 180}}
Wh["interactables"] = [
    {"id": "door_dam", "kind": "door", "pos": [uw, 1.0, 19.55], "radius": 1.0},
    {"id": "door_beveiliging", "kind": "door", "pos": [20.5, 1.0, 0.45], "radius": 1.0},
    {"id": "escalators", "kind": "examine", "pos": [Ww - 3.5, 1.0, 5.0], "radius": 1.6,
     "text": "The escalators up are stopped. From the floor above comes the sound of water running, a lot of it."},
    {"id": "perfume", "kind": "examine", "pos": [9.0, 1.0, 8.4], "radius": 1.2, "text": "The testers are still out. The whole floor smells of roses and canal."}]
Wh["enemies"] = [{"id": "bij_de_parfum", "kind": "verdronkene", "pos": [12.0, 0.0, 9.5], "yaw": 200}]
write(Wh)

# ── The security office: the monitors, the lockers, the cabinet ─────────────────────────────
BO = [WO[0] + 18.0, WO[1] - T - 8.0]   # behind the store's back wall (not behind a house front: its window cards would stand in it)
B = shop_room("beveiliging", "Beveiliging", BO, (5.0, 8.0), 3.0,
              "the store's security office: a wall of monitors still showing the empty floors, lockers, a desk, the guards' "
              "cabinet hanging open.",
              {"floor": {"ph": "old_linoleum_flooring_01", "tint": [0.5, 0.52, 0.55], "rough": 0.5}, "wall": {"color": [0.6, 0.62, 0.64], "rough": 0.7},
               "ceiling": {"color": [0.7, 0.7, 0.7], "rough": 0.8}, "skirting": None}, exposure=0.9)
B["walls"] = {"south": {"openings": [{"kind": "door", "center": 2.5, "width": 0.9, "height": 2.1, "hinge": "right"}]}}
B["props"] = [
    {"type": "model", "model": "ph:metal_office_desk", "pos": [2.6, 0.0, 1.0], "yaw": 0, "scale": 1.0, "size": [1.4, 0.75, 0.7]},
    {"type": "wall_sign", "pos": [1.4, 1.6, 0.05], "size": [0.9, 0.6, 0.03], "text": "CAM 1", "color": [0.5, 0.7, 1.0], "glow": 1.2, "collide": False},
    {"type": "wall_sign", "pos": [2.5, 1.6, 0.05], "size": [0.9, 0.6, 0.03], "text": "CAM 2", "color": [0.5, 0.7, 1.0], "glow": 1.2, "collide": False},
    {"type": "wall_sign", "pos": [3.6, 1.6, 0.05], "size": [0.9, 0.6, 0.03], "text": "CAM 3", "color": [0.5, 0.7, 1.0], "glow": 1.2, "collide": False},
    {"type": "wall_sign", "pos": [1.9, 2.3, 0.05], "size": [0.9, 0.6, 0.03], "text": "CAM 4", "color": [0.5, 0.7, 1.0], "glow": 1.2, "collide": False},
    {"type": "wall_sign", "pos": [3.1, 2.3, 0.05], "size": [0.9, 0.6, 0.03], "text": "GEEN SIGNAAL", "color": [1.0, 0.2, 0.15], "glow": 1.5, "collide": False},
    {"type": "lockers", "pos": [4.75, 0.0, 5.0], "yaw": -90, "size": [2.8, 1.9, 0.5], "seed": 9, "open": 0.4},
    {"type": "model", "model": "ph:plastic_monobloc_chair_01", "pos": [2.4, 0.0, 1.9], "yaw": 160, "scale": 1.0, "collide": False},
    {"type": "strip_light", "pos": [2.5, 3.0, 4.0], "size": [2.5, 0.1, 0.2], "yaw": 90, "collide": False}]
B["lights"] = [{"kind": "area", "pos": [2.5, 2.95, 4.0], "look_at": [2.5, 0.0, 4.0], "size": 1.2, "color": [0.92, 0.96, 1.0], "blender_power": 160, "godot_energy": 0.5, "range": 5.0},
               {"kind": "point", "pos": [3.2, 1.3, 1.2], "color": [0.6, 0.75, 1.0], "blender_power": 25, "godot_energy": 0.3, "range": 3.0, "radius": 0.3}]   # the monitors' glow
B["shots"] = [{"id": "a", "pos": [0.5, 2.5, 7.5], "look_at": [3.6, 1.0, 0.8], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [5.0, 8.0]}, "priority": 1}]
B["spawns"] = {"from_warenhuis": {"pos": [2.5, 0.0, 7.2], "yaw": 0}}
B["interactables"] = [
    {"id": "door_warenhuis", "kind": "door", "pos": [2.5, 1.0, 7.55], "radius": 1.0},
    {"id": "cabinet", "kind": "examine", "pos": [4.2, 1.0, 5.0], "radius": 1.2,
     "text": "The guards' cabinet, hanging open. Their batons are gone. In the back, behind the radios, a box they missed."},
    {"id": "ammo_cabinet", "kind": "pickup", "item": "handgun_ammo", "count": 15, "pos": [4.4, 1.0, 5.6], "radius": 0.9},
    {"id": "monitors", "kind": "examine", "pos": [2.5, 1.0, 1.2], "radius": 1.2,
     "text": "Camera 3: the second floor. The floor is under water. Something is walking through it, slowly, toward the stairs."}]
B["enemies"] = []
write(B)

# ── Rokin noord: the checkpoint opened onto the Dam ───────────────────────────────────────
N = json.load(open(R + "rokin_noord.json"))
N["outdoor"]["facades"] = [f for f in N["outdoor"]["facades"] if not f.get("classic")]   # (the stand-in palace: the Dam is real now)
N["outdoor"]["ground"] = [g for g in N["outdoor"]["ground"] if g.get("name") != "dam_ahead"]
N["outdoor"]["rows"] = [r for r in N["outdoor"]["rows"] if r.get("line") != 50.0]
N["walls"]["north"] = {"openings": [{"kind": "passage", "center": 13.0, "width": 26.0, "height": 10.0}]}
N["props"] = [p for p in N["props"] if not (p.get("model") == "ph:concrete_road_barrier" and abs(p["pos"][0] - 13.0) < 0.5)]   # a gap in the checkpoint
N["props"].append({"type": "model", "model": "ph:concrete_road_barrier", "pos": [6.8, 0.0, 3.0], "yaw": -30, "fit": [3.0, 1.0, 0.7]})   # shoved aside
N["interactables"] = [i for i in N["interactables"] if i["id"] not in ("to_dam",)]
N["interactables"].append({"id": "to_dam", "kind": "door", "pos": [12.6, 1.0, 0.2], "radius": 1.6, "target_room": "dam", "target_spawn": "from_rokin"})
for i in N["interactables"]:
    if i["id"] == "checkpoint":
        i["text"] = "An army checkpoint across the end of Rokin, abandoned: the barriers still up, one shoved aside. The Dam is beyond, all lit up."
N["spawns"]["from_dam"] = {"pos": [12.6, 0.0, 2.0], "yaw": 180}
json.dump(N, open(R + "rokin_noord.json", "w"), indent=2, ensure_ascii=True)
open(R + "rokin_noord.json", "a").write("\n")
print("doors: kerk", KERK_DOOR, "store", round(sc, 3), round(sw, 3), round(sh, 3))
