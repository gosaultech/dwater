// damned_waters/engine/src/game.cpp
// Purpose: see game.hpp. Render order per frame:
//   1. plate: painted background, writing its painted DEPTH into the z-buffer
//   2. characters: real-time, depth-tested against the painting
//   3. blob shadows, then post (grain + vignette) to the window
#include "game.hpp"

#include <rlgl.h>
#include <cmath>
#include <cstdio>

#include "dw/shaders.hpp"

namespace dw {
namespace {
constexpr float LIGHT_SCALE = 2.4f;   // RoomSpec godot_energy -> this shader's units
float ease_out(float t) { return 1.0f - (1.0f - t) * (1.0f - t); }
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
    rt_ = LoadRenderTexture(W, H);
    near_ = float(rlGetCullDistanceNear());
    far_ = float(rlGetCullDistanceFar());
    hero_ = Character::make(Kind::Survivor);
    drowned_ = Character::make(Kind::Drowned);
    const Spawn& sp = spec_.spawns.count("start") ? spec_.spawns.at("start") : spec_.spawns.begin()->second;
    player_ = {sp.pos.x, sp.pos.z, sp.yaw};
    enemy_ = {0.6f, 1.6f, 0.0f};
    for (const auto& e : spec_.enemies)
        if (e.requires_flag.empty()) { enemy_ = {e.pos.x, e.pos.z, e.yaw}; break; }
    cut_to(select_shot(spec_.zones(), "", player_.x, player_.z));
    upload_lights();
    animate(0.0f);
    return true;
}

void Game::shutdown() {
    for (auto& [id, p] : plates_) { UnloadTexture(p.first); UnloadTexture(p.second); }
    hero_.unload();
    drowned_.unload();
    UnloadMesh(blob_mesh_);
    UnloadShader(plate_); UnloadShader(char_); UnloadShader(blob_); UnloadShader(post_);
    UnloadRenderTexture(rt_);
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
    SetShaderValue(char_, l_count_, &n, SHADER_UNIFORM_INT);
    SetShaderValueV(char_, l_pos_, pos, SHADER_UNIFORM_VEC4, 8);
    SetShaderValueV(char_, l_col_, col, SHADER_UNIFORM_VEC4, 8);
    SetShaderValueV(char_, l_dir_, dir, SHADER_UNIFORM_VEC4, 8);
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

void Game::move_player(float dt) {
    Actor& p = player_;
    p.speed = 0;
    if (health_ <= 0) { p.pose = Pose::Dead; return; }
    if (IsKeyPressed(KEY_T)) tank_ = !tank_;
    const float ix = float(IsKeyDown(KEY_D) || IsKeyDown(KEY_RIGHT)) - float(IsKeyDown(KEY_A) || IsKeyDown(KEY_LEFT));
    const float iy = float(IsKeyDown(KEY_W) || IsKeyDown(KEY_UP)) - float(IsKeyDown(KEY_S) || IsKeyDown(KEY_DOWN));
    if (qt_ >= 0) {   // quick turn: 180 degrees in 0.3 s
        qt_ = std::min(1.0f, qt_ + dt / 0.3f);
        p.yaw = qt_from_ + kPi * ease_out(qt_);
        if (qt_ >= 1) qt_ = -1;
        p.pose = Pose::Idle;
        return;
    }
    if (IsKeyPressed(KEY_Q)) { qt_ = 0; qt_from_ = p.yaw; return; }
    if (hurt_t_ > 0) { p.pose = Pose::Hurt; return; }
    if (IsMouseButtonDown(MOUSE_BUTTON_RIGHT) || IsKeyDown(KEY_K)) {
        p.yaw -= ix * 1.9f * dt;
        p.pose = Pose::Aim;
        return;
    }
    const float speed = IsKeyDown(KEY_LEFT_SHIFT) ? 3.8f : 1.9f;
    float mx = 0, mz = 0;
    if (tank_) {
        p.yaw -= ix * 2.6f * dt;
        V2 f = forward_from_yaw(p.yaw);
        float k = iy * speed * (iy < 0 ? 0.6f : 1.0f);
        mx = f.x * k; mz = f.z * k;
    } else {
        Vector3 fwd = Vector3Subtract(cam_.target, cam_.position);
        fwd.y = 0;
        fwd = Vector3Normalize(fwd);
        Vector3 right{-fwd.z, 0, fwd.x};
        Vector2 in{ix, iy};
        if (Vector2Length(in) < 0.2f) holding_ = false;
        else if (!holding_ || std::fabs(Vector2Angle(in, held_in_)) > 35.0f * DEG2RAD) {
            holding_ = true;   // keep this camera's basis until the stick changes: no cut-induced reversals
            held_fwd_ = fwd; held_right_ = right; held_in_ = in;
        }
        if (holding_) {
            Vector3 d = Vector3Add(Vector3Scale(held_right_, ix), Vector3Scale(held_fwd_, iy));
            if (Vector3Length(d) > 1) d = Vector3Normalize(d);
            mx = d.x * speed; mz = d.z * speed;
            p.yaw = step_yaw(p.yaw, yaw_towards(0, 0, d.x, d.z), 12.0f * dt);
        }
    }
    p.x += mx * dt;
    p.z += mz * dt;
    collide(p.x, p.z, 0.28f);
    p.speed = std::sqrt(mx * mx + mz * mz);
    p.pose = p.speed > 2.6f ? Pose::Run : p.speed > 0.1f ? Pose::Walk : Pose::Idle;
}

void Game::update_enemy(float dt) {
    Actor& e = enemy_;
    float dx = player_.x - e.x, dz = player_.z - e.z, dist = std::sqrt(dx * dx + dz * dz);
    V2 f = forward_from_yaw(e.yaw);
    float ang = std::acos(std::clamp((f.x * dx + f.z * dz) / std::max(dist, 1e-4f), -1.0f, 1.0f));
    bool sees = health_ > 0 && dist < 9.0f && (ang < 60.0f * DEG2RAD || dist < 1.5f);
    EEvent ev = brain_.update(dt, sees, false, dist);
    float want = yaw_towards(e.x, e.z, player_.x, player_.z);
    e.speed = 0;
    switch (brain_.state) {
        case EState::Pursuit: {
            e.yaw = step_yaw(e.yaw, want, 2.2f * dt);
            float align = std::clamp(std::cos(wrap_pi(want - e.yaw)), 0.2f, 1.0f);
            e.speed = 0.85f * align;
            e.pose = Pose::Shamble;
            break;
        }
        case EState::Attack: {
            bool striking = brain_.t >= brain_.windup;
            if (!striking) e.yaw = step_yaw(e.yaw, want, 1.4f * dt);
            e.speed = striking ? 2.0f : 0.0f;
            e.pose = striking ? Pose::Strike : Pose::Windup;
            break;
        }
        case EState::Alert: e.yaw = step_yaw(e.yaw, want, 1.2f * dt); e.pose = Pose::Idle; break;
        case EState::Recovery: e.pose = Pose::Shamble; break;
        default: e.pose = Pose::Idle;
    }
    V2 fw = forward_from_yaw(e.yaw);
    e.x += fw.x * e.speed * dt;
    e.z += fw.z * e.speed * dt;
    collide(e.x, e.z, 0.32f);
    if (ev == EEvent::Strike && dist <= 1.7f && ang < 55.0f * DEG2RAD && hurt_t_ <= 0 && health_ > 0) {
        health_ -= 20;
        hurt_t_ = 0.5f;
        player_.x += dx / std::max(dist, 1e-3f) * 0.35f;
        player_.z += dz / std::max(dist, 1e-3f) * 0.35f;
        collide(player_.x, player_.z, 0.28f);
    }
    // Bodies don't overlap.
    dx = player_.x - e.x; dz = player_.z - e.z;
    float d2 = std::sqrt(dx * dx + dz * dz), minD = 0.6f;
    if (d2 < minD && d2 > 1e-4f) { player_.x += dx / d2 * (minD - d2); player_.z += dz / d2 * (minD - d2); }
}

void Game::animate(float dt) {
    hero_.place({player_.x, 0, player_.z}, player_.yaw);
    hero_.animate(player_.pose, player_.speed, dt);
    drowned_.place({enemy_.x, 0, enemy_.z}, enemy_.yaw);
    drowned_.animate(enemy_.pose, enemy_.speed, dt);
}

void Game::update(float dt) {
    time_ += dt;
    hurt_t_ -= dt;
    banner_t_ -= dt;
    if (IsKeyPressed(KEY_F3)) debug = !debug;
    move_player(dt);
    update_enemy(dt);
    std::string next = select_shot(spec_.zones(), shot_, player_.x, player_.z);
    if (next != shot_) cut_to(next);
    upload_lights();
    animate(dt);
}

std::string Game::stage(int i) {
    struct S { float px, pz, pyaw; Pose ppose; float pspeed, ex, ez, eyaw; Pose epose; float espeed; const char* name; };
    static const S setups[] = {
        {1.0f, 7.2f, kPi, Pose::Aim, 0, 1.1f, 8.85f, 0.0f, Pose::Windup, 0, "front_door_windup"},
        {0.62f, 2.45f, kPi, Pose::Idle, 0, 0.55f, 1.0f, kPi, Pose::Shamble, 0.6f, "cellar_door_behind_you"},
        {0.75f, 4.6f, 0.0f, Pose::Walk, 1.9f, 0.6f, 2.0f, kPi, Pose::Shamble, 0.7f, "hall_approach"},
        {1.35f, 0.45f, kPi, Pose::Idle, 0, 0.6f, 2.2f, kPi, Pose::Idle, 0, "drowned_portrait"},
    };
    const S& s = setups[i];
    player_ = {s.px, s.pz, s.pyaw, s.pspeed, s.ppose};
    enemy_ = {s.ex, s.ez, s.eyaw, s.espeed, s.epose};
    cut_to(select_shot(spec_.zones(), "", player_.x, player_.z));
    for (int f = 0; f < 90; ++f) { time_ += 1.0f / 60; animate(1.0f / 60); }
    upload_lights();
    return s.name;
}

void Game::upload_studio_lights() {
    // Neutral three-point rig for judging a model: warm key front-left, cold fill, cold rim behind.
    const Vector4 pos[3] = {{-1.3f, 2.7f, -1.7f, 8.0f}, {1.6f, 1.2f, -1.3f, 8.0f}, {0.4f, 2.5f, 1.9f, 8.0f}};
    const Vector4 col[3] = {{1.0f * 3.6f, 0.78f * 3.6f, 0.55f * 3.6f, 0}, {0.45f, 0.55f, 0.8f, 0}, {0.6f * 3.2f, 0.7f * 3.2f, 1.0f * 3.2f, 0}};
    const Vector4 dir[3] = {};
    const int n = 3;
    SetShaderValue(char_, l_count_, &n, SHADER_UNIFORM_INT);
    SetShaderValueV(char_, l_pos_, pos, SHADER_UNIFORM_VEC4, 3);
    SetShaderValueV(char_, l_col_, col, SHADER_UNIFORM_VEC4, 3);
    SetShaderValueV(char_, l_dir_, dir, SHADER_UNIFORM_VEC4, 3);
    const float top[3] = {0.05f, 0.055f, 0.07f}, bot[3] = {0.02f, 0.018f, 0.015f}, rim[3] = {0.1f, 0.12f, 0.16f};
    const float fog[3] = {0, 0, 0}, fogr[2] = {50.0f, 60.0f};
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fog_, fog, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fogr_, fogr, SHADER_UNIFORM_VEC2);
}

void Game::model_sheet(const std::string& dir) {
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
    static const Subject subjects[] = {{"drowned", Kind::Drowned, 0, Pose::Idle}, {"drowned_windup", Kind::Drowned, 0, Pose::Windup},
                                       {"drowned_b", Kind::Drowned, 1, Pose::Shamble}, {"survivor", Kind::Survivor, 0, Pose::Idle}};
    upload_studio_lights();
    for (const auto& sub : subjects) {
        Character c = Character::make(sub.kind, sub.variant);
        c.place({0, 0, 0}, 0);
        for (int f = 0; f < 150; ++f) c.animate(sub.pose, sub.pose == Pose::Shamble ? 0.7f : 0.0f, 1.0f / 60);
        Image sheet = GenImageColor(4 * 400, kRows * 560, Color{10, 10, 12, 255});
        for (int v = 0; v < kViews; ++v) {
            const View& w = views[v];
            // Bodies orbit the feet; heads orbit the skull, starting from wherever the face points.
            Vector3 at{0, w.target_y, 0};
            float a = w.orbit_deg * DEG2RAD, e = w.elev_deg * DEG2RAD;
            if (w.head) {
                at = c.head_point();
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
    char who[32] = {};
    float orbit = 0, elev = 0, dist = 1, tx = 0, ty = 1, fovy = 30;
    if (std::sscanf(spec.c_str(), "%31[^,],%f,%f,%f,%f,%f,%f", who, &orbit, &elev, &dist, &tx, &ty, &fovy) != 7) return false;
    const std::string w = who;
    upload_studio_lights();
    Character c = Character::make(w == "survivor" ? Kind::Survivor : Kind::Drowned, 0);
    c.place({0, 0, 0}, 0);
    for (int f = 0; f < 150; ++f) c.animate(Pose::Idle, 0.0f, 1.0f / 60);
    const float a = orbit * DEG2RAD, e = elev * DEG2RAD;
    Camera3D cam{};
    cam.position = {tx + dist * std::sin(a) * std::cos(e), ty + dist * std::sin(e), -dist * std::cos(a) * std::cos(e)};
    cam.target = {tx, ty, 0};
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
    BeginTextureMode(rt_);
    ClearBackground(BLACK);
    rlEnableDepthTest();
    rlEnableDepthMask();
    BeginShaderMode(plate_);
    SetShaderValueTexture(plate_, l_depth_, plate.second);
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
    drowned_.draw(char_mat_);
    rlEnableBackfaceCulling();
    rlDisableDepthMask();
    BeginBlendMode(BLEND_ALPHA);
    const float strength = 0.55f;
    SetShaderValue(blob_, l_blob_, &strength, SHADER_UNIFORM_FLOAT);
    for (const Actor* a : {&player_, &enemy_})
        DrawMesh(blob_mesh_, blob_mat_, MatrixMultiply(MatrixScale(0.85f, 1, 0.85f), MatrixTranslate(a->x, 0.012f, a->z)));
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
    const char* cond = health_ > 66 ? "FINE" : health_ > 33 ? "CAUTION" : health_ > 0 ? "DANGER" : "YOU DIED";
    Color cc = health_ > 66 ? Color{90, 200, 110, 200} : health_ > 33 ? Color{230, 170, 40, 220} : Color{220, 40, 30, 230};
    if (health_ < 100) DrawText(cond, 40, GetScreenHeight() - 50, 22, cc);
    if (debug) DrawText(TextFormat("%d fps  shot %s  pos %.2f %.2f  %s  enemy %d", GetFPS(), shot_.c_str(), player_.x, player_.z,
                                   tank_ ? "TANK" : "MODERN", int(brain_.state)), 10, 10, 18, YELLOW);
}

}  // namespace dw
