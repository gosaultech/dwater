// damned_waters/engine/include/dw/character.hpp
// Purpose: characters. A skeleton of joints (forward kinematics) drives either a
// skinned body built offline from MakeHuman's CC0 human (tools/characters, loaded
// from a .dwc file and skinned on the GPU) or procedural swept tubes, plus rigid
// parts (a gun, teeth, gore) and "dangles": little rope simulations for anything
// that should swing (locs, guts, a tongue, loose skin, drawstrings, canal weed).
// Every part carries a body Region (anatomy.hpp) so it can be hit and cut off.
// Poses are eased joint angles, in CHARACTER axes:
//   x (pitch): limbs hanging DOWN swing forward with +x; knees bend with -x;
//              spine/neck/head lean BACK with +x (forward lean = -x); feet lift toes with +x;
//              the jaw OPENS with -x
//   y (yaw):   +y turns toward the character's left
//   z (roll):  DOWN limbs' tips move toward the character's right with +z
#ifndef DW_CHARACTER_HPP
#define DW_CHARACTER_HPP
#include <algorithm>
#include <array>
#include <cmath>
#include <string>
#include <vector>
#include "dw/anatomy.hpp"
#include "dw/clearance.hpp"
#include "dw/combat.hpp"
#include "dw/mesh_builder.hpp"
#include "dw/reload.hpp"
#include "dw/two_bone.hpp"

namespace dw {

struct FilePart;

enum Joint : int {
    J_PELVIS, J_SPINE, J_CHEST, J_NECK, J_HEAD, J_JAW, J_SHO_L, J_ELB_L, J_WRI_L, J_SHO_R, J_ELB_R, J_WRI_R,
    J_HIP_L, J_KNE_L, J_ANK_L, J_HIP_R, J_KNE_R, J_ANK_R,
    // The hands, left then right: three joints along each finger (the knuckle, the middle joint, the
    // joint by the nail) and along the thumb (its root down by the wrist, its knuckle, the joint by
    // its nail), so a hand can close round a grip one segment at a time.
    J_THUMB1_L, J_THUMB2_L, J_THUMB3_L, J_INDEX1_L, J_INDEX2_L, J_INDEX3_L, J_MIDDLE1_L, J_MIDDLE2_L, J_MIDDLE3_L,
    J_RING1_L, J_RING2_L, J_RING3_L, J_LITTLE1_L, J_LITTLE2_L, J_LITTLE3_L,
    J_THUMB1_R, J_THUMB2_R, J_THUMB3_R, J_INDEX1_R, J_INDEX2_R, J_INDEX3_R, J_MIDDLE1_R, J_MIDDLE2_R, J_MIDDLE3_R,
    J_RING1_R, J_RING2_R, J_RING3_R, J_LITTLE1_R, J_LITTLE2_R, J_LITTLE3_R,
    J_COUNT
};
enum Finger : int { F_THUMB, F_INDEX, F_MIDDLE, F_RING, F_LITTLE };
// Finger f's joint k (0 the knuckle or the thumb's root, 1 the middle, 2 by the nail) on one hand.
constexpr int finger_joint(bool right, int f, int k) { return (right ? J_THUMB1_R : J_THUMB1_L) + f * 3 + k; }
// Which hand a joint is part of: 0 neither, 1 the left, 2 the right (the wrist counts: the palm is its).
constexpr int hand_of(int j) {
    return j == J_WRI_L || (j >= J_THUMB1_L && j < J_THUMB1_R) ? 1 : j == J_WRI_R || (j >= J_THUMB1_R && j < J_COUNT) ? 2 : 0;
}
// How a hand holds a gun (fitted by --fitgrips into grips_fitted.inc): where the gun sits in the
// hand (gun space -> that wrist's), and the hand's 15 finger joints (thumb, index, middle, ring,
// little; each from the knuckle out) as this rig's angles.
struct Grip { Matrix hold; Vector3 fingers[15]; };
enum class Kind { Survivor, Drowned };
enum class Pose {
    Idle, Walk, Run, Aim, Hurt, Dead,                       // shared
    Dodge, Kick, Reload,                                    // the survivor fighting
    Shamble, Windup, Strike, Stagger, Floored,              // the Drowned on its feet
    Crawl, CrawlWindup, CrawlStrike                         // the Drowned after losing a leg
};

class Character {
public:
    static Character make(Kind k, int variant = 0);
    void place(Vector3 pos, float yaw) { pos_ = pos; yaw_ = yaw; }
    // Ease toward `pose`, step the dangles, then rebuild the skin.
    void animate(Pose pose, float speed, float dt, float aim_pitch = 0.0f);
    void draw(const Material& m, bool shadow_caster = false) const;   // shadow_caster: for a light's depth map
    void unload();
    Vector3 joint(int j) const { return {W_[j].m12, W_[j].m13, W_[j].m14}; }
    Vector3 head_point() const { return Vector3Transform(head_c_, W_[J_HEAD]); }        // centre of the skull
    Vector3 face_dir() const { return Vector3Normalize({-W_[J_HEAD].m8, -W_[J_HEAD].m9, -W_[J_HEAD].m10}); }
    Kind kind = Kind::Survivor;

    // ── Combat: being hit, and coming apart ──
    // Capsules round each body region still attached, for the shot rays (combat.hpp).
    int hit_volumes(int owner, HitVolume* out, int max) const;
    // Where a ray really meets the skin or clothes of `region` (a capsule is only a stand-in): the
    // point, the surface's normal and the joint that carries it. False if it slips past.
    bool surface_hit(int region, Vector3 ro, Vector3 rd, Vector3& at, Vector3& n, int& joint) const;
    // A wound that stays: a dark, raw crater at `at` (world), riding `joint` from then on.
    void add_wound(int joint, Vector3 at, Vector3 n, float size);
    // Cut off `root` and everything hanging from it. `piece` is what comes away, posed as it was, in
    // world space about `centre` (the game drops it); a raw stump stays on the body, and bleeds.
    void sever(int root, MeshData& piece, Vector3& centre);
    bool severed(int region) const { return (hidden_ >> region) & 1u; }
    void recoil(float kick);                  // the gun bucks: arms, shoulders and head jolt
    void set_weapon(int w);                   // the survivor's gun in hand: 0 = M92FS, 1 = Remington 870
    int weapon() const { return weapon_; }
    Vector3 muzzle() const;                   // where the shot leaves the barrel (world)
    Vector3 barrel_dir() const;               // which way the barrel points (world)
    Vector3 ejection_port() const;            // where spent brass (or a spent shell) comes out (world)
    // The survivor's flashlight on his backpack strap: where the lens is, and which way it shines.
    bool has_lamp() const { return lamp_joint_ >= 0; }
    Vector3 lamp() const;
    Vector3 lamp_dir() const;
    // How each gun sits in the right hand (gun space -> the wrist's), as --fitgrips fitted it to the
    // way people hold them (grips_fitted.inc). The wrist, not the gun, then turns to aim it.
    static Matrix pistol_hold();
    static Matrix shotgun_hold();
    // Debugging the grips: >= 0 shows one hand on its gun with the arms at rest (0 the pistol in the
    // right hand, 1 the 870's wrist in the right, 2 its fore-end in the left; 3 the pistol in both,
    // the left hand put on by hands(); 4 a magazine in the left hand, 5 an 870 shell), whatever
    // the pose.
    int grip_view = -1;
    const Grip& view_grip() const;   // the grip of the hand the gun is in
    bool r_gun_on_left() const { return grip_view == 2 || grip_view >= 4; }
    Matrix grip_view_frame() const { return MatrixMultiply(view_grip().hold, W_[r_gun_on_left() ? J_WRI_L : J_WRI_R]); }   // gun space -> world
    // A joint's angles (this rig's order: z, then x, then y) with a further pitch `a` about its
    // parent's x axis on top. Aiming a long gun up or down the way a shooter does, from the waist:
    // the gun, both arms and the cheek on the stock move as one.
    static Vector3 pitched(Vector3 e, float a) {
        const Matrix m = MatrixMultiply(MatrixMultiply(MatrixMultiply(MatrixRotateZ(e.z), MatrixRotateX(e.x)), MatrixRotateY(e.y)),
                                        MatrixRotateX(a));
        // m = Rx(a) Ry Rx Rz (column vectors); read it back as Ry(y) Rx(x) Rz(z).
        return {std::asin(std::clamp(-m.m9, -1.0f, 1.0f)), std::atan2(m.m8, m.m10), std::atan2(m.m1, m.m5)};
    }
    // A tool: search the arms and the right wrist so the shotgun's bore lies along `aim`, the butt
    // sits at `pocket` (from the right shoulder joint), the elbow no higher than the shoulder and the
    // left hand at `left` (a point on the gun, as cast_guns.cpp places it before the hold), on top
    // of `pose`'s body. With `cheek`, the head and upper body join the search too: the cheek goes
    // down on the comb with the right eye over the bore, just above the receiver, as a shooter
    // sights along a bead. Returns the result as text for the pose tables.
    struct ShotgunFit {
        Vector3 aim{0, 0, -1};
        // The shoulder pocket (from the shoulder joint, chest frame): on the front of his jacket, the
        // pad's top about level with the top of his shoulder.
        Vector3 pocket{-0.05f, 0.02f, -0.15f};   // (the pad pressing the coat in, not through it)
        Vector3 left{0, -0.3547f, 0.0032f};       // under the fore-end, near its back
        bool cheek = true;
        Pose pose = Pose::Aim;                    // the body the arms are fitted on
    };
    std::string fit_shotgun(const ShotgunFit& goal);
    // A tool (--fitpistol): the two-handed pistol aim, thumbs forward. Search the right arm, its
    // wrist and the head so the bore lies along `aim` and the right eye sits on the sight line an
    // arm's length behind the rear sight, the head up and looking along it; and where the left
    // elbow goes, so hands() turns the left wrist no further than it must. Returns the
    // result as text for the pose tables.
    std::string fit_pistol(Vector3 aim = {0, 0, -1});
    // A tool (--fitgrips, grip_fit.cpp): fit his hands to his guns the way people hold them, write
    // the result to `out_path` (src/grips_fitted.inc) and say how close it came.
    std::string fit_grips(const std::string& out_path);
    float limp = 0;                           // 0..1: how badly the survivor limps (the only sign of his health)
    float pump = 0;                           // 0..1: the 870's fore-end racked back
    float slide = 0;                          // 0..1: the M92FS's slide back (1 and staying: locked open, empty)
    float lean = 0;                           // dodge: -1 hops to his left, 1 to his right, 0 straight back
    // A reload under way, as the game has it each frame (the gun's timing, combat.hpp): which kind,
    // how far through it (0..1; a shell: through this shell), and for a shell whether the hand
    // starts on the fore-end (the first shell, or the one after a rack) or at the loading port.
    // In the Reload pose, the hands follow reload.hpp's steps.
    // Where the reloads take the hands. The pistol brought in close, in the chest's frame: its grip
    // at `close_at` (x to his right, y up, -z ahead), in front of his chest where he can see into
    // the magazine well (the "workspace" shooters are taught), its top canted over to his left by
    // `cant`, the muzzle up by `pitch` and turned in by `yaw` (radians), so the well faces the
    // left hand coming up from the pocket. His left coat pocket, in the pelvis's frame: where the
    // wrist goes as the hand dips into it, and how the hand is turned there. --fitreload fits the
    // pistol's numbers so both wrists stay within what wrists do and nothing goes through him.
    struct ReloadShape {
        Vector3 close_at{0.030f, -0.020f, -0.430f};
        float cant = -0.388f, pitch = 0.338f, yaw = 0.0f;
        Vector3 pocket_at{-0.13f, 0.08f, -0.18f};
        float pocket_tilt = -0.35f, pocket_turn = -1.6f;
    };
    ReloadShape reload_shape;
    // A tool (--fitreload): search the pistol's close position and turn (reload_shape) for the
    // magazine change that strains his wrists least with nothing going through anything; returns
    // the result as text, the numbers to put in ReloadShape.
    std::string fit_reload();
    struct Reloading { bool on = false; reload::Kind kind = reload::Kind::Magazine; float t = 0; bool from_grip = true; };
    Reloading reloading;
    // Where the gun's load (cast::GunParts::load: the magazine in the grip) is, its space -> world:
    // for the game to drop the empty magazine from where it was.
    Matrix load_frame() const;
    // A tool (--clearance, character_clearance.cpp): how far anything goes through anything this
    // frame (m): each arm into the body, the gun into the body, the left hand into the right hand
    // and into the gun, and the right forefinger into the gun (the trigger finger going on and off
    // the trigger). Each the deepest point, how many points go in, and (for the first three)
    // where the deepest is (world).
    struct Clearance { clearance::Worst larm, rarm, gun, hands, lhand_gun, rindex_gun; Vector3 larm_at{}, rarm_at{}, gun_at{}; };
    Clearance clearance(std::vector<Vector3>* clashes = nullptr) const;
    // How far a wrist is bent (radians): the angle between the forearm and the hand (wrist to the
    // middle knuckle), whichever way. Comfortable to about 40 degrees, a strain past 60.
    float wrist_bend(bool right) const;
    Vector3 chest_local(Vector3 p) const { return Vector3Transform(p, MatrixInvert(W_[J_CHEST])); }   // (tuning) a point in the chest's frame   // clashes: each arm point that's in (world)
    // A tool (--clearance): each reload played through as the game plays it, the clearance at every
    // step of it, as a table.
    std::string reload_clearance();
    // A tool (--clearance): each gun carried as the game carries it (standing at the ready, a
    // walking and a running stride, the raise to the aim and back down), frame by frame: the
    // clearance, both wrists, and how far the trigger finger is from the trigger.
    std::string stance_clearance();

private:
    // tag: 0 always shown; 1 + weapon: only while that gun is in hand. drive: 1 the slide, 2 the
    // fore-end: the part sits `travel` further along (joint space) when the gun is worked all the way;
    // 3 what the gun's loaded with (the magazine, a shell), wherever a reload has it (load_at_).
    struct Rigid { int joint, region; Mesh mesh; int tag = 0; int drive = 0; Vector3 travel{}; };
    struct Pt { int joint; Vector3 off; int region; };   // sweep control point (region: the segment ENDING here)
    struct Dyn { Sweep sweep; std::vector<Pt> pts; Mesh mesh; };
    struct Dangle {
        int joint, region;
        Vector3 anchor, rest;       // pinned point and hanging direction, both in joint space
        int pin_joint;              // >= 0: the far end is pinned too (a tendon strung between two points)
        Vector3 pin;
        int n; float seg, drag, stiff;
        std::vector<Vector3> p, prev;
        Sweep sweep; Mesh mesh;
        bool live;
    };
    struct Capsule { int a, b; Vector3 oa, ob; float r; };   // keeps dangles out of the body
    struct Skinned { std::string name; Mesh mesh; std::vector<std::vector<int>> by_region; };   // vertex ids per region
    struct Anchor { std::string name; int joint; Vector3 pos, dir; };   // joint space, from the .dwc
    // Hair that swings: many thin strands (locs), simulated like dangles but drawn as ONE small
    // indexed mesh, so 64 locs cost one upload a frame.
    struct Strands {
        int joint = J_HEAD, n = 8, sides = 5;
        std::vector<Vector3> anchor;            // per strand root, joint space
        std::vector<Vector3> rest;              // strands x n: the hairstyle, joint space (physics swings round it)
        std::vector<float> seg, radius, stiff;  // per strand
        std::vector<Vector3> p, prev;           // strands x n, world space
        Mesh mesh{};
        bool live = false;
        Color col{20, 16, 13, 255};
        Color tip{0, 0, 0, 0};                  // alpha > 0: the colour the ends fade to (sun-bleached tips)
        int mat = 0;
        float taper = 0.22f;                    // how much thinner the end is than the root (0..1)
        float lump = 0.09f;                     // how uneven the thickness is along it (palm-rolled locs)
        // Ribbons instead of tubes (long hair as "cards"): flat strips `radius` wide that lie against
        // the head, facing away from the skull's axis (axisA-axisB, joint space); their edges and ends
        // thin out into single hairs (the shader stipples them away).
        bool ribbon = false;
        Vector3 axisA{}, axisB{};
    };

    void fk();
    // The hands, after fk(): in the pistol's reload, the right arm brings the gun in close; the left
    // hand onto the gun where `support_` holds it, or through a reload's steps (reload.hpp). Each arm
    // bent by two-bone IK, blended in and out (character.cpp says how).
    void hands(float dt);
    // Put a hand's wrist at `want` (world), `w` of the way from where the pose put it: the elbow
    // bent and the upper arm turned to reach (two_bone.hpp), the elbow kept where the pose had it,
    // the wrist turned onto `want`, the fingers carried along. Returns the wrist's own turn (this
    // rig's angles), for the forearm's skin.
    // `free`: no fitted pose says where this elbow goes (a reload's moves), so it also turns to
    // spare the wrist (character.cpp says how).
    Vector3 arm_to(bool right, const Matrix& want, float w, bool free = false);
    // Where the left wrist goes for a reload's step (world): on the gun, in the pocket, or holding
    // the load on its way in. `G` is the gun (its built space -> world).
    Matrix reload_place(const reload::Step& s, const Matrix& G) const;
    // The left hand's fingers for a step's hand (15 joints, as Grip::fingers).
    void reload_fingers(reload::Hand h, Vector3* f) const;
    void targets(Pose pose, float speed, float dt, float aim_pitch, Vector3* T, float& bob);
    // Curl one finger toward the palm (radians at its knuckle, middle joint and the joint by the
    // nail; for the thumb, its root, knuckle and tip joint), each about that joint's own hinge;
    // `together` (0..1) closes the finger toward the middle one at the knuckle (the rest pose splays them).
    void curl(Vector3* T, bool right, int finger, float k0, float k1, float k2, float together = 0) const;
    void find_hinges();   // the fingers' hinges, from the rest pose (load_body)
    void step_dangles(float dt);
    bool load_body(const std::string& path);   // skinned body + rest joints from a .dwc file
    const Anchor* anchor(const std::string& name) const;
    void add_strands(Strands s);
    void step_strands(float dt);
    // Water running off a Drowned: drops form at a few low points (fingertips, the chin, hems, the
    // ends of wet hair), fall, and are gone at the floor.
    struct Drip { Vector3 p, v; bool blood; };
    struct DripSource { int joint; Vector3 off; float next; bool blood; int region; };   // joint < 0: the end of hair strand `off.x`
    void add_drip_source(int joint, Vector3 off, bool blood = false, int region = R_BODY);
    void step_drips(float dt);
    void add_skinned(const FilePart& p);
    void add_rigid(int joint, int region, MeshData& d, int tag = 0, int drive = 0, Vector3 travel = {});
    Matrix gun_frame() const;                                       // the gun in hand -> world
    Vector3 right_eye() const;                                      // the middle of the right eyeball (head space)
    Vector3 skin_point(const Skinned& s, int v) const;             // a skinned vertex where it is this frame
    Vector3 skin_normal(const Skinned& s, int v) const;
    void add_sweep(Sweep s, std::vector<Pt> pts);
    void add_dangle(int joint, int region, Vector3 anchor, Vector3 rest, int n, float seg, Profile prof, int mat, Color c,
                    float drag = 0.96f, float stiff = 0.0f, int pin_joint = -1, Vector3 pin = {});

    Vector3 pattern_offset();                                       // a fresh pattern space per part
    Vector3 off_[J_COUNT]{}, ang_[J_COUNT]{}, twitch_[J_COUNT]{}, head_c_{0, 0.1f, 0};
    Vector3 hinge_[J_COUNT]{};                                      // a finger joint's axis: + curls it toward the palm
    Matrix W_[J_COUNT]{};
    Vector3 rest_[J_COUNT]{};                                       // rest-pose joint positions (skinned bodies)
    Matrix bones_[J_COUNT]{};                                       // skinning matrices, this frame
    float pelvis_h_ = 0.95f, bob_ = 0, t_ = 0, phase_ = 0, yaw_ = 0;
    float pitch_ = 0, pivot_ = 0, lift_ = 0;                        // root: falls and crawling
    float from_pitch_ = 0, from_pivot_ = 0, from_lift_ = 0, root_k_ = 1;
    int root_mode_ = 0;                                             // 0 standing, 1 on its back, 2 prone
    float thickness_ = 0.14f;                                       // lying down: how far the back sits above the floor
    float twitch_in_ = 2.0f;                                        // seconds to the next twitch (Drowned)
    float bow_ = 0.0f;                                              // 0..1: the head hangs forward instead of lolling back (Drowned)
    unsigned rng_ = 1, parts_ = 0;
    Vector3 pos_{};
    std::vector<Rigid> rigid_;
    std::vector<Dyn> dyn_;
    std::vector<Dangle> dangles_;
    std::vector<Capsule> colliders_;
    std::vector<Skinned> skinned_;
    std::vector<Anchor> anchors_;
    std::vector<Strands> strands_;
    std::vector<DripSource> drip_src_;
    std::vector<Drip> drips_;
    Mesh drip_mesh_{}, blood_drip_mesh_{};
    unsigned hidden_ = 0;                                           // bit per Region: cut off
    int weapon_ = 0, wounds_ = 0;
    const Grip* support_ = nullptr;                                 // the left hand's grip, while both hands hold the gun
    const Grip* want_support_ = nullptr;                            // ... as this pose has it (targets())
    float support_w_ = 0;                                           // 0..1: how far the left hand has gone onto it
    bool steps_ = false;                                            // the left hand follows a reload's steps (targets())
    // When what the left hand follows changes (the grip, a reload's steps, the other gun), it
    // eases over from where it was, held on the gun meanwhile: lh_from_ (the gun's built space),
    // lh_fade_ 0..1 of the way.
    int lh_source_ = 0;
    Matrix lh_from_ = MatrixIdentity(), lh_last_ = MatrixIdentity();
    float lh_fade_ = 1;
    float close_w_ = 0;                                             // 0..1: the right arm bringing the pistol in to reload
    bool ik_[2]{};                                                  // this frame, the left / right arm was put by arm_to
    Vector3 ik_wrist_[2]{};                                         // ... and its wrist's own turn
    float swivel_[2]{};                                             // each elbow swung out of the body (arm_to), radians
    float dt_ = 1.0f / 60;                                          // this frame's step (animate)
    clearance::Torso torso_[2]{{-0.45f, 0.35f}, {-0.3f, 0.45f}};    // his torso's shape about the chest and the pelvis (load_body)
    float torso_in(Vector3 p, float r) const;                       // a ball into it (m; <= 0 clear)
    int load_at_ = 0;                                               // the load: 0 in the gun, 1 nowhere, 2 in the left hand, 3 going in
    float load_along_ = 0;                                          // (3) how far along its way in
    int lamp_joint_ = -1;                                           // the flashlight's lens: joint and offset (joint space)
    Vector3 lamp_off_{};
    Vector3 chin_{0, -0.05f, -0.085f};                              // jaw space: the chin (for the jaw's hit capsule)
    friend Character build_survivor();
    friend Character build_drowned(int variant);
    friend Character build_citizen(const std::string& id, int variant);
};

}  // namespace dw
#endif
