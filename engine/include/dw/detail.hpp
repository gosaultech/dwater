// damned_waters/engine/include/dw/detail.hpp
// Purpose: the tiling detail maps laid over the cast, the guns and the items: which there are,
// the shader uniform each is read through, and how many metres of surface one tile covers.
// The files are engine/assets/detail/<name>.png, built by tools/assets/detail_maps.py (which
// holds the same table; a test keeps the two in step). Layout of every map: R, G the surface's
// slope (a normal's x and y), B tone (0.5 = the material's own colour), A gloss.
#ifndef DW_DETAIL_HPP
#define DW_DETAIL_HPP

namespace dw::detail {

struct Map { const char* name; const char* uniform; float tile; };

constexpr Map MAPS[] = {
    {"skin", "u_dSkin", 0.024f},      // pores and fine furrows (generated)
    {"leather", "u_dLeather", 0.3f},  // pebbled grain (scan)
    {"denim", "u_dDenim", 0.3f},      // twill (scan)
    {"cotton", "u_dCotton", 0.3f},    // jersey knit (scan)
    {"walnut", "u_dWalnut", 1.0f},    // grain and figure (scan)
    {"metal", "u_dMetal", 0.08f},     // scratches, pits, a rubbed finish (generated)
};
constexpr int COUNT = int(sizeof(MAPS) / sizeof(MAPS[0]));
// Texture units they stay bound to for the whole run: above the ones raylib's materials and
// batches use, so nothing rebinds them between draws (no per-draw cost).
constexpr int FIRST_UNIT = 8;

}  // namespace dw::detail
#endif
