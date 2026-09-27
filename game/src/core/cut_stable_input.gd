# damned_waters/game/src/core/cut_stable_input.gd
# Purpose: keep modern (camera-relative) controls stable across camera cuts.
# Problem: you hold "up" to walk away from the camera; the camera cuts to face
# you; "up" now means "toward camera" and you walk straight back into the cut.
# Fix: keep the camera basis that was live when you started holding a direction
# until you release the stick or change direction substantially.
# Analogy: a runner keeps heading for the finish line even when the TV feed
# switches cameras; only the viewer's perspective changes.
class_name CutStableInput
extends RefCounted

const DEADZONE := 0.2
const REBASE_ANGLE := deg_to_rad(35.0)

var _held_basis := Basis.IDENTITY
var _held_input := Vector2.ZERO
var _holding := false


func basis_for(input: Vector2, live_basis: Basis) -> Basis:
	if input.length() < DEADZONE:
		_holding = false
		return live_basis
	if not _holding or absf(input.angle_to(_held_input)) > REBASE_ANGLE:
		_holding = true
		_held_basis = live_basis
		_held_input = input
	return _held_basis


func reset() -> void:
	_holding = false
