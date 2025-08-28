# Vision Model Benchmark - Detailed Analysis

## Model Configurations

### Google Gemma 3 4B

- **Model ID**: `gemma3:4b`
- **Family**: gemma
- **Size**: 4b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 73.3%
- Parsing Success: 75.0%
- Coordinate Success: 75.0%
- Average Distance: 4.8px
- Hit Rate: 96.7%
- Response Time: 1.74s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 93.3%
  - Distance: 9.7px
  - Hit Rate: 93.3%

- **mixed_scenario**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **game_elements**:
  - Success: 0.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Known Limitations**:

- Strong center-bias without explicit coordinates
- Poor performance on non-DOM elements
- Generates coordinates around (540, 960) frequently

**Strengths**:

- Perfect accuracy with explicit coordinates
- Excellent visual element recognition
- Good at selecting from provided options

---

### Google Gemma 3 12B

- **Model ID**: `gemma3:12b`
- **Family**: gemma
- **Size**: 12b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 81.7%
- Parsing Success: 100.0%
- Coordinate Success: 85.0%
- Average Distance: 33.5px
- Hit Rate: 91.7%
- Response Time: 2.62s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 93.3%
  - Distance: 31.6px
  - Hit Rate: 93.3%

- **mixed_scenario**:
  - Success: 53.3%
  - Distance: 36.7px
  - Hit Rate: 88.9%

- **game_elements**:
  - Success: 80.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- Larger model - potentially better reasoning
- May have improved spatial understanding

---

### Meta Llama 3.2 Vision 11B

- **Model ID**: `llama3.2-vision:11b`
- **Family**: llama
- **Size**: 11b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 45.0%
- Parsing Success: 100.0%
- Coordinate Success: 46.7%
- Average Distance: 25.8px
- Hit Rate: 94.1%
- Response Time: 4.40s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 20.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 93.3%
  - Distance: 27.2px
  - Hit Rate: 93.3%

- **mixed_scenario**:
  - Success: 13.3%
  - Distance: 14.8px
  - Hit Rate: 100.0%

- **game_elements**:
  - Success: 53.3%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- Meta's vision model - different training approach
- Potentially better spatial reasoning
- Different tokenization strategy

---

### LLaVA Llama 3 8B

- **Model ID**: `llava-llama3:8b`
- **Family**: llava
- **Size**: 8b
- **Temperature**: 0.2
- **Max Tokens**: 350

**Performance Summary**:
- Overall Success Rate: 40.0%
- Parsing Success: 100.0%
- Coordinate Success: 76.7%
- Average Distance: 303.6px
- Hit Rate: 26.7%
- Response Time: 2.08s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 26.7%
  - Distance: 281.3px
  - Hit Rate: 26.7%

- **mixed_scenario**:
  - Success: 26.7%
  - Distance: 326.0px
  - Hit Rate: 26.7%

- **game_elements**:
  - Success: 6.7%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- LLaVA architecture - specialized for vision
- Strong image understanding capabilities
- Good at detailed visual analysis

---

### Qwen 2.5 Vision Language 3B

- **Model ID**: `qwen2.5vl:3b`
- **Family**: qwen
- **Size**: 3b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 96.7%
- Parsing Success: 100.0%
- Coordinate Success: 100.0%
- Average Distance: 36.1px
- Hit Rate: 93.3%
- Response Time: 2.01s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 86.7%
  - Distance: 72.3px
  - Hit Rate: 86.7%

- **mixed_scenario**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **game_elements**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- Chinese model - different training data
- Compact but efficient
- May have different spatial reasoning patterns

---

### Qwen 2.5 Vision Language 7B

- **Model ID**: `qwen2.5vl:7b`
- **Family**: qwen
- **Size**: 7b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 98.3%
- Parsing Success: 100.0%
- Coordinate Success: 100.0%
- Average Distance: 3.8px
- Hit Rate: 96.7%
- Response Time: 2.45s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **mixed_scenario**:
  - Success: 93.3%
  - Distance: 7.5px
  - Hit Rate: 93.3%

- **game_elements**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- Larger Qwen model
- Improved reasoning capabilities
- Better multilingual understanding

---

### IBM Granite 3.2 Vision 2B

- **Model ID**: `granite3.2-vision:2b`
- **Family**: granite
- **Size**: 2b
- **Temperature**: 0.15
- **Max Tokens**: 280

**Performance Summary**:
- Overall Success Rate: 51.7%
- Parsing Success: 100.0%
- Coordinate Success: 51.7%
- Average Distance: 2.1px
- Hit Rate: 100.0%
- Response Time: 3.28s

**Performance by Scenario**:

- **visual_generation**:
  - Success: 13.3%
  - Distance: 0.0px
  - Hit Rate: 0.0%

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 2.1px
  - Hit Rate: 100.0%

- **mixed_scenario**:
  - Success: 93.3%
  - Distance: 2.2px
  - Hit Rate: 100.0%

- **game_elements**:
  - Success: 0.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- IBM enterprise-focused model
- Compact and efficient
- Business-oriented reasoning

---
