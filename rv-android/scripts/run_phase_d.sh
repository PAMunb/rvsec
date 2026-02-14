#!/bin/bash
# Phase D — Micro Calibration (100 trials x 75 APKs, ~160h / 6.7 days)
#
# Fine-tunes 16 additional parameters with macro params fixed from Phase C.
# Uses multimode agent (LLM + algorithm), requires SGLang server.
#
# Usage:
#   ./scripts/run_phase_d.sh              # First run
#   ./scripts/run_phase_d.sh --resume     # Resume after interruption
#
# Prerequisites:
#   - Phase C completed with optimal_params.json
#   - SGLang server running at 192.168.0.36:30000

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

DATA_DIR="modules/rv-agent-validation/data/calibration_dataset_v2"
FILTER_FILE="modules/rv-agent-validation/data/calibration_set_v2.txt"
OUTPUT_DIR="./results/calibration_micro_v2"
BASELINE_DIR="./results/baseline_v2"
BEST_MACRO="./results/calibration_macro_v2/optimal_params.json"
N_TRIALS=100
N_CONTAINERS=6
TIMEOUT=300
AGENT_MODE="multimode"
SEED=42
SGLANG_URL="http://192.168.0.36:30000"

# Parse flags
EXTRA_FLAGS=""
for arg in "$@"; do
    case "$arg" in
        --resume) EXTRA_FLAGS="$EXTRA_FLAGS --resume" ;;
    esac
done

# Pre-flight: macro results must exist
if [[ ! -f "$BEST_MACRO" ]]; then
    echo "ERROR: Macro calibration results not found at $BEST_MACRO"
    echo "Run Phase C first: ./scripts/run_phase_c.sh"
    exit 1
fi

# Pre-flight: baseline must exist
if [[ ! -f "$BASELINE_DIR/summary.csv" ]]; then
    echo "ERROR: Baseline results not found at $BASELINE_DIR/summary.csv"
    echo "Run Phase B first: ./scripts/run_phase_b.sh"
    exit 1
fi

# Pre-flight: SGLang server must be reachable
if ! curl -s --max-time 5 "$SGLANG_URL/v1/models" > /dev/null 2>&1; then
    echo "ERROR: SGLang server not reachable at $SGLANG_URL"
    echo "Start the SGLang server before running multimode calibration."
    exit 1
fi
echo "SGLang: OK ($SGLANG_URL)"

echo "=== Phase D — Micro Calibration ==="
echo "Trials:      $N_TRIALS (batches of $N_CONTAINERS)"
echo "APKs:        $(wc -l < "$FILTER_FILE") calibration set"
echo "Parameters:  16 micro (8 macro fixed from Phase C)"
echo "Agent mode:  $AGENT_MODE"
echo "Macro params: $BEST_MACRO"
echo "Baseline:    $BASELINE_DIR"
echo "Output:      $OUTPUT_DIR"
echo "Est. time:   ~160 hours (6.7 days)"
echo "===================================="

poetry run python scripts/calibration_orchestrator.py \
    --phase micro \
    --n-trials "$N_TRIALS" \
    --n-containers "$N_CONTAINERS" \
    --data-dir "$DATA_DIR" \
    --filter-file "$FILTER_FILE" \
    --output-dir "$OUTPUT_DIR" \
    --timeout "$TIMEOUT" \
    --agent-mode "$AGENT_MODE" \
    --seed "$SEED" \
    --best-macro "$BEST_MACRO" \
    --baseline-dir "$BASELINE_DIR" \
    $EXTRA_FLAGS

echo ""
echo "=== Phase D Complete ==="
echo "Run verification:"
echo "  poetry run python scripts/verify_phase.py d --results-dir $OUTPUT_DIR --macro-dir ./results/calibration_macro_v2"
