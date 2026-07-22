#!/usr/bin/env bats
# Integration test for docker/rvandroid/scripts/validate_env_vars.sh (gh55 INV-EXP-31).
#
# This bats suite exercises the allow-list validator directly (without
# building the Docker image) to keep CI fast. The validator works against
# the actual rv-android-core/constants.py registry; the only Docker-specific
# concern (mounted constants path) is parameterized via RV_ANDROID_CONSTANTS_FILE.
#
# Run with:
#   bats tests/integration/test_validate_env_vars.bats
# Or, if bats is not installed, run the equivalent shell snippets manually.

setup() {
    SCRIPT="$BATS_TEST_DIRNAME/../../docker/rvandroid/scripts/validate_env_vars.sh"
    CONSTANTS="$BATS_TEST_DIRNAME/../../modules/rv-android-core/src/rv_android_core/constants.py"
    export RV_ANDROID_CONSTANTS_FILE="$CONSTANTS"

    # Snapshot env to clean state for each test (tests must not leak RV_* vars).
    for v in $(env | grep -E '^RV_[A-Z_]+=' | cut -d= -f1); do
        unset "$v" || true
    done
}

@test "allow-list passes when only known RV_* vars are set" {
    export RV_TOOLS=monkey
    export RV_TIMEOUTS=300
    export RV_EXPERIMENT_NAME=batch_01
    run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "allow-list passes with empty environment (no RV_* set)" {
    run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "unknown RV_* variable triggers exit 64" {
    export RV_INVENTADO=foo
    run "$SCRIPT"
    [ "$status" -eq 64 ]
    [[ "$output" == *"RV_INVENTADO"* ]]
}

@test "removed RV_JCA_SPEC triggers exit 64 with migration hint" {
    export RV_JCA_SPEC=true
    run "$SCRIPT"
    [ "$status" -eq 64 ]
    [[ "$output" == *"RV_JCA_SPEC"* ]]
    [[ "$output" == *"RV_SPEC_SET"* ]]
}

@test "removed RV_MEMORY_FILE triggers exit 64 with dead-code hint" {
    export RV_MEMORY_FILE=/tmp/x
    run "$SCRIPT"
    [ "$status" -eq 64 ]
    [[ "$output" == *"RV_MEMORY_FILE"* ]]
    [[ "$output" == *"removed"* ]]
}

@test "L1 cross-layer infra family is allow-listed" {
    export RV_PYDANTIC=true
    export RV_PYDANTIC_STRICT=false
    export RV_PYDANTIC_LOG=false
    export RVSEC_HOME=/opt/rvsec
    export ANDROID_HOME=/opt/android-sdk
    export TOOLS_DIR=/opt/tools
    run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "RV_DELAY is allow-listed even though it is not in constants.py" {
    # RV_DELAY is handled by the entrypoint itself (sleep before exec).
    # The validator must accept it.
    export RV_DELAY=30
    run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "RV_ANDROID_CONSTANTS_FILE (validator's own control var) is allow-listed" {
    # The script reads RV_ANDROID_CONSTANTS_FILE to locate the registry; if
    # the validator did not allow-list its own control variable, every
    # invocation would self-fail (regression discovered during gh55 §5.5).
    run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "missing constants.py file produces a clear error" {
    export RV_ANDROID_CONSTANTS_FILE=/nonexistent/constants.py
    run "$SCRIPT"
    [ "$status" -eq 64 ]
    [[ "$output" == *"not found"* ]]
}
