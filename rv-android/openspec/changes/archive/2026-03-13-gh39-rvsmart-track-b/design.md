## Context

GitHub Issue: #39. Track B of the rvsmart calibration plan (`docs/20260313_rvsmart_refatoracao.md` §6).

After Track A (gh37: throttle 50ms, BACK +50, UCB scorer, LLM first-visit), rvsmart has four structural inefficiencies:
1. **Excessive retries**: `max_retries_per_cycle=3` means up to 3 extra actions per iteration on the same screen. On saturated screens this is pure waste.
2. **No sterile screen handling**: Null/empty UIAutomator roots cause `forceStop + startApp + reset` but the hash is never blacklisted, so the agent re-navigates there.
3. **Backward-only stuck recovery**: `BacktrackBfs` searches ancestors only. When all ancestors are saturated, it falls back to RESTART. It never considers forward reachable states.
4. **Missing content-description in hash**: `ScreenItem.contentDescription` is captured but excluded from `computeContentHash()`, causing accessibility-described widgets to appear identical.

All changes are in the rvsmart Java codebase (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`). No Python modules affected.

## Architecture

All four changes are internal to rvsmart. No new classes are required for items 1, 2, 4. Item 3 adds one new class (`FrontierFinder`).

```
┌─────────────────────────────────────────────────────────┐
│                      AgentLoop                          │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ retry loop  │  │ StuckDetector│  │ UiCapture     │  │
│  │ (item 1)    │  │ (item 2+3)   │  │ (item 2)      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────────┘  │
│         │                │                              │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌───────────────┐  │
│  │ContentGraph │  │BacktrackBfs  │  │FrontierFinder │  │
│  │getSaturation│  │(ancestors)   │  │(NEW, item 3)  │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐                      │
│  │ScreenState  │  │ Config       │                      │
│  │(item 4)     │  │(items 1,2,3) │                      │
│  └─────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Modified/New |
|-----------|---------------|--------------|
| `Config.java` | Defaults for retry, sterile threshold, frontier threshold | Modified |
| `AgentLoop.java:659-691` | Retry loop with saturation check | Modified |
| `StuckDetector.java` | Sterile tracking + frontier-aware recovery | Modified |
| `FrontierFinder.java` | BFS forward through ContentGraph transitions | **New** |
| `BacktrackBfs.java` | Augmented to accept sterile blacklist | Modified |
| `ScreenState.java:140-158` | Include contentDescription in contentSignature | Modified |
| `ContentGraph.java` | Expose sterile blacklist set | Modified |

## Mapping: Spec -> Implementation -> Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Retry budget reduction | `AgentLoop.java` retry loop + `Config.java` | `AgentLoopRetryTest` |
| Saturated screen skip | `AgentLoop.java` checks `graph.getSaturation()` | `AgentLoopRetryTest` |
| Sterile blacklist add | `ContentGraph.markSterile()` + `StuckDetector` | `SterileBlacklistTest` |
| Sterile blacklist skip | `BacktrackBfs` filters sterile hashes | `BacktrackBfsTest` |
| Frontier BFS forward | `FrontierFinder.findFrontier()` | `FrontierFinderTest` |
| StuckDetector frontier | `StuckDetector.recover()` calls FrontierFinder | `StuckDetectorTest` |
| Content-desc in hash | `ScreenState.contentSignature()` | `ScreenStateHashTest` |

## Goals / Non-Goals

**Goals:**
- Reduce wasted iterations by limiting retries and blacklisting sterile screens
- Enable forward navigation to frontier states when all ancestors are saturated
- Improve state identity by including content-description in content hash

**Non-Goals:**
- Component budget allocation (per-Activity time) — too complex
- RewardPropagator — does not exist, high complexity
- PhaseController simplification — works well
- Anti-tarpit beyond period-4 cycles — incremental, future change
- Cross-run persistence — out of thesis scope

## Decisions

### D1: Retry reduction — config + saturation gate

**Choice**: Change default to 1, add saturation gate in the retry loop.

When `graph.getSaturation(currentHash) >= config.getRetrySaturationThreshold()`, skip retries entirely (retries = 0). The threshold is configurable (default 0.8 = 80% of widget actions saturated).

**Alternative considered**: Remove retries entirely. Rejected because retries have value on newly discovered screens where the first action may not have effect due to timing.

### D2: Sterile blacklist — counter in ContentGraph, filter in BacktrackBfs

**Choice**: Add `sterileHashes: Set<String>` to `ContentGraph`. When UIAutomator returns null root, attribute the failure to the **last known content hash** (from the previous successful iteration) — because no ScreenState can be computed without a root, there is no "current hash" available. AgentLoop tracks `lastKnownHash` and passes it to `graph.incrementSterileCounter(lastKnownHash)`. After `config.getSterileThreshold()` consecutive failures (default 3), call `graph.markSterile(hash)`. On successful parse, call `graph.resetSterileCounter(hash)`. BacktrackBfs and FrontierFinder exclude sterile hashes from target candidates. If no last known hash exists (first iteration), sterile tracking is skipped.

**Alternative considered**: Separate SterileBlacklist class. Rejected per P1 (simplicity) — ContentGraph already owns state identity, adding a Set<String> is minimal.

### D3: Forward navigation — FrontierFinder BFS on ContentGraph transitions

**Choice**: New class `FrontierFinder` in `recovery/` package. BFS forward through `ContentNode.getTransitions()` starting from current hash. A node is a "frontier" if `getCoverage() < config.getFrontierCoverageThreshold()` (default 0.8) AND not sterile. Returns the hash of the nearest frontier, or null.

StuckDetector.recover() flow becomes:
1. Try BacktrackBfs (ancestor, backward) — if found, return BACK
2. Try FrontierFinder (forward) — if found, return RESTART (indirect: UCB+scorers bias toward the unsaturated frontier after restart)
3. No frontier found — fall back to RESTART

The key insight: FrontierFinder's value is **diagnostic, not navigational**. It answers "does an unsaturated state exist?" rather than "how do I get there?". When a frontier exists, RESTART is better than staying stuck — the agent re-enters from main activity and UCB naturally gives high scores to unsaturated states. When no frontier exists (all states saturated), RESTART still helps by resetting the stuck detector and trying the main activity again.

**Alternative considered**: Direct forward navigation via NavigationMap replay. Rejected because NavigationMap uses struct hashes while stuck recovery operates on content hashes, and forward navigation requires a sequence of specific actions that don't exist yet. Future change could add this.

**Alternative considered**: Replace BacktrackBfs entirely with FrontierFinder. Rejected because backward navigation (BACK actions) is cheaper and more reliable than RESTART. Backward-first is always preferable when an unsaturated ancestor exists.

### D4: Content-description in hash — append to contentSignature

**Choice**: In `ScreenState.contentSignature()`, append truncated `contentDescription` (≤50 chars) to the signature string for interactive widgets only (same filter as text). Non-interactive widget content-descriptions are excluded to prevent dynamic accessibility labels from creating spurious hashes.

Format: `className|resourceId|text|contentDesc|enabled|checkable`

**Alternative considered**: Include content-description for all widgets. Rejected because output-only TextViews often have dynamic content-descriptions (e.g., "Result: 42") that change every interaction.

## API Design

### `FrontierFinder.findFrontier(startHash, graph, coverageThreshold, sterileHashes) -> String`

- **Precondition**: startHash is a valid content hash in graph
- **Postcondition**: Returns hash of nearest frontier node (coverage < threshold, not sterile), or null
- **Algorithm**: BFS forward through ContentNode.getTransitions(), skipping visited and sterile nodes
- **Complexity**: O(V + E) where V = content nodes, E = transitions

### `ContentGraph.markSterile(hash)` / `ContentGraph.isSterile(hash)` / `ContentGraph.getSterileHashes()`

- **Side-effect**: Adds hash to internal sterileHashes set
- **Invariant**: Sterile hashes are never removed (once sterile, always sterile within a run)

### `StuckDetector.recover()` updated flow

```
1. BacktrackBfs.findPathToUnsaturated(hash, tracker, graph, threshold, sterileHashes)
   → if found: return Action.back("algorithm")
2. FrontierFinder.findFrontier(hash, graph, coverageThreshold, sterileHashes)
   → if found: return Action.restart("algorithm")  // UCB bias guides toward frontier
3. return handleNoBacktrackPath(hash)  // existing RESTART logic
```

FrontierFinder's role is diagnostic: it determines whether unsaturated states exist. When they do, RESTART is preferred over staying stuck because UCB+scorers naturally bias the agent toward unsaturated states after restart. This avoids the need for explicit forward navigation (which would require struct→content hash translation and action replay).

### Config additions

| Parameter | Key | Default | Description |
|-----------|-----|---------|-------------|
| `retrySaturationThreshold` | `retry_saturation_threshold` | 0.8f | Skip retries when screen saturation >= this |
| `sterileThreshold` | `sterile_threshold` | 3 | Consecutive null-root failures to mark sterile |
| `frontierCoverageThreshold` | `frontier_coverage_threshold` | 0.8f | Coverage below this = frontier candidate |

## Data Flow

```
Iteration N:
  0. Track lastKnownHash (updated at end of every successful iteration)

  1. Capture screen → null root?
     YES → if lastKnownHash != null:
              graph.incrementSterileCounter(lastKnownHash)
              if counter >= threshold → graph.markSterile(lastKnownHash)
            handleNullRoot() (existing: forceStop + startApp or wait)
     NO  → graph.resetSterileCounter(hash)
            normal flow

  2. Select action → execute → check effect
     NO effect → retry loop:
       if graph.getSaturation(hash) >= retrySaturationThreshold → skip retries
       else → try up to maxRetriesPerCycle alternatives

  3. Stuck detected (consecutiveUnchanged >= stuckMaxBlocks)?
     YES → StuckDetector.recover():
       a. BacktrackBfs.findPathToUnsaturated(hash, tracker, graph, threshold)
          → filter out sterile hashes
          → if found: BACK
       b. FrontierFinder.findFrontier(hash, graph, coverageThreshold, sterileHashes)
          → if found: RESTART (UCB bias guides toward frontier)
       c. no frontier: RESTART

  4. End of iteration → lastKnownHash = hash
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Null root from UIAutomator | UiCapture/getRootInActiveWindow | Increment sterile counter for lastKnownHash | handleNullRoot (existing) |
| FrontierFinder returns null | No reachable frontier | Fall through to RESTART | Existing RESTART logic |
| No lastKnownHash on null root | First iteration null root | Skip sterile tracking | handleNullRoot (existing) |

## Risks / Trade-offs

- **[Risk] Sterile threshold too low** → Transient failures (slow app startup) might blacklist valid screens. **Mitigation**: Default threshold 3 (not 1); counter resets on successful parse at same hash.
- **[Risk] Frontier BFS on large graphs** → O(V+E) could be slow with thousands of states. **Mitigation**: In practice, rvsmart discovers 50-200 content states per 600s run; BFS is negligible.
- **[Risk] Content-description changes hash space** → More distinct states = slower coverage convergence. **Mitigation**: Only included for interactive widgets; truncated to 50 chars.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | FrontierFinder BFS | Mock ContentGraph with known topology | ~6 tests |
| Unit | Sterile blacklist | ContentGraph.markSterile/isSterile | ~4 tests |
| Unit | Retry saturation gate | AgentLoop retry logic | ~4 tests |
| Unit | Content-desc in hash | ScreenState.computeContentHash | ~3 tests |
| Unit | BacktrackBfs sterile filter | BFS with sterile exclusion | ~3 tests |
| Integration | StuckDetector full flow | BacktrackBfs + FrontierFinder | ~3 tests |
| **Total** | | | **~23 tests** |

## Open Questions

_(none — all design decisions resolved)_
