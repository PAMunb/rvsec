"""
Batch Actions Analyzer for the test framework.

This module provides analysis tools for comparing batch action strategies 
with single action approaches, generating visualizations and insights.
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple, Set

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from rv_android_core.test_framework.batch_metrics import BatchActionMetrics, BatchMetricsCollector
from rv_android_core.test_framework.executor import TestResult
from rv_android_core.test_framework.config import ToolConfiguration


class BatchAnalyzer:
    """
    Analyzer for batch action performance in test framework.
    
    Compares batch action strategies with single action approaches,
    generating insights and visualizations to quantify improvements.
    
    ### Key Responsibilities:
    - Analyzes batch metrics from test results
    - Compares batch and single action performance
    - Provides insights on efficiency improvements
    - Generates visualizations for comparative analysis
    - Integrates with the test framework's result analysis
    """
    
    def __init__(self, results: List[TestResult], output_dir: str = "analysis_results"):
        """
        Initialize the batch analyzer.
        
        Args:
            results: List of test results
            output_dir: Directory for analysis output
        """
        self.results = results
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Group results by configuration and strategy type
        self.batch_results = {}
        self.single_results = {}
        self.comparative_results = {}
        
        # Collect and organize results
        self._organize_results()
        
    def _organize_results(self) -> None:
        """
        Organize test results by configuration and strategy type.
        
        This separates batch action results from single action results
        for proper comparative analysis.
        """
        # Group results by configuration ID
        configs = {}
        for result in self.results:
            config_id = result.test_case.tool_config.get_id()
            
            if config_id not in configs:
                configs[config_id] = []
                
            configs[config_id].append(result)
        
        # Classify configurations as batch or single based on strategy
        for config_id, results in configs.items():
            # Get strategy from first result
            strategy_type = results[0].test_case.tool_config.strategy_type.lower()
            
            # Classify as batch if strategy contains "batch", "flow", or "sequence"
            is_batch = any(term in strategy_type for term in ["batch", "flow", "sequence"])
            
            if is_batch:
                self.batch_results[config_id] = results
            else:
                self.single_results[config_id] = results
    
    def analyze_batch_performance(self) -> Dict[str, BatchActionMetrics]:
        """
        Analyze batch action performance metrics.
        
        Returns:
            Dictionary mapping configuration IDs to BatchActionMetrics
        """
        batch_metrics = {}
        
        # Analyze each batch configuration
        for config_id, results in self.batch_results.items():
            # Extract batch metrics from test results
            metrics = self._extract_batch_metrics(config_id, results)
            batch_metrics[config_id] = metrics
            
        return batch_metrics
    
    def _extract_batch_metrics(self, config_id: str, results: List[TestResult]) -> BatchActionMetrics:
        """
        Extract batch metrics from test results.
        
        Args:
            config_id: Configuration ID
            results: List of test results for this configuration
            
        Returns:
            BatchActionMetrics instance
        """
        # Get configuration details from first result
        first_result = results[0]
        tool_config = first_result.test_case.tool_config
        
        # Create metrics instance
        metrics = BatchActionMetrics(
            config_id=config_id,
            tool_name=tool_config.tool_name,
            llm_type=tool_config.llm_type,
            llm_model=tool_config.llm_model,
            strategy_type=tool_config.strategy_type
        )
        
        # Look for batch_metrics.json files in result directories
        collectors = []
        for result in results:
            # Check if app completed successfully
            if result.status != "completed":
                continue
                
            # Check for batch metrics file
            metrics_file = os.path.join(result.test_case.get_result_dir(), "batch_metrics.json")
            if os.path.exists(metrics_file):
                collector = BatchMetricsCollector.from_file(metrics_file)
                if collector:
                    collectors.append(collector)
        
        # If no metrics files found, return empty metrics
        if not collectors:
            return metrics
            
        # Aggregate metrics from all collectors
        aggregated_metrics = self._aggregate_batch_metrics(collectors)
        
        # Map aggregated metrics to BatchActionMetrics structure
        metrics.total_batch_executions = aggregated_metrics.get("batch_executions", 0)
        metrics.successful_batch_executions = aggregated_metrics.get("successful_batch_executions", 0)
        metrics.batch_success_rate = aggregated_metrics.get("batch_success_rate", 0.0)
        metrics.average_batch_size = aggregated_metrics.get("average_batch_size", 0.0)
        
        metrics.total_actions = aggregated_metrics.get("single_actions", 0)
        metrics.successful_actions = aggregated_metrics.get("successful_single_actions", 0)
        metrics.action_success_rate = aggregated_metrics.get("action_success_rate", 0.0)
        
        metrics.avg_batch_execution_time = aggregated_metrics.get("avg_batch_execution_time", 0.0)
        metrics.avg_single_action_time = aggregated_metrics.get("avg_single_action_time", 0.0)
        metrics.time_per_effective_action = aggregated_metrics.get("time_per_effective_action", 0.0)
        metrics.tokens_per_effective_action = aggregated_metrics.get("tokens_per_effective_action", 0.0)
        metrics.llm_call_count = aggregated_metrics.get("llm_call_count", 0)
        metrics.llm_token_usage = aggregated_metrics.get("llm_token_usage", 0)
        metrics.llm_overhead_reduction = aggregated_metrics.get("llm_overhead_reduction", 0.0)
        metrics.action_throughput = aggregated_metrics.get("action_throughput", 0.0)
        
        metrics.batch_mop_triggered_count = aggregated_metrics.get("batch_mop_triggered_count", 0)
        metrics.single_mop_triggered_count = aggregated_metrics.get("single_mop_triggered_count", 0)
        
        # Add MOP coverage from coverage metrics if available (simplified, using MOP method coverage from first result)
        # This is an approximation as we'd need more detailed MOP analysis
        if results[0].coverage_data and "mop_method_coverage" in results[0].coverage_data:
            metrics.mop_coverage = results[0].coverage_data["mop_method_coverage"] / 100.0  # Convert from percentage
        
        # Copy pattern metrics
        metrics.pattern_distributions = aggregated_metrics.get("pattern_distributions", {})
        metrics.pattern_success_rates = aggregated_metrics.get("pattern_success_rates", {})
        metrics.batch_completion_rates = aggregated_metrics.get("batch_completion_rates", {})
        metrics.batch_interruption_reasons = aggregated_metrics.get("batch_interruption_reasons", {})
        
        return metrics
    
    def _aggregate_batch_metrics(self, collectors: List[BatchMetricsCollector]) -> Dict[str, Any]:
        """
        Aggregate metrics from multiple BatchMetricsCollector instances.
        
        Args:
            collectors: List of BatchMetricsCollector instances
            
        Returns:
            Dictionary with aggregated metrics
        """
        # Initialize aggregated metrics
        aggregated = {
            "batch_executions": 0,
            "successful_batch_executions": 0,
            "single_actions": 0,
            "successful_single_actions": 0,
            "llm_call_count": 0,
            "llm_token_usage": 0,
            "batch_mop_triggered_count": 0,
            "single_mop_triggered_count": 0,
            "pattern_distributions": {
                "form": 0,
                "list": 0,
                "tabs": 0,
                "navigation": 0,
                "dialog": 0,
                "unknown": 0
            },
            "batch_execution_times": [],
            "single_action_times": [],
            "pattern_success_rates": {},
            "batch_completion_rates": {},
            "batch_interruption_reasons": {}
        }
        
        # Combine metrics from all collectors
        for collector in collectors:
            # Get metrics from this collector
            metrics = collector.calculate_metrics()
            
            # Update basic counters
            aggregated["batch_executions"] += metrics.get("batch_executions", 0)
            aggregated["successful_batch_executions"] += metrics.get("successful_batch_executions", 0)
            aggregated["single_actions"] += metrics.get("single_actions", 0)
            aggregated["successful_single_actions"] += metrics.get("successful_single_actions", 0)
            aggregated["llm_call_count"] += metrics.get("llm_call_count", 0)
            aggregated["llm_token_usage"] += metrics.get("llm_token_usage", 0)
            aggregated["batch_mop_triggered_count"] += metrics.get("batch_mop_triggered_count", 0)
            aggregated["single_mop_triggered_count"] += metrics.get("single_mop_triggered_count", 0)
            
            # Extend time lists
            if "raw_data" in metrics:
                raw = metrics["raw_data"]
                aggregated["batch_execution_times"].extend(raw.get("batch_execution_times", []))
                aggregated["single_action_times"].extend(raw.get("single_action_times", []))
            
            # Update pattern distributions
            for pattern, count in metrics.get("pattern_distributions", {}).items():
                if pattern in aggregated["pattern_distributions"]:
                    aggregated["pattern_distributions"][pattern] += count
            
            # Update pattern success rates (will be recalculated at the end)
            for pattern, data in metrics.get("pattern_success_rates", {}).items():
                if pattern not in aggregated["pattern_success_rates"]:
                    aggregated["pattern_success_rates"][pattern] = {
                        "success_rate": 0.0,
                        "executions": 0,
                        "successes": 0,
                        "execution_times": [],
                        "batch_sizes": [],
                        "mops_triggered": 0
                    }
                
                agg_data = aggregated["pattern_success_rates"][pattern]
                # Raw data is needed to recalculate averages
                if "raw_data" in metrics and "pattern_execution_stats" in metrics["raw_data"]:
                    pattern_stats = metrics["raw_data"]["pattern_execution_stats"].get(pattern, {})
                    agg_data["executions"] += pattern_stats.get("executions", 0)
                    agg_data["successes"] += pattern_stats.get("successes", 0)
                    agg_data["execution_times"].extend(pattern_stats.get("execution_times", []))
                    agg_data["batch_sizes"].extend(pattern_stats.get("batch_sizes", []))
                    agg_data["mops_triggered"] += pattern_stats.get("mops_triggered", 0)
            
            # Update completion rates (will be recalculated at the end)
            for pattern, rate in metrics.get("batch_completion_rates", {}).items():
                if pattern not in aggregated["batch_completion_rates"]:
                    aggregated["batch_completion_rates"][pattern] = {
                        "total_actions": 0,
                        "completed_actions": 0
                    }
                
                # Raw data needed to recalculate rates
                if "raw_data" in metrics and "batch_completion_rates" in metrics["raw_data"]:
                    completion_data = metrics["raw_data"]["batch_completion_rates"].get(pattern, {})
                    aggregated["batch_completion_rates"][pattern]["total_actions"] += completion_data.get("total_actions", 0)
                    aggregated["batch_completion_rates"][pattern]["completed_actions"] += completion_data.get("completed_actions", 0)
            
            # Update interruption reasons
            for reason, count in metrics.get("batch_interruption_reasons", {}).items():
                if reason not in aggregated["batch_interruption_reasons"]:
                    aggregated["batch_interruption_reasons"][reason] = 0
                aggregated["batch_interruption_reasons"][reason] += count
        
        # Calculate derived metrics from aggregated data
        
        # Success rates
        if aggregated["batch_executions"] > 0:
            aggregated["batch_success_rate"] = (aggregated["successful_batch_executions"] / aggregated["batch_executions"]) * 100
        else:
            aggregated["batch_success_rate"] = 0.0
            
        if aggregated["single_actions"] > 0:
            aggregated["action_success_rate"] = (aggregated["successful_single_actions"] / aggregated["single_actions"]) * 100
        else:
            aggregated["action_success_rate"] = 0.0
        
        # Average batch size
        batch_sizes = []
        for pattern, data in aggregated["pattern_success_rates"].items():
            batch_sizes.extend(data["batch_sizes"])
            
        if batch_sizes:
            aggregated["average_batch_size"] = sum(batch_sizes) / len(batch_sizes)
        else:
            aggregated["average_batch_size"] = 0.0
        
        # Time metrics
        if aggregated["batch_execution_times"]:
            aggregated["avg_batch_execution_time"] = sum(aggregated["batch_execution_times"]) / len(aggregated["batch_execution_times"])
        else:
            aggregated["avg_batch_execution_time"] = 0.0
            
        if aggregated["single_action_times"]:
            aggregated["avg_single_action_time"] = sum(aggregated["single_action_times"]) / len(aggregated["single_action_times"])
        else:
            aggregated["avg_single_action_time"] = 0.0
        
        # Time per effective action
        if aggregated["successful_single_actions"] > 0:
            total_execution_time = sum(aggregated["batch_execution_times"]) + sum(aggregated["single_action_times"])
            aggregated["time_per_effective_action"] = total_execution_time / aggregated["successful_single_actions"]
        else:
            aggregated["time_per_effective_action"] = 0.0
        
        # Token efficiency
        if aggregated["successful_single_actions"] > 0:
            aggregated["tokens_per_effective_action"] = aggregated["llm_token_usage"] / aggregated["successful_single_actions"]
        else:
            aggregated["tokens_per_effective_action"] = 0.0
        
        # LLM overhead reduction
        if aggregated["single_actions"] > 0:
            single_action_equivalent_calls = aggregated["single_actions"]
            actual_calls = aggregated["llm_call_count"]
            call_reduction = (single_action_equivalent_calls - actual_calls) / single_action_equivalent_calls
            aggregated["llm_overhead_reduction"] = call_reduction * 100
        else:
            aggregated["llm_overhead_reduction"] = 0.0
        
        # Recalculate pattern success rates
        for pattern, data in aggregated["pattern_success_rates"].items():
            if data["executions"] > 0:
                data["success_rate"] = (data["successes"] / data["executions"]) * 100
                data["avg_execution_time"] = sum(data["execution_times"]) / len(data["execution_times"]) if data["execution_times"] else 0.0
                data["avg_batch_size"] = sum(data["batch_sizes"]) / len(data["batch_sizes"]) if data["batch_sizes"] else 0.0
        
        # Recalculate completion rates
        completion_rates = {}
        for pattern, data in aggregated["batch_completion_rates"].items():
            if data["total_actions"] > 0:
                completion_rates[pattern] = (data["completed_actions"] / data["total_actions"]) * 100
            else:
                completion_rates[pattern] = 0.0
        aggregated["batch_completion_rates"] = completion_rates
        
        return aggregated
    
    def compare_batch_vs_single(self) -> Dict[str, Any]:
        """
        Compare batch and single action strategies.
        
        Analyzes results to quantify improvements and tradeoffs between
        batch action strategies and single action approaches.
        
        Returns:
            Dictionary with comparison results
        """
        batch_metrics = self.analyze_batch_performance()
        
        # For single action approaches, calculate basic metrics
        single_metrics = self._calculate_single_metrics()
        
        # Find the best batch and single configurations
        best_batch = self._find_best_configuration(batch_metrics, "efficiency")
        best_single = self._find_best_single_configuration(single_metrics)
        
        # Calculate improvement percentages
        improvements = self._calculate_improvements(best_batch, best_single)
        
        # Create comparison results
        comparison = {
            "batch_metrics": {config_id: metrics.to_dict() for config_id, metrics in batch_metrics.items()},
            "single_metrics": single_metrics,
            "best_batch_config": best_batch.config_id if best_batch else None,
            "best_single_config": best_single.get("config_id") if best_single else None,
            "improvements": improvements,
            "pattern_effectiveness": self._analyze_pattern_effectiveness(batch_metrics)
        }
        
        # Generate visualizations
        chart_files = self._create_comparison_visualizations(batch_metrics, single_metrics, improvements)
        comparison["chart_files"] = chart_files
        
        return comparison
    
    def _calculate_single_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate metrics for single action approaches.
        
        Returns:
            Dictionary mapping configuration IDs to metrics
        """
        single_metrics = {}
        
        for config_id, results in self.single_results.items():
            # Extract configuration details
            first_result = results[0]
            tool_config = first_result.test_case.tool_config
            
            # Calculate basic metrics
            successful_results = [r for r in results if r.status == "completed"]
            success_rate = (len(successful_results) / len(results)) * 100 if results else 0
            
            # Calculate execution time
            execution_times = [r.execution_time for r in successful_results]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
            
            # Extract coverage metrics (simplified)
            method_coverage = 0.0
            activity_coverage = 0.0
            mop_coverage = 0.0
            
            for result in successful_results:
                if result.coverage_data:
                    method_coverage += result.coverage_data.get("method_coverage", 0.0)
                    activity_coverage += result.coverage_data.get("activity_coverage", 0.0)
                    mop_coverage += result.coverage_data.get("mop_method_coverage", 0.0)
            
            # Calculate averages
            if successful_results:
                method_coverage /= len(successful_results)
                activity_coverage /= len(successful_results)
                mop_coverage /= len(successful_results)
            
            # Store metrics
            single_metrics[config_id] = {
                "config_id": config_id,
                "tool_name": tool_config.tool_name,
                "llm_type": tool_config.llm_type,
                "llm_model": tool_config.llm_model,
                "strategy_type": tool_config.strategy_type,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "method_coverage": method_coverage,
                "activity_coverage": activity_coverage,
                "mop_coverage": mop_coverage,
                "result_count": len(results),
                "successful_count": len(successful_results)
            }
            
        return single_metrics
    
    def _find_best_configuration(self, batch_metrics: Dict[str, BatchActionMetrics], 
                               criteria: str = "efficiency") -> Optional[BatchActionMetrics]:
        """
        Find the best batch configuration based on criteria.
        
        Args:
            batch_metrics: Dictionary of BatchActionMetrics by config_id
            criteria: Selection criteria ("efficiency" or "effectiveness")
            
        Returns:
            Best BatchActionMetrics or None if no metrics
        """
        if not batch_metrics:
            return None
            
        if criteria == "effectiveness":
            # Sort by effectiveness score
            sorted_metrics = sorted(
                batch_metrics.values(),
                key=lambda m: m.get_effectiveness_score(),
                reverse=True
            )
        else:
            # Default to efficiency score
            sorted_metrics = sorted(
                batch_metrics.values(),
                key=lambda m: m.get_efficiency_score(),
                reverse=True
            )
            
        return sorted_metrics[0] if sorted_metrics else None
    
    def _find_best_single_configuration(self, single_metrics: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best single action configuration.
        
        Args:
            single_metrics: Dictionary of metrics by config_id
            
        Returns:
            Best metrics dictionary or None if no metrics
        """
        if not single_metrics:
            return None
            
        # Sort by success rate and coverage
        sorted_metrics = sorted(
            single_metrics.values(),
            key=lambda m: (m["success_rate"] * 0.6 + m["mop_coverage"] * 0.4),
            reverse=True
        )
            
        return sorted_metrics[0] if sorted_metrics else None
    
    def _calculate_improvements(self, best_batch: Optional[BatchActionMetrics], 
                              best_single: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate improvement percentages between batch and single approaches.
        
        Args:
            best_batch: Best batch configuration metrics
            best_single: Best single configuration metrics
            
        Returns:
            Dictionary with improvement percentages
        """
        improvements = {}
        
        if not best_batch or not best_single:
            return improvements
            
        # Calculate time efficiency improvement
        # Batch methods are expected to reduce time per effective action
        if best_single["avg_execution_time"] > 0:
            time_improvement = ((best_single["avg_execution_time"] - best_batch.time_per_effective_action) / 
                               best_single["avg_execution_time"]) * 100
            improvements["time_efficiency"] = time_improvement
        
        # Calculate LLM call reduction
        # Already calculated in batch metrics
        improvements["llm_call_reduction"] = best_batch.llm_overhead_reduction
        
        # Calculate MOP coverage improvement
        if best_single["mop_coverage"] > 0:
            mop_improvement = ((best_batch.mop_coverage * 100 - best_single["mop_coverage"]) / 
                              best_single["mop_coverage"]) * 100
            improvements["mop_coverage"] = mop_improvement
        
        # Calculate action throughput improvement
        # Action throughput is actions per second, higher is better
        # Calculate approximate single action throughput
        single_throughput = 1.0 / best_single["avg_execution_time"] if best_single["avg_execution_time"] > 0 else 0
        
        if single_throughput > 0:
            throughput_improvement = ((best_batch.action_throughput - single_throughput) / 
                                    single_throughput) * 100
            improvements["action_throughput"] = throughput_improvement
        
        return improvements
    
    def _analyze_pattern_effectiveness(self, batch_metrics: Dict[str, BatchActionMetrics]) -> Dict[str, Any]:
        """
        Analyze effectiveness of different UI patterns.
        
        Args:
            batch_metrics: Dictionary of BatchActionMetrics by config_id
            
        Returns:
            Dictionary with pattern effectiveness analysis
        """
        if not batch_metrics:
            return {}
            
        # Collect pattern metrics across configurations
        pattern_data = {}
        
        for config_id, metrics in batch_metrics.items():
            # Process success rates
            for pattern, data in metrics.pattern_success_rates.items():
                if pattern not in pattern_data:
                    pattern_data[pattern] = {
                        "success_rates": [],
                        "batch_sizes": [],
                        "execution_times": [],
                        "mops_triggered": 0,
                        "completion_rates": []
                    }
                
                # Add data
                pattern_data[pattern]["success_rates"].append(data.get("success_rate", 0.0))
                pattern_data[pattern]["batch_sizes"].append(data.get("avg_batch_size", 0.0))
                pattern_data[pattern]["execution_times"].append(data.get("avg_execution_time", 0.0))
                pattern_data[pattern]["mops_triggered"] += data.get("mops_triggered", 0)
                
                # Add completion rate if available
                if pattern in metrics.batch_completion_rates:
                    pattern_data[pattern]["completion_rates"].append(metrics.batch_completion_rates[pattern])
        
        # Calculate averages
        pattern_effectiveness = {}
        
        for pattern, data in pattern_data.items():
            # Calculate averages
            avg_success_rate = sum(data["success_rates"]) / len(data["success_rates"]) if data["success_rates"] else 0
            avg_batch_size = sum(data["batch_sizes"]) / len(data["batch_sizes"]) if data["batch_sizes"] else 0
            avg_execution_time = sum(data["execution_times"]) / len(data["execution_times"]) if data["execution_times"] else 0
            avg_completion_rate = sum(data["completion_rates"]) / len(data["completion_rates"]) if data["completion_rates"] else 0
            
            # Calculate efficiency (actions per second)
            efficiency = avg_batch_size / avg_execution_time if avg_execution_time > 0 else 0
            
            # Calculate effectiveness score
            effectiveness = (avg_success_rate * 0.4 + avg_completion_rate * 0.6)
            
            pattern_effectiveness[pattern] = {
                "avg_success_rate": avg_success_rate,
                "avg_batch_size": avg_batch_size,
                "avg_execution_time": avg_execution_time,
                "avg_completion_rate": avg_completion_rate,
                "mops_triggered": data["mops_triggered"],
                "efficiency": efficiency,
                "effectiveness": effectiveness
            }
        
        # Rank patterns
        ranked_by_effectiveness = sorted(
            pattern_effectiveness.items(),
            key=lambda x: x[1]["effectiveness"],
            reverse=True
        )
        
        ranked_by_efficiency = sorted(
            pattern_effectiveness.items(),
            key=lambda x: x[1]["efficiency"],
            reverse=True
        )
        
        return {
            "pattern_metrics": pattern_effectiveness,
            "best_by_effectiveness": [p[0] for p in ranked_by_effectiveness][:3],
            "best_by_efficiency": [p[0] for p in ranked_by_efficiency][:3]
        }
    
    def _create_comparison_visualizations(self, batch_metrics: Dict[str, BatchActionMetrics],
                                        single_metrics: Dict[str, Dict[str, Any]],
                                        improvements: Dict[str, float]) -> Dict[str, str]:
        """
        Create visualizations comparing batch and single action approaches.
        
        Args:
            batch_metrics: Dictionary of BatchActionMetrics by config_id
            single_metrics: Dictionary of single action metrics by config_id
            improvements: Dictionary with improvement percentages
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        chart_files = {}
        
        # Create efficiency comparison chart
        efficiency_chart = os.path.join(self.output_dir, "batch_efficiency_comparison.png")
        self._create_efficiency_chart(batch_metrics, single_metrics, efficiency_chart)
        chart_files["efficiency_comparison"] = efficiency_chart
        
        # Create pattern effectiveness chart
        pattern_chart = os.path.join(self.output_dir, "pattern_effectiveness.png")
        self._create_pattern_chart(batch_metrics, pattern_chart)
        chart_files["pattern_effectiveness"] = pattern_chart
        
        # Create improvements chart
        improvements_chart = os.path.join(self.output_dir, "batch_improvements.png")
        self._create_improvements_chart(improvements, improvements_chart)
        chart_files["improvements"] = improvements_chart
        
        # Create batch size vs success rate chart
        batch_size_chart = os.path.join(self.output_dir, "batch_size_analysis.png")
        self._create_batch_size_chart(batch_metrics, batch_size_chart)
        chart_files["batch_size_analysis"] = batch_size_chart
        
        return chart_files
    
    def _create_efficiency_chart(self, batch_metrics: Dict[str, BatchActionMetrics],
                               single_metrics: Dict[str, Dict[str, Any]],
                               output_file: str) -> None:
        """
        Create chart comparing efficiency of batch vs. single approaches.
        
        Args:
            batch_metrics: Dictionary of BatchActionMetrics by config_id
            single_metrics: Dictionary of single action metrics by config_id
            output_file: Path to save the chart
        """
        # Prepare data
        batch_configs = list(batch_metrics.keys())
        batch_times = [metrics.time_per_effective_action for metrics in batch_metrics.values()]
        batch_llm_overhead = [metrics.llm_overhead_reduction for metrics in batch_metrics.values()]
        batch_labels = [f"{metrics.tool_name}/{metrics.strategy_type}" for metrics in batch_metrics.values()]
        
        single_configs = list(single_metrics.keys())
        single_times = [metrics["avg_execution_time"] for metrics in single_metrics.values()]
        single_labels = [f"{metrics['tool_name']}/{metrics['strategy_type']}" for metrics in single_metrics.values()]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # First subplot: Time per effective action comparison
        batch_bars = ax1.barh(batch_labels, batch_times, color='skyblue', alpha=0.7, label='Batch Strategy')
        
        # Add single action times
        if single_times:
            # Calculate average
            avg_single_time = sum(single_times) / len(single_times)
            # Draw line for average single action time
            ax1.axvline(x=avg_single_time, color='tomato', linestyle='--', linewidth=2, 
                      label=f'Avg Single Action ({avg_single_time:.2f}s)')
        
        # Add value labels
        for bar in batch_bars:
            width = bar.get_width()
            ax1.text(
                width + 0.3,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.2f}s',
                ha='left', va='center',
                fontsize=9
            )
        
        # Set chart properties
        ax1.set_xlabel('Time per Effective Action (s)')
        ax1.set_title('Execution Efficiency (lower is better)')
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.5)
        
        # Second subplot: LLM overhead reduction
        bars2 = ax2.barh(batch_labels, batch_llm_overhead, color='lightgreen', alpha=0.7)
        
        # Add value labels
        for bar in bars2:
            width = bar.get_width()
            ax2.text(
                width + 2,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.1f}%',
                ha='left', va='center',
                fontsize=9
            )
        
        # Set chart properties
        ax2.set_xlabel('LLM Overhead Reduction (%)')
        ax2.set_title('LLM Call Reduction')
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Set overall title
        fig.suptitle('Batch vs. Single Action Efficiency Comparison', fontsize=14, y=0.98)
        
        # Save chart
        plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust for suptitle
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_pattern_chart(self, batch_metrics: Dict[str, BatchActionMetrics], output_file: str) -> None:
        """
        Create chart visualizing effectiveness of different UI patterns.
        
        Args:
            batch_metrics: Dictionary of BatchActionMetrics by config_id
            output_file: Path to save the chart
        """
        if not batch_metrics:
            return
            
        # Get the first configuration with pattern data
        pattern_data = None
        for metrics in batch_metrics.values():
            if metrics.pattern_success_rates:
                pattern_data = metrics.pattern_success_rates
                break
        
        if not pattern_data:
            return
            
        # Prepare data
        patterns = list(pattern_data.keys())
        success_rates = [data.get("success_rate", 0) for _, data in pattern_data.items()]
        avg_batch_sizes = [data.get("avg_batch_size", 0) for _, data in pattern_data.items()]
        avg_exec_times = [data.get("avg_execution_time", 0) for _, data in pattern_data.items()]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # First subplot: Success rates and batch sizes
        x = range(len(patterns))
        
        # Success rate bars
        bars1 = ax1.bar([i - 0.2 for i in x], success_rates, width=0.4, label='Success Rate (%)', color='lightblue')
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                height + 1,
                f'{height:.1f}%',
                ha='center', va='bottom',
                fontsize=9
            )
        
        # Batch size bars
        ax1_t = ax1.twinx()
        bars2 = ax1_t.bar([i + 0.2 for i in x], avg_batch_sizes, width=0.4, label='Avg Batch Size', color='lightgreen')
        
        # Add value labels
        for bar in bars2:
            height = bar.get_height()
            ax1_t.text(
                bar.get_x() + bar.get_width() / 2,
                height + 0.1,
                f'{height:.1f}',
                ha='center', va='bottom',
                fontsize=9,
                color='green'
            )
        
        # Set chart properties
        ax1.set_xticks(x)
        ax1.set_xticklabels(patterns)
        ax1.set_ylabel('Success Rate (%)')
        ax1_t.set_ylabel('Avg Batch Size')
        ax1.set_title('Pattern Success Rates and Batch Sizes')
        
        # Add dual legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1_t.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
        
        # Second subplot: Execution time per action
        # Calculate actions per second (higher is better)
        actions_per_second = []
        for i in range(len(patterns)):
            batch_size = avg_batch_sizes[i]
            exec_time = avg_exec_times[i]
            if exec_time > 0:
                actions_per_second.append(batch_size / exec_time)
            else:
                actions_per_second.append(0)
        
        bars3 = ax2.bar(patterns, actions_per_second, color='orange', alpha=0.7)
        
        # Add value labels
        for bar in bars3:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                height + 0.1,
                f'{height:.2f}',
                ha='center', va='bottom',
                fontsize=9
            )
        
        # Set chart properties
        ax2.set_ylabel('Actions per Second')
        ax2.set_title('Pattern Efficiency (higher is better)')
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Set overall title
        fig.suptitle('UI Pattern Effectiveness Analysis', fontsize=14, y=0.98)
        
        # Save chart
        plt.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust for suptitle
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_improvements_chart(self, improvements: Dict[str, float], output_file: str) -> None:
        """
        Create chart visualizing improvements from batch strategies.
        
        Args:
            improvements: Dictionary with improvement percentages
            output_file: Path to save the chart
        """
        if not improvements:
            return
            
        # Prepare data
        metrics = list(improvements.keys())
        values = list(improvements.values())
        
        # Create colors based on values (positive=green, negative=red)
        colors = ['green' if v >= 0 else 'red' for v in values]
        
        # Format metric names for display
        display_metrics = [m.replace('_', ' ').title() for m in metrics]
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create horizontal bar chart
        bars = ax.barh(display_metrics, values, color=colors, alpha=0.7)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + (2 if width >= 0 else -2),
                bar.get_y() + bar.get_height() / 2,
                f'{width:.1f}%',
                ha='left' if width >= 0 else 'right',
                va='center',
                fontsize=10,
                fontweight='bold',
                color='black'
            )
        
        # Set chart properties
        ax.set_xlabel('Improvement (%)')
        ax.set_title('Batch vs. Single Action Strategy Improvements')
        ax.grid(True, linestyle='--', alpha=0.5)
        
        # Add reference line at 0
        ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
        
        # Set reasonable x-limits based on data
        max_abs_value = max(abs(min(values, default=0)), abs(max(values, default=0)))
        if max_abs_value > 0:
            # Add 20% padding
            limit = max_abs_value * 1.2
            ax.set_xlim(-limit if min(values, default=0) < 0 else 0, 
                      limit if max(values, default=0) > 0 else 0)
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_batch_size_chart(self, batch_metrics: Dict[str, BatchActionMetrics], output_file: str) -> None:
        """
        Create chart analyzing the relationship between batch size and success rate.
        
        Args:
            batch_metrics: Dictionary of BatchActionMetrics by config_id
            output_file: Path to save the chart
        """
        if not batch_metrics:
            return
            
        # Collect batch size and success rate data
        pattern_data = {}
        
        for metrics in batch_metrics.values():
            for pattern, data in metrics.pattern_success_rates.items():
                if pattern not in pattern_data:
                    pattern_data[pattern] = {
                        "batch_sizes": [],
                        "success_rates": []
                    }
                
                # Add batch size and success rate
                if "avg_batch_size" in data and "success_rate" in data:
                    pattern_data[pattern]["batch_sizes"].append(data["avg_batch_size"])
                    pattern_data[pattern]["success_rates"].append(data["success_rate"])
        
        # Filter patterns with enough data
        valid_patterns = {p: d for p, d in pattern_data.items() if len(d["batch_sizes"]) >= 2}
        
        if not valid_patterns:
            return
            
        # Create scatter plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Define colors for different patterns
        colors = plt.cm.tab10(range(len(valid_patterns)))
        
        # Create scatter plot for each pattern
        for i, (pattern, data) in enumerate(valid_patterns.items()):
            ax.scatter(
                data["batch_sizes"], 
                data["success_rates"],
                label=pattern.title(),
                color=colors[i],
                alpha=0.7,
                s=80
            )
        
        # Set chart properties
        ax.set_xlabel('Average Batch Size')
        ax.set_ylabel('Success Rate (%)')
        ax.set_title('Relationship Between Batch Size and Success Rate by Pattern')
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        
        # Add trend line
        all_sizes = []
        all_rates = []
        for data in valid_patterns.values():
            all_sizes.extend(data["batch_sizes"])
            all_rates.extend(data["success_rates"])
            
        if all_sizes and all_rates:
            # Simple linear regression
            try:
                from scipy import stats
                slope, intercept, r_value, p_value, std_err = stats.linregress(all_sizes, all_rates)
                
                # Add trend line
                x_vals = np.array([min(all_sizes), max(all_sizes)])
                y_vals = intercept + slope * x_vals
                ax.plot(x_vals, y_vals, 'k--', alpha=0.5, 
                      label=f'Trend (r={r_value:.2f})')
                
                # Update legend
                ax.legend()
            except:
                # If scipy is not available, skip trend line
                pass
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def generate_report(self) -> Tuple[str, Dict[str, Any]]:
        """
        Generate an HTML report of the batch analysis.
        
        Returns:
            Tuple of (report file path, analysis results dictionary)
        """
        # Run analysis
        comparison_results = self.compare_batch_vs_single()
        
        # Create report filename
        report_file = os.path.join(self.output_dir, "batch_analysis_report.html")
        
        # Generate HTML content
        html_content = self._generate_html_report(comparison_results)
        
        # Write to file
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        # Save analysis results as JSON
        analysis_file = os.path.join(self.output_dir, "batch_analysis_results.json")
        with open(analysis_file, 'w') as f:
            # Remove chart files from JSON (they're just paths)
            results_json = dict(comparison_results)
            if "chart_files" in results_json:
                del results_json["chart_files"]
            json.dump(results_json, f, indent=2)
        
        return report_file, comparison_results
    
    def _generate_html_report(self, comparison_results: Dict[str, Any]) -> str:
        """
        Generate HTML content for the batch analysis report.
        
        Args:
            comparison_results: Results from batch vs. single comparison
            
        Returns:
            HTML content for the report
        """
        # Get improvements
        improvements = comparison_results.get("improvements", {})
        
        # Get chart files
        chart_files = comparison_results.get("chart_files", {})
        
        # Get pattern effectiveness
        pattern_effectiveness = comparison_results.get("pattern_effectiveness", {})
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch Action Strategy Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .chart-container {{ margin: 20px 0; text-align: center; }}
        .chart {{ max-width: 100%; height: auto; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .summary-card {{ background-color: #f8f9fa; border-radius: 5px; padding: 15px; margin: 10px 0; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }}
        .metric-item {{ background-color: #f0f7ff; padding: 15px; border-radius: 5px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
        .section {{ margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Batch Action Strategy Analysis Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="section">
            <h2>Summary of Improvements</h2>
            <div class="summary-card">
                <div class="metric-grid">
        """
        
        # Add improvement metrics
        for metric, value in improvements.items():
            # Format metric name for display
            display_name = metric.replace('_', ' ').title()
            
            # Determine if positive or negative
            css_class = "positive" if value >= 0 else "negative"
            
            html_content += f"""
                    <div class="metric-item">
                        <div class="metric-value {css_class}">{value:.1f}%</div>
                        <div class="metric-label">{display_name}</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
        </div>
        """
        
        # Add visualizations section
        html_content += """
        <div class="section">
            <h2>Comparison Visualizations</h2>
        """
        
        # Add each chart
        for chart_name, chart_path in chart_files.items():
            # Convert to relative path for HTML
            rel_path = os.path.basename(chart_path)
            
            # Format chart title
            title = chart_name.replace('_', ' ').title()
            
            html_content += f"""
            <div class="chart-container">
                <h3>{title}</h3>
                <img class="chart" src="{rel_path}" alt="{title}">
            </div>
            """
        
        html_content += """
        </div>
        """
        
        # Add pattern effectiveness section
        if pattern_effectiveness:
            html_content += """
            <div class="section">
                <h2>UI Pattern Effectiveness</h2>
            """
            
            # Add best patterns by effectiveness
            if "best_by_effectiveness" in pattern_effectiveness:
                html_content += """
                <h3>Most Effective UI Patterns</h3>
                <p>These patterns have the highest success and completion rates:</p>
                <ol>
                """
                
                for pattern in pattern_effectiveness["best_by_effectiveness"]:
                    html_content += f"<li><strong>{pattern.title()}</strong></li>"
                
                html_content += """
                </ol>
                """
            
            # Add best patterns by efficiency
            if "best_by_efficiency" in pattern_effectiveness:
                html_content += """
                <h3>Most Efficient UI Patterns</h3>
                <p>These patterns execute the most actions per second:</p>
                <ol>
                """
                
                for pattern in pattern_effectiveness["best_by_efficiency"]:
                    html_content += f"<li><strong>{pattern.title()}</strong></li>"
                
                html_content += """
                </ol>
                """
            
            # Add pattern metrics table
            if "pattern_metrics" in pattern_effectiveness:
                html_content += """
                <h3>Pattern Performance Metrics</h3>
                <table>
                    <tr>
                        <th>Pattern</th>
                        <th>Success Rate</th>
                        <th>Completion Rate</th>
                        <th>Avg Batch Size</th>
                        <th>Actions/Second</th>
                        <th>MOPs Triggered</th>
                    </tr>
                """
                
                for pattern, metrics in pattern_effectiveness["pattern_metrics"].items():
                    html_content += f"""
                    <tr>
                        <td>{pattern.title()}</td>
                        <td>{metrics["avg_success_rate"]:.1f}%</td>
                        <td>{metrics["avg_completion_rate"]:.1f}%</td>
                        <td>{metrics["avg_batch_size"]:.1f}</td>
                        <td>{metrics["efficiency"]:.2f}</td>
                        <td>{metrics["mops_triggered"]}</td>
                    </tr>
                    """
                
                html_content += """
                </table>
                """
            
            html_content += """
            </div>
            """
        
        # Add key findings section
        html_content += """
        <div class="section">
            <h2>Key Findings</h2>
            <ul>
        """
        
        # Generate key findings based on improvement percentages
        if "time_efficiency" in improvements and improvements["time_efficiency"] > 0:
            html_content += f"""
                <li>Batch action strategies reduced time per effective action by <strong>{improvements["time_efficiency"]:.1f}%</strong></li>
            """
        
        if "llm_call_reduction" in improvements and improvements["llm_call_reduction"] > 0:
            html_content += f"""
                <li>Batch processing reduced LLM API calls by <strong>{improvements["llm_call_reduction"]:.1f}%</strong>, improving resource efficiency</li>
            """
        
        if "mop_coverage" in improvements and improvements["mop_coverage"] > 0:
            html_content += f"""
                <li>MOP coverage increased by <strong>{improvements["mop_coverage"]:.1f}%</strong> with batch strategies, improving security testing effectiveness</li>
            """
        
        if "action_throughput" in improvements and improvements["action_throughput"] > 0:
            html_content += f"""
                <li>Action throughput (actions per second) improved by <strong>{improvements["action_throughput"]:.1f}%</strong> with batch processing</li>
            """
        
        # Pattern-specific findings
        if pattern_effectiveness and "best_by_effectiveness" in pattern_effectiveness and pattern_effectiveness["best_by_effectiveness"]:
            top_pattern = pattern_effectiveness["best_by_effectiveness"][0]
            html_content += f"""
                <li>The <strong>{top_pattern}</strong> pattern showed the highest overall effectiveness, with good success and completion rates</li>
            """
        
        html_content += """
            </ul>
        </div>
        """
        
        # Close containers
        html_content += """
    </div>
</body>
</html>
        """
        
        return html_content