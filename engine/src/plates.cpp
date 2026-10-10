// damned_waters/engine/src/plates.cpp
// Purpose: see plates.hpp. The worker only reads and decodes PNGs (CPU); textures are made on the
// main thread, which owns the OpenGL context.
#include "plates.hpp"

namespace dw {
namespace {
std::string key(const std::string& room, const std::string& shot) { return room + "/" + shot; }
}  // namespace

void PlateStore::start(const std::string& dir) {
    dir_ = dir;
    quit_ = false;
    worker_ = std::thread([this] { work(); });
}

void PlateStore::stop() {
    {
        std::lock_guard<std::mutex> lk(m_);
        quit_ = true;
        jobs_.clear();
    }
    cv_.notify_all();
    if (worker_.joinable()) worker_.join();
    for (auto& d : done_) { UnloadImage(d.color); UnloadImage(d.depth); }
    done_.clear();
    for (auto& [room, shots] : loaded_)
        for (auto& [id, p] : shots) { UnloadTexture(p.first); UnloadTexture(p.second); }
    loaded_.clear();
    queued_.clear();
}

void PlateStore::work() {
    for (;;) {
        Job j;
        {
            std::unique_lock<std::mutex> lk(m_);
            cv_.wait(lk, [this] { return quit_ || !jobs_.empty(); });
            if (quit_) return;
            j = jobs_.front();
            jobs_.pop_front();
        }
        const std::string base = dir_ + "/" + j.room + "/" + j.shot;
        Done d{j.room, j.shot, LoadImage((base + "_color.png").c_str()), LoadImage((base + "_depth.png").c_str())};
        std::lock_guard<std::mutex> lk(m_);
        if (quit_) { UnloadImage(d.color); UnloadImage(d.depth); return; }
        done_.push_back(d);
    }
}

bool PlateStore::upload(const std::string& room, const std::string& shot, Image& c, Image& d) {
    if (c.data == nullptr || d.data == nullptr) {
        TraceLog(LOG_WARNING, "plates: missing %s/%s", room.c_str(), shot.c_str());
        UnloadImage(c);
        UnloadImage(d);
        return false;
    }
    Pair p{LoadTextureFromImage(c), LoadTextureFromImage(d)};
    UnloadImage(c);
    UnloadImage(d);
    SetTextureFilter(p.first, TEXTURE_FILTER_BILINEAR);
    SetTextureFilter(p.second, TEXTURE_FILTER_POINT);   // depth bytes must never be blended
    auto& slot = loaded_[room][shot];
    if (slot.first.id) { UnloadTexture(slot.first); UnloadTexture(slot.second); }
    slot = p;
    return true;
}

void PlateStore::want(const std::string& room, const std::vector<std::string>& shots) {
    {
        std::lock_guard<std::mutex> lk(m_);
        for (const auto& s : shots) {
            if (has(room, s) || queued_.count(key(room, s))) continue;
            queued_.insert(key(room, s));
            jobs_.push_back({room, s});
        }
    }
    cv_.notify_one();
}

bool PlateStore::need(const std::string& room, const std::vector<std::string>& shots) {
    bool ok = true;
    for (const auto& s : shots) {
        if (has(room, s)) continue;
        {   // take it out of the worker's queue if it hasn't started on it (a duplicate later is harmless)
            std::lock_guard<std::mutex> lk(m_);
            for (auto it = jobs_.begin(); it != jobs_.end(); ++it)
                if (it->room == room && it->shot == s) { jobs_.erase(it); break; }
        }
        const std::string base = dir_ + "/" + room + "/" + s;
        Image c = LoadImage((base + "_color.png").c_str()), d = LoadImage((base + "_depth.png").c_str());
        ok = upload(room, s, c, d) && ok;
    }
    return ok;
}

void PlateStore::pump(int budget) {
    for (int i = 0; i < budget; ++i) {
        Done d;
        {
            std::lock_guard<std::mutex> lk(m_);
            if (done_.empty()) return;
            d = done_.front();
            done_.pop_front();
            queued_.erase(key(d.room, d.shot));
        }
        if (has(d.room, d.shot)) { UnloadImage(d.color); UnloadImage(d.depth); continue; }   // loaded on the spot meanwhile
        upload(d.room, d.shot, d.color, d.depth);
    }
}

void PlateStore::keep_only(const std::set<std::string>& keep) {
    for (auto it = loaded_.begin(); it != loaded_.end();) {
        if (keep.count(it->first)) { ++it; continue; }
        for (auto& [id, p] : it->second) { UnloadTexture(p.first); UnloadTexture(p.second); }
        it = loaded_.erase(it);
    }
}

const PlateStore::Pair* PlateStore::get(const std::string& room, const std::string& shot) const {
    const auto r = loaded_.find(room);
    if (r == loaded_.end()) return nullptr;
    const auto s = r->second.find(shot);
    return s == r->second.end() ? nullptr : &s->second;
}

}  // namespace dw
