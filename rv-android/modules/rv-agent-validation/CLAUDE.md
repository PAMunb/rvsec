# CLAUDE.md - rv-agent-validation

This file provides guidance to Claude Code when working with the rv-agent-validation module.

## Module Overview

**rv-agent-validation** is a comprehensive validation framework for testing and comparing rv-agent exploration strategies. It provides experiment orchestration, statistical analysis, metrics collection, and report generation capabilities.

### Purpose

- Execute controlled validation experiments comparing exploration strategies (rvagent, dfs, bfs, greedy)
- Collect and analyze multimodal metrics (coverage, hit rate, latency, token usage)
- Perform statistical significance tests and effect size calculations
- Generate reports for academic validation

### Key Features

- **3-Phase Validation Methodology**: Algorithm comparison, prompt/LLM tuning, multimode validation
- **Checkpoint/Resume**: Experiments can be interrupted and resumed
- **Reproducibility**: Deterministic seed management for reproducible results
- **Coverage Tracking**: Method coverage from logcat with MOP (monitored operations) tracking
- **Statistical Analysis**: Kruskal-Wallis, Wilcoxon tests, Cliff's Delta effect sizes
- **Report Generation**: JSON, CSV, and LaTeX table exports

## Module Architecture

```
rv-agent-validation/
├── src/rv_agent_validation/
│   ├── experiment/           # Experiment orchestration
│   │   ├── config.py         # ExperimentConfig, RunConfig dataclasses
│   │   ├── runner.py         # ExperimentRunner (main execution engine)
│   │   ├── checkpoint.py     # CheckpointManager for resume capability
│   │   └── seed_manager.py   # Deterministic seed generation
│   │
│   ├── statistics/           # Statistical analysis
│   │   ├── descriptive.py    # DescriptiveStats (mean, std, median, quartiles)
│   │   ├── significance.py   # SignificanceTests (Kruskal-Wallis, Wilcoxon)
│   │   ├── effect_size.py    # EffectSize (Cliff's Delta, Cohen's d)
│   │   └── composite_score.py # CompositeScorer (multi-objective ranking)
│   │
│   ├── multimodal/           # LLM-specific metrics
│   │   ├── metrics.py        # SessionMetrics, LLMActionRecord dataclasses
│   │   ├── collector.py      # MultimodalMetricsCollector
│   │   ├── analyzer.py       # MultimodalAnalyzer, AggregatedMetrics
│   │   └── hit_classifier.py # HitClassifier for click accuracy
│   │
│   ├── coverage/             # Method coverage tracking
│   │   ├── methods_parser.py # Parse .methods files from instrumentation
│   │   ├── logcat_parser.py  # Parse logcat for coverage events
│   │   ├── tracker.py        # CoverageTracker, CoverageResult
│   │   └── signature_normalizer.py # Normalize method signatures
│   │
│   ├── analysis/             # Post-experiment analysis
│   │   ├── strategy_comparison.py # StrategyComparison (full analysis)
│   │   └── app_selector.py   # App selection utilities
│   │
│   ├── reports/              # Report generation
│   │   ├── json_exporter.py  # JSON export
│   │   ├── csv_exporter.py   # CSV export
│   │   └── latex_tables.py   # LaTeX table generation
│   │
│   ├── preprocessing/        # APK preparation
│   │   └── instrumentation.py # InstrumentationWrapper
│   │
│   ├── calibration/          # Parameter calibration (Optuna)
│   │   ├── __init__.py       # Module exports
│   │   ├── parameter_space.py # 24 tunable parameters with ranges
│   │   ├── objective.py      # ObjectiveFunction (coverage + errors)
│   │   ├── optimizer.py      # CalibrationOptimizer (Optuna TPESampler)
│   │   ├── runner.py         # CalibrationRunner (rv-experiment subprocess)
│   │   ├── cli.py            # CLI commands (calibrate, show-params)
│   │   └── metrics_collector.py # CalibrationMetricsCollector
│   │
│   └── __main__.py           # CLI entry point
│
├── data/
│   ├── calibration_dataset_v2/  # 105 APKs instrumented + SA flat (420 files)
│   │   ├── name.apk            #   Instrumented APK with JCA monitors
│   │   ├── name.apk.gesda      #   GESDA — named {apk_filename}.gesda
│   │   ├── name.apk.wtg        #   GATOR WTG — named {apk_filename}.wtg
│   │   └── name.apk.reach      #   REACH — named {apk_filename}.reach
│   ├── calibration_set_v2.txt   # 75 APKs for calibration (Phases C/D)
│   ├── holdout_set_v2.txt       # 30 APKs for hold-out validation (Phase E)
│   ├── all_valid_apks.txt       # 105 APKs (all valid)
│   ├── dataset_split.csv        # Metadata + set assignment
│   ├── calibration_dataset/     # Legacy: 15 APKs (v1)
│   ├── calibration_set.txt      # Legacy: 10 APKs (v1)
│   └── holdout_set.txt          # Legacy: 5 APKs (v1)
│
├── results/                  # Experiment output
│   └── <experiment_id>/
│       ├── config.json       # Experiment configuration
│       ├── checkpoint.json   # Resume checkpoint
│       ├── experiment.log    # Execution log
│       ├── runs/             # Individual run results
│       ├── logcat/           # Logcat captures
│       └── reports/          # Generated reports
│
└── tests/                    # Test files
```

## CLI Commands

### Run Experiment

```bash
# Run from configuration file
poetry run python -m rv_agent_validation run --config data/configs/my_config.json --output results

# Dry run (show what would execute)
poetry run python -m rv_agent_validation run --config data/configs/my_config.json --dry-run

# Resume interrupted experiment
poetry run python -m rv_agent_validation run --config data/configs/my_config.json --resume

# Direct CLI (without config file)
poetry run python -m rv_agent_validation.experiment.runner run \
    --apks-dir ./apks \
    --strategies rvagent,dfs \
    --mode pure_algorithm \
    --timeout 300 \
    --seed 42
```

### Preprocess APKs

```bash
# Instrument APKs and run static analysis
poetry run python -m rv_agent_validation preprocess --data-dir data/

# Force re-instrumentation
poetry run python -m rv_agent_validation preprocess --force

# Skip static analysis phase
poetry run python -m rv_agent_validation preprocess --skip-static
```

### Analyze Results

```bash
# Run strategy comparison analysis
python -m rv_agent_validation.analysis.strategy_comparison \
    --experiment-dir results/experiment_20260115/ \
    --output analysis.json
```

### Parameter Calibration (Optuna)

The calibration module uses Bayesian optimization (Optuna with TPESampler) to tune RVAgentStrategy parameters for optimal coverage and MOP error detection.

```bash
# Run macro phase calibration (8 high-impact parameters)
poetry run python -m rv_agent_validation calibrate \
    --apks-dir data/calibration_dataset \
    --phase macro \
    --n-trials 50 \
    --timeout 300 \
    --seed 42 \
    --output ./calibration_macro

# Run micro phase calibration (16 fine-tuning parameters)
poetry run python -m rv_agent_validation calibrate \
    --apks-dir data/calibration_dataset \
    --phase micro \
    --best-macro ./calibration_macro/optimal_params.json \
    --n-trials 30 \
    --output ./calibration_micro

# Show calibrated parameters
poetry run python -m rv_agent_validation show-params \
    --params-file ./calibration_macro/optimal_params.json

# Show default parameter values
poetry run python -m rv_agent_validation show-defaults
```

**Calibration Workflow:**
1. **Dataset Preparation**: Use pre-instrumented APKs in `data/calibration_dataset/`
2. **Macro Phase**: Tune 8 high-impact parameters (scorer weights, exploration)
3. **Micro Phase**: Fine-tune 16 additional parameters using best macro params
4. **Validation**: Test on hold-out set (`data/holdout_set.txt`)

**Objective Function**: 50% method coverage + 50% normalized MOP errors (higher is better).

## Configuration Format

### Phase 1: Algorithm Comparison (pure_algorithm)

```json
{
  "experiment_id": "phase1_algorithms",
  "experiment_name": "Phase 1 - Algorithm Comparison",
  "apk_paths": ["data/apks_instrumented/app.apk/app.apk"],
  "strategies": ["rvagent", "dfs", "bfs", "greedy"],
  "timeout_seconds": 300,
  "agent_mode": "pure_algorithm",
  "seeds": [42, 123, 456],
  "device_serial": "emulator-5554",
  "static_analysis_variants": [true]
}
```

### Phase 2: Prompt and LLM Parameters (llm_only)

```json
{
  "experiment_id": "phase2_prompts",
  "experiment_name": "Phase 2 - Prompt Comparison",
  "apk_paths": ["data/apks_instrumented/app.apk/app.apk"],
  "strategies": ["rvagent"],
  "timeout_seconds": 300,
  "agent_mode": "llm_only",
  "prompt_versions": ["v13", "v14"],
  "llm_param_configs": ["default", "temp_low", "temp_high"],
  "seeds": [42],
  "device_serial": "emulator-5554"
}
```

### Phase 3: Multimode Proportions

```json
{
  "experiment_id": "phase3_multimode",
  "experiment_name": "Phase 3 - Multimode Validation",
  "apk_paths": ["data/apks_instrumented/app.apk/app.apk"],
  "strategies": ["rvagent"],
  "timeout_seconds": 300,
  "agent_mode": "multimode",
  "llm_probability_variants": [0.7, 0.5, 0.3],
  "seeds": [42, 123, 456],
  "device_serial": "emulator-5554"
}
```

### LLM Parameter Presets

| Config | temperature | top_p | top_k | Description |
|--------|-------------|-------|-------|-------------|
| `default` | 0.01 | 0.6 | 50 | Current optimal |
| `deterministic` | 0.001 | 0.5 | 30 | Minimal randomness |
| `explorative` | 0.1 | 0.9 | 70 | Higher exploration |
| `temp_low` | 0.001 | 0.6 | 50 | Low temperature |
| `temp_mid` | 0.3 | 0.6 | 50 | Medium temperature |
| `temp_high` | 0.7 | 0.6 | 50 | High temperature |

## Python API

### Running Experiments

```python
from rv_agent_validation.experiment import ExperimentRunner, ExperimentConfig
from pathlib import Path

config = ExperimentConfig(
    experiment_id="my_experiment",
    experiment_name="My Experiment",
    apk_paths=["data/apks_instrumented/app.apk/app.apk"],
    strategies=["rvagent", "dfs"],
    timeout_seconds=300,
    agent_mode="pure_algorithm",
    seeds=[42, 123],
)

runner = ExperimentRunner(config=config, base_dir=Path("results"))
runner.run_experiment(resume=True)
```

### Statistical Analysis

```python
from rv_agent_validation.statistics import (
    DescriptiveStats,
    SignificanceTests,
    EffectSize,
    CompositeScorer,
)

# Descriptive statistics
stats = DescriptiveStats.aggregate_by_strategy(results, "states_discovered")

# Kruskal-Wallis test (multiple groups)
kw_result = SignificanceTests.kruskal_wallis(
    results, "states_discovered", ["rvagent", "dfs", "bfs", "greedy"]
)

# Effect sizes
effect = EffectSize.compare_strategies(results, "states_discovered", "rvagent", "dfs")

# Composite scoring
scorer = CompositeScorer()
rankings = scorer.rank_strategies(results)
recommendation = scorer.recommend_best_strategy(results)
```

### Strategy Comparison

```python
from rv_agent_validation.analysis import StrategyComparison

comparison = StrategyComparison(results, strategies=["rvagent", "dfs", "bfs", "greedy"])
analysis = comparison.run_full_analysis()
comparison.print_report()
comparison.save_results(Path("analysis.json"))
```

### Multimodal Analysis

```python
from rv_agent_validation.multimodal import MultimodalAnalyzer

analyzer = MultimodalAnalyzer()
analyzer.load_sessions(Path("results/experiment/runs"))

by_mode = analyzer.aggregate_by_mode()
comparison = analyzer.compare_modes("llm_only", "pure_algorithm")
report = analyzer.generate_report(Path("report.json"))
```

### Calibration API

```python
from rv_agent_validation.calibration import (
    CalibrationOptimizer,
    CalibrationRunner,
    ObjectiveFunction,
    get_default_params,
    params_to_tool_spec,
    CalibrationPhase,
)

# Create objective function (50% coverage, 50% errors)
objective_fn = ObjectiveFunction(
    coverage_weight=0.50,
    errors_weight=0.50,
    baseline_max_errors=10.0  # Optional: from baseline experiment
)

# Create runner for executing trials via rv-experiment
runner = CalibrationRunner(
    dataset_dir="./data/calibration_dataset",
    objective_fn=objective_fn,
    output_base_dir="./calibration_output",
    timeout=300,
    agent_mode="pure_algorithm"
)

# Create optimizer
optimizer = CalibrationOptimizer(
    phase=CalibrationPhase.MACRO,
    objective_fn=objective_fn,
    trial_runner=runner.run_trial,
    seed=42
)

# Run optimization
best_params = optimizer.optimize(n_trials=50)
optimizer.save_results("./calibration_output")

# Convert to tool specification DSL
tool_spec = params_to_tool_spec(best_params)
# Output: "mop_direct_score=350.0,wtg_guided_score=280.0,..."
```

## Key Classes

### ExperimentConfig

Central configuration for experiments. Supports three agent modes:
- `pure_algorithm`: Tests exploration strategies without LLM
- `llm_only`: Tests LLM-driven exploration
- `multimode`: Tests hybrid LLM/algorithm mode

Key properties:
- `total_runs`: Calculated total number of experiment runs
- `estimated_time_hours`: Estimated execution time
- `generate_runs()`: Generate all RunConfig instances

### CompositeScorer

Multi-objective scoring with configurable weights:
- **30% Coverage**: UI coverage + states discovered
- **25% MOP**: Monitored operations selection rate
- **25% Efficiency**: States per action, low repetition
- **20% Robustness**: Action validity, crash avoidance

### HitClassifier

Classifies LLM click accuracy with adaptive tolerance:
- **HIT**: Click inside target element (within tolerance)
- **NEAR_MISS**: Click hit another interactive element
- **UI_MISS**: Click hit non-interactive UI element
- **EMPTY_MISS**: Click hit empty screen area

Tolerance calculation: 20% of element's smallest dimension, clamped to [10, 50] pixels.

### CheckpointManager

Enables experiment resume capability:
- Tracks completed and failed runs
- Persists to JSON file
- Filters pending runs on resume

### CalibrationOptimizer

Optuna-based Bayesian optimization for RVAgentStrategy parameters:
- **TPESampler**: Tree-structured Parzen Estimator for efficient exploration
- **Reproducible**: Fixed seed (42) for deterministic results
- **Two-phase**: Macro (8 params) + Micro (16 params) calibration

### Calibration Parameters

**Macro Parameters (Phase 1 - 8 params):**

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `mop_direct_score` | 300.0 | 200-500 | MOP method prioritization |
| `wtg_guided_score` | 250.0 | 100-400 | WTG navigation guidance |
| `unsaturated_bonus` | 80.0 | 40-120 | State diversity bonus |
| `max_re_enables` | 6 | 3-15 | Successor exploration depth |
| `ui_coverage_threshold` | 0.9 | 0.7-1.0 | Re-enable trigger threshold |
| `stochastic_probability` | 0.3 | 0.1-0.7 | Exploration randomness |
| `strength_weight` | 50.0 | 25-100 | Historical action success |
| `visitation_penalty_factor` | -10.0 | -20 to -5 | Over-visited penalty |

**Micro Parameters (Phase 2 - 16 params):**

| Parameter | Default | Range |
|-----------|---------|-------|
| `mop_transitive_score` | 150.0 | 75-250 |
| `stochastic_temperature` | 1.0 | 0.1-5.0 |
| `scroll_probability` | 0.15 | 0.05-0.3 |
| `plateau_window` | 10 | 5-20 |
| `max_input_variations` | 3 | 1-6 |
| `gradual_decay_rate` | 0.7 | 0.5-0.9 |
| `component_high_priority` | 50.0 | 30-80 |
| `component_medium_priority` | 40.0 | 20-60 |
| `llm_probability` | 0.7 | 0.0-1.0 |
| `llm_temperature` | 0.01 | 0.001-0.3 |

## Testing

```bash
# Run all tests
cd modules/rv-agent-validation
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_pilot.py -v

# Run with coverage
poetry run pytest --cov=src tests/
```

## Dependencies

- **rv-android-core**: Foundation infrastructure (App, StaticAnalysisData, LogcatManager)
- **rv-agent**: Agent execution (AgentFactory, RVAgentConfig)
- **rv-static-analysis**: Static analysis parsing (StaticAnalysisParser)
- **rv-screen-parser**: UI parsing utilities
- **rv-monitor-generator**: Monitor generation for instrumentation
- **rv-instrumentation**: APK instrumentation
- **scipy**: Statistical tests (Kruskal-Wallis, Wilcoxon)
- **optuna**: Bayesian optimization for parameter calibration
- **pandas**: Data processing for calibration metrics
- **langchain-openai**: LLM interaction for multimodal validation

## Validation Methodology

The framework implements a 3-phase validation methodology:

| Phase | Objective | Mode | Variables |
|-------|-----------|------|-----------|
| **1. Algorithms** | Find best exploration strategy | `pure_algorithm` | rvagent, dfs, bfs, greedy |
| **2. Prompts/Params** | Optimize LLM configuration | `llm_only` | v13/v14 prompts, temperature |
| **3. Multimode** | Find optimal LLM/algorithm ratio | `multimode` | 70/30, 50/50, 30/70 |

**Standard Experiment Parameters:**
- 15 APKs selected for diversity (category, complexity)
- 3 seeds per configuration (42, 123, 456)
- 300 seconds timeout per run
- Static analysis enabled

## Important Implementation Notes

### Reproducibility

- Seeds are deterministically generated from (app, strategy, repetition) tuples
- Each unique combination receives a unique seed via MD5 hash
- Run order is randomized but deterministic (using first seed)

### Coverage Calculation

- Uses custom implementation compatible with .methods file format
- Parses logcat for coverage events (tag: RVAndroid)
- Calculates method coverage, reaches_mop coverage, and error counts

### Infrastructure Error Handling

Runner implements automatic retry (up to 3 attempts) for infrastructure errors:
- `INSTALL_FAILED`
- `device not found`
- `Connection refused`
- `ADB server` issues

### Results Format

Each run produces a JSON file with:
- Run metadata (run_id, package, strategy, seed)
- Execution metrics (states_discovered, total_actions, execution_time)
- Coverage metrics (method_coverage, reaches_mop_coverage, errors)
- UI coverage metrics (element_coverage, interactions_by_type)
- LLM metrics (latency, tokens, hit_rate) for llm_only/multimode

## Documentation

| Document | Description |
|----------|-------------|
| `docs/20260115_rvagent_validacao_multimodal.md` | Full validation methodology |
| `docs/20260119_phase1_results.md` | Phase 1 results and analysis |
| `docs/20260121_phase2_results.md` | Phase 2 results |
| `docs/20260118_calibration_report.md` | Calibration run results |


## Development Notes

This module is part of the RV-Android Poetry workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `poetry install` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
poetry install          # Install/update all modules
poetry install --sync   # Also remove unused packages
```

