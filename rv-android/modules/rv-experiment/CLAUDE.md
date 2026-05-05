# CLAUDE.md - rv-experiment

This file provides guidance for working with the rv-experiment module.

## Module Overview

**rv-experiment** is the experiment orchestration and coordination system for the RV-Android framework. It provides the primary CLI interface and three-phase workflow for executing Android testing experiments with runtime verification monitors.

### Key Responsibilities

- **CLI Interface**: Primary entry point for experiment execution (`rv-experiment` command)
- **Experiment Orchestration**: Three-phase workflow (pre-processing, execution, post-processing)
- **Configuration Management**: Type-safe experiment configuration with Pydantic validation
- **Module Coordination**: Delegates execution to rv-platform while managing pre/post processing

### Architectural Principles

- **Clean Separation**: rv-experiment handles orchestration only; rv-platform handles execution
- **No Data Transfer**: Results stay in rv-platform; rv-experiment provides coordination
- **Just-in-Time Configuration**: Sub-module configurations created only when needed


## Directory Structure

```
modules/rv-experiment/
├── src/rv_experiment/
│   ├── __main__.py              # CLI entry point with Click commands
│   ├── config.py                # ExperimentConfig Pydantic model
│   ├── constants.py             # Directory paths and defaults
│   ├── experiment/
│   │   ├── experiment_controller.py    # Main orchestration controller
│   │   └── workflow/
│   │       ├── workflow_factory.py     # Factory for workflow components
│   │       ├── pre_processor.py       # Monitor generation, APK instrumentation, static analysis
│   │       ├── execution_controller.py # rv-platform coordination
│   │       ├── post_processor.py      # Basic diagnostics only
│   │       └── result_manager.py      # Instrumentation error tracking
│   └── factories/
│       └── configuration_factory.py    # Factory pattern for configurations
└── tests/
    ├── conftest.py
    ├── helpers.py
    ├── experiment/
    │   ├── test_execution_controller.py  # ExecutionController tests
    │   ├── test_experiment_controller.py  # ExperimentController tests
    │   ├── test_post_processor.py         # Post-processor tests
    │   ├── test_resume_experiment.py      # Resume experiment tests
    │   └── test_workflow_factory.py       # WorkflowFactory tests
    ├── test_config_jit.py                 # JIT configuration tests
    ├── test_config_json.py                # JSON serialization tests
    ├── test_config_validation.py          # Validation tests
    ├── test_configuration_factory.py      # Factory tests
    ├── test_configuration_factory_methods.py  # Factory method tests
    ├── test_constants.py                  # Constants tests
    ├── test_post_processor.py             # Post-processing tests
    └── test_resume_cli.py                 # Resume CLI tests
```

## CLI Commands

### Run Experiments
```bash
# Basic execution with default tools
rv-experiment run --tools monkey

# Multiple tools with variants
rv-experiment run --tools monkey,droidbot:dfs_greedy

# With specification set and parameters
rv-experiment run --tools rvagent:multimode@temperature=0.3 --specification-set jca

# From configuration file
rv-experiment run --config experiment_config.json

# Full example with all options
rv-experiment run \
  --tools monkey,droidbot:dfs_greedy \
  --timeout 600 \
  --repetitions 3 \
  --apks-dir ./apks/ \
  --specification-set jca \
  --generate-monitors \
  --instrument-apks \
  --static-analysis
```

### Generate Configuration Templates
```bash
# Basic template
rv-experiment config --template-type basic --output basic_config.json

# Advanced template with multiple tools
rv-experiment config --template-type advanced --output advanced_config.json

# Research template with statistical rigor
rv-experiment config --template-type research --output research_config.json
```

### List Available Tools
```bash
# Show all tools
rv-experiment list-tools

# Show detailed information with variants
rv-experiment list-tools --detailed

# Filter by category
rv-experiment list-tools --filter-by basic --detailed
```

### Validate Configuration
```bash
rv-experiment validate experiment_config.json
```

## Tool Specification DSL

Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`

Examples:
- `monkey` - Basic tool usage
- `droidbot:dfs_greedy` - Tool with variant
- `rvagent:multimode` - Tool with variant
- `rvagent:multimode@temperature=0.3` - Tool with parameters
- `monkey,droidbot:dfs_greedy,ape` - Multiple tools (comma-separated)

## Three-Phase Workflow

### Phase 1: Pre-Processing (PreProcessor)
- **Monitor Generation**: Creates JavaMOP/RV-Monitor monitors from specification files
- **APK Instrumentation**: Instruments APKs with runtime verification monitors. Variant
  selection (`ajc` vs `dexlib2`) flows through the canonical
  `rv_instrumentation.get_instrumenter(variant, config)` factory (INV-INS-36) — the
  PreProcessor does not import variant impls directly. Both variants implement the
  `Instrumenter` ABC defined in `rv-instrumentation-core`. (Closes gh52 task §15.4 —
  CLAUDE.md now documents the multi-variant architecture without anticipating the
  default flip.)
- **Static Analysis**: Runs GATOR, GESDA, REACH analysis on APKs

### Phase 2: Execution (ExecutionController)
- Creates PlatformConfig from ExperimentConfig
- Delegates to rv-platform for task execution
- rv-platform handles all task execution and result processing
- No data transfer back to rv-experiment

### Phase 3: Post-Processing (PostProcessor)
- Generates instrumentation errors JSON
- Creates completion diagnostics
- Publishes experiment completion events
- Note: CSV/JSON results handled by rv-platform

## Configuration (ExperimentConfig)

### Core Fields
```python
ExperimentConfig(
    name="experiment_name",
    description="Experiment description",

    # Tool configuration
    tool_configs=[
        ToolConfig(name="monkey"),
        ToolConfig(name="droidbot", variant="dfs_greedy"),
    ],

    # Execution parameters
    repetitions=3,
    timeouts=[300, 600],
    no_window=True,

    # Pre-processing flags
    generate_monitors=True,
    instrument_apks=True,
    run_static_analysis=True,

    # Specification set (jca, generic, custom)
    specification_set="jca",
    custom_specs_dir=None,  # Required for "custom"

    # Directories
    apks_dir="./apks_examples/",
    output_dir="./out/",
    results_dir="./results/",
)
```

### Just-in-Time Configuration Methods
```python
config = ExperimentConfig(...)

# Get monitor generation config (rv-monitor-generator)
monitor_config = config.get_monitored_operations_config()

# Get instrumentation config (rv-instrumentation)
instr_config = config.get_instrumentation_config()

# Get static analysis config (rv-static-analysis)
static_config = config.get_static_analysis_config()

# Generic dispatch by module name (returns empty dict for unknown modules)
module_config = config.get_module_config("rv-instrumentation")
```

## Directory Constants

```python
RESULTS_DIR = "results"              # Experiment results
INSTRUMENTED_DIR = "out"             # Temporary artifacts
MONITORS_DIR = "monitors"            # Generated monitors
INSTRUMENTED_APKS_DIR = "instrumented_apks"
STATIC_ANALYSIS_DIR = "static_analysis"
DEFAULT_APKS_DIR = "apks_examples"
DEFAULT_TIMEOUT = 300
DEFAULT_REPETITIONS = 1
DEFAULT_SPEC_SET = "jca"
```

## Tool Registration

External tools (e.g., rvagent) are registered by rv-platform on import. rv-experiment uses the standard `ToolRegistry` from rv-tools to access all available tools:

```python
from rv_tools import ToolRegistry

registry = ToolRegistry.get_instance()
tools = registry.get_all_tools()
variants = registry.get_tool_variants("rvagent")
```

## Integration with rv-platform

rv-experiment creates a PlatformConfig and delegates execution:

```python
# ExecutionController creates platform configuration
platform_config = PlatformConfig(
    apks_dir=instrumented_apks_dir,
    tools=platform_tools,
    repetitions=repetitions,
    timeouts=timeouts,
    results_dir=results_dir,
    no_window=no_window,
)

# Platform handles execution and results
platform = Platform(platform_config)
results = platform.run()
```

## Environment Variables

- `RVSEC_HOME`: Required for monitor generation and instrumentation tools
- `ANDROID_HOME`: Required for APK processing and emulator management

## Testing

```bash
cd modules/rv-experiment

# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/experiment/test_experiment_controller.py -v

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Common Development Tasks

### Adding a New Tool
1. Create tool class in appropriate module (e.g., rvagent-tool)
2. Add the module dependency to `rv-platform/pyproject.toml`
3. Register in `rv-platform/src/rv_platform/__init__.py` via `_register_external_tools()`

### Creating Custom Configuration
```python
from rv_experiment.config import ExperimentConfig
from rv_android_core.domain.task import ToolConfig

config = ExperimentConfig(
    name="custom_experiment",
    tool_configs=[
        ToolConfig(name="monkey", parameters={"seed": 42}),
        ToolConfig(name="droidbot", variant="dfs_greedy"),
    ],
    specification_set="jca",
    apks_dir="./my_apks/",
)

# Run experiment
from rv_experiment.experiment.experiment_controller import execute_with_config
success = execute_with_config(config)
```

### Using Configuration Factory
```python
from rv_experiment.factories.configuration_factory import ConfigurationFactory

factory = ConfigurationFactory()

# Create from tool specifications
tools = factory.parse_tool_specifications(["monkey", "droidbot:dfs_greedy"])
config = factory.create_cli_config(tools=tools, timeout=600)

# Create templates
basic = factory.create_basic_template()
advanced = factory.create_advanced_template()
llm_config = factory.create_llm_template()
```

## Specification Sets

rv-experiment supports three specification sets for runtime verification:

1. **JCA (Java Cryptography Architecture)**: Monitors JCA API usage patterns
   - Location: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`

2. **Generic**: Monitors general programming patterns (Iterator, Collections, etc.)
   - Location: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/`

3. **Custom**: User-defined specification sets
   - Requires `--custom-specs-dir` pointing to directory with `.mop` files

## Experiment Resume

rv-experiment supports resuming interrupted or expanding completed experiments through two mechanisms:

- **`--name`** (implicit resume): When `results/<name>/tasks.json` exists, resume mode activates automatically
- **`--resume-dir`** (explicit resume): Points directly to a results directory containing `tasks.json`; overrides `--name`

### Resume Invariants

**Auto-skip pre-processing**: On resume, all pre-processing flags (`generate_monitors`, `instrument_apks`, `run_static_analysis`) are forced to `False` regardless of CLI values, disabling all pre-processing phases. This prevents redundant monitor generation, instrumentation, and static analysis when resuming an experiment that already completed pre-processing.

**Flat results directory**: ExperimentController uses `config.results_dir` directly as the output location. There is no subdirectory nesting — all results for an experiment live in a single flat directory (e.g., `results/my_exp/`).

### Resume Behavior

When resume mode is active:
1. `ExperimentConfig.resume_mode` is set to `True`
2. All pre-processing flags are forced to `False` (auto-skip)
3. rv-platform loads completed tasks from `tasks.json` and skips them
4. Only new/pending tasks are executed
5. Results are consolidated across all sessions (including MOP violation reconstruction from logcat for resumed tasks)

### Resume Forms

**Expand Experiment** (add repetitions):
```bash
# First run: 1 repetition
rv-experiment run --tools ape --apks-dir ./apks_examples --name my_exp --repetitions 1

# Resume with more repetitions: skips rep 1, executes rep 2
rv-experiment run --tools ape --apks-dir ./apks_examples --name my_exp --repetitions 2
```

**Crash Recovery** (re-run same command):
```bash
# Re-run after interruption: skips completed tasks, executes remaining
rv-experiment run --tools ape --apks-dir ./apks_examples --name my_exp --repetitions 3
```

**Resume from specific directory**:
```bash
rv-experiment run --tools ape --apks-dir ./apks_examples --resume-dir ./results/my_exp
```

## Docker Execution Mode

rv-experiment runs inside Docker containers via `docker/rvandroid/docker-entrypoint.sh`, which translates environment variables to CLI arguments. This enables declarative experiment configuration through Docker Compose or `docker run`.

### Key Environment Variables

| Variable | CLI Argument | Description |
|----------|--------------|-------------|
| `RV_TOOLS` | `--tools` | Tool specification DSL |
| `RV_TIMEOUTS` | `--timeout` | Execution timeout (seconds) |
| `RV_REPETITIONS` | `--repetitions` | Number of repetitions |
| `RV_APKS_DIR` | `--apks-dir` | APK directory path |
| `RV_NO_WINDOW` | `--no-window / --window` | Emulator headless mode |
| `RV_SPEC_SET` | `--specification-set` | Specification set name |
| `RV_SKIP_MONITORS` | `--skip-monitors` | Skip monitor generation |
| `RV_SKIP_INSTRUMENT` | `--skip-instrument` | Skip APK instrumentation |
| `RV_SKIP_STATIC_ANALYSIS` | `--skip-static` | Skip static analysis |
| `RV_SKIP_EXECUTION` | `--skip-execution` | Skip task execution phase (preprocessing-only mode) |
| `RV_DEVICE_PORT` | `--device-port` | Emulator port |
| `RV_APKS_FILTER` | `--apks-filter` | APK filter file |
| `RV_EXPERIMENT_NAME` | `--name` | Experiment name (enables implicit resume) |
| `RV_RESUME_DIR` | `--resume-dir` | Explicit resume directory |
| `RV_DEBUG` | `--debug` | Debug logging |
| `RV_DELAY` | (startup delay) | Stagger parallel container launches |

The entrypoint supports interactive mode: pass `bash` or `shell` as the first argument to get a shell instead of running the experiment.

## Key Design Decisions

### No Data Transfer Between Modules
- rv-experiment provides orchestration only
- rv-platform handles all task execution and result processing
- Results stay in platform layer; experiment layer only tracks metadata

### Just-in-Time Configuration
- Sub-module configurations created only when accessed
- Reduces initialization overhead
- Enables lazy validation

### Factory Pattern for Configuration
- ConfigurationFactory provides clean creation methods
- Eliminates complex coordination patterns
- Supports both CLI and programmatic usage


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

