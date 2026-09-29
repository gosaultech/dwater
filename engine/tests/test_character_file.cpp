// damned_waters/engine/tests/test_character_file.cpp
// Purpose: GoogleTest suite for the .dwc loader: the shipped survivor and Drowned citizens load
// with a full rig and sane skinning, and a damaged file gives an error instead of a crash.
#include <gtest/gtest.h>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iterator>

#include "dw/character_file.hpp"
#include "dw/room_spec.hpp"

using namespace dw;

namespace {
const std::string SURVIVOR = repo_root() + "/engine/assets/characters/survivor.dwc";

std::vector<char> read_all(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(in), {}};
}

std::string write_temp(const std::string& name, const std::vector<char>& bytes) {
    const std::string path = testing::TempDir() + name;
    std::ofstream(path, std::ios::binary).write(bytes.data(), std::streamsize(bytes.size()));
    return path;
}
}  // namespace

TEST(CharacterFile, ShippedSurvivorLoadsWithAFullRig) {
    const CharacterFile f = CharacterFile::load(SURVIVOR);
    ASSERT_TRUE(f.ok()) << f.error;
    EXPECT_EQ(f.joints.size(), 24u);                       // dw::J_COUNT
    for (const char* name : {"body", "jeans", "hoodie", "jacket", "boot_l", "boot_r"})
        EXPECT_NE(f.part(name), nullptr) << name;
    EXPECT_EQ(f.part("cape"), nullptr);
    bool backpack = false;
    for (const auto& a : f.anchors) backpack |= a.name == "backpack";
    EXPECT_TRUE(backpack);
}

TEST(CharacterFile, EveryVertexIsFullySkinned) {
    const CharacterFile f = CharacterFile::load(SURVIVOR);
    ASSERT_TRUE(f.ok()) << f.error;
    for (const auto& p : f.parts) {
        ASSERT_EQ(p.weight.size(), p.vertices() * 4) << p.name;
        ASSERT_EQ(p.index.size() % 3, 0u) << p.name;
        for (size_t v = 0; v < p.vertices(); ++v) {
            const float* w = &p.weight[v * 4];
            ASSERT_NEAR(w[0] + w[1] + w[2] + w[3], 1.0f, 1e-3f) << p.name << " vertex " << v;
        }
        for (float x : p.pos) ASSERT_TRUE(std::isfinite(x)) << p.name;
    }
}

// The Drowned citizens: each loads, is fully skinned, and every part fits the engine's 16-bit
// index buffers (a part past 65535 vertices would wrap its indices and tear).
TEST(CharacterFile, ShippedCitizensLoadAndFitSixteenBitIndices) {
    for (const char* id : {"office_worker", "pieter", "woman_dress"}) {
        const CharacterFile f = CharacterFile::load(repo_root() + "/engine/assets/characters/" + id + ".dwc");
        ASSERT_TRUE(f.ok()) << id << ": " << f.error;
        EXPECT_EQ(f.joints.size(), 24u) << id;
        EXPECT_NE(f.part("body"), nullptr) << id;
        bool drips = false;
        for (const auto& a : f.anchors) drips |= a.name == "drip_chin";
        EXPECT_TRUE(drips) << id;
        EXPECT_NE(f.part("throat"), nullptr) << id;   // the scream's black hollow
        for (const auto& p : f.parts) {
            EXPECT_LE(p.vertices(), 65535u) << id << "/" << p.name;
            for (size_t v = 0; v < p.vertices(); ++v) {
                const float* w = &p.weight[v * 4];
                ASSERT_NEAR(w[0] + w[1] + w[2] + w[3], 1.0f, 1e-3f) << id << "/" << p.name << " vertex " << v;
            }
        }
    }
}

TEST(CharacterFile, TruncatedFileIsAnErrorNotACrash) {
    const std::vector<char> whole = read_all(SURVIVOR);
    ASSERT_GT(whole.size(), 4096u);
    for (size_t keep : {size_t(6), size_t(200), whole.size() / 2, whole.size() - 3}) {
        const CharacterFile f = CharacterFile::load(write_temp("dw_truncated.dwc", {whole.begin(), whole.begin() + long(keep)}));
        EXPECT_FALSE(f.ok()) << "kept " << keep << " bytes";
    }
}

TEST(CharacterFile, ForeignOrMissingFileIsRejected) {
    EXPECT_NE(CharacterFile::load(write_temp("dw_foreign.dwc", {'G', 'L', 'T', 'F', 1, 0, 0, 0})).error.find("not a .dwc"),
              std::string::npos);
    EXPECT_NE(CharacterFile::load("/nonexistent/x.dwc").error.find("cannot open"), std::string::npos);
}

TEST(CharacterFile, OutOfRangeJointIsRejected) {
    std::vector<char> b = read_all(SURVIVOR);
    ASSERT_GT(b.size(), 4096u);
    // The first part's header follows the joint table: magic, version, count, 24 x 12 bytes, part count.
    const size_t part0 = 4 + 4 + 4 + 24 * 12 + 4;
    uint32_t nv = 0;
    std::memcpy(&nv, &b[part0 + 24], 4);
    const size_t joint_ids = part0 + 24 + 8 + size_t(nv) * (12 + 12 + 4 + 1 + 1);
    b[joint_ids] = char(200);                              // vertex 0's first joint: far past the rig
    EXPECT_NE(CharacterFile::load(write_temp("dw_badjoint.dwc", b)).error.find("joint out of range"), std::string::npos);
}
