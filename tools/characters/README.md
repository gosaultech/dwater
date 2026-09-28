# Character pipeline (MakeHuman to `.dwc`)

<!-- damned_waters/tools/characters/README.md: how the cast is built, and why it's built this way. -->

This pipeline builds the game's people (the survivor and the Drowned citizens of Amsterdam)
from **MakeHuman's CC0 human**. The output is one small binary file per character,
`engine/assets/characters/<name>.dwc`. The engine loads that file and skins it on the GPU.

```bash
python3 tools/characters/build_characters.py             # the whole cast
python3 tools/characters/build_characters.py survivor    # one character
python3 -m unittest discover -s tools/characters/tests   # unit tests (no download needed)
```

On its first run the build clones a pinned MakeHuman commit's data into
`tools/characters/.cache/` (about 130 MB, gitignored). Later runs are offline. Every build is
logged to `tools/characters/builds.db` (SQLite):

```bash
sqlite3 tools/characters/builds.db "SELECT datetime(at,'unixepoch'), character, status, vertices, seconds FROM builds ORDER BY id DESC LIMIT 5;"
```

## The idea (ELI5)

A tailor doesn't sculpt a suit out of thin air. They start from a real body, measure it, and
cut cloth to fit. This pipeline works the same way:

1. **Body.** Start from MakeHuman's average human, a 13k-vertex mesh an artist spent years on.
   Blend in "macro" morphs (gender, age, muscle, weight, height, ethnicity) exactly the way
   MakeHuman does. It works like mixing paint from a few base tubes: each morph is one corner of
   a box, and a body is a weighted mix of the corners around its settings.
2. **Pose.** MakeHuman models stand in an "A" pose, with the arms out. The pipeline swings the
   arms down with MakeHuman's own 163-bone skeleton. It spreads the turn over the collarbone,
   shoulder and upper arm, so the shoulder keeps its shape instead of pinching.
3. **Engine space.** Convert to metres, face -Z, and put the soles on the floor.
4. **Fold the skeleton.** The engine animates 24 joints. Each of the 163 bones joins its
   nearest mapped ancestor: every spine bone folds into `spine` or `chest`, every finger segment
   into the knuckle line, and so on. Each vertex keeps its four strongest influences.
5. **Clothes as shells.** A garment is a patch of the body's own skin, chosen by a rule such as
   "legs from the waist to the ankle". The patch is then:
   - pushed outward;
   - smoothed so it drapes over the anatomy instead of clinging to it (Taubin smoothing, which
     doesn't shrink);
   - stretched like a drum skin across hollows (the `membrane` pass), so a leather jacket spans
     the chest instead of showing every muscle;
   - loosened into its cut (straight jeans, a boxy leather jacket that falls straight from the
     chest, with each horizontal slice pushed out to its convex hull);
   - creased where cloth creases;
   - cut exactly along smooth lines (`trim`): hems, cuffs, necklines and the jacket's opening
     are clipped through the triangles, so the edges are clean curves rather than the
     stair-steps of the body mesh;
   - given thickness at the hem.

   Pieces laid on another garment (backpack straps on the jacket) are cut from that garment's
   outer surface with `clip_overlay`, so the two can never cross.

   Because it's made from the skin, the garment inherits the skin's joint weights and moves with
   the body for free. Skin that is fully covered is dropped, so nothing pokes through.
6. **Face.** The pipeline paints lips, brows, stubble and palms using MakeHuman's facial bone
   weights as a map. The lips are wherever the *orbicularis oris* bones pull, so the paint lands
   on the right place on every body shape.
7. **Write** the result as a `.dwc` file.

The engine adds what moves or is held, in C++ (`engine/src/cast_*.cpp`):

- physics locs, anchored to scalp points the pipeline exports;
- the backpack, the flashlight and the pistol, anchored the same way;
- hoodie drawstrings;
- for the Drowned: guts sagging from the split belly, the swollen tongue, loose skin, the tie
  knot and staff pass, mussels, canal weed, and long wet hair.

## The Drowned citizens

`cast_drowned.py` dresses three ordinary Amsterdammers the way they went into the water;
`drowned.py` then ruins them the same way for each. Think of it as two passes by two
departments: wardrobe first, then the make-up effects team.

| Id | Who | Wardrobe | What the canal did |
|---|---|---|---|
| `office_worker` | Jeroen, 48, civil servant | Pale blue shirt with the collar open, a loosened burgundy tie, lanyard and staff pass, charcoal trousers and belt, one shoe | Belly split with guts out, torn right cheek, scalp slipping at the front, left hand degloved |
| `woman_dress` | Sanne, 34 | Teal midi dress with a small flower print, cropped mustard cardigan, barefoot | Long wet hair over her face, torn right cheek, left hand degloved |
| `pieter` | Pieter, 67, pensioner | Navy cable-knit sweater over a checked shirt collar, faded jeans, white trainers | One eye gone, torn left cheek, belly split through the sweater, right hand degloved |

The engine picks them by variant: `Character::make(Kind::Drowned, 0 | 1 | 2)`.

What makes them read as bodies rather than painted mannequins:

- **Bloat** uses MakeHuman's own morph targets (belly, face, neck, hands) instead of scaling.
- **Tears are real holes with depth.** Wounds are cut exactly along a ragged outline (like a
  garment trim), and the cut edge is folded inward into a wall of flesh (`drowned.skin`).
  The surface keeps its skin material; only the walls are flesh. Materials change per
  triangle, so a material boundary on the skin would show as jagged shards.
- **Cut edges blend their skin weights.** A new vertex on a cut takes a mix of both ends'
  joint weights (`garments.dense_weights` / `top4`), not one end's. The Drowned's jaw hangs
  open 54 degrees, and copied weights would tear the edge into spikes.
- **Small things lie on the clothes.** The tie and lanyard are cut from the shirt's outer
  surface (`clip_overlay`, subdividing first with `detail` for pieces narrower than a face of
  the body mesh). The knot and pass sit on anchors placed on the shirt (`on_garment`).
- **A skirt from MakeHuman's skirt proxy** (`garments.build_helper`), because a shell of the
  body can't bridge the gap between the legs. It is flared toward the hem.
- **Collars follow the neckline loop** (`garments.neckline` walks the edge and ignores stray
  slivers), with weights blended along it.
- **Eyes** are rings round the pupil (`cast.eyeball`), so a clouded iris stays round and crisp.

Sanne's hair is grown in the engine from 220 scalp anchors as flat ribbons ("hair cards")
rather than tubes. Each ribbon lies against the skull, and its edges and ends are stippled away
into single hairs by the shader (`MAT_WETHAIR`).

## Files

| File | Role |
|---|---|
| `mhdata.py` | Fetches the pinned MakeHuman data. Reads the base mesh (OBJ), morph targets, skeleton and skin weights. Holds the macro-slider maths (`macro_factors`), mirroring MakeHuman's `human.py`. |
| `rig.py` | Re-poses from the A-pose (linear blend skinning with all 163 bones), converts axes (`to_engine`), finds engine joint positions, and folds the weights (`fold_weights`). |
| `body.py` | `Body`: one morphed, posed, engine-space human with normals, engine weights, body regions and MakeHuman's own bone weights (for face paint). |
| `garments.py` | `Garment` and `build()` (clothes as body shells); `clip` (exact trims that blend skin weights), `subdivide`, `fold_edges` (hems, tear walls), `clip_overlay`, `collar` and `neckline`, `build_helper` (garments from MakeHuman's proxies); the helpers `adjacency`, `taubin`, `boundary_loops`, `hang_straight` and `knit_rib`; and `shoe()` (a boot built like a cobbler's last). |
| `parts.py` | The `MAT` table (mirrors `dw::Mat` in `engine/include/dw/mesh_builder.hpp`) and `part_from_quads`. |
| `cast.py` | The survivor, plus shared pieces: eyes, hair caps, hair patches, brows, lashes, scalp anchors. |
| `cast_drowned.py` | The Drowned citizens: wardrobe, gore anchors, and the per-character touches. |
| `drowned.py` | What the canal does to any body: bloat targets, wounds and their flesh walls, drowned skin paint, canal-stained cloth. |
| `bake.py` | Baked ambient occlusion per vertex (voxel grid and hemisphere rays), stored in the colour alpha. |
| `dwc.py` | The `.dwc` binary format: `write`, `read`, and the byte layout. |
| `build_characters.py` | Command line entry point and SQLite build log. |
| `tests/test_characters.py` | Unit tests: macro weights sum to one, rotations, the axis change, weight folding, mesh helpers, the `.dwc` round trip, and checks on the shipped `survivor.dwc`. |
| `tests/test_drowned.py` | Unit tests: weight blending on cuts, subdivision, folded edges, the neckline walk, and checks on the shipped citizens (skinning, height, tear walls, gore and hair anchors). |

## The `.dwc` format

The format is little-endian throughout. The full layout is documented at the top of `dwc.py`
and read by `engine/src/character_file.cpp`.

- **Header.** The magic `DWC1`, then the version.
- **Joints.** 24 rest-pose joint positions.
- **Parts.** Each part is a separately drawn mesh (body, jeans, hoodie and so on). A vertex
  carries:
  - position, normal and sRGB colour;
  - material ID (`dw::Mat`) and body region (`dw::Region`, which drives dismemberment);
  - four joint IDs and four weights.

  Triangles follow as 16-bit indices, so a part has at most 65535 vertices.
- **Anchors.** Named points in joint space: loc and hair roots, backpack, flashlight,
  drawstrings, and for the Drowned `guts`, `tongue`, `loose_skin`, `tie`, `badge`,
  `mussels*` and `weed*`.

The C++ loader bounds-checks every read. A truncated or foreign file gives an error string,
never a crash (see `engine/tests/test_character_file.cpp`).

## Libraries

| Library | Used for | Why |
|---|---|---|
| **numpy** | All mesh maths: morphs (sparse deltas via `np.add.at`), skinning, normals, smoothing | Vectorised maths keeps a full build to seconds rather than minutes. |
| **sqlite3** (standard library) | Build log | Zero setup, and one file you can query. |
| **struct**, **dataclasses**, **pathlib**, **subprocess** (standard library) | Binary packing, records, paths, the `git` fetch | No extra dependencies. |
| **unittest** (standard library) | Tests | Same framework as `tools/pipeline/tests`. |
| **git** (command line) | Sparse, blob-less clone of one pinned MakeHuman commit | Reproducible, and downloads only the folders it needs. |

## Licence of the source data

MakeHuman's base mesh, targets, skeleton and weights are CC0 1.0 (public domain), as stated in
`LICENSE.ASSETS.md` in the MakeHuman repository. MakeHuman's *code* is AGPL. None of it is
imported or copied here: the pipeline reads only the data files, and the macro-slider weights
in `mhdata.py` are our own implementation of the same blending rule. The generated `.dwc`
files are derived from CC0 data and ship with the game.
