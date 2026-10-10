// damned_waters/engine/src/game_world.cpp
// Purpose: the things in the house the survivor can walk up to: pickups lying where the room files
// put them (or where he dropped them to make room), notes, things to look at, doors (whose leaves
// and stairs live in game_house.cpp). Everything on his storey counts, so a thing in the next room
// can be seen glinting through an open door. Interact
// (Cross, when there's nothing to kick) takes the nearest one he's facing: a pickup opens the
// "Take it?" screen, a note opens in the case's Files, anything else says its line at the bottom
// of the screen while time stands still. And what the status screen asks for (status.hpp's
// Commands) is carried out here: equip, use, load from the case, drop, take, leave.
#include <algorithm>
#include <cmath>

#include "cast_items.hpp"
#include "game.hpp"

namespace dw {
namespace {
constexpr float FACING = 0.26f;   // cos 75 degrees: what he's facing, give or take
// How many of `count` the case would take.
int fits(const Inventory& inv, int item, int count) {
    Inventory trial = inv;
    return count - trial.add(item, count);
}
}  // namespace

void Game::reset_world() {
    world_ = {};
    notes_.clear();
    text_queue_.clear();
    status_.close();
    pickup_loot_ = -1;
    notice_.clear();
    refresh_loot();
}

void Game::refresh_loot() {
    loot_.clear();
    for (const auto& r : rooms_) {   // every room on his storey: through an open door, the next room's things show
        if (r.floor != storey_) continue;
        for (const auto& i : r.interactables) {
            if (i.kind != "pickup") continue;
            const int item = item_by_key(i.item.c_str());
            const std::string k = status::WorldState::key(r.id, i.id);
            const int n = world_.remaining(k, i.count);
            if (item != I_NONE && n > 0) loot_.push_back({k, item, n, {i.pos.x, i.pos.y, i.pos.z}, -1});
        }
        for (size_t d = 0; d < world_.dropped.size(); ++d) {
            const auto& dr = world_.dropped[d];
            if (dr.room == r.id && dr.count > 0) loot_.push_back({"", dr.item, dr.count, {dr.x, 0.0f, dr.z}, int(d)});
        }
    }
}

int Game::loot_in_reach() const {
    const V2 f = forward_from_yaw(player_.yaw);
    int best = -1;
    float best_d = 1e9f;
    for (size_t i = 0; i < loot_.size(); ++i) {
        const float dx = loot_[i].pos.x - player_.x, dz = loot_[i].pos.z - player_.z, d = std::hypot(dx, dz);
        if (d > 1.0f || (d > 0.45f && (dx * f.x + dz * f.z) / d < FACING)) continue;
        if (d < best_d) { best_d = d; best = int(i); }
    }
    return best;
}

std::pair<int, int> Game::spot_in_reach() const {
    const V2 f = forward_from_yaw(player_.yaw);
    std::pair<int, int> best{-1, -1};
    float best_d = 1e9f;
    for (size_t r = 0; r < rooms_.size(); ++r) {
        if (rooms_[r].floor != storey_) continue;
        for (size_t i = 0; i < rooms_[r].interactables.size(); ++i) {
            const auto& s = rooms_[r].interactables[i];
            if (s.kind == "pickup") continue;
            const float dx = s.pos.x - player_.x, dz = s.pos.z - player_.z, d = std::hypot(dx, dz);
            if (d > s.radius || (d > 0.45f && (dx * f.x + dz * f.z) / d < FACING)) continue;
            if (!sight_clear(player_.x, player_.z, s.pos.x, s.pos.z)) continue;   // not through a wall or a shut door
            if (d < best_d) { best_d = d; best = {int(r), int(i)}; }
        }
    }
    return best;
}

void Game::show_text(const std::string& text) {
    if (text.empty()) return;
    text_queue_.push_back(text);
    if (text_queue_.size() == 1) text_t_ = 0;
}

bool Game::interact() {
    if (const int l = loot_in_reach(); l >= 0) {
        const Loot& o = loot_[size_t(l)];
        pickup_loot_ = l;
        status_.open_pickup(o.item, o.count, fits(inv_, o.item, o.count));
        sfx_.play("ui_confirm", 0.6f);
        return true;
    }
    const auto [room, s] = spot_in_reach();
    if (room < 0) return false;
    const Interactable& it = rooms_[size_t(room)].interactables[size_t(s)];
    if (it.kind == "note") {
        const std::string k = status::WorldState::key(rooms_[size_t(room)].id, it.id);
        if (!world_.has_note(k)) {
            world_.notes.push_back(k);
            notes_.push_back({k, it.title.empty() ? "A note" : it.title, it.text});
        }
        int at = 0;
        for (size_t n = 0; n < notes_.size(); ++n)
            if (notes_[n].key == k) at = int(n);
        status_.read(at);
        sfx_.play("paper", 0.8f);
        return true;
    }
    if (it.kind == "door") return use_door(room, it);   // unlock, open, shut, or the stairs (game_house.cpp)
    show_text(it.text);   // examine, the typewriter, the water gate
    return !it.text.empty();
}

void Game::apply(const status::Command& c) {
    using status::Command;
    auto item_in = [&](int slot) { return slot >= 0 && slot < int(inv_.slots.size()) ? inv_.slots[size_t(slot)].item : I_NONE; };
    auto gun_of = [](int item) { return item == I_HANDGUN ? 0 : item == I_SHOTGUN ? 1 : -1; };
    switch (c.kind) {
        case Command::Close:
            status_.close();
            sfx_.play("case_close", 0.7f);
            break;
        case Command::Equip:
            if (const int g = gun_of(item_in(c.a)); g >= 0) {
                switch_gun(g);
                notice(std::string("The ") + weapon_spec(Weapon(g)).name + " in hand.");
            }
            break;
        case Command::Use: {
            const int item = item_in(c.a);
            if (!is_medicine(item)) break;
            if (health_ >= MAX_HEALTH) {
                sfx_.play("ui_deny", 0.7f);
                notice("You don't need it now.");
                break;
            }
            health_ = healed(health_, item);
            Slot& s = inv_.slots[size_t(c.a)];
            if (--s.count <= 0) s = {};
            sfx_.play("med_use", 0.9f);
            notice(condition(health_) == Condition::Fine ? "That's better." : "It helps. Some.");
            break;
        }
        case Command::Load: {
            const int a = item_in(c.a), b = item_in(c.b);
            const int g = gun_of(a) >= 0 ? gun_of(a) : gun_of(b);
            if (g < 0) break;
            const int n = status::load_from_case(inv_, guns_[g]);
            if (n <= 0) {
                sfx_.play("ui_deny", 0.7f);
                notice(guns_[g].mag >= guns_[g].spec().mag ? "It's already full." : "No rounds to spare.");
                break;
            }
            if (g == 0) { slide_locked_ = false; if (gun_ == 0) hero_.slide = 0; }   // a full magazine, the slide home
            sfx_.play(g == 0 ? "mag_in" : "shell_insert", 0.9f);
            notice(TextFormat("Loaded %d into the %s.", n, weapon_spec(Weapon(g)).name));
            break;
        }
        case Command::Discard: {
            Slot& s = inv_.slots[size_t(c.a)];
            if (!status::can_discard(s.item)) break;
            const float ang = frand() * 2 * kPi;   // at his feet
            world_.dropped.push_back({spec_.id, s.item, s.count, player_.x + 0.3f * std::cos(ang), player_.z + 0.3f * std::sin(ang)});
            notice(std::string(item_spec(s.item).name) + " left on the floor.");
            s = {};
            sfx_.play("ui_confirm", 0.5f);
            // Making room for something: keep the pickup the screen asks about pointing at it.
            const Loot was = pickup_loot_ >= 0 ? loot_[size_t(pickup_loot_)] : Loot{};
            refresh_loot();
            if (pickup_loot_ >= 0) {
                for (size_t i = 0; i < loot_.size(); ++i)
                    if (loot_[i].key == was.key && loot_[i].dropped == was.dropped) pickup_loot_ = int(i);
                status_.pickup_fits(fits(inv_, was.item, was.count));
            }
            break;
        }
        case Command::Take: {
            if (pickup_loot_ < 0) break;
            const Loot o = loot_[size_t(pickup_loot_)];
            const int left = inv_.add(o.item, o.count), took = o.count - left;
            if (o.dropped >= 0) world_.dropped[size_t(o.dropped)].count = left;
            else world_.set_remaining(o.key, left);
            sfx_.play("pickup", 0.7f);
            notice(left > 0 ? TextFormat("Took %d. %d left: no more room.", took, left) : "");
            status_.close();
            pickup_loot_ = -1;
            refresh_loot();
            for (const auto& r : rooms_)   // what happens as he takes it (the key on the mantel: a bang at the front door)
                for (const auto& i : r.interactables)
                    if (status::WorldState::key(r.id, i.id) == o.key) {
                        if (!i.then_text.empty()) show_text(i.then_text);
                        set_flag(i.sets_flag);
                    }
            break;
        }
        case Command::Leave:
            status_.close();
            pickup_loot_ = -1;
            break;
        default: break;
    }
}

// What lies in the room: each model at its spot (guns and the key laid down flat, the rest
// standing as they stand), and a glint that catches the eye now and then, the way the classics
// mark a pickup without a HUD.
void Game::draw_loot() {
    for (const Loot& o : loot_) {
        if (item_mesh_[o.item].vertexCount == 0) continue;
        const bool flat = o.item == I_HANDGUN || o.item == I_SHOTGUN || o.item == I_CELLAR_KEY;
        const unsigned h = unsigned(std::hash<std::string>{}(o.key + std::to_string(o.dropped)));
        const float yaw = float(h % 360) * DEG2RAD;
        const Vector3 c = item_centre_[o.item];
        Matrix m = MatrixTranslate(-c.x, -c.y, -c.z);
        if (flat) m = MatrixMultiply(m, MatrixRotateX(-PI / 2));   // its side up
        m = MatrixMultiply(m, MatrixRotateY(yaw));
        const float lift = flat ? 0.015f : -item_base_[o.item];   // its underside on the surface
        m = MatrixMultiply(m, MatrixTranslate(o.pos.x, o.pos.y + lift, o.pos.z));
        DrawMesh(item_mesh_[o.item], char_mat_, m);
    }
}

void Game::draw_text_box() const {
    if (text_queue_.empty()) return;
    const float sw = float(GetScreenWidth()), sh = float(GetScreenHeight()), k = sh / float(H);
    const std::string& t = text_queue_.front();
    const size_t shown = std::min(t.size(), size_t(text_t_ * 55.0f));   // it types itself out
    DrawRectangleGradientV(0, int(sh - 190 * k), int(sw), int(190 * k), Color{0, 0, 0, 0}, Color{0, 0, 0, 220});
    const float size = 27 * k, width = 980 * k;
    float y = sh - 150 * k;
    std::string line, word;
    auto flush = [&] {
        DrawTextEx(f_body_, line.c_str(), {(sw - width) / 2, y}, size, 0, Color{226, 216, 196, 255});
        y += size * 1.2f;
        line.clear();
    };
    const std::string vis = t.substr(0, shown);
    for (size_t i = 0; i <= vis.size(); ++i) {   // wrapped to the box, line breaks kept
        const char ch = i < vis.size() ? vis[i] : '\0';
        if (ch == ' ' || ch == '\n' || ch == '\0') {
            const std::string tryline = line.empty() ? word : line + " " + word;
            if (MeasureTextEx(f_body_, tryline.c_str(), size, 0).x > width && !line.empty()) { flush(); line = word; }
            else line = tryline;
            word.clear();
            if (ch == '\n') flush();
        } else {
            word += ch;
        }
    }
    if (!line.empty()) flush();
    if (shown >= t.size() && std::fmod(ui_t_, 1.0f) < 0.7f)   // read it: press on
        DrawPoly({(sw + width) / 2, sh - 46 * k}, 3, 8 * k, 90, Color{170, 24, 18, 255});
}

// The glint on each pickup: a small star that flares for a moment every couple of seconds, each
// on its own beat, where the item lies (only the camera's view: a fixed shot, so it's honest).
void Game::draw_glints() const {
    const float k = float(GetScreenHeight()) / float(H);
    for (const Loot& o : loot_) {
        const unsigned h = unsigned(std::hash<std::string>{}(o.key + std::to_string(o.dropped)));
        const float phase = std::fmod(time_ * 0.45f + float(h % 100) / 100.0f, 1.0f);
        const float a = phase < 0.12f ? std::sin(phase / 0.12f * PI) : 0.0f;
        if (a <= 0.01f) continue;
        // (a glint is drawn over the picture: only where the camera could see the thing, not
        // through a wall from the next room)
        if (!sight_clear(cam_.position.x, cam_.position.z, o.pos.x, o.pos.z)) continue;
        const Vector3 at{o.pos.x, o.pos.y + 0.05f, o.pos.z};
        const Vector3 to_cam = Vector3Subtract(cam_.position, at);
        if (Vector3DotProduct(to_cam, Vector3Subtract(cam_.target, cam_.position)) > 0) continue;   // behind the camera
        const Vector2 p = GetWorldToScreenEx(at, cam_, W, H);
        const Vector2 s{p.x * k * float(GetScreenWidth()) / (float(W) * k), p.y * k};
        const float r = (6 + 10 * a) * k;
        const Color c{255, 236, 190, static_cast<unsigned char>(220 * a)};
        DrawLineEx({s.x - r, s.y}, {s.x + r, s.y}, 2 * k, c);
        DrawLineEx({s.x, s.y - r * 1.4f}, {s.x, s.y + r * 1.4f}, 2 * k, c);
        DrawCircleV(s, 3 * k * a, Color{255, 250, 235, static_cast<unsigned char>(255 * a)});
    }
}

}  // namespace dw
