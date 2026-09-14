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
    SAC->>Parser: parse_file(json_path)
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

3. **MOP means Monitored Operations, not security**: The term "MOP" refers to methods being monitored by ANY specification set (JCA cryptographic specifications or generic FSM specifications). The `reaches_target` and `directly_reaches_target` flags in the reachability section indicate paths to monitored API methods, regardless of specification domain. Do NOT use "security" terminology when referring to MOP coverage.

4. **Coverage.aj logs via HashSet dedup**: The Coverage.aj aspect woven into instrumented APKs logs method calls via `Log.v("RVSEC-COV", signature)` with a `HashSet` to ensure each signature is logged only once per execution. The signature format is `<className: returnType methodName(params)>`. The `LogcatParser` also supports a legacy format (`class:::method:::params`) for backward compatibility.

5. **Identifiers are stored as the artefact spells them**: GATOR and the woven `Coverage.aj` both emit the JVM binary name — `$` at genuine nesting, `.` at every package boundary — so the `StaticAnalysisParser` stores class names, window names and method signatures verbatim, and no transformation is applied on either side of the coverage crossing (INV-ANA-67).

6. **PackageDetector resolves manifest vs code package**: In approximately 27.5% of APKs, the AndroidManifest.xml package name differs from the actual code package (e.g., Godot games: manifest=`ir.hsn6.trans`, code=`org.godotengine.godot`). The `PackageDetector` uses a priority-based heuristic with 6 strategies: same-package check, game engine detection, single package, common prefix, frequency-based selection, and string similarity fallback. The key it elects scopes the analysis when one is **run** — it is passed to GATOR as `-clientParam codePackage=`. Parsing a produced artefact receives no key at all (INV-ANA-61).

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
  reaches_target: bool             # Has path (direct or indirect) to a monitored API method
  directly_reaches_target: bool    # Directly invokes a monitored API method

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
  prompt: str | None            # android:prompt (Spinner dialog title); null when absent
  spinner_mode: str | None      # android:spinnerMode ("dropdown" | "dialog" | null)
  content_description: str | None  # android:contentDescription (accessibility label); null when absent
  tooltip_text: str | None      # android:tooltipText (long-press hint); null when absent

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
  reaches_target: bool                 # Whether lifecycle methods reach monitored operations
  target_methods: List[str]            # Signatures of lifecycle methods reaching MOP

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
  reaches_target: bool             # Action reaches monitored operations
  directly_reaches_target: bool    # Action directly reaches monitored operations
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
  Consumed by: rv-agent (ScreenProcessor), rv-uiautomator (device interaction)
```

## Data Contracts

### Input

- `apk_path: str` -- Path to Android APK file (source: rv-experiment or user, consumed by StaticAnalyzer)
- `code_package: str` -- Application code package name (source: App.code_package via PackageDetector, consumed by `RVStaticAnalysisConfig.get_tool_command` to scope the GATOR invocation; not consumed by the parser)
- `rvsec_root: str` -- Path to RVSEC installation (source: RVSEC_HOME env var or explicit, consumed by RVStaticAnalysisConfig for tool path resolution)
- `mop_dir: str` -- Path to MOP specification directory (source: RVStaticAnalysisConfig, consumed by the analysis client via `-clientParam mopDir=<path>`). The directory may declare owners exactly with explicit imports (`jca`, `jca_android`) or by hierarchy with wildcard imports, `+` owners and wildcard method names (`generic_new`). `rv-experiment` passes the directory of the selected specification set (`ExperimentConfig.resolve_spec_set_dir`); `--specification-set generic` maps to `resources/generic` (synthetic `FSM*` specs), not to `generic_new`, which is reached through `--specification-set custom --custom-specs-dir` or `rv-static-analysis --mop-dir`
- `Scene` -- The Soot whole-program scene of the APK (call sites, declaring classes/types), in which target owners are resolved (source: GATOR/Soot 4.7.1, INV-ANA-18)
- `codePackageSource: str` -- The scope key's origin (`manifest`, `manifest-neutralized` or `detector`), delivered to GATOR on its own client parameter beside `codePackage` (INV-ANA-66)
- `libraryPackageFile: str` -- Path to `libPackages.txt` (2,170 patterns), passed to GATOR unconditionally; it shapes the reachability predicates, not the class denominator (INV-ANA-69)
- `targets_file: str` -- Path to a text file of Soot method signatures, one per line (`#` comments allowed); mutually exclusive with `mop_dir` (source: RVStaticAnalysisConfig CLI `--targets-file`, consumed via `-clientParam targetsFile=<path>`; INV-ANA-33)
- `cg_algorithm: str` -- Soot call graph algorithm, one of `spark` (default), `cha`, `rta`, `vta` (source: RVStaticAnalysisConfig CLI `--cg-algorithm`, forwarded to GATOR as `-cgAlgorithm`)
- `cg_delegation: bool` -- Whether WTG construction delegates virtual-dispatch resolution to the SPARK call graph (default `false` after M3 paridade-gate failure, 2026-05-15), passed via `-clientParam cgDelegation=<bool>`. When `true`, `FlowgraphRebuilder.buildCallGraph()` consults `Scene.v().getCallGraph()` and skips the local CHA-style rebuild (opt-in, 2–23× speedup for apps without hybrid-framework wiring). When `false` (default), legacy points-to + CHA-fallback behavior is preserved bit-for-bit (INV-ANA-21). See `docs/20260515_diagnostico_paridade_cgdelegation.md`.
- `skip_wtg: bool` -- Whether `WTGBuilder.build()` is bypassed (default `false`), passed via `-clientParam skipWtg=<bool>`. When `true`, WTG is not built and `transitions[]` is emitted as an empty array (source: RVStaticAnalysisConfig CLI `--skip-wtg`).
- `analysis_timeout: float` -- Timeout in seconds for the analysis tool (default: 600.0). Passed both as `Command.timeout` (Python process-level kill) and `--timeout` (GATOR's internal timeout)
- `analysis_client_jar: str` -- Path to the analysis client fat JAR (`lib/gator/rvsec-analysis-client.jar`)
- `logcat_file: str` -- Path to Android logcat output file (source: LogcatComponent in rv-platform, consumed by CoverageTracker and CoverageAnalyzer)
- `line: str` -- One raw threadtime logcat line, fed by `parse_logcat_file` (offline / resume) and by `CoverageTracker` (live) in file order (source: `task.result.logcat_file`)
- `message: str` -- The text after the `RVSEC` tag of one line; seven comma-separated fields when written by the logcat `ErrorCollector`, one of the two `went into an error state.` shapes when written by a generic monitor (source: `_parse_logcat_line`)
- `static_data: StaticAnalysisData` -- Parsed static analysis data (source: StaticAnalyzer.get_static_data(), consumed by CoverageTracker for repository initialization)
- `xml_data: str` -- UIAutomator2 XML hierarchy dump string (source: uiautomator2 device.dump_hierarchy(), consumed by UIAutomator2Parser)
- `screenshot_path: str` -- Path to screenshot image file (source: device screenshot capture, consumed by ScreenshotAnalyzer)
- `task_start_time: datetime` -- Tool execution start time (source: rv-platform TaskExecutor, consumed by CoverageTracker for relative timing)
- `task_id: str` -- Task identifier for event correlation (source: rv-platform, consumed by CoverageTracker)

### Output

- `StaticAnalysisData` -- Unified static analysis results containing Classes, Windows, WTG, and Components (destination: rv-platform StaticAnalysisComponent, rv-agent, rv-coverage)
- Analysis artefact scope members -- `code_package` and `code_package_source` (the effective scope key and its origin) and `class_defs_under_key` (the net count of compiled classes under the key that survive `isAppClass`), recorded beside the manifest `package` member (INV-ANA-66)
- `StaticAnalysisResult` -- Analysis pipeline status with analysis file path, timeout flag, and errors (destination: rv-experiment pre-processing)
- `Dict[str, float]` -- Coverage metrics dictionary with method_coverage, activity_coverage, mop_method_coverage, called_methods, total_errors (destination: rv-platform CoverageComponent)
- `ScreenDescription` -- Complete screen state with items, actions, and coordinates (destination: rv-agent ScreenProcessor, LLM prompt generation)
- `ScreenshotAnalysisResult` -- Visual analysis results with detected texts, buttons, errors, and interactive elements (destination: rv-agent screenshot analysis)
- `PackageDetectionResult` -- Package detection result with code_package, confidence, and detection method (destination: App.code_package property)
- `RvErrorLog` -- The six fields `spec`, `error_type`, `class_full_name`, `method`, `source`, `message` plus the envelope fields `code`, `event`, `obj`, `val`, `exp`, `msg` (all `str`) and the flag `truncated: bool`. `code` and `event` hold the sentinel `UNSPECIFIED` when the message is not an envelope; `obj`/`val`/`exp`/`msg` hold `""` then. `unique_msg` is a computed field owned by `core` (INV-CORE-25/41) and is not assigned by the parser (destination: `LogcatRepository.register_rv_error`, `CoverageTracker`, `result_processor`)
- `ParserDiagnostics` -- Counter object defined in `rv-android-core` beside `LogcatRepository` (`domain/coverage.py`), carried by the returned repository as `parser_diagnostics` and shared by the live `CoverageTracker`; `parse_logcat_line(line, diagnostics=None)` counts into the object it is given and into a fresh one otherwise. Integer counters: `lines_not_threadtime`, `lines_other_tag`, `format1_regex_failed`, `format2_short`, `format3_unresolved`, `unrecognised`, `continuation_lines`, `truncated_envelopes`, `sentinel_error_type`, `sentinel_source`, `sentinel_code`, `sentinel_event`, `envelope_forbidden_chars`, and the scope-split discard counters `unmatched_out_of_scope`, `unmatched_in_scope` and `unmatched_unclassified` (INV-ANA-68). No result artefact persists these counters: `result_processor` writes only `unmatched_out_of_scope` and `unmatched_in_scope` to `summary.csv` (destination: in-memory repository, tests)
- `TargetMethod{className, methodName, params, signature, policy, includeSubtypes, nameIsPattern}` -- Resolved by `MopSpecsTargetSource.load()` from each `MopMethod` (destination: `TargetResolver.resolveInScene` and the direct bytecode scan)
- `reachability[].methods[].{reachable, reachesTarget, directlyReachesTarget}: bool` -- Per-method flags in the GATOR JSON; the key set does not depend on the specification set (INV-ANA-44). Readers of the raw artefact that tolerate no key change: `static_analysis_parser.py` (the single parse point in `rv-static-analysis`), the gate and sweep scripts under `scripts/`, and `aperv-tool`, which parses `<apk>.json` itself (`analysis/static_artifact.py`, `tools/aperv/derive_mop_artifact.py`, where `method.get("reachesTarget") is True` turns a rename into a silent `False`). The device-side `MopData` reads the derived `*.mop.json`, where the key is renamed `reachesMop`, not this artefact. Two value gates watch these booleans against the `jca` default: `tests/parity/test_reachability_parity.py` (`G_paridade_targets`, the set of signatures with `reachesTarget=true`) and `tests/parity/test_historical_methods_coverage.py` (three methods pinned at `directlyReachesTarget=true`)

### Side-Effects

- **File System (analysis)**: Creates `{app_name}.json` analysis output file in output directory containing reachability, windows, transitions, and components sections
- **File System (logcat)**: CoverageTracker creates empty logcat file if it does not exist
- **GATOR Scene**: `SootClass.setLibraryClass()` demotes every class outside the effective scope key; the demotion is irreversible within the run (INV-ANA-65)
- **File System (analysis cache)**: a stored artefact whose recorded key differs from the run's effective key is regenerated rather than reused; `--force` discards it before the analysis runs (INV-ANA-70)
- **Background Thread**: CoverageTracker starts a daemon thread for continuous logcat monitoring; thread terminates on stop() or context manager exit
- **Logging (logcat parser)**: every counted discard is logged at WARNING with the line number and the counter name; a re-raised file-level exception is logged at ERROR with the line number before propagating
- **Soot Scene (target matching)**: each declared target owner FQN is force-resolved into the Scene at HIERARCHY level before `canStoreType` is queried (INV-ANA-43)
- **Log (target matching)**: an owner that cannot be resolved into the Scene with hierarchy content is logged and degrades to exact matching; an owner the extractor cannot resolve is logged and skipped (INV-ANA-40)

### Error

- `StaticAnalysisException` -- Raised when the analysis tool returns a non-zero exit code. Contains tool name ("ANALYSIS"), exit code, and stderr output.
- `RVCommandTimeoutError` -- Raised when the analysis tool exceeds `analysis_timeout`. The `Command` class kills the process tree via `kill_process_tree()`.
- `DenominatorImplausibleError` -- Raised by the denominator gate when the class denominator is empty, the compiled universe under the key is zero, or the parsed-to-compiled ratio falls below `0.15` (INV-ANA-69)
- `ConfigurationError` -- Raised by RVStaticAnalysisConfig when required paths are missing (analysis client JAR, MOP directory, Android SDK).
- Unresolvable target super-type -- Not raised: the owner degrades to exact `equals` matching with a logged warning rather than throwing or silently dropping the target (INV-ANA-43)
- Any exception raised while iterating the file inside `parse_logcat_file` -- logged with the 1-based line number at which it occurred, then re-raised; a partially populated repository MUST NOT be returned in its place, because a caller that receives a repository is entitled to read its counts as the counts of the whole file (INV-ANA-62)
- `ValueError` -- Raised by ItemAction coordinate validation when coordinates are not a 2-element integer tuple or contain negative values.
- Parser errors -- Caught internally and logged; the parser returns empty domain objects per-section (empty Classes, empty Windows, empty WindowTransitionGraph, empty Components) on failure rather than propagating exceptions.

## Invariants

- **INV-ANA-04**: The `CoverageTracker` MUST log coverage metric updates whenever coverage metrics change. It MUST log MOP error detections immediately when an RV error is detected. Log entries MUST include the `task_id` if one was provided during initialization.

- **INV-ANA-05**: The `CoverageTracker` MUST be thread-safe. All shared state access MUST be protected by the `_reader_lock` (RLock). The background monitoring thread MUST be a daemon thread that terminates when stop() is called or the context manager exits.

- **INV-ANA-06**: The `StaticAnalysisParser` MUST NOT propagate exceptions to callers. On parse failure of any section (`windows`, `transitions`, `reachability`), it MUST log the error and return empty domain objects for that section: `Windows()` for window parsing failures, `WindowTransitionGraph()` for transition parsing failures, `Classes()` for reachability parsing failures. Each section is parsed independently — a failure in one section MUST NOT prevent parsing of other sections.

- **INV-ANA-07**: The `LogcatParser` MUST support two coverage message formats: the modern format (`<class: returnType method(params)>`) and the legacy format (`class:::method:::params`). Both formats MUST produce valid `RvCoverageLog` instances.

- **INV-ANA-08**: The `LogcatParser` MUST support three error message formats and MUST recognise each by structure, in this order: Format 1, the generic format with source location (`class.method(file:line) ::: Spec went into an error state.`), selected by the suffix `went into an error state.` **together with the spaced separator ` ::: `** — the suffix alone does not select it, because Format 3 ends in the same words and is distinguished by writing the separator unspaced — and parsed by its regex; a line that carries the suffix but fails the regex MUST be counted under `format1_regex_failed` and dropped, never re-tried as Format 2; Format 2, the JCA format written by the logcat `ErrorCollector` as seven comma-separated fields `spec,classQualifiedName,className,methodName,location,errorType,expecting`, recognised when `len(message.split(",")) >= 6`, with fields 6 onwards rejoined with `,` into `message` (commas inside a message are legal); Format 3, the FSM format (`class.method():::Spec went into an error state.`), recognised by `:::`. When the Format-2 message is an envelope `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'`, the parser MUST expose its keys as `code`, `event`, `obj`, `val`, `exp`, `msg` on `RvErrorLog`, unescaping `\'` to `'` and `\\n` (the collector's escape of a newline) back to a newline. Fabricated values MUST NOT be emitted: an empty `errorType` becomes `error_type=UNSPECIFIED`, an empty or absent location becomes `source=UNSPECIFIED:0` (Format 3 included), a message that is not an envelope yields `code=UNSPECIFIED` and `event=UNSPECIFIED`, and each use of a sentinel is counted. A message matching no format MUST return `None`, be logged, and be counted under `unrecognised`.

- **INV-ANA-09**: The `ItemAction.action_type` computed property MUST derive the action type from `WidgetEventType` as the single source of truth, using the `WIDGET_EVENT_TO_ACTION_TYPE` mapping. Text parsing MUST only be used for scroll direction refinement (scroll_up, scroll_down, scroll_left, scroll_right), never for primary type classification.

- **INV-ANA-10**: The `ScreenDescription` MUST build an `events_by_id` mapping from all `ItemAction` objects across all `ScreenItem` elements. The `get_action_by_id()` method MUST return the correct `ItemAction` for any valid ID within the screen context.

- **INV-ANA-11**: The `StaticAnalyzer` MUST implement intelligent caching: if the analysis `.json` output file already exists, tool execution MUST be skipped. A `CommandResult(0, b"", b"")` MUST be returned for cached results. An info log with `execution_status='cached'` MUST be recorded.

- **INV-ANA-12**: The `Node.accept(visitor)` method MUST dispatch to element-specific visitor methods based on `view_class` (e.g., `visit_button` for `android.widget.Button`). System navigation buttons (navbar, status bar) MUST be filtered by calling `visitor.should_exclude_system_button(node)` for leaf nodes only, never for container nodes. Container filtering would exclude all children.

- **INV-ANA-13**: `ItemAction.coordinates` MUST be validated as a non-negative integer tuple of exactly 2 elements `(x, y)`, or None. The `get_execution_coordinates()` method MUST resolve coordinates using priority: (1) explicit coordinates, (2) target view bounds center.

- **INV-ANA-14**: When — and only when — the user has enabled `PackageDetector`, it MUST apply detection heuristics in the following priority order: (1) same-as-manifest, (2) game engine detection, (3) single package, (4) common prefix, (5) most common (60%+ frequency), (6) string similarity (85%+ threshold), (7) manifest fallback. Each strategy returns early if a match is found. With the detector disabled — the default — none of these strategies MUST run.

- **INV-ANA-15**: Coverage metrics MUST be calculated with reachability data as the denominator. `method_coverage` = (called methods) / (total reachable methods from the analysis JSON's reachability section). `mop_method_coverage` = (called methods that reach MOP) / (total methods with reaches_target=true). Without reachability data, percentage-based coverage MUST NOT be reported; only absolute counts are valid.

- **INV-ANA-20**: `windows[]` MUST be populated in every successful run of `RvsecAnalysisClient.run()` regardless of WTG completion status. The partial-JSON path (`wtg == null`) MUST emit identical widget data to the full-JSON path, differing only in: (a) catch-all WTG-only window entries (fragments, context menus discovered via `wtg.getNodes()` iteration) are absent, and (b) numeric window IDs use the `fallbackId` sequence instead of `windowNodeIds.get(...)`.
- **INV-ANA-21**: When `cgDelegation=true`, `AndroidCallGraph.v()` MUST NOT be populated by `FlowgraphRebuilder.buildCallGraph()` — virtual-dispatch resolution MUST come exclusively from `Scene.v().getCallGraph()` queries plus a bytecode-scan complement for `IGNORED_CLASSES` library targets. The two-call-graph problem is structurally absent.
- **INV-ANA-22**: The bytecode-scan WTG complement MUST mirror the policy of `BUG-INV-ANA-19` (existing complement for `directlyReachesTarget`): same `IGNORED_CLASSES` set, same FQN+method-name match policy, same body-retrieval resilience pattern (catch `RuntimeException`/`OutOfMemoryError`, log, continue).
- **INV-ANA-24**: `MenuExtractor` and `SpinnerItemExtractor` MUST be resilient to body-retrieval failures (same pattern as INV-ANA-17): catch per-method exceptions, log, continue. A single corrupt class MUST NOT abort the extraction.

- **INV-ANA-25**: `parse_logcat_file(logcat_file, static_data)` MUST be invoked with a non-`None` `StaticAnalysisData` whenever the caller intends to reconstruct per-method coverage from a persisted logcat (e.g. on resume, or in offline analysis tooling). When `static_data` is `None`, the returned `LogcatRepository` has `classes = {}`, `register_method_call` silently no-ops for every `RVSEC-COV` entry, and `calculate_metrics().to_dict()` returns zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`. Only `total_errors` and `unique_errors` remain accurate. Callers that omit `static_data` MUST do so deliberately (errors-only path) and log the degraded state.

- **INV-ANA-30**: `JsonReportWriter` MUST NOT hold a reference to `ReachabilityIndex` or invoke any reachability lookup during serialization. All reachability flags emitted in the JSON are read from `ReportModel` fields populated upstream by `ReachabilityEnricher`.
- **INV-ANA-31**: The JSON output of a successful (non-truncated) GATOR run MUST end with the literal field `"complete": true` as the final top-level field. Truncated outputs MUST NOT contain this field.
- **INV-ANA-32**: The set of values declared in `JsonSchema.Keys` (Java) MUST equal the set of values in `_JK` (Python). Verified by `tests/parity/json_keys.py` in CI.
- **INV-ANA-33**: The `rv-static-analysis` CLI MUST require exactly one of `--mop-dir` or `--targets-file`. Both or neither MUST cause the process to exit with a non-zero code before GATOR launches.
- **INV-ANA-34**: `SignatureFileTargetSource` MUST tolerate blank lines and `#` comments. Other malformed content MUST raise `IllegalArgumentException` with line number.
- **INV-ANA-35**: `MopSpecsTargetSource.load()` MUST produce a `Set<TargetMethod>` whose cardinality and `(className, methodName)` pairs equal those produced by the historical `loadMopSignatures()` on the same `mopDir`. For `cryptoapp.mop`, this set has exactly 16 entries (gh57 baseline `b2e04a26`).
- **INV-ANA-36**: `MatchPolicy` is an attribute of the source / target, never a CLI-level override. No `--match-mode` or equivalent flag exists.
- **INV-ANA-37**: After C1f rename, the monorepo MUST NOT contain references to the legacy field names `reachesMop`, `directlyReachesMop`, `mopMethods`, `handlerReachesMop`, `handlerDirectlyReachesMop`, `reaches_mop`, `directly_reaches_mop`, `handler_reaches_mop`, `handler_directly_reaches_mop`, `target_reaches_mop`, `cov_reaches_mop`, `mop_methods` (Pydantic field), or the class name `MopMethod` outside of these documented exclusions: `MopSpecsTargetSource.java`, CLI flag `--mop-dir`, config attribute `mop_dir`, published CSVs under `results/` and `experimento-*/`, archived OpenSpec deltas, historical commit messages, and `modules/rv-agent/` (deprecated per CLAUDE.md — excluded by directory). The gate MUST scan `rvsec-gator/`, `modules/` (minus `rv-agent/`), and `scripts/`. Verified by `G_no_legacy_mop` CI gate.
- **INV-ANA-38**: GATOR Jimple definition-resolution helpers (`definitionRhs`, `resolveInt`, `resolveStr`) MUST live in `presto.android.util.JimpleDefUtils` only. `MenuExtractor`, `SpinnerItemExtractor`, and any future consumer MUST call them via the helper class.

- **INV-ANA-40**: The `rvsec-mop-extractor` (`UsedJcaMethodsVisitor`) MUST extract a non-empty target
  set from spec sets that declare owners via wildcard imports and the `+` subtype operator. For each
  `call(...)` pointcut: wildcard-import packages MUST be registered (the `isAsterisk()` import MUST NOT
  be discarded); a trailing `+` on the owner MUST be stripped and the resulting `MopMethod` MUST carry
  `includeSubtypes=true`; the simple owner name MUST be resolved to an FQN through explicit imports
  first, `Class.forName(pkg + "." + simple)` over the wildcard packages second, and the implicit
  `java.lang` package **third and last**. Every target whose owner resolves ONLY through that implicit
  package MUST carry `MatchPolicy.STRICT`, and `getParams()` MUST resolve pointcut parameter types to
  FQN, since a STRICT target is compared by its full Soot signature. The seed and the STRICT policy are
  inseparable: seeding alone re-introduces the over-match that boundary (c) measures, and STRICT has
  nothing to bind to without the seed. The criterion is the route by which the owner resolved, never
  the owner's name: an owner resolved by its own import keeps the policy it has.

  An owner whose package is registered by no import and which the implicit package does not resolve
  either MUST be logged and skipped — never silently dropped. Resolvability is import-driven, **not** a
  property of being a JDK class. A wildcard method name MUST be preserved as a pattern with
  `nameIsPattern=true` (derivable from the stored name, since a Java identifier cannot contain `*`, and
  kept to record extractor intent at the boundary; design D7). A trailing `*` matches by prefix and the
  bare `*` matches every method of the owner (prefix `""`). The `MopMethod` identity
  (`equals`/`hashCode`) MUST include `includeSubtypes`, `nameIsPattern` and `ownerFromImplicitSeed`, so
  two pointcuts that differ only by `+` are not deduplicated in the extractor's `Set<MopMethod>`.

  **Fixture values.** The verification fixture is `generic_new` (27 specs), chosen because it exercises
  all four constructions at once; the figures are fixture values, not the requirement, and a spec set
  that uses none of the constructions is conformant with an empty delta. The unit test MUST state which
  owner key it uses and assert a number fixed by enumeration over the corpus, not pinned to whatever the
  code emits: **69 distinct `call()` pairs** with the `+` in the owner key and **68** without, including
  the 3 constructor pointcuts of boundary (b) (pairs `(java.net.ServerSocket, <init>)` and
  `(java.util.TreeMap, <init>)`). The single pair the `+`-less key merges is `Iterator.next` in
  `Map_UnsafeIterator` against `Iterator+.next` in `ListIterator_Set`. All **21** distinct `call()`
  owners are JDK classes and all carry targets; 23 owners exist counting the two
  `staticinitialization`-only owners `Serializable`/`URLConnection` of boundary (a). The extractor emits
  72 signature rows and MUST report **zero** unresolved-owner skips for `generic_new`, which holds
  because `CharSequence_NotInSet.mop` imports `java.util.*` for its `Set+` owner; **24/27** specs carry
  at least one static target. The seven `generic_new` specs with a `java.lang` `call()` owner —
  `Object_MonitorOwner`, `Comparable_CompareToNull`, `Comparable_CompareToNullException`,
  `CharSequence_UndefinedHashCode`, `Long_BadParsingArgs`, and (owner `Iterable`) `ListIterator_Set` and
  `Map_UnsafeIterator` — declare `import java.lang.*;`, resolve at the first step and are never STRICT,
  which matters because they declare `(..)` parameters that STRICT would stop matching.

  **Scope boundaries.** This invariant covers `call(...)` pointcuts only.

  (a) **`staticinitialization` is out of scope — a documented static false-negative.** Three specs whose
  ONLY pointcut is `staticinitialization(Owner+)` — `Collection_HashCode`,
  `Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission` — contribute **zero** static
  targets (the pointcut never reaches `visit(MethodPointCut)`), so they never set `reachesTarget` even
  though the runtime monitor fires on class-load.

  (b) **Constructor pointcuts `call(Owner.new(..))` MUST be extracted as `MopMethod(owner, "<init>")`**,
  not logged and skipped. The javamop grammar routes `Owner.new(..)` through `MethodPointCut`
  (`javamop/src/main/javacc/javamop/parser/aspectj_parser/aspectj.jj:1730-1737`, where `"." <NEW>` sets
  `owner = retType` and `name = "new"`), and Soot names every constructor `<init>`, so a target carrying
  the literal name `new` matches nothing. The mapping is unambiguous — `new` is a Java keyword — and needs
  no GATOR-side change, because `TargetResolver.resolveInScene` compares names by equality and
  `SignatureFileTargetSource` accepts `<init>` through its `([^(]+)` capture. The mapping applies to the
  frozen `jca` set as well, under the gh101 doctrine that a repair applying equally to every set is
  admissible when its effect on the frozen set is enumerated: 18 `jca` signature rows collapse into 11 of
  its pairs (`SecureRandom`, `KeyPair`, `CipherInputStream`, `CipherOutputStream`, `SecretKeySpec`,
  `IvParameterSpec`, `GCMParameterSpec`, `PBEKeySpec`, `PBEParameterSpec`, `DHGenParameterSpec`,
  `HMACParameterSpec`) — including `new SecretKeySpec(...)` and `new IvParameterSpec(...)`, which are
  central to JCA misuse. On the frozen fixture (`modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`)
  the fixture carries 11 constructor call sites (`SecretKeySpec` ×5, `IvParameterSpec` ×4,
  `SecureRandom` ×2) in 10 methods, 8 of them flagged by other targets as well; the mapping adds
  `CryptoUtils.createSecretKeyFromBytes` and `CryptographyActivity.executeSecretKeyOperation` to the
  direct axis.

  (c) **`jca`: `RandomStringPassword.mop` contributes its two static targets as STRICT.**
  Its two pointcuts name the owner `String` while the file imports only `java.util.stream.IntStream` and
  three `br.unb.cic.mop.*` packages, so the owner resolves only through the implicit `java.lang` step and
  both targets — `java.lang.String#valueOf(java.lang.Object)` and `java.lang.String#toCharArray()` — carry
  `MatchPolicy.STRICT`. The woven aspect carries both pointcuts
  (`rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879`), so without the targets
  the aspect would advise call sites the static layer never marks, and every `cov_reaches_target`
  computed from `jca` would count 22 of its 23 specs (RISK-013). STRICT is what makes the seed admissible:
  under LENIENT matching (class and name, signature ignored) `String#valueOf` matches every overload —
  over 3 corpus APKs, 74 call sites of `String.valueOf`/`toCharArray` of which only **17** match the
  woven signatures, leaving 57 false positives propagated to their callers by the transitive axis, on
  the spec set that is the published ruler. The successor `jca_android` does not carry the file (a
  `removed-spec` row of `data/jca_android/divergence_record.csv`): it cannot accuse under any trace and
  writes no predicate, while its two targets, even STRICT, reach every Kotlin string template, which
  compiles to `String.valueOf(Object)`.
  **Both match points MUST honour `MatchPolicy.STRICT`.** A `className#methodName` key *is* the lenient
  policy — it readmits exactly the overloads STRICT excludes — and the reverse BFS is seeded with the
  direct set (INV-ANA-64), so a STRICT target admitted leniently on the direct axis returns its false
  positives to the transitive axis. A STRICT target MUST therefore be withheld from the direct scan's key
  set and matched per invoke against the parameter types the call instruction's own descriptor carries
  (`SootMethodRef.parameterTypes()`), by one predicate (`RvsecAnalysisClient.matchesAtCallSite`) that
  agrees with the comparison `TargetResolver.resolveInScene` performs. Measured on `cryptoapp` with a
  single `String.valueOf` target, the policy being the only variable: **24** direct callers under LENIENT
  against **9** under STRICT (design D13).
  **The effect on the frozen set is enumerated** (measured 2026-08-28): the extractor emits `jca`
  **122** signatures / **70** pairs / **23** owners, the difference from the unseeded extractor being
  exactly the two rows above, with no row merged by the FQN
  parameter resolution (row count equals distinct-key count on both sides; the resolution respelled one
  parameter list in each JCA set — `SSLContext.init`, `javax.net.ssl.KeyManager[]` and
  `javax.net.ssl.TrustManager[]` — and 16 in `generic_new`, which stays at 72 rows). On the `cryptoapp`
  fixture `directlyReachesTarget` is **23** — the APK has no app-level call site of either woven
  signature, which is STRICT bounding the seed — and `reachesTarget` is **37**, four of them the default
  constructors of `MainActivity`, `CipherActivity`, `CryptographyActivity` and `MessageDigestActivity`,
  which reach `String.valueOf(Object)` through the framework call graph; running the same APK against a
  copy of `jca` without `RandomStringPassword.mop` yields 120 signatures, 0 STRICT, 33 reaching and 23
  direct, which attributes those four to that one specification. The skipped-owner log for `jca` and
  `jca_android` MUST be empty, and a target whose owner resolved through the implicit package while the
  target stays LENIENT MUST NOT exist. Design **D5** (the seed), **D10** (the STRICT criterion) and
  **D11** (measuring parameter resolution apart from the seed); risk body in RISK-013 of the gh69 risk
  register.

  (d) **Pointcut narrowing is discarded — the one false-*positive* direction.** The extractor keys on
  owner + method name; the `&& args(...)`, `&& target(...)` and `&& condition(...)` conjuncts that narrow
  a pointcut are dropped. Measured by event over `generic_new`: **55 of the 58 `call(` events, 95%**,
  carry some discarded restriction. The `args()` axis recovers nothing: of the 22 events with
  `args(...)`, only **2** narrow a type rather than bind a variable, and neither changes the resolved
  `SootMethod` set — `call(* Set+.add(..)) && args(CharSequence) && !args(String) && !args(CharBuffer)`
  tests the argument at the call site, which neither `resolveInScene` (which sees only `SootMethod`) nor
  the extractor can apply, and `(Collection+, add*)` from `Collection_UnsynchronizedAddAll` already
  covers `Set.add` unrestricted; the other, `Collections.newSetFromMap`, has a single overload. The
  recoverable precision lives in `target()`-of-type: 22 of its 57 occurrences name a type (8 positive,
  14 negated), and it is the only restriction class applicable at the layer where matching happens, since
  both `TargetResolver.resolveInScene` and the bytecode scan hold the receiver type. Two pairs survive the
  union — `CharSequence+.equals`/`hashCode` (over 3 corpus APKs, **100%** of their call sites on a
  `CharSequence` have receiver `java.lang.String`, which the spec's `!target(String)` excludes) and the
  non-`java.io` part of `Closeable+.close` — and applying just those two shrinks the direct seed by
  11–41% (pindroid 153→119, lesserpad 37→22, moneytracker 171→152). Applying them belongs to a separate
  change. The loss is accepted (matching is LENIENT by construction, INV-ANA-35), but it MUST be read
  together with the quasi-universal owners (`Object+`, `Iterable+`): the two compound into the
  saturation of boundary (e). Boundary (a) understates the true target set; (d) overstates it.

  (e) **A corpus property, not a property of this capability: `reachesTarget` is degenerate over the
  `generic_new` fixture.** It follows from *which* APIs those 27 specs monitor (adding to a container,
  iterating, closing a stream), not from how the matcher works, and says nothing about a spec set that
  declares owners by hierarchy over a narrower API family. Measured over 8 corpus APKs (827,443 call
  sites): the transitive flag reaches **84–94%** of app methods over this fixture against 11–47% over
  `jca`, and on 4 of the 8 it exceeds the app's own `reachable` fraction. Owner filtering MUST NOT be
  added to repair it — dropping 34 of the 69 pairs was measured not to move the flag on any medium or
  large APK (quicknote 1752→1752, mupen 2342→2340) — because there is nothing to repair. Over this
  fixture the load-bearing gate assertion is `directlyReachesTarget` (2–12%, discriminating) and
  `reachesTarget` is smoke only. `aperv-tool` reads `reachesTarget`, and that is safe for three reasons:
  (i) the count model's size term is a pre-registration item with no default
  (`estimators/count_glm.py:240-243` raises `FreezeItemUnset` when it is omitted) and both columns are
  emitted side by side (`analysis/static_artifact.py:414-415`), so a degenerate offset cannot be
  inherited silently; (ii) the `hot`/`cold` handler verdict has no in-repo code consumer — it reaches CSV,
  and its readers run against `jca`; and (iii) `sa_methods_reaches_mop` is pinned normatively to
  `reachesTarget` by the `campaign-analysis` capability, so moving it to the direct axis is a change
  against that capability. Gating on the spec set is not available: `<apk>.json` carries no spec-set
  provenance (`package`, `mainActivity`, `reachability`, `windows`, `transitions`, `components`).

- **INV-ANA-41**: `MopSpecsTargetSource.load()` MUST propagate `includeSubtypes` and `nameIsPattern`
  from each `MopMethod` to the corresponding `TargetMethod`. A target derived from a JCA spec (no `+`,
  no wildcard method name) MUST carry `includeSubtypes=false` and `nameIsPattern=false`.

- **INV-ANA-42**: When `includeSubtypes=true`, both target match points — `TargetResolver.resolveInScene`
  (which seeds the reverse call-graph BFS) and `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan`
  (the direct bytecode scan) — MUST match a call site by `nameMatches(pattern) &&
  FastHierarchy.canStoreType(callSiteDeclaringType, declaredSuperType)` evaluated against the **declared
  super-type**, NOT against pre-resolved exact keys. Both match points therefore receive the declared
  `Set<TargetMethod>` (which carries the super-type FQN and the two flags) alongside the resolved
  `Set<SootMethod>`, which has lost them. `nameMatches` MUST be evaluated **before** `canStoreType` (cheap
  name short-circuit before the hierarchy query). The exact (`!includeSubtypes`) targets MUST retain the
  `Set<String>` `class#method` key path (a **hybrid** scan), so the JCA O(1) lookup, performance, and
  parity (INV-ANA-35) hold; STRICT targets are withheld from that key path per INV-ANA-40 boundary (c).
  The predicate MUST match interface→interface (e.g. `java.util.List <: java.lang.Iterable`) so
  interface-typed call sites are covered. When `includeSubtypes=false`, both points MUST use the exact
  `equals(className) && equals(methodName)` path.

  **Cost bound (NFR04).** Widening the predicate removes the `equals(fqn)` fast-reject in
  `resolveInScene` and enlarges the seed set it produces, so this capability MUST NOT make the analysis
  materially slower. The bound is stated over the **sum** of the three stages it touches —
  `TargetResolver.resolveInScene`, the direct bytecode scan, and the reverse BFS that consumes the seed
  set (`ReachabilityEngine.multiSourceBfs`) — which together MUST run within **2×** their `jca` baseline
  on the same APK. Each stage MUST additionally be **reported** against its own baseline, so that a
  regression is attributable; a per-stage ratio above 2× is a finding to enumerate, not a failure.
  A per-stage bound would reject a faster pipeline. Measured 2026-08-28 on
  `net.phbwt.paperwork_1003007` (45 MB, 3763 app methods, 60973 methods in the Scene) under spark,
  `generic_new` against `jca` with nothing else varied:

  | stage | `generic_new` | `jca` | ratio |
  |---|---|---|---|
  | `resolveInScene` | 2734 ms | 892 ms | **3.07×** |
  | bytecode scan | 148 ms | 52 ms | **2.85×** |
  | reverse BFS | 246 ms | 3545 ms | **0.07×** |
  | **sum** | **3128 ms** | **4489 ms** | **0.70×** |

  Two stages exceed 2× and the third is 14× cheaper, because seeding the BFS more widely is not giving it
  more work: 5661 seeds against 239 fill the visited set almost immediately, so it marks more methods
  (49039 against 30014) while traversing each edge once instead of walking long chains. The three stages
  together are ~3 s of a run whose wall clock on that APK is ~51 minutes. The two mitigations that keep
  the sum there are mandatory: ordering `nameMatches` before `canStoreType`, and caching the resolved
  super-type `RefType` once per target.

- **INV-ANA-43**: Before `FastHierarchy.canStoreType` is queried, each declared target owner FQN MUST
  be force-resolved into the Soot `Scene` at HIERARCHY level or above. Because GATOR runs Soot with
  `allow_phantom_refs=true`, `forceResolve` of a name Soot cannot find yields a **phantom** `SootClass`
  that satisfies `Scene.containsClass` yet carries no hierarchy; it resolves at `SIGNATURES`, so
  `checkLevel(HIERARCHY)` passes and `canStoreType` returns a **definite `false`** — it does **not**
  throw, and it silently masks a false-negative. So `containsClass` alone MUST NOT be the guard.
  **`isPhantom()` MUST NOT be the guard either.** Measured on the real Scene (`cryptoapp.apk`, API 33,
  2026-08-28): under `-force-android-jar` the `java.*`/`javax.*` owners of both spec sets are read out of
  the platform `android.jar` with a complete and correct hierarchy — real superclass, real interface
  list, real `ACC_INTERFACE` modifier — and are flagged phantom nonetheless (**522 of 575** JDK classes
  in the Scene), while `canStoreType` answers correctly over all of them, interface-to-interface
  included (`java.util.List <: java.lang.Iterable`). Keying the degrade on the flag would degrade every
  declared owner of both spec sets and switch the subtype axis off entirely.

  The degrade criterion MUST therefore be: the owner is absent, OR `resolvingLevel() < HIERARCHY`, OR
  the resolved class **carries no hierarchy content** — i.e. it has no superclass AND no interfaces AND
  no methods, which is what a class Soot invented for a missing source measures (`getModifiers() == 0`
  as well). The three content clauses MUST be a disjunction, so that a marker interface such as
  `java.io.Serializable` is not rejected for declaring no methods. An owner failing the criterion MUST
  degrade to exact `equals` matching and the degradation MUST be logged (no silent false-negative).
  `canStoreType` MUST NOT be called with an absent owner or one that carries no hierarchy content.
  **Ordering**: the owners MUST be force-resolved *before* the `FastHierarchy` used to answer
  `canStoreType` is obtained, and that `FastHierarchy` instance MUST NOT be cached across a resolution.
  This capability does not require force-resolution to precede every `getOrMakeFastHierarchy()` call in
  the process — that is unsatisfiable, since SPARK materialises the hierarchy during the `cg` pack,
  before any client analysis runs — and it need not: `Scene.addClass` invalidates the cached
  `FastHierarchy` via `modifyHierarchy()`, so resolving a not-yet-present owner rebuilds it. For an owner
  already present that was upgraded **in place** (the one case `addClass` does not cover)
  `Scene.releaseFastHierarchy()` MUST be called before the rebuild. It MUST NOT be called merely because
  an owner is flagged phantom: per the paragraph above that is the common case, and such an owner is not
  modified by the resolution.

- **INV-ANA-44**: The GATOR JSON output schema MUST be unchanged by this capability — no new, renamed,
  or removed keys. The key set of a `generic_new` run MUST be identical to that of a `jca` run; only
  the boolean values of `reachesTarget`/`directlyReachesTarget` differ. INV-ANA-35 (JCA byte-for-byte
  parity in `MopSpecsTargetSource.load()` vs the historical `loadMopSignatures`) MUST remain satisfied.

- **INV-ANA-46**: `parse_logcat_line` MUST retain its signature `Tuple[Optional[RvErrorLog], Optional[RvCoverageLog]]` and its existing behavior for RVSEC/RVSEC-COV lines, with one stated exception: RVSEC lines whose `class`/`method` fields are in frame form now yield normalized values. The golden output MUST be byte-identical to baseline for every line that does not carry a frame-form value; for the lines that do, the golden baseline is re-frozen and the diff MUST be confined to the `class_full_name`, `method` and `source` fields of those lines.
- **INV-ANA-47**: Tag recognition MUST match the parsed threadtime *tag field*, never a substring of the message; a `RVSEC-COV` line whose message contains `isAndroidRuntime()` MUST NOT produce a diagnostic event.
- **INV-ANA-48**: A multi-line crash block sharing one `(tag, pid, tid)` MUST yield exactly one `RvDiagnosticEvent`; lines that do not match the threadtime regex (e.g. `--------- beginning of crash`) MUST be skipped without error. Such a line remains a real boundary and still closes an open block: unlike a foreign-tag line, it is written by logcat itself to mark a discontinuity, not by another process that merely happened to log.

- **INV-ANA-53**: The full static-analysis JSON SHALL remain byte-identical after any derivation, and
  SHALL remain the sole static-analysis input of every metric computation, gate and offline
  consolidation path. No metric or analysis code SHALL read a `*.mop.json` artifact.
- **INV-ANA-54**: The derived artifact SHALL be a strict downstream projection: the producer, its
  schema and its `"complete": true` sentinel SHALL be unaffected by its existence, and no producer
  behaviour SHALL be conditioned on whether an artifact was derived.

- **INV-ANA-56**: A logcat line whose parsed tag field is not a diagnostic tag MUST be transparent to diagnostic block assembly. It MUST yield no event and MUST NOT close an open block. Logcat merges every process into one timestamp-ordered stream, so a line under a foreign tag arriving between two lines of a block is the expected case and carries no information about whether that block has ended. Closing on it truncates the event at the interleaving point and discards its remaining lines, and both losses are silent.

- **INV-ANA-57**: A caller driving the parser directly MUST call `flush()` at end of input. With foreign-tag lines transparent, a block is closed by a diagnostic key change, a new block start, a non-threadtime line, or `flush()` — so a block at the end of the input is emitted only by the flush. `parse_logcat_file` flushes internally; `CoverageTracker` flushes after its final drain, in that order, so a block completed by the drained lines is emitted rather than discarded.
- **INV-ANA-49**: For every entry registered by `parse_logcat_file` when `tool_execution_start` is non-`None` and the entry has a parseable `time_occurred`, `time_since_task_start` MUST equal `max(0, int((time_occurred − tool_execution_start).total_seconds()))` — identical to the live `CoverageTracker._process_line` arithmetic, including the clamp to zero for entries buffered from before tool start. When `tool_execution_start` is `None`, `time_since_task_start` MUST remain `0` and the degraded state MUST be logged; no component may substitute a fabricated value for it downstream.
- **INV-ANA-50**: `parse_logcat_line` MUST NOT return an `RvErrorLog` whose `class_full_name` or `method` ends with a `(<file>:<line>)` group. Any such value present in the emitted message MUST be normalized before the record is constructed.
- **INV-ANA-51**: Normalization MUST be idempotent and MUST be a no-op on well-formed values: for any value `v` that does not end with a `(<file>:<line>)` group, `normalize(v) == v` byte-for-byte, and for any value at all, `normalize(normalize(v)) == normalize(v)`.
- **INV-ANA-52**: The normalization guard MUST be anchored on the trailing group only. It MUST NOT constrain the prefix, because real method names in the corpus contain spaces and nested parentheses. Verified by the corner-case corpus, which includes `…CryptoMigrationV2CompatibilityTest.V2-header files (3xx format) are still decryptable after reading a V1-header file(CryptoMigrationV2CompatibilityTest.kt:131)`.

- **INV-ANA-58**: No component of the analysis pipeline MUST derive a filtering key from an existing analysis artefact. The `package` member of a GATOR JSON is the manifest package as GATOR read it and MUST NOT be treated as the key that filtered that file. A run that **performs** an analysis MUST record the key it used and its origin; it MUST NOT infer, repair, or override a key on the basis of a stored artefact. The invariant governs the **production** path only, because parsing no longer uses a key.

- **INV-ANA-59**: The `StaticAnalysisParser` MUST load every entry of the `reachability` member of an analysis artefact and MUST NOT filter that member by any package key. The artefact is scoped by its producer, so the parsed method universe MUST equal the artefact's `reachability` member exactly, and the coverage denominator MUST equal that universe.

- **INV-ANA-60**: The `StaticAnalysisParser` MUST scope `ACTIVITY` windows by membership in the artefact's `reachability` member: an `ACTIVITY` window MUST be admitted if and only if its class name, as the artefact spells it, is present there. Window types other than `ACTIVITY` MUST be admitted unconditionally, because they can be system-provided overlays triggered by application code. No package key MUST participate in this decision.

- **INV-ANA-61**: No function on the analysis **consumption** path — `StaticAnalysisParser.parse_file`, `read_static_analysis_files`, and their callers in `rv-platform` — MUST accept, resolve, or pass a package key. Resolving a scope is a **production**-path concern only.

- **INV-ANA-62**: No logcat line MUST be discarded silently. For every line `parse_logcat_file` or `CoverageTracker` reads that does not become an `RvErrorLog`, an `RvCoverageLog` or a diagnostic-block line, exactly one counter of `ParserDiagnostics` MUST be incremented — `lines_not_threadtime`, `lines_other_tag`, `format1_regex_failed`, `format2_short`, `format3_unresolved`, `unrecognised` or `continuation_lines` — and every value the parser substitutes for a value the producer did not supply MUST be counted under the matching `sentinel_*` counter. `parse_logcat_file` MUST NOT catch an exception raised while iterating the file and return the repository built so far; it MUST log the line number and re-raise. The sum of records registered plus lines counted MUST equal the number of lines read.

- **INV-ANA-63**: An envelope whose last quoted value is not closed MUST be treated as a truncated record: `truncated=True`, the record registered and counted under `truncated_envelopes`, and no field parsed from the unclosed value onwards (the fields before it are kept). Logcat cuts a payload at `LOGGER_ENTRY_MAX_PAYLOAD` (4068 bytes) without a marker and a `\n` inside a value ends the line at that byte, so an unclosed quote is the only evidence the parser has that the record it holds is not the record the monitor wrote. A value containing `:::` MUST be kept verbatim, the record registered, and `envelope_forbidden_chars` incremented — the producer contract, not the parser, forbids the character.

- **INV-ANA-64**: `ReachabilityEngine.run()` MUST compute the direct-caller set **before** the
  transitive one, and MUST seed the reverse BFS with `targets ∪ directTargetSet` rather than with
  `targets` alone. The containment `reachesTarget ⊇ directlyReachesTarget` — definitional, since a
  direct caller is a path of length 1 — then holds **by construction** for every method the call graph
  contains. Rationale: the two fields are computed from two different oracles. `directlyReachesTarget`
  is the union of the call-graph callers and the bytecode scan that repairs BUG-INV-ANA-19 (SPARK
  quarantines app→library edges); `reachesTarget` is a reverse BFS over the call graph alone, which that
  scan does not reach. Seeded with `targets` alone, the engine was measured to violate the containment
  on 14 flags across 6 distinct methods in 2 APKs of the 269 `*.apk.json` in the tree
  (`app.notesr_59`, `com.beemdevelopment.aegis_81`), 12 of the 14 on methods with `reachable=false` —
  methods SPARK never processed, which carry no call-graph vertex at all. `multiSourceBfs` calls
  `graph.addVertex(seed)` before its visited check, so a seed absent from the graph needs no defensive
  code.
  **No consumer-side enforcement**: `JsonReportWriter` MUST NOT gate, assert, or abort on a residual
  case, and the analysis MUST continue normally. The residual this seeding cannot remove is a method the
  bytecode scan discovers whose *callers* are themselves absent from the call graph — that yields an
  unmarked ancestor, i.e. a false negative on the transitive axis, never a violated containment.
  Observability, if wanted, belongs in the `[ReachabilityEngine]` counter line, not in a failing gate.
  The containment is asserted by `tests/parity/test_reachability_parity.py`
  (`test_directly_reaches_target_is_subset_of_reaches_target`), which runs GATOR over `cryptoapp` with
  the `jca` specs only; the two APKs where the unseeded engine violated it are outside that test, so the
  guarantee is the seeding, not the test's coverage.

- **INV-ANA-65**: `AnalysisEntrypoint` MUST resolve the package that guards the application/library demotion from `Configs.getClientParamCode("codePackage=")`, falling back to the manifest `package` attribute only when the client parameter is absent. The guard in `AnalysisEntrypoint` and the filter in `RvsecAnalysisClient` MUST resolve to the same value in every run, so that the set the guard protects is exactly the set the client will filter.

- **INV-ANA-66**: The analysis artefact MUST record the scope key that produced it, that key's origin, and the count of compiled classes under that key. The `package` member MUST continue to hold the manifest package as GATOR read it (INV-ANA-58), and the effective key MUST be recorded in a distinct member, so that no reader has to infer one from the other. The count — `class_defs_under_key` — MUST be recorded beside the key, because it is what makes the denominator gate a **pure predicate over the artefact**: evaluable at every consumption point, including resume and `--process-results`, which re-parse `.apk.json` with no APK within reach. It MUST be produced by applying `RvsecAnalysisClient.isAppClass` — the very predicate that filters the parsed side — to the compiled universe under the key, which the client reads from `Scene.getClasses()`; the demotion does not shrink that set, because `setLibraryClass()` reclassifies a class without removing it. One predicate, both sides: the ratio the gate computes compares like with like by construction, and no consumer is asked to perform a subtraction for which it holds a count and not the names. The origin MUST reach the producer on a channel of its own, `-clientParam codePackageSource=<manifest|manifest-neutralized|detector>`, because `codePackage=` carries the key and not where it came from.

- **INV-ANA-67**: The `StaticAnalysisParser` MUST store class names, window names and method signatures exactly as the artefact spells them. No normalization, repair or transformation of any identifier MUST occur on the consumption path. The producers of both sides of the crossing emit the JVM binary name, so any transformation applied to one side alone breaks an agreement that already holds. Measured on the raw logcat of `com.hwloc.lstopo_271`: of its 17 distinct `RVSEC-COV` class names, every `$` sits at genuine nesting (`About$1`, `MainActivity$MenuItems`) and every package boundary is a dot.

- **INV-ANA-68**: `ParserDiagnostics` MUST count every discarded runtime event, separating **out-of-scope** discards (the class is not under the effective scope key — the application did not own it) from **in-scope** discards (the class is under the key but absent from the denominator, or present with a signature that does not match), with a third counter, **unclassified**, for discards under a key of `None` (INV-CORE-60). The three are different failures and MUST NOT be summed with each other. None of the three MUST enter `ParserDiagnostics.discarded_lines`: they count lines that **did** become records, the same reason that property excludes the sentinel and grammar counters — so the INV-ANA-62 identity (records registered plus counted lines equals lines read) holds. The counters MUST be serialized by `to_dict()`; `unmatched_out_of_scope` and `unmatched_in_scope` MUST reach the run's CSV output as columns (INV-PLT-34), while `unmatched_unclassified` is serialized but has no published column — a row with no key is `measured=false`, which already carries the fact (INV-PLT-36).

- **INV-ANA-69**: The denominator gate (`DenominatorImplausibleError`) MUST refuse three distinct conditions and MUST fail loudly rather than publishing a percentage: an **empty** denominator (`reachability` holds no entries); a **compiled universe of zero** (`class_defs_under_key == 0`, which under the default policy was measured as the state of 75 of the 162 corpus APKs, and which makes `parsed / compiled_under_key` a `ZeroDivisionError` rather than a refusal); and a **degenerate** denominator, whose ratio of parsed to compiled classes under the key falls below `0.15`. The ratio MUST be computed over a compiled count that `isAppClass` has already filtered at write time (INV-ANA-66), so that both of its terms answer to one predicate. The gate divides; it MUST NOT attempt a subtraction of its own, holding a count and not the names. A denominator of one class out of a compiled universe of 771 is not empty, and a gate testing only for emptiness would admit every collapsed artefact of that shape. The gate covers the **class** universe only: `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target` carry denominators of their own that the gate does not inspect, and those denominators still answer to `libPackages.txt` — the demotion shapes `Hierarchy.appClasses` and from it the `reachable`, `reachesTarget` and `directlyReachesTarget` predicates. What INV-ANA-65 takes away from the deny-list is the **class** denominator, not those three.

- **INV-ANA-70**: A stored analysis artefact MUST NOT be reused as a cache hit unless the key it records equals the run's effective scope key: the filename carries no key, and the artefact's `package` member holds the manifest package whatever key filtered the file, so only the recorded key (INV-ANA-66) identifies what produced it. A run whose effective key differs from the recorded one MUST regenerate the artefact or abort naming both keys; it MUST NOT evaluate an artefact produced under one key against another, which is what a denominator gate wired over a stale cache hit would do. `rv-static-analysis --force` MUST discard the artefact the cache would answer with, before the analysis runs; it is the one **deliberate** invalidation path, and it is not a substitute for the key comparison — an operator re-measuring the same key against a rebuilt jar needs a way to say so, and the comparison fires only when the keys disagree.

- **INV-ANA-71**: Generated resource classes MUST leave the denominator at **every** package segment, not only at the scope key's root. The test in `RvsecAnalysisClient.isAppClass` MUST be on the **last segment** of the class name — `R`, `R$*`, `BuildConfig`, `Manifest`, `Manifest$*` — wherever that segment sits under the key: a suffix test against `<key>.R`, `<key>.R$*` and `<key>.BuildConfig` keeps `<key>.<module>.R`, and a key that is an ancestor of the resource namespace escapes it entirely. Measured over the 162 corpus artefacts produced by the root-only test, 505 such classes sat in the denominator (117 in `app.pachli_50` alone, 33 in `com.blacksquircle.ui_10028`), carrying 547 methods of which **zero** are non-trivial: they are constant tables with nothing to cover, and their only effect was to depress `cov_class`. Artefacts produced before this rule and after it are therefore not comparable on `cov_class`. Output of annotation processors (`_Factory`, `_Impl`, `_MembersInjector`, `$$serializer`, `Hilt_*`, `Dagger*`, DataBinding) is deliberately **not** covered: 5,816 such classes carry 36,264 non-trivial methods that execute at runtime, so removing them would redefine the denominator rather than close a leak; that measurement is an open question.
## Requirements
### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing four data sections written in priority order: (1) method reachability relative to a `TargetMethodSource` (coverage denominator), (2) window and widget inventory with event listeners, **populated regardless of WTG completion status (INV-ANA-20)**, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and target reachability. The JSON output MUST end with a sentinel `"complete": true` as the last top-level field on successful completion (INV-ANA-31).

The partial-write path (`wtg == null`) MUST emit a populated `windows[]` section using the same `extractWindows` helper as the full-write path, supplying `Collections.emptyMap()` for `windowNodeIds` and `null` for the WTG handle (INV-ANA-20). The catch-all loop over `wtg.getNodes()` (which adds fragment/context-menu windows not enumerated by `output.getActivities()`/`getDialogs()`/`getOptionsMenu()`) is guarded by `if (wtg != null)`; its absence in the partial path is the only widget-data difference between the two paths.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. Following decomposition, `RvsecAnalysisClient` is an orchestrator (~200 LOC) that wires four single-responsibility components plus a streaming enricher: `TargetResolver` (loads from a `TargetMethodSource` and resolves into Soot `Scene`), `ReachabilityEngine` (builds JGraphT call graph, runs multi-source BFS, complements with bytecode scan), `ReachabilityIndex` (encapsulated lookup ADT), `ReachabilityEnricher` (per-node visitor that annotates each window/transition/component/method on the fly using `ReachabilityIndex`, called by the writer during the section walk — NOT a batch materializer), and `JsonReportWriter` (incremental walker that emits each section to the output stream and flushes immediately, invoking `ReachabilityEnricher` callbacks per node to obtain the annotated values; `flush()` per section preserves partial recovery on timeout). The `JsonReportWriter` MUST NOT itself call any `ReachabilityIndex` lookup method (INV-ANA-30); all flag decisions go through the injected `ReachabilityEnricher` callback interface, which is purely a delegate — the writer holds no direct reference to the index.

GATOR initializes Soot once with defensive configuration (INV-ANA-16), builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the orchestrator writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file (no sentinel emitted — `complete` is absent or implicitly `false`). The writer MUST NOT buffer all sections into memory before serialization — this would defeat the partial-recovery guarantee when timeout is the dominant failure mode (~30-50% of large sweeps per gh57 ground truth). Each section is enriched and emitted in one stream, then flushed before the next section is computed.

The `Flowgraph.processApplicationClasses()` method MUST handle individual method failures gracefully (INV-ANA-17). When `retrieveActiveBody()` or `createOpNode()` throws an exception for a specific method, the Flowgraph MUST skip that method and continue processing remaining methods. The resulting Flowgraph may be incomplete (missing OpNodes, widgets, or listeners for skipped methods), but the GUIAnalysis pipeline MUST complete and the `RvsecAnalysisClient` MUST produce JSON output. Reachability data (computed from `Scene.v().getCallGraph()` via BFS) is NOT affected by Flowgraph incompleteness — it depends on the Soot call graph, not on the Flowgraph.

The GATOR MUST use Soot 4.7.1 (`org.soot-oss:soot`, INV-ANA-18) with defensive configuration (INV-ANA-16). The `ClassHierarchy.typeNode()` bug (soot-oss/soot#1071) is not fixed in Soot 4.7.1, but the improved Dexpler in 4.x reduces crash frequency. The defensive options (excluding `kotlin.*`, `kotlinx.*`, and `androidx.compose.*` from body loading, disabling `jb.sils`/`jb.dae`) further reduce the crash surface.

Crash recovery is bounded by phase: failures inside `Flowgraph.processApplicationClasses()` are method-local (skip method, continue — INV-ANA-17) and the analysis pipeline completes. Failures inside Soot's call-graph construction phase (e.g., SPARK `InternalTypingException`) are NOT recoverable at the Flowgraph level — the JVM exits with a non-zero code and no JSON is produced. This boundary is load-bearing: it prevents the silent emission of a "complete-looking" report built on a corrupt call graph. Together, these recovery rules form a layered defense — prevention (defensive Soot config), method-local skip (Flowgraph try-catch), and hard halt (call-graph phase) — each at a distinct layer with non-overlapping responsibility.

When comparing analysis output against a baseline (e.g., gh57 commit `b2e04a26`), tolerances reflect Soot 4.7.1 non-determinism: for set-based reachability comparisons the contract is **strict equality** (BFS is deterministic over a fixed call graph and target set); for cardinality metrics derived from Flowgraph skips (window/transition/widget counts) a ±10% tolerance is permitted to absorb crash-frequency variation across Soot runs. `directlyReachesTarget` MUST be a strict superset or equal to the baseline `directlyReachesMop` set (BUG-INV-ANA-19: the bytecode-scan complement can only add direct callers SPARK missed, never remove them).

The execution order inside `run()`:

1. **Loads target methods via `TargetMethodSource` and resolves into Soot `Scene`**. The source is constructed from CLI input: `--mop-dir <dir>` yields a `MopSpecsTargetSource` wrapping `JavamopFacade.listUsedMethods(mopDir, false)`; `--targets-file <path>` yields a `SignatureFileTargetSource` parsing a text file of Soot signatures (one per line, `#` comments, blank lines tolerated). The two CLI flags are mutually exclusive (INV-ANA-33). The `TargetResolver` calls `source.load()` to produce a `Set<TargetMethod>`, then resolves each to one or more `SootMethod` instances per the source's matching policy: LENIENT (class+name only) for `MopSpecsTargetSource` because AspectJ wildcards in `.mop` specs leave the full signature semantically undefined; STRICT (full Soot signature) for `SignatureFileTargetSource` because the user controls precision. Wildcard parameter lists in a targets-file entry (`(..)` or `(*)`) resolve LENIENT for that entry only.

2. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). For each application method, the `ReachabilityEngine` computes: `reachable` (reachable from entry points), `reachesTarget` (has path to a resolved target method — renamed from `reachesMop`), and `directlyReachesTarget` (directly invokes a resolved target method — renamed from `directlyReachesMop`). The `ReachabilityIndex` materializes these as `Set<String>` for O(1) lookup. This section is written and flushed first.

3. **Extracts windows and widgets** using GATOR's internal APIs (`getActivities()`, `getActivityRoots()`, `getDialogs()`, `getDialogRoots()`, `getOptionsMenu()`, `PropertyManager`). GATOR's interprocedural analysis provides the widget inventory (IDs, names, types, text, hint, listeners) including dynamically-registered listeners. Widget XML attributes not available via GATOR APIs — `inputType`, `entries` (from `android:entries="@array/X"`), and the four attributes `prompt`, `spinnerMode`, `contentDescription`, `tooltipText` — are extracted by `enrichFromXml()` from the decoded layout XML files at `Configs.resourceLocation`. The `windows[]` section is written in both the partial-JSON path (after reachability, with `wtg=null`) and the full-JSON path (after WTG completion, with the WTG handle for numeric ID assignment and catch-all enumeration).

4. **Extracts the Window Transition Graph** using GATOR's `WTGBuilder` and `WTGAnalysisOutput`, producing window IDs, transition edges with event types, widget IDs, and handler signatures. WTG construction MUST use `Scene.v().getCallGraph()` (the SPARK CG already built by Soot) as the single source of virtual-dispatch resolution when the `cgDelegation` client parameter is `true`; `AndroidCallGraph.v()` MUST NOT be populated by `FlowgraphRebuilder.buildCallGraph()` in this mode (INV-ANA-21). The legacy `AndroidCallGraph` rebuild via `FlowgraphRebuilder.buildCallGraph()` MUST be preserved behind `cgDelegation=false` (default after the M3 paridade-gate decision in `docs/20260515_diagnostico_paridade_cgdelegation.md`), where rollback is bit-for-bit. Edges to library classes quarantined by SPARK's `IGNORED_CLASSES` are recovered via a WTG-level bytecode-scan complement (INV-ANA-22). WTG construction is skipped entirely when the `skipWtg` client parameter is `true` (see the `skipWtg` ADDED requirement), in which case `transitions[]` is emitted as an empty array.

5. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager`, `android:exported` attribute, and target reachability cross-referenced with the reachability BFS results. This section is written and flushed last.

6. **Emits sentinel `"complete": true`** as the final top-level field, after all sections are flushed. Parser uses this to distinguish a successful run from a truncated one (INV-ANA-31).

The `complementWithCallbacks()` method, which propagates target reachability flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null` when the method belongs to no component) and `isMain` (boolean) fields. The legacy `isActivity` and `isMainActivity` fields are removed (no shim — P3). The `StaticAnalysisParser` (Python) MUST parse the new fields into the `Clazz` domain model as `component_type: str | None` and `is_main: bool`. The `null` handler exists because `getSootClassUnsafe` may return `null` for methods declared on synthetic or excluded classes; the producer emits `componentType=null` rather than dropping the entry, preserving the reachability set cardinality.

All JSON keys MUST be emitted via constants in `presto.android.gui.clients.json.JsonSchema.Keys` (Java) and consumed via `_JK = SimpleNamespace(...)` in `rv_static_analysis.parser.static.static_analysis_parser` (Python). The two constant sets MUST be value-equal (INV-ANA-32) — verified by `tests/parity/json_keys.py`.

The analysis JSON output is parsed by `StaticAnalysisParser` into the `StaticAnalysisData` domain model (Classes, Windows, WindowTransitionGraph, Components, `complete: bool`). Downstream consumers (rv-coverage, rv-platform, rv-experiment, aperv-tool, scripts) receive renamed Pydantic fields per the `core` spec delta. rv-agent (deprecated) is not a live consumer; sweep regenerates JSONs and breaks rv-agent's stale reader by design.

The reachability section defines the **method universe** — the total set of reachable methods that serves as the denominator for all coverage percentage calculations. Without reachability data, the system can count absolute method calls but cannot compute coverage percentages.

The reachability section also provides target prioritization data consumed by agents. The agent's action ranker assigns score boosts to actions whose handler method has `directly_reaches_target=true` or `reaches_target=true` (consumer side details outside this spec).

The call graph is built using SPARK (`-cgAlgorithm spark`) with `all-reachable:true`, which performs full points-to analysis to resolve virtual calls based on types effectively instantiated in the program. SPARK is the operational default. Other algorithms — CHA, RTA, VTA — remain available. JCA framework classes appear as call targets whenever any application method invokes them — they do not need to be entry points.

**Module**: rv-static-analysis (launcher + parser — modified for `--targets-file`, `_JK`, sentinel check), rvsec-gator (analysis client — decomposed + renamed + sentinel-emitting)
**Key components**: `Main.java` (Soot config), `Flowgraph.java` (error handling), `RvsecAnalysisClient` (orchestrator, ~200 LOC post-decomp), `TargetMethod`, `TargetMethodSource`, `MopSpecsTargetSource`, `SignatureFileTargetSource`, `TargetResolver`, `ReachabilityEngine`, `ReachabilityIndex`, `ReachabilityEnricher` (visitor callback, no `ReportModel` materialization), `JsonReportWriter` (streaming walker with `flush()` per section), `JsonSchema.Keys`, `JsonSchemaKeysDump` (reflection-based parity dumper), `JimpleDefUtils`, `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser` (consumes `_JK` + sentinel; builds `window_methods_index` for `WindowTransition.target_reaches_target`), `Clazz`.

#### Scenario: Successful static analysis with valid APK using --mop-dir

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path, the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`, and the user passed `--mop-dir <dir>` on the CLI
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -cgAlgorithm spark`
- **AND** the producer MUST instantiate `MopSpecsTargetSource(Path(mopDir))` and `TargetResolver` MUST resolve targets LENIENT (class+name)
- **AND** the resulting `.json` file MUST end with `"complete": true` as the final top-level field
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` with `complete == True`
- **AND** all JSON keys present in the output MUST match values declared in `JsonSchema.Keys`

#### Scenario: Successful static analysis using --targets-file

- **WHEN** the user invokes `rv-static-analysis --targets-file demo.txt <apk>` and `demo.txt` contains lines such as `<javax.crypto.Cipher: void init(int,java.security.Key)>` and `# comment` and blank lines
- **THEN** the CLI MUST accept the invocation (mutex group permits exactly one of `--mop-dir` or `--targets-file`, INV-ANA-33)
- **AND** GATOR MUST be invoked with `-clientParam targetsFile=<path>` instead of `mopDir=...`
- **AND** the producer MUST instantiate `SignatureFileTargetSource(Path(targetsFile))` and `TargetResolver` MUST resolve targets STRICT (full signature) for non-wildcard entries
- **AND** entries containing `(..)` or `(*)` MUST resolve LENIENT for that entry only
- **AND** the output JSON MUST follow the same schema as the `--mop-dir` path (same keys, sentinel last)

#### Scenario: CLI mutex rejects passing both --mop-dir and --targets-file

- **WHEN** the user invokes `rv-static-analysis --mop-dir /m --targets-file /t <apk>`
- **THEN** the argparse mutex group MUST emit an error to stderr explaining `--mop-dir` and `--targets-file` are mutually exclusive
- **AND** the process MUST exit with a non-zero return code before launching GATOR

#### Scenario: CLI rejects passing neither --mop-dir nor --targets-file

- **WHEN** the user invokes `rv-static-analysis <apk>` without specifying any target source
- **THEN** the argparse mutex group MUST emit an error indicating one of `--mop-dir` or `--targets-file` is required
- **AND** the process MUST exit with a non-zero return code

#### Scenario: --targets-file with malformed signature line

- **WHEN** the targets-file contains a line that is not blank, not a `#` comment, and is not a valid Soot signature (e.g., `Cipher.init` without angle brackets)
- **THEN** `SignatureFileTargetSource.load()` MUST raise `IllegalArgumentException` with the offending line number and content
- **AND** the GATOR process MUST exit with a non-zero code before producing any JSON

#### Scenario: MopSpecsTargetSource preserves baseline byte-for-byte

- **WHEN** GATOR analyzes `cryptoapp.apk` with `--mop-dir cryptoapp.mop` using the decomposed pipeline (`TargetResolver` + `ReachabilityEngine`)
- **THEN** the resulting `set(method.signature for method in data.methods if method.reaches_target)` MUST be equal to the same set computed from the gh57 baseline at commit `b2e04a26` (`reaches_mop` semantically — set comparison transparent to rename)
- **AND** the resulting `set(method.signature for method in data.methods if method.directly_reaches_target)` MUST be equal to the corresponding baseline set
- **AND** `cryptoapp.apk` MUST report exactly 16 target methods (INV-ANA-35)

#### Scenario: WTG timeout still produces populated windows[] in partial JSON

- **WHEN** GATOR analyzes an APK whose WTG construction exceeds the external sweep timeout (e.g. `ac.mdiq.podcini.X_256.apk` from the original-APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/`), and the Java process is killed via SIGTERM during `WTGBuilder.build()`
- **THEN** the JSON file written before the kill MUST contain a fully-populated `windows[]` section with all activities, dialogs, options-menu skeletons, and their widgets (including listeners, text, hint, inputType, entries) extracted from `GUIAnalysisOutput`
- **AND** the JSON `transitions[]` MUST be `[]` (empty array, not missing)
- **AND** the JSON `windows[].widgets[]` MUST NOT contain the catch-all WTG-only entries (fragments, context menus that depend on `wtg.getNodes()` enumeration) — these are skipped because `wtg == null` (INV-ANA-20)
- **AND** numeric `windows[].id` values MUST come from the `fallbackId` sequence (starting at `100000`) or from `dialog.id`/`menu.id` fallbacks, since `windowNodeIds` is an empty map in the partial-write path

#### Scenario: WTG built using legacy call graph (cgDelegation=false, default post-M3)

- **WHEN** `RvsecAnalysisClient.run()` is invoked with default client parameters (`cgDelegation` defaults to `false` per `docs/20260515_diagnostico_paridade_cgdelegation.md`)
- **AND** `WTGBuilder.build(output)` is called and reaches `FlowgraphRebuilder.buildCallGraph()`
- **THEN** `FlowgraphRebuilder.buildCallGraph()` MUST take the legacy points-to + CHA-fallback code path (`buildCallGraphLegacy` — `hier.virtualDispatch()` + `hier.getConcreteSubtypes()`)
- **AND** `AndroidCallGraph.v()` MUST be populated as before the change
- **AND** the output `transitions[]` MUST match exactly the pre-change baseline for the same APK on this code path (rollback is bit-for-bit on the WTG section)

#### Scenario: WTG built using SPARK call graph (cgDelegation=true, opt-in)

- **WHEN** `RvsecAnalysisClient.run()` is invoked with `-clientParam cgDelegation=true`
- **AND** `WTGBuilder.build(output)` is called and reaches `FlowgraphRebuilder.buildCallGraph()`
- **THEN** `FlowgraphRebuilder.buildCallGraph()` MUST consult `Scene.v().getCallGraph()` to resolve virtual-dispatch targets for each `InvokeExpr` site
- **AND** `AndroidCallGraph.v()` MUST NOT be populated via the legacy CHA-style loop (INV-ANA-21)
- **AND** for `InvokeExpr` sites whose declared callee class is in `IGNORED_CLASSES` (SPARK quarantine — `java.*`, `javax.*`, `sun.*`, `android.*`, `androidx.*`, `dalvik.*`), edges MUST be recovered via the WTG-level bytecode-scan complement (INV-ANA-22)

#### Scenario: Hybrid-framework apps lose transitions in cgDelegation=true mode

This scenario documents a known limitation of the opt-in SPARK delegation path until a follow-up change ports the CHA fallback at application-class scope for zero-edge invoke sites.

- **GIVEN** an APK whose UI listener dispatch is routed through synthetic lambdas (`$$ExternalSyntheticLambda*`) declared in application packages, instantiated through native bridges (React Native, Flutter, Capacitor)
- **WHEN** the analyzer runs with `-clientParam cgDelegation=true`
- **THEN** the WTG MAY fail to create WTGNodes for the entry activities (the SPARK call graph lacks the edges that signal "this activity is live")
- **AND** the resulting `transitions[]` section MAY be empty for those apps
- **AND** the activities WILL appear in `windows[]` with fallback IDs (≥100000)
- **AND** consumers MUST treat an empty `transitions[]` paired with fallback-IDed windows as an analyzer limitation, not a "no transitions exist" assertion (reference: `docs/20260515_diagnostico_paridade_cgdelegation.md`)

This limitation does NOT apply to `cgDelegation=false` (the default), which uses the legacy CHA fallback over application-class subtypes and captures these lambdas.

#### Scenario: GATOR crashes during call graph construction

- **WHEN** Soot's call-graph builder throws an `InternalTypingException` during call graph construction for a method in a Kotlin class
- **THEN** the GATOR process MUST terminate with a non-zero exit code
- **AND** no `.json` output file MUST exist (the crash occurs before `RvsecAnalysisClient.run()` is invoked)
- **AND** the `StaticAnalyzer` wrapper MUST log the failure as `StaticAnalysisException`
- **AND** the `StaticAnalysisResult.analysis_file` MUST point to the expected output path (which does not exist)

#### Scenario: Timeout during JSON write produces truncated file without sentinel

- **WHEN** GATOR is killed by external timeout enforcement mid-way through `JsonReportWriter.write` (e.g., after `windows[]` is flushed but before `transitions[]` is complete)
- **THEN** the partial JSON file on disk MUST NOT contain the `"complete": true` sentinel
- **AND** `StaticAnalysisParser` MUST parse what is available via `_recover_truncated_json` (load-bearing recovery)
- **AND** `StaticAnalysisData.complete` MUST be `False` (Pydantic default for absent key)
- **AND** downstream gates requiring completeness MUST exclude this sample

#### Scenario: Flowgraph skips method with failing body (Scenario B recovery)

- **WHEN** `Flowgraph.processApplicationClasses()` calls `currentMethod.retrieveActiveBody()` and Soot throws an exception for a specific method
- **THEN** the exception MUST be caught by the try-catch around `retrieveActiveBody()` (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.warn()` with the skipped method's signature and exception message
- **AND** the loop MUST continue to the next method via `continue`
- **AND** the Flowgraph MUST complete with partial data
- **AND** the `RvsecAnalysisClient.run()` MUST execute and produce a JSON file (with sentinel if no further failure)

#### Scenario: Flowgraph skips statement with failing OpNode creation

- **WHEN** `Flowgraph.processApplicationClasses()` calls `createOpNode(currentStmt)` and the method throws an exception for a specific statement
- **THEN** the exception MUST be caught by the existing catch block (INV-ANA-17)
- **AND** a log MUST be emitted via `Logger.warn()`
- **AND** the loop MUST continue to the next statement via `continue`

#### Scenario: Kotlin stdlib exclusion impact on reachability

- **WHEN** GATOR analyzes an APK with Kotlin dependencies and `-exclude kotlin.`, `-exclude kotlinx.`, and `-exclude androidx.compose.` are active
- **THEN** classes in those packages MUST NOT have their bodies jimplified
- **AND** the call graph MUST still contain edges from application code to excluded package methods (as phantom refs)
- **AND** the `reachability` section MUST NOT include excluded-package classes
- **AND** for targets like `javax.crypto.*` / `java.security.*`, reachability MUST NOT be affected because those APIs are called by application code, not by Kotlin stdlib or Compose runtime

#### Scenario: Analysis output comparison after decomposition (refactor-only)

- **WHEN** the decomposed pipeline analyzes `cryptoapp.apk` with `--mop-dir cryptoapp.mop` and the output is compared against the saved characterization fixture captured immediately before C1c on the same Soot 4.7.1 + same baseline commit
- **THEN** window count MUST match exactly (±0)
- **AND** transition count MUST match exactly (±0)
- **AND** total method count MUST match exactly (±0)
- **AND** `set(reaches_target signatures)` post-decomposition MUST equal the pre-decomposition `set(reaches_mop signatures)` (set-equivalence, transparent to field rename and to JSON byte-order)
- **AND** `set(directly_reaches_target signatures)` post-decomposition MUST equal the pre-decomposition `set(directly_reaches_mop signatures)` (the decomposition is a refactor — no new direct edges introduced)

#### Scenario: Analysis output comparison against gh57 baseline across Soot runs

- **WHEN** the post-rename pipeline analyzes `cryptoapp.apk` and is compared against the gh57 baseline at commit `b2e04a26`, potentially across distinct Soot 4.7.1 invocations
- **THEN** `set(reaches_target signatures)` MUST equal `set(reaches_mop signatures)` from the baseline (strict equality — BFS is deterministic over the same call graph and target set)
- **AND** `set(directly_reaches_target signatures)` MUST equal the baseline `set(directly_reaches_mop signatures)` (the bytecode-scan complement is deterministic)
- **AND** window / transition / widget counts MAY differ by up to ±10% to absorb Soot 4.7.1 non-determinism from Flowgraph skips on borderline-broken methods
- **AND** the GESDA widget parity subset MUST match exactly (this subset is hand-curated and skip-free)

#### Scenario: directlyReachesTarget detects literal library invocations omitted by SPARK (BUG-INV-ANA-19)

- **WHEN** an application method's bytecode contains a literal `invoke-*` whose target's `(declaringClass.getName(), methodRef.name())` matches a resolved target from `ReachabilityIndex.reachesTargetSignatures()`
- **AND** Soot's SPARK call graph does NOT contain that target as a vertex
- **THEN** `findDirectTargetCallersByBytecodeScan` (renamed from `findDirectMopCallersByBytecodeScan`) MUST detect the invocation by walking the method's `Body.getUnits()`, casting each to `Stmt`, and inspecting `InvokeExpr.getMethodRef()` against the precomputed `Set<String>` of `"className#methodName"` keys
- **AND** the detection MUST be independent of the call graph
- **AND** the matched method MUST be unioned into `directTargetSet` after `findDirectTargetCallers` completes
- **AND** the output JSON MUST report `directlyReachesTarget=true` for that method
- **AND** the implementation MUST log scan statistics

#### Scenario: Bytecode-scan resilience on corrupted method bodies

- **WHEN** the bytecode scanner attempts `method.retrieveActiveBody()` and Soot raises a `RuntimeException` or `OutOfMemoryError` on a single application method
- **THEN** the scanner MUST catch the throwable, emit a WARN log, and `continue` to the next method
- **AND** the body-retrieval skip MUST be counted in the `bodies_skipped` log statistic
- **AND** the scanner MUST NOT abort the analysis

#### Scenario: Bytecode-scan scope is limited to application classes

- **WHEN** the bytecode scanner runs as part of the `ReachabilityEngine`
- **THEN** it MUST iterate only the `appClasses` map produced by `extractClasses` (filtered by `code_package`)
- **AND** it MUST NOT iterate every class in `Scene.v().getClasses()`
- **AND** the union with `directTargetSet` MUST never report a library class as a direct target caller

#### Scenario: JsonReportWriter purity — no runtime ReachabilityIndex lookup

- **WHEN** the post-decomposition `JsonReportWriter.write(ReportModel, Path)` is invoked
- **THEN** the writer MUST NOT hold any reference to `ReachabilityIndex` (verified by absence of import and absence of constructor parameter)
- **AND** every flag in the emitted JSON (`reachesTarget`, `directlyReachesTarget`, future `handlerReachesTarget`, etc.) MUST be read directly from the `ReportModel` fields populated upstream by `ReachabilityEnricher` (INV-ANA-30)

#### Scenario: JsonSchema.Keys ↔ _JK parity

- **WHEN** the parity test `tests/parity/json_keys.py` runs in CI
- **THEN** it MUST execute a small Java helper (`JsonSchemaKeysDump`) via subprocess that uses reflection (`Arrays.stream(JsonSchema.Keys.class.getDeclaredFields()).filter(Modifier::isStatic).map(f -> f.get(null))`) and prints the values one-per-line
- **AND** it MUST import `_JK` from Python and collect `set(_JK.__dict__.values())`
- **AND** the two sets MUST be equal (INV-ANA-32)
- **AND** the test MUST fail with a diff listing keys only in Java vs only in Python if they diverge
- **AND** the test MUST NOT rely on text-level regex against the `.java` source (fragile to Javadoc, multi-line concatenation, comments)

#### Scenario: MatchPolicy has no CLI flag

- **WHEN** any caller inspects the `rv-static-analysis` `argparse.ArgumentParser`
- **THEN** there MUST be no argument named `--match-mode`, `--matching`, `--lenient`, `--strict`, or any equivalent that would override policy at the CLI level (INV-ANA-36)
- **AND** the assertion is verified by `tests/cli/test_no_match_mode_flag.py` walking `parser._actions` for forbidden option strings

#### Scenario: G_no_legacy_mop CI gate finds zero legacy references

- **WHEN** the CI gate `tests/parity/no_legacy_mop.py` runs `git grep -nE "reachesMop|directlyReachesMop|mopMethods|handlerReachesMop|handlerDirectlyReachesMop|reaches_mop|directly_reaches_mop|handler_reaches_mop|handler_directly_reaches_mop|target_reaches_mop|cov_reaches_mop|\\bMopMethod\\b|loadMopSignatures|resolveMopInScene|findDirectMopCallersByBytecodeScan"` across `rvsec-gator/`, `modules/` (excluding `modules/rv-agent/` — deprecated per CLAUDE.md), and `scripts/`
- **THEN** the only matches MUST be inside the documented exclusion set: `MopSpecsTargetSource.java`, the CLI flag literal `--mop-dir`, the config attribute name `mop_dir`, published CSVs under `results/` and `experimento-*/`, archived OpenSpec deltas under `openspec/changes/archive/`, and historical commit messages
- **AND** zero matches MUST appear in any other location
- **AND** on any extra match the gate MUST exit non-zero with the file:line of each unexpected hit (INV-ANA-37)

#### Scenario: JsonReportWriter contains no inline string literals for JSON keys

- **WHEN** the audit `tests/parity/no_json_literals.py` parses `JsonReportWriter.java` and counts string literals that match the pattern `"[a-z][a-zA-Z0-9]*"` outside of `JsonSchema.Keys.*` references
- **THEN** the count MUST be zero
- **AND** the test MUST fail with the offending line numbers if any inline literal is found

#### Scenario: JimpleDefUtils replaces duplicated helpers in MenuExtractor and SpinnerItemExtractor

- **WHEN** the post-extraction GATOR jar is inspected
- **THEN** `presto.android.util.JimpleDefUtils` MUST exist with public static methods `definitionRhs(Unit, Local)`, `resolveInt(Value)`, `resolveStr(Value)`
- **AND** `MenuExtractor.java` and `SpinnerItemExtractor.java` MUST contain zero private duplicates of those helpers (grep within those two files yields zero hits for `private.*definitionRhs|private.*resolveInt|private.*resolveStr`)
- **AND** `MenuExtractor` and `SpinnerItemExtractor` MUST invoke the helpers via `JimpleDefUtils.*` qualified calls

### Requirement: Analysis Key Provenance Is Recorded, Never Inferred (FR04, FR05, FR06, NFR06)

Every static analysis run MUST record the package key it filtered on and the origin of that key (`manifest`, `manifest-neutralized` or `detector`), at the time the analysis is performed, in the run's own output — and, with this change, in the analysis artefact itself (INV-ANA-66). GATOR keeps writing the manifest package into the JSON's `package` member irrespective of the `codePackage` client parameter (INV-ANA-58 unchanged); the effective key now occupies a distinct member beside it, so the artefact stops being silent about its own scope.

The requirement still governs the **production** path: a run that performs an analysis chooses a scope, passes it to GATOR as `-clientParam codePackage=`, and records it. A run that merely reads an artefact still chooses nothing — it consumes the file at the scope the producer gave it — but where the artefact carries a record, that record is now read: it classifies discards at the crossing (INV-CORE-60) and feeds the denominator gate (INV-ANA-69), and a stored artefact is reused as a cache hit only under its own key (INV-ANA-70), so a disagreement between a run's key and an artefact's key is **detected**, never resolved silently in either direction. A legacy artefact that records no key supplies `None` — never a value recovered from the `package` member (INV-ANA-58).

#### Scenario: The key and its origin are recorded with the analysis

- **WHEN** a static analysis runs over `org.fossify.calendar_20.apk` with the detector disabled and no neutralization, so that the resolved key is the declared `org.fossify.calendar.debug`
- **THEN** the run's record MUST state the key `org.fossify.calendar.debug` and the origin `manifest`
- **AND** the same key MUST be the one passed to GATOR as `-clientParam codePackage=`
- **AND** the artefact written by the run MUST record that key, its origin and `class_defs_under_key` beside the manifest `package` member (INV-ANA-66)

#### Scenario: A stored artefact never supplies a key, because none is wanted

- **WHEN** an analysis JSON exists at `<results_dir>/<apk>.json`, produced before this change, whose `package` member reads `org.fossify.calendar.debug` and which records no effective key, and a later run parses it
- **THEN** the parser MUST load the artefact at the scope its producer gave it
- **AND** the `package` member MUST NOT be read as a filtering key, and no filtering key MUST be resolved for the parse — the effective key for that task is `None` and its discards are counted as unclassified, while its coverage is computed from the artefact's denominator exactly as before: the missing key costs the row its two `unmatched_*` cells, not its measurement

### Requirement: The Analysis Artefact Defines Its Own Scope (FR04, FR05, FR06, FR12)

The parser MUST treat the analysis artefact as authoritative about which classes belong to the application. It MUST load the `reachability` member whole, and it MUST NOT apply any package-based filter to it. The producer already removed out-of-scope classes when it wrote the file; a second filter over that output cannot add information and can only remove some of it.

The parser MUST also treat the artefact as authoritative about **how those classes are spelled**. It MUST store every class name, window name and method signature exactly as the artefact writes it, and MUST NOT apply `SignatureNormalizer` or any other transformation to an identifier on the consumption path. GATOR emits `SootClass.getName()`, the JVM binary name, in which a dot is always a package boundary and a dollar is always genuine nesting; both runtime producers emit the same form — the dexlib2 weaver converts the DEX type descriptor to a dotted FQN inside `SignatureFormatter.toFqn` before emitting, and the ajc aspect reads `method.getDeclaringClass().getName()`. The two sides of the crossing therefore agree without normalization, and the heuristic that converts a dot to a dollar when both adjacent segments start with an uppercase letter is always wrong at a capitalized package segment. The transformation was also applied inconsistently — to the class name and not to the method signature stored beside it — so when it fired it produced a record whose two halves disagreed.

`ACTIVITY` windows MUST be scoped by membership in `reachability`, because the producer does not scope the `windows` member. Windows of other types MUST continue to be admitted unconditionally. Both sides of that comparison MUST be read in the artefact's own spelling, which is why the two transformation sites are removed together: removing only the class-name site would leave windows dollar-separated and classes dotted, silently changing which activities are admitted.

Neither `StaticAnalysisParser.parse_file` nor `read_static_analysis_files` MUST accept a package argument, and no caller on the consumption path MUST resolve a **filtering** key for the parse. The **classification** key the crossing uses (INV-CORE-60) is a different thing: it is read from the artefact's own record (INV-ANA-66), never resolved from outside, and it filters nothing — reading a recorded key is not resolving one.

#### Scenario: An applicationId that scopes nothing no longer empties the universe

- **WHEN** `io.keepalive.android_133.apk.json` is parsed, whose `package` member reads `io.keepalive.android.debug` while its 203 `reachability` entries are named `io.keepalive.android.*`
- **THEN** the parser MUST report 203 classes and 949 methods
- **AND** `LogcatRepository` MUST be initialized with those 203 classes and 949 methods
- **AND** `cov_method` MUST be computed over 949 as denominator, so a run whose logcat carries `RVSEC-COV` lines MUST NOT report `0.00`

#### Scenario: A framework activity present in windows but absent from reachability is excluded

- **WHEN** an artefact lists `androidx.compose.ui.tooling.PreviewActivity` as an `ACTIVITY` window and does not list it in `reachability`
- **THEN** that window MUST NOT be admitted
- **AND** it MUST NOT be counted in `total_activities`, so `cov_act` MUST NOT be diluted by an activity the application does not own

#### Scenario: A non-ACTIVITY window is admitted regardless of reachability

- **WHEN** an artefact lists a `DIALOG` window whose class is absent from `reachability`
- **THEN** that window MUST be admitted, because a dialog can be a system-provided overlay triggered by application code

#### Scenario: The consumption path carries no key

- **WHEN** `rv-platform` loads static data for a task, or re-parses the artefact while reconstructing a repository from logcat on resume
- **THEN** it MUST call `read_static_analysis_files` with the results directory and APK name only
- **AND** it MUST NOT read `App.code_package`, so the parsed universe MUST be identical whether or not `PackageDetector` is enabled for the run

#### Scenario: A capitalized package segment is stored as written

- **WHEN** the artefact for `com.hwloc.lstopo_80283.apk` contains `className = com.hwloc.lstopo.ZoomView.ZoomView`, where `ZoomView` is both a package and a class
- **THEN** the parser MUST store `com.hwloc.lstopo.ZoomView.ZoomView`
- **AND** it MUST match the 1080 `RVSEC-COV` events that name the same string across the 99 archived logcats
- **AND** the previously produced `com.hwloc.lstopo.ZoomView$ZoomView`, which matched zero events in 99 of 99 logcats, MUST NOT occur

#### Scenario: A genuine inner class keeps its dollar

- **WHEN** the artefact contains `className = com.hwloc.lstopo.ZoomView.ZoomView$ZoomViewListener`
- **THEN** the parser MUST store it unchanged
- **AND** the dollar MUST survive, because the producer already spelled the nesting

#### Scenario: Windows and classes are compared in one spelling

- **WHEN** an `ACTIVITY` window named `br.com.colman.petals.MainActivity` is checked against the `reachability` member
- **THEN** both sides MUST be compared in the artefact's own spelling
- **AND** the admission decision MUST be unchanged from the artefact's point of view

### Requirement: Target Method Source Abstraction (FR04)

The GATOR analysis client MUST load methods of interest via a `TargetMethodSource` interface with at least two production implementations: `MopSpecsTargetSource` (loads from JavaMOP `.mop` specs via `JavamopFacade.listUsedMethods`) and `SignatureFileTargetSource` (loads from a plain-text file of Soot method signatures). The interface decouples target loading from JavaMOP, enabling use of GATOR for use cases outside RV-Android (taint sinks for auditing, custom method lists for papers, third-party toolchains).

The `TargetMethod` POJO (in `presto.android.gui.clients.target`) carries `className: String`, `methodName: String`, `params: List<String>`, `signature: String`, `policy: MatchPolicy` where `MatchPolicy` is the enum `{ LENIENT, STRICT }`, and — added by this capability — `includeSubtypes: boolean` and `nameIsPattern: boolean`. The policy is populated by the source — it is NOT a CLI-level concern (INV-ANA-36).

The three attributes are **orthogonal axes** and MUST NOT be collapsed into one another. `MatchPolicy` is *signature strictness* (`LENIENT` = class+name, `STRICT` = full signature). `includeSubtypes` is *owner matching* (exact FQN vs `FastHierarchy.canStoreType` against the declared super-type). `nameIsPattern` is *method-name matching* (exact vs trailing-`*` prefix). A `generic_new` owner is LENIENT + subtype + pattern; a JCA owner is LENIENT + exact + exact; a signature-file entry may be STRICT + exact + exact. Folding them into a single enum would explode to the cartesian product and break the `LENIENT`/`STRICT` semantics; see ADR 0004.

`TargetMethod.equals`/`hashCode` MUST include `includeSubtypes` and `nameIsPattern`, so two targets differing only by a flag are not collapsed in a `Set<TargetMethod>`. The canonical constructor MUST carry both flags; per P3 there MUST NOT be a delegating overload that defaults them, and every call site MUST be migrated — `MopSpecsTargetSource` passes the real extracted flags, while `SignatureFileTargetSource` and all test call sites pass `false`/`false`, keeping the JCA and signature-file paths on exact matching (INV-ANA-35).

`MopSpecsTargetSource` MUST resolve LENIENT (match by class+name only) to preserve compatibility with AspectJ pointcuts in `.mop` specs whose parameter lists contain wildcards (`init(int, Certificate, ..)`, `getInstance(String, Object+)`).

`SignatureFileTargetSource` MUST resolve STRICT (full Soot signature match) for each non-wildcard entry. Entries whose parameter list is `(..)` or `(*)` resolve LENIENT for that entry only — wildcard syntax is opt-in per entry, not file-wide. STRICT and `includeSubtypes` is an unused combination in this capability: no signature-file entry declares a `+` owner, so the STRICT parameter-matching path in `TargetResolver.resolveInScene` is never reached with subtype matching on.

The `SignatureFileTargetSource` parser MUST tolerate blank lines and lines beginning with `#` (comments), and MUST raise `IllegalArgumentException` (with line number) on any other malformed line.

**Module**: rvsec-gator (`commons/target/TargetMethod.java`, `commons/target/TargetMethodSource.java`, `client/target/MopSpecsTargetSource.java`, `client/target/SignatureFileTargetSource.java`).

#### Scenario: TargetMethodSource interface is the only entry point to target loading

- **WHEN** `RvsecAnalysisClient.run()` needs to load methods of interest
- **THEN** it MUST construct a `TargetMethodSource` (from CLI argument dispatch) and call `source.load()` to obtain `Set<TargetMethod>`
- **AND** it MUST NOT call `JavamopFacade.listUsedMethods` directly (that call lives inside `MopSpecsTargetSource` only)

#### Scenario: SignatureFileTargetSource parses comments, blanks, and signatures

- **WHEN** `SignatureFileTargetSource.load()` is invoked on a file containing:
  ```
  # JCA crypto sinks
  <javax.crypto.Cipher: void init(int,java.security.Key)>

  <javax.crypto.Cipher: byte[] doFinal(byte[])>
  # LENIENT wildcard
  <javax.crypto.Cipher: void init(..)>
  ```
- **THEN** the returned set MUST contain exactly 3 `TargetMethod` instances
- **AND** the first two MUST have `policy == STRICT`
- **AND** the third MUST have `policy == LENIENT`
- **AND** all three MUST have `includeSubtypes == false` and `nameIsPattern == false`

#### Scenario: MopSpecsTargetSource is a thin wrapper over JavamopFacade

- **WHEN** `MopSpecsTargetSource(Path.of("/m")).load()` is invoked
- **THEN** it MUST delegate to `JavamopFacade.listUsedMethods(/m, false)`
- **AND** it MUST convert each `MopMethod` to a `TargetMethod` with `policy == LENIENT`, **propagating `includeSubtypes` and `nameIsPattern` from the `MopMethod`** rather than defaulting them (INV-ANA-41)
- **AND** the resulting `Set<TargetMethod>` MUST be equal in cardinality to the historical `Set<MopMethod>` produced by `loadMopSignatures` on the same input (INV-ANA-35)

### Requirement: JSON Completion Sentinel (NFR02)

The `JsonReportWriter` MUST emit the literal field `"complete": true` as the **final** top-level field of the JSON output, written only after all preceding sections have been flushed successfully. The Python parser MUST surface this field as the `complete: bool` attribute on `StaticAnalysisData`, with default `False` when the key is absent (truncated or corrupted output).

The sentinel is NOT a schema version. It carries no version number, no schema identifier, no producer metadata — it is a single binary invariant: "the producer reached the end of write successfully". P3 (no backward compatibility) is preserved because `complete` is a new field, not a transformation of any existing one.

Downstream gates and consumers MAY filter samples where `complete is False` to avoid false positives caused by truncation. Gates that compare against the baseline (`G_paridade_reachability`, `G_widget_reachability`, `G_transition_reachability`) MUST apply this filter.

**Module**: rvsec-gator (`client/json/JsonReportWriter.java`), rv-static-analysis (`parser/static/static_analysis_parser.py`).

#### Scenario: Successful run emits sentinel as last field

- **WHEN** GATOR completes analysis of `cryptoapp.apk` without timeout or crash
- **THEN** the JSON file MUST end with `,"complete":true}` (allowing for whitespace and field ordering of preceding fields)
- **AND** `JSON.parse(...)["complete"] == true`

#### Scenario: Truncated run does not emit sentinel

- **WHEN** GATOR is killed mid-write by external timeout enforcement after `windows[]` flushed but before `transitions[]` completes
- **THEN** the partial JSON file MUST NOT contain the literal `"complete":true`
- **AND** `StaticAnalysisParser` MUST parse what is recoverable via `_recover_truncated_json`
- **AND** the resulting `StaticAnalysisData.complete` MUST be `False`

#### Scenario: Parser default for absent sentinel key

- **WHEN** `StaticAnalysisParser.parse_json` reads a JSON object that does not contain the `complete` key
- **THEN** the resulting `StaticAnalysisData.complete` MUST be `False`
- **AND** no warning or error MUST be raised

### Requirement: Shared JSON Schema Keys (P1, NFR04)

All field names in the JSON contract between `rvsec-gator` (Java producer) and `rv-static-analysis` (Python consumer) MUST be defined as constants in two parallel locations: `presto.android.gui.clients.json.JsonSchema.Keys` on the Java side (public static final String fields), and `_JK = SimpleNamespace(...)` in `rv_static_analysis.parser.static.static_analysis_parser` on the Python side.

The two constant sets MUST be value-equal (INV-ANA-32). A parity test `tests/parity/json_keys.py` MUST run in CI and fail if they diverge.

This eliminates a category of historical drift bugs (e.g., listener events emitted under key `"eventType"` while transitions emitted `"type"`, both read as `"type"` by the Python parser with a silent default).

**Module**: rvsec-gator (`client/json/JsonSchema.java`), rv-static-analysis (`parser/static/static_analysis_parser.py`).

#### Scenario: JsonSchema.Keys and _JK are value-equal

- **WHEN** the CI parity test runs `python tests/parity/json_keys.py`
- **THEN** it MUST extract the values of all `public static final String` fields declared in `JsonSchema.Keys` (Java, via parsing the source file)
- **AND** it MUST extract `set(_JK.__dict__.values())` (Python)
- **AND** the test MUST assert the two sets are equal (using `xor` to find differences)
- **AND** if they differ, the test MUST print which keys are only-Java and only-Python, then fail

#### Scenario: All JSON writes use the constants

- **WHEN** code review or grep audit examines `JsonReportWriter.java`
- **THEN** it MUST NOT contain string literals matching `"[a-zA-Z]+":` outside of `JsonSchema.Keys` references
- **AND** all `out.append("\"...\"")` for key names MUST use `JsonSchema.Keys.X` references

### Requirement: ReachabilityEnricher Materializes ReportModel (P1, NFR04)

A `ReachabilityEnricher` component MUST sit between `ReachabilityEngine` (producer of `ReachabilityIndex`) and `JsonReportWriter` (consumer of the model). The enricher takes raw collections (`List<Window>`, `WTG`, `ComponentSet`), the index, and metadata (manifest package, code package), and produces an immutable `ReportModel` POJO with every JSON-bound field already computed.

The `JsonReportWriter` MUST receive only the `ReportModel` as input. It MUST NOT hold a reference to `ReachabilityIndex` or invoke any `index.reachesTarget(...)` style lookup during serialization (INV-ANA-30). This decouples enrichment logic from serialization, making each independently testable and preventing god-writer regression as future enrichments (G7/G8/G9/G11 in change C3) are added.

**Module**: rvsec-gator (`client/reach/ReachabilityEnricher.java`, `client/json/ReportModel.java`, `client/json/JsonReportWriter.java`).

#### Scenario: Writer has no ReachabilityIndex dependency

- **WHEN** a static analysis check (CI gate `G_enricher_purity`) inspects `JsonReportWriter.java`
- **THEN** the file MUST NOT contain `import ...ReachabilityIndex;`
- **AND** the constructor of `JsonReportWriter` MUST NOT accept `ReachabilityIndex` as a parameter
- **AND** no method body MUST reference any `ReachabilityIndex` instance

#### Scenario: Enricher produces fully-annotated ReportModel

- **WHEN** `ReachabilityEnricher.enrich(...)` is invoked with raw collections and a populated `ReachabilityIndex`
- **THEN** the returned `ReportModel` MUST contain all per-method reachability flags resolved
- **AND** for every method `m` in `model.reachability`, `m.reachesTarget == index.reachesTarget(soot(m))`
- **AND** the model MUST be deep-immutable (final fields, no setters)

### Requirement: Mutex CLI for Target Source Selection (FR04)

The `rv-static-analysis` CLI MUST expose `--mop-dir PATH` and `--targets-file PATH` as mutually exclusive options. Exactly one of the two MUST be specified on every invocation. The mutex is enforced via `argparse.add_mutually_exclusive_group(required=True)` (INV-ANA-33).

**Module**: rv-static-analysis (`src/rv_static_analysis/__main__.py`, `src/rv_static_analysis/config.py`).

#### Scenario: Both flags passed simultaneously

- **WHEN** the user runs `rv-static-analysis --mop-dir /m --targets-file /t cryptoapp.apk`
- **THEN** argparse MUST emit an error containing `--mop-dir` and `--targets-file` to stderr
- **AND** the process MUST exit with code 2 (argparse default error code) without launching GATOR

#### Scenario: Neither flag passed

- **WHEN** the user runs `rv-static-analysis cryptoapp.apk`
- **THEN** argparse MUST emit an error indicating one of the two flags is required
- **AND** the process MUST exit with code 2

#### Scenario: Only --mop-dir passed

- **WHEN** the user runs `rv-static-analysis --mop-dir /m cryptoapp.apk`
- **THEN** argparse MUST accept the invocation
- **AND** `RVStaticAnalysisConfig.target_source` MUST be `("mop_dir", "/m")` (or equivalent representation)

#### Scenario: Only --targets-file passed

- **WHEN** the user runs `rv-static-analysis --targets-file /t cryptoapp.apk`
- **THEN** argparse MUST accept the invocation
- **AND** the GATOR command MUST include `-clientParam targetsFile=/t`

### Requirement: Shared Jimple Helpers (P1)

GATOR analysis code duplicates a small Jimple-expression resolution layer (`definitionRhs`, `resolveInt`, `resolveStr`) across `MenuExtractor` and `SpinnerItemExtractor`. The duplication is mechanical and load-bearing for menu / spinner static extraction. A single `presto.android.util.JimpleDefUtils` class MUST host the canonical implementation; both extractors MUST call it. New consumers of Jimple definition resolution MUST use the helper class.

**Module**: rvsec-gator (`sootandroid/src/main/java/presto/android/util/JimpleDefUtils.java`, `client/src/main/java/presto/android/gui/clients/menu/MenuExtractor.java`, `client/src/main/java/presto/android/gui/clients/spinner/SpinnerItemExtractor.java`).

#### Scenario: JimpleDefUtils is the single Jimple-def resolution layer

- **WHEN** any GATOR component needs to resolve the RHS of a local assignment, an integer literal, or a string literal in Jimple
- **THEN** it MUST call `JimpleDefUtils.definitionRhs(...)`, `JimpleDefUtils.resolveInt(...)`, or `JimpleDefUtils.resolveStr(...)` (INV-ANA-38)
- **AND** no other class MUST contain a private copy of these helpers

### Requirement: Call Graph Algorithm CLI Exposure (FR04)

The `rv-static-analysis` CLI MUST expose `--cg-algorithm {spark,cha,rta,vta}` (default `spark`) and forward it to GATOR as `-cgAlgorithm <value>`. SPARK remains the operational default (full points-to analysis, validated in gh57 sweep); the alternatives exist because Soot supports them and they are useful for experiments comparing reachability precision. This flag is mechanical CLI plumbing — it does not introduce new analysis behavior beyond what Soot already provides.

**Module**: rv-static-analysis (`src/rv_static_analysis/__main__.py`, `src/rv_static_analysis/config.py`).

#### Scenario: --cg-algorithm forwards to GATOR

- **WHEN** the user runs `rv-static-analysis --mop-dir /m --cg-algorithm cha cryptoapp.apk`
- **THEN** the assembled GATOR command MUST include `-cgAlgorithm cha`
- **AND** `RVStaticAnalysisConfig.cg_algorithm` MUST be `"cha"`

#### Scenario: --cg-algorithm rejects invalid values

- **WHEN** the user runs `rv-static-analysis --cg-algorithm bogus --mop-dir /m cryptoapp.apk`
- **THEN** argparse MUST reject the invocation with a `choices` error listing `spark`, `cha`, `rta`, `vta`
- **AND** the process MUST exit with code 2

#### Scenario: Default --cg-algorithm is spark

- **WHEN** the user omits `--cg-algorithm`
- **THEN** the GATOR command MUST include `-cgAlgorithm spark`

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

### Requirement: Reachability BFS Handles Isolated Entry-Point Seeds (FR04)

The multi-source BFS that produces `reachable[]` MUST add every entry-point seed to its visited set even when the seed has no incident edges in the SPARK call graph. Today the graph is constructed by `buildJGraph` only from CG edges, so entry points with no outgoing/incoming calls are absent from the vertex set, and the existing `if (graph.containsVertex(seed) && visited.add(seed))` guard silently drops them. The downstream effect is a deflated `reachable[]` that misrepresents legitimate callbacks (e.g. a `BroadcastReceiver.onReceive` that the SPARK CG could not link to a call site) as dead code, inflating the apparent gap between `reachable[]` and the application surface.

The fix is structural: the BFS MUST treat seeds as roots unconditionally. Implementations may either (a) call `graph.addVertex(seed)` immediately before the visited-check, or (b) pre-populate the vertex set with the full seed set inside `buildJGraph` before iterating edges. Either is acceptable; the observable contract is that an entry-point that exists in the application's class hierarchy MUST appear in `reachable[]` even when the call graph yields no edge for it.

#### Scenario: Entry-point seed without CG edges remains reachable

- **WHEN** `getEntryPoints(output)` returns a `SootMethod m` whose vertex would not be added by `buildJGraph` (no edge in `Scene.v().getCallGraph()` involves `m`)
- **THEN** `multiSourceBfs` MUST nevertheless include `m` in the returned set
- **AND** the serialized `reachable[]` field MUST contain `m`'s canonical signature
- **AND** the bytecode-scan complement (`findDirectTargetCallersByBytecodeScan`) MUST still observe `m` as a candidate caller of target signatures if its body contains a matching invoke

#### Scenario: Synthetic graph without edges

- **GIVEN** a `DefaultDirectedGraph` containing zero edges
- **AND** a non-empty `seeds` set
- **WHEN** `multiSourceBfs(graph, seeds)` is invoked
- **THEN** the returned set MUST equal `seeds` (no member is silently dropped)

### Requirement: XML Enrichment Recognizes Both `@id/` and `@+id/` Prefixes (FR06)

The widget enrichment pass that reads `res/layout/*.xml` MUST recognize both `@id/foo` (reference) and `@+id/foo` (declaration) forms when matching the `android:id` attribute against the in-memory widget map. The current implementation accepts only `@id/`; since the **declaration** form `@+id/foo` is overwhelmingly more common in Android layouts (any widget being created for the first time uses `@+id`), most XML-declared widgets are silently skipped by enrichment and their `inputType`, `entries`, `prompt`, `spinnerMode`, `contentDescription`, and `tooltipText` fields remain `null` even when present in the source layout.

#### Scenario: Layout uses `@+id/` declaration form

- **GIVEN** a layout file containing `<EditText android:id="@+id/password" android:inputType="textPassword"/>`
- **AND** the widget `password` is present in the in-memory widget map for the activity
- **WHEN** `enrichFromElement` traverses this element
- **THEN** the widget's `inputType` field MUST be set to `"textPassword"`

#### Scenario: Layout uses `@id/` reference form

- **GIVEN** a layout file containing `<Spinner android:id="@id/country_picker" android:entries="@array/countries"/>` (a reference to an id declared in `ids.xml` or elsewhere)
- **WHEN** `enrichFromElement` traverses this element
- **THEN** the widget's `entries[]` field MUST be populated from `@array/countries` (existing behavior preserved)

#### Scenario: Element without id is ignored

- **GIVEN** a `<TextView>` element with no `android:id` attribute (or with an empty string)
- **WHEN** `enrichFromElement` evaluates the element
- **THEN** no enrichment side-effects MUST occur (no map lookups, no NullPointerException)

### Requirement: `MenuExtractor` Resolves `R.string.*` Titles (FR06)

The programmatic-menu extractor MUST resolve `R.string.*` resource ids passed as the title argument of `Menu.add(group, id, order, int)` to the corresponding string value. The constructor accepts a `Function<Integer, String> resIdResolver` and ultimately defers the lookup to its caller. `RvsecAnalysisClient` MUST supply a resolver that maps a numeric resource id to the string value by combining: (1) the SPARK-resident `R.string` inner class to derive the symbolic name from the integer constant, and (2) the existing `Configs.resourceLocation` strings-XML parsing path (the same mechanism `putStringAttr` uses for `@string/` references). Today the caller supplies `resId -> null`, so any menu item created via `Menu.add(group, id, order, R.string.foo)` is serialized with `text=""`, which masks the item from downstream consumers that key off the title (e.g. APE-RV when ranking event affordances).

The resolver MUST tolerate missing mappings (return null/empty when the numeric id is not a `R.string.*` member of the analyzed APK), and the extractor MUST fall back to the existing empty-string default in that case. No exception MUST propagate from the resolver into the extractor's main path.

#### Scenario: `Menu.add` with `R.string.foo` resolves to the string value

- **GIVEN** an `onCreateOptionsMenu` body containing `menu.add(0, R.id.action_settings, 0, R.string.menu_settings)`
- **AND** `res/values/strings.xml` declares `<string name="menu_settings">Settings</string>`
- **WHEN** `MenuExtractor.extractItems(activity)` runs with the production resolver
- **THEN** the resulting widget map MUST contain `"text" -> "Settings"` (not `""`)

#### Scenario: Resolver returns null for an unknown id

- **GIVEN** a `Menu.add` whose title argument is an `IntConstant` not present in the APK's `R.string`
- **WHEN** `MenuExtractor.resolveTitle` invokes the resolver
- **THEN** the resolver MUST return null
- **AND** the widget's `text` field MUST be `""` (the existing empty-string default — no NullPointerException)

#### Scenario: `Menu.add` with a literal CharSequence is unaffected

- **GIVEN** an invocation `menu.add(0, R.id.foo, 0, "Direct Title")` (StringConstant)
- **WHEN** `MenuExtractor.resolveTitle` runs
- **THEN** the widget's `text` MUST equal `"Direct Title"` (the resolver MUST NOT be consulted)

### Requirement: `SpinnerItemExtractor` Unwraps Cast Expressions for `findViewById` (FR06)

When resolving the receiver of a `setAdapter` call to its underlying Spinner widget id, the extractor MUST follow `CastExpr` definitions. The dominant Jimple pattern for the source `Spinner s = (Spinner) findViewById(R.id.foo)` materializes as two statements: `$r1 = findViewById($id)` and `$r2 = (android.widget.Spinner) $r1`. The current `resolveSpinnerWidgetId` reads `definitionRhs(spinnerLocal)` once and only matches `InvokeExpr`, so the cast result `$r2` (whose RHS is a `CastExpr`, not an `InvokeExpr`) breaks the chain and the widget id is never recovered. Without this fix, Spinners declared with the typical cast pattern surface in `widgets[]` but their `entries[]` field stays empty even though `SpinnerItemExtractor` correctly identified the ArrayAdapter literal items.

The fix MUST traverse cast chains bounded by `SimpleLocalDefs`'s fixed-point property: when `definitionRhs(local)` returns a `CastExpr`, the extractor recurses on `(Local) castExpr.getOp()`. Recursion terminates because each step reduces to a new local whose def must be reachable (or unresolvable, in which case the existing single-reaching-def policy returns null). The recursion depth is bounded by the number of casts in the chain (typically 1).

#### Scenario: Spinner declared with cast pattern

- **GIVEN** a method containing `$r1 = findViewById(R.id.spinner); $r2 = (Spinner) $r1; $r2.setAdapter($adapter)`
- **AND** `$adapter` was built from a literal `new ArrayAdapter<>(this, layout, new String[]{"A","B","C"})`
- **WHEN** `SpinnerItemExtractor.extractItems` processes the method body
- **THEN** the returned map MUST contain `R.id.spinner -> ["A","B","C"]`

#### Scenario: Chained casts terminate at the first findViewById

- **GIVEN** statements `$r1 = findViewById($id); $r2 = (View) $r1; $r3 = (Spinner) $r2; $r3.setAdapter(...)`
- **WHEN** the extractor walks the cast chain
- **THEN** the spinner widget id MUST resolve to the value of `$id` from the original `findViewById` call

#### Scenario: Unresolvable receiver does not crash

- **GIVEN** a `setAdapter` call whose receiver's reaching def is ambiguous (multiple defs) or non-local (a field load)
- **WHEN** the extractor attempts to resolve the widget id
- **THEN** `resolveSpinnerWidgetId` MUST return null
- **AND** the extractor MUST count this as an unresolved case (existing `stats.unresolved++`) and continue

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

Three error message formats are supported by the `LogcatParser`, tried in this order and each recognised by structure (INV-ANA-08):

1. **Generic format with source location (Format 1)**: `class.method(file:line) ::: Spec went into an error state.` -- Selected by the suffix `went into an error state.` together with the spaced separator ` ::: ` (the generic emitter spaces it; the FSM emitter of Format 3 does not, and its lines end in the same words), and parsed by the regex `(.*)\.(.*)\((.*):(.*)\) ::: (.*) went into an error state.`. Example: `com.example.IO.read(IO.java:42) ::: InputStream_ManipulateAfterClose went into an error state.` A line carrying the suffix whose regex fails MUST be counted under `format1_regex_failed` and dropped; it MUST NOT fall through into the comma split, because a generic class or method name bearing five commas would otherwise be scrambled into a JCA record whose `spec` is a fragment of that name.

2. **JCA format (Format 2)**: seven comma-separated fields `spec,classQualifiedName,className,methodName,location,errorType,expecting`, exactly as the logcat `ErrorCollector` writes `ErrorSummary.toString()` followed by `,` and the expecting text -- Recognised when `len(message.split(",")) >= 6`; fields 6 onwards are rejoined with `,` into `message`, since commas inside a message are legal. Field 3 (`className`) is redundant with field 2 and is not stored. Example: `CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,MISUSE,Using weak algorithm DES`. When `message` is a **v1 envelope** — `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`, values single-quoted with `'` escaped as `\'` — the parser MUST fill `code`, `event`, `obj`, `val`, `exp`, `msg` on `RvErrorLog` (plain optional string fields; no sub-object) and MUST treat an unclosed final quote as truncation (INV-ANA-63). A `message` that is not an envelope (the legacy `unknown`, a free-text expecting, a pre-change corpus) MUST yield `code=UNSPECIFIED`, `event=UNSPECIFIED`, and empty `obj`/`val`/`exp`/`msg`, counting `sentinel_code` and `sentinel_event`; an envelope whose `code=` or `ev=` value is itself the literal `UNSPECIFIED` — the collector's `null` guard — MUST count under the same counters, since the value is a sentinel whoever wrote it. An empty field 6 MUST yield `error_type=UNSPECIFIED` (counting `sentinel_error_type`); an empty field 5 MUST yield `source=UNSPECIFIED:0` (counting `sentinel_source`); an empty seventh field MUST yield `message=""`, never `No additional message`. A message that carries between one and four commas, no `:::` and no Format-1 suffix MUST be counted under `format2_short` and dropped — the shape logcat leaves when it cuts a payload before its sixth comma.

3. **FSM format (Format 3)**: `class.method():::Spec went into an error state.` -- Recognised by `:::`; class and method are split at the last `.` before `(`. Example: `java.util.Iterator.next():::HasNext went into an error state.` The record's `source` MUST be the sentinel `UNSPECIFIED:0` (counting `sentinel_source`), never `Unknown Source:1`. A `:::` line whose left part has no `.` — the `[helper] ::: ` lines of `generic_new`, a written non-goal of gh104 — MUST be counted under `format3_unresolved` and dropped.

A message matching none of the three MUST be logged, return `None` and be counted under `unrecognised`; a message that matches none of the three **and** immediately follows, from the same `(pid, tid)`, an `RVSEC` record flagged `truncated` MUST instead be counted under `continuation_lines` — it is the second half of a payload logcat split on a `\n` the producer contract forbids. Lines that do not match the threadtime format are counted under `lines_not_threadtime`; threadtime lines under a tag that is neither `RVSEC`, `RVSEC-COV` nor a diagnostic tag are counted under `lines_other_tag`. The counters live in a `ParserDiagnostics` object defined in `rv-android-core` (`rv_android_core/domain/coverage.py`, beside `LogcatRepository`), carried by the returned `LogcatRepository` as `parser_diagnostics` and shared by the live `CoverageTracker`, which passes it as the `diagnostics` parameter of `parse_logcat_line`; no line is dropped without incrementing exactly one of them (INV-ANA-62). `parse_logcat_file` MUST NOT swallow an exception raised while iterating the file: it logs the 1-based line number and re-raises, so a caller never mistakes a partial repository for a complete one.

Each parsed error produces an `RvErrorLog` with `spec`, `error_type`, `class_full_name`, `method`, `source`, `message`, `code`, `event`, `obj`, `val`, `exp`, `msg` and `truncated`. The `LogcatRepository` stores all registered errors and provides deduplication via the `unique_msg` computed field, which `core` composes from the record's fields (INV-CORE-25/41); the parser MUST NOT assemble `unique_msg` itself.

In the ICST study, the top 4 violation classes (SSLContextSpec, MessageDigestSpec, CipherSpec, SecretKeySpecSpec) accounted for 78% of 230 unique violations. 33.91% originated from application code; the rest from external libraries. In the published dataset 72.93 % of the 97,018 records carry the literal `unknown` as their message; those records now surface as `code=UNSPECIFIED` with `sentinel_code` counted, rather than as a message that looks like text.

#### Scenario: JCA envelope parsing with commas inside a value

- **WHEN** a logcat line contains `RVSEC: MessageDigestSpec,okio.ByteString,ByteString,digest$okio,ByteString.kt:12,UnsafeAlgorithm,v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest val='MD2' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found MD2'`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=MessageDigestSpec`, `class_full_name=okio.ByteString`, `method=digest$okio`, `source=ByteString.kt:12`, `error_type=UnsafeAlgorithm`
- **AND** `code=MESSAGEDIGEST-ALG-01`, `event=update`, `obj=MessageDigest`, `val=MD2`, `exp=MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384`, `msg=expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found MD2`, `truncated=False`
- **AND** `message` MUST be the whole envelope from `v=1` to the closing `'`, the commas inside `exp` and `msg` preserved
- **AND** no `sentinel_*` counter MUST be incremented

#### Scenario: Unclosed quote is a truncated record

- **WHEN** a logcat line contains `RVSEC: CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,UnsafeAlgorithm,v=1 code=CIPHER-ALG-02 ev=c1 obj=Cipher val='AES/ECB/PKCS5Padding' exp='AES/GCM/NoPadding,AES/CBC/PKCS7Pad` and no closing `'` follows before end of line
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `truncated=True`, `code=CIPHER-ALG-02`, `event=c1`, `obj=Cipher`, `val=AES/ECB/PKCS5Padding`
- **AND** `exp` and `msg` MUST be `""` — the unclosed value MUST NOT be parsed as a valid value
- **AND** the record MUST be registered and `truncated_envelopes` MUST be incremented by 1

#### Scenario: Legacy `unknown` message receives sentinels, not text

- **WHEN** a logcat line contains `RVSEC: MessageDigestSpec,com.example.Hash,Hash,digest,Hash.java:40,UnsafeAlgorithm,unknown`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `message=unknown`, `code=UNSPECIFIED`, `event=UNSPECIFIED`, `obj=""`, `val=""`, `exp=""`, `msg=""`, `truncated=False`
- **AND** `sentinel_code` and `sentinel_event` MUST each be incremented by 1
- **AND** `error_type=UnsafeAlgorithm` and `source=Hash.java:40` MUST be kept as written, with `sentinel_error_type` and `sentinel_source` unchanged

#### Scenario: Format-1 line with a comma-bearing prefix and a failing regex is counted, not scrambled

- **WHEN** a logcat line contains `RVSEC: com.example.Svc.call(a,b,c,d,e,f) ::: HasNext went into an error state.` — the suffix selects Format 1, the parenthesised group carries no `file:line` colon so the regex fails, and the prefix bears five commas
- **THEN** `parse_logcat_line()` MUST return `(None, None)`
- **AND** `format1_regex_failed` MUST be incremented by 1
- **AND** no `RvErrorLog` with `spec=com.example.Svc.call(a` MUST be produced

#### Scenario: Property test over the characters the envelope grammar constrains

- **WHEN** a property test generates envelopes whose `val`, `exp` and `msg` values contain, in any combination, `,`, an escaped `\'`, and `:::`, and whose total payload is optionally cut at 4068 bytes or split at a `\n` inserted inside a value, and writes each as one or two `RVSEC` threadtime lines
- **THEN** for every uncut, unsplit envelope the parsed `val`/`exp`/`msg` MUST equal the generated values byte-for-byte after unescaping, and every `,` inside a value MUST survive
- **AND** every payload cut at 4068 bytes inside a quoted value MUST yield `truncated=True` and increment `truncated_envelopes` by exactly 1
- **AND** every payload split at a `\n` MUST yield one record with `truncated=True` for the first line and increment `continuation_lines` by 1 for the second line, and MUST NOT yield a second `RvErrorLog`
- **AND** every value containing `:::` MUST be kept verbatim on the record and increment `envelope_forbidden_chars` by 1
- **AND** for the whole generated file, records registered plus counted lines MUST equal lines read (INV-ANA-62)

#### Scenario: Empty fields receive sentinels

- **WHEN** a logcat line contains `RVSEC: SecretKeySpecSpec,com.example.K,K,make,,,`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `error_type=UNSPECIFIED`, `source=UNSPECIFIED:0`, `message=""`, `code=UNSPECIFIED`, `event=UNSPECIFIED`
- **AND** `sentinel_error_type`, `sentinel_source`, `sentinel_code` and `sentinel_event` MUST each be incremented by 1
- **AND** the string `No additional message` MUST NOT appear in any field

#### Scenario: Standard (JCA) error format parsing

- **WHEN** a logcat line contains `RVSEC: CipherSpec,com.example.Crypto,<init>,doEncrypt,Crypto.java:15,MISUSE,Using weak algorithm DES`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=CipherSpec`, `class_full_name=com.example.Crypto`, `method=doEncrypt`, `error_type=MISUSE`
- **AND** the seven-field grammar MUST be unchanged for a line whose seventh field is free text rather than an envelope: `message` MUST keep that text verbatim
- **AND** because the message is not an envelope, `code=UNSPECIFIED` and `event=UNSPECIFIED`, and `sentinel_code` and `sentinel_event` MUST each be incremented by 1

#### Scenario: FSM error format parsing

- **WHEN** a logcat line contains `RVSEC: java.util.Iterator.next():::HasNext went into an error state.`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=HasNext`, `class_full_name=java.util.Iterator`, `method=next`, `source=UNSPECIFIED:0`
- **AND** `sentinel_source` MUST be incremented by 1

#### Scenario: Generic error format parsing

- **WHEN** a logcat line contains `RVSEC: com.example.IO.read(IO.java:42) ::: InputStream_ManipulateAfterClose went into an error state.`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with `spec=InputStream_ManipulateAfterClose`, `class_full_name=com.example.IO`, `method=read`, `source=IO.java`

#### Scenario: `generic_new` helper lines are counted, not parsed

- **WHEN** a logcat line contains `RVSEC: [helper] ::: Iterator_HasNext went into an error state.`
- **THEN** `parse_logcat_line()` MUST return `(None, None)`
- **AND** `format3_unresolved` MUST be incremented by 1

#### Scenario: MOP error detection and registration

- **WHEN** CoverageTracker processes a logcat line that yields an RvErrorLog
- **THEN** the error MUST be registered in LogcatRepository via register_rv_error()
- **AND** a log entry MUST be emitted with spec, error_type, class_full_name, method, message, code, event and time_since_task_start

#### Scenario: Malformed error message handling

- **WHEN** a logcat line contains `RVSEC: some malformed message that does not match any format`
- **THEN** _parse_error_message() MUST log a warning
- **AND** MUST return None (not a malformed RvErrorLog)
- **AND** `unrecognised` MUST be incremented by 1
- **AND** CoverageTracker MUST NOT register any error

#### Scenario: A file-level exception is re-raised with the line number

- **WHEN** `parse_logcat_file(path, static_data)` reads a file whose line 1,203 raises `UnicodeDecodeError` inside the loop
- **THEN** the exception MUST be logged at ERROR naming line 1203 and re-raised to the caller
- **AND** no `LogcatRepository` MUST be returned for that call

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

Each visitor produces `ScreenItem` objects containing `ItemAction` objects. The `ItemAction` carries MOP tracking flags (`reaches_target`, `directly_reaches_target`) derived from the static analysis `WidgetEvent` data when available.

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
- **THEN** the ItemAction's reaches_target and directly_reaches_target flags MUST reflect the corresponding WidgetEvent callback method's reachability flags
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

### Requirement: Error Aggregates Are Independent of Static Analysis Data (FR12)

`CoverageMetricsRepository.calculate_metrics()` MUST compute `total_errors` and `unique_errors` from the repository's `errors`/`unique_errors` collections regardless of whether static-analysis class data is present. The absence of `classes` (no static analysis) MUST zero only the coverage-percentage metrics, never the error aggregates. Concretely, the error count MUST be assigned before any early return guarded by `if not self.classes`, so that a repository reconstructed from a logcat without static data still reports accurate violation totals via `to_dict()`.

This requirement is the testable expression of `analysis` INV-ANA-25 ("Only `total_errors` and `unique_errors` remain accurate" when `static_data` is `None`) and the formal anchor for the platform-side guarantee that `summary.csv` reports correct `mop_errors_total`/`mop_errors_unique` on resume even when coverage is zero (platform INV-PLT-15).

#### Scenario: Metrics Over Empty Classes Still Count Errors

- **WHEN** a `CoverageMetricsRepository` has an empty `classes` dict (no static-analysis data) but holds K violation entries registered via `register_rv_error` (J of them with distinct `unique_msg`)
- **THEN** `calculate_metrics().to_dict()["total_errors"]` MUST equal K
- **AND** `calculate_metrics().to_dict()["unique_errors"]` MUST equal J
- **AND** `calculate_metrics().to_dict()["method_coverage"]` MUST be `0`
- **AND** every other coverage-percentage metric (`class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, `direct_mop_method_coverage`, `activity_coverage`) MUST be `0`

#### Scenario: Error Count Matches get_errors After Logcat-Only Reconstruction

- **WHEN** `parse_logcat_file(path, static_data=None)` reconstructs a repository from a logcat containing `RVSEC` violation entries
- **THEN** `repository.get_errors()` and `repository.calculate_metrics().to_dict()["total_errors"]` MUST report the same count
- **AND** that count MUST equal the number of `RVSEC` violation lines in the logcat

### Requirement: Logcat-Based Repository Reconstruction Requires Static Data for Coverage (FR12)

When a caller invokes `parse_logcat_file(logcat_file, static_data, tool_execution_start)` to reconstruct a `LogcatRepository` outside of real-time execution (e.g., from a persisted `.logcat` on resume or in an offline analysis script), `static_data` MUST be a non-`None` `StaticAnalysisData` instance for per-method coverage to be reconstructed correctly. The parser does not raise when `static_data` is omitted — that signature is preserved for callers that only need MOP violation extraction — but the resulting repository's `classes` dict is empty, and any subsequent call to `register_method_call` (driven internally by `RVSEC-COV` log entries) returns without recording the call. Downstream metrics computed by `LogcatRepository.calculate_metrics()` (which returns a `CoverageMetrics` Pydantic model; callers normally access fields via attributes or `to_dict()`) over an empty `classes` dict yield zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`. `total_errors` and `unique_errors` MUST remain accurate: they are counted from the `errors`/`unique_errors` collections independently of `classes`, so the empty-`classes` early return MUST NOT zero them (see "Error Aggregates Are Independent of Static Analysis Data").

Analogously, `tool_execution_start` MUST be a non-`None` `datetime` for reconstructed timing to be correct. When it is provided, the parser MUST stamp `time_since_task_start = max(0, int((time_occurred − tool_execution_start).total_seconds()))` on every parsed error, coverage entry, and diagnostic event before registering it (INV-ANA-49) — making reconstructed repositories temporally equivalent to those populated live by `CoverageTracker`. When it is omitted, `time_since_task_start` remains `0` on every entry and the parser MUST log one warning about the degraded timing; callers that omit it MUST do so deliberately (no timing available or not needed).

This contract is the formal reason `ResultProcessorComponent._reconstruct_repository_from_logcat` MUST pass `static_data` (see platform `INV-PLT-15`) AND `task.result.tool_execution_start` (see platform `INV-PLT-23`). It also governs offline analysis tooling (e.g., `scripts/regenerate_results/regenerate_container.py`), which loads `StaticAnalysisData` via `StaticAnalysisParser.parse_file` before each `parse_logcat_file` call.

#### Scenario: Coverage Reconstruction with Static Data Populates Repository

- **WHEN** `parse_logcat_file(path, static_data)` is called with `static_data` containing at least one `Class` whose `methods` include the signature emitted in an `RVSEC-COV:` line of the logcat
- **THEN** the returned `LogcatRepository.get_method_calls()` MUST return at least one entry for that signature
- **AND** `LogcatRepository.calculate_metrics().to_dict()["method_coverage"]` MUST be greater than zero
- **AND** `register_method_call` MUST have been invoked exactly once per matching `RVSEC-COV:` line

#### Scenario: Coverage Reconstruction Without Static Data Yields Empty Coverage

- **WHEN** `parse_logcat_file(path, static_data=None)` is called with a logcat containing `RVSEC-COV:` entries and `RVSEC:` violation entries
- **THEN** the returned `LogcatRepository.classes` MUST be an empty dict
- **AND** `LogcatRepository.get_method_calls()` MUST return an empty list
- **AND** `LogcatRepository.calculate_metrics().to_dict()` MUST return zero for `method_coverage`, `class_coverage`, `reachable_method_coverage`, `mop_method_coverage`, and `direct_mop_method_coverage`
- **AND** `LogcatRepository.get_errors()` MUST still return one entry per `RVSEC:` line (errors are unaffected by missing static data)
- **AND** `LogcatRepository.calculate_metrics().to_dict()["total_errors"]` MUST equal `len(get_errors())` (the empty-`classes` early return MUST NOT zero the error aggregate)
- **AND** the parser MUST NOT raise an exception

#### Scenario: Reconstruction With Tool Execution Start Stamps Timing

- **WHEN** `parse_logcat_file(path, static_data, tool_execution_start=datetime(2026, 3, 24, 19, 37, 0))` is called and the logcat contains an `RVSEC:` violation line timestamped `03-24 19:37:05.000` and an `RVSEC-COV:` line timestamped `03-24 19:37:12.000` for a signature present in `static_data`
- **THEN** the reconstructed error's `time_since_task_start` MUST equal `5`
- **AND** the reconstructed method's `MethodCoverageData.time_since_task_start` MUST equal `12`
- **AND** `LogcatRepository.get_method_calls()` MUST return entries whose `time` values reflect those stamps (not `0`)

#### Scenario: Reconstruction Clamps Entries Predating Tool Start

- **WHEN** `parse_logcat_file(path, static_data, tool_execution_start=datetime(2026, 3, 24, 19, 37, 0))` is called and the logcat contains an `RVSEC:` line timestamped `03-24 19:36:58.000` (buffered from before tool start)
- **THEN** that entry's `time_since_task_start` MUST equal `0` (clamped, not negative)

#### Scenario: Reconstruction Without Tool Execution Start Degrades Explicitly

- **WHEN** `parse_logcat_file(path, static_data)` is called without `tool_execution_start` and the logcat contains `RVSEC:` entries
- **THEN** every reconstructed entry's `time_since_task_start` MUST remain `0`
- **AND** the parser MUST log exactly one warning stating that reconstructed timing is unavailable
- **AND** the parser MUST NOT raise an exception

### Requirement: WTG Container-Flow Linking Pass Performance (FR04, NFR04)

GATOR's WTG construction MUST link data flow through container reads and writes in `FlowgraphRebuilder.buildFlowThroughContainer()` (`rvsec-android/rvsec-gator/.../presto/android/gui/wtg/flowgraph/FlowgraphRebuilder.java`) before the WTG stages run. This pass resolves, for each container read/write statement, its container-field position via `WTGUtil.getReadContainerField` / `getWriteContainerField` (`WTGUtil.java`), and adds a flow edge from each writer node to each reader node reachable through the same container.

Because `getReadContainerField` and `getWriteContainerField` are pure functions of the statement, the pass MUST resolve each read statement's field position and target node at most once per allocation node (resolution hoisted out of the inner write loop) and MUST memoize field-position resolution across allocation nodes (`Map<Stmt,Integer>` surviving the outer loop). The target-node computation MUST be guarded so it runs only for allocation nodes that add at least one edge — i.e. only after a write statement resolves to a non-null writer node — because the node-resolution factories (`simpleNode`/`varNode`) lazily create flow-graph nodes; an unguarded hoist would create read-target nodes for allocation nodes the unoptimized pass leaves untouched. These are performance optimizations that MUST preserve the produced edge set exactly (INV-ANA-39); they MUST NOT prune, depth-limit, or otherwise alter the WTG algorithm's result. The per-allocation forward-reachability closure (`GraphUtil.reachableNodes()`) is out of scope for this requirement and remains as-is.

The optimization addresses the dominant pre-WTG cost without changing output, so APKs that previously exceeded the analysis timeout during this pass can complete and emit `transitions[]`. When an APK still times out, the write-first partial-JSON behavior is unchanged: reachability, windows, and components remain populated and `transitions[]` is empty, which downstream consumers (rv-agent, aperv `scoreWtg`) already handle by degrading cleanly (NFR04).

#### Scenario: Optimized pass produces identical transitions on a passing APK
- **WHEN** GATOR analyzes an APK that already produces `transitions>0` under the unoptimized pass (one of the 72 baseline APKs from the `experimento-20260604` sweep)
- **THEN** the `transitions[]` section of the produced JSON MUST be identical (diff-zero on the edge set keyed on stable identifiers: source window name, target window name, event type, widget name, and handler signature — not on the GATOR-assigned numeric node IDs, which need not be stable) to the unoptimized output
- **AND** the `reachability`, `windows`, and `components` sections MUST be unchanged

#### Scenario: Read-field resolution is hoisted out of the write loop
- **WHEN** `buildFlowThroughContainer()` processes an allocation node whose container has `W` write statements and `R` read statements
- **THEN** `getReadContainerField(tgt)` MUST be invoked at most `R` times for that allocation node (once per read statement), NOT `W × R` times (once per write-read pair)
- **AND** the resulting writer-to-reader edges MUST be the same edges the unoptimized `W × R` traversal would add (INV-ANA-39)

#### Scenario: Hoist does not create nodes for an allocation node that adds no edge
- **WHEN** `buildFlowThroughContainer()` processes an allocation node whose container has read statements but whose write statements all fail to resolve to a writer node (`getWriteContainerField` returns null or the writer node is null)
- **THEN** the optimized pass MUST NOT invoke the target-node factories (`simpleNode`/`varNode`) for that allocation node's reads, creating no read-target flow-graph nodes — identical to the unoptimized pass, whose nested loop never reaches the read resolution when no writer node exists
- **AND** the set of flow-graph nodes and the produced edge set MUST be unchanged from the unoptimized pass (INV-ANA-39c)

#### Scenario: Field-position resolution is memoized across allocation nodes
- **WHEN** the same container statement appears as a read or write across multiple allocation nodes in `flowgraph.allNAllocNodes`
- **THEN** its container-field position MUST be resolved by `getReadContainerField`/`getWriteContainerField` once and reused from a `Map<Stmt,Integer>` for subsequent allocation nodes
- **AND** the memoized value MUST equal the value a fresh resolution would return (purity, INV-ANA-39)

#### Scenario: APK that previously timed out completes WTG construction
- **WHEN** GATOR analyzes an APK that exceeded the analysis timeout inside `buildFlowThroughContainer()` under the unoptimized pass (one of the 97 sweep timeouts)
- **THEN** the optimized pass MAY allow the analysis to complete within the same timeout and emit a populated `transitions[]`
- **AND** if it still times out, the partial JSON MUST preserve `reachability`, `windows`, and `components` with `transitions[]` empty, unchanged from the prior timeout behavior (NFR04)

### Requirement: Stateful Diagnostic Event Parsing (FR12, FR13)

The analysis domain SHALL provide a stateful `DiagnosticEventParser` that assembles diagnostic events
from logcat lines while leaving `parse_logcat_line` (RVSEC/RVSEC-COV) unchanged. It SHALL group lines
sharing one `(tag, pid, tid)` into one event.

An open block SHALL be closed when, and only when, one of the following occurs: a diagnostic line
arrives whose `(tag, pid, tid)` key differs from the open block's; a diagnostic line arrives that
starts a new event; a line arrives that does not match the threadtime format (INV-ANA-48); or
`flush()` is called at end of input.

A line under any tag outside the diagnostic set — `RVSEC`, `RVSEC-COV`, `ApeRvHb`, or any other —
SHALL NOT close an open block and SHALL produce no event (INV-ANA-56). Lines between the block's own
lines come from other processes sharing the stream and say nothing about whether the block has ended.

Both `parse_logcat_file` and `CoverageTracker` SHALL feed every line to a `DiagnosticEventParser` and
register emitted events via `LogcatRepository.register_diagnostic_event`. Diagnostic events SHALL
remain isolated in their own repository collection and SHALL enter no coverage, MOP or violation
metric.

#### Scenario: Multi-line AndroidRuntime FATAL assembled into one crash event
- **WHEN** the input contains `E AndroidRuntime: FATAL EXCEPTION: main`, then
  `E AndroidRuntime: Process: br.unb.cic.cryptoapp, PID: 7071`, then
  `E AndroidRuntime: java.lang.NullPointerException: ...getPackageName()...`, then several
  `E AndroidRuntime: \tat ...` frames, all with pid/tid `7071/7071`
- **THEN** exactly one `RvDiagnosticEvent` is emitted with `category="crash"`, `fatal=true`,
  `exception_class="java.lang.NullPointerException"`, `process="br.unb.cic.cryptoapp"`
- **AND** `n_frames` equals the number of `\tat` frames and `stack_head` is the first frame

#### Scenario: A foreign-tag line inside a crash block does not truncate it
- **WHEN** a crash block's `FATAL EXCEPTION`, `Process:` and exception lines are followed by an
  `I RVSEC-COV: <com.x.A: void m()>` line from pid `9000`, and then by the block's own
  `E AndroidRuntime: \tat com.x.A.m(A.java:1)` frame from pid `7071`
- **THEN** the `RVSEC-COV` line SHALL produce no diagnostic event and SHALL leave the block open
- **AND** the frame following it SHALL still belong to that block
- **AND** the emitted event SHALL carry `class_full_name` set, `n_frames` counting the frame that
  followed the interleaved line, and `stack_head` naming it
- **AND** the foreign line's text SHALL NOT appear in the event's `original_msg`

#### Scenario: Event closes on a diagnostic key change and flush at EOF
- **WHEN** a crash block from pid `7071` is followed by a `FATAL EXCEPTION` line from pid `8080`,
  then input ends
- **THEN** the first block SHALL be emitted when the second one starts
- **AND** `flush()` at EOF SHALL emit the second block, so nothing is lost

#### Scenario: A separator line still closes the block
- **WHEN** an open crash block is followed by the non-threadtime line
  `--------- beginning of crash`
- **THEN** the block SHALL be closed and the separator SHALL be skipped without error (INV-ANA-48)
- **AND** the separator SHALL NOT appear in the event's `original_msg`

#### Scenario: A trailing block requires the caller's flush
- **WHEN** a caller feeds a crash block that is still open when the input ends and does not call
  `flush()`
- **THEN** no event is emitted for that block (INV-ANA-57)
- **AND** `parse_logcat_file` SHALL NOT exhibit this, because it flushes internally
- **AND** `CoverageTracker` SHALL NOT exhibit this, because it drains the unread tail and then
  flushes, in that order

#### Scenario: VerifyError at class load
- **WHEN** the input contains `E art: Rejecting class com.foo.Bar ... Verification error`
- **THEN** one `RvDiagnosticEvent` is emitted with `category="verify_error"` naming the rejected class

#### Scenario: ANR event
- **WHEN** the input contains `E ActivityManager: ANR in br.unb.cic.cryptoapp` (or `... has died`)
- **THEN** one `RvDiagnosticEvent` is emitted with `category="anr"` and `process="br.unb.cic.cryptoapp"`

#### Scenario: RVSEC/COV path is unchanged
- **WHEN** the input is a logcat containing only `RVSEC` and `RVSEC-COV` lines (e.g. an existing
  `cmp_*` logcat)
- **THEN** `parse_logcat_line` returns the same `(RvErrorLog, RvCoverageLog)` tuples as baseline
- **AND** no `RvDiagnosticEvent` is produced

#### Scenario: Tag-field match avoids substring false positive
- **WHEN** the input contains `I RVSEC-COV: <com.foo.Utils: boolean isAndroidRuntime()>`
- **THEN** no diagnostic event is produced (the tag field is `RVSEC-COV`, not `AndroidRuntime`)

### Requirement: Frame-Form Normalization of Violation Class and Method (FR11, FR13)

The `LogcatParser` MUST normalize violation records whose `class` or `method` field carries a
whole stack frame instead of a class name and a method name. A value is in **frame form** when
it ends with a parenthesised group of the shape `(<file>:<line>)`. When a value is in frame
form, the parser MUST strip that trailing group and split the remainder at its **last** dot,
binding the part before the dot to `class_full_name` and the part after it to `method`, and
MUST bind the stripped group's contents to `source`.

The guard MUST test the trailing group only and MUST place no constraint on what precedes it.
Method names in the observed corpus contain `$` (Kotlin internal mangling, lambdas, Robolectric
shadows), `-` (Kotlin inline-class mangling), spaces (Kotlin backtick test names) and nested
parenthesis pairs; a guard that constrains the prefix silently fails on roughly half of them.

Normalization MUST be idempotent and MUST leave well-formed values byte-identical, so that
running the parser over output from a corrected monitor produces exactly the same records as
running it over output from an uncorrected one. The parser MUST apply normalization to the JCA
comma-separated format (Format 2), which is the only format whose class and method fields
originate from the Java `ErrorSummary` and can therefore arrive in frame form.

This requirement exists because APKs are instrumented once and replayed across many runs: an
APK already instrumented with an uncorrected monitor jar keeps emitting frame-form values
regardless of any upstream fix, and normalizing at parse time is the only protection for data
produced from those existing artifacts.

#### Scenario: Kotlin `$`-mangled internal method in frame form

- **WHEN** an `RVSEC` line carries the JCA format with `class` and `method` both equal to
  `okio.ByteString.digest$okio(ByteString.kt:83)`
- **THEN** `parse_logcat_line()` MUST return an `RvErrorLog` with
  `class_full_name` = `okio.ByteString`
- **AND** `method` = `digest$okio`
- **AND** `source` = `ByteString.kt:83`
- **AND** neither `class_full_name` nor `method` MUST contain a parenthesis

#### Scenario: Two adjacent source lines collapse to one unique key

- **WHEN** two `RVSEC` lines from the same APK carry
  `okio.ByteString.digest$okio(ByteString.kt:83)` and
  `okio.ByteString.digest$okio(ByteString.kt:84)` under spec `MessageDigestSpec`
- **THEN** both MUST yield `class_full_name` = `okio.ByteString` and `method` = `digest$okio`
- **AND** the two records MUST agree on the `(class_full_name, method, spec)` triple, so that
  the `(apk, class, method, spec)` key counts them as one unique misuse
- **AND** their `source` values MUST differ (`ByteString.kt:83` and `ByteString.kt:84`)

#### Scenario: Kotlin inline-class hyphen mangling

- **WHEN** the frame-form value is `io.ktor.util.DigestImpl.plusAssign-impl(CryptoJvm.kt:51)`
- **THEN** `class_full_name` MUST be `io.ktor.util.DigestImpl` and `method` MUST be
  `plusAssign-impl`

#### Scenario: Robolectric shadow with double `$$`

- **WHEN** the frame-form value is
  `android.os.SystemProperties.$$robo$$android_os_SystemProperties$digestOf(SystemProperties.java:350)`
- **THEN** `class_full_name` MUST be `android.os.SystemProperties`
- **AND** `method` MUST be `$$robo$$android_os_SystemProperties$digestOf`

#### Scenario: Lambda with `$` in both class and method

- **WHEN** the frame-form value is
  `io.matthewnelson.kmp.tor.runtime.FileID$Companion.createFID$lambda$0(FileID.kt:57)`
- **THEN** `class_full_name` MUST be `io.matthewnelson.kmp.tor.runtime.FileID$Companion`
- **AND** `method` MUST be `createFID$lambda$0`

#### Scenario: Backtick test name containing spaces and nested parentheses

- **WHEN** the frame-form value is
  `dev.leonlatsch.photok.CryptoMigrationV2CompatibilityTest.V2-header files (3xx format) are still decryptable after reading a V1-header file(CryptoMigrationV2CompatibilityTest.kt:131)`
- **THEN** `class_full_name` MUST be `dev.leonlatsch.photok.CryptoMigrationV2CompatibilityTest`
- **AND** `method` MUST be
  `V2-header files (3xx format) are still decryptable after reading a V1-header file`
- **AND** `source` MUST be `CryptoMigrationV2CompatibilityTest.kt:131`

#### Scenario: Constructor and static initializer

- **WHEN** the frame-form value is `com.example.Crypto.<init>(Crypto.java:15)`
- **THEN** `class_full_name` MUST be `com.example.Crypto` and `method` MUST be `<init>`
- **AND** the same MUST hold for `<clinit>`

#### Scenario: Well-formed record passes through untouched

- **WHEN** an `RVSEC` line carries `class` = `okhttp3.internal.platform.Platform` and
  `method` = `newSSLContext`, neither in frame form
- **THEN** `class_full_name` MUST be `okhttp3.internal.platform.Platform` byte-identical
- **AND** `method` MUST be `newSSLContext` byte-identical
- **AND** no normalization log entry MUST be emitted

#### Scenario: Normalization is idempotent

- **WHEN** the normalization is applied twice to
  `okio.ByteString.digest$okio(ByteString.kt:83)`
- **THEN** the second application MUST return exactly what the first returned

### Requirement: Coverage Tracker Final Drain (FR12, NFR06)

`CoverageTracker.stop()` MUST guarantee that the tracking thread consumes the remainder of the logcat file before terminating. Terminating on the stop signal alone leaves any lines written since the thread's last read permanently absent from the repository, and the repository is the only input `CoverageComponent.process_results()` has.

The drain MUST read forward from the handle's current position to end-of-file and process those lines through the same path the tail loop uses, so parsing, timing arithmetic, and diagnostic-event handling are identical. It MUST run before the existing `flush_diagnostics()` call, so that any diagnostic event completed by the drained lines is emitted rather than discarded.

The drain MUST be resilient. A read error MUST be caught and logged as a warning; `stop()` MUST NOT raise, because the platform now invokes it from a `finally` where a raised exception would replace the exception being propagated.

This requirement is only fully effective when the logcat producer has already been stopped, which the platform guarantees by finalizing logcat before coverage (platform INV-PLT-31). Without that ordering the drain still reads whatever is present at the moment it runs, but the file may continue to grow afterwards.

#### Scenario: Lines written after the last tail iteration are recovered

- **WHEN** the tail loop completes an iteration, three `RVSEC-COV` lines are appended to the file, and `stop()` is then called
- **THEN** all three lines MUST be present in the repository after `stop()` returns
- **AND** `repository.calculate_metrics()` MUST count the methods they name

#### Scenario: Live metrics match re-parsing the same file

- **WHEN** the `adb logcat` producer is stopped, then `stop()` is called on the tracker, for a task that ends `COMPLETED`
- **THEN** `repository.calculate_metrics().to_dict()` MUST equal the metrics obtained by parsing the same logcat file from the beginning with `parse_logcat_file`, for every coverage and error field, within a tolerance of `0.01`
- **AND** this MUST hold for the round trip required by platform INV-PLT-18

#### Scenario: Drain does not double-count

- **WHEN** a violation line was already processed by the tail loop before `stop()` was called
- **THEN** the drain MUST NOT register it again
- **AND** `total_errors` MUST be identical to its value immediately before `stop()` was called, plus only the errors found in genuinely unread lines

#### Scenario: Drain completes before diagnostics are flushed

- **WHEN** the unread tail contains the final line of a diagnostic event whose earlier lines were already buffered
- **THEN** the drain MUST process that line before `flush_diagnostics()` runs
- **AND** the completed diagnostic event MUST be emitted

#### Scenario: Read failure during drain does not propagate

- **WHEN** reading the remainder of the file raises `OSError`
- **THEN** `stop()` MUST NOT raise
- **AND** the condition MUST be logged as a warning naming the logcat file
- **AND** the thread MUST still terminate and the handle MUST still be closed

#### Scenario: Stopping an already-stopped tracker remains inert

- **WHEN** `stop()` is called on a tracker whose `is_running` is already `False`
- **THEN** it MUST return immediately without attempting a drain
- **AND** the repository MUST be unchanged

---

### Requirement: Derived MOP Artifact as a Device-Only Consumer (FR04, FR05, FR06)

The static-analysis chain SHALL gain exactly one new downstream consumer: the host-side derivation in
`aperv-tool` that projects the full JSON into `<results_dir>/<apk_name>.mop.json`. The derivation
SHALL read the full JSON and SHALL NOT modify it. The artifact SHALL be device input only — pushed by
`aperv-tool`, parsed by the jar, and read by nothing else.

The `"complete": true` sentinel SHALL NOT be a precondition of derivation. A document written by the
producer's first pass — valid JSON with populated `reachability` and `windows` per `INV-ANA-20`, and an
empty `transitions` array — SHALL yield an artifact whose `wtg` is empty and whose
`stats["wtgEdges"]` is `0`, which is how WTG absence reaches the device (`INV-DRV-08` in the `aperv`
capability). The sentinel keeps its producer-side meaning unchanged (`INV-ANA-31`) and remains
available to the consumers that do require completeness; the derivation is no longer one of them. A
genuinely interrupted write is still refused, one step earlier: the producer truncates its output file
on open, so a killed second pass leaves unparseable bytes that fail in `json.loads` before `derive()`
runs.

#### Scenario: derivation leaves the producer output untouched
- **WHEN** `aperv-tool` derives an artifact for `com.example_1.apk`
- **THEN** `<results_dir>/com.example_1.apk.json` SHALL be byte-identical to its content before the
  derivation
- **AND** `<results_dir>/com.example_1.apk.mop.json` SHALL exist alongside it

#### Scenario: WTG-less analysis still yields an artifact
- **WHEN** the full JSON lacks the `"complete": true` sentinel because `WTGBuilder` did not finish, and
  it carries populated `reachability` and `windows` with `transitions: []`
- **THEN** a `*.mop.json` SHALL be produced for that app
- **AND** it SHALL carry `wtg == {}` and `stats["wtgEdges"] == 0`
- **AND** the MOP arm for that app SHALL run, with the jar disabling its WTG-dependent scoring passes
  through `MopData.hasWtgData()`

#### Scenario: unparseable analysis output still yields no artifact
- **WHEN** the full JSON is syntactically invalid because the producer was killed during its second
  write pass, which truncated the file on open
- **THEN** no `*.mop.json` SHALL be produced for that app
- **AND** the failure SHALL be raised by `json.loads` in `_derive_mop_artifact()` as
  `RVToolExecutionError`, before `derive()` is reached

#### Scenario: producer is unaware of the derivation
- **WHEN** static analysis runs for an app
- **THEN** its output SHALL be identical whether or not an artifact is later derived from it
- **AND** no producer code path SHALL read, write or test for a `*.mop.json` (INV-ANA-54)

---

### Requirement: Full JSON Remains the Sole Metric Input (R9, NFR02)

Every metric computation, gate and offline consolidation path SHALL read the full static-analysis JSON
and logcat exclusively. The frozen definitions — *MOP coverage* over `directly_reaches_mop`, *unique
misuse* keyed `(app, class, method, specification)`, and the app-versus-library split by the `Mneut`
prefix test — SHALL be unaffected by this change, because their input is unchanged.

No metric or analysis code SHALL read a `*.mop.json` artifact (INV-ANA-53). The artifact is a lossy
projection: it carries no `reachability` section, no method signatures, `reachesTarget` renamed to
`reachesMop`, `targetMethods` compacted to a boolean, and dialog widgets merged into host activities.
A metric computed over it would answer a different question under the same name. This SHALL be
enforced by an audit over the repository — a test asserting that no module outside `aperv-tool`
references the `.mop.json` suffix — rather than by convention. The audit test is itself the only
permitted match outside `aperv-tool`.

#### Scenario: metrics unchanged by the presence of an artifact
- **WHEN** the derivation runs for an app and the analysis pipeline then computes its
  `directly_reaches_mop` set
- **THEN** the set SHALL be computed from the full JSON
- **AND** it SHALL be identical to the value computed before this change

#### Scenario: audit catches an analysis path reading the artifact
- **WHEN** any module other than `aperv-tool` references a `.mop.json` path
- **THEN** the audit test SHALL fail naming the file and the reference
- **AND** the audit SHALL treat its own assertion text as the single permitted occurrence

#### Scenario: resume and offline consolidation re-parse the full JSON
- **WHEN** an experiment is resumed and `ResultProcessorComponent` re-resolves static data for an app
- **THEN** it SHALL re-parse `<results_dir>/<apk_name>.json`
- **AND** the presence, absence or staleness of a `*.mop.json` SHALL have no effect on the result

### Requirement: Subtype/Wildcard-Aware Target Matching for Hierarchy-Declared Spec Sets (FR04, FR05, FR06)

The GATOR target-matching pipeline MUST match a call site to a `.mop` pointcut when the pointcut
declares its owner by **type hierarchy** (the `+` subtype operator) and/or via **wildcard imports**
and **wildcard method names**, and MUST resolve the constructor form `Owner.new(..)` to `<init>` — in
addition to the existing exact-FQN matching for explicitly-declared owners. The requirement is stated
over these constructions and holds for **every** spec set that uses them, present or future; the
`generic_new` corpus is the fixture that exercises all four, not the subject of the requirement. The pipeline spans the extractor, `MopSpecsTargetSource`, `TargetResolver`, and the
bytecode-scan complement.

A method `a()` MUST transition from `reachesTarget=false` to `reachesTarget=true` when it reaches
(directly or transitively) a call site whose declaring type is-a-subtype-of the super-type declared
in a spec pointcut and whose method name matches the (possibly wildcard) declared name. The match MUST
be decided by `FastHierarchy.canStoreType(callSiteDeclaringType, declaredSuperType)` at match time
(decision A2). The output JSON schema MUST NOT change (INV-ANA-44); per-spec attribution remains a
runtime concern (the `.mop` handlers log `RVSEC ... ::: <SpecName>`, parsed by `rv-coverage`).

The JCA spec style (explicit imports, exact `Class.method` pointcuts, no `+`, no wildcard method
names) MUST continue to use the exact-`equals` path with no behavioral change (INV-ANA-35 parity).

#### Scenario: Extractor loads targets from a wildcard/subtype generic spec
- **WHEN** the extractor parses `generic_new/Collection_UnsynchronizedAddAll.mop` containing `import java.util.*;` and `call(boolean Collection+.addAll(..))`
- **THEN** it MUST emit a `MopMethod` with `className="java.util.Collection"`, `methodName="addAll"`, and `includeSubtypes=true`
- **AND** over all 27 `generic_new` specs the emitted target set MUST have the cardinality fixed in advance by INV-ANA-40 — **69** distinct `call()` pairs when the trailing `+` is part of the owner key, **68** when it is not (currently 0), the constructor pointcuts included per boundary (b); asserting merely `> 0` is the pinned-to-whatever-is-emitted weakness that INV-ANA-40 forbids
- **AND** the same extractor run on the 23 `jca` specs MUST emit **exactly 122** targets (**70** `(class, method)` pairs, **23** owners), each with `includeSubtypes=false` and `nameIsPattern=false`. **This literal was 120/68/22 until scope boundary (c) became a requirement to repair**: the seed of that boundary resolves the two `RandomStringPassword` pointcuts, which had never loaded. The freeze forbids an *unenumerated* move of the frozen set, not every move — the two added rows are named in boundary (c) and are the whole difference, and pinning the new literal here is what stops a third move arriving unenumerated
- **AND** the `jca_android` count MUST be **derived by enumerating that directory**, never asserted as a literal: gh109 is adding specs to it (23 → 48 specs, 130 → 238 `call()` pointcuts between 2026-08-21 and 2026-08-28), so only the set-independent properties are pinned — every flag false, and (after the seed of this invariant) **no unresolved owner at all**
- **AND** the `String` owner of `RandomStringPassword.mop` MUST resolve — through the implicit `java.lang` seed, at the third and last resolution step — and both targets it yields MUST carry `MatchPolicy.STRICT` (scope boundary (c)). **This clause inverted on 2026-08-28**: it previously required `String` to stay unresolved and merely logged, which was the accepted-debt reading of boundary (c). The debt is repaired inside this change instead, so the extractor MUST report **zero** unresolved owners for `jca` and `jca_android`, and the skipped-owner log for those two sets MUST be empty rather than naming `String`

#### Scenario: Wildcard method names are preserved as patterns (including the bare `*`)
- **WHEN** a pointcut declares `call(* Collection+.add*(..))`
- **THEN** the emitted `MopMethod` MUST carry `nameIsPattern=true` with stored name pattern `add*`
- **AND** the matcher MUST match call-site method names `add` and `addAll` but MUST NOT match `remove`
- **AND** every trailing-`*` pattern present in `generic_new` — `add*`, `remove*`, `retain*`, `clear*`, `put*`, `offer*`, `write*` — MUST be preserved and matched by prefix
- **AND** the bare pattern `*` (`call(* Iterator.*(..))`, exact owner `Iterator`) MUST match every method name of the owner (prefix `""`): this match-all is the intended AspectJ semantics, not a degenerate case, and MUST NOT be rejected/forced to `false`

#### Scenario: Flags propagate from MopMethod to TargetMethod (INV-ANA-41)
- **WHEN** `MopSpecsTargetSource.load()` maps the extracted `MopMethod` set to `TargetMethod` entries
- **THEN** each `TargetMethod` derived from a `generic_new` `+`/wildcard pointcut MUST carry `includeSubtypes=true` (and `nameIsPattern=true` for wildcard names) — the flags MUST NOT be dropped at this boundary
- **AND** each `TargetMethod` derived from a `jca` spec MUST carry `includeSubtypes=false` and `nameIsPattern=false`
- **AND** `TargetMethod.equals`/`hashCode` MUST include both flags so two targets differing only by a flag are not collapsed in the `Set<TargetMethod>`; `MopSpecsTargetSource` is the ONE constructor call site that passes the **real extracted flags** (per the two clauses above), while every other call site (`SignatureFileTargetSource`, tests) MUST pass both flags as `false` so the JCA/signature-file paths stay on exact matching (INV-ANA-35)

#### Scenario: Subtype match on a concrete library type
- **WHEN** an APK method calls `java.util.ArrayList.addAll(Collection)` and the active target is `Collection+.addAll` with `includeSubtypes=true`
- **THEN** `FastHierarchy.canStoreType(ArrayList, java.util.Collection)` MUST return `true`
- **AND** the calling method MUST be marked `directlyReachesTarget=true` and `reachesTarget=true`

#### Scenario: Interface-typed call site (A2 covers what A1 misses)
- **WHEN** an APK call site is `java.util.List.iterator()` (declaring type is the interface `List`) and the active target is `Iterable+.iterator` with `includeSubtypes=true`
- **THEN** `FastHierarchy.canStoreType(java.util.List, java.lang.Iterable)` MUST return `true` and the call site MUST match
- **AND** this case MUST match even though `getActiveHierarchy().getImplementersOf(Iterable)` does not contain `List` (the rejected A1 pre-expansion would miss it)

#### Scenario: Predicate applied at both match points
- **WHEN** the target set contains a `includeSubtypes=true` entry
- **THEN** `TargetResolver.resolveInScene` MUST seed the reverse-BFS by matching scene methods via `canStoreType` against the declared super-type
- **AND** `RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` MUST match invokes **for those `includeSubtypes=true` entries** via `canStoreType` against the declared super-type, NOT against pre-resolved exact keys
- **AND** the scan MUST remain **hybrid**: the `!includeSubtypes` entries in the same target set MUST keep the existing `Set<String>` `class#method` key path, so JCA lookup stays O(1) and byte-for-byte parity (INV-ANA-35) is unaffected. The prohibition on pre-resolved keys applies to the subtype entries only

#### Scenario: Target super-type force-resolved into the Scene with graceful degradation
- **WHEN** the declared target owner `java.io.Closeable` is not yet loaded as a `SootClass` in the Scene
- **THEN** the matcher MUST force-resolve `java.io.Closeable` at HIERARCHY level, and MUST obtain the `FastHierarchy` only afterwards (never reusing an instance held from before the resolution)
- **AND** because Soot runs with `allow_phantom_refs=true`, the matcher MUST treat a resolved-but-**phantom** owner (or one whose `resolvingLevel() < HIERARCHY`) as unresolved — `containsClass` alone is insufficient, since `canStoreType` would return a definite (wrong) `false` rather than throwing
- **AND** IF a declared owner remains absent or phantom at match time THEN that owner MUST degrade to exact `equals` matching and the degradation MUST be logged as a warning (no silent false-negative)

#### Scenario: Output schema unchanged across spec sets
- **WHEN** GATOR writes the static-analysis JSON for an APK against `generic_new`
- **THEN** the set of JSON keys MUST be identical to a `jca` run on the same APK (only `reachesTarget`/`directlyReachesTarget` boolean values differ)
- **AND** the three raw-JSON readers — `static_analysis_parser.py`, the `scripts/` gates, and `aperv-tool` (`static_artifact.py` + `derive_mop_artifact.py`) — MUST require no key-mapping change; `derive_mop_artifact.py:422` is the one that would degrade a rename to a silent `False` rather than erroring, so it is the sharpest indicator
- **AND** the ape `MopData.java` MUST NOT be cited as evidence of schema safety: it consumes the *derived* `*.mop.json` (key already renamed to `reachesMop`), not this artefact

#### Scenario: Non-target call site stays unmatched — no subtype over-match (negative E2E)
Because `generic_new` declares `Object+` owners (`Object_MonitorOwner.mop`: `wait`/`notify`/`notifyAll`),
**every** call-site declaring type is a subtype of some declared owner. A non-match is therefore decided
on the **method-name axis**, never on the type axis — an earlier framing that called `String.length()`
"not a subtype" was wrong, since `String <: Object`.

- **WHEN** a method invokes a call site whose declaring type is a subtype of a declared owner but whose method name does NOT match that owner's declared pattern/name — e.g. `java.lang.String.length()` (`String <: Object+` but `length` ∉ {`wait`,`notify`,`notifyAll`}), or `java.util.ArrayList.remove(...)` against `Collection+.add*`
- **THEN** the method MUST be reported `reachesTarget=false` and `directlyReachesTarget=false`
- **AND** `nameMatches` MUST reject the name **before** `canStoreType` is consulted, so a non-matching name short-circuits regardless of subtype
- **AND** every `directlyReachesTarget=true` call site in a **sampled** subset of the IT APK MUST be a genuine subtype+name match. The criterion is deliberately bounded: exhaustive ground-truth labelling of an APK is impractical, so acceptance is a documented sample (every call site of at least two declared owners, plus ten randomly drawn positives) with zero misclassifications in that sample. This is a sampling gate, not a completeness proof, and MUST NOT be restated as "zero spurious positives" — a universal claim that no feasible check can discharge

#### Scenario: JCA exact path preserved (parity)
- **WHEN** the matcher resolves a JCA target such as `Cipher.getInstance(String)` (`includeSubtypes=false`)
- **THEN** matching MUST use exact `equals(className) && equals(methodName)` with no hierarchy query
- **AND** `MopSpecsParityTest` MUST keep passing (INV-ANA-35, source-layer parity)
- **AND** because that test compares `MopSpecsTargetSource.load()` against `JavamopFacade.listUsedMethods()` on the same directory — both sides running through the modified visitor — it CANNOT detect an extractor-side JCA regression; the load-bearing JCA gate is therefore the **literal count** asserted in the extractor test (122 targets / 70 pairs / 23 owners, all flags `false` — 120/68/22 until the seed of scope boundary (c) made the two `RandomStringPassword` rows load), plus the `BaselineComparisonIT` on `cryptoapp.apk`

#### Scenario: Constructor pointcut resolves to `<init>` (INV-ANA-40 boundary (b))

- **WHEN** the extractor visits `call(ServerSocket.new(int, int))` in `ServerSocket_Backlog.mop`, or
  `call(TreeMap.new(Map))` in `TreeMap_Comparable.mop`
- **THEN** it MUST emit `MopMethod("java.net.ServerSocket", "<init>")` / `MopMethod("java.util.TreeMap", "<init>")`
  with `includeSubtypes=false` — the pointcuts carry no `+`
- **AND** `TargetResolver.resolveInScene` MUST resolve them, because `SootMethod.getName()` of a
  constructor is `<init>` and the comparison at `TargetResolver.java:53` is name equality
- **AND** the `generic_new` cardinality gate MUST read 69 pairs / 21 owners, not 67 / 20
- **AND** this repair alone MUST leave `jca` at 120 signatures / 68 pairs / 22 owners — the 18 constructor
  rows already existed and only their emitted name changes from `new` to `<init>`. (The set's final
  literal is **122/70/23**; the further two rows come from scope boundary (c)'s seed, which is a
  different cause measured separately. This clause pins *this* repair's effect, not the end state.)
- **AND** the frozen `cryptoapp` fixture MUST move by exactly the two enumerated methods
  (`CryptoUtils.createSecretKeyFromBytes`, `CryptographyActivity.executeSecretKeyOperation`), re-baselined
  with that enumeration written into the commit message

#### Scenario: Seeded `java.lang` owner yields STRICT targets (INV-ANA-40 boundary (c))

- **WHEN** the extractor visits `call(public static String String.valueOf(Object))` and
  `call(public char[] String.toCharArray())` in `jca/RandomStringPassword.mop`, whose imports declare
  `java.util.stream.IntStream` and three `br.unb.cic.mop.*` packages and no `java.lang`
- **THEN** the owner MUST resolve to `java.lang.String` through the implicit-`java.lang` seed — the third
  and last resolution step, reached only because neither the explicit-import map nor `Class.forName` over
  the declared wildcard packages resolved it
- **AND** both emitted targets MUST carry `MatchPolicy.STRICT`, because their owner resolved only through
  the seed; targets whose owner resolved at an earlier step MUST keep the policy they already had
- **AND** their parameter types MUST be FQN (`java.lang.Object` for `valueOf`, none for `toCharArray`), so
  the STRICT signature comparison is expressible at all
- **AND** a call site of `String.valueOf(int)` or `String.valueOf(long)` MUST NOT match, which is the whole
  point of the STRICT clause: under LENIENT the two targets match every overload, measured at 74 call sites
  over 3 corpus APKs of which only 17 are the woven signatures
- **AND** `generic_new` MUST be unaffected — its seven `java.lang`-owner specs declare `import java.lang.*;`
  and so resolve before the seed is consulted, keeping the LENIENT policy their `(..)` parameters require
- **AND** the extractor MUST report zero unresolved owners for `jca` and `jca_android`, the skipped-owner
  log for those sets being empty rather than naming `String`
- **AND** the movement of the frozen `jca` count MUST be enumerated by signature and attributed to its
  cause, the FQN parameter resolution having been measured in isolation first (design D11)

#### Scenario: Bytecode-scan-only direct caller is also transitive (INV-ANA-64)

- **WHEN** a method `m` of the app calls a target method `t` through an invoke that SPARK quarantines,
  so the call graph carries no `m → t` edge and the bytecode scan is the only oracle that sees it
- **THEN** `m` MUST appear in `directlyReachesTarget` (as today, via the scan)
- **AND** `m` MUST also appear in `reachesTarget`, because the reverse BFS is seeded with
  `targets ∪ directTargetSet` and `m` is therefore a seed
- **AND** any caller of `m` that the call graph does contain MUST also appear in `reachesTarget`,
  which post-hoc union of the two sets would not deliver
- **AND** when `m` carries no call-graph vertex at all (measured: 12 of the 14 current violations),
  `m` itself is still marked and only its unreachable ancestors stay unmarked — a false negative on the
  transitive axis, not a containment violation, and the run MUST NOT fail

### Requirement: The Demotion Guard Resolves Scope From the Code Key

`AnalysisEntrypoint` SHALL guard the application-to-library demotion with the same scope key the analysis client uses to filter its results. It MUST read `Configs.getClientParamCode("codePackage=")` and MUST fall back to the manifest `package` attribute only when that client parameter is absent. `Configs.clientParams` is populated by `Main.main` before `setupAndInvokeSoot()` runs, so no new dependency between `sootandroid` and `client` is introduced.

The rescue branch that admits classes named in an `<activity>` element MUST remain unchanged. With the guard repaired it stops being load-bearing for application classes and becomes what it was written to be — a safety net for components Soot misclassified — so widening it to services, receivers and providers MUST NOT be part of this change.

#### Scenario: An APK whose manifest package carries a build-type suffix
- **WHEN** `br.com.colman.petals_3040000.apk` is analysed with manifest `package = br.com.colman.petals.debug` and `-clientParam codePackage=br.com.colman.petals`
- **THEN** the guard MUST protect the 771 classes under `br.com.colman.petals`
- **AND** the `libPackages.txt` pattern `br.com.*` MUST NOT demote them
- **AND** the artefact MUST report 762 application classes instead of 1 — the 771 the guard protects, minus the nine generated classes (`.R`, `.R$*`) that `RvsecAnalysisClient.isAppClass` strips before writing

#### Scenario: An APK whose code package matches no library pattern
- **WHEN** `app.pachli_50.apk` is analysed with manifest `package = app.pachli.current` and `codePackage = app.pachli`
- **THEN** the application class count MUST be 6467 both before and after the repair
- **AND** the repair MUST be invariant for every application whose package matches no `libPackages.txt` pattern

#### Scenario: The client parameter is absent
- **WHEN** GATOR is invoked without `-clientParam codePackage=`
- **THEN** the guard MUST use the manifest `package` attribute
- **AND** the demotion MUST proceed exactly as it does under a manifest-key guard: no class protected or demoted differently than when the parameter is never supplied

### Requirement: The Artefact Records the Key That Produced It

A run that performs an analysis SHALL record the effective scope key and its origin in the artefact it writes. The `package` member MUST keep holding the manifest package as GATOR read it, because INV-ANA-58 forbids treating it as the filtering key; the effective key MUST occupy a distinct member so that the two are never conflated.

Measured over the 162 artefacts of the article corpus, zero classes start with the recorded `package` and 162 of 162 start with the neutralized key — the artefact today records a value that describes nothing about its own contents.

The run SHALL also record `class_defs_under_key`: the number of compiled classes whose name starts with the effective key, counted from the `class_defs` tables of the APK's DEX files at the moment the artefact is written. The reason is the wiring site of the denominator gate. The gate needs two numbers — what was parsed and what was compiled — and only the producer holds both: the parser's entry points are `parse_file(file_path)` (`static_analysis_parser.py:205`) and `read_static_analysis_files(results_dir, apk)` (`:267-286`, where `apk` is a filename **string**), so neither sees an APK, and INV-ANA-61 forbids passing a package key into that module at all (its docstring states *"No package key reaches this module"*). Recording the count at write time resolves that contradiction instead of arguing with it: the gate becomes a **pure predicate over the artefact**, evaluable wherever the artefact is read — including resume and `--process-results`, which re-parse `.apk.json` long after the APK is out of reach.

#### Scenario: A run with a neutralized key
- **WHEN** an analysis runs with manifest package `org.fossify.paint.debug` and effective key `org.fossify.paint`
- **THEN** the artefact `package` member MUST be `org.fossify.paint.debug`
- **AND** the artefact MUST record `org.fossify.paint` as the effective key
- **AND** it MUST record the origin of that key

#### Scenario: The artefact carries its own compiled-class count
- **WHEN** `br.com.colman.petals_3040000.apk` is analysed with effective key `br.com.colman.petals`, and 771 compiled classes carry a name starting with that key, nine of them generated resource classes
- **THEN** the artefact MUST record `class_defs_under_key = 762` beside the effective key — the count after `isAppClass`, the same predicate that filtered the parsed side
- **AND** it MUST NOT record the raw 771, which no consumer could correct: the gate receives a count, never the names it would need to filter
- **AND** a later `--process-results` run over the same results directory MUST be able to evaluate the denominator gate from the artefact alone, with no APK on hand and no package key passed to the parser

### Requirement: Generated Resource Classes Leave the Denominator at Every Segment

The analysis client SHALL exclude generated resource classes from the classes it writes, testing the **last segment** of each class name rather than the suffix that follows the scope key.

The filter exists and is correct in intent; it leaks by construction. `isAppClass` computes `className.substring(filterPackage.length())` and compares that suffix to `.R`, `.R$*` and `.BuildConfig`, which answers only for a resource class sitting directly under the key. Two shapes escape it, and both are ordinary: a multi-module application, whose modules each generate their own `R` (`app.pachli.core.database.R`, `com.blacksquircle.ui.feature.editor.R$drawable`), and a scope key that is an ancestor of the resource namespace, where the whole suffix `.screenshottile.R` matches none of the three patterns.

These classes are not app code by any reading: over the 162 corpus artefacts their 547 methods contain **zero** non-trivial members — no method that a test could call, nothing to cover — so their entire contribution is to enlarge the `cov_class` denominator with classes whose coverage can never rise above zero.

#### Scenario: A multi-module application

- **WHEN** `app.pachli_50.apk` is analysed with effective key `app.pachli` and its compiled classes include `app.pachli.core.database.R` and `app.pachli.feature.intentrouter.R$id`
- **THEN** neither class MUST appear in `reachability`
- **AND** the 117 classes of that shape now present in the artefact MUST all be absent
- **AND** `class_defs_under_key` MUST be counted with the same predicate, so the gate's ratio is unaffected by the repair

#### Scenario: A scope key that is an ancestor of the resource namespace

- **WHEN** `com.github.cvzi.screenshottile_148.apk` is analysed under the detector-elected key `com.github.cvzi`, and the application's resource classes are named `com.github.cvzi.screenshottile.R` and `…R$*`
- **THEN** those classes MUST NOT be counted, even though the suffix left after the key is `.screenshottile.R` and matches no root-anchored pattern
- **AND** the denominator asserted for this APK MUST be the value measured **after** this repair — the pre-repair 550 counted the leaked resource classes and MUST NOT be carried forward as the expected number

#### Scenario: Annotation-processor output stays

- **WHEN** an artefact holds `com.example.MainViewModel_Factory`, `com.example.AppDatabase_Impl` and `com.example.Model$$serializer`
- **THEN** all three MUST remain in the denominator
- **AND** the rule MUST NOT be widened to them by analogy, because they carry methods that execute at runtime and their removal would be a redefinition of what the denominator means

### Requirement: The Crossing Counts What It Discards

The coverage crossing SHALL count every runtime event it does not register, and SHALL classify each discard as out-of-scope or in-scope. An out-of-scope discard means the event's class does not start with the effective key — the application does not own that code, and the discard is correct. An in-scope discard means the class is under the key but the denominator does not contain it, or contains it under a signature that does not match — which is a defect in the chain and MUST be visible.

Both counts SHALL be serialized and SHALL reach the run's CSV output. Without them no repair in this chain is verifiable, and no scope-key rule is safe, because no rule is total.

#### Scenario: A runtime event from a bundled library
- **WHEN** `RVSEC-COV` reports `<okhttp3.internal.Util: void closeQuietly(java.io.Closeable)>` and the effective key is `br.com.colman.petals`
- **THEN** the event MUST be discarded
- **AND** the out-of-scope counter MUST be incremented
- **AND** the in-scope counter MUST NOT be incremented

#### Scenario: A runtime event whose class is in scope but absent from the denominator
- **WHEN** `RVSEC-COV` reports a method of `br.com.colman.petals.settings.SettingsWorker`, the effective key is `br.com.colman.petals`, and that class is not present in the artefact's `reachability` member
- **THEN** the event MUST be discarded
- **AND** the in-scope counter MUST be incremented
- **AND** the counter MUST be serialized in the parser diagnostics and MUST appear in `summary.csv`

### Requirement: The Denominator Gate Refuses Empty and Degenerate Results

The analysis pipeline SHALL apply a plausibility gate to every denominator it produces or consumes, and the gate SHALL fail loudly. The gate reads the two numbers the artefact records — the size of its `reachability` member and `class_defs_under_key` — and it MUST refuse three conditions, each named separately in the failure:

1. **An empty denominator**: `reachability` holds no entries.
2. **A compiled universe of zero**: `class_defs_under_key == 0`. This MUST be tested as its own refusal case, before any division. It is not a corner case — the build-type suffix policy defaults to `False` and 75 of the 162 corpus APKs have zero compiled classes under their manifest key, so a gate written as `parsed / compiled_under_key` raises `ZeroDivisionError` in the default configuration instead of `DenominatorImplausibleError`, and reports nothing about the key that produced the state.
3. **A degenerate denominator**: the ratio of parsed classes to compiled classes under the key falls below `0.15` — the condition that publishes `cov_class = 100.00%` over one class.

The ratio SHALL be computed over a compiled count already filtered by `isAppClass` at write time (INV-ANA-66) — one predicate on both terms. Without that, the raw ratio is depressed by exactly the application's resource classes, which `isAppClass` strips from the parsed side alone. Measured over all 162 corpus artefacts, the raw healthy floor is `0.5610` (`org.cry.otp_31`, 23 of 41) and 17 of 158 healthy applications sit below `0.90` — among them `com.tananaev.passportreader`, at 18 of 28, whose ten missing classes are its `.R` plus nine `R$*`. The claim that healthy small applications sit at 100% is therefore false on the raw counts and true only after the subtraction. With the subtraction applied, all 158 healthy artefacts sit at exactly 1.0 (the corrected ratio is the client's own filter re-derived, so the agreement is exact) and the four collapsed artefacts sit between 0.0010 and 0.0393, so a threshold of `0.15` stands 3.8× above the collapsed ceiling and 6.7× below the healthy floor, inside a 25.5× separation, rather than being calibrated against either band. The calibration holds under the **neutralized** key: under the literal manifest key, 75 of the 162 have no compiled class at all (a `0/0` is not a low ratio, it is the zero-universe refusal above).

The gate covers the **class** universe only. `cov_reachable`, `cov_reaches_target` and `cov_directly_reaches_target` are published columns with denominators of their own (`reachable_methods_total`, `target_methods_total`) that the gate does not check; those predicates are shaped by `Hierarchy.appClasses` (`Hierarchy.java:305` → `FlowgraphRebuilder.java:72`), which `libPackages.txt` continues to govern even after the demotion guard is repaired. The repair takes the deny-list out of the **class** denominator, not out of those three.

The gate is an instrument of detection, not a redefinition of the denominator: the list GATOR produces inside the informed package remains the 100% by definition.

The 162 artefacts already on disk carry neither a recorded key nor `class_defs_under_key`, and `modules/rv-platform/src/rv_platform/components/result_processor.py:245-325` re-parses `.apk.json` on every resume and on every `--process-results` run, so these artefacts remain live inputs. An artefact that records no key SHALL be treated as one whose key is unknown, never as one whose key can be recovered: the key is `None`, the gate does not run, and the accounting degrades honestly rather than guessing. The key MUST NOT be re-derived from the artefact's `package` member — INV-ANA-58 forbids it, and re-derivation reproduces precisely the defect the recorded key exists to expose.

#### Scenario: A collapsed denominator
- **WHEN** an artefact for `br.com.colman.petals_3040000.apk` reports 1 class in `reachability` and records `class_defs_under_key = 762` under the effective key `br.com.colman.petals`
- **THEN** the ratio MUST be `1 / 762 ≈ 0.0013`, below the `0.15` threshold
- **AND** the gate MUST refuse the artefact
- **AND** the run MUST fail with a message naming the class count, the compiled count and the effective key
- **AND** the pipeline MUST NOT publish a coverage percentage for that APK

#### Scenario: An empty denominator
- **WHEN** an artefact's `reachability` member is empty
- **THEN** the gate MUST refuse the artefact
- **AND** the failure MUST name the effective key, because an empty result is the signature of a key that matches nothing

#### Scenario: No class is compiled under the effective key
- **WHEN** an artefact records `class_defs_under_key = 0` for effective key `br.com.colman.petals.debug`, the state of 75 of the 162 corpus APKs while the suffix-stripping policy is `False`
- **THEN** the gate MUST refuse the artefact on that condition alone, before computing any ratio
- **AND** the failure MUST name `br.com.colman.petals.debug` as the key under which zero classes were counted
- **AND** the run MUST NOT raise `ZeroDivisionError`

#### Scenario: A genuinely small application
- **WHEN** an artefact for `com.tananaev.passportreader` reports 18 classes in `reachability` and records `class_defs_under_key = 18`, its 28 compiled classes minus the ten generated ones — one `com.tananaev.passportreader.R` and nine `R$*` — that `isAppClass` removed at write time
- **THEN** the ratio MUST be `18 / 18 = 1.00`, above the `0.15` threshold
- **AND** the gate MUST admit the artefact with no warning
- **AND** the raw ratio `18 / 28 = 0.6429` MUST NOT be what the artefact records, because it would report a healthy application as an outlier

#### Scenario: A legacy artefact that records no key
- **WHEN** a resume or a `--process-results` run re-parses one of the 162 existing artefacts, which carries neither a recorded effective key nor `class_defs_under_key`
- **THEN** the effective key for that task MUST be `None`
- **AND** the gate MUST NOT run, because it has no compiled count to test against
- **AND** every discard MUST be counted as **unclassified**, not attributed to the in-scope counter, since without a key neither scope can be decided
- **AND** the two `unmatched_*` columns of that row MUST be empty, because no classification was possible
- **AND** the coverage cells MUST still be computed from the artefact's own denominator: the effective key classifies discards and nothing else, and all 162 stored artefacts carry a non-empty `reachability` (from 1 to 14,860 classes). Emptying their coverage would delete, on every resume and every `--process-results`, the measurement INV-PLT-15 and INV-PLT-16 exist to recover. `measured` answers to the denominator alone (INV-PLT-35), never to the presence of a recorded key
- **AND** no component MUST re-derive the key from the artefact's `package` member

### Requirement: A Stored Artefact Is Reused Only Under Its Own Key

A run that finds an analysis artefact already on disk SHALL compare the key that artefact records against the run's own effective scope key, and SHALL NOT reuse it silently when the two differ. It MUST either regenerate the artefact or abort with a message naming both keys.

Nothing in the pipeline today can make that comparison. `StaticAnalyzer._execute_command` treats the mere existence of `<apk>.apk.json` as a cache hit (`static_analysis.py:323-335`), and the code says so out loud: *"We do not validate content -- existence implies a previous run completed"*. The filename carries no key (`:198-200`), and neither does the content: the artefact's `package` member is the **manifest** package whatever key actually filtered the file. Before this change there was no invalidation path either — the standalone `--force` flag was declared twice at `modules/rv-static-analysis/src/rv_static_analysis/__main__.py:214` and `:236` and never read, so the only way to invalidate a stale artefact was to delete it by hand.

The consequence is specific to this change: a re-run whose scope-key policy changed reuses the artefact produced under the old policy, and the new denominator gate then evaluates an old artefact against a new key. The recorded key of INV-ANA-66 is what makes that mismatch detectable instead of invisible.

#### Scenario: A re-run under a changed scope-key policy
- **WHEN** `results/<id>/br.com.colman.petals_3040000.apk.json` records effective key `br.com.colman.petals.debug`, and the run is re-executed with the suffix-stripping policy enabled so that its effective key is `br.com.colman.petals`
- **THEN** the stored artefact MUST NOT be treated as a cache hit
- **AND** the run MUST regenerate it, or abort with a message naming both `br.com.colman.petals.debug` and `br.com.colman.petals`
- **AND** the denominator gate MUST NOT be evaluated over the stored artefact under the new key

#### Scenario: A re-run under the same key
- **WHEN** the stored artefact records effective key `app.pachli` and the run's effective key is `app.pachli`
- **THEN** the artefact MUST be reused as a cache hit, with GATOR not re-executed
- **AND** the reuse MUST follow the existing cache-hit path unchanged — the key comparison adds a condition to reuse, never a new way of reusing

#### Scenario: An explicit request to discard the cache
- **WHEN** the stored artefact records effective key `com.github.cvzi.screenshottile` and the run's effective key is the same, but the run is invoked with `--force`
- **THEN** the stored artefact MUST be discarded before the analysis runs, and GATOR MUST be re-executed
- **AND** the log MUST show `Executing analysis`, never `Analysis result already exists`
- **AND** this is the only path by which a matching key is deliberately not honoured — an A/B over one directory, or a re-measurement against a rebuilt jar, has no other way to say "measure again"

