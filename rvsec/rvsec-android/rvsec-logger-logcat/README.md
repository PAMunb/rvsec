# rvsec-logger-logcat

Logcat-based violation logger for runtime verification on Android devices.

## Purpose

Provides `br.unb.cic.mop.eh.ErrorCollector`, the violation sink the monitors call, on top of
Android's logcat system.
When an instrumented APK runs on a device or emulator, the JavaMOP-generated monitors
report each violation to `ErrorCollector.instance().addError(...)`, and the collector
writes it to logcat under two tags, `RVSEC` and `RVSEC-OCC`. The Python `rv-platform`
module captures both tags in real time via `adb logcat` (baseline filter
`RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`, built in `rv-android-core`'s `logcat_manager.py`).

## Log Format

A violation's identity is its `ErrorSummary` (`rvsec-core`), compared over seven fields:
specification, error type, class, method, location (`file:line`), `code` and `ev`. Both
lines are written with `Log.v`.

### `RVSEC` — first occurrence

One line per identity per app process, written on the identity's first occurrence:

```
V/RVSEC: spec,classQualifiedName,className,methodName,location,errorType,<expecting envelope>
```

The seventh field is the specification's expecting text, trimmed, with every line break
escaped as `\n` so the record stays on one logcat line. Commas are left as they are: the
line is positional, and the seventh field takes everything after the sixth comma. A report
without an expecting value carries the sentinel envelope
`v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''`.

### `RVSEC-OCC` — every occurrence, counted

The collector counts every occurrence of an identity and writes:

```
V/RVSEC-OCC: spec,classQualifiedName,className,methodName,location,errorType,code,event,n
```

- The line is written on the first occurrence and afterwards at most once per identity per
  100 ms (`System.nanoTime()`). Occurrences inside the window are counted and not written.
- The first six fields are byte-identical to the first six fields of the identity's `RVSEC`
  line, so a reader joins the two by key. `code` and `event` are the identity's values from
  the envelope (`UNSPECIFIED` for a report without one). The envelope itself is not
  repeated; it is in the `RVSEC` line.
- `n` is the number of occurrences of the identity in the process up to and including this
  one, suppressed occurrences included. The difference between two consecutive `n` values of
  an identity is how many occurrences fell between its two lines.
- Occurrences after an identity's last written line are counted in memory and never
  written, so the last `n` of an identity is a lower bound on its occurrences.

On a first occurrence the `RVSEC` line is written before the `RVSEC-OCC` line with `n=1`.

Coverage events (`RVSEC-COV`) are produced separately by the weaver's `Coverage.aj`,
not by this module.

## Threading

Monitors call the collector from whatever thread runs the monitored code. The singleton
is created when the class loads, the first-occurrence set and the per-identity counters
are `ConcurrentHashMap`-backed, and the 100 ms window is claimed with a compare-and-set,
so two threads never write two lines for one identity in one window. `reset()` clears
both the first-occurrence set and the counters.

## Integration

```
Instrumented APK (on device)
    -> rvsec-logger-logcat (this module, runs inside APK)
    -> Android logcat stream (RVSEC, RVSEC-OCC)
    -> rv-platform (Python, captures via adb logcat)
    -> rv-coverage (Python, parses RVSEC; RVSEC-OCC is read by tag by the offline analysis)
```

## Build

```bash
mvn clean install
```

## Dependencies

- `rvsec-core`: error types (`ErrorDescription`, `ErrorSummary`, `ErrorType`)
- Android SDK (logcat API, `provided` scope)
