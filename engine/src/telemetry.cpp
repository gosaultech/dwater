// damned_waters/engine/src/telemetry.cpp
// Purpose: SQLite session log (see telemetry.hpp).
#include "dw/telemetry.hpp"

#include <sqlite3.h>
#include <ctime>

namespace dw {

Telemetry::Telemetry(const std::string& path) {
    if (sqlite3_open(path.c_str(), &db_) != SQLITE_OK) { db_ = nullptr; return; }
    sqlite3_exec(db_, "PRAGMA journal_mode=WAL;"
                      "CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, started INTEGER,"
                      " ended INTEGER, mode TEXT, room TEXT, status TEXT, runtime_s REAL, frames INTEGER, worst_frame_ms REAL);",
                 nullptr, nullptr, nullptr);
}

Telemetry::~Telemetry() { if (db_) sqlite3_close(db_); }

void Telemetry::begin(const std::string& mode, const std::string& room) {
    if (!db_) return;
    sqlite3_stmt* st = nullptr;
    sqlite3_prepare_v2(db_, "INSERT INTO sessions(started, mode, room, status) VALUES(?,?,?, 'running')", -1, &st, nullptr);
    sqlite3_bind_int64(st, 1, static_cast<sqlite3_int64>(std::time(nullptr)));
    sqlite3_bind_text(st, 2, mode.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(st, 3, room.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_step(st);
    sqlite3_finalize(st);
    session_ = static_cast<long>(sqlite3_last_insert_rowid(db_));
}

void Telemetry::end(const std::string& status, double runtime_s, long frames, double worst_frame_ms) {
    if (!db_ || session_ < 0) return;
    sqlite3_stmt* st = nullptr;
    sqlite3_prepare_v2(db_, "UPDATE sessions SET ended=?, status=?, runtime_s=?, frames=?, worst_frame_ms=? WHERE id=?", -1, &st, nullptr);
    sqlite3_bind_int64(st, 1, static_cast<sqlite3_int64>(std::time(nullptr)));
    sqlite3_bind_text(st, 2, status.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(st, 3, runtime_s);
    sqlite3_bind_int64(st, 4, frames);
    sqlite3_bind_double(st, 5, worst_frame_ms);
    sqlite3_bind_int64(st, 6, session_);
    sqlite3_step(st);
    sqlite3_finalize(st);
}

}  // namespace dw
