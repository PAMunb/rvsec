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
  flags: `includeSubtypes`, `nameIsPattern`.

- **Matcher (`rvsec-gator`, `commons` + `client`)** — make target matching subtype/wildcard-aware
  via decision **A2**: carry `includeSubtypes` + name-pattern on `TargetMethod`, and at the two match
  points (`TargetResolver.resolveInScene` and `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan`)
  replace `equals(className)` with `FastHierarchy.canStoreType(callSiteType, declaredSuperType)` and
  `equals(methodName)` with pattern matching, **when** `includeSubtypes` is set. Interface-typed call
  sites (e.g. `java.util.List.iterator`) are matched because `canStoreType` covers interface→interface.

- **Scene resolution of the target super-type** — before building the `FastHierarchy`, force-resolve
  each declared target owner into the Soot `Scene` (`forceResolve(fqn, HIERARCHY)`); when a type is
  still absent, **degrade to exact `equals` + log** (no silent false-negative). This closes the one
  high-risk gap surfaced by the spike (`canStoreType` returns a non-answer when a type is not loaded).

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
- **Dependency on gh60-targets-core** (issue #60, OPEN): the `TargetMethod`/`MatchPolicy`/
  `TargetResolver`/`MopSpecsTargetSource` abstraction and INV-ANA-33/35 are introduced there. The
  code is already in the gator source; this change extends it. INV-ANA-35 parity (JCA byte-for-byte)
  MUST be preserved.
  - **Mandatory archive/sync order — gh60 → gh66 → gh69**: three changes stack deltas on the same
    `analysis` capability (gh60: INV-ANA-33..38; gh66 `gator-wtg-flowcontainer-perf`: INV-ANA-39; gh69:
    INV-ANA-40..44). This change's spec delta references INV-ANA-33/35 and the `TargetMethod`/
    `MatchPolicy`/`TargetResolver` abstraction, which live only in gh60's not-yet-synced delta
    (`openspec/specs/analysis/spec.md` currently contains neither). If gh69 is `/opsx:sync`-ed/archived
    before gh60, the synced spec carries dangling references to INV-ANA-33/35. **gh60 MUST sync/archive
    first**; gh66 is independent of gh69 (does not reference 33/35) but should sync in number order
    (gh60→gh66→gh69) to avoid merge conflicts on the shared capability. See RISK-008. This bites only at
    Phase 6 (archive), not at `/opsx:apply`.
- **Invariant preserved**: `FlowgraphRebuilder` arity guard (WTG SPARK cgDelegation) lives in source
  (`FlowgraphRebuilder.java:212-225,704-717`) — including `sootandroid` in the rebuild keeps it.
- **Downstream (out of scope)**: the 400-APK `generic_new` reachability sweep and the generic dataset
  definition are a separate later change (`docs/20260611_sweep_generic_new_400.md`).
