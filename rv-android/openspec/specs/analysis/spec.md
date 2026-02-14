# Specification: Analysis and Coverage

## Purpose

The Analysis and Coverage domain encompasses three modules -- rv-static-analysis, rv-coverage, and rv-screen-parser -- that collectively provide the data foundation for the RV-Android system. These modules produce the static analysis data, runtime coverage metrics, and UI state representations that every other component in the pipeline depends on.

### Problem Context

Runtime verification of Android applications requires three categories of pre-computed data:

1. **Application structure data**: Before any test can run, the system needs to know which methods exist, which are reachable from entry points, and which have paths to monitored API methods. Without this, there is no denominator for coverage calculations and no basis for exploration prioritization.

2. **Runtime coverage data**: During test execution, the system needs real-time visibility into which methods have been exercised and which specification violations have occurred. This data is captured via logcat from the instrumented APK's Coverage.aj aspect and MOP monitors.

3. **UI state data**: For both LLM-driven and algorithmic exploration, the system needs structured representations of the current Android screen -- which elements exist, what actions are available, and where elements are positioned. Raw UIAutomator XML dumps are too verbose and unstructured for direct consumption.

### How This Domain Fits in the Pipeline

The three modules occupy distinct positions in the experiment lifecycle:

```
Pre-Processing Phase:
  APK -----> rv-static-analysis -----> StaticAnalysisData
                                        (Classes, Windows, WTG)

Execution Phase:
  Logcat -----> rv-coverage -----> CoverageTracker
                                    (method calls, RV errors, metrics)

  UIAutomator XML -----> rv-screen-parser -----> ScreenDescription
                                                  (items, actions, coordinates)
```

**rv-static-analysis** runs during the pre-processing phase of an experiment. It executes three external Java tools (GESDA, GATOR, REACH) against the original APK, producing JSON and CSV output files. The `StaticAnalysisParser` then parses these files into the unified `StaticAnalysisData` domain model. This data is consumed by:
- rv-coverage (to initialize the LogcatRepository with the known method universe)
- rv-agent (to guide exploration via WTG transitions and MOP reachability)
- rv-platform (to load static data as a TaskExecutor component)

**rv-coverage** runs during the execution phase, in parallel with tool execution. The `CoverageTracker` monitors a logcat file in a background thread, parsing each line for `RVSEC-COV` (coverage) and `RVSEC` (RV error) tags. It updates a `LogcatRepository` with method calls and violations, and provides real-time coverage metrics via logging. The `CoverageAnalyzer` provides batch (offline) analysis of logcat files with fallback modes when static analysis data is unavailable.

**rv-screen-parser** runs on demand during test execution. When the rv-agent or any UI-aware tool needs to understand the current screen state, it captures a UIAutomator2 XML hierarchy dump and passes it through a parser (UIAutomator2Parser or DroidBotParser) combined with a visitor (BasicTextVisitor, DefaultTextVisitor, or EnhancedTextVisitor). The visitor traverses the UI tree and produces a `ScreenDescription` containing `ScreenItem` objects with `ItemAction` objects. The BasicTextVisitor achieves approximately 69% token reduction compared to raw XML, which is critical for LLM prompt efficiency. The module also provides screenshot analysis via OpenCV and Tesseract for detecting visual elements not present in the UI hierarchy.

### Key Design Decisions

1. **REACH defines the method universe**: The total number of reachable methods from REACH output is the denominator for all coverage percentages. Without REACH data, coverage percentages cannot be computed (only absolute method call counts). The `CoverageAnalyzer` has explicit fallback modes for this scenario.

2. **GESDA is a prerequisite for REACH**: The analysis pipeline MUST execute GESDA before REACH, because REACH uses GESDA's application structure output. GATOR is independent and can run in parallel with GESDA.

3. **MOP means Monitored Operations, not security**: The term "MOP" refers to methods being monitored by ANY specification set (JCA cryptographic specifications or generic FSM specifications). The `reaches_mop` and `directly_reaches_mop` flags in REACH output indicate paths to monitored API methods, regardless of specification domain. Do NOT use "security" terminology when referring to MOP coverage.

4. **Coverage.aj logs via HashSet dedup**: The Coverage.aj aspect woven into instrumented APKs logs method calls via `Log.v("RVSEC-COV", signature)` with a `HashSet` to ensure each signature is logged only once per execution. The signature format is `<className: returnType methodName(params)>`. The `LogcatParser` also supports a legacy format (`class:::method:::params`) for backward compatibility.

5. **SignatureNormalizer for inner class notation**: Static analysis tools (Soot) use `$` for inner classes (`OuterClass$InnerClass`), but GESDA and GATOR output may use `.` notation (`OuterClass.InnerClass`). All three parsers (GatorParser, GesdaParser, ReachParser) use `SignatureNormalizer` to convert `.` to `$` based on Java naming convention heuristics (uppercase after separator indicates inner class).

6. **PackageDetector resolves manifest vs code package**: In approximately 27.5% of APKs, the AndroidManifest.xml package name differs from the actual code package (e.g., Godot games: manifest=`ir.hsn6.trans`, code=`org.godotengine.godot`). The `PackageDetector` uses a priority-based heuristic with 6 strategies: same-package check, game engine detection, single package, common prefix, frequency-based selection, and string similarity fallback. Static analysis parsers receive `code_package` (not `package_name`) for class filtering.

7. **Visitor pattern for extensible UI parsing**: The rv-screen-parser uses the visitor pattern with `Node.accept(visitor)` dispatching to element-specific methods (`visit_button`, `visit_edit_text`, etc.). This allows different visitors to produce different output formats without modifying the parser. The visitor handles 30+ Android widget classes including standard, AndroidX AppCompat, and Material Design components.

8. **Thread-safe real-time tracking**: The `CoverageTracker` runs in a background daemon thread with `RLock` protection. It uses file position tracking (seek to end, read new lines) to process logcat entries incrementally without re-reading processed data. Change detection optimizes CPU usage by only recalculating metrics when data has actually changed.

### Data Models

```
StaticAnalysisData:
  classes: Classes              # Collection of application classes and methods from REACH
  windows: Windows              # Collection of UI windows and widgets from GESDA
  wtg: WindowTransitionGraph    # Navigation graph from GATOR

Classes:
  classes: Dict[str, Clazz]     # Class name -> class info (is_activity, is_main_activity, methods)

Clazz:
  name: str                     # Fully qualified class name
  is_activity: bool             # True if this class is an Android Activity
  is_main_activity: bool        # True if this is the launcher Activity
  methods: Dict[str, Method]    # Method name -> method info

Method:
  class_name: str               # Owning class
  name: str                     # Method name
  params: List[str]             # Parameter types
  signature: str                # Full signature: <class: returnType method(params)>
  reachable: bool               # Reachable from framework entry points
  reaches_mop: bool             # Has path (direct or indirect) to a monitored API method
  directly_reaches_mop: bool    # Directly invokes a monitored API method

Windows:
  windows: Dict[str, Window]    # Window name -> window info
  widgets: Dict[str, Widget]    # Widget ID -> widget info

Window:
  name: str                     # Fully qualified activity/fragment class name
  id: str                       # GATOR window ID
  type: WindowType              # ACTIVITY, SERVICE, FRAGMENT, etc.
  activity: str                 # Activity class name
  class_name: str               # Class name
  layout_file: str              # Layout XML filename
  widgets: List[Widget]         # Widgets in this window

Widget:
  id: str                       # Widget ID
  name: str                     # Widget resource name
  type: WidgetType              # BUTTON, EDIT_TEXT, TEXT_VIEW, etc.
  events: Set[WidgetEvent]      # Event handlers registered on this widget
  text: str                     # Static text content
  hint: str                     # Hint text for input fields
  input_type: str               # Input type specification

WindowTransitionGraph:
  graph: networkx.DiGraph       # Directed graph of window transitions

WindowTransition:
  widget_id: str                # Widget that triggers this transition
  event: WidgetEventType        # Event type (CLICK, LONG_CLICK, etc.)
  handler: str                  # Handler method signature

RvCoverageLog:
  clazz: str                    # Fully qualified class name
  method: str                   # Method name
  params: str                   # Parameter types
  signature: str                # Full method signature
  time_occurred: datetime       # When the method was called
  time_since_task_start: int    # Seconds since tool execution started

RvErrorLog:
  spec: str                     # Specification name (e.g., CipherSpec, MessageDigestSpec)
  error_type: str               # Error classification
  class_full_name: str          # Class where violation occurred
  method: str                   # Method where violation was detected
  source: str                   # Source file or monitor location
  message: str                  # Violation description
  time_occurred: datetime       # When the violation was detected
  time_since_task_start: int    # Seconds since tool execution started

LogcatRepository:
  classes: Dict[str, ...]       # Known classes from static analysis
  errors: List[RvErrorLog]      # Registered RV errors
  # Provides: register_method_call(), register_rv_error(), calculate_metrics()

ScreenDescription:
  activity: str                 # Current activity name
  items: List[ScreenItem]       # All UI elements with actions
  events_by_id: Dict[int, ItemAction]  # Action ID -> action lookup

ScreenItem:
  view: Dict[str, Any]          # Raw UI element data
  base_description: str         # Human-readable element description
  actions: List[ItemAction]     # Available actions for this element
  complement: Dict[str, Any]    # Additional metadata

ItemAction:
  id: int                       # Unique action ID within screen
  text: str                     # Action description
  event: WidgetEventType        # Widget event type
  reaches_mop: bool             # Action reaches monitored operations
  directly_reaches_mop: bool    # Action directly reaches monitored operations
  target_view: Dict[str, Any]   # Target element properties
  coordinates: Tuple[int, int]  # Explicit action coordinates
  widget_id: str                # Target widget ID
  callback_signature: str       # Callback method signature
  text_input: str               # Text value for TEXT_CHANGE actions
  action_type: str              # Computed: click, set_text, scroll, etc.
  coords_for_matching: Tuple    # Computed: ((x, y), action_type) signature

Node:
  data: Dict[str, Any]          # Raw UI element data from UIAutomator
  children: List[Node]          # Child nodes in UI hierarchy
  parent: Node                  # Parent node reference
  clickable: bool               # Supports click
  scrollable: bool              # Supports scroll
  editable: bool                # Supports text editing
  view_class: str               # Android widget class name
  bounds: List[List[int]]       # Bounding box [[x1,y1],[x2,y2]]
  actionable: bool              # Computed: supports any interaction

PackageDetectionResult:
  manifest_package: str         # Package from AndroidManifest.xml
  code_package: str             # Detected implementation package
  confidence: str               # "high", "medium", "low"
  detection_method: str         # Heuristic that produced the result
  all_packages: List[str]       # All candidate packages found
  similarity_score: float       # Similarity score (0.0-1.0) if similarity_match
  game_engine: str              # Detected game engine name, if any

StaticAnalysisResult:
  gesda_file: str               # Path to GESDA output file
  gator_file: str               # Path to GATOR WTG output file
  reach_file: str               # Path to REACH reachability output file
  success: bool                 # Overall pipeline success
  errors: List[str]             # Error messages during analysis
  execution_times: Dict[str, float]  # Per-tool execution times in seconds

CoverageCalculationMode:
  FULL_STATIC_ANALYSIS          # Complete static data available
  PARTIAL_STATIC_ANALYSIS       # Limited static data (< 10 methods)
  RUNTIME_ONLY                  # No static data, only runtime
  FALLBACK_MODE                 # Minimal functionality
```

### Cross-Domain Dependencies

```
rv-static-analysis:
  Depends on: rv-android-core (App, Classes, Windows, WTG, ErrorHandler, LoggingManager)
  Consumed by: rv-platform (StaticAnalysisComponent), rv-agent (TransitionManager, MOP prioritization),
               rv-coverage (repository initialization), rv-experiment (pre-processing phase)

rv-coverage:
  Depends on: rv-android-core (LogcatRepository, RvErrorLog, RvCoverageLog)
  Consumed by: rv-platform (CoverageComponent), rv-experiment (post-processing)

rv-screen-parser:
  Depends on: rv-android-core (StaticAnalysisData for MOP tracking, WidgetEventType, ErrorHandler)
  Consumed by: rv-agent (ScreenProcessor), rv-uiautomator (device interaction),
               rv-agent-validation (benchmark framework)
```

## Data Contracts

### Input

- `apk_path: str` -- Path to Android APK file (source: rv-experiment or user, consumed by StaticAnalyzer)
- `code_package: str` -- Application code package name (source: App.code_package via PackageDetector, consumed by all static analysis parsers for class filtering)
- `rvsec_root: str` -- Path to RVSEC installation (source: RVSEC_HOME env var or explicit, consumed by RVStaticAnalysisConfig for tool path resolution)
- `mop_dir: str` -- Path to MOP specification directory (source: RVStaticAnalysisConfig, consumed by REACH tool)
- `logcat_file: str` -- Path to Android logcat output file (source: LogcatComponent in rv-platform, consumed by CoverageTracker and CoverageAnalyzer)
- `static_data: StaticAnalysisData` -- Parsed static analysis data (source: StaticAnalyzer.get_static_data(), consumed by CoverageTracker for repository initialization)
- `xml_data: str` -- UIAutomator2 XML hierarchy dump string (source: uiautomator2 device.dump_hierarchy(), consumed by UIAutomator2Parser)
- `screenshot_path: str` -- Path to screenshot image file (source: device screenshot capture, consumed by ScreenshotAnalyzer)
- `task_start_time: datetime` -- Tool execution start time (source: rv-platform TaskExecutor, consumed by CoverageTracker for relative timing)
- `task_id: str` -- Task identifier for event correlation (source: rv-platform, consumed by CoverageTracker)

### Output

- `StaticAnalysisData` -- Unified static analysis results containing Classes, Windows, and WTG (destination: rv-platform StaticAnalysisComponent, rv-agent, rv-coverage)
- `StaticAnalysisResult` -- Analysis pipeline status with file paths, execution times, and errors (destination: rv-experiment pre-processing)
- `Dict[str, float]` -- Coverage metrics dictionary with method_coverage, activity_coverage, mop_method_coverage, called_methods, total_errors (destination: rv-platform CoverageComponent)
- `ScreenDescription` -- Complete screen state with items, actions, and coordinates (destination: rv-agent ScreenProcessor, LLM prompt generation)
- `ScreenshotAnalysisResult` -- Visual analysis results with detected texts, buttons, errors, and interactive elements (destination: rv-agent screenshot analysis)
- `PackageDetectionResult` -- Package detection result with code_package, confidence, and detection method (destination: App.code_package property)

### Side-Effects

- **File System (GESDA)**: Creates `{app_name}.gesda` JSON file in output directory containing application structure
- **File System (GATOR)**: Creates `{app_name}.wtg` JSON file in output directory containing window transition graph
- **File System (REACH)**: Creates `{app_name}.reach` CSV file in output directory containing method reachability data
- **File System (logcat)**: CoverageTracker creates empty logcat file if it does not exist
- **Background Thread**: CoverageTracker starts a daemon thread for continuous logcat monitoring; thread terminates on stop() or context manager exit

### Error

- `StaticAnalysisException` -- Raised when a static analysis tool (GESDA, GATOR, or REACH) returns a non-zero exit code. Contains tool name, exit code, and stderr output. Handled by StaticAnalyzer.analyze() which sets result.success=False.
- `ConfigurationError` -- Raised by RVStaticAnalysisConfig when required paths are missing, tool JARs are not found, Android SDK is not configured, or MOP directory does not exist.
- `ValueError` -- Raised by ItemAction coordinate validation when coordinates are not a 2-element integer tuple or contain negative values.
- Parser errors (all three parsers) -- Caught internally and logged; parsers return empty domain objects (empty Classes, empty Windows, empty WindowTransitionGraph) on failure rather than propagating exceptions.

## Invariants

- **INV-ANA-01**: GESDA analysis MUST complete before REACH analysis begins. REACH depends on GESDA output for application structure data. GATOR MAY execute independently of GESDA and REACH.

- **INV-ANA-02**: All static analysis parsers (GatorParser, GesdaParser, ReachParser) MUST apply `SignatureNormalizer` to class names and method signatures before storing them in domain models. The normalization converts inner class dot notation (`OuterClass.InnerClass`) to dollar notation (`OuterClass$InnerClass`) using Java naming convention heuristics.

- **INV-ANA-03**: Static analysis parsers MUST receive `code_package` (from `App.code_package`, detected by `PackageDetector`) for class filtering, NOT `package_name` (from AndroidManifest.xml). This ensures correct behavior for APKs where the manifest package differs from the implementation package.

- **INV-ANA-04**: The `CoverageTracker` MUST log coverage metric updates whenever coverage metrics change. It MUST log MOP error detections immediately when an RV error is detected. Log entries MUST include the `task_id` if one was provided during initialization.

- **INV-ANA-05**: The `CoverageTracker` MUST be thread-safe. All shared state access MUST be protected by the `_reader_lock` (RLock). The background monitoring thread MUST be a daemon thread that terminates when stop() is called or the context manager exits.

- **INV-ANA-06**: Static analysis parsers MUST NOT propagate exceptions to callers. On parse failure, they MUST log the error and return empty domain objects: `Classes()` for ReachParser, `Windows()` for GesdaParser, `WindowTransitionGraph()` for GatorParser. The `StaticAnalysisParser` facade applies the same graceful degradation per-parser.

- **INV-ANA-07**: The `LogcatParser` MUST support two coverage message formats: the modern format (`<class: returnType method(params)>`) and the legacy format (`class:::method:::params`). Both formats MUST produce valid `RvCoverageLog` instances.

- **INV-ANA-08**: The `LogcatParser` MUST support three error message formats: the standard JCA format (comma-separated: `spec,class,init,method,source,error_type,message`), the FSM format (`class.method():::Spec went into an error state.`), and the generic format (`class.method(file:line) ::: Spec went into an error state.`). Malformed messages MUST be logged as warnings and return None, not malformed data.

- **INV-ANA-09**: The `ItemAction.action_type` computed property MUST derive the action type from `WidgetEventType` as the single source of truth, using the `WIDGET_EVENT_TO_ACTION_TYPE` mapping. Text parsing MUST only be used for scroll direction refinement (scroll_up, scroll_down, scroll_left, scroll_right), never for primary type classification.

- **INV-ANA-10**: The `ScreenDescription` MUST build an `events_by_id` mapping from all `ItemAction` objects across all `ScreenItem` elements. The `get_action_by_id()` method MUST return the correct `ItemAction` for any valid ID within the screen context.

- **INV-ANA-11**: The `StaticAnalyzer` MUST implement intelligent caching: if an output file already exists, the corresponding tool execution MUST be skipped. A `CommandResult(0, b"", b"")` MUST be returned for cached results.

- **INV-ANA-12**: The `Node.accept(visitor)` method MUST dispatch to element-specific visitor methods based on `view_class` (e.g., `visit_button` for `android.widget.Button`). System navigation buttons (navbar, status bar) MUST be filtered by calling `visitor.should_exclude_system_button(node)` for leaf nodes only, never for container nodes. Container filtering would exclude all children.

- **INV-ANA-13**: `ItemAction.coordinates` MUST be validated as a non-negative integer tuple of exactly 2 elements `(x, y)`, or None. The `get_execution_coordinates()` method MUST resolve coordinates using priority: (1) explicit coordinates, (2) target view bounds center.

- **INV-ANA-14**: The `PackageDetector` MUST apply detection heuristics in the following priority order: (1) same-as-manifest, (2) game engine detection, (3) single package, (4) common prefix, (5) most common (60%+ frequency), (6) string similarity (85%+ threshold), (7) manifest fallback. Each strategy returns early if a match is found.

- **INV-ANA-15**: Coverage metrics MUST be calculated with REACH data as the denominator. `method_coverage` = (called methods) / (total reachable methods from REACH). `mop_method_coverage` = (called methods that reach MOP) / (total methods with reaches_mop=true from REACH). Without REACH data, percentage-based coverage MUST NOT be reported; only absolute counts are valid.

## Requirements

### Requirement: GATOR Analysis - Window Transition Graph (FR04)

The system MUST run GATOR static analysis to produce a Window Transition Graph (WTG) representing the navigation structure of an Android application. GATOR is a program analysis toolkit that performs static analysis of the application's UI to construct a directed graph where nodes represent windows (Activities, Fragments) and edges represent transitions triggered by user events (click, long_click, scroll, selection, etc.).

The WTG is consumed by rv-agent's `TransitionManager` to guide exploration toward unvisited windows, and by the `WtgScorer` to boost the ranking of actions that correspond to known transitions. Without GATOR data, exploration falls back to purely algorithmic or LLM-driven strategies without navigation guidance.

GATOR execution involves a Python script (`gator`) that orchestrates a Java client JAR (`rvsec-gator-client.jar`) with the `RvsecWtgClient` mode. The output is a JSON file containing windows (with IDs and names) and transitions (with source/target IDs, events, widget IDs, event types, and handler signatures).

The `GatorParser` processes this JSON output into domain objects. For each window, it normalizes the class name via `SignatureNormalizer`, adds it to the `Classes` collection if it belongs to the application package, and creates or retrieves a `Window` object. For each transition, it resolves source and target windows by ID, processes events to create `Widget` objects with `WidgetEvent` entries, and adds `WindowTransition` edges to the `WindowTransitionGraph`.

GATOR is independent of GESDA and MAY run in parallel with it.

#### Scenario: Successful GATOR analysis with valid APK

- **WHEN** StaticAnalyzer._run_gator() is called with a valid APK path and output file path
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <client_jar> --out <output_file> -client RvsecWtgClient`
- **AND** the resulting `.wtg` JSON file MUST be parseable by GatorParser into a WindowTransitionGraph

#### Scenario: GATOR output parsing with inner class normalization

- **WHEN** GatorParser encounters a window name like `com.example.OuterActivity.InnerFragment`
- **THEN** SignatureNormalizer MUST convert it to `com.example.OuterActivity$InnerFragment`
- **AND** the normalized class name MUST be used for Classes collection lookup and Window creation

#### Scenario: GATOR output with widget events

- **WHEN** GatorParser processes a transition containing events with widget IDs and handler signatures
- **THEN** each event MUST be converted to a `WidgetEventType` using the mapping (click events -> CLICK, long_click events -> LONG_CLICK, scroll -> SCROLL, etc.)
- **AND** events with type OTHER MUST be skipped
- **AND** widgets not yet in the Windows collection MUST be created with `WidgetType.from_class_name(widgetClass)`
- **AND** widgets with type OTHER MUST be skipped (create_widget returns None)

#### Scenario: GATOR output file does not exist

- **WHEN** GatorParser.parse_file() is called with a non-existent file path
- **THEN** a warning MUST be logged
- **AND** an empty `WindowTransitionGraph()` MUST be returned

#### Scenario: GATOR analysis result is cached

- **WHEN** StaticAnalyzer._execute_command() detects that the `.wtg` output file already exists
- **THEN** tool execution MUST be skipped
- **AND** a `CommandResult(0, b"", b"")` MUST be returned
- **AND** an info log with execution_status='cached' MUST be recorded

### Requirement: GESDA Analysis - GUI Element Extraction (FR05)

The system MUST run GESDA analysis to extract GUI elements including activities, widgets, and event listeners from Android applications. GESDA (GUI Element Static Detection for Android) analyzes application bytecode to produce a comprehensive inventory of UI components, their properties, and registered event handlers.

GESDA output is consumed directly by REACH analysis (as a prerequisite), by rv-agent for widget information, and by the `StaticAnalysisParser` for building the `Windows` domain model. GESDA provides the widget-level detail that GATOR does not: text content, hint text, input types, layout file associations, and listener-to-callback method mappings.

GESDA execution is a Java JAR (`rvsec-gesda.jar`) invoked with the APK path, Android SDK platforms directory, Java rt.jar path, and output file path. The output is a JSON file containing windows with type (ACTIVITY, SERVICE, etc.), isMain flag, layout file name, and widgets with IDs, names, types, text, hints, input types, and listener arrays.

The `GesdaParser` processes this JSON output. For each window, it normalizes the class name, verifies the window belongs to the application package (via `code_package` filtering), creates the Window object with type and layout information, and parses widgets with their event listeners. Listeners are mapped to `WidgetEventType` values (OnClickListener -> CLICK, OnLongClickListener -> LONG_CLICK, OnScrollListener -> SCROLL, etc.).

#### Scenario: Successful GESDA analysis with valid APK

- **WHEN** StaticAnalyzer._run_gesda() is called with a valid APK path
- **THEN** the system MUST execute: `java -jar rvsec-gesda.jar --android-dir <platforms_dir> --rt-jar <rt_jar> --output <output_file> --apk <apk_path>`
- **AND** the resulting `.gesda` JSON file MUST be parseable by GesdaParser into Windows and Widget objects

#### Scenario: GESDA parser filters by code_package

- **WHEN** GesdaParser.process_window() encounters a window with class_name not containing the `code_package` string
- **THEN** the window MUST be skipped with a warning log
- **AND** no Window or Widget objects MUST be created for that entry

#### Scenario: GESDA widget listener parsing

- **WHEN** GesdaParser.parse_listeners() processes a widget's listener array
- **THEN** each listener type MUST be mapped to a WidgetEventType (OnClickListener -> CLICK, OnLongClickListener -> LONG_CLICK, OnScrollListener -> SCROLL, OnItemSelectedListener -> SELECTION, etc.)
- **AND** listeners mapping to WidgetEventType.OTHER MUST be excluded
- **AND** each valid listener MUST produce a WidgetEvent with event_type, className, method name, and callback signature

#### Scenario: GESDA output file does not exist

- **WHEN** GesdaParser.parse_file() is called with a non-existent file path
- **THEN** a warning MUST be logged
- **AND** the existing `windows` parameter (or empty `Windows()`) MUST be returned unchanged

### Requirement: REACH Analysis - Method Reachability (FR06)

The system MUST run REACH analysis to compute method reachability information relative to MOP specifications. REACH determines, for each method in the application, three boolean properties: `reachable` (reachable from Android framework entry points), `reaches_mop` (has a direct or indirect call path to a monitored API method), and `directly_reaches_mop` (directly invokes a monitored API method).

REACH defines the **method universe** -- the total set of reachable methods that serves as the denominator for all coverage percentage calculations. This is critical: without REACH data, the system can count absolute method calls but cannot compute coverage percentages (method_coverage, mop_method_coverage). The `CoverageAnalyzer` explicitly switches to `RUNTIME_ONLY` or `FALLBACK_MODE` when REACH data is unavailable.

REACH also provides the MOP prioritization data consumed by rv-agent. The `MopScorer` in rv-agent's `ActionRanker` assigns +100 score to actions with `directly_reaches_mop=true` and +50 to actions with `reaches_mop=true`, directing exploration toward MOP-relevant code paths.

REACH execution requires GESDA output as input. It is a Java JAR (`rvsec-reach.jar`) invoked with the APK path, Android SDK, rt.jar, MOP specification directory, GESDA output file, writer format (CSV), timeout (default 300s), and output path. The output is a CSV file with columns: class, isActivity, isMainActivity, method, params, reachable, reachesMop, directlyReachesMop, signature.

The `ReachParser` processes this CSV. For each row, it normalizes the class name, creates a `Clazz` object (with activity flags), and creates a `Method` object with all reachability flags. Parameters are parsed from a bracket-and-semicolon format (`[param1;param2;...]`). Signatures are normalized via `SignatureNormalizer`.

#### Scenario: Successful REACH analysis with GESDA prerequisite

- **WHEN** StaticAnalyzer._run_reachability() is called after GESDA analysis has completed
- **THEN** the system MUST execute: `java -jar rvsec-reach.jar --android-dir <platforms_dir> --rt-jar <rt_jar> --mop-dir <mop_dir> --gesda <gesda_file> --writer csv --timeout 300 --apk <apk_path> --output <output_file>`
- **AND** the `--gesda` argument MUST point to the GESDA output file from the same analysis run

#### Scenario: REACH CSV parsing with reachability flags

- **WHEN** ReachParser.read_file() processes a CSV row: `com.example.App,true,true,doEncrypt,[javax.crypto.Cipher],true,true,true,<com.example.App: void doEncrypt(javax.crypto.Cipher)>`
- **THEN** a Clazz MUST be created with name=`com.example.App`, is_activity=true, is_main_activity=true
- **AND** a Method MUST be created with reachable=true, reaches_mop=true, directly_reaches_mop=true
- **AND** params MUST be parsed as `["javax.crypto.Cipher"]`
- **AND** the signature MUST be normalized by SignatureNormalizer

#### Scenario: REACH data used as coverage denominator

- **WHEN** CoverageTracker or CoverageAnalyzer initializes with StaticAnalysisData containing REACH-parsed Classes
- **THEN** the repository MUST be initialized with all classes and methods from static data
- **AND** method_coverage MUST be calculated as: (called_methods) / (total_reachable_methods)
- **AND** mop_method_coverage MUST be calculated as: (called_mop_methods) / (total_methods_with_reaches_mop)

#### Scenario: REACH output file does not exist

- **WHEN** ReachParser.parse_file() is called with a non-existent file path
- **THEN** a warning MUST be logged
- **AND** the existing `classes` parameter (or empty `Classes()`) MUST be returned unchanged

#### Scenario: Coverage without REACH data (fallback)

- **WHEN** CoverageAnalyzer is initialized without StaticAnalysisData or with empty Classes
- **THEN** calculation_mode MUST be set to RUNTIME_ONLY or FALLBACK_MODE
- **AND** coverage percentage metrics MUST be reported as 0.0 (unavailable)
- **AND** only absolute counts (called_methods, total_errors) MUST be valid

### Requirement: Method Coverage Tracking (FR12, NFR06)

The system MUST track method coverage in real-time during test execution via the `CoverageTracker`, and provide batch analysis via the `CoverageAnalyzer`. Coverage tracking relies on the instrumented APK's Coverage.aj aspect, which logs unique method signatures to Android logcat using the `RVSEC-COV` tag.

The `CoverageTracker` monitors a logcat file in a background daemon thread. It reads new lines incrementally (using file position tracking to avoid re-reading), parses each line via `parse_logcat_line()`, and registers method calls in the `LogcatRepository`. When initialized with `StaticAnalysisData`, the repository is populated with the known method universe from REACH, enabling percentage-based coverage calculation.

Two types of coverage are tracked:
- **Overall method coverage**: Percentage of all reachable application methods exercised during testing. Best observed: 26.77% (Humanoid at 300s) in the ICST study.
- **MOP method coverage**: Percentage of methods with paths to monitored API methods exercised during testing. Best observed: 17.16% (Humanoid at 300s).

The `CoverageTracker` logs coverage metric updates when metrics change, including method_coverage, activity_coverage, mop_method_coverage, called_methods, total_activities, and unique_errors. It uses change detection to avoid redundant metric calculations and logging.

The `CoverageAnalyzer` provides offline analysis with four calculation modes: FULL_STATIC_ANALYSIS (complete static data), PARTIAL_STATIC_ANALYSIS (limited data, < 10 methods), RUNTIME_ONLY (no static data), and FALLBACK_MODE (minimal functionality). It can process logcat files, individual RvCoverageLog entries, RvErrorLog entries, or lists thereof.

#### Scenario: Real-time coverage tracking with CoverageTracker

- **WHEN** CoverageTracker is started with a logcat file path and static analysis data
- **THEN** a daemon background thread MUST be started to monitor the logcat file
- **AND** existing lines in the file MUST be processed first
- **AND** the file position MUST be moved to the end after initial processing
- **AND** new lines MUST be read and processed in a continuous loop with adaptive sleep (0.5s with data, 1.0s without)

#### Scenario: Coverage log parsing (modern format)

- **WHEN** a logcat line contains `RVSEC-COV: <com.example.App: void doEncrypt(javax.crypto.Cipher)>`
- **THEN** parse_logcat_line() MUST return a RvCoverageLog with clazz=`com.example.App`, method=`doEncrypt`, params=`javax.crypto.Cipher`
- **AND** CoverageTracker MUST register the method call in LogcatRepository
- **AND** _data_changed_since_last_update MUST be set to True

#### Scenario: Coverage log parsing (legacy format)

- **WHEN** a logcat line contains `RVSEC-COV: com.example.App:::doEncrypt:::javax.crypto.Cipher`
- **THEN** parse_logcat_line() MUST return a RvCoverageLog with clazz=`com.example.App`, method=`doEncrypt`, params=`javax.crypto.Cipher`

#### Scenario: CoverageTracker context manager lifecycle

- **WHEN** CoverageTracker is used as a context manager (`with tracker.track_coverage() as t:`)
- **THEN** start() MUST be called on entry
- **AND** stop() MUST be called on exit (including on exception)
- **AND** the background thread MUST join with a 5-second timeout on stop()

#### Scenario: CoverageAnalyzer batch processing of logcat file

- **WHEN** CoverageAnalyzer.analyze() is called with a logcat file path string
- **THEN** it MUST delegate to process_logcat_file()
- **AND** all errors from the parsed repository MUST be transferred to the analyzer's repository
- **AND** the returned metrics dictionary MUST include method_coverage, activities_coverage, methods_jca_reachable_coverage, total_errors, and total_method_calls

### Requirement: Specification Violation Detection (FR13)

The system MUST detect and record violations of MOP specifications (RV errors) reported via logcat during test execution. Violations are logged by the runtime monitors woven into the instrumented APK, using the `RVSEC` logcat tag. The `CoverageTracker` detects these violations in real-time and logs them immediately.

Three error message formats are supported by the `LogcatParser`:

1. **Standard (JCA) format**: `spec,class,init,method,source,error_type,message` -- Used by JCA specification monitors. Example: `CipherSpec,com.example.Crypto,<init>,doEncrypt,Crypto.java,MISUSE,Algorithm not allowed`

2. **FSM format**: `class.method():::Spec went into an error state.` -- Used by FSM-based generic specifications. Example: `java.util.Iterator.next():::HasNext went into an error state.`

3. **Generic format**: `class.method(file:line) ::: Spec went into an error state.` -- Used by generic specifications with source location. Example: `com.example.IO.read(IO.java:42) ::: InputStream_ManipulateAfterClose went into an error state.`

Each parsed error produces an `RvErrorLog` with spec, error_type, class_full_name, method, source, and message fields. The `LogcatRepository` stores all registered errors and provides deduplication via the `unique_msg` computed field.

In the ICST study, the top 4 violation classes (SSLContextSpec, MessageDigestSpec, CipherSpec, SecretKeySpecSpec) accounted for 78% of 230 unique violations. 33.91% originated from application code; the rest from external libraries.

#### Scenario: Standard (JCA) error format parsing

- **WHEN** a logcat line contains `RVSEC: CipherSpec,com.example.Crypto,<init>,doEncrypt,Crypto.java:15,MISUSE,Using weak algorithm DES`
- **THEN** parse_logcat_line() MUST return an RvErrorLog with spec=`CipherSpec`, class_full_name=`com.example.Crypto`, method=`doEncrypt`, error_type=`MISUSE`

#### Scenario: FSM error format parsing

- **WHEN** a logcat line contains `RVSEC: java.util.Iterator.next():::HasNext went into an error state.`
- **THEN** parse_logcat_line() MUST return an RvErrorLog with spec=`HasNext`, class_full_name=`java.util.Iterator`, method=`next`

#### Scenario: Generic error format parsing

- **WHEN** a logcat line contains `RVSEC: com.example.IO.read(IO.java:42) ::: InputStream_ManipulateAfterClose went into an error state.`
- **THEN** parse_logcat_line() MUST return an RvErrorLog with spec=`InputStream_ManipulateAfterClose`, class_full_name=`com.example.IO`, method=`read`, source=`IO.java`

#### Scenario: MOP error detection and registration

- **WHEN** CoverageTracker processes a logcat line that yields an RvErrorLog
- **THEN** the error MUST be registered in LogcatRepository via register_rv_error()
- **AND** a log entry MUST be emitted with spec, error_type, class_full_name, method, message, and time_since_task_start

#### Scenario: Malformed error message handling

- **WHEN** a logcat line contains `RVSEC: some malformed message that does not match any format`
- **THEN** _parse_error_message() MUST log a warning
- **AND** MUST return None (not a malformed RvErrorLog)
- **AND** CoverageTracker MUST NOT register any error

#### Scenario: Logcat timestamp to datetime conversion with year handling

- **WHEN** a logcat line has date `12-31` and is parsed in January of the following year
- **THEN** _convert_to_datetime() MUST attribute the log to the previous year
- **AND** all other months MUST use the current year

### Requirement: UI Screen Parsing (FR23 - Analysis Component)

The rv-screen-parser module MUST parse Android UI state from UIAutomator2 XML hierarchy dumps and DroidBot JSON state data into standardized `ScreenDescription` objects. The parsing system uses a factory pattern for parser selection and a visitor pattern for UI tree traversal, producing structured output suitable for LLM consumption and algorithmic exploration.

The `UIAutomator2Parser` handles XML dumps from the `uiautomator2` library. It converts XML elements into a tree of `Node` objects, where each Node extracts properties (clickable, scrollable, editable, text, bounds, resource_id, etc.) from the XML attributes. The parser then applies a visitor to the node tree.

The visitor pattern is the core of the transformation. `AbstractScreenVisitor` defines the interface with element-specific methods (`visit_button`, `visit_edit_text`, `visit_checkbox`, etc.) and common infrastructure (MOP tracking via StaticAnalysisData, system button filtering for navbar/status bar elements). Three concrete visitors are provided:

- **BasicTextVisitor**: Produces compact descriptions optimized for LLM token efficiency, achieving approximately 69% reduction compared to raw XML. This is the default visitor used by rv-agent.
- **DefaultTextVisitor**: Standard visitor with default formatting.
- **EnhancedTextVisitor**: Comprehensive analysis with detailed coordinate information.

The `Node.accept(visitor)` method implements the dispatch. For leaf nodes, it checks `should_exclude_system_button()` and then dispatches to the appropriate `visit_*` method based on `view_class`, falling back to `visit_leaf_node` for unmapped classes. For container nodes, it handles specialized containers (Spinner, RadioGroup, ChipGroup) and recursively traverses children. Container nodes are NOT filtered for system buttons because containers often span the full screen height.

Each visitor produces `ScreenItem` objects containing `ItemAction` objects. The `ItemAction` carries MOP tracking flags (`reaches_mop`, `directly_reaches_mop`) derived from the static analysis `WidgetEvent` data when available.

#### Scenario: UIAutomator XML parsing to ScreenDescription

- **WHEN** UIAutomator2Parser.parse() is called with a valid XML string and activity name
- **THEN** it MUST produce a ScreenDescription with the correct activity
- **AND** each actionable XML element MUST be represented as a ScreenItem with appropriate ItemActions
- **AND** the events_by_id mapping MUST contain all ItemAction objects indexed by their unique IDs

#### Scenario: Visitor pattern dispatch for widget types

- **WHEN** Node.accept(visitor) is called on a leaf node with view_class `android.widget.Button`
- **THEN** the visitor's `visit_button(node)` method MUST be called
- **AND** for `android.widget.EditText`, `visit_edit_text(node)` MUST be called
- **AND** for `com.google.android.material.button.MaterialButton`, `visit_button(node)` MUST be called (Material Design mapping)
- **AND** for unknown classes, `visit_leaf_node(node)` MUST be called as fallback

#### Scenario: System button filtering for leaf nodes only

- **WHEN** Node.accept(visitor) is called on a leaf node that the visitor identifies as a system button (navbar, status bar)
- **THEN** the node MUST be skipped (no visitor method called)
- **AND** WHEN Node.accept(visitor) is called on a container node that spans the full screen
- **THEN** the container MUST NOT be filtered; all its children MUST be processed recursively

#### Scenario: MOP tracking in ItemAction

- **WHEN** a visitor creates an ItemAction for a widget that has WidgetEvent data from StaticAnalysisData
- **THEN** the ItemAction's reaches_mop and directly_reaches_mop flags MUST reflect the corresponding WidgetEvent callback method's reachability flags
- **AND** the widget_id and callback_signature fields SHOULD be populated from the WidgetEvent data

#### Scenario: ItemAction coordinate resolution

- **WHEN** ItemAction.get_execution_coordinates() is called on an action with explicit coordinates (540, 960)
- **THEN** it MUST return (540, 960) directly
- **AND** WHEN the action has no explicit coordinates but has target_view with bounds [[100, 200], [300, 400]]
- **THEN** it MUST return the center point (200, 300)

#### Scenario: ScreenDescription action lookup by ID

- **WHEN** ScreenDescription.get_action_by_id(5) is called
- **THEN** it MUST return the ItemAction with id=5 if it exists in any ScreenItem
- **AND** it MUST return None if no action with that ID exists
