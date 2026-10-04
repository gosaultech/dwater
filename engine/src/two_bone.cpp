// damned_waters/engine/src/two_bone.cpp
// Purpose: the two-bone arm solve (two_bone.hpp): the elbow from the triangle the bones make with
// the gap to the goal, then the upper arm turned onto the goal with the elbow kept where the pose
// had it; and two measures of how an arm looks (its elbow hanging down, its bend) for the aim
// fitters. Pure maths, no window: the tests run it directly.
#include "dw/two_bone.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace dw {

TwoBone solve_two_bone(Vector3 oe, Vector3 ow, Vector3 goal, Vector3 hinge) {
    // The elbow: |oe + Rx(e) ow| = |goal|, i.e. P cos e + Q sin e = C.
    const float P = oe.y * ow.y + oe.z * ow.z, Q = oe.z * ow.y - oe.y * ow.z;
    const float C = 0.5f * (Vector3LengthSqr(goal) - Vector3LengthSqr(oe) - Vector3LengthSqr(ow)) - oe.x * ow.x;
    const float M = std::max(std::sqrt(P * P + Q * Q), 1e-6f);
    TwoBone out{std::clamp(std::atan2(Q, P) + std::acos(std::clamp(C / M, -1.0f, 1.0f)), 0.0f, 2.6f), MatrixIdentity()};
    // The upper arm: shoulder-to-wrist as built (v) onto shoulder-to-goal, the hinge (x as built)
    // toward the one asked for. Two frames, each an axis and a second squared to it; the turn takes
    // one onto the other.
    const Vector3 v = Vector3Add(oe, Vector3Transform(ow, MatrixRotateX(out.elbow)));
    auto frame = [](Vector3 a, Vector3 b) {
        const Vector3 x = Vector3Normalize(a), y = Vector3Normalize(Vector3Subtract(b, Vector3Scale(x, Vector3DotProduct(b, x))));
        return std::array<Vector3, 3>{x, y, Vector3CrossProduct(x, y)};
    };
    const auto A = frame(v, {1, 0, 0}), B = frame(goal, hinge);
    float* m[3][3] = {{&out.turn.m0, &out.turn.m4, &out.turn.m8}, {&out.turn.m1, &out.turn.m5, &out.turn.m9}, {&out.turn.m2, &out.turn.m6, &out.turn.m10}};
    auto at = [](Vector3 p, int k) { return k == 0 ? p.x : k == 1 ? p.y : p.z; };
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 3; ++c) {
            float sum = 0;
            for (size_t i = 0; i < 3; ++i) sum += at(B[i], r) * at(A[i], c);   // B A^T
            *m[r][c] = sum;
        }
    return out;
}

float elbow_not_down(Vector3 sh, Vector3 el, Vector3 wr) {
    const Vector3 sw = Vector3Subtract(wr, sh);
    const float t = std::clamp(Vector3DotProduct(Vector3Subtract(el, sh), sw) / std::max(Vector3LengthSqr(sw), 1e-6f), 0.0f, 1.0f);
    const Vector3 off = Vector3Subtract(el, Vector3Add(sh, Vector3Scale(sw, t)));
    const float len = Vector3Length(off);
    if (len < 1e-4f) return 0;
    const float shy = std::max(0.0f, 0.82f + off.y / len);   // short of pointing down (cos 35 degrees)
    return 3000.0f * len * len * shy * shy + (off.y > 0 ? 2000.0f * off.y * off.y : 0.0f);
}

float elbow_bend(Vector3 sh, Vector3 el, Vector3 wr) {
    return std::acos(std::clamp(Vector3DotProduct(Vector3Normalize(Vector3Subtract(el, sh)), Vector3Normalize(Vector3Subtract(wr, el))), -1.0f, 1.0f));
}
Vector3 slerp_angles(Vector3 a, Vector3 b, float k) {
    auto turn = [](Vector3 e) { return MatrixMultiply(MatrixMultiply(MatrixRotateZ(e.z), MatrixRotateX(e.x)), MatrixRotateY(e.y)); };
    const Matrix m = QuaternionToMatrix(QuaternionSlerp(QuaternionFromMatrix(turn(a)), QuaternionFromMatrix(turn(b)), k));
    return {std::asin(std::clamp(-m.m9, -1.0f, 1.0f)), std::atan2(m.m8, m.m10), std::atan2(m.m1, m.m5)};
}

void swing_twist(Quaternion q, Vector3 axis, float& swing, float& twist) {
    axis = Vector3Normalize(axis);
    const float d = q.x * axis.x + q.y * axis.y + q.z * axis.z;
    Quaternion t{axis.x * d, axis.y * d, axis.z * d, q.w};   // the part of q about the axis
    const float n = std::sqrt(t.x * t.x + t.y * t.y + t.z * t.z + t.w * t.w);
    if (n < 1e-6f) {   // turned half round about some line across the axis: all swing
        swing = PI;
        twist = 0;
        return;
    }
    t = {t.x / n, t.y / n, t.z / n, t.w / n};
    twist = 2.0f * std::atan2(t.x * axis.x + t.y * axis.y + t.z * axis.z, t.w);
    if (twist > PI) twist -= 2 * PI;
    if (twist < -PI) twist += 2 * PI;
    const Quaternion sw = QuaternionMultiply(q, QuaternionInvert(t));   // q = swing * twist
    swing = 2.0f * std::acos(std::clamp(std::fabs(sw.w), 0.0f, 1.0f));
}

}  // namespace dw
