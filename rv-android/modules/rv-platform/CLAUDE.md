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
| `ResultProcessorComponent` | CSV/JSON output from completed tasks, one task-major pass with a per-APK static model |
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
| `errors.csv` | Monitored-operations violations. **13 columns (INV-PLT-19)**: `apk, rep, timeout, tool, time, spec, class, method, source, code, event, message, unique_msg` — defined once, in `ERRORS_CSV_COLUMNS` (`components/result_processor.py`). `code`/`event` are the `code=`/`ev=` values of the message envelope, or `UNSPECIFIED` when the record carries none (the frozen `jca` set writes none). `unique_msg` is **read** from `RvErrorLog`, never rebuilt in the writer (INV-CORE-25); an absent key is a `KeyError`. Consumers address columns by name, so appending is compatible; positional readers are not supported. |
| `summary.csv` | Aggregate metrics per task (activities, methods, MOP coverage, errors) |
| `results.json` | Hierarchical JSON with complete experiment data |
| `performance.csv` | Task execution timing metrics |
| `app_events.csv` | Diagnostic events (crash / VerifyError / ANR), `stack_head` only — the full trace stays in the `.logcat`. Diagnostic fields never enter the three CSVs above (INV-PLT-19). |
| `tasks.json` | Task-state persistence for continuation. Holds `ExperimentMetadata` (with `config_checksum`) and per-task `result` incl. `logcat_file`. **On resume, coverage/MOP are reconstructed from the logcat + co-located SA JSON — not from the serialized `coverage_metrics`.** |

## Experiment Resume

When `tasks.json` exists, the platform loads completed tasks, skips them, executes only new/pending ones, and consolidates results across all sessions.

**Resume forms**
- **Expand**: rerun with more repetitions — completed tasks matched by `(apk_name, name, variant, repetition, timeout)` identity are skipped; only new tasks run.
- **Crash recovery**: rerun the same command — tasks persisted atomically after each completion are skipped; the interrupted task re-executes from scratch.

**Flow** (`Platform.run()`): `_generate_tasks()` → build `ExperimentMetadata` with SHA-256 `config_checksum` → `_skip_completed_tasks()` matches the identity tuple, removes matches, stores `_skipped_count` → if the stored checksum differs, `platform.py` logs a WARNING with the first 8 hex chars of each (TaskStorage logs at DEBUG) → remaining tasks execute → `_process_results()` calls `task_storage.get_completed_tasks()` (ALL sessions) → `ResultProcessorComponent` writes unified CSV/JSON → `_generate_summary()` includes `_skipped_count`.

**Coverage + MOP reconstruction from logcat.** No task reaches result processing with a repository. Tasks loaded from `tasks.json` have `repository=None` (the in-memory `LogcatRepository` is not serialized), and a task finished in the current session has already released it: `Platform` sets `task.repository` and `task.static_data` to `None` right after `task_storage.update_task(task)`, on the success and the error path alike (INV-PLT-38). Nothing after completion needs either field — the run's coverage metrics are already on `task.result`, and neither field is serialized — while keeping them would grow a long session's memory with every finished execution. `ResultProcessorComponent` therefore calls `_reconstruct_repository_from_logcat(task)` for every task, which re-reads `task.result.logcat_file` and passes the APK's static model from `_resolve_static_data`, so the rebuilt repository carries **both** per-method coverage AND MOP violations — equivalent to the live path. The coverage writer stores the rebuilt repository on the task, and the other writers of the same task reuse it. Call sites: `_write_task_coverage_data()`, `_write_task_error_data()`, `_write_task_summary_data()`, `_extract_task_data()`.

**One pass, task-major.** `execute()` sorts the completed tasks by `(apk, tool, rep, timeout)`, writes the four CSV headers once (the `_generate_*_csv([])` calls), reopens those files for append and loops over the tasks: for each one, the coverage, errors, app-events and summary writers run and `_add_results_entry` extracts its `results.json` entry, and then `task.repository` and `task.static_data` are set to `None` before the next task. `results.json` is written once after the loop from the accumulated dictionary (it holds no repository or model), and `performance.csv` follows, reading no repository. Rows in every file follow the sorted task order. The shape is dictated by memory: a file-major loop (six passes over all tasks) keeps a reconstructed repository and a static model alive on every task already visited until the last file is written, and a campaign-sized export is killed by the kernel that way; the task-major loop holds one repository and one static model at a time.

**Static model: one entry per APK.** `_resolve_static_data` keeps `_static_data_by_apk`, a dictionary with at most one entry `{apk: StaticAnalysisData}`, and calls `read_static_analysis_files` only when the task's APK is not the cached one, replacing the entry (INV-PLT-15). The sort makes each APK's tasks contiguous, so the JSON of an APK is parsed once per `execute()`. The entry holds a valid `StaticAnalysisData` on every path — an empty one when the JSON is absent or the parser raises — so the APK's later tasks do not retry the parse and `parse_logcat_file` always receives a legal argument; the cache is emptied when the pass ends. There is no per-task parse memo on `task.static_data`: the field only carries the model during the task's own writers.

`_resolve_static_data` uses `task.results_dir` when set and otherwise derives the per-APK dir from `os.path.dirname(task.result.logcat_file)` — always the case on resume, because `Task.to_dict` serializes only `id/config/result` and `from_dict` leaves `results_dir=""`/`app=None` (gh65). The SA JSON is co-located with the logcat, so the derived path resolves both. The parser is called with the directory and APK name only — it takes no key on either path (INV-ANA-61), so `app=None` on resume costs the reconstruction nothing and the parsed universe is identical to the live path's.

**INV-PLT-16** — no fallback to serialized `task.result.coverage_metrics`: it would populate `summary.csv` `cov_*` while `coverage.csv` (per-method rows, only producible from a populated repository) stays empty — the `summary != 0 with coverage_rows = 0` inconsistency `verify.py` C3 flags. When the logcat is present but the JSON is genuinely absent, the task's coverage cells are written **empty**, not `0.00`, and its `summary.csv` row has `measured=false` (INV-PLT-35; errors still accurate — `calculate_metrics` counts them before the empty-`classes` early return) and the task is counted once in `_unresolved_task_ids`. **INV-PLT-18** — `execute()` surfaces the aggregate as one `N/M` resume health-check WARNING. When the logcat itself is missing, no coverage row is emitted.

**A `COMPLETED` task is not by itself a valid one.** The state records that the tool returned without raising, not that the run did what it was asked to do. A run whose emulator died mid-exploration, or whose tool stopped on its own, can be stored `COMPLETED` with an empty `error_message` — gh97 found two of these in a 360-run campaign, at 1284 s and 1012 s of an 1800 s budget. Anything that consumes `tasks.json` for analysis has to decide admissibility itself, from the artefacts, before aggregating: state and empty error message, elapsed time against the declared timeout, a trace with at least one step beyond the run header, and a non-empty coverage signal. The tool-side counterpart of this rule lives in `modules/aperv-tool/CLAUDE.md` (INV-APV-60).

**What resume does with each state.** `_skip_completed_tasks()` matches on the identity tuple `(apk_name, name, variant, repetition, timeout)` and skips only records whose state is `COMPLETED`. An `ERROR` record is **not** skipped, so the identity re-executes — and the store **appends**, it does not overwrite: after recovery that identity holds two records, the `ERROR` and the `COMPLETED`. This is why analysis must **count per identity, never per record** (a 360-identity campaign with 9 recoveries holds 369 records), and why the way to return a silently-bad `COMPLETED` run to the queue is to rewrite its state to `ERROR` after preserving its artefacts. An interrupted run that never reached persistence leaves no record at all and simply re-executes.

**Key fields**
- `Platform._skipped_count`: tasks skipped from previous runs (used in summary).
- `TaskResult.logcat_file`: path to persisted logcat (serialized in `tasks.json`; resume derives `results_dir` from its dirname and resolves the co-located SA JSON).
- `ResultProcessorComponent._unresolved_task_ids`: per-pass set of task IDs whose SA JSON could not be resolved, each task recorded once; `len(...)` is the `N` in the health-check WARNING (re-initialized each `execute()`).
- `ResultProcessorComponent._static_data_by_apk`: the one-entry static-model cache of the pass (re-initialized each `execute()`, emptied after the loop).

## Important Notes

- **Timeout handling**: tool timeouts are treated as successful completion (expected behavior).
- **APK installation**: `EmulatorComponent.install_app()` returns False on install failure (`CommandResult.is_failure()`) and holds the ADB reason in `last_install_error`; `TaskExecutor` raises `TaskExecutionError` with that reason, so the `INSTALL_FAILED_*` code reaches the stored `error_message`.
- **One device resolution**: `device.resolve_device(parameters)` derives `(device_port, device_serial)` from `tool_config.parameters` — the serial follows the port unless `device_serial` is given explicitly. Boot, app install, logcat capture and `Platform._generate_tasks`'s `device_id` all call it, so no component carries its own `"emulator-5554"` fallback (INV-PLT-28). It takes the parameters mapping, not a `Task`, because `_generate_tasks` runs before any `Task` exists. A wrong-device *capture* is what makes this load-bearing: unlike a wrong-device install it raises nothing, yielding an empty logcat and therefore an empty resume reconstruction.
- **Emulator boot is a gate**: `Android.wait_for_boot()` raises `TimeoutError` when the budget (`RV_EMULATOR_BOOT_TIMEOUT`, default 300 s) is exhausted, wrapped as `EmulatorError` by `start_emulator()`; no task runs against a half-booted device. Per-probe ADB timeout: `RV_ADB_CMD_TIMEOUT` (30 s); install: `RV_APK_INSTALL_TIMEOUT` (600 s).
- **Coverage/logcat finalization** happens at exactly one point — a `finally` inside the emulator `with` in `TaskExecutor._run_emulator_session()` — calling `logcat_component.cleanup()` then `coverage_component.cleanup()`. Logcat first because `adb logcat` is the producer writing the file and `CoverageTracker` is the consumer reading it: freezing the file first makes the tracker's final drain see a complete input. The repeat call from `_cleanup_components()` is inert.
- **Static analysis** is non-critical — execution continues without it. Loading it resolves no package key: GATOR scoped the artefact when it produced it, and `reachability[]` is the whole coverage denominator (INV-ANA-59). `app.code_package` still chooses the scope when an analysis is *run*, which happens in rv-static-analysis, not here.
- **Result processing** can be skipped during execution and run standalone later (`--process-results`).
- **Lost rows are counted, not swallowed** (INV-PLT-32): a failed `errors.csv` write, a failed `results.json` extraction, a missing logcat (`logcat_missing`) or a failed reconstruction (`logcat_reconstruction`) log at ERROR with the number of rows lost and increment `TaskResult.write_errors[artefact]`. Without the count, a task whose violations were lost reads downstream exactly like a task that violated nothing. Generation continues with the next task.
