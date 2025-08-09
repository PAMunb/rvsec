# Refactoring Plan: rv-evaluator Module

## 1. Objective

The primary objective of this refactoring is to streamline the `rv-evaluator` module by simplifying its metrics collection system. The focus will be shifted from a broad quality assessment to a lean, precise evaluation of **performance and throughput**. This will result in a more maintainable and focused evaluation tool, better aligned with the goal of identifying the most efficient LLM configurations.

## 2. Guiding Principles

- **Code and Documentation Language:** All new and modified code, comments, and documentation will be in English.
- **No Legacy Code:** The refactoring will involve direct modification and removal of existing code. No adapters or compatibility layers for legacy components will be introduced.
- **Preserve Functionality:** The core functionality of running evaluations and generating summary reports must be maintained.
- **Technical Documentation:** Comments will be updated to reflect the current state of the architecture, aimed at a technical audience (developers and researchers). Promotional or biased language will be avoided.

## 3. Metric Simplification

### 3.1. Metrics to be Removed

The following metrics will be completely removed from the collection, calculation, and reporting process:
- `load_duration_ms`
- `actions_count`
- `explanation_quality_score`
- `input_output_ratio`
- `response_length_chars`
- `generation_latency_ms`

### 3.2. Metrics to be Kept

The evaluation will focus on this concise set of metrics:
- **Core Performance Metrics:**
    - `total_duration_ms`
    - `input_tokens`
    - `output_tokens`
    - `output_tokens_duration_ms`
- **Core Throughput Metric (Derived):**
    - `tokens_per_second`
- **Success and Error Metrics:**
    - `parsing_success`
    - `error_occurred`
    - `timeout_occurred`
- **Aggregated Rates:**
    - `parsing_success_rate`
    - `error_rate`
    - `timeout_rate`
    - `overall_success_rate`

## 4. `overall_score` Redefinition

The `overall_score` will be simplified to provide a clear ranking based on performance and reliability. The new formula will be a weighted combination of the following key indicators:
1.  **Throughput (`tokens_per_second`):** Prioritizes faster models.
2.  **Inference Time (`total_duration_ms`):** Penalizes slower models.
3.  **Reliability (`overall_success_rate`):** Ensures that fast models are also stable and produce valid output.

The implementation will reside in the `_calculate_overall_score` method within the `StatisticsCalculator` class.

## 5. Step-by-Step Implementation Plan

### Step 1: Backup Original Files
Before any modifications, create a backup of the core files involved in this refactoring.
1. Create a new directory: `modules/rv-evaluator/src/rv_evaluator/backup/`
2. Move the following files into the `backup/` directory:
    - `metrics.py`
    - `evaluator.py`
    - `export.py`

### Step 2: Analyze `export.py`
To prevent `KeyError` exceptions after refactoring, the first implementation step is to understand how results are exported.
1. Read the contents of `export.py`.
2. Identify the code responsible for writing detailed and summary results to files (e.g., CSV).
3. Make a list of the column names or dictionary keys related to the metrics that will be removed. This list will guide the modifications in Step 5.

### Step 3: Refactor `metrics.py`
This is the core of the refactoring.
1.  **In `MetricsCollector` class:**
    -   Remove the logic for `explanation_quality_score` (`_calculate_explanation_quality` and `_score_explanation` methods).
    -   In `_initialize_default_metrics`, remove the keys for the discarded metrics.
    -   In `_collect_performance_metrics`, remove the collection of `load_duration_ms`.
    -   In `_calculate_derived_metrics`, remove the calculation for `input_output_ratio` and `generation_latency_ms`.
2.  **In `StatisticsCalculator` class:**
    -   Rewrite the `_calculate_overall_score` method to implement the new performance-focused formula.
    -   Remove any logic that handles the statistics of the now-removed metrics.
3.  **Update Documentation:**
    -   Review and update all class and method docstrings in the file to reflect the changes.
    -   Ensure comments are in English and accurately describe the current, simplified logic.

### Step 4: Refactor `evaluator.py`
The changes in this file are expected to be minimal but are necessary for consistency.
1.  Review the `_create_error_result` method to ensure it no longer attempts to populate or reference any of the removed metrics.
2.  Scan the file for any other potential references to the removed metrics in logging or result dictionaries.
3.  Update file and class-level comments and docstrings to align with the new evaluation focus.

### Step 5: Refactor `export.py`
Using the analysis from Step 2, modify the results exporter.
1.  Remove the code that writes the columns or keys for the discarded metrics to the output files.
2.  Adjust any logic that may depend on the presence of these metrics.
3.  Update all relevant comments and docstrings to be in English and reflect the new, simplified output format.

### Step 6: Verification
After all files are modified, run the main evaluation script to ensure the system works end-to-end.
1.  Execute the evaluation runner (e.g., `example_run_evaluation.py` or the main evaluation script).
2.  Confirm that the process completes without any `KeyError` or other runtime exceptions.
3.  Inspect the generated output files (e.g., `detailed_results.csv`, `summary_results.csv`) to confirm that the columns corresponding to the removed metrics are no longer present and the new `overall_score` is calculated correctly.
