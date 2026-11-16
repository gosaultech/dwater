// damned_waters/engine/src/rain.cpp
// Purpose: see rain.hpp: where each sheet of rain stands for a camera, sized to the picture there.
#include "dw/rain.hpp"

#include <algorithm>
#include <cmath>

namespace dw::rain {

namespace {
V3 sub(V3 a, V3 b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
V3 norm(V3 a) {
    const float l = std::sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
    return l > 1e-9f ? V3{a.x / l, a.y / l, a.z / l} : V3{0, 0, -1};
}
float dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
}  // namespace

std::array<Sheet, SHEETS> sheets(V3 pos, V3 target, float fovy_deg, float aspect) {
    const V3 f = norm(sub(target, pos));
    const V3 h = norm({f.x, 0, f.z});              // the level forward the sheets stand square to
    const V3 r{-h.z, 0, h.x};                      // the picture's right, level
    const V3 u = norm({-f.x * f.y, f.x * f.x + f.z * f.z, -f.z * f.y});   // the picture's up (r x f)
    const float th = std::tan(fovy_deg * 0.5f * 3.14159265f / 180.0f), tw = th * aspect;
    V3 rays[4];
    int k = 0;
    for (float sy : {-1.0f, 1.0f})
        for (float sx : {-1.0f, 1.0f})
            rays[k++] = norm({f.x + r.x * sx * tw + u.x * sy * th, f.y + r.y * sx * tw + u.y * sy * th, f.z + r.z * sx * tw + u.z * sy * th});
    std::array<Sheet, SHEETS> out{};
    for (int i = 0; i < SHEETS; ++i) {
        const float d = DIST[i];
        float a0 = 1e9f, a1 = -1e9f, y0 = 1e9f, y1 = -1e9f;
        for (const V3& ray : rays) {
            const float t = d / std::max(dot(ray, h), 0.05f);   // where the ray meets the sheet's plane
            const V3 p{pos.x + ray.x * t, pos.y + ray.y * t, pos.z + ray.z * t};
            const float across = dot(sub(p, pos), r);
            a0 = std::min(a0, across);
            a1 = std::max(a1, across);
            y0 = std::min(y0, p.y);
            y1 = std::max(y1, p.y);
        }
        a0 -= MARGIN;
        a1 += MARGIN;
        y0 -= MARGIN;
        y1 += MARGIN;
        const float cx = pos.x + h.x * d, cz = pos.z + h.z * d;
        auto at = [&](float a, float y) { return V3{cx + r.x * a, y, cz + r.z * a}; };
        Sheet& s = out[size_t(i)];
        s.c[0] = at(a0, y0);
        s.c[1] = at(a1, y0);
        s.c[2] = at(a1, y1);
        s.c[3] = at(a0, y1);
        s.u0 = a0;
        s.u1 = a1;
        s.v0 = y0;
        s.v1 = y1;
        s.dist = d;
    }
    return out;
}

}  // namespace dw::rain
