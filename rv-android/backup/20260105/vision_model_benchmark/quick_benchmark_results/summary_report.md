# Vision Model Benchmark - Summary Report

**Total Models Tested**: 5
**Total Test Executions**: 30
**Test Scenarios**: 2

## Executive Summary

### 🏆 Model Performance Ranking

| Rank | Model | Success Rate | Avg Distance | Hit Rate | Response Time |
|------|-------|--------------|--------------|----------|---------------|
| 1 | **gemma3:4b** | 100.0% | 0.0px | 100.0% | 2.88s |
| 2 | **gemma3:12b** | 100.0% | 0.0px | 100.0% | 4.20s |
| 3 | **qwen2.5vl:7b** | 100.0% | 0.0px | 100.0% | 2.34s |
| 4 | **llama3.2-vision:11b** | 83.3% | 0.0px | 100.0% | 6.03s |
| 5 | **granite3.2-vision:2b** | 50.0% | 0.0px | 100.0% | 3.20s |

### 🎯 Category Leaders

- **Highest Success Rate**: gemma3:4b (100.0%)
- **Best Accuracy**: gemma3:4b (0.0px avg distance)
- **Fastest Response**: qwen2.5vl:7b (2.34s avg)

### 📊 Performance by Scenario

- **coordinate_validation**: 100.0% average success rate
- **visual_generation**: 73.3% average success rate

### 💡 Key Insights

- Model family 'gemma' shows best average performance (100.0%)
- Larger models tend to perform better on coordinate generation tasks
- Easiest scenario: 'coordinate_validation' (100.0% average success)
- Most challenging scenario: 'visual_generation' (73.3% average success)