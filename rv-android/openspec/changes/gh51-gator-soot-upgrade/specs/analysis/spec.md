## Purpose

Delta spec for the GATOR Soot upgrade (gh51). The GATOR analysis client crashes on 72.4% of APKs due to Soot 3.3.0's `InternalTypingException` in `ClassHierarchy.typeNode()` when processing Kotlin bytecode. This change adds defensive Soot configuration, graceful error handling in `Flowgraph.java`, and upgrades Soot from 3.3.0 to 4.7.1. The Python-side parser (`StaticAnalysisParser`) is unchanged — it already handles partial JSON via INV-ANA-06. All changes are in the Java GATOR codebase (`rvsec-gator`).

The crash has two distinct paths: **Scenario A** (dominant) occurs during CHA call graph construction (`CHATransformer.internalTransform()`), before the GATOR GUI analysis phase executes. **Scenario B** occurs during `Flowgraph.processApplicationClasses()` when `retrieveActiveBody()` or `createOpNode()` triggers the same TypeResolver crash. FIX 1 (defensive options) and FIX 3 (Soot upgrade) reduce Scenario A frequency; FIX 2 (graceful error handling) captures residual Scenario B crashes.

### Empirical Validation (2026-04-19)

CryptoAnalysis 5.0.1 (Soot 4.6.0 + FlowDroid 2.14.1) was tested on the same APKs that crash GATOR (Soot 3.3.0):

| APK | Size | GATOR (Soot 3.3.0) | CogniCrypt (Soot 4.6.0) |
|-----|------|-------------------|------------------------|
| `app.zornslemma.mypricelog_4.apk` | Small, 1 DEX | **CRASH** (7s, TypeResolver) | **OK** (26s) |
| `be.chvp.nanoledger_2026040501.apk` | 31 .kt, Compose | **OK** (165s, JSON 834KB) | **OK** (24s) |
| `ac.mdiq.podcini.X_256.apk` | 167 .kt, large | **CRASH** (50s, TypeResolver) | **TIMEOUT** (>5min, no crash) |
| `app.fluffy_730.apk` | 53 .kt, Compose | **CRASH** (18s, TypeResolver) | **TIMEOUT** (>2min, no crash) |
| `app.siftrecipes_6.apk` | Medium, target 34 | **CRASH** (17s, TypeResolver) | **TIMEOUT** (>2min, no crash) |

Conclusion: Soot 4.6.0 with defensive options does NOT crash — the timeouts are due to CogniCrypt's SPARK call graph (slower than GATOR's CHA), not TypeResolver issues.

### SA Success Rates by APK Category (baseline)

| Category | APKs | SA Rate | Example |
|----------|------|---------|---------|
| Java pure | ~20 | ~80% | NoteSR (162 .java, 0 .kt) |
| Kotlin small (< 30 .kt) | ~30 | ~60% | NanoLedger (31 .kt, 165s SA OK) |
| Kotlin + Compose (> 50 .kt) | ~250 | ~15% | Podcini.X (167 .kt), HypoStats (63 .kt) |
| Flutter/other | ~50 | ~40% | pomodorot (Flutter) |

### Soot Configuration Comparison (rationale for FIX 1 options)

| Soot Option | GATOR (3.3.0) | CryptoAnalysis 5.0.1 (4.6.0) | FlowDroid 2.15+ (4.8.0) | Effect |
|-------------|---------------|-------------------------------|------------------------|--------|
| `no_bodies_for_excluded` | **No** | **Yes** | **Yes** | Skips jimplification of excluded packages |
| Exclude `android.*`, `androidx.*` | **No** | **Yes** | **Yes** | Avoids framework body processing |
| Exclude `kotlin.*`, `kotlinx.*` | **No** | No | No | Avoids Kotlin stdlib crashes |
| `ignore_resolution_errors` | **No** | **Yes** | **Yes** | Handles unresolvable classes gracefully (does NOT prevent `InternalTypingException`) |
| `jb.sils` disabled | **No** | **Yes** | No | Avoids typing errors in static inlining (soot#1641) |
| `jb.dae` disabled | **No** | **Yes** | No | Avoids typing errors in dead assignment elimination |
| `throw_analysis_dalvik` | **No** | **Yes** | **Yes** | Correct exception semantics for DEX (does NOT prevent `InternalTypingException`) |
| Soot version | **3.3.0** | **4.6.0** | **4.8.0** | Dexpler improvements reduce crash frequency |

**Note**: GATOR MUST NOT exclude `android.*`/`androidx.*` (unlike CryptoAnalysis/FlowDroid) because it needs framework bodies for widget and listener analysis (WTG construction).

## Data Contracts

No changes to data contracts. The analysis JSON format, `StaticAnalysisData` model, and `StaticAnalysisParser` interface are all unchanged. The change affects only the rate at which GATOR produces JSON files — more APKs will produce output.

## Invariants

- **INV-ANA-16**: The GATOR `Main.java` MUST configure Soot with the following defensive options in both `withCHA` and non-CHA branches: `-p jb.sils enabled:false`, `-p jb.dae enabled:false`, `-no-bodies-for-excluded`, `-exclude kotlin.`, `-exclude kotlinx.`. Programmatically: `Options.v().set_ignore_resolution_errors(true)` and `Options.v().set_throw_analysis(Options.throw_analysis_dalvik)`. The options `jb.sils` and `jb.dae` are the primary crash triggers (soot-oss/soot#1641). The excludes and `no_bodies_for_excluded` prevent jimplification of Kotlin stdlib classes. The remaining options (`ignore_resolution_errors`, `throw_analysis_dalvik`) are general robustness practices that do NOT prevent the `InternalTypingException` specifically.

- **INV-ANA-17**: The GATOR `Flowgraph.processApplicationClasses()` MUST wrap the `currentMethod.retrieveActiveBody()` call (line 274) in a try-catch that logs the skipped method and continues to the next method. The existing catch block around `createOpNode()` (line 343) MUST replace `throw new RuntimeException(e)` with a log message and `continue`. Both catch blocks MUST log the skipped method signature and exception message using `Logger.verb()`. This ensures partial Flowgraph construction when individual methods fail to jimplify.

- **INV-ANA-18**: The GATOR module (`rvsec-gator`) MUST use `org.soot-oss:soot` with version `${soot.version}` from the parent pom (4.7.1), replacing `ca.mcgill.sable:soot:3.3.0`. The `rvsec-gator/client/pom.xml` MUST NOT exclude Soot from the assembly plugin (the groupId conflict no longer exists). The parent `rvsec/pom.xml` MUST set `<soot.version>4.7.1</soot.version>`.

## MODIFIED Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing four data sections written in priority order: (1) method reachability relative to MOP specifications (coverage denominator), (2) window and widget inventory with event listeners, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and MOP reachability.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. GATOR initializes Soot once with defensive configuration (INV-ANA-16), builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the client writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file.

The `Flowgraph.processApplicationClasses()` method MUST handle individual method failures gracefully (INV-ANA-17). When `retrieveActiveBody()` or `createOpNode()` throws an exception for a specific method, the Flowgraph MUST skip that method and continue processing remaining methods. The resulting Flowgraph may be incomplete (missing OpNodes, widgets, or listeners for skipped methods), but the GUIAnalysis pipeline MUST complete and the `RvsecAnalysisClient` MUST produce JSON output. Reachability data (computed from `Scene.v().getCallGraph()` via BFS) is NOT affected by Flowgraph incompleteness — it depends on the Soot call graph, not on the Flowgraph.

The GATOR MUST use Soot 4.7.1 (`org.soot-oss:soot`, INV-ANA-18) with defensive configuration (INV-ANA-16). The `ClassHierarchy.typeNode()` bug (soot-oss/soot#1071) is not fixed in Soot 4.7.1, but the improved Dexpler in 4.x reduces crash frequency. The defensive options (excluding `kotlin.*` from body loading, disabling `jb.sils`/`jb.dae`) further reduce the crash surface. Together, these changes form a layered defense: prevention (FIX 1), recovery (FIX 2), and fundamental improvement (FIX 3).

The execution order inside `run()`:

1. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). Service, Receiver, and Provider class names are resolved to `SootClass` via `Scene.v().getSootClassUnsafe()`, which returns `null` for unresolvable classes (logged as WARNING, skipped). Lifecycle methods are found by iterating `SootClass.getMethods()` and filtering by name. For each application method, it computes: `reachable` (reachable from entry points), `reachesMop` (has path to a monitored API method), and `directlyReachesMop` (directly invokes a monitored API method). MOP method signatures are loaded from `.mop` specification files via `JavamopFacade`. This section is written and flushed first.

2. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners discovered through interprocedural data flow. Two fields not available via GATOR APIs — `inputType` and `entries` — are extracted by parsing the decoded layout XML files at `Configs.resourceLocation`.

3. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures.

4. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager` (for Services/Receivers) or `android:authorities` attribute (for Providers), `android:exported` attribute from the manifest, and MOP reachability cross-referenced with the reachability BFS results. This section is written and flushed last — lowest priority for timeout graceful degradation.

The `complementWithCallbacks()` method, which propagates MOP flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive MOP flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null`) and `isMain` (boolean) fields. The old `isActivity` and `isMainActivity` fields are removed. The `StaticAnalysisParser` (Python) MUST parse these fields into the `Clazz` domain model (`component_type: str | None`, `is_main: bool`).

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components). Downstream consumers (rv-agent, rv-coverage, rv-platform) receive this data structure.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages. The `CoverageAnalyzer` explicitly switches to `RUNTIME_ONLY` or `FALLBACK_MODE` when reachability data is unavailable.

The reachability section also provides MOP prioritization data consumed by rv-agent. The `MopScorer` in rv-agent's `ActionRanker` assigns +100 score to actions with `directly_reaches_mop=true` and +50 to actions with `reaches_mop=true`, directing exploration toward MOP-relevant code paths.

The call graph is built using CHA (`-withCHA` flag) with `all-reachable:true`, which resolves all virtual calls based on the class hierarchy. If CHA crashes due to residual `InternalTypingException` (after defensive options and Soot 4.7.1), the analysis fails for that APK — there is no Flowgraph-level recovery for CHA-phase crashes. JCA framework classes (`javax.crypto.Cipher`, `java.security.MessageDigest`, etc.) appear as call targets whenever any application method invokes them — they do not need to be entry points.

**Module**: rv-static-analysis (launcher + parser — unchanged), rvsec-gator (analysis client — modified)
**Key components**: `Main.java` (Soot config), `Flowgraph.java` (error handling), `RvsecAnalysisClient` (unchanged), `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser` (unchanged), `Clazz`

#### Scenario: Successful static analysis with valid APK

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path and the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -withCHA`
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` containing non-empty `Classes`, `Windows`, `WindowTransitionGraph`, and `Components`
- **AND** the `.json` file MUST contain a `components` section (may have empty `receivers[]`, `services[]`, and `providers[]` arrays)

#### Scenario: GATOR crashes during CHA call graph construction

- **WHEN** Soot's `CHATransformer.internalTransform()` throws an `InternalTypingException` during call graph construction for a method in a Kotlin class
- **THEN** the GATOR process MUST terminate with a non-zero exit code
- **AND** no `.json` output file MUST exist (the crash occurs before `RvsecAnalysisClient.run()` is invoked)
- **AND** the `StaticAnalyzer` wrapper MUST log the failure as `StaticAnalysisException`
- **AND** the `StaticAnalysisResult.analysis_file` MUST point to the expected output path (which does not exist)

#### Scenario: Flowgraph skips method with failing body (Scenario B recovery)

- **WHEN** `Flowgraph.processApplicationClasses()` calls `currentMethod.retrieveActiveBody()` and Soot throws an exception (e.g., `InternalTypingException`) for a specific method
- **THEN** the exception MUST be caught by the try-catch around `retrieveActiveBody()` (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.verb()` with the skipped method's signature and exception message
- **AND** the loop MUST continue to the next method via `continue`
- **AND** the Flowgraph MUST complete with partial data (missing OpNodes for the skipped method)
- **AND** the `RvsecAnalysisClient.run()` MUST execute and produce a JSON file

#### Scenario: Flowgraph skips statement with failing OpNode creation

- **WHEN** `Flowgraph.processApplicationClasses()` calls `createOpNode(currentStmt)` and the method throws an exception for a specific statement
- **THEN** the exception MUST be caught by the existing catch block (line 343, INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.verb()` with the skipped statement and exception message
- **AND** the loop MUST continue to the next statement via `continue`
- **AND** the resulting Flowgraph MUST be missing the OpNode for that statement but otherwise complete

#### Scenario: Kotlin stdlib exclusion impact on reachability

- **WHEN** GATOR analyzes an APK with Kotlin dependencies and `-exclude kotlin.` and `-exclude kotlinx.` are active
- **THEN** classes in `kotlin.*` and `kotlinx.*` packages MUST NOT have their bodies jimplified
- **AND** the call graph MUST still contain edges from application code to `kotlin.*` methods (as phantom refs)
- **AND** the `reachability` section of the output JSON MUST NOT include `kotlin.*` classes (they are not application classes)
- **AND** for JCA specifications (`javax.crypto.*`, `java.security.*`), reachability MUST NOT be affected because JCA APIs are called by application code, not by Kotlin stdlib

#### Scenario: Analysis output baseline comparison after Soot upgrade

- **WHEN** the analysis tool analyzes `cryptoapp.apk` with Soot 4.7.1 and its output is compared against the saved baseline (produced with Soot 3.3.0)
- **THEN** window count MUST match exactly (±0)
- **AND** transition count MUST match exactly (±0)
- **AND** total method count MUST match exactly (±0)
- **AND** `reachable` and `reachesMop` method counts MAY differ by up to ±10% due to Soot version change (3.3.0 → 4.7.1) — differences MUST be documented
- **AND** `directlyReachesMop` counts MUST match exactly (±0) because direct call edges are CG-construction-independent
- **AND** widget `inputType` and `entries` fields MUST match GESDA output for the same APK
