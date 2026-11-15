#!/usr/bin/env python3
# damned_waters/tools/dev/commit_room.py
# Purpose: bring one re-rendered room into the repo the way the project's rule asks: a room joins a
# look (catastrophe.DRESSED, catastrophe.LOOK2) in the same commit as the plates that show it. Adds
# the room to those sets, runs the generator's tests (the committed spec must match a rebuild),
# commits the plates, the spec and the generator, and pushes. Used by hand or by auto_commit.sh
# after render_queue.sh logs "ok <room>".
#
#   python3 tools/dev/commit_room.py <room> "<what the plates now show>"
#
# ELI5: the stage manager's sign-off. A new backdrop only goes up once the prop list has been
# updated to match it, and the list is checked before the curtain.
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GEN = REPO / "tools" / "citygen" / "catastrophe.py"
TRAILER = "Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_018Fg2TGhREH4MYXioixRmNn"


def add_to_set(source: str, name: str, room: str) -> str:
    """The generator's source with `room` in the set literal assigned to `name` (kept sorted)."""
    m = re.search(rf"^{name} = (set\(\)|\{{[^}}]*\}})", source, flags=re.M)
    if not m:
        raise ValueError(f"no set {name} in the generator")
    have = set(re.findall(r'"([a-z0-9_]+)"', m.group(1)))
    have.add(room)
    literal = "{" + ", ".join(f'"{r}"' for r in sorted(have)) + "}"
    return source[:m.start(1)] + literal + source[m.end(1):]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)


def main(argv: list[str]) -> int:
    room, what = argv[1], (argv[2] if len(argv) > 2 else "the second look")
    before = GEN.read_text()
    after = add_to_set(add_to_set(before, "DRESSED", room), "LOOK2", room)
    GEN.write_text(after)
    tests = subprocess.run([sys.executable, "-m", "unittest", "tests.test_catastrophe", "tests.test_cameras"],
                           cwd=REPO / "tools" / "citygen", capture_output=True, text=True)
    if tests.returncode != 0:
        GEN.write_text(before)   # (nothing half-done: the sets go back)
        print(f"[commit_room] {room}: tests failed, not committed\n{tests.stderr[-1500:]}")
        return 1
    run(["git", "add", f"game/assets/rooms/{room}", f"game/data/rooms/{room}.json", "tools/citygen/catastrophe.py"])
    msg = f"Plates: {room} re-rendered at 2048x1152 ({what})\n\n{TRAILER}"
    c = run(["git", "commit", "-q", "-m", msg])
    if c.returncode != 0:
        print(f"[commit_room] {room}: nothing committed\n{c.stdout[-500:]}{c.stderr[-500:]}")
        return 1
    for wait in (0, 2, 4, 8, 16):
        if wait:
            import time
            time.sleep(wait)
        p = run(["git", "push", "-q", "-u", "origin", "claude/bold-ritchie-dow5ha"])
        if p.returncode == 0:
            break
    print(f"[commit_room] {room}: committed" + ("" if p.returncode == 0 else " (push failed: push by hand)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
