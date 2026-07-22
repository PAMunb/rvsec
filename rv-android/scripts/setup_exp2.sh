#!/bin/bash
# Setup for experiment 2: aperv:sata_mop (new weights) + rvsmart:mvp.
# Generates batch files for 10 containers from 169 APKs already in data/apks/.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_exp2.sh

set -e

DATA_DIR="data"
APK_DIR="$DATA_DIR/apks"
CONTAINERS=10
APK_LIST="$APK_DIR/available_169.txt"

echo "=== Experiment 2: aperv:sata_mop + rvsmart:mvp ==="
echo "APKs: $(wc -l < "$APK_LIST") (from $APK_LIST)"
echo "Containers: $CONTAINERS"
echo "Tools: aperv:sata_mop, rvsmart:mvp"
echo "Reps: 2"
echo ""

# 1. Create result directories
echo "[1/3] Creating result directories..."
for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "$DATA_DIR/results/exp2_%02d" $i)
    mkdir -p "$dir"
done

# 2. Generate batch files (round-robin split for balanced distribution)
echo "[2/3] Generating batch files..."
rm -f "$APK_DIR"/exp2_batch_*.txt

cd "$APK_DIR"
split -n r/$CONTAINERS -d -a 2 --additional-suffix=.txt \
    "available_169.txt" exp2_batch_
cd ../..

# 3. Verify
echo ""
echo "[3/3] Verification"
echo "  APKs:  $(ls "$APK_DIR"/*.apk 2>/dev/null | wc -l)"
echo "  JSONs: $(ls "$APK_DIR"/*.apk.json 2>/dev/null | wc -l)"
echo ""
echo "  Batches:"
total_apks=0
for b in "$APK_DIR"/exp2_batch_*.txt; do
    n=$(wc -l < "$b")
    total_apks=$((total_apks + n))
    echo "    $(basename $b): $n APKs"
done
echo "  Total: $total_apks APKs across $CONTAINERS batches"
echo ""

tasks=$((total_apks * 2 * 2))
echo "  Expected tasks: $tasks (${total_apks} APKs × 2 tools × 2 reps)"
est_hours=$(echo "scale=1; ($tasks / $CONTAINERS + 1) * 641 / 3600" | bc)
echo "  Estimated wall time: ~${est_hours}h"

echo ""
echo "=== Setup Complete ==="
echo "Next:"
echo "  1. Rebuild Docker image:"
echo "     cd docker/rvandroid && bash build.sh"
echo "  2. Run experiment:"
echo "     docker compose -f docker/docker-compose.exp-aperv-rvsmart.yml up -d"
echo "  3. Monitor:"
echo "     watch -n 60 bash scripts/monitor_comparacao.sh data/results"
