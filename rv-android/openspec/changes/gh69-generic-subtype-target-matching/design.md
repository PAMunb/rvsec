## Context

GATOR marks each APK method with `reachesTarget`/`directlyReachesTarget` against the target methods of
the active JavaMOP spec set (FR04–FR06). The matching pipeline is exact-FQN and import-explicit, written
for the JCA spec style, and it silently discards four constructions the AspectJ pointcut grammar admits:
the `+` subtype operator, an asterisk import as an owner's only declaration, a trailing `*` in a method
name, and the constructor form `Owner.new(..)`. A pointcut using any of them yields no target and no
diagnostic. The design below is therefore written against those **constructions**, not against a corpus.

Two corpora anchor it, with different jobs. **`jca_android` is the production evidence**: 2 `+` owners
(`Key+.getEncoded`, `SecretKey+.getEncoded`) and 39 constructor pointcuts, all dead today — and the
frozen `jca` ruler carries 25 dead constructor pointcuts of its own. **`generic_new` is the verification
fixture**: 71 `+` owners, 15 `*` names, 3 constructor pointcuts and asterisk imports in all 27 specs, so
it is the only set that exercises all four constructions at once and it is where the gates get their
numbers. The extractor emits **0** targets for it today (vs 120 for `jca`).

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
| INV-ANA-40 (extractor wildcard/`+`/pattern) | `UsedJcaMethodsVisitor.visit(ImportDeclaration\|MethodPointCut)` | `UsedMethodsGenericTest` — N fixed **in advance** (**69** distinct `(owner-with-`+`, method-name)` `call()` pairs under D9; **68** if `+` is not part of the owner key — state which key the test uses), not pinned to whatever the implementation emits; extractor run asserts 27→N (24 specs with ≥1 target), 23→120 |
| INV-ANA-41 (flag propagation) | `MopSpecsTargetSource.load()` + `MopMethod`/`TargetMethod` ctors | `MopSpecsTargetSourceTest` (generic flags true, jca flags false) — **task 2.4b** |
| INV-ANA-42 (A2 predicate, both points + cascade) | `TargetMatching` in `TargetResolver.resolveInScene` + `ReachabilityEngine`/`findDirectTargetCallersByBytecodeScan` carrying `Set<TargetMethod>` (hybrid scan) | `TargetMatchingTest` (class→iface, **iface→iface `List<:Iterable`**, bare `*`); `RvsecAnalysisClient` IT |
| INV-ANA-43 (Scene force-resolve + phantom-aware degrade) | `TargetMatching.forceResolveTargets` + `isPhantom`/`resolvingLevel` guard + degrade branch | `TargetMatchingTest` (absent type **and phantom owner** → equals + warn) |
| INV-ANA-44 (schema invariance) | no JSON writer change; assert key-set equality | JSON key-set diff generic vs jca; `MopSpecsParityTest` (INV-ANA-35) |
| INV-ANA-64 (`reaches ⊇ direct` by construction) | `ReachabilityEngine.run()`: compute `directTargetSet` first, then `multiSourceBfs(reversed, targets ∪ directTargetSet)`; `JsonReportWriter` untouched (no gate) | new cases in the existing `ReachabilityBfsTest` (scan-only caller marked; **its caller marked too** — the property post-hoc union misses; empty direct set ⇒ byte-identical to today) + the **already-existing** tripwire `test_reachability_parity.py:163`, whose "by construction" docstring this change finally makes true — **tasks 3.2b/3.2c** |
| INV-ANA-40 JCA half (drift on the frozen set is enumerated, not zero) | extractor unchanged for exact-import owners; `java.lang` seeded and bounded by STRICT (D5/D10) | pre-5.6 literal count 120/68/22 (`jca`), re-pinned by the phase-5.6 enumeration; `jca_android` **derived by enumeration, never pinned** (gh109 is growing it), flags false — **task 1.5 is the real JCA gate**, not `MopSpecsParityTest` |

## Goals / Non-Goals

**Goals:**
- Extractor emits N>0 targets for `generic_new`, with `includeSubtypes`/`nameIsPattern` set correctly.
- Both match points are subtype/wildcard-aware via `canStoreType`, covering interface→interface.
- Target super-types are loaded into the Scene before `canStoreType`; absent types degrade gracefully.
- Output JSON schema unchanged; the gator-side JCA exact-match path (INV-ANA-35 / `MopSpecsParityTest`)
  untouched. **The extractor's `jca` triple does move**, deliberately: D5's seed adds the two
  `RandomStringPassword` signatures, and D11's parameter resolution may merge others. That movement is
  enumerated by the phase-5.6 gates rather than presumed absent — the form D9 established. What is
  preserved is the matching of every owner that already resolved.
- The implicit `java.lang` package is seeded **and bounded**: `RandomStringPassword.mop`'s `String` owner
  resolves, and the two targets it yields are STRICT, so resolving it cannot over-match (D5 + D10). This
  discharges RISK-013 by repair rather than by acceptance.
- Pointcut parameter types resolve to FQN (`UsedJcaMethodsVisitor.getParams`) — the prerequisite that makes
  a STRICT target expressible at all, since STRICT compares the full Soot signature (D11).

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
> **Two entries left this list on 2026-08-28**, by the researcher's instruction, and are now Goals:
> seeding the implicit `java.lang` package (with the `RandomStringPassword` repair it enables) and
> resolving pointcut parameter types to FQN. They were deferred here on the argument that the repair is
> only safe when its three parts land together; the decision is that they land together **in this change**
> rather than in a later one. The argument was never that the repair is wrong — see **D5**, **D10** and
> **D11**, which carry it forward as the rule governing how the three parts are sequenced, and
> `risk-register.md` RISK-013, which closes by repair instead of by acceptance.
- Extracting **non-`call()` pointcut shapes** (documented static false-negative, bounded): the 3 specs
  whose only pointcut is `staticinitialization(Owner+)` (`Collection_HashCode`,
  `Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission`) emit zero static targets —
  such a pointcut never reaches `visit(MethodPointCut)`, so there is nothing for this change to extract.
  **Constructor pointcuts are NOT part of this Non-Goal.** An earlier draft placed them here — "the
  `new`→`<init>` mapping is out of scope; the explicit skip is the requirement" — and **decision D9
  reversed that**: `call(Owner.new(..))` (`ServerSocket.new` ×2, `TreeMap.new`) is extracted as
  `MopMethod(owner, "<init>")`, because the same defect is live and silent in the frozen `jca` set (18
  rows / 11 pairs that have never resolved) and suppressing only the `generic_new` three would ship an
  asymmetry this change itself created. See **D9** for the full argument and **phase 4b** for the gate
  and the re-baseline; the cardinality consequence is 69 pairs / 21 owners for `generic_new`, not 67/20.
  Net static coverage is 24/27 specs — 24 rather than 23 precisely because the mapping is in scope, since
  `TreeMap_Comparable`'s only `call()` pointcut is the constructor; the runtime monitor still covers all
  27. See INV-ANA-40 scope boundary (a) and (b).

## Decisions

**D1 — Subtype match via `canStoreType` at match-time (A2), not pre-expansion (A1).** A1 expands each
super-type to its implementers via `getActiveHierarchy().getImplementersOf(...)` and matches by exact
key. The spike (`out/spike_subtype_hierarchy/`) proved A1 is incomplete: `getImplementersOf(Iterable)`
omits sub-interfaces (`java.util.List` absent), so an interface-typed call site `List.iterator()`
against `Iterable+.iterator` is missed. A2 asks `canStoreType(List, Iterable)=true` at the call site
and is correct by construction (the call-site type is always in the Scene). **Recorded as an ADR.**

**D2 — Force-resolve target super-types into the Scene, then degrade on *hierarchy content*, not on
the phantom flag.** This decision was written against a phantom model that the real Scene falsified;
what follows is the measured version (`cryptoapp.apk`, API 33, gator fat jar, 2026-08-28), with the
superseded reading kept because the trap it describes is real and only its *criterion* was wrong.

*What is true.* GATOR runs Soot with `allow_phantom_refs=true`, so a type Soot cannot find becomes a
phantom `SootClass` that satisfies `Scene.containsClass` and passes `checkLevel(HIERARCHY)` —
`canStoreType` then returns a **definite, wrong `false`** rather than throwing. A `try/catch` is
therefore dead code, and `containsClass` alone is not a sufficient guard. (The spike line
`ByteArrayInputStream <: Closeable : one side NOT in Scene` was the spike's own `containsClass` guard,
not a `canStoreType` result.)

*What is false — and was the change's actual blocker.* The earlier criterion, "classify an owner as
resolved only if `!isPhantom() && resolvingLevel() >= HIERARCHY`", treats `isPhantom()` as a proxy for
"carries no hierarchy". In the GATOR Scene it is not. Under `-force-android-jar` the `java.*`/`javax.*`
owners of both spec sets are read out of the platform `android.jar`
(`$ANDROID_HOME/platforms/android-33/android.jar`, which does ship the `java.*` stubs) with a
**complete and correct hierarchy** — real superclass, real interface list, real `ACC_INTERFACE`
modifier, real method counts — and are flagged phantom all the same. Measured: **522 of the 575**
`java.*`/`javax.*` classes in the Scene are phantom, against 26 of 1665 `android.*` ones. And
`FastHierarchy.canStoreType` answers correctly over every one of them, in every direction tested:
class→class (`ArrayList <: AbstractList`), class→interface (`ArrayList <: Collection`,
`ByteArrayInputStream <: Closeable`) and **interface→interface** (`List <: Collection`,
`List <: Iterable`, `Collection <: Iterable`) — the last being the case decision A2 exists for.
`Collection.getInterfaces()` reads `[java.lang.Iterable]`; `getAllSubinterfaces(Iterable)` has 13
members and `getAllImplementersOfInterface(Iterable)` has 21.

Keying the degrade on the flag therefore degraded **every declared owner of both spec sets** —
`generic_new` 19 of 21, `jca` 22 of 22 — and the direct axis fell to 0.0% of app methods. RISK-001
fired, caused by its own mitigation.

*Two repairs measured and rejected.* Both were tried against the real Scene, and both are inert.
`Scene.forceResolve` genuinely cannot upgrade a pre-existing phantom — `SootResolver.addToResolveWorklist`
returns early when `sc.resolvingLevel() >= desiredLevel`, and a phantom already sits at SIGNATURES — so
`forceResolve(fqn, BODIES)` leaves the class phantom. `Scene.removeClass` followed by a fresh
`forceResolve` completes in 3 ms and changes nothing either; worse, it *destroys* interface data that
was correct before (it is what made `List <: Iterable` read `false` in the first diagnostic, a
measurement artefact and not a property of the Scene). Neither is needed, because these owners require
no repair.

*The rule.* Force-resolve each distinct declared owner at `SIGNATURES` (not HIERARCHY: `canStoreType`
needs only HIERARCHY, but `TargetResolver.resolveInScene` calls `cls.getMethods()` in an unguarded
loop, which opens with `checkLevel(SIGNATURES)`), obtain the `FastHierarchy` **afterwards**, and never
cache it across a resolution. Then classify an owner as usable when it is at HIERARCHY or above **and
carries hierarchy content** — `hasSuperclass() || getInterfaceCount() > 0 || getMethodCount() > 0`.
A class Soot invented because `SourceLocator` found no source carries none of the three: measured,
`getModifiers() == 0`, no superclass, no interfaces, no methods. The three clauses are a disjunction so
that a marker interface (`java.io.Serializable`) is not rejected for having no methods. An owner
failing the test degrades to exact `equals` and logs a warning once per owner — a reported
false-negative rather than a silent one (INV-ANA-43).

*Result.* `generic_new` resolves **21 usable / 0 degraded**, the hard gate of RISK-001 and task 4.3.
`jca` resolves 21 usable / 1 degraded — `javax.xml.crypto.dsig.spec.HMACParameterSpec`, which the
Android platform genuinely does not ship, and which is inert because every `jca` target is
`includeSubtypes=false` and never consults the hierarchy. JCA app-method counts are identical either
side of the criterion change, so INV-ANA-35 is preserved by construction, not by tolerance.

*Ordering, unchanged from the earlier draft.* This capability does **not** require force-resolution to
precede every `getOrMakeFastHierarchy()` in the process. That is unsatisfiable — GATOR itself never
calls `forceResolve`/`getOrMakeFastHierarchy`/`getActiveHierarchy` (zero occurrences across `client`,
`commons` and `sootandroid`; it uses its own `presto.android.Hierarchy`), while SPARK materialises the
`FastHierarchy` inside the `cg` pack long before `RvsecAnalysisClient.run()` executes at the tail of
`GUIAnalysis.run()`. It is also unnecessary: `Scene.addClass` calls `modifyHierarchy()`, which nulls
`activeFastHierarchy`, and `getOrMakeFastHierarchy()` rebuilds when that field is null. The one case
`addClass` does not cover is an owner already present that was upgraded **in place**; the
implementation calls `Scene.releaseFastHierarchy()` exactly then, and not merely because an owner was
flagged phantom — which, per the above, is the common case and modifies nothing.

This remains the highest-risk point, and it is validated in the IT against the real
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
second, the implicit `java.lang` package third — seeded, and bounded by STRICT (D10).** All 21 owners appearing in `generic_new`
`call()` pointcuts are JDK classes (`java.lang`/`util`/`io`/`net`), hence loadable at the extractor's
runtime. **Being a JDK class is not sufficient**, though: resolution is import-driven, so an owner whose
package no import of *its own spec* registers cannot be resolved at all. That case was live in the corpus
— `CharSequence_NotInSet.mop` declared `Set+` while importing only `java.io`/`java.lang`/`java.nio` — and
is repaired in task 1.0b by adding the missing `import java.util.*;`. After that repair, all 20
non-constructor owners resolve. An owner that resolves via neither route is logged and skipped
(validated §14 item 14); this is RISK-006's failure mode, and the corpus shows it is not hypothetical.

The earlier plan seeded `java.lang` by default as defense-in-depth; a measurement on 2026-08-21 reversed
that, and on 2026-08-28 the decision reverses once more — **not** because that measurement was wrong, but
because the objection it raised is removed by D10. The measurement stands, and it is now the statement of
why seeding **alone** is forbidden. It has two halves. First, `generic_new` does not need the seed: all
**seven** of its specs with a `java.lang` `call()` owner carry an explicit `import java.lang.*;`
(`CharSequence_UndefinedHashCode`, `Comparable_CompareToNull`, `Comparable_CompareToNullException`,
`Long_BadParsingArgs`, `Object_MonitorOwner`, and — owner `Iterable` — `ListIterator_Set` and
`Map_UnsafeIterator`; an earlier draft listed six and wrongly included `CharSequence_NotInSet`, whose
`call()` owner is `Set`, `CharSequence` appearing only in `args()`). Second, seeding moves the frozen
`jca`/`jca_android` sets: `String`, owner of the two `RandomStringPassword.mop` pointcuts, is the only
unresolved owner in either set, and resolving it **under LENIENT** makes `String#valueOf` match every
overload — 74 call sites over 3 corpus APKs, only 17 of them woven, the other 57 propagated to their
callers by the transitive axis.

**What changes is the second half, and only under LENIENT.** The seed ships bound to the STRICT policy of
D10 and the FQN parameter resolution of D11, which is exactly what makes those 57 unmatchable: a STRICT
target compares the full Soot signature, so `valueOf(Object)` stops matching `valueOf(int)`. Any one of the
three parts alone still makes the measurement worse than the hole it repairs — that is the whole content of
RISK-011, which is therefore **re-aimed rather than retired**: it now forbids the *partial* seed, not the
seed. See INV-ANA-40 (the seeding rule and scope boundary (c)) and `docs/20260821_handoff_gh69_coringas.md`.

**The unresolved-owner enumeration was re-run on 2026-08-28, not quoted.** INV-ANA-40 required re-running
it rather than citing the 2026-08-21 figure, because gh109 grew `jca_android` in the interval. Method:
declared `call()` owners parsed from the `.mop` corpora, diffed against the owners the extractor actually
emits (`evidence/after_{jca,jca_android,generic_new}.csv`). Result: `jca` declares 23 `call()` owners and
emits 22; `jca_android` declares 47 and emits 46; `generic_new` declares 21 and emits 21. In both
JCA-family sets the one missing owner is `String`, from `RandomStringPassword.mop`. So the seed's blast
radius is exactly the two pointcuts D10 makes STRICT — no other owner in either set changes resolution
status, and `generic_new` is untouched because it has nothing left to resolve.

Two consequences recorded here before the repair moved into scope, **both still standing**: (i) writing
the owner as an FQN in the pointcut (`call(... java.lang.String.valueOf(Object))`) does **not** work either
— the visitor keys its map by simple name, so a dotted owner never matches and would need its own rule.
This is why the seed, and not a spec rewrite, is the route: `RandomStringPassword.mop` could not be
repaired from the spec side even if the file were editable, and under the gh101 freeze it is not.
(ii) Resolution being import-driven means a non-JDK owner reached only through a wildcard import cannot be
resolved by `Class.forName` at all (RISK-006), which an explicit-import convention would fix. The seed does
not change this: it adds one implicit package, it does not make resolution classpath-driven.

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

**D9 — Constructor targets are mapped to `<init>` inside this change, in a phase of their own.** An
earlier draft suppressed them (log+skip, "mapping `new`→`<init>` is out of scope") and treated the
suppression as a required guard. That was right about the guard and wrong about the scope, for three
reasons that only became visible once the effect was measured.

First, **the defect is not in `generic_new`, it is in the frozen `jca`**. The extractor already emits 18
constructor rows for `jca`, collapsing into 11 of its 68 pairs, and none of them has ever resolved —
`TargetResolver.java:53` compares names by equality and Soot calls every constructor `<init>`. The
published ruler has never counted a constructor call site, `new SecretKeySpec(...)` included. Suppressing
the `generic_new` three would have left that untouched and shipped the asymmetry: three suppressed on one
side, eighteen silently dead on the other. (An earlier draft of this paragraph also cited task 5.8 as an
open reconciliation the asymmetry would worsen; 5.8's premise was refuted by measurement on 2026-08-28 —
see D12 — and that clause is withdrawn. The asymmetry argument does not depend on it.)

Second, **this change is already at that code site**. Boundary (b) obliges the extractor to decide what
`Owner.new(..)` means; the grammar routes it through `MethodPointCut` and the visitor must branch either
way. Mapping instead of suppressing is the same site and the same branch, plus a keyword rename that
cannot be ambiguous. The test infrastructure it needs is task 1.0, which this change creates because the
extractor module has none.

Third, **the approval cost is now enumerated rather than feared**. The concern was moving the frozen
ruler. Measured on the fixture behind `G_paridade_targets`: 11 constructor call sites in 10 methods, 8 of
them already flagged, so exactly **two** methods change on the direct axis (21 → 23), both nameable and
both plainly correct. That is precisely the form gh101 requires of a repair to shared code — "its effect
on the frozen set is enumerated rather than assumed absent."

**Why a phase of its own, and not a branch of task 1.3.** The change's review story is "the JCA path is
untouched; parity is preserved". This repair deliberately moves JCA values, and if a parity gate goes red
with both landed at once, nothing separates the subtype matcher from the constructor mapping. So the work
is sequenced after phase 4 has the subtype path green on a real scene, carries its own before/after gate,
and re-baselines the two fixtures with the enumeration written into the commit. Evidence stays separable
without a second change.

**What stays out.** The transitive effect is not estimated — a new seed propagates to its callers, and
only a real run says how far. The phase measures it rather than predicting it.

**D10 — The STRICT criterion for a seeded owner: a target whose owner resolves ONLY via the implicit
`java.lang` seed is STRICT; every other target keeps the policy it has.** This is the decision that makes
D5's seed admissible, and it was chosen on 2026-08-28 from three candidates, each measured before being
compared. Its blast radius is exactly **2 pointcuts in `jca` and 2 in `jca_android`** — both in
`RandomStringPassword.mop` — and **0 in `generic_new`**, which follows directly from the re-run enumeration
in D5: `String` is the only owner in either JCA-family set that the seed resolves, and `generic_new` has no
unresolved owner for the seed to reach. The rule is stated over *how the owner resolved*, not over what it
is named, and that is deliberate: it binds the strictness to the new resolution path, so a target that
already resolved cannot silently change policy underneath the frozen ruler.

The two rejected candidates are recorded with the number that refutes each, so neither is re-proposed:

- **"Every `java.lang` owner is STRICT."** Simpler to state, and wrong: `generic_new` declares `Object+`,
  `Comparable+` and `CharSequence+` as `call()` owners with `import java.lang.*;`, and those pointcuts
  write `(..)` for their parameters. A STRICT target compares the full Soot signature, so under this rule
  they would match nothing and the `generic_new` direct axis — the load-bearing measurement of this whole
  change (RISK-004) — would collapse. The rule would break the set it is supposed to leave alone.
- **"An explicit, non-`..` parameter list is STRICT."** The most principled-sounding of the three, since it
  honours what the spec author wrote, and refuted by scale: measured over the corpora, it selects **112 of
  the 142 `call()` pointcuts in `jca`** and **185 of 222 in `jca_android`** (`generic_new`: 21 of 89). That
  is not a criterion for one repaired target, it is a wholesale conversion of the frozen ruler from LENIENT
  to STRICT, arriving as a side effect of an unrelated repair. The gh101 freeze doctrine admits a repair to
  shared code whose effect on the frozen set is enumerated; it does not admit this one, whose effect is the
  frozen set.

**D11 — `getParams()` resolves parameter types to FQN, and its effect is measured in ISOLATION before the
seed lands.** STRICT compares the full Soot signature, so D10 is unexpressible while `getParams` consults
only the explicit-import map and leaves parameters with the simple names the pointcut wrote (`Map`,
`Object`) beside an owner that resolved (`java.util.Map`). D11 is therefore a prerequisite of D10, not a
companion to it.

It also carries the one hazard this change knew about before the repair entered scope, and the sequencing
exists to catch it: the parameter list participates in `MopMethod.equals`/`hashCode`, so resolving it may
**merge** entries that differ today only in how two specs spelled the same type — moving the `jca` count of
120 for a reason that has nothing to do with the owner fix. A combined measurement could not tell the two
apart. So the phase measures D11 alone first and enumerates whatever moves, then lands D5+D10 and
enumerates that separately. This is the form D9 already used on the frozen ruler (21 → 23, with both
signatures named), applied to a repair with two independent causes instead of one.

**D13 — The bytecode scan honours `MatchPolicy.STRICT`; it was lenient unconditionally, and that
made D10 ineffective.** Found while implementing phase 5.6, and repaired there. The scan reduced
every resolved target to a `className#methodName` key
(`RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan`) and matched invokes against that key
set. A key set *is* the lenient policy: `java.lang.String#valueOf` readmits `valueOf(int)` and
`valueOf(long)` however carefully `resolveInScene` excluded them. So a STRICT target was strict on
the transitive-seed axis and lenient on the direct one — and since D8 seeds the reverse BFS with the
direct set, the false positives reached the transitive axis anyway. D10 would have bounded nothing.

The method's javadoc had asserted the opposite, that "a STRICT source still benefits from LENIENT
bytecode scan because `methodRef` alone cannot reliably reconstruct the full Soot signature at the
call site". That is false for the parameter list: `SootMethodRef.parameterTypes()` returns the types
the invoke instruction's own descriptor carries, which is exactly as reliable as the class and the
name read from the same descriptor. The claim was never measured; it is now, and the javadoc is
corrected rather than left standing beside the code that contradicts it.

**The repair.** A STRICT target is withheld from the key set and matched per invoke against
`ref.parameterTypes()`, by a helper (`paramsMatchAtCallSite`) that mirrors
`TargetResolver.paramsMatch` — the two must agree, or the direct and transitive axes would disagree
about the same call site. Subtype targets already had their own per-invoke bucket for the analogous
reason (a key set is a flattened hierarchy), so this is the same shape applied to the second axis.

**Measured, on `cryptoapp` with a single `String.valueOf` target supplied through a signature file
so the policy is the only variable**: LENIENT gives **24** direct callers and 402→427 on the
transitive axis; STRICT gives **9**. The 15 that fall away are the `valueOf(int)`/`valueOf(long)`
call sites RISK-011 enumerates. That is the bound doing its work, and it is the reason RISK-011
closes as satisfied rather than as avoided.

**What it moves in what already shipped: nothing.** Before phase 5.6 no `.mop` directory produced a
STRICT target at all — `MopSpecsTargetSource` emitted every target LENIENT — so no published
measurement passed through this branch. The other STRICT producer is `SignatureFileTargetSource`,
reached only by `scripts/check_signature_file_subset.py`, whose gate asserts `STRICT ⊆ LENIENT`;
tightening STRICT shrinks the left side and the containment still holds (measured after the repair:
|LENIENT|=37, |STRICT|=27, diff=0, PASS). That script's comment claiming "the bytecode-scan layer is
LENIENT by construction (D7)" is stale and corrected with it.

**D12 — Task 5.8 is refuted by measurement, not deferred.** The task asserted that two synced specs record
different counts for the same token in the same corpus — `instrumentation/spec.md` saying **64** where this
change says **71** — and asked for a reconciliation. The two numbers count **different artifacts**, and
both are correct. `DemandCounter` (`rvsec-instrumentation-dexlib2/grammar-tests/.../util/DemandCounter.java`)
maintains two independent signals: `countMop` over the `.mop` corpora (four: `aspect`, `jca`, `generic`,
`generic_new`) and `countCompiledAj` over the committed
`empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj` snapshot (three, post-JavaMOP).
`docs/aspectj_grammar_coverage.md` already records the `T+ in call() owner` row with **both**: SourceDemand
`0,0,0,71` and PipelineDemand `0,0,64`. Reproduced on 2026-08-28 with `DemandCounter`'s own regex,
`[A-Za-z0-9_]\+\.`: the `generic_new` `.mop` source gives **71** (all 71 in `call()` owner position, over
an 89-`call(` denominator) and the compiled `.aj` gives **64**. So this change's 71 *is* the pinned source
count, already asserted by `MatrixIntegrityTest.testSourceDemandCountsReproducible`; INV-INS-93 is correct
as written and is not touched, and no delta spec for the `instrumentation` capability is created. What
remains is a phrasing defect in the main spec — `openspec/specs/instrumentation/spec.md:1504` writes
"§4.O — `T+` in `call()` owner (R11: 64 sites generic_new)" without naming the unit, which is what misled
the task's author — and repairing that sentence is the whole of task 5.8's residue.


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
| Unit (extractor) | Parse generic_new → the N fixed in advance (**69** pairs under a `+`-aware owner key, **68** otherwise; **zero** ctor-skip notices — D9 maps constructors instead; 0 unresolved-owner skips after the 1.0b repair; 24/27 specs covered), flags set; jca → 120, flags false | JUnit on `UsedJcaMethodsVisitor`/`JavamopFacade` with the 27+23 specs | ~4 |
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
