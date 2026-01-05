# RVAgent - Autonomous Android Testing Tool

**Phase 0 Prototype Implementation with Parameter Grid Search**

## Overview

RVAgent is an autonomous Android testing tool using LangChain and vision models. This Phase 0 prototype implements parameter grid search to optimize vision model performance for coordinate generation using the research-validated methodology.

## Architecture

- **LangChain Integration**: Pure LangChain framework with ChatOllama
- **Vision Model**: qwen2.5vl:7b (98.3% success rate from research)  
- **UI Parsing**: rv-screen-parser with UIAutomator XML files
- **Coordinate Validation**: 50-pixel tolerance (research methodology)
- **Grid Search**: Systematic parameter optimization

## Parameter Grid Search

The prototype tests all combinations of:
- **Temperature**: [0.1, 0.3, 0.7] (deterministic → creative)
- **Top-p**: [0.7, 0.9] (conservative → diverse)  
- **Top-k**: [20, 40] (restricted → open)

**Total Tests**: 3 × 2 × 2 × 10 apps × 5 screenshots = **600 tests**
**Estimated Duration**: ~5 hours (30s timeout per test)

## Requirements

### Dependencies
- Python 3.12+
- Poetry (for dependency management)
- Ollama with qwen2.5vl:7b model
- rv-android-core, rv-screen-parser modules

### Data Requirements
- Screenshots directory: `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots`
- Structure: `app_name.apk/NNN.png` + `NNN.uiautomator` files
- Minimum: 14 apps with 5+ screenshots each

### Ollama Setup
```bash
# Install qwen2.5vl:7b model
ollama pull qwen2.5vl:7b

# Verify model is running
ollama list
```

## Installation

```bash
cd modules/rv-agent
poetry install --with dev --extras ollama
```

## Configuration

Edit `src/rv_agent/prototype_main.py` to modify parameters:

```python
config = PrototypeConfig(
    NUM_TEST_APPS=10,              # Apps to test (5-50)
    SCREENSHOTS_PER_APP=5,         # Screenshots per app (3-20)
    TIMEOUT_SECONDS=30,            # Timeout per test
    TEMPERATURES=[0.1, 0.3, 0.7],  # Temperature grid
    TOP_PS=[0.7, 0.9],             # Top-p grid
    TOP_KS=[20, 40],               # Top-k grid
    RANDOM_SEED=42                 # Reproducible results
)
```

## Execution

### Quick Start
```bash
cd modules/rv-agent
poetry run python src/rv_agent/prototype_main.py
```

### Development Mode
```bash
cd modules/rv-agent
poetry shell
python src/rv_agent/prototype_main.py
```

## Output

### Results Files
- `rv_agent_prototype_results_YYYYMMDD_HHMMSS.json`: Complete detailed results
- `rv_agent_prototype_results_YYYYMMDD_HHMMSS_summary.txt`: Summary report
- Intermediate files saved every 100 tests

### Results Structure
```json
{
  "summary": {
    "total_tests": 600,
    "success_rate": 94.2,
    "total_duration_minutes": 315.5,
    "best_parameters": {...}
  },
  "parameter_performance": {
    "temp=0.3_p=0.9_k=40": {
      "success_rate": 96.8,
      "avg_execution_time": 28.3,
      "avg_tokens_used": 245
    }
  },
  "detailed_results": [...]
}
```

### Console Output
```
========================================
RVAgent Phase 0 Prototype Configuration  
========================================
Screenshots Directory: /home/pedro/.../screenshots
Available Apps: 14
Test Apps: 10
Primary Model: qwen2.5vl:7b
Total Tests: 600
Estimated Duration: 5.0 hours
========================================

Progress: 100/600 tests (94.2% success rate so far)
...
```

## Grid Search Analysis

The prototype identifies optimal parameters by comparing:
- **Success Rate**: % of coordinates within 50px of clickable elements
- **Execution Time**: Average response time per test
- **Token Usage**: LLM efficiency metrics
- **Error Rates**: Timeout and failure analysis

## Expected Results

Based on vision research findings:
- **Overall Success Rate**: >95% (target from research)
- **Best Parameters**: Likely temperature=0.3, top_p=0.9 (balanced creativity)
- **Token Usage**: ~200-300 tokens per test
- **Processing Time**: 20-30s per test

## Troubleshooting

### Common Issues

**1. Screenshots Directory Not Found**
```bash
# Verify path exists
ls -la /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots
```

**2. Ollama Model Not Found**
```bash
# Check Ollama is running
ollama list
# Pull model if missing
ollama pull qwen2.5vl:7b
```

**3. rv-screen-parser Import Errors**
```bash
cd ../rv-screen-parser
poetry install
cd ../rv-agent
poetry install
```

### Debug Mode
Change logging level in `prototype_main.py`:
```python
logging_manager.configure_logging(level="DEBUG")
```

## Development

### Module Structure
```
rv-agent/
├── src/rv_agent/
│   ├── config.py              # Prototype configuration
│   ├── data_structures.py     # Result data models
│   ├── llm_integration.py     # LangChain + Ollama
│   ├── coordinate_validator.py # rv-screen-parser integration
│   ├── prototype_executor.py  # Grid search logic
│   └── prototype_main.py      # Main execution script
└── pyproject.toml
```

### Testing
```bash
poetry run pytest tests/
```

### Code Quality
```bash
poetry run black src/
poetry run flake8 src/
poetry run mypy src/
```

## Research Integration

This prototype implements findings from vision model research:
- **qwen2.5vl:7b**: Best performing model (98.3% success)
- **Coordinate Validation**: Proven approach vs visual generation  
- **50px Tolerance**: Research-validated threshold
- **Parameter Optimization**: Systematic A/B testing

Results feed directly into production RVAgent implementation.

## Next Steps

1. **Execute Prototype**: Run full 600-test grid search
2. **Analyze Results**: Identify optimal parameters
3. **Validate Findings**: Compare with research benchmarks
4. **Production Integration**: Apply best parameters to full RVAgent

---

**Phase 0 Prototype Status: Ready for Execution** ✅