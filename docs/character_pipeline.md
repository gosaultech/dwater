<!-- damned_waters/docs/character_pipeline.md: how to get RE2-remake / Echoes-level characters into the game -->
# Character Art Pipeline: from placeholder to RE2-remake quality

**Why the current characters look like clay.** The procedural bodies have no real anatomy: no facial planes, clavicles, tendons or fabric folds. RE2 Remake-grade characters come from **photogrammetry scans of real people**, refined by character artists. Their detail is **baked from multi-million-polygon sculpts** into normal maps, backed by **scanned skin textures**, **SSS skin shaders** and **hair cards**. No script generates that data. You source it (scans / MetaHuman) or sculpt it.

## Status of the real-model slot (honest)
- Verified: auto-facing from heel->toe bones (fixes models that face -Z); bone lookup tolerant of Godot's import renaming (`mixamorig:Hips` -> `mixamorig_Hips`).
- NOT yet verified: merging animation clips from a different rig (`animation_sources`) broke skinning in testing, and the `zombify` material pass is untested visually. Validate both with real assets on real hardware: `godot --path game -s res://tests/visual/model_check.gd -- --autostart`.

## The game side
Drop a rigged `.glb` in `game/assets/characters/<id>/<id>.glb`. The manifest `game/data/characters/<id>.json` maps clips, bones and scale. `CharacterFactory` swaps it in for the placeholder; if the file is missing, the game keeps working with placeholders. Wired today: `survivor` (player) and `verdronkene`.
- Locomotion clips play at speed-matched rates (no foot sliding).
- A `PoseOverlay` skeleton modifier swings the arms to the aim direction on any rig, so you don't need aim clips to start.
- Room lights already light real models to match the pre-rendered plates, and depth compositing works with them (verified with a stand-in Mixamo-rigged model).

## Recommended sourcing (solo, Godot, commercial-safe)
| Character | Source | Why |
|---|---|---|
| **Survivor** | **MetaHuman** (UE 5.6+, free under $1M revenue; allowed in Godot since June 2025, no AI training) | Scan-based faces: the closest free thing to RE2R. Expect a tech-art pass: UE → FBX → Blender → glTF. See the community MetaHuman→Godot look-dev tool (ibrews/MetaHumanGodot, MatMADNESS SSS skin shader, MIT). |
| Alternative | Character Creator (Reallusion, paid) + Headshot, or Renderpeople scanned rigged people | CC has the smoothest DCC export and a huge clothing/hair library. |
| **Verdronkene** | Same human base (a MetaHuman or CC body with a different face per zombie), then **zombified**: sculpt bloat and wounds in Blender, texture marbling/wet skin in Substance Painter (the bible's optional €149 tool), hair cards for wet lank hair | Every RE zombie is a human base plus makeup. Variety comes from swapping heads and clothes. |
| **Kelderkind, Grachtenvorst** | Sculpt in Blender starting from `tools/blender/characters.py` base meshes (that's what they are for). Retopo, UV, bake normal/AO, texture in Substance. Or commission a creature artist (ArtStation) with `docs/concept/` + `docs/enemy_design.md` as the brief. | Creatures can't be sourced from human generators. This is the one place paid art time pays off most. |
| **Animations** | Mixamo (free, `mixamorig` skeleton: zombie walk/attack/death, pistol idle/aim/walk). Retarget to MetaHuman/CC skeletons in Blender or with Godot's humanoid retargeting | The manifest's `clips` map uses these names directly. |

## Godot look checklist (what makes it read as "polished")
1. Skin: SSS enabled, a detail normal map for pores, roughness varied by region (nose and forehead oilier). For the Drowned, add a clearcoat for the wet film.
2. Eyes: separate cornea with a refraction/specular highlight; this does most of the "alive vs dead" work.
3. Hair: alpha-tested cards with alpha antialiasing; wet hair gets lower roughness.
4. Lighting: per-room light rigs already mirror the Blender lights. Next step is a per-room panorama from Cycles as the character's environment/reflection light, so bounce color matches the plates.
