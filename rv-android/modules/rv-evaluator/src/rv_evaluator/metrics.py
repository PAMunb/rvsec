# rv_evaluator/metrics.py
"""
Simplified metrics collection and statistical analysis for LLM evaluations.

This module provides core metrics collection focused on the essential performance 
indicators for comparing LLM configurations.

Core Metrics:
- Performance: tokens_per_second, total_duration_ms
- Reliability: success_rate (parsing + no errors)
- Token Usage: input_tokens, output_tokens
- Simple Overall Score: weighted combination of speed and reliability
"""

import statistics
from typing import Dict, List, Any, Optional

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.data_structures import LLMResponse


class MetricsCollector:
    """
    Collects core metrics from individual LLM evaluation runs.
    
    Focuses on essential performance indicators without unnecessary complexity.
    """

    def __init__(self):
        """Initialize the MetricsCollector."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_evaluator.metrics",
            {CONTEXT_COMPONENT: "MetricsCollector"}
        )

    def collect_run_metrics(self,
                            response: Optional[LLMResponse],
                            parsed_actions: List[Dict[str, Any]],
                            parsing_errors: List[str],
                            error_info: Optional[Dict[str, Any]] = None,
                            execution_time: float = 0.0) -> Dict[str, Any]:
        """
        Collect core metrics from a single evaluation run.

        Args:
            response: LLM response object (None if generation failed)
            parsed_actions: Successfully parsed actions
            parsing_errors: Parsing error messages
            error_info: Error information dictionary
            execution_time: Total execution time in seconds

        Returns:
            Dictionary with core metrics
        """
        metrics = {
            # Core performance metrics
            "total_duration_ms": 0.0,
            "tokens_per_second": 0.0,
            
            # Token usage metrics
            "input_tokens": 0,
            "output_tokens": 0,
            
            # Success/failure indicators
            "success": False,
            "error_occurred": False,
            "timeout_occurred": False,
            "error_type": "",
            
            # Additional context
            "execution_time_s": execution_time
        }

        # Extract performance metrics from response
        if response:
            metrics.update(self._extract_response_metrics(response))

        # Determine success/failure
        metrics.update(self._determine_success_metrics(parsed_actions, parsing_errors, error_info))

        # Calculate derived metrics
        metrics.update(self._calculate_derived_metrics(metrics))

        return metrics

    def _extract_response_metrics(self, response: LLMResponse) -> Dict[str, Any]:
        """Extract performance metrics from LLM response."""
        # Convert nanoseconds to milliseconds
        ns_to_ms = 1_000_000.0

        return {
            "total_duration_ms": response.total_duration / ns_to_ms if response.total_duration else 0.0,
            "input_tokens": response.input_tokens or 0,
            "output_tokens": response.output_tokens or 0,
            "load_duration_ms": response.load_duration / ns_to_ms if response.load_duration else 0.0,
            "input_tokens_duration_ms": response.input_tokens_duration / ns_to_ms if response.input_tokens_duration else 0.0,
            "output_tokens_duration_ms": response.output_tokens_duration / ns_to_ms if response.output_tokens_duration else 0.0
        }

    def _determine_success_metrics(self,
                                   parsed_actions: List[Dict[str, Any]],
                                   parsing_errors: List[str],
                                   error_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine success/failure metrics."""
        metrics = {
            "error_occurred": False,
            "timeout_occurred": False,
            "error_type": ""
        }
        
        if error_info:
            metrics["error_occurred"] = True
            metrics["error_type"] = error_info.get("type", "unknown")
            metrics["timeout_occurred"] = error_info.get("timeout", False)
        
        # Success = has parsed actions AND no parsing errors AND no runtime errors
        parsing_success = len(parsed_actions) > 0 and len(parsing_errors) == 0
        no_errors = not metrics["error_occurred"]
        metrics["success"] = parsing_success and no_errors
        
        return metrics

    def _calculate_derived_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived performance metrics."""
        derived = {}
        
        # Calculate tokens per second from output generation time
        output_duration_ms = metrics.get("output_tokens_duration_ms", 0)
        output_tokens = metrics.get("output_tokens", 0)
        
        if output_duration_ms > 0 and output_tokens > 0:
            generation_time_sec = output_duration_ms / 1000.0
            derived["tokens_per_second"] = output_tokens / generation_time_sec
        else:
            derived["tokens_per_second"] = 0.0
            
        return derived


class StatisticsCalculator:
    """
    Calculate summary statistics across multiple evaluation runs.
    
    Provides simple aggregations focused on actionable insights.
    """

    def __init__(self):
        """Initialize the StatisticsCalculator."""
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_evaluator.statistics", 
            {CONTEXT_COMPONENT: "StatisticsCalculator"}
        )

    def calculate_summary_statistics(self, runs_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics for a list of runs.

        Args:
            runs_data: List of metrics from individual runs

        Returns:
            Dictionary with aggregated statistics
        """
        if not runs_data:
            return {}

        summary = {}
        
        # Core numeric metrics to aggregate
        core_metrics = [
            "total_duration_ms",
            "tokens_per_second", 
            "input_tokens",
            "output_tokens",
            "execution_time_s"
        ]
        
        # Calculate statistics for each core metric
        for metric in core_metrics:
            values = [float(run.get(metric, 0)) for run in runs_data if isinstance(run.get(metric, 0), (int, float))]
            if values:
                summary[metric] = self._calculate_basic_stats(values)
            else:
                summary[metric] = {"mean": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
        
        # Calculate success rates
        summary.update(self._calculate_success_rates(runs_data))
        
        # Calculate simple overall score
        summary["overall_score"] = self._calculate_simple_score(summary)
        
        return summary

    def _calculate_basic_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate basic statistics for a list of values."""
        if not values:
            return {"mean": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "mean": statistics.mean(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values)
        }

    def _calculate_success_rates(self, runs_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate success and error rates."""
        total_runs = len(runs_data)
        if total_runs == 0:
            return {
                "success_rate": 0.0,
                "error_rate": 0.0,
                "timeout_rate": 0.0
            }

        successes = sum(1 for run in runs_data if run.get("success", False))
        errors = sum(1 for run in runs_data if run.get("error_occurred", False))
        timeouts = sum(1 for run in runs_data if run.get("timeout_occurred", False))

        return {
            "success_rate": successes / total_runs,
            "error_rate": errors / total_runs,
            "timeout_rate": timeouts / total_runs
        }

    def _calculate_simple_score(self, summary: Dict[str, Any]) -> float:
        """
        Calculate simple overall score focused on speed and reliability.
        
        Score = (tokens_per_second * 0.6) + (success_rate * 100 * 0.4)
        
        This gives 60% weight to performance and 40% to reliability.
        Maximum theoretical score is ~100 (assuming 200+ tokens/sec and 100% success).
        """
        mean_tps = summary.get("tokens_per_second", {}).get("mean", 0.0)
        success_rate = summary.get("success_rate", 0.0)
        
        # Simple weighted score
        score = (mean_tps * 0.6) + (success_rate * 100 * 0.4)
        
        return min(score, 100.0)  # Cap at 100 for readability