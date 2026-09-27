// damned_waters/engine/include/dw/character.hpp
// Purpose: procedural characters. A skeleton of joints (forward kinematics),
// swept tubes for torso/arms/legs (seamless bends), rigid parts for heads,
// hands, feet, cloth and gore, and "dangles": little rope simulations for
// anything that should swing (guts, hair, a tongue, loose skin, canal weed).
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
#include <vector>
#include "dw/anatomy.hpp"
#include "dw/mesh_builder.hpp"

namespace dw {

enum Joint : int {
    J_PELVIS, J_SPINE, J_CHEST, J_NECK, J_HEAD, J_JAW, J_SHO_L, J_ELB_L, J_WRI_L, J_SHO_R, J_ELB_R, J_WRI_R,
    J_HIP_L, J_KNE_L, J_ANK_L, J_HIP_R, J_KNE_R, J_ANK_R, J_COUNT
};
enum class Kind { Survivor, Drowned };
enum class Pose {
    Idle, Walk, Run, Aim, Hurt, Dead,                       // shared
    Shamble, Windup, Strike, Stagger, Floored,              // the Drowned on its feet
    Crawl, CrawlWindup, CrawlStrike                         // the Drowned after losing a leg
};

class Character {
public:
    static Character make(Kind k, int variant = 0);
    void place(Vector3 pos, float yaw) { pos_ = pos; yaw_ = yaw; }
    // Ease toward `pose`, step the dangles, then rebuild the skin.
    void animate(Pose pose, float speed, float dt, float aim_pitch = 0.0f);
    void draw(const Material& m) const;
    void unload();
    Vector3 joint(int j) const { return {W_[j].m12, W_[j].m13, W_[j].m14}; }
    Vector3 head_point() const { return Vector3Transform(head_c_, W_[J_HEAD]); }        // centre of the skull
    Vector3 face_dir() const { return Vector3Normalize({-W_[J_HEAD].m8, -W_[J_HEAD].m9, -W_[J_HEAD].m10}); }
    Kind kind = Kind::Survivor;

private:
    struct Rigid { int joint, region; Mesh mesh; };
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

    void fk();
    void targets(Pose pose, float speed, float dt, float aim_pitch, Vector3* T, float& bob);
    void step_dangles(float dt);
    void add_rigid(int joint, int region, MeshData& d);
    void add_sweep(Sweep s, std::vector<Pt> pts);
    void add_dangle(int joint, int region, Vector3 anchor, Vector3 rest, int n, float seg, Profile prof, int mat, Color c,
                    float drag = 0.96f, float stiff = 0.0f, int pin_joint = -1, Vector3 pin = {});

    Vector3 pattern_offset();                                       // a fresh pattern space per part
    Vector3 off_[J_COUNT]{}, ang_[J_COUNT]{}, twitch_[J_COUNT]{}, head_c_{0, 0.1f, 0};
    Matrix W_[J_COUNT]{};
    float pelvis_h_ = 0.95f, bob_ = 0, t_ = 0, phase_ = 0, yaw_ = 0;
    float pitch_ = 0, pivot_ = 0, lift_ = 0;                        // root: falls and crawling
    float from_pitch_ = 0, from_pivot_ = 0, from_lift_ = 0, root_k_ = 1;
    int root_mode_ = 0;                                             // 0 standing, 1 on its back, 2 prone
    float thickness_ = 0.14f;                                       // lying down: how far the back sits above the floor
    float twitch_in_ = 2.0f;                                        // seconds to the next twitch (Drowned)
    unsigned rng_ = 1, parts_ = 0;
    Vector3 pos_{};
    std::vector<Rigid> rigid_;
    std::vector<Dyn> dyn_;
    std::vector<Dangle> dangles_;
    std::vector<Capsule> colliders_;
    friend Character build_survivor();
    friend Character build_drowned(int variant);
};

}  // namespace dw
#endif
