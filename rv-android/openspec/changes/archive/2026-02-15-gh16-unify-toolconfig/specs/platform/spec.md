## REMOVED Requirements

### Requirement: Platform-local ToolConfig class
**Reason**: Replaced by unified ToolConfig in rv-android-core. The platform-local ToolConfig class (`rv_platform.config.platform_config.ToolConfig`) with fields `name`, `variants: List[str]`, `parameters` is deleted. All modules now import ToolConfig from `rv_android_core.domain.task`.
**Migration**: Import `ToolConfig` from `rv_android_core.domain.task` instead of `rv_platform.config.platform_config`. Use `variant: str` (singular) instead of `variants: List[str]` (plural). Multi-variant tools are represented as multiple ToolConfig instances in the `tools` list.

## MODIFIED Requirements

### Requirement: Android Emulator Management (FR07, NFR04, NFR07)

The platform MUST manage the full lifecycle of Android emulator instances during task execution. This includes starting the emulator with a named AVD, allocating a unique device port, installing the APK under test, and stopping the emulator after task completion. Emulator management is encapsulated in `EmulatorComponent`, which operates within the Phase 3 context manager in `TaskExecutor._run_emulator_session()`.

Dynamic port allocation is necessary because the ICST study runs multiple tool configurations across 188 applications, and future parallel execution requires isolated emulator instances. Each task can specify a unique `device_port` (default 5554) and `device_serial` (default `emulator-5554`) via `tool_config.parameters`, enabling multiple concurrent emulator sessions without port conflicts.

The emulator is started using the `EmulatorManager.start_emulator()` context manager, which ensures proper cleanup on both normal and exceptional exits. App installation is verified via `CommandResult.is_failure()` -- if installation fails, `EmulatorError` is raised and the task transitions to `ERROR` state.

#### Scenario: Successful Emulator Startup and APK Installation

- **WHEN** a task is being executed with `apk_name="cryptoapp.apk"` and `no_window=True`
- **THEN** `EmulatorComponent.start_emulator("RVSec")` MUST start the emulator in headless mode on the default port 5554
- **AND** `EmulatorComponent.install_app()` MUST install the APK on the emulator

#### Scenario: APK Installation Failure

- **WHEN** `EmulatorComponent.install_app()` is called and `EmulatorManager.install_app()` returns `False`
- **THEN** the component MUST raise `EmulatorError` with message containing the app name
- **AND** the error MUST be handled by `ErrorHandler` with task context
- **AND** the method MUST return `False`

#### Scenario: Dynamic Port Allocation for Parallel Execution

- **WHEN** a task has `tool_config.parameters = {"device_port": 5558, "device_serial": "emulator-5558"}`
- **THEN** `EmulatorComponent.start_emulator()` MUST pass port `5558` to `EmulatorManager.start_emulator()`
- **AND** `EmulatorComponent.install_app()` MUST pass `device_serial="emulator-5558"` to `EmulatorManager.install_app()`

#### Scenario: Skip Installation When Configured

- **WHEN** `task.config.skip_installation` is `True`
- **THEN** `EmulatorComponent.install_app()` MUST return `True` without calling `EmulatorManager.install_app()`
- **AND** a skip log message MUST be emitted

#### Scenario: Logcat Buffer Clearing

- **WHEN** `EmulatorComponent.clean_logcat()` is called
- **THEN** the component MUST call `EmulatorManager.clear_logcat()` to reset the logcat buffer
- **AND** if clearing fails, the error MUST be logged as a warning (non-critical)

### Requirement: Task Generation (FR08)

The platform MUST generate tasks as the Cartesian product of discovered APKs, configured tools (each ToolConfig representing one tool+variant pair), repetitions, and timeouts. Each unique combination produces exactly one `Task` object with a `TaskConfiguration` containing the APK name, tool configuration (name, variant, parameters), repetition number, and timeout value.

Task generation is the first step of `Platform.run()`. The platform discovers APK files by globbing `*.apk` in the configured `apks_dir` (sorted alphabetically). If no APK files are found, `Platform._discover_apks()` raises `ValueError`. For each APK, the platform iterates over all tool configs, repetition numbers (1 to `config.repetitions` inclusive), and timeout values. For each combination, a `Task` is created via `TaskFactory.create_task()`, associated with an `App` instance, and initialized with the results directory.

Variant expansion is handled at the CLI parser layer, not inside Platform. When the CLI receives `droidbot:dfs_greedy:bfs_greedy`, the parser creates two separate ToolConfig instances — `ToolConfig(name="droidbot", variant="dfs_greedy")` and `ToolConfig(name="droidbot", variant="bfs_greedy")`. Platform receives a flat list of ToolConfig objects with singular variants.

Tasks follow a lifecycle: `CREATED` (initial) -> `RUNNING` (when executor begins) -> `COMPLETED` (success, including timeout) or `ERROR` (failure). The `INITIALIZING`, `READY`, and `CANCELED` states are defined in `TaskState` but are not actively used by `TaskExecutor.execute()` in the current implementation.

#### Scenario: Basic Task Generation

- **WHEN** `apks_dir` contains 2 APK files, `tools` has 1 ToolConfig with `variant="default"`, `repetitions=1`, and `timeouts=[300]`
- **THEN** `Platform._generate_tasks()` MUST produce exactly 2 tasks (2 APKs x 1 tool_config x 1 rep x 1 timeout)
- **AND** each task MUST have an `App` instance set via `task.set_app()`
- **AND** each task MUST be initialized with the results directory via `task.initialize()`

#### Scenario: Multi-Variant Task Generation

- **WHEN** `tools` has 2 ToolConfig instances `[ToolConfig(name="droidbot", variant="dfs_greedy"), ToolConfig(name="droidbot", variant="bfs_greedy")]`, `repetitions=3`, and `timeouts=[60, 300]`
- **THEN** the number of tasks per APK MUST be `2 x 3 x 2 = 12`
- **AND** each task's `TaskConfiguration.tool_config.variant` MUST match the corresponding variant name

#### Scenario: No APKs Found

- **WHEN** `apks_dir` exists but contains no `.apk` files
- **THEN** `Platform._discover_apks()` MUST raise `ValueError` with a message including the directory path

### Requirement: Logcat Capture (FR11)

The platform MUST capture Android logcat output during tool execution for post-experiment analysis.

#### Scenario: Parallel Execution Device Serial

- **WHEN** `task.config.tool_config.parameters` contains `device_serial: "emulator-5558"`
- **THEN** `LogcatComponent` MUST initialize `LogcatManager` with `device_serial="emulator-5558"`
- **AND** logcat capture MUST be scoped to that specific emulator instance
