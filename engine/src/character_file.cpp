// damned_waters/engine/src/character_file.cpp
// Purpose: see character_file.hpp. Reads the whole file once, then walks it with
// bounds checks: a truncated or foreign file gives an error, never a crash.
#include "dw/character_file.hpp"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <iterator>

namespace dw {
namespace {
class Reader {
public:
    explicit Reader(std::vector<char> b) : b_(std::move(b)) {}
    bool take(void* dst, size_t n) {
        if (o_ + n > b_.size()) { bad_ = true; return false; }
        std::memcpy(dst, b_.data() + o_, n);
        o_ += n;
        return true;
    }
    uint32_t u32() { uint32_t v = 0; take(&v, 4); return v; }   // little-endian hosts (x86, Apple Silicon)
    template <class T> void vec(std::vector<T>& v, size_t count) {
        if (count > (b_.size() - std::min(o_, b_.size())) / sizeof(T)) { bad_ = true; return; }
        v.resize(count);
        take(v.data(), count * sizeof(T));
    }
    std::string name() {
        char n[24] = {};
        take(n, 24);
        n[23] = 0;
        return n;
    }
    bool bad() const { return bad_; }
private:
    std::vector<char> b_;
    size_t o_ = 0;
    bool bad_ = false;
};
}  // namespace

const FilePart* CharacterFile::part(const std::string& name) const {
    for (const auto& p : parts)
        if (p.name == name) return &p;
    return nullptr;
}

CharacterFile CharacterFile::load(const std::string& path) {
    CharacterFile f;
    std::ifstream in(path, std::ios::binary);
    if (!in) { f.error = "cannot open " + path; return f; }
    Reader r(std::vector<char>(std::istreambuf_iterator<char>(in), {}));
    char magic[4] = {};
    r.take(magic, 4);
    if (std::memcmp(magic, "DWC1", 4) != 0) { f.error = path + ": not a .dwc file"; return f; }
    const uint32_t version = r.u32();   // 2 adds a spare value per vertex (aux); 1 still loads
    if (version != 1 && version != 2) { f.error = path + ": unsupported version"; return f; }
    const uint32_t nj = r.u32();
    if (nj > 64) { f.error = path + ": too many joints"; return f; }
    f.joints.resize(nj);
    for (auto& j : f.joints) r.take(j.data(), 12);
    const uint32_t np = r.u32();
    for (uint32_t i = 0; i < np && !r.bad(); ++i) {
        FilePart p;
        p.name = r.name();
        const uint32_t nv = r.u32(), ni = r.u32();
        if (nv > 65535 || ni % 3) { f.error = path + ": bad part " + p.name; return f; }
        r.vec(p.pos, size_t(nv) * 3);
        r.vec(p.nrm, size_t(nv) * 3);
        r.vec(p.col, size_t(nv) * 4);
        r.vec(p.mat, nv);
        r.vec(p.region, nv);
        r.vec(p.joint, size_t(nv) * 4);
        r.vec(p.weight, size_t(nv) * 4);
        if (version >= 2) r.vec(p.aux, nv);
        else p.aux.assign(nv, 0.0f);
        r.vec(p.index, ni);
        for (uint16_t ix : p.index)
            if (ix >= nv) { f.error = path + ": index out of range in " + p.name; return f; }
        for (uint8_t j : p.joint)
            if (j >= nj) { f.error = path + ": joint out of range in " + p.name; return f; }
        f.parts.push_back(std::move(p));
    }
    const uint32_t na = r.bad() ? 0 : r.u32();
    for (uint32_t i = 0; i < na && !r.bad(); ++i) {
        FileAnchor a;
        a.name = r.name();
        uint8_t hdr[4] = {};
        r.take(hdr, 4);
        a.joint = hdr[0];
        r.take(a.pos.data(), 12);
        r.take(a.dir.data(), 12);
        f.anchors.push_back(a);
    }
    if (r.bad()) f.error = path + ": truncated";
    return f;
}

}  // namespace dw
