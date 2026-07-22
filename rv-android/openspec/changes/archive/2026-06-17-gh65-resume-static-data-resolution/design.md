## Context

GitHub Issue #65 (follow-up of #58). gh58 made the resume path re-parse the static-analysis JSON on demand (`_resolve_static_data` → `read_static_analysis_files(results_dir, apk, code_package)`), but the JSON path is built from `task.results_dir`, which is not serialized in `tasks.json`. On resume, `Task.from_dict()` → `__init__` leaves `results_dir=""` and `app=None`, so the parser builds a relative non-existent path and returns empty `StaticAnalysisData` (no exception). Empty `classes` then triggers an early return in `CoverageMetricsRepository.calculate_metrics()` that zeroes coverage **and** error aggregates. Symptoms: `summary.csv` `cov_*` and `mop_errors_*` = 0, `coverage.csv` empty; `errors.csv` survives (reads `get_errors()` directly).

The Phase 0/1 analysis (`docs/20260610_correcao_resume.md`) confirmed the root cause end-to-end in code and validated the fix empirically on `experimento-20260604` (4 VMs, 169 APKs): the runtime identity `task.results_dir == os.path.dirname(task.result.logcat_file)` holds, and `dirname(logcat_file)` resolves both logcat and co-located JSON for 1299/1299 tasks (0 missing). Relevant requirements: FR10 (resume), FR12 (coverage), NFR03 (testability), NFR08 (reproducibility).

## Architecture

```
Platform._process_results()
  └─ TaskStorage.get_completed_tasks()        # all sessions; resumed tasks have results_dir="", app=None
       └─ ResultProcessorComponent
            ├─ _resolve_static_data(task)              [rv-platform]   ← Option A: derive results_dir from logcat dirname
            │    └─ static_analysis_parser.read_static_analysis_files(<dir>, apk, code_package)  [rv-static-analysis]
            ├─ _reconstruct_repository_from_logcat(task)
            │    └─ parse_logcat_file(logcat, static_data)             [rv-coverage]
            └─ _write_task_summary_data / _write_task_coverage_data
                 └─ repository.calculate_metrics().to_dict()           [rv-android-core/coverage.py] ← D5: count errors before early-return
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `result_processor._resolve_static_data` | Derive per-APK dir, re-parse SA JSON, memoize, count unresolved | `task` (resumed: `results_dir=""`) | `StaticAnalysisData` or `None` |
| `coverage.CoverageMetricsRepository.calculate_metrics` | Compute metrics; error aggregates independent of `classes` | repository state | `CoverageMetrics` |
| `result_processor._write_task_summary_data` | Summary row; zeroed row + warning when reconstruction fails (no serialized fallback) | `task`, populated `repository` | `summary.csv` row |
| `verify.py` C3 (offline) | Cross-check `cov_class` summary↔coverage | regen CSVs | PASS/FAIL |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-PLT-15 (derive results_dir) | `_resolve_static_data`: `results_dir or os.path.dirname(task.result.logcat_file)` | `test_resolve_static_data_derives_dir_from_logcat` |
| Scenario: Resume After tasks.json Round-Trip | `_resolve_static_data` + `_reconstruct_repository_from_logcat` | `test_resume_roundtrip_coverage_nonzero` |
| INV-PLT-15 (counter once per task) | `_resolve_static_data`: empty `StaticAnalysisData` memo + `_unresolved_task_ids` set | `test_unresolved_counter_increments_once_per_task` |
| INV-PLT-15 / D-3a (accounting integrity) | two-field split + memo short-circuit; counter reset per `execute()` | `test_d3a_accounting_matrix` (G9, parametrized: writer-order × task-state, parser spy `call_count`) |
| INV-ANA-25 / Error Aggregates Independent | `calculate_metrics`: count errors before `if not self.classes` | `test_metrics_empty_classes_counts_errors` |
| Scenario: Static Analysis JSON Missing on Resume | `_resolve_static_data` warning + counter | `test_missing_json_counts_and_errors_survive` |
| INV-PLT-18 (round-trip equivalence) | `from_dict(to_dict)` reconstruct == live metrics | `test_roundtrip_metric_equivalence` (G1, parametrized) |
| INV-PLT-18 (loud signal) | aggregate health-check WARNING in `execute()` | `test_resume_health_check_warning` (G4) |
| Scenario: Two-session resume / canary | `Platform.run()` ×2 with stub tool | `test_e2e_two_session_resume` (G2/G6) |
| INV-PLT-17 (offline cov_class) | `verify.py` C3 adds `cov_class` | offline `verify.py` run |

## Goals / Non-Goals

**Goals:**
- Resume produces correct `cov_*` and `mop_errors_*` in in-container CSVs by construction.
- `calculate_metrics()` error aggregates conform to INV-ANA-25 (survive empty `classes`).
- A regression test that exercises the **real** resume precondition (`results_dir=""`), which the gh58 fixture masked.
- `verify.py` C3 validates `cov_class` (residual; the write fix already landed in `b2bc5aa9`).

**Non-Goals:**
- Changing the `tasks.json` schema (Option B rejected — see Decisions).
- Re-introducing the silent 3-tier cascade gh58 deleted, or any fallback to serialized `coverage_metrics` (D-3 rejected — conflicts with INV-PLT-17 / verify.py C3).
- Re-running `experimento-20260604` (data already consolidated offline).
- Touching `parse_logcat_file`/rv-coverage API, instrumentation, or the execution pipeline.

## Decisions

**D-1: Derive `results_dir` from the logcat path (Option A) rather than serializing it (Option B).**
Option A uses already-serialized data (`task.result.logcat_file`) and the runtime identity `task.results_dir == os.path.dirname(task.result.logcat_file)`, so it reconstructs the *exact* value with no schema change. Option B (serialize `results_dir`) is more general but mutates `tasks.json`, must handle container-absolute paths (`/rvandroid/...`) that don't exist outside the container, and re-opens the storage-size concern ADR 0002 weighed. Option A is minimal (P1) and validated on 1299/1299 tasks. **This partially revisits ADR 0002** — recorded in an ADR.

**D-2: Count error aggregates before the empty-`classes` early return.**
`calculate_metrics()` returns `CoverageMetrics()` early when `self.classes` is empty, before `metrics.total_errors = len(self.errors)`. Moving the two error-count assignments before that early return makes `to_dict()["total_errors"]` accurate in the degraded case, conforming to the already-written INV-ANA-25. Errors are independent of static analysis, so this is correct in all paths (the populated path is unchanged — it counts the same values later).

**D-3: No fallback to serialized `coverage_metrics` (INV-PLT-16 unchanged).**
A fallback to serialized `task.result.coverage_metrics` was considered and **rejected**. It conflicts with INV-PLT-17 / `verify.py` C3: the serialized value is an aggregate summary with no per-method rows, so it would populate `summary.csv` `cov_*` (non-zero) while `coverage.csv` stays empty — exactly the `summary != 0 with coverage_rows = 0` inconsistency C3 flags as a failure (`result_processor.py` writes `coverage.csv` per-method rows only from a populated repository; the serialized metrics cannot produce them). Its one value scenario (run 1 had static data, the JSON was deleted before resume) is marginal and explicitly out of scope — offline data is already consolidated. So when logcat is present but the JSON is genuinely absent, both writers emit a **zeroed row with an explicit per-task warning**, and the unresolved-static-data counter (D-3a) drives one aggregate WARNING (G4). gh58's removal of the silent cascade stands; INV-PLT-16 is not amended.

**D-3a: The unresolved-static-data counter increments at most once per task, via two separated responsibilities.**
The three reconstruction call sites (`_write_task_coverage_data`, `_write_task_error_data`, `_extract_task_data`) all guard on `task.repository`, and the first writer (`_generate_coverage_csv`) caches the reconstructed repository — so under the current ordering `_resolve_static_data` runs once per task. To make G4's "exact N" robust against writer reordering, the once-per-task guarantee MUST NOT depend on call ordering. Rather than a single overloaded "sentinel" on `task.static_data` (which is also the value passed to `parse_logcat_file` — an arbitrary sentinel object would crash the parser on re-entry), the design splits the concern into two fields with disjoint roles:

1. **Parse memo — `task.static_data`.** `_resolve_static_data` MUST assign `task.static_data` a *valid* `StaticAnalysisData` on every path, including the unresolved one (an **empty** `StaticAnalysisData()` when the JSON is absent or the parser raises). The empty instance is non-`None`, so the leading `if task.static_data is not None: return ...` guard short-circuits re-entry **without re-parsing** — and it is still a legal argument to `parse_logcat_file` (empty `classes` → zero coverage). This removes the parser-pollution and re-parse failure modes. To the callers, `_resolve_static_data` returns `None` whenever the memo has empty `classes` (so downstream coverage is zeroed), and the populated instance otherwise.
2. **Counted set — `ResultProcessorComponent._unresolved_task_ids: set[str]`.** Counting is a property of the **task**, not of `static_data`. The first resolution that finds empty `classes` adds `task.id` to the set (guarded by membership, so it is idempotent across writers and across writer orderings); `len(self._unresolved_task_ids)` is exactly the `N` surfaced in the G4 aggregate WARNING. The set MUST be (re)initialized at the start of `ResultProcessorComponent.execute()` so a second consolidation pass (G3) reports only that pass.

The exception path MUST also memoize the empty `StaticAnalysisData` (otherwise a re-entry re-parses and re-counts). Observability: because the memo short-circuits re-entry, `read_static_analysis_files` MUST be invoked **at most once per task** across all writers — this is directly assertable via a spy `call_count`, and is the test hook that catches a regression the count alone would miss.

**D-4: Offline tooling scope limited to `verify.py` C3.**
The `cov_class` write fix and the versioning of `scripts/regenerate_results/` already landed in `b2bc5aa9`. Only the residual remains: `verify.py` C3 skips `cov_class` and carries a stale comment. Bring it under the same INV-PLT-17 guarantee.

## API Design

### `_resolve_static_data(self, task) -> Optional[StaticAnalysisData]`

- **Precondition:** `task.config.apk_name` set; `task.result.logcat_file` set for resumed tasks.
- **Behavior:** if `task.static_data is not None`, short-circuit (parse memo — no re-parse). Otherwise `results_dir = task.results_dir or os.path.dirname(task.result.logcat_file)` when `logcat_file` is set; parse, then assign `task.static_data` a valid `StaticAnalysisData` on **every** path (empty `StaticAnalysisData()` when the JSON is absent or the parser raises). When the resolved memo has empty `classes`, add `task.id` to `self._unresolved_task_ids` (membership-guarded — at most once per task) and return `None`; otherwise return the populated instance.
- **Postcondition:** returns non-empty `StaticAnalysisData` when `<dir>/<apk>.json` exists; `None` otherwise, with `task.id` recorded once in `_unresolved_task_ids`. `read_static_analysis_files` is invoked at most once per task across all writers.
- **Error behavior:** parser does not raise on missing file (returns empty data) — the method treats empty `classes` as "JSON absent" and counts it; the `except` backstop for genuinely unexpected failures MUST also memoize the empty `StaticAnalysisData` so it does not re-parse/re-count on re-entry.
- **Lifecycle:** `_unresolved_task_ids` is (re)initialized at the start of `execute()`; `len(_unresolved_task_ids)` is the `N` reported by the G4 aggregate WARNING.

### `calculate_metrics(self, restrict_to_static: bool = True) -> CoverageMetrics`

- **Change:** assign `metrics.total_errors` / `metrics.unique_errors` before `if not self.classes: return metrics`. Postcondition: error aggregates accurate regardless of `classes`; coverage percentages still `0` when `classes` empty.

## Data Flow

Resumed task (`results_dir=""`, `app=None`) → `_resolve_static_data` derives `<dir>=dirname(logcat_file)` → `read_static_analysis_files(<dir>, apk, None)` → non-empty `StaticAnalysisData` → `parse_logcat_file(logcat, static_data)` → populated `LogcatRepository` → `calculate_metrics().to_dict()` → summary/coverage rows with correct `cov_*` and `mop_errors_*`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| JSON absent at derived dir | `_resolve_static_data` | log + increment unresolved counter (once/task); memoize unresolved outcome | errors still reconstructed; coverage zeroed by construction |
| Logcat missing/None | `_reconstruct_repository_from_logcat` | warning; no reconstruction | zeroed row + warning (no serialized fallback) |
| Unexpected parser exception | `_resolve_static_data` `except` | warning (backstop) | `None` |

## Risks / Trade-offs

- [Derived dir wrong if logcat path was rewritten between sessions] → mitigated: identity is established in `Task.initialize` and `logcat_file` is the only path proven resolvable on resume (4285 errors reconstructed from it across the dataset).
- [Wide JSON-absence could pass unnoticed as zero coverage] → mitigated: every unresolved task is counted once and surfaced as one aggregate WARNING (G4 / INV-PLT-18), so systemic zeroing is loud, not silent; with D-3 rejected there is no serialized fallback to hide it.
- [Container-relative vs absolute paths] → Option A inherits the same relativity as `logcat_file` (portable in-container, resolves on the same machine outside), avoiding Option B's absolute-path problem.
- [D-3a "sentinel" ambiguity — a non-`StaticAnalysisData` sentinel on `task.static_data` would crash `parse_logcat_file` on re-entry, or guarding the count on `static_data` alone could double-count/under-count] → mitigated by splitting the two roles (empty `StaticAnalysisData` as parse memo; `_unresolved_task_ids` set for counting), and by G9 asserting the parser spy `call_count` (observable contract), not just the final counter.
- [G8 (real cross-entry-point E2E) is slow/online and not in CI] → accepted: the orchestrated-resume path (case-matrix rows 1/4/6) has no CI net. The structural tripwire is INV-PLT-18 / G1 (round-trip equivalence, in CI), which breaks the instant any runtime field needed for reconstruction is dropped; G8 is run manually in Phase 5 before declaring done.
- [G5 golden fixtures could bloat the repo (real logcats + MB-sized SA JSONs)] → mitigated: truncate each fixture logcat to the `RVSEC` / `RVSEC-COV` lines actually exercised and subset each SA JSON to the referenced classes/methods, keeping the fixture set small enough to run in the default (non-slow) suite.

## Resume Entry Points & Case Matrix

Resume has two entry points across two modules, but a single consolidation path. Both entry points funnel execution and result consolidation through `Platform.run()` → `ResultProcessorComponent` (verified: rv-experiment's `PostProcessor`/`ResultManager` are diagnostic-only — no CSV, no `parse_logcat_file`, no `calculate_metrics`). So the fix in `result_processor.py` + `coverage.py` covers both modules; there is no parallel broken path. The entry points and cases below must each be validated:

| Entry point | Trigger | Pre-processing on resume |
|-------------|---------|--------------------------|
| rv-platform auto-resume | `tasks.json` detected in results dir (no flag) | n/a (platform doesn't run Phase 1) |
| rv-platform standalone consolidation | `--process-results <dir>` | none — pure re-consolidation; ALL tasks from disk |
| rv-experiment implicit resume | `--name <X>` when `results/<X>/tasks.json` exists | forces `--skip-monitors/--skip-instrument/--skip-static` |
| rv-experiment explicit resume | `--resume-dir <path>` | same forcing |

**Case matrix (each MUST keep coverage AND error aggregates correct):**

1. **Crash recovery** — re-run same config; completed tasks skipped, interrupted task re-run from scratch.
2. **Expand** — more `--repetitions`/`--timeout`; old combos skipped, new ones executed.
3. **Multi-pass campaign** — T=60/180/300 sequence (the real `experimento-20260604` shape; the pass that surfaced the T=300 zeroing).
4. **Mid-task interruption** — process killed during a task; that task re-runs, prior tasks resume from `tasks.json`.
5. **Consolidation-only** — `--process-results` over an existing dir; 100% of rows loaded via `from_dict`.
6. **Orchestrated resume with forced `--skip-static`** — rv-experiment resume skips Phase 1; the JSON from run 1 MUST still resolve via `dirname(logcat)` (platform scenario "Orchestrated Resume Skips Static Analysis but Reuses Persisted JSON").
7. **JSON genuinely absent** (edge) — degraded path: coverage zero, errors accurate, loud aggregate signal (G4).

## Validation Criteria (Definition of Done)

Resume has regressed repeatedly because tests set the runtime fields (`results_dir`, `app`, `repository`) that resume actually drops, and because the failure is silent. These gates attack both. The change is NOT done until every gate is green.

- **G0 — Reproduce-first:** the real-resume integration test (G2) MUST fail on the pre-fix code and pass after — committed as a RED→GREEN pair. A test that does not fail on the current code does not exercise the bug (the gh58 fixture's lesson).
- **G1 — Round-trip metric equivalence (INV-PLT-18):** for ≥3 fixtures (MOP-violations, `--skip-static`, normal), `metrics(live task) == metrics(Task.from_dict(Task.to_dict(task)) reconstructed)` for the 6 `cov_*` columns AND `mop_errors_total`/`mop_errors_unique`, tolerance `0.01`. This is the invariant that breaks the instant any runtime field needed for reconstruction is lost.
- **G2 — Two-session E2E (emulator-free):** a stub tool writes a real logcat + co-located SA JSON; session 1 runs task A and persists `tasks.json`; session 2 (resume) loads A from disk via real `from_dict` and runs task B; the consolidated `summary.csv` has both rows with `cov_method > 0` and correct `mop_errors_*`, asserting **specifically the resumed row A**. No emulator — the bug lives entirely in the post-execution serialization→consolidation path.
- **G3 — Consolidation-only pass:** re-processing where ALL tasks are loaded from disk (skip everything) — the path that zeroed T=300 — produces correct CSVs for 100% of rows.
- **G4 — Loud signal (INV-PLT-18, anti-silence):** when ≥1 resumed task has a non-empty logcat but zero reconstructed coverage, `ResultProcessorComponent` emits one prominent aggregate WARNING with the exact `N/M` count; the test asserts the warning fires and `N` is exact.
- **G5 — Golden regression vs offline reference:** on ≥10 sampled real `experimento-20260604` tasks, in-container-style reconstruction matches the offline regen (the validated reference) for `cov_method`/`cov_class`/`mop_errors`, tolerance `0.01`.
- **G6 — Coverage canary:** in the G2/G3 consolidated `summary.csv`, the fraction of tasks-with-`RVSEC-COV` that have `cov_method > 0` MUST be 100% (historical symptom: 4/1055 ≈ 0.4%).
- **G7 — Standard gates:** `/rv-verify` (pytest `not (slow or online or ...)` + black + flake8) green for `rv-platform` and `rv-android-core`; `/opsx:verify` green.
- **G8 — Real E2E across both entry points (Phase 5, tool-managed emulator):** APK = `apks_examples/cryptoapp.apk` (`br.unb.cic.cryptoapp` — deliberately misuses the JCA, so instrumented with JCA specs it guarantees both `RVSEC-COV` coverage and `RVSEC` violations); tool = **`ape`** (default variant `strategy=sata`, `running_minutes=5`). Drive `rv-experiment run --tools ape --apks-dir apks_examples --name <X>` and (separately) `rv-platform run`/`--process-results`; let ≥1 task complete; **interrupt the process** with SIGINT/SIGTERM (NEVER `emulator`/`adb emu kill` — the tools own the emulator lifecycle per CLAUDE.md); re-run the same command to trigger resume; assert the consolidated `summary.csv`/`coverage.csv` carry non-zero `cov_method` AND correct `mop_errors_*` for BOTH the pre-interrupt and post-resume tasks. Use `--repetitions 2` (or timeouts `60,120`) so there are ≥2 tasks to interrupt between. Covers case-matrix rows 1, 4, 6 on the real stack; rows 2/3/5 covered by the faster G2/G3 test-double tests (synthetic fixtures, not a real tool). G8 is slow/online — not in CI; executed manually in Phase 5 before declaring done.

- **G9 — Unresolved-accounting integrity (D-3a, anti-double-count):** a single parametrized matrix over the cartesian product of {all permutations of the three writers} × {JSON populated, JSON absent, JSON present-but-empty, parser raises} MUST assert, for one task per cell: (a) `len(_unresolved_task_ids) == (1 if unresolved else 0)`; (b) the parser spy `read_static_analysis_files.call_count <= 1` (memo holds → no re-parse, including on the exception path); (c) re-entry produces a valid zeroed repository, never an exception (no sentinel pollution); and (d) a second `execute()` pass re-initializes the counter (idempotent — protects G3 reprocessing). The JSON-populated cell pins the resolved↔unresolved distinction (`call_count` may be 1, counter 0). G9 is the hard pass/fail for D-3a; it is what makes "exact N" robust against writer reordering rather than incidental to the current call order.

## Testing Strategy

| Gate | Layer | What to test | How | Count |
|------|-------|-------------|-----|-------|
| G1 | Unit | Round-trip metric equivalence (live vs `from_dict(to_dict)` reconstructed) over 3 fixtures | parametrized over logcat+JSON fixtures | ~3 |
| D-2 | Unit | `calculate_metrics` counts errors with empty `classes`; error count == `get_errors()` | direct repository construction | ~2 |
| D-1 | Unit | `_resolve_static_data` derives dir from logcat; non-empty data; counts unresolved on missing JSON | tmp dir with/without co-located JSON | ~3 |
| G2/G0 | Integration | Two-session resume via stub tool: session1→`tasks.json`→session2 resume; assert resumed row non-zeroed (RED on pre-fix) | `Platform.run()` twice, no emulator | ~2 |
| G3/G6 | Integration | Consolidation-only pass (all tasks from disk); canary: 100% of RVSEC-COV tasks have `cov_method>0` | reprocess persisted `tasks.json` | ~2 |
| G4 | Integration | Aggregate health-check WARNING fires with exact `N`; silent when N=0 | caplog assertion, missing-JSON mix | ~2 |
| G9 | Unit | D-3a integrity: writer-order × task-state matrix; counter once/task, parser spy `call_count<=1`, no re-entry crash, counter resets per `execute()` | parametrized matrix + `read_static_analysis_files` spy | ~1 (parametrized) |
| G5 | Regression | Golden: ≥10 real 20260604 tasks reconstruct == offline regen (logcats truncated to exercised lines, SA JSONs subset to referenced classes) | fixtures sampled from real data | ~1 |
| INV-PLT-17 | Offline | `verify.py` C3 validates `cov_class` | run on regen CSVs | n/a (script) |

## Open Questions

None — all decisions locked in Phase 0/1 (`docs/20260610_correcao_resume.md §0`).
