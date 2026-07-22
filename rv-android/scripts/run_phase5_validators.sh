#!/usr/bin/env bash
# Run all five Phase-5 validators against a paired (ajc, dexlib2) dataset.
#
# Inputs are two rv-experiment results directories produced by running the
# same APK set through each pipeline:
#
#   <ajc_results>/instrumented_apks/*.apk
#   <ajc_results>/<apk>.apk/<apk>__<rep>__<timeout>__<tool>.logcat
#   <ajc_results>/summary.csv
#
#   <dex_results>/instrumented_apks/*.apk
#   <dex_results>/<apk>.apk/<apk>__<rep>__<timeout>__<tool>.logcat
#   <dex_results>/summary.csv
#
# The script then runs Layer 1 (hook recall via baksmali), Layer 2 (VE
# regression), Layer 3 (trace comparison vs oracles), Layer 5 (coverage
# recall), and Layer 3 batch + Layer 4 (Wilcoxon TOST). All reports land
# under <output>/layerN.json. Per-spec metrics CSV under <output>/per_spec.csv.
#
# Each layer's exit code is non-zero on gate failure; the script aggregates
# the gates and exits non-zero if ANY mandatory gate fails. Diagnostic gates
# (Layer 3 with no oracles for the APK set) are surfaced but don't fail the
# run — operators should provide oracles to gate Layer 3 properly.
#
# Usage:
#   run_phase5_validators.sh <ajc_results> <dex_results> <output_dir> [thresholds]

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <ajc_results> <dex_results> <output_dir> [thresholds_yaml]" >&2
  exit 64
fi

AJC_DIR=$(readlink -f "$1")
DEX_DIR=$(readlink -f "$2")
OUT_DIR=$(readlink -f "$3")

# gh56: derive repo + validator paths from the script's own location instead
# of hardcoding the gh52 sibling-clone path. Operators with side-by-side
# clones can override via env vars (RVSEC_REPO_ROOT, RVSEC_VALIDATOR_DIR).
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
RV_ANDROID_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
DEFAULT_REPO_ROOT=$(cd "$RV_ANDROID_ROOT/.." && pwd)
REPO_ROOT=${RVSEC_REPO_ROOT:-$DEFAULT_REPO_ROOT}
VALIDATOR_DIR=${RVSEC_VALIDATOR_DIR:-$REPO_ROOT/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator}
ORACLE_DIR="$VALIDATOR_DIR/oracles"
THRESHOLDS=${4:-$ORACLE_DIR/layer4-thresholds.yaml}
DESCRIPTOR=$(find "$DEX_DIR/monitors" -name "MultiSpec_*MonitorAspect.json" 2>/dev/null | head -1)

# gh56 INV-INS-73: detect cryptoapp in the dex result set. When present, the
# layer3 batch invocation is run with --mandatory so any per-(apk, spec)
# deviation produces Report(passed=false) → exit 1 → GATES_FAILED.
HAS_CRYPTOAPP=false
if find "$DEX_DIR/instrumented_apks" -name 'cryptoapp*.apk' -print -quit 2>/dev/null | grep -q .; then
  HAS_CRYPTOAPP=true
fi

# gh56 INV-INS-71: fail-fast when cryptoapp's instrumentation skipped any
# advice due to unresolved bindings. Replaces the previous manual
# "cat instrument_results.json" check from the task list.
if $HAS_CRYPTOAPP && [[ -f "$DEX_DIR/instrument_results.json" ]] && command -v jq >/dev/null 2>&1; then
  SKIPPED=$(jq -r '.plansSkippedUnresolvedBinding // 0' "$DEX_DIR/instrument_results.json")
  if [[ "$SKIPPED" -gt 0 ]]; then
    echo "[runner] FAIL: plansSkippedUnresolvedBinding=$SKIPPED on cryptoapp run" >&2
    echo "[runner]   gh56 INV-INS-71: bindings were not resolved at instrumentation time." >&2
    exit 1
  fi
fi

mkdir -p "$OUT_DIR"

# Resolve the validator's classpath once. Use mvn dependency:build-classpath
# (cached after first run since the file is timestamp-checked).
CP_FILE="$OUT_DIR/.validator_classpath.txt"
if [[ ! -s "$CP_FILE" || "$VALIDATOR_DIR/pom.xml" -nt "$CP_FILE" ]]; then
  echo "[runner] resolving validator classpath..."
  (cd "$VALIDATOR_DIR" && mvn -q dependency:build-classpath -Dmdep.outputFile="$CP_FILE" >/dev/null)
fi
VALIDATOR_JAR="$VALIDATOR_DIR/target/validator-0.9.2.jar"
CP="$(cat "$CP_FILE"):$VALIDATOR_JAR"
RUN_VALIDATOR=(java -cp "$CP" br.unb.cic.rv.validator.ValidationCli)

# Track gate outcomes for the aggregated exit code.
GATES_PASSED=()
GATES_FAILED=()
GATES_DIAGNOSTIC=()

run_layer() {
  local layer="$1"; shift
  local report="$OUT_DIR/${layer}.json"
  echo "[runner] running $layer..."
  if "${RUN_VALIDATOR[@]}" --report "$report" "$@"; then
    GATES_PASSED+=("$layer")
    echo "[runner]   $layer: PASS  → $report"
  else
    local rc=$?
    if [[ $rc -eq 1 ]]; then
      GATES_FAILED+=("$layer")
      echo "[runner]   $layer: FAIL  → $report"
    else
      GATES_DIAGNOSTIC+=("$layer (exit $rc)")
      echo "[runner]   $layer: ERROR (exit $rc) → $report"
    fi
  fi
}

# --- Layer 1: BaksmaliDiffer (per-spec hook recall) ---
if [[ -d "$AJC_DIR/instrumented_apks" && -d "$DEX_DIR/instrumented_apks" && -n "$DESCRIPTOR" ]]; then
  run_layer layer1 layer1 \
    --ajc "$AJC_DIR/instrumented_apks" \
    --dexlib2 "$DEX_DIR/instrumented_apks" \
    --descriptor "$DESCRIPTOR"
else
  echo "[runner] layer1 SKIP: missing instrumented_apks dirs or descriptor"
  GATES_DIAGNOSTIC+=("layer1 (skipped: missing inputs)")
fi

# --- Layer 2: BootValidator (VE regression analyze mode) ---
# Layer 2 analyze takes top-level results dirs; it walks all .logcat files
# recursively and pairs by parent-dir-name (the rv-experiment layout).
run_layer layer2 layer2 --ajc "$AJC_DIR" --dexlib2 "$DEX_DIR"

# --- Layer 5: CoverageValidator (RVSEC-COV recall) ---
run_layer layer5 layer5 --ajc "$AJC_DIR" --dexlib2 "$DEX_DIR"

# --- Layer 3: TraceComparator (analyze + batch) ---
# Analyze mode pairs logcats per-oracle; we expect <apkSubsetDir>/<oracleName>/{ajc,dexlib2}.logcat.
# That layout is built on demand by the operator (e.g. by symlinking a single rep into the per-oracle slot).
# When no per-oracle dir exists we skip analyze and go straight to batch mode.
TRACE_INPUT="$OUT_DIR/_trace_input"
ORACLE_DIR_AVAIL=true
if ! ls "$ORACLE_DIR"/*-oracle.yaml >/dev/null 2>&1; then
  ORACLE_DIR_AVAIL=false
fi

if $ORACLE_DIR_AVAIL; then
  # Batch mode operates over the rv-experiment results trees directly.
  PER_SPEC_CSV="$OUT_DIR/per_spec.csv"
  # gh56 INV-INS-73: --mandatory promotes Layer 3 from "diagnostic" to a
  # blocking gate when cryptoapp is in scope. Any per-(apk, spec) deviation
  # produces Report(passed=false), which Report.exitCode() maps to exit 1,
  # which run_layer classifies as GATES_FAILED (script then exits 1 at end).
  LAYER3_ARGS=(layer3 --batch
    --oracles "$ORACLE_DIR"
    --ajc-results "$AJC_DIR" --dexlib2-results "$DEX_DIR"
    --output-csv "$PER_SPEC_CSV")
  if $HAS_CRYPTOAPP; then
    LAYER3_ARGS+=(--mandatory)
    echo "[runner] cryptoapp detected — layer3 gate is MANDATORY"
  fi
  run_layer layer3_batch "${LAYER3_ARGS[@]}"
else
  echo "[runner] layer3_batch SKIP: no oracles in $ORACLE_DIR"
  GATES_DIAGNOSTIC+=("layer3_batch (skipped: no oracles)")
  PER_SPEC_CSV=""
fi

# --- Layer 4: BatchValidator (TOST on cov_method + per-spec when CSV present) ---
if [[ -f "$AJC_DIR/summary.csv" && -f "$DEX_DIR/summary.csv" ]]; then
  args=(layer4 --thresholds "$THRESHOLDS" --ajc "$AJC_DIR" --dexlib2 "$DEX_DIR")
  if [[ -n "$PER_SPEC_CSV" && -f "$PER_SPEC_CSV" ]]; then
    args+=(--per-spec-csv "$PER_SPEC_CSV")
  fi
  run_layer layer4 "${args[@]}"
else
  echo "[runner] layer4 SKIP: missing summary.csv on one or both sides"
  GATES_DIAGNOSTIC+=("layer4 (skipped: missing summary.csv)")
fi

echo
echo "=== Phase 5 validator summary ==="
echo "  passed: ${#GATES_PASSED[@]}  ${GATES_PASSED[*]:-<none>}"
echo "  failed: ${#GATES_FAILED[@]}  ${GATES_FAILED[*]:-<none>}"
echo "  diagnostic: ${#GATES_DIAGNOSTIC[@]}  ${GATES_DIAGNOSTIC[*]:-<none>}"
echo "Reports: $OUT_DIR"

if [[ ${#GATES_FAILED[@]} -gt 0 ]]; then
  exit 1
fi
exit 0
