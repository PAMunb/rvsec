<!-- Dependency order: Group 1 (core models/repo) → Group 2 (core capture) are independent of each other.
     Group 3 (analysis parser) depends on Group 1. Group 4 (analysis integration) depends on Groups 1+3.
     Group 5 (platform CSV) depends on Groups 1+4. Group 6 (platform flag) depends on Group 2.
     Group 7 (E2E + verify) integrates everything.
     Critical path: 1 → 3 → 4 → 5 → 7. ~10 files touched — single-session groups, no subagent fan-out needed. -->

## 1. Core — Diagnostic Event Model and Isolated Repository Collection

- [ ] 1.1 Add `ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` to `modules/rv-android-core/src/rv_android_core/constants.py`
- [ ] 1.2 Add `RvDiagnosticEvent` model (category enum crash/verify_error/anr, fields per design, `unique_msg`, `to_dict`/`from_dict`) to `modules/rv-android-core/src/rv_android_core/domain/log.py`
- [ ] 1.3 Add `diagnostic_events` collection + `register_diagnostic_event` + `get_diagnostic_events` to `LogcatRepository` in `modules/rv-android-core/src/rv_android_core/domain/coverage.py`
- [ ] 1.4 Add unit tests: `RvDiagnosticEvent` (fields, unique_msg by category) and repository isolation (INV-CORE-39: metrics/total_errors unchanged when events registered)
- [ ] 1.5 Run `/rv-doc-code modules/rv-android-core/src/rv_android_core/domain/log.py`
- [ ] 1.6 Run `/rv-test-run rv-android-core`

## 2. Core — Opt-in Logcat Capture

- [ ] 2.1 Extend `LogcatManager.start_capture` use so callers can pass diagnostic tags; ensure flag-off path emits the baseline command unchanged (`modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py`)
- [ ] 2.2 Define `DIAGNOSTIC_TAGS = ["AndroidRuntime:E","art:E","dalvikvm:E","ActivityManager:W"]` constant (single source of truth)
- [ ] 2.3 Add unit tests: INV-CORE-37 (flag off byte-identical command) and INV-CORE-38 (tags additive, RVSEC/COV preserved)
- [ ] 2.4 Run `/rv-test-run rv-android-core`

## 3. Analysis — Stateful Diagnostic Parser

- [ ] 3.1 Implement `DiagnosticEventParser` (`feed_line`/`flush`, group by `(tag,pid,tid)`, close on key change/non-continuation) in new `modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py`
- [ ] 3.2 Implement category extraction: crash (`AndroidRuntime` FATAL + `Process:`/`Caused by:`), verify_error (`art`/`dalvikvm` `Rejecting class`/`Verification error`), anr (`ActivityManager` `ANR in`/`has died`); attribution from block (D6)
- [ ] 3.3 Match on the parsed threadtime **tag field**, never substring (INV-ANA-47); skip non-threadtime lines (INV-ANA-48)
- [ ] 3.4 Create fixtures for the canonical formats (crash multi-line with Caused by + `... N more`, art VerifyError, ANR, and the `isAndroidRuntime()` false-positive) under `modules/rv-coverage/tests/parser/log/fixtures/`
- [ ] 3.5 Add unit tests for `DiagnosticEventParser` (all scenarios in specs/analysis)
- [ ] 3.6 Run `/rv-doc-code modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py`
- [ ] 3.7 Run `/rv-test-run rv-coverage`

## 4. Analysis — Integration into File and Live Parsing

- [ ] 4.1 Drive a `DiagnosticEventParser` inside `parse_logcat_file` (register events; `flush()` at EOF) — keep `parse_logcat_line` signature/behavior unchanged (INV-ANA-46) in `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`
- [ ] 4.2 Drive a `DiagnosticEventParser` inside `CoverageTracker._process_line` / read loop; `flush()` on stop (`modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`)
- [ ] 4.3 Add golden test: re-parse an existing `cmp_*` RVSEC/COV logcat → `parse_logcat_line` output byte-identical to baseline; zero diagnostic events (G1, INV-ANA-46)
- [ ] 4.4 Add integration test: `parse_logcat_file` over a fixture with RVSEC + crash → both registered, metrics unaffected
- [ ] 4.5 Run `/rv-verify rv-coverage`

## 5. Platform — app_events.csv Writer

- [ ] 5.1 Implement `_generate_app_events_csv` + `_write_task_app_events` in `modules/rv-platform/src/rv_platform/components/result_processor.py` (header per spec; `stack_head` only; full trace stays in logcat)
- [ ] 5.2 Call it in the result-processing flow alongside the existing CSV writers; leave coverage/errors/summary writers untouched (INV-PLT-19)
- [ ] 5.3 Add test: one row per event with expected fields; headers of coverage/errors/summary byte-identical to baseline
- [ ] 5.4 Add test: events survive the resume reconstruction path (`_reconstruct_repository_from_logcat`) → `app_events.csv` populated (INV-PLT-20)
- [ ] 5.5 Run `/rv-test-run rv-platform`

## 6. Platform/Experiment — Flag Threading

- [ ] 6.1 Add `logcat_diagnostics` field to `ExperimentConfig` and `PlatformConfig`; add Click `--logcat-diagnostics/--no-logcat-diagnostics` with `envvar=ENV_LOGCAT_DIAGNOSTICS` (default false) in `modules/rv-experiment/src/rv_experiment/__main__.py`
- [ ] 6.2 Thread the flag into `LogcatComponent`; pass `tags=default_tags + DIAGNOSTIC_TAGS` only when enabled (INV-PLT-21) in `modules/rv-platform/src/rv_platform/components/logcat.py`
- [ ] 6.3 Add integration test: flag end-to-end (config → component → emitted command) for on and off
- [ ] 6.4 Run `/rv-test-run rv-platform`

## 7. Integration, E2E, and Verification

- [ ] 7.1 E2E (G7): run a short capture with `RV_LOGCAT_DIAGNOSTICS=true` on `examples/cryptoapp`, exercise the option menu (Message Digest), confirm `app_events.csv` has the NPE crash (`category=crash`, `exception_class=java.lang.NullPointerException`, `process=br.unb.cic.cryptoapp`, `stack_head`→`MainActivity.java:50`) and the `.logcat` has the raw block
- [ ] 7.2 Confirm AC7.2: coverage/MOP of non-crashing flow unchanged vs a flag-off run; record AC7.3 (whether `art`/`dalvikvm` emitted at W vs E)
- [ ] 7.3 Run `/rv-qa-lint-fix rv-android-core rv-coverage rv-platform`
- [ ] 7.4 Run `/rv-verify rv-android-core rv-coverage rv-platform`
- [ ] 7.5 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 7.6 Run `/rv-docs-sync rv-coverage` (document the new parser + app_events.csv if module docs need it)
