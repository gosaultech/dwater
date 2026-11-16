// damned_waters/engine/src/game_fx.cpp
// Purpose: the room's live layer over the painting (its "fx"; dw/fxlive.hpp for the timing): flames
// and smoke on upright cards facing the camera, a wire's sparks as short streaks, a beacon's halo,
// all depth-tested against the painted depth so a wall still hides them; and each one's light, as
// the difference from what the painting was rendered with, handed to the plate shader (a fire's
// glow breathing on the walls, a beacon's blue sweeping the street, a tube dying in a tram).
#include <raylib.h>
#include <raymath.h>
#include <rlgl.h>

#include <algorithm>
#include <array>
#include <cmath>

#include "dw/fxlive.hpp"
#include "dw/shaders.hpp"
#include "game.hpp"

namespace dw {

void Game::init_fx() {
    fire_sh_ = LoadShaderFromMemory(nullptr, shaders::FIRE_FS);
    smoke_sh_ = LoadShaderFromMemory(nullptr, shaders::SMOKE_FS);
    glow_sh_ = LoadShaderFromMemory(nullptr, shaders::GLOW_FS);
    for (auto [sh, loc] : {std::pair<Shader*, int*>{&fire_sh_, l_fire_}, {&smoke_sh_, l_smoke_}}) {
        loc[0] = GetShaderLocation(*sh, "u_time");
        loc[1] = GetShaderLocation(*sh, "u_seed");
        loc[2] = GetShaderLocation(*sh, "u_power");
    }
    l_glow_[0] = GetShaderLocation(glow_sh_, "u_color");
    l_glow_[1] = GetShaderLocation(glow_sh_, "u_power");
    l_pFxPos_ = GetShaderLocation(plate_, "u_fxPos");
    l_pFxCol_ = GetShaderLocation(plate_, "u_fxCol");
}

void Game::update_fx(float dt) {
    if (sparks_.size() != spec_.fx.size()) sparks_.assign(spec_.fx.size(), {});
    for (size_t i = 0; i < spec_.fx.size(); ++i) {
        const Fx& f = spec_.fx[i];
        if (f.kind == "sparks") sparks_[i].update(dt, time_, {f.pos.x, f.pos.y, f.pos.z}, f.every, f.seed);
    }
}

void Game::fx_plate() {
    // Up to four lights, the nearest the camera first: each the change from the painting's own.
    Vector4 pos[4]{}, col[4]{};
    int n = 0;
    std::array<std::pair<float, size_t>, 16> order{};
    size_t m = 0;
    for (size_t i = 0; i < spec_.fx.size() && m < order.size(); ++i)
        if (spec_.fx[i].kind != "smoke")
            order[m++] = {std::hypot(spec_.fx[i].pos.x - cam_.position.x, spec_.fx[i].pos.z - cam_.position.z), i};
    std::sort(order.begin(), order.begin() + std::ptrdiff_t(m));
    for (size_t k = 0; k < m && n < 4; ++k) {
        const Fx& f = spec_.fx[order[k].second];
        Vector3 d{};
        float reach = f.radius;
        if (f.kind == "fire") {
            const float b = (fxlive::fire(time_, f.seed) - 1.0f) * 1.6f;
            d = {b, b * 0.45f, b * 0.12f};
        } else if (f.kind == "strobe") {
            const float s = fxlive::strobe(time_, f.rate, f.seed) * 1.2f;
            d = {f.color.x * s, f.color.y * s, f.color.z * s};
        } else if (f.kind == "flicker") {
            const float s = (fxlive::flicker(time_, f.seed) - 1.0f) * f.amount * 2.0f;
            d = {s, s * 0.88f, s * 0.7f};
        } else if (f.kind == "sparks") {
            const float s = order[k].second < sparks_.size() ? sparks_[order[k].second].flash() * 1.5f : 0.0f;
            d = {s * 0.7f, s * 0.8f, s};
            reach = 3.0f;
        } else {
            continue;
        }
        pos[n] = {f.pos.x, f.pos.y, f.pos.z, reach};
        col[n] = {d.x, d.y, d.z, 0.0f};
        ++n;
    }
    SetShaderValueV(plate_, l_pFxPos_, pos, SHADER_UNIFORM_VEC4, 4);
    SetShaderValueV(plate_, l_pFxCol_, col, SHADER_UNIFORM_VEC4, 4);
}

void Game::draw_fx() const {
    if (spec_.fx.empty() || peek_ >= 0) return;
    rlDrawRenderBatchActive();
    rlDisableDepthMask();   // (tested against the painting and the people, never hiding them)
    rlDisableBackfaceCulling();
    const Vector3 cp = cam_.position;
    const Vector3 fw = Vector3Normalize(Vector3Subtract(cam_.target, cp));
    const Vector3 r = Vector3Normalize(Vector3CrossProduct(fw, {0, 1, 0}));
    const Vector3 up = Vector3CrossProduct(r, fw);
    auto card = [&](Vector3 base, float w, float h, bool upright) {   // facing the camera; upright: standing on its foot
        const Vector3 v = upright ? Vector3{0, 1, 0} : up;
        const Vector3 o = upright ? base : Vector3Subtract(base, Vector3Scale(v, h / 2));
        rlBegin(RL_QUADS);
        rlColor4ub(255, 255, 255, 255);
        rlTexCoord2f(0, 1); rlVertex3f(o.x - r.x * w / 2, o.y - r.y * w / 2, o.z - r.z * w / 2);
        rlTexCoord2f(1, 1); rlVertex3f(o.x + r.x * w / 2, o.y + r.y * w / 2, o.z + r.z * w / 2);
        rlTexCoord2f(1, 0); rlVertex3f(o.x + r.x * w / 2 + v.x * h, o.y + r.y * w / 2 + v.y * h, o.z + r.z * w / 2 + v.z * h);
        rlTexCoord2f(0, 0); rlVertex3f(o.x - r.x * w / 2 + v.x * h, o.y - r.y * w / 2 + v.y * h, o.z - r.z * w / 2 + v.z * h);
        rlEnd();
    };
    auto set3 = [&](const Shader& sh, const int* loc, float seed, float power) {
        SetShaderValue(sh, loc[0], &time_, SHADER_UNIFORM_FLOAT);
        SetShaderValue(sh, loc[1], &seed, SHADER_UNIFORM_FLOAT);
        SetShaderValue(sh, loc[2], &power, SHADER_UNIFORM_FLOAT);
    };
    for (const Fx& f : spec_.fx) {   // smoke first (it's behind the flames that make it)
        if (f.kind != "smoke") continue;
        BeginBlendMode(BLEND_ALPHA);
        BeginShaderMode(smoke_sh_);
        for (int k = 0; k < 3; ++k) {
            set3(smoke_sh_, l_smoke_, float(f.seed * 7 + k), 1.0f);
            const float s = f.size * (1.0f + 0.45f * float(k));
            card({f.pos.x + r.x * (float(k) - 1.0f) * 0.25f * f.size, f.pos.y + float(k) * f.size * 0.7f, f.pos.z + r.z * (float(k) - 1.0f) * 0.25f * f.size},
                 s, s * 2.0f, true);
            rlDrawRenderBatchActive();
        }
        EndShaderMode();
        EndBlendMode();
    }
    for (const Fx& f : spec_.fx) {
        if (f.kind == "fire") {
            BeginBlendMode(BLEND_ADDITIVE);
            BeginShaderMode(fire_sh_);
            const float b = fxlive::fire(time_, f.seed);
            for (int k = 0; k < 3; ++k) {   // three tongues, side by side, each its own
                set3(fire_sh_, l_fire_, float(f.seed * 5 + k), b * (k == 1 ? 1.0f : 0.75f));
                const float s = f.size * (k == 1 ? 1.0f : 0.7f);
                card({f.pos.x + r.x * (float(k) - 1.0f) * 0.32f * f.size, f.pos.y, f.pos.z + r.z * (float(k) - 1.0f) * 0.32f * f.size}, s, s * 1.5f, true);
                rlDrawRenderBatchActive();
            }
            EndShaderMode();
            EndBlendMode();
        } else if (f.kind == "strobe") {
            const float s = fxlive::strobe(time_, f.rate, f.seed);
            if (s < 0.02f) continue;
            BeginBlendMode(BLEND_ADDITIVE);
            BeginShaderMode(glow_sh_);
            const float c[3] = {f.color.x, f.color.y, f.color.z};
            SetShaderValue(glow_sh_, l_glow_[0], c, SHADER_UNIFORM_VEC3);
            SetShaderValue(glow_sh_, l_glow_[1], &s, SHADER_UNIFORM_FLOAT);
            card({f.pos.x, f.pos.y, f.pos.z}, 1.1f, 1.1f, false);
            rlDrawRenderBatchActive();
            EndShaderMode();
            EndBlendMode();
        }
    }
    for (size_t i = 0; i < spec_.fx.size() && i < sparks_.size(); ++i) {
        const Fx& f = spec_.fx[i];
        if (f.kind != "sparks") continue;
        BeginBlendMode(BLEND_ADDITIVE);
        rlBegin(RL_QUADS);
        for (const auto& s : sparks_[i].all()) {   // each a streak along its flight, white-hot cooling to red
            if (s.life <= 0) continue;
            const float h = s.heat();
            const Vector3 a = s.p, b = Vector3Subtract(s.p, Vector3Scale(s.v, 0.03f));
            Vector3 side = Vector3CrossProduct(Vector3Subtract(b, a), Vector3Subtract(cp, a));
            const float sl = Vector3Length(side);
            if (sl < 1e-6f) continue;
            side = Vector3Scale(side, 0.006f / sl);
            rlColor4ub(255, static_cast<unsigned char>(120 + 135 * h), static_cast<unsigned char>(40 + 215 * h * h), static_cast<unsigned char>(255 * std::min(1.0f, h * 1.5f)));
            rlVertex3f(a.x - side.x, a.y - side.y, a.z - side.z);
            rlVertex3f(a.x + side.x, a.y + side.y, a.z + side.z);
            rlVertex3f(b.x + side.x, b.y + side.y, b.z + side.z);
            rlVertex3f(b.x - side.x, b.y - side.y, b.z - side.z);
        }
        rlEnd();
        rlDrawRenderBatchActive();
        const float fl = sparks_[i].flash();
        if (fl > 0.02f) {   // the arc itself
            BeginShaderMode(glow_sh_);
            const float c[3] = {0.7f, 0.82f, 1.0f};
            SetShaderValue(glow_sh_, l_glow_[0], c, SHADER_UNIFORM_VEC3);
            SetShaderValue(glow_sh_, l_glow_[1], &fl, SHADER_UNIFORM_FLOAT);
            card({f.pos.x, f.pos.y + 0.1f, f.pos.z}, 0.8f, 0.8f, false);
            rlDrawRenderBatchActive();
            EndShaderMode();
        }
        EndBlendMode();
    }
    rlEnableBackfaceCulling();
    rlEnableDepthMask();
}

}  // namespace dw
