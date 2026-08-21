## Context

GATOR marks each APK method with `reachesTarget`/`directlyReachesTarget` against the target methods of
the active JavaMOP spec set (FR04–FR06). The matching pipeline is exact-FQN and import-explicit, written
for the JCA spec style. The `generic_new` spec set declares owners by type hierarchy (`Collection+`),
uses wildcard imports (`java.util.*`), and wildcard method names (`add*`). Result: the extractor emits
**0** targets for `generic_new` (vs 120 for `jca`), so `reachesTarget=false` everywhere.

This design implements **decision A2** (subtype match at match-time via `FastHierarchy.canStoreType`),
keeps the **output schema unchanged** (decision B), and scopes the change to **matching + rebuild +
tests** — a scoping choice recorded here rather than as a lettered decision (an earlier draft called it
"decision C"; no such decision was ever written, so the label is dropped). It builds on the `TargetMethod`/`MatchPolicy`/`TargetResolver`/`MopSpecsTargetSource`
abstraction from gh60-targets-core (INV-ANA-33/35) and the Soot 4.7.1 baseline (INV-ANA-18). Full
ideation and adversarial validation: `docs/20260617_sa_generic_new.md` §1–§15.

## Architecture

```
 .mop (generic_new / jca)                          Soot Scene (of the APK)
        │                                                  │
        ▼  [Extractor: rvsec-mop-extractor]                │
 UsedJcaMethodsVisitor                                     │
   • register wildcard-import packages                     │
   • strip owner '+'  → includeSubtypes=true               │
   • resolve simple name → FQN (imports, then Class.forName)
   • keep 'add*' as pattern → nameIsPattern=true           │
        │  MopMethod{className,name,params,sig,            │
        │            +includeSubtypes,+nameIsPattern}       │
        ▼                                                   │
 [Gator commons] TargetMethod{...,+includeSubtypes,+nameIsPattern}
        │  (MopSpecsTargetSource.load propagates flags)     │
        ▼  [Gator client — A2 predicate, 2 points]          ▼
 TargetResolver.resolveInScene ───────────────────► canStoreType(callSiteType, superType)
 RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan ─┘  && nameMatches(pattern)
        │   (super-types force-resolved into Scene; degrade→equals+log if absent)
        ▼
 reachability[].methods[].{reachesTarget,directlyReachesTarget}   ← schema UNCHANGED
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `UsedJcaMethodsVisitor.visit(ImportDeclaration)` | Register wildcard-import packages instead of discarding them | `import java.util.*;` | packages map `{java.util, java.io, ...}` |
| `UsedJcaMethodsVisitor.visit(MethodPointCut)` | Resolve owner (imports → `Class.forName`), strip `+`, keep name pattern | `call(* Collection+.add*(..))` | `MopMethod{java.util.Collection, add*, includeSubtypes=true, nameIsPattern=true}` |
| `MopMethod` (extractor model) | Carry the two new flags **and include them in `equals`/`hashCode`/`toString`** (else flag-differing pointcuts are silently deduped in the visitor's `Set<MopMethod>`) | — | fields `includeSubtypes`, `nameIsPattern` |
| `TargetMethod` (gator commons) | Carry the two new flags | `MopMethod` | fields `includeSubtypes`, `nameIsPattern` |
| `MopSpecsTargetSource.load()` | Propagate flags `MopMethod → TargetMethod` | `Set<MopMethod>` | `Set<TargetMethod>` |
| `TargetMatching` (new helper, gator client) | `nameMatches(pattern,name)` + `canStoreType(sub,sup)` + `forceResolveTargets(scene)` | `TargetMethod`, Soot types | boolean / resolved types |
| `TargetResolver.resolveInScene` | Seed reverse-BFS via subtype predicate when `includeSubtypes` | `Set<TargetMethod>`, Scene | `Set<SootMethod>` |
| `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` | Direct scan via subtype predicate against declared super-type | invokes, targets | callers `Set<SootMethod>` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-ANA-40 (extractor wildcard/`+`/pattern) | `UsedJcaMethodsVisitor.visit(ImportDeclaration\|MethodPointCut)` | `UsedMethodsGenericTest` — N fixed **in advance** (67 distinct `(owner-with-`+`, method-name)` `call()` pairs; 66 if `+` is not part of the owner key — state which key the test uses), not pinned to whatever the implementation emits; extractor run asserts 27→N (24 specs with ≥1 target), 23→120 |
| INV-ANA-41 (flag propagation) | `MopSpecsTargetSource.load()` + `MopMethod`/`TargetMethod` ctors | `MopSpecsTargetSourceTest` (generic flags true, jca flags false) — **task 2.4b** |
| INV-ANA-42 (A2 predicate, both points + cascade) | `TargetMatching` in `TargetResolver.resolveInScene` + `ReachabilityEngine`/`findDirectTargetCallersByBytecodeScan` carrying `Set<TargetMethod>` (hybrid scan) | `TargetMatchingTest` (class→iface, **iface→iface `List<:Iterable`**, bare `*`); `RvsecAnalysisClient` IT |
| INV-ANA-43 (Scene force-resolve + phantom-aware degrade) | `TargetMatching.forceResolveTargets` + `isPhantom`/`resolvingLevel` guard + degrade branch | `TargetMatchingTest` (absent type **and phantom owner** → equals + warn) |
| INV-ANA-44 (schema invariance) | no JSON writer change; assert key-set equality | JSON key-set diff generic vs jca; `MopSpecsParityTest` (INV-ANA-35) |
| INV-ANA-64 (`reaches ⊇ direct` by construction) | `ReachabilityEngine.run()`: compute `directTargetSet` first, then `multiSourceBfs(reversed, targets ∪ directTargetSet)`; `JsonReportWriter` untouched (no gate) | new cases in the existing `ReachabilityBfsTest` (scan-only caller marked; **its caller marked too** — the property post-hoc union misses; empty direct set ⇒ byte-identical to today) + the **already-existing** tripwire `test_reachability_parity.py:163`, whose "by construction" docstring this change finally makes true — **tasks 3.2b/3.2c** |
| INV-ANA-40 JCA half (no drift on the frozen set) | extractor unchanged for exact-import owners; `java.lang` not seeded (D5) | literal count 120/68/22 (`jca`) and 119/67/22 (`jca_android`), flags false — **task 1.5 is the real JCA gate**, not `MopSpecsParityTest` |

## Goals / Non-Goals

**Goals:**
- Extractor emits N>0 targets for `generic_new`, with `includeSubtypes`/`nameIsPattern` set correctly.
- Both match points are subtype/wildcard-aware via `canStoreType`, covering interface→interface.
- Target super-types are loaded into the Scene before `canStoreType`; absent types degrade gracefully.
- Output JSON schema unchanged; JCA parity (INV-ANA-35) preserved byte-for-byte.

**Non-Goals:**
- Running the `generic_new` reachability sweep or defining the generic dataset (separate later change;
  the sweep corpus has moved from the 400-APK set to `rvsec-dataset` — see proposal Impact).
- Per-spec `reachesTarget` in the static output (decision B — per-spec stays at runtime).
- Handling owner subtype-matching in the **parameter** position (JCA `Object+` parameters already
  handled by `getParams`; out of scope).
- Mitigating quasi-universal specs (`Object+`, `Iterable+`, `Comparable+`) inflating `reachesTarget` —
  accepted as correct behavior for the matcher. But "downstream concern" understates it: `aperv-tool`
  already consumes `reachesTarget` directly, so saturation lands on shipped code, not only on a future
  dataset filter. Specifically `signatures(..., reaching_only=True)` (`static_artifact.py:337-360`), the
  `hot`/`cold`/`unresolved` handler verdict (`:288-296`, where saturation collapses `cold` → `hot`), the
  MOP widget set and `mopActivitiesAugmented` (`derive_mop_artifact.py:421-424,1029`), and — most
  consequential — `sa_methods_reaches_mop`, documented at `static_artifact.py:13-17` as the size covariate
  / offset of a count model, which degenerates toward `total_methods` once saturated. None of this blocks
  gh69; all of it belongs in the downstream change's problem statement rather than being discovered there.
- **Seeding the implicit `java.lang` package / repairing the `RandomStringPassword` false-negative**
  (D5, INV-ANA-40 scope boundary (c)). The repair needs owner visibility *plus* a STRICT policy for that
  target *plus* FQN parameter resolution; done piecemeal it degrades the `jca` measurement instead of
  improving it. Deferred to its own change (task 5.6). **This is the one non-goal on the list that
  leaves a High risk standing — RISK-013**: `RandomStringPasswordSpec` is 1 of the 23 `jca` specs and
  contributes zero static targets, so every `cov_reaches_target` published from the frozen set was
  computed over 22 of 23. Deferring the *measurement* repair is the right call (the half-repair is
  measurably worse: 74 call sites, 17 woven, 57 false positives); deferring the *visibility* is not,
  and this change does not — task 1.3(b) turns the silent drop into a logged skip, and task 1.5 asserts
  it stays logged. Read this non-goal together with `risk-register.md` RISK-013 before treating it as
  routine.
- **Resolving pointcut parameter types to FQN** (`UsedJcaMethodsVisitor.getParams`). After this change an
  owner resolves (`java.util.Map`) while its parameters keep the simple names the pointcut wrote (`Map`,
  `Object`), because `getParams` consults only the explicit-import map. This is inert for matching — MOP
  targets are LENIENT and ignore parameters — but two things follow: the parameter list participates in
  `MopMethod.equals`/`hashCode`, so it affects the cardinality N pinned by task 1.4; and resolving it
  later may *merge* entries that differ today only by how a spec spelled a type, which would move the
  `jca` count of 120 for reasons unrelated to the owner fix. Measure before touching it.
- Extracting **non-`call()` pointcut shapes** (documented static false-negatives, bounded): the 3 specs
  whose only pointcut is `staticinitialization(Owner+)` (`Collection_HashCode`,
  `Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission`) emit zero static targets, and
  the 3 constructor pointcuts `call(Owner.new(..))` (`ServerSocket.new` ×2, `TreeMap.new`) are not
  extracted (Soot `<init>` mapping not implemented). **What is in scope is suppressing them.** The
  javamop grammar routes `.new` through `MethodPointCut` (`aspectj.jj:1730-1737`: `"." <NEW>` sets
  `owner = retType`, `name = "new"`), and nothing rejects it today — the corpus yields nothing only
  because every `generic_new` import is an asterisk import, leaving the `imports` map empty. Register
  wildcard packages without adding the skip and these pointcuts start emitting a `MopMethod` named
  `new`, a target no Soot method can match, quietly breaking the 67/66 cardinality gate. So the Non-Goal
  is the `new`→`<init>` *mapping*; the explicit skip in task 1.3(d) is a requirement.
  Net static coverage is 24/27 specs; the runtime
  monitor still covers all 27. See INV-ANA-40 scope boundary.

## Decisions

**D1 — Subtype match via `canStoreType` at match-time (A2), not pre-expansion (A1).** A1 expands each
super-type to its implementers via `getActiveHierarchy().getImplementersOf(...)` and matches by exact
key. The spike (`out/spike_subtype_hierarchy/`) proved A1 is incomplete: `getImplementersOf(Iterable)`
omits sub-interfaces (`java.util.List` absent), so an interface-typed call site `List.iterator()`
against `Iterable+.iterator` is missed. A2 asks `canStoreType(List, Iterable)=true` at the call site
and is correct by construction (the call-site type is always in the Scene). **Recorded as an ADR.**

**D2 — Force-resolve target super-types into the Scene + phantom-aware degrade-to-exact-with-log.**
The real failure mode (verified empirically against Soot 4.7.1 in the gator fat jar) is **not** an
exception and **not** a "non-answer": because GATOR runs with `allow_phantom_refs=true`, an unresolvable
type force-resolves to a **phantom** `SootClass` at `BODIES` level, so `checkLevel(HIERARCHY)` passes and
`canStoreType` returns a **definite `false`** that silently masks a false-negative. (The spike line
`ByteArrayInputStream <: Closeable : one side NOT in Scene` was the spike's own `containsClass` guard,
not a `canStoreType` result.) The call-site type is normally loaded, but a declared super-type may be
phantom/absent. Mitigation: `Scene.v().forceResolve(fqn, SootClass.HIERARCHY)` for each declared target
owner, **then** obtain the `FastHierarchy`. An earlier draft demanded that `forceResolveTargets` run
before the first `Scene.v().getOrMakeFastHierarchy()` call *anywhere in the run*. That requirement is
**dropped**: it is both unsatisfiable and unnecessary. Unsatisfiable, because GATOR itself never calls
`forceResolve`/`getOrMakeFastHierarchy`/`getActiveHierarchy` (zero occurrences across `client`, `commons`
and `sootandroid` — it uses its own `presto.android.Hierarchy`, unrelated to Soot's `FastHierarchy`),
while SPARK materialises the `FastHierarchy` inside the `cg` pack (`PAG`, `ContextInsensitiveBuilder`,
`TypeManager`, `OnFlyCallGraphBuilder`, `VirtualCalls`) long before `RvsecAnalysisClient.run()` executes
at the tail of `GUIAnalysis.run()` → `executeClientAnalyses` → `client.run()`. Unnecessary, because the
premise is false for Soot 4.7.1: `Scene.addClass` calls `modifyHierarchy()`, which nulls
`activeFastHierarchy`, and `getOrMakeFastHierarchy()` rebuilds whenever that field is null — so
force-resolving a not-yet-present owner invalidates the cache by itself. **The real rule** is therefore:
resolve the owners first, obtain the `FastHierarchy` afterwards (calling `Scene.releaseFastHierarchy()`
first if an owner was already present as a phantom, the one case `addClass` does not cover), and never
cache the `FastHierarchy` instance across a resolution. Then, at match time, guard on `isPhantom()` /
`resolvingLevel() < HIERARCHY` (NOT merely `containsClass`) — if phantom/absent, degrade that owner to
exact `equals` and log a warning once per owner. A `try/catch` is **not** the right mitigation (the call
does not throw for natural phantoms — it would be dead code). Alternative (do nothing) rejected: silent
false-negatives. This is the highest-risk point — validated in the IT against the real
`RvsecAnalysisClient` scene, where a degrade on a `generic_new` owner is a **hard gate** (blocks the sweep).

**D3 — Output schema unchanged (decision B, adopted).** Per-spec attribution already lives at runtime
(the `.mop` handlers log `RVSEC ... ::: <SpecName>`, parsed by `rv-coverage` into `errors.csv` —
`logcat_parser.py:495-660`); coverage uses the aggregated `reachesTarget` as denominator
(`result_processor.py:487-491`, arithmetic in `rv-android-core/domain/coverage.py:438-440`, denominator
populated at `coverage.py:886-888`). **Known hole, specific to this change's target set**: the
`[helper] ::: ` lines emitted by `generic_new` are deliberately *not* parsed — a `:::` line whose left
part has no dot resolves to no class and no method, so those lines are counted into
`diagnostics.format3_unresolved` and dropped (`logcat_parser.py:556-560,636-645`). Runtime per-spec
attribution is therefore **partial for `generic_new`**, i.e. exactly for the spec set gh69 enables. B
still holds — the static layer should not grow per-spec keys — but the "attribution already lives at
runtime" justification is weaker here than for `jca` and must not be cited as though it were complete. Adding a per-spec
`targetSummary` to the JSON is unnecessary. The destructive variant would break the raw-JSON readers —
and the sharpest of them is `derive_mop_artifact.py:422` (`method.get("reachesTarget") is True`), which
degrades a rename to a silent `False`. An earlier draft cited the ape `opt*` parser here; that was
wrong, since `MopData.java` reads the *derived* `*.mop.json` and never this artefact. Alternative (additive `targetSummary`) rejected as unneeded complexity (P1).

**D4 — Name-pattern matching: trailing-`*` prefix semantics, including the bare `*`.** The wildcard
method names in `generic_new` are **8** (verified by grep — the earlier "only 3" was wrong): `add*`,
`remove*`, `retain*`, `clear*`, `put*`, `offer*`, `write*`, and the bare `*` (`call(* Iterator.*(..))`,
in `Collections_SynchronizedCollection.mop` and `Collections_SynchronizedMap.mop`).
`nameMatches(pattern, name)` is `pattern.endsWith("*") ? name.startsWith(pattern[:-1]) :
name.equals(pattern)`. The bare `*` reduces to prefix `""`, so `name.startsWith("")` matches every
method of the owner — this is the **intended** AspectJ semantics for `Iterator.*`, and MUST NOT be
special-cased to `false` (rejecting an earlier review suggestion that would have broken these specs). A
non-trailing-`*` pattern falls through to `equals` (safe literal). No general glob (`*Listener`) needed (P1).

**D5 — Extractor owner resolution: explicit imports first, `Class.forName` over wildcard packages
second; the implicit `java.lang` package is NOT seeded.** All 21 owners appearing in `generic_new`
`call()` pointcuts are JDK classes (`java.lang`/`util`/`io`/`net`), hence loadable at the extractor's
runtime. **Being a JDK class is not sufficient**, though: resolution is import-driven, so an owner whose
package no import of *its own spec* registers cannot be resolved at all. That case was live in the corpus
— `CharSequence_NotInSet.mop` declared `Set+` while importing only `java.io`/`java.lang`/`java.nio` — and
is repaired in task 1.0b by adding the missing `import java.util.*;`. After that repair, all 20
non-constructor owners resolve. An owner that resolves via neither route is logged and skipped
(validated §14 item 14); this is RISK-006's failure mode, and the corpus shows it is not hypothetical.

The earlier plan also seeded `java.lang` by default as defense-in-depth. That is **reversed** on
measurement (2026-08-21, list corrected 2026-08-21): `generic_new` does not need it — all **seven**
specs with a `java.lang` `call()` owner carry an explicit `import java.lang.*;`
(`CharSequence_UndefinedHashCode`, `Comparable_CompareToNull`, `Comparable_CompareToNullException`,
`Long_BadParsingArgs`, `Object_MonitorOwner`, and — owner `Iterable` — `ListIterator_Set` and
`Map_UnsafeIterator`; an earlier draft listed six and wrongly included `CharSequence_NotInSet`, whose
`call()` owner is `Set`, `CharSequence` appearing only in `args()`). Seeding it, meanwhile, silently
moves the frozen `jca`/`jca_android` sets —
`String`, owner of the two `RandomStringPassword.mop` pointcuts, is the only unresolved owner in either
set, and resolving it under LENIENT makes `String#valueOf` match every overload (74 call sites over 3
corpus APKs, only 17 of them woven). See INV-ANA-40 scope boundary (c) and `docs/20260821_handoff_gh69_coringas.md`.

Two consequences worth recording for whoever repairs that later: (i) writing the owner as an FQN in the
pointcut (`call(... java.lang.String.valueOf(Object))`) does **not** work either — the visitor keys its
map by simple name, so a dotted owner never matches and would need its own rule; (ii) resolution being
import-driven means a non-JDK owner reached only through a wildcard import cannot be resolved by
`Class.forName` at all (RISK-006), which an explicit-import convention would fix.

**D6 — Rebuild order: extractor `install` → gator `client`.** The extractor is a compile-scope
dependency bundled into `rvsec-analysis-client.jar`; rebuilding gator without first `install`-ing the
extractor links the stale `.m2` copy (validated §14 item 12).

**D7 — Representation: two orthogonal booleans on `MopMethod`/`TargetMethod`; `MatchPolicy` untouched.**
`includeSubtypes` (owner: exact-FQN vs `canStoreType` subtype) and `nameIsPattern` (method name: exact
vs trailing-`*` prefix) are added as independent boolean fields — **not** folded into the existing
`MatchPolicy` enum. `MatchPolicy` is a different, orthogonal axis: *signature strictness* — `LENIENT`
(className+methodName) vs `STRICT` (full Soot signature), set per target by the sources and branched on
in `TargetResolver.resolveInScene`. The three axes are independent (a `generic_new` owner is
`LENIENT`+subtype+pattern; a JCA owner is `LENIENT`+exact+exact; a signature-file entry may be
`STRICT`+exact+exact), so collapsing them into one enum explodes to the cartesian product (up to 8
values) and would break the `LENIENT`/`STRICT` semantics, `equals`/`hashCode`, and the `STRICT`
signature-file path. Two booleans with `MatchPolicy` left intact is the minimal faithful representation
(P1). The alternative considered and rejected here was raised during artefact review (2026-06-18);
recorded in ADR 0004 ("Representation" alternative). Task 2.1 enforces "do not change `MatchPolicy`".

**Caveat on `nameIsPattern` (raised 2026-08-21, kept deliberately).** Of the two booleans, only
`includeSubtypes` carries information the name cannot. `nameIsPattern` is a pure function of the stored
name — `nameMatches` consults it only in conjunction with `methodName.endsWith("*")`, and a Java
identifier can never contain `*`, so `nameIsPattern == methodName.endsWith("*")` always. It therefore adds
no discriminating power to `equals`/`hashCode` either: `add*` and `add` are already different strings. The
dedup argument in D-Key-Components and task 1.1 holds **only** for `includeSubtypes`, and there it is
earned by exactly one real pair in the corpus (`Iterator.next` in `Map_UnsafeIterator` vs `Iterator+.next`
in `ListIterator_Set`). The flag is kept anyway, for one reason: it records the extractor's *intent* at
the boundary, so a future non-trailing glob (`*Listener`) changes `nameMatches` alone rather than
re-deriving intent from string shape at every call site. If that future never arrives, deleting
`nameIsPattern` is a safe simplification — noted here so the P1 tension is a recorded decision rather than
an oversight.

**D8 — Restore `reaches ⊇ direct` (INV-ANA-64) by seeding the reverse BFS with the direct set, not by
patching the sets afterwards.** The containment is definitional (a direct caller is a path of length 1), yet the tree
violates it: measured over the 269 `*.apk.json` present, 14 flags across 6 distinct methods in 2 APKs
carry `directlyReachesTarget=true` with `reachesTarget=false`. The cause is that **one relation has two
oracles, and only one of them was repaired**. `directlyReachesTarget` is
`findDirectTargetCallers(cg) ∪ findDirectTargetCallersByBytecodeScan(...)`, the union that repairs
BUG-INV-ANA-19 (SPARK quarantines app→library invokes and omits the edges); `reachesTarget` is
`multiSourceBfs(reversed(cg), targets)` — the call graph alone, which never received that repair.
`complementWithCallbacks` does not close the hole either: it patches callbacks only, and only through
call-graph edges. Of the 14, **12 sit on methods with `reachable=false`** — code SPARK never processed,
which therefore has no vertex in the graph at all; the other 2 are in the graph with the specific edge
missing.

Three repairs were considered.

*Post-hoc union* (`reachesTargetSet.addAll(directTargetSet)` after both are computed) is one line and
restores the containment, but only asserts it: the callers of those methods stay `false`, so the
transitive false negative survives. Rejected — it makes the invariant true without making it derived.

*Graph repair* (have the scan return `(caller, target)` pairs and inject the missing edges into the
JGraphT graph before any BFS) is the structurally pure option and yields **exactly the same `reaches`
set** as the one adopted — the caller lands at distance 1, the reverse BFS picks it up and climbs
identically. It costs a signature change, and because the scan keys on `class#name` (which collapses
overloads) one scan hit would expand into N synthetic edges in a graph other code reads. Rejected on
cost for zero difference in outcome (P1).

*Seeding* is adopted: compute `directTargetSet` first, then
`multiSourceBfs(reversed, targets ∪ directTargetSet)`. Containment holds by construction, propagation
upward is correct, no signature changes, and `multiSourceBfs` already calls `graph.addVertex(seed)`
before its visited check — with a comment describing precisely this case — so a seed with no
call-graph vertex needs no new defensive code.

**No enforcement gate.** The invariant is stated over the *construction*, not over the output, so it is
verifiable by test without demanding a runtime check. `JsonReportWriter` is deliberately left untouched:
aborting a long analysis over a residual method would trade slightly inconsistent data for no data. The
residual that seeding cannot remove is an *ancestor* of a scan-discovered method that is itself absent
from the call graph — a false negative on the transitive axis, never a violated containment.

The containment was already asserted — `tests/parity/test_reachability_parity.py:163` calls itself an
"Invariant by construction ... Tripwire if not". It is not, today, by construction: that test runs GATOR
over `cryptoapp` alone and passes because that APK has zero violations, while the 6 that violate sit in
`app.notesr_59` and `com.beemdevelopment.aegis_81`. So this decision does not introduce a contract; it
delivers one that the test suite has been claiming for longer than it has been true. Note also that
`ReachabilityEngine.run()` is Scene-bound (`Scene.v().getCallGraph()`), so the wiring itself is reachable
only by IT — the synthetic-graph tests lock the composition semantics, not the call site.

**Measurement cost: none.** The frozen fixture behind `G_paridade_targets`
(`modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`) has **zero** violations today
(21 direct, 32 transitive), so the value-stability gate does not move; `BaselineComparisonIT` tolerates
±10% on `reachesTarget` regardless. The defect predates this change — it is the unfinished half of
BUG-INV-ANA-19 — but gh69 amplifies it: the direct set grows from 0.0–0.3% of app methods to 2–12%
(RISK-004), and the scan-only share of it grows with it, so a defect that is 6 methods today would be
projected (projection, not measurement) into the hundreds. That is why it is repaired here rather than
deferred.

## API Design

### `boolean TargetMatching.matches(Type callSiteType, String callSiteName, TargetMethod t, FastHierarchy fh)`
- **Signature decided** (closes the open question in task 2.3): the helper takes the **raw** call-site
  `(Type, String)`, NOT a `SootMethodRef`. Both match points adapt with zero allocation —
  `resolveInScene` passes `method.getDeclaringClass().getType()` + `method.getName()` (`SootMethod`); the
  bytecode scan passes `ref.getDeclaringClass().getType()` + `ref.getName()` (`SootMethodRef`). This
  avoids a `makeRef()` allocation per Scene method in `resolveInScene`. `STRICT` param-matching stays in
  `resolveInScene` (not folded into this helper, which is lenient by design).
- **Pre**: the call-site `Type` is in the Scene; `t` is a loaded target.
- **Behavior**: evaluate `nameMatches(t, callSiteName)` **first** (cheap short-circuit — return `false`
  with no hierarchy query if it fails). Then: if `!t.includeSubtypes` →
  `callSiteType.toString().equals(t.className)` (exact path, unchanged). If `t.includeSubtypes` →
  `fh.canStoreType(callSiteType, superType(t))` where `superType(t)` is the **cached** resolved `RefType`
  of `t.className` (resolved once per target, not per invoke). **Phantom guard**: if the `SootClass` of
  `t.className` `isPhantom()` or `resolvingLevel() < HIERARCHY`, do NOT call `canStoreType` (it would
  return a definite, wrong `false`); fall back to exact `equals` and log once per owner.
- **Post**: returns whether the call site is a target invocation. No Scene mutation.

### `Set<RefType> TargetMatching.forceResolveTargets(Set<TargetMethod> targets)`
- Resolves each distinct `t.className` via `Scene.v().forceResolve(fqn, SootClass.HIERARCHY)`; returns
  the set actually loaded. Owners that fail to resolve are logged and excluded (degrade to exact).

### `nameMatches(TargetMethod t, String name)`
- `t.nameIsPattern && t.methodName.endsWith("*")` → `name.startsWith(t.methodName[:-1])`; else `name.equals(t.methodName)`.

## Data Flow

1. Extractor parses each `.mop`: wildcard packages registered → owner resolved to FQN → `+` stripped
   (`includeSubtypes`) → method name kept as pattern (`nameIsPattern`) → `MopMethod`.
2. `MopSpecsTargetSource.load()` maps each `MopMethod` to a `TargetMethod`, propagating both flags.
3. `forceResolveTargets` loads declared super-types into the Scene.
4. `TargetResolver.resolveInScene` seeds the reverse-BFS `Set<SootMethod>` by applying `matches(...)`
   across scene methods; `ReachabilityEngine` runs the reverse-BFS unchanged.
5. **Contract change (cascade):** the declared `Set<TargetMethod>` (super-type FQN + flags) must reach
   the second match point. Today `RvsecAnalysisClient.run()` holds both `targetSpecs`
   (`Set<TargetMethod>`, declared at `:115`) and the resolved `targetMethods` (`Set<SootMethod>`) — and
   `targetSpecs` is in fact a **dead local**: assigned in both branches and never read afterwards, which
   is precisely the gap this cascade closes. But `ReachabilityEngine`'s
   constructor receives **only** `targetMethods`, and `findDirectTargetCallersByBytecodeScan(appClasses,
   Set<SootMethod> targets)` rebuilds a `Set<String> targetKeys`. So `ReachabilityEngine` and the scan
   MUST be extended to also carry `Set<TargetMethod>`. The scan becomes **hybrid**: a `Set<String>` of
   exact `class#method` keys for `!includeSubtypes` targets (JCA O(1) lookup + parity preserved) plus
   iteration over the `includeSubtypes` targets (grouped by distinct super-type to amortize resolution)
   applying `matches(...)` per invoke against the declared super-type — recovering literal subtype
   invocations (BUG-INV-ANA-19).
6. JSON written with the unchanged key set; only boolean values reflect the new matches.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Owner unresolvable in extractor | `Class.forName` over wildcard pkgs fails | log + skip that pointcut | target absent; no crash (no JDK-external owner today) |
| Super-type absent from Scene at match | `forceResolve` could not load it | degrade owner to exact `equals` + log warning | exact matching for that owner; no silent FN (INV-ANA-43) |
| Corrupt method body during scan | `retrieveActiveBody()` throws | catch + skip (mirror INV-ANA-17/BUG-INV-ANA-19) | rest of scan proceeds |

## Risks / Trade-offs

- **Super-type absent from Scene** → mitigated by `forceResolve` + degrade-with-log (D2); validated in
  the IT on the real `RvsecAnalysisClient` scene before any sweep.
- **`canStoreType` cost in the scan** → O(1) amortized in `FastHierarchy`; the scan already iterates all
  invokes. Measured in the IT.
- **The reverse BFS inherits a much larger seed set** → `resolveInScene` iterates `Scene.v().getClasses()`, so a quasi-universal owner makes it seed with every matching library method
  rather than the ~120 JCA ones, and `ReachabilityEngine.multiSourceBfs` runs from that. It is the
  stage that grows least visibly, so the INV-ANA-42 cost bound and task 4.8 time the BFS alongside the
  two match points.
- **`resolveInScene` loses its `equals(fqn)` fast-reject** for subtype targets → it iterates
  `Scene.getClasses()` × methods × targets, and with `includeSubtypes` the per-pair cost rises from a
  string-equal to a `canStoreType`. Mitigated by ordering `nameMatches` before `canStoreType` (name
  short-circuit) and caching the resolved `superType(t)` `RefType` once per target (RISK-005, now
  broadened to cover both match points, not just the scan).
- **Quasi-universal owners** (`Object+`, `Iterable+`) inflate `reachesTarget` → correct per the spec;
  any dataset-level exclusion is a downstream decision, not a matcher concern.
- **Extractor↔gator rebuild coupling** → mitigated by the mandatory 2-step order (D6).

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (extractor) | Parse generic_new → the N fixed in advance (67 pairs under a `+`-aware owner key, 66 otherwise; 3 ctor-skip notices; 0 unresolved-owner skips after the 1.0b repair; 24/27 specs covered), flags set; jca → 120, flags false | JUnit on `UsedJcaMethodsVisitor`/`JavamopFacade` with the 27+23 specs | ~4 |
| Unit (matcher) | `canStoreType` class→iface, **iface→iface (`List<:Iterable` — the only case that distinguishes A2 from A1)**; name patterns `add*`…`write*` and bare `*`; non-trailing pattern → `equals`; absent-type **and phantom owner** degrade | JUnit on `TargetMatching` with a minimal Scene | ~7 |
| Source | `MopSpecsTargetSource.load()` propagates flags (generic true / jca false) | `MopSpecsTargetSourceTest` (INV-ANA-41 — task 2.4b) | ~2 |
| Parity | Source-layer parity only: `MopSpecsTargetSource.load` vs `JavamopFacade.listUsedMethods` on the same dir — **both sides run through the modified visitor**, so this test cannot catch an extractor-side JCA regression (its fixtures are `CipherSpec`/`MessageDigestSpec` only, no `String`). The JCA regression gate is the literal count in the extractor test | `MopSpecsParityTest` (INV-ANA-35) | existing |
| Integration | 1 APK against generic_new: **`directlyReachesTarget` in the measured 2–12% band** (the load-bearing assertion — `reachesTarget` saturates at 84–94% under `generic_new` and passes trivially, RISK-004); `reachesTarget>0` kept as smoke only; `canStoreType` in real `RvsecAnalysisClient` scene; JSON key-set == jca run; **negative — a subtype-receiver call with a non-matching name (`ArrayList.remove` vs `add*`; `String.length` vs `Object+.wait/notify`) stays `reachesTarget=false` (name-axis, since `Object+` makes every type a subtype)**. All of these are failsafe `*IT` tests and are **skipped by default** (`client/pom.xml:18` sets `<skipITs>true</skipITs>`) — every IT command MUST pass `-DskipITs=false` | gator E2E on a small APK | ~3 |
| Integration (JCA gate) | `BaselineComparisonIT` on `cryptoapp.apk` — the end-to-end half of the JCA regression gate named in INV-ANA-40's scope boundary. It exists (`client/src/test/java/presto/android/gui/clients/BaselineComparisonIT.java`) but no task ran it before; task 5.1b does | failsafe, `-DskipITs=false` | 1 |
| Integration (scan-only) | A `generic_new` method reachable **only** via the direct bytecode scan (not via the SPARK call graph) reports `directlyReachesTarget=true` — the RISK-009 indicator, previously asserted by no test | failsafe, `-DskipITs=false` | 1 |
| Performance | Wall-time of `resolveInScene` **and** of the bytecode scan, generic_new vs jca on the same APK, MUST be ≤ 2× the JCA baseline — the RISK-005 hard trigger, previously measured by no task | timed IT | 1 |
| Downstream smoke | `static_analysis_parser.py` parses the `generic_new` output without error (RISK-007 indicator) | one parser call on the IT JSON | 1 |

## Open Questions

- None blocking. The quasi-universal-spec dataset treatment (exclude `Object+`/`Iterable+` from the
  dataset filter, or keep) is explicitly deferred to the downstream sweep/dataset change — it does not
  affect this matcher design.
