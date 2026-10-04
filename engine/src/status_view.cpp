// damned_waters/engine/src/status_view.cpp
// Purpose: the status screen on screen (its rules are status.hpp's). Tab, or the View/Touchpad
// button, opens the case and time stands still. Three tabs, changed with L1 / R1:
//  * ITEMS: how he's doing (his figure as he stands now, a heart monitor's trace, one word), the
//    eight slots of the case, the gun in hand and what's left for it, and the selected thing
//    turning in 3D (the right stick turns it). Cross opens its actions; Square combines; Triangle
//    examines it big.
//  * FILES: the notes he's found, to read again.
//  * MAP: the house as far as he knows it, floor by floor: rooms he's been in, red while something
//    is still lying in one, blue once it's cleared; the doors, locked ones in red; where he stands.
// Finding something opens a smaller screen: it turns in the light, "Take it?"; if there's no room
// he can leave it or open the case to drop something for it.
// Everything is drawn at 1280 x 720 into ui_rt_ (scaled to the window in present()), over a
// blurred, darkened copy of the frame he left. Fonts: Cinzel for names and headings, EB Garamond
// for the words (both SIL OFL, engine/assets/fonts).
#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

#include "cast_items.hpp"
#include "game.hpp"

#include <rlgl.h>

namespace dw {
namespace {
const Color C_INK{214, 202, 178, 255}, C_DIM{128, 118, 104, 255}, C_FAINT{90, 82, 72, 255}, C_RED{168, 22, 18, 255}, C_RED_HI{220, 48, 36, 255},
    C_PANEL{14, 12, 12, 238}, C_LINE{70, 60, 52, 255}, C_GREEN{92, 214, 120, 255}, C_AMBER{232, 170, 48, 255};
Color cond_colour(Condition c) { return c == Condition::Fine ? C_GREEN : c == Condition::Caution ? C_AMBER : C_RED_HI; }
Color alpha(Color c, float a) { c.a = static_cast<unsigned char>(std::clamp(a, 0.0f, 1.0f) * float(c.a)); return c; }

// Text, placed by its left edge (align 0), middle (1) or right edge (2), y its vertical middle.
void text(const Font& f, const std::string& s, float x, float y, float size, Color c, int align = 0) {
    const Vector2 m = MeasureTextEx(f, s.c_str(), size, 0);
    DrawTextEx(f, s.c_str(), {x - (align == 1 ? m.x / 2 : align == 2 ? m.x : 0), y - size * 0.55f}, size, 0, c);
}
float width_of(const Font& f, const std::string& s, float size) { return MeasureTextEx(f, s.c_str(), size, 0).x; }
// Words wrapped to `width`, the text's own line breaks kept.
std::vector<std::string> wrap(const Font& f, const std::string& s, float size, float width) {
    std::vector<std::string> out;
    std::string line, word;
    for (size_t i = 0; i <= s.size(); ++i) {
        const char ch = i < s.size() ? s[i] : '\0';
        if (ch == ' ' || ch == '\n' || ch == '\0') {
            const std::string t = line.empty() ? word : line + " " + word;
            if (width_of(f, t, size) > width && !line.empty()) { out.push_back(line); line = word; }
            else line = t;
            word.clear();
            if (ch == '\n') { out.push_back(line); line.clear(); }
        } else {
            word += ch;
        }
    }
    if (!line.empty()) out.push_back(line);
    return out;
}
void panel(float x0, float y0, float x1, float y1, Color fill = C_PANEL, Color line = C_LINE) {
    DrawRectangleRec({x0, y0, x1 - x0, y1 - y0}, fill);
    DrawRectangleLinesEx({x0, y0, x1 - x0, y1 - y0}, 1, line);
}
// One beat of a heart monitor's trace at phase u (0..1 of a beat): P, QRS, T.
float ecg(float u) {
    if (u > 0.10f && u < 0.14f) return 0.18f * std::sin((u - 0.10f) / 0.04f * PI);
    if (u > 0.20f && u < 0.22f) return -0.25f;
    if (u > 0.22f && u < 0.25f) return 1.0f - std::fabs(u - 0.235f) / 0.015f * 0.9f;
    if (u > 0.25f && u < 0.27f) return -0.35f;
    if (u > 0.38f && u < 0.48f) return 0.3f * std::sin((u - 0.38f) / 0.10f * PI);
    return 0;
}
std::string storey_name(int s) { return s == 0 ? "GROUND FLOOR" : s < 0 ? (s == -1 ? "CELLAR" : "BELOW") : s == 1 ? "FIRST FLOOR" : "UPSTAIRS"; }
constexpr int PREVIEW_W = 900, PREVIEW_H = 640, ICON = 160;
enum Glyph { G_CONFIRM, G_BACK, G_COMBINE, G_EXAMINE, G_TAB_L, G_TAB_R, G_STICK, G_DPAD };
}  // namespace

void Game::init_status() {
    const std::string dir = repo_root() + "/engine/assets/fonts/";
    const char* extra = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~×·—–‘’“”éëïöüàèáóú…";
    int n = 0;
    int* cps = LoadCodepoints(extra, &n);
    auto load = [&](const char* file, int size) {
        Font f = LoadFontEx((dir + file).c_str(), size, cps, n);
        SetTextureFilter(f.texture, TEXTURE_FILTER_BILINEAR);
        return f;
    };
    f_head_ = load("Cinzel-Regular.ttf", 64);
    f_head_b_ = load("Cinzel-Bold.ttf", 64);
    f_body_ = load("EBGaramond-Regular.ttf", 48);
    f_body_b_ = load("EBGaramond-SemiBold.ttf", 48);
    f_italic_ = load("EBGaramond-Italic.ttf", 48);
    UnloadCodepoints(cps);
    for (int i = I_NONE + 1; i < I_COUNT; ++i) {
        const cast::ItemModel m = cast::item_model(i);
        if (m.mesh.count() == 0) continue;
        item_mesh_[i] = upload(m.mesh);
        item_centre_[i] = m.centre;
        item_size_[i] = m.size;
        float lo = 1e9f;
        for (size_t v = 0; v < m.mesh.count(); ++v) lo = std::min(lo, m.mesh.pos[v * 3 + 1]);
        item_base_[i] = lo - m.centre.y;
    }
    preview_rt_ = LoadRenderTexture(PREVIEW_W, PREVIEW_H);
    figure_rt_ = LoadRenderTexture(300, 600);
    ui_rt_ = LoadRenderTexture(W, H);
    blur_rt_ = LoadRenderTexture(W / 16, H / 16);
    icon_rt_ = LoadRenderTexture((I_COUNT - 1) * ICON, ICON);
    icons_ready_ = false;
    for (RenderTexture2D* r : {&preview_rt_, &figure_rt_, &ui_rt_, &blur_rt_, &icon_rt_}) SetTextureFilter(r->texture, TEXTURE_FILTER_BILINEAR);
    map_ = worldmap::load_all(repo_root() + "/game/data/rooms");
    worldmap::place(map_, spec_.id);
    storeys_ = worldmap::storeys(map_);
}

void Game::unload_status() {
    for (Font* f : {&f_head_, &f_head_b_, &f_body_, &f_body_b_, &f_italic_}) UnloadFont(*f);
    for (Mesh& m : item_mesh_)
        if (m.vertexCount) UnloadMesh(m);
    for (RenderTexture2D* r : {&preview_rt_, &figure_rt_, &ui_rt_, &blur_rt_, &icon_rt_}) UnloadRenderTexture(*r);
}

status::Pad Game::status_pad() const {
    status::Pad p;
    p.dx = in_.nav_x;
    p.dy = in_.nav_y;
    p.confirm = in_.hit(ACT_CONFIRM);
    p.back = in_.hit(ACT_BACK) || (in_.hit(ACT_STATUS) && !in_.ui_examine);   // (Type A: Triangle opens the case, and examines in it)
    p.combine = in_.ui_combine;
    p.examine = in_.ui_examine;
    p.tab = in_.ui_tab;
    return p;
}

void Game::update_status(float dt) {
    ui_t_ += dt;
    notice_t_ -= dt;
    const int before = status_.slot();
    const status::Mode was = status_.mode();
    const status::Command c = status_.update(status_pad(), inv_, gun_, int(notes_.size()), int(storeys_.size()));
    switch (status_.sound()) {
        case status::Sound::Move: sfx_.play("ui_move", 0.5f); break;
        case status::Sound::Confirm: sfx_.play("ui_confirm", 0.5f); break;
        case status::Sound::Back: sfx_.play("ui_back", 0.5f); break;
        case status::Sound::Deny: sfx_.play("ui_deny", 0.6f); break;
        default: break;
    }
    if (c.kind != status::Command::None) { notice_t_ = 0; apply(c); }
    if (status_.slot() != before || status_.mode() != was) { spin_ = 0.35f; tilt_ = 0; }   // a new thing to look at: start it turned to the light
    // The preview: the right stick (or the mouse, held) turns it; left alone it turns slowly.
    Vector2 turn = in_.look;
    if (IsMouseButtonDown(MOUSE_BUTTON_LEFT)) turn = Vector2Add(turn, Vector2Scale(in_.mouse, 0.08f));
    const bool held = std::fabs(turn.x) + std::fabs(turn.y) > 0.01f;
    spin_ += (held ? turn.x * 2.6f : 0.35f) * dt;
    tilt_ = std::clamp(tilt_ + turn.y * 1.6f * dt, -0.7f, 0.7f);
    if (!held) tilt_ *= std::exp(-dt * 1.5f);
}

// ── Rendering into the textures ─────────────────────────────────────────────────
void Game::render_status() {
    // The frame he left, small: drawn back up large it's a soft blur behind the case.
    BeginTextureMode(blur_rt_);
    DrawTexturePro(rt_.texture, {0, 0, float(W), -float(H)}, {0, 0, float(W / 16), float(H / 16)}, {0, 0}, 0, WHITE);
    EndTextureMode();
    // A product shot's lights for the preview and his figure (as the gun catalogue views).
    const Vector4 pos[8] = {{-0.5f, 1.3f, 1.1f, 9.0f}, {1.3f, 0.2f, 0.9f, 9.0f}, {0.2f, 1.6f, -0.4f, 9.0f}, {-0.6f, 0.4f, -1.3f, 9.0f}};
    const Vector4 col[8] = {{2.0f, 1.94f, 1.85f, 0}, {0.5f, 0.52f, 0.56f, 0}, {1.0f, 0.98f, 0.95f, 0}, {0.9f, 0.9f, 0.95f, 0}};
    const Vector4 dir[8] = {};
    set_lights(pos, col, dir, 4);
    static_lights_ = 4;
    flash_light_ = lamp_light_ = -1;
    const float top[3] = {0.16f, 0.16f, 0.17f}, bot[3] = {0.07f, 0.07f, 0.07f}, rim[3] = {0.25f, 0.22f, 0.2f};
    const float env_top[3] = {0.8f, 0.78f, 0.75f}, env_bot[3] = {0.05f, 0.05f, 0.055f}, fog[3] = {0, 0, 0}, fogr[2] = {50.0f, 60.0f}, softbox = 0.35f;
    SetShaderValue(char_, l_softbox_, &softbox, SHADER_UNIFORM_FLOAT);
    SetShaderValue(char_, l_top_, top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_bot_, bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_rim_, rim, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_top_, env_top, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_env_bot_, env_bot, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fog_, fog, SHADER_UNIFORM_VEC3);
    SetShaderValue(char_, l_fogr_, fogr, SHADER_UNIFORM_VEC2);
    for (auto& sm : shadows_) sm.light = sm.dyn = -1;
    bind_shadows();
    if (!icons_ready_) {   // each item's icon, once: the model turned a little toward the light, into its cell
        RenderTexture2D one = LoadRenderTexture(ICON, ICON);
        for (int i = I_NONE + 1; i < I_COUNT; ++i) {
            BeginTextureMode(one);
            ClearBackground(Color{0, 0, 0, 0});
            draw_item(i, i == I_HANDGUN || i == I_SHOTGUN ? 0.25f : 0.55f, 0.25f, 1.0f);
            EndTextureMode();
            BeginTextureMode(icon_rt_);
            if (i == I_NONE + 1) ClearBackground(Color{0, 0, 0, 0});
            DrawTextureRec(one.texture, {0, 0, float(ICON), -float(ICON)}, {float((i - 1) * ICON), 0}, WHITE);
            EndTextureMode();
        }
        UnloadRenderTexture(one);
        icons_ready_ = true;
    }
    // The thing to show: what he found, or what's under the cursor.
    using status::Mode;
    const Mode md = status_.mode();
    const int item = md == Mode::Pickup || md == Mode::NoRoom ? status_.pickup_item() : inv_.slots[size_t(status_.slot())].item;
    BeginTextureMode(preview_rt_);
    ClearBackground(Color{0, 0, 0, 0});
    if (item != I_NONE) draw_item(item, spin_, tilt_ + 0.15f, float(PREVIEW_W) / float(PREVIEW_H));
    EndTextureMode();
    // His figure, as he stands right now (the limp shows), lit like a photograph.
    if (status_.tab() == status::Tab::Items && md != Mode::Pickup && md != Mode::NoRoom) {
        const V2 f = forward_from_yaw(player_.yaw);
        const V2 r{-f.z, f.x};
        // A portrait's lights, where he stands: a key high in front and to one side, a fill, a rim behind.
        auto at = [&](float fw, float side, float up) { return Vector4{player_.x + f.x * fw + r.x * side, up, player_.z + f.z * fw + r.z * side, 9.0f}; };
        const Vector4 fpos[8] = {at(2.0f, 1.2f, 2.4f), at(1.6f, -1.8f, 1.2f), at(-1.5f, 0.6f, 2.2f), at(-1.2f, -1.0f, 1.6f)};
        const Vector4 fcol[8] = {{3.2f, 3.0f, 2.7f, 0}, {0.8f, 0.85f, 0.95f, 0}, {1.6f, 1.6f, 1.8f, 0}, {0.9f, 0.9f, 1.0f, 0}};
        set_lights(fpos, fcol, dir, 4);
        BeginTextureMode(figure_rt_);
        ClearBackground(Color{0, 0, 0, 0});
        Camera3D cam{};
        cam.fovy = 34;
        cam.projection = CAMERA_PERSPECTIVE;
        cam.target = {player_.x, 0.93f, player_.z};
        cam.position = {player_.x + f.x * 3.5f + r.x * 1.1f, 1.25f, player_.z + f.z * 3.5f + r.z * 1.1f};
        cam.up = {0, 1, 0};
        BeginMode3D(cam);
        SetShaderValue(char_, l_cam_, &cam.position, SHADER_UNIFORM_VEC3);
        rlDisableBackfaceCulling();
        hero_.draw(char_mat_);
        rlEnableBackfaceCulling();
        EndMode3D();
        EndTextureMode();
    }
    upload_lights();   // the room's lights back for the game
    BeginTextureMode(ui_rt_);
    ClearBackground(BLACK);
    draw_status_ui();
    EndTextureMode();
    status_drawn_ = true;
}

// One item's model, framed to fill the view it's drawn into (aspect: that view's width / height).
void Game::draw_item(int item, float spin, float tilt, float aspect) {
    if (item <= I_NONE || item >= I_COUNT || item_mesh_[item].vertexCount == 0) return;
    Camera3D cam{};
    cam.fovy = 22;
    cam.projection = CAMERA_PERSPECTIVE;
    const float fit = item_size_[item] * 0.5f / std::tan(cam.fovy * 0.5f * DEG2RAD) / std::min(1.0f, aspect);   // its length across the view
    cam.position = {0, fit * 0.18f, fit};
    cam.target = {0, 0, 0};
    cam.up = {0, 1, 0};
    BeginMode3D(cam);
    SetShaderValue(char_, l_cam_, &cam.position, SHADER_UNIFORM_VEC3);
    rlDisableBackfaceCulling();
    const Vector3 c = item_centre_[item];
    DrawMesh(item_mesh_[item], char_mat_, MatrixMultiply(MatrixMultiply(MatrixTranslate(-c.x, -c.y, -c.z), MatrixRotateY(spin)), MatrixRotateX(tilt)));
    rlEnableBackfaceCulling();
    EndMode3D();
}

// ── Buttons, as the pad in hand shows them ──────────────────────────────────────
void Game::draw_glyph(float x, float y, int which, const char* label, float s) const {
    const float r = s / 2, cx = x + r, cy = y;
    if (in_.glyphs == 0) {   // the keyboard: a key cap
        const float w = std::max(s, width_of(f_head_b_, label, s * 0.5f) + s * 0.5f);
        DrawRectangleRounded({x, y - r, w, s}, 0.3f, 6, Color{58, 54, 50, 255});
        text(f_head_b_, label, x + w / 2, y, s * 0.5f, Color{235, 228, 215, 255}, 1);
        return;
    }
    if (which == G_TAB_L || which == G_TAB_R || which == G_STICK || which == G_DPAD) {   // shoulders, the stick, the d-pad
        const char* l = which == G_TAB_L ? (in_.glyphs == 1 ? "L1" : "LB") : which == G_TAB_R ? (in_.glyphs == 1 ? "R1" : "RB")
                      : which == G_STICK ? (in_.glyphs == 1 ? "R" : "RS") : "+";
        const float w = std::max(s * 1.2f, width_of(f_head_b_, l, s * 0.5f) + s * 0.6f);
        DrawRectangleRounded({x, y - r, w, s}, 0.45f, 6, Color{58, 54, 50, 255});
        text(f_head_b_, l, x + w / 2, y, s * 0.5f, Color{235, 228, 215, 255}, 1);
        return;
    }
    if (in_.glyphs == 2) {   // Xbox: coloured letters
        static const Color C[4] = {{70, 140, 60, 255}, {170, 40, 34, 255}, {50, 90, 170, 255}, {190, 150, 40, 255}};
        static const char* L[4] = {"A", "B", "X", "Y"};
        DrawCircleV({cx, cy}, r, C[which]);
        text(f_head_b_, L[which], cx, cy, s * 0.62f, Color{245, 242, 236, 255}, 1);
        return;
    }
    // PlayStation: the shapes themselves.
    DrawCircleV({cx, cy}, r, Color{40, 38, 38, 255});
    const float k = r * 0.48f, t = std::max(1.5f, s * 0.08f);
    switch (which) {
        case G_CONFIRM:
            DrawLineEx({cx - k, cy - k}, {cx + k, cy + k}, t, Color{120, 150, 230, 255});
            DrawLineEx({cx - k, cy + k}, {cx + k, cy - k}, t, Color{120, 150, 230, 255});
            break;
        case G_BACK: DrawRing({cx, cy}, k - t / 2, k + t / 2, 0, 360, 24, Color{230, 90, 90, 255}); break;
        case G_COMBINE: DrawRectangleLinesEx({cx - k, cy - k, 2 * k, 2 * k}, t, Color{220, 130, 200, 255}); break;
        default:
            DrawTriangleLines({cx, cy - k * 1.1f}, {cx - k * 1.05f, cy + k * 0.75f}, {cx + k * 1.05f, cy + k * 0.75f}, Color{90, 210, 180, 255});
            break;
    }
}

float Game::draw_hint(float x, float y, int which, const char* what) const {
    static const char* KEY[8] = {"Enter", "Esc", "C", "X", "Q", "R", "Mouse", "Arrows"};
    const float s = 26;
    draw_glyph(x, y, which, KEY[which], s);
    const float w = in_.glyphs == 0 ? std::max(s, width_of(f_head_b_, KEY[which], s * 0.5f) + s * 0.5f)
                  : which >= G_TAB_L ? std::max(s * 1.2f, width_of(f_head_b_, "LB", s * 0.5f) + s * 0.6f) : s;
    text(f_body_, what, x + w + 8, y, 21, Color{205, 195, 175, 255});
    return x + w + 8 + width_of(f_body_, what, 21) + 30;
}

// ── The screen ──────────────────────────────────────────────────────────────────
void Game::draw_status_ui() {
    using status::Mode;
    using status::Tab;
    const Mode md = status_.mode();
    // Behind it: the room he's standing in, out of focus and in shadow.
    DrawTexturePro(blur_rt_.texture, {0, 0, float(W / 16), -float(H / 16)}, {0, 0, float(W), float(H)}, {0, 0}, 0, WHITE);
    DrawRectangle(0, 0, W, H, Color{4, 4, 6, 214});
    DrawRectangleGradientV(0, 0, W, 120, Color{0, 0, 0, 140}, Color{0, 0, 0, 0});
    DrawRectangleGradientV(0, H - 140, W, 140, Color{0, 0, 0, 0}, Color{0, 0, 0, 160});
    const int item_sel = inv_.slots[size_t(status_.slot())].item;
    auto preview = [&](float cx, float cy, float w, float h) {   // the turning thing, in a warm pool of light
        DrawCircleGradient(int(cx), int(cy + h * 0.1f), w * 0.45f, Color{90, 70, 50, 70}, Color{0, 0, 0, 0});
        const float k = std::min(w / float(PREVIEW_W), h / float(PREVIEW_H));
        DrawTexturePro(preview_rt_.texture, {0, 0, float(PREVIEW_W), -float(PREVIEW_H)},
                       {cx - PREVIEW_W * k / 2, cy - PREVIEW_H * k / 2, PREVIEW_W * k, PREVIEW_H * k}, {0, 0}, 0, WHITE);
    };
    auto count_label = [&](int slot) -> std::string {   // what the slot's corner says
        const Slot& s = inv_.slots[size_t(slot)];
        if (s.item == I_HANDGUN || s.item == I_SHOTGUN) {
            const Firearm& g = guns_[s.item == I_HANDGUN ? 0 : 1];
            return TextFormat("%d / %d", g.mag, g.spec().mag);
        }
        return item_spec(s.item).max_stack > 1 ? std::to_string(s.count) : "";
    };
    auto hints = [&](std::initializer_list<std::pair<int, const char*>> hs) {
        DrawLine(50, 640, 1230, 640, Color{50, 44, 40, 255});
        float x = 60;
        for (const auto& [g, w] : hs) x = draw_hint(x, 676, g, w);
    };

    // ── Something found ──
    if (md == Mode::Pickup || md == Mode::NoRoom) {
        const int it = status_.pickup_item(), n = status_.pickup_count(), fit = status_.pickup_fits();
        preview(640, 270, 760, 400);
        const std::string name = item_spec(it).name;
        std::string head = name;
        for (char& ch : head) ch = char(std::toupper(static_cast<unsigned char>(ch)));
        if (n > 1) head += TextFormat("  \xC3\x97%d", n);   // ×
        text(f_head_b_, head, 640, 488, 40, C_INK, 1);
        const auto lines = wrap(f_italic_, item_spec(it).desc, 23, 900);
        for (size_t i = 0; i < lines.size() && i < 2; ++i) text(f_italic_, lines[i], 640, 528 + 28 * float(i), 23, Color{180, 170, 150, 255}, 1);
        const bool noroom = md == Mode::NoRoom;
        text(f_head_, noroom ? "No room in the case." : n > 1 ? "Take them?" : "Take it?", 640, 590, 26, noroom ? C_RED_HI : C_INK, 1);
        const char* opts[2] = {noroom ? "Make room" : "Take", "Leave it"};
        for (int k = 0; k < 2; ++k) {
            const float x = 555 + 170 * float(k);
            const bool on = status_.choice() == k;
            if (on) { DrawRectangleRec({x - 75, 610, 150, 36}, Color{80, 16, 12, 230}); DrawRectangleLinesEx({x - 75, 610, 150, 36}, 1, C_RED_HI); }
            text(on ? f_head_b_ : f_head_, opts[k], x, 628, 23, on ? C_INK : C_DIM, 1);
        }
        std::string where = TextFormat("Case %d / %d", int(inv_.slots.size()) - inv_.free_slots(), int(inv_.slots.size()));
        if (!noroom && fit < n && fit > 0) where = TextFormat("Room for %d of them  \xC2\xB7  ", fit) + where;
        else if (!noroom && inv_.has(it) && item_spec(it).max_stack > 1) where = TextFormat("With the %d you carry  \xC2\xB7  ", inv_.count_of(it)) + where;
        text(f_body_, where, 640, 666, 19, C_DIM, 1);
        float x = 500;
        x = draw_hint(x, 700, G_CONFIRM, "Choose");
        draw_hint(x, 700, G_BACK, "Leave it");
        return;
    }

    // ── The tabs ──
    if (md == Mode::MakeRoom || (md == Mode::Discard && status_.pickup_item() != I_NONE)) {
        text(f_head_, TextFormat("Make room for the %s", item_spec(status_.pickup_item()).name), 640, 44, 28, C_INK, 1);
        DrawLine(470, 64, 810, 64, C_RED_HI);
    } else {
        float x = 470;
        draw_glyph(400, 42, G_TAB_L, "Q", 26);
        for (int t = 0; t < status::TABS; ++t) {
            const bool on = int(status_.tab()) == t;
            const Font& f = on ? f_head_b_ : f_head_;
            text(f, status::tab_name(Tab(t)), x, 42, on ? 27 : 24, on ? C_INK : C_DIM);
            const float w = width_of(f, status::tab_name(Tab(t)), on ? 27 : 24);
            if (on) DrawRectangleRec({x, 60, w, 3}, C_RED_HI);
            x += w + 56;
        }
        draw_glyph(x - 20, 42, G_TAB_R, "R", 26);
    }

    // ── ITEMS ──
    if (status_.tab() == Tab::Items) {
        if (md == Mode::Examine) {   // big, turning, with its words
            preview(640, 300, 1100, 470);
            text(f_head_b_, item_spec(item_sel).name, 640, 540, 34, C_INK, 1);
            const auto lines = wrap(f_body_, item_spec(item_sel).desc, 23, 900);
            for (size_t i = 0; i < lines.size() && i < 3; ++i) text(f_body_, lines[i], 640, 580 + 28 * float(i), 23, Color{190, 180, 160, 255}, 1);
            hints({{G_STICK, "Turn it"}, {G_BACK, "Back"}});
            return;
        }
        // How he's doing: his figure, the trace, one word.
        panel(50, 90, 390, 600);
        text(f_head_, "CONDITION", 70, 112, 20, C_DIM);
        DrawCircleGradient(220, 330, 150, Color{50, 46, 40, 90}, Color{0, 0, 0, 0});
        DrawTexturePro(figure_rt_.texture, {0, 0, 300, -600}, {220 - 90, 118, 180, 360}, {0, 0}, 0, WHITE);
        const Condition cond = condition(health_);
        const Color cc = cond_colour(cond);
        DrawRectangleRec({70, 480, 300, 60}, Color{4, 14, 8, 235});
        for (int gx = 70; gx < 370; gx += 20) DrawLine(gx, 481, gx, 539, Color{14, 34, 20, 255});
        DrawRectangleLinesEx({70, 480, 300, 60}, 1, Color{30, 60, 40, 255});
        const float bpm = status::heart_rate(health_), beats = 3.2f;   // three beats or so across the screen
        Vector2 prev{};
        for (int i = 0; i < 296; ++i) {   // the trace sweeps: brightest at the head, fading behind it
            const float tt = float(i) / 296.0f * beats + ui_t_ * bpm / 60.0f;
            const Vector2 p{72.0f + float(i), 510 - ecg(tt - std::floor(tt)) * 24};
            if (i) DrawLineEx(prev, p, 2, alpha(cc, 0.25f + 0.75f * float(i) / 296.0f));
            prev = p;
        }
        DrawCircleV(prev, 3, cc);
        text(f_head_b_, status::condition_name(cond), 70, 570, 34, cc);

        // The case.
        panel(420, 90, 860, 600);
        text(f_head_, md == Mode::Combine ? "COMBINE WITH..." : "CASE", 440, 112, 20, md == Mode::Combine ? C_RED_HI : C_DIM);
        text(f_body_, TextFormat("%d / %d", int(inv_.slots.size()) - inv_.free_slots(), int(inv_.slots.size())), 840, 112, 19, C_DIM, 2);
        constexpr float SW = 96, GX = 446, GY = 140;
        const int from = status_.combine_from();
        for (int i = 0; i < int(inv_.slots.size()); ++i) {
            const float x = GX + float(i % 4) * (SW + 6), y = GY + float(i / 4) * (SW + 6);
            const Slot& s = inv_.slots[size_t(i)];
            const bool on = i == status_.slot();
            const bool can = md == Mode::Combine && i != from && status::can_combine(inv_.slots[size_t(from)].item, s.item);
            DrawRectangleRec({x, y, SW, SW}, s.item ? Color{26, 22, 20, 235} : Color{16, 14, 14, 200});
            if (can) DrawRectangleLinesEx({x + 2, y + 2, SW - 4, SW - 4}, 1, Color{150, 120, 70, 255});
            if (i == from && md == Mode::Combine) DrawRectangleLinesEx({x, y, SW, SW}, 2, Color{200, 160, 90, 255});
            DrawRectangleLinesEx({x, y, SW, SW}, on ? 3.0f : 1.0f, on ? C_RED_HI : Color{60, 52, 46, 255});
            if (on) for (int k = 1; k < 6; ++k) DrawRectangleLinesEx({x - float(k), y - float(k), SW + 2.0f * float(k), SW + 2.0f * float(k)}, 1, alpha(C_RED, 0.35f - 0.06f * float(k)));
            if (s.item != I_NONE) {   // its icon: the model, small and still
                const float ix = float((s.item - 1) * ICON);
                DrawTexturePro(icon_rt_.texture, {ix, 0, float(ICON), -float(ICON)}, {x + 4, y + 2, SW - 8, SW - 8}, {0, 0}, 0, WHITE);
                const std::string cnt = count_label(i);
                if (!cnt.empty()) text(f_body_b_, cnt, x + SW - 7, y + SW - 15, 19, C_INK, 2);
                if ((s.item == I_HANDGUN && gun_ == 0) || (s.item == I_SHOTGUN && gun_ == 1)) {   // in hand
                    DrawRectangleRec({x + 4, y + 4, 18, 18}, C_RED);
                    text(f_head_b_, "E", x + 13, y + 13, 14, Color{240, 230, 220, 255}, 1);
                }
            }
        }
        // What's in hand, at a glance.
        DrawLine(440, 360, 840, 360, Color{60, 52, 46, 255});
        text(f_head_, "IN HAND", 440, 386, 18, C_DIM);
        const Firearm& g = guns_[gun_];
        text(f_head_b_, g.spec().name, 440, 420, 26, C_INK);
        text(f_body_b_, TextFormat("%d / %d", g.mag, g.spec().mag), 840, 420, 30, C_INK, 2);
        text(f_italic_, gun_ == 0 ? "spare 9mm" : "spare shells", 440, 452, 20, C_DIM);
        text(f_body_, std::to_string(inv_.count_of(g.spec().ammo)), 840, 452, 22, C_DIM, 2);
        const Firearm& o = guns_[1 - gun_];
        if (inv_.has(o.spec().item))
            text(f_body_, TextFormat("%s   %d / %d  \xC2\xB7  spare %d", o.spec().name, o.mag, o.spec().mag, inv_.count_of(o.spec().ammo)), 440, 486, 20, C_DIM);
        const std::string& line = notice_t_ > 0 && !notice_.empty() ? notice_ : status_.note();
        text(f_italic_, line.empty() ? "Time stands still while the case is open." : line, 440, 560, 19,
             line.empty() ? Color{110, 100, 88, 255} : Color{210, 190, 150, 255});

        // The thing under the cursor.
        panel(890, 90, 1230, 600);
        if (item_sel != I_NONE) {
            preview(1060, 215, 320, 230);
            text(f_italic_, "turn it with the right stick", 1060, 330, 16, Color{100, 92, 80, 255}, 1);
            text(f_head_b_, item_spec(item_sel).name, 910, 372, 28, C_INK);
            const auto lines = wrap(f_body_, item_spec(item_sel).desc, 20, 300);
            for (size_t i = 0; i < lines.size() && i < 5; ++i) text(f_body_, lines[i], 910, 410 + 25 * float(i), 20, Color{190, 180, 160, 255});
            std::string stat;
            if (item_sel == I_HANDGUN || item_sel == I_SHOTGUN) stat = TextFormat("Holds %d", weapon_spec(item_sel == I_HANDGUN ? Weapon::Pistol : Weapon::Shotgun).mag);
            else if (status::gun_for_ammo(item_sel) >= 0) stat = std::string("Combine with the ") + weapon_spec(Weapon(status::gun_for_ammo(item_sel))).name + " to load it";
            else if (is_medicine(item_sel)) stat = health_ >= MAX_HEALTH ? "You don't need it now." : "Use it to treat your wounds.";
            else if (item_sel == I_CELLAR_KEY) stat = "It's used at its door.";
            text(f_italic_, stat, 910, 556, 17, C_DIM);
        } else {
            text(f_italic_, "Empty.", 1060, 330, 22, C_FAINT, 1);
        }

        // The action list, open on the slot.
        if (md == Mode::Actions) {
            status::Action acts[status::MAX_ACTIONS];
            const int n = status_.actions(acts);
            const float mx = GX + float(status_.slot() % 4) * (SW + 6) + SW + 10, my = GY + float(status_.slot() / 4) * (SW + 6) + 4;
            panel(mx, my, mx + 170, my + 18 + 36 * float(n), Color{10, 8, 8, 245}, C_RED);
            for (int k = 0; k < n; ++k) {
                const float yy = my + 26 + 36 * float(k);
                const bool on = k == status_.action();
                if (on) DrawRectangleRec({mx + 3, yy - 15, 164, 30}, Color{80, 16, 12, 230});
                text(on ? f_head_b_ : f_head_, status::action_name(acts[k]), mx + 22, yy, 20, on ? C_INK : C_DIM);
            }
        }
        // Leaving something behind.
        if (md == Mode::Discard) {
            panel(420, 380, 860, 520, Color{10, 8, 8, 248}, C_RED);
            text(f_head_, TextFormat("Leave the %s here?", item_spec(item_sel).name), 640, 418, 23, C_INK, 1);
            for (int k = 0; k < 2; ++k) {
                const float x = 570 + 140 * float(k);
                const bool on = status_.choice() == k;
                if (on) DrawRectangleRec({x - 55, 458, 110, 34}, Color{80, 16, 12, 230});
                text(on ? f_head_b_ : f_head_, k == 0 ? "Yes" : "No", x, 475, 22, on ? C_INK : C_DIM, 1);
            }
        }
        if (md == Mode::Actions || md == Mode::Discard || md == Mode::Combine || md == Mode::MakeRoom)
            hints({{G_CONFIRM, md == Mode::MakeRoom ? "Leave this here" : "Select"}, {G_BACK, "Back"}});
        else
            hints({{G_CONFIRM, "Select"}, {G_BACK, "Close"}, {G_COMBINE, "Combine"}, {G_EXAMINE, "Examine"}, {G_STICK, "Turn"}, {G_TAB_R, "Tab"}});
        return;
    }

    // ── FILES ──
    if (status_.tab() == Tab::Files) {
        if (notes_.empty()) {
            panel(50, 90, 1230, 600);
            text(f_italic_, "Nothing to read yet. Notes and papers you find are kept here.", 640, 340, 24, C_FAINT, 1);
            hints({{G_BACK, "Close"}, {G_TAB_R, "Tab"}});
            return;
        }
        const NoteRead& nr = notes_[size_t(std::clamp(status_.file(), 0, int(notes_.size()) - 1))];
        if (md == Mode::Read) {   // the page itself, full: ink on old paper
            DrawRectangleRec({250, 80, 780, 560}, Color{206, 194, 166, 255});
            DrawRectangleLinesEx({250, 80, 780, 560}, 2, Color{120, 100, 74, 255});
            DrawRectangleGradientV(250, 80, 780, 60, Color{170, 150, 116, 120}, Color{0, 0, 0, 0});
            text(f_head_b_, nr.title, 640, 126, 30, Color{50, 36, 26, 255}, 1);
            const auto lines = wrap(f_italic_, nr.text, 23, 680);
            for (size_t i = 0; i < lines.size() && i < 17; ++i) text(f_italic_, lines[i], 300, 178 + 27 * float(i), 23, Color{44, 34, 28, 255});
            hints({{G_BACK, "Back"}});
            return;
        }
        panel(50, 90, 430, 600);
        text(f_head_, "FILES", 70, 112, 20, C_DIM);
        for (int i = 0; i < int(notes_.size()); ++i) {
            const float y = 150 + 40 * float(i);
            const bool on = i == status_.file();
            if (on) DrawRectangleRec({58, y - 17, 364, 34}, Color{80, 16, 12, 230});
            text(on ? f_head_b_ : f_head_, notes_[size_t(i)].title, 72, y, 20, on ? C_INK : C_DIM);
        }
        panel(460, 90, 1230, 600);
        text(f_head_b_, nr.title, 490, 128, 28, C_INK);
        const auto lines = wrap(f_body_, nr.text, 22, 700);
        for (size_t i = 0; i < lines.size() && i < 15; ++i) text(f_body_, lines[i], 490, 176 + 26 * float(i), 22, Color{190, 180, 160, 255});
        hints({{G_CONFIRM, "Read"}, {G_BACK, "Close"}, {G_DPAD, "Choose"}, {G_TAB_R, "Tab"}});
        return;
    }

    // ── MAP ──
    panel(50, 90, 1230, 600);
    const int si = std::clamp(status_.floor(), 0, std::max(0, int(storeys_.size()) - 1));
    const int storey = storeys_.empty() ? 0 : storeys_[size_t(si)];
    text(f_head_b_, storey_name(storey), 80, 122, 28, C_INK);
    for (int i = 0; i < int(storeys_.size()); ++i) {   // the floors, top first: up and down change them
        const bool on = i == si;
        text(on ? f_head_b_ : f_head_, storey_name(storeys_[size_t(i)]), 1200, 122 + 30 * float(i), 18, on ? C_INK : C_FAINT, 2);
    }
    // What he knows: rooms he's been in, and the rooms their doors open on.
    auto visited = [&](const worldmap::Room& r) { return world_.visited.count(r.id) > 0; };
    std::vector<const worldmap::Room*> shown;
    for (const auto& r : map_) {
        if (!r.placed || r.storey != storey) continue;
        bool known = visited(r);
        for (const auto& o : map_)
            if (visited(o))
                for (const auto& d : o.doors) known = known || d.to == r.id;
        if (known) shown.push_back(&r);
    }
    if (shown.empty()) {
        text(f_italic_, "You haven't found the way down here.", 640, 360, 24, C_FAINT, 1);
    } else {
        float x0 = 1e9f, z0 = 1e9f, x1 = -1e9f, z1 = -1e9f;
        for (const auto* r : shown) {
            x0 = std::min(x0, r->ox + r->bounds.x0); x1 = std::max(x1, r->ox + r->bounds.x1);
            z0 = std::min(z0, r->oz + r->bounds.z0); z1 = std::max(z1, r->oz + r->bounds.z1);
        }
        const float ax = 120, ay = 170, aw = 1040, ah = 380;
        const float sc = std::min(aw / std::max(x1 - x0, 0.1f), ah / std::max(z1 - z0, 0.1f)) * 0.9f;
        const float offx = ax + (aw - (x1 - x0) * sc) / 2, offy = ay + (ah - (z1 - z0) * sc) / 2;
        auto to_screen = [&](float wx, float wz) { return Vector2{offx + (wx - x0) * sc, offy + (wz - z0) * sc}; };
        for (const auto* r : shown) {
            const Vector2 a = to_screen(r->ox + r->bounds.x0, r->oz + r->bounds.z0), b = to_screen(r->ox + r->bounds.x1, r->oz + r->bounds.z1);
            const Rectangle rr{a.x, a.y, b.x - a.x, b.y - a.y};
            const bool here = r->id == spec_.id, been = visited(*r);
            bool items = false;   // something still lying in it
            if (here) items = !loot_.empty();
            for (const auto& d : world_.dropped) items = items || (d.room == r->id && d.count > 0);
            if (been) {
                const Color fill = items ? Color{110, 32, 26, 200} : Color{36, 56, 86, 200};
                DrawRectangleRec(rr, fill);
                DrawRectangleLinesEx(rr, here ? 3.0f : 2.0f, here ? C_INK : Color{150, 140, 120, 255});
                if (width_of(f_head_, r->name, 20) < rr.width - 12) text(f_head_, r->name, rr.x + rr.width / 2, rr.y + rr.height / 2, 20, C_INK, 1);
                else text(f_head_, r->name, rr.x + rr.width + 14, rr.y + 16, 20, C_INK);   // (too narrow: beside it)
            } else {   // seen through a door: its outline, dashed; its name not yet
                for (float t = 0; t < 1; t += 0.04f) {
                    DrawLineEx({rr.x + rr.width * t, rr.y}, {rr.x + rr.width * (t + 0.02f), rr.y}, 1.5f, C_FAINT);
                    DrawLineEx({rr.x + rr.width * t, rr.y + rr.height}, {rr.x + rr.width * (t + 0.02f), rr.y + rr.height}, 1.5f, C_FAINT);
                    DrawLineEx({rr.x, rr.y + rr.height * t}, {rr.x, rr.y + rr.height * (t + 0.02f)}, 1.5f, C_FAINT);
                    DrawLineEx({rr.x + rr.width, rr.y + rr.height * t}, {rr.x + rr.width, rr.y + rr.height * (t + 0.02f)}, 1.5f, C_FAINT);
                }
                text(f_head_, "?", rr.x + rr.width / 2, rr.y + rr.height / 2, 26, C_FAINT, 1);
            }
            for (const auto& d : r->doors) {   // its doors: a gap in the wall; red while locked; stairs marked
                const auto [ex, ez] = worldmap::to_edge(r->bounds, d.x, d.z);
                const Vector2 p = to_screen(r->ox + ex, r->oz + ez);
                const bool locked = !d.lock.empty() && !world_.unlocked.count(status::WorldState::key(r->id, d.id));
                if (d.stairs) {
                    for (int k = 0; k < 3; ++k) DrawRectangleRec({p.x - 8 + 5.0f * float(k), p.y - 2 - 4.0f * float(k), 5, 3 + 4.0f * float(k)}, Color{200, 190, 170, 255});
                } else {
                    DrawCircleV(p, 6, been ? Color{24, 22, 20, 255} : Color{20, 20, 20, 255});
                }
                if (locked) DrawRectangleRec({p.x - 5, p.y - 5, 10, 10}, C_RED_HI);
            }
            if (here) {   // where he stands, and which way he faces
                const Vector2 p = to_screen(r->ox + player_.x, r->oz + player_.z);
                const V2 f = forward_from_yaw(player_.yaw);
                const Vector2 fw{f.x, f.z}, side{-f.z, f.x};
                const float s = 11 + 2 * std::sin(ui_t_ * 4);
                DrawTriangle(Vector2Add(p, Vector2Scale(fw, s)), Vector2Add(p, Vector2Add(Vector2Scale(fw, -s * 0.6f), Vector2Scale(side, -s * 0.6f))),
                             Vector2Add(p, Vector2Add(Vector2Scale(fw, -s * 0.6f), Vector2Scale(side, s * 0.6f))), Color{240, 220, 120, 255});
                DrawTriangle(Vector2Add(p, Vector2Scale(fw, s)), Vector2Add(p, Vector2Add(Vector2Scale(fw, -s * 0.6f), Vector2Scale(side, s * 0.6f))),
                             Vector2Add(p, Vector2Add(Vector2Scale(fw, -s * 0.6f), Vector2Scale(side, -s * 0.6f))), Color{240, 220, 120, 255});
            }
        }
    }
    // The key to it.
    float lx = 80;
    auto key = [&](Color c, const char* what) {
        DrawRectangleRec({lx, 566, 18, 14}, c);
        text(f_body_, what, lx + 26, 573, 18, C_DIM);
        lx += 26 + width_of(f_body_, what, 18) + 30;
    };
    key(Color{110, 32, 26, 255}, "Something left here");
    key(Color{36, 56, 86, 255}, "Nothing left");
    key(C_RED_HI, "Locked");
    key(Color{240, 220, 120, 255}, "You");
    hints({{G_DPAD, "Floor"}, {G_BACK, "Close"}, {G_TAB_R, "Tab"}});
}

}  // namespace dw
