# damned_waters/tools/pipeline/house.py
# Purpose: the house's floor plan for the set builder, by the same rules as the engine's
# engine/include/dw/house.hpp: each room sits at its "origin"; a door opening in one room's wall
# and one in the next room's wall at the same place are one doorway; a doorway is "live" (the
# game hangs and swings its leaf, so the picture must show the hole, not a painted leaf) when it
# has a room behind it or its door leads somewhere; a wall two rooms share is built half by each
# (no two surfaces in the same place). Pure Python, unit-tested (tools/pipeline/tests).
#
# ELI5: the same building plan the game reads, so the painter and the builder agree on where every
# door is, which doors open, and who plasters which half of each shared wall.
from __future__ import annotations

import math

WALL_T = 0.3     # wall thickness, grown outward from the bounds (engine: room_spec.hpp WALL_T)
PAIR_TOL = 0.06  # doorway ends this close are the same hole
DOOR_REACH = 1.6
SIDES = ("north", "south", "west", "east")
OPPOSITE = {"north": "south", "south": "north", "west": "east", "east": "west"}


def origin(spec: dict) -> tuple[float, float]:
    o = spec.get("origin", [0.0, 0.0])
    return float(o[0]), float(o[1])


def house_bounds(spec: dict) -> tuple[float, float, float, float]:
    ox, oz = origin(spec)
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    return x0 + ox, z0 + oz, x1 + ox, z1 + oz


def openings(spec: dict) -> list[tuple[str, int, dict]]:
    out = []
    for side in SIDES:
        for k, op in enumerate(spec.get("walls", {}).get(side, {}).get("openings", [])):
            out.append((side, k, op))
    return out


def opening_ends(spec: dict, side: str, op: dict) -> tuple[float, float, float, float]:
    """The opening's two ends on the wall's centre line, in house coordinates."""
    x0, z0, x1, z1 = house_bounds(spec)
    t, h = WALL_T / 2, op["width"] / 2
    if side in ("north", "south"):
        z = z0 - t if side == "north" else z1 + t
        return x0 + op["center"] - h, z, x0 + op["center"] + h, z
    x = x0 - t if side == "west" else x1 + t
    return x, z0 + op["center"] - h, x, z0 + op["center"] + h


def _door_near(spec: dict, x: float, z: float) -> dict | None:
    ox, oz = origin(spec)
    best, bd = None, DOOR_REACH
    for it in spec.get("interactables", []):
        if it.get("kind") != "door":
            continue
        d = math.hypot(it["pos"][0] + ox - x, it["pos"][2] + oz - z)
        if d < bd:
            best, bd = it, d
    return best


def doorways(specs: dict[str, dict]) -> list[dict]:
    """Every door opening, paired across rooms on the same storey (as the engine pairs them)."""
    out, used = [], set()
    ids = sorted(specs)   # the engine loads room files in name order: the same "room a" on both sides
    for a in ids:
        A = specs[a]
        for side, k, op in openings(A):
            if op.get("kind") != "door" or (a, side, k) in used:
                continue
            used.add((a, side, k))
            ax, az, bx, bz = opening_ends(A, side, op)
            d = {"a": a, "side_a": side, "open_a": k, "b": None, "side_b": None, "open_b": None,
                 "ends": (ax, az, bx, bz)}
            for b in ids:
                if b == a or specs[b].get("storey", 0) != A.get("storey", 0) or d["b"]:
                    continue
                for side_b, m, op_b in openings(specs[b]):
                    if op_b.get("kind") != "door" or (b, side_b, m) in used:
                        continue
                    px0, pz0, px1, pz1 = opening_ends(specs[b], side_b, op_b)
                    if math.hypot(px0 - ax, pz0 - az) < PAIR_TOL and math.hypot(px1 - bx, pz1 - bz) < PAIR_TOL:
                        used.add((b, side_b, m))
                        d.update(b=b, side_b=side_b, open_b=m)
                        break
            door = _door_near(A, (ax + bx) / 2, (az + bz) / 2)
            d["live"] = d["b"] is not None or bool(door and door.get("target_room"))
            d["door_a"] = door["id"] if door else None
            out.append(d)
    return out


def live_openings(specs: dict[str, dict], room: str) -> set[tuple[str, int]]:
    """(side, index) of this room's door openings whose leaf the game draws (leave them open)."""
    live = set()
    for d in doorways(specs):
        if not d["live"]:
            continue
        if d["a"] == room:
            live.add((d["side_a"], d["open_a"]))
        if d["b"] == room:
            live.add((d["side_b"], d["open_b"]))
    return live


def stair_openings(specs: dict[str, dict], room: str) -> set[tuple[str, int]]:
    """Live doors with no room behind them on this storey: a flight of stairs beyond (to show)."""
    return {(d["side_a"], d["open_a"]) for d in doorways(specs) if d["a"] == room and d["live"] and d["b"] is None}


def shared_sides(specs: dict[str, dict], room: str) -> set[str]:
    """The walls of this room that another room on its storey shares (each builds half)."""
    R = specs[room]
    x0, z0, x1, z1 = house_bounds(R)
    out = set()
    for other, S in specs.items():
        if other == room or S.get("storey", 0) != R.get("storey", 0):
            continue
        u0, w0, u1, w1 = house_bounds(S)
        overlap_x = min(x1, u1) - max(x0, u0) > 0.05
        overlap_z = min(z1, w1) - max(z0, w0) > 0.05
        if overlap_x and abs(w1 + WALL_T - z0) < 0.02:
            out.add("north")
        if overlap_x and abs(w0 - WALL_T - z1) < 0.02:
            out.add("south")
        if overlap_z and abs(u1 + WALL_T - x0) < 0.02:
            out.add("west")
        if overlap_z and abs(u0 - WALL_T - x1) < 0.02:
            out.add("east")
    return out


def storey_rooms(specs: dict[str, dict], room: str) -> list[str]:
    s = specs[room].get("storey", 0)
    return sorted(r for r, d in specs.items() if d.get("storey", 0) == s)


def peek_shots(spec: dict) -> list[dict]:
    """The doors' views through the crack, as shots to render ("peek_<door id>")."""
    out = []
    for it in spec.get("interactables", []):
        if it.get("kind") == "door" and "peek" in it:
            p = it["peek"]
            out.append({"id": "peek_" + it["id"], "pos": p["pos"], "look_at": p["look_at"], "fov": p.get("fov", 50)})
    return out
