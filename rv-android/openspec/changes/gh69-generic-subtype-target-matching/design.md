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
| `MopMethod` (extractor model) | Carry the two new flags | — | fields `includeSubtypes`, `nameIsPattern` |
| `TargetMethod` (gator commons) | Carry the two new flags | `MopMethod` | fields `includeSubtypes`, `nameIsPattern` |
| `MopSpecsTargetSource.load()` | Propagate flags `MopMethod → TargetMethod` | `Set<MopMethod>` | `Set<TargetMethod>` |
| `TargetMatching` (new helper, gator client) | `nameMatches(pattern,name)` + `canStoreType(sub,sup)` + `forceResolveTargets(scene)` | `TargetMethod`, Soot types | boolean / resolved types |
| `TargetResolver.resolveInScene` | Seed reverse-BFS via subtype predicate when `includeSubtypes` | `Set<TargetMethod>`, Scene | `Set<SootMethod>` |
| `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` | Direct scan via subtype predicate against declared super-type | invokes, targets | callers `Set<SootMethod>` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-ANA-40 (extractor wildcard/`+`/pattern) | `UsedJcaMethodsVisitor.visit(ImportDeclaration\|MethodPointCut)` | `UsedMethodsGenericTest` (parse generic_new → N>0); extractor run asserts 27→N>0, 23→120 |
| INV-ANA-41 (flag propagation) | `MopSpecsTargetSource.load()` + `MopMethod`/`TargetMethod` ctors | `MopSpecsTargetSourceTest` (generic flags true, jca flags false) |
| INV-ANA-42 (A2 predicate, both points) | `TargetMatching.canStoreType` in `TargetResolver.resolveInScene` + `findDirectTargetCallersByBytecodeScan` | `TargetMatchingTest` (class→iface, iface→iface); `RvsecAnalysisClient` IT |
| INV-ANA-43 (Scene force-resolve + degrade) | `TargetMatching.forceResolveTargets` + degrade branch | `TargetMatchingTest` (absent type → equals + warn) |
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

## Decisions

**D1 — Subtype match via `canStoreType` at match-time (A2), not pre-expansion (A1).** A1 expands each
super-type to its implementers via `getActiveHierarchy().getImplementersOf(...)` and matches by exact
key. The spike (`out/spike_subtype_hierarchy/`) proved A1 is incomplete: `getImplementersOf(Iterable)`
omits sub-interfaces (`java.util.List` absent), so an interface-typed call site `List.iterator()`
against `Iterable+.iterator` is missed. A2 asks `canStoreType(List, Iterable)=true` at the call site
and is correct by construction (the call-site type is always in the Scene). **Recorded as an ADR.**

**D2 — Force-resolve target super-types into the Scene + degrade-to-exact-with-log.** `canStoreType`
returns a non-answer when a type is absent from the Scene (spike: `ByteArrayInputStream <: Closeable :
one side NOT in Scene`). The call-site type is always loaded, but the declared super-type may not be.
Mitigation: `Scene.v().forceResolve(fqn, SootClass.HIERARCHY)` for each declared target owner before
building the `FastHierarchy`; if a type is still absent at match time, degrade that owner to exact
`equals` and log a warning. Alternative (do nothing) rejected: silent false-negatives. This is the
highest-risk point — validated in the IT against the real `RvsecAnalysisClient` scene.

**D3 — Output schema unchanged (B descartada).** Per-spec attribution already lives at runtime (the
`.mop` handlers log `RVSEC ... ::: <SpecName>`, parsed by `rv-coverage` into `errors.csv`); coverage
uses the aggregated `reachesTarget` as denominator (`result_processor.py:402-435`). Adding a per-spec
`targetSummary` to the JSON is unnecessary and the destructive variant would silently break the ape
`opt*` parser. Alternative (additive `targetSummary`) rejected as unneeded complexity (P1).

**D4 — Name-pattern matching: trailing-`*` prefix semantics.** The only wildcard method names in
`generic_new` are `add*`, `remove*`, `retain*` (trailing `*`). `nameMatches(pattern, name)` is
`pattern.endsWith("*") ? name.startsWith(prefix) : name.equals(pattern)`. No general glob needed (P1).

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

### `boolean TargetMatching.matches(SootMethodRef callSite, TargetMethod t, FastHierarchy fh)`
- **Pre**: `callSite.getDeclaringClass()` is resolved in the Scene; `t` is a loaded target.
- **Behavior**: if `!t.includeSubtypes` → `callSite.declaringClass.name.equals(t.className) &&
  nameMatches(t, callSite.name)` (exact path, unchanged). If `t.includeSubtypes` → `nameMatches(t,
  callSite.name) && fh.canStoreType(callSite.declaringClass.type, superType(t))` where `superType(t)`
  is the resolved `RefType` of `t.className`; if `superType(t)` is absent from the Scene → fall back to
  exact `equals` and log once per owner.
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
5. `findDirectTargetCallersByBytecodeScan` applies `matches(...)` per invoke against declared
   super-types (not pre-resolved keys), recovering literal subtype invocations (BUG-INV-ANA-19).
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
- **Quasi-universal owners** (`Object+`, `Iterable+`) inflate `reachesTarget` → correct per the spec;
  any dataset-level exclusion is a downstream decision, not a matcher concern.
- **Extractor↔gator rebuild coupling** → mitigated by the mandatory 2-step order (D6).

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (extractor) | Parse generic_new → N>0 targets, flags set; jca → 120, flags false | JUnit on `UsedJcaMethodsVisitor`/`JavamopFacade` with the 27+23 specs | ~4 |
| Unit (matcher) | `canStoreType` class→iface, iface→iface (`List<:Iterable`); name pattern `add*`; absent-type degrade | JUnit on `TargetMatching` with a minimal Scene | ~5 |
| Parity | JCA byte-for-byte (`MopSpecsTargetSource.load` vs historical) | `MopSpecsParityTest` (INV-ANA-35) | existing |
| Integration | 1 APK against generic_new: `reachesTarget>0`; `canStoreType` in real `RvsecAnalysisClient` scene; JSON key-set == jca run; **negative — a non-target call site stays `reachesTarget=false` (no subtype over-match)** | gator E2E on a small APK | ~3 |

## Open Questions

- None blocking. The quasi-universal-spec dataset treatment (exclude `Object+`/`Iterable+` from the
  dataset filter, or keep) is explicitly deferred to the downstream sweep/dataset change — it does not
  affect this matcher design.
