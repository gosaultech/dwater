# damned_waters/tools/assets/polyhaven.py
# Purpose: fetch the CC0 textures and models the room sets use from Poly Haven (polyhaven.com),
# cache them outside git (pipeline_out/assets/polyhaven/), and keep a record of what was used and
# who made it (tools/assets/manifest.json). A RoomSpec names an asset as "ph:<id>": a material
# ("materials": {"floor": "ph:herringbone_parquet"} or {"ph": "...", "tint": [...]}) or a prop
# model ({"type": "model", "model": "ph:sofa_02"}). Blender reads only the cache (no network
# inside Blender); build_backgrounds.py runs `fetch` first, so the Mac downloads on first build.
#
# ELI5: a lending library for the set builder. The RoomSpec is the reading list; this goes and
# borrows each book once, keeps it on the shelf (the cache), and writes the authors in the ledger.
#
#   python3 tools/assets/polyhaven.py fetch            # everything the RoomSpecs name
#   python3 tools/assets/polyhaven.py fetch --res 2k   # sharper (final renders)
#
# Poly Haven assets are CC0 (public domain): no attribution is required; we record it anyway.
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CACHE = REPO / "pipeline_out" / "assets" / "polyhaven"
MANIFEST = HERE / "manifest.json"
API = "https://api.polyhaven.com"
UA = {"User-Agent": "damned-waters-set-builder/1.0"}
# Texture maps the set builder reads, by Poly Haven's map names.
MAPS = {"diff": "Diffuse", "rough": "Rough", "nor_gl": "nor_gl", "arm": "arm", "disp": "Displacement"}
# What the set kit (tools/blender/kit.py) falls back on when a prop names no material.
KIT_DEFAULTS = {"marble_01": "texture", "dark_wood": "texture"}


# ── Pure: what a RoomSpec asks for, and which files serve it ─────────────────────
def ref_id(value) -> str | None:
    """The asset id in a material or model reference ("ph:<id>" or {"ph": id}), else None."""
    if isinstance(value, str) and value.startswith("ph:"):
        return value[3:]
    if isinstance(value, dict) and isinstance(value.get("ph"), str):
        return value["ph"]
    return None


def references(spec: dict) -> dict[str, str]:
    """Every Poly Haven asset a RoomSpec names: {id: "texture" | "model"}."""
    out: dict[str, str] = {}

    def walk(v, kind):
        i = ref_id(v)
        if i:
            out.setdefault(i, kind)
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, "model" if k == "model" else kind)
        elif isinstance(v, list):
            for x in v:
                walk(x, kind)

    walk(spec.get("materials", {}), "texture")
    for p in spec.get("props", []):
        walk(p, "texture")
    for w in spec.get("walls", {}).values():
        walk(w, "texture")
    if isinstance(spec.get("exterior"), dict):
        walk(spec["exterior"], "texture")
    return out


def pick_texture(files: dict, res: str, fmt: str = "jpg") -> dict[str, dict]:
    """From the API's file list for a texture: {map: {"url", "md5"}} for the maps we use."""
    picked = {}
    for ours, theirs in MAPS.items():
        r = files.get(theirs, {}).get(res, {})
        f = r.get(fmt) or r.get("png")
        if f:
            picked[ours] = {"url": f["url"], "md5": f.get("md5", "")}
    return picked


def pick_model(files: dict, res: str) -> dict:
    """From the API's file list for a model: the glTF and every file it pulls in."""
    g = files.get("gltf", {}).get(res, {}).get("gltf")
    if not g:
        raise KeyError(f"no glTF at {res}")
    inc = {rel: {"url": f["url"], "md5": f.get("md5", "")} for rel, f in g.get("include", {}).items()}
    return {"gltf": {"url": g["url"], "md5": g.get("md5", "")}, "include": inc}


def local_name(url: str) -> str:
    return url.rsplit("/", 1)[-1]


# ── Network and cache ────────────────────────────────────────────────────────────
def _get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path, md5: str = "") -> Path:
    """Download once: a file already there with the right checksum is kept."""
    if dest.exists() and (not md5 or md5_of(dest) == md5):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    if md5 and md5_of(tmp) != md5:
        tmp.unlink()
        raise IOError(f"checksum mismatch for {url}")
    tmp.replace(dest)
    return dest


def ensure(asset_id: str, kind: str, res: str = "1k", cache: Path = CACHE) -> dict:
    """Fetch one asset into the cache; returns (and writes) its asset.json for Blender."""
    base = cache / asset_id / res
    meta_path = base / "asset.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    info = _get_json(f"{API}/info/{asset_id}")
    files = _get_json(f"{API}/files/{asset_id}")
    meta = {"id": asset_id, "kind": kind, "res": res, "name": info.get("name", asset_id),
            "authors": sorted(info.get("authors", {})), "license": "CC0",
            "dimensions_mm": info.get("dimensions"), "source": f"https://polyhaven.com/a/{asset_id}"}
    if kind == "model":
        m = pick_model(files, res)
        for rel, f in m["include"].items():
            fetch(f["url"], base / rel, f["md5"])
        gl = fetch(m["gltf"]["url"], base / local_name(m["gltf"]["url"]), m["gltf"]["md5"])
        meta["gltf"] = str(gl.relative_to(base))
    else:
        maps = pick_texture(files, res)
        if "diff" not in maps:
            raise KeyError(f"{asset_id}: no diffuse map at {res}")
        meta["maps"] = {}
        for k, f in maps.items():
            p = fetch(f["url"], base / local_name(f["url"]), f["md5"])
            meta["maps"][k] = str(p.relative_to(base))
    meta_path.write_text(json.dumps(meta, indent=1))
    return meta


def update_manifest(metas: list[dict], path: Path = MANIFEST) -> dict:
    """The ledger in git: every asset used, its licence and authors (sorted, so diffs stay quiet)."""
    m = json.loads(path.read_text()) if path.exists() else {"_file": "", "assets": {}}
    m["_file"] = ("damned_waters/tools/assets/manifest.json: the CC0 assets the room sets use "
                  "(written by tools/assets/polyhaven.py fetch).")
    for meta in metas:
        m["assets"][meta["id"]] = {"kind": meta["kind"], "name": meta["name"], "authors": meta["authors"],
                                   "license": meta["license"], "source": meta["source"]}
    m["assets"] = dict(sorted(m["assets"].items()))
    path.write_text(json.dumps(m, indent=1) + "\n")
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch the Poly Haven assets the RoomSpecs name.")
    ap.add_argument("cmd", choices=["fetch"])
    ap.add_argument("--res", default="1k")
    ap.add_argument("--specs", default=str(REPO / "game" / "data" / "rooms"))
    ap.add_argument("--extra", default="", help="more specs (files or dirs), comma separated")
    a = ap.parse_args(argv)
    wanted: dict[str, str] = dict(KIT_DEFAULTS)
    paths = [Path(a.specs)] + [Path(p) for p in a.extra.split(",") if p]
    for p in paths:
        for f in sorted(p.glob("*.json")) if p.is_dir() else [p]:
            for k, v in references(json.loads(f.read_text())).items():
                wanted.setdefault(k, v)
    metas = []
    for asset_id, kind in sorted(wanted.items()):
        print(f"[assets] {kind:7s} {asset_id}")
        metas.append(ensure(asset_id, kind, a.res))
    if metas:
        update_manifest(metas)
    print(f"[assets] {len(metas)} ready in {CACHE}")


if __name__ == "__main__":
    sys.exit(main())
