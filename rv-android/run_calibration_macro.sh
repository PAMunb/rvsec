#!/bin/bash
# Calibration Macro Phase - RVAgent
# 50 trials with 10 APKs from calibration set
#
# Supports resume: if interrupted, run with --resume flag:
#   ./run_calibration_macro.sh --resume
#
# The calibration state is stored in SQLite (optuna_study.db)

set -e

export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"
CALIBRATION_SET="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent-validation/data/calibration_set"
BASELINE_DIR="./results/baseline/cli_experiment_20260202_152204_8c8a2811"
OUTPUT_DIR="./results/calibration_macro"
LOG_FILE="./results/calibration_macro_$(date +%Y%m%d_%H%M%S).log"

# Check for --resume flag
RESUME_FLAG=""
if [[ "$1" == "--resume" ]]; then
    RESUME_FLAG="--resume"
    echo "=== RESUMING Calibration Macro Phase ==="
else
    echo "=== RVAgent Calibration Macro Phase ==="
fi

echo "RVSEC_HOME: $RVSEC_HOME"
echo "Dataset: $CALIBRATION_SET"
echo "APKs: $(ls $CALIBRATION_SET/*.apk | wc -l)"
echo "Baseline: $BASELINE_DIR"
echo "Output: $OUTPUT_DIR"
echo "SQLite: $OUTPUT_DIR/optuna_study.db"
echo "Log: $LOG_FILE"
echo "========================================"

poetry run python -m rv_agent_validation calibrate \
  --apks-dir "$CALIBRATION_SET" \
  --phase macro \
  --n-trials 50 \
  --timeout 300 \
  --seed 42 \
  --baseline-dir "$BASELINE_DIR" \
  --output "$OUTPUT_DIR" \
  $RESUME_FLAG \
  2>&1 | tee "$LOG_FILE"
