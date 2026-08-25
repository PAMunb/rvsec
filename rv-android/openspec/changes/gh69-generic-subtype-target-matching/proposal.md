## Why

GitHub Issue: #69.

The GATOR static-analysis pipeline computes `reachesTarget`/`directlyReachesTarget` by matching the
monitored API call sites of an APK against the target methods declared in a JavaMOP spec set. This
matching is **exact-FQN** and was written for the JCA spec style (explicit imports + exact
`Class.method` pointcuts). The `generic_new` spec set uses a different style — wildcard imports
(`import java.util.*;`), owners declared by **subtype** (`call(* Collection+.addAll(..))`), and
**wildcard method names** (`add*`). Against `generic_new` the pipeline loads **0 targets** and reports
`reachesTarget=false` for every method of every APK — the static layer contributes no reachability
signal whatsoever for that spec set. That is the defect this change repairs. What the repaired signal is
then *good for* is a separate question, deliberately not claimed here: see the two downstream caveats in
Impact (the experiment path cannot select `generic_new` today, and quasi-universal owners saturate the
boolean). This change makes the matcher correct; it does not by itself deliver the generic dataset.

This is confirmed empirically: the `rvsec-mop-extractor` extracts **0 methods** from the 27
`generic_new` specs versus **120** from `jca`; **27/27** generic specs use wildcard imports and **Read those two numbers carefully — they are not the same unit** (re-derived 2026-08-21): the 120 counts *signatures* and **includes** constructor pointcuts; the 67 counts *(owner, method) pairs* and **excludes** them. Under one convention it is 120 vs **72** signatures, or **68 vs 69** pairs — essentially level. Sharper still: 18 of the `jca` 120 are constructor targets named `new`, which match no Soot method (constructors are `<init>`), so the frozen set carries **~102 live signatures / 57 live pairs** today. The repaired `generic_new` would therefore yield *more* live targets than the published ruler, not half as many. The headline "0 → N" claim is unaffected; the "much smaller than jca" reading is wrong.
**71/89** `call(...)` pointcuts use a `+` subtype owner. Full root-cause analysis and an adversarial
validation are in `docs/20260617_sa_generic_new.md` (§1–§15 — §15 is the adversarial validation of
this change's own artefacts, added the same day) and `docs/20260611_sweep_generic_new_400.md`
(§10 — the former §11 was folded into §10 when decision B was recorded, so cite §10 only; the Estágio A
*procedure* is §5). The reachability sweep that stalled at 49/400 on the old sweep corpus waits on this
fix; that corpus has since been superseded (see Impact).

## What Changes

- **Extractor (`rvsec-mop-extractor`)** — teach `UsedJcaMethodsVisitor` to handle the generic style:
  register wildcard-import packages (stop discarding `isAsterisk()` imports), strip the `+` subtype
  suffix from owners and flag `includeSubtypes`, resolve simple owner names to FQN via explicit
  imports first and `Class.forName` over wildcard packages second (all 21 owners appearing in `call(...)`
  pointcuts are JDK classes — 23 counting the two `staticinitialization`-only owners `Serializable`/
  `URLConnection`; 20 carry non-constructor targets, `TreeMap` appearing only in a constructor pointcut),
  and preserve wildcard method names (`add*`) as a pattern rather than a literal. New `MopMethod`
  flags: `includeSubtypes`, `nameIsPattern`. **Coverage boundary (documented, accepted)**: only
  `call(...)` pointcuts are extracted — the 3 specs whose sole pointcut is `staticinitialization(Owner+)`
  and the 3 constructor `call(Owner.new(..))` pointcuts remain without static targets. The constructor
  half is **an active guard, not a passive gap**: the javamop grammar routes `Owner.new(..)` through
  `MethodPointCut` (`aspectj.jj:1730-1737`), so once wildcard packages are registered these pointcuts
  would emit a `MopMethod` named `new` — matching no Soot method, since constructors are `<init>` — and
  silently inflate the cardinality gate. Task 1.3(d) must skip them explicitly and log 3 notices (net 24/27 specs
  with ≥1 target; see design Non-Goals and INV-ANA-40 scope boundary). **That 24/27 depends on the
  one-line spec repair in task 1.0b**: `CharSequence_NotInSet.mop` declared owner `Set+` while importing
  only `java.io`/`java.lang`/`java.nio`, so under the import-driven resolution rule its owner resolved to
  nothing. Without the repair the spec contributes zero targets and coverage is 23/27 — being a JDK class
  is not sufficient for an owner to resolve; the spec must actually import its package (RISK-006). The implicit `java.lang` package
  is deliberately **not** seeded: `generic_new` does not need it, and seeding it would move the frozen
  `jca`/`jca_android` sets (120→122 / 119→121) by resolving `RandomStringPassword.mop`'s `String` owner
  into a LENIENT target that matches every `String.valueOf` overload — 74 call sites over 3 corpus APKs,
  17 of them woven. That false-negative is documented in scope boundary (c) and repaired in its own
  change; evidence in `docs/20260821_handoff_gh69_coringas.md`. **It is a High risk, not a footnote —
  `risk-register.md` RISK-013**: `RandomStringPasswordSpec` is 1 of the 23 `jca` specs, its two
  pointcuts are woven and live, and it contributes zero static targets, so every `cov_reaches_target`
  ever published from the frozen `jca` ruler was computed over **22 of 23** specs. What this change
  does deliver against it is visibility — the log-and-skip rule makes `String` a named skipped owner
  instead of a silent drop; the measurement repair stays in task 5.6.

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

- **Reachability set consistency (`ReachabilityEngine`)** — `reachesTarget` MUST contain
  `directlyReachesTarget`. That containment is definitional (a direct caller is a path of length 1) but
  the tree violates it: 14 flags across 6 distinct methods in 2 APKs, out of the 269 `*.apk.json`
  present. The cause is that one relation has two oracles and only one was repaired — the direct axis is
  `call-graph callers ∪ bytecode scan` (the BUG-INV-ANA-19 repair for the app→library edges SPARK
  quarantines), while the transitive axis is a reverse BFS over the call graph alone, which never got
  that repair. The fix is to compute the direct set **first** and seed the reverse BFS with
  `targets ∪ directTargetSet` (INV-ANA-64, design D8) — containment then holds by construction and
  propagates to callers, which a post-hoc union of the two sets would not do. This is a **pre-existing**
  defect, not one gh69 introduces; it is repaired here because gh69 amplifies it, taking the direct set
  from 0.0–0.3% of app methods to 2–12% (RISK-004) and the scan-only share of it with it. It is
  deliberately **not** enforced at the consumer: `JsonReportWriter` gains no gate and no abort, so a
  residual case degrades to an unmarked ancestor (a transitive false negative) and the run continues.
  No frozen gate moves — the `G_paridade_targets` fixture has zero violations today.

- **Constructor targets (`new` → `<init>`)** — the extractor emits `MopMethod(owner, "new")` for every
  `call(Owner.new(..))` pointcut, and Soot names every constructor `<init>`, so those targets have never
  matched anything. This is a live defect in the **frozen `jca` set**, not only a `generic_new` gap: 18
  signature rows collapsing into **11 of its 68 pairs** — `SecureRandom`, `SecretKeySpec`,
  `IvParameterSpec`, `PBEKeySpec` and seven more — all dead, which means the published ruler has never
  counted a constructor call site, `new SecretKeySpec(...)` included. An earlier draft of this change
  suppressed the three `generic_new` constructor pointcuts and left the eighteen `jca` ones standing;
  that shipped an asymmetry this change itself created. The repair is a keyword rename at a code site
  phase 1 already rewrites, with no GATOR-side change (`TargetResolver.java:53` compares names by
  equality; `SignatureFileTargetSource` already accepts `<init>`). It is admissible under the freeze
  doctrine gh101 established — shared code, no branching on spec set — **provided its effect on the
  frozen set is enumerated**, which phase 4b does: measured on the `cryptoapp` fixture, exactly two
  methods change on the direct axis (21 → 23), both named. It is sequenced in a phase of its own, after
  the subtype path is green, so that a red parity gate can still be attributed. `generic_new` goes 67 →
  **69** pairs and 20 → **21** owners; the `jca` triple 120/68/22 does not move.

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
  (INV-ANA-40+) for extractor extraction of wildcard/`+`/pattern owners, plus a `## MODIFIED Requirements`
  block restating "Target Method Source Abstraction (FR04)" in full: `TargetMethod` gains
  `includeSubtypes`/`nameIsPattern`, and the `MopSpecsTargetSource` thin-wrapper scenario now requires
  propagating them rather than carrying `policy` alone. Without that block the synced spec would keep
  claiming a five-field POJO and a policy-only conversion, the A2 `canStoreType`
  predicate at both match points, target-super-type Scene resolution with graceful degradation, and
  the output-schema-invariance guarantee. Builds on the `TargetMethod`/`MatchPolicy`/`TargetResolver`
  abstraction and INV-ANA-33/INV-ANA-35 introduced by **gh60-targets-core** (dependency, see Impact).

## Impact

- **Modules / repos**: `rvsec-mop-extractor` (extractor JAR), `rvsec-gator` `commons` + `client`
  (`rvsec-gator.jar` + `rvsec-analysis-client.jar`, copied to `rv-android/lib/gator/` on `mvn install`).
  No Python module changes — the schema is unchanged (INV-ANA-44), only boolean values move. Note the
  consumer map is wider than earlier drafts stated: the raw GATOR JSON has **three** independent readers,
  not two — `rv-static-analysis` through its single parser boundary (`static_analysis_parser.py:98-99`),
  the repo gate/sweep scripts under `scripts/`, and **`aperv-tool`**, which parses `<apk>.json` itself and
  imports nothing from `rv_static_analysis` (`analysis/static_artifact.py:261,270-271,293,359`;
  `tools/aperv/derive_mop_artifact.py:421-422,1029,1158`). **Wider still (2026-08-21)**: those three are
  complete only for `modules/`. Six further raw readers live elsewhere — `tests/parity/` (four files),
  `docs/20260803_charac_static_corpus.py`, and `experimento-comp162-ajc/scripts/{covadjust,analise}.py`.
  Two of them are **value**-stability gates on exactly the booleans this change moves:
  `tests/parity/test_reachability_parity.py:156` (`G_paridade_targets`) freezes the *set* of signatures
  carrying `reachesTarget=true` against a committed baseline, and
  `tests/parity/test_historical_methods_coverage.py:134` pins three methods at
  `directlyReachesTarget=true`. INV-ANA-44 promises key-set invariance; these guard values. Both run
  against the default `mopDir` (`jca`), so the JCA-untouched premise is what keeps them green — and they
  would catch a JCA regression before anything else does. The ape `MopData.java` is **not** one of them:
  it reads the *derived* `*.mop.json`, where the key has already been renamed `reachesTarget` →
  `reachesMop` (`derive_mop_artifact.py:1158`), and hard-rejects any document without `formatVersion == 1`
  (`<workspace-rv>/ape/src/main/java/com/android/commands/monkey/ape/utils/MopData.java:207-213` — the
  full path matters: no `MopData.java` exists anywhere under `rv-android` or `rvsec`). So its `opt*` tolerance is no argument for schema safety here; the component
  actually exposed to a GATOR key change is `derive_mop_artifact.py`, which is **not** tolerant
  (`method.get("reachesTarget") is True` at :422 degrades a rename to a silent `False`).
- **Requirements**: FR04 (WTG), FR05 (GUI elements), FR06 (method reachability) — the reachability
  target-set computation. Relates to INV-ANA-15 (coverage denominator uses `reaches_target`),
  INV-ANA-18 (Soot 4.7.1), BUG-INV-ANA-19 (bytecode-scan complement gains the subtype predicate).
  Note that of these, only INV-ANA-15 has a normative bullet in the synced `analysis/spec.md`; INV-ANA-17,
  INV-ANA-18 and BUG-INV-ANA-19 survive there as narrative references only, their bullets living in the
  gh51 archive. They are cited here as context, not as invariants this change can rely on being synced
  (RISK-008).
- **Dependency on gh60-targets-core** (issue #60, ARCHIVED 2026-06-17): the `TargetMethod`/`MatchPolicy`/
  `TargetResolver`/`MopSpecsTargetSource` abstraction and INV-ANA-33/35 are introduced there. The
  code is already in the gator source; this change extends it. INV-ANA-35 parity (JCA byte-for-byte)
  MUST be preserved.
  - **Sync/archive ordering — constraint now SATISFIED (as of 2026-07-06)**: gh60 (INV-ANA-33..38) and
    gh66 `gator-wtg-flowcontainer-perf` are **already archived**, and gh60's invariants are synced
    (gh66's INV-ANA-39 requirement is synced but its normative bullet is not — see RISK-008) — the synced
    `openspec/specs/analysis/spec.md` now contains INV-ANA-33/35, so this change's references resolve and
    the earlier "gh60 MUST sync first / dangling reference" hazard no longer applies. gh69 claims
    INV-ANA-40..44, which are **free** in the synced spec and unclaimed by any active change. Two residual
    Phase-6 checks remain (not blockers for `/opsx:apply`): (a) confirm 40-44 are still free and INV-ANA-33/35
    still present at archive time; (b) reconcile a pre-existing sync anomaly — two changes archived *after*
    gh66 took higher numbers (gh70-wtg-reachability-sharing: INV-ANA-45; gh72-logcat-diagnostic-events:
    INV-ANA-46/47/48) yet the synced inventory jumps **38 → 46,47,48**. The gap is systemic, not a one-off
    gh70 miss: INV-ANA-39 (gh66) has no bullet either, and INV-ANA-55 (gh92, archived 2026-08-02) is also
    absent. Related: gh69 cites INV-ANA-17, INV-ANA-18 and BUG-INV-ANA-19 as though defined in the synced
    spec; there they survive only as narrative references, their normative bullets living in the gh51
    archive. gh69's insertion at 40-44 is non-contiguous but collision-free. See RISK-008.
- **Invariant preserved**: `FlowgraphRebuilder` arity guard (WTG SPARK cgDelegation) lives in source
  (`FlowgraphRebuilder.java:212-225,704-717`) — including `sootandroid` in the rebuild keeps it. Caveat
  worth knowing: `Configs.cgDelegation` defaults to **`false`** (`Configs.java:89`), contradicting the
  comment at `FlowgraphRebuilder.java:1030`, so the live path today is the legacy one at
  `FlowgraphRebuilder.java:1065` unless `-cgDelegation true` is passed. The guards still ship; they simply
  protect the non-default path.
- **Downstream (out of scope) — how `generic_new` is actually selected**: the experiment path cannot
  reach it today. `rv-experiment`/`rv-platform` never set `mop_dir`, so `RVStaticAnalysisConfig` always
  falls back to `rvsec-mop/src/main/resources/jca` (`config.py:199-208`) — the static analysis runs
  against `jca` even under `--specification-set jca_android` or `generic`; and `--specification-set
  generic` maps to `resources/generic`, a different corpus (118 synthetic `FSM*` specs — no wildcard
  imports, no `+` owners, no wildcard method names; they *do* use `*` as a return-type wildcard in 356 of
  436 `call()` pointcuts, which the extractor ignores since it keys on owner+method), not to `generic_new`. This change is verified through `rv-static-analysis --mop-dir
  .../generic_new` directly (tasks 4.3/5.2, procedure in `docs/20260611_sweep_generic_new_400.md`), which
  is unaffected. Wiring the spec-set → `mopDir` selection is the sibling orchestrator repair. It is
  tracked in `docs/20260821_plano_correcao_analise_estatica.md` (D2) — an **untracked** document — but the
  vehicle that actually implements it is **issue #104, task 10.0** (`tasks/E10-integration.md:7`, open as of
  2026-08-21, first in its group): "`get_static_analysis_config()` passes the resolved set directory as
  `mop_dir` — today `RVStaticAnalysisConfig` defaults it to `resources/jca` (`rv_static_analysis/config.py:198-207`)".
  The coupling is one-directional and narrow: **gh69 does not depend on it to be implemented, verified or
  archived** — every gate here runs through `--mop-dir` directly — but the *product* of gh69 stays
  unreachable from `rv-experiment`/`rv-platform` until that task lands. Conversely gh104 task 10.0 does not
  depend on anything in gh69: without gh69 it selects `generic_new` and gets 0 targets, which is the present
  defect, not a new one. Neither change registered the other before 2026-08-21.
- **Downstream (out of scope)**: the `generic_new` reachability sweep and the generic dataset definition
  are a separate later change. **Corpus updated 2026-07-09, re-verified 2026-08-21**: the generic
  experiment will draw APKs from the new dataset repo (`rvsec-dataset`), superseding the 400-APK sweep
  corpus. Two corrections to the earlier note: `apks_original/` is **empty** (a lone `.gitkeep`) — the APKs
  live in `head_apks/` (348), `built_apks/` (317) and `instrumented_apks/` (219) — and the "219 curated
  apps" figure is stale, the repo having re-frozen to 182 (Phase 10) and then 181 (Phase 11) on
  2026-07-14;
  `docs/20260611_sweep_generic_new_400.md` remains the procedure reference. Two caveats on that corpus,
  both verified 2026-08-21 and neither settled: its `ROADMAP.md` marks Phases 10 and 11 with an open
  "⚠ M10/M11 desync follow-up", so 181 is a live figure rather than a frozen one; and its selection
  criterion is **JCA** static reachability (the 23 `jca` specs), which means a corpus chosen for JCA
  reachability would be handed to a generic experiment — a selection bias the downstream change must
  confront, distinct from the already-noted fact that the ROADMAP is JCA-only. Caveat for that downstream
  change: with quasi-universal owners (`Object+`, `Iterable+`) `reachesTarget` saturates near-true across
  APKs, and decision B (no per-owner attribution in the JSON) means the dataset filter cannot statically
  discriminate universal from selective targets — the downstream change must plan around this (per-owner
  side data or runtime attribution).
