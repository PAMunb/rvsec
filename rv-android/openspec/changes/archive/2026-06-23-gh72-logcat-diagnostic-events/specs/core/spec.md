# Delta Spec: Core — Logcat Diagnostic Capture and Event Model

## Purpose

The core domain (`rv-android-core`) owns logcat capture (`util/android/logcat_manager.py`), the shared
domain models for log data (`domain/log.py`), and the in-memory `LogcatRepository`
(`domain/coverage.py`). Today capture is hard-wired to `adb logcat -v threadtime -s RVSEC:V
RVSEC-COV:V`, which silences every non-RVSEC tag at the source, so application crashes, class-load
`VerifyError`s, and ANRs are never recorded.

This delta adds an **opt-in** capture mode and the data model needed to represent execution-level
diagnostic events. The capture change is gated by an environment flag so that, by default, the emitted
command and the captured `.logcat` remain byte-identical to the current baseline — a hard requirement
because every existing experiment depends on that baseline (see the non-regression gate G1). A new
`RvDiagnosticEvent` model and an isolated `diagnostic_events` collection on `LogcatRepository` carry the
parsed events. Isolation is structural: the existing coverage/MOP metric calculation reads only
`self.classes`, and `total_errors`/`unique_errors` read only `self.errors`/`self.unique_errors`, so a
new collection cannot perturb any existing metric.

This capability is consumed by the analysis domain (the parser that produces `RvDiagnosticEvent`s) and
the platform domain (the `app_events.csv` writer and the flag wiring).

## Data Contracts

### Input
- `RV_LOGCAT_DIAGNOSTICS: bool` — opt-in flag (env var name `ENV_LOGCAT_DIAGNOSTICS` in
  `constants.py`); default `false`. Threaded to `LogcatManager.start_capture(tags=...)` by the platform.
- `default_tags: List[str]` — base capture tags on `LogcatManager` (unchanged: `["RVSEC", "RVSEC-COV"]`).

### Output
- `RvDiagnosticEvent` — a parsed diagnostic event (constructed by the analysis-domain parser),
  registered via `LogcatRepository.register_diagnostic_event` and read via
  `LogcatRepository.get_diagnostic_events`.

### Side-Effects
- **[Device]**: when the flag is `true`, the emitted `adb logcat` command additionally whitelists
  `AndroidRuntime:E art:E dalvikvm:E ActivityManager:W`; when `false`, the command is unchanged.

### Error
- None new. Malformed input handling stays in the analysis-domain parser (warning + skip).

## Invariants

- **INV-CORE-37**: WHEN `RV_LOGCAT_DIAGNOSTICS` is unset or `false`, the `adb logcat` command emitted by
  `LogcatManager.start_capture` MUST be byte-identical to the baseline `-v threadtime -s RVSEC:V
  RVSEC-COV:V` (with the device serial), and the resulting `.logcat` MUST be unchanged.
- **INV-CORE-38**: The diagnostic tag set MUST be *additive* — when enabled, `RVSEC:V` and `RVSEC-COV:V`
  MUST remain in the filter; the diagnostic tags MUST NOT replace or reorder them.
- **INV-CORE-39**: Registering any number of `RvDiagnosticEvent`s into `LogcatRepository.diagnostic_events`
  MUST NOT change `calculate_metrics()` output, `total_errors`, `unique_errors`, or any coverage value;
  those computations MUST read only `self.classes`, `self.errors`, and `self.unique_errors`.

## ADDED Requirements

### Requirement: Opt-in Diagnostic Logcat Capture (FR33, FR34)

`LogcatManager` SHALL support an opt-in capture mode that, when enabled via the
`RV_LOGCAT_DIAGNOSTICS` flag, augments the logcat tag filter with the diagnostic tags
`AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` in addition to the existing `RVSEC:V RVSEC-COV:V`.
When the flag is disabled (the default), capture behavior MUST be identical to the current baseline.
The flag SHALL be exposed as a named constant `ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` in
`rv_android_core/constants.py`.

#### Scenario: Flag off preserves baseline command byte-for-byte
- **WHEN** `RV_LOGCAT_DIAGNOSTICS` is unset and `start_capture` is called for serial `emulator-5554`
- **THEN** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V`
- **AND** no diagnostic tag (`AndroidRuntime`, `art`, `dalvikvm`, `ActivityManager`) appears in the filter

#### Scenario: Flag on appends diagnostic tags additively
- **WHEN** `RV_LOGCAT_DIAGNOSTICS=true` and `start_capture` is called
- **THEN** the filter contains `RVSEC:V` and `RVSEC-COV:V` unchanged
- **AND** the filter additionally contains `AndroidRuntime:E`, `art:E`, `dalvikvm:E`, and `ActivityManager:W`

### Requirement: Diagnostic Event Domain Model (FR33)

The core domain SHALL provide an `RvDiagnosticEvent` model in `domain/log.py` representing a single
execution-level diagnostic event, following the existing `RvErrorLog`/`RvCoverageLog` conventions
(validated model, `to_dict`/`from_dict`, computed `unique_msg`). The model SHALL carry a `category`
discriminator with values `crash`, `verify_error`, and `anr`.

#### Scenario: Crash event carries attribution and trace summary
- **WHEN** a crash event is constructed from a parsed `AndroidRuntime` FATAL block for package
  `br.unb.cic.cryptoapp`
- **THEN** `category == "crash"`, `fatal == true`, `process == "br.unb.cic.cryptoapp"`, and `pid` is set
- **AND** `exception_class`, `stack_head`, `n_frames`, and `original_msg` (the full multi-line block) are populated

#### Scenario: unique_msg disambiguates by category
- **WHEN** two events share class/method but differ in `category` (`crash` vs `verify_error`)
- **THEN** their `unique_msg` values differ

### Requirement: Isolated Diagnostic Event Collection on LogcatRepository (FR33, FR37)

`LogcatRepository` SHALL expose a `diagnostic_events` collection with
`register_diagnostic_event(event)` and `get_diagnostic_events()`, kept strictly separate from the
coverage (`classes`) and property-violation (`errors`) data so that diagnostic events never enter
coverage/MOP metrics or the `total_errors`/`unique_errors` counts.

#### Scenario: Diagnostics do not affect metrics
- **WHEN** a repository holds RVSEC violations and coverage data, and N crash events are registered
- **THEN** `calculate_metrics()`, `total_errors`, `unique_errors`, and every coverage value are identical
  to the same repository with zero diagnostic events
- **AND** `get_diagnostic_events()` returns the N events sorted by `time_since_task_start`
