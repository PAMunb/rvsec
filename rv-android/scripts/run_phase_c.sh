#!/bin/bash
# Phase C — Macro Calibration (80 trials x 75 APKs, ~122h / 5.1 days)
#
# Tunes 8 high-impact parameters using Optuna TPESampler with batch parallelism.
# Requires Phase B baseline results for BASELINE_MAX_ERRORS normalization.
#
# Usage:
#   ./scripts/run_phase_c.sh              # First run
#   ./scripts/run_phase_c.sh --resume     # Resume after interruption
#
# Resume recovers orphaned RUNNING trials from SQLite and continues.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="modules/rv-agent-validation/data/calibration_dataset_v2"
FILTER_FILE="modules/rv-agent-validation/data/calibration_set_v2.txt"
OUTPUT_DIR="./results/calibration_macro_v2"
BASELINE_DIR="./results/baseline_v2"
N_TRIALS=80
N_CONTAINERS=6
TIMEOUT=300
AGENT_MODE="pure_algorithm"
SEED=42

# Parse flags
EXTRA_FLAGS=""
for arg in "$@"; do
    case "$arg" in
        --resume) EXTRA_FLAGS="$EXTRA_FLAGS --resume" ;;
    esac
done

# Pre-flight: baseline must exist
if [[ ! -f "$BASELINE_DIR/summary.csv" ]]; then
    echo "ERROR: Baseline results not found at $BASELINE_DIR/summary.csv"
    echo "Run Phase B first: ./scripts/run_phase_b.sh"
    exit 1
fi

echo "=== Phase C — Macro Calibration ==="
echo "Trials:      $N_TRIALS (batches of $N_CONTAINERS)"
echo "APKs:        $(wc -l < "$FILTER_FILE") calibration set"
echo "Parameters:  8 macro (scorer weights + exploration)"
echo "Agent mode:  $AGENT_MODE"
echo "Baseline:    $BASELINE_DIR"
echo "Output:      $OUTPUT_DIR"
echo "Est. time:   ~122 hours (5.1 days)"
echo "===================================="

poetry run python scripts/calibration_orchestrator.py \
    --phase macro \
    --n-trials "$N_TRIALS" \
    --n-containers "$N_CONTAINERS" \
    --data-dir "$DATA_DIR" \
    --filter-file "$FILTER_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --timeout "$TIMEOUT" \
    --agent-mode "$AGENT_MODE" \
    --seed "$SEED" \
    --baseline-dir "$BASELINE_DIR" \
    $EXTRA_FLAGS

echo ""
echo "=== Phase C Complete ==="
echo "Run verification:"
echo "  poetry run python scripts/verify_phase.py c --results-dir $OUTPUT_DIR"
