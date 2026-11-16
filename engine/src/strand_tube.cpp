// damned_waters/engine/src/strand_tube.cpp
// Purpose: see dw/strand_tube.hpp: a smooth, lumpy, round-ended rope through a strand's points.
#include "dw/strand_tube.hpp"

#include <algorithm>
#include <cmath>

namespace dw::strand {
namespace {
// A smooth curve through b and c (Catmull-Rom: its slope at each comes from the points either side).
Vector3 through(const Vector3& a, const Vector3& b, const Vector3& c, const Vector3& d, float t) {
    const float t2 = t * t, t3 = t2 * t;
    auto f = [&](float pa, float pb, float pc, float pd) {
        return 0.5f * (2 * pb + (pc - pa) * t + (2 * pa - 5 * pb + 4 * pc - pd) * t2 + (3 * pb - pa - 3 * pc + pd) * t3);
    };
    return {f(a.x, b.x, c.x, d.x), f(a.y, b.y, c.y, d.y), f(a.z, b.z, c.z, d.z)};
}
float smooth01(float t) { t = std::clamp(t, 0.0f, 1.0f); return t * t * (3 - 2 * t); }
// Where the cap's rings sit past the last point (in tip radii), and how wide each is: a dome.
constexpr float CAP_AT[CAP] = {0.5f, 0.87f}, CAP_R[CAP] = {0.866f, 0.5f};
}  // namespace

float radius_at(const Shape& s, float along) {
    const float L = s.seg * float(s.n - 1), k = std::clamp(along / std::max(L, 1e-6f), 0.0f, 1.0f);
    const float swell = 0.6f * std::sin(along * 180.0f + s.phase) + 0.4f * std::sin(along * 470.0f + s.phase * 2.3f);
    const float root = s.root + (1.0f - s.root) * smooth01(along / 0.03f);   // new growth: 3 cm to reach full thickness
    return s.radius * (1.0f - s.taper * k) * (1.0f + s.lump * swell) * root;
}

Vector3 build(const Vector3* p, const Shape& s, Vector3 x, Ring* out) {
    const int R = (s.n - 1) * s.sub + 1, total = R + CAP;
    const float L = s.seg * float(s.n - 1);
    for (int m = 0; m < R; ++m) {
        const int i = std::min(m / s.sub, s.n - 2);
        const float t = float(m - i * s.sub) / float(s.sub);
        out[m].c = through(p[std::max(i - 1, 0)], p[i], p[i + 1], p[std::min(i + 2, s.n - 1)], t);
        out[m].along = L * float(m) / float(R - 1);
        out[m].r = radius_at(s, out[m].along);
    }
    Vector3 dir = Vector3Subtract(out[R - 1].c, out[R - 2].c);
    dir = Vector3LengthSqr(dir) > 1e-12f ? Vector3Normalize(dir) : Vector3{0, -1, 0};
    const float rt = out[R - 1].r;
    for (int k = 0; k < CAP; ++k) {
        out[R + k].c = Vector3Add(out[R - 1].c, Vector3Scale(dir, rt * CAP_AT[k]));
        out[R + k].along = L + rt * CAP_AT[k];
        out[R + k].r = rt * CAP_R[k];
    }
    // Frames: carry x down the strand, each time taking out what lies along the strand (parallel
    // transport), so the rings never twist against each other.
    for (int m = 0; m < total; ++m) {
        Vector3 t = Vector3Subtract(out[std::min(m + 1, total - 1)].c, out[std::max(m - 1, 0)].c);
        t = Vector3LengthSqr(t) > 1e-12f ? Vector3Normalize(t) : dir;
        x = Vector3Subtract(x, Vector3Scale(t, Vector3DotProduct(x, t)));
        if (Vector3LengthSqr(x) < 1e-8f) x = Vector3CrossProduct(t, std::fabs(t.z) < 0.9f ? Vector3{0, 0, 1} : Vector3{1, 0, 0});
        x = Vector3Normalize(x);
        out[m].x = x;
        out[m].y = Vector3CrossProduct(t, x);
    }
    // The wander: each ring slides a little in its own plane, nothing at the root (it grows from the scalp).
    Vector3 tip = Vector3Add(out[R - 1].c, Vector3Scale(dir, rt));
    if (s.wave > 0) {
        Vector3 last{};
        for (int m = 0; m < total; ++m) {
            const float a = std::min(out[m].along, L), w = s.wave * smooth01(a / 0.04f);
            last = Vector3Add(Vector3Scale(out[m].x, w * std::sin(a * 95.0f + s.phase * 1.7f)),
                              Vector3Scale(out[m].y, w * std::cos(a * 61.0f + s.phase * 0.9f)));
            out[m].c = Vector3Add(out[m].c, last);
        }
        tip = Vector3Add(tip, last);
    }
    return tip;
}

}  // namespace dw::strand
