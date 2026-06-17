## Why

GitHub Issue: #66

The Window Transition Graph (WTG) section of GATOR static analysis (FR04) is timeout-bound, not time-bound. In the `experimento-20260604` WTG sweep (169 JCA APKs, SPARK + `cgDelegation=true`), only **72/169 APKs** produced `transitions>0`; the other **97 all timed out** during WTG construction — and doubling the timeout (1800s→3600s) rescued ~1 in 65. A `jstack` probe (6 dumps on `ch.famoser.mensa_60`, a 2 MB app) showed the `main` thread RUNNABLE on-CPU, single-threaded, inside `FlowgraphRebuilder.buildFlowThroughContainer()` — a pass that runs in `preBuild`, **before** WTG stage 1, and is **O(allocNodes × flowgraph) quadratic**. The cost is real work, not waiting; more time does not help. A semantics-preserving performance fix to one hot spot of that pass recovers tractability without altering the WTG result, raising transition completeness for the consumer (rv-agent navigation; aperv scoring).

Full diagnosis (problem, jstack evidence, three fix options, validation protocol): `docs/20260613_wtg_timeout_buildflowthroughcontainer.md`. Sweep context: `docs/20260609_sweep_wtg_completo_169.md` and `docs/20260613_relatorio_sweep_wtg_jca_169.md`.

## What Changes

- **GATOR (`rvsec` monorepo, Java)**: Optimize `FlowgraphRebuilder.buildFlowThroughContainer()` (`rvsec-android/rvsec-gator/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java:311-369`), the quadratic container-flow linking pass, with two semantics-preserving moves:
  - **(a) Hoist** the per-target resolution — `WTGUtil.getReadContainerField(tgt)` plus the target-node computation — out of the inner `for (Stmt src : writes)` loop, so each `tgt` is resolved once per alloc node instead of once per `(src × tgt)` pair (`|writes|×|reads|` → `|reads|` resolutions). `getWriteContainerField(src)` is already hoisted at line 334; only the read side is redundant. The hoist is **guarded**: the read-target nodes are materialized only when the alloc node has at least one resolvable write (the original computes them lazily inside the write loop, never reaching the read loop when no write resolves). This is required because the target-node computation (`simpleNode`/`varNode`, `FlowgraphRebuilder.java:794-839`) is *not* a pure getter — it lazily creates and registers flow-graph nodes — so an unguarded precompute would create read-target nodes for alloc nodes that add zero edges, a side effect the unoptimized pass does not have. The guard keeps both the edge set **and** the node-creation side effects identical.
  - **(b) Memoize** `getReadContainerField`/`getWriteContainerField` in a `Map<Stmt,Integer>` that survives the outer `for (Expr e : allNAllocNodes)` loop, since the same container statements recur across alloc nodes. `getReadContainerField` (`WTGUtil.java:919-944`) is a pure function of the statement (verified: reads only the statement, the static container-method maps, and the Scene-global hierarchy), so memoization preserves the edge set exactly.
- **rv-android**: Rebuild `lib/gator/rvsec-gator.jar` from the corrected source — the JAR is a Maven build artifact (the `rvsec-gator` module produces it and a Maven plugin copies it into `lib/gator/`); it is gitignored by design. Same source-vs-JAR discipline as the arity fix `e584894a`.
- **Out of scope** (NOT in this change): the per-alloc `GraphUtil.reachableNodes()` transitive closure at line 319 (Fix 2 / Fix 3 in the diagnosis); any pruning or depth-limiting of the WTG algorithm (would change the result — explicitly forbidden).

This change edits the GATOR original. It **relaxes the standing project rule "do not touch the GATOR"** specifically for semantics-preserving performance fixes that produce identical output. This is an architectural decision recorded via ADR in the design phase — and the reason the change uses the Full SDD track (it modifies the static-analysis engine and a standing rule, not because of repo topology).

## Capabilities

### New Capabilities
<!-- None. This is a performance fix; it introduces no new documented behavior or data. -->

### Modified Capabilities

- `analysis`: The `Unified Static Analysis` requirement (FR04/FR05/FR06) gains one current-state invariant documenting that GATOR's pre-WTG container-flow linking pass (`buildFlowThroughContainer`) resolves container field positions via memoization and loop hoisting, producing flow edges **identical** to the unoptimized pass. New invariant **INV-ANA-39** (16–24 reserved by gh57; 30–38 used by gh60; 39 is the first free number — verified no collision across the openspec tree). No existing requirement scenario changes — the produced `transitions` section is **edge-set-identical** (the same set of WTG edges, keyed on stable identifiers; the JSON array ordering is not part of the contract); only the time-to-produce changes. The invariant exists so the spec records why the pass is structured as it is, alongside the existing GATOR internals invariants (defensive config INV-ANA-16, Flowgraph graceful skip INV-ANA-17, Soot version INV-ANA-18).

## Impact

- **Modules**: `rv-static-analysis` (consumer of the GATOR JAR; no Python source change — the tooling already invokes GATOR). The GATOR source lives at `rvsec/rvsec-android/rvsec-gator`, a subdirectory of the same `PAMunb/rvsec` monorepo as rv-android (verified: both share git root `.../workspace-rv/rvsec`), not in the rv-android uv workspace.
- **Single repo, one commit**: rv-android and the GATOR Java tree are subdirectories of one repository, so the Java edit, the OpenSpec artifacts, and the docs land in a single atomic commit. The rebuilt `lib/gator/rvsec-gator.jar` is a Maven-generated build artifact (gitignored by design) — not committed, reproduced by the Maven build; source-vs-JAR consistency mirrors `e584894a`.
- **Downstream consumers**: rv-agent (navigation guidance via WTG transitions) and the aperv tool (`scoreWtg`) receive more complete `transitions[]` for APKs that previously timed out. Both already degrade cleanly when `transitions[]` is empty (`scoreWtg→0`), so the change is an improvement, not a correctness prerequisite.
- **Requirements**: FR04 (GATOR WTG analysis — primary), FR05/FR06 (same JSON, unaffected), NFR04 (Resilience — write-first timeout degradation is preserved; partial JSON on timeout still carries reachability + windows + components).
- **Risk**: Low. The fix is local to one method, validated by a diff-zero edge comparison on the 72 already-passing APKs before measuring recovery on the 97 timeouts.
