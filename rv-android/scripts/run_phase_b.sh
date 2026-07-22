#!/bin/bash
# Phase B — Baseline (3 tools x 105 APKs x 3 reps = 945 tasks, ~18.4h)
#
# Establishes performance baselines for APE, FastBot, RVAgent:pure_algorithm.
# Key output: BASELINE_MAX_ERRORS (needed by Phases C and D).
#
# Usage:
#   ./scripts/run_phase_b.sh              # First run (resume is automatic)
#   ./scripts/run_phase_b.sh --generate-only  # Inspect compose without launching
#
# Resume is automatic: each container uses RV_EXPERIMENT_NAME, so rv-experiment
# skips completed tasks on re-run. Just re-run the same command.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="modules/rv-agent-validation/data/calibration_dataset_v2"
FILTER_FILE="modules/rv-agent-validation/data/all_valid_apks.txt"
OUTPUT_DIR="./results/baseline_v2"
TOOLS="ape,fastbot,rvagent:pure_algorithm"
N_CONTAINERS=6
TIMEOUT=300
REPETITIONS=3

# Parse flags
EXTRA_FLAGS=""
for arg in "$@"; do
    case "$arg" in
        --generate-only) EXTRA_FLAGS="$EXTRA_FLAGS --generate-only" ;;
    esac
done

echo "=== Phase B — Baseline ==="
echo "Tools:       $TOOLS"
echo "APKs:        $(wc -l < "$FILTER_FILE") (all valid)"
echo "Repetitions: $REPETITIONS"
echo "Containers:  $N_CONTAINERS"
echo "Timeout:     ${TIMEOUT}s per APK"
echo "Output:      $OUTPUT_DIR"
echo "Tasks:       3 tools x 105 APKs x 3 reps = 945"
echo "Est. time:   ~18.4 hours"
echo "=========================="

uv run python scripts/baseline_docker.py \
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
    echo "=== Phase B Complete ==="
    echo "Run verification:"
    echo "  uv run python scripts/verify_phase.py b --results-dir $OUTPUT_DIR"
fi
