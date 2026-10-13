# damned_waters/tools/assets/photos.py
# Purpose: the photographs that go into the sets where modelling can't compete (packed shelves,
# bottles, clothes on a rail). Each is CC0, CC-BY or public domain (Openverse), listed with
# its author and licence in tools/assets/photos.json, cached outside git (pipeline_out/assets/photos/)
# and credited in docs/photo_credits.md. A RoomSpec prop names one by its id ("photo": "wine_rows").
# Blender reads only the cache, so fetch before rendering.
#
# ELI5: a set dresser's prop photos. Where building a thousand tiny bottles would take a week, a
# good photo of real bottles is pinned up behind the shelf edges, and the photographer is credited.
#
#   python3 tools/assets/photos.py fetch     # download what the manifest lists
#   python3 tools/assets/photos.py credits   # rewrite docs/photo_credits.md
import argparse
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CACHE = REPO / "pipeline_out" / "assets" / "photos"
MANIFEST = HERE / "photos.json"
CREDITS = REPO / "docs" / "photo_credits.md"
ALLOWED = {"cc0", "by", "pdm"}   # (no NC, ND or SA: those stay layout reference, outside the repo)
LICENCE_NAMES = {"cc0": "CC0 1.0", "by": "CC BY", "pdm": "Public Domain Mark"}


def manifest(path: Path = MANIFEST) -> dict:
    return {k: v for k, v in json.loads(path.read_text()).items() if not k.startswith("_")}


def path_of(pid: str, cache: Path = CACHE) -> Path:
    return cache / f"{pid}.jpg"


def references(spec: dict) -> set:
    """The photos a RoomSpec's props name (a "photo" on any prop)."""
    return {p["photo"] for p in spec.get("props", []) if isinstance(p.get("photo"), str)}


def fetch(cache: Path = CACHE) -> list:
    cache.mkdir(parents=True, exist_ok=True)
    got = []
    for pid, m in manifest().items():
        dest = path_of(pid, cache)
        if not dest.exists():
            req = urllib.request.Request(m["url"], headers={"User-Agent": "damned-waters-assets/1.0"})
            dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        got.append(dest)
    return got


def credits_md(m: dict) -> str:
    lines = ["# Photo credits", "",
             "Photographs used as texture in the pre-rendered sets (tools/assets/photos.json). Each is",
             "used as published, cropped and lit within the scene.", ""]
    for pid, e in sorted(m.items()):
        lic = LICENCE_NAMES[e["license"]] + (f" {e['license_version']}" if e["license"] == "by" and e.get("license_version") else "")
        lines.append(f"- **{pid}**: \"{e.get('title') or 'untitled'}\" by {e.get('creator') or 'unknown'}, {lic}, <{e['landing']}>")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch the set photos, or write their credits.")
    ap.add_argument("what", choices=["fetch", "credits"])
    a = ap.parse_args(argv)
    if a.what == "fetch":
        for p in fetch():
            print("[photos]", p)
    else:
        CREDITS.write_text(credits_md(manifest()))
        print("[photos] wrote", CREDITS)


if __name__ == "__main__":
    main()
