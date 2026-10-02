// damned_waters/engine/src/cast_guns.hpp
// Purpose: the survivor's two guns, modelled from the real ones (cast_guns.cpp). Each comes as
// the parts that stay put and the part that moves when it's worked: the M92FS's slide, the
// Remington 870's fore-end, with how far that part travels back.
#ifndef DW_CAST_GUNS_HPP
#define DW_CAST_GUNS_HPP
#include "dw/mesh_builder.hpp"

namespace dw::cast {

struct GunParts {
    MeshData fixed, moving;
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
// The 870's furniture: the oiled walnut of the classic police guns (the survivor's), or black synthetic.
enum class Stock { Walnut, Synthetic };
GunParts r870(const Matrix& hold, Stock stock = Stock::Walnut);

}  // namespace dw::cast
#endif
