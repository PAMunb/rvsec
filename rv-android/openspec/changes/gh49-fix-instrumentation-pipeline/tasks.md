<!-- Subagent dispatch hints:
     - Group 1 (ErrorHandler) has no dependencies — can start immediately.
     - Group 2 (Instrumentation) depends on Group 1 (uses _error_phase annotation).
     - Group 3 (Experiment) is independent of Groups 1-2 (file-based filtering, no code dependency).
     - Groups 1 and 3 can run in parallel.
     - Group 4 (Verification) must run after all other groups.
     - This change touches 3 files + ~12 test files — subagent orchestration optional. -->

## 1. ErrorHandler Phase Annotation (rv-android-core)

- [x] 1.1 In `modules/rv-android-core/src/rv_android_core/util/error/error_handler.py`, add `_error_phase` annotation before each `raise` in the `handle_errors` decorator wrapper (lines 455-456 and 459-460): `if phase and not hasattr(e, '_error_phase'): e._error_phase = phase`
- [x] 1.2 Add unit tests in `modules/rv-android-core/tests/util/error/`:
  - Test that `reraise=True` decorator annotates `_error_phase` on exception
  - Test that `reraise=False` does NOT annotate (returns None, no raise)
  - Test nested decorators: inner phase="signing", outer phase="creation" → `_error_phase == "signing"`
- [x] 1.3 Run `/rv-test-run rv-android-core`

## 2. Instrumentation Error Propagation (rv-instrumentation)

- [x] 2.1 In `modules/rv-instrumentation/src/rv_instrumentation/rvandroid.py`, add `reraise=True` to 5 decorators:
  - Line 416: `instrument()` — `phase="single_apk_instrumentation"`
  - Line 712: `__include_generated_monitors()` — `phase="monitor_integration"`
  - Line 747: `__weave_monitors()` — `phase="aspect_weaving"`
  - Line 824: `__create_apk()` — `phase="apk_creation"`
  - Line 1048: `__sign_apk()` — `phase="apk_signing"`
- [x] 2.2 In `rvandroid.py`, update the loop `except` blocks to read `_error_phase`:
  - Line 277: `phase=getattr(ex, '_error_phase', 'command_execution')`
  - Line 305: `phase=getattr(ex, '_error_phase', 'general_error')`
- [x] 2.3 Add/update tests in `modules/rv-instrumentation/tests/`:
  - Test that simulated `CommandException` from `__sign_apk` propagates to loop and produces `InstrumentationError` with `phase="apk_signing"` and `tool="jarsigner"` (`test_sign_apk_failure_propagates`)
  - Test that `InstrumentationError.phase` reflects the actual pipeline phase for different failure points (`test_error_model_has_correct_phase`)
  - Test that `success_count == 0` when all APKs fail instrumentation
  - Test batch with mixed results: N successes + M failures → accurate counts and phases (`test_batch_mixed_results_accurate_counts`)
  - Test that `instrument_errors.json` is written when errors exist
- [x] 2.4 Run `/rv-test-run rv-instrumentation`

## 3. PreProcessor Downstream Filtering (rv-experiment)

- [x] 3.1 In `modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py`, modify `_get_target_apks_for_analysis()` (line 346): scan `instrumented_apks/` for `.apk` files, return only original APK paths that have a corresponding instrumented file. Log skipped APKs.
- [x] 3.2 In `pre_processor.py`, modify `get_instrumented_apks()` (line 356): for each `.apk` found, check if `<name>.apk.json` exists in the same directory. Exclude APKs without `.json` and log warning. Preserve fallback to original APKs if NO APKs pass the filter.
- [x] 3.3 Add tests in `modules/rv-experiment/tests/`:
  - Test `_get_target_apks_for_analysis()` returns only APKs present in `instrumented_apks/`
  - Test `_get_target_apks_for_analysis()` returns empty list when `instrumented_apks/` is empty
  - Test `get_instrumented_apks()` excludes APKs without `.apk.json`
  - Test `get_instrumented_apks()` includes APKs with `.apk.json`
  - Test `get_instrumented_apks()` falls back to original APKs when no APK has `.json`
- [x] 3.4 Run `/rv-test-run rv-experiment`

## 4. Verification

- [ ] 4.1 Run `/rv-qa-lint-fix rv-android-core`
- [ ] 4.2 Run `/rv-qa-lint-fix rv-instrumentation`
- [ ] 4.3 Run `/rv-qa-lint-fix rv-experiment`
- [ ] 4.4 Run `/rv-verify rv-android-core`
- [ ] 4.5 Run `/rv-verify rv-instrumentation`
- [ ] 4.6 Run `/rv-verify rv-experiment`
- [ ] 4.7 E2E: create test dir with `cryptoapp` + 1 failing APK from error dataset, run `uv run rv-experiment run --tools monkey --specification-set jca --apks-dir <test-dir> --timeout 60`. Verify:
  - `cryptoapp` instrumented, SA produces `.json`, executed with coverage > 0%
  - Failing APK in `instrument_errors.json` with correct phase/tool
  - Failing APK has no SA `.json` and no task execution
- [ ] 4.8 Invoke `/rv-code-reviewer` via Skill tool
