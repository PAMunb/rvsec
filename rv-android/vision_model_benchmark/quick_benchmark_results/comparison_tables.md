# Vision Model Benchmark - Comparison Tables

## Overall Performance Comparison

| Model | Family | Size | Success Rate | Avg Distance | Hit Rate | Speed |
|-------|--------|------|--------------|--------------|----------|-------|
| gemma3:4b | gemma | 4b | 100.0% | 0.0px | 100.0% | 2.88s |
| gemma3:12b | gemma | 12b | 100.0% | 0.0px | 100.0% | 4.20s |
| qwen2.5vl:7b | qwen | 7b | 100.0% | 0.0px | 100.0% | 2.34s |
| llama3.2-vision:11b | llama | 11b | 83.3% | 0.0px | 100.0% | 6.03s |
| granite3.2-vision:2b | granite | 2b | 50.0% | 0.0px | 100.0% | 3.20s |

## Performance by Model Family

| Family | Models | Avg Success | Avg Distance | Avg Speed |
|--------|--------|-------------|--------------|-----------|
| gemma | 2 | 100.0% | 0.0px | 3.54s |
| llama | 1 | 83.3% | 0.0px | 6.03s |
| qwen | 1 | 100.0% | 0.0px | 2.34s |
| granite | 1 | 50.0% | 0.0px | 3.20s |

## Performance by Scenario

| Model | coordinate_validation | visual_generation |
|-------|---|---|
| gemma3:4b | 100.0% | 100.0% |
| gemma3:12b | 100.0% | 100.0% |
| qwen2.5vl:7b | 100.0% | 100.0% |
| llama3.2-vision:11b | 100.0% | 66.7% |
| granite3.2-vision:2b | 100.0% | 0.0% |