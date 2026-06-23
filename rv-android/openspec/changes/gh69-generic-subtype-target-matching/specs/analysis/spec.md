## Purpose

GATOR computes method reachability for an APK and marks each method with `reachesTarget` /
`directlyReachesTarget` — whether it reaches (transitively or directly) a **target method**: an API
the active JavaMOP spec set monitors. The target set is produced by the `rvsec-mop-extractor` (parsing
the `.mop` specs into `MopMethod` entries) and resolved against the Soot `Scene` by the gator
`TargetResolver`/`RvsecAnalysisClient`. This capability covers **how a `.mop` pointcut owner is matched
to the classes and methods seen at an APK's call sites**.

Until now that matching is **exact-FQN**: a `.mop` pointcut contributes a target only if its owner is
an explicitly imported class whose simple name appears in the `imports` map, and a call site matches
only if its declaring class FQN and method name are string-equal to a resolved target. This fits the
JCA spec style (explicit imports, exact `Cipher.getInstance(...)` pointcuts) but fails the
`generic_new` style, which declares owners by **type hierarchy** and uses wildcard imports and
wildcard method names. The concrete consequence: the extractor emits **0** targets for the 27
`generic_new` specs (vs **120** for JCA), so `reachesTarget=false` for every method of every APK and
the generic reachability sweep is meaningless.

This change adds **subtype/wildcard-aware target matching**. The extractor learns to resolve owners
declared via wildcard imports, to strip the `+` subtype operator and flag `includeSubtypes`, and to
keep wildcard method names (`add*`) as patterns. The matcher learns to match a call site when its
declaring type **is-a-subtype-of** the declared super-type — using Soot's `FastHierarchy.canStoreType`
at the moment of match (decision **A2**), rather than pre-expanding the super-type to its
implementers (decision A1, rejected: `getImplementersOf` omits sub-interfaces, so interface-typed call
sites like `java.util.List.iterator` against `Iterable+.iterator` would be missed). The output JSON
schema is unchanged — `reachesTarget`/`directlyReachesTarget` keep their shape and only become more
correct; per-spec attribution stays at runtime (decision **B**). The JCA exact path is preserved
byte-for-byte (no `+`, no wildcard method names → `includeSubtypes=false` → exact `equals`), keeping
INV-ANA-35 / `MopSpecsParityTest` green.

This capability builds on the `TargetMethod` / `MatchPolicy` / `TargetResolver` / `MopSpecsTargetSource`
abstraction introduced by gh60-targets-core (INV-ANA-33, INV-ANA-35).

## Data Contracts

### Input
- `mopDir: path` — JavaMOP spec directory, `jca` (exact, explicit imports) or `generic_new` (wildcard
  imports, `+` owners, wildcard method names). Source: `RVStaticAnalysisConfig.mop_dir` → `-clientParam mopDir=`.
- `Scene` — the Soot whole-program scene of the APK (call sites, declaring classes/types). Source: GATOR/Soot 4.7.1 (INV-ANA-18).

### Output
- `TargetMethod{className, methodName, params, signature, policy, includeSubtypes, nameIsPattern}` —
  resolved by `MopSpecsTargetSource.load()` from `MopMethod`. Consumer: `TargetResolver.resolveInScene`.
- `reachability[].methods[].{reachable, reachesTarget, directlyReachesTarget}: bool` — per-method flags
  in the GATOR JSON. **Key set unchanged**; only values change. Consumer: `static_analysis_parser.py`
  (Python boundary) and ape `MopData.java` (`opt*`-tolerant).

### Side-Effects
- **[Soot Scene]**: each declared target owner FQN is force-resolved into the Scene at HIERARCHY level
  before `canStoreType` is queried.
- **[Log]**: when a target owner cannot be resolved into the Scene, a warning is logged and that owner
  degrades to exact matching (no silent false-negative).

### Error
- No new exceptions. An unresolvable target super-type degrades to exact `equals` matching with a
  logged warning rather than throwing or silently dropping the target.

## Invariants

- **INV-ANA-40**: The `rvsec-mop-extractor` (`UsedJcaMethodsVisitor`) MUST extract a non-empty target
  set from spec sets that declare owners via wildcard imports and the `+` subtype operator. For each
  `call(...)` pointcut: wildcard-import packages MUST be registered (the `isAsterisk()` import MUST NOT
  be discarded); a trailing `+` on the owner MUST be stripped and the resulting `MopMethod` MUST carry
  `includeSubtypes=true`; the simple owner name MUST be resolved to an FQN via explicit imports first
  and `Class.forName(pkg + "." + simple)` over the wildcard packages second. The implicit `java.lang`
  package MUST be seeded by default (Java imports it implicitly; the owners `Object+` and `Comparable+`
  appear in `generic_new` without an explicit `import java.lang.*`). A wildcard method name MUST be
  preserved as a pattern with `nameIsPattern=true`; the patterns actually present in `generic_new` are
  `add*`, `remove*`, `retain*`, `clear*`, `put*`, `offer*`, `write*` and the bare `*`
  (`call(* Iterator.*(..))`) — a trailing `*` matches by prefix and the bare `*` matches every method of
  the owner (prefix `""`). The `MopMethod` identity (`equals`/`hashCode`) MUST include `includeSubtypes`
  and `nameIsPattern`, so two pointcuts that differ only by `+` or by name-pattern are not silently
  deduplicated in the extractor's `Set<MopMethod>`. For `generic_new` (27 specs) the emitted set MUST
  have cardinality > 0 (currently 0). All 21 `generic_new` owners are JDK classes
  (`java.lang`/`util`/`io`/`net`); an owner that cannot be resolved MUST be logged and skipped.

- **INV-ANA-41**: `MopSpecsTargetSource.load()` MUST propagate `includeSubtypes` and `nameIsPattern`
  from each `MopMethod` to the corresponding `TargetMethod`. A target derived from a JCA spec (no `+`,
  no wildcard method name) MUST carry `includeSubtypes=false` and `nameIsPattern=false`.

- **INV-ANA-42**: When `includeSubtypes=true`, both target match points — `TargetResolver.resolveInScene`
  (which seeds the reverse call-graph BFS) and `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan`
  (the direct bytecode scan) — MUST match a call site by `nameMatches(pattern) &&
  FastHierarchy.canStoreType(callSiteDeclaringType, declaredSuperType)` evaluated against the **declared
  super-type**, NOT against pre-resolved exact keys. To make this possible the declared
  `Set<TargetMethod>` (which carries the super-type FQN and the two flags) MUST be propagated to **both**
  match points: today `ReachabilityEngine` and `findDirectTargetCallersByBytecodeScan` receive only the
  resolved `Set<SootMethod>` (which has lost the declared owner and flags), so their contract MUST be
  extended to also carry the `Set<TargetMethod>`. `nameMatches` MUST be evaluated **before**
  `canStoreType` (cheap name short-circuit before the hierarchy query). The exact (`!includeSubtypes`)
  targets MUST retain the existing `Set<String>` `class#method` key path (a **hybrid** scan), so the JCA
  O(1) lookup, performance, and byte-for-byte parity (INV-ANA-35) are unchanged. The predicate MUST
  match interface→interface (e.g. `java.util.List <: java.lang.Iterable`) so interface-typed call sites
  are covered. When `includeSubtypes=false`, both points MUST use the exact `equals(className) &&
  equals(methodName)` path unchanged.

- **INV-ANA-43**: Before `FastHierarchy.canStoreType` is queried, each declared target owner FQN MUST
  be force-resolved into the Soot `Scene` at HIERARCHY level. Because GATOR runs Soot with
  `allow_phantom_refs=true`, `forceResolve` of an unresolvable type yields a **phantom** `SootClass`
  that satisfies `Scene.containsClass` yet carries no hierarchy. Empirically (Soot 4.7.1, run against the
  gator fat jar) such a phantom resolves at `BODIES` level, so `checkLevel(HIERARCHY)` passes and
  `canStoreType` returns a **definite `false`** — it does **not** throw, and it silently masks a
  false-negative. Therefore the degrade criterion MUST be `isPhantom()` or `resolvingLevel() < HIERARCHY`
  on the declared super-type — **not** merely `containsClass`. An owner that is absent or phantom MUST
  degrade to exact `equals` matching and the degradation MUST be logged (no silent false-negative).
  `canStoreType` MUST NOT be called with a phantom or absent type.

- **INV-ANA-44**: The GATOR JSON output schema MUST be unchanged by this capability — no new, renamed,
  or removed keys. The key set of a `generic_new` run MUST be identical to that of a `jca` run; only
  the boolean values of `reachesTarget`/`directlyReachesTarget` differ. INV-ANA-35 (JCA byte-for-byte
  parity in `MopSpecsTargetSource.load()` vs the historical `loadMopSignatures`) MUST remain satisfied.

## ADDED Requirements

### Requirement: Subtype/Wildcard-Aware Target Matching for Hierarchy-Declared Spec Sets (FR04, FR06)

The GATOR target-matching pipeline MUST match a call site to a `.mop` pointcut when the pointcut
declares its owner by **type hierarchy** (the `+` subtype operator) and/or via **wildcard imports**
and **wildcard method names**, in addition to the existing exact-FQN matching for explicitly-declared
owners. The pipeline spans the extractor, `MopSpecsTargetSource`, `TargetResolver`, and the
bytecode-scan complement.

A method `a()` MUST transition from `reachesTarget=false` to `reachesTarget=true` when it reaches
(directly or transitively) a call site whose declaring type is-a-subtype-of the super-type declared
in a spec pointcut and whose method name matches the (possibly wildcard) declared name. The match MUST
be decided by `FastHierarchy.canStoreType(callSiteDeclaringType, declaredSuperType)` at match time
(decision A2). The output JSON schema MUST NOT change (INV-ANA-44); per-spec attribution remains a
runtime concern (the `.mop` handlers log `RVSEC ... ::: <SpecName>`, parsed by `rv-coverage`).

The JCA spec style (explicit imports, exact `Class.method` pointcuts, no `+`, no wildcard method
names) MUST continue to use the exact-`equals` path with no behavioral change (INV-ANA-35 parity).

#### Scenario: Extractor loads targets from a wildcard/subtype generic spec
- **WHEN** the extractor parses `generic_new/Collection_UnsynchronizedAddAll.mop` containing `import java.util.*;` and `call(boolean Collection+.addAll(..))`
- **THEN** it MUST emit a `MopMethod` with `className="java.util.Collection"`, `methodName="addAll"`, and `includeSubtypes=true`
- **AND** over all 27 `generic_new` specs the emitted target set MUST have cardinality > 0 (currently 0)
- **AND** the same extractor run on the 23 `jca` specs MUST still emit 120 targets, each with `includeSubtypes=false` and `nameIsPattern=false`

#### Scenario: Wildcard method names are preserved as patterns (including the bare `*`)
- **WHEN** a pointcut declares `call(* Collection+.add*(..))`
- **THEN** the emitted `MopMethod` MUST carry `nameIsPattern=true` with stored name pattern `add*`
- **AND** the matcher MUST match call-site method names `add` and `addAll` but MUST NOT match `remove`
- **AND** every trailing-`*` pattern present in `generic_new` — `add*`, `remove*`, `retain*`, `clear*`, `put*`, `offer*`, `write*` — MUST be preserved and matched by prefix
- **AND** the bare pattern `*` (`call(* Iterator.*(..))`, exact owner `Iterator`) MUST match every method name of the owner (prefix `""`): this match-all is the intended AspectJ semantics, not a degenerate case, and MUST NOT be rejected/forced to `false`

#### Scenario: Flags propagate from MopMethod to TargetMethod (INV-ANA-41)
- **WHEN** `MopSpecsTargetSource.load()` maps the extracted `MopMethod` set to `TargetMethod` entries
- **THEN** each `TargetMethod` derived from a `generic_new` `+`/wildcard pointcut MUST carry `includeSubtypes=true` (and `nameIsPattern=true` for wildcard names) — the flags MUST NOT be dropped at this boundary
- **AND** each `TargetMethod` derived from a `jca` spec MUST carry `includeSubtypes=false` and `nameIsPattern=false`
- **AND** `TargetMethod.equals`/`hashCode` MUST include both flags so two targets differing only by a flag are not collapsed in the `Set<TargetMethod>`, while every constructor call site (`MopSpecsTargetSource`, `SignatureFileTargetSource`, tests) MUST default both flags to `false` so the JCA/signature-file paths stay on exact matching (INV-ANA-35)

#### Scenario: Subtype match on a concrete library type
- **WHEN** an APK method calls `java.util.ArrayList.addAll(Collection)` and the active target is `Collection+.addAll` with `includeSubtypes=true`
- **THEN** `FastHierarchy.canStoreType(ArrayList, java.util.Collection)` MUST return `true`
- **AND** the calling method MUST be marked `directlyReachesTarget=true` and `reachesTarget=true`

#### Scenario: Interface-typed call site (A2 covers what A1 misses)
- **WHEN** an APK call site is `java.util.List.iterator()` (declaring type is the interface `List`) and the active target is `Iterable+.iterator` with `includeSubtypes=true`
- **THEN** `FastHierarchy.canStoreType(java.util.List, java.lang.Iterable)` MUST return `true` and the call site MUST match
- **AND** this case MUST match even though `getActiveHierarchy().getImplementersOf(Iterable)` does not contain `List` (the rejected A1 pre-expansion would miss it)

#### Scenario: Predicate applied at both match points
- **WHEN** the target set contains a `includeSubtypes=true` entry
- **THEN** `TargetResolver.resolveInScene` MUST seed the reverse-BFS by matching scene methods via `canStoreType` against the declared super-type
- **AND** `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` MUST match invokes via `canStoreType` against the declared super-type, NOT against a set of pre-resolved exact `class#method` keys

#### Scenario: Target super-type force-resolved into the Scene with graceful degradation
- **WHEN** the declared target owner `java.io.Closeable` is not yet loaded as a `SootClass` in the Scene
- **THEN** the matcher MUST force-resolve `java.io.Closeable` at HIERARCHY level before calling `canStoreType`
- **AND** because Soot runs with `allow_phantom_refs=true`, the matcher MUST treat a resolved-but-**phantom** owner (or one whose `resolvingLevel() < HIERARCHY`) as unresolved — `containsClass` alone is insufficient, since `canStoreType` would return a definite (wrong) `false` rather than throwing
- **AND** IF a declared owner remains absent or phantom at match time THEN that owner MUST degrade to exact `equals` matching and the degradation MUST be logged as a warning (no silent false-negative)

#### Scenario: Output schema unchanged across spec sets
- **WHEN** GATOR writes the static-analysis JSON for an APK against `generic_new`
- **THEN** the set of JSON keys MUST be identical to a `jca` run on the same APK (only `reachesTarget`/`directlyReachesTarget` boolean values differ)
- **AND** the Python parser boundary (`static_analysis_parser.py`) and ape `MopData.java` MUST require no key-mapping change

#### Scenario: Non-target call site stays unmatched — no subtype over-match (negative E2E)
- **NOTE** `generic_new` includes `Object+` owners (`Object_MonitorOwner.mop`: `wait`/`notify`/`notifyAll`), so **every** call-site declaring type IS a subtype of some declared owner. Non-matches are therefore decided on the **method-name axis**, not the type axis. (The earlier `String.length()` "not a subtype" framing was incorrect: `String <: Object`.)
- **WHEN** a method invokes a call site whose declaring type is a subtype of a declared owner but whose method name does NOT match that owner's declared pattern/name — e.g. `java.lang.String.length()` (`String <: Object+` but `length` ∉ {`wait`,`notify`,`notifyAll`}), or `java.util.ArrayList.remove(...)` against `Collection+.add*`
- **THEN** the method MUST be reported `reachesTarget=false` and `directlyReachesTarget=false`
- **AND** `nameMatches` MUST reject the name **before** `canStoreType` is consulted, so a non-matching name short-circuits regardless of subtype
- **AND** subtype/pattern widening MUST introduce zero spurious positives on the IT APK: on a small APK with an enumerable set of target call sites, the `directlyReachesTarget=true` set MUST correspond to genuine subtype+name matches. Where exhaustive ground-truth labelling is impractical this is verified by **spot-checks + sampled inspection** (an honest, bounded criterion — not a completeness proof)

#### Scenario: JCA exact path preserved (parity)
- **WHEN** the matcher resolves a JCA target such as `Cipher.getInstance(String)` (`includeSubtypes=false`)
- **THEN** matching MUST use exact `equals(className) && equals(methodName)` with no hierarchy query
- **AND** `MopSpecsParityTest` MUST pass byte-for-byte against the gh57 baseline (INV-ANA-35), including the `cryptoapp.mop` 16-target count
