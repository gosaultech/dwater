// damned_waters/engine/tests/test_death.cpp
// Purpose: GoogleTest suite for the death screen's timing (death.hpp): it goes dark before the
// words come, the words settle to their size, the drips only ever run on and stop, and the choice
// waits for the words.
#include <gtest/gtest.h>

#include "dw/death.hpp"

using namespace dw::death;

TEST(Death, DarkFirstThenTheWords) {
    EXPECT_FLOAT_EQ(darkness(0.0f), 0.0f);
    EXPECT_FLOAT_EQ(title(0.0f), 0.0f);
    EXPECT_GT(darkness(TITLE_FROM), 0.3f);   // it's well on its way to dark when the words start
    EXPECT_FLOAT_EQ(darkness(10.0f), 1.0f);
    EXPECT_FLOAT_EQ(title(10.0f), 1.0f);
    EXPECT_GT(title_scale(TITLE_FROM), 1.05f);
    EXPECT_FLOAT_EQ(title_scale(10.0f), 1.0f);
}

TEST(Death, DripsRunOnAndStop) {
    for (int i = 0; i < DRIPS; ++i) {
        float last = 0;
        for (float t = 0; t < 12.0f; t += 0.05f) {
            const float d = drip(i, t);
            EXPECT_GE(d, last) << i;   // never back up
            last = d;
        }
        EXPECT_FLOAT_EQ(drip(i, 0.0f), 0.0f);
        EXPECT_FLOAT_EQ(last, 1.0f);   // done
        EXPECT_NE(drip_letter(i), 3);   // never from the space between the words
        EXPECT_LE(drip_offset(i), 0.5f);
        EXPECT_GE(drip_offset(i), -0.5f);
    }
}

TEST(Death, TheChoiceWaitsForTheWords) {
    EXPECT_FALSE(choosing(TITLE_FROM));
    EXPECT_TRUE(choosing(TITLE_TO + 0.5f));
    EXPECT_GE(CHOICE_AT, TITLE_TO);
}
