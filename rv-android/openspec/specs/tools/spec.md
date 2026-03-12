# Specification: Tool Infrastructure

## Purpose

The Tool Infrastructure domain provides the plugin system, registry, factory, and device interaction layer that enable RV-Android to integrate diverse Android testing tools through a uniform interface. It spans two modules -- **rv-tools** (registry, factory, and 8 built-in tool implementations) and **rv-uiautomator** (shared device interaction components) -- and is consumed by rv-platform (task execution), rv-experiment (experiment orchestration), and rv-agent (LLM-driven exploration).

### Problem Addressed

RV-Android evaluates multiple Android test-generation tools (Monkey, DroidBot, APE, FastBot, ARES, DroidMate, Humanoid, QTesting) and an LLM-driven agent (rv-agent) in runtime verification experiments. Each tool has different invocation mechanisms (ADB shell commands, Python scripts, Docker containers, JAR files), configuration schemas, process patterns for cleanup, and supported variants (e.g., DroidBot offers 6 exploration policies). Without a unified abstraction, experiment orchestration code would contain tool-specific branching, making it difficult to add new tools or run multi-tool experiments.

### Design Decisions

1. **Singleton Registry**: `ToolRegistry` uses a class-level singleton (`_instance`) to ensure a single source of truth for registered tools. All modules that need tools -- rv-platform's `ToolExecutionComponent`, rv-experiment's CLI, CLI's `list-tools` command -- access the same instance via `ToolRegistry.get_instance()`. The registry provides `reset_instance()` for test isolation.

2. **Auto-Registration at Import**: When `rv_tools` is imported, `_register_builtin_tools()` iterates over `BUILTIN_TOOLS` (a list of 8 tool classes from `rv_tools.builtin`) and calls `registry.register_tool_class(tool_class)` for each. This means the 8 built-in tools are available immediately after `import rv_tools`. Registration failures are logged as warnings but do not block module import.

3. **External Tool Registration via rv-platform**: Tools that live outside rv-tools (rvagent in `rvagent-tool`) are registered by `_register_external_tools()` in rv-platform's `__init__.py` when that module is imported. The function checks `is_tool_registered("rvagent")` before attempting registration to ensure idempotency. This respects the module dependency hierarchy: rv-tools depends only on rv-android-core, while rvagent-tool depends on rv-agent + rv-tools.

4. **AbstractTool Contract**: All tools extend `AbstractTool` (defined in rv-android-core), which enforces a template method pattern: `execute()` calls `execute_tool_specific_logic()`, handles `RVCommandTimeoutError` (converting it to `RVToolTimeoutError` -- timeouts are expected behavior), performs process cleanup via `kill_related_processes()`, and delegates to `ErrorHandler` for other exceptions. This gives every tool consistent timeout handling and cleanup.

5. **Variant System**: Each tool defines named variants as dictionaries of configuration parameters. Variants are registered alongside the tool class in the registry. The factory resolves a variant by name, merges it with any additional parameters from the experiment configuration, and calls `tool.configure(merged_config)`. This enables the tool specification DSL (`droidbot:dfs_greedy@count=5000`).

6. **UIAdapter Abstraction**: `UIAdapter` (in rv-uiautomator) defines a framework-agnostic interface for device operations. Currently, only `UIAutomator2Adapter` implements it (using the `uiautomator2` Python library). This abstraction enables future alternative backends without changing higher-level code.

7. **Action Executor Pattern**: `UIAutomatorActionExecutor` translates `GeneratedAction` objects (from LLM or algorithm) into concrete `UIAdapter` method calls. It dispatches on `WidgetEventType` (CLICK, LONG_CLICK, TEXT_CHANGE, SCROLL, BACK) and supports custom coordinate-based actions from vision strategies.

8. **State Format Conversion**: `StateConverter` bridges the UIAutomator state format (`xml`, `current_activity`, `current_package`) and DroidBot's expected format (`view_tree`/`hierarchy`, `activity`, `package_name`). This is documented as a temporary solution; the long-term plan is a typed `DeviceState` model.

### Data Models

```
ToolSpec (BaseValidatedModel):
  name: str               # Tool identifier used in registry keys and CLI
  description: str        # Human-readable tool description
  url: str                # Repository or documentation URL
  version: str            # Version string (default "1.0.0")
  process_pattern: str?   # Pattern for kill_related_processes() cleanup (nullable)

ToolConfig (BaseValidatedModel, defined in rv-android-core):
  name: str               # Tool identifier (must match registry key)
  variant: str            # Variant name (singular, default "default")
  parameters: Dict        # Parameter overrides

AbstractTool (ABC):
  name: str               # Tool identifier (from ToolSpec.name)
  description: str        # Tool description (from ToolSpec.description)
  process_pattern: str    # Process pattern for cleanup
  config: Dict            # Resolved configuration (set by configure())
  logger: Logger          # Structured logger
  error_handler: ErrorHandler
  circuit_breaker: CommandCircuitBreaker

UIAdapter (ABC):
  (no state -- pure interface)
  Methods: connect, get_ui_state, click, input_text, long_click,
           swipe, press_back, press_home, take_screenshot,
           launch_app, stop_app

UIAutomator2Adapter (UIAdapter):
  device_id: str          # Target device (default "emulator-5554")
  device: u2.Device?      # UIAutomator2 device handle
  connected: bool         # Connection status
```

### Component Interactions

```
Module Import
     |
     v
rv_tools.__init__ --> _register_builtin_tools()
     |                          |
     |                 For each BUILTIN_TOOLS[]:
     |                          |
     v                          v
ToolRegistry.get_instance() <-- register_tool_class(tool_class)
     |                              |
     |                     tool_class.get_tool_spec() --> ToolSpec
     |                     tool_class.get_variants()  --> Dict[str, Dict]
     |                              |
     |                     register_variant() for each variant
     v
rv_platform.__init__ --> _register_external_tools()
     |                          |
     |                 is_tool_registered("rvagent")? --> skip if True
     |                          |
     |                 import RVAgentTool from rvagent_tool
     |                 register_tool_class(RVAgentTool)
     v
ToolFactory.create_tool(tool_config)
     |
     +-- Resolve tool_class from registry
     +-- Get variant_config from registry
     +-- Merge with tool_config.parameters
     +-- Create tool_class() instance
     +-- Call tool.configure(merged_config)
     v
Configured AbstractTool instance
     |
     v
TaskExecutor (rv-platform) --> tool.execute(task, app)
     |
     +-- execute_tool_specific_logic(task, app) [tool-specific]
     +-- kill_related_processes(process_pattern) [cleanup]
     +-- ErrorHandler for exceptions
```

```
UIAutomator2Adapter                 UIAutomatorActionExecutor
        |                                     |
        v                                     v
  u2.connect(device_id)              execute(action, adapter)
  device.dump_hierarchy()                |
  device.click(x, y)             dispatch on WidgetEventType:
  device.send_keys(text)           CLICK  -> adapter.click(x, y)
  device.long_click(x, y, dur)    TEXT_CHANGE -> adapter.click + adapter.input_text
  device.swipe(...)               LONG_CLICK -> adapter.long_click(x, y, dur)
  device.press("back"/"home")     SCROLL -> adapter.swipe(x1, y1, x2, y2)
  device.screenshot(path)         BACK   -> adapter.press_back()
  device.app_start(package)       custom -> adapter.click(coords)
  device.app_stop(package)
```

### Relationship with Other Domains

**Consumers:**
- **rv-platform**: `ToolFactory.create_tool()` in `ToolExecutionComponent` to instantiate tools for task execution. Uses `ToolRegistry` for tool validation and discovery.
- **rv-experiment**: Uses `ToolRegistry.get_instance()` from rv-tools directly. CLI parses tool specification DSL and generates `ToolConfig` objects.
- **rv-agent**: Uses `UIAutomator2Adapter` (via rv-uiautomator) for device interaction. `UIAutomatorActionExecutor` executes generated actions. `RVAgentTool` (in rvagent-tool module) wraps rv-agent as an `AbstractTool`.

**Dependencies:**
- **rv-android-core**: Provides `AbstractTool`, `ToolSpec`, `Command`, `CommandResult`, `ErrorHandler`, `LoggingManager`, `PerformanceMonitor`, `BaseValidatedModel`, domain models (`Task`, `App`, `WidgetEventType`), and exception classes.
- **rv-screen-parser**: rv-uiautomator depends on it for UI parsing capabilities.
- **uiautomator2**: Python library for device communication (external dependency).
- **pillow**: Image processing for screenshot management (external dependency).

## Data Contracts

### Input

- `tool_config: ToolConfig` -- Tool name, variant, and parameter overrides. Provided by rv-platform from `PlatformConfig.tools` or by rv-experiment's CLI DSL parser.
- `task: Task` -- Task context containing execution timeout, device serial, result paths, and static analysis data. Provided by rv-platform's `TaskExecutor`.
- `app: App` -- Application under test with `package_name`, `path` (APK file), and metadata. Provided by rv-platform's APK discovery.
- `device_id: str` -- Android device identifier (default `"emulator-5554"`). Provided by emulator management or user.

### Output

- `tool_instance: AbstractTool` -- Configured tool instance ready for execution. Consumed by rv-platform's `ToolExecutionComponent`.
- `ui_state: Dict[str, Any]` -- Device UI state containing `xml` (hierarchy), `current_activity`, `current_package`, `device_info`, `timestamp`. Consumed by rv-agent and rv-screen-parser.
- `execution_result: bool` -- Success/failure of action execution. Consumed by rv-agent's execute_node.
- `registry_info: Dict[str, Any]` -- Registry statistics and metadata including `total_tools`, `total_variants`, `tools` list, `variants_by_tool` mapping. Consumed by CLI and diagnostics.

### Side-Effects

- **Device**: UIAutomator2Adapter performs clicks, swipes, text input, button presses, app launches/stops, and screenshot captures on the connected Android device/emulator.
- **File System**: Screenshot files written to configurable directory (`./screenshots/` default). Tool trace files written to `task.result.trace_file` during execution.
- **Processes**: `kill_related_processes()` terminates device-side processes matching the tool's `process_pattern` via `adb shell kill`.
- **Logging**: All operations emit structured log entries via `LoggingManager` with component context.

### Error

- `ToolNotFoundError` -- Raised when requesting a tool or variant that is not registered in the registry.
- `ToolRegistrationError` -- Raised when tool class registration fails (e.g., `get_tool_spec()` or `get_variants()` throws).
- `ConfigurationError` -- Raised when tool configuration is invalid (e.g., missing required parameter, invalid variant name, invalid DroidBot policy).
- `ToolCreationError` -- Raised when `ToolFactory.create_tool()` fails during instance creation.
- `RVToolTimeoutError` -- Raised when tool execution exceeds the configured timeout. This is expected behavior and is handled gracefully (task is marked as completed, not failed).
- `RVToolExecutionError` -- Raised when a tool command returns a non-zero exit code.
- `CircuitBreakerOpenError` -- Raised when the circuit breaker blocks command execution after consecutive failures.

## Invariants

- **INV-TOOL-01**: The `ToolRegistry` singleton MUST return the same instance across all callers within a process. `ToolRegistry.get_instance()` MUST always return a non-None `ToolRegistry` object. `reset_instance()` MUST only be used in test code.

- **INV-TOOL-02**: Every registered tool MUST have at least a `"default"` variant. The `get_variants()` classmethod MUST return a dictionary containing the key `"default"`.

- **INV-TOOL-03**: Tool names MUST be unique within the registry. Registering a tool with an existing name MUST replace the previous registration and log a warning. The registry MUST NOT contain duplicate tool names.

- **INV-TOOL-04**: A `ToolSpec` MUST have non-empty `name`, `description`, `url`, and `version` fields. These fields are validated by Pydantic via the `@validated_model(['name', 'description', 'url', 'version'])` decorator.

- **INV-TOOL-05**: `ToolFactory.create_tool()` MUST call `tool.configure(config)` before returning the tool instance. A tool instance returned by the factory MUST have its configuration applied.

- **INV-TOOL-06**: `AbstractTool.execute()` MUST convert `RVCommandTimeoutError` to `RVToolTimeoutError`. Tool timeouts MUST NOT be treated as errors -- they indicate the tool ran for the full allocated time.

- **INV-TOOL-07**: `AbstractTool.execute()` MUST call `kill_related_processes()` after successful execution. Process cleanup MUST NOT raise exceptions that propagate to the caller (cleanup errors are logged as warnings).

- **INV-TOOL-08**: Built-in tool auto-registration MUST NOT fail the `rv_tools` module import. Any individual tool registration failure MUST be logged as a warning and skipped.

- **INV-TOOL-09**: `UIAutomator2Adapter` MUST check `self.connected` and `self.device is not None` before every device operation. If the device is not connected, the operation MUST return `False` (for actions) or `{}` (for state capture) without raising an exception.

- **INV-TOOL-10**: `UIAutomatorActionExecutor.execute()` MUST dispatch actions based on `WidgetEventType`. Unknown action types MUST return `False` and log a warning. The executor MUST NOT raise exceptions to the caller -- all errors MUST be caught and returned as `False`.

- **INV-TOOL-11**: `StateConverter.uiautomator_to_droidbot()` MUST map `xml` to both `view_tree` and `hierarchy`, `current_activity` to `activity`, and `current_package` to `package_name`. The converted state MUST include `_conversion_metadata` with source and target format identifiers.

- **INV-TOOL-12**: External tool registration in rv-platform MUST be idempotent. The `_register_external_tools()` function MUST check `is_tool_registered("rvagent")` before calling `register_tool_class()`. Multiple imports of `rv_platform` MUST NOT produce duplicate registrations.

- **INV-TOOL-13**: Variant configuration returned by `get_variant_config()` MUST be a copy of the stored configuration, not a reference. Modifications to the returned dictionary MUST NOT affect the registry's internal state.

- **INV-TOOL-14**: `UIAutomator2Adapter.connect()` MUST configure UIAutomator2 settings (`wait_timeout`) after successful connection. The `_configure_uiautomator_settings()` method MUST be called before returning `True`.

- **INV-TOOL-15**: When ARES or QTesting tools build their Docker `run` command inside a Docker container (detected by the presence of `/.dockerenv`), the command MUST include `--network container:<hostname>` where `<hostname>` is the current container's ID obtained via `socket.gethostname()`. This flag makes the sibling container (ARES/QTesting) share the parent container's network namespace, allowing it to reach the emulator at `localhost:5554` without any network configuration changes in the ARES/QTesting code or Dockerfiles. When running outside Docker (`/.dockerenv` does not exist), the command MUST use `--network host` so the sibling container shares the host's network namespace and can reach the emulator at `localhost:5554`.

- **INV-RSM-20**: `UICoverageTracker` MUST track elements per screen using hybrid IDs: `"res:{resource_id}"` when the element has a non-empty `resourceId`, otherwise `"coords:{centerX},{centerY}"`. This avoids coordinate collision for overlapping widgets (e.g., Button containing ImageView) while handling elements without resource IDs. Each element MUST be associated with exactly one screen hash. The tracker MUST NOT duplicate element registrations across visits to the same screen — re-visiting a screen updates interaction counts but does not re-register already-known elements.

- **INV-RSM-21**: `UICoverageTracker.getCoverageGap(screenHash)` MUST return a value between 0.0 (all elements tested at least once) and 1.0 (no elements tested). If the screen hash is unknown, it MUST return 1.0 (fully unexplored). The value MUST be consistent with the actual interaction count: an element with interactionCount > 0 MUST be counted as tested.

- **INV-RSM-22**: `PlateauDetector` MUST use a sliding window of exactly 10 iterations. A plateau is detected WHEN the window contains zero new-state events AND zero new-MOP-coverage events. The plateau state MUST be cleared immediately when either a new state or new MOP coverage is observed.

- **INV-RSM-23**: During a detected plateau, `ActionSelector` MUST use a stochastic probability of 0.5 (instead of the default 0.15). When the plateau clears, the stochastic probability MUST revert to the configured default. The boost MUST NOT persist beyond one iteration after plateau clearance.

- **INV-RSM-24**: `InputValueGenerator` MUST select input values based on the widget's `hint`, `resource_id`, or `inputType` attributes. It MUST NOT use the same input value twice for the same element within a single exploration run. If all generated values have been used, it MUST cycle back to the first value.

- **INV-RSM-25**: `WtgScorer` MUST read the `transitions` section of the static analysis JSON (loaded by `StaticMap`). It MUST perform BFS of depth 3 on the transitions graph with diminishing boost: +200 for 1-hop transitions to unvisited activities, +100 for 2-hop transitions to unvisited activities, +50 for 3-hop transitions to unvisited activities or any-hop transitions to under-visited activities (visitCount < 3). If no static analysis data is available, `WtgScorer` MUST return 0 for all actions. `WtgScorer` MUST return 0 for SCROLL, BACK, RESTART, and SET_TEXT actions — WTG transitions only describe widget-triggered navigation.

- **INV-RSM-26**: Launcher packages (`com.android.launcher3`, `com.google.android.apps.nexuslauncher`, `com.android.launcher`) MUST trigger immediate app restart in the out-of-app handler, bypassing the tolerance counter. The tolerance counter MUST only apply to non-launcher external packages.

- **INV-RSM-27**: `ActionSelector.generateCandidateActions()` MUST exclude elements whose `packageName` matches `com.android.systemui`. Elements with null or empty `packageName` MUST NOT be excluded (they are framework widgets rendered by the app).

- **INV-RSM-28**: `ActionSelector` MUST trigger proactive backtrack (Tier 3) when `screenNode.getSaturationRate() >= 0.8`. The score-based threshold (`PROACTIVE_BACKTRACK_THRESHOLD`) SHALL NOT be used as the backtrack trigger. This is self-calibrating: it depends only on how many actions have been tried on the current screen, not on scorer weights.

- **INV-RSM-29**: `ActionSelector` MUST apply the failure filter as a safety net, not a hard gate. After filtering out candidates with `failureCount >= 3`, if the filtered list is empty AND there were unfiltered candidates, the unfiltered list MUST be kept instead. An empty candidate list after filtering causes all candidates to be removed and forces RESTART even when valid widget actions exist — for example, when hash blindness causes false failure counts (ViewPager pages with identical structural hashes).

- **INV-RSM-30**: `StaticMap.parseReachability()` MUST parse the `"reachability"` key as a `JsonArray` (not `JsonObject`). Each array element is a class object containing `"className"` (String, fully qualified) and `"methods"` (JsonArray). Each method object contains `"signature"` (String), `"reachable"` (boolean), `"reachesMop"` (boolean), and `"directlyReachesMop"` (boolean). Activity name matching MUST normalize trace-format names (e.g., `"uiactivitiesSplashActivity"`) to fully-qualified names (e.g., `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"`) by reconstructing dots from camelCase boundaries and prepending the code package.

- **INV-RSM-31**: `StaticMap.parseTransitions()` MUST parse the `"transitions"` key as a `JsonArray`. Each array element contains `"sourceId"` (int), `"targetId"` (int), and `"events"` (JsonArray of {type, widgetClass} objects). The parser MUST build an adjacency map from window IDs to their transitions, cross-referencing window IDs with activity names from the `"windows"` section.

- **INV-RSM-32**: The rvsmart scoring chain MUST consist of exactly 7 scorers: `MopScorer`, `WtgScorer`, `GradualDecayScorer`, `SystemElementFilter`, `ComponentPriorityScorer`, `ConfirmedCoverageScorer`, `CoverageDensityScorer`. The `RewardScorer` and `RewardPropagator` classes MUST NOT exist in the codebase — they are deleted per P3 (no backward compatibility). `CoverageDensityScorer` becomes functional once the `UICoverageTracker` ID mismatch is fixed (INV-RSM-39).

- **INV-RSM-33**: When out-of-app is detected with `consecutiveOoaAfterRestart >= MAX_CONSECUTIVE_OOA_AFTER_RESTART`, the recovery sequence MUST: (1) send `input keyevent BACK` via `adb shell`, (2) if still out-of-app, call `am force-stop <foregroundPackage>`, (3) then `forceStop(targetPackage)` and `startApp(targetPackage)`. The `foregroundPackage` MUST be obtained from `root.getPackageName()` at OOA detection time.

- **INV-RSM-34**: When `ActionSelector.generateCandidateActions()` produces 0 interactive candidates AND the current screen has no parent in `SuccessorTracker`, the agent MUST `Thread.sleep(2000)` and recapture the screen before falling back to RESTART. This allows splash screen auto-transitions (Handler/Timer-based) to complete. If the recapture still produces 0 candidates, RESTART is the correct fallback.

- **INV-RSM-35**: When `action.type == SET_TEXT`, the `hadEffect` variable MUST be set to `true` unconditionally after action execution. The structural hash excludes text content by design (to avoid state explosion from dynamic content), so SET_TEXT never changes the hash — but it always changes the UI content. This prevents the stuck detector from counting SET_TEXT as "no progress" and triggering premature RESTART during form filling.

- **INV-RSM-36**: When `runIteration()` throws an exception caught by the `run()` method's catch block, the agent MUST write a trace line with `action_type="ERROR"` and the exception message to stdout before continuing to the next iteration. Additionally, all 6 early-return paths in `runIteration()` — (1) crash-at-start, (2) null root from `getRootInActiveWindow()`, (3) system dialog dismiss, (4) post-action crash, (5) post-action native crash, (6) OOA tolerance-not-exceeded — MUST write a trace line with `action_type="SKIP"` and a `reason` field describing the exit cause.

- **INV-RSM-37**: Every `AccessibilityNodeInfo` obtained via `getRootInActiveWindow()` MUST be recycled via `root.recycle()` in a `finally` block. This applies to all 4 call sites in `AgentLoop`: (1) initial capture at iteration start, (2) post-action capture, (3) adaptive wait recapture, (4) OOA detection capture. Failure to recycle causes native object accumulation (~4000 objects per 300s run) that can trigger OOM in long-running sessions.

- **INV-RSM-38**: `PathBuffer.invalidateIfDiverged(currentHash)` MUST compare `currentHash` against `expectedHashes[currentIndex]` (the hash at the current position in the planned path), NOT against `expectedHashes[currentIndex + 1]` or any other offset. An off-by-one error causes all multi-hop BFS recovery paths to fail on the first hop.

- **INV-RSM-39**: `UICoverageTracker` MUST use the same element ID scheme for both `registerScreenElements()` and `recordInteraction()`. If registration uses `"res:{resource_id}"` for elements with resource IDs, then `recordInteraction()` MUST also receive `"res:{resource_id}"` (not `"coords:{x},{y}"`). Mismatched ID schemes cause the tracker to never match registered elements with their interactions, making `getCoverageGap()` always return the maximum value.

- **INV-RSM-40**: `ScreenNode.totalActions` MUST be updated on every visit to the screen via `Math.max(existingTotal, currentCount)`. If the first visit to a screen captures 0 elements (transient UI state during activity transition), `totalActions` MUST NOT be permanently locked to 0 — subsequent visits with more elements MUST update the count. A permanent 0 causes `getSaturationRate()` to return 1.0, triggering premature proactive backtracking.

- **INV-RSM-41**: `UICoverageTracker.recordInteraction(screenHash, elementId)` MUST use `screenHash` to scope interactions by screen. The interaction counts map MUST use a composite key `screenHash + "|" + elementId` so that interactions recorded on screen A do not count toward coverage of elements on screen B that happen to share the same element ID (e.g., same resource ID used in different activities).

- **INV-RSM-42**: `AgentLoop` MUST use the return value of `HeapMonitor.check()` as the actual sleep duration between iterations, instead of always sleeping `config.getThrottleMs()`. When heap pressure is normal, `check()` returns the configured throttle value (no behavior change). When heap pressure is high, `check()` returns a larger value that MUST actually delay the next iteration.

- **INV-RSM-43**: When `SystemDialogDetector.dismiss()` fails to dismiss a system dialog, `AgentLoop` MUST: (a) sleep 500ms to prevent CPU spinning (prevents 646 it/s SKIP storms), (b) increment a `consecutiveSystemDialogs` counter. When `consecutiveSystemDialogs >= 3`, the agent MUST press BACK. When `consecutiveSystemDialogs >= 6`, the agent MUST force-stop the foreground app and restart the target. The counter MUST reset to 0 when any non-system-dialog iteration runs.

- **INV-TOOL-TRACE-01**: The rvsmart trace file format (`RVTRACK:` lines) SHALL remain parseable by existing post-processing scripts. New trace line types MAY be added with distinct prefixes but existing prefixes SHALL preserve their format.

- **INV-TOOL-METRICS-01**: The `RVSMART_METRICS:` JSON SHALL be a strict superset of the gh32 metrics schema — no existing fields removed, only new fields added.

## Requirements

### Requirement: Tool Registration and Factory System (FR18, NFR02)

The tool system MUST provide a centralized registry and factory for all Android testing tools. `ToolRegistry` maintains a singleton registry of tool classes and their variant configurations. `ToolFactory` creates configured tool instances from `ToolConfig` objects.

The factory resolution flow in `ToolFactory.create_tool()` is:
1. Resolve `tool_class` from registry using `tool_config.name`.
2. Get `variant_config` from registry using `tool_config.name` and `tool_config.variant`.
3. Merge variant_config with `tool_config.parameters` (parameters override variant values).
4. Create `tool_class()` instance and call `tool.configure(merged_config)`.

#### Scenario: Factory creates configured tool from ToolConfig

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="droidbot"`, `tool_config.variant="dfs_greedy"`, `tool_config.parameters={"count": 5000}`
- **THEN** the factory MUST return a `DroidBotTool` instance
- **AND** the instance MUST have `config["policy"] == "dfs_greedy"` (from variant)
- **AND** the instance MUST have `config["count"] == 5000` (from parameters override)
- **AND** the instance MUST have `config["ignore_ad"] == True` (from variant defaults)

#### Scenario: Factory rejects invalid tool or variant

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="nonexistent_tool"`
- **THEN** the factory MUST raise `ConfigurationError` with a message indicating the tool is not found
- **AND** no tool instance MUST be created

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="droidbot"`, `tool_config.variant="invalid_variant"`
- **THEN** the factory MUST raise `ConfigurationError` with a message indicating the variant is invalid

### Requirement: External Tool Support (FR19, NFR02)

The system MUST support 8 third-party Android test generation tools, each implemented as a class extending `AbstractTool` in the `rv_tools.builtin` package. Each tool implementation follows a consistent pattern: a class-level `TOOL_SPEC` attribute created via `ToolSpec.create_builtin_spec()`, a parameterless `__init__()` that delegates to `super().__init__(name, description, process_pattern)`, and implementations of `get_tool_spec()`, `get_variants()`, `configure()`, and `execute_tool_specific_logic()`.

Tools execute via the template method in `AbstractTool.execute()`: it calls `execute_tool_specific_logic()`, then `kill_related_processes()`. If `RVCommandTimeoutError` is raised, it is converted to `RVToolTimeoutError` (expected behavior). Tools build their specific commands (ADB shell commands, project scripts, etc.) and execute them via `_execute_and_check_command()`, which integrates the circuit breaker pattern for resilience against consistently failing commands.

The 8 built-in tools and their invocation mechanisms are:

| Tool | Module | Invocation | Process Pattern |
|------|--------|------------|-----------------|
| Monkey | `builtin/monkey/` | `adb shell monkey` | `com.android.commands.monkey` |
| DroidBot | `builtin/droidbot/` | `uv run droidbot` | `droidbot` |
| APE | `builtin/ape/` | ADB command | `ape` |
| FastBot | `builtin/fastbot/` | ADB command | `fastbot` |
| ARES | `builtin/ares/` | Docker-based | `ares` |
| DroidMate | `builtin/droidmate/` | JAR execution | `droidmate` |
| Humanoid | `builtin/humanoid/` | DroidBot + Humanoid inference | `humanoid` |
| QTesting | `builtin/qtesting/` | Docker-based | `qtesting` |

The LLM-driven tool (`rvagent`) lives in a separate module (`rvagent-tool`) and is registered via rv-platform's `_register_external_tools()` on import, not as a built-in. Its `RVAgentTool` wraps `rv-agent`'s `AgentFactory` and `RVAgent`, mapping platform `Task`/`App` objects to `RVAgentConfig`.

ARES and QTesting are Docker-based tools that execute via `docker run` commands built by `_build_ares_command()` and `_build_qtesting_command()` respectively. Unlike other tools (Monkey, DroidBot, APE) that run via ADB shell commands or local scripts, these tools spawn a separate Docker container for each execution.

In standalone mode (developer workstation), the spawned container uses `--network host` to share the host's network namespace and reach the emulator at `localhost:5554`. In production Docker deployment (rvandroid container), the spawned container MUST share the parent container's network namespace via `--network container:$(hostname)` (INV-TOOL-15) to reach the emulator at `localhost:5554`.

The Docker socket (`/var/run/docker.sock`) MUST be mounted into the rvandroid container for Docker-based tools to function. Without this mount, `docker run` commands fail because there is no Docker daemon available inside the container. The Docker CLI binary is installed in the tools Docker image layer (`docker/tools/Dockerfile`).

ARES and QTesting images (`phtcosta/ares:latest`, `phtcosta/qtesting:latest`) MUST be pre-built on the Docker host before running experiments that use these tools. They are NOT declared as services in `docker-compose.yml` — they are spawned on-demand at runtime by each rvandroid container. Only Humanoid is declared as a shared service in the compose files because it operates as a REST server that multiple rvandroid containers connect to over the network.

#### Scenario: Monkey tool executes with configured parameters

- **WHEN** a `MonkeyTool` instance is created and configured with variant `"default"` (event_count=1000, throttle=0)
- **AND** `execute(task, app)` is called with `app.package_name="com.example.app"` and `task.config.timeout=60`
- **THEN** the tool MUST build an ADB command: `adb -s <device_id> shell monkey -v -v --ignore-security-exceptions -p com.example.app <event_count>`
- **AND** the command MUST have a timeout of 60 seconds
- **AND** stdout and stderr MUST be redirected to `task.result.trace_file`

#### Scenario: DroidBot tool validates policy configuration

- **WHEN** `DroidBotTool.configure()` is called with `config={"policy": "invalid_policy"}`
- **THEN** a `ConfigurationError` MUST be raised with a message listing available policies
- **AND** the tool MUST NOT be left in a partially configured state

- **WHEN** `DroidBotTool.configure()` is called with `config={"policy": "dfs_greedy", "count": 10000000000}`
- **THEN** `self.config["policy"]` MUST equal `"dfs_greedy"`
- **AND** `self.config["count"]` MUST equal `10000000000`

#### Scenario: Tool timeout is handled as expected behavior

- **WHEN** a tool's `execute_tool_specific_logic()` raises `RVCommandTimeoutError` with `timeout_seconds=300`
- **THEN** `AbstractTool.execute()` MUST raise `RVToolTimeoutError` with `tool_name` and `timeout_seconds=300`
- **AND** the timeout MUST be logged at INFO level (not ERROR)
- **AND** the calling code (rv-platform `ToolExecutionComponent`) MUST treat this as successful completion

#### Scenario: RVAgent tool maps platform context to agent configuration

- **WHEN** `RVAgentTool` is configured with variant `"pure_algorithm"` and `execute_tool_specific_logic(task, app)` is called
- **THEN** `build_agent_config_dict()` MUST produce a dictionary with `agent_mode="pure_algorithm"` and `package_name=app.package_name`
- **AND** `timeout` MUST come from `task.config.timeout`, not from the variant configuration
- **AND** if `task.static_data` is available, it MUST be passed to `AgentFactory.create_agent()`

#### Scenario: Process cleanup after tool execution

- **WHEN** `MonkeyTool.execute()` completes successfully
- **THEN** `kill_related_processes("com.android.commands.monkey")` MUST be called
- **AND** matching processes on the device MUST be terminated via `adb shell kill`
- **AND** any failure during process cleanup MUST be logged as a warning but MUST NOT cause the execution to fail

#### Scenario: Circuit breaker prevents repeated failing commands

- **WHEN** `_execute_and_check_command()` is called and the command returns a non-zero exit code
- **THEN** `circuit_breaker.record_failure()` MUST be called
- **AND** `RVToolExecutionError` MUST be raised with the tool name and error details

- **WHEN** the circuit breaker is in the OPEN state due to consecutive failures
- **THEN** `_execute_and_check_command()` MUST raise `CircuitBreakerOpenError` without executing the command

#### Scenario: ARES Command Includes Network Flag Inside Docker

- **WHEN** `AresTool._build_ares_command()` is called
- **AND** the code is running inside a Docker container (`/.dockerenv` exists)
- **THEN** the generated `docker run` command MUST include `--network container:<hostname>` where `<hostname>` is `socket.gethostname()` (which returns the container ID inside Docker)
- **AND** the `--network` flag MUST appear before the Docker image name in the argument list
- **AND** all other command arguments (volumes, environment variables, ARES-specific flags) MUST remain unchanged

#### Scenario: QTesting Command Includes Network Flag Inside Docker

- **WHEN** `QTestingTool._build_qtesting_command()` is called
- **AND** the code is running inside a Docker container (`/.dockerenv` exists)
- **THEN** the generated `docker run` command MUST include `--network container:<hostname>` where `<hostname>` is `socket.gethostname()`
- **AND** the `--network` flag MUST appear before the Docker image name in the argument list
- **AND** all other command arguments MUST remain unchanged

#### Scenario: Host Network Outside Docker

- **WHEN** `AresTool._build_ares_command()` or `QTestingTool._build_qtesting_command()` is called
- **AND** the code is NOT running inside a Docker container (`/.dockerenv` does not exist)
- **THEN** the generated `docker run` command MUST include `--network host` so the sibling container can reach the emulator at `localhost:5554`
- **AND** no `--network container:` flag MUST be used (container networking is only for Docker-in-Docker)

### Requirement: Per-Tool Variant System (FR20)

Each tool MUST support multiple named variants representing different operational modes and parameter sets. Variants provide a way to reference complete tool configurations by name in experiment specifications, CLI arguments, and configuration files. The variant system enables the tool specification DSL format: `tool_name:variant_name@param=value`.

Variants are defined by each tool's `get_variants()` classmethod, which returns a dictionary mapping variant names to configuration parameter dictionaries. Every tool MUST include a `"default"` variant. Variants are registered in the `ToolRegistry.variants` data structure as a three-level dictionary: `tool_name -> variant_name -> config_dict`.

The variant resolution flow in `ToolFactory.create_tool()` is:
1. If `variant_name` is provided and not `"default"`, validate it exists via `registry.validate_tool_variant()`.
2. Get the variant configuration via `registry.get_variant_config()` (returns a copy).
3. Merge with `tool_config.parameters` (parameters override variant values).
4. Call `tool.configure(merged_config)` on the new instance.

The following tools and their variants are registered in the current system:

| Tool | Variants |
|------|----------|
| monkey | default, fast, stress |
| droidbot | default, dfs_greedy, bfs_greedy, dfs_naive, bfs_naive, random |
| ape | default, sata, bfs, dfs, random |
| fastbot | conservative, aggressive, balanced |
| ares | default, debug, fast |
| droidmate | default, systematic, quick, research |
| humanoid | default, visual, nlp, hybrid |
| qtesting | default, qlearning, dqn, ddqn |
| rvagent | default, multimode, pure_algorithm, llm_only, thorough |

#### Scenario: Listing variants for a registered tool

- **WHEN** `registry.get_tool_variants("droidbot")` is called
- **THEN** the result MUST contain at least `["default", "dfs_greedy", "bfs_greedy", "dfs_naive", "bfs_naive", "random"]`
- **AND** the order of variant names is not significant

#### Scenario: Variant configuration contains complete parameters

- **WHEN** `registry.get_variant_config("droidbot", "dfs_greedy")` is called
- **THEN** the returned dictionary MUST contain `policy="dfs_greedy"`, `count=10000000000`, `interval=3`, `ignore_ad=True`
- **AND** the dictionary MUST contain all parameters needed for `DroidBotTool.configure()` to succeed

#### Scenario: Additional parameters override variant values

- **WHEN** `ToolFactory.create_tool()` is called with variant `"dfs_greedy"` (which has `count=10000000000`) and `parameters={"count": 500}`
- **THEN** the final configuration passed to `configure()` MUST have `count=500`
- **AND** all other variant parameters MUST be preserved (e.g., `policy="dfs_greedy"`, `interval=3`)

#### Scenario: Validating a tool variant combination

- **WHEN** `registry.validate_tool_variant("monkey", "fast")` is called
- **THEN** the result MUST be `True`

- **WHEN** `registry.validate_tool_variant("monkey", "nonexistent")` is called
- **THEN** the result MUST be `False`

#### Scenario: RVAgent variants map to execution modes

- **WHEN** `registry.get_variant_config("rvagent", "pure_algorithm")` is called
- **THEN** the returned dictionary MUST contain `agent_mode="pure_algorithm"` and `strategy="rvagent"`
- **AND** the dictionary MUST NOT contain `llm_probability` (not applicable to pure_algorithm mode)

- **WHEN** `registry.get_variant_config("rvagent", "multimode")` is called
- **THEN** the returned dictionary MUST contain `agent_mode="multimode"`, `llm_probability=0.7`, `strategy="rvagent"`

#### Scenario: Tool specification DSL parsing

- **WHEN** the CLI receives the tool specification string `"droidbot:dfs_greedy@count=5000"`
- **THEN** the parser MUST extract `name="droidbot"`, `variant="dfs_greedy"`, `parameters={"count": "5000"}`
- **AND** the resulting `ToolConfig` MUST be usable by `ToolFactory.create_tool()`

- **WHEN** the CLI receives `"monkey,droidbot:bfs_greedy,rvagent:pure_algorithm"`
- **THEN** the parser MUST produce 3 `ToolConfig` objects, one for each tool specification

### Requirement: Device Interaction Abstraction (UIAdapter and UIAutomator2)

The rv-uiautomator module MUST provide a framework-agnostic device interaction interface (`UIAdapter`) with a concrete UIAutomator2 implementation (`UIAutomator2Adapter`). This abstraction is consumed by rv-agent for LLM-driven exploration and by other tools that need direct device interaction.

The `UIAdapter` abstract class defines 11 methods covering the fundamental device interactions needed for Android testing: `connect()`, `get_ui_state()`, `click()`, `input_text()`, `long_click()`, `swipe()`, `press_back()`, `press_home()`, `take_screenshot()`, `launch_app()`, `stop_app()`.

`UIAutomator2Adapter` implements this interface using the `uiautomator2` Python library (`import uiautomator2 as u2`). It wraps `u2.connect()` for device connection and delegates all operations to the device handle. Every operation is wrapped with `@ErrorHandler.handle_errors()` for consistent error management and `PerformanceMonitor.measure_time()` for execution timing.

The module also provides supporting utilities:
- **DeviceManager**: ADB-based device discovery (`adb devices`), connection verification, and device property retrieval.
- **ScreenshotManager**: Screenshot file path generation, image optimization (PNG to JPEG with quality control), validation, and cleanup of old files.
- **StateConverter**: Converts UIAutomator state to DroidBot-compatible format.
- **UIAutomatorActionExecutor**: Translates `GeneratedAction` objects to `UIAdapter` method calls.

Performance constants are tuned for headless mode execution: `ACTION_EXECUTION_DELAY=0.3s`, `TEXT_INPUT_DELAY=0.2s`, `DEFAULT_SWIPE_DURATION=0.25s`, `WAIT_FOR_IDLE_TIMEOUT=5.0s`.

#### Scenario: Connecting to an Android emulator

- **WHEN** `UIAutomator2Adapter.connect("emulator-5554")` is called
- **THEN** the adapter MUST call `u2.connect("emulator-5554")` and request `device.info`
- **AND** if `device.info` returns a non-None value, `connected` MUST be set to `True`
- **AND** `_configure_uiautomator_settings()` MUST be called to set `wait_timeout=5.0`
- **AND** the method MUST return `True`

- **WHEN** `u2.connect()` raises an exception
- **THEN** `connected` MUST remain `False`
- **AND** the method MUST return `False`
- **AND** the error MUST be logged

#### Scenario: Capturing UI state from device

- **WHEN** `get_ui_state()` is called on a connected adapter
- **THEN** the returned dictionary MUST contain keys `device_info`, `current_package`, `current_activity`, `xml`, `timestamp`
- **AND** `xml` MUST contain the UIAutomator XML hierarchy string from `device.dump_hierarchy()`
- **AND** `current_package` and `current_activity` MUST come from `device.app_current()`

- **WHEN** `get_ui_state()` is called on a disconnected adapter
- **THEN** the method MUST return an empty dictionary `{}`
- **AND** a warning MUST be logged

#### Scenario: Executing a click action via UIAutomatorActionExecutor

- **WHEN** `executor.execute(action, adapter)` is called with `action.action_type="click"` and `action.coordinates=[540, 1200]`
- **THEN** `adapter.click(540, 1200)` MUST be called
- **AND** the method MUST return `True` if the click succeeded

- **WHEN** `executor.execute(action, adapter)` is called with an action that has no coordinates
- **THEN** the executor MUST return `False`
- **AND** an error MUST be logged

#### Scenario: State format conversion

- **WHEN** `StateConverter.uiautomator_to_droidbot(ui_state)` is called with `ui_state={"xml": "<hierarchy>...</hierarchy>", "current_activity": ".MainActivity", "current_package": "com.example"}`
- **THEN** the result MUST contain `view_tree="<hierarchy>...</hierarchy>"`, `hierarchy="<hierarchy>...</hierarchy>"`, `activity=".MainActivity"`, `package_name="com.example"`
- **AND** `_conversion_metadata` MUST be present with `source_format="uiautomator"` and `target_format="droidbot"`

#### Scenario: Screen hash computation

- **WHEN** `StateConverter.compute_screen_hash(state)` is called with a state containing a hierarchy XML
- **THEN** the returned hash MUST be a 16-character hexadecimal string (SHA-256 truncated to `SCREEN_HASH_LENGTH`)
- **AND** calling the method twice with the same state MUST return the same hash

- **WHEN** the state has no hierarchy/XML but has activity and package
- **THEN** the hash MUST be computed from `"{package}/{activity}"`

#### Scenario: Device discovery via DeviceManager

- **WHEN** `DeviceManager.get_available_devices()` is called and `adb devices` lists `emulator-5554  device`
- **THEN** the result MUST include `"emulator-5554"`
- **AND** devices with status other than `"device"` (e.g., `"offline"`, `"unauthorized"`) MUST be excluded

---

## RVSmartTool (added by gh29-rvsmart)

### Requirement: RVSmartTool Registration

`RVSmartTool` SHALL be registered as an external tool via rv-platform's `__init__.py` (same pattern as rvagent). It SHALL be registered via `registry.register_tool_class(RVSmartTool)` with idempotency check (`is_tool_registered("rvsmart")`).

The tool spec SHALL be:
- `name`: "rvsmart"
- `description`: "Java agent running inside emulator via app_process"
- `url`: "https://github.com/PAMunb/rvsec"
- `version`: "1.0.0"
- `process_pattern`: "br.unb.cic.rvsmart"

#### Scenario: RVSmartTool auto-registration
- **WHEN** `rv_platform` is imported
- **THEN** `ToolRegistry.get_instance().is_tool_registered("rvsmart")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("rvsmart").name` SHALL be "rvsmart"

#### Scenario: Tool creation via factory
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="rvsmart", variant="mvp"))` is called
- **THEN** the factory SHALL return a configured `RVSmartTool` instance
- **AND** `tool.config["mode"]` SHALL be "pure_algorithm"
- **AND** `tool.config["throttle_ms"]` SHALL be 50

### Requirement: RVSmartTool Variants

`RVSmartTool` SHALL define 4 variants with a `"default"` variant (INV-TOOL-02):

| Variant | mode | throttle_ms | Notes |
|---------|------|-------------|-------|
| `default` | pure_algorithm | 50 | Same as mvp |
| `mvp` | pure_algorithm | 50 | Phase 1 target: ~12-16 evt/s |
| `fast` | pure_algorithm | 30 | Reduced throttle for maximum throughput |
| `hybrid` | multimode | 50 | LLM hybrid mode, requires SGLang |

The `hybrid` variant SHALL additionally include `llm_base_url: "http://10.0.2.2:30000/v1"` in its configuration.

#### Scenario: Variant resolution for hybrid mode
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="rvsmart", variant="hybrid"))` is called
- **THEN** `tool.config["mode"]` SHALL be "multimode"
- **AND** `tool.config["llm_base_url"]` SHALL be "http://10.0.2.2:30000/v1"

#### Scenario: Parameter override on variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="rvsmart", variant="mvp", parameters={"throttle_ms": 100}))` is called
- **THEN** `tool.config["throttle_ms"]` SHALL be 100 (parameter overrides variant default)

### Requirement: RVSmartTool Execution Contract

`RVSmartTool.execute_tool_specific_logic(task, app)` SHALL:
1. Resolve `rvsmart.jar` path via `JarResolver` (search paths in priority order: (a) `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/target/rvsmart.jar` — development Maven build, (b) `$TOOLS_DIR/rvsmart/rvsmart.jar` — manual placement, (c) `/opt/rv-android/tools/rvsmart/rvsmart.jar` — Docker image). First match wins.
2. Push `rvsmart.jar` to `/data/local/tmp/rvsmart.jar` via `adb push`.
3. If `task.static_data` is available and has a `json_path`, push the JSON to `/data/local/tmp/static_analysis.json`.
4. If configuration parameters require a properties file, generate `rvsmart.properties` and push to `/data/local/tmp/`.
5. Build the `adb shell` command: `adb -s <device_serial> shell CLASSPATH=/data/local/tmp/rvsmart.jar /system/bin/app_process /data/local/tmp/ br.unb.cic.rvsmart.Main --package <package_name> --timeout <timeout> [--static-data ...] [--config ...] [--mode ...]`.
6. Execute via `self._execute_and_check_command()` with stdout and stderr directed to `task.result.trace_file`.

Before full execution, `RVSmartTool` SHALL run a health check: `adb shell CLASSPATH=... app_process ... --health-check`. This validates ServiceManager connections and performs one UI capture to verify AccessibilityNodeInfo reflection, then exits with code 0 (success) or 1 (failure). If the health check fails, the tool SHALL log an error with the health check output and raise an exception.

Timeout behavior follows the standard `AbstractTool` contract: `RVCommandTimeoutError` is converted to `RVToolTimeoutError` by the base class. This is expected behavior (INV-TOOL-06).

#### Scenario: Health check passes
- **WHEN** `--health-check` exits with code 0
- **THEN** `RVSmartTool` SHALL proceed with full execution

#### Scenario: Health check fails
- **WHEN** `--health-check` exits with code 1
- **THEN** `RVSmartTool` SHALL log "rvsmart health check failed: <stderr output>"
- **AND** `RVSmartTool` SHALL NOT proceed with full execution
- **AND** the task SHALL be marked as failed with a clear error message

#### Scenario: Execution with static analysis data
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `task.static_data.json_path = "/results/exp1/instrumented_apks/cryptoapp/static_analysis.json"`
- **THEN** rvsmart.jar SHALL be pushed to `/data/local/tmp/rvsmart.jar`
- **AND** static_analysis.json SHALL be pushed to `/data/local/tmp/static_analysis.json`
- **AND** the adb shell command SHALL include `--static-data /data/local/tmp/static_analysis.json`
- **AND** `StaticMap` SHALL parse the JSON correctly as JsonArrays (INV-RSM-30, INV-RSM-31)
- **AND** `MopScorer` SHALL return non-zero scores for actions on screens whose methods have `directlyReachesMop=true`
- **AND** `WtgScorer` SHALL return non-zero scores for actions matching known transitions to unvisited activities

#### Scenario: Empty trace file detected
- **WHEN** execution completes and the trace file exists but has 0 bytes
- **THEN** `RVSmartTool` SHALL log a warning "rvsmart produced empty trace file — possible silent hang or startup crash"
- **AND** execution SHALL NOT be marked as failure (the agent ran for the full timeout)

#### Scenario: Execution without static analysis data
- **WHEN** `task.static_data` is None
- **THEN** the adb shell command SHALL NOT include `--static-data`
- **AND** rvsmart SHALL operate in heuristic mode (MopScorer/WtgScorer return 0)

#### Scenario: Timeout after configured duration
- **WHEN** the tool executes for the configured timeout (e.g., 300 seconds)
- **THEN** `RVCommandTimeoutError` SHALL be raised by the Command
- **AND** `AbstractTool.execute()` SHALL convert it to `RVToolTimeoutError`
- **AND** rv-platform SHALL treat this as success (INV-PLT-04)

### Requirement: RVSmartTool Metrics Extraction

After execution completes (timeout or otherwise), `RVSmartTool` SHALL extract the final metrics report from the trace file and write it to a separate file. The extraction logic searches for the last line starting with `RVSMART_METRICS:` in the trace file, parses the JSON payload, and writes it to `rvsmart_metrics.json` alongside the trace file in the task output directory.

Standard coverage metrics (`coverage_metrics` in `TaskResult`) are populated by rv-platform's `CoverageComponent` from logcat `RVSEC-COV` tags — same pipeline as all other tools. No changes to `TaskResult` model or `ResultProcessorComponent`. The `rvsmart_metrics.json` file contains rvsmart-specific operational metrics (throughput, multi-attempt stats, LLM stats) for Optuna calibration and post-processing scripts.

If the `RVSMART_METRICS:` line is not found (e.g., agent crashed before writing it), the tool SHALL log a warning and write a default metrics JSON. This is not a failure condition.

The metrics JSON payload SHALL include the following fields (in addition to existing fields preserved from gh30-gh32):

Within the `exploration` section (alongside `unique_states`, `unique_hashes`):
- `content_states`: integer — number of distinct content-hash states explored
- `structural_clusters`: integer — number of distinct structural-hash clusters
- `nav_map_edges`: integer — number of recorded structural navigation transitions
- `phase_distribution`: object — `{"phase1": N, "phase2": N, "phase3": N}` counting iterations spent in each phase

Within the `decisions` section (alongside `forced_backs`):
- `backtrack_replays`: integer — number of times RESTART+replay was used (BACK failure recovery)

Counter wiring in AgentLoop:
- `content_states`: read from `ContentGraph.size()` at metrics finalization
- `structural_clusters`: read from `StructuralGraph.size()` at metrics finalization
- `nav_map_edges`: read from `NavigationMap.size()` at metrics finalization
- `phase_distribution`: incremented in `AgentLoop.runIteration()` after `PhaseController.currentPhase()` returns
- `backtrack_replays`: incremented in `BacktrackStrategy` each time replay path is executed

#### Scenario: Metrics extraction from trace file
- **WHEN** the trace file contains a line `RVSMART_METRICS:{"metadata":{...},...}`
- **THEN** `RVSmartTool` SHALL parse the JSON after the prefix
- **AND** the parsed metrics SHALL be written to `rvsmart_metrics.json` in the task output directory

#### Scenario: Metrics JSON includes dual hash and phase data
- **WHEN** rvsmart completes execution with the redesigned algorithm
- **THEN** `RVSmartTool` SHALL extract `RVSMART_METRICS:` JSON from trace file
- **AND** the JSON SHALL contain `content_states` as an integer >= 1
- **AND** the JSON SHALL contain `structural_clusters` as an integer >= 1
- **AND** the JSON SHALL contain `phase_distribution` with keys `phase1`, `phase2`, `phase3`
- **AND** the JSON SHALL contain `backtrack_replays` as an integer >= 0

#### Scenario: Backward-compatible metrics fields preserved
- **WHEN** rvsmart completes execution
- **THEN** `RVSMART_METRICS:` JSON SHALL still contain all fields from gh30-gh32 metrics format (iterations, unique_screens, mop_hits, ooa_count, restart_count, avg_cycle_ms, etc.)
- **AND** `RVSmartTool` Python extraction logic SHALL require no changes

#### Scenario: Missing metrics line
- **WHEN** the trace file does not contain a `RVSMART_METRICS:` line
- **THEN** `RVSmartTool` SHALL log a warning "rvsmart metrics not found in trace file"
- **AND** `RVSmartTool` SHALL write a default metrics JSON to `rvsmart_metrics.json`:
  ```json
  {
    "metadata": {"tool": "rvsmart", "status": "metrics_unavailable", "reason": "RVSMART_METRICS line not found"},
    "exploration": {"iterations": 0, "unique_states": 0, "throughput_evt_per_s": 0},
    "decisions": {"total_actions": 0, "algorithm_actions": 0, "llm_actions": 0},
    "ui_coverage": {"unique_activities": 0, "unique_hashes": 0},
    "confirmed_coverage": {"enabled": false, "unique_methods": 0},
    "llm": {"total_calls": 0, "successful_calls": 0, "circuit_breaker_trips": 0}
  }
  ```
- **AND** execution SHALL NOT be marked as failure

---

## RVSmart Scoring and Recovery Fixes (added by gh32-rvsmart-scoring-recovery)

### Requirement: StaticMap JSON Parser Compatibility (FR18, FR19)

`StaticMap` SHALL correctly parse the JSON format produced by `RvsecAnalysisClient` (gh27). The JSON file contains three top-level keys, all of which are `JsonArray` values (not `JsonObject`). The parser was originally written expecting `JsonObject` values, causing `getAsJsonObject()` to return `null` silently — this made MopScorer and WtgScorer return 0 for all actions since gh29.

The parser MUST handle three aspects correctly:

1. **Format**: Read `"reachability"` and `"transitions"` as `JsonArray` via `getAsJsonArray()`.
2. **Activity name normalization**: Trace-format activity names (e.g., `"uiactivitiesSplashActivity"` — dots stripped from relative path) MUST be normalized to match fully-qualified names in the JSON (e.g., `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"`). The normalization reconstructs the fully-qualified name by prepending the code package and re-inserting dots at camelCase boundaries.
3. **Transitions data model**: The `"transitions"` section uses `{sourceId, targetId, events}` objects referencing window IDs from the `"windows"` section. The parser MUST cross-reference window IDs with activity names to build the activity-to-transitions adjacency map that `WtgScorer` reads.

#### Scenario: Reachability parsed from JsonArray
- **WHEN** `StaticMap` loads a JSON file where `"reachability"` is a JsonArray with 50 class entries
- **AND** class `"com.example.app.MainActivity"` has method `"<com.example.app.MainActivity: void onClick(View)>"` with `directlyReachesMop=true`
- **THEN** `getMopMethodsForActivity("MainActivity")` SHALL return a non-empty set containing that method signature
- **AND** `MopScorer.score()` SHALL return a positive value for CLICK actions on that activity's screen

#### Scenario: Transitions parsed from JsonArray
- **WHEN** `StaticMap` loads a JSON file where `"transitions"` is a JsonArray with `{sourceId: 1, targetId: 2, events: [{type: "implicit_launch_event"}]}`
- **AND** the `"windows"` section maps windowId=1 to `"com.example.app.MainActivity"` and windowId=2 to `"com.example.app.SettingsActivity"`
- **THEN** `getTransitions("MainActivity")` SHALL return transitions containing a path to `"SettingsActivity"`
- **AND** `WtgScorer.score()` SHALL return +200 for CLICK actions that match this transition when `"SettingsActivity"` is unvisited

#### Scenario: Activity name normalization
- **WHEN** the trace reports activity `"uiactivitiesSplashActivity"` and the code package is `"com.crazyhitty.chdev.ks.munch"`
- **THEN** `StaticMap` SHALL normalize the name to match against `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"` in the JSON
- **AND** MOP and WTG queries for that activity SHALL return correct results

### Requirement: Scoring Chain Composition (FR18, NFR01)

The rvsmart scoring chain SHALL consist of exactly 7 additive scorers, each contributing an independent score component that is summed to produce the total action score:

| # | Scorer | Contribution | Status |
|---|--------|-------------|--------|
| 1 | `MopScorer` | Boost for actions on screens with methods that reach monitored operations | Functional (requires StaticMap fix) |
| 2 | `WtgScorer` | Boost for actions matching static WTG transitions to unvisited activities (+200/+100/+50 by hop distance) | Functional (requires StaticMap fix) |
| 3 | `GradualDecayScorer` | 200→0 decay over 5 visits to penalize revisitation | Unchanged |
| 4 | `SystemElementFilter` | -5000 for system UI elements to prevent interaction | Unchanged |
| 5 | `ComponentPriorityScorer` | SET_TEXT=200, CLICK=100, SCROLL=25 to prioritize high-value action types | Unchanged |
| 6 | `ConfirmedCoverageScorer` | 150/(1+revisits) to boost screens with confirmed MOP coverage, decaying on revisits | Unchanged |
| 7 | `CoverageDensityScorer` | coverageGap * weight (default 100) to direct exploration toward screens with untested elements | Functional (requires UICoverageTracker ID fix — INV-RSM-39) |

The following are REMOVED (P3 — complete deletion, backed up to `backup/`):

- `RewardScorer` — accumulated rewards infinitely without bound, eventually dominating 96.8% of total score. With functional MOP and WTG scorers, the agent has real static analysis guidance and no longer needs reward accumulation.
- `RewardPropagator` — infrastructure supporting `RewardScorer`. All values were consumed only by the removed `RewardScorer`.

#### Scenario: Scoring with functional MOP and WTG data
- **WHEN** static analysis data is loaded and `MopScorer` has MOP method data for the current activity
- **AND** `WtgScorer` has transition data showing a 1-hop path to an unvisited activity via a CLICK action
- **THEN** the CLICK action's total score SHALL include: mop > 0, wtg = 200, decay (visit-dependent), component = 100, confirmed (coverage-dependent), system = 0
- **AND** the RewardScorer component SHALL NOT appear in the score breakdown

#### Scenario: Scoring without static analysis data
- **WHEN** no static analysis data is available (`StaticMap.isLoaded() == false`)
- **THEN** `MopScorer` SHALL return 0 for all actions
- **AND** `WtgScorer` SHALL return 0 for all actions
- **AND** scoring falls back to the 5 non-static scorers (GradualDecay, SystemElement, ComponentPriority, ConfirmedCoverage, CoverageDensity)

### Requirement: OOA Multi-Stage Recovery (FR19, NFR04)

When out-of-app is detected and `consecutiveOoaAfterRestart` reaches `MAX_CONSECUTIVE_OOA_AFTER_RESTART`, the agent SHALL execute a multi-stage recovery sequence:

1. Send `input keyevent BACK` via `adb shell` to dismiss modal activities
2. Wait 500ms and re-check foreground package
3. If still out-of-app, call `am force-stop <foregroundPackage>` to close the blocking app
4. Then proceed with the standard `forceStop(targetPackage) + startApp(targetPackage)`

#### Scenario: Modal activity blocking recovery
- **WHEN** the agent detects OOA with foreground package `"com.google.android.soundpicker"` for `MAX_CONSECUTIVE_OOA_AFTER_RESTART` consecutive attempts
- **THEN** the agent SHALL send `input keyevent BACK`
- **AND** if the foreground is still `"com.google.android.soundpicker"` after 500ms
- **THEN** the agent SHALL call `am force-stop com.google.android.soundpicker`
- **AND** then `forceStop(targetPackage)` and `startApp(targetPackage)`

#### Scenario: BACK dismisses the blocking activity
- **WHEN** the agent sends `input keyevent BACK` and the foreground returns to the target package
- **THEN** the agent SHALL NOT call `forceStop` on either package
- **AND** `consecutiveOoaAfterRestart` SHALL reset to 0

### Requirement: Empty Screen Wait Strategy (FR19, NFR01)

When `ActionSelector.generateCandidateActions()` produces 0 interactive candidates AND the current screen has no parent in the `SuccessorTracker` graph (indicating the agent cannot backtrack), the agent SHALL wait for a potential auto-transition before resorting to RESTART.

Many Android apps use splash screens that auto-transition to the main activity after 2-3 seconds via `Handler.postDelayed()`. Without waiting, the agent's RESTART (~1.2s cycle) relaunches the app before the transition completes, creating an infinite loop of splash screen restarts.

#### Scenario: Splash screen auto-transition
- **WHEN** the agent captures a screen with 0 interactive elements and no parents in the graph
- **THEN** the agent SHALL `Thread.sleep(2000)` and recapture the screen via `UiCapture.capture()`
- **AND** if the recaptured screen has interactive elements, the agent SHALL proceed with normal action selection
- **AND** if the recaptured screen still has 0 elements, the agent SHALL fall back to RESTART

### Requirement: Exception Visibility in Trace Output (FR19, NFR04)

When `runIteration()` throws an exception caught by the `run()` method's catch block, the agent SHALL write a trace line to stdout with `action_type="ERROR"` and the exception message. This ensures that failures are visible in the `.trace` file, which is the primary diagnostic artifact for rvsmart executions.

RVSmart runs via `app_process` without access to the device's logcat buffer from the Python plugin's stdout redirection. The `Log.w(TAG, ...)` call in the catch block writes to logcat, which is not captured — errors are silently lost without this fix.

#### Scenario: Exception produces trace line
- **WHEN** `runIteration()` throws `NullPointerException` at iteration 42
- **THEN** the agent SHALL write to stdout: `{"iteration":42, "action_type":"ERROR", "error":"NullPointerException: <message>", ...}`
- **AND** the agent SHALL continue to iteration 43

#### Scenario: Early return produces SKIP trace line
- **WHEN** `getRootInActiveWindow()` returns `null` at iteration 15
- **THEN** the agent SHALL write to stdout: `{"iteration":15, "action_type":"SKIP", "reason":"null_root", ...}`
- **AND** the agent SHALL continue to iteration 16

---

## RVSmart Coverage and Scoring (added by gh31-rvsmart-coverage-scoring)

### Requirement: Element-Level UI Coverage Tracking (FR18, NFR01)

RVSmart SHALL track UI element coverage at the per-screen, per-element level through `UICoverageTracker`. When the agent visits a screen, all interactive elements from the `UiCapture` result SHALL be registered with the tracker using hybrid IDs: `"res:{resource_id}"` when the element has a non-empty `resourceId`, otherwise `"coords:{centerX},{centerY}"`. After each action execution, the tracker SHALL record the interaction by incrementing the count for the targeted element.

The tracker provides two key capabilities to the exploration strategy:

1. **Coverage gap computation**: `getCoverageGap(screenHash)` returns the fraction of untested elements on a given screen, enabling `CoverageDensityScorer` to direct exploration toward screens with many untested elements. A screen with 20 elements where 5 have been tested has a coverage gap of 0.75.

2. **Element type tracking**: Each element's widget class (Button, EditText, ImageView, etc.) is recorded alongside its hybrid ID. This enables future per-type coverage statistics without a separate tracking mechanism.

The tracker is integrated into `AgentLoop`: elements are registered after `UiCapture.capture()`, and interactions are recorded after action execution. The tracker is NOT accessible from outside the agent — it is an internal decision-making component.

#### Scenario: Elements registered on first screen visit

- **WHEN** `AgentLoop` visits a screen with hash `"abc123def456"` for the first time
- **AND** `UiCapture.capture()` returns 15 interactive elements (8 Buttons, 4 EditTexts, 2 ImageViews, 1 CheckBox)
- **THEN** `UICoverageTracker.registerScreenElements("abc123def456", items)` SHALL register 15 elements
- **AND** each element SHALL have a hybrid ID: `"res:{resource_id}"` when resourceId is non-empty, otherwise `"coords:{centerX},{centerY}"`
- **AND** `getCoverageGap("abc123def456")` SHALL return 1.0 (no elements tested)

#### Scenario: Coverage gap decreases after interactions

- **WHEN** the agent has visited screen `"abc123def456"` which has 10 registered elements
- **AND** 3 elements have been interacted with (interactionCount > 0)
- **THEN** `getCoverageGap("abc123def456")` SHALL return 0.7

#### Scenario: Re-visiting a screen does not duplicate elements

- **WHEN** the agent visits screen `"abc123def456"` for the 3rd time
- **AND** the screen has the same 15 elements as the first visit
- **THEN** the element count for that screen SHALL remain 15 (not 45)
- **AND** interaction counts from previous visits SHALL be preserved

#### Scenario: CoverageDensityScorer uses real coverage data

- **WHEN** `CoverageDensityScorer.score(action, context)` is called
- **AND** `context.coverageGap` for the current screen is 0.8 (80% untested)
- **THEN** the scorer SHALL return `0.8 * weight` (where weight is configurable, default 100)
- **AND** actions on screens with lower coverage gap SHALL receive lower scores from this scorer

### Requirement: Plateau Detection and Adaptive Stochastic Boost (FR18, NFR01)

RVSmart SHALL detect exploration plateaus using a `PlateauDetector` with a sliding window of 10 iterations. A plateau occurs when the agent discovers no new screens AND triggers no new MOP coverage for 10 consecutive iterations — indicating the agent is stuck in a local optimum where deterministic action selection cycles through the same states.

When a plateau is detected, `ActionSelector` SHALL temporarily increase the stochastic selection probability from the configured default (0.15) to 0.5. This means 50% of actions during a plateau are selected with score-weighted randomness instead of the top-scored action, dramatically increasing the chance of escaping the local optimum. The probability reverts to the default as soon as a new state or new MOP coverage is observed.

The plateau detector is integrated into `AgentLoop`: after each iteration, the loop calls `plateauDetector.recordIteration(isNewState, hasNewMopCoverage)`. The detected plateau state is passed to `ActionSelector` via the scoring context.

#### Scenario: Plateau detected after 10 iterations without progress

- **WHEN** the agent completes 10 consecutive iterations
- **AND** none of those iterations discovered a new screen (all `afterHash` values were already in `DynamicStateGraph`)
- **AND** none of those iterations produced new MOP coverage from logcat
- **THEN** `PlateauDetector.isPlateauDetected()` SHALL return `true`
- **AND** `ActionSelector` SHALL use stochastic probability 0.5

#### Scenario: Plateau clears on new state discovery

- **WHEN** `PlateauDetector.isPlateauDetected()` returns `true`
- **AND** the agent discovers a new screen (hash not in `DynamicStateGraph`)
- **THEN** `PlateauDetector.isPlateauDetected()` SHALL return `false` on the next call
- **AND** `ActionSelector` SHALL revert to the configured stochastic probability (default 0.15)

#### Scenario: No plateau when progress is ongoing

- **WHEN** the agent discovers at least one new screen within any 10-iteration window
- **THEN** `PlateauDetector.isPlateauDetected()` SHALL return `false`

### Requirement: Context-Aware Text Input Generation (FR18)

RVSmart SHALL generate context-appropriate text input values using `InputValueGenerator` instead of the hardcoded string `"test"`. The generator SHALL examine the target widget's `hint`, `resource_id`, and `inputType` attributes to determine the appropriate input category, then select a value from a pre-defined list for that category.

Input categories and their value lists:

| Category | Detection Heuristic | Values |
|----------|-------------------|--------|
| Email | hint/resource_id contains "email" or "mail" | `"test@test.com"`, `"user@example.org"`, `"a@b.c"` |
| Password | hint/resource_id contains "password" or "pass" | `"Test1234!"`, `"password123"`, `"Aa1!aaaa"` |
| Number | inputType is `TYPE_CLASS_NUMBER` or hint contains "number", "amount", "age" | `"42"`, `"0"`, `"999"` |
| Phone | inputType is `TYPE_CLASS_PHONE` or hint contains "phone", "tel" | `"+5561999999999"`, `"123456789"` |
| URL | hint/resource_id contains "url" or "website" | `"https://example.com"`, `"http://test.org"` |
| Generic | No pattern matched | `"test"`, `""`, `"a very long text string for testing"`, `"12345"` |

The generator tracks which values have been used for each element (by hybrid ID) and rotates through the list to maximize input diversity.

#### Scenario: Email field detected by hint

- **WHEN** `InputValueGenerator.generateInput(item)` is called
- **AND** `item.getHint()` returns `"Enter your email"`
- **THEN** the generator SHALL return a value from the Email category (e.g., `"test@test.com"`)
- **AND** the value SHALL NOT be one already used for this element in this run

#### Scenario: Password field detected by resource ID

- **WHEN** `InputValueGenerator.generateInput(item)` is called
- **AND** `item.getResourceId()` returns `"com.example:id/password_input"`
- **THEN** the generator SHALL return a value from the Password category

#### Scenario: Generic fallback when no pattern matches

- **WHEN** `InputValueGenerator.generateInput(item)` is called
- **AND** `item.getHint()` is null, `item.getResourceId()` is `"com.example:id/field1"`, `item.getInputType()` is 0
- **THEN** the generator SHALL return a value from the Generic category

#### Scenario: Value rotation for repeated interactions

- **WHEN** the agent interacts with the same EditText element 4 times
- **AND** the element is categorized as Generic (4 values available)
- **THEN** the first 4 interactions SHALL use 4 different values
- **AND** the 5th interaction SHALL cycle back to the first value

### Requirement: WTG-Based Transition Scoring (FR18, NFR01)

`WtgScorer` SHALL use the `transitions` section of the static analysis JSON to boost actions that correspond to known window transitions leading to unvisited or under-visited activities. This enables the agent to prioritize actions that are statically known to navigate to unexplored parts of the application.

The `transitions` section of the JSON maps source activities to lists of `{target_activity, widget_event}` objects. `StaticMap` (fixed in gh30 to support activity-based queries) SHALL expose `getTransitions(activityName)` returning the list of known transitions from the given activity.

For each candidate CLICK or LONG_CLICK action, `WtgScorer` performs BFS of depth 3 on the transitions graph, matching the action's widget resource ID and event type (click, long_click) against known transitions. The score uses diminishing boost based on BFS hop depth:

- +200 if the action's widget matches a 1-hop transition to an unvisited activity (visit count 0)
- +100 if the action's widget matches a 1-hop transition to an activity that is 2-hops away from an unvisited activity
- +50 if the action's widget matches a 1-hop transition to an activity that is 3-hops away from an unvisited activity, OR any-hop transition to an under-visited activity (visit count < 3)
- 0 if no transition match found, no static data, or action type is SCROLL/BACK/RESTART/SET_TEXT

BFS tracks visited nodes to handle cycles in the transitions graph.

#### Scenario: 1-hop to unvisited activity (+200)

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** `context.currentActivity` is `"com.example.MainActivity"`
- **AND** `StaticMap.getTransitions("com.example.MainActivity")` returns `[{target: "com.example.SettingsActivity", widget: "btn_settings", event: "click"}]`
- **AND** the action's target widget has resource_id `"com.example:id/btn_settings"` and type CLICK
- **AND** `"com.example.SettingsActivity"` has visit count 0 in the graph
- **THEN** `WtgScorer` SHALL return 200

#### Scenario: 2-hop to unvisited activity (+100)

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** `context.currentActivity` is `"com.example.MainActivity"`
- **AND** the action's widget matches a transition to `"com.example.SettingsActivity"` (1-hop, already visited)
- **AND** `StaticMap.getTransitions("com.example.SettingsActivity")` contains a transition to `"com.example.DetailActivity"` (2-hop from current)
- **AND** `"com.example.DetailActivity"` has visit count 0 in the graph
- **THEN** `WtgScorer` SHALL return 100

#### Scenario: Under-visited activity (+50)

- **WHEN** the same conditions as the 1-hop scenario apply, but `"com.example.SettingsActivity"` has visit count 2 (under-visited, < 3)
- **THEN** `WtgScorer` SHALL return 50

#### Scenario: No static analysis data available

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** `StaticMap` has no data (rvsmart running in heuristic mode)
- **THEN** `WtgScorer` SHALL return 0

#### Scenario: Non-widget actions return 0

- **WHEN** `WtgScorer.score(action, context)` is called
- **AND** the action type is SCROLL, BACK, RESTART, or SET_TEXT
- **THEN** `WtgScorer` SHALL return 0 (WTG transitions only describe widget-triggered navigation)

### Requirement: Scoring Parameter Tuning (FR18)

RVSmart SHALL use updated default scoring parameters that improve action selection quality based on analysis from 5 independent LLMs and comparison with APE/FastBot behavior.

Changes from gh29 defaults:

| Parameter | Old Value | New Value | Rationale |
|-----------|-----------|-----------|-----------|
| BACK base score | -500 | -100 | At -500, BACK is 13x less attractive than average CLICK (~100), preventing voluntary backtracking |
| Proactive backtrack trigger | Score-based (`bestScore < 50`) | Saturation-based (`getSaturationRate() >= 0.8`) | Score-based threshold is fragile — adding/removing scorers shifts score range, requiring re-tuning. Saturation is self-calibrating: depends only on how many actions have been tried on the current screen |
| Stochastic selection | Uniform random | Softmax-weighted (temperature=50) | Uniform ignores scores entirely; softmax prefers higher-scored actions while maintaining exploration |
| maxRetriesPerCycle | 1 | 3 | Retry costs ~250ms vs ~500ms for a new cycle; more retries reduces wasted cycles |

The softmax-weighted stochastic selection computes `p(a) = exp(score(a) / temperature) / sum(exp(scores / temperature))` and samples from this distribution. Temperature=50 gives gentle preference to higher-scored actions. When all scores are equal, softmax degenerates to uniform random (same behavior as before).

#### Scenario: BACK action is selectable when forward options are poor

- **WHEN** the current screen has 5 candidate actions
- **AND** 4 CLICK actions have scores of 80, 70, 60, 50 (all tested, low priority)
- **AND** 1 BACK action has score -100 + context bonuses
- **THEN** BACK SHALL be selectable via stochastic selection with non-negligible probability
- **AND** BACK SHALL NOT be the top-scored action unless forward options score below -100

#### Scenario: Saturation-based proactive backtrack activates

- **WHEN** `screenNode.getSaturationRate()` returns 0.85 (85% of actions tried)
- **AND** the saturation threshold is 0.8
- **THEN** Tier 3 (proactive backtrack) SHALL activate because 0.85 >= 0.8
- **AND** the agent SHALL attempt to backtrack to a screen with lower saturation and untested actions

#### Scenario: Softmax-weighted selection preserves exploration

- **WHEN** stochastic selection triggers (15% probability, or 50% during plateau)
- **AND** candidate actions have scores [300, 200, 100, 50]
- **THEN** the selection SHALL use softmax with temperature=50
- **AND** the action with score 300 SHALL have the highest selection probability
- **AND** the action with score 50 SHALL have non-zero selection probability

### Requirement: Time-Based Stuck Detection (FR18)

RVSmart SHALL detect stuck states using both iteration count and wall-clock time. The existing `StuckDetector` uses consecutive unchanged screen hashes to detect stuck states. This change adds a secondary time-based trigger: if no new screen has been discovered for 30 seconds of wall-clock time (regardless of iteration count), the agent SHALL trigger stuck recovery.

Time-based detection addresses a gap in the current design where slow iterations (LLM calls, long adaptive waits) reduce the iteration count but not the actual time spent stuck. An agent stuck for 30 seconds in LLM mode may have only completed 3 iterations (below the iteration threshold) while an agent in pure_algorithm mode would have completed 30+ iterations.

#### Scenario: Time-based stuck detection triggers

- **WHEN** the agent has been executing for 30 seconds since the last new screen discovery
- **AND** the iteration-based stuck detector has NOT triggered (fewer than `stuckMaxBlocks` consecutive unchanged hashes)
- **THEN** the time-based stuck detection SHALL trigger recovery
- **AND** the recovery mechanism SHALL be the same as iteration-based stuck recovery

#### Scenario: Time-based threshold resets on new screen

- **WHEN** the agent discovers a new screen (hash not previously in `DynamicStateGraph`)
- **THEN** the time-based stuck timer SHALL reset to 0

### Requirement: Element-Level Package Filtering (FR18)

`ActionSelector.generateCandidateActions()` SHALL pre-filter elements whose `packageName` matches `com.android.systemui`. These are system UI elements (notification bar, status bar widgets) that appear within the app's foreground window but do not belong to the app under test. Elements with null or empty `packageName` SHALL NOT be filtered — they are framework widgets rendered by the app and may be interactive.

#### Scenario: System UI elements excluded from candidates

- **WHEN** `generateCandidateActions()` processes elements on a screen
- **AND** 2 elements have `packageName == "com.android.systemui"` (notification icons)
- **AND** 12 elements have `packageName == "com.example.app"` (app widgets)
- **AND** 3 elements have `packageName == null` (framework widgets)
- **THEN** the candidate list SHALL contain 15 actions (12 + 3), not 17
- **AND** the 2 system UI elements SHALL be excluded before scoring

### Requirement: LLM Coordinate Boundary Protection (FR18)

When executing LLM-generated actions in hybrid/multimode, `AgentLoop` SHALL validate that click coordinates are not in the status bar (top 5% of screen height) or navigation bar (bottom 6% of screen height). If the coordinates fall in these regions, the action SHALL be replaced with a BACK action. This prevents the LLM from accidentally tapping system UI elements that navigate away from the app.

#### Scenario: LLM tap in status bar rejected

- **WHEN** the agent executes an LLM-generated CLICK action
- **AND** the click y-coordinate is 40 (screen height 1920, top 5% = y < 96)
- **THEN** the CLICK SHALL be replaced with a BACK action
- **AND** RVTRACK SHALL log `llm_boundary_reject` with the original coordinates

#### Scenario: LLM tap in app area accepted

- **WHEN** the agent executes an LLM-generated CLICK action
- **AND** the click y-coordinate is 960 (middle of screen)
- **THEN** the CLICK SHALL be executed as-is

### Requirement: ApeRVTool External Registration (FR18, FR19, NFR02)

`_register_external_tools()` in `rv_platform/__init__.py` SHALL include an idempotent registration block for `ApeRVTool`, placed after the `RVSmartTool` registration block. The structure MUST follow the same pattern as the existing `RVSmartTool` block: check `is_tool_registered("aperv")`, attempt `from aperv_tool.tools.aperv.tool import ApeRVTool`, catch `ImportError` as warning and any other exception as error. This registration makes `aperv` available to `ToolFactory` and `ToolRegistry` whenever `rv_platform` is imported and `aperv-tool` is installed.

#### Scenario: aperv registered alongside rvsmart
- **WHEN** `import rv_platform` is executed and both `rvsmart-tool` and `aperv-tool` are installed
- **THEN** both `"rvsmart"` and `"aperv"` SHALL be registered in `ToolRegistry`
- **AND** `ToolRegistry.get_instance().list_tools()` SHALL contain both `"rvsmart"` and `"aperv"`

#### Scenario: aperv registration isolated from rvsmart registration
- **WHEN** `aperv-tool` raises `ImportError` during registration
- **THEN** `"rvsmart"` SHALL still be registered and functional
- **AND** `"aperv"` SHALL NOT appear in `ToolRegistry`
