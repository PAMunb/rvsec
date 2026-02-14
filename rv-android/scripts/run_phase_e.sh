#!/bin/bash
# Phase E — Validation (3 tools x 30 holdout APKs x 3 reps = 270 tasks, ~5.6h)
#
# Validates calibrated parameters on the holdout set (never seen during calibration).
# Runs same tools as baseline for direct statistical comparison.
#
# Usage:
#   ./scripts/run_phase_e.sh              # First run
#   ./scripts/run_phase_e.sh --resume     # Resume after interruption
#   ./scripts/run_phase_e.sh --generate-only  # Inspect compose
#
# Prerequisites:
#   - Phase D completed with param_string.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="modules/rv-agent-validation/data/calibration_dataset_v2"
FILTER_FILE="modules/rv-agent-validation/data/holdout_set_v2.txt"
OUTPUT_DIR="./results/validation_v2"
PARAM_STRING_FILE="./results/calibration_micro_v2/param_string.txt"
N_CONTAINERS=6
TIMEOUT=300
REPETITIONS=3

# Parse flags
EXTRA_FLAGS=""
for arg in "$@"; do
    case "$arg" in
        --resume)        EXTRA_FLAGS="$EXTRA_FLAGS --resume" ;;
        --generate-only) EXTRA_FLAGS="$EXTRA_FLAGS --generate-only" ;;
    esac
done

# Pre-flight: calibrated params must exist
if [[ ! -f "$PARAM_STRING_FILE" ]]; then
    echo "ERROR: Calibrated parameters not found at $PARAM_STRING_FILE"
    echo "Run Phase D first: ./scripts/run_phase_d.sh"
    exit 1
fi

PARAMS=$(cat "$PARAM_STRING_FILE")
TOOLS="ape,fastbot,rvagent:multimode@${PARAMS}"

echo "=== Phase E — Validation ==="
echo "Tools:       ape, fastbot, rvagent:multimode (calibrated)"
echo "APKs:        $(wc -l < "$FILTER_FILE") holdout set"
echo "Repetitions: $REPETITIONS"
echo "Containers:  $N_CONTAINERS"
echo "Output:      $OUTPUT_DIR"
echo "Tasks:       3 tools x 30 APKs x 3 reps = 270"
echo "Est. time:   ~5.6 hours"
echo "============================="

poetry run python scripts/baseline_docker.py \
    --tools "$TOOLS" \
    --data-dir "$DATA_DIR" \
    --filter-file "$FILTER_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --n-containers "$N_CONTAINERS" \
    --timeout "$TIMEOUT" \
    --repetitions "$REPETITIONS" \
    $EXTRA_FLAGS

if [[ "$EXTRA_FLAGS" != *"--generate-only"* ]]; then
    echo ""
    echo "=== Phase E Complete ==="
    echo "Run verification:"
    echo "  poetry run python scripts/verify_phase.py e --results-dir $OUTPUT_DIR --baseline-dir ./results/baseline_v2"
fi
