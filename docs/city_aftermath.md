<!-- damned_waters/docs/city_aftermath.md — the brief for dressing the city's streets and shops: an Amsterdam emptied by an evacuation, not one that was never busy. Every area follows it when it is scaffolded; areas 1–3 get it retrofitted before the final polish pass. -->

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
- **Horror stays rare.** A covered body or two near an aid post at most. The Drowned are the horror;
  the dressing is sadness and haste.
- **Survivors are tabled** until the story has a place for them.

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
