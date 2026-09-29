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
#include <array>
#include <string>
#include <vector>
#include "dw/anatomy.hpp"
#include "dw/combat.hpp"
#include "dw/mesh_builder.hpp"

namespace dw {

struct FilePart;

enum Joint : int {
    J_PELVIS, J_SPINE, J_CHEST, J_NECK, J_HEAD, J_JAW, J_SHO_L, J_ELB_L, J_WRI_L, J_SHO_R, J_ELB_R, J_WRI_R,
    J_HIP_L, J_KNE_L, J_ANK_L, J_HIP_R, J_KNE_R, J_ANK_R,
    J_FING1_L, J_FING2_L, J_THUMB_L, J_FING1_R, J_FING2_R, J_THUMB_R,   // knuckles, middle joints, thumb
    J_COUNT
};
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
    void set_weapon(int w);                   // the survivor's gun in hand: 0 = M92FS, 1 = Jachtgeweer
    int weapon() const { return weapon_; }
    Vector3 muzzle() const;                   // where the shot leaves the barrel (world)
    Vector3 barrel_dir() const;               // which way the barrel points (world)
    Vector3 ejection_port() const;            // where spent brass (or a spent shell) comes out (world)
    // The survivor's flashlight on his backpack strap: where the lens is, and which way it shines.
    bool has_lamp() const { return lamp_joint_ >= 0; }
    Vector3 lamp() const;
    Vector3 lamp_dir() const;
    // The Jachtgeweer sits in the hand tipped by this much (radians about the wrist's x), so it
    // lies level along the aim with the strong elbow bent at the shoulder.
    static constexpr float SHOTGUN_HOLD = -0.12f;
    float limp = 0;                           // 0..1: how badly the survivor limps (the only sign of his health)
    float pump = 0;                           // 0..1: the 870's fore-end racked back
    float slide = 0;                          // 0..1: the M92FS's slide back (1 and staying: locked open, empty)
    float lean = 0;                           // dodge: -1 hops to his left, 1 to his right, 0 straight back

private:
    struct Rigid { int joint, region; Mesh mesh; int tag = 0; };   // tag: 0 always shown; 1 + weapon: only while held
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
    void targets(Pose pose, float speed, float dt, float aim_pitch, Vector3* T, float& bob);
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
    void add_rigid(int joint, int region, MeshData& d, int tag = 0);
    Matrix gun_frame() const;                                       // the gun in hand -> world
    Vector3 skin_point(const Skinned& s, int v) const;             // a skinned vertex where it is this frame
    Vector3 skin_normal(const Skinned& s, int v) const;
    void add_sweep(Sweep s, std::vector<Pt> pts);
    void add_dangle(int joint, int region, Vector3 anchor, Vector3 rest, int n, float seg, Profile prof, int mat, Color c,
                    float drag = 0.96f, float stiff = 0.0f, int pin_joint = -1, Vector3 pin = {});

    Vector3 pattern_offset();                                       // a fresh pattern space per part
    Vector3 off_[J_COUNT]{}, ang_[J_COUNT]{}, twitch_[J_COUNT]{}, head_c_{0, 0.1f, 0};
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
    int lamp_joint_ = -1;                                           // the flashlight's lens: joint and offset (joint space)
    Vector3 lamp_off_{};
    Vector3 chin_{0, -0.05f, -0.085f};                              // jaw space: the chin (for the jaw's hit capsule)
    friend Character build_survivor();
    friend Character build_drowned(int variant);
    friend Character build_citizen(const std::string& id, int variant);
};

}  // namespace dw
#endif
