# damned_waters/game/tests/unit/test_inventory.gd
# Purpose: slots, stacking, removal, overflow and save round-trips.
extends GutTest


func test_stacks_ammo_up_to_cap():
	var inv := Inventory.new(2)
	assert_eq(inv.add("handgun_ammo", 50), 0)
	assert_eq(inv.add("handgun_ammo", 20), 0)
	assert_eq(inv.count_of("handgun_ammo"), 70)
	assert_eq(inv.free_slots(), 0, "60 cap -> spills into a second slot")


func test_overflow_is_reported():
	var inv := Inventory.new(1)
	inv.add("cellar_key", 1)
	assert_eq(inv.add("first_aid", 1), 1)


func test_remove_empties_slot():
	var inv := Inventory.new(4)
	inv.add("cellar_key", 1)
	assert_eq(inv.remove("cellar_key", 1), 1)
	assert_false(inv.has("cellar_key"))
	assert_eq(inv.free_slots(), 4)


func test_round_trip():
	var inv := Inventory.new(8)
	inv.add("handgun", 1)
	inv.add("handgun_ammo", 15)
	var back := Inventory.from_array(JSON.parse_string(JSON.stringify(inv.to_array())))
	assert_eq(back.count_of("handgun_ammo"), 15)
	assert_true(back.has("handgun"))
