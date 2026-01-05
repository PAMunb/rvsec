# Vision Model Benchmark - Detailed Analysis

## Model Configurations

### Google Gemma 3 4B

- **Model ID**: `gemma3:4b`
- **Family**: gemma
- **Size**: 4b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 100.0%
- Parsing Success: 100.0%
- Coordinate Success: 100.0%
- Average Distance: 0.0px
- Hit Rate: 100.0%
- Response Time: 2.88s

**Performance by Scenario**:

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **visual_generation**:
  - Success: 100.0%
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
- Overall Success Rate: 100.0%
- Parsing Success: 100.0%
- Coordinate Success: 100.0%
- Average Distance: 0.0px
- Hit Rate: 100.0%
- Response Time: 4.20s

**Performance by Scenario**:

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **visual_generation**:
  - Success: 100.0%
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
- Overall Success Rate: 83.3%
- Parsing Success: 100.0%
- Coordinate Success: 83.3%
- Average Distance: 0.0px
- Hit Rate: 100.0%
- Response Time: 6.03s

**Performance by Scenario**:

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **visual_generation**:
  - Success: 66.7%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- Meta's vision model - different training approach
- Potentially better spatial reasoning
- Different tokenization strategy

---

### Qwen 2.5 Vision Language 7B

- **Model ID**: `qwen2.5vl:7b`
- **Family**: qwen
- **Size**: 7b
- **Temperature**: 0.1
- **Max Tokens**: 300

**Performance Summary**:
- Overall Success Rate: 100.0%
- Parsing Success: 100.0%
- Coordinate Success: 100.0%
- Average Distance: 0.0px
- Hit Rate: 100.0%
- Response Time: 2.34s

**Performance by Scenario**:

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **visual_generation**:
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
- Overall Success Rate: 50.0%
- Parsing Success: 100.0%
- Coordinate Success: 50.0%
- Average Distance: 0.0px
- Hit Rate: 100.0%
- Response Time: 3.20s

**Performance by Scenario**:

- **coordinate_validation**:
  - Success: 100.0%
  - Distance: 0.0px
  - Hit Rate: 100.0%

- **visual_generation**:
  - Success: 0.0%
  - Distance: 0.0px
  - Hit Rate: 0.0%

**Strengths**:

- IBM enterprise-focused model
- Compact and efficient
- Business-oriented reasoning

---
