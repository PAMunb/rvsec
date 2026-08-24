# Risk Register: gh106-mop-crysl-conformance

> GitHub Issue: #106 — Full SDD. Companion to `proposal.md` / `design.md` / `tasks.md`.
> Authoritative sources: `design.md` §Decisions / §Error Handling / §Risks-Trade-offs / §Open Questions,
> the sixteen group files under `tasks/`, and the Phase 0 material the proposal header lists. Every
> risk below was **re-verified against the tree at HEAD `5fbe8173`** on 2026-08-24 — the same commit
> the eight calibration targets are pinned at — rather than copied out of the design's own
> risk section. This register applies the **proactive strategy**: each risk is documented *before*
> implementation, with an RMMM plan, so the failure is anticipated rather than fire-fought.

## Scope under analysis

Build a **new Java component in the sibling `rvsec` Maven reactor** (`rvsec-crysl` parent plus
`-core`, `-mop`, `-crysl`) that mechanically compares the hand-translated `jca_android` JavaMOP set
against the CrySL rules it came from, on five metrics, against the single upstream oracle
(`rvsec-cognicrypt/CrySL-Rules`), and publishes stamped,
countable, refusable results. The change is **a measuring instrument**: it edits no `.mop`, alters no
pipeline step, and changes nothing about what the monitors accuse.

That shape is what drives the risk profile, and it is unusual for this repository on four axes:

1. **The product is a number, not a behaviour.** The usual failure mode here is a regression a test
   catches; the failure mode of an instrument is a *plausible wrong number nobody can tell from a
   right one*. Most of the High-level risks below are integrity risks, not breakage risks.
2. **Java in the reactor, where CI does not run tests.** The instrument's whole contract is 17
   invariants plus a calibration gate, all expressed as Java tests, in a build whose CI step passes
   `-DskipTests` (`.github/workflows/ci.yml:30`).
3. **The corpus spans two git repositories and one SDK directory**, only one of which is checked
   out by CI.
4. **The evidence base that justifies the eight calibration targets is not in git.**

Per the **Risk Projection** principle the analysis concentrates there, and deliberately does *not*
re-litigate the engineering decisions Phase 0 and the risk pass already paid for (D-01 … D-19).
Those are recorded in `design.md`; re-opening them is itself a risk, and it is filed as RISK-005's
mirror image in the Monitoring Schedule.

## Summary

| Risk Level | Total | Open | Accepted | Controlled by design | Mitigated / Resolved |
|------------|-------|------|----------|----------------------|----------------------|
| Critical | 0 | 0 | 0 | 0 | 0 |
| High | 5 | 3 (001, 003, 004) | 0 | 1 (005) | 1 (006 — mitigated by D-18) |
| Medium | 8 | 7 (002, 008, 009, 010, 011, 012, 014) | 0 | 0 | 1 (007 — resolved by the oracle switch) |
| Low | 3 | 2 (013, 015) | 1 (016) | 0 | 0 |
| **Total** | **16** | **12** | **1** | **1** | **2** |

**Rubric.** Level = f(Probability, Effect), on *inherent* risk, before mitigation. Same rubric as
`gh69-generic-subtype-target-matching/risk-register.md`, reused deliberately so levels are comparable
across changes:

| | Insignificant | Tolerable | Serious | Catastrophic |
|---|---|---|---|---|
| **High / Very High** | Low | Medium | High | Critical |
| **Moderate** | Low | Medium | High | Critical |
| **Low / Very Low** | Low | Low | Medium | High |

The Level column always means inherent risk; the Status column carries the disposition.

| ID | Title | Category | Prob. | Effect | Level |
|----|-------|----------|-------|--------|-------|
| RISK-001 | The four new modules' tests never run in CI — `-DskipTests` at the reactor build step | Tools (build / false green) | High (certain today) | Serious | **High** |
| RISK-002 | The oracle corpus and the API index live outside the repository, so the oracle-dependent tests cannot run in CI at all | Tools (environment) | High (certain) | Tolerable | **Medium** |
| RISK-003 | `Version.commit` is one field and the corpus spans **two** git repositories | Product (measurement integrity) | Moderate | Serious | **High** |
| RISK-004 | The evidence base of the change — harness, three Phase 0 docs, the change tree itself — is **untracked** | Project (process / provenance) | High (certain today) | Serious | **High** |
| RISK-005 | A calibration mismatch resolved by tuning the instrument until it agrees | Product (measurement integrity) | Moderate | Serious | **High** |
| RISK-006 | Three of the eight calibration targets are **not** independent routes | Product (measurement integrity) | High (structural, as written) | Serious | **High** |
| RISK-007 | The upstream pairing rule is undeclared, and INV-CONF-11 demands both oracles on every metric | Requirements (open question) | Moderate | Tolerable | **Medium** |
| RISK-008 | INV-CONF-03's machine-checkable form has no type to key on — `Event.label` is a `String` | Product (verification) | High | Tolerable | **Medium** |
| RISK-009 | `-core` "zero external dependencies" contradicts the validated V10 pom (Gson) and the emitters' job | Technology (layering) | High | Tolerable | **Medium** |
| RISK-010 | JUnit 5 / ArchUnit are unmanaged in the reactor, which manages JUnit 4 and `surefire-junit4` | Tools (build) | Moderate | Tolerable | **Medium** |
| RISK-011 | The corpus moves under the component during implementation (gh104 and gh105 still open on the same files) | Requirements (moving target) | High | Tolerable | **Medium** |
| RISK-012 | The "five surviving CI gates" are not run by CI, and CI deletes the `backup/` tree the retirement test asserts | Process (gate hygiene) | High (certain) | Tolerable | **Medium** |
| RISK-013 | G13a's census rule is ambiguous and the retirement is partial — a reader outside `audit/20260808_*` has no disposition | Process (P3 completeness) | Moderate | Insignificant | **Low** |
| RISK-014 | Size: 209 checkboxes, ~45 Java files, ~150 tests, one researcher, two predecessors still open | Estimation | High | Tolerable | **Medium** |
| RISK-015 | JDK 21 is not the host default — only JDK 25 is installed system-wide | Tools (build environment) | Moderate | Insignificant | **Low** |
| RISK-016 | Two copies of the upstream oracle exist in the workspace, byte-identical today | Technology (corpus identity) | Low | Tolerable | **Low** |

---

## Top Risks

### RISK-001: The four new modules' tests never run in CI — the reactor build step passes `-DskipTests`

- **Category**: Tools (build / false green)
- **Description** (measured 2026-08-24 against `.github/workflows/ci.yml`, 115 lines): the `maven-build`
  job runs `mvn clean install -DskipTests -DskipMopAgent -pl '!rvsec/rvsec-android/rvsmart'` (`:30`).
  The **only** module whose tests execute in CI is `rvsec-instrumentation-dexlib2/grammar-tests`, and
  only because a second step re-enables them explicitly: `mvn -ntp -B -pl grammar-tests -am
  -DskipTests=false test` (`:44`). Nothing else in the reactor is tested by CI. gh106's contract is
  almost entirely tests: 17 invariant tests (one per `INV-CONF-01…17`), the 40-shuffle order-invariance
  test, the ArchUnit shape rules, ~80 unit and ~40 integration tests, and the eight-target calibration
  gate. Under the current workflow every one of them is a green that exists only on the researcher's
  machine, and only for as long as that session lasts.
- **Why this is a top risk (Risk Projection)**: this repository has shipped this exact false green
  **twice** — `rvsec/rvsec-android/rvsec-gator/pom.xml:18` (`<skipTests>true</skipTests>`, measured to
  hide 178 passing tests) and `client/pom.xml:18` (`<skipITs>true</skipITs>`, which made every gh69 IT
  command a no-op). Both were found by audit, not by CI. The probability of a third instance is not
  hypothetical: the default path already skips, so the failure needs no mistake to occur — it needs a
  deliberate act to *not* occur. Effect is Serious because the artifact whose verification disappears is
  the instrument's own correctness contract, and the whole change exists to stop unverifiable numbers
  from being published.
- **Probability**: High (certain unless a step is added) · **Effect**: Serious · **Level**: High
- **Mitigation strategy**: Avoidance (add the step) + Minimization (make a skipped run loud)
  - **Avoidance**: add a CI step modelled line for line on the gh62 precedent —
    `mvn -ntp -B -pl rvsec/rvsec-crysl -am -DskipTests=false test` — restricted to the
    corpus-independent subset defined by RISK-002. This is a **new task for G05**, alongside 5.6/5.7;
    the group currently asserts the *effective pom* but never asserts that CI runs the suite.
  - **Minimization**: G00 task 0.21, G05 5.9 and G14 14.2 currently say "green". Restate them as
    *"reports a non-zero `Tests run:` count"* — a run printing `Tests are skipped.` alongside
    `BUILD SUCCESS` MUST be treated as a failed gate, never as a pass. This is the wording that caught
    the gator case.
- **Indicators (Monitoring)**:
  - CI log shows four `Tests run: N` lines with `N > 0`, one per new module. Any `Tests are skipped.`
    for `rvsec-crysl*` is **Red**.
  - Count of invariant tests executed in CI == the number of INV-CONF invariants runnable without the
    external oracles (see RISK-002 for the split; expected ≥ 10 of 17).
- **Contingency (Management)**:
  - **Trigger**: G05 closes without a CI step, or a CI run reports zero tests for the new modules.
  - **Actions**: (1) add the step before G12 runs, not after — a calibration gate that has never run in
    CI is exactly the artifact this risk is about; (2) if the corpus split makes a CI run impossible
    for a given test, mark it *local-gate* explicitly in the test's Javadoc and list it in G14, so the
    residue is declared rather than discovered.
  - **Owner**: implementer (G05), re-checked by the change author at G14.
- **Status**: Open

---

### RISK-002: The oracle corpus and the API index live outside the repository, so the oracle-dependent tests cannot run in CI at all

- **Category**: Tools (environment / test reachability)
- **Description** (measured 2026-08-24): the git repository rooted at `rvsec` contains the 215 `.mop`
  files (`rvsec/rvsec-mop/src/main/resources/{jca:23, jca_android:24, jca_android_bug_predicate:23,
  generic:118, generic_new:27}`) and the committed CSVs under `rv-android/data/jca_android/`. It does
  **not** contain the oracle or the API index:
  - `rvsec-cognicrypt` is a **separate repository** at `f2f4d3b` — 49 upstream rules, tracked and clean;
  - `android.jar` comes from `$ANDROID_HOME/platforms/android-30` (present on this host;
    `ANDROID_HOME=/home/pedro/desenvolvimento/aplicativos/android/sdk`).

  The CI checkout (`actions/checkout@v6`, `ci.yml:17`) takes one repository. Consequently
  `CryslLiftOracleTest` (G02 2.6), `test_inv_conf_04_order_invariance` (2.7), `ApiIndexTest` (2.8),
  the M1/M3/M4 oracle tests and calibration targets 4–6 are **unrunnable in CI** even once RISK-001
  is fixed. The oracle switch (D-06) reduced the exposure — one external repository instead of two —
  but does not resolve it: `rvsec-cognicrypt` is **not** in the CI checkout (verified against
  `.github/workflows/ci.yml`). The half that *is* CI-reachable is substantial and worth protecting: all
  of `-core` (automata, model shape, `Unknown`, witness, emitters), the whole MOP lift including the
  215-file corpus test, M0, and the round-trip gate.
- **Probability**: High (certain — it is a property of the checkout) · **Effect**: Tolerable (the tests
  still run locally, where both trees are present; the harm is unattended coverage, and the
  false-green half is already carried by RISK-001) · **Level**: Medium
- **Mitigation strategy**: Minimization (classify at write time) + Avoidance for the CI-reachable half
  - **Classify every test as it is written** into *corpus-independent* (runs in CI) or
    *oracle-dependent* (local gate). The classification belongs in the test, not in a document:
    JUnit 5 `Assumptions.assumeTrue(oraclesPresent())` **plus a printed reason**, so a skipped run says
    which path was missing. A test that silently passes when its corpus is absent is the same defect as
    RISK-001 wearing different clothes.
  - **Do not** vendor the oracle into this repository as a reflex: 49 rule files would create a
    third copy of a corpus that already exists twice (RISK-016), and INV-CONF-12 makes them
    read-only anyway. If the researcher wants CI coverage of the lift, the cheaper option is a **pinned
    snapshot under test resources** of a handful of named rules (the ones the tests actually assert on),
    labelled with the source repository and revision.
- **Indicators**: number of tests reported as *skipped for missing corpus* in a local full run == 0;
  the same number in CI is expected and must be **printed with its reason**, never silent.
- **Contingency**:
  - **Trigger**: a test asserting an oracle number passes in CI. That means it is not reading the
    oracle, and the number it asserts is coming from somewhere else.
  - **Actions**: inspect the fixture; if a snapshot was introduced, stamp it with the source revision
    (RISK-003) and record it in the calibration targets.
  - **Owner**: implementer (G02, G12).
- **Status**: Open

---

### RISK-003: `Version.commit` is a single field and the corpus spans two independent repositories

- **Category**: Product (measurement integrity)
- **Description**: `design.md` §API Design declares `record Version(String commit, Instant data, String
  corpus)`, and INV-CONF-01/02 make it the anchor of every emitted table. Measured, the corpora
  come from two repositories with independent revisions: `rvsec` @ `5fbe8173` (the `.mop`
  corpora, the committed CSVs, and all of `rv-android`) and `rvsec-cognicrypt` @ `f2f4d3b` (the
  oracle) — plus `android.jar`, which carries no revision
  at all beyond its API level. A table stamped `5fbe8173` beside an upstream-derived number therefore
  states a commit that has nothing to do with the artifact that produced the number.
- **Why this matters more than it looks**: this is INV-CONF-02's own defect, reproduced one level up.
  The capability exists because "a published scalar with no counting rule and no commit stamp beside it
  is not checkable" (proposal §Why). A stamp that names the wrong repository is worse than no stamp: it
  is checkable and wrong, and it will be believed.
- **Probability**: Moderate (the type as designed does not prevent it; the researcher's discipline
  does) · **Effect**: Serious (silently mis-attributed measurement, in the change whose product is
  attribution) · **Level**: High
- **Mitigation strategy**: Avoidance (make the type carry what the data needs)
  - Extend the stamp so that **each corpus read contributes its own (path, revision)** — either
    `Version(String commit, Instant data, Map<String,String> corpusRevisions)` or a `CorpusRef` record
    with `SpecModel.version.corpus` holding one. `Version.corpus` is already a `String` per corpus in
    the design (G02 2.11 stamps corpus identity per oracle), so the missing half is only the revision.
  - The emitter (`StampedTable`, G04 4.1) **refuses to render** a table whose contributing corpora are
    not all revision-stamped — the same refusal it already performs for the counting rule.
  - Where a corpus has no revision (`android.jar`), stamp what it does have: the API level and the file
    hash. A hash is one line and removes the exception.
  - **New task in G00** (the types) rather than in G04, because a type that changes on day two costs six
    merges — the group file says so itself.
- **Indicators**: no emitted table names an upstream-derived aggregate with fewer than two revisions
  (`rvsec` and `rvsec-cognicrypt`) in its stamp; `git -C rvsec-cognicrypt rev-parse HEAD` appears in
  every report header.
- **Contingency**:
  - **Trigger**: a report is produced with a single commit hash and an upstream column.
  - **Actions**: do not hand-edit the report; fix the stamp and re-run. A hand-stamped table is
    indistinguishable from a wrongly-stamped one six months later.
  - **Owner**: implementer (G00 types, G04 emitters).
- **Status**: Open

---

### RISK-004: The evidence base of this change is not in git

- **Category**: Project (process / provenance)
- **Description** (measured 2026-08-24 with `git ls-files`): the material the proposal names as its
  foundation is largely **untracked in the working tree**:
  - `docs/handoff/20260824_arnes_adjudicacao/` — the "reproducible harness" the proposal cites (six
    Java probes `Census.java`, `Binding.java`, `V3Fresh.java`, `Overlap.java`, `Dump.java`,
    `InitTest.java`; three scripts `absorve.py`, `absorve2.py`, `normalize_api30.py`; four authored
    control traces; 18 raw outputs under `saidas/`) — **0 of ~30 files tracked**, while 75 other files under `docs/handoff/` are tracked;
  - `docs/20260824_adjudicacao_plano_conformidade.md` — **untracked**;
  - `docs/20260824_medicoes_pre_change_conformidade.md` — **untracked** (this is the document that
    closes prerequisites P1 and P2);
  - `docs/20260822_verificacao_consistencia_conformidade.md` — **untracked**;
  - the entire `openspec/changes/gh106-mop-crysl-conformance/` tree — **0 files tracked**;
  - the working tree carries 642 dirty entries at HEAD.

  Three of those probes are the *independent route* of calibration targets 1, 2, 3, 4 and 7 (G12's
  table). `normalize_api30.py` is historical since the oracle switch removed the lexical
  normalization; it stays in the harness as the record of how the abandoned `api30` numbers were
  produced.
- **Why this is a top risk**: the change's central claim is that numbers must be reproducible from a
  stated commit. Its own numbers currently are not: nothing outside this machine's working tree can
  reproduce them, and `ci.yml:20` even runs `rm -rf rv-android/backup/ …` before any job, so parts of
  the tree that P3 designates as the archive are deliberately removed in CI. If the tree is cleaned,
  the eight targets become eight numbers with no route — the exact object the proposal calls
  uncheckable.
- **Probability**: High (it is the state today) · **Effect**: Serious (unreproducible calibration =
  the instrument cannot be trusted, and G12 cannot be honestly closed) · **Level**: High
- **Mitigation strategy**: Avoidance (commit before implementing)
  - Commit the harness directory, the three untracked Phase 0 documents, and the change tree **before
    G00 starts**, in one `refs #106` commit. The register, the proposal, the design and the group files
    are the artifacts a later session resumes from; the resume protocol assumes they are in git.
  - Check the interaction with `ci.yml:20` before writing `tests/parity/test_gh106_retirement.py`
    (see RISK-012): a test asserting *presence under `backup/`* is CI-hostile by construction.
- **Indicators**: `git status --short` inside `openspec/changes/gh106-*` is empty at the end of each
  session; `git ls-files docs/handoff/20260824_arnes_adjudicacao | wc -l` > 0 before G00 closes.
- **Contingency**:
  - **Trigger**: a session opens and a cited artifact is missing.
  - **Actions**: reconstruct from the tracked half (`docs/20260821_conformidade_mop_crysl.md`,
    `docs/20260822_adjudicacao_revisoes_externas.md`, `docs/20260821_auditoria_conformidade_mop_crysl.md`
    are tracked) and re-run the probes; record in G12 12.10 that the target's original route was lost,
    rather than silently re-deriving it with the component (which would be RISK-005).
  - **Owner**: change author.
- **Status**: Open

---

### RISK-005: A calibration mismatch resolved by tuning the instrument until it agrees

- **Category**: Product (measurement integrity)
- **Description**: G12 is the gate that decides whether the component's output counts as measurement.
  The cheapest way to pass such a gate is to break the instrument: relax a counting rule, widen a
  recogniser, "fix" a lift so a total lands on the expected value. The result compiles, the gate goes
  green, and the component ships producing numbers that agree with the past by construction rather than
  by measurement — which is strictly worse than having no gate, because the green is now evidence.
- **Probability**: Moderate (the pressure is real and arrives exactly when the change is nearly done —
  G12 sits second-to-last on the critical path) · **Effect**: Serious · **Level**: High
- **Mitigation strategy**: Controlled by design; the residual is procedural
  - INV-CONF-14 makes a mismatch a `CalibrationMismatch` carrying **both** measurements, **both**
    counting rules and the differing items named individually (G12 12.3); the gate reports and does not
    reconcile (12.2); a mismatch stops publication of the affected metric only (12.4).
  - **The residual this register adds**: G12 12.9 ("record the adjudication in `docs/`") is a task like
    any other, and a task can be checked off with a sentence. Make it a **closing condition** of the
    group: G12 does not close while any of the eight targets is in state *mismatch, unadjudicated*.
    The group file already says "a closed G12 with an unadjudicated mismatch is the one failure this
    whole change is designed to prevent" — this register asks that the sentence be enforced by the
    checklist rather than by memory.
  - A second, quieter form of the same risk: **re-opening a Phase 0 decision because it is inconvenient
    during implementation**. D-02 is explicitly marked *forbidden to reverse*, and
    `docs/20260822_adjudicacao_revisoes_externas.md` §1 lists claims that converged across independent
    reviewers and were still wrong. Reversing one under implementation pressure produces the same
    outcome as tuning the gate.
- **Indicators**:
  - Number of targets in state *mismatch, unadjudicated* at any G12 review — must be 0 at close.
  - Any commit in the G12 window that changes a counting rule, a recogniser threshold or a lift
    behaviour **and** moves a calibration number: a Yellow trigger by construction, requiring the
    adjudication document before it merges.
  - Any edit to a decision in `design.md` §Decisions during implementation: Red until adjudicated in
    writing.
- **Contingency**:
  - **Trigger**: a target does not reproduce.
  - **Actions**: measure both sides; if the target proves unreproducible under **any** written rule — as
    happened in Phase 0 with `129`, `12 of 23`, `10/26` and `28 of 55` — record it as unreproducible and
    publish the component's value **with its rule** (G12 12.10). Do not chase a rule that was never
    written down, and do not adjust the component to hit a number whose provenance is unknown.
  - **Owner**: change author (adjudication is not delegable).
- **Status**: Open — controlled by design (INV-CONF-14, D-13); residual is the closing condition above

---

### RISK-006: Three of the eight calibration targets are not independent routes

- **Category**: Product (measurement integrity)
- **Description**: G12's premise is that the component must "reproduce numbers already measured by
  **another route**". Read against the group's own table, five of the eight targets satisfy that
  (targets 1, 2, 3, 4 and 7 come from the Java probes `Census.java`, `V3Fresh.java`, `Binding.java`).
  Three do not:
  - **Target 5** — "M3 clauses implemented, `25 of 55 = 45,5 %`", route: `constraint_table.csv`. That
    file (60 lines, `rv-android/data/jca_android/`) is one of the **hand-maintained tables this change
    exists to replace**, and the proposal's own indictment of the substrate applies to it: judgement
    columns no analyzer can re-derive, carried forward by copying. Calibrating M3 against it measures
    agreement with a prior human reading, not correctness.
  - **Target 6** — "`.mop` ↔ rule name pairing, `22 of 24`", route: "by name; consistent with the two
    declared skips". That is not a second route; it is the same rule the component applies, restated.
    It will reproduce by construction and prove nothing.
  - **Target 8** — "specifications without `MapOfMonitor`, `5 of 24`", route: "AST proxy; the generated
    monitor is the real oracle". The AST proxy **is** what G06 6.1 implements. The component will be
    calibrated against its own algorithm, and G06 6.2 already says so in as many words.
- **Why this is High**: a calibration gate whose targets partly restate the instrument gives a green
  that reads exactly like a real one. Two of the three affected targets sit on M0 and M3 — the metric
  that decides which specifications get a verdict at all, and the metric whose `25/55` figure is the
  most quotable number in the change.
- **Probability**: High (structural — it is in the table as written) · **Effect**: Serious ·
  **Level**: High
- **Mitigation strategy**: Minimization (label the weak targets) + Avoidance where a second route is
  cheap
  - **Label each target with its route class** — *independent probe*, *committed hand table*, or
    *same-algorithm restatement* — as a field of `CalibrationTargets` (G12 12.1), and print it in the
    gate's output. A target that cannot fail is not a gate, and saying so costs one enum.
  - **Target 8 has a real second route and it is named in the change**: generate the monitors and count
    the `MapOfMonitor` classes. That is what "the generated monitor is the real oracle" means. If the
    generation run is out of scope for gh106, record target 8 as *proxy-calibrated* and carry it as a
    known limitation into the report, not as one of "eight independently measured targets".
  - **Target 5**: the honest second route is the clause census executed by hand in Phase 0 under rule R1
    (`docs/20260821_conformidade_mop_crysl.md`); cite the section rather than the CSV, or accept the CSV
    and label it *committed hand table*.
  - **Target 6**: demote from the gate to a consistency check (it already is one — G07 7.5).
- **Indicators**: the gate's output prints a route class beside each of the eight; the count of targets
  in class *independent probe* is stated in the report (expected 5, not 8).
- **Contingency**:
  - **Trigger**: the report or the change's closing summary claims "eight independently measured
    targets".
  - **Actions**: correct the claim to the measured composition before publication; a mis-stated
    calibration is the one error this change cannot survive rhetorically.
  - **Owner**: change author (G12).
- **Update (2026-08-24, oracle-switch revision)**: mitigated by **D-18** — the by-name and AST-proxy
  routes were replaced in the artifacts. Target 6 now calibrates against the `disposition` column of
  `order_alphabet_map.csv` (an artifact the component does not produce), target 8 against the
  regenerated monitors, and target 5 was re-based on the upstream M3 denominator (`80` under R1 over
  the 22 paired rules) via the two independent R1 implementations of the adjudication harness. The
  residual is target 5's committed `constraint_table.csv` (`25/55`, `api30`-anchored) standing as a
  **labelled historical reconciliation** — kept legible as history, never counted as calibration. The
  description above is preserved as the history that motivated D-18.
- **Status**: Mitigated by D-18 (routes replaced in the artifacts); residual: target 5's
  historical-reconciliation labelling

---

### RISK-007: The upstream pairing rule is undeclared while INV-CONF-11 demands both oracles on every metric

- **Category**: Requirements (open question, `design.md` Open Question 2)
- **Description**: `api30` pairs 22 of 24 specifications by name, and the two unpaired ones
  (`IvChainJunction`, `RandomStringPassword`) are exactly the two the alphabet map declares as skips —
  a clean, checkable rule. Upstream is different: 47 effective rules against 24 specifications, and the
  pairing rule "needs to be declared before any number derived from it is published". INV-CONF-11 makes
  a report that names one oracle without the other unemittable, and D-06 makes the two-oracle difference
  *the* oracle-ceiling measurement — a headline contribution. If the rule stays unwritten, G07 7.6's
  fallback fires and the upstream column of M1, M2 and M4 is `Unknown` for every specification, leaving
  the oracle ceiling resting on M3 alone (whose `−33` across 16 rules was derived by hand in Phase 0 and
  is asserted, not re-derived, by G08 8.8).
- **Probability**: Moderate (G07 7.6 forces the decision, but forces it *late* — G07 unlocks only after
  G01 and G02) · **Effect**: Tolerable (an `Unknown` is honest output, by this capability's own
  philosophy; the loss is a deliverable, not a wrong number) · **Level**: Medium
- **Mitigation strategy**: Avoidance (decide early, in writing)
  - Declare the pairing rule as part of **G02**, not G07: the lifter already stamps corpus identity
    (2.11), and the rule is a property of the oracle, not of the metric. Candidate rule, to be written
    and defended rather than assumed: pair on the rule's declared `SPEC` type against the
    specification's monitored type, with the residue (upstream rules with no specification) counted as
    the **subject ceiling** of M3 task 8.7 rather than as unpaired noise.
  - Whatever the rule is, it is emitted beside every upstream-derived table (INV-CONF-02 already
    requires this — a pairing rule is a counting rule).
- **Indicators**: count of upstream columns emitted as `Unknown` per metric; if M1's upstream column is
  100 % `Unknown` at G12, the oracle-ceiling deliverable has silently shrunk to M3.
- **Contingency**:
  - **Trigger**: G10 starts with the rule still unwritten.
  - **Actions**: publish the pair of bounds under two declared rules — the same discipline Open
    Question 3 already applies to the overlapping-pointcut count — rather than a single figure under an
    undeclared one.
  - **Owner**: change author (it is a measurement decision, not an implementation one).
- **Update (2026-08-24, oracle-switch revision)**: **resolved and closed**. INV-CONF-11 was rewritten
  — every report names its oracle (repository and commit) and its pairing rule — and the pairing rule
  is written and measured: by declared type (the rule's `SPEC` FQN against the specification's
  declared parameter type; the pointcut's declaring type for the two parameterless specifications),
  `22 of 24` with the same two skips (`design.md` Open Question 2, resolved; G07 7.6 implements and
  tests it, including `SecretKeySpec.mop` → `SecretKey.crysl` × `SecretKeySpecSpec.mop` →
  `SecretKeySpec.crysl`). The `−33` figure referenced above survives only as the method note behind
  D-06 — why `api30` was abandoned — not as an oracle-ceiling deliverable. The body above is
  preserved as history.
- **Status**: Resolved / Closed (2026-08-24) — single oracle plus the declared-type pairing rule,
  written and measured

---

### RISK-008: INV-CONF-03's machine-checkable form has no type to key on

- **Category**: Product (verification)
- **Description**: INV-CONF-03 forbids "a representation of the form `Map<Label, Set<Signature>>`", and
  G00 task 0.20 asks ArchUnit to enforce it: "no field in `-core` has a type assignable to
  `Map<?, Set<?>>` whose key is a label type". But the model as designed has **no label type**:
  `record Event(String label, …)` (`design.md` §API Design, G00 0.10). With `Label = String`, the rule
  either (a) forbids every `Map<String, Set<?>>` in the module — over-broad, and it will be suppressed
  the first time a legitimate string-keyed index appears — or (b) cannot be expressed at all, and
  INV-CONF-03 quietly degrades from a machine-checked invariant to a convention, which is exactly the
  standing the design refuses everywhere else. (ArchUnit 1.2.1 is available offline and *can* read
  generic field types; the obstacle is the missing type, not the tool.)
- **Probability**: High (it follows from the declared record shapes) · **Effect**: Tolerable (the
  invariant's substance — D-02's ordered event list — is carried by the model shape and by
  `InverseMorphism`; what is lost is the enforcement) · **Level**: Medium
- **Mitigation strategy**: Avoidance (introduce the type the rule needs)
  - Add `record Label(String value)` in G00 and use it in `Event` and in the alphabet map. One record,
    and the ArchUnit rule becomes expressible, precise and un-suppressible. It also makes
    `h : Σ_sig* → Label*` type-check in the signature the design already writes.
  - If the researcher prefers to keep `String`, then say so in the spec: rewrite INV-CONF-03's second
    sentence as a review convention and delete task 0.20, rather than shipping an ArchUnit rule that
    passes because it matches nothing.
- **Indicators**: `ModelShapeArchTest` fails when a `Map<Label, Set<Signature>>` field is deliberately
  introduced in a scratch branch — the standard "assert the violation is refused" check the design's
  own testing strategy prescribes for all 17 invariants. A rule that cannot be made to fail is not a
  rule.
- **Contingency**:
  - **Trigger**: task 0.20 is written and cannot be made to fail on a deliberate violation.
  - **Actions**: introduce `Label`, or downgrade the invariant explicitly in the delta spec. Do not
    leave a green test that checks nothing.
  - **Owner**: implementer (G00).
- **Status**: Open

---

### RISK-009: `-core`'s "zero external dependencies" contradicts the validated pom and the emitters' job

- **Category**: Technology (layering)
- **Description**: G00 task 0.2 requires `rvsec-crysl-core` to have "**zero external dependencies**
  beyond JUnit 5 and ArchUnit in test scope", and `design.md` repeats it in the module diagram. The
  V10 poms — the ones Phase 0 validated as building inside the reactor with `main.basedir` resolving —
  say otherwise: `docs/handoff/20260821_arnes_validacoes/v10/rvsec-crysl/rvsec-crysl-core/pom.xml`
  declares `com.google.code.gson:gson:${gson.version}` as a compile dependency, and the parent declares
  `<gson.version>2.13.1</gson.version>`. The work in `-core` also includes reading
  `order_alphabet_map.csv` (207 lines, G10 3.3), reading four committed CSV headers at build time
  (G04 4.3) and emitting JSON, CSV and Markdown (G04). So the choice is real and must be made once:
  either the layering rule bends for serialization libraries, or the emitters are hand-rolled inside the
  module whose output *is* the published measurement — where a quoting or escaping defect is a data
  defect.
- **Probability**: High (the contradiction exists in the artifacts today) · **Effect**: Tolerable
  (either resolution works; the cost of discovering it in G04 is a pom change plus rework, not a wrong
  number) · **Level**: Medium
- **Mitigation strategy**: Avoidance (decide in G00, record the reason)
  - Recommended resolution: restate 0.2's constraint as what the layering actually needs — *`-core` must
    not depend on either parser (`javamop`, `CrySLParser`); if it ever does, the layering is wrong* —
    and allow Gson (already validated, already in the local repository) for serialization. That
    preserves the property the rule protects (the core does not know how a specification is parsed)
    without pretending a JSON writer is free.
  - If zero-deps wins instead, add a test that round-trips pathological content through the hand-rolled
    emitters — embedded quotes, commas, newlines, non-ASCII (the corpus and the reports are partly in
    Portuguese, and `divergence_record.csv` carries free text).
- **Indicators**: `-core`'s resolved compile classpath contains no `javamop` and no `CrySLParser` (this
  is the assertion worth keeping in `DependencyDisciplineTest`, G05 5.7); the number of hand-rolled
  serialization helpers in `-core` is 0 or covered by an escaping test.
- **Contingency**:
  - **Trigger**: G04 starts and the decision has not been made.
  - **Actions**: take the V10 pom as the tie-breaker — it is the configuration that was actually
    measured to build — and amend G00 0.2 in the same commit, so the group files and the tree agree.
  - **Owner**: implementer (G00), recorded by the change author.
- **Status**: Open

---

### RISK-010: JUnit 5 and ArchUnit are unmanaged in the reactor, which manages JUnit 4 and `surefire-junit4`

- **Category**: Tools (build)
- **Description**: the reactor root pins `<junit.version>4.13.2</junit.version>` and manages both
  `junit:junit` and `org.apache.maven.surefire:surefire-junit4` in `dependencyManagement`
  (`rvsec/pom.xml:211-221`); it manages **no** JUnit 5 BOM and no ArchUnit. gh106's entire test contract
  is Jupiter plus ArchUnit. A module that ends up with JUnit 4 on the test classpath alongside Jupiter
  can produce a build that succeeds while running a subset of the tests — the same *shape* of failure as
  RISK-001, arrived at differently. Both artifacts are available offline
  (`junit-jupiter` is used in the reactor already; `archunit 1.2.1` is in the local repository), and a
  working precedent exists: `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pom.xml:38` pins
  `<junit-jupiter.version>5.11.3</junit-jupiter.version>` for its whole subtree.
- **Probability**: Moderate · **Effect**: Tolerable · **Level**: Medium
- **Mitigation strategy**: Avoidance (copy the working precedent)
  - Pin `junit-jupiter` (5.11.3, matching the dexlib2 subtree so the reactor has one version, not two)
    and `archunit-junit5` (1.2.1) in `rvsec-crysl/pom.xml`'s `dependencyManagement`; declare them in the
    three children.
  - Assert **counts, not colours**: G00 0.21 asserts a non-zero `Tests run:` per module (shared
    indicator with RISK-001).
- **Indicators**: `mvn -pl rvsec/rvsec-crysl -am test` prints four `Tests run: N` lines with `N` equal
  to the number of test methods written; `junit:junit` absent from the four modules' resolved test
  classpaths.
- **Contingency**:
  - **Trigger**: a module reports fewer tests than it declares, or `Tests run: 0`.
  - **Actions**: inspect the resolved test classpath for a JUnit 4 leak and for the surefire provider
    actually selected; pin locally rather than diverging the root.
  - **Owner**: implementer (G00).
- **Status**: Open

---

### RISK-011: The corpus moves under the component during implementation

- **Category**: Requirements (moving target)
- **Description**: every fixed number in this change is pinned at `5fbe8173`, which is HEAD today: the
  eight calibration targets, the five M0 non-indexing specifications, the `22 of 24` pairing, the
  `18 of 24` / `15 of 23` misuse-absorption census, the upstream M3 denominator `80` (with the committed `25/55` vector standing as a labelled
  historical reconciliation), the 207-line alphabet map. Two predecessor changes are **still open on the same files**: gh105 has 2 of 74 tasks open (its
  remaining group is blocked on gh104 archival) and gh104 has 9 of 96 open — literals counted
  2026-08-24 and **stale by construction**: the gh104/gh105 state moves inside this change's window,
  so they must be re-checked at close rather than reused. The design records the
  history plainly — the predicate-substrate signature moved five times in four days and
  `predicate_graph.csv` went 85 → 45 → 70 rows.
- **Probability**: High (it moved in every prior round, and two changes are open) · **Effect**:
  Tolerable (the stamp makes the movement visible and the targets are re-runnable — this is precisely
  what `version` is for) · **Level**: Medium
- **Mitigation strategy**: Minimization (already designed) + an explicit re-open trigger
  - `version : {commit, data, corpus}` on every model and table (INV-CONF-01/02), extended per
    RISK-003; G14 14.5 re-runs the eight targets if HEAD moved.
  - **Add the trigger to the monitoring checklist rather than to a final task**: any commit touching
    `rvsec/rvsec-mop/src/main/resources/jca_android/` or `rv-android/data/jca_android/*.csv` re-opens
    G12, whoever makes it. Waiting until G14 to discover the movement means discovering it after G13b
    has already compared the component against the Python gates on a corpus that no longer exists.
- **Indicators**: `git log --oneline 5fbe8173..HEAD -- rvsec/rvsec-mop/src/main/resources/jca_android
  rv-android/data/jca_android` is empty at each review; if non-empty, G12 is Yellow until re-run.
- **Contingency**:
  - **Trigger**: the log above is non-empty.
  - **Actions**: re-run the eight targets at the new HEAD and record **both** stamps side by side
    (G12 12.5 already emits them); adjudicate any target that moved as a finding about the corpus, not
    about the component.
  - **Owner**: change author.
- **Status**: Open

---

### RISK-012: The "five surviving CI gates" are not run by CI, and CI deletes the `backup/` tree the retirement test asserts

- **Category**: Process (gate hygiene)
- **Description** (measured against `.github/workflows/ci.yml`): the Python job runs tests only for
  `modules/*/tests` (`:79-100`). `tests/parity/` appears nowhere in the workflow, and neither do
  `scripts/gh105_order_gate.py`, `scripts/gh101_conformance_check.py`, `scripts/gh104_baseline.py` or
  `scripts/gh104_gates.py` — a full grep of the file for `parity|scripts/|gh10` returns nothing. All
  five files exist and are substantial (45 KB, 16 KB, 79 KB, 74 KB and 130 KB respectively), and they
  are load-bearing **local** gates, but calling them "CI gates" (proposal, design D-14, G13b's table)
  overstates their standing in two directions at once: nothing automatic protects them today, and
  G13a task 13a.7 ("confirm no CI job changes status") is therefore vacuous as written.
  A second, sharper edge: the new `tests/parity/test_gh106_retirement.py` asserts the 13 moved files are
  **present under `backup/`**, while the workflow's first step is
  `rm -rf rv-android/backup/ …` (`:20`). If `tests/parity` is ever added to CI, that test fails for a
  reason that has nothing to do with the retirement.
- **Probability**: High (certain — verified in the workflow) · **Effect**: Tolerable (the gates still
  run when invoked; the harm is a false sense of automatic protection and a task that cannot do its job)
  · **Level**: Medium
- **Mitigation strategy**: Avoidance (say what is true) + Minimization (make the local gates explicit)
  - Restate the five as **local gates** in G13b's table and in D-14, and record the exact command for
    each in G13b 13b.5's evidence document, so "reproduced" is checkable by a reader who was not there.
  - Rewrite G13a 13a.7 into something executable: run the five commands before and after the move and
    diff their outputs. "Confirm no CI job changes status" cannot be executed against a CI that does not
    run them.
  - Write `test_gh106_retirement.py` so its *absence* assertion (the 13 files are gone from `audit/`) is
    the CI-safe half, and its *presence* assertion is skipped when `backup/` does not exist, with the
    reason printed (same discipline as RISK-002).
- **Indicators**: G13b's evidence document contains a runnable command per gate; the retirement test
  passes both with and without `backup/` present.
- **Contingency**:
  - **Trigger**: `tests/parity` is added to CI and the retirement test fails.
  - **Actions**: check the `rm -rf` step first; do not "fix" the test by weakening the absence
    assertion.
  - **Owner**: implementer (G13a), change author (D-14 wording).
- **Status**: Open

---

### RISK-013: G13a's census rule is ambiguous, and the retirement is partial

- **Category**: Process (P3 completeness)
- **Description**: G13a 13a.1 declares the census — 6 `ORDER` comparators and 7 CrySL readers under
  `audit/20260808_*`, 13 distinct files, with `batchD/alfa_language_check.py` counted in both — and
  instructs the implementer to **stop and report** if the census differs. Measured on 2026-08-24, the
  comparator half matches exactly (`alfa_automata_check.py` ×3, `alfa_language_check.py` ×2,
  `juiz_walk_batchB.py` all present). The reader half depends entirely on the predicate: a
  mention-based grep (`crysl|cryptsl`) returns **10** files under `audit/20260808_*`, against the
  declared 7 — the declared rule is "opens a `.crysl`/`.cryptsl`", which is narrower than *mentions*.
  Separately, an eleventh reader lives **outside** the declared scope —
  `audit/20260820_verificacao_plano_predicados_v2/agentA/parse_cryptsl.py` — and the proposal counts
  eleven ad-hoc CrySL readers in total while G13a moves seven. The four outside `audit/20260808_*` have
  no recorded disposition in any artifact.
- **Probability**: Moderate (the stop-and-report will fire on a rule difference rather than on tree
  movement, costing a session) · **Effect**: Insignificant (nothing depends on these files; the harm is
  churn and an incomplete P3 story) · **Level**: Low
- **Mitigation strategy**: Minimization (make the census executable) + completeness
  - Encode the census as the executable predicate it claims to be — a grep for actual file opens on
    `.crysl`/`.cryptsl` — inside `test_gh106_retirement.py`, so "the tree moved" and "the rule differs"
    are distinguishable without judgement.
  - Record the disposition of the readers outside `audit/20260808_*`: moved, kept with a reason, or out
    of scope. P3 asks for a complete story, and "eleven readers" in the proposal against "seven moved"
    in the tasks is not one.
- **Indicators**: the census predicate, run at G13a and again at G14, returns the same file list.
- **Contingency**:
  - **Trigger**: the census differs at 13a.1.
  - **Actions**: report the difference with the predicate that produced it; do not adjust the list to
    match the document.
  - **Owner**: implementer (G13a).
- **Status**: Open

---

### RISK-014: Size — 209 checkboxes, ~45 Java files, ~150 tests, one researcher, two predecessors still open

- **Category**: Estimation
- **Description**: counted 2026-08-24 after the oracle-switch revision, under the declared rule
  `grep -c '^- \[ \]'` per group file, the sixteen group files carry **193** open checkboxes (G00 23,
  G10 16, G01 14, G12/G14 13, G06/G08/G09 12, G03/G04/G05 11, G02/G11 10, G07/G13a 9, G13b 7), plus
  the 16 checkboxes of the revised `tasks.md` — **209** in total.
  For comparison, gh105 has 74 tasks (2 open) and gh104 has 96 (9 open) — both still active. The work
  is in Java, in a reactor subtree with no existing test infrastructure of its own, with a critical path
  five groups deep (G00 → {G01, G02, G03} → G10 → G12 → G13b → G14) whose last two links (G12
  calibration, G13b reproduction evidence) are the ones that cannot be parallelised and cannot be
  rushed, because their product is adjudication.
- **Probability**: High · **Effect**: Tolerable (schedule, not correctness — provided the pressure does
  not land on G12, which is RISK-005) · **Level**: Medium
- **Mitigation strategy**: Minimization (the dispatch plan already exists; commit to the split points)
  - `tasks.md` already declares 6-way parallelism after G00 and names the two groups likeliest to
    exceed the sizing rule (G01, G10). **Pre-commit those splits** (G01a lift / G01b idioms; G10a
    comparison / G10b normalizations) rather than deciding mid-implementation, when the decision
    competes with momentum.
  - Treat **G12, not G14, as the release gate**. G14 is verification and documentation; G12 is where the
    change either becomes a measurement or does not.
  - Land G13a on day one as planned — it is inert, and it keeps the final diff about the component.
- **Indicators**: number of groups closed per session against the dependency graph; any group whose
  file exceeds 15 implementation files without having been split.
- **Contingency**:
  - **Trigger**: G10 or G12 slips while metric groups are still open.
  - **Actions**: cut scope at the metric boundary, not inside a metric — a complete M0–M3 with M4
    deferred is publishable; a half-calibrated M4 is not.
  - **Owner**: change author.
- **Status**: Open

---

### RISK-015: JDK 21 is not the host default

- **Category**: Tools (build environment)
- **Description**: G00 0.6, G05 5.9 and G14 14.2 all say "with JDK 21 in the prefix". Measured,
  `/usr/lib/jvm` contains only JDK 25 (`java -version` → Temurin 25.0.3), and JDK 21 exists solely under
  SDKMAN (`~/.sdkman/candidates/java/21.0.12-tem`; 8, 11, 17, 21 and 25 are all installed there). The
  reactor pom targets 21 and has been observed to build under 25, so this is not a blocker — but a
  `.m2` populated by alternating JDKs, or a build run without the prefix while a task claims 21, makes
  the "built under 21" statement in G14 unverifiable.
- **Probability**: Moderate · **Effect**: Insignificant · **Level**: Low
- **Mitigation strategy**: Avoidance (write the command once)
  - Record the exact prefix in G00 0.6 and reuse it verbatim in 5.9 and 14.2, e.g.
    `JAVA_HOME=$HOME/.sdkman/candidates/java/21.0.12-tem mvn clean install -DskipMopAgent`.
  - G14 14.2 already notes the reactor also builds under 25; keep that note, since it prevents a future
    session from treating a 25 build as a defect.
- **Indicators**: the build log's `Java version:` line reads 21 for the runs the tasks claim as 21.
- **Contingency**: if a mixed-JDK `.m2` is suspected, rebuild the reactor from clean under the pinned
  JDK before running the calibration gate. **Owner**: implementer.
- **Status**: Open

---

### RISK-016: Two copies of the upstream oracle exist in the workspace

- **Category**: Technology (corpus identity)
- **Description**: the upstream CrySL rules exist twice — `rvsec-cognicrypt/CrySL-Rules` (49 files, the
  path the design names) and `rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules` (49 files, the
  path an existing script uses: `scripts/gh101_predicate_edges.py:39`). Measured 2026-08-24,
  `diff -rq` between them is **empty** — they are byte-identical today. They are, however, in different
  repositories with different lifecycles, so a future update to one and not the other would silently
  change which upstream oracle a run reads, and RISK-003's single-commit stamp would not show it.
  Since the oracle switch (D-06) these are the two copies of the **only** oracle, which raises the
  stakes of the choice without changing it.
- **Probability**: Low (they agree today, and gh106 reads only the named path) · **Effect**: Tolerable
  · **Level**: Low
- **Mitigation strategy**: Acceptance, with the choice named
  - Name `rvsec-cognicrypt/CrySL-Rules` as the canonical upstream path in the CLI's documentation and in
    the emitted report header; combine with RISK-003's per-corpus revision stamp, which makes a
    divergence visible the first time it matters.
- **Indicators**: the report header names the upstream path and revision it read.
- **Contingency**: if the two ever diverge, record which one the published numbers were taken against
  before deciding anything else. **Owner**: change author.
- **Status**: Accepted (documented; no action beyond the stamp)

---

## Monitoring Schedule

- **Review cadence**: at each Full-SDD phase boundary of this change.
  - **End of Design (now)**: register created. Four items must be encoded into artifacts **before G00
    starts**, because they change the types or the poms and both are day-one work: RISK-003 (per-corpus
    revision in `Version`), RISK-008 (`Label` type, or the invariant downgraded in writing), RISK-009
    (the `-core` dependency rule decided), RISK-004 (commit the evidence base and the change tree).
  - **During Implement (`/opsx:apply`)**: RISK-001 and RISK-010 are checked at G00 close (non-zero
    `Tests run:` per module) and again when the CI step lands; RISK-011's git trigger is checked at every
    group close; RISK-002's classification is applied as each test is written, not retrofitted.
  - **At G12 (the release gate)**: RISK-005 and RISK-006 are hard gates — no unadjudicated mismatch, and
    every target labelled with its route class. RISK-007 is resolved (declared-type
    pairing); verify the rule is emitted beside every upstream-derived table.
  - **During Verify (`/rv-verify` + `/opsx:verify`)**: RISK-001 (CI runs the suite), RISK-012 (the local
    gates were actually run, with commands recorded), RISK-013 (census predicate stable), RISK-015 (the
    JDK the build claims).
- **Risk review checklist** (run at each boundary):
  - [ ] Any new risk surfaced by the first real run over the corpora?
  - [ ] RISK-001: does CI report a non-zero `Tests run:` for all four `rvsec-crysl` modules?
  - [ ] RISK-002: is every oracle-dependent test marked, and does a skipped run print its reason?
  - [ ] RISK-003: does every emitted table carry a revision for **each** corpus that contributed to it?
  - [ ] RISK-004: is `openspec/changes/gh106-*` committed, and is the Phase 0 harness tracked?
  - [ ] RISK-005: zero targets in state *mismatch, unadjudicated*? No decision in `design.md`
        §Decisions edited without a written adjudication?
  - [ ] RISK-006: does the gate print a route class per target, and does the change avoid claiming
        "eight independently measured targets"?
  - [ ] RISK-007 (resolved): is the declared-type pairing rule still the one emitted beside every upstream-derived table?
  - [ ] RISK-008: can `ModelShapeArchTest` be made to fail on a deliberate violation?
  - [ ] RISK-009: is `-core`'s dependency rule decided and recorded, and does its classpath still
        exclude both parsers?
  - [ ] RISK-010: `junit:junit` absent from the new modules' test classpaths?
  - [ ] RISK-011: `git log 5fbe8173..HEAD -- <jca_android paths>` still empty?
  - [ ] RISK-012: are the five local gates run with recorded commands, and does the retirement test
        survive a missing `backup/`?
  - [ ] RISK-013: does the census predicate return the same 13 files it did at G13a?
  - [ ] RISK-014: any group past 15 implementation files without the declared split?
  - [ ] RISK-015: does the build log say Java 21 where a task claims 21?
  - [ ] Any risk closeable?
- **Owner**: change author (Pedro Costa).

## Change Log

| Date | Risk | Change |
|------|------|--------|
| 2026-08-24 | all | Register created at end of Design phase. Every entry verified against the tree at HEAD `5fbe8173` rather than derived from `design.md` §Risks — which is why six of the sixteen are risks the design does not carry: RISK-001 (`ci.yml:30` builds with `-DskipTests`; only dexlib2 `grammar-tests` re-enables them at `:44`), RISK-002 (`MetaCrySL` @ `fb1ecab` and `rvsec-cognicrypt` @ `f2f4d3b` are separate repositories, absent from the CI checkout), RISK-003 (`Version` has one `commit` field for three repositories), RISK-004 (`docs/handoff/20260824_arnes_adjudicacao/` 0 files tracked; three Phase 0 docs untracked; the change tree untracked; `ci.yml:20` deletes `backup/`), RISK-006 (targets 5, 6 and 8 of the eight are a hand-maintained CSV, a restatement of the component's own pairing rule, and the AST proxy the component implements), RISK-012 (`tests/parity` and the four `gh10*` scripts appear nowhere in the workflow, so "CI gates" overstates their standing and 13a.7 is vacuous as written). Verified and **confirmed** rather than corrected: the corpus counts (215 `.mop` = 23+24+23+118+27; `api30` 33; upstream 49), the availability of every dependency in the local repository (`CrySLParser 4.0.6`, `javamop 0.9.3-SNAPSHOT`, `guava 33.5.0-jre`, `archunit 1.2.1`), the existence of every parser API the design assumes (`SpecExtractor`, `MOPNameSpace`, `MOPSpecFile`, `DumpVisitor`, `crysl/parsing/CrySLModelReader`, `crysl/rule/StateMachineGraph`), `android-30` present under `ANDROID_HOME`, and that HEAD is exactly the commit the eight targets are pinned at. Two smaller corrections recorded in the bodies: G02 2.2 cites `scripts/normalize_api30.py`, which does not exist (the file is under `docs/handoff/20260824_arnes_adjudicacao/scripts/`); and the V10 `-core` pom validated in Phase 0 declares a Gson dependency, contradicting G00 0.2's "zero external dependencies" (RISK-009). |
| 2026-08-24 | scope, 002, 003, 004, 006, 007, 011, 014, 016 | **Oracle-switch revision** (same day, after the risk pass). D-06 makes `rvsec-cognicrypt/CrySL-Rules` the single oracle — 49 rules, 47 of which parse with **no** normalization; the two failures are `OAEPParameterSpec` (reserved word `alg`) and `SSLEngine` (`ORDER` references `cp1`, declared `ep1`) — and abandons `MetaCrySL/generated/api30`, which survives only as the method note recording that it deletes 25 clauses across 12 of the 22 paired rules under R1. Folded in: the lexical normalization died (G02 rewritten); pairing is by declared type, `22 of 24` (RISK-007 resolved and closed); calibration target 4 is `47 of 49` via `V3Fresh.java` and target 5 is the upstream denominator `80` via the two independent R1 implementations, with `constraint_table.csv` demoted to a labelled historical reconciliation (RISK-006 mitigated by D-18); RISK-002 and RISK-003 re-scoped to two repositories plus the SDK — reduced, not resolved: `rvsec-cognicrypt` is still absent from the CI checkout; the harness inventory corrected to six probes, three scripts and 18 raw outputs (RISK-004); RISK-011's gh104/gh105 open-task literals stamped as stale within this window; RISK-014 recounted to 209 checkboxes (193 in the group files plus 16 in the revised `tasks.md`); RISK-016 now guards the two copies of the *only* oracle; the decision range extends to D-01 … D-19 (D-18 route independence, D-19 the EMF provenance route). |
