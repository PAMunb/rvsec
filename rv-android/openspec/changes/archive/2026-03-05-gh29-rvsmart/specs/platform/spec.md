# Delta Specification: Execution Platform

## Purpose

This delta documents how rvsmart's output integrates with the existing rv-platform result processing pipeline. No behavioral changes to the platform itself — the platform already supports any tool conforming to `AbstractTool`. This delta specifies the contract between rvsmart's trace output and the result processing expectations.

## ADDED Requirements

### Requirement: rvsmart Trace File Compatibility

rvsmart's stdout output, captured into `task.result.trace_file` by `RVSmartTool`, SHALL be compatible with rv-platform's result processing pipeline. The trace file contains JSON lines (one per iteration) followed by a final metrics line prefixed with `RVSMART_METRICS:`.

`ResultProcessorComponent` does not need to parse rvsmart's trace file directly. Standard coverage metrics (`task.result.coverage_metrics`) are populated by rv-platform's `CoverageComponent` from logcat `RVSEC-COV` tags — the same pipeline used for all other tools. `ResultProcessorComponent` reads `task.result.coverage_metrics` for `results.json` and `summary.csv` generation, exactly as with APE, DroidBot, or Monkey.

rvsmart-specific operational metrics (throughput, multi-attempt stats, LLM stats) are written by `RVSmartTool` to `rvsmart_metrics.json` alongside the trace file. These are consumed by Optuna calibration scripts and post-processing — not by `ResultProcessorComponent`.

MOP coverage data (monitored operation violations) continues to come from logcat parsing, independent of rvsmart's trace — the existing `CoverageComponent` and `LogcatComponent` handle this via `RVSEC-COV` tags in logcat, same as for all other tools.

#### Scenario: Result processing with rvsmart task
- **WHEN** a rvsmart task completes
- **THEN** `ResultProcessorComponent` SHALL include the task in `results.json` and `summary.csv` using `task.result.coverage_metrics` (method_coverage, activities_coverage, etc.)
- **AND** coverage data SHALL come from logcat parsing (standard pipeline)
- **AND** rvsmart-specific metrics SHALL be available in `rvsmart_metrics.json` for calibration scripts

#### Scenario: Result processing when agent crashed
- **WHEN** a rvsmart task completes but the agent crashed before timeout
- **THEN** `task.result.coverage_metrics` SHALL still be populated from logcat data collected before the crash
- **AND** `rvsmart_metrics.json` SHALL contain a default JSON with `"status":"metrics_unavailable"`
- **AND** `ResultProcessorComponent` SHALL include the task in results normally
- **AND** this SHALL NOT prevent result generation for other tasks in the experiment

### Requirement: rvsmart Task Identity in Resume

rvsmart tasks SHALL follow the standard task identity tuple for resume support: `(apk_name, "rvsmart", variant, repetition, timeout)`. This is automatic — rv-platform's `_skip_completed_tasks()` uses `ToolConfig.name` and `ToolConfig.variant`, which are set by the factory from `RVSmartTool`'s registration.

#### Scenario: Resume experiment with rvsmart tasks
- **WHEN** an experiment with `--tools rvsmart:mvp` is resumed
- **AND** 3 of 10 tasks were completed in the previous session
- **THEN** `_skip_completed_tasks()` SHALL identify the 3 completed tasks by identity tuple
- **AND** only the remaining 7 tasks SHALL be executed
