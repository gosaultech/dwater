// damned_waters/engine/include/dw/settings.hpp
// Purpose: the player's options, kept in the game's SQLite database (damned_waters.db, table
// `settings`, one row per option) so they survive a restart: the controller layout, how running is
// asked for, the back + Circle quick turn, slow motion on a perfect dodge, tank controls. Loaded
// once at start, saved when changed in the pause menu; nothing on the hot path. Unit-tested
// against a temporary database.
#ifndef DW_SETTINGS_HPP
#define DW_SETTINGS_HPP
#include <string>

#include "dw/controls.hpp"

namespace dw {

struct Settings {
    Scheme scheme = Scheme::TypeA;   // the controller layout
    bool slowmo = false;             // slow motion on a perfect dodge (off: the opening and the bonus only)
    bool tank = false;               // classic tank controls (modern, camera-relative, by default)
    RunMode run = RunMode::Analog;   // how running is asked for: the stick's tilt, L3 held or clicked, or a button held
    bool back_turn = true;           // the stick back + the right face button quick-turns (where that button dodges)

    // Missing file or rows: the defaults. A value out of range falls back too.
    static Settings load(const std::string& db_path);
    bool save(const std::string& db_path) const;
};

}  // namespace dw
#endif
