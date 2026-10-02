// damned_waters/engine/src/grip_fit.cpp
// Purpose: a tool (`damned_waters --fitgrips`): fit the survivor's hands to his guns the way people
// actually hold them, and write the result to src/grips_fitted.inc for the pose tables.
//
// How it works, in three pieces:
//  - Each gun becomes a signed distance field: for any point near it, how far the gun's surface is
//    (negative inside the steel or wood), sampled on a 1 mm grid like a topographic map in 3D.
//  - Each hand is the survivor's own skin (about 1600 vertices), bent by its 15 finger joints the
//    way the engine bends it (linear blend skinning), in the frame of its wrist.
//  - A search moves the gun about in the hand and bends each finger until: no skin sinks more than
//    a millimetre into the gun (flesh gives a little, steel doesn't); the palm side of every
//    gripping finger segment lies on it; and the points a shooting instructor checks land where
//    they should (the web of the hand up under the pistol's tang, the pad of the trigger finger on
//    the trigger with its other two segments clear of the frame, the thumb forward along the
//    frame, or round the shotgun's wrist; the support hand over the strong one).
// The goals are written out below, gun by gun, with the technique they come from.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

#include "cast_guns.hpp"
#include "dw/character.hpp"
#include "grips.hpp"

namespace dw {
namespace {
constexpr float MM = 0.001f;

// ── The gun as a distance field ─────────────────────────────────────────────────
struct Sdf {
    Vector3 lo{};
    float h = 0.001f, band = 0.008f;   // grid step; distances are only exact this close to the surface
    int n[3]{};
    std::vector<float> d;
    float at(Vector3 p) const {
        float g[3] = {(p.x - lo.x) / h, (p.y - lo.y) / h, (p.z - lo.z) / h}, out = 0;
        int i[3];
        float f[3];
        for (int a = 0; a < 3; ++a) {   // outside the box: from its nearest edge, plus the way there
            const float c = std::clamp(g[a], 0.0f, float(n[a] - 1));
            out += (g[a] - c) * (g[a] - c);
            g[a] = c;
            i[a] = std::min(int(g[a]), n[a] - 2);
            f[a] = g[a] - float(i[a]);
        }
        out = std::sqrt(out) * h;
        auto v = [&](int x, int y, int z) { return d[(size_t(z) * size_t(n[1]) + size_t(y)) * size_t(n[0]) + size_t(x)]; };
        const float c00 = Lerp(v(i[0], i[1], i[2]), v(i[0] + 1, i[1], i[2]), f[0]);
        const float c10 = Lerp(v(i[0], i[1] + 1, i[2]), v(i[0] + 1, i[1] + 1, i[2]), f[0]);
        const float c01 = Lerp(v(i[0], i[1], i[2] + 1), v(i[0] + 1, i[1], i[2] + 1), f[0]);
        const float c11 = Lerp(v(i[0], i[1] + 1, i[2] + 1), v(i[0] + 1, i[1] + 1, i[2] + 1), f[0]);
        return Lerp(Lerp(c00, c10, f[1]), Lerp(c01, c11, f[1]), f[2]) + out;
    }
};

// The point of triangle abc nearest p (Ericson, Real-Time Collision Detection, 5.1.5).
Vector3 nearest_on_triangle(Vector3 p, Vector3 a, Vector3 b, Vector3 c) {
    const Vector3 ab = Vector3Subtract(b, a), ac = Vector3Subtract(c, a), ap = Vector3Subtract(p, a);
    const float d1 = Vector3DotProduct(ab, ap), d2 = Vector3DotProduct(ac, ap);
    if (d1 <= 0 && d2 <= 0) return a;
    const Vector3 bp = Vector3Subtract(p, b);
    const float d3 = Vector3DotProduct(ab, bp), d4 = Vector3DotProduct(ac, bp);
    if (d3 >= 0 && d4 <= d3) return b;
    const float vc = d1 * d4 - d3 * d2;
    if (vc <= 0 && d1 >= 0 && d3 <= 0) return Vector3Add(a, Vector3Scale(ab, d1 / (d1 - d3)));
    const Vector3 cp = Vector3Subtract(p, c);
    const float d5 = Vector3DotProduct(ab, cp), d6 = Vector3DotProduct(ac, cp);
    if (d6 >= 0 && d5 <= d6) return c;
    const float vb = d5 * d2 - d1 * d6;
    if (vb <= 0 && d2 >= 0 && d6 <= 0) return Vector3Add(a, Vector3Scale(ac, d2 / (d2 - d6)));
    const float va = d3 * d6 - d5 * d4;
    if (va <= 0 && d4 - d3 >= 0 && d5 - d6 >= 0)
        return Vector3Add(b, Vector3Scale(Vector3Subtract(c, b), (d4 - d3) / ((d4 - d3) + (d5 - d6))));
    const float inv = 1.0f / (va + vb + vc);
    return Vector3Add(a, Vector3Add(Vector3Scale(ab, vb * inv), Vector3Scale(ac, vc * inv)));
}

// Distances in a band round every triangle; then inside or out along each x-row of the grid, by
// counting the surfaces crossed (+1 going into a part, -1 coming out, so overlapping parts, like a
// grip panel on the frame, still count as solid). The parts must be closed and face outward
// (test_guns.cpp checks they do).
Sdf make_sdf(const std::vector<const MeshData*>& parts, Vector3 lo, Vector3 hi, float h, float band) {
    Sdf s;
    s.lo = lo;
    s.h = h;
    s.band = band;
    s.n[0] = int(std::ceil((hi.x - lo.x) / h)) + 1;
    s.n[1] = int(std::ceil((hi.y - lo.y) / h)) + 1;
    s.n[2] = int(std::ceil((hi.z - lo.z) / h)) + 1;
    const size_t nx = size_t(s.n[0]), ny = size_t(s.n[1]), nz = size_t(s.n[2]);
    s.d.assign(nx * ny * nz, 1.0f);   // (a metre: "far", until measured or swept)
    struct Tri { Vector3 a, b, c; };
    std::vector<Tri> tris;
    for (const MeshData* m : parts)
        for (size_t t = 0; t + 2 < m->count(); t += 3) {
            Tri tr{{m->pos[t * 3], m->pos[t * 3 + 1], m->pos[t * 3 + 2]},
                   {m->pos[t * 3 + 3], m->pos[t * 3 + 4], m->pos[t * 3 + 5]},
                   {m->pos[t * 3 + 6], m->pos[t * 3 + 7], m->pos[t * 3 + 8]}};
            const Vector3 mn = Vector3Min(tr.a, Vector3Min(tr.b, tr.c)), mx = Vector3Max(tr.a, Vector3Max(tr.b, tr.c));
            if (mx.x < lo.x - band || mx.y < lo.y - band || mx.z < lo.z - band || mn.x > hi.x + band || mn.y > hi.y + band ||
                mn.z > hi.z + band)
                continue;
            tris.push_back(tr);
        }
    auto clampi = [](int v, int a, int b) { return std::max(a, std::min(b, v)); };
    for (const Tri& t : tris) {
        const Vector3 mn = Vector3Min(t.a, Vector3Min(t.b, t.c)), mx = Vector3Max(t.a, Vector3Max(t.b, t.c));
        int r0[3], r1[3];
        const float lo3[3] = {lo.x, lo.y, lo.z}, mn3[3] = {mn.x, mn.y, mn.z}, mx3[3] = {mx.x, mx.y, mx.z};
        for (int a = 0; a < 3; ++a) {
            r0[a] = clampi(int(std::floor((mn3[a] - band - lo3[a]) / h)), 0, s.n[a] - 1);
            r1[a] = clampi(int(std::ceil((mx3[a] + band - lo3[a]) / h)), 0, s.n[a] - 1);
        }
        for (int k = r0[2]; k <= r1[2]; ++k)
            for (int j = r0[1]; j <= r1[1]; ++j)
                for (int i = r0[0]; i <= r1[0]; ++i) {
                    const Vector3 p{lo.x + float(i) * h, lo.y + float(j) * h, lo.z + float(k) * h};
                    float& dd = s.d[(size_t(k) * ny + size_t(j)) * nx + size_t(i)];
                    const float dist = Vector3Distance(p, nearest_on_triangle(p, t.a, t.b, t.c));
                    if (dist < band) dd = std::min(dd, dist);
                }
    }
    std::vector<std::vector<int>> cols(ny * nz);
    for (size_t t = 0; t < tris.size(); ++t) {
        const Tri& tr = tris[t];
        const float y0 = std::min(tr.a.y, std::min(tr.b.y, tr.c.y)), y1 = std::max(tr.a.y, std::max(tr.b.y, tr.c.y));
        const float z0 = std::min(tr.a.z, std::min(tr.b.z, tr.c.z)), z1 = std::max(tr.a.z, std::max(tr.b.z, tr.c.z));
        for (int k = clampi(int(std::floor((z0 - lo.z) / h)), 0, s.n[2] - 1); k <= clampi(int(std::ceil((z1 - lo.z) / h)), 0, s.n[2] - 1); ++k)
            for (int j = clampi(int(std::floor((y0 - lo.y) / h)), 0, s.n[1] - 1); j <= clampi(int(std::ceil((y1 - lo.y) / h)), 0, s.n[1] - 1); ++j)
                cols[size_t(k) * ny + size_t(j)].push_back(int(t));
    }
    std::vector<std::pair<float, int>> hits;
    for (size_t k = 0; k < nz; ++k)
        for (size_t j = 0; j < ny; ++j) {
            const float y = lo.y + (float(j) + 0.0013f) * h, z = lo.z + (float(k) + 0.0029f) * h;   // a hair off the grid: never down an edge
            hits.clear();
            for (int t : cols[k * ny + j]) {
                const Tri& tr = tris[size_t(t)];
                const float area = (tr.b.y - tr.a.y) * (tr.c.z - tr.a.z) - (tr.c.y - tr.a.y) * (tr.b.z - tr.a.z);
                if (std::fabs(area) < 1e-14f) continue;
                const float u = ((tr.b.y - y) * (tr.c.z - z) - (tr.c.y - y) * (tr.b.z - z)) / area;
                const float v = ((tr.c.y - y) * (tr.a.z - z) - (tr.a.y - y) * (tr.c.z - z)) / area;
                const float w = 1 - u - v;
                if (u < 0 || v < 0 || w < 0) continue;
                hits.push_back({u * tr.a.x + v * tr.b.x + w * tr.c.x, area < 0 ? 1 : -1});   // facing -x: the ray goes in
            }
            std::sort(hits.begin(), hits.end());
            int wind = 0;
            size_t next = 0;
            for (size_t i = 0; i < nx; ++i) {
                const float x = lo.x + float(i) * h;
                while (next < hits.size() && hits[next].first < x) wind += hits[next++].second;
                if (wind > 0) {
                    float& dd = s.d[(k * ny + j) * nx + i];
                    dd = -dd;
                }
            }
        }
    // Past the band, distances grow outward (and inward) a voxel at a time: a chamfer sweep, down
    // the grid and back up, each voxel taking the best of its neighbours plus the step to them.
    // Rough, but it tells a finger 3 cm away which way the gun is.
    const float step[3] = {h, h * 1.41421f, h * 1.73205f};
    for (int pass = 0; pass < 2; ++pass) {
        const int dir = pass == 0 ? 1 : -1;
        for (int kk = 0; kk < int(nz); ++kk)
            for (int jj = 0; jj < int(ny); ++jj)
                for (int ii = 0; ii < int(nx); ++ii) {
                    const int k = pass == 0 ? kk : int(nz) - 1 - kk, j = pass == 0 ? jj : int(ny) - 1 - jj, i = pass == 0 ? ii : int(nx) - 1 - ii;
                    float& dd = s.d[(size_t(k) * ny + size_t(j)) * nx + size_t(i)];
                    if (std::fabs(dd) < band) continue;   // measured exactly: keep it
                    for (int dk = -1; dk <= 0; ++dk)
                        for (int dj = -1; dj <= 1; ++dj)
                            for (int di = -1; di <= 1; ++di) {
                                if (dk == 0 && (dj > 0 || (dj == 0 && di >= 0))) continue;   // only the half already swept
                                const int x = i + di * dir, y = j + dj * dir, z = k + dk * dir;
                                if (x < 0 || y < 0 || z < 0 || x >= int(nx) || y >= int(ny) || z >= int(nz)) continue;
                                const float nb = s.d[(size_t(z) * ny + size_t(y)) * nx + size_t(x)];
                                const float w = step[std::abs(di) + std::abs(dj) + std::abs(dk) - 1];
                                if (dd > 0 && nb >= 0) dd = std::min(dd, std::max(nb + w, band));
                                if (dd < 0 && nb <= 0) dd = std::max(dd, std::min(nb - w, -band));
                            }
                }
    }
    return s;
}

// What a hand mustn't sink into: a gun, and for the support hand the strong hand too, as capsules
// (a sausage round each finger segment, a few through the palm) drawn into the gun's field.
struct FleshCapsule { Vector3 a, b; float r; };
float capsule_distance(Vector3 p, const FleshCapsule& c) {
    const Vector3 ab = Vector3Subtract(c.b, c.a);
    const float t = std::clamp(Vector3DotProduct(Vector3Subtract(p, c.a), ab) / std::max(Vector3LengthSqr(ab), 1e-12f), 0.0f, 1.0f);
    return Vector3Distance(p, Vector3Add(c.a, Vector3Scale(ab, t))) - c.r;
}
// A union of shapes is the nearest of their distances: each voxel takes the capsules' if nearer.
void draw_into(Sdf& s, const std::vector<FleshCapsule>& caps) {
    for (int k = 0; k < s.n[2]; ++k)
        for (int j = 0; j < s.n[1]; ++j)
            for (int i = 0; i < s.n[0]; ++i) {
                const Vector3 p{s.lo.x + float(i) * s.h, s.lo.y + float(j) * s.h, s.lo.z + float(k) * s.h};
                float& d = s.d[(size_t(k) * size_t(s.n[1]) + size_t(j)) * size_t(s.n[0]) + size_t(i)];
                for (const FleshCapsule& c : caps) d = std::min(d, capsule_distance(p, c));
            }
}
struct Field {
    const Sdf* gun = nullptr;
    float at(Vector3 p) const { return gun->at(p); }
};

// ── The hand ────────────────────────────────────────────────────────────────────
// Points an instructor looks at, each the average of a few skin vertices.
// Skin points, and three joints (inside the hand: where a knuckle is).
enum Named {
    WEB, INDEX_PAD, THUMB_PAD, THUMB_TIP, THENAR, PALM, HEEL, INDEX_TIP, MIDDLE_TIP, RING_TIP, LITTLE_TIP,
    INDEX_KNUCKLE, LITTLE_KNUCKLE, THUMB_JOINT, NAMED
};
const char* const NAMED_NAME[NAMED] = {"web",        "index pad",  "thumb pad",     "thumb tip",      "thenar",
                                       "palm",       "heel",       "index tip",     "middle tip",     "ring tip",
                                       "little tip", "index knuckle", "little knuckle", "thumb joint"};
constexpr int PALM_SEG = 15;   // segments: finger * 3 + joint (0..14), and the palm

struct HandVert {
    int j[4];
    float w[4];
    Vector3 rel[4];   // the vertex from each of its joints, at rest
    int seg;          // -1: not skin, a joint's centre (for the named knuckles)
    bool palmar;
};
struct Hand {
    bool right = true;
    std::vector<HandVert> v;
    std::vector<int> named[NAMED];
    std::vector<int> faces;   // triangles among v (for drawing the hand into another's field)
};

// Every bend of the hand the search can make: the gun's place in the hand, then the fingers.
// q: [0..2] turn of the gun about the pivot (rotation vector), [3..5] its shift (m),
//    then index..little: knuckle, middle, nail curls and the knuckle's spread (4 each),
//    then the thumb: its root as a rotation vector (3), its knuckle's curl and spread, its tip's curl.
constexpr int K = 6 + 4 * 4 + 6;
}  // namespace

// The tool lives in Character for its skeleton and skin; the goals and the search are below.
std::string Character::fit_grips(const std::string& out_path) {
    weapon_ = 0;
    std::string report;
    char line[512];
    // ── The hands, from his skin ────────────────────────────────────────────────
    const Skinned* body = nullptr;
    for (const Skinned& s : skinned_)
        if (s.name == "body") body = &s;
    if (!body) return "no body part\n";
    auto palm_normal = [&](bool right) {
        const Vector3 wrist = rest_[right ? J_WRI_R : J_WRI_L];
        Vector3 n = Vector3Normalize(Vector3CrossProduct(Vector3Subtract(rest_[finger_joint(right, F_INDEX, 0)], wrist),
                                                         Vector3Subtract(rest_[finger_joint(right, F_LITTLE, 0)], wrist)));
        return right ? n : Vector3Negate(n);
    };
    auto make_hand = [&](bool right) {
        Hand hd;
        hd.right = right;
        const Mesh& m = body->mesh;
        const int side = right ? 2 : 1, wrist = right ? J_WRI_R : J_WRI_L;
        const Vector3 along = Vector3Normalize(Vector3Subtract(rest_[finger_joint(right, F_MIDDLE, 0)], rest_[wrist]));
        const Vector3 pn = palm_normal(right);
        std::vector<int> index_of(size_t(m.vertexCount), -1);
        for (int i = 0; i < m.vertexCount; ++i) {
            HandVert hv{};
            float in_hand = 0, best = -1;
            const Vector3 p{m.vertices[i * 3], m.vertices[i * 3 + 1], m.vertices[i * 3 + 2]};
            for (int k = 0; k < 4; ++k) {
                hv.j[k] = m.boneIds[i * 4 + k];
                hv.w[k] = m.boneWeights[i * 4 + k];
                hv.rel[k] = Vector3Subtract(p, rest_[hv.j[k]]);
                if (hand_of(hv.j[k]) == side) in_hand += hv.w[k];
                if (hv.w[k] > best) { best = hv.w[k]; hv.seg = hv.j[k]; }
            }
            if (in_hand < 0.5f || Vector3DotProduct(Vector3Subtract(p, rest_[wrist]), along) < -0.005f) continue;
            hv.seg = hand_of(hv.seg) == side && hv.seg != wrist ? hv.seg - finger_joint(right, 0, 0) : PALM_SEG;
            const Vector3 n{m.normals[i * 3], m.normals[i * 3 + 1], m.normals[i * 3 + 2]};
            hv.palmar = Vector3DotProduct(n, pn) > 0.25f;
            index_of[size_t(i)] = int(hd.v.size());
            hd.v.push_back(hv);
        }
        if (m.indices)
            for (int t = 0; t < m.triangleCount; ++t) {
                const int a = index_of[m.indices[t * 3]], b = index_of[m.indices[t * 3 + 1]], c = index_of[m.indices[t * 3 + 2]];
                if (a >= 0 && b >= 0 && c >= 0) hd.faces.insert(hd.faces.end(), {a, b, c});
            }
        // The named points, picked on the rest pose.
        auto rest_pos = [&](const HandVert& hv) { return Vector3Add(rest_[hv.j[0]], hv.rel[0]); };
        auto nearest = [&](Vector3 at, int count, auto keep) {
            std::vector<std::pair<float, int>> d;
            for (size_t i = 0; i < hd.v.size(); ++i)
                if (keep(hd.v[i])) d.push_back({Vector3Distance(rest_pos(hd.v[i]), at), int(i)});
            std::sort(d.begin(), d.end());
            std::vector<int> out;
            for (int i = 0; i < count && i < int(d.size()); ++i) out.push_back(d[size_t(i)].second);
            return out;
        };
        const auto J = [&](int f, int k) { return rest_[finger_joint(right, f, k)]; };
        auto pad = [&](int f) {   // the middle of the last segment's palm side
            const Vector3 base = J(f, 2), dir = Vector3Normalize(Vector3Subtract(J(f, 2), J(f, 1)));
            float reach = 0;
            for (const HandVert& hv : hd.v)
                if (hv.seg == f * 3 + 2) reach = std::max(reach, Vector3DotProduct(Vector3Subtract(rest_pos(hv), base), dir));
            const Vector3 at = Vector3Add(Vector3Add(base, Vector3Scale(dir, reach * 0.6f)), Vector3Scale(pn, 0.01f));
            return nearest(at, 6, [&](const HandVert& hv) { return hv.seg == f * 3 + 2 && hv.palmar; });
        };
        // The web: not out by the knuckles but down in the crotch between the thumb's bone and the
        // forefinger's, where a pistol's backstrap sits (two fifths of the way from the forefinger's
        // knuckle back to the wrist).
        hd.named[WEB] = nearest(Vector3Lerp(Vector3Lerp(J(F_THUMB, 1), J(F_INDEX, 0), 0.5f), rest_[wrist], 0.4f), 4,
                                [](const HandVert&) { return true; });
        hd.named[INDEX_PAD] = pad(F_INDEX);
        hd.named[THUMB_PAD] = pad(F_THUMB);
        {
            const Vector3 base = J(F_THUMB, 2), dir = Vector3Normalize(Vector3Subtract(J(F_THUMB, 2), J(F_THUMB, 1)));
            hd.named[THUMB_TIP] = nearest(Vector3Add(base, Vector3Scale(dir, 0.06f)), 3, [](const HandVert& hv) { return hv.seg == 2; });
        }
        hd.named[THENAR] = nearest(Vector3Add(Vector3Lerp(J(F_THUMB, 0), J(F_THUMB, 1), 0.5f), Vector3Scale(pn, 0.02f)), 8,
                                   [](const HandVert& hv) { return hv.palmar && (hv.seg == PALM_SEG || hv.seg == 0); });
        hd.named[PALM] = nearest(Vector3Add(Vector3Lerp(rest_[wrist], J(F_MIDDLE, 0), 0.6f), Vector3Scale(pn, 0.03f)), 8,
                                 [](const HandVert& hv) { return hv.palmar && hv.seg == PALM_SEG; });
        hd.named[HEEL] = nearest(Vector3Add(Vector3Lerp(rest_[wrist], J(F_LITTLE, 0), 0.35f), Vector3Scale(pn, 0.03f)), 8,
                                 [](const HandVert& hv) { return hv.palmar && hv.seg == PALM_SEG; });
        auto tip = [&](int f) {   // the pad at the very end of a finger
            const Vector3 base = J(f, 2), dir = Vector3Normalize(Vector3Subtract(J(f, 2), J(f, 1)));
            float reach = 0;
            for (const HandVert& hv : hd.v)
                if (hv.seg == f * 3 + 2) reach = std::max(reach, Vector3DotProduct(Vector3Subtract(rest_pos(hv), base), dir));
            const Vector3 at = Vector3Add(Vector3Add(base, Vector3Scale(dir, reach * 0.85f)), Vector3Scale(pn, 0.008f));
            return nearest(at, 4, [&](const HandVert& hv) { return hv.seg == f * 3 + 2 && hv.palmar; });
        };
        hd.named[INDEX_TIP] = tip(F_INDEX);
        hd.named[MIDDLE_TIP] = tip(F_MIDDLE);
        hd.named[RING_TIP] = tip(F_RING);
        hd.named[LITTLE_TIP] = tip(F_LITTLE);
        auto joint_point = [&](int j) {   // a joint's centre, skinned like a vertex that only it moves
            HandVert hv{};
            hv.j[0] = j;
            hv.w[0] = 1;
            for (int k = 1; k < 4; ++k) hv.j[k] = wrist;
            hv.seg = -1;
            hd.v.push_back(hv);
            return std::vector<int>{int(hd.v.size()) - 1};
        };
        hd.named[INDEX_KNUCKLE] = joint_point(finger_joint(right, F_INDEX, 0));
        hd.named[LITTLE_KNUCKLE] = joint_point(finger_joint(right, F_LITTLE, 0));
        hd.named[THUMB_JOINT] = joint_point(finger_joint(right, F_THUMB, 2));
        return hd;
    };

    // ── Bending it: the parameters to rotations, the skin to gun space ──────────
    auto finger_rotations = [&](const float* q, bool right, Matrix* R) {
        const Vector3 pn = palm_normal(right);
        for (int f = F_INDEX; f <= F_LITTLE; ++f) {
            const float* c = q + 6 + (f - 1) * 4;
            const int j0 = finger_joint(right, f, 0);
            R[j0] = MatrixMultiply(MatrixRotate(hinge_[j0], c[0]), MatrixRotate(pn, c[3]));   // curl, then spread
            R[j0 + 1] = MatrixRotate(hinge_[j0 + 1], c[1]);
            R[j0 + 2] = MatrixRotate(hinge_[j0 + 2], c[2]);
        }
        const float* t = q + 22;
        const int t0 = finger_joint(right, F_THUMB, 0);
        const Vector3 rv{t[0], t[1], t[2]};
        const float ang = Vector3Length(rv);
        R[t0] = ang > 1e-6f ? MatrixRotate(Vector3Scale(rv, 1.0f / ang), ang) : MatrixIdentity();
        R[t0 + 1] = MatrixMultiply(MatrixRotate(hinge_[t0 + 1], t[3]), MatrixRotate(pn, t[4]));
        R[t0 + 2] = MatrixRotate(hinge_[t0 + 2], t[5]);
    };
    auto hold_of = [&](const float* q, const Matrix& h0, Vector3 pivot) {
        const Vector3 c = Vector3Transform(pivot, h0), rv{q[0], q[1], q[2]};
        const float ang = Vector3Length(rv);
        const Matrix turn = ang > 1e-6f ? MatrixRotate(Vector3Scale(rv, 1.0f / ang), ang) : MatrixIdentity();
        return MatrixMultiply(MatrixMultiply(MatrixMultiply(MatrixMultiply(h0, MatrixTranslate(-c.x, -c.y, -c.z)), turn),
                                             MatrixTranslate(c.x, c.y, c.z)),
                              MatrixTranslate(q[3], q[4], q[5]));
    };
    // The hand's joints in its wrist's frame, bent by R; then any vertex placed in gun space.
    auto frames = [&](const Hand& hd, const Matrix* R, Matrix* L) {
        const int wrist = hd.right ? J_WRI_R : J_WRI_L;
        for (int j = 0; j < J_COUNT; ++j)   // the rest of the arm doesn't move in the wrist's frame
            L[j] = MatrixTranslate(rest_[j].x - rest_[wrist].x, rest_[j].y - rest_[wrist].y, rest_[j].z - rest_[wrist].z);
        L[wrist] = MatrixIdentity();
        for (int f = 0; f < 5; ++f)
            for (int k = 0; k < 3; ++k) {
                const int j = finger_joint(hd.right, f, k);
                L[j] = MatrixMultiply(MatrixMultiply(R[j], MatrixTranslate(off_[j].x, off_[j].y, off_[j].z)), k == 0 ? L[wrist] : L[j - 1]);
            }
    };
    auto place = [](const HandVert& hv, const Matrix* L, const Matrix& to_gun) {
        Vector3 x{};
        for (int k = 0; k < 4; ++k)
            if (hv.w[k] > 0) x = Vector3Add(x, Vector3Scale(Vector3Transform(hv.rel[k], L[hv.j[k]]), hv.w[k]));
        return Vector3Transform(x, to_gun);
    };
    auto skin = [&](const Hand& hd, const Matrix* R, const Matrix& hold, std::vector<Vector3>& out) {
        Matrix L[J_COUNT];
        frames(hd, R, L);
        const Matrix to_gun = MatrixInvert(hold);
        out.resize(hd.v.size());
        for (size_t i = 0; i < hd.v.size(); ++i) out[i] = place(hd.v[i], L, to_gun);
    };
    // A fitted hand as solid shapes, in gun space, for the other hand to close onto: a capsule down
    // each finger segment, as thick as the middle of its skin's distances from the bone; four
    // through the palm from the wrist to the knuckles; and the wrist, its sleeve's cuff on it.
    auto hand_capsules = [&](const Hand& hd, const Matrix* R, const Matrix& hold) {
        Matrix L[J_COUNT];
        frames(hd, R, L);
        const Matrix to_gun = MatrixInvert(hold);
        const int wrist = hd.right ? J_WRI_R : J_WRI_L, elbow = hd.right ? J_ELB_R : J_ELB_L;
        auto rest_pos = [&](const HandVert& hv) { return Vector3Add(rest_[hv.j[0]], hv.rel[0]); };
        auto posed = [&](int j, Vector3 rel) { return Vector3Transform(Vector3Transform(rel, L[j]), to_gun); };   // rel: from joint j, at rest
        auto median = [](std::vector<float> d) {
            if (d.empty()) return 0.008f;
            std::nth_element(d.begin(), d.begin() + std::ptrdiff_t(d.size() / 2), d.end());
            return d[d.size() / 2];
        };
        std::vector<FleshCapsule> caps;
        for (int f = 0; f < 5; ++f)
            for (int k = 0; k < 3; ++k) {
                const int j = finger_joint(hd.right, f, k), sg = f * 3 + k;
                const Vector3 a = rest_[j];
                Vector3 b;
                if (k < 2) {
                    b = rest_[j + 1];
                } else {   // the last segment: as far as its skin reaches
                    const Vector3 along = Vector3Normalize(Vector3Subtract(rest_[j], rest_[j - 1]));
                    float reach = 0;
                    for (const HandVert& hv : hd.v)
                        if (hv.seg == sg) reach = std::max(reach, Vector3DotProduct(Vector3Subtract(rest_pos(hv), a), along));
                    b = Vector3Add(a, Vector3Scale(along, reach));
                }
                std::vector<float> d;
                for (const HandVert& hv : hd.v)
                    if (hv.seg == sg) d.push_back(capsule_distance(rest_pos(hv), {a, b, 0}));
                const float r = median(d);
                if (k == 2) b = Vector3Lerp(a, b, std::max(0.0f, 1.0f - r / std::max(Vector3Distance(a, b), 1e-4f)));   // the cap ends at the tip
                caps.push_back({posed(j, {}), posed(j, Vector3Subtract(b, a)), r});
            }
        std::vector<float> d;
        for (const HandVert& hv : hd.v) {
            if (hv.seg != PALM_SEG) continue;
            float best = 1;
            for (int f = F_INDEX; f <= F_LITTLE; ++f)
                best = std::min(best, capsule_distance(rest_pos(hv), {rest_[wrist], rest_[finger_joint(hd.right, f, 0)], 0}));
            d.push_back(best);
        }
        const float palm = median(d);
        for (int f = F_INDEX; f <= F_LITTLE; ++f) caps.push_back({posed(wrist, {}), posed(finger_joint(hd.right, f, 0), {}), palm});
        const Vector3 up = Vector3Normalize(Vector3Subtract(rest_[elbow], rest_[wrist]));   // up the forearm, at rest
        caps.push_back({posed(wrist, {}), posed(wrist, Vector3Scale(up, 0.06f)), palm + 0.012f});
        return caps;
    };

    // ── The goals ───────────────────────────────────────────────────────────────
    struct Target { Named what; Vector3 at; float tol; };   // a named point to a gun-space point (m), within tol (m)
    struct Goal {
        const char* id;     // its name in grips_fitted.inc
        const char* name;
        bool right;
        const Field* field;
        // The first guess, as the technique puts it: one point of the hand pinned (the web, or the
        // middle of the palm), which way the palm faces, and which way the hand reaches (wrist to
        // middle knuckle; all gun space). The rest of the hand lands where its own shape puts it:
        // in this rig the palm is one rigid piece, so the hand is seated whole and the fingers,
        // closing from there, do the wrapping.
        Named anchor;
        Vector3 anchor_at, face, reach;        Vector3 pivot;      // gun space: what the search turns the gun about
        std::vector<Target> targets;
        unsigned wrap;      // bit per segment: its palm side lies on the gun
        unsigned clear;     // bit per segment: it stays clear of the gun (the trigger finger's first two)
        unsigned closing;   // bit per finger: closes round the gun by itself (the rest are posed by the search)
        Sdf* flesh_into = nullptr;   // once fitted, this hand is drawn into that field (for the other hand to grip over)
        // Which way the forearm leaves the wrist (gun space), as the arm comes to the gun in the
        // stance. The grip has to be one an arm can hold up: a hand placed however suits the fingers
        // can leave the wrist bent further than wrists go. Without strain a wrist tips the hand 30
        // degrees toward the little finger (ulnar; what "camming" a support wrist down means), 15
        // toward the thumb, and bends 50 toward the palm or 45 back.
        Vector3 forearm{};
    };
    auto bit = [](int f, int k) { return 1u << unsigned(f * 3 + k); };
    const unsigned gripping = bit(F_MIDDLE, 0) | bit(F_MIDDLE, 1) | bit(F_MIDDLE, 2) | bit(F_RING, 0) | bit(F_RING, 1) | bit(F_RING, 2) |
                              bit(F_LITTLE, 0) | bit(F_LITTLE, 1) | bit(F_LITTLE, 2) | (1u << PALM_SEG);
    const unsigned trigger_finger_clear = bit(F_INDEX, 0) | bit(F_INDEX, 1);
    const unsigned wrapping = (1u << F_MIDDLE) | (1u << F_RING) | (1u << F_LITTLE);

    // The guns as built (no hold), each as a distance field round where the hands go.
    const cast::GunParts pistol = cast::m92fs(), shotgun = cast::r870(MatrixIdentity());
    auto box_of = [](Vector3 a, Vector3 b) { return std::make_pair(Vector3Min(a, b), Vector3Max(a, b)); };
    const auto pbox = box_of(cast::m92fs_at(-45, 25, -45), cast::m92fs_at(150, -140, 45));
    const Sdf pistol_sdf = make_sdf({&pistol.fixed, &pistol.moving}, pbox.first, pbox.second, 0.001f, 0.008f);
    const auto sbox = box_of(cast::r870_at(-170, 45, -55), cast::r870_at(110, -150, 55));
    const Sdf stock_sdf = make_sdf({&shotgun.fixed}, sbox.first, sbox.second, 0.001f, 0.008f);
    const auto fbox = box_of(cast::r870_at(215, 25, -65), cast::r870_at(470, -95, 65));
    const Sdf fore_sdf = make_sdf({&shotgun.fixed, &shotgun.moving}, fbox.first, fbox.second, 0.001f, 0.008f);
    // The pistol again, wider (the support hand wraps the strong one), the strong hand drawn in once
    // it's fitted.
    const auto sbox2 = box_of(cast::m92fs_at(-80, 25, -80), cast::m92fs_at(150, -150, 65));
    Sdf support_sdf = make_sdf({&pistol.fixed, &pistol.moving}, sbox2.first, sbox2.second, 0.001f, 0.008f);
    Field pistol_field{&pistol_sdf}, stock_field{&stock_sdf}, fore_field{&fore_sdf}, support_field{&support_sdf};
    std::snprintf(line, sizeof line, "fields: pistol %dx%dx%d, stock %dx%dx%d, fore-end %dx%dx%d, both hands %dx%dx%d (1 mm)\n",
                  pistol_sdf.n[0], pistol_sdf.n[1], pistol_sdf.n[2], stock_sdf.n[0], stock_sdf.n[1], stock_sdf.n[2], fore_sdf.n[0],
                  fore_sdf.n[1], fore_sdf.n[2], support_sdf.n[0], support_sdf.n[1], support_sdf.n[2]);
    report += line;
    const auto P = [](float u, float v, float w) { return cast::m92fs_at(u, v, w); };
    const auto S = [](float u, float v, float w) { return cast::r870_at(u, v, w); };

    std::vector<Goal> goals;
    // The M92FS in the strong hand (thumbs forward, the grip taught to the Marines and most police):
    // the gun as high in the hand as it goes, the web of the hand pressed up under the tang; the
    // palm on the right grip panel, its heel on the back of the grip; the middle finger tight under
    // the trigger guard, ring and little fingers wrapped round the front strap; the pad of the
    // trigger finger on the trigger's face, the rest of that finger off the frame; the thumb
    // pointing forward along the left of the frame, under the slide.
    // (The palm flat on the right panel, the hand reaching forward and a little down from the wrist
    // behind the grip, so the knuckles come to the front strap's right edge and the fingers close
    // round it onto the left panel. A real palm folds round the backstrap to put the web dead
    // centre; this rig's palm is one rigid piece, so the web sits a little right.)
    const auto dir = [](float u, float v, float w) { return Vector3Normalize({w, -u, -v}); };   // a gun-space direction
    goals.push_back({"PISTOL_RIGHT", "pistol, strong hand", true, &pistol_field, INDEX_KNUCKLE, P(42, -47, 34), dir(0, 0, -1), dir(1.0f, -0.04f, 0), P(20, -70, 0),
                     {{WEB, P(-6, -31, 9), 4 * MM},                    // (his palm doesn't bend: the web sits at the backstrap's top right)
                      {INDEX_PAD, P(84.7f, -42.5f, 0), 2 * MM},        // on the trigger's face
                      {INDEX_KNUCKLE, P(34, -46, 34), 12 * MM},        // the trigger finger's knuckle: right of the frame, behind the trigger
                      {LITTLE_KNUCKLE, P(24, -104, 34), 14 * MM},      // the knuckle line runs down the right of the grip
                      {MIDDLE_TIP, P(36, -64, -17), 6 * MM},           // the fingers round the front strap, their tips
                      {RING_TIP, P(29, -83, -17), 7 * MM},             //   on the left grip panel (his little finger, a big
                      {LITTLE_TIP, P(22, -102, -16), 9 * MM},          //   man's, finds the bottom of the grip)
                      {THUMB_TIP, P(72, -22, -20), 7 * MM},            // the thumb forward along the left of the frame,
                      {THUMB_JOINT, P(45, -25, -21), 9 * MM}},         //   under the slide
                     gripping, trigger_finger_clear, wrapping, &support_sdf,
                     dir(-0.9f, -0.41f, 0.12f)});                      // the arm bent, its elbow down, up to the eye
    // The support hand over it (the same thumbs-forward grip): the wrist cammed forward and down,
    // so the heel of the hand fills the gap the strong fingers leave on the left grip panel; the
    // fingers wrap round the front of the strong fingers, the forefinger high, pressed up under the
    // trigger guard; the thumb forward along the frame under the strong thumb, pointing at the
    // target. (A big hand: with its knuckles at the front of the grip, the palm reaches back to
    // the backstrap and its heel meets the strong hand's behind the grip; the little finger finds
    // the bottom of the magazine. Fitted onto the strong hand as fitted above: its fingers and palm
    // are drawn into this field.)
    goals.push_back({"PISTOL_LEFT", "pistol, support hand", false, &support_field, INDEX_KNUCKLE, P(28, -66, -40), dir(0, 0, 1),
                     dir(1.0f, -0.03f, 0), P(5, -70, -25),
                     {{INDEX_KNUCKLE, P(28, -66, -40), 10 * MM},       // under the trigger guard, over the strong fingertips
                      {THUMB_TIP, P(88, -36, -17), 10 * MM},           // forward along the frame, under the strong thumb
                      {THUMB_JOINT, P(58, -38, -20), 12 * MM},
                      {INDEX_TIP, P(64, -68, 14), 16 * MM},            // round the front of the strong fingers, the tips
                      {MIDDLE_TIP, P(56, -88, 14), 18 * MM}},          //   on their right side
                     gripping | bit(F_INDEX, 0) | bit(F_INDEX, 1) | bit(F_INDEX, 2), 0, wrapping | (1u << F_INDEX), nullptr,
                     dir(-0.8f, -0.46f, -0.38f)});                     // from the left, the elbow down, the wrist cammed
    // The 870's wrist in the strong hand, shaken hands with: the palm along its right side, the web
    // up toward its top behind the receiver, the thumb round over the top to the far side (not along
    // the top, where it would block the view); the trigger finger's pad on the trigger; the other
    // three fingers round the front of the half pistol grip. Held the modern way, elbow down: the
    // wrist below and beside the stock's wrist, the hand reaching forward and up across it, the palm
    // cupping its right side. (DW_FIT_870_REACH: the hand's slant, degrees below the bore.)
    const float reach870 = std::getenv("DW_FIT_870_REACH") ? float(std::atof(std::getenv("DW_FIT_870_REACH"))) * DEG2RAD : 0.0f;
    goals.push_back({"SHOTGUN_RIGHT", "870, strong hand", true, &stock_field, INDEX_KNUCKLE, S(-12, -50, 32), dir(0, 0.3f, -0.95f),
                     dir(std::cos(reach870), -std::sin(reach870), 0), S(-35, -60, 0),
                     {{WEB, S(-30, -15, 15), 15 * MM},
                      {INDEX_PAD, S(33, -60, 0), 2 * MM},              // on the trigger's face
                      {INDEX_KNUCKLE, S(-12, -50, 32), 12 * MM},       // knuckles down the right of the grip
                      {MIDDLE_TIP, S(-14, -70, -16), 12 * MM},         // the fingers round its front, tips on the left
                      {RING_TIP, S(-27, -86, -16), 14 * MM},
                      {LITTLE_TIP, S(-40, -100, -15), 16 * MM},
                      {THUMB_PAD, S(-32, -14, -17), 12 * MM},          // the thumb over the top, its pad on the left
                      {THUMB_JOINT, S(-40, -4, -14), 14 * MM}},
                     gripping, trigger_finger_clear, wrapping, nullptr,
                     dir(-0.55f, -0.65f, 0.5f)});                      // the elbow down and a little out, the butt in the shoulder
    // The fore-end in the support hand: across the palm on a slant, from the heel of the hand (under
    // its right side, toward the back) to between thumb and forefinger (its left side, toward the
    // front); the fingers round its right side, the thumb along its left; the hand toward the front
    // of it, where it steers the gun best.
    goals.push_back({"SHOTGUN_LEFT", "870, support hand", false, &fore_field, PALM, S(335, -57, -4), dir(0, 1, 0), dir(0.71f, 0, 0.71f), S(335, -33, 0),
                     {{PALM, S(335, -58, -2), 6 * MM},
                      {THUMB_TIP, S(395, -32, -29), 8 * MM},           // the thumb along its left side
                      {INDEX_TIP, S(385, -45, 27), 9 * MM},            // the fingers round under and up its right side
                      {MIDDLE_TIP, S(365, -40, 27), 9 * MM},
                      {RING_TIP, S(348, -42, 26), 9 * MM},
                      {LITTLE_TIP, S(332, -46, 25), 10 * MM}},
                     gripping | bit(F_INDEX, 0) | bit(F_INDEX, 1) | bit(F_INDEX, 2), 0, wrapping | (1u << F_INDEX)});

    // ── The search ──────────────────────────────────────────────────────────────
    // A hand at rest, its fingers half closed: the shape the first guess seats on the gun.
    float generic[K]{};
    for (int f = 0; f < 4; ++f) { generic[6 + f * 4] = 1.0f; generic[7 + f * 4] = 1.0f; generic[8 + f * 4] = 0.6f; }
    generic[25] = 0.3f;
    generic[27] = 0.3f;
    // A frame on the palm: at its middle, x along `heel` to `web` (the way the hand reaches), z the
    // way the palm faces (squared to x). The first guess maps the hand's onto the goal's.
    auto palm_frame = [](Vector3 palm, Vector3 face, Vector3 heel, Vector3 web) {
        const Vector3 x = Vector3Normalize(Vector3Subtract(web, heel));
        const Vector3 z = Vector3Normalize(Vector3Subtract(face, Vector3Scale(x, Vector3DotProduct(face, x))));
        const Vector3 y = Vector3CrossProduct(z, x), a = palm;
        Matrix m = MatrixIdentity();
        m.m0 = x.x; m.m1 = x.y; m.m2 = x.z;
        m.m4 = y.x; m.m5 = y.y; m.m6 = y.z;
        m.m8 = z.x; m.m9 = z.y; m.m10 = z.z;
        m.m12 = a.x; m.m13 = a.y; m.m14 = a.z;
        return m;   // the triple's frame -> the space the points are in
    };

    struct Result { Matrix hold; Vector3 joints[15]; float cost, worst_mm; };
    std::vector<Result> results;
    // DW_FIT_ONLY=PISTOL_RIGHT,PISTOL_LEFT (say): fit those grips alone; the others stay as
    // grips_fitted.inc has them.
    const char* only = std::getenv("DW_FIT_ONLY");
    const std::pair<const char*, const Grip*> table[] = {{"PISTOL_RIGHT", &grips::PISTOL_RIGHT}, {"PISTOL_LEFT", &grips::PISTOL_LEFT},
                                                        {"SHOTGUN_RIGHT", &grips::SHOTGUN_RIGHT}, {"SHOTGUN_LEFT", &grips::SHOTGUN_LEFT}};
    for (const Goal& g : goals) {
        const Hand hd = make_hand(g.right);
        std::vector<Vector3> pts;
        Matrix R[J_COUNT];
        for (auto& m : R) m = MatrixIdentity();
        if (only && (std::string(",") + only + ",").find(std::string(",") + g.id + ",") == std::string::npos) {   // kept as it was
            Result r{};
            for (const auto& [id, grip] : table)
                if (std::string(id) == g.id) {
                    r.hold = grip->hold;
                    for (int k = 0; k < 15; ++k) {
                        const Vector3 e = grip->fingers[k];
                        r.joints[k] = e;
                        R[finger_joint(g.right, k / 3, k % 3)] =
                            MatrixMultiply(MatrixMultiply(MatrixRotateZ(e.z), MatrixRotateX(e.x)), MatrixRotateY(e.y));
                    }
                }
            results.push_back(r);
            if (g.flesh_into) draw_into(*g.flesh_into, hand_capsules(hd, R, r.hold));
            report += std::string(g.name) + ": kept\n";
            continue;
        }
        auto centroid = [&](Named nm) {
            Vector3 c{};
            for (int i : hd.named[nm]) c = Vector3Add(c, pts[size_t(i)]);
            return Vector3Scale(c, 1.0f / float(std::max<size_t>(1, hd.named[nm].size())));
        };
        // The first guess: the generic hand's palm frame onto the goal's.
        Matrix h0 = MatrixIdentity();
        Vector3 seat[3];   // where that puts the web, the middle of the palm and the heel (gun space)
        {
            finger_rotations(generic, g.right, R);
            skin(hd, R, MatrixIdentity(), pts);   // (identity hold: pts are in the wrist's frame)
            const int wrist = g.right ? J_WRI_R : J_WRI_L;
            const Vector3 reach = Vector3Subtract(rest_[finger_joint(g.right, F_MIDDLE, 0)], rest_[wrist]);   // (wrist frame)
            const Matrix hand = palm_frame(centroid(PALM), palm_normal(g.right), {0, 0, 0}, reach);
            // The same frame on the gun: x the way the hand reaches, z the way the palm faces;
            // placed so the anchor point lands where the goal pins it.
            Matrix gun = palm_frame({0, 0, 0}, g.face, {0, 0, 0}, g.reach);
            const Vector3 anchor_in_hand = Vector3Transform(centroid(g.anchor), MatrixInvert(hand));
            const Vector3 lands = Vector3Transform(anchor_in_hand, gun);
            gun.m12 = g.anchor_at.x - lands.x; gun.m13 = g.anchor_at.y - lands.y; gun.m14 = g.anchor_at.z - lands.z;
            h0 = MatrixMultiply(MatrixInvert(gun), hand);   // gun space -> palm frame -> wrist space
            const Named nm[3] = {WEB, PALM, HEEL};
            for (int i = 0; i < 3; ++i) seat[i] = Vector3Transform(Vector3Transform(centroid(nm[i]), MatrixInvert(hand)), gun);
            if (std::getenv("DW_FIT_TRACE")) {   // the hand's landmarks, and the seat's, each in its palm frame (mm)
                const Matrix hi_ = MatrixInvert(hand), gi = MatrixInvert(gun);
                const Named nm[3] = {WEB, PALM, HEEL};
                for (int i = 0; i < 3; ++i) {
                    const Vector3 a = Vector3Scale(Vector3Transform(centroid(nm[i]), hi_), 1 / MM);
                    const Vector3 b = Vector3Scale(Vector3Transform(seat[i], gi), 1 / MM);
                    std::snprintf(line, sizeof line, "  palm frame: hand %-5s (%.0f %.0f %.0f)  seat (%.0f %.0f %.0f)\n", NAMED_NAME[nm[i]],
                                  a.x, a.y, a.z, b.x, b.y, b.z);
                    report += line;
                }
                const Named more[] = {INDEX_KNUCKLE, LITTLE_KNUCKLE, THENAR, THUMB_TIP, INDEX_PAD};
                for (Named n : more) {
                    const Vector3 a = Vector3Scale(Vector3Transform(centroid(n), hi_), 1 / MM);
                    std::snprintf(line, sizeof line, "  palm frame: hand %-14s (%.0f %.0f %.0f)\n", NAMED_NAME[n], a.x, a.y, a.z);
                    report += line;
                }
            }
        }
        // The fingers closing round the gun by themselves, the way robot hands are made to grasp
        // (GraspIt's "auto-grasp"): from open, every joint closes at its own pace, all the fingers
        // together; when a segment closes onto something, it and every joint before it stop, and
        // the joints beyond it carry on curling, so each finger wraps whatever it meets. A step that
        // sinks a segment deeper into the gun is taken back. (Only closing onto: a finger that
        // starts with its back against something, the trigger guard over it, closes away from it
        // and carries on. Together, and always from open: the skin by the knuckles moves with the
        // fingers either side, so a finger closed alone would land where its neighbours happened to
        // be.)
        std::vector<int> finger_verts[5];
        for (size_t i = 0; i < hd.v.size(); ++i)
            if (hd.v[i].seg >= 0 && hd.v[i].seg < 15) finger_verts[hd.v[i].seg / 3].push_back(int(i));
        std::vector<char> web_skin(hd.v.size(), 0);   // within 2 cm of the web's middle, at rest
        {
            finger_rotations(generic, g.right, R);
            skin(hd, R, MatrixIdentity(), pts);
            const Vector3 web = centroid(WEB);
            for (size_t i = 0; i < hd.v.size(); ++i) web_skin[i] = Vector3Distance(pts[i], web) < 0.02f;
        }
        Matrix L[J_COUNT];
        auto close = [&](float* q, const Matrix& to_gun) {
            struct Closing { int f; float* c; bool moving[3]; };
            Closing fs[4];
            int n = 0;
            for (int f = F_INDEX; f <= F_LITTLE; ++f)
                if (g.closing & (1u << unsigned(f))) {
                    float* c = q + 6 + (f - 1) * 4;
                    c[0] = -0.45f; c[1] = 0.05f; c[2] = 0.03f; c[3] = 0;   // open, bent back off the gun
                    fs[n++] = {f, c, {true, true, true}};
                }
            const float pace[3] = {1.0f, 1.1f, 0.75f}, top[3] = {1.6f, 1.85f, 1.3f};
            float before[4][3];   // the nearest each segment came to the gun, the step before
            auto nearest = [&](const Closing& cl, float* d) {
                d[0] = d[1] = d[2] = 1;
                for (int vi : finger_verts[cl.f]) {
                    const HandVert& hv = hd.v[size_t(vi)];
                    d[hv.seg % 3] = std::min(d[hv.seg % 3], g.field->at(place(hv, L, to_gun)));
                }
            };
            finger_rotations(q, g.right, R);
            frames(hd, R, L);
            for (int i = 0; i < n; ++i) nearest(fs[i], before[i]);
            for (int step = 0; step < 90; ++step) {
                float was[4][3];
                bool any = false;
                for (int i = 0; i < n; ++i) {
                    std::copy(fs[i].c, fs[i].c + 3, was[i]);
                    for (int k = 0; k < 3; ++k)
                        if (fs[i].moving[k]) { fs[i].c[k] = std::min(top[k], fs[i].c[k] + 0.03f * pace[k]); any = true; }
                }
                if (!any) break;
                finger_rotations(q, g.right, R);
                frames(hd, R, L);
                for (int i = 0; i < n; ++i) {
                    Closing& cl = fs[i];
                    if (!cl.moving[0] && !cl.moving[1] && !cl.moving[2]) continue;
                    float d[3];
                    nearest(cl, d);
                    for (int k = 2; k >= 0; --k) {
                        const bool onto = d[k] < before[i][k];   // closing onto something, not away from it
                        if (onto && d[k] < -1.0f * MM) {   // sunk in: take the step back for this segment's joints and stop them
                            for (int m = 0; m <= k; ++m) { cl.c[m] = was[i][m]; cl.moving[m] = false; }
                        } else if (onto && d[k] <= 0.3f * MM) {   // touching: it and the joints before it hold
                            for (int m = 0; m <= k; ++m) cl.moving[m] = false;
                        }
                    }
                    for (int k = 0; k < 3; ++k) {
                        if (cl.c[k] >= top[k]) cl.moving[k] = false;
                        before[i][k] = d[k];
                    }
                }
            }
        };
        // The cost, term by term.
        struct Terms { float pen[16], wrap[16], clear[16], aim, seat, nature[5], worst, wrist; } T{};
        // How the wrist must bend for the forearm to come in the way the goal says: (ulnar
        // deviation, flexion), radians. In the wrist's frame (the rest pose's axes, the hand hanging
        // thumb forward): up the unbent forearm `n`. Tip the hand toward its little finger and,
        // seen from the hand, the forearm leans the other way from its line: toward the little
        // finger's side (back, +z). Bend the hand toward the palm and the forearm leans toward the
        // palm's side.
        const Vector3 n = Vector3Normalize(Vector3Subtract(rest_[g.right ? J_ELB_R : J_ELB_L], rest_[g.right ? J_WRI_R : J_WRI_L]));
        const Vector3 pn_hand = palm_normal(g.right);
        const Vector3 thumb_side = Vector3Normalize(Vector3Subtract({0, 0, -1}, Vector3Scale(n, -n.z)));
        const Vector3 palm_side = Vector3Normalize(Vector3Subtract(pn_hand, Vector3Add(Vector3Scale(n, Vector3DotProduct(pn_hand, n)),
                                                                                         Vector3Scale(thumb_side, Vector3DotProduct(pn_hand, thumb_side)))));
        auto wrist_bend = [&](const Matrix& hold) {
            const Vector3 f = Vector3Normalize(Vector3Subtract(Vector3Transform(g.forearm, hold), Vector3Transform({0, 0, 0}, hold)));   // gun -> wrist
            const float along = Vector3DotProduct(f, n);
            return Vector2{std::atan2(-Vector3DotProduct(f, thumb_side), along), std::atan2(Vector3DotProduct(f, palm_side), along)};
        };
        bool no_close = false;   // (debugging: show the fingers as they start)
        auto terms = [&](float* q) {
            const Matrix hold = hold_of(q, h0, g.pivot), to_gun = MatrixInvert(hold);
            if (!no_close) close(q, to_gun);
            finger_rotations(q, g.right, R);
            skin(hd, R, hold, pts);
            float seg_min[16], seg_any[16];
            std::fill(seg_min, seg_min + 16, 1.0f);
            std::fill(seg_any, seg_any + 16, 1.0f);
            std::fill(T.pen, T.pen + 16, 0.0f);
            T.worst = 0;
            for (size_t i = 0; i < pts.size(); ++i) {
                const HandVert& hv = hd.v[i];
                if (hv.seg < 0) continue;   // a knuckle's centre, not skin
                const float sd = g.field->at(pts[i]);
                const float give = web_skin[i] ? 2.5f * MM : 0.8f * MM;   // flesh gives a millimetre; the web of the hand more
                const float in = std::max(0.0f, -sd - give) / MM;
                T.pen[hv.seg] += 2 * in * in;
                T.worst = std::max(T.worst, -sd);
                seg_any[hv.seg] = std::min(seg_any[hv.seg], sd);
                if (hv.palmar) seg_min[hv.seg] = std::min(seg_min[hv.seg], sd);
            }
            for (int sg = 0; sg < 16; ++sg) {
                const float gap = (g.wrap & (1u << unsigned(sg))) ? std::max(0.0f, seg_min[sg] - 0.3f * MM) / MM : 0.0f;
                const float c = (g.clear & (1u << unsigned(sg))) ? std::max(0.0f, 2.0f * MM - seg_any[sg]) / MM : 0.0f;
                T.wrap[sg] = gap * gap;
                T.clear[sg] = c * c;
            }
            T.seat = 0;   // the first guess's points: a rough place to start from, no more
            const Named seats[3] = {WEB, PALM, HEEL};
            for (int i = 0; i < 3; ++i) {
                const float d = Vector3Distance(centroid(seats[i]), seat[i]) / (5 * MM);
                T.seat += d * d;
            }
            T.aim = 0;
            for (const Target& t : g.targets) {
                const float d = Vector3Distance(centroid(t.what), t.at) / t.tol;
                T.aim += d * d;
            }
            T.wrist = 0;
            if (Vector3LengthSqr(g.forearm) > 0) {   // how the wrist must bend for the arm to come in that way
                const Vector2 b = wrist_bend(hold);
                const float over_dev = std::max(0.0f, std::max(b.x - 0.52f, -0.26f - b.x)), over_flex = std::max(0.0f, std::max(b.y - 0.87f, -0.79f - b.y));
                T.wrist = (over_dev * over_dev + over_flex * over_flex) / (0.1f * 0.1f);   // a tenth of a radian past: as bad as a target missed by its tolerance
                T.aim += T.wrist;
            }
            for (int f = 0; f < 4; ++f) {   // the last two joints of a finger bend together (one tendon works both)
                const float* c = q + 6 + f * 4;
                T.nature[f + 1] = (g.closing & (1u << unsigned(f + 1))) ? 0.0f : 4 * (c[2] - 0.65f * c[1]) * (c[2] - 0.65f * c[1]) + 2 * c[3] * c[3];
            }
            T.nature[0] = 0.3f * (q[22] * q[22] + q[23] * q[23] + q[24] * q[24]);
        };
        auto sum = [&](unsigned segs, bool aim, bool nature) {
            float c = 0;
            for (int sg = 0; sg < 16; ++sg)
                if (segs & (1u << unsigned(sg))) c += T.pen[sg] + T.wrap[sg] + T.clear[sg];
            c += aim ? T.aim + 0.5f * T.seat : T.seat;   // the seat stays: it's where the technique puts the palm
            if (nature) for (float n : T.nature) c += n;
            return c;
        };
        const unsigned all = 0xFFFFu;
        float lo[K], hi[K], q[K];
        for (int k = 0; k < 3; ++k) { lo[k] = -0.7f; hi[k] = 0.7f; }
        for (int k = 3; k < 6; ++k) { lo[k] = -0.035f; hi[k] = 0.035f; }
        for (int f = 0; f < 4; ++f) {
            float* l = lo + 6 + f * 4, * h = hi + 6 + f * 4;
            l[0] = -0.3f; h[0] = 1.65f; l[1] = 0; h[1] = 1.9f; l[2] = 0; h[2] = 1.35f; l[3] = -0.3f; h[3] = 0.3f;
        }
        for (int k = 22; k < 25; ++k) { lo[k] = -2.2f; hi[k] = 2.2f; }   // the thumb's root swings a long way (opposition)
        lo[25] = -0.5f; hi[25] = 1.3f;
        lo[26] = -0.5f; hi[26] = 0.5f;
        lo[27] = -0.4f; hi[27] = 1.4f;
        std::copy(generic, generic + K, q);
        unsigned rng = 0x9E3779B9u;
        auto rnd = [&rng]() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return float(rng & 0xFFFFFF) / 16777215.0f; };
        // What the search moves: the gun in the hand, and the fingers that don't close by themselves.
        std::vector<int> searched = {0, 1, 2, 3, 4, 5, 22, 23, 24, 25, 26, 27};
        for (int f = F_INDEX; f <= F_LITTLE; ++f)
            if (!(g.closing & (1u << unsigned(f))))
                for (int k = 0; k < 4; ++k) searched.push_back(6 + (f - 1) * 4 + k);
        // A run: shake the chosen parameters, keep what helps (judged on the segments in `segs`),
        // shake less and less.
        auto stage = [&](const std::vector<int>& ks, unsigned segs, bool aim, int iters, float step0) {
            terms(q);
            float cur = sum(segs, aim, true), step = step0;
            for (int it = 0; it < iters; ++it) {
                float t[K];
                std::copy(q, q + K, t);
                const int n = 1 + int(rnd() * 2.99f);
                for (int m = 0; m < n; ++m) {
                    const int k = ks[std::min(ks.size() - 1, size_t(rnd() * float(ks.size())))];
                    t[k] = std::clamp(t[k] + (rnd() * 2 - 1) * step * (hi[k] - lo[k]), lo[k], hi[k]);
                }
                terms(t);
                const float c = sum(segs, aim, true);
                if (c < cur) { cur = c; std::copy(t, t + K, q); }
                if (it % (iters / 8) == iters / 8 - 1) step *= 0.6f;
            }
            terms(q);
            return cur;
        };
        const bool quick = std::getenv("DW_FIT_QUICK") != nullptr;
        const int N = quick ? 200 : 1500;
        const bool trace = std::getenv("DW_FIT_TRACE") != nullptr;
        const Vector3 o = g.field == &pistol_field || g.field == &support_field ? P(0, 0, 0) : S(0, 0, 0);
        auto mm = [&](Vector3 p) { return Vector3{(o.y - p.y) / MM, (o.z - p.z) / MM, p.x / MM}; };
        const char* keep_stage = std::getenv("DW_FIT_STAGE");   // write out this stage, not the last (debugging)
        float kept[K];
        bool have_kept = false;
        auto show = [&](const char* what) {
            if (keep_stage && std::string(keep_stage) == what) { std::copy(q, q + K, kept); have_kept = true; }
            if (!trace) return;
            terms(q);
            std::snprintf(line, sizeof line, "  [%s] seat %.1f aim %.1f;", what, T.seat, T.aim);
            report += line;
            report += " sinking by segment:";
            for (int sg = 0; sg < 16; ++sg)
                if (T.pen[sg] > 0.5f) { std::snprintf(line, sizeof line, " %d:%.0f", sg, T.pen[sg]); report += line; }
            report += "; gaps:";
            for (int sg = 0; sg < 16; ++sg)
                if (T.wrap[sg] > 0.5f) { std::snprintf(line, sizeof line, " %d:%.0f", sg, std::sqrt(T.wrap[sg])); report += line; }
            report += ";";
            const Named nm[] = {WEB, PALM, HEEL, INDEX_PAD, THUMB_TIP, MIDDLE_TIP};
            for (Named n : nm) {
                const Vector3 c = mm(centroid(n));
                std::snprintf(line, sizeof line, " %s (%.0f %.0f %.0f)", NAMED_NAME[n], c.x, c.y, c.z);
                report += line;
            }
            report += "\n";
        };
        if (keep_stage && std::string(keep_stage) == "open") {   // the first guess, fingers as they start
            std::copy(generic, generic + K, kept);
            for (int f = F_INDEX; f <= F_LITTLE; ++f) { float* c = kept + 6 + (f - 1) * 4; c[0] = -0.1f; c[1] = 0.05f; c[2] = 0.03f; }
            have_kept = true;
        }
        show("first guess");
        // 1. Seat the palm, the gripping fingers closing round whatever they meet. (Not the thumb or
        //    the trigger finger: at rest the thumb lies along the forefinger, through the frame,
        //    until it's posed in 2.)
        unsigned closing_segs = 1u << PALM_SEG, posed_segs = 0;
        std::vector<int> posed = {22, 23, 24, 25, 26, 27};
        for (int f = 0; f < 5; ++f) {
            const unsigned three = bit(f, 0) | bit(f, 1) | bit(f, 2);
            if (f > 0 && (g.closing & (1u << unsigned(f)))) closing_segs |= three;
            else posed_segs |= three;
            if (f > 0 && !(g.closing & (1u << unsigned(f))))
                for (int k = 0; k < 4; ++k) posed.push_back(6 + (f - 1) * 4 + k);
        }
        stage({0, 1, 2, 3, 4, 5}, closing_segs, false, 2 * N, 0.06f);
        show("seated");
        // 2. The thumb and the trigger finger, the gun where it sits (a few starts: a thumb can go
        //    round either way).
        float best[K], best_c = 1e30f;
        for (int restart = 0; restart < 20; ++restart) {
            float start[K];
            std::copy(q, q + K, start);
            if (restart > 0)
                for (int k : posed) q[k] = lo[k] + (hi[k] - lo[k]) * rnd();
            // First to the targets as if the gun weren't there (a thumb that must go round the back of
            // the grip can't get there through it), then settled where it's clear of the gun.
            stage(posed, 0, true, N / 2, 0.25f);
            const float c = stage(posed, posed_segs, true, N, 0.08f);
            if (c < best_c) { best_c = c; std::copy(q, q + K, best); }
            std::copy(start, start + K, q);
        }
        std::copy(best, best + K, q);
        show("thumb");
        // 3. Everything together, in small steps.
        stage(searched, all, true, 3 * N, 0.05f);
        show("fitted");
        if (have_kept) {
            std::copy(kept, kept + K, q);
            no_close = std::string(keep_stage) == "open";
        }
        terms(q);
        const float total = sum(all, true, true);
        Result r{};
        r.hold = hold_of(q, h0, g.pivot);
        finger_rotations(q, g.right, R);
        for (int f = 0; f < 5; ++f)
            for (int k = 0; k < 3; ++k) {
                const Matrix& m = R[finger_joint(g.right, f, k)];   // as this rig's angles (z, then x, then y)
                r.joints[f * 3 + k] = {std::asin(std::clamp(-m.m9, -1.0f, 1.0f)), std::atan2(m.m8, m.m10), std::atan2(m.m1, m.m5)};
            }
        r.cost = total;
        r.worst_mm = T.worst / MM;
        results.push_back(r);
        float pen = 0, wrap = 0, clear = 0;
        for (int sg = 0; sg < 16; ++sg) { pen += T.pen[sg]; wrap += T.wrap[sg]; clear += T.clear[sg]; }
        std::snprintf(line, sizeof line, "%s: cost %.3f (sinking %.3f, gaps %.3f, trigger finger %.3f, targets %.3f); deepest %.1f mm\n",
                      g.name, total, pen, wrap, clear, T.aim, r.worst_mm);
        report += line;
        if (Vector3LengthSqr(g.forearm) > 0) {
            const Vector2 b = wrist_bend(r.hold);
            std::snprintf(line, sizeof line, "  the wrist, for the arm to come in as it does: %.0f deg toward the little finger, %.0f toward the palm\n",
                          b.x * RAD2DEG, b.y * RAD2DEG);
            report += line;
        }
        for (const Target& t : g.targets) {
            const Vector3 c = mm(centroid(t.what));
            std::snprintf(line, sizeof line, "  %-11s %.1f mm off (at u %.0f v %.0f w %.0f)\n", NAMED_NAME[t.what],
                          Vector3Distance(centroid(t.what), t.at) / MM, c.x, c.y, c.z);
            report += line;
        }
        std::string gaps = "  gaps by segment (mm):";
        for (int sg = 0; sg < 16; ++sg)
            if (g.wrap & (1u << unsigned(sg))) { std::snprintf(line, sizeof line, " %d:%.1f", sg, std::sqrt(T.wrap[sg])); gaps += line; }
        report += gaps + "\n";
        if (g.flesh_into) {   // this hand, solid, for the other one to grip over
            const std::vector<FleshCapsule> caps = hand_capsules(hd, R, r.hold);
            draw_into(*g.flesh_into, caps);
            if (trace)
                for (const FleshCapsule& c : caps) {
                    const Vector3 a = mm(c.a), b = mm(c.b);
                    std::snprintf(line, sizeof line, "  flesh (%.0f %.0f %.0f)-(%.0f %.0f %.0f) r %.1f\n", a.x, a.y, a.z, b.x, b.y, b.z, c.r / MM);
                    report += line;
                }
        }
    }

    // ── Out to the pose tables ──────────────────────────────────────────────────
    std::ofstream out(out_path);
    out << "// damned_waters/engine/src/grips_fitted.inc\n"
           "// Purpose: how the survivor holds his guns. Written by `damned_waters --fitgrips` (grip_fit.cpp):\n"
           "// change the goals there (or a gun, or his hands) and run it again rather than editing this.\n"
           "// Each grip: where the gun sits in that hand (gun space -> the wrist's), and the hand's finger\n"
           "// joints (thumb, index, middle, ring, little; each from the knuckle out) as this rig's angles.\n";
    for (size_t i = 0; i < results.size(); ++i) {
        const Result& r = results[i];
        const Matrix& m = r.hold;
        char buf[4096];
        int n = std::snprintf(buf, sizeof buf,
                              "inline constexpr Grip %s = {{%.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, %.6ff, "
                              "%.6ff, %.6ff, %.6ff, %.6ff},\n    {",
                              goals[i].id, m.m0, m.m4, m.m8, m.m12, m.m1, m.m5, m.m9, m.m13, m.m2, m.m6, m.m10, m.m14, m.m3, m.m7, m.m11, m.m15);
        for (int k = 0; k < 15; ++k)
            n += std::snprintf(buf + n, sizeof buf - size_t(n), "{%.4ff, %.4ff, %.4ff}%s", r.joints[k].x, r.joints[k].y, r.joints[k].z,
                               k == 14 ? "}};\n" : (k % 3 == 2 ? ",\n     " : ", "));
        out << buf;
    }
    report += "written: " + out_path + "\n";
    return report;
}

}  // namespace dw
