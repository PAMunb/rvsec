# ADR 0003 — Resume path derives `results_dir` from the logcat path; error aggregates counted before the empty-classes early return

**Status**: Accepted (gh65, 2026-06-13)

## Context

ADR 0002 (gh58) established that the resume path obtains `StaticAnalysisData` by re-parsing the static-analysis JSON on demand inside `ResultProcessorComponent`, rather than serializing `StaticAnalysisData` into `tasks.json` (which would inflate the ledger by megabytes per task). That decision stands. The re-parse is performed by `_resolve_static_data(task)`, which calls `read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)`.

The gh58 fix repaired the *mechanism* but rested on an unstated *precondition*: that `task.results_dir` is available when `_resolve_static_data` runs on a resumed task. It is not. `Task.to_dict` serializes only `id/config/result`; `Task.from_dict` → `__init__` leaves `results_dir=""` and `app=None`. On resume, the parser therefore receives an empty `results_dir`, builds a relative non-existent path, and returns an empty `StaticAnalysisData` *without raising* — the failure is silent.

A single root cause then produces three symptoms downstream:

1. Empty `StaticAnalysisData` → `LogcatRepository.classes` is empty → `register_method_call` no-ops → per-method coverage is zero in `coverage.csv` (rows empty) and `summary.csv` (`cov_*` = 0).
2. Empty `classes` triggers an early return in `CoverageMetricsRepository.calculate_metrics()` (`coverage.py:593`) that runs **before** the error-count assignments (`coverage.py:623`). This zeroes `mop_errors_total` / `mop_errors_unique` in `summary.csv` — a spec violation: **INV-ANA-25** guarantees that `total_errors` / `unique_errors` stay accurate when `static_data` is absent, because errors are reconstructed independently of static analysis.
3. `errors.csv` survives (it reads `get_errors()` directly), masking the severity in a quick glance at outputs.

The gh58 regression test masked the gap because its fixture (`_make_gh58_task`) set `results_dir` and `app` manually — the exact fields that resume leaves empty. So the test exercised a path that never occurs on a real resume.

The impact is not hypothetical. Resume is the *norm* for the campaigns this project runs: `experimento-20260604` ran 169 APKs across 4 VMs with intensive resume, and every in-container `summary.csv` / `coverage.csv` it produced had coverage and error aggregates zeroed for practically all completed-in-a-prior-session tasks. The data was recovered offline; this change makes **future campaigns produce correct CSVs by construction**.

Phase 0/1 analysis (`docs/20260610_correcao_resume.md`) confirmed the root cause end-to-end and validated the fix empirically: the runtime identity `task.results_dir == os.path.dirname(task.result.logcat_file)`, established in `Task.initialize`, holds; and `os.path.dirname(logcat_file)` resolves both the logcat and its co-located static-analysis JSON for 1299/1299 tasks (0 missing) on `experimento-20260604`.

The question for this fix is: **how should the resume path recover `results_dir` so that the gh58 re-parse precondition is satisfied?**

PRD references: FR10 (persistent task storage / resume), FR12 (method coverage tracking), NFR03 (testability), NFR08 (reproducibility).

## Decision

**The resume path derives `results_dir` from the serialized logcat path: `_resolve_static_data` computes `results_dir = task.results_dir or os.path.dirname(task.result.logcat_file)`.**

This relies on the runtime identity `task.results_dir == os.path.dirname(task.result.logcat_file)`, which `Task.initialize` establishes by placing the logcat directly inside the task's results directory. `logcat_file` *is* serialized in `task.result`, so the exact `results_dir` value is reconstructed on resume with no `tasks.json` schema change. When neither `task.results_dir` nor a `logcat_file` directory is available, `_resolve_static_data` logs and increments an unresolved-task counter and returns `None`; the parser does not raise on a missing file, so the empty-data path is treated explicitly as "JSON absent" and counted (the existing `except` remains as a backstop for genuinely unexpected failures).

Two related decisions accompany the primary one:

- **Error aggregates are counted before the empty-`classes` early return.** In `CoverageMetricsRepository.calculate_metrics()`, the `metrics.total_errors` / `metrics.unique_errors` assignments move ahead of `if not self.classes: return metrics`. This makes `to_dict()["total_errors"]` accurate in the legitimate degraded case (logcat present, JSON genuinely absent — e.g. a `--skip-static` run), bringing the code into conformance with the already-written **INV-ANA-25**. Errors are independent of static analysis, so the populated path is unchanged (it counts the same values, just earlier).

- **The no-fallback rule (INV-PLT-16) is reconciled to "no *silent* fallback".** When logcat is present but the JSON is genuinely absent, falling back to the serialized `task.result.coverage_metrics` for the fields it carries is permitted, gated behind an explicit per-task log and a counter surfaced in aggregate. This is distinct from the silent 3-tier cascade gh58 deleted: it is observable and bounded. When neither reconstruction nor serialized metrics are available, a zeroed row is emitted with a warning.

ADR 0002 remains valid in full: `StaticAnalysisData` is still **not** serialized into `tasks.json`; the re-parse-on-demand mechanism is unchanged. ADR 0003 corrects only the precondition that the re-parse depends on.

## Alternatives Considered

**A. Derive `results_dir` from `os.path.dirname(task.result.logcat_file)` (chosen).** Uses already-serialized data and the runtime identity established in `Task.initialize`, reconstructing the exact value with no schema change. Inherits the same path relativity as `logcat_file` itself — portable inside the container, resolvable on the same machine outside. Minimal (P1) and validated on 1299/1299 tasks. Trade-off: depends on the `results_dir == dirname(logcat_file)` identity holding; if a future change relocates logcats away from the results directory, the derivation breaks. Mitigated by the identity being a single, testable construction point in `Task.initialize`.

**B. Serialize `results_dir` into `tasks.json`.** Rejected. More general, but it mutates the `tasks.json` schema and must handle container-absolute paths (`/rvandroid/...`) that do not exist outside the container — the very paths a resume on a different host or a post-hoc offline run cannot resolve. It also re-opens the persistence-size and schema-coupling concern that ADR 0002 weighed for `StaticAnalysisData`: extending the serialized task contract with derived runtime state is exactly the coupling P1 and ADR 0002 sought to avoid. Option A obtains the same value from data already present, so Option B's generality buys nothing the resume path needs.

**C. Re-introduce a static-data-independent coverage fallback (revert part of gh58).** Rejected. The gh58 cascade was deleted deliberately (INV-PLT-16) because it silently emitted degraded rows that looked plausible. Reverting it would re-corrupt outputs by construction. The auditable, counted fallback in this ADR is the bounded alternative: it covers only the genuinely-absent-JSON case, is logged per task, and surfaces an aggregate counter so wide zeroing is visible rather than silent.

## Consequences

**Positive.**

- Resume-path `summary.csv` and `coverage.csv` carry correct `cov_*` and `mop_errors_*` by construction, with no offline regeneration step required for future campaigns.
- `calculate_metrics()` error aggregates survive the empty-`classes` case, conforming to INV-ANA-25. The `--skip-static` degraded path now reports accurate `total_errors` / `unique_errors`.
- The regression test exercises the *real* resume precondition (`Task.from_dict(Task.to_dict())` round-trip with `results_dir=""`), closing the gap the gh58 fixture masked. Any future change that drops `results_dir` recovery will fail this test.
- No `tasks.json` schema change: existing ledgers from prior campaigns remain readable, and the resume contract stays minimal.
- `cov_class` in `coverage.csv` becomes reliable rather than aliasing `cov_method` (the write fix landed in `b2bc5aa9`; `verify.py` C3 now validates it under INV-PLT-17).

**Negative.**

- The derivation is coupled to the `task.results_dir == os.path.dirname(task.result.logcat_file)` identity. If a future change writes logcats outside the results directory, `_resolve_static_data` will derive the wrong directory and silently zero coverage again. The coupling is a single construction point in `Task.initialize` and is covered by a unit test, but it is an implicit contract that must be kept.
- The auditable fallback to serialized `coverage_metrics` could, in principle, mask a systemic JSON-absence across many tasks. Mitigated by the aggregate unresolved-task counter surfaced in the processing log: a wide zeroing is visible, not silent.

**Neutral.**

- INV-PLT-16 is reframed from "no fallback" to "no *silent* fallback" — a clarification of intent, not a loosening: the silent cascade gh58 removed stays removed; only an observable, counted fallback is allowed.

## Verification

- Unit: `calculate_metrics` counts errors with empty `classes`; the reported count equals `get_errors()` length (INV-ANA-25 conformance, `test_metrics_empty_classes_counts_errors`).
- Unit: `_resolve_static_data` derives the directory from `logcat_file`, returns non-empty `StaticAnalysisData` when the co-located JSON exists, and increments the unresolved counter when it is missing (`test_resolve_static_data_derives_dir_from_logcat`, `test_missing_json_counts_and_errors_survive`).
- Integration: real resume via `Task.from_dict(Task.to_dict())` with `results_dir=""` and a co-located JSON asserts `cov_method > 0` and `total_errors > 0` in the summary row (`test_resume_roundtrip_coverage_nonzero`) — the test the gh58 fixture could not produce.
- Integration: auditable fallback logs and counts, and emits a zeroed row when nothing is available (`test_auditable_fallback_logs_and_counts`).
- Offline: `scripts/regenerate_results/verify.py` C3 validates `cov_class` on regenerated CSVs.

## References

- GitHub Issue: PAMunb/rvsec#65 (follow-up of #58)
- OpenSpec change: `openspec/changes/gh65-resume-static-data-resolution/`
- Phase 0/1 analysis: `docs/20260610_correcao_resume.md`
- Revisits (partially): `docs/adr/0002-resume-path-static-data-reparse.md` — ADR 0002 stays valid (no `StaticAnalysisData` serialization); ADR 0003 fixes the re-parse precondition only.
- Affected code: `modules/rv-platform/src/rv_platform/components/result_processor.py` (`_resolve_static_data`), `modules/rv-android-core/src/rv_android_core/domain/coverage.py` (`calculate_metrics`), `scripts/regenerate_results/verify.py` (C3)
- Related invariants: INV-PLT-15 (resume obtains static_data — now states the `results_dir` precondition and how resume satisfies it), INV-PLT-16 (no *silent* fallback), INV-PLT-17 (cov_class = class_coverage, extended to offline tooling), INV-ANA-25 (calculate_metrics error aggregates independent of static_data)
