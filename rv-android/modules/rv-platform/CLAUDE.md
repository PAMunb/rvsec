# CLAUDE.md - rv-platform

## Purpose

Central execution engine for RV-Android experiments. Generates tasks from APK discovery, runs them through a component-based `TaskExecutor`, coordinates emulator/tool lifecycle, and processes results into CSV/JSON. Sits between experiment orchestration (rv-experiment) and task-execution mechanics; usable standalone via CLI or as a service.

Coverage runs here as a `TaskExecutor` component (`CoverageComponent` → rv-coverage `CoverageTracker`); rv-coverage only supplies the tracker/parser. The logcat-based resume reconstruction (below) is owned by this module. Domain models and `package_name` vs `code_package` are owned by rv-android-core — referenced, not redescribed here.

## Key Components

| Component | Purpose |
|-----------|---------|
| `Platform` | Entry point — orchestrates task generation and execution |
| `TaskExecutor` | Component-based execution with initialize/execute/cleanup lifecycle |
| `EmulatorComponent` | Emulator lifecycle, app install, dynamic port allocation (parallel exec) |
| `CoverageComponent` | Coverage tracker init + result processing |
| `StaticAnalysisComponent` | Loads static-analysis data (GATOR) for tasks |
| `LogcatComponent` | Logcat capture/filtering during execution |
| `ToolExecutionComponent` | Tool invocation and result processing |
| `ResultProcessorComponent` | CSV/JSON output from completed tasks |
| `PerformanceProcessorComponent` | Task-timing CSV |
| `TaskStorage` | Persistent task storage; atomic file ops with transaction support |
| `PlatformConfig` | Pydantic-validated configuration schema |
| `device.resolve_device` | `(port, serial)` from `tool_config.parameters` — the one device derivation |

Platform-unique design points: components execute in **coordinated phases** (static analysis + coverage init outside the emulator session, tool execution inside it); `TaskStorage` persists task state via atomic transactions after each task.

## Output Files

Written to the results directory:

| File | Description |
|------|-------------|
| `coverage.csv` | Per-method coverage with timing and progressive metrics |
| `errors.csv` | Monitored-operations violations with timing/context |
| `summary.csv` | Aggregate metrics per task (activities, methods, MOP coverage, errors) |
| `results.json` | Hierarchical JSON with complete experiment data |
| `performance.csv` | Task execution timing metrics |
| `tasks.json` | Task-state persistence for continuation. Holds `ExperimentMetadata` (with `config_checksum`) and per-task `result` incl. `logcat_file`. **On resume, coverage/MOP are reconstructed from the logcat + co-located SA JSON — not from the serialized `coverage_metrics`.** |

## Experiment Resume

When `tasks.json` exists, the platform loads completed tasks, skips them, executes only new/pending ones, and consolidates results across all sessions.

**Resume forms**
- **Expand**: rerun with more repetitions — completed tasks matched by `(apk_name, name, variant, repetition, timeout)` identity are skipped; only new tasks run.
- **Crash recovery**: rerun the same command — tasks persisted atomically after each completion are skipped; the interrupted task re-executes from scratch.

**Flow** (`Platform.run()`): `_generate_tasks()` → build `ExperimentMetadata` with SHA-256 `config_checksum` → `_skip_completed_tasks()` matches the identity tuple, removes matches, stores `_skipped_count` → if the stored checksum differs, `platform.py` logs a WARNING with the first 8 hex chars of each (TaskStorage logs at DEBUG) → remaining tasks execute → `_process_results()` calls `task_storage.get_completed_tasks()` (ALL sessions) → `ResultProcessorComponent` writes unified CSV/JSON → `_generate_summary()` includes `_skipped_count`.

**Coverage + MOP reconstruction from logcat.** Tasks loaded from `tasks.json` have `repository=None` (the in-memory `LogcatRepository` is not serialized). `ResultProcessorComponent` detects this and calls `_reconstruct_repository_from_logcat(task)`, which re-reads `task.result.logcat_file` and re-parses the co-located SA JSON via `_resolve_static_data`, so the rebuilt repository carries **both** per-method coverage AND MOP violations — equivalent to the live path. Call sites: `_write_task_coverage_data()`, `_write_task_error_data()`, `_write_task_summary_data()`, `_extract_task_data()`.

`_resolve_static_data` derives the per-APK dir from `os.path.dirname(task.result.logcat_file)` when `task.results_dir` is empty — always true on resume, because `Task.to_dict` serializes only `id/config/result` and `from_dict` leaves `results_dir=""`/`app=None` (gh65). The SA JSON is co-located with the logcat, so the derived path resolves both. The parser is called with `code_package=None` (app is `None` on resume); GATOR already pre-filtered `reachability[]` to app classes, so no class filter is needed.

**INV-PLT-16** — no fallback to serialized `task.result.coverage_metrics`: it would populate `summary.csv` `cov_*` while `coverage.csv` (per-method rows, only producible from a populated repository) stays empty — the `summary != 0 with coverage_rows = 0` inconsistency `verify.py` C3 flags. When the logcat is present but the JSON is genuinely absent, both writers emit a **zeroed coverage row** (errors still accurate — `calculate_metrics` counts them before the empty-`classes` early return) and the task is counted once in `_unresolved_task_ids`. **INV-PLT-18** — `execute()` surfaces the aggregate as one `N/M` resume health-check WARNING. When the logcat itself is missing, no coverage row is emitted.

**Key fields**
- `Platform._skipped_count`: tasks skipped from previous runs (used in summary).
- `TaskResult.logcat_file`: path to persisted logcat (serialized in `tasks.json`; resume derives `results_dir` from its dirname and resolves the co-located SA JSON).
- `ResultProcessorComponent._unresolved_task_ids`: per-pass set of task IDs whose SA JSON could not be resolved; `len(...)` is the `N` in the health-check WARNING (re-initialized each `execute()`).

## Important Notes

- **Timeout handling**: tool timeouts are treated as successful completion (expected behavior).
- **APK installation**: `EmulatorComponent.install_app()` returns False on install failure (`CommandResult.is_failure()`) and holds the ADB reason in `last_install_error`; `TaskExecutor` raises `TaskExecutionError` with that reason, so the `INSTALL_FAILED_*` code reaches the stored `error_message`.
- **One device resolution**: `device.resolve_device(parameters)` derives `(device_port, device_serial)` from `tool_config.parameters` — the serial follows the port unless `device_serial` is given explicitly. Boot, app install, logcat capture and `Platform._generate_tasks`'s `device_id` all call it, so no component carries its own `"emulator-5554"` fallback (INV-PLT-28). It takes the parameters mapping, not a `Task`, because `_generate_tasks` runs before any `Task` exists. A wrong-device *capture* is what makes this load-bearing: unlike a wrong-device install it raises nothing, yielding an empty logcat and therefore an empty resume reconstruction.
- **Emulator boot is a gate**: `Android.wait_for_boot()` raises `TimeoutError` when the budget (`RV_EMULATOR_BOOT_TIMEOUT`, default 300 s) is exhausted, wrapped as `EmulatorError` by `start_emulator()`; no task runs against a half-booted device. Per-probe ADB timeout: `RV_ADB_CMD_TIMEOUT` (30 s); install: `RV_APK_INSTALL_TIMEOUT` (600 s).
- **Coverage/logcat finalization** happens at exactly one point — a `finally` inside the emulator `with` in `TaskExecutor._run_emulator_session()` — calling `logcat_component.cleanup()` then `coverage_component.cleanup()`. Logcat first because `adb logcat` is the producer writing the file and `CoverageTracker` is the consumer reading it: freezing the file first makes the tracker's final drain see a complete input. The repeat call from `_cleanup_components()` is inert.
- **Static analysis** is non-critical — execution continues without it. It uses `app.code_package` (detected implementation package), not `app.package_name` (manifest), for class filtering (see rv-android-core).
- **Result processing** can be skipped during execution and run standalone later (`--process-results`).
