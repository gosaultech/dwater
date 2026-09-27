# damned_waters/game/src/actors/actor_visual.gd
# Purpose: the contract every character visual fulfils, so gameplay code never
# cares whether it's driving the procedural placeholder (Mannequin) or a real
# rigged model (CharacterModel: MetaHuman, Character Creator, Mixamo, ...).
# Analogy: a DI box. Any instrument plugs in; the desk sees the same signal.
class_name ActorVisual
extends Node3D

var pose := "idle"      # idle|walk|run|aim|reload|shamble|windup|strike|stagger|hurt|dodge|kick|floored|dead
var speed := 0.0        # planar m/s, drives locomotion playback rate
var aim_pitch := 0.0    # radians, + is up
var head: Node3D        # attach point for particles (drips etc.)


func build() -> ActorVisual:
	return self


func animate(_delta: float) -> void:
	pass


func set_weapon(_weapon_id: String) -> void:
	pass


## Named attach point (joint or bone), or null.
func joint(_n: String) -> Node3D:
	return null
