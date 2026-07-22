#!/bin/bash
# Smoke test for APE-RV calibration infrastructure.
#
# Validates end-to-end: Optuna DB, Docker containers, scoring, param injection.
# Uses 5 APKs × 120s timeout × 5 trials (1 round) ≈ 30 minutes.
#
# After completion, test --resume by killing and restarting:
#   1. Run this script
#   2. Wait for completion (~30min)
#   3. Verify results in results/aperv_smoke_test/
#   4. Run again with --resume to test crash recovery
#
# Usage:
#   bash scripts/smoke_test_calibration.sh
#   bash scripts/smoke_test_calibration.sh --resume   # test resume

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OUTPUT_DIR="$REPO_ROOT/results/aperv_smoke_test"
DATA_DIR="$REPO_ROOT/data/apks"
FILTER_FILE="$REPO_ROOT/data/apks/aperv_smoke_5.txt"

RESUME_FLAG=""
if [[ "$1" == "--resume" ]]; then
    RESUME_FLAG="--resume"
    echo "=== SMOKE TEST (resume mode) ==="
else
    echo "=== SMOKE TEST (fresh run) ==="
    # Clean previous smoke test results
    if [ -d "$OUTPUT_DIR" ]; then
        echo "Removing previous smoke test results..."
        rm -rf "$OUTPUT_DIR"
    fi
fi

echo "  APKs: 5 (aperv_smoke_5.txt)"
echo "  Timeout: 120s per APK"
echo "  Trials: 5 (1 round of 5 containers)"
echo "  Output: $OUTPUT_DIR"
echo "  Estimated time: ~30 minutes"
echo ""

cd "$REPO_ROOT"

uv run python scripts/calibration_orchestrator.py \
    --tool aperv:sata_mop \
    --phase macro \
    --n-trials 5 \
    --n-containers 5 \
    --data-dir "$DATA_DIR" \
    --filter-file "$FILTER_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --timeout 120 \
    --cpus 4 --memory 10g \
    --seed 42 \
    --convergence-rounds 0 \
    $RESUME_FLAG

echo ""
echo "=== SMOKE TEST COMPLETE ==="
echo ""
echo "Verify results:"
echo "  ls $OUTPUT_DIR/"
echo "  cat $OUTPUT_DIR/optimal_params.json"
echo "  cat $OUTPUT_DIR/orchestrator.log"
echo ""
echo "To test resume, run:"
echo "  bash scripts/smoke_test_calibration.sh --resume"
