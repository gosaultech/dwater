// damned_waters/engine/include/dw/mesh_builder.hpp
// Purpose: CPU geometry for characters. No OpenGL here (unit-testable);
// upload() turns MeshData into a raylib Mesh.
// Vertex layout, as the character shader reads it:
//   position  object space            normal   smooth normal
//   texcoord  x = material id (Mat), y = baked occlusion (1 = open, 0 = crevice)
//   tangent   xyz = SURFACE coordinate for procedural detail (stable while the
//             mesh animates), w unused
//   color     albedo (sRGB)
// Material-in-a-vertex (Bumper Ball Maze's trick): one uber-shader, no texture swaps.
#ifndef DW_MESH_BUILDER_HPP
#define DW_MESH_BUILDER_HPP
#include <raylib.h>
#include <raymath.h>
#include <array>
#include <functional>
#include <vector>

namespace dw {

enum Mat : int {
    MAT_DEFAULT = 0, MAT_SKIN = 1, MAT_DROWNED = 2, MAT_SHEET = 3, MAT_WOOL = 4, MAT_CLOTH = 5, MAT_DENIM = 6,
    MAT_LEATHER = 7, MAT_HAIR = 8, MAT_EYE = 9, MAT_IRIS = 10, MAT_METAL = 11, MAT_FLESH = 12, MAT_VOID = 13,
    MAT_LEECH = 14, MAT_ROT = 15
};

struct MeshData {
    std::vector<float> pos, nrm, uv, tan;
    std::vector<unsigned char> col;
    size_t count() const { return pos.size() / 3; }
};

using Grid = std::vector<std::vector<Vector3>>;   // rows x columns (columns wrap around)
using Bump = std::function<float(Vector3 dir)>;    // unit direction (front = -Z) -> radial offset (m)

class MeshBuilder {
public:
    explicit MeshBuilder(MeshData& d) : d_(d) {}
    MeshBuilder& material(int m) { mat_ = float(m); return *this; }
    MeshBuilder& color(Color c) { col_ = c; return *this; }
    MeshBuilder& ao(float a) { ao_ = a; return *this; }
    // Wrapped grid -> smooth triangles; normals from neighbours, forced outward from each ring's centre.
    void grid(const Grid& g, bool close_top = false, bool close_bottom = false);
    void ellipsoid(Vector3 c, Vector3 r, int segs = 20, int rings = 12, const Bump& bump = {});
    void tube(Vector3 a, Vector3 b, float r0, float r1, int sides = 8);
    void chain(const std::vector<Vector3>& pts, const std::vector<float>& radii, int sides = 8);
    // Hanging cloth (coat skirts, veils): rings go DOWN from `top`. length(theta) lets the
    // hem be uneven (theta 0 = front); folds ripple more toward the hem.
    void drape(Vector3 top, Vector2 r_top, Vector2 r_bottom, float length, int rings, int segs, int folds,
               float fold_amp, const std::function<float(float)>& length_scale = {}, unsigned seed = 1);
private:
    void tri(Vector3 a, Vector3 b, Vector3 c, Vector3 na, Vector3 nb, Vector3 nc);
    MeshData& d_;
    float mat_ = 0, ao_ = 1;
    Color col_ = WHITE;
};

// Cross-section profile along a sweep: (s 0..1, rx, rz, forward shift).
struct Profile {
    std::vector<std::array<float, 4>> keys;
    std::array<float, 3> at(float s) const;
};

// A tube REBUILT every frame along a smooth curve through moving joints: elbows,
// knees and the waist bend without seams because the skin is one continuous surface.
class Sweep {
public:
    Sweep(int rings, int sides, Profile profile, int mat, Color c, float length_hint);
    Sweep& tail(float from_s, int mat, Color c);   // e.g. sleeve -> bare wrist
    void build(const std::vector<Vector3>& pts, Vector3 right_hint);
    MeshData data;
private:
    void topology();
    int rings_, sides_;
    Profile prof_;
    int mat_, tail_mat_ = -1;
    Color col_, tail_col_{};
    float tail_from_ = 2.0f, length_ = 1.0f;
};

Mesh upload(const MeshData& d, bool dynamic = false);
void refresh(Mesh& m, const MeshData& d);   // push new positions/normals (dynamic meshes)

}  // namespace dw
#endif
