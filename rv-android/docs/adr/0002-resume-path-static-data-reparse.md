# ADR 0002 — Resume path obtains static_data via on-demand JSON re-parse, not via tasks.json serialization

**Status**: Accepted (gh58, 2026-05-14)

## Context

`ResultProcessorComponent` in `rv-platform` is invoked at two distinct moments:

1. **Real-time**: at the end of each task, while `task.repository` (a `LogcatRepository`) is still alive in memory and `task.static_data` (a `StaticAnalysisData`) was already loaded by `StaticAnalysisComponent` earlier in the same task lifecycle.
2. **Resume / post-hoc**: when an experiment is re-run after a crash, OOM kill, or preemption — `Platform.run()` loads tasks from `tasks.json` and calls `ResultProcessorComponent` on the consolidated set. Tasks that were completed in a previous session have `task.repository is None` (LogcatRepository is runtime-only, never serialized) and `task.static_data is None` (not serialized either).

Before gh58, the resume path called `parse_logcat_file(logcat_file)` without `static_data`. With `static_data=None`, `LogcatRepository.classes` stays empty, `register_method_call` silently no-ops for every `RVSEC-COV` entry, and `calculate_metrics().to_dict()` returns zero for every method-based coverage metric. Only `RVSEC` (MOP violations) entries survived because `register_rv_error` does not depend on static data. The CSV writers compounded the damage with degraded fallback paths that emitted empty `class/method/signature` rows or pulled stale percentages from `task.result.coverage_metrics` (the only piece of coverage state that *is* serialized in `tasks.json`).

The experiment `experimento-20260508` (18,770 tasks, 4 GCP VMs, 85 h) made the impact tangible: 1,315 tasks lost their summary row, 759,630 coverage rows had empty `class/method/signature`, and `cov_method` collapsed to `cov_rv_method` for every resumed task. The offline regeneration tooling (`scripts/regenerate_results/`) re-parsed each task's static-analysis JSON on demand to reconstruct the correct CSVs — establishing empirically that the JSON is sufficient input for full coverage reconstruction.

The question for the upstream fix is: **how should the resume path obtain `static_data`?**

PRD references: FR10 (result consolidation), FR12 (coverage metrics), NFR03 (experiment reproducibility), NFR08 (resume durability).

## Decision

**The resume path obtains `static_data` by re-parsing the static-analysis JSON on demand inside `ResultProcessorComponent._reconstruct_repository_from_logcat`.**

A new private helper `_resolve_static_data(task)` returns `task.static_data` when already set; otherwise it calls `static_analysis_parser.read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)` — exactly the same triple that `StaticAnalysisComponent.load_static_data` uses in the real-time path. The result is cached back on `task.static_data` so repeated invocations within a single `execute()` call do not re-parse. If the JSON is absent or unreadable, the helper logs a warning and returns `None`; `parse_logcat_file` is still invoked but with `static_data=None`, leaving `RVSEC` violations reliable and the per-method coverage explicitly zero (auditable, not silent).

`tasks.json` is **not** extended to carry `static_data`.

## Alternatives Considered

**A. Serialize `StaticAnalysisData` into `tasks.json`.** Rejected. Each APK's `reachability` section contains hundreds to thousands of class/method entries; serializing one `StaticAnalysisData` per task inflates `tasks.json` by megabytes per task. For a 18,000-task campaign this would produce a multi-gigabyte tasks.json — slow to load on every resume, expensive to write atomically, and brittle when the `StaticAnalysisData` schema evolves (the domain model would become coupled to a persistence contract). The JSONs already live on disk in `task.results_dir`; duplicating them inside the task ledger violates P1 (Simplicity).

**B. Require `StaticAnalysisComponent` to run before any reconstruct path.** Rejected. `ResultProcessorComponent` is also invoked in standalone mode via `rv-platform run --process-results <results_dir>`, which loads `tasks.json` without going through the full execution lifecycle. Forcing `StaticAnalysisComponent` to run in that path would couple a pure post-processing CLI to the runtime setup chain and break the `--skip-result-processing` / standalone re-run use case documented in FR14.

**C. Move reconstruction logic to the offline regen script and accept degraded upstream output.** Rejected. The regen tooling proved the approach works but lives outside the platform; future campaigns would continue to produce corrupt CSVs by default, with the regen as a manual repair step. The fix belongs upstream so resume produces correct output by construction (NFR03 Reproducibility).

## Consequences

**Positive.**

- Resume-path output is byte-equivalent (in column semantics) to single-session output. Per-method coverage rows in `coverage.csv` and aggregate rows in `summary.csv` are populated for every task that has both a logcat file and a static-analysis JSON.
- The legacy cascade fallbacks in `_write_task_coverage_data` (Branch 2 empty-row) and `_write_task_summary_data` (3-tier `coverage_metrics → repository → zeros`) become unreachable dead code and are deleted (INV-PLT-16, P3 No Backward Compatibility).
- The pre-existing bug at the old `result_processor.py:322` (writing `method_coverage` into the `cov_class` slot) is fixed incidentally — both writers now read `class_coverage` from `CoverageMetrics.to_dict()` (INV-PLT-17).
- The extended CSV schema (cov_class, cov_reachable, cov_reaches_target, cov_directly_reaches_target, mop_errors_total, mop_errors_unique) becomes the persistent contract; the offline regen tooling and the platform converge on the same schema.

**Negative.**

- Resume incurs ~50–200 ms of disk I/O per task for the re-parse. For an 18,000-task resume this adds ~5–60 minutes, dominated by SSD read latency. Memoization on `task.static_data` ensures one parse per task within a single `execute()` call. Trade-off accepted: resume is the exceptional path; tool execution timeouts dwarf the parse cost.
- Standalone `rv-platform run --process-results <dir>` now requires the static-analysis JSONs to be co-located with the persisted logcats in each task's `results_dir`. This is already the case for any campaign run through `Platform.run()` (the `StaticAnalysisComponent.copy_static_analysis_files` step copies them into `task.results_dir` before execution), but campaigns that move CSVs without the JSON sidecars will see zeroed coverage and a warning log.

## Verification

- Regression test `TestGh58ReconstructWithStaticData::test_reconstruct_repository_from_logcat_populates_coverage_with_static_data` (RED before the fix, GREEN after) — uses a real fixture logcat + minimal 30-method JSON.
- Helper-level tests `TestGh58ResolveStaticData::test_resolve_static_data_{reuses_task_attribute, returns_none_when_json_missing, tolerates_task_app_none}` cover the cache hit, JSON missing, and `task.app is None` paths.
- Slot-fix tests `TestGh58CovClassSlotFix::test_{coverage,summary}_csv_cov_class_uses_class_coverage_not_method_coverage` lock the cov_class column to `class_coverage` and would catch any future regression to the pre-existing bug.
- Pre-existing tests that encoded the removed cascade fallback (`test_coverage_csv_fallback_without_repository`, `test_summary_csv_from_coverage_metrics`, `TestCoverageCSVResumedTasks::test_resumed_task_produces_single_summary_row`, `TestCoverageCSVResumedTasks::test_mixed_live_and_resumed_tasks`) were rewritten as `*_no_rows_when_repository_and_logcat_both_missing` / `*_uses_repository_metrics_only` to assert the corrected contract.
- `openspec validate --strict gh58-result-processor-static-data` PASS.

## References

- GitHub Issue: PAMunb/rvsec#58
- OpenSpec change: `openspec/changes/gh58-result-processor-static-data/`
- Plan: `docs/20260514_regenerar_planilhas.md`
- Experiment report: `experimento-20260508/RELATORIO.md` §2.2
- Offline workaround: `scripts/regenerate_results/` (untracked at the time of writing, to be committed in a separate chore PR)
- Related invariants: INV-PLT-15 (resume re-parse), INV-PLT-16 (no cascade fallback), INV-PLT-17 (cov_class = class_coverage), INV-ANA-25 (parse_logcat_file static_data contract)
