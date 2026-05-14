# Design — gh58: result_processor static_data fix + ASE-Journal CSV schema

## Context

The proposal (`proposal.md`) and delta specs (`specs/platform/spec.md`, `specs/analysis/spec.md`) establish *what* must change. This document specifies *how*: the exact reshape of `ResultProcessorComponent`, the helper extracted to keep the reconstruct method P1-simple, the CSV writer changes, and the regression test fixture. Driven by GitHub Issue #58 and the experimentally-verified workaround in `scripts/regenerate_results/` (Branch 2 fallback unreachable once reconstruct succeeds; ASE-Journal schema validated against 18 267 logcats with verify C1–C4 PASS).

Relevant FRs/NFRs: FR10 (result consolidation), FR10-ext (resume integration), FR12 (coverage metrics), FR14 (result generation), NFR03 (reproducibility), NFR08 (resume durability).

Source of truth references in the codebase (verified against current HEAD):
- `modules/rv-platform/src/rv_platform/components/result_processor.py:151-186` — reconstruct method (single call site of `parse_logcat_file` to fix).
- `modules/rv-platform/src/rv_platform/components/result_processor.py:230-348` — `_write_task_coverage_data`: Branch 1 at lines 253-331 (real-time), single `else` fallback at lines 332-348 (writes empty `class/method/signature`). Branch 1 also contains a **pre-existing bug**: line 322 writes `round(method_coverage, 2)` into the `cov_class` column slot (position 8).
- `modules/rv-platform/src/rv_platform/components/result_processor.py:502-555` — `_write_task_summary_data` is a **3-tier cascade**, not Branch 1 / Branch 2: tier 1 reads `task.result.coverage_metrics` (dict serialized in tasks.json — current PRIMARY path), tier 2 falls back to `task.repository.calculate_metrics()` (only reached if `coverage_metrics` is absent), tier 3 emits zeros with a warning. All three tiers MUST be unified to a single path that reads from `task.repository.calculate_metrics().to_dict()` after reconstruct.
- `modules/rv-platform/src/rv_platform/components/static_analysis.py:130-140` — the canonical re-parse call to reuse: `static_analysis_parser.read_static_analysis_files(self.task.results_dir, self.task.config.apk_name, self.task.app.code_package if self.task.app else None)`.
- `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py:147-167` — class method `StaticAnalysisParser.read_static_analysis_files` (constructs `os.path.join(results_dir, apk + ".json")` and delegates to `parse_file`).
- `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py:699-712` — module-level convenience function (delegates to the class method via `_instance`).
- `modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py:254` — `package` filter: `if package and package not in normalized` — tolerates `package=None` (acts as "no filter"), so the `task.app is None` path is safe.
- `modules/rv-android-core/src/rv_android_core/domain/coverage.py:578` — `calculate_metrics(restrict_to_static=True) -> CoverageMetrics` (Pydantic model). Callers access fields via attributes (`metrics.method_coverage`) or via `metrics.to_dict()` which returns a dict with keys `class_coverage, activity_coverage, method_coverage, reachable_method_coverage, mop_method_coverage, direct_mop_method_coverage, total_errors, unique_errors`.
- `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py:42` — `parse_logcat_file(path, static_data)` signature.

## Architecture

```
                ┌───────────────────────────────────────────────────────┐
                │ ResultProcessorComponent (rv-platform)                │
                │                                                       │
                │   _generate_coverage_csv ──► _write_task_coverage    │
                │   _generate_summary_csv  ──► _write_task_summary     │  
                │   _generate_errors_csv   ──► _write_task_error       │
                │                              │                        │
                │                              ▼ (when task.repo None)  │
                │                _reconstruct_repository_from_logcat   │
                │                              │                        │
                └──────────────────────────────┼────────────────────────┘
                                               │
                       ┌───────────────────────┼──────────────────────────┐
                       │                       │                          │
                       ▼                       ▼                          ▼
        StaticAnalysisParser           parse_logcat_file        LogcatRepository
        .read_static_analysis_files   (path, static_data)       .calculate_metrics()
        (rv-static-analysis)          (rv-coverage)              (rv-android-core)
        ────────────────────────      ────────────────────       ──────────────────
        Re-parse JSON on demand       Returns repository         All 6 ASE-Journal
        Inputs: results_dir,          with classes populated     metrics already
        apk_name, code_package        from static_data           exposed; no change
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `result_processor._resolve_static_data(task)` | NEW private helper. Returns `task.static_data` if set; else re-parses via `read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)`; else `None` with warning log. Memoizes on `task.static_data` to avoid double-parse within one CSV generation pass. | `Task` | `Optional[StaticAnalysisData]` |
| `result_processor._reconstruct_repository_from_logcat(task)` | MODIFIED. Calls `_resolve_static_data(task)` then `parse_logcat_file(logcat_file, static_data)`. Same defensive try/except, same warning paths. | `Task` | `Optional[LogcatRepository]` |
| `result_processor._write_task_coverage_data(writer, task)` | MODIFIED. Always calls `_reconstruct_repository_from_logcat(task)` first if `task.repository is None`, then proceeds with the (now unified) Branch 1 code. The `else` fallback at lines 332-348 (empty-row write) is deleted. Branch 1 itself is corrected so that the `cov_class` slot reads `class_coverage` from `metrics.to_dict()` instead of `method_coverage`. Writes 15-column rows pulling `cov_reachable/cov_reaches_mop/cov_directly_reaches_mop` from a per-call progressive set against `calculate_metrics().to_dict()` denominators. | `csv.writer`, `Task` | none (side-effect: rows in `coverage.csv`) |
| `result_processor._write_task_summary_data(writer, task)` | MODIFIED. **Existing 3-tier cascade (result.coverage_metrics → repository.calculate_metrics → zeros) is collapsed to a single path.** Calls reconstruct first, then `repository.calculate_metrics().to_dict()` is the sole source of values. Writes 13-column rows. When reconstruct returns `None` (logcat missing), emits a zeroed row with explicit warning — no fallback to `task.result.coverage_metrics`. | `csv.writer`, `Task` | none (side-effect: row in `summary.csv`) |
| `result_processor._write_task_error_data` | UNCHANGED behavior. Already uses reconstruct via path `:421`; still works because errors don't need `static_data`. | — | — |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-PLT-15 (resume re-parse) | `_resolve_static_data` + reconstruct call site | `test_reconstruct_repository_from_logcat_populates_coverage_with_static_data` (RED before fix), `test_resolve_static_data_reuses_task_attribute`, `test_resolve_static_data_returns_none_when_json_missing`, `test_resolve_static_data_tolerates_task_app_none` |
| INV-PLT-16 (unified cascade) | Deletion of `else` block at lines 332-348 (coverage) and full 3-tier cascade at lines 518-540 (summary); both unified to single repository-based path | `test_write_coverage_data_uniform_path_resumed_and_runtime`, `test_write_summary_data_no_fallback_to_serialized_metrics` |
| INV-PLT-17 (cov_class = class_coverage) | Read `class_coverage` from `metrics.to_dict()` for the `cov_class` slot in both writers | `test_coverage_csv_cov_class_uses_class_coverage_not_method_coverage`, `test_summary_csv_cov_class_uses_class_coverage_not_method_coverage` |
| FR10-ext "Logcat Re-Reading with On-Demand Static Data Re-Parse" | `_resolve_static_data` + `parse_logcat_file(., static_data)` | scenario test fixture: logcat with 5 `RVSEC-COV` + 2 `RVSEC` + JSON with 10 reachable methods |
| FR10-ext "Static Analysis JSON Missing on Resume" | warning log + `static_data=None` path | `test_reconstruct_warns_and_zeroes_coverage_when_json_missing` |
| FR14 Coverage/Summary CSV format scenarios | Extended headers in `_generate_coverage_csv` / `_generate_summary_csv` | `test_coverage_csv_header_15_columns`, `test_summary_csv_header_13_columns` |
| INV-ANA (analysis delta) | Documentation only — verified by the platform tests above | covered by platform integration test |

## Goals / Non-Goals

**Goals:**
- Resume path produces CSV output byte-equivalent in column semantics to single-session output.
- ASE-Journal CSV columns are populated for every completed task (current-session and resumed).
- One regression test that fails against the pre-fix code; quality gate (lint+pytest) green.
- ADR explaining why we re-parse instead of serializing static_data into `tasks.json`.

**Non-Goals:**
- Performance optimization beyond memoization on `task.static_data` — re-parse is ~50–200 ms/task, dwarfed by tool execution timeouts (minutes).
- Backporting the schema change to existing `experimento-20260508/` CSVs (already covered by `scripts/regenerate_results/` workaround).
- Serializing `static_data` in `tasks.json` (ADR rejects this).
- Touching `rv-coverage` or `rv-static-analysis` code — the analysis delta is documentation only.
- Modifying `performance.csv` or `results.json` schema (no FR14 scenario changed there).
- Promoting `_regen.csv` → `_all.csv` in the external `RESULTADOS/` tree (manual, out of scope).

## Decisions

**D1: On-demand re-parse vs. serialize static_data in `tasks.json`.**
Chosen: on-demand re-parse inside `_resolve_static_data`. Alternative rejected: serialize `StaticAnalysisData` into `tasks.json`. Serialization would inflate `tasks.json` by megabytes per task (each APK's reachability section is thousands of class/method entries), and would couple persistence format to a domain model that already changes per analysis tool. The JSON files are already on disk in `task.results_dir`, so re-parsing is local I/O — no network, no IPC. Empirical cost: 50–200 ms/task per the regen run (18 267 tasks reparsed in ~30 min on 16 cores). Captured as ADR `docs/adr/adr-NNNN-resume-path-static-data-reparse.md`.

**D2: Memoize on `task.static_data` rather than a separate cache.**
Chosen: writing `_resolve_static_data`'s result back to `task.static_data` mirrors the runtime path (`StaticAnalysisComponent.load_static_data` writes to the same attribute). Alternative rejected: a `Dict[task_id, StaticAnalysisData]` field on the component, which would duplicate state and require explicit invalidation. The task-level field is the canonical home; reusing it keeps the resume and runtime paths symmetric.

**D3: Delete Branch 2 (no shim).**
Chosen: delete the fallback paths in `_write_task_coverage_data` and `_write_task_summary_data` entirely (P3). Alternative rejected: keep them as `if False:`-guarded or behind a feature flag. With `_resolve_static_data` returning a populated `StaticAnalysisData` for every task that has the JSON, and an explicit warning-and-zeros path for those that don't, the Branch 2 fallback is unreachable. Keeping dead code violates P3 and risks future re-introduction of the degenerate output.

**D4: Extend headers append-only (no reordering of existing columns).**
Chosen: new columns appended after existing ones. Alternative rejected: reorder columns to group "reachability-based" metrics adjacent to existing `cov_*`. Appending preserves positional readers in downstream notebooks for the original columns; named/header-based readers gain new columns without breakage. The cost is a slightly less aesthetic header order — acceptable.

**D5: `parse_file(json, package="")` vs `parse_file(json, code_package)`.**
The plan and workaround validated empirically that `package=""` is equivalent to `package=code_package` for the JCA-190 dataset because GATOR upstream already filters classes by `code_package` via `PackageDetector` before emitting the JSON. We use `task.app.code_package if task.app else None`, falling back to passing through `read_static_analysis_files` which itself handles `None` (it treats it as "no filter"). This matches `StaticAnalysisComponent.load_static_data:135` exactly.

## API Design

### `_resolve_static_data(task: Any) -> Optional[StaticAnalysisData]`

Pre-conditions: `task` has `config.apk_name` (always true for tasks loaded from `tasks.json`).
Post-conditions: returns the `StaticAnalysisData` cached on `task.static_data` if non-`None`; else attempts re-parse via `static_analysis_parser.read_static_analysis_files(task.results_dir, task.config.apk_name, task.app.code_package if task.app else None)`; else returns `None`.
Side effect on success: sets `task.static_data` so subsequent CSV writers within the same `execute()` call reuse it.
Error behavior: never raises. Any exception during re-parse is caught, logged as `warning`, and `None` is returned.

### `_reconstruct_repository_from_logcat(task: Any) -> Optional[LogcatRepository]`

Pre-conditions: unchanged from current code.
Post-conditions: returns a `LogcatRepository` with `errors` populated and (if `_resolve_static_data` returned non-`None`) with `classes` populated and method-call data registered. Returns `None` only when the logcat file itself is missing.
Error behavior: unchanged from current code (try/except around `parse_logcat_file`, warning on failure).

## Data Flow

```
Resume path (task.repository is None):
  task ──► _resolve_static_data ──┐
                                  ▼
                       (read_static_analysis_files)
                                  │
                                  ▼ static_data
  task.result.logcat_file ──► parse_logcat_file(path, static_data)
                                  │
                                  ▼
                            LogcatRepository
                            (classes populated,
                             method calls registered,
                             errors registered)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
   coverage.csv              summary.csv                errors.csv
   (15 cols)                 (13 cols)                  (10 cols, unchanged)
   per-method rows           1 row, calculate_metrics() 1 row per RVSEC
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `FileNotFoundError` on JSON | `_resolve_static_data` re-parse | Warning + return `None` | Coverage rows = 0 for this task; errors still captured |
| Logcat file missing | `_reconstruct_repository_from_logcat` | Warning + return `None` (unchanged) | Task row written with zeros (unchanged) |
| `JSONDecodeError` on JSON | `static_analysis_parser.read_static_analysis_files` (existing handler) | Already caught inside parser; returns empty `StaticAnalysisData` | Same as missing JSON path |
| Any other exception during reconstruct | broad `except Exception as e` (unchanged) | Warning + return `None` | Same as current code |

## Risks / Trade-offs

- **Risk**: re-parsing 18k JSONs in a serial loop during `execute()` could be slow. **Mitigation**: memoization on `task.static_data` ensures one parse per `(apk_name, code_package)` pair within a single task; across tasks the parse is local SSD I/O (~100 ms each); a 1000-task resume adds ~2 minutes — negligible vs. tool-execution time.
- **Risk**: positional CSV readers in older notebooks break on the new columns. **Mitigation**: new columns appended after existing ones, so positional readers continue to return correct values for the original columns; named-header readers gain new columns transparently. Notebooks that read `summary.csv` columns by name (the standard pandas pattern) are unaffected.
- **Risk**: tests against the pre-extended schema (existing tests assert 8-column summary header) will fail. **Mitigation**: update those tests as part of the implementation tasks; counted in the test plan below.
- **Risk**: `task.app` may be `None` for very old `tasks.json` versions (before App attachment). **Mitigation**: the existing `getattr` pattern handles this; `code_package` becomes `None` and `read_static_analysis_files` treats `None` as "no filter".

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `_resolve_static_data` cache hit / cache miss / JSON missing | Pytest with mocked filesystem | 3 tests |
| Unit | `_reconstruct_repository_from_logcat` with and without `static_data` | Real fixture logcat (small) + real minimal JSON | 2 tests (one is the RED regression) |
| Integration | `_generate_coverage_csv` over a 2-task mix (1 with repository, 1 resumed) | Tmpfs results_dir, assert 15-column header + correct per-method counts | 1 test |
| Integration | `_generate_summary_csv` schema 13 cols + values from `calculate_metrics` | Same setup, assert values match `calculate_metrics()` output | 1 test |
| Integration | Branch 2 deleted: same code path runs for resumed and runtime tasks | Assert no `coverage_metrics`-only fallback row | 1 test |
| Smoke (manual, not in CI) | Real run with `--name gh58_smoke` + Ctrl+C + resume | Visual check of CSVs | 0 (manual) |

Total: 8 automated tests added or modified. Fixture data lives under `modules/rv-platform/tests/components/fixtures/gh58/` (new directory).

## Open Questions

None remaining — design decisions D1–D5 are all settled. The exact ADR identifier (`adr-NNNN-...`) will be assigned by `/rv-doc-adr` when invoked in Phase 3.
