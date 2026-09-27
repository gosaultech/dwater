# damned_waters/tools/art/materials.py
# Purpose: generate the creature material library: tileable 256x256 albedo +
# normal maps (normal derived from a height field), written to
# game/assets/materials/. Godot maps them triplanar, so models need no UVs.
#   python3 tools/art/materials.py      (numpy + Pillow)
# Every texture tiles seamlessly because all noise is built on a periodic lattice.
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "game" / "assets" / "materials"
N = 256
rng = np.random.default_rng(1996)
Y, X = np.mgrid[0:N, 0:N] / N


def value_noise(cells: int, seed: int) -> np.ndarray:
    """Periodic value noise: a cells x cells lattice, smoothstep-interpolated, wraps."""
    g = np.random.default_rng(seed).random((cells, cells))
    fx, fy = X * cells, Y * cells
    x0, y0 = np.floor(fx).astype(int) % cells, np.floor(fy).astype(int) % cells
    x1, y1 = (x0 + 1) % cells, (y0 + 1) % cells
    tx, ty = fx - np.floor(fx), fy - np.floor(fy)
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = g[y0, x0] * (1 - tx) + g[y0, x1] * tx
    b = g[y1, x0] * (1 - tx) + g[y1, x1] * tx
    return a * (1 - ty) + b * ty


def fbm(base: int, octaves: int, seed: int, gain: float = 0.5) -> np.ndarray:
    out, amp, total = np.zeros((N, N)), 1.0, 0.0
    for o in range(octaves):
        out += value_noise(base * 2 ** o, seed + o) * amp
        total += amp
        amp *= gain
    return out / total


def ramp(t, stops):
    """Map 0..1 through color stops [(pos, (r,g,b)), ...]."""
    t = np.clip(t, 0, 1)
    out = np.zeros((*t.shape, 3))
    for (p0, c0), (p1, c1) in zip(stops[:-1], stops[1:]):
        m = (t >= p0) & (t <= p1)
        k = ((t - p0) / max(p1 - p0, 1e-6))[m][:, None]
        out[m] = np.array(c0) * (1 - k) + np.array(c1) * k
    out[t < stops[0][0]] = stops[0][1]
    out[t > stops[-1][0]] = stops[-1][1]
    return out


def normal_from_height(h: np.ndarray, strength: float) -> np.ndarray:
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5) * 255


def _imp(name, kind, extra=""):
    return (f'[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n[deps]\n\n'
            f'source_file="res://assets/materials/{name}_{kind}.png"\n\n[params]\n\n'
            f"compress/mode=0\nmipmaps/generate=true\n{extra}detect_3d/compress_to=0\n")


def save(name: str, albedo: np.ndarray, height: np.ndarray, strength: float, rough: np.ndarray | None = None):
    """albedo 0..255 RGB, height 0..1, rough 0..1 (None = no roughness map)."""
    Image.fromarray(np.clip(albedo, 0, 255).astype(np.uint8), "RGB").save(OUT / f"{name}_albedo.png")
    Image.fromarray(normal_from_height(height, strength).astype(np.uint8), "RGB").save(OUT / f"{name}_normal.png")
    (OUT / f"{name}_albedo.png.import").write_text(_imp(name, "albedo"))
    (OUT / f"{name}_normal.png.import").write_text(_imp(name, "normal", "compress/normal_map=1\n"))
    if rough is not None:
        Image.fromarray((np.clip(rough, 0, 1) * 255).astype(np.uint8), "L").save(OUT / f"{name}_rough.png")
        (OUT / f"{name}_rough.png.import").write_text(_imp(name, "rough"))
    print(f"[mat] {name}")


def blotch(seed, cells, lo, hi):
    """Soft mask of patches (0..1) from thresholded noise."""
    n = fbm(cells, 4, seed)
    return np.clip((n - lo) / (hi - lo), 0, 1)


def layer(base, color, mask):
    return base * (1 - mask[..., None]) + np.array(color) * mask[..., None]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grime = fbm(6, 5, 900)
    # ── Coroner's sheet: dirty linen, canal mud, old blood; matte, damp patches glossier.
    weave = (np.sin(X * np.pi * 2 * 96) * np.sin(Y * np.pi * 2 * 96)) * 0.5 + 0.5
    wrinkles = fbm(4, 4, 11) * 0.7 + np.abs(np.sin((X * 7 + fbm(3, 3, 12) * 1.5) * np.pi)) * 0.3
    a = ramp(fbm(3, 5, 13) * 0.7 + weave * 0.1, [(0.3, (104, 100, 86)), (0.6, (150, 146, 128)), (0.8, (168, 162, 142))])
    a = layer(a, (70, 60, 42), blotch(14, 3, 0.55, 0.75) * 0.8)          # canal mud
    a = layer(a, (72, 18, 14), blotch(15, 5, 0.66, 0.78) * 0.85)         # old blood
    wet = blotch(16, 3, 0.45, 0.7)
    save("shroud", a * (0.88 + 0.12 * weave[..., None]), wrinkles + weave * 0.1, 7.0, 0.85 - wet * 0.4)
    # ── Drowned skin: marbling, black veins, bruising, peeling "washerwoman" patches.
    marb = fbm(4, 5, 21)
    veins = np.clip(1 - np.abs(fbm(6, 4, 22) - 0.5) * 16, 0, 1)
    a = ramp(marb, [(0.25, (70, 84, 66)), (0.5, (118, 128, 106)), (0.68, (104, 82, 100)), (0.85, (52, 60, 44))])
    a = layer(a, (38, 30, 44), blotch(23, 4, 0.62, 0.8) * 0.7)            # deep bruises
    a = layer(a, (170, 172, 150), blotch(24, 9, 0.7, 0.8) * 0.6)          # peeling skin
    a = a * (1 - veins[..., None] * 0.5)
    slime = blotch(25, 4, 0.5, 0.7)
    save("skin_drowned", a, fbm(18, 4, 26) * 0.5 + veins * 0.5 + blotch(24, 9, 0.7, 0.8) * 0.4, 5.0, 0.7 - slime * 0.4)
    # ── Raw flesh: split skin, exposed muscle fibre, yellow fat; wet.
    fibre = np.abs(np.sin((X * 30 + fbm(4, 3, 31) * 3) * np.pi))
    a = ramp(fibre * 0.6 + fbm(8, 3, 32) * 0.4, [(0.2, (40, 6, 8)), (0.55, (110, 22, 24)), (0.8, (150, 60, 50))])
    a = layer(a, (170, 150, 80), blotch(33, 8, 0.72, 0.82) * 0.8)
    save("flesh_raw", a, fibre * 0.6 + fbm(10, 3, 34) * 0.4, 6.0, 0.25 + fbm(5, 3, 35) * 0.2)
    # ── Cellar skin: bloodless, bruised, filthy.
    veins = np.clip(1 - np.abs(fbm(5, 4, 41) - 0.5) * 14, 0, 1)
    a = ramp(fbm(6, 4, 42), [(0.3, (150, 150, 146)), (0.6, (196, 194, 188)), (0.85, (176, 170, 164))])
    a = a * (1 - veins[..., None] * np.array([0.3, 0.24, 0.1]))
    a = layer(a, (80, 60, 70), blotch(43, 4, 0.63, 0.8) * 0.6)
    a = layer(a, (70, 62, 50), blotch(44, 3, 0.5, 0.75) * 0.7)            # grime
    save("skin_pale", a, fbm(20, 4, 45) * 0.5 + veins * 0.5, 4.0, 0.75 - blotch(46, 5, 0.6, 0.8) * 0.3)
    # ── Waterlogged wool coat: felted, muddy, matte.
    felt = fbm(24, 4, 51)
    a = ramp(fbm(3, 4, 52) * 0.5 + felt * 0.5, [(0.3, (24, 25, 26)), (0.6, (42, 42, 42)), (0.8, (58, 54, 48))])
    a = layer(a, (52, 44, 30), blotch(53, 3, 0.55, 0.8) * 0.7)
    save("coat_wet", a, felt, 5.0, 0.9 - blotch(54, 3, 0.5, 0.75) * 0.35)
    # ── Plague canvas: weathered black oilcloth, cracked and dusty. NOT shiny.
    cracks = np.clip(1 - np.abs(fbm(12, 3, 61) - 0.5) * 30, 0, 1)
    creases = np.abs(np.sin((Y * 6 + fbm(3, 4, 62) * 2.0) * np.pi))
    a = ramp(fbm(8, 4, 63) * 0.6 + creases * 0.4, [(0.2, (14, 13, 12)), (0.7, (34, 31, 28))])
    a = layer(a, (76, 70, 60), cracks * 0.7)                               # dry cracks catch dust
    a = layer(a, (58, 50, 38), blotch(64, 3, 0.55, 0.8) * 0.6)             # dried mud
    save("canvas_black", a, creases * 0.6 + cracks * 0.4, 6.0, 0.8 - creases * 0.15)
    # ── Old leather: cracked, stained, stitched.
    grain = fbm(28, 4, 71)
    cracks = np.clip(1 - np.abs(fbm(10, 3, 72) - 0.5) * 22, 0, 1)
    a = ramp(fbm(4, 4, 73) * 0.6 + grain * 0.4, [(0.2, (34, 22, 15)), (0.6, (72, 48, 30)), (0.85, (96, 68, 42))])
    a = a * (1 - cracks[..., None] * 0.55)
    save("leather", a, grain * 0.5 + cracks * 0.5, 6.0, 0.75 - grain * 0.15)
    # ── Waxed cotton jacket (survivor): olive, creased, worn at the edges.
    creases = np.abs(np.sin((Y * 5 + X * 2 + fbm(3, 4, 81) * 2.2) * np.pi))
    a = ramp(fbm(6, 4, 82) * 0.6 + creases * 0.4, [(0.2, (40, 44, 30)), (0.7, (70, 72, 48))])
    a = layer(a, (54, 48, 36), blotch(83, 3, 0.55, 0.8) * 0.5)
    save("jacket", a, creases * 0.7 + fbm(30, 2, 84) * 0.3, 5.0, 0.7 - creases * 0.15)
    # ── Denim: diagonal twill, faded.
    twill = np.sin((X * 90 + Y * 90) * np.pi * 2) * 0.5 + 0.5
    a = ramp(fbm(4, 4, 91) * 0.7 + twill * 0.3, [(0.2, (26, 34, 54)), (0.7, (56, 70, 100))])
    save("denim", a, twill * 0.7 + fbm(20, 2, 92) * 0.3, 4.0, np.full((N, N), 0.9))
    # ── Hair: dark, clumped, damp.
    streak = np.abs(np.sin((X * 60 + fbm(3, 3, 101) * 4) * np.pi))
    save("hair", ramp(streak * 0.6 + fbm(10, 2, 102) * 0.4, [(0.2, (12, 9, 7)), (0.8, (46, 34, 24))]), streak, 8.0,
         0.55 - streak * 0.2)
    # ── Bone: yellowed, stained.
    save("bone", ramp(fbm(6, 4, 111), [(0.3, (140, 124, 90)), (0.7, (196, 184, 150))]), fbm(16, 3, 112), 3.0,
         np.full((N, N), 0.6))
    # ── Leech: segmented, slick, near-black.
    rings = np.sin(Y * np.pi * 2 * 24) * 0.5 + 0.5
    save("leech", ramp(rings * 0.5 + fbm(8, 2, 121) * 0.5, [(0.2, (10, 8, 6)), (0.8, (46, 32, 22))]), rings, 5.0,
         np.full((N, N), 0.22))
    # Rust / rope / flesh / kelp: now with roughness.
    rust_mask = fbm(5, 5, 131)
    pits = fbm(32, 3, 132)
    a = ramp(rust_mask, [(0.3, (40, 44, 46)), (0.45, (92, 50, 30)), (0.7, (140, 72, 36)), (0.9, (70, 40, 24))])
    save("rust", a * (0.75 + 0.25 * pits[..., None]), pits * 0.6 + (rust_mask > 0.45) * 0.4, 5.0, 0.8 + pits * 0.2)
    twist = np.sin((X * 6 + Y * 24) * np.pi * 2) * 0.5 + 0.5
    save("rope", ramp(twist * 0.7 + fbm(8, 3, 141) * 0.3, [(0.2, (52, 44, 30)), (0.7, (110, 96, 68))]), twist, 8.0,
         np.full((N, N), 0.95))
    lumps = fbm(4, 6, 151)
    a = ramp(lumps, [(0.25, (26, 22, 20)), (0.45, (66, 40, 38)), (0.6, (104, 104, 88)), (0.8, (50, 58, 42))])
    a = layer(a, (110, 22, 24), blotch(152, 5, 0.68, 0.8) * 0.8)
    save("flesh", a, lumps, 9.0, 0.35 + fbm(4, 3, 153) * 0.35)
    streak = np.abs(np.sin((X * 11 + fbm(2, 3, 161)) * np.pi))
    save("kelp", ramp(streak * 0.6 + fbm(6, 3, 162) * 0.4, [(0.2, (14, 26, 10)), (0.8, (40, 62, 24))]), streak, 4.0,
         np.full((N, N), 0.35))
    paint_face()
    paint_eye()


def paint_face():
    """UV texture for the survivor's head (equirect: u = 0.5 + theta/2pi, v = 0.5 - phi/pi,
    theta = atan2(x, y) from the front, phi = elevation). Must match skinned.py head UVs.
    PS2 practice: lighting and form painted into the face."""
    from scipy.ndimage import gaussian_filter
    W, H = 1024, 512
    vv, uu = np.mgrid[0:H, 0:W] + 0.5
    th = (uu / W - 0.5) * 2 * np.pi
    ph = (0.5 - vv / H) * np.pi
    g = np.random.default_rng(7)
    noise = gaussian_filter(g.standard_normal((H, W)), 3)
    img = np.zeros((H, W, 3)) + np.array([176, 132, 108]) + noise[..., None] * np.array([10, 8, 7])

    def blob(t, p, st, sp, amt, color=None):
        m = np.exp(-(((th - t) / st) ** 2 + ((ph - p) / sp) ** 2))
        if color is None:
            img[:] = img * (1 + amt * m[..., None])
        else:
            img[:] = img * (1 - m[..., None] * amt) + np.array(color) * m[..., None] * amt
        return m

    E_T, E_P = 0.352, 0.103       # eye centres (+/- theta)
    for sx in (-1, 1):
        blob(sx * E_T, E_P, 0.13, 0.07, -0.22)                       # socket shadow
        blob(sx * E_T, E_P - 0.055, 0.1, 0.035, 0.0, (110, 70, 80))  # tired, bruised under-eye
        blob(sx * 0.55, -0.1, 0.18, 0.1, 0.08)                        # cheekbone light
        blob(sx * E_T, E_P - 0.05, 0.09, 0.02, 0.35, (120, 78, 86))
        # almond eye: white, iris, pupil, lid line, lashes
        el = ((th - sx * E_T) / 0.058) ** 2 + ((ph - E_P) / 0.022) ** 2
        img[el < 1] = np.array([214, 204, 192])
        ir = np.hypot(th - sx * E_T, (ph - E_P) * 1.05)
        img[(ir < 0.02) & (el < 1)] = np.array([78, 64, 44])
        img[(ir < 0.009) & (el < 1)] = np.array([12, 10, 10])
        img[(ir < 0.004) & (el < 1) & (th - sx * E_T < 0)] = np.array([240, 240, 235])  # catch-light
        lid = (np.abs(el - 1.0) < 0.35) & (ph > E_P)
        img[lid] = img[lid] * 0.35
        brow = (np.abs(ph - (E_P + 0.075 + 0.02 * np.cos((th - sx * E_T) * 8))) < 0.012) & (np.abs(th - sx * (E_T + 0.01)) < 0.085)
        img[brow] = np.array([44, 32, 24]) + g.normal(0, 8, (brow.sum(), 3))
        blob(sx * 1.57, 0.02, 0.12, 0.09, 0.0, (182, 120, 104))       # ears: pinker
    blob(0, 0.02, 0.035, 0.12, 0.12)                                    # nose bridge light
    for sx in (-1, 1):
        blob(sx * 0.07, -0.02, 0.03, 0.08, -0.18)                       # sides of the nose
        blob(sx * 0.03, -0.1, 0.012, 0.01, 0.0, (60, 36, 34))          # nostrils
    blob(0, -0.03, 0.05, 0.04, 0.0, (186, 118, 102))                    # nose tip redness
    mouth = (np.abs(ph + 0.34) < 0.006 * (1 - (th / 0.14) ** 2).clip(0)) & (np.abs(th) < 0.14)
    blob(0, -0.315, 0.12, 0.025, 0.0, (140, 84, 76))                    # upper lip
    blob(0, -0.37, 0.11, 0.03, 0.0, (156, 96, 86))                      # lower lip
    img[mouth] = np.array([52, 28, 26])
    blob(0, -0.43, 0.14, 0.04, -0.15)                                   # under-lip shadow
    blob(0, -0.62, 0.35, 0.18, -0.12)                                   # jaw underside
    jaw = np.exp(-(((th / 0.85) ** 2) + (((ph + 0.5) / 0.28) ** 2)) ** 2)          # soft jaw-shaped region
    jaw = np.maximum(jaw, np.exp(-(((th / 0.16) ** 2) + (((ph + 0.27) / 0.035) ** 2))))  # upper lip
    lips = np.exp(-(((th / 0.13) ** 2) + (((ph + 0.345) / 0.045) ** 2)) ** 2)
    dots = gaussian_filter(g.random((H, W)), 0.6)
    img[:] = img * (1 - 0.14 * (jaw * (1 - lips) * (dots > 0.53))[..., None])
    # a cut through the left eyebrow with dried blood, and grime
    cut = (np.abs((th + 0.4) * 0.6 - (ph - 0.2) * 0.8) < 0.006) & (np.abs(th + 0.4) < 0.06)
    blob(-0.4, 0.2, 0.05, 0.05, 0.0, (110, 50, 44))
    img[cut] = np.array([70, 14, 12])
    img[:] = img * (0.88 + 0.12 * gaussian_filter(g.random((H, W)), 12)[..., None] * 2)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(OUT / "face_survivor_albedo.png")
    (OUT / "face_survivor_albedo.png.import").write_text(_imp("face_survivor", "albedo"))
    print("[mat] face_survivor")


def paint_eye():
    """A bloodshot human eye (equirect), pressed against a plague mask lens."""
    W, H = 512, 256
    vv, uu = np.mgrid[0:H, 0:W] + 0.5
    th = (uu / W - 0.5) * 2 * np.pi
    ph = (0.5 - vv / H) * np.pi
    r = np.hypot(th, ph)
    img = np.zeros((H, W, 3)) + np.array([206, 196, 170])
    g = np.random.default_rng(3)
    for _ in range(40):  # veins crawling in from the edges
        t0 = g.uniform(-np.pi, np.pi)
        pts = [(t0, g.uniform(-1.2, 1.2))]
        for _ in range(30):
            t, p = pts[-1]
            pts.append((t * 0.93 + g.normal(0, 0.03), p * 0.93 + g.normal(0, 0.03)))
        for t, p in pts[:22]:
            m = np.hypot(th - t, ph - p) < 0.02
            img[m] = np.array([150, 30, 28])
    img[r < 0.42] = np.array([92, 104, 84])
    img[r < 0.2] = np.array([6, 6, 6])
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(OUT / "eye_bloodshot_albedo.png")
    (OUT / "eye_bloodshot_albedo.png.import").write_text(_imp("eye_bloodshot", "albedo"))
    print("[mat] eye_bloodshot")


if __name__ == "__main__":
    main()
