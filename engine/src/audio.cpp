// damned_waters/engine/src/audio.cpp
// Purpose: see audio.hpp.
#include "audio.hpp"

#include <raymath.h>
#include <algorithm>
#include <cmath>

namespace dw {
namespace {
constexpr int VOICES = 4;                 // copies of each sound that can play at once
constexpr const char* SKIP[] = {"boss_", "title_", "amb_"};   // not in this demo (the ambience streams instead)
}  // namespace

bool SoundBank::init(const std::string& dir) {
    dir_ = dir;
    if (!IsAudioDeviceReady()) {
        InitAudioDevice();
        owns_device_ = IsAudioDeviceReady();
    }
    ready_ = IsAudioDeviceReady();
    if (!ready_) return false;
    const FilePathList files = LoadDirectoryFilesEx(dir.c_str(), ".wav", false);
    for (unsigned i = 0; i < files.count; ++i) {
        const std::string name = GetFileNameWithoutExt(files.paths[i]);
        if (std::any_of(std::begin(SKIP), std::end(SKIP), [&](const char* s) { return name.rfind(s, 0) == 0; })) continue;
        Voices v;
        v.base = LoadSound(files.paths[i]);
        if (v.base.frameCount == 0) continue;
        for (int k = 0; k < VOICES; ++k) v.alias.push_back(k == 0 ? v.base : LoadSoundAlias(v.base));
        sounds_[name] = std::move(v);
    }
    UnloadDirectoryFiles(files);
    return true;
}

void SoundBank::shutdown() {
    for (auto& [name, v] : sounds_) {
        for (size_t k = 1; k < v.alias.size(); ++k) UnloadSoundAlias(v.alias[k]);
        UnloadSound(v.base);
    }
    sounds_.clear();
    if (amb_.frameCount) UnloadMusicStream(amb_);
    amb_ = {};
    if (owns_device_) CloseAudioDevice();
    ready_ = owns_device_ = false;
}

void SoundBank::play(const std::string& name, float volume, float pitch_jitter) {
    if (!ready_) return;
    auto it = sounds_.find(name);
    if (it == sounds_.end()) return;
    Voices& v = it->second;
    Sound& s = v.alias[v.next];
    v.next = (v.next + 1) % v.alias.size();
    rng_ ^= rng_ << 13; rng_ ^= rng_ >> 17; rng_ ^= rng_ << 5;
    const float r = float(rng_ & 0xFFFF) / 65535.0f * 2 - 1;
    SetSoundVolume(s, std::clamp(volume, 0.0f, 1.0f));
    SetSoundPitch(s, 1.0f + r * pitch_jitter);
    SetSoundPan(s, 0.5f);
    PlaySound(s);
}

void SoundBank::play_at(const std::string& name, Vector3 at, Vector3 ear, Vector3 right, float volume, float pitch_jitter) {
    if (!ready_) return;
    auto it = sounds_.find(name);
    if (it == sounds_.end()) return;
    const Vector3 d = Vector3Subtract(at, ear);
    const float dist = Vector3Length(d);
    const float gain = volume / (1.0f + 0.35f * dist * dist * 0.25f);   // falls off, never to silence in a small house
    const float side = dist > 1e-3f ? Vector3DotProduct(Vector3Scale(d, 1.0f / dist), right) : 0.0f;
    play(name, gain, pitch_jitter);
    Voices& v = it->second;
    const size_t last = (v.next + v.alias.size() - 1) % v.alias.size();
    SetSoundPan(v.alias[last], std::clamp(0.5f - 0.35f * side, 0.1f, 0.9f));   // raylib: 1 = left, 0 = right
}

void SoundBank::ambience(const std::string& name, float volume) {
    if (!ready_ || name == amb_name_) return;
    if (amb_.frameCount) { StopMusicStream(amb_); UnloadMusicStream(amb_); amb_ = {}; }
    amb_name_ = name;
    if (name.empty()) return;
    amb_ = LoadMusicStream((dir_ + "/" + name + ".wav").c_str());
    if (!amb_.frameCount) return;
    amb_.looping = true;
    SetMusicVolume(amb_, volume);
    PlayMusicStream(amb_);
}

void SoundBank::update() {
    if (ready_ && amb_.frameCount) UpdateMusicStream(amb_);
}

}  // namespace dw
