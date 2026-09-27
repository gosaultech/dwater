# damned_waters/engine/CMakeLists.txt
# Purpose: the Damned Waters C++ engine (raylib 5.5, C++17).
# Dependencies are fetched and pinned (like Bumper Ball Maze):
#   raylib 5.5, nlohmann/json 3.11.3, GoogleTest 1.14. SQLite: system package
#   when present (macOS SDK / libsqlite3-dev), else the amalgamation.
# Build:  cmake -S engine -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
cmake_minimum_required(VERSION 3.20)
project(damned_waters LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
option(DW_BUILD_TESTS "Build unit tests" ON)

include(FetchContent)
set(BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_WAYLAND OFF CACHE BOOL "" FORCE)
FetchContent_Declare(raylib GIT_REPOSITORY https://github.com/raysan5/raylib.git GIT_TAG 5.5 GIT_SHALLOW TRUE)
FetchContent_Declare(json URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz)
FetchContent_MakeAvailable(raylib json)

find_package(SQLite3 QUIET)
if(NOT SQLite3_FOUND)
    FetchContent_Declare(sqlite3_src
        URL https://www.sqlite.org/2024/sqlite-amalgamation-3450000.zip
        SOURCE_SUBDIR _no_cmake_here)
    FetchContent_MakeAvailable(sqlite3_src)
    add_library(sqlite3_static STATIC ${sqlite3_src_SOURCE_DIR}/sqlite3.c)
    target_include_directories(sqlite3_static SYSTEM PUBLIC ${sqlite3_src_SOURCE_DIR})
    add_library(SQLite::SQLite3 ALIAS sqlite3_static)
endif()

# Core library: pure logic + data (no window needed) so tests link it without a GPU.
add_library(dw_core STATIC src/room_spec.cpp src/telemetry.cpp)
target_include_directories(dw_core PUBLIC include)
target_link_libraries(dw_core PUBLIC nlohmann_json::nlohmann_json SQLite::SQLite3 raylib)
target_compile_definitions(dw_core PUBLIC DW_REPO_ROOT="${CMAKE_SOURCE_DIR}/..")

add_executable(damned_waters src/main.cpp src/game.cpp src/character.cpp src/mesh_builder.cpp src/shaders.cpp)
target_link_libraries(damned_waters PRIVATE dw_core raylib)
if(MSVC)
    target_compile_options(damned_waters PRIVATE /W4)
else()
    target_compile_options(damned_waters PRIVATE -Wall -Wextra -Wno-missing-field-initializers)
endif()

if(DW_BUILD_TESTS)
    FetchContent_Declare(googletest URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz)
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    add_executable(dw_tests tests/test_core.cpp src/mesh_builder.cpp)
    target_link_libraries(dw_tests PRIVATE dw_core GTest::gtest_main)
    enable_testing()
    add_test(NAME dw_tests COMMAND dw_tests)
endif()
