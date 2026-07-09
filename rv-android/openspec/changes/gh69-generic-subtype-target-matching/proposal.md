## Why

GitHub Issue: #69.

The GATOR static-analysis pipeline computes `reachesTarget`/`directlyReachesTarget` by matching the
monitored API call sites of an APK against the target methods declared in a JavaMOP spec set. This
matching is **exact-FQN** and was written for the JCA spec style (explicit imports + exact
`Class.method` pointcuts). The `generic_new` spec set uses a different style — wildcard imports
(`import java.util.*;`), owners declared by **subtype** (`call(* Collection+.addAll(..))`), and
**wildcard method names** (`add*`). Against `generic_new` the pipeline loads **0 targets** and reports
`reachesTarget=false` for every method of every APK, making the static analysis useless for defining
the generic experiment dataset.

This is confirmed empirically: the `rvsec-mop-extractor` extracts **0 methods** from the 27
`generic_new` specs versus **120** from `jca`; **27/27** generic specs use wildcard imports and
**71/89** `call(...)` pointcuts use a `+` subtype owner. Full root-cause analysis and an adversarial
validation are in `docs/20260617_sa_generic_new.md` (§1–§14) and `docs/20260611_sweep_generic_new_400.md`
(§10–§11). The blocked reachability sweep (49/400) waits on this fix.

## What Changes

- **Extractor (`rvsec-mop-extractor`)** — teach `UsedJcaMethodsVisitor` to handle the generic style:
  register wildcard-import packages (stop discarding `isAsterisk()` imports), strip the `+` subtype
  suffix from owners and flag `includeSubtypes`, resolve simple owner names to FQN via explicit
  imports first and `Class.forName` over wildcard packages second (all 21 owners are JDK classes),
  and preserve wildcard method names (`add*`) as a pattern rather than a literal. New `MopMethod`
  flags: `includeSubtypes`, `nameIsPattern`. **Coverage boundary (documented, accepted)**: only
  `call(...)` pointcuts are extracted — the 3 specs whose sole pointcut is `staticinitialization(Owner+)`
  and the 3 constructor `call(Owner.new(..))` pointcuts remain without static targets (net 24/27 specs
  with ≥1 target; see design Non-Goals and INV-ANA-40 scope boundary).

- **Matcher (`rvsec-gator`, `commons` + `client`)** — make target matching subtype/wildcard-aware
  via decision **A2**: carry `includeSubtypes` + name-pattern on `TargetMethod`, and at the two match
  points (`TargetResolver.resolveInScene` and `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan`)
  replace `equals(className)` with `FastHierarchy.canStoreType(callSiteType, declaredSuperType)` and
  `equals(methodName)` with pattern matching, **when** `includeSubtypes` is set (the name check runs
  **first** — cheap short-circuit before the hierarchy query; see design D-API). Interface-typed call
  sites (e.g. `java.util.List.iterator`) are matched because `canStoreType` covers interface→interface.
  This requires propagating the declared `Set<TargetMethod>` (super-type FQN + flags) to **both** points
  — today `ReachabilityEngine` and the bytecode scan receive only the resolved `Set<SootMethod>`, so the
  scan becomes **hybrid** (exact `class#method` keys for JCA owners + `canStoreType` for subtype owners).

- **Scene resolution of the target super-type** — before building the `FastHierarchy`, force-resolve
  each declared target owner into the Soot `Scene` (`forceResolve(fqn, HIERARCHY)`); guard on
  `isPhantom()`/`resolvingLevel()` (not just `containsClass`) and, when a type is phantom or absent,
  **degrade to exact `equals` + log** (no silent false-negative). This closes the one high-risk gap:
  under `allow_phantom_refs=true` an unresolvable owner becomes a phantom and `canStoreType` returns a
  silent (wrong) `false` — verified empirically against Soot 4.7.1 (it does **not** throw).

- **Output schema — UNCHANGED.** No new or renamed JSON keys. `reachesTarget`/`directlyReachesTarget`
  keep their shape; they only become *more correct* (more `true` on specs with `+`). Per-spec
  attribution stays at runtime (the `.mop` handlers log `RVSEC ... ::: <SpecName>` → `rv-coverage` →
  `errors.csv`); the static layer only needs the aggregated boolean (decision **B**).

- **Rebuild** — two JARs in order: `mvn install` the extractor first (it is a compile-scope
  dependency bundled into `rvsec-analysis-client.jar`), then rebuild the gator `client`.

The JCA path is untouched: JCA owners carry no `+` and no wildcard method names, so the predicate
falls through to today's exact `equals` (`includeSubtypes=false`). This is **not** a breaking change.

## Capabilities

### New Capabilities
<!-- None. This change modifies the existing analysis capability; it introduces no new spec domain. -->

### Modified Capabilities
- `analysis`: the "Unified Static Analysis" requirement (FR04–FR06) — target matching gains
  subtype/wildcard awareness for spec sets that declare owners by hierarchy. New invariants
  (INV-ANA-40+) for extractor extraction of wildcard/`+`/pattern owners, the A2 `canStoreType`
  predicate at both match points, target-super-type Scene resolution with graceful degradation, and
  the output-schema-invariance guarantee. Builds on the `TargetMethod`/`MatchPolicy`/`TargetResolver`
  abstraction and INV-ANA-33/INV-ANA-35 introduced by **gh60-targets-core** (dependency, see Impact).

## Impact

- **Modules / repos**: `rvsec-mop-extractor` (extractor JAR), `rvsec-gator` `commons` + `client`
  (`rvsec-gator.jar` + `rvsec-analysis-client.jar`, copied to `rv-android/lib/gator/` on `mvn install`).
  No Python module changes — `rv-static-analysis` consumes the unchanged JSON through its single
  parser boundary (`static_analysis_parser.py`); the ape `MopData.java` parser is `opt*`-tolerant.
- **Requirements**: FR04 (WTG), FR05 (GUI elements), FR06 (method reachability) — the reachability
  target-set computation. Relates to INV-ANA-15 (coverage denominator uses `reaches_target`),
  INV-ANA-18 (Soot 4.7.1), BUG-INV-ANA-19 (bytecode-scan complement gains the subtype predicate).
- **Dependency on gh60-targets-core** (issue #60, ARCHIVED 2026-06-17): the `TargetMethod`/`MatchPolicy`/
  `TargetResolver`/`MopSpecsTargetSource` abstraction and INV-ANA-33/35 are introduced there. The
  code is already in the gator source; this change extends it. INV-ANA-35 parity (JCA byte-for-byte)
  MUST be preserved.
  - **Sync/archive ordering — constraint now SATISFIED (as of 2026-07-06)**: gh60 (INV-ANA-33..38) and
    gh66 `gator-wtg-flowcontainer-perf` (INV-ANA-39) are **already archived and synced** — the synced
    `openspec/specs/analysis/spec.md` now contains INV-ANA-33/35, so this change's references resolve and
    the earlier "gh60 MUST sync first / dangling reference" hazard no longer applies. gh69 claims
    INV-ANA-40..44, which are **free** in the synced spec and unclaimed by any active change. Two residual
    Phase-6 checks remain (not blockers for `/opsx:apply`): (a) confirm 40-44 are still free and INV-ANA-33/35
    still present at archive time; (b) reconcile a pre-existing sync anomaly — two changes archived *after*
    gh66 took higher numbers (gh70-wtg-reachability-sharing: INV-ANA-45; gh72-logcat-diagnostic-events:
    INV-ANA-46/47/48) yet the synced inventory jumps 39 → 46,47,48, so gh70's INV-ANA-45 is **absent** from
    the synced spec. gh69's insertion at 40-44 is therefore non-contiguous but collision-free. See RISK-008.
- **Invariant preserved**: `FlowgraphRebuilder` arity guard (WTG SPARK cgDelegation) lives in source
  (`FlowgraphRebuilder.java:212-225,704-717`) — including `sootandroid` in the rebuild keeps it.
- **Downstream (out of scope)**: the `generic_new` reachability sweep and the generic dataset definition
  are a separate later change. **Corpus updated 2026-07-09**: the generic experiment will draw APKs from
  the new dataset repo (`rvsec-dataset`, 219 curated apps), superseding the 400-APK sweep corpus;
  `docs/20260611_sweep_generic_new_400.md` remains the procedure reference. Caveat for that downstream
  change: with quasi-universal owners (`Object+`, `Iterable+`) `reachesTarget` saturates near-true across
  APKs, and decision B (no per-owner attribution in the JSON) means the dataset filter cannot statically
  discriminate universal from selective targets — the downstream change must plan around this (per-owner
  side data or runtime attribution).
