<!-- damned_waters/docs/handoff/areas_session_prompt.md -->
<!-- Purpose: the brief that starts the next session (new areas as pre-rendered backgrounds). Paste it as the first message. -->

Continue Damned Waters (repo gosaultech/dwater). Start from branch `claude/inspiring-turing-gl0kys`
(last commit: the death screen), and develop on the branch this session is given. This session
EXPANDS THE AREAS: more rooms of the canal house, then the city outside, all as pre-rendered
backgrounds. I'm the game director: show me checkpoints as rendered images, ask instead of
assuming, keep replies to concise bullet points. I'll attach reference photos of Amsterdam canal
houses, streets and Amsterdam Centraal (the metro comes later).

## Rules
- Push only to this session's branch. No PR unless I ask.
- No model identifiers in code, comments or commits. End commit messages with the
  Co-Authored-By line and this session's Claude-Session link.
- Every file starts with a path/purpose comment. Write tests for new logic (GoogleTest in
  engine/tests; Python unittest in tools/). Keep latency low. Document in engine/README.md with
  short ELI5 analogies. README requests: the whole file inside one markdown code block.

## Where the project is
- Two codebases: `game/` (the Godot prototype, the original demo) and `engine/` (the C++17 /
  raylib 5.5 port, where all current work happens). Read `engine/README.md` first.
- Playable in the engine: one room, `gang` (the Entrance Hall): fixed camera shots over
  pre-rendered plates with painted depth, the survivor, the Drowned, both guns with full
  reloads, kick/dodge/counters, gore, the status screen (Items / Files / Map, pickups, notes,
  examine text), the death screen. No HUD (RE style). Controller-first (Type A/B/C layouts).
- Room-to-room travel does NOT exist yet: doors say "Only this hall is built so far"
  (`engine/src/game_world.cpp`, `Game::interact`). `Game::init` loads one room.

## How backgrounds work (the pipeline to extend)
- One RoomSpec JSON per room, `game/data/rooms/<id>.json`, is the single source of truth: bounds,
  walls with openings, props, lights, camera `shots` (each with a trigger `zone`), `spawns`,
  `interactables` (pickup / note / examine / door with target_room + target_spawn + lock / save /
  end), `enemies`, and `"storey"` (0 ground floor, -1 cellar; used by the map).
- Blender builds each room procedurally from its spec (`tools/blender/builders.py`, render in
  `tools/blender/render_rooms.py`) and renders, per shot, a colour plate and a 16-bit depth plate
  (`tools/pipeline/build_backgrounds.py --quality final --gpu`; `depth_pack.py` packs them into
  `game/assets/rooms/<id>/<shot>_color.png` / `_depth.png`). The engine draws the plate and writes
  its depth so 3D characters hide behind painted furniture (`engine/src/game.cpp`, plate shader).
- Existing specs: `gang` (Entrance Hall), `voorkamer` (Front Parlor: Marit's note, the cellar key,
  the typewriter, a shotgun), `kelder` (Flooded Cellar, storey -1, the water gate and the boss).
  All three have rendered plates (preview quality). The engine's map (Tab, MAP) already lays rooms
  out from their doors (`engine/include/dw/world_map.hpp`), so new rooms join it by their doors.
- Blender is NOT installed in the cloud container: install it (apt, or blender.org if the network
  allows) and render at preview quality on the CPU here; final quality (256 samples) runs on my
  M4 Pro with the command above.

## What I want this session
1. Room transitions in the engine first: walk through a door into the next room (load its
   RoomSpec and plates, arrive at target_spawn, a short RE-style door beat), with the world
   state (pickups taken, notes, rooms visited, doors unlocked; `status::WorldState`, keyed
   "room/id") carried across. Make `voorkamer` and `kelder` playable.
2. Then extend the canal house (an extension of the current area): propose the extra rooms
   (e.g. back room, kitchen, stairwell, upstairs, attic) from my reference photos, write their
   RoomSpecs, build and render them, show me plates before wiring them in.
3. Then the exterior route: the canal streets (Herengracht / Prinsengracht), to Amsterdam
   Centraal; later the metro (Noord-Zuidlijn) to Station Noord. The survivor goes on foot from
   Centraal to Noord. Same pre-rendered approach; propose how photos guide the Blender sets
   (modelling to match, texture reference, camera framing) and ask before choosing.
4. Before building each area: a short plan, then a render checkpoint for my review.

## Open items to keep in mind (don't do unless I ask)
- #27 (deferred): a palm arch joint so the 870's right wrist cocks less; rig change, rebuild
  `survivor.dwc`, refit grips (`--fitgrips`) and poses (`--fitpistol`, `--fit870`).
- I'm play-testing the reloads; notes may come (timing; the 870's hip load pose).
- Saves (the typewriter) and a title screen are not built.

## Build, test, render (the container)
- Packages: `apt-get install -y libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev
  libgl1-mesa-dev libsqlite3-dev xvfb ninja-build libgtest-dev`; Python: `pip install numpy
  scipy pillow` (audio synth, sheets). GitHub tarball downloads are blocked; the system GTest works.
- Build: `cmake -S engine -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release`, then `ninja`.
  Tests: `./dw_tests`.
- Render under xvfb: `xvfb-run -a -s "-screen 0 1280x720x24" ./damned_waters --capture <dir>`
  (27 staged screenshots), or `--view "<spec>" out.png` for studio stills (see the README).
- Fonts are vendored (`engine/assets/fonts`, SIL OFL); Google Fonts' static files are reachable.
