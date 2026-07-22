# Proposal: gh40-rvsmart-track-b2

GitHub Issue: #40

## Problem

After gh37 (Track A: calibration + UCB) and gh39 (Track B first batch: retry gate, sterile blacklist, frontier finder, content-description hash), three items from the Track B plan remain unimplemented:

1. **Component Budget Allocation**: The agent spends equal time on all Activities regardless of widget density. A Settings screen with 30 widgets gets the same budget as a splash screen with 3. This under-explores complex screens.

2. **Anti-Tarpit Detection**: CycleDetector catches period 2-4 ping-pong patterns, but not longer repetitive patterns — e.g., 50 iterations scrolling an infinite list or a dialog that reappears after dismissal. These "tarpits" waste iterations without coverage gain.

3. **PhaseController Simplification**: PhaseController manages 3 phases with explicit transitions (Phase 1→2→3). Phase 2 (coverage-guided navigation) overlaps with what UCBScorer + CoverageDensityScorer already provide. Merging Phase 2 into Phase 1 with coverage-gap as a scorer tiebreaker simplifies the architecture and reduces tunable parameters.

## Scope

All changes are in the rvsmart Java agent (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`). No Python module changes.

### In Scope
- Per-Activity iteration budget based on interactive widget count
- Tarpit detection: N iterations without new state/MOP → force escape + blacklist pattern
- Merge Phase 2 into Phase 1; Phase 3 remains (stochastic escape)
- Config parameters for budget and tarpit thresholds
- Unit tests for all new/modified classes

### Out of Scope
- Cross-run persistence (Fastbot2-style)
- LLM routing changes
- Scroll-position-aware hashing
- Python rv-agent changes

## Expected Impact

| Metric | Current (post-gh39) | Target |
|--------|---------------------|--------|
| Activity coverage | ~65% | +5-9pp from component budget |
| Wasted iterations | ~15% (tarpits) | <5% from tarpit detection |
| Tunable parameters | Phase 1/2/3 thresholds | Phase 1/3 only (fewer params) |

## Approach

- **Item 4 (Component Budget)**: Add `ActivityBudgetTracker` that assigns iteration budgets proportional to `totalActions` count per Activity. When budget exhausts, force backtrack/restart to another Activity.
- **Item 5 (Anti-Tarpit)**: Extend `PlateauDetector` or create `TarpitDetector` that detects N consecutive iterations without new state AND without coverage gain on a specific screen hash. On detection, blacklist the hash temporarily and force RESTART.
- **Item 8 (PhaseController Simplification)**: Remove Phase 2 from `PhaseController` (keep Phase 1 and Phase 3 only). Phase 2's coverage-guided behavior is already provided by `CoverageDensityScorer` + `UCBScorer`. `PhaseController.onIteration()` transitions directly from Phase 1 to Phase 3 when plateau is detected.
