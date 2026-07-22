#!/bin/bash
# generate_filters_exp_ape_gh59.sh
#
# Lê out/validate_instrument_jca190/install_report.csv (resultado da validação
# install+launch+logcat), filtra APKs com status == PASS, e particiona em 8
# batches round-robin pra docker-compose.exp-ape-gh59.yml.

set -euo pipefail

PROJECT_ROOT=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
CSV="$PROJECT_ROOT/out/validate_instrument_jca190/install_report.csv"
OUTDIR="$PROJECT_ROOT/data/exp_ape_gh59_filters"

echo "[$(date)] === generate filters exp_ape_gh59 ==="

if [ ! -f "$CSV" ]; then
  echo "ERROR: $CSV não existe — rode validate_instrument_jca190.py primeiro"
  exit 1
fi

CSV_ROWS=$(($(wc -l < "$CSV") - 1))
echo "CSV: $CSV_ROWS APKs validados"

mkdir -p "$OUTDIR"

# Filter PASS, sort por nome p/ reprodutibilidade
awk -F, 'NR>1 && $12=="PASS" {print $1}' "$CSV" | sort -u > "$OUTDIR/pass_apks.txt"
N_PASS=$(wc -l < "$OUTDIR/pass_apks.txt")
echo "PASS: $N_PASS APKs"

# Status counts
echo "--- breakdown ---"
awk -F, 'NR>1 {c[$12]++} END {for (s in c) printf "  %-15s %d\n", s, c[s]}' "$CSV" | sort

# Round-robin em 8 batches
python3 << EOF
from pathlib import Path
apks = Path("$OUTDIR/pass_apks.txt").read_text().strip().splitlines()
N = 8
batches = [[] for _ in range(N)]
for i, apk in enumerate(apks):
    batches[i % N].append(apk)
for i, b in enumerate(batches):
    Path(f"$OUTDIR/batch_{i:02d}.txt").write_text("\n".join(b) + "\n")
    print(f"batch_{i:02d}.txt: {len(b)} APKs")
print(f"total: {sum(len(b) for b in batches)}")
EOF

echo "[$(date)] done. Filtros em $OUTDIR/"
