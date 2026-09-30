// damned_waters/engine/tests/test_mesh_builder.cpp
// Purpose: GoogleTest suite for the hard-surface slab (MeshBuilder::slab, used for the guns): it
// comes out the size it was drawn, closed and facing outward, and concave outlines (a pistol's
// side view is full of them) fill only their inside.
#include <gtest/gtest.h>
#include <cmath>

#include "dw/mesh_builder.hpp"

using namespace dw;

namespace {
struct Bounds { Vector3 lo{1e9f, 1e9f, 1e9f}, hi{-1e9f, -1e9f, -1e9f}; };
Bounds bounds(const MeshData& d) {
    Bounds b;
    for (size_t i = 0; i < d.count(); ++i) {
        const Vector3 p{d.pos[i * 3], d.pos[i * 3 + 1], d.pos[i * 3 + 2]};
        b.lo = Vector3Min(b.lo, p);
        b.hi = Vector3Max(b.hi, p);
    }
    return b;
}
// Signed volume by the divergence theorem: positive only if the surface is closed and its
// triangles face outward.
float volume(const MeshData& d) {
    double v = 0;
    for (size_t t = 0; t + 2 < d.count(); t += 3) {
        const Vector3 a{d.pos[t * 3], d.pos[t * 3 + 1], d.pos[t * 3 + 2]}, b{d.pos[t * 3 + 3], d.pos[t * 3 + 4], d.pos[t * 3 + 5]},
                      c{d.pos[t * 3 + 6], d.pos[t * 3 + 7], d.pos[t * 3 + 8]};
        v += double(Vector3DotProduct(a, Vector3CrossProduct(b, c))) / 6.0;
    }
    return float(v);
}
}  // namespace

TEST(Slab, ARoundedBarKeepsItsSizeAndIsClosed) {
    MeshData d;
    MeshBuilder b(d);
    Outline o;
    o.to(0, 0).to(2, 0).to(2, 1).to(0, 1);
    b.slab(o.p, 0.0f, 0.25f, 0.05f, 3);
    const Bounds bb = bounds(d);
    EXPECT_NEAR(bb.lo.x, -0.25f, 1e-4f);
    EXPECT_NEAR(bb.hi.x, 0.25f, 1e-4f);
    EXPECT_NEAR(bb.lo.y, 0.0f, 1e-4f);
    EXPECT_NEAR(bb.hi.y, 2.0f, 1e-4f);
    EXPECT_NEAR(bb.lo.z, 0.0f, 1e-4f);
    EXPECT_NEAR(bb.hi.z, 1.0f, 1e-4f);
    const float v = volume(d);
    EXPECT_GT(v, 0.97f);   // about 2 x 1 x 0.5 ...
    EXPECT_LT(v, 1.0f);    // ... less the rounded-off edges
}

TEST(Slab, AConcaveOutlineFillsOnlyItsInside) {
    Outline o;   // an L: a 2 x 2 square with a 1 x 1 bite out of it, area 3
    o.to(0, 0).to(2, 0).to(2, 1).to(1, 1).to(1, 2).to(0, 2);
    MeshData d;
    MeshBuilder(d).slab(o.p, 0.0f, 0.5f, 0.0f);
    EXPECT_NEAR(volume(d), 3.0f, 1e-3f);
}

TEST(Slab, EitherWindingComesOutTheSame) {
    Outline cw;
    cw.to(0, 0).to(0, 1).to(2, 1).to(2, 0);   // clockwise
    MeshData d;
    MeshBuilder(d).slab(cw.p, 0.0f, 0.25f, 0.05f);
    EXPECT_GT(volume(d), 0.97f);
}

TEST(Outline, ArcsAndCurvesLandWhereAsked) {
    Outline o;
    o.to(1, 0).arc(0, 0, 1, 0, PI / 2, 8);
    EXPECT_NEAR(o.p.back().x, 0.0f, 1e-5f);
    EXPECT_NEAR(o.p.back().y, 1.0f, 1e-5f);
    o.curve(-1, 1, -1, 0, 6);
    EXPECT_NEAR(o.p.back().x, -1.0f, 1e-5f);
    EXPECT_NEAR(o.p.back().y, 0.0f, 1e-5f);
    const Outline mm = o.scaled(0.001f, 1.0f, 0.0f);
    EXPECT_NEAR(mm.p.back().x, 0.999f, 1e-6f);   // millimetres to metres, and moved
}
