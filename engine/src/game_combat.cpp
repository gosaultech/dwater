// damned_waters/engine/src/game_combat.cpp
// Purpose: the fight in the hall.
//  * The survivor's verbs, read as actions (input.hpp): move (analog, with a little weight), aim
//    (locks on; the right stick or the mouse moves the aim over the body: head, arms, legs; a flick
//    or the wheel switches target), fire, reload, switch guns, dodge, quick turn, and the kick:
//    a counter in the last moment of a lunge, or a Drowned staggered or overbalanced kicked down.
//    A dodge in the last moment of a lunge is perfect: it overbalances, the next shot does double.
//  * The Drowned: senses, the brain's events, the lunge, crawling on after losing a leg.
//  * What a shot does: wounds that stay, limbs that come off, heads that burst, blood on the floor.
//  * The hall's script: one Drowned, then a bang at the front door and two more.
// The rules themselves (damage, magazines, when a limb comes off, the brain) are pure and
// unit-tested in combat.hpp and core.hpp; this file is the referee that applies them to the bodies
// in the room and makes the noise.
#include <algorithm>
#include <array>
#include <cmath>

#include "cast_guns.hpp"
#include "dw/death.hpp"
#include "game.hpp"

namespace dw {
namespace {
using namespace verbs;
constexpr size_t MAX_ENEMIES = 8;
constexpr float SIGHT = 9.0f;                              // how far a Drowned sees (m)
constexpr float VIEW_HALF = 60.0f * kPi / 180.0f;          // ... and how wide (half angle)
constexpr float STRIKE_HALF = 55.0f * kPi / 180.0f;        // a lunge only lands in front of it
constexpr float PLAYER_R = 0.28f, ENEMY_R = 0.32f;         // bodies on the floor plane (m)
constexpr float LOCK_HALF = 15.0f * kPi / 180.0f;          // auto-aim holds while the gun faces this close to the target
constexpr float ACCEL = 24.0f, DECEL = 32.0f;              // m/s^2: full run in a sixth of a second, a stop in an eighth
constexpr float TURN = 14.0f, PIVOT = 24.0f;               // rad/s turning to the stick; a reversal pivots faster
constexpr int VARIANTS[] = {0, 2, 1};                      // who they were: the office worker, Pieter, Sanne

float ease_out(float t) { return 1.0f - (1.0f - t) * (1.0f - t); }
Vector3 flat_forward(float yaw) { const V2 f = forward_from_yaw(yaw); return {f.x, 0, f.z}; }
P3 p3(Vector3 v) { return {v.x, v.y, v.z}; }

// What the body shows for what the mind is doing.
Pose pose_for(const Enemy& e) {
    const EnemyBrain& b = e.brain;
    if (b.state == EState::Dead) return Pose::Dead;
    if (e.crawling) {
        if (b.state == EState::Attack) return b.t >= b.windup ? Pose::CrawlStrike : Pose::CrawlWindup;
        return Pose::Crawl;
    }
    switch (b.state) {
        case EState::Pursuit:
        case EState::Retreat: return Pose::Shamble;
        case EState::Attack: return b.t >= b.windup ? Pose::Strike : Pose::Windup;
        case EState::Stagger: return e.stumble > 0 ? Pose::Strike : Pose::Stagger;   // overbalanced: carried on by its lunge
        case EState::Floored: return Pose::Floored;
        default: return Pose::Idle;
    }
}

// How much a lunge takes out of him: less from a crawler; a Drowned with no hands and no jaw left
// can only shove.
float strike_damage(const Enemy& e) {
    if (e.damage.hands() == 0 && e.damage.off[R_JAW]) return 5.0f;
    return e.bite;
}
}  // namespace

// ── Setting up ──────────────────────────────────────────────────────────────────

void Game::reset_fight() {
    if (pmode_ == PMode::Dead) {   // a retry: the survivor gets up clean
        hero_.unload();
        hero_ = Character::make(Kind::Survivor);
    }
    for (auto& e : enemies_) e.body.unload();
    enemies_.clear();
    enemies_.reserve(MAX_ENEMIES);
    for (const auto& s : spec_.enemies) {
        if (s.kind != "verdronkene" || enemies_.size() >= MAX_ENEMIES) continue;
        Enemy e;
        e.id = s.id;
        e.variant = VARIANTS[enemies_.size() % 3];
        e.a = {s.pos.x, s.pos.z, s.yaw};
        e.active = s.requires_flag.empty();   // the rest wait for the script
        e.gurgle = 2.0f + 3.0f * frand();
        e.body = Character::make(Kind::Drowned, e.variant);
        enemies_.push_back(std::move(e));
    }
    fx_.clear();
    script_ = {};
    health_ = 100;
    inv_ = {};
    inv_.add(I_HANDGUN, 1);
    inv_.add(I_SHOTGUN, 1);
    inv_.add(I_HANDGUN_AMMO, 30);
    inv_.add(I_SHELLS, 4);
    reset_world();
    guns_[0] = {Weapon::Pistol, weapon_spec(Weapon::Pistol).mag};
    guns_[1] = {Weapon::Shotgun, weapon_spec(Weapon::Shotgun).mag};   // 6 in the tube, 1 in the chamber
    gun_ = 0;
    hero_.set_weapon(0);
    hero_.limp = 0;
    const Spawn& sp = spec_.spawns.count("start") ? spec_.spawns.at("start") : spec_.spawns.begin()->second;
    player_ = {sp.pos.x, sp.pos.z, sp.yaw};
    set_pmode(PMode::Normal);
    invuln_ = dodge_cd_ = aim_pitch_ = aim_snap_ = dead_t_ = step_accum_ = 0;
    death_sel_ = 0;
    focus_t_ = slowmo_t_ = 0;
    time_scale_ = 1;
    dodge_dir_ = knock_ = {};
    vel_ = aim_look_ = {};
    flick_ = {};
    aim_target_ = kick_target_ = -1;
    pump_t_ = slide_t_ = -1;
    hero_.pump = hero_.slide = 0;
    hero_.reloading = {};
    slide_locked_ = false;
    shell_from_grip_ = true;
    holding_ = false;
}

// ── Small helpers ──────────────────────────────────────────────────────────────

bool Game::aim_held() const { return in_.held(ACT_AIM); }
bool Game::fire_pressed() const { return in_.hit(ACT_FIRE); }

Vector3 Game::ear_right() const {
    Vector3 f = Vector3Subtract(cam_.target, cam_.position);
    f.y = 0;
    f = Vector3Normalize(f);
    return {-f.z, 0, f.x};
}

void Game::say(const Enemy& e, const char* sound, float volume) {
    sfx_.play_at(sound, e.body.head_point(), ear(), ear_right(), volume, 0.07f);
}

void Game::noise(float x, float z, float radius) {
    for (auto& e : enemies_)
        if (e.active && std::hypot(e.a.x - x, e.a.z - z) <= radius) e.heard = true;
}

// How far a shot flies before it meets a wall, the floor or the ceiling (the hall is a box).
float Game::wall_hit(Vector3 o, Vector3 d, float range) const {
    float t = range;
    auto slab = [&t](float o1, float d1, float lo, float hi) {
        if (d1 > 1e-6f) t = std::min(t, (hi - o1) / d1);
        else if (d1 < -1e-6f) t = std::min(t, (lo - o1) / d1);
    };
    slab(o.x, d.x, spec_.bounds.x0, spec_.bounds.x1);
    slab(o.y, d.y, 0.0f, spec_.height);
    slab(o.z, d.z, spec_.bounds.z0, spec_.bounds.z1);
    return std::max(t, 0.0f);
}

// ── The survivor ───────────────────────────────────────────────────────────────

void Game::update_player(float dt) {
    for (int k = 0; k < 2; ++k) {   // the 870 takes its shells one at a time, out of the case
        const bool was_empty = guns_[k].mag == 0;
        for (int in = guns_[k].tick(dt); in > 0; --in) load_shell(was_empty && guns_[k].mag == 1);
    }
    reload_hands();
    invuln_ = std::max(0.0f, invuln_ - dt);
    dodge_cd_ = std::max(0.0f, dodge_cd_ - dt);
    focus_t_ = std::max(0.0f, focus_t_ - dt);
    pmode_t_ += dt;
    Actor& p = player_;
    p.speed = 0;
    // How hurt he is shows only in how he moves: the limp eases in, there's no health bar.
    const Condition cond = condition(health_);
    hero_.limp += (limp_of(cond) - hero_.limp) * smoothing(3.0f, dt);
    if (IsKeyPressed(KEY_T)) { settings_.tank = !settings_.tank; save_settings(); }   // classic tank controls (keyboard)
    const Vector2 in = in_.move;
    // How hard he's pushed (sneak, walk, run; controls.hpp) and the stick back + the right face
    // button, read every frame whatever he's doing so a toggled run or the turn's grace never goes stale.
    gait_ = gaits_.update(settings_.tank && !in_.move_keys ? std::fabs(in.y) : std::min(1.0f, Vector2Length(in)), in_.move_keys,
                          settings_.run, in_.hit(ACT_RUN) && !in_.move_keys, in_.held(ACT_RUN), in_.held(ACT_RUN_HOLD));
    const Vector3 cam_f = Vector3Subtract(cam_.target, cam_.position);
    const V2 ahead = forward_from_yaw(p.yaw);
    const bool chord_on = settings_.back_turn && back_turn_shares_dodge(settings_.scheme) && pmode_ == PMode::Normal;
    const int chord = back_turn_.update(dt, settings_.tank ? in : stick_in_his_frame(in, {cam_f.x, cam_f.z}, {ahead.x, ahead.z}),
                                        chord_on && in_.hit(ACT_BACK_TURN), chord_on);
    work_actions(dt);
    if (pmode_ != PMode::Aim) aim_pitch_ -= aim_pitch_ * smoothing(10.0f, dt);
    if (pmode_ != PMode::Normal) vel_ = approach(vel_, {0, 0}, DECEL * dt);   // verbs stop the walk
    switch (pmode_) {
        case PMode::Dead:
            dead_t_ += dt;
            p.pose = Pose::Dead;
            if (death::choosing(dead_t_)) {   // try again, or quit
                if (in_.nav_y || in_.nav_x) { death_sel_ ^= 1; sfx_.play("ui_move", 0.5f); }
                if (in_.hit(ACT_CONFIRM)) {
                    sfx_.play("ui_confirm", 0.6f);
                    if (death_sel_ == 0) reset_fight();
                    else quit_ = true;
                }
            }
            return;
        case PMode::QuickTurn: {   // 180 degrees in 0.3 s
            const float k = std::min(1.0f, pmode_t_ / QUICK_TURN_TIME);
            p.yaw = qt_from_ + kPi * ease_out(k);
            p.pose = Pose::Idle;
            if (k >= 1.0f) set_pmode(PMode::Normal);
            return;
        }
        case PMode::Dodge: {   // fast off the mark, slowing as he lands
            const float k = std::min(1.0f, pmode_t_ / DODGE_TIME), v = DODGE_SPEED * (1 - k) * (1 - k);
            p.x += dodge_dir_.x * v * dt;
            p.z += dodge_dir_.z * v * dt;
            collide(p.x, p.z, PLAYER_R);
            p.pose = Pose::Dodge;
            if (pmode_t_ >= DODGE_TIME) {
                vel_ = {dodge_dir_.x * v, dodge_dir_.z * v};   // he lands moving: no dead stop
                if (aim_held()) enter_aim();
                else set_pmode(PMode::Normal);
            }
            return;
        }
        case PMode::Kick: {
            p.pose = Pose::Kick;
            if (!kick_done_ && pmode_t_ >= KICK_AT) {
                kick_done_ = true;
                sfx_.play("kick", kick_counter_ ? 1.0f : 0.9f, 0.05f);
                if (kick_target_ >= 0 && kick_target_ < int(enemies_.size())) {
                    Enemy& e = enemies_[size_t(kick_target_)];
                    const float dx = e.a.x - p.x, dz = e.a.z - p.z, d = std::max(std::hypot(dx, dz), 1e-3f);
                    if (!e.brain.dead() && d <= KICK_RANGE * 1.25f) {   // it may have stumbled back a little
                        ++stats_.kicks;
                        say(e, "enemy_hit", 0.8f);
                        fx_.blood_spray(e.body.joint(J_CHEST), flat_forward(p.yaw), 4, 1.2f);
                        const float shove = kick_counter_ ? 5.5f : 4.0f;   // a counter throws it back
                        e.push_x = dx / d * shove;
                        e.push_z = dz / d * shove;
                        input_.rumble(0.9f, 0.4f, 0.15f);
                        if (e.brain.take_hit(KICK_DAMAGE, 2, true) == EHit::Died) kill_enemy(e);
                    }
                }
            }
            if (pmode_t_ >= KICK_TIME) set_pmode(PMode::Normal);
            return;
        }
        case PMode::Hurt: {   // knocked back, sliding to a stop
            p.x += knock_.x * dt;
            p.z += knock_.z * dt;
            const float v = Vector3Length(knock_);
            if (v > 1e-4f) knock_ = Vector3Scale(knock_, std::max(0.0f, v - 8.0f * dt) / v);
            collide(p.x, p.z, PLAYER_R);
            p.pose = Pose::Hurt;
            if (pmode_t_ >= HURT_TIME) set_pmode(PMode::Normal);
            return;
        }
        case PMode::Aim:
            aim(dt);
            return;
        case PMode::Normal:
            break;
    }
    if (chord == BackTurnChord::DODGE && dodge_cd_ <= 0) { start_dodge(in_.move); return; }   // the button alone, after its grace
    if (common_actions()) return;
    if (aim_held()) { enter_aim(); return; }
    const bool run_tap = IsKeyPressed(KEY_LEFT_SHIFT) || IsKeyPressed(KEY_RIGHT_SHIFT);
    // The layout's quick turn, stick back + the right face button (an option), or back + run on
    // tank controls with the keys (RE3).
    if (chord == BackTurnChord::TURN || in_.hit(ACT_QUICK_TURN) || (settings_.tank && in.y < -0.5f && run_tap)) {
        qt_from_ = p.yaw;
        set_pmode(PMode::QuickTurn);
        return;
    }
    if (in_.hit(ACT_KICK) && try_kick()) return;
    if (in_.hit(ACT_INTERACT) && interact()) { vel_ = {}; return; }   // nothing to kick: whatever he's facing
    if (guns_[gun_].is_reloading()) {   // he stands still to reload; walking off stops the 870's shells
        const bool moving = gait_ != Gait::Still;
        if (!moving || !guns_[gun_].spec().single_load) { p.pose = Pose::Reload; vel_ = {}; return; }
        guns_[gun_].stop_loading();
    }
    move_player(dt, in, limp_speed(cond));
}

// Walking and running. How hard he's pushed picks the gait (update_player: a light touch sneaks,
// half walks, all the way runs, or the run option's button); he gets up to speed and stops in a
// few frames, and turns to the stick fast (a reversal pivots faster still), so circling a Drowned
// is a matter of skill, not of fighting the controls.
void Game::move_player(float dt, Vector2 in, float speed_scale) {
    Actor& p = player_;
    const float speed = gait_speed(gait_) * speed_scale;
    Vector2 want{};
    if (settings_.tank) {   // classic: left/right turn him, forward/back move him (backing up is slower)
        p.yaw -= in.x * 2.6f * dt;
        const V2 f = forward_from_yaw(p.yaw);
        const float k = in.y > 0.02f ? speed : in.y < -0.02f ? -0.6f * speed : 0.0f;
        want = {f.x * k, f.z * k};
    } else {
        Vector3 fwd = Vector3Subtract(cam_.target, cam_.position);
        fwd.y = 0;
        fwd = Vector3Normalize(fwd);
        const Vector3 right{-fwd.z, 0, fwd.x};
        if (gait_ == Gait::Still) holding_ = false;
        else if (!holding_ || std::fabs(Vector2Angle(in, held_in_)) > 35.0f * DEG2RAD) {
            holding_ = true;   // keep this camera's basis until the stick changes: no cut-induced reversals
            held_fwd_ = fwd;
            held_right_ = right;
            held_in_ = in;
        }
        if (holding_) {
            const Vector3 d = Vector3Normalize(Vector3Add(Vector3Scale(held_right_, in.x), Vector3Scale(held_fwd_, in.y)));
            want = {d.x * speed, d.z * speed};
            const float to = yaw_towards(0, 0, d.x, d.z);
            const bool reversal = std::fabs(wrap_pi(to - p.yaw)) > 2.4f;
            p.yaw = step_yaw(p.yaw, to, (reversal ? PIVOT : TURN) * dt);
        }
    }
    const bool faster = Vector2LengthSqr(want) > Vector2LengthSqr(vel_);
    vel_ = approach(vel_, want, (faster ? ACCEL : DECEL) * dt);
    const float ox = p.x, oz = p.z;
    p.x += vel_.x * dt;
    p.z += vel_.y * dt;
    collide(p.x, p.z, PLAYER_R);
    const float moved = std::hypot(p.x - ox, p.z - oz);
    if (dt > 0 && moved < Vector2Length(vel_) * dt * 0.5f) vel_ = Vector2Scale(vel_, 0.5f);   // ran into a wall: lose the momentum
    p.speed = dt > 0 ? moved / dt : 0.0f;
    p.pose = p.speed > 2.6f ? Pose::Run : p.speed > 0.1f ? Pose::Walk : Pose::Idle;
    // Footsteps: one a stride, as loud as the gait, and the Drowned in earshot hear them (a sneak
    // only at arm's length; a run across the hall).
    const Footfall ff = footfall(gait_);
    step_accum_ += moved;
    if (p.speed > 0.1f && step_accum_ >= ff.stride) {
        step_accum_ = 0;
        sfx_.play("step_" + spec_.footsteps, ff.volume, 0.08f);
        noise(p.x, p.z, ff.radius);
    }
}

// Dodge, reload and the weapon buttons work walking or aiming. True if a dodge took over.
bool Game::common_actions() {
    // Where stick back + the right face button turns him (an option), update_player's chord settles
    // what that button's press means, so it doesn't dodge here at once.
    const bool chord_press = pmode_ == PMode::Normal && settings_.back_turn && back_turn_shares_dodge(settings_.scheme) && in_.hit(ACT_BACK_TURN);
    if (in_.hit(ACT_DODGE) && !chord_press && dodge_cd_ <= 0) {
        start_dodge(in_.move);
        return true;
    }
    if (in_.hit(ACT_RELOAD)) reload();
    if (in_.hit(ACT_WEAPON_NEXT)) switch_gun(1 - gun_);
    else if (in_.hit(ACT_WEAPON_1)) switch_gun(0);
    else if (in_.hit(ACT_WEAPON_2)) switch_gun(1);
    return false;
}

void Game::start_dodge(Vector2 in) {
    const Vector3 f = flat_forward(player_.yaw), right{-f.z, 0, f.x};
    Vector3 d{};
    if (settings_.tank || (pmode_ == PMode::Aim && !in_.pad)) {   // relative to him: sideways, or forward past it
        d = Vector3Add(Vector3Scale(right, in.x), Vector3Scale(f, std::max(in.y, 0.0f)));
    } else {                               // relative to the camera, like walking (and aiming with a pad)
        Vector3 fwd = Vector3Subtract(cam_.target, cam_.position);
        fwd.y = 0;
        fwd = Vector3Normalize(fwd);
        d = Vector3Add(Vector3Scale({-fwd.z, 0, fwd.x}, in.x), Vector3Scale(fwd, in.y));
    }
    if (Vector3LengthSqr(d) < 0.04f) d = Vector3Negate(f);   // no direction: hop back
    dodge_dir_ = Vector3Normalize(d);
    dodge_cd_ = DODGE_TIME + DODGE_COOLDOWN;
    hero_.lean = Vector3DotProduct(dodge_dir_, right);       // the pose leans into it
    set_pmode(PMode::Dodge);
    ++stats_.dodges;
    sfx_.play("dodge", 0.8f, 0.06f);
}

// Cross (or E) does what's in front of him. A Drowned in the last moment of its lunge: a counter,
// it's thrown back and floored. One staggered or overbalanced: kicked down. One still winding up:
// the kick whiffs and he eats the bite (that's the risk). Nothing there: nothing happens.
bool Game::try_kick() {
    const V2 f = forward_from_yaw(player_.yaw);
    int best = -1, best_rank = 0;
    float best_d = 1e9f;
    for (size_t i = 0; i < enemies_.size(); ++i) {
        const Enemy& e = enemies_[i];
        if (!e.active || e.brain.dead()) continue;
        const float dx = e.a.x - player_.x, dz = e.a.z - player_.z, d = std::hypot(dx, dz);
        if (d > KICK_RANGE || (d > 1e-3f && (dx * f.x + dz * f.z) / d < std::cos(70.0f * kPi / 180.0f))) continue;
        const int rank = counterable(e.brain) ? 3 : e.brain.kickable() ? 2 : e.brain.state == EState::Attack ? 1 : 0;
        if (rank > best_rank || (rank == best_rank && rank > 0 && d < best_d)) { best = int(i); best_rank = rank; best_d = d; }
    }
    if (best < 0) return false;
    Enemy& e = enemies_[size_t(best)];
    kick_counter_ = best_rank == 3;
    if (kick_counter_) {   // cut its lunge short: it's the one staggering now
        e.brain.go(EState::Stagger);
        e.brain.immune = 0;
        ++stats_.counters;
        sfx_.play("perfect_dodge", 0.8f, 0.0f);
        input_.rumble(0.3f, 0.9f, 0.1f);
    }
    kick_target_ = best_rank >= 2 ? best : -1;   // a whiff hits nothing
    kick_done_ = false;
    player_.yaw = yaw_towards(player_.x, player_.z, e.a.x, e.a.z);
    set_pmode(PMode::Kick);
    player_.pose = Pose::Kick;
    return true;
}

// A dodge in the last moment of its lunge: it bites the air and stumbles on past, wide open,
// and his next shot does double. (Slow motion too, if the option is on.)
void Game::perfect_dodge_on(Enemy& e) {
    e.brain.overbalance(OVERBALANCE_TIME);
    e.stumble = 0.45f;
    const V2 f = forward_from_yaw(e.a.yaw);
    e.push_x += f.x * 1.8f;
    e.push_z += f.z * 1.8f;
    focus_t_ = FOCUS_TIME;
    ++stats_.perfect_dodges;
    sfx_.play("perfect_dodge", 0.9f, 0.0f);
    input_.rumble(0.2f, 0.8f, 0.12f);
    if (settings_.slowmo) slowmo_t_ = 0.6f;
}

int Game::kickable() const {
    const V2 f = forward_from_yaw(player_.yaw);
    for (size_t i = 0; i < enemies_.size(); ++i) {
        const Enemy& e = enemies_[i];
        if (!e.active || !e.brain.kickable()) continue;
        const float dx = e.a.x - player_.x, dz = e.a.z - player_.z, d = std::hypot(dx, dz);
        if (d <= KICK_RANGE && (d < 1e-3f || (dx * f.x + dz * f.z) / d > std::cos(60.0f * kPi / 180.0f))) return int(i);
    }
    return -1;
}

void Game::hurt_player(float dmg, float from_x, float from_z) {
    if (pmode_ == PMode::Dead) return;
    if (pmode_ == PMode::Dodge && pmode_t_ <= DODGE_IFRAMES) return;   // dodged it
    if (invuln_ > 0) return;
    health_ = std::max(0.0f, health_ - dmg);
    stats_.damage_taken += dmg;
    sfx_.play("player_hurt", 1.0f, 0.06f);
    Vector3 away{player_.x - from_x, 0, player_.z - from_z};
    away = Vector3LengthSqr(away) > 1e-8f ? Vector3Normalize(away) : Vector3Negate(flat_forward(player_.yaw));
    fx_.blood_spray(Vector3Lerp(hero_.joint(J_NECK), hero_.joint(J_SHO_L), 0.5f), away, 8, 1.4f);   // the bite
    if (health_ <= 0) {
        ++stats_.deaths;
        set_pmode(PMode::Dead);
        dead_t_ = 0;
        return;
    }
    set_pmode(PMode::Hurt);
    invuln_ = HURT_INVULN;
    knock_ = Vector3Scale(away, 2.5f);
}

// ── Aiming and shooting ─────────────────────────────────────────────────────────

void Game::enter_aim() {
    set_pmode(PMode::Aim);
    std::array<AimCandidate, MAX_ENEMIES> c{};
    const int n = int(std::min(enemies_.size(), MAX_ENEMIES));
    for (int i = 0; i < n; ++i) {
        const Enemy& e = enemies_[size_t(i)];
        c[size_t(i)] = {e.a.x, e.a.z, e.active && !e.brain.dead()};
    }
    aim_target_ = pick_target(player_.x, player_.z, player_.yaw, c.data(), n);
    aim_snap_ = 0.2f;
    aim_look_ = {};   // every lock starts on the chest
    flick_ = {};
}

// A flick of the right stick (or the mouse wheel): the next Drowned that way across the screen.
void Game::switch_target(int dir) {
    if (aim_target_ < 0) { enter_aim(); return; }
    const Vector3 right = ear_right();
    const Enemy& cur = enemies_[size_t(aim_target_)];
    const float cx = cur.a.x * right.x + cur.a.z * right.z;
    int best = -1;
    float best_dx = 1e9f;
    for (size_t i = 0; i < enemies_.size(); ++i) {
        const Enemy& e = enemies_[i];
        if (int(i) == aim_target_ || !e.active || e.brain.dead()) continue;
        if (std::hypot(e.a.x - player_.x, e.a.z - player_.z) > AIM_RANGE) continue;
        const float dx = (e.a.x * right.x + e.a.z * right.z - cx) * float(dir);
        if (dx > 0.05f && dx < best_dx) { best_dx = dx; best = int(i); }
    }
    if (best < 0) return;
    aim_target_ = best;
    aim_snap_ = 0.2f;
    sfx_.play("dry_fire", 0.25f, 0.1f);   // a small click as it moves over
}

// Where the gun points on the target: the right stick (or the mouse, or W/S) is a cursor over its
// body (controls.hpp: body_aim). Centred: the chest. Up: the head. Sideways: the forearm of the
// arm on that side of the screen. Down: the shin of the leg on that side. A part already shot off
// passes the aim to what's left (the upper arm, the thigh, the other limb).
Vector3 Game::aim_point(const Enemy& e) const {
    const Character& b = e.body;
    const Vector3 torso = Vector3Lerp(b.joint(J_PELVIS), b.joint(J_CHEST), 0.6f);
    const BodyAim a = body_aim(aim_look_);
    if (a.at == AimAt::Torso || a.k <= 0) return torso;
    const Vector3 right = ear_right();
    // Of a pair of joints, the one on the wanted side of the screen: 0 = the body's left, 1 = its right.
    auto side = [&](int jl, int jr, bool want_left) {
        const bool l_on_left = Vector3DotProduct(b.joint(jl), right) < Vector3DotProduct(b.joint(jr), right);
        return want_left == l_on_left ? 0 : 1;
    };
    Vector3 to = torso;
    if (a.at == AimAt::Head) {
        to = b.severed(R_HEAD) ? b.joint(J_NECK) : b.head_point();
    } else if (a.at == AimAt::ArmLeft || a.at == AimAt::ArmRight) {
        int s = side(J_SHO_L, J_SHO_R, a.at == AimAt::ArmLeft);
        if (b.severed(s ? R_UARM_R : R_UARM_L)) s = 1 - s;
        const int sho = s ? J_SHO_R : J_SHO_L, elb = s ? J_ELB_R : J_ELB_L, wri = s ? J_WRI_R : J_WRI_L;
        if (b.severed(s ? R_UARM_R : R_UARM_L)) to = torso;                                     // no arms left
        else if (b.severed(s ? R_FARM_R : R_FARM_L)) to = Vector3Lerp(b.joint(sho), b.joint(elb), 0.6f);   // the upper arm
        else to = Vector3Lerp(b.joint(elb), b.joint(wri), 0.3f);                                // the forearm
    } else {
        int s = side(J_HIP_L, J_HIP_R, a.at == AimAt::LegLeft);
        if (b.severed(s ? R_THIGH_R : R_THIGH_L)) s = 1 - s;
        const int hip = s ? J_HIP_R : J_HIP_L, kne = s ? J_KNE_R : J_KNE_L, ank = s ? J_ANK_R : J_ANK_L;
        if (b.severed(s ? R_THIGH_R : R_THIGH_L)) to = torso;                                   // no legs left
        else if (b.severed(s ? R_SHIN_R : R_SHIN_L)) to = Vector3Lerp(b.joint(hip), b.joint(kne), 0.6f);   // the thigh
        else to = Vector3Lerp(b.joint(kne), b.joint(ank), 0.4f);                                // the shin, below the knee
    }
    return Vector3Lerp(torso, to, a.k);
}

// The way a shot flies. Locked on and facing the target, it goes to the aim point (the gun's
// few degrees of wobble in the pose don't matter, as in the classic games); otherwise straight
// along his facing at the aim pitch.
Vector3 Game::shot_dir() const {
    const Vector3 mz = hero_.muzzle();
    if (aim_target_ >= 0 && aim_target_ < int(enemies_.size()) && enemies_[size_t(aim_target_)].active) {
        const Vector3 to = Vector3Subtract(aim_point(enemies_[size_t(aim_target_)]), mz), b = hero_.barrel_dir();
        if (std::fabs(wrap_pi(yaw_towards(0, 0, to.x, to.z) - yaw_towards(0, 0, b.x, b.z))) < LOCK_HALF && Vector3LengthSqr(to) > 1e-4f)
            return Vector3Normalize(to);
    }
    const V2 f = forward_from_yaw(player_.yaw);
    return {f.x * std::cos(aim_pitch_), std::sin(aim_pitch_), f.z * std::cos(aim_pitch_)};
}

void Game::aim(float dt) {
    Actor& p = player_;
    if (!aim_held()) { set_pmode(PMode::Normal); return; }
    if (common_actions()) return;   // dodging out of the aim
    p.pose = guns_[gun_].is_reloading() ? Pose::Reload : Pose::Aim;
    // The target went down: after a beat, the next one (if any).
    if (aim_target_ >= 0) {
        const Enemy& t = enemies_[size_t(aim_target_)];
        if (t.brain.dead() && t.dead_t > 0.6f) enter_aim();
    }
    // The aim cursor over the body. A stick glides to where it's held (let go: back to the chest);
    // the mouse drags it; W/S hold it on the head or the legs.
    if (in_.pad) {
        aim_look_ = approach(aim_look_, in_.look, 8.0f * dt);
        if (const int flick = flick_.update(in_.look, dt)) switch_target(flick);
    } else {
        aim_look_.x = std::clamp(aim_look_.x + in_.mouse.x * 0.006f, -1.0f, 1.0f);
        aim_look_.y = std::clamp(aim_look_.y - in_.mouse.y * 0.006f, -1.0f, 1.0f);
        if (std::fabs(in_.move.y) > 0.1f) aim_look_ = {0, in_.move.y > 0 ? 1.0f : -1.0f};
        if (in_.wheel != 0) switch_target(in_.wheel < 0 ? 1 : -1);
    }
    const Enemy* t = aim_target_ >= 0 ? &enemies_[size_t(aim_target_)] : nullptr;
    const float turn = in_.pad || !t ? in_.move.x : (std::fabs(in_.move.x) > 0.1f ? in_.move.x : 0.0f);
    const Vector3 ap = t ? aim_point(*t) : Vector3{}, mz = hero_.muzzle();
    if (t && std::fabs(turn) < 0.2f) {   // snap to it, then follow it round (the left stick or A/D takes over)
        // Line the GUN up with it, not his chest: the gun sits right of his middle, so he turns a
        // touch left of the target, more the closer it is (as a shooter does).
        const float right_x = std::cos(p.yaw), right_z = -std::sin(p.yaw);
        const float off = std::clamp((mz.x - p.x) * right_x + (mz.z - p.z) * right_z, -0.3f, 0.3f);
        const float dist = std::max(std::hypot(ap.x - p.x, ap.z - p.z), 0.4f);
        const float want = yaw_towards(p.x, p.z, ap.x, ap.z) + std::asin(std::clamp(off / dist, -0.6f, 0.6f));
        p.yaw = step_yaw(p.yaw, want, (aim_snap_ > 0 ? 9.0f : 2.5f) * dt);
    } else {
        p.yaw -= turn * AIM_TURN * dt;
    }
    aim_snap_ -= dt;
    float pitch = aim_look_.y * 0.4f;
    if (t) pitch = std::atan2(ap.y - mz.y, std::max(std::hypot(ap.x - mz.x, ap.z - mz.z), 0.3f));   // from the muzzle
    aim_pitch_ += (std::clamp(pitch, -0.8f, 0.55f) - aim_pitch_) * smoothing(12.0f, dt);
    if (fire_pressed()) fire();
    if (in_.hit(ACT_KICK)) try_kick();   // a counter, or a kick at one that's down on its luck
}

void Game::fire() {
    Firearm& g = guns_[gun_];
    const WeaponSpec& s = g.spec();
    if ((g.is_reloading() && !g.spec().single_load) || g.cooldown > 0) return;
    if (g.mag <= 0) {   // empty: reload if there's anything to load, else the click
        if (g.is_reloading()) return;   // the first shell is on its way
        if (inv_.count_of(s.ammo) > 0) reload();
        else { sfx_.play("dry_fire", 0.9f, 0.03f); g.cooldown = 0.3f; }
        return;
    }
    if (!g.fire()) return;
    ++stats_.shots;
    const bool shotgun = s.pellets > 1;
    if (shotgun) { pump_t_ = 0; pump_eject_ = true; }   // and then he pumps the next one in
    else slide_t_ = 0;           // the slide flies back, throws the brass, and runs home (or locks open: empty)
    const Vector3 mz = hero_.muzzle(), aim = shot_dir();
    const float focus = focus_t_ > 0 ? FOCUS_MULT : 1.0f;   // the shot after a perfect dodge
    focus_t_ = 0;
    sfx_.play(shotgun ? "shotgun" : "gunshot", 1.0f, 0.04f);
    fx_.flash(mz, hero_.barrel_dir(), shotgun);
    hero_.recoil(shotgun ? 0.8f : 0.4f);   // the muzzle climbs about 20 degrees for the shotgun, 10 for the pistol
    noise(player_.x, player_.z, s.noise);

    // Every body in the room can be hit, the dead too: a corpse can still be shot apart.
    std::array<HitVolume, MAX_ENEMIES * 12> vols{};
    int nv = 0;
    for (size_t i = 0; i < enemies_.size(); ++i)
        if (enemies_[i].active) nv += enemies_[i].body.hit_volumes(int(i), vols.data() + nv, int(vols.size()) - nv);
    // One blast is one hit reaction: pellets are added up per Drowned, then applied together.
    struct Tally { float dmg[R_COUNT]{}; float life = 0; int pellets = 0, head_pellets = 0, wounds = 0; bool crit = false; };
    std::array<Tally, MAX_ENEMIES> tally{};
    const Vector3 up{0, 1, 0}, side = Vector3Normalize(Vector3CrossProduct(aim, up));
    const float spread = s.spread_deg * DEG2RAD;
    const Vector3 ro = Vector3Subtract(mz, Vector3Scale(aim, 0.4f));   // from just behind the muzzle: a barrel pressed into a body still hits it
    for (int k = 0; k < s.pellets; ++k) {
        Vector3 d = aim;
        if (spread > 0) {
            d = Vector3RotateByAxisAngle(d, up, (frand() * 2 - 1) * spread);
            d = Vector3RotateByAxisAngle(d, side, (frand() * 2 - 1) * spread * 0.6f);
        }
        const RayHit h = first_hit(p3(ro), p3(d), wall_hit(ro, d, s.range + 0.4f), vols.data(), nv);
        if (h.owner < 0) continue;
        Enemy& e = enemies_[size_t(h.owner)];
        Tally& t = tally[size_t(h.owner)];
        Vector3 at = Vector3Add(ro, Vector3Scale(d, h.t)), n = Vector3Negate(d);
        int j = -1;
        // Where it really went in (the capsule is only a stand-in for the body): a wound that stays.
        // A handful per blast is plenty to read, and each one costs a search of the skin.
        if (t.wounds < 4 && e.body.surface_hit(h.region, ro, d, at, n, j)) {
            e.body.add_wound(j, at, n, shotgun ? 0.012f : 0.017f);
            ++t.wounds;
        }
        bool crit = false;
        const float dmg = g.damage_for(h.region == R_HEAD, frand(), Vector3Distance(mz, at), &crit) * focus;
        t.dmg[h.region] += dmg;
        t.life += dmg * BodyDamage::LIFE[h.region];
        t.crit = t.crit || crit;
        t.head_pellets += (h.region == R_HEAD || h.region == R_JAW) ? 1 : 0;
        ++t.pellets;
        fx_.blood_spray(at, d, shotgun ? 3 : 7, 2.6f);   // out the back
        fx_.blood_spray(at, n, shotgun ? 2 : 4, 1.1f);   // and back at him
    }
    for (size_t i = 0; i < enemies_.size() && i < MAX_ENEMIES; ++i) {
        const Tally& t = tally[i];
        if (t.pellets == 0) continue;
        ++stats_.hits;
        Enemy& e = enemies_[i];
        const bool was_dead = e.brain.dead();
        say(e, "enemy_hit", 0.9f);
        // What comes off. A crit bursts the head, and so does a face full of shot.
        const bool burst = t.crit || (shotgun && t.head_pellets >= 4);
        for (int r = 0; r < R_COUNT; ++r) {
            if (t.dmg[r] <= 0) continue;
            const int off = e.damage.hit(r, t.dmg[r], burst && (r == R_HEAD || r == R_JAW));
            if (off >= 0) cut_off(e, off, aim);
        }
        if (was_dead) continue;   // a corpse only comes apart
        const float dx = e.a.x - player_.x, dz = e.a.z - player_.z, dl = std::max(std::hypot(dx, dz), 1e-3f);
        if (e.damage.head_gone()) {
            kill_enemy(e);
            e.push_x = dx / dl * 1.5f;
            e.push_z = dz / dl * 1.5f;
            continue;
        }
        const bool knock = s.knockdown_hits > 0 && t.pellets >= s.knockdown_hits;
        const EHit hit = e.brain.take_hit(t.life, s.stagger_power, knock);
        float push = 0;
        if (hit == EHit::Died) { kill_enemy(e); push = shotgun ? 2.5f : 1.2f; }
        else if (hit == EHit::Floored) { say(e, "enemy_alert", 0.7f); push = 3.0f; }
        else if (hit == EHit::Staggered) { say(e, "enemy_alert", 0.7f); push = 1.2f; }
        e.push_x = dx / dl * push;
        e.push_z = dz / dl * push;
        if (!e.brain.dead() && !e.crawling && e.damage.lost_leg()) become_crawler(e);
    }
}

// A part of it comes away: the piece falls and rolls, the stump bleeds. A head bursts instead.
void Game::cut_off(Enemy& e, int region, Vector3 dir) {
    const Vector3 head = e.body.head_point();
    MeshData piece;
    Vector3 centre{};
    e.body.sever(region, piece, centre);
    if (region == R_HEAD) {   // full of canal water: it bursts like a dropped melon
        ++stats_.heads;
        fx_.blood_burst(head, 70);
        fx_.chips(head, 14);
        fx_.blood_spray(head, dir, 24, 3.2f);
        sfx_.play_at("splash", head, ear(), ear_right(), 1.0f, 0.1f);
        return;
    }
    ++stats_.limbs;
    fx_.gib(piece, centre, Vector3Add(Vector3Scale(dir, 1.4f), {0, 0.6f, 0}));
    fx_.blood_spray(centre, dir, 16, 2.0f);
    sfx_.play_at("splash", centre, ear(), ear_right(), 0.6f, 0.12f);
}

void Game::reload() {
    Firearm& g = guns_[gun_];
    const WeaponSpec& s = g.spec();
    const bool was_reloading = g.is_reloading();
    const int taken = g.reload(inv_.count_of(s.ammo));
    if (s.single_load) {   // the 870's shells go in one at a time: see load_shell
        if (!was_reloading && g.is_reloading()) shell_from_grip_ = true;   // the first comes off the fore-end
        return;
    }
    if (taken <= 0) return;
    inv_.remove(s.ammo, taken);
    // The hands change the magazine (reload_hands); a slide locked open stays back until the support
    // thumb drops the slide stop, once the fresh magazine is home.
    slide_locked_ = slide_t_ >= 0 && hero_.slide > 0.5f;
    slide_t_ = -1;
}

// The 870: a shell pushed up into the tube, out of the case (it clicked home as the hand pushed it:
// reload_hands). Into an empty gun the hand racked it into the chamber too, and starts the next
// shell from the fore-end.
void Game::load_shell(bool first_into_empty) {
    inv_.remove(I_SHELLS, 1);
    shell_from_grip_ = first_into_empty;
}

// The hands through a reload, as the gun's timing has it (Character::reloading, reload.hpp's steps),
// and what happens on the way: the empty magazine falls and clatters on the floor, the fresh one
// clicks home, the slide runs forward; each shell clicks past the latch; an empty 870 is racked.
void Game::reload_hands() {
    const Firearm& g = guns_[gun_];
    const WeaponSpec& s = g.spec();
    Character::Reloading& r = hero_.reloading;
    const Character::Reloading was = r;
    r.on = g.is_reloading();
    if (!r.on) return;
    if (!s.single_load) {
        r.kind = reload::Kind::Magazine;
        r.t = 1.0f - g.reloading / s.reload_time;
    } else {   // this shell (an empty gun's first takes longer: it's racked into the chamber too)
        const bool rack = g.mag == 0;
        r.kind = rack ? reload::Kind::ShellRack : reload::Kind::Shell;
        r.t = 1.0f - g.reloading / (s.reload_time + (rack ? s.rack_time : 0.0f));
        r.from_grip = shell_from_grip_;
    }
    r.t = std::clamp(r.t, 0.0f, 1.0f);
    const bool same = was.on && was.kind == r.kind && r.t >= was.t;
    auto passed = [&](float at) { return same && was.t < at && r.t >= at; };
    const Vector3 at = hero_.joint(J_WRI_R);
    if (r.kind == reload::Kind::Magazine) {
        if (passed(reload::MAG_DROP)) {   // the strong thumb on the release: the empty one drops out of the grip
            const Matrix f = hero_.load_frame();
            const Vector3 out = Vector3Normalize(Vector3Subtract(Vector3Transform(Vector3Transform(cast::m92fs_well_out(), Character::pistol_hold()), f),
                                                                 Vector3Transform(Vector3Transform({0, 0, 0}, Character::pistol_hold()), f)));
            fx_.magazine(f, Vector3Scale(out, 1.1f));
            sfx_.play_at("mag_out", at, ear(), ear_right(), 0.8f, 0.04f);
        }
        if (passed(reload::MAG_HOME)) sfx_.play_at("mag_in", at, ear(), ear_right(), 0.9f, 0.04f);
        if (passed(reload::SLIDE_HOME) && slide_locked_) {
            slide_locked_ = false;
            hero_.slide = 0;
            sfx_.play_at("slide_release", at, ear(), ear_right(), 1.0f, 0.04f);
        }
        return;
    }
    const float u0 = reload::shell_time(was.kind, was.t), u1 = reload::shell_time(r.kind, r.t);
    if (same && u0 < reload::SHELL_HOME && u1 >= reload::SHELL_HOME) sfx_.play_at("shell_insert", at, ear(), ear_right(), 0.8f, 0.06f);
    if (r.kind == reload::Kind::ShellRack) {   // the hand racks the fore-end: back, a beat, home
        if (passed(reload::RACK_BACK0)) sfx_.play_at("shotgun_pump", at, ear(), ear_right(), 0.9f, 0.04f);
        hero_.pump = reload::pump(r.kind, r.t);
    }
}

// The actions that work between shots. The 870: a beat after the shot he racks the fore-end back
// (the spent hull flies out to the right) and forward again. The M92FS: the slide slams back and
// runs home in a blink, throwing the brass; after the last round it stays locked back.
void Game::work_actions(float dt) {
    const Vector3 right{std::cos(player_.yaw), 0, -std::sin(player_.yaw)};
    if (pump_t_ >= 0) {
        const float t0 = pump_t_;
        pump_t_ += dt;
        constexpr float BACK = 0.25f, HOME = 0.52f;
        if (t0 < BACK && pump_t_ >= BACK) {
            sfx_.play("shotgun_pump", 0.9f, 0.04f);
            if (pump_eject_) fx_.casing(hero_.ejection_port(), right, true);
        }
        const float k = pump_t_ < BACK ? 0.0f : pump_t_ < BACK + 0.12f ? (pump_t_ - BACK) / 0.12f
                      : pump_t_ < HOME - 0.12f ? 1.0f : std::max(0.0f, (HOME - pump_t_) / 0.12f);
        hero_.pump = k;
        if (pump_t_ >= HOME) { pump_t_ = -1; hero_.pump = 0; }
    }
    if (slide_t_ >= 0) {
        const float t0 = slide_t_;
        slide_t_ += dt;
        if (t0 == 0.0f) fx_.casing(hero_.ejection_port(), right, false);
        const bool locked = guns_[0].mag == 0;   // slide lock: empty, it stays back
        hero_.slide = slide_t_ < 0.03f ? 1.0f : locked ? 1.0f : std::max(0.0f, 1.0f - (slide_t_ - 0.03f) / 0.05f);
        if (!locked && slide_t_ > 0.08f) { slide_t_ = -1; hero_.slide = 0; }
    }
}

void Game::switch_gun(int g) {
    if (g == gun_ || g < 0 || g > 1) return;
    Firearm& now = guns_[gun_];
    if (now.is_reloading() && !now.spec().single_load) return;   // not halfway through a magazine change
    if (!inv_.has(weapon_spec(guns_[g].id).item)) return;
    now.stop_loading();
    gun_ = g;
    hero_.set_weapon(g);
    sfx_.play("weapon_switch", 0.7f, 0.05f);
}

// ── The Drowned ─────────────────────────────────────────────────────────────────

void Game::kill_enemy(Enemy& e) {
    e.brain.kill();
    e.dead_t = 0;
    ++stats_.kills;
    say(e, "enemy_death", 1.0f);
}

// A leg came off: it goes down, and then it drags itself on after you. Slower, shorter reach,
// and it can't be staggered off its feet any more.
void Game::become_crawler(Enemy& e) {
    e.crawling = true;
    e.speed = 0.38f;
    e.turn = 1.6f;
    e.reach = 1.3f;
    e.bite = 12;
    e.brain.attack_range = 0.9f;
    e.brain.windup = 0.7f;
    e.brain.floor_time = 1.3f;
    e.brain.go(EState::Floored);
    say(e, "enemy_alert", 0.9f);
}

void Game::update_enemies(float dt) {
    const bool player_alive = pmode_ != PMode::Dead;
    int alive = 0;
    for (auto& e : enemies_) {
        if (!e.active) continue;
        Actor& a = e.a;
        // Momentum from hits and kicks, sliding out.
        a.x += e.push_x * dt;
        a.z += e.push_z * dt;
        const float pl = std::hypot(e.push_x, e.push_z);
        if (pl > 1e-4f) {
            const float k = std::max(0.0f, pl - 6.0f * dt) / pl;
            e.push_x *= k;
            e.push_z *= k;
        }
        if (e.brain.dead()) {
            e.dead_t += dt;
            a.pose = Pose::Dead;
            a.speed = 0;
            if (!e.pooled && e.dead_t > 0.9f) {   // it has hit the floor: the blood spreads out under it
                e.pooled = true;
                fx_.pool(e.body.joint(J_CHEST), 0.55f);
                if (e.damage.head_gone()) fx_.pool(e.body.joint(J_NECK), 0.35f);
            }
            collide(a.x, a.z, ENEMY_R);
            continue;
        }
        ++alive;
        const float dx = player_.x - a.x, dz = player_.z - a.z, dist = std::hypot(dx, dz);
        const V2 f = forward_from_yaw(a.yaw);
        const float ang = std::acos(std::clamp((f.x * dx + f.z * dz) / std::max(dist, 1e-4f), -1.0f, 1.0f));
        const bool sees = player_alive && dist < SIGHT && (ang < VIEW_HALF || dist < 1.5f);
        const EEvent ev = e.brain.update(dt, sees, e.heard && player_alive, player_alive ? dist : 99.0f);
        e.heard = false;
        e.stumble = std::max(0.0f, e.stumble - dt);
        switch (ev) {
            case EEvent::Alerted: say(e, "enemy_alert"); break;
            case EEvent::Windup: say(e, "enemy_windup"); break;
            case EEvent::Strike:
                if (player_alive && pmode_ == PMode::Dodge && perfect_dodge(pmode_t_) && dist <= e.reach + 1.2f)
                    perfect_dodge_on(e);   // it bites the air
                else if (player_alive && dist <= e.reach && ang <= STRIKE_HALF)
                    hurt_player(strike_damage(e), a.x, a.z);
                break;
            default: break;
        }
        const float want = yaw_towards(a.x, a.z, player_.x, player_.z);
        float v = 0;
        switch (e.brain.state) {
            case EState::Pursuit:
                a.yaw = step_yaw(a.yaw, want, e.turn * dt);
                v = e.speed * std::clamp(std::cos(wrap_pi(want - a.yaw)), 0.2f, 1.0f);   // turning slows it
                if (!player_alive && dist < 0.9f) v = 0;   // it stands over him
                break;
            case EState::Attack: {
                const bool striking = e.brain.t >= e.brain.windup;
                if (!striking) a.yaw = step_yaw(a.yaw, want, e.turn * 0.6f * dt);
                v = striking ? (e.crawling ? 1.6f : 2.2f) : 0.0f;   // the lunge
                break;
            }
            case EState::Stagger: v = e.crawling ? 0.0f : -0.9f; break;
            case EState::Alert: a.yaw = step_yaw(a.yaw, want, e.turn * 0.5f * dt); break;
            default: break;
        }
        const V2 fw = forward_from_yaw(a.yaw);
        a.x += fw.x * v * dt;
        a.z += fw.z * v * dt;
        a.speed = std::fabs(v);
        a.pose = pose_for(e);
        collide(a.x, a.z, ENEMY_R);
        if ((e.gurgle -= dt) <= 0) {
            e.gurgle = 3.0f + 4.0f * frand();
            say(e, "enemy_gurgle", 0.7f);
        }
        e.step += a.speed * dt;   // wet feet on the marble
        if (!e.crawling && e.step > 0.7f) {
            e.step = 0;
            sfx_.play_at("step_water", {a.x, 0.05f, a.z}, ear(), ear_right(), 0.3f, 0.1f);
        }
    }
    // Bodies don't overlap: the ones on their feet shove the survivor and each other apart.
    auto solid = [](const Enemy& e) { return e.active && !e.brain.dead() && e.brain.state != EState::Floored; };
    for (auto& e : enemies_) {
        if (!solid(e) || !player_alive) continue;
        const float r = e.crawling ? 0.5f : 0.6f;
        const float dx = player_.x - e.a.x, dz = player_.z - e.a.z, d = std::hypot(dx, dz);
        if (d < r && d > 1e-4f) {
            player_.x += dx / d * (r - d);
            player_.z += dz / d * (r - d);
        }
    }
    collide(player_.x, player_.z, PLAYER_R);
    for (size_t i = 0; i < enemies_.size(); ++i)
        for (size_t j = i + 1; j < enemies_.size(); ++j) {
            Enemy &a = enemies_[i], &b = enemies_[j];
            if (!solid(a) || !solid(b)) continue;
            const float dx = b.a.x - a.a.x, dz = b.a.z - a.a.z, d = std::hypot(dx, dz), r = 0.62f;
            if (d >= r || d < 1e-4f) continue;
            const float k = (r - d) / d * 0.5f;
            a.a.x -= dx * k; a.a.z -= dz * k;
            b.a.x += dx * k; b.a.z += dz * k;
        }
    // The hall's script: when the first one is down, something hits the front door; then two more.
    switch (script_.update(dt, alive)) {
        case HallEncounter::Event::DoorBang:
            sfx_.play_at("door_bang", {1.05f, 1.2f, spec_.bounds.z1 - 0.1f}, ear(), ear_right(), 1.0f, 0.0f);
            break;
        case HallEncounter::Event::SecondWave:
            for (auto& e : enemies_) {
                if (e.active) continue;
                e.active = true;
                if (std::hypot(e.a.x - player_.x, e.a.z - player_.z) < 1.0f) { e.a.x = 1.05f; e.a.z = spec_.bounds.z1 - 0.4f; }   // don't land on him
                e.a.yaw = yaw_towards(e.a.x, e.a.z, player_.x, player_.z);
                e.brain.go(EState::Pursuit);   // they heard the shots: they know where he is
                say(e, "enemy_alert");
            }
            break;
        default: break;
    }
}

}  // namespace dw
