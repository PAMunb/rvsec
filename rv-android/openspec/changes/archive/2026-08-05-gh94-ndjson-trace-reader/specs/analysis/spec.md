# analysis Delta Specification — Foreign-Tag Lines Are Transparent to Diagnostic Block Assembly

## Purpose

`DiagnosticEventParser` (`modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py`) assembles the multi-line diagnostic events a captured logcat carries: a crash is a `FATAL EXCEPTION` header followed by a `Process:` line, the exception line, N stack frames, `Caused by:` and `... N more`, all sharing one `(tag, pid, tid)`. Unlike the `RVSEC` / `RVSEC-COV` records — one line, one record, handled by the stateless `parse_logcat_line` — assembling one of these means holding state across lines and deciding, at each line, whether the block is still open.

That decision was wrong, and this delta corrects it. The parser treated **any** line whose tag was not diagnostic as the end of the block. The reasoning was that a foreign line marks a boundary; the fact that defeats it is that logcat is not one process's output. It is a single stream into which the device merges every process, ordered by timestamp. A crash block is contiguous only in the *crashing* process's own output — between two of its frames, the kernel, the activity manager, the instrumented application under test, and the exploration agent all continue writing. So a foreign line inside a block is the normal case, not the boundary case.

The consequence was silent and total for the affected event. Closing early truncated it at the interleaving point, and the frames arriving afterwards then found an empty buffer and were not a block start, so they were discarded without a count or a log. What is lost is exactly what a diagnostic event is read for: the exception class, the first application stack frame, and the frame count. A caller comparing two runs would see a crash recorded in both and no indication that one of them had been cut.

The defect is older than the change that found it and is independent of any one tag. It surfaced while verifying core INV-CORE-54 — that the APE-RV step heartbeat changes no value `parse_logcat_file` produces — but a control fixture shows an `RVSEC-COV` line in the same position doing identical damage, and that tag has always been in the capture allowlist. The heartbeat is therefore not the cause; it would only have been one more source of an interleaving that the coverage stream already produces far more often. Realized impact on the recorded corpus is nil — 2 of 48,822 captured logcats carry `AndroidRuntime` lines at all, because the diagnostic tags reach the file only when `RV_LOGCAT_DIAGNOSTICS` is enabled — so this is a correction that protects future captures rather than one that revises past results.

Grouping by `(tag, pid, tid)` is what makes the fix available without new machinery: the key already identifies the block, so a foreign line can simply be ignored rather than interpreted.

## Data Contracts

### Input

- `line: str` — one raw logcat line, fed to `feed_line()` by both `parse_logcat_file` (offline / resume) and `CoverageTracker` (live), in file order (source: `task.result.logcat_file`)

### Output

- `RvDiagnosticEvent | None` — returned by `feed_line()` when the line closes a buffered block, and by `flush()` for a block still open at end of input (destination: `LogcatRepository.diagnostic_events`)

### Side-Effects

- **[Parser state]**: the buffered block and its `(tag, pid, tid)` key. No filesystem or device access.

### Error

- None propagate: a malformed block is logged at WARNING inside `_close()` and yields no event, rather than aborting the parse of the remaining file.

## Invariants

- **INV-ANA-56**: A logcat line whose parsed tag field is not a diagnostic tag MUST be transparent to diagnostic block assembly. It MUST yield no event and MUST NOT close an open block. Logcat merges every process into one timestamp-ordered stream, so a line under a foreign tag arriving between two lines of a block is the expected case and carries no information about whether that block has ended. Closing on it truncates the event at the interleaving point and discards its remaining lines, and both losses are silent.

- **INV-ANA-48** (unchanged, restated because it bounds the rule above): a multi-line block sharing one `(tag, pid, tid)` MUST yield exactly one `RvDiagnosticEvent`, and a line that does not match the threadtime regex — `--------- beginning of crash` — MUST be skipped without error. Such a line remains a real boundary and still closes an open block: unlike a foreign-tag line, it is written by logcat itself to mark a discontinuity, not by another process that merely happened to log.

- **INV-ANA-57**: A caller driving the parser directly MUST call `flush()` at end of input. With foreign-tag lines transparent, a block is closed by a diagnostic key change, a new block start, a non-threadtime line, or `flush()` — so a block at the end of the input is emitted only by the flush. `parse_logcat_file` flushes internally; `CoverageTracker` flushes after its final drain, in that order, so a block completed by the drained lines is emitted rather than discarded.

## MODIFIED Requirements

### Requirement: Stateful Diagnostic Event Parsing (FR12, FR13)

The analysis domain SHALL provide a stateful `DiagnosticEventParser` that assembles diagnostic events
from logcat lines while leaving `parse_logcat_line` (RVSEC/RVSEC-COV) unchanged. It SHALL group lines
sharing one `(tag, pid, tid)` into one event.

An open block SHALL be closed when, and only when, one of the following occurs: a diagnostic line
arrives whose `(tag, pid, tid)` key differs from the open block's; a diagnostic line arrives that
starts a new event; a line arrives that does not match the threadtime format (INV-ANA-48); or
`flush()` is called at end of input.

A line under any tag outside the diagnostic set — `RVSEC`, `RVSEC-COV`, `ApeRvHb`, or any other —
SHALL NOT close an open block and SHALL produce no event (INV-ANA-56). Lines between the block's own
lines come from other processes sharing the stream and say nothing about whether the block has ended.

Both `parse_logcat_file` and `CoverageTracker` SHALL feed every line to a `DiagnosticEventParser` and
register emitted events via `LogcatRepository.register_diagnostic_event`. Diagnostic events SHALL
remain isolated in their own repository collection and SHALL enter no coverage, MOP or violation
metric.

#### Scenario: Multi-line AndroidRuntime FATAL assembled into one crash event
- **WHEN** the input contains `E AndroidRuntime: FATAL EXCEPTION: main`, then
  `E AndroidRuntime: Process: br.unb.cic.cryptoapp, PID: 7071`, then
  `E AndroidRuntime: java.lang.NullPointerException: ...getPackageName()...`, then several
  `E AndroidRuntime: \tat ...` frames, all with pid/tid `7071/7071`
- **THEN** exactly one `RvDiagnosticEvent` is emitted with `category="crash"`, `fatal=true`,
  `exception_class="java.lang.NullPointerException"`, `process="br.unb.cic.cryptoapp"`
- **AND** `n_frames` equals the number of `\tat` frames and `stack_head` is the first frame

#### Scenario: A foreign-tag line inside a crash block does not truncate it
- **WHEN** a crash block's `FATAL EXCEPTION`, `Process:` and exception lines are followed by an
  `I RVSEC-COV: <com.x.A: void m()>` line from pid `9000`, and then by the block's own
  `E AndroidRuntime: \tat com.x.A.m(A.java:1)` frame from pid `7071`
- **THEN** the `RVSEC-COV` line SHALL produce no diagnostic event and SHALL leave the block open
- **AND** the frame following it SHALL still belong to that block
- **AND** the emitted event SHALL carry `class_full_name` set, `n_frames` counting the frame that
  followed the interleaved line, and `stack_head` naming it
- **AND** the foreign line's text SHALL NOT appear in the event's `original_msg`

#### Scenario: Event closes on a diagnostic key change and flush at EOF
- **WHEN** a crash block from pid `7071` is followed by a `FATAL EXCEPTION` line from pid `8080`,
  then input ends
- **THEN** the first block SHALL be emitted when the second one starts
- **AND** `flush()` at EOF SHALL emit the second block, so nothing is lost

#### Scenario: A separator line still closes the block
- **WHEN** an open crash block is followed by the non-threadtime line
  `--------- beginning of crash`
- **THEN** the block SHALL be closed and the separator SHALL be skipped without error (INV-ANA-48)
- **AND** the separator SHALL NOT appear in the event's `original_msg`

#### Scenario: A trailing block requires the caller's flush
- **WHEN** a caller feeds a crash block that is still open when the input ends and does not call
  `flush()`
- **THEN** no event is emitted for that block (INV-ANA-57)
- **AND** `parse_logcat_file` SHALL NOT exhibit this, because it flushes internally
- **AND** `CoverageTracker` SHALL NOT exhibit this, because it drains the unread tail and then
  flushes, in that order

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
