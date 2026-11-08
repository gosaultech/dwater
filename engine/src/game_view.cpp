// damned_waters/engine/src/game_view.cpp
// Purpose: the game's side of the following view (dw/framing.hpp): him, what he aims at, what's on
// him and the pickup near him, as the shot's camera sees them; the zoom each shot starts from (his
// typical size in it, measured once over the floor it covers); and the moments it pushes in.
#include <algorithm>
#include <cmath>

#include "game.hpp"

namespace dw {

namespace {
constexpr float THREAT = 2.6f;      // m: a Drowned this close is in the picture with him
constexpr float ITEM_NEAR = 2.2f;   // m: a pickup this close is in the picture with him
constexpr float SAMPLE = 0.5f;      // m: the floor grid a shot's typical size is measured on
}  // namespace

framing::Lens Game::lens() const { return framing::Lens::from(cam_.position, cam_.target, cam_.fovy, float(W) / float(H)); }

float Game::shot_zoom(const std::string& id) {
    if (shot_zoom_.size() != rooms_.size()) shot_zoom_.assign(rooms_.size(), {});
    auto& zs = shot_zoom_[size_t(room_)];
    if (zs.size() != spec_.shots.size()) zs.assign(spec_.shots.size(), -1.0f);
    for (size_t i = 0; i < spec_.shots.size(); ++i) {
        const Shot& s = spec_.shots[i];
        if (s.id != id) continue;
        if (zs[i] > 0) return zs[i];
        // His height in the picture wherever he can stand in the shot's zone; the middle of those.
        const framing::Lens L = framing::Lens::from({s.pos.x, s.pos.y, s.pos.z}, {s.look_at.x, s.look_at.y, s.look_at.z}, s.fov, float(W) / float(H));
        near_solid_.clear();   // (only the solids round the zone: a storey of the city has thousands)
        for (const Obb2& b : solid_) {
            const float rad = std::hypot(b.hx, b.hz) + 0.3f;
            if (b.cx + rad >= s.zone.x0 && b.cx - rad <= s.zone.x1 && b.cz + rad >= s.zone.z0 && b.cz - rad <= s.zone.z1) near_solid_.push_back(b);
        }
        zoom_scratch_.clear();
        for (float x = s.zone.x0 + SAMPLE * 0.5f; x < s.zone.x1; x += SAMPLE)
            for (float z = s.zone.z0 + SAMPLE * 0.5f; z < s.zone.z1; z += SAMPLE) {
                bool free = true;
                for (const Obb2& b : near_solid_) {
                    float px = x, pz = z;
                    if (resolve_circle_obb(px, pz, 0.3f, b)) { free = false; break; }   // (in something: he can't stand there)
                }
                if (!free) continue;
                const Vector3 f = L.project({x, 0.05f, z}), h = L.project({x, 1.82f, z});
                if (f.z > 0.3f && h.z > 0.3f) zoom_scratch_.push_back(f.y - h.y);
            }
        float median = 0;
        if (!zoom_scratch_.empty()) {
            auto mid = zoom_scratch_.begin() + std::ptrdiff_t(zoom_scratch_.size() / 2);
            std::nth_element(zoom_scratch_.begin(), mid, zoom_scratch_.end());
            median = *mid;
        }
        return zs[i] = framing::base_zoom(median);
    }
    return 1.0f;   // (a shot not in this room: the whole picture)
}

void Game::update_view(float dt) {
    if (peek_ >= 0 || title_) {   // through the crack (his eye at the door), or no picture: the whole of it
        win_ = {};
        view_cut_ = true;
        return;
    }
    const framing::Lens L = lens();
    // Him: his feet, the top of his head over them (crouching, lying, as he is now), and which way
    // he faces across the picture.
    framing::Subject s;
    const float top = std::max(hero_.head_point().y + 0.12f, 0.35f);
    const Vector3 feet = L.project({player_.x, 0.05f, player_.z}), head = L.project({player_.x, top, player_.z});
    s.seen = feet.z > 0.3f && head.z > 0.3f;
    s.feet = {feet.x, feet.y};
    s.head = {head.x, head.y};
    {
        const V2 fw = forward_from_yaw(player_.yaw);
        const Vector3 a = L.project({player_.x + fw.x, 0.9f, player_.z + fw.z}), b = L.project({player_.x, 0.9f, player_.z});
        const float dx = a.x - b.x, dy = a.y - b.y;
        s.lead = dx / (std::sqrt(dx * dx + dy * dy) + 1e-5f);
    }
    // Behind something in the painting (the field hospital's tent, a bus, a generator): his chest,
    // the top of his head and both shoulders all behind what's painted there. (dw/framing.hpp opens
    // the window wide if it lasts.)
    if (s.seen && pmode_ != PMode::Dead) {
        int n = 0, behind = 0;
        const Vector3 pts[4] = {{player_.x, 1.3f, player_.z}, {player_.x, top - 0.12f, player_.z},
                                {player_.x + L.r.x * 0.22f, 1.35f, player_.z + L.r.z * 0.22f},
                                {player_.x - L.r.x * 0.22f, 1.35f, player_.z - L.r.z * 0.22f}};
        for (const Vector3& at : pts) {
            const Vector3 q = L.project(at);
            if (q.z <= 0.3f || q.x < 0 || q.x > 1 || q.y < 0 || q.y > 1) continue;
            const float d = plates_.depth_at(spec_.id, shot_, q.x, q.y);
            if (d < 0) continue;
            ++n;
            if (d < q.z - 0.25f) ++behind;
        }
        s.hidden = n >= 3 && behind == n;
    }
    // With him: what he aims at, anything on him, the pickup near him (if the camera can see it).
    framing::Extra also;
    auto hold_body = [&](float x, float z) {
        const Vector3 f = L.project({x, 0.05f, z}), h = L.project({x, 1.8f, z});
        if (f.z <= 0.3f || h.z <= 0.3f) return;
        const float half = 0.2f * (f.y - h.y);
        also.add({f.x - half, h.y}, {f.x + half, f.y});
    };
    for (size_t i = 0; i < enemies_.size(); ++i) {
        const Enemy& e = enemies_[i];
        if (!e.active) continue;
        const bool aimed = pmode_ == PMode::Aim && int(i) == aim_target_;
        if (aimed || (std::hypot(e.a.x - player_.x, e.a.z - player_.z) < THREAT && sight_clear(player_.x, player_.z, e.a.x, e.a.z)))
            hold_body(e.a.x, e.a.z);
    }
    int near = -1;
    float best = ITEM_NEAR;
    for (size_t i = 0; i < loot_.size(); ++i) {
        const float d = std::hypot(loot_[i].pos.x - player_.x, loot_[i].pos.z - player_.z);
        if (d < best && sight_clear(cam_.position.x, cam_.position.z, loot_[i].pos.x, loot_[i].pos.z)) { best = d; near = int(i); }
    }
    if (near >= 0) {
        const Vector3 p = loot_[size_t(near)].pos;
        const Vector3 a = L.project({p.x - 0.2f, p.y + 0.25f, p.z}), b = L.project({p.x + 0.2f, std::max(p.y - 0.1f, 0.0f), p.z});
        if (a.z > 0.3f && b.z > 0.3f) also.add({a.x, a.y}, {b.x, b.y});
    }
    // In closer: a little, facing a pickup in reach; at once, for a blow; slowly, as he dies.
    item_push_ += ((loot_in_reach() >= 0 ? 1.12f : 1.0f) - item_push_) * smoothing(3.0f, dt);
    float push = item_push_;
    if (pmode_ == PMode::Hurt) push *= 1.0f + 0.09f * (pmode_t_ < 0.05f ? pmode_t_ / 0.05f : std::exp(-(pmode_t_ - 0.05f) / 0.3f));
    if (pmode_ == PMode::Dead) {
        const float k = std::min(1.0f, dead_t_ / 3.0f);
        push *= 1.0f + 0.7f * k * k * (3 - 2 * k);
    }
    if (view_cut_) {
        view_.cut(s, also, shot_zoom(shot_), view_establish_);
        view_cut_ = view_establish_ = false;
        win_ = view_.update(s, also, push, 0);
        return;
    }
    win_ = view_.update(s, also, push, dt);
}

}  // namespace dw
