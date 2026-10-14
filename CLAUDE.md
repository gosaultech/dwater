<!-- damned_waters/CLAUDE.md -->
<!-- Purpose: what Claude Code reads first in every session here: the user's rules, how to build, test and render, and where to find where the last session left off. -->

# Damned Waters: notes for Claude

**Start by reading `docs/handoff/session_memory.md`.** It records where the last session left
off, what is open, and the lessons learned in this container.

## The project
- A survival-horror game set in Amsterdam on the night the water came: RE-style fixed cameras
  over pre-rendered backgrounds with painted depth.
- `engine/` is the C++17 / raylib 5.5 game, and all current work happens there. Read
  `engine/README.md` first.
- `game/` is the original Godot prototype. Its data and assets are shared with the engine
  (`game/data/rooms`, `game/assets`).
- The default branch is `claude/inspiring-turing-gl0kys`. Finished work goes in through a PR to
  it. The user asks for each finished chunk to be merged so they can play it.

## The user's rules
- Branches, commits and PRs:
  - Push only to the session's branch.
  - Open a PR only when asked (or when the user asks for work to be merged).
  - Never force-push someone else's branch.
- No model identifiers in code, comments, commits or PRs. Commit messages end with the
  Co-Authored-By and Claude-Session lines the session gives; PR bodies end with the Claude Code
  footer.
- Code and docs:
  - Every file starts with a path/purpose comment; otherwise keep comments short.
  - Write tests for new logic: GoogleTest in `engine/tests`, unittest in `tools/*/tests`.
  - Keep latency low.
  - Document in `engine/README.md` with short ELI5 analogies (any music analogies subtle).
- Photos:
  - Only CC0, CC BY or public-domain pixels go into a background (`tools/assets/photos.json`,
    credited in `docs/photo_credits.md`).
  - NC, ND and SA photos, and the user's own reference photos, are layout reference only. Keep
    them in the scratchpad and never commit them.
- Names: real places and landmarks keep their real names. Every business name is invented, and
  no real brands appear.
- Working style:
  - Show checkpoints as rendered images, and keep replies to concise bullets.
  - When a tool call is rejected, stop and wait.
- The user pays for tokens. Renders cost CPU time, not tokens: queue them in the background, wait
  for one notification, and review once per batch. Don't poll, and don't re-render what didn't
  change.

## Build, test, render (cloud container; details in the memory file)
- Engine: `cmake -S engine -B <dir> -G Ninja -DCMAKE_BUILD_TYPE=Release && ninja -C <dir>`.
  - Tests: `<dir>/dw_tests`.
  - Screenshots: `xvfb-run -a -s "-screen 0 1920x1080x24" <dir>/damned_waters --capture <out>`
    (97 setups).
- Tools tests: `python3 -m unittest discover -s tools/<citygen|assets|pipeline|telemetry>/tests`.
  Use `set -o pipefail` before piping a check through `tail`.
- City room files: `python3 tools/citygen/build_city.py` regenerates `game/data/rooms` (set
  `DW_ROOMS=<dir>/` to write elsewhere).
- Backgrounds:
  - Render: `blender -b --factory-startup -P tools/blender/render_rooms.py -- --rooms <id>
    --quality preview --res 1280x720 --out pipeline_out/renders`, one Blender at a time.
  - Pack: `python3 tools/pipeline/depth_pack.py --src <dir of symlinks to the rendered rooms>`.
