# Delta Spec: analysis (gh57-static-analysis-overhaul)

## Purpose

This delta updates the `analysis` capability to (1) eliminate the structural *two-call-graph* problem that causes `windows[]` to be empty in **58.4% of the canonical original-APK corpus** (222 / 380 JSONs at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA_analise_estatica_soot/`, derived from the 400-APK `JOAO/APKs/` originals) and in 71.6% of the v3 calibration's 190-APK instrumented subset, (2) add widget-level extraction features that are absent from the current unified `RvsecAnalysisClient` output (four XML widget attributes, programmatic options-menu items, and programmatic Spinner items via `ArrayAdapter` dataflow), and (3) introduce an explicit `schemaVersion` field on the JSON output to enable forward-compatible consumer evolution.

The root-cause diagnosis is documented in `rv-android/docs/20260513_gator_analise_wtg.md` (Phase-0 ideation). The empirical impact analysis is in `rvsec-calibracao/docs/20260513_analise_gator_window.md`. Both are authoritative inputs to this change and their architectural conclusions are not re-litigated here.

The delta operates entirely within the existing `analysis` capability — no new domain is introduced. The modification of the existing `Unified Static Analysis` requirement is intentionally surgical: it touches only the two execution steps that change (windows population path and WTG call-graph source). Four orthogonal new requirements are added (`skipWtg` parameter, widget XML attribute parity, programmatic options-menu extraction, programmatic Spinner items). One new top-level requirement governs JSON schema versioning.

## Data Contracts

### Input
- `apk_path: Path` — absolute path to the original APK (DEX-instrumented or not) passed to GATOR via `gator a -p <apk_path>`.
- `mop_dir: Path` — directory of `.mop` specification files, passed via `-clientParam mopDir=<path>`.
- `code_package: str | None` — application package prefix, passed via `-clientParam codePackage=<pkg>`.
- `cg_algorithm: str` — `spark` (default), `cha`, `rta`, or `vta`, passed via `-cgAlgorithm <algo>`.
- `cg_delegation: bool` — new (default `true`), passed via `-clientParam cgDelegation=<bool>`. When `true`, `FlowgraphRebuilder.buildCallGraph()` consults `Scene.v().getCallGraph()` and skips the local CHA-style rebuild. When `false`, legacy behavior is preserved.
- `skip_wtg: bool` — new (default `false`), passed via `-clientParam skipWtg=<bool>`. When `true`, `WTGBuilder.build()` is not invoked and `transitions[]` is emitted as an empty array.

### Output
- `analysis.json` — the unified JSON file containing `schemaVersion`, `package`, `mainActivity`, `reachability[]`, `windows[]`, `transitions[]`, and `components`. Consumed by `StaticAnalysisParser` (Python) and by `MopData.java` (Java, in the external `ape` codebase).

### Side-Effects
- **Soot Scene state**: SPARK CG is built once during the `cg` pack (whole-program) phase; `FlowgraphRebuilder` no longer mutates a second `AndroidCallGraph` singleton when `cgDelegation=true`.
- **Filesystem**: `analysis.json` is written once via `writeJson(..., wtg=null)` immediately after the reachability section is finalized, then rewritten via `writeJson(..., wtg=wtg)` after WTG completion. Both writes contain a populated `windows[]` section.

### Error
- `StaticAnalysisException` — raised by the Python wrapper when GATOR exits non-zero (e.g. SPARK CG crash before `RvsecAnalysisClient.run()` is invoked).
- WTG-construction exceptions are caught in `RvsecAnalysisClient.run()` and logged; the existing partial JSON (with reachability + windows populated) remains the final artifact.

## Invariants

- **INV-ANA-20**: `windows[]` MUST be populated in every successful run of `RvsecAnalysisClient.run()` regardless of WTG completion status. The partial-JSON path (`wtg == null`) MUST emit identical widget data to the full-JSON path, differing only in: (a) catch-all WTG-only window entries (fragments, context menus discovered via `wtg.getNodes()` iteration) are absent, and (b) numeric window IDs use the `fallbackId` sequence instead of `windowNodeIds.get(...)`.
- **INV-ANA-21**: When `cgDelegation=true`, `AndroidCallGraph.v()` MUST NOT be populated by `FlowgraphRebuilder.buildCallGraph()` — virtual-dispatch resolution MUST come exclusively from `Scene.v().getCallGraph()` queries plus a bytecode-scan complement for `IGNORED_CLASSES` library targets. The two-call-graph problem is structurally absent.
- **INV-ANA-22**: The bytecode-scan WTG complement MUST mirror the policy of `BUG-INV-ANA-19` (existing complement for `directlyReachesMop`): same `IGNORED_CLASSES` set, same FQN+method-name match policy, same body-retrieval resilience pattern (catch `RuntimeException`/`OutOfMemoryError`, log, continue).
- **INV-ANA-23**: The output JSON MUST include a top-level `schemaVersion` string field as the second field (immediately after `package`). The value MUST be `"2.0"` for any JSON produced by `RvsecAnalysisClient` after this change. Legacy JSONs (without `schemaVersion` or with `"1.0"`) MUST be readable by `MopData.java` with safe defaults (missing v2.0 fields treated as `null`/empty).
- **INV-ANA-24**: `MenuExtractor` and `SpinnerItemExtractor` MUST be resilient to body-retrieval failures (same pattern as INV-ANA-17): catch per-method exceptions, log, continue. A single corrupt class MUST NOT abort the extraction.

## MODIFIED Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing five sections written in priority order: (0) **`schemaVersion` field at the root** (string, value `"2.0"`), (1) method reachability relative to MOP specifications (coverage denominator), (2) **window and widget inventory with event listeners, populated regardless of WTG completion status**, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and MOP reachability.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. GATOR initializes Soot once with defensive configuration (INV-ANA-16), builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the client writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file. **The partial-write path (`wtg == null`) MUST emit a populated `windows[]` section using the same `extractWindows` helper as the full-write path, supplying `Collections.emptyMap()` for `windowNodeIds` and `null` for the WTG handle (INV-ANA-20). The catch-all loop over `wtg.getNodes()` (which adds fragment/context-menu windows not enumerated by `output.getActivities()`/`getDialogs()`/`getOptionsMenu()`) is guarded by `if (wtg != null)`; its absence in the partial path is the only widget-data difference between the two paths.**

The `Flowgraph.processApplicationClasses()` method MUST handle individual method failures gracefully (INV-ANA-17). When `retrieveActiveBody()` or `createOpNode()` throws an exception for a specific method, the Flowgraph MUST skip that method and continue processing remaining methods. The resulting Flowgraph may be incomplete (missing OpNodes, widgets, or listeners for skipped methods), but the GUIAnalysis pipeline MUST complete and the `RvsecAnalysisClient` MUST produce JSON output. Reachability data (computed from `Scene.v().getCallGraph()` via BFS) is NOT affected by Flowgraph incompleteness — it depends on the Soot call graph, not on the Flowgraph.

The GATOR MUST use Soot 4.7.1 (`org.soot-oss:soot`, INV-ANA-18) with defensive configuration (INV-ANA-16). The `ClassHierarchy.typeNode()` bug (soot-oss/soot#1071) is not fixed in Soot 4.7.1, but the improved Dexpler in 4.x reduces crash frequency. The defensive options (excluding `kotlin.*`, `kotlinx.*`, and `androidx.compose.*` from body loading, disabling `jb.sils`/`jb.dae`) further reduce the crash surface. Together, these changes form a layered defense: prevention (FIX 1), recovery (FIX 2), and fundamental improvement (FIX 3).

The execution order inside `run()`:

1. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). Service, Receiver, and Provider class names are resolved to `SootClass` via `Scene.v().getSootClassUnsafe()`, which returns `null` for unresolvable classes (logged as WARNING, skipped). Lifecycle methods are found by iterating `SootClass.getMethods()` and filtering by name. For each application method, it computes: `reachable` (reachable from entry points), `reachesMop` (has path to a monitored API method), and `directlyReachesMop` (directly invokes a monitored API method, computed as the union of `findDirectMopCallers` and `findDirectMopCallersByBytecodeScan`). MOP method signatures are loaded from `.mop` specification files via `JavamopFacade`. This section is written and flushed first.

2. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `getDialogs()`, `getDialogRoots()`, `getOptionsMenu()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners discovered through interprocedural data flow. **Widget XML attributes — `inputType`, `entries` (from `android:entries="@array/X"`), and the four new attributes `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` — are extracted by `enrichFromXml()` from the decoded layout XML files at `Configs.resourceLocation`.** **The `windows[]` section is written in both the partial-JSON path (after reachability, with `wtg=null`) and the full-JSON path (after WTG completion, with the WTG handle for numeric ID assignment and catch-all enumeration).**

3. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures. **WTG construction MUST use `Scene.v().getCallGraph()` (the SPARK CG already built by Soot) as the single source of virtual-dispatch resolution when the `cgDelegation` client parameter is `true` (default); `AndroidCallGraph.v()` MUST NOT be populated by `FlowgraphRebuilder.buildCallGraph()` in this mode (INV-ANA-21). The legacy `AndroidCallGraph` rebuild via `FlowgraphRebuilder.buildCallGraph()` MUST be preserved behind `cgDelegation=false` for rollback.** Edges to library classes quarantined by SPARK's `IGNORED_CLASSES` are recovered via a WTG-level bytecode-scan complement (INV-ANA-22). **WTG construction is skipped entirely when the `skipWtg` client parameter is `true`** (see ADDED requirement below).

4. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager` (for Services/Receivers) or `android:authorities` attribute (for Providers), `android:exported` attribute from the manifest, and MOP reachability cross-referenced with the reachability BFS results. This section is written and flushed last — lowest priority for timeout graceful degradation.

The `complementWithCallbacks()` method, which propagates MOP flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive MOP flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null`) and `isMain` (boolean) fields. The `StaticAnalysisParser` (Python) MUST parse these fields into the `Clazz` domain model (`component_type: str | None`, `is_main: bool`).

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components). Downstream consumers (rv-coverage, rv-platform, the aperv binary via `MopData.java`) receive this data structure.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages. The `CoverageAnalyzer` explicitly switches to `RUNTIME_ONLY` or `FALLBACK_MODE` when reachability data is unavailable.

The reachability section also provides MOP prioritization data consumed by `aperv:sata_mop` (via `MopData.java`). When `transitions[]` is empty (e.g. after WTG skip or pre-fix legacy JSONs), `MopScorer.scoreWtg()` returns 0 cleanly via the existing `hasWtgData()` guard; the remaining three MOP weights (`mop_weight_direct`, `mop_weight_activity`, `mop_weight_transitive`) continue to operate on the populated `windows[]` and `reachability[]` sections.

The call graph is built using SPARK (`-cgAlgorithm spark`) with `all-reachable:true`, which performs full points-to analysis to resolve virtual calls based on types effectively instantiated in the program. SPARK is the operational default per design.md D5. Other algorithms — CHA (`-cgAlgorithm cha`), RTA (`-cgAlgorithm rta`), VTA (`-cgAlgorithm vta`) — remain available; the legacy `-withCHA` flag is accepted as an alias for `-cgAlgorithm cha` for backward compatibility. If the chosen algorithm crashes due to residual `InternalTypingException` (after defensive options and Soot 4.7.1), the analysis fails for that APK — there is no Flowgraph-level recovery for call-graph-phase crashes. JCA framework classes (`javax.crypto.Cipher`, `java.security.MessageDigest`, etc.) appear as call targets whenever any application method invokes them — they do not need to be entry points.

**Module**: rv-static-analysis (launcher + parser — sweep CLI gains `--skip-wtg` argument; widget Pydantic model gains four optional string fields), rvsec-gator (analysis client — modified: `RvsecAnalysisClient.writeJson` partial path, `extractWindows` catch-all guard, `FlowgraphRebuilder.buildCallGraph` SPARK delegation, new `MenuExtractor` and `SpinnerItemExtractor` classes, `Configs` new client parameters).
**External modules** (out of this repo but coordinated via JAR sync): `ape` (Java — `MopData.java` reads the `schemaVersion` field and tolerates v1.0 legacy JSONs with `null`/empty defaults for v2.0-only fields; rebuilds `ape-rv.jar` synchronously with `rvsec-analysis-client.jar`).
**Key components**: `Main.java`, `Flowgraph.java`, `RvsecAnalysisClient`, `FlowgraphRebuilder`, `MenuExtractor` (new), `SpinnerItemExtractor` (new), `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser`, `Clazz`.

#### Scenario: Successful static analysis with valid APK

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path and the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -cgAlgorithm spark`
- **AND** the resulting `.json` file MUST start with `"schemaVersion": "2.0"` (as the second field after `package`)
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` containing non-empty `Classes`, `Windows`, and `Components` (transitions may be empty if `skipWtg=true` or if WTG fails)
- **AND** the `.json` file MUST contain a `components` section (may have empty `receivers[]`, `services[]`, and `providers[]` arrays)

#### Scenario: WTG timeout still produces populated windows[] in partial JSON

- **WHEN** GATOR analyzes an APK whose WTG construction exceeds the external sweep timeout (e.g. `ac.mdiq.podcini.X_256.apk` from the original-APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/`), and the Java process is killed via SIGTERM during `WTGBuilder.build()`
- **THEN** the JSON file written before the kill MUST contain a fully-populated `windows[]` section with all activities, dialogs, options-menu skeletons, and their widgets (including listeners, text, hint, inputType, entries) extracted from `GUIAnalysisOutput`
- **AND** the JSON `transitions[]` MUST be `[]` (empty array, not missing)
- **AND** the JSON `schemaVersion` MUST be `"2.0"`
- **AND** the JSON `windows[].widgets[]` MUST NOT contain the catch-all WTG-only entries (fragments, context menus that depend on `wtg.getNodes()` enumeration) — these are skipped because `wtg == null` (INV-ANA-20)
- **AND** numeric `windows[].id` values MUST come from the `fallbackId` sequence (starting at `100000`) or from `dialog.id`/`menu.id` fallbacks, since `windowNodeIds` is an empty map in the partial-write path

#### Scenario: GATOR crashes during call graph construction

- **WHEN** Soot's call-graph builder throws an `InternalTypingException` during call graph construction for a method in a Kotlin class
- **THEN** the GATOR process MUST terminate with a non-zero exit code
- **AND** no `.json` output file MUST exist (the crash occurs before `RvsecAnalysisClient.run()` is invoked)
- **AND** the `StaticAnalyzer` wrapper MUST log the failure as `StaticAnalysisException`

#### Scenario: WTG built using SPARK call graph (cgDelegation=true, default)

- **WHEN** `RvsecAnalysisClient.run()` is invoked with default client parameters (i.e. `cgDelegation` not set, defaults to `true`)
- **AND** `WTGBuilder.build(output)` is called and reaches `FlowgraphRebuilder.buildCallGraph()`
- **THEN** `FlowgraphRebuilder.buildCallGraph()` MUST consult `Scene.v().getCallGraph()` to resolve virtual-dispatch targets for each `InvokeExpr` site
- **AND** `AndroidCallGraph.v()` MUST NOT be populated via the legacy CHA-style loop (`hier.getConcreteSubtypes()` + `hier.virtualDispatch()`)
- **AND** for `InvokeExpr` sites whose declared callee class is in `IGNORED_CLASSES` (SPARK quarantine — e.g. `java.security.*`, `javax.crypto.*`), edges MUST be recovered via the WTG-level bytecode-scan complement (INV-ANA-22)
- **AND** the resulting `transitions[]` JSON section MUST be semantically equivalent to the legacy `cgDelegation=false` output, modulo edges from `IGNORED_CLASSES` libraries that SPARK omits (recovered by bytecode-scan)

#### Scenario: WTG rollback via cgDelegation=false feature flag

- **WHEN** `RvsecAnalysisClient.run()` is invoked with `-clientParam cgDelegation=false`
- **THEN** `FlowgraphRebuilder.buildCallGraph()` MUST take the legacy code path (the pre-change CHA-style virtual-dispatch loop using `hier.virtualDispatch()` + `hier.getConcreteSubtypes()`)
- **AND** `AndroidCallGraph.v()` MUST be populated as before the change
- **AND** the output `transitions[]` MUST match exactly the pre-change baseline for the same APK (rollback is bit-for-bit on the WTG section)

#### Scenario: Flowgraph skips method with failing body (Scenario B recovery)

- **WHEN** `Flowgraph.processApplicationClasses()` calls `currentMethod.retrieveActiveBody()` and Soot throws an exception for a specific method
- **THEN** the exception MUST be caught (INV-ANA-17), a WARN log emitted, and the loop MUST continue
- **AND** the `RvsecAnalysisClient.run()` MUST execute and produce a JSON file with `schemaVersion: "2.0"` and a populated `windows[]` section

#### Scenario: Analysis output baseline comparison after Soot upgrade

- **WHEN** the analysis tool analyzes `cryptoapp.apk` and its output is compared against a saved baseline (produced by the pre-change build with `cgDelegation=false`)
- **THEN** window count MUST match exactly (±0) — windows[] is now WTG-independent so partial and full paths produce identical window sets except for WTG-only catch-all entries
- **AND** transition count MUST match within ±5% (Jaccard ≥0.95 on `{(src, tgt, event)}` tuples — see scenario "Paridade Jaccard WTG-SPARK")
- **AND** total method count MUST match exactly (±0)
- **AND** widget `inputType`, `entries`, `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` fields MUST match the expected XML-attribute values for the same APK (verified via `apktool d` inspection)

#### Scenario: Paridade Jaccard WTG-SPARK on baseline-OK APKs

- **WHEN** the change is validated against the 10-APK fixture defined in the change's `tasks.md` (a stratified sample of the 54 baseline-OK APKs)
- **AND** for each APK, `T_before` = set of `(source_window_id, target_window_id, event_type)` tuples from the pre-change `transitions[]`, and `T_after` = the same set from the post-change `transitions[]` with `cgDelegation=true`
- **THEN** the average Jaccard index `|T_before ∩ T_after| / |T_before ∪ T_after|` across the 10 APKs MUST be ≥ 0.95
- **AND** no individual APK MUST have Jaccard < 0.85
- **AND** divergences (transitions added by SPARK but missing in baseline, or vice versa) MUST be documented in the change's `tasks.md` paridade report and justified via SPARK semantics (e.g. tighter points-to set) or via the bytecode-scan complement

#### Scenario: Kotlin stdlib exclusion impact on reachability

- **WHEN** GATOR analyzes an APK with Kotlin dependencies and `-exclude kotlin.`, `-exclude kotlinx.`, and `-exclude androidx.compose.` are active
- **THEN** classes in `kotlin.*`, `kotlinx.*`, and `androidx.compose.*` packages MUST NOT have their bodies jimplified
- **AND** the call graph MUST still contain edges from application code to excluded package methods (as phantom refs)
- **AND** the `reachability` section of the output JSON MUST NOT include excluded-package classes (they are not application classes)
- **AND** for JCA specifications (`javax.crypto.*`, `java.security.*`), reachability MUST NOT be affected because JCA APIs are called by application code, not by Kotlin stdlib or Compose runtime

#### Scenario: `directlyReachesMop` detects literal library MOP invocations omitted by SPARK (BUG-INV-ANA-19)

- **WHEN** an application method's bytecode contains a literal invoke whose target's `(declaringClass.getName(), methodRef.name())` matches a MOP signature loaded from the `mopDir`
- **AND** Soot's SPARK call graph does NOT contain that target as a vertex (because library packages are quarantined as IGNORED_CLASSES)
- **THEN** `findDirectMopCallersByBytecodeScan` MUST detect the invocation by walking the method's `Body.getUnits()` and inspecting `InvokeExpr.getMethodRef()` against the precomputed `Set<String>` of `"className#methodName"` keys
- **AND** the matched method MUST be unioned into `directMopSet`
- **AND** the implementation MUST log scan statistics

#### Scenario: Bytecode-scan resilience on corrupted method bodies

- **WHEN** the bytecode scanner attempts `method.retrieveActiveBody()` and Soot raises a `RuntimeException` or `OutOfMemoryError`
- **THEN** the scanner MUST catch the throwable, emit a WARN log, and continue to the next method
- **AND** the scanner MUST NOT abort the analysis

#### Scenario: Bytecode-scan scope is limited to application classes

- **WHEN** the bytecode scanner runs as part of `RvsecAnalysisClient.run`
- **THEN** it MUST iterate only the `appClasses` map produced by `extractClasses` (already filtered by `code_package`)
- **AND** it MUST NOT iterate every class in `Scene.v().getClasses()`

## ADDED Requirements

### Requirement: JSON Schema Versioning (FR04, FR19)

The `RvsecAnalysisClient` MUST emit an explicit `schemaVersion` string field at the JSON root, immediately after the `package` field. The value MUST be `"2.0"` for any output produced after this change. Consumers (`StaticAnalysisParser`, `MopData.java`) MUST treat the absence of `schemaVersion` or a value of `"1.0"` as a legacy JSON and substitute safe defaults (`null` or empty array) for any v2.0-only field they cannot find. No backward-compatibility shims are required in the producer — `RvsecAnalysisClient` only writes v2.0 going forward, in accordance with P3 (no backward compatibility).

The fields gated by v2.0 are:
- `windows[].widgets[].prompt: string | null` (from `android:prompt`)
- `windows[].widgets[].spinnerMode: "dropdown" | "dialog" | null` (from `android:spinnerMode`)
- `windows[].widgets[].contentDescription: string | null` (from `android:contentDescription`)
- `windows[].widgets[].tooltipText: string | null` (from `android:tooltipText`)
- `windows[type="OPTIONSMENU"].widgets[].items: WidgetEntry[]` (recursive widget objects from `MenuExtractor`)
- `windows[].widgets[].entries: string[]` (now populated by both XML resolution AND `SpinnerItemExtractor` dataflow, when applicable; was previously XML-only)

The 158 pre-existing populated JSONs in `…/APKS_JCA_analise_estatica_soot/` are NOT migrated in-place. The 380-APK ground-truth re-run on `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/` (originals only — never the `*_DEXLIB`/`*_AJC` instrumented sets) that closes this change is the canonical source of v2.0 outputs.

#### Scenario: New JSON includes schemaVersion field

- **WHEN** `RvsecAnalysisClient.run()` completes for any APK
- **THEN** the output JSON MUST contain `"schemaVersion": "2.0"` as the second key in the root object (immediately after `"package"`)
- **AND** the field MUST be emitted by `writeJson()` before any other section (reachability, windows, transitions, components)

#### Scenario: Legacy JSON readable by updated MopData

- **WHEN** the `MopData.java` parser (in the external `ape` codebase) is invoked on a pre-change JSON (no `schemaVersion` field, or `schemaVersion == "1.0"`)
- **THEN** the parser MUST NOT raise a parse error
- **AND** missing v2.0 fields (`prompt`, `spinnerMode`, `contentDescription`, `tooltipText`, `items`) MUST be treated as `null` or empty list
- **AND** the parser MUST continue to extract reachability and windows as in the legacy contract

### Requirement: `skipWtg` Client Parameter for WTG Bypass (FR05, NFR06)

The `RvsecAnalysisClient` MUST honor a new client parameter `skipWtg=true` / `skipWtg=false` (default `false`). When `true`, `WTGBuilder.build()` MUST NOT be invoked: control flows directly from the reachability+windows partial-JSON write to the components section, and `transitions[]` is emitted as an empty array. When `false` (default), the existing WTG flow is preserved.

The sweep launcher `scripts/static_analysis_sweep.py` MUST expose a `--skip-wtg` boolean argument that propagates as `-clientParam skipWtg=true` to GATOR. The default is `false`. The flag exists to save wall-clock on APKs known to time out in WTG construction, when `transitions[]` is not required by the downstream consumer (e.g. aperv:sata_mop, which degrades gracefully via `MopScorer.scoreWtg → 0`).

When `skipWtg=true` is passed, `RvsecAnalysisClient` MUST log a single line at INFO: `[RvsecAnalysisClient] WTG skipped by client parameter`. The JSON `transitions[]` MUST be `[]` (not absent).

#### Scenario: skipWtg=true bypasses WTGBuilder

- **WHEN** `RvsecAnalysisClient.run()` is invoked with `-clientParam skipWtg=true`
- **THEN** `WTGBuilder.build()` MUST NOT be called
- **AND** no WTG-stage log lines (`stage 1 finishes`, ..., `stage 6 finishes`) MUST appear in stdout
- **AND** the output JSON MUST contain `"transitions": []`
- **AND** the output JSON `windows[]` MUST be populated (via the partial-JSON path with `wtg=null`)
- **AND** stdout MUST contain the line `[RvsecAnalysisClient] WTG skipped by client parameter`

#### Scenario: sweep --skip-wtg propagates to GATOR

- **WHEN** `scripts/static_analysis_sweep.py` is invoked with `--skip-wtg`
- **THEN** the GATOR command line for each APK MUST contain `-clientParam skipWtg=true`
- **AND** the sweep progress log MUST reflect that WTG is skipped (one line per batch: `[SWEEP] skipWtg=true active for this run`)

### Requirement: Widget XML Attribute Extensions (FR06)

The `enrichFromXml()` method of `RvsecAnalysisClient` MUST extract four additional widget attributes from decoded layout XML files (`Configs.resourceLocation`), in addition to the existing `inputType` and `entries` extraction. The four attributes are:

- `android:prompt` → widget field `prompt` (string, applies primarily to Spinner — the title shown when `spinnerMode="dialog"`).
- `android:spinnerMode` → widget field `spinnerMode` (string enum: `"dropdown"` | `"dialog"` | `null`).
- `android:contentDescription` → widget field `contentDescription` (string, accessibility label).
- `android:tooltipText` → widget field `tooltipText` (string, long-press hint).

Missing attributes MUST map to `null` (not empty string), so the JSON consumer can distinguish "attribute absent" from "attribute present but empty".

#### Scenario: Spinner widget gets prompt and spinnerMode

- **WHEN** a decoded layout XML file at `Configs.resourceLocation/layout/foo.xml` contains `<Spinner android:id="@+id/bar" android:prompt="@string/p" android:spinnerMode="dialog"/>`
- **AND** `enrichFromXml` processes that file for an activity whose root contains a widget with `idName == "bar"`
- **THEN** the corresponding widget in `windows[].widgets[]` MUST have `prompt = "<resolved p text>"` (after `@string/` resolution) and `spinnerMode = "dialog"`

#### Scenario: Button widget gets contentDescription and tooltipText

- **WHEN** a decoded layout XML contains `<Button android:id="@+id/b" android:contentDescription="Save" android:tooltipText="Save the form"/>`
- **THEN** the corresponding widget MUST have `contentDescription = "Save"` and `tooltipText = "Save the form"`

#### Scenario: Missing XML attribute maps to null

- **WHEN** a widget in a layout has no `android:prompt` attribute set
- **THEN** the JSON `windows[].widgets[].prompt` MUST be `null` (not empty string `""` and not absent from the object)

### Requirement: Inflated OPTIONSMENU Items via Existing GUI Flow Graph (FR06)

`RvsecAnalysisClient.extractWindows()` MUST emit the menu items of every XML-inflated options menu (i.e. menus populated by `MenuInflater.inflate(R.menu.<name>, menu)` inside `onCreateOptionsMenu`). The data is already produced by the existing GATOR pipeline: `FixpointSolver.processMenuInflaterCalls()` resolves the layout id to the activity's `NOptionsMenuNode`, and `FixpointSolver.doMenuInflate()` builds an `NMenuItemInflNode` for every `<item>` in the menu XML, attaches it as a child of the `NOptionsMenuNode` (via `addParent` / `children`), and populates its id node, text, and hint. Today this data is discarded by `extractWindows` because the OPTIONSMENU branch hardcodes `widgets: []`.

The fix MUST walk `menu.getChildren()` for each `NOptionsMenuNode` and feed the children into the existing `collectWidgets(output, child, widgets, visited)` recursion, mirroring the dialog-handling block immediately above (which already does this for `NDialogNode` via `output.getDialogRoots(dialog)`).

This requirement covers **only the XML-inflation path**. Programmatic construction (`menu.add(...)` inside `onCreateOptionsMenu`) is covered separately by the requirement "Programmatic Options-Menu Extraction via Soot CFG" — the two are complementary and may produce items for the same OPTIONSMENU when an activity mixes XML inflation with programmatic additions; in that case, the JSON output contains both sets of items in `widgets[]` (no deduplication needed because the id space is disjoint by construction — XML items carry the `R.id` from the menu resource, programmatic items carry the int constant passed to `Menu.add`).

#### Scenario: XML-inflated options menu populates items

- **WHEN** an activity calls `inflater.inflate(R.menu.foo, menu)` inside `onCreateOptionsMenu` with a valid `res/menu/foo.xml` containing items `@+id/a`, `@+id/b`
- **AND** the analysis pipeline (`FixpointSolver.doMenuInflate`) has built `NMenuItemInflNode` children of the `NOptionsMenuNode` for that activity
- **THEN** the `windows[type="OPTIONSMENU"]` entry for the activity MUST have `widgets[]` containing two entries with the respective ids and resolved titles
- **AND** each entry MUST include the same fields as widgets in ACTIVITY/DIALOG windows (`id`, `idName`, `type`, `text`, `hint`, `listeners`, plus the four XML attributes from "Widget XML Attribute Extensions" — all `null` for menu items)

#### Scenario: cryptoapp baseline regression test

- **WHEN** the analysis runs on `apks_examples/cryptoapp.apk` (which has `onCreateOptionsMenu` calling `inflater.inflate(R.menu.cryptoapp_menu, menu)` and `res/menu/cryptoapp_menu.xml` containing 3 items: `menu_item_message_digest`, `menu_item_cipher`, `menu_item_home`)
- **THEN** the produced JSON MUST have `windows[where type="OPTIONSMENU" and name endsWith "#OptionsMenu"].widgets[]` with exactly 3 entries
- **AND** each of the 3 entries MUST have a non-null `id` corresponding to the menu-item resource id

### Requirement: Programmatic Options-Menu Extraction via Soot CFG (FR06)

A new class `MenuExtractor` (in the `rvsec-gator` client module) MUST trace programmatic options-menu construction in `onCreateOptionsMenu(Menu)` methods of application activities. The extractor MUST resolve the following invocation patterns via Soot CFG walking from the entry point of `onCreateOptionsMenu`:

- `Menu.add(int groupId, int itemId, int order, CharSequence title)` → menu item with literal `title`.
- `Menu.add(int groupId, int itemId, int order, int titleRes)` → menu item with title resolved from `@string/<name>` via the existing `XMLParser`/string-resource lookup.
- `Menu.addSubMenu(int groupId, int itemId, int order, CharSequence title)` → submenu node followed by `getSubItems` CFG-forward walk to collect `SubMenu.add(...)` invocations.
- `Menu.addSubMenu(int groupId, int itemId, int order, int titleRes)` → same with string-resource resolution.

The extractor populates `windows[type="OPTIONSMENU"].widgets[].items[]` as a recursive widget-entry list (each `items[]` entry is itself a widget object that may contain its own `items[]` for submenus). Widget IDs come from the `itemId` argument of the `Menu.add` call (literal int constant).

The extractor MUST be resilient to body-retrieval failures (catch per-method exceptions, log, continue — same pattern as INV-ANA-17, codified as INV-ANA-24).

#### Scenario: Programmatic Menu.add with literal CharSequence

- **WHEN** an activity's `onCreateOptionsMenu(Menu menu)` body contains the Jimple equivalent of `menu.add(0, 100, 0, "Settings")`
- **AND** `MenuExtractor` walks the CFG of that method
- **THEN** the `windows[type="OPTIONSMENU"]` entry for that activity MUST contain a widget with `items[]` including `{id: 100, text: "Settings", type: "MenuItem"}`

#### Scenario: Programmatic Menu.add with @string resource

- **WHEN** the activity calls `menu.add(0, 200, 0, R.string.cfg_label)` where `R.string.cfg_label` resolves to `"Configuration"`
- **THEN** the corresponding menu item MUST have `text: "Configuration"` (resolved via the existing string-resource lookup helpers in `RvsecAnalysisClient`)

#### Scenario: SubMenu followed by SubMenu.add chains

- **WHEN** the activity calls `SubMenu sub = menu.addSubMenu(0, 300, 0, "Tools"); sub.add(0, 301, 0, "Export"); sub.add(0, 302, 0, "Import")`
- **THEN** the corresponding submenu widget MUST have `id: 300`, `text: "Tools"`, and `items: [{id: 301, text: "Export"}, {id: 302, text: "Import"}]` (recursive structure)

#### Scenario: Body-retrieval failure does not abort extraction

- **WHEN** `MenuExtractor` attempts to walk the CFG of an activity's `onCreateOptionsMenu` and Soot raises a `RuntimeException` during `retrieveActiveBody()`
- **THEN** the extractor MUST catch the exception, emit a WARN log with the activity class name, and continue with the next activity (INV-ANA-24)
- **AND** the JSON `windows[type="OPTIONSMENU"]` for the failing activity MUST have `items: []` (empty, not missing the widget)

### Requirement: Programmatic Spinner Items via ArrayAdapter Dataflow (FR06, MVP)

A new class `SpinnerItemExtractor` (in the `rvsec-gator` client module) MUST resolve Spinner items populated programmatically via `ArrayAdapter`. The MVP scope covers exactly two patterns:

1. **Literal constructor**: `new ArrayAdapter<>(ctx, layoutId, items)` where `items` is a literal `String[]` array (`new String[]{"a", "b", "c"}`) or a literal `List<String>` (`Arrays.asList(...)` over literal strings).
2. **Programmatic add**: `adapter.add(s)` / `adapter.addAll(arr)` where `s` is a literal string and `arr` is a literal `String[]`.

Resolution MUST use the SPARK points-to set (`Scene.v().getPointsToAnalysis()`) to find the receiver type of the `setAdapter` call and to trace the def-use chain of the items argument to its allocation site. The receiver Spinner is identified by walking back from `spinner.setAdapter(adapter)` to a `findViewById` whose argument is the Spinner widget ID.

**Out of scope for MVP** (deferred to a future change, gated on corpus coverage measurement):
- `getResources().getStringArray(R.array.X)` source (resolution of `R.array` to `arrays.xml`).
- Kotlin `listOf("a", "b")` source (Kotlin desugaring to `Arrays.asList`).
- Dynamic strings (concatenation, function calls, field reads).

When the extractor cannot fully resolve an item (e.g. it traces back to a non-literal), the partial result MUST be emitted (literals resolved, non-literals omitted with a per-Spinner WARN log). The extractor MUST union its results into `windows[].widgets[where type="Spinner"].entries[]` after the XML-based `enrichFromXml` runs, so XML-defined `entries` from `android:entries="@array/X"` are preserved and the programmatic items are appended.

The extractor MUST carry a corpus-coverage telemetry log: `[SpinnerItemExtractor] processed N spinners: X literal-constructor, Y add/addAll, Z unresolved`.

#### Scenario: Literal constructor populates Spinner entries

- **WHEN** an activity's code contains the Jimple equivalent of `ArrayAdapter<String> a = new ArrayAdapter<>(this, R.layout.spinner_item, new String[]{"red", "green", "blue"}); spinner.setAdapter(a)` and `spinner = findViewById(R.id.color)`
- **THEN** the widget `windows[].widgets[where idName="color"].entries` MUST be `["red", "green", "blue"]`

#### Scenario: adapter.add() calls populate entries incrementally

- **WHEN** an activity's code contains `ArrayAdapter<String> a = new ArrayAdapter<>(this, R.layout.spinner_item); a.add("alpha"); a.add("beta"); spinner.setAdapter(a)`
- **THEN** the widget `entries` MUST be `["alpha", "beta"]`

#### Scenario: XML entries and programmatic entries coexist

- **WHEN** a Spinner has both `android:entries="@array/preset"` (resolving to `["x", "y"]`) and a runtime `adapter.add("z")` call that is later set via `setAdapter`
- **THEN** the JSON `entries` MUST contain both XML entries first then programmatic entries: `["x", "y", "z"]`

#### Scenario: Non-literal item is logged and skipped

- **WHEN** an activity's code calls `adapter.add(getString(R.string.dynamic))` where the string-resource lookup is hidden behind a method call
- **THEN** `SpinnerItemExtractor` MUST emit a WARN log identifying the unresolved item and continue
- **AND** the JSON `entries` for that Spinner MUST contain only the items that WERE resolved (not the unresolved one)

### Requirement: GATOR Invocation Robustness (FR04)

The Python invoker (`rv-static-analysis`) MUST invoke the GATOR launcher using the running interpreter (`sys.executable`) — never a literal `"python"` string. The launcher is a Python script with `#!/usr/bin/env python3` shebang, but the invoker passes it as `<interpreter> <script> <args>`, so the interpreter argument is what reaches `execve`. Hardcoding `"python"` breaks on systems where the `python-is-python3` shim is absent (clean containers, fresh shells on non-Debian distros, CI runners without the shim package), producing a `CommandNotFoundError` that gets caught upstream as a warning and yields a silently-empty JSON output. The invoker MUST always pick the actual Python 3.x binary that is executing the workspace (uv's `.venv/bin/python` in the standard layout), which is reachable by construction.

Additionally, `StaticAnalyzer._run_analysis` MUST validate, after the GATOR command returns (including the timeout-tolerant `RVCommandTimeoutError` path), that the output JSON file exists on disk. If absent, the method MUST raise `StaticAnalysisException` with a message identifying the missing path and pointing at interpreter / launcher reachability as the likely cause. This converts upstream silent failures (e.g. `CommandNotFoundError` swallowed by the `ErrorHandler` decorator, a JVM crash before any output was flushed, a permission error on the output directory) into hard, observable errors before the parser is invoked and before the downstream summary CSV is written with misleading zero-coverage metrics.

A timed-out GATOR invocation produces a partial JSON file (the client flushes reachability first, then windows, then transitions, with intermediate flushes — INV-ANA-06), so the existence check passes on timeout. Only the genuinely-empty case (no file at all) escalates.

#### Scenario: Interpreter resolution uses the running Python

- **WHEN** `RVStaticAnalysisConfig.get_tool_command("analysis", apk_path, output_file)` is called from any context (CLI, rv-experiment pre-processing, unit tests)
- **THEN** the returned command list's first element MUST equal `sys.executable` (the absolute path of the running Python 3.x interpreter)
- **AND** the second element MUST be the path to the `gator` launcher script
- **AND** the command MUST be reachable via `execve` on any POSIX system that has the same uv-managed virtualenv on PATH (no dependency on `/usr/bin/python` existing)

#### Scenario: Missing output JSON escalates to StaticAnalysisException

- **WHEN** `StaticAnalyzer._run_analysis` completes (either via successful `Command.invoke` return or via the `RVCommandTimeoutError` partial-success path)
- **AND** the configured output file does not exist on disk
- **THEN** the method MUST raise `StaticAnalysisException` with a message that includes the missing path and the diagnostic hint "check that the python interpreter and gator launcher are reachable"
- **AND** the `analyze()` wrapper MUST propagate the exception into `result.success = False` and `result.errors`, not swallow it as a warning

#### Scenario: Timeout with partial JSON is not escalated

- **WHEN** the GATOR invocation hits the analysis timeout and `RVCommandTimeoutError` is caught
- **AND** the GATOR client wrote at least the reachability section before being killed (partial JSON exists)
- **THEN** `_run_analysis` MUST NOT raise — the existence check sees the partial file and returns normally
- **AND** `result.timed_out` MUST be set to `True` so downstream consumers can distinguish a partial run from a clean one
