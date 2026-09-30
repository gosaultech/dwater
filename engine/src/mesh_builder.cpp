// damned_waters/engine/src/mesh_builder.cpp
// Purpose: see mesh_builder.hpp.
#include "dw/mesh_builder.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <random>

namespace dw {
namespace {
constexpr float TAU = 6.28318530718f;
Vector3 safe_norm(Vector3 v, Vector3 fallback) {
    float l = Vector3Length(v);
    if (l > 1e-8f) return Vector3Scale(v, 1.0f / l);
    float lf = Vector3Length(fallback);
    return lf > 1e-8f ? Vector3Scale(fallback, 1.0f / lf) : Vector3{0, 1, 0};
}
// Direction part of a rigid (or uniformly scaled) transform.
Vector3 rotate(Vector3 v, const Matrix& m) {
    return {m.m0 * v.x + m.m4 * v.y + m.m8 * v.z, m.m1 * v.x + m.m5 * v.y + m.m9 * v.z, m.m2 * v.x + m.m6 * v.y + m.m10 * v.z};
}
}  // namespace

void MeshData::append(const MeshData& s, const Matrix& xf) {
    const size_t n = s.count();
    pos.reserve(pos.size() + n * 3); nrm.reserve(nrm.size() + n * 3);
    for (size_t i = 0; i < n; ++i) {
        Vector3 p = Vector3Transform({s.pos[i * 3], s.pos[i * 3 + 1], s.pos[i * 3 + 2]}, xf);
        Vector3 nn = safe_norm(rotate({s.nrm[i * 3], s.nrm[i * 3 + 1], s.nrm[i * 3 + 2]}, xf), {0, 1, 0});
        pos.insert(pos.end(), {p.x, p.y, p.z});
        nrm.insert(nrm.end(), {nn.x, nn.y, nn.z});
    }
    // Surface coordinates stay as they were, so procedural detail doesn't swim on the moved copy.
    uv.insert(uv.end(), s.uv.begin(), s.uv.end());
    tan.insert(tan.end(), s.tan.begin(), s.tan.end());
    col.insert(col.end(), s.col.begin(), s.col.end());
}

void MeshBuilder::tri(const Vector3* p, const Vector3* n, const Color* c, float mat) {
    for (int i = 0; i < 3; ++i) {
        Vector3 P = Vector3Transform(p[i], xf_), N = safe_norm(rotate(n[i], xf_), {0, 1, 0});
        d_.pos.insert(d_.pos.end(), {P.x, P.y, P.z});
        d_.nrm.insert(d_.nrm.end(), {N.x, N.y, N.z});
        d_.uv.insert(d_.uv.end(), {mat, ao_});
        d_.tan.insert(d_.tan.end(), {P.x, P.y, P.z, 0.0f});   // surface coord = object space
        d_.col.insert(d_.col.end(), {c[i].r, c[i].g, c[i].b, c[i].a});
    }
}

void MeshBuilder::grid(const Grid& g, bool close_top, bool close_bottom, bool wrap, const PaintGrid* paint) {
    const int R = int(g.size()), C = int(g[0].size());
    std::vector<Vector3> centre(R);
    for (int i = 0; i < R; ++i) {
        if (wrap) {   // ring: its average is its centre
            Vector3 s{};
            for (auto& p : g[i]) s = Vector3Add(s, p);
            centre[i] = Vector3Scale(s, 1.0f / C);
        } else {      // open panel: the middle of its bounding box sits near the body it hangs around
            Vector3 lo = g[i][0], hi = g[i][0];
            for (auto& p : g[i]) { lo = Vector3Min(lo, p); hi = Vector3Max(hi, p); }
            centre[i] = Vector3Scale(Vector3Add(lo, hi), 0.5f);
        }
    }
    Vector3 all{};   // whole-shape centroid: fallback "outward" at poles where a ring collapses
    for (auto& c : centre) all = Vector3Add(all, c);
    all = Vector3Scale(all, 1.0f / R);
    Grid n(R, std::vector<Vector3>(C));
    for (int i = 0; i < R; ++i)
        for (int j = 0; j < C; ++j) {
            int jn = wrap ? (j + 1) % C : std::min(j + 1, C - 1), jp = wrap ? (j + C - 1) % C : std::max(j - 1, 0);
            Vector3 du = Vector3Subtract(g[i][jn], g[i][jp]);
            Vector3 dv = Vector3Subtract(g[std::min(i + 1, R - 1)][j], g[std::max(i - 1, 0)][j]);
            Vector3 out = Vector3Subtract(g[i][j], centre[i]);
            if (Vector3Length(out) < 1e-5f) out = Vector3Subtract(g[i][j], all);
            Vector3 nn = safe_norm(Vector3CrossProduct(du, dv), out);
            if (Vector3DotProduct(nn, out) < 0) nn = Vector3Negate(nn);
            n[i][j] = nn;
        }
    auto col_at = [&](int i, int j) { return paint ? (*paint)[i][j].col : col_; };
    const int cols = wrap ? C : C - 1;
    for (int i = 0; i + 1 < R; ++i)
        for (int j = 0; j < cols; ++j) {
            int k = (j + 1) % C;
            float mat = mat_;
            if (paint) {
                const auto& P = *paint;
                if (P[i][j].mat < 0 || P[i][k].mat < 0 || P[i + 1][j].mat < 0 || P[i + 1][k].mat < 0) continue;
                mat = float(P[i][j].mat);
            }
            const Vector3 a[3] = {g[i][j], g[i][k], g[i + 1][k]}, na[3] = {n[i][j], n[i][k], n[i + 1][k]};
            const Color ca[3] = {col_at(i, j), col_at(i, k), col_at(i + 1, k)};
            tri(a, na, ca, mat);
            const Vector3 b[3] = {g[i][j], g[i + 1][k], g[i + 1][j]}, nb[3] = {n[i][j], n[i + 1][k], n[i + 1][j]};
            const Color cb[3] = {col_at(i, j), col_at(i + 1, k), col_at(i + 1, j)};
            tri(b, nb, cb, mat);
        }
    auto cap = [&](int row, bool first) {
        // Outward = away from the neighbouring row; wind each fan triangle to face that way.
        Vector3 c = centre[row], cn = safe_norm(Vector3Subtract(c, centre[first ? std::min(row + 1, R - 1) : std::max(row - 1, 0)]), {0, first ? 1.f : -1.f, 0});
        for (int j = 0; j < C; ++j) {
            int k = (j + 1) % C;
            bool flip = Vector3DotProduct(Vector3CrossProduct(Vector3Subtract(g[row][j], c), Vector3Subtract(g[row][k], c)), cn) < 0;
            int a = flip ? k : j, b = flip ? j : k;
            const Vector3 p[3] = {c, g[row][a], g[row][b]}, nn[3] = {cn, n[row][a], n[row][b]};
            const Color cc[3] = {col_at(row, a), col_at(row, a), col_at(row, b)};
            tri(p, nn, cc, mat_);
        }
    };
    if (wrap && close_top) cap(0, true);
    if (wrap && close_bottom) cap(R - 1, false);
}

void MeshBuilder::ellipsoid(Vector3 c, Vector3 r, int segs, int rings, const Bump& bump, const Painter& paint) {
    Grid g(rings + 1, std::vector<Vector3>(segs));
    PaintGrid pg;
    if (paint) pg.assign(rings + 1, std::vector<Paint>(segs));
    for (int i = 0; i <= rings; ++i) {
        float phi = PI * float(i) / rings;   // 0 = top
        for (int j = 0; j < segs; ++j) {
            float th = TAU * float(j) / segs;   // 0 = front (-Z), then toward +X
            Vector3 d{std::sin(phi) * std::sin(th), std::cos(phi), -std::sin(phi) * std::cos(th)};
            float off = bump ? bump(d) : 0.0f;
            g[i][j] = {c.x + d.x * (r.x + off), c.y + d.y * (r.y + off), c.z + d.z * (r.z + off)};
            if (paint) pg[i][j] = paint(d);
        }
    }
    grid(g, false, false, true, paint ? &pg : nullptr);
}

void MeshBuilder::tube(Vector3 a, Vector3 b, float r0, float r1, int sides) { chain({a, b}, {r0, r1}, sides); }

Outline& Outline::arc(float cy, float cz, float r, float a0, float a1, int n) {
    for (int i = 0; i <= n; ++i) {
        const float a = a0 + (a1 - a0) * float(i) / float(n);
        p.push_back({cy + r * std::cos(a), cz + r * std::sin(a)});
    }
    return *this;
}

Outline& Outline::curve(float ky, float kz, float y, float z, int n) {
    const Vector2 a = p.empty() ? Vector2{ky, kz} : p.back();
    for (int i = 1; i <= n; ++i) {
        const float t = float(i) / float(n), u = 1 - t;
        p.push_back({u * u * a.x + 2 * u * t * ky + t * t * y, u * u * a.y + 2 * u * t * kz + t * t * z});
    }
    return *this;
}

Outline Outline::scaled(float k, float dy, float dz) const {
    Outline o;
    for (const Vector2& v : p) o.p.push_back({v.x * k + dy, v.y * k + dz});
    return o;
}

namespace {
float cross2(Vector2 a, Vector2 b) { return a.x * b.y - a.y * b.x; }
bool in_triangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c) {
    const float d1 = cross2(Vector2Subtract(b, a), Vector2Subtract(p, a)), d2 = cross2(Vector2Subtract(c, b), Vector2Subtract(p, b)),
                d3 = cross2(Vector2Subtract(a, c), Vector2Subtract(p, c));
    return d1 >= 0 && d2 >= 0 && d3 >= 0;
}
// Ear clipping: a simple counter-clockwise polygon into triangles (index triples).
std::vector<std::array<int, 3>> triangulate(const std::vector<Vector2>& poly) {
    std::vector<int> idx(poly.size());
    for (size_t i = 0; i < idx.size(); ++i) idx[i] = int(i);
    std::vector<std::array<int, 3>> out;
    while (idx.size() > 3) {
        bool clipped = false;
        const size_t m = idx.size();
        for (size_t i = 0; i < m && !clipped; ++i) {
            const int a = idx[(i + m - 1) % m], b = idx[i], c = idx[(i + 1) % m];
            const Vector2 A = poly[size_t(a)], B = poly[size_t(b)], C = poly[size_t(c)];
            if (cross2(Vector2Subtract(B, A), Vector2Subtract(C, B)) <= 1e-12f) continue;   // a reflex corner: not an ear
            bool inside = false;
            for (int k : idx)
                if (k != a && k != b && k != c && in_triangle(poly[size_t(k)], A, B, C)) { inside = true; break; }
            if (inside) continue;
            out.push_back({a, b, c});
            idx.erase(idx.begin() + long(i));
            clipped = true;
        }
        if (!clipped) break;   // degenerate (it crosses itself): leave the rest open
    }
    if (idx.size() == 3) out.push_back({idx[0], idx[1], idx[2]});
    return out;
}
}  // namespace

void MeshBuilder::slab(const std::vector<Vector2>& outline, float xc, float hw, float round, int steps) {
    std::vector<Vector2> P = outline;
    if (P.size() > 1 && Vector2Distance(P.front(), P.back()) < 1e-7f) P.pop_back();
    const int n = int(P.size());
    if (n < 3) return;
    float area = 0;
    for (int i = 0; i < n; ++i) area += cross2(P[size_t(i)], P[size_t((i + 1) % n)]);
    if (area < 0) std::reverse(P.begin(), P.end());   // counter-clockwise in (y, z): the outside is to each edge's right
    round = std::clamp(round, 0.0f, hw * 0.95f);
    steps = round > 0 ? std::max(1, steps) : 0;
    const size_t N = P.size();
    std::vector<Vector2> en(N), vn(N), miter(N);
    std::vector<bool> sharp(N);
    for (int i = 0; i < n; ++i) {
        const Vector2 d = Vector2Normalize(Vector2Subtract(P[size_t((i + 1) % n)], P[size_t(i)]));
        en[size_t(i)] = {d.y, -d.x};   // outward
    }
    for (int i = 0; i < n; ++i) {
        const Vector2 a = en[size_t((i + n - 1) % n)], b = en[size_t(i)];
        Vector2 m = Vector2Add(a, b);
        m = Vector2Length(m) > 1e-6f ? Vector2Normalize(m) : b;
        miter[size_t(i)] = Vector2Scale(m, 1.0f / std::max(Vector2DotProduct(m, b), 0.35f));   // very sharp corners don't spike
        vn[size_t(i)] = m;
        sharp[size_t(i)] = Vector2DotProduct(a, b) < 0.819f;   // cos 35 degrees
    }
    // Rings across the width: the -x face's outline, round the edge to its equator, straight across,
    // and round again to the +x face.
    struct Ring { float x, inset, c, s, side; };
    std::vector<Ring> rings;
    for (int k = steps; k >= 0; --k) {
        const float t = steps ? 0.5f * PI * float(k) / float(steps) : 0.0f;
        rings.push_back({xc - (hw - round + round * std::sin(t)), round * (1 - std::cos(t)), std::cos(t), std::sin(t), -1});
    }
    for (int k = 0; k <= steps; ++k) {
        const float t = steps ? 0.5f * PI * float(k) / float(steps) : 0.0f;
        rings.push_back({xc + (hw - round + round * std::sin(t)), round * (1 - std::cos(t)), std::cos(t), std::sin(t), 1});
    }
    auto at = [&](const Ring& r, int i) {
        const Vector2 q = Vector2Subtract(P[size_t(i)], Vector2Scale(miter[size_t(i)], r.inset));
        return Vector3{r.x, q.x, q.y};
    };
    auto nrm = [](const Ring& r, Vector2 n2) { return Vector3Normalize({r.side * r.s, n2.x * r.c, n2.y * r.c}); };
    const Color cols[3] = {col_, col_, col_};
    auto emit = [&](Vector3 a, Vector3 b, Vector3 c, Vector3 na, Vector3 nb, Vector3 nc) {
        const Vector3 face = Vector3CrossProduct(Vector3Subtract(b, a), Vector3Subtract(c, a));
        if (Vector3DotProduct(face, Vector3Add(Vector3Add(na, nb), nc)) < 0) { std::swap(b, c); std::swap(nb, nc); }
        const Vector3 p[3] = {a, b, c}, nn[3] = {na, nb, nc};
        tri(p, nn, cols, mat_);
    };
    for (size_t k = 0; k + 1 < rings.size(); ++k) {
        const Ring &r0 = rings[k], &r1 = rings[k + 1];
        for (int i = 0; i < n; ++i) {
            const int j = (i + 1) % n;
            const Vector2 ni = sharp[size_t(i)] ? en[size_t(i)] : vn[size_t(i)], nj = sharp[size_t(j)] ? en[size_t(i)] : vn[size_t(j)];
            const Vector3 a = at(r0, i), b = at(r0, j), c = at(r1, j), d = at(r1, i);
            emit(a, b, c, nrm(r0, ni), nrm(r0, nj), nrm(r1, nj));
            emit(a, c, d, nrm(r0, ni), nrm(r1, nj), nrm(r1, ni));
        }
    }
    // The flat faces: the outline inset by the rounding, fanned into triangles.
    std::vector<Vector2> face(N);
    for (int i = 0; i < n; ++i) face[size_t(i)] = Vector2Subtract(P[size_t(i)], Vector2Scale(miter[size_t(i)], round));
    const auto tris = triangulate(face);
    for (float side : {-1.0f, 1.0f}) {
        const float x = xc + side * hw;
        const Vector3 nn{side, 0, 0};
        for (const auto& t : tris)
            emit({x, face[size_t(t[0])].x, face[size_t(t[0])].y}, {x, face[size_t(t[1])].x, face[size_t(t[1])].y},
                 {x, face[size_t(t[2])].x, face[size_t(t[2])].y}, nn, nn, nn);
    }
}

void MeshBuilder::box(Vector3 c, Vector3 half, float k, int segs, int rings) {
    auto shape = [k](float v) { return (v < 0 ? -1.0f : 1.0f) * std::pow(std::fabs(v), k); };
    Grid g(rings + 1, std::vector<Vector3>(segs));
    for (int i = 0; i <= rings; ++i) {
        float phi = PI * float(i) / rings;
        for (int j = 0; j < segs; ++j) {
            float th = TAU * float(j) / segs;
            Vector3 d{std::sin(phi) * std::sin(th), std::cos(phi), -std::sin(phi) * std::cos(th)};
            g[i][j] = {c.x + shape(d.x) * half.x, c.y + shape(d.y) * half.y, c.z + shape(d.z) * half.z};
        }
    }
    grid(g);
}

void MeshBuilder::chain(const std::vector<Vector3>& pts, const std::vector<float>& radii, int sides, float flatten) {
    Grid g;
    Vector3 ref{1, 0, 0};
    for (size_t i = 0; i < pts.size(); ++i) {
        Vector3 t = Vector3Normalize(Vector3Subtract(pts[std::min(i + 1, pts.size() - 1)], pts[i > 0 ? i - 1 : 0]));
        if (std::fabs(Vector3DotProduct(t, ref)) > 0.9f) ref = {0, 0, 1};
        Vector3 x = Vector3Normalize(Vector3CrossProduct(t, ref)), z = Vector3CrossProduct(t, x);
        std::vector<Vector3> row(sides);
        for (int j = 0; j < sides; ++j) {
            float th = TAU * float(j) / sides;
            row[j] = Vector3Add(pts[i], Vector3Add(Vector3Scale(x, std::cos(th) * radii[i]), Vector3Scale(z, std::sin(th) * radii[i] * flatten)));
        }
        g.push_back(row);
    }
    grid(g, true, true);
}

void MeshBuilder::drape(Vector3 top, Vector2 rt, Vector2 rb, float length, int rings, int segs, int folds,
                        float fold_amp, const std::function<float(float)>& length_scale, unsigned seed, float th0, float th1) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<float> U(0.0f, TAU);
    const float p0 = U(rng), p1 = U(rng);
    const bool full = th1 - th0 >= TAU - 1e-3f;
    const int cols = full ? segs : segs + 1;
    Grid g(rings + 1, std::vector<Vector3>(cols));
    for (int i = 0; i <= rings; ++i) {
        float t = float(i) / rings, e = std::pow(t, 0.8f);
        for (int j = 0; j < cols; ++j) {
            float th = th0 + (th1 - th0) * float(j) / segs;
            float L = length * (length_scale ? length_scale(th) : 1.0f);
            float fold = 1.0f + fold_amp * t * (std::sin(th * folds + p0) * 0.65f + std::sin(th * folds * 2.3f + p1) * 0.35f);
            float rx = (rt.x + (rb.x - rt.x) * e) * fold, rz = (rt.y + (rb.y - rt.y) * e) * fold;
            g[i][j] = {top.x + std::sin(th) * rx, top.y - t * L, top.z - std::cos(th) * rz};
        }
    }
    grid(g, false, false, full);
}

// ── Sweeps ──────────────────────────────────────────────────────────────────────
std::array<float, 3> Profile::at(float s) const {
    if (s <= keys.front()[0]) return {keys.front()[1], keys.front()[2], keys.front()[3]};
    for (size_t i = 1; i < keys.size(); ++i)
        if (s <= keys[i][0]) {
            const auto &a = keys[i - 1], &b = keys[i];
            float k = (s - a[0]) / std::max(b[0] - a[0], 1e-6f);
            k = k * k * (3 - 2 * k);   // smooth, so muscles swell rather than kink
            return {a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k, a[3] + (b[3] - a[3]) * k};
        }
    return {keys.back()[1], keys.back()[2], keys.back()[3]};
}

Sweep::Sweep(int rings, int sides, Profile profile, int mat, Color c, float length_hint)
    : rings_(rings), sides_(sides), prof_(std::move(profile)), mat_(mat), col_(c), length_(length_hint) { topology(); }

Sweep& Sweep::tail(float from_s, int mat, Color c) { tail_from_ = from_s; tail_mat_ = mat; tail_col_ = c; topology(); return *this; }

Sweep& Sweep::arc(float th0, float th1) { th0_ = th0; th1_ = th1; topology(); return *this; }

Sweep& Sweep::surface(Vector3 offset) { surf_off_ = offset; topology(); return *this; }
Sweep& Sweep::sculpt(SculptFn f) { sculpt_ = std::move(f); topology(); return *this; }
Sweep& Sweep::paint(PaintFn f) { paint_ = std::move(f); topology(); return *this; }

void Sweep::topology() {
    const size_t n = size_t(rings_ - 1) * sides_ * 6;
    const int C = sides_ + 1;
    data.pos.assign(n * 3, 0.0f);
    data.nrm.assign(n * 3, 0.0f);
    data.uv.clear(); data.tan.clear(); data.col.clear();
    disp_.assign(size_t(rings_) * C, 0.0f);
    gp_.assign(size_t(rings_) * C, {});
    gn_.assign(size_t(rings_) * C, {});
    if (sculpt_)
        for (int r = 0; r < rings_; ++r)
            for (int j = 0; j < C; ++j)
                disp_[size_t(r) * C + j] = sculpt_(float(r) / (rings_ - 1), th0_ + (th1_ - th0_) * float(j) / sides_);
    for (int i = 0; i + 1 < rings_; ++i)
        for (int j = 0; j < sides_; ++j) {
            const int corners[6][2] = {{i, j}, {i, j + 1}, {i + 1, j + 1}, {i, j}, {i + 1, j + 1}, {i + 1, j}};
            for (auto& ck : corners) {
                float s = float(ck[0]) / (rings_ - 1), th = th0_ + (th1_ - th0_) * float(ck[1]) / sides_;
                bool tail = s >= tail_from_ && tail_mat_ >= 0;
                Color c = tail ? tail_col_ : col_;
                if (paint_) c = paint_(s, th, c);
                auto pr = prof_.at(s);
                float ao = 0.8f + 0.2f * std::min(1.0f, std::min(s, 1.0f - s) * 6.0f);   // ends tuck into joints
                data.uv.insert(data.uv.end(), {float(tail ? tail_mat_ : mat_), ao});
                data.tan.insert(data.tan.end(), {std::sin(th) * pr[0] + surf_off_.x, s * length_ + surf_off_.y, std::cos(th) * pr[1] + surf_off_.z, 0.0f});
                data.col.insert(data.col.end(), {c.r, c.g, c.b, c.a});
            }
        }
}

void Sweep::build(const std::vector<Vector3>& pts, Vector3 right_hint, int keep) {
    // 1) Catmull-Rom through the joints, sampled finely, with arc length.
    const int n = int(pts.size()), per = 12;
    std::vector<Vector3> P(n + 2);
    P[0] = Vector3Subtract(Vector3Scale(pts[0], 2), pts[1]);
    for (int i = 0; i < n; ++i) P[i + 1] = pts[i];
    P[n + 1] = Vector3Subtract(Vector3Scale(pts[n - 1], 2), pts[n - 2]);
    std::vector<Vector3>& fine = fine_;
    fine.clear();
    for (int seg = 0; seg + 1 < n; ++seg)
        for (int k = 0; k < per; ++k) {
            float t = float(k) / per, t2 = t * t, t3 = t2 * t;
            const Vector3 &p0 = P[seg], &p1 = P[seg + 1], &p2 = P[seg + 2], &p3 = P[seg + 3];
            Vector3 v{};
            for (int a = 0; a < 3; ++a) {
                float c0 = (&p0.x)[a], c1 = (&p1.x)[a], c2 = (&p2.x)[a], c3 = (&p3.x)[a];
                (&v.x)[a] = 0.5f * (2 * c1 + (-c0 + c2) * t + (2 * c0 - 5 * c1 + 4 * c2 - c3) * t2 + (-c0 + 3 * c1 - 3 * c2 + c3) * t3);
            }
            fine.push_back(v);
        }
    fine.push_back(pts.back());
    std::vector<float>& acc = acc_;
    acc.assign(fine.size(), 0.0f);
    for (size_t i = 1; i < fine.size(); ++i) acc[i] = acc[i - 1] + Vector3Distance(fine[i], fine[i - 1]);
    const float total = std::max(acc.back(), 1e-5f);
    point_s_.resize(n);
    for (int i = 0; i < n; ++i) point_s_[i] = acc[std::min(size_t(i) * per, fine.size() - 1)] / total;
    const float cut_len = (keep >= 1 && keep < n) ? acc[size_t(keep - 1) * per] : total;
    // 2) Rings at even arc length, framed by parallel transport (no twisting). Rings past a
    //    cut: the first one lands exactly on the cut, the rest collapse onto it (invisible).
    frames_.assign(rings_, Frame{});
    size_t cur = 0;
    bool past = false;
    for (int r = 0; r < rings_; ++r) {
        float nominal = total * float(r) / (rings_ - 1), want = std::min(nominal, cut_len);
        while (cur + 2 < fine.size() && acc[cur + 1] < want) ++cur;
        float seg = std::max(acc[cur + 1] - acc[cur], 1e-6f), k = std::clamp((want - acc[cur]) / seg, 0.0f, 1.0f);
        Frame& f = frames_[r];
        f.c = Vector3Lerp(fine[cur], fine[cur + 1], k);
        f.t = safe_norm(Vector3Subtract(fine[cur + 1], fine[cur]), {0, 1, 0});
        Vector3 prev = r == 0 ? right_hint : frames_[r - 1].x;
        f.x = safe_norm(Vector3Subtract(prev, Vector3Scale(f.t, Vector3DotProduct(prev, f.t))), {1, 0, 0});
        f.z = Vector3CrossProduct(f.x, f.t);
        auto pr = prof_.at(want / total);
        f.c = Vector3Add(f.c, Vector3Scale(f.z, -pr[2]));   // forward shift (bellies, chests)
        if (past) { f.rx = f.rz = 0.0f; continue; }
        f.rx = pr[0]; f.rz = pr[1];
        if (nominal >= cut_len - 1e-6f) { past = true; cut_ = f; }
    }
    if (!past) cut_ = frames_.back();
    // 3) Grid of surface points (profile + sculpt), normals from the neighbours (so the
    //    profile's slope and the sculpt both shade), then the fixed-topology triangle soup.
    const int C = sides_ + 1;
    const bool full = th1_ - th0_ >= TAU - 1e-3f;
    for (int r = 0; r < rings_; ++r) {
        const Frame& f = frames_[r];
        for (int j = 0; j < C; ++j) {
            float th = th0_ + (th1_ - th0_) * float(j) / sides_, c = std::sin(th), z = std::cos(th);
            float d = f.rx > 1e-6f ? disp_[size_t(r) * C + j] : 0.0f;
            gp_[size_t(r) * C + j] = Vector3Add(f.c, Vector3Add(Vector3Scale(f.x, c * (f.rx + d)), Vector3Scale(f.z, z * (f.rz + d))));
        }
    }
    for (int r = 0; r < rings_; ++r) {
        const Frame& f = frames_[r];
        const int rn = std::min(r + 1, rings_ - 1), rp = std::max(r - 1, 0);
        for (int j = 0; j < C; ++j) {
            int jn = j + 1, jp = j - 1;
            if (full) { jn = jn % sides_; jp = (jp + sides_) % sides_; }
            else { jn = std::min(jn, C - 1); jp = std::max(jp, 0); }
            Vector3 du = Vector3Subtract(gp_[size_t(r) * C + jn], gp_[size_t(r) * C + jp]);
            Vector3 dv = Vector3Subtract(gp_[size_t(rn) * C + j], gp_[size_t(rp) * C + j]);
            float th = th0_ + (th1_ - th0_) * float(j) / sides_;
            Vector3 radial = Vector3Add(Vector3Scale(f.x, std::sin(th)), Vector3Scale(f.z, std::cos(th)));
            Vector3 nn = safe_norm(Vector3CrossProduct(du, dv), radial);
            if (Vector3DotProduct(nn, radial) < 0) nn = Vector3Negate(nn);
            gn_[size_t(r) * C + j] = nn;
        }
    }
    size_t v = 0;
    auto put = [&](int ri, int sj) {
        std::memcpy(&data.pos[v * 3], &gp_[size_t(ri) * C + sj], sizeof(float) * 3);
        std::memcpy(&data.nrm[v * 3], &gn_[size_t(ri) * C + sj], sizeof(float) * 3);
        ++v;
    };
    for (int i = 0; i + 1 < rings_; ++i)
        for (int j = 0; j < sides_; ++j) {
            put(i, j); put(i, j + 1); put(i + 1, j + 1);
            put(i, j); put(i + 1, j + 1); put(i + 1, j);
        }
}

Sweep::Frame Sweep::ring_frame(float s) const {
    if (frames_.empty()) return {};
    int r = std::clamp(int(std::lround(s * (rings_ - 1))), 0, rings_ - 1);
    return frames_[r];
}

void Sweep::append_span(MeshData& out, float s0, float s1) const {
    const size_t per_band = size_t(sides_) * 6;
    for (int i = 0; i + 1 < rings_; ++i) {
        float mid = (float(i) + 0.5f) / (rings_ - 1);
        if (mid < s0 || mid >= s1) continue;
        size_t a = i * per_band, b = a + per_band;
        out.pos.insert(out.pos.end(), data.pos.begin() + a * 3, data.pos.begin() + b * 3);
        out.nrm.insert(out.nrm.end(), data.nrm.begin() + a * 3, data.nrm.begin() + b * 3);
        out.uv.insert(out.uv.end(), data.uv.begin() + a * 2, data.uv.begin() + b * 2);
        out.tan.insert(out.tan.end(), data.tan.begin() + a * 4, data.tan.begin() + b * 4);
        out.col.insert(out.col.end(), data.col.begin() + a * 4, data.col.begin() + b * 4);
    }
}

// ── GPU upload ─────────────────────────────────────────────────────────────────
Mesh upload(const MeshData& d, bool dynamic) {
    Mesh m{};
    m.vertexCount = int(d.count());
    m.triangleCount = m.vertexCount / 3;
    auto copy = [](const auto& src) {
        using T = typename std::decay_t<decltype(src)>::value_type;
        T* p = static_cast<T*>(MemAlloc(static_cast<unsigned int>(std::max<size_t>(src.size(), 1) * sizeof(T))));
        if (!src.empty()) std::memcpy(p, src.data(), src.size() * sizeof(T));
        return p;
    };
    m.vertices = copy(d.pos);
    m.normals = copy(d.nrm);
    m.texcoords = copy(d.uv);
    m.tangents = copy(d.tan);
    m.colors = copy(d.col);
    UploadMesh(&m, dynamic);
    return m;
}

void refresh(Mesh& m, const MeshData& d) {
    std::memcpy(m.vertices, d.pos.data(), d.pos.size() * sizeof(float));
    std::memcpy(m.normals, d.nrm.data(), d.nrm.size() * sizeof(float));
    UpdateMeshBuffer(m, 0, m.vertices, int(d.pos.size() * sizeof(float)), 0);
    UpdateMeshBuffer(m, 2, m.normals, int(d.nrm.size() * sizeof(float)), 0);
}

}  // namespace dw
