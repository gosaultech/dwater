# damned_waters/tools/telemetry/tests/test_ingest.py
# Purpose: ingest is idempotent, tolerant of torn lines, and reports correctly.
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest  # noqa: E402


def ev(seq, event, data=None):
    return json.dumps({"v": 1, "session": "s1", "seq": seq, "ts": 1000.0 + seq, "t_ms": seq * 10, "event": event, "data": data or {}})


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        lines = [ev(1, "session_start", {"os": "macOS"}), ev(2, "shot", {"hit": True}), ev(3, "shot", {"hit": False}),
                 ev(4, "enemy_killed", {"enemy": "zwerver"}), ev(5, "perf", {"worst_frame_ms": 9.5}),
                 ev(6, "session_end", {"status": "clean", "runtime_s": 42.0}), '{"torn": ']
        (self.tmp / "s1.jsonl").write_text("\n".join(lines))
        self.con = ingest.connect(self.tmp / "t.db")

    def test_idempotent(self):
        self.assertEqual(ingest.ingest(self.con, self.tmp), (1, 6))
        self.assertEqual(ingest.ingest(self.con, self.tmp), (1, 0))

    def test_session_lifecycle(self):
        ingest.ingest(self.con, self.tmp)
        status, runtime = self.con.execute("SELECT status, runtime_s FROM sessions").fetchone()
        self.assertEqual((status, runtime), ("clean", 42.0))

    def test_report(self):
        ingest.ingest(self.con, self.tmp)
        r = ingest.report(self.con)[0]
        self.assertEqual((r["shots"], r["hits"], r["kills"], r["accuracy"], r["worst_frame_ms"]), (2, 1, 1, 50.0, 9.5))


if __name__ == "__main__":
    unittest.main()
