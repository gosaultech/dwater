# damned_waters/tools/assets/decals.py
# Purpose: the paint and paper the survivors and the rescuers left on the city's walls, made as
# textures (RGBA PNGs, transparent round the paint) for the sets: words sprayed in a hurry ("spray":
# each letter a little off, the paint misted round it and run down in drips), the search team's X
# on a door ("xcode": the date in the top, the team on the left, the hazard on the right, the dead
# below), and notices pasted up and rained on ("poster": an official notice or a missing person).
# A RoomSpec prop names its decal inline ({"type": "spray", "decal": {"style": "spray", "text": ...,
# "id": ...}}); `make` draws every decal the RoomSpecs name into the asset cache, outside git
# (pipeline_out/assets/decals/<id>.png), where tools/blender/ruin.py reads them. All the words are
# invented; no real organisation's marks.
#
# ELI5: a sign-writer's shop that paints every message the script calls for, once, and keeps them
# on a shelf for the set dressers.
#
#   python3 tools/assets/decals.py make      # every decal the RoomSpecs name
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[2]
ROOMS = REPO / "game" / "data" / "rooms"
CACHE = REPO / "pipeline_out" / "assets" / "decals"
FONTS = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
         Path("/Library/Fonts/Arial Bold.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
         Path("C:/Windows/Fonts/arialbd.ttf")]
SERIF = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"), Path("/Library/Fonts/Georgia Bold.ttf")]
PX = 1024   # the long side, in pixels


def decal_id(spec: dict) -> str:
    """A decal's name: the same words, style, colour and seed always make the same file."""
    body = {k: v for k, v in spec.items() if k != "id"}
    return hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]


def _font(size: int, serif: bool = False):
    for f in (SERIF if serif else []) + FONTS:
        if f.exists():
            return ImageFont.truetype(str(f), size)
    return ImageFont.load_default()


def _rgb(c) -> tuple:
    return tuple(int(max(0.0, min(1.0, v)) * 255) for v in c)


def spray(spec: dict) -> Image.Image:
    """Words sprayed by hand: each letter a little off its line and its neighbours, a mist round the
    strokes, specks, and the paint run down in drips where it went on thick."""
    rng = random.Random(spec.get("seed", 1))
    lines = spec["text"].split("\n")
    aspect = spec.get("aspect", 2.5)
    W, H = PX, max(64, int(PX / aspect))
    mask = Image.new("L", (W, H), 0)
    n = max(len(lines), 1)
    ref = _font(100)   # fit the widest line to the width, the lines to the height
    widest = max(sum(ref.getlength(ch) * 0.98 for ch in l) for l in lines) / 100.0
    size = int(min(H / n * 0.78, W * 0.86 / max(widest, 1e-3)))
    font = _font(size)
    y = (H - n * size * 1.05) / 2
    bottoms = []
    for line in lines:
        widths = [font.getlength(ch) * 0.98 for ch in line]
        x = (W - sum(widths)) / 2 + rng.uniform(-0.03, 0.03) * W
        slope = rng.uniform(-0.04, 0.04)
        for ch, w in zip(line, widths):
            if ch.strip():
                g = Image.new("L", (int(size * 1.6), int(size * 1.6)), 0)
                ImageDraw.Draw(g).text((size * 0.3, size * 0.15), ch, font=font, fill=255,
                                       stroke_width=max(1, size // 22), stroke_fill=255)
                g = g.rotate(rng.uniform(-7, 7), resample=Image.BICUBIC)
                k = rng.uniform(0.92, 1.08)
                g = g.resize((int(g.width * k), int(g.height * k)))
                gx, gy = int(x - size * 0.3), int(y + slope * (x - W / 2) + rng.uniform(-0.05, 0.05) * size - size * 0.15)
                mask.paste(Image.new("L", g.size, 255), (gx, gy), g)
                if rng.random() < 0.45:
                    bottoms.append((x + w * rng.uniform(0.2, 0.8), gy + size * 1.25 * k))
            x += w
        y += size * 1.05
    core = mask.filter(ImageFilter.GaussianBlur(size * 0.012))
    mist = mask.filter(ImageFilter.GaussianBlur(size * 0.09)).point(lambda v: int(v * 0.38))
    paint = ImageChops.lighter(core, mist)
    d = ImageDraw.Draw(paint)
    for bx, by in bottoms:   # the drips
        length = rng.uniform(0.15, 1.1) * size
        wd = max(2, int(size * rng.uniform(0.025, 0.05)))
        d.line([(bx, by - size * 0.3), (bx + rng.uniform(-2, 2), by + length)], fill=235, width=wd)
        d.ellipse([bx - wd, by + length - wd, bx + wd, by + length + wd * 1.4], fill=235)
    for _ in range(int(W * H / 900)):   # specks of overspray near the paint
        sx, sy = rng.uniform(0, W), rng.uniform(0, H)
        if mist.getpixel((int(sx) % W, int(sy) % H)) > 10:
            r = rng.uniform(0.5, 2.2)
            d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=int(rng.uniform(120, 230)))
    out = Image.new("RGBA", (W, H), _rgb(spec.get("color", (0.7, 0.05, 0.03))) + (0,))
    out.putalpha(paint)
    return out


def xcode(spec: dict) -> Image.Image:
    """The search team's mark on a door they went through: a big X; in its quarters the date and
    time (top), the team (left), what they found inside (right), and how many dead (bottom)."""
    rng = random.Random(spec.get("seed", 2))
    W = H = PX
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    wd = int(W * 0.035)
    for (a, b) in (((0.12, 0.1), (0.88, 0.9)), ((0.88, 0.1), (0.12, 0.9))):
        pts = [(W * (a[0] + (b[0] - a[0]) * t) + rng.uniform(-6, 6), H * (a[1] + (b[1] - a[1]) * t) + rng.uniform(-6, 6))
               for t in (0, 0.33, 0.66, 1)]
        d.line(pts, fill=255, width=wd, joint="curve")
    font = _font(int(H * 0.085))
    for key, (cx, cy) in (("top", (0.5, 0.2)), ("left", (0.22, 0.5)), ("right", (0.78, 0.5)), ("bottom", (0.5, 0.8))):
        t = spec.get(key, "")
        if t:
            tw = font.getlength(t)
            d.text((W * cx - tw / 2 + rng.uniform(-8, 8), H * cy - H * 0.045 + rng.uniform(-8, 8)), t, font=font, fill=255,
                   stroke_width=2, stroke_fill=255)
    paint = ImageChops.lighter(mask.filter(ImageFilter.GaussianBlur(1.2)),
                               mask.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * 0.35)))
    out = Image.new("RGBA", (W, H), _rgb(spec.get("color", (0.95, 0.45, 0.02))) + (0,))
    out.putalpha(paint)
    return out


def poster(spec: dict) -> Image.Image:
    """A notice pasted up and rained on: the paper yellowed and streaked, a corner torn off; an
    official notice (a heavy title, a black band, small print) or a missing person (VERMIST, a grey
    photograph, a name, where they were last seen)."""
    rng = random.Random(spec.get("seed", 3))
    W, H = int(PX * 0.71), PX
    paper = Image.new("RGB", (W, H), (int(228 - rng.uniform(0, 30)), int(222 - rng.uniform(0, 30)), int(200 - rng.uniform(0, 40))))
    d = ImageDraw.Draw(paper)
    ink = (22, 20, 18)
    lines = spec.get("text", "").split("\n")
    title, rest = (lines[0], lines[1:]) if lines else ("", [])
    tf = _font(int(W * 0.15))
    d.text(((W - tf.getlength(title)) / 2, H * 0.05), title, font=tf, fill=_rgb(spec.get("ink", (0.08, 0.07, 0.06))))
    y = H * 0.24
    if spec.get("photo"):   # a grey photograph of someone, a shape only
        d.rectangle([W * 0.2, y, W * 0.8, y + H * 0.36], fill=(120, 118, 112))
        d.ellipse([W * 0.38, y + H * 0.05, W * 0.62, y + H * 0.19], fill=(70, 68, 64))
        d.chord([W * 0.26, y + H * 0.2, W * 0.74, y + H * 0.5], 180, 360, fill=(70, 68, 64))
        y += H * 0.4
    else:
        d.rectangle([W * 0.06, y, W * 0.94, y + H * 0.02], fill=ink)
        y += H * 0.05
    bf = _font(int(W * 0.055))
    for line in rest:
        d.text(((W - bf.getlength(line)) / 2, y), line, font=bf, fill=ink)
        y += W * 0.085
    streaks = Image.new("L", (W, H), 0)   # the rain's runs, faint, and the damp spreading up from the bottom
    sd = ImageDraw.Draw(streaks)
    for _ in range(9):
        x = rng.uniform(0, W)
        sd.line([(x, rng.uniform(0, H * 0.5)), (x + rng.uniform(-6, 6), H)], fill=int(rng.uniform(40, 90)), width=int(rng.uniform(3, 12)))
    paper = Image.composite(Image.new("RGB", (W, H), (140, 128, 100)), paper, streaks.filter(ImageFilter.GaussianBlur(4)))
    damp = Image.new("L", (W, H), 0)
    ImageDraw.Draw(damp).rectangle([0, H * rng.uniform(0.7, 0.85), W, H], fill=90)
    paper = Image.composite(Image.new("RGB", (W, H), (120, 108, 82)), paper, damp.filter(ImageFilter.GaussianBlur(30)))
    alpha = Image.new("L", (W, H), 255)
    ad = ImageDraw.Draw(alpha)
    c = rng.choice([(0, 0), (W, 0), (W, H)])   # a corner torn off
    tear = [c, (abs(c[0] - W * rng.uniform(0.15, 0.4)), c[1]), (c[0], abs(c[1] - H * rng.uniform(0.1, 0.3)))]
    ad.polygon(tear, fill=0)
    out = paper.convert("RGBA")
    out.putalpha(alpha)
    return out


STYLES = {"spray": spray, "xcode": xcode, "poster": poster}


def draw(spec: dict) -> Image.Image:
    return STYLES[spec.get("style", "spray")](spec)


def named(rooms: Path = ROOMS) -> list:
    """Every decal the RoomSpecs name (each once)."""
    seen, out = set(), []
    for f in sorted(rooms.glob("*.json")):
        for p in json.loads(f.read_text()).get("props", []):
            dc = p.get("decal")
            if isinstance(dc, dict) and dc.get("id") not in seen:
                seen.add(dc.get("id"))
                out.append(dc)
    return out


def make(cache: Path = CACHE, rooms: Path = ROOMS) -> int:
    cache.mkdir(parents=True, exist_ok=True)
    n = 0
    for spec in named(rooms):
        path = cache / f"{spec.get('id') or decal_id(spec)}.png"
        if not path.exists():
            draw(spec).save(path)
            n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the paint and paper on the walls, as textures")
    ap.add_argument("cmd", choices=["make"])
    a = ap.parse_args(argv)
    if a.cmd == "make":
        print(f"decals: {make()} drawn into {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
