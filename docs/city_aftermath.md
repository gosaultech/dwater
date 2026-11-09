<!-- damned_waters/docs/city_aftermath.md — the brief for dressing the city's streets and shops: an Amsterdam emptied by an evacuation and struck by a catastrophe, not one that was never busy. Every area follows it when it is scaffolded; areas 1–3 get it retrofitted before the final polish pass. -->

# City aftermath: how the streets should look

Amsterdam is one of the busiest tourist cities in the world. A street with nobody in it reads as
*unfinished* unless it is full of the things people left behind. The city had a disaster, an
evacuation was ordered, everyone went, fast. What's left: the Drowned (the ones who turned), and
everything the living dropped on their way out.

Like a stage after the audience has fled the theatre: the coats are still on the seats.

## The rules

- **Never empty, never crowded.** Every shot shows signs of people: a few things in the foreground,
  more down the street. Clutter sits where people walked (the middle of the pavement, by doors, by
  the tram stops), never neatly along the walls.
- **The power is still on.** Neon, shop windows and street lamps burn. Emergency lights (blue,
  amber) are the only ones that flash.
- **One story per street.** Each street gets one thing that happened there (the evacuation queue for
  the trams, a looted jeweller, the aid post where people were checked), plus the general mess.
- **Tragedy, not gore** (the user, 2026-11-09: "the streets really tell a story of survival and
  tragedy", RE3's Raccoon City as the model). The dead are covered or bagged, never shown; the
  tragedy is in what's written and left: the missing posters, the messages, the empty pushchair.
- **Survivors are tabled** until the story has a place for them.

## The night itself: the catastrophe layer

Emptied in a hurry was the first pass; this is the second, and it's the one that sells it. The user
asked for a world that feels "lived in, dirty, run down, like a real catastrophic event happened".
Rokin is the first street done this way (the vertical slice); every street follows it.

- **The water's mark on everything.** A tide line at the street's flood height (its "outdoor" tide)
  on every wall, door, car and post, a pale crust at the line and silt below it; real scanned mud
  over the street in patches, thickest against whatever stands; rust on bare metal; streaks down
  the walls from every ledge (`builders._wear`, `ruin.silt`).
- **Debris where it would drift.** The flood's leavings (scanned bottles, cans, crates, branches,
  bags, tyres, boots) piled against walls, kerbs and the railing, thinner in the open; the big
  pieces off the lanes he walks (`catastrophe.drift`). Bikes wound into railings; a raft of rubbish
  in the basin.
- **One story per street, told by the night.** What went wrong there: Rokin's last tram derailed
  and slewed toward the water with its wire down and arcing; a car run into the quay and burned;
  the dead lined up by an ambulance. Then what the survivors and rescuers wrote: messages sprayed
  in Dutch ("HOTEL VOL · 14 LEVEND", "NIET NAAR BENEDEN"), the search teams' X on the doors they
  went through, missing posters papering the police post, shops boarded and written on
  (`catastrophe.STORIES`, `ruin.py`, `tools/assets/decals.py`).
- **The painting is alive.** Fires burn and breathe their light on the walls, beacons flash blue
  down the street, a snapped wire throws sparks, a tram's last tube fails (the room's "fx"; the
  engine's live layer, `dw/fxlive.hpp`).
- **Something by the lens.** Each shot looks past something close (a bag, a tyre, a crate), placed
  where it never hides him (`catastrophe.foreground`).

## The kit (what each area draws on)

| What | Where it goes | Source |
| --- | --- | --- |
| Crowd barriers with police tape, concrete jersey barriers | street mouths, checkpoints | built (`landmarks.crowd_barrier`); CC0 scans `concrete_road_barrier` |
| "EVACUATIEROUTE → CENTRAAL" boards, hand-painted arrows | junctions along the route north | built |
| Aid post: a gazebo tent, stretchers, a floodlight on a generator, a covered body | squares | built; CC0 `portable_searchlight`, `portable_generator` |
| Dropped luggage: suitcases, bags, a pushchair, a wheelchair, crutches, shoes, umbrellas | pavements, tram stops | CC0 `vintage_suitcase`, `wheelchair_01`, `vintage_crutches_01`, `rubber_boots`; built |
| Leaflets (evacuation notices) blown everywhere | ground, against kerbs | built (paper cards) |
| Abandoned vehicles, doors open, lights on: cars, a taxi, a police van, an ambulance | roads | built; CC0 `covered_car` |
| Bikes in heaps, scooters on their sides | everywhere | built (`street.bike`) |
| The water: a tide line on the fronts, silt and weed on the cobbles near canals, puddles | canal streets | material on facades and ground |
| Sandbag walls across shop doors, fire-brigade pumps with hoses into the canal | shops, quays | built; CC0 `metal_jerrycan` |
| Lifebuoys, life jackets, a dropped megaphone, a gas mask | quays, checkpoints | CC0 `lifebuoy`, `life_jacket`, `Megaphone_01`, `old_gas_mask` |
| Looting: a smashed shop window and the glass on the pavement, shelves stripped | one or two shops a street | built |
| Overturned terraces, a table still set | cafés | CC0 `outdoor_table_chair_set_01` |
| The evacuation point: buses with their doors open, army trucks, a field hospital (olive tents, a red cross), mobile light towers | the squares the army used (the Dam) | built (`aftermath.bus`, `vehicle`, `aid_post` with `"military"`, `light_tower`) |
| A shelter: camp beds in rows, blankets thrown back, a bag at each foot | churches, halls | built (`aftermath.camp_bed`) |

Pickups (ammunition, medicine) are never painted into a picture: the game draws them, so they can
be taken. Anything painted that looks like a pickup must not be one.

The first districts (Herengracht, Thorbeckeplein, Rembrandtplein, Reguliersbreestraat, Muntplein, the
Bloemenmarkt) predate this brief; their stories are retrofitted by `tools/citygen/aftermath13.py`: a family's
luggage at the kerb, the hotel's guests, the queue for the last tram, a looted coffeeshop and a taxi, the
police line at the Rokin, sandbagged doors along the flower market.
