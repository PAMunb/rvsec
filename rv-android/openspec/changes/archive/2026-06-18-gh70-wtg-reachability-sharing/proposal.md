> **⛔ DESFECHO (2026-06-18): NÃO-VIÁVEL — revertido. Ver `REPORT-validation.md`.**
> A premissa do design (grafo de sucessores estático durante o passo) é falsa:
> `buildFlowThroughContainer` muta o grafo (`addEdgeTo` no laço) e a reachability de cada
> nó de alocação precisa ver as arestas das iterações anteriores. Pré-computar uma vez
> zerou `transitions` em 19/20 APKs baseline-`tr>0`. Código revertido ao estado gh66;
> INV-ANA-45 **não** sincronizada. Resultado negativo documentado; gh70 não vira fix.

## Why

GitHub Issue: #70

Follow-up to #66 (Fix 1). gh66 removed the quadratic container-field resolution hot spot in `FlowgraphRebuilder.buildFlowThroughContainer()` (semantics-preserving; diff-zero proven on the 72 baseline-`tr>0` APKs). But the empirical validation (archived `2026-06-18-gh66-.../REPORT-validation.md`) showed WTG construction is **still timeout-bound**: on the 169-APK JCA corpus the WTG count stayed at **72** (= baseline), net recovery ≈ **+1** (`org.fossify.musicplayer` 0→54). Decisive measurement: the **96** APKs that emit `complete` with `transitions==0` **all hit the timeout** (`analysis_seconds` = 1800s/3600s) — they are **not** genuine zero-transition apps; the WTG simply does not finish building.

With Fix 1's hot spot gone, the dominant remaining cost is the **per-allocation-node forward-reachability closure** `GraphUtil.reachableNodes(...)` called inside the `for (Expr e : flowgraph.allNAllocNodes.keySet())` loop of `buildFlowThroughContainer()` (`FlowgraphRebuilder.java`, the `reachableNodes` call ~line 327). It is a BFS recomputed from scratch for each of `N` allocation nodes, over `getSuccessors()`, with heavily overlapping closures — `O(N × (V+E))`. This is the deferred "Fix 2" the gh66 design (D2) explicitly scoped out as the higher-payoff but more delicate change, to be done after measuring Fix 1. That measurement is now in: it motivates this change.

Diagnosis context: archived `2026-06-18-gh66-gator-wtg-flowcontainer-perf/REPORT-validation.md` (§4 — the timeout-bound finding), `docs/20260613_wtg_timeout_buildflowthroughcontainer.md` (original three-fix diagnosis).

## What Changes

- **GATOR (`rvsec` monorepo, Java)**: Eliminate the per-allocation recomputation of forward reachability in `FlowgraphRebuilder.buildFlowThroughContainer()`. Instead of calling `GraphUtil.reachableNodes(allocNode)` independently for every allocation node, **compute the shared reachability once and reuse it** — e.g. condense the flow graph's strongly-connected components (the graph has cycles, which is why the current BFS carries a visited set) and propagate reachable-node sets over the condensation DAG, or memoize per-node closures. The change is **semantics-preserving**: the reachable-node set returned for each allocation node MUST be **identical** to the current `reachableNodes()` result, so the derived `reads`/`writes` sets — and therefore the WTG `transitions[]` edge set — are unchanged (INV-ANA-45, diff-zero / INV-ANA-39 from gh66 still holds).
  - The `NOpNode` subtlety MUST be preserved exactly: the current traversal **adds** an `NOpNode` to the reachable set but does **not** expand through it (`if (!(s instanceof NOpNode)) worklist.add(s); reachableNodes.add(s);`). Any condensation/closure reformulation MUST reproduce this "include-but-don't-expand" behavior node-for-node.
  - Implement as a **new cached/precomputed variant scoped to `buildFlowThroughContainer`**, NOT by changing the public `GraphUtil.reachableNodes`/`findReachableNodes` (used by other callers) — avoids perturbing unrelated analyses (P3: no incidental behavior change elsewhere).
- **rv-android**: Rebuild `lib/gator/rvsec-gator.jar` from the corrected source (gitignored Maven build artifact; same source-vs-JAR discipline as gh66 / `e584894a`).
- **Out of scope**: any pruning, depth-limiting, or approximation of the WTG algorithm (would change the result — forbidden); the `buildFlowThroughContainer` field-resolution hoist/memoize (already done in gh66); the `TargetResolver`/extractor reachability path (that is #69's territory — disjoint files).

## Capabilities

### New Capabilities
<!-- None. Performance fix; introduces no new documented behavior or data. -->

### Modified Capabilities

- `analysis`: The `analysis` domain gains one current-state invariant documenting that the per-allocation forward-reachability closure in `buildFlowThroughContainer` is computed via shared/precomputed reachability rather than recomputed per allocation node, producing reachable-node sets — and therefore WTG flow edges — **identical** to the unshared computation. New invariant **INV-ANA-45** (39 used by gh66; 40–44 reserved by the active gh69 delta; 45 is the first free number — verified against `openspec/specs/analysis/spec.md` and the gh69 change delta). No existing requirement scenario changes — `transitions[]` is **edge-set-identical**; only the time-to-produce changes. This complements gh66's INV-ANA-39 (which scoped the per-alloc reachability closure OUT); INV-ANA-45 now covers it.

## Impact

- **Modules**: `rv-static-analysis` (consumer of the GATOR JAR; no Python source change). GATOR source at `rvsec/rvsec-android/rvsec-gator` (same `PAMunb/rvsec` monorepo git root as rv-android).
- **Single repo, one commit**: the Java edit, OpenSpec artifacts, and docs land atomically. The rebuilt `lib/gator/rvsec-gator.jar` is a gitignored Maven build output (not committed; reproduced by the build).
- **Coordination with #69 (active)**: NO file conflict — #69 touches `TargetResolver`/`UsedJcaMethodsVisitor` (reachability/target-matching path); gh70 touches `FlowgraphRebuilder`/`GraphUtil` (WTG flow graph). Disjoint INV-ANA numbering (#69 = 40–44, gh70 = 45). The shared concern is the **gator JAR rebuild**: whoever rebuilds must include the other's committed source (source-vs-JAR discipline). Also coexists with gh57 (Analysis spec, ≤24) — disjoint.
- **Downstream consumers**: rv-agent (WTG navigation) and aperv (`scoreWtg`) receive more complete `transitions[]` for APKs that previously timed out. Both degrade cleanly on empty `transitions[]`, so this is an improvement, not a correctness prerequisite.
- **Requirements**: FR04 (GATOR WTG — primary), FR05/FR06 (same JSON, unaffected), NFR04 (write-first timeout degradation preserved).
- **Risk**: Medium (higher than gh66). The fix is **algorithmic** (SCC condensation / shared closure over a cyclic graph, with the `NOpNode` subtlety) on a hot path, not a one-line memoization. Mitigated by: a guarded same-result discipline (the cached variant MUST return sets identical to `reachableNodes`), a unit test asserting set-equality on a fixture graph (cycles + `NOpNode`), and the full-corpus diff-zero gate (`scripts/wtg_sweep_invariance.py`) re-run before claiming any recovery. The standing "do not touch GATOR" rule was already relaxed for semantics-preserving perf fixes by gh66's ADR — this change operates under that precedent (no new ADR needed unless the SCC approach introduces a structural decision worth recording).
