# Damned Waters Engine (C++ / raylib) - Milestone 1

Fixed-camera survival horror on a custom C++17 engine, built on the same stack as
Bumper Ball Maze: raylib 5.5, CMake, SQLite and GoogleTest. The Godot prototype
remains in `../game/`; its room data and pre-rendered backgrounds feed this engine directly.

## Milestone 1: what it is

One room (`gang`, the entrance hall) with:

- **Backgrounds and depth.** Pre-rendered Cycles backgrounds, each with a painted depth map.
  Characters are hidden correctly behind painted furniture, like RE (1998).
- **Camera cuts.** The camera switches shots as you cross zones. The current shot is kept near
  the thresholds (hysteresis), so it never flickers back and forth.
- **The survivor.** Walk and run, tank or modern controls, quick turn, and an aim pose.
- **One Verdronkene.** Its brain runs IDLE → ALERT → PURSUIT → ATTACK (0.85 s readable
  wind-up) → RECOVERY. The strike does 20 damage and knocks you back.
- **Characters built in C++ at startup.** There are no model files. Torso, arms and legs are
  swept tubes regenerated every frame through the joints, so elbows, knees and the waist bend
  without seams.
- **A horror lighting model.** Procedural surface detail, bump detail, wet-versus-dry
  specular, room lights, a cold rim, and fog. Grain and vignette are added in post.

**Not ported yet:** weapons and combat, the other rooms, doors, UI and inventory, saves and audio.

## Build and run (macOS, Apple Silicon)

```bash
xcode-select --install        # compilers (once)
brew install cmake            # once
cmake -S engine -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/damned_waters                     # play
./build/damned_waters --capture /tmp/dw   # stage 4 setups and save screenshots
./build/dw_tests                          # unit tests
```

Dependencies are fetched on the first configure and pinned: raylib 5.5, nlohmann/json 3.11.3
and GoogleTest 1.14. SQLite comes from the macOS SDK, or from the amalgamation if the SDK copy
isn't found. The engine reads `../game/data/rooms` and `../game/assets/rooms` through
`DW_REPO_ROOT`, which CMake sets at compile time.

## Controls

| Action | Key |
|---|---|
| Move | WASD / arrows |
| Run | Shift |
| Quick turn (180 degrees) | Q |
| Aim | Right mouse / K |
| Toggle tank / modern controls | T |
| Debug line (fps, shot, position) | F3 |

In modern mode, controls keep the previous camera's direction across a cut until you change
direction, so a cut never reverses your movement.

## Architecture

| File | Role |
|---|---|
| `include/dw/core.hpp` | Pure logic: depth codec, shot selection, movement maths, 2D collision, enemy brain. Header-only and unit-tested. |
| `include/dw/room_spec.hpp`, `src/room_spec.cpp` | Parses the RoomSpec JSON into colliders, shots, lights and spawns. It is the same file Blender renders from. |
| `include/dw/mesh_builder.hpp`, `src/mesh_builder.cpp` | Ellipsoids with sculpt bumps, drapes and chains, plus `Sweep`, the per-frame tube along a Catmull-Rom curve with parallel-transport frames. |
| `include/dw/character.hpp`, `src/character.cpp` | Joint forward kinematics, the cast, and the pose tables. |
| `src/shaders.cpp` | All GLSL, embedded. |
| `src/game.cpp` | Room, cameras, input, AI, and render order. |
| `src/main.cpp` | Entry point, capture mode, and telemetry. |

**Render order per frame:**

1. The background is drawn, writing `gl_FragDepth` from its painted depth.
2. Characters are drawn depth-tested against the painting.
3. Blob shadows are drawn.
4. The post pass (grain and vignette) goes to the window.

**Pose convention (character axes):**

- Downward limbs swing forward with +x, and knees bend with -x.
- The spine leans back with +x, so a forward lean is -x.
- Rolling with +z moves a hanging limb's tip toward the character's right.

## Telemetry

Every run is logged in `damned_waters.db` next to the binary. The `sessions` table records
start and end times, mode, room, status, runtime, frame count and the worst frame time.

```bash
sqlite3 build/damned_waters.db "SELECT mode, status, runtime_s, frames, worst_frame_ms FROM sessions ORDER BY id DESC LIMIT 5;"
```

## Next milestones

1. Look pass on the Drowned: make the face in the sheet read from high cameras, and add water drips.
2. Combat port: pistol and shotgun, kick, dodge, hit-stop.
3. Rooms `voorkamer` and `kelder`, with doors and transitions.
4. UI, inventory, saves.
5. Audio: a C++ synth like Bumper Ball Maze's.
6. Remaining creatures in the stylized-grotesque style.
