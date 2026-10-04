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
#include <cstring>

#include "cast_guns.hpp"
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
    l_env_top_ = GetShaderLocation(char_, "u_envTop");
    l_env_bot_ = GetShaderLocation(char_, "u_envBottom");
    l_softbox_ = GetShaderLocation(char_, "u_softbox");
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
    {   // the pistol's magazine as he holds the gun, to drop when he reloads
        Matrix turn = Character::pistol_hold();
        turn.m12 = turn.m13 = turn.m14 = 0;
        fx_.set_magazine(cast::m92fs(Character::pistol_hold()).load, Vector3Transform(cast::m92fs_well_out(), turn), Vector3Transform({1, 0, 0}, turn));
    }
    settings_ = settings_path.empty() ? Settings{} : Settings::load(settings_path);
    input_.scheme = settings_.scheme;
    hero_ = Character::make(Kind::Survivor);
    init_status();
    reset_fight();
    cut_to(select_shot(spec_.zones(), "", player_.x, player_.z));
    upload_lights();
    animate(0.0f);
    return true;
}

void Game::shutdown() {
    unload_status();
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
    l_pDynSh_ = GetShaderLocation(plate_, "u_dynShadow");
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

// Draw the casters' depth as one light sees them, into shadow map k.
void Game::shadow_pass(int k, const Camera3D& from, double near_d, double far_d, const std::vector<const Character*>& casters) {
    const double keep_near = rlGetCullDistanceNear(), keep_far = rlGetCullDistanceFar();
    rlSetClipPlanes(near_d, far_d);   // tight: precise depth
    const unsigned t1 = char_mat_.maps[MATERIAL_MAP_METALNESS].texture.id, t2 = char_mat_.maps[MATERIAL_MAP_NORMAL].texture.id;
    char_mat_.maps[MATERIAL_MAP_METALNESS].texture.id = 0;   // never sample a map while drawing into it
    char_mat_.maps[MATERIAL_MAP_NORMAL].texture.id = 0;
    BeginTextureMode(shadows_[k].rt);
    ClearBackground(WHITE);
    BeginMode3D(from);
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
}

namespace {
// A perspective view from `lp` that frames every point within `r` of `c`; false if it can't
// (the light is among them, or so close it would need a fisheye).
bool frame_from(Vector3 lp, Vector3 c, float r, Camera3D& lc, double& near_d, double& far_d) {
    const float dist = Vector3Distance(lp, c);
    if (dist < 0.5f) return false;
    lc = {};
    lc.position = lp;
    lc.target = c;
    lc.up = std::fabs(Vector3Normalize(Vector3Subtract(c, lp)).y) > 0.95f ? Vector3{0, 0, 1} : Vector3{0, 1, 0};
    lc.fovy = 2.0f * std::atan(r / dist) * RAD2DEG * 1.05f;
    lc.projection = CAMERA_PERSPECTIVE;
    near_d = std::max(0.05, double(dist - r - 0.3f));
    far_d = double(dist + r + 0.5f);
    return lc.fovy <= 165.0f;   // a hanging lamp right overhead would need a wider view than that
}
}  // namespace

void Game::render_shadows(const std::vector<const Character*>& casters, const std::vector<const Character*>& gun_lit) {
    for (auto& sm : shadows_) sm.light = sm.dyn = -1;
    if (light_n_ == 0) return;
    int used = 0;
    // The flash, then the flashlight: only a shadow map can hold back the light they add to the
    // painting, where a Drowned stands in the way.
    for (int slot = 0; slot < 2 && !gun_lit.empty(); ++slot) {
        const int li = slot == 0 ? flash_light_ : lamp_light_;
        if (li < 0) continue;
        const Vector4 p = light_pos_[li];
        const Vector3 lp{p.x, p.y, p.z};
        Camera3D lc{};
        double nd = 0.08, fd = p.w;
        if (slot == 1) {   // the flashlight: exactly its cone
            const Vector4 d = light_dir_[li];
            lc.position = lp;
            lc.target = Vector3Add(lp, {d.x, d.y, d.z});
            lc.up = std::fabs(d.y) > 0.95f ? Vector3{0, 0, 1} : Vector3{0, 1, 0};
            lc.fovy = 2.0f * std::acos(std::clamp(d.w, 0.0f, 1.0f)) * RAD2DEG * 1.1f;
            lc.projection = CAMERA_PERSPECTIVE;
        } else {           // the flash: framing the Drowned within its reach
            Vector3 c{};
            int n = 0;
            for (const Character* ch : gun_lit)
                if (Vector3Distance(ch->joint(J_PELVIS), lp) < p.w) { c = Vector3Add(c, ch->joint(J_PELVIS)); ++n; }
            if (n == 0) continue;
            c = Vector3Scale(c, 1.0f / float(n));
            float r = 0;
            for (const Character* ch : gun_lit)
                if (Vector3Distance(ch->joint(J_PELVIS), lp) < p.w) r = std::max(r, Vector3Distance(ch->joint(J_PELVIS), c));
            if (!frame_from(lp, c, r + 1.15f, lc, nd, fd)) continue;
        }
        shadow_pass(used, lc, nd, fd, gun_lit);
        shadows_[used].light = li;
        shadows_[used].dyn = slot;
        ++used;
    }
    if (used >= 2 || casters.empty()) return;
    // The room's lamps: the brightest on the characters, framing all of them.
    Vector3 c{};
    for (const Character* ch : casters) c = Vector3Add(c, ch->joint(J_PELVIS));
    c = Vector3Scale(c, 1.0f / float(casters.size()));
    float r = 0;
    for (const Character* ch : casters) r = std::max(r, Vector3Distance(ch->joint(J_PELVIS), c));
    r += 1.15f;   // a character reaches about a metre from its hips (hair, raised arms)
    struct Pick { int i; float e; };
    Pick picks[8];
    int np = 0;
    for (int i = 0; i < static_lights_; ++i) {
        const Vector4 p = light_pos_[i], col = light_col_[i];
        if (int(col.w + 0.5f) == 2) continue;                       // suns: none indoors
        const float dist = Vector3Distance({p.x, p.y, p.z}, c);
        const float x = std::clamp(1.0f - std::pow(dist / std::max(p.w, 1e-3f), 4.0f), 0.0f, 1.0f);
        const float e = (col.x + col.y + col.z) * x * x / (1.0f + dist * dist * 0.35f);
        if (e > 0.02f && np < 8) picks[np++] = {i, e};
    }
    for (int k = 0; k < std::min(np, 2); ++k)   // the brightest two to the front (all we need)
        for (int m = k + 1; m < np; ++m)
            if (picks[m].e > picks[k].e) std::swap(picks[k], picks[m]);
    for (int k = 0; k < np && used < 2; ++k) {
        const Vector4 p = light_pos_[picks[k].i];
        Camera3D lc{};
        double nd = 0, fd = 0;
        if (!frame_from({p.x, p.y, p.z}, c, r, lc, nd, fd)) continue;
        shadow_pass(used, lc, nd, fd, casters);
        shadows_[used].light = picks[k].i;
        ++used;
    }
}

void Game::bind_shadows() {
    int which[2], dyn_map[2] = {-1, -1};
    Vector4 pl[2];
    for (int k = 0; k < 2; ++k) {
        const ShadowMap& sm = shadows_[k];
        which[k] = sm.light;
        const Vector4 p = sm.light >= 0 ? light_pos_[sm.light] : Vector4{0, 0, 0, 0};
        // A room lamp's shadow darkens the painting (the lamp is painted in); the flash's and the
        // flashlight's hold back the light they add instead.
        pl[k] = {p.x, p.y, p.z, sm.light >= 0 && sm.dyn < 0 ? 1.0f : 0.0f};
        if (sm.dyn >= 0) dyn_map[sm.dyn] = k;
        SetShaderValueMatrix(char_, l_shVP_[k], sm.vp);
        SetShaderValueMatrix(plate_, l_pShVP_[k], sm.vp);
    }
    SetShaderValueV(char_, l_shLight_, which, SHADER_UNIFORM_INT, 2);
    SetShaderValueV(plate_, l_pShL_, pl, SHADER_UNIFORM_VEC4, 2);
    SetShaderValueV(plate_, l_pDynSh_, dyn_map, SHADER_UNIFORM_INT, 2);
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
    flash_light_ = lamp_light_ = -1;
    // The muzzle flash: one more light on the characters, and a light the painted room never saw
    // (the plate shader relights the painting with it, from the painted depth).
    Vector4 dpos[2]{}, dcol[2]{}, ddir[2]{};
    const float fp = fx_.flash_power();
    if (fp > 0) {
        const Vector3 at = fx_.flash_pos();
        const Vector3 c = Vector3Scale(FLASH_COLOR, fp / 4.0f);
        dpos[0] = {at.x, at.y, at.z, FLASH_RANGE};
        dcol[0] = {c.x, c.y, c.z, 0};
        if (n < 8) { pos[n] = dpos[0]; col[n] = dcol[0]; flash_light_ = n++; }
    }
    if (flashlight && hero_.has_lamp()) {
        const Vector3 at = hero_.lamp(), d = hero_.lamp_dir();
        dpos[1] = {at.x, at.y, at.z, LAMP_RANGE};
        dcol[1] = {LAMP_COLOR.x, LAMP_COLOR.y, LAMP_COLOR.z, 1};   // w: a spot
        ddir[1] = {d.x, d.y, d.z, std::cos(LAMP_HALF)};
        if (n < 8) { pos[n] = dpos[1]; col[n] = {LAMP_COLOR.x, LAMP_COLOR.y, LAMP_COLOR.z, 1}; dir[n] = ddir[1]; lamp_light_ = n++; }
    }
    SetShaderValueV(plate_, l_dynPos_, dpos, SHADER_UNIFORM_VEC4, 2);
    SetShaderValueV(plate_, l_dynCol_, dcol, SHADER_UNIFORM_VEC4, 2);
    SetShaderValueV(plate_, l_dynDir_, ddir, SHADER_UNIFORM_VEC4, 2);
    set_lights(pos, col, dir, n);
    const float top[3] = {0.03f, 0.034f, 0.046f}, bot[3] = {0.011f, 0.009f, 0.007f}, rim[3] = {0.1f, 0.12f, 0.16f};
    const float fog[3] = {0.006f, 0.007f, 0.009f}, fogr[2] = {5.0f, 16.0f};
    const float env_top[3] = {0.07f, 0.075f, 0.09f}, env_bot[3] = {0.02f, 0.017f, 0.014f};   // a dark hall to mirror
    const float no_softbox = 0;
    SetShaderValue(char_, l_softbox_, &no_softbox, SHADER_UNIFORM_FLOAT);
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_top_, env_top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_bot_, env_bot, SHADER_UNIFORM_VEC3);
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
    input_.scheme = settings_.scheme;
    in_ = input_.poll();
    in_.move = {in_.move.x + staged_in_.x, in_.move.y + staged_in_.y};   // (capture setups hold the stick from code)
    in_.down[ACT_AIM] = in_.down[ACT_AIM] || staged_aim_;
    time_ += dt;
    banner_t_ -= dt;
    if (IsKeyPressed(KEY_F3)) debug = !debug;
    // A line of text being read (something looked at, a locked door): time stands still.
    if (!text_queue_.empty()) {
        ui_t_ += dt;
        text_t_ += dt;
        if (in_.hit(ACT_CONFIRM) || in_.hit(ACT_BACK)) {
            if (size_t(text_t_ * 55.0f) < text_queue_.front().size()) {
                text_t_ = 1e3f;   // the rest at once
            } else {
                text_queue_.erase(text_queue_.begin());
                text_t_ = 0;
                sfx_.play("ui_move", 0.4f);
            }
        }
        sfx_.update();
        return;
    }
    // The case open (or something found): time stands still.
    if (status_.is_open()) {
        update_status(dt);
        sfx_.update();
        return;
    }
    if (in_.hit(ACT_PAUSE) && pmode_ != PMode::Dead) {
        paused_ = !paused_;
        menu_sel_ = 0;
        sfx_.play("ui_confirm", 0.6f);
    } else if (paused_) {
        update_menu();
    }
    if (paused_) { sfx_.update(); return; }   // time stands still
    if (in_.hit(ACT_STATUS) && pmode_ != PMode::Dead) {   // the case
        status_.open(status::Tab::Items);
        for (size_t i = 0; i < storeys_.size(); ++i)   // the map opens on the floor he's on
            if (storeys_[i] == spec_.floor) status_.show_floor(int(i));
        sfx_.play("case_open", 0.7f);
        return;
    }
    if (in_.hit(ACT_FLASHLIGHT)) { flashlight = !flashlight; sfx_.play("dry_fire", 0.3f, 0.05f); }   // its switch clicks
    // The slow-motion beat after a perfect dodge (an option): the world slows, then catches up.
    slowmo_t_ = std::max(0.0f, slowmo_t_ - dt);
    time_scale_ = slowmo_t_ > 0.2f ? 0.3f : slowmo_t_ > 0 ? 1.0f - 0.7f * slowmo_t_ / 0.2f : 1.0f;
    const float g = dt * time_scale_;
    update_player(g);
    update_enemies(g);
    fx_.update(g);
    for (Vector3 at; fx_.landed(at);) sfx_.play_at("mag_drop", at, ear(), ear_right(), 0.9f, 0.08f);   // an empty magazine on the floor
    sfx_.update();
    std::string next = select_shot(spec_.zones(), shot_, player_.x, player_.z);
    if (next != shot_) cut_to(next);
    animate(g);
    upload_lights();   // after the pose: the flash light sits where the muzzle is now
}

// ── The pause menu ──────────────────────────────────────────────────────────────
namespace {
constexpr int MENU_ITEMS = 5;   // resume, controller layout, slow motion, movement, quit
}

void Game::update_menu() {
    if (in_.hit(ACT_BACK)) { paused_ = false; return; }
    if (in_.nav_y) { menu_sel_ = (menu_sel_ - in_.nav_y + MENU_ITEMS) % MENU_ITEMS; sfx_.play("ui_move", 0.6f); }
    const int change = in_.nav_x != 0 ? in_.nav_x : in_.hit(ACT_CONFIRM) ? 1 : 0;
    switch (menu_sel_) {
        case 0: if (in_.hit(ACT_CONFIRM)) paused_ = false; return;
        case 1:
            if (!change) return;
            settings_.scheme = Scheme((int(settings_.scheme) + change + int(Scheme::Count)) % int(Scheme::Count));
            input_.scheme = settings_.scheme;
            break;
        case 2: if (!change) return; settings_.slowmo = !settings_.slowmo; break;
        case 3: if (!change) return; settings_.tank = !settings_.tank; break;
        default: if (in_.hit(ACT_CONFIRM)) quit_ = true; return;
    }
    save_settings();
    sfx_.play("ui_confirm", 0.6f);
}

void Game::draw_menu() const {
    const int sw = GetScreenWidth(), sh = GetScreenHeight(), fs = std::max(14, sh / 26), x = sw / 2 - fs * 11, y0 = sh / 3;
    DrawRectangle(0, 0, sw, sh, Color{0, 0, 0, 175});
    DrawText("PAUSED", x, y0 - fs * 3, fs * 2, Color{200, 190, 170, 255});
    const std::string items[MENU_ITEMS] = {
        "Resume",
        std::string("Controller layout:  < ") + scheme_name(settings_.scheme) + " >",
        std::string("Slow motion on a perfect dodge:  < ") + (settings_.slowmo ? "On" : "Off") + " >",
        std::string("Movement:  < ") + (settings_.tank ? "Tank (classic)" : "Modern") + " >",
        "Quit"};
    for (int i = 0; i < MENU_ITEMS; ++i) {
        const bool sel = i == menu_sel_;
        DrawText(items[i].c_str(), x, y0 + i * fs * 2, fs, sel ? Color{235, 225, 200, 255} : Color{130, 122, 112, 255});
        if (sel) DrawText(">", x - fs, y0 + i * fs * 2, fs, Color{170, 20, 16, 255});
    }
    // The chosen layout at a glance.
    const int acts[] = {ACT_AIM, ACT_FIRE, ACT_DODGE, ACT_KICK, ACT_QUICK_TURN, ACT_RELOAD, ACT_STATUS, ACT_FLASHLIGHT, ACT_WEAPON_1, ACT_WEAPON_2};
    int y = y0 + MENU_ITEMS * fs * 2 + fs;
    const int hs = std::max(12, fs * 3 / 4);
    for (size_t i = 0; i < sizeof(acts) / sizeof(acts[0]); ++i) {
        const int col = int(i % 2), row = int(i / 2);
        DrawText(TextFormat("%-12s %s", act_name(acts[i]), pad_button_name(pad_button(settings_.scheme, acts[i]))),
                 x + col * fs * 12, y + row * (hs + 6), hs, Color{150, 142, 130, 230});
    }
    y += 5 * (hs + 6) + fs / 2;
    DrawText("Aim: the right stick moves the aim over the body (head, arms, legs); flick it to switch target.", x, y, hs,
             Color{120, 114, 104, 220});
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
    paused_ = false;
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
        case 5: {   // the Remington 870 at two metres
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
        case 10: {   // a perfect dodge: dodged as the bite comes, it lunges into nothing and stumbles on past
            Enemy& e = join(0, 1.0f, 8.15f, 0.0f, EState::Attack);
            e.brain.t = e.brain.windup - 0.12f;   // about to bite
            player_ = {1.0f, 7.05f, kPi};
            run(DT);
            start_dodge({-1.0f, 0.0f});
            run(0.2f);
            TraceLog(LOG_INFO, "STAGE perfect dodge: state %d stumble %.2f focus %.2f hp %.0f", int(e.brain.state), e.stumble, focus_t_, health_);
            run(0.15f);
            name = "perfect_dodge";
            break;
        }
        case 11: {   // a counter kick in the last moment of the lunge: thrown back and floored
            Enemy& e = join(1, 1.0f, 8.2f, 0.0f, EState::Attack);
            e.brain.t = e.brain.windup - 0.15f;
            player_ = {1.0f, 7.0f, kPi};
            run(DT);
            const bool took = try_kick();
            run(0.35f);
            TraceLog(LOG_INFO, "STAGE counter: took %d counter %d state %d hp %.0f", int(took), int(kick_counter_), int(e.brain.state), health_);
            name = "counter_kick";
            break;
        }
        case 12: {   // the pause menu: the options
            join(0, 0.75f, 3.1f, kPi, EState::Idle);
            player_ = {1.05f, 5.55f, 0.0f};
            run(0.3f);
            paused_ = true;
            menu_sel_ = 1;
            name = "pause_menu";
            break;
        }
        case 13: {   // the M92FS run dry and reloaded: the empty magazine on the floor, the fresh one going up into the grip
            player_ = {1.0f, 5.2f, kPi};
            guns_[0].mag = 1;
            staged_aim_ = true;
            run(0.4f);
            fire();   // the last round: the slide locks open
            run(0.5f);
            reload();
            run(weapon_spec(Weapon::Pistol).reload_time * 0.56f);
            name = "pistol_reload";
            break;
        }
        case 14: {   // the 870 empty: the first shell on its way up into the loading port
            switch_gun(1);
            guns_[1].mag = 0;
            player_ = {1.0f, 5.2f, kPi};
            run(0.4f);
            reload();
            const WeaponSpec& s = weapon_spec(Weapon::Shotgun);
            run((s.reload_time + s.rack_time) * 0.4f);
            name = "shotgun_reload";
            break;
        }
        case 15: case 16: case 17: case 18: case 19: case 20: case 21: case 22: case 23: case 24: case 25: {
            // The status screen and the room's things, driven through the screen's own rules as a
            // player's thumbs would (status.hpp), then left open on the frame.
            auto press = [&](status::Pad p) {
                const status::Command c = status_.update(p, inv_, gun_, int(notes_.size()), int(storeys_.size()));
                if (c.kind != status::Command::None) apply(c);
            };
            auto nav = [](int dx, int dy) { status::Pad p; p.dx = dx; p.dy = dy; return p; };
            status::Pad ok, combine, examine, tab;
            ok.confirm = true;
            combine.combine = true;
            examine.examine = true;
            tab.tab = 1;
            auto marit = [&] {   // the parlour's note, as if he'd found it
                const RoomSpec v = RoomSpec::load(repo_root() + "/game/data/rooms/voorkamer.json");
                for (const auto& it : v.interactables)
                    if (it.kind == "note") { notes_.push_back({"voorkamer/" + it.id, it.title, it.text}); world_.notes.push_back("voorkamer/" + it.id); }
            };
            player_ = {1.05f, 6.4f, 0.0f};
            run(0.3f);
            guns_[0].mag = 9;
            if (i == 15) {
                status_.open();
                name = "status_items";
            } else if (i == 16) {
                health_ = 45;
                hero_.limp = limp_of(condition(health_));
                status_.open();
                press(nav(1, 0));
                press(ok);
                name = "status_actions";
            } else if (i == 17) {
                status_.open();
                press(nav(1, 0));
                press(nav(1, 0));
                press(combine);
                press(nav(-1, 0));
                press(nav(-1, 0));
                name = "status_combine";
            } else if (i == 18) {
                health_ = 18;
                hero_.limp = limp_of(condition(health_));
                status_.open();
                press(nav(1, 0));
                press(examine);
                name = "status_examine";
            } else if (i == 19) {
                marit();
                status_.open();
                press(tab);
                name = "status_files";
            } else if (i == 20) {
                marit();
                status_.open();
                press(tab);
                press(ok);
                name = "status_read";
            } else if (i == 21) {
                world_.dropped.push_back({spec_.id, I_MED_S, 1, 1.0f, 3.0f});
                refresh_loot();
                status_.open();
                press(tab);
                press(tab);
                name = "status_map";
            } else if (i == 22 || i == 23 || i == 24) {
                player_ = {1.6f, 6.4f, 0.0f};   // in front of the shells on the hall floor
                for (const auto& it : spec_.interactables)
                    if (it.id == "shells_gang") player_ = {it.pos.x - 0.1f, it.pos.z - 0.6f, yaw_towards(it.pos.x - 0.1f, it.pos.z - 0.6f, it.pos.x, it.pos.z)};
                run(0.5f);   // (settled where he stands)
                inv_.remove(I_SHELLS, 4);
                if (i > 22)
                    for (int k = 0; k < 8; ++k) inv_.add(k % 3 ? I_MED_S : I_MED_M, 1);   // a case with no room left
                const bool found = interact();
                TraceLog(LOG_INFO, "STAGE pickup: found %d", int(found));
                if (i > 22) press(ok);   // Take: no room
                if (i > 23) press(ok);   // Make room
                name = i == 22 ? "pickup_prompt" : i == 23 ? "pickup_no_room" : "pickup_make_room";
            } else {
                for (const auto& it : spec_.interactables)
                    if (it.id == "clock") player_ = {it.pos.x - 0.3f, it.pos.z - 0.7f, yaw_towards(it.pos.x - 0.3f, it.pos.z - 0.7f, it.pos.x, it.pos.z)};
                run(0.5f);
                const bool found = interact();
                text_t_ = 30;   // typed out
                TraceLog(LOG_INFO, "STAGE examine: found %d", int(found));
                name = "examine_text";
            }
            animate(DT);
            break;
        }
        default: {   // bitten once too often: the words coming up (26), and all of it, the choice there (14)
            join(1, 1.0f, 8.3f, 0.0f, EState::Pursuit);
            player_ = {1.0f, 7.4f, kPi};
            health_ = 15;
            hurt_player(20, 1.0f, 8.3f);
            run(i == 26 ? 2.4f : 6.0f);
            name = i == 26 ? "you_died_falling" : "you_died";
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
    static_lights_ = 3;
    flash_light_ = lamp_light_ = -1;
    const float top[3] = {0.05f, 0.055f, 0.07f}, bot[3] = {0.02f, 0.018f, 0.015f}, rim[3] = {0.1f, 0.12f, 0.16f};
    const float fog[3] = {0, 0, 0}, fogr[2] = {50.0f, 60.0f};
    const float env_top[3] = {0.12f, 0.13f, 0.15f}, env_bot[3] = {0.035f, 0.032f, 0.03f};
    const float no_softbox = 0;
    SetShaderValue(char_, l_softbox_, &no_softbox, SHADER_UNIFORM_FLOAT);
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_top_, env_top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_bot_, env_bot, SHADER_UNIFORM_VEC3);
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
    // who = survivor | drowned[N] (N: the citizen), optionally @head / @chest / @pelvis / @hand / @lhand to orbit that
    // joint instead (the target is then offset from it by target_x, target_y; @head orbits from the face),
    // then any of /pose=aim /gun=1 /limp=1 /cut=3+8 (regions cut off first; anatomy.hpp) /pitch=20
    // (aiming 20 degrees up; negative is down) /grip=0..5 (one hand on its gun, or holding a magazine or
    // a shell: Character::grip_view) /reload=0.4 (that far through a reload; the 870's: one shell, /rack
    // into an empty gun, /port starting from the loading port; /live plays it there in real time).
    std::string w = who, at_joint, opts;
    if (const auto k = w.find('/'); k != std::string::npos) { opts = w.substr(k); w.resize(k); }
    if (const auto k = w.find('@'); k != std::string::npos) { at_joint = w.substr(k + 1); w.resize(k); }
    if (w == "m92fs" || w == "r870") return gun_view(w, opts, orbit, elev, dist, tx, ty, fovy, png);
    const bool survivor = w == "survivor";
    const int variant = !survivor && w.size() > 7 ? std::atoi(w.c_str() + 7) : 0;
    upload_studio_lights();
    Character c = Character::make(survivor ? Kind::Survivor : Kind::Drowned, variant);
    c.place({0, 0, 0}, 0);
    Pose pose = Pose::Idle;
    std::vector<int> cuts;
    float pitch = 0;
    bool live = false;   // /live: a reload played up to its moment as the game plays it, not posed and settled there
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
        if (key == "pitch") pitch = float(std::atof(val.c_str())) * DEG2RAD;
        if (key == "grip") {   // one hand on its gun, the arms at rest (Character::grip_view)
            c.grip_view = std::atoi(val.c_str());
            c.set_weapon(c.grip_view == 1 || c.grip_view == 2 || c.grip_view == 5 ? 1 : 0);
        }
        if (key == "cut")
            for (size_t a = 0; a < val.size();) { cuts.push_back(std::atoi(val.c_str() + a)); a = std::min(val.find('+', a), val.size()) + 1; }
        if (key == "reload") {   // a reload, this far through (the pose is Reload): /reload=0.4, and for the 870 /rack /port
            pose = Pose::Reload;
            c.reloading.on = true;
            c.reloading.t = float(std::atof(val.c_str()));
        }
        if (key == "rack") c.reloading.kind = reload::Kind::ShellRack;
        if (key == "port") c.reloading.from_grip = false;
        if (key == "live") live = true;
        i = j;
    }
    const float speed = pose == Pose::Walk || pose == Pose::Shamble ? 0.8f : 0.0f;
    if (c.reloading.on && c.weapon() == 1 && c.reloading.kind == reload::Kind::Magazine) c.reloading.kind = reload::Kind::Shell;
    if (live && c.reloading.on) {   // played as the game plays it: from the aim, the reload running in real time up to t
        const float until = c.reloading.t;
        const float secs = c.weapon() == 0 ? 1.4f : c.reloading.kind == reload::Kind::ShellRack ? 0.9f : 0.5f;
        Character::Reloading r = c.reloading;
        c.reloading.on = false;
        for (int f = 0; f < 90; ++f) c.animate(Pose::Aim, 0, 1.0f / 60, pitch);
        for (float t = 0; t < until; t += 1.0f / 60 / secs) {
            r.t = std::min(t, until);
            c.reloading = r;
            c.pump = reload::pump(r.kind, r.t);
            c.animate(Pose::Reload, 0, 1.0f / 60, pitch);
        }
        r.t = until;
        c.reloading = r;
    } else {
        for (int f = 0; f < 90; ++f) c.animate(pose, speed, 1.0f / 60, pitch);
    }
    for (int r : cuts) { MeshData piece; Vector3 centre; c.sever(r, piece, centre); }
    if (survivor) {   // how true the barrel lies to where he faces (the shots fly along his facing)
        const Vector3 b = c.barrel_dir();
        TraceLog(LOG_INFO, "VIEW barrel dir %.2f %.2f %.2f  muzzle %.2f %.2f %.2f", b.x, b.y, b.z, c.muzzle().x, c.muzzle().y, c.muzzle().z);
    }
    if (!live) for (int f = 0; f < 60; ++f) c.animate(pose, speed, 1.0f / 60, pitch);
    else c.animate(pose, speed, 1.0f / 60, pitch);
    render_shadows({&c});
    bind_shadows();
    float a = orbit * DEG2RAD;
    const float e = elev * DEG2RAD;
    Vector3 at{tx, ty, 0};
    if (!at_joint.empty()) {
        const Vector3 j = at_joint == "head" ? c.head_point() : at_joint == "hand" ? c.joint(J_WRI_R)
                        : at_joint == "lhand" ? c.joint(J_WRI_L) : c.joint(at_joint == "chest" ? J_CHEST : J_PELVIS);
        at = {j.x + tx, j.y + ty, j.z};
        if (at_joint == "head") { const Vector3 f = c.face_dir(); a += std::atan2(f.x, -f.z); }
    }
    Camera3D cam{};
    cam.position = {at.x + dist * std::sin(a) * std::cos(e), at.y + dist * std::sin(e), at.z - dist * std::cos(a) * std::cos(e)};
    cam.target = at;
    cam.up = {0, 1, 0};
    if (c.grip_view >= 0) {   // a grip: orbit the gun in its own frame (orbit 90 = its right side, 0 = muzzle-on)
        const Matrix G = c.grip_view_frame();
        const Vector3 centre = c.grip_view == 0 || c.grip_view == 3 ? cast::m92fs_at(40 + tx * 1000, -55 + ty * 1000)
                             : c.grip_view == 1                     ? cast::r870_at(-15 + tx * 1000, -45 + ty * 1000)
                             : c.grip_view == 4                     ? cast::m92fs_at(25 + tx * 1000, -85 + ty * 1000)
                             : c.grip_view == 5                     ? cast::r870_at(165 + tx * 1000, -35 + ty * 1000)
                                                                    : cast::r870_at(335 + tx * 1000, -35 + ty * 1000);
        const Vector3 dir{std::sin(a) * std::cos(e), -std::cos(a) * std::cos(e), -std::sin(e)};   // (u, v, w) -> gun space
        cam.position = Vector3Transform(Vector3Add(centre, Vector3Scale(dir, dist)), G);
        cam.target = Vector3Transform(centre, G);
        cam.up = Vector3Subtract(Vector3Transform({0, 0, -1}, G), Vector3Transform({0, 0, 0}, G));
    }
    cam.fovy = fovy;
    cam.projection = CAMERA_PERSPECTIVE;
    BeginTextureMode(rt_);
    ClearBackground(Color{16, 16, 19, 255});
    BeginMode3D(cam);
    SetShaderValue(char_, l_cam_, &cam.position, SHADER_UNIFORM_VEC3);
    rlDisableBackfaceCulling();
    c.draw(char_mat_);
    rlEnableBackfaceCulling();
    if (std::getenv("DW_CLASH")) {   // (tuning) mark every arm point that's gone into the body (Character::clearance)
        std::vector<Vector3> clashes;
        const Character::Clearance cl = c.clearance(&clashes);
        rlDisableDepthTest();
        for (const Vector3& p : clashes) DrawSphere(p, 0.004f, RED);
        rlEnableDepthTest();
        TraceLog(LOG_INFO, "VIEW wrist bend (elbow-wrist vs wrist-knuckle) L %.0f R %.0f", c.wrist_bend(false) * RAD2DEG, c.wrist_bend(true) * RAD2DEG);
        TraceLog(LOG_INFO, "VIEW clearance (mm) larm %.0f rarm %.0f gun %.0f hands %.0f lhand-gun %.0f", cl.larm.depth * 1000, cl.rarm.depth * 1000,
                 cl.gun.depth * 1000, cl.hands.depth * 1000, cl.lhand_gun.depth * 1000);
    }
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

// A gun on its own, turned side-on (muzzle to the right, its right side facing the camera at
// orbit 0), lit like a catalogue photo so it can be held up against the real thing. opts:
//   /slide=0..1   the slide or fore-end worked back
//   /roll=deg     the picture turned (muzzle up), to match a reference photo's angle
//   /bg=dark      a black backdrop instead of the studio's pale grey
//   /obj=stem     also write the meshes to stem_fixed.obj and stem_moving.obj
//   /synthetic    the 870 in black synthetic rather than walnut
bool Game::gun_view(const std::string& who, const std::string& opts, float orbit, float elev, float dist, float tx, float ty,
                    float fovy, const std::string& png) {
    auto opt = [&](const char* key, float fallback) {
        const auto k = opts.find(key);
        return k == std::string::npos ? fallback : float(std::atof(opts.c_str() + k + std::strlen(key)));
    };
    const float back = opt("/slide=", 0), roll = opt("/roll=", 0);
    const bool dark = opts.find("/bg=dark") != std::string::npos;
    // A product shot: a big soft key above and in front, a fill from the other side, a light
    // behind to trace the edges, and pale surroundings for the steel to mirror.
    const Vector4 pos[8] = {{-0.5f, 1.3f, 1.1f, 9.0f}, {1.3f, 0.2f, 0.9f, 9.0f}, {0.2f, 1.6f, -0.4f, 9.0f}, {-0.6f, 0.4f, -1.3f, 9.0f}};
    const Vector4 col[8] = {{2.3f, 2.27f, 2.22f, 0}, {0.6f, 0.62f, 0.65f, 0}, {1.2f, 1.2f, 1.22f, 0}, {1.0f, 1.02f, 1.05f, 0}};
    const Vector4 dir[8] = {};
    set_lights(pos, col, dir, 4);
    static_lights_ = 4;
    flash_light_ = lamp_light_ = -1;
    const float top[3] = {0.2f, 0.2f, 0.21f}, bot[3] = {0.09f, 0.09f, 0.09f}, rim[3] = {0.2f, 0.2f, 0.21f};
    const float env_top[3] = {1.1f, 1.1f, 1.13f}, env_bot[3] = {0.05f, 0.05f, 0.055f};
    const float fog[3] = {0, 0, 0}, fogr[2] = {50.0f, 60.0f}, softbox = 0.35f;
    SetShaderValue(char_, l_softbox_, &softbox, SHADER_UNIFORM_FLOAT);
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_top_, env_top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_bot_, env_bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fog_, fog, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fogr_, fogr, SHADER_UNIFORM_VEC2);
    for (auto& sm : shadows_) sm.light = sm.dyn = -1;   // no characters: no shadow maps
    bind_shadows();
    const cast::Stock furniture = opts.find("/synthetic") != std::string::npos ? cast::Stock::Synthetic : cast::Stock::Walnut;
    cast::GunParts gp = who == "m92fs" ? cast::m92fs() : cast::r870(MatrixIdentity(), furniture);   // (straight, not as held)
    Mesh fixed = upload(gp.fixed), moving = upload(gp.moving);
    if (const auto k = opts.find("/obj="); k != std::string::npos) {   // the meshes as OBJ files (wrist space), for matching photos
        const std::string stem = opts.substr(k + 5, opts.find('/', k + 1) - (k + 5));
        // (raylib's ExportMesh keeps two decimals: a centimetre, far too coarse for a pistol)
        auto write = [](const MeshData& d, const std::string& path) {
            if (FILE* f = std::fopen(path.c_str(), "w")) {
                for (size_t i = 0; i < d.count(); ++i) std::fprintf(f, "v %.6f %.6f %.6f\n", d.pos[i * 3], d.pos[i * 3 + 1], d.pos[i * 3 + 2]);
                for (size_t t = 0; t + 2 < d.count(); t += 3) std::fprintf(f, "f %zu %zu %zu\n", t + 1, t + 2, t + 3);
                std::fclose(f);
            }
        };
        write(gp.fixed, stem + "_fixed.obj");
        write(gp.moving, stem + "_moving.obj");
    }
    Matrix lay = MatrixIdentity();   // wrist space -> side-on: -y to +x (the muzzle right), -z up, +x toward the camera
    lay.m0 = 0; lay.m4 = -1; lay.m8 = 0;
    lay.m1 = 0; lay.m5 = 0; lay.m9 = -1;
    lay.m2 = 1; lay.m6 = 0; lay.m10 = 0;
    const Matrix M = MatrixMultiply(MatrixTranslate(-gp.centre.x, -gp.centre.y, -gp.centre.z), lay);
    const Matrix Mm = MatrixMultiply(MatrixTranslate(gp.travel.x * back, gp.travel.y * back, gp.travel.z * back), M);
    const float a = orbit * DEG2RAD, e = elev * DEG2RAD;
    Camera3D cam{};
    cam.target = {tx, ty, 0};
    cam.position = {tx + dist * std::sin(a) * std::cos(e), ty + dist * std::sin(e), dist * std::cos(a) * std::cos(e)};
    cam.up = Vector3RotateByAxisAngle({0, 1, 0}, Vector3Normalize(Vector3Subtract(cam.target, cam.position)), roll * DEG2RAD);
    cam.fovy = fovy;
    cam.projection = CAMERA_PERSPECTIVE;
    constexpr int SS = 3;   // drawn at three times the size and shrunk: smooth edges on the machined parts
    RenderTexture2D big = LoadRenderTexture(W * SS, H * SS);
    BeginTextureMode(big);
    ClearBackground(dark ? Color{8, 8, 9, 255} : Color{226, 226, 228, 255});
    BeginMode3D(cam);
    SetShaderValue(char_, l_cam_, &cam.position, SHADER_UNIFORM_VEC3);
    rlDisableBackfaceCulling();
    DrawMesh(fixed, char_mat_, M);
    DrawMesh(moving, char_mat_, Mm);
    rlEnableBackfaceCulling();
    EndMode3D();
    EndTextureMode();
    Image img = LoadImageFromTexture(big.texture);
    ImageFlipVertical(&img);
    ImageResize(&img, W, H);
    const bool ok = ExportImage(img, png.c_str());
    UnloadImage(img);
    UnloadRenderTexture(big);
    UnloadMesh(fixed);
    UnloadMesh(moving);
    TraceLog(LOG_INFO, "VIEW %s: %d + %d triangles", who.c_str(), int(gp.fixed.count() / 3), int(gp.moving.count() / 3));
    upload_lights();
    return ok;
}

void Game::render() {
    const auto& plate = plates_.at(shot_);
    casters_.clear();   // (reused: no allocation per frame)
    gun_lit_.clear();
    casters_.push_back(&hero_);
    for (const auto& e : enemies_)
        if (e.active) { casters_.push_back(&e.body); gun_lit_.push_back(&e.body); }
    render_shadows(casters_, gun_lit_);
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
    draw_loot();           // what's lying about to be picked up
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
    status_drawn_ = false;
    if (status_.is_open()) render_status();
}

void Game::present() const {
    ClearBackground(BLACK);
    const float t = time_, res[2] = {float(W), float(H)};
    SetShaderValue(post_, l_time_, &t, SHADER_UNIFORM_FLOAT);
    SetShaderValue(post_, l_res_, res, SHADER_UNIFORM_VEC2);
    BeginShaderMode(post_);
    DrawTexturePro(rt_.texture, {0, 0, float(W), -float(H)}, {0, 0, float(GetScreenWidth()), float(GetScreenHeight())}, {0, 0}, 0, WHITE);
    EndShaderMode();
    if (status_.is_open() && status_drawn_) {   // the case, over everything
        DrawTexturePro(ui_rt_.texture, {0, 0, float(W), -float(H)}, {0, 0, float(GetScreenWidth()), float(GetScreenHeight())}, {0, 0}, 0, WHITE);
        return;
    }
    draw_glints();
    draw_text_box();
    if (banner_t_ > 0) {
        unsigned char a = static_cast<unsigned char>(std::min(1.0f, banner_t_) * 210);
        DrawText(spec_.display_name.c_str(), 40, 34, 26, Color{210, 200, 180, a});
    }
    // No HUD: how hurt he is shows in his limp; ammo and health live on the status screen.
    // Only death gets words on the screen, as in the classic games.
    if (pmode_ == PMode::Dead) draw_death();
    if (paused_) draw_menu();
    if (debug) {
        std::string es;
        for (const auto& e : enemies_)
            if (e.active) es += TextFormat("  %s:%d%s", e.id.c_str(), int(e.brain.state), e.crawling ? "c" : "");
        DrawText(TextFormat("%d fps  shot %s  pos %.2f %.2f  %s  hp %.0f  mag %d/%d%s", GetFPS(), shot_.c_str(), player_.x, player_.z,
                            settings_.tank ? "TANK" : "MODERN", health_, guns_[gun_].mag, inv_.count_of(guns_[gun_].spec().ammo), es.c_str()),
                 10, 10, 18, YELLOW);
    }
}

}  // namespace dw
