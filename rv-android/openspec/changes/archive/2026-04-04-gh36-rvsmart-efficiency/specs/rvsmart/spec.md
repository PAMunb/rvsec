# Delta Spec: rvsmart — Exploration Efficiency (gh36)

Changes to `openspec/specs/rvsmart/spec.md`. All modifications are additive or replace specific invariant definitions.

## Modified Invariants

### INV-RSM-07 (Multi-Attempt Retries) — REPLACE

**Current**: Multi-attempt retries within a cycle MUST NOT exceed `MAX_RETRIES_PER_CYCLE`. Actions with ≥3 consecutive failures on the same screen MUST be skipped by `selectNextBest()`.

**New**: Multi-attempt retries within a cycle SHALL use an **adaptive budget** based on screen saturation:
- When screen saturation < 0.8: `MAX_RETRIES_PER_CYCLE = 1`
- When screen saturation ≥ 0.8: `MAX_RETRIES_PER_CYCLE = 0` (no retries on saturated screens)

Actions with ≥3 consecutive failures on the same screen MUST still be skipped by `selectNextBest()`.

**WHEN** the agent executes an action on a saturated screen (saturation ≥ 0.8)
**AND** the action has no effect (hash unchanged, same activity, same focused resource)
**THEN** the agent SHALL proceed directly to the learn phase without retrying.

**WHEN** the agent executes an action on a fresh screen (saturation < 0.8)
**AND** the action has no effect
**THEN** the agent MAY retry once with the next best action from `selectNextBest()`.

### INV-RSM-03 (Structural Hash) — EXTEND

**Current**: SHA-256[:12] computed from canonical JSON of 9 widget properties sorted by (resource_id, class).

**New**: The structural hash SHALL additionally include a **content digest** suffix:
- Count of nodes with non-empty `text` or `contentDescription` (integer)
- SHA-256[:4] of the first non-empty text value encountered in BFS order

Final hash format: `{structural_12hex}_{text_count}_{text_sample_4hex}`

Example: `a1b2c3d4e5f6_42_7f8e` (12-char structural + text count + 4-char text sample)

**WHEN** two screens have identical widget structure (same classes, resource IDs, interactive properties)
**BUT** different visible text content (e.g., scrolled list with different items)
**THEN** the hash SHALL differ, resulting in distinct states in the `DynamicStateGraph`.

**WHEN** a screen has no text-bearing nodes
**THEN** the content digest suffix SHALL be `0_0000`.

### INV-RSM-09 (Stuck Detection) — REPLACE (repurposed, was LLM circuit breaker)

**Note**: INV-RSM-09 in the current spec describes `LlmCircuitBreaker`. The stuck detection thresholds are described in the behavioral spec (section "Stuck Detection and Recovery"). This delta adds a new invariant for stuck detection.

### INV-RSM-14 (Stuck Detection Thresholds) — NEW

The `StuckDetector` SHALL use the following thresholds:
- **Force BACK**: After **5** consecutive iterations with the same screen hash (was 10)
- **Force RESTART**: After **3** consecutive BACK actions that fail to change state (was 5)

**WHEN** the agent has been on the same screen hash for 5 consecutive iterations
**THEN** the agent SHALL force a BACK action regardless of Tier selection.

**WHEN** the agent has executed 3 consecutive BACK actions without state change
**THEN** the agent SHALL force a RESTART action.

### INV-RSM-15 (Sterile Screen Blacklist) — NEW

The `DynamicStateGraph` SHALL maintain a **sterile screen set**: hashes of screens where all visits produced only SKIP actions (no actionable widgets found by the parser).

**WHEN** a screen hash has been visited at least 2 times
**AND** every visit produced only SKIP actions
**THEN** the hash SHALL be added to the sterile set.

**WHEN** the `ActionSelector` computes Tier 3 BFS navigation targets
**THEN** sterile hashes SHALL be excluded from the candidate set.

**WHEN** a RESTART occurs
**THEN** the sterile set SHALL be cleared (transient loading may have resolved).

### INV-RSM-16 (Frontier Navigation) — NEW

When `ActionSelector` enters Tier 3 (saturation ≥ 0.8 on current screen), it SHALL first attempt **frontier navigation** before falling back to BFS-to-ancestor:

1. Query `DynamicStateGraph` for all states with saturation < 0.8 (frontier states), excluding sterile hashes
2. Compute shortest path from current state to nearest frontier state using nav_map edges
3. If path exists and length ≤ 5 hops: buffer the path actions into `PathBuffer` and execute
4. If no path exists or path > 5 hops: fall back to existing BFS-to-ancestor behavior

**WHEN** the current screen is saturated (≥ 0.8)
**AND** a frontier state exists within 5 nav_map hops
**THEN** the agent SHALL navigate to that frontier state via the shortest path.

**WHEN** no frontier state is reachable within 5 hops
**THEN** the agent SHALL fall back to existing BFS-to-ancestor behavior (Tier 3 current).

## Modified Behavior

### Adaptive Throttle on Known Screens

**WHEN** the current screen hash already exists in the `DynamicStateGraph` (revisit)
**THEN** `throttle_ms` MAY be reduced to 50% of the configured value.

**WHEN** the current screen hash is new (first visit)
**THEN** `throttle_ms` SHALL remain at the configured value.

This reduces wait-for-idle overhead on screens where the UI tree is already known and stable.

## New Metrics

The `MetricsCollector` SHALL report the following additional fields in the final metrics JSON:

```json
{
  "efficiency": {
    "retry_waste_pct": <float>,       // retries / total_actions × 100
    "revisitation_pct": <float>,      // revisited_states / total_iterations × 100
    "transition_rate_pct": <float>,   // state_transitions / total_iterations × 100
    "sterile_screens": <int>,         // count of sterile hashes
    "frontier_navigations": <int>,    // count of successful frontier nav attempts
    "frontier_fallbacks": <int>       // count of fallbacks to BFS-to-ancestor
  }
}
```

These metrics enable tracking whether the efficiency improvements are effective across experiments.
