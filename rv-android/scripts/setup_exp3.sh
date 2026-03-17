#!/bin/bash
# Setup for experiment 3: APE-RV LLM baseline.
# Generates batch files for 10 containers from 169 APKs already in data/apks/.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_exp3.sh

set -e

DATA_DIR="data"
APK_DIR="$DATA_DIR/apks"
CONTAINERS=8
APK_LIST="$APK_DIR/available_169.txt"

echo "=== Experiment 3: APE-RV LLM Baseline ==="
echo "APKs: $(wc -l < "$APK_LIST") (from $APK_LIST)"
echo "Containers: $CONTAINERS"
echo "Tools: aperv:sata_mop_llm"
echo "Reps: 3"
echo ""

# 1. Create result directories
echo "[1/3] Creating result directories..."
for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "$DATA_DIR/results/exp3_%02d" $i)
    mkdir -p "$dir"
done

# 2. Generate batch files (round-robin split for balanced distribution)
echo "[2/3] Generating batch files..."
rm -f "$APK_DIR"/exp3_batch_*.txt

cd "$APK_DIR"
split -n r/$CONTAINERS -d -a 2 --additional-suffix=.txt \
    "available_169.txt" exp3_batch_
cd ../..

# 3. Verify
echo ""
echo "[3/3] Verification"
echo "  APKs:  $(ls "$APK_DIR"/*.apk 2>/dev/null | wc -l)"
echo "  JSONs: $(ls "$APK_DIR"/*.apk.json 2>/dev/null | wc -l)"
echo ""
echo "  Batches:"
total_apks=0
for b in "$APK_DIR"/exp3_batch_*.txt; do
    n=$(wc -l < "$b")
    total_apks=$((total_apks + n))
    echo "    $(basename $b): $n APKs"
done
echo "  Total: $total_apks APKs across $CONTAINERS batches"
echo ""

tasks=$((total_apks * 1 * 3))
echo "  Expected tasks: $tasks (${total_apks} APKs × 1 tool × 3 reps)"
est_hours=$(echo "scale=1; ($tasks / $CONTAINERS + 1) * 680 / 3600" | bc)
echo "  Estimated wall time: ~${est_hours}h (com overhead LLM)"

echo ""
echo "=== Setup Complete ==="
echo "Next:"
echo "  1. Rebuild Docker image:"
echo "     cd docker/rvandroid && bash build.sh"
echo "  2. Run experiment:"
echo "     docker compose -f docker/docker-compose.exp3-aperv-llm.yml up -d"
echo "  3. Monitor:"
echo "     watch -n 60 bash scripts/monitor_exp3.sh"
