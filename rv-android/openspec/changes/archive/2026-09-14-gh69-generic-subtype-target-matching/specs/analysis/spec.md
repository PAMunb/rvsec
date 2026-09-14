## Purpose

GATOR computes method reachability for an APK and marks each method with `reachesTarget` /
`directlyReachesTarget` — whether it reaches (transitively or directly) a **target method**: an API
the active JavaMOP spec set monitors. The target set is produced by the `rvsec-mop-extractor` (parsing
the `.mop` specs into `MopMethod` entries) and resolved against the Soot `Scene` by the gator
`TargetResolver`/`RvsecAnalysisClient`. This capability covers **how a `.mop` pointcut owner is matched
to the classes and methods seen at an APK's call sites**.

Until now that matching is **exact-FQN**: a `.mop` pointcut contributes a target only if its owner is
an explicitly imported class whose simple name appears in the `imports` map, and a call site matches
only if its declaring class FQN and method name are string-equal to a resolved target.

**The gap is in the pointcut grammar, not in any one corpus.** AspectJ admits four constructions that
this pipeline silently discards: the `+` subtype operator on an owner, an asterisk import
(`import java.util.*;`) as the owner's only declaration, a trailing `*` in a method name (`add*`), and
the constructor form `Owner.new(..)`. A pointcut using any of them contributes **no** target, with no
diagnostic — the target simply is not there, and every method downstream of it reads `false`. This
capability therefore states the requirement over the **constructions**, and any spec set that uses them
inherits it. Measured across the four sets present in the tree (2026-08-28):

| spec set | specs | `+` owners | `*` method names | `Owner.new(..)` |
|---|---|---|---|---|
| `jca` (frozen ruler) | 23 | 0 | 0 | **25** |
| `jca_android` (production successor) | 48 | **2** | 0 | **39** |
| `generic` | 118 | 0 | 0 | **80** |
| `generic_new` | 27 | **71** | **15** | 3 |

Two readings follow. First, **the defect is live in the set that is in production**: `jca_android`
declares `Key+.getEncoded` (`KeySpec.mop`, added 2026-08 by gh109) and `SecretKey+.getEncoded`
(`SecretKeySpec.mop`), and both load zero targets today; the constructor form is dead in **all four**
sets. Second, `generic_new` is the corpus that exercises all four constructions at once, which is what
makes it the **verification fixture** of this capability — its cardinality figures below are fixture
values, not the requirement. The requirement is that a pointcut using any of the four constructions
resolves to a target.

This change adds **subtype/wildcard-aware target matching**, for any spec set. The extractor learns to
resolve owners declared via wildcard imports, to strip the `+` subtype operator and flag
`includeSubtypes`, to keep wildcard method names (`add*`) as patterns, and to map `Owner.new(..)` to
`<init>`. The matcher learns to match a call site when its
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
  **Reachability caveat**: no orchestrator path sets `mop_dir` today — neither `rv-experiment` nor
  `rv-platform` passes it, so `RVStaticAnalysisConfig` always falls back to
  `rvsec-mop/src/main/resources/jca` (`config.py:199-208`) and the static analysis runs against `jca`
  regardless of `--specification-set`. `--specification-set generic` maps to `resources/generic` (118
  synthetic `FSM*` specs), a different corpus, not to `generic_new`. This capability is therefore
  exercised through `rv-static-analysis --mop-dir .../generic_new` directly; wiring spec-set → `mopDir`
  is a sibling repair (`docs/20260821_plano_correcao_analise_estatica.md`, D2), not part of this change.
- `Scene` — the Soot whole-program scene of the APK (call sites, declaring classes/types). Source: GATOR/Soot 4.7.1 (INV-ANA-18).

### Output
- `TargetMethod{className, methodName, params, signature, policy, includeSubtypes, nameIsPattern}` —
  resolved by `MopSpecsTargetSource.load()` from `MopMethod`. Consumer: `TargetResolver.resolveInScene`.
- `reachability[].methods[].{reachable, reachesTarget, directlyReachesTarget}: bool` — per-method flags
  in the GATOR JSON. **Key set unchanged**; only values change. Consumers of this **raw** artefact are
  three independent readers, none of which tolerates a key change: the Python boundary
  `static_analysis_parser.py:98-99` (the single parse point in `rv-static-analysis`); the repo gate and
  sweep scripts under `scripts/`; and `aperv-tool`, which parses `<apk>.json` itself and imports nothing
  from `rv_static_analysis` (`analysis/static_artifact.py:261,270-271,293,359`;
  `tools/aperv/derive_mop_artifact.py:421-422,1029,1158`). `derive_mop_artifact.py:422` is the least
  forgiving — `method.get("reachesTarget") is True` turns a rename into a silent `False`, not an error.
  The ape `MopData.java` is **not** a consumer of this artefact: it reads the *derived* `*.mop.json`,
  where the key has already been renamed `reachesTarget` → `reachesMop`
  (`derive_mop_artifact.py:1158`), and it hard-rejects any document without `formatVersion == 1`
  (`<workspace-rv>/ape/src/main/java/com/android/commands/monkey/ape/utils/MopData.java:207-213`). Its
  `opt*` tolerance is therefore no argument for schema safety here.
  Beyond the readers, two **value**-stability gates already watch these booleans and are not part of
  this change's own test plan: `tests/parity/test_reachability_parity.py:156` (`G_paridade_targets`)
  freezes the *set* of signatures carrying `reachesTarget=true` against a committed baseline, and
  `tests/parity/test_historical_methods_coverage.py:134` pins three methods at
  `directlyReachesTarget=true`. Both run against the default `mopDir` (`jca`), so the JCA-untouched
  premise of this capability is what keeps them green.

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
  package MUST be seeded **third and last**, and every target whose owner resolves ONLY through that seed
  MUST carry `MatchPolicy.STRICT`. The two halves of that rule are inseparable and MUST NOT be implemented
  apart: seeding alone re-introduces the over-match that scope boundary (c) enumerates, and the STRICT
  policy has nothing to bind to without the seed. A **third** part is a prerequisite of the second and is
  stated in INV-ANA-40 below: `getParams()` MUST resolve pointcut parameter types to FQN, since a STRICT
  target is compared by its full Soot signature and cannot be expressed while its parameters carry the
  simple names the pointcut wrote.

  The seed changes nothing for `generic_new`, and that is a measured property rather than an intention:
  all **seven** of its specs with a `java.lang` `call()` owner — `Object_MonitorOwner`,
  `Comparable_CompareToNull`, `Comparable_CompareToNullException`, `CharSequence_UndefinedHashCode`,
  `Long_BadParsingArgs`, and (owner `Iterable`) `ListIterator_Set` and `Map_UnsafeIterator` — carry an
  explicit `import java.lang.*;` (list corrected 2026-08-21: an earlier draft named six and wrongly
  included `CharSequence_NotInSet`, whose `call()` owner is `Set`; `CharSequence` appears there only in
  `args()`). Their owners resolve at the first step and never reach the seed, so none of them becomes
  STRICT — which matters, because they declare `(..)` parameters and STRICT would stop them matching.
  An owner whose package is registered by no import and which the seed does not resolve either MUST be
  logged and skipped — never silently dropped.
  Resolvability is import-driven, **not** a property of being a JDK class: `CharSequence_NotInSet.mop`
  declared owner `Set+` while importing only `java.io`/`java.lang`/`java.nio`, and so resolved to nothing.
  That spec is repaired within this change (one added `import java.util.*;`); after the repair all 20
  non-constructor owners resolve and the extractor MUST report **zero** unresolved-owner skips for
  `generic_new`. A wildcard
  method name MUST be
  preserved as a pattern with `nameIsPattern=true`. (`nameIsPattern` is derivable from the stored name —
  a Java identifier cannot contain `*` — and is kept to record extractor intent at the boundary, not
  because it discriminates; see design D7 caveat.) The patterns actually present in `generic_new` are
  `add*`, `remove*`, `retain*`, `clear*`, `put*`, `offer*`, `write*` and the bare `*`
  (`call(* Iterator.*(..))`) — a trailing `*` matches by prefix and the bare `*` matches every method of
  the owner (prefix `""`). The `MopMethod` identity (`equals`/`hashCode`) MUST include `includeSubtypes`
  and `nameIsPattern`, so two pointcuts that differ only by `+` are not silently deduplicated in the
  extractor's `Set<MopMethod>` (the corpus contains exactly one such pair: `Iterator.next` in
  `Map_UnsafeIterator` vs `Iterator+.next` in `ListIterator_Set`). The **verification fixture** for this invariant is
  `generic_new` (27 specs), chosen because it exercises all four constructions at once; the figures that
  follow are fixture values, not the requirement, and a spec set that uses none of the constructions is
  conformant with an empty delta. Over that fixture the
  emitted set MUST have cardinality equal to a number **fixed before implementation**, not pinned to
  whatever the implementation happens to emit: the enumeration over the corpus gives **69 distinct
  `call()` pairs** when the `+` is part of the owner key and **68** when it is not, **including** the 3
  constructor pointcuts, which boundary (b) requires be mapped to `<init>` rather than skipped. (The
  pre-D9 figures were 67/66 with constructors excluded; they are superseded and MUST NOT be used as the
  gate. The two constructor pairs are `(java.net.ServerSocket, <init>)` and `(java.util.TreeMap, <init>)`;
  both survive the `+`-less key, because the `ServerSocket+` entries carry the method names `accept`,
  `bind` and `setSoTimeout` — dropping the `+` merges the owners, not the pairs. The single pair the
  `+`-less key does merge is `Iterator`, used as `Iterator.next` in `Map_UnsafeIterator` and
  `Iterator+.next` in `ListIterator_Set`, which is the whole of the 69 → 68 difference. An earlier
  draft read 67 here by subtracting a `ServerSocket` merge that does not happen.) The unit test MUST state which key it uses and assert that number; parameter
  granularity may raise it, and any such raise MUST be explained rather than absorbed. All **21** distinct
  `call()` owners are JDK classes (`java.lang`/`util`/`io`/`net`) and all 21 carry targets under boundary
  (b) — the pre-D9 count of 20 excluded `TreeMap`, which appears only in `call(TreeMap.new(Map))` and now
  resolves; 23 owners exist in total counting the two
  `staticinitialization`-only owners `Serializable`/`URLConnection`, which are out of scope (see below).
  (The log-and-skip rule for an unresolvable owner is stated once, above.)

  **Scope boundary (documented static false-negatives, accepted):** this invariant covers `call(...)`
  pointcuts only. (a) Three specs whose ONLY pointcut is `staticinitialization(Owner+)` —
  `Collection_HashCode`, `Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission` —
  contribute **zero** static targets (the pointcut never reaches `visit(MethodPointCut)`), so they can
  never set `reachesTarget` even though the runtime monitor fires on class-load. (b) Constructor pointcuts
  `call(Owner.new(..))` MUST be extracted as `MopMethod(owner, "<init>")`, **not** logged and skipped.
  The javamop grammar routes `Owner.new(..)` through `MethodPointCut`
  (`javamop/src/main/javacc/javamop/parser/aspectj_parser/aspectj.jj:1730-1737`, where `"." <NEW>` sets
  `owner = retType` and `name = "new"`), so the pointcut already reaches the visitor; what it emits today
  is the literal name `new`, and Soot names every constructor `<init>`, so such a target matches nothing.
  The mapping is unambiguous — `new` is a Java keyword, no method may be named it — and it is the whole
  repair: no GATOR-side change is required, because `TargetResolver.resolveInScene` compares names by
  equality and `SignatureFileTargetSource` already accepts `<init>` through its `([^(]+)` capture.
  **This corrects a live defect in the frozen `jca` set, not only a `generic_new` gap.** The extractor
  already emits constructor targets for `jca`: 18 signature rows collapsing into **11 of its 68 pairs**
  (`SecureRandom`, `KeyPair`, `CipherInputStream`, `CipherOutputStream`, `SecretKeySpec`,
  `IvParameterSpec`, `GCMParameterSpec`, `PBEKeySpec`, `PBEParameterSpec`, `DHGenParameterSpec`,
  `HMACParameterSpec`), and all 11 resolve to nothing today. The published ruler has therefore never
  counted a single constructor call site — including `new SecretKeySpec(...)` and
  `new IvParameterSpec(...)`, which are central to JCA misuse.
  Per the freeze doctrine established by gh101 — "shared code MUST NOT branch on the active
  specification set. A repair that applies equally to both sets is admissible, and its effect on the
  frozen set is **enumerated** rather than assumed absent" — the repair is admissible and the enumeration
  is required. Measured on the frozen fixture
  (`modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`, 106 methods): 11 constructor call
  sites (`SecretKeySpec` ×5, `IvParameterSpec` ×4, `SecureRandom` ×2) in 10 methods, of which **8 are
  already flagged** by other targets. Exactly **two** methods change on the direct axis —
  `CryptoUtils.createSecretKeyFromBytes` and `CryptographyActivity.executeSecretKeyOperation` — taking
  `directlyReachesTarget` from 21 to 23. The transitive axis is not estimated here and MUST be measured
  by a real run, since a new seed propagates to its callers.
  Cardinality consequences: `generic_new` goes from 67 to **69** distinct pairs with a `+`-aware owner
  key (66 → **68** without), and from 20 to **21** owners carrying targets — `TreeMap` appears only in a
  constructor pointcut and had no target before. The `jca` triple does **not** move: 120/68/22 stays
  120/68/22, because those rows already exist; only the emitted name changes from `new` to `<init>`.
  Net coverage: **24/27 specs** with ≥1 static target — a figure that holds only because
  `CharSequence_NotInSet.mop` is repaired within this change. Without the added `import java.util.*;` its
  owner `Set` resolves to nothing, the spec contributes zero targets, and net coverage is 23/27.

  (d) **Pointcut narrowing is discarded — the one false-*positive* direction.** The extractor keys on
  owner + method name only; the `&& args(...)`, `&& target(...)` and `&& condition(...)` conjuncts that
  narrow a pointcut are dropped. Measured over `generic_new`: 40 of the 88 `call(` lines carry a `&&`
  conjunct, 14 of them an `args(...)`. Re-measured **by event** rather than by line (the right unit — a
  conjunct routinely continues onto following lines): **55 of the 58 `call(` events, 95%**, carry some
  discarded restriction.
  **The `args()` axis recovers nothing, and the example this boundary used to give was the worst case to
  pick.** Of the 22 events with `args(...)`, only **2** narrow a type rather than merely binding a
  variable, and neither changes the resolved `SootMethod` set:
  `call(* Set+.add(..)) && args(CharSequence) && !args(String) && !args(CharBuffer)` is a test on the
  *argument at the call site*, which neither `resolveInScene` (which sees only `SootMethod`) nor the
  extractor can apply — and the pair `(Collection+, add*)` from `Collection_UnsynchronizedAddAll` already
  covers `Set.add` with no restriction at all, so the union erases any narrowing even in principle. The
  other, `Collections.newSetFromMap`, has a single overload.
  **Where the recoverable precision actually lives is `target()`-of-type**: 22 of its 57 occurrences name
  a type (8 positive, 14 negated), and it is the only restriction class applicable at the layer where
  matching happens — both `TargetResolver.resolveInScene` and the bytecode scan already hold the receiver
  type. Two pairs survive the union: `CharSequence+.equals`/`hashCode` (whose `!target(String)` matters —
  over 3 corpus APKs, **100%** of `equals`/`hashCode` call sites on a `CharSequence` have receiver
  `java.lang.String`, so the static target is entirely false-positive there) and the non-`java.io` part of
  `Closeable+.close`. Applying just those two shrinks the direct seed by 11–41% (measured: pindroid
  153→119, lesserpad 37→22, moneytracker 171→152). That is a separate change, not this one.
  This is accepted (matching is LENIENT by construction,
  INV-ANA-35), but it MUST be read together with the quasi-universal owners (`Object+`, `Iterable+`):
  the two compound, and the resulting saturation of `reachesTarget` is what the downstream dataset
  change has to plan around. Boundaries (a)-(c) understate the true target set; (d) overstates it.

  (e) **A corpus property, not a property of this capability: `reachesTarget` is degenerate over the
  `generic_new` fixture.** It is recorded here because that fixture is what the gates run against, and a
  reader would otherwise mistake the saturation for a matcher defect. It is neither — it follows from
  *which* APIs those 27 specs monitor (adding to a container, iterating, closing a stream), not from how
  the matcher works, and it says nothing about a spec set that declares owners by hierarchy over a
  narrower API family. Measured over 8 corpus APKs (827,443 call sites): the transitive flag reaches
  **84–94%** of app methods over this fixture against 11–47% over `jca`, and on 4 of the 8 it exceeds the
  app's own `reachable` fraction. Owner filtering MUST NOT be added to repair it — dropping 34 of the 69
  pairs was measured not to move the flag on any medium or large APK (quicknote 1752→1752, mupen
  2342→2340) — because there is nothing here to repair. The consequence for the gates is narrow and
  practical: over this fixture the load-bearing assertion is `directlyReachesTarget` (2–12%, discriminating)
  and `reachesTarget` is smoke only. **No consumer changes under this capability**: `aperv-tool` keeps reading
  `reachesTarget`, because (i) the count model's size term is a pre-registration item with no default
  (`estimators/count_glm.py:240-243` raises `FreezeItemUnset` when it is omitted) and both columns are
  already emitted side by side (`analysis/static_artifact.py:414-415`), so the degenerate offset cannot be
  inherited silently; (ii) the `hot`/`cold` handler verdict has no in-repo code consumer — it reaches CSV,
  and its readers run against `jca`, which this change does not move; and (iii) `sa_methods_reaches_mop` is
  pinned normatively to `reachesTarget` by the synced `campaign-analysis` capability, so migrating it
  belongs to a change against **that** capability, not this one. Gating on the spec set is not available in
  any case: `<apk>.json` carries no spec-set provenance (`package`, `mainActivity`, `reachability`,
  `windows`, `transitions`, `components`).

  (c) **`jca`/`jca_android`: `RandomStringPassword.mop` MUST contribute its two static targets — this is a
  requirement to repair, no longer a boundary to accept.** It is listed here, among the scope boundaries,
  because that is where it lived until 2026-08-28 and a reader tracing RISK-013 will look for it here;
  what follows states the repair and keeps the measurement that constrains it.

  **The defect.** The spec's two pointcuts name the owner `String` while the file imports only
  `java.util.stream.IntStream` and three `br.unb.cic.mop.*` packages — `java.lang.String` being implicit
  in Java but not for the visitor, which had no `else` and no log at `UsedJcaMethodsVisitor:70-77`. The
  woven aspect does carry both pointcuts
  (`rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879` — the full path matters:
  the ~40 generated copies elsewhere in the tree are 664–733 lines and do not contain these lines). That
  is weaving evidence by construction rather than an observed runtime trace, and it is sufficient: the
  aspect advises call sites the static layer never marked. **This is what RISK-013 (High) is about**, and
  it damages the published measurement ruler rather than a diagnostic: `jca` is the frozen set, so every
  `cov_reaches_target` published from it was computed over **22 of its 23 specs**. No published violation
  count is wrong — the harm is in the denominator.

  **The enumeration, re-run 2026-08-28 rather than quoted** (the earlier text required this, because
  gh109 grew `jca_android` after the 2026-08-21 measurement). Declared `call()` owners diffed against the
  owners the extractor emits: `jca` declares 23 and emits 22; `jca_android` declares 47 and emits 46;
  `generic_new` declares 21 and emits 21. In both JCA-family sets the single missing owner is `String`,
  from this one spec. So the repair's blast radius is exactly these two pointcuts.

  **The repair MUST have three parts and they MUST land together**, because each one alone makes the
  measurement worse than the hole:
  (i) **owner visibility** — the implicit `java.lang` seed of the resolution rule stated above;
  (ii) **`MatchPolicy.STRICT` for any target whose owner resolved only through that seed**;
  (iii) **`getParams()` resolving pointcut parameter types to FQN**, without which (ii) cannot be
  expressed, since STRICT compares the full Soot signature.
  A fourth condition is **not** part of the repair but is a precondition of it, and MUST hold for
  (ii) to bound anything: **both** match points MUST honour `MatchPolicy.STRICT`. The direct
  bytecode scan reduced every resolved target to a `className#methodName` key, and such a key *is*
  the lenient policy — it readmits exactly the overloads STRICT excludes — so a STRICT target was
  bounded on the transitive-seed axis and unbounded on the direct one, and through the reverse BFS
  seeded by the direct set (INV-ANA-64) the false positives returned to the transitive axis anyway.
  A STRICT target MUST therefore be withheld from the key set and matched per invoke against the
  parameter types the call instruction's own descriptor carries
  (`SootMethodRef.parameterTypes()`), by a comparison that agrees with the one
  `TargetResolver.resolveInScene` performs. Measured on `cryptoapp` with a single `String.valueOf`
  target, the policy being the only variable: **24** direct callers under LENIENT against **9**
  under STRICT (design D13).
  The reason (i) alone is forbidden is measured and MUST be preserved by any future reading of this
  requirement: seeding under LENIENT (class+name, signature ignored) makes `String#valueOf` match every
  overload — over 3 corpus APKs, 74 call sites of `String.valueOf`/`toCharArray` of which only **17**
  match the woven signatures (`valueOf(Object)`, `toCharArray()`), leaving 57 false positives propagated
  to their callers by the transitive axis, on the spec set that is the published ruler. Part (ii) is
  what makes those 57 unmatchable, and is therefore the condition on which (i) is admissible at all.

  **The cardinality consequence MUST be enumerated, not presumed.** The seed takes `jca` 120→122 and
  `jca_android` 119→121 on the owner axis alone; part (iii) may additionally **merge** `MopMethod` entries
  that differ today only in how two specs spelled the same type, moving the `jca` count for a reason
  unrelated to the owner fix. The two causes MUST be measured separately — (iii) in isolation first, then
  (i)+(ii) — and each delta enumerated by signature, in the form decision D9 established for the
  constructor repair (21 → 23, with both signatures named). A combined measurement cannot attribute a
  movement to its cause, and an unenumerated re-baseline of the frozen set is what the gh101 doctrine
  forbids. `cryptoapp.apk` carries **0** `String.valueOf`/`toCharArray` call sites of the woven
  signatures, so `BaselineComparisonIT` and the `cryptoapp` fixture are predicted not to move — a
  prediction that MUST be verified against the real run rather than assumed.

  **Measured 2026-08-28, and the prediction held only on the axis it was made about.** The
  extractor triple went `jca` 120/68/22 → **122/70/23** and `jca_android` 209 → **211**, in both
  cases by exactly the two `RandomStringPassword` rows —
  `java.lang.String#valueOf(java.lang.Object)` and `java.lang.String#toCharArray()` — with no row
  removed and no rows merged anywhere (row count equals distinct-key count on both sides, which is
  the check that matters, since the parameter list participates in `MopMethod` identity).
  `generic_new` stayed at 72. The isolated (iii) measurement that preceded it changed 1 parameter
  list in `jca` (`SSLContext.init`, gaining the `javax.net.ssl` prefix on `KeyManager[]` and
  `TrustManager[]`), 1 in `jca_android` and 16 in `generic_new`, and added or removed no row in any
  set — so the merge hazard is measured absent rather than assumed absent. On the frozen `cryptoapp`
  fixture the **direct axis did not move** (23 → 23), which is the repair working rather than the
  repair being inert: the APK has no app-level call site of either woven signature, and under a
  lenient seed it would have gained the false ones. The **transitive axis moved by four** — the
  default constructors of `MainActivity`, `CipherActivity`, `CryptographyActivity` and
  `MessageDigestActivity`, which reach `String.valueOf(Object)` through the framework call graph.
  That movement was **attributed by isolation, not assumed**: the same APK run against a copy of
  `jca` with `RandomStringPassword.mop` removed reproduces 120 signatures, 0 STRICT, 33 reaching and
  23 direct, so the whole delta belongs to that one specification.

  **The silence is discharged either way.** Before the repair the log-and-skip rule turned a drop with no
  `else` and no log into a named skip; after it, `String` resolves and the skipped-owner log for `jca`
  and `jca_android` MUST be empty. What MUST NOT happen is the middle state: a seed that resolves the
  owner while leaving the target LENIENT. Evidence: `docs/20260821_handoff_gh69_coringas.md`; design
  **D5** (the seed), **D10** (the STRICT criterion, with the two candidates it was chosen over) and
  **D11** (the isolation-measurement sequencing); risk body in `risk-register.md` RISK-013.

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

  **Cost bound (NFR04).** Widening the predicate removes the `equals(fqn)` fast-reject that
  `resolveInScene` relies on today and enlarges the seed set it produces, so this capability MUST NOT
  make the analysis materially slower. The bound is stated over the **sum** of the three stages the
  change touches — `TargetResolver.resolveInScene`, the direct bytecode scan, and the reverse BFS that
  consumes the seed set (`ReachabilityEngine.multiSourceBfs`) — which together MUST run within **2×**
  their `jca` baseline on the same APK. Each stage MUST additionally be **reported** against its own
  baseline, so that a regression is attributable; a per-stage ratio above 2× is a finding to enumerate
  rather than a failure, and the clause below is the enumeration.

  **The per-stage 2× this invariant used to require is not what the measurement supports, and the
  reason is that the stage the earlier reading feared is the one that got cheaper.** That reading
  named the BFS explicitly, on the argument that `resolveInScene` iterates `Scene.v().getClasses()`,
  so with `Collection+`/`Object+`/`Iterable+` its seed set goes from ~120 JCA methods to every
  matching library method in the Scene and the BFS input grows with it. The first half holds; the
  conclusion does not. Measured 2026-08-28 on a large APK (`net.phbwt.paperwork_1003007`, 45 MB, 3763
  app methods, 60973 methods in the Scene) under spark, `generic_new` against `jca` with nothing else
  varied:

  | stage | `generic_new` | `jca` | ratio |
  |---|---|---|---|
  | `resolveInScene` | 2734 ms | 892 ms | **3.07×** |
  | bytecode scan | 148 ms | 52 ms | **2.85×** |
  | reverse BFS | 246 ms | 3545 ms | **0.07×** |
  | **sum** | **3128 ms** | **4489 ms** | **0.70×** |

  Two stages exceed 2× and the third is 14× cheaper, so the widened matcher costs **less** in total
  than the exact one on this APK. The BFS inverts because seeding it more widely is not the same as
  giving it more work: 5661 seeds against 239 fill the visited set almost immediately, so it marks
  more methods (49039 against 30014) while traversing each edge once instead of walking long chains.
  A per-stage bound would have failed a change that made the pipeline faster.

  Scale, for the reader deciding whether any of this matters: the three stages together are ~3 s of a
  run whose wall clock on that APK is ~51 minutes. The earlier `cryptoapp` measurement (task 4.8:
  `resolveInScene` 0.68×, under CHA, with the other two stages below the IT's 250 ms floor and
  therefore unrated) does not contradict this one — it measures a fixture two orders of magnitude
  smaller under a different call-graph algorithm, which is exactly why 4.8 recorded its own two
  stages as unrated and said the bound had to come from a larger APK.

  The two mandated mitigations are unchanged and are what keep the sum where it is: ordering
  `nameMatches` before `canStoreType`, and caching the resolved super-type `RefType` once per target.

- **INV-ANA-43**: Before `FastHierarchy.canStoreType` is queried, each declared target owner FQN MUST
  be force-resolved into the Soot `Scene` at HIERARCHY level or above. Because GATOR runs Soot with
  `allow_phantom_refs=true`, `forceResolve` of a name Soot cannot find yields a **phantom** `SootClass`
  that satisfies `Scene.containsClass` yet carries no hierarchy; it resolves at `SIGNATURES`, so
  `checkLevel(HIERARCHY)` passes and `canStoreType` returns a **definite `false`** — it does **not**
  throw, and it silently masks a false-negative. So `containsClass` alone MUST NOT be the guard.
  **But `isPhantom()` MUST NOT be the guard either**, and this is a correction to an earlier reading of
  this invariant rather than a refinement of it. Measured on the real Scene (`cryptoapp.apk`, API 33,
  2026-08-28): under `-force-android-jar` the `java.*`/`javax.*` owners of both spec sets are read out
  of the platform `android.jar` with a complete and correct hierarchy — real superclass, real interface
  list, real `ACC_INTERFACE` modifier — and are flagged phantom nonetheless (**522 of 575** JDK classes
  in the Scene), while `canStoreType` answers correctly over all of them, interface-to-interface
  included (`java.util.List <: java.lang.Iterable`). Keying the degrade on the flag therefore degrades
  every declared owner of both spec sets and switches the subtype axis off entirely.

  The degrade criterion MUST therefore be: the owner is absent, OR `resolvingLevel() < HIERARCHY`, OR
  the resolved class **carries no hierarchy content** — i.e. it has no superclass AND no interfaces AND
  no methods, which is what a class Soot invented for a missing source measures (`getModifiers() == 0`
  as well). The three content clauses MUST be a disjunction, so that a marker interface such as
  `java.io.Serializable` is not rejected for declaring no methods. An owner failing the criterion MUST
  degrade to exact `equals` matching and the degradation MUST be logged (no silent false-negative).
  `canStoreType` MUST NOT be called with an absent owner or one that carries no hierarchy content.
  **Ordering**: the owners MUST be
  force-resolved *before* the `FastHierarchy` used to answer `canStoreType` is obtained, and that
  `FastHierarchy` instance MUST NOT be cached across a resolution. This capability MUST NOT require
  force-resolution to precede every `getOrMakeFastHierarchy()` call in the process — that is
  unsatisfiable, since SPARK materialises the hierarchy during the `cg` pack, before any client analysis
  runs — and it need not: `Scene.addClass` invalidates the cached `FastHierarchy` via `modifyHierarchy()`,
  so resolving a not-yet-present owner rebuilds it. For an owner already present that was upgraded **in
  place** (the one case `addClass` does not cover) `Scene.releaseFastHierarchy()` MUST be called before
  the rebuild. It MUST NOT be called merely because an owner was flagged phantom: per the paragraph
  above that is the common case, and such an owner is not modified by the resolution.

- **INV-ANA-44**: The GATOR JSON output schema MUST be unchanged by this capability — no new, renamed,
  or removed keys. The key set of a `generic_new` run MUST be identical to that of a `jca` run; only
  the boolean values of `reachesTarget`/`directlyReachesTarget` differ. INV-ANA-35 (JCA byte-for-byte
  parity in `MopSpecsTargetSource.load()` vs the historical `loadMopSignatures`) MUST remain satisfied.

- **INV-ANA-64**: `ReachabilityEngine.run()` MUST compute the direct-caller set **before** the
  transitive one, and MUST seed the reverse BFS with `targets ∪ directTargetSet` rather than with
  `targets` alone. The containment `reachesTarget ⊇ directlyReachesTarget` — definitional, since a
  direct caller is a path of length 1 — then holds **by construction** for every method the call graph
  contains. Rationale: the two fields are computed from two different oracles. `directlyReachesTarget`
  is the union of the call-graph callers and the bytecode scan that repairs BUG-INV-ANA-19 (SPARK
  quarantines app→library edges); `reachesTarget` is a reverse BFS over the call graph alone, which
  never received that repair. Measured over the 269 `*.apk.json` in the tree: 14 flags across 6 distinct
  methods in 2 APKs violate the containment today, and 12 of the 14 sit on methods with
  `reachable=false` — methods SPARK never processed, so they carry no call-graph vertex at all.
  `multiSourceBfs` already calls `graph.addVertex(seed)` before its visited check, so a seed absent
  from the graph is supported without new defensive code.
  **No consumer-side enforcement is added**: `JsonReportWriter` MUST NOT gate, assert, or abort on a
  residual case, and the analysis MUST continue normally. The residual this seeding cannot remove is a
  method the bytecode scan discovers whose *callers* are themselves absent from the call graph — that
  yields an unmarked ancestor, i.e. a false negative on the transitive axis, never a violated
  containment. Observability, if wanted, belongs in the existing `[ReachabilityEngine]` counter line,
  not in a failing gate.
  The containment is **already asserted** by `tests/parity/test_reachability_parity.py:163`
  (`test_directly_reaches_target_is_subset_of_reaches_target`), whose docstring reads "Invariant by
  construction: directly⊆reaches. Tripwire if not." That claim is **false today** and this invariant is
  what makes it true: the tripwire runs GATOR fresh over `cryptoapp` with the `jca` specs, and passes
  only because that one APK happens to have zero violations (21 direct, 32 transitive) — the 6 methods
  that do violate live in `app.notesr_59` and `com.beemdevelopment.aegis_81`, which the tripwire never
  sees. No new consumer-side assertion is required; what changes is that the existing one stops holding
  by luck.

## MODIFIED Requirements

### Requirement: Target Method Source Abstraction (FR04)

The GATOR analysis client MUST load methods of interest via a `TargetMethodSource` interface with at least two production implementations: `MopSpecsTargetSource` (loads from JavaMOP `.mop` specs via `JavamopFacade.listUsedMethods`) and `SignatureFileTargetSource` (loads from a plain-text file of Soot method signatures). The interface decouples target loading from JavaMOP, enabling use of GATOR for use cases outside RV-Android (taint sinks for auditing, custom method lists for papers, third-party toolchains).

The `TargetMethod` POJO (in `presto.android.gui.clients.target`) carries `className: String`, `methodName: String`, `params: List<String>`, `signature: String`, `policy: MatchPolicy` where `MatchPolicy` is the enum `{ LENIENT, STRICT }`, and — added by this capability — `includeSubtypes: boolean` and `nameIsPattern: boolean`. The policy is populated by the source — it is NOT a CLI-level concern (INV-ANA-36).

The three attributes are **orthogonal axes** and MUST NOT be collapsed into one another. `MatchPolicy` is *signature strictness* (`LENIENT` = class+name, `STRICT` = full signature). `includeSubtypes` is *owner matching* (exact FQN vs `FastHierarchy.canStoreType` against the declared super-type). `nameIsPattern` is *method-name matching* (exact vs trailing-`*` prefix). A `generic_new` owner is LENIENT + subtype + pattern; a JCA owner is LENIENT + exact + exact; a signature-file entry may be STRICT + exact + exact. Folding them into a single enum would explode to the cartesian product and break the `LENIENT`/`STRICT` semantics; see ADR 0004.

`TargetMethod.equals`/`hashCode` MUST include `includeSubtypes` and `nameIsPattern`, so two targets differing only by a flag are not collapsed in a `Set<TargetMethod>`. The canonical constructor MUST carry both flags; per P3 there MUST NOT be a delegating overload that defaults them, and every call site MUST be migrated — `MopSpecsTargetSource` passes the real extracted flags, while `SignatureFileTargetSource` and all test call sites pass `false`/`false`, keeping the JCA and signature-file paths on exact matching (INV-ANA-35).

`MopSpecsTargetSource` MUST resolve LENIENT (match by class+name only) to preserve compatibility with AspectJ pointcuts in `.mop` specs whose parameter lists contain wildcards (`init(int, Certificate, ..)`, `getInstance(String, Object+)`).

`SignatureFileTargetSource` MUST resolve STRICT (full Soot signature match) for each non-wildcard entry. Entries whose parameter list is `(..)` or `(*)` resolve LENIENT for that entry only — wildcard syntax is opt-in per entry, not file-wide. STRICT and `includeSubtypes` is an unused combination in this capability: no signature-file entry declares a `+` owner, so the STRICT parameter-matching path in `TargetResolver.resolveInScene` is never reached with subtype matching on.

The `SignatureFileTargetSource` parser MUST tolerate blank lines and lines beginning with `#` (comments), and MUST raise `IllegalArgumentException` (with line number) on any other malformed line.

**Module**: rvsec-gator (`commons/target/TargetMethod.java`, `commons/target/TargetMethodSource.java`, `client/target/MopSpecsTargetSource.java`, `client/target/SignatureFileTargetSource.java`).

#### Scenario: TargetMethodSource interface is the only entry point to target loading

- **WHEN** `RvsecAnalysisClient.run()` needs to load methods of interest
- **THEN** it MUST construct a `TargetMethodSource` (from CLI argument dispatch) and call `source.load()` to obtain `Set<TargetMethod>`
- **AND** it MUST NOT call `JavamopFacade.listUsedMethods` directly (that call lives inside `MopSpecsTargetSource` only)

#### Scenario: SignatureFileTargetSource parses comments, blanks, and signatures

- **WHEN** `SignatureFileTargetSource.load()` is invoked on a file containing:
  ```
  # JCA crypto sinks
  <javax.crypto.Cipher: void init(int,java.security.Key)>

  <javax.crypto.Cipher: byte[] doFinal(byte[])>
  # LENIENT wildcard
  <javax.crypto.Cipher: void init(..)>
  ```
- **THEN** the returned set MUST contain exactly 3 `TargetMethod` instances
- **AND** the first two MUST have `policy == STRICT`
- **AND** the third MUST have `policy == LENIENT`
- **AND** all three MUST have `includeSubtypes == false` and `nameIsPattern == false`

#### Scenario: MopSpecsTargetSource is a thin wrapper over JavamopFacade

- **WHEN** `MopSpecsTargetSource(Path.of("/m")).load()` is invoked
- **THEN** it MUST delegate to `JavamopFacade.listUsedMethods(/m, false)`
- **AND** it MUST convert each `MopMethod` to a `TargetMethod` with `policy == LENIENT`, **propagating `includeSubtypes` and `nameIsPattern` from the `MopMethod`** rather than defaulting them (INV-ANA-41)
- **AND** the resulting `Set<TargetMethod>` MUST be equal in cardinality to the historical `Set<MopMethod>` produced by `loadMopSignatures` on the same input (INV-ANA-35)

## ADDED Requirements

### Requirement: Subtype/Wildcard-Aware Target Matching for Hierarchy-Declared Spec Sets (FR04, FR05, FR06)

The GATOR target-matching pipeline MUST match a call site to a `.mop` pointcut when the pointcut
declares its owner by **type hierarchy** (the `+` subtype operator) and/or via **wildcard imports**
and **wildcard method names**, and MUST resolve the constructor form `Owner.new(..)` to `<init>` — in
addition to the existing exact-FQN matching for explicitly-declared owners. The requirement is stated
over these constructions and holds for **every** spec set that uses them, present or future; the
`generic_new` corpus is the fixture that exercises all four, not the subject of the requirement. The pipeline spans the extractor, `MopSpecsTargetSource`, `TargetResolver`, and the
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
- **AND** over all 27 `generic_new` specs the emitted target set MUST have the cardinality fixed in advance by INV-ANA-40 — **69** distinct `call()` pairs when the trailing `+` is part of the owner key, **68** when it is not (currently 0), the constructor pointcuts included per boundary (b); asserting merely `> 0` is the pinned-to-whatever-is-emitted weakness that INV-ANA-40 forbids
- **AND** the same extractor run on the 23 `jca` specs MUST emit **exactly 122** targets (**70** `(class, method)` pairs, **23** owners), each with `includeSubtypes=false` and `nameIsPattern=false`. **This literal was 120/68/22 until scope boundary (c) became a requirement to repair**: the seed of that boundary resolves the two `RandomStringPassword` pointcuts, which had never loaded. The freeze forbids an *unenumerated* move of the frozen set, not every move — the two added rows are named in boundary (c) and are the whole difference, and pinning the new literal here is what stops a third move arriving unenumerated
- **AND** the `jca_android` count MUST be **derived by enumerating that directory**, never asserted as a literal: gh109 is adding specs to it (23 → 48 specs, 130 → 238 `call()` pointcuts between 2026-08-21 and 2026-08-28), so only the set-independent properties are pinned — every flag false, and (after the seed of this invariant) **no unresolved owner at all**
- **AND** the `String` owner of `RandomStringPassword.mop` MUST resolve — through the implicit `java.lang` seed, at the third and last resolution step — and both targets it yields MUST carry `MatchPolicy.STRICT` (scope boundary (c)). **This clause inverted on 2026-08-28**: it previously required `String` to stay unresolved and merely logged, which was the accepted-debt reading of boundary (c). The debt is repaired inside this change instead, so the extractor MUST report **zero** unresolved owners for `jca` and `jca_android`, and the skipped-owner log for those two sets MUST be empty rather than naming `String`

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
- **AND** `TargetMethod.equals`/`hashCode` MUST include both flags so two targets differing only by a flag are not collapsed in the `Set<TargetMethod>`; `MopSpecsTargetSource` is the ONE constructor call site that passes the **real extracted flags** (per the two clauses above), while every other call site (`SignatureFileTargetSource`, tests) MUST pass both flags as `false` so the JCA/signature-file paths stay on exact matching (INV-ANA-35)

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
- **AND** `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` MUST match invokes **for those `includeSubtypes=true` entries** via `canStoreType` against the declared super-type, NOT against pre-resolved exact keys
- **AND** the scan MUST remain **hybrid**: the `!includeSubtypes` entries in the same target set MUST keep the existing `Set<String>` `class#method` key path, so JCA lookup stays O(1) and byte-for-byte parity (INV-ANA-35) is unaffected. The prohibition on pre-resolved keys applies to the subtype entries only

#### Scenario: Target super-type force-resolved into the Scene with graceful degradation
- **WHEN** the declared target owner `java.io.Closeable` is not yet loaded as a `SootClass` in the Scene
- **THEN** the matcher MUST force-resolve `java.io.Closeable` at HIERARCHY level, and MUST obtain the `FastHierarchy` only afterwards (never reusing an instance held from before the resolution)
- **AND** because Soot runs with `allow_phantom_refs=true`, the matcher MUST treat a resolved-but-**phantom** owner (or one whose `resolvingLevel() < HIERARCHY`) as unresolved — `containsClass` alone is insufficient, since `canStoreType` would return a definite (wrong) `false` rather than throwing
- **AND** IF a declared owner remains absent or phantom at match time THEN that owner MUST degrade to exact `equals` matching and the degradation MUST be logged as a warning (no silent false-negative)

#### Scenario: Output schema unchanged across spec sets
- **WHEN** GATOR writes the static-analysis JSON for an APK against `generic_new`
- **THEN** the set of JSON keys MUST be identical to a `jca` run on the same APK (only `reachesTarget`/`directlyReachesTarget` boolean values differ)
- **AND** the three raw-JSON readers — `static_analysis_parser.py`, the `scripts/` gates, and `aperv-tool` (`static_artifact.py` + `derive_mop_artifact.py`) — MUST require no key-mapping change; `derive_mop_artifact.py:422` is the one that would degrade a rename to a silent `False` rather than erroring, so it is the sharpest indicator
- **AND** the ape `MopData.java` MUST NOT be cited as evidence of schema safety: it consumes the *derived* `*.mop.json` (key already renamed to `reachesMop`), not this artefact

#### Scenario: Non-target call site stays unmatched — no subtype over-match (negative E2E)
Because `generic_new` declares `Object+` owners (`Object_MonitorOwner.mop`: `wait`/`notify`/`notifyAll`),
**every** call-site declaring type is a subtype of some declared owner. A non-match is therefore decided
on the **method-name axis**, never on the type axis — an earlier framing that called `String.length()`
"not a subtype" was wrong, since `String <: Object`.

- **WHEN** a method invokes a call site whose declaring type is a subtype of a declared owner but whose method name does NOT match that owner's declared pattern/name — e.g. `java.lang.String.length()` (`String <: Object+` but `length` ∉ {`wait`,`notify`,`notifyAll`}), or `java.util.ArrayList.remove(...)` against `Collection+.add*`
- **THEN** the method MUST be reported `reachesTarget=false` and `directlyReachesTarget=false`
- **AND** `nameMatches` MUST reject the name **before** `canStoreType` is consulted, so a non-matching name short-circuits regardless of subtype
- **AND** every `directlyReachesTarget=true` call site in a **sampled** subset of the IT APK MUST be a genuine subtype+name match. The criterion is deliberately bounded: exhaustive ground-truth labelling of an APK is impractical, so acceptance is a documented sample (every call site of at least two declared owners, plus ten randomly drawn positives) with zero misclassifications in that sample. This is a sampling gate, not a completeness proof, and MUST NOT be restated as "zero spurious positives" — a universal claim that no feasible check can discharge

#### Scenario: JCA exact path preserved (parity)
- **WHEN** the matcher resolves a JCA target such as `Cipher.getInstance(String)` (`includeSubtypes=false`)
- **THEN** matching MUST use exact `equals(className) && equals(methodName)` with no hierarchy query
- **AND** `MopSpecsParityTest` MUST keep passing (INV-ANA-35, source-layer parity)
- **AND** because that test compares `MopSpecsTargetSource.load()` against `JavamopFacade.listUsedMethods()` on the same directory — both sides running through the modified visitor — it CANNOT detect an extractor-side JCA regression; the load-bearing JCA gate is therefore the **literal count** asserted in the extractor test (122 targets / 70 pairs / 23 owners, all flags `false` — 120/68/22 until the seed of scope boundary (c) made the two `RandomStringPassword` rows load), plus the `BaselineComparisonIT` on `cryptoapp.apk`

#### Scenario: Constructor pointcut resolves to `<init>` (INV-ANA-40 boundary (b))

- **WHEN** the extractor visits `call(ServerSocket.new(int, int))` in `ServerSocket_Backlog.mop`, or
  `call(TreeMap.new(Map))` in `TreeMap_Comparable.mop`
- **THEN** it MUST emit `MopMethod("java.net.ServerSocket", "<init>")` / `MopMethod("java.util.TreeMap", "<init>")`
  with `includeSubtypes=false` — the pointcuts carry no `+`
- **AND** `TargetResolver.resolveInScene` MUST resolve them, because `SootMethod.getName()` of a
  constructor is `<init>` and the comparison at `TargetResolver.java:53` is name equality
- **AND** the `generic_new` cardinality gate MUST read 69 pairs / 21 owners, not 67 / 20
- **AND** this repair alone MUST leave `jca` at 120 signatures / 68 pairs / 22 owners — the 18 constructor
  rows already existed and only their emitted name changes from `new` to `<init>`. (The set's final
  literal is **122/70/23**; the further two rows come from scope boundary (c)'s seed, which is a
  different cause measured separately. This clause pins *this* repair's effect, not the end state.)
- **AND** the frozen `cryptoapp` fixture MUST move by exactly the two enumerated methods
  (`CryptoUtils.createSecretKeyFromBytes`, `CryptographyActivity.executeSecretKeyOperation`), re-baselined
  with that enumeration written into the commit message

#### Scenario: Seeded `java.lang` owner yields STRICT targets (INV-ANA-40 boundary (c))

- **WHEN** the extractor visits `call(public static String String.valueOf(Object))` and
  `call(public char[] String.toCharArray())` in `jca/RandomStringPassword.mop`, whose imports declare
  `java.util.stream.IntStream` and three `br.unb.cic.mop.*` packages and no `java.lang`
- **THEN** the owner MUST resolve to `java.lang.String` through the implicit-`java.lang` seed — the third
  and last resolution step, reached only because neither the explicit-import map nor `Class.forName` over
  the declared wildcard packages resolved it
- **AND** both emitted targets MUST carry `MatchPolicy.STRICT`, because their owner resolved only through
  the seed; targets whose owner resolved at an earlier step MUST keep the policy they already had
- **AND** their parameter types MUST be FQN (`java.lang.Object` for `valueOf`, none for `toCharArray`), so
  the STRICT signature comparison is expressible at all
- **AND** a call site of `String.valueOf(int)` or `String.valueOf(long)` MUST NOT match, which is the whole
  point of the STRICT clause: under LENIENT the two targets match every overload, measured at 74 call sites
  over 3 corpus APKs of which only 17 are the woven signatures
- **AND** `generic_new` MUST be unaffected — its seven `java.lang`-owner specs declare `import java.lang.*;`
  and so resolve before the seed is consulted, keeping the LENIENT policy their `(..)` parameters require
- **AND** the extractor MUST report zero unresolved owners for `jca` and `jca_android`, the skipped-owner
  log for those sets being empty rather than naming `String`
- **AND** the movement of the frozen `jca` count MUST be enumerated by signature and attributed to its
  cause, the FQN parameter resolution having been measured in isolation first (design D11)

#### Scenario: Bytecode-scan-only direct caller is also transitive (INV-ANA-64)

- **WHEN** a method `m` of the app calls a target method `t` through an invoke that SPARK quarantines,
  so the call graph carries no `m → t` edge and the bytecode scan is the only oracle that sees it
- **THEN** `m` MUST appear in `directlyReachesTarget` (as today, via the scan)
- **AND** `m` MUST also appear in `reachesTarget`, because the reverse BFS is seeded with
  `targets ∪ directTargetSet` and `m` is therefore a seed
- **AND** any caller of `m` that the call graph does contain MUST also appear in `reachesTarget`,
  which post-hoc union of the two sets would not deliver
- **AND** when `m` carries no call-graph vertex at all (measured: 12 of the 14 current violations),
  `m` itself is still marked and only its unreachable ancestors stay unmarked — a false negative on the
  transitive axis, not a containment violation, and the run MUST NOT fail
