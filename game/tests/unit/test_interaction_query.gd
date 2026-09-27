# damned_waters/game/tests/unit/test_interaction_query.gd
# Purpose: you interact with what you face, within reach, nearest first.
extends GutTest

var items := [
	{"id": "note", "pos": Vector3(0, 1, -0.8), "radius": 1.0},
	{"id": "door", "pos": Vector3(0, 1, 0.8), "radius": 1.0},
	{"id": "far", "pos": Vector3(0, 1, -3.0), "radius": 1.0},
]


func test_picks_item_in_front():
	assert_eq(InteractionQuery.best(items, Vector3.ZERO, Vector3(0, 0, -1)).get("id"), "note")


func test_ignores_item_behind():
	assert_eq(InteractionQuery.best(items, Vector3.ZERO, Vector3(0, 0, 1)).get("id"), "door")


func test_out_of_reach_returns_empty():
	assert_true(InteractionQuery.best(items, Vector3(5, 0, 5), Vector3(0, 0, -1)).is_empty())


func test_point_blank_ignores_facing():
	var one := [{"id": "x", "pos": Vector3(0.2, 1, 0), "radius": 1.0}]
	assert_eq(InteractionQuery.best(one, Vector3.ZERO, Vector3(0, 0, 1)).get("id"), "x")
