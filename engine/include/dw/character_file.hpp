// damned_waters/engine/include/dw/character_file.hpp
// Purpose: read a .dwc character file (built by tools/characters/build_characters.py
// from MakeHuman's CC0 body; the byte layout is documented in tools/characters/dwc.py).
// Pure data, no GPU: the loader is unit-tested, and Character uploads what it returns.
#ifndef DW_CHARACTER_FILE_HPP
#define DW_CHARACTER_FILE_HPP
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace dw {

struct FilePart {
    std::string name;
    std::vector<float> pos, nrm;                      // xyz per vertex
    std::vector<uint8_t> col;                         // rgba per vertex (sRGB)
    std::vector<uint8_t> mat, region;                 // per vertex
    std::vector<uint8_t> joint;                       // 4 per vertex
    std::vector<float> weight;                        // 4 per vertex, summing to 1
    std::vector<float> aux;                           // 1 per vertex: meaning set by the material (hair: edge fade)
    std::vector<uint16_t> index;                      // triangles
    size_t vertices() const { return pos.size() / 3; }
};

struct FileAnchor { std::string name; int joint = 0; std::array<float, 3> pos{}, dir{}; };

struct CharacterFile {
    std::vector<std::array<float, 3>> joints;         // rest-pose joint positions (m)
    std::vector<FilePart> parts;
    std::vector<FileAnchor> anchors;
    std::string error;                                // empty = loaded fine
    bool ok() const { return error.empty(); }
    const FilePart* part(const std::string& name) const;
    static CharacterFile load(const std::string& path);
};

}  // namespace dw
#endif
