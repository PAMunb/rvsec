<!-- ════════════════════════════════════════════════════════════════════════════════
     OUTCOME (2026-06-18): NÃO-VIÁVEL — REVERTIDO. Ver REPORT-validation.md.
     O approach (pré-computar reachability UMA vez) é semanticamente inválido:
     buildFlowThroughContainer MUTA o grafo durante o passo (addEdgeTo no laço), e a
     reachability de cada alloc node precisa ver as arestas das iterações anteriores.
     Snapshot estático → transitions=0 em 19/20 APKs baseline-tr>0 (Fossify/messengers).
     Prova: gh66 (reachability viva)==baseline; gh70 (snapshot)==0; helper provado correto
     em grafo estático (teste aleatório passa). Código revertido ao estado gh66; JAR
     rebuildado (helper ausente via javap); INV-ANA-45 NÃO sincronizada. Os [x] abaixo
     refletem trabalho feito-e-depois-revertido, não um fix entregue.
     ════════════════════════════════════════════════════════════════════════════════ -->

<!-- Scope: 1 GATOR method (FlowgraphRebuilder.buildFlowThroughContainer) + 1 new private helper
     (shared reachability) in rvsec-android/rvsec-gator, + JAR rebuild + validation. Single PAMunb/rvsec
     monorepo (rv-android and GATOR share git root) — single commit. Follow-up to #66 (Fix 2).
     Critical path: 2 (implement shared reachability) -> 3 (build JAR) -> 4.A (JUnit set-equality + edge-set IT)
     -> 4.B (corpus diff-zero gate, then recovery) -> 5 (review/close).
     NOTE: /rv-test-run, /rv-qa-lint-fix, /rv-verify target Python and do NOT apply (zero Python source).
     Validation is layered: in-process JUnit set-equality (the cheap correctness proof for the NOpNode/cycle
     edge cases the corpus cannot isolate) AND full-corpus diff-zero (INV-ANA-45 / INV-ANA-39 hold) BEFORE
     any recovery is claimed. Coordinate the gator JAR rebuild with the active #69 (source-vs-JAR discipline). -->

## 1. Design Records (Phase 3 completion)

- [x] 1.1 Risk register — run `/rv-risk gh70-wtg-reachability-sharing`. Capture: SCC-reachability correctness vs `reachableNodes` (incl. NOpNode), SCC memory on large graphs (OOM-vs-timeout trade), rebuild/source-vs-JAR discipline, coordination with #69's gator JAR. Output: `risk-register.md`.
- [x] 1.2 ADR: NOT required — gh70 operates under gh66's ADR-001 (the "do not touch GATOR" rule was already relaxed for semantics-preserving perf fixes). Record an ADR only if the SCC-condensation introduces a structural decision worth a standalone record (decide during implementation; default: no new ADR).

## 2. GATOR Optimization — `rvsec` repo (Java)

File: `rvsec/rvsec-android/rvsec-gator/sootandroid/src/main/java/presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java` (method `buildFlowThroughContainer`, the `graphUtil.reachableNodes(...)` call inside the `for (Expr e : allNAllocNodes.keySet())` loop). Reference: `GraphUtil.reachableNodes`/`findReachableNodes` in `presto/android/gui/GraphUtil.java`.

- [x] 2.1 Add a private helper `computeSharedForwardReachability(...)` (in `FlowgraphRebuilder` or a package-private helper it owns) that computes, once, the forward-reachable set for every allocation node via **SCC condensation + reverse-topological reachable-set propagation** over the condensation DAG (D1). Read-only over the successor relation; creates/mutates NO flow-graph nodes.
- [x] 2.2 Replicate the `NOpNode` rule exactly (D3): an `NOpNode` successor is **included** in a reachable set but **not expanded** (its successors do not propagate through it) — treat `NOpNode`s as sink-like for propagation. This is the diff-zero-critical detail.
- [x] 2.3 Replace the per-allocation `graphUtil.reachableNodes(flowgraph.allNAllocNodes.get(e))` call with a lookup into the precomputed map (computed once before the outer loop). The downstream `reads`/`writes` derivation, gh66's cached field resolution, and the edge-add loop are UNCHANGED.
- [x] 2.4 Do NOT modify the public `GraphUtil.reachableNodes`/`findReachableNodes` (D2, INV-ANA-45c) — other callers must be byte-for-byte unaffected. Confirm via grep that no other call site changed.
- [x] 2.5 Keep the existing `instanceof RefType` / null guards and the `varsAtContainerRead`/`varsAtContainerWrite` lookups identical (only the reachability source changes).

## 3. Build & JAR Synchronization (Maven module -> `lib/gator`, same repo)

- [x] 3.1 Rebuild the GATOR JAR from corrected source, from the monorepo root, pinned command (same as gh66):
  ```bash
  cd rvsec/rvsec-android/rvsec-gator && mvn clean install -DskipTests -pl sootandroid,client -am
  ```
  `install` triggers the `maven-resources-plugin` copy into `rv-android/lib/gator/` (overwrite=true). Keep Soot 4.7.1 (INV-ANA-18). **Coordinate with #69**: if #69's `TargetResolver`/extractor source is committed, this rebuild must include it (source-vs-JAR discipline) — rebuild from the current monorepo HEAD, not a stale tree.
- [x] 3.2 Refresh `rv-android/lib/gator/rvsec-gator.jar` (and `rvsec-analysis-client.jar` if regenerated) from the freshly built artifact.
- [x] 3.3 Verify the shipped JAR matches the committed source — `javap` the new helper symbol present in `lib/gator/rvsec-gator.jar`; record the build timestamp + JDK (bytecode target pinned to 21 in parent pom → reproducible across JDK 21/25, as established in gh66 §3.3).

## 4. Validation & Tests (JUnit set-equality + empirical diff-zero gate)

### 4.A Automated tests — `rvsec-gator` JUnit/IT (`mvn verify`)

- [x] 4.A1 **Set-equality unit test** (`FlowgraphReachabilityShareTest` in `sootandroid/src/test/...`): build small in-process flow-graph fixtures — (i) a cycle, (ii) a node with an `NOpNode` successor, (iii) a diamond — and assert the shared helper returns sets **equal** to `GraphUtil.reachableNodes(n)` for every node. The NOpNode fixture (include-but-don't-expand) is the key case (INV-ANA-45a/D3). Green under `mvn -pl sootandroid test`.
- [x] 4.A2 **Edge-set regression IT** — re-run `BaselineComparisonIT` (`testTransitionEdgeSetExact`, RVSEC_HOME-gated, cryptoapp) and confirm **diff-zero** still holds with the gh70 JAR. Full gator suite green (`mvn verify`: sootandroid + client unit + client IT).

### 4.B Empirical full-corpus gates (real-APK protocol)

- [ ] 4.1 **Full-invariance gate (PRIMARY)**: run the gh70 JAR over the 169 (`scripts/static_analysis_sweep.py`, spark + cgDelegation, mirror baseline config, never `--skip-wtg`/`--succ-depth`) into a fresh output dir and compare to `out/sweep_20260604_wtg_spark` with `scripts/wtg_sweep_invariance.py` — require invariants identical (windows/components by structural identity, reachability/package/mainActivity strict) AND `transitions` diff-zero on every baseline-`tr>0` APK (INV-ANA-45 / INV-ANA-39). ANY removed/added edge on a baseline-`tr>0` APK fails the change. NOTE the gh66 resume caveat: a WTG timeout writes `transitions:[]` → status `complete` → resume skips it; to re-measure timeouts at the staged timeout, run them into a fresh output dir or force-reprocess (do NOT rely on resume to retry `complete`-tr0 APKs).
- [ ] 4.2 **Recovery measurement**: count APKs with `transitions>0` under gh70 minus baseline 72 — the §4.2 number (how many of the 96 timeouts gh70 recovers). Record in `REPORT-validation.md`. Compare against gh66's net ≈ +1 to quantify Fix 2's benefit.
- [ ] 4.3 **jstack re-probe**: re-run `scripts/jstack_wtg_probe.sh` on an APK that still times out and confirm the `main` thread is no longer dominated by `GraphUtil.findReachableNodes`/reachability traversal (the behavioral proof the shared-reachability JAR is running). If a fourth bottleneck appears (e.g. `WTGBuilder.build` stages), record it (informs follow-up).
- [ ] 4.4 **NFR04 regression**: on an APK that still times out, confirm the partial JSON keeps `reachability` + `windows` + `components` populated with `transitions[]` empty (write-first degradation unchanged).
- [ ] 4.5 **Clean-rebuild reproducibility**: from committed source, clean `mvn clean install` (§3.1) and confirm the resulting JAR passes the 4.1 diff-zero.

## 5. Review, Docs & Close

- [x] 5.1 `/rv-code-reviewer` on the GATOR Java diff (args: verify (1) shared reachability returns sets identical to `reachableNodes` incl. NOpNode include-but-don't-expand; (2) public `GraphUtil.reachableNodes`/`findReachableNodes` untouched; (3) no flow-graph node created/mutated by the helper; (4) cycles terminate; (5) gh66 field-resolution path unchanged).
- [ ] 5.2 `/rv-docs-sync` — update CLAUDE.md "Current Work" WTG note (Fix 2 landed; record the recovery number).
- [ ] 5.3 Update `tasks.md` checkboxes and record the recovery number (4.2) in `REPORT-validation.md`.
- [ ] 5.4 Commit (Java source + OpenSpec artifacts + docs; JAR gitignored) with `closes #70`; move the Kanban card. Coordinate spec sync with the active #69/#57 Analysis deltas (gh70 = INV-ANA-45, disjoint).
