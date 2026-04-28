#!/bin/bash
set -e

# Docker entry point for RV-Android experiments.
# Translates environment variables to rv-experiment CLI arguments.

# Interactive mode: if first arg is "bash" or "shell", drop to shell
if [ "$1" = "bash" ] || [ "$1" = "shell" ]; then
    exec /bin/bash "${@:2}"
fi

# Startup delay for staggering parallel container launches
if [ -n "$RV_DELAY" ] && [ "$RV_DELAY" -gt 0 ] 2>/dev/null; then
    echo "=== RV-Android Docker: waiting ${RV_DELAY}s before start ==="
    sleep "$RV_DELAY"
fi

# Pre-computed static analysis files: copy from mounted dir to instrumented_apks/
# Expected layout: $RV_SA_DIR/<apk_name>.apk/<apk_name>.apk.{gesda,wtg,reach}
# Target depends on whether --name is used (results/<name>/instrumented_apks)
# or not (out/instrumented_apks).
if [ -n "$RV_SA_DIR" ] && [ -d "$RV_SA_DIR" ]; then
    if [ -n "$RV_EXPERIMENT_NAME" ]; then
        SA_TARGET="results/$RV_EXPERIMENT_NAME/instrumented_apks"
    else
        SA_TARGET="out/instrumented_apks"
    fi
    mkdir -p "$SA_TARGET"
    copied=0
    for sa_dir in "$RV_SA_DIR"/*.apk/; do
        [ -d "$sa_dir" ] || continue
        for f in "$sa_dir"/*.gesda "$sa_dir"/*.wtg "$sa_dir"/*.reach; do
            [ -f "$f" ] && cp "$f" "$SA_TARGET/" && copied=$((copied + 1))
        done
    done
    echo "=== RV-Android Docker: copied $copied SA files to $SA_TARGET ==="
fi

# Build CLI command from environment variables
CMD="uv run rv-experiment run"

# Tool specification
if [ -n "$RV_TOOLS" ]; then
    CMD="$CMD --tools $RV_TOOLS"
fi

# Execution parameters
if [ -n "$RV_TIMEOUTS" ]; then
    CMD="$CMD --timeout $RV_TIMEOUTS"
fi

if [ -n "$RV_REPETITIONS" ]; then
    CMD="$CMD --repetitions $RV_REPETITIONS"
fi

# APK directory
if [ -n "$RV_APKS_DIR" ]; then
    CMD="$CMD --apks-dir $RV_APKS_DIR"
fi

# Emulator window mode
if [ "$RV_NO_WINDOW" = "true" ] || [ "$RV_NO_WINDOW" = "1" ]; then
    CMD="$CMD --no-window"
elif [ "$RV_NO_WINDOW" = "false" ] || [ "$RV_NO_WINDOW" = "0" ]; then
    CMD="$CMD --window"
fi

# Specification set: RV_SPEC_SET takes precedence over RV_JCA_SPEC
if [ -n "$RV_SPEC_SET" ]; then
    CMD="$CMD --specification-set $RV_SPEC_SET"
elif [ -n "$RV_JCA_SPEC" ]; then
    if [ "$RV_JCA_SPEC" = "true" ] || [ "$RV_JCA_SPEC" = "1" ]; then
        CMD="$CMD --specification-set jca"
    else
        CMD="$CMD --specification-set generic"
    fi
fi

# Pre-processing skip flags
if [ "$RV_SKIP_MONITORS" = "true" ] || [ "$RV_SKIP_MONITORS" = "1" ]; then
    CMD="$CMD --skip-monitors"
fi

if [ "$RV_SKIP_INSTRUMENT" = "true" ] || [ "$RV_SKIP_INSTRUMENT" = "1" ]; then
    CMD="$CMD --skip-instrument"
fi

if [ "$RV_SKIP_STATIC_ANALYSIS" = "true" ] || [ "$RV_SKIP_STATIC_ANALYSIS" = "1" ]; then
    CMD="$CMD --skip-static"
fi

# Device port for parallel execution
if [ -n "$RV_DEVICE_PORT" ]; then
    CMD="$CMD --device-port $RV_DEVICE_PORT"
fi

# gh52: instrumentation variant (ajc | dexlib2). The CLI default is "ajc"
# so the dexlib2 image needs this env var translated to a flag for
# rv-experiment to dispatch to the dexlib2 PreProcessor branch. Forgetting
# this silently runs ajc despite the variant label on the image.
if [ -n "$RV_INSTRUMENTATION_VARIANT" ]; then
    CMD="$CMD --instrumentation-variant $RV_INSTRUMENTATION_VARIANT"
fi

# APK filter file
if [ -n "$RV_APKS_FILTER" ]; then
    CMD="$CMD --apks-filter $RV_APKS_FILTER"
fi

# Experiment name (enables resume via --name)
if [ -n "$RV_EXPERIMENT_NAME" ]; then
    CMD="$CMD --name $RV_EXPERIMENT_NAME"
fi

# Explicit resume directory (overrides --name for resume)
if [ -n "$RV_RESUME_DIR" ]; then
    CMD="$CMD --resume-dir $RV_RESUME_DIR"
fi

# Debug logging
if [ "$RV_DEBUG" = "true" ] || [ "$RV_DEBUG" = "1" ]; then
    CMD="$CMD --debug"
fi

# Socat bridge for LLM hybrid mode (rvsmart multimode/llm_only)
# 'sglang' is the expected Docker Compose service name for the SGLang LLM server
if [ "${RVSMART_LLM_MODE:-false}" = "true" ]; then
    echo "Starting socat bridge for SGLang server..."
    socat TCP-LISTEN:30000,bind=127.0.0.1,fork,reuseaddr TCP:sglang:30000 &
    SOCAT_PID=$!
    trap "kill $SOCAT_PID 2>/dev/null" EXIT
    echo "Socat bridge started (PID: $SOCAT_PID)"
fi

echo "=== RV-Android Docker ==="
echo "CMD: $CMD"
echo "========================="

exec $CMD
