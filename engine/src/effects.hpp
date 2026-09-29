// damned_waters/engine/src/effects.hpp
// Purpose: what a fight leaves behind, and the flash that lights it. Blood that sprays from a
// hit and lands as spatters on the floor; pools that spread under the dead; brass casings and
// spent shells that bounce and stay; limbs that come away, fall and roll; bone chips when a head
// bursts; and the muzzle flash (a burst of flame at the barrel, plus the light it throws, which
// the game adds to the room's lights and to the painted plate).
// Everything persists for the rest of the encounter (up to a cap), the way RE2 Remake keeps its
// mess: you can read the fight from the floor afterwards.
#ifndef DW_EFFECTS_HPP
#define DW_EFFECTS_HPP
#include <raylib.h>
#include <raymath.h>
#include <algorithm>
#include <vector>

#include "dw/mesh_builder.hpp"

namespace dw {

class Effects {
public:
    void init();       // builds the shared meshes (needs a GL context)
    void set_bounds(float x0, float z0, float x1, float z1) { bx0_ = x0; bz0_ = z0; bx1_ = x1; bz1_ = z1; }   // the room's floor
    void shutdown();
    void clear();      // a fresh start: floors mopped, brass swept up
    void blood_spray(Vector3 at, Vector3 dir, int count, float speed);   // from a wound, mostly along dir
    void blood_burst(Vector3 at, int count);                             // every way at once (a head bursting)
    void chips(Vector3 at, int count);                                   // bone and teeth
    void casing(Vector3 at, Vector3 right, bool shell);                  // brass from the pistol; shells from the shotgun
    void gib(const MeshData& piece, Vector3 centre, Vector3 push);       // a limb that came away
    void pool(Vector3 at, float radius);                                 // blood spreading under a body
    void flash(Vector3 at, Vector3 dir, bool shotgun);                   // the muzzle flash, for a frame or three
    void follow_flash(Vector3 at, Vector3 dir) { if (flash_t_ > 0) { flash_at_ = at; flash_dir_ = Vector3Normalize(dir); } }
    void update(float dt);
    void draw(const Material& m) const;          // blood, brass, pieces: solid
    void draw_flash(const Material& m) const;    // the muzzle flash: draw last, blending additively, no depth writes
    // The flash as a light: where, how bright (0 when dark), and its colour.
    Vector3 flash_pos() const { return flash_at_; }
    float flash_power() const { return flash_t_ > 0 ? flash_power_ * (flash_t_ / flash_len_) : 0.0f; }

private:
    struct Drop { Vector3 p, v; float r; };
    struct Splat { Vector3 p; float r, yaw; int shape; float grow_to = 0; };
    struct Brass { Vector3 p, v, axis; float angle, spin, yaw; bool shell, rest; };
    struct Gib { Mesh mesh; Vector3 p, v, axis; float angle, spin, rest_h; Matrix spun; bool rest; };
    float rnd();   // 0..1

    std::vector<Drop> drops_;
    std::vector<Splat> splats_;
    std::vector<Brass> brass_;
    std::vector<Gib> gibs_;
    Mesh drop_mesh_{}, chip_mesh_{}, casing_mesh_{}, shell_mesh_{}, flash_mesh_[2]{}, splat_mesh_[3]{};
    std::vector<Drop> chips_;
    Vector3 flash_at_{}, flash_dir_{0, 0, -1};
    float flash_t_ = 0, flash_len_ = 0.05f, flash_power_ = 0, flash_roll_ = 0;
    bool flash_shotgun_ = false;
    float bx0_ = 0, bz0_ = 0, bx1_ = 2.1f, bz1_ = 10;
    Vector3 inside(Vector3 p) const { return {std::clamp(p.x, bx0_ + 0.04f, bx1_ - 0.04f), p.y, std::clamp(p.z, bz0_ + 0.04f, bz1_ - 0.04f)}; }
    unsigned rng_ = 0x51ED270Bu;
};

}  // namespace dw
#endif
