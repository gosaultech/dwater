// damned_waters/engine/src/clearance.cpp
// Purpose: the vertex-against-surface depth test (clearance.hpp says what it's for).
#include "dw/clearance.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>

namespace dw::clearance {

void Cloud::add(V3 p, V3 n) {
    grid_[key(int(std::floor(p.x / cell_)), int(std::floor(p.y / cell_)), int(std::floor(p.z / cell_)))].push_back(int(p_.size()));
    p_.push_back(p);
    n_.push_back(n);
}

int Cloud::nearest(V3 q, float reach) const {
    const int r = int(std::ceil(reach / cell_));
    const int cx = int(std::floor(q.x / cell_)), cy = int(std::floor(q.y / cell_)), cz = int(std::floor(q.z / cell_));
    int best = -1;
    float bd = reach * reach;
    for (int x = cx - r; x <= cx + r; ++x)
        for (int y = cy - r; y <= cy + r; ++y)
            for (int z = cz - r; z <= cz + r; ++z) {
                const auto it = grid_.find(key(x, y, z));
                if (it == grid_.end()) continue;
                for (int i : it->second) {
                    const V3& p = p_[size_t(i)];
                    const float dx = q.x - p.x, dy = q.y - p.y, dz = q.z - p.z, d = dx * dx + dy * dy + dz * dz;
                    if (d < bd) { bd = d; best = i; }
                }
            }
    return best;
}

float Cloud::depth(V3 q, float reach) const {
    const int i = nearest(q, reach);
    if (i < 0) return 0;
    const V3 &p = p_[size_t(i)], &n = n_[size_t(i)];
    const float s = (q.x - p.x) * n.x + (q.y - p.y) * n.y + (q.z - p.z) * n.z;
    return s < 0 ? -s : 0;
}

Torso::Torso(float y0, float y1, float step) : y0_(y0), step_(step), s_(size_t(std::max(1.0f, std::ceil((y1 - y0) / step)))) {}

void Torso::add(V3 p) {
    const int i = int(std::floor((p.y - y0_) / step_));
    if (i < 0 || i >= int(s_.size())) return;
    Slice& s = s_[size_t(i)];
    s.x.push_back(std::fabs(p.x));
    s.z.push_back(p.z);
    ++s.n;
    ++n_;
}

void Torso::finish(float keep) {
    auto at = [](std::vector<float>& v, float q) {   // the q-th share of the way up the sorted values
        std::sort(v.begin(), v.end());
        return v[size_t(std::lround(q * float(v.size() - 1)))];
    };
    const float tail = 0.5f * (1.0f - keep);
    for (Slice& s : s_) {
        if (s.n == 0) continue;
        s.half = at(s.x, keep);
        s.front = at(s.z, tail);
        s.back = at(s.z, 1.0f - tail);
        s.x = {};
        s.z = {};
    }
}

float Torso::depth(V3 p, float r) const {
    const float f = (p.y - y0_) / step_ - 0.5f;   // between the two nearest slices' middles
    const int i0 = int(std::floor(f));
    float best = -1e9f;
    for (int i : {i0, i0 + 1}) {
        if (i < 0 || i >= int(s_.size()) || s_[size_t(i)].n < 6) continue;   // (too few points to say where its edge is)
        const Slice& s = s_[size_t(i)];
        const float a = std::max(s.half, 0.01f), b = std::max(0.5f * (s.back - s.front), 0.01f), zc = 0.5f * (s.back + s.front);
        const float k = std::sqrt((p.x / a) * (p.x / a) + ((p.z - zc) / b) * ((p.z - zc) / b));   // 1 on the ellipse
        best = std::max(best, r + (1.0f - k) * std::min(a, b));
    }
    return best == -1e9f ? -1.0f : best;
}

std::string Torso::describe() const {
    std::string out;
    char b[96];
    for (size_t i = 0; i < s_.size(); ++i) {
        if (s_[i].n == 0) continue;
        std::snprintf(b, sizeof b, "  y %+.2f: half %.3f, z %.3f..%.3f (%d)\n", y0_ + step_ * (float(i) + 0.5f), s_[i].half, s_[i].front, s_[i].back, s_[i].n);
        out += b;
    }
    return out;
}

Worst worst(const std::vector<V3>& pts, const Cloud& surface, float reach, float tolerance) {
    Worst w;
    for (size_t k = 0; k < pts.size(); ++k) {
        const float d = surface.depth(pts[k], reach);
        if (d > tolerance) ++w.count;
        if (d > w.depth) { w.depth = d; w.at = int(k); }
    }
    return w;
}

}  // namespace dw::clearance
