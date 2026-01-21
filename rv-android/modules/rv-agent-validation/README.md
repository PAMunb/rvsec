# RV-Agent Validation

Validation framework for RV-Agent experiments.

## Features

- **Experiment orchestration**: Run validation experiments with configurable strategies, prompts, and LLM parameters
- **Metrics collection**: Method coverage, UI coverage, LLM latency, token usage, hit rate
- **Multi-phase experiments**: Support for algorithm comparison (Phase 1), prompt/params tuning (Phase 2), and multimode validation (Phase 3)
- **Report generation**: Aggregated metrics reports per experiment

## Installation

```bash
cd modules && ./install.sh rv-agent-validation
```

## CLI Commands

### Run Experiment

```bash
# Run experiment from config file
poetry run python -m rv_agent_validation run --config data/configs/my_config.json --output results

# Dry run (show what would execute)
poetry run python -m rv_agent_validation run --config data/configs/my_config.json --dry-run

# Resume from checkpoint
poetry run python -m rv_agent_validation run --config data/configs/my_config.json --resume
```

### Preprocess APKs

```bash
# Instrument APKs and run static analysis
poetry run python -m rv_agent_validation preprocess --data-dir data/

# Force re-instrumentation
poetry run python -m rv_agent_validation preprocess --force

# Skip static analysis
poetry run python -m rv_agent_validation preprocess --skip-static
```

## Configuration

### Phase 1: Algorithm Comparison

```json
{
  "experiment_id": "phase1_algorithms",
  "experiment_name": "Phase 1 - Algorithm Comparison",
  "apk_paths": ["data/apks_instrumented/app.apk/app.apk"],
  "strategies": ["dfs", "bfs", "greedy", "rvagent"],
  "timeout_seconds": 300,
  "agent_mode": "pure_algorithm",
  "seeds": [42, 123, 456],
  "device_serial": "emulator-5554",
  "enable_static_analysis": false
}
```

### Phase 2: Prompt and LLM Parameters

```json
{
  "experiment_id": "phase2_prompts",
  "experiment_name": "Phase 2 - Prompt Comparison",
  "apk_paths": ["data/apks_instrumented/app.apk/app.apk"],
  "strategies": ["rvagent"],
  "timeout_seconds": 300,
  "agent_mode": "llm_only",
  "prompt_versions": ["v13", "v14"],
  "llm_param_configs": ["default", "low_temp", "high_diversity"],
  "seeds": [42],
  "device_serial": "emulator-5554",
  "enable_static_analysis": false
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
  "seeds": [42, 123, 456],
  "device_serial": "emulator-5554",
  "enable_static_analysis": false
}
```

### LLM Parameter Configurations

Available `llm_param_configs`:

| Config | temperature | top_p | top_k | Description |
|--------|-------------|-------|-------|-------------|
| `default` | 0.01 | 0.6 | 50 | Current optimal |
| `low_temp` | 0.001 | 0.6 | 50 | Minimal temperature |
| `high_diversity` | 0.1 | 0.9 | 100 | Higher exploration |
| `conservative` | 0.01 | 0.5 | 20 | More focused |
| `no_topk` | 0.01 | 0.6 | -1 | No top_k filter |

## Data Directory Structure

```
data/
├── apks/                    # Original APK files
├── apks_instrumented/       # Instrumented APKs (after preprocess)
├── static_data/             # Static analysis data (.wtg, .gesda, .reach)
├── configs/                 # Experiment configuration files
│   ├── phase1_algorithms.json
│   ├── phase2_prompts.json
│   └── mini_phase2.json
└── *.csv                    # APK metadata
```

## Results Directory Structure

```
results/
└── experiment_id_timestamp/
    ├── config.json          # Experiment configuration
    ├── experiment.log       # Execution log
    ├── checkpoint.json      # Resume checkpoint
    ├── runs/                # Individual run results
    │   └── multimodal_metrics_*.json
    ├── reports/             # Aggregated reports
    │   └── metrics_report.txt
    └── logcat/              # Android logcat captures
```

## Python API

```python
from rv_agent_validation.experiment import ExperimentRunner, ExperimentConfig

# Create config
config = ExperimentConfig(
    experiment_id="my_experiment",
    experiment_name="My Experiment",
    apk_paths=["data/apks_instrumented/app.apk/app.apk"],
    strategies=["rvagent"],
    timeout_seconds=300,
    agent_mode="llm_only",
    prompt_versions=["v13", "v14"],
)

# Run experiment
runner = ExperimentRunner(config=config, base_dir=Path("results"))
runner.run_experiment()
```

## Validation Methodology

The validation follows a 3-phase methodology:

| Phase | Objective | Mode | Variables |
|-------|-----------|------|-----------|
| **1. Algorithms** | Find best exploration strategy | `pure_algorithm` | dfs, bfs, greedy, rvagent |
| **2. Prompts + Params** | Optimize LLM configuration | `llm_only` | v13/v14 prompts, temperature, top_p, top_k |
| **3. Multimode** | Find optimal LLM/algorithm ratio | `multimode` | 70/30, 50/50, 30/70, 10/90 |

**Experiment Parameters:**
- 15 APKs selected for diversity
- 3 seeds per configuration (42, 123, 456)
- 300s timeout per run

## Results

### Phase 1: Algorithm Comparison (Completed)

Winner: **rvagent** strategy with 54.6% method coverage (vs 49.5% for greedy, the second place).

See `docs/20260119_phase1_results.md` for full analysis.

### Phase 2: Prompt + LLM Parameters (In Progress)

Comparing v13 (dialog handling) vs v14 (structured reasoning) with different sampling parameters.

## Documentation

| Document | Description |
|----------|-------------|
| `docs/20260115_rvagent_validacao_multimodal.md` | Full validation methodology (3 phases) |
| `docs/20260119_phase1_results.md` | Phase 1 results and analysis |
| `docs/20260118_calibration_report.md` | Calibration run results |
| `docs/20260113_rvagent_validacao_modulo.md` | Module architecture |
