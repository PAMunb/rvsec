#!/bin/bash
# gh55: Docker entry-point — allow-list validation + exec rv-experiment.
#
# Two responsibilities and only two:
#   1. Validate the env-var allow-list against the canonical ENV_* registry
#      in rv-android-core/constants.py (delegated to validate_env_vars.sh).
#      Unknown RV_*/RVSEC_HOME/ANDROID_HOME/TOOLS_DIR fail with exit 64.
#   2. Exec `rv-experiment run`. The Python layer reads env vars itself via
#      ENV_* constants — no env→flag translation here.
#
# Special cases handled inline:
#   - bash/shell: drop into interactive shell, skip validation
#   - RV_DELAY:   sleep before exec, for staggering parallel container starts
#   - RVSMART_LLM_MODE: socat bridge for the SGLang LLM service network alias

set -e

# Interactive mode bypasses validation (operator is debugging).
if [ "$1" = "bash" ] || [ "$1" = "shell" ]; then
    exec /bin/bash "${@:2}"
fi

# Allow-list validation. Exits 64 on first unknown RV_* name.
"$(dirname "$0")/scripts/validate_env_vars.sh"

# Startup delay (RV_DELAY) staggers parallel container launches so they don't
# all hit the same emulator-boot resource peak.
if [ -n "$RV_DELAY" ] && [ "$RV_DELAY" -gt 0 ] 2>/dev/null; then
    echo "=== RV-Android Docker: waiting ${RV_DELAY}s before start ==="
    sleep "$RV_DELAY"
fi

# Socat bridge for LLM hybrid mode (SGLang). Out of scope for the env-var
# allow-list because RVSMART_LLM_MODE is a docker-compose toggle, not an
# rv-experiment input — handled here at the entry-point level.
if [ "${RVSMART_LLM_MODE:-false}" = "true" ]; then
    echo "Starting socat bridge for SGLang server..."
    socat TCP-LISTEN:30000,bind=127.0.0.1,fork,reuseaddr TCP:sglang:30000 &
    SOCAT_PID=$!
    trap "kill $SOCAT_PID 2>/dev/null" EXIT
    echo "Socat bridge started (PID: $SOCAT_PID)"
fi

# Pre-computed static analysis files: copy from mounted dir to instrumented_apks/.
# Layout: $RV_SA_DIR/<apk_name>.apk/<apk_name>.apk.{gesda,wtg,reach}
# Target depends on whether --name is used (results/<name>) or not (out/).
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

echo "=== RV-Android Docker: validation passed; exec rv-experiment ==="
exec uv run rv-experiment run
