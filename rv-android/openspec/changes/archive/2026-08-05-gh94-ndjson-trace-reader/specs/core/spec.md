# core Delta Specification — The APE-RV Step Heartbeat Tag in the Capture Allowlist

## Purpose

`LogcatManager` (`modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py`) owns how the framework captures logcat, and the way it captures is what makes this delta necessary. It does not dump the device's ring buffer after a run. It clears the buffer at start and then streams `adb -s <serial> logcat -v threadtime -s RVSEC:V RVSEC-COV:V` for the run's whole duration, writing into `task.result.logcat_file`. The `-s` flag is a **strict allowlist**: a line written under any tag not named in it is discarded at the device and never reaches the file. Everything downstream — coverage, violations, the offline clock-to-violation join — reads that file and nothing else.

Stage 4 of the APE-RV re-architecture adds a write-only heartbeat: one `Log.i` line per exploration step, carrying the step number and its run-relative timestamp. Its entire purpose is to place the step series and the `RVSEC` violation series in the same file, on the same clock, so that `aperv-tool`'s offline join can stop reconstructing the device's UTC offset from first principles. That purpose is served only if the heartbeat's tag is in the allowlist. Under any other tag the heartbeat is filtered out at the device, the join sees nothing, and — because the join would go on working against its old reconstruction — nothing anywhere reports a problem. The mechanism would be silently inert, which is precisely the failure class stage 4 exists to remove.

So the tag is not a free choice made independently on each side. The jar's design names `ApeRvHb`; this delta adopts that exact string, declares it as a named constant beside `TAG_RVSEC` and `TAG_RVSEC_COV`, and adds it to `default_tags`. It is 7 characters, well inside the 23-character bound the device enforces on logcat tags. The two existing entries keep their position and order, so the addition is purely additive in the same sense the diagnostic tags are.

One consequence has to be stated because it reaches beyond `aperv-tool`: `default_tags` is global to every capture, so every tool's runs — `monkey`, `droidbot`, `rvagent` and the rest — will be launched with the heartbeat tag in their filter. This costs nothing and captures nothing for those tools, since none of them writes under that tag, but it does mean the baseline command changes for all of them, which is why the two invariants that pin that command byte-for-byte are amended here and in the `platform` delta rather than being worked around.

## Data Contracts

### Input
- `tags: List[str] | None` — explicit tag list passed to `start_capture`; when `None`, `default_tags` is used
- `TAG_APERV_HEARTBEAT: str` — the heartbeat tag constant, `"ApeRvHb"`, matching the tag the APE-RV jar writes under

### Output
- the `adb logcat` argument vector emitted by `start_capture`, whose filter section is the allowlist
- `task.result.logcat_file` — now additionally carrying one heartbeat line per exploration step of an APE-RV run

### Side-Effects
- **[Device]**: none beyond the existing capture process. The heartbeat is written by the jar, not by this module; this module only stops the device from discarding it.

### Error
- `LogcatValidationError` — raised by the existing `default_tags` validator when the tag list is empty or a tag is malformed

## Invariants

- **INV-CORE-37** (amended): WHEN `RV_LOGCAT_DIAGNOSTICS` is unset or `false`, the `adb logcat` command emitted by `LogcatManager.start_capture` MUST be byte-identical to the baseline `-v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V` (with the device serial). The previous two-tag form is superseded, not retained as an alternative: a capture that omits the heartbeat tag produces a logcat the offline join cannot use.

- **INV-CORE-53**: The heartbeat tag MUST be declared once, as the named constant `TAG_APERV_HEARTBEAT` in `rv_android_core/util/logging/constants.py`, beside `TAG_RVSEC` and `TAG_RVSEC_COV`, and `LogcatManager.default_tags` MUST be built from those three constants rather than from repeated string literals. The value MUST equal the tag the APE-RV jar writes under; a literal duplicated across the two repositories is where that equality would silently drift, and the failure mode of a mismatch is an empty capture rather than an error.

- **INV-CORE-54**: The presence of heartbeat lines in a captured logcat MUST NOT change any value produced by `parse_logcat_file` — not `calculate_metrics()`, not `total_errors`, not `unique_errors`, not any coverage value, and not the diagnostic-event collection.

  This holds for two different reasons, and only one of them was true before this change. On the violation and coverage path it holds by construction: `parse_logcat_line` dispatches on the exact tag field, so a heartbeat line yields neither an error nor a coverage record. On the **diagnostic-event** path it did not hold, and had to be made to: `DiagnosticEventParser` is stateful and assembles a multi-line block, and it closed that block on any line whose tag was not diagnostic — after which the block's remaining lines found an empty buffer and were discarded, losing the exception class, the app stack frame and the frame count. Logcat merges every process into one timestamp-ordered stream, so a crash block is contiguous only in the crashing process's own output and an interleaved line lands inside it. Block assembly therefore MUST treat a line under any non-diagnostic tag as transparent — yielding no event and **not** closing the open block — and MUST close on a diagnostic key change, a new block start, a non-threadtime line (`analysis` INV-ANA-48) or `flush()`.

  The invariant is verified rather than assumed, and the verification MUST exercise the hard case: a fixture in which a heartbeat lands **between two lines of a crash block**, not merely between blocks. An equality asserted over interleavings that cannot reach the stateful path would be green by construction. The defect this uncovered is pre-existing and tag-agnostic — an `RVSEC-COV` line in the same position does identical damage, and that tag has always been in the allowlist — so the heartbeat is not its cause, and the correction protects every consumer of the diagnostic collection rather than only APE-RV runs.

- **INV-CORE-38** (unchanged, restated for the reader): the diagnostic tag set remains additive — when `RV_LOGCAT_DIAGNOSTICS` is enabled, the three baseline tags MUST remain in the filter and MUST NOT be replaced or reordered by the diagnostic tags.

## MODIFIED Requirements

### Requirement: Opt-in Diagnostic Logcat Capture (FR33, FR34)

`LogcatManager` SHALL support an opt-in capture mode that, when enabled via the
`RV_LOGCAT_DIAGNOSTICS` flag, augments the logcat tag filter with the diagnostic tags
`AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` in addition to the baseline tags
`RVSEC:V RVSEC-COV:V ApeRvHb:V`. When the flag is disabled (the default), capture behavior MUST be
the baseline described by INV-CORE-37. The flag SHALL be exposed as a named constant
`ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` in `rv_android_core/constants.py`.

The baseline is three tags rather than two because the APE-RV step heartbeat must survive the
device-side filter; see "APE-RV Step Heartbeat Tag in the Capture Allowlist" below for why the tag
cannot be added at the point of use instead.

#### Scenario: Flag off emits the baseline command byte-for-byte
- **WHEN** `RV_LOGCAT_DIAGNOSTICS` is unset and `start_capture` is called for serial `emulator-5554`
- **THEN** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V`
- **AND** no diagnostic tag (`AndroidRuntime`, `art`, `dalvikvm`, `ActivityManager`) appears in the filter

#### Scenario: Flag on appends diagnostic tags additively
- **WHEN** `RV_LOGCAT_DIAGNOSTICS=true` and `start_capture` is called
- **THEN** the filter contains `RVSEC:V`, `RVSEC-COV:V` and `ApeRvHb:V` unchanged and in that order
- **AND** the filter additionally contains `AndroidRuntime:E`, `art:E`, `dalvikvm:E`, and `ActivityManager:W`

## ADDED Requirements

### Requirement: APE-RV Step Heartbeat Tag in the Capture Allowlist (FR33, FR34)

`LogcatManager.default_tags` SHALL include the APE-RV step heartbeat tag `ApeRvHb`, declared as the
constant `TAG_APERV_HEARTBEAT` in `rv_android_core/util/logging/constants.py` beside `TAG_RVSEC` and
`TAG_RVSEC_COV`, and appended after them so the existing two keep their position and order
(INV-CORE-53).

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
- **AND** `LogcatManager.default_tags` SHALL be `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT]`

#### Scenario: Heartbeat lines change no parsed value
- **WHEN** `parse_logcat_file` runs over a captured logcat containing 1,603 heartbeat lines, and again over the same file with those lines removed
- **THEN** `calculate_metrics()`, `total_errors`, `unique_errors` and every coverage value SHALL be identical between the two runs
- **AND** the diagnostic-event collection SHALL be identical between the two runs

#### Scenario: A run by a tool that writes no heartbeat is unaffected
- **WHEN** a `monkey` task runs with the same `default_tags`
- **THEN** the emitted command SHALL carry `ApeRvHb:V` like every other capture
- **AND** the captured file SHALL contain no line under that tag, and every downstream value SHALL be what it was before this change
