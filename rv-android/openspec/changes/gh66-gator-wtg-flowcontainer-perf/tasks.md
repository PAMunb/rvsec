<!-- Scope: 1 Java method (FlowgraphRebuilder.buildFlowThroughContainer) in rvsec-android/rvsec-gator
     + JAR rebuild + ADR/risk/docs. All inside the one PAMunb/rvsec monorepo (rv-android and the GATOR
     tree share git root) — single commit. Small file count — NO subagent orchestration needed.
     Critical path: 2 (optimize + unit test) -> 3 (build JAR) -> 4.A (automated JUnit/IT) -> 4.B (empirical gates:
     diff-zero on 72 + guard differential + jstack + NFR04 + clean rebuild) -> 5 (review).
     NOTE: /rv-test-run, /rv-qa-lint-fix, /rv-verify target Python modules and do NOT apply — this change
     touches zero rv-android Python source. Validation is layered (NO single sole gate): automated JUnit/IT in
     rvsec-gator (purity unit test 4.A1 + edge-set regression IT 4.A2) AND empirical full-corpus gates. The
     guard differential (4.1b) is what proves correctness on the 97 recovered APKs (no baseline to diff), and
     the jstack re-probe (4.3) proves the freshly-built JAR shipped (the JAR is a gitignored build artifact,
     so diff-zero alone cannot detect a stale/never-rebuilt JAR). -->

## 1. Design Records (Phase 3 completion)

- [x] 1.1 Create ADR recording the decision to relax the "do not touch GATOR" rule for semantics-preserving performance fixes — run `/rv-doc-adr` (decision D1 in design.md). Output: `modules/rv-static-analysis/docs/adr/ADR-001-relax-gator-no-touch-rule-for-semantics-preserving-perf-fixes.md` (status Proposed).
- [x] 1.2 Create the risk register (rebuild/validate discipline, external Java tooling, source-vs-JAR consistency; single monorepo) — run `/rv-risk gh66-gator-wtg-flowcontainer-perf`. Output: `risk-register.md`.

## 2. GATOR Optimization — `rvsec` repo (Java)

File: `rvsec/rvsec-android/rvsec-gator/sootandroid/src/main/java/presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java` (method `buildFlowThroughContainer`, lines 311-369).

- [ ] 2.1 Declare two method-local caches `Map<Stmt,Integer> readFieldCache`, `Map<Stmt,Integer> writeFieldCache` before the outer `for (Expr e : allNAllocNodes.keySet())` loop (decision D4).
- [ ] 2.2 Add private helpers `cachedReadContainerField(Stmt)` / `cachedWriteContainerField(Stmt)` using the `containsKey`-null pattern (NOT `computeIfAbsent`, which would not cache null returns) (D4, INV-ANA-39 purity).
- [ ] 2.3 Hoist the read resolution with a **guard against node-creation side effects** (D3, point 2): build `List<NNode> readTargets` of the non-null target nodes `tn` once per alloc node (resolve `tgtPos` via `cachedReadContainerField`, compute `tn` exactly as the current inner block does, skip `tgtPos==null` / `tn==null` identically), but materialize it **lazily** — only on the first write that resolves to a non-null `sn`. Do NOT build `readTargets` (and therefore do NOT call `simpleNode`/`varNode` for the reads) for an alloc node whose writes all fail to resolve, because those factories (`FlowgraphRebuilder.java:794-839`) lazily create+register flow-graph nodes; the original never reaches the read loop in that case, so an unguarded precompute would create nodes the unoptimized pass does not (INV-ANA-39c). Hoists `R` not `W×R` resolutions.
- [ ] 2.4 Rewrite the inner loop body to `for (NNode tn : readTargets) sn.addEdgeTo(tn);` — same edge set, no per-pair re-resolution; the surrounding write loop still does `resolve sn (cached) → skip if null → (lazy-build readTargets) → add edges` so the `if (sn==null) continue;` guard still gates whether any read-target work happens (D3).
- [ ] 2.5 Replace the `wtgUtil.getWriteContainerField(src)` call at line 334 with `cachedWriteContainerField(src)` (D4 memoization across alloc nodes).
- [ ] 2.6 Confirm the per-alloc `graphUtil.reachableNodes()` call (line 319) is left untouched (Non-Goal / Fix 2 deferred).
- [ ] 2.6a Code-review checkpoint for the guard (RISK-004): confirm `simpleNode`/`varNode` are never invoked for an alloc node before a non-null `sn` is found, so no read-target node is created when the alloc node adds no edge (INV-ANA-39c). This cannot be caught by the diff-zero gate (the 97 timeout APKs have no baseline), so it is a review gate, not a validation gate.
- [ ] 2.7 **Add the purity unit test (mandatory — the test tree exists).** In `rvsec/rvsec-android/rvsec-gator/sootandroid/src/test/java/presto/android/...`, assert `cachedReadContainerField(s) == wtgUtil.getReadContainerField(s)` and the write variant for representative statements **including the `null` (non-container) case**, proving the `containsKey`-null memoization equals fresh resolution. Statically confirm the diff contains no `computeIfAbsent`. (rvsec-gator has 21 JUnit/IT tests, JUnit 4.12 + surefire/failsafe — the earlier "if a test tree exists" caveat is void.)

## 3. Build & JAR Synchronization (Maven module -> `lib/gator`, same repo)

- [ ] 3.1 Rebuild the GATOR JAR from the corrected source with the **pinned** command (RISK-002/RISK-005), run from the monorepo root `/.../workspace-rv/rvsec`:

  ```bash
  cd rvsec/rvsec-android/rvsec-gator && mvn clean install -DskipTests -pl sootandroid,client -am
  ```

  - The `install` phase is required: it triggers the `maven-resources-plugin` `copy-resource-one` execution declared in `rvsec/rvsec-android/rvsec-gator/pom.xml`, which copies the built JAR into `rv-android/lib/gator/` with `overwrite=true` (so step 3.2 is automatic, not a hand-copy). A `package`-only build will NOT refresh `lib/gator`.
  - Do NOT bump Soot — keep Soot 4.7.1 (INV-ANA-18); use the same JDK/Maven as the 2026-06-13 reference build that produced the current JAR.
  - Optional isolation check (RISK-005): build once with **no source change** first and confirm the resulting JAR still passes the 72-APK diff-zero, to separate "build env changed" from "my edit changed behavior".
- [ ] 3.2 Refresh `rv-android/lib/gator/rvsec-gator.jar` (and `rvsec-analysis-client.jar` if the build regenerates it) from the freshly built artifact (same source-vs-JAR discipline as `e584894a`).
- [ ] 3.3 Verify the shipped JAR matches the committed source (no drift) — record the build timestamp.

## 4. Validation & Tests (automated JUnit/IT + empirical full-corpus gates)

Rigorous, layered validation — **all gates below must pass; no single layer is the sole gate.** Automated tests (4.A) run in CI on every build; the empirical gates (4.B) prove the contract on the real corpus.

### 4.A Automated tests — `rvsec-gator` JUnit/IT (`mvn verify`)

- [ ] 4.A1 Purity unit test — authored in task 2.7 (cached resolver == fresh resolution incl. `null`; no `computeIfAbsent`). Confirm it runs green under `mvn -pl sootandroid test`.
- [ ] 4.A2 **Edge-set regression IT (mandatory).** Extend `BaselineComparisonIT` (`client/src/test/.../BaselineComparisonIT.java`, `RVSEC_HOME`-gated) so it compares the `transitions[]` **edge set** — keyed on the stable 5-field tuple (source window name, target window name, event type, widget name, handler signature), resolving numeric IDs via `windows[]`/`widgets[]` — against the `cryptoapp` baseline, **not only** `transitions.size()` (the current `testTransitionCountExact`). This automates the diff-zero contract as a CI regression on a real APK. If the stored `cryptoapp_baseline.json` lacks the per-edge detail, capture it once from the current pre-change JAR and commit it as the baseline resource.

### 4.B Empirical full-corpus gates (real-APK protocol)

- [ ] 4.1a **Provide the exact diff-zero comparator** (no existing script does this faithfully — `scripts/wtg_paridade_diff.py` is a Jaccard/threshold comparator keyed on the 3-tuple `(sourceId, targetId, event_type)` of raw numeric IDs, which omits widget/handler identity and tolerates divergence). Write/extend a comparator that, per APK, keys each `transitions[]` edge on the **stable** tuple (`source window name`, `target window name`, and per event `event type`, `widget name`, `handler signature`) — resolving numeric `sourceId`/`targetId`/`widgetId` to names via the same JSON's `windows[]`/`widgets[]` first, since GATOR node IDs are not stable across builds — and asserts **set equality** (zero added, zero removed edges). Scope the baseline to the canonical per-APK JSONs `out/sweep_20260604_wtg_spark/<app>/<app>.apk.json`, **excluding** `out/sweep_20260604_wtg_spark/_backup/`. (Optionally run `wtg_paridade_diff.py --threshold-avg 1.0 --threshold-min 1.0` as a coarse pre-check, but the exact comparator is the gate.) Reuse the same edge-keying logic as 4.A2 so the IT and the corpus gate agree.
- [ ] 4.1 **Diff-zero on the 72 baseline**: run the corrected JAR over the 72 APKs that already produce `transitions>0` and run the 4.1a comparator vs `out/sweep_20260604_wtg_spark` (canonical JSONs, `_backup/` excluded). ANY added or removed edge fails the change (INV-ANA-39). This gate covers only the 72 with a baseline; the guard differential (4.1b) — not this gate — is what protects the 97 recovered APKs, which have no baseline to diff.
- [ ] 4.1b **Guard differential (B1 / INV-ANA-39c) — the proof for the un-baselined case.** Build the current pre-change JAR and the corrected JAR each with a **throwaway** debug counter in `buildFlowThroughContainer` reporting (i) alloc nodes processed, (ii) alloc nodes with `reads≠∅` but no resolvable write (the divergence-prone case), (iii) `flowgraph.allNNodes` size before/after the pass. Run both on a sample of the 72 **and** several of the 97 and assert: the corrected pass's `allNNodes` delta equals the original's (the guard creates **no** extra nodes), **AND** counter (ii) > 0 on ≥1 APK (the guard path is actually exercised, not vacuously satisfied). Revert the debug counter before commit (P3). This empirically closes the one hazard the 72-diff-zero cannot see.
- [ ] 4.2 **Recovery on the 97 timeouts**: run the corrected JAR over the 97 timeout APKs (`scripts/static_analysis_sweep.py`, spark + cgDelegation) and count how many now emit `transitions>0`. Record the number (design D5; informs the Fix 2 follow-up decision).
- [ ] 4.3 **jstack re-probe (MANDATORY gate, RISK-001)**: re-run `scripts/jstack_wtg_probe.sh` on `ch.famoser.mensa` and confirm the `main` thread is no longer dominated by `getReadContainerField`/`SootMethodRefImpl.resolve`. This is the behavioral proof the freshly-built JAR (not a stale one) is running — diff-zero alone cannot detect a never-rebuilt JAR.
- [ ] 4.4 **NFR04 regression**: on an APK that still times out, confirm the partial JSON keeps `reachability` + `windows` + `components` populated with `transitions[]` empty (write-first degradation unchanged).
- [ ] 4.5 **Clean-rebuild reproducibility (RISK-002)**: from the committed source, do a clean `mvn clean install` (§3.1) and confirm the resulting JAR passes the 4.1 diff-zero — proving a fresh clone reproduces the validated artifact.

## 5. Review, Docs & Close

- [ ] 5.1 Invoke `/rv-code-reviewer` via the Skill tool on the GATOR Java diff (args: "Review gh66-gator-wtg-flowcontainer-perf — FlowgraphRebuilder.buildFlowThroughContainer hoist + memoize; verify: (1) the read-target hoist is GUARDED — simpleNode/varNode never reached before a non-null sn, no node created when an alloc adds no edge (INV-ANA-39c); (2) memoization uses containsKey-null, never computeIfAbsent; (3) reachableNodes() line 319 untouched; (4) cached resolvers never throw").
- [ ] 5.2 Run `/rv-docs-sync` — update the CLAUDE.md "Current Work" WTG note and the relevant docs to record that the buildFlowThroughContainer perf fix landed (and the rule relaxation).
- [ ] 5.3 Update `tasks.md` checkboxes and record the recovery number (4.2) in the consolidated report `docs/20260613_relatorio_sweep_wtg_jca_169.md`.
- [ ] 5.4 Commit (Java source + OpenSpec artifacts + docs; the JAR is gitignored, not committed) with `closes #66`; move the Kanban card to Done (or In Review if submitted as PR).
