## Why

rvsmart:mvp achieves only 24.4% mean method coverage vs APE's 27.8% (-3.3pp) across 169 APKs (600s timeout, JCA specs). Root cause: **93.9% of iterations revisit already-known states**. The exploration pipeline loses efficiency at every stage — 52.6% retries, 82.6% no-effect actions, 62.8% transitions to known states. The algorithm saturates individual screens quickly (96.9% reach ≥0.8 saturation) but fails to navigate efficiently to new screens. State discovery plateaus at median 360s, meaning more timeout doesn't help. GitHub Issue: #36.

## What Changes

- **Reduce retry budget**: Lower `max_retries_per_cycle` from 3 to 1 globally, and to 0 on screens with saturation ≥0.8. Recovers ~80 wasted iterations per APK.
- **Forward-first navigation**: When Tier 3 fires (saturation ≥0.8), prioritize navigating to the nearest frontier state (state with untested widgets) via nav_map edges instead of BFS to unsaturated ancestor. Reduces the backward-navigation loop that causes 93.9% revisitation.
- **Faster stuck detection**: Reduce same-hash-for-BACK threshold from 10 to 5 iterations; reduce BACK-failure-for-RESTART threshold from 5 to 3. Saves ~15 wasted iterations per stuck episode.
- **Sterile screen blacklist**: Mark screen hashes that produce only SKIP actions as sterile; never select them as navigation targets. Eliminates repeated visits to unparseable screens (19% of actions are SKIP).
- **Content-aware state hashing**: Include a partial text digest (e.g., hash of first visible text node content, or item count for lists) in the structural hash. Distinguishes scrolled views that are currently collapsed to the same hash, increasing discovered states.
- **Reduce wait-for-idle on known screens**: Profile the iteration loop to identify wait-for-idle as a throughput bottleneck; reduce idle timeout on screens already in the state graph. Target: close the throughput gap from 0.5 to 0.7+ evt/s.

## Capabilities

### New Capabilities

_None — all changes are internal algorithm improvements within the existing rvsmart capability._

### Modified Capabilities

- `rvsmart`: Changes to retry policy (INV-RSM-07 multi-attempt), Tier 3 navigation strategy, stuck detection thresholds, state hashing (INV-RSM-03), and screen blacklisting. No new external interfaces.

## Impact

- **Modules affected**: rvsmart Java source (`$RVSEC_HOME/rvsec-android/rvsmart/`), rvsmart-tool Python wrapper (metrics extraction may need updates for new metrics)
- **Specs affected**: `openspec/specs/rvsmart/spec.md` — invariants INV-RSM-03 (hash), INV-RSM-07 (multi-attempt), INV-RSM-09/10 (stuck detection), Tier 3 BFS behavior
- **No breaking changes**: All changes are internal to rvsmart. External interfaces (trace format, metrics JSON, coverage output) remain compatible. rv-platform, rv-experiment, and rv-coverage are unaffected.
- **PRD references**: FR18 (tool execution), FR19 (tool configuration), NFR02 (performance)
