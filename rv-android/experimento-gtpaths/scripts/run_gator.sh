#!/usr/bin/env bash
# Usage: run_gator.sh <outdir> <apk> <heap> [extra rv-static-analysis args...]
# Runs rv-static-analysis analyze on the worktree's jar with the E6 campaign settings
# (jca_android specs, SPARK, cgDelegation=true) and records the wall time.
set -u
WT=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/paths
out=$1; apk=$2; heap=$3; shift 3
name=$(basename "$apk")
mkdir -p "$out/$name.d"
cd "$WT/rv-android" || exit 127
start=$(date +%s.%N)
RV_STRIP_BUILD_TYPE_SUFFIX=true RVSEC_HOME=$WT uv run --offline rv-static-analysis analyze --apk "$apk" --output "$out/$name.d" \
  --rvsec-root "$WT" --mop-dir "$WT/rvsec/rvsec-mop/src/main/resources/jca_android" \
  --jvm-memory "$heap" --cg-algorithm spark --cg-delegation true --analysis-timeout "${GATOR_TIMEOUT:-1800}" --force "$@" \
  > "$out/$name.d/analysis.log" 2>&1
rc=$?
end=$(date +%s.%N)
LC_ALL=C printf '%s\t%s\t%.1f\n' "$name" "$rc" "$(echo "$end - $start" | bc)" >> "$out/walltime.tsv"
