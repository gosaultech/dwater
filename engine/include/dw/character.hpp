// damned_waters/engine/include/dw/character.hpp
// Purpose: procedural characters. A skeleton of joints (forward kinematics),
// swept tubes for torso/arms/legs (seamless bends), rigid parts for heads,
// hands, feet, cloth and gore. Poses are eased joint angles, in CHARACTER axes:
//   x (pitch): limbs hanging DOWN swing forward with +x; knees bend with -x;
//              spine/neck lean BACK with +x (forward lean = -x); feet lift toes with +x
//   y (yaw):   +y turns toward the character's left
//   z (roll):  DOWN limbs' tips move toward the character's right with +z
#ifndef DW_CHARACTER_HPP
#define DW_CHARACTER_HPP
#include <string>
#include <utility>
#include <vector>
#include "dw/mesh_builder.hpp"

namespace dw {

enum Joint : int {
    J_PELVIS, J_SPINE, J_CHEST, J_NECK, J_HEAD, J_SHO_L, J_ELB_L, J_WRI_L, J_SHO_R, J_ELB_R, J_WRI_R,
    J_HIP_L, J_KNE_L, J_ANK_L, J_HIP_R, J_KNE_R, J_ANK_R, J_COUNT
};
enum class Kind { Survivor, Drowned };

class Character {
public:
    static Character make(Kind k);
    void place(Vector3 pos, float yaw) { pos_ = pos; yaw_ = yaw; }
    // Ease toward `pose` (idle|walk|run|aim|hurt|shamble|windup|strike|stagger|dead), then rebuild skin.
    void animate(const std::string& pose, float speed, float dt, float aim_pitch = 0.0f);
    void draw(const Material& m) const;
    void unload();
    Vector3 joint(int j) const { return {W_[j].m12, W_[j].m13, W_[j].m14}; }
    Kind kind = Kind::Survivor;

private:
    struct Rigid { int joint; Mesh mesh; };
    struct Dyn { Sweep sweep; std::vector<std::pair<int, Vector3>> pts; Mesh mesh; };
    void fk();
    void targets(const std::string& pose, float speed, float dt, float aim_pitch, Vector3* T, float& bob);
    void add_rigid(int joint, MeshData& d) { rigid_.push_back({joint, upload(d)}); }
    void add_sweep(Sweep s, std::vector<std::pair<int, Vector3>> pts);

    Vector3 off_[J_COUNT]{}, ang_[J_COUNT]{};
    Matrix W_[J_COUNT]{};
    float pelvis_h_ = 0.95f, bob_ = 0, t_ = 0, phase_ = 0, fall_ = 0, yaw_ = 0;
    Vector3 pos_{};
    std::vector<Rigid> rigid_;
    std::vector<Dyn> dyn_;
    friend Character build_survivor();
    friend Character build_drowned();
};

}  // namespace dw
#endif
