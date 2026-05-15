# Change Proposal: static-analysis-overhaul

GitHub Issue: #57
Schema: rv-sdd (Full SDD)
Phase-0 ideation: `rv-android/docs/20260513_gator_analise_wtg.md`

## Why

The unified static analysis (GATOR post-`gh27-unified-static-analysis`, with Soot 4.7.1 and SPARK default from `gh51-gator-soot-upgrade`) produces empty `windows[]` and `transitions[]` arrays in **58.4% of APKs (222 / 380)** when run on the canonical original-APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` (ground-truth JSONs in `…/APKS_JCA_analise_estatica_soot/`). Root cause is a *two-call-graph problem*: SPARK is correctly configured and used by reachability analysis, but the Window Transition Graph (WTG) phase bypasses it via `AndroidCallGraph.v()` — an independent singleton populated by `FlowgraphRebuilder.buildCallGraph()` with CHA-style virtual dispatch over all concrete subtypes. The combinatorial cost of this second graph causes the WTG phase to exceed the sweep timeout on the larger APKs, leaving the partial JSON (written before WTG) as the final artifact. The downstream APE-RV v3 calibration dataset (a 190-APK subset filtered by JCA reachability + dexlib2-instrumentability + x86 ABI compatibility) feels this more acutely — 71.6% (136 / 190) empty there — because the subset is biased toward the harder app size profile.

Three of the four MOP weights consumed by `aperv:sata_mop` (`mop_weight_direct`, `mop_weight_activity`, `mop_weight_wtg`) require `windows[]`/`transitions[]` to operate. The APE-RV v3 calibration cannot proceed with the default objective function (FR04) until this is fixed at the static-analysis source.

A parallel audit of the unified `RvsecAnalysisClient` against the widget-extraction needs of `aperv:sata_mop` identified five widget-level features absent from the current static-analysis output that reduce its fidelity for downstream MOP scoring.

## What Changes

Single consolidated change addressing both the structural root cause and the missing widget-extraction features:

1. **Decouple `windows[]` from WTG completion.** `RvsecAnalysisClient.writeJson()` MUST emit a populated `windows[]` section in the partial-JSON path (when `wtg == null`) using `extractWindows(output, Collections.emptyMap(), null)`. The catch-all loop over `wtg.getNodes()` is guarded by `if (wtg != null)`. All widget data (activities, dialogs, options-menu skeletons, widgets, listeners, text, hint, inputType, entries) already exists in `GUIAnalysisOutput` before WTG runs — the previous code artificially gated the section on WTG presence.
2. **New `skipWtg` client parameter** (sweep CLI `--skip-wtg` propagated as `-clientParam skipWtg=true`) that skips `WTGBuilder.build()` entirely for known-slow APKs, saving the wall-clock spent on a guaranteed timeout.
3. **Add four XML widget attributes** to `enrichFromXml()` and the widget JSON schema: `android:prompt`, `android:spinnerMode`, `android:contentDescription`, `android:tooltipText`. Parsed alongside the existing widget XML attributes.
4. **Inflated OPTIONSMENU items via existing flow graph.** `RvsecAnalysisClient.extractWindows()` currently hardcodes `widgets: Collections.emptyList()` for every OPTIONSMENU, throwing away the `NMenuItemInflNode` children that `FixpointSolver.doMenuInflate()` already built from the menu XML. Replace the hardcoded empty list with a `collectWidgets()` walk over `menu.getChildren()` — the same pattern that already works for DIALOG and ACTIVITY windows. This is a 5-line fix that recovers menu items for every APK with `MenuInflater.inflate(R.menu.<name>, menu)`.
5. **Programmatic options-menu extraction via Soot CFG**. New class `MenuExtractor` walks `onCreateOptionsMenu(Menu)`'s control-flow graph, matches `Menu.add(int,int,int,CharSequence)` / `Menu.add(int,int,int,int)` / `Menu.addSubMenu(...)` invocations, resolves arguments (group id, item id, title) via def-use chains, and populates `windows[type="OPTIONSMENU"].widgets[].items[]`. Complementary to item #4 — handles activities that build the menu in code instead of (or in addition to) inflating XML.
6. **Programmatic Spinner items via `ArrayAdapter` dataflow** (MVP scope — literal `new ArrayAdapter<>(ctx, layoutId, items)` constructors plus `adapter.add()`/`adapter.addAll()` calls; def-use resolution to `String[]` / `List<String>` literals). New class `SpinnerItemExtractor`. This is a feature net-new to the project. Out-of-scope for MVP: `getResources().getStringArray(R.array.X)` and Kotlin `listOf()` desugaring (deferred pending corpus coverage measurement).
7. **Refactor `FlowgraphRebuilder.buildCallGraph()` to delegate virtual dispatch to `Scene.v().getCallGraph()`** (the SPARK CG already built by Soot), eliminating the second graph entirely. Edges to library classes quarantined by SPARK's `IGNORED_CLASSES` are recovered via a WTG-level bytecode-scan (analogous to `BUG-INV-ANA-19` for `directlyReachesMop`). **Controlled by a runtime feature flag** `cgDelegation` (default `true`) for rollback without rebuild.
8. **Codex pre-sweep correctness fixes** (independent code review 2026-05-15, four small targeted defects landed before the 380-APK sweep so the sweep validates the corrected pipeline):
   a. **Isolated entry-point seeds in BFS** (`RvsecAnalysisClient.multiSourceBfs`): seeds without CG edges are no longer dropped silently — fixes deflated `reachable[]` for callbacks that SPARK cannot link.
   b. **`@+id/` matched in XML enrichment** (`RvsecAnalysisClient.enrichFromElement`): both `@id/` (reference) and `@+id/` (declaration) forms now feed the enrichment pass; was missing the dominant declaration form.
   c. **`MenuExtractor` resolves `R.string.*` titles**: replaces the placeholder `resId -> null` closure with a real lookup chain (R.string → `Configs.resourceLocation` strings.xml). Menus created with `Menu.add(group, id, order, R.string.foo)` now carry their actual text.
   d. **`SpinnerItemExtractor` unwraps `CastExpr`**: walks past the `(Spinner) findViewById(...)` cast pattern that breaks single-RHS resolution; restores `entries[]` for the canonical Jimple shape.

The Spinner-XML `entries[]` resolution (already present in `RvsecAnalysisClient`) is preserved unchanged. Opção D (refactor `AndroidCallGraph` to `OnFlyCallGraphBuilder`/RTA) is explicitly *not* included; Opção A (item 7 above) makes it redundant.

## Capabilities

### New Capabilities

None. This change modifies an existing capability rather than introducing a new spec domain.

### Modified Capabilities

- `analysis`: existing requirement `Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)` is modified to (a) decouple `windows[]` from WTG completion and (b) replace the secondary `AndroidCallGraph` with the SPARK CG already available in `Scene.v().getCallGraph()` (gated by a runtime feature flag). Ten new requirements are added: `skipWtg Client Parameter for WTG Bypass`, `Widget XML Attribute Extensions`, `Inflated OPTIONSMENU Items via Existing GUI Flow Graph`, `Programmatic Options-Menu Extraction via Soot CFG`, `Programmatic Spinner Items via ArrayAdapter Dataflow (MVP)`, `Reachability BFS Handles Isolated Entry-Point Seeds`, `XML Enrichment Recognizes Both @id/ and @+id/ Prefixes`, `MenuExtractor Resolves R.string.* Titles`, `SpinnerItemExtractor Unwraps Cast Expressions for findViewById`, and `GATOR Invocation Robustness` (`sys.executable` interpreter resolution + defensive output-file post-condition in `StaticAnalyzer._run_analysis`).

The `tools` domain is not modified at the requirement level. Downstream Java consumer `MopData.java` (in the external `ape` codebase) will need to read the four new widget attribute fields (`prompt`, `spinnerMode`, `contentDescription`, `tooltipText`); the update lives in the external repo and is handled separately post-archive (owner decision 2026-05-15).

## Impact

**Modules touched directly:**
- `rvsec-gator` (Java, external — under `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator/`): `RvsecAnalysisClient.java`, `FlowgraphRebuilder.java`, new `MenuExtractor.java`, new `SpinnerItemExtractor.java`, `Configs.java` (new `cgDelegation` and `skipWtg` client params).
- `rv-static-analysis` (Python uv module): `scripts/static_analysis_sweep.py` gains `--skip-wtg` argument; `analyzer.py` propagates as `-clientParam skipWtg=`.
- `ape` (Java, external — under `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape/`): `MopData.java` needs to read the four new widget attribute fields (`prompt`, `spinnerMode`, `contentDescription`, `tooltipText`) and the populated OPTIONSMENU widgets. Update **deferred out of scope of gh57** — owner-handled in a separate cycle post-archive (2026-05-15 decision).

**Modules not touched (verified in Phase-0):** rv-experiment, rv-platform, rv-agent (currently inactive consumer), rv-coverage, MopScorer.java (degrades gracefully via existing `hasWtgData()` guard).

**FRs / NFRs referenced (from docs/PRD.md):**
- FR04 (static analysis output schema) — modified (four widget attribute fields added; populated OPTIONSMENU items; programmatic menu/spinner extractors).
- FR05 (call-graph construction) — modified (single SPARK CG).
- FR06 (widget extraction completeness) — modified (new fields + programmatic menu/spinner).
- FR19 (external tool support — aperv) — touched (`MopData.java` consumer in `ape` repo will need to read the new widget fields; update deferred out of scope).
- NFR06 (wall-clock budget for analysis) — improved (target ≥30% reduction on large APKs, baseline measured in pre-flight).

**Cross-module dependencies:**
- The GATOR JAR (`rvsec-analysis-client.jar`) and `ape-rv.jar` MUST be rebuilt synchronously before the 380-APK ground-truth re-run on the original APK corpus. A pre-flight script (`scripts/check_jar_sync.sh`) verifies timestamps. Static analysis is run **only on the original APKs** (`/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/`) — never on the instrumented `*_DEXLIB` / `*_AJC` sets, where Soot's Dexpler can crash on monitor-injected bytecode (project memory `feedback_static_analysis_original_apks_only.md`).
- Concurrent CogniCrypt sessions MUST be paused or build-locked (`flock /tmp/rvsec-gator.lock`) during the rebuild window.

**Calibration impact:** after this change, fresh ground-truth JSONs (on the 380 originals) flow into the v3 calibration's 190-APK instrumented subset; the default objective `0.5 × mop_coverage + 0.5 × method_coverage` (calibration v2 §3.8) recovers usable widget data on the full 190 (not the current 54), making the `two-score` mitigation (calibration v3 spec §6.2) and the timeout/CHA-fallback workarounds (analise_gator_window §6.3) obsolete. See Phase-0 §15 for the verification matrix.

**Wall-clock estimate:** ~3 weeks for MVP (item 5 scope-locked to literal constructors). Item 6 may be reverted via feature flag without rebuild if the WTG-paridade gate (Jaccard ≥ 0.95 over `{(src, tgt, event)}` tuples) fails.
