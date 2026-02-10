#!/bin/bash
# Baseline Phase B - APE, FastBot, RVAgent (105 APKs, 3 reps)
# 3 tools x 105 APKs x 3 reps = 945 tasks, 6 emulators in parallel
#
# Supports resume: if interrupted, rerun the same command:
#   ./run_baseline_v2.sh --resume
#
# Dry run (show what would resume without executing):
#   ./run_baseline_v2.sh --resume --dry-run
#
# Resume works at two levels:
#   1. parallel_run.py: skips fully-completed APKs from filter files
#   2. platform.py: skips already-completed tasks within partial APKs

set -e

export RVSEC_HOME="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec"
DATASET="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent-validation/data/calibration_dataset_v2"
OUTPUT_BASE="./results/baseline_v2"
LOG_FILE="${OUTPUT_BASE}/baseline_v2_$(date +%Y%m%d_%H%M%S).log"

# Parse flags
EXTRA_FLAGS=""
for arg in "$@"; do
    case "$arg" in
        --resume)   EXTRA_FLAGS="$EXTRA_FLAGS --resume" ;;
        --dry-run)  EXTRA_FLAGS="$EXTRA_FLAGS --dry-run" ;;
    esac
done

if [[ "$EXTRA_FLAGS" == *"--resume"* ]]; then
    echo "=== RESUMING Baseline Phase B ==="
else
    echo "=== Baseline Phase B ==="
fi

echo "RVSEC_HOME: $RVSEC_HOME"
echo "Dataset: $DATASET"
echo "APKs: $(ls "$DATASET"/*.apk 2>/dev/null | wc -l)"
echo "Output: $OUTPUT_BASE"
echo "Log: $LOG_FILE"
echo "Emulators: 6"
echo "Tasks: 3 tools x 105 APKs x 3 reps = 945"
echo "Estimated time: ~18h (first run), ~14h (resume from 25%)"
echo "========================================"

mkdir -p "$OUTPUT_BASE"

nohup poetry run python scripts/parallel_run.py \
  --tools ape,fastbot,rvagent:pure_algorithm \
  --apks-dir "$DATASET" \
  --n-emulators 6 \
  --timeout 300 \
  --repetitions 3 \
  --output-base "$OUTPUT_BASE" \
  --skip-preprocessing \
  $EXTRA_FLAGS \
  > "$LOG_FILE" 2>&1 &

PID=$!
echo ""
echo "Launched in background: PID $PID"
echo "Log: $LOG_FILE"
echo ""
echo "Monitor with:"
echo "  tail -f $LOG_FILE"
echo "  ps aux | grep $PID"
