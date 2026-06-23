<!-- Dependency order: Group 1 (core models/repo) → Group 2 (core capture) are independent of each other.
     Group 3 (analysis parser) depends on Group 1. Group 4 (analysis integration) depends on Groups 1+3.
     Group 5 (platform CSV) depends on Groups 1+4. Group 6 (platform flag) depends on Group 2.
     Group 7 (E2E + verify) integrates everything.
     Critical path: 1 → 3 → 4 → 5 → 7. ~10 files touched — single-session groups, no subagent fan-out needed. -->

## 1. Core — Diagnostic Event Model and Isolated Repository Collection

- [x] 1.1 Add `ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` to `modules/rv-android-core/src/rv_android_core/constants.py`
- [x] 1.2 Add `RvDiagnosticEvent` model (category enum crash/verify_error/anr, fields per design, `unique_msg`, `to_dict`/`from_dict`) to `modules/rv-android-core/src/rv_android_core/domain/log.py`
- [x] 1.3 Add `diagnostic_events` collection + `register_diagnostic_event` + `get_diagnostic_events` to `LogcatRepository` in `modules/rv-android-core/src/rv_android_core/domain/coverage.py`
- [x] 1.4 Add unit tests: `RvDiagnosticEvent` (fields, unique_msg by category) and repository isolation (INV-CORE-39: metrics/total_errors unchanged when events registered)
- [x] 1.5 Run `/rv-doc-code modules/rv-android-core/src/rv_android_core/domain/log.py` — docstrings written inline to P2/convention (RvErrorLog pattern); audit deferred to final docs-sync
- [x] 1.6 Run `/rv-test-run rv-android-core` — new tests 7/7 green; full-suite run batched with task 2.4

## 2. Core — Opt-in Logcat Capture

- [x] 2.1 Extend `LogcatManager.start_capture` use so callers can pass diagnostic tags; ensure flag-off path emits the baseline command unchanged (`modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py`) — priority-bearing tags kept verbatim (no spurious `:V`)
- [x] 2.2 Define `DIAGNOSTIC_TAGS = ["AndroidRuntime:E","art:E","dalvikvm:E","ActivityManager:W"]` constant (single source of truth) — in `logcat_manager.py`, imported by platform
- [x] 2.3 Add unit tests: INV-CORE-37 (flag off byte-identical command) and INV-CORE-38 (tags additive, RVSEC/COV preserved)
- [x] 2.4 Run `/rv-test-run rv-android-core` — full suite 902 passed

## 3. Analysis — Stateful Diagnostic Parser

- [x] 3.1 Implement `DiagnosticEventParser` (`feed_line`/`flush`, group by `(tag,pid,tid)`, close on key change/non-continuation) in new `modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py`
- [x] 3.2 Implement category extraction: crash (`AndroidRuntime` FATAL + `Process:`/`Caused by:`), verify_error (`art`/`dalvikvm` `Rejecting class`/`Verification error`), anr (`ActivityManager` `ANR in`/`has died`); attribution from block (D6)
- [x] 3.3 Match on the parsed threadtime **tag field**, never substring (INV-ANA-47); skip non-threadtime lines (INV-ANA-48)
- [x] 3.4 Create fixtures for the canonical formats (crash multi-line with Caused by + `... N more`, art VerifyError, ANR, and the `isAndroidRuntime()` false-positive) under `modules/rv-coverage/tests/parser/log/fixtures/`
- [x] 3.5 Add unit tests for `DiagnosticEventParser` (all scenarios in specs/analysis) — 11/11 green
- [x] 3.6 Run `/rv-doc-code modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py` — module/class/method docstrings written inline to P2; audit deferred to docs-sync
- [x] 3.7 Run `/rv-test-run rv-coverage` — diagnostic-parser subset green; full-suite run batched with task 4.5

## 4. Analysis — Integration into File and Live Parsing

- [x] 4.1 Drive a `DiagnosticEventParser` inside `parse_logcat_file` (register events; `flush()` at EOF) — keep `parse_logcat_line` signature/behavior unchanged (INV-ANA-46) in `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` (lazy import breaks the cycle)
- [x] 4.2 Drive a `DiagnosticEventParser` inside `CoverageTracker._process_line` / read loop; `flush()` on stop (`modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`) — `flush_diagnostics()` in `_track_coverage` finally
- [x] 4.3 Add golden test: re-parse an existing `cmp_*` RVSEC/COV logcat → `parse_logcat_line` output byte-identical to baseline; zero diagnostic events (G1, INV-ANA-46) — committed golden fixture + optional real `cmp_*` test (passed over 5994-line real logcat)
- [x] 4.4 Add integration test: `parse_logcat_file` over a fixture with RVSEC + crash → both registered, metrics unaffected
- [x] 4.5 Run `/rv-verify rv-coverage` — full suite 93 passed; lint/type batched into task 7.4

## 5. Platform — app_events.csv Writer

- [x] 5.1 Implement `_generate_app_events_csv` + `_write_task_app_events` in `modules/rv-platform/src/rv_platform/components/result_processor.py` (header per spec; `stack_head` only; full trace stays in logcat)
- [x] 5.2 Call it in the result-processing flow alongside the existing CSV writers; leave coverage/errors/summary writers untouched (INV-PLT-19)
- [x] 5.3 Add test: one row per event with expected fields; headers of coverage/errors/summary byte-identical to baseline
- [x] 5.4 Add test: events survive the resume reconstruction path (`_reconstruct_repository_from_logcat`) → `app_events.csv` populated (INV-PLT-20)
- [x] 5.5 Run `/rv-test-run rv-platform` — result_processor tests 55 passed; full-suite run batched with task 6.4

## 6. Platform/Experiment — Flag Threading

- [x] 6.1 Add `logcat_diagnostics` field to `ExperimentConfig` and `PlatformConfig`; add Click `--logcat-diagnostics/--no-logcat-diagnostics` with `envvar=ENV_LOGCAT_DIAGNOSTICS` (default false) in `modules/rv-experiment/src/rv_experiment/__main__.py` — mapped to PlatformConfig in execution_controller
- [x] 6.2 Thread the flag into `LogcatComponent`; pass `tags=default_tags + DIAGNOSTIC_TAGS` only when enabled (INV-PLT-21) in `modules/rv-platform/src/rv_platform/components/logcat.py` (flag from platform.py via `self.config.logcat_diagnostics`)
- [x] 6.3 Add integration test: flag end-to-end (config → component → emitted command) for on and off — INV-PLT-21 on/off tests in test_logcat.py
- [x] 6.4 Run `/rv-test-run rv-platform` — full suite 253 passed; rv-experiment suite 193 passed (1 mock fixture updated)

## 7. Integration, E2E, and Verification

- [x] 7.1 E2E (G7): ran `RV_LOGCAT_DIAGNOSTICS=true` (`--logcat-diagnostics`) on the instrumented `cryptoapp` via rv-platform-managed emulator (`--window`, tool `aperv:sata_mop@throttle_ms=4000`, 60s); manually exercised the overflow menu → *Message Digest* → NPE. **Confirmed in `results/g7_crash_aperv/app_events.csv`** (2 crash rows): `category=crash`, `exception_class=java.lang.NullPointerException`, `process=br.unb.cic.cryptoapp`, `fatal=True`, `method=onMenuItemClick`, `source=MainActivity.java:50`, `n_frames=47`, `stack_head=br.unb.cic.cryptoapp.MainActivity$1.onMenuItemClick(MainActivity.java:50)`; the `.logcat` carries the raw `AndroidRuntime` FATAL blocks (lines 652-657, 1400-1405). Task 1/1 successful — `aperv` tolerates the crash exit and runs to timeout (unlike `monkey`, which aborts with exit 41 → task ERROR → no CSV writer). Live `DiagnosticEventParser` also logged `Diagnostic event (crash) detected` inside the `CoverageTracker`.
- [x] 7.2 AC7.2 confirmed: coverage/MOP computed normally (`mop_errors_total=16`/`unique=10`; 28 coverage rows; `cov_method=26.42%`) and **isolated** from diagnostics — 0 crash/NPE refs in `errors.csv`/`coverage.csv` (G4/INV-CORE-39). Non-interference proven by byte-identical headers across crash vs no-crash runs for `coverage.csv`/`errors.csv`/`summary.csv`/`performance.csv` (INV-PLT-19) and `errors.csv` rows == `summary.mop_errors_total`. AC7.3 recorded: **0** `art`/`dalvikvm` tags emitted and **0** `verify_error` events (the NPE is a runtime crash, not load-time VerifyError) → no need to widen capture to `art:W`.
- [x] 7.3 Run `/rv-qa-lint-fix rv-android-core rv-coverage rv-platform` — black applied; flake8 F-codes clean on changed files (E501 is pre-existing/un-gated baseline; CI runs pytest only)
- [x] 7.4 Run `/rv-verify rv-android-core rv-coverage rv-platform` — tests green across all 4 touched modules (902 + 93 + 253 + 193 = 1441); F-code lint clean on changed files
- [x] 7.5 Invoke `/rv-code-reviewer` via Skill tool — **dispensado pelo usuário**
- [x] 7.6 Run `/rv-docs-sync rv-coverage` (document the new parser + app_events.csv if module docs need it) — **dispensado pelo usuário**
