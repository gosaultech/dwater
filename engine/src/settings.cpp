// damned_waters/engine/src/settings.cpp
// Purpose: see settings.hpp. A key/value table: easy to read with any SQLite tool, and new
// options need no schema change.
#include "dw/settings.hpp"

#include <sqlite3.h>
#include <cstdlib>
#include <string>
#include <utility>

namespace dw {
namespace {
constexpr const char* SCHEMA = "CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);";
}  // namespace

Settings Settings::load(const std::string& db_path) {
    Settings s;
    sqlite3* db = nullptr;
    if (sqlite3_open_v2(db_path.c_str(), &db, SQLITE_OPEN_READWRITE, nullptr) != SQLITE_OK) {
        sqlite3_close(db);   // no database yet: the defaults
        return s;
    }
    sqlite3_stmt* st = nullptr;
    if (sqlite3_prepare_v2(db, "SELECT key, value FROM settings", -1, &st, nullptr) == SQLITE_OK) {
        while (sqlite3_step(st) == SQLITE_ROW) {
            const std::string key = reinterpret_cast<const char*>(sqlite3_column_text(st, 0));
            const int v = std::atoi(reinterpret_cast<const char*>(sqlite3_column_text(st, 1)));
            if (key == "scheme" && v >= 0 && v < int(Scheme::Count)) s.scheme = Scheme(v);
            else if (key == "slowmo") s.slowmo = v != 0;
            else if (key == "tank") s.tank = v != 0;
            else if (key == "run" && v >= 0 && v < int(RunMode::Count)) s.run = RunMode(v);
            else if (key == "back_turn") s.back_turn = v != 0;
        }
    }
    sqlite3_finalize(st);
    sqlite3_close(db);
    return s;
}

bool Settings::save(const std::string& db_path) const {
    sqlite3* db = nullptr;
    if (sqlite3_open(db_path.c_str(), &db) != SQLITE_OK) { sqlite3_close(db); return false; }
    bool ok = sqlite3_exec(db, SCHEMA, nullptr, nullptr, nullptr) == SQLITE_OK;
    sqlite3_stmt* st = nullptr;
    ok = ok && sqlite3_prepare_v2(db, "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", -1, &st, nullptr) == SQLITE_OK;
    const std::pair<const char*, int> rows[] = {{"scheme", int(scheme)}, {"slowmo", slowmo ? 1 : 0}, {"tank", tank ? 1 : 0},
                                                {"run", int(run)}, {"back_turn", back_turn ? 1 : 0}};
    for (const auto& [key, value] : rows) {
        if (!ok) break;
        const std::string v = std::to_string(value);
        sqlite3_bind_text(st, 1, key, -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(st, 2, v.c_str(), -1, SQLITE_TRANSIENT);
        ok = sqlite3_step(st) == SQLITE_DONE;
        sqlite3_reset(st);
    }
    sqlite3_finalize(st);
    sqlite3_close(db);
    return ok;
}

}  // namespace dw
