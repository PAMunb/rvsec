#!/bin/bash
#
# gh60 sweep — 380 APKs static-analysis regression vs pre-gh60 baseline.
#
# Wraps scripts/static_analysis_sweep.py (the actual sweep driver, 1070 LOC,
# already battle-tested through gh51/57) and chains scripts/check_gh60_sweep_delta.py
# (the gh60-specific comparator) after the sweep completes.
#
# What the sweep produces (per-APK):
#   - <out>/<package>/<apk>.json   — raw GATOR analysis output
#   - <out>/_progress/<apk>.json   — status record (used for resume)
#   - <out>/_logs/<apk>.log        — captured stdout/stderr of the worker
#   - <out>/progress.csv           — flat report (status, counts, deltas)
#   - <out>/sweep_runs.jsonl       — one JSON line per invocation
#
# What this wrapper adds:
#   - Sane defaults (cg-algorithm spark, jvm 12g, timeout 900s, 8 workers)
#   - PLANILHA cross-validation if the file is on the expected path
#   - Optional --baseline-dir to trigger the delta comparator at the end
#   - Pidfile-aware kill instructions printed on launch
#
# Usage:
#
#   # Foreground run (interactive, watches stderr live)
#   ./scripts/run_gh60_sweep.sh \\
#       --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs \\
#       --out ./out/gh60_sweep
#
#   # With pre-gh60 baseline for the regression comparator
#   ./scripts/run_gh60_sweep.sh \\
#       --apks-dir /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs \\
#       --out ./out/gh60_sweep \\
#       --baseline-dir ./out/sweep_jca400_pre_gh60
#
#   # Smoke test on 5 APKs (skips delta even if --baseline-dir set)
#   ./scripts/run_gh60_sweep.sh --apks-dir /tmp/5apks --out ./out/smoke --smoke
#
#   # Background — wrap in nohup so the sweep survives SSH disconnect
#   nohup ./scripts/run_gh60_sweep.sh --apks-dir ... --out ./out/gh60_sweep \\
#       > ./out/gh60_sweep/sweep.stdout 2>&1 &
#   # ... then watch:
#   tail -F ./out/gh60_sweep/sweep.stdout
#
# Resume:
#   The underlying sweep is resumable — re-run the SAME command and any
#   APK with an existing complete/skipped status is left alone; partial
#   and failed-timeout entries are retried with the new timeout.
#
# Kill:
#   First SIGINT/SIGTERM kills the descendant tree and writes a final
#   CSV + sweep_runs.jsonl entry, then exits 130. Second signal escalates.
#   The handler in static_analysis_sweep.py uses os._exit(130) to bypass
#   ProcessPoolExecutor.shutdown(wait=True), which would otherwise block
#   the whole sweep timeout.
#
#       kill -INT "$(cat <out>/sweep.pid)"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Defaults — overridable via flags below.
APKS_DIR=""
OUT_DIR=""
BASELINE_DIR=""
TIMEOUT=900
WORKERS=8
JVM_MEMORY="12g"
CG_ALGORITHM="spark"
PLANILHA=""
SMOKE_LIMIT=""
EXTRA_ARGS=()

usage() {
    sed -n '2,/^# Usage:/p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apks-dir)        APKS_DIR="$2"; shift 2 ;;
        --out)             OUT_DIR="$2"; shift 2 ;;
        --baseline-dir)    BASELINE_DIR="$2"; shift 2 ;;
        --timeout)         TIMEOUT="$2"; shift 2 ;;
        --workers)         WORKERS="$2"; shift 2 ;;
        --jvm-memory)      JVM_MEMORY="$2"; shift 2 ;;
        --cg-algorithm)    CG_ALGORITHM="$2"; shift 2 ;;
        --planilha)        PLANILHA="$2"; shift 2 ;;
        --smoke)           SMOKE_LIMIT="--limit 5"; shift ;;
        --limit)           SMOKE_LIMIT="--limit $2"; shift 2 ;;
        --)                shift; EXTRA_ARGS=("$@"); break ;;
        -h|--help)         usage ;;
        *)                 EXTRA_ARGS+=("$1"); shift ;;
    esac
done

if [[ -z "$APKS_DIR" || -z "$OUT_DIR" ]]; then
    echo "ERROR: --apks-dir and --out are required" >&2
    usage
fi

if [[ ! -d "$APKS_DIR" ]]; then
    echo "ERROR: APKs dir not found: $APKS_DIR" >&2
    exit 2
fi

mkdir -p "$OUT_DIR"

# Auto-detect PLANILHA if not given. The canonical path is set by memory
# `reference_jca_400_dataset.md`. Falls back to no cross-validation if absent.
if [[ -z "$PLANILHA" ]]; then
    CANDIDATE="/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/PLANILHA.csv"
    if [[ -f "$CANDIDATE" ]]; then
        PLANILHA="$CANDIDATE"
        echo "[gh60-sweep] auto-detected PLANILHA: $PLANILHA"
    fi
fi

# Sanity — RVSEC_HOME and the deployed jar are mandatory for GATOR.
if [[ -z "${RVSEC_HOME:-}" ]]; then
    echo "ERROR: RVSEC_HOME not set in environment" >&2
    exit 2
fi
JAR_PATH="$PROJECT_ROOT/lib/gator/rvsec-analysis-client.jar"
if [[ ! -f "$JAR_PATH" ]]; then
    echo "ERROR: analysis client jar missing at $JAR_PATH — run mvn install" >&2
    echo "  cd $RVSEC_HOME/rvsec/rvsec-android/rvsec-gator && mvn -pl client -am install -DskipTests=true" >&2
    exit 2
fi

echo "[gh60-sweep] config:"
echo "  apks-dir       = $APKS_DIR"
echo "  out            = $OUT_DIR"
echo "  baseline-dir   = ${BASELINE_DIR:-<not set — delta comparator will be skipped>}"
echo "  timeout        = ${TIMEOUT}s"
echo "  workers        = $WORKERS"
echo "  jvm-memory     = $JVM_MEMORY"
echo "  cg-algorithm   = $CG_ALGORITHM"
echo "  planilha       = ${PLANILHA:-<none>}"
[[ -n "$SMOKE_LIMIT" ]] && echo "  smoke          = $SMOKE_LIMIT"

# Build the sweep command. PLANILHA flag is conditional — passing an
# empty path would trip static_analysis_sweep.py's path-isfile check.
SWEEP_ARGS=(
    --apks-dir "$APKS_DIR"
    --output "$OUT_DIR"
    --timeout "$TIMEOUT"
    --workers "$WORKERS"
    --jvm-memory "$JVM_MEMORY"
    --cg-algorithm "$CG_ALGORITHM"
)
[[ -n "$PLANILHA" ]] && SWEEP_ARGS+=(--planilha "$PLANILHA")
[[ -n "$SMOKE_LIMIT" ]] && read -ra SMOKE_ARR <<<"$SMOKE_LIMIT" && SWEEP_ARGS+=("${SMOKE_ARR[@]}")
SWEEP_ARGS+=("${EXTRA_ARGS[@]}")

echo "[gh60-sweep] kill instructions:"
echo "  PID file will be at $OUT_DIR/sweep.pid"
echo "  kill -INT \"\$(cat $OUT_DIR/sweep.pid)\"  # graceful (writes CSV + descendants)"
echo "  kill -INT \"\$(cat $OUT_DIR/sweep.pid)\"  # second signal escalates to nuclear"
echo ""
echo "[gh60-sweep] launching:"
echo "  uv run python scripts/static_analysis_sweep.py ${SWEEP_ARGS[*]}"
echo ""

uv run python scripts/static_analysis_sweep.py "${SWEEP_ARGS[@]}"
SWEEP_EXIT=$?

if [[ "$SWEEP_EXIT" -ne 0 ]]; then
    echo "[gh60-sweep] static_analysis_sweep.py exited $SWEEP_EXIT" >&2
    exit "$SWEEP_EXIT"
fi

# Chain the delta comparator if a baseline is configured. Smoke runs skip
# this because their 5-APK subset isn't a meaningful regression sample.
if [[ -z "$BASELINE_DIR" ]]; then
    echo "[gh60-sweep] no --baseline-dir set; skipping delta comparator"
    exit 0
fi
if [[ -n "$SMOKE_LIMIT" ]]; then
    echo "[gh60-sweep] smoke run; skipping delta comparator"
    exit 0
fi
if [[ ! -d "$BASELINE_DIR" ]]; then
    echo "[gh60-sweep] baseline dir missing: $BASELINE_DIR — skipping delta" >&2
    exit 0
fi

echo "[gh60-sweep] running delta comparator vs baseline $BASELINE_DIR"
uv run python scripts/check_gh60_sweep_delta.py \
    --baseline-dir "$BASELINE_DIR" \
    --new-dir "$OUT_DIR" \
    --verbose
DELTA_EXIT=$?

echo "[gh60-sweep] delta comparator exit $DELTA_EXIT"
exit "$DELTA_EXIT"
