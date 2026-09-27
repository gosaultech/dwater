<!-- damned_waters/README.md: how to run, test and extend the demo -->
# Damned Waters: Demo "Het Grachtenpand"

Fixed-camera survival horror set in a drowning Amsterdam. The demo is one canal house (hall, parlor, flooded cellar): three rooms, seven pre-rendered camera shots, three enemy types and a boss, about 10-15 minutes of play.

## Play it (macOS)
1. Install **Godot 4.7** (Standard, not .NET).
2. Godot Project Manager: **Import**, select `game/project.godot`, then **Run** (F5). The first open imports assets for about a minute.

| Action | Keyboard / mouse | Gamepad |
|---|---|---|
| Move / run | WASD / Shift | Left stick / B |
| Aim / fire | RMB (hold) / LMB, J or Space | LT / RT |
| Aim up / down while aiming | W / S | Left stick |
| Reload / switch weapon | R / 1, 2, F | X / R3 |
| Dodge / quick turn | C or Alt / Q | RB / LB |
| Interact, kick | E | A |
| Inventory / pause | Tab / Esc | Y / Start |
| Tank / modern controls | T | Back |
| Debug: show collision | F1 | |

## How the pre-rendered look works
One JSON **RoomSpec** per room (`game/data/rooms/*.json`) is the single source of truth. Blender reads it to render each shot's background and a 16-bit **depth image**. Godot reads the same file to build collision, camera zones, doors, pickups and enemies. A shader writes the painted depth into the GPU depth buffer, so real-time characters are hidden by painted furniture, water and walls. Camera cuts are a transform plus two preloaded textures: no disk I/O, no hitch.

```bash
# Re-render backgrounds after editing a RoomSpec or tools/blender/builders.py (GPU, final quality):
python3 tools/pipeline/build_backgrounds.py --quality final --gpu
# Rebuild creature models + material library (then refocus Godot to re-import):
python3 tools/art/materials.py && /Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender/enemies_v2.py
# Re-render character look targets (studio key art + in-room target frames):
/Applications/Blender.app/Contents/MacOS/Blender -b -P tools/blender/render_characters.py -- --mode frames --quality final --gpu --samples 256
# Regenerate placeholder audio (needs numpy + scipy):
python3 tools/audio/synth_sfx.py
```

## Tests
```bash
# Godot unit tests (GUT is vendored in game/addons/gut): 55 tests
godot --headless --path game -s addons/gut/gut_cmdln.gd -gdir=res://tests/unit -ginclude_subdirs -gexit
# Scripted combat run (pistol, kick, shotgun, full boss fight); exit code 0 = pass
godot --headless --path game -s res://tests/visual/combat_smoke.gd -- --autostart
# Visual checks (need a display): staged screenshots and enemy bestiary
godot --path game -s res://tests/visual/capture.gd -- --autostart --out=/tmp/caps
# Python pipeline + telemetry
python3 -m unittest discover -s tools/pipeline/tests && python3 -m unittest discover -s tools/telemetry/tests
```

## Telemetry (SQLite)
The game appends JSON lines to `~/Library/Application Support/Godot/app_userdata/Damned Waters/telemetry/`. Events include shots, hits, kills, damage, deaths, saves, camera cuts, and frame-time percentiles every 10 s. Load them into SQLite and report:
```bash
python3 tools/telemetry/ingest.py ingest && python3 tools/telemetry/ingest.py report
```

## Layout
```
game/        Godot project. src/core = pure logic (brains, weapons, inventory, codecs), fully unit tested;
             src/actors = player + enemies; src/world = rooms, cameras, plate shader; src/ui; data/rooms
tools/       blender/ (room builder, character kit, renderers), pipeline/ (depth packing), audio/, telemetry/
docs/        enemy_design.md, concept/ (character key art + target frames), enemy_designs/ (in-game placeholders)
```

## What's final vs placeholder
- **Pipeline, systems, combat, tests:** production-shaped.
- **Backgrounds:** procedural Blender sets rendered at 960x540 with 20 samples. Run the final-quality command above on the M4 Pro.
- **Characters in game:** procedural placeholders by default. Real rigged models drop in via `game/data/characters/*.json` (see `docs/character_pipeline.md` for sourcing MetaHuman/CC/Mixamo and zombifying them).
- **Audio:** synthesized placeholders. Replace any WAV in `game/assets/audio/` with a recording of the same name.
