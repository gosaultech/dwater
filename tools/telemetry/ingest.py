# damned_waters/tools/telemetry/ingest.py
# Purpose: load the game's telemetry (JSON lines written by
# game/src/core/telemetry.gd) into SQLite, and report on playtests.
#   python3 tools/telemetry/ingest.py ingest          # idempotent, run any time
#   python3 tools/telemetry/ingest.py report          # per-session combat summary
# Idempotent via PRIMARY KEY(session_id, seq) + INSERT OR IGNORE: re-running
# never double counts. Each ingest run is itself logged (ingest_runs).
from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import sys
import time
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "damned_waters.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY, started_ts REAL, ended_ts REAL, status TEXT,
  runtime_s REAL, godot TEXT, os TEXT, renderer TEXT, build TEXT);
CREATE TABLE IF NOT EXISTS events (
  session_id TEXT NOT NULL, seq INTEGER NOT NULL, ts REAL, t_ms INTEGER,
  event TEXT NOT NULL, data TEXT, PRIMARY KEY (session_id, seq));
CREATE INDEX IF NOT EXISTS events_by_type ON events(event);
CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_ts REAL, source TEXT, files INTEGER,
  events_added INTEGER, runtime_ms REAL, exit_status TEXT);
"""


def default_source() -> Path:
    home = Path.home()
    base = {
        "Darwin": home / "Library/Application Support/Godot/app_userdata",
        "Windows": Path(os.environ.get("APPDATA", home)) / "Godot/app_userdata",
    }.get(platform.system(), home / ".local/share/godot/app_userdata")
    return base / "Damned Waters" / "telemetry"


def connect(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


def ingest(con: sqlite3.Connection, source: Path) -> tuple[int, int]:
    files, added = 0, 0
    for f in sorted(source.glob("*.jsonl")):
        files += 1
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn final line from a crash: skip, don't fail
            cur = con.execute("INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?)",
                              (e["session"], e["seq"], e.get("ts"), e.get("t_ms"), e["event"], json.dumps(e.get("data", {}))))
            added += cur.rowcount
            d = e.get("data", {})
            if e["event"] == "session_start":
                con.execute("INSERT OR IGNORE INTO sessions(session_id, started_ts, godot, os, renderer, build) VALUES (?,?,?,?,?,?)",
                            (e["session"], e.get("ts"), d.get("godot"), d.get("os"), d.get("renderer"), d.get("build")))
            elif e["event"] == "session_end":
                con.execute("UPDATE sessions SET ended_ts=?, status=?, runtime_s=? WHERE session_id=?",
                            (e.get("ts"), d.get("status"), d.get("runtime_s"), e["session"]))
    con.commit()
    return files, added


REPORT_SQL = """
SELECT e.session_id,
  SUM(e.event = 'shot') AS shots,
  SUM(e.event = 'shot' AND json_extract(e.data, '$.hit')) AS hits,
  SUM(e.event = 'enemy_killed') AS kills,
  SUM(e.event = 'death') AS deaths,
  SUM(e.event = 'damage') AS times_hit,
  MAX(CASE WHEN e.event = 'perf' THEN json_extract(e.data, '$.worst_frame_ms') END) AS worst_frame_ms,
  MAX(e.event = 'demo_complete') AS completed
FROM events e GROUP BY e.session_id ORDER BY MIN(e.ts)
"""


def report(con: sqlite3.Connection) -> list[dict]:
    cols = ["session", "shots", "hits", "kills", "deaths", "times_hit", "worst_frame_ms", "completed"]
    rows = [dict(zip(cols, r)) for r in con.execute(REPORT_SQL)]
    for r in rows:
        r["accuracy"] = round(100.0 * (r["hits"] or 0) / r["shots"], 1) if r["shots"] else None
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["ingest", "report"])
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--source", type=Path, default=default_source())
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    con = connect(a.db)
    status = "ok"
    try:
        if a.command == "ingest":
            files, added = ingest(con, a.source)
            print(f"ingested {added} new events from {files} file(s) in {a.source}")
        else:
            files, added = 0, 0
            for r in report(con):
                print(f"{r['session']}: shots {r['shots']} acc {r['accuracy']}% kills {r['kills']} "
                      f"deaths {r['deaths']} worst frame {r['worst_frame_ms']} ms completed={bool(r['completed'])}")
    except Exception as exc:  # recorded, then re-raised: the log never hides a failure
        status = f"error: {exc}"
        raise
    finally:
        con.execute("INSERT INTO ingest_runs(run_ts, source, files, events_added, runtime_ms, exit_status) VALUES (?,?,?,?,?,?)",
                    (time.time(), str(a.source), locals().get("files", 0), locals().get("added", 0),
                     (time.perf_counter() - t0) * 1000.0, f"{a.command}:{status}"))
        con.commit()
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
