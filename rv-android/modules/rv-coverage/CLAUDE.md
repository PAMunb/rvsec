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

- **LogcatParser** — `parse_logcat_line(line, diagnostics=None)`, `parse_logcat_file(log_file, static_data, tool_execution_start)` (→ `LogcatRepository`). Stateless: one line → at most one record. Real-time streaming is the tracker's tail loop, not a parser generator. `parse_logcat_file` never swallows an error raised while iterating: it logs the 1-based line number and re-raises, so a caller cannot mistake a partial repository for a complete one.
- **ParserDiagnostics** (rv-android-core, `domain/coverage.py`) — 13 counters carried by `LogcatRepository.parser_diagnostics`. It lives beside the repository because rv-android-core cannot import rv-coverage. rv-coverage constructs nothing: `CoverageTracker` passes `self.repository.parser_diagnostics` into `parse_logcat_line`, and `parse_logcat_file` increments the repository's own object — so the live and the offline path count onto the same totals.
- **DiagnosticEventParser** — stateful, multi-line: `feed_line()` / `flush()` assemble crashes, `VerifyError`s and ANRs grouped by `(tag, pid, tid)` into `RvDiagnosticEvent`. Runs as a second pass alongside `parse_logcat_line()`; events land in the isolated `LogcatRepository.diagnostic_events` collection and never touch coverage/MOP metrics (see `docs/adr/ADR-001-separate-stateful-diagnostic-parser.md`).
- **CoverageTracker** — monitors logcat in a background thread, logs coverage/MOP detections, calculates metrics incrementally with change detection; context-manager lifecycle; thread-safe.
- **CoverageAnalyzer** — offline batch analysis; extends `BaseAnalyzer` (rv-android-core); modes `FULL_STATIC_ANALYSIS`, `PARTIAL_STATIC_ANALYSIS`, `RUNTIME_ONLY`, `FALLBACK_MODE`.

### Parser log-format contract

- Tags: **RVSEC** = property violation (error); **RVSEC-COV** = method call (coverage). Diagnostic tags (`AndroidRuntime`, `art`/`dalvikvm`, `ActivityManager`) are matched on the parsed tag field, never a line substring.
- Error formats, each recognised by structure and tried in this order:
  - **Format 1 (generic)** `class.method(file:line) ::: Spec went into an error state.` — selected by the suffix **and** the spaced ` ::: ` separator. Both are required, because Format 3 ends in the same words with an unspaced `:::`. A line that matches the punctuation but whose regex fails is dropped and counted (`format1_regex_failed`), never retried as Format 2: a name bearing five commas would otherwise parse into a JCA record whose every field is a fragment of a value.
  - **Format 2 (JCA)** `spec,classQualifiedName,className,methodName,location,errorType,expecting` — selected by six or more comma-separated parts. Field 3 is redundant with field 2 and is not stored; fields 7 onwards are rejoined with `,` into `message`, since commas inside a message are legal. This is the only format whose class and method arrive pre-split from Java, so it is the only one that runs `_normalize_frame()`.
  - **Format 3 (FSM)** `class.method(params):::Spec message` — selected by `:::`. The line carries no source position at all, so `source` is the sentinel `UNSPECIFIED:0` (counted), never a fabricated `Unknown Source:1`.
- Coverage formats: Soot signature `<class: returnType method(params)>`; triple-colon `class:::method:::params`. The triple-colon layout is still emitted by APKs instrumented with an older Coverage aspect — an APK is instrumented once and replayed across many runs.
- **Frame-form normalization** (INV-ANA-50/51/52): in the standard error format the Java `ErrorSummary` sometimes fails to split class from method and copies the whole `StackTraceElement` into both fields. `_normalize_frame()` recovers `(class, method, source)` by stripping the trailing `(<file>:<line>)` group and splitting the remainder at its **last** dot. The guard is anchored on that trailing group only — method names in the corpus contain spaces and nested parentheses, so the prefix is left unconstrained. Normalization is idempotent and byte-identical no-op on well-formed values.

### v1 message envelope (INV-ANA-63)

The seventh field of a Format-2 line written by the `jca_android` monitors is an envelope: `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`. Bare values carry no space; quoted values are delimited by `'`, with `\'` as the escape and `\n` for a newline the collector escaped so logcat would not split the line. `_parse_envelope()` scans it by hand rather than by regex, because the escape has to be undone as the value is read and an unclosed closing quote is evidence, not a non-match.

- `v=1` is what decides whether a message is an envelope — the presence of the keys is not, or a pre-envelope sentence quoting `ev=` would erase the boundary between the two eras.
- An **unclosed final quote** means logcat cut the payload (4068 bytes, no marker): the record is registered with `truncated=True` and counted under `truncated_envelopes`, keeping the fields parsed before the cut and nothing from the cut value onwards.
- A value containing `:::` is kept **verbatim** and counted under `envelope_forbidden_chars` (one per record). The producer contract forbids the character because it separates `unique_msg`; the parser counts the defect, it does not repair it.
- A non-envelope message (the frozen `jca` set, a legacy `unknown`, a free-text `expecting …`) leaves `code`/`event` at `UNSPECIFIED` and `obj`/`val`/`exp`/`msg` empty. An envelope whose `code=` or `ev=` is itself the literal `UNSPECIFIED` — the collector's `null` guard — counts under the same sentinel counters: the value is a sentinel whoever wrote it.

### Discard and sentinel accounting (INV-ANA-62)

No line is dropped silently. Every line that does not become a record increments exactly one of the seven discard counters, and every value the parser substitutes for one the producer did not supply is counted under its own name. The gate is arithmetic: records registered plus counted lines equals lines read. Diagnostic-tag lines are neither records nor discards here — they are the raw material `DiagnosticEventParser` assembles on its own pass.

| Discard counter | Line it accounts for |
|---|---|
| lines_not_threadtime | not in Android's threadtime format (`--------- beginning of crash`, a truncated tail) |
| lines_other_tag | well-formed, under a tag that is neither RVSEC, RVSEC-COV nor a diagnostic tag |
| format1_regex_failed | Format-1 punctuation, regex did not match |
| format2_short | one to four commas, no `:::`, no Format-1 suffix — logcat cut the payload before the sixth comma |
| format3_unresolved | a `:::` message whose left part has no dot (the `[helper] ::: ` lines of `generic_new`) |
| unrecognised | matched none of the three formats |
| continuation_lines | an unrecognised message immediately following, from the same `(pid, tid)`, a record flagged truncated |

Sentinel and grammar counters: `truncated_envelopes`, `sentinel_error_type`, `sentinel_source`, `sentinel_code`, `sentinel_event`, `envelope_forbidden_chars`. They are excluded from `discarded_lines` — those lines did become records.

Continuation detection is one-shot: `last_truncated_key` is armed by a truncated record and cleared on the next line from that thread, so a truncation can swallow at most one following line, and that line is counted rather than dropped. The after-the-fact rule alone cannot prevent a split second half carrying six commas from parsing as a second record.

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
| unique_errors | Distinct violations at **event** granularity, keyed on `class:::method:::spec:::error_type:::code:::event:::message` — seven `:::` parts, deliberately finer than the `(apk, class, method, spec)` key used to count unique *misuses* downstream. `code` and `event` come from the message envelope and name which automaton transition failed; they are `UNSPECIFIED` for every record with no envelope, so two causes at one call site stay distinct |

## Important Notes

- **Logcat format**: parser expects `MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message`.
- **Year handling**: logcat timestamps lack a year — December logs seen in January are attributed to the previous year; other months use the current year.
- **Error vs coverage**: RVSEC → violation; RVSEC-COV → method call. Never conflate.
- **Violation identity**: downstream misuse counting keys on `(apk, class, method, spec)`. A source position leaking into `class` or `method` splits one misuse into one record per line it occurs at, which is why normalization happens here in the parser and not only in the Java monitor — already-instrumented APKs keep emitting the uncorrected form.
- **Diagnostics are isolated**: `RvDiagnosticEvent` records live in their own repository collection and are excluded from every coverage and violation metric. Callers driving the parser manually must call `flush()` at end of input, or a final buffered crash is lost.
- **Thread safety**: `CoverageTracker` uses a background monitor thread with `RLock` protection over shared state; event publishing is non-blocking.
- **No invented values**: a field the producer did not supply becomes the explicit sentinel `UNSPECIFIED` (`UNSPECIFIED:0` for a source position), never a plausible-looking `Unknown Source:1` or `No additional message` — an invented value reads as a measurement in every file it reaches and there is no way back from it. An absent seventh comma field is `message=""`.
- **`unique_msg` is composed once**, in `RvErrorLog` (rv-android-core). Readers key on it; nothing downstream recomposes it, and an absent CSV column is a `KeyError` rather than a second composition that could disagree.
