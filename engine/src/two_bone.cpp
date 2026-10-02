// damned_waters/engine/src/two_bone.cpp
// Purpose: the two-bone arm solve (two_bone.hpp): the elbow from the triangle the bones make with
// the gap to the goal, then the upper arm turned onto the goal with the elbow kept where the pose
// had it. Pure maths, no window: the tests run it directly.
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
}  // namespace dw
