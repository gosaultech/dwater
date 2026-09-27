# damned_waters/tools/pipeline/depth_pack.py
# Purpose: turn Blender's renders into game-ready plates.
#   <shot>_depth16.png (16-bit gray) -> <shot>_depth.png (RG8: R = high byte, G = low byte)
#   <shot>_color.png                 -> copied as-is
# and write a Godot .import file next to each so the engine never VRAM-compresses
# them (compression would blur the depth bytes into garbage).
#
# Why RG8? Godot's PNG loader strips 16-bit images to 8-bit. Splitting one
# 16-bit number across two 8-bit channels is like writing "1,234" as two
# cheques of "1" thousand and "234" units: nothing is lost, it just travels
# in two envelopes. The shader (game/src/world/plate.gdshader) reassembles it.
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[2]

# Godot 4.7 texture importer params: lossless, no mipmaps, never auto-switch to
# VRAM compression when the texture is used in 3D (detect_3d/compress_to=0).
IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="{res_path}"

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=false
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


def pack_depth16(depth16: np.ndarray) -> np.ndarray:
    """uint16 HxW -> uint8 HxWx3 (R=hi, G=lo, B=0)."""
    if depth16.dtype != np.uint16:
        raise TypeError(f"expected uint16 depth, got {depth16.dtype}")
    out = np.zeros((*depth16.shape, 3), dtype=np.uint8)
    out[..., 0] = depth16 >> 8
    out[..., 1] = depth16 & 0xFF
    return out


def unpack_rg8(rgb: np.ndarray) -> np.ndarray:
    """Inverse of pack_depth16 (mirrors the shader's decode)."""
    return (rgb[..., 0].astype(np.uint16) << 8) | rgb[..., 1].astype(np.uint16)


def read_depth16(path: Path) -> np.ndarray:
    im = Image.open(path)
    arr = np.array(im)
    if arr.dtype != np.uint16:  # Pillow may hand back int32 for 'I' mode
        arr = arr.astype(np.uint16)
    if arr.ndim == 3:  # defensive: an RGB 16-bit export
        arr = arr[..., 0]
    return arr


def import_text(res_path: str) -> str:
    return IMPORT_TEMPLATE.format(res_path=res_path)


def process_room(src_room: Path, dst_room: Path, game_root: Path) -> list[str]:
    dst_room.mkdir(parents=True, exist_ok=True)
    written = []
    for color in sorted(src_room.glob("*_color.png")):
        shot = color.name.removesuffix("_color.png")
        depth = src_room / f"{shot}_depth16.png"
        if not depth.exists():
            raise FileNotFoundError(f"missing depth for {color}")
        c_dst = dst_room / f"{shot}_color.png"
        d_dst = dst_room / f"{shot}_depth.png"
        shutil.copyfile(color, c_dst)
        d16 = read_depth16(depth)
        c_size = Image.open(color).size
        if (d16.shape[1], d16.shape[0]) != c_size:
            raise ValueError(f"{shot}: color {c_size} and depth {d16.shape[::-1]} sizes differ")
        Image.fromarray(pack_depth16(d16), "RGB").save(d_dst, optimize=False, compress_level=6)
        for f in (c_dst, d_dst):
            res = "res://" + f.relative_to(game_root).as_posix()
            Path(str(f) + ".import").write_text(import_text(res), encoding="utf-8")
            written.append(res)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pack Blender renders into Godot plates")
    ap.add_argument("--src", default=str(REPO / "pipeline_out" / "renders"))
    ap.add_argument("--game", default=str(REPO / "game"))
    a = ap.parse_args(argv)
    game = Path(a.game)
    for room in sorted(p for p in Path(a.src).iterdir() if p.is_dir()):
        files = process_room(room, game / "assets" / "rooms" / room.name, game)
        print(f"[pack] {room.name}: {len(files)} plates")


if __name__ == "__main__":
    main()
