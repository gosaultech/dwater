# damned_waters/game/src/core/game_events.gd
# Purpose: global signal bus (autoload "GameEvents"). Systems announce facts
# here instead of holding references to each other; Telemetry, audio and UI
# just listen. Like a newsroom wire: reporters file, desks subscribe.
extends Node

signal room_entered(room_id: String)
signal camera_cut(room_id: String, shot_id: String)
signal prompt_changed(label: String)
signal interaction_requested(item: Dictionary)
signal player_damaged(amount: int, health: int)
signal player_died
signal shot_fired(hit: bool, enemy_id: String)
signal enemy_killed(enemy_id: String)
signal item_picked(item_id: String, count: int)
signal game_saved
signal ammo_changed(mag: int, reserve: int)
signal aiming_changed(is_aiming: bool)
signal noise_emitted(position: Vector3, radius: float)
signal control_scheme_changed(scheme: String)
signal debug_overlay_toggled(visible: bool)
signal demo_completed(stats: Dictionary)
signal flag_set(flag: String)
signal enemy_hit(enemy_id: String, damage: float, heavy: bool)
signal weapon_changed(weapon_id: String)
signal perfect_dodge
signal boss_started(boss_name: String, max_hp: float)
signal boss_health_changed(hp: float, max_hp: float)
signal boss_defeated
