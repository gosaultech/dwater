# damned_waters/game/src/core/depth_codec.gd
# Purpose: the GDScript twin of tools/pipeline/depth_pack.py and the decode in
# plate.gdshader. Tests pin all three to the same numbers.
class_name DepthCodec
extends RefCounted

const DEPTH_MAX_M := 32.0


static func encode(metres: float) -> Vector2i:
	var v := clampi(roundi(metres / DEPTH_MAX_M * 65535.0), 0, 65535)
	return Vector2i(v >> 8, v & 0xFF)


static func decode(hi: int, lo: int) -> float:
	return float(hi * 256 + lo) / 65535.0 * DEPTH_MAX_M
