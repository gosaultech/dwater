// damned_waters/engine/include/dw/telemetry.hpp
// Purpose: every run is recorded in SQLite (damned_waters.db): start/end time,
// runtime, frames, worst frame time, exit status. One insert at start, one
// update at exit: nothing on the hot path.
#ifndef DW_TELEMETRY_HPP
#define DW_TELEMETRY_HPP
#include <string>
struct sqlite3;
namespace dw {
class Telemetry {
public:
    explicit Telemetry(const std::string& path);
    ~Telemetry();
    void begin(const std::string& mode, const std::string& room);
    void end(const std::string& status, double runtime_s, long frames, double worst_frame_ms);
    long session() const { return session_; }
private:
    sqlite3* db_ = nullptr;
    long session_ = -1;
};
}  // namespace dw
#endif
