#!/usr/bin/env bash
# experimento-stampcb, step 2: gather the treatment APKs instrumented in step 1 into
# apks_treatment/, each beside the corpus .apk.json of the same app (the static model is
# the same; only the stamp helper changed), then check the DEX against the corpus.
set -euo pipefail
X="$(cd "$(dirname "$0")/.." && pwd)"
CORPUS=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-study03-replication-package/data/raw/e6-corpus
mkdir -p "$X/apks_treatment"
while read -r apk; do
  src=$(ls "$X"/results/instrument/*/instrumented_apks/"$apk" 2>/dev/null | head -1 || true)
  if [ -z "$src" ]; then echo "missing instrumented $apk" >&2; exit 1; fi
  cp "$src" "$X/apks_treatment/$apk"
  cp "$CORPUS/$apk.json" "$X/apks_treatment/$apk.json"
done < "$X/apks.txt"
python3 -I "$X/scripts/check_dex.py" "$CORPUS" "$X/apks_treatment" $(cat "$X/apks.txt")
