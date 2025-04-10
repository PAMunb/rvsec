# RV-Android Usage Guide

This guide provides comprehensive information on how to use the RV-Android platform for testing Android applications with runtime verification capabilities.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Prerequisites](#2-prerequisites)
3. [Basic Usage](#3-basic-usage)
4. [Command-Line Arguments](#4-command-line-arguments)
5. [Tool Configuration](#5-tool-configuration)
   - [Tool Specification Format](#51-tool-specification-format)
   - [Available Tools](#52-available-tools)
   - [Tool Variants](#53-tool-variants)
6. [Configuration Files](#6-configuration-files)
7. [Enhanced Execution Mode](#7-enhanced-execution-mode)
8. [Environment Variables](#8-environment-variables)
9. [Experiment Resumption](#9-experiment-resumption)
10. [Result Analysis](#10-result-analysis)
11. [Advanced Usage Examples](#11-advanced-usage-examples)
12. [Troubleshooting](#12-troubleshooting)

## 1. Introduction

RV-Android is a modular testing framework for Android applications with runtime verification capabilities. It integrates multiple testing tools, including RVDroid and RVAndroid, which are embedded within the platform. The framework supports:

- Automated testing with multiple tools and configurations
- LLM-guided testing strategies
- Runtime verification with monitor generation and APK instrumentation
- Static analysis of Android applications
- Comprehensive result analysis and visualization

The platform provides a unified interface for configuring and executing experiments with different testing tools, allowing researchers and developers to systematically evaluate their effectiveness.

## 2. Prerequisites

Before using RV-Android, ensure you have the following:

- Python 3.10 or later
- Android SDK (with ANDROID_HOME environment variable set)
- Android emulator image or physical device
- Java Development Kit (JDK) 8 or later
- Required Python packages (install with `pip install -r requirements.txt`)

### Environment Setup

1. Clone the RV-Android repository:
   ```bash
   git clone https://github.com/username/rv-android.git
   cd rv-android
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   export ANDROID_HOME=/path/to/android/sdk
   export ANDROID_TOOLS=$ANDROID_HOME/tools
   export ANDROID_PLATFORM_TOOLS=$ANDROID_HOME/platform-tools
   export PATH=$PATH:$ANDROID_TOOLS:$ANDROID_PLATFORM_TOOLS
   ```

## 3. Basic Usage

The main entry point for RV-Android is the `main.py` script, which can be used to run experiments with various testing tools and configurations.

### Simple Examples

1. Run a test with the default Monkey tool for 60 seconds:
   ```bash
   python main.py --no_window -tools monkey -r 1 -t 60
   ```

2. Run tests with multiple tools and timeouts:
   ```bash
   python main.py --no_window -tools monkey droidbot:dfs_greedy -r 3 -t 120 300 600
   ```

3. List available tools and their variants:
   ```bash
   python main.py --list-tools
   ```

### Execution Flow

When you execute an experiment, RV-Android performs the following steps:

1. **Initialization**: Loads configurations and prepares the environment
2. **APK Processing** (optional): 
   - Monitor generation for runtime verification
   - APK instrumentation with monitors
   - Static analysis of application code
3. **Experiment Execution**:
   - Setting up test environment
   - Running test tools with specified configurations
   - Collecting and storing results
4. **Result Processing**:
   - Analyzing test results
   - Generating performance metrics
   - Creating reports and visualizations

## 4. Command-Line Arguments

RV-Android supports the following command-line arguments:

| Argument | Description | Default | Example |
|----------|-------------|---------|---------|
| `-tools` | List of testing tools to use | `["monkey"]` | `-tools monkey droidbot:dfs_greedy` |
| `-t` | List of execution timeouts in seconds | `[60]` | `-t 120 300 600` |
| `-r` | Number of repetitions | `1` | `-r 3` |
| `-c` | Path to memory file or configuration JSON | `""` | `-c experiment_config.json` |
| `--no_window` | Start emulator without GUI window | `False` | `--no_window` |
| `--debug` | Enable debug logging | `False` | `--debug` |
| `--list-tools` | Display available tools and variants | - | `--list-tools` |
| `--skip_monitors` | Skip monitor generation | `False` | `--skip_monitors` |
| `--skip_instrument` | Skip instrumentation | `False` | `--skip_instrument` |
| `--skip_experiment` | Skip experiment execution | `False` | `--skip_experiment` |
| `--skip_static_analysis` | Skip static analysis | `False` | `--skip_static_analysis` |
| `--enhanced` | Use enhanced experiment controller | `False` | `--enhanced` |
| `--orchestration-mode` | Orchestration mode for enhanced controller | `SEQUENTIAL` | `--orchestration-mode PARALLEL` |

## 5. Tool Configuration

### 5.1 Tool Specification Format

Tools can be specified with variants and parameters using the following format:
```
tool_name[:variant1][:variant2][@param1=value1,param2=value2]
```

Examples:
- `monkey`: Use the default Monkey tool
- `droidbot:dfs_greedy`: Use DroidBot with the dfs_greedy variant
- `rvandroid:llama:single_action`: Use RVAndroid with llama LLM and single_action strategy
- `rvandroid@model=gpt-4,strategy=composable`: Use RVAndroid with custom parameters

### 5.2 Available Tools

RV-Android includes the following testing tools:

| Tool | Description |
|------|-------------|
| `monkey` | Android UI/Application Exerciser Monkey |
| `droidbot` | Android app automated testing tool with UI analysis |
| `rvandroid` | LLM-guided testing tool for Android applications |
| `rvdroid` | Enhanced testing tool with memory and LLM capabilities |
| `ape` | Android testing tool with model-based exploration |
| `droidmate` | Automated Android testing tool with state-based exploration |
| `fastbot` | Fast model-based Android app testing tool |
| `humanoid` | ML-based Android testing tool that mimics human behavior |
| `qtesting` | Reinforcement learning-based Android testing tool |

### 5.3 Tool Variants

Each tool can have several variants that modify its behavior:

#### DroidBot Variants
- `dfs_naive`: Depth-first search strategy with naive selection
- `dfs_greedy`: Depth-first search strategy with greedy selection
- `bfs_naive`: Breadth-first search strategy with naive selection
- `bfs_greedy`: Breadth-first search strategy with greedy selection

#### RVAndroid Variants
- LLM Variants:
  - `llama`: Uses Llama LLM
  - `gpt4`: Uses GPT-4 model
  - `claude`: Uses Claude model
- Strategy Variants:
  - `single_action`: Single action strategy
  - `composable`: Composable action strategy

#### RVDroid Variants
- `llm_enabled`: Enables LLM-guided testing
- `detailed_ui`: Uses detailed UI parser
- `batch_action`: Enables Flow-Based Batch Action Strategy
- `flow_based`: Alias for batch_action strategy

#### Monkey Variants
- `fixed_seed`: Uses a fixed seed (42)
- `low_throttle`: Uses lower throttle value (50)

#### FastBot Variants
- `fast`: Uses low throttle (50)
- `slow`: Uses high throttle (500)

## 6. Configuration Files

Instead of specifying all parameters via command line, you can use a JSON configuration file:

```bash
python main.py -c experiment_config.json
```

Configuration file example:
```json
{
   "repetitions": 3,
   "timeouts": [60, 120, 300],
   "no_window": true,
   "tools": [
       {
           "name": "monkey",
           "variant": "fixed_seed"
       },
       {
           "name": "droidbot",
           "variant": "dfs_greedy",
           "params": {
               "count": "1000"
           }
       },
       {
           "name": "rvandroid",
           "variants": ["llama", "single_action"],
           "params": {
               "temperature": 0.2
           }
       }
   ]
}
```

## 7. Enhanced Execution Mode

RV-Android provides an enhanced execution mode that uses advanced orchestration and analysis systems:

```bash
python main.py --enhanced -tools monkey -r 2 -t 120
```

### Orchestration Modes

The enhanced execution controller supports different orchestration modes:

- `SEQUENTIAL`: Run tasks one after another (default)
- `PARALLEL`: Run tasks in parallel when possible
- `ADAPTIVE`: Dynamically adjust parallelism based on resource availability
- `PRIORITY_BASED`: Execute tasks based on priority

Example:
```bash
python main.py --enhanced --orchestration-mode PARALLEL -tools droidbot -r 2 -t 120 300
```

## 8. Environment Variables

The following environment variables can be used to override command-line arguments:

| Variable | Description | Type |
|----------|-------------|------|
| `RV_TOOLS` | Comma-separated list of tools | String |
| `RV_REPETITIONS` | Number of repetitions | Integer |
| `RV_TIMEOUTS` | Space-separated list of timeouts | String |
| `RV_MEMORY_FILE` | Path to memory file | String |
| `RV_SKIP_MONITORS` | Skip monitor generation | Boolean |
| `RV_SKIP_INSTRUMENT` | Skip instrumentation | Boolean |
| `RV_SKIP_STATIC_ANALYSIS` | Skip static analysis | Boolean |
| `RV_SKIP_EXPERIMENT` | Skip experiment execution | Boolean |
| `RV_NO_WINDOW` | Start emulator without window | Boolean |
| `RV_DEBUG` | Enable debug mode | Boolean |
| `RV_HUMANOID_URL` | URL for Humanoid service | String |
| `RV_RVANDROID_URL` | URL for RVAndroid service | String |

Example:
```bash
RV_TOOLS="rvandroid:llama:single_action" RV_NO_WINDOW=true python main.py
```

## 9. Experiment Resumption

To continue an interrupted experiment, use the memory file option:

```bash
python main.py -c path/to/execution_memory.json
```

The memory file is automatically created during experiment execution and contains the current state of the experiment, including completed and pending tasks.

## 10. Result Analysis

After running experiments, you can analyze the results using the built-in analysis tools:

```bash
python examples/analyze_results.py --results-dir test_results --visualize --export-csv --export-excel
```

The analysis script supports the following options:

| Option | Description |
|--------|-------------|
| `--results-dir`, `-r` | Directory containing test results |
| `--output-dir`, `-o` | Directory for analysis output |
| `--visualize`, `-v` | Generate visualizations |
| `--export-csv`, `-c` | Export results to CSV |
| `--export-excel`, `-e` | Export results to Excel |
| `--enhanced-export`, `-E` | Generate enhanced spreadsheet with detailed metrics |
| `--detect-anomalies`, `-a` | Detect anomalies in results |
| `--analyze-correlations`, `-C` | Analyze correlations between app characteristics and configurations |
| `--dashboard`, `-d` | Generate interactive dashboard |
| `--launch-dashboard`, `-l` | Launch dashboard in web browser |

You can also analyze results programmatically using the Python API:

```python
from rvandroid.test_framework.results_loader import ResultsLoader
from rvandroid.test_framework.exporters import export_to_csv
from rvandroid.test_framework.visualization import generate_visualizations

# Load and analyze results
loader = ResultsLoader("test_results")
results = loader.load_and_analyze()

# Generate visualizations
generate_visualizations(results, "visualizations")

# Export to CSV
export_to_csv(results, "results.csv")
```

## 11. Advanced Usage Examples

### Running with Multiple LLM-guided Tools

```bash
python main.py --no_window -tools rvandroid:llama rvandroid:gpt4 -r 2 -t 300 600
```

### Custom Configuration for RVAndroid

```bash
python main.py --no_window -tools rvandroid@model=llama3.2:3b,temperature=0.1,strategy=composable
```

### Running Only on Pre-instrumented Apps

```bash
python main.py --skip_monitors --skip_instrument -tools monkey -r 1 -t 120
```

### Comparing Multiple Tool Variants

```bash
python main.py -tools monkey:fixed_seed monkey:low_throttle droidbot:dfs_naive droidbot:dfs_greedy -r 3 -t 300
```

### Running with Different Orchestration Modes

```bash
# Sequential execution (default)
python main.py --enhanced --orchestration-mode SEQUENTIAL -tools monkey -r 2 -t 120

# Parallel execution
python main.py --enhanced --orchestration-mode PARALLEL -tools monkey droidbot -r 2 -t 120

# Adaptive execution
python main.py --enhanced --orchestration-mode ADAPTIVE -tools rvandroid rvdroid -r 2 -t 300

# Priority-based execution
python main.py --enhanced --orchestration-mode PRIORITY_BASED -tools rvandroid:llama rvandroid:gpt4 -r 1 -t 300
```

## 12. Troubleshooting

### Common Issues

1. **Emulator issues**: 
   - Make sure the emulator is running before starting the experiment
   - Check if the AVD image is properly installed
   - Try increasing the emulator memory: `--memory 2048`

   ```bash
   # Start emulator manually before running experiment
   emulator -avd RVSec -no-window -memory 2048
   ```

2. **LLM connection issues**:
   - Check if the LLM server is running
   - Verify the connection URL is correct
   - For Ollama, ensure the model is downloaded:
   
   ```bash
   ollama pull llama3.2:3b
   ```

3. **APK instrumentation failures**:
   - Check if the APK is signed properly
   - Verify monitor specifications are compatible
   - Try skipping instrumentation for testing:
   
   ```bash
   python main.py --skip_instrument -tools monkey
   ```

4. **Memory issues**:
   - Reduce the number of parallel tests in enhanced mode
   - Use smaller LLM models
   - Increase JVM memory: `export JAVA_OPTS="-Xmx4g"`

### Logs

Detailed logs are stored in the following locations:

- Main log: `results/experiment_[timestamp]/logs/main.log`
- Tool-specific logs: `results/experiment_[timestamp]/logs/tools/`
- Emulator logs: `results/experiment_[timestamp]/logs/emulator/`

You can increase logging verbosity with the `--debug` flag:

```bash
python main.py --debug -tools monkey
```

For more detailed information about specific components, refer to the component-specific documentation in the `docs/` directory.