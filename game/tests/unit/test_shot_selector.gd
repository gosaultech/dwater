# damned_waters/game/tests/unit/test_shot_selector.gd
# Purpose: camera zone selection, including hysteresis in overlapping zones.
extends GutTest

var shots := [
	{"id": "a", "zone": Rect2(0, 0, 2, 5.7), "priority": 0},
	{"id": "b", "zone": Rect2(0, 5.3, 2, 4.7), "priority": 0},
	{"id": "close", "zone": Rect2(0, 0, 2, 1), "priority": 5},
]


func test_initial_pick_uses_zone():
	assert_eq(ShotSelector.select(shots, "", Vector2(1, 8)), "b")


func test_priority_wins_on_entry():
	assert_eq(ShotSelector.select(shots, "b", Vector2(1, 0.5)), "close")


func test_hysteresis_keeps_current_in_overlap():
	assert_eq(ShotSelector.select(shots, "a", Vector2(1, 5.5)), "a")
	assert_eq(ShotSelector.select(shots, "b", Vector2(1, 5.5)), "b")


func test_leaving_zone_switches():
	assert_eq(ShotSelector.select(shots, "a", Vector2(1, 6.0)), "b")


func test_zone_edges_are_inclusive():
	assert_true(ShotSelector.zone_has(Rect2(0, 0, 2, 2), Vector2(2, 2)))


func test_outside_everything_keeps_current():
	assert_eq(ShotSelector.select(shots, "a", Vector2(50, 50)), "a")
