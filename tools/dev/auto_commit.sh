#!/bin/bash
# damned_waters/tools/dev/auto_commit.sh
# Purpose: watch a render queue's log and commit each room as it finishes (commit_room.py), so a
# long re-render lands room by room without anyone awake. Stops at QUEUEDONE or after two failures.
#
#   setsid nohup tools/dev/auto_commit.sh <queue log> "<what the plates show>" > auto_commit.log 2>&1 < /dev/null &
LOG=$1; WHAT=${2:-the second look}
REPO=$(cd "$(dirname "$0")/../.." && pwd)
DONE=$REPO/pipeline_out/queue_logs/committed.txt
mkdir -p "$(dirname "$DONE")"; touch "$DONE"
fails=0
while true; do
  for room in $(grep "^ok " "$LOG" 2>/dev/null | awk '{print $2}'); do
    grep -qx "$room" "$DONE" && continue
    if python3 "$REPO/tools/dev/commit_room.py" "$room" "$WHAT"; then echo "$room" >> "$DONE"; else fails=$((fails + 1)); echo "$room" >> "$DONE.failed"; echo "$room" >> "$DONE"; fi
  done
  [ "$fails" -ge 2 ] && { echo "AUTO STOPPED (failures)"; break; }
  grep -q QUEUEDONE "$LOG" 2>/dev/null && { echo "AUTO DONE"; break; }
  sleep 60
done
