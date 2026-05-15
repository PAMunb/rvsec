# Design: static-analysis-overhaul (gh57)

## Context

The unified GATOR static analysis (post-`gh27`, with Soot 4.7.1 + SPARK default from `gh51`) is producing empty `windows[]` arrays in **58.4% (222 / 380)** of the canonical original-APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` (ground-truth JSONs in `…/APKS_JCA_analise_estatica_soot/`). The Phase-0 investigation (`rv-android/docs/20260513_gator_analise_wtg.md`) traced this to a *two-call-graph problem*: SPARK is correctly configured and serves the reachability phase, but the WTG (Window Transition Graph) phase bypasses it via `AndroidCallGraph.v()` — an independent singleton populated by `FlowgraphRebuilder.buildCallGraph()` with CHA-style virtual dispatch over all concrete subtypes. The combinatorial cost (~O(|methods| × |stmts| × |subtypes| × |hierarchy|)) exceeds the sweep timeout on large APKs, leaving a partial JSON (with reachability but artificially-empty windows) as the final artifact.

The downstream APE-RV v3 calibration subset (190 of the 400 APKs, filtered for JCA reachability + dexlib2-instrumentability + x86 ABI) sees this more acutely at **71.6% empty (136 / 190)** because the filtering biases toward larger / harder apps. Static analysis is run **only on the original APKs** (per project memory `feedback_static_analysis_original_apks_only.md`); the instrumented `*_DEXLIB` set is a downstream artefact and never feeds back into Soot, where Dexpler can crash on monitor-injected bytecode (observed 2026-05-14: `Unrealizable cast` in `AesGcmHkdfStreaming`).

Three of the four MOP weights consumed by `aperv:sata_mop` (`mop_weight_direct`, `mop_weight_activity`, `mop_weight_wtg`) require `windows[]` / `transitions[]` to operate. Without this fix, the APE-RV v3 calibration must fall back to the *two-score* objective mitigation (`rvsec-calibracao/docs/20260513_analise_gator_window.md` §6.2) and lose representativeness from 136 of the 190 instrumented APKs.

A parallel audit of `RvsecAnalysisClient`'s widget-extraction coverage (Phase-0 §12) identified five widget-level features absent from the current output that `aperv:sata_mop` consumes. The two structurally cheapest (four extra XML attributes, programmatic options-menu extraction via Soot CFG) are mechanical additions to existing pipelines; the third (programmatic Spinner items via `ArrayAdapter` dataflow) is a feature net-new to the project, scoped to MVP for this change.

References:
- Phase-0 ideation: `rv-android/docs/20260513_gator_analise_wtg.md`
- Empirical impact: `rvsec-calibracao/docs/20260513_analise_gator_window.md`
- Calibration v2 plan: `rvsec-calibracao/docs/20260407_aperv_calibracao_v2.md`
- Related FRs: FR04 (analysis output schema), FR05 (call-graph construction), FR06 (widget extraction), FR19 (aperv tool support), NFR06 (analysis wall-clock budget).

## Architecture

The change touches three loci in two repos. The `rv-android` workspace (Python uv modules + the `rvsec` Java git submodule) owns the GATOR side; the external `ape` repository owns the consumer side.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Soot whole-program session                    │
│                                                                     │
│   APK + Spec ──▶  cg pack: -cgAlgorithm spark, all-reachable=true   │
│                       │                                             │
│                       ▼                                             │
│             Scene.v().getCallGraph()   ◀── SPARK CG                 │
│                       │                                             │
│                       ▼                                             │
│             wjtp.gui transformer                                    │
│                       │                                             │
│                       ▼                                             │
│             RvsecAnalysisClient.run(output)                         │
│             │                                                       │
│             ├── reachability (uses Scene CG + JGraphT)              │
│             │   + bytecode-scan complement (BUG-INV-ANA-19)         │
│             │                                                       │
│             ├── writeJson(wtg=null) ◀── populated windows[]  ★ NEW  │
│             │                          schemaVersion="2.0"          │
│             │                                                       │
│             ├── if (skipWtg) goto components ◀────────── ★ NEW      │
│             │                                                       │
│             └── WTGBuilder.build(output)                            │
│                       │                                             │
│                       ▼                                             │
│             FlowgraphRebuilder                                      │
│                       │                                             │
│                ┌──────┴──────┐                                      │
│                │ cgDelegation │  (feature flag)            ★ NEW   │
│                └──────┬──────┘                                      │
│                       │                                             │
│           true ──► Scene.v().getCallGraph()  + bytecode-scan        │
│                    for IGNORED_CLASSES                              │
│                       │                                             │
│           false ──► AndroidCallGraph.v() (legacy CHA-style)         │
│                       │                                             │
│                       ▼                                             │
│             writeJson(wtg=full)  ◀── rewrites with transitions[]    │
│                                                                     │
│             MenuExtractor   ◀──────────────────── ★ NEW             │
│             SpinnerItemExtractor (MVP) ◀───────── ★ NEW             │
│             enrichFromXml(): +4 attrs ◀────────── ★ NEW             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (JSON v2.0)
              ┌──────────────────────────────────────┐
              │  StaticAnalysisParser (Python)       │  unchanged
              │  rv-static-analysis                  │
              └──────────────────────────────────────┘
                                  ▼
              ┌──────────────────────────────────────┐
              │  MopData.java (Java, in ape repo)    │  ★ MODIFIED
              │  reads schemaVersion; tolerates v1   │
              └──────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `RvsecAnalysisClient.run()` | Orchestrates 4-section JSON write; honors `cgDelegation` and `skipWtg` client params | `GUIAnalysisOutput`, client params | `analysis.json` (v2.0) |
| `RvsecAnalysisClient.writeJson()` (modified) | Emits `schemaVersion`, populated `windows[]` in both `wtg=null` and `wtg=full` paths | `output`, `wtg`, `windowNodeIds`, sets | JSON file |
| `RvsecAnalysisClient.extractWindows()` (modified) | Builds widget list from `GUIAnalysisOutput`; catch-all WTG-node loop guarded by `if (wtg != null)` | `output`, `windowNodeIds`, `wtg` (nullable) | `List<Map<String, Object>>` |
| `RvsecAnalysisClient.enrichFromXml()` (modified) | Reads `inputType`, `entries`, **new**: `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` from layout XMLs | `List<window>` | mutates in place |
| `FlowgraphRebuilder.buildCallGraph()` (modified) | When `cgDelegation=true`: queries `Scene.v().getCallGraph()` + bytecode-scan complement. When `false`: legacy CHA path | invoke sites | `AndroidCallGraph` (always populated for downstream WTG stages) |
| `MenuExtractor` (new) | Walks `onCreateOptionsMenu` CFG to extract `Menu.add` / `Menu.addSubMenu` items | activity class | `items[]` widget list |
| `SpinnerItemExtractor` (new) | Uses SPARK points-to + def-use to extract `ArrayAdapter` items from literal constructors and `add/addAll` calls | activity class | per-Spinner entries list |
| `Configs` (modified) | New fields `cgDelegation` (boolean, default true), `skipWtg` (boolean, default false) parsed from `-clientParam` | client params | populated singleton |
| `scripts/static_analysis_sweep.py` (modified) | New CLI arg `--skip-wtg` propagated as `-clientParam skipWtg=true` | command line | GATOR commands |
| `MopData.java` (modified, in `ape` repo) | Reads `schemaVersion`; tolerates absent v2 fields | `analysis.json` | parsed MOP data |
| `scripts/wtg_paridade_diff.py` (new) | Computes Jaccard index over `{(src, tgt, event)}` for paridade gate | two JSONs | report |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|-------------------------|----------------|------|
| MODIFIED `Unified Static Analysis` (windows[] populated regardless of WTG) | `RvsecAnalysisClient.writeJson()` partial path + `extractWindows()` guard | `RvsecAnalysisClientTest.testPartialJsonHasPopulatedWindows` |
| ADDED `JSON Schema Versioning` | `RvsecAnalysisClient.writeJson()` first emits `schemaVersion: "2.0"`; `MopData.java` reads with fallback | `MopDataTest.testReadsLegacyV1Json`, `RvsecAnalysisClientTest.testSchemaVersionFieldPresent` |
| ADDED `skipWtg Client Parameter` | `Configs.skipWtg`, `RvsecAnalysisClient.run` branch, `static_analysis_sweep.py` arg | `RvsecAnalysisClientTest.testSkipWtgBypassesBuilder`, `test_sweep_skip_wtg.py` |
| ADDED `Widget XML Attribute Extensions` | `RvsecAnalysisClient.enrichFromXml()` reads 4 attrs | `EnrichFromXmlTest.testFourNewAttrs` |
| ADDED `Inflated OPTIONSMENU Items via Existing GUI Flow Graph` | `RvsecAnalysisClient.extractWindows()` walks `menu.getChildren()` and calls `collectWidgets` (replace hardcoded `Collections.emptyList()`) | `RvsecAnalysisClientTest.testCryptoappOptionsMenuHasThreeItems`, integration smoke on `cryptoapp.apk` |
| ADDED `Programmatic Options-Menu Extraction` | `MenuExtractor` (new), called from `extractWindows` for OPTIONSMENU in addition to the inflated-items walk | `MenuExtractorTest.testMenuAddLiteral`, `testMenuAddStringResource`, `testSubMenuChain`, `testBodyRetrievalFailure` |
| ADDED `Programmatic Spinner Items via ArrayAdapter (MVP)` | `SpinnerItemExtractor` (new), invoked after `enrichFromXml` | `SpinnerItemExtractorTest.testLiteralConstructor`, `testAdapterAddCalls`, `testXmlAndProgrammaticCoexist`, `testNonLiteralLogged` |
| ADDED `GATOR Invocation Robustness` | `rv_static_analysis.config.get_tool_command` uses `sys.executable`; `StaticAnalyzer._run_analysis` raises `StaticAnalysisException` when output JSON is missing post-execution | `test_config.test_tool_command_generation` (asserts `cmd[0] == sys.executable`); `test_static_analysis.test_run_analysis*` (isfile mocked `[False, True]` for execute-then-validate sequence) |
| INV-ANA-20 (windows always populated) | `writeJson` invariant; assertion in tests | `testPartialJsonHasPopulatedWindows` |
| INV-ANA-21 (no second CG when `cgDelegation=true`) | `FlowgraphRebuilder.buildCallGraph` branch | `FlowgraphRebuilderTest.testCgDelegationDoesNotPopulateAndroidCallGraph` |
| INV-ANA-22 (bytecode-scan WTG complement mirrors `BUG-INV-ANA-19`) | shared helper `scanInvokesByPattern` | `FlowgraphRebuilderTest.testIgnoredClassesEdgesRecoveredViaBytecode` |
| INV-ANA-23 (`schemaVersion` is 2nd JSON field) | `writeJson` write order | `RvsecAnalysisClientTest.testSchemaVersionFieldOrder` |
| INV-ANA-24 (per-method resilience in extractors) | try/catch in `MenuExtractor` and `SpinnerItemExtractor` | `*ExtractorTest.testBodyRetrievalFailure` |
| Paridade Jaccard ≥ 0.95 | `scripts/wtg_paridade_diff.py` over 10-APK fixture | `test_wtg_paridade.py` (integration, runs against fixture) |

## Goals / Non-Goals

**Goals:**
- Eliminate the two-call-graph problem at the structural level (single SPARK CG, controlled by `cgDelegation` feature flag for safe rollback).
- Populate `windows[]` in 100% of successful runs (including WTG-timeout cases), so 3 of the 4 aperv MOP weights become operational on the full ground-truth set (380 originals). The downstream v3 calibration subset (190 instrumented APKs) picks up the new windows data automatically when re-instrumented from the refreshed JSONs.
- Add 5 widget metadata fields (4 XML attributes + programmatic menu items) at near-zero additional cost.
- Add explicit JSON schema versioning to decouple producer/consumer evolution going forward.
- Stay within ~3 weeks of effort for the MVP scope of item 5 (ArrayAdapter literal patterns only).

**Non-Goals:**
- Replacing `AndroidCallGraph` with `OnFlyCallGraphBuilder` or RTA (Phase-0 Opção D — high effort, low marginal benefit once Opção A lands).
- Re-implementing rv-agent's WTG-guided navigation (rv-agent is not an active consumer in 2026 H1).
- Fixing the `MopScorer` weighting (the score itself is unchanged; only the inputs `MopScorer` consumes are richer).
- Migrating the 158 pre-existing legacy-v1 JSONs in-place; the 380-APK ground-truth re-run on `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` is the canonical v2.0 source.
- Covering `getResources().getStringArray(R.array.X)` or Kotlin `listOf()` in `SpinnerItemExtractor` — deferred to a future change pending corpus coverage measurement.
- Modifying the sweep timeout policy (Phase-0 explicitly rejects `analise_gator_window.md` §6.3.A/B/C as obsoleted by this change).

## Decisions

### D1 — Decouple `windows[]` from WTG via partial-JSON path (Opção C)

**Choice:** Modify `RvsecAnalysisClient.writeJson()` so the `wtg == null` branch calls `extractWindows(output, Collections.emptyMap(), null)` instead of writing an empty array. Guard the catch-all `for (WTGNode node : wtg.getNodes())` loop in `extractWindows` with `if (wtg != null)`.

**Why:** Phase-0 §3.4bis verified that 100% of widget data (`getActivities`, `getDialogs`, `getOptionsMenu`, widget roots, `PropertyManager` text/hint, event handlers) is populated by GATOR's `wjtp.gui` transformer *before* `RvsecAnalysisClient.run()` is invoked. The `if (wtg != null)` gate in `writeJson` was an artificial coupling, not an algorithmic necessity.

**Alternatives considered:**
- **Opção B (`--fast-windows` XML-only path)**: parse layout XMLs directly, bypassing GATOR's interprocedural analysis. Rejected because Opção C is strictly simpler and reuses the existing `extractWindows` helper that already handles dynamic listeners correctly.
- **`--skip-wtg` only**: skipping WTG without fixing the partial-JSON path still produces `transitions: []` but with an unwarranted `windows: []`. Rejected because it misses the structural fix.

**Trade-off:** The partial path loses the "catch-all WTG-only windows" (fragments, context menus enumerated only via `wtg.getNodes()`). These already have `widgets: []` in the full path, so they are informational; their absence is documented in INV-ANA-20.

### D2 — `skipWtg` as a client parameter, not an env var or JVM property

**Choice:** New `-clientParam skipWtg=true` parsed in `RvsecAnalysisClient.run()` via `Configs.getClientParamCode("skipWtg=")`. Sweep CLI exposes `--skip-wtg` that propagates.

**Why:** Matches the existing GATOR convention (`mopDir=`, `codePackage=`, `cgDelegation=`). Enables per-APK control (a future enhancement) — env vars and JVM properties would force the whole sweep to be uniform.

### D3 — `cgDelegation` as a runtime feature flag (with default = false post-M3)

**Choice:** Refactor `FlowgraphRebuilder.buildCallGraph()` to switch on `Configs.cgDelegation`. When `true`, use `Scene.v().getCallGraph()` + bytecode-scan complement; when `false`, use the legacy CHA-style code path verbatim. **Default is `false` — the SPARK delegation path is opt-in via `-cgDelegation true` (CLI) or `--cg-delegation true` (Python sweep)**.

**Original intent (pre-M3):** default `true`, with the legacy path kept only for rollback. Item 6 is the highest-risk change in the scope (Phase-0 §7.1).

**Why the default was flipped to `false` on 2026-05-15:** the paridade M3 gate (`scripts/wtg_paridade_diff.py` against 10 baseline-OK APKs from `notes/preflight_fixtures.md(c)`) **failed** with avg Jaccard 0.543 (threshold 0.95) / min 0.000 (threshold 0.85). The failure is **categorically structured**, not random:

- 3 APKs lost **all** their `transitions[]` (Jaccard = 0.000): `com.mouzinho.pokebase` (React Native — `com.swmansion.rnscreens.*`), `com.nyx.custom_uploader` (Flutter — `io.flutter.plugins.urllauncher.*`), `com.wordtracer.app` (Capacitor — `com.getcapacitor.BridgeActivity`). In all three, the activities are surfaced with fallback IDs (100000+) by `RvsecAnalysisClient.extractWindows`, indicating the WTG did not build WTGNodes for them.
- 1 APK had a partial loss: `com.akylas.enforcedoze` (native Android) dropped from 97 → 86 transitions (Jaccard 0.887 — borderline).
- 1 APK had a *gain* (baseline timeout → candidate completed): `org.fossify.keyboard` 0 → 36 transitions, confirming the perf benefit is real.
- 1 APK was a control (`com.dewdrop623.androidcrypt`, native Android) with Jaccard 1.000.

**Root cause** (full diagnostic in `docs/20260515_diagnostico_paridade_cgdelegation.md`): hybrid-framework apps wire their UI listeners through synthetic lambdas (`$$ExternalSyntheticLambda*`) and native bridges (`com.facebook.react.bridge.*`, `io.flutter.embedding.engine.*`, `com.getcapacitor.Bridge`). SPARK's points-to does not materialize edges for these dispatch patterns. The legacy `buildCallGraphLegacy` covered them via a CHA fallback over all concrete subtypes of the receiver type (lines 1067–1083). `buildCallGraphFromSparkCg` has only an `IGNORED_CLASSES` recovery scoped to `java.*/android.*/etc.` — application-package lambdas like `com.swmansion.…$$ExternalSyntheticLambda0` are structurally outside that scope.

Without WTGNodes for the entry activities, **all** transitions referencing them (including implicit `_home_/_power_/_rotate_event`) are dropped — so the regression amplifies: losing one set of edges loses the WTG nodes those edges anchor, which loses every transition out of those nodes. The 3 zero-Jaccard outcomes are a direct consequence.

**Performance vs paridade trade-off observed:**
- Performance gain (when paridade holds): 2.8× to 23× on apps that completed in baseline; 4 of the 10 APKs recovered from a 600s timeout to under 200s in candidate.
- Paridade cost (where it fails): full transitions loss in framework-hybrid apps.

We chose paridade over performance because the `windows[]` decoupling (G2) and `--skip-wtg` (G2) **already** solved the operational problem the cgDelegation was meant to solve secondarily (71.6% empty `windows[]` rate in experimento-20260508). The remaining benefit of cgDelegation is recovering `transitions[]` for those same APKs — a strictly weaker need than the windows fix, and one we cannot ship at the cost of silently dropping transitions for an entire app category.

**Follow-up change to land in a future cycle** (`gh<N>-cg-delegation-framework-edges`, scope sketched in §5.2 of the diagnostic): port the legacy CHA fallback into `buildCallGraphFromSparkCg` scoped to application classes when SPARK returns zero edges. If the re-run paridade gate meets thresholds, that follow-up flips the default back to `true`.

**Alternatives considered (at decision time):**
- **Build-time toggle**: rejected because rollback requires rebuild and JAR redistribution. The runtime flag enabled this very pivot without a JAR change.
- **No flag (commit to SPARK delegation only)**: rejected because the paridade gate needed an in-place baseline — and indeed the gate is what surfaced the regression.
- **Default `true` with documented regression**: rejected — would silently degrade calibration v3 for hybrid-framework APKs without consumer notice. Violates the paridade contract documented in `cgDelegation Default Behavior` requirement.
- **Drop the legacy path now, ship SPARK-only**: rejected — would preclude the rollback that we then needed within hours.

### D4 — Bytecode-scan complement at the WTG level (INV-ANA-22)

**Choice:** Extend the existing `BUG-INV-ANA-19` bytecode-scan helper into a generic `scanInvokesByPattern(Set<SootClass> appClasses, Predicate<MethodRef> matches) -> Set<Edge>` that returns call-graph edges rather than only direct-MOP-callers. Use it inside `FlowgraphRebuilder.buildCallGraph()` for invoke sites whose callee class is in SPARK's `IGNORED_CLASSES`.

**Why:** Mirrors the proven gh51-D6 pattern at a different granularity. Preserves edges to library classes that SPARK quarantines, which are semantically relevant for some WTG transitions (e.g. dialogs returned by `AlertDialog.Builder`).

**Risk:** The bytecode scan over every invoke site (vs only MOP-targeted invokes in BUG-INV-ANA-19) is more expensive. Mitigation: cache per-method body retrieval, reuse across MOP and WTG scans within one `run()` invocation.

### D5 — `MenuExtractor` and `SpinnerItemExtractor` as new top-level classes, not methods on `RvsecAnalysisClient`

**Choice:** Two new files: `presto/android/gui/clients/MenuExtractor.java` and `presto/android/gui/clients/SpinnerItemExtractor.java`. Each receives `GUIAnalysisOutput output` + `PropertyManager` and returns a per-activity / per-Spinner result.

**Why:** P1 (simplicity) + testability. `RvsecAnalysisClient.run()` is already long; adding ~200 lines of Soot CFG walking inside it would harm readability. Separate classes enable focused unit tests with minimal Soot bootstrap fixtures.

### D7 — Inflated OPTIONSMENU items: reuse existing flow graph, do not re-parse menu XML

**Choice:** In `RvsecAnalysisClient.extractWindows()`, replace the hardcoded `widgets: Collections.emptyList()` for OPTIONSMENU windows (line ~729) with a `collectWidgets(output, child, widgets, visited)` walk over `menu.getChildren()` — identical in shape to the DIALOG block on lines 700–715.

**Why:** `FixpointSolver.doMenuInflate()` (sootandroid `FixpointSolver.java:1004`) already does the heavy lifting — it parses `res/menu/<name>.xml` via `getRootForLayoutId(menuId)`, builds an `NMenuItemInflNode` for every `<item>`, sets `idNode` (line 1044), `text` via `addTextNode` (line 1056), `hint` via `addHintNode` (line 1064), and attaches each item to the `NOptionsMenuNode` parent via `vNode.addParent(parent)` (line 1068). The `NNode.addParent` contract (`NNode.java:167`) reciprocates: `p.children.add(this)`. So `menu.getChildren()` returns the inflated menu items with all metadata already filled in. The fix is to *stop discarding* this data — not to re-parse anything.

This is the simplest possible fix (5 lines, mirrors an existing pattern, zero new APIs). It is orthogonal to D5 (`MenuExtractor`): D5 handles activities that construct the menu programmatically in `onCreateOptionsMenu`; D7 handles the inflated-XML case. The two paths produce items in the same `widgets[]` array; the id spaces are disjoint by construction (XML items carry `R.id.*` constants from the menu resource; programmatic items carry the literal int passed to `Menu.add(...)`).

**Alternative considered:** parse the menu XML directly in `RvsecAnalysisClient` (analogous to `enrichFromXml` for layouts). Rejected because it would duplicate `doMenuInflate`'s work, would not benefit from `FixpointSolver`'s string-resource and id resolution, and would not see programmatic menus at all.

**Discovery context:** this gap was identified during the gh57 cryptoapp smoke (2026-05-14). The smoke produced `windows[type="OPTIONSMENU"].widgets: []` for an activity whose menu is XML-inflated with 3 items in `res/menu/cryptoapp_menu.xml`. Tracing back through `FixpointSolver.processMenuInflaterCalls` → `doMenuInflate` → `NMenuItemInflNode` showed the data is built in-memory and then thrown away by the JSON serializer.

### D6 — Schema version field as a string `"2.0"` at the second JSON position

**Choice:** Emit `"schemaVersion": "2.0"` immediately after `"package"` in `writeJson()`. The `MopData.java` parser reads the field and, when absent or `"1.0"`, treats all v2.0 fields as `null` / empty.

**Why:** P3 (no backward compatibility in producer) — `RvsecAnalysisClient` only emits v2.0 going forward. The consumer must tolerate legacy v1 JSONs because the 158 pre-existing populated files in `…/APKS_JCA_analise_estatica_soot/` are not migrated in-place; they are simply re-generated during the closing 380-APK ground-truth re-run.

**Alternative considered:** semver `"2.0.0"`. Rejected because two digits are sufficient and easier to grep / version-bump.

### D8 — Codex pre-sweep correctness fixes land inside gh57 (not deferred)

**Choice:** Four small targeted defects flagged by an independent code review on 2026-05-15 — isolated entry-point seeds (#1), `@+id/` XML matcher (#5), `MenuExtractor` resource-id resolver (#6), `SpinnerItemExtractor` CastExpr unwrap (#7) — are folded into gh57 as Group 8 (executed before the Group 9 acceptance sweep). Each fix is < 10 lines of code, ortogonal to the other gh57 mechanics, and has measurable downstream impact on either `reachable[]` (defect #1) or `widgets[]` completeness (defects #5–#7).

**Why:**
- **Acceptance signal integrity.** The Group 9 sweep produces the closing numbers that the calibration v2/v3 of APE-RV builds on. If we defer these fixes, the sweep measures a pipeline we already know has known correctness gaps and the resulting `windows[]≥95%` / aperv-smoke numbers are conservative. Landing the fixes first means the sweep validates the corrected pipeline.
- **Cost is negligible.** Each fix is < 10 lines + a focused unit test; the four together add roughly one afternoon to gh57. The alternative — opening four separate one-line changes — costs more on overhead alone (proposal/design/tasks/specs/archive ceremony × 4) than just folding them in here.
- **No risk of scope creep.** These are *defect-class* fixes, not refactors. None touch the architectural questions raised by codex (RvsecAnalysisClient splitting, window-id identity refactor, XML ownership inference) — those are out of scope and explicitly slated for a follow-up `gh<N>-rvsec-client-refactor`.
- **Ortogonal to the in-flight paridade gate (M3).** Each fix lives in a different code path from `FlowgraphRebuilder.buildCallGraphFromSparkCg`, so the paridade gate verdict and the codex fixes can be implemented and committed independently. The paridade gate (Group 6.9) does not need to be re-run after the codex fixes because none of them changes WTG transition semantics.

**Alternatives considered:**
- *Defer all four to a follow-up change*: rejected because it would mean the closing 380-APK sweep measures a known-incorrect pipeline, and re-doing the sweep after the follow-up change has a 3–4h wall-clock cost.
- *Defer only #1 and #6 (the moderate-cost ones), land only #5 and #7 inside gh57*: rejected because #1 directly affects the `reachable[]` denominator that Group 9.3 evaluates, and shipping a sweep where reachable[] under-reports for isolated callbacks would mislead consumers of the JSON.
- *Land the codex fixes as a separate Group 8 with its own architectural justification*: chosen and reflected in `tasks.md` Group 8 + spec.md sub-requirements. The "Group 8 — Codex Pre-Sweep Fixes" header makes the boundary explicit; reviewers can audit defect-fix-only vs. architectural-refactor-out-of-scope at a glance.

**Out-of-scope (deferred to follow-up change):**
- Architectural decomposition of `RvsecAnalysisClient` into `EntryPointResolver` / `ReachabilityAnalyzer` / `WindowModelExtractor` / `ResourceIndex` / `JsonResultWriter` (codex review §Sugestões #1).
- Window-id identity refactor (codex review §Achados #3) — uses class names as keys today, which can collide for multiple windows of the same class; fix requires a typed `WindowIdMapping` DTO.
- XML ownership inference per activity (codex review §Achados #4) — fix requires walking `setContentView(R.layout.X)` in the activity's CFG to identify the owning layout file rather than indexing all layouts globally.
- JSON proveniência fields (`reachableBy=["cg","callback","bytecodeScan"]`, `xmlEnriched`, etc., codex review §Sugestões #6) — high ROI but a new public-schema addition (would force a `schemaVersion` bump to 2.1 and a parallel `MopData.java` update); appropriate for a focused follow-up change rather than slipped into gh57.

## API Design

### `Configs` (new fields)

```java
public final class Configs {
    // existing fields ...

    /** Default: true. When true, FlowgraphRebuilder.buildCallGraph() delegates virtual dispatch
     *  to Scene.v().getCallGraph() (SPARK) and uses bytecode-scan for IGNORED_CLASSES libs.
     *  When false, the legacy CHA-style local rebuild is used (rollback path). */
    public static boolean cgDelegation = true;

    /** Default: false. When true, RvsecAnalysisClient.run() skips WTGBuilder.build()
     *  entirely; transitions[] is emitted as []. */
    public static boolean skipWtg = false;
}
```

Both fields are populated from `-clientParam <name>=<value>` parsing in `Main.java`, identical to the existing `mopDir=` / `codePackage=` pattern.

### `RvsecAnalysisClient.writeJson()` (modified signature unchanged)

```java
private void writeJson(
    String outputPath,
    String appPackage,
    SootClass mainActivity,
    Map<SootClass, List<SootMethod>> appClasses,
    GUIAnalysisOutput output,
    Set<SootMethod> reachableSet,
    Set<SootMethod> reachesMopSet,
    Set<SootMethod> directMopSet,
    WTG wtg,                                    // nullable
    Map<String, Integer> windowNodeIds          // empty when wtg == null
);
```

Preconditions:
- `output` is non-null and has had `wjtp.gui` transformer applied.
- When `wtg != null`, `windowNodeIds` MUST be the result of iterating `wtg.getNodes()`.

Postconditions:
- File at `outputPath` exists and is parseable JSON.
- Root object's second field is `"schemaVersion": "2.0"`.
- `windows[]` is populated regardless of `wtg`'s nullity.
- `transitions[]` is `[]` when `wtg == null`, else the full transition set.

### `MenuExtractor` (new)

```java
public final class MenuExtractor {
    public MenuExtractor(GUIAnalysisOutput output, PropertyManager propertyManager);

    /** Walks the CFG of `activity.onCreateOptionsMenu(Menu)` to extract programmatic menu items.
     *  Returns an empty list (not null) if onCreateOptionsMenu is absent or its body is unretrievable. */
    public List<Map<String, Object>> extractItems(SootClass activity);
}
```

The returned widget-entry list is recursive (`items[]` may contain nested widget objects for submenus).

Resilience: per-method try/catch around `retrieveActiveBody()`; WARN log on failure; empty list result, no exception propagation (INV-ANA-24).

### `SpinnerItemExtractor` (new)

```java
public final class SpinnerItemExtractor {
    public SpinnerItemExtractor(GUIAnalysisOutput output);

    /** Returns a map: widgetIdName -> list of resolved item strings, for Spinners populated via
     *  ArrayAdapter literal constructor or .add()/.addAll() calls. Items that cannot be resolved
     *  to literal strings are logged and omitted. */
    public Map<String, List<String>> extractItems(SootClass activity);
}
```

Uses `Scene.v().getPointsToAnalysis()` (SPARK) to find Spinner receivers and `ArrayAdapter` allocation sites.

### `scripts/static_analysis_sweep.py` (modified argparse)

```python
parser.add_argument(
    "--skip-wtg",
    action="store_true",
    default=False,
    help="Pass skipWtg=true to RvsecAnalysisClient. Skips WTGBuilder.build() entirely; "
         "transitions[] is empty. Windows[] is still populated.",
)
```

When `args.skip_wtg`, the per-APK GATOR invocation appends `-clientParam skipWtg=true`.

### `scripts/wtg_paridade_diff.py` (new)

```python
def wtg_jaccard(before_json: Path, after_json: Path) -> float:
    """Compute Jaccard index over the set of (source_id, target_id, event_type) tuples
    extracted from each JSON's transitions[]. Returns a float in [0.0, 1.0]."""
```

CLI: `python scripts/wtg_paridade_diff.py --baseline-dir <dir1> --candidate-dir <dir2> --threshold 0.95`. Exits 0 on PASS, 1 on FAIL.

## Data Flow

```
sweep CLI ──▶ static_analysis_sweep.py
              │
              │ (per APK)
              ▼
   gator a -p <apk> -client RvsecAnalysisClient
       -clientParam mopDir=...
       -clientParam codePackage=...
       -clientParam cgDelegation=true       (default)
       -clientParam skipWtg=false           (default)
       -cgAlgorithm spark
              │
              ▼
   Soot whole-program (CG → wjtp.gui transformer)
              │
              ▼
   RvsecAnalysisClient.run(output):
       1. reachability + bytecode-scan complement (BUG-INV-ANA-19)
       2. writeJson(wtg=null):
            { schemaVersion: "2.0",
              package: "...",
              mainActivity: "...",
              reachability: [...],
              windows: [...]   ★ populated
              transitions: [],
              components: {...} }
       3. if (skipWtg) { stop and return }
       4. WTGBuilder.build(output):
            FlowgraphRebuilder.buildCallGraph():
                if (cgDelegation) {
                    for each invoke site:
                        edges = Scene.getCallGraph().edgesOutOf(src)
                                 .filter(subSigMatch)
                        if (callee.class in IGNORED_CLASSES):
                            edges ∪= scanInvokesByPattern(...)
                } else {
                    legacy CHA-style loop  (rollback path)
                }
       5. MenuExtractor.extractItems(activity)     ★ NEW
          per OPTIONSMENU window
       6. SpinnerItemExtractor.extractItems(activity)  ★ NEW
          merged into widgets[type=Spinner].entries
       7. enrichFromXml(): inputType, entries, + 4 new attrs ★
       8. writeJson(wtg=full):
            same file, now with populated transitions[]
              │
              ▼
   analysis.json (v2.0)
              │
              ▼
   StaticAnalysisParser (Python, unchanged)  ──▶ Pydantic models
              │
              ▼
   MopData.java (Java, in ape repo) ★ MODIFIED
              │
              ▼
   aperv binary  ──▶  scoreMop, scoreActivity, scoreWtg, scoreTransitive
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| SPARK `InternalTypingException` during CG build | Soot CG phase | Process exits non-zero before `run()` is invoked | No JSON produced. Sweep records failure. Operator may retry with `-cgAlgorithm cha` |
| `RuntimeException` in `MenuExtractor.extractItems` body retrieval | per-activity `retrieveActiveBody()` | catch + WARN log + return `[]` (INV-ANA-24) | Per-activity isolation; other activities unaffected |
| `OutOfMemoryError` in `SpinnerItemExtractor` def-use walk | per-method body inspection | catch + WARN log + skip method | Per-method isolation; other methods unaffected |
| WTG construction timeout (process SIGTERMed by sweep) | external sweep watchdog | partial JSON already on disk (windows[] populated, transitions[] empty) | None needed — partial JSON is the canonical result |
| `JsonParseException` reading legacy v1.0 JSON | `MopData.java` | tolerate via `getOrDefault` on each v2 field | aperv operates on v1 data with degraded MOP weights |
| Jaccard < 0.85 on any APK in paridade gate | `scripts/wtg_paridade_diff.py` | exit 1; surface in CI/manual report | Operator sets `cgDelegation=false`, files paridade defect report |
| Concurrent CogniCrypt session during JAR rebuild | external | `flock /tmp/rvsec-gator.lock mvn package` | Manual coordination; documented in pre-flight |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| SPARK CG omits edges to `IGNORED_CLASSES` that the legacy CHA path included → `transitions[]` regression | Bytecode-scan complement (INV-ANA-22); paridade Jaccard gate (avg ≥ 0.95, no individual APK < 0.85) on 10-APK fixture; runtime feature flag for rollback |
| Jaccard per-APK < 0.85 on any single baseline-OK APK while average is still ≥ 0.95 | The gate enforces BOTH thresholds: avg ≥ 0.95 AND min ≥ 0.85. If a single APK fails the minimum, treat as paridade FAIL and either (a) extend `scanInvokesByPattern` predicate to cover the missed cases, or (b) keep `cgDelegation=false` as default (D3 feature flag enables runtime rollback without rebuild) |
| `SpinnerItemExtractor` MVP coverage is too low on real APKs (mostly Kotlin `listOf()` or `getStringArray()`) | Pre-flight corpus scan (Phase-0 §7.7); decide to ship MVP or extend to full |
| `MenuExtractor` implementation hits an unsupported Soot 4.7.1 API | Pre-flight Soot API availability check (Phase-0 §7.6 / `notes/preflight_soot_api.md`); 0 divergences confirmed — fallback adapter layer not required |
| The 158 pre-existing legacy-v1 JSONs become inconsistent with v2.0 outputs across the dataset | The 380-APK ground-truth re-run at the close of the change re-generates all of them; `MopData.java` tolerates both schemas during the transition |
| Aperv MopData reader changes ship in the `ape` repo, not `rv-android`; coordination risk | Pre-flight `scripts/check_jar_sync.sh` validates timestamps; explicit task in `tasks.md` to rebuild both JARs |
| Wall-clock improvement target (≥30% on large APKs) is aspirational | Baseline measurement is part of pre-flight (Phase-0 §7.4); if gain is <20%, the change still ships (it is justified on windows[] populated, not on speed) |

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `RvsecAnalysisClient.writeJson` partial path; `extractWindows` guard; schema field order; `Configs` parsing | JUnit 5 in `rvsec-gator/client/src/test/java`; mock `GUIAnalysisOutput` | ~12 tests |
| Unit (Java) | `MenuExtractor` 4 scenarios + resilience | JUnit with minimal Soot fixture | ~6 tests |
| Unit (Java) | `SpinnerItemExtractor` 4 scenarios + resilience | JUnit with SPARK-enabled Soot fixture | ~6 tests |
| Unit (Java) | `FlowgraphRebuilder.buildCallGraph` `cgDelegation=true/false` branches | JUnit; mock `Scene.v().getCallGraph()` | ~4 tests |
| Unit (Java, `ape` repo) | `MopData` reads v1.0 and v2.0 JSONs | JUnit on existing `MopDataTest.java` | +4 tests |
| Unit (Python) | `static_analysis_sweep.py --skip-wtg` propagation | pytest on `rv-static-analysis/tests/` | ~3 tests |
| Integration | 5-APK smoke (3 baseline-OK, 2 baseline-frozen) — partial+full JSON correctness | invoke real GATOR JAR on fixtures in `apks_examples/` | ~1 test run |
| Integration | Paridade Jaccard ≥0.95 on 10-APK fixture | `scripts/wtg_paridade_diff.py` | ~1 test run |
| Acceptance | Full re-run of 380-APK originals at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` | sweep + post-hoc check `windows[]` non-empty in ≥95% | ~1 manual run |
| Acceptance | Aperv smoke with v2.0 JSON | rv-experiment `--tools aperv:sata_mop` on 3 APKs | ~1 manual run |

## Open Questions

- **Q1 (resolved by pre-flight §7.6 / `notes/preflight_soot_api.md`):** Soot 4.7.1 provides every API the `MenuExtractor` algorithm needs (`InterfaceInvokeExpr`, `AssignStmt`, `IntConstant`, `UnitGraph.getSuccsOf`, `Value.equivTo`); 0 divergences. No adapter layer required.
- **Q2 (deferred to pre-flight §7.7):** is the corpus coverage of literal-`ArrayAdapter` patterns ≥40%? If not, extend item 5 to "full" scope (+2–3 days, includes `getResources().getStringArray()` and Kotlin `listOf()`).
- **Q3 (resolved by pre-flight §7.11):** suitable APK fixtures for items 4 and 5 were sourced from the original corpus (`app.notesr_59` for menu; `com.eanema.graph89_1200` for Spinner); no synthetic test APK needed.
- **Q4 (decided in §16.3 of Phase-0):** the `flock` against CogniCrypt is manual coordination only — no in-build enforcement. Revisit if collisions become frequent.
- **Q5 (deferred to follow-up change):** when should the `cgDelegation=false` legacy branch be deleted? Phase-0 suggests "after N weeks of stable operation". Defer to a follow-up `gh<N>-cgdelegation-cleanup` change once telemetry confirms zero rollback use.
