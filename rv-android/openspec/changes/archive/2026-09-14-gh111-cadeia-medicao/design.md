# Design: gh111-cadeia-medicao

## Context

Seven repairs on one pipeline, spanning the Java reactor (`rvsec-gator`) and five Python modules of the uv workspace. The proposal maps the chain link by link and establishes the identifier forms it carries; this document decides how each repair is built, in what order, and how each is verified.

Three constraints shape every decision:

**The reactor and the workspace are separate builds.** `AnalysisEntrypoint.java` lives in `rvsec/rvsec-android/rvsec-gator/sootandroid/`, outside the uv workspace, and `JsonReportWriter.java` / `ReachabilityEnricher.java` live in the sibling `client` module. Both are rebuilt in **one** `mvn clean install` under JDK 21 and delivered to `rv-android/lib/gator/` through the `main.basedir` mechanism, whose copy is bound to the `install` phase — a `mvn package` does not refresh the deployed jars. The reactor runs its own unit tests by default (no gator pom sets `skipTests`; only `-Pcheck` does), so the build command must **not** pass `-DskipTests`: `ReachabilityEnricherTest::topLevelMetadataReturnsExactlyThreeKeys` and `JsonSchemaKeysTest` (whose three `getDeclaredFields()` sweeps — `valuesAreUnique`, `allFieldsArePublicStaticFinalString`, `allValuesAreNonEmpty` — automatically cover any key task 1.4 adds) are the tests a mistake in task 1.4 would trip. `ExtractClassesFilterTest` **is** a guard for one of the edits and not for the others: all 32 of its assertions call `RvsecAnalysisClient.isAppClass`, which the INV-ANA-71 repair changes (and which the guard and writer edits do not touch). Its existing cases pin only root-anchored resource classes (`com.gh4a.R`, `com.gh4a.R$layout`, `com.gh4a.BuildConfig`), so they stay green under the widened rule and say nothing about it — the module-level and ancestor-key cases are new assertions. And nothing in the reactor guards task 1.1 at all — which is exactly why task 1.2 exists. `client/pom.xml:18` additionally sets `skipITs=true`, so the integration tests need an explicit `-DskipITs=false` pass.

It is **not** true that nothing in the Python suite exercises the jar: `tests/parity/test_json_keys.py:67` shells out to `java -cp lib/gator/rvsec-analysis-client.jar` and asserts the Java and Python key sets are equal against the `_JK` mirror at `static_analysis_parser.py:79`. That gate has two blind spots worth knowing before tasks 1.4/2.0 add a top-level key — it **skips** rather than fails when the jar is absent or `java` is off the PATH (`:83-89`), so a Java edit that was never `install`ed passes green; and it compares the `JsonSchema.Keys` constants, not the JSON actually emitted, so a key written as a literal would evade it entirely.

**D9 is not observable under the default policy** — which is how every recorded run has executed. `App.code_package` returns the manifest verbatim when both package policies are off, so under that policy a guard reading `codePackage` reads today's value and changes nothing until D2 supplies a different one. It is observable under `--package-detector`, which is live and spec-mandated (INV-EXP-34): the detector elects `com.github.cvzi` for `com.github.cvzi.screenshottile_148`, and the class count moves 21 → 535 with no D2 anywhere. That is what makes D9's acceptance an end-to-end run rather than a probe. `D9Probe.java` stays as the ~13 s prediction; it imports nothing from `presto.android`, reimplements the demotion predicate and prints both guards without mutating the Scene, so editing `AnalysisEntrypoint.java:119` changes its output by exactly zero — it can characterise the hypothesis, it cannot accept the repair.

**Measurement changes must be attributable.** Three items move numbers (D9, D2, D3) and two of them share a symptom. The ordering D9 → D1 → D2 → D3 exists so that each delta has one owner: D9 lands with an acceptance of its own under `--package-detector` and no effect on the default path; D1 lands the instrumentation that makes any delta readable; D2 then produces a measurable improvement attributable to D2; D3 produces one attributable to D3, with an automatable single-APK witness. Attribution binds the **measurement runs**, not the commits — which is why the ordering does not by itself forbid running D2's and D3's code work in parallel, and why the file matrix does.

Relevant requirements: FR21, FR24, NFR03, NFR06.

## Architecture

```
                        ┌──────────────────────── run policy (scalar) ───────────────────────┐
                        │                                                                     │
  rv-experiment         ▼                                                                     │
  __main__ / config.py  strip_build_type_suffix ──┬──> ExperimentConfig ──> PlatformConfig ────┤
     (entry point:                                │                                            │
      env + CLI)                                  │                                            ▼
                                                  │                                    App(strip=…)
                                                  │                                     (rv-android-core)
                                                  │                                            │
                                                  │                            code_package ───┤
                                                  │                                            │
                                                  ▼                                            │
                                        rv-instrumentation-ajc                                 │
                                        receives the DECLARED id ← INV-EXP-36                  │
                                                                                               │
  rv-static-analysis ──── -clientParam codePackage=<key> ───────────────────────────────────────┘
     config.py:395                    │
                                      ▼
  ┌─────────────────────────── rvsec-gator (Java reactor) ───────────────────────────┐
  │  Main.main ─> Configs.clientParams populated                                      │
  │  AnalysisEntrypoint.run                                                           │
  │     :112 rescue by <activity>                                                     │
  │     :119 GUARD ── was: manifest ── becomes: getClientParamCode("codePackage=")     │  D9
  │     :121 demotion via libPackages.txt (2170 patterns)                              │
  │  RvsecAnalysisClient :90 filter ── codePackage ?: manifest                         │
  │  JsonReportWriter :84 ── records manifest + NEW: effective key, its origin,        │
  │                          and class_defs_under_key                                  │  D9 build
  └───────────────────────────────────────────────────────────────────────────────────┘
        (both Java edits ship in ONE reactor build — the install-phase copy is what
         delivers lib/gator/, so a second unbuilt edit would leave a stale jar)
                                      │  <apk>.apk.json
                                      ▼
  rv-static-analysis/parser ── StaticAnalysisParser
     :371 / :455  normalizer calls REMOVED                                              D3
     ParserDiagnostics ── unmatched_out_of_scope / unmatched_in_scope                    D1
     denominator gate ── refuses empty, degenerate AND zero-universe                     D1
                       ── reads class_defs_under_key FROM the artefact (pure predicate)
                                      │
                                      ▼
  rv-android-core/domain/coverage.py ── LogcatRepository.register_method_call
     :660 / :672  discards now counted, classified by scope                              D1
                                      │
                                      ▼
  rv-platform/result_processor.py ── summary.csv gains denominators, counters, measured   D1
     + a save after result processing, without which write_errors never reaches disk       D4
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `AnalysisEntrypoint.run()` | app/library classification of the Soot Scene | `Configs.clientParams`, manifest | mutated Scene |
| `App.code_package` | the scope key a study treats as app-owned | `strip_build_type_suffix: bool` | `str` |
| `neutralize_build_type_suffix()` | the denylist rule, one place | `str` | `str` |
| `StaticAnalysisParser._parse_reachability` | build the denominator from the artefact | artefact `dict` | `Classes` |
| `check_denominator()` (module-level function, `denominator_gate.py`) | refuse empty, degenerate and zero-universe denominators | `Classes`, the artefact's `class_defs_under_key` | pass / raise |
| `ParserDiagnostics` (`rv-android-core`, `domain/coverage.py:453`) | count discards, split by scope | discard events | serialized `dict` |
| `LogcatRepository.register_method_call` (`domain/coverage.py:640`) | the crossing | `RvCoverageLog` | registration or classified discard |
| `ResultProcessor` | the report | `LogcatRepository`, `ParserDiagnostics` | `summary.csv` |
| `D9Probe` | **predict** the guard's effect without a full run — not an acceptance test | apk, manifest, android.jar, libPackages, key | class counts under both guards |
| end-to-end `--package-detector` run | **accept** the guard against the deployed jar | `com.github.cvzi.screenshottile_148` | `len(reachability)`: 21 before, 535 after |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-ANA-65 (guard reads code key) | `rvsec-gator/sootandroid/.../AnalysisEntrypoint.java:119`, via an extracted `resolveScopeKey(String, String)` | `AnalysisEntrypointTest` (4 cases: prefix stripped / `null` / empty / non-prefix) **plus** an end-to-end `--package-detector` run asserting 21 → 535; `D9Probe` predicts the 4 collapsed + `app.pachli` control |
| INV-ANA-66 (artefact records the key, its origin and `class_defs_under_key`) | `client/.../json/JsonReportWriter.java`, `ReachabilityEnricher.topLevelMetadata()`, `JsonSchema.Keys` + the `_JK` mirror at `static_analysis_parser.py:79` | `test_artifact_records_effective_key`; `ReachabilityEnricherTest` (its 3-key assertion moves); `tests/parity/test_json_keys.py` |
| INV-ANA-71 (generated resource classes leave at every segment) | `RvsecAnalysisClient.isAppClass` — test the class name's **last segment**, not the suffix after the key | `ExtractClassesFilterTest` (new cases: module-level `app.pachli.core.database.R`, ancestor key `com.github.cvzi` over `…screenshottile.R$*`, `Manifest$*`, and a negative case pinning `_Factory`/`_Impl`/`$$serializer` **in**) |
| INV-ANA-70 (artefact not reused across keys) | `analysis/static/static_analysis.py:323-335` cache check | `test_stale_artifact_key_mismatch_regenerates` |
| INV-ANA-67 (no transformation on consumption) | `static_analysis_parser.py` — remove `:371`, `:455`, the import and the field | `test_parser_stores_artifact_spelling`, `test_capitalized_package_segment` |
| INV-ANA-68 (discard counters split by scope) | `rv-android-core/.../domain/coverage.py:453` `ParserDiagnostics`, `to_dict()` | `test_diagnostics_split_by_scope`, `test_diagnostics_serialized` |
| INV-ANA-69 (denominator gate) | new `check_denominator()` in `rv-static-analysis/analysis/static/denominator_gate.py` | `test_gate_refuses_degenerate`, `test_gate_refuses_empty`, `test_gate_admits_small_app`, `test_gate_warns_at_analyze` |
| INV-CORE-58 (neutralization rule) | `rv_android_core/util/android/build_type_suffix.py`, used by `domain/app.py` | `test_neutralize_*` (single, stacked, capitalized, floor, off) |
| INV-CORE-59 (denylist is not total) | documented in `app.py` docstring; enforced by INV-ANA-69 | `test_uncovered_suffix_reaches_gate` |
| INV-CORE-60 (crossing counts) | `domain/coverage.py:640-674` (`LogcatRepository`) | `test_register_counts_out_of_scope`, `test_register_counts_in_scope` |
| INV-CORE-61 (`write_errors` round trip **and persistence**) | `domain/task.py` `to_dict`/`from_dict` (type `Dict[str, int]`) + a save after `Platform._process_results()` and in `rv_platform/__main__.py:497-514` | `test_write_errors_round_trip`, `test_legacy_tasks_json_loads`, `test_write_errors_survive_result_processing` |
| INV-CORE-62 (`setup_file_logging` caller) | `rv-experiment/__main__.py` entry point | `test_file_logging_installed_at_entry_point` |
| INV-EXP-35 (env var at entry points) | `rv-experiment/config.py`, `rv-static-analysis/__main__.py`, `ENV_*` constant | `scripts/check_env_vars_drift.py` reports zero violations |
| INV-EXP-36 (policy excluded from ajc) | `rv-experiment` construction sites; `rv-instrumentation-ajc` untouched | `test_ajc_receives_declared_id` |
| INV-EXP-37 (no silently disabled step) | `pre_processor.py:318,433-492` | `test_skip_instrument_with_static_aborts` |
| INV-EXP-38 (monitors provenance) | `pre_processor.py` + `out/monitors` provenance marker | `test_skip_monitors_wrong_set_aborts` |
| INV-EXP-16 (modified) | `pre_processor.py:433-492` | `test_logged_set_equals_executed_set` |
| INV-PLT-33 / INV-PLT-34 (report columns) | `result_processor.py` | `test_summary_has_denominators`, `test_summary_counters_not_summed` |
| INV-PLT-35 (empty cells, all six percentages) | `result_processor.py:903-917` (`summary.csv`), `:483-493` (`coverage.csv`), `:1034-1064` (`results.json`); discriminator `total_classes == 0` | `test_summary_empty_when_no_denominator`, `test_coverage_csv_empty_when_no_denominator` |
| INV-PLT-36 (`measured` column) | `result_processor.py` header + row builder; consumers made live in task 8.3 (`aperv_objective.py`, `analyze_calibration.py`, `verify_phase.py`, aperv-tool `loader._PAYLOAD_COLUMNS`) | `test_measured_false_when_no_denominator`, plus 8.3's acceptance: the aggregate verdict changes when one row flips to `measured=False` |
| INV-PLT-19 (restated header) | `result_processor.py:847-861` | `test_summary_header_exact` |
| INV-PLT-37 (directional summary↔coverage consistency; **new number** — the base's INV-PLT-17 is a different rule and is left alone) | `scripts/regenerate_results/verify.py:164` (check C3) | `test_c3_directional_no_denominator`, `test_c3_directional_measured_zero` |
| INV-PLT-15 / 16 / 18 (amended clauses only; the base bodies stand) | `result_processor.py` — the degraded-case wording at `:206` and the two writers' empty-cell path | covered by INV-PLT-35's tests plus `test_resume_health_warning_wording` |
| INV-EXP-39 (consolidated pre-processing report) | `experiment/workflow/pre_processor.py` | `test_consolidated_report_names_two_of_fifty` |
| INV-CORE-18 (modified — third provenance value) | `domain/app.py` `code_package_source` | `test_source_manifest_neutralized`, and the existing consumers at `static_analysis.py:88,235,243,448` and `rv-platform/tests/test_platform.py:144` |
| INV-ANA-60 (amended — the word *normalized* is struck) | `openspec/specs/analysis/spec.md:394`, by hand at sync time (task 8.17 — the merge engine rebuilds only `## Requirements`) | `test_capitalized_package_segment` (an ACTIVITY window matches in the artefact spelling) |
| REMOVED INV-ANA-02 | deletion of `signature_normalizer.py` + its tests, after a `backup/` copy (P3) | grep gate: zero references in `modules/*/src` **and** `scripts/` |

## Goals / Non-Goals

**Goals:**
- Both scope keys of a GATOR run resolve to the same value.
- The effective scope key reaches disk.
- No identifier is transformed on the consumption path.
- Every discard is counted and classified; every denominator is gated.
- A flag combination that disables a requested step says so.

**Non-Goals:**
- **Pruning `libPackages.txt`.** After D9 the list cannot reach the **class** denominator — everything under the app prefix leaves the loop at the guard — but it still governs what the GUI/WTG analysis treats as library (`Hierarchy.java:305` → `FlowgraphRebuilder.java:72`) and therefore the `reachable` / `reachesTarget` / `directlyReachesTarget` predicates, which are the denominators of `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target` — three of the six published coverage columns. So it does not stop being a denominator risk; it stops being a risk to one denominator and stays one to three others. Pruning changes measurement for every app; recorded as debt.
- **A dot boundary on `isAppClass`.** Decision D-C, deferred. The demotion is upstream of `isAppClass` and independent of it, and it is a different defect from the root-anchored resource test that INV-ANA-71 repairs — that one moves here, the dot boundary does not.
- **Removing annotation-processor output from the denominator.** 5,816 classes carrying 36,264 non-trivial methods (`_Factory`, `_Impl`, `_MembersInjector`, `$$serializer`, `Hilt_*`, `Dagger*`, DataBinding), measured over the 162 artefacts — 2.70% of classes and 4.20% of methods. Unlike the resource classes of INV-ANA-71, this code executes, so its removal is a redefinition of the denominator and a research decision, not a repair. Recorded with its numbers as an open question.
- **Repairing the ajc instrumenter.** Out of scope by researcher decision; the divergence is recorded.
- **Widening the `<activity>` rescue branch** to services, receivers and providers. With the guard repaired it stops being load-bearing.
- **Filtering violations against the static analysis.** Withdrawn (Q8): two legitimate scenarios forbid it — running an instrumented APK with no static analysis, and wanting library violations.
- **Provenance columns and checksum scope** (D5). Withdrawn, and verification showed it would be inert.
- **The `new`→`<init>` and unresolved-owner repairs** — they belong to #69 and are already written there.

## Decisions

**D-1. The guard reads the client parameter directly, rather than the client passing it down.**
`Configs.getClientParamCode("codePackage=")` is available inside `sootandroid` (`Configs.java:292`) and `Configs.clientParams` is populated by `Main.main` before `setupAndInvokeSoot()` runs. The alternative — having `RvsecAnalysisClient` resolve the key and hand it to the entrypoint — inverts the run order (the entrypoint runs first, to decide what exists for the client to filter) and would introduce a `sootandroid` → `client` dependency that does not exist. Few lines, one site.

**D-2. The neutralization rule lives in one function in `rv-android-core`, not in the GATOR argv.**
The `AnalysisEntrypoint` receives the key already resolved. Repeating the denylist on the Java side would create a second implementation of a rule whose subtleties (lowercase, repeated application, two-segment floor) are exactly the kind that drift apart. Rejected alternative: neutralize inside `config.py` when building the argv — it would leave `App.code_package` reporting one key while GATOR used another, reintroducing the two-key problem this change exists to end.

**D-3. The policy is a run scalar, not a per-APK map.**
Considered and rejected: a curated key channel (CSV column, config field) per APK. It would need a loader, an input policy that does not exist today, and resume semantics, against a benefit that a scalar already delivers for 162/162 of the article corpus and 179/219 of the broad one. The 40 APKs no string rule resolves (`de.grobox.liberario` → `de.grobox.transportr`, the 13 `metadude` apps → `nerd.tuxmobil.fahrplan.congress`) are not a case for a bigger list — they are the case for the gate. This mirrors `package_detector` under INV-EXP-34.

**D-4. The gate compares against the APK's compiled class universe, and the comparison subtracts generated classes first.**
`class_defs_size` across the APK's DEX files, counted under the effective key, is available cheaply from the APK the run already opened — and is recorded **into the artefact** at write time (D-11), which is what lets the gate run on every consumption path. A fixed floor ("fewer than N classes is suspicious") would reject `com.tananaev.passportreader` (18 classes, correct) and admit `com.github.cvzi.screenshottile` (21 of 550, collapsed). The ratio is the discriminator; the absolute count is not.

The raw ratio, however, is not the right one, and an earlier version of this document justified the threshold with a claim that measurement refutes: *"the healthy small apps sit at 100%"*. Measured over all 162 artefacts, the healthy floor is **0.5610** (`org.cry.otp_31`, 23 of 41) and 17 of 158 healthy apps sit below 0.90 — `com.tananaev.passportreader`, the app named just above as "18 classes, correct", is in fact **18 of 28 = 0.6429**. The cause is exact: its ten missing classes are `…passportreader.R` and nine `R$*`, which `RvsecAnalysisClient.isAppClass:294` strips from the parsed side and nothing strips from the compiled side.

So the **producer** applies `isAppClass` to the compiled universe before recording `class_defs_under_key`, and the gate merely divides. The subtraction cannot live in the gate: `check_denominator` receives an `int`, and filtering by name needs the names. One predicate on both terms is also what makes the agreement exact rather than approximate — the corrected ratio *is* the client's own filter re-derived. On that corrected ratio the healthy band sits at **exactly 1.0 for all 158 healthy artefacts** (re-measured 30/08 from the corpus DEX headers plus the `isAppClass` predicate as written), the four collapsed artefacts sit at 0.0010–0.0393, and the threshold is **0.15** — 3.8× above the collapsed ceiling (`com.github.cvzi.screenshottile`, 21/535 = 0.0393 under the root-only rule) and 6.7× below the healthy floor, inside a 25.5× separation between the bands. Widening the strip to every segment (INV-ANA-71) moves both terms of the ratio, because both answer to `isAppClass` — the absolute denominators shift, the separation does not. Two riders the numbers demand. First, the calibration holds **under the neutralized key**: under the literal manifest key 75 of the 162 have no compiled class at all (0/0 is not a low ratio, it is no ratio), and a 0.15 gate would refuse 75 apps, 71 of them healthy — which is why task 2.6 lands the gate warn-only until D2 supplies the key. Second, the threshold is principled rather than tuned only because of the subtraction; without it, any value that catches the collapsed cases also rejects healthy apps.

**D-4b. What the 0.15 threshold actually catches, once D9 has landed.**
Worth stating, because D-4's calibration reads as though the threshold discriminated live measurements and it does not. After D9 the guard and the client answer to one key (INV-ANA-65), so every non-generated class under the key survives the demotion and the ratio is **1.0 by construction** — which is exactly what the corpus measurement found for all 158 healthy artefacts. A key the denylist failed to resolve lands in the zero-universe branch, not the degenerate one. And the 162 stored artefacts record no `class_defs_under_key` at all, so the gate does not run on them. The degenerate branch therefore fires on exactly one live condition, and it is a valuable one: a **stale jar** — the client filtering by the new key while the guard still runs the old one, which is the failure task 1.5 chases with sha256 — plus any future regression of INV-ANA-65. The threshold is a tripwire on the repair, not a discriminator over the corpus; the calibration of task 2.5 is what proves the tripwire is correctly placed.

**D-4c. Generated resource classes leave the denominator at every segment (INV-ANA-71).**
Measured over the 162 artefacts: 505 classes named `R`, `R$*` or `BuildConfig` are in the denominator today — 117 in `app.pachli_50`, 33 in `com.blacksquircle.ui_10028` — because `isAppClass` anchors its test at the scope key's root, so `app.pachli.core.database.R` escapes while `app.pachli.R` does not. They carry 547 methods of which **zero** are non-trivial: constant tables that can never be covered and whose only effect is to enlarge the `cov_class` denominator. The test moves to the class name's last segment.

The alternative of leaving it was considered and rejected on its own evidence: task 1.8's asserted `550` for `screenshottile` was *justified* by the leak — the elected key being an ancestor of the resource namespace, so `com.github.cvzi.screenshottile.R` matches no root-anchored pattern — which would have pinned a leaked denominator as this change's D9 acceptance number. A change whose subject is the denominator cannot ratify a known contaminant in it.

The rule stops at resource classes. Annotation-processor output (`_Factory`, `_Impl`, `_MembersInjector`, `$$serializer`, `Hilt_*`, `Dagger*`, DataBinding) is 5,816 classes carrying 36,264 non-trivial methods that execute at runtime; excluding them would redefine the denominator rather than close a leak, and it is recorded as an open question instead.

**D-5. The gate raises rather than warns.**
A warning is what the current code already emits at several of these points, and it is why the defects survived three changes. INV-ANA-69 says fail loudly. The escape hatch for a deliberate run over a truncated artefact is an explicit flag, not a default-on tolerance.

**D-6. Both normalizer call sites are removed in one task, not two.**
INV-ANA-60 matches `ACTIVITY` windows against class names. Removing `:371` alone leaves classes in the artefact spelling and windows dollar-separated, silently changing which activities are admitted. The tests that break (four, one of them by monkeypatching the method) are updated in the same task.

**D-7. `SignatureNormalizer` is deleted, not deprecated.**
P3. One consumer across `modules/*/src`; with the two call sites gone it is dead. Keeping it "in case a future GATOR emits dotted inner classes" is exactly the speculative-generality P1 forbids, and the hypothetical is falsified: GATOR emits `SootClass.getName()`.

**D-8. The two discard counters are separate columns, empty when unmeasured — and emptiness is paired with a `measured` boolean.**
Writing `0` for "no diagnostics produced" would assert a measurement that was not made — the same class of silence this change removes. So the cell stays empty.

An earlier version of this decision stopped there, on the reasoning that "empty cells preserve the distinction". They do not, and the correction is the reason a column was added. The pandas consumers of `summary.csv` read it with `pd.read_csv` and no `dtype`; an empty cell becomes `NaN`; and `.mean()`, `.groupby()` and `.dropna()` **skip** `NaN`. The row count is unchanged while the denominator of every aggregate changes, with nothing recording it — which is precisely the failure class this change exists to remove, relocated one layer downstream. (Not every consumer is pandas: three scripts read summary-schema CSVs with `csv.DictReader` + `float()`, where an empty cell raises `ValueError` instead — task 8.3 names them.) The measured consequences, corrected 30/08 against the code: `scripts/verify_phase.py` has **no** coverage gate — its gate at `:115` is over `errors`, and the `cov_method` means at `:385-386` feed a check that is `passed=True  # Informational` — so what changes silently there is a report, not a verdict; the verdict-class consequence is that `scripts/aperv_objective.py:76-78` **and** `scripts/analyze_calibration.py:186-192` feed `scipy.stats.trim_mean`, which does **not** skip `NaN`, so an APK whose rows are all empty makes the APE-RV calibration objective return `nan`.

A boolean survives a `.mean()`; an empty cell does not. `measured` is therefore not redundant with emptiness — it is the half of the signal that reaches an aggregate. (Researcher decision, 29/08.) And the column is **live, not merely published** (researcher decision, 30/08): task 8.3 makes the two `trim_mean` consumers and `verify_phase.py`'s informational means filter by it, and adds it to the aperv-tool loader's `_PAYLOAD_COLUMNS` — with an acceptance test in which the aggregate verdict changes when a row flips to `measured=False`. A related boundary, decided the other way (researcher decision, 30/08): `tasks.json`'s `coverage_metrics` deliberately keeps `0.0` for the unmeasured case — the field is consumed as a number by the resume protocol and by aperv-tool's loader, and the not-measured distinction is carried by the CSVs' empty cells and by `measured`; aperv-tool's `_coverage_rank` already ranks a missing number below every present one on its own side.

**D-9. The monitors provenance check uses a marker file written by the generator.**
Alternative rejected: infer the set from the monitor file names. The sets share most names; the ones they do not share are exactly the ones a mismatch would hide.

**D-10. INV-EXP-16 is made true by executing, not by excluding (researcher decision, 29/08).**
An APK in `instrumented_apks/` with no `.apk.json` runs; the log stops claiming an exclusion that never happens; its coverage cells are empty and its violation columns are written.

Three prior decisions force it. Violations do not depend on static analysis (Q8, whose first scenario is running an instrumented APK with no static analysis, already implemented at the report level in `result_processor.py:632-638`) — excluding the APK from execution would destroy that scenario one layer earlier. Excluding APKs so a number closes is a named anti-pattern that has already cost this corpus 55 applications. And once the denominator is a published column (INV-PLT-33), excluding a denominator-less row becomes a reader-side decision, explicit and revisable, instead of a pipeline-side one that is irreversible and invisible.

Alternatives considered. **Exclude for real**, using the `apks_filter_file` channel the `Platform` already honours at `platform.py:356-363` — cheap to build, and rejected on the three grounds above. **Abort the run** when static analysis was requested and did not produce for every APK — its core is right and survives as INV-EXP-39, but as a consolidated report rather than an abort: stopping a 200-APK campaign because GATOR failed on three is a cost the failure does not justify.

The rider carries the decision's weight: empty cells, never `0.00` (INV-PLT-35). `_percentage` returns `0.0` for `0/0`, so without the rider this decision would publish rows in which "no denominator" and "covered nothing" are the same value — the exact ambiguity the rest of this change removes.

**D-11. The producer records `class_defs_under_key`; the consumer does not recompute it.**
The gate needs the APK's compiled class universe. The producer has the APK open; no consumer does. `parse_file(file_path)` and `read_static_analysis_files(results_dir, apk)` — where `apk` is a filename string — see a path, and INV-ANA-61 forbids handing the parser a package key at all. Recording the count in the artefact next to the effective key turns the gate into a predicate over the artefact alone, which is the only form that also runs on the two paths that produced today's 162 files: resume, and `--process-results`, both of which re-parse `.apk.json` from `result_processor.py:245-325`. Rejected alternative: passing the APK path down to the parser — it breaks INV-ANA-61 and leaves the gate silently not running on exactly the paths where a stale artefact is most likely.

**D-12. A stored artefact is reused only under its own key.**
`static_analysis.py:323-335` treats the existence of `<apk>.apk.json` as a cache hit and says so in a comment: *"We do not validate content."* The filename carries no key (`:198-200`) and the artefact's `package` member is the manifest package whatever key filtered the contents, so nothing recovers the producing key — INV-ANA-58 already records that. The standalone `--force` flag that would bypass the cache is dead code: declared at `rv-static-analysis/__main__.py:214,236` and never read. Once D2 makes the key a run policy, a re-run with the policy flipped reuses artefacts produced under the old key, and the new gate then evaluates the old artefact against the new key. The artefact's recorded key (D-11) is what makes the mismatch detectable; the cache check must consult it and regenerate or abort. This is the same mechanism as the monitors provenance marker (D-9), applied to the other reused artefact.

**D-13. The Java side is one build, and it runs its tests.**
Both Java edits — the guard in `sootandroid`, the writer and enricher in `client` — ship in a single `mvn clean install`, because the copy into `rv-android/lib/gator/` is bound to the `install` phase and a later `package` would not refresh it. This is why the artefact half of the original task 3.7 moves into Group 1: leaving it in Group 3 would have every artefact produced by tasks 3.15 and 8.10 written by a stale jar. And the build drops `-DskipTests`: no gator pom sets it (the reactor default is `false`; only `-Pcheck` skips), so the command was the only thing suppressing the client suites — of which `ReachabilityEnricherTest` and `JsonSchemaKeysTest` are the ones a mistake in task 1.4 would actually trip (`ExtractClassesFilterTest` only exercises `isAppClass`, which neither edit touches; task 1.1 has no reactor guard at all, which is why task 1.2 exists). `client/pom.xml:18` sets `skipITs=true` separately, so the integration tests need one explicit `-DskipITs=false` pass in Group 8.

## API Design

### `neutralize_build_type_suffix(application_id: str) -> str`

Module: `modules/rv-android-core/src/rv_android_core/util/android/build_type_suffix.py`

- **Preconditions**: `application_id` is a non-empty dotted identifier.
- **Postconditions**: returns `application_id` with trailing denied segments removed, comparing in lowercase and applying repeatedly, never reducing below two segments. Returns the input unchanged when no segment is denied.
- **Errors**: none; a malformed input is returned unchanged.
- **Constants**: `BUILD_TYPE_DENYLIST = frozenset({"debug","dev","beta","staging","qa","nightly","alpha","snapshot","current","head","indev"})`, `MIN_SEGMENTS = 2`.

### `App(app_path: str, *, package_detector: bool = False, strip_build_type_suffix: bool = False, validate_on_init: bool = True)`

- **Postconditions**: `code_package` is the declared applicationId when both policies are off; the neutralized id when `strip_build_type_suffix` is on and a segment was removed; the `PackageDetector` election when `package_detector` is on. `package_name` is unaffected by either policy.
- **`code_package_source`**: `"manifest"` | `"manifest-neutralized"` | `"detector"`. It reports `"manifest"` when the policy was on but removed nothing.
- **Invariant**: reads no environment variable (INV-CORE-55).

### `check_denominator(classes: Classes, compiled_under_key: int, key: str) -> None`

Module: `modules/rv-static-analysis/src/rv_static_analysis/analysis/static/denominator_gate.py`

- **Preconditions**: `compiled_under_key` is read **from the artefact**, where the producer recorded it already **net** (INV-ANA-66): the compiled classes under `key` that survive `RvsecAnalysisClient.isAppClass` — the same predicate that filtered the parsed side. The gate performs no subtraction of its own; it holds a count, not the names.
- **Postconditions**: returns on a plausible denominator — `len(classes) / compiled_under_key >= 0.15`.
- **Errors**: `DenominatorImplausibleError` naming the parsed count, the compiled count and the key, in three cases: the parsed count is zero; the ratio is below the threshold; or `compiled_under_key` is itself zero, which is not a ratio at all but the signature of a key that matches nothing — 75 of the 162 corpus APKs are in that state under the manifest key, so `0/0` would raise `ZeroDivisionError` instead of this error if the case were not named.
- **Shape**: a module-level function, not a gate class — `rv-static-analysis` has nine files, no `exceptions.py` and no class-per-check (P1). `DenominatorImplausibleError` is the one exception the gate module defines, in `denominator_gate.py` itself, subclassing `RVAndroidError`: it cannot import `StaticAnalysisException` from `static_analysis.py`, because that module imports the gate (task 2.6) and the import back would be a cycle.

### `ParserDiagnostics`

Module: `modules/rv-android-core/src/rv_android_core/domain/coverage.py:453` — **not** `rv-coverage`. Its own docstring records why it cannot move: `rv-android-core` cannot import `rv-coverage`.

- **Added fields**: `unmatched_out_of_scope: int = 0`, `unmatched_in_scope: int = 0`, `unmatched_unclassified: int = 0`.
- **`to_dict()`**: includes all three.
- **Note on INV-ANA-62 — resolved, no restatement needed**: that invariant states an arithmetic identity — records registered plus counted lines equals lines read (`coverage.py:461-462`). The new counters fire at the **crossing**, on lines that did become records, so they must not enter the identity's line-count side — and the code already carries the resolution: `discarded_lines` (`coverage.py:541-556`) hand-sums only the seven discard counters, and its docstring excludes the sentinel and grammar counters for exactly this reason ("those lines did become records"). The three `unmatched_*` counters stay out of `discarded_lines` on the same principle (task 2.9, INV-ANA-68), the identity holds unchanged, and its guard tests in `rv-coverage` (`test_logcat_parser.py:1089,:1104,:1113`) stay green.

### `LogcatRepository.register_method_call(coverage_log: RvCoverageLog) -> None`

- **Postconditions**: on a failed class or signature lookup, increments `unmatched_out_of_scope` when `coverage_log.clazz` does not start with the effective scope key, and `unmatched_in_scope` otherwise. The `logger.debug` lines stay; they are no longer the only record.
- **New state**: `LogcatRepository` needs the effective scope key to classify. It is supplied at construction, from the artefact's recorded key (INV-ANA-66) — not re-derived, per INV-ANA-58. The class is constructed at eight no-argument sites across three modules (`domain/task.py:576,594,615,679`; `rv-coverage/analysis/coverage/analyzer.py:100`; `tracker.py:157`; `parser/log/logcat_parser.py:141`; `rv-platform/components/coverage.py:58`), several on the resume path where no artefact is loaded at all; the `logcat_parser.py:141` site is additionally reached through `parse_logcat_file` by seven callers that must thread the key (task 2.2 enumerates them). The key is therefore `Optional[str]` with default `None`, and when it is `None` — which is the state of all 162 existing artefacts, none of which records one — discards are counted as **unclassified** rather than silently attributed to in-scope. It costs the row its two `unmatched_*` cells and **nothing else**: coverage is still computed from the artefact's own denominator, because the key classifies discards and filters nothing. All 162 stored artefacts carry a non-empty `reachability` (1 to 14,860 classes), so tying `measured` to the presence of a key would delete, on every resume and every `--process-results`, precisely the measurement INV-PLT-15/16 exist to recover. `measured` answers to the denominator alone (INV-PLT-35).

## Data Flow

1. The entry point resolves `strip_build_type_suffix` (CLI > env > `False`) and records it in `experiment_config.json`.
2. `App` is constructed with the policy; `code_package` returns the neutralized key and `code_package_source` reports `"manifest-neutralized"`.
3. `rv-static-analysis` passes `-clientParam codePackage=<key>`; the ajc instrumenter receives the declared id instead (INV-EXP-36).
4. `Main.main` populates `Configs.clientParams`; `AnalysisEntrypoint` reads the key at `:119`, protects the app classes, and lets `libPackages.txt` demote only what is outside the key.
5. `RvsecAnalysisClient` filters `getApplicationClasses()` by the same key; `JsonReportWriter` records both the manifest package and the effective key.
6. The parser loads `reachability` with no transformation, runs the gate against the APK's compiled class count, and initializes `ParserDiagnostics` with the recorded key.
7. Execution produces logcat; the crossing registers matches and classifies every discard.
8. `ResultProcessor` writes the denominators and the two counters alongside the percentages.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `DenominatorImplausibleError` | `check_denominator` | abort the APK's analysis, name parsed count / compiled count / key | fix the key or the guard; re-run that APK |
| Stored artefact whose recorded key differs from the run's effective key | `StaticAnalyzer` cache check | regenerate, or abort naming both keys | drop the stale artefact, or align the policy |
| Pre-processing abort (`--skip-instrument --static-analysis`) | `pre_processor._run_static_analysis` | abort naming both flags and the missing directory | drop `--skip-instrument`, or point `--apks-dir` at a previous run's `instrumented_apks/` |
| Monitors provenance mismatch | `pre_processor` monitor reuse check | abort naming both specification sets | `./clear.sh` or drop `--skip-monitors` |
| `click.BadParameter` | entry-point env parsing | abort before any `App` is constructed | correct `RV_STRIP_BUILD_TYPE_SUFFIX` |
| Missing `write_errors` key in a legacy `tasks.json` | `TaskResult.from_dict` | default to `{}` — the field is `Dict[str, int]`, a per-artefact loss count, not a list | none needed |
| Absent `codePackage` client parameter | `AnalysisEntrypoint` | fall back to the manifest | none needed; pre-change behaviour |

## Risks / Trade-offs

- **[D9 and D2 land in different builds — the Java jar and the Python workspace — and under the default policy only together produce the measured delta]** → D9's acceptance is an end-to-end run under `--package-detector`, which needs no D2, run against the rebuilt jar before D2 starts; the probe stays as the prediction. The task list makes both explicit checkpoints rather than implicit consequences.
- **[Task 1.5 rebuilds the jar and re-trips `tests/parity/test_baseline_freshness.py`]** → Group 1 regenerates the cryptoapp baseline after the rebuild. Note that a regeneration diff is large and mostly meaningless: GATOR assigns window/widget ids and orders widget lists non-deterministically, so two runs of one jar over one APK differ in several hundred lines with every count identical. Only a changed **count** is a regression.
- **[The new top-level artefact members move three gates at once]** → `ReachabilityEnricherTest`'s three-key assertion, `tests/parity/test_json_keys.py` and its `_JK` mirror all change in the same commit as `JsonReportWriter`.
- **[Removing the normalizer changes ajc-era numbers too]** → It changes them for the better by the same mechanism (both weavers emit the binary name), but the ajc archive is not re-measured by this change. Recorded, not repaired.
- **[The denylist is not total; 40 of 219 broad-corpus APKs are unresolvable by any string rule]** → INV-ANA-69 is the backstop: an unresolved key produces an empty or degenerate denominator, which the gate refuses loudly instead of publishing.
- **[The gate can refuse a legitimately tiny application]** → The comparison is against the APK's own compiled class count under the key, not an absolute floor, so a 18-class app with 18 compiled classes passes.
- **[`ReachabilityEnricher` keeps a four-argument constructor that only its tests call — a P3 violation, deliberately deferred]** → Its javadoc says it is "kept for callers that carry no provenance — the tests", and eleven test call sites use it while production uses the six-argument form. Removing it is a one-line change with a disproportionate cost: it forces a reactor rebuild, the rebuild changes the jar's sha256, and the sha256 is what anchors this change's evidence (task 1.5 pins it deliberately). That invalidates the D9 acceptance of 1.8, the invariance control of 1.9 **and** the twenty-seven-leg D2 campaign of 3.15 — three measurements, roughly three hours of machine time, none of which the edit would change. Recorded as debt for a change that rebuilds the reactor for its own reasons.
- **[`TaskResult.to_dict()` touches the resume format]** → `from_dict` is changed in the same task and a legacy-file test is required.
- **[The pipeline will deliberately hold two answers for `code_package`, by consumer]** → Recorded in INV-EXP-36 and in the ajc module documentation; the comment at `ajc_instrumentation.py:858-866` already anticipates it.
- **[After D9, `libPackages.txt` still governs three of the six published coverage denominators]** → Named as debt in the proposal with the reason stated precisely: it stops being a risk to the class denominator and remains one to `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target`. Task 8.1 publishes only `classes_total` and `methods_total`, so those three keep unpublished denominators — recorded, not repaired.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `resolveScopeKey` — parameter present → prefix stripped; `null` → manifest; empty after `=` → manifest; non-prefix → manifest | `AnalysisEntrypointTest` in the reactor's surefire, no Soot | 4 |
| Reactor regression | the two suites the old build command suppressed | `mvn clean install` **without** `-DskipTests`; one `-DskipITs=false` pass in Group 8 | `ReachabilityEnricherTest`, `ExtractClassesFilterTest`, + 3 ITs |
| Probe (Java) | **prediction** of the guard's effect on 4 collapsed APKs + 1 control — not acceptance | `D9Probe` against the rebuilt jar | 5 runs, ~13 s each |
| Acceptance (end to end) | the repair itself: `rv-static-analysis --package-detector` on `com.github.cvzi.screenshottile_148`, `len(reachability)` 21 → 535 across the rebuild; `me.zhanghai.android.untracker_9` invariant at 330 — **not** `app.pachli_50`, whose code package matches no `libPackages.txt` pattern, so its demotion loop never runs and it is invariant under any guard whatsoever | real GATOR run against the deployed jar | 2 |
| Unit | neutralization rule; gate thresholds and the zero-universe case; discard classification incl. unclassified; `write_errors` round trip **and persistence**; parser spelling; `measured` | pytest, no I/O | ~34 |
| Unit (removal) | zero references to `SignatureNormalizer` in `modules/*/src` **and `scripts/`**; the deleted test module's 50 tests; the 5 tests that break (`test_dot_notation_normalized` + the 4 of `TestNormalizerSafetyNet`) | grep gate + suite run | 1 gate |
| Regression (existing tests this change invalidates) | 6 of the 29 in `test_pre_processor.py` (by the fixed-arity `App` stub, one also by an exact-kwargs assertion at `:190-192`), `test_resume_integration.py:675`, `test_result_processor.py:1283`, `test_summary_csv_zeros_when_no_data` | update in the same task as the behaviour change | 9 |
| Integration | policy propagation entry point → `App` → GATOR argv → artefact → parser → CSV; ajc exclusion; pre-processing aborts; monitors provenance; artefact key mismatch | pytest with real config objects | ~14 |
| Parity | the Java↔Python key sets after the new top-level members | `RV_GATOR_REQUIRED=1 uv run pytest tests/parity/` — note it **skips** rather than fails without the jar on PATH | 204 |
| Corpus witness | `com.hwloc.lstopo_80283` — 1080 dotted events match after D3 | committed trimmed fixture (task 4.6); the 99 archived logcats under `RV_ANDROID_NOVO_DATASET` stay as the manual cross-check | 1 |
| Drift | `scripts/check_env_vars_drift.py` — note its checks 2-3 require the new `ENV_*` constant to be documented in `README.md` **and** `.env.example`, or it reports two violations | CI | 1 |

All pytest invocations use `--import-mode=importlib -o "addopts="`, per the CI contract, which lives in the parent repo at `rvsec/.github/workflows/ci.yml`.

**Starting line.** Measured 29/08 with that invocation: `tests/parity/` 204 passed and all 16 modules green. Five failures that existed before this change (two `rv-static-analysis` baseline-ledger failures from `2a0f5280`, three in `tests/parity/`) were repaired on 29/08, so any red during implementation belongs to this change. One of them is a standing hazard rather than history: `test_baseline_not_older_than_jar` compares baseline and jar mtimes, and task 1.5 rebuilds the jar — Group 1 regenerates the baseline after the rebuild or the tripwire fires by construction.

## Open Questions

None outstanding. The three that stood in the previous revision are settled:

- **Where the effective key is recorded in the artefact** — settled: `ReachabilityEnricher.topLevelMetadata()` is wired into `JsonReportWriter`, and it carries `manifestPackage`, `codePackage`, its origin and `class_defs_under_key`. Two gates move with it in the same commit: `ReachabilityEnricherTest::topLevelMetadataReturnsExactlyThreeKeys` pins the method to exactly three keys, and `tests/parity/test_json_keys.py` compares `JsonSchema.Keys` against the `_JK` mirror at `static_analysis_parser.py:79`, which today has no `codePackage` entry. `JsonReportWriterPurityTest` does not object — it forbids a `ReachabilityIndex` field on the writer, which is precisely why the metadata is routed through the enricher.
- **The gate's ratio threshold** — settled at **0.15**, on the ratio corrected by subtracting generated classes (D-4). Measured against all 162 rather than the 5 examined.
- **Whether INV-EXP-16 is made true by excluding or by executing** — settled by the researcher on 29/08; see D-10.
