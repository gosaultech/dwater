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

## Build and run (macOS and Windows)

The same three commands on every platform, through CMake presets (`engine/CMakePresets.json`).
The first configure downloads the pinned dependencies (raylib 5.5, nlohmann/json 3.11.3,
GoogleTest 1.14, and SQLite on Windows), so the first build takes a few minutes. Builds land in
`build/<platform>/` at the repo root.

**macOS (Apple Silicon M1 to M4, or Intel)**

```bash
xcode-select --install          # compilers (once)
brew install cmake              # CMake 3.21 or newer (once)
cd engine
cmake --preset macos            # configure
cmake --build --preset macos    # build
ctest --preset macos            # unit tests
../build/macos/damned_waters    # play
```

**Windows 10 or 11**

Install once: Visual Studio 2022 (Community or Build Tools) with *Desktop development with C++*
(it includes CMake), and Git. Then, in a *Developer PowerShell for VS*:

```powershell
cd engine
cmake --preset windows
cmake --build --preset windows
ctest --preset windows
..\build\windows\Release\damned_waters.exe
```

The game finds its rooms through `DW_REPO_ROOT`, which CMake bakes in at configure time, so
run it from this checkout. On the Mac it draws through Apple's OpenGL 4.1 (layered on Metal);
the shaders are GLSL 3.30 core, which both platforms support.

**Tools** (swap in `build\windows\Release\` on Windows):

```bash
../build/macos/damned_waters --capture /tmp/dw   # stage the capture setups and save screenshots
../build/macos/damned_waters --flashlight --capture /tmp/dw   # the same with the flashlight on
../build/macos/damned_waters --sheet /tmp/dw     # studio turnaround of every character
../build/macos/damned_waters --sheet /tmp/dw --only pieter,survivor               # just those
../build/macos/damned_waters --view drowned1@head,0,5,0.5,0,-0.05,30 face.png     # one close-up
../build/macos/damned_waters --view m92fs,0,0,2.0,0,0,8.3 pistol.png              # a gun, catalogue-lit
../build/macos/damned_waters --view r870/wood,30,14,1.6,0.05,0,14 shotgun.png      # the 870 in walnut
../build/macos/damned_waters --fit870    # fit the arms and wrists that hold the 870, print them, exit
```

`--view` takes `who,orbit,elevation,distance,target_x,target_y,fov`. `who` is `survivor` or
`drowned0`..`drowned2` (the office worker, Sanne, Pieter). Add `@head`, `@chest`, `@pelvis` or
`@hand` to orbit that joint; the target is then an offset from it, and `@head` starts from the
face. Then any of `/pose=aim`, `/gun=1` (the 870 in hand), `/limp=1`, `/cut=3+8`.

`who` can also be a gun, `m92fs` or `r870`, lit like a catalogue photo so it can be held up
against reference photos: `/slide=1` works the slide or fore-end back, `/roll=20` turns the
picture, `/bg=dark` puts it on black, `/wood` gives the 870 its walnut stock, `/obj=name` writes
the meshes out as `name_fixed.obj` and `name_moving.obj` (full precision, for matching a camera
to a photo).

Dependencies are fetched on the first configure and pinned: raylib 5.5, nlohmann/json 3.11.3
and GoogleTest 1.14. SQLite comes from the macOS SDK, or from the amalgamation if the SDK copy
isn't found. The engine reads `../game/data/rooms` and `../game/assets/rooms` through
`DW_REPO_ROOT`, which CMake sets at compile time.

## Controls

Controller first: any DualSense, Xbox or Switch Pro controller (USB or Bluetooth) on both
macOS and Windows, with the keyboard and mouse working alongside. Pick the layout in the pause
menu (Options/Start or Esc); it's saved in `damned_waters.db` with the other options. Buttons
are named by position (PlayStation / Xbox):

| Action | Type A (RE Remake) | Type B (Souls) | Type C (Shooter) | Keyboard / mouse |
|---|---|---|---|---|
| Move (tilt: walk, all the way: run) | Left stick | Left stick | Left stick | WASD, Shift runs |
| Aim (locks on) | L2 | L1 | L2 | Right mouse / K |
| Aim over the body (head, arms, legs) | Right stick | Right stick | Right stick | Mouse, or W/S |
| Switch target | Flick the right stick | Flick | Flick | Mouse wheel |
| Fire | R2 | R1 | R2 | Left mouse / J |
| Dodge | R1 | Circle/B | Circle/B | Space / C |
| Kick (counter, or a staggered one) and interact | Cross/A | Square/X kicks, Cross/A interacts | Square/X kicks, Cross/A interacts | E |
| Quick turn | Circle/B | R2 | L1 | Q |
| Reload | Square/X | Triangle/Y | R1 | R |
| Status screen | Triangle/Y | Share/View | Share/View | Tab |
| Flashlight | L1 | L2 | D-pad down | L |
| M92FS / Remington 870 / next | D-pad left / right / up | D-pad left / right / up | D-pad left / right, Triangle/Y | 1 / 2 / F |
| Pause and options | Options/Menu | Options/Menu | Options/Menu | Esc |

**Skill.** Dodge in the last moment of a lunge (a perfect dodge) and the Drowned bites air and
stumbles past, open to a kick, and your next shot does double damage; slow motion on a perfect
dodge is an option. Kick in the last moment of a lunge (a counter) and it's thrown back and
floored; kick too early and you eat the bite.

Movement is camera-relative, and a cut keeps the previous camera's directions until you change
direction, so a cut never reverses your movement. Classic tank controls are in the options
(or T). Rumble arrives with the switch to raylib's SDL3 backend. F3 shows a debug line.

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

1. Combat port: pistol and shotgun, kick, dodge, hit-stop; the three Drowned in the hall.
2. The cyclist (yellow rain jacket, chain lock) for a later room; water drips on the Drowned.
3. Rooms `voorkamer` and `kelder`, with doors and transitions.
4. UI, inventory, saves.
5. Audio: a C++ synth like Bumper Ball Maze's.
6. Remaining creatures in the stylized-grotesque style.
