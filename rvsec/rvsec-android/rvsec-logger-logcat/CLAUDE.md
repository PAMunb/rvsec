# CLAUDE.md - rvsec-logger-logcat

## Purpose

Android-side violation logger: single class `br.unb.cic.mop.eh.ErrorCollector`
(same FQCN as `rvsec-logger-csv`'s — the two are mutually exclusive, only one is
woven per instrumented APK). It writes two logcat streams, both with `Log.v`:

- **`RVSEC`** — the first occurrence of an identity per process. The identity is the
  seven-field `ErrorSummary` (spec, error type, class, method, location, `code`, `ev`).
  Line: `spec,classQualifiedName,className,methodName,location,errorType,<escaped expecting envelope>`.
- **`RVSEC-OCC`** — every occurrence, counted. Written on the first occurrence and then at
  most once per identity per 100 ms (`OCC_INTERVAL_NANOS`, on `System.nanoTime()`). Line:
  `spec,classQualifiedName,className,methodName,location,errorType,code,event,n`. The first
  six fields are identical to the `RVSEC` line's, so the two join by key; `n` counts every
  occurrence, suppressed ones included. Occurrences after an identity's last line are never
  written, so the last `n` is a lower bound.

`addError` decides the `RVSEC` line first, then the `RVSEC-OCC` line, so on a first
occurrence `RVSEC` precedes `RVSEC-OCC` with `n=1`.

## Role in pipeline

Provides the `ErrorCollector` API the JavaMOP-generated monitors call at runtime
inside the instrumented APK on-device; this is the Android-path equivalent of the
JSE-path CSV logger. Every report of the `jca` and `jca_android` sets reaches
`addError(ErrorDescription)` (the two convenience overloads build one and delegate).

## Key behavior

- **Line builders free of `android.util.Log`.** `buildLine` (the `RVSEC` text) and
  `occurrenceLine` (count, throttle, `RVSEC-OCC` text or `null`) are package-private and
  testable off the device. `buildLine` passes the trimmed expecting text through `escape()`,
  which replaces line breaks with `\n` and leaves commas untouched; a `null` expecting
  yields `SENTINEL_ENVELOPE` (`v=1 code=UNSPECIFIED ev=UNSPECIFIED obj='' val='' exp='' msg=''`).
- **Thread safety.** The singleton is created at class load. The first-occurrence set and
  the per-identity counters are `ConcurrentHashMap`-backed; the counter is keyed by
  `ErrorSummary`. The window opens when an identity's state is created, and an expired
  window is claimed with a compare-and-set, so one window yields at most one line.
  `reset()` clears both structures in place.

## Relationships

- Depends on `rvsec-core` (error types) and `com.google.android:android` (`provided`,
  compile-only — supplied by the Android runtime at execution time).
- ⟶ `rv-android` (Python, `logcat_manager.py` in `rv-android-core`) captures with the
  baseline filter `RVSEC:V RVSEC-COV:V ApeRvHb:V RVSEC-OCC:V`. This module writes
  `RVSEC` and `RVSEC-OCC` only; `RVSEC-COV` comes from the weaver and `ApeRvHb` from the
  APE-RV jar. The host names the occurrence tag once, as `TAG_RVSEC_OCC`, and must match
  the string written here.
- `rv-coverage`'s parser reads `RVSEC` and `RVSEC-COV` by exact tag; `RVSEC-OCC` lines are
  counted as other-tag lines and change no parsed value. The occurrence stream is read by tag
  by the offline analysis.

## Dependencies

- Internal: `rvsec-core`.
- External: `com.google.android:android` (`provided` scope, compile-only Android stub).

## Gotchas

- Every `android.util.Log` method in the stub jar throws `RuntimeException("Stub!")`, so the
  tests (`ErrorCollectorTest`) never call `addError`; they test `buildLine`, `escape` and
  `occurrenceLine` directly. The order of the two decisions inside `addError` is checked by
  reading the method.
- Coverage events (`RVSEC-COV`) are produced by the weaver's `Coverage.aj` (dexlib2/ajc
  instrumentation), not by this module.
- The instrumenters resolve this jar from the local Maven repository
  (`mvn dependency:copy-dependencies`), so an APK keeps the collector it was instrumented
  with. An APK whose capture has no `RVSEC-OCC` line at all while it has `RVSEC` lines was
  instrumented with a collector that does not write the occurrence stream.
