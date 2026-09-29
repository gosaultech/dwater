// damned_waters/engine/src/audio.hpp
// Purpose: every sound in the game, the C++ counterpart of the Godot demo's AudioDirector.
//  * Each WAV in game/assets/audio is loaded once at start: playing a sound never touches disk.
//  * Each sound gets a few voices (raylib sound aliases), so four quick shots don't cut each
//    other off; a little random pitch keeps repeats from sounding machine-made.
//  * Positional one-shots: louder when close, panned left or right of the listener.
//  * The room's ambience loops underneath.
// If there is no audio device (a headless test run), everything quietly does nothing.
#ifndef DW_AUDIO_HPP
#define DW_AUDIO_HPP
#include <raylib.h>
#include <map>
#include <string>
#include <vector>

namespace dw {

class SoundBank {
public:
    bool init(const std::string& dir);   // loads every .wav in dir; false if there's no audio device
    void shutdown();
    // Play by name (the file's stem). volume 0..1; pitch_jitter: +- fraction.
    void play(const std::string& name, float volume = 1.0f, float pitch_jitter = 0.0f);
    // Play from a point in the room, heard by a listener at `ear` whose right-hand side is `right`.
    void play_at(const std::string& name, Vector3 at, Vector3 ear, Vector3 right, float volume = 1.0f, float pitch_jitter = 0.05f);
    void ambience(const std::string& name, float volume = 0.5f);   // loop it (empty: stop)
    void update();   // keep the ambience stream fed; call once a frame
    bool ready() const { return ready_; }

private:
    struct Voices { Sound base{}; std::vector<Sound> alias; size_t next = 0; };
    std::map<std::string, Voices> sounds_;
    std::string dir_;
    Music amb_{};
    std::string amb_name_;
    bool ready_ = false, owns_device_ = false;
    unsigned rng_ = 0x2468ACE1u;
};

}  // namespace dw
#endif
