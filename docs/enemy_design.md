<!-- damned_waters/docs/enemy_design.md: enemy design bible for the demo and roadmap -->
# Damned Waters: Enemy Design

Rules every enemy obeys (from the dev bible, enforced by tests):
- **Readable tells.** Every attack has a wind-up of at least 0.5 s (`test_every_enemy_windup_is_readable`). Tension should come from "I see it coming and might not escape", never from cheap hits.
- **Silhouette first.** Each enemy must be identifiable as a black shape against a lit plate: upright and bloated, low and spidery, or towering and fused.
- **Heard before seen.** Each has an audio signature, played from its position.
- **Amsterdam-born.** Every enemy comes from the city's water, history or architecture.

Concept renders are in `docs/concept/`. Target frames show the cast in the real rooms through the game cameras. In-game models are still procedural placeholders; the concept sculpts in `tools/blender/characters.py` are the base meshes to refine and rig.

## Art direction (v2): PS2-era creature design
Horror from **silhouette and wrongness, not facial detail** (the Silent Hill 2/3 lesson). Faces are hidden, inverted or replaced. Every design uses Amsterdam materials: the coroner's wet sheet, fishing net, mooring rope, and the thousands of bicycles fished out of the canals each year.
Models: `tools/blender/enemies_v2.py` builds the geometry. Surfaces come from `tools/art/materials.py` (tileable PBR with normal maps, applied triplanar by material name in Godot). Animation is procedural per species (`src/actors/creature_model.gd`). Key art: `docs/bestiary/`.

| Creature | Hook | Silhouette | Where |
|---|---|---|---|
| **Verdronkene, the Veiled** | Still wearing the coroner's sheet; the cloth is sucked into the mouth when it breathes | Hooded, bowed, long waterlogged coat | Demo |
| **Verdronkene, the Netted** | Bound in a fishing net that pins one arm | Same body, cross-hatched torso | Demo |
| **Kelderkind** | Walks backbent on hands and feet; the upside-down head hangs between its arms, hair dragging on the floor | Low, pale, four high joints | Demo |
| **Grachtenvorst** | Veiled bodies fused with canal bicycles: wheels jut from its back, bike frames cage its green heart, sprockets are fused into its fists | Huge mass, raised club arms | Demo boss |
| **Pestmeester** | 2.2 m plague doctor; the leather beak hangs slightly open over something pale and wet; the coat hides that it has no legs to walk with | Tall black cone, wide hat, lit lenses | Stalker (post-demo) |
| **Fietser** | A drowned cyclist fused into a rusted granny bike, face sealed under a yellow rain poncho, a bicycle bell lodged in its mouth | Yellow shape on two thin wheels | Street charger (post-demo) |

## Demo roster

### Verdronkene (The Drowned): the baseline threat
- **Fantasy:** townsfolk who went into the contaminated canals and came back. Pieter from the note is one of them.
- **References:** drowning pathology (bloat, marbled skin, clouded eyes, "washerwoman" hands), *The Ring*'s wet hair over the face, RE2's zombies for pacing.
- **Silhouette:** hunched and bloated, arms reaching forward, head lolling.
- **Behavior:** `IDLE -> ALERT (0.7 s) -> PURSUIT (0.85 m/s, slow turns) -> ATTACK (0.85 s arms-up tell) -> RECOVERY (1.1 s)`. Hit it to stagger it, with a 1.2 s immunity window; shotgun blasts and kicks ignore that immunity.
- **Counterplay:** shoot to stagger, then **kick** (E) to floor it for 2.4 s, then finish it or walk past. One point-blank shotgun blast kills (tested).
- **Audio:** wet gurgle every 3-7 s, a rising moan on wind-up.

### Kelderkind (Cellar Child): the ambusher
- **Fantasy:** something that lived in the cellars and chimneys long before the flood.
- **References:** the crawlers of *The Descent* (eyeless, emaciated, cave-pale), the spider-walk in *The Exorcist*, Silent Hill's low-profile creatures.
- **Silhouette:** a horizontal white shape with elbows above its back. Eyeless, with a mouth full of teeth.
- **Behavior:** fast (2.7 m/s, faster than you walk), 0.5 s crouch-and-leap tell, then **hit and run**: it retreats for 1.3 s and circles back.
- **Counterplay:** it's low, so auto-aim pitches down for you. Shoot during the crouch, or dodge the leap and punish the landing. 3 HP.
- **Audio:** dry skittering, and a high screech on alert and leap.

### Grachtenvorst (Canal Prince): demo boss
- **Fantasy:** the drowned of a whole street, fused into one mass. The green heart is whatever is in the water.
- **References:** *The Thing* (1982) body horror, RE's chimeras and G-Birkin's growths, Dead Space's Hive Mind, the corpse-clusters of classical Dutch Last Judgment paintings.
- **Attacks:** slam (1.0 s tell, narrow cone, 35 dmg), sweep (0.8 s tell, 140° arc, 25 dmg), charge at range (0.9 s tell).
- **Charging into a pillar dazes it for 2.2 s.** The room design is the counterplay.
- **Weak point:** the glowing heart takes 2.5x damage. Aim UP; auto-aim deliberately targets centre mass. Every 8 damage breaks its stance.
- **Phase 2 (50% HP):** roars, moves 35% faster, tells shrink 20% (still at least 0.64 s), and calls a Drowned out of the water.
- **Arena lock:** the stairs are cut off until it dies.

## Player combat verbs
| Verb | Input | Purpose |
|---|---|---|
| Aim / fire | RMB (hold) + LMB | Auto-targets and auto-pitches; W/S adjusts aim height (headshots, the boss heart) |
| Shotgun | 2 / F | 8 pellets, heavy stagger, knocks down with 5+ pellet hits |
| Kick | E near a staggered enemy | Floors it; the follow-up that makes combat feel active |
| Dodge | C / Alt | 0.3 s of invulnerability. Dodging as a hit lands = **Perfect Dodge**: slow-mo, and your next shot within 1.5 s does 2x damage |
| Quick turn | Q | 180° in 0.3 s |

## Roadmap roster (outside the canal house)
- **Fietser (Cyclist):** fused to a bicycle, wheels spinning. A fast lane-runner on narrow canal streets; you hear the bell before it arrives. References: *Christine*-style machine-fusion, the Licker's speed.
- **Nachtwacht (Night Watch):** a 17th-century militiaman stepped out of the painting, with the wrong face. A slow area guard with pike reach. It punishes rushing in, like RE's armored enemies.
- **Pestmeester (Plague Doctor):** the stalker. The mask *is* the face and something moves inside it. It follows you between rooms (Mr. X / Nemesis model), can't be killed permanently, and announces itself with a tapping cane.
