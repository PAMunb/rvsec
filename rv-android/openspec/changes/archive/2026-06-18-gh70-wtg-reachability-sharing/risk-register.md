# Risk Register: gh70-wtg-reachability-sharing

**GitHub Issue**: #70
**Change**: Eliminate the per-allocation forward-reachability recomputation in GATOR `FlowgraphRebuilder.buildFlowThroughContainer()` (Fix 2, follow-up to #66). Replace the `N` independent `GraphUtil.reachableNodes(allocNode)` BFS calls with a single shared computation — SCC condensation + reverse-topological reachable-set propagation over the condensation DAG — returning per-allocation reachable sets **identical** to `reachableNodes` (incl. the `NOpNode` include-but-don't-expand rule), so the derived `reads`/`writes` and WTG `transitions[]` edge set are unchanged (INV-ANA-45, consistent with gh66's INV-ANA-39).
**Track**: Full SDD (edits the GATOR analysis engine; algorithmic change on a hot path). Single monorepo (`PAMunb/rvsec`); one commit covers source + tracked artifacts. The shipped `lib/gator/rvsec-gator.jar` is a gitignored Maven build artifact.
**Owner**: Pedro Costa
**Date**: 2026-06-18
**References**: `design.md` (D1–D4, Risks, API Design), `proposal.md`, `tasks.md`, `modules/rv-static-analysis/docs/adr/ADR-001-relax-gator-no-touch-rule-for-semantics-preserving-perf-fixes.md` (gh70 operates under this — no new ADR), archived gh66 `risk-register.md` + `REPORT-validation.md` (the timeout-bound finding that motivates Fix 2), `docs/20260613_wtg_timeout_buildflowthroughcontainer.md`.

This register applies the **proactive strategy** principle: every risk below is identified before the Java edit lands, so the layered diff-zero discipline (in-process JUnit set-equality + full-corpus invariance gate, INV-ANA-45/INV-ANA-39) and the rebuild-before-validate discipline are in place as mitigations, not as post-failure fire-fighting. It inherits the **verified topology findings** from gh66 (a single monorepo, one commit; the JAR is a by-design Maven build output) and reweights the **correctness profile upward**: gh66 was a guarded hoist+memoize (mechanical); gh70 is an **algorithmic reformulation** (SCC condensation over a cyclic graph with the `NOpNode` subtlety), which is the harder correctness problem the gh66 design (D2) deliberately deferred for exactly this reason.

---

## Investigation Findings (ground truth for this register)

Verified against the working tree on 2026-06-18:

1. **Single repo, single working tree (inherited from gh66, re-confirmed).** `rv-android` and the GATOR Java tree (`rvsec/rvsec-android/rvsec-gator/...`) share one git root (`PAMunb/rvsec`). The Java source edit and every tracked artifact land in **one atomic commit** — no cross-tree partial-landing hazard. The shipped JAR is **gitignored by design** (Maven module builds it; a Maven plugin copies it into `lib/gator/`). Consequence carried forward: the corpus diff-zero gate **cannot detect a never-rebuilt (stale) JAR** (a stale JAR reproduces the baseline by definition). The behavioral proof the new code shipped is the **jstack re-probe (task 4.3)** plus the `javap` symbol check (task 3.3).

2. **The `NOpNode` rule is an asymmetric BFS detail, confirmed at `GraphUtil.findReachableNodes` (lines 42–61).** The traversal `add`s every successor to the result but only enqueues non-`NOpNode` successors: `if (!(s instanceof NOpNode)) worklist.add(s); reachableNodes.add(s);`. Critically, the **start node is always enqueued and expanded regardless of type** (`worklist.add(start)` at line 44, unconditional). So an `NOpNode` is a sink **only when reached as a successor**, not when it is itself the query origin. For Fix 2 this means: if an allocation node's strongly-connected component **contains** an `NOpNode`, the SCC's shared reachable set must still treat that `NOpNode` as a sink *for propagation across SCC boundaries*, yet the `NOpNode` must appear *inside* its own SCC's set. This start-vs-successor asymmetry is the single most error-prone point of the condensation (drives RISK-001).

3. **The public utility has other callers — `reachableNodes`/`findReachableNodes` must stay byte-for-byte.** `GraphUtil.findReachableNodes` is a shared method; the design (D2, INV-ANA-45c) requires the sharing to be a NEW private helper scoped to `buildFlowThroughContainer`, leaving the public method untouched. There are also `findBackwardReachableNodes` variants in the same file with a *different* `NOpNode` rule (lines 71–117) — these are out of scope and must not be confused with the forward rule when implementing the helper (a copy-paste-the-wrong-rule hazard, folded into RISK-001).

4. **INV-ANA numbering verified collision-free.** Main `analysis/spec.md` tops out at INV-ANA-39 (gh66). gh69's active delta reserves 40–44. gh70's delta introduces **45** (the first free number). No overlap. The only shared artifact with #69 is the **gator JAR rebuild** (source-vs-JAR discipline; RISK-005).

5. **Validation tooling exists.** `scripts/wtg_sweep_invariance.py` and `scripts/jstack_wtg_probe.sh` are present. The invariance gate was **relaxed in gh66 (commit d09002b9)**: windows/components compared by *structural identity* (window `name` set; component `(category, className)` set), reachability/package/mainActivity strict, `transitions` strict diff-zero. This relaxation is a known threat-to-validity, not a gh70 regression — but it means the gate's strength for gh70 rests almost entirely on the **`transitions` diff-zero** column, which makes the in-process JUnit set-equality test (task 4.A1) load-bearing, not redundant.

---

## Summary

| Risk Level | Count |
|------------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 3 |
| Low | 3 |

The change is **higher correctness risk than gh66** (the one High below). gh66 was a guarded hoist+memoize whose only un-gateable hazard was a node-creation side effect closed by construction; gh70 **reformulates the reachability algorithm** — SCC condensation + DAG propagation over a cyclic graph, replicating an asymmetric `NOpNode` sink rule. *Risk Projection* puts RISK-001 (set divergence vs `reachableNodes`) at **High** because the SCC reformulation is delicate (Moderate likelihood of an initial off-by-one on the `NOpNode`/start asymmetry) and a single divergent set on a recovered APK silently corrupts `transitions[]` where the corpus gate has no baseline (Serious effect). It is driven down to acceptable by a **layered, construction-first** strategy: a dedicated in-process JUnit set-equality test on cycle + `NOpNode` + diamond fixtures (the cheap correctness proof the corpus cannot isolate), the public-utility-untouched invariant, and the full-corpus `transitions` diff-zero gate as backstop — **all three GREEN before any recovery is claimed**. Governance risk is low (single monorepo, one commit, Maven-built JAR). Residual risk concentrates in **effectiveness** (RISK-004 — a third bottleneck may dominate, capping recovery) and **scope discipline** (RISK-006 — no pruning/approximation), neither of which can break correctness.

---

## Top Risks

### RISK-001: Shared-reachability set diverges from `reachableNodes` (the `NOpNode`/SCC reformulation)
- **Category**: Technology (correctness — the load-bearing risk)
- **Description**: The fix replaces `N` independent BFS closures with one SCC-condensation + reverse-topological DP. Correctness requires `helper.get(a)` to equal `GraphUtil.reachableNodes(a)` **as a set** for every allocation node `a`. The failure modes are specific and the diff-zero corpus gate cannot see most of them:
  - **(a) `NOpNode` sink rule mis-replicated in the condensation.** In the original BFS an `NOpNode` reached *as a successor* is added but not expanded; the *start* node is always expanded (Finding 2). In SCC form: an `NOpNode` must be a member of any SCC set that can reach it, but must **not** forward its own successors across SCC edges. If the condensation either (i) expands through an `NOpNode` (over-approximates → extra reachable nodes → spurious `reads`/`writes` → **added** WTG edges) or (ii) drops an `NOpNode` that the BFS would have included (under-approximates → **removed** edges), the result diverges. The asymmetry — an allocation node that *is itself* an `NOpNode` is still expanded — is an easy off-by-one to miss.
  - **(b) SCC self-inclusion / cycle handling.** All nodes in one SCC share a forward-reachable set that must include the entire SCC (the cycle is why the original carries a visited set). A condensation that computes "successors of the SCC" without unioning the SCC's own members back in under-approximates within-cycle reachability.
  - **(c) Wrong rule borrowed.** `GraphUtil` also has `findBackwardReachableNodes` with a *different* `NOpNode` treatment (Finding 3). Implementing the helper against the backward rule, or the public-API `stopAtOpNode` variant, silently changes semantics.
  - **Why the corpus gate is insufficient alone**: a divergence that manifests only on a previously-timed-out APK (one of the 96) has **no `transitions[]` baseline** to diff against — exactly the APKs gh70 is meant to recover. The relaxed invariance gate (Finding 5) further means `transitions` diff-zero is the *only* strict edge signal. So (a)/(b)/(c) must be caught by **in-process set-equality**, not validated away on the 72.
- **Probability**: **Moderate** (25–50%) — SCC condensation with an asymmetric sink rule is genuinely error-prone; a first implementation plausibly gets the `NOpNode`/start asymmetry or the SCC self-union subtly wrong. Detection probability is high (the unit test targets exactly these), so the *shipped*-divergence probability is low, but the *introduced*-divergence probability that the gates must catch is Moderate.
- **Effect**: **Serious** — a single added/removed reachable node changes `reads`/`writes`, hence the WTG edge set, violating the binding INV-ANA-45 constraint; if it lands only on a recovered APK it ships silently absent the unit test.
- **Risk Level**: **High** — *Risk Projection*: Moderate likelihood × Serious effect, elevated because the primary corpus gate is blind to the most likely failure surface (the 96 recovered APKs).
- **Mitigation Strategy**: Avoidance by construction + layered detection (the unit test is the *primary* gate here, the corpus the backstop).
- **Actions**:
  1. **(Construction)** Implement the helper to mirror `findReachableNodes` node-for-node: treat `NOpNode`s as sink-like for cross-SCC propagation (contribute self, do not forward successors), union each SCC's own members into its set, and preserve the start-vs-successor asymmetry (D3). Reference the **forward** rule (lines 42–61) only — never the backward variants.
  2. **(Detection, PRIMARY — task 4.A1)** `FlowgraphReachabilityShareTest`: in-process flow-graph fixtures — (i) a cycle, (ii) a node with an `NOpNode` successor, (iii) a node that *is* an `NOpNode` with successors, (iv) a diamond — assert `helper.get(n).equals(GraphUtil.reachableNodes(n))` for **every** node, not just allocation nodes. The `NOpNode` cases (a) and the start-is-`NOpNode` asymmetry are mandatory scenarios. Green under `mvn -pl sootandroid test`.
  3. **(Backstop — task 4.1)** Full-corpus invariance gate: `transitions` strict diff-zero on every baseline-`tr>0` APK (the 72). ANY added/removed edge fails the change. This catches (a)/(b) effects that land on the 72; it does NOT cover the 96 — that is why action 2 is primary.
  4. **(Edge-set IT — task 4.A2)** `BaselineComparisonIT` (cryptoapp) stays diff-zero on the gh70 JAR.
  5. **(Review — task 5.1)** Code review verifies the helper returns sets identical to `reachableNodes` incl. the `NOpNode` include-but-don't-expand rule, and that the cycle handling terminates.
- **Indicators**: any node where `helper.get(n) != reachableNodes(n)` in the unit test (RED — block); any added/removed edge on the 72 (RED — block); helper references `findBackwardReachableNodes` or `stopAtOpNode` in the diff (RED — wrong rule); recovered-APK `transitions` count implausibly large vs comparable apps (YELLOW — possible over-approximation through `NOpNode`, inspect).
- **Status**: Open (primary gate = unit set-equality 4.A1; backstop = corpus diff-zero 4.1).

### RISK-002: SCC condensation OOMs on the large graphs that are the problem cases
- **Category**: Technology (resource — trading timeout for OOM)
- **Description**: The APKs that time out have the largest flow graphs — precisely where any new data structure is most expensive. The design (D1) **rejects** a full `V×V` transitive-closure bitset for this reason (`O(V²)` memory). SCC condensation + per-SCC reachable-set storage is bounded by node/edge count, but the per-SCC reachable **sets** can still be large (a near-fully-connected condensation stores near-`V`-size sets per SCC → toward `O(V²)` in the union total). If a pathological APK exceeds heap, the fix trades a recoverable timeout for an OOM crash.
- **Probability**: **Low** (10–25%) — D1's SCC approach is asymptotically better than the rejected full-closure; most graphs condense substantially; the storage is the union of reachable sets, not a dense matrix.
- **Effect**: **Tolerable** — if it OOMs, the GATOR process fails on that APK and the existing write-first timeout/degradation path is *not* reached (an OOM is not a clean timeout). But it is a per-APK failure that degrades to "no JSON for that APK", which is no worse than today's timeout for that APK (which also yields no `transitions`), and does not affect the other 168.
- **Risk Level**: **Medium** — *Risk Projection*: Low × Tolerable, but listed prominently because it is the direct trade-off the algorithm choice makes and the design explicitly weighed it.
- **Mitigation Strategy**: Minimization + Contingency.
- **Actions**:
  1. **(Construction)** Implement per D1 (SCC condensation, not full closure); store reachable sets as shared references where SCCs share suffixes (reverse-topological DP naturally allows a successor SCC's set to be referenced, not copied) to keep memory near the union size, not the product.
  2. **(Detection — task 4.1 sweep)** The full-corpus sweep over the 169 surfaces any OOM as a process failure on a specific APK; record it.
  3. **(Contingency)** If a specific APK OOMs, it is a *per-APK* failure isolated to that APK; the change still recovers the others. Document the OOM APK; do NOT respond by adding pruning/approximation (RISK-006). If OOM is widespread, the fix is reconsidered (escalate), not patched with a result-altering shortcut.
- **Indicators**: `OutOfMemoryError` / process death on a large APK during the 4.1 sweep (RED for that APK — record, isolate); heap-time near the JVM `-Xmx` ceiling on the largest graphs (YELLOW).
- **Status**: Open (bounded by D1 design choice; surfaced by the sweep).

### RISK-003: Validating against a stale (never-rebuilt) JAR
- **Category**: Tools / Technology (build process discipline — inherited from gh66 RISK-001)
- **Description**: `lib/gator/rvsec-gator.jar` is gitignored by design (Finding 1). If validation runs against a JAR not rebuilt after the source edit, the corpus diff-zero passes deceptively — a stale JAR reproduces the baseline byte-for-byte (the baseline *was* the old JAR), so diff-zero cannot distinguish "new code, correct" from "old code, never recompiled". For gh70 the additional twist: the in-process JUnit test (4.A1) compiles fresh from source under `mvn`, so it would pass on the corrected code even if the *shipped* JAR is stale — the unit test proves the *source* is correct but **not** that the corpus sweep ran the corrected JAR.
- **Probability**: **Low** (10–25%) — the Maven `install` plugin auto-copies; no hand-copy step to forget. The hazard is "ran the sweep without rebuilding first".
- **Effect**: **Moderate** — a "completed" change ships no behavioral change and the recovery never materializes; caught by the jstack re-probe and `javap` symbol check.
- **Risk Level**: **Low** — *Risk Projection*: Low × Moderate.
- **Mitigation Strategy**: Minimization.
- **Actions**:
  1. **(Behavioral proof — task 4.3)** jstack re-probe on a still-timing-out APK after rebuild: a stale JAR still shows `GraphUtil.findReachableNodes`/per-alloc reachability dominating `main`; the corrected JAR does not. Mandatory gate.
  2. **(Symbol proof — task 3.3)** `javap` the new `computeSharedForwardReachability` symbol present in the shipped `lib/gator/rvsec-gator.jar`; record build timestamp + JDK.
  3. Rebuild via Maven (triggers the plugin copy) immediately before the sweep, in one session; do not reuse a pre-existing JAR.
- **Indicators**: jstack still hot on `findReachableNodes` post-fix (RED — stale JAR, rebuild); `javap` shows no `computeSharedForwardReachability` symbol (RED); JAR mtime older than the Java edit (YELLOW).
- **Status**: Open (gated at 4.3 + 3.3).

### RISK-004: Recovery is marginal — a third bottleneck (WTG stages 1..5) dominates
- **Category**: Technology / Estimation (effectiveness)
- **Description**: The diagnosis localizes the *current* dominant cost to the per-alloc `reachableNodes` closure. If, after sharing it, the wall-clock is dominated by `WTGBuilder.build`'s own stages (1..5) rather than `buildFlowThroughContainer`, the recovery (task 4.2) stays low — few of the 96 timeouts cross below the threshold. gh66's Fix 1 already showed this pattern (net recovery ≈ +1 because the *next* bottleneck dominated). Fix 2 attacks the named next bottleneck, but there may be a fourth.
- **Probability**: **Moderate** (25–50%) — the 96 are heterogeneous; the jstack that motivated Fix 2 is from a sample, and WTG stages are non-trivial.
- **Effect**: **Tolerable** — *not a correctness or schedule failure*. Consumers (aperv `scoreWtg`, rv-agent navigation) degrade cleanly on empty `transitions[]`; the 72 stay valid; the change is purely additive. Worst case: recovery is small and a Fix 3 (WTG stages) becomes a follow-up.
- **Risk Level**: **Medium** — *Risk Projection*: Moderate × Tolerable. Governs *value delivered*, not correctness.
- **Mitigation Strategy**: Minimization + Contingency (accepted-by-design, mirroring gh66's "measure first").
- **Actions**:
  1. **(Measure, not gate — task 4.2)** Count `tr>0` under gh70 minus baseline 72; record in `REPORT-validation.md`. Any positive recovery is success for *this* change.
  2. **(Scope the follow-up — task 4.3)** jstack re-probe: if `main` is now dominated by `WTGBuilder.build` stages, that empirically scopes a Fix 3. Record it; do NOT fold Fix 3 into gh70 (RISK-006).
  3. **(Contingency)** If recovery ≈ 0, the change is still a correct, safe optimization (diff-zero holds) — close it as "shared reachability landed; next bottleneck is X" and open Fix 3 separately.
- **Indicators**: recovery count near 0 (YELLOW — Fix 3 likely needed); jstack now hot on `WTGBuilder.build`/WTG stages (informational — confirms the next target).
- **Status**: Open (accepted-by-design; outcome measured, not gated).

### RISK-005: gator JAR rebuild collides with the active #69 source (source-vs-JAR discipline)
- **Category**: Tools / Requirements (coordination)
- **Description**: #69 (`gh69-generic-subtype-target-matching`, active, 0/24) touches `TargetResolver`/`UsedJcaMethodsVisitor` in the **same** `rvsec-gator` Maven module. The Java files are disjoint from gh70's (`FlowgraphRebuilder`/`GraphUtil`), so there is no merge conflict. But both changes rebuild **one shared JAR** (`lib/gator/rvsec-gator.jar`). If gh70 rebuilds from a tree that does not include #69's committed source (or vice versa), the shipped JAR carries only one fix — and the *other* change's validation, run later against that JAR, measures the wrong binary.
- **Probability**: **Low** (10–25%) — both are active and the discipline is documented; the hazard is rebuilding from a stale local tree.
- **Effect**: **Tolerable** — caught when the second change re-runs its own validation against a JAR missing its source; fixed by rebuilding from current HEAD.
- **Risk Level**: **Low** — *Risk Projection*: Low × Tolerable.
- **Mitigation Strategy**: Minimization.
- **Actions**:
  1. **(task 3.1)** Rebuild from the current monorepo HEAD, not a stale checkout: `cd rvsec/rvsec-android/rvsec-gator && mvn clean install -DskipTests -pl sootandroid,client -am`. If #69's source is already committed, this build includes it automatically (same module).
  2. **(task 3.3 / 4.3)** The `javap` symbol check confirms gh70's `computeSharedForwardReachability` is present; if #69 has landed, its symbols are present too — a quick `javap` cross-check confirms both fixes coexist in the shipped JAR.
  3. Keep Soot 4.7.1 (INV-ANA-18); do not bump as part of this change.
- **Indicators**: shipped JAR missing the other active change's symbols when both are merged (RED — rebuild from HEAD); a #69/#70 validation run against a JAR built before the other's commit (YELLOW — re-run after the joint rebuild).
- **Status**: Open (coordinate at JAR rebuild — task 3.1).

### RISK-006: Scope creep — pruning / depth-limiting / WTG-stage rewrite smuggled in
- **Category**: Requirements (scope discipline — inherited from gh66 RISK-006)
- **Description**: Two temptations. (a) Having localized the *next* bottleneck (RISK-004, the WTG stages), "while I'm in here" rewrite `WTGBuilder.build` too — a delicate, result-sensitive change that belongs in its own change. (b) Make WTG "faster" by pruning, depth-limiting, or approximating reachability — **forbidden**, because any such change *alters the WTG result*, breaking INV-ANA-45 and invalidating the diff-zero gate's meaning. The SCC sharing is allowed precisely because it is exact; an approximate variant is not.
- **Probability**: **Moderate** (25–50%) — the asymptotic payoff of approximation is tempting on the still-timing-out APKs, and the next bottleneck is adjacent code.
- **Effect**: **Serious** — a result-altering change masquerading as a perf fix. Pruning that changes the 72 would *fail* diff-zero (good, caught), but an approximation tuned to pass on the 72 could ship divergence on the 96 where there is no baseline.
- **Risk Level**: **Medium** — *Risk Projection*: Moderate × Serious.
- **Mitigation Strategy**: Avoidance (binding non-goals + review gate).
- **Actions**:
  1. **(Non-goals binding)** design.md Non-Goals forbid any pruning/depth-limiting/approximation and any WTG-stage edit. The helper is *exact-set-equal* to `reachableNodes` by contract.
  2. **(task 2.4 negative checkpoint)** Confirm the diff touches only `FlowgraphRebuilder` (the new helper + the call-site swap) and does NOT edit `GraphUtil.reachableNodes`/`findReachableNodes` or any WTG stage. Code review (5.1) verifies.
  3. **(Contingency)** If a WTG-stage fix is warranted post-measurement (RISK-004), it is a **separate change** with its own validation — never folded into gh70.
- **Indicators**: diff adds any depth limit / pruning / sampling (RED — block); diff edits `WTGBuilder.build` stages or `GraphUtil.reachableNodes`/`findReachableNodes` (RED — block at review).
- **Status**: Open (gated at review).

### RISK-007: NFR04 timeout-degradation path inadvertently altered
- **Category**: Technology (resilience contract — inherited from gh66 RISK-008)
- **Description**: NFR04 requires that on timeout the write-first partial JSON still carries `reachability` + `windows` + `components` with `transitions[]` empty. The fix is inside `buildFlowThroughContainer` (a `preBuild` pass before the WTG stages) and does not touch the partial-JSON/timeout machinery, but a careless edit (e.g. throwing on a missing SCC entry, or restructuring control flow so an exception escapes the pass) could perturb the degradation path.
- **Probability**: **Very Low** (<10%) — the helper is a pure read-only computation (design postcondition: no node created/mutated, no exception thrown); the timeout/write-first machinery is elsewhere.
- **Effect**: **Serious** *if it occurred* — the clean-degradation guarantee consumers rely on (`scoreWtg→0`) would break.
- **Risk Level**: **Low** — *Risk Projection*: Very Low × Serious.
- **Mitigation Strategy**: Avoidance (regression check).
- **Actions**:
  1. **(task 4.4)** On an APK that still times out, confirm partial JSON keeps `reachability` + `windows` + `components` with `transitions[]` empty.
  2. The helper must be exception-free (design API postcondition: "Error: none; pure computation"); never add a throw on a cache/SCC miss — return the computed set.
- **Indicators**: a still-timing-out APK loses `reachability`/`windows`/`components` from its partial JSON (RED — block).
- **Status**: Open (gated at 4.4).

---

## Monitoring Schedule

- **Review cadence**: at each task-group boundary in `tasks.md` (after Group 2 Java edit, after Group 3 JAR build, after Group 4 validation). Small, short-lived change — no recurring calendar review.
- **Hard gates before "done"** (all must be GREEN):
  1. **RISK-001 (PRIMARY)**: in-process JUnit set-equality (task 4.A1) GREEN — `helper.get(n) == reachableNodes(n)` for every node on cycle + `NOpNode`-successor + `NOpNode`-start + diamond fixtures. **This is the control for the 96 recovered APKs, which have no `transitions` baseline.**
  2. **RISK-001 backstop**: full-corpus `transitions` strict diff-zero on the 72 baseline-`tr>0` APKs (task 4.1) — zero added/removed edges; INV-ANA-45/INV-ANA-39.
  3. **RISK-001 IT**: `BaselineComparisonIT` edge-set diff-zero on cryptoapp with the gh70 JAR (task 4.A2); full gator suite green (`mvn verify`).
  4. **RISK-003**: jstack re-probe (task 4.3) confirms the hot spot moved off `GraphUtil.findReachableNodes` — **the behavioral proof the new JAR shipped** — AND `javap` shows the `computeSharedForwardReachability` symbol (task 3.3).
  5. **RISK-006**: code review (task 5.1) confirms diff touches only the helper + call-site swap; `GraphUtil.reachableNodes`/`findReachableNodes` and WTG stages untouched.
  6. **RISK-007**: NFR04 partial-JSON regression check (task 4.4).
  7. **RISK-002 / RISK-005**: clean rebuild-from-committed-HEAD reproduces a diff-zero-passing JAR (task 4.5); no OOM on the 169 sweep (or OOM isolated + documented, not patched with approximation).
- **Measured, not gated**: RISK-004 recovery count (task 4.2) — records value delivered; informs the Fix 3 (WTG-stage) follow-up decision.
- **Next review**: at Group 2 completion (Java edit landed).

## Change Log

| Date | Risk | Change |
|------|------|--------|
| 2026-06-18 | — | Register created (task 1.1). Inherits gh66's verified topology (single monorepo, one commit; gitignored Maven JAR — RISK-003/RISK-005) and reweights correctness upward for the algorithmic SCC reformulation. |
| 2026-06-18 | RISK-001 | Rated **High** (the one High). *Risk Projection*: Moderate × Serious, elevated because the relaxed invariance gate (gh66 d09002b9) leaves `transitions` diff-zero as the only strict edge signal AND the most likely failure surface (the 96 recovered APKs) has no baseline — so the in-process JUnit set-equality test (4.A1) is the **primary** correctness gate, not a redundancy. Verified the `NOpNode` start-vs-successor asymmetry at `GraphUtil.findReachableNodes` lines 42–61 and the existence of differently-behaving backward variants (wrong-rule hazard). |
| 2026-06-18 | RISK-002 | Added (no gh66 analog): the SCC approach is the deliberate D1 alternative to a full `V×V` closure to *avoid* OOM, but per-SCC reachable-set storage can still approach `O(V²)` on near-complete condensations of the largest (= timing-out) graphs. Bounded by D1, surfaced by the 4.1 sweep, contingency = isolate the APK (no approximation). |
