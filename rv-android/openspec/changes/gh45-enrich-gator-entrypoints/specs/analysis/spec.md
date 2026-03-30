# Delta Specification: Analysis and Coverage

## Purpose

Extends the Unified Static Analysis requirement (FR04-FR06) to include Service, BroadcastReceiver, and ContentProvider lifecycle methods as entry points in the call graph traversal performed by `RvsecAnalysisClient`. Currently, only Activity classes serve as entry points, causing methods reachable only through these non-GUI components to be excluded from the `reachableSet` and MOP reachability analysis. This change also adds a `components{}` section to the JSON output with intent-filters (or authorities for providers), exported status, and MOP reachability per component, and replaces `isActivity`/`isMainActivity` booleans with `componentType`/`isMain` in `reachability[]` entries.

The rv-static-analysis Python parser (`StaticAnalysisParser`) and the `Clazz` domain model are updated to parse the new `componentType`/`isMain` fields. The old `isActivity`/`isMainActivity` fields are removed from the JSON. The `components{}` section is consumed by APE-RV's `MopData` (Java, on-device).

---

## MODIFIED Requirements

### Requirement: Unified Static Analysis — Window Transition Graph, GUI Elements, and Method Reachability (FR04, FR05, FR06)

The system MUST run a single GATOR analysis client to produce a single JSON output file containing four data sections written in priority order: (1) method reachability relative to MOP specifications (coverage denominator), (2) window and widget inventory with event listeners, (3) window transition graph, and (4) non-Activity component data (Services, BroadcastReceivers, ContentProviders) with intent-filters/authorities and MOP reachability.

The analysis tool is a GATOR client (`RvsecAnalysisClient`) that implements the `GUIAnalysisClient` interface. GATOR initializes Soot once, builds its constraint graph and fixpoint analysis, and then invokes the client's `run(GUIAnalysisOutput output)` method. Inside this method, the client writes each JSON section incrementally with explicit flush, so that a timeout or crash after any section produces a parseable partial file. The execution order inside `run()`:

1. **Enumerates application classes and computes method reachability** using `Scene.v().getApplicationClasses()` for class/method enumeration and `Scene.v().getCallGraph()` + JGraphT for reachability flags. Entry points include: Activity lifecycle handlers and public/protected methods (via `output.getActivities()`), Service lifecycle methods (`onCreate`, `onStartCommand`, `onBind`, `onUnbind`, `onRebind`, `onDestroy`, `onHandleIntent`) and public/protected methods (via `XMLParser.getServices()`), BroadcastReceiver lifecycle method (`onReceive`) and public/protected methods (via `XMLParser.getReceivers()`), and ContentProvider lifecycle methods (`onCreate`, `query`, `insert`, `update`, `delete`, `call`, `openFile`) and public/protected methods (via `XMLParser.getProviders()`). Service, Receiver, and Provider class names are resolved to `SootClass` via `Scene.v().getSootClassUnsafe()`, which returns `null` for unresolvable classes (logged as WARNING, skipped). Lifecycle methods are found by iterating `SootClass.getMethods()` and filtering by name. For each application method, it computes: `reachable` (reachable from entry points), `reachesMop` (has path to a monitored API method), and `directlyReachesMop` (directly invokes a monitored API method). MOP method signatures are loaded from `.mop` specification files via `JavamopFacade`. This section is written and flushed first.

2. **Extracts windows and widgets** using GATOR's internal APIs — unchanged.

3. **Extracts the Window Transition Graph** — unchanged.

4. **Extracts non-Activity components** (Services, BroadcastReceivers, ContentProviders) from `XMLParser.getServices()`, `XMLParser.getReceivers()`, and `XMLParser.getProviders()`, enriched with intent-filters from `IntentFilterManager` (for Services/Receivers) or `android:authorities` attribute (for Providers), `android:exported` attribute from the manifest, and MOP reachability cross-referenced with the reachability BFS results. This section is written and flushed last — lowest priority for timeout graceful degradation.

The `complementWithCallbacks()` method, which propagates MOP flags for lifecycle and event handlers, MUST also include Service, Receiver, and Provider lifecycle methods in its callback set, so they receive MOP flag propagation via the call graph.

Each entry in `reachability[]` MUST include `componentType` (string: `"activity"`, `"service"`, `"receiver"`, `"provider"`, or `null`) and `isMain` (boolean) fields. The old `isActivity` and `isMainActivity` fields are removed. The `StaticAnalysisParser` (Python) MUST parse these fields into the `Clazz` domain model (`component_type: str | None`, `is_main: bool`).

**Module**: rv-static-analysis (launcher + parser), rvsec-gator (analysis client)
**Key components**: `RvsecAnalysisClient`, `XMLParser`, `DefaultXMLParser`, `IntentFilterManager`, `StaticAnalysisParser`, `Clazz`

#### Scenario: Successful static analysis with valid APK

- **WHEN** `StaticAnalyzer._run_analysis()` is called with a valid APK path and the analysis client JAR exists at `lib/gator/rvsec-analysis-client.jar`
- **THEN** the system MUST execute the GATOR Python script with arguments: `python gator a -p <apk_path> --client-jar <analysis_client_jar> --out <output_file> -client RvsecAnalysisClient -clientParam mopDir=<mop_dir> --timeout <timeout> -withCHA`
- **AND** the resulting `.json` file MUST be parseable by `StaticAnalysisParser` into a `StaticAnalysisData` containing non-empty `Classes`, `Windows`, and `WindowTransitionGraph`
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

#### Scenario: Components section in JSON — app with Services, Receivers, and Providers

- **WHEN** an APK declares Receiver `com.example.app.BootReceiver` with intent-filter action `android.intent.action.BOOT_COMPLETED`, Service `com.example.app.CryptoService` with action `com.example.START_CRYPTO`, and Provider `com.example.app.DataProvider` with authorities `com.example.app.data`
- **THEN** the JSON MUST contain:
  ```json
  "components": {
    "receivers": [{
      "className": "com.example.app.BootReceiver",
      "intentFilters": [{"actions": ["android.intent.action.BOOT_COMPLETED"], "categories": []}],
      "exported": true,
      "reachesMop": true,
      "mopMethods": ["<com.example.app.BootReceiver: void onReceive(android.content.Context,android.content.Intent)>"]
    }],
    "services": [{
      "className": "com.example.app.CryptoService",
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

#### Scenario: Components section — app without non-Activity components

- **WHEN** an APK declares no Services, BroadcastReceivers, or ContentProviders
- **THEN** the JSON MUST contain `"components": {"receivers": [], "services": [], "providers": []}`
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
