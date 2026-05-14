# Delta Spec — analysis (gh58)

## Purpose

This delta documents an invariant that already holds in code but was implicit: `parse_logcat_file(path, static_data)` in `rv-coverage` produces a `LogcatRepository` whose per-method coverage data is meaningful only when `static_data` is non-`None`. Without it, `LogcatRepository.classes` is empty, `register_method_call` silently no-ops for every `RVSEC-COV` entry, and `calculate_metrics()` returns zero for every method-based coverage metric. Errors (from `RVSEC` entries) remain reliable because `register_rv_error` stores them unconditionally. Capturing this contract in the analysis spec closes the loophole that allowed `rv-platform`'s resume path to call the parser without `static_data` for an extended period without surfacing as a test failure, and provides the formal anchor for the platform-side INV-PLT-15 added in this change.

No code changes occur in `rv-coverage`, `rv-static-analysis`, or `rv-screen-parser` — this delta is documentation-only.

## Invariants

<!-- INV-ANA-16..24 are reserved by gh57-static-analysis-overhaul (in-flight). gh58 takes INV-ANA-25
     to avoid archive-time collision. -->

- **INV-ANA-25**: `parse_logcat_file(logcat_file, static_data)` MUST be invoked with a non-`None` `StaticAnalysisData` whenever the caller intends to reconstruct per-method coverage from a persisted logcat (e.g. on resume, or in offline analysis tooling). When `static_data` is `None`, the returned `LogcatRepository` has `classes = {}`, `register_method_call` silently no-ops for every `RVSEC-COV` entry, and `calculate_metrics().to_dict()` returns zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`. Only `total_errors` and `unique_errors` remain accurate. Callers that omit `static_data` MUST do so deliberately (errors-only path) and log the degraded state.

## ADDED Requirements

### Requirement: Logcat-Based Repository Reconstruction Requires Static Data for Coverage (FR12)

When a caller invokes `parse_logcat_file(logcat_file, static_data)` to reconstruct a `LogcatRepository` outside of real-time execution (e.g., from a persisted `.logcat` on resume or in an offline analysis script), `static_data` MUST be a non-`None` `StaticAnalysisData` instance for per-method coverage to be reconstructed correctly. The parser does not raise when `static_data` is omitted — that signature is preserved for callers that only need MOP violation extraction — but the resulting repository's `classes` dict is empty, and any subsequent call to `register_method_call` (driven internally by `RVSEC-COV` log entries) returns without recording the call. Downstream metrics computed by `LogcatRepository.calculate_metrics()` (which returns a `CoverageMetrics` Pydantic model; callers normally access fields via attributes or `to_dict()`) over an empty `classes` dict yield zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`. Only `total_errors` and `unique_errors` remain accurate.

This contract is the formal reason `ResultProcessorComponent._reconstruct_repository_from_logcat` MUST pass `static_data` (see platform `INV-PLT-15`). It also governs offline analysis tooling (e.g., `scripts/regenerate_results/regenerate_container.py`), which loads `StaticAnalysisData` via `StaticAnalysisParser.parse_file` before each `parse_logcat_file` call.

#### Scenario: Coverage Reconstruction with Static Data Populates Repository

- **WHEN** `parse_logcat_file(path, static_data)` is called with `static_data` containing at least one `Class` whose `methods` include the signature emitted in an `RVSEC-COV:` line of the logcat
- **THEN** the returned `LogcatRepository.get_method_calls()` MUST return at least one entry for that signature
- **AND** `LogcatRepository.calculate_metrics().to_dict()["method_coverage"]` MUST be greater than zero
- **AND** `register_method_call` MUST have been invoked exactly once per matching `RVSEC-COV:` line

#### Scenario: Coverage Reconstruction Without Static Data Yields Empty Coverage

- **WHEN** `parse_logcat_file(path, static_data=None)` is called with a logcat containing `RVSEC-COV:` entries
- **THEN** the returned `LogcatRepository.classes` MUST be an empty dict
- **AND** `LogcatRepository.get_method_calls()` MUST return an empty list
- **AND** `LogcatRepository.calculate_metrics().to_dict()` MUST return zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`
- **AND** `LogcatRepository.get_errors()` MUST still return one entry per `RVSEC:` line (errors are unaffected by missing static data)
- **AND** the parser MUST NOT raise an exception
