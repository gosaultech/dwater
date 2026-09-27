// damned_waters/engine/src/mesh_builder.cpp
// Purpose: see mesh_builder.hpp.
#include "dw/mesh_builder.hpp"

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
}  // namespace

void MeshBuilder::tri(Vector3 a, Vector3 b, Vector3 c, Vector3 na, Vector3 nb, Vector3 nc) {
    const Vector3 P[3] = {a, b, c}, N[3] = {na, nb, nc};
    for (int i = 0; i < 3; ++i) {
        d_.pos.insert(d_.pos.end(), {P[i].x, P[i].y, P[i].z});
        d_.nrm.insert(d_.nrm.end(), {N[i].x, N[i].y, N[i].z});
        d_.uv.insert(d_.uv.end(), {mat_, ao_});
        d_.tan.insert(d_.tan.end(), {P[i].x, P[i].y, P[i].z, 0.0f});   // surface coord = object space
        d_.col.insert(d_.col.end(), {col_.r, col_.g, col_.b, col_.a});
    }
}

void MeshBuilder::grid(const Grid& g, bool close_top, bool close_bottom) {
    const int R = int(g.size()), C = int(g[0].size());
    std::vector<Vector3> centre(R);
    for (int i = 0; i < R; ++i) {
        Vector3 s{};
        for (auto& p : g[i]) s = Vector3Add(s, p);
        centre[i] = Vector3Scale(s, 1.0f / C);
    }
    Vector3 all{};   // whole-shape centroid: fallback "outward" at poles where a ring collapses
    for (auto& c : centre) all = Vector3Add(all, c);
    all = Vector3Scale(all, 1.0f / R);
    Grid n(R, std::vector<Vector3>(C));
    for (int i = 0; i < R; ++i)
        for (int j = 0; j < C; ++j) {
            Vector3 du = Vector3Subtract(g[i][(j + 1) % C], g[i][(j + C - 1) % C]);
            Vector3 dv = Vector3Subtract(g[std::min(i + 1, R - 1)][j], g[std::max(i - 1, 0)][j]);
            Vector3 out = Vector3Subtract(g[i][j], centre[i]);
            if (Vector3Length(out) < 1e-5f) out = Vector3Subtract(g[i][j], all);
            Vector3 nn = safe_norm(Vector3CrossProduct(du, dv), out);
            if (Vector3DotProduct(nn, out) < 0) nn = Vector3Negate(nn);
            n[i][j] = nn;
        }
    for (int i = 0; i + 1 < R; ++i)
        for (int j = 0; j < C; ++j) {
            int k = (j + 1) % C;
            tri(g[i][j], g[i][k], g[i + 1][k], n[i][j], n[i][k], n[i + 1][k]);
            tri(g[i][j], g[i + 1][k], g[i + 1][j], n[i][j], n[i + 1][k], n[i + 1][j]);
        }
    auto cap = [&](int row, bool up) {
        Vector3 c = centre[row], cn = safe_norm(Vector3Subtract(c, centre[up ? std::min(row + 1, R - 1) : std::max(row - 1, 0)]), {0, up ? 1.f : -1.f, 0});
        for (int j = 0; j < C; ++j) tri(c, g[row][j], g[row][(j + 1) % C], cn, n[row][j], n[row][(j + 1) % C]);
    };
    if (close_top) cap(0, true);
    if (close_bottom) cap(R - 1, false);
}

void MeshBuilder::ellipsoid(Vector3 c, Vector3 r, int segs, int rings, const Bump& bump) {
    Grid g(rings + 1, std::vector<Vector3>(segs));
    for (int i = 0; i <= rings; ++i) {
        float phi = PI * float(i) / rings;   // 0 = top
        for (int j = 0; j < segs; ++j) {
            float th = TAU * float(j) / segs;   // 0 = front (-Z)
            Vector3 d{std::sin(phi) * std::sin(th), std::cos(phi), -std::sin(phi) * std::cos(th)};
            float off = bump ? bump(d) : 0.0f;
            g[i][j] = {c.x + d.x * (r.x + off), c.y + d.y * (r.y + off), c.z + d.z * (r.z + off)};
        }
    }
    grid(g);
}

void MeshBuilder::tube(Vector3 a, Vector3 b, float r0, float r1, int sides) { chain({a, b}, {r0, r1}, sides); }

void MeshBuilder::chain(const std::vector<Vector3>& pts, const std::vector<float>& radii, int sides) {
    Grid g;
    Vector3 ref{1, 0, 0};
    for (size_t i = 0; i < pts.size(); ++i) {
        Vector3 t = Vector3Normalize(Vector3Subtract(pts[std::min(i + 1, pts.size() - 1)], pts[i > 0 ? i - 1 : 0]));
        if (std::fabs(Vector3DotProduct(t, ref)) > 0.9f) ref = {0, 0, 1};
        Vector3 x = Vector3Normalize(Vector3CrossProduct(t, ref)), z = Vector3CrossProduct(t, x);
        std::vector<Vector3> row(sides);
        for (int j = 0; j < sides; ++j) {
            float th = TAU * float(j) / sides;
            row[j] = Vector3Add(pts[i], Vector3Add(Vector3Scale(x, std::cos(th) * radii[i]), Vector3Scale(z, std::sin(th) * radii[i])));
        }
        g.push_back(row);
    }
    grid(g, true, true);
}

void MeshBuilder::drape(Vector3 top, Vector2 rt, Vector2 rb, float length, int rings, int segs, int folds,
                        float fold_amp, const std::function<float(float)>& length_scale, unsigned seed) {
    std::mt19937 rng(seed);
    std::uniform_real_distribution<float> U(0.0f, TAU);
    const float p0 = U(rng), p1 = U(rng);
    Grid g(rings + 1, std::vector<Vector3>(segs));
    for (int i = 0; i <= rings; ++i) {
        float t = float(i) / rings, e = std::pow(t, 0.8f);
        for (int j = 0; j < segs; ++j) {
            float th = TAU * float(j) / segs;
            float L = length * (length_scale ? length_scale(th) : 1.0f);
            float fold = 1.0f + fold_amp * t * (std::sin(th * folds + p0) * 0.65f + std::sin(th * folds * 2.3f + p1) * 0.35f);
            float rx = (rt.x + (rb.x - rt.x) * e) * fold, rz = (rt.y + (rb.y - rt.y) * e) * fold;
            g[i][j] = {top.x + std::sin(th) * rx, top.y - t * L, top.z - std::cos(th) * rz};
        }
    }
    grid(g);
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

void Sweep::topology() {
    const size_t n = size_t(rings_ - 1) * sides_ * 6;
    data.pos.assign(n * 3, 0.0f);
    data.nrm.assign(n * 3, 0.0f);
    data.uv.clear(); data.tan.clear(); data.col.clear();
    for (int i = 0; i + 1 < rings_; ++i)
        for (int j = 0; j < sides_; ++j) {
            const int corners[6][2] = {{i, j}, {i, j + 1}, {i + 1, j + 1}, {i, j}, {i + 1, j + 1}, {i + 1, j}};
            for (auto& ck : corners) {
                float s = float(ck[0]) / (rings_ - 1), th = TAU * float(ck[1]) / sides_;
                bool tail = s >= tail_from_ && tail_mat_ >= 0;
                Color c = tail ? tail_col_ : col_;
                auto pr = prof_.at(s);
                float ao = 0.8f + 0.2f * std::min(1.0f, std::min(s, 1.0f - s) * 6.0f);   // ends tuck into joints
                data.uv.insert(data.uv.end(), {float(tail ? tail_mat_ : mat_), ao});
                data.tan.insert(data.tan.end(), {std::sin(th) * pr[0], s * length_, std::cos(th) * pr[1], 0.0f});
                data.col.insert(data.col.end(), {c.r, c.g, c.b, c.a});
            }
        }
}

void Sweep::build(const std::vector<Vector3>& pts, Vector3 right_hint) {
    // 1) Catmull-Rom through the joints, sampled finely, with arc length.
    const int n = int(pts.size()), per = 12;
    std::vector<Vector3> P(n + 2);
    P[0] = Vector3Subtract(Vector3Scale(pts[0], 2), pts[1]);
    for (int i = 0; i < n; ++i) P[i + 1] = pts[i];
    P[n + 1] = Vector3Subtract(Vector3Scale(pts[n - 1], 2), pts[n - 2]);
    std::vector<Vector3> fine;
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
    std::vector<float> acc(fine.size(), 0.0f);
    for (size_t i = 1; i < fine.size(); ++i) acc[i] = acc[i - 1] + Vector3Distance(fine[i], fine[i - 1]);
    const float total = std::max(acc.back(), 1e-5f);
    // 2) Rings at even arc length, framed by parallel transport (no twisting).
    std::vector<Vector3> C(rings_), X(rings_), Z(rings_);
    size_t cur = 0;
    for (int r = 0; r < rings_; ++r) {
        float want = total * float(r) / (rings_ - 1);
        while (cur + 2 < fine.size() && acc[cur + 1] < want) ++cur;
        float seg = std::max(acc[cur + 1] - acc[cur], 1e-6f), k = std::clamp((want - acc[cur]) / seg, 0.0f, 1.0f);
        C[r] = Vector3Lerp(fine[cur], fine[cur + 1], k);
        Vector3 t = safe_norm(Vector3Subtract(fine[cur + 1], fine[cur]), {0, 1, 0});
        Vector3 prev = r == 0 ? right_hint : X[r - 1];
        X[r] = safe_norm(Vector3Subtract(prev, Vector3Scale(t, Vector3DotProduct(prev, t))), {1, 0, 0});
        Z[r] = Vector3CrossProduct(X[r], t);
    }
    // 3) Fill the fixed-topology triangle soup.
    size_t v = 0;
    auto put = [&](int ri, int sj) {
        float s = float(ri) / (rings_ - 1), th = TAU * float(sj % sides_) / sides_;
        auto pr = prof_.at(s);
        float c = std::sin(th), z = std::cos(th);
        Vector3 centre = Vector3Add(C[ri], Vector3Scale(Z[ri], -pr[2]));   // forward shift (bellies, chests)
        Vector3 p = Vector3Add(centre, Vector3Add(Vector3Scale(X[ri], c * pr[0]), Vector3Scale(Z[ri], z * pr[1])));
        Vector3 nn = safe_norm(Vector3Add(Vector3Scale(X[ri], c / pr[0]), Vector3Scale(Z[ri], z / pr[1])), X[ri]);
        std::memcpy(&data.pos[v * 3], &p, sizeof(float) * 3);
        std::memcpy(&data.nrm[v * 3], &nn, sizeof(float) * 3);
        ++v;
    };
    for (int i = 0; i + 1 < rings_; ++i)
        for (int j = 0; j < sides_; ++j) {
            put(i, j); put(i, j + 1); put(i + 1, j + 1);
            put(i, j); put(i + 1, j + 1); put(i + 1, j);
        }
}

// ── GPU upload ─────────────────────────────────────────────────────────────────
Mesh upload(const MeshData& d, bool dynamic) {
    Mesh m{};
    m.vertexCount = int(d.count());
    m.triangleCount = m.vertexCount / 3;
    auto copy = [](const auto& src) {
        using T = typename std::decay_t<decltype(src)>::value_type;
        T* p = static_cast<T*>(MemAlloc(static_cast<unsigned int>(src.size() * sizeof(T))));
        std::memcpy(p, src.data(), src.size() * sizeof(T));
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
