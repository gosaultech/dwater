// damned_waters/engine/src/game.cpp
// Purpose: see game.hpp. The fight itself is in game_combat.cpp. Render order per frame:
//   1. plate: painted background, writing its painted DEPTH into the z-buffer (relit by any
//      muzzle flash)
//   2. characters and the fight's debris: real-time, depth-tested against the painting
//   3. blob shadows, then post (grain + vignette) to the window, and the death screen
#include "game.hpp"

#include <rlgl.h>
#include <algorithm>
#include <cmath>
#include <vector>
#include <cstdio>
#include <cstdlib>

#include "dw/shaders.hpp"

namespace dw {
namespace {
constexpr float LIGHT_SCALE = 2.4f;   // RoomSpec godot_energy -> this shader's units
// The muzzle flash as a light: warm white, bright for a frame or three, reaching a few metres.
constexpr float FLASH_RANGE = 6.0f;
const Vector3 FLASH_COLOR{2.6f, 1.9f, 1.1f};
// The flashlight: a warm-white LED spot, about 42 degrees across, good for a hall's length.
constexpr float LAMP_RANGE = 9.0f, LAMP_HALF = 21.0f * DEG2RAD;
const Vector3 LAMP_COLOR{2.5f, 2.35f, 2.1f};
}  // namespace

bool Game::init(const std::string& room_id) {
    const std::string root = repo_root();
    spec_ = RoomSpec::load(root + "/game/data/rooms/" + room_id + ".json");
    if (!spec_.ok()) {
        for (auto& e : spec_.errors) TraceLog(LOG_ERROR, "RoomSpec: %s", e.c_str());
        return false;
    }
    for (const auto& s : spec_.shots) {
        std::string base = root + "/game/assets/rooms/" + spec_.id + "/" + s.id;
        Texture2D c = LoadTexture((base + "_color.png").c_str()), d = LoadTexture((base + "_depth.png").c_str());
        if (c.id == 0 || d.id == 0) { TraceLog(LOG_ERROR, "missing plate %s", base.c_str()); return false; }
        SetTextureFilter(c, TEXTURE_FILTER_BILINEAR);
        SetTextureFilter(d, TEXTURE_FILTER_POINT);   // depth bytes must never be blended
        plates_[s.id] = {c, d};
    }
    plate_ = LoadShaderFromMemory(nullptr, shaders::PLATE_FS);
    l_depth_ = GetShaderLocation(plate_, "u_depth");
    l_near_ = GetShaderLocation(plate_, "u_near");
    l_far_ = GetShaderLocation(plate_, "u_far");
    l_dmax_ = GetShaderLocation(plate_, "u_depthMax");
    char_ = LoadShaderFromMemory(shaders::CHAR_VS, shaders::CHAR_FS);
    char_.locs[SHADER_LOC_MATRIX_MODEL] = GetShaderLocation(char_, "matModel");
    char_.locs[SHADER_LOC_MATRIX_NORMAL] = GetShaderLocation(char_, "matNormal");
    l_cam_ = GetShaderLocation(char_, "u_camPos");
    l_count_ = GetShaderLocation(char_, "u_lightCount");
    l_pos_ = GetShaderLocation(char_, "u_lightPos");
    l_col_ = GetShaderLocation(char_, "u_lightCol");
    l_dir_ = GetShaderLocation(char_, "u_lightDir");
    l_top_ = GetShaderLocation(char_, "u_ambTop");
    l_bot_ = GetShaderLocation(char_, "u_ambBottom");
    l_rim_ = GetShaderLocation(char_, "u_rim");
    l_fog_ = GetShaderLocation(char_, "u_fog");
    l_fogr_ = GetShaderLocation(char_, "u_fogRange");
    char_mat_ = LoadMaterialDefault();
    char_mat_.shader = char_;
    blob_ = LoadShaderFromMemory(nullptr, shaders::BLOB_FS);
    l_blob_ = GetShaderLocation(blob_, "u_strength");
    blob_mat_ = LoadMaterialDefault();
    blob_mat_.shader = blob_;
    blob_mesh_ = GenMeshPlane(1, 1, 1, 1);
    post_ = LoadShaderFromMemory(nullptr, shaders::POST_FS);
    l_time_ = GetShaderLocation(post_, "u_time");
    l_res_ = GetShaderLocation(post_, "u_res");
    l_dynPos_ = GetShaderLocation(plate_, "u_dynPos");
    l_dynCol_ = GetShaderLocation(plate_, "u_dynCol");
    l_dynDir_ = GetShaderLocation(plate_, "u_dynDir");
    rt_ = LoadRenderTexture(W, H);
    init_shadows();
    near_ = float(rlGetCullDistanceNear());
    far_ = float(rlGetCullDistanceFar());
    sfx_.init(root + "/game/assets/audio");   // quietly does nothing without an audio device
    sfx_.ambience(spec_.ambience, 0.45f);
    fx_.init();
    fx_.set_bounds(spec_.bounds.x0, spec_.bounds.z0, spec_.bounds.x1, spec_.bounds.z1);
    hero_ = Character::make(Kind::Survivor);
    reset_fight();
    cut_to(select_shot(spec_.zones(), "", player_.x, player_.z));
    upload_lights();
    animate(0.0f);
    return true;
}

void Game::shutdown() {
    for (auto& [id, p] : plates_) { UnloadTexture(p.first); UnloadTexture(p.second); }
    hero_.unload();
    for (auto& e : enemies_) e.body.unload();
    enemies_.clear();
    fx_.shutdown();
    sfx_.shutdown();
    UnloadMesh(blob_mesh_);
    UnloadShader(plate_); UnloadShader(char_); UnloadShader(blob_); UnloadShader(post_);
    UnloadRenderTexture(rt_);
    for (auto& sm : shadows_) {
        rlUnloadTexture(sm.rt.depth.id);
        rlUnloadTexture(sm.rt.texture.id);
        rlUnloadFramebuffer(sm.rt.id);
    }
}

void Game::init_shadows() {
    for (auto& sm : shadows_) {
        RenderTexture2D& t = sm.rt;
        t.id = rlLoadFramebuffer();
        t.texture.id = rlLoadTexture(nullptr, SHADOW_RES, SHADOW_RES, PIXELFORMAT_UNCOMPRESSED_R8G8B8A8, 1);   // unused; some drivers want one
        t.texture.width = t.texture.height = SHADOW_RES;
        t.texture.format = PIXELFORMAT_UNCOMPRESSED_R8G8B8A8;
        t.texture.mipmaps = 1;
        t.depth.id = rlLoadTextureDepth(SHADOW_RES, SHADOW_RES, false);   // a texture, so shaders can read it
        t.depth.width = t.depth.height = SHADOW_RES;
        t.depth.format = 19;
        t.depth.mipmaps = 1;
        rlEnableFramebuffer(t.id);
        rlFramebufferAttach(t.id, t.texture.id, RL_ATTACHMENT_COLOR_CHANNEL0, RL_ATTACHMENT_TEXTURE2D, 0);
        rlFramebufferAttach(t.id, t.depth.id, RL_ATTACHMENT_DEPTH, RL_ATTACHMENT_TEXTURE2D, 0);
        if (!rlFramebufferComplete(t.id)) TraceLog(LOG_WARNING, "shadows: framebuffer incomplete");
        rlDisableFramebuffer();
    }
    l_depthOnly_ = GetShaderLocation(char_, "u_depthOnly");
    l_shLight_ = GetShaderLocation(char_, "u_shadowLight");
    l_pInvView_ = GetShaderLocation(plate_, "u_invView");
    l_pTan_ = GetShaderLocation(plate_, "u_tanHalf");
    l_pSh0_ = GetShaderLocation(plate_, "u_shadow0");
    l_pSh1_ = GetShaderLocation(plate_, "u_shadow1");
    l_pShL_ = GetShaderLocation(plate_, "u_shadowL");
    for (int k = 0; k < 2; ++k) {
        l_shVP_[k] = GetShaderLocation(char_, TextFormat("u_shadowVP[%d]", k));
        l_pShVP_[k] = GetShaderLocation(plate_, TextFormat("u_shadowVP[%d]", k));
    }
    bind_shadows();
}

void Game::set_lights(const Vector4* pos, const Vector4* col, const Vector4* dir, int n) {
    light_n_ = n;
    for (int i = 0; i < 8; ++i) { light_pos_[i] = pos[i]; light_col_[i] = col[i]; light_dir_[i] = dir[i]; }
    SetShaderValue(char_, l_count_, &n, SHADER_UNIFORM_INT);
    SetShaderValueV(char_, l_pos_, pos, SHADER_UNIFORM_VEC4, 8);
    SetShaderValueV(char_, l_col_, col, SHADER_UNIFORM_VEC4, 8);
    SetShaderValueV(char_, l_dir_, dir, SHADER_UNIFORM_VEC4, 8);
}

// Pick the (up to) two lights that light the characters most, and draw the characters' depth as
// each of those lights sees them: a perspective view from the light, framing all the characters.
void Game::render_shadows(const std::vector<const Character*>& casters) {
    for (auto& sm : shadows_) sm.light = -1;
    if (casters.size() == 0 || light_n_ == 0) return;
    Vector3 c{};
    for (const Character* ch : casters) c = Vector3Add(c, ch->joint(J_PELVIS));
    c = Vector3Scale(c, 1.0f / float(casters.size()));
    float r = 0;
    for (const Character* ch : casters) r = std::max(r, Vector3Distance(ch->joint(J_PELVIS), c));
    r += 1.15f;   // a character reaches about a metre from its hips (hair, raised arms)
    struct Pick { int i; float e; };
    Pick picks[8];
    int np = 0;
    for (int i = 0; i < static_lights_; ++i) {                        // the room's lights; a muzzle flash is too brief
        const Vector4 p = light_pos_[i], col = light_col_[i];
        if (int(col.w + 0.5f) == 2) continue;                       // suns: none indoors
        const float dist = Vector3Distance({p.x, p.y, p.z}, c);
        if (dist < 0.5f) continue;                                    // a light among the characters can't frame them
        const float x = std::clamp(1.0f - std::pow(dist / std::max(p.w, 1e-3f), 4.0f), 0.0f, 1.0f);
        const float e = (col.x + col.y + col.z) * x * x / (1.0f + dist * dist * 0.35f);
        if (e > 0.02f && np < 8) picks[np++] = {i, e};
    }
    for (int k = 0; k < std::min(np, 2); ++k)   // the brightest two to the front (all we need)
        for (int m = k + 1; m < np; ++m)
            if (picks[m].e > picks[k].e) std::swap(picks[k], picks[m]);
    const double keep_near = rlGetCullDistanceNear(), keep_far = rlGetCullDistanceFar();
    for (int k = 0; k < np && k < 2; ++k) {
        const Vector4 p = light_pos_[picks[k].i];
        const Vector3 lp{p.x, p.y, p.z};
        const float dist = Vector3Distance(lp, c);
        Camera3D lc{};
        lc.position = lp;
        lc.target = c;
        lc.up = std::fabs(Vector3Normalize(Vector3Subtract(c, lp)).y) > 0.95f ? Vector3{0, 0, 1} : Vector3{0, 1, 0};
        lc.fovy = 2.0f * std::atan(r / dist) * RAD2DEG * 1.05f;
        lc.projection = CAMERA_PERSPECTIVE;
        if (lc.fovy > 165.0f) continue;                               // a hanging lamp right overhead needs a wide view
        rlSetClipPlanes(std::max(0.05, double(dist - r - 0.3f)), double(dist + r + 0.5f));   // tight: precise depth
        const unsigned t1 = char_mat_.maps[MATERIAL_MAP_METALNESS].texture.id, t2 = char_mat_.maps[MATERIAL_MAP_NORMAL].texture.id;
        char_mat_.maps[MATERIAL_MAP_METALNESS].texture.id = 0;         // never sample a map while drawing into it
        char_mat_.maps[MATERIAL_MAP_NORMAL].texture.id = 0;
        BeginTextureMode(shadows_[k].rt);
        ClearBackground(WHITE);
        BeginMode3D(lc);
        shadows_[k].vp = MatrixMultiply(rlGetMatrixModelview(), rlGetMatrixProjection());
        const int one = 1, zero = 0;
        SetShaderValue(char_, l_depthOnly_, &one, SHADER_UNIFORM_INT);
        rlDisableBackfaceCulling();
        for (const Character* ch : casters) ch->draw(char_mat_, true);
        rlEnableBackfaceCulling();
        SetShaderValue(char_, l_depthOnly_, &zero, SHADER_UNIFORM_INT);
        EndMode3D();
        EndTextureMode();
        char_mat_.maps[MATERIAL_MAP_METALNESS].texture.id = t1;
        char_mat_.maps[MATERIAL_MAP_NORMAL].texture.id = t2;
        rlSetClipPlanes(keep_near, keep_far);
        shadows_[k].light = picks[k].i;
    }
}

void Game::bind_shadows() {
    int which[2];
    Vector4 pl[2];
    for (int k = 0; k < 2; ++k) {
        const ShadowMap& sm = shadows_[k];
        which[k] = sm.light;
        const Vector4 p = sm.light >= 0 ? light_pos_[sm.light] : Vector4{0, 0, 0, 0};
        pl[k] = {p.x, p.y, p.z, sm.light >= 0 ? 1.0f : 0.0f};
        SetShaderValueMatrix(char_, l_shVP_[k], sm.vp);
        SetShaderValueMatrix(plate_, l_pShVP_[k], sm.vp);
    }
    SetShaderValueV(char_, l_shLight_, which, SHADER_UNIFORM_INT, 2);
    SetShaderValueV(plate_, l_pShL_, pl, SHADER_UNIFORM_VEC4, 2);
    char_mat_.maps[MATERIAL_MAP_METALNESS].texture = shadows_[0].rt.depth;   // the shader's texture1
    char_mat_.maps[MATERIAL_MAP_NORMAL].texture = shadows_[1].rt.depth;      // the shader's texture2
}

void Game::cut_to(const std::string& id) {
    for (const auto& s : spec_.shots)
        if (s.id == id) {
            shot_ = id;
            cam_.position = {s.pos.x, s.pos.y, s.pos.z};
            cam_.target = {s.look_at.x, s.look_at.y, s.look_at.z};
            cam_.up = {0, 1, 0};
            cam_.fovy = s.fov;   // vertical FOV, exactly as Blender rendered it
            cam_.projection = CAMERA_PERSPECTIVE;
        }
}

void Game::upload_lights() {
    Vector4 pos[8]{}, col[8]{}, dir[8]{};
    int n = 0;
    for (size_t i = 0; i < spec_.lights.size() && n < 8; ++i, ++n) {
        const Light& L = spec_.lights[i];
        float flick = L.flicker ? 0.88f + 0.08f * std::sin(time_ * 13.0f + i) + 0.04f * std::sin(time_ * 31.0f + i * 2) : 1.0f;
        float e = L.energy * LIGHT_SCALE * flick;
        int type = L.kind == "sun" ? 2 : (L.kind == "spot" || L.kind == "area") ? 1 : 0;
        pos[n] = {L.pos.x, L.pos.y, L.pos.z, L.range};
        col[n] = {L.color.x * e, L.color.y * e, L.color.z * e, float(type)};
        if (type == 2) {
            Vector3 d = Vector3Normalize({-L.dir_from.x, -L.dir_from.y, -L.dir_from.z});
            dir[n] = {d.x, d.y, d.z, 0};
        } else if (type == 1) {
            Vector3 d = Vector3Normalize({L.look_at.x - L.pos.x, L.look_at.y - L.pos.y, L.look_at.z - L.pos.z});
            float half = (L.kind == "area" ? 120.0f : L.spot_angle) * 0.5f * DEG2RAD;
            dir[n] = {d.x, d.y, d.z, std::cos(half)};
        }
    }
    static_lights_ = n;
    // The muzzle flash: one more light on the characters, and a light the painted room never saw
    // (the plate shader relights the painting with it, from the painted depth).
    Vector4 dpos[2]{}, dcol[2]{}, ddir[2]{};
    const float fp = fx_.flash_power();
    if (fp > 0) {
        const Vector3 at = fx_.flash_pos();
        const Vector3 c = Vector3Scale(FLASH_COLOR, fp / 4.0f);
        dpos[0] = {at.x, at.y, at.z, FLASH_RANGE};
        dcol[0] = {c.x, c.y, c.z, 0};
        if (n < 8) { pos[n] = dpos[0]; col[n] = dcol[0]; ++n; }
    }
    if (flashlight && hero_.has_lamp()) {
        const Vector3 at = hero_.lamp(), d = hero_.lamp_dir();
        dpos[1] = {at.x, at.y, at.z, LAMP_RANGE};
        dcol[1] = {LAMP_COLOR.x, LAMP_COLOR.y, LAMP_COLOR.z, 1};   // w: a spot
        ddir[1] = {d.x, d.y, d.z, std::cos(LAMP_HALF)};
        if (n < 8) { pos[n] = dpos[1]; col[n] = {LAMP_COLOR.x, LAMP_COLOR.y, LAMP_COLOR.z, 1}; dir[n] = ddir[1]; ++n; }
    }
    SetShaderValueV(plate_, l_dynPos_, dpos, SHADER_UNIFORM_VEC4, 2);
    SetShaderValueV(plate_, l_dynCol_, dcol, SHADER_UNIFORM_VEC4, 2);
    SetShaderValueV(plate_, l_dynDir_, ddir, SHADER_UNIFORM_VEC4, 2);
    set_lights(pos, col, dir, n);
    const float top[3] = {0.03f, 0.034f, 0.046f}, bot[3] = {0.011f, 0.009f, 0.007f}, rim[3] = {0.1f, 0.12f, 0.16f};
    const float fog[3] = {0.006f, 0.007f, 0.009f}, fogr[2] = {5.0f, 16.0f};
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fog_, fog, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fogr_, fogr, SHADER_UNIFORM_VEC2);
}

void Game::collide(float& x, float& z, float r) const {
    for (int it = 0; it < 3; ++it)
        for (const auto& b : spec_.colliders) resolve_circle_obb(x, z, r, b);
}

void Game::animate(float dt) {
    hero_.place({player_.x, 0, player_.z}, player_.yaw);
    hero_.animate(player_.pose, player_.speed, dt, aim_pitch_);
    fx_.follow_flash(hero_.muzzle(), hero_.barrel_dir());   // the flame stays on the barrel as it kicks
    for (auto& e : enemies_) {
        if (!e.active) continue;
        e.body.place({e.a.x, 0, e.a.z}, e.a.yaw);
        e.body.animate(e.a.pose, e.a.speed, dt);
    }
}

void Game::update(float dt) {
    time_ += dt;
    banner_t_ -= dt;
    if (IsKeyPressed(KEY_F3)) debug = !debug;
    if (IsKeyPressed(KEY_L)) flashlight = !flashlight;
    update_player(dt);
    update_enemies(dt);
    fx_.update(dt);
    sfx_.update();
    std::string next = select_shot(spec_.zones(), shot_, player_.x, player_.z);
    if (next != shot_) cut_to(next);
    animate(dt);
    upload_lights();   // after the pose: the flash light sits where the muzzle is now
}

// The capture setups (--capture): the first four are posed (no AI); the rest play the fight out,
// with the aim held and the trigger pulled from here, and stop on the frame worth looking at.
std::string Game::stage(int i) {
    constexpr float DT = 1.0f / 60;
    auto run = [&](float seconds) { for (float t = 0; t < seconds; t += DT) update(DT); };
    auto join = [&](size_t k, float x, float z, float yaw, EState st) -> Enemy& {
        Enemy& e = enemies_[std::min(k, enemies_.size() - 1)];
        e.active = true;
        e.a = {x, z, yaw};
        e.brain.go(st);
        return e;
    };
    reset_fight();
    banner_t_ = 0;   // no room title over the stills
    staged_aim_ = false;
    staged_in_ = {};
    for (auto& e : enemies_) e.active = false;
    if (enemies_.empty()) return "no_enemies";
    std::string name;
    if (i < 4) {
        struct S { float px, pz, pyaw; Pose ppose; float pspeed, ex, ez, eyaw; Pose epose; float espeed; const char* name; };
        static const S setups[] = {
            {1.0f, 7.2f, kPi, Pose::Aim, 0, 1.1f, 8.85f, 0.0f, Pose::Windup, 0, "front_door_windup"},
            {0.62f, 2.45f, kPi, Pose::Idle, 0, 0.55f, 1.0f, kPi, Pose::Shamble, 0.6f, "cellar_door_behind_you"},
            {0.75f, 4.6f, 0.0f, Pose::Walk, 1.9f, 0.6f, 2.0f, kPi, Pose::Shamble, 0.7f, "hall_approach"},
            {1.35f, 0.45f, kPi, Pose::Idle, 0, 0.6f, 2.2f, kPi, Pose::Idle, 0, "drowned_portrait"},
        };
        const S& s = setups[i];
        player_ = {s.px, s.pz, s.pyaw, s.pspeed, s.ppose};
        Enemy& e = join(0, s.ex, s.ez, s.eyaw, EState::Idle);
        e.a.speed = s.espeed;
        e.a.pose = s.epose;
        cut_to(select_shot(spec_.zones(), "", player_.x, player_.z));
        for (int f = 0; f < 90; ++f) { time_ += DT; animate(DT); }
        upload_lights();
        return s.name;
    }
    switch (i) {
        case 4: {   // the M92FS: the flash lights him, the Drowned and the hall for a frame
            join(0, 0.75f, 3.1f, kPi, EState::Pursuit);
            player_ = {1.05f, 5.55f, 0.0f};
            staged_aim_ = true;
            run(0.6f);
            fire();
            run(DT);
            name = "pistol_flash";
            break;
        }
        case 5: {   // the Jachtgeweer at two metres
            join(1, 1.1f, 9.1f, 0.0f, EState::Pursuit);
            switch_gun(1);
            player_ = {0.9f, 7.0f, kPi};
            staged_aim_ = true;
            run(0.6f);
            fire();
            run(DT);
            name = "shotgun_blast";
            break;
        }
        case 6: {   // S aims at the legs: three or four rounds and a shin comes off; it crawls on
            Enemy& z = join(0, 0.7f, 0.45f, kPi, EState::Pursuit);
            player_ = {1.0f, 2.5f, 0.0f};
            staged_aim_ = true;
            staged_in_ = {0, -1};
            run(0.5f);
            for (int k = 0; k < 5 && !z.crawling; ++k) { fire(); run(0.5f); }
            if (const int off = z.damage.hit(R_FARM_R, 9.0f); off >= 0) cut_off(z, off, shot_dir());   // and a stray round took a hand
            staged_in_ = {};
            run(2.5f);
            name = "legs_off_crawler";
            break;
        }
        case 7: {   // W aims at the head: a crit bursts it (forced here; the dice decide in play)
            Enemy& s = join(2, 0.75f, 0.5f, kPi, EState::Pursuit);
            player_ = {0.95f, 2.45f, 0.0f};
            staged_aim_ = true;
            staged_in_ = {0, 1};
            run(0.7f);
            fire();
            if (!s.damage.head_gone()) {
                s.damage.hit(R_HEAD, 0, true);
                cut_off(s, R_HEAD, shot_dir());
                kill_enemy(s);
            }
            run(0.22f);
            name = "head_burst";
            break;
        }
        case 8: {   // the first one headless by the door, a bang, and two more come in
            Enemy& z = join(0, 0.45f, 8.0f, 0.4f, EState::Pursuit);
            z.damage.hit(R_HEAD, 0, true);
            cut_off(z, R_HEAD, {0, 0, 1});
            kill_enemy(z);
            player_ = {1.1f, 6.95f, kPi};
            run(1.2f);
            script_.phase = HallEncounter::Phase::Bang;   // skip the quiet: straight to the door
            script_.t = HallEncounter::BANG_TO_ENTRY - DT;
            run(0.6f);
            staged_aim_ = true;
            run(0.4f);
            name = "second_wave";
            break;
        }
        default: {   // bitten once too often
            join(1, 1.0f, 8.3f, 0.0f, EState::Pursuit);
            player_ = {1.0f, 7.4f, kPi};
            health_ = 15;
            hurt_player(20, 1.0f, 8.3f);
            run(3.2f);
            name = "you_died";
            break;
        }
    }
    staged_aim_ = false;
    staged_in_ = {};
    return name;
}

void Game::upload_studio_lights() {
    // Neutral three-point rig for judging a model: warm key front-left, cold fill, cold rim behind.
    const Vector4 pos[8] = {{-1.3f, 2.7f, -1.7f, 8.0f}, {1.6f, 1.2f, -1.3f, 8.0f}, {0.4f, 2.5f, 1.9f, 8.0f}};
    const Vector4 col[8] = {{1.0f * 3.9f, 0.78f * 3.9f, 0.55f * 3.9f, 0}, {0.9f, 1.0f, 1.3f, 0}, {0.6f * 3.2f, 0.7f * 3.2f, 1.0f * 3.2f, 0}};
    const Vector4 dir[8] = {};
    set_lights(pos, col, dir, 3);
    const float top[3] = {0.05f, 0.055f, 0.07f}, bot[3] = {0.02f, 0.018f, 0.015f}, rim[3] = {0.1f, 0.12f, 0.16f};
    const float fog[3] = {0, 0, 0}, fogr[2] = {50.0f, 60.0f};
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fog_, fog, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fogr_, fogr, SHADER_UNIFORM_VEC2);
}

void Game::model_sheet(const std::string& dir, const std::string& only) {
    struct View { const char* name; float orbit_deg, elev_deg, dist, target_y, fovy; bool head; };
    static const View views[] = {
        {"front", 0, 8, 2.9f, 1.0f, 40, false},       {"three_quarter", 38, 10, 2.9f, 1.0f, 40, false},
        {"side", 90, 6, 2.9f, 1.0f, 40, false},       {"back", 180, 10, 2.9f, 1.0f, 40, false},
        {"head_front", 0, 4, 0.62f, 0, 30, true},     {"head_three_quarter", 38, 8, 0.62f, 0, 30, true},
        {"head_side", 82, 4, 0.62f, 0, 30, true},     {"head_game_angle", 15, 40, 0.8f, 0, 30, true},
        {"torso_front", 0, 5, 1.25f, 1.2f, 40, false}, {"torso_three_quarter", 38, 8, 1.25f, 1.2f, 40, false},
        {"torso_back", 180, 8, 1.25f, 1.2f, 40, false}, {"legs_and_hands", 25, 12, 1.4f, 0.55f, 40, false},
    };
    constexpr int kViews = int(sizeof(views) / sizeof(views[0])), kRows = kViews / 4;
    struct Subject { const char* name; Kind kind; int variant; Pose pose; };
    static const Subject subjects[] = {{"office_worker", Kind::Drowned, 0, Pose::Idle}, {"woman_dress", Kind::Drowned, 1, Pose::Idle},
                                       {"pieter", Kind::Drowned, 2, Pose::Idle}, {"drowned_windup", Kind::Drowned, 0, Pose::Windup},
                                       {"drowned_shamble", Kind::Drowned, 2, Pose::Shamble}, {"survivor", Kind::Survivor, 0, Pose::Idle}};
    upload_studio_lights();
    for (const auto& sub : subjects) {
        if (!only.empty() && ("," + only + ",").find("," + std::string(sub.name) + ",") == std::string::npos) continue;
        Character c = Character::make(sub.kind, sub.variant);
        c.place({0, 0, 0}, 0);
        for (int f = 0; f < 150; ++f) c.animate(sub.pose, sub.pose == Pose::Shamble ? 0.7f : 0.0f, 1.0f / 60);
        render_shadows({&c});
        bind_shadows();
        Image sheet = GenImageColor(4 * 400, kRows * 560, Color{10, 10, 12, 255});
        for (int v = 0; v < kViews; ++v) {
            const View& w = views[v];
            // Bodies orbit the feet; heads orbit the skull, starting from wherever the face points.
            Vector3 at{0, w.target_y, 0};
            float a = w.orbit_deg * DEG2RAD, e = w.elev_deg * DEG2RAD;
            if (w.head) {
                at = Vector3Add(c.head_point(), {0, -0.04f, 0});   // the face, mouth and all, not just the skull
                Vector3 f = c.face_dir();
                a += std::atan2(f.x, -f.z);
            }
            Camera3D cam{};
            cam.position = {at.x + w.dist * std::sin(a) * std::cos(e), at.y + w.dist * std::sin(e), at.z - w.dist * std::cos(a) * std::cos(e)};
            cam.target = at;
            cam.up = {0, 1, 0};
            cam.fovy = w.fovy;
            cam.projection = CAMERA_PERSPECTIVE;
            BeginTextureMode(rt_);
            ClearBackground(Color{16, 16, 19, 255});
            BeginMode3D(cam);
            SetShaderValue(char_, l_cam_, &cam.position, SHADER_UNIFORM_VEC3);
            rlDisableBackfaceCulling();
            c.draw(char_mat_);
            rlEnableBackfaceCulling();
            EndMode3D();
            EndTextureMode();
            Image img = LoadImageFromTexture(rt_.texture);
            ImageFlipVertical(&img);
            // Crop a portrait strip from the middle of the frame (full height for bodies).
            const Rectangle src{float(W) / 2 - 257, 0, 514, float(H)};
            ImageCrop(&img, src);
            ImageResize(&img, 400, 560);
            ImageDraw(&sheet, img, {0, 0, 400, 560}, {float(v % 4) * 400, float(v / 4) * 560, 400, 560}, WHITE);
            ImageDrawText(&sheet, w.name, (v % 4) * 400 + 10, (v / 4) * 560 + 8, 18, Color{170, 160, 140, 255});
            UnloadImage(img);
        }
        ExportImage(sheet, (dir + "/sheet_" + sub.name + ".png").c_str());
        UnloadImage(sheet);
        c.unload();
        TraceLog(LOG_INFO, "sheet %s", sub.name);
    }
    upload_lights();
}

bool Game::studio_view(const std::string& spec, const std::string& png) {
    char who[48] = {};
    float orbit = 0, elev = 0, dist = 1, tx = 0, ty = 1, fovy = 30;
    if (std::sscanf(spec.c_str(), "%47[^,],%f,%f,%f,%f,%f,%f", who, &orbit, &elev, &dist, &tx, &ty, &fovy) != 7) return false;
    // who = survivor | drowned[N] (N: the citizen), optionally @head / @chest / @pelvis to orbit that
    // joint instead (the target is then offset from it by target_x, target_y; @head orbits from the face),
    // then any of /pose=aim /gun=1 /limp=1 /cut=3+8 (regions cut off first; anatomy.hpp).
    std::string w = who, at_joint, opts;
    if (const auto k = w.find('/'); k != std::string::npos) { opts = w.substr(k); w.resize(k); }
    if (const auto k = w.find('@'); k != std::string::npos) { at_joint = w.substr(k + 1); w.resize(k); }
    const bool survivor = w == "survivor";
    const int variant = !survivor && w.size() > 7 ? std::atoi(w.c_str() + 7) : 0;
    upload_studio_lights();
    Character c = Character::make(survivor ? Kind::Survivor : Kind::Drowned, variant);
    c.place({0, 0, 0}, 0);
    Pose pose = Pose::Idle;
    std::vector<int> cuts;
    for (size_t i = 0; i < opts.size();) {
        const size_t j = std::min(opts.find('/', i + 1), opts.size());
        const std::string o = opts.substr(i + 1, j - i - 1), key = o.substr(0, o.find('=')), val = o.substr(o.find('=') + 1);
        static const std::map<std::string, Pose> poses = {
            {"idle", Pose::Idle}, {"walk", Pose::Walk}, {"run", Pose::Run}, {"aim", Pose::Aim}, {"hurt", Pose::Hurt},
            {"dead", Pose::Dead}, {"dodge", Pose::Dodge}, {"kick", Pose::Kick}, {"reload", Pose::Reload},
            {"shamble", Pose::Shamble}, {"windup", Pose::Windup}, {"strike", Pose::Strike}, {"stagger", Pose::Stagger},
            {"floored", Pose::Floored}, {"crawl", Pose::Crawl}};
        if (key == "pose" && poses.count(val)) pose = poses.at(val);
        if (key == "gun") c.set_weapon(std::atoi(val.c_str()));
        if (key == "limp") c.limp = float(std::atof(val.c_str()));
        if (key == "cut")
            for (size_t a = 0; a < val.size();) { cuts.push_back(std::atoi(val.c_str() + a)); a = std::min(val.find('+', a), val.size()) + 1; }
        i = j;
    }
    for (int f = 0; f < 90; ++f) c.animate(pose, pose == Pose::Walk || pose == Pose::Shamble ? 0.8f : 0.0f, 1.0f / 60);
    for (int r : cuts) { MeshData piece; Vector3 centre; c.sever(r, piece, centre); }
    if (survivor) {   // how true the barrel lies to where he faces (the shots fly along his facing)
        const Vector3 b = c.barrel_dir();
        TraceLog(LOG_INFO, "VIEW barrel dir %.2f %.2f %.2f  muzzle %.2f %.2f %.2f", b.x, b.y, b.z, c.muzzle().x, c.muzzle().y, c.muzzle().z);
    }
    for (int f = 0; f < 60; ++f) c.animate(pose, pose == Pose::Walk || pose == Pose::Shamble ? 0.8f : 0.0f, 1.0f / 60);
    render_shadows({&c});
    bind_shadows();
    float a = orbit * DEG2RAD;
    const float e = elev * DEG2RAD;
    Vector3 at{tx, ty, 0};
    if (!at_joint.empty()) {
        const Vector3 j = at_joint == "head" ? c.head_point() : c.joint(at_joint == "chest" ? J_CHEST : J_PELVIS);
        at = {j.x + tx, j.y + ty, j.z};
        if (at_joint == "head") { const Vector3 f = c.face_dir(); a += std::atan2(f.x, -f.z); }
    }
    Camera3D cam{};
    cam.position = {at.x + dist * std::sin(a) * std::cos(e), at.y + dist * std::sin(e), at.z - dist * std::cos(a) * std::cos(e)};
    cam.target = at;
    cam.up = {0, 1, 0};
    cam.fovy = fovy;
    cam.projection = CAMERA_PERSPECTIVE;
    BeginTextureMode(rt_);
    ClearBackground(Color{16, 16, 19, 255});
    BeginMode3D(cam);
    SetShaderValue(char_, l_cam_, &cam.position, SHADER_UNIFORM_VEC3);
    rlDisableBackfaceCulling();
    c.draw(char_mat_);
    rlEnableBackfaceCulling();
    EndMode3D();
    EndTextureMode();
    Image img = LoadImageFromTexture(rt_.texture);
    ImageFlipVertical(&img);
    const bool ok = ExportImage(img, png.c_str());
    UnloadImage(img);
    c.unload();
    upload_lights();
    return ok;
}

void Game::render() {
    const auto& plate = plates_.at(shot_);
    casters_.clear();   // (reused: no allocation per frame)
    casters_.push_back(&hero_);
    for (const auto& e : enemies_)
        if (e.active) casters_.push_back(&e.body);
    render_shadows(casters_);
    bind_shadows();
    SetShaderValueMatrix(plate_, l_pInvView_, MatrixInvert(MatrixLookAt(cam_.position, cam_.target, cam_.up)));
    const float th = std::tan(cam_.fovy * 0.5f * DEG2RAD), tan_half[2] = {th * float(W) / float(H), th};
    SetShaderValue(plate_, l_pTan_, tan_half, SHADER_UNIFORM_VEC2);
    BeginTextureMode(rt_);
    ClearBackground(BLACK);
    rlEnableDepthTest();
    rlEnableDepthMask();
    BeginShaderMode(plate_);
    SetShaderValueTexture(plate_, l_depth_, plate.second);
    SetShaderValueTexture(plate_, l_pSh0_, shadows_[0].rt.depth);
    SetShaderValueTexture(plate_, l_pSh1_, shadows_[1].rt.depth);
    const float dmax = depth::MAX_M;
    SetShaderValue(plate_, l_near_, &near_, SHADER_UNIFORM_FLOAT);
    SetShaderValue(plate_, l_far_, &far_, SHADER_UNIFORM_FLOAT);
    SetShaderValue(plate_, l_dmax_, &dmax, SHADER_UNIFORM_FLOAT);
    DrawTexturePro(plate.first, {0, 0, float(plate.first.width), float(plate.first.height)}, {0, 0, float(W), float(H)}, {0, 0}, 0, WHITE);
    EndShaderMode();
    BeginMode3D(cam_);
    SetShaderValue(char_, l_cam_, &cam_.position, SHADER_UNIFORM_VEC3);
    rlDisableBackfaceCulling();
    hero_.draw(char_mat_);
    for (const auto& e : enemies_)
        if (e.active) e.body.draw(char_mat_);
    fx_.draw(char_mat_);   // blood, brass, what came off
    rlEnableBackfaceCulling();
    rlDisableDepthMask();
    BeginBlendMode(BLEND_ADDITIVE);   // the flash glows over whatever is behind it
    fx_.draw_flash(char_mat_);
    EndBlendMode();
    BeginBlendMode(BLEND_ALPHA);
    const float strength = 0.35f;   // contact darkening under the feet; the lights cast the real shadows
    SetShaderValue(blob_, l_blob_, &strength, SHADER_UNIFORM_FLOAT);
    auto blob = [&](const Character& c, const Actor& a) {   // under the feet, or under the whole body when it's down
        const bool down = a.pose == Pose::Dead || a.pose == Pose::Floored || a.pose == Pose::Crawl ||
                          a.pose == Pose::CrawlWindup || a.pose == Pose::CrawlStrike;
        const Vector3 at = down ? Vector3Lerp(c.joint(J_PELVIS), c.joint(J_CHEST), 0.5f) : Vector3{a.x, 0, a.z};
        const float sz = down ? 1.25f : 0.85f;
        DrawMesh(blob_mesh_, blob_mat_, MatrixMultiply(MatrixScale(sz, 1, sz), MatrixTranslate(at.x, 0.012f, at.z)));
    };
    blob(hero_, player_);
    for (const auto& e : enemies_)
        if (e.active) blob(e.body, e.a);
    EndBlendMode();
    rlEnableDepthMask();
    EndMode3D();
    EndTextureMode();
}

void Game::present() const {
    ClearBackground(BLACK);
    const float t = time_, res[2] = {float(W), float(H)};
    SetShaderValue(post_, l_time_, &t, SHADER_UNIFORM_FLOAT);
    SetShaderValue(post_, l_res_, res, SHADER_UNIFORM_VEC2);
    BeginShaderMode(post_);
    DrawTexturePro(rt_.texture, {0, 0, float(W), -float(H)}, {0, 0, float(GetScreenWidth()), float(GetScreenHeight())}, {0, 0}, 0, WHITE);
    EndShaderMode();
    if (banner_t_ > 0) {
        unsigned char a = static_cast<unsigned char>(std::min(1.0f, banner_t_) * 210);
        DrawText(spec_.display_name.c_str(), 40, 34, 26, Color{210, 200, 180, a});
    }
    // No HUD: how hurt he is shows in his limp; ammo and health live on the status screen.
    // Only death gets words on the screen, as in the classic games.
    if (pmode_ == PMode::Dead) {
        const int sw = GetScreenWidth(), sh = GetScreenHeight();
        const float k = std::clamp((dead_t_ - 0.8f) / 1.6f, 0.0f, 1.0f);
        DrawRectangle(0, 0, sw, sh, Color{14, 0, 0, static_cast<unsigned char>(k * 190)});
        if (k > 0) {
            const int fs = sh / 9, tw = MeasureText("YOU DIED", fs);
            DrawText("YOU DIED", (sw - tw) / 2, sh / 2 - fs, fs, Color{170, 16, 12, static_cast<unsigned char>(k * 255)});
            if (dead_t_ > 2.5f) {
                const int ps = sh / 36, pw = MeasureText("Press Enter to try again", ps);
                DrawText("Press Enter to try again", (sw - pw) / 2, sh / 2 + fs / 2, ps, Color{150, 140, 130, 200});
            }
        }
    }
    if (debug) {
        std::string es;
        for (const auto& e : enemies_)
            if (e.active) es += TextFormat("  %s:%d%s", e.id.c_str(), int(e.brain.state), e.crawling ? "c" : "");
        DrawText(TextFormat("%d fps  shot %s  pos %.2f %.2f  %s  hp %.0f  mag %d/%d%s", GetFPS(), shot_.c_str(), player_.x, player_.z,
                            tank_ ? "TANK" : "MODERN", health_, guns_[gun_].mag, inv_.count_of(guns_[gun_].spec().ammo), es.c_str()),
                 10, 10, 18, YELLOW);
    }
}

}  // namespace dw
