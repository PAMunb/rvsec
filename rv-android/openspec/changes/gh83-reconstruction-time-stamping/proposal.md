# Proposal: gh83-reconstruction-time-stamping

GitHub Issue: #83

## Why

The `time` column in rv-platform CSV reports degenerates whenever a task's repository is rebuilt through the logcat reconstruction path (resume or offline consolidation): `errors.csv` and `app_events.csv` show a sequential row counter (1, 2, 3, …) instead of seconds since tool execution start, and `coverage.csv` shows all zeros while losing chronological row order. The `time` column is a primary research artifact — it feeds time-series coverage analysis in the thesis experiments — so fabricated values silently corrupt published data. The core spec already defines the correct semantics (`time_since_task_start` = seconds since tool execution started); the reconstruction path simply never implements it, and the CSV writers mask the missing data by substituting the row index.

## What Changes

- `parse_logcat_file` (rv-coverage) gains timing reconstruction: given the tool execution start epoch, it stamps `time_since_task_start = max(0, time_occurred − tool_execution_start)` on every parsed error, coverage entry, and diagnostic event — the same arithmetic the live `CoverageTracker` uses.
- `ResultProcessorComponent._reconstruct_repository_from_logcat` (rv-platform) passes the task's serialized `tool_execution_start` (already persisted in `tasks.json`) into the parser so reconstructed repositories carry real timing.
- **BREAKING (data semantics)**: the `time_value == 0 → row index` fabrication guards in `_write_task_error_data` and `_write_task_app_events` are removed. A `time` of `0` now means "occurred in the first second of tool execution" (representable and correct), never a fabricated index. Consumers that relied on the counter behavior (none known) would break.
- Degraded case made explicit: when `tool_execution_start` is absent (legacy `tasks.json`), timing stays `0` and a warning is logged — no silent fabrication.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `analysis`: the `parse_logcat_file` reconstruction contract (INV-ANA-25 area) is extended with a timing requirement — reconstructed entries MUST carry `time_since_task_start` computed from the caller-supplied tool execution start epoch, with the no-epoch degraded case defined.
- `platform`: CSV writer requirements change — `errors.csv`, `app_events.csv`, and `coverage.csv` `time` columns MUST contain real seconds-since-tool-start on both live and reconstruction paths (extends the INV-PLT-18 live/resume round-trip equivalence to the `time` column); writers MUST NOT fabricate timing values.

## Impact

- **Modules**: `rv-coverage` (`parser/log/logcat_parser.py`), `rv-platform` (`components/result_processor.py`). No other module reads or writes `time_since_task_start` on the reconstruction path.
- **Interfaces**: `parse_logcat_file(log_file, static_data)` gains an optional tool-execution-start parameter. Callers: `ResultProcessorComponent` (updated), `CoverageComponent._parse_existing_logcat`, `CoverageAnalyzer` (audited in design).
- **Data artifacts**: `errors.csv`, `app_events.csv`, `coverage.csv` — schema unchanged (same columns), value semantics of `time` corrected on the reconstruction path.
- **Requirements**: FR12 (Coverage Tracking), FR14 (Result Processing).
- **Not affected**: live tracking path (`CoverageTracker`), `summary.csv`, `performance.csv`, coverage metrics/denominators (gh58/gh65 behavior preserved).
