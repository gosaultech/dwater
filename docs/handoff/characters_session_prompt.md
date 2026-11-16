<!-- damned_waters/docs/handoff/characters_session_prompt.md -->
<!-- Purpose: the brief for the next session (characters, hair, enemies, weapons and items), written so a brand-new session can pick up without this one. Paste the block below as the first message. -->

# Next session: the cast and their kit

Paste this as the first message of a new Claude Code session on `gosaultech/dwater`:

```text
Continue Damned Waters (repo gosaultech/dwater), a survival-horror game set in Amsterdam on the
night the water came (RE3-style fixed cameras over pre-rendered backgrounds; engine/ is C++17 /
raylib 5.5). Start from the default branch claude/inspiring-turing-gl0kys and develop on the
branch this session is given.

FIRST: read CLAUDE.md, then docs/handoff/session_memory.md, then
docs/handoff/characters_session_prompt.md (this brief, with the file map and the decisions
already made). Set up the container as session_memory.md says before anything else.

THIS SESSION: make the people and what they carry look like a polished game.
1. The main character (the survivor) must look GREAT, and his hair (his locs) as good as it
   can possibly look.
2. The enemies (the Drowned) must look disgusting and scary.
3. The weapons (the pistol and the shotgun) and the item models must look polished and real.
All of this is drawn live by the engine over the backgrounds: no background re-render is needed
this session, so don't start one.

Decided already: keep the generated bodies (MakeHuman-based, tools/characters) and make them
look much better ("option A"); do not swap in licensed character models. Licensed CC0/CC BY
textures, and CC0/CC BY models for guns and items, are allowed (the ledger and licence gate are
in tools/assets/sketchfab.py).

How I work: I'm the game director. Show me before/after checkpoints as rendered images, keep
replies to concise bullets, don't stop to ask what you can decide yourself, commit and push as
soon as each piece stands up (the container is sometimes replaced and loses everything
uncommitted). I pay for tokens: keep image reviews lean. Open a PR and merge when I ask.
```

## Where things are (read before changing anything)

- **Shading of everything on a character**: `CHAR_FS` in `engine/src/shaders.cpp`. Each surface
  is a material number (`vMat`): 1 living skin, 2 drowned skin, 3 sheet, 4 wool, 5 waxed cotton,
  6 denim, 7 leather, 8 short hair, 9/10 wet eyes, 12 raw flesh, 16 dead eye, 17 teeth, 18 bone,
  19 tongue, 20 intestine, 23 loose skin, 24 dermis, 25 brushed steel, 26 rubber grips, 28 cable
  knit, 29 lips, 30 brows, 31 soles, 32 nylon, 33 cotton, 34 print, 35 locs, 37 soaked long hair,
  38 water drops, 39 walnut, 40 blood, 41 gun synthetic. After the per-material block come the
  shared passes added in the last session: folds, wear and stains, the flood's mud up the legs,
  rain (`u_wet`), cloth's nap, a harder light (less wrap), deeper occlusion. Lighting uniforms
  are set in `Game::upload_lights` (`engine/src/game.cpp`); the fill light is there too.
- **Who is built how**: `engine/src/cast_survivor.cpp` (him), `cast_drowned.cpp` and
  `cast_citizens.cpp` (the enemies), `cast_guns.cpp` (pistol "m92fs", shotgun "r870"),
  `cast_items.cpp` (pickups), `mesh_builder.cpp`, `character.cpp` (poses, the dead),
  `dw/anatomy.hpp` (body regions that can be shot away). The bodies come from
  `tools/characters/` (MakeHuman CC0 base, garments, rig, bake to `.dwc`):
  `python3 tools/characters/build_characters.py [name]`.
- **Design notes**: `docs/character_pipeline.md` (why they read as clay and what real games
  do: baked sculpt detail, scanned skin, SSS, hair cards), `docs/enemy_design.md` (the Drowned).
- **Guns are fitted to his hands**: `--fitgrips`, `--fitpistol`, `--fit870`, `--fitreload` and
  `--clearance` in `engine/src/main.cpp` regenerate `grips_fitted.inc` and the pose tables.
  Changing a gun's shape means re-running them, then `--clearance` must report nothing through
  anything.
- **Looking at them** (all under `xvfb-run -a -s "-screen 0 1920x1080x24"`):
  - `damned_waters --sheet out --only survivor` (studio turnaround; `--only drowned0`, ...).
  - `damned_waters --view survivor@head,20,5,0.7,0,1.6,30 out.png` (one close shot; who:
    `survivor`, `drowned[N]`, `@head|@chest|@pelvis|@hand`, or a gun `m92fs | r870`).
  - `damned_waters --room voorkamer --still 3.6,2.6,200 out.png --shot a` (in a lit room); the
    street look is best judged in `rokin_noord` (shots e, l) at night with rain.
- **Tests**: `<build>/dw_tests` (199 at the end of the last session), the tool suites in
  `tools/*/tests`, `--capture <dir>` (97 setups) and `--walkthrough <report.txt>` (255 trials,
  0 failed). Run all of them before asking for a merge.

## Ideas that fit "option A" (a starting point, not a prescription)

- **His face and skin**: a real skin detail texture (CC0 scans, e.g. pores and fine wrinkles) in
  place of noise, a proper subsurface look (red-shifted terminator), specular breakup, eyes with
  a wet meniscus and a catchlight, darker eyelid creases and lash line.
- **His locs**: the strands' own geometry (thicker, tapered, slightly frizzed rope), alpha
  frizz cards round each loc, a root-to-tip colour shift, anisotropic sheen, self-shadow in the
  shadow maps, and rain making them darker and glossier.
- **The Drowned**: bloated and waxy skin with marbling, slippage and blisters (mat 2, 23, 24),
  wet glossy rot, silt in the creases, torn clothes clinging wet, milky eyes (16), and wounds
  with depth (12, 13, 40). Scary in silhouette as well as close up.
- **Guns and items**: bevelled edges (no knife-sharp or rubber-round silhouettes), real
  materials (parkerised and blued steel, worn edges, stippled polymer, walnut), small parts
  (screws, sights, markings invented: no real brands), or CC0/CC BY models refitted to his
  hands. Pickups the same: herbs, ammo boxes, keys.

## Later, in a separate session (after the cast is done)

Not this session: these are baked into the backgrounds and need a re-render of the streets they
appear in (about ten street rooms, not all 27), batched into one run with
`tools/dev/render_queue.sh`.
- Dutch number plates (yellow, black lettering, invented numbers) as decals over the licensed
  cars' own plates (`tools/blender/licensed.py`).
- Abandoned cars along the kerbs, placed by `tools/citygen/catastrophe.py` (new rooms' specs join
  `LOOK2`-style with their plates, as the second look did).
- The city bus's "TOWN BUS" livery replaced with an invented Amsterdam one (projected like the
  ambulance's stripes in `licensed.py`).
