// damned_waters/engine/src/game.hpp
// Purpose: one playable room: pre-rendered plates with depth, fixed camera
// cuts, the survivor (tank or modern controls), one Verdronkene with its brain.
#ifndef DW_GAME_HPP
#define DW_GAME_HPP
#include <raylib.h>
#include <map>
#include <string>
#include "dw/character.hpp"
#include "dw/core.hpp"
#include "dw/room_spec.hpp"

namespace dw {

struct Actor { float x = 0, z = 0, yaw = 0, speed = 0; Pose pose = Pose::Idle; };

class Game {
public:
    static constexpr int W = 1280, H = 720;   // plates are 16:9 at this aspect
    bool init(const std::string& room_id);
    void shutdown();
    void update(float dt);          // input, AI, animation
    void render();                  // scene -> offscreen target
    void present() const;           // post-process to the window + HUD
    int capture_count() const { return 4; }
    std::string stage(int i);       // pose a capture setup; returns its name
    // Studio turnaround of the cast (no room): body and head from several angles -> PNGs in dir.
    void model_sheet(const std::string& dir);
    // One full-resolution studio shot, for close inspection. spec = "who,orbit_deg,elev_deg,dist,target_x,target_y,fovy"
    // (who: survivor | drowned); the camera orbits the point (target_x, target_y, 0).
    bool studio_view(const std::string& spec, const std::string& png);
    bool debug = false;

private:
    void cut_to(const std::string& id);
    void upload_lights();
    void upload_studio_lights();
    void move_player(float dt);
    void update_enemy(float dt);
    void collide(float& x, float& z, float r) const;
    void animate(float dt);

    RoomSpec spec_;
    std::map<std::string, std::pair<Texture2D, Texture2D>> plates_;
    std::string shot_;
    Camera3D cam_{};
    Shader plate_{}, char_{}, blob_{}, post_{};
    Material char_mat_{}, blob_mat_{};
    Mesh blob_mesh_{};
    RenderTexture2D rt_{};
    Character hero_, drowned_;
    Actor player_, enemy_;
    EnemyBrain brain_;
    float health_ = 100, hurt_t_ = 0, time_ = 0, banner_t_ = 3.5f, qt_ = -1, qt_from_ = 0, near_ = 0.01f, far_ = 1000.0f;
    bool tank_ = false;
    Vector3 held_fwd_{0, 0, -1}, held_right_{1, 0, 0};
    Vector2 held_in_{};
    bool holding_ = false;
    int l_cam_ = -1, l_count_ = -1, l_pos_ = -1, l_col_ = -1, l_dir_ = -1, l_top_ = -1, l_bot_ = -1, l_rim_ = -1, l_fog_ = -1, l_fogr_ = -1;
    int l_depth_ = -1, l_near_ = -1, l_far_ = -1, l_dmax_ = -1, l_blob_ = -1, l_time_ = -1, l_res_ = -1;
};

}  // namespace dw
#endif
