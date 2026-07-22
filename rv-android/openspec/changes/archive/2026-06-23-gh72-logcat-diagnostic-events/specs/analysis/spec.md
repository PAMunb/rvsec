# Delta Spec: Analysis — Logcat Diagnostic Event Parsing

## Purpose

The analysis domain parses captured logcat into structured data (`rv-coverage`:
`parser/log/logcat_parser.py`, `analysis/coverage/tracker.py`). Today `parse_logcat_line` is a pure,
stateless function returning `(Optional[RvErrorLog], Optional[RvCoverageLog])` — one line maps to at
most one record — and the `CoverageTracker` calls it per line on a background thread.

This delta adds parsing for execution-level diagnostic events without disturbing that hot path. The
hard part is that diagnostic events are **multi-line**: an `AndroidRuntime` FATAL block is a header line
plus N stack-frame lines (`\tat ...`, `Caused by:`, `... N more`), all sharing the same `(tag, pid,
tid)`. A pure per-line function cannot assemble them. The chosen design (decision D1, by blast-radius)
keeps `parse_logcat_line` untouched and introduces a separate **stateful** `DiagnosticEventParser` with
`feed_line(line) -> Optional[RvDiagnosticEvent]` and `flush()`. It buffers consecutive lines of the same
`(tag, pid, tid)`, closing an event when that key changes or a non-continuation line arrives, and
emitting the last buffered event at EOF via `flush()`.

The parser produces three categories: `crash` (`AndroidRuntime:E` FATAL blocks, including
`Caused by: java.lang.VerifyError` at runtime), `verify_error` (`art`/`dalvikvm` class-load rejection,
e.g. `Rejecting class` / `Verification error`), and `anr` (`ActivityManager` `ANR in <pkg>` /
`Process ... has died`). App attribution is taken from the block itself (`Process: <pkg>` for crashes,
`ANR in <pkg>` for ANRs), not from a live PID. Both `parse_logcat_file` (the offline / resume
reconstruction path) and `CoverageTracker` drive a `DiagnosticEventParser` and register completed events
via `LogcatRepository.register_diagnostic_event`.

## Data Contracts

### Input
- `line: str` — a raw logcat line in threadtime format (`MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message`).
- diagnostic tags present only when capture ran with `RV_LOGCAT_DIAGNOSTICS=true` (core domain).

### Output
- `RvDiagnosticEvent` — emitted by `DiagnosticEventParser.feed_line`/`flush`, registered into
  `LogcatRepository.diagnostic_events`.

### Side-Effects
- None (pure parsing into in-memory repository).

### Error
- Unparseable diagnostic content SHALL be logged at WARNING and skipped (no malformed events emitted),
  mirroring the existing `_parse_error_message` fallback behavior.

## Invariants

- **INV-ANA-46**: `parse_logcat_line` MUST retain its signature
  `Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]` and its existing behavior for RVSEC/RVSEC-COV
  lines (the RVSEC/COV golden output MUST be byte-identical to baseline).
- **INV-ANA-47**: Tag recognition MUST match the parsed threadtime *tag field*, never a substring of the
  message; a `RVSEC-COV` line whose message contains `isAndroidRuntime()` MUST NOT produce a diagnostic
  event.
- **INV-ANA-48**: A multi-line crash block sharing one `(tag, pid, tid)` MUST yield exactly one
  `RvDiagnosticEvent`; lines that do not match the threadtime regex (e.g. `--------- beginning of crash`)
  MUST be skipped without error.

## ADDED Requirements

### Requirement: Stateful Diagnostic Event Parsing (FR12, FR13)

The analysis domain SHALL provide a stateful `DiagnosticEventParser` that assembles diagnostic events
from logcat lines while leaving `parse_logcat_line` (RVSEC/RVSEC-COV) unchanged. It SHALL group
consecutive lines of identical `(tag, pid, tid)` into one event, close the event when the key changes or
a non-continuation line appears, and emit any buffered event on `flush()` at end of input. Both
`parse_logcat_file` and `CoverageTracker` SHALL feed every line to a `DiagnosticEventParser` and register
emitted events via `LogcatRepository.register_diagnostic_event`.

#### Scenario: Multi-line AndroidRuntime FATAL assembled into one crash event
- **WHEN** the input contains `E AndroidRuntime: FATAL EXCEPTION: main`, then
  `E AndroidRuntime: Process: br.unb.cic.cryptoapp, PID: 7071`, then
  `E AndroidRuntime: java.lang.NullPointerException: ...getPackageName()...`, then several
  `E AndroidRuntime: \tat ...` frames, all with pid/tid `7071/7071`
- **THEN** exactly one `RvDiagnosticEvent` is emitted with `category="crash"`, `fatal=true`,
  `exception_class="java.lang.NullPointerException"`, `process="br.unb.cic.cryptoapp"`
- **AND** `n_frames` equals the number of `\tat` frames and `stack_head` is the first frame

#### Scenario: Event closes on tag/pid change and flush at EOF
- **WHEN** a crash block is immediately followed by an `RVSEC-COV` line, then input ends
- **THEN** the crash event is closed when the `(tag,pid,tid)` key changes
- **AND** `flush()` at EOF emits any still-buffered event so nothing is lost

#### Scenario: VerifyError at class load
- **WHEN** the input contains `E art: Rejecting class com.foo.Bar ... Verification error`
- **THEN** one `RvDiagnosticEvent` is emitted with `category="verify_error"` naming the rejected class

#### Scenario: ANR event
- **WHEN** the input contains `E ActivityManager: ANR in br.unb.cic.cryptoapp` (or `... has died`)
- **THEN** one `RvDiagnosticEvent` is emitted with `category="anr"` and `process="br.unb.cic.cryptoapp"`

#### Scenario: RVSEC/COV path is unchanged
- **WHEN** the input is a logcat containing only `RVSEC` and `RVSEC-COV` lines (e.g. an existing
  `cmp_*` logcat)
- **THEN** `parse_logcat_line` returns the same `(RvErrorLog, RvCoverageLog)` tuples as baseline
- **AND** no `RvDiagnosticEvent` is produced

#### Scenario: Tag-field match avoids substring false positive
- **WHEN** the input contains `I RVSEC-COV: <com.foo.Utils: boolean isAndroidRuntime()>`
- **THEN** no diagnostic event is produced (the tag field is `RVSEC-COV`, not `AndroidRuntime`)
