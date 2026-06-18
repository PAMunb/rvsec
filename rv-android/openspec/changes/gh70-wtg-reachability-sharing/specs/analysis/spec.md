## Purpose

This delta documents a current-state performance property of GATOR's Window Transition Graph (WTG) construction — specifically the per-allocation forward-reachability closure inside `FlowgraphRebuilder.buildFlowThroughContainer()` (FR04). It adds one invariant and one requirement; it changes no existing requirement and alters no produced data. It complements gh66's INV-ANA-39, which optimized the container-field resolution of the same pass but explicitly scoped the per-allocation reachability closure OUT; INV-ANA-45 now covers that closure.

`buildFlowThroughContainer()`, for every allocation node in the reconstructed flow graph (`flowgraph.allNAllocNodes`), computes the set of nodes forward-reachable from that allocation node via `GraphUtil.reachableNodes()` (a BFS over `NNode.getSuccessors()`), then derives the container `reads`/`writes` from the `NVarNode`s in that set and links writer→reader flow edges. After gh66 removed the field-resolution hot spot, this per-allocation reachability recomputation became the dominant cost: it runs a fresh BFS for each of the `N` allocation nodes, and the closures overlap heavily, so the work is `O(N × (V+E))`. Empirically (archived `2026-06-18-gh66-.../REPORT-validation.md` §4) the 96 APKs that fail to emit `transitions[]` on the `experimento-20260604` corpus ALL time out inside WTG construction — they are not genuine zero-transition apps — and Fix 1 alone left the WTG count at 72 (= baseline). Sharing the reachability computation across allocation nodes (e.g. SCC condensation + reachable-set propagation over the condensation DAG) removes this recomputation while returning the identical reachable-node set per allocation node, hence the identical `reads`/`writes` and the identical WTG edge set.

This delta records that current-state structure alongside the existing GATOR-internals invariants (defensive Soot config INV-ANA-16, Flowgraph graceful skip INV-ANA-17, Soot version INV-ANA-18, SPARK CG delegation INV-ANA-21) and gh66's container-flow-linking performance invariant INV-ANA-39.

## Data Contracts

### Input
- `flowgraph.allNAllocNodes: Map<Expr, NAllocNode>` — allocation nodes of the reconstructed flow graph; drives the outer loop of `buildFlowThroughContainer()`.
- The flow graph's successor relation (`NNode.getSuccessors()`) — a cyclic directed graph; the basis of the forward-reachability closure.

### Output
- `transitions[]` section of the `{app_name}.json` analysis file — UNCHANGED by this delta. The container-flow edges derived from the reachability closure feed later WTG stages; the optimization produces an **edge-set-identical** `transitions[]` (same WTG edges keyed on stable identifiers: source/target window name, event type, widget name, handler signature; JSON array ordering and GATOR-assigned numeric node IDs are not part of the contract).

### Side-Effects
- **Build artifact**: `lib/gator/*.jar` (rv-android) is rebuilt from the corrected GATOR source so the shipped JAR matches the source tree (gitignored Maven output; source-vs-JAR consistency maintained by rebuilding).

### Error
- None introduced. The pass remains exception-free; timeout handling is unchanged (write-first partial JSON preserves reachability + windows + components per NFR04).

## Invariants

- **INV-ANA-45**: The per-allocation forward-reachability closure in `FlowgraphRebuilder.buildFlowThroughContainer()` MUST produce, for each allocation node, the **same set of reachable nodes** whether computed independently per allocation node (`GraphUtil.reachableNodes`) or via a shared/precomputed reachability structure. Specifically: (a) for every allocation node `a`, the shared computation MUST return a set equal to `GraphUtil.reachableNodes(a)` — same membership, including the `NOpNode` semantics: an `NOpNode` reachable as a successor MUST be **included** in the set but MUST NOT be **expanded** (its successors are not followed), exactly as `findReachableNodes` does; (b) because the derived `reads`/`writes` sets are a pure function of the `NVarNode`s in the reachable set, identical reachable sets yield identical `reads`/`writes` and therefore an identical container-flow edge set; (c) the public `GraphUtil.reachableNodes`/`findReachableNodes` used by other callers MUST remain behaviorally unchanged (the sharing is a new variant scoped to this pass). The optimization is correct only if the produced `transitions[]` edge set is identical to the per-allocation-recompute pass on the same APK (diff-zero, consistent with INV-ANA-39).

## ADDED Requirements

### Requirement: WTG Per-Allocation Reachability Sharing (FR04, NFR04)

GATOR's WTG construction MUST, in `FlowgraphRebuilder.buildFlowThroughContainer()` (`rvsec-android/rvsec-gator/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java`), determine for each allocation node the set of forward-reachable flow-graph nodes, from which it derives the container `reads`/`writes` and links writer→reader flow edges.

Because this reachability is a pure function of the flow graph's successor relation (static during the pass) and the closures of different allocation nodes overlap, the pass MUST compute reachability via a **shared or precomputed structure** rather than recomputing an independent BFS per allocation node. The shared computation MUST return, for each allocation node, a reachable-node set **identical** to `GraphUtil.reachableNodes()` (INV-ANA-45), including the `NOpNode` include-but-don't-expand behavior. This is a performance optimization that MUST preserve the produced edge set exactly; it MUST NOT prune, depth-limit, approximate, or otherwise alter the WTG algorithm's result. It MUST be implemented without changing the behavior of the public `GraphUtil.reachableNodes`/`findReachableNodes` used by other callers.

The optimization addresses the dominant remaining pre-WTG cost (after gh66's INV-ANA-39 removed the field-resolution hot spot) without changing output, so APKs that previously exceeded the analysis timeout during this pass can complete and emit `transitions[]`. When an APK still times out, the write-first partial-JSON behavior is unchanged: reachability, windows, and components remain populated and `transitions[]` is empty (NFR04).

#### Scenario: Shared reachability produces identical transitions on a passing APK
- **WHEN** GATOR analyzes an APK that already produces `transitions>0` under the per-allocation-recompute pass (one of the 72 baseline APKs from the `experimento-20260604` sweep)
- **THEN** the `transitions[]` section of the produced JSON MUST be identical (diff-zero on the edge set keyed on stable identifiers: source window name, target window name, event type, widget name, handler signature — not on the GATOR-assigned numeric node IDs) to the per-allocation-recompute output
- **AND** the `reachability`, `windows`, and `components` sections MUST be unchanged

#### Scenario: Shared reachable set equals per-allocation reachableNodes (incl. NOpNode)
- **WHEN** `buildFlowThroughContainer()` determines the forward-reachable set for an allocation node whose closure includes one or more `NOpNode`s and traverses one or more cycles in the successor graph
- **THEN** the shared/precomputed set MUST equal `GraphUtil.reachableNodes(allocNode)` exactly — every `NOpNode` reachable as a successor is INCLUDED but NOT expanded, and cycles terminate identically (no node visited twice)
- **AND** the derived `reads`/`writes` `NVarNode` sets MUST be unchanged, so the writer→reader edges added are the same (INV-ANA-45)

#### Scenario: Public reachableNodes behavior is not changed for other callers
- **WHEN** any GATOR code path other than `buildFlowThroughContainer()` calls `GraphUtil.reachableNodes`/`findReachableNodes`
- **THEN** that call MUST return the same result as before this change (the reachability sharing is a new variant scoped to the WTG container-flow pass; the public utility is not altered)

#### Scenario: APK that previously timed out completes WTG construction
- **WHEN** GATOR analyzes an APK that exceeded the analysis timeout inside `buildFlowThroughContainer()`'s per-allocation reachability recomputation (one of the 96 sweep timeouts)
- **THEN** the shared-reachability pass MAY allow the analysis to complete within the same timeout and emit a populated `transitions[]`
- **AND** if it still times out, the partial JSON MUST preserve `reachability`, `windows`, and `components` with `transitions[]` empty, unchanged from the prior timeout behavior (NFR04)
