#!/bin/bash
# Setup for experiment 4: aperv:sata_mop (calibrated) + ape + fastbot.
# 169 APKs, 600s timeout, 3 reps, 10 containers, JCA specs.
#
# Tests the calibrated APE-RV parameters from MACRO calibration (trial #101)
# against the APE original and FastBot baselines.
#
# Usage:
#   cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
#   bash scripts/setup_exp4.sh

set -e

DATA_DIR="data"
APK_DIR="$DATA_DIR/apks"
CONTAINERS=10
APK_LIST="$APK_DIR/available_169.txt"
PREFIX="exp4"

echo "=== Experiment 4: aperv:sata_mop (calibrated) + ape + fastbot ==="
echo "APKs: $(wc -l < "$APK_LIST") (from $APK_LIST)"
echo "Containers: $CONTAINERS"
echo "Tools: aperv:sata_mop@calibrated, ape, fastbot"
echo "Reps: 3"
echo ""

# 1. Create result directories
echo "[1/3] Creating result directories..."
for i in $(seq 0 $((CONTAINERS - 1))); do
    dir=$(printf "$DATA_DIR/results/${PREFIX}_%02d" $i)
    mkdir -p "$dir"
done

# 2. Generate batch files (round-robin split for balanced distribution)
echo "[2/3] Generating batch files..."
rm -f "$APK_DIR"/${PREFIX}_batch_*.txt

cd "$APK_DIR"
split -n r/$CONTAINERS -d -a 2 --additional-suffix=.txt \
    "available_169.txt" ${PREFIX}_batch_
cd ../..

# 3. Verify
echo ""
echo "[3/3] Verification"
echo "  APKs:  $(ls "$APK_DIR"/*.apk 2>/dev/null | wc -l)"
echo "  JSONs: $(ls "$APK_DIR"/*.apk.json 2>/dev/null | wc -l)"
echo ""
echo "  Batches:"
total_apks=0
for b in "$APK_DIR"/${PREFIX}_batch_*.txt; do
    n=$(wc -l < "$b")
    total_apks=$((total_apks + n))
    echo "    $(basename $b): $n APKs"
done
echo "  Total: $total_apks APKs across $CONTAINERS batches"
echo ""

tools=3
reps=3
tasks=$((total_apks * tools * reps))
echo "  Expected tasks: $tasks (${total_apks} APKs × $tools tools × $reps reps)"
est_hours=$(echo "scale=1; ($tasks / $CONTAINERS + 1) * 680 / 3600" | bc)
echo "  Estimated wall time: ~${est_hours}h"

echo ""
echo "=== Setup Complete ==="
echo "Next:"
echo "  1. Build APE JAR (if needed):"
echo "     cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape"
echo "     mvn clean install -Drvsec_home=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"
echo "  2. Copy JAR + rebuild Docker image:"
echo "     cp modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar docker/rvandroid/"
echo "     cd docker/rvandroid && bash build.sh"
echo "  3. Run experiment:"
echo "     docker compose -f docker/docker-compose.exp4-calibrated.yml up -d"
echo "  4. Monitor:"
echo "     watch -n 60 bash scripts/monitor_comparacao.sh data/results exp4"
