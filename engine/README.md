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
../build/macos/damned_waters --view r870,30,14,1.6,0.05,0,14 shotgun.png           # the 870
../build/macos/damned_waters --fitgrips  # fit his hands to both guns as people hold them, write src/grips_fitted.inc, exit
../build/macos/damned_waters --fitpistol # fit the two-handed pistol aim (right arm, wrist, head), print it, exit
../build/macos/damned_waters --fit870    # fit the hold on the 870 (arms, wrists, back; aiming, the cheek on the stock), print it, exit
```

`--fitgrips` takes a few minutes. `DW_FIT_ONLY=PISTOL_LEFT` (or a comma list) refits just those
grips and keeps the rest, `DW_FIT_QUICK=1` makes a fast rough pass, and `DW_FIT_TRACE=1` reports
each stage of the search.

`--view` takes `who,orbit,elevation,distance,target_x,target_y,fov`. `who` is `survivor` or
`drowned0`..`drowned2` (the office worker, Sanne, Pieter). Add `@head`, `@chest`, `@pelvis`,
`@hand` or `@lhand` (the right or left wrist) to orbit that joint; the target is then an offset from it, and `@head` starts from the
face. Then any of `/pose=aim`, `/gun=1` (the 870 in hand), `/limp=1`, `/cut=3+8`, `/pitch=20` (aiming 20
degrees up; negative is down), `/grip=0..3` (one grip on its own, held out clear of the body: 0 the
pistol in the right hand, 1 the 870's wrist in the right, 2 its fore-end in the left, 3 the pistol
in both hands). With `/grip`, the camera orbits the gun instead: orbit 90 looks at its right side,
-90 its left, 0 down the muzzle.

`who` can also be a gun, `m92fs` or `r870`, lit like a catalogue photo so it can be held up
against reference photos: `/slide=1` works the slide or fore-end back, `/roll=20` turns the
picture, `/bg=dark` puts it on black, `/synthetic` gives the 870 a black stock, `/obj=name` writes
the meshes out as `name_fixed.obj` and `name_moving.obj` (full precision, for matching a camera
to a photo).

Dependencies are fetched on the first configure and pinned: raylib 5.5, nlohmann/json 3.11.3
and GoogleTest 1.14. SQLite comes from the macOS SDK, or from the amalgamation if the SDK copy
isn't found. The engine reads `../game/data/rooms` and `../game/assets/rooms` through
`DW_REPO_ROOT`, which CMake sets at compile time.

## How he holds the guns

The way a shooting instructor would check it, and fitted rather than posed by eye:

- **The pistol, two hands, thumbs forward.** The web of the right hand high under the tang, the
  middle finger tight under the trigger guard, ring and little fingers round the front strap,
  the pad of the trigger finger on the trigger and the rest of that finger off the frame, the
  thumb forward along the left of the frame. The left hand's heel fills the gap the right
  fingers leave on the left grip panel, its fingers wrap over the right ones (the forefinger
  pressed up under the guard), its thumb lies forward under the right thumb, the wrist cammed
  down. Arms out, the gun brought up to the eye rather than the head down to the gun.
- **The 870.** The right hand shakes hands with the stock's wrist (thumb round it, not along
  the top), the butt in the shoulder pocket, the cheek down on the comb. The left hand holds the
  fore-end across the palm on a slant, fingers round its right side, thumb along its left, and
  goes back and forth with it when he racks the pump.

**The grips** (`--fitgrips`, `src/grip_fit.cpp`, written to `src/grips_fitted.inc`). Think of
fitting a glove in the dark. Each gun becomes a distance field (for any point near it: how far
the surface is, negative inside the steel or wood), so the fitter can feel the gun everywhere at
once. The hand is his own skin, bent by its 15 finger joints the way the engine bends it. A
search moves the gun about in the hand while the fingers close round it by themselves, the way
robot hands grasp (each joint closes until its segment touches, then the next one carries on
curling, so the finger wraps what it meets). It keeps whatever puts the instructor's check
points (the web, the trigger pad, the knuckle line, the thumb) where the technique says, with no
skin sinking more than a millimetre or two into the gun. The pistol's support hand is fitted
second, onto the first: the right hand, as fitted, is drawn into the pistol's field so the left
fingers close over it. Change a goal and run the tool again rather than editing the numbers.

**The left hand stays on the gun** (`Character::support_hand`, `src/two_bone.cpp`). The right
hand carries the gun, and the left arm is solved every frame so its hand lands exactly where its
grip says, whatever the right hand has done: aimed up or down, bucking from a shot, or (the
870) with the fore-end racked back under it. An arm is two bones, so it's solved outright, no
searching: the elbow bends until the arm is as long as the gap to the grip, and of the ways the
arm can then reach it, it takes the one with the elbow where the pose had it (down and out). It
costs a few dozen multiplications a frame. The pose tables (`--fitpistol`, `--fit870`) give the
rest: the right arm and wrist so the bore lies along the aim, the head so the right eye sits on
the sight line or the cheek on the comb, each wrist bent no further than a wrist goes.

A grip has to suit the arm as well as the gun. A hand placed however suits the fingers can leave
the wrist bent past what wrists do, so each pistol grip is fitted against the way the forearm
comes in (a wrist tips about 30 degrees toward the little finger, 15 toward the thumb). The 870's
right hand sits 30 degrees down across the stock's wrist: square across it the fingers wrap best
but the wrist ends up by his face once the butt is in the shoulder. A forearm turns the hand by
twisting along its length; this rig has no joint for that, so the wrist turns the hand and the
forearm's skin takes half the twist, the way a sleeve wrings along an arm rather than at the cuff.

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
| `include/dw/character.hpp`, `src/character.cpp` | Joint forward kinematics, the cast, the pose tables, and the left hand put on the gun each frame. |
| `src/grip_fit.cpp`, `src/grips_fitted.inc` | The grip fitter (`--fitgrips`) and what it wrote: where each gun sits in each hand and how the fingers wrap it. |
| `include/dw/two_bone.hpp`, `src/two_bone.cpp` | The two-bone arm solve that keeps the left hand on the gun. Pure maths, unit-tested. |
| `src/character_combat.cpp` | Hit capsules, wounds, severing, the guns in hand, and the aim fitters (`--fitpistol`, `--fit870`). |
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
