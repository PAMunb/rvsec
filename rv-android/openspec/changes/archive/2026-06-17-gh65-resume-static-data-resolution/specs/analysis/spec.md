# Analysis — Coverage Error Aggregates Survive Absent Static Data (gh65)

## Purpose

INV-ANA-25 already guarantees that, when `parse_logcat_file` is called without `static_data`, the reconstructed `LogcatRepository` yields zero for every per-method coverage metric while `total_errors` and `unique_errors` **remain accurate**. The code currently violates that guarantee: `CoverageMetricsRepository.calculate_metrics()` (in `rv-android-core/domain/coverage.py`) takes an early return when `self.classes` is empty (`if not self.classes: return CoverageMetrics()`), and that early return happens **before** the lines that count errors (`metrics.total_errors = len(self.errors)`; `metrics.unique_errors = len(self.unique_errors)`). As a result, `calculate_metrics().to_dict()["total_errors"]` is zero even when the repository holds violation entries — conflating "no coverage" with "no errors".

This delta makes the code conform to INV-ANA-25 (it does not amend the invariant): the error aggregates MUST be counted before the early return, so they survive the legitimate degraded case (logcat present, static-analysis JSON absent, e.g. `--skip-static` or a campaign run without static analysis). `get_errors()` already returns the right entries because it reads `self.errors` directly; the gap is only in the metrics aggregate consumed by the summary writer.

## ADDED Requirements

### Requirement: Error Aggregates Are Independent of Static Analysis Data (FR12)

`CoverageMetricsRepository.calculate_metrics()` MUST compute `total_errors` and `unique_errors` from the repository's `errors`/`unique_errors` collections regardless of whether static-analysis class data is present. The absence of `classes` (no static analysis) MUST zero only the coverage-percentage metrics, never the error aggregates. Concretely, the error count MUST be assigned before any early return guarded by `if not self.classes`, so that a repository reconstructed from a logcat without static data still reports accurate violation totals via `to_dict()`.

This requirement is the testable expression of `analysis` INV-ANA-25 ("Only `total_errors` and `unique_errors` remain accurate" when `static_data` is `None`) and the formal anchor for the platform-side guarantee that `summary.csv` reports correct `mop_errors_total`/`mop_errors_unique` on resume even when coverage is zero (platform INV-PLT-15).

#### Scenario: Metrics Over Empty Classes Still Count Errors

- **WHEN** a `CoverageMetricsRepository` has an empty `classes` dict (no static-analysis data) but holds K violation entries registered via `register_rv_error` (J of them with distinct `unique_msg`)
- **THEN** `calculate_metrics().to_dict()["total_errors"]` MUST equal K
- **AND** `calculate_metrics().to_dict()["unique_errors"]` MUST equal J
- **AND** `calculate_metrics().to_dict()["method_coverage"]` MUST be `0`
- **AND** every other coverage-percentage metric (`class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, `direct_mop_method_coverage`, `activity_coverage`) MUST be `0`

#### Scenario: Error Count Matches get_errors After Logcat-Only Reconstruction

- **WHEN** `parse_logcat_file(path, static_data=None)` reconstructs a repository from a logcat containing `RVSEC` violation entries
- **THEN** `repository.get_errors()` and `repository.calculate_metrics().to_dict()["total_errors"]` MUST report the same count
- **AND** that count MUST equal the number of `RVSEC` violation lines in the logcat

## MODIFIED Requirements

### Requirement: Logcat-Based Repository Reconstruction Requires Static Data for Coverage (FR12)

When a caller invokes `parse_logcat_file(logcat_file, static_data)` to reconstruct a `LogcatRepository` outside of real-time execution (e.g., from a persisted `.logcat` on resume or in an offline analysis script), `static_data` MUST be a non-`None` `StaticAnalysisData` instance for per-method coverage to be reconstructed correctly. The parser does not raise when `static_data` is omitted — that signature is preserved for callers that only need MOP violation extraction — but the resulting repository's `classes` dict is empty, and any subsequent call to `register_method_call` (driven internally by `RVSEC-COV` log entries) returns without recording the call. Downstream metrics computed by `LogcatRepository.calculate_metrics()` (which returns a `CoverageMetrics` Pydantic model; callers normally access fields via attributes or `to_dict()`) over an empty `classes` dict yield zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`. `total_errors` and `unique_errors` MUST remain accurate: they are counted from the `errors`/`unique_errors` collections independently of `classes`, so the empty-`classes` early return MUST NOT zero them (see "Error Aggregates Are Independent of Static Analysis Data").

This contract is the formal reason `ResultProcessorComponent._reconstruct_repository_from_logcat` MUST pass `static_data` (see platform `INV-PLT-15`). It also governs offline analysis tooling (e.g., `scripts/regenerate_results/regenerate_container.py`), which loads `StaticAnalysisData` via `StaticAnalysisParser.parse_file` before each `parse_logcat_file` call.

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
