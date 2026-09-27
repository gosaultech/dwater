# damned_waters/game/tests/unit/test_depth_codec.gd
# Purpose: GDScript codec == Python packer == shader decode. The vectors below
# are also asserted in tools/pipeline/tests/test_depth_pack.py.
extends GutTest

const VECTORS := [[0.0, 0, 0], [5.0, 40, 0], [32.0, 255, 255], [1.2345, 9, 224]]


func test_known_vectors():
	for v in VECTORS:
		assert_eq(DepthCodec.encode(v[0]), Vector2i(v[1], v[2]), "encode %s" % v[0])


func test_round_trip_precision_under_a_millimetre():
	for m in [0.06, 0.5, 2.0, 7.77, 19.9, 31.99]:
		var e := DepthCodec.encode(m)
		assert_almost_eq(DepthCodec.decode(e.x, e.y), m, 0.0005)
