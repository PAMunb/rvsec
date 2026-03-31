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
                                        (Classes, Windows, WTG, Components)

Execution Phase:
  Logcat -----> rv-coverage -----> CoverageTracker
                                    (method calls, RV errors, metrics)

  UIAutomator XML -----> rv-screen-parser -----> ScreenDescription
                                                  (items, actions, coordinates)
```

The end-to-end pipeline from static analysis through execution to coverage calculation:

```mermaid
sequenceDiagram
    participant Pre as PreProcessor
    participant SA as StaticAnalyzer
    participant GATOR as GATOR/RvsecAnalysisClient
    participant JSON as analysis JSON
    participant Parser as StaticAnalysisParser
    participant SAC as StaticAnalysisComponent
    participant CT as CoverageTracker
    participant Agent as rv-agent
    participant APK as Instrumented APK
    participant LC as .logcat file
    participant RP as ResultProcessor

    Note over Pre,GATOR: Pre-Processing Phase
    Pre->>SA: analyze(apk_path)
    SA->>GATOR: execute via gator launcher
    GATOR->>JSON: write {reachability, windows, transitions}
    SA-->>Pre: StaticAnalysisResult(analysis_file)

    Note over SAC,CT: Task Initialization
    SAC->>JSON: copy to task results dir
    SAC->>Parser: parse_file(json_path, code_package)
    Parser-->>SAC: StaticAnalysisData(Classes, Windows, WTG, Components)
    SAC->>CT: initialize(static_data)
    CT->>CT: build LogcatRepository (method universe)

    Note over Agent,LC: Execution Phase
    CT->>LC: start monitoring (background thread)
    Agent->>APK: explore via UIAutomator
    APK->>LC: Coverage.aj logs RVSEC-COV signatures
    APK->>LC: MOP monitors log RVSEC errors
    CT->>LC: read new lines (incremental)
    CT->>CT: register_method_call / register_rv_error

    Note over CT,RP: Post-Processing Phase
    CT->>CT: calculate_metrics()
    CT-->>RP: coverage dict (method%, activity%, mop%)
    RP->>RP: generate CSV, JSON results
```

**rv-static-analysis** runs during the pre-processing phase of an experiment. It executes a single GATOR analysis client (`RvsecAnalysisClient`) against the original APK, producing a single JSON output file containing reachability data, window/widget inventory, and window transition graph. The `StaticAnalysisParser` then parses this file into the unified `StaticAnalysisData` domain model. This data is consumed by:
- rv-coverage (to initialize the LogcatRepository with the known method universe)
- rv-agent (to guide exploration via WTG transitions and MOP reachability)
- rv-platform (to load static data as a TaskExecutor component)

**rv-coverage** runs during the execution phase, in parallel with tool execution. The `CoverageTracker` monitors a logcat file in a background thread, parsing each line for `RVSEC-COV` (coverage) and `RVSEC` (RV error) tags. It updates a `LogcatRepository` with method calls and violations, and provides real-time coverage metrics via logging. The `CoverageAnalyzer` provides batch (offline) analysis of logcat files with fallback modes when static analysis data is unavailable.

**rv-screen-parser** runs on demand during test execution. When the rv-agent or any UI-aware tool needs to understand the current screen state, it captures a UIAutomator2 XML hierarchy dump and passes it through a parser (UIAutomator2Parser or DroidBotParser) combined with a visitor (BasicTextVisitor, DefaultTextVisitor, or EnhancedTextVisitor). The visitor traverses the UI tree and produces a `ScreenDescription` containing `ScreenItem` objects with `ItemAction` objects. The BasicTextVisitor achieves approximately 69% token reduction compared to raw XML, which is critical for LLM prompt efficiency. The module also provides screenshot analysis via OpenCV and Tesseract for detecting visual elements not present in the UI hierarchy.

### Key Design Decisions

1. **Reachability defines the method universe**: The total number of reachable methods from the analysis JSON's `reachability` section is the denominator for all coverage percentages. Without reachability data, coverage percentages cannot be computed (only absolute method call counts). The `CoverageAnalyzer` has explicit fallback modes for this scenario.

2. **Single GATOR analysis client**: A single GATOR invocation (`RvsecAnalysisClient`) produces all four data sections (reachability, windows, transitions, components) in one JSON file. The client writes sections in priority order: reachability first (coverage denominator), then windows, then transitions, then components (non-Activity component data with intent-filters, exported status, and MOP reachability). Entry points include all four Android component types: Activity lifecycle handlers, Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`), BroadcastReceiver (`onReceive`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`). On timeout, partial JSON preserves the most critical data first.

3. **MOP means Monitored Operations, not security**: The term "MOP" refers to methods being monitored by ANY specification set (JCA cryptographic specifications or generic FSM specifications). The `reaches_mop` and `directly_reaches_mop` flags in the reachability section indicate paths to monitored API methods, regardless of specification domain. Do NOT use "security" terminology when referring to MOP coverage.

4. **Coverage.aj logs via HashSet dedup**: The Coverage.aj aspect woven into instrumented APKs logs method calls via `Log.v("RVSEC-COV", signature)` with a `HashSet` to ensure each signature is logged only once per execution. The signature format is `<className: returnType methodName(params)>`. The `LogcatParser` also supports a legacy format (`class:::method:::params`) for backward compatibility.

5. **SignatureNormalizer for inner class notation**: Static analysis tools (Soot) use `$` for inner classes (`OuterClass$InnerClass`), but the analysis JSON may use `.` notation (`OuterClass.InnerClass`). The `StaticAnalysisParser` uses `SignatureNormalizer` to convert `.` to `$` based on Java naming convention heuristics (uppercase after separator indicates inner class).

6. **PackageDetector resolves manifest vs code package**: In approximately 27.5% of APKs, the AndroidManifest.xml package name differs from the actual code package (e.g., Godot games: manifest=`ir.hsn6.trans`, code=`org.godotengine.godot`). The `PackageDetector` uses a priority-based heuristic with 6 strategies: same-package check, game engine detection, single package, common prefix, frequency-based selection, and string similarity fallback. Static analysis parsers receive `code_package` (not `package_name`) for class filtering.

7. **Visitor pattern for extensible UI parsing**: The rv-screen-parser uses the visitor pattern with `Node.accept(visitor)` dispatching to element-specific methods (`visit_button`, `visit_edit_text`, etc.). This allows different visitors to produce different output formats without modifying the parser. The visitor handles 30+ Android widget classes including standard, AndroidX AppCompat, and Material Design components.

8. **Thread-safe real-time tracking**: The `CoverageTracker` runs in a background daemon thread with `RLock` protection. It uses file position tracking (seek to end, read new lines) to process logcat entries incrementally without re-reading processed data. Change detection optimizes CPU usage by only recalculating metrics when data has actually changed.

### Data Models

```
StaticAnalysisData:
  classes: Classes              # Collection of application classes and methods (reachability section)
  windows: Windows              # Collection of UI windows and widgets (windows section)
  wtg: WindowTransitionGraph    # Navigation graph (transitions section)
  components: Components        # Non-Activity component data with intent-filters and MOP reachability (components section)

Classes:
  classes: Dict[str, Clazz]     # Class name -> class info (component_type, is_main, methods)

Clazz:
  name: str                     # Fully qualified class name
  component_type: str | None    # "activity", "service", "receiver", "provider", or None
  is_main: bool                 # True if this is the main launcher Activity
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

Components:
  activities: List[ComponentInfo]   # Activities with intent-filters and MOP data
  receivers: List[ComponentInfo]    # BroadcastReceivers with intent-filters and MOP data
  services: List[ComponentInfo]     # Services with intent-filters and MOP data
  providers: List[ComponentInfo]    # ContentProviders with authorities and MOP data

ComponentInfo:
  class_name: str                   # Fully qualified class name
  component_type: str               # "activity", "service", "receiver", "provider"
  is_main: bool                     # True if this is the main launcher Activity
  intent_filters: List[IntentFilter]  # Intent filters (empty for providers)
  authorities: str | None           # Content provider authorities (providers only)
  exported: bool                    # Whether the component is exported
  reaches_mop: bool                 # Whether lifecycle methods reach monitored operations
  mop_methods: List[str]            # Signatures of lifecycle methods reaching MOP

IntentFilter:
  actions: List[str]                # Intent actions (e.g., "android.intent.action.MAIN")
  categories: List[str]             # Intent categories (e.g., "android.intent.category.LAUNCHER")

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
  analysis_file: str            # Path to unified analysis JSON output file
  timed_out: bool               # Whether analysis exceeded timeout (partial JSON may exist)
  success: bool                 # Overall pipeline success
  errors: List[str]             # Error messages during analysis

CoverageCalculationMode:
  FULL_STATIC_ANALYSIS          # Complete static data available
  PARTIAL_STATIC_ANALYSIS       # Limited static data (< 10 methods)
  RUNTIME_ONLY                  # No static data, only runtime
  FALLBACK_MODE                 # Minimal functionality
```

### Cross-Domain Dependencies

```
rv-static-analysis:
  Depends on: rv-android-core (App, Classes, Windows, WTG, Components, ErrorHandler, LoggingManager)
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
- `code_package: str` -- Application code package name (source: App.code_package via PackageDetector, consumed by StaticAnalysisParser for class filtering)
- `rvsec_root: str` -- Path to RVSEC installation (source: RVSEC_HOME env var or explicit, consumed by RVStaticAnalysisConfig for tool path resolution)
- `mop_dir: str` -- Path to MOP specification directory (source: RVStaticAnalysisConfig, consumed by the analysis client via `-clientParam mopDir=<path>`)
- `analysis_timeout: float` -- Timeout in seconds for the analysis tool (default: 600.0). Passed both as `Command.timeout` (Python process-level kill) and `--timeout` (GATOR's internal timeout)
- `analysis_client_jar: str` -- Path to the analysis client fat JAR (`lib/gator/rvsec-analysis-client.jar`)
- `logcat_file: str` -- Path to Android logcat output file (source: LogcatComponent in rv-platform, consumed by CoverageTracker and CoverageAnalyzer)
- `static_data: StaticAnalysisData` -- Parsed static analysis data (source: StaticAnalyzer.get_static_data(), consumed by CoverageTracker for repository initialization)
- `xml_data: str` -- UIAutomator2 XML hierarchy dump string (source: uiautomator2 device.dump_hierarchy(), consumed by UIAutomator2Parser)
- `screenshot_path: str` -- Path to screenshot image file (source: device screenshot capture, consumed by ScreenshotAnalyzer)
- `task_start_time: datetime` -- Tool execution start time (source: rv-platform TaskExecutor, consumed by CoverageTracker for relative timing)
- `task_id: str` -- Task identifier for event correlation (source: rv-platform, consumed by CoverageTracker)

### Output

- `StaticAnalysisData` -- Unified static analysis results containing Classes, Windows, WTG, and Components (destination: rv-platform StaticAnalysisComponent, rv-agent, rv-coverage)
- `StaticAnalysisResult` -- Analysis pipeline status with analysis file path, timeout flag, and errors (destination: rv-experiment pre-processing)
- `Dict[str, float]` -- Coverage metrics dictionary with method_coverage, activity_coverage, mop_method_coverage, called_methods, total_errors (destination: rv-platform CoverageComponent)
- `ScreenDescription` -- Complete screen state with items, actions, and coordinates (destination: rv-agent ScreenProcessor, LLM prompt generation)
- `ScreenshotAnalysisResult` -- Visual analysis results with detected texts, buttons, errors, and interactive elements (destination: rv-agent screenshot analysis)
- `PackageDetectionResult` -- Package detection result with code_package, confidence, and detection method (destination: App.code_package property)

### Side-Effects

- **File System (analysis)**: Creates `{app_name}.json` analysis output file in output directory containing reachability, windows, transitions, and components sections
- **File System (logcat)**: CoverageTracker creates empty logcat file if it does not exist
- **Background Thread**: CoverageTracker starts a daemon thread for continuous logcat monitoring; thread terminates on stop() or context manager exit

### Error

- `StaticAnalysisException` -- Raised when the analysis tool returns a non-zero exit code. Contains tool name ("ANALYSIS"), exit code, and stderr output.
- `RVCommandTimeoutError` -- Raised when the analysis tool exceeds `analysis_timeout`. The `Command` class kills the process tree via `kill_process_tree()`.
- `ConfigurationError` -- Raised by RVStaticAnalysisConfig when required paths are missing (analysis client JAR, MOP directory, Android SDK).
- `ValueError` -- Raised by ItemAction coordinate validation when coordinates are not a 2-element integer tuple or contain negative values.
- Parser errors -- Caught internally and logged; the parser returns empty domain objects per-section (empty Classes, empty Windows, empty WindowTransitionGraph, empty Components) on failure rather than propagating exceptions.

## Invariants

- **INV-ANA-02**: The `StaticAnalysisParser` MUST apply `SignatureNormalizer` to all class names and method signatures before storing them in domain models. The normalization converts inner class dot notation (`OuterClass.InnerClass`) to dollar notation (`OuterClass$InnerClass`) using Java naming convention heuristics. The normalizer is applied in all three JSON sections (`windows`, `transitions`, `reachability`).

- **INV-ANA-03**: The `StaticAnalysisParser` MUST receive `code_package` (from `App.code_package`, detected by `PackageDetector`) for class filtering, NOT `package_name` (from AndroidManifest.xml). The parser MUST filter classes in the `reachability` section and windows in the `windows` section by verifying that class names contain the `code_package` string.

- **INV-ANA-04**: The `CoverageTracker` MUST log coverage metric updates whenever coverage metrics change. It MUST log MOP error detections immediately when an RV error is detected. Log entries MUST include the `task_id` if one was provided during initialization.

- **INV-ANA-05**: The `CoverageTracker` MUST be thread-safe. All shared state access MUST be protected by the `_reader_lock` (RLock). The background monitoring thread MUST be a daemon thread that terminates when stop() is called or the context manager exits.

- **INV-ANA-06**: The `StaticAnalysisParser` MUST NOT propagate exceptions to callers. On parse failure of any section (`windows`, `transitions`, `reachability`), it MUST log the error and return empty domain objects for that section: `Windows()` for window parsing failures, `WindowTransitionGraph()` for transition parsing failures, `Classes()` for reachability parsing failures. Each section is parsed independently — a failure in one section MUST NOT prevent parsing of other sections.

- **INV-ANA-07**: The `LogcatParser` MUST support two coverage message formats: the modern format (`<class: returnType method(params)>`) and the legacy format (`class:::method:::params`). Both formats MUST produce valid `RvCoverageLog` instances.

- **INV-ANA-08**: The `LogcatParser` MUST support three error message formats: the standard JCA format (comma-separated: `spec,class,init,method,source,error_type,message`), the FSM format (`class.method():::Spec went into an error state.`), and the generic format (`class.method(file:line) ::: Spec went into an error state.`). Malformed messages MUST be logged as warnings and return None, not malformed data.

- **INV-ANA-09**: The `ItemAction.action_type` computed property MUST derive the action type from `WidgetEventType` as the single source of truth, using the `WIDGET_EVENT_TO_ACTION_TYPE` mapping. Text parsing MUST only be used for scroll direction refinement (scroll_up, scroll_down, scroll_left, scroll_right), never for primary type classification.

- **INV-ANA-10**: The `ScreenDescription` MUST build an `events_by_id` mapping from all `ItemAction` objects across all `ScreenItem` elements. The `get_action_by_id()` method MUST return the correct `ItemAction` for any valid ID within the screen context.

- **INV-ANA-11**: The `StaticAnalyzer` MUST implement intelligent caching: if the analysis `.json` output file already exists, tool execution MUST be skipped. A `CommandResult(0, b"", b"")` MUST be returned for cached results. An info log with `execution_status='cached'` MUST be recorded.

- **INV-ANA-12**: The `Node.accept(visitor)` method MUST dispatch to element-specific visitor methods based on `view_class` (e.g., `visit_button` for `android.widget.Button`). System navigation buttons (navbar, status bar) MUST be filtered by calling `visitor.should_exclude_system_button(node)` for leaf nodes only, never for container nodes. Container filtering would exclude all children.

- **INV-ANA-13**: `ItemAction.coordinates` MUST be validated as a non-negative integer tuple of exactly 2 elements `(x, y)`, or None. The `get_execution_coordinates()` method MUST resolve coordinates using priority: (1) explicit coordinates, (2) target view bounds center.

- **INV-ANA-14**: The `PackageDetector` MUST apply detection heuristics in the following priority order: (1) same-as-manifest, (2) game engine detection, (3) single package, (4) common prefix, (5) most common (60%+ frequency), (6) string similarity (85%+ threshold), (7) manifest fallback. Each strategy returns early if a match is found.

- **INV-ANA-15**: Coverage metrics MUST be calculated with reachability data as the denominator. `method_coverage` = (called methods) / (total reachable methods from the analysis JSON's reachability section). `mop_method_coverage` = (called methods that reach MOP) / (total methods with reaches_mop=true). Without reachability data, percentage-based coverage MUST NOT be reported; only absolute counts are valid.

## Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing four data sections written in priority order: (1) method reachability relative to MOP specifications (coverage denominator), (2) window and widget inventory with event listeners, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and MOP reachability.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. GATOR initializes Soot once, builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the client writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file. The execution order inside `run()`:

1. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). Service, Receiver, and Provider class names are resolved to `SootClass` via `Scene.v().getSootClassUnsafe()`, which returns `null` for unresolvable classes (logged as WARNING, skipped). Lifecycle methods are found by iterating `SootClass.getMethods()` and filtering by name. For each application method, it computes: `reachable` (reachable from entry points), `reachesMop` (has path to a monitored API method), and `directlyReachesMop` (directly invokes a monitored API method). MOP method signatures are loaded from `.mop` specification files via `JavamopFacade`. This section is written and flushed first.

2. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners discovered through interprocedural data flow. Two fields not available via GATOR APIs — `inputType` and `entries` — are extracted by parsing the decoded layout XML files at `Configs.resourceLocation`.

3. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures.

4. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager` (for Services/Receivers) or `android:authorities` attribute (for Providers), `android:exported` attribute from the manifest, and MOP reachability cross-referenced with the reachability BFS results. This section is written and flushed last — lowest priority for timeout graceful degradation.

The `complementWithCallbacks()` method, which propagates MOP flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive MOP flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null`) and `isMain` (boolean) fields. The old `isActivity` and `isMainActivity` fields are removed. The `StaticAnalysisParser` (Python) MUST parse these fields into the `Clazz` domain model (`component_type: str | None`, `is_main: bool`).

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components). Downstream consumers (rv-agent, rv-coverage, rv-platform) receive this data structure.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages. The `CoverageAnalyzer` explicitly switches to `RUNTIME_ONLY` or `FALLBACK_MODE` when reachability data is unavailable.

The reachability section also provides MOP prioritization data consumed by rv-agent. The `MopScorer` in rv-agent's `ActionRanker` assigns +100 score to actions with `directly_reaches_mop=true` and +50 to actions with `reaches_mop=true`, directing exploration toward MOP-relevant code paths.

The call graph is built using Soot's default entry point strategy — Android lifecycle callbacks discovered by FlowDroid's callback analysis. JCA framework classes (`javax.crypto.Cipher`, `java.security.MessageDigest`, etc.) appear as call targets whenever any application method invokes them — they do not need to be entry points. If reachability is insufficient for specific APKs, GATOR supports a `-withCHA` flag that enables CHA (Class Hierarchy Analysis), which resolves all virtual calls based on the class hierarchy.

**Module**: rv-static-analysis (launcher + parser), rvsec-gator (analysis client)
**Key components**: `RvsecAnalysisClient`, `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser`, `Clazz`

#### Scenario: Successful static analysis with valid APK

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path and the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -withCHA`
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` containing non-empty `Classes`, `Windows`, `WindowTransitionGraph`, and `Components`
- **AND** the `.json` file MUST contain a `components` section (may have empty `receivers[]`, `services[]`, and `providers[]` arrays)

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

#### Scenario: Static analysis JSON parsing — reachability section with component type

- **WHEN** `StaticAnalysisParser._parse_classes()` processes the `reachability` array from the analysis JSON
- **THEN** each class entry MUST produce a `Clazz` object with `name`, `component_type` (string or None), and `is_main` (boolean)
- **AND** `component_type` MUST be parsed from the JSON `componentType` field (`"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null`)
- **AND** `is_main` MUST be parsed from the JSON `isMain` field
- **AND** each method in the class's `methods` array MUST produce a `Method` object with `name`, `signature`, `reachable`, `reachesMop`, and `directlyReachesMop` flags
- **AND** class names and signatures MUST be normalized via `SignatureNormalizer` (INV-ANA-02)
- **AND** classes not containing `code_package` in their name MUST be filtered out (INV-ANA-03)

#### Scenario: Static analysis JSON parsing — components section

- **WHEN** `StaticAnalysisParser._parse_components()` processes the `components` object from the analysis JSON
- **THEN** each entry in `activities[]`, `receivers[]`, and `services[]` MUST produce a `ComponentInfo` object with `class_name`, `component_type`, `is_main`, `intent_filters` (list of `IntentFilter`), `exported`, `reaches_mop`, and `mop_methods`
- **AND** each entry in `providers[]` MUST produce a `ComponentInfo` object with `class_name`, `component_type="provider"`, `is_main=False`, `authorities` (string), `exported`, `reaches_mop`, and `mop_methods`
- **AND** if the `components` key is missing from the JSON (e.g., timeout before Section 4 was written), `_parse_components()` MUST return an empty `Components` object
- **AND** if the `components` section contains malformed data, `_parse_components()` MUST log an error and return an empty `Components` object (INV-ANA-06)
- **AND** the resulting `Components` object MUST be stored in `StaticAnalysisData.components`

#### Scenario: Static analysis JSON parsing with inner class normalization

- **WHEN** `StaticAnalysisParser` encounters a class name like `com.example.OuterActivity.InnerFragment` in any section
- **THEN** `SignatureNormalizer` MUST convert it to `com.example.OuterActivity$InnerFragment`
- **AND** the normalized name MUST be used for all domain model lookups and storage

#### Scenario: Analysis output file does not exist

- **WHEN** `StaticAnalysisParser.parse_file()` is called with a non-existent file path
- **THEN** a warning MUST be logged
- **AND** an empty `StaticAnalysisData` MUST be returned with empty `Classes()`, `Windows()`, `WindowTransitionGraph()`, and `Components()`

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

#### Scenario: Service lifecycle methods as entry points

- **WHEN** an APK declares a Service `com.example.app.MyService` with an overridden `onStartCommand` method
- **THEN** `getEntryPoints()` MUST include `MyService.onStartCommand` in the returned set
- **AND** the call graph traversal MUST reach methods called from `onStartCommand`
- **AND** MOP reachability MUST be computed for these methods
- **AND** `reachability[]` entry for `com.example.app.MyService` MUST have `componentType="service"`

#### Scenario: BroadcastReceiver onReceive as entry point

- **WHEN** an APK declares a BroadcastReceiver `com.example.app.MyReceiver` with an `onReceive` method
- **THEN** `getEntryPoints()` MUST include `MyReceiver.onReceive` in the returned set
- **AND** methods called from `onReceive` MUST appear in `reachability[]` with correct MOP flags
- **AND** `reachability[]` entry for `com.example.app.MyReceiver` MUST have `componentType="receiver"`

#### Scenario: ContentProvider lifecycle methods as entry points

- **WHEN** an APK declares a ContentProvider `com.example.app.MyProvider` with overridden `onCreate` and `query` methods
- **THEN** `getEntryPoints()` MUST include `MyProvider.onCreate` and `MyProvider.query` in the returned set
- **AND** the call graph traversal MUST reach methods called from these lifecycle methods
- **AND** MOP reachability MUST be computed for these methods
- **AND** `reachability[]` entry for `com.example.app.MyProvider` MUST have `componentType="provider"`

#### Scenario: Unresolvable component class

- **WHEN** the manifest declares `<service android:name=".MissingService"/>` but the class does not exist in the APK
- **THEN** the class MUST be skipped
- **AND** a WARNING MUST be logged with the class name
- **AND** no exception MUST propagate
- **AND** the class MUST NOT appear in `components{}`

#### Scenario: Components section in JSON — app with all component types

- **WHEN** an APK declares Activity `com.example.app.MainActivity` (main launcher) and `com.example.app.DetailActivity` (with action EDIT), Receiver `com.example.app.BootReceiver` with intent-filter action `android.intent.action.BOOT_COMPLETED`, Service `com.example.app.CryptoService` with action `com.example.START_CRYPTO`, and Provider `com.example.app.DataProvider` with authorities `com.example.app.data`
- **THEN** the JSON MUST contain:
  ```json
  "components": {
    "activities": [{
      "className": "com.example.app.MainActivity",
      "isMain": true,
      "intentFilters": [{"actions": ["android.intent.action.MAIN"], "categories": ["android.intent.category.LAUNCHER"]}],
      "exported": true,
      "reachesMop": false,
      "mopMethods": []
    }, {
      "className": "com.example.app.DetailActivity",
      "isMain": false,
      "intentFilters": [{"actions": ["android.intent.action.EDIT"], "categories": []}],
      "exported": true,
      "reachesMop": false,
      "mopMethods": []
    }],
    "receivers": [{
      "className": "com.example.app.BootReceiver",
      "isMain": false,
      "intentFilters": [{"actions": ["android.intent.action.BOOT_COMPLETED"], "categories": []}],
      "exported": true,
      "reachesMop": true,
      "mopMethods": ["<com.example.app.BootReceiver: void onReceive(android.content.Context,android.content.Intent)>"]
    }],
    "services": [{
      "className": "com.example.app.CryptoService",
      "isMain": false,
      "intentFilters": [{"actions": ["com.example.START_CRYPTO"], "categories": []}],
      "exported": false,
      "reachesMop": true,
      "mopMethods": ["<com.example.app.CryptoService: int onStartCommand(android.content.Intent,int,int)>"]
    }],
    "providers": [{
      "className": "com.example.app.DataProvider",
      "authorities": "com.example.app.data",
      "exported": false,
      "reachesMop": true,
      "mopMethods": ["<com.example.app.DataProvider: android.database.Cursor query(android.net.Uri,java.lang.String[],java.lang.String,java.lang.String[],java.lang.String)>"]
    }]
  }
  ```

#### Scenario: Components section — app with only Activities

- **WHEN** an APK declares no Services, BroadcastReceivers, or ContentProviders
- **THEN** the JSON MUST contain `"components": {"activities": [...], "receivers": [], "services": [], "providers": []}`
- **AND** `activities[]` MUST contain entries for all declared Activities with their intent-filters
- **AND** all other sections (`reachability[]`, `windows[]`, `transitions[]`) MUST be unchanged

#### Scenario: Component without intent-filters

- **WHEN** a Service is declared without any `<intent-filter>` in the manifest
- **THEN** its entry MUST have `"intentFilters": []`
- **AND** it MUST still appear in the `services[]` array

#### Scenario: MOP flag propagation for Service/Receiver callbacks

- **WHEN** a Service's `onStartCommand` method calls a method that directly reaches a MOP specification
- **THEN** `onStartCommand` MUST be marked with `reachesMop=true` in `reachability[]`

#### Scenario: Timeout with partial JSON — components section missing

- **WHEN** the analysis tool times out after writing reachability, windows, and transitions sections but before completing the components section
- **THEN** `StaticAnalysisParser` MUST parse the partial file successfully for the existing three sections
- **AND** the missing `components` section MUST NOT cause a parse error
- **AND** downstream consumers (APE-RV `MopData`) MUST handle absent `components` gracefully (empty lists)

#### Scenario: Provider without intent-filters uses authorities

- **WHEN** a ContentProvider is declared with `android:authorities="com.example.provider"` and no `<intent-filter>`
- **THEN** its entry MUST have `"authorities": "com.example.provider"` instead of `intentFilters`
- **AND** it MUST appear in the `providers[]` array
- **AND** `exported` MUST default to `false` (providers without intent-filters)

#### Scenario: Existing Activity reachability data unchanged

- **WHEN** the analysis JSON is generated for an APK that was previously analyzed without Service/Receiver/Provider entry points
- **THEN** the `reachability[]` entries for Activity classes and their methods MUST have identical `reachable`, `reachesMop`, and `directlyReachesMop` values
- **AND** `windows[]` and `transitions[]` sections MUST be unchanged
- **AND** all `reachability[]` entries MUST use `componentType`/`isMain` instead of the old `isActivity`/`isMainActivity` fields
- **AND** non-component classes MUST have `componentType=null` and `isMain=false`

#### Scenario: Reachability data used as coverage denominator

- **WHEN** `CoverageTracker` or `CoverageAnalyzer` initializes with `StaticAnalysisData` containing `Classes` parsed from the analysis JSON's `reachability` section
- **THEN** the repository MUST be initialized with all classes and methods from the static data
- **AND** `method_coverage` MUST be calculated as: (called_methods) / (total_reachable_methods)
- **AND** `mop_method_coverage` MUST be calculated as: (called_mop_methods) / (total_methods_with_reaches_mop)
- **AND** these coverage calculations MUST use the `reachability` section from the analysis JSON as the method universe

#### Scenario: Coverage without reachability data (fallback)

- **WHEN** CoverageAnalyzer is initialized without StaticAnalysisData or with empty Classes
- **THEN** calculation_mode MUST be set to RUNTIME_ONLY or FALLBACK_MODE
- **AND** coverage percentage metrics MUST be reported as 0.0 (unavailable)
- **AND** only absolute counts (called_methods, total_errors) MUST be valid

### Requirement: Method Coverage Tracking (FR12, NFR06)

The system MUST track method coverage in real-time during test execution via the `CoverageTracker`, and provide batch analysis via the `CoverageAnalyzer`. Coverage tracking relies on the instrumented APK's Coverage.aj aspect, which logs unique method signatures to Android logcat using the `RVSEC-COV` tag.

The `CoverageTracker` monitors a logcat file in a background daemon thread. It reads new lines incrementally (using file position tracking to avoid re-reading), parses each line via `parse_logcat_line()`, and registers method calls in the `LogcatRepository`. When initialized with `StaticAnalysisData`, the repository is populated with the known method universe from the analysis JSON's reachability section, enabling percentage-based coverage calculation.

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
