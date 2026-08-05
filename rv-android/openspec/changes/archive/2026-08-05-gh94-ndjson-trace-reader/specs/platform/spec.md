# platform Delta Specification — Baseline Capture Tag Set Gains the Heartbeat Tag

## Purpose

`LogcatComponent` (`modules/rv-platform/src/rv_platform/components/logcat.py`) is where the platform decides which tags a task's logcat capture will admit. It delegates to `LogcatManager` and passes either nothing — in which case `default_tags` applies and the baseline command is emitted — or `default_tags + DIAGNOSTIC_TAGS` when `PlatformConfig.logcat_diagnostics` is set. INV-PLT-21 pins the first branch: with the flag off, capture must start with the baseline tag set and nothing else.

That invariant is written in terms of "the baseline tag set", and the `core` delta of this change moves what the baseline *is*. `LogcatManager.default_tags` gains the APE-RV step heartbeat tag `ApeRvHb`, because the capture is a live stream under a strict device-side allowlist and a heartbeat outside that allowlist is discarded before it can reach the file. So the platform's guard changes with it: the flag-off command that INV-PLT-21 and its test pin byte-for-byte is now the three-tag form.

No code changes here. `LogcatComponent` already passes `default_tags` through untouched, and it gains the new tag for free. What changes is the normative statement of what "baseline" means and the fixtures that assert it — which is the whole point of amending the invariant rather than quietly letting the test drift. The platform's own description of the captured file also changes, because that file now carries a third category of line.

## Data Contracts

### Input
- `logcat_diagnostics: bool` — from `PlatformConfig`, as today
- `LogcatManager.default_tags` — the baseline tag set, now three entries (`core` delta)

### Output
- the `adb logcat` command emitted at capture start, whose flag-off form is pinned byte-for-byte

### Side-Effects
- **[Filesystem]**: `task.result.logcat_file` now additionally carries one heartbeat line per exploration step for APE-RV tasks

### Error
- unchanged: a `stop_capture()` failure is logged at WARNING and does not propagate

## Invariants

- **INV-PLT-21** (amended): WHEN `logcat_diagnostics` is `false`, `LogcatComponent` MUST start capture with the baseline tag set and no diagnostic tags. The baseline tag set is `LogcatManager.default_tags` — `RVSEC`, `RVSEC-COV` and `ApeRvHb` — and the emitted command is `adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V` (core INV-CORE-37). The component MUST NOT filter, reorder or subset `default_tags`: the baseline is defined in one place, and a platform-side copy of the list would be a second place for it to drift.

## MODIFIED Requirements

### Requirement: Logcat Capture (FR11)

The platform MUST capture Android logcat output during task execution via `LogcatComponent`. Logcat capture runs as a background process that writes raw logcat output to a file on disk. The captured output contains three categories of data relevant to the framework: method coverage events (tagged `RVSEC-COV`), specification violation events (tagged `RVSEC`), and — for APE-RV tasks from the stage-4 jar onward — one step heartbeat line per exploration step (tagged `ApeRvHb`). Parsing of the first two is handled by `CoverageComponent` via rv-coverage's `CoverageTracker`; the third is consumed offline by `aperv-tool`'s clock-to-violation join and is inert to the coverage path (core INV-CORE-54).

`LogcatComponent` delegates to `LogcatManager` (from rv-android-core) for starting and stopping the capture process. The component supports device-specific capture through `device_serial`, which is extracted from `task.config.tool_config.parameters` to support parallel execution on different emulator instances.

Logcat capture starts after the emulator is running and the APK is installed, and stops after the testing tool completes. The captured file is stored at `task.result.logcat_file`. If `task.config.clean_logcat` is `True`, the logcat buffer is cleared before capture begins to avoid contamination from previous runs.

#### Scenario: Logcat Capture Lifecycle

- **WHEN** a task is executed with `LogcatComponent` registered
- **THEN** `start_capture()` MUST be called after emulator startup and APK installation
- **AND** the capture MUST write to `task.result.logcat_file`
- **AND** `stop_capture()` MUST be called after tool execution completes and coverage tracking stops

#### Scenario: Clean Logcat Buffer

- **WHEN** `task.config.clean_logcat` is `True`
- **THEN** `LogcatManager.start_capture()` MUST be called with `clear_buffer=True`
- **AND** the logcat buffer MUST be cleared before capture begins

#### Scenario: Parallel Execution Device Serial

- **WHEN** `task.config.tool_config.parameters` contains `device_serial: "emulator-5558"`
- **THEN** `LogcatComponent` MUST initialize `LogcatManager` with `device_serial="emulator-5558"`
- **AND** logcat capture MUST be scoped to that specific emulator instance

#### Scenario: Capture Stop Failure

- **WHEN** `stop_capture()` is called and `LogcatManager.stop_capture()` raises an exception
- **THEN** the error MUST be logged as a warning
- **AND** the exception MUST NOT propagate (cleanup is non-critical)

#### Scenario: Heartbeat lines reach the captured file

- **WHEN** an `aperv` task completes and its jar wrote one heartbeat line per step
- **THEN** `task.result.logcat_file` MUST contain those lines under tag `ApeRvHb`
- **AND** every coverage and violation value derived from that file MUST be what it would have been without them

### Requirement: Capture Flag Threading to LogcatComponent (FR07, FR08)

The platform SHALL thread the `RV_LOGCAT_DIAGNOSTICS` setting from `PlatformConfig` into
`LogcatComponent`, which SHALL pass the augmented tag set to `LogcatManager.start_capture` only when
diagnostics are enabled. When disabled, capture SHALL use the baseline tags — `default_tags` as
`LogcatManager` defines them, passed through without filtering, reordering or subsetting
(INV-PLT-21).

#### Scenario: Enabled flag augments capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `true`
- **THEN** `LogcatComponent` calls `start_capture(tags=default_tags + ["AndroidRuntime:E","art:E","dalvikvm:E","ActivityManager:W"])`
- **AND** the resulting filter carries `RVSEC:V`, `RVSEC-COV:V` and `ApeRvHb:V` first, in that order

#### Scenario: Disabled flag uses baseline capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `false` (default)
- **THEN** `LogcatComponent` starts capture without passing diagnostic tags
- **AND** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V`
