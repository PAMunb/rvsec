#!/bin/bash
# Setup for APE-RV vs APE comparison experiment.
# Generates batch files for 10 containers from 169 APKs already in data/apks/.
# Does NOT copy APKs — they must already be present (reused from exp 2026-03-11).
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_aperv_comparacao.sh
#
# See: docs/20260313_aperv_comparacao.md

set -e

DATA_DIR="data"
APK_DIR="$DATA_DIR/apks"
RESULTS_DIR="$DATA_DIR/results"
CONTAINERS=10
TOOLS=3    # ape, aperv:sata, aperv:sata_mop
REPS=2
APK_LIST="$APK_DIR/available_169.txt"

echo "=== APE-RV Comparison Experiment Setup ==="
echo ""

# Validate APK list exists
if [ ! -f "$APK_LIST" ]; then
    echo "ERROR: APK list not found: $APK_LIST"
    exit 1
fi

APK_COUNT=$(wc -l < "$APK_LIST")
echo "APKs:       $APK_COUNT (from $APK_LIST)"
echo "Containers: $CONTAINERS"
echo "Tools:      ape, aperv:sata, aperv:sata_mop ($TOOLS)"
echo "Reps:       $REPS"
echo "Tasks:      $((APK_COUNT * TOOLS * REPS))"
echo ""

# 1. Create result directories
echo "[1/4] Creating result directories..."
for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "$RESULTS_DIR/aperv_%02d" $i)
    mkdir -p "$dir"
    echo "  $dir"
done

# 2. Generate batch files (round-robin split for balanced distribution)
echo ""
echo "[2/4] Generating batch files..."
rm -f "$APK_DIR"/aperv_batch_*.txt

cd "$APK_DIR"
split -n r/$CONTAINERS -d -a 2 --additional-suffix=.txt \
    "available_169.txt" aperv_batch_
cd ../..

# 3. Verify APKs and JSONs
echo ""
echo "[3/4] Verifying data..."
apk_count=$(ls "$APK_DIR"/*.apk 2>/dev/null | wc -l)
json_count=$(ls "$APK_DIR"/*.apk.json 2>/dev/null | wc -l)

echo "  APKs:  $apk_count"
echo "  JSONs: $json_count"

if [ "$apk_count" -ne "$APK_COUNT" ]; then
    echo "  WARNING: Expected $APK_COUNT APKs, found $apk_count"
fi
if [ "$json_count" -ne "$APK_COUNT" ]; then
    echo "  WARNING: Expected $APK_COUNT JSONs, found $json_count"
fi

# Check that every APK in the list has a corresponding .apk file
missing=0
while IFS= read -r apk; do
    if [ ! -f "$APK_DIR/$apk" ]; then
        echo "  MISSING APK: $apk"
        missing=$((missing + 1))
    fi
done < "$APK_LIST"
if [ "$missing" -gt 0 ]; then
    echo "  ERROR: $missing APKs missing from $APK_DIR"
    exit 1
fi

# 4. Display batch summary
echo ""
echo "[4/4] Batch summary"
total_apks=0
for b in "$APK_DIR"/aperv_batch_*.txt; do
    n=$(wc -l < "$b")
    tasks=$((n * TOOLS * REPS))
    total_apks=$((total_apks + n))
    echo "  $(basename $b): $n APKs → $tasks tasks"
done
echo ""
echo "  Total: $total_apks APKs, $((total_apks * TOOLS * REPS)) tasks across $CONTAINERS containers"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
echo "  docker compose -f docker/docker-compose.aperv-comparacao.yml up -d"
echo "  watch -n 60 bash scripts/monitor_aperv_comparacao.sh"
