# damned_waters/tools/pipeline/roomspec.py
# Purpose: load + validate RoomSpec JSON (the single source of truth for a room)
# and convert Godot coordinates to Blender coordinates. Pure Python, no bpy,
# so it is unit-testable and importable from both Blender and plain Python.
#
# ELI5: a RoomSpec is the architect's blueprint. Blender reads it to paint the
# picture; Godot reads the same blueprint to place the invisible walls. One
# blueprint means the picture and the walls can never disagree.
from __future__ import annotations

import json
from pathlib import Path

SIDES = ("north", "south", "east", "west")
DEPTH_MAX_M = 32.0  # must match game/src/core/depth_codec.gd and plate.gdshader


class SpecError(ValueError):
    """Raised when a RoomSpec is structurally invalid."""


def g2b(v):
    """Godot (x, y-up, z-toward-viewer) -> Blender (x, y-forward, z-up)."""
    x, y, z = v
    return (x, -z, y)


def wall_segments(spec: dict) -> dict:
    """Return each wall's line (in Godot XZ) and its openings.

    North = min-z side, South = max-z, West = min-x, East = max-x.
    Opening 'center' is measured along the wall from its min coordinate.
    """
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    walls = spec.get("walls", {})
    lines = {
        "north": ((x0, z0), (x1, z0)),
        "south": ((x0, z1), (x1, z1)),
        "west": ((x0, z0), (x0, z1)),
        "east": ((x1, z0), (x1, z1)),
    }
    return {s: {"line": lines[s], "openings": walls.get(s, {}).get("openings", [])} for s in SIDES}


def validate(spec: dict) -> list[str]:
    """Return a list of human-readable problems (empty list == valid)."""
    problems = []
    for key in ("id", "bounds", "height", "shots", "spawns"):
        if key not in spec:
            problems.append(f"missing '{key}'")
    if problems:
        return problems
    (x0, z0), (x1, z1) = spec["bounds"]["min"], spec["bounds"]["max"]
    if not (x1 > x0 and z1 > z0):
        problems.append("bounds max must exceed min")
    ids = [s.get("id") for s in spec["shots"]]
    if len(ids) != len(set(ids)):
        problems.append("duplicate shot ids")
    for shot in spec["shots"]:
        for key in ("id", "pos", "look_at", "fov", "zone"):
            if key not in shot:
                problems.append(f"shot {shot.get('id')} missing '{key}'")
    for side, wall in wall_segments(spec).items():
        (ax, az), (bx, bz) = wall["line"]
        length = abs(bx - ax) + abs(bz - az)
        for op in wall["openings"]:
            half = op["width"] / 2.0
            if op["center"] - half < 0 or op["center"] + half > length:
                problems.append(f"{side} opening at {op['center']} exceeds wall length {length}")
    return problems


def load(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = validate(spec)
    if problems:
        raise SpecError(f"{path}: " + "; ".join(problems))
    return spec


def load_all(rooms_dir: str | Path) -> dict[str, dict]:
    return {p.stem: load(p) for p in sorted(Path(rooms_dir).glob("*.json"))}
