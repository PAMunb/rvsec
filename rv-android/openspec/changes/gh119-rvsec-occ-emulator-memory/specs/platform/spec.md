## Purpose

`LogcatComponent` (`modules/rv-platform/src/rv_platform/components/logcat.py`) starts and stops the logcat capture of each task. It does not own the tag list: it passes `LogcatManager.default_tags` through and, when diagnostics are enabled, appends the diagnostic tags after them. This change adds `RVSEC-OCC` to `default_tags` in `rv-android-core`. The component's code does not change. What changes is the baseline this domain states, because INV-PLT-21 and the "Capture Flag Threading to LogcatComponent" requirement spell out the tags and the emitted command verbatim, and they have to name the four tags the capture now admits.

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
