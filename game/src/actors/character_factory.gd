# damned_waters/game/src/actors/character_factory.gd
# Purpose: pick the best available visual for a character id. A real model is
# used when data/characters/<id>.json exists AND its .glb is present;
# otherwise the procedural placeholder keeps the game playable.
class_name CharacterFactory
extends RefCounted


static func manifest(id: String) -> Dictionary:
	var path := "res://data/characters/%s.json" % id
	if not FileAccess.file_exists(path):
		return {}
	var m = JSON.parse_string(FileAccess.get_file_as_string(path))
	if typeof(m) != TYPE_DICTIONARY or not ResourceLoader.exists(String(m.get("model", ""))):
		return {}
	return m


## A jointed creature from enemies_v2.py, if its .glb has been built.
static func creature(model_id: String, species: String) -> ActorVisual:
	if not CreatureModel.available(model_id):
		return null
	if species in ["humanoid", "crawler"]:  # skinned: one continuous mesh on a skeleton
		return SkeletalCreature.new().setup(model_id, species)
	return CreatureModel.new().setup(model_id, species)


static func create(id: String) -> ActorVisual:
	var m := manifest(id)
	return CharacterModel.new().setup(m) if not m.is_empty() else null
