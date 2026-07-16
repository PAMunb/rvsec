# Specification: ApeRV Tool

## Purpose

`aperv-tool` is an rv-platform external tool module that wraps the APE-RV binary (`ape-rv.jar`) for integration into the rv-android experiment framework. APE-RV is an enhanced fork of APE (Ape Explores Apps, ICSE 2019), a model-based Android UI exploration tool that uses adaptive random testing with a Widget Table Graph model. The enhanced version adds AndroidX ViewPager support, systematic OptionsMenu exploration (`MODEL_MENU` action), optional MOP-guided action scoring from static analysis data, optional LLM-guided action selection via an SGLang server, and probabilistic component triggering for Services and BroadcastReceivers.

The tool runs on the Android device using the `app_process` execution model. The JAR is pushed to `/data/local/tmp/ape-rv.jar` via ADB, and execution is launched via `adb shell CLASSPATH=... /system/bin/app_process /system/bin com.android.commands.monkey.Monkey`. This execution model is necessary because APE requires internal Android APIs (`android.app.UiAutomationConnection`, `android.hardware.display.DisplayManagerGlobal`) that are inaccessible from the host via `adb shell monkey`.

The module is an optional uv workspace member, auto-discovered by `members = ["modules/*"]` in the root `pyproject.toml`. If not installed, rv-platform's `_register_external_tools()` catches the `ImportError` and logs a warning, allowing the platform to function normally with other tools.

Coverage metrics (method calls, MOP violations) are collected by the rv-android Python infrastructure via logcat `RVSEC-COV` tags -- the same pipeline used by all other tools. No special output parsing is required.

### APE-RV Java Capabilities

The `ape-rv.jar` binary supports several capabilities that `aperv-tool` configures via `ape.properties`:

1. **MOP-Guided Scoring**: When `ape.mopDataPath` points to a static analysis JSON on the device, APE-RV loads widget-to-MOP mappings and applies priority boosts (+500 direct, +300 transitive, +100 activity-level) to actions whose handlers reach monitored operations. This biases exploration toward code paths under runtime verification.

2. **LLM-Guided Action Selection**: When `ape.llmUrl` points to an SGLang server, APE-RV captures screenshots and consults a vision-language model (Qwen3-VL) at two decision points: (a) first visit to a new state (`llmOnNewState`), and (b) stagnation midpoint (`llmOnStagnation`). A probabilistic mode (`llmPercentage`) routes a configurable fraction of steps through the LLM. A circuit breaker (3 failures, 60s recovery) protects the exploration loop from cascading LLM failures. All LLM failures fall back to SATA transparently.

3. **Component Triggering**: When MOP data includes a `components{}` section with receivers and services, APE-RV probabilistically fires broadcast intents and starts services during exploration. A `system-broadcast.json` catalog provides typed extras for known system broadcast actions.

4. **Prompt Variants**: The `llm_prompt_variant` property selects which prompt template APE-RV uses for LLM calls (e.g., `ape_current`, `ape_reasoning`, `compact_v1`, `v13`, `v17`, `visual_only`), enabling controlled prompt ablation experiments.

### Relationship with Other Domains

- **rv-platform**: Consumes `ApeRVTool` via `ToolFactory.create_tool()` in `ToolExecutionComponent`. Registration via `_register_external_tools()`.
- **rv-experiment**: Orchestrates experiments using `aperv` tool variants. APK instrumentation and static analysis happen in pre-processing; `aperv-tool` receives the instrumented APK already installed on the emulator.
- **rv-static-analysis**: Produces the static analysis JSON consumed by MOP variants. The JSON maps activities to widgets with MOP reachability flags and includes component data for triggering.
- **rv-tools**: Provides `AbstractTool` base class, `ToolSpec`, `ToolRegistry`, and `ToolFactory` infrastructure.
- **builtin ape tool**: Shares `process_pattern` (`com.android.commands.monkey`). The two tools must not run concurrently on the same device.

## Data Contracts

### Input

- `task.config.device_id: str` -- ADB device serial (default `"emulator-5554"`)
- `task.config.timeout: int` -- exploration duration in seconds (default 300)
- `task.result.trace_file: str` -- path where stdout/stderr from APE-RV is written
- `task.results_dir: str` -- directory containing static analysis JSON (for MOP variants)
- `task.config.apk_name: str` -- APK filename used to locate the static analysis JSON
- `app.package_name: str` -- Android package name passed to APE's `-p` flag
- `self._tool_config: Dict[str, Any]` -- resolved variant configuration from `configure()`
- `ape-rv.jar` -- Dalvik JAR resolved at execution time via priority search
- `system-broadcast.json` -- optional broadcast catalog file shipped alongside the tool module

### Output

- `task.result.trace_file` -- populated with APE-RV stdout+stderr (binary write mode)

### Side-Effects

- **[Device]**: `ape-rv.jar` pushed to `/data/local/tmp/ape-rv.jar`
- **[Device]**: `system-broadcast.json` pushed to `/data/local/tmp/system-broadcast.json` (if file exists in module directory)
- **[Device]**: `/data/local/tmp/static_analysis.json` receives the compacted static analysis document (or the source document, on fallback) -- MOP variants only, when the file is found
- **[Filesystem]**: on the success path, a temporary file holding the compacted document is created and unlinked after the push completes
- **[Filesystem]**: on the fallback path, any temporary file created before the failure is unlinked by the compaction function before it returns, so no temporary file exists at push time
- **[Filesystem]**: `<task.results_dir>/<task.config.apk_name>.json` is read and never written
- **[Device]**: `ape.properties` pushed to `/data/local/tmp/ape.properties` (when `_tool_config` is non-empty)
- **[Logcat]**: APE-RV writes `RVSEC-COV` log lines during execution (read by rv-android coverage infrastructure)
- **[Network]**: LLM variants send HTTP requests from the emulator to the SGLang server (via `10.0.2.2` loopback or overridden URL)

### Error

- `ConfigurationError` -- raised by `configure()` when `strategy` key is absent or not in `["sata", "random", "bfs", "dfs"]`
- `RVToolExecutionError` -- raised when `ape-rv.jar` cannot be found in any search path, or when an ADB push fails
- `RVToolTimeoutError` -- raised when execution exceeds `task.config.timeout + 15` seconds (expected normal exit for exploration tools)

## Invariants

- **INV-APV-01**: `ApeRVTool` SHALL locate `ape-rv.jar` using `JarResolver` with search paths in priority order: (a) `os.path.dirname(__file__)` -- module directory populated by `mvn install`, (b) `$RVSEC_HOME/ape/target/` -- development Maven build, (c) `$TOOLS_DIR/aperv/` -- manual placement. First match wins. If no path resolves, a `RVToolExecutionError` SHALL be raised listing all searched paths.

- **INV-APV-02**: `ApeRVTool.configure()` SHALL validate that the `strategy` key exists in `config` and its value is one of `["sata", "random", "bfs", "dfs"]`. An absent or invalid strategy SHALL raise `ConfigurationError` before any device interaction.

- **INV-APV-03**: `ApeRVTool` SHALL use device path `/data/local/tmp/ape-rv.jar` (not `/data/local/tmp/ape.jar`) to avoid collision with the builtin `ape` tool's device artifact.

- **INV-APV-04**: The `app_process` working directory SHALL be `/system/bin` (not `/data/local/tmp/`). The enhanced APE binary references system-level resources relative to its working directory during startup; using `/data/local/tmp/` causes startup failures. This intentionally diverges from the builtin `ape` tool, which uses `/data/local/tmp/` as working directory.

- **INV-APV-05**: `get_variants()` SHALL return a dict containing at minimum the keys `["default", "sata", "sata_mop", "bfs", "random", "sata_llm", "sata_mop_llm"]` plus the prompt variant experiment variants (`sata_mop_llm_<prompt>`). The `"default"` key SHALL map to the `sata` strategy (INV-TOOL-02 compliance).

- **INV-APV-06**: The `sata_mop` variant SHALL set `mop_data` to `"static_analysis"`. When `mop_data == "static_analysis"`, `execute_tool_specific_logic()` SHALL locate the static analysis JSON, compact it (INV-APV-21), and push the compacted document to the device; when compaction fails, the source document SHALL be pushed instead (INV-APV-24). If the JSON is not found, execution SHALL continue without MOP data (graceful degradation).

- **INV-APV-07**: `ApeRVTool.TOOL_SPEC.process_pattern` SHALL be `"com.android.commands.monkey"`. This is the same value used by the builtin `ape` tool. `AbstractTool.kill_related_processes()` uses this pattern to terminate device-side processes after execution. As a consequence, `ape` and `aperv` MUST NOT run concurrently on the same device -- each cleanup would terminate the other's process. Experiments using `aperv` SHALL NOT include the builtin `ape` tool in the same run.

- **INV-APV-08**: `ape.properties` generation SHALL use `APERV_PROPERTY_MAPPING` to translate Python config keys to Java property names. Only keys present in both `_tool_config` and `APERV_PROPERTY_MAPPING` are written. Python-only keys (`strategy`, `mop_data`) have no mapping entry and are excluded automatically.

- **INV-APV-09**: LLM variants SHALL use `http://10.0.2.2:30000/v1` as the default `llm_url`. The `10.0.2.2` address is the Android emulator's alias for the host loopback interface. The `APERV_LLM_BASE_URL` environment variable SHALL override this value in `configure()` when set, allowing Docker or non-emulator setups to specify a different endpoint.

- **INV-APV-10**: The `system-broadcast.json` catalog file SHALL be pushed to the device when present in the module directory (`os.path.dirname(__file__)`). When absent, APE-RV degrades gracefully (component triggering proceeds without typed extras for system broadcasts).

- **INV-APV-11**: Timeout is ALWAYS controlled by `task.config.timeout` (set by rv-platform). The `running_minutes` passed to APE is derived from `max(1, task.config.timeout // 60)`. Variants MUST NOT hardcode a timeout.

- **INV-APV-12**: Non-zero exit codes from APE-RV SHALL NOT be treated as failures. APE-RV exits with non-zero codes when it detects app crashes during exploration (e.g., exit code 211). Coverage is collected via logcat regardless. Only `RVCommandTimeoutError` is re-raised as `RVToolTimeoutError`.

- **INV-APV-20**: Compaction SHALL write to a temporary file. The source file at `<task.results_dir>/<task.config.apk_name>.json` SHALL remain byte-identical after `execute_tool_specific_logic()` returns. This file is an archived experiment artifact: offline consolidation and `ResultProcessorComponent._resolve_static_data` re-parse it on resume. Keeping it byte-identical to the producer's output preserves it as ground truth rather than a derived artifact, and confines this change to the device-push path.

- **INV-APV-21**: Compaction SHALL be lossless. It SHALL consist of exactly two operations: (a) removing exact-duplicate entries from `transitions`, and (b) serializing without pretty-print whitespace. Every top-level key present in the source document (`package`, `mainActivity`, `components`, `reachability`, `windows`, `transitions`, `complete`) SHALL be present in the compacted document. No field SHALL be projected away, renamed, or rewritten.

- **INV-APV-22**: Deduplication of `transitions` SHALL preserve the order of first occurrence. `rekeyDialogsToHost` (`MopData.java:884`) resolves the first inbound edge and breaks, making edge order semantically load-bearing even though edge multiplicity is not.

- **INV-APV-23**: Compaction SHALL run unconditionally on every MOP-arm push, with no size threshold gating it.

- **INV-APV-24**: Any failure during compaction SHALL be caught, SHALL log a warning, and SHALL fall back to pushing the source file unchanged. Compaction SHALL NOT raise, and SHALL NOT be a task-failure path. The fallback preserves the pre-change behavior as a floor.

- **INV-APV-25**: No temporary file SHALL survive `execute_tool_specific_logic()`, on either the success or the fallback path.

## Requirements

### Requirement: ApeRVTool Registration (FR18, FR19)

`ApeRVTool` SHALL be registered as an external tool via rv-platform's `_register_external_tools()` function in `rv_platform/__init__.py`. Registration SHALL be idempotent: the function MUST check `registry.is_tool_registered("aperv")` before calling `registry.register_tool_class(ApeRVTool)`. If `aperv-tool` is not installed, the resulting `ImportError` SHALL be caught and logged as a warning; the platform SHALL continue operating normally. An unexpected exception during registration SHALL be logged as an error and SHALL NOT propagate.

#### Scenario: ApeRVTool registers on rv-platform import
- **WHEN** `import rv_platform` is executed and `aperv-tool` is installed
- **THEN** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("aperv").name` SHALL be `"aperv"`

#### Scenario: Missing aperv-tool does not break rv-platform
- **WHEN** `import rv_platform` is executed and `aperv-tool` is NOT installed
- **THEN** rv-platform SHALL import successfully
- **AND** a warning log line SHALL be written containing `"aperv tool not available"`
- **AND** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return False

#### Scenario: Re-importing rv-platform does not double-register
- **WHEN** `import rv_platform` is executed twice
- **THEN** `ToolRegistry.get_instance()` SHALL contain exactly one registration for `"aperv"`

---

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define named variants organized in three tiers: base variants, LLM variants, and prompt experiment variants. Every variant SHALL include a `"strategy"` key and a `"throttle_ms"` key. The `"default"` variant SHALL use strategy `"sata"` (INV-TOOL-02).

#### Base Variants

| Variant | strategy | throttle_ms | mop_data | Notes |
|---------|----------|-------------|----------|-------|
| `default` | `"sata"` | 200 | -- | Alias for sata |
| `sata` | `"sata"` | 200 | -- | SATA adaptive random (primary strategy) |
| `sata_mop` | `"sata"` | 200 | `"static_analysis"` | SATA + MOP-guided scoring |
| `bfs` | `"bfs"` | 200 | -- | Breadth-first traversal |
| `random` | `"random"` | 200 | -- | Priority-weighted random baseline |

#### LLM Variants

LLM variants add LLM-guided action selection via an SGLang server. The `llm_url` uses `http://10.0.2.2:30000/v1` (emulator host loopback), overridable via `APERV_LLM_BASE_URL` environment variable.

| Variant | strategy | mop_data | llm_url | llm_on_new_state | llm_on_stagnation | Notes |
|---------|----------|----------|---------|------------------|-------------------|-------|
| `sata_llm` | `"sata"` | -- | `http://10.0.2.2:30000/v1` | `"true"` | `"true"` | SATA + LLM (no MOP) |
| `sata_mop_llm` | `"sata"` | `"static_analysis"` | `http://10.0.2.2:30000/v1` | `"true"` | `"true"` | SATA + MOP + LLM |

LLM variants also include sampling parameters: `llm_model="default"`, `llm_temperature=0.3`, `llm_top_p=0.6`, `llm_top_k=50`, `llm_timeout_ms=15000`.

#### Prompt Experiment Variants

Six variants for controlled prompt ablation experiments. All use SATA + MOP + LLM with `llm_percentage=0.7` (70% of steps routed to LLM). They differ only in `llm_prompt_variant`:

| Variant | llm_prompt_variant |
|---------|--------------------|
| `sata_mop_llm_ape_current` | `ape_current` |
| `sata_mop_llm_ape_reasoning` | `ape_reasoning` |
| `sata_mop_llm_compact_v1` | `compact_v1` |
| `sata_mop_llm_v13` | `v13` |
| `sata_mop_llm_v17` | `v17` |
| `sata_mop_llm_visual_only` | `visual_only` |

#### Scenario: Creating tool with sata variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["strategy"]` SHALL equal `"sata"`

#### Scenario: Creating tool with sata_mop variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata_mop"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["mop_data"]` SHALL be `"static_analysis"`

#### Scenario: Creating tool with sata_llm variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata_llm"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["llm_url"]` SHALL equal `"http://10.0.2.2:30000/v1"`
- **AND** `tool._tool_config["llm_on_new_state"]` SHALL equal `"true"`

#### Scenario: Creating tool with prompt experiment variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata_mop_llm_v13"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["llm_prompt_variant"]` SHALL equal `"v13"`
- **AND** `tool._tool_config["llm_percentage"]` SHALL equal `0.7`

---

### Requirement: ApeRVTool Configuration (FR19)

`ApeRVTool.configure(config)` SHALL store the resolved variant configuration in `self._tool_config` after validation. It SHALL validate that `config["strategy"]` is one of `["sata", "random", "bfs", "dfs"]`. If absent or invalid, it SHALL raise `ConfigurationError` before any device interaction.

When the `APERV_LLM_BASE_URL` environment variable is set and `llm_url` is present in the config, the environment variable value SHALL override the config value. This allows operators to redirect LLM traffic without modifying variant definitions.

#### Scenario: Valid strategy configured
- **WHEN** `configure({"strategy": "sata", "throttle_ms": 200})` is called
- **THEN** `self._tool_config["strategy"]` SHALL equal `"sata"`
- **AND** no exception SHALL be raised

#### Scenario: Invalid strategy raises ConfigurationError
- **WHEN** `configure({"strategy": "unknown"})` is called
- **THEN** `ConfigurationError` SHALL be raised with a message listing valid strategies

#### Scenario: LLM URL override via environment variable
- **WHEN** `configure({"strategy": "sata", "llm_url": "http://10.0.2.2:30000/v1"})` is called
- **AND** the `APERV_LLM_BASE_URL` environment variable is set to `"http://192.168.1.100:30000/v1"`
- **THEN** `self._tool_config["llm_url"]` SHALL equal `"http://192.168.1.100:30000/v1"`

---

### Requirement: JAR Resolution (FR19)

`ApeRVTool._resolve_jar_path()` SHALL use `JarResolver.resolve_jar_path("ape-rv.jar", search_paths)` where `search_paths` is built as follows:

1. Always include `os.path.dirname(__file__)` (the module directory)
2. If `RVSEC_HOME` env var is set, append `$RVSEC_HOME/ape/target/`
3. If `TOOLS_DIR` env var is set, append `$TOOLS_DIR/aperv/`

The first existing path that contains `ape-rv.jar` wins. If no path resolves, `RVToolExecutionError` SHALL be raised with a message listing all searched paths.

#### Scenario: JAR found in module directory
- **WHEN** `ape-rv.jar` exists in `os.path.dirname(__file__)`
- **THEN** `_resolve_jar_path()` SHALL return the absolute path to that file

#### Scenario: JAR not found anywhere
- **WHEN** `ape-rv.jar` does not exist in any search path
- **THEN** `_resolve_jar_path()` SHALL raise `RVToolExecutionError`
- **AND** the error message SHALL list all searched paths

---

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Compact and push static analysis JSON** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json` via `_find_static_analysis_file(task)`. If found, compact it into a temporary file (deduplicate `transitions`, serialize without pretty-print whitespace -- see "Static Analysis JSON Compaction"), push the compacted file to `/data/local/tmp/static_analysis.json`, unlink the temporary file, and set `mop_json_pushed = True`. If compaction fails, log a warning and push the source file unchanged, still setting `mop_json_pushed = True`. If the JSON is not found, log a warning and continue without MOP data.

5. **Push ape.properties**: Generate `ape.properties` from `_tool_config` using `APERV_PROPERTY_MAPPING` to translate Python keys to Java property names. When `mop_json_pushed` is True, include `ape.mopDataPath=/data/local/tmp/static_analysis.json`. Push to `/data/local/tmp/ape.properties`.

6. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. Command timeout is `timeout_seconds + 15` seconds.

7. **Handle timeout**: If `RVCommandTimeoutError` is raised, re-raise as `RVToolTimeoutError` (timeout is the expected exit path for exploration tools).

8. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty.

The `app_process` invocation SHALL use:
```
adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey -p <package_name>
  --running-minutes <max(1, timeout_seconds // 60)>
  --ape <strategy>
  [-s <seed>]
```

The trailing `-s <seed>` is appended only when a seed is configured (`tool.py:765-771`). The seed argument itself is owned by change `gh74-aperv-arm-variants` (INV-APV-18), which is implemented in code but whose delta is not yet synced; it is reproduced here so this spec does not freeze the seedless form as the contract.

#### Scenario: Successful APE-RV execution with sata variant
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `strategy="sata"`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout+stderr SHALL be written to `task.result.trace_file`
- **AND** no static analysis JSON SHALL be pushed to the device
- **AND** no compaction SHALL be attempted

#### Scenario: sata_mop execution with static analysis JSON present
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a valid path
- **THEN** the JSON SHALL be compacted into a temporary file
- **AND** the compacted file SHALL be pushed to `/data/local/tmp/static_analysis.json`
- **AND** the source file SHALL remain byte-identical
- **AND** `ape.properties` SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`

#### Scenario: sata_mop execution when compaction fails
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a path whose content is not parseable as JSON
- **THEN** a WARNING SHALL be logged
- **AND** the source file SHALL be pushed unchanged to `/data/local/tmp/static_analysis.json`
- **AND** `ape.properties` SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`
- **AND** execution SHALL continue normally

#### Scenario: sata_mop execution with static analysis JSON absent
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** no static analysis JSON file is found in `task.results_dir`
- **THEN** a WARNING SHALL be logged: `"sata_mop: static analysis file not found in results_dir, running without MOP data"`
- **AND** no compaction SHALL be attempted
- **AND** `ape.properties` SHALL NOT contain `ape.mopDataPath`
- **AND** execution SHALL continue (APE-RV runs as plain `sata`)

#### Scenario: Broadcast catalog pushed when present
- **WHEN** `system-broadcast.json` exists in the module directory
- **THEN** it SHALL be pushed to `/data/local/tmp/system-broadcast.json`
- **AND** APE-RV SHALL use it for component triggering with typed extras

#### Scenario: Broadcast catalog absent
- **WHEN** `system-broadcast.json` does not exist in the module directory
- **THEN** no broadcast catalog SHALL be pushed
- **AND** execution SHALL continue normally (APE-RV component triggering degrades gracefully)

#### Scenario: Execution timeout
- **WHEN** APE-RV runs for longer than `timeout_seconds + 15` seconds
- **THEN** `RVToolTimeoutError` SHALL be raised and logged
- **AND** the timeout SHALL be re-raised to the caller

#### Scenario: Non-zero exit code from APE-RV
- **WHEN** APE-RV exits with a non-zero exit code (e.g., 211)
- **THEN** execution SHALL NOT raise an error
- **AND** a debug log SHALL be emitted noting the exit code is normal when app crashes are detected

#### Scenario: Empty trace file
- **WHEN** APE-RV execution completes but writes nothing to stdout
- **THEN** a warning log line SHALL contain `"aperv produced empty trace file"`

---

### Requirement: ape.properties Generation

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file from `_tool_config` using `APERV_PROPERTY_MAPPING` and push it to `/data/local/tmp/ape.properties` on the device.

The property mapping translates Python config keys to Java property names:

| Python Key | Java Property | Category |
|------------|--------------|----------|
| `throttle_ms` | `ape.defaultGUIThrottle` | Exploration |
| `default_epsilon` | `ape.defaultEpsilon` | Exploration |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | Exploration |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | Exploration |
| `fuzzing_rate` | `ape.fuzzingRate` | Exploration |
| `do_fuzzing` | `ape.doFuzzing` | Exploration |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | Exploration |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | Exploration |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | Exploration |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | Exploration |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | Exploration |
| `mop_weight_direct` | `ape.mopWeightDirect` | MOP |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | MOP |
| `mop_weight_activity` | `ape.mopWeightActivity` | MOP |
| `llm_url` | `ape.llmUrl` | LLM |
| `llm_on_new_state` | `ape.llmOnNewState` | LLM |
| `llm_on_stagnation` | `ape.llmOnStagnation` | LLM |
| `llm_model` | `ape.llmModel` | LLM |
| `llm_temperature` | `ape.llmTemperature` | LLM |
| `llm_top_p` | `ape.llmTopP` | LLM |
| `llm_top_k` | `ape.llmTopK` | LLM |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | LLM |
| `llm_percentage` | `ape.llmPercentage` | LLM |
| `llm_prompt_variant` | `ape.llmPromptVariant` | LLM |

Keys in `_tool_config` that do not appear in `APERV_PROPERTY_MAPPING` (e.g., `strategy`, `mop_data`) are Python-only and are not written to the properties file.

When `mop_json_pushed` is True, the properties file SHALL also include `ape.mopDataPath=/data/local/tmp/static_analysis.json` (hardcoded device path matching the push destination).

#### Scenario: Properties file for sata variant
- **WHEN** `_push_properties()` is called for a `sata` variant with `throttle_ms=200`
- **THEN** the generated properties file SHALL contain `ape.defaultGUIThrottle=200`
- **AND** it SHALL NOT contain `ape.mopDataPath`
- **AND** it SHALL NOT contain `ape.llmUrl`

#### Scenario: Properties file for sata_mop_llm variant
- **WHEN** `_push_properties()` is called for a `sata_mop_llm` variant with `mop_json_pushed=True`
- **THEN** the generated properties file SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`
- **AND** it SHALL contain `ape.llmUrl=http://10.0.2.2:30000/v1`
- **AND** it SHALL contain `ape.llmOnNewState=true`
- **AND** it SHALL contain `ape.llmOnStagnation=true`
- **AND** it SHALL contain `ape.llmTemperature=0.3`

#### Scenario: Properties file for prompt experiment variant
- **WHEN** `_push_properties()` is called for `sata_mop_llm_v13` with `mop_json_pushed=True`
- **THEN** the generated properties file SHALL contain `ape.llmPromptVariant=v13`
- **AND** it SHALL contain `ape.llmPercentage=0.7`

---

### Requirement: Static Analysis File Discovery

`ApeRVTool._find_static_analysis_file(task)` SHALL locate the static analysis JSON file at `<task.results_dir>/<task.config.apk_name>.json`. This file is produced by rv-android's static analysis pipeline (GATOR/GESDA/REACH) during experiment pre-processing.

The method SHALL return the absolute path if the file exists, or `None` otherwise. It SHALL return `None` without error when `task.results_dir` or `task.config` are absent (graceful degradation for standalone execution outside rv-experiment).

#### Scenario: Static analysis file found
- **WHEN** `_find_static_analysis_file(task)` is called
- **AND** `task.results_dir` is `/results/exp1/` and `task.config.apk_name` is `com.example_1.apk`
- **AND** `/results/exp1/com.example_1.apk.json` exists
- **THEN** the method SHALL return `"/results/exp1/com.example_1.apk.json"`

#### Scenario: Static analysis file not found
- **WHEN** the JSON file does not exist in `task.results_dir`
- **THEN** `None` SHALL be returned

#### Scenario: Standalone execution without results_dir
- **WHEN** `task.results_dir` is None or absent
- **THEN** `None` SHALL be returned without error

---

### Requirement: Static Analysis JSON Compaction (FR19, FR04, NFR04)

`ApeRVTool` SHALL compact the static analysis JSON into a temporary file before pushing it to the device, and SHALL push the compacted file rather than the source file.

Compaction SHALL consist of exactly two lossless operations. First, entries in the `transitions` array SHALL be deduplicated by exact equality of the whole entry, preserving first-occurrence order. Entries carry exactly the keys `sourceId`, `targetId`, and `events`, so whole-entry canonical equality is identical to the `(sourceId, targetId, events)` tuple and cannot silently ignore a field added later. Second, the document SHALL be serialized without pretty-print whitespace.

The source file SHALL NOT be modified (INV-APV-20). Compaction SHALL run unconditionally, not gated on file size (INV-APV-23). No field SHALL be projected away (INV-APV-21).

Any failure -- malformed JSON, filesystem error writing the temporary file, or memory exhaustion loading the document -- SHALL be caught, SHALL emit a warning, and SHALL degrade to pushing the source file unchanged (INV-APV-24). The temporary file SHALL be unlinked after the push on every path (INV-APV-25).

#### Scenario: Oversized JSON compacted below the Java footprint ceiling
- **WHEN** `execute_tool_specific_logic(task, app)` runs with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a 50.6 MB JSON with 24,300 `transitions` entries of which 7,124 are unique (`org.quantumbadger.redreader_117.apk.json`)
- **THEN** the file pushed to `/data/local/tmp/static_analysis.json` SHALL be approximately 21.0 MB
- **AND** it SHALL contain exactly 7,124 `transitions` entries
- **AND** it SHALL be below the ~32 MB guard ceiling of `MopData.java:202`, so the MOP arm SHALL explore with more than 0 steps

#### Scenario: Source file is never modified
- **WHEN** compaction runs on `<task.results_dir>/<apk_name>.json`
- **THEN** the source file SHALL be byte-identical to its content before the call
- **AND** it SHALL remain byte-identical to the producer's output, so offline consolidation and `ResultProcessorComponent._resolve_static_data` on resume re-parse the archived artifact rather than a derived one

#### Scenario: Deduplication preserves first-occurrence order
- **WHEN** `transitions` is `[A, B, A, C, B]` where A, B, C are distinct entries
- **THEN** the compacted `transitions` SHALL be exactly `[A, B, C]`
- **AND** the relative order SHALL match first occurrence in the source

#### Scenario: All top-level keys survive compaction
- **WHEN** the source document has top-level keys `package`, `mainActivity`, `components`, `reachability`, `windows`, `transitions`, `complete`
- **THEN** the compacted document SHALL contain all seven keys
- **AND** the value of every key other than `transitions` SHALL be unchanged

#### Scenario: Small JSON is compacted anyway
- **WHEN** the source JSON is 100 KB, well below the ceiling
- **THEN** compaction SHALL still run (INV-APV-23)
- **AND** the compacted file SHALL be pushed

#### Scenario: JSON with no transitions key
- **WHEN** the source document has no `transitions` key
- **THEN** compaction SHALL succeed and minify the document
- **AND** no `transitions` key SHALL be added

#### Scenario: JSON with empty transitions array
- **WHEN** the source document has `transitions: []` (as in `sdmse` at 23.7 MB and `email` at 20.8 MB, the two next-largest JSONs in the `cmpma` set)
- **THEN** compaction SHALL succeed
- **AND** `transitions` SHALL remain `[]`

#### Scenario: Malformed JSON falls back to pushing the original
- **WHEN** the source file is not parseable as JSON
- **THEN** a warning SHALL be logged naming the file and the failure
- **AND** the source file SHALL be pushed unchanged to `/data/local/tmp/static_analysis.json`
- **AND** no exception SHALL propagate out of `execute_tool_specific_logic()`
- **AND** `ape.properties` SHALL still contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`

#### Scenario: No temporary file leaks on the success path
- **WHEN** compaction succeeds and the push completes
- **THEN** the temporary file SHALL NOT exist after `execute_tool_specific_logic()` returns

#### Scenario: No temporary file leaks on the fallback path
- **WHEN** compaction fails after the temporary file was created
- **THEN** the temporary file SHALL NOT exist after `execute_tool_specific_logic()` returns
- **AND** the source file SHALL have been pushed

---

### Requirement: uv Workspace Declaration

`aperv-tool/pyproject.toml` SHALL declare the package as a uv workspace member compatible with rv-android's `members = ["modules/*"]` discovery. It SHALL declare dependencies on `rv-android-core` and `rv-tools` as workspace sources.

The `[project.entry-points."rv_tools.plugins"]` table SHALL NOT be used for `aperv-tool` -- registration is done explicitly in `rv-platform/__init__.py`, not via entry-point auto-discovery.

#### Scenario: Module added to workspace
- **WHEN** `aperv-tool/` exists under `modules/` in the rv-android root
- **THEN** `uv sync` SHALL include `aperv-tool` in the workspace without any change to the root `pyproject.toml`
