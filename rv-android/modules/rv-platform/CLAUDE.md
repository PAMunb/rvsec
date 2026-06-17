# CLAUDE.md - rv-platform

## Purpose

rv-platform is the central execution engine for Android testing experiments in the RV-Android framework. It orchestrates task generation from APK discovery, manages task execution through a component-based architecture, coordinates emulator lifecycle and tool execution, and processes results into standardized CSV/JSON output files. The platform provides a clean separation between experiment orchestration (rv-experiment) and the actual task execution mechanics, enabling both standalone usage via CLI and integration as a service within larger experiment workflows.

## Architecture

### Key Patterns and Design Decisions

- **Component-Based Execution**: TaskExecutor uses pluggable components (EmulatorComponent, CoverageComponent, etc.) for different execution phases with initialize/execute/cleanup lifecycle
- **Coordinated Component Execution**: Components execute in specific phases - static analysis and coverage initialization outside emulator session, tool execution inside emulator context
- **Persistent Task Storage**: TaskStorage provides atomic file operations with transaction support for robust task state persistence
- **Pydantic Configuration**: PlatformConfig uses Pydantic for validation with comprehensive field validators
- **Error Handler Integration**: ErrorHandler decorator pattern for consistent error management across all components

### Execution Flow

1. **Task Generation**: Platform discovers APKs, generates tasks for each APK/tool/variant/repetition/timeout combination
2. **ExperimentMetadata Creation**: Creates `ExperimentMetadata` from config, including a SHA-256 `config_checksum`
3. **Resume Check**: `_skip_completed_tasks()` loads completed tasks from `TaskStorage`, matches by `(apk_name, name, variant, repetition, timeout)` identity, removes matches from the execution list, and stores `_skipped_count`. If the config checksum differs from a previous run, a WARNING is logged with the first 8 hex chars of each checksum
4. **Component Registration**: TaskExecutor registers essential components (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution)
5. **Coordinated Execution** (for each remaining task):
   - Phase 1: Static analysis data loading (outside emulator)
   - Phase 2: Coverage tracker initialization (outside emulator)
   - Phase 3: Emulator session with tool execution (inside emulator context)
6. **Result Processing**: `_process_results()` calls `task_storage.get_completed_tasks()` to collect ALL completed tasks across all sessions (previous + current), then passes them to ResultProcessorComponent for CSV/JSON generation
7. **Summary Generation**: `_generate_summary()` includes `_skipped_count` in the experiment summary

### Key Components

| Component | Purpose |
|-----------|---------|
| `Platform` | Main entry point - orchestrates task generation and execution |
| `TaskExecutor` | Component-based task execution with lifecycle management |
| `EmulatorComponent` | Manages emulator lifecycle, app installation, dynamic port allocation |
| `CoverageComponent` | Coverage tracker initialization and result processing |
| `StaticAnalysisComponent` | Loads static analysis data (GATOR, GESDA, REACH) for tasks |
| `LogcatComponent` | Logcat capture and filtering during task execution |
| `ToolExecutionComponent` | Tool invocation and result processing |
| `ResultProcessorComponent` | Generates CSV/JSON output files from completed tasks |
| `PerformanceProcessorComponent` | Generates task execution timing CSV |
| `TaskStorage` | Persistent task storage with atomic operations and transaction support |
| `PlatformConfig` | Configuration schema with Pydantic validation |

## Directory Structure

```
src/rv_platform/
    __init__.py              # External tool registration (rvagent, aperv)
    __main__.py              # CLI entry point with subcommands
    platform.py              # Main Platform class
    config/
        __init__.py
        platform_config.py   # PlatformConfig model (ToolConfig imported from rv-android-core)
    execution/
        __init__.py
        executor.py          # TaskExecutor with component-based architecture
    components/
        __init__.py
        coverage.py          # Coverage tracking component
        emulator.py          # Emulator lifecycle management
        logcat.py            # Logcat capture component
        performance_processor.py  # Performance metrics processing
        result_processor.py  # CSV/JSON result generation
        static_analysis.py   # Static analysis data loading
        tool_execution.py    # Tool invocation component
    interfaces/
        __init__.py
        task_interfaces.py   # ITaskComponent, ITaskExecutor, ITaskStorage interfaces
    storage/
        __init__.py
        task_storage.py      # TaskStorage with transactions and experiment metadata
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `platform.py` | Main Platform class - task generation, execution orchestration | 571 |
| `execution/executor.py` | TaskExecutor - component coordination and lifecycle | 511 |
| `storage/task_storage.py` | TaskStorage - persistent storage with transactions | 852 |
| `components/result_processor.py` | Result processing - CSV/JSON generation | 802 |
| `__main__.py` | CLI entry point with run, list-tools, validate-config commands | 498 |
| `components/coverage.py` | Coverage tracker lifecycle management | 334 |
| `components/performance_processor.py` | Task execution timing CSV generation | 151 |
| `interfaces/task_interfaces.py` | Core interfaces (ITaskComponent, ITaskExecutor, ITaskStorage) | 269 |
| `components/static_analysis.py` | Static analysis file copying and loading | 249 |
| `components/emulator.py` | Emulator startup and app installation | 241 |
| `config/platform_config.py` | PlatformConfig with Pydantic validation | 223 |
| `components/tool_execution.py` | Tool invocation and error handling | 171 |
| `components/logcat.py` | Logcat capture component | 179 |

## Dependencies

### Internal (rv-android modules)

- **rv-android-core**: Domain models (Task, App), ErrorHandler, LoggingManager
- **rv-tools**: ToolFactory, ToolRegistry for tool creation and discovery
- **rv-coverage**: CoverageTracker, logcat_parser for coverage analysis
- **rv-static-analysis**: static_analysis_parser for loading GATOR/GESDA/REACH data
- **rvagent-tool**: RVAgentTool for LLM-driven testing (registered on import)
- **aperv-tool**: ApeRVTool for APE-based exploration (registered on import)

### External

- **pydantic** (^2.9.0): Configuration validation and serialization
- **pandas** (^2.3.1): Data processing support

## Testing

```bash
cd modules/rv-platform

# Run all tests with coverage
PYTHONPATH=../rv-android-core/src:../rv-tools/src:../rv-coverage/src:../rv-static-analysis/src:src uv run pytest tests/ -v

# Run specific test category
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src uv run pytest tests/components/ -v
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src uv run pytest tests/execution/ -v
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src uv run pytest tests/config/ -v
```

### Test Structure

```
tests/
    __init__.py
    test_platform.py                # Platform-level tests
    components/
        __init__.py
        test_coverage.py            # CoverageComponent tests
        test_emulator.py            # EmulatorComponent tests
        test_logcat.py              # LogcatComponent tests
        test_result_processor.py    # ResultProcessorComponent tests
        test_static_analysis.py     # StaticAnalysisComponent tests
        test_tool_execution.py      # ToolExecutionComponent tests
    config/
        test_platform_config.py     # PlatformConfig validation tests
    execution/
        __init__.py
        test_executor.py            # TaskExecutor tests
        test_resume.py              # Resume and result consolidation tests
        test_resume_integration.py  # Resume integration tests
    storage/
        __init__.py
        test_task_storage.py        # TaskStorage tests
    manual_tests/
        debug_executor.py
```

## Common Tasks

### Run Platform via CLI

```bash
# Basic execution with monkey tool
uv run rv-platform run --tools monkey --apks-dir ./apks_examples

# Multiple tools with variants
uv run rv-platform run --tools monkey,droidbot --apks-dir ./apks_examples --repetitions 3

# With custom timeout and headless mode
uv run rv-platform run --tools rvagent:pure_algorithm --apks-dir ./apks --timeout 600 --no-window

# Skip result processing (for debugging)
uv run rv-platform run --tools monkey --apks-dir ./apks --skip-result-processing

# Process existing results (standalone mode)
uv run rv-platform run --process-results ./results/experiment_dir
```

### List Available Tools

```bash
# List all registered tools
uv run rv-platform list-tools

# With detailed information (variants, capabilities)
uv run rv-platform list-tools --detailed
```

### Generate Configuration Templates

```bash
# Basic configuration template
uv run rv-platform config --template-type basic --output basic_config.json

# Advanced configuration template
uv run rv-platform config --template-type advanced --output advanced_config.json
```

### Validate Configuration

```bash
uv run rv-platform validate-config my_config.json
```

### Use Platform Programmatically

```python
from rv_platform.platform import Platform
from rv_platform.config.platform_config import PlatformConfig
from rv_android_core.domain.task import ToolConfig

# Create configuration
config = PlatformConfig(
    apks_dir="./apks_examples",
    tools=[
        ToolConfig(name="monkey", variant="default", parameters={"event_count": 1000})
    ],
    repetitions=1,
    timeouts=[300],
    results_dir="./results/my_experiment",
    no_window=True,
    log_level="INFO"
)

# Create and run platform
platform = Platform(config)
results = platform.run()

# Access task objects directly
tasks = platform.get_tasks()
```

## Output Files

The platform generates the following output files in the results directory:

| File | Description |
|------|-------------|
| `coverage.csv` | Per-method coverage data with timing and progressive metrics |
| `errors.csv` | Monitored operations violations with timing and context |
| `summary.csv` | Aggregate metrics per task (activities, methods, MOP coverage, errors) |
| `results.json` | Hierarchical JSON with complete experiment data |
| `performance.csv` | Task execution timing and performance metrics |
| `tasks.json` | Task state persistence for experiment continuation (includes ExperimentMetadata with config_checksum and per-task `result`, including `logcat_file` — the resume path reconstructs coverage/MOP from the logcat + co-located SA JSON, not from the serialized `coverage_metrics`) |

## Experiment Resume

The platform supports resuming interrupted or expanding completed experiments through `TaskStorage`-backed persistence. When `tasks.json` exists from a previous run, the platform loads completed tasks, skips them, and executes only new/pending tasks. Results are consolidated across all sessions.

### Resume Forms

**Expand Experiment**: Run with more repetitions than the first run. The platform detects completed tasks by matching `(apk_name, name, variant, repetition, timeout)` identity and skips them. Only new tasks are executed.

**Crash Recovery**: Re-run the same command after an interruption. Completed tasks (persisted atomically to `tasks.json` after each task) are skipped. The interrupted task is re-executed from scratch.

### Resume Flow in Platform.run()

1. `_generate_tasks()` creates all tasks for the current configuration
2. `ExperimentMetadata` is created with a SHA-256 `config_checksum` from `PlatformConfig`
3. `_skip_completed_tasks()` loads completed tasks from `TaskStorage`, matches by `(apk_name, name, variant, repetition, timeout)` identity tuple, and removes matches from the execution list. The `_skipped_count` is stored for summary reporting
4. If the config checksum differs from the previous run, a WARNING is logged in `platform.py` with the first 8 hex chars of each checksum (stored checksum vs current). `TaskStorage` logs at DEBUG level
5. Only remaining tasks are executed
6. `_process_results()` uses `task_storage.get_completed_tasks()` which returns ALL tasks with COMPLETED state from all sessions (previous + current). These are passed to ResultProcessorComponent for unified CSV/JSON generation

### Coverage + MOP Reconstruction from Logcat on Resume

Tasks loaded from `tasks.json` have `repository=None` because the in-memory `LogcatRepository` is not serialized. `ResultProcessorComponent` detects this and calls `_reconstruct_repository_from_logcat(task)`, which re-reads `task.result.logcat_file` and re-parses the co-located static-analysis JSON on demand (`_resolve_static_data`) so the reconstructed repository carries **both** per-method coverage AND MOP violations — equivalent to the live path. The four reconstruction call sites are `_write_task_coverage_data()`, `_write_task_error_data()`, `_write_task_summary_data()`, and `_extract_task_data()`.

`_resolve_static_data` derives the per-APK directory from `os.path.dirname(task.result.logcat_file)` when `task.results_dir` is empty — which it always is on resume, because `Task.to_dict` serializes only `id/config/result` and `from_dict` leaves `results_dir=""`/`app=None` (gh65). At runtime `task.results_dir == os.path.dirname(logcat_file)` and the SA JSON is co-located with the logcat, so the derived path resolves both. The parser is called with `code_package=None` (app is `None` on resume); GATOR already pre-filtered `reachability[]` to app classes, so no class filter is needed.

No fallback to serialized `task.result.coverage_metrics` (INV-PLT-16): a serialized fallback would populate `summary.csv` `cov_*` while `coverage.csv` (per-method rows, only producible from a populated repository) stays empty — the `summary != 0 with coverage_rows = 0` inconsistency `verify.py` C3 flags. When the logcat is present but the JSON is genuinely absent, both writers emit a **zeroed coverage row** (errors still accurate — `calculate_metrics` counts them before the empty-`classes` early return) and the task is counted once in `_unresolved_task_ids`; `execute()` surfaces the aggregate as one `N/M` resume health-check WARNING (INV-PLT-18). When the logcat itself is missing, no coverage row is emitted.

### Key Fields

- `Platform._skipped_count`: Number of tasks skipped from previous runs (used in summary)
- `TaskResult.logcat_file`: Path to persisted logcat file (serialized in `tasks.json`; the resume path derives `results_dir` from its dirname and resolves the co-located SA JSON)
- `ResultProcessorComponent._unresolved_task_ids`: per-pass set of task IDs whose SA JSON could not be resolved; `len(...)` is the `N` in the resume health-check WARNING (re-initialized each `execute()`)

## Important Notes

- **Parallel Execution**: EmulatorComponent supports dynamic port allocation for parallel task execution
- **Timeout Handling**: Tool timeouts are considered successful completion (expected behavior)
- **Static Analysis**: Static analysis loading is non-critical - execution continues without it. Uses `app.code_package` (detected implementation package) instead of `app.package_name` (manifest) for correct class filtering
- **APK Installation**: EmulatorComponent raises `EmulatorError` if APK installation fails (checked via `CommandResult.is_failure()`). TaskExecutor catches this and marks the task as FAILED
- **Result Processing**: Can be skipped during execution and run standalone later
- **Task Continuation**: TaskStorage supports experiment continuation via config checksum validation


## Development Notes

This module is part of the RV-Android uv workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `uv sync` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
uv sync             # Install/update all modules (also removes unused packages)
```

