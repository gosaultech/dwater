# damned_waters/tools/art/paint_classic.py
# Purpose: paint RE2-Classic style texture atlases (128x128 pixel art) for the
# low-poly cast, and write the atlas layout JSON Godot reads for UV mapping.
#   python3 tools/art/paint_classic.py            (needs numpy + Pillow)
# Conventions shared with game/src/actors/classic_body.gd:
#   * each body part is a prism; texture u runs around it starting at the BACK,
#     so the FRONT of every part sits at the horizontal centre of its region
#   * v runs top -> bottom of the part
# PS1 look: tiny textures, painted-in folds/seams/stubble, per-pixel noise.
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "game" / "assets" / "characters" / "classic"
SIZE = 128
LAYOUT = {  # name: (x, y, w, h)
    "head": (0, 0, 64, 32), "torso": (64, 0, 64, 48), "upper_arm": (0, 32, 32, 24),
    "forearm": (32, 32, 32, 24), "thigh": (0, 56, 32, 32), "shin": (32, 56, 32, 32),
    "hand": (64, 48, 16, 16), "foot": (80, 48, 16, 16), "cap": (96, 48, 16, 16),
    "hair_long": (64, 64, 32, 48), "extra": (96, 64, 32, 64),
}


class Canvas:
    def __init__(self, seed: int):
        self.a = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
        self.rng = random.Random(seed)
        self.np = np.random.default_rng(seed)

    def region(self, name):
        x, y, w, h = LAYOUT[name]
        return self.a[y:y + h, x:x + w]

    def fill(self, name, color, noise=7.0):
        r = self.region(name)
        r[:] = color
        r += self.np.normal(0, noise, r.shape[:2])[..., None]

    def rows(self, name, v0, v1, color, noise=6.0):
        r = self.region(name)
        h = r.shape[0]
        a, b = int(v0 * h), max(int(v0 * h) + 1, int(v1 * h))
        r[a:b] = color
        r[a:b] += self.np.normal(0, noise, r[a:b].shape[:2])[..., None]

    def px(self, name, u, v, color, w=1, h=1):
        """u, v in pixels within the region; u measured from the region's left."""
        r = self.region(name)
        r[max(v, 0):v + h, max(u, 0):u + w] = color

    def blotches(self, name, color, count, size=(1, 3), alpha=0.6, v_range=(0.0, 1.0)):
        r = self.region(name)
        h, w = r.shape[:2]
        for _ in range(count):
            cx, cy = self.rng.randrange(w), self.rng.randrange(int(v_range[0] * h), max(int(v_range[1] * h), 1))
            s = self.rng.randint(*size)
            ys, xs = slice(max(cy - s, 0), cy + s), slice(max(cx - s, 0), cx + s)
            r[ys, xs] = r[ys, xs] * (1 - alpha) + np.array(color) * alpha

    def vline(self, name, u, v0, v1, color):
        r = self.region(name)
        h = r.shape[0]
        r[int(v0 * h):int(v1 * h), u] = color

    def shade_sides(self, name, amount=0.18):
        """Darken the flanks and back a little: baked PS1-style form shading."""
        r = self.region(name)
        w = r.shape[1]
        u = (np.arange(w) + 0.5) / w
        front = 0.5 + 0.5 * np.cos((u - 0.5) * 2 * np.pi)  # 1 at front, 0 at back
        r *= (1 - amount + amount * front)[None, :, None]

    def save(self, path):
        img = np.clip(self.a, 0, 255).astype(np.uint8)
        Image.fromarray(img, "RGB").save(path)


# ─────────────────────────────── faces ──────────────────────────────────────
def face(c: Canvas, skin, hair, style: str):
    """Head region 64x32. Front centre is u=32. Eyes ~row 15, mouth ~row 25."""
    dark = tuple(x * 0.72 for x in skin)
    c.fill("head", skin, 5)
    if style in ("survivor", "drowned_m"):
        # hair: crown all round, back of head down to the nape, hairline at front
        c.rows("head", 0, 0.28, hair, 8)
        r = c.region("head")
        for u in range(64):
            back = min(u, 63 - u) < 16            # u 0..15 and 48..63 = back half
            depth = 20 if back else (9 if abs(u - 32) < 10 else 13)
            if style == "drowned_m" and not back and c.rng.random() < 0.35:
                depth -= 4                        # thinning, plastered hair
            r[:depth, u] = np.array(hair) + c.np.normal(0, 8, 3)
        for s in (-1, 1):                          # sideburns
            c.px("head", 32 + s * 12 - (1 if s < 0 else 0), 9, hair, 2, 5)
    if style == "survivor":
        white, iris = (222, 212, 200), (58, 44, 34)
        for s in (-1, 1):
            ex = 32 + s * 5 - (2 if s < 0 else 0)
            c.px("head", ex, 12, hair, 4, 1)               # eyebrow
            c.px("head", ex, 15, white, 3, 1)               # eye white
            c.px("head", ex + (1 if s < 0 else 1), 15, iris, 1, 1)
            c.px("head", ex, 16, dark, 3, 1)                # lower lid shadow
            c.px("head", 32 + s * 13, 14, dark, 2, 6)        # ears (sides)
        c.px("head", 32, 16, dark, 1, 4)                     # nose bridge shadow
        c.px("head", 31, 20, dark, 3, 1)                     # nostrils
        c.px("head", 30, 24, (138, 82, 72), 5, 1)            # mouth
        c.px("head", 31, 25, (120, 70, 62), 3, 1)
        c.blotches("head", tuple(x * 0.8 for x in skin), 40, (0, 1), 0.5, (0.72, 1.0))  # stubble
    elif style == "drowned_m":
        sock = (70, 72, 66)
        for s in (-1, 1):
            ex = 32 + s * 5 - (2 if s < 0 else 0)
            c.px("head", ex - 1, 14, sock, 5, 4)             # sunken sockets
            c.px("head", ex, 15, (206, 210, 196), 3, 1)      # milky, no pupils
            c.px("head", 32 + s * 13, 14, dark, 2, 6)
        c.px("head", 32, 17, dark, 1, 4)
        c.px("head", 29, 23, (96, 98, 124), 7, 1)            # blue lips
        c.px("head", 29, 24, (34, 14, 16), 7, 4)             # slack open jaw
        c.px("head", 30, 24, (190, 180, 150), 1, 1)          # a tooth
        c.px("head", 33, 24, (170, 160, 130), 1, 1)
        c.blotches("head", (110, 92, 112), 14, (1, 2), 0.45, (0.3, 1.0))   # marbling
        for _ in range(3):                                    # water trails from the mouth
            u = c.rng.randrange(29, 36)
            c.vline("head", u, 0.88, 1.0, (70, 90, 70))
    elif style == "drowned_f":
        # Long wet hair hanging over the face: The Ring, painted in pixels.
        c.fill("head", hair, 7)
        r = c.region("head")
        for u in range(22, 43):
            if c.rng.random() < 0.3:                        # gaps in the curtain show skin
                top = c.rng.randrange(12, 20)
                r[top:top + c.rng.randrange(3, 9), u] = np.array(skin) * (0.8 + 0.2 * c.rng.random())
        c.px("head", 35, 16, (206, 210, 196), 2, 1)          # one milky eye, through the hair
        c.px("head", 29, 25, (34, 14, 16), 4, 3)             # open mouth glimpsed
    c.shade_sides("head", 0.12)
    # cap = top of head
    c.fill("cap", hair if style != "none" else skin, 8)


# ─────────────────────────────── bodies ─────────────────────────────────────
def survivor(c: Canvas):
    skin, hair = (196, 152, 124), (48, 36, 28)
    jacket, seam, dark = (88, 82, 56), (60, 56, 38), (44, 40, 28)
    jeans, stitch, boot = (56, 68, 96), (132, 116, 80), (60, 42, 30)
    face(c, skin, hair, "survivor")
    # torso: jeans at the hips, belt, waxed jacket, open collar with grey tee + neck
    c.fill("torso", jacket, 7)
    c.rows("torso", 0.9, 1.0, jeans)
    c.rows("torso", 0.86, 0.9, (32, 24, 20))                 # belt
    c.px("torso", 31, 39, (150, 140, 110), 3, 2)              # buckle
    c.rows("torso", 0.0, 0.1, skin)                           # neck
    c.rows("torso", 0.1, 0.18, (110, 76, 48))                 # corduroy collar
    c.px("torso", 28, 5, (122, 124, 128), 9, 6)               # tee in the open collar
    c.vline("torso", 32, 0.18, 0.86, (36, 36, 38))             # zipper
    for v in range(9, 41, 3):
        c.px("torso", 32, v, (150, 150, 150))
    for s in (-1, 1):                                          # pockets + flaps
        c.px("torso", 32 + s * 9 - 3, 30, dark, 7, 1)
        c.px("torso", 32 + s * 9 - 3, 31, seam, 7, 5)
        c.vline("torso", 32 + s * 16, 0.18, 0.86, seam)         # side seams
    c.blotches("torso", dark, 30, (0, 1), 0.4, (0.2, 0.85))    # creases / wax wear
    c.shade_sides("torso")
    # sleeves, forearm cuff + wrist skin
    c.fill("upper_arm", jacket, 7)
    c.vline("upper_arm", 16, 0.0, 1.0, seam)
    c.fill("forearm", jacket, 7)
    c.rows("forearm", 0.78, 0.9, dark)                        # cuff
    c.rows("forearm", 0.9, 1.0, skin)
    c.blotches("forearm", dark, 12, (0, 1), 0.5)
    # jeans: stitched seams, knee fade, boots at the bottom of the shin
    for part in ("thigh", "shin"):
        c.fill(part, jeans, 8)
        c.vline(part, 8, 0.0, 1.0, stitch)
        c.vline(part, 24, 0.0, 1.0, stitch)
    c.blotches("thigh", (88, 100, 128), 10, (1, 2), 0.35, (0.75, 1.0))   # knee fade
    c.rows("shin", 0.78, 1.0, boot)
    c.fill("hand", skin, 6)
    c.fill("foot", boot, 6)
    c.rows("foot", 0.8, 1.0, (26, 20, 16))                    # sole


def drowned_m(c: Canvas):
    skin, hair = (138, 150, 128), (30, 32, 26)
    shirt, stain, blood = (150, 156, 150), (100, 110, 96), (108, 30, 24)
    trousers = (50, 52, 58)
    face(c, skin, hair, "drowned_m")
    c.fill("torso", shirt, 9)
    c.rows("torso", 0.0, 0.1, skin)
    c.rows("torso", 0.1, 0.16, (170, 172, 166))               # collar
    c.vline("torso", 32, 0.16, 0.9, (120, 124, 118))            # button placket
    for v in range(10, 40, 5):
        c.px("torso", 32, v, (200, 200, 190))
    c.px("torso", 31, 7, (90, 22, 26), 3, 16)                  # loosened tie
    c.blotches("torso", stain, 25, (1, 3), 0.55)                 # water stains
    c.blotches("torso", skin, 7, (2, 4), 0.95, (0.25, 0.8))      # tears in the shirt show skin
    c.blotches("torso", blood, 10, (1, 2), 0.7, (0.2, 0.6))
    c.blotches("torso", (60, 84, 44), 10, (0, 2), 0.6)           # algae
    c.rows("torso", 0.9, 1.0, trousers)
    c.shade_sides("torso")
    c.fill("upper_arm", shirt, 9)
    c.blotches("upper_arm", stain, 8, (1, 2), 0.5)
    c.fill("forearm", skin, 7)                                  # sleeves rolled/torn away
    c.rows("forearm", 0.0, 0.2, shirt)
    c.blotches("forearm", (110, 92, 112), 10, (1, 2), 0.5)       # bruising
    for part in ("thigh", "shin"):
        c.fill(part, trousers, 6)
        c.blotches(part, (60, 84, 44), 8, (0, 2), 0.5)
        c.vline(part, 16, 0.0, 1.0, (40, 42, 46))
    c.fill("hand", skin, 7)
    c.blotches("hand", (80, 90, 80), 6, (0, 1), 0.6)             # wrinkled "washerwoman" skin
    c.fill("foot", (30, 28, 26), 5)


def drowned_f(c: Canvas):
    skin, hair = (160, 170, 156), (18, 18, 16)
    gown, stain = (120, 132, 146), (80, 92, 100)
    face(c, skin, hair, "drowned_f")
    c.fill("torso", gown, 8)
    c.rows("torso", 0.0, 0.14, skin)
    c.blotches("torso", stain, 30, (1, 3), 0.5)
    c.blotches("torso", (108, 30, 24), 6, (1, 2), 0.6, (0.3, 0.7))
    c.shade_sides("torso")
    c.fill("upper_arm", skin, 7)
    c.blotches("upper_arm", (120, 100, 124), 6, (1, 2), 0.5)
    c.fill("forearm", skin, 7)
    c.blotches("forearm", (120, 100, 124), 6, (1, 2), 0.5)
    c.fill("thigh", gown, 8)
    c.blotches("thigh", stain, 10, (1, 2), 0.5)
    c.fill("shin", skin, 7)                                     # bare legs under the gown
    c.fill("hand", skin, 7)
    c.fill("foot", skin, 7)                                     # barefoot
    c.fill("hair_long", hair, 9)                                # the hair curtain down her back
    r = c.region("hair_long")
    for u in range(r.shape[1]):
        if c.rng.random() < 0.4:
            r[:, u] *= 0.7


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("survivor", survivor), ("drowned_m", drowned_m), ("drowned_f", drowned_f)):
        c = Canvas(sum(map(ord, name)))  # stable seed (hash() is randomized per run)
        fn(c)
        c.save(OUT / f"{name}.png")
        (OUT / f"{name}.png.import").write_text(IMPORT.format(name=name))
        print(f"[paint] {name}")
    (OUT / "atlas_layout.json").write_text(json.dumps({"size": SIZE, "regions": LAYOUT}, indent=2) + "\n")


IMPORT = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://assets/characters/classic/{name}.png"

[params]

compress/mode=0
mipmaps/generate=false
process/fix_alpha_border=false
detect_3d/compress_to=0
"""

if __name__ == "__main__":
    main()
