// damned_waters/engine/src/game.hpp
// Purpose: the house, room by room: pre-rendered plates with depth, fixed camera cuts, the survivor
// and the Drowned. Rooms on a storey share one floor plan (house.hpp): he walks from one into the
// next through doors he pushes open (doors.hpp), no loading screen; a change of storey is a short
// beat in the dark (transition.hpp). Controller-first (input.hpp: Type A/B/C layouts, keyboard and mouse alongside).
// Survival-horror combat with skill in it (game_combat.cpp): lock-on aim with the right stick as a
// cursor over the body, the M92FS and the Remington 870, a counter kick and a perfect dodge;
// RE2-Remake-style gore; no HUD (the survivor's limp tells you how hurt he is); a pause menu with
// the options. The story moves on flags: taking the cellar key brings a bang at the front door
// and two more Drowned into the hall.
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
#include "dw/doors.hpp"
#include "dw/house.hpp"
#include "dw/room_spec.hpp"
#include "dw/settings.hpp"
#include "dw/status.hpp"
#include "dw/transition.hpp"
#include "dw/world_map.hpp"
#include "effects.hpp"
#include "input.hpp"
#include "plates.hpp"

namespace dw {

struct Actor { float x = 0, z = 0, yaw = 0, speed = 0; Pose pose = Pose::Idle; };

// One Drowned: its body, where it is, its mind and what's been shot off it.
struct Enemy {
    std::string id;
    std::string key;              // "room/id": what the world remembers it by
    int room = -1;                // the room it's in now (index into Game::rooms_)
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
    bool submerged = false;       // under the water, waiting ("emerge" in the room file)
    float rise = -1;              // rising out of it: 0..1 (-1: not rising)
    float heard_t = 0;            // remembers a noise for a moment (keeps it on his trail through the house)
    float bang_t = 0;             // at a shut door: how long it has been beating on it
    std::string wake_flag;        // waits for this flag (requires_flag)
};

// The survivor's fighting state.
enum class PMode { Normal, Aim, QuickTurn, Dodge, Kick, Hurt, Dead };

class Game {
public:
    static constexpr int W = 1280, H = 720;   // plates are 16:9 at this aspect
    bool init(const std::string& room_id);
    // DW_STREAM_REPORT: how many plates are resident (for the tests of streaming by hand).
    int resident_rooms() const;
    void shutdown();
    void update(float dt);          // input, AI, animation
    void render();                  // scene -> offscreen target
    void present() const;           // post-process to the window + HUD
    int capture_count() const { return 33; }
    std::string stage(int i);       // pose a capture setup; returns its name
    // A still of the room (--still): the survivor standing at (x, z) facing yaw (degrees), no
    // Drowned, seen from `shot` (empty: whichever shot covers him). Render and present after.
    void pose_still(float x, float z, float yaw_deg, const std::string& shot);
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
    void reload_hands();                         // the hands through a reload (reload.hpp), and what they drop and click home
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

    // The status screen (status_view.cpp) and what lies about in the room to be picked up, read or
    // looked at (game_world.cpp). Time stands still while either has the screen.
    struct Loot { std::string key; int item = I_NONE, count = 0; Vector3 pos{}; int dropped = -1; };   // still lying here
    struct NoteRead { std::string key, title, text; };
    void init_status();
    void unload_status();
    void reset_world();                          // a fresh start (and after dying): nothing taken, nothing read
    void refresh_loot();                         // this storey's pickups, as the world remembers them
    bool interact();                             // Cross with nothing to kick: whatever he's facing, close enough
    int loot_in_reach() const;                   // the pickup he's facing (-1: none)
    std::pair<int, int> spot_in_reach() const;   // the interactable he's facing: (room, index), room -1: none
    void update_status(float dt);
    void apply(const status::Command& c);
    status::Pad status_pad() const;
    void render_status();                        // the preview, his figure and the screen, into ui_rt_
    void draw_status_ui();
    void draw_loot();                            // in the 3D pass: what lies in the room, and its glint
    void draw_text_box() const;                  // a line of text at the bottom (present)
    void draw_glints() const;                    // the glint that marks each pickup (present)
    void draw_death() const;                     // YOU DIED, and the choice after it (present; death.hpp times it)
    void draw_glyph(float x, float y, int which, const char* label, float size) const;   // a button, as this pad shows it
    float draw_hint(float x, float y, int which, const char* what) const;
    void show_text(const std::string& text);     // shown at the bottom, time stopped until it's read
    void notice(const std::string& s) { notice_ = s; notice_t_ = 3.0f; }

    // The pause menu (time stands still) with the options, saved to the database.
    void update_menu();
    void draw_menu() const;
    void save_settings() const { if (!settings_path.empty()) settings_.save(settings_path); }

    // The house (game_house.cpp): every room, moved to where it lies; the one he's in; its storey's
    // walls, doorways and door leaves; the plates around him; the beat between storeys.
    bool load_house(const std::string& start_room);
    void build_storey(int storey);                  // colliders, sight walls, enemies and loot for that floor
    void enter_room(int r);                         // he's stepped into room r (seamless): its shots, lights, sound
    void stream_plates();                           // the plates of the rooms next door, decoded in the background
    std::vector<std::string> shot_ids(const RoomSpec& r) const;   // its camera shots and its doors' peeks
    int room_index(const std::string& id) const;
    void update_doors(float dt, Vector2 want, float tilt);   // pushing, leaning, peeking, the stairs
    bool use_door(int room, const Interactable& it);  // Cross at a door: unlock, open, shut, or the stairs
    int doorway_of(int room, const std::string& door_id) const;
    void start_beat(const std::string& room, const std::string& spawn);
    void finish_beat();
    void set_flag(const std::string& flag);
    void wake(const std::string& flag);             // the Drowned that were waiting for it come in
    bool sight_clear(float ax, float az, float bx, float bz) const;   // no wall or shut door between
    void steer_target(const Enemy& e, float& tx, float& tz) const;    // where it heads for to reach him (a doorway first)
    void push_on_doors(Enemy& e, float dt);          // a Drowned at a shut door beats on it, then shoves it open
    void update_emerging(Enemy& e, float dt);        // under the water until he comes near; then it rises
    void draw_leaves();
    void checkpoint();                              // remember him as he came into this room (Try again)
    void retry();                                   // dead: back to the last room's threshold, as he was
    const PlateStore::Pair* current_plate() const;
    Camera3D shot_camera(const Shot& s) const;

    std::vector<RoomSpec> rooms_;                   // every room of the house, in house coordinates
    std::string start_room_;                        // where a new game begins
    int room_ = -1, storey_ = 0;
    std::vector<house::Doorway> doorways_;
    std::vector<doors::Leaf> leaves_;               // one per doorway (painted-shut ones never move and aren't drawn)
    std::vector<Obb2> statics_, sight_, solid_;     // this storey's walls and props; walls only; + the leaves (per frame)
    std::vector<Obb2> shut_;                        // the leaves that block sight now (per frame; kept: no allocation)
    std::vector<Mesh> leaf_meshes_;                 // each live doorway's leaf: the hinge at the origin, along +x
    std::string ambience_;                          // the loop playing now (changes only when a room's differs)
    int peek_ = -1, peek_room_ = -1;                // peeking through doorway peek_ (from room peek_room_'s side)
    Shot peek_shot_;
    Beat beat_;
    std::string beat_room_, beat_spawn_;
    float wake_t_ = -1;                             // a wave on its way in (after the bang)
    std::string wake_flag_;
    struct Checkpoint {
        Inventory inv;
        Firearm guns[2];
        int gun = 0;
        float health = 100;
        status::WorldState world;
        std::vector<NoteRead> notes;
        Actor at;
        int room = -1;
        bool set = false;
    } checkpoint_;

    RoomSpec spec_;                                 // the room he's in (a copy of rooms_[room_])
    Input input_;
    InputFrame in_;                              // this frame's actions (polled once in update)
    GaitPicker gaits_;                           // how hard he's being pushed: sneak, walk or run (controls.hpp)
    Gait gait_ = Gait::Still;                    // ... this frame
    BackTurnChord back_turn_;                    // stick back + the right face button: a quick turn (an option)
    Settings settings_;
    bool paused_ = false, quit_ = false;
    int menu_sel_ = 0;
    PlateStore plates_;
    std::string shot_;
    Camera3D cam_{};
    Shader plate_{}, char_{}, blob_{}, post_{};
    Material char_mat_{}, blob_mat_{};
    Mesh blob_mesh_{};
    RenderTexture2D rt_{};
    Character hero_;
    Actor player_;
    std::vector<Enemy> enemies_;
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
    bool slide_locked_ = false;                  // ... locked open on an empty magazine, until a reload drops it home
    bool shell_from_grip_ = true;                // the 870's next shell: the hand starts from the fore-end (else the port)
    unsigned rng_ = 0x9E3779B9u;
    Stats stats_;
    bool staged_aim_ = false;                    // capture setups hold the aim and the stick from code
    Vector2 staged_in_{};
    std::vector<const Character*> casters_, gun_lit_;   // who casts shadows this frame (kept: no allocation per frame)
    // The status screen and the room's things.
    status::Screen status_;
    status::WorldState world_;
    std::vector<NoteRead> notes_;                // read, in the order found
    std::vector<worldmap::Room> map_;
    std::vector<int> storeys_;
    std::vector<Loot> loot_;
    int pickup_loot_ = -1;                       // the pickup the screen is asking about
    std::vector<std::string> text_queue_;        // lines waiting to be read (examine, a door, what happens next)
    float text_t_ = 0;                           // how long the current line has been up (it types itself out)
    Font f_head_{}, f_head_b_{}, f_body_{}, f_body_b_{}, f_italic_{};
    Font f_fell_{};                              // the death screen's words (IM FELL English)
    int death_sel_ = 0;                          // dead: 0 try again, 1 quit
    Mesh item_mesh_[I_COUNT]{};
    Vector3 item_centre_[I_COUNT]{};
    float item_size_[I_COUNT]{}, item_base_[I_COUNT]{};
    RenderTexture2D preview_rt_{}, figure_rt_{}, ui_rt_{}, blur_rt_{};
    RenderTexture2D icon_rt_{};                  // every item's icon, rendered once from its model (a row of 128 px cells)
    bool icons_ready_ = false;
    void draw_item(int item, float spin, float tilt, float aspect);   // the model, filling the current target's view
    float ui_t_ = 0, spin_ = 0, tilt_ = 0;       // the screen's own clock; the preview's turn
    std::string notice_;                         // what the last action did ("Loaded 12 rounds.")
    float notice_t_ = 0;
    bool status_drawn_ = false;                  // ui_rt_ holds this frame's screen
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
