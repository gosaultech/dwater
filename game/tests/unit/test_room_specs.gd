# damned_waters/game/tests/unit/test_room_specs.gd
# Purpose: data integrity for every shipped room: valid spec, doors lead to
# real rooms/spawns, every shot has rendered plates, spawns aren't inside props.
extends GutTest

const ROOMS := ["gang", "voorkamer", "kelder"]


func test_all_rooms_parse_and_validate():
	for r in ROOMS:
		var s := RoomSpec.load_room(r)
		assert_true(s.is_valid(), "%s: %s" % [r, s.errors])


func test_doors_link_to_existing_spawns():
	for r in ROOMS:
		for it in RoomSpec.load_room(r).interactables:
			if it.kind == "door":
				var target := RoomSpec.load_room(it.target_room)
				assert_true(target.is_valid(), "door %s -> %s" % [it.id, it.target_room])
				assert_true(target.spawns.has(it.target_spawn), "door %s -> spawn %s" % [it.id, it.target_spawn])


func test_every_shot_has_plates():
	for r in ROOMS:
		for s in RoomSpec.load_room(r).shots:
			for layer in ["color", "depth"]:
				var p := RoomSpec.plate_path(r, s.id, layer)
				assert_true(ResourceLoader.exists(p), "missing %s" % p)


func test_every_spawn_is_covered_by_a_camera_zone():
	for r in ROOMS:
		var s := RoomSpec.load_room(r)
		for id in s.spawns:
			var p: Vector3 = s.spawns[id].pos
			assert_ne(ShotSelector.select(s.shots, "", Vector2(p.x, p.z)), "", "%s/%s" % [r, id])
			var covered := s.shots.any(func(sh): return ShotSelector.zone_has(sh.zone, Vector2(p.x, p.z)))
			assert_true(covered, "%s spawn %s outside all zones" % [r, id])


func test_spawns_are_not_inside_collision():
	for r in ROOMS:
		var s := RoomSpec.load_room(r)
		for id in s.spawns:
			var p: Vector3 = s.spawns[id].pos + Vector3.UP * 0.9
			for b in s.collision_boxes():
				var local: Vector3 = (p - b.center).rotated(Vector3.UP, -b.yaw)
				var half: Vector3 = b.size / 2.0 + Vector3(0.28, 0, 0.28)
				var inside := absf(local.x) < half.x and absf(local.y) < half.y and absf(local.z) < half.z
				assert_false(inside, "%s spawn %s overlaps a collider at %s" % [r, id, b.center])
