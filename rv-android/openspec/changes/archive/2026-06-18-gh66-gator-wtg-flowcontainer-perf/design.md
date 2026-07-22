## Context

GATOR's WTG construction is timeout-bound (proposal #66): 72/169 APKs produced `transitions[]` in the `experimento-20260604` sweep, the other 97 timed out, and doubling the timeout rescued ~1 in 65. A `jstack` probe localized the cost to `FlowgraphRebuilder.buildFlowThroughContainer()` (`rvsec-android/rvsec-gator/sootandroid/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java:311-369`), an O(allocNodes × flowgraph) pass that runs single-threaded in `preBuild`, before the WTG stages. The full diagnosis (six dumps, two hot spots) is in `docs/20260613_wtg_timeout_buildflowthroughcontainer.md`.

This design covers **Fix 1** only: a semantics-preserving optimization of one hot spot (the read-side container-field resolution), validated to produce an **edge-set-identical** `transitions[]` (the same set of WTG edges keyed on stable identifiers — see *Validation comparator* below; the JSON array ordering is not relied upon). It satisfies the `analysis` delta requirement *WTG Container-Flow Linking Pass Performance* and INV-ANA-39 (FR04; NFR04 timeout degradation preserved). The change edits the GATOR original at `rvsec/rvsec-android/rvsec-gator` and rebuilds `lib/gator/rvsec-gator.jar` — both are subdirectories of the same `PAMunb/rvsec` monorepo (verified: shared git root `.../workspace-rv/rvsec`), so the edit lands in a single commit. Editing the static-analysis engine and relaxing the standing "do not touch GATOR" rule are what make this a Full SDD change with an ADR.

Constraint (binding): the optimization MUST NOT alter the WTG result. "Make the WTG smaller/faster by pruning" is explicitly forbidden; only constant-factor reductions that preserve the edge set are in scope.

## Architecture

The change is localized to one GATOR method. No rv-android Python source changes — the tooling already invokes the GATOR JAR; only the JAR artifact is refreshed.

Both paths below are subdirectories of the one `PAMunb/rvsec` monorepo.

```
rvsec-android/rvsec-gator (Java source)        lib/gator (build output)
───────────────────────────────────────       ────────────────────────
FlowgraphRebuilder.buildFlowThroughContainer()
  ├── outer: for (Expr e : allNAllocNodes)
  │     ├── reachableNodes(alloc)   [Fix 2 — OUT OF SCOPE, unchanged]
  │     └── for (src : writes)                            ──┐
  │           ├── resolve sn (cached); skip if null         │  mvn build +
  │           ├── LAZY-build readTargets on 1st valid sn     │  plugin copy
  │           │     [Fix 1a — guarded hoist, no node-create  │
  │           │      side effect when no write resolves]     │
  │           └── for (tn : readTargets) sn.addEdgeTo(tn)    │
  └── cachedReadContainerField / cachedWriteContainerField│  ───────────────►  lib/gator/rvsec-gator.jar
        via Map<Stmt,Integer>        [Fix 1b — memoize] ──┘                     (gitignored build artifact)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `FlowgraphRebuilder.buildFlowThroughContainer()` | Link data flow through container reads/writes before WTG stages | `flowgraph.allNAllocNodes` | flow edges (`sn.addEdgeTo(tn)`) |
| `WTGUtil.getReadContainerField(Stmt)` | Resolve a read statement's container-field position (pure fn of stmt) | `Stmt` | `Integer` position / null |
| `WTGUtil.getWriteContainerField(Stmt)` | Resolve a write statement's container-field position (pure fn of stmt) | `Stmt` | `Integer` position / null |
| `rvsec-gator` maven module | Build the GATOR JAR | Java source | `rvsec-gator.jar` |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test / Validation |
|-------------------------|----------------|-------------------|
| Req. *WTG Container-Flow Linking Pass Performance* (FR04) | `buildFlowThroughContainer()` rewritten: hoist read-target precompute + memoized field resolution | Diff-zero edge comparison on 72 baseline APKs (`out/sweep_20260604_wtg_spark`) |
| INV-ANA-39 (purity + edge-set preservation) | `cachedReadContainerField`/`cachedWriteContainerField` (`Map<Stmt,Integer>`); precomputed `readTargets` list | Diff-zero comparison; optional JUnit purity assertion on the cache |
| Scenario: hoisted resolution (`R` not `W×R`) | read resolution moved out of `for(src:writes)` loop | Code review + counter/log inspection on one APK |
| Scenario: memoized across alloc nodes | `Map<Stmt,Integer>` declared before outer loop | Code review + cache-hit count |
| Scenario: previously-timed-out APK completes | same edges, lower constant factor | Recovery run on the 97 timeouts; `jstack` re-probe |
| NFR04 (timeout degradation preserved) | no change to write-first partial-JSON path | Inspect a still-timing-out APK: reach+windows+components present, `transitions[]` empty |

## Goals / Non-Goals

**Goals:**
- Reduce the constant factor of `buildFlowThroughContainer()` by eliminating the read-side resolution recomputed per `(write × read)` pair and across allocation nodes.
- Produce edge-set-identical `transitions[]` on all APKs (diff-zero on the 72 baseline; same WTG edge set, ordering not relied upon).
- Recover `transitions[]` for some fraction of the 97 timeouts; measure how many.
- Keep source-and-JAR in sync (rebuild `rvsec-gator.jar`), per the `e584894a` discipline.

**Non-Goals:**
- The per-allocation forward-reachability closure `GraphUtil.reachableNodes()` (line 319) — that is Fix 2/3, deferred. Measure Fix 1 first.
- Any change to the WTG algorithm's output (pruning, depth limits, `sDepth`). Forbidden.
- Any rv-android Python change, any change to the partial-JSON / timeout path, any change to other GATOR phases.
- Parallelizing the pass.

## Decisions

**D1 — Edit the GATOR original (relax the "don't touch GATOR" rule).** The diagnosis proved there is no native configuration lever (`buildFlowThroughContainer` is unconditional) and that a larger timeout is futile (super-linear cost). The only fix is a code change. Because the change preserves semantics (identical edges), it does not alter the analysis contract; it relaxes the standing rule specifically for semantics-preserving performance fixes. Recorded in ADR (`docs/adr/`). *Alternative — accept the 72 and stop (proposal option C): rejected because the consumer wants transitions and the fix is low-risk and validable byte-for-byte.*

**D2 — Fix 1 only; defer Fix 2.** Fix 1 (read-side hoist + memoize) is edge-set-identical by construction (pure resolvers + guarded hoist, D3) and risk ~zero. Fix 2 (avoid per-alloc transitive closure) has the larger asymptotic payoff but is delicate to keep identical. *Alternative — Fix 1+2 together: rejected; measure Fix 1's recovery first, then decide whether Fix 2 is warranted (proposal option A → measure → B).*

**D3 — Hoist by precomputing a `readTargets` list per allocation node, guarded against the read loop's node-creation side effect.** For each `tgt` in `reads`, resolve `tgtPos = getReadContainerField(tgt)` and compute the target node `tn` once, collecting the non-null `tn` into a `List<NNode> readTargets`; the inner loop becomes `for (NNode tn : readTargets) sn.addEdgeTo(tn)`. Two things must hold for byte-for-byte equivalence, and only the first is about edges:

1. **Edge set.** `addEdgeTo` targets a set and the same `(src,tgt)` pairs are visited, so the produced edge set is identical regardless of `readTargets` ordering.
2. **Node-creation side effects (the subtle one).** Computing `tn` calls `simpleNode(...)`/`varNode(...)` (`FlowgraphRebuilder.java:794-839`), which are **not** pure getters — they lazily create and register flow-graph nodes (`varNode`/`fieldNode` get-or-create; `classConstNode` does `new NClassConstantNode` + `flowgraph.allNNodes.add`; `stringConstantNode`/`allocNode` create). In the original code the read loop runs only when some write resolves to a non-null `sn` (the `if (sn == null) continue;` and the nesting guarantee `tn` is never computed for an alloc node that adds no edge). An **unguarded** precompute would call `simpleNode`/`varNode` for every `tgt` of every alloc node — including alloc nodes whose writes all fail to resolve — creating read-target nodes the unoptimized pass never creates. That divergence cannot be caught by the diff-zero gate on the 72 (it may only manifest on a previously-timed-out APK, which has no baseline), so it must be designed out, not validated away.

   **Resolution:** materialize `readTargets` **lazily** — build it on the first iteration that produces a non-null `sn`, and skip the whole write loop body when no write resolves. This reproduces the original's "no read-target node is created unless at least one edge would be added" property exactly, so both the edge set and the node-creation side effects match. (Equivalently: pre-check that `writes` contains at least one resolvable `sn` before building `readTargets`.)

*Side effect: the `Logger.verb` "read container stmt can not be found" message is emitted once per unresolved `tgt` (when the read loop runs at all) instead of `|writes|×` — a verbose-level log volume reduction, not an edge change.* *Alternative — memoize `getReadContainerField` but keep the nested structure: rejected; still recomputes the `tn` node lookup and re-walks the read set per write, leaving most of the redundancy. Alternative — unguarded precompute: rejected for the node-creation divergence above.*

**D4 — Memoize field resolution with `Map<Stmt,Integer>` using `containsKey`, not `computeIfAbsent`.** Both resolvers can legitimately return `null` (statement is not a container op). `computeIfAbsent` does not store null and would re-resolve every null every time, so use an explicit `if (cache.containsKey(s)) return cache.get(s);` pattern that caches null. The caches are method-local, declared before the outer loop so they span all allocation nodes (the recurrence we are exploiting). *Alternative — a field-level cache on `WTGUtil`: rejected; method-local keeps lifetime tight (P1) and avoids cross-analysis staleness.*

**D5 — Validate by diff-zero on the 72, then measure recovery on the 97.** The 72-APK baseline (`out/sweep_20260604_wtg_spark`, present) is the ground truth; the corrected JAR must reproduce identical `transitions[]` edges. Only after diff-zero passes do we run the 97 timeouts and count completions, and re-run `scripts/jstack_wtg_probe.sh` on `ch.famoser.mensa` to confirm the hot spot moved off `getReadContainerField`. *Same protocol as the arity fix `e584894a`.*

## API Design

### `private List<NNode> /* inlined */` — read-target precompute (within `buildFlowThroughContainer`)

For each allocation node, only once a write has resolved to a non-null `sn` (lazy materialization, D3):
- **Precondition**: `reads` is the set of read statements reachable through the container, **and** at least one write statement of this alloc node resolved to a non-null `sn` (otherwise `readTargets` is never built and `simpleNode`/`varNode` are never called — matching the original, which never reaches the read loop in that case).
- **Postcondition**: `readTargets` contains exactly the non-null `tn` nodes that the original inner loop would have produced **and created** for those reads — `tgtPos == null` and `tn == null` reads are skipped identically, and no read-target node is materialized for an alloc node that adds no edge.
- **Error behavior**: none; unresolved reads are skipped (with one `Logger.verb` each, only when the read loop runs).

### `private Integer cachedReadContainerField(Stmt s)` / `cachedWriteContainerField(Stmt s)`

```
Integer cachedReadContainerField(Stmt s) {
  if (readFieldCache.containsKey(s)) return readFieldCache.get(s);  // caches null
  Integer v = wtgUtil.getReadContainerField(s);
  readFieldCache.put(s, v);
  return v;
}
```
- **Precondition**: `readFieldCache` is a `Map<Stmt,Integer>` declared before the outer `allNAllocNodes` loop.
- **Postcondition**: returns the same value `wtgUtil.getReadContainerField(s)` would return (purity, INV-ANA-39); resolves the underlying method reference at most once per distinct `s` per `buildFlowThroughContainer` invocation.
- **Error behavior**: delegates to the existing resolver, which already catches resolution exceptions and returns null.

## Data Flow

`flowgraph.allNAllocNodes` → (per alloc) `reachableNodes` → `reads`/`writes` sets → **precompute** `readTargets` (cached read-field resolution) → **per write** resolve `sn` (cached write-field resolution) → add edges `sn → tn` for each precomputed `tn` → flow edges consumed by the WTG stages → `transitions[]` JSON section. The data produced is identical to the prior flow; only the number of resolver invocations decreases.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Method-ref resolution failure | `getRead/WriteContainerField` (Soot) | Already caught inside the resolver → returns `null` | Cache stores `null`; statement skipped, same as today |
| `RVCommandTimeoutError` | Analysis exceeds `--timeout` | Unchanged: write-first partial JSON | reach+windows+components persisted; `transitions[]` empty (NFR04) |
| JAR/source drift | Forgetting to rebuild `rvsec-gator.jar` | Rebuild + copy step in tasks.md; mirror `e584894a` | Re-run diff-zero on 72; mismatch signals stale JAR |

## Risks / Trade-offs

- **[Fix 1 alone may not move enough of the 97 below the timeout]** → The other hot spot (`reachableNodes` per alloc, line 319) is untouched; some APKs are dominated by it. Mitigation: D5 measures the recovery; if marginal, Fix 2 becomes a follow-up change (the consumer degrades cleanly meanwhile).
- **[A subtle non-purity in the resolvers would make memoization diverge]** → The resolvers are verified pure (read only the statement, the static container-method maps, and Scene-global `hier`). Mitigation: INV-ANA-39 diff-zero on 72 APKs is the gate; any single divergent edge fails the change before it ships.
- **[The hoist creates flow-graph nodes the original would not]** → `simpleNode`/`varNode` are node factories with lazy-create side effects (D3, point 2). An unguarded precompute would materialize read-target nodes for alloc nodes that add no edge, diverging from the original — and the diff-zero gate **cannot** catch this in general, because the 97 timeout APKs have no `transitions[]` baseline to diff against, so a divergence that only manifests on a recovered APK would ship unseen. Mitigation is by *construction*, not validation: the guarded/lazy materialization (D3) reproduces the original's "no node created unless an edge is added" property exactly. Code review (task 5.1) verifies the guard is present.
- **[Mixed-build dataset]** → The delivered dataset stays as-is (72 already shipped); a recovery run only *adds* `transitions[]` to APKs that had none, never rewrites the 72. No regression surface.
- **[Validating against a stale JAR]** → The JAR is a gitignored Maven build artifact; running diff-zero without rebuilding would pass on old behavior. Mitigation: rebuild via Maven (plugin auto-copies) before validating, and the jstack re-probe (4.3) behaviorally confirms the new code shipped. Single monorepo, single commit — no cross-tree landing hazard.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Validation (primary) | `transitions[]` edge-set-identical | Diff edges of corrected JAR vs `out/sweep_20260604_wtg_spark` on all 72 baseline APKs (see *Validation comparator*) | 72 APKs |
| Validation (recovery) | How many of 97 timeouts complete | Recovery run with corrected JAR, count `transitions>0` | 97 APKs |
| Profiling | Hot spot moved off `getReadContainerField` | Re-run `scripts/jstack_wtg_probe.sh` on `ch.famoser.mensa` | 1 APK, ≥6 dumps |
| Unit (mandatory) | Cache purity / `containsKey`-null behavior | JUnit in `rvsec-gator/sootandroid/src/test`: `cachedX(s) == wtgUtil.getX(s)` incl. the `null` (non-container) case; static-check the diff has no `computeIfAbsent` | 1-2 tests |
| Integration (mandatory) | `transitions[]` **edge set** preserved (not just count) | Extend `BaselineComparisonIT` (client module, `RVSEC_HOME`-gated, `mvn verify`) to compare the edge set on the stable 5-field key on `cryptoapp.apk` — today it only asserts `transitions.size()` | 1 IT |
| Differential (guard, B1 / INV-ANA-39c) | No extra flow-graph node created when an alloc node has reads but no resolvable write | A/B run original vs corrected JAR with a throwaway node counter; assert `allNNodes` delta identical AND the guard path is exercised (>0) on ≥1 APK | A/B on a sample |
| Regression (NFR04) | Timeout still yields partial JSON | Inspect a still-timing-out APK's JSON sections | 1 APK |
| Reproducibility (RISK-002) | Clean rebuild reproduces a passing JAR | Clean Maven rebuild from committed source then re-run the 72 diff-zero | 72 APKs |

Validation is **layered, and no single layer is the sole gate**:
- **Automated** (CI-able, `mvn verify`): a purity unit test for the cached resolvers and an edge-set regression IT (`BaselineComparisonIT` upgraded from count to edge set) catch the common regressions on every build.
- **Empirical** (full corpus, manual protocol): edge-set diff-zero on all 72 baseline APKs (exhaustive), the guard differential (the one B1 hazard the 72-diff-zero cannot see — see Risks), the jstack re-probe, the NFR04 regression, and the clean-rebuild reproducibility check.

The rv-android Python pytest suite does not apply — this is a Java/GATOR change whose contract is "identical edge set, faster".

### Validation comparator (diff-zero definition)

"Diff-zero" compares the **edge set**, not raw file bytes. Each `transitions[]` edge in `{app}.json` is `{sourceId, targetId, events:[{widgetId, type, handlerMethod}]}`. The numeric `sourceId`/`targetId`/`widgetId` are GATOR-assigned node IDs and are **not guaranteed stable across builds**, so the comparator MUST key on stable identifiers, not raw IDs:

- edge key = (`source window name`, `target window name`, and for each event: `event type`, `widget name`, `handler signature`), resolving window/widget IDs to their `name` via the same JSON's `windows[]`/`widgets[]` before comparison;
- comparison is **set equality** (order-independent): the corrected-JAR edge set MUST equal the baseline edge set with zero additions and zero removals;
- scope the baseline to the **canonical per-APK JSONs** under `out/sweep_20260604_wtg_spark/<app>/<app>.apk.json`, **excluding** the `_backup/` directory (otherwise duplicates inflate the 72 count).

`scripts/wtg_paridade_diff.py` is **not** sufficient as-is: it is a Jaccard-similarity comparator keyed on the 3-tuple `(sourceId, targetId, event_type)` with a tolerance threshold and raw numeric IDs — it omits widget/handler identity and tolerates divergence. The gate needs exact set-equality on the stable 5-field key above; task 4.1 either (a) extends/replaces it with a faithful exact comparator, or (b) runs it at `--threshold-avg 1.0 --threshold-min 1.0` only as a coarse pre-check, with the exact comparison as the actual gate.

## Open Questions

- After measuring D5 recovery: is Fix 2 (per-alloc reachability) warranted as a follow-up change, or is the recovered fraction enough for the consumer? (Decide post-measurement; not a blocker for this change.)

(Resolved during design: `rvsec-gator` has a JUnit/IT test tree — `sootandroid/src/test` and `client/src/test` hold 21 tests, JUnit 4.12, surefire/failsafe, including the `RVSEC_HOME`-gated `BaselineComparisonIT`. So the purity unit test and the edge-set IT are mandatory layers, not optional. No existing test exercises `buildFlowThroughContainer`/`FlowgraphRebuilder`/`WTGUtil`, so the changed method has zero direct coverage today; this change adds it.)
