# damned_waters/tools/citygen/aftermath13.py
# Purpose: the evacuation's leavings retrofitted to the first districts' streets (docs/city_aftermath.md):
# one story a street, placed by hand clear of the ways through; applied once (props marked "after").
STORIES = {
    "herengracht": [   # a family loading a car, then running for it
        {"type": "luggage", "pos": [13.5, 0.04, 4.6], "size": [3.0, 0.0, 2.2], "seed": 101, "cases": 3, "bags": 2, "umbrella": True},
        {"type": "leaflets", "pos": [16.0, 0.0, 4.5], "size": [16.0, 0.0, 4.0], "seed": 102, "count": 24},
        {"type": "leaflets", "pos": [31.0, 0.0, 4.5], "size": [8.0, 0.0, 3.0], "seed": 103, "count": 10}],
    "thorbeckeplein": [   # the hotel's guests, and the way north painted on a board
        {"type": "luggage", "pos": [3.2, 0.04, 49.5], "size": [3.0, 0.0, 3.0], "seed": 111, "cases": 4, "bags": 2, "umbrella": False},
        {"type": "evac_board", "pos": [18.5, 0.0, 55.5], "size": [2.0, 1.8, 0.8], "yaw": 0, "to": "CENTRAAL", "arrow": "up"},
        {"type": "leaflets", "pos": [12.0, 0.0, 44.0], "size": [14.0, 0.0, 14.0], "seed": 112, "count": 40},
        {"type": "leaflets", "pos": [12.0, 0.0, 10.0], "size": [12.0, 0.0, 10.0], "seed": 113, "count": 24}],
    "rembrandtplein": [   # the queue for the last tram: what it couldn't take
        {"type": "luggage", "pos": [28.0, 0.04, 11.5], "size": [4.0, 0.0, 2.5], "seed": 121, "cases": 4, "bags": 4, "umbrella": True, "pushchair": True},
        {"type": "luggage", "pos": [45.0, 0.04, 12.0], "size": [4.0, 0.0, 2.5], "seed": 122, "cases": 3, "bags": 3, "umbrella": True, "chair": True},
        {"type": "vehicle", "pos": [50.0, 0.0, 25.0], "size": [4.6, 1.5, 1.8], "yaw": 35, "livery": "police", "door_open": "left"},
        {"type": "evac_board", "pos": [24.0, 0.0, 45.0], "size": [2.0, 1.8, 0.8], "yaw": 0, "to": "CENTRAAL", "arrow": "left"},
        {"type": "leaflets", "pos": [30.0, 0.0, 22.0], "size": [22.0, 0.0, 12.0], "seed": 123, "count": 60},
        {"type": "leaflets", "pos": [10.0, 0.0, 8.0], "size": [12.0, 0.0, 8.0], "seed": 124, "count": 24}],
    "reguliersbreestraat": [   # a shop looted on the way out; a taxi left with its door open
        {"type": "vehicle", "pos": [50.0, 0.0, 5.0], "size": [4.6, 1.5, 1.8], "yaw": 6, "livery": "taxi", "door_open": "right"},
        {"type": "luggage", "pos": [58.0, 0.04, 3.0], "size": [3.0, 0.0, 1.6], "seed": 131, "cases": 2, "bags": 2, "umbrella": True},
        {"type": "leaflets", "pos": [35.0, 0.0, 5.0], "size": [40.0, 0.0, 6.0], "seed": 132, "count": 50}],
    "muntplein": [   # the police line at the Rokin
        {"type": "vehicle", "pos": [35.0, 0.0, 9.5], "size": [5.6, 2.6, 2.1], "yaw": 20, "livery": "police", "van": True, "door_open": "right"},
        {"type": "model", "model": "ph:Megaphone_01", "pos": [27.8, 0.0, 4.4], "yaw": 70, "tip": 90, "scale": 1.0, "collide": False},
        {"type": "leaflets", "pos": [22.0, 0.0, 12.0], "size": [16.0, 0.0, 12.0], "seed": 141, "count": 40}],
    "bloemenmarkt": [   # the stalls shut, the doors opposite sandbagged
        {"type": "sandbags", "pos": [20.5, 0.0, 11.2], "size": [2.4, 0.6, 0.6], "seed": 151},
        {"type": "sandbags", "pos": [53.5, 0.0, 11.2], "size": [2.4, 0.6, 0.6], "seed": 152},
        {"type": "luggage", "pos": [40.0, 0.04, 7.0], "size": [3.0, 0.0, 2.0], "seed": 153, "cases": 2, "bags": 3, "umbrella": True},
        {"type": "leaflets", "pos": [35.0, 0.0, 6.0], "size": [50.0, 0.0, 6.0], "seed": 154, "count": 50}],
}
LOOTED = {"reguliersbreestraat": [("south", 34.05, [1])]}   # (facing, its first edge, the bays smashed)


def apply(spec):
    """Put a street's story down, once."""
    rid = spec["id"]
    if rid not in STORIES or any(p.get("after") for p in spec.get("props", [])):
        return
    for p in STORIES[rid]:
        q = dict(p, after=True)
        if q["type"] in ("luggage", "leaflets", "model") and "collide" not in q:
            q["collide"] = False
        spec["props"].append(q)
    for facing, edge, bays in LOOTED.get(rid, []):
        for f in spec.get("outdoor", {}).get("facades", []):
            if f.get("facing") == facing and abs(f.get("x0", f.get("z0", -1)) - edge) < 0.01 and f.get("shop"):
                f["shop"]["smashed"] = bays
