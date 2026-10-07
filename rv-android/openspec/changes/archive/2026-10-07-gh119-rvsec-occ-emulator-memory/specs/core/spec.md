## Purpose

`rv-android-core` owns two pieces of device plumbing this change touches: the tag allowlist of the logcat capture (`LogcatManager`, `util/android/logcat_manager.py`) and the emulator launch (`Android.start_emulator`, `util/android/android.py`).

The capture is a live stream filtered on the device: `adb logcat -s <tags>` discards every line whose tag is not in the list before it leaves the emulator, so a stream the analysis needs exists only if its tag is admitted when capture starts. The monitor runtime now writes a second violation stream, `RVSEC-OCC` — every occurrence of a violation identity, throttled to one line per identity per 100 ms (instrumentation INV-INS-171). The baseline allowlist therefore grows from three tags to four. The new tag is declared once as a named constant, beside the three the list is already built from. The logcat buffer size stays at 16 MiB (INV-CORE-64): the measured volume does not need more, and a larger buffer costs guest memory.

The emulator launch sets the guest's memory and its data partition. The AVD in the campaign image is created by `avdmanager` with the `pixel` profile defaults, `hw.ramSize=1536M` and `disk.dataPartition.size=800M`. `docker/android/Dockerfile` declares no emulator memory, storage, core count or GPU mode. `Android.start_emulator` is the one place the launch sets them, and it passes the memory and the data partition from named constants on every launch. The number of CPU cores is left to the AVD (`hw.cpu.ncore=4`).

## Data Contracts

### Input
- `TAG_RVSEC_OCC: str = "RVSEC-OCC"` — `rv_android_core/util/logging/constants.py`.
- `EMULATOR_MEMORY_MB: int = 4096`, `EMULATOR_PARTITION_SIZE_MB: int = 8192` — `rv_android_core/constants.py`.

### Output
- Baseline capture command: `adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`.
- Emulator launch argv: `emulator -avd <name> -port <port> -read-only -no-cache -no-boot-anim -noaudio -no-snapshot-save -delay-adb -memory 4096 -partition-size 8192 [-no-window]`.

### Side-Effects
- **Device**: the guest boots with 4096 MB of RAM and an 8192 MB `/data` partition; the read-only AVD writes the partition to a temporary image for the life of the emulator process.
- **Captured file**: lines under `RVSEC-OCC` reach `task.result.logcat_file`.

### Error
- None new. A launch the emulator rejects fails the boot wait as any failed launch does (`TimeoutError` → `EmulatorError`, "Emulator Session Failure Attribution").

## Invariants

- **INV-CORE-37**: WHEN `RV_LOGCAT_DIAGNOSTICS` is unset or `false`, the `adb logcat` command emitted by `LogcatManager.start_capture` MUST be byte-identical to the baseline `-v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V` (with the device serial). The three-tag form is superseded, not retained as an alternative: a capture that omits `RVSEC-OCC` produces a logcat with no occurrence stream, and nothing downstream can tell that from a run in which no violation repeated.
- **INV-CORE-38**: The diagnostic tag set MUST be *additive* — when enabled, `RVSEC:V`, `RVSEC-COV:V`, `ApeRvHb:V` and `RVSEC-OCC:V` MUST remain in the filter, first and in that order; the diagnostic tags MUST NOT replace or reorder them.
- **INV-CORE-53**: The heartbeat tag and the occurrence tag MUST each be declared once, as the named constants `TAG_APERV_HEARTBEAT` and `TAG_RVSEC_OCC` in `rv_android_core/util/logging/constants.py`, beside `TAG_RVSEC` and `TAG_RVSEC_COV`, and `LogcatManager.default_tags` MUST be built from those four constants, in the order `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT, TAG_RVSEC_OCC]`, rather than from repeated string literals. Each value MUST equal the tag its producer writes under (the APE-RV jar, the monitor runtime's `ErrorCollector`); a literal duplicated across repositories is where that equality would silently drift, and the failure mode of a mismatch is an empty stream rather than an error.
- **INV-CORE-65**: The presence of `RVSEC-OCC` lines in a captured logcat MUST NOT change any value produced by `parse_logcat_file` — not `calculate_metrics()`, not `total_errors`, not `unique_errors`, not any coverage value, and not the diagnostic-event collection. `parse_logcat_line` dispatches on the exact tag field, so an `RVSEC-OCC` line yields neither an error nor a coverage record and is counted as `lines_other_tag`, as an `ApeRvHb` line is.
- **INV-CORE-66**: `Android.start_emulator` MUST pass `-memory <EMULATOR_MEMORY_MB>` and `-partition-size <EMULATOR_PARTITION_SIZE_MB>`, with `EMULATOR_MEMORY_MB = 4096` and `EMULATOR_PARTITION_SIZE_MB = 8192` from `rv_android_core/constants.py`, and MUST NOT pass `-cores`. The values are constants, not environment variables: they describe the execution condition of a campaign, which a per-container override would make differ between the containers of one campaign.

## ADDED Requirements

### Requirement: Violation Occurrence Tag in the Capture Allowlist (FR11, FR13)

`LogcatManager.default_tags` SHALL include the violation occurrence tag `RVSEC-OCC`, declared as the constant `TAG_RVSEC_OCC` in `rv_android_core/util/logging/constants.py` and appended after `TAG_APERV_HEARTBEAT`, so the three existing tags keep their position and order (INV-CORE-53).

The tag is the monitor runtime's: `ErrorCollector` in `rvsec-logger-logcat` writes one line under it per violation occurrence, throttled to one line per identity per 100 ms, and the `RVSEC` stream keeps only the first occurrence (instrumentation INV-INS-170, INV-INS-171). It is admitted globally, in `default_tags`, for the reason the heartbeat is: the filter runs on the device for the whole capture, and there is no per-tool tag channel. An uninstrumented APK writes nothing under it, so the global default costs such runs nothing.

`RVSEC-OCC` lines SHALL be inert to every existing consumer of the captured file (INV-CORE-65). They are read by an analysis that asks for the tag by name, as `aperv-tool`'s `read_tagged_lines(path, tag)` does.

#### Scenario: The tag is declared once

- **WHEN** the module's tests search the source tree for the literal `"RVSEC-OCC"`
- **THEN** it SHALL appear exactly once, as the value of `TAG_RVSEC_OCC`
- **AND** `LogcatManager.default_tags` SHALL be `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT, TAG_RVSEC_OCC]`

#### Scenario: Occurrence lines change no parsed value

- **WHEN** `parse_logcat_file` runs over a captured logcat containing 2 000 `RVSEC-OCC` lines interleaved with its `RVSEC`, `RVSEC-COV` and `ApeRvHb` lines, and again over the same file with the `RVSEC-OCC` lines removed
- **THEN** `calculate_metrics()`, `total_errors`, `unique_errors` and every coverage value SHALL be identical between the two runs
- **AND** the diagnostic-event collection SHALL be identical between the two runs, and the first run's `lines_other_tag` SHALL be the second run's plus 2 000

### Requirement: Emulator Memory and Data Partition at Launch (FR07, NFR04)

`Android.start_emulator` SHALL launch the emulator with `-memory 4096 -partition-size 8192`, the values of `EMULATOR_MEMORY_MB` and `EMULATOR_PARTITION_SIZE_MB` in `rv_android_core/constants.py` (INV-CORE-66), in addition to the flags it already passes. It SHALL NOT pass `-cores`; the AVD's `hw.cpu.ncore=4` stays in force.

The AVD of the campaign image is created by `avdmanager` with the `pixel` profile defaults, `hw.ramSize=1536M` and `disk.dataPartition.size=800M`. With 1536 MB, the guest's low-memory killer can terminate the app under test during a run. That kill looks like an app restart, and a restart resets the monitor's in-process state. With 800 MB, a large APK can fail to install. Passing the values at launch, rather than editing the AVD's `config.ini` in the image, keeps the change in the module that owns the launch and needs no rebuild of the `docker/android` image layer. The flags take precedence over the AVD's configuration for that launch.

The new values change the conditions a run executes under. Campaigns run before this requirement ran with 1536 MB and 800 MB, and a comparison with them SHALL state the difference beside it.

#### Scenario: the launch argv carries memory and partition

- **WHEN** `Android.start_emulator("RVSec", no_window=True, device_port=5556)` is called
- **THEN** the emulator command MUST be `emulator -avd RVSec -port 5556 -read-only -no-cache -no-boot-anim -noaudio -no-snapshot-save -delay-adb -memory 4096 -partition-size 8192 -no-window`
- **AND** it MUST NOT contain `-cores`

#### Scenario: the values come from the constants

- **WHEN** a test sets `EMULATOR_MEMORY_MB` to `2048` through monkeypatching the constants module and calls `start_emulator`
- **THEN** the argv MUST carry `-memory 2048`
- **AND** no environment variable MUST be read to build either value

## MODIFIED Requirements

### Requirement: Opt-in Diagnostic Logcat Capture (FR33, FR34)

`LogcatManager` SHALL support an opt-in capture mode that, when enabled via the
`RV_LOGCAT_DIAGNOSTICS` flag, augments the logcat tag filter with the diagnostic tags
`AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` in addition to the baseline tags
`RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`. When the flag is disabled (the default), capture behavior MUST be
the baseline described by INV-CORE-37. The flag SHALL be exposed as a named constant
`ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` in `rv_android_core/constants.py`.

The baseline is four tags. The APE-RV step heartbeat and the violation occurrence stream must both
survive the device-side filter; see "APE-RV Step Heartbeat Tag in the Capture Allowlist" and
"Violation Occurrence Tag in the Capture Allowlist" for why neither tag can be added at the point
of use instead.

#### Scenario: Flag off emits the baseline command byte-for-byte
- **WHEN** `RV_LOGCAT_DIAGNOSTICS` is unset and `start_capture` is called for serial `emulator-5554`
- **THEN** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`
- **AND** no diagnostic tag (`AndroidRuntime`, `art`, `dalvikvm`, `ActivityManager`) appears in the filter

#### Scenario: Flag on appends diagnostic tags additively
- **WHEN** `RV_LOGCAT_DIAGNOSTICS=true` and `start_capture` is called
- **THEN** the filter contains `RVSEC:V`, `RVSEC-COV:V`, `ApeRvHb:V` and `RVSEC-OCC:V` unchanged and in that order
- **AND** the filter additionally contains `AndroidRuntime:E`, `art:E`, `dalvikvm:E`, and `ActivityManager:W`

### Requirement: APE-RV Step Heartbeat Tag in the Capture Allowlist (FR33, FR34)

`LogcatManager.default_tags` SHALL include the APE-RV step heartbeat tag `ApeRvHb`, declared as the
constant `TAG_APERV_HEARTBEAT` in `rv_android_core/util/logging/constants.py` beside `TAG_RVSEC` and
`TAG_RVSEC_COV`, and placed after them so those two keep their position and order
(INV-CORE-53). `TAG_RVSEC_OCC` follows it ("Violation Occurrence Tag in the Capture Allowlist").

**Why the allowlist and not the point of use.** Capture is a live stream, not a post-run dump: the
buffer is cleared at start and `adb logcat -s <tags>` runs for the run's duration, so a tag that is
not in the filter when capture begins is discarded at the device and cannot be recovered afterwards
by any consumer. There is no per-tool tag channel — `LogcatComponent` builds the tag list from
`default_tags` for every task regardless of which tool runs — so adding the tag anywhere narrower
would mean inventing that channel for one string. The tag emits nothing for tools that do not write
under it, so the global default costs those runs nothing.

**Why the tag string is not chosen locally.** The jar writes the heartbeat under a fixed tag defined
by the `ape` change `rearch-04-step-ndjson-telemetry` (design D-6, `Log.i("ApeRvHb", "s=<N> t=<tRelMs>")`).
The two sides must name the same string, and a mismatch fails silently: capture succeeds, the file
contains no heartbeat, and the consumer that needed it reports nothing unusual. The constant is
therefore the single place the string appears on this side, and the tag SHALL fit the device's
23-character bound on logcat tags.

Heartbeat lines SHALL be inert to every existing consumer of the captured file (INV-CORE-54).
`parse_logcat_file` dispatches on `RVSEC` and `RVSEC-COV` alone; the heartbeat is neither, so it
contributes to no coverage value, no violation, and no diagnostic event.

#### Scenario: Heartbeat lines survive the device-side filter
- **WHEN** an APE-RV run executes 1,603 steps with the heartbeat flag at its jar-side default and capture runs with `default_tags`
- **THEN** `task.result.logcat_file` SHALL contain 1,603 heartbeat lines under tag `ApeRvHb`
- **AND** their `s` values SHALL match the step numbers of the trace's `StepRecord` lines

#### Scenario: The tag is declared once
- **WHEN** the module's tests search the source tree for the literal `"ApeRvHb"`
- **THEN** it SHALL appear exactly once, as the value of `TAG_APERV_HEARTBEAT`
- **AND** `LogcatManager.default_tags` SHALL be `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT, TAG_RVSEC_OCC]`

#### Scenario: Heartbeat lines change no parsed value
- **WHEN** `parse_logcat_file` runs over a captured logcat containing 1,603 heartbeat lines, and again over the same file with those lines removed
- **THEN** `calculate_metrics()`, `total_errors`, `unique_errors` and every coverage value SHALL be identical between the two runs
- **AND** the diagnostic-event collection SHALL be identical between the two runs

#### Scenario: A run by a tool that writes no heartbeat is unaffected
- **WHEN** a `monkey` task runs with the same `default_tags`
- **THEN** the emitted command SHALL carry `ApeRvHb:V` like every other capture
- **AND** the captured file SHALL contain no line under that tag, and every downstream value SHALL be what it was before this change

### Requirement: The Device Log Buffer Is Sized Before Capture (FR33, NFR06)

`LogcatManager.start_capture` SHALL set the device's log ring buffers to 16 MiB with `adb -s <serial> logcat -G 16M` before it clears the buffer and starts the capture (INV-CORE-64). The size is a named constant, `LOGCAT_BUFFER_SIZE`, in `rv_android_core/constants.py`.

A capture is a live stream of a ring buffer, so a line that `logd` prunes before the host reader receives it is lost without a trace in the file. The default of the campaign image is 2 MiB, which held 46 s of history in a one-minute run; 16 MiB, the largest size Android's developer settings offer, holds eight times that. The sizing runs on every capture rather than once per device because it is cheap and a device may have been rebooted between tasks. It is a separate command, not an extra flag on the capture command, so the capture command stays byte-identical to INV-CORE-37. A failure is logged and the capture proceeds: a smaller buffer loses lines under load, and no capture loses every line.

The size is not raised for the occurrence stream. The buffer only has to hold what the live reader has not yet received, not the whole run. The E6 capture absorbed peaks of 6 673 lines in one second; at about 400 bytes a line, 16 MiB is several seconds of reader lag at that rate. `-G` sizes each default buffer separately, so a larger value would take guest memory three times over.

#### Scenario: the buffer is sized before the capture starts

- **WHEN** `start_capture` is called for serial `emulator-5554` with `clear_buffer=True`
- **THEN** the commands MUST be issued in the order `adb -s emulator-5554 logcat -G 16M`, `adb -s emulator-5554 logcat -c`, `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`
- **AND** the third command MUST be byte-identical to the one INV-CORE-37 fixes

#### Scenario: a failed sizing does not stop the capture

- **WHEN** `adb -s emulator-5554 logcat -G 16M` exits non-zero
- **THEN** a WARNING naming `emulator-5554` and the requested size MUST be logged
- **AND** the capture command MUST still be started and `start_capture` MUST return `True` when the capture starts
