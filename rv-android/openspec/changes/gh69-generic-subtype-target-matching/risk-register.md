# Risk Register: gh69-generic-subtype-target-matching

> GitHub Issue: #69 — Full SDD. Companion to `proposal.md` / `design.md`.
> Authoritative source of risks: `docs/20260617_sa_generic_new.md` §12/§14 and `design.md`
> "Decisions / Error Handling / Risks-Trade-offs". This register applies the **proactive strategy**:
> every risk below is documented *before* implementation, with an RMMM plan, so failures are
> anticipated rather than fire-fought.

## Scope under analysis

Make GATOR target matching subtype/wildcard-aware (decision **A2**, `FastHierarchy.canStoreType`),
output schema **INTACT** (decision B). Touches two Java repos/modules — `rvsec-mop-extractor`
(extractor) and `rvsec-gator` (`commons` + `client`) — depends on an external library
(Soot 4.7.1 `FastHierarchy`), and requires an **ordered rebuild of two JARs**. This combination
(multi-module + external dependency + binary artifact coupling) is what drives the risk profile;
per the **Risk Projection** principle the analysis concentrates on the product and tool risks that
the cross-module rebuild and the external hierarchy API introduce.

## Summary

| Risk Level | Count |
|------------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 5 |
| Low | 3 |
| **Total** | **9** |

| ID | Title | Category | Prob. | Effect | Level |
|----|-------|----------|-------|--------|-------|
| RISK-001 | Target super-type **phantom**/absent → `canStoreType` silent wrong `false` | Technology (external dep) | Moderate | Serious | **High** |
| RISK-002 | JCA parity regression (INV-ANA-35 / `MopSpecsParityTest`) | Product (regression) | Low | Serious | **Medium** |
| RISK-003 | Out-of-order rebuild links stale `.m2` extractor (fix never ships) | Tools (build coupling) | Moderate | Tolerable | **Medium** |
| RISK-004 | Quasi-universal specs (`Object+`, `Iterable+`, `Comparable+`) inflate `reachesTarget` | Requirements (scope) | High | Tolerable | **Medium** |
| RISK-005 | `canStoreType` cost at **both** match points (scan **and** `resolveInScene`) | Technology (performance) | Low | Tolerable | **Low** |
| RISK-006 | Non-JDK owner via wildcard import fails `Class.forName` | Technology (extractor) | Very Low | Tolerable | **Low** |
| RISK-007 | Accidental output-schema change breaks the 2 consumers | Product (interface) | Low | Serious | **Medium** |
| RISK-008 | 3-way sync ordering on `analysis` (gh60→gh66→gh69); + gh66 concurrent `FlowgraphRebuilder` edit (RISK-003) | Process (sync ordering) | Moderate | Tolerable | **Low** |
| RISK-009 | Second match point left non-subtype-aware (bytecode-scan contract gap) | Product (architecture) | Moderate | Serious | **Medium** |

---

## Top Risks

### RISK-001: Target super-type phantom/absent in Scene → `canStoreType` returns a silent wrong `false`
- **Category**: Technology (external dependency — Soot 4.7.1 `FastHierarchy`)
- **Description**: `canStoreType(sub, sup)` only answers correctly when **both** types are loaded in the
  Soot `Scene` with a real hierarchy. The call-site type is normally loaded, but a declared **target
  super-type** (e.g. `Closeable`, `Iterable`) may not be. **Mechanism corrected after empirical
  verification (Soot 4.7.1, run against the gator fat jar):** under `allow_phantom_refs=true` an
  unresolvable owner force-resolves to a **phantom** `SootClass` at `BODIES` level — it passes
  `Scene.containsClass`, `checkLevel(HIERARCHY)` passes (`3>=1`), and `canStoreType` returns a **definite
  `false`** rather than throwing or signalling a "non-answer". The spike line `ByteArrayInputStream <:
  Closeable : one side NOT in Scene` was the spike's own `containsClass` guard, not a `canStoreType`
  result. If unmitigated, the predicate silently returns `false` → false-negatives → `reachesTarget=false`
  where it should be `true` — the same failure mode this change exists to fix, now hidden instead of
  zeroed. (A reviewer hypothesis that `canStoreType` *throws* on phantom was empirically refuted; a pure
  `try/catch` mitigation would be dead code.)
- **Why this is the top risk (Risk Projection)**: the spike that proved A2 was **standalone**; it did
  **not** exercise the production Scene configuration of `RvsecAnalysisClient` (its own class-path,
  `whole-program`, exclude/include lists, phantom-ref policy). Whether `forceResolve` actually populates
  the hierarchy under that real config is unverified until the IT runs. Design itself flags this as "the
  highest-risk point" (D2). Effect is Serious because a silent FN defeats the change's purpose and would
  only surface much later, in the downstream 400-APK sweep.
- **Probability**: Moderate · **Effect**: Serious · **Level**: High
- **Mitigation strategy**: Minimization + Avoidance
  - **Avoidance**: `Scene.v().forceResolve(fqn, SootClass.HIERARCHY)` for **every distinct declared
    target owner** before building the `FastHierarchy` (`TargetMatching.forceResolveTargets`, INV-ANA-43 / D2).
  - **Phantom-aware guard (the actual mitigation)**: classify an owner as resolved ONLY if
    `!isPhantom() && resolvingLevel() >= HIERARCHY` — **not** merely `containsClass` (a phantom passes
    `containsClass`). Guard before calling `canStoreType`.
  - **Minimization (no silent FN)**: any owner phantom/absent at match time **degrades to exact `equals`
    and logs a warning once per owner** — wrong matches become detectable, never silent.
  - **Verification gate**: the IT MUST exercise `canStoreType` against the **real `RvsecAnalysisClient`
    scene** (not a synthetic minimal Scene) and assert `reachesTarget>0` on a known generic-positive APK
    **before any sweep is run**. The standalone spike does not satisfy this gate.
- **Indicators (Monitoring)**:
  - Count of "degraded to exact for owner X" warnings emitted during the IT run — expected **0** for the
    21 JDK owners; any >0 is a Yellow trigger (forceResolve not populating hierarchy under prod config).
  - IT assertion `reachesTarget>0` on the generic-positive APK.
- **Contingency (Management)**:
  - **Trigger**: degrade-warnings > 0 in the IT, or `reachesTarget` still 0 after force-resolve.
  - **Actions**: (1) inspect the Scene config (`Options.set_whole_program`, exclude lists,
    `set_allow_phantom_refs`) — phantom refs can leave a type "present but unresolved"; (2) escalate the
    resolve level (`SootClass.SIGNATURES`/`BODIES`) for target owners; (3) if a JDK type genuinely cannot
    be hierarchy-resolved under prod config, document it and confirm the degrade path keeps JCA-style
    exact matching intact — do not ship a silent FN.
  - **Owner**: implementer (gator client).
- **Status**: Open

---

### RISK-002: JCA parity regression (INV-ANA-35 / `MopSpecsParityTest`)
- **Category**: Product (regression in existing capability)
- **Description**: The matcher and extractor are shared between `jca` and `generic_new`. A change meant
  to add the subtype branch could alter the **exact** JCA path (e.g. `nameMatches` no longer falling
  through to `equals`, or flag defaults leaking `includeSubtypes=true` onto JCA targets), silently
  changing JCA `reachesTarget` values that feed the coverage denominator (INV-ANA-15).
- **Probability**: Low (the design's predicate explicitly branches on `includeSubtypes`, false for JCA)
  · **Effect**: Serious (JCA is the primary production spec set; the 226-APK pipeline depends on it) ·
  **Level**: Medium
- **Mitigation strategy**: Minimization (structural) + verification gate
  - JCA owners carry **no `+`** and **no wildcard method name** → extractor sets `includeSubtypes=false`,
    `nameIsPattern=false` → predicate falls through to today's exact `equals` (design "API Design",
    proposal closing paragraph). The subtype branch is **unreachable** for JCA by construction.
  - **Gate**: `MopSpecsParityTest` (INV-ANA-35) must pass **byte-for-byte** for JCA; the extractor run
    must still emit exactly **120** JCA targets with both flags false (INV-ANA-40 test).
- **Indicators**: `MopSpecsParityTest` Green/Red; JCA target count == 120; JCA-target flags all false.
- **Contingency**:
  - **Trigger**: parity test fails or JCA count ≠ 120.
  - **Actions**: diff the offending `TargetMethod` set, confirm flag defaults, restore exact fall-through
    before proceeding. Block archive until parity is byte-for-byte.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-003: Out-of-order rebuild links a stale `.m2` extractor (fix never ships)
- **Category**: Tools (build / artifact coupling)
- **Description**: The extractor is a **compile-scope dependency bundled into**
  `rvsec-analysis-client.jar`. If gator `client` is rebuilt **before** `mvn install`-ing the extractor,
  Maven links the stale `.m2` copy and the extractor fix silently does not enter the shipped JAR — the
  pipeline still emits 0 generic targets while *looking* rebuilt (validated §14 item 12, D6). A related
  trap: omitting `sootandroid` from the rebuild `-pl` set drops the `FlowgraphRebuilder` arity guard
  (WTG SPARK `cgDelegation`), reintroducing the committed-`e584894a` crash.
  - **Concurrent-edit overlap with gh66 (in-flight)**: `gh66-gator-wtg-flowcontainer-perf` is editing
    the **same** `FlowgraphRebuilder.java` (its `buildFlowThroughContainer` hoist/memo perf fix) in the
    same `sootandroid` module that gh69 rebuilds with `-pl sootandroid`. The current `lib/gator/*.jar`
    (dated 2026-06-17) already reflect gh66's WIP. When gh69 rebuilds, the source tree MUST carry **both**
    the arity guard (gh60/`e584894a`) **and** gh66's perf change — neither rebuild may revert the other.
    Coordinate: rebuild gh69 from a tree that includes the latest gh66 `FlowgraphRebuilder` state.
- **Probability**: Moderate (easy to get wrong; multi-step manual build) · **Effect**: Tolerable
  (caught quickly by the target-count check, recoverable by re-running in order) · **Level**: Medium
- **Mitigation strategy**: Avoidance (process) + Minimization
  - **Mandatory ordered build (D6)**: `mvn install` extractor **first** → then rebuild gator `client`.
  - Include `sootandroid` in the rebuild `-pl` to preserve the `FlowgraphRebuilder` arity guard
    (proposal "Impact: Invariant preserved").
  - Encode the order in `tasks.md` as explicit sequential steps (not a single "rebuild JARs" task).
- **Indicators**:
  - Extractor target count for `generic_new` is **N>0** (not 0) **after** the gator rebuild — the
    canary that the fresh extractor is actually inside `rvsec-analysis-client.jar`.
  - JAR build timestamp under `rv-android/lib/gator/` newer than the source edit.
  - WTG SPARK run does not regress to `ArrayIndexOutOfBoundsException`.
- **Contingency**:
  - **Trigger**: post-rebuild generic target count still 0, or WTG crash returns.
  - **Actions**: `mvn install` extractor, confirm the new artifact in `.m2`, rebuild gator with
    `sootandroid` included, re-copy JARs to `lib/gator/`, re-run the canary.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-004: Quasi-universal specs inflate `reachesTarget`
- **Category**: Requirements (scope boundary)
- **Description**: Specs whose owner is `Object+`, `Iterable+`, or `Comparable+` will match a huge
  fraction of call sites once subtype matching is on, driving `reachesTarget=true` almost everywhere.
- **Probability**: High (these owners exist in `generic_new`) · **Effect**: Tolerable (it is *correct*
  per the spec semantics; only affects downstream dataset interpretation) · **Level**: Medium
- **Mitigation strategy**: Acceptance (documented scope decision)
  - Per design Non-Goals and "Risks/Trade-offs": this inflation is **correct behavior** for this
    matcher. Any dataset-level exclusion (drop quasi-universal owners from the dataset filter) is an
    explicit **downstream concern** — the 400-APK sweep / dataset-definition change. Documented as an
    Open Question that does **not** block this design.
  - Guard against scope creep: do **not** add owner-blacklisting to the matcher in this change
    (P1 simplicity; "No unilateral scope decisions" — defer to the downstream owner).
- **Indicators**: presence of `Object+`/`Iterable+`/`Comparable+` in the extracted target set is
  expected, not a defect; only flag if a reviewer mistakes the inflation for a matcher bug.
- **Contingency**:
  - **Trigger**: stakeholder requests dataset-level filtering during this change.
  - **Actions**: record as the downstream sweep/dataset change; do not absorb it here.
  - **Owner**: change author / downstream sweep owner.
- **Status**: Open (accepted)

---

### RISK-005: `canStoreType` cost at **both** match points (bytecode scan **and** `resolveInScene`)
- **Category**: Technology (performance)
- **Description**: Two hot loops, not one. (a) The direct bytecode scan iterates every invoke; adding
  `canStoreType` per candidate adds cost. (b) **`TargetResolver.resolveInScene` (verified) iterates
  `Scene.getClasses()` × methods × targets and today fast-rejects via `t.getClassName().equals(fqn)`
  before any work** — for `includeSubtypes` targets that string fast-reject **disappears**, turning every
  (Scene-method × subtype-target) pair into a `canStoreType`. With `android.jar`/JDK in whole-program
  that is tens of thousands of classes × ~71 subtype targets. The original register covered only the
  scan; `resolveInScene` is the larger hot spot.
- **Probability**: Low · **Effect**: Tolerable · **Level**: Low
- **Mitigation strategy**: Minimization + measurement
  - `FastHierarchy.canStoreType` is **O(1) amortized** (interval-encoded class hierarchy).
  - **Mandatory ordering**: evaluate `nameMatches` **before** `canStoreType` at both points (cheap name
    short-circuit replaces the lost `equals(fqn)` fast-reject) — promoted from contingency to design
    requirement (tasks 2.3/3.1).
  - **Cache** the resolved `superType(t)` `RefType` once per target (not per invoke/per Scene-method).
  - Measure wall-time of **both** the scan and `resolveInScene` in the IT; compare to a JCA-equivalent run.
- **Indicators**: IT scan time **and** `resolveInScene` time within the same order of magnitude as the JCA baseline.
- **Contingency**:
  - **Trigger**: scan time regresses materially (e.g. >2×) on the IT APK.
  - **Actions**: cache resolved `superType(t)` `RefType` per target (resolve once, not per invoke);
    short-circuit the predicate when `!includeSubtypes`.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-006: Non-JDK owner via wildcard import fails `Class.forName`
- **Category**: Technology (extractor owner resolution)
- **Description**: Owner FQN resolution uses explicit imports first, then `Class.forName` over
  wildcard-import packages. A non-JDK owner reachable only via a wildcard import would fail to resolve at
  the extractor's runtime classpath.
- **Probability**: Very Low (validated §14 item 14: **all 21** `generic_new` owners are JDK —
  `java.lang`/`util`/`io`/`net`) · **Effect**: Tolerable · **Level**: Low
- **Mitigation strategy**: Acceptance + safe degrade (D5)
  - An owner resolvable via neither imports nor `Class.forName` is **logged and skipped** (no crash);
    the target is simply absent. No JDK-external owner exists today.
- **Indicators**: count of "owner skipped — unresolvable" log lines during extraction == **0** for
  `generic_new`.
- **Contingency**:
  - **Trigger**: a future spec introduces a non-JDK wildcard-imported owner (skip-count > 0).
  - **Actions**: add that library to the extractor's resolution classpath, or resolve via the explicit
    import; revisit only when such an owner appears.
  - **Owner**: extractor maintainer.
- **Status**: Open

---

### RISK-007: Accidental output-schema change breaks the two consumers
- **Category**: Product (interface contract)
- **Description**: The output JSON is consumed by **two** parsers — the Python
  `static_analysis_parser.py` boundary in `rv-static-analysis`, and the ape `MopData.java` (`opt*`,
  optional-field-tolerant). An accidental key add/rename/removal while editing the writer area would
  break one or both consumers, even though no schema change is intended.
- **Probability**: Low (the change explicitly touches matching, not the JSON writer) · **Effect**:
  Serious (silent breakage of downstream coverage + ape) · **Level**: Medium (reclassified for
  consistency with RISK-002, also Low×Serious → Medium; the previous "Low" was internally inconsistent)
- **Mitigation strategy**: Avoidance (invariant) + verification gate
  - **Schema invariance is an invariant** (INV-ANA-44, decision B/D3): no JSON writer change at all;
    only boolean *values* of `reachesTarget`/`directlyReachesTarget` move.
  - **Gate**: in the IT, diff the **key-set** of a `generic_new` run against a `jca` run on the same
    APK — must be **identical**. This is a hard gate before archive.
- **Indicators**: generic-vs-jca JSON key-set diff is empty; `static_analysis_parser.py` parses the
  generic output without error; ape `MopData` `opt*` fields unaffected.
- **Contingency**:
  - **Trigger**: key-set diff non-empty, or a consumer fails to parse.
  - **Actions**: revert any writer-area edit; confirm the boolean-only change set; re-run the diff.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-008: 3-way sync/archive ordering on the `analysis` capability (gh60 → gh66 → gh69)
- **Category**: Process (OpenSpec sync ordering / cross-change dependency)
- **Description**: **Three** in-flight changes stack deltas on the same `analysis` capability —
  **gh60-targets-core** (INV-ANA-33..38, the `TargetMethod`/`MatchPolicy`/`TargetResolver` abstraction),
  **gh66-gator-wtg-flowcontainer-perf** (INV-ANA-39), and this change gh69 (INV-ANA-40..44). gh69's delta
  **references** INV-ANA-33/35 and the gh60 abstraction. Verified: `openspec/specs/analysis/spec.md`
  currently contains **none** of INV-ANA-33..44 — none of the three is synced yet. If gh69 is
  `/opsx:sync`-ed/archived **before gh60**, the resulting `analysis/spec.md` carries references to
  invariants that do not exist in the synced spec (the same class of friction recorded for the gh50/52/53
  batch sync). gh66 does **not** reference gh60/gh69 invariants (technically independent), but syncing out
  of number order risks merge conflicts on the shared capability text.
- **Probability**: Moderate (three changes in-flight; easy to archive in the wrong order) ·
  **Effect**: Tolerable (caught at sync time; recoverable by syncing in order, no data loss) ·
  **Level**: Low
- **Mitigation strategy**: Avoidance (process ordering)
  - **Mandatory order**: **gh60 first**, then gh66, then gh69 (ascending INV-ANA-number order). gh60
    before gh69 is hard (dangling 33/35 otherwise); gh66 before gh69 is soft (conflict-avoidance).
    Encoded in `proposal.md` §Impact (gh60 dependency bullet).
  - At gh69 Phase 6, before `/opsx:archive`, confirm `openspec/specs/analysis/spec.md` already contains
    INV-ANA-33/35 (and, ideally, INV-ANA-39 from gh66).
- **Indicators**: `grep -n 'INV-ANA-33\|INV-ANA-35' openspec/specs/analysis/spec.md` is **non-empty**
  before gh69 sync.
- **Contingency**:
  - **Trigger**: gh69 about to be synced while the grep above is empty.
  - **Actions**: sync/archive gh60 (then gh66) first; then sync gh69; re-grep the synced spec for any
    remaining dangling INV-ANA references.
  - **Owner**: change author (archive sequencing).
- **Status**: Open

---

### RISK-009: Second match point left non-subtype-aware (bytecode-scan contract gap)
- **Category**: Product (architecture completeness)
- **Description**: Surfaced by multi-LLM artefact review and **verified against source**:
  `findDirectTargetCallersByBytecodeScan(appClasses, Set<SootMethod>)` and `ReachabilityEngine` receive
  only the **resolved** `Set<SootMethod>`, which has lost the declared owner FQN and the
  `includeSubtypes`/`nameIsPattern` flags; the scan rebuilds exact `class#method` string keys. If an
  implementer follows a naive "swap `equals` for `matches`" reading, the bytecode scan **cannot** evaluate
  `canStoreType` against the declared super-type — so the second match point silently stays exact-only and
  INV-ANA-42 ("predicate at both points") is half-met. `RvsecAnalysisClient.run()` already holds the
  declared `Set<TargetMethod> targetSpecs` in scope, so the fix is a contract change, not new analysis.
- **Probability**: Moderate (easy to miss; the original tasks under-specified it) · **Effect**: Serious
  (one of the two reachability match points would under-report `reachesTarget` for subtype owners) ·
  **Level**: Medium
- **Mitigation strategy**: Avoidance (explicit contract change) + verification
  - Extend `ReachabilityEngine`'s constructor/`run(...)` and `findDirectTargetCallersByBytecodeScan` to
    also carry `Set<TargetMethod> targetSpecs`; **hybrid scan** preserving the `Set<String>` exact path
    for `!includeSubtypes` (JCA O(1)/parity) + per-invoke `canStoreType` for `includeSubtypes` targets
    (now an explicit step in **task 3.2**, with design Data-Flow §5 describing the cascade).
- **Indicators**: a `generic_new` IT method reachable **only** via the direct bytecode scan (not the CG)
  reports `directlyReachesTarget=true`; unit/IT exercises the scan with at least one subtype target.
- **Contingency**:
  - **Trigger**: the scan still consumes `Set<SootMethod>`/`targetKeys` after implementation.
  - **Actions**: thread `Set<TargetMethod>` through `ReachabilityEngine`; re-run the scan-only IT.
  - **Owner**: implementer (gator client).
- **Status**: Open

---

## Monitoring Schedule

- **Review cadence**: at each Full-SDD phase boundary during the change —
  - **End of Design** (now): register created; RISK-001 and RISK-003 mitigations must be encoded as
    explicit ordered steps / IT gates in `tasks.md`.
  - **During Implement** (`/opsx:apply`): re-check RISK-003 indicator (post-rebuild generic count > 0)
    after every JAR rebuild.
  - **During Verify** (`/rv-verify` + `/opsx:verify`): RISK-001 (IT on real scene, 0 degrade-warnings),
    RISK-002 (parity byte-for-byte + 120 JCA targets), RISK-005 (scan time), RISK-007 (key-set diff) are
    all hard gates.
- **Risk review checklist** (run at each boundary):
  - [ ] Any new risk surfaced by the IT on the real scene?
  - [ ] RISK-001 degrade-warning count still 0 for the 21 owners; no owner phantom (`isPhantom` guard active)?
  - [ ] RISK-002 parity still byte-for-byte / JCA count == 120?
  - [ ] RISK-003 post-rebuild generic target count > 0; `sootandroid` in rebuild; WTG no crash?
  - [ ] RISK-005 `resolveInScene` + scan wall-time within JCA order of magnitude?
  - [ ] RISK-007 key-set diff still empty?
  - [ ] RISK-008 (at Phase 6 only) `analysis/spec.md` already has INV-ANA-33/35 (gh60 synced first)?
  - [ ] RISK-009 bytecode scan carries `Set<TargetMethod>` (scan-only IT method reports subtype `directlyReachesTarget=true`)?
  - [ ] Any risk closeable?
- **Owner**: change author (Pedro Costa).

## Change Log

| Date | Risk | Change |
|------|------|--------|
| 2026-06-17 | all | Register created at end of Design phase from `design.md` + `docs/20260617_sa_generic_new.md` §12/§14 |
| 2026-06-17 | RISK-008 | Added (sync ordering gh60→gh69) from adversarial artifact validation `docs/20260617_sa_generic_new.md` §15 |
| 2026-06-17 | RISK-008 / RISK-003 | Broadened to 3-way ordering gh60→gh66→gh69 + gh66 concurrent `FlowgraphRebuilder` edit overlap (per operator note: gh66 in-flight) |
| 2026-06-23 | RISK-001 | Mechanism corrected after **empirical** Soot 4.7.1 verification: phantom owner → `canStoreType` returns silent wrong `false` (does NOT throw; phantom resolves at `BODIES`). Mitigation is an `isPhantom()`/`resolvingLevel` guard, not `try/catch`. |
| 2026-06-23 | RISK-005 | Broadened to cover `resolveInScene` (loss of `equals(fqn)` fast-reject), not just the bytecode scan. |
| 2026-06-23 | RISK-007 | Reclassified Low→Medium for internal consistency with RISK-002 (both Low×Serious). |
| 2026-06-23 | RISK-009 | Added: bytecode-scan/`ReachabilityEngine` contract gap (declared `Set<TargetMethod>` not propagated to the second match point) — from multi-LLM review, source-verified. |
