// damned_waters/engine/src/game_house.cpp
// Purpose: the house around the fight. Every room is loaded at the start and moved to where it lies
// (its "origin"), so the rooms of a storey share one floor plan; he walks from one into the next
// through a doorway and the camera simply cuts to the new room's shot (the next room's plates were
// decoded in the background while he was still next door). Doors are real: he eases one ajar by
// walking gently into it and, leaning on it, looks through the crack (the door's peek shot); a
// push, or running into it, swings it wide; Cross at an open door slams it. The Drowned follow him
// through the house by the doorways, beat on a shut door and shove it open. A change of storey
// (down the cellar stairs) is a short beat in the dark. Rooms remember what was taken, read and
// killed; dying puts him back on the threshold of the room he last walked into.
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <set>

#include "game.hpp"

namespace dw {
namespace {
constexpr float REACH = 0.8f;        // how close to a doorway's line he must be to lean on its door (m)
constexpr float BEAT_ON_DOOR = 1.1f; // how long a Drowned beats on a shut door before it gives (s)
constexpr float RISE_TIME = 1.7f;    // a Drowned coming up out of the water (s)
constexpr float RISE_NEAR = 4.0f;    // how near he must come for it to rise (m)
constexpr float RISE_DEPTH = 1.75f;  // how far under it waits (m)
constexpr float WAKE_DELAY = 1.4f;   // from the bang to them coming in (s)
constexpr int VARIANTS[] = {0, 2, 1};   // who they were: the office worker, Pieter, Sanne

// A door leaf, hinge at the origin, its width along +x, up +y, its thickness across z: a framed
// leaf with two raised panels each side and a brass knob each side near the latch.
Mesh leaf_mesh(float w, float h) {
    MeshData d;
    MeshBuilder b(d);
    const Color wood{62, 39, 24, 255}, panel{54, 33, 20, 255}, brass{182, 142, 66, 255};
    const float t = doors::THICK / 2;
    b.material(MAT_WOOD).color(wood).box({w / 2, h / 2, 0}, {w / 2 - 0.003f, h / 2 - 0.003f, t}, 0.05f, 16, 10);
    for (float side : {-1.0f, 1.0f}) {
        for (const auto& [pv, ph] : {std::pair{0.70f, 0.38f}, std::pair{0.27f, 0.34f}})
            b.color(panel).box({w * 0.5f, h * pv, side * (t + 0.005f)}, {w * 0.34f, h * ph / 2, 0.008f}, 0.2f, 12, 6);
        b.material(MAT_METAL).color(brass);
        b.tube({w - 0.09f, 0.98f, side * t}, {w - 0.09f, 0.98f, side * (t + 0.045f)}, 0.009f, 0.009f, 10);
        b.ellipsoid({w - 0.09f, 0.98f, side * (t + 0.05f)}, {0.027f, 0.027f, 0.022f}, 14, 8);
        b.material(MAT_WOOD).color(wood);
    }
    return upload(d);
}
}  // namespace

int Game::room_index(const std::string& id) const {
    for (size_t i = 0; i < rooms_.size(); ++i)
        if (rooms_[i].id == id) return int(i);
    return -1;
}

std::vector<std::string> Game::shot_ids(const RoomSpec& r) const {
    std::vector<std::string> ids;
    for (const auto& s : r.shots) ids.push_back(s.id);
    for (const auto& i : r.interactables)
        if (!i.peek.id.empty()) ids.push_back(i.peek.id);
    return ids;
}

bool Game::load_house(const std::string& start) {
    rooms_.clear();
    std::vector<std::string> files;
    std::error_code ec;
    for (const auto& e : std::filesystem::directory_iterator(repo_root() + "/game/data/rooms", ec))
        if (e.path().extension() == ".json") files.push_back(e.path().string());
    std::sort(files.begin(), files.end());
    for (const auto& f : files) {
        RoomSpec r = RoomSpec::load(f);
        if (!r.ok()) {
            for (auto& e : r.errors) TraceLog(LOG_ERROR, "RoomSpec %s: %s", f.c_str(), e.c_str());
            continue;
        }
        r.translate(r.origin_x, r.origin_z);   // into the house (no origin: it stays where it's written)
        rooms_.push_back(std::move(r));
    }
    room_ = room_index(start);
    if (room_ < 0) { TraceLog(LOG_ERROR, "no room '%s'", start.c_str()); return false; }
    start_room_ = start;
    doorways_ = house::doorways(rooms_);
    leaves_.clear();
    for (const auto& d : doorways_) {
        leaves_.push_back(doors::hang(d.ax, d.az, d.bx, d.bz, d.nx, d.nz, d.hinge_at_a));
        leaf_meshes_.push_back(d.live ? leaf_mesh(d.width(), d.height) : Mesh{});
    }
    storey_ = rooms_[size_t(room_)].floor;
    return true;
}

void Game::build_storey(int storey) {
    storey_ = storey;
    statics_.clear();
    sight_.clear();
    Rect2 all{1e9f, 1e9f, -1e9f, -1e9f};
    for (const auto& r : rooms_) {
        if (r.floor != storey) continue;
        statics_.insert(statics_.end(), r.colliders.begin(), r.colliders.end());
        sight_.insert(sight_.end(), r.colliders.begin(), r.colliders.begin() + long(r.wall_count));
        all = {std::min(all.x0, r.bounds.x0), std::min(all.z0, r.bounds.z0), std::max(all.x1, r.bounds.x1), std::max(all.z1, r.bounds.z1)};
    }
    fx_.clear();
    fx_.set_bounds(all.x0, all.z0, all.x1, all.z1);
    // Doors: painted shut ones never move; a locked one waits for its key (from either side).
    for (size_t i = 0; i < doorways_.size(); ++i) {
        const auto& d = doorways_[i];
        bool locked = !d.live;
        for (const auto& [r, id] : {std::pair{d.a, d.door_a}, std::pair{d.b, d.door_b}}) {
            if (r < 0 || id.empty()) continue;
            for (const auto& it : rooms_[size_t(r)].interactables)
                if (it.id == id && !it.lock.empty() && !world_.unlocked.count(status::WorldState::key(rooms_[size_t(r)].id, it.id))) locked = true;
        }
        leaves_[i].locked = locked;
    }
    // The Drowned of this storey, as the world remembers them: the dead stay dead, the rest are
    // back where they were waiting.
    for (auto& e : enemies_) e.body.unload();
    enemies_.clear();
    enemies_.reserve(8);
    for (size_t r = 0; r < rooms_.size(); ++r) {
        if (rooms_[r].floor != storey) continue;
        for (const auto& s : rooms_[r].enemies) {
            const std::string k = status::WorldState::key(rooms_[r].id, s.id);
            if (s.kind != "verdronkene" || enemies_.size() >= 8 || world_.dead.count(k)) continue;
            Enemy e;
            e.id = s.id;
            e.key = k;
            e.room = int(r);
            e.variant = VARIANTS[enemies_.size() % 3];
            e.a = {s.pos.x, s.pos.z, s.yaw};
            e.wake_flag = s.requires_flag;
            e.submerged = s.emerge;
            e.active = !e.submerged && (s.requires_flag.empty() || world_.has_flag(s.requires_flag));
            e.gurgle = 2.0f + 3.0f * frand();
            e.body = Character::make(Kind::Drowned, e.variant);
            enemies_.push_back(std::move(e));
        }
    }
    aim_target_ = kick_target_ = -1;
    refresh_loot();
}

void Game::enter_room(int r) {
    room_ = r;
    spec_ = rooms_[size_t(r)];
    if (!world_.visited.count(spec_.id)) {
        world_.visited.insert(spec_.id);
        banner_t_ = 3.5f;   // its name, the first time
    }
    if (spec_.ambience != ambience_) {
        ambience_ = spec_.ambience;
        sfx_.ambience(spec_.ambience, 0.45f);
    }
    plates_.need(spec_.id, shot_ids(spec_));
    peek_ = -1;
    cut_to(select_shot(spec_.zones(), "", player_.x, player_.z));
    upload_lights();
    stream_plates();
    checkpoint();
}

void Game::stream_plates() {
    std::set<std::string> keep{spec_.id};
    for (const auto& d : doorways_) {
        if (d.b < 0 || (d.a != room_ && d.b != room_)) continue;
        const RoomSpec& n = rooms_[size_t(d.a == room_ ? d.b : d.a)];
        keep.insert(n.id);
        plates_.want(n.id, shot_ids(n));
    }
    for (const auto& i : spec_.interactables) {   // the rooms its stairs lead to
        const int t = i.kind == "door" ? room_index(i.target_room) : -1;
        if (t >= 0 && rooms_[size_t(t)].floor != storey_) {
            keep.insert(rooms_[size_t(t)].id);
            plates_.want(rooms_[size_t(t)].id, shot_ids(rooms_[size_t(t)]));
        }
    }
    plates_.keep_only(keep);
}

int Game::resident_rooms() const {
    int n = 0;
    for (const auto& r : rooms_)
        if (!r.shots.empty() && plates_.has(r.id, r.shots.front().id)) ++n;
    return n;
}

int Game::doorway_of(int room, const std::string& door_id) const {
    for (size_t i = 0; i < doorways_.size(); ++i) {
        const auto& d = doorways_[i];
        if ((d.a == room && d.door_a == door_id) || (d.b == room && d.door_b == door_id)) return int(i);
    }
    return -1;
}

// The doors, every frame: they swing, they creak and slam; and the one he's against answers him.
// want: the way the stick points him on the floor (length: how far it's pushed, 0..1).
void Game::update_doors(float dt, Vector2 want, float tilt) {
    for (size_t i = 0; i < leaves_.size(); ++i) {
        const auto& d = doorways_[i];
        if (!d.live || rooms_[size_t(d.a)].floor != storey_) continue;
        const doors::Event ev = leaves_[i].update(dt);
        const Vector3 at{d.mid_x(), 1.2f, d.mid_z()};
        if (ev == doors::Event::Creak) sfx_.play_at("door_open", at, ear(), ear_right(), 0.55f, 0.08f);
        if (ev == doors::Event::Slam) {
            sfx_.play_at("door_bang", at, ear(), ear_right(), 0.7f, 0.05f);
            noise(at.x, at.z, 7.0f);
        }
    }
    const int was_peek = peek_;
    peek_ = -1;
    if (pmode_ == PMode::Normal && tilt > 0.2f) {
        const float wl = std::max(Vector2Length(want), 1e-4f);
        for (size_t i = 0; i < leaves_.size(); ++i) {
            const auto& d = doorways_[i];
            if (!d.live || rooms_[size_t(d.a)].floor != storey_) continue;
            doors::Leaf& L = leaves_[i];
            const float ux = (d.bx - d.ax) / d.width(), uz = (d.bz - d.az) / d.width();
            const float px = player_.x - d.mid_x(), pz = player_.z - d.mid_z();
            const float along = px * ux + pz * uz, across = px * d.nx + pz * d.nz;
            if (std::fabs(along) > d.width() / 2 + 0.05f || std::fabs(across) > REACH) continue;
            const int side = across <= 0 ? 1 : -1;   // +1: he's on room a's side, pushing toward b
            const float into = (want.x * d.nx + want.y * d.nz) / wl * float(side);
            if (into < 0.6f || L.passable()) continue;
            if (L.locked) break;   // (Cross says why)
            if (tilt > 0.85f) {    // running into it: it flies open
                L.push(side);
                break;
            }
            L.ease(side, dt);
            // Braced against it: he stays on his side of the door while he leans (it isn't open).
            constexpr float BRACE = 0.3f;
            if (across * float(side) > -BRACE) {
                const float back = across * float(side) + BRACE;
                player_.x -= d.nx * float(side) * back;
                player_.z -= d.nz * float(side) * back;
                vel_ = {};
            }
            if (std::fabs(L.angle) >= 0.3f) {   // leaning on the crack: the view through it
                const int mine = side > 0 ? d.a : d.b;
                const std::string& door = side > 0 ? d.door_a : d.door_b;
                if (mine >= 0)
                    for (const auto& it : rooms_[size_t(mine)].interactables)
                        if (it.id == door && !it.peek.id.empty()) { peek_ = int(i); peek_room_ = mine; peek_shot_ = it.peek; }
            }
            break;
        }
    }
    if (peek_ != was_peek) {
        if (peek_ >= 0) {
            plates_.need(rooms_[size_t(peek_room_)].id, {peek_shot_.id});
            cam_ = shot_camera(peek_shot_);
        } else {
            cut_to(shot_);
        }
        upload_lights();
    }
    // Through a doorway that leads down (or up) the stairs: the beat between storeys.
    for (size_t i = 0; i < leaves_.size() && !beat_.busy(); ++i) {
        const auto& d = doorways_[i];
        if (!d.live || d.b >= 0 || rooms_[size_t(d.a)].floor != storey_ || !leaves_[i].passable()) continue;
        const float ux = (d.bx - d.ax) / d.width(), uz = (d.bz - d.az) / d.width();
        const float px = player_.x - d.mid_x(), pz = player_.z - d.mid_z();
        if (std::fabs(px * ux + pz * uz) > d.width() / 2 || px * d.nx + pz * d.nz < 0.02f) continue;
        for (const auto& it : rooms_[size_t(d.a)].interactables)
            if (it.id == d.door_a && !it.target_room.empty()) start_beat(it.target_room, it.target_spawn);
    }
}

bool Game::use_door(int room, const Interactable& it) {
    const RoomSpec& r = rooms_[size_t(room)];
    const std::string k = status::WorldState::key(r.id, it.id);
    if (!it.lock.empty() && !world_.unlocked.count(k)) {
        const int key = item_by_key(it.lock.c_str());
        if (key != I_NONE && inv_.has(key)) {
            world_.unlocked.insert(k);
            inv_.remove(key, 1);   // (one door, one key: it has no more use)
            show_text(it.unlock_text.empty() ? "The lock gives." : it.unlock_text);
            sfx_.play("door_open", 0.8f);
            if (const int di = doorway_of(room, it.id); di >= 0) leaves_[size_t(di)].locked = false;
        } else {
            show_text(it.locked_text.empty() ? "It's locked." : it.locked_text);
            sfx_.play("door_locked", 0.8f);
        }
        return true;
    }
    const int di = doorway_of(room, it.id);
    if (di < 0 || !doorways_[size_t(di)].live) {   // no leaf: a flight of stairs (the cellar's way up)
        const int t = room_index(it.target_room);
        if (t >= 0 && rooms_[size_t(t)].floor != storey_) { start_beat(it.target_room, it.target_spawn); return true; }
        if (!it.text.empty()) show_text(it.text);
        return !it.text.empty();
    }
    doors::Leaf& L = leaves_[size_t(di)];
    if (L.locked) { sfx_.play("door_locked", 0.8f); show_text("It won't open."); return true; }
    if (L.passable()) L.shut_it();
    else L.push(L.side_of(player_.x, player_.z));
    return true;
}

void Game::start_beat(const std::string& room, const std::string& spawn) {
    if (room_index(room) < 0) return;
    beat_.start();
    beat_room_ = room;
    beat_spawn_ = spawn;
    vel_ = {};
    peek_ = -1;
    plates_.want(room, shot_ids(rooms_[size_t(room_index(room))]));
}

// In the dark: the other floor goes in, he stands at the foot (or the head) of the stairs.
void Game::finish_beat() {
    const int r = room_index(beat_room_);
    if (r < 0) return;
    const RoomSpec& to = rooms_[size_t(r)];
    const auto sp = to.spawns.find(beat_spawn_);
    const Spawn s = sp != to.spawns.end() ? sp->second : to.spawns.begin()->second;
    player_ = {s.pos.x, s.pos.z, s.yaw};
    holding_ = false;
    if (to.floor != storey_) build_storey(to.floor);
    enter_room(r);
    animate(0.0f);
}

void Game::set_flag(const std::string& flag) {
    if (flag.empty() || !world_.flags.insert(flag).second) return;
    // Whoever was waiting for it: a bang at the door they come through, then they're in.
    Vector3 at{};
    int n = 0;
    for (const auto& e : enemies_)
        if (!e.active && !e.submerged && e.wake_flag == flag) { at = Vector3Add(at, {e.a.x, 1.2f, e.a.z}); ++n; }
    if (n == 0) return;
    at = Vector3Scale(at, 1.0f / float(n));
    sfx_.play_at("door_bang", at, ear(), ear_right(), 1.0f, 0.0f);
    wake_t_ = WAKE_DELAY;
    wake_flag_ = flag;
}

void Game::wake(const std::string& flag) {
    for (auto& e : enemies_) {
        if (e.active || e.submerged || e.wake_flag != flag) continue;
        e.active = true;
        if (std::hypot(e.a.x - player_.x, e.a.z - player_.z) < 1.2f) e.a.x += 1.2f;   // don't land on him
        e.a.yaw = yaw_towards(e.a.x, e.a.z, player_.x, player_.z);
        e.brain.go(EState::Pursuit);   // they heard him: they know where he is
        e.heard_t = 6.0f;
        say(e, "enemy_alert");
    }
}

bool Game::sight_clear(float ax, float az, float bx, float bz) const {
    return !house::crosses(sight_, ax, az, bx, bz) && !house::crosses(shut_, ax, az, bx, bz);
}

// A Drowned on his trail: straight at him in the same room; else to the doorway that leads his
// way: first to a spot before it on its own side, then on through.
void Game::steer_target(const Enemy& e, float& tx, float& tz) const {
    tx = player_.x;
    tz = player_.z;
    if (e.room < 0 || e.room == room_) return;
    const int di = house::next_doorway(doorways_, e.room, room_);
    if (di < 0) return;
    const auto& d = doorways_[size_t(di)];
    const int s = leaves_[size_t(di)].side_of(e.a.x, e.a.z);
    const float fx = d.mid_x() - d.nx * float(s) * 0.55f, fz = d.mid_z() - d.nz * float(s) * 0.55f;
    if (std::hypot(e.a.x - fx, e.a.z - fz) > 0.3f && std::hypot(e.a.x - d.mid_x(), e.a.z - d.mid_z()) > 0.5f) {
        tx = fx;
        tz = fz;
    } else {
        tx = d.mid_x() + d.nx * float(s) * 0.9f;
        tz = d.mid_z() + d.nz * float(s) * 0.9f;
    }
}

// At a shut door on its way: it beats on it for a moment (he hears it), then shoves it open.
void Game::push_on_doors(Enemy& e, float dt) {
    if (e.brain.state != EState::Pursuit || e.room == room_ || e.room < 0) { e.bang_t = 0; return; }
    const int di = house::next_doorway(doorways_, e.room, room_);
    if (di < 0) return;
    doors::Leaf& L = leaves_[size_t(di)];
    const auto& d = doorways_[size_t(di)];
    if (L.passable() || std::hypot(e.a.x - d.mid_x(), e.a.z - d.mid_z()) > 0.95f) { e.bang_t = 0; return; }
    const float before = e.bang_t;
    e.bang_t += dt;
    if (std::floor(before / 0.45f) != std::floor(e.bang_t / 0.45f))
        sfx_.play_at("door_bang", {d.mid_x(), 1.2f, d.mid_z()}, ear(), ear_right(), 0.55f, 0.15f);
    if (e.bang_t >= BEAT_ON_DOOR && !L.locked) {
        L.push(L.side_of(e.a.x, e.a.z));
        e.bang_t = 0;
    }
}

// Under the cellar's water until he comes close (or a shot goes off near it); then it rises.
void Game::update_emerging(Enemy& e, float dt) {
    if (e.submerged) {
        const float d = std::hypot(player_.x - e.a.x, player_.z - e.a.z);
        if ((d < RISE_NEAR && sight_clear(e.a.x, e.a.z, player_.x, player_.z)) || e.heard) {
            e.submerged = false;
            e.active = true;
            e.rise = 0;
            e.a.yaw = yaw_towards(e.a.x, e.a.z, player_.x, player_.z);
            e.brain.go(EState::Alert);
            sfx_.play_at("splash", {e.a.x, 0.3f, e.a.z}, ear(), ear_right(), 1.0f, 0.05f);
            say(e, "enemy_alert", 0.8f);
        }
        return;
    }
    if (e.rise >= 0) {
        e.rise += dt / RISE_TIME;
        if (e.rise >= 1.0f) { e.rise = -1; e.brain.go(EState::Pursuit); }
    }
}

void Game::checkpoint() {
    checkpoint_.inv = inv_;
    checkpoint_.guns[0] = guns_[0];
    checkpoint_.guns[1] = guns_[1];
    checkpoint_.gun = gun_;
    checkpoint_.health = health_;
    checkpoint_.world = world_;
    checkpoint_.notes = notes_;
    checkpoint_.at = player_;
    checkpoint_.room = room_;
    checkpoint_.set = true;
}

// Try again: as he was when he last stepped into a room, on its threshold.
void Game::retry() {
    if (!checkpoint_.set) { reset_fight(); return; }
    const Checkpoint c = checkpoint_;
    reset_fight();   // a clean survivor, the fight's state cleared
    inv_ = c.inv;
    guns_[0] = c.guns[0];
    guns_[1] = c.guns[1];
    gun_ = c.gun;
    hero_.set_weapon(gun_);
    health_ = c.health;
    world_ = c.world;
    notes_ = c.notes;
    player_ = c.at;
    for (auto& l : leaves_) { l.angle = l.target = 0; l.moving = false; }
    build_storey(rooms_[size_t(c.room)].floor);
    enter_room(c.room);
    animate(0.0f);
}

const PlateStore::Pair* Game::current_plate() const {
    if (peek_ >= 0) return plates_.get(rooms_[size_t(peek_room_)].id, peek_shot_.id);
    return plates_.get(spec_.id, shot_);
}

Camera3D Game::shot_camera(const Shot& s) const {
    Camera3D c{};
    c.position = {s.pos.x, s.pos.y, s.pos.z};
    c.target = {s.look_at.x, s.look_at.y, s.look_at.z};
    c.up = {0, 1, 0};
    c.fovy = s.fov;
    c.projection = CAMERA_PERSPECTIVE;
    return c;
}

void Game::draw_leaves() {
    for (size_t i = 0; i < leaves_.size(); ++i) {
        const auto& d = doorways_[i];
        if (!d.live || leaf_meshes_[i].vertexCount == 0 || rooms_[size_t(d.a)].floor != storey_) continue;
        const doors::Leaf& L = leaves_[i];
        const V2 dir = L.dir();
        const Matrix m = MatrixMultiply(MatrixRotateY(std::atan2(-dir.z, dir.x)), MatrixTranslate(L.hx, 0.0f, L.hz));
        DrawMesh(leaf_meshes_[i], char_mat_, m);
    }
}

}  // namespace dw
