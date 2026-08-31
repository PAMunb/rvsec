# ADR-001: Relax the "do not touch GATOR" rule for semantics-preserving performance fixes

## Status

Proposed

## Date

2026-06-17

## Context

The Window Transition Graph (WTG) section of GATOR static analysis (FR04) is
timeout-bound rather than time-bound. In the `experimento-20260604` WTG sweep
(169 JCA APKs, SPARK call graph with `cgDelegation=true`), only **72/169 APKs**
produced `transitions>0`; the other **97 all timed out** during WTG
construction, and doubling the timeout (1800s → 3600s) rescued roughly 1 in 65.

A `jstack` probe (6 dumps on `ch.famoser.mensa_60`, a 2 MB app) showed the
`main` thread RUNNABLE on-CPU, single-threaded, inside
`FlowgraphRebuilder.buildFlowThroughContainer()`
(`rvsec` repo, `rvsec-android/rvsec-gator/sootandroid/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java:311-369`).
That pass runs in `preBuild` — before WTG stage 1 — and is
**O(allocNodes × flowgraph) quadratic**. The cost is real CPU work, not waiting:
more time does not help.

The standing project rule states "do not touch the GATOR original". The
diagnosis (`docs/20260613_wtg_timeout_buildflowthroughcontainer.md`) established
three facts that bear on whether that rule can hold here:

- **No native lever gates this pass.** `buildFlowThroughContainer` runs
  unconditionally; no GATOR `Configs` flag disables, bounds, or reshapes it.
- **A larger timeout is futile.** The cost is super-linear; the recovery rate of
  doubling the timeout (~1 in 65) confirms that time is not the bottleneck, work
  is.
- **`sDepth=3` was refuted.** Lowering the WTG search depth via the native flag
  recovered 0/24 APKs and would, in any case, change the WTG result — which is
  out of bounds.

The only remaining fix is a code change to GATOR. This forces a decision about
the standing rule: either the rule is absolute and the consumer accepts an
incomplete `transitions[]`, or the rule admits a narrow exception for changes
that demonstrably do not alter the analysis result.

This decision is the architectural precedent that enables Phase 4 implementation
of change `gh66-gator-wtg-flowcontainer-perf` (GitHub Issue #66). It corresponds
to design decision **D1**.

## Decision Drivers

- **Output fidelity over performance**: GATOR is treated as a fixed oracle
  precisely because its output is a contract consumed downstream (rv-agent
  navigation, aperv `scoreWtg`). Any rule relaxation must protect that contract
  absolutely — a faster pass that changes one edge is unacceptable.
- **Validability**: A relaxation is only safe if "did not change the result" is
  mechanically checkable, not argued. The 72 already-passing APKs in
  `out/sweep_20260604_wtg_spark` provide a byte-level ground truth for a
  diff-zero gate.
- **Consumer need for `transitions[]`**: The aperv consumer wants the WTG
  transitions. It degrades cleanly when they are absent (`scoreWtg→0`), but
  "degrades cleanly" is a fallback, not the desired state for a consumer that
  scores on them.
- **Source-vs-JAR discipline**: The shipped artifact `lib/gator/rvsec-gator.jar`
  must match the GATOR source tree. The arity fix `e584894a` established the
  rebuild discipline; any GATOR edit must follow it or the fix is silently lost
  on the next rebuild.
- **Precedent containment**: Relaxing a standing rule risks scope creep. The
  relaxation must be scoped so narrowly that it cannot be invoked to justify
  result-altering changes (pruning, depth limits, algorithm changes).

## Considered Options

### Option A: Accept the 72 and stop (keep the rule absolute)

**Description**: Treat the "do not touch GATOR" rule as inviolable. Ship the 72
APKs that already produce `transitions[]` and rely on the consumer's clean
degradation (`scoreWtg→0`) for the other 97.

**Pros**:
- Zero risk to the GATOR output contract — no GATOR code changes at all.
- No JAR rebuild, no source-vs-JAR consistency surface.
- Honors the standing rule without exception.

**Cons**:
- Leaves `transitions[]` permanently incomplete (97/169 absent) for a consumer
  that wants them; clean degradation is a fallback, not the intended state.
- Discards a low-risk, byte-for-byte validable fix that the diagnosis already
  identified.
- Does not resolve the underlying tension: any future WTG-completeness need hits
  the same wall.

### Option B: Increase the timeout

**Description**: Keep GATOR untouched and raise the per-analysis timeout to give
the quadratic pass more time to complete on the 97 APKs.

**Pros**:
- No GATOR code change; rule untouched.
- Trivial to configure.

**Cons**:
- Refuted empirically: doubling 1800s → 3600s rescued ~1 in 65. The cost is
  super-linear, so time is not the bottleneck.
- Inflates wall-clock for every analysis while recovering almost nothing.

### Option C: Lower WTG search depth via the native `sDepth=3` flag

**Description**: Use the existing GATOR `sDepth` configuration to reduce the
WTG search depth, shrinking the work without editing GATOR source.

**Pros**:
- Uses a native configuration lever; no source edit.

**Cons**:
- Refuted empirically: recovered 0/24 APKs.
- Would change the WTG result (fewer/shorter transitions) — a violation of the
  output-fidelity driver, independent of its ineffectiveness.

### Option D: Relax the rule for semantics-preserving performance fixes, then edit GATOR

**Description**: Narrow the standing rule to permit GATOR edits that are
**semantics-preserving** — i.e., produce a byte-identical WTG result — for the
sole purpose of reducing the constant factor of a hot pass. Under this relaxed
rule, rewrite `FlowgraphRebuilder.buildFlowThroughContainer()` with two moves:
hoist `getReadContainerField` resolution out of the inner writes loop, and
memoize `getRead/WriteContainerField` in a `Map<Stmt,Integer>` spanning the
outer allocation-node loop. Rebuild `lib/gator/rvsec-gator.jar` from the
corrected source, following the `e584894a` discipline. The rule continues to
forbid any change that alters the WTG result (pruning, depth limits, algorithm
changes). A mandatory diff-zero edge comparison on the 72 already-passing APKs
gates the change before any recovery measurement on the 97 timeouts.

**Pros**:
- Recovers tractability for some fraction of the 97 timeouts without altering
  the WTG result.
- The relaxation is mechanically bounded: the diff-zero gate makes "preserves
  semantics" a checkable precondition, not a claim.
- The two moves are edge-set-identical by construction: `getReadContainerField`
  is a pure function of the statement (memoization safe), and the hoist is
  **guarded** so the node-resolution factories (`simpleNode`/`varNode`, which
  lazily create flow-graph nodes) run only for allocation nodes that add an edge
  — reproducing the original's node-creation behavior, not just its edge set.
  The risk surface is the validation, exhaustive on the 72 baseline; the guard
  (a construction property, verified at code review) is what protects the 97
  recovered APKs, which have no baseline to diff.
- Establishes a reusable, narrowly-scoped precedent for future
  semantics-preserving GATOR perf fixes (e.g., the deferred Fix 2 on
  per-allocation reachability).

**Cons**:
- Opens the GATOR original to edits, introducing a Maven rebuild step (the
  `rvsec-gator` module builds the JAR and a Maven plugin copies it into
  `lib/gator/`, gitignored) and a source-vs-JAR consistency surface. All within
  the one `PAMunb/rvsec` monorepo, so a single commit covers the change.
- Carries residual risk if a resolver were not actually pure; mitigated, not
  eliminated, by the diff-zero gate.
- A relaxed rule must be policed so it is never stretched to cover
  result-altering changes.

## Decision

**Option D** — relax the standing "do not touch GATOR" rule specifically for
**semantics-preserving performance fixes that produce byte-identical WTG
output**, and under that relaxed rule edit
`FlowgraphRebuilder.buildFlowThroughContainer()` (hoist + memoize) and rebuild
`lib/gator/rvsec-gator.jar`.

The relaxation is bounded by three conditions that together make it safe and
non-expansive:

1. **Semantics-preserving only.** The change must produce an identical WTG edge
   set. The rule continues to forbid any change that alters the WTG result —
   pruning, depth limits (`sDepth`), or algorithm changes remain prohibited.
2. **Diff-zero gate.** Before any recovery measurement, the corrected JAR must
   reproduce byte-identical `transitions[]` edges on all 72 already-passing APKs
   (`out/sweep_20260604_wtg_spark`). A single divergent edge fails the change.
3. **Source-vs-JAR discipline.** `lib/gator/rvsec-gator.jar` is rebuilt from the
   committed GATOR source, mirroring the arity fix `e584894a`, so the shipped
   artifact matches the source tree.

Options A, B, and C are rejected: B and C are empirically refuted (timeout
super-linear; `sDepth=3` recovered 0/24 and would change the result), and A,
while safe, leaves `transitions[]` incomplete for a consumer that wants them
when a low-risk, byte-for-byte validable fix exists.

## Consequences

### Positive

- The project gains a narrow, well-defined exception that permits recovering
  GATOR tractability without compromising the output contract.
- `transitions[]` becomes available for some fraction of the 97 previously-timed-out
  APKs, improving WTG completeness for rv-agent navigation and aperv `scoreWtg`.
- The diff-zero gate institutionalizes "preserves semantics" as a checkable
  precondition, so future semantics-preserving GATOR perf fixes (e.g., deferred
  Fix 2) have a clear, reusable bar to clear.
- The change is additive to the delivered dataset: a recovery run only *adds*
  `transitions[]` to APKs that had none; it never rewrites the 72 baseline, so
  there is no regression surface on already-shipped results.

### Negative

- GATOR edits now require a Maven rebuild (Java source + `rvsec-gator` build,
  Maven plugin copies the JAR into `lib/gator/`) and introduce a source-vs-JAR
  consistency surface that must be guarded by the rebuild discipline (the JAR is
  a gitignored build artifact; diff-zero cannot detect a stale one — the jstack
  re-probe does).
- The relaxed rule must be actively policed: it is valid only for
  semantics-preserving changes and must never be stretched to justify
  result-altering edits.
- Residual risk remains if a resolver assumed pure were not — mitigated by the
  exhaustive diff-zero gate, but not eliminated in principle.

### Neutral

- No rv-android Python source changes; the tooling already invokes the GATOR
  JAR, only the artifact is refreshed.
- The timeout-degradation path (write-first partial JSON, NFR04) is unchanged: a
  still-timing-out APK persists reachability + windows + components with an empty
  `transitions[]`.
- A side effect of hoisting is a verbose-level log volume reduction (the
  "read container stmt can not be found" message is emitted once per unresolved
  read instead of once per write × read pair) — a log change, not an edge change.

## Implementation Notes

- The relaxation authorizes **Fix 1 only** (read-side hoist + memoize), which is
  edge-set-identical by construction. The read-target hoist is **guarded**
  (read-target nodes materialized lazily, only once a write resolves to a
  non-null writer node) because `simpleNode`/`varNode` lazily create flow-graph
  nodes; an unguarded hoist would create nodes the unoptimized pass does not, a
  divergence the diff-zero gate cannot catch on the recovered APKs. The
  per-allocation forward-reachability closure `GraphUtil.reachableNodes()`
  (line 319, "Fix 2") is deferred to a follow-up change and is *not* covered by
  this decision until it too is validated semantics-preserving.
- Memoization uses an explicit `containsKey` pattern rather than
  `computeIfAbsent`, because both resolvers can legitimately return `null`
  (statement is not a container op); `computeIfAbsent` would not cache null and
  would re-resolve every null. The caches are method-local, declared before the
  outer allocation-node loop so they span it (the recurrence being exploited).
- Validation protocol mirrors the arity fix `e584894a`: diff-zero on the 72,
  then count `transitions>0` completions on the 97, then re-run
  `scripts/jstack_wtg_probe.sh` on `ch.famoser.mensa` to confirm the hot spot
  moved off `getReadContainerField`.

## Scope note (2026-08-30)

This ADR relaxes the no-touch rule for **semantics-preserving performance**
fixes only. It is not the authority for the GATOR edits made under gh111
(`AnalysisEntrypoint`, `RvsecAnalysisClient`, `JsonReportWriter`,
`JsonSchema`, `ReachabilityEnricher`), which deliberately **change** what the
client writes: the demotion guard resolves its package from the `codePackage`
client parameter instead of the manifest (INV-ANA-65), and the artefact gains
the key, its origin and `class_defs_under_key` (INV-ANA-66). That is a
correctness change with its own justification in
`openspec/changes/gh111-cadeia-medicao/design.md`. Nothing in the decision
below is withdrawn by it.

## Related

- Change: `openspec/changes/gh66-gator-wtg-flowcontainer-perf/` (proposal.md,
  design.md decision D1)
- GitHub Issue: #66
- Diagnosis: `docs/20260613_wtg_timeout_buildflowthroughcontainer.md`
- Sweep context: `docs/20260609_sweep_wtg_completo_169.md`,
  `docs/20260613_relatorio_sweep_wtg_jca_169.md`
- Prior GATOR edit precedent (arity guard, source-vs-JAR discipline): commit
  `e584894a` (`rvsec` repo)
- Spec invariant: INV-ANA-39 (`openspec/specs/analysis/spec.md`, FR04; NFR04)
- GATOR source:
  `rvsec-android/rvsec-gator/sootandroid/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java:311-369`
  (`rvsec` repo)
- Shipped artifact: `lib/gator/rvsec-gator.jar`
