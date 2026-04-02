#!/bin/bash
# Setup script for Experiment 4: Prompt Variant Comparison
# Creates batch files for 10 containers from the 169-APK dataset.

set -e
cd "$(dirname "$0")/.."

APKS_DIR="data/apks"
AVAILABLE="$APKS_DIR/available_169.txt"
CONTAINERS=10
PREFIX="exp4_batch"

echo "=== Experiment 4: Prompt Variant Comparison ==="
echo "6 variants x 169 APKs x 1 rep x 180s timeout"
echo "10 containers, estimated ~6.7h"
echo ""

if [ ! -f "$AVAILABLE" ]; then
    echo "ERROR: $AVAILABLE not found"
    exit 1
fi

TOTAL=$(wc -l < "$AVAILABLE")
echo "APKs available: $TOTAL"

# Clean old batch files
for i in $(seq 0 $((CONTAINERS - 1))); do
    batch=$(printf "%s/%s_%02d.txt" "$APKS_DIR" "$PREFIX" "$i")
    rm -f "$batch"
done

# Round-robin distribution
line_num=0
while IFS= read -r apk; do
    batch_idx=$((line_num % CONTAINERS))
    batch=$(printf "%s/%s_%02d.txt" "$APKS_DIR" "$PREFIX" "$batch_idx")
    echo "$apk" >> "$batch"
    line_num=$((line_num + 1))
done < "$AVAILABLE"

echo ""
echo "Batch files:"
for i in $(seq 0 $((CONTAINERS - 1))); do
    batch=$(printf "%s/%s_%02d.txt" "$APKS_DIR" "$PREFIX" "$i")
    count=$(wc -l < "$batch")
    echo "  $batch: $count APKs"
done

for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "data/results/exp4_%02d" "$i")
    mkdir -p "$dir"
done

echo ""
echo "Ready: docker compose -f docker/docker-compose.exp4-prompt-variants.yml up -d"
