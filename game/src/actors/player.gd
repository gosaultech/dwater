# damned_waters/game/src/actors/player.gd
# Purpose: the protagonist. Thin glue between input and the pure models:
# MovementMath, CutStableInput, Firearm/WeaponDB, InteractionQuery.
# Combat loop (action-oriented survival horror):
#   aim (auto-targets, auto-pitches to low enemies) -> shoot to stagger ->
#   KICK a staggered enemy to floor it -> finish or reposition.
#   DODGE through a telegraphed attack; dodging as it lands = PERFECT DODGE:
#   slow motion + your next shot within 1.5 s deals double damage.
# Keys: WASD move, Shift run, Q quick turn, RMB/K aim (W/S aim up/down),
# LMB/J/Space fire, R reload, C/Alt dodge, 1/2/F weapons, E interact/kick.
class_name Player
extends CharacterBody3D

enum Mode { NORMAL, AIM, QUICK_TURN, DODGE, KICK, HURT, DEAD }

const WALK := 1.9
const RUN := 3.8
const TANK_TURN_DEG := 150.0
const AIM_TURN_DEG := 110.0
const QUICK_TURN_TIME := 0.3
const DODGE_TIME := 0.42
const DODGE_IFRAMES := 0.3
const DODGE_SPEED := 6.2
const DODGE_COOLDOWN := 0.35
const KICK_TIME := 0.5
const KICK_RANGE := 1.8
const FOCUS_TIME := 1.5
const STRIDE := {"walk": 0.62, "run": 0.85}
const PROMPTS := {"door": "Open", "examine": "Examine", "pickup": "Take", "note": "Read", "save": "Use", "end": "Go"}
const MASK_WORLD := 1
const MASK_ENEMY := 4

var mode: Mode = Mode.NORMAL
var weapons := {}   # id -> Firearm
var weapon: Firearm
var body: ActorVisual
var room: Room
var surface := "wood"
var move_scale := 1.0

var _cut_input := CutStableInput.new()
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _mode_t := 0.0
var _qt_from := 0.0
var _dodge_dir := Vector3.ZERO
var _dodge_cd := 0.0
var _perfect_used := false
var _focus_t := 0.0
var _kick_target: Enemy
var _kick_done := false
var _invuln := 0.0
var _input_block := 0.0
var _step_accum := 0.0
var _prompt_id := ""
var _aim_target: Enemy
var _aim_snap := 0.0
var _manual_pitch := 0.0
var _laser: MeshInstance3D
var _laser_dot: MeshInstance3D
var _flash: OmniLight3D
var _flash_t := 0.0


func _ready() -> void:
	add_to_group("player")
	collision_layer = 2
	collision_mask = MASK_WORLD | MASK_ENEMY
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.28
	cap.height = 1.75
	cs.shape = cap
	cs.position.y = 0.875
	add_child(cs)
	body = CharacterFactory.creature("survivor", "humanoid")  # modelled survivor if built
	if body == null:
		body = CharacterFactory.create("survivor")  # else an installed rigged model
	if body == null:
		var m := Mannequin.new()
		m.with_gun = true
		body = m
	add_child(body.build())
	_build_laser()
	_flash = OmniLight3D.new()
	_flash.light_color = Color(1.0, 0.75, 0.4)
	_flash.omni_range = 4.5
	_flash.light_energy = 0.0
	_flash.position = Vector3(0, 1.45, -0.7)
	add_child(_flash)
	for id in WeaponDB.ORDER:
		weapons[id] = Firearm.new(id, int(GameState.mags.get(id, WeaponDB.get_weapon(id).mag_size)))
	equip(GameState.equipped if GameState.owned_weapons().has(GameState.equipped) else "pistol", false)


func place(pos: Vector3, yaw: float) -> void:
	global_position = pos
	rotation.y = yaw
	velocity = Vector3.ZERO
	mode = Mode.NORMAL
	_cut_input.reset()
	_set_aiming(false)
	for id in weapons:
		weapons[id].mag = int(GameState.mags.get(id, weapons[id].mag))


func equip(id: String, announce: bool = true) -> void:
	if not weapons.has(id):
		return
	weapon = weapons[id]
	GameState.equipped = id
	body.set_weapon(id)
	if announce:
		AudioDirector.play("weapon_switch")
		GameEvents.weapon_changed.emit(id)
	_emit_ammo()


func _cycle_weapon(direct: String = "") -> void:
	var owned := GameState.owned_weapons()
	var next := direct
	if next == "":
		if owned.size() < 2:
			return
		next = owned[(owned.find(weapon.id) + 1) % owned.size()]
	if owned.has(next) and next != weapon.id:
		equip(next)


func block_input(seconds: float) -> void:
	_input_block = maxf(_input_block, seconds)


func is_dead() -> bool:
	return mode == Mode.DEAD


func forward() -> Vector3:
	return MovementMath.forward_from_yaw(rotation.y)


func _physics_process(delta: float) -> void:
	for id in weapons:
		weapons[id].tick(delta)
	_invuln = maxf(0.0, _invuln - delta)
	_input_block = maxf(0.0, _input_block - delta)
	_dodge_cd = maxf(0.0, _dodge_cd - delta)
	_focus_t = maxf(0.0, _focus_t - delta)
	_flash_t = maxf(0.0, _flash_t - delta)
	_flash.light_energy = 7.0 if _flash_t > 0.0 else 0.0
	_mode_t += delta
	var accepting := _input_block <= 0.0
	match mode:
		Mode.DEAD:
			velocity.x = 0.0
			velocity.z = 0.0
		Mode.QUICK_TURN:
			var k := minf(1.0, _mode_t / QUICK_TURN_TIME)
			rotation.y = _qt_from + PI * ease(k, -2.0)
			velocity.x = 0.0
			velocity.z = 0.0
			if k >= 1.0:
				_set_mode(Mode.NORMAL)
		Mode.DODGE:
			var spd := DODGE_SPEED * (1.0 - ease(minf(1.0, _mode_t / DODGE_TIME), 0.5))
			velocity.x = _dodge_dir.x * spd
			velocity.z = _dodge_dir.z * spd
			if _mode_t >= DODGE_TIME:
				_set_mode(Mode.AIM if accepting and Input.is_action_pressed("aim") else Mode.NORMAL)
		Mode.KICK:
			velocity.x = 0.0
			velocity.z = 0.0
			if not _kick_done and _mode_t >= 0.18:
				_kick_done = true
				AudioDirector.play("kick", 0.0, 0.05)
				if is_instance_valid(_kick_target) and not _kick_target.is_dead():
					_kick_target.kick(global_position)
			if _mode_t >= KICK_TIME:
				_set_mode(Mode.NORMAL)
		Mode.HURT:
			velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
			velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)
			if _mode_t >= 0.45:
				_set_mode(Mode.NORMAL)
		Mode.AIM:
			_aim(delta, accepting)
		Mode.NORMAL:
			_move(delta, accepting)
	velocity.y = 0.0 if is_on_floor() else velocity.y - _gravity * delta
	move_and_slide()
	GameState.player_pos = global_position
	GameState.player_yaw = rotation.y
	if mode != Mode.DEAD:
		_update_prompt(accepting)
	_animate(delta)


func _set_mode(m: Mode) -> void:
	if mode == Mode.AIM and m != Mode.AIM:
		_set_aiming(false)
	mode = m
	_mode_t = 0.0
	if m == Mode.AIM:
		_set_aiming(true)


func _common_actions(input: Vector2, accepting: bool) -> bool:
	if not accepting:
		return false
	if Input.is_action_just_pressed("dodge") and _dodge_cd <= 0.0:
		_start_dodge(input)
		return true
	if Input.is_action_just_pressed("reload"):
		_reload()
	if Input.is_action_just_pressed("weapon_cycle"):
		_cycle_weapon()
	elif Input.is_action_just_pressed("weapon_1"):
		_cycle_weapon("pistol")
	elif Input.is_action_just_pressed("weapon_2"):
		_cycle_weapon("shotgun")
	return false


func _move(delta: float, accepting: bool) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_back", "move_forward") if accepting else Vector2.ZERO
	var running := accepting and Input.is_action_pressed("run")
	var speed := (RUN if running else WALK) * move_scale * (0.7 if GameState.condition() == "danger" else 1.0)
	if _common_actions(input, accepting):
		return
	if accepting and Input.is_action_just_pressed("aim"):
		_enter_aim()
		return
	if accepting and (Input.is_action_just_pressed("quick_turn")
			or (GameState.control_scheme == "tank" and input.y < -0.5 and Input.is_action_just_pressed("run"))):
		_qt_from = rotation.y
		_set_mode(Mode.QUICK_TURN)
		return
	var planar := Vector3.ZERO
	if GameState.control_scheme == "tank":
		rotation.y += MovementMath.tank_turn_delta(input.x, deg_to_rad(TANK_TURN_DEG), delta)
		planar = MovementMath.tank_velocity(input.y, rotation.y, speed)
	else:
		var basis := _cut_input.basis_for(input, CameraDirector.live_basis())
		var dir := MovementMath.camera_relative_direction(input, basis)
		planar = dir * speed
		var yaw := MovementMath.facing_from_direction(dir, rotation.y)
		rotation.y = lerp_angle(rotation.y, yaw, MovementMath.smoothing_alpha(12.0, delta))
	velocity.x = planar.x
	velocity.z = planar.z
	var moved := Vector2(velocity.x, velocity.z).length() * delta
	_step_accum += moved
	var stride: float = STRIDE.run if running else STRIDE.walk
	if moved > 0.0 and _step_accum >= stride:
		_step_accum = 0.0
		AudioDirector.play("step_" + surface, -6.0 if not running else -2.0, 0.08)
		GameEvents.noise_emitted.emit(global_position, 6.0 if running else 2.5)


func _start_dodge(input: Vector2) -> void:
	var dir := Vector3.ZERO
	if GameState.control_scheme == "tank" or mode == Mode.AIM:
		var right := forward().cross(Vector3.UP)
		dir = right * input.x + forward() * maxf(input.y, 0.0)
	else:
		dir = MovementMath.camera_relative_direction(input, CameraDirector.live_basis())
	if dir.length_squared() < 0.04:
		dir = -forward()  # no direction: hop backwards
	_dodge_dir = dir.normalized()
	_dodge_cd = DODGE_TIME + DODGE_COOLDOWN
	_perfect_used = false
	var keep_aim := mode == Mode.AIM
	mode = Mode.DODGE
	_mode_t = 0.0
	if not keep_aim:
		_set_aiming(false)
	AudioDirector.play("dodge", -2.0, 0.06)


func _enter_aim() -> void:
	_set_mode(Mode.AIM)
	_aim_target = _find_aim_target()
	_aim_snap = 0.2
	_manual_pitch = 0.0


func _find_aim_target() -> Enemy:
	var best: Enemy = null
	var best_d := 14.0
	for e in get_tree().get_nodes_in_group("enemies"):
		if not e is Enemy or e.is_dead() or not e.is_targetable():
			continue
		var to: Vector3 = e.global_position - global_position
		var ang := absf(Vector2(forward().x, forward().z).angle_to(Vector2(to.x, to.z)))
		if to.length() < best_d and ang < deg_to_rad(100.0):
			best = e
			best_d = to.length()
	return best


func _aim(delta: float, accepting: bool) -> void:
	velocity.x = 0.0
	velocity.z = 0.0
	if not accepting or not Input.is_action_pressed("aim"):
		_set_mode(Mode.NORMAL)
		return
	var input := Input.get_vector("move_left", "move_right", "move_back", "move_forward")
	if _common_actions(input, accepting):
		return
	var has_target := is_instance_valid(_aim_target) and _aim_target.is_targetable()
	if _aim_snap > 0.0 and has_target and absf(input.x) < 0.2:
		_aim_snap -= delta
		var want := MovementMath.yaw_towards(global_position, _aim_target.global_position, rotation.y)
		rotation.y = MovementMath.step_yaw(rotation.y, want, 9.0 * delta)
	else:
		rotation.y += MovementMath.tank_turn_delta(input.x, deg_to_rad(AIM_TURN_DEG), delta)
	# Auto-pitch toward the target's centre (so low crawlers are hittable), plus manual W/S offset.
	var base_pitch := 0.0
	if has_target:
		var ap := _aim_target.aim_point()
		var flat := Vector2(ap.x - global_position.x, ap.z - global_position.z).length()
		base_pitch = atan2(ap.y - (global_position.y + 1.42), maxf(flat, 0.3))
	_manual_pitch = move_toward(_manual_pitch, input.y * 0.4, 2.0 * delta)
	var pitch := clampf(base_pitch + _manual_pitch, -0.8, 0.55)
	body.aim_pitch = lerpf(body.aim_pitch, pitch, MovementMath.smoothing_alpha(12.0, delta))
	var hit := _ray(_muzzle(), _aim_dir(), 25.0, MASK_WORLD | MASK_ENEMY)
	var end: Vector3 = hit.position if hit else _muzzle() + _aim_dir() * 25.0
	_draw_laser(_muzzle(), end)
	if Input.is_action_just_pressed("fire"):
		_fire()


func _muzzle() -> Vector3:
	return global_position + Vector3.UP * 1.42 + forward() * 0.55


func _aim_dir() -> Vector3:
	return (forward() * cos(body.aim_pitch) + Vector3.UP * sin(body.aim_pitch)).normalized()


func _fire() -> void:
	var cfg := weapon.cfg
	if weapon.mag <= 0:
		if GameState.inventory.count_of(cfg.ammo) > 0:
			_reload()
		else:
			AudioDirector.play("dry_fire")
		return
	if not weapon.fire():
		return
	GameState.mags[weapon.id] = weapon.mag
	GameState.bump("shots")
	AudioDirector.play(cfg.sfx, 0.0, 0.04)
	_flash_t = 0.06 if weapon.id == "shotgun" else 0.045
	GameEvents.noise_emitted.emit(global_position, float(cfg.noise))
	# Pellets: accumulate per enemy so one blast = one hit reaction.
	var tally := {}  # Enemy -> [damage, pellets, weak, pos]
	var spread := deg_to_rad(float(cfg.spread_deg))
	var focused := _focus_t > 0.0
	for i in int(cfg.pellets):
		var dir := _aim_dir()
		if spread > 0.0:
			dir = dir.rotated(Vector3.UP, randf_range(-spread, spread))
			dir = dir.rotated(forward().cross(Vector3.UP).normalized(), randf_range(-spread, spread) * 0.6)
		var hit := _ray(_muzzle(), dir, float(cfg.range), MASK_WORLD | MASK_ENEMY)
		if hit and hit.collider is Enemy:
			var e: Enemy = hit.collider
			var weak: bool = e.is_weak_hit(hit.position)
			var dmg := weapon.damage_for(weak, 0.0 if focused else randf(), _muzzle().distance_to(hit.position))
			if focused:
				dmg *= 2.0
			var t: Array = tally.get(e, [0.0, 0, false, hit.position])
			tally[e] = [t[0] + dmg, t[1] + 1, t[2] or weak, hit.position]
	var knock_hits := int(cfg.knockdown_hits)
	for e in tally:
		var t: Array = tally[e]
		e.take_hit(t[0], t[2], t[3], int(cfg.stagger_power), knock_hits > 0 and t[1] >= knock_hits)
		GameState.bump("hits")
		GameEvents.shot_fired.emit(true, e.enemy_id)
	if tally.is_empty():
		GameEvents.shot_fired.emit(false, "")
	if focused:
		_focus_t = 0.0
	_emit_ammo()


func _reload() -> void:
	var ammo: String = weapon.cfg.ammo
	var taken := weapon.reload(GameState.inventory.count_of(ammo))
	if taken > 0:
		GameState.inventory.remove(ammo, taken)
		GameState.mags[weapon.id] = weapon.mag
		AudioDirector.play("shotgun_reload" if weapon.id == "shotgun" else "reload")
		_emit_ammo()


func _emit_ammo() -> void:
	if weapon:
		GameEvents.ammo_changed.emit(weapon.mag, GameState.inventory.count_of(weapon.cfg.ammo))


func _set_aiming(on: bool) -> void:
	if _laser:
		_laser.visible = on
		_laser_dot.visible = on
	if not on and body:
		body.aim_pitch = 0.0
	GameEvents.aiming_changed.emit(on)
	if on:
		_emit_ammo()


func _kickable() -> Enemy:
	for e in get_tree().get_nodes_in_group("enemies"):
		if e is Enemy and e.can_be_kicked():
			var to: Vector3 = e.global_position - global_position
			to.y = 0.0
			if to.length() <= KICK_RANGE and absf(Vector2(forward().x, forward().z).angle_to(Vector2(to.x, to.z))) < deg_to_rad(60.0):
				return e
	return null


func _update_prompt(accepting: bool) -> void:
	var kick_target: Enemy = _kickable() if mode in [Mode.NORMAL, Mode.AIM] else null
	var best := {}
	if kick_target == null and room and mode == Mode.NORMAL:
		best = InteractionQuery.best(room.interactables, global_position, forward())
	var id: String = "__kick" if kick_target else String(best.get("id", ""))
	if id != _prompt_id:
		_prompt_id = id
		var label: String = "Kick" if kick_target else (PROMPTS.get(best.get("kind", ""), "") if id != "" else "")
		GameEvents.prompt_changed.emit(label)
	if not accepting or not Input.is_action_just_pressed("interact"):
		return
	if kick_target:
		_kick_target = kick_target
		_kick_done = false
		rotation.y = MovementMath.yaw_towards(global_position, kick_target.global_position, rotation.y)
		_set_mode(Mode.KICK)
	elif id != "":
		GameEvents.interaction_requested.emit(best)


func take_damage(amount: int, from: Vector3) -> void:
	if mode == Mode.DEAD:
		return
	if mode == Mode.DODGE and _mode_t <= DODGE_IFRAMES:
		if not _perfect_used:
			_perfect_used = true
			_focus_t = FOCUS_TIME
			GameState.bump("perfect_dodges")
			AudioDirector.play("perfect_dodge")
			GameEvents.perfect_dodge.emit()
		return
	if _invuln > 0.0:
		return
	GameState.health = maxi(0, GameState.health - amount)
	GameState.bump("damage_taken", amount)
	GameEvents.player_damaged.emit(amount, GameState.health)
	AudioDirector.play("player_hurt", 0.0, 0.06)
	if GameState.health <= 0:
		_set_mode(Mode.DEAD)
		collision_layer = 0
		GameEvents.prompt_changed.emit("")
		GameEvents.player_died.emit()
		return
	_set_mode(Mode.HURT)
	_invuln = 0.9
	var away := (global_position - from)
	away.y = 0.0
	velocity = away.normalized() * 2.5


func _animate(delta: float) -> void:
	var planar := Vector2(velocity.x, velocity.z).length()
	body.speed = planar
	match mode:
		Mode.DEAD:
			body.pose = "dead"
		Mode.HURT:
			body.pose = "hurt"
		Mode.DODGE:
			body.pose = "dodge"
		Mode.KICK:
			body.pose = "kick"
		Mode.AIM:
			body.pose = "reload" if weapon.is_reloading() else "aim"
		_:
			if weapon.is_reloading():
				body.pose = "reload"
			elif planar > 2.6:
				body.pose = "run"
			elif planar > 0.1:
				body.pose = "walk"
			else:
				body.pose = "idle"
	body.animate(delta)


func _ray(from: Vector3, dir: Vector3, length: float, mask: int) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, from + dir * length, mask, [get_rid()])
	return get_world_3d().direct_space_state.intersect_ray(q)


func _build_laser() -> void:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(1.0, 0.08, 0.05, 0.55)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_laser = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.006, 0.006, 1.0)
	bm.material = m
	_laser.mesh = bm
	_laser.top_level = true
	_laser.visible = false
	add_child(_laser)
	_laser_dot = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.02
	sm.height = 0.04
	var dm := m.duplicate() as StandardMaterial3D
	dm.albedo_color = Color(1, 0.15, 0.1, 1)
	sm.material = dm
	_laser_dot.mesh = sm
	_laser_dot.top_level = true
	_laser_dot.visible = false
	add_child(_laser_dot)


func _draw_laser(from: Vector3, to: Vector3) -> void:
	var len := from.distance_to(to)
	if len < 0.01:
		return
	_laser.global_position = (from + to) * 0.5
	_laser.look_at(to, Vector3.UP if absf((to - from).normalized().y) < 0.99 else Vector3.FORWARD)
	_laser.scale = Vector3(1, 1, len)
	_laser_dot.global_position = to
