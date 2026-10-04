// damned_waters/engine/src/character_clearance.cpp
// Purpose: Character::clearance(), the check that nothing goes through anything as he moves: his
// arms and hands against his body and coat, the gun against his body, his left hand against the
// right and against the gun. Measured from the skinned vertices as they are this frame
// (clearance.hpp), so it sees what the camera would. Used by --clearance to sweep the reloads, and
// the ways he carries each gun (standing, walking, running, raising it to the aim and lowering it),
// frame by frame while tuning them; never run in play.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

#include "dw/character.hpp"
#include "dw/clearance.hpp"
#include "cast_guns.hpp"

namespace dw {
namespace {
clearance::V3 v3(Vector3 v) { return {v.x, v.y, v.z}; }
Vector3 turn_only(Vector3 v, const Matrix& m) {
    return {m.m0 * v.x + m.m4 * v.y + m.m8 * v.z, m.m1 * v.x + m.m5 * v.y + m.m9 * v.z, m.m2 * v.x + m.m6 * v.y + m.m10 * v.z};
}
}  // namespace

float Character::wrist_bend(bool right) const {
    const Vector3 e = joint(right ? J_ELB_R : J_ELB_L), w = joint(right ? J_WRI_R : J_WRI_L), k = joint(finger_joint(right, F_MIDDLE, 0));
    return Vector3Angle(Vector3Subtract(w, e), Vector3Subtract(k, w));
}

Character::Clearance Character::clearance(std::vector<Vector3>* clashes) const {
    using clearance::Cloud;
    using clearance::V3;
    // The surfaces: the body (torso, coat, pelvis), each forearm with its hand, the gun in hand.
    Cloud body(0.025f), rhand(0.015f), gun(0.012f);
    std::vector<V3> larm, rarm, lhand, rindex;
    const Vector3 sho_l = joint(J_SHO_L), sho_r = joint(J_SHO_R), wri_l = joint(J_WRI_L);
    for (const Skinned& s : skinned_) {
        for (int v : s.by_region[R_BODY]) body.add(v3(skin_point(s, v)), v3(skin_normal(s, v)));
        for (int r : {R_UARM_L, R_FARM_L, R_UARM_R, R_FARM_R})
            for (int v : s.by_region[size_t(r)]) {
                const Vector3 p = skin_point(s, v);
                const bool left = r == R_UARM_L || r == R_FARM_L;
                // (the top of the arm meets the body at the armpit and the shoulder: that's where it joins, not a clash)
                if (Vector3Distance(p, left ? sho_l : sho_r) < 0.16f) continue;
                (left ? larm : rarm).push_back(v3(p));
                if (r == R_FARM_R) rhand.add(v3(p), v3(skin_normal(s, v)));
                if (r == R_FARM_L && Vector3Distance(p, wri_l) < 0.2f) lhand.push_back(v3(p));
                if (r == R_FARM_R && s.mesh.boneIds) {   // the forefinger's skin: carried mostly by its middle or last joint
                    int top = 0;
                    for (int k = 1; k < 4; ++k)
                        if (s.mesh.boneWeights[v * 4 + k] > s.mesh.boneWeights[v * 4 + top]) top = k;
                    const int j = s.mesh.boneIds[v * 4 + top];
                    if (j == J_INDEX2_R || j == J_INDEX3_R) rindex.push_back(v3(p));
                }
            }
    }
    std::vector<V3> gun_pts;
    for (const Rigid& r : rigid_) {
        if (r.tag != weapon_ + 1 || r.drive == 3 || r.mesh.vertices == nullptr) continue;
        const float k = r.drive == 1 ? slide : r.drive == 2 ? pump : 0.0f;
        const Matrix at = MatrixMultiply(MatrixTranslate(r.travel.x * k, r.travel.y * k, r.travel.z * k), W_[r.joint]);
        for (int v = 0; v < r.mesh.vertexCount; ++v) {
            const Vector3 p = Vector3Transform({r.mesh.vertices[v * 3], r.mesh.vertices[v * 3 + 1], r.mesh.vertices[v * 3 + 2]}, at);
            gun_pts.push_back(v3(p));
            if (r.mesh.normals)
                gun.add(v3(p), v3(Vector3Normalize(turn_only({r.mesh.normals[v * 3], r.mesh.normals[v * 3 + 1], r.mesh.normals[v * 3 + 2]}, at))));
        }
    }
    constexpr float REACH = 0.05f, TOL = 0.006f;
    Clearance c;
    c.larm = clearance::worst(larm, body, REACH, TOL);
    c.rarm = clearance::worst(rarm, body, REACH, TOL);
    c.gun = clearance::worst(gun_pts, body, REACH, TOL);
    c.hands = clearance::worst(lhand, rhand, 0.025f, TOL);
    c.lhand_gun = clearance::worst(lhand, gun, 0.015f, TOL);
    c.rindex_gun = clearance::worst(rindex, gun, 0.015f, 0.002f);
    if (clashes)  // every point more than a whisker in, for drawing
        for (const auto* set : {&larm, &rarm, &gun_pts})
            for (const V3& p : *set)
                if (body.depth(p, REACH) > 0.008f) clashes->push_back({p.x, p.y, p.z});
    auto where = [](const std::vector<V3>& pts, const clearance::Worst& w) { return w.at >= 0 ? Vector3{pts[size_t(w.at)].x, pts[size_t(w.at)].y, pts[size_t(w.at)].z} : Vector3{}; };
    c.larm_at = where(larm, c.larm);
    c.rarm_at = where(rarm, c.rarm);
    c.gun_at = where(gun_pts, c.gun);
    return c;
}

}  // namespace dw

namespace dw {

// Each reload played as the game plays it (60 frames a second, from the aim, back to the aim),
// the worst of every 0.05 of it.
std::string Character::reload_clearance() {
    struct Run { const char* name; int gun; reload::Kind kind; bool from_grip; float secs; };
    const Run runs[] = {{"pistol magazine", 0, reload::Kind::Magazine, true, 1.4f},
                        {"870 shell (from the fore-end)", 1, reload::Kind::Shell, true, 0.5f},
                        {"870 shell (from the port)", 1, reload::Kind::Shell, false, 0.5f},
                        {"870 shell + rack", 1, reload::Kind::ShellRack, true, 0.9f}};
    std::string out;
    char line[256];
    out += "torso about the chest:\n" + torso_[0].describe() + "torso about the pelvis:\n" + torso_[1].describe();
    const float dt = 1.0f / 60;
    for (const Run& r : runs) {
        set_weapon(r.gun);
        reloading = {};
        pump = slide = 0;
        for (int f = 0; f < 90; ++f) animate(Pose::Aim, 0, dt);
        std::snprintf(line, sizeof line, "\n%s (%.1f s)\n   t     larm  rarm  gun   hands lh-gun (mm deep; worst over the bin)   wrists L / R (deg: swing, twist)\n", r.name, r.secs);
        out += line;
        const int frames = int(std::lround(r.secs / dt));
        Clearance bin{}, all{};
        auto keep = [](clearance::Worst& a, Vector3& a_at, const clearance::Worst& b, Vector3 b_at) { if (b.depth > a.depth) { a = b; a_at = b_at; } };
        auto fold = [&](Clearance& a, const Clearance& b) {
            keep(a.larm, a.larm_at, b.larm, b.larm_at);
            keep(a.rarm, a.rarm_at, b.rarm, b.rarm_at);
            keep(a.gun, a.gun_at, b.gun, b.gun_at);
            Vector3 none{};
            keep(a.hands, none, b.hands, {});
            keep(a.lhand_gun, none, b.lhand_gun, {});
        };
        auto near = [&](Vector3 at) {   // the joint nearest a point (to say where a clash is)
            int best = 0;
            for (int j = 0; j < J_THUMB1_L; ++j) if (Vector3Distance(joint(j), at) < Vector3Distance(joint(best), at)) best = j;
            static const char* N[] = {"pelvis", "spine", "chest", "neck", "head", "jaw", "sho_l", "elb_l", "wri_l", "sho_r", "elb_r", "wri_r",
                                      "hip_l", "kne_l", "ank_l", "hip_r", "kne_r", "ank_r"};
            return N[best];
        };
        auto row = [&](const char* label, const Clearance& c) {
            Vector3 st[2];
            for (int k = 0; k < 2; ++k) {   // each wrist's swing and twist (this frame)
                const Vector3 a = ik_wrist_[k];
                const Matrix m = MatrixMultiply(MatrixMultiply(MatrixRotateZ(a.z), MatrixRotateX(a.x)), MatrixRotateY(a.y));
                swing_twist(QuaternionFromMatrix(m), off_[k ? J_WRI_R : J_WRI_L], st[k].x, st[k].y);
            }
            std::snprintf(line, sizeof line, "  %-5s %5.0f %5.0f %5.0f %5.0f %5.0f   %4.0f %4.0f / %4.0f %4.0f   larm@%s rarm@%s gun@%s\n", label,
                          c.larm.depth * 1000, c.rarm.depth * 1000, c.gun.depth * 1000, c.hands.depth * 1000, c.lhand_gun.depth * 1000,
                          st[0].x * RAD2DEG, st[0].y * RAD2DEG, st[1].x * RAD2DEG, st[1].y * RAD2DEG, c.larm.depth > 0 ? near(c.larm_at) : "-",
                          c.rarm.depth > 0 ? near(c.rarm_at) : "-", c.gun.depth > 0 ? near(c.gun_at) : "-");
            out += line;
        };
        for (int f = 0; f <= frames + 30; ++f) {
            const float t = float(f) / float(frames);
            reloading = {f <= frames, r.kind, std::min(t, 1.0f), r.from_grip};
            pump = reload::pump(r.kind, std::min(t, 1.0f));
            animate(f <= frames ? Pose::Reload : Pose::Aim, 0, dt);
            fold(bin, clearance());
            if (f % 3 == 2 || f == frames + 30) {
                char label[16];
                std::snprintf(label, sizeof label, f <= frames ? "%.2f" : "after", std::min(t, 1.0f));
                if (f > frames && f != frames + 30) continue;
                row(label, bin);
                fold(all, bin);
                bin = {};
            }
        }
        row("WORST", all);
    }
    return out;
}

}  // namespace dw

namespace dw {

// Each gun carried as the game carries it, at 60 frames a second: standing at the ready (settled),
// a walking stride and a running one (at the game's speeds, 1.9 and 3.8 m/s), the raise to the
// aim and the lowering back to the ready, the worst of every 0.05 s. Beside the clearance: both
// wrists (swing, twist; comfortable to about 40 and 75 degrees), and where the trigger finger is:
// how near the skin of its last segment comes to the trigger's face (mm), and whether any of it is
// inside the trigger guard.
std::string Character::stance_clearance() {
    std::string out;
    char line[320];
    const float dt = 1.0f / 60;
    auto wrist = [&](int k) {   // swing and twist (radians) of a wrist as this frame has it
        const Vector3 a = ik_[k] ? ik_wrist_[k] : Vector3Add(ang_[k ? J_WRI_R : J_WRI_L], twitch_[k ? J_WRI_R : J_WRI_L]);
        const Matrix m = MatrixMultiply(MatrixMultiply(MatrixRotateZ(a.z), MatrixRotateX(a.x)), MatrixRotateY(a.y));
        Vector2 st{};
        swing_twist(QuaternionFromMatrix(m), off_[k ? J_WRI_R : J_WRI_L], st.x, st.y);
        return st;
    };
    struct Row { Clearance c; Vector2 wl, wr; float trig; bool in_guard; };
    auto sample = [&]() {
        Row r{clearance(), wrist(0), wrist(1), 1e9f, false};
        // The skin of the forefinger's last segment, in the gun's own measure (mm: u forward, v up,
        // w to its right), against the trigger's face and the guard's opening (cast_guns.cpp).
        const Matrix to_gun = MatrixInvert(gun_frame());
        const Vector3 o = weapon_ == 1 ? cast::r870_at(0, 0, 0) : cast::m92fs_at(0, 0, 0);
        const Vector3 face = weapon_ == 1 ? Vector3{31, -60, 0} : Vector3{84.7f, -42.5f, 0};
        for (const Skinned& s : skinned_) {
            if (!s.mesh.boneIds || R_FARM_R >= int(s.by_region.size())) continue;
            for (int v : s.by_region[R_FARM_R]) {
                int top = 0;
                for (int k = 1; k < 4; ++k)
                    if (s.mesh.boneWeights[v * 4 + k] > s.mesh.boneWeights[v * 4 + top]) top = k;
                if (s.mesh.boneIds[v * 4 + top] != J_INDEX3_R) continue;
                const Vector3 g = Vector3Transform(skin_point(s, v), to_gun);
                const Vector3 p{(o.y - g.y) * 1000, (o.z - g.z) * 1000, g.x * 1000};
                r.trig = std::min(r.trig, Vector3Distance(p, face));
                r.in_guard = r.in_guard || (std::fabs(p.z) < 5 && (weapon_ == 1 ? p.x > 16 && p.x < 87 && p.y < -45 && p.y > -73
                                                                                 : p.x > 56 && p.x < 116 && p.y < -28 && p.y > -57));
            }
        }
        return r;
    };
    auto fold = [](Row& a, const Row& b) {
        auto keep = [](clearance::Worst& x, const clearance::Worst& y) { if (y.depth > x.depth) x = y; };
        keep(a.c.larm, b.c.larm); keep(a.c.rarm, b.c.rarm); keep(a.c.gun, b.c.gun); keep(a.c.hands, b.c.hands);
        keep(a.c.lhand_gun, b.c.lhand_gun); keep(a.c.rindex_gun, b.c.rindex_gun);
        a.wl = {std::max(a.wl.x, b.wl.x), std::fabs(b.wl.y) > std::fabs(a.wl.y) ? b.wl.y : a.wl.y};
        a.wr = {std::max(a.wr.x, b.wr.x), std::fabs(b.wr.y) > std::fabs(a.wr.y) ? b.wr.y : a.wr.y};
        a.trig = std::min(a.trig, b.trig);
        a.in_guard = a.in_guard || b.in_guard;
    };
    auto print = [&](const char* label, const Row& r) {
        std::snprintf(line, sizeof line, "  %-6s %5.0f %5.0f %5.0f %5.0f %6.0f %6.0f   %4.0f %4.0f / %4.0f %4.0f   %5.0f %s\n", label,
                      r.c.larm.depth * 1000, r.c.rarm.depth * 1000, r.c.gun.depth * 1000, r.c.hands.depth * 1000, r.c.lhand_gun.depth * 1000,
                      r.c.rindex_gun.depth * 1000, r.wl.x * RAD2DEG, r.wl.y * RAD2DEG, r.wr.x * RAD2DEG, r.wr.y * RAD2DEG, r.trig,
                      r.in_guard ? "in the guard" : "out");
        out += line;
    };
    const char* header = "         larm  rarm   gun hands lh-gun finger   wrists L / R (deg: swing, twist)   trigger (mm: the fingertip from its face)\n";
    for (int gun = 0; gun < 2; ++gun) {
        set_weapon(gun);
        reloading = {};
        pump = slide = 0;
        limp = 0;
        Row all{};
        all.trig = 1e9f;
        auto settle = [&](Pose p, float speed) { for (int f = 0; f < 120; ++f) animate(p, speed, dt); };
        auto play = [&](const char* name, Pose p, float speed, float secs, bool rows) {
            std::snprintf(line, sizeof line, "\n%s, %s\n%s", gun ? "870" : "M92FS", name, header);
            out += line;
            Row bin{}, worst{};
            bin.trig = worst.trig = 1e9f;
            const int frames = int(std::lround(secs / dt));
            for (int f = 1; f <= frames; ++f) {
                animate(p, speed, dt);
                fold(bin, sample());
                if (f % 3 == 0 || f == frames) {
                    if (rows) {
                        char label[16];
                        std::snprintf(label, sizeof label, "%.2f", float(f) * dt);
                        print(label, bin);
                    }
                    fold(worst, bin);
                    bin = {};
                    bin.trig = 1e9f;
                }
            }
            print("WORST", worst);
            fold(all, worst);
        };
        settle(Pose::Idle, 0);
        play("standing at the ready", Pose::Idle, 0, 1.0f, false);
        settle(Pose::Walk, 1.9f);
        play("walking (1.9 m/s)", Pose::Walk, 1.9f, 1.4f, false);
        settle(Pose::Run, 3.8f);
        play("running (3.8 m/s)", Pose::Run, 3.8f, 1.0f, false);
        settle(Pose::Idle, 0);
        play("raised to the aim", Pose::Aim, 0, 0.6f, true);
        settle(Pose::Aim, 0);
        play("lowered to the ready", Pose::Idle, 0, 0.6f, true);
        settle(Pose::Walk, 1.9f);
        play("walking, then aiming", Pose::Aim, 0, 0.6f, false);
        std::snprintf(line, sizeof line, "\n%s, all of it\n%s", gun ? "870" : "M92FS", header);
        out += line;
        print("WORST", all);
    }
    return out;
}

// --fitreload. The pistol's close position and turn, searched (coordinate descent: each number
// nudged either way while that helps, the nudges halved when nothing does) to make the magazine
// change, played through frame by frame, cost least: wrists past what's comfortable, anything
// going into anything, and the muzzle swinging off down-range.
std::string Character::fit_reload() {
    const float dt = 1.0f / 60;
    auto strain = [&](bool right) {   // how far past comfortable a wrist is (radians)
        const Vector3 a = ik_wrist_[right ? 1 : 0];
        const Matrix m = MatrixMultiply(MatrixMultiply(MatrixRotateZ(a.z), MatrixRotateX(a.x)), MatrixRotateY(a.y));
        float sw = 0, tw = 0;
        swing_twist(QuaternionFromMatrix(m), off_[right ? J_WRI_R : J_WRI_L], sw, tw);
        return std::max(sw - 40.0f * DEG2RAD, 0.0f) + 0.6f * std::max(std::fabs(tw) - 75.0f * DEG2RAD, 0.0f);
    };
    auto score = [&](const ReloadShape& r, std::string* why) {
        reload_shape = r;
        set_weapon(0);
        reloading = {};
        pump = slide = 0;
        for (int k = 0; k < 2; ++k) swivel_[k] = 0;
        for (int f = 0; f < 60; ++f) animate(Pose::Aim, 0, dt);
        const int frames = int(std::lround(1.4f / dt));
        float wl = 0, wr = 0, in = 0, aim = 0, worst = 0;
        int n = 0;
        for (int f = 0; f <= frames; ++f) {
            const float t = float(f) / float(frames);
            reloading = {true, reload::Kind::Magazine, t, true};
            animate(Pose::Reload, 0, dt);
            if (f % 2) continue;
            const Clearance c = clearance();
            // (the wrists count while the gun's in close: the left with the magazine, from the pocket to home)
            const float l = t > 0.42f && t < 0.75f ? strain(false) : 0.0f, rr = t > 0.1f && t < reload::DRIVE_OUT ? strain(true) : 0.0f;
            auto past = [](const clearance::Worst& w) { return std::max(w.depth - 0.006f, 0.0f); };
            const float deep = 60.0f * (past(c.larm) + past(c.rarm) + past(c.hands) + past(c.gun)) + 30.0f * past(c.lhand_gun);
            const Vector3 fwd = Vector3Normalize({-W_[J_CHEST].m8, 0, -W_[J_CHEST].m10});   // where he faces
            const float off = std::max(Vector3Angle(barrel_dir(), fwd) - 40.0f * DEG2RAD, 0.0f);
            wl += l; wr += rr; in += deep; aim += off;
            worst = std::max(worst, l + rr + deep + off);
            ++n;
        }
        const float total = (wl + wr + in + aim) / float(n) + 0.5f * worst;
        if (why) {
            char b[200];
            std::snprintf(b, sizeof b, "cost %.3f: left wrist %.3f, right wrist %.3f, clashes %.3f, muzzle off %.3f (per frame), worst frame %.3f", total,
                          wl / float(n), wr / float(n), in / float(n), aim / float(n), worst);
            *why = b;
        }
        return total;
    };
    ReloadShape best = reload_shape;
    if (const char* from = std::getenv("DW_FIT_FROM"))   // (a starting point: x,y,z,cant,pitch,yaw)
        std::sscanf(from, "%f,%f,%f,%f,%f,%f", &best.close_at.x, &best.close_at.y, &best.close_at.z, &best.cant, &best.pitch, &best.yaw);
    float* p[6] = {&best.close_at.x, &best.close_at.y, &best.close_at.z, &best.cant, &best.pitch, &best.yaw};
    const float lo[6] = {-0.12f, -0.16f, -0.48f, -1.2f, -0.3f, -0.6f}, hi[6] = {0.14f, 0.12f, -0.28f, 1.1f, 0.9f, 0.7f};
    float step[6] = {0.03f, 0.03f, 0.03f, 0.15f, 0.15f, 0.15f};
    std::string before, after;
    float cost = score(best, &before);
    for (int round = 0; round < 5; ++round) {
        bool moved = true;
        while (moved) {
            moved = false;
            for (int i = 0; i < 6; ++i)
                for (float sgn : {1.0f, -1.0f}) {
                    ReloadShape tryit = best;
                    float* q[6] = {&tryit.close_at.x, &tryit.close_at.y, &tryit.close_at.z, &tryit.cant, &tryit.pitch, &tryit.yaw};
                    *q[i] = std::clamp(*p[i] + sgn * step[i], lo[i], hi[i]);
                    if (*q[i] == *p[i]) continue;
                    const float c = score(tryit, nullptr);
                    if (c < cost - 1e-4f) { cost = c; best = tryit; moved = true; }
                }
        }
        for (float& s : step) s *= 0.5f;
        TraceLog(LOG_INFO, "FITRELOAD round %d: cost %.3f", round, cost);
    }
    score(best, &after);
    char out[400];
    std::snprintf(out, sizeof out, "\nbefore: %s\nafter:  %s\nclose_at{%.3ff, %.3ff, %.3ff}, cant %.3f, pitch %.3f, yaw %.3f\n", before.c_str(), after.c_str(),
                  best.close_at.x, best.close_at.y, best.close_at.z, best.cant, best.pitch, best.yaw);
    reload_shape = best;
    return out;
}

}  // namespace dw
