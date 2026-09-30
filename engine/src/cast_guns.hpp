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

// Both in the right hand's wrist space: the barrel runs down the hand (-y) above the web of the
// thumb (-z); +x is the gun's right side.
GunParts m92fs();
// The 870's furniture: the Express Tactical's black synthetic, or the oiled walnut of the classic guns.
enum class Stock { Synthetic, Walnut };
GunParts r870(const Matrix& hold, Stock stock = Stock::Synthetic);   // hold: how it's turned in the hand (Character::shotgun_hold)

}  // namespace dw::cast
#endif
