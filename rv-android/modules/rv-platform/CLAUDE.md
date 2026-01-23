# CLAUDE.md - rv-platform

## Purpose

rv-platform is the central execution engine for Android testing experiments in the RV-Android framework. It orchestrates task generation from APK discovery, manages task execution through a component-based architecture, coordinates emulator lifecycle and tool execution, and processes results into standardized CSV/JSON output files. The platform provides a clean separation between experiment orchestration (rv-experiment) and the actual task execution mechanics, enabling both standalone usage via CLI and integration as a service within larger experiment workflows.

## Architecture

### Key Patterns and Design Decisions

- **Component-Based Execution**: TaskExecutor uses pluggable components (EmulatorComponent, CoverageComponent, etc.) for different execution phases with initialize/execute/cleanup lifecycle
- **Event-Driven Communication**: Integrates with rv-android-core's EventBus for publishing task lifecycle events (started, completed, failed)
- **Coordinated Component Execution**: Components execute in specific phases - static analysis and coverage initialization outside emulator session, tool execution inside emulator context
- **Persistent Task Storage**: TaskStorage provides atomic file operations with transaction support for robust task state persistence
- **Pydantic Configuration**: PlatformConfig uses Pydantic for validation with comprehensive field validators
- **Error Handler Integration**: ErrorHandler decorator pattern for consistent error management across all components

### Execution Flow

1. **Task Generation**: Platform discovers APKs, generates tasks for each APK/tool/variant/repetition/timeout combination
2. **Component Registration**: TaskExecutor registers essential components (StaticAnalysis, Emulator, Logcat, Coverage, ToolExecution)
3. **Coordinated Execution**:
   - Phase 1: Static analysis data loading (outside emulator)
   - Phase 2: Coverage tracker initialization (outside emulator)
   - Phase 3: Emulator session with tool execution (inside emulator context)
4. **Result Processing**: ResultProcessorComponent generates coverage.csv, errors.csv, summary.csv, results.json, performance.csv

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
| `PerformanceProcessorComponent` | Generates performance metrics CSV |
| `TaskStorage` | Persistent task storage with atomic operations and transaction support |
| `PlatformConfig` | Configuration schema with Pydantic validation |

## Directory Structure

```
src/rv_platform/
    __init__.py
    __main__.py              # CLI entry point with subcommands
    platform.py              # Main Platform class
    config/
        __init__.py
        platform_config.py   # PlatformConfig and ToolConfig models
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
| `platform.py` | Main Platform class - task generation, execution orchestration | 419 |
| `execution/executor.py` | TaskExecutor - component coordination and lifecycle | 483 |
| `storage/task_storage.py` | TaskStorage - persistent storage with transactions | 740 |
| `components/result_processor.py` | Result processing - CSV/JSON generation | 607 |
| `__main__.py` | CLI entry point with run, list-tools, validate-config commands | 473 |
| `components/coverage.py` | Coverage tracker lifecycle management | 353 |
| `components/performance_processor.py` | Performance metrics CSV generation | 325 |
| `interfaces/task_interfaces.py` | Core interfaces (ITaskComponent, ITaskExecutor, ITaskStorage) | 267 |
| `components/static_analysis.py` | Static analysis file copying and loading | 231 |
| `components/emulator.py` | Emulator startup and app installation | 223 |
| `config/platform_config.py` | PlatformConfig with Pydantic validation | 192 |
| `components/tool_execution.py` | Tool invocation and error handling | 175 |
| `components/logcat.py` | Logcat capture component | 168 |

## Dependencies

### Internal (rv-android modules)

- **rv-android-core**: Domain models (Task, App), EventBus, ErrorHandler, LoggingManager, PerformanceMonitor
- **rv-tools**: ToolFactory, ToolRegistry for tool creation and discovery
- **rv-coverage**: CoverageTracker, logcat_parser for coverage analysis
- **rv-static-analysis**: static_analysis_parser for loading GATOR/GESDA/REACH data

### External

- **pydantic** (^2.9.0): Configuration validation and serialization
- **pandas** (^2.3.1): Data processing support

## Testing

```bash
cd modules/rv-platform

# Run all tests with coverage
PYTHONPATH=../rv-android-core/src:../rv-tools/src:../rv-coverage/src:../rv-static-analysis/src:src poetry run pytest tests/ -v

# Run specific test category
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src poetry run pytest tests/components/ -v
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src poetry run pytest tests/execution/ -v
PYTHONPATH=../rv-android-core/src:../rv-tools/src:src poetry run pytest tests/config/ -v
```

### Test Structure

```
tests/
    __init__.py
    components/
        __init__.py
        test_tool_execution.py
    config/
        test_platform_config.py
    execution/
        __init__.py
        test_executor.py
    manual_tests/
        debug_executor.py
```

## Common Tasks

### Run Platform via CLI

```bash
# Basic execution with monkey tool
poetry run rv-platform run --tools monkey --apks-dir ./apks_examples

# Multiple tools with variants
poetry run rv-platform run --tools monkey,droidbot --apks-dir ./apks_examples --repetitions 3

# With custom timeout and headless mode
poetry run rv-platform run --tools rvandroid:vision --apks-dir ./apks --timeout 600 --no-window

# Skip result processing (for debugging)
poetry run rv-platform run --tools monkey --apks-dir ./apks --skip-result-processing

# Process existing results (standalone mode)
poetry run rv-platform run --process-results ./results/experiment_dir
```

### List Available Tools

```bash
# List all registered tools
poetry run rv-platform list-tools

# With detailed information (variants, capabilities)
poetry run rv-platform list-tools --detailed
```

### Generate Configuration Templates

```bash
# Basic configuration template
poetry run rv-platform config --template-type basic --output basic_config.json

# Advanced configuration template
poetry run rv-platform config --template-type advanced --output advanced_config.json
```

### Validate Configuration

```bash
poetry run rv-platform validate-config my_config.json
```

### Use Platform Programmatically

```python
from rv_platform.platform import Platform
from rv_platform.config.platform_config import PlatformConfig, ToolConfig

# Create configuration
config = PlatformConfig(
    apks_dir="./apks_examples",
    tools=[
        ToolConfig(name="monkey", variants=[], parameters={"event_count": 1000})
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
| `tasks.json` | Task state persistence for experiment continuation |

## Important Notes

- **Parallel Execution**: EmulatorComponent supports dynamic port allocation for parallel task execution
- **Timeout Handling**: Tool timeouts are considered successful completion (expected behavior)
- **Static Analysis**: Static analysis loading is non-critical - execution continues without it
- **Result Processing**: Can be skipped during execution and run standalone later
- **Task Continuation**: TaskStorage supports experiment continuation via config checksum validation
