#!/bin/bash
# damned_waters/tools/dev/render_queue.sh
# Purpose: render a list of rooms one after another in the cloud container, packing each as it
# finishes, and pick up where it stopped when the container restarts (a restart kills the render in
# flight). Lives in the repo because the scratchpad does not survive a replaced container.
#
#   setsid nohup tools/dev/render_queue.sh <specs dir> <queue file> [extra render_rooms args] > queue.log 2>&1 < /dev/null &
#
# The queue file holds one room id per line; a room is taken off the line only when it is packed.
# Shots that already have both plates in pipeline_out/renders/<room>/ are not rendered again.
# For each finished room the log gets "ok <room>" (or "FAILED <room>"); "QUEUEDONE" at the end.
#
# ELI5: a print shop's job tray. Jobs wait in a pile; each is printed, bound and ticked off; if the
# power fails mid-job, the half-printed job is still on top of the pile when the lights come back.
SPECS=$1; QUEUE=$2; shift 2
REPO=$(cd "$(dirname "$0")/../.." && pwd)
BLENDER=${BLENDER:-/opt/blender/blender-4.5.9-linux-x64/blender}
RES=${RES:-2048x1152}
OUT=$REPO/pipeline_out/renders
LOGS=$REPO/pipeline_out/queue_logs
mkdir -p "$OUT" "$LOGS"
cd "$REPO" || exit 1
while true; do
  room=$(head -1 "$QUEUE"); [ -z "$room" ] && break
  # the shots still to do: every shot in the spec without both of its plates
  shots=$(python3 - "$SPECS/$room.json" "$OUT/$room" <<'PY'
import json, sys
from pathlib import Path
spec, out = json.load(open(sys.argv[1])), Path(sys.argv[2])
print(",".join(s["id"] for s in spec["shots"] if not ((out / f"{s['id']}_color.png").exists() and (out / f"{s['id']}_depth16.png").exists())))
PY
)
  if [ -n "$shots" ]; then
    while [ "$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)" -lt 8 ]; do sleep 15; done
    echo "start $room ($shots) $(date +%T)"
    "$BLENDER" -b --factory-startup -P tools/blender/render_rooms.py -- --specs "$SPECS" --rooms "$room" --shots "$shots" \
      --quality preview --res "$RES" --out "$OUT" "$@" > "$LOGS/$room.log" 2>&1
  fi
  # packed only if every shot is there
  left=$(python3 - "$SPECS/$room.json" "$OUT/$room" <<'PY'
import json, sys
from pathlib import Path
spec, out = json.load(open(sys.argv[1])), Path(sys.argv[2])
print(sum(not ((out / f"{s['id']}_color.png").exists() and (out / f"{s['id']}_depth16.png").exists()) for s in spec["shots"]))
PY
)
  if [ "$left" = "0" ]; then
    link=$(mktemp -d); ln -s "$OUT/$room" "$link/$room"
    python3 tools/pipeline/depth_pack.py --src "$link" > "$LOGS/$room.pack.log" 2>&1 && cp "$SPECS/$room.json" game/data/rooms/ && echo "ok $room $(date +%T)" || echo "FAILED $room (pack) $(date +%T)"
    rm -rf "$link"
  else
    echo "FAILED $room ($left shots missing) $(date +%T)"
  fi
  sed -i 1d "$QUEUE"
done
echo QUEUEDONE
