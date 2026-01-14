# RV-Agent Validation

Validation framework for RV-Agent experiments, providing tools for:

- **Experiment orchestration**: Run validation experiments with multiple strategies
- **Multimodal validation**: Measure hit rate, unique states, and activity coverage
- **Coverage analysis**: Track method and MOP coverage during exploration
- **Statistical analysis**: Kruskal-Wallis, Wilcoxon tests, effect sizes
- **Report generation**: CSV, JSON, and LaTeX output formats

## Installation

```bash
cd modules && ./install.sh rv-agent-validation
```

## Usage

### CLI Commands

```bash
# Run multimodal validation
rv-agent-validation multimodal --help

# Run experiment
rv-agent-validation experiment --help

# Select APKs for validation
rv-agent-validation select-apps --help
```

### Python API

```python
from rv_agent_validation.experiment import ExperimentRunner, ExperimentConfig
from rv_agent_validation.multimodal import MultimodalCollector, HitClassifier
from rv_agent_validation.statistics import run_kruskal_wallis, calculate_cliff_delta
```

## Data Directory

The `data/` directory contains:

- `apks/`: Test APK files
- `static_data/`: Static analysis data (.wtg, .gesda, .reach files)
- `configs/`: Experiment configuration files
- `*.csv`: APK metadata and baseline coverage data

## Documentation

See `docs/20260113_rvagent_validacao_modulo.md` for detailed documentation.
