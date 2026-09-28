// damned_waters/engine/src/cast_common.hpp
// Purpose: small sculpting helpers shared by the cast builders (cast_*.cpp):
// Gaussian bumps on ellipsoids, points on an ellipsoid, a smooth noise for
// ragged edges, colour mixing, and a parametric hand.
#ifndef DW_CAST_COMMON_HPP
#define DW_CAST_COMMON_HPP
#include <algorithm>
#include <cmath>
#include <vector>
#include "dw/character.hpp"

namespace dw::cast {

// A bump centred on a direction: sigma = width (in unit-direction distance), amp = height (m).
struct Feature { Vector3 dir; float sigma, amp; };
inline Bump features(std::vector<Feature> f) {
    for (auto& x : f) x.dir = Vector3Normalize(x.dir);
    return [f](Vector3 d) {
        float s = 0;
        for (const auto& x : f) {
            float q = Vector3LengthSqr(Vector3Subtract(d, x.dir));
            s += x.amp * std::exp(-q / (2 * x.sigma * x.sigma));
        }
        return s;
    };
}
inline Vector3 dirn(float x, float y, float z) { return Vector3Normalize({x, y, z}); }
inline Vector3 on_ellipsoid(Vector3 c, Vector3 r, Vector3 dir, float inset) {
    Vector3 d = Vector3Normalize(dir);
    return {c.x + d.x * (r.x - inset), c.y + d.y * (r.y - inset), c.z + d.z * (r.z - inset)};
}
// Smooth 3D value noise in [0, 1]: ragged edges that stay put.
inline float hash3(int x, int y, int z) {
    unsigned h = unsigned(x) * 374761393u + unsigned(y) * 668265263u + unsigned(z) * 2147483647u;
    h = (h ^ (h >> 13)) * 1274126177u;
    return float(h ^ (h >> 16)) / 4294967295.0f;
}
inline float vnoise(Vector3 p) {
    int ix = int(std::floor(p.x)), iy = int(std::floor(p.y)), iz = int(std::floor(p.z));
    float fx = p.x - ix, fy = p.y - iy, fz = p.z - iz;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy); fz = fz * fz * (3 - 2 * fz);
    auto L = [](float a, float b, float t) { return a + (b - a) * t; };
    float x00 = L(hash3(ix, iy, iz), hash3(ix + 1, iy, iz), fx), x10 = L(hash3(ix, iy + 1, iz), hash3(ix + 1, iy + 1, iz), fx);
    float x01 = L(hash3(ix, iy, iz + 1), hash3(ix + 1, iy, iz + 1), fx), x11 = L(hash3(ix, iy + 1, iz + 1), hash3(ix + 1, iy + 1, iz + 1), fx);
    return L(L(x00, x10, fy), L(x01, x11, fy), fz);
}
inline float gauss(float x, float mu, float sigma) { float d = (x - mu) / sigma; return std::exp(-0.5f * d * d); }
inline float wrap_angle(float a) {
    while (a > PI) a -= 2 * PI;
    while (a < -PI) a += 2 * PI;
    return a;
}
inline float smooth01(float a, float b, float x) { float t = std::clamp((x - a) / (b - a), 0.0f, 1.0f); return t * t * (3 - 2 * t); }
inline Color mix(Color a, Color b, float t) {
    t = std::clamp(t, 0.0f, 1.0f);
    auto m = [t](unsigned char x, unsigned char y) { return static_cast<unsigned char>(std::lround(x + (y - x) * t)); };
    return {m(a.r, b.r), m(a.g, b.g), m(a.b, b.b), 255};
}
// Rotation that turns +Y onto `up` (for shells and clusters placed on a surface).
inline Matrix align_y(Vector3 up, float spin) {
    up = Vector3Normalize(up);
    Vector3 ref = std::fabs(up.y) > 0.9f ? Vector3{1, 0, 0} : Vector3{0, 1, 0};
    Vector3 x = Vector3Normalize(Vector3CrossProduct(ref, up)), z = Vector3CrossProduct(x, up);
    Matrix m = MatrixIdentity();
    m.m0 = x.x; m.m1 = x.y; m.m2 = x.z;
    m.m4 = up.x; m.m5 = up.y; m.m6 = up.z;
    m.m8 = z.x; m.m9 = z.y; m.m10 = z.z;
    return MatrixMultiply(MatrixRotateY(spin), m);
}

// A cluster of zebra mussels on a surface: small striped shells, packed and half-buried.
inline void mussels(MeshData& d, Vector3 at, Vector3 normal, int count, float spread, unsigned seed) {
    const Color dark{34, 26, 18, 255}, light{168, 152, 116, 255};
    unsigned s = seed * 2654435761u + 1u;
    auto rnd = [&s]() { s ^= s << 13; s ^= s >> 17; s ^= s << 5; return float(s & 0xFFFF) / 65535.0f; };
    const Matrix frame = align_y(normal, 0.0f);
    const Painter stripes = [dark, light](Vector3 q) {   // the zigzag bands that give zebra mussels their name
        if (q.y < -0.35f) return Paint{MAT_MUSSEL, dark};
        float z = std::sin(q.z * 22.0f + 3.0f * std::fabs(std::sin(q.x * 6.0f)));
        return Paint{MAT_MUSSEL, z > 0.3f ? light : dark};
    };
    for (int i = 0; i < count; ++i) {
        float a = rnd() * 2 * PI, r = std::sqrt(rnd()) * spread, len = 0.013f + rnd() * 0.007f;
        Vector3 local{std::cos(a) * r, -0.002f, std::sin(a) * r};
        Matrix m = MatrixMultiply(MatrixMultiply(MatrixRotateX((rnd() - 0.5f) * 0.9f), MatrixRotateY(rnd() * 2 * PI)),
                                  MatrixTranslate(local.x, local.y, local.z));
        m = MatrixMultiply(m, MatrixMultiply(frame, MatrixTranslate(at.x, at.y, at.z)));
        MeshBuilder(d).transform(m).ellipsoid({0, 0.004f, 0}, {len * 0.5f, len * 0.42f, len}, 10, 7, {}, stripes);
    }
}

// A hand hanging from the wrist: palm faces the body, fingers point down (-Y), thumb forward (-Z).
struct HandStyle {
    float scale = 1.0f, finger_len = 0.075f;
    int mat = MAT_SKIN; Color skin{198, 150, 122, 255};
    int tip_mat = -1; Color tip{20, 16, 14, 255};   // tip_mat >= 0: dark nail beds / rotted tips
    float curl = 0.0f;                              // 0 straight, 1 clawed
};
inline void hand(MeshData& d, float side, const HandStyle& h) {
    MeshBuilder b(d);
    const float s = h.scale;
    b.material(h.mat).color(h.skin);
    b.ellipsoid({0, -0.052f * s, -0.004f}, {0.021f * s, 0.05f * s, 0.043f * s}, 14, 10);
    for (int f = 0; f < 4; ++f) {
        float zf = (-0.03f + f * 0.019f) * s, L = h.finger_len * (f == 3 ? 0.8f : (f == 1 ? 1.08f : 1.0f));
        float c = h.curl * (0.8f + 0.1f * f);
        Vector3 a{0, -0.092f * s, zf}, m{-0.004f * side - 0.01f * c, -0.092f * s - L * 0.55f, zf - 0.006f - 0.012f * c},
            t{-0.009f * side - 0.02f * c, -0.092f * s - L * (1.0f - 0.25f * c), zf - 0.018f - 0.03f * c};
        b.chain({a, m, t}, {0.0095f * s, 0.0085f * s, 0.0068f * s}, 7);
        if (h.tip_mat >= 0) {
            MeshBuilder r(d);
            r.material(h.tip_mat).color(h.tip).ellipsoid(t, Vector3Scale(Vector3{0.0075f, 0.011f, 0.0075f}, s), 8, 6);
        }
    }
    b.chain({{-0.01f * side, -0.042f * s, -0.034f * s}, {-0.017f * side, -0.074f * s, -0.054f * s},
             {-0.021f * side, -0.1f * s, -0.062f * s}},
            {0.011f * s, 0.0095f * s, 0.0078f * s}, 7);
}

}  // namespace dw::cast
#endif
