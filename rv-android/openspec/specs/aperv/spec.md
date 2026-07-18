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

- **INV-APV-13**: `APERV_PROPERTY_MAPPING` MUST contain an entry for every key in `ARM_DEFINING_KEYS`. The
  Python→Java names MUST be: `ape_pure_mode`→`ape.apePureMode`, `frontier_boost_weight`→`ape.frontierBoostWeight`,
  `activity_trigger_enabled`→`ape.activityTriggerEnabled`,
  `back_menu_pick_cap`→`ape.backMenuPickCap`, `foreign_activity_guard`→`ape.foreignActivityGuard`,
  `tree_package_guard`→`ape.treePackageGuard`, `dynamic_epsilon`→`ape.dynamicEpsilon`,
  `heuristic_input`→`ape.heuristicInput`, `fuzz_input_typed`→`ape.fuzzInputTyped`,
  `form_completion_enabled`→`ape.formCompletionEnabled`, `step_telemetry_enabled`→`ape.stepTelemetryEnabled`,
  `model_menu_enabled`→`ape.modelMenuEnabled`, `least_visited_priority_tiebreak`→`ape.leastVisitedPriorityTiebreak`,
  `tree_enhancements_enabled`→`ape.treeEnhancementsEnabled`, `activity_budget_enabled`→`ape.activityBudgetEnabled`,
  `mop_activity_source_components`→`ape.mopActivitySourceComponents`, `mop_frontier_weight`→`ape.mopFrontierWeight`,
  `llm_percentage_no_substrate`→`ape.llmPercentageNoSubstrate`. (`trigger_mop_first` was removed — the
  APE-RV jar deleted `Config.triggerMopFirst` in `mop-census-launcher`, making `ape.triggerMopFirst` inert;
  it is no longer an arm-defining key.)

- **INV-APV-14**: Every variant returned by `get_variants()` **except** the exempt ones (INV-APV-17) MUST
  set **every** key in `ARM_DEFINING_KEYS` explicitly in its dictionary. A variant MUST NOT rely on a jar
  `Config` default for any arm-defining flag.

- **INV-APV-15**: `ARM_DEFINING_KEYS` MUST be a module-level constant in `tool.py` (a `frozenset` or
  tuple), the single source of truth consumed by both the guard tests and any reviewer. Adding a new
  arm-defining flag means adding it to `ARM_DEFINING_KEYS`, to `APERV_PROPERTY_MAPPING`, and to every
  non-exempt variant — in the same commit (the guard tests fail otherwise). `mop_data` and `strategy` are
  Python-only orchestration keys and MUST NOT be in `ARM_DEFINING_KEYS`; the MOP weight keys
  (`mop_weight_direct`/`mop_weight_transitive`/`mop_weight_open_menu`/`mop_weight_wtg`) are gated by
  `mop_data` (a null `MopData` disables scoring regardless of weights) and are therefore NOT arm-defining,
  but MUST be set explicitly in the MOP arms for auditability. `max_idle_timeout_ms`
  (→ `ape.maxIdleTimeoutMs`) is likewise an arm-neutral tuning knob: it is in `APERV_PROPERTY_MAPPING` but
  NOT in `ARM_DEFINING_KEYS`, and need not be set per-variant.

- **INV-APV-16**: `get_variants()["sata_mop"]` MUST be identical to `get_variants()["sata_mop_widget"]`
  (the documented alias). Changing the widget arm MUST change the alias in lockstep (they SHOULD reference
  one shared dict).

- **INV-APV-17**: The six gh43 prompt-experiment variants (`sata_mop_llm_ape_current`,
  `sata_mop_llm_ape_reasoning`, `sata_mop_llm_compact_v1`, `sata_mop_llm_v13`, `sata_mop_llm_v17`,
  `sata_mop_llm_visual_only`) are **frozen for historical reproducibility** and are EXEMPT from INV-APV-14.
  The exemption set MUST be an explicit, named constant so the guard test enumerates it deliberately (not a
  prefix match that could silently absorb a future non-exempt `sata_mop_llm_*` arm).

- **INV-APV-18**: When a `seed` is present in `_tool_config`, `_build_main_command` MUST append `-s <seed>`
  to the `app_process` argument vector (after `--ape <strategy>`). When no seed is configured, the command
  MUST NOT include `-s` (preserving the current non-deterministic default). The seed value is passed
  verbatim as a string. The `mop-fairtest` jar honors this seed (it parses `-s SEED` and seeds both
  `Monkey.mRandom` and APE's `RandomHelper`, INV-EXPL-14); this invariant closes the rv-android-side gap
  that previously dropped the seed.

- **INV-APV-19**: Introducing a new arm-defining APE-RV flag into `aperv-tool` MUST, in the same commit,
  (a) add the Python key to `ARM_DEFINING_KEYS`, (b) add its `APERV_PROPERTY_MAPPING` entry, and (c) set it
  explicitly in every non-exempt variant. INV-APV-13 and INV-APV-14 are the executable enforcement of this
  policy.

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

`ApeRVTool` SHALL define named variants organized in four tiers: base variants, MOP-arm variants, LLM
variants, and prompt experiment variants. Every variant SHALL include a `"strategy"` key and a
`"throttle_ms"` key. The `"default"` variant SHALL use strategy `"sata"` (INV-TOOL-02).

Every variant **except** the exempt prompt-experiment variants (INV-APV-17) SHALL set every key in
`ARM_DEFINING_KEYS` explicitly (INV-APV-14) so the arm's behavior is defined by the variant dictionary and
never by a jar `Config` default. Baseline arms (`default`/`sata`, `bfs`, `random`) SHALL set the RV
exploration flags to the current jar defaults made explicit (`back_menu_pick_cap=3`,
`foreign_activity_guard=true`, `tree_package_guard=true`, `dynamic_epsilon=true`,
`heuristic_input=true`, `fuzz_input_typed=true`, `form_completion_enabled=true`, `step_telemetry_enabled=true`,
`model_menu_enabled=true`, `least_visited_priority_tiebreak=true`, `tree_enhancements_enabled=true`,
`activity_budget_enabled=true`, `llm_percentage_no_substrate=-1`) and the MOP/reach/frontier flags
OFF (`ape_pure_mode=false`, `frontier_boost_weight=0`, `activity_trigger_enabled=false`,
`mop_activity_source_components=false`, `mop_frontier_weight=0`).

#### Base Variants

| Variant | strategy | mop_data | ape_pure_mode | RV exploration flags | frontier_boost_weight | activity_trigger_enabled | Notes |
|---------|----------|----------|---------------|----------------------|-----------------------|--------------------------|-------|
| `default` | `"sata"` | -- | `false` | ON (defaults explicit) | `0` | `false` | Alias for sata |
| `sata` | `"sata"` | -- | `false` | ON (defaults explicit) | `0` | `false` | aperv baseline, RV exploration ON, MOP off |
| `bfs` | `"bfs"` | -- | `false` | ON (defaults explicit) | `0` | `false` | Breadth-first baseline |
| `random` | `"random"` | -- | `false` | ON (defaults explicit) | `0` | `false` | Priority-weighted random baseline |
| `ape_pure` | `"sata"` | -- | `true` | **OFF (all explicit)** | `0` | `false` | Original APE via kill-switch; every RV flag off/0 |

`ape_pure` SHALL set `ape_pure_mode=true` **and** set every other arm-defining flag to its off/zero value
explicitly (defense-in-depth: the jar kill-switch forces RV off, and the explicit offs keep the guard test
uniform and the arm auditable without trusting the kill-switch). `ape_pure` SHALL NOT set `mop_data`.

#### MOP-Arm Variants

The MOP arms decompose the reach mechanism. All set `mop_data="static_analysis"` and the four MOP weights
explicitly (`mop_weight_direct=500`, `mop_weight_transitive=300`, `mop_weight_open_menu=250`,
`mop_weight_wtg=200`) and keep the full RV exploration baseline ON.

| Variant | mop_activity_source_components (A′) | frontier_boost_weight | mop_frontier_weight (B) | activity_trigger_enabled (E-min) | Notes |
|---------|-------------------------------------|-----------------------|-------------------------|----------------------------------|-------|
| `sata_mop_widget` | `false` | `0` | `0` | `false` | Current widget mechanism (MOP control) |
| `sata_mop_activity` | `true` | `0` | `0` | `false` | Isolates strategy A′ |
| `sata_mop_act_frontier` | `true` | `200` | `200` | `true` | Reach package A′+B+E-min |
| `sata_mop` | — alias of `sata_mop_widget` (identical dict, INV-APV-16) — | | | | Back-compat name |

The `mop_frontier_weight=200` value for `sata_mop_act_frontier` is a calibration starting point (design
§4: "≈200, calibrate in smoke"); calibration smokes use the DSL override
(`aperv:sata_mop_act_frontier@mop_frontier_weight=400`) and do not require a new variant.

#### LLM Variants

LLM variants add LLM-guided action selection. `llm_url` uses `http://10.0.2.2:30000/v1` (emulator host
loopback), overridable via `APERV_LLM_BASE_URL`. They set the full arm-defining set explicitly:
`sata_llm` on the `sata` baseline (MOP off), `sata_mop_llm` on the `sata_mop_widget` substrate (MOP on).

| Variant | mop_data | Arm-defining baseline | Notes |
|---------|----------|-----------------------|-------|
| `sata_llm` | -- | `sata` (MOP off) | SATA + LLM |
| `sata_mop_llm` | `"static_analysis"` | `sata_mop_widget` (MOP on) | SATA + MOP + LLM (round-2 base) |

LLM variants also include sampling parameters: `llm_model="default"`, `llm_temperature=0.3`,
`llm_top_p=0.6`, `llm_top_k=50`, `llm_timeout_ms=15000`.

#### Prompt Experiment Variants (FROZEN / EXEMPT — INV-APV-17)

Six variants for controlled prompt ablation (gh43). All use SATA + MOP + LLM with `llm_percentage=0.7` and
differ only in `llm_prompt_variant`. They are **frozen exactly as authored** and are EXEMPT from the
arm-defining explicitness policy (INV-APV-14) to preserve historical reproducibility.

| Variant | llm_prompt_variant |
|---------|--------------------|
| `sata_mop_llm_ape_current` | `ape_current` |
| `sata_mop_llm_ape_reasoning` | `ape_reasoning` |
| `sata_mop_llm_compact_v1` | `compact_v1` |
| `sata_mop_llm_v13` | `v13` |
| `sata_mop_llm_v17` | `v17` |
| `sata_mop_llm_visual_only` | `visual_only` |

#### Scenario: Baseline sata arm disables RV steering explicitly
- **WHEN** `get_variants()["sata"]` is read
- **THEN** it SHALL contain `frontier_boost_weight == 0` and `activity_trigger_enabled == False` explicitly
- **AND** it SHALL contain every key in `ARM_DEFINING_KEYS`
- **AND** it SHALL NOT contain a `mop_data` key

#### Scenario: ape_pure arm sets the kill-switch and every RV flag off
- **WHEN** `get_variants()["ape_pure"]` is read
- **THEN** `ape_pure_mode` SHALL be `True`
- **AND** every other key in `ARM_DEFINING_KEYS` SHALL be present with its off/zero value (e.g. `dynamic_epsilon == False`, `form_completion_enabled == False`, `model_menu_enabled == False`, `tree_enhancements_enabled == False`)
- **AND** `mop_data` SHALL NOT be present

#### Scenario: sata_mop_widget is the MOP control arm
- **WHEN** `get_variants()["sata_mop_widget"]` is read
- **THEN** `mop_data` SHALL equal `"static_analysis"`
- **AND** `mop_weight_direct == 500`, `mop_weight_transitive == 300`, `mop_weight_open_menu == 250`, `mop_weight_wtg == 200`
- **AND** `mop_activity_source_components == False`, `frontier_boost_weight == 0`, `mop_frontier_weight == 0`, `activity_trigger_enabled == False`
- **AND** `trigger_mop_first` SHALL NOT be present (removed — jar deleted the property)

#### Scenario: sata_mop_activity isolates strategy A′
- **WHEN** `get_variants()["sata_mop_activity"]` is read
- **THEN** it SHALL differ from `sata_mop_widget` only by `mop_activity_source_components == True`
- **AND** all other arm-defining keys SHALL equal the `sata_mop_widget` values

#### Scenario: sata_mop_act_frontier enables the reach package
- **WHEN** `get_variants()["sata_mop_act_frontier"]` is read
- **THEN** `mop_activity_source_components == True`, `frontier_boost_weight == 200`, `mop_frontier_weight == 200`, `activity_trigger_enabled == True`
- **AND** `mop_data` SHALL equal `"static_analysis"`
- **AND** `trigger_mop_first` SHALL NOT be present (E-min is carried by `activity_trigger_enabled` alone)

#### Scenario: sata_mop is an alias of sata_mop_widget
- **WHEN** `get_variants()["sata_mop"]` and `get_variants()["sata_mop_widget"]` are compared
- **THEN** the two dictionaries SHALL be equal (INV-APV-16)

#### Scenario: Every non-exempt variant sets every arm-defining key (guard)
- **WHEN** `get_variants()` is iterated over every variant whose name is NOT in the exempt set (the six `sata_mop_llm_<prompt>` variants)
- **THEN** each such variant SHALL contain every key in `ARM_DEFINING_KEYS`
- **AND** a variant missing any arm-defining key SHALL fail the guard test with a message naming the variant and the missing keys

#### Scenario: Creating tool with a new MOP arm variant
- **WHEN** `ToolFactory.create_tool(ToolConfig(name="aperv", variant="sata_mop_act_frontier"))` is called
- **THEN** the factory SHALL return a configured `ApeRVTool` instance
- **AND** `tool._tool_config["mop_data"]` SHALL be `"static_analysis"`
- **AND** `tool._tool_config["activity_trigger_enabled"]` SHALL be `True`

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

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file from `_tool_config` using
`APERV_PROPERTY_MAPPING` and push it to `/data/local/tmp/ape.properties` on the device. Only keys present
in both `_tool_config` and `APERV_PROPERTY_MAPPING` are written; Python-only keys (`strategy`, `mop_data`,
`seed`) have no mapping entry and are excluded automatically.

`APERV_PROPERTY_MAPPING` SHALL contain an entry for every arm-defining key (INV-APV-13), so that a flag set
in a variant dictionary actually reaches the device. The mapping translates Python config keys to Java
property names:

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
| `back_menu_pick_cap` | `ape.backMenuPickCap` | RV exploration (arm-defining) |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | arm-neutral (global tuning knob) |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | RV exploration (arm-defining) |
| `tree_package_guard` | `ape.treePackageGuard` | RV exploration (arm-defining) |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | RV exploration (arm-defining) |
| `heuristic_input` | `ape.heuristicInput` | RV exploration (arm-defining) |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | RV exploration (arm-defining) |
| `form_completion_enabled` | `ape.formCompletionEnabled` | RV exploration (arm-defining) |
| `step_telemetry_enabled` | `ape.stepTelemetryEnabled` | RV exploration (arm-defining) |
| `model_menu_enabled` | `ape.modelMenuEnabled` | RV exploration (arm-defining) |
| `least_visited_priority_tiebreak` | `ape.leastVisitedPriorityTiebreak` | RV exploration (arm-defining) |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | RV exploration (arm-defining) |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | RV exploration (arm-defining) |
| `ape_pure_mode` | `ape.apePureMode` | Kill-switch (arm-defining) |
| `mop_weight_direct` | `ape.mopWeightDirect` | MOP |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | MOP |
| `mop_weight_activity` | `ape.mopWeightActivity` | MOP (inert; back-compat) |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | MOP |
| `mop_weight_wtg` | `ape.mopWeightWtg` | MOP |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | MOP reach A′ (arm-defining) |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | MOP reach B (arm-defining) |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | Frontier (arm-defining) |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | Component triggering / MOP reach E-min (arm-defining) |
| `component_percentage` | `ape.componentPercentage` | Component triggering |
| `mop_target_pick_cap` | `ape.mopTargetPickCap` | MOP |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | Coverage |
| `llm_url` | `ape.llmUrl` | LLM |
| `llm_on_new_state` | `ape.llmOnNewState` | LLM |
| `llm_on_stagnation` | `ape.llmOnStagnation` | LLM |
| `llm_model` | `ape.llmModel` | LLM |
| `llm_temperature` | `ape.llmTemperature` | LLM |
| `llm_top_p` | `ape.llmTopP` | LLM |
| `llm_top_k` | `ape.llmTopK` | LLM |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | LLM |
| `llm_percentage` | `ape.llmPercentage` | LLM |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | LLM seam F′ (arm-defining) |
| `llm_prompt_variant` | `ape.llmPromptVariant` | LLM |

When `mop_json_pushed` is True, the properties file SHALL also include
`ape.mopDataPath=/data/local/tmp/static_analysis.json` (hardcoded device path matching the push
destination). An `ape.*` key the jar does not recognize is ignored by the jar's `Config` loader (a
name-mismatch is inert, not an error).

#### Scenario: Arm-defining flags appear in properties for a baseline arm
- **WHEN** `_push_properties()` is called for the `sata` variant
- **THEN** the generated properties file SHALL contain `ape.frontierBoostWeight=0`
- **AND** it SHALL contain `ape.activityTriggerEnabled=false`
- **AND** it SHALL contain `ape.dynamicEpsilon=true`
- **AND** it SHALL NOT contain `ape.mopDataPath`

#### Scenario: Kill-switch flag appears in properties for ape_pure
- **WHEN** `_push_properties()` is called for the `ape_pure` variant
- **THEN** the generated properties file SHALL contain `ape.apePureMode=true`
- **AND** it SHALL contain `ape.frontierBoostWeight=0` and `ape.activityTriggerEnabled=false`

#### Scenario: Reach-package flags appear in properties for sata_mop_act_frontier
- **WHEN** `_push_properties()` is called for `sata_mop_act_frontier` with `mop_json_pushed=True`
- **THEN** the properties file SHALL contain `ape.mopActivitySourceComponents=true`
- **AND** it SHALL contain `ape.mopFrontierWeight=200` and `ape.activityTriggerEnabled=true`
- **AND** it SHALL contain `ape.mopDataPath=/data/local/tmp/static_analysis.json`
- **AND** it SHALL NOT contain `ape.triggerMopFirst` (property removed)

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for a variant whose `_tool_config` contains `strategy`, `mop_data`, and `seed`
- **THEN** the properties file SHALL NOT contain `strategy`, `mop_data`, or `seed`

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

---

### Requirement: Arm-Defining Flag Completeness (FR20)

`aperv-tool` SHALL declare a module-level constant `ARM_DEFINING_KEYS` in `tool.py` enumerating every
Python config key whose value defines an experiment arm (INV-APV-15). A guard test suite SHALL enforce two
properties so an arm's identity can never silently fall back to a jar default:

1. **Mapping completeness (INV-APV-13)**: every key in `ARM_DEFINING_KEYS` has an entry in
   `APERV_PROPERTY_MAPPING`.
2. **Variant explicitness (INV-APV-14)**: every variant returned by `get_variants()`, except the exempt
   gh43 prompt-experiment variants (INV-APV-17), sets every key in `ARM_DEFINING_KEYS` explicitly.

The exempt set SHALL be an explicit named constant (not a prefix match), so a future non-exempt
`sata_mop_llm_*` arm is not silently absorbed (INV-APV-17). Introducing a new arm-defining flag SHALL
require updating `ARM_DEFINING_KEYS`, `APERV_PROPERTY_MAPPING`, and every non-exempt variant in the same
commit (INV-APV-19) — the guard tests are the executable enforcement.

`mop_data` and `strategy` are Python-only orchestration keys and SHALL NOT be members of
`ARM_DEFINING_KEYS`. The four MOP weight keys are gated by `mop_data` (a null `MopData` disables scoring
regardless of weight) and SHALL NOT be members of `ARM_DEFINING_KEYS`, but SHALL be set explicitly in the
MOP arms for auditability.

#### Scenario: Every arm-defining key is mapped
- **WHEN** the guard test iterates `ARM_DEFINING_KEYS`
- **THEN** every key SHALL be present in `APERV_PROPERTY_MAPPING`
- **AND** a key absent from the mapping SHALL fail the test naming the offending key

#### Scenario: Every non-exempt variant is explicit
- **WHEN** the guard test iterates `get_variants()` excluding the six named gh43 prompt-experiment variants
- **THEN** each remaining variant SHALL contain every key in `ARM_DEFINING_KEYS`
- **AND** the failure message SHALL name the variant and the missing arm-defining keys

#### Scenario: Exempt variants are skipped deliberately
- **WHEN** the guard test computes the exempt set
- **THEN** it SHALL be the explicit constant naming exactly the six `sata_mop_llm_<prompt>` variants
- **AND** the six exempt variants SHALL NOT be required to set `ARM_DEFINING_KEYS`

#### Scenario: mop_data and strategy are not arm-defining keys
- **WHEN** the guard test inspects `ARM_DEFINING_KEYS`
- **THEN** it SHALL NOT contain `mop_data` or `strategy`

---

### Requirement: Seed Propagation to APE-RV (FR18, FR19)

`ApeRVTool._build_main_command()` SHALL append `-s <seed>` to the `app_process` argument vector when a
`seed` key is present in `_tool_config` (INV-APV-18). The seed reaches `_tool_config` via the tool DSL
(`aperv:<variant>@seed=<n>`) or `ToolConfig.parameters`, merged by `ToolFactory`. When no seed is
configured, the command SHALL NOT include `-s`, preserving the current default where the jar self-seeds
non-deterministically.

The `mop-fairtest` APE-RV jar already honors a passed seed: `Monkey` parses `-s SEED`
(`Monkey.java:886-887`), and when `mSeed != 0` it seeds both `Monkey.mRandom` and APE's `RandomHelper`
(`Monkey.java:731`, `RandomHelper.seed(mSeed)`, INV-EXPL-14) — so a fixed seed makes a run reproducible.
The rv-android-side gap (the command never emitting `-s`) is what this requirement closes; no jar change
is required.

#### Scenario: Seed configured is passed as -s
- **WHEN** `_build_main_command(app, "emulator-5554", 60)` is called with `_tool_config` containing `seed=42`
- **THEN** the command argument vector SHALL contain `-s` immediately followed by `"42"`
- **AND** the `-s 42` pair SHALL appear after `--ape <strategy>`

#### Scenario: No seed configured omits -s
- **WHEN** `_build_main_command(app, "emulator-5554", 60)` is called with `_tool_config` containing no `seed` key
- **THEN** the command argument vector SHALL NOT contain `-s`

#### Scenario: Seed is not written to ape.properties
- **WHEN** `_push_properties()` is called for a variant whose `_tool_config` contains `seed=42`
- **THEN** the generated properties file SHALL NOT contain a `seed` line (it is a CLI-only, Python-only key)
