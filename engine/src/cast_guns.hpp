// damned_waters/engine/src/cast_guns.hpp
// Purpose: the survivor's two guns, modelled from the real ones (cast_guns.cpp). Each comes as
// the parts that stay put, the part that moves when it's worked (the M92FS's slide, the Remington
// 870's fore-end, with how far that part travels back) and what goes into it when it's reloaded
// (the M92FS's magazine, a 12-gauge shell for the 870).
#ifndef DW_CAST_GUNS_HPP
#define DW_CAST_GUNS_HPP
#include "dw/mesh_builder.hpp"

namespace dw::cast {

struct GunParts {
    MeshData fixed, moving;
    // What goes in when it's reloaded. The M92FS: its magazine, in the grip (only the base plate
    // shows; it drops out to be changed). The 870: one live shell, lying in the loading port as
    // it goes in, brass to the back (shell_in() says where it goes from there).
    MeshData load;
    Vector3 travel{};   // where the moving part sits when all the way back (wrist space, m)
    Vector3 centre{};   // the middle of the gun (wrist space): what a studio view orbits
};

// Both built in the right hand's wrist space (the barrel runs down the hand (-y) above the web of
// the thumb (-z); +x is the gun's right side), then turned by `hold`: how the gun sits in the hand
// (Character::pistol_hold / shotgun_hold; identity: as built, for catalogue views and tests).
GunParts m92fs(const Matrix& hold = MatrixIdentity());
// A point in a gun's own measure, in the space it's built in (mm: u forward along the bore, v up
// from its centreline, w across to its right; cast_guns.cpp says where each part is).
Vector3 m92fs_at(float u, float v, float w = 0);
Vector3 r870_at(float u, float v, float w = 0);
// The M92FS's magazine well: the way the magazine slides out of the grip (down and a little back,
// along the grip's rake; a unit direction in the space the gun is built in). The magazine's base
// plate is everything below v = MAG_PLATE_TOP (mm): the only part of it a hand can touch while
// it's in.
Vector3 m92fs_well_out();
constexpr float MAG_PLATE_TOP = -116.95f;
// The 870's shell on its way in, `s` from 0 to 1, as a move of the shell from where GunParts::load
// has it (the space the gun is built in): from under the loading port, nose up, into the port and
// level under the tube (s = 0.75), then pushed forward into the tube (s = 1).
Matrix shell_in(float s);
// The 870's furniture: the oiled walnut of the classic police guns (the survivor's), or black synthetic.
enum class Stock { Walnut, Synthetic };
GunParts r870(const Matrix& hold, Stock stock = Stock::Walnut);

}  // namespace dw::cast
#endif
