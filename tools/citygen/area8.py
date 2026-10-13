# damned_waters/tools/citygen/area8.py
# Generates area 8, the end of the route: stationsplein (storey 16), the square before Centraal with the
# station's middle arch open; centraal_hal, the hall behind it (shops shuttered, the boards, the gate line,
# the escalators down to line 52); metro_centraal (storey 17), the platform under the station, the last
# train north waiting with its doors open; station_noord (storey 18), across the IJ, where the line ends.
# Dressed as the evacuation left it (docs/city_aftermath.md).
from pathlib import Path
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import street_room, shop_room, write, PAVERS, BRICKS, SUN, ROOMS, WET  # noqa: E402

T = 0.3
SO = [887.0, -519.4]                          # stationsplein: 70 x 63.6, Damrak's mouth in its south side (x 25..45)
SW, SD = 70.0, 63.6
ARCH, ARCH_W, ARCH_H = 35.0, 5.2, 8.5         # the station's middle arch, on Damrak's axis
HO = [SO[0] + ARCH - 12.0, SO[1] - T - 36.0]  # centraal_hal: 24 x 36 behind the arch
MO = [904.0, -640.0]                          # metro_centraal: 16 x 64, under the tracks
NO_ = [930.0, -720.0]                         # station_noord: 18 x 56
BLUE = {"color": [0.02, 0.05, 0.16], "rough": 0.4}
TRAIN = {"type": "tram", "yaw": 90, "size": [48.0, 3.5, 2.7], "board": "52 NOORD", "power": 380.0,
         "material": {"color": [0.8, 0.81, 0.82], "rough": 0.35, "noise": 0.08, "noise_scale": 1.5, "coat": 1.0, "grime": 0.9},
         "band": {"color": [0.62, 0.04, 0.04], "rough": 0.35}, "pantograph": False, "doors_open": "all", "inside": 0.3,
         "underframe": 0.7, "collide": False}
TRAIN_DOORS = (47.67, 29.21, 15.5)            # its open doors along z, the train's middle at z 30 (city.tram)


def face(x, z, tx, tz):
    """The yaw that turns a prop's front (+z) from (x, z) toward (tx, tz)."""
    return round(math.degrees(math.atan2(tx - x, tz - z)), 1)


def along(x0, z0, x1, z1):
    """A prop laid along local x from (x0, z0) to (x1, z1): its middle, yaw and length."""
    return [round((x0 + x1) / 2, 3), 0.0, round((z0 + z1) / 2, 3)], round(math.degrees(math.atan2(-(z1 - z0), x1 - x0)), 1), round(math.hypot(x1 - x0, z1 - z0), 3)


def barrier(x0, z0, x1, z1, seed):
    pos, yaw, n = along(x0, z0, x1, z1)
    return {"type": "crowd_barrier", "pos": pos, "yaw": yaw, "size": [n, 1.1, 0.7], "seed": seed}


def zone_shots(specs):
    return [{"id": i, "pos": p, "look_at": l, "fov": f, "zone": {"min": z0, "max": z1}, "priority": 1} for i, p, l, f, z0, z1 in specs]


# ════════════════════════════════════════════════════════════════════════════════════
# Stationsplein: the square, the checkpoint, the station's front
# ════════════════════════════════════════════════════════════════════════════════════
C.DISTRICT.update({"storey": 16, "name": "district 7: Centraal"})
S = street_room("stationsplein", "Stationsplein", SO, (SW, SD), 14.0,
                "the square before Centraal Station: the Prins Hendrikkade across its south side where Damrak runs in, "
                "the trams' terminus, buses left where they stood, bikes by the hundred, the army's checkpoint funnelling "
                "the crowd to the station's middle arch, and over it all the station's long front, floodlit.")
S["outdoor"] = {
    "window_rooms": ROOMS, "lamp_power": 420.0, "lamp_energy": 1.0,
    "ground": [{"name": "plein", "min": [-45.0, -8.0], "max": [115.0, 40.0], "y": 0.0, "material": PAVERS, "kerb": True},
               {"name": "hendrikkade", "min": [-45.0, 40.0], "max": [115.0, SD], "y": 0.0, "material": BRICKS}],
    "tracks": [{"from": [33.5, SD], "to": [33.5, 32.0], "y": 0.0}, {"from": [33.5, 32.0], "to": [24.0, 24.0], "y": 0.0},
               {"from": [24.0, 24.0], "to": [-30.0, 24.0], "y": 0.0},
               {"from": [36.5, SD], "to": [36.5, 30.0], "y": 0.0}, {"from": [36.5, 30.0], "to": [26.0, 21.0], "y": 0.0},
               {"from": [26.0, 21.0], "to": [-30.0, 21.0], "y": 0.0}],
    "rows": [{"from": -40.0, "to": 24.7, "line": SD, "facing": "north", "lit": 0.35, "shops": 0.5, "row_ends": "end"},
             {"from": 6.0, "to": 39.0, "line": -2.0, "facing": "east", "lit": 0.3, "shops": 0.4, "row_ends": "both"},
             {"from": 6.0, "to": 39.0, "line": 72.0, "facing": "west", "lit": 0.3, "shops": 0.4, "row_ends": "both"}],
    "lamps": [[6.0, 38.0], [20.0, 38.0], [50.0, 38.0], [64.0, 38.0], [6.0, 14.0], [64.0, 14.0], [22.0, 4.0], [48.0, 4.0]]}
props = [
    {"type": "station", "pos": [ARCH - 55.0, 0.0, -1.5], "yaw": 0, "size": [110.0, 18.0, 40.0], "arch_open": True,
     "encloses": ["centraal_hal"], "collide": False},
    {"type": "collider", "pos": [ARCH - 16.5, 0.0, 0.25], "size": [6.0, 1.0, 0.5]},   # the towers' feet
    {"type": "collider", "pos": [ARCH + 16.5, 0.0, 0.25], "size": [6.0, 1.0, 0.5]},
    {"type": "tram", "pos": [10.0, 0.0, 24.0], "yaw": 0, "size": [30.0, 3.4, 2.4], "board": "NIET INSTAPPEN", "power": 240.0},
    {"type": "tram_stop", "pos": [10.0, 0.0, 26.5], "yaw": 180, "size": [26.0, 0.25, 2.6], "collide": False},
    {"type": "bus", "pos": [17.0, 0.0, 51.9], "yaw": 0, "size": [12.0, 3.2, 2.6], "seed": 82},
    {"type": "bus", "pos": [55.0, 0.0, 49.9], "yaw": 180, "size": [12.0, 3.2, 2.6], "seed": 83},
    # the checkpoint: a funnel of barriers to the arch, sandbags either side of it, the army's lights on it
    barrier(22.0, 15.0, 32.6, 2.6, 801), barrier(48.0, 15.0, 37.4, 2.6, 802),
    {"type": "sandbags", "pos": [29.0, 0.0, 1.3], "size": [4.4, 0.7, 0.7], "seed": 803},
    {"type": "sandbags", "pos": [41.0, 0.0, 1.3], "size": [4.4, 0.7, 0.7], "seed": 804},
    {"type": "vehicle", "pos": [15.0, 0.0, 10.0], "yaw": 75, "size": [7.0, 3.0, 2.4], "livery": "army", "van": True, "door_open": "left"},
    {"type": "light_tower", "pos": [52.0, 0.0, 10.0], "yaw": face(52.0, 10.0, ARCH, 0.0), "size": [2.2, 8.5, 1.4], "aim": [0.0, 0.0, 19.0]},
    {"type": "light_tower", "pos": [18.0, 0.0, 34.0], "yaw": face(18.0, 34.0, ARCH, 10.0), "size": [2.2, 8.5, 1.4], "aim": [0.0, 0.0, 28.0]},
    {"type": "aid_post", "pos": [60.0, 0.0, 27.0], "yaw": -90, "size": [6.0, 3.4, 6.0], "military": True, "covered": 2, "stretchers": 2, "seed": 805},
    {"type": "trestle_table", "pos": [26.0, 0.0, 17.0], "yaw": 20, "size": [2.0, 0.76, 0.8], "laptops": 1, "seed": 806},
    {"type": "evac_board", "pos": [35.0, 0.0, 18.0], "yaw": 0, "size": [2.0, 1.9, 0.6], "text": "METRO 52 · NOORD", "to": "LAATSTE TREIN 00:30", "arrow": "up"},
    {"type": "evac_board", "pos": [44.0, 0.0, 44.0], "yaw": 20, "size": [1.8, 1.9, 0.6], "text": "TREINEN", "to": "RIJDEN NIET", "arrow": "up"},
    {"type": "model", "model": "ph:portable_searchlight", "pos": [41.5, 0.7, 1.2], "yaw": 200, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:Megaphone_01", "pos": [33.4, 0.0, 6.8], "yaw": 70, "tip": 90, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:wheelchair_01", "pos": [39.0, 0.0, 9.5], "yaw": 140, "scale": 1.0, "size": [0.7, 0.9, 1.0]},
    {"type": "model", "model": "ph:portable_generator", "pos": [54.0, 0.0, 12.5], "yaw": 30, "scale": 1.0, "size": [0.7, 0.6, 0.5]},
    {"type": "luggage", "pos": [30.0, 0.0, 9.0], "size": [5.0, 0.0, 6.0], "seed": 807, "cases": 6, "bags": 8, "pushchair": True, "collide": False},
    {"type": "luggage", "pos": [40.0, 0.0, 26.0], "size": [6.0, 0.0, 5.0], "seed": 808, "cases": 4, "bags": 5, "collide": False},
    {"type": "luggage", "pos": [28.0, 0.0, 44.0], "size": [5.0, 0.0, 4.0], "seed": 809, "cases": 3, "bags": 4, "chair": True, "collide": False},
    {"type": "luggage", "pos": [48.0, 0.0, 56.0], "size": [4.0, 0.0, 4.0], "seed": 810, "cases": 2, "bags": 3, "collide": False},
    {"type": "leaflets", "pos": [35.0, 0.0, 30.0], "size": [60.0, 0.0, 56.0], "seed": 811, "count": 520, "collide": False}]
for k in range(14):   # the racks of bikes along the west side, knocked down in a heap where the crowd went through
    z = 30.0 + 0.7 * k
    props.append({"type": "bike", "pos": [3.0 + (0.4 if k % 3 == 1 else 0.0), 0.0, round(z, 2)], "yaw": 90 + (8 if k % 2 else -6),
                  **({"roll": 84 if k % 2 else -82} if k in (3, 4, 9, 10, 11) else {}), "size": [1.8, 1.1, 0.5], "seed": 820 + k, "collide": False})
props.append({"type": "collider", "pos": [3.2, 0.0, 34.5], "size": [2.4, 1.0, 10.4]})
S["props"] = props
S["walls"] = {"south": {"openings": [{"kind": "passage", "center": ARCH, "width": 20.0, "height": 12.0}]},
              "north": {"openings": [{"kind": "passage", "center": ARCH, "width": ARCH_W, "height": ARCH_H}]}}
S["lights"] = [SUN]
S["shots"] = zone_shots([
    ("a", [35.0, 4.4, 63.2], [35.0, 7.0, 0.0], 58, [20.0, 40.0], [50.0, SD]),       # from Damrak: the station over the square
    ("aw", [36.0, 4.4, 62.0], [6.0, 1.5, 44.0], 60, [0.0, 40.0], [20.0, SD]),
    ("ae", [34.0, 4.4, 62.0], [64.0, 1.5, 44.0], 60, [50.0, 40.0], [SW, SD]),
    ("bw", [44.0, 4.6, 44.0], [14.0, 3.0, 14.0], 60, [0.0, 16.0], [35.0, 40.0]),    # the tram, the bikes, the truck
    ("be", [26.0, 4.6, 44.0], [56.0, 3.0, 14.0], 60, [35.0, 16.0], [SW, 40.0]),     # the tent, the lights
    ("c", [50.0, 3.4, 24.0], [33.0, 3.5, 0.0], 60, [22.0, 0.0], [48.0, 16.0]),      # the funnel and the arch
    ("dw", [30.0, 3.6, 22.0], [8.0, 2.0, 4.0], 60, [0.0, 0.0], [22.0, 16.0]),
    ("de", [40.0, 3.6, 22.0], [62.0, 2.0, 4.0], 60, [48.0, 0.0], [SW, 16.0])])
S["spawns"] = {"from_damrak": {"pos": [ARCH, 0.0, SD - 1.8], "yaw": 0}, "from_hal": {"pos": [ARCH, 0.0, 1.6], "yaw": 180}}
S["interactables"] = [
    {"id": "to_damrak", "kind": "door", "pos": [ARCH, 1.0, SD - 0.2], "radius": 1.6, "target_room": "damrak_noord", "target_spawn": "from_stationsplein"},
    {"id": "station", "kind": "examine", "pos": [ARCH, 1.0, 3.2], "radius": 2.0,
     "text": "Centraal. The army chained the side doors and left the middle arch open. The lights are still on inside."},
    {"id": "notice", "kind": "note", "pos": [26.0, 0.8, 17.6], "radius": 1.2, "title": "Notice, taped to the table",
     "text": "MUNICIPALITY OF AMSTERDAM - EVACUATION\n\nNo trains will run from Centraal. Metro 52 runs north to Noord until 00:30, then the "
             "line is closed.\n\nTake only what you can carry. Do not go back for anyone. Do not go near the water."},
    {"id": "shells_truck", "kind": "pickup", "item": "shotgun_shells", "count": 6, "pos": [17.6, 0.0, 12.6], "radius": 0.9},
    {"id": "first_aid_tent", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [57.6, 0.0, 27.0], "radius": 0.9},
    {"id": "rounds_bus", "kind": "pickup", "item": "handgun_ammo", "count": 10, "pos": [24.0, 0.0, 52.6], "radius": 0.9}]
S["enemies"] = [{"id": "bij_de_tram", "kind": "verdronkene", "pos": [12.0, 0.0, 29.2], "yaw": 160},
                {"id": "op_het_plein", "kind": "verdronkene", "pos": [45.0, 0.0, 32.0], "yaw": 200},
                {"id": "bij_de_poort", "kind": "verdronkene", "pos": [42.0, 0.0, 6.0], "yaw": 220, "lying": True}]
write(S)

# ════════════════════════════════════════════════════════════════════════════════════
# The station's hall: the shops, the boards, the gate line, the escalators down to line 52
# ════════════════════════════════════════════════════════════════════════════════════
H = shop_room("centraal_hal", "Centraal Station · Hal", HO, (24.0, 36.0), 11.0,
              "the front hall of Centraal behind the middle arch: brick and sandstone, a dark timber ceiling, lanterns; the "
              "shops along the walls shuttered, the boards still lit with trains that won't run, the gate line shut on red "
              "but for the gap the army cut in it, and beyond it the escalators down to line 52.",
              {"floor": {"ph": "terrazzo_tiles", "tint": [0.62, 0.6, 0.57], "rough": 0.3},
               "wall": {"ph": "red_bricks_04", "tint": [0.75, 0.52, 0.42], "scale": 1.0},
               "ceiling": {"ph": "dark_wood", "tint": [0.3, 0.22, 0.16], "scale": 0.5},
               "wainscot": {"ph": "large_sandstone_blocks", "tint": [0.86, 0.8, 0.68], "scale": 0.8}, "wainscot_height": 1.4,
               "pit": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "skirting": None}, exposure=1.0)
H["walls"] = {"south": {"openings": [{"kind": "passage", "center": 12.0, "width": ARCH_W, "height": ARCH_H}]},
              "north": {"openings": [{"kind": "passage", "center": 12.0, "width": 4.4, "height": 4.0}]}}   # the escalators down, beyond it
units = [("west", 3.4, "KRANTEN · TIJDSCHRIFTEN", 0.0), ("west", 8.2, "BROODJES · KOFFIE", 0.35), ("west", 13.0, "BLOEMEN", 0.0),
         ("east", 3.4, "STROOPWAFELS", 0.0), ("east", 8.2, "BOEKHANDEL", 0.0), ("east", 13.0, "DROGISTERIJ", 0.6)]
props = []
for side, z, name, up in units:
    props.append({"type": "shop_unit", "pos": [0.5 if side == "west" else 23.5, 0.0, z], "yaw": 90 if side == "west" else -90,
                  "size": [4.4, 3.4, 1.0], "name": name, "open": up})
props += [
    {"type": "shop_unit", "pos": [4.0, 0.0, 0.5], "yaw": 0, "size": [5.0, 4.2, 1.0], "name": "PERRONS 1 – 7", "sign": [1.0, 1.0, 1.0]},
    {"type": "shop_unit", "pos": [20.0, 0.0, 0.5], "yaw": 0, "size": [5.0, 4.2, 1.0], "name": "PERRONS 8 – 15", "sign": [1.0, 1.0, 1.0]},
    {"type": "broken_glass", "pos": [21.6, 0.0, 13.0], "size": [1.6, 0.0, 3.2], "seed": 831, "collide": False},
    {"type": "escalator", "pos": [11.2, 0.0, -0.3], "yaw": 0, "size": [1.4, 5.5, 9.0], "collide": False},
    {"type": "escalator", "pos": [12.8, 0.0, -0.3], "yaw": 0, "size": [1.4, 5.5, 9.0], "collide": False},
    {"type": "block", "pos": [9.65, -6.5, -5.0], "size": [0.3, 11.5, 9.4], "material": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "collide": False},
    {"type": "block", "pos": [14.35, -6.5, -5.0], "size": [0.3, 11.5, 9.4], "material": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "collide": False},
    {"type": "block", "pos": [12.0, 4.0, -5.0], "size": [5.0, 0.3, 9.4], "material": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "collide": False},
    {"type": "block", "pos": [12.0, -6.5, -9.85], "size": [5.0, 10.8, 0.3], "material": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "collide": False},
    {"type": "departure_board", "pos": [12.0, 4.4, 0.6], "yaw": 0, "size": [4.0, 1.0, 0.2], "hang": 5.6, "title": "METRO 52",
     "rows": [["00:30", "NOORD", "1", "STAAT KLAAR"]], "collide": False},
    {"type": "departure_board", "pos": [12.0, 5.6, 21.5], "yaw": 0, "size": [7.0, 1.9, 0.3], "hang": 3.5, "both": True, "collide": False,
     "rows": [["23:31", "SCHIPHOL", "4", "RIJDT NIET"], ["23:38", "UTRECHT CENTRAAL", "7", "RIJDT NIET"], ["23:44", "ZANDVOORT", "2", "RIJDT NIET"],
              ["23:52", "HAARLEM", "1", "RIJDT NIET"], ["00:02", "ALKMAAR", "8", "RIJDT NIET"], ["00:13", "ROTTERDAM", "5", "RIJDT NIET"]]},
    {"type": "ticket_gates", "pos": [5.15, 0.0, 18.0], "yaw": 0, "size": [9.7, 1.1, 0.3]},
    {"type": "ticket_gates", "pos": [18.85, 0.0, 18.0], "yaw": 0, "size": [9.7, 1.1, 0.3]},
    {"type": "evac_board", "pos": [12.0, 0.0, 19.4], "yaw": 0, "size": [1.8, 1.9, 0.6], "text": "DOORGANG", "to": "METRO 52", "arrow": "up", "collide": False},
    {"type": "stanchions", "pos": [10.0, 0.0, 26.0], "yaw": 90, "size": [8.0, 0.95, 0.1]},
    {"type": "stanchions", "pos": [14.0, 0.0, 26.0], "yaw": 90, "size": [8.0, 0.95, 0.1]},
    {"type": "lockers", "pos": [0.35, 0.0, 29.0], "yaw": 90, "size": [8.0, 2.0, 0.6], "seed": 832, "open": 0.35},
    {"type": "trestle_table", "pos": [6.0, 0.0, 30.5], "yaw": 0, "size": [2.4, 0.76, 0.8], "laptops": 1, "seed": 833},
    {"type": "model", "model": "ph:clipboard", "pos": [6.6, 0.78, 30.4], "yaw": 15, "scale": 1.0, "collide": False},
    {"type": "luggage", "pos": [4.0, 0.0, 21.5], "size": [3.0, 0.0, 2.5], "seed": 834, "cases": 3, "bags": 3, "collide": False},
    {"type": "luggage", "pos": [20.0, 0.0, 22.0], "size": [3.0, 0.0, 2.5], "seed": 835, "cases": 2, "bags": 4, "pushchair": True, "collide": False},
    {"type": "luggage", "pos": [6.0, 0.0, 10.0], "size": [2.4, 0.0, 2.4], "seed": 836, "cases": 2, "bags": 2, "collide": False},
    {"type": "leaflets", "pos": [12.0, 0.0, 28.0], "size": [10.0, 0.0, 12.0], "seed": 837, "count": 60, "collide": False},
    {"type": "leaflets", "pos": [12.0, 0.0, 15.0], "size": [14.0, 0.0, 6.0], "seed": 838, "count": 30, "collide": False},
    {"type": "model", "model": "ph:wall_clock", "pos": [12.0, 7.4, 0.04], "yaw": 0, "scale": 3.0, "collide": False},
    {"type": "model", "model": "ph:lantern_chandelier_01", "pos": [12.0, 9.0, 8.0], "yaw": 0, "fit": [1.2, 2.0, 1.2], "collide": False},
    {"type": "model", "model": "ph:lantern_chandelier_01", "pos": [12.0, 9.0, 28.5], "yaw": 0, "fit": [1.2, 2.0, 1.2], "collide": False}]
for k, x in enumerate((16.6, 17.6, 18.6, 19.6, 20.6)):   # camp beds: they waited the night here
    props.append({"type": "camp_bed", "pos": [x, 0.0, 32.6], "yaw": 0, "size": [0.7, 0.42, 1.9], "occupied": k == 3, "seed": 840 + k})
for z in (25.2, 26.2, 27.2, 28.2):
    props.append({"type": "ticket_machine", "pos": [23.7, 0.0, z], "yaw": -90, "size": [0.8, 1.7, 0.5]})
H["props"] = props
H["lights"] = [
    {"kind": "area", "pos": [12.0, 10.8, 8.0], "look_at": [12.0, 0.0, 8.0], "size": 3.0, "color": [1.0, 0.86, 0.68], "blender_power": 320, "godot_energy": 0.6, "range": 12.0},
    {"kind": "area", "pos": [12.0, 10.8, 20.0], "look_at": [12.0, 0.0, 20.0], "size": 3.0, "color": [1.0, 0.86, 0.68], "blender_power": 300, "godot_energy": 0.6, "range": 12.0, "flicker": True},
    {"kind": "area", "pos": [12.0, 10.8, 30.0], "look_at": [12.0, 0.0, 30.0], "size": 3.0, "color": [1.0, 0.86, 0.68], "blender_power": 260, "godot_energy": 0.5, "range": 12.0},
    {"kind": "point", "pos": [12.0, -4.4, -8.6], "color": [0.75, 0.85, 1.0], "blender_power": 80, "godot_energy": 0.2, "range": 6.0, "radius": 0.3}]
H["shots"] = [
    {"id": "a", "pos": [21.8, 5.2, 22.5], "look_at": [7.0, 1.2, 34.5], "fov": 64, "zone": {"min": [0.0, 24.0], "max": [24.0, 36.0]}, "priority": 1},
    {"id": "b", "pos": [2.2, 4.6, 35.0], "look_at": [13.5, 0.8, 12.0], "fov": 62, "zone": {"min": [0.0, 12.0], "max": [24.0, 24.0]}, "priority": 1},
    {"id": "c", "pos": [20.5, 4.2, 14.5], "look_at": [9.0, 0.6, 0.0], "fov": 64, "zone": {"min": [0.0, 0.0], "max": [24.0, 12.0]}, "priority": 1}]
H["spawns"] = {"from_square": {"pos": [12.0, 0.0, 34.6], "yaw": 0}, "from_metro": {"pos": [12.0, 0.0, 1.4], "yaw": 180}}
H["interactables"] = [
    {"id": "escalator_down", "kind": "door", "pos": [12.0, 1.0, 0.2], "radius": 1.6, "target_room": "metro_centraal", "target_spawn": "from_hal"},
    {"id": "board", "kind": "examine", "pos": [8.4, 1.0, 19.4], "radius": 1.2,
     "text": "Every train on the board: RIJDT NIET. Over the escalators one line is still lit. METRO 52, NOORD, 00:30. STAAT KLAAR."},
    {"id": "perrons", "kind": "examine", "pos": [4.0, 1.0, 1.6], "radius": 1.2,
     "text": "The way through to the platforms, shuttered and padlocked. Sprayed across it: TREINEN RIJDEN NIET."},
    {"id": "registration", "kind": "note", "pos": [6.0, 0.8, 31.2], "radius": 1.0, "title": "The registration list",
     "text": "Names on a clipboard, sheet after sheet, a time by each: 23:10, 23:11, 23:11, 23:14...\n\nThe last sheet stops at 00:19, halfway down."},
    {"id": "rounds_locker", "kind": "pickup", "item": "handgun_ammo", "count": 12, "pos": [1.0, 0.9, 27.4], "radius": 0.9},
    {"id": "shells_hall", "kind": "pickup", "item": "shotgun_shells", "count": 4, "pos": [20.6, 0.0, 21.0], "radius": 0.9},
    {"id": "first_aid_desk", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [5.2, 0.8, 30.5], "radius": 0.9}]
H["enemies"] = [{"id": "bij_de_kiosk", "kind": "verdronkene", "pos": [4.5, 0.0, 12.5], "yaw": 120},
                {"id": "bij_de_poortjes", "kind": "verdronkene", "pos": [17.0, 0.0, 15.6], "yaw": 200},
                {"id": "op_het_veldbed", "kind": "verdronkene", "pos": [15.2, 0.0, 30.4], "yaw": 90, "lying": True}]
write(H)

# ════════════════════════════════════════════════════════════════════════════════════
# Line 52's platform under the station: the last train north
# ════════════════════════════════════════════════════════════════════════════════════
C.DISTRICT.update({"storey": 17, "name": "district 7: Centraal"})
Mp = shop_room("metro_centraal", "Metro 52 · Centraal", MO, (16.0, 64.0), 12.5,
               "line 52's platform deep under the station: an island between two tracks under a long concrete vault, white "
               "tiles on the walls. On one track the last train north stands with every door open, its lights on, humming; "
               "the other track is under black water, still rising.",
               {"floor": {"ph": "granite_tile", "tint": [0.5, 0.5, 0.5], "rough": 0.35},
                "wall": {"ph": "rectangular_facade_tiles", "tint": [0.78, 0.8, 0.8], "scale": 1.0},
                "ceiling": {"color": [0.3, 0.3, 0.3], "rough": 0.8}, "pit": {"color": [0.16, 0.16, 0.16], "rough": 0.8}, "skirting": None},
               exposure=1.0)
Mp["vault"] = {"spring": 4.2, "axis": "z", "material": {"color": [0.36, 0.36, 0.35], "rough": 0.85, "noise": 0.3, "noise_scale": 2.0}}
Mp["floor_holes"] = [[0.0, 0.0, 3.6, 64.0], [12.4, 0.0, 16.0, 64.0]]
mouths = [{"kind": "passage", "center": 1.8, "width": 3.4, "height": 4.0}, {"kind": "passage", "center": 14.2, "width": 3.4, "height": 4.0}]
Mp["walls"] = {"north": {"openings": [dict(m) for m in mouths]},
               "south": {"openings": [dict(m) for m in mouths] + [{"kind": "passage", "center": 8.0, "width": 3.6, "height": 4.0}]}}
props = [
    {"type": "trackbed", "pos": [1.8, -1.1, 32.0], "yaw": -90, "size": [64.0, 0.5, 3.4], "collide": False},
    {"type": "trackbed", "pos": [14.2, -1.1, 32.0], "yaw": 90, "size": [64.0, 0.5, 3.4], "water": 0.55, "collide": False},
    dict(TRAIN, pos=[1.8, -0.38, 30.0]),
    {"type": "platform_edge", "pos": [4.1, 0.0, 32.0], "yaw": -90, "size": [64.0, 0.01, 1.0], "collide": False},
    {"type": "platform_edge", "pos": [11.9, 0.0, 32.0], "yaw": 90, "size": [64.0, 0.01, 1.0], "collide": False},
    {"type": "collider", "pos": [1.8, 0.0, 32.0], "size": [3.6, 1.0, 64.0]},
    {"type": "collider", "pos": [14.2, 0.0, 32.0], "size": [3.6, 1.0, 64.0]},
    {"type": "escalator", "pos": [7.2, 5.2, 72.8], "yaw": 0, "size": [1.4, 5.2, 8.5], "collide": False},
    {"type": "escalator", "pos": [8.8, 5.2, 72.8], "yaw": 0, "size": [1.4, 5.2, 8.5], "collide": False},
    {"type": "block", "pos": [6.05, 0.0, 68.6], "size": [0.3, 9.0, 8.6], "material": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "collide": False},
    {"type": "block", "pos": [9.95, 0.0, 68.6], "size": [0.3, 9.0, 8.6], "material": {"color": [0.2, 0.2, 0.2], "rough": 0.7}, "collide": False},
    {"type": "departure_board", "pos": [8.0, 2.6, 40.0], "yaw": 0, "size": [3.0, 0.7, 0.18], "hang": 8.8, "both": True, "title": "METRO 52",
     "rows": [["00:30", "NOORD", "1", "STAAT KLAAR"]], "collide": False},
    {"type": "evac_board", "pos": [10.9, 0.0, 52.0], "yaw": -20, "size": [1.8, 1.9, 0.6], "text": "LAATSTE TREIN", "to": "NOORD", "arrow": "left"},
    {"type": "model", "model": "ph:wall_clock", "pos": [8.0, 8.6, 63.96], "yaw": 180, "scale": 2.5, "collide": False},
    {"type": "luggage", "pos": [9.6, 0.0, 34.0], "size": [3.0, 0.0, 3.0], "seed": 851, "cases": 3, "bags": 3, "collide": False},
    {"type": "luggage", "pos": [6.0, 0.0, 49.0], "size": [2.4, 0.0, 2.4], "seed": 852, "cases": 2, "bags": 1, "pushchair": True, "collide": False},
    {"type": "leaflets", "pos": [8.0, 0.0, 32.0], "size": [8.0, 0.0, 60.0], "seed": 853, "count": 120, "collide": False},
    {"type": "model", "model": "ph:wheelchair_01", "pos": [10.6, 0.0, 22.0], "yaw": 30, "scale": 1.0, "size": [0.7, 0.9, 1.0]},
    {"type": "model", "model": "ph:street_rat", "pos": [4.7, 0.0, 19.0], "yaw": 80, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:street_rat", "pos": [5.1, 0.0, 19.7], "yaw": 200, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:street_rat", "pos": [11.3, 0.0, 44.0], "yaw": 10, "scale": 1.0, "collide": False}]
for z in (14.0, 32.0, 50.0):   # the station's name along the far wall, over the flooded track
    props.append({"type": "wall_sign", "pos": [15.96, 2.4, z], "yaw": -90, "size": [4.0, 0.5, 0.03], "text": "CENTRAAL STATION",
                  "panel": BLUE, "color": [1.0, 1.0, 1.0], "glow": 2.0, "collide": False})
for z in (18.0, 30.0, 46.0):
    props.append({"type": "bench", "pos": [8.0, 0.0, z], "yaw": 90, "size": [1.8, 0.85, 0.5]})
for x in (0.12, 15.88):   # the strip lights along the vault's foot
    for z in (10.0, 26.0, 42.0, 56.0):
        props.append({"type": "strip_light", "pos": [x, 4.0, z], "yaw": 90, "size": [6.0, 0.1, 0.2], "collide": False})
Mp["props"] = props
Mp["lights"] = [
    {"kind": "area", "pos": [8.0, 4.4, 12.0], "look_at": [8.0, 0.0, 12.0], "size": 2.5, "color": [0.85, 0.92, 1.0], "blender_power": 160, "godot_energy": 0.5, "range": 9.0},
    {"kind": "area", "pos": [8.0, 4.4, 30.0], "look_at": [8.0, 0.0, 30.0], "size": 2.5, "color": [0.85, 0.92, 1.0], "blender_power": 160, "godot_energy": 0.5, "range": 9.0, "flicker": True},
    {"kind": "area", "pos": [8.0, 4.4, 48.0], "look_at": [8.0, 0.0, 48.0], "size": 2.5, "color": [0.85, 0.92, 1.0], "blender_power": 160, "godot_energy": 0.5, "range": 9.0}]
Mp["shots"] = [
    {"id": "a", "pos": [4.2, 3.4, 44.5], "look_at": [10.5, 0.8, 63.5], "fov": 62, "zone": {"min": [0.0, 46.0], "max": [16.0, 64.0]}, "priority": 1},
    {"id": "b", "pos": [11.8, 3.6, 62.0], "look_at": [4.0, 1.2, 30.0], "fov": 58, "zone": {"min": [0.0, 24.0], "max": [16.0, 46.0]}, "priority": 1},
    {"id": "c", "pos": [11.8, 3.0, 28.0], "look_at": [5.0, 1.0, 0.0], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [16.0, 24.0]}, "priority": 1}]
Mp["spawns"] = {"from_hal": {"pos": [8.0, 0.0, 62.6], "yaw": 0}}
Mp["interactables"] = [
    {"id": "escalator_up", "kind": "door", "pos": [8.0, 1.0, 63.8], "radius": 1.6, "target_room": "centraal_hal", "target_spawn": "from_metro"},
    {"id": "train", "kind": "examine", "pos": [4.2, 1.0, 38.0], "radius": 1.2,
     "text": "Line 52, NOORD on its boards, every door open, the lights on, the motors humming. The driver's cab is empty. "
             "On the seat a radio hisses: '...last run north. Anyone on the platform, get on.'"}]
for k, z in enumerate(TRAIN_DOORS):
    Mp["interactables"].append({"id": "board_train_%d" % (k + 1), "kind": "door", "board": True, "pos": [3.9, 1.0, z], "radius": 1.1,
                                "target_room": "station_noord", "target_spawn": "from_metro"})   # (Interact at the open door: no gap to walk through)
Mp["interactables"] += [
    {"id": "shells_platform", "kind": "pickup", "item": "shotgun_shells", "count": 6, "pos": [9.6, 0.0, 36.4], "radius": 0.9},
    {"id": "med_platform", "kind": "pickup", "item": "med_small", "count": 1, "pos": [6.4, 0.0, 50.6], "radius": 0.9}]
Mp["enemies"] = [{"id": "op_het_perron", "kind": "verdronkene", "pos": [9.0, 0.0, 26.0], "yaw": 170},
                 {"id": "bij_de_bank", "kind": "verdronkene", "pos": [10.5, 0.0, 11.0], "yaw": 200},
                 {"id": "uit_het_water", "kind": "verdronkene", "pos": [11.6, 0.0, 36.0], "yaw": 250, "emerge": True}]
write(Mp)

# ════════════════════════════════════════════════════════════════════════════════════
# Station Noord: the end of the line
# ════════════════════════════════════════════════════════════════════════════════════
C.DISTRICT.update({"storey": 18, "name": "district 8: Noord"})
L = 56.0
Nd = street_room("station_noord", "Station Noord", NO_, (18.0, L), 10.0,
                 "the end of line 52, across the IJ: an island platform under a long canopy between the tracks, the train he "
                 "came on standing at it; past the gate line the bus station, where the army set up to receive the city: "
                 "floodlights, tents, trucks in rows. Nobody is there.")
GRAVEL = WET("gravel_floor", [0.6, 0.58, 0.55], 0.6, 0.4)
Nd["outdoor"] = {
    "window_rooms": ROOMS, "lamp_power": 380.0, "lamp_energy": 1.0, "rain": False,
    "ground": [{"name": "perron", "min": [4.6, -4.0], "max": [13.4, L + 4.0], "y": 0.0, "material": PAVERS},
               {"name": "perron_base", "min": [4.6, -4.0], "max": [13.4, L + 4.0], "y": -0.4, "material": {"color": [0.3, 0.3, 0.29], "rough": 0.8}},
               {"name": "kade_w", "min": [-40.0, -40.0], "max": [0.0, L + 40.0], "y": 0.0, "material": PAVERS},
               {"name": "kade_w_base", "min": [-40.0, -40.0], "max": [0.0, L + 40.0], "y": -0.4, "material": {"color": [0.3, 0.3, 0.29], "rough": 0.8}},
               {"name": "busstation", "min": [18.0, -40.0], "max": [80.0, L + 40.0], "y": 0.0, "material": BRICKS},
               {"name": "busstation_base", "min": [18.0, -40.0], "max": [80.0, L + 40.0], "y": -0.4, "material": {"color": [0.3, 0.3, 0.29], "rough": 0.8}},
               {"name": "baan_w", "min": [0.0, -40.0], "max": [4.6, L + 40.0], "y": -1.0, "material": GRAVEL},
               {"name": "baan_e", "min": [13.4, -40.0], "max": [18.0, L + 40.0], "y": -1.0, "material": GRAVEL}],
    "rows": [{"from": -30.0, "to": 90.0, "line": -34.0, "facing": "east", "lit": 0.25, "shops": 0.0}],
    "lamps": [[24.0, 6.0], [24.0, 30.0], [24.0, 54.0]]}
props = [
    {"type": "trackbed", "pos": [2.3, -1.0, 28.0], "yaw": -90, "size": [80.0, 0.5, 3.4], "collide": False},
    {"type": "trackbed", "pos": [15.7, -1.0, 28.0], "yaw": 90, "size": [80.0, 0.5, 3.4], "collide": False},
    dict(TRAIN, pos=[2.3, -0.4, 30.0], underframe=0.6),
    {"type": "platform_edge", "pos": [5.1, 0.0, 28.0], "yaw": -90, "size": [64.0, 0.01, 1.0], "collide": False},
    {"type": "platform_edge", "pos": [12.9, 0.0, 28.0], "yaw": 90, "size": [64.0, 0.01, 1.0], "collide": False},
    {"type": "canopy", "pos": [9.0, 0.0, 28.0], "yaw": 90, "size": [52.0, 4.6, 10.0], "light": 300.0, "seed": 18, "collide": False},
    {"type": "collider", "pos": [2.3, 0.0, 28.0], "size": [4.6, 1.0, 64.0]},
    {"type": "collider", "pos": [15.7, 0.0, 28.0], "size": [4.6, 1.0, 64.0]},
    {"type": "ticket_gates", "pos": [9.0, 0.0, 1.6], "yaw": 0, "size": [8.8, 1.1, 0.3]},
    {"type": "wall_sign", "pos": [9.0, 3.6, 2.6], "yaw": 0, "size": [3.2, 0.5, 0.03], "text": "NOORD", "panel": BLUE, "color": [1.0, 1.0, 1.0], "glow": 2.0, "collide": False},
    {"type": "bench", "pos": [9.0, 0.0, 20.0], "yaw": 90, "size": [1.8, 0.85, 0.5]},
    {"type": "bench", "pos": [9.0, 0.0, 38.0], "yaw": 90, "size": [1.8, 0.85, 0.5]},
    {"type": "leaflets", "pos": [9.0, 0.0, 28.0], "size": [8.0, 0.0, 52.0], "seed": 861, "count": 40, "collide": False},
    # past the gates: the army's reception, set up and abandoned
    {"type": "crowd_barrier", "pos": [19.0, 0.0, 28.0], "yaw": 90, "size": [40.0, 1.1, 0.7], "seed": 862, "collide": False},
    {"type": "bus", "pos": [27.0, 0.0, 18.0], "yaw": 90, "size": [12.0, 3.2, 2.6], "seed": 863, "collide": False},
    {"type": "bus", "pos": [31.0, 0.0, 38.0], "yaw": 90, "size": [12.0, 3.2, 2.6], "seed": 864, "collide": False},
    {"type": "vehicle", "pos": [40.0, 0.0, 8.0], "yaw": 60, "size": [7.0, 3.0, 2.4], "livery": "army", "van": True, "door_open": "left", "collide": False},
    {"type": "vehicle", "pos": [44.0, 0.0, 20.0], "yaw": 60, "size": [7.0, 3.0, 2.4], "livery": "army", "van": True, "collide": False},
    {"type": "light_tower", "pos": [22.0, 0.0, 4.0], "yaw": face(22.0, 4.0, 9.0, 14.0), "size": [2.2, 8.5, 1.4], "aim": [0.0, 0.0, 16.0], "collide": False},
    {"type": "light_tower", "pos": [36.0, 0.0, 30.0], "yaw": face(36.0, 30.0, 30.0, 10.0), "size": [2.2, 8.5, 1.4], "aim": [0.0, 0.0, 20.0], "collide": False},
    {"type": "aid_post", "pos": [48.0, 0.0, 34.0], "yaw": -90, "size": [6.0, 3.4, 6.0], "military": True, "covered": 0, "stretchers": 3, "seed": 865, "collide": False},
    {"type": "aid_post", "pos": [48.0, 0.0, 44.0], "yaw": -90, "size": [6.0, 3.4, 6.0], "military": True, "covered": 0, "stretchers": 3, "seed": 866, "collide": False}]
Nd["props"] = props
Nd["walls"] = {}
Nd["lights"] = [SUN]
Nd["shots"] = [
    {"id": "a", "pos": [12.6, 3.6, 55.0], "look_at": [6.0, 1.0, 26.0], "fov": 60, "zone": {"min": [0.0, 24.0], "max": [18.0, L]}, "priority": 1},
    {"id": "b", "pos": [6.0, 3.4, 30.0], "look_at": [16.0, 1.0, 2.0], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [18.0, 24.0]}, "priority": 1}]
Nd["spawns"] = {"from_metro": {"pos": [5.8, 0.0, TRAIN_DOORS[1]], "yaw": -90}}
Nd["interactables"] = [
    {"id": "train_back", "kind": "examine", "pos": [5.0, 1.0, 40.0], "radius": 1.2,
     "text": "The train hums at the platform, doors open, lights on. It isn't going back."},
    {"id": "the_end", "kind": "end", "pos": [9.0, 1.0, 3.2], "radius": 2.0,
     "text": "Noord. Past the gates the army's floodlights are on over the bus station: tents pitched, stretchers made up, trucks "
             "parked in rows. Nobody. Not a soldier, not one of the thousands who came this way tonight.\n\nOut on the IJ a ship's "
             "horn sounds, once, and stops."}]
Nd["enemies"] = []
write(Nd)
print("centraal: plein", SO, "hal", HO, "metro", MO, "noord", NO_)
