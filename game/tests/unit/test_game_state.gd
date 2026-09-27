# damned_waters/game/tests/unit/test_game_state.gd
# Purpose: new-game defaults, conditions and save serialization.
extends GutTest


func test_new_game_starts_armed_and_healthy():
	GameState.reset_new_game()
	assert_true(GameState.inventory.has("handgun"))
	assert_eq(GameState.mags.pistol, 10)
	assert_eq(GameState.inventory.count_of("handgun_ammo"), 15)
	assert_eq(GameState.owned_weapons(), ["pistol"])
	assert_eq(GameState.condition(), "fine")


func test_condition_bands():
	GameState.reset_new_game()
	GameState.health = 50
	assert_eq(GameState.condition(), "caution")
	GameState.health = 20
	assert_eq(GameState.condition(), "danger")


func test_dict_round_trip_through_json():
	GameState.reset_new_game()
	GameState.set_flag("heard_thud")
	GameState.dead_enemies["pieter"] = true
	GameState.player_pos = Vector3(1, 0, 2)
	var d = JSON.parse_string(JSON.stringify(GameState.to_dict()))
	GameState.reset_new_game()
	GameState.from_dict(d)
	assert_true(GameState.has_flag("heard_thud"))
	assert_true(GameState.dead_enemies.has("pieter"))
	assert_almost_eq(GameState.player_pos, Vector3(1, 0, 2), Vector3.ONE * 1e-5)
