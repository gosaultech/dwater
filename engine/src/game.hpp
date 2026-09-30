// damned_waters/engine/src/game.hpp
// Purpose: one playable room: pre-rendered plates with depth, fixed camera cuts, the survivor and
// the Drowned. Controller-first (input.hpp: Type A/B/C layouts, keyboard and mouse alongside).
// Survival-horror combat with skill in it (game_combat.cpp): lock-on aim with the right stick as a
// cursor over the body, the M92FS and the Remington 870, a counter kick and a perfect dodge;
// RE2-Remake-style gore; no HUD (the survivor's limp tells you how hurt he is); a pause menu with
// the options. The hall's script: one Drowned, then a bang at the front door and two more.
#ifndef DW_GAME_HPP
#define DW_GAME_HPP
#include <raylib.h>
#include <initializer_list>
#include <map>
#include <string>
#include <vector>
#include "audio.hpp"
#include "dw/character.hpp"
#include "dw/combat.hpp"
#include "dw/controls.hpp"
#include "dw/core.hpp"
#include "dw/room_spec.hpp"
#include "dw/settings.hpp"
#include "effects.hpp"
#include "input.hpp"

namespace dw {

struct Actor { float x = 0, z = 0, yaw = 0, speed = 0; Pose pose = Pose::Idle; };

// One Drowned: its body, where it is, its mind and what's been shot off it.
struct Enemy {
    std::string id;
    int variant = 0;
    Character body;
    Actor a;
    EnemyBrain brain;
    BodyDamage damage;
    bool active = false;          // in the room (the second wave waits behind the front door)
    float gurgle = 3, dead_t = 0, push_x = 0, push_z = 0, step = 0;
    float stumble = 0;            // overbalanced by a perfect dodge: its lunge still carrying it on
    float speed = 0.85f, turn = 2.2f, reach = 1.7f, bite = 20;     // m/s, rad/s, m, and what a lunge takes off him
    bool pooled = false;          // blood has started spreading under it
    bool heard = false;           // a noise reached it this frame (a shot, a footstep)
    bool crawling = false;        // lost a leg: down on the floor for good
};

// The survivor's fighting state.
enum class PMode { Normal, Aim, QuickTurn, Dodge, Kick, Hurt, Dead };

class Game {
public:
    static constexpr int W = 1280, H = 720;   // plates are 16:9 at this aspect
    bool init(const std::string& room_id);
    void shutdown();
    void update(float dt);          // input, AI, animation
    void render();                  // scene -> offscreen target
    void present() const;           // post-process to the window + HUD
    int capture_count() const { return 13; }
    std::string stage(int i);       // pose a capture setup; returns its name
    // Studio turnaround of the cast (no room): body and head from several angles -> PNGs in dir.
    // only: a comma-separated list of subjects to render (empty: all).
    void model_sheet(const std::string& dir, const std::string& only = "");
    // One full-resolution studio shot, for close inspection. spec = "who,orbit_deg,elev_deg,dist,target_x,target_y,fovy"
    // (who: survivor | drowned[N], optionally @head, @chest or @pelvis); the camera orbits the point
    // (target_x, target_y, 0), or that joint offset by (target_x, target_y).
    bool studio_view(const std::string& spec, const std::string& png);
    // who: m92fs | r870, a gun on its own, side-on and catalogue-lit; opts: /slide=1 (worked back),
    // /roll=deg, /bg=dark, /synthetic (the 870 in black synthetic), /obj=stem (write the meshes out)
    bool gun_view(const std::string& who, const std::string& opts, float orbit, float elev, float dist, float tx, float ty,
                  float fovy, const std::string& png);
    bool debug = false;
    bool flashlight = false;   // L1 / L: the flashlight on his strap (a spot on the characters and on the painted room)
    std::string settings_path; // the SQLite database the options live in (set before init)
    bool quit_requested() const { return quit_; }
    // What happened in the fight, for the telemetry database.
    struct Stats {
        int shots = 0, hits = 0, kills = 0, limbs = 0, heads = 0, kicks = 0, counters = 0, dodges = 0, perfect_dodges = 0, deaths = 0;
        float damage_taken = 0;
    };
    const Stats& stats() const { return stats_; }

private:
    // Real shadows from up to two lights at a time: each light gets a depth map of the characters
    // seen from it; the character shader reads it for self-shadowing, the plate shader for shadows
    // cast onto the painted room. The muzzle flash and the flashlight (lights the painting never
    // saw) come first while they're on; then the room's lamps that light the characters most.
    struct ShadowMap {
        RenderTexture2D rt{};           // depth only
        Matrix vp = MatrixIdentity();   // world -> the light's clip space
        int light = -1;                 // index into the light arrays, -1 = unused this frame
        int dyn = -1;                   // which light the painting never saw (0 flash, 1 flashlight), -1: a room lamp
    };
    static constexpr int SHADOW_RES = 1024;
    void init_shadows();
    // casters: everyone, for the room's lamps; gun_lit: the Drowned, for the flash and the
    // flashlight (they sit on the survivor, so they don't shadow him).
    void render_shadows(const std::vector<const Character*>& casters, const std::vector<const Character*>& gun_lit = {});
    void shadow_pass(int k, const Camera3D& from, double near_d, double far_d, const std::vector<const Character*>& casters);
    void bind_shadows();                // shadow uniforms for the character and plate shaders

    void cut_to(const std::string& id);
    void upload_lights();
    void upload_studio_lights();
    void set_lights(const Vector4* pos, const Vector4* col, const Vector4* dir, int n);   // uploads and remembers them
    void move_player(float dt, Vector2 in, float speed_scale);   // walking and running
    void collide(float& x, float& z, float r) const;
    void animate(float dt);
    // Combat (game_combat.cpp).
    void reset_fight();                          // a fresh start: full health, guns loaded, the first Drowned waiting
    void update_player(float dt);
    void update_enemies(float dt);
    void enter_aim();
    void aim(float dt);
    void switch_target(int dir);                 // a flick (or the wheel): the next Drowned that way on screen
    void fire();
    void reload();
    void switch_gun(int g);
    void load_shell(bool first_into_empty);      // the 870: one shell went into the tube
    void work_actions(float dt);                 // the 870's pump and the M92FS's slide, and the brass they throw
    bool common_actions();                       // dodge, reload, weapon buttons: true if a dodge took over
    void start_dodge(Vector2 in);
    bool try_kick();                             // what's in front of him: a counter, a kick, or a whiff
    void perfect_dodge_on(Enemy& e);
    int kickable() const;
    void hurt_player(float dmg, float from_x, float from_z);
    void cut_off(Enemy& e, int region, Vector3 dir);   // a part of it comes away: the piece falls, blood
    float wall_hit(Vector3 from, Vector3 dir, float range) const;   // how far a shot flies before a wall (or range)
    void noise(float x, float z, float radius);   // every Drowned in earshot hears it
    void set_pmode(PMode m) { pmode_ = m; pmode_t_ = 0; }
    bool aim_held() const;
    bool fire_pressed() const;
    Vector3 aim_point(const Enemy& e) const;     // where on the target the gun points (W: the head, S: a leg)
    Vector3 shot_dir() const;                    // the way a shot flies (before any spread)
    void kill_enemy(Enemy& e);
    void become_crawler(Enemy& e);
    Vector3 ear() const { return {player_.x, 1.6f, player_.z}; }
    Vector3 ear_right() const;                   // the screen's right: sounds pan the way the camera sees them
    void say(const Enemy& e, const char* sound, float volume = 1.0f);   // a sound from a Drowned
    float frand() { rng_ ^= rng_ << 13; rng_ ^= rng_ >> 17; rng_ ^= rng_ << 5; return float(rng_ & 0xFFFFFF) / 16777215.0f; }

    // The pause menu (time stands still) with the options, saved to the database.
    void update_menu();
    void draw_menu() const;
    void save_settings() const { if (!settings_path.empty()) settings_.save(settings_path); }

    RoomSpec spec_;
    Input input_;
    InputFrame in_;                              // this frame's actions (polled once in update)
    Settings settings_;
    bool paused_ = false, quit_ = false;
    int menu_sel_ = 0;
    std::map<std::string, std::pair<Texture2D, Texture2D>> plates_;
    std::string shot_;
    Camera3D cam_{};
    Shader plate_{}, char_{}, blob_{}, post_{};
    Material char_mat_{}, blob_mat_{};
    Mesh blob_mesh_{};
    RenderTexture2D rt_{};
    Character hero_;
    Actor player_;
    std::vector<Enemy> enemies_;
    HallEncounter script_;
    SoundBank sfx_;
    Effects fx_;
    // The survivor in a fight.
    PMode pmode_ = PMode::Normal;
    float pmode_t_ = 0, invuln_ = 0, dodge_cd_ = 0, aim_pitch_ = 0, aim_snap_ = 0, dead_t_ = 0;
    Vector2 vel_{};                              // his velocity on the floor (m/s): gets up to speed in a few frames
    Vector2 aim_look_{};                         // the aim cursor over the target's body (-1..1; controls.hpp body_aim)
    FlickDetector flick_;
    float focus_t_ = 0;                          // after a perfect dodge: the next shot does double
    float slowmo_t_ = 0, time_scale_ = 1;        // the slow-motion beat after a perfect dodge (an option)
    Vector3 dodge_dir_{}, knock_{};              // the dodge's direction; being knocked back (m/s)
    int aim_target_ = -1, kick_target_ = -1, gun_ = 0;
    bool kick_done_ = false, kick_counter_ = false;
    Firearm guns_[2];
    Inventory inv_;
    float step_accum_ = 0;
    float pump_t_ = -1;                          // the 870: time since the pump began (-1: at rest)
    bool pump_eject_ = false;                    // ... and whether it throws out a spent hull (not when racking a fresh load)
    float slide_t_ = -1;                         // the M92FS: time since the slide last cycled (-1: at rest)
    unsigned rng_ = 0x9E3779B9u;
    Stats stats_;
    bool staged_aim_ = false;                    // capture setups hold the aim and the stick from code
    Vector2 staged_in_{};
    std::vector<const Character*> casters_, gun_lit_;   // who casts shadows this frame (kept: no allocation per frame)
    float health_ = 100, time_ = 0, banner_t_ = 3.5f, qt_ = -1, qt_from_ = 0, near_ = 0.01f, far_ = 1000.0f;
    int static_lights_ = 0;                      // room lights; the flash and the flashlight come after them
    int flash_light_ = -1, lamp_light_ = -1;     // where the flash and the flashlight sit in the light arrays (-1: off)
    int l_dynPos_ = -1, l_dynCol_ = -1, l_dynDir_ = -1, l_pDynSh_ = -1;
    Vector3 held_fwd_{0, 0, -1}, held_right_{1, 0, 0};
    Vector2 held_in_{};
    bool holding_ = false;
    int l_cam_ = -1, l_count_ = -1, l_pos_ = -1, l_col_ = -1, l_dir_ = -1, l_top_ = -1, l_bot_ = -1, l_rim_ = -1, l_fog_ = -1, l_fogr_ = -1;
    int l_env_top_ = -1, l_env_bot_ = -1, l_softbox_ = -1;
    int l_depth_ = -1, l_near_ = -1, l_far_ = -1, l_dmax_ = -1, l_blob_ = -1, l_time_ = -1, l_res_ = -1;
    ShadowMap shadows_[2];
    Vector4 light_pos_[8]{}, light_col_[8]{}, light_dir_[8]{};
    int light_n_ = 0;
    int l_depthOnly_ = -1, l_shVP_[2]{-1, -1}, l_shLight_ = -1;                              // character shader
    int l_pInvView_ = -1, l_pTan_ = -1, l_pSh0_ = -1, l_pSh1_ = -1, l_pShVP_[2]{-1, -1}, l_pShL_ = -1;   // plate shader
};

}  // namespace dw
#endif
