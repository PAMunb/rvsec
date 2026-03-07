## Why

GitHub Issue: [#31](https://github.com/PAMunb/rvsec/issues/31)

After gh30 fixes rvsmart's critical bugs (hash redesign, saturation, scroll, MopScorer, UI captures, action selection gaps, OOA recovery) and speed bottlenecks, the agent will have a functional foundation but still lack exploration intelligence. The Python rvagent has element-level UI coverage tracking with memory integration, a plateau detector, context-aware text input, and scored stochastic selection — none of which were ported to rvsmart during gh29. The scorer chain has parameter problems (BACK score -500 makes voluntary backtracking impossible, saturation thresholds too low causing premature backtracking, WtgScorer is a stub returning 0, ConfirmedCoverageScorer overfits to known-productive screens) and uses uniform random selection that ignores scores entirely. The stuck detector has no form action exemption (SET_TEXT increments stuck counter even though it does not change the screen hash) and uses a fixed threshold regardless of screen complexity. These gaps explain why rvsmart underperforms APE and FastBot on diverse APK sets despite its speed advantage.

## What Changes

**UI Coverage Tracking + Memory:**
- Add `UICoverageTracker` class that tracks UI elements per screen by hybrid ID (resourceId-primary, coords-fallback), records interaction counts, and computes coverage gaps (fraction of untested elements per screen)
- Enable `CoverageDensityScorer` (currently excluded) to use real coverage data from UICoverageTracker
- Add `PlateauDetector` with sliding window that detects stalled exploration (no new states AND no new MOP for 10 iterations) and boosts stochastic probability to 0.5

**Scoring and Strategy:**
- Change BACK base score from -500 to -100
- Replace score-based proactive backtrack trigger with saturation-based (>= 0.8)
- Increase saturation thresholds (2→4 default, 4→6 multi-value) to prevent premature backtracking
- Add ConfirmedCoverageScorer revisit decay (150/(1+revisits)) to prevent overfitting
- Implement `WtgScorer` with multi-hop BFS (depth 3, diminishing boost: +200/+100/+50) using static analysis transition data
- Add `InputValueGenerator` for context-aware text input (email, password, number, generic) replacing hardcoded `"test"`
- Replace uniform random stochastic selection with softmax-weighted selection (temperature=50)
- Enhance stuck detection: time-based (30s), form action exemption, dynamic threshold (max(8, num_elements * 1.5))
- Change `maxRetriesPerCycle` default from 1 to 3

**UI Filtering and Observability:**
- Pre-filter system UI elements from candidate actions
- Add LLM coordinate boundary protection (reject taps on status/nav bars)
- Add per-action score breakdown in RVTRACK trace output for fast debugging and calibration

## Capabilities

### New Capabilities

None — all changes are within the existing rvsmart Java codebase, which is documented in the tools domain spec.

### Modified Capabilities

- `tools`: The rvsmart section of the tools spec gains new invariants and scenarios for UICoverageTracker, PlateauDetector, WtgScorer (multi-hop), InputValueGenerator, and updated scoring parameters. The RVSmartTool Python plugin is NOT modified — changes are in the Java agent only, but the spec documents the agent's behavioral contracts.

## Impact

**Modules affected:**
- `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/` (Java) — primary target, all changes here
- `modules/rvsmart-tool/` (Python) — NOT modified, but its integration tests may need updating if rvsmart output format changes

**FRs/NFRs:**
- FR18 (Tool Registration): rvsmart tool capabilities expand
- FR19 (External Tool Support): enhanced exploration behavior
- NFR01 (Performance): better coverage per unit time through smarter action selection
- NFR03 (Extensibility): new components (UICoverageTracker, PlateauDetector, InputValueGenerator) are pluggable and independently testable

**Cross-module interfaces:**
- No changes to the rvsmart-tool Python plugin interface
- No changes to the RVSMART_METRICS JSON format (new internal components do not produce external output changes)
- Static analysis JSON consumption by StaticMap changes in gh30 (task 0.3); WtgScorer here builds on that fix to also consume the transitions section via `getTransitions()`

**Dependencies:**
- gh30 must be completed first (hash redesign, saturation, scroll, MopScorer, StaticMap transitions, UI capture, OOA recovery, and speed fixes are prerequisites)
