#!/usr/bin/env bash
# Usage: run_fixture_recipe.sh <outdir> [extra gator args...]
# The recipe of modules/rv-static-analysis/tests/resources/cryptoapp.apk.json (scripts/check_signature_file_subset.py,
# baselines/MANIFEST.json): ./gator on apks_examples/cryptoapp.apk with the jca specs, GATOR's default SPARK,
# no cgDelegation, no codePackage, full mode. Uses whatever jar is in lib/gator/ at the time of the run.
set -u
W=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/worktrees-gator/distmax
out=$1; shift
mkdir -p "$out"
cd "$W/rv-android/lib/gator" || exit 127
start=$(date +%s.%N)
./gator a -p "$W/rv-android/apks_examples/cryptoapp.apk" --client-jar "$W/rv-android/lib/gator/rvsec-analysis-client.jar" \
  --out "$out/cryptoapp.apk.json" -client RvsecAnalysisClient \
  -clientParam "mopDir=$W/rvsec/rvsec-mop/src/main/resources/jca" -clientParam fullOutput=true --timeout 300 "$@" \
  > "$out/gator.log" 2>&1
rc=$?
end=$(date +%s.%N)
LC_ALL=C printf '%s\t%s\t%.1f\n' cryptoapp.apk "$rc" "$(echo "$end - $start" | bc)" >> "$out/walltime.tsv"
(cd "$W/rv-android/lib/gator" && sha256sum rvsec-analysis-client.jar rvsec-gator.jar) > "$out/jars.SHA256"
