#!/bin/bash
# gh55 INV-EXP-31: Docker entry-point allow-list validator.
#
# Reads the canonical ENV_* registry from rv-android-core/constants.py and
# compares it against every RV_* (and the legacy non-RV_* L1 cross-layer
# infra: RVSEC_HOME, ANDROID_HOME, TOOLS_DIR) variable currently present in
# the environment. Exits 64 with a clear message naming the offending
# variable on the first unknown name.
#
# Why a separate script (vs inline checks in docker-entrypoint.sh): keeps the
# allow-list mechanism single-purpose, lets tests/integration/test_docker_entrypoint.sh
# exercise it without booting the full container, and makes the registry
# extraction strategy (Python parse) explicit.
#
# The registry derivation strategy follows design.md Open Questions: we use
# `python -c "..."` because the Python environment is already available
# inside the rvandroid image (uv venv is part of the image). The fallback —
# parsing constants.py with grep — is unnecessary when Python is on PATH.

set -e

CONSTANTS_FILE="${RV_ANDROID_CONSTANTS_FILE:-/opt/rvsec/rv-android/modules/rv-android-core/src/rv_android_core/constants.py}"

if [ ! -f "$CONSTANTS_FILE" ]; then
    echo "ERROR (validate_env_vars.sh): constants registry not found at $CONSTANTS_FILE" >&2
    echo "  Set RV_ANDROID_CONSTANTS_FILE to override." >&2
    exit 64
fi

# Build allow-list = {ENV_* values from constants.py}.
# Output format: one variable name per line.
ALLOW_LIST=$(python3 -c "
import re
with open('$CONSTANTS_FILE') as f:
    for line in f:
        m = re.match(r'^(ENV_[A-Z0-9_]+)\s*=\s*[\"\']([^\"\']+)[\"\']', line)
        if m:
            print(m.group(2))
")

if [ -z "$ALLOW_LIST" ]; then
    echo "ERROR (validate_env_vars.sh): allow-list parsed from $CONSTANTS_FILE is empty" >&2
    exit 64
fi

# Variables that are out of scope for this allow-list (not RV_* names, not
# in the L1 infra family, but legitimately set by Docker / shell / OS).
# RV_DELAY is special: handled by the entrypoint itself before we run, so it
# is allow-listed even though it does not need to be in constants.py.
LEGITIMATE_NON_RV_VARS="HOME PATH PWD USER SHELL TERM HOSTNAME LANG LC_ALL JAVA_HOME RVSMART_LLM_MODE"

# Iterate over every RV_* variable currently set in the environment plus the
# three legacy non-RV_* L1 cross-layer infra paths.
unknown_vars=""
while IFS='=' read -r name _; do
    case "$name" in
        RV_DELAY) ;;  # entrypoint handles it directly
        RV_ANDROID_CONSTANTS_FILE) ;;  # script's own control variable
        RV_*|RVSEC_HOME|ANDROID_HOME|TOOLS_DIR)
            if ! echo "$ALLOW_LIST" | grep -qx "$name"; then
                unknown_vars="$unknown_vars $name"
            fi
            ;;
    esac
done < <(env | sort)

if [ -n "$unknown_vars" ]; then
    echo "ERROR (validate_env_vars.sh): unknown environment variable(s):$unknown_vars" >&2
    echo "" >&2
    echo "  These names are not in the canonical ENV_* registry at:" >&2
    echo "  $CONSTANTS_FILE" >&2
    echo "" >&2

    # Helpful hint for the canonical removed-var migration.
    case "$unknown_vars" in
        *RV_JCA_SPEC*)
            echo "  Note: RV_JCA_SPEC was removed by gh55. Use RV_SPEC_SET=jca instead." >&2
            ;;
    esac
    case "$unknown_vars" in
        *RV_MEMORY_FILE*|*RV_RVANDROID_URL*|*RV_SKIP_EXPERIMENT*)
            echo "  Note: this variable was removed by gh55 as dead code. Remove it from the compose file." >&2
            ;;
    esac

    exit 64
fi

# Allow-list passes — be silent in the success path so the entrypoint stays clean.
exit 0
