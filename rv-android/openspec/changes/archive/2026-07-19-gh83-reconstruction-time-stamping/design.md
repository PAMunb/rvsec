# Design: gh83-reconstruction-time-stamping

GitHub Issue: #83

## Context

The `time` column in rv-platform CSV reports (FR12 Coverage Tracking, FR14 Result Processing) is defined as seconds elapsed since tool execution start. The live path implements this in `CoverageTracker._process_line` (`modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py:388-426`): for each logcat entry it computes `max(0, int((time_occurred − tool_execution_start_time).total_seconds()))` and stamps it on the log object before registering it in the `LogcatRepository`.

The reconstruction path — `ResultProcessorComponent._reconstruct_repository_from_logcat` (`modules/rv-platform/src/rv_platform/components/result_processor.py`) delegating to `parse_logcat_file` (`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`) — performs no timing computation at all. Every reconstructed `RvErrorLog`, `RvCoverageLog`, and `RvDiagnosticEvent` keeps the Pydantic default `time_since_task_start = 0`. Two CSV writers then mask the zeros: `_write_task_error_data` and `_write_task_app_events` apply `if time_value is None or time_value == 0: time_value = i`, turning the whole `time` column into a sequential row counter on resume/consolidation. `_write_task_coverage_data` has no such guard, so `coverage.csv` shows all zeros and `LogcatRepository.get_method_calls()`'s chronological sort (`sorted(..., key="time")`) degenerates to arbitrary order, corrupting the progressive `cov_method/cov_act/cov_rv_method` columns.

Both inputs needed for correct reconstruction already survive serialization: `TaskResult.tool_execution_start` is written to and restored from `tasks.json` (`modules/rv-android-core/src/rv_android_core/domain/task.py:430, 466-476`), and each parsed logcat line yields `time_occurred`. Git archaeology (issue #83) shows the parser never stamped timing in its history; the counter fallback predates the reconstruction path and became observable when resume was introduced (commit `788a4f7a`), surviving the gh58/gh65 static-data fixes which did not touch timing.

Constraints: P1 (minimal change — reuse the live arithmetic, no new abstractions), P3 (the fabrication guards are deleted outright, no compatibility shim), INV-PLT-18 (live/resume round-trip equivalence, now extended to `time`).

## Architecture

```
tasks.json ──► TaskResult.from_dict ──► task.result.tool_execution_start ─┐
                                                                          │ (epoch)
.logcat ──► parse_logcat_file(log_file, static_data, tool_execution_start)│
              │  per line: time_occurred (logcat timestamp)               │
              │  stamp: max(0, int((time_occurred − epoch).total_seconds()))
              ▼
        LogcatRepository (errors / methods / diagnostic events with real timing)
              ▼
        ResultProcessorComponent writers ──► coverage.csv / errors.csv / app_events.csv
              (time written as-is; fabrication guards removed)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `logcat_parser.parse_logcat_file` | Reconstruct repository; NEW: stamp `time_since_task_start` when epoch given | `log_file: str`, `static_data: Optional[StaticAnalysisData]`, `tool_execution_start: Optional[datetime]` | `LogcatRepository` |
| `logcat_parser._stamp_time` (new, module-private) | Shared arithmetic `max(0, int((occurred − epoch).total_seconds()))` | `time_occurred`, `epoch` | `int` |
| `result_processor._reconstruct_repository_from_logcat` | Pass `task.result.tool_execution_start` to the parser; warn when absent | `task` | `LogcatRepository` |
| `result_processor._write_task_error_data` / `_write_task_app_events` | Write `time_since_task_start` as-is (guards deleted) | repository dicts | CSV rows |
| `components/coverage.CoverageComponent._parse_existing_logcat` | Existing secondary caller; forwards the same epoch | `self.task.result` | `LogcatRepository` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-ANA-49 (stamp arithmetic + degraded case) | `parse_logcat_file` + `_stamp_time` in `logcat_parser.py` | `rv-coverage/tests/parser/log/test_logcat_parser.py::test_reconstruction_stamps_time*` |
| Scenario "Reconstruction With Tool Execution Start Stamps Timing" | same | `test_reconstruction_stamps_time_errors_coverage_events` |
| Scenario "Reconstruction Clamps Entries Predating Tool Start" | `_stamp_time` clamp | `test_reconstruction_clamps_negative_offsets` |
| Scenario "Reconstruction Without Tool Execution Start Degrades Explicitly" | warning branch in `parse_logcat_file` | `test_reconstruction_without_epoch_warns_once` |
| INV-PLT-23 (epoch forwarded on resume) | `_reconstruct_repository_from_logcat` in `result_processor.py` | `rv-platform/tests/components/test_result_processor.py::test_reconstruct_passes_tool_execution_start` |
| INV-PLT-24 (no fabricated time; t=0 representable) | guard deletion in `_write_task_error_data`, `_write_task_app_events` | `test_errors_csv_time_zero_not_replaced`, `test_app_events_csv_time_zero_not_replaced` |
| Scenario "Time Column Round-Trip Equivalence on Resume" | both halves together | `test_time_column_round_trip_live_vs_reconstructed` |
| Scenario "Errors/Coverage CSV Format" (`time` semantics) | writers unchanged apart from guard removal | existing CSV format tests extended with `time` assertions |

## Goals / Non-Goals

**Goals:**
- Reconstructed repositories carry the same `time_since_task_start` values the live tracker would have produced (round-trip equivalence extended to `time`).
- `errors.csv`, `app_events.csv`, `coverage.csv` never contain fabricated `time` values; `0` means first-second occurrence.
- Degraded case (no persisted epoch) is explicit: zeros + one warning, per task and per parse.

**Non-Goals:**
- No change to the live tracking path (`CoverageTracker`), `summary.csv`, `performance.csv`, coverage metrics or denominators (gh58/gh65 semantics preserved).
- No CSV schema change (column sets identical).
- No update to `Task`'s lazy repository reconstruction (`task.py:670-700`) — dead code behind a false `TYPE_CHECKING` guard, deferred to the planned deep refactoring; the optional parameter keeps its call sites valid.
- No re-generation of historical experiment CSVs (offline tooling can be re-run separately; `scripts/regenerate_results/` update is out of scope here).

## Decisions

1. **Stamp inside `parse_logcat_file` (epoch parameter) rather than post-parse in `result_processor`.** The repository's `register_method_call` collapses repeated calls into `MethodCoverageData` keyed by first call — timing must be attached *before* registration or the first-call time is unrecoverable. Post-parse stamping would require re-walking logcat lines and re-matching entries, duplicating parser logic in rv-platform. The parameter mirrors how the live tracker already owns the arithmetic next to the parsing. Alternative rejected: serializing `LogcatRepository` into `tasks.json` — large payload, breaks the established "logcat is the source of truth on resume" model (INV-PLT-15/18).
2. **Optional parameter, not a new function.** All existing callers remain valid; errors-only callers (`CoverageAnalyzer.process_logcat_file`, `scripts/migrate_logcat_files.py`) simply do not pass it. P1: one signature, no wrapper.
3. **Delete the `0 → i` guards outright (P3).** The guard conflates "no timing available" with "occurred at t=0" and fabricates plausible-looking data. With stamping in place, zeros only remain in the explicit degraded case, which is logged — writing `0` there is honest and analyzable, a counter is not.
4. **Reuse the exact live arithmetic including the `max(0, …)` clamp.** Buffered lines predating tool start exist in real logcats (documented in `tracker.py`); reconstruction must clamp identically or round-trip equivalence fails.
5. **`CoverageComponent._parse_existing_logcat` forwards the epoch too.** It is a live-session convenience path over the same contract; leaving it unstamped would reintroduce the asymmetry this change removes. One-line change.

## API Design

### `parse_logcat_file(log_file: str, static_data=None, tool_execution_start: Optional[datetime] = None) -> LogcatRepository`

- **Preconditions**: `log_file` exists (missing file handled as today — error logged, repository returned); `tool_execution_start`, when given, is the naive local `datetime` persisted by `Task.mark_tool_execution_start()` (same clock base as `_convert_to_datetime`'s output).
- **Postconditions**: when `tool_execution_start` is non-`None`, every registered error, coverage entry, and diagnostic event with a parseable `time_occurred` satisfies INV-ANA-49; when `None`, all `time_since_task_start` are `0` and one warning was logged if any RVSEC/COV/diagnostic entry was parsed.
- **Errors**: unchanged — per-line failures are swallowed and logged; the function never raises for missing timing.

### `ResultProcessorComponent._reconstruct_repository_from_logcat(task) -> Optional[LogcatRepository]`

- Passes `tool_execution_start=task.result.tool_execution_start`; when that is `None`, logs `WARNING` naming `task.id` before parsing (INV-PLT-23).

## Data Flow

1. Resume/consolidation loads `tasks.json` → `TaskResult.from_dict` restores `tool_execution_start`.
2. Writers find `task.repository is None` → `_reconstruct_repository_from_logcat(task)`.
3. The method resolves `static_data` (unchanged, INV-PLT-15) and calls `parse_logcat_file(logcat, static_data, tool_execution_start)`.
4. The parser stamps each entry via `_stamp_time` before `register_rv_error` / `register_method_call` / `register_diagnostic_event`; `MethodCoverageData.register_call` preserves the first-call stamp as today.
5. Writers emit `time_since_task_start` verbatim; `get_method_calls()`'s chronological sort now operates on real seconds, restoring progressive-column ordering.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `tool_execution_start is None` (legacy `tasks.json`) | `_reconstruct_repository_from_logcat` | WARNING with task id; proceed with `None` | `time` = 0 (explicit degraded state); researcher informed via log |
| Unparseable logcat timestamp on a line | `parse_logcat_line` | line already yields no entry today (regex mismatch) — unchanged | n/a |
| Entry predates epoch (buffered lines) | `_stamp_time` | clamp to `0` (matches live tracker) | n/a |

## Risks / Trade-offs

- [Device-clock vs host-clock skew: logcat timestamps come from the emulator, the epoch from host `datetime.now()`] → identical to the live tracker's exposure; reconstruction is no worse than live by construction (same arithmetic), and round-trip equivalence is preserved regardless of skew.
- [Historical CSVs generated with the counter remain wrong on disk] → out of scope; documented in issue #83. Re-running `--process-results` after this fix regenerates them correctly.
- [Third-party callers of `parse_logcat_file` not passing the epoch keep zero timing] → acceptable: they are errors-only paths; the new warning surfaces it.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (rv-coverage) | stamp arithmetic, clamp, degraded warning, propagation into `MethodCoverageData`/errors/diagnostic events | tmp logcat fixtures with known timestamps + fixed epoch | ~5 |
| Unit (rv-platform) | epoch forwarded from `task.result`; guards removed (t=0 written as `0`); warning on missing epoch | mocked task + spy on `parse_logcat_file`; CSV row assertions | ~4 |
| Integration (rv-platform) | round-trip: live-built repository vs serialize→reload→reconstruct produce identical `time` columns in all three CSVs | real logcat fixture + minimal static JSON (pattern from gh58 regression tests) | ~2 |

CI contract: `pytest --import-mode=importlib -o "addopts="` per module.

## Open Questions

(none — the epoch source, arithmetic, and guard removal are fully determined by the existing live-path behavior and the specs in this change)
