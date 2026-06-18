## Context

Follow-up to #66. gh66 (Fix 1) optimized container-field resolution in `FlowgraphRebuilder.buildFlowThroughContainer()` and proved it semantics-preserving (diff-zero on 72 APKs). The archived gh66 `REPORT-validation.md` (§4) then measured that WTG construction is still timeout-bound: 96/169 APKs emit `transitions==0` because they **time out** inside this pass (not because they have no transitions), so the WTG count stayed at 72 (= baseline), net recovery ≈ +1.

The remaining dominant cost is the per-allocation forward-reachability closure. In `buildFlowThroughContainer()`:

```
for (Expr e : flowgraph.allNAllocNodes.keySet()) {        // N allocation nodes
    Set<NNode> reached = graphUtil.reachableNodes(allocNode);   // <-- Fix 2 target (~line 327)
    // derive reads/writes from NVarNodes in `reached`
    // (gh66 Fix 1) resolve container fields (hoisted + memoized)
    // add writer -> reader edges
}
```

`GraphUtil.reachableNodes(n)` runs a fresh BFS over `NNode.getSuccessors()` from `n`, with a visited set (the graph is cyclic), and a subtlety: an `NOpNode` successor is **added** to the result set but **not expanded** (`if (!(s instanceof NOpNode)) worklist.add(s); reachableNodes.add(s);`). Running this independently for each of `N` allocation nodes, over closures that overlap heavily, is `O(N × (V+E))`. FR04 (GATOR WTG); NFR04 (write-first timeout degradation). Relevant invariants: gh66 INV-ANA-39 (this delta adds INV-ANA-45 for the reachability closure it scoped out).

## Architecture

The change is internal to one GATOR method plus a new private helper; no module boundary moves. rv-static-analysis consumes the rebuilt JAR unchanged.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `FlowgraphRebuilder.buildFlowThroughContainer()` | Link container data-flow before WTG stages | `flowgraph.allNAllocNodes`, successor graph | flow edges → `transitions[]` |
| `GraphUtil.reachableNodes(NNode)` (unchanged, public) | Per-node forward closure (BFS) used by other callers | `NNode` | `Set<NNode>` |
| **NEW** shared-reachability helper (private, scoped to the pass) | Compute reachable sets for all allocation nodes once via SCC condensation + DAG propagation | successor graph + allocation nodes | per-node `Set<NNode>` identical to `reachableNodes` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| FR04: WTG reachability sharing | new private helper in `FlowgraphRebuilder` replacing the per-alloc `reachableNodes` call | `FlowgraphReachabilityShareTest` (set-equality on fixture graph) |
| INV-ANA-45 (a) same set incl. NOpNode | helper returns `== reachableNodes(a)` per node; NOpNode include-but-don't-expand replicated | unit: cyclic + NOpNode fixture asserts set-equality vs `reachableNodes` |
| INV-ANA-45 (b) identical reads/writes → edges | unchanged derivation from `NVarNode`s | corpus diff-zero (`wtg_sweep_invariance.py`) |
| INV-ANA-45 (c) public utility unchanged | `GraphUtil.reachableNodes` untouched; sharing is a new variant | grep/diff: no edit to `GraphUtil.reachableNodes`/`findReachableNodes` |

## Goals / Non-Goals

**Goals:**
- Remove the `O(N × (V+E))` per-allocation reachability recomputation, computing shared reachability once.
- Preserve the WTG `transitions[]` edge set exactly (diff-zero, INV-ANA-45 / consistent with INV-ANA-39).
- Recover WTG completion on APKs that previously timed out (raise `tr>0` above 72); measure the recovery.

**Non-Goals:**
- Changing the public `GraphUtil.reachableNodes`/`findReachableNodes` (other callers untouched).
- Any pruning/depth-limiting/approximation of the WTG result (forbidden).
- The `TargetResolver`/extractor reachability path (#69 — disjoint files).
- gh66's field-resolution hoist/memoize (already landed).

## Decisions

**D1 — SCC condensation + reachable-set propagation over the condensation DAG.** All nodes in one strongly-connected component share an identical forward-reachable set; condense SCCs (Tarjan/Kosaraju), then compute each SCC's reachable set as the union of itself and its successor SCCs' sets over the (acyclic) condensation, in reverse-topological order. Each allocation node's set is its SCC's set. This computes the closure once instead of `N` times. *Alternative — full `V×V` transitive-closure bitset: rejected* (up to `O(V²)` memory; risks trading timeout for OOM on the large graphs that are exactly the problem cases). *Alternative — naive per-node memoization keyed by start node: rejected* (allocation nodes are distinct start nodes queried once each → no reuse; the reuse must be at the SCC/successor level, not the query level).

**D2 — New private helper scoped to `buildFlowThroughContainer`; do NOT modify `GraphUtil.reachableNodes`.** The public utility has other callers whose behavior must not change (P3, INV-ANA-45c). The shared computation lives in `FlowgraphRebuilder` (or a package-private helper it owns) and is used only by this pass.

**D3 — Replicate the `NOpNode` include-but-don't-expand rule exactly.** In the condensation, an `NOpNode` must appear in a reachable set when it is a successor, but its own successors must not propagate through it. Concretely: treat `NOpNode`s as **sink-like** for propagation (they contribute themselves to predecessors' sets but do not forward their successors), matching `findReachableNodes`. This is the single most error-prone point for diff-zero and gets a dedicated unit-test scenario.

**D4 — Layered validation, diff-zero is the gate (mirrors gh66).** (a) A JUnit unit test builds a small flow-graph fixture with a cycle and an `NOpNode` and asserts the shared helper returns sets equal to `GraphUtil.reachableNodes` for every node. (b) The edge-set IT (`BaselineComparisonIT` cryptoapp) must stay diff-zero. (c) The full-corpus gate `scripts/wtg_sweep_invariance.py` (baseline × gh70) must report invariants identical + transitions diff-zero on every baseline-`tr>0` APK before any recovery is claimed. Recovery (§4.2-style) is measured only after diff-zero passes.

## API Design

### `private Map<NNode, Set<NNode>> computeSharedForwardReachability(Collection<NNode> allocNodes)`

- **Precondition**: the flow graph successor relation is fully built and static for the duration of the pass.
- **Postcondition**: for every `a` in `allocNodes`, `result.get(a)` equals `GraphUtil.reachableNodes(a)` (set membership, including `NOpNode` include-but-don't-expand). No flow-graph nodes are created or mutated (read-only over the successor relation).
- **Error**: none; pure computation. (Allocation that fails to map is handled identically to the current code — the existing `instanceof RefType` / null guards are unchanged.)

Call-site change: replace `graphUtil.reachableNodes(flowgraph.allNAllocNodes.get(e))` with a lookup into the precomputed map (computed once before the outer loop).

## Data Flow

successor graph → **SCC condensation** (once) → reverse-topological **reachable-set DP** per SCC (once) → per-allocation-node reachable set (lookup) → `reads`/`writes` from `NVarNode`s (unchanged) → container-field resolution (gh66, unchanged) → writer→reader flow edges (unchanged) → WTG stages → `transitions[]`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Timeout still exceeded | very large graph even after sharing | unchanged write-first degradation | partial JSON keeps reachability+windows+components, `transitions[]` empty (NFR04) |
| (no new error classes) | — | the pass remains exception-free | — |

## Risks / Trade-offs

- **[`NOpNode` semantics diverge in the condensation]** → dedicated unit-test scenario asserting set-equality vs `reachableNodes` on an `NOpNode`+cycle fixture; corpus diff-zero gate as backstop.
- **[SCC condensation memory on huge graphs]** → bounded by node/edge count, not `V²` (D1 rejects full closure); if a pathological APK still OOMs, it falls back to the unchanged write-first timeout path (no regression vs today).
- **[Recovery is marginal]** → possible: if a third bottleneck dominates (WTG stages 1..5 themselves), recovery stays low. The diff-zero gate still makes the change a safe, correct optimization; the recovery number is measured and reported (informs whether further WTG-stage work is warranted), not assumed.
- **[Stale JAR / source-vs-JAR drift]** → rebuild discipline (gh66 / `e584894a`); confirm new symbol present in shipped JAR via `javap`.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | shared helper returns sets `== reachableNodes` (cycle + NOpNode + diamond fixtures); public `reachableNodes` untouched | JUnit in `sootandroid` (in-process fixture graph) | ~3-4 |
| Integration | cryptoapp `transitions[]` edge set diff-zero | `BaselineComparisonIT` (RVSEC_HOME-gated) | reuse existing |
| Empirical | full-corpus invariance + diff-zero on the 72; recovery count on the 96 timeouts | `scripts/wtg_sweep_invariance.py` + sweep | corpus |

## Open Questions

- SCC algorithm: Tarjan (single pass, recursion/explicit stack) vs Kosaraju (two DFS). Decide at implementation; both yield identical condensations — pick the one that keeps the `NOpNode` rule cleanest. Not a blocker.
- Whether the recovery justifies follow-up work on the WTG stages themselves (`WTGBuilder.build` 1..5) — decide post-measurement, as gh66 did for this change.
