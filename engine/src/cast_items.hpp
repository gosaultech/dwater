// damned_waters/engine/src/cast_items.hpp
// Purpose: the things in the case as 3D models (cast_items.cpp), for the status screen's preview
// and for items lying in the world waiting to be picked up.
#ifndef DW_CAST_ITEMS_HPP
#define DW_CAST_ITEMS_HPP
#include "dw/combat.hpp"
#include "dw/mesh_builder.hpp"

namespace dw::cast {

struct ItemModel {
    MeshData mesh;        // upright, its best face toward +z, in metres
    Vector3 centre{};     // the middle of its bounds (the preview turns it about this)
    float size = 0.1f;    // its longest extent (m): how far back the preview camera stands
};
// The model of an item (an Item id); empty for I_NONE.
ItemModel item_model(int item);

}  // namespace dw::cast
#endif
