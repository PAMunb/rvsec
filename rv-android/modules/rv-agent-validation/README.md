# RV-Agent Validation

Validation and calibration framework for RV-Agent experiments.

## Features

- **Experiment orchestration**: Run validation experiments with configurable strategies, prompts, and LLM parameters
- **Metrics collection**: Method coverage, UI coverage, LLM latency, token usage, hit rate
- **Multi-phase experiments**: Support for algorithm comparison (Phase 1), prompt/params tuning (Phase 2), and multimode validation (Phase 3)
- **Parameter calibration**: Bayesian optimization (Optuna) for tuning RVAgentStrategy parameters
- **Report generation**: Aggregated metrics reports per experiment

## Installation

```bash
cd modules && ./install.sh rv-agent-validation
```

## CLI Commands

### Run Experiment

```bash
# Run experiment from config file
uv run python -m rv_agent_validation run --config data/configs/my_config.json --output results

# Dry run (show what would execute)
uv run python -m rv_agent_validation run --config data/configs/my_config.json --dry-run

# Resume from checkpoint
uv run python -m rv_agent_validation run --config data/configs/my_config.json --resume
```

### Preprocess APKs

```bash
# Instrument APKs and run static analysis
uv run python -m rv_agent_validation preprocess --data-dir data/

# Force re-instrumentation
uv run python -m rv_agent_validation preprocess --force

# Skip static analysis
uv run python -m rv_agent_validation preprocess --skip-static
```

### Parameter Calibration (Docker-based)

Calibration uses Docker containers for parallel trial execution, orchestrated by host-side scripts.

```bash
# Run calibration (macro phase, 6 parallel containers, 50 trials)
uv run python scripts/calibration_orchestrator.py \
    --data-dir data/calibration_dataset_v2 \
    --filter-file data/calibration_set_v2.txt \
    --output-dir ./results/calibration_macro \
    --n-containers 6 --n-trials 50 --timeout 300 --phase macro

# Run baseline experiment (3 tools, 6 containers)
uv run python scripts/baseline_docker.py \
    --tools ape,fastbot,rvagent:pure_algorithm \
    --data-dir data/calibration_dataset_v2 \
    --filter-file data/all_valid_apks.txt \
    --output-dir ./results/baseline_v2 \
    --n-containers 6 --timeout 300 --repetitions 3

# Show calibrated parameters
uv run python -m rv_agent_validation show-params \
    --params-file ./results/calibration_macro/optimal_params.json

# Show default parameter values
uv run python -m rv_agent_validation show-defaults
```

**Calibration Workflow:**
1. **Phase B (Baseline)**: `baseline_docker.py` — establish error baselines
2. **Phase C (Macro)**: `calibration_orchestrator.py --phase macro` — tune 8 parameters
3. **Phase D (Micro)**: `calibration_orchestrator.py --phase micro` — fine-tune 16 parameters
4. **Phase E (Validation)**: `baseline_docker.py` — validate on hold-out set

**Objective Function**: 40% method coverage + 40% normalized MOP errors + 20% UI coverage.

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
├── calibration_dataset/     # Pre-instrumented APKs for calibration (15 APKs)
│   ├── *.apk                # Instrumented APK files
│   └── *.apk.json           # Unified static analysis (reachability, windows, transitions)
├── smoke_test_dataset/      # Small dataset for quick tests (2 APKs)
├── calibration_set.txt      # 10 APKs for calibration trials
├── holdout_set.txt          # 5 APKs for hold-out validation
├── configs/                 # Experiment configuration files
│   ├── phase1_algorithms.json
│   ├── phase2_prompts.json
│   └── mini_phase2.json
└── *.csv                    # APK metadata
```

### Calibration Dataset Split

To prevent overfitting, the dataset is split into:

**Calibration Set (10 APKs)** - Used for Optuna optimization:
- byrne.utilities.hashpass_2.apk
- com.allansimon.verbisteandroid_2.apk
- com.andybotting.tramhunter_1300.apk
- com.aptasystems.dicewarepasswordgenerator_8.apk
- com.blippex.app_5.apk
- com.example.openpass_1.apk
- com.example.root.analyticaltranslator_6.apk
- com.freezingwind.animereleasenotifier_9.apk
- com.koushikdutta.superuser_1030.apk
- com.linuxcounter.lico_update_003_8.apk

**Hold-out Validation Set (5 APKs)** - Used ONLY for final validation:
- biz.gyrus.yaab_30.apk
- ca.farrelltonsolar.classic_314.apk
- com.aidinhut.simpletextcrypt_14.apk
- com.crazyhitty.chdev.ks.munch_14.apk
- com.github.axet.darknessimmunity_28.apk

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

### Experiment Runner

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

### Calibration API

```python
from rv_agent_validation.calibration import (
    ObjectiveFunction,
    get_default_params,
    params_to_tool_spec,
    CalibrationPhase,
    suggest_params,
)

# Objective function (40% coverage + 40% errors + 20% UI coverage)
objective_fn = ObjectiveFunction(
    coverage_weight=0.40,
    errors_weight=0.40,
    ui_coverage_weight=0.20,
    baseline_max_errors=10.0  # From baseline experiment
)

# Score experiment results
score = objective_fn.compute("./results/trial_0/trial_0")

# Convert parameters to tool specification DSL
params = {"mop_direct_score": 350.0, "max_re_enables": 8}
tool_spec = params_to_tool_spec(params)
# Output: "mop_direct_score=350.0000,max_re_enables=8"
```

Docker-based calibration is orchestrated by `scripts/calibration_orchestrator.py`.

### Calibration Parameters

**Macro Parameters (8 high-impact):**

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

**Micro Parameters (16 fine-tuning):**

| Parameter | Default | Range |
|-----------|---------|-------|
| `mop_transitive_score` | 150.0 | 75-250 |
| `stochastic_temperature` | 1.0 | 0.1-5.0 |
| `scroll_probability` | 0.15 | 0.05-0.3 |
| `plateau_window` | 10 | 5-20 |
| `max_input_variations` | 3 | 1-6 |
| `gradual_decay_rate` | 0.7 | 0.5-0.9 |
| `llm_probability` | 0.7 | 0.0-1.0 |
| `llm_temperature` | 0.01 | 0.001-0.3 |

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
| `docs/20260202_rvagent_validacao.md` | Calibration and validation framework plan |
| `CLAUDE.md` | Module reference for Claude Code |

## Testing

```bash
# Run unit tests
cd modules/rv-agent-validation
uv run pytest tests/ -v

# Run calibration smoke test (3 trials, generate-only)
uv run python scripts/calibration_orchestrator.py \
    --data-dir data/calibration_dataset_v2 \
    --filter-file data/calibration_set_v2.txt \
    --output-dir ./results/smoke_test \
    --n-containers 2 --n-trials 3 --timeout 60 --phase macro --generate-only
```

## Dependencies

- **rv-android-core**: Foundation infrastructure
- **rv-agent**: Agent execution (AgentFactory, RVAgentConfig)
- **rv-experiment**: Experiment orchestration (rv-experiment CLI)
- **rv-platform**: Task execution and result processing
- **optuna**: Bayesian optimization for parameter calibration
- **pandas**: Data processing for calibration metrics
- **scipy**: Statistical tests
