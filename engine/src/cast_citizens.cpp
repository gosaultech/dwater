// damned_waters/engine/src/cast_citizens.cpp
// Purpose: the Drowned as Amsterdammers: an office worker, a woman in a dress, Pieter in his
// sweater. Their bodies (clothes, wounds, drowned skin) come from engine/assets/characters/<id>.dwc,
// built by tools/characters/cast_drowned.py. Here we add what hangs, grows or dangles, at the
// anchors that file names: guts pushed out of the split belly, the swollen tongue, a loosened tie
// and a staff pass, skin sliding off the degloved hand, zebra mussels, canal weed.
#include <algorithm>
#include <cmath>
#include <vector>

#include "cast_common.hpp"
#include "dw/room_spec.hpp"

namespace dw {
using namespace cast;
namespace {
const Color GUTS{150, 116, 112, 255}, GUTS_DARK{124, 92, 92, 255}, TONGUE{56, 32, 48, 255}, SLOUGH{160, 158, 140, 255},
    WEED{44, 60, 26, 255}, TIE{80, 20, 30, 255}, CARD{214, 214, 206, 255}, CARD_BAND{36, 62, 128, 255}, INK{60, 60, 64, 255};

// Lie flat on a surface: local x across, y up it, -z out along `normal` (a card on a shirt).
Matrix lying_on(Vector3 at, Vector3 normal) {
    const Vector3 out = Vector3Normalize(normal);
    const Vector3 x = Vector3Normalize(Vector3CrossProduct({0, 1, 0}, Vector3Negate(out)));
    const Vector3 y = Vector3CrossProduct(Vector3Negate(out), x);
    Matrix m = MatrixIdentity();
    m.m0 = x.x; m.m1 = x.y; m.m2 = x.z;
    m.m4 = y.x; m.m5 = y.y; m.m6 = y.z;
    m.m8 = -out.x; m.m9 = -out.y; m.m10 = -out.z;
    m.m12 = at.x; m.m13 = at.y; m.m14 = at.z;
    return m;
}

int region_of(int joint) {   // which body region a joint's skin belongs to (for dismemberment)
    switch (joint) {
        case J_HEAD: return R_HEAD;
        case J_JAW: return R_JAW;
        case J_SHO_L: return R_UARM_L;
        case J_SHO_R: return R_UARM_R;
        case J_ELB_L: case J_WRI_L: case J_FING1_L: case J_FING2_L: case J_THUMB_L: return R_FARM_L;
        case J_ELB_R: case J_WRI_R: case J_FING1_R: case J_FING2_R: case J_THUMB_R: return R_FARM_R;
        case J_HIP_L: return R_THIGH_L;
        case J_HIP_R: return R_THIGH_R;
        case J_KNE_L: case J_ANK_L: return R_SHIN_L;
        case J_KNE_R: case J_ANK_R: return R_SHIN_R;
        default: return R_BODY;
    }
}
}  // namespace

Character build_citizen(const std::string& id, int variant) {
    Character c;
    c.kind = Kind::Drowned;
    c.thickness_ = 0.17f;   // bloated: lies high off the floor
    c.rng_ = 0x9E3779B9u ^ unsigned(variant * 7919 + 31);
    if (!c.load_body(repo_root() + "/engine/assets/characters/" + id + ".dwc")) return c;
    c.head_c_ = {0, 0.075f, -0.02f};
    // Colliders keep what dangles (guts, the tie, weed, the tongue) outside the body.
    c.colliders_ = {{J_PELVIS, J_CHEST, {0, 0.02f, 0}, {0, 0.1f, 0.01f}, 0.17f},
                    {J_HIP_L, J_KNE_L, {}, {}, 0.085f}, {J_HIP_R, J_KNE_R, {}, {}, 0.085f},
                    {J_HEAD, J_HEAD, {0, 0.07f, -0.01f}, {0, 0.07f, 0.02f}, 0.085f}, {J_NECK, J_HEAD, {}, {}, 0.07f}};
    MeshData d;
    // Guts: loops bulging through the split in the belly, a void behind them; two loops have slid
    // out and sag from the wound (both ends held inside), and one torn end hangs free.
    if (const auto* a = c.anchor("guts")) {
        MeshBuilder b(d);
        const Vector3 p = a->pos;
        b.material(MAT_VOID).color(BLACK).ellipsoid({p.x, p.y, p.z + 0.012f}, {0.02f, 0.06f, 0.012f}, 12, 10);
        b.material(MAT_GUTS).color(GUTS);
        for (int i = 0; i < 4; ++i)
            b.ellipsoid({p.x + (i % 2 ? 0.01f : -0.009f), p.y - 0.03f + i * 0.02f, p.z - 0.008f}, {0.019f, 0.015f, 0.016f}, 10, 8);
        c.add_rigid(a->joint, R_BODY, d);
        const Profile gut{{{0, 0.014f, 0.014f, 0}, {1, 0.014f, 0.014f, 0}}};
        c.add_dangle(a->joint, R_BODY, {p.x - 0.012f, p.y - 0.035f, p.z - 0.006f}, {0.1f, -1, -0.3f}, 8, 0.03f, gut, MAT_GUTS, GUTS,
                     0.97f, 0.0f, a->joint, {p.x + 0.013f, p.y - 0.055f, p.z - 0.006f});
        c.add_dangle(a->joint, R_BODY, {p.x + 0.006f, p.y - 0.0f, p.z - 0.008f}, {-0.1f, -1, -0.3f}, 5, 0.028f,
                     Profile{{{0, 0.012f, 0.012f, 0}, {1, 0.012f, 0.012f, 0}}}, MAT_GUTS, GUTS_DARK, 0.97f, 0.0f, a->joint,
                     {p.x + 0.016f, p.y - 0.03f, p.z - 0.008f});
        c.add_dangle(a->joint, R_BODY, {p.x - 0.004f, p.y - 0.06f, p.z - 0.008f}, {0.2f, -1, -0.3f}, 4, 0.03f,
                     Profile{{{0, 0.012f, 0.012f, 0}, {0.8f, 0.011f, 0.011f, 0}, {1, 0.006f, 0.006f, 0}}}, MAT_GUTS, GUTS_DARK, 0.97f);
    }
    // The swollen tongue pushes out over the lower teeth: short, broad, dark.
    if (const auto* a = c.anchor("tongue"))
        c.add_dangle(J_JAW, R_JAW, a->pos, {0.05f, -0.6f, -1}, 3, 0.016f,
                     Profile{{{0, 0.021f, 0.011f, 0}, {0.6f, 0.022f, 0.01f, 0}, {1, 0.014f, 0.007f, 0}}}, MAT_TONGUE, TONGUE, 0.9f, 0.3f);
    // The degloved hand: the skin hangs off it in two torn flaps.
    if (const auto* a = c.anchor("loose_skin"))
        for (float x : {-0.022f, 0.022f})
            c.add_dangle(a->joint, region_of(a->joint), {a->pos.x + x, a->pos.y, a->pos.z}, {0, -1, 0.1f}, 5, 0.03f,
                         Profile{{{0, 0.018f, 0.0025f, 0}, {1, 0.008f, 0.002f, 0}}}, MAT_SLOUGH, SLOUGH, 0.93f);
    // Office worker: the knot of his loosened tie (the tie itself lies on the shirt, in the .dwc),
    // and his staff pass at the end of its lanyard: laminated card, blue band, photo, name.
    if (const auto* a = c.anchor("tie")) {
        d = {};
        MeshBuilder(d).transform(lying_on(a->pos, a->dir)).material(MAT_NYLON).color(TIE).box({}, {0.014f, 0.013f, 0.007f}, 0.5f, 10, 8);
        c.add_rigid(a->joint, R_BODY, d);
    }
    if (const auto* a = c.anchor("badge")) {
        d = {};
        MeshBuilder b(d);
        b.transform(lying_on(a->pos, a->dir));
        b.material(MAT_DEFAULT).color(CARD).box({}, {0.027f, 0.043f, 0.0012f}, 0.15f, 10, 8);
        b.color(CARD_BAND).box({0, 0.031f, -0.0011f}, {0.0262f, 0.0095f, 0.0003f}, 0.15f, 8, 4);
        b.color(Color{120, 112, 104, 255}).box({-0.011f, -0.004f, -0.0011f}, {0.009f, 0.012f, 0.0003f}, 0.2f, 6, 6);   // photo
        b.color(INK).box({0.01f, 0.0f, -0.0011f}, {0.009f, 0.0012f, 0.0003f}, 0.3f, 6, 3);                            // name
        b.color(INK).box({0.008f, -0.006f, -0.0011f}, {0.007f, 0.001f, 0.0003f}, 0.3f, 6, 3);
        b.material(MAT_METAL).color(Color{150, 150, 155, 255}).box({0, 0.046f, -0.0006f}, {0.004f, 0.006f, 0.0015f}, 0.3f, 6, 4);
        c.add_rigid(a->joint, R_BODY, d);
    }
    // Long hair, soaked: a clump from every "hair" anchor, lying along the skull away from the crown
    // and hanging straight once it leaves it. Clumps rooted at the front fall forward: a wet
    // curtain over the face (her head hangs forward, so it stays there), parted a finger's width,
    // so the scream shows through the gap.
    int roots = 0;
    for (const auto& a : c.anchors_) roots += a.name.rfind("hair", 0) == 0;
    if (roots > 0) {
        const float y0 = 0.065f, z0 = -0.012f, z1 = 0.02f;
        auto axis_at = [&](Vector3 p) { return Vector3{0, y0, std::clamp(p.z, z0, z1)}; };
        std::vector<float> reach;
        for (const auto& a : c.anchors_)
            if (a.name.rfind("hair", 0) == 0) reach.push_back(Vector3Distance(a.pos, axis_at(a.pos)));
        std::nth_element(reach.begin(), reach.begin() + long(reach.size() / 2), reach.end());
        const float skR = reach[reach.size() / 2];                        // the skull, fitted to this scalp
        const Vector3 skA{0, y0, z0}, skB{0, y0, z1}, faceA{0, 0.0f, -0.035f}, faceB{0, 0.1f, -0.035f}, nose{0, 0.01f, -0.095f};
        const float faceR = skR - 0.003f;
        c.colliders_[3] = {J_HEAD, J_HEAD, skA, skB, skR};
        c.colliders_.push_back({J_HEAD, J_HEAD, faceA, faceB, faceR});
        c.colliders_.push_back({J_HEAD, J_HEAD, nose, nose, 0.025f});
        c.colliders_.push_back({J_SHO_L, J_SHO_R, {0, 0.03f, 0.02f}, {0, 0.03f, 0.02f}, 0.07f});
        c.bow_ = 0.75f;
        Character::Strands hair;
        hair.joint = J_HEAD;
        hair.n = 14;
        hair.sides = 5;
        hair.mat = MAT_WETHAIR;
        hair.col = {42, 32, 26, 255};
        hair.taper = 0.5f;
        hair.lump = 0.0f;
        hair.ribbon = true;
        hair.axisA = {0, y0, z0};
        hair.axisB = {0, y0, z1};
        unsigned h = 0x6C8E9CF5u;
        auto rnd = [&h]() { h ^= h << 13; h ^= h >> 17; h ^= h << 5; return float(h & 0xFFFF) / 65535.0f; };
        const Vector3 crown{0.0f, y0 + skR * 0.95f, 0.012f};
        auto push_out = [](Vector3 p, Vector3 a, Vector3 b, float r) {   // p moved out of the capsule a-b of radius r
            const Vector3 ab = Vector3Subtract(b, a);
            const float t = std::clamp(Vector3DotProduct(Vector3Subtract(p, a), ab) / std::max(Vector3LengthSqr(ab), 1e-8f), 0.0f, 1.0f);
            const Vector3 q = Vector3Add(a, Vector3Scale(ab, t)), d = Vector3Subtract(p, q);
            const float l = Vector3Length(d);
            return l < r ? Vector3Add(q, Vector3Scale(d, r / std::max(l, 1e-5f))) : p;
        };
        for (const auto& a : c.anchors_) {
            if (a.name.rfind("hair", 0) != 0) continue;
            const Vector3 n = Vector3Normalize(a.dir), p0 = a.pos;
            const bool curtain = p0.z < -0.02f && std::fabs(p0.x) < 0.055f;       // the front of the scalp
            const float part = p0.x < 0 ? -1.0f : 1.0f;                               // which side of the parting
            const float len = curtain ? 0.3f + 0.06f * rnd() : 0.36f + 0.08f * rnd();
            const float seg = len / float(hair.n - 1), radius = 0.01f + 0.012f * rnd();   // ribbon width
            Vector3 p = Vector3Subtract(p0, Vector3Scale(n, 0.002f));
            hair.anchor.push_back(p);
            hair.rest.push_back(p);
            Vector3 dir{0, -1, 0};   // replaced by the first step's direction: along the skull, never off it
            bool first = true;
            for (int i = 1; i < hair.n; ++i) {
                const Vector3 radial = Vector3Normalize(Vector3Subtract(p, axis_at(p)));
                // Over the skull: away from the crown, hugging it; below its widest band (or past the
                // brow, for the curtain): straight down.
                Vector3 along = Vector3Subtract(Vector3Subtract(p, crown), Vector3Scale(radial, Vector3DotProduct(Vector3Subtract(p, crown), radial)));
                along = Vector3LengthSqr(along) > 1e-8f ? Vector3Normalize(along) : Vector3{0, -1, 0};
                const float leave = curtain ? (p.z < -0.075f ? 1.0f : 0.25f) : std::clamp((0.35f - radial.y) / 0.4f, 0.0f, 1.0f);
                const Vector3 fall = curtain ? Vector3{part * 0.22f, -1, 0} : Vector3{0, -1, 0};
                const Vector3 want = Vector3Normalize(Vector3Lerp(along, fall, leave));
                dir = first ? want : Vector3Normalize(Vector3Lerp(dir, want, 0.5f));
                first = false;
                p = Vector3Add(p, Vector3Scale(dir, seg));
                p = push_out(p, skA, skB, skR + 0.004f);
                p = push_out(p, faceA, faceB, faceR + 0.006f);
                p = push_out(p, nose, nose, 0.03f);
                hair.rest.push_back(p);
            }
            hair.seg.push_back(seg);
            hair.radius.push_back(radius);
            hair.stiff.push_back(curtain ? 0.22f : 0.1f);
        }
        c.add_strands(std::move(hair));
    }
    // Water still running off them: from the points the .dwc marks (fingertips, chin, hems) and
    // from every tenth hank of wet hair.
    for (const auto& a : c.anchors_) {
        if (a.name.rfind("drip", 0) != 0) continue;
        c.add_drip_source(a.joint, a.pos, false, region_of(a.joint));
        if (a.name == "drip_chin") c.chin_ = a.pos;   // the jaw's hit capsule runs to it
    }
    if (!c.strands_.empty())
        for (size_t k = 0; k < c.strands_.front().anchor.size(); k += 10) c.add_drip_source(-1, {float(k), 0, 0});
    // Canal growth: mussel clusters, weed trailing from hems and belts.
    unsigned seed = 31u + unsigned(variant);
    for (const auto& a : c.anchors_) {
        if (a.name.rfind("mussels", 0) == 0) {
            d = {};
            mussels(d, a.pos, a.dir, 10, 0.03f, seed++);
            c.add_rigid(a.joint, region_of(a.joint), d);
        } else if (a.name.rfind("weed", 0) == 0) {
            c.add_dangle(a.joint, region_of(a.joint), a.pos, {0, -1, 0.3f}, 6, 0.042f,
                         Profile{{{0, 0.013f, 0.0025f, 0}, {1, 0.004f, 0.002f, 0}}}, MAT_WEED, WEED, 0.95f);
        }
    }
    return c;
}

}  // namespace dw
