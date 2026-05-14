# Change Proposal: static-analysis-overhaul

GitHub Issue: #57
Schema: rv-sdd (Full SDD)
Phase-0 ideation: `rv-android/docs/20260513_gator_analise_wtg.md`

## Why

The unified static analysis (GATOR post-`gh27-unified-static-analysis`, with Soot 4.7.1 and SPARK default from `gh51-gator-soot-upgrade`) produces empty `windows[]` and `transitions[]` arrays in **71.6% of APKs (136/190)** of the canonical dataset `APKS_FINAL_JCA_DEXLIB`. Root cause is a *two-call-graph problem*: SPARK is correctly configured and used by reachability analysis, but the Window Transition Graph (WTG) phase bypasses it via `AndroidCallGraph.v()` — an independent singleton populated by `FlowgraphRebuilder.buildCallGraph()` with CHA-style virtual dispatch over all concrete subtypes. The combinatorial cost of this second graph causes the WTG phase to exceed the sweep timeout in most APKs, leaving the partial JSON (written before WTG) as the final artifact.

Three of the four MOP weights consumed by `aperv:sata_mop` (`mop_weight_direct`, `mop_weight_activity`, `mop_weight_wtg`) require `windows[]`/`transitions[]` to operate. The APE-RV v3 calibration cannot proceed with the default objective function (FR04) on 71.6% of the corpus until this is fixed.

A parallel audit of the legacy `rvsec-gesda` tool against the unified `RvsecAnalysisClient` identified five widget-level features lost during the gh27 unification that further reduce static-analysis fidelity for `aperv:sata_mop`.

## What Changes

Single consolidated change addressing both the structural root cause and the inherited GESDA gaps:

1. **Decouple `windows[]` from WTG completion.** `RvsecAnalysisClient.writeJson()` MUST emit a populated `windows[]` section in the partial-JSON path (when `wtg == null`) using `extractWindows(output, Collections.emptyMap(), null)`. The catch-all loop over `wtg.getNodes()` is guarded by `if (wtg != null)`. All widget data (activities, dialogs, options-menu skeletons, widgets, listeners, text, hint, inputType, entries) already exists in `GUIAnalysisOutput` before WTG runs — the previous code artificially gated the section on WTG presence.
2. **New `skipWtg` client parameter** (sweep CLI `--skip-wtg` propagated as `-clientParam skipWtg=true`) that skips `WTGBuilder.build()` entirely for known-slow APKs, saving the wall-clock spent on a guaranteed timeout.
3. **Port four XML widget attributes from GESDA**: `android:prompt`, `android:spinnerMode`, `android:contentDescription`, `android:tooltipText` extracted in `enrichFromXml()` and added to the widget JSON schema.
4. **Port programmatic options-menu extraction from GESDA**. New class `MenuExtractor` traces `Menu.add(int,int,int,CharSequence)` / `Menu.addSubMenu(int,int,int,CharSequence)` invocations via Soot CFG walking, resolves string references, and populates `windows[type="OPTIONSMENU"].widgets[].items[]`. Direct port of `SootAnalyze.java:372-531` from `rvsec-gesda`.
5. **New: programmatic Spinner items via `ArrayAdapter` dataflow** (MVP scope — literal `new ArrayAdapter<>(ctx, layoutId, items)` constructors plus `adapter.add()`/`adapter.addAll()` calls; def-use resolution to `String[]` / `List<String>` literals). New class `SpinnerItemExtractor`. This is a feature net-new to the project (GESDA did not implement it). Out-of-scope for MVP: `getResources().getStringArray(R.array.X)` and Kotlin `listOf()` desugaring (deferred pending corpus coverage measurement).
6. **Refactor `FlowgraphRebuilder.buildCallGraph()` to delegate virtual dispatch to `Scene.v().getCallGraph()`** (the SPARK CG already built by Soot), eliminating the second graph entirely. Edges to library classes quarantined by SPARK's `IGNORED_CLASSES` are recovered via a WTG-level bytecode-scan (analogous to `BUG-INV-ANA-19` for `directlyReachesMop`). **Controlled by a runtime feature flag** `cgDelegation` (default `true`) for rollback without rebuild.
7. **Schema version bump `1.0 → 2.0`**: add explicit `schemaVersion` field at the JSON root, document the new widget fields, document the recursive `items[]` for OPTIONSMENU. Update `MopData.java` in `ape` to read both schemas (`null` defaults for missing v2.0 fields).
8. **BREAKING (downstream signal only)**: the JSON schema produced by `RvsecAnalysisClient` is no longer compatible with pre-`schemaVersion` aperv builds. Aperv `MopData.java` is updated in lockstep; rv-agent and other consumers are not currently active (see `Phase-0 §3.4`).

The Spinner-XML `entries[]` resolution (already present in both GESDA and unified) is preserved unchanged. Item #4 (Opção D — refactor `AndroidCallGraph` to `OnFlyCallGraphBuilder`/RTA) is explicitly *not* included; Opção A (item 6 above) makes it redundant.

## Capabilities

### New Capabilities

None. This change modifies an existing capability rather than introducing a new spec domain.

### Modified Capabilities

- `analysis`: existing requirement `Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)` is modified to (a) decouple `windows[]` from WTG completion and (b) replace the secondary `AndroidCallGraph` with the SPARK CG already available in `Scene.v().getCallGraph()` (gated by a runtime feature flag). Five new requirements are added: `JSON Schema Versioning` (introduces the `schemaVersion` field at the JSON root and the `MopData.java` consumer-side reader tolerance — FR04 + FR19), `skipWtg Client Parameter for WTG Bypass`, `Widget XML Attribute Parity with GESDA`, `Programmatic Options-Menu Extraction via Soot CFG`, and `Programmatic Spinner Items via ArrayAdapter Dataflow (MVP)`.

The `tools` domain is not modified at the requirement level. The change to `MopData.java` lives in the external `ape` codebase (Java) and only updates how the existing aperv binary parses the JSON; no Python-level tool capability requirement changes. FR19 is referenced in the `JSON Schema Versioning` requirement because that requirement bounds the producer/consumer contract for the aperv reader.

## Impact

**Modules touched directly:**
- `rvsec-gator` (Java, external — under `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-gator/`): `RvsecAnalysisClient.java`, `FlowgraphRebuilder.java`, new `MenuExtractor.java`, new `SpinnerItemExtractor.java`, `Configs.java` (new `cgDelegation` and `skipWtg` client params).
- `rv-static-analysis` (Python uv module): `scripts/static_analysis_sweep.py` gains `--skip-wtg` argument; `analyzer.py` propagates as `-clientParam skipWtg=`.
- `ape` (Java, external — under `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape/`): `MopData.java` reads `schemaVersion` and the five new widget fields.

**Modules not touched (verified in Phase-0):** rv-experiment, rv-platform, rv-agent (currently inactive consumer), rv-coverage, MopScorer.java (degrades gracefully via existing `hasWtgData()` guard).

**FRs / NFRs referenced (from docs/PRD.md):**
- FR04 (static analysis output schema) — modified (schema bump).
- FR05 (call-graph construction) — modified (single SPARK CG).
- FR06 (widget extraction completeness) — modified (new fields + programmatic menu/spinner).
- FR19 (external tool support — aperv) — modified (schema reader).
- NFR06 (wall-clock budget for analysis) — improved (target ≥30% reduction on large APKs, baseline measured in pre-flight).

**Cross-module dependencies:**
- The GATOR JAR (`rvsec-analysis-client.jar`) and `ape-rv.jar` MUST be rebuilt synchronously before the 190-APK re-run. A pre-flight script (`scripts/check_jar_sync.sh`) verifies timestamps.
- Concurrent CogniCrypt sessions MUST be paused or build-locked (`flock /tmp/rvsec-gator.lock`) during the rebuild window.

**Calibration impact:** after this change, the default objective `0.5 × mop_coverage + 0.5 × method_coverage` (calibration v2 §3.8) operates on 190/190 APKs (not 54/190), making the `two-score` mitigation (calibration v3 spec §6.2) and the timeout/CHA-fallback workarounds (analise_gator_window §6.3) obsolete. See Phase-0 §15 for the verification matrix.

**Wall-clock estimate:** ~3 weeks for MVP (item 5 scope-locked to literal constructors). Item 6 may be reverted via feature flag without rebuild if the WTG-paridade gate (Jaccard ≥ 0.95 over `{(src, tgt, event)}` tuples) fails.
