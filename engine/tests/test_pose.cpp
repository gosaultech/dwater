// damned_waters/engine/tests/test_pose.cpp
// Purpose: GoogleTest suite for posing the dead (character.hpp's mirror_targets): a body sprawled
// the other way round trades its left and right limbs' targets and turns every lean and twist to
// the other side; mirrored twice, it is as it was.
#include <gtest/gtest.h>

#include "dw/character.hpp"

using namespace dw;

TEST(Pose, MirroredTheLimbsTradeSides) {
    Vector3 T[J_COUNT]{};
    T[J_SHO_L] = {2.95f, 0.0f, -0.35f};   // face down: the left arm reaching on along the ground,
    T[J_SHO_R] = {0.12f, 0.0f, 0.18f};    // the right along its side,
    T[J_HEAD] = {0.05f, 1.0f, 0.1f};      // the face turned to the left
    mirror_targets(T);
    EXPECT_FLOAT_EQ(T[J_SHO_R].x, 2.95f);   // now the right arm reaches,
    EXPECT_FLOAT_EQ(T[J_SHO_R].z, 0.35f);   // out to its own side
    EXPECT_FLOAT_EQ(T[J_SHO_L].x, 0.12f);
    EXPECT_FLOAT_EQ(T[J_SHO_L].z, -0.18f);
    EXPECT_FLOAT_EQ(T[J_HEAD].x, 0.05f);    // a nod is a nod either way round,
    EXPECT_FLOAT_EQ(T[J_HEAD].y, -1.0f);    // but the face turns the other way
    EXPECT_FLOAT_EQ(T[J_HEAD].z, -0.1f);
}

TEST(Pose, MirroredTwiceItIsAsItWas) {
    Vector3 T[J_COUNT]{}, U[J_COUNT]{};
    for (int k = 0; k < J_COUNT; ++k) T[k] = U[k] = {0.1f * float(k), 0.2f - 0.01f * float(k), 0.03f * float(k) - 0.5f};
    mirror_targets(T);
    mirror_targets(T);
    for (int k = 0; k < J_COUNT; ++k) {
        EXPECT_FLOAT_EQ(T[k].x, U[k].x);
        EXPECT_FLOAT_EQ(T[k].y, U[k].y);
        EXPECT_FLOAT_EQ(T[k].z, U[k].z);
    }
}
