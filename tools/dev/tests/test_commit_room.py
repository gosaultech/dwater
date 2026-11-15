# damned_waters/tools/dev/tests/test_commit_room.py
# Purpose: the sign-off's bookkeeping (commit_room.py): a room is added to the generator's sets
# once, in order, without touching the rest of the line; a missing set is an error, not a silence.
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commit_room  # noqa: E402

SRC = 'A = 1\nDRESSED = {"dam", "rokin_noord"}   # the rooms whose plates show dress()\nLOOK2 = set()\nfor _r in []:\n    LOOK2.add(_r)\n'


class CommitRoomTests(unittest.TestCase):
    def test_a_room_joins_both_sets_in_order(self):
        out = commit_room.add_to_set(commit_room.add_to_set(SRC, "DRESSED", "apotheek"), "LOOK2", "apotheek")
        self.assertIn('DRESSED = {"apotheek", "dam", "rokin_noord"}   # the rooms whose plates show dress()', out)
        self.assertIn('LOOK2 = {"apotheek"}\nfor _r in []:', out)

    def test_joining_twice_changes_nothing(self):
        once = commit_room.add_to_set(SRC, "DRESSED", "dam")
        self.assertEqual(once, SRC)
        self.assertEqual(commit_room.add_to_set(commit_room.add_to_set(SRC, "LOOK2", "dam"), "LOOK2", "dam").count('"dam"'), 3)

    def test_a_missing_set_is_an_error(self):
        with self.assertRaises(ValueError):
            commit_room.add_to_set(SRC, "NOPE", "dam")


if __name__ == "__main__":
    unittest.main()
