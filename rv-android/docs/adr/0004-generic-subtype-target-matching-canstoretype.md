# ADR 0004 — Generic-spec subtype target matching via `FastHierarchy.canStoreType` at match-time (not implementer pre-expansion)

**Status**: Accepted (gh69, 2026-06-17)

## Context

GATOR marks each APK method with `reachesTarget` / `directlyReachesTarget` against the target methods of the active JavaMOP spec set (FR04–FR06). The matching pipeline — built on the `TargetMethod` / `MatchPolicy` / `TargetResolver` / `MopSpecsTargetSource` abstraction from gh60 (INV-ANA-33/35) — was written for the JCA spec style: every owner is an exact fully-qualified class name and every method an exact name. JCA specs declare concrete owners (e.g. `javax.crypto.Cipher`), so exact-FQN equality at the call site is sufficient and correct.

The `generic_new` spec set breaks that assumption. It declares owners **by type hierarchy** using AspectJ subtype syntax — `call(* Collection+.add*(..))` means "any `add*` call whose static receiver type is `java.util.Collection` *or any subtype of it*". With the exact-FQN matcher, the extractor emits **0** targets for `generic_new` (vs 120 for `jca`), so `reachesTarget=false` everywhere: a call site typed `java.util.ArrayList.add(...)` or interface-typed `java.util.List.iterator()` never equals the literal owner `java.util.Collection` / `java.lang.Iterable`.

Making the matcher subtype-aware is the core of gh69. The non-obvious decision — the one whose rationale is not derivable from the code alone — is **how** the matcher answers "is this call site a subtype of a declared target owner?", because the two candidate mechanisms (pre-expand the owner to its implementers and match by exact key, vs. ask the hierarchy at the call site) differ in *correctness*, not merely in cost. The choice was settled empirically by a spike before any production code was written; this ADR records that choice so a future reader does not re-derive it the wrong way.

Constraint: Soot is `org.soot-oss` 4.7.1, pinned by the gator fat jar (INV-ANA-18). The JCA path must remain byte-for-byte unchanged (INV-ANA-35 / `MopSpecsParityTest`). Full ideation and adversarial validation: `docs/20260617_sa_generic_new.md` §3.A / §5 / §14. Design D1/D2: `openspec/changes/gh69-generic-subtype-target-matching/design.md`.

PRD references: FR04–FR06 (static reachability against the active spec set).

## Decision

**For subtype-aware owners (`includeSubtypes=true`, i.e. owners declared with `+` in `generic_new`), the matcher tests `FastHierarchy.canStoreType(callSiteDeclaringType, declaredSuperType)` at the moment of the match — not against a pre-expanded set of implementers.** The predicate is applied at the two points where a call site is matched against a target:

1. `TargetResolver.resolveInScene` — seeding the reverse-BFS `Set<SootMethod>`.
2. `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` — the direct bytecode-scan caller detection.

At each point, when `includeSubtypes=true`, the match is `nameMatches(pattern, callSite.name) && fh.canStoreType(callSite.declaringClass.type, superType(target))`, where `superType(target)` is the resolved `RefType` of the declared owner. This is correct by construction: the call-site declaring type is always present in the Scene (it is an invocation Soot has already loaded), so `canStoreType` always has a real left-hand side, and it answers interface→interface subtyping — `canStoreType(java.util.List, java.lang.Iterable) = true` — which is exactly the case the rejected alternative loses.

JCA owners keep `includeSubtypes=false` and stay on the **exact** path (`callSite.declaringClass.name.equals(target.className)`), so INV-ANA-35 / `MopSpecsParityTest` and the JCA target count of 120 are preserved unchanged.

## Alternatives Considered

**A2 — `canStoreType(callSiteType, declaredSuperType)` at match-time (chosen).** Resolve each declared super-type into the Scene, then at every candidate call site ask the `FastHierarchy` whether the call-site's static receiver type can store into the declared super-type. Correct by construction because the call-site type is always in the Scene, and it covers both class→interface and interface→interface subtyping. Trade-off: `canStoreType` returns a non-answer when one side is absent from the Scene (see Consequences → Risk); mitigated below. Cost is O(1) amortized in `FastHierarchy`, and the scan already iterates every invoke, so no new traversal is introduced.

**A1 — pre-expand each super-type to its implementers via `getActiveHierarchy().getImplementersOf(...)` and match by exact key (rejected).** Build, once per run, the set of all concrete implementers of each declared owner, then reuse the existing exact-FQN matcher against that expanded key set. Attractive because it reuses the JCA matcher verbatim. **Rejected because the spike proved it is incomplete.** The spike (`out/spike_subtype_hierarchy/`, Soot 4.7.1 from the gator fat jar; `spike_result.txt`) showed that `getImplementersOf` does **not** return sub-interfaces:

- `getImplementersOf(java.lang.Iterable)` returned 4 implementers — `[ArrayList, AbstractList, AbstractCollection, TextUtils$SimpleStringSplitter]` — all *classes*. `java.util.List`, a sub-*interface* of `Iterable`, is **absent**.
- The same spike's call-site scan recorded a real app invocation `iterator <- java.util.List` (an interface-typed receiver). Under A1, that call site is matched by exact key against `Iterable`'s implementer set, which does not contain `java.util.List`, so the target invocation is **silently lost** (a false negative).
- A2 handles the identical case directly: `canStoreType(java.util.List, java.lang.Iterable) = true` (spike §3 confirms interface→interface resolves `true` for in-Scene types such as `String <: CharSequence`).

A1 would therefore systematically under-report `reachesTarget` for any interface-typed call site against an interface owner — precisely the dominant shape in `generic_new` (`Collection+`, `Iterable+`, `Map+`). The reuse benefit does not outweigh a correctness defect.

**Representation — fold `includeSubtypes` / `nameIsPattern` into the existing `MatchPolicy` enum (rejected).** A tempting "simplification" is to express the two new matching modes as additional `MatchPolicy` values instead of two booleans on `TargetMethod`. It is rejected because `MatchPolicy` is an **orthogonal** axis: it already means *signature strictness* — `LENIENT` (match on `className`+`methodName`) vs `STRICT` (match on the full Soot signature) — set per target by `SignatureFileTargetSource`/`MopSpecsTargetSource` and branched on in `TargetResolver.resolveInScene`. Subtype-of-owner (`includeSubtypes`) and method-name-pattern (`nameIsPattern`) are independent of strictness: a `generic_new` owner is `LENIENT` + subtype + pattern; a JCA owner is `LENIENT` + exact + exact; a signature-file entry may be `STRICT` + exact + exact. Folding all three into one enum yields the cartesian product (`{LENIENT,STRICT} × {exact,subtype} × {exact,pattern}` → up to 8 values) and would break the existing `LENIENT`/`STRICT` semantics, `equals`/`hashCode`, and the `STRICT` signature-file path — the opposite of simplicity. Two orthogonal booleans, with `MatchPolicy` left untouched, is the minimal faithful representation (P1). See design D7.

## Consequences

**Positive.**

- Subtype matching is **correct by construction** for both class→interface and interface→interface, eliminating the interface-typed-call-site false negatives that A1 would have introduced.
- No new graph traversal: `canStoreType` is O(1) amortized in the existing `FastHierarchy`, and the bytecode scan already visits every invoke. The cost is folded into work already done.
- The JCA path is untouched (`includeSubtypes=false` → exact `equals`), so INV-ANA-35 / `MopSpecsParityTest` hold byte-for-byte and the 120-target JCA baseline is preserved.
- The predicate lives at the two real match points rather than in a separate pre-expansion phase, so there is no expanded-key-set cache to keep consistent with the Scene.

**Negative / Trade-offs.**

- The matcher now branches on `includeSubtypes`, adding a second code path (exact vs. subtype). This is intrinsic to supporting two spec styles in one matcher and is covered by dedicated unit tests (`TargetMatchingTest`: class→iface, iface→iface, name-pattern, absent-type degrade).
- Correctness depends on the declared super-type being loaded into the Scene before `canStoreType` is called — a precondition the exact path never had. Handled by the mitigation below.

**Risk — `canStoreType` is silent when a type is absent from the Scene.** `FastHierarchy.canStoreType` does **not** report whether a type is missing; it simply cannot give a meaningful answer. The spike captured this exactly: `java.io.ByteArrayInputStream <: java.io.Closeable` reported `one side NOT in Scene` rather than `true`. The call-site type is always loaded, but a *declared target super-type* may not be.

*Mitigation (design D2):* before building the `FastHierarchy`, `forceResolve(fqn, SootClass.HIERARCHY)` every declared target owner so its super-types are present. If an owner still fails to resolve at match time, that owner **degrades to exact `equals` and logs a warning once** — never a silent false negative (INV-ANA-43). This is the highest-risk point of gh69 and is validated in the integration test against the real `RvsecAnalysisClient` Scene before any sweep runs. JCA owners never enter this path (they are on the exact route with `includeSubtypes=false`).

**Neutral.**

- Output JSON schema is unchanged (design D3); only the boolean values of `reachesTarget` / `directlyReachesTarget` reflect the new matches. `rv-coverage` and the ape `opt*` parser see the same key set.

## References

- GitHub Issue: #69
- Change: `openspec/changes/gh69-generic-subtype-target-matching/` — `design.md` (Decisions D1, D2), `proposal.md`
- Ideation / adversarial validation: `docs/20260617_sa_generic_new.md` §3.A, §5, §14
- Spike evidence: `out/spike_subtype_hierarchy/` (`HierarchyProbe.java`, `run_spike.sh`, `spike_result.txt`) — Soot 4.7.1 from `lib/gator/rvsec-gator.jar`
- Invariants: INV-ANA-18 (Soot `org.soot-oss` 4.7.1), INV-ANA-35 (JCA parity / `MopSpecsParityTest`), INV-ANA-40..44 (gh69 spec deltas)
- Match points (affected code): `TargetResolver.resolveInScene`, `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan`, `TargetMatching` (new helper)
- Related ADRs: 0001 (env-var pattern), 0002, 0003 (resume-path static-data)
