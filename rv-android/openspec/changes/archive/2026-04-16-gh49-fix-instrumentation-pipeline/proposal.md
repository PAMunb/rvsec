## Why

The instrumentation pipeline silently masks failures as successes, and downstream phases (static analysis, execution) waste compute on APKs that cannot produce useful data. Measured across 280 APKs in 10 Docker containers: 82% false success rate — 230 failures absorbed by `@ErrorHandler.handle_errors(reraise=False)` decorators, only 55 physical APKs produced, yet all 280 reported as "Successfully instrumented". `instrument_errors.json` stays empty because exceptions never reach the loop's `except` blocks. Additionally, GATOR static analysis runs on all APKs regardless of instrumentation outcome, and APKs without static analysis data enter experiments with meaningless 0% coverage. GitHub Issue: #49.

## What Changes

- **ErrorHandler decorator phase annotation**: When `reraise=True`, the `@handle_errors` decorator annotates the exception with `_error_phase` (the decorator's `phase` parameter) before re-raising. Innermost decorator's phase wins — outer decorators do not overwrite.
- **Instrumentation pipeline error propagation**: 5 decorators in `rvandroid.py` change from `reraise=False` to `reraise=True` (`instrument`, `__include_generated_monitors`, `__weave_monitors`, `__create_apk`, `__sign_apk`). Loop `except` blocks read `_error_phase` via `getattr()` instead of hardcoding `"command_execution"` / `"general_error"`.
- **Static analysis filtering by instrumentation**: `_get_target_apks_for_analysis()` in PreProcessor filters to only APKs with a corresponding file in `instrumented_apks/`, returning original APK paths (GATOR needs unmodified bytecode).
- **Execution filtering by static analysis**: `get_instrumented_apks()` in PreProcessor filters to only `.apk` files that have a corresponding `.apk.json` (static analysis output) in the same directory.

## Capabilities

### New Capabilities

(none — all changes modify existing capabilities)

### Modified Capabilities

- `core`: ErrorHandler `@handle_errors` decorator gains `_error_phase` annotation behavior when `reraise=True`
- `instrumentation`: Instrumentation pipeline error propagation — exceptions propagate with accurate phase, `instrument_errors.json` is populated correctly
- `experiment`: PreProcessor downstream filtering — static analysis and execution phases only process APKs that passed prior phases

## Impact

**Modules affected**:
- rv-android-core (`error_handler.py`) — M1: ~4 lines
- rv-instrumentation (`rvandroid.py`) — M2+M3: ~7 lines
- rv-experiment (`pre_processor.py`) — M4+M5: ~25 lines

**FRs/NFRs**: FR02 (APK Instrumentation), FR15 (Three-Phase Workflow), NFR04 (Resilience), NFR08 (Reproducibility)

**Cross-module interface**: ErrorHandler's `_error_phase` annotation is consumed by rv-instrumentation's loop `except` blocks. PreProcessor's filtering depends on physical file presence in `instrumented_apks/`, not on return values from rv-instrumentation — loose coupling preserved.
