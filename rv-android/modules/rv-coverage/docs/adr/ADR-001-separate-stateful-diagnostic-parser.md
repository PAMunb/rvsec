# ADR-001: Separate Stateful Diagnostic Parser over a Union Return Type

## Status

Accepted

## Date

2026-06-23

## Context

Logcat parsing in rv-coverage is built around `parse_logcat_line(line)` in
`modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`. It is a pure, stateless function
that maps exactly one logcat line to at most one record and returns a 2-tuple `(error, coverage)`.
Both the live path (`CoverageTracker._process_line`) and the offline/resume path
(`parse_logcat_file`) depend on this shape, and the public API re-exports it through
`rv_coverage/__init__.py`.

Change gh72 (GitHub Issue #72) adds capture and structuring of *diagnostic* events — application
crashes (`AndroidRuntime:E`), class-load `VerifyError`s (`art`/`dalvikvm:E`), and ANRs
(`ActivityManager:W`). Unlike RVSEC/COV records, a diagnostic event is **multi-line and stateful**:
its content spans many logcat lines that must be assembled by `(tag, pid, tid)` and only closes when
the key changes or a non-continuation line arrives. This is structurally different from the
"one line → one record" contract that `parse_logcat_line` was designed around.

The forces at play:

- **Hot-path stability (G1 non-regression).** With the diagnostics flag off, the RVSEC/COV parse
  output must remain byte-identical to baseline — every experiment depends on that baseline
  (memory: `feedback_never_change_experiment_config`). Any change that touches the existing parse
  path risks perturbing coverage/MOP metrics.
- **Public API surface.** `parse_logcat_line` is re-exported; changing its signature is a breaking
  API change with a measurable blast radius.
- **Structural mismatch.** Stateful multi-line assembly does not fit a stateless per-line function.

Without a decision, diagnostics would either be bolted onto the existing function (entangling
stateful logic with the stateless hot path) or left out (the invisible-confounder problem the change
exists to solve: an instrumented APK that crashes early looks like a low-coverage tool result).

The full blast-radius investigation and decision record (D1, §11.1) are in
`docs/20260621_plano_logcat_tags_expandidas.md` and
`openspec/changes/gh72-logcat-diagnostic-events/design.md`.

## Decision Drivers

- **Hot-path non-regression (must-have)**: The RVSEC/COV parse path produces the metrics every
  experiment baseline relies on; it must not change behaviorally when diagnostics are off.
- **P1 Simplicity (must-have)**: Keep the stateless per-line contract that already exists; do not
  conflate it with stateful multi-line assembly.
- **Blast radius / backward compatibility (must-have)**: Changing the public `parse_logcat_line`
  signature touches production call-sites, tests, and the re-exported API.
- **Testability (should-have)**: Stateful assembly is easier to test in isolation than woven into the
  existing parse path.

## Considered Options

### Option A: Union return type for `parse_logcat_line`

**Description**: Refactor `parse_logcat_line` to return a single `Optional[RvLogEvent]` where
`RvLogEvent` is a union base class for error, coverage, and diagnostic records (or, equivalently, a
3-tuple `(error, coverage, diagnostic)`). The multi-line state would be carried by the caller or by
the union model.

**Pros**:
- Single entry point for all logcat-derived records.
- Diagnostics flow through the same call as RVSEC/COV.

**Cons**:
- Breaks the public API: `parse_logcat_line` is re-exported via `rv_coverage/__init__.py`.
- Blast radius of 6 production call-sites + 7 test asserts that assume the 2-tuple shape.
- Forces stateful multi-line logic into a function whose contract is stateless per-line, contradicting
  the structural reality (RVSEC/COV is 1 line → 1 record; diagnostics are multi-line).
- Risks perturbing the hot path the non-regression gate (G1) is meant to protect, with no offsetting
  benefit on that path.

### Option B: Separate stateful `DiagnosticEventParser`

**Description**: Leave `parse_logcat_line` untouched as a pure 2-tuple function. Introduce a new
`DiagnosticEventParser` (`modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py`) that
holds the multi-line state and exposes `feed_line(line) -> Optional[RvDiagnosticEvent]` plus
`flush() -> Optional[RvDiagnosticEvent]`. Both the live tracker and the offline file parser drive the
two parsers side by side.

**Pros**:
- Zero churn on the hot path: `parse_logcat_line` and the public API are unchanged, so the G1
  byte-identical gate holds by construction.
- Stateful logic is isolated where it belongs, separate from the stateless per-line contract.
- Additive change: new file, new model, no edits to existing call-sites' contracts.
- The stateful parser is independently unit-testable (multi-line assembly, flush, categories,
  false-positive guards).

**Cons**:
- Two parsers run over the same line stream (a second pass per line), a small constant overhead.
- Callers must drive both parsers and remember to `flush()` at end of input.

## Decision

We will keep `parse_logcat_line` as a pure 2-tuple function and introduce a separate stateful
`DiagnosticEventParser` (Option B) because it adds diagnostics without touching the RVSEC/COV hot path
or the public API, satisfying the non-regression gate by construction.

The RVSEC/COV path (1 line → 1 record) stays orthogonal to diagnostics (multi-line, stateful). The
live `CoverageTracker` and the offline `parse_logcat_file` each feed every line to both
`parse_logcat_line` (RVSEC/COV) and a `DiagnosticEventParser` instance (diagnostics); completed
diagnostic events are registered into an isolated repository collection. Turning the existing function
into a 3-tuple `(error, coverage, diagnostic)` is explicitly rejected — it is Option A in disguise and
contradicts this decision.

## Consequences

### Positive
- The G1 non-regression constraint holds by construction: with the flag off, the parse path and its
  outputs are byte-identical to baseline.
- Stateful multi-line assembly is contained in one testable component, keeping the per-line contract
  simple (P1).
- The change is additive — no edits to the 6 production call-sites or 7 test asserts that depend on
  the 2-tuple, and the public API is unchanged.

### Negative
- A second per-line pass runs over the logcat stream when diagnostics are enabled (small constant
  overhead; bounded by named error-priority tags, no `*:E` catch-all).
- Callers carry the responsibility of driving two parsers and invoking `flush()` at end of input;
  forgetting `flush()` can truncate a final buffered event.

### Risks
- **A final event is left buffered if `flush()` is not called** → tracker flushes at stop and on key
  change; revisit with a quiescence timeout if a final crash is observed truncated (Open Question in
  design.md).
- **State in the new parser could regress the hot path indirectly** → mitigated by keeping
  `parse_logcat_line` byte-for-byte unchanged and guarding it with the RVSEC/COV golden re-parse test
  (`test_rvsec_cov_golden`).

## Implementation Notes

- New file: `modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py` with
  `DiagnosticEventParser.feed_line` / `flush`.
- `parse_logcat_line` in `logcat_parser.py` is unchanged; `parse_logcat_file` and `CoverageTracker`
  drive both parsers.
- Diagnostic events are registered into the isolated `diagnostic_events` collection on
  `LogcatRepository` (see D4), keeping coverage/MOP metrics untouched.
- Tag match is performed on the parsed tag field, not a line substring, to avoid false positives such
  as an `isAndroidRuntime()` substring (INV-ANA-47).

## References

- GitHub Issue: #72
- Phase 0 ideation (authoritative, D1 / §11.1): `docs/20260621_plano_logcat_tags_expandidas.md`
- Design (D1): `openspec/changes/gh72-logcat-diagnostic-events/design.md`
- Proposal: `openspec/changes/gh72-logcat-diagnostic-events/proposal.md`
- Affected code:
  - `modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py` (unchanged hot path)
  - `modules/rv-coverage/src/rv_coverage/parser/log/diagnostic_parser.py` (new)
  - `modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`
  - `modules/rv-android-core/src/rv_android_core/domain/log.py` (`RvDiagnosticEvent`)
  - `modules/rv-android-core/src/rv_android_core/domain/coverage.py` (`LogcatRepository`)
- Related invariants: INV-ANA-46 / INV-ANA-47 / INV-ANA-48, INV-CORE-39
