## Context

GATOR marks each APK method with `reachesTarget`/`directlyReachesTarget` against the target methods of
the active JavaMOP spec set (FR04–FR06). The matching pipeline is exact-FQN and import-explicit, written
for the JCA spec style. The `generic_new` spec set declares owners by type hierarchy (`Collection+`),
uses wildcard imports (`java.util.*`), and wildcard method names (`add*`). Result: the extractor emits
**0** targets for `generic_new` (vs 120 for `jca`), so `reachesTarget=false` everywhere.

This design implements **decision A2** (subtype match at match-time via `FastHierarchy.canStoreType`),
keeps the **output schema unchanged** (decision B), and scopes the change to **matching + rebuild +
tests** (decision C). It builds on the `TargetMethod`/`MatchPolicy`/`TargetResolver`/`MopSpecsTargetSource`
abstraction from gh60-targets-core (INV-ANA-33/35) and the Soot 4.7.1 baseline (INV-ANA-18). Full
ideation and adversarial validation: `docs/20260617_sa_generic_new.md` §1–§14.

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
| INV-ANA-40 (extractor wildcard/`+`/pattern) | `UsedJcaMethodsVisitor.visit(ImportDeclaration\|MethodPointCut)` | `UsedMethodsGenericTest` (parse generic_new → exact N pinned at implementation, ref. enumeration 67 distinct call() pairs); extractor run asserts 27→N (24 specs with ≥1 target), 23→120 |
| INV-ANA-41 (flag propagation) | `MopSpecsTargetSource.load()` + `MopMethod`/`TargetMethod` ctors | `MopSpecsTargetSourceTest` (generic flags true, jca flags false) — **task 2.4b** |
| INV-ANA-42 (A2 predicate, both points + cascade) | `TargetMatching` in `TargetResolver.resolveInScene` + `ReachabilityEngine`/`findDirectTargetCallersByBytecodeScan` carrying `Set<TargetMethod>` (hybrid scan) | `TargetMatchingTest` (class→iface, **iface→iface `List<:Iterable`**, bare `*`); `RvsecAnalysisClient` IT |
| INV-ANA-43 (Scene force-resolve + phantom-aware degrade) | `TargetMatching.forceResolveTargets` + `isPhantom`/`resolvingLevel` guard + degrade branch | `TargetMatchingTest` (absent type **and phantom owner** → equals + warn) |
| INV-ANA-44 (schema invariance) | no JSON writer change; assert key-set equality | JSON key-set diff generic vs jca; `MopSpecsParityTest` (INV-ANA-35) |

## Goals / Non-Goals

**Goals:**
- Extractor emits N>0 targets for `generic_new`, with `includeSubtypes`/`nameIsPattern` set correctly.
- Both match points are subtype/wildcard-aware via `canStoreType`, covering interface→interface.
- Target super-types are loaded into the Scene before `canStoreType`; absent types degrade gracefully.
- Output JSON schema unchanged; JCA parity (INV-ANA-35) preserved byte-for-byte.

**Non-Goals:**
- Running the 400-APK `generic_new` sweep or defining the generic dataset (separate later change).
- Per-spec `reachesTarget` in the static output (decision B — per-spec stays at runtime).
- Handling owner subtype-matching in the **parameter** position (JCA `Object+` parameters already
  handled by `getParams`; out of scope).
- Mitigating quasi-universal specs (`Object+`, `Iterable+`, `Comparable+`) inflating `reachesTarget` —
  accepted as correct behavior here; any dataset-level exclusion is a downstream concern.
- Extracting **non-`call()` pointcut shapes** (documented static false-negatives, bounded): the 3 specs
  whose only pointcut is `staticinitialization(Owner+)` (`Collection_HashCode`,
  `Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission`) emit zero static targets, and
  the 3 constructor pointcuts `call(Owner.new(..))` (`ServerSocket.new` ×2, `TreeMap.new`) are not
  extracted (Soot `<init>` mapping not implemented). Net static coverage is 24/27 specs; the runtime
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
owner before building the `FastHierarchy` — **ordering requirement**: `forceResolveTargets` MUST run
before the first `Scene.v().getOrMakeFastHierarchy()` call anywhere in the run (Soot caches the
`FastHierarchy`; types resolved after it is materialized are not incorporated), and the IT logs whether
the hierarchy was already built when `forceResolveTargets` ran; then, at match time, guard on `isPhantom()` /
`resolvingLevel() < HIERARCHY` (NOT merely `containsClass`) — if phantom/absent, degrade that owner to
exact `equals` and log a warning once per owner. A `try/catch` is **not** the right mitigation (the call
does not throw for natural phantoms — it would be dead code). Alternative (do nothing) rejected: silent
false-negatives. This is the highest-risk point — validated in the IT against the real
`RvsecAnalysisClient` scene, where a degrade on a `generic_new` owner is a **hard gate** (blocks the sweep).

**D3 — Output schema unchanged (B descartada).** Per-spec attribution already lives at runtime (the
`.mop` handlers log `RVSEC ... ::: <SpecName>`, parsed by `rv-coverage` into `errors.csv`); coverage
uses the aggregated `reachesTarget` as denominator (`result_processor.py:402-435`). Adding a per-spec
`targetSummary` to the JSON is unnecessary and the destructive variant would silently break the ape
`opt*` parser. Alternative (additive `targetSummary`) rejected as unneeded complexity (P1).

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
second.** All 21 `generic_new` owners are JDK classes (`java.lang`/`util`/`io`/`net`), resolvable at
the extractor's runtime. An owner that resolves via neither is logged and skipped (no JDK-external
owner exists today, validated §14 item 14).

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
   (`Set<TargetMethod>`) and the resolved `targetMethods` (`Set<SootMethod>`), but `ReachabilityEngine`'s
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
| Unit (extractor) | Parse generic_new → exact pinned N targets (ref. 67 distinct call() pairs; 3 ctor-skip notices; 24/27 specs covered), flags set; jca → 120, flags false | JUnit on `UsedJcaMethodsVisitor`/`JavamopFacade` with the 27+23 specs | ~4 |
| Unit (matcher) | `canStoreType` class→iface, **iface→iface (`List<:Iterable` — the only case that distinguishes A2 from A1)**; name patterns `add*`…`write*` and bare `*`; non-trailing pattern → `equals`; absent-type **and phantom owner** degrade | JUnit on `TargetMatching` with a minimal Scene | ~7 |
| Source | `MopSpecsTargetSource.load()` propagates flags (generic true / jca false) | `MopSpecsTargetSourceTest` (INV-ANA-41 — task 2.4b) | ~2 |
| Parity | JCA byte-for-byte (`MopSpecsTargetSource.load` vs historical) | `MopSpecsParityTest` (INV-ANA-35) | existing |
| Integration | 1 APK against generic_new: `reachesTarget>0`; `canStoreType` in real `RvsecAnalysisClient` scene; JSON key-set == jca run; **negative — a subtype-receiver call with a non-matching name (`ArrayList.remove` vs `add*`; `String.length` vs `Object+.wait/notify`) stays `reachesTarget=false` (name-axis, since `Object+` makes every type a subtype)** | gator E2E on a small APK | ~3 |

## Open Questions

- None blocking. The quasi-universal-spec dataset treatment (exclude `Object+`/`Iterable+` from the
  dataset filter, or keep) is explicitly deferred to the downstream sweep/dataset change — it does not
  affect this matcher design.
