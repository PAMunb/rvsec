# LLM Evaluation Analysis Report

**Generated:** 2025-06-03 11:04:27

This report provides a comprehensive analysis of LLM model configurations evaluated for Android testing action generation. The evaluation compared different models, strategies, and parameters across multiple prompt scenarios.

---

## Executive Summary

- **Total Configurations Evaluated:** 64
- **Average Success Rate:** 97.8%
- **Average Overall Score:** 94.0/100

### Best Performing Configuration
- **Model:** llama3.2:1b
- **Strategy:** standard_modular
- **Temperature:** 0.2
- **Overall Score:** 99.5/100
- **Success Rate:** 100.0%

The evaluation reveals significant performance variations across different configurations, with clear winners emerging based on success rates, response quality, and generation speed.

## Overall Configuration Rankings
**1. llama3.2:1b | standard_modular | T=0.2**
   - Overall Score: 99.5/100
   - Success Rate: 100.0%

**2. llama3.2:1b | batch_action_modular | T=0.2**
   - Overall Score: 99.0/100
   - Success Rate: 100.0%

**3. llama3.2:1b | standard_modular | T=0.2**
   - Overall Score: 99.0/100
   - Success Rate: 100.0%

**4. llama3.2:1b | standard_modular | T=0.2**
   - Overall Score: 99.0/100
   - Success Rate: 100.0%

**5. llama3.2:1b | batch_action_modular | T=0.2**
   - Overall Score: 99.0/100
   - Success Rate: 100.0%

**6. llama3.2:1b | batch_action_modular | T=0.2**
   - Overall Score: 99.0/100
   - Success Rate: 100.0%

**7. llama3.2:1b | batch_action_modular | T=0.2**
   - Overall Score: 98.6/100
   - Success Rate: 100.0%

**8. llama3.2:1b | standard_modular | T=0.2**
   - Overall Score: 98.6/100
   - Success Rate: 100.0%

**9. llama3.2:1b | batch_action_modular | T=0.2**
   - Overall Score: 98.6/100
   - Success Rate: 100.0%

**10. llama3.2:1b | standard_modular | T=0.2**
   - Overall Score: 98.6/100
   - Success Rate: 100.0%


## Detailed Metric Analysis
### Performance Metrics
- **Fastest Generation:** qwen3:0.6b (201.2 tokens/sec)
- **Lowest Latency:** llama3.2:1b (413ms)

### Quality Metrics
- **Best Explanation Quality:** llama3.2:1b (Score: 1.00)
- **Average Actions Generated:** 1.2

### Reliability Metrics
- **Most Reliable:** llama3.2:1b (100.0% success rate)
- **Average Error Rate:** 0.0%

## Pattern Analysis
### Model Performance Patterns
- **llama3.2:1b:** Avg Score 96.3, Success Rate 100.0% (32 configs)
- **qwen3:0.6b:** Avg Score 91.8, Success Rate 95.6% (32 configs)

### Strategy Performance Patterns
- **standard_modular:** Avg Score 93.7, Avg Actions 1.2
- **batch_action_modular:** Avg Score 94.3, Avg Actions 1.1

### Parameter Impact Analysis
**Temperature Impact:**
- T=0.2: Avg Score 95.7
- T=0.7: Avg Score 92.4

## Recommendations
### Primary Recommendation
For optimal performance, use **llama3.2:1b** with **standard_modular** strategy and temperature **0.2**.
This configuration achieved an overall score of **99.5/100** with a **100.0%** success rate.

### Alternative Configurations
2. **llama3.2:1b** | batch_action_modular | T=0.2 (Score: 99.0)
3. **llama3.2:1b** | standard_modular | T=0.2 (Score: 99.0)
4. **llama3.2:1b** | standard_modular | T=0.2 (Score: 99.0)

### Specialized Use Cases
- **For Speed:** qwen3:0.6b with batch_action_modular strategy
- **For Quality:** llama3.2:1b with standard_modular strategy

## Generated Files

The evaluation produced the following output files:

### CSV Data Files
- **`detailed_results.csv`**: Complete results for every individual run with all metrics
- **`summary_results.csv`**: Configuration summaries ranked by overall performance
- **`top_10_configurations.csv`**: Top 10 best performing configurations
- **`tokens_per_second_ranking.csv`**: Configurations ranked by generation speed
- **`latency_ranking.csv`**: Configurations ranked by response latency (lowest first)
- **`parsing_success_ranking.csv`**: Configurations ranked by parsing success rate
- **`quality_ranking.csv`**: Configurations ranked by explanation quality
- **`success_rate_ranking.csv`**: Configurations ranked by overall success rate

### Analysis Files
- **`analysis_report.md`**: This comprehensive analysis report

### How to Use the Files
1. **For overall ranking**: Check `summary_results.csv` or `top_10_configurations.csv`
2. **For specific metrics**: Use the specialized ranking CSV files
3. **For detailed analysis**: Review individual runs in `detailed_results.csv`
4. **For insights**: Read the recommendations in this analysis report

All CSV files can be opened in Excel, Google Sheets, or any data analysis tool.

## Appendix
### Evaluation Methodology
- **Total Configurations:** 64
- **Total Runs:** 640
- **Repetitions per Configuration:** 10
- **Warm-up Runs:** 2 (excluded from results)
- **Timeout:** 30 seconds per generation

### Scoring Methodology
The overall score (0-100) is calculated based on:
- **Success Rates (40%):** Parsing success, error rates
- **Performance (30%):** Generation speed, latency
- **Quality (20%):** Explanation quality, action relevance
- **Consistency (10%):** Low standard deviation across runs

### File Formats
- **CSV files:** Universal format compatible with Excel, Google Sheets, Python pandas, R, etc.
- **Markdown report:** Human-readable analysis with insights and recommendations
- **UTF-8 encoding:** Ensures compatibility across different systems