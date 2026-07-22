#!/bin/bash
# Run static analysis in parallel across preprocessed container outputs.
# Each instance processes only the APKs that were successfully instrumented,
# using the original APKs as input (GATOR needs unmodified DEX bytecode).
# The SA module skips APKs that already have .json output (file-level cache).
#
# Usage:
#   ./scripts/sa_parallel.sh <preprocess_dir> <original_apks_dir> [timeout_seconds]
#
# Example:
#   ./scripts/sa_parallel.sh /data/gh50_preprocess_jca /data/APKs 3600

set -e

PREPROCESS_DIR="${1:?Usage: $0 <preprocess_dir> <original_apks_dir> [timeout_seconds]}"
ORIGINAL_APKS_DIR="${2:?Usage: $0 <preprocess_dir> <original_apks_dir> [timeout_seconds]}"
SA_TIMEOUT="${3:-3600}"
JVM_MEMORY="${4:-16g}"

# Count container dirs
N_CONTAINERS=$(ls -d "$PREPROCESS_DIR"/preprocess_*/instrumented_apks 2>/dev/null | wc -l)
if [ "$N_CONTAINERS" -eq 0 ]; then
    echo "ERROR: no preprocess_*/instrumented_apks dirs found in $PREPROCESS_DIR"
    exit 1
fi

echo "=== Static Analysis Parallel Runner ==="
echo "Preprocess dir: $PREPROCESS_DIR"
echo "Original APKs:  $ORIGINAL_APKS_DIR"
echo "Timeout:        ${SA_TIMEOUT}s"
echo "JVM memory:     $JVM_MEMORY"
echo "Containers:     $N_CONTAINERS"
echo ""

PIDS=()

for container_dir in "$PREPROCESS_DIR"/preprocess_*/; do
    container_name=$(basename "$container_dir")
    instrumented_dir="$container_dir/instrumented_apks"

    if [ ! -d "$instrumented_dir" ]; then
        echo "SKIP $container_name: no instrumented_apks/"
        continue
    fi

    # Count instrumented APKs and existing SA results
    n_apks=$(ls "$instrumented_dir"/*.apk 2>/dev/null | wc -l)
    n_jsons=$(ls "$instrumented_dir"/*.apk.json 2>/dev/null | wc -l)

    if [ "$n_apks" -eq 0 ]; then
        echo "SKIP $container_name: no APKs"
        continue
    fi

    # Create temp dir with symlinks to relevant original APKs only
    tmp_apks="$container_dir/sa_input"
    rm -rf "$tmp_apks"
    mkdir -p "$tmp_apks"

    linked=0
    for apk in "$instrumented_dir"/*.apk; do
        apk_name=$(basename "$apk")
        original="$ORIGINAL_APKS_DIR/$apk_name"
        if [ -f "$original" ]; then
            ln -s "$original" "$tmp_apks/$apk_name"
            linked=$((linked + 1))
        fi
    done

    echo "START $container_name: $linked APKs ($n_jsons already have SA data)"

    # Run SA batch — output goes to instrumented_dir (alongside .apk files)
    # The SA module writes {output}/{app.name}.json and skips if file exists
    uv run python -m rv_static_analysis batch \
        --apks-dir "$tmp_apks" \
        --output "$instrumented_dir" \
        --analysis-timeout "$SA_TIMEOUT" \
        --jvm-memory "$JVM_MEMORY" \
        --continue-on-error \
        --verbose \
        > "$container_dir/sa_log.txt" 2>&1 &

    PIDS+=($!)
done

echo ""
echo "All $N_CONTAINERS instances launched. Waiting..."
echo ""

# Wait for all and report results
failed=0
for i in "${!PIDS[@]}"; do
    if wait "${PIDS[$i]}"; then
        echo "DONE preprocess_$i (exit 0)"
    else
        echo "FAIL preprocess_$i (exit $?)"
        failed=$((failed + 1))
    fi
done

echo ""
echo "=== Results ==="
total_apks=0
total_jsons=0
for container_dir in "$PREPROCESS_DIR"/preprocess_*/; do
    container_name=$(basename "$container_dir")
    instrumented_dir="$container_dir/instrumented_apks"
    n_apks=$(ls "$instrumented_dir"/*.apk 2>/dev/null | wc -l)
    n_jsons=$(ls "$instrumented_dir"/*.apk.json 2>/dev/null | wc -l)
    total_apks=$((total_apks + n_apks))
    total_jsons=$((total_jsons + n_jsons))
    echo "  $container_name: $n_jsons/$n_apks SA data"
done
echo ""
echo "Total: $total_jsons/$total_apks APKs with SA data"
echo "Failed instances: $failed"
