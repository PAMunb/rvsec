# RV-Android: Runtime Verification for Android Applications

A modular platform for Android application testing that integrates runtime verification (JavaMOP/RV-Monitor), static analysis, automated test generation, and LLM-guided exploration. Supports detection of both JCA (Java Cryptography Architecture) API misuses and general programming pattern violations through 168+ MOP specifications.

## Architecture Overview

RV-Android uses a uv workspace with 13 independent modules organized in four layers:

```
Experiment Orchestration:  rv-experiment, rv-agent-validation
LLM Testing:               rv-agent, rvagent-tool
Analysis and Processing:   rv-monitor-generator, rv-instrumentation, rv-static-analysis,
                           rv-coverage, rv-screen-parser
Core Infrastructure:       rv-android-core, rv-platform, rv-tools, rv-uiautomator
```

### Modules

| Module | Purpose |
|--------|---------|
| **rv-android-core** | Foundation infrastructure: domain models, error handling, logging |
| **rv-platform** | Central execution engine: task generation, component-based execution, result processing |
| **rv-tools** | Testing tool plugin system with registry and factory patterns |
| **rv-uiautomator** | Shared UIAutomator2 components for Android device interaction |
| **rv-monitor-generator** | JavaMOP/RV-Monitor integration for generating runtime verification monitors |
| **rv-instrumentation** | APK instrumentation with monitor and coverage aspect weaving |
| **rv-static-analysis** | Unified GATOR-based static analysis: reachability, windows, transitions |
| **rv-coverage** | Coverage analysis and tracking for monitored operations |
| **rv-screen-parser** | Android UI parsing with visitor patterns for state analysis |
| **rv-agent** | LLM-driven testing tool using Qwen3-VL vision model with LangGraph workflow |
| **rvagent-tool** | Bridge module registering rv-agent as a tool in the rv-tools plugin system |
| **rv-experiment** | Experiment orchestration: pre-processing, execution coordination, post-processing |
| **rv-agent-validation** | Validation framework for rv-agent calibration and benchmarking |

### Pipeline

The full experiment workflow consists of three phases:

1. **Pre-processing**: Monitor generation from MOP specs, APK instrumentation with monitors + coverage aspect, unified GATOR static analysis
2. **Execution**: Task generation (APK x tool x variant x repetition x timeout), emulator management, tool execution with logcat capture, coverage tracking
3. **Post-processing**: Result generation in CSV/JSON format (coverage, errors, summary, performance)

## Quick Start

### Prerequisites

- Python 3.12+
- Java 21+
- AspectJ 1.9.24
- Android SDK (with emulator and platform-tools)
- RVSEC environment (for monitor generation and instrumentation)

### Installation

```bash
# Set environment variables
export RVSEC_HOME="/path/to/rvsec"
export ANDROID_HOME="/path/to/android-sdk"

# Install all modules (uv workspace, editable mode)
cd rv-android
uv sync
```

All 13 modules are installed in editable mode via the root `pyproject.toml`. Source code changes are reflected immediately — no reinstall needed unless `pyproject.toml` dependencies change.

### Running Experiments

```bash
# Run experiment with Monkey tool
uv run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 300

# Run with multiple tools and DroidBot variant
uv run rv-experiment run --tools monkey,droidbot:dfs_greedy --timeout 600 --repetitions 3

# Run with rv-agent (LLM-driven testing)
uv run rv-experiment run --tools rvagent:multimode --apks-dir ./apks_examples --timeout 60

# Skip pre-processing (use pre-processed APKs from a previous run)
uv run rv-experiment run --tools monkey --apks-dir results/my_exp/instrumented_apks \
  --skip-monitors --skip-instrument --skip-static
```

## Testing Tools

RV-Android integrates 9 testing tools through a plugin system:

| Tool | Type | Description |
|------|------|-------------|
| **Monkey** | Random | Android's built-in random event generator |
| **DroidBot** | Model-based | DFS/BFS exploration with UI model (variants: `dfs_greedy`, `bfs_greedy`, `dfs_naive`) |
| **APE** | Model-based | Activity/Property Explorer with model-based exploration |
| **FastBot** | Model-based | Bytedance's high-speed fuzzing tool |
| **ARES** | RL-based | Reinforcement learning exploration (Docker-based) |
| **DroidMate** | Model-based | GUI-driven testing |
| **Humanoid** | DL-based | Deep learning model for human-like interaction (requires Humanoid server) |
| **QTesting** | RL-based | Reinforcement learning testing (Docker-based) |
| **rv-agent** | LLM-driven | Vision-language model exploration (variants: `pure_algorithm`, `llm_only`, `multimode`) |

### Tool Specification DSL

Tools are specified via a DSL: `tool_name[:variant][@param=value]`

```bash
# Simple tool
--tools monkey

# Tool with variant
--tools droidbot:dfs_greedy

# Tool with variant and parameters
--tools rvagent:multimode@temperature=0.3

# Multiple tools (comma-separated)
--tools monkey,droidbot:dfs_greedy,ape
```

## Specification Sets

MOP specifications define the runtime verification monitors woven into APKs. Each experiment uses one specification set — sets are never mixed within a single experiment.

| Set | Specs | Description |
|-----|-------|-------------|
| **JCA** | 23 | Java Cryptography Architecture monitors (Cipher, MessageDigest, SSLContext, SecretKeySpec, KeyGenerator, Signature, Mac, KeyStore, etc.). Derived from 23 CrySL rules validated by cryptography experts. |
| **Generic (FSM)** | 118 | General programming pattern monitors from JavaMOP's specification database (Iterator hasNext/next, stream closing, collection modification during iteration, etc.) |
| **Generic (new)** | 27 | Curated generic specifications with descriptive names (e.g., `Closeable_MeaninglessClose`, `Map_UnsafeIterator`, `InputStream_ManipulateAfterClose`) |
| **Custom** | User-defined | Any directory containing `.mop` specification files |

Specification source: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`

```bash
# JCA specifications (default)
uv run rv-experiment run --tools monkey --specification-set jca

# Generic FSM specifications
uv run rv-experiment run --tools monkey --specification-set generic

# Custom specification directory
uv run rv-experiment run --tools monkey --specification-set custom --custom-specs-dir /path/to/specs
```

## RV-Agent (LLM-Driven Testing)

RV-Agent uses a Vision Language Model (Qwen3-VL-4B-Instruct) served via SGLang to analyze device screenshots and interact with applications. It combines LLM semantic understanding with algorithmic exploration strategies.

### Execution Modes

| Mode | Description |
|------|-------------|
| `pure_algorithm` | DFS-based exploration using action ranking without LLM |
| `llm_only` | LLM decides all actions from screenshots |
| `multimode` | Hybrid: 70% LLM / 30% algorithm decisions (default) |

### Architecture

RV-Agent uses a LangGraph workflow: parse UI state from device, route decision to LLM or algorithm, validate the chosen action, execute on device, and learn from the result. Key features:

- **Stateless LLM context**: Fresh context each iteration (~2500 tokens) prevents context overflow
- **MOP-aware prioritization**: Prioritizes actions that reach monitored operations (from static analysis)
- **WTG-guided navigation**: Uses Window Transition Graph from GATOR for navigation
- **Hybrid tool calling**: Native `bind_tools()` with XML/JSON fallback for SGLang compatibility
- **Coordinate normalization**: Handles Qwen3-VL [0, 1000) coordinate space to device pixels

### Infrastructure Requirements

- SGLang inference server with Qwen3-VL-4B-Instruct (default endpoint: `http://192.168.0.36:30000/v1`)
- GPU with 16GB+ VRAM (tested on NVIDIA RTX 5070 Ti)
- bf16 precision (no quantization) for optimal quality

### Standalone Usage

```bash
# Requires: emulator running + APK installed
cd modules/rv-agent
uv run rv-agent run --package com.example.app --mode multimode --timeout 60

# Via rv-experiment (recommended — platform manages emulator and APK)
uv run rv-experiment run --tools rvagent:multimode --apks-dir ./apks_examples --timeout 60
```

## Experiment Resume

Experiments can be resumed after interruption or expanded with additional repetitions. Resume is backed by persistent task storage in `tasks.json`.

### Resume Modes

```bash
# Implicit resume via --name (resumes if results/<name>/tasks.json exists)
uv run rv-experiment run --tools monkey --name my_experiment --repetitions 3

# Explicit resume via --resume-dir
uv run rv-experiment run --tools monkey --resume-dir ./results/my_experiment
```

### Resume Behavior

- Completed tasks are loaded from `tasks.json` and skipped
- Pre-processing (monitor generation, instrumentation, static analysis) is auto-skipped on resume
- Results are consolidated across all sessions, including MOP violation reconstruction from logcat for resumed tasks
- Configuration checksum tracks whether the experiment config has changed between runs

### Expanding Experiments

```bash
# First run: 1 repetition
uv run rv-experiment run --tools ape --name exp1 --repetitions 1

# Expand: adds repetition 2 (repetition 1 is skipped)
uv run rv-experiment run --tools ape --name exp1 --repetitions 2
```

## Docker Deployment

RV-Android runs inside Docker containers with a 4-layer image chain:

| Layer | Image | Purpose |
|-------|-------|---------|
| 1 | `phtcosta/rvandroid_base` | Java 8, Python 3.10, uv (Ubuntu 22.04) |
| 2 | `phtcosta/rvandroid_android` | Android SDK, emulator (API 25 x86), KVM support |
| 3 | `phtcosta/rvandroid_tools` | DroidBot, APE, FastBot, Docker CLI |
| 4 | `phtcosta/rvandroid:0.8.0` | Full RV-Android framework |

### Running with Docker

The entrypoint (`docker-entrypoint.sh`) translates environment variables to `rv-experiment run` CLI arguments:

```bash
docker run --privileged \
  -e RV_TOOLS=monkey \
  -e RV_TIMEOUTS=300 \
  -e RV_SPEC_SET=jca \
  -e RV_EXPERIMENT_NAME=batch_01 \
  -v ./results:/app/results \
  phtcosta/rvandroid:0.8.0
```

### Parallel Execution

Docker Compose supports parallel containers with YAML anchors. Each container gets its own experiment name, device port, and startup delay:

```yaml
# docker-compose.parallel.yml pattern
services:
  rv01:
    environment:
      RV_EXPERIMENT_NAME: batch_01
      RV_DEVICE_PORT: 5554
      RV_DELAY: 0
  rv02:
    environment:
      RV_EXPERIMENT_NAME: batch_02
      RV_DEVICE_PORT: 5556
      RV_DELAY: 30
```

### Resume in Docker

Set `RV_EXPERIMENT_NAME` and mount the results volume. When restarted with the same name, the container auto-detects `tasks.json` and resumes.

## Output Files

The platform generates the following files in the results directory:

| File | Description |
|------|-------------|
| `coverage.csv` | Per-method coverage data with timing and progressive metrics |
| `errors.csv` | Monitored operations violations with timing and context |
| `summary.csv` | Aggregate metrics per task (activities, methods, MOP coverage, errors) |
| `results.json` | Hierarchical JSON with complete experiment data |
| `performance.csv` | Task execution timing and performance metrics |
| `tasks.json` | Task state persistence for experiment resume |

## CLI Reference

### rv-experiment (Experiment Orchestration)

```bash
# Run experiment
uv run rv-experiment run --tools <tools> [options]

# Options
--tools TOOLS              # Tool specification DSL (required)
--timeout SECONDS          # Execution timeout (default: 300)
--repetitions N            # Number of repetitions (default: 1)
--apks-dir DIR             # APK directory (default: ./apks_examples)
--specification-set SET    # jca, generic, or custom (default: jca)
--name NAME                # Experiment name (enables implicit resume)
--resume-dir DIR           # Resume from specific directory
--no-window                # Headless emulator mode
--skip-monitors            # Skip monitor generation
--skip-instrument          # Skip APK instrumentation
--skip-static              # Skip static analysis
--generate-monitors        # Generate monitors in pre-processing
--instrument-apks          # Instrument APKs in pre-processing
--static-analysis          # Run static analysis in pre-processing

# List available tools
uv run rv-experiment list-tools --detailed

# Generate configuration template
uv run rv-experiment config --template-type basic --output config.json

# Validate configuration
uv run rv-experiment validate config.json
```

### rv-platform (Direct Task Execution)

```bash
# Run tasks directly (no pre-processing)
uv run rv-platform run --tools monkey --apks-dir ./apks_examples

# Process existing results
uv run rv-platform run --process-results ./results/experiment_dir
```

### rv-agent (Standalone LLM Testing)

```bash
# Requires emulator running + APK installed
uv run rv-agent run --package <package_name> --mode <mode> --timeout <seconds>
```

## Development

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RVSEC_HOME` | For instrumentation | Path to RVSEC installation |
| `ANDROID_HOME` | For emulator | Android SDK path |
| `RV_PYDANTIC` | No | Set to `true` for development validation |

### Testing

```bash
# Run all tests
uv run pytest

# Test specific module
uv run pytest modules/rv-agent/tests/ -v

# Fast unit tests only
uv run pytest -m "not slow" -v

# Format and lint
uv run black modules/ && uv run flake8 modules/
```

### Directory Structure

```
rv-android/
├── modules/                   # 13 uv workspace modules
│   ├── rv-android-core/       # Foundation infrastructure
│   ├── rv-platform/           # Execution engine
│   ├── rv-tools/              # Tool plugin system
│   ├── rv-uiautomator/        # Device interaction
│   ├── rv-monitor-generator/  # Monitor generation
│   ├── rv-instrumentation/    # APK instrumentation
│   ├── rv-static-analysis/    # Unified GATOR static analysis
│   ├── rv-coverage/           # Coverage tracking
│   ├── rv-screen-parser/      # UI parsing
│   ├── rv-agent/              # LLM-driven testing
│   ├── rvagent-tool/          # rv-agent tool bridge
│   ├── rv-experiment/         # Experiment orchestration
│   └── rv-agent-validation/   # Agent validation/calibration
├── docker/                    # Docker images (4-layer chain)
├── apks_examples/             # Sample APKs for testing
├── results/                   # Experiment results (persistent)
├── out/                       # Temporary artifacts (monitors, instrumented APKs)
├── docs/                      # Documentation
├── openspec/                  # Spec-Driven Development artifacts
└── pyproject.toml             # uv workspace configuration
```

### Cleanup

```bash
./clear.sh                 # Clean temporary artifacts (keeps results/)
./clear.sh --clean-results # Clean everything including results
```

## Documentation

| Document | Description |
|----------|-------------|
| Module `CLAUDE.md` files | Architecture and development reference per module |
| Module `docs/architecture.md` files | Detailed architecture documentation |
| `docs/PRD.md` | Product Requirements Document (37 FRs, 8 NFRs) |
| `docs/WORKFLOW.md` | Development workflow and SDD process |
| `docs/VISION.md` | VLM evaluation methodology and results |
| `docker/README.md` | Docker infrastructure documentation |

## Related Projects

- **RVSEC**: Parent project providing the runtime verification infrastructure ([github.com/PAMunb/rvsec](https://github.com/PAMunb/rvsec))
- **RV-Android (original)**: The original bash-based instrumentation tool by Runtime Verification Inc. that inspired the instrumentation pipeline ([github.com/runtimeverification/rv-android](https://github.com/runtimeverification/rv-android))
