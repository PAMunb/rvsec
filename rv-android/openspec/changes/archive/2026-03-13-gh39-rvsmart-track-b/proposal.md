## Why

GitHub Issue: #39

After Track A calibration (gh37: throttle 50ms, BACK +50, UCB scorer, LLM first-visit), rvsmart still has structural inefficiencies identified in the gh36 analysis: 52.6% of actions are retries on the same screen, 19% of actions target unparseable screens, and BacktrackBfs only navigates backward to ancestors when saturated. These waste iteration budget that could drive new coverage. Track B addresses these algorithmic gaps with four targeted improvements.

## What Changes

- **Retry budget reduction**: Default `max_retries_per_cycle` from 3 to 1; disable retries entirely (0) on screens where `ContentNode.getSaturationRate()` exceeds a configurable threshold. Recovers ~80 iterations per APK.
- **Sterile screen blacklist**: Track consecutive UIAutomator parse failures (null/empty root) per content hash. After a configurable threshold (e.g., 3), mark the hash as "sterile" and exclude it from backtracking targets. Prevents infinite re-exploration of broken screens.
- **Forward navigation on saturation**: When stuck, find the nearest **frontier state** (unsaturated, reachable screen) via BFS on ContentGraph, not just backward to ancestors. Augments BacktrackBfs with forward-capable frontier search; when a frontier exists but backward path is unavailable, RESTART and let UCB+scorers bias toward the frontier.
- **Dual hash: include content-description**: `contentDescription` is already captured in `ScreenItem` but excluded from both hashes. Include truncated contentDescription (≤50 chars) in `ScreenState.computeContentHash()` for better state identity on accessibility-described widgets.

## Capabilities

### New Capabilities

_(none — all changes modify existing rvsmart behavior)_

### Modified Capabilities

- `tools`: Modifies rvsmart exploration behavior — retry budget (INV-RSM relates to action selection), sterile blacklist (new recovery mechanism), forward navigation (augments BacktrackBfs stuck recovery), content hash computation (INV-RSM relates to state identity). Requires delta spec updating affected INV-RSM invariants.

## Impact

- **Modules affected**: None (rvsmart is a Java agent at `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`, not a Python uv module). The Python wrapper `rvsmart-tool` is unaffected — no interface changes.
- **FRs**: FR18 (tool abstraction — rvsmart behavior), FR19 (tool execution — exploration efficiency)
- **NFRs**: NFR07 (performance — throughput via fewer wasted iterations)
- **Cross-module**: No cross-module impact. All changes are internal to the rvsmart Java codebase.
- **Risk**: Forward navigation (item 3) is the most complex change — introduces a new concept (frontier state) and modifies stuck recovery flow. Items 1, 2, 4 are low-risk config/hash changes.
