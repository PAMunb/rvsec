# CLAUDE.md - rvsec-logger-logcat

## Purpose

Android-side violation logger: single class `br.unb.cic.mop.eh.ErrorCollector`
(same FQCN as `rvsec-logger-csv`'s — the two are mutually exclusive, only one is
woven per instrumented APK) that de-dups `ErrorDescription`s and emits each new one via
`Log.v("RVSEC", message)`.

## Role in pipeline

Provides the `ErrorCollector` API the JavaMOP-generated monitors call at runtime
inside the instrumented APK on-device; this is the Android-path equivalent of the
JSE-path CSV logger.

## Relationships

- Depends on `rvsec-core` (error types) and `com.google.android:android` (`provided`,
  compile-only — supplied by the Android runtime at execution time).
- ⟶ `rv-android` (Python, `logcat_manager.py` in `rv-android-core`) captures the
  `RVSEC` logcat tag via `adb logcat` at runtime; default tag set there is
  `["RVSEC", "RVSEC-COV"]`, but this module only ever emits `"RVSEC"` — the
  `"RVSEC-COV"` coverage tag comes from a different source (see Gotchas).

## Dependencies

- Internal: `rvsec-core`.
- External: `com.google.android:android` (`provided` scope, compile-only Android stub).

## Gotchas / README corrections

- The module README (`rvsec-logger-logcat/README.md`) documents an `E/RVSEC: <spec> violated at ...`
  format and a separate `I/RVSEC_COV: <class>.<method>(...)` coverage-event format. The
  code does not emit either: `ErrorCollector.addError` only calls
  `Log.v("RVSEC", err.getErrorSummary() + "," + err.getExpecting().trim())` — no
  `RVSEC_COV` tag, no structured "violated at" text. Coverage tags/events are produced by
  the weaver's `Coverage.aj` (dexlib2/ajc instrumentation), not by this module — confirm
  the real format against `rv-android`'s `logcat_manager.py` parser before citing any tag string.
- `escapeSpecialCharacters()` is defined but unused (the call in `addError` is commented out).
