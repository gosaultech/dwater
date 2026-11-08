<!-- damned_waters/docs/handoff/session_memory.md -->
<!-- Purpose: the memory between sessions: where the work stands, how it is made, what was learned, what is open. Update it at the end of each session. -->

# Where Damned Waters stands (last updated 2026-11-08)

## In one paragraph
The route runs end to end on pre-rendered backgrounds, from the canal house through central
Amsterdam to Station Noord, where a "to be continued" card returns to a new title screen. The
session of 2026-11-08 answered the user's playtest ("controls reverse at room transitions"; "the
camera shots outside and in the big halls are way too wide; think RE3's city"):
- **Controls:** a held stick never turns him round at a cut (`HeldFrame`, `controls.hpp`);
  `--walkthrough` proves it on every doorway and staircase (255 tries, none turn back).
- **The wide rooms are cordoned** (user's choice, over "keep open with ~430 shots"): crowd-barrier
  lanes through the Dam, Stationsplein, Rembrandtplein, Muntplein, Thorbeckeplein, Rokin and
  Damrak (`tools/citygen/barricades.py`).
- **Their cameras are planned by rule** (`tools/citygen/cameras.py`): 254 shots in 27 rooms where
  there were about 95; he stands about a fifth of the picture high (5 to 10 percent before).
- **Plates stream by shot** (`dw/streaming.hpp`), not by room.
- **Rain on the whole shot** (`dw/rain.hpp`, `RAIN_FS`, `SPLASH_FS`): eight depth-tested sheets from
  1.2 to 34 m in front of the camera, not a box following him; brighter where it's lit from behind.
- **Motion capture** (`tools/anim/bake_mocap.py`, `dw/mocap.hpp`, `docs/motion_credits.md`): his
  sneak (Swat), walk and run (Rushed) and idle (Neutral), and the Drowned's three shambles
  (DragRightLeg, Drunk, BentForward), from the 100STYLE dataset (CC BY 4.0). The dataset isn't in the
  repo: re-bake from Zenodo record 8127870 (1.5 GB). Next for it: turning on the spot, starts and
  stops, a limp from LimpLeft/LimpRight, foot IK on slopes and steps.

Earlier sessions: the city (areas 2 to 8), the shops' interior pass, the colour pass (Amsterdam's own
colours on a spooky night), modelled tulips, a basic title screen. Everything up to PR #5 is merged
into `claude/inspiring-turing-gl0kys`. All backgrounds are preview quality at 1280x720 (Cycles on
the container's CPU).

## Merged PRs (gosaultech/dwater, base `claude/inspiring-turing-gl0kys`)
1. #1: the city route from the canal house to Damrak, the realism pass, rain, the ending.
2. #2: the route to its end (the Stationsplein, Centraal's hall, metro line 52, Station Noord),
   Centraal rebuilt, roof fixes.
3. #3: the interior pass: photographed stock (CC BY, credited) and denser fixtures in twelve shops.
4. #4: Amsterdam's colours on a spooky night, modelled tulips, the title screen; 33 rooms re-rendered.

## The game now
- **Rooms by storey** (`game/data/rooms/*.json`; the storey is in each file):
  - Canal house: -1 kelder, souterrain, waterpoort; 0 gang, voorkamer, bibliotheek, herengracht
    (the street outside); 2 badkamer (built, waiting for its stairs).
  - 10: thorbeckeplein, rembrandtplein.
  - 11: reguliersbreestraat, muntplein, bloemenmarkt, plus apotheek, bioscoop, bloemenkraam.
  - 12: rokin_zuid, rokin_noord, plus hotel_lobby, politiepost, metro_rokin.
  - 13: kalverstraat, kalverstraat_noord, kalversteeg, plus drogist, juwelier, wapenhandel.
  - 14: dam, plus nieuwe_kerk, warenhuis, beveiliging.
  - 15: damrak_zuid, damrak_noord, rondvaartboot, plus beurs_zaal, hotel_bar, magazijn,
    souvenirwinkel, wisselkantoor.
  - 16: stationsplein, centraal_hal. 17: metro_centraal. 18: station_noord (the "end"
    interactable).
- **Engine features:**
  - Combat: both guns, reloads, kick, dodge, counters, gore.
  - Screens: the status screen (items, files, map), the death screen, the end card, the title
    screen.
  - Movement and options: seamless doorways on a storey; a short dark beat between storeys; the
    pause menu with options saved in SQLite next to the telemetry (`damned_waters.db`).
- **Title screen** (basic, by the user's choice for now):
  - Black screen; "DAMNED WATERS" in IM FELL English, then New Game / Quit, with the
    `title_drone` loop underneath.
  - New Game fades to black and runs `reset_fight()`. The end card returns to the title on a press.
  - `--room <id>` skips the title.
  - Code: `include/dw/title.hpp` (pure, tested in `tests/test_title.cpp`) and
    `Game::open_title/update_title/draw_title`. Capture stage 96 is `title_screen`.

## How the city is made
- **Generators** (`tools/citygen/area3.py` .. `area8.py`) write the RoomSpecs.
- **`build_city.py`** runs, in order:
  1. the generators, in ORDER;
  2. `aftermath13` (the evacuation's leavings, applied once);
  3. the KEPT rooms (thorbeckeplein, rembrandtplein, herengracht), which carry hand edits and are
     dressed in place: sky set to `common.SKY`, the clinker road re-tinted to `common.BRICKS`;
  4. the interior pass, `tools/citygen/interiors.py`. It is idempotent: what it adds is marked
     `"interior"` and replaced on every run. It also sets each shop's wall paint from `PAINT`.
  5. the cordons (`barricades.py`: LANES per room, barrier lines generated where a lane's edge
     crosses open floor, MOVES puts Drowned/items/spawns into lanes; idempotent, marked
     `"barricade"`), then the camera pass (`cameras.py`: replaces "shots" of every room in its
     ROOMS; `python3 tools/citygen/cameras.py report` prints each shot's numbers). Both tested.
- `area2.py` is reference only: its rooms carry hand edits.
- **Doors between storeys:** a "door" interactable within 1.6 m of the doorway (a test enforces
  this), or `"board": true` for interact-only beats such as the train doors. Seamless doorways on
  the same storey are paired 0.3 m apart.
- **Blender** (`tools/blender/`) builds each room from its spec:
  - `builders.py`, plus kits: `street.py` (facades, lamps, `FRONTS` paint), `landmarks.py`,
    `city.py` (trams), `station.py`, `shops.py`, `photos.py` (photo cards behind shelf edges),
    `flowers.py` (modelled tulips), `surfaces.py` (Poly Haven PBR scans).
  - Neighbouring streets within 40 m are built for outdoor rooms. A prop's `"encloses"` drops a
    landmark when the room inside it renders.
- **The look** (keep to it): Amsterdam's own colours on a spooky night.
  - `surfaces.GRADE` corrects each scan's hue and saturation (they were all orange or tan):
    red-brown brick, a dark purple-brown clinker road, grey pavements and cobbles. Any material
    can also set `"hue"` and `"sat"`.
  - `common.SKY` is cool moonlight; street lamps are warm-white; exit signs glow green.
  - Each shop's walls are painted on a neutral plaster (`common.plaster`, `interiors.PAINT`).
  - The engine's post grade lives in `engine/src/shaders.cpp` (`POST_FS`): saturation 1.05, blue
    shadows, a gentle S-curve, a vignette. Judge renders through it.
- **Photos:** `tools/assets/photos.json` lists 11 CC BY photos, cropped onto cards.
  `python3 tools/assets/photos.py fetch` downloads them; `credits` rewrites
  `docs/photo_credits.md`. Flowers are modelled, never photographed (the user rejected flat flower
  photos).

## Working in the cloud container
- **Setup in a fresh container:**
  - `apt-get install -y libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev libgl1-mesa-dev
    libsqlite3-dev xvfb ninja-build libgtest-dev`, and `pip install numpy scipy pillow`.
  - Blender 4.5 LTS:
    `mkdir -p /opt/blender && curl -L -o /tmp/b.tar.xz https://download.blender.org/release/Blender4.5/blender-4.5.9-linux-x64.tar.xz && tar xf /tmp/b.tar.xz -C /opt/blender`.
  - Texture and model caches (outside git): `python3 tools/assets/polyhaven.py fetch` and
    `python3 tools/assets/photos.py fetch`.
- **Memory and CPU:** the container has 15 GB and 4 cores, and a street peaks at about 6 GB.
  Run one Blender at a time: two at once ran out of memory and one was killed.
- **The render queue** (keep it in the scratchpad):
  - Rooms are popped off `queue.txt`, one at a time, each waiting for 9 GB free.
  - Start it detached with `setsid nohup ./qlane.sh 999999 > lane.log 2>&1 < /dev/null &`, so the
    tool's two-hour limit can't cut it off.
  - Wait on it with one background `until grep -q LANEDONE lane.log; do sleep 30; done`, and
    re-arm that waiter if it times out.
  - A container restart kills the render in flight. Find the room whose log lacks "Blender quit"
    and put it back at the front of the queue.
  - The script:
    ```bash
    #!/bin/bash
    S=/tmp/claude-0/<project>/<session>/scratchpad   # this session's scratchpad
    Q=$S/queue.txt
    cd /home/user/dwater
    while true; do
      r=$(flock $Q.lock sh -c "head -1 $Q; sed -i 1d $Q"); [ -z "$r" ] && break
      while [ $(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo) -lt 9 ]; do sleep 15; done
      /opt/blender/blender-4.5.9-linux-x64/blender -b --factory-startup -P tools/blender/render_rooms.py -- \
        --rooms $r --quality preview --res 1280x720 --out pipeline_out/renders > $S/full_$r.log 2>&1
      echo "$r $? $(date +%T)"
    done
    echo LANEDONE
    ```
- **Timings:** shops take 2 to 5 minutes each, streets 6 to 17. A full city re-render (33 rooms)
  took about 4 hours.
- **Packing:** pack only the rooms that were re-rendered. Symlink them into a directory and run
  `depth_pack.py --src` on it. Unchanged depth plates come out byte-identical.
- **Before committing:** run the four Python suites, `dw_tests`, and a full `--capture`. Then
  commit the plates and push.

## Gotchas learned
- `fan_prism` sweeps along its frame's W axis from 0 to depth. A negative depth put roofs beside
  their buildings.
- Light linking: a ground surface lit only by its own room's lights rendered black inside the hall.
- `| tail` hides a failing exit code; use `set -o pipefail`. One commit went in with a failing
  pipeline test this way.
- A generator with its own hard-coded output path ignored `DW_ROOMS` (now fixed in area2 and area3).
- The engine lights characters with only the first 8 room lights.
- After a merge, the local `origin/<default>` ref can be stale. A post-merge fetch was once denied
  by the permission classifier; check PR state with the GitHub tools instead, and don't work
  around a denial.
- `merge_pull_request` wants the full 40-character head SHA.
- **Cameras, learned from the pilot renders:** a camera planned on floor maths alone stood under
  stall canopies, over a van's floodlight and against shop awnings. The planner now keeps clear of
  everything standing (solid or not, at its own height), of lights in 3D, of walls except along a
  passage's own span (a whole side once counted as open because one passage was on it). Contact
  sheets of in-game stills (`--still` per shot) are the review; a dark wall filling half a small
  thumbnail can look like a bug when it's only an unlit facade, so look at the full frame.
- **Flips at thresholds** come from the cameras either side facing each other, not from either
  one alone: making the first shot past a door "look the way he walks in" made it worse. Rooms
  along the route share a travel direction, so their cameras agree; entry zones hold close to it.
- **The container sleeps when the session is idle** (about five minutes after the last turn ends)
  unless a tracked background task (a Bash `run_in_background` waiter) is still running, and that
  kills a detached render queue too. A `send_later` check-in does not keep it awake. Keep a waiter
  armed for the whole render: one that returns at a milestone (the next N rooms done) under the
  two-hour limit, then arm the next.
- **Render queue and plans:** a Blender run reads the room files when that room starts, so
  changing the planner mid-queue leaves rendered rooms on the old shots. Freeze the planner first;
  compare a room's shots with a saved copy to find the few to re-render (`--shots a,b`).
- `depth_pack.py --prune` removes plates of shots a room no longer has; pack re-rendered rooms with it.
- The camera planner only knows its own room's props: a camera standing out through a passage can
  hang over the next street's kiosk (Rembrandtplein m, n did; fixed with `AVOID`). The general fix,
  not yet done: read the neighbours' props near passages into `_avoid`.
- A fresh container's asset fetch: the shelf-stock scans (shops.py's `SCANS`) and "ph:<id>" textures
  named in kit code were both missed or mis-fetched before this session's fixes; if a render stops on
  a missing or map-less asset, `polyhaven.py fetch` again (it now asks Poly Haven what each asset is).

## Decisions the user made
- **The big squares are channelled** with the evacuation's crowd-barrier lanes (chosen over keeping
  them open with ~430 shots, or looser framing in the squares), for RE3-style framing.
- **Fix the fixed-camera bugs before** the over-the-shoulder camera.
- The gun shop (`wapenhandel`) stays as it is ("ignore the gunshop becoming a regular shop for
  now"). Weapons can also be hidden in ordinary shops; the police post has an armoury.
- The title screen stays basic for now: no background image, and no Continue until there are saves.
- Don't render more than the change needs (the user is careful with credits).

## Open, in order (ask before starting the big ones)
0. **The user's playtest notes** (they are writing them up): more bugs in the fixed cameras and
   controls are coming. The over-the-shoulder camera with an on-the-fly toggle (R3 / V) is on hold
   by the user's choice until the bugs are done; the plan for it is in the 2026-11-08 session (a
   box-room prototype first, then real room geometry, then baked lighting).
1. **Waiting on the user:** should the cellar (`kelder`) and the water gate (`waterpoort`) lose
   their strong teal, cold-lit look? It predates the colour pass.
2. **Task #20: the interior pass, part 2.** Match each shop's camera and light to a reference
   photo of a real shop of its kind, and check them side by side.
3. **Saves** (the typewriter), then a Continue on the title screen.
4. **What lies past Noord** (the README's next area).
5. **Final-quality backgrounds** on the user's M4 Pro:
   `python3 tools/pipeline/build_backgrounds.py --quality final --gpu`.
6. **Deferred items:**
   - #27, a palm arch joint for the 870's right wrist (a rig change, then refit with
     `--fitgrips`, `--fitpistol`, `--fit870`);
   - reload tuning from the user's playtests;
   - rumble and SDL3; the cyclist and other creatures.
