# damned_waters/tools/characters/build_characters.py
# Purpose: build the cast from MakeHuman's CC0 data into engine/assets/characters/*.dwc.
#   python3 tools/characters/build_characters.py              # every character
#   python3 tools/characters/build_characters.py survivor     # just one
# The first run clones the pinned MakeHuman data into tools/characters/.cache (~130 MB).
# Every run is logged to tools/characters/builds.db (SQLite): what was built, how big, how long.
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import dwc
import mhdata
from cast import CAST

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "engine" / "assets" / "characters"
DB = Path(__file__).resolve().parent / "builds.db"


def log_build(name: str, ch: dwc.Character, path: Path, seconds: float, status: str):
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS builds(id INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER, character TEXT,"
                " status TEXT, parts INTEGER, vertices INTEGER, triangles INTEGER, bytes INTEGER, seconds REAL)")
    v = sum(len(p.pos) for p in ch.parts) if ch else 0
    t = sum(len(p.tris) for p in ch.parts) if ch else 0
    con.execute("INSERT INTO builds(at, character, status, parts, vertices, triangles, bytes, seconds) VALUES(?,?,?,?,?,?,?,?)",
                (int(time.time()), name, status, len(ch.parts) if ch else 0, v, t, path.stat().st_size if path.exists() else 0, seconds))
    con.commit()
    con.close()


def main(argv: list[str]) -> int:
    data = mhdata.fetch()
    names = argv or list(CAST)
    for name in names:
        t0 = time.perf_counter()
        path = OUT / f"{name}.dwc"
        try:
            ch = CAST[name](data)
            dwc.write(path, ch)
            status = "ok"
        except Exception:
            log_build(name, None, path, time.perf_counter() - t0, "failed")
            raise
        dt = time.perf_counter() - t0
        log_build(name, ch, path, dt, status)
        print(f"{name}: {len(ch.parts)} parts, {sum(len(p.pos) for p in ch.parts)} vertices, "
              f"{path.stat().st_size / 1e6:.2f} MB, {dt:.1f} s -> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
