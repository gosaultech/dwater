# damned_waters/tools/citygen/area6.py
# Generates area 6 (storey 13, district 5: the Kalverstraat), the side loop of shops between the Munt and
# the Dam: kalverstraat_noord (its corner by the Dam), kalverstraat (the street), kalversteeg (the alley
# through to Muntplein), and three shops to search: wapenhandel (a sport-shooting shop: ammunition),
# drogist (a chemist's: dressings), juwelier (looted; a box of 9mm under the counter). Opens the Dam's
# corner and Muntplein's west side onto it. Shutters down along most of it, as the evacuation left it.
from pathlib import Path
import json
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import front, shop, shop_doorway, glass_door, street_room, shop_room, write, PAVERS, BRICKS, SUN, ROOMS, R  # noqa: E402

C.DISTRICT.update({"storey": 13, "name": "district 5: the Kalverstraat"})
T = 0.3
KN = [836.0, -224.6]                       # the corner by the Dam: 22 x 24.6
KS = [836.0, KN[1] + 24.6 + T]             # the street: 8 wide, south to the Singel
L = round(-60.3 - KS[1], 3)                # its length: to the Singel's north quay
AL = [844.0 + T, -63.7]                    # the lane east to Muntplein along the quay: 20.8 x 3.4
AW = 3.4
TILES = C.WET("cobblestone_floor_04", [0.75, 0.72, 0.68], 0.65, 0.3)
rng = random.Random(131)

# ── The corner by the Dam ──────────────────────────────────────────────────────────────
N = street_room("kalverstraat_noord", "Kalverstraat", KN, (22.0, 24.6), 10.0,
                "the Kalverstraat's north end, where it opens on the Dam beside the palace: a little square of shops, "
                "their shutters down, the Dam's lights and the funfair over the barrier.")
o = {"window_rooms": ROOMS, "lamp_power": 320.0, "lamp_energy": 1.0, "tide": 0.4,
     "ground": [{"name": "corner", "min": [0.0, 0.0], "max": [22.0, 24.6], "y": 0.0, "material": TILES}],
     "lamps": [[11.0, 12.0], [1.2, 6.0]]}
o["facades"] = [
    front("south", 0.0, 13.95, 0.0, [4.6, 3.6, 3.4, 3.2, 3.0], 4, "cornice", 1301, shop("CAFÉ HET PALEIS", "cafe", "CAFÉ", shutter=0.7), lean=0.0),
    front("east", 0.0, 24.6, 0.0, [4.4, 3.4, 3.2, 3.0], 5, "cornice", 1302, shop("MODEHUIS VAN DAM", "souvenir", "MODE", shutter=1.0, tag="DICHT")),
    front("west", 0.0, 12.0, 22.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 1303, shop("SCHOENEN", "souvenir", "SCHOENEN", shutter=0.9), gable_h=3.8),
    front("west", 12.05, 24.6, 22.0, [4.4, 3.4, 3.2, 3.0], 3, "step", 1304, shop("PARFUMERIE", "hotel", "PARFUM", awning=False, shutter=0.5), gable_h=3.6),
    front("north", 8.05, 22.0, 24.6, [4.4, 3.4, 3.2, 3.0], 4, "cornice", 1305, shop("BOEKHANDEL", "books", "BOEKEN", shutter=1.0, tag="WEG")),
]
N["outdoor"] = o
N["props"] = [
    {"type": "crowd_barrier", "pos": [15.2, 0.0, 0.8], "yaw": 0, "size": [4.4, 1.1, 0.7], "seed": 1},
    {"type": "crowd_barrier", "pos": [20.0, 0.0, 2.2], "yaw": 70, "size": [2.4, 1.1, 0.7], "seed": 2, "roll": 82, "collide": False},   # knocked over: the way through
    {"type": "garland", "pos": [11.0, 0.0, 8.0], "yaw": 0, "size": [22.0, 6.6, 0.1], "collide": False, "color": [1.0, 0.86, 0.6]},
    {"type": "garland", "pos": [11.0, 0.0, 18.0], "yaw": 0, "size": [22.0, 6.6, 0.1], "collide": False, "color": [1.0, 0.86, 0.6]},
    {"type": "luggage", "pos": [10.0, 0.0, 14.0], "size": [6.0, 0.0, 6.0], "seed": 3, "cases": 2, "bags": 4, "collide": False},
    {"type": "leaflets", "pos": [11.0, 0.0, 12.0], "size": [22.0, 0.0, 24.0], "seed": 4, "count": 90, "collide": False},
    {"type": "bike", "pos": [1.2, 0.0, 8.0], "yaw": 5, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 170}]
N["walls"] = {"north": {"openings": [{"kind": "passage", "center": 18.0, "width": 8.0, "height": 10.0}]},
              "south": {"openings": [{"kind": "passage", "center": 4.0, "width": 8.0, "height": 10.0}]}}
N["lights"] = [SUN]
N["shots"] = [
    {"id": "a", "pos": [4.2, 4.2, 24.2], "look_at": [18.0, 4.5, -6.0], "fov": 62, "zone": {"min": [0.0, 12.0], "max": [22.0, 24.6]}, "priority": 1},
    {"id": "b", "pos": [20.6, 3.0, 1.4], "look_at": [3.0, 1.6, 22.0], "fov": 62, "zone": {"min": [0.0, 0.0], "max": [22.0, 12.0]}, "priority": 1}]
N["spawns"] = {"from_dam": {"pos": [18.0, 0.0, 1.6], "yaw": 180}}
N["interactables"] = [
    {"id": "to_dam", "kind": "door", "pos": [18.0, 1.0, 0.2], "radius": 1.6, "target_room": "dam", "target_spawn": "from_kalverstraat"},
    {"id": "palace_side", "kind": "examine", "pos": [10.0, 1.0, 2.0], "radius": 1.8,
     "text": "Over the barrier, the Dam: the wheel turning its lights, the palace lit gold. And the noise of the funfair, still playing."}]
N["enemies"] = [{"id": "op_de_hoek", "kind": "verdronkene", "pos": [6.0, 0.0, 16.0], "yaw": 40}]
write(N)

# ── The street ────────────────────────────────────────────────────────────────────────
S = street_room("kalverstraat", "Kalverstraat", KS, (8.0, L), 10.0,
                "the Kalverstraat, the city's busiest shopping street, from the Dam south to the Singel: shop after shop, "
                "most with their shutters down, garlands of lights still strung across it; a gun shop, a chemist's, a "
                "jeweller's put in by looters; the alley through to Muntplein near its end.")
GUN = (60.0, 69.6)   # (along the west side)
DRUG = (96.0, 105.0)
JEWEL = (30.0, 38.5)  # (along the east side)
west_names = [("H&K MODE", "souvenir"), ("SPORTZAAK DE BAL", "souvenir"), ("HORLOGES", "jeweller"), ("SCHOENEN", "souvenir"), ("TASSEN", "souvenir"),
              ("DAMES MODE", "souvenir"), ("BRILLEN", "hotel"), ("CAFÉ KALVER", "cafe"), ("SPEELGOED", "souvenir"), ("PARFUMERIE", "hotel"),
              ("KAAS · STROOPWAFELS", "snack"), ("CD · DVD", "books"), ("MOBIEL", "hotel"), ("BAKKERIJ", "cafe"), ("HEREN MODE", "souvenir"),
              ("ZONNEBRILLEN", "hotel"), ("SOUVENIRS", "souvenir")]
east_names = [("KINDERKLEDING", "souvenir"), ("BOEKHANDEL", "books"), ("ELEKTRONICA", "hotel"), ("IJSSALON", "restaurant"), ("SNACKBAR", "snack"),
              ("LINGERIE", "hotel"), ("FOTO · CAMERA", "hotel"), ("THEEHUIS", "cafe"), ("SPORTSCHOENEN", "souvenir"), ("CHOCOLATERIE", "cafe"),
              ("PARFUMERIE", "hotel"), ("MODE", "souvenir"), ("SIERADEN", "jeweller"), ("KLOMPEN", "souvenir"), ("TASSEN", "souvenir")]
fac = []
WEST, EAST = [], []


def run_of(side, z_from, z_to, specials, names, seed0):
    """Fronts down one side from z_from to z_to, the special shops where they fall, plain shops between
    (most of them shuttered)."""
    z, k = z_from, 0
    out = []
    while z < z_to - 0.5:
        sp = next((s for s in specials if abs(s[0] - z) < 0.6), None)
        if sp:
            z0, z1, f = sp
            out.append(f)
            z = z1 + 0.05
            continue
        nxt = min([s[0] for s in specials if s[0] > z] + [z_to])
        w = min(rng.uniform(7.0, 9.5), nxt - z - 0.05)
        if w < 3.0:   # too narrow for a shop before the next special: stretch the last one
            z = nxt
            continue
        name, kind = names[k % len(names)]
        storeys = [4.4, 3.4, 3.2, 3.0] + ([2.8] if rng.random() < 0.4 else [])
        gable = rng.choice(["neck", "bell", "step", "cornice", "cornice", "spout"])
        shp = shop(name, kind, name.split()[-1][:10], door_bay=1, shutter=rng.choice([1.0, 1.0, 0.85, 0.6, 0.0]),
                   tag=rng.choice(["", "", "DICHT", "WEG", "NAAR CENTRAAL"]))
        if shp.get("shutter") == 0.0:
            shp.pop("shutter")
        out.append(front(side, round(z, 2), round(z + w, 2), 0.0 if side == "east" else 8.0, storeys, 3, gable, seed0 + k, shp,
                         gable_h=rng.uniform(3.4, 4.0)))
        z += w + 0.05
        k += 1
    return out


GUNF = front("east", GUN[0], GUN[1], 0.0, [4.4, 3.4, 3.2, 3.0], 3, "cornice", 1390,
             shop("WAPENHANDEL DE JAGER", "police", "JAGER", door_bay=1, power=90.0, awning=False, enter=True), lean=0.0)
DRUGF = front("east", DRUG[0], DRUG[1], 0.0, [4.4, 3.4, 3.2, 3.0], 3, "neck", 1391,
              shop("DROGISTERIJ VAN DER LINDEN", "pharmacy", False, door_bay=1, power=95.0, enter=True, cross=False), lean=0.0, gable_h=3.8)
JEWF = front("west", JEWEL[0], JEWEL[1], 8.0, [4.4, 3.4, 3.2, 3.0], 3, "cornice", 1392,
             shop("JUWELIER GOUDSMIT", "jeweller", "GOUD", door_bay=1, power=80.0, awning=False, enter=True, smashed=[0, 2]), lean=0.0)
WEST = run_of("east", 0.0, L, [(GUN[0], GUN[1], GUNF), (DRUG[0], DRUG[1], DRUGF)], west_names, 1310)
ALLEY_Z = (round(AL[1] - KS[1], 3), round(AL[1] + AW - KS[1], 3))
EAST = run_of("west", 0.0, ALLEY_Z[0] - 0.05, [(JEWEL[0], JEWEL[1], JEWF)], east_names, 1350)
o = {"window_rooms": ROOMS, "lamp_power": 300.0, "lamp_energy": 1.0, "tide": 0.5,
     "ground": [{"name": "street", "min": [0.0, 0.0], "max": [8.0, L + 0.3], "y": 0.0, "material": TILES}],   # (to the quay's edge)
     "lamps": [[0.6, float(z)] for z in range(12, int(L), 24)] + [[7.4, float(z)] for z in range(30, int(L), 24)]}   # (off the cameras' shoulders)
o["facades"] = WEST + EAST
S["outdoor"] = o
sp = [{"type": "garland", "pos": [4.0, 0.0, float(z)], "yaw": 0, "size": [8.0, 6.4, 0.1], "collide": False,
       "color": [1.0, 0.86, 0.6] if (z // 12) % 2 else [0.95, 0.95, 1.0], "sag": 0.7}
      for z in range(6, int(L) - 3, 12)]   # (none over the last camera's head)
sp += [
    {"type": "railing", "pos": [4.0, 0.0, L - 0.2], "yaw": 0, "size": [8.0, 1.0, 0.1], "collide": True},   # the quay and the Singel beyond
    {"type": "luggage", "pos": [4.0, 0.0, 22.0], "size": [6.0, 0.0, 6.0], "seed": 11, "cases": 1, "bags": 4, "pushchair": True, "collide": False},
    {"type": "luggage", "pos": [4.0, 0.0, 80.0], "size": [6.0, 0.0, 8.0], "seed": 12, "cases": 2, "bags": 5, "collide": False},
    {"type": "luggage", "pos": [4.0, 0.0, 124.0], "size": [6.0, 0.0, 8.0], "seed": 13, "cases": 1, "bags": 3, "umbrella": True, "collide": False},
    {"type": "leaflets", "pos": [4.0, 0.0, L / 2], "size": [8.0, 0.0, L], "seed": 14, "count": 300, "collide": False},
    {"type": "broken_glass", "pos": [8.0, 0.0, (JEWEL[0] + JEWEL[1]) / 2], "yaw": -90, "size": [8.0, 0.0, 2.2], "seed": 15, "collide": False},
    {"type": "bike", "pos": [1.0, 0.0, 44.0], "yaw": 8, "roll": 84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 180},
    {"type": "bike", "pos": [6.8, 0.0, 112.0], "yaw": 170, "roll": -84, "size": [1.8, 1.1, 0.5], "collide": False, "seed": 181},
    {"type": "model", "model": "ph:trashbag", "pos": [0.8, 0.0, 88.0], "yaw": 30, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:WetFloorSign_01", "pos": [1.0, 0.0, DRUG[0] + 2.0], "yaw": 60, "scale": 1.0, "collide": False},
    {"type": "evac_board", "pos": [4.0, 0.0, 132.0], "yaw": 0, "size": [1.8, 1.9, 0.6], "text": "EVACUATIEROUTE", "to": "VIA DE DAM", "arrow": "up", "collide": False}]
S["props"] = sp
S["walls"] = {"north": {"openings": [{"kind": "passage", "center": 4.0, "width": 8.0, "height": 10.0}]},
              "east": {"openings": [{"kind": "passage", "center": round((ALLEY_Z[0] + ALLEY_Z[1]) / 2, 3), "width": AW, "height": 8.0}]}}
gc, gw, gh = shop_doorway(GUNF)
dc, dw, dh = shop_doorway(DRUGF)
jc, jw, jh = shop_doorway(JEWF)
S["walls"]["west"] = {"openings": [glass_door(gc, gw, gh), glass_door(dc, dw, dh)]}
S["walls"]["east"]["openings"].append(glass_door(jc, jw, jh))
S["lights"] = [SUN]
shots = []
zones = [(0.0, 24.0), (24.0, 48.0), (48.0, 72.0), (72.0, 96.0), (96.0, 120.0), (120.0, L)]
for k, (z0, z1) in enumerate(zones):   # down the street and back, as a shopper would look: high, off the shopfronts,
    south = k % 2 == 0                  # a few metres back from the zone so whoever walks into it is in the frame
    cz = z0 - 3.0 if south else min(z1 + 3.0, L - 0.6)
    shots.append({"id": "abcdef"[k], "pos": [5.4 if south else 2.6, 4.2, cz], "look_at": [2.4 if south else 5.6, 0.6, z1 + 4.0 if south else z0 - 4.0],
                  "fov": 60, "zone": {"min": [0.0, z0], "max": [8.0, z1]}, "priority": 1})
S["shots"] = shots
S["spawns"] = {"from_noord": {"pos": [4.0, 0.0, 1.2], "yaw": 180}, "from_steeg": {"pos": [7.0, 0.0, (ALLEY_Z[0] + ALLEY_Z[1]) / 2], "yaw": 90},
               "from_wapenhandel": {"pos": [0.8, 0.0, gc], "yaw": -90}, "from_drogist": {"pos": [0.8, 0.0, dc], "yaw": -90},
               "from_juwelier": {"pos": [7.2, 0.0, jc], "yaw": 90}}
S["interactables"] = [
    {"id": "door_wapenhandel", "kind": "door", "pos": [0.45, 1.0, gc], "radius": 1.0},
    {"id": "door_drogist", "kind": "door", "pos": [0.45, 1.0, dc], "radius": 1.0},
    {"id": "door_juwelier", "kind": "door", "pos": [7.55, 1.0, jc], "radius": 1.0},
    {"id": "shutters", "kind": "examine", "pos": [4.0, 1.0, 50.0], "radius": 1.6,
     "text": "Shutter after shutter, all the way down. On one, sprayed: NAAR CENTRAAL. On the next: TE LAAT."},
    {"id": "singel", "kind": "examine", "pos": [4.0, 1.0, L - 1.0], "radius": 2.0,
     "text": "The Singel, black. Across it, the flower market's stalls rock on their pontoons, their bulbs still lit."},
    {"id": "shells_street", "kind": "pickup", "item": "shotgun_shells", "count": 2, "pos": [6.4, 0.0, 84.0], "radius": 0.9}]
S["enemies"] = [{"id": "voor_de_etalage", "kind": "verdronkene", "pos": [6.5, 0.0, 34.0], "yaw": 270},
                {"id": "in_de_straat_2", "kind": "verdronkene", "pos": [3.0, 0.0, 78.0], "yaw": 10},
                {"id": "bij_de_steeg", "kind": "verdronkene", "pos": [4.5, 0.0, 132.0], "yaw": 200}]
write(S)

# ── The alley through to Muntplein ─────────────────────────────────────────────────────────
A = street_room("kalversteeg", "Kalversteeg", AL, (20.8, AW), 8.0,
                "the narrow lane from the Kalverstraat along the Singel's quay through to Muntplein: bins, bikes chained to "
                "the drainpipes, the back door of a restaurant's kitchen, the flower market's stalls across the water.")
o = {"window_rooms": ROOMS, "lamp_power": 200.0, "lamp_energy": 1.0,
     "ground": [{"name": "alley", "min": [0.0, 0.0], "max": [20.8, AW + 0.3], "y": 0.0, "material": C.WET("cobblestone_floor_04", [0.65, 0.62, 0.58], 0.9, 0.6)}],
     "lamps": [[10.4, 0.5]]}
o["facades"] = [front("south", 0.0, 20.8, 0.0, [4.0, 3.2, 3.0, 2.8], 6, "cornice", 1395, door_bay=3, stoop=0.0, lean=0.0, lit=0.2)]   # (the quay side is open)
A["outdoor"] = o
A["props"] = [
    {"type": "model", "model": "ph:metal_trash_can", "pos": [5.0, 0.0, 0.6], "yaw": 0, "scale": 1.0, "size": [0.5, 1.0, 0.5]},
    {"type": "model", "model": "ph:metal_trash_can", "pos": [5.7, 0.0, 0.6], "yaw": 20, "scale": 1.0, "size": [0.5, 1.0, 0.5]},
    {"type": "model", "model": "ph:trashbag", "pos": [6.6, 0.0, 0.7], "yaw": 50, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:plastic_crate_02", "pos": [14.0, 0.0, 0.5], "yaw": 10, "scale": 1.0, "collide": False},
    {"type": "bike", "pos": [16.5, 0.0, 0.5], "yaw": 178, "size": [1.8, 1.1, 0.5], "collide": True, "seed": 191},
    {"type": "railing", "pos": [10.4, 0.0, AW - 0.1], "yaw": 0, "size": [20.8, 1.0, 0.1], "collide": False}]
A["walls"] = {"west": {"openings": [{"kind": "passage", "center": AW / 2, "width": AW, "height": 8.0}]},
              "east": {"openings": [{"kind": "passage", "center": AW / 2, "width": AW, "height": 8.0}]}}
A["lights"] = [SUN]
A["shots"] = [{"id": "a", "pos": [1.2, 3.6, 2.4], "look_at": [20.8, 2.4, 5.0], "fov": 60, "zone": {"min": [0.0, 0.0], "max": [20.8, AW]}, "priority": 1}]   # east along the quay: the Munttoren over the water
A["spawns"] = {"from_muntplein": {"pos": [19.6, 0.0, AW / 2], "yaw": 90}}
A["interactables"] = [
    {"id": "to_muntplein", "kind": "door", "pos": [20.6, 1.0, AW / 2], "radius": 1.6, "target_room": "muntplein", "target_spawn": "from_kalverstraat"},
    {"id": "kitchen", "kind": "examine", "pos": [9.0, 1.0, 0.6], "radius": 1.2,
     "text": "A kitchen's back door, propped open. A pan still on the flame inside, burned black. Nobody turned it off."}]
A["enemies"] = []
write(A)

# ── The gun shop: a sport-shooting and hunting shop ─────────────────────────────────────────
WO = [KS[0] - T - 9.0, KS[1] + GUN[0]]
Wd = GUN[1] - GUN[0]
ug = gc - GUN[0]
Wg = shop_room("wapenhandel", "Wapenhandel de Jager", WO, (9.0, Wd), 3.6,
               "a sport-shooting and hunting shop: the gun racks behind the counter mostly empty, the glass cases of rifles "
               "chained shut, targets on the walls, boxes torn open on the floor. Whoever got here first knew what they wanted.",
               {"floor": {"ph": "wood_floor_worn", "tint": [0.5, 0.42, 0.34], "rough": 0.6}, "wall": {"color": [0.3, 0.34, 0.28], "rough": 0.7},
                "ceiling": {"color": [0.6, 0.6, 0.58], "rough": 0.8}, "wainscot": {"ph": "dark_wood", "tint": [0.5, 0.38, 0.28], "scale": 0.5},
                "wainscot_height": 1.0, "skirting": None}, exposure=0.85)
Wg["walls"] = {"east": {"facade": True, "openings": [glass_door(ug, gw, gh)]}}
Wg["props"] = [   # the rack on the back wall, the glass counter in front of it; cartridges down the south wall
    {"type": "gun_rack", "pos": [0.25, 0.0, Wd / 2], "size": [5.6, 2.5, 0.42], "yaw": 90, "slots": 24, "chained": 2, "left": 1, "seed": 20},
    {"type": "counter", "pos": [2.4, 0.0, Wd / 2 + 1.6], "size": [3.6, 1.0, 0.7], "yaw": 90, "till": True},
    {"type": "display_case", "pos": [2.4, 0.0, Wd / 2 - 1.9], "size": [3.0, 1.0, 0.7], "yaw": 90, "palette": "guns", "empty": 0.85, "seed": 21},
    {"type": "broken_glass", "pos": [3.0, 0.0, Wd / 2 - 1.9], "yaw": 90, "size": [3.0, 0.0, 1.2], "seed": 23, "collide": False},
    {"type": "shelving", "pos": [4.9, 0.0, Wd - 0.3], "size": [6.0, 2.2, 0.45], "yaw": 180, "palette": "ammo", "empty": 0.7, "seed": 22, "fallen": 14},
    {"type": "coat_rack", "pos": [6.0, 0.0, 5.6], "size": [2.2, 1.7, 0.6], "yaw": 0, "seed": 24, "collide": True,
     "colors": [[0.2, 0.24, 0.13], [0.3, 0.22, 0.12], [0.85, 0.3, 0.04], [0.14, 0.16, 0.1], [0.36, 0.32, 0.22]]},   # hunting jackets
    {"type": "wall_sign", "pos": [0.04, 2.95, Wd / 2], "size": [2.2, 0.42, 0.03], "yaw": 90, "text": "SCHIETSPORT · JACHT", "color": [1.0, 0.85, 0.6], "glow": 2.0, "collide": False},
    {"type": "poster", "pos": [2.6, 2.75, Wd - 0.03], "size": [0.6, 0.8, 0.05], "yaw": 180, "title": "10 · 9 · 8", "color": [0.85, 0.83, 0.75], "glow": 0.2, "collide": False},
    {"type": "poster", "pos": [4.6, 2.75, Wd - 0.03], "size": [0.6, 0.8, 0.05], "yaw": 180, "title": "10 · 9 · 8", "color": [0.85, 0.83, 0.75], "glow": 0.2, "collide": False},
    {"type": "poster", "pos": [6.6, 2.75, Wd - 0.03], "size": [0.6, 0.8, 0.05], "yaw": 180, "title": "10 · 9 · 8", "color": [0.85, 0.83, 0.75], "glow": 0.2, "collide": False},
    {"type": "model", "model": "ph:ammo_box", "pos": [4.6, 0.0, Wd - 1.4], "yaw": 40, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:ammo_box", "pos": [5.3, 0.0, Wd - 1.1], "yaw": 110, "scale": 1.0, "collide": False},
    {"type": "model", "model": "ph:cardboard_box_01", "pos": [5.2, 0.0, 4.2], "yaw": 70, "scale": 0.8, "collide": False},
    {"type": "model", "model": "ph:cardboard_box_01", "pos": [6.0, 0.0, Wd - 1.6], "yaw": 15, "scale": 0.6, "collide": False},
    {"type": "strip_light", "pos": [3.0, 3.6, Wd / 2], "size": [5.0, 0.1, 0.2], "yaw": 90, "collide": False},
    {"type": "strip_light", "pos": [6.4, 3.6, Wd / 2], "size": [5.0, 0.1, 0.2], "yaw": 90, "collide": False}]
Wg["lights"] = [{"kind": "area", "pos": [3.0, 3.5, Wd / 2], "look_at": [3.0, 0.0, Wd / 2], "size": 1.6, "color": [1.0, 0.95, 0.85], "blender_power": 90, "godot_energy": 0.5, "range": 7.0},
                {"kind": "area", "pos": [6.4, 3.5, Wd / 2], "look_at": [6.4, 0.0, Wd / 2], "size": 1.6, "color": [1.0, 0.95, 0.85], "blender_power": 60, "godot_energy": 0.4, "range": 7.0}]
Wg["shots"] = [{"id": "a", "pos": [8.5, 2.9, 0.5], "look_at": [0.6, 1.1, Wd / 2 + 1.2], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [9.0, Wd]}, "priority": 1}]
Wg["spawns"] = {"from_street": {"pos": [8.2, 0.0, ug], "yaw": 90}}
Wg["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [8.55, 1.0, ug], "radius": 1.0},
    {"id": "racks", "kind": "examine", "pos": [1.4, 1.0, Wd / 2 - 2.0], "radius": 1.4,
     "text": "The racks are empty but for two hunting rifles chained through their trigger guards. No key. No use to you anyway."},
    {"id": "shells_counter", "kind": "pickup", "item": "shotgun_shells", "count": 10, "pos": [2.4, 1.02, Wd / 2 + 2.6], "radius": 0.9},
    {"id": "ammo_case", "kind": "pickup", "item": "handgun_ammo", "count": 15, "pos": [4.9, 0.0, Wd - 1.2], "radius": 0.9}]
Wg["enemies"] = [{"id": "de_wapenhandelaar", "kind": "verdronkene", "pos": [1.3, 0.0, Wd / 2 - 0.5], "yaw": 90}]
write(Wg)

# ── The chemist's ─────────────────────────────────────────────────────────────────────────
DO_ = [KS[0] - T - 9.0, KS[1] + DRUG[0]]
Dd = DRUG[1] - DRUG[0]
ud = dc - DRUG[0]
Dg = shop_room("drogist", "Drogisterij van der Linden", DO_, (9.0, Dd), 3.4,
               "a chemist's: shelves of shampoo and plasters and cough sweets, picked over, the till open, a carved gaper's head "
               "over the counter with its tongue out, as the old Dutch chemists had.",
               {"floor": {"ph": "large_floor_tiles_02", "tint": [0.8, 0.8, 0.78], "rough": 0.35}, "wall": {"color": [0.85, 0.87, 0.86], "rough": 0.6},
                "ceiling": {"color": [0.85, 0.85, 0.85], "rough": 0.8}, "skirting": {"color": [0.15, 0.3, 0.45], "rough": 0.4}, "skirting_height": 0.1},
               exposure=0.85)
Dg["walls"] = {"east": {"facade": True, "openings": [glass_door(ud, dw, dh)]}}
Dg["props"] = [
    {"type": "counter", "pos": [1.6, 0.0, Dd / 2], "size": [4.0, 1.0, 0.7], "yaw": 90, "till": True},
    {"type": "shelving", "pos": [4.6, 0.0, 2.6], "size": [5.0, 1.7, 0.9], "yaw": 90, "double": True, "palette": "pharmacy", "empty": 0.35, "seed": 31, "shelves": 4},
    {"type": "shelving", "pos": [4.5, 0.0, 0.3], "size": [7.0, 2.2, 0.45], "yaw": 0, "palette": "pharmacy", "empty": 0.3, "seed": 32},
    {"type": "shelving", "pos": [3.4, 0.0, Dd - 0.3], "size": [5.6, 2.2, 0.45], "yaw": 180, "palette": "pharmacy", "empty": 0.45, "seed": 33},
    {"type": "wall_sign", "pos": [0.04, 2.5, Dd / 2], "size": [2.4, 0.45, 0.03], "yaw": 90, "text": "DROGISTERIJ", "color": [0.9, 0.95, 1.0], "glow": 2.0, "collide": False},
    {"type": "strip_light", "pos": [4.5, 3.4, Dd / 2], "size": [5.0, 0.1, 0.2], "yaw": 90, "collide": False}]
Dg["lights"] = [{"kind": "area", "pos": [4.5, 3.3, Dd / 2], "look_at": [4.5, 0.0, Dd / 2], "size": 1.6, "color": [0.95, 0.98, 1.0], "blender_power": 85, "godot_energy": 0.5, "range": 7.0}]
Dg["shots"] = [{"id": "a", "pos": [8.4, 2.7, Dd - 0.6], "look_at": [1.0, 1.0, 1.5], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [9.0, Dd]}, "priority": 1}]
Dg["spawns"] = {"from_street": {"pos": [8.2, 0.0, ud], "yaw": 90}}
Dg["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [8.55, 1.0, ud], "radius": 1.0},
    {"id": "dressing_shelf", "kind": "pickup", "item": "med_small", "count": 1, "pos": [4.6, 0.62, 3.6], "radius": 0.9},
    {"id": "dressing_counter", "kind": "pickup", "item": "med_small", "count": 1, "pos": [1.7, 1.02, Dd / 2 + 1.2], "radius": 0.9},
    {"id": "first_aid_back", "kind": "pickup", "item": "first_aid", "count": 1, "pos": [7.6, 0.0, 0.8], "radius": 0.9},
    {"id": "gaper", "kind": "examine", "pos": [1.2, 1.0, Dd / 2 - 1.2], "radius": 1.2,
     "text": "The gaper, the chemist's carved head, tongue out, eyes rolled up. Someone has hung a rosary on it."}]
Dg["enemies"] = []
write(Dg)

# ── The jeweller's, looted ────────────────────────────────────────────────────────────────
JO = [KS[0] + 8.0 + T, KS[1] + JEWEL[0]]
Jd = JEWEL[1] - JEWEL[0]
uj = jc - JEWEL[0]
Jg = shop_room("juwelier", "Juwelier Goudsmit", JO, (8.0, Jd), 3.4,
               "a jeweller's, put in by looters: the cases smashed and emptied, the glass everywhere, the trays thrown down, "
               "the safe door open. Under the counter, a box the looters missed.",
               {"floor": {"ph": "marble_01", "tint": [0.85, 0.82, 0.78], "rough": 0.5, "scale": 1.5}, "wall": {"color": [0.36, 0.3, 0.26], "rough": 0.6},
                "ceiling": {"color": [0.6, 0.57, 0.52], "rough": 0.7}, "wainscot": {"ph": "rosewood_veneer1", "tint": [0.6, 0.42, 0.32], "scale": 0.6},
                "wainscot_height": 1.0, "skirting": None}, exposure=0.9)
Jg["walls"] = {"west": {"facade": True, "openings": [glass_door(uj, jw, jh)]}}
Jg["props"] = [
    {"type": "display_case", "pos": [3.2, 0.0, 2.2], "size": [3.0, 1.0, 0.7], "yaw": 0, "palette": "candy", "empty": 0.95, "seed": 41},
    {"type": "display_case", "pos": [3.2, 0.0, Jd - 2.2], "size": [3.0, 1.0, 0.7], "yaw": 180, "palette": "candy", "empty": 0.95, "seed": 42},
    {"type": "counter", "pos": [6.6, 0.0, Jd / 2], "size": [3.6, 1.0, 0.7], "yaw": -90, "till": True, "material": {"ph": "rosewood_veneer1", "tint": [0.6, 0.42, 0.32], "scale": 0.6}},
    {"type": "broken_glass", "pos": [3.2, 0.0, Jd / 2], "yaw": 0, "size": [5.0, 0.0, 3.0], "seed": 43, "collide": False},
    {"type": "model", "model": "ph:drawer_cabinet", "pos": [7.6, 0.0, 1.0], "yaw": -90, "scale": 1.0, "size": [0.6, 1.2, 0.5]},
    {"type": "model", "model": "ph:Chandelier_02", "pos": [4.0, 2.4, Jd / 2], "yaw": 0, "fit": [1.0, 0.9, 1.0], "collide": False}]
Jg["lights"] = [{"kind": "point", "pos": [4.0, 2.4, Jd / 2], "color": [1.0, 0.8, 0.55], "blender_power": 120, "godot_energy": 0.6, "range": 6.0, "radius": 0.3},
                {"kind": "area", "pos": [3.2, 3.3, 2.2], "look_at": [3.2, 0.0, 2.2], "size": 1.0, "color": [1.0, 0.94, 0.85], "blender_power": 110, "godot_energy": 0.4, "range": 5.0},
                {"kind": "area", "pos": [3.2, 3.3, Jd - 2.2], "look_at": [3.2, 0.0, Jd - 2.2], "size": 1.0, "color": [1.0, 0.94, 0.85], "blender_power": 110, "godot_energy": 0.4, "range": 5.0}]   # the spots over the cases
Jg["shots"] = [{"id": "a", "pos": [0.6, 2.7, 0.6], "look_at": [7.0, 0.8, Jd - 1.5], "fov": 66, "zone": {"min": [0.0, 0.0], "max": [8.0, Jd]}, "priority": 1}]
Jg["spawns"] = {"from_street": {"pos": [0.8, 0.0, uj], "yaw": -90}}
Jg["interactables"] = [
    {"id": "door_street", "kind": "door", "pos": [0.45, 1.0, uj], "radius": 1.0},
    {"id": "ammo_counter", "kind": "pickup", "item": "handgun_ammo", "count": 6, "pos": [6.9, 0.3, Jd / 2 + 0.8], "radius": 0.9},
    {"id": "safe", "kind": "examine", "pos": [7.2, 1.0, 1.2], "radius": 1.2,
     "text": "The safe stands open and empty. Whoever opened it had the code; there isn't a mark on it."},
    {"id": "under_counter", "kind": "examine", "pos": [6.0, 1.0, Jd / 2 + 0.6], "radius": 1.0,
     "text": "A holster screwed under the counter, empty. Its box of rounds is still on the shelf beside it."}]
Jg["enemies"] = []
write(Jg)

# ── The Dam's corner and Muntplein's west side, opened onto it ───────────────────────────────
D = json.load(open(R + "dam.json"))
D["props"] = [p for p in D["props"] if not (p["type"] == "crowd_barrier" and abs(p["pos"][0] - 4.0) < 0.1 and p["pos"][2] > 68)]
D["props"].append({"type": "crowd_barrier", "pos": [2.0, 0.0, 69.0], "yaw": 0, "size": [4.0, 1.1, 0.7], "seed": 30})
D["props"].append({"type": "crowd_barrier", "pos": [6.4, 0.0, 67.6], "yaw": -60, "size": [2.4, 1.1, 0.7], "seed": 34, "roll": 82, "collide": False})
D["interactables"] = [i for i in D["interactables"] if i["id"] not in ("kalverstraat", "to_kalverstraat")]
D["interactables"].append({"id": "to_kalverstraat", "kind": "door", "pos": [5.4, 1.0, 69.8], "radius": 1.6, "target_room": "kalverstraat_noord",
                           "target_spawn": "from_dam"})
D["spawns"]["from_kalverstraat"] = {"pos": [6.0, 0.0, 68.0], "yaw": 0}
json.dump(D, open(R + "dam.json", "w"), indent=2, ensure_ascii=True)
open(R + "dam.json", "a").write("\n")
M = json.load(open(R + "muntplein.json"))
M["walls"]["west"]["openings"] = [o_ for o_ in M["walls"]["west"]["openings"] if abs(o_["center"] - 2.0) > 0.1] + \
    [{"kind": "passage", "center": 2.0, "width": AW, "height": 8.0}]
M["interactables"] = [i for i in M["interactables"] if i["id"] != "to_kalverstraat"]
M["interactables"].append({"id": "to_kalverstraat", "kind": "door", "pos": [0.2, 1.0, 2.0], "radius": 1.6, "target_room": "kalversteeg",
                           "target_spawn": "from_muntplein"})
M["spawns"]["from_kalverstraat"] = {"pos": [1.8, 0.0, 2.0], "yaw": -90}
json.dump(M, open(R + "muntplein.json", "w"), indent=2, ensure_ascii=True)
open(R + "muntplein.json", "a").write("\n")
B = json.load(open(R + "bloemenmarkt.json"))   # its far bank stops short of the Kalverstraat's houses
B["outdoor"]["canal"]["far_span"] = [-40.0, 30.0]
json.dump(B, open(R + "bloemenmarkt.json", "w"), indent=2, ensure_ascii=True)
open(R + "bloemenmarkt.json", "a").write("\n")
print("length", L, "alley", ALLEY_Z, "doors gun", round(gc, 2), "drug", round(dc, 2), "jewel", round(jc, 2))
