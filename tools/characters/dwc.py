# damned_waters/tools/characters/dwc.py
# Purpose: the .dwc character file ("Damned Waters Character"): everything the
# engine needs to draw and skin one character, written by build_characters.py and
# read by engine/src/character_file.cpp. Little-endian, no padding surprises:
#
#   char[4] "DWC1"   u32 version (1)
#   u32 joint_count, then joint_count x f32[3]      rest-pose joint positions (m, engine axes)
#   u32 part_count, then per part:
#       char[24] name  u32 vertex_count  u32 index_count
#       f32[3] position x V   f32[3] normal x V
#       u8[4]  colour   x V   (sRGB albedo)
#       u8     material x V   (dw::Mat)       u8 region x V   (dw::Region)
#       u8[4]  joint ids x V  f32[4] joint weights x V (sum to 1)
#       u16    index x I      (triangles, counter-clockwise from outside)
#   u32 anchor_count, then per anchor:
#       char[24] name  u8 joint  u8[3] pad  f32[3] position (joint space)  f32[3] direction (joint space)
#
# A part is a separately drawn mesh (body, jeans, hoodie...), at most 65535 vertices.
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAGIC, VERSION = b"DWC1", 1


@dataclass
class Part:
    name: str
    pos: np.ndarray            # (V,3) float32
    nrm: np.ndarray            # (V,3) float32
    col: np.ndarray            # (V,4) uint8
    mat: np.ndarray            # (V,) uint8
    region: np.ndarray         # (V,) uint8
    joints: np.ndarray         # (V,4) uint8
    weights: np.ndarray        # (V,4) float32
    tris: np.ndarray           # (T,3) int

    def validate(self):
        v = len(self.pos)
        assert v <= 65535, f"{self.name}: {v} vertices (max 65535)"
        for a, shape in ((self.nrm, (v, 3)), (self.col, (v, 4)), (self.joints, (v, 4)), (self.weights, (v, 4))):
            assert a.shape == shape, (self.name, a.shape, shape)
        assert self.mat.shape == (v,) and self.region.shape == (v,)
        assert len(self.tris) == 0 or (self.tris.min() >= 0 and self.tris.max() < v), self.name
        assert np.all(np.isfinite(self.pos)) and np.all(np.isfinite(self.nrm)), self.name


@dataclass
class Anchor:
    name: str
    joint: int
    pos: np.ndarray            # joint space
    dir: np.ndarray


@dataclass
class Character:
    joints: np.ndarray                         # (J,3)
    parts: list[Part] = field(default_factory=list)
    anchors: list[Anchor] = field(default_factory=list)


def _name(s: str) -> bytes:
    b = s.encode("ascii")[:23]
    return b + b"\0" * (24 - len(b))


def write(path: Path, ch: Character) -> None:
    out = bytearray(MAGIC + struct.pack("<I", VERSION))
    out += struct.pack("<I", len(ch.joints)) + np.asarray(ch.joints, "<f4").tobytes()
    out += struct.pack("<I", len(ch.parts))
    for p in ch.parts:
        p.validate()
        out += _name(p.name) + struct.pack("<II", len(p.pos), len(p.tris) * 3)
        out += np.asarray(p.pos, "<f4").tobytes() + np.asarray(p.nrm, "<f4").tobytes()
        out += np.asarray(p.col, "u1").tobytes() + np.asarray(p.mat, "u1").tobytes() + np.asarray(p.region, "u1").tobytes()
        out += np.asarray(p.joints, "u1").tobytes() + np.asarray(p.weights, "<f4").tobytes()
        out += np.asarray(p.tris, "<u2").tobytes()
    out += struct.pack("<I", len(ch.anchors))
    for a in ch.anchors:
        out += _name(a.name) + struct.pack("<B3x", a.joint)
        out += np.asarray(a.pos, "<f4").tobytes() + np.asarray(a.dir, "<f4").tobytes()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(bytes(out))


def read(path: Path) -> Character:
    b = Path(path).read_bytes()
    assert b[:4] == MAGIC, "not a .dwc file"
    o = 8
    def take(fmt):
        nonlocal o
        v = struct.unpack_from(fmt, b, o)
        o += struct.calcsize(fmt)
        return v
    def arr(dtype, count, shape):
        nonlocal o
        a = np.frombuffer(b, dtype=dtype, count=count, offset=o).reshape(shape)
        o += a.nbytes
        return a
    (nj,) = take("<I")
    ch = Character(arr("<f4", nj * 3, (nj, 3)))
    (np_,) = take("<I")
    for _ in range(np_):
        name = b[o:o + 24].split(b"\0")[0].decode(); o += 24
        nv, ni = take("<II")
        pos, nrm = arr("<f4", nv * 3, (nv, 3)), arr("<f4", nv * 3, (nv, 3))
        col, mat, reg = arr("u1", nv * 4, (nv, 4)), arr("u1", nv, (nv,)), arr("u1", nv, (nv,))
        jid, jw = arr("u1", nv * 4, (nv, 4)), arr("<f4", nv * 4, (nv, 4))
        tris = arr("<u2", ni, (ni // 3, 3))
        ch.parts.append(Part(name, pos, nrm, col, mat, reg, jid, jw, tris))
    (na,) = take("<I")
    for _ in range(na):
        name = b[o:o + 24].split(b"\0")[0].decode(); o += 24
        (j,) = take("<B3x")
        ch.anchors.append(Anchor(name, j, arr("<f4", 3, (3,)), arr("<f4", 3, (3,))))
    return ch
