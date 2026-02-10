# rvandroid/llm/evaluator/metrics.py
"""
Metrics collection and calculation system for LLM evaluation.

This module provides comprehensive metrics collection from LLM responses,
including performance, quality, and error metrics with statistical analysis.

### Architectural Decisions:
- Implements a comprehensive metrics collection framework for LLM evaluation
- Provides unified metrics calculation from LLMResponse objects
- Supports both raw metrics and derived analytical metrics
- Integrates with response parsing for quality assessment
- Enables statistical analysis across multiple runs

### Role in the System:
- Acts as the central metrics calculation engine for evaluation
- Processes LLMResponse objects into structured metrics data
- Calculates derived metrics for performance analysis
- Provides quality assessment of LLM responses
- Enables statistical aggregation across test runs

### Key Considerations:
- Handles edge cases in metrics calculation (division by zero, null values)
- Provides consistent metrics format across different models
- Supports extensible metrics framework for future enhancements
- Integrates with existing response processing components
- Maintains precision in timing and token measurements
"""

import re
import statistics
from typing import Dict, List, Any, Optional

from rvandroid.llm.data_structures import LLMResponse
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class MetricsCollector:
    """
    Collects and calculates comprehensive metrics from LLM evaluation runs.

    Provides unified metrics calculation from LLMResponse objects and response
    content, including performance, quality, and error metrics.
    """

    def __init__(self):
        """Initialize the metrics collector."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.evaluator.metrics",
            {CONTEXT_COMPONENT: "MetricsCollector"}
        )

    def collect_run_metrics(self,
                            response: Optional[LLMResponse],
                            parsed_actions: List[Dict[str, Any]],
                            parsing_errors: List[str],
                            error_info: Optional[Dict[str, Any]] = None,
                            execution_time: float = 0.0) -> Dict[str, Any]:
        """
        Collect comprehensive metrics from a single evaluation run.

        Args:
            response: LLMResponse object (None if error occurred)
            parsed_actions: Successfully parsed actions from response
            parsing_errors: List of parsing error messages
            error_info: Information about any errors that occurred
            execution_time: Total execution time in seconds

        Returns:
            Dictionary containing all collected metrics
        """
        metrics = {}

        # Initialize with default values
        self._initialize_default_metrics(metrics)

        # Collect error information
        if error_info:
            metrics.update(self._collect_error_metrics(error_info))

        # Collect performance metrics from LLMResponse
        if response:
            metrics.update(self._collect_performance_metrics(response))
            metrics.update(self._collect_response_metrics(response))

        # Collect parsing and quality metrics
        metrics.update(self._collect_parsing_metrics(parsed_actions, parsing_errors))

        # Collect derived metrics
        metrics.update(self._calculate_derived_metrics(metrics, execution_time))

        return metrics

    def _initialize_default_metrics(self, metrics: Dict[str, Any]) -> None:
        """Initialize metrics dictionary with default values."""
        default_values = {
            "total_duration_ms": 0.0,
            "load_duration_ms": 0.0,
            "input_tokens": 0,
            "input_tokens_duration_ms": 0.0,
            "output_tokens": 0,
            "output_tokens_duration_ms": 0.0,
            "tokens_per_second": 0.0,
            "input_output_ratio": 0.0,
            "generation_latency_ms": 0.0,
            "parsing_success": False,
            "response_length_chars": 0,
            "actions_count": 0,
            "explanation_quality_score": 0.0,
            "error_occurred": False,
            "error_type": "",
            "timeout_occurred": False
        }
        metrics.update(default_values)

    def _collect_performance_metrics(self, response: LLMResponse) -> Dict[str, Any]:
        """
        Collect performance metrics from LLMResponse object.

        Args:
            response: LLMResponse containing performance data

        Returns:
            Dictionary with performance metrics
        """
        metrics = {}

        # Convert nanoseconds to milliseconds for readability
        # LLMResponse times are in nanoseconds according to documentation
        ns_to_ms = 1_000_000

        metrics["total_duration_ms"] = response.total_duration / ns_to_ms if response.total_duration else 0.0
        metrics["load_duration_ms"] = response.load_duration / ns_to_ms if response.load_duration else 0.0
        metrics["input_tokens"] = response.input_tokens if response.input_tokens else 0
        metrics[
            "input_tokens_duration_ms"] = response.input_tokens_duration / ns_to_ms if response.input_tokens_duration else 0.0
        metrics["output_tokens"] = response.output_tokens if response.output_tokens else 0
        metrics[
            "output_tokens_duration_ms"] = response.output_tokens_duration / ns_to_ms if response.output_tokens_duration else 0.0

        return metrics

    def _collect_response_metrics(self, response: LLMResponse) -> Dict[str, Any]:
        """
        Collect response content metrics.

        Args:
            response: LLMResponse containing generated content

        Returns:
            Dictionary with response metrics
        """
        metrics = {}

        # Response length in characters
        metrics["response_length_chars"] = len(response.content) if response.content else 0

        return metrics

    def _collect_parsing_metrics(self,
                                 parsed_actions: List[Dict[str, Any]],
                                 parsing_errors: List[str]) -> Dict[str, Any]:
        """
        Collect metrics related to response parsing and action quality.

        Args:
            parsed_actions: Successfully parsed actions
            parsing_errors: List of parsing errors

        Returns:
            Dictionary with parsing and quality metrics
        """
        metrics = {}

        # Parsing success
        metrics["parsing_success"] = len(parsed_actions) > 0 and len(parsing_errors) == 0

        # Number of actions extracted
        metrics["actions_count"] = len(parsed_actions)

        # Calculate explanation quality score
        metrics["explanation_quality_score"] = self._calculate_explanation_quality(parsed_actions)

        return metrics

    def _collect_error_metrics(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect error-related metrics.

        Args:
            error_info: Dictionary containing error information

        Returns:
            Dictionary with error metrics
        """
        metrics = {}

        metrics["error_occurred"] = True
        metrics["error_type"] = error_info.get("type", "unknown")
        metrics["timeout_occurred"] = error_info.get("timeout", False)

        return metrics

    def _calculate_derived_metrics(self, metrics: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
        """
        Calculate derived metrics from base metrics.

        Args:
            metrics: Base metrics dictionary
            execution_time: Total execution time in seconds

        Returns:
            Dictionary with derived metrics
        """
        derived = {}

        # Tokens per second (based on output tokens and generation time)
        if metrics["output_tokens_duration_ms"] > 0:
            generation_time_sec = metrics["output_tokens_duration_ms"] / 1000.0
            derived["tokens_per_second"] = metrics["output_tokens"] / generation_time_sec
        else:
            derived["tokens_per_second"] = 0.0

        # Input/Output token ratio
        if metrics["input_tokens"] > 0:
            derived["input_output_ratio"] = metrics["output_tokens"] / metrics["input_tokens"]
        else:
            derived["input_output_ratio"] = 0.0

        # Generation latency (time to first token + generation time)
        derived["generation_latency_ms"] = (
                metrics["input_tokens_duration_ms"] + metrics["output_tokens_duration_ms"]
        )

        return derived

    def _calculate_explanation_quality(self, actions: List[Dict[str, Any]]) -> float:
        """
        Calculate a quality score for action explanations.

        Args:
            actions: List of action dictionaries with explanations

        Returns:
            Quality score between 0.0 and 1.0
        """
        if not actions:
            return 0.0

        total_score = 0.0

        for action in actions:
            explanation = action.get("explanation", "")
            score = self._score_explanation(explanation)
            total_score += score

        return total_score / len(actions)

    def _score_explanation(self, explanation: str) -> float:
        """
        Score a single explanation for quality.

        Args:
            explanation: Explanation text to score

        Returns:
            Score between 0.0 and 1.0
        """
        if not explanation or not explanation.strip():
            return 0.0

        score = 0.0

        # Length check (reasonable explanations are 10-200 characters)
        length = len(explanation.strip())
        if 10 <= length <= 200:
            score += 0.3
        elif length > 5:
            score += 0.1

        # Content quality indicators
        quality_indicators = [
            r'\b(test|testing|verify|check|validate)\b',  # Testing terminology
            r'\b(click|tap|scroll|input|enter|select)\b',  # Action verbs
            r'\b(button|field|menu|screen|element)\b',  # UI elements
            r'\b(functionality|feature|behavior)\b'  # Functional terms
        ]

        for pattern in quality_indicators:
            if re.search(pattern, explanation.lower()):
                score += 0.175  # Each indicator adds to score

        return min(score, 1.0)  # Cap at 1.0


class StatisticsCalculator:
    """
    Calculates statistical summaries across multiple evaluation runs.

    Provides aggregation and statistical analysis of metrics collected
    from multiple runs of the same configuration.
    """

    def __init__(self):
        """Initialize the statistics calculator."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.evaluator.statistics",
            {CONTEXT_COMPONENT: "StatisticsCalculator"}
        )

    def calculate_summary_statistics(self,
                                     runs_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics across multiple runs.

        Args:
            runs_data: List of metrics dictionaries from individual runs

        Returns:
            Dictionary containing summary statistics
        """
        if not runs_data:
            return {}

        summary = {}

        # Get numeric metrics from the first run to determine which metrics to process
        numeric_metrics = self._get_numeric_metrics(runs_data[0])

        # Calculate statistics for each numeric metric
        for metric in numeric_metrics:
            values = self._extract_metric_values(runs_data, metric)
            summary[metric] = self._calculate_metric_statistics(values)

        # Calculate success rates
        summary.update(self._calculate_success_rates(runs_data))

        # Calculate overall score
        summary["overall_score"] = self._calculate_overall_score(summary)

        return summary

    def _get_numeric_metrics(self, sample_run: Dict[str, Any]) -> List[str]:
        """
        Get list of numeric metrics from a sample run.

        Args:
            sample_run: Sample metrics dictionary

        Returns:
            List of numeric metric names
        """
        numeric_metrics = []

        for key, value in sample_run.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_metrics.append(key)

        return numeric_metrics

    def _extract_metric_values(self,
                               runs_data: List[Dict[str, Any]],
                               metric: str) -> List[float]:
        """
        Extract values for a specific metric from all runs.

        Args:
            runs_data: List of run metrics
            metric: Metric name to extract

        Returns:
            List of metric values
        """
        values = []

        for run in runs_data:
            value = run.get(metric, 0)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))

        return values

    def _calculate_metric_statistics(self, values: List[float]) -> Dict[str, float]:
        """
        Calculate statistical measures for a list of values.

        Args:
            values: List of numeric values

        Returns:
            Dictionary with statistical measures
        """
        if not values:
            return {
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0
            }

        stats = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values)
        }

        # Standard deviation (handle case with single value)
        if len(values) > 1:
            stats["std_dev"] = statistics.stdev(values)
        else:
            stats["std_dev"] = 0.0

        return stats

    def _calculate_success_rates(self, runs_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate success rates for boolean metrics.

        Args:
            runs_data: List of run metrics

        Returns:
            Dictionary with success rates
        """
        success_rates = {}

        # Calculate parsing success rate
        parsing_successes = sum(1 for run in runs_data if run.get("parsing_success", False))
        success_rates["parsing_success_rate"] = parsing_successes / len(runs_data)

        # Calculate error rate
        errors = sum(1 for run in runs_data if run.get("error_occurred", False))
        success_rates["error_rate"] = errors / len(runs_data)

        # Calculate timeout rate
        timeouts = sum(1 for run in runs_data if run.get("timeout_occurred", False))
        success_rates["timeout_rate"] = timeouts / len(runs_data)

        # Overall success rate (parsing success and no errors)
        successful_runs = sum(1 for run in runs_data
                              if run.get("parsing_success", False) and not run.get("error_occurred", False))
        success_rates["overall_success_rate"] = successful_runs / len(runs_data)

        return success_rates

    def _calculate_overall_score(self, summary: Dict[str, Any]) -> float:
        """
        Calculate an overall performance score for ranking configurations.

        Args:
            summary: Summary statistics dictionary

        Returns:
            Overall score between 0 and 100
        """
        score = 0.0

        # Success rates (40% of score)
        success_component = (
                summary.get("overall_success_rate", 0) * 25 +
                summary.get("parsing_success_rate", 0) * 10 +
                (1 - summary.get("error_rate", 1)) * 5
        )
        score += success_component

        # Performance (30% of score)
        # Normalize tokens per second (assume max reasonable value of 100)
        tokens_per_sec = summary.get("tokens_per_second", {}).get("mean", 0)
        score += min(tokens_per_sec / 100.0, 1.0) * 20

        # Normalize latency (assume max reasonable value of 10000ms)
        latency = summary.get("generation_latency_ms", {}).get("mean", 10000)
        latency_score = max(0, 1 - (latency / 10000.0))
        score += latency_score * 10

        # Quality (20% of score)
        explanation_quality = summary.get("explanation_quality_score", {}).get("mean", 0)
        score += explanation_quality * 15

        # Actions count (reasonable number, penalize too few or too many)
        actions_count = summary.get("actions_count", {}).get("mean", 0)
        if 1 <= actions_count <= 5:
            score += 5
        elif actions_count > 0:
            score += 2

        # Consistency (10% of score) - lower standard deviation is better
        # Normalize by checking std dev of key metrics
        consistency_score = 0
        for metric in ["tokens_per_second", "explanation_quality_score"]:
            if metric in summary:
                mean_val = summary[metric].get("mean", 0)
                std_val = summary[metric].get("std_dev", 0)
                if mean_val > 0:
                    cv = std_val / mean_val  # Coefficient of variation
                    consistency_score += max(0, 1 - cv) * 5

        score += consistency_score

        return min(score, 100.0)  # Cap at 100
   