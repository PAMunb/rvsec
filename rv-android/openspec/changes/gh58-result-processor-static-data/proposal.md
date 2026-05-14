# Proposal — gh58: result_processor resume path obtains static_data via on-demand JSON re-parse

GitHub Issue: #58

## Why

The experiment `experimento-20260508` (18,770 tasks across 4 GCP VMs over 85 hours) produced the consolidated `summary.csv`, `coverage.csv`, and `errors.csv` with severe data corruption: 1,315 tasks had no summary row, 759,630 coverage rows had empty `class/method/signature`, and `cov_method` collapsed to `cov_rv_method` for resumed tasks. The root cause is `ResultProcessorComponent` in `rv-platform`: whenever a task is loaded from `tasks.json` on resume (`task.repository is None`), the result writer either calls `parse_logcat_file(logcat_file)` without `static_data` (so `LogcatRepository.classes` is empty and `register_method_call` silently no-ops), or takes a degraded Branch 2 fallback that writes empty per-method coverage rows and reads stale percentages from `task.result.coverage_metrics`. Any future campaign using resume — which is the norm given OOM/preemption — produces the same corrupt CSVs. The offline regeneration script (`scripts/regenerate_results/`, verified 2026-05-14 with C1–C4 PASS) demonstrated that the static-analysis JSON can be re-parsed on demand to fully reconstruct per-method coverage; this proposal promotes that fix upstream and updates the CSV contract to the ASE-Journal schema the workaround already produces. Relates to FR10 (result consolidation), FR12 (coverage metrics), and NFR03 (reproducibility of experiment outputs).

## What Changes

- `ResultProcessorComponent._reconstruct_repository_from_logcat` re-parses the static-analysis JSON on demand via `static_analysis_parser.read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)` and passes the resulting `StaticAnalysisData` to `parse_logcat_file`. Same triple already used by `StaticAnalysisComponent.load_static_data`. The parser tolerates `package=None` (uses `if package and package not in normalized`), so missing `task.app` is safe.
- **BREAKING** (CSV schema, positional readers break): `summary.csv` grows from 8 columns to 13 columns and reorders to `apk, rep, timeout, tool, cov_act, cov_class, cov_method, cov_rv_method, cov_reachable, cov_reaches_mop, cov_directly_reaches_mop, mop_errors_total, mop_errors_unique`. The `errors` column (position 7 in the old schema) is renamed to `mop_errors_total` and a sibling `mop_errors_unique` is added. `cov_class` is inserted at position 5 (between `cov_act` and `cov_method`), so any downstream reader using positional indexing past column 4 sees shifted semantics. Header-based readers (pandas default) get the new columns transparently. The new column order matches the schema already produced by `scripts/regenerate_results/` (validated against 18,267 logcats), so the platform output and the offline regen tooling converge on a single schema.
- **BREAKING** (CSV schema, positional readers safe): `coverage.csv` grows from 12 columns to 15 columns with the three new columns `cov_reachable, cov_reaches_mop, cov_directly_reaches_mop` appended after the existing 12. Existing positional readers continue to work for columns 0-11.
- **Behavioral fix** (incidental, not a column rename): in the old code's Branch 1 of `_write_task_coverage_data`, the `cov_class` slot was being written with `method_coverage` (a pre-existing bug — `result_processor.py:322` reads `round(method_coverage, 2)`). After this change, `cov_class` MUST be `class_coverage` from `CoverageMetrics.to_dict()`. Captured as an explicit value-level scenario in the spec and a regression test.
- **REMOVED** (P3, no backward compat): the cascade fallbacks in `_write_task_coverage_data` (the `else` branch at lines ~332–348 that emitted empty `class/method/signature` rows) and `_write_task_summary_data` (the 3-tier cascade at lines ~518-540: primary `task.result.coverage_metrics`, secondary `task.repository.calculate_metrics()`, tertiary zeros). Both writers are unified to a single path that reads from `task.repository.calculate_metrics().to_dict()` after `_reconstruct_repository_from_logcat` ensures `task.repository` is populated. When the logcat file itself is missing (the only remaining degenerate case), the writers emit a single zeroed row with an explicit warning log. No silent fallback to stale serialized metrics.
- New regression test `test_reconstruct_repository_from_logcat_populates_coverage_with_static_data` in `modules/rv-platform/tests/components/test_result_processor.py`: uses a real fixture logcat and minimal static JSON, asserts `len(repo.get_method_calls()) > 0` and `metrics["method_coverage"] > 0`. Designed to fail against the pre-fix code (RED).
- New ADR in `docs/adr/` documenting the design decision: resume path obtains `static_data` via on-demand JSON re-parse, not via serialization in `tasks.json`.

Out of scope (explicit): committing `scripts/regenerate_results/` (separate chore PR after gh58 merges); renaming `_regen.csv → _all.csv` in the external `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/` tree (manual operation by the researcher).

## Capabilities

### New Capabilities

None — this change modifies behavior of existing capabilities without introducing a new domain.

### Modified Capabilities

- `platform`: data contracts for `coverage.csv` and `summary.csv` extended (ASE-Journal schema); resume-path invariant added requiring `static_data` to be present when reconstructing a repository from logcat; Branch 2 fallback paths in CSV writers removed.
- `analysis`: documentation invariant added stating that `parse_logcat_file` requires `static_data` for coverage reconstruction — without it, only `errors` are reliable. No code change in `rv-coverage`; the spec captures the contract that already exists in code.

## Impact

**Modules modified (code):**
- `rv-platform` — `modules/rv-platform/src/rv_platform/components/result_processor.py` (reconstruct method + 3 CSV writers); `modules/rv-platform/tests/components/test_result_processor.py` (new regression test + fixture data).

**Modules read (no change):**
- `rv-coverage` — `parse_logcat_file` signature unchanged; contract documented in the analysis spec.
- `rv-static-analysis` — `read_static_analysis_files` and `parse_file` unchanged; we promote an existing call from `StaticAnalysisComponent` into the resume path.
- `rv-android-core` — `LogcatRepository.calculate_metrics()` already exposes every metric we need; no change.

**Downstream consumers of CSV schema:**
- `scripts/regenerate_results/` (untracked workaround tooling) already produces this exact extended schema and remains compatible.
- Existing analysis notebooks/scripts under `experimento-*/` that parse `summary.csv` BY POSITION must be updated — `cov_class` insertion at index 5 shifts every later column. Notebooks that read columns by name (`df["cov_method"]`) continue to work. Notebooks that read `coverage.csv` by position continue to work for the original 12 columns (new columns append at indices 12-14). Notebooks looking for `errors` in `summary.csv` must switch to `mop_errors_total` (same semantic).

**No impact on:**
- `rv-experiment` orchestration (uses platform output but does not parse CSVs).
- `rv-agent`, `rv-monitor-generator`, `rv-instrumentation-*` — no contract changes.
- `tasks.json` persistence format — explicitly NOT extended (ADR-documented decision).

**Cross-references:** FR10 (`rv-platform` produces consolidated CSVs), FR12 (coverage metric calculation), NFR03 (experiment reproducibility), NFR08 (resume durability).
