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

| Risk Level | Total | Open | Accepted | Largely mitigated | Closed by design |
|------------|-------|------|----------|-------------------|------------------|
| Critical | 0 | 0 | 0 | 0 | 0 |
| High | 5 | 2 (001, 009) | 2 (004, 013) | 0 | 1 (011) |
| Medium | 5 | 4 (002, 003, 007, 012) | 1 (010) | 0 | 0 |
| Low | 3 | 2 (005, 006) | 0 | 1 (008) | 0 |
| **Total** | **13** | **8** | **3** | **1** | **1** |

The count went 12→**13** on 2026-08-21 with RISK-013, which is not a new finding but a
**re-classification**: the `RandomStringPassword` static false-negative had been filed as scope
boundary (c) of RISK-010, inheriting that risk's Effect of *Tolerable*. It is not tolerable — it
corrupts the denominator of the frozen `jca` set, which is the published measurement ruler, and it
does so **silently**. Filed under its own id at its own level, per the researcher's instruction of
2026-08-21. What also changed on that date is that the Level column now means *inherent* risk
consistently, and disposition moved to its own columns. Reading the total as a count of live risks
was always wrong — five of the thirteen are not open.

**Rubric (published 2026-08-21 — previously implicit and applied inconsistently).** Level = f(Probability,
Effect), on *inherent* risk, before mitigation:

| | Tolerable | Serious | Critical |
|---|---|---|---|
| **High** | Medium | High | Critical |
| **Moderate** | Medium | High | Critical |
| **Low / Very Low** | Low | Medium | High |

Three prior assignments did not follow it and are reconciled below: RISK-009 (Moderate×Serious) was
Medium while RISK-001 with the same pair was High — RISK-009 is raised to **High**; RISK-012
(High×Tolerable) was Low while RISK-010 with the same pair was Medium — RISK-012 is raised to
**Medium**; RISK-011 (High×Serious) was Medium because the *post-decision* state was recorded in the
Level column — its inherent level is **High**, carried in the table with Status "Closed by design". The
Level column now always means inherent risk; the Status column carries the disposition.

| ID | Title | Category | Prob. | Effect | Level |
|----|-------|----------|-------|--------|-------|
| RISK-001 | Target super-type **phantom**/absent → `canStoreType` silent wrong `false` | Technology (external dep) | Moderate | Serious | **High** |
| RISK-002 | JCA parity regression (INV-ANA-35 / `MopSpecsParityTest`) | Product (regression) | Low | Serious | **Medium** |
| RISK-003 | Out-of-order rebuild links stale `.m2` extractor (fix never ships) | Tools (build coupling) | Moderate | Tolerable | **Medium** |
| RISK-004 | Quasi-universal targets saturate `reachesTarget` (measured); owner-filtering measured **not** to fix it | Requirements (scope) | High | Serious | **High** |
| RISK-005 | `canStoreType` cost at **both** match points (scan **and** `resolveInScene`) | Technology (performance) | Low | Tolerable | **Low** |
| RISK-006 | Owner unresolvable because its package is imported by no import of its own spec (was framed as "non-JDK owner") — **observed in the corpus**, repaired by task 1.0b | Technology (extractor) | Very Low | Tolerable | **Low** |
| RISK-007 | Accidental output-schema change breaks the JSON consumers (3 Python readers; ape reads the *derived* artifact) | Product (interface) | Low | Serious | **Medium** |
| RISK-008 | Sync/archive ordering on `analysis` — gh60/gh66 now synced (constraint satisfied); residual = gh70 INV-ANA-45 anomaly + Phase-6 slot check | Process (sync ordering) | Low | Tolerable | **Low** |
| RISK-009 | Second match point left non-subtype-aware (bytecode-scan contract gap) | Product (architecture) | Moderate | Serious | **High** |
| RISK-010 | Non-`call()` pointcuts uncovered: 3 `staticinitialization`-only specs + 3 ctor pointcuts yield no static targets | Requirements (coverage boundary) | High (certain) | Tolerable | **Medium** |
| RISK-011 | Seeding the implicit `java.lang` package moves the frozen `jca` set and over-matches under LENIENT | Product (measurement integrity) | High if seeded | Serious | **High** |
| RISK-012 | Java test infrastructure does not run: extractor has none (tasks 1.0/1.4–1.6) **and** the gator skips its own tests by default (`rvsec-gator/pom.xml:18`), yielding a false green | Tools (build) | High (certain) | Tolerable | **Medium** |
| RISK-013 | `RandomStringPasswordSpec` contributes zero static targets to the frozen `jca` set, silently — the denominator of every published `cov_reaches_target` is computed over 22 of 23 specs | Product (measurement integrity) | High (certain) | Serious | **High** |

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
  only surface much later, in the downstream reachability sweep (whose corpus has since moved from the
  400-APK set to `rvsec-dataset` — see proposal Impact).
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
    **20** owners that reach `forceResolveTargets` (21 distinct `call()` owners minus `TreeMap`, which
    occurs only in the skipped constructor pointcut); any >0 is a Yellow trigger (forceResolve not
    populating hierarchy under prod config).
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
- **Gate now has an owner task**: `BaselineComparisonIT` on `cryptoapp.apk` was named as the end-to-end
  half of this gate but executed by no task until **task 5.1b** was added (2026-08-21). Failsafe ITs are
  skipped by default (`client/pom.xml:18`), so the command must pass `-DskipITs=false`.
- **Probability**: Low (the design's predicate explicitly branches on `includeSubtypes`, false for JCA)
  · **Effect**: Serious (JCA is the primary production spec set, and it is the published measurement
  ruler — every experiment run does static analysis against `jca` regardless of `--specification-set`,
  because `mop_dir` is never set by `rv-experiment`/`rv-platform`) · **Level**: Medium
- **Mitigation strategy**: Minimization (structural) + verification gate
  - JCA owners carry **no `+`** and **no wildcard method name** → extractor sets `includeSubtypes=false`,
    `nameIsPattern=false` → predicate falls through to today's exact `equals` (design "API Design",
    proposal closing paragraph). The subtype branch is **unreachable** for JCA by construction.
  - **Gate (corrected 2026-08-21)**: the load-bearing gate is the **literal count** in the extractor
    test — `jca` 120 signatures / 68 `(class, method)` pairs / 22 owners, `jca_android` 119/67/22, all
    flags false (task 1.5). `MopSpecsParityTest` is NOT that gate: it compares
    `MopSpecsTargetSource.load()` with `JavamopFacade.listUsedMethods()` over the same directory, so both
    sides run through the modified visitor and any extractor-side JCA drift passes it unnoticed; its
    fixtures are `CipherSpec`/`MessageDigestSpec` only. `BaselineComparisonIT` on `cryptoapp.apk` is the
    complementary end-to-end gate (measured: that APK has 0 `String.valueOf`/`toCharArray` call sites, so
    it is insensitive to the RISK-011 axis).
- **Indicators**: JCA target count == 120 (and `jca_android` == 119); JCA-target flags all false;
  `MopSpecsParityTest` Green/Red (necessary, not sufficient).
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
  - **Overlap with gh66 — RESOLVED (updated 2026-08-21)**: `gh66-gator-wtg-flowcontainer-perf` touched
    the same `FlowgraphRebuilder.java` in the same `sootandroid` module gh69 rebuilds. It is **archived
    since 2026-06-18** and its change is in the source tree, so the earlier coordination burden ("rebuild
    from a tree that includes the latest gh66 WIP") no longer applies. What survives is the plain
    requirement that the rebuild carry both the arity guard (gh60/`e584894a`) and gh66's perf change —
    satisfied by building the current tree. Related fact worth recording: `Configs.cgDelegation` defaults
    to **`false`** (`Configs.java:89`), contradicting the comment at `FlowgraphRebuilder.java:1030`, so the
    guards protect the non-default path; the live caller of `buildCallGraphLegacy` is
    `FlowgraphRebuilder.java:1065` (an earlier note said `:980`, which is a different method).
- **Probability**: Moderate (easy to get wrong; multi-step manual build) · **Effect**: Tolerable
  (caught quickly by the target-count check, recoverable by re-running in order) · **Level**: Medium
- **Mitigation strategy**: Avoidance (process) + Minimization
  - **Mandatory ordered build (D6)**: `mvn install` extractor **first** → then rebuild gator `client`.
  - **Build from the reactor root, never from inside the module (added 2026-08-21)**: `main.basedir` is
    resolved by `directory-maven-plugin` against the `br.unb.cic:rvsec-parent` project and does not
    resolve in a standalone module build. The tree already contains the residue of that mistake —
    `rvsec/rvsec-mop-extractor/${main.basedir}/rv-android/lib/mop-extractor/mop-extractor.jar` as a
    literal directory (also present under `rvsec-apk`, `rvsec-frame-computer`, `rvsmart`). The `~/.m2`
    install still happens, so the failure is silent: the fat jar picks up the fix while
    `rv-android/lib/` keeps the stale copy. Tasks 4.1/4.2 now run from the reactor root with JDK 21.
  - Include `sootandroid` in the rebuild `-pl` to preserve the `FlowgraphRebuilder` arity guard
    (proposal "Impact: Invariant preserved").
  - Encode the order in `tasks.md` as explicit sequential steps (not a single "rebuild JARs" task).
- **Indicators**:
  - Extractor target count for `generic_new` is **N>0** (not 0) **after** the gator rebuild — the
    canary that the fresh extractor is actually inside `rvsec-analysis-client.jar`.
  - JAR build timestamp under `rv-android/lib/gator/` **and** `rv-android/lib/mop-extractor/` newer than
    the source edit; no new literal `${main.basedir}` directory anywhere under `rvsec/`.
  - WTG SPARK run does not regress to `ArrayIndexOutOfBoundsException`.
- **Contingency**:
  - **Trigger**: post-rebuild generic target count still 0, or WTG crash returns.
  - **Actions**: `mvn install` extractor, confirm the new artifact in `.m2`, rebuild gator with
    `sootandroid` included, re-copy JARs to `lib/gator/`, re-run the canary.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-004: Quasi-universal targets saturate `reachesTarget` — measured, and owner-filtering does not fix it
- **Category**: Requirements (scope boundary)
- **Description**: Once subtype matching is on, the union of the 67 `generic_new` target pairs marks so
  many call sites that `reachesTarget` collapses onto `reachable` — it stops meaning "reaches a monitored
  operation" and starts meaning "is reachable at all". **Measured 2026-08-21** over 8 corpus APKs
  (0.2–75 MB; 205,519 bodied methods, 827,443 call sites) via `dexdump -d` + an `android.jar` hierarchy
  parse + reverse closure, with the direct axis calibrated against the real `directlyReachesTarget` in the
  shipped `jca` `*.apk.json` files — exact on 7 of 8 APKs (`cryptoapp` 21 = 21), so the direct figures are
  measurement, not estimate:

  | signal | `jca` (measured, shipped) | `generic_new` (measured, repaired) |
  |---|---|---|
  | `directlyReachesTarget` | 0.0–0.3% of app methods | **2–12%** |
  | `reachesTarget` | 11–47% | **84–94%** (rigorous lower bound) |

  The `reachesTarget` lower bound **exceeds the anchor's own `reachable` fraction** on 4 of the 8 APKs
  (mupen 93.8% > 82.4%; rcx 91.7% > 86.9%; flym 87.5% > 85.3%; quicknote 87.2% > 79.5%): the binding
  constraint stops being the target set and becomes reachability itself. Raw scale: 34,411 of 827,443 call
  sites (4.16%) match one of the 67 pairs, against 225 (0.027%) for `jca` — **153×**.

  **The owners this risk used to name were the wrong ones.** Measured share of app methods marked directly,
  per pair: `Object+` accounts for **0.02%** of all call sites and `Object+.notifyAll` marks **zero** methods
  across the whole sample; `Comparable+.compareTo` is moderate (0.31%); `Iterable+` is wide through exactly
  one of its two methods (`iterator` 1.84%, `listIterator` zero). The real vectors are `Collection+.add*`
  (2.50%), `CharSequence+.equals` (2.10%), the `Iterator` family (1.88% × 4), `Iterable+.iterator` (1.84%),
  `Collection+.iterator` (1.68%) and `Closeable+.close` (1.12%) — none of which this risk named. The first
  two are wide for a **structural** reason rather than a semantic one: the extractor drops the
  `!target(String)` / `target(ByteArrayInputStream)` residues, so the static target captures every
  `String.equals` and every `close()` while the woven aspect fires on almost none of them. Over 3 APKs,
  100% of `equals`/`hashCode` call sites on a `CharSequence` have receiver `java.lang.String` — the exact
  type the spec excludes. This compounds with scope boundary (d).
- **Probability**: High (measured, not predicted) · **Effect**: **Serious** (the transitive signal
  degenerates, the previously accepted mitigation is refuted, and shipped code changes verdict) ·
  **Level**: **High** (per the published rubric, High × Serious)
- **Mitigation strategy**: Acceptance of the *matcher* behaviour, with the scope claim **corrected** — the
  earlier "the downstream dataset change will filter the quasi-universal owners" is empirically refuted.
  - **Refutation (measured)**: dropping 34 of the 67 pairs — the entire collection/iterator/CharSequence
    family — does **not** move `reachesTarget` on any medium or large APK: quicknote 1752→1752,
    geometerplus 1358→1358, rcx 2514→2513, flym 2247→2245, mupen 2342→2340. Only the tiny APKs react
    (cryptoapp 65→57, t20kdc 116→10). The I/O residue alone (`InputStream+`, `OutputStream+`, `Reader+`,
    `Writer+`, `Closeable+`) is already spread widely enough through the bundled libraries to reproduce the
    saturation. **Owner blacklisting cannot repair the transitive signal**; at best it repairs
    `directlyReachesTarget`, which does not need repairing.
  - **What this change therefore delivers for `generic_new` is `directlyReachesTarget`.** Under `jca` that
    field has an unusably small denominator (0–3% of methods, sometimes 0 or 1 method in a whole APK); under
    `generic_new` it becomes 2–12% — a usable one. `reachesTarget` should be **declared degenerate** for this
    spec set, not filtered. The two sets are complementary on the two axes rather than redundant: `jca`
    discriminates transitively and is noise directly; `generic_new` is the reverse. This is a property of the
    two API families, not a defect introduced here.
  - Still guard against scope creep: do **not** add owner-blacklisting to the matcher (P1 simplicity) — now
    for the stronger reason that it is **measured not to work**.
  - The one narrowing that survives the union is `target()`-of-type, and only for two pairs
    (`CharSequence+.equals`/`hashCode`, and the non-`java.io` part of `Closeable+.close`), worth 11–41% of
    the direct seed over 3 APKs. That is a separate change — see scope boundary (d).
- **Indicators**:
  - `reachesTarget` ≈ `reachable` on the IT APK is **expected**, not a matcher defect.
  - `directlyReachesTarget` failing to land in the 2–12% band **is** a defect signal — it is the field that
    carries the deliverable, so task 4.3 should read it rather than `reachesTarget`.
  - `aperv-tool` returning `hot` for every APK is the shipped-code symptom, not a tuning issue.
- **Contingency**:
  - **Trigger**: a consumer depends on `reachesTarget` discriminating under `generic_new`.
  - **Actions**: move that consumer to `directlyReachesTarget`; do not attempt owner filtering.
    **`aperv-tool` is already such a consumer and breaks in the same commit this change lands**:
    `sa_methods_reaches_mop` degenerates toward `total_methods` as its count-model offset
    (`static_artifact.py:13-17`), and the `hot`/`cold`/`unresolved` verdict (`static_artifact.py:288-296`)
    collapses to `hot`. That is production code, not a future dataset filter, and needs its own decision
    before or with Phase 4. The 2026-08-21 audit recorded this in the change log (item (i)) but the risk body
    was never updated — it is now.
  - **Owner**: change author (matcher) / `aperv-tool` owner (consumer).
- **Evidence**: `docs/20260821_gh69_veredito_coringas.md` §4.3–§4.5 — commands, per-APK tables, the per-pair
  ranking over 827,443 call sites, and the calibration of the measurement pipeline against the `jca` anchor.
- **Status**: Open (accepted as matcher behaviour; **re-scoped 2026-08-21** — mitigation refuted, effect
  raised to Serious, level Medium→High)

---

### RISK-005: `canStoreType` cost at **both** match points (bytecode scan **and** `resolveInScene`)
- **Category**: Technology (performance)
- **Description**: Two hot loops, not one. (a) The direct bytecode scan iterates every invoke; adding
  `canStoreType` per candidate adds cost. (b) **`TargetResolver.resolveInScene` (verified) iterates
  `Scene.getClasses()` × methods × targets and today fast-rejects via `t.getClassName().equals(fqn)`
  before any work** — for `includeSubtypes` targets that string fast-reject **disappears**, turning every
  (Scene-method × subtype-target) pair into a `canStoreType`. With `android.jar`/JDK in whole-program
  that is tens of thousands of classes × the subtype targets. Sizing note (corrected 2026-08-21): the
  figure **71** is the count of `call()` *pointcuts* carrying a `+` owner, not of distinct targets — the
  whole corpus yields at most **67** distinct `call()` pairs, of which only **54** carry a `+` and therefore
  reach the `canStoreType` path at all (re-derived 2026-08-21; the other 13 stay on the exact path with the
  JCA owners). Note also that `canStoreType` is **not** O(1) amortized when the declared super-type is an
  interface, and 10 of the 16 distinct `+` owners are interfaces: the interval encoding
  (`classToInterval`) exists for classes only, so an interface parent falls to a linear scan over
  `getAllImplementersOfInterface` — or, above 100 implementers, to the `canStoreClassClassic` BFS.
  Measured against `android.jar` (android-30): `Comparable` 245 subtypes and `Closeable` 154 take the BFS
  branch; `Iterable` 67, `Collection` 38, `Map` 19, `Queue` 17, `CharSequence` 15, `Set` 11, `Iterator` 9
  take the linear scan; only `Reader+`/`Writer+`/`InputStream+`/`OutputStream+`/`ServerSocket+`
  (class→class) get the O(1) interval test, and `Object+` short-circuits before `canStoreClass`. The
  bound below therefore holds on target *count*, not on per-query cost, so the subtype target count is
  bounded by
  that. The original register covered only the scan; `resolveInScene` is the larger hot spot.
- **Probability**: Low · **Effect**: Tolerable · **Level**: Low
- **Mitigation strategy**: Minimization + measurement
  - `FastHierarchy.canStoreType` is **O(1) amortized** (interval-encoded class hierarchy).
  - **Mandatory ordering**: evaluate `nameMatches` **before** `canStoreType` at both points (cheap name
    short-circuit replaces the lost `equals(fqn)` fast-reject) — promoted from contingency to design
    requirement (tasks 2.3/3.1).
  - **Cache** the resolved `superType(t)` `RefType` once per target (not per invoke/per Scene-method).
  - Measure wall-time of **both** the scan and `resolveInScene` in the IT; compare to a JCA-equivalent
    run. This is **task 4.8**, added 2026-08-21 — until then the trigger below was a hard gate that no
    task actually measured.
- **Indicators**: IT scan time **and** `resolveInScene` time each ≤ **2×** the JCA baseline (this is the
  single gate — the earlier "same order of magnitude" phrasing was looser than the trigger and is superseded).
- **Contingency**:
  - **Trigger**: scan or `resolveInScene` time > 2× the JCA baseline on the IT APK.
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

### RISK-007: Accidental output-schema change breaks the JSON consumers
- **Category**: Product (interface contract)
- **Description** (**corrected 2026-08-21 — the earlier "two parsers" framing was wrong on both halves**):
  the raw GATOR JSON has **three** independent readers, not two: the Python `static_analysis_parser.py`
  boundary in `rv-static-analysis` (`:98-99`); the repo gate/sweep scripts under `scripts/`; and
  **`aperv-tool`**, which parses `<apk>.json` itself and imports nothing from `rv_static_analysis`
  (`analysis/static_artifact.py:261,270-271,293,359`; `tools/aperv/derive_mop_artifact.py:421-422,1029,1158`).
  The ape `MopData.java` is **not** among them: it reads the *derived* `*.mop.json`, where the key has
  already been renamed `reachesTarget` → `reachesMop` (`derive_mop_artifact.py:1158`), and it hard-rejects
  any document lacking `formatVersion == 1` (`MopData.java:207-213`). Its `opt*` tolerance therefore
  provides **no** protection for this risk — and worse, that tolerance is silent-default
  (`optBoolean("reachesMop", false)`), so a slip degrades to "nothing reaches MOP" rather than erroring.
  The component genuinely exposed to a GATOR key change is `derive_mop_artifact.py`, which is **not**
  tolerant: `method.get("reachesTarget") is True` at `:422` turns a rename into a silent `False`.
  An accidental key add/rename/removal while editing the writer area would break these consumers silently,
  even though no schema change is intended.
- **Probability**: Low (the change explicitly touches matching, not the JSON writer) · **Effect**:
  Serious (silent breakage of downstream coverage + ape) · **Level**: Medium (reclassified for
  consistency with RISK-002, also Low×Serious → Medium; the previous "Low" was internally inconsistent)
- **Mitigation strategy**: Avoidance (invariant) + verification gate
  - **Schema invariance is an invariant** (INV-ANA-44, decision B/D3): no JSON writer change at all;
    only boolean *values* of `reachesTarget`/`directlyReachesTarget` move.
  - **Gate**: in the IT, diff the **key-set** of a `generic_new` run against a `jca` run on the same
    APK — must be **identical**. This is a hard gate before archive.
- **Consumer map is wider than `modules/` (added 2026-08-21)**: the three production readers named above
  are complete *for `modules/`*, but six more read the raw JSON elsewhere and none were in the impact
  analysis: `tests/parity/test_reachability_parity.py:158,165,166`,
  `tests/parity/test_baseline_freshness.py:119,122`,
  `tests/parity/test_historical_methods_coverage.py:134`, `tests/parity/test_gh60_sweep_delta.py:63-64`,
  `docs/20260803_charac_static_corpus.py`, and
  `experimento-comp162-ajc/scripts/{covadjust.py:97,analise.py:211}`. The consequential ones are the
  **value**-stability gates: `test_reachability_parity.py:156` (`G_paridade_targets`) freezes the *set*
  of signatures carrying `reachesTarget=true` against a committed baseline, and
  `test_historical_methods_coverage.py:134` pins three methods at `directlyReachesTarget=true`.
  INV-ANA-44 guarantees only **key-set** invariance; these two guard **values** — precisely what this
  change moves. They run against the default `mopDir` (`jca`), so the JCA-untouched premise is what
  keeps them green, and a JCA regression would surface here before it surfaced anywhere else.
- **Indicators**: generic-vs-jca JSON key-set diff is empty; `static_analysis_parser.py` parses the
  generic output without error (now asserted by **task 4.4**, extended 2026-08-21 — the key-set diff alone
  never covered it); `aperv-tool`'s `static_artifact.py` still resolves signatures on the generic output;
  `tests/parity/test_reachability_parity.py` and `test_historical_methods_coverage.py` stay green.
- **Contingency**:
  - **Trigger**: key-set diff non-empty, or a consumer fails to parse.
  - **Actions**: revert any writer-area edit; confirm the boolean-only change set; re-run the diff.
  - **Owner**: implementer.
- **Status**: Open

---

### RISK-008: Sync/archive ordering on the `analysis` capability (largely mitigated — gh60/gh66 already synced)
- **Category**: Process (OpenSpec sync ordering / cross-change dependency)
- **Description**: The original hazard was a **3-way ordering** constraint: gh69's delta **references**
  INV-ANA-33/35 (the gh60 `TargetMethod`/`MatchPolicy`/`TargetResolver` abstraction), so syncing gh69
  before gh60 would leave dangling references in `openspec/specs/analysis/spec.md`. **As of 2026-07-06
  this hard ordering constraint is satisfied** — verified against the repo:
  - **gh60-targets-core** is **archived** (`openspec/changes/archive/2026-06-17-gh60-targets-core`), and
    **INV-ANA-33 and INV-ANA-35 are present** in the synced `openspec/specs/analysis/spec.md`. The
    dangling-reference hazard this risk guarded against **no longer exists**.
  - **gh66-gator-wtg-flowcontainer-perf** is **archived** (2026-06-18). Its *requirement* is synced
    (`openspec/specs/analysis/spec.md:1369`), but **INV-ANA-39 has no normative bullet there** — it
    survives only as four narrative/scenario citations, one of them the sub-lettered `INV-ANA-39c`
    (`:1390`). See the sync anomaly below; this is the same defect, not a counter-example to it.
  - Two **later** changes archived after gh66 consumed higher invariant numbers: **gh70-wtg-reachability-sharing**
    (2026-06-18, INV-ANA-45) and **gh72-logcat-diagnostic-events** (2026-06-23, INV-ANA-46/47/48).
  - gh69 claims **INV-ANA-40..44**, which are **free** in the synced spec and claimed by **no** active
    change (full sweep of the active `openspec/changes/` tree, 2026-08-21: the only other active `analysis`
    delta is gh104, which sits at INV-ANA-62/63), so gh69 can sync 40-44 **without collision**.

  **Residual (why this is not yet Closed):**
  1. **Sync anomaly — systemic, not a one-off (restated 2026-08-21)**. The synced `analysis/spec.md`
     bullet inventory jumps **38 → 46,47,48**, not 39 → 46. Three post-gh60 invariants have no bullet
     there: **INV-ANA-39** (gh66), **INV-ANA-45** (gh70) and **INV-ANA-55** (gh92, archived 2026-08-02).
     Separately, gh69 cites INV-ANA-17, INV-ANA-18 and BUG-INV-ANA-19 as though defined in the synced
     spec; there they exist only as narrative references, their normative bullets living in the gh51
     archive. Whether gh69's own sync must wait on that backfill is the open question. gh69's insertion of 40-44 is
     **non-contiguous** (39 and 45 absent below it, 46-48 taken above) but **collision-free**, so it is a
     spec-inventory gap to reconcile at gh69 sync, not a blocker for gh69's own numbers. (An earlier
     "Original note" here stated the jump as **39 → 46, 47, 48**; that was wrong and is deleted —
     measured 2026-08-21, the normative bullets run `… 37, 38, 46, 47, 48 …`.)
  2. **Phase-6 slot re-check** — before `/opsx:archive`, re-confirm 40-44 are still free (no new change
     grabbed them in the interim) and that INV-ANA-33/35 are still present.
- **Probability**: Low (the hard ordering dependency is already discharged; only a bookkeeping re-check
  and one inventory anomaly remain) · **Effect**: Tolerable (caught at sync time; recoverable, no data
  loss) · **Level**: Low
- **Mitigation strategy**: Avoidance (process) — largely discharged
  - **Ordering constraint satisfied**: gh60 and gh66 are archived and synced; gh69 no longer depends on
    an un-synced predecessor.
  - **At gh69 Phase 6**, before `/opsx:archive`: (a) confirm `openspec/specs/analysis/spec.md` still
    contains INV-ANA-33/35 (it does today) and that 40-44 are still unclaimed; (b) reconcile the gh70
    INV-ANA-45 gap — decide whether gh69's sync should backfill 45 or leave it for a gh70 re-sync, so the
    synced inventory ends contiguous.
- **Indicators**:
  - `grep -n 'INV-ANA-33\|INV-ANA-35' openspec/specs/analysis/spec.md` **non-empty** (currently true).
  - `grep -n 'INV-ANA-4[0-4]' openspec/specs/analysis/spec.md` **empty** before gh69 sync (slots free).
  - `grep -n 'INV-ANA-45' openspec/specs/analysis/spec.md` — currently **empty** (the anomaly); watch
    whether it is backfilled at gh69 sync.
- **Contingency**:
  - **Trigger**: at gh69 Phase 6, INV-ANA-40..44 are no longer free, INV-ANA-33/35 are missing, or the
    45 gap causes a non-contiguous synced inventory that a reviewer flags.
  - **Actions**: renumber gh69's delta to the next free contiguous block if 40-44 got taken; if
    INV-ANA-33/35 regressed, re-sync gh60's delta; reconcile the gh70 INV-ANA-45 gap (backfill at gh69
    sync or open a gh70 re-sync) so `analysis/spec.md` ends contiguous.
  - **Owner**: change author (archive sequencing).
- **Status**: Largely mitigated — near-closeable (residual = Phase-6 slot re-check + gh70 INV-ANA-45 reconciliation)

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
  **Level**: High (raised 2026-08-21 to match the published rubric — Moderate×Serious, the same pair as
  RISK-001, which was already High)
- **Mitigation strategy**: Avoidance (explicit contract change) + verification
  - Extend `ReachabilityEngine`'s constructor/`run(...)` and `findDirectTargetCallersByBytecodeScan` to
    also carry `Set<TargetMethod> targetSpecs`; **hybrid scan** preserving the `Set<String>` exact path
    for `!includeSubtypes` (JCA O(1)/parity) + per-invoke `canStoreType` for `includeSubtypes` targets
    (now an explicit step in **task 3.2**, with design Data-Flow §5 describing the cascade).
- **Indicators**: a `generic_new` IT method reachable **only** via the direct bytecode scan (not the CG)
  reports `directlyReachesTarget=true` — now asserted by **task 4.7**, added 2026-08-21; until then this
  indicator was owned by no task. Supporting fact: `RvsecAnalysisClient.java:115` `targetSpecs` is today a
  **dead local** (assigned in both branches, never read), which is exactly the gap the cascade closes.
- **Contingency**:
  - **Trigger**: the scan still consumes `Set<SootMethod>`/`targetKeys` after implementation.
  - **Actions**: thread `Set<TargetMethod>` through `ReachabilityEngine`; re-run the scan-only IT.
  - **Owner**: implementer (gator client).
- **Status**: Open

---

### RISK-010: Non-`call()` pointcut shapes yield no static targets (3 staticinit-only specs + 3 constructor pointcuts)
- **Category**: Requirements (coverage boundary) — surfaced by the 2026-07-09 multi-agent artifact
  validation (ground-truth pass over the 27 `.mop` files).
- **Description**: The extractor design covers `call(...)` pointcuts only. (a) Three specs whose ONLY
  pointcut is `staticinitialization(Owner+)` — `Collection_HashCode`, `Serializable_NoArgConstructor`,
  `URLConnection_OverrideGetPermission` — emit **zero** static targets and can never set
  `reachesTarget`, though the runtime monitor still fires on class-load. (b) Three constructor pointcuts
  `call(Owner.new(..))` (`ServerSocket.new` ×2, `TreeMap.new`) are not extracted (Soot models
  constructors as `<init>`; no `new`→`<init>` mapping); both owning specs keep other `call()` targets.
  Net static coverage: 24/27 specs. The distinct-owner total is 23 (21 `call()` owners + `Serializable`/
  `URLConnection` from staticinit); of the 21 `call()` owners only **20** reach `forceResolveTargets`,
  since `TreeMap` occurs solely in the skipped constructor pointcut — that 20 is the number the task 4.3
  gate asserts. (c) **Moved out of this risk on 2026-08-21.** The `jca`/`jca_android`
  false-negative of `RandomStringPassword.mop` used to be carried here, and inherited this risk's
  Effect of *Tolerable*. It is not tolerable — see **RISK-013 (High)**, which now owns it. This risk
  keeps only the pointcut-shape boundary: staticinit-only specs and constructor pointcuts.
- **Probability**: High (certain — structural) · **Effect**: Tolerable (bounded; quasi-universal owners
  dominate `reachesTarget` anyway; runtime coverage unaffected) · **Level**: Medium — this rating
  applies to the pointcut-shape boundary only, now that the `jca` false-negative has moved to RISK-013
- **Mitigation strategy**: Acceptance (documented scope decision)
  - Documented in proposal (coverage boundary), design (Non-Goals), and INV-ANA-40 (scope boundary).
  - Task 1.3(d) logs+skips constructor pointcuts with a notice; task 1.4 asserts exactly 3 ctor-skip
    notices, so the boundary is visible, never silent.
  - A `new`→`<init>` mapping (cheap) and a class-init target concept (non-trivial) are explicit
    candidates for the downstream generic-dataset change, not this one (P1).
- **Indicators**: extractor logs exactly 3 constructor-skip notices for `generic_new`; the 3
  staticinit-only specs absent from the target set (expected); 24/27 specs with ≥1 target.
- **Contingency**:
  - **Trigger**: the downstream dataset change needs class-init or constructor events statically.
  - **Actions**: implement `new`→`<init>` mapping first (small); design class-init targets separately.
  - **Owner**: downstream sweep/dataset change author.
- **Status**: Open (accepted)

---

### RISK-011: Seeding the implicit `java.lang` package moves the frozen `jca` set and over-matches under LENIENT
- **Category**: Product (measurement integrity) — surfaced 2026-08-21 by the sibling session
  (`docs/20260821_handoff_gh69_coringas.md`), reproduced and confirmed independently.
- **Description**: The original task 1.2 seeded `java.lang` "as defense-in-depth", on the belief that no
  current spec needed it. That is true for `generic_new` and **false for `jca`**:
  `RandomStringPassword.mop` names the owner `String` without importing it, and is the ONLY unresolved
  owner in `jca`/`jca_android` (enumerated over 144 + 130 `call()` pointcuts). Seeding therefore takes
  `jca` 120→122 and `jca_android` 119→121. Worse, MOP targets are emitted LENIENT
  (`MopSpecsTargetSource.java:39` — class+name, signature ignored), so the new `String#valueOf` target
  matches every overload: measured over 3 corpus APKs, 74 call sites of `String.valueOf`/`toCharArray`
  of which only 17 correspond to the woven signatures (`valueOf(Object)` ×14, `toCharArray()` ×3); the
  other 57 are `valueOf(int)`/`valueOf(long)` in `toString`/log code. `reachesTarget` is transitive, so
  each false positive propagates to all its callers, and it feeds the coverage denominator (INV-ANA-15)
  of the spec set that is the published measurement ruler. Two distinct samples are quoted here and must
  not be conflated: the 74/17/57 call-site breakdown was measured over **3** corpus APKs, while a
  separate **12**-APK sample was used only to gauge how widespread the pattern is (8 of the 12 carry ≥1
  such call site).
- **Probability**: High **if** the seed ships · **Effect**: Serious (silently degrades published JCA
  measurements) · **Level**: High — **retired by design decision, not by mitigation** (the Level column
  is inherent risk, per the published rubric: High×Serious → High; the disposition lives in Status)
- **Mitigation strategy**: Avoidance
  - D5 / INV-ANA-40 now forbid the seed: owner resolution comes only from imports the spec declares.
    `generic_new` is unaffected — all **seven** of its `java.lang`-owner specs carry `import java.lang.*;`
    (`Object_MonitorOwner`, `Comparable_CompareToNull`, `Comparable_CompareToNullException`,
    `CharSequence_UndefinedHashCode`, `Long_BadParsingArgs`, and — owner `Iterable` — `ListIterator_Set`
    and `Map_UnsafeIterator`).
  - The false-negative it would have "fixed" is documented instead (INV-ANA-40 scope boundary (c)), with
    its measurements, so the follow-up change does not have to re-derive them. **That false-negative is
    itself a High risk in its own right — RISK-013.** Avoiding the seed is correct and does not make the
    hole benign: this risk says "do not half-repair it", RISK-013 says "the hole is grave". Both hold.
  - The real repair needs three things together — owner visibility (explicit import, an FQN-owner rule,
    or the seed) + a STRICT policy for that target + FQN parameter resolution in `getParams` — and is
    tracked as its own issue (task 5.6). Any one of the three alone makes the measurement worse.
- **Indicators**: `jca` target count stays 120 and `jca_android` 119 after the extractor change; the
  extractor log shows `String` as a skipped owner; `BaselineComparisonIT` unchanged (`cryptoapp.apk` has
  0 such call sites — measured).
- **Contingency**:
  - **Trigger**: a future change proposes seeding `java.lang` or importing `String` in the spec.
  - **Actions**: require the STRICT-policy and `getParams` FQN work in the same change, plus a re-run of
    the JCA measurements that the seed invalidates; do not land the visibility half alone.
  - **Owner**: follow-up change author.
- **Status**: Closed by design (D5) for this change; open as follow-up scope.

---

### RISK-013: `RandomStringPasswordSpec` contributes zero static targets to the frozen `jca` set — silently
- **Category**: Product (measurement integrity) — surfaced 2026-08-21 by the sibling session
  (`docs/20260821_handoff_gh69_coringas.md`, there called N9), reproduced independently the same day.
  **Promoted to its own id on 2026-08-21 by the researcher's instruction**, after having been filed as
  scope boundary (c) of RISK-010 and inheriting that risk's Effect of *Tolerable*.
- **Description**: `RandomStringPassword.mop` names its owner `String` and never imports it — implicit
  in Java, not for the visitor. `UsedJcaMethodsVisitor:70-77` keys pointcut extraction on the explicit
  import map and has **no `else` and no log**, so both of its pointcuts vanish without a trace. The
  spec is 1 of the 23 in `jca` and 1 of the 23 in `jca_android`, and it is the **only** unresolved owner
  in either set (enumerated over the 144 `jca` and 130 `jca_android` `call()` pointcuts). The woven
  aspect carries both pointcuts — `rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879`,
  the canonical 1042-line copy, verified 2026-08-21 (the ~40 generated copies elsewhere in the tree are
  shorter and do not contain these lines). So the monitor advises call sites that the static layer never
  marks as targets.

  **What this costs, stated exactly.** The harm is in the reach denominator, not in the violation
  counts. Across every campaign in the tree, 16 distinct specs appear in `errors.csv` and
  `RandomStringPasswordSpec` is **not among them** — no published violation count is wrong. What *is*
  wrong is that `cov_reaches_target` and `cov_directly_reaches_target` have been computed over
  **22 of the 23** `jca` specs in every measurement ever published from that set: the 120 signatures /
  68 pairs / 22 owners the extractor emits are the count *after* the two `String` pointcuts were
  dropped. `jca` is the frozen ruler against which `jca_android` and the gh104 campaign are compared
  (`experimento-gh104/CONTEXTO.md:159-161`), so the hole is in the instrument itself.

  **Why the level is High and not Tolerable.** Three properties compound: (i) the failure is
  **silent** — no log, no count, no gate ever reported it, and it took a targeted audit to find;
  (ii) it is **structural and repeating** — any spec added later to `jca` whose owner is unimported
  disappears the same way, and nothing in the pipeline would say so; (iii) it lands on the
  **published measurement ruler**, not on a diagnostic. Probability × Effect under the register's own
  rubric (High × Serious) gives **High**; filing it as *Tolerable* under RISK-010 is what kept it
  invisible for the life of the project.
- **Probability**: High (certain — structural, present in every run to date) · **Effect**: Serious
  (silently understates the published `jca` reach denominator) · **Level**: **High**
- **Mitigation strategy**: Acceptance for this change, with a **visibility** mitigation that this
  change does deliver
  - **What gh69 fixes**: the log-and-skip rule of INV-ANA-40 (task 1.3(b)) converts the silent drop
    into a logged skip. After this change the extractor names `String` as a skipped owner instead of
    swallowing it — property (i) above is discharged here, and it is the property that made the risk
    grave rather than merely known.
  - **What gh69 deliberately does NOT fix**: the measurement itself. Seeding the implicit `java.lang`
    package alone would take `jca` 120→122 and `jca_android` 119→121 and, under LENIENT matching,
    make `String#valueOf` match every overload — 74 call sites over 3 corpus APKs, 17 of them woven,
    57 false positives propagated transitively (RISK-011). **The half-repair is worse than the hole.**
  - **The full repair needs three things together** — owner visibility, a STRICT policy for that
    target, and FQN parameter resolution in `getParams` — and is tracked as task 5.6.
  - Task 1.5 asserts that `String` stays unresolved **and logged**, so the boundary cannot silently
    close or silently widen.
- **Indicators**: the extractor log names `String` among skipped owners for `jca`/`jca_android`;
  `jca` stays at 120 signatures / 68 pairs / 22 owners; for `jca_android` the triple 119/67/22 is a **2026-08-21 observation, not a frozen gate** — gh105 is actively editing that set (`call(` 144 → 130 since commit `42a3528`, with 39 of its 74 tasks still open, Group 5 adding new `<Chain>Junction.mop` files). Task 1.5 therefore derives the `jca_android` count by enumeration; only `jca` is asserted literally; the follow-up
  issue of task 5.6 exists and carries the 74/17/57 measurement.
- **Contingency**:
  - **Trigger**: a published result depends on the `jca` reach denominator being complete, or a new
    spec is added to `jca`/`jca_android` whose owner is unimported.
  - **Actions**: land the three-part repair of task 5.6 as one change, and re-run the `jca`
    measurements it invalidates; never land the visibility half alone.
  - **Owner**: follow-up change author (task 5.6).
- **Status**: Open (accepted for this change — visibility mitigated here, measurement deferred to 5.6)

---

### RISK-012: the Java test infrastructure does not run — extractor has none, gator skips its own
- **Category**: Tools (build)
- **Description**: Two independent build traps, same shape and same phase.
  **(a) Extractor has no test infrastructure**: `rvsec-mop-extractor` has no `src/test` directory and
  declares no test dependency (verified 2026-08-21). Tasks 1.4–1.6 assume `mvn test` works there, so
  implementation stops on the first task that writes a unit test.
  **(b) The gator skips its own tests by default** (found 2026-08-21, and the sharper half): the gator
  parent `rvsec/rvsec-android/rvsec-gator/pom.xml:18` sets `<skipTests>true</skipTests>`, overriding the
  reactor root's `false` (`rvsec/pom.xml:21`) for `commons`, `sootandroid` and `client`. Failsafe honours
  `skipTests` as well, so `-DskipITs=false` alone does **not** enable the ITs. Unlike (a), this one does
  not stop anything — it produces a **false green**: `mvn ... test` prints `Tests are skipped.` and exits
  BUILD SUCCESS, so every verification gate in this change would tick without executing. Measured from
  the reactor root under JDK 21: with `-DskipTests=false`, `Tests run: 178, Failures: 0, Errors: 0,
  Skipped: 0`; without it, zero. The line dates from `d94e33cc "starting rvsec-gator"` (2024-09-25),
  when the module was freshly vendored and held no RV-Android test; the project's own gator tests
  (gh27 2026-02-24, gh60 2026-05-25) were all born skipped, and no automated path runs them today
  (CI `ci.yml:30` uses `-DskipTests`; its only `-DskipTests=false`, `:44`, is scoped to `-pl grammar-tests`).
- **Probability**: High (certain — both verified in the tree) · **Effect**: Tolerable for (a), a
  one-line pom edit; **Serious in kind** for (b), because a skipped gate is indistinguishable from a
  passing one, but bounded because it is equally a one-line fix · **Level**: Medium
- **Mitigation strategy**: Avoidance
  - (a) Task **1.0** declares the `junit` dependency (version inherited from the root reactor
    `dependencyManagement`, junit 4.13.2; no local pin) and creates `src/test/java` + `src/test/resources`
    before any test is written.
  - (b) Task **1.0c**: pass `-DskipTests=false` on every gator maven command (2.5 / 3.3 / 4.3-4.8 / 5.1 /
    5.1b — already applied), **and** delete the `<skipTests>true</skipTests>` line so the trap does not
    outlive this change. Removing it is safe: the suite is 178/178 green.
- **Indicators**: `mvn -pl rvsec/rvsec-mop-extractor test` runs and reports tests (not "no tests"); every
  gator test command reports a non-zero `Tests run:` count — a run that prints `Tests are skipped.` MUST
  be treated as a failed gate, never as a pass.
- **Contingency**: if the root `dependencyManagement` entry ever moves, pin `junit` locally at the same
  version rather than diverging. If deleting the gator `skipTests` line turns out to break an unrelated
  build, fall back to the per-command override and open an issue. **Owner**: implementer.
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
  - [ ] RISK-001 degrade-warning count still 0 for the **20** owners that carry targets; no owner phantom (`isPhantom` guard active)?
  - [ ] RISK-002 parity still byte-for-byte / JCA count == 120?
  - [ ] RISK-003 post-rebuild generic target count > 0; `sootandroid` in rebuild; WTG no crash?
  - [ ] RISK-005 `resolveInScene` + scan wall-time each **≤ 2× the JCA baseline** (task 4.8) — the older "order of magnitude" phrasing is superseded and must not be used?
  - [ ] RISK-007 key-set diff still empty?
  - [ ] RISK-008 (at Phase 6 only) `analysis/spec.md` still has INV-ANA-33/35 (gh60/gh66 already synced) **and** INV-ANA-40..44 still free; gh70 INV-ANA-45 gap reconciled at sync?
  - [ ] RISK-009 bytecode scan carries `Set<TargetMethod>` (scan-only IT method reports subtype `directlyReachesTarget=true`, task 4.7)?
  - [ ] RISK-004 saturation: is `aperv-tool`'s `hot`/`cold` verdict still discriminating on the IT APK, or has `reachesTarget` gone near-universal?
  - [ ] RISK-006 unresolved-owner skip count for `generic_new` still 0 (task 1.0b repair not reverted)?
  - [ ] RISK-010 constructor-skip notices still exactly 3?
  - [ ] RISK-011 `java.lang` still unseeded; `jca` still 120/68/22 and `jca_android` 119/67/22?
  - [ ] RISK-012 extractor test infrastructure present and green (task 1.0)?
  - [ ] Any risk closeable?
- **Owner**: change author (Pedro Costa).

## Change Log

| Date | Risk | Change |
|------|------|--------|
| 2026-08-21 | **RISK-013** | **Added by researcher instruction**, as a re-classification rather than a new finding. The `RandomStringPassword` static false-negative had been filed as scope boundary (c) of RISK-010 and inherited its Effect of *Tolerable*; that filing is what kept it invisible. It is now its own risk at **High** (High × Serious under the published rubric): the drop is silent (`UsedJcaMethodsVisitor:70-77` has no `else` and no log), structural and repeating for any future unimported owner, and it lands on the frozen `jca` set, so every published `cov_reaches_target` was computed over **22 of 23** specs. New measurement recorded so nobody re-derives it: across every campaign in the tree, 16 distinct specs appear in `errors.csv` and `RandomStringPasswordSpec` is not among them — the harm is in the reach denominator, not in the violation counts. The aspect citation was re-verified against the canonical 1042-line `rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879`. Implementation scope is unchanged: gh69 discharges the *silence* via the log-and-skip rule (task 1.3(b), asserted by 1.5); the measurement repair stays deferred to task 5.6. RISK-010 (c) and RISK-011 now cross-reference instead of owning it. Summary 12→13, High 4→5. |
| 2026-06-17 | all | Register created at end of Design phase from `design.md` + `docs/20260617_sa_generic_new.md` §12/§14 |
| 2026-06-17 | RISK-008 | Added (sync ordering gh60→gh69) from adversarial artifact validation `docs/20260617_sa_generic_new.md` §15 |
| 2026-06-17 | RISK-008 / RISK-003 | Broadened to 3-way ordering gh60→gh66→gh69 + gh66 concurrent `FlowgraphRebuilder` edit overlap (per operator note: gh66 in-flight) |
| 2026-06-23 | RISK-001 | Mechanism corrected after **empirical** Soot 4.7.1 verification: phantom owner → `canStoreType` returns silent wrong `false` (does NOT throw; phantom resolves at `BODIES`). Mitigation is an `isPhantom()`/`resolvingLevel` guard, not `try/catch`. |
| 2026-06-23 | RISK-005 | Broadened to cover `resolveInScene` (loss of `equals(fqn)` fast-reject), not just the bytecode scan. |
| 2026-06-23 | RISK-007 | Reclassified Low→Medium for internal consistency with RISK-002 (both Low×Serious). |
| 2026-06-23 | RISK-009 | Added: bytecode-scan/`ReachabilityEngine` contract gap (declared `Set<TargetMethod>` not propagated to the second match point) — from multi-LLM review, source-verified. |
| 2026-07-06 | RISK-008 | Downgraded to **largely mitigated / near-closeable** (Prob. Moderate→Low, Status Open→Largely-mitigated; Level stays Low). Verified against repo: gh60 (INV-ANA-33/35) and gh66 (INV-ANA-39) are **archived and synced** into `analysis/spec.md` — the hard 3-way ordering constraint is discharged and the dangling-reference hazard no longer exists. gh69's INV-ANA-40..44 slots are **free** (no active claimant). Residual narrowed to: (a) Phase-6 re-check that 40-44 remain free and 33/35 remain present, and (b) reconcile the **gh70 INV-ANA-45 sync anomaly** (synced inventory jumps 39→46,47,48; 45 absent, 46-48 from gh70/gh72) so gh69's sync ends contiguous. Summary count unchanged (Level Low → Low). |
| 2026-07-09 | RISK-010 | Added from multi-agent artifact validation (ground-truth pass over the 27 `.mop` files): 3 `staticinitialization`-only specs + 3 constructor pointcuts yield no static targets — accepted + documented in proposal/design/INV-ANA-40; tasks 1.3(d)/1.4 make the boundary observable. Summary 9→10 risks (Medium 5→6). |
| 2026-07-09 | RISK-005 | Gate unified: indicator and trigger both ≤/> **2×** the JCA baseline (the looser "order of magnitude" phrasing superseded). |
| 2026-07-09 | — | Validation corrections applied across artifacts: spec "Flags propagate" scenario no longer lists `MopSpecsTargetSource` among default-false call sites (contradicted INV-ANA-41); `java.lang` seeding re-justified as defense-in-depth (all current `java.lang`-owner specs carry explicit `import java.lang.*;` — the earlier "no explicit import" claim was refuted against the files); generic target-count acceptance strengthened from "N>0" to pin-exact-N (reference enumeration: 67 distinct call() pairs); task 2.1 drops the optional 5-arg overload (P3); D2 gains the FastHierarchy ordering requirement; task 5.2 smoke corpus switched to `rvsec-dataset`. Soot 4.7.1 claim re-verified CORRECT (pom.properties inside shipped `rvsec-gator.jar`). |
| 2026-08-21 | RISK-011 / RISK-012 / RISK-002 / RISK-003 / RISK-010 | Rigorous re-verification against the tree, prompted by the sibling session's handoff (`docs/20260821_handoff_gh69_coringas.md`) — every claim reproduced independently. (a) **RISK-011 added and retired by decision**: the `java.lang` seed in task 1.2 would have moved the frozen `jca` (120→122) / `jca_android` (119→121) sets via `RandomStringPassword.mop`'s unimported `String` owner, and under LENIENT the resulting `String#valueOf` target matches every overload (74 call sites over 3 corpus APKs, 17 legitimate). The seed is now forbidden by D5 / INV-ANA-40; `generic_new` does not need it (all **seven** `java.lang`-owner specs carry `import java.lang.*;` — the count was corrected from six on 2026-08-21, see the audit entry below). This **reverses** the 2026-07-09 entry above that had re-justified the seed. (b) **RISK-012 added**: the extractor module has no test infrastructure — new task 1.0. (c) **RISK-002 gate corrected**: `MopSpecsParityTest` is source-layer only (both sides call the same visitor) and cannot catch an extractor-side JCA regression; the literal 120/68/22 count is the gate. (d) **RISK-003**: `main.basedir` does not resolve in a standalone module build (literal `${main.basedir}` directory found in the tree) — tasks 4.1/4.2 now build from the reactor root with JDK 21. (e) **RISK-010**: gained scope boundary (c) (the `RandomStringPassword` false-negative) and the 21-vs-**20** owner correction for the task 4.3 gate (`TreeMap` appears only in the skipped constructor pointcut). Also corrected: 17 `new TargetMethod(` call sites (not ~14). Summary 10→12 risks. (An arithmetic slip in this row originally read "Medium 6→7, Low 3→4", which sums to 14, not 12, and contradicted the summary table; the rubric pass later in the same day settled the distribution at High 3 / Medium 6 / Low 3.) |
| 2026-08-21 | all | **Consistency audit** (6 parallel verification agents against code + corpus + docs). Corrections: (a) `CharSequence_NotInSet.mop` declared owner `Set+` with no `java.util` import — the only unresolvable `generic_new` owner; repaired in **task 1.0b**, without which the 1.4 skip-count gate, the 4.3 20-owner gate and the 24/27 coverage figure were all false (RISK-006 promoted from hypothetical to observed). (b) **D2's ordering requirement dropped** — GATOR never calls `getOrMakeFastHierarchy`/`forceResolve` (SPARK materialises the hierarchy in the `cg` pack before any client analysis), so the requirement was unsatisfiable; and its premise was false, since `Scene.addClass` invalidates the cache via `modifyHierarchy()`. Replaced by resolve-then-obtain + never-cache + `releaseFastHierarchy()` for phantoms; INV-ANA-43 and task 4.3 updated. (c) **Task ordering fixed**: phase 2 compiles the gator against the new `MopMethod`, so the extractor install moved to **task 1.7**, ahead of it (the old list put it at 4.1, violating D6). (d) All Maven commands normalised to reactor-root + absolute paths (2.5's `cd ../rvsec/...` was a broken path; 2.5/3.3/5.1 were module-local, which breaks `main.basedir`); 4.2's `${main.basedir}` gate replaced by an mtime check, since three such directories already exist under `rvsec-gator/`. (e) **ITs never ran**: `<skipITs>true</skipITs>`, so `-DskipITs=false` added throughout and **task 5.1b** now runs `BaselineComparisonIT`, the JCA gate the spec named but no task executed. (f) Four orphan gates given tasks: RISK-005 timing (**4.8**), RISK-009 scan-only (**4.7**), RISK-007 parser smoke (**4.4**), RISK-002 end-to-end (**5.1b**). (g) INV-ANA-42's scenario contradicted its own body by forbidding the hybrid scan — rewritten. (h) **RISK-007 was wrong on both halves**: three independent Python readers of the raw JSON (incl. `aperv-tool`), and `MopData.java` reads the *derived* `*.mop.json`, not the GATOR output. (i) RISK-004 saturation shown to reach shipped code (`aperv-tool`'s hot/cold verdict and its count-model offset), not only a future dataset filter. (j) D3 gains the `generic_new` `[helper] :::` hole — runtime per-spec attribution is partial for exactly this spec set. (k) Rubric published and applied: RISK-009 Medium→High, RISK-011 Medium→High (Level now means inherent risk, Status carries disposition), RISK-012 Low→Medium. (l) `java.lang`-owner spec list corrected from six to seven. (m) Generic cardinality gate de-circularised: N fixed in advance (67 with a `+`-aware owner key, 66 without) instead of pinning whatever the implementation emits. (n) Citation fixes: `result_processor.py:402-435`→`:487-491`+`coverage.py:438-440,886-888`; `FlowgraphRebuilder.java:980`→`:1065`; `MultiSpec_1MonitorAspect.aj` given its full path; `20260611_sweep_generic_new_400.md` §11 does not exist (procedure is §5); `rvsec-dataset/apks_original/` is empty and the 219 figure is stale (182→181, Phase 10/11). Numbers re-verified and left unchanged: 27/89/71, 3+3 boundary cases, 8 wildcard patterns, jca 120/68/22, jca_android 119/67/22, 74/17/57, 17 `new TargetMethod(`. |
| 2026-08-21 | RISK-007 / RISK-011 / RISK-012 / RISK-008 | **Second consistency audit** (5 parallel verification agents + empirical runs; the numeric backbone was re-derived and found exact, so no count changed). Corrections: (a) **RISK-012 broadened and is now the load-bearing build risk** — besides the extractor having no test infrastructure, the gator parent `rvsec-gator/pom.xml:18` sets `<skipTests>true</skipTests>`, which failsafe also honours, so `-DskipITs=false` alone never enabled the ITs and every gator test command in this change was a **false green**. Measured under JDK 21 from the reactor root: `-DskipTests=false` → `Tests run: 178, Failures: 0, Errors: 0, Skipped: 0`; without it, `Tests are skipped.` + BUILD SUCCESS. The line dates from the 2024-09-25 vendoring commit `d94e33cc`, predates every RV-Android test in the module, and no automated path (CI, `build.sh`, docker entrypoint, any README) runs those tests today. New task **1.0c** applies the override everywhere and deletes the line. (b) **RISK-007 consumer map widened**: six raw-JSON readers outside `modules/` were unlisted, including two **value**-stability gates — `tests/parity/test_reachability_parity.py:156` (`G_paridade_targets`) freezes the set of `reachesTarget=true` signatures against a baseline, and `test_historical_methods_coverage.py:134` pins three methods — which guard exactly what INV-ANA-44 does not (values, not keys). (c) **RISK-011 Level corrected in its body** from Medium to **High**, and **RISK-012 from Low to Medium**, matching the summary table and the rubric published earlier the same day; the bodies had never been updated. (d) RISK-011's "six" `java.lang`-owner specs → **seven** (last surviving instance), and its two samples (3 APKs for 74/17/57; 12 APKs for prevalence) disambiguated. (e) **RISK-008 de-contradicted**: it carried both "INV-ANA-39 is synced" and "39 has no bullet", plus an un-deleted "Original note" stating the jump as 39→46. Measured: the normative bullets run `… 37, 38, 46, 47, 48 …`; 39 is narrative-only, 45 and 55 absent. The two false statements are deleted. (f) Change-log arithmetic fixed ("Medium 6→7, Low 3→4" summed to 14, not 12) and this table re-sorted chronologically (the 2026-07-06 row sat after 2026-07-09). Delta-spec and task changes recorded in those artifacts: `## MODIFIED Requirements` added for `Target Method Source Abstraction`; `MopData.java` removed as the schema-safety consumer; scope boundary (d) added for the discarded `args()`/`target()`/`condition()` narrowing; the constructor skip reframed as a required guard; INV-ANA-42 gained an NFR04 cost bound that now includes `ReachabilityEngine.multiSourceBfs`. |
| 2026-08-21 | RISK-004 | **Re-scoped after measurement** (6 parallel measurement agents; 8 corpus APKs, 205,519 methods, 827,443 call sites; pipeline calibrated against the shipped `jca` `*.apk.json`, exact on 7 of 8). The risk had never carried a single measured number — the wording was "a huge fraction", "almost everywhere" — while the false-*negative* it does **not** introduce (`RandomStringPassword`) had been measured to 74/17/57. Three corrections: (a) **the named owners were wrong** — `Object+` is 0.02% of call sites and `Object+.notifyAll` marks zero methods in the whole sample; `Comparable+.compareTo` is 0.31%; `Iterable+` is wide only through `iterator`. The real vectors are `Collection+.add*` (2.50%), `CharSequence+.equals` (2.10%), the `Iterator` family (1.88%), `Iterable+.iterator` (1.84%), `Collection+.iterator` (1.68%), `Closeable+.close` (1.12%), and the first two are wide structurally, because the extractor drops the `!target(String)` residue (compounds with scope boundary (d)). (b) **The saturation is now quantified**: `directlyReachesTarget` 0.0–0.3% → **2–12%**; `reachesTarget` 11–47% → **84–94%**, whose lower bound exceeds the anchor's own `reachable` fraction on 4 of 8 APKs — it collapses onto "is reachable". (c) **The accepted mitigation is empirically refuted**: dropping 34 of the 67 pairs does not move `reachesTarget` on any medium or large APK (quicknote 1752→1752, geometerplus 1358→1358, rcx 2514→2513, flym 2247→2245, mupen 2342→2340) — owner filtering cannot repair the transitive signal. Consequences recorded: the signal this change delivers for `generic_new` is **`directlyReachesTarget`**, with `reachesTarget` declared degenerate for that spec set (the two spec sets are complementary on the two axes); and `aperv-tool` — production code — changes verdict in the same commit (`static_artifact.py:13-17`, `:288-296`), which the 2026-08-21 audit had logged as item (i) but never written into the risk body. Effect Tolerable→**Serious**, Level Medium→**High** per the published rubric; summary distribution High 3→4, Medium 6→5 (total still 12). Evidence: `docs/20260821_gh69_veredito_coringas.md` §4.3–§4.5. |
| 2026-08-21 | — (scope addition) | **`reaches ⊇ direct` repaired inside this change** (INV-ANA-64, design D8, tasks 3.2b/3.2c). Measured over the 269 `*.apk.json` in the tree: 14 flags on 6 distinct methods in 2 APKs carry `directlyReachesTarget=true` with `reachesTarget=false`, violating a **definitional** containment. Cause: one relation, two oracles — the direct axis is `findDirectTargetCallers(cg) ∪ findDirectTargetCallersByBytecodeScan(...)`, carrying the BUG-INV-ANA-19 repair for SPARK-quarantined app→library edges, while the transitive axis is `multiSourceBfs(reversed(cg), targets)`, which never received it; `complementWithCallbacks` patches callbacks only, and only through CG edges. 12 of the 14 sit on methods with `reachable=false` (no CG vertex at all); the other 2 are in the graph with the single edge missing. Repair adopted: seed the reverse BFS with `targets ∪ directTargetSet` — containment by construction **and** correct upward propagation, ~4 lines, no signature change (`multiSourceBfs` already `addVertex`es its seeds, with a comment for this case). Post-hoc union rejected (asserts the invariant without propagating it); graph-edge injection rejected on cost for an identical `reaches` set. **No enforcement gate**: `JsonReportWriter` is untouched by operator decision — the residual is an unmarked ancestor, a transitive false negative rather than a containment violation, and the analysis must continue normally. **No frozen gate moves**: the `G_paridade_targets` fixture `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` has zero violations today (21 direct, 32 transitive) and `BaselineComparisonIT` tolerates ±10% on `reachesTarget`. The defect predates gh69; it is absorbed here because RISK-004's measured growth of the direct set (0.0–0.3% → 2–12%) scales the scan-only share with it. Invariant numbered **64**, not 45: gh70 (archived 2026-06-18) used 45 for a different property whose result was negative and never synced, so reusing it would falsify that archive. Task count 36→38. Evidence: `docs/20260821_gh69_veredito_coringas.md` and the JSON sweep in this session. |
| 2026-08-21 | RISK-005 / RISK-004 / — | **Verdict follow-through** (measurement session, `docs/20260821_gh69_veredito_coringas.md`). Artifact corrections: (a) **RISK-005 bound corrected** — of the 67 pairs only **54** carry a `+` and reach the `canStoreType` path; and the "O(1) amortized" justification is **false for interface parents**, which is 10 of the 16 distinct `+` owners: the interval encoding covers classes only, so an interface falls to a linear implementers scan or, above 100, to `canStoreClassClassic` (measured against `android.jar` android-30: `Comparable` 245, `Closeable` 154 → BFS branch; `Iterable` 67, `Collection` 38 → scan). The count bound stands; the per-query cost claim did not. (b) **Task 4.3's IT gate re-pointed**: `reachesTarget>0` passes trivially under `generic_new` (84–94% saturation) and proves nothing — the assertion that carries weight is `directlyReachesTarget` inside the measured 2–12% band. Same correction in the design testing table. (c) **Scope boundary (d) rewritten**: measured by *event* it is 55 of 58 (95%), not 40 of 88 lines; the `args()` axis recovers **zero** precision (2 of 22 events narrow a type, neither changes the resolved `SootMethod` set, and `Collection+.add*` already covers `Set.add` unrestricted in the union) — the boundary's own example was the emptiest case available; the recoverable precision is `target()`-of-type, worth 11–41% of the direct seed on two pairs. (d) **`forceResolve` level changed HIERARCHY → SIGNATURES** (task 2.x): resolving at `HIERARCHY` can leave a class below `SIGNATURES`, and `TargetResolver.resolveInScene` calls `cls.getMethods()` unguarded over `Scene.v().getClasses()` (`TargetResolver.java:48-50`) — `getMethods()` opens with `checkLevel(SIGNATURES)`, `doneResolving()` is true in `wjtp`, and `ignore_resolving_levels` is never set, so the next pass throws `RuntimeException`. A **crash created by this change's own mitigation**, realistic trigger `java.net.ServerSocket` in a socket-free APK. (e) **Task 1.4 gate made locale-safe**: `sort -u` under pt_BR folds `Map+.put` into `Map+.put*` and returns 66, failing the 67 gate for the wrong reason. (f) **Proposal's 120-vs-67 comparison qualified**: different units (signatures-with-constructors vs pairs-without); level under one convention (68 vs 69 pairs), and 18 of the `jca` 120 are `new`-named targets that match no Soot method, leaving ~102 live signatures / 57 live pairs — the repaired generic set yields *more* live targets than the frozen ruler, not fewer. (g) New task **5.2b** forces an explicit decision on `aperv-tool` before shipping. Tasks 38→40. |
| 2026-08-21 | RISK-011 / — | **Two cross-change couplings registered** (neither change had recorded the other). (a) **gh105 is editing `jca_android` while gh69 treated it as frozen.** The two changes use "frozen" with different scopes: gh101 (archived 2026-08-16) froze `jca` alone — "not one byte of `rvsec-mop/src/main/resources/jca` ... Every correction to a specification lands in `jca_android` alone" — and made `jca_android` the successor carrying the repairs; gh105 is executing precisely that. Measured: `call(` occurrences in `jca_android` went **144 → 130** between commit `42a3528` and the working tree (gh105's F1 twin fusions), and gh105 has **39 of 74 tasks open**, including the group that adds new `<Chain>Junction.mop` files to that directory. gh69's triple 119/67/22 is accurate today but would go red on a change doing the right thing, so **task 1.5 now derives the `jca_android` count by enumeration and asserts only `jca` literally** — the discipline gh105 already imposes on its own gates. Exposure is limited: the production static-analysis path never reads `jca_android` (`config.py:199-208` always falls back to `jca`), so only gh69's unit test was at risk, not `G_paridade_targets`. No `.mop` file is written by both changes — gh69 edited one file, in `generic_new`. (b) **gh104 task 10.0 is the vehicle for the spec-set → `mopDir` wiring** that gh69's Impact described only as a plan document (`docs/20260821_plano_correcao_analise_estatica.md` D2, untracked). The proposal now names it. The coupling is one-directional and narrow: gh69 needs nothing from it to be implemented, verified or archived — its gates run through `--mop-dir` directly — but gh69's *product* stays unreachable from `rv-experiment`/`rv-platform` until 10.0 lands, and 10.0 is open. |
