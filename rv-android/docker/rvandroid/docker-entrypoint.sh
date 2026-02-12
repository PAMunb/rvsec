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

# Build CLI command from environment variables
CMD="poetry run rv-experiment run"

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

# Specification set: RV_SPEC_SET takes precedence over legacy RV_JCA_SPEC
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

echo "=== RV-Android Docker ==="
echo "CMD: $CMD"
echo "========================="

exec $CMD
