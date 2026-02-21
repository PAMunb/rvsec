# Delta Spec: Analysis Domain — Unified Static Analysis

**Change**: gh27-unified-static-analysis
**Domain**: analysis (rv-static-analysis, rv-coverage, rv-screen-parser)
**Affected modules**: rv-static-analysis (major), rv-android-core (minor), rv-platform (minor)

## Purpose

This delta spec documents the consolidation of three separate static analysis tools (GESDA, GATOR, REACH) into a single GATOR analysis client. The motivation is eliminating 3 redundant Soot initializations per APK, which cause timeouts in gh26 experiments. After this change, a single GATOR invocation produces one analysis JSON file containing windows (from GESDA), transitions (from GATOR WTG), and reachability data (from REACH). The `StaticAnalyzer` invokes one tool instead of three, and a single `StaticAnalysisParser` replaces three separate parsers.

The rv-coverage and rv-screen-parser modules are unaffected — they consume `StaticAnalysisData` (Classes, Windows, WindowTransitionGraph) which retains the same structure. Only the production pathway changes: one JSON file parsed by one parser, instead of three files parsed by three parsers.

## Data Contracts

### Input (changed)

- `apk_path: str` — Path to Android APK file (unchanged)
- `code_package: str` — Application code package name from `App.code_package` (unchanged)
- `mop_dir: str` — Path to MOP specification directory. Previously consumed only by REACH via `--mop-dir` CLI flag. Now passed to the single GATOR analysis client via `-clientParam mopDir=<path>`.
- `analysis_timeout: float` — Timeout in seconds for the analysis tool (default: 600.0). Replaces the implicit no-timeout behavior of the previous three-tool pipeline. Passed both as `Command.timeout` (Python process-level kill) and `--timeout` (GATOR's internal timeout).
- `analysis_client_jar: str` — Path to the analysis client fat JAR (`lib/analysis-client/rvsec-analysis-client.jar`). Replaces `gesda_jar`, `gator_dir`, and `reach_jar`.
- `jvm_memory: str` — JVM max heap size (default: `"8g"`). Applied as `-Xmx` flag to the GATOR launcher.

### Output (changed)

- `StaticAnalysisData` — Contains Classes, Windows, and WindowTransitionGraph. Structure is unchanged for downstream consumers.
- `StaticAnalysisResult` — **CHANGED**: Previously contained `gesda_file: str`, `gator_file: str`, `reach_file: str`. Now contains `analysis_file: str` and `timed_out: bool`.

### Side-Effects (changed)

- **File System**: Creates `{app_name}.json` analysis output file in the output directory. Replaces the previous three files (`.gesda`, `.wtg`, `.reach`).

### Error (unchanged)

- `StaticAnalysisException` — Raised when the analysis tool returns a non-zero exit code. Contains tool name ("ANALYSIS"), exit code, and stderr output.
- `RVCommandTimeoutError` — Raised when the analysis tool exceeds `analysis_timeout`. The `Command` class kills the process tree via `kill_process_tree()`.
- `ConfigurationError` — Raised when `analysis_client_jar` path does not exist or MOP directory is missing.

## Invariants

### REMOVED Invariants

- **INV-ANA-01** (REMOVED): "GESDA analysis MUST complete before REACH analysis begins" — No longer applicable. There is one tool, not a pipeline. The single GATOR analysis client performs all extraction (windows, transitions, reachability) in a single invocation. **Reason**: The ordering constraint existed because REACH consumed GESDA output as input. In the analysis client, all data is available in memory from the same GATOR analysis pass.

### MODIFIED Invariants

- **INV-ANA-02**: The `StaticAnalysisParser` MUST apply `SignatureNormalizer` to all class names and method signatures before storing them in domain models. The normalization converts inner class dot notation (`OuterClass.InnerClass`) to dollar notation (`OuterClass$InnerClass`) using Java naming convention heuristics. Previously, this invariant applied to three separate parsers (GatorParser, GesdaParser, ReachParser). Now it applies to a single `StaticAnalysisParser` which normalizes class names in all three JSON sections (`windows`, `transitions`, `reachability`).

- **INV-ANA-03**: The `StaticAnalysisParser` MUST receive `code_package` (from `App.code_package`, detected by `PackageDetector`) for class filtering, NOT `package_name` (from AndroidManifest.xml). The parser MUST filter classes in the `reachability` section and windows in the `windows` section by verifying that class names contain the `code_package` string. Previously, this filtering was performed independently by each of the three parsers.

- **INV-ANA-06**: The `StaticAnalysisParser` MUST NOT propagate exceptions to callers. On parse failure of any section (`windows`, `transitions`, `reachability`), it MUST log the error and return empty domain objects for that section: `Windows()` for window parsing failures, `WindowTransitionGraph()` for transition parsing failures, `Classes()` for reachability parsing failures. Each section is parsed independently — a failure in one section MUST NOT prevent parsing of other sections. Previously, this graceful degradation was implemented per-parser; now it is per-section within a single parser.

- **INV-ANA-11**: The `StaticAnalyzer` MUST implement intelligent caching: if the analysis `.json` output file already exists, tool execution MUST be skipped. A `CommandResult(0, b"", b"")` MUST be returned for cached results. An info log with `execution_status='cached'` MUST be recorded. Previously, caching was checked independently for each of the three output files (`.gesda`, `.wtg`, `.reach`).

## MODIFIED Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing three data sections written in priority order: (1) method reachability relative to MOP specifications (coverage denominator), (2) window and widget inventory with event listeners, and (3) window transition graph. The section ordering is deliberate: `reachability` is written first because it defines the method universe used as the coverage denominator. On timeout, partial JSON preserves the most critical data first.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. GATOR initializes Soot once, builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the client writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file. The execution order inside `run()`:

1. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. For each application method, it computes: `reachable` (reachable from Android framework entry points), `reachesMop` (has a direct or indirect path to a monitored API method from the MOP specification directory), and `directlyReachesMop` (directly invokes a monitored API method). MOP method signatures are loaded from `.mop` specification files via `JavamopFacade`. This section is written and flushed first — it establishes the method universe that Coverage.aj runtime logging matches against (both use Soot's `<class: returnType method(params)>` signature format).

2. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners discovered through interprocedural data flow. Two fields not available via GATOR APIs — `inputType` and `entries` — are extracted by parsing the decoded layout XML files at `Configs.resourceLocation`.

3. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures.

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph). Downstream consumers (rv-agent, rv-coverage, rv-platform) receive this data structure.

The call graph is built using Soot's default entry point strategy — Android lifecycle callbacks discovered by FlowDroid's callback analysis. JCA framework classes (`javax.crypto.Cipher`, `java.security.MessageDigest`, etc.) appear as call targets whenever any application method invokes them — they do not need to be entry points. If reachability is insufficient for specific APKs, GATOR supports a `-withCHA` flag that enables CHA (Class Hierarchy Analysis), which resolves all virtual calls based on the class hierarchy.

**Module**: rv-static-analysis
**Key components**: `StaticAnalyzer`, `StaticAnalysisParser`, `RVStaticAnalysisConfig`

#### Scenario: Successful static analysis with valid APK

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path and the analysis client JAR exists at `lib/analysis-client/rvsec-analysis-client.jar`
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout>`
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` containing non-empty `Classes`, `Windows`, and `WindowTransitionGraph`

#### Scenario: Static analysis JSON parsing — windows section

- **WHEN** `StaticAnalysisParser._parse_windows()` processes the `windows` array from the analysis JSON
- **THEN** each window entry MUST produce a `Window` object with `id`, `name`, `type` (ACTIVITY, DIALOG, OPTIONSMENU), and `isMain` flag
- **AND** each widget in the window's `widgets` array MUST produce a `Widget` object with `id`, `idName`, `type`, `text`, `hint`, `inputType`, and `entries`
- **AND** each listener in a widget's `listeners` array MUST produce a `WidgetEvent` with `event_type` mapped from the listener's `eventType` string (click → CLICK, long_click → LONG_CLICK, scroll → SCROLL, selection → SELECTION) and `signature` from the `handler` field
- **AND** listeners with `eventType` mapping to `OTHER` MUST be excluded
- **AND** class names MUST be normalized via `SignatureNormalizer` (INV-ANA-02)
- **AND** windows with class names not containing `code_package` MUST be filtered out (INV-ANA-03)

#### Scenario: Static analysis JSON parsing — transitions section

- **WHEN** `StaticAnalysisParser._parse_transitions()` processes the `transitions` array from the analysis JSON
- **THEN** each transition MUST resolve `sourceId` and `targetId` to `Window` objects from the previously parsed `windows` section
- **AND** each event in the transition's `events` array MUST produce a `Widget` (if not already created) with `widgetId`, `widgetClass`, and `widgetName`, and a `WidgetEvent` with the handler signature
- **AND** a `WindowTransition` edge MUST be added to the `WindowTransitionGraph` connecting source to target window
- **AND** transitions referencing unknown window IDs MUST be logged as warnings and skipped

#### Scenario: Static analysis JSON parsing — reachability section

- **WHEN** `StaticAnalysisParser._parse_classes()` processes the `reachability` array from the analysis JSON
- **THEN** each class entry MUST produce a `Clazz` object with `name`, `isActivity`, and `isMainActivity` flags
- **AND** each method in the class's `methods` array MUST produce a `Method` object with `name`, `signature`, `reachable`, `reachesMop`, and `directlyReachesMop` flags
- **AND** class names and signatures MUST be normalized via `SignatureNormalizer` (INV-ANA-02)
- **AND** classes not containing `code_package` in their name MUST be filtered out (INV-ANA-03)

#### Scenario: Static analysis JSON parsing with inner class normalization

- **WHEN** `StaticAnalysisParser` encounters a class name like `com.example.OuterActivity.InnerFragment` in any section
- **THEN** `SignatureNormalizer` MUST convert it to `com.example.OuterActivity$InnerFragment`
- **AND** the normalized name MUST be used for all domain model lookups and storage

#### Scenario: Analysis output file does not exist

- **WHEN** `StaticAnalysisParser.parse_file()` is called with a non-existent file path
- **THEN** a warning MUST be logged
- **AND** an empty `StaticAnalysisData` MUST be returned with empty `Classes()`, `Windows()`, and `WindowTransitionGraph()`

#### Scenario: Partial JSON parse failure (per-section graceful degradation)

- **WHEN** the analysis JSON file exists but the `reachability` section contains malformed data
- **THEN** `StaticAnalysisParser._parse_classes()` MUST catch the exception, log an error, and return empty `Classes()`
- **AND** the `windows` and `transitions` sections MUST still be parsed successfully
- **AND** the returned `StaticAnalysisData` MUST contain the successfully parsed `Windows` and `WindowTransitionGraph` with empty `Classes`

#### Scenario: Analysis result is cached

- **WHEN** `StaticAnalyzer._execute_command()` detects that the `.json` output file already exists
- **THEN** tool execution MUST be skipped
- **AND** a `CommandResult(0, b"", b"")` MUST be returned
- **AND** an info log with `execution_status='cached'` MUST be recorded

#### Scenario: Analysis timeout

- **WHEN** the analysis tool execution exceeds `analysis_timeout` (default: 600 seconds)
- **THEN** `Command` MUST kill the process tree via `kill_process_tree()`
- **AND** `StaticAnalysisResult.timed_out` MUST be set to `True`
- **AND** the `StaticAnalyzer` MUST log a warning with the tool name and timeout duration
- **AND** `StaticAnalysisResult.analysis_file` MUST be set to the expected output path (which may not exist)

#### Scenario: Timeout with partial JSON output

- **WHEN** the analysis tool times out after writing a partial JSON file (e.g., `reachability` section written and flushed, but `windows` and `transitions` sections missing due to timeout)
- **THEN** `StaticAnalysisParser` MUST attempt to parse the partial file. If `json.loads()` fails due to truncation, the parser MUST attempt recovery by finding the last complete `]` bracket, truncating the content there, closing the JSON object, and retrying
- **AND** valid sections present in the recovered JSON MUST be parsed successfully into their domain objects
- **AND** missing or truncated sections MUST result in empty domain objects for those sections (INV-ANA-06)
- **AND** a warning MUST be logged indicating incomplete file due to timeout
- **AND** `StaticAnalysisResult.timed_out` MUST be `True`

#### Scenario: Analysis output equivalence to previous 3-tool pipeline

- **WHEN** the analysis tool analyzes `cryptoapp.apk` and its output is compared against saved baseline from the previous 3-tool pipeline (GESDA + GATOR + REACH)
- **THEN** window count MUST match exactly (±0)
- **AND** transition count MUST match exactly (±0)
- **AND** total method count MUST match exactly (±0)
- **AND** `reachable` and `reachesMop` method counts MAY differ by up to ±10% due to the removal of `cg all-reachable` — differences MUST be documented
- **AND** `directlyReachesMop` counts MUST match exactly (±0) because direct call edges are CG-construction-independent
- **AND** widget `inputType` and `entries` fields MUST match GESDA output for the same APK

#### Scenario: Reachability data used as coverage denominator

- **WHEN** `CoverageTracker` or `CoverageAnalyzer` initializes with `StaticAnalysisData` containing `Classes` parsed from the analysis JSON's `reachability` section
- **THEN** the repository MUST be initialized with all classes and methods from the static data
- **AND** `method_coverage` MUST be calculated as: (called_methods) / (total_reachable_methods)
- **AND** `mop_method_coverage` MUST be calculated as: (called_mop_methods) / (total_methods_with_reaches_mop)
- **AND** these coverage calculations MUST use the `reachability` section from the analysis JSON as the method universe

## REMOVED Requirements

### Requirement: GATOR Analysis - Window Transition Graph (FR04)

**Reason**: Consolidated into the unified static analysis requirement above. The WTG extraction logic is now performed inside `RvsecAnalysisClient` as part of a single GATOR invocation, not as a standalone tool invocation. The `GatorParser` is deleted (P3: no backward compatibility).

### Requirement: GESDA Analysis - GUI Element Extraction (FR05)

**Reason**: Consolidated into the unified static analysis requirement above. Window and widget extraction is now performed by the single GATOR analysis client using GATOR's internal APIs (which provide the same data as GESDA's intra-procedural pattern matching, plus `inputType` and `entries` extracted from decoded layout XMLs). The `GesdaParser` is deleted (P3).

### Requirement: REACH Analysis - Method Reachability (FR06)

**Reason**: Consolidated into the unified static analysis requirement above. Reachability analysis is now performed inside the single GATOR analysis client using `Scene.v().getCallGraph()` + JGraphT, without the `cg all-reachable` misconfiguration that caused 10-100x performance degradation. The `ReachParser` is deleted (P3).
