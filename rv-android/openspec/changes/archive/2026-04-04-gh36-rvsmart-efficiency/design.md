## Context

rvsmart:mvp explores 169 APKs with 24.4% mean method coverage vs APE's 27.8% (experiment `exp-rvsmart-ape`, 600s timeout, JCA specs). The root cause is a cascade of inefficiencies: 52.6% retry waste, 17.4% state-transition rate, 93.9% revisitation rate. State discovery plateaus at median 360s. See proposal.md and GitHub Issue #36.

The changes target the Java source in `$RVSEC_HOME/rvsec-android/rvsmart/` — the core `AgentLoop`, `ActionSelector`, `StuckDetector`, `BacktrackBfs`, `DynamicStateGraph`, `UiCapture`, and `Learner` components. No Python-side changes except optional metrics extraction updates in `modules/rvsmart-tool/`.

Relevant invariants: INV-RSM-03 (hash), INV-RSM-07 (multi-attempt), INV-RSM-11 (BFS cap), INV-RSM-12 (unified Tier 4 queue). PRD: FR18, FR19, NFR02.

## Architecture

All changes are internal to the `rvsmart.jar` Java agent. No cross-module interactions change.

```
rvsmart.jar (modified components)
├── core/AgentLoop          — adaptive retry budget (change 1)
├── strategy/ActionSelector — frontier navigation in Tier 3 (change 2)
├── recovery/StuckDetector  — lower thresholds (change 3)
├── graph/DynamicStateGraph — sterile screen tracking (change 4)
├── device/UiCapture        — content-aware hash option (change 5)
└── core/AgentLoop          — adaptive wait-for-idle (change 6)
```

### Key Components

| Component | Change | Current | Proposed |
|-----------|--------|---------|----------|
| `AgentLoop.executeIteration()` | Retry budget | `MAX_RETRIES_PER_CYCLE=3` always | 1 globally, 0 when saturation ≥0.8 |
| `ActionSelector.selectTier3()` | Navigation | BFS to unsaturated ancestor | Navigate to nearest frontier state via nav_map |
| `StuckDetector` | Thresholds | 10 same-hash → BACK; 5 BACK-fail → RESTART | 5 same-hash → BACK; 3 BACK-fail → RESTART |
| `DynamicStateGraph` | Blacklist | None | Track sterile hashes, exclude from nav targets |
| `UiCapture.computeHash()` | Hash | Structural only (9 widget props) | Structural + partial text digest |
| `AgentLoop.throttle()` | Wait | Fixed `throttle_ms` | Reduced on known screens |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-RSM-07 (multi-attempt) | `AgentLoop.executeIteration()` — adaptive retry limit | `test_retry_budget_saturated`, `test_retry_budget_normal` |
| INV-RSM-12 (Tier 4 queue) | `ActionSelector.selectTier3()` — frontier nav | `test_tier3_frontier_navigation` |
| INV-RSM-09 (stuck detection) | `StuckDetector` — lowered thresholds | `test_stuck_detection_thresholds` |
| New: sterile blacklist | `DynamicStateGraph.markSterile()` | `test_sterile_screen_exclusion` |
| INV-RSM-03 (structural hash) | `UiCapture.computeHash()` — text digest | `test_content_aware_hash` |
| NFR02 (performance) | `AgentLoop.throttle()` — adaptive idle | `test_adaptive_throttle` |

## Goals / Non-Goals

**Goals:**
- Reduce revisitation rate from 93.9% to <80%
- Increase state discovery rate from 5.4% to >10% per iteration
- Close the method coverage gap with APE (target: ≥27% mean)
- Maintain trace format and metrics JSON compatibility

**Non-Goals:**
- LLM integration changes (separate concern, multimode unaffected)
- Scorer weight tuning (separate calibration concern)
- Python wrapper changes beyond metrics extraction
- Throughput optimization via JVM tuning or threading

## Decisions

### D1: Adaptive retry budget (not fixed reduction)

**Choice**: Retry limit depends on screen saturation — 1 retry on fresh screens (<0.8 saturation), 0 on saturated screens.

**Alternative considered**: Fixed reduction to 1 everywhere. Rejected because fresh screens genuinely benefit from retries (widget may not respond on first attempt due to animation).

**Rationale**: The data shows retries are wasteful specifically on saturated screens where all widgets have been tried. On fresh screens, a retry can still discover new behavior.

### D2: Frontier navigation via nav_map (not random walk)

**Choice**: When Tier 3 fires, query `DynamicStateGraph` for the nearest state with untested widgets (frontier), then follow nav_map edges to reach it.

**Alternative considered**: Random BACK+RESTART. Rejected — this is what Phase 3 stochastic already does and it's only 22.3% of decisions.

**Rationale**: The nav_map already tracks edges between states. Using it to find and route to frontier states avoids the backward-only BFS pattern that causes revisitation loops.

### D3: Content-aware hash via text count (not full text hash)

**Choice**: Append the count of text-bearing nodes and the hash of the first visible text node's content to the structural hash. This is lightweight and avoids hash explosion.

**Alternative considered**: Full text content hash of all nodes. Rejected — would create too many unique states for dynamic content (timestamps, counters), overwhelming the graph and reducing saturation effectiveness.

**Rationale**: The primary missed case is scrolled lists where items change but structure is identical. Counting text nodes and sampling the first text node distinguishes these cases without exploding the state space.

### D4: Sterile blacklist at graph level (not parser level)

**Choice**: `DynamicStateGraph` tracks hashes that produced only SKIP actions across all visits. These are excluded from Tier 3 navigation targets.

**Alternative considered**: Parser-level detection (don't emit SKIP, just skip). Rejected — the parser correctly reports no actionable widgets; the issue is that the navigator returns to these screens.

**Rationale**: The problem isn't detecting sterile screens (that works), it's revisiting them. The fix belongs in navigation, not parsing.

### D5: Implement changes incrementally (not all at once)

**Choice**: Implement in priority order (retry → navigation → stuck → sterile → hash → throttle), with experiment validation after each batch.

**Rationale**: Each change can be validated independently. If retry reduction alone closes most of the gap, later changes may be unnecessary. P1 simplicity — minimum changes for maximum impact.

## Data Flow

No change to external data flow. Internal iteration loop changes:

```
Current:  capture → graph → route → select → execute → retry(×3) → learn → throttle(fixed)
Proposed: capture → graph → route → select → execute → retry(×0-1) → learn → throttle(adaptive)
                      ↓
              sterile check → skip if sterile
                      ↓
              frontier nav → route to nearest untested state (Tier 3)
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|---------|
| No frontier states | All reachable states saturated | Fall back to current BFS-to-ancestor | Existing behavior preserved |
| Nav_map path broken | Intermediate state unreachable | Abandon path, RESTART | Existing RESTART recovery |
| Content hash collision | Different content, same hash | No action needed | Structural hash still prevents UI confusion |
| Empty graph on sterile check | All screens sterile | RESTART with sterile list cleared | Reset exploration |

## Risks / Trade-offs

- **[Lower retry may miss delayed UI effects]** → Mitigated by keeping 1 retry on fresh screens. Only saturated screens get 0.
- **[Content hash increases state count]** → Controlled by using text count + first-node sample, not full content. Expected: +20-30% states, not explosion.
- **[Frontier navigation path length]** → Path through nav_map may be long. Cap at 5 hops; if longer, fall back to RESTART.
- **[Sterile screens that become active]** → Rare but possible (e.g., async loading). Mitigated by clearing sterile list on RESTART.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | Retry budget logic | Mock saturation values | ~4 tests |
| Unit | Frontier finding in graph | Synthetic graph with known frontier | ~4 tests |
| Unit | Stuck detection thresholds | Sequence of same-hash iterations | ~3 tests |
| Unit | Sterile screen tracking | Mark + query sterile hashes | ~3 tests |
| Unit | Content-aware hash | Same structure, different text → different hash | ~3 tests |
| Integration | Full loop with adaptive retry | Run 100 iterations on test APK | ~2 tests |
| Experiment | Coverage comparison | Same 169 APKs, 600s, 3 reps | 1 experiment |

## Open Questions

1. **Frontier nav path planning**: Should we precompute shortest paths in the nav_map or compute on-demand? On-demand is simpler (P1) but may add latency per Tier 3 decision.
2. **Content hash backward compatibility**: New hash will produce different state IDs than old hash. Should we maintain parallel hashes for transition period? Leaning toward no (P3 — no backward compatibility).
3. **Sterile threshold**: How many consecutive SKIP-only visits before marking sterile? Propose 2 visits minimum to avoid false positives from transient loading states.
