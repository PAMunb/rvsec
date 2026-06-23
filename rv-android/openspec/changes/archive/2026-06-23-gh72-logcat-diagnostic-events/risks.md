# Risk Register: gh72-logcat-diagnostic-events

**Change**: Opt-in capture + parsing of diagnostic logcat events (crashes, class-load `VerifyError`, ANR). Multi-module: `rv-android-core` (capture + models + repo), `rv-coverage` (parser + integration), `rv-platform` (`app_events.csv` + flag), with thin pass-through in `rv-experiment`.
**Date**: 2026-06-23 | **Owner**: Pedro Costa | **Status**: Open (pre-implementation)
**Grounding**: `design.md` §Risks, Phase 0 plan §9 (`docs/20260621_plano_logcat_tags_expandidas.md`), specs (core/analysis/platform), `tasks.md`, ADR-001. Two design claims verified against source (notes below).
**GitHub Issue**: #72

## Summary

| Risk Level | Count |
|------------|-------|
| Critical | 0 |
| High | 2 |
| Medium | 3 |
| Low | 3 |

**Methodology note**: Every Phase 0 §9 risk and every design "Risks / Trade-offs" item was carried forward and re-projected, then two were re-rated after a source-code check (isolation reads and resume call-site count). No risk was retired without evidence. The dominant risk class is **Product** (correctness of the experiment baseline), not Project/Schedule — the change is ~10 files, single-session.

---

## Top Risks

### RISK-001: Capture change silently alters the experiment baseline
- **Category**: Technology / Product
- **Description**: Every existing experiment depends on the byte-identical baseline `adb logcat -v threadtime -s RVSEC:V RVSEC-COV:V` (memory `feedback_never_change_experiment_config`). A regression in the flag-off path — wrong default, tag-list mutation leaking into the off-branch, or reordering — would corrupt the baseline of all future runs invisibly.
- **Probability**: Low (10-25%) — the `tags` parameter already exists; the off-path is a no-op by design (D5).
- **Effect**: Catastrophic — invalidates experiment comparability across the whole pipeline; discovered late.
- **Risk Level**: **High** (Low × Catastrophic).
- **Mitigation**: Avoidance + Minimization.
  - **Avoidance**: opt-in flag `RV_LOGCAT_DIAGNOSTICS` default `false`; off-state emits the unchanged command (D5, INV-CORE-37). Do NOT flip the flag on in baseline compose (Non-Goal D9).
  - **Minimization**: golden re-parse gate G1 over the 2,028 `cmp_*` logcats reproducing `coverage.csv`/`errors.csv`/`summary.csv` diff-zero (task 4.3); unit test INV-CORE-37 asserting the exact command string for serial `emulator-5554`.
- **Indicators**: any non-empty diff in the G1 golden run; off-branch command-string test failing; a PR diff editing the flag default. **Trigger to halt**: G1 diff ≠ 0.
- **Owner**: Pedro Costa | **Status**: Open (mitigation designed, not yet verified).

### RISK-002: Diagnostic events survive the resume path incorrectly (gh58)
- **Category**: Technology / Product
- **Description**: `app_events.csv` must repopulate when a task's repository is rebuilt from its `.logcat` on resume (INV-PLT-20). **Verified in source**: `_reconstruct_repository_from_logcat` → `parse_logcat_file` is invoked from **four** call-sites in `result_processor.py` (lines 368, 529, 636, 807). If the `DiagnosticEventParser` is wired into `parse_logcat_file` but a reconstruction call-site or its CSV-write counterpart is missed, resumed tasks silently drop events — and the gh58 CSV-zeroing bug (memory `project_resume_csv_zeroing_bug`) shows the resume path is already a landmine.
- **Probability**: Moderate (25-50%) — multiple call-sites + a pre-existing resume defect.
- **Effect**: Serious — silent data loss on the resume subset; undermines the feature precisely on long/interrupted runs.
- **Risk Level**: **High** (Moderate × Serious).
- **Mitigation**: Minimization + Contingency.
  - **Minimization**: drive the parser *inside* `parse_logcat_file` so reconstruction is automatic (task 4.1, single source of truth); integration test reconstructing from a fixture logcat with a crash block (task 5.4 / INV-PLT-20).
  - **Contingency**: route any bypassing call-site through `parse_logcat_file`; offline re-parse of `.logcat` recovers events post-hoc (`.logcat` is source of truth, D3).
- **Indicators**: resume integration test (5.4) failing/absent; `app_events.csv` empty for crashed tasks; event-count diff between live and reconstructed runs on the same `.logcat`. **Trigger**: reconstruction event count ≠ live event count for an identical logcat.
- **Owner**: Pedro Costa | **Status**: Open.

### RISK-003: Stateful parser perturbs the RVSEC/COV hot path
- **Category**: Technology / Product
- **Description**: The new `DiagnosticEventParser` runs on the same `CoverageTracker` background thread that drives `parse_logcat_line`. State (multi-line buffering by `(tag,pid,tid)`) near the hot path could corrupt coverage/MOP/violation extraction if the two parsers share mutable state or line dispatch is refactored.
- **Probability**: Low (10-25%) — D1 (option B) keeps `parse_logcat_line` a pure untouched 2-tuple function; the parser is additive.
- **Effect**: Serious — coverage/MOP is the metric the framework reports.
- **Risk Level**: **Medium** (Low × Serious).
- **Mitigation**: Avoidance.
  - **Avoidance**: D1 keeps `parse_logcat_line` signature/behavior unchanged (INV-ANA-46 asserts the 2-tuple signature); the diagnostic parser is a separate object with its own buffer, fed in parallel, not chained.
  - **Minimization**: RVSEC/COV golden test (task 4.3); explicit rejection of the 3-tuple variant in D1/ADR-001 guards against drift in review.
- **Indicators**: golden RVSEC/COV diff ≠ 0; any change to `parse_logcat_line`'s return type; coverage delta vs flag-off run in AC7.2. **Trigger**: AC7.2 shows coverage/MOP delta on a non-crashing flow.
- **Owner**: Pedro Costa | **Status**: Open (isolation **confirmed in source** — metric methods read only `self.classes`/`self.errors`/`self.unique_errors`, `coverage.py` lines 569-808).

### RISK-004: `art`/`dalvikvm` emit verification logs at priority W, not E
- **Category**: Technology (device/runtime behavior)
- **Description**: The tag set whitelists `art:E dalvikvm:E`. If the AVD's ART emits `Rejecting class` / `Verification error` at **W**, those VerifyError events are never captured — the exact confounder the change exists to expose.
- **Probability**: Moderate (25-50%) — ART verification priority is version/config-dependent and unverified on the target AVD (Open Question in design.md).
- **Effect**: Tolerable — partial loss of one category; crashes/ANRs unaffected; recoverable by widening the tag.
- **Risk Level**: **Medium** (Moderate × Tolerable).
- **Mitigation**: Contingency (empirical resolution).
  - **Contingency**: AC7.3 records the observed priority in the E2E run; if W, widen to `art:W`/`dalvikvm:W` (one-line change in `DIAGNOSTIC_TAGS`, task 2.2).
- **Indicators**: AC7.3 observation; a known load-time-rejecting APK producing zero `verify_error` rows. **Trigger**: AC7.3 shows W-priority verification logs.
- **Owner**: Pedro Costa | **Status**: Open (resolved empirically in task 7.2).

### RISK-005: False-positive tag match (substring) pollutes events
- **Category**: Technology / Product
- **Description**: An `RVSEC-COV` line whose **message** contains `isAndroidRuntime()` (real instrumented-method name) would be mis-classified as an `AndroidRuntime` crash if matching is on the line, not the parsed tag field.
- **Probability**: Low (10-25%) — explicitly anticipated; mitigation specified.
- **Effect**: Tolerable — spurious rows in `app_events.csv`; metrics unaffected (isolated collection).
- **Risk Level**: **Low** (Low × Tolerable).
- **Mitigation**: Avoidance.
  - **Avoidance**: match the parsed threadtime **tag field**, never a message substring (INV-ANA-47); dedicated false-positive fixture in tasks 3.4/3.5.
- **Indicators**: false-positive fixture test failing; `category=crash` rows with empty/instrumentation-internal `process`. **Trigger**: any `app_events.csv` row sourced from a `RVSEC-COV` tag.
- **Owner**: Pedro Costa | **Status**: Open.

### RISK-006: Log volume in long runs burdens the tracker thread / fills disk
- **Category**: Tools / Performance
- **Description**: Adding tags widens capture; on long campaigns a noisy app could bloat the `.logcat` and load the background `CoverageTracker` thread.
- **Probability**: Low (10-25%) — scoped to named error-priority tags, no `*:E` catch-all.
- **Effect**: Tolerable — larger files / minor overhead; bounded by tag scoping.
- **Risk Level**: **Low** (Low × Tolerable).
- **Mitigation**: Minimization.
  - **Minimization**: named error-priority tags only (NFR Performance); measure overhead in the validation run. Off by default → baseline campaigns carry zero cost.
- **Indicators**: `.logcat` size or task wall-clock materially higher in a flag-on run vs flag-off. **Trigger**: >X% wall-clock or file-size regression (threshold set during AC7.2).
- **Owner**: Pedro Costa | **Status**: Open.

### RISK-007: `app_events.csv` schema churn breaks downstream consolidation
- **Category**: Requirements / Tools
- **Description**: The new CSV's columns must NOT add to or reorder `coverage.csv`/`errors.csv`/`summary.csv`, which downstream consolidation scripts and the paired Wilcoxon analysis read positionally.
- **Probability**: Very Low (<10%) — existing schemas untouched (D3, INV-PLT-19); `app_events.csv` is a new file.
- **Effect**: Serious if it occurred (silent consolidation breakage), but very low probability.
- **Risk Level**: **Low** (Very Low × Serious).
- **Mitigation**: Avoidance.
  - **Avoidance**: `app_events.csv` is additive; INV-PLT-19 asserts byte-identical headers/order for the three existing CSVs; test in task 5.3.
- **Indicators**: header diff on the three existing CSVs; consolidation script column-index errors. **Trigger**: INV-PLT-19 test diff ≠ 0.
- **Owner**: Pedro Costa | **Status**: Open.

### RISK-008: Multi-line block assembly mis-groups events
- **Category**: Technology
- **Description**: Crash blocks are assembled by `(tag,pid,tid)` with close-on-key-change + `flush()` at EOF. Interleaved logcat from concurrent processes, a final crash truncated at capture stop, or non-threadtime separators (`--------- beginning of crash`) could split one event into many or drop the last.
- **Probability**: Moderate (25-50%) — multi-line assembly from interleaved real-device logs is fiddly.
- **Effect**: Insignificant-to-Tolerable — wrong `n_frames`/split rows; the full trace is always preserved in `.logcat` (D3), so no information loss, only structure.
- **Risk Level**: **Medium** (Moderate likelihood).
- **Mitigation**: Minimization + Contingency.
  - **Minimization**: skip non-threadtime lines without error (INV-ANA-48); fixtures for canonical formats incl. `Caused by:` + `... N more` (task 3.4); `flush()` at stop and on key change.
  - **Contingency**: `.logcat` retains the raw block → re-parse with a corrected grouping rule recovers structure offline (Open Question in design.md: flush on quiescence vs stop).
- **Indicators**: `n_frames` mismatch in fixture tests; duplicate/split rows for one observed crash in E2E. **Trigger**: E2E G7 produces ≠1 row for the single cryptoapp NPE.
- **Owner**: Pedro Costa | **Status**: Open.

---

## Monitoring Schedule

- **Review cadence**: at each task-group boundary in `tasks.md` (groups 1→7), plus a mandatory full review at Phase 5 (Verify) before archive.
- **Blocking gates** (any red halts archive): G1 golden re-parse diff-zero (RISK-001/003), INV-PLT-20 resume test (RISK-002), AC7.2 coverage/MOP unchanged (RISK-003), INV-PLT-19 header diff-zero (RISK-007), E2E G7 single-NPE-row (RISK-008).
- **Empirical-resolution checkpoint**: AC7.3 in task 7.2 retires or escalates RISK-004.
- **Next review**: at completion of task group 4 (analysis integration — the critical path for RISK-001/002/003).

## Change Log

| Date | Risk | Change |
|------|------|--------|
| 2026-06-23 | RISK-001..008 | Initial register from design.md §Risks + Phase 0 §9; carried all 6 source risks + added RISK-007 (CSV schema) and RISK-008 (block assembly) from spec invariants. |
| 2026-06-23 | RISK-002 | Re-rated to **High** after source check: `parse_logcat_file` reconstruction invoked from 4 call-sites in `result_processor.py`; pre-existing gh58 resume defect compounds. |
| 2026-06-23 | RISK-003 | Isolation **confirmed in source** (`coverage.py` metric methods read only `self.classes`/`self.errors`/`self.unique_errors`); kept Medium. |
