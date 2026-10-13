// damned_waters/engine/tests/test_title.cpp
// Purpose: GoogleTest suite for the title screen (title.hpp): the name comes up before the choice,
// a press before the choice is up picks nothing, the cursor goes round both ways, New Game's dark
// comes all the way down; and the route's end gives way to the title once its last line is up.
#include <gtest/gtest.h>

#include "dw/title.hpp"

using namespace dw;

TEST(Title, TheNameBeforeTheChoice) {
    EXPECT_FLOAT_EQ(title::name(0.0f), 0.0f);
    EXPECT_FLOAT_EQ(title::menu(0.0f), 0.0f);
    EXPECT_GT(title::name(title::MENU_FROM), 0.5f);   // well up by the time the choice starts
    EXPECT_FLOAT_EQ(title::menu(title::MENU_FROM), 0.0f);
    EXPECT_FLOAT_EQ(title::name(10.0f), 1.0f);
    EXPECT_FLOAT_EQ(title::menu(10.0f), 1.0f);
}

TEST(Title, NoChoosingUntilTheChoiceIsUp) {
    EXPECT_FALSE(title::choosing(0.0f));
    EXPECT_FALSE(title::choosing(title::MENU_FROM - 0.01f));
    EXPECT_TRUE(title::choosing(title::MENU_FROM));
}

TEST(Title, TheCursorGoesRoundBothWays) {
    EXPECT_EQ(title::next(title::NEW_GAME, -1), title::QUIT);   // down
    EXPECT_EQ(title::next(title::QUIT, -1), title::NEW_GAME);   // down, round the bottom
    EXPECT_EQ(title::next(title::NEW_GAME, 1), title::QUIT);    // up, round the top
    EXPECT_EQ(title::next(title::QUIT, 1), title::NEW_GAME);
    EXPECT_EQ(title::next(title::QUIT, 0), title::QUIT);        // no push, no move
}

TEST(Title, NewGameBringsTheDarkAllTheWayDown) {
    float last = 0;
    for (float t = 0; t <= title::LEAVE + 0.5f; t += 0.05f) {
        const float d = title::leaving(t);
        EXPECT_GE(d, last);
        last = d;
    }
    EXPECT_FLOAT_EQ(title::leaving(0.0f), 0.0f);
    EXPECT_FLOAT_EQ(title::leaving(title::LEAVE), 1.0f);
    EXPECT_FALSE(title::gone(title::LEAVE - 0.01f));
    EXPECT_TRUE(title::gone(title::LEAVE));
}

TEST(Title, TheRoutesEndGivesWayOnceItsLastLineIsUp) {
    EXPECT_FALSE(death::end_over(death::END_LINE_FROM));
    EXPECT_FALSE(death::end_over(death::END_LINE_TO - 0.01f));
    EXPECT_TRUE(death::end_over(death::END_LINE_TO));
    EXPECT_FLOAT_EQ(death::end_line(death::END_LINE_TO), 1.0f);   // the line is all the way up by then
}
