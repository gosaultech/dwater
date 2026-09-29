// damned_waters/engine/src/game_combat.cpp
// Purpose: the fight in the hall.
//  * The survivor's verbs: aim (auto-targets; W/S for the head or the legs), fire, reload, switch
//    guns, kick a staggered Drowned, dodge, quick turn; hurt, limping, dead.
//  * The Drowned: senses, the brain's events, the lunge, crawling on after losing a leg.
//  * What a shot does: wounds that stay, limbs that come off, heads that burst, blood on the floor.
//  * The hall's script: one Drowned, then a bang at the front door and two more.
// The rules themselves (damage, magazines, when a limb comes off, the brain) are pure and
// unit-tested in combat.hpp and core.hpp; this file is the referee that applies them to the bodies
// in the room and makes the noise.
#include <algorithm>
#include <array>
#include <cmath>

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
constexpr int VARIANTS[] = {0, 2, 1};                      // who they were: the office worker, Pieter, Sanne

float ease_out(float t) { return 1.0f - (1.0f - t) * (1.0f - t); }
Vector3 flat_forward(float yaw) { const V2 f = forward_from_yaw(yaw); return {f.x, 0, f.z}; }
P3 p3(Vector3 v) { return {v.x, v.y, v.z}; }
float move_toward(float v, float to, float step) { return v < to ? std::min(v + step, to) : std::max(v - step, to); }

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
        case EState::Stagger: return Pose::Stagger;
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
    guns_[0] = {Weapon::Pistol, weapon_spec(Weapon::Pistol).mag};
    guns_[1] = {Weapon::Shotgun, weapon_spec(Weapon::Shotgun).mag};   // 6 in the tube, 1 in the chamber
    gun_ = 0;
    hero_.set_weapon(0);
    hero_.limp = 0;
    const Spawn& sp = spec_.spawns.count("start") ? spec_.spawns.at("start") : spec_.spawns.begin()->second;
    player_ = {sp.pos.x, sp.pos.z, sp.yaw};
    set_pmode(PMode::Normal);
    invuln_ = dodge_cd_ = aim_pitch_ = manual_pitch_ = aim_snap_ = dead_t_ = step_accum_ = 0;
    dodge_dir_ = knock_ = {};
    aim_target_ = kick_target_ = -1;
    pump_t_ = slide_t_ = -1;
    hero_.pump = hero_.slide = 0;
    holding_ = false;
}

// ── Small helpers ──────────────────────────────────────────────────────────────

bool Game::aim_held() const { return staged_aim_ || IsMouseButtonDown(MOUSE_BUTTON_RIGHT) || IsKeyDown(KEY_K); }
bool Game::fire_pressed() const { return IsMouseButtonPressed(MOUSE_BUTTON_LEFT) || IsKeyPressed(KEY_J) || IsKeyPressed(KEY_SPACE); }

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
    invuln_ = std::max(0.0f, invuln_ - dt);
    dodge_cd_ = std::max(0.0f, dodge_cd_ - dt);
    pmode_t_ += dt;
    Actor& p = player_;
    p.speed = 0;
    // How hurt he is shows only in how he moves: the limp eases in, there's no health bar.
    const Condition cond = condition(health_);
    hero_.limp += (limp_of(cond) - hero_.limp) * smoothing(3.0f, dt);
    if (IsKeyPressed(KEY_T)) tank_ = !tank_;
    const float ix = float(IsKeyDown(KEY_D) || IsKeyDown(KEY_RIGHT)) - float(IsKeyDown(KEY_A) || IsKeyDown(KEY_LEFT)) + staged_in_.x;
    const float iy = float(IsKeyDown(KEY_W) || IsKeyDown(KEY_UP)) - float(IsKeyDown(KEY_S) || IsKeyDown(KEY_DOWN)) + staged_in_.y;
    work_actions(dt);
    if (pmode_ != PMode::Aim) aim_pitch_ -= aim_pitch_ * smoothing(10.0f, dt);
    switch (pmode_) {
        case PMode::Dead:
            dead_t_ += dt;
            p.pose = Pose::Dead;
            if (dead_t_ > 2.5f && (IsKeyPressed(KEY_ENTER) || IsKeyPressed(KEY_E))) reset_fight();
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
                if (aim_held()) enter_aim();
                else set_pmode(PMode::Normal);
            }
            return;
        }
        case PMode::Kick: {
            p.pose = Pose::Kick;
            if (!kick_done_ && pmode_t_ >= KICK_AT) {
                kick_done_ = true;
                sfx_.play("kick", 0.9f, 0.05f);
                if (kick_target_ >= 0 && kick_target_ < int(enemies_.size())) {
                    Enemy& e = enemies_[size_t(kick_target_)];
                    const float dx = e.a.x - p.x, dz = e.a.z - p.z, d = std::max(std::hypot(dx, dz), 1e-3f);
                    if (!e.brain.dead() && d <= KICK_RANGE * 1.25f) {   // it may have stumbled back a little
                        ++stats_.kicks;
                        say(e, "enemy_hit", 0.8f);
                        fx_.blood_spray(e.body.joint(J_CHEST), flat_forward(p.yaw), 4, 1.2f);
                        e.push_x = dx / d * 4.0f;
                        e.push_z = dz / d * 4.0f;
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
            aim(dt, ix, iy);
            return;
        case PMode::Normal:
            break;
    }
    if (common_actions(ix, iy)) return;
    if (aim_held()) { enter_aim(); return; }
    const bool run_tap = IsKeyPressed(KEY_LEFT_SHIFT) || IsKeyPressed(KEY_RIGHT_SHIFT);
    if (IsKeyPressed(KEY_Q) || (tank_ && iy < -0.5f && run_tap)) {   // Q, or back + run on tank controls (RE3)
        qt_from_ = p.yaw;
        set_pmode(PMode::QuickTurn);
        return;
    }
    if (IsKeyPressed(KEY_E)) {
        const int k = kickable();
        if (k >= 0) {
            kick_target_ = k;
            kick_done_ = false;
            p.yaw = yaw_towards(p.x, p.z, enemies_[size_t(k)].a.x, enemies_[size_t(k)].a.z);
            set_pmode(PMode::Kick);
            p.pose = Pose::Kick;
            return;
        }
    }
    if (guns_[gun_].is_reloading()) {   // he stands still to reload; walking off stops the 870's shells
        const bool moving = std::fabs(ix) > 0.2f || std::fabs(iy) > 0.2f;
        if (!moving || !guns_[gun_].spec().single_load) { p.pose = Pose::Reload; return; }
        guns_[gun_].stop_loading();
    }
    move_player(dt, ix, iy, limp_speed(cond));
}

void Game::move_player(float dt, float ix, float iy, float speed_scale) {
    Actor& p = player_;
    const bool run = IsKeyDown(KEY_LEFT_SHIFT) || IsKeyDown(KEY_RIGHT_SHIFT);
    const float speed = (run ? 3.8f : 1.9f) * speed_scale;
    float mx = 0, mz = 0;
    if (tank_) {
        p.yaw -= ix * 2.6f * dt;
        const V2 f = forward_from_yaw(p.yaw);
        const float k = iy * speed * (iy < 0 ? 0.6f : 1.0f);
        mx = f.x * k;
        mz = f.z * k;
    } else {
        Vector3 fwd = Vector3Subtract(cam_.target, cam_.position);
        fwd.y = 0;
        fwd = Vector3Normalize(fwd);
        const Vector3 right{-fwd.z, 0, fwd.x};
        const Vector2 in{ix, iy};
        if (Vector2Length(in) < 0.2f) holding_ = false;
        else if (!holding_ || std::fabs(Vector2Angle(in, held_in_)) > 35.0f * DEG2RAD) {
            holding_ = true;   // keep this camera's basis until the stick changes: no cut-induced reversals
            held_fwd_ = fwd;
            held_right_ = right;
            held_in_ = in;
        }
        if (holding_) {
            Vector3 d = Vector3Add(Vector3Scale(held_right_, ix), Vector3Scale(held_fwd_, iy));
            if (Vector3Length(d) > 1) d = Vector3Normalize(d);
            mx = d.x * speed;
            mz = d.z * speed;
            p.yaw = step_yaw(p.yaw, yaw_towards(0, 0, d.x, d.z), 12.0f * dt);
        }
    }
    const float ox = p.x, oz = p.z;
    p.x += mx * dt;
    p.z += mz * dt;
    collide(p.x, p.z, PLAYER_R);
    p.speed = std::sqrt(mx * mx + mz * mz);
    p.pose = p.speed > 2.6f ? Pose::Run : p.speed > 0.1f ? Pose::Walk : Pose::Idle;
    // Footsteps: one per stride, and the Drowned nearby hear them (running carries further).
    const bool running = p.pose == Pose::Run;
    step_accum_ += std::hypot(p.x - ox, p.z - oz);
    if (p.speed > 0.1f && step_accum_ >= (running ? 0.85f : 0.62f)) {
        step_accum_ = 0;
        sfx_.play("step_" + spec_.footsteps, running ? 0.8f : 0.5f, 0.08f);
        noise(p.x, p.z, running ? 6.0f : 2.5f);
    }
}

// Dodge, reload and the weapon keys work walking or aiming. True if a dodge took over.
bool Game::common_actions(float ix, float iy) {
    if ((IsKeyPressed(KEY_C) || IsKeyPressed(KEY_LEFT_ALT) || IsKeyPressed(KEY_RIGHT_ALT)) && dodge_cd_ <= 0) {
        start_dodge(ix, iy);
        return true;
    }
    if (IsKeyPressed(KEY_R)) reload();
    if (IsKeyPressed(KEY_F)) switch_gun(1 - gun_);
    else if (IsKeyPressed(KEY_ONE)) switch_gun(0);
    else if (IsKeyPressed(KEY_TWO)) switch_gun(1);
    return false;
}

void Game::start_dodge(float ix, float iy) {
    const Vector3 f = flat_forward(player_.yaw), right{-f.z, 0, f.x};
    Vector3 d{};
    if (tank_ || pmode_ == PMode::Aim) {   // relative to him: sideways, or forward past it
        d = Vector3Add(Vector3Scale(right, ix), Vector3Scale(f, std::max(iy, 0.0f)));
    } else {                               // relative to the camera, like walking
        Vector3 fwd = Vector3Subtract(cam_.target, cam_.position);
        fwd.y = 0;
        fwd = Vector3Normalize(fwd);
        d = Vector3Add(Vector3Scale({-fwd.z, 0, fwd.x}, ix), Vector3Scale(fwd, iy));
    }
    if (Vector3LengthSqr(d) < 0.04f) d = Vector3Negate(f);   // no direction: hop back
    dodge_dir_ = Vector3Normalize(d);
    dodge_cd_ = DODGE_TIME + DODGE_COOLDOWN;
    hero_.lean = Vector3DotProduct(dodge_dir_, right);       // the pose leans into it
    set_pmode(PMode::Dodge);
    ++stats_.dodges;
    sfx_.play("dodge", 0.8f, 0.06f);
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
    manual_pitch_ = 0;
    aim_leg_ = -1;
}

// Where the gun points on the target: the middle of the body, drifting up to the head as W is
// held, or down to a leg with S: the shin, below the knee, of one leg until it's gone (aim_leg_).
Vector3 Game::aim_point(const Enemy& e) const {
    const Character& b = e.body;
    const Vector3 torso = Vector3Lerp(b.joint(J_PELVIS), b.joint(J_CHEST), 0.6f);
    if (manual_pitch_ > 0) {
        const Vector3 head = b.severed(R_HEAD) ? b.joint(J_NECK) : b.head_point();
        return Vector3Lerp(torso, head, manual_pitch_);
    }
    if (manual_pitch_ < 0 && aim_leg_ >= 0 && !b.severed(aim_leg_ ? R_SHIN_R : R_SHIN_L)) {
        const Vector3 leg = Vector3Lerp(b.joint(aim_leg_ ? J_KNE_R : J_KNE_L), b.joint(aim_leg_ ? J_ANK_R : J_ANK_L), 0.4f);
        return Vector3Lerp(torso, leg, -manual_pitch_);
    }
    return torso;
}

namespace {
// Aiming low picks the nearer leg still on, and stays on it.
int pick_leg(const Character& b, float px, float pz) {
    int best = -1;
    float best_d = 1e9f;
    for (int s = 0; s < 2; ++s) {
        if (b.severed(s ? R_SHIN_R : R_SHIN_L)) continue;
        const Vector3 k = b.joint(s ? J_KNE_R : J_KNE_L);
        const float d = std::hypot(k.x - px, k.z - pz);
        if (d < best_d) { best_d = d; best = s; }
    }
    return best;
}
}  // namespace

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

void Game::aim(float dt, float ix, float iy) {
    Actor& p = player_;
    if (!aim_held()) { set_pmode(PMode::Normal); return; }
    if (common_actions(ix, iy)) return;   // dodging out of the aim
    p.pose = guns_[gun_].is_reloading() ? Pose::Reload : Pose::Aim;
    // The target went down: after a beat, the next one (if any).
    if (aim_target_ >= 0) {
        const Enemy& t = enemies_[size_t(aim_target_)];
        if (t.brain.dead() && t.dead_t > 0.6f) enter_aim();
    }
    const Enemy* t = aim_target_ >= 0 ? &enemies_[size_t(aim_target_)] : nullptr;
    manual_pitch_ = move_toward(manual_pitch_, iy, 4.0f * dt);   // W: up to the head, S: down to the legs
    if (t && manual_pitch_ < 0 && (aim_leg_ < 0 || t->body.severed(aim_leg_ ? R_SHIN_R : R_SHIN_L)))
        aim_leg_ = pick_leg(t->body, p.x, p.z);
    const Vector3 ap = t ? aim_point(*t) : Vector3{}, mz = hero_.muzzle();
    if (t && std::fabs(ix) < 0.2f) {   // snap to it, then follow it round (A/D takes over)
        // Line the GUN up with it, not his chest: the gun sits right of his middle, so he turns a
        // touch left of the target, more the closer it is (as a shooter does).
        const float right_x = std::cos(p.yaw), right_z = -std::sin(p.yaw);
        const float off = std::clamp((mz.x - p.x) * right_x + (mz.z - p.z) * right_z, -0.3f, 0.3f);
        const float dist = std::max(std::hypot(ap.x - p.x, ap.z - p.z), 0.4f);
        const float want = yaw_towards(p.x, p.z, ap.x, ap.z) + std::asin(std::clamp(off / dist, -0.6f, 0.6f));
        p.yaw = step_yaw(p.yaw, want, (aim_snap_ > 0 ? 9.0f : 2.5f) * dt);
    } else {
        p.yaw -= ix * AIM_TURN * dt;
    }
    aim_snap_ -= dt;
    float pitch = manual_pitch_ * 0.4f;
    if (t) pitch = std::atan2(ap.y - mz.y, std::max(std::hypot(ap.x - mz.x, ap.z - mz.z), 0.3f));   // from the muzzle
    aim_pitch_ += (std::clamp(pitch, -0.8f, 0.55f) - aim_pitch_) * smoothing(12.0f, dt);
    if (fire_pressed()) fire();
    if (IsKeyPressed(KEY_E)) {   // a staggered one in reach: kick it down
        const int k = kickable();
        if (k >= 0) {
            kick_target_ = k;
            kick_done_ = false;
            p.yaw = yaw_towards(p.x, p.z, enemies_[size_t(k)].a.x, enemies_[size_t(k)].a.z);
            set_pmode(PMode::Kick);
            p.pose = Pose::Kick;
        }
    }
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
        const float dmg = g.damage_for(h.region == R_HEAD, frand(), Vector3Distance(mz, at), &crit);
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
    const int taken = g.reload(inv_.count_of(s.ammo));
    if (s.single_load) return;   // the 870's shells go in one at a time: see load_shell
    if (taken <= 0) return;
    inv_.remove(s.ammo, taken);
    sfx_.play("reload", 0.9f, 0.03f);
    slide_t_ = -1;               // a fresh magazine, and the slide runs home
    hero_.slide = 0;
}

// The 870: a shell pushed up into the tube, out of the case. Into an empty gun, he racks it too.
void Game::load_shell(bool first_into_empty) {
    inv_.remove(I_SHELLS, 1);
    sfx_.play("shell_insert", 0.8f, 0.06f);
    if (first_into_empty) { pump_t_ = 0; pump_eject_ = false; }   // rack it into the chamber: no spent hull to throw
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
        switch (ev) {
            case EEvent::Alerted: say(e, "enemy_alert"); break;
            case EEvent::Windup: say(e, "enemy_windup"); break;
            case EEvent::Strike:
                if (player_alive && dist <= e.reach && ang <= STRIKE_HALF) hurt_player(strike_damage(e), a.x, a.z);
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
