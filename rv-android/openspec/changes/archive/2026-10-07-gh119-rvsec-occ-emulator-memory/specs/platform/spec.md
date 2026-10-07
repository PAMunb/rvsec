## Purpose

`LogcatComponent` (`modules/rv-platform/src/rv_platform/components/logcat.py`) starts and stops the logcat capture of each task. It does not own the tag list: it passes `LogcatManager.default_tags` through and, when diagnostics are enabled, appends the diagnostic tags after them. This change adds `RVSEC-OCC` to `default_tags` in `rv-android-core`. The component's code does not change. What changes is the baseline this domain states, because INV-PLT-21 and the "Capture Flag Threading to LogcatComponent" requirement spell out the tags and the emitted command verbatim, and they have to name the four tags the capture now admits. The "Logcat Capture" requirement describes the categories of data the captured file carries, and it gains the occurrence stream as the fourth.

## Data Contracts

### Input
- `LogcatManager.default_tags: List[str]` — `[RVSEC, RVSEC-COV, ApeRvHb, RVSEC-OCC]` (core INV-CORE-53).

### Output
- Baseline capture command: `adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`.

### Side-Effects
- **Captured file**: `task.result.logcat_file` carries the `RVSEC-OCC` lines the instrumented app writes.

### Error
- None new.

## Invariants

- **INV-PLT-21**: WHEN `logcat_diagnostics` is `false`, `LogcatComponent` MUST start capture with the baseline tag set and no diagnostic tags. The baseline tag set is `LogcatManager.default_tags` — `RVSEC`, `RVSEC-COV`, `ApeRvHb` and `RVSEC-OCC` — and the emitted command is `adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V` (core INV-CORE-37). The component MUST NOT filter, reorder or subset `default_tags`: the baseline is defined in one place, and a platform-side copy of the list would be a second place for it to drift.

## MODIFIED Requirements

### Requirement: Capture Flag Threading to LogcatComponent (FR07, FR08)

The platform SHALL thread the `RV_LOGCAT_DIAGNOSTICS` setting from `PlatformConfig` into
`LogcatComponent`, which SHALL pass the augmented tag set to `LogcatManager.start_capture` only when
diagnostics are enabled. When disabled, capture SHALL use the baseline tags — `default_tags` as
`LogcatManager` defines them, passed through without filtering, reordering or subsetting
(INV-PLT-21).

#### Scenario: Enabled flag augments capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `true`
- **THEN** `LogcatComponent` calls `start_capture(tags=default_tags + ["AndroidRuntime:E","art:E","dalvikvm:E","ActivityManager:W"])`
- **AND** the resulting filter carries `RVSEC:V`, `RVSEC-COV:V`, `ApeRvHb:V` and `RVSEC-OCC:V` first, in that order

#### Scenario: Disabled flag uses baseline capture
- **WHEN** `PlatformConfig.logcat_diagnostics` is `false` (default)
- **THEN** `LogcatComponent` starts capture without passing diagnostic tags
- **AND** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`

### Requirement: Logcat Capture (FR11)

The platform MUST capture Android logcat output during task execution via `LogcatComponent`. Logcat capture runs as a background process that writes raw logcat output to a file on disk. The captured output contains four categories of data relevant to the framework: method coverage events (tagged `RVSEC-COV`), specification violation events on their first occurrence (tagged `RVSEC`), one step heartbeat line per exploration step for APE-RV tasks from the stage-4 jar onward (tagged `ApeRvHb`), and, for APKs instrumented with the current collector, the violation occurrence stream (tagged `RVSEC-OCC`): one line per occurrence of a violation identity, at most one per identity every 100 ms, with a counter (instrumentation INV-INS-171). Parsing of the first two is handled by `CoverageComponent` via rv-coverage's `CoverageTracker`. The heartbeat and the occurrence stream are consumed offline by `aperv-tool`, which places each line on the exploration step of the last heartbeat before it, and both are inert to the coverage path (core INV-CORE-54, INV-CORE-65).

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

#### Scenario: Occurrence lines reach the captured file

- **WHEN** an instrumented APK reports a violation identity 300 times during a task, and its collector writes `RVSEC-OCC` lines under the 100 ms throttle
- **THEN** `task.result.logcat_file` MUST contain those lines under tag `RVSEC-OCC`
- **AND** every coverage and violation value derived from that file MUST be what it would have been without them

