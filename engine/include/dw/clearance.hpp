// damned_waters/engine/include/dw/clearance.hpp
// Purpose: how far one surface sinks into another, measured from their vertices: for checking that
// an arm, a hand or a gun never goes inside the body (an elbow through the coat, fingers through
// the other hand) as the poses and the reloads move them. A tool for tuning and for tests, never
// run in play. No raylib: plain points, unit-tested (tests/test_clearance.cpp).
//
// Like checking a suit for a pin left in it: for each point of the one thing, find the nearest
// point of the other's skin and ask which side of that skin it's on. Behind the skin by more than
// a whisker means it's poking through.
#ifndef DW_CLEARANCE_HPP
#define DW_CLEARANCE_HPP
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace dw::clearance {

struct V3 { float x, y, z; };

// A surface as points with their outward normals, bucketed in a grid so the nearest one is found
// by looking only in the cells round a point.
class Cloud {
public:
    explicit Cloud(float cell = 0.03f) : cell_(cell) {}
    void add(V3 p, V3 n);
    size_t size() const { return p_.size(); }
    // The nearest point within `reach` of `q`: its index, or -1.
    int nearest(V3 q, float reach) const;
    // How far `q` is behind the surface (m, > 0 inside), judged by the nearest point within `reach`
    // and its normal; 0 if it's outside or nothing is near.
    float depth(V3 q, float reach) const;
    V3 point(int i) const { return p_[size_t(i)]; }

private:
    int64_t key(int x, int y, int z) const { return (int64_t(x) * 73856093) ^ (int64_t(y) * 19349663) ^ (int64_t(z) * 83492791); }
    float cell_;
    std::vector<V3> p_, n_;
    std::unordered_map<int64_t, std::vector<int>> grid_;
};

// A torso's shape for play-time checks, cheap enough to ask every frame: slices across it, each an
// ellipse (its half-width, and its front and back), stacked up a joint's y axis in that joint's
// frame. Built once from the body's rest-pose vertices; asked how far a ball (an elbow, a
// forearm) is into it. Like a tailor's dummy made of stacked oval plates.
class Torso {
public:
    Torso(float y0 = -0.4f, float y1 = 0.4f, float step = 0.02f);
    void add(V3 p);   // a surface point (the joint's frame)
    // Once every point is in: each slice's edges, taken a little inside its outermost points (the
    // `keep` share of them inside), so a few stray points (a seam under the arm, a flap) don't
    // make the torso fatter than it looks.
    void finish(float keep = 0.92f);
    // How far a ball of radius `r` at `p` (the joint's frame) is into the torso (m; > 0 in, <= 0
    // clear by that much). Above or below every slice: clear.
    float depth(V3 p, float r) const;
    bool empty() const { return n_ == 0; }
    std::string describe() const;   // the slices, one a line (for tuning)

private:
    struct Slice { float half = 0, front = 0, back = 0; int n = 0; std::vector<float> x, z; };   // x half-width; z from front to back
    float y0_, step_;
    int n_ = 0;
    std::vector<Slice> s_;
};

// The worst of a set of points against a cloud: the deepest any goes in, and how many go deeper
// than `tolerance`.
struct Worst { float depth = 0; int count = 0; int at = -1; };
Worst worst(const std::vector<V3>& pts, const Cloud& surface, float reach, float tolerance);

}  // namespace dw::clearance
#endif
