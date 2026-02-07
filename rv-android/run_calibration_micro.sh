#!/bin/bash
# Calibration Micro Phase - RVAgent (Multimode)
# 50 trials with 10 APKs from calibration set
# Uses best macro params from Phase C as base
# Runs in multimode (hybrid LLM + algorithm) to calibrate all 16 params
#
# Prerequisites:
#   - SGLang server running at 192.168.0.36:30000
#
# Supports resume: if interrupted, run with --resume flag:
#   ./run_calibration_micro.sh --resume
#
# The calibration state is stored in SQLite (optuna_study.db)

set -e

export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"
CALIBRATION_SET="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent-validation/data/calibration_set"
BASELINE_DIR="./results/baseline/cli_experiment_20260202_152204_8c8a2811"
BEST_MACRO="./results/calibration_macro/optimal_params.json"
AGENT_MODE="multimode"
OUTPUT_DIR="./results/calibration_micro"
LOG_FILE="./results/calibration_micro_$(date +%Y%m%d_%H%M%S).log"

# Check for --resume flag
RESUME_FLAG=""
if [[ "$1" == "--resume" ]]; then
    RESUME_FLAG="--resume"
    echo "=== RESUMING Calibration Micro Phase (${AGENT_MODE}) ==="
else
    echo "=== RVAgent Calibration Micro Phase (${AGENT_MODE}) ==="
fi

# Verify SGLang server is reachable
if ! curl -s --max-time 5 http://192.168.0.36:30000/v1/models > /dev/null 2>&1; then
    echo "ERROR: SGLang server not reachable at 192.168.0.36:30000"
    echo "Please start the SGLang server before running multimode calibration."
    exit 1
fi
echo "SGLang: OK (192.168.0.36:30000)"

echo "RVSEC_HOME: $RVSEC_HOME"
echo "Dataset: $CALIBRATION_SET"
echo "APKs: $(ls $CALIBRATION_SET/*.apk | wc -l)"
echo "Best Macro Params: $BEST_MACRO"
echo "Agent Mode: $AGENT_MODE"
echo "Baseline: $BASELINE_DIR"
echo "Output: $OUTPUT_DIR"
echo "SQLite: $OUTPUT_DIR/optuna_study.db"
echo "Log: $LOG_FILE"
echo "========================================"

# Verify best macro params exist
if [[ ! -f "$BEST_MACRO" ]]; then
    echo "ERROR: Best macro params file not found: $BEST_MACRO"
    echo "Please run Phase C (Macro Calibration) first."
    exit 1
fi

poetry run python -m rv_agent_validation calibrate \
  --apks-dir "$CALIBRATION_SET" \
  --phase micro \
  --n-trials 100 \
  --timeout 300 \
  --seed 42 \
  --agent-mode "$AGENT_MODE" \
  --best-macro "$BEST_MACRO" \
  --baseline-dir "$BASELINE_DIR" \
  --output "$OUTPUT_DIR" \
  $RESUME_FLAG \
  2>&1 | tee "$LOG_FILE"
