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

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

REPO = Path(__file__).resolve().parents[2]
ROOMS = REPO / "game" / "data" / "rooms"
CACHE = REPO / "pipeline_out" / "assets" / "decals"
FONTS = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
         Path("/Library/Fonts/Arial Bold.ttf"), Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
         Path("C:/Windows/Fonts/arialbd.ttf")]
SERIF = [Path("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"), Path("/Library/Fonts/Georgia Bold.ttf")]
PX = 1024   # the long side, in pixels
# The hands that wrote on the walls (tools/assets/fonts: OFL / Apache lettering, see its README): a
# font file, how fat the can's cap sprays (a share of the letter height), how much each letter wanders.
HAND_FONTS = Path(__file__).resolve().parent / "fonts"
HANDS = {"marker": ("permanentmarker/PermanentMarker-Regular.ttf", 0.006, 4.0),
         "grace": ("coveredbyyourgrace/CoveredByYourGrace.ttf", 0.017, 5.0),
         "scratch": ("rocksalt/RockSalt-Regular.ttf", 0.008, 3.0),
         "reenie": ("reeniebeanie/ReenieBeanie.ttf", 0.02, 5.0),
         "tag": ("sedgwickavedisplay/SedgwickAveDisplay-Regular.ttf", 0.004, 3.0),
         "stencil": ("sairastencilone/SairaStencilOne-Regular.ttf", 0.0, 0.6)}
DRAWN = "2"   # the drawing's version: `make` redraws the whole cache when this changes (the decals' names do not)


def decal_id(spec: dict) -> str:
    """A decal's name: the same words, style, colour and seed always make the same file."""
    body = {k: v for k, v in spec.items() if k != "id"}
    return hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12]


def _font(size: int, serif: bool = False):
    for f in (SERIF if serif else []) + FONTS:
        if f.exists():
            return ImageFont.truetype(str(f), size)
    return ImageFont.load_default()


def _hand(spec: dict, rng) -> str:
    """Whose hand: the one the spec names, else by what is written: a long message in a hand you can
    read, a word or two in anything, a tag now and then."""
    if spec.get("hand") in HANDS:
        return spec["hand"]
    words = spec.get("text", "")
    long_ = "\n" in words or len(words) > 11
    return rng.choice(["marker", "marker", "grace", "reenie"] if long_ else ["marker", "grace", "scratch", "reenie", "tag"])


def _hand_font(hand: str, size: int):
    p = HAND_FONTS / HANDS[hand][0]
    return ImageFont.truetype(str(p), size) if p.exists() else _font(size)


def _has(font, ch: str) -> bool:
    """Whether a font draws this letter (some hands have no accents or dots: those fall back)."""
    try:
        return font.getmask(ch).getbbox() != font.getmask("\uffff").getbbox() or ch == " "
    except Exception:
        return False


def _cloud(nrng, w: int, h: int, cw: int, ch: int) -> np.ndarray:
    """Soft noise, 0..1, w x h: random values on a coarse cw x ch grid, blown up smoothly."""
    small = Image.fromarray((nrng.random((max(2, ch), max(2, cw))) * 255).astype(np.uint8), "L")
    return np.asarray(small.resize((w, h), Image.BICUBIC), dtype=np.float32) / 255.0


def _sprayed(mask: Image.Image, size: float, cap: float, rng, nrng, drips: list) -> Image.Image:
    """Paint from a can, from the shape the hand drew: a solid core with a soft edge, thinner where
    the hand moved fast and where the can sputtered, a mist round it flecked with droplets, runs down
    from where it went on thick, and the wall's own tooth showing through. Returns the alpha."""
    W, H = mask.size
    if cap > 0:   # the cap's width: the line fattened to it
        r = max(1, int(size * cap))
        mask = mask.filter(ImageFilter.MaxFilter(2 * r + 1))
    m = np.asarray(mask, dtype=np.float32) / 255.0
    press = 0.55 + 0.45 * _cloud(nrng, W, H, W // 150, H // 110)                       # the hand's speed
    sputter = np.clip((_cloud(nrng, W, H, W // 36, max(2, H // 10)) - 0.7) * 5.0, 0.0, 1.0)   # the can running dry in streaks
    core = np.asarray(mask.filter(ImageFilter.GaussianBlur(max(0.8, size * 0.011))), dtype=np.float32) / 255.0
    core = np.clip((core - 0.22) * 1.7, 0.0, 1.0) * (0.7 + 0.3 * press) * (1.0 - 0.22 * sputter)
    mist = np.asarray(mask.filter(ImageFilter.GaussianBlur(size * 0.1)), dtype=np.float32) / 255.0
    far = np.asarray(mask.filter(ImageFilter.GaussianBlur(size * 0.22)), dtype=np.float32) / 255.0
    dots = (nrng.random((H, W)) < far * 0.1).astype(np.float32)                         # droplets thrown past the line
    dots = np.asarray(Image.fromarray((dots * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.7)), dtype=np.float32) / 255.0
    a = np.maximum(core, mist * 0.3 * press)
    a = np.maximum(a, np.clip(dots * 2.2, 0.0, 0.75))
    run = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(run)
    for bx, by in drips:   # runs: straight down, thinning, a bead at the end
        length = rng.uniform(0.12, 0.95) * size
        wd = max(2.0, size * max(cap, 0.014) * rng.uniform(0.6, 1.0))
        steps = max(4, int(length / 6))
        for q in range(steps):
            t = q / (steps - 1)
            y0 = by + length * t
            w_ = wd * (1.0 - 0.55 * t)
            x_ = bx + math.sin(t * 3.0 + bx) * 0.8
            d.ellipse([x_ - w_ / 2, y0 - w_ * 0.9, x_ + w_ / 2, y0 + w_ * 0.9], fill=int(235 - 60 * t))
        d.ellipse([bx - wd * 0.55, by + length - wd * 0.3, bx + wd * 0.55, by + length + wd * 1.1], fill=225)
    a = np.maximum(a, np.asarray(run.filter(ImageFilter.GaussianBlur(0.8)), dtype=np.float32) / 255.0 * 0.92)
    tooth = 0.8 + 0.2 * nrng.random((H, W)).astype(np.float32)                           # the wall's pores: paint sits thinner in them
    tooth = np.asarray(Image.fromarray((tooth * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float32) / 255.0
    edge = np.minimum(np.minimum(np.arange(W)[None, :], W - 1 - np.arange(W)[None, :]), np.minimum(np.arange(H)[:, None], H - 1 - np.arange(H)[:, None]))
    a = a * (0.72 + 0.28 * tooth / tooth.max()) * np.clip(edge / 6.0, 0.0, 1.0)          # (nothing runs off the sheet)
    return Image.fromarray((np.clip(a, 0.0, 1.0) * 255).astype(np.uint8), "L")


def _rgb(c) -> tuple:
    return tuple(int(max(0.0, min(1.0, v)) * 255) for v in c)


def spray(spec: dict) -> Image.Image:
    """Words sprayed by hand: written in a real hand (HANDS; "hand" names one, else picked by what is
    written), each letter a little off its line and its neighbours, then put through the can
    (_sprayed): soft-edged, uneven, misted, run."""
    seed = spec.get("seed", 1)
    rng, nrng = random.Random(seed), np.random.default_rng(seed)
    hand = _hand(spec, rng)
    _file, cap, wander = HANDS[hand]
    lines = spec["text"].split("\n")
    aspect = spec.get("aspect", 2.5)
    W, H = PX, max(64, int(PX / aspect))
    mask = Image.new("L", (W, H), 0)
    n = max(len(lines), 1)
    ref, ref_plain = _hand_font(hand, 100), _font(100)
    width_of = lambda font, plain, l: sum((font if _has(font, ch) else plain).getlength(ch) * 0.97 for ch in l)   # noqa: E731
    widest = max(width_of(ref, ref_plain, l) for l in lines) / 100.0
    size = int(min(H / n * 0.7, W * 0.8 / max(widest, 1e-3)))
    font, plain = _hand_font(hand, size), _font(size)
    y = (H - n * size * 1.08) / 2
    bottoms = []
    for line in lines:
        widths = [(font if _has(font, ch) else plain).getlength(ch) * 0.97 for ch in line]
        x = (W - sum(widths)) / 2 + rng.uniform(-0.02, 0.02) * W
        slope = rng.uniform(-0.035, 0.035)
        for ch, w in zip(line, widths):
            if ch.strip():
                g = Image.new("L", (int(size * 2.0), int(size * 2.0)), 0)
                ImageDraw.Draw(g).text((size * 0.5, size * 0.3), ch, font=font if _has(font, ch) else plain, fill=255)
                g = g.rotate(rng.uniform(-wander, wander), resample=Image.BICUBIC)
                k = rng.uniform(0.94, 1.07)
                g = g.resize((int(g.width * k), int(g.height * k)))
                gx, gy = int(x - size * 0.5 * k), int(y + slope * (x - W / 2) + rng.uniform(-0.04, 0.04) * size - size * 0.3 * k)
                mask.paste(Image.new("L", g.size, 255), (gx, gy), g)
                box = g.getbbox()
                if box and rng.random() < 0.4:   # a run from the foot of the letter
                    bottoms.append((gx + rng.uniform(box[0] + 2, max(box[0] + 3, box[2] - 2)), gy + box[3] - size * 0.06))
            x += w
        y += size * 1.08
    out = Image.new("RGBA", (W, H), _rgb(spec.get("color", (0.7, 0.05, 0.03))) + (0,))
    out.putalpha(_sprayed(mask, size, cap, rng, nrng, bottoms))
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
    font, plain = _hand_font("marker", int(H * 0.095)), _font(int(H * 0.085))   # (written with the can, in a marker's hand)
    for key, (cx, cy) in (("top", (0.5, 0.2)), ("left", (0.22, 0.5)), ("right", (0.78, 0.5)), ("bottom", (0.5, 0.8))):
        t = spec.get(key, "")
        if t:
            fo = font if all(_has(font, ch) for ch in t) else plain
            tw = fo.getlength(t)
            d.text((W * cx - tw / 2 + rng.uniform(-8, 8), H * cy - H * 0.05 + rng.uniform(-8, 8)), t, font=fo, fill=255, stroke_width=1, stroke_fill=255)
    drips = [(W * (0.12 + 0.76 * t_) + rng.uniform(-4, 4), H * (0.1 + 0.8 * (t_ if q else 1 - t_)) + wd * 0.3) for q in (0, 1) for t_ in (rng.uniform(0.1, 0.9),)]
    out = Image.new("RGBA", (W, H), _rgb(spec.get("color", (0.95, 0.45, 0.02))) + (0,))
    out.putalpha(_sprayed(mask, H * 0.3, 0.0, rng, np.random.default_rng(spec.get("seed", 2)), drips))
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
    stamp = cache / ".drawn"
    fresh = not stamp.exists() or stamp.read_text().strip() != DRAWN   # (the drawing changed: every decal again)
    stamp.write_text(DRAWN)
    for spec in named(rooms):
        path = cache / f"{spec.get('id') or decal_id(spec)}.png"
        if fresh or not path.exists():
            draw(spec).save(path)
            n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the paint and paper on the walls, as textures")
    ap.add_argument("cmd", choices=["make"])
    ap.add_argument("--rooms", default=str(ROOMS), help="the RoomSpecs to read (default: the game's)")
    a = ap.parse_args(argv)
    if a.cmd == "make":
        print(f"decals: {make(rooms=Path(a.rooms))} drawn into {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
