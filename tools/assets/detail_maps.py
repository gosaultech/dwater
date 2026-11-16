# damned_waters/tools/assets/detail_maps.py
# Purpose: build the small tiling "detail maps" the engine lays over its characters, guns and items
# (engine/assets/detail/<name>.png, in git: the game runs without this tool). The cast has no UVs:
# the shader lays each map on by where a point sits in the rest pose, three ways, so all a map has
# to do is tile.
#
# ELI5: a rubber stamp. The body is smooth clay; a stamp of real leather grain (or skin, or wood)
# is rolled over it wherever that material is, so close up it has the small-scale truth that noise
# never gets right. Leather, denim, cotton and walnut are stamps cut from real scans (Poly Haven,
# CC0); skin and worn gun metal are cut here, by rule.
#
# One layout for every map (RGBA, 8 bits):
#   R, G  the surface's slope, as a normal's x and y (0.5 = flat)
#   B     tone: how much lighter or darker than the material's own colour (0.5 = the same)
#   A     gloss: how smooth this spot is (1 = polished, 0 = dull); for metal, how worn the finish is
#
#   python3 tools/assets/detail_maps.py build            # every map (fetches the scans once)
#   python3 tools/assets/detail_maps.py build skin metal # just those
#
# Libraries: numpy (the maths), scipy (nearest-neighbour search for the skin's cells, blurs),
# Pillow (reading scans, drawing scratches, writing PNGs), sqlite3 (the run log).
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = REPO / "engine" / "assets" / "detail"
LOG = REPO / "pipeline_out" / "assets" / "detail_maps.db"

# name -> where it comes from, its size in pixels, and how many metres one tile covers on the body
# (engine/include/dw/detail.hpp says the same; a test holds them together).
MAPS = {
    "skin":    {"make": "skin", "size": 512, "tile": 0.024},
    "leather": {"scan": "brown_leather", "size": 1024, "tile": 0.3},
    "denim":   {"scan": "denim_fabric_04", "size": 512, "tile": 0.3},
    "cotton":  {"scan": "cotton_jersey", "size": 512, "tile": 0.3},
    "walnut":  {"scan": "american_walnut_veneer", "size": 1024, "tile": 1.0, "contrast": 1.7},
    "metal":   {"make": "metal", "size": 512, "tile": 0.08},
}


# ── Pure: packing, and noise that tiles ──────────────────────────────────────────
def slopes(height: np.ndarray, tile_m: float) -> tuple[np.ndarray, np.ndarray]:
    """dh/du and dh/dv of a height field (metres) that wraps round, u to the right, v UP the image
    (as OpenGL reads it: the image's last row is v = 0)."""
    n = height.shape[0]
    px = tile_m / n
    du = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) / (2 * px)
    dv = (np.roll(height, 1, axis=0) - np.roll(height, -1, axis=0)) / (2 * px)
    return du, dv


def pack(du: np.ndarray, dv: np.ndarray, tone: np.ndarray, gloss: np.ndarray) -> np.ndarray:
    """Slopes, tone (1 = unchanged) and gloss (0..1) as the RGBA bytes the shader reads."""
    inv = 1.0 / np.sqrt(du * du + dv * dv + 1.0)
    rgba = np.stack([-du * inv * 0.5 + 0.5, -dv * inv * 0.5 + 0.5, np.clip(tone * 0.5, 0, 1), np.clip(gloss, 0, 1)], axis=-1)
    return np.clip(np.rint(rgba * 255), 0, 255).astype(np.uint8)


def unpack_slopes(rgba: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """What the shader recovers from R and G (pack's inverse, to 8 bits)."""
    x, y = rgba[..., 0] / 255.0 * 2 - 1, rgba[..., 1] / 255.0 * 2 - 1
    z = np.sqrt(np.clip(1 - x * x - y * y, 0.02, 1))
    return -x / z, -y / z


def tiling_noise(n: int, falloff: float, seed: int, low: float = 0.0) -> np.ndarray:
    """Noise that wraps round, 0..1: random numbers filtered in frequency space (which is periodic
    by nature), each frequency f weighted 1 / f^falloff; `low` drops the waves longer than 1/low."""
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    f = np.sqrt(f) * n
    w = np.where(f > max(low, 0.5), 1.0 / np.maximum(f, 1e-6) ** falloff, 0.0)
    x = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * w))
    lo, hi = np.percentile(x, [0.5, 99.5])
    return np.clip((x - lo) / (hi - lo), 0, 1)


def cell_edges(n: int, cells: int, seed: int, warp: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """A honeycomb of `cells` irregular cells that wraps round: for every pixel, how far it is from
    its cell's wall (F2 - F1, in tiles) and from its cell's seed (F1). `warp` (tiles) bends the
    walls, so they read as creases in something soft rather than cracks in something hard."""
    rng = np.random.default_rng(seed)
    pts = rng.random((cells, 2))
    g = (np.arange(n) + 0.5) / n
    q = np.stack(np.meshgrid(g, g), axis=-1)
    if warp > 0:
        low = np.sqrt(cells) * 0.7   # bends a little longer than a cell
        q = q + warp * (np.stack([tiling_noise(n, 2.0, seed + 101, low), tiling_noise(n, 2.0, seed + 102, low)], axis=-1) - 0.5) * 2
    q = (q % 1.0).reshape(-1, 2)
    d, _ = cKDTree(pts, boxsize=1.0).query(q, k=2)
    return (d[:, 1] - d[:, 0]).reshape(n, n), d[:, 0].reshape(n, n)


def seam(a: np.ndarray) -> float:
    """How much rougher the map is across its wrap than inside it (about 1 = it tiles)."""
    a = a.astype(np.float64)
    inside = np.mean(np.abs(np.diff(a, axis=1))) + np.mean(np.abs(np.diff(a, axis=0)))
    across = np.mean(np.abs(a[:, 0] - a[:, -1])) + np.mean(np.abs(a[0, :] - a[-1, :]))
    return float(across / max(inside, 1e-9))


# ── The generated maps ───────────────────────────────────────────────────────────
def skin(n: int, tile_m: float, seed: int = 7) -> np.ndarray:
    """Skin close up: a net of fine furrows round small plateaus, deeper lines every few of them,
    pores sunk where furrows meet. Slightly larger than life, as game skin is, so it survives the
    distance the camera keeps."""
    mm = 0.001 / tile_m   # one millimetre, in tiles
    fine, _ = cell_edges(n, int(1.0 / (0.6 * mm) ** 2), seed, warp=0.35 * mm)
    coarse, _ = cell_edges(n, int(1.0 / (1.9 * mm) ** 2), seed + 1, warp=0.9 * mm)
    fa = np.exp(-(fine / (0.07 * mm)) ** 2)
    fb = np.exp(-(coarse / (0.1 * mm)) ** 2) * (0.35 + 0.65 * tiling_noise(n, 1.8, seed + 6))   # some lines deeper than others
    _, pore = cell_edges(n, int(1.0 / (1.1 * mm) ** 2), seed + 2)
    pores = np.exp(-(pore / (0.09 * mm)) ** 2)
    grain = tiling_noise(n, 1.0, seed + 3, low=n / 24)
    height = gaussian_filter(-(0.5 * fa + 0.9 * fb + 0.9 * pores) * 0.00006 + (grain - 0.5) * 0.00002, 0.8, mode="wrap")
    du, dv = slopes(height, tile_m)
    tone = 1.0 - 0.1 * fa - 0.16 * fb - 0.28 * pores + (tiling_noise(n, 1.6, seed + 4) - 0.5) * 0.12
    tone = gaussian_filter(tone, 0.6, mode="wrap")
    gloss = np.clip(1.0 - 0.5 * np.maximum(fa, fb) - 0.9 * pores, 0, 1) * (0.75 + 0.25 * tiling_noise(n, 1.8, seed + 5))
    return pack(du, dv, tone / tone.mean(), gloss)


def metal(n: int, tile_m: float, seed: int = 11) -> np.ndarray:
    """A gun that has been carried: fine scratches (most along the part, the way it is drawn from a
    holster and wiped down), pin-prick pits, and patches where the finish has rubbed thin."""
    rng = np.random.default_rng(seed)
    canvas = Image.new("F", (n, n), 0.0)
    draw = ImageDraw.Draw(canvas)
    for _ in range(280):
        x, y = rng.random(2) * n
        ang = rng.normal(0.0, 0.45) + (np.pi / 2 if rng.random() < 0.12 else 0.0)
        ln = n * rng.uniform(0.02, 0.4) * rng.random()
        dx, dy = np.cos(ang) * ln, np.sin(ang) * ln
        depth = float(rng.uniform(0.25, 1.0))
        for ox in (-n, 0, n):        # drawn again a tile over, so a scratch off one edge comes in at the other
            for oy in (-n, 0, n):
                draw.line([(x + ox, y + oy), (x + dx + ox, y + dy + oy)], fill=depth, width=1)
    scratch = gaussian_filter(np.asarray(canvas, dtype=np.float64), 0.6, mode="wrap")
    scratch = np.clip(scratch / max(scratch.max(), 1e-9) * 1.6, 0, 1)
    _, pit = cell_edges(n, 900, seed + 1)
    pits = np.exp(-(pit * n / 1.1) ** 2) * (tiling_noise(n, 2.0, seed + 2) > 0.45)
    rubbed = np.clip((tiling_noise(n, 2.2, seed + 3) - 0.52) * 4.0, 0, 1)
    height = -(scratch * 0.000012 + pits * 0.00003) + (tiling_noise(n, 0.6, seed + 4, low=n / 6) - 0.5) * 0.000004
    du, dv = slopes(height, tile_m)
    tone = 1.0 + 0.5 * scratch - 0.3 * pits + (tiling_noise(n, 1.7, seed + 5) - 0.5) * 0.25
    wear = np.clip(0.75 * rubbed + 0.85 * scratch, 0, 1)
    return pack(du, dv, tone / tone.mean(), wear)


# ── A scan, repacked ─────────────────────────────────────────────────────────────
def from_scan(diff: np.ndarray, nor: np.ndarray, rough: np.ndarray, contrast: float = 1.0) -> np.ndarray:
    """A scanned material (colour, OpenGL normal map and roughness, floats 0..1) in the engine's
    layout: its own slopes; its colour kept only as light-and-dark round its average (the character
    brings the colour); its roughness turned over into gloss."""
    lum = diff[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    lum = lum ** 2.2
    tone = 1.0 + (lum / max(lum.mean(), 1e-6) - 1.0) * contrast
    rgba = np.stack([nor[..., 0], nor[..., 1], np.clip(tone * 0.5, 0, 1), 1.0 - rough], axis=-1)
    return np.clip(np.rint(rgba * 255), 0, 255).astype(np.uint8)


def _scan_map(asset: str, size: int, contrast: float) -> np.ndarray:
    sys.path.insert(0, str(HERE))
    import polyhaven   # noqa: E402 (the lending library: fetches once, keeps the ledger)
    meta = polyhaven.ensure(asset, "texture", "1k")
    polyhaven.update_manifest([meta])
    base = polyhaven.CACHE / asset / "1k"

    def load(key: str, mode: str) -> np.ndarray:
        return np.asarray(Image.open(base / meta["maps"][key]).convert(mode).resize((size, size), Image.LANCZOS), dtype=np.float64) / 255.0
    return from_scan(load("diff", "RGB"), load("nor_gl", "RGB"), load("rough", "L"), contrast)


def build(name: str, out: Path = OUT) -> Path:
    spec = MAPS[name]
    if "scan" in spec:
        rgba = _scan_map(spec["scan"], spec["size"], spec.get("contrast", 1.0))
    else:
        rgba = {"skin": skin, "metal": metal}[spec["make"]](spec["size"], spec["tile"])
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.png"
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)
    return path


def _log(started: float, names: list[str], status: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(LOG) as db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_ts REAL, maps TEXT, "
                   "runtime_ms REAL, exit_status TEXT)")
        db.execute("INSERT INTO runs (run_ts, maps, runtime_ms, exit_status) VALUES (?, ?, ?, ?)",
                   (started, ",".join(names), (time.time() - started) * 1000, status))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the engine's tiling detail maps.")
    ap.add_argument("command", choices=["build"])
    ap.add_argument("names", nargs="*", help="which maps (default: all)")
    args = ap.parse_args(argv)
    names = args.names or list(MAPS)
    started, status = time.time(), "ok"
    try:
        for name in names:
            p = build(name)
            print(f"{name}: {p.relative_to(REPO)} ({p.stat().st_size // 1024} KB)")
    except Exception as e:   # noqa: BLE001 (logged, then raised)
        status = f"error: {e}"
        raise
    finally:
        _log(started, names, status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
