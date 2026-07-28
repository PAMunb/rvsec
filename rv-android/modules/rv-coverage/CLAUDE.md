# CLAUDE.md - rv-coverage

## Overview

Coverage analysis and tracking for Android runtime verification. Parses logcat for RV events, tracks method execution coverage in real time, detects monitored-operations (MOP) violations, and calculates multi-dimensional coverage metrics. Domain models (`RvErrorLog`, `RvCoverageLog`, `RvDiagnosticEvent`, `LogcatRepository`) come from rv-android-core. On resume, rv-platform reconstructs coverage/MOP from the logcat using this parser (see rv-platform CLAUDE.md).

## Core Components

```
src/rv_coverage/
    parser/log/logcat_parser.py       # logcat line/file parsing
    parser/log/diagnostic_parser.py   # stateful multi-line diagnostic events
    analysis/coverage/tracker.py      # real-time coverage tracking
    analysis/coverage/analyzer.py     # batch analysis with fallback
```

- **LogcatParser** — `parse_logcat_line()`, `parse_logcat_file()` (→ `LogcatRepository`). Stateless: one line → at most one record. Real-time streaming is the tracker's tail loop, not a parser generator.
- **DiagnosticEventParser** — stateful, multi-line: `feed_line()` / `flush()` assemble crashes, `VerifyError`s and ANRs grouped by `(tag, pid, tid)` into `RvDiagnosticEvent`. Runs as a second pass alongside `parse_logcat_line()`; events land in the isolated `LogcatRepository.diagnostic_events` collection and never touch coverage/MOP metrics (see `docs/adr/ADR-001-separate-stateful-diagnostic-parser.md`).
- **CoverageTracker** — monitors logcat in a background thread, logs coverage/MOP detections, calculates metrics incrementally with change detection; context-manager lifecycle; thread-safe.
- **CoverageAnalyzer** — offline batch analysis; extends `BaseAnalyzer` (rv-android-core); modes `FULL_STATIC_ANALYSIS`, `PARTIAL_STATIC_ANALYSIS`, `RUNTIME_ONLY`, `FALLBACK_MODE`.

### Parser log-format contract

- Tags: **RVSEC** = property violation (error); **RVSEC-COV** = method call (coverage). Diagnostic tags (`AndroidRuntime`, `art`/`dalvikvm`, `ActivityManager`) are matched on the parsed tag field, never a line substring.
- Error formats: standard `spec,class,init,method,source,error_type,message`; FSM `class.method():::Spec went into an error state.`; generic `class.method(file:line) ::: Spec went into an error state.`
- Coverage formats: Soot signature `<class: returnType method(params)>`; triple-colon `class:::method:::params`. The triple-colon layout is still emitted by APKs instrumented with an older Coverage aspect — an APK is instrumented once and replayed across many runs.
- **Frame-form normalization** (INV-ANA-50/51/52): in the standard error format the Java `ErrorSummary` sometimes fails to split class from method and copies the whole `StackTraceElement` into both fields. `_normalize_frame()` recovers `(class, method, source)` by stripping the trailing `(<file>:<line>)` group and splitting the remainder at its **last** dot. The guard is anchored on that trailing group only — method names in the corpus contain spaces and nested parentheses, so the prefix is left unconstrained. Normalization is idempotent and byte-identical no-op on well-formed values.

## Coverage Metrics

Keys returned by `LogcatRepository.calculate_metrics()` (rv-android-core).

| Metric | Description |
|--------|-------------|
| method_coverage | % of methods executed |
| reachable_method_coverage | % of reachable methods executed |
| class_coverage | % of classes with at least one method called |
| activity_coverage | % of activities accessed |
| mop_method_coverage | % of methods reaching a monitored operation that were executed |
| direct_mop_method_coverage | Same, restricted to methods that reach a monitored operation directly |
| called_methods | Total unique methods called |
| total_errors | Number of property violations |
| unique_errors | Distinct violations at **event** granularity, keyed on `class:::method:::spec:::error_type:::message` — deliberately finer than the `(apk, class, method, spec)` key used to count unique *misuses* downstream |

## Important Notes

- **Logcat format**: parser expects `MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message`.
- **Year handling**: logcat timestamps lack a year — December logs seen in January are attributed to the previous year; other months use the current year.
- **Error vs coverage**: RVSEC → violation; RVSEC-COV → method call. Never conflate.
- **Violation identity**: downstream misuse counting keys on `(apk, class, method, spec)`. A source position leaking into `class` or `method` splits one misuse into one record per line it occurs at, which is why normalization happens here in the parser and not only in the Java monitor — already-instrumented APKs keep emitting the uncorrected form.
- **Diagnostics are isolated**: `RvDiagnosticEvent` records live in their own repository collection and are excluded from every coverage and violation metric. Callers driving the parser manually must call `flush()` at end of input, or a final buffered crash is lost.
- **Thread safety**: `CoverageTracker` uses a background monitor thread with `RLock` protection over shared state; event publishing is non-blocking.
