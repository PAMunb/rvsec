# RV-Experiment Module

Experiment orchestration system for monitored operations testing in Android applications.

## Overview

rv-experiment orchestrates the complete experiment lifecycle for the RV-Android framework: APK instrumentation, static analysis, task execution (via rv-platform), and result processing. It provides the primary CLI interface for running experiments.

### Key Capabilities

- Three-phase workflow: pre-processing, execution, post-processing
- Tool specification DSL (`tool:variant@param=value`)
- APK instrumentation with runtime verification monitors
- Static analysis generation (GATOR, GESDA, REACH)
- Parallel execution support (multiple emulators)
- APK filtering for subset execution
- Coordination with rv-platform for task execution

## Installation

```bash
# From the project root (uv workspace)
uv sync
```

## CLI Commands

### run

Execute experiments with tool specification parsing or configuration files.

```bash
uv run rv-experiment run [OPTIONS]
```

**Core options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--tools, -t` | `monkey` | Comma-separated tools with variants and parameters |
| `--config, -c` | — | Configuration file path (JSON) |
| `--timeout` | 300 | Execution timeout per APK in seconds |
| `--repetitions, -r` | 1 | Number of repetitions |
| `--apks-dir, -a` | `./apks_examples/` | Directory containing APK files |
| `--specification-set` | `jca` | Specification set: `jca`, `generic`, `custom` |
| `--output-dir` | auto-generated | Output directory for results |
| `--name` | auto-generated | Experiment name. When `results/<name>/tasks.json` exists, auto-enables resume |
| `--resume-dir` | — | Resume from a specific results directory (overrides `--name`) |

**Pre-processing flags:**

| Option | Default | Description |
|--------|---------|-------------|
| `--generate-monitors / --skip-monitors` | enabled | Generate runtime verification monitors |
| `--instrument-apks / --skip-instrument` | enabled | Instrument APKs with monitors |
| `--static-analysis / --skip-static` | enabled | Run static analysis (GATOR, GESDA, REACH) |
| `--run-execution / --skip-execution` | enabled | Execute tasks after preprocessing |

**Note:** On resume (via `--name` with existing `tasks.json` or `--resume-dir`), all pre-processing flags are forced to disabled regardless of CLI values.

**Parallel execution options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--device-port` | 5554 | Emulator port for parallel execution |
| `--apks-filter` | — | Text file listing APK filenames to process (one per line) |
| `--no-window / --window` | headless | Run emulator in headless mode |

**Examples:**

```bash
# Basic experiment
uv run rv-experiment run --tools monkey --apks-dir ./apks_examples

# Multiple tools with variants
uv run rv-experiment run --tools monkey,droidbot:dfs_greedy --repetitions 3

# RVAgent with calibrated parameters
uv run rv-experiment run \
  --tools "rvagent:pure_algorithm@mop_direct_score=400,stochastic_probability=0.5" \
  --apks-dir ./data/calibration_dataset \
  --skip-monitors --skip-instrument --skip-static \
  --timeout 300

# Pre-processing only (no task execution)
uv run rv-experiment run \
  --tools monkey \
  --apks-dir ./apks \
  --specification-set jca \
  --skip-execution

# Parallel execution on specific emulator port
uv run rv-experiment run \
  --tools rvagent:pure_algorithm \
  --apks-dir ./data/instrumented_apks \
  --device-port 5556 \
  --name worker_1 \
  --skip-monitors --skip-instrument --skip-static

# Process only a subset of APKs
uv run rv-experiment run \
  --tools ape,fastbot \
  --apks-dir ./data/instrumented_apks \
  --apks-filter ./calibration_set.txt \
  --skip-monitors --skip-instrument --skip-static
```

### config

Generate configuration templates.

```bash
uv run rv-experiment config [template_type] [OPTIONS]

# Templates: basic, advanced, research
uv run rv-experiment config --template-type basic --output config.json
```

### list-tools

List available tools and variants.

```bash
uv run rv-experiment list-tools
uv run rv-experiment list-tools --detailed
```

### validate

Validate experiment configuration files.

```bash
uv run rv-experiment validate config.json
```

## Tool Specification DSL

Format: `tool[:variant][@param1=value1,param2=value2]`

| Example | Description |
|---------|-------------|
| `monkey` | Basic tool |
| `droidbot:dfs_greedy` | Tool with variant |
| `rvagent:pure_algorithm` | RVAgent in algorithm mode |
| `rvagent:multimode` | RVAgent in hybrid LLM/algorithm mode |
| `rvagent:pure_algorithm@mop_direct_score=400` | Tool with parameters |
| `monkey,ape,rvagent:pure_algorithm` | Multiple tools |

## Three-Phase Workflow

### Phase 1: Pre-Processing

- **Monitor Generation**: Creates JavaMOP/RV-Monitor monitors from specification files
- **APK Instrumentation**: Instruments APKs with runtime verification monitors
- **Static Analysis**: Runs GATOR (WTG), GESDA, REACH on APKs

Skippable with `--skip-monitors`, `--skip-instrument`, `--skip-static`.

### Phase 2: Execution

- Creates PlatformConfig and delegates to rv-platform
- rv-platform generates tasks from APK/tool combinations and executes them
- Results stored in `results/<experiment_name>/`

Skippable with `--skip-execution` (runs only pre-processing).

### Phase 3: Post-Processing

- Generates instrumentation error reports
- Creates completion diagnostics

## Experiment Resume

rv-experiment supports resuming interrupted or expanding completed experiments through two mechanisms:

- **`--name`** (implicit): When `results/<name>/tasks.json` exists, resume activates automatically
- **`--resume-dir`** (explicit): Points to a specific results directory; overrides `--name`

### Resume via `--name`

```bash
# First run: 1 repetition
uv run rv-experiment run --tools ape --name my_exp --repetitions 1

# Resume with 2 repetitions: skips rep 1, executes rep 2
uv run rv-experiment run --tools ape --name my_exp --repetitions 2

# Crash recovery: re-run same command, completed tasks are skipped
uv run rv-experiment run --tools ape --name my_exp --repetitions 3
```

### Resume via `--resume-dir`

For resuming from a specific directory (overrides `--name`):

```bash
uv run rv-experiment run --tools ape --apks-dir ./apks_examples --resume-dir ./results/my_exp
```

### Resume Behavior

- **Auto-skip pre-processing**: On resume, all pre-processing flags (`generate_monitors`, `instrument_apks`, `run_static_analysis`) are forced to `False` regardless of CLI values, disabling all pre-processing phases
- **Flat results directory**: ExperimentController uses `config.results_dir` directly as the output location with no subdirectory nesting
- **Task persistence**: Completed tasks (persisted in `tasks.json`) are skipped; only pending tasks execute
- **Result consolidation**: MOP violation data is reconstructed from persisted logcat files for resumed tasks, and results are consolidated across all sessions into unified CSV/JSON output files

## Parallel Execution

rv-experiment supports parallel execution via `--device-port` and `--apks-filter`. Each parallel instance gets its own emulator port, APK subset, and output directory.

Use `scripts/parallel_run.py` to orchestrate multiple instances:

```bash
python scripts/parallel_run.py \
  --tools ape,fastbot,rvagent:pure_algorithm \
  --apks-dir ./data/calibration_dataset \
  --n-emulators 6 \
  --timeout 300 \
  --output-base ./results/baseline \
  --skip-preprocessing
```

The script splits APKs across N workers via round-robin, creating separate filter files and output directories per worker.

## Reusing Pre-Processed Artifacts

When using `--skip-monitors`, `--skip-instrument`, or `--skip-static`, the `--apks-dir` must point to **instrumented APKs** from a previous run, not the original APKs directory.

```bash
# Step 1: Run full pre-processing
uv run rv-experiment run \
  --tools monkey \
  --apks-dir ./apks_examples \
  --specification-set jca \
  --skip-execution

# Step 2: Reuse instrumented APKs
uv run rv-experiment run \
  --tools rvagent:pure_algorithm \
  --apks-dir ./results/<experiment_id>/instrumented_apks \
  --skip-monitors --skip-instrument --skip-static
```

## Specification Sets

| Set | Description | Location |
|-----|-------------|----------|
| `jca` | JCA cryptography API monitoring | `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/` |
| `generic` | General programming patterns (Iterator, Collections) | `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/` |
| `custom` | User-defined specifications (requires `--custom-specs-dir`) | User-provided |

## Docker Execution Mode

rv-experiment runs inside Docker containers via `docker/rvandroid/docker-entrypoint.sh`, which translates environment variables into CLI arguments. This enables declarative experiment configuration through Docker Compose or `docker run` without modifying the container.

| Environment Variable | CLI Argument | Description |
|---------------------|--------------|-------------|
| `RV_TOOLS` | `--tools` | Tool specification (same DSL as CLI) |
| `RV_TIMEOUTS` | `--timeout` | Execution timeout in seconds |
| `RV_REPETITIONS` | `--repetitions` | Number of repetitions |
| `RV_APKS_DIR` | `--apks-dir` | APK directory path |
| `RV_NO_WINDOW` | `--no-window / --window` | Emulator headless mode (`true`/`false`) |
| `RV_SPEC_SET` | `--specification-set` | Specification set name |
| `RV_SKIP_MONITORS` | `--skip-monitors` | Skip monitor generation |
| `RV_SKIP_INSTRUMENT` | `--skip-instrument` | Skip APK instrumentation |
| `RV_SKIP_STATIC_ANALYSIS` | `--skip-static` | Skip static analysis |
| `RV_DEVICE_PORT` | `--device-port` | Emulator port for parallel execution |
| `RV_APKS_FILTER` | `--apks-filter` | APK filter file path |
| `RV_EXPERIMENT_NAME` | `--name` | Experiment name (enables implicit resume) |
| `RV_RESUME_DIR` | `--resume-dir` | Explicit resume directory |
| `RV_DEBUG` | `--debug` | Debug logging |
| `RV_DELAY` | (startup delay) | Seconds to wait before starting (for staggering parallel containers) |

Pass `bash` or `shell` as the container command for interactive access instead of running the experiment.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RVSEC_HOME` | For pre-processing | Path to RVSEC installation (monitors, instrumentation, static analysis) |
| `ANDROID_HOME` | Yes | Android SDK path for emulator management |

## Directory Structure

```
modules/rv-experiment/
├── src/rv_experiment/
│   ├── __main__.py                     # CLI entry point
│   ├── config.py                       # ExperimentConfig (Pydantic)
│   ├── constants.py                    # Default paths and values
│   ├── experiment/
│   │   ├── experiment_controller.py    # Three-phase orchestration
│   │   └── workflow/
│   │       ├── pre_processor.py        # Monitors, instrumentation, static analysis
│   │       ├── execution_controller.py # rv-platform coordination
│   │       ├── post_processor.py       # Diagnostics
│   │       └── result_manager.py       # Error tracking
│   └── factories/
│       └── configuration_factory.py    # Config creation
└── tests/
```

## Testing

```bash
uv run pytest modules/rv-experiment/tests/ -v
```

## Dependencies

- **rv-platform**: Task execution and result processing
- **rv-android-core**: Logging, error handling, domain models
- **rv-tools**: Tool registry and plugin system
- **rv-instrumentation**: APK instrumentation
- **rv-static-analysis**: GATOR, GESDA, REACH integration
- **rv-monitor-generator**: JavaMOP/RV-Monitor integration
