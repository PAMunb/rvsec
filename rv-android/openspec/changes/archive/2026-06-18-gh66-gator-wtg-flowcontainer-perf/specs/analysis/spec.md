## Purpose

This delta documents a current-state performance property of GATOR's Window Transition Graph (WTG) construction, the analysis domain capability that produces the `transitions[]` section of the static-analysis JSON (FR04). It adds one invariant and one requirement; it changes no existing requirement and alters no produced data.

GATOR builds the WTG in two stages. First, in `FlowgraphRebuilder.preBuild()`, it reconstructs an inter-procedural flow graph and links data flow through container reads and writes (`buildFlowThroughContainer()`). Only then do the WTG stages proper run (`WTGBuilder.build()` stages 1..5). The container-flow linking pass is invisible in the logs (it emits no per-iteration output) and runs single-threaded on the `main` thread, so when it dominates runtime the analysis appears to hang silently after "Reachability JSON written". Empirically, this pass is the dominant pre-WTG cost: a `jstack` probe on a 2 MB app (`ch.famoser.mensa`) found the `main` thread RUNNABLE on-CPU inside `buildFlowThroughContainer()` across every sampled dump, and in the `experimento-20260604` WTG sweep 97/169 APKs failed to produce `transitions[]` purely because this pass (and the later WTG stages it precedes) exceeded the timeout — doubling the timeout from 1800s to 3600s rescued ~1 in 65, the signature of a super-linear cost rather than a time shortfall.

The pass is structured as, for every allocation node in the flow graph, a forward-reachability closure followed by a nested loop over `(write statement × read statement)` pairs. Two redundancies inflate its constant factor without affecting its output: the read-side container-field resolution (`WTGUtil.getReadContainerField`, which resolves a Soot method reference and walks the container-method hierarchy) is recomputed for every `(write × read)` pair although it depends only on the read statement; and the same container statements recur across allocation nodes, so their field-position resolution is recomputed once per allocation node. Because `getReadContainerField` and `getWriteContainerField` are pure functions of the statement, hoisting the read resolution out of the write loop and memoizing both across allocation nodes produces the identical set of flow edges. This delta records that current-state structure so the spec explains why the pass is written this way, alongside the existing GATOR-internals invariants (defensive Soot config INV-ANA-16, Flowgraph graceful skip INV-ANA-17, Soot version INV-ANA-18, SPARK CG delegation INV-ANA-21).

## Data Contracts

### Input
- `flowgraph.allNAllocNodes: Map<Expr, NAllocNode>` — allocation nodes of the reconstructed flow graph (internal to GATOR's `FlowgraphRebuilder`); drives the outer loop of `buildFlowThroughContainer()`.

### Output
- `transitions[]` section of the `{app_name}.json` analysis file — UNCHANGED by this delta. The container-flow edges feed later WTG stages; the optimization produces an **edge-set-identical** `transitions[]` — the same set of WTG edges keyed on stable identifiers (source/target window name, event type, widget name, handler signature); the JSON array ordering and the GATOR-assigned numeric node IDs are not part of the contract (destination: rv-agent navigation, aperv `scoreWtg`).

### Side-Effects
- **Build artifact**: `lib/gator/*.jar` (rv-android) is rebuilt from the corrected GATOR source so the shipped JAR matches the GATOR source tree (the JAR is a gitignored Maven build output; source-vs-JAR consistency must be maintained by rebuilding).

### Error
- None introduced. The pass remains exception-free; timeout handling is unchanged (write-first partial JSON preserves reachability + windows + components per NFR04).

## Invariants

- **INV-ANA-39**: `FlowgraphRebuilder.buildFlowThroughContainer()` MUST produce the same set of container-flow edges whether or not container-field resolution is hoisted and memoized. Specifically: (a) `WTGUtil.getReadContainerField(stmt)` and `WTGUtil.getWriteContainerField(stmt)` MUST be treated as pure functions of `stmt` — for a given statement they return the same field position on every call within a run; (b) hoisting the read-side resolution and target-node computation out of the `for (Stmt src : writes)` loop, and memoizing field-position resolution across the `for (Expr e : allNAllocNodes)` loop, MUST NOT add, drop, or redirect any edge; (c) the target-node factories (`simpleNode`/`varNode`) have lazy node-creation side effects, so the hoisted computation MUST be guarded — read-target nodes are materialized only for allocation nodes that add at least one edge, never for an allocation node whose writes all fail to resolve, so the set of flow-graph nodes created by the pass is also unchanged. The optimization is correct only if the produced `transitions[]` edge set is identical to the unoptimized pass on the same APK (keyed on stable identifiers; see Data Contracts — Output).

## ADDED Requirements

### Requirement: WTG Container-Flow Linking Pass Performance (FR04, NFR04)

GATOR's WTG construction MUST link data flow through container reads and writes in `FlowgraphRebuilder.buildFlowThroughContainer()` (`rvsec-android/rvsec-gator/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java`) before the WTG stages run. This pass resolves, for each container read/write statement, its container-field position via `WTGUtil.getReadContainerField` / `getWriteContainerField` (`WTGUtil.java`), and adds a flow edge from each writer node to each reader node reachable through the same container.

Because `getReadContainerField` and `getWriteContainerField` are pure functions of the statement, the pass MUST resolve each read statement's field position and target node at most once per allocation node (resolution hoisted out of the inner write loop) and MUST memoize field-position resolution across allocation nodes (`Map<Stmt,Integer>` surviving the outer loop). The target-node computation MUST be guarded so it runs only for allocation nodes that add at least one edge — i.e. only after a write statement resolves to a non-null writer node — because the node-resolution factories (`simpleNode`/`varNode`) lazily create flow-graph nodes; an unguarded hoist would create read-target nodes for allocation nodes the unoptimized pass leaves untouched. These are performance optimizations that MUST preserve the produced edge set exactly (INV-ANA-39); they MUST NOT prune, depth-limit, or otherwise alter the WTG algorithm's result. The per-allocation forward-reachability closure (`GraphUtil.reachableNodes()`) is out of scope for this requirement and remains as-is.

The optimization addresses the dominant pre-WTG cost without changing output, so APKs that previously exceeded the analysis timeout during this pass can complete and emit `transitions[]`. When an APK still times out, the write-first partial-JSON behavior is unchanged: reachability, windows, and components remain populated and `transitions[]` is empty, which downstream consumers (rv-agent, aperv `scoreWtg`) already handle by degrading cleanly (NFR04).

#### Scenario: Optimized pass produces identical transitions on a passing APK
- **WHEN** GATOR analyzes an APK that already produces `transitions>0` under the unoptimized pass (one of the 72 baseline APKs from the `experimento-20260604` sweep)
- **THEN** the `transitions[]` section of the produced JSON MUST be identical (diff-zero on the edge set keyed on stable identifiers: source window name, target window name, event type, widget name, and handler signature — not on the GATOR-assigned numeric node IDs, which need not be stable) to the unoptimized output
- **AND** the `reachability`, `windows`, and `components` sections MUST be unchanged

#### Scenario: Read-field resolution is hoisted out of the write loop
- **WHEN** `buildFlowThroughContainer()` processes an allocation node whose container has `W` write statements and `R` read statements
- **THEN** `getReadContainerField(tgt)` MUST be invoked at most `R` times for that allocation node (once per read statement), NOT `W × R` times (once per write-read pair)
- **AND** the resulting writer-to-reader edges MUST be the same edges the unoptimized `W × R` traversal would add (INV-ANA-39)

#### Scenario: Hoist does not create nodes for an allocation node that adds no edge
- **WHEN** `buildFlowThroughContainer()` processes an allocation node whose container has read statements but whose write statements all fail to resolve to a writer node (`getWriteContainerField` returns null or the writer node is null)
- **THEN** the optimized pass MUST NOT invoke the target-node factories (`simpleNode`/`varNode`) for that allocation node's reads, creating no read-target flow-graph nodes — identical to the unoptimized pass, whose nested loop never reaches the read resolution when no writer node exists
- **AND** the set of flow-graph nodes and the produced edge set MUST be unchanged from the unoptimized pass (INV-ANA-39c)

#### Scenario: Field-position resolution is memoized across allocation nodes
- **WHEN** the same container statement appears as a read or write across multiple allocation nodes in `flowgraph.allNAllocNodes`
- **THEN** its container-field position MUST be resolved by `getReadContainerField`/`getWriteContainerField` once and reused from a `Map<Stmt,Integer>` for subsequent allocation nodes
- **AND** the memoized value MUST equal the value a fresh resolution would return (purity, INV-ANA-39)

#### Scenario: APK that previously timed out completes WTG construction
- **WHEN** GATOR analyzes an APK that exceeded the analysis timeout inside `buildFlowThroughContainer()` under the unoptimized pass (one of the 97 sweep timeouts)
- **THEN** the optimized pass MAY allow the analysis to complete within the same timeout and emit a populated `transitions[]`
- **AND** if it still times out, the partial JSON MUST preserve `reachability`, `windows`, and `components` with `transitions[]` empty, unchanged from the prior timeout behavior (NFR04)
