#!/bin/bash
# Setup script for RVSmart vs APE vs FastBot comparison experiment.
# Uses stratified sampling (select_dataset.py) to select APKs, then copies
# instrumented APKs + SA JSONs and generates batch files for parallel containers.
#
# Usage: bash scripts/setup_comparacao.sh

set -e

DATASET="modules/rv-agent-validation/data/calibration_dataset_v2"
CSV="modules/rv-agent-validation/data/apks_complete.csv"
DATA_DIR="data"
SELECTION_DIR="$DATA_DIR/selection"
APK_COUNT=100
CONTAINERS=6
APKS_PER_BATCH=17
SEED=42

echo "=== Comparison Experiment Setup ==="
echo "Dataset: $DATASET"
echo "APKs: $APK_COUNT (stratified)"
echo "Containers: $CONTAINERS"
echo "Seed: $SEED"
echo ""

# 1. Create directories
echo "[1/5] Creating directories..."
mkdir -p "$DATA_DIR/apks"
for i in $(seq -w 1 $CONTAINERS); do
    mkdir -p "$DATA_DIR/results/cmp0$i"
done

# 2. Stratified selection
echo "[2/5] Selecting $APK_COUNT APKs (stratified by category + size)..."
uv run python scripts/select_dataset.py \
    --passed-apks "$DATASET/all_valid_apks.txt" \
    --csv "$CSV" \
    --cal-size "$APK_COUNT" \
    --output-dir "$SELECTION_DIR" \
    --seed "$SEED"

# Convert selection to .apk extension (select_dataset outputs without .apk)
APKLIST="$DATA_DIR/comparacao_100apks.txt"
sed 's/$/.apk/' "$SELECTION_DIR/calibration_set_v2.txt" > "$APKLIST"
echo "  Selected $(wc -l < "$APKLIST") APKs"

# 3. Copy APKs and SA JSONs
echo "[3/5] Copying instrumented APKs and static analysis JSONs..."
copied=0
missing=0
while IFS= read -r apk; do
    if [ -f "$DATASET/$apk" ]; then
        cp "$DATASET/$apk" "$DATA_DIR/apks/"
        copied=$((copied + 1))
    else
        echo "  WARNING: APK not found: $apk"
        missing=$((missing + 1))
    fi

    json="${apk}.json"
    if [ -f "$DATASET/$json" ]; then
        cp "$DATASET/$json" "$DATA_DIR/apks/"
    else
        echo "  WARNING: JSON not found: $json"
    fi
done < "$APKLIST"
echo "  Copied $copied APKs ($missing missing)"

# 4. Generate batch files
echo "[4/5] Generating batch files..."
# Clean old batches
rm -f "$DATA_DIR/apks"/batch_*.txt

cd "$DATA_DIR/apks"
split -l $APKS_PER_BATCH -d -a 2 --additional-suffix=.txt "../../$APKLIST" batch_
cd ../..

# 5. Verify
echo ""
echo "[5/5] Verification"
echo "  APKs:  $(ls "$DATA_DIR/apks"/*.apk 2>/dev/null | wc -l)"
echo "  JSONs: $(ls "$DATA_DIR/apks"/*.apk.json 2>/dev/null | wc -l)"
echo ""
echo "  Batches:"
for b in "$DATA_DIR/apks"/batch_*.txt; do
    echo "    $(basename $b): $(wc -l < "$b") APKs"
done
echo ""
echo "  Stratification summary: $SELECTION_DIR/selection_summary.txt"

echo ""
echo "=== Setup Complete ==="
echo "Next: docker compose -f docker/docker-compose.comparacao.yml up -d"
