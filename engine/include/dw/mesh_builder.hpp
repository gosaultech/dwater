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
// Winding: every builder emits counter-clockwise triangles seen from OUTSIDE, so the
// shader can tell the outside of a body from its inside (gl_FrontFacing) and paint
// the inside as raw flesh wherever a surface is torn open.
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
    MAT_LEECH = 14, MAT_ROT = 15,
    MAT_DEAD_EYE = 16,   // milky, clouded cornea
    MAT_TOOTH = 17,      // yellowed enamel
    MAT_BONE = 18,       // wet, dirty bone
    MAT_TONGUE = 19,     // swollen, dark, glossy
    MAT_GUTS = 20,       // intestine: grey-pink, slick
    MAT_MUSSEL = 21,     // zebra mussel shell (stripes baked into the vertex colour)
    MAT_WEED = 22,       // canal weed: slimy ribbons
    MAT_SLOUGH = 23,     // loose, wrinkled skin coming away ("washerwoman" skin)
    MAT_DERMIS = 24,     // raw pink skin where the outer layer slipped off
    MAT_STEEL = 25,      // brushed stainless steel
    MAT_GRIP = 26,       // checkered black polymer grips
    MAT_WAX = 27,        // waxed cotton jacket
    MAT_KNIT = 28,       // chunky cable knit
    MAT_LIPS = 29,       // moist lips
    MAT_BROW = 30,       // eyebrows
    MAT_RUBBER = 31,     // soles
    MAT_NYLON = 32,      // rain jacket, backpack
    MAT_COTTON = 33,     // t-shirts, shirts
    MAT_PRINT = 34,      // printed dress fabric
    MAT_LOCS = 35,       // locs: twisted, matted hair
    MAT_LAMP = 36,       // a lit lens: glows, ignores the room's light
    MAT_WETHAIR = 37,    // long hair, soaked: dark, clumped, glossy
    MAT_WATER = 38       // a drop of water: dark and glassy, it only shows where it catches the light
};

struct MeshData {
    std::vector<float> pos, nrm, uv, tan;
    std::vector<unsigned char> col;
    size_t count() const { return pos.size() / 3; }
    // Append `src` with every position/normal/surface coordinate moved by `xf`.
    void append(const MeshData& src, const Matrix& xf);
};

using Grid = std::vector<std::vector<Vector3>>;   // rows x columns
using Bump = std::function<float(Vector3 dir)>;    // unit direction (front = -Z) -> radial offset (m)
struct Paint { int mat; Color col; };              // mat < 0: leave this spot open (no triangles)
using Painter = std::function<Paint(Vector3 dir)>;
using PaintGrid = std::vector<std::vector<Paint>>;

class MeshBuilder {
public:
    explicit MeshBuilder(MeshData& d) : d_(d) {}
    MeshBuilder& material(int m) { mat_ = float(m); return *this; }
    MeshBuilder& color(Color c) { col_ = c; return *this; }
    MeshBuilder& ao(float a) { ao_ = a; return *this; }
    // Place everything emitted from now on with this transform (rotated shells, clusters).
    MeshBuilder& transform(const Matrix& m) { xf_ = m; return *this; }
    // Grid -> smooth triangles; normals from neighbours, forced outward from each row's centre.
    // wrap: columns join up (tubes, shells); otherwise an open sheet (a coat panel).
    // paint: optional per-vertex material + colour; a quad touching mat < 0 is left out.
    void grid(const Grid& g, bool close_top = false, bool close_bottom = false, bool wrap = true,
              const PaintGrid* paint = nullptr);
    void ellipsoid(Vector3 c, Vector3 r, int segs = 20, int rings = 12, const Bump& bump = {}, const Painter& paint = {});
    void tube(Vector3 a, Vector3 b, float r0, float r1, int sides = 8);
    // Rounded box (a superellipsoid): k = 1 is an ellipsoid, smaller k is boxier with rounded edges.
    void box(Vector3 c, Vector3 half, float k = 0.3f, int segs = 20, int rings = 12);
    // Tube through points; flatten < 1 squashes the cross-section (tongues, ribbons).
    void chain(const std::vector<Vector3>& pts, const std::vector<float>& radii, int sides = 8, float flatten = 1.0f);
    // Hanging cloth (coat skirts, sleeves): rings go DOWN from `top`. length(theta) makes the
    // hem uneven (theta 0 = front); folds ripple more toward the hem. th0..th1 narrower than
    // a full turn gives an open panel, e.g. a coat hanging open at the front.
    void drape(Vector3 top, Vector2 r_top, Vector2 r_bottom, float length, int rings, int segs, int folds,
               float fold_amp, const std::function<float(float)>& length_scale = {}, unsigned seed = 1,
               float th0 = 0.0f, float th1 = 2.0f * PI);
private:
    void tri(const Vector3* p, const Vector3* n, const Color* c, float mat);
    MeshData& d_;
    float mat_ = 0, ao_ = 1;
    Color col_ = WHITE;
    Matrix xf_ = MatrixIdentity();
};

// Cross-section profile along a sweep: (s 0..1, rx, rz, forward shift).
struct Profile {
    std::vector<std::array<float, 4>> keys;
    std::array<float, 3> at(float s) const;
};

// A tube REBUILT every frame along a smooth curve through moving joints: elbows,
// knees and the waist bend without seams because the skin is one continuous surface.
// Sculpt (collarbones, folds) and paint (blood trails) are functions of (s, theta):
// s = 0..1 along the tube, theta = angle round it (0 = the frame's +Z side, pi/2 = +X).
// Both are evaluated once at setup, so a rebuild costs the same with or without them.
using SculptFn = std::function<float(float s, float th)>;         // radial offset (m)
using PaintFn = std::function<Color(float s, float th, Color base)>;
class Sweep {
public:
    Sweep(int rings, int sides, Profile profile, int mat, Color c, float length_hint);
    Sweep& tail(float from_s, int mat, Color c);    // e.g. sleeve -> bare wrist
    Sweep& arc(float th0, float th1);               // open tube (th 0 = the +Z side of the frame)
    Sweep& surface(Vector3 offset);                 // shift the pattern space (so no two parts share a pattern)
    Sweep& sculpt(SculptFn f);
    Sweep& paint(PaintFn f);
    // keep < pts.size(): the tube ends at control point keep-1 (a severed limb); the
    // rings past it collapse to nothing and cut() describes the open end.
    void build(const std::vector<Vector3>& pts, Vector3 right_hint, int keep = -1);
    struct Frame { Vector3 c, x, z, t; float rx = 0, rz = 0; };
    const Frame& cut() const { return cut_; }                  // end ring of the last build
    Frame ring_frame(float s) const;                           // frame at arc fraction s (last build)
    float point_s(int i) const { return i < int(point_s_.size()) ? point_s_[i] : 1.0f; }
    int rings() const { return rings_; }
    int sides() const { return sides_; }
    // Triangles of the ring bands whose middle lies in [s0, s1), in the space they were built in.
    void append_span(MeshData& out, float s0, float s1) const;
    MeshData data;
private:
    void topology();
    int rings_, sides_;
    Profile prof_;
    int mat_, tail_mat_ = -1;
    Color col_, tail_col_{};
    float tail_from_ = 2.0f, length_ = 1.0f, th0_ = 0.0f, th1_ = 2.0f * PI;
    Vector3 surf_off_{};
    SculptFn sculpt_;
    PaintFn paint_;
    std::vector<float> disp_;                      // sculpt, sampled per grid vertex
    std::vector<Vector3> fine_, gp_, gn_;          // per-frame scratch, kept to avoid reallocating
    std::vector<float> acc_;
    Frame cut_{};
    std::vector<Frame> frames_;
    std::vector<float> point_s_;
};

Mesh upload(const MeshData& d, bool dynamic = false);
void refresh(Mesh& m, const MeshData& d);   // push new positions/normals (dynamic meshes)

}  // namespace dw
#endif
