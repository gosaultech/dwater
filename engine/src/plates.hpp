// damned_waters/engine/src/plates.hpp
// Purpose: the painted plates (colour + depth per camera shot) of the rooms around him, kept ready
// on the GPU. With seamless doors the next room's picture must already be there the moment he
// steps through, so the rooms next door are decoded on a worker thread in the background and
// uploaded a couple per frame; rooms out of reach are let go. If he outruns it, the plate is
// loaded on the spot (a hitch, never a missing picture).
//
// ELI5: a stage crew that sets up the next scene's backdrops in the wings while the current scene
// plays, and strikes the ones nobody will need.
#ifndef DW_PLATES_HPP
#define DW_PLATES_HPP
#include <raylib.h>

#include <condition_variable>
#include <deque>
#include <map>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <utility>
#include <vector>

namespace dw {

class PlateStore {
public:
    using Pair = std::pair<Texture2D, Texture2D>;   // colour, depth
    // dir: game/assets/rooms
    void start(const std::string& dir);
    void stop();
    // Decode this room's shots in the background (no-op if they're loaded or on their way).
    void want(const std::string& room, const std::vector<std::string>& shots);
    // Load this room's shots now if they aren't (blocking): the room he's standing in.
    bool need(const std::string& room, const std::vector<std::string>& shots);
    // Upload what the worker has decoded: at most `budget` plates this frame.
    void pump(int budget = 2);
    // Let go of every room not in `keep`.
    void keep_only(const std::set<std::string>& keep);
    const Pair* get(const std::string& room, const std::string& shot) const;
    bool has(const std::string& room, const std::string& shot) const { return get(room, shot) != nullptr; }

private:
    struct Job { std::string room, shot; };
    struct Done { std::string room, shot; Image color{}, depth{}; };
    void work();
    bool upload(const std::string& room, const std::string& shot, Image& c, Image& d);
    std::string dir_;
    std::map<std::string, std::map<std::string, Pair>> loaded_;
    std::set<std::string> queued_;           // "room/shot" sent to the worker and not yet uploaded
    std::deque<Job> jobs_;
    std::deque<Done> done_;
    std::mutex m_;
    std::condition_variable cv_;
    std::thread worker_;
    bool quit_ = false;
};

}  // namespace dw
#endif
