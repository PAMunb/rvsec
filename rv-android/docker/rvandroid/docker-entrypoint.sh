#!/bin/bash
# gh55: Docker entry-point — allow-list validation + exec rv-experiment.
#
# Two responsibilities and only two:
#   1. Validate the env-var allow-list against the canonical ENV_* registry
#      in rv-android-core/constants.py (delegated to validate_env_vars.sh).
#      Unknown RV_*/RVSEC_HOME/ANDROID_HOME/TOOLS_DIR fail with exit 64.
#   2. Exec `rv-experiment run`. The Python layer reads env vars itself via
#      ENV_* constants — no env→flag translation here, EXCEPT for the 5
#      negation-style flags listed in §9.6 (see below).
#
# Special cases handled inline:
#   - bash/shell: drop into interactive shell, skip validation
#   - RV_DELAY:   sleep before exec, for staggering parallel container starts
#   - RVSMART_LLM_MODE: socat bridge for the SGLang LLM service network alias
#   - gh55 §9.6 negation-flag translation: see SKIP_FLAG_ARGS block below

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

# gh55 §9.6 — negation-flag translation (post-code-review fix).
#
# Click `envvar=` resolves env values to the option's POSITIVE dest, not to
# the negation. For paired flags like `--generate-monitors/--skip-monitors`
# (dest=`generate_monitors`), setting RV_SKIP_MONITORS=true via envvar=
# would set generate_monitors=True (the OPPOSITE of intent). The
# rv-experiment-side `envvar=` for these 5 flags is therefore unsafe to
# rely on; the entry-point translates them to explicit negative CLI flags
# here, which override any envvar-resolved positive value via Click's
# CLI > env precedence.
#
# Affected: RV_SKIP_MONITORS, RV_SKIP_INSTRUMENT, RV_SKIP_STATIC_ANALYSIS,
# RV_SKIP_EXECUTION, RV_NO_QUARANTINE. The proper architectural fix lives
# in the env-vars-architecture follow-up change (see gh55/design.md
# "Known Limitations"). Outside Docker (standalone module execution),
# these 5 vars remain ineffective — that gap is the broader gambiarra
# scope.
SKIP_FLAG_ARGS=()
[ "${RV_SKIP_MONITORS:-}" = "true" ]        && SKIP_FLAG_ARGS+=(--skip-monitors)
[ "${RV_SKIP_INSTRUMENT:-}" = "true" ]      && SKIP_FLAG_ARGS+=(--skip-instrument)
[ "${RV_SKIP_STATIC_ANALYSIS:-}" = "true" ] && SKIP_FLAG_ARGS+=(--skip-static)
[ "${RV_SKIP_EXECUTION:-}" = "true" ]       && SKIP_FLAG_ARGS+=(--skip-execution)
[ "${RV_NO_QUARANTINE:-}" = "true" ]        && SKIP_FLAG_ARGS+=(--no-quarantine)

echo "=== RV-Android Docker: validation passed; exec rv-experiment ==="
# --frozen --no-dev: `uv run` alone performs an implicit sync against ALL
# dependency-groups (including [dependency-groups] dev in pyproject.toml —
# pytest, flake8, hypothesis, etc), even though the image is built with
# `uv sync --no-dev`. Every container start would then try to fetch ~13
# dev-only packages from PyPI for no production benefit; a network hiccup
# during that fetch kills the container before rv-experiment even starts
# (observed 2026-07-02, cmpds run: 4/8 containers died on PyPI timeouts for
# pycodestyle/pytest/sortedcontainers/pyflakes). These flags make `uv run`
# use the .venv exactly as built at image-build time, with zero network
# calls at container start.
exec uv run --frozen --no-dev rv-experiment run "${SKIP_FLAG_ARGS[@]}"
