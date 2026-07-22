# Delta Spec: analysis — gh83-reconstruction-time-stamping

## Purpose

This delta extends the logcat reconstruction contract of `parse_logcat_file` (`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`) with timing semantics. Today the function reconstructs a `LogcatRepository` from a persisted `.logcat` file but never computes `time_since_task_start` on the entries it registers, so every reconstructed error, coverage entry, and diagnostic event carries the Pydantic default `0`. The only component that stamps timing is the live `CoverageTracker._process_line`, which subtracts the tool execution start epoch from each entry's logcat timestamp. The consequence is that any repository obtained through reconstruction (resume, offline consolidation) is temporally flat, and downstream CSV writers either expose the zeros (`coverage.csv`) or mask them with fabricated row indices (`errors.csv`, `app_events.csv` — see the platform delta).

The timing information needed for a correct reconstruction exists at parse time: each parsed entry carries `time_occurred` (converted from the logcat line's `MM-DD HH:MM:SS.mmm` prefix), and the caller can supply the tool execution start epoch (`TaskResult.tool_execution_start`, which is serialized in `tasks.json` and survives resume). This delta therefore adds an optional `tool_execution_start` parameter to `parse_logcat_file` and requires the parser to stamp `time_since_task_start = max(0, int((time_occurred − tool_execution_start).total_seconds()))` on every entry — the exact arithmetic the live tracker uses — so that live and reconstructed repositories are temporally equivalent. When the epoch is not supplied (legacy `tasks.json` predating `tool_execution_start` serialization, or errors-only callers that do not need timing), the field keeps its `0` default and the degraded state is explicit at the call site, never silently fabricated downstream.

## Data Contracts

### Input
- `log_file: str` — absolute path to the persisted `.logcat` file (unchanged).
- `static_data: Optional[StaticAnalysisData]` — pre-populates repository classes for coverage reconstruction (unchanged, see INV-ANA-25).
- `tool_execution_start: Optional[datetime]` — NEW. The tool execution start epoch. Sourced from `TaskResult.tool_execution_start` (deserialized from `tasks.json`) by rv-platform callers, or from any equivalent record by offline tooling. When `None`, no timing is stamped.

### Output
- `LogcatRepository` — as before, with `time_since_task_start` populated on every registered `RvErrorLog`, `RvCoverageLog` (propagated into `MethodCoverageData` via `register_method_call`), and `RvDiagnosticEvent` whenever `tool_execution_start` is provided.

### Side-Effects
- **[Logging]**: when `tool_execution_start` is `None` and the logcat contains at least one RVSEC/RVSEC-COV/diagnostic entry, the parser MUST log a single warning stating that reconstructed timing is unavailable and `time_since_task_start` values remain `0`.

### Error
- No new error paths. The parser continues to swallow per-line parse failures and never raises on missing timing input.

## Invariants

- **INV-ANA-49**: For every entry registered by `parse_logcat_file` when `tool_execution_start` is non-`None` and the entry has a parseable `time_occurred`, `time_since_task_start` MUST equal `max(0, int((time_occurred − tool_execution_start).total_seconds()))` — identical to the live `CoverageTracker._process_line` arithmetic, including the clamp to zero for entries buffered from before tool start. When `tool_execution_start` is `None`, `time_since_task_start` MUST remain `0` and the degraded state MUST be logged; no component may substitute a fabricated value for it downstream.

## MODIFIED Requirements

### Requirement: Logcat-Based Repository Reconstruction Requires Static Data for Coverage (FR12)

When a caller invokes `parse_logcat_file(logcat_file, static_data, tool_execution_start)` to reconstruct a `LogcatRepository` outside of real-time execution (e.g., from a persisted `.logcat` on resume or in an offline analysis script), `static_data` MUST be a non-`None` `StaticAnalysisData` instance for per-method coverage to be reconstructed correctly. The parser does not raise when `static_data` is omitted — that signature is preserved for callers that only need MOP violation extraction — but the resulting repository's `classes` dict is empty, and any subsequent call to `register_method_call` (driven internally by `RVSEC-COV` log entries) returns without recording the call. Downstream metrics computed by `LogcatRepository.calculate_metrics()` (which returns a `CoverageMetrics` Pydantic model; callers normally access fields via attributes or `to_dict()`) over an empty `classes` dict yield zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`. `total_errors` and `unique_errors` MUST remain accurate: they are counted from the `errors`/`unique_errors` collections independently of `classes`, so the empty-`classes` early return MUST NOT zero them (see "Error Aggregates Are Independent of Static Analysis Data").

Analogously, `tool_execution_start` MUST be a non-`None` `datetime` for reconstructed timing to be correct. When it is provided, the parser MUST stamp `time_since_task_start = max(0, int((time_occurred − tool_execution_start).total_seconds()))` on every parsed error, coverage entry, and diagnostic event before registering it (INV-ANA-49) — making reconstructed repositories temporally equivalent to those populated live by `CoverageTracker`. When it is omitted, `time_since_task_start` remains `0` on every entry and the parser MUST log one warning about the degraded timing; callers that omit it MUST do so deliberately (no timing available or not needed).

This contract is the formal reason `ResultProcessorComponent._reconstruct_repository_from_logcat` MUST pass `static_data` (see platform `INV-PLT-15`) AND `task.result.tool_execution_start` (see platform `INV-PLT-23`). It also governs offline analysis tooling (e.g., `scripts/regenerate_results/regenerate_container.py`), which loads `StaticAnalysisData` via `StaticAnalysisParser.parse_file` before each `parse_logcat_file` call.

#### Scenario: Coverage Reconstruction with Static Data Populates Repository

- **WHEN** `parse_logcat_file(path, static_data)` is called with `static_data` containing at least one `Class` whose `methods` include the signature emitted in an `RVSEC-COV:` line of the logcat
- **THEN** the returned `LogcatRepository.get_method_calls()` MUST return at least one entry for that signature
- **AND** `LogcatRepository.calculate_metrics().to_dict()["method_coverage"]` MUST be greater than zero
- **AND** `register_method_call` MUST have been invoked exactly once per matching `RVSEC-COV:` line

#### Scenario: Coverage Reconstruction Without Static Data Yields Empty Coverage

- **WHEN** `parse_logcat_file(path, static_data=None)` is called with a logcat containing `RVSEC-COV:` entries and `RVSEC:` violation entries
- **THEN** the returned `LogcatRepository.classes` MUST be an empty dict
- **AND** `LogcatRepository.get_method_calls()` MUST return an empty list
- **AND** `LogcatRepository.calculate_metrics().to_dict()` MUST return zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`
- **AND** `LogcatRepository.get_errors()` MUST still return one entry per `RVSEC:` line (errors are unaffected by missing static data)
- **AND** `LogcatRepository.calculate_metrics().to_dict()["total_errors"]` MUST equal `len(get_errors())` (the empty-`classes` early return MUST NOT zero the error aggregate)
- **AND** the parser MUST NOT raise an exception

#### Scenario: Reconstruction With Tool Execution Start Stamps Timing

- **WHEN** `parse_logcat_file(path, static_data, tool_execution_start=datetime(2026, 3, 24, 19, 37, 0))` is called and the logcat contains an `RVSEC:` violation line timestamped `03-24 19:37:05.000` and an `RVSEC-COV:` line timestamped `03-24 19:37:12.000` for a signature present in `static_data`
- **THEN** the reconstructed error's `time_since_task_start` MUST equal `5`
- **AND** the reconstructed method's `MethodCoverageData.time_since_task_start` MUST equal `12`
- **AND** `LogcatRepository.get_method_calls()` MUST return entries whose `time` values reflect those stamps (not `0`)

#### Scenario: Reconstruction Clamps Entries Predating Tool Start

- **WHEN** `parse_logcat_file(path, static_data, tool_execution_start=datetime(2026, 3, 24, 19, 37, 0))` is called and the logcat contains an `RVSEC:` line timestamped `03-24 19:36:58.000` (buffered from before tool start)
- **THEN** that entry's `time_since_task_start` MUST equal `0` (clamped, not negative)

#### Scenario: Reconstruction Without Tool Execution Start Degrades Explicitly

- **WHEN** `parse_logcat_file(path, static_data)` is called without `tool_execution_start` and the logcat contains `RVSEC:` entries
- **THEN** every reconstructed entry's `time_since_task_start` MUST remain `0`
- **AND** the parser MUST log exactly one warning stating that reconstructed timing is unavailable
- **AND** the parser MUST NOT raise an exception
