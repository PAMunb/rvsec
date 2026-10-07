## Purpose

The logcat collector is the last link of the runtime-verification chain on the device. Every specification of the `jca` and `jca_android` sets reports a violation by calling `ErrorCollector.instance().addError(...)` (`rvsec/rvsec-android/rvsec-logger-logcat/src/main/java/br/unb/cic/mop/eh/ErrorCollector.java`), and the collector turns the report into logcat lines that the host captures and every downstream analysis reads. The collector is woven into every instrumented APK through `rvsec-logger-logcat.jar` by both instrumenters, so what it writes is what any campaign can measure.

The collector writes two streams. The `RVSEC` line is the violation record: one line per identity per app process, written on the first occurrence and carrying the full message envelope. Its identity is the seven-field `ErrorSummary` (specification, error type, class, method, `file:line`, `code`, `ev`), and every count published from the project's campaigns is a count of these lines. That stream does not change here.

The `RVSEC-OCC` line is the occurrence record this change adds. It exists because the `RVSEC` stream says only that an identity happened, never when it happened again. The offline join of the APE-RV exploration clock places each logcat line on the exploration step of the last `ApeRvHb` heartbeat before it (`aperv-tool`, `clock_logcat_join.place_on_timeline`). With the first occurrence alone, a step that re-executes violating code cannot be told apart from a step that executes nothing monitored. The occurrence stream carries every occurrence as a counter and as many lines as a throttle allows: at most one line per identity every 100 ms. 100 ms is short against an exploration step (E6 ran about one step per second), so a line still lands on the step it belongs to, and it bounds the volume a violation inside a tight loop can push into the device's log buffer. The counter keeps the occurrences the throttle suppressed visible as a jump, so the stream says how much it left out.

Both streams are keyed by one identity held in shared state, and the monitors call the collector from whatever thread runs the monitored code. The collector is therefore safe across threads: one instance, created when the class loads, and concurrent maps for the first-occurrence set and the counters.

## Data Contracts

### Input
- `err: ErrorDescription` — one violation report from a specification's handler; its `getErrorSummary()` is the identity (`rvsec-core`, `ErrorSummary.equals`/`hashCode` over seven fields).
- `nowNanos: long` — `System.nanoTime()` at the call; a monotonic clock, so a wall-clock change on the device cannot open or close a throttle window.

### Output
- `RVSEC` logcat line (`Log.v`), first occurrence of an identity only: `spec,classQualifiedName,className,methodName,location,errorType,<escaped expecting>` — unchanged.
- `RVSEC-OCC` logcat line (`Log.v`), on the first occurrence and then at most once per identity per 100 ms: `spec,classQualifiedName,className,methodName,location,errorType,code,event,n` — nine comma-separated fields; the first six are `ErrorSummary.toString()` as the `RVSEC` line writes them; `code` and `event` are `ErrorSummary.getCode()`/`getEvent()` (the sentinel `UNSPECIFIED` when the report has no envelope); `n` is the decimal count of occurrences of the identity in the process up to and including this one.

### Side-Effects
- **Device logcat**: writes to the `main` buffer under the tags `RVSEC` and `RVSEC-OCC`.
- **Collector state**: one first-occurrence entry and one counter per identity, for the life of the process; `reset()` clears both.

### Error
- None. A write the device's logger cannot accept is dropped by `android.util.Log`, never thrown into the monitored application.

## Invariants

- **INV-INS-170**: `ErrorCollector.addError(ErrorDescription)` MUST write the `RVSEC` line exactly as before this change — same text, tag, level, and first-occurrence rule — and MUST decide it before the occurrence line, so that on a first occurrence the `RVSEC` line precedes the `RVSEC-OCC` line with `n=1`.
- **INV-INS-171**: For every call of `addError`, the identity's counter MUST increase by exactly one, whether or not a line is written. The `RVSEC-OCC` line MUST be written when the new count is `1`, or when at least 100 ms (`OCC_INTERVAL_NANOS = 100_000_000L`) have passed on `System.nanoTime()` since the last `RVSEC-OCC` line of the same identity; otherwise no line MUST be written. Two threads MUST NOT both write a line for one identity in one window.
- **INV-INS-172**: The `RVSEC-OCC` line MUST be `ErrorSummary.toString() + "," + code + "," + event + "," + n`, built without `android.util.Log` so it is testable off the device, and MUST NOT carry the `expecting` text. Its first six fields MUST be byte-identical to the first six fields of the `RVSEC` line of the same identity, so a reader joins the two by key.
- **INV-INS-173**: `ErrorCollector` MUST be safe across threads: the single instance MUST be created when the class is initialised, and the first-occurrence set and the per-identity counters MUST be concurrent structures (`ConcurrentHashMap`). `reset()` MUST clear both.

## MODIFIED Requirements

### Requirement: Violation Line Emission by the Collector

The logcat `ErrorCollector` (`rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java`) SHALL emit `getErrorSummary() + "," + escape(getExpecting().trim())`, where `escape` replaces `\n` with `\\n` and leaves commas untouched, and SHALL guard a `null` expecting value with the sentinel envelope `v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''` instead of throwing. Today the escaping method exists and its call is commented out (`:38`), so a newline inside a message becomes a second logcat line the parser reads as a fabricated record. The CSV collector (`rvsec-logger-csv`) already escapes; both collectors SHALL agree on the escaping rule.

`ViolationRecorder.makeRelevantList` (`rv-monitor-rt/.../ViolationRecorder.java:87-105`) SHALL exclude a monitoring-runtime frame whose `fileName` is `null` instead of including it: today the per-frame filter is fail-open, `getLineOfCode()` returns `relevantStack.get(0)`, and a runtime frame without debug information becomes the reported `location` — which is part of the dedupe identity.

**Occurrence lines.** Besides the `RVSEC` line, which is written on the first occurrence of an identity only (INV-INS-170), the collector SHALL count every occurrence of the identity and SHALL write an `RVSEC-OCC` line under the throttle of INV-INS-171: always on the first occurrence, and afterwards at most once per identity per 100 ms. The line is `spec,classQualifiedName,className,methodName,location,errorType,code,event,n` (INV-INS-172). The first six fields are the `ErrorSummary.toString()` the `RVSEC` line starts with, so the full message is recovered by joining on the key. `code` and `event` are the identity values read from the envelope, so two causes at one call site stay two keys. `n` is the count so far. The envelope is not repeated, because the occurrence line answers *when* an identity occurred, and the *what* is already in its `RVSEC` line.

The counter counts what the throttle drops. A burst of 1 000 occurrences in 50 ms writes one line; the next line, written 100 ms or more later, carries a count at least 1 000 higher. A reader therefore sees how many occurrences fell between two lines, even though it cannot place each of them on a step. The other side of this is that occurrences after the last line of an identity are counted in memory and never written: a burst that ends in silence shows only its first line. The last `n` an identity shows is a lower bound on its occurrences, and an analysis MUST say so where it uses that `n`.

The collector SHALL be safe across threads (INV-INS-173). The monitors call it from the thread that runs the monitored code, which on Android includes the UI thread, worker pools and coroutine dispatchers. A lazily created singleton could be created twice, and each instance would keep its own counters and its own first-occurrence set. A `HashSet` can let two threads both pass `add` for one identity, which writes two `RVSEC` lines for one violation.

Every report in the `jca` and `jca_android` sets passes through `addError(ErrorDescription)`: the two convenience overloads build an `ErrorDescription` and delegate. The occurrence line is therefore emitted for every specification without any edit to a `.mop` file or a generated monitor.

#### Scenario: a message with a newline

- **WHEN** a specification composes an envelope whose `msg` contains `\n`
- **THEN** exactly one logcat line MUST be emitted, with the newline escaped
- **AND** the parser MUST recover the message with the newline restored

#### Scenario: a runtime frame without file name

- **WHEN** the top of the stack at report time is `com.runtimeverification.rvmonitor...` with `fileName == null`
- **THEN** it MUST NOT be the reported `location`
- **AND** the first application frame below it MUST be

#### Scenario: the first occurrence writes both lines in order

- **WHEN** `CipherSpec` reports `InvalidSequenceOfMethodCalls` at `com.example.Crypto.encrypt(Crypto.java:42)` with envelope `v=1 code=CIPHER-ORDER-00 ev=doFinal …` for the first time in the process
- **THEN** the collector MUST write the `RVSEC` line `CipherSpec,com.example.Crypto,Crypto,encrypt,Crypto.java:42,InvalidSequenceOfMethodCalls,v=1 code=CIPHER-ORDER-00 ev=doFinal …`
- **AND** it MUST then write the `RVSEC-OCC` line `CipherSpec,com.example.Crypto,Crypto,encrypt,Crypto.java:42,InvalidSequenceOfMethodCalls,CIPHER-ORDER-00,doFinal,1`

#### Scenario: repetitions inside one window are counted, not written

- **WHEN** the same identity is reported again at `t0 + 10 ms`, `t0 + 20 ms` and `t0 + 90 ms`, after its first occurrence at `t0`
- **THEN** no `RVSEC` line and no `RVSEC-OCC` line MUST be written for those three calls
- **AND** a fifth report at `t0 + 120 ms` MUST write the `RVSEC-OCC` line ending in `,5`

#### Scenario: a report without an envelope

- **WHEN** a report built with the three-argument `addError(type, spec, location)` arrives for the first time
- **THEN** its `RVSEC-OCC` line MUST carry `UNSPECIFIED,UNSPECIFIED` as `code` and `event`
- **AND** its `RVSEC` line MUST be the line the collector wrote for such a report before this change

#### Scenario: two threads report one identity at once

- **WHEN** 8 threads each report one identity 10 000 times at the same `nowNanos`, starting together
- **THEN** the identity's count MUST be 80 000 after all threads finish
- **AND** exactly one `RVSEC-OCC` line MUST have been produced, the one with `n = 1`, because the window opened by the first report has not expired

#### Scenario: reset clears both streams' state

- **WHEN** `reset()` is called after an identity has reached `n = 12`
- **THEN** the next report of that identity MUST write an `RVSEC` line again
- **AND** its `RVSEC-OCC` line MUST end in `,1`
