# CLAUDE.md - rv-coverage

## Overview

Coverage analysis and tracking for Android runtime verification. Parses logcat for RV events, tracks method execution coverage in real time, detects monitored-operations (MOP) violations, and calculates multi-dimensional coverage metrics. Domain models (`RvErrorLog`, `RvCoverageLog`, `LogcatRepository`) come from rv-android-core. On resume, rv-platform reconstructs coverage/MOP from the logcat using this parser (see rv-platform CLAUDE.md).

## Core Components

```
src/rv_coverage/
    parser/log/logcat_parser.py       # logcat line/file parsing
    parser/log/diagnostic_parser.py   # diagnostic-line parsing
    analysis/coverage/tracker.py      # real-time coverage tracking
    analysis/coverage/analyzer.py     # batch analysis with fallback
```

- **LogcatParser** — `parse_logcat_line()`, `parse_logcat_file()` (→ `LogcatRepository`), `stream_logcat_entries()` (generator for real-time streaming).
- **CoverageTracker** — monitors logcat in a background thread, logs coverage/MOP detections, calculates metrics incrementally with change detection; context-manager lifecycle; thread-safe.
- **CoverageAnalyzer** — offline batch analysis; extends `BaseAnalyzer` (rv-android-core); modes `FULL_STATIC_ANALYSIS`, `PARTIAL_STATIC_ANALYSIS`, `RUNTIME_ONLY`, `FALLBACK_MODE`.

### Parser log-format contract

- Tags: **RVSEC** = property violation (error); **RVSEC-COV** = method call (coverage).
- Error formats: standard `spec,class,init,method,source,error_type,message`; FSM `class.method():::Spec went into an error state.`; generic `class.method(file:line) ::: Spec went into an error state.`
- Coverage formats: modern `<class: returnType method(params)>`; legacy `class:::method:::params`.

## Coverage Metrics

| Metric | Description |
|--------|-------------|
| method_coverage | % of reachable methods executed |
| activity_coverage | % of activities accessed |
| mop_method_coverage | Coverage of monitored-operations methods |
| called_methods | Total unique methods called |
| total_errors | Number of property violations |

## Important Notes

- **Logcat format**: parser expects `MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message`.
- **Year handling**: logcat timestamps lack a year — December logs seen in January are attributed to the previous year; other months use the current year.
- **Error vs coverage**: RVSEC → violation; RVSEC-COV → method call. Never conflate.
- **Thread safety**: `CoverageTracker` uses a background monitor thread with `RLock` protection over shared state; event publishing is non-blocking.
