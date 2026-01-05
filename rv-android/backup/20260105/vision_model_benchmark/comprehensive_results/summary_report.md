# Vision Model Benchmark - Summary Report

**Total Models Tested**: 7
**Total Test Executions**: 420
**Test Scenarios**: 4

## Executive Summary

### 🏆 Model Performance Ranking

| Rank | Model | Success Rate | Avg Distance | Hit Rate | Response Time |
|------|-------|--------------|--------------|----------|---------------|
| 1 | **qwen2.5vl:7b** | 98.3% | 3.8px | 96.7% | 2.45s |
| 2 | **qwen2.5vl:3b** | 96.7% | 36.1px | 93.3% | 2.01s |
| 3 | **gemma3:12b** | 81.7% | 33.5px | 91.7% | 2.62s |
| 4 | **gemma3:4b** | 73.3% | 4.8px | 96.7% | 1.74s |
| 5 | **granite3.2-vision:2b** | 51.7% | 2.1px | 100.0% | 3.28s |
| 6 | **llama3.2-vision:11b** | 45.0% | 25.8px | 94.1% | 4.40s |
| 7 | **llava-llama3:8b** | 40.0% | 303.6px | 26.7% | 2.08s |

### 🎯 Category Leaders

- **Highest Success Rate**: qwen2.5vl:7b (98.3%)
- **Best Accuracy**: granite3.2-vision:2b (2.1px avg distance)
- **Fastest Response**: gemma3:4b (1.74s avg)

### 📊 Performance by Scenario

- **visual_generation**: 76.2% average success rate
- **coordinate_validation**: 84.8% average success rate
- **mixed_scenario**: 68.6% average success rate
- **game_elements**: 48.6% average success rate

### 💡 Key Insights

- Model family 'qwen' shows best average performance (97.5%)
- Easiest scenario: 'coordinate_validation' (84.8% average success)
- Most challenging scenario: 'game_elements' (48.6% average success)