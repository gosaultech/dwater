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

**Not ported yet:** the other rooms (and walking between them through doors), and saves.

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
../build/macos/damned_waters --capture /tmp/dw   # stage the capture setups (the fight, the reloads, the status screen) and save screenshots
../build/macos/damned_waters --flashlight --capture /tmp/dw   # the same with the flashlight on
../build/macos/damned_waters --sheet /tmp/dw     # studio turnaround of every character
../build/macos/damned_waters --sheet /tmp/dw --only pieter,survivor               # just those
../build/macos/damned_waters --view drowned1@head,0,5,0.5,0,-0.05,30 face.png     # one close-up
../build/macos/damned_waters --view m92fs,0,0,2.0,0,0,8.3 pistol.png              # a gun, catalogue-lit
../build/macos/damned_waters --view r870,30,14,1.6,0.05,0,14 shotgun.png           # the 870
../build/macos/damned_waters --fitgrips  # fit his hands to both guns as people hold them, write src/grips_fitted.inc, exit
../build/macos/damned_waters --fitpistol # fit the pistol in both hands (the aim: right arm, wrist, head; the low ready, standing and running: the arms), print it, exit
../build/macos/damned_waters --fit870    # fit the hold on the 870 (arms, wrists, back; aiming, the cheek on the stock; the low ready; the reload), print it, exit
```

`--fitgrips` takes a few minutes. `DW_FIT_ONLY=PISTOL_LEFT` (or a comma list: `PISTOL_RIGHT`,
`PISTOL_LEFT`, `SHOTGUN_RIGHT`, `SHOTGUN_LEFT`, `MAG_LEFT`, `SHELL_LEFT`, `PISTOL_RIGHT_INDEXED`,
`SHOTGUN_RIGHT_INDEXED`) refits just those grips and keeps the rest, `DW_FIT_QUICK=1` makes a fast
rough pass, and `DW_FIT_TRACE=1` reports each stage of the search. `--fitpistol` takes
`DW_FIT_ONLY=aim`, `low` or `run` (a few seconds each), `--fit870` `aim`, `low` or `reload`.

`--view` takes `who,orbit,elevation,distance,target_x,target_y,fov`. `who` is `survivor` or
`drowned0`..`drowned2` (the office worker, Sanne, Pieter). Add `@head`, `@chest`, `@pelvis`,
`@hand` or `@lhand` (the right or left wrist) to orbit that joint; the target is then an offset from it, and `@head` starts from the
face. Then any of `/pose=aim`, `/gun=1` (the 870 in hand), `/limp=1`, `/cut=3+8`, `/pitch=20` (aiming 20
degrees up; negative is down), `/grip=0..5` (one grip on its own, held out clear of the body: 0 the
pistol in the right hand, 1 the 870's wrist in the right, 2 its fore-end in the left, 3 the pistol
in both hands, 4 a magazine in the left hand, 5 an 870 shell). With `/grip`, the camera orbits the
gun (or what's in the hand) instead: orbit 90 looks at its right side, -90 its left, 0 down the
muzzle. `/reload=0.4` shows him that far through a reload (the 870's: one shell; add `/rack` for
the first shell into an empty gun, `/port` for a shell after the first; `/live` plays it there in
real time from the aim, as the game would).

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
  aiming, the pad of the trigger finger on the trigger and the rest of that finger off the frame
  (otherwise it lies along the frame: below), the thumb forward along the left of the frame. The left hand's heel fills the gap the right
  fingers leave on the left grip panel, its fingers wrap over the right ones (the forefinger
  pressed up under the guard), its thumb lies forward under the right thumb, the wrist cammed
  down. The modern isosceles: both arms out but bent about 40 degrees, never locked, the elbows
  hanging down under the gun; the gun brought up to the eye rather than the head down to it.
- **The 870.** The right hand shakes hands with the stock's wrist (thumb round it, not along
  the top), the butt in the shoulder pocket, the cheek down on the comb, and the elbows down:
  the right one dropped under the stock rather than winged out to make a pocket. The left hand holds the
  fore-end across the palm on a slant, fingers round its right side, thumb along its left, and
  goes back and forth with it when he racks the pump.

**Ready for action, until he aims** (the pose tables in `Character::targets`,
`include/dw/ready.hpp`). Holding a gun without aiming it (standing, walking, running, knocked back)
he carries it at the ready: low in front of him in both hands, gripped exactly as he shoots with
it, the muzzle at the floor a stride or two ahead, so bringing it up is one short move. Like a
goalkeeper waiting with his knees bent and his hands up: everything is already where it needs to
be.

- **The M92FS at the low ready.** The arms lowered from the aim at the shoulders, bent about as
  much (45 degrees) with the elbows down by his sides, the wrists no more bent than aiming; the
  gun on his middle line between his belly and the bottom of his chest, a forearm out from his
  coat; the muzzle 42 degrees down, at the floor 1.9 m ahead. Running, the same ready fitted on
  his running body as it leans into the stride: 4 cm nearer him, the muzzle 45 degrees down at
  1.6 m. (A compressed ready, the gun pulled in to the chest, would bend this rig's one-piece
  palm past 55 degrees at the wrist.)
- **The 870 at the low ready.** Both hands on it as to shoot, turned the way he aims, the left
  shoulder forward (his left arm, straight, reaches the fore-end that way); the butt dropped from
  the shoulder pocket to just under it, on his chest by the armpit, the muzzle 35 degrees down.
  Raising it is the butt back up into the pocket and the muzzle up. (Kept in the pocket, the hand
  on the stock's wrist would have to turn round it, further than a wrist goes.)
- **Trigger discipline.** Off the trigger, the forefinger lies straight along the side of the
  frame (the 870's receiver), its pad above the trigger guard, never inside it; the rest of the
  hand doesn't move on the gun (`PISTOL_RIGHT_INDEXED`, `SHOTGUN_RIGHT_INDEXED`: the shooting grips
  refitted with the forefinger alone moving). Aiming, the gun comes up as the arms ease to the aim
  (a quarter of a second, most of the way), and only once it's 80 percent up does the finger go
  to the trigger (0.12 s); lowering, it comes off first (0.08 s), and it stays off through a
  reload, a dodge or a kick. Like holding a pen just above the paper until you know what you're
  going to write. (A shot fired before the finger gets there snaps it on: he pulled the trigger.)
- Carrying it, he keeps both hands on it however badly hurt he is: he no longer holds his ribs
  with a free hand (he has none); the limp and the hunch show it.

Going to the ready, and up from it to the aim, his shoulders and wrists turn the short way, as his
fingers do (`slerp_angles`, written back the way the pose table writes them, `angles_near`): eased
angle by angle, an arm written down one way in one pose and the other way in the next would swing
the long way round, through his chest, on the way up. The ready is fitted like the aim:
`fit_pistol` takes a goal (`PistolFit`: a box for the grip in front of him, where the bore's line
meets the floor, both wrists as a physio measures them, nothing through his body), and the 870's
low ready is fitted with the same care for the wrists and the left hand held on the wood.

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

**The left hand stays on the gun** (`Character::hands`, `Character::arm_to`, `src/two_bone.cpp`). The right
hand carries the gun, and the left arm is solved every frame so its hand lands exactly where its
grip says, whatever the right hand has done: aimed up or down, bucking from a shot, or (the
870) with the fore-end racked back under it. An arm is two bones, so it's solved outright, no
searching: the elbow bends until the arm is as long as the gap to the grip, and of the ways the
arm can then reach it, it takes the one with the elbow where the pose had it (down and out). It
costs a few dozen multiplications a frame. The pose tables (`--fitpistol`, `--fit870`) give the
rest: the right arm and wrist so the bore lies along the aim, the head so the right eye sits on
the sight line or the cheek on the comb, each wrist bent no further than a wrist goes.

A grip has to suit the arm as well as the gun. A hand placed however suits the fingers can leave
the wrist bent past what wrists do, so each grip is fitted against the way the forearm comes in,
elbows down (a wrist tips about 30 degrees toward the little finger, 15 toward the thumb). The
870's right hand sits level across the stock's wrist so the elbow can hang down; its half pistol
grip is raked about 45 degrees and this rig's palm is one rigid piece, so the wrist cocks hard
toward the little finger, as holding a sporting stock elbows-down does. A forearm turns the hand
by twisting along its length; this rig has no joint for that, so the wrist turns the hand and the
forearm's skin takes half the twist, the way a sleeve wrings along an arm rather than at the cuff.

## How he reloads

The hands do the work, timed to the gun's rules (`include/dw/reload.hpp`, `src/reload.cpp`):

- **The M92FS (1.4 s).** He brings the gun in close in front of his chest, about 43 cm out,
  its top canted over to his right so the magazine well faces down toward the incoming left hand
  (`Character::ReloadShape`, fitted by `--fitreload`). As the right thumb drops the empty
  magazine (it falls, clatters and lies on the floor), the left hand is already on its way to his
  coat pocket. It comes out with the fresh magazine held the way a fast reload is taught: the
  base plate in the hand, the forefinger straight up the front with its tip under the top round
  (it steers the magazine into the grip), the other fingers wrapped loosely round it. Turned
  upright on the way, it goes up into the grip; the fingers open off it and the heel of the hand
  slaps it home. Then the gun is pushed back out to the aim and the left hand rejoins it there;
  if the slide was locked open, the left thumb drops the slide stop on the way.
- **The 870 (0.5 s a shell).** Each shell comes out of the same pocket held in the fingertips,
  the brass against the thumb, goes up nose first through the loading port, levels under the
  tube and is thumbed home past the shell latch. He loads with the gun brought down to his hip,
  the stock against it and the muzzle angled up across his body, so the port is in front of his
  belly where the left hand reaches it without crossing his chest. Into an empty gun, the first
  shell is followed by the hand sliding forward onto the fore-end and racking it right there (he
  doesn't turn away to do it). He can stop to fire, or walk off, between shells.

The reload is written down like dance notation: a list of steps, each a place for the left hand
(on the gun, in the pocket, or holding the load somewhere along its way in) and the moment it
gets there. Between steps the hand travels on a smooth curve, stopping only where a step says (to
grab, to slap the magazine home); the arm is bent there by the same two-bone solve that keeps the
hand on the gun. The magazine and the shell in the hand are held by grips fitted like the guns'
(`MAG_LEFT`, `SHELL_LEFT`), so the fingers close round them rather than through them. The sounds
are timed to the steps: the release's click, the slap home, the slide slamming forward, the
magazine hitting the floor, each shell's click, the pump.

### Nothing goes through anything

A hand that goes through a coat, or a wrist bent like a broken doll's, is the first thing a player
notices. Three things keep the arms honest.

- **The torso as a stack of oval plates** (`include/dw/clearance.hpp`). At load, the body's own
  vertices are sliced every 2 cm up the chest and the pelvis. Each slice keeps how wide, how far
  forward and how far back it is, ignoring the few strays (a seam under the arm) that would make
  it look fatter than it is. Asking "is this elbow inside him?" then costs a few multiplies, like
  holding a ruler up to a tailor's dummy.
- **The elbow finds its own way** (`Character::arm_to`). Once the IK has put the hand where it
  must be, the elbow is still free to swing round the shoulder-to-hand line, the way you can lift
  or drop your elbow with your hand flat on a table. Every frame it tries that circle every 10
  degrees and takes the cheapest: out of the body first, then (in a reload, where no fitted pose
  says where the elbow goes) the wrist least bent and twisted, then the elbow kept down, never
  winged up by the shoulder. The choice is eased, so the elbow glides rather than snaps.
- **Wrists are measured the way a physio would** (`swing_twist`, `two_bone.hpp`). A wrist's turn
  is split into twist (the forearm's bones rolling round each other, fine up to about 75
  degrees) and swing (the hand tipping off the forearm's line, comfortable to about 40). Finger
  poses blend as true turns (`slerp_angles`), not angle by angle, so a finger never swings out
  sideways halfway between two grips. Flat-handed, the fingers close together (`curl`'s
  `together`), and the end of each sleeve follows the wrist a little, so a bent wrist's skin
  never pokes through the cuff.

Two tools check it and tune it:

```bash
../build/macos/damned_waters --clearance    # play each way he carries a gun (standing, walking, running, raising
                                            # it and lowering it) and every reload through, frame by frame: how deep
                                            # the arms, hands and gun go into the body (and each other), both wrists,
                                            # and where the trigger finger is (DW_CLEAR_ONLY=stance or reload: half)
../build/macos/damned_waters --fitreload    # search where the pistol is brought in to reload (least wrist strain,
                                            # nothing through anything); paste the result into ReloadShape
DW_CLASH=1 ../build/macos/damned_waters --view "survivor@chest/gun=0/live/reload=0.6,-30,10,1.3,0,-0.1,38" out.png
                                            # a still with every point that's gone in marked red
```

`/live` in a `--view` plays the reload up to that moment as the game does (from the aim, in real
time) instead of posing him there and letting him settle. `--fit870` also scores the loading pose
by where the reload's IK really puts the left hand, and keeps the stock out of the coat;
`DW_FIT_ONLY=aim`, `low` or `reload` fits just that one.

## The status screen

Tab (or the status button in your layout) opens the case, RE style, and time stands still. No
HUD otherwise: this is where the ammo and his condition live. Like opening a field kit on a
table: everything laid out, nothing moving until you close it.

- **ITEMS.** His figure as he stands right now (a limp shows), a heart monitor's trace and one
  word: FINE in green, CAUTION in amber, DANGER in red. The trace speeds up as he weakens. No
  numbers: you read him the way the classics make you. Beside it, the case's eight slots (each
  item's 3D model as its icon, the gun in hand marked E, rounds loaded and stack counts in the
  corner), what's in hand and its spare rounds, and the selected thing turning in 3D, with its
  description. Cross opens its actions: Equip, Use (med kits; refused at full health so none is
  wasted), Combine (spare rounds into their gun loads it on the spot), Examine (big, turned with
  the right stick or the mouse) and Discard (guns and keys stay; anything dropped lies on the floor
  and can be picked up again). Square combines and Triangle examines straight away.
- **FILES.** Every note he's read, to read again on the page.
- **MAP.** The house as far as he knows it, worked out from the room files' doors (rooms meet
  where their doorways do, so nobody draws the map): rooms he's been in, red while something is
  still lying in one, blue once it's cleared; rooms seen through a door as dashed outlines; locked
  doors in red; stairs; where he stands and which way he faces. Up and down change floor.
- **Finding something.** It glints where it lies. Cross picks it up: it turns in the light,
  "Take it?". If the case is full he can leave it, or open the case and drop something to make
  room.
- **Looking at things.** Cross by a door, the clock or the stairs says what he sees, typed out
  at the bottom of the screen, time stopped until it's read.

The buttons drawn are the pad in your hand: PlayStation shapes, Xbox letters, or key caps.
Fonts are Cinzel and EB Garamond, under the SIL Open Font License (`engine/assets/fonts`).

## The death screen

When he goes down, the picture drains into a deep red-black and blood seeps in from the edges;
YOU DIED rises out of the dark in IM FELL English (a 17th-century typeface, SIL OFL), blood red,
settling as it comes, and drops gather at the letters' feet and run. Then the choice: Try again
or Quit. Like a curtain coming down in a set order: lights, words, then the house lights.
The timing lives in `include/dw/death.hpp` (pure, unit-tested); `Game::draw_death` draws it.
`--capture` has it twice: `you_died_falling` (the words coming up) and `you_died` (all of it).

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
| In the case: select / back | Cross/A / Circle/B | Cross/A / Circle/B | Cross/A / Circle/B | Enter / Esc |
| In the case: combine / examine | Square/X / Triangle/Y | Square/X / Triangle/Y | Square/X / Triangle/Y | C / X |
| In the case: change tab / turn the item | L1, R1 / right stick | L1, R1 / right stick | L1, R1 / right stick | Q, R / mouse drag |

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
| `include/dw/character.hpp`, `src/character.cpp` | Joint forward kinematics, the cast, the pose tables, and the hands put on the gun (and through a reload) each frame. |
| `src/grip_fit.cpp`, `src/grips_fitted.inc` | The grip fitter (`--fitgrips`) and what it wrote: where each gun (and the magazine and shell the left hand loads) sits in each hand and how the fingers wrap it. |
| `include/dw/two_bone.hpp`, `src/two_bone.cpp` | The two-bone arm solve that keeps the left hand on the gun, the aim fitters' arm measures (elbow hanging down, its bend), a wrist's swing and twist, and blending joint turns the short way. Pure maths, unit-tested. |
| `include/dw/clearance.hpp`, `src/clearance.cpp` | How far one surface sinks into another, and the torso as stacked oval slices for the elbows to keep out of. Pure, unit-tested. |
| `src/character_clearance.cpp` | The clearance check on the posed body (`--clearance`: the carries and the reloads) and the pistol's reload-position fitter (`--fitreload`). |
| `include/dw/ready.hpp` | Trigger discipline: how far up the gun is, and when the trigger finger may go on and must come off. Pure, unit-tested. |
| `include/dw/reload.hpp`, `src/reload.cpp` | The reloads' steps: where the left hand goes and what it holds, and when the magazine drops, goes home and the slide runs forward. Pure, unit-tested. |
| `include/dw/status.hpp`, `src/status.cpp` | The status screen as rules: condition, what each item can do, loading from the case, what the world remembers, and the screen's state machine (browse, act, combine, discard, read, pick up, make room). Pure, unit-tested. |
| `include/dw/world_map.hpp`, `src/world_map.cpp` | The map, laid out from the room files' doors and storeys. Pure, unit-tested. |
| `src/status_view.cpp` | The status screen on screen: fonts, the 3D previews and icons, his figure, the tabs, the button glyphs. |
| `include/dw/death.hpp` | The death screen's timing: the fade, the words, the drips, the choice. Pure, unit-tested. |
| `src/game_world.cpp` | Pickups, notes, things to look at and doors in a room; carrying out what the screen asks for. |
| `src/cast_items.cpp` | The case's items as 3D models (the guns are `cast_guns.cpp`'s). |
| `src/effects.cpp` | Blood, brass and spent shells, limbs that come away, the empty magazines he drops, the muzzle flash. |
| `src/character_combat.cpp` | Hit capsules, wounds, severing, the guns in hand, and the aim and ready fitters (`--fitpistol`, `--fit870`). |
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

Done in the C++ engine: combat (both guns, kick, dodge, counters, gore), the reloads, the
status screen (items, files, map, pickups), the death screen. Still to come, in order:

1. **More of the house, and the city.** The canal house's other rooms (`voorkamer`, `kelder`
   and new ones), with doors and room-to-room transitions; then the streets along the canals,
   Amsterdam Centraal, and the metro north under the IJ to Station Noord. All pre-rendered
   backgrounds from RoomSpecs (`docs/handoff/areas_session_prompt.md` is the brief).
2. Saves (the typewriter), a title screen.
3. **#27 (polish, deferred): a palm arch joint**, so the 870's right wrist cocks less (about 49
   degrees toward the little finger now). A rig change: rebuild `survivor.dwc`, then refit the
   grips (`--fitgrips`) and the poses (`--fitpistol`, `--fit870`).
4. Reload tuning from play-testing (timing, the 870's hip load).
5. Rumble and the SDL3 backend; the cyclist and the other creatures.
