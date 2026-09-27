# damned_waters/tools/pipeline/build_backgrounds.py
# Purpose: the one command you run after editing a RoomSpec or the Blender kit.
#   python3 tools/pipeline/build_backgrounds.py --quality final --gpu
# 1) runs Blender headless on tools/blender/render_rooms.py
# 2) packs the renders into game/assets/rooms/ (depth_pack.py)
# Then reopen/refocus Godot: it re-imports the changed PNGs automatically.
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import depth_pack  # noqa: E402

CANDIDATES = {
    "Darwin": ["/Applications/Blender.app/Contents/MacOS/Blender"],
    "Windows": [r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"],
    "Linux": ["/usr/bin/blender", "/snap/bin/blender"],
}


def find_blender(explicit: str | None) -> str:
    for c in [explicit, os.environ.get("BLENDER"), shutil.which("blender"),
              *CANDIDATES.get(platform.system(), [])]:
        if c and Path(c).exists():
            return c
    raise SystemExit("Blender not found. Set BLENDER=/path/to/blender or pass --blender.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quality", default="final", choices=["preview", "ship", "final"])
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--rooms", default="")
    ap.add_argument("--shots", default="")
    ap.add_argument("--gpu", action="store_true")
    ap.add_argument("--blender", default=None)
    ap.add_argument("--skip-render", action="store_true", help="only re-pack existing renders")
    a = ap.parse_args()
    out = REPO / "pipeline_out" / "renders"
    if not a.skip_render:
        cmd = [find_blender(a.blender), "-b", "--factory-startup", "-P",
               str(REPO / "tools" / "blender" / "render_rooms.py"), "--",
               "--quality", a.quality, "--res", a.res, "--out", str(out)]
        if a.rooms:
            cmd += ["--rooms", a.rooms]
        if a.shots:
            cmd += ["--shots", a.shots]
        if a.gpu:
            cmd.append("--gpu")
        print("[build]", " ".join(cmd))
        subprocess.run(cmd, check=True)
    depth_pack.main(["--src", str(out), "--game", str(REPO / "game")])


if __name__ == "__main__":
    main()
