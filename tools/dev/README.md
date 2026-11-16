<!-- damned_waters/tools/dev/README.md: the helper scripts for working in the cloud container. -->
# tools/dev

Scripts for the container, kept in git because its scratch folder is wiped when the container is
replaced.

- `render_queue.sh <specs dir> <queue file>`: renders the queued rooms one by one at 2048x1152,
  packs each, copies its spec into `game/data/rooms`, and resumes after a restart (only the shots
  still missing are rendered). Start it detached (see the script's header).

ELI5: the night shift's checklist, pinned to the wall instead of kept in someone's head.
