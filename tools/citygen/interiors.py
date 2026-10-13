# damned_waters/tools/citygen/interiors.py
# Purpose: the interior pass over the city's shops: their stock a photo of real stock (the photos in
# tools/assets/photos.json, behind the shelves' edges), the fixtures a real shop of the kind is
# crowded with, its posters and signs. Applied after the area generators (build_city.py); what it
# adds is marked "interior" and replaced each run, so it can run any number of times.
import math

PHOTOS = {"pharmacy": "health_wall", "souvenir": "souvenir_window", "bar": "wine_shelf"}   # a palette's stock, photographed
SAND = {"ph": "large_sandstone_blocks", "tint": [0.86, 0.8, 0.68], "scale": 0.8}


def _footprint(p):
    w, d = p["size"][0], p["size"][-1]
    t = math.radians(p.get("yaw", 0.0))
    return p["pos"][0], p["pos"][2], w / 2, d / 2, t


def _inside(x, z, fp, margin):
    cx, cz, hx, hz, t = fp
    dx, dz = x - cx, z - cz
    lx, lz = dx * math.cos(t) - dz * math.sin(t), dx * math.sin(t) + dz * math.cos(t)
    return abs(lx) < hx + margin and abs(lz) < hz + margin


def put(spec, *props):
    """Add fixtures, clearing the loose clutter (boxes, crates, bags, a chair knocked over) they land on."""
    for p in props:
        p["interior"] = True
        if "size" in p and p.get("collide", True) is not False:
            fp = _footprint(p)
            spec["props"] = [q for q in spec["props"] if not (q["type"] == "model" and not q.get("interior") and q["pos"][1] < 0.5
                                                              and _inside(q["pos"][0], q["pos"][2], fp, 0.35))]
        spec["props"].append(p)


def stock(spec, photo=None, rows=0):
    """Every shelving unit's stock a photo of its kind's (or `photo`'s)."""
    for p in spec["props"]:
        if p["type"] == "shelving":
            p["photo"] = photo or PHOTOS.get(p.get("palette", ""), "health_wall")
            p.setdefault("seed", rows)
            rows += 1


def poster(x, y, z, yaw, title, line, color, w=1.0, h=1.4):
    return {"type": "poster", "pos": [x, y, z], "size": [w, h, 0.05], "yaw": yaw, "title": title, "line": line, "color": color, "collide": False}


def sign(x, y, z, yaw, text, w, panel, color=(1.0, 1.0, 1.0), glow=1.0):
    return {"type": "wall_sign", "pos": [x, y, z], "size": [w, 0.4, 0.03], "yaw": yaw, "text": text, "panel": {"color": list(panel), "rough": 0.5},
            "color": list(color), "glow": glow, "collide": False}


def apotheek(s):
    stock(s)
    for p in s["props"]:
        if p["type"] == "shelving" and abs(p["pos"][2] - 0.3) < 0.01:   # behind the counter: the old jars
            p["photo"] = "apothecary_jars"
    put(s, {"type": "block", "pos": [8.25, 0.0, 0.3], "size": [1.9, 1.05, 0.5], "material": {"ph": "dark_wood", "tint": [0.42, 0.3, 0.22], "scale": 0.5}},
        {"type": "photo_layer", "photo": "pharmacy_drawers", "pos": [8.25, 0.06, 0.56], "size": [1.8, 0.95, 0.01], "collide": False},
        poster(9.42, 0.9, 4.2, -90, "GRIEPPRIK", "VRAAG HET UW APOTHEKER", [0.1, 0.45, 0.35]),
        poster(9.42, 0.9, 6.6, -90, "HOOIKOORTS?", "WIJ HELPEN U VERDER", [0.85, 0.75, 0.2]))


def drogist(s):
    stock(s)
    put(s, {"type": "shelving", "pos": [7.2, 0.0, 2.8], "yaw": 90, "size": [3.6, 1.7, 0.9], "double": True, "palette": "pharmacy", "shelves": 4,
            "photo": "health_wall", "seed": 4},
        {"type": "shelving", "pos": [0.3, 0.0, 4.5], "yaw": 90, "size": [4.0, 2.0, 0.45], "palette": "candy", "photo": "candy_jars"},
        {"type": "shelving", "pos": [4.6, 0.0, 6.8], "yaw": 90, "size": [1.6, 1.5, 0.9], "double": True, "palette": "pharmacy", "shelves": 4,
         "photo": "health_wall", "seed": 7},
        sign(4.5, 2.65, 0.05, 0, "2E HALVE PRIJS", 2.6, (0.8, 0.05, 0.05)),
        sign(3.4, 2.65, 8.95, 180, "ACTIE", 1.6, (0.8, 0.05, 0.05)))


def souvenirwinkel(s):
    stock(s)
    put(s, {"type": "clothes_rail", "pos": [6.0, 0.0, 3.4], "yaw": 90, "size": [1.5, 1.55, 0.5], "photo": "tshirts_rack"},
        {"type": "clothes_rail", "pos": [6.0, 0.0, 1.4], "yaw": 90, "size": [1.4, 1.55, 0.5], "photo": "clothes_hangers"},
        {"type": "photo_layer", "photo": "souvenir_window", "pos": [8.97, 0.95, 2.4], "yaw": -90, "size": [2.6, 1.6, 0.01], "collide": False},
        {"type": "shelving", "pos": [0.3, 0.0, 4.6], "yaw": 90, "size": [2.6, 2.0, 0.45], "palette": "candy", "photo": "candy_jars"})


def hotel_bar(s):
    stock(s)


def bloemenkraam(s):
    stock(s, "tulip_buckets")
    for p in s["props"]:
        if p["type"] == "flower_buckets":
            p["photo"] = True


def juwelier(s):
    for p in s["props"]:
        if p["type"] == "display_case":
            p["palette"] = "jewel"
    put(s, {"type": "display_case", "pos": [2.0, 0.0, 0.3], "size": [1.6, 2.0, 0.5], "palette": "jewel", "seed": 11},
        {"type": "display_case", "pos": [4.4, 0.0, 0.3], "size": [1.6, 2.0, 0.5], "palette": "jewel", "seed": 12},
        {"type": "display_case", "pos": [6.4, 0.0, 8.2], "yaw": 180, "size": [1.6, 2.0, 0.5], "palette": "jewel", "seed": 13},
        {"type": "safe", "pos": [7.45, 0.0, 0.6], "yaw": -90, "size": [0.8, 1.2, 0.7], "open": True},
        {"type": "runner", "pos": [3.0, 0.0, 4.25], "yaw": 90, "size": [0.9, 0.012, 4.6], "collide": False},
        {"type": "model", "model": "ph:modern_arm_chair_01", "pos": [1.2, 0.0, 7.6], "yaw": 160, "scale": 1.0, "size": [0.7, 0.8, 0.7]},
        {"type": "model", "model": "ph:side_table_01", "pos": [2.2, 0.0, 7.8], "yaw": 0, "scale": 1.0, "collide": False},
        {"type": "model", "model": "ph:ornate_mirror_01", "pos": [5.0, 1.0, 8.45], "yaw": 180, "scale": 1.0, "collide": False})


def wisselkantoor(s):
    put(s, {"type": "stanchions", "pos": [4.8, 0.0, 3.0], "yaw": 90, "size": [3.0, 0.95, 0.1]},
        {"type": "bench", "pos": [6.6, 0.0, 1.8], "yaw": -90, "size": [1.8, 0.85, 0.5]},
        poster(6.97, 0.9, 3.6, -90, "GEEN COMMISSIE", "BESTE KOERS VAN DAMRAK", [0.05, 0.25, 0.55]),
        poster(4.6, 0.9, 0.03, 0, "EXCHANGE", "OPEN 7 DAGEN", [0.85, 0.65, 0.1], w=0.9))


def warenhuis(s):
    stock(s, "health_wall")
    looks = ["clothes_closet", "clothes_hangers", "tshirts_rack"]
    spots = [(2.6, 16.6), (4.6, 16.6), (2.6, 18.6), (4.6, 18.6), (8.0, 17.6), (14.0, 16.6), (14.0, 18.6), (19.0, 16.6), (19.0, 18.6), (21.0, 17.6)]
    put(s, *[{"type": "clothes_rail", "pos": [x, 0.0, z], "yaw": 0, "size": [1.5, 1.55, 0.5], "photo": looks[k % 3]} for k, (x, z) in enumerate(spots)],
        {"type": "shelving", "pos": [9.0, 0.0, 0.3], "yaw": 0, "size": [15.0, 2.4, 0.45], "palette": "pharmacy", "photo": "health_wall", "seed": 3},
        sign(9.0, 3.1, 0.05, 0, "PARFUMERIE · COSMETICA", 4.2, (0.08, 0.06, 0.05), (0.95, 0.85, 0.6), 1.5))


def bioscoop(s):
    put(s, {"type": "shelving", "pos": [15.65, 0.0, 9.6], "yaw": -90, "size": [2.6, 2.0, 0.45], "palette": "candy", "photo": "candy_jars"},
        poster(15.92, 0.9, 3.4, -90, "DE DIEPTE", "VANAF DONDERDAG", [0.05, 0.12, 0.2]),
        poster(15.92, 0.9, 1.6, -90, "ZOMERNACHT", "UITVERKOCHT", [0.55, 0.1, 0.15]))


def politiepost(s):
    missing = [("SANNE (7)", [0.9, 0.88, 0.8]), ("DHR. DE VRIES (81)", [0.88, 0.86, 0.78]), ("AHMED (12)", [0.9, 0.9, 0.85]),
               ("LOTTE EN BRAM", [0.86, 0.85, 0.8])]
    put(s, *[poster(0.03, 1.15 + 0.85 * (k // 2), 4.3 + 0.75 * (k % 2), 90, "VERMIST", name, col, w=0.55, h=0.75) for k, (name, col) in enumerate(missing)],
        poster(3.0, 0.9, 0.03, 0, "EVACUATIE", "VERZAMELPUNT: DE DAM", [0.85, 0.45, 0.05]))


def hotel_lobby(s):
    for p in s["props"]:
        if p["type"] == "shelving":   # behind the desk: the guests' pigeonholes
            p["photo"] = "pharmacy_drawers"


def centraal_hal(s):
    for p in s["props"]:
        if p["type"] == "shop_unit" and p.get("open", 0) > 0:
            p["photo"] = "candy_jars" if "BROODJES" in p.get("name", "") else "health_wall"


ROOMS = {"apotheek": apotheek, "drogist": drogist, "souvenirwinkel": souvenirwinkel, "hotel_bar": hotel_bar, "bloemenkraam": bloemenkraam,
         "juwelier": juwelier, "wisselkantoor": wisselkantoor, "warenhuis": warenhuis, "bioscoop": bioscoop, "politiepost": politiepost,
         "hotel_lobby": hotel_lobby, "centraal_hal": centraal_hal}


def apply(spec):
    """The pass over one room (nothing if it isn't one of the shops); run again, the same result."""
    f = ROOMS.get(spec["id"])
    if not f:
        return
    spec["props"] = [p for p in spec["props"] if not p.get("interior")]
    f(spec)
