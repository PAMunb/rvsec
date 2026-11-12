#!/usr/bin/env bash
# Task 5.6: rv-static-analysis analyze WITHOUT --force on a stored full document of cryptoapp (no distMax member).
# Usage: run_reuse.sh <label> [extra args]; records the log, the wall time and the document's sha256 before/after.
label=$1; shift
d=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/reuse/cryptoapp.apk.d; f=$d/cryptoapp.apk.json
before=$(sha256sum "$f" | cut -c1-16)
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android || exit 127
start=$(date +%s.%N)
RV_STRIP_BUILD_TYPE_SUFFIX=true RVSEC_HOME=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax uv run --offline rv-static-analysis analyze --apk /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/apks_examples/cryptoapp.apk --output "$d" \
  --rvsec-root "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax" --mop-dir "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rvsec/rvsec-mop/src/main/resources/jca_android" \
  --jvm-memory 12g --cg-algorithm spark --cg-delegation true --analysis-timeout 1800 --full-output "$@" > /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax/rv-android/experimento-gtdistmax/new/reuse/$label.log 2>&1
rc=$?
end=$(date +%s.%N)
after=$(sha256sum "$f" | cut -c1-16)
LC_ALL=C printf '%s args=[%s] exit=%s wall=%.1fs sha256 before=%s after=%s distMax_member=%s\n' "$label" "$*" $rc "$(echo "$end - $start" | bc)" $before $after \
  "$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('distMax'))" "$f")"
