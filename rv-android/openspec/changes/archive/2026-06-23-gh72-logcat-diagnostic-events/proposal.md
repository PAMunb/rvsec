# Proposal: Logcat Diagnostic Events (crashes, VerifyError, ANR)

GitHub Issue: #72

Phase 0 ideation document (authoritative for decisions D1–D9, deep investigation, and acceptance
criteria G1–G7): `docs/20260621_plano_logcat_tags_expandidas.md`.

## Why

The pipeline captures logcat with `adb logcat -s RVSEC:V RVSEC-COV:V`. The `-s` flag silences every
other tag at the source, so application crashes, class-load `VerifyError`s, and ANRs never reach the
captured `.logcat` file — confirmed empirically across the 2,028 logcats of the APE×APE-RV run (only
`RVSEC`/`RVSEC-COV` present; the `--------- beginning of crash` separator appears in 8.8% of runs with
its content filtered away). A crash that kills the app early is therefore an invisible confounder: the
instrumented APK looks like a "low-coverage tool result" with no record of why. The bottleneck is
capture, not parsing. This change makes those execution failures observable, replacing the offline
`grep` forensics already done by hand (`out/forensic_ajc_zero/check_crashes.py`).

## What Changes

- **Opt-in capture flag** `RV_LOGCAT_DIAGNOSTICS` (default `false`). When `false`, the emitted `adb`
  command and resulting `.logcat` are byte-identical to today's baseline (no experiment-config change).
  When `true`, the logcat filter additionally whitelists `AndroidRuntime:E art:E dalvikvm:E
  ActivityManager:W` alongside `RVSEC:V RVSEC-COV:V`.
- **New diagnostic-event parsing** that assembles multi-line crash blocks (header + stack frames +
  `Caused by:` + `... N more`) grouped by `(tag, pid, tid)` into single events, plus single/few-line
  `VerifyError` (class-load rejection) and ANR events. The existing `parse_logcat_line` (RVSEC/COV)
  stays unchanged; a separate stateful `DiagnosticEventParser` carries the multi-line state (decision
  D1, chosen by blast-radius: option A would touch 6 production call-sites + 7 test asserts and break
  the public API; option B is additive).
- **New domain model** `RvDiagnosticEvent` with a `category` enum (`crash` | `verify_error` | `anr`)
  and an isolated `diagnostic_events` collection on `LogcatRepository` (decisions D2, D4). Coverage/MOP
  metrics and `total_errors` are unaffected — confirmed: metric calculation reads only `self.classes`
  and `self.errors`.
- **New per-task CSV** `app_events.csv` storing one row per event with `stack_head` (first frame); the
  full multi-line trace stays in the `.logcat` (decision D3). Schemas of `coverage.csv`/`errors.csv` are
  unchanged.
- **App-level attribution** by parsing the crash block itself (`Process: <pkg>` / `ANR in <pkg>`),
  not by a live `--pid` filter (decision D6 — the capture component has no package name at capture
  start, and `--pid` is not practical mid-stream).
- **Out of scope (v1):** native tombstones (`DEBUG:F`/`libc:F`, SIGSEGV) — instrumentation is DEX/Java
  and cannot induce native crashes, and the dataset has 0 ARM-translation-only APKs (decision D8).

No **BREAKING** changes: with the flag off, behavior and all existing CSV schemas are preserved.

## Capabilities

### New Capabilities
<!-- None. This change extends existing domains; it introduces no new spec domain. -->

### Modified Capabilities
- `analysis`: new requirement for diagnostic-event parsing in rv-coverage — a stateful
  `DiagnosticEventParser` (multi-line grouping by `(tag,pid,tid)`, `flush()` at EOF) that feeds
  `LogcatRepository.register_diagnostic_event` from both `parse_logcat_file` (resume reconstruction
  path) and `CoverageTracker`. `parse_logcat_line` and the coverage/MOP metric requirements remain
  unchanged. (FR12, FR13.)
- `core`: opt-in logcat capture in `LogcatManager` (the `RV_LOGCAT_DIAGNOSTICS`-gated tag set, with the
  off-state byte-identical to baseline) plus the `RvDiagnosticEvent` domain model and the isolated
  `diagnostic_events` collection / register / accessor on `LogcatRepository`. (FR33–FR37.)
- `platform`: generation of `app_events.csv` in `result_processor` (surviving the resume
  reconstruction path) and threading the diagnostics flag from config to `LogcatComponent.start_capture`.
  Existing `coverage.csv`/`errors.csv`/`summary.csv` schemas unchanged. (FR07–FR11, FR14.)

## Impact

- **Modules:** `rv-android-core` (`util/android/logcat_manager.py`, `domain/log.py`,
  `domain/coverage.py`, `constants.py`), `rv-coverage`
  (`parser/log/logcat_parser.py`, `analysis/coverage/tracker.py`), `rv-platform`
  (`components/result_processor.py`, `components/logcat.py`, platform config). Flag wiring also passes
  through `rv-experiment` CLI (`__main__.py` Click `envvar=`) and `ExperimentConfig`/`PlatformConfig` as
  a thin pass-through following the existing `RV_*` env-var pattern (no new experiment requirement).
- **Non-regression (NFR):** with the flag off, the adb command, `.logcat` output, and all CSV schemas
  must be byte-identical to baseline; re-parsing the existing 2,028 `cmp_*` logcats must reproduce
  `coverage.csv`/`errors.csv`/`summary.csv` diff-zero. This is the blocking gate G1.
- **Performance (NFR):** capture stays scoped to named error-priority tags (no `*:E` catch-all) to bound
  volume in the `CoverageTracker` background thread.
- **Validation:** E2E uses `examples/cryptoapp` whose option menu carries an intentional crash
  (`MainActivity.java:50`: `new Intent(null, MessageDigestActivity.class)` → `NullPointerException` →
  `FATAL EXCEPTION` under `AndroidRuntime:E`) as the canonical G7 fixture.
- **Cross-dependency:** the resume reconstruction path (gh58, `_reconstruct_repository_from_logcat` →
  `parse_logcat_file`) must re-populate diagnostic events from the logcat so `app_events.csv` survives
  resumed tasks.
