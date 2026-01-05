# Vision Model Benchmark - Comparison Tables

## Overall Performance Comparison

| Model | Family | Size | Success Rate | Avg Distance | Hit Rate | Speed |
|-------|--------|------|--------------|--------------|----------|-------|
| qwen2.5vl:7b | qwen | 7b | 98.3% | 3.8px | 96.7% | 2.45s |
| qwen2.5vl:3b | qwen | 3b | 96.7% | 36.1px | 93.3% | 2.01s |
| gemma3:12b | gemma | 12b | 81.7% | 33.5px | 91.7% | 2.62s |
| gemma3:4b | gemma | 4b | 73.3% | 4.8px | 96.7% | 1.74s |
| granite3.2-vision:2b | granite | 2b | 51.7% | 2.1px | 100.0% | 3.28s |
| llama3.2-vision:11b | llama | 11b | 45.0% | 25.8px | 94.1% | 4.40s |
| llava-llama3:8b | llava | 8b | 40.0% | 303.6px | 26.7% | 2.08s |

## Performance by Model Family

| Family | Models | Avg Success | Avg Distance | Avg Speed |
|--------|--------|-------------|--------------|-----------|
| gemma | 2 | 77.5% | 19.2px | 2.18s |
| llama | 1 | 45.0% | 25.8px | 4.40s |
| llava | 1 | 40.0% | 303.6px | 2.08s |
| qwen | 2 | 97.5% | 19.9px | 2.23s |
| granite | 1 | 51.7% | 2.1px | 3.28s |

## Performance by Scenario

| Model | visual_generation | coordinate_validation | mixed_scenario | game_elements |
|-------|---|---|---|---|
| qwen2.5vl:7b | 100.0% | 100.0% | 93.3% | 100.0% |
| qwen2.5vl:3b | 100.0% | 86.7% | 100.0% | 100.0% |
| gemma3:12b | 100.0% | 93.3% | 53.3% | 80.0% |
| gemma3:4b | 100.0% | 93.3% | 100.0% | 0.0% |
| granite3.2-vision:2b | 13.3% | 100.0% | 93.3% | 0.0% |
| llama3.2-vision:11b | 20.0% | 93.3% | 13.3% | 53.3% |
| llava-llama3:8b | 100.0% | 26.7% | 26.7% | 6.7% |