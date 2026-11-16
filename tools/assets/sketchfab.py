# damned_waters/tools/assets/sketchfab.py
# Purpose: bring licensed 3D models (cars, vans, bicycles, street furniture) from Sketchfab into the
# set builder's cache, and keep the ledger of who made each one. Only CC0 and CC BY models pass the
# gate (the project's rule for pixels, applied to meshes); anything else is refused before a byte
# is downloaded. The models themselves live outside git (pipeline_out/assets/sketchfab/<key>/, each
# in its own directory: downloads are untrusted data); what is committed is the ledger
# (tools/assets/models.json) and the credits it writes (docs/model_credits.md).
#
#   python3 tools/assets/sketchfab.py search "delivery van" [--sheet sheet.jpg]   # look for candidates
#   python3 tools/assets/sketchfab.py add <key> <uid> [--role car]                # put one in the ledger
#   python3 tools/assets/sketchfab.py fetch [key ...]                             # download what the ledger names
#   python3 tools/assets/sketchfab.py credits                                     # rewrite docs/model_credits.md
#
# The API token is never in this file or the environment: the cloud environment's network proxy
# adds it to requests for api.sketchfab.com. Every run is logged to a small SQLite file in the
# cache (usage.db: when, what, how many, how long, how it ended).
#
# ELI5: a prop house with a strict doorman. You ask for "a van"; the doorman only lets in vans
# whose owners said "anyone may use this, just say my name" - and writes every name in the book.
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CACHE = REPO / "pipeline_out" / "assets" / "sketchfab"
LEDGER = HERE / "models.json"
CREDITS = REPO / "docs" / "model_credits.md"
API = "https://api.sketchfab.com/v3"
UA = {"User-Agent": "set-builder-asset-fetch/1.0"}
# Sketchfab's licence labels -> what we may do with them. Nothing else passes.
ALLOWED = {"CC Attribution": "CC BY 4.0", "CC0 Public Domain": "CC0 1.0"}
LICENCE_URL = {"CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/", "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/"}


def licence_of(model: dict) -> str | None:
    """Our name for a model's licence ("CC BY 4.0", "CC0 1.0"), or None if it is not one we may use."""
    lic = model.get("license")
    label = lic.get("label", "") if isinstance(lic, dict) else str(lic or "")
    return ALLOWED.get(label)


def pick_archive(download: dict) -> tuple[str, str]:
    """Which of a model's download formats to take: (kind, url). A single binary glTF if there is
    one, else the zipped glTF; never the author's source file (any format, any size)."""
    for kind in ("glb", "gltf"):
        if (download.get(kind) or {}).get("url"):
            return kind, download[kind]["url"]
    raise ValueError("no glTF download offered")


def entry(key: str, model: dict, role: str = "") -> dict:
    """A ledger line for a model the gate let in (raises if its licence is not CC0 or CC BY)."""
    lic = licence_of(model)
    if lic is None:
        raise ValueError(f"{key}: licence {model.get('license')!r} is not CC0 or CC BY")
    user = model.get("user") or {}
    return {"uid": model["uid"], "title": model.get("name", ""), "author": user.get("displayName") or user.get("username", ""),
            "author_url": user.get("profileUrl", ""), "licence": lic, "url": model.get("viewerUrl", f"https://sketchfab.com/3d-models/{model['uid']}"),
            "faces": model.get("faceCount", 0), "role": role}


def credit_lines(ledger: dict) -> list[str]:
    """docs/model_credits.md, line by line: every model, its author, its licence, what we changed."""
    out = ["<!-- damned_waters/docs/model_credits.md: who made the licensed 3D models in the sets. Written by tools/assets/sketchfab.py credits; do not edit by hand. -->",
           "# Model credits", "",
           "The licensed models in the backgrounds come from Sketchfab under CC BY 4.0 or CC0. Each was changed for the game:",
           "scaled, weathered by the set's flood and grime, makers' badges removed, and given an invented livery where it has one.", "",
           "| Model | Author | Licence | Used as |", "|---|---|---|---|"]
    for key in sorted(k for k in ledger if not k.startswith("_")):
        e = ledger[key]
        author = f"[{e['author']}]({e['author_url']})" if e.get("author_url") else e["author"]
        out.append(f"| [{e['title']}]({e['url']}) | {author} | [{e['licence']}]({LICENCE_URL[e['licence']]}) | {e.get('role') or key} |")
    return out + [""]


def safe_members(names: list[str]) -> list[str]:
    """The archive's members that stay inside the directory they are unpacked into."""
    return [n for n in names if not n.startswith(("/", "\\")) and ".." not in Path(n).parts and ":" not in n]


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read())


def _download(url: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    return dest.stat().st_size


def load_ledger(path: Path = LEDGER) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"_file": "damned_waters/tools/assets/models.json - the licensed 3D models the sets use (tools/assets/sketchfab.py): "
                     "Sketchfab uid, title, author, licence (CC0 or CC BY only), and what each is used as."}


def save_ledger(ledger: dict, path: Path = LEDGER) -> None:
    path.write_text(json.dumps(ledger, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def model_path(key: str, cache: Path = CACHE) -> Path | None:
    """The cached model's file (a .glb, or the unzipped scene.gltf), if it has been fetched."""
    d = cache / key
    for cand in sorted(d.glob("*.glb")) + sorted(d.glob("*.gltf")) + sorted(d.glob("*/*.gltf")):
        return cand
    return None


def search(query: str, count: int = 24) -> list[dict]:
    """Downloadable models for a query that pass the licence gate, most liked first."""
    q = urllib.parse.urlencode({"type": "models", "q": query, "downloadable": "true", "count": count, "sort_by": "-likeCount"})
    out = []
    for m in _get_json(f"{API}/search?{q}").get("results", []):
        if licence_of(m):
            thumbs = sorted((m.get("thumbnails") or {}).get("images", []), key=lambda t: abs(t.get("width", 0) - 400))
            out.append({"uid": m["uid"], "name": m["name"], "licence": licence_of(m), "faces": m.get("faceCount") or 0, "likes": m.get("likeCount") or 0,
                        "author": (m.get("user") or {}).get("username", ""), "thumb": thumbs[0]["url"] if thumbs else ""})
    return out


def sheet(found: list[dict], out: Path, cache: Path = CACHE) -> None:
    """A contact sheet of candidates' preview pictures, each labelled with its uid's start and name."""
    from PIL import Image, ImageDraw
    tiles = []
    for c in found:
        if not c["thumb"]:
            continue
        f = cache / "_thumbs" / f"{c['uid']}.jpg"
        if not f.exists():
            _download(c["thumb"], f)
        im = Image.open(f).convert("RGB").resize((400, 225))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 400, 15), fill=(0, 0, 0))
        d.text((3, 2), f"{c['uid'][:8]} {c['name'][:40]} | {c['faces'] // 1000}k", fill=(255, 230, 120))
        tiles.append(im)
    cols = 3
    sh = Image.new("RGB", (400 * cols, 225 * max(1, (len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % cols) * 400, (i // cols) * 225))
    out.parent.mkdir(parents=True, exist_ok=True)
    sh.save(out, quality=82)


def fetch(key: str, e: dict, cache: Path = CACHE) -> Path:
    """Download one ledger model into its own directory (skipped if it is already there)."""
    have = model_path(key, cache)
    if have:
        return have
    if licence_of(_get_json(f"{API}/models/{e['uid']}")) is None:   # (a licence can change after a model was added)
        raise ValueError(f"{key}: no longer CC0 or CC BY on Sketchfab")
    kind, url = pick_archive(_get_json(f"{API}/models/{e['uid']}/download"))
    d = cache / key
    if kind == "glb":
        _download(url, d / f"{e['uid']}.glb")
    else:
        z = d / f"{e['uid']}.zip"
        _download(url, z)
        with zipfile.ZipFile(z) as zf:
            zf.extractall(d / "gltf", members=safe_members(zf.namelist()))
        z.unlink()
    return model_path(key, cache)


def _log(cache: Path, command: str, detail: str, count: int, started: float, status: str) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(cache / "usage.db") as db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_ts REAL, command TEXT, detail TEXT, "
                   "models INTEGER, runtime_ms REAL, exit_status TEXT)")
        db.execute("INSERT INTO runs (run_ts, command, detail, models, runtime_ms, exit_status) VALUES (?, ?, ?, ?, ?, ?)",
                   (started, command, detail, count, (time.time() - started) * 1000, status))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Licensed models from Sketchfab (CC0 / CC BY only).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query", nargs="+")
    s.add_argument("--sheet")
    a = sub.add_parser("add")
    a.add_argument("key")
    a.add_argument("uid")
    a.add_argument("--role", default="")
    f = sub.add_parser("fetch")
    f.add_argument("keys", nargs="*")
    sub.add_parser("credits")
    args = ap.parse_args(argv)
    started, count, status, detail = time.time(), 0, "ok", ""
    try:
        if args.cmd == "search":
            detail = " ".join(args.query)
            found = [c for q in args.query for c in search(q)]
            count = len(found)
            for c in found:
                print(f"{c['uid']} {c['licence']:9} {c['faces']:>8} faces {c['likes']:>5} likes  {c['name'][:50]}  ({c['author']})")
            if args.sheet:
                sheet(found, Path(args.sheet))
        elif args.cmd == "add":
            ledger = load_ledger()
            ledger[args.key] = entry(args.key, _get_json(f"{API}/models/{args.uid}"), args.role)
            save_ledger(ledger)
            detail, count = args.key, 1
            print(f"[models] {args.key}: {ledger[args.key]['title']} by {ledger[args.key]['author']} ({ledger[args.key]['licence']})")
        elif args.cmd == "fetch":
            ledger = load_ledger()
            keys = args.keys or [k for k in ledger if not k.startswith("_")]
            detail = ",".join(keys)
            for key in keys:
                p = fetch(key, ledger[key])
                count += 1
                print(f"[models] {key}: {p.relative_to(REPO)} ({p.stat().st_size // 1024} KB)")
        else:
            ledger = load_ledger()
            CREDITS.write_text("\n".join(credit_lines(ledger)))
            count = len([k for k in ledger if not k.startswith("_")])
            print(f"[models] {count} credited in {CREDITS.relative_to(REPO)}")
    except Exception as exc:   # (logged, then reported: the run's record must say how it ended)
        status = f"error: {exc}"
        print(f"[models] {status}", file=sys.stderr)
    _log(CACHE, args.cmd, detail, count, started, status)
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
