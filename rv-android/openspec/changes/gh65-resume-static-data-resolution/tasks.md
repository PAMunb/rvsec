<!-- Small change (~3 source files + tests + 1 offline script + docs). No subagent orchestration needed.
     Critical path: Group 1 (coverage.py / D-2) -> Group 2 (result_processor / D-1, D-3a) -> Group 3 (regression test) -> Group 5 (verify). -->

## 1. Error aggregates independent of static data (D-2 — rv-android-core)

- [ ] 1.1 In `modules/rv-android-core/src/rv_android_core/domain/coverage.py`, move the `metrics.total_errors = len(self.errors)` and `metrics.unique_errors = len(self.unique_errors)` assignments to **before** the `if not self.classes: return metrics` early return in `calculate_metrics()` (D-2; analysis spec "Error Aggregates Are Independent of Static Analysis Data", INV-ANA-25)
- [ ] 1.2 Add unit tests: `test_metrics_empty_classes_counts_errors` (empty `classes` + K errors / J unique → `to_dict()["total_errors"]==K`, `unique_errors==J`, all coverage `0`) and `test_error_count_matches_get_errors_logcat_only` (analysis scenarios "Metrics Over Empty Classes Still Count Errors", "Error Count Matches get_errors After Logcat-Only Reconstruction")
- [ ] 1.3 Run `/rv-test-run rv-android-core`

## 2. Resume results_dir resolution + once-per-task unresolved counter (D-1, D-3, D-3a — rv-platform)

- [ ] 2.1 In `modules/rv-platform/src/rv_platform/components/result_processor.py` `_resolve_static_data`, derive the directory as `task.results_dir or os.path.dirname(task.result.logcat_file)` when `logcat_file` is set; pass the derived dir to `read_static_analysis_files(..., apk_name, task.app.code_package if task.app else None)` (D-1; INV-PLT-15; ADR 0003)
- [ ] 2.2 Account for tasks with unresolved static data using **two fields of disjoint responsibility** (D-3a; INV-PLT-15; platform scenario "Static Analysis JSON Missing on Resume"): (a) on every path, assign `task.static_data` a *valid* `StaticAnalysisData` — an **empty** `StaticAnalysisData()` when the JSON is absent or the parser raises — so it is both the parse memo (non-`None` short-circuits re-entry, no re-parse) and a legal argument to `parse_logcat_file`; `_resolve_static_data` returns `None` to callers when the memo has empty `classes`. (b) Track the count on a component-level `self._unresolved_task_ids: set[str]`, membership-guarded (incremented at most once per task, order-independent), (re)initialized at the start of `execute()`; `len(...)` is the aggregate `N`. The `except` backstop MUST also memoize the empty `StaticAnalysisData`. Per-task warning on first unresolved resolution
- [ ] 2.3 In `_write_task_summary_data`/`_write_task_coverage_data`, emit a zeroed row with an explicit warning when reconstruction fails (logcat present but JSON genuinely absent, or logcat missing). Do **NOT** fall back to serialized `task.result.coverage_metrics` — it would make `summary.csv` `cov_*` non-zero while `coverage.csv` stays empty, which `verify.py` C3 flags as a failure (D-3; INV-PLT-16 unchanged; INV-PLT-17; platform scenario "No Fallback to Serialized Coverage Metrics When JSON Is Absent")
- [ ] 2.4 Add unit tests: `test_resolve_static_data_derives_dir_from_logcat`, `test_missing_json_counts_and_errors_survive`, `test_unresolved_counter_increments_once_per_task` (call all three writers for one JSON-absent task; assert `len(_unresolved_task_ids) == 1` AND the parser spy `read_static_analysis_files.call_count == 1`), `test_missing_json_summary_row_zeroed_no_fallback` (serialized `coverage_metrics` present but JSON absent → `summary.csv` `cov_*` still `0.00`, `mop_errors_*` accurate). The exhaustive D-3a integrity matrix lives in Group 3 (G9, task 3.9)
- [ ] 2.5 Run `/rv-test-run rv-platform`

## 3. Resume validation gate (G0–G6 — rv-platform)

> Definition of Done lives in `design.md` "Validation Criteria". Each gate is a hard pass/fail. The
> recurring failure mode is tests that set the very runtime fields resume drops — these gates forbid that.

- [ ] 3.1 **G0/G2 — RED first**: before applying the Group 2 fix, write the two-session resume integration test and confirm it **FAILS** on current code (proves it exercises the bug). Commit the failing test, then the fix, then the green test
- [ ] 3.2 **G1 — Round-trip equivalence** (`test_roundtrip_metric_equivalence`, parametrized over ≥3 fixtures: MOP-violations / `--skip-static` / normal): assert `metrics(live task) == metrics(Task.from_dict(Task.to_dict(task)) reconstructed)` for the 6 `cov_*` + `mop_errors_total`/`mop_errors_unique`, tolerance `0.01` (INV-PLT-18, platform scenario "Round-Trip Metric Equivalence")
- [ ] 3.3 **G2 — Two-session E2E (no emulator)** (`test_e2e_two_session_resume`): stub tool writes a real logcat + co-located SA JSON; `Platform.run()` session 1 (task A) → persist `tasks.json` → `Platform.run()` session 2 resume (task B); assert consolidated `summary.csv` has BOTH rows with `cov_method>0` and correct `mop_errors_*`, asserting **specifically the resumed row A**
- [ ] 3.4 **G3 — Consolidation-only pass**: reprocess where all tasks are loaded from disk (skip everything — the path that zeroed T=300); assert correct CSV for 100% of rows
- [ ] 3.5 **G4 — Loud signal** (`test_resume_health_check_warning`): with ≥1 task whose logcat is present but JSON absent, assert one aggregate WARNING fires with the exact `N/M`; assert no warning when N=0 (INV-PLT-18, platform scenario "Resume Coverage Health Check Warning")
- [ ] 3.6 **G6 — Coverage canary**: in the G2/G3 consolidated `summary.csv`, assert the fraction of tasks-with-`RVSEC-COV` having `cov_method>0` is 100% (historical symptom: 4/1055)
- [ ] 3.7 Revise `_make_gh58_task` so the resume variant goes through `Task.from_dict(Task.to_dict())` (no manual `results_dir`/`app`); keep the live-task variant for G1's "live" side
- [ ] 3.8 Run `/rv-verify rv-platform`
- [ ] 3.9 **G9 — D-3a accounting integrity** (`test_d3a_accounting_matrix`, parametrized): cartesian product of {all permutations of the 3 writers} × {JSON populated, JSON absent, JSON present-but-empty, parser raises}. For each cell assert: (a) `len(_unresolved_task_ids) == (1 if unresolved else 0)`; (b) parser spy `read_static_analysis_files.call_count <= 1` (no re-parse, incl. exception path); (c) re-entry returns a valid zeroed repository, never raises (no sentinel pollution); (d) a second `execute()` pass re-initializes the set. This is the hard pass/fail for D-3a (design.md G9; INV-PLT-15; platform scenario "Static Analysis JSON Missing on Resume")

## 3b. Golden regression vs offline reference (G5 — rv-platform)

- [ ] 3b.1 Add `test_golden_vs_offline_regen`: sample ≥10 real `experimento-20260604` tasks (logcat + co-located JSON committed as fixtures), reconstruct in-container-style, and assert `cov_method`/`cov_class`/`mop_errors` match the offline regen reference within `0.01` (locks behavior to the validated `scripts/regenerate_results/` pipeline). Truncate each fixture logcat to the `RVSEC`/`RVSEC-COV` lines actually exercised and subset each SA JSON to the referenced classes/methods to keep the repo footprint small
- [ ] 3b.2 Mark with `@pytest.mark.regression` if the fixture set is large; ensure it runs in the default (non-slow) suite if small

## 4. Offline tooling residual (D-4 — scripts/regenerate_results)

- [ ] 4.1 In `scripts/regenerate_results/verify.py`, extend C3 to validate `cov_class` (summary ↔ last coverage row) and remove the stale comment claiming `cov_class` duplicates `cov_method` (INV-PLT-17). Note: the `cov_class` write fix and script versioning already landed in `b2bc5aa9`
- [ ] 4.2 Run `verify.py` against an existing regen output to confirm C3 passes with `cov_class` included

## 5. Integration, docs & verification

- [ ] 5.1 Run `/rv-qa-lint-fix rv-platform` and `/rv-qa-lint-fix rv-android-core`
- [ ] 5.2 Run `/rv-verify rv-platform` and `/rv-verify rv-android-core`
- [ ] 5.3 Update `modules/rv-platform/CLAUDE.md` "MOP Violation Reconstruction" section (currently describes pre-gh58 "writes a single summary row using `coverage_metrics`") and remove/refresh `experimento-20260604/CLAUDE.md` gotcha #7 (D4)
- [ ] 5.4 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 5.5 Run `/rv-docs-sync rv-platform` (CLAUDE.md + spec invariants alignment)

## 5b. Real E2E across both entry points (G8 — Phase 5 / Verify; tool-managed emulator)

> The tools own the emulator lifecycle. NEVER run `emulator`, `adb emu kill`, or any emulator command
> manually (CLAUDE.md). Interrupt only the rv-experiment/rv-platform **process** (SIGINT/SIGTERM).
> Fixed for G8: APK = `apks_examples/cryptoapp.apk` (guarantees RVSEC-COV + RVSEC when instrumented);
> tool = `ape` (default variant). Use `--repetitions 2` (or timeouts `60,120`) for ≥2 tasks.

- [ ] 5b.1 **rv-experiment `--name` implicit resume + forced skip-static** (case 1/4/6): `rv-experiment run --tools ape --apks-dir apks_examples --name e2e_resume --repetitions 2` (run 1 does Phase 1 = instrument + static analysis + monitors); after ≥1 task completes, SIGINT the process; re-run the identical command (resume forces `--skip-monitors/--skip-instrument/--skip-static`); assert consolidated `summary.csv` has non-zero `cov_method` + correct `mop_errors_*` for BOTH the pre-interrupt and post-resume tasks, that coverage was reconstructed from the JSON persisted in run 1 via `dirname(logcat)`, and that no new GATOR invocation occurred (platform scenario "Orchestrated Resume Skips Static Analysis but Reuses Persisted JSON")
- [ ] 5b.2 **rv-platform auto-resume** (case 1/4): `rv-platform run --tools ape --apks-dir results/e2e_resume/instrumented_apks` (rv-platform does NOT instrument — reuse the instrumented cryptoapp + co-located JSON from 5b.1); after ≥1 task completes, SIGINT the process; re-run the same command (auto-resume via `tasks.json`); assert both rows non-zeroed
- [ ] 5b.3 **Consolidation-only on real dir** (case 5): `rv-platform run --process-results results/e2e_resume` over the completed run from 5b.1; assert 100% of rows non-zeroed (G6 canary on real data) — this is the exact path that zeroed T=300
- [ ] 5b.4 Record the G8 evidence (row counts, zeroed fraction before/after) in the change's verification notes; confirm G6 canary == 100% on the real consolidated `summary.csv`

## 6. Archive-time caveat (Phase 6 — `/opsx:archive` / `/opsx:sync`)

- [ ] 6.1 **Manual invariant reconciliation**: the OpenSpec delta engine parses only the `### Requirement:` blocks as deltas — the `## Invariants` bullets in `specs/platform/spec.md` are NOT auto-applied. At sync: (a) replace the INV-PLT-15 bullet in the main `openspec/specs/platform/spec.md` with the MODIFIED text from this delta (results_dir derivation + once-per-task unresolved counter); (b) ADD the new INV-PLT-18 bullet (round-trip metric equivalence + loud aggregate WARNING). INV-PLT-16 is **unchanged** (gh58's "no fallback" stands; this delta only restates it for context) — do NOT edit it. INV-PLT-17 is unchanged in the spec (only its offline-tooling reach is exercised by D-4). INV-ANA-25 is unchanged (verified, not amended) — do not edit its bullet
