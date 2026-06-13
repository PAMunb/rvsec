## Why

GitHub Issue: #65 (follow-up of #58).

The gh58 change fixed the *mechanism* by which the resume path reconstructs per-method coverage (on-demand re-parse of the static-analysis JSON via `_resolve_static_data`), but the *precondition* fails on real resume: `Task.results_dir` and `Task.app` are **not serialized** in `tasks.json` (`Task.to_dict` writes only `id/config/result`). On resume, `Task.from_dict` → `__init__` leaves `results_dir=""` and `app=None`. As a result, every in-container `summary.csv`/`coverage.csv` produced during a campaign that uses resume (the norm: `experimento-20260604` ran 169 APKs across 4 VMs with intensive resume) has coverage zeroed for practically all tasks. The data was recovered offline, so this is not a rescue — it is to make **future campaigns produce correct CSVs by construction**.

A single root cause produces three symptoms, and one of them is a documented spec violation: when `static_data` is empty, `repository.classes` is empty, so `CoverageMetrics.calculate_metrics()` takes an early return (`coverage.py:593`) **before** counting errors (`coverage.py:623`). This zeroes `mop_errors_total/unique` in `summary.csv` too — violating **INV-ANA-25**, which guarantees that `total_errors`/`unique_errors` remain accurate when `static_data` is absent.

## What Changes

- **`result_processor._resolve_static_data`**: when `results_dir` is empty/None, derive it from `os.path.dirname(task.result.logcat_file)` (Option A — `logcat_file` *is* serialized and, at runtime, `task.results_dir == os.path.dirname(task.result.logcat_file)`). No `tasks.json` schema change.
- **Auditable fallback + accounting**: when the logcat/JSON are genuinely absent, fall back to the serialized `task.result.coverage_metrics` with an explicit log and a counter of affected tasks — reconciling INV-PLT-16 as "no *silent* fallback" rather than "no fallback". The silent `warning` becomes a counted, surfaced outcome.
- **`coverage.calculate_metrics`**: count `total_errors`/`unique_errors` **before** the `if not self.classes` early return, so error aggregates survive the legitimate degraded case (logcat present, JSON genuinely absent, e.g. `--skip-static`) — bringing the code into conformance with INV-ANA-25.
- **Regression test**: exercise the real resume path (`Task.from_dict(Task.to_dict())` round-trip, `results_dir=""`, logcat + co-located JSON present) and assert `cov_method > 0` and `errors > 0`. The gh58 fixture masked the gap by setting `results_dir`/`app` manually.
- **`scripts/regenerate_results/verify.py` C3**: check `cov_class` (residual; the `cov_class` write fix already landed in `b2bc5aa9`). Remove the stale comment that claims `cov_class` duplicates `cov_method`.
- **Docs/invariants sync**: update `rv-platform/CLAUDE.md` (pre-gh58 description), `experimento-20260604/CLAUDE.md` gotcha #7; revisit INV-PLT-15/16/17 and INV-ANA-25.

No **BREAKING** changes: CSV column names are unchanged; `cov_class` in `coverage.csv` becomes reliable rather than aliasing `cov_method`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `platform`: INV-PLT-15 (resume obtains static_data — must state the `results_dir` precondition and how it is satisfied on resume); INV-PLT-16 (the no-fallback rule — reconcile to "no *silent* fallback", allowing an auditable, counted fallback); INV-PLT-17 (`cov_class = class_coverage` — extend the guarantee's reach to the offline tooling).
- `analysis`: ADDS a requirement "Error Aggregates Are Independent of Static Analysis Data" (the testable expression of INV-ANA-25: `calculate_metrics()` counts `total_errors`/`unique_errors` before the empty-`classes` early return) and MODIFIES "Logcat-Based Repository Reconstruction Requires Static Data for Coverage" to assert that those aggregates stay accurate when `static_data` is absent. INV-ANA-25 itself is verified, not amended — the early-return fix makes the code conform to the already-written invariant.

## Impact

**Modules:**
- `rv-platform` — `components/result_processor.py` (`_resolve_static_data`: Option A + auditable fallback/accounting); `tests/components/test_result_processor.py` (real-resume regression test, revise `_make_gh58_task`); `tests/execution/test_resume*.py` (integration coverage).
- `rv-android-core` — `domain/coverage.py` (`calculate_metrics`: count errors before the early return). **Not** `domain/task.py` (Option A avoids serializing `results_dir`).

**Tooling (outside `modules/`):**
- `scripts/regenerate_results/verify.py` (C3 cov_class check). `regenerate_container.py` and the scripts directory are already committed (`b2bc5aa9`).

**Not touched:** `parse_logcat_file`/`rv-coverage` API; `rv-experiment`; `tasks.json` schema; instrumentation; execution pipeline.

**Requirements:** FR10 (Persistent Task Storage / resume), FR12 (Method Coverage Tracking), NFR03 (Testability — the regression test that closes the gh58 gap), NFR08 (Reproducibility — CSVs correct by construction across resume).

**Cross-module:** the fix spans `rv-platform` (consumer) and `rv-android-core` (`coverage.py`), and touches two spec domains (`platform`, `analysis`). ADR 0002 (resume reparse, gh58) is revisited — partially superseded by the `results_dir`-derivation decision.

**Resume entry points (validation scope, not fix scope):** resume has two entry points — rv-platform (auto-detect `tasks.json`; `--process-results`) and rv-experiment (`--name` implicit, `--resume-dir` explicit, both forcing `--skip-monitors/--skip-instrument/--skip-static`) — but a **single consolidation path**: rv-experiment delegates all result processing to `Platform.run()` → `ResultProcessorComponent` (its `PostProcessor`/`ResultManager` are diagnostic-only — no CSV, no `parse_logcat_file`, no `calculate_metrics`). The fix in `result_processor.py`/`coverage.py` therefore covers both modules with no parallel path. `rv-experiment` is touched only as a validation surface (the real E2E gate G8 drives both entry points; the orchestrated resume's forced `--skip-static` must still resolve the JSON persisted from run 1 via `dirname(logcat)`).
