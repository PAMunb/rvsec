"""
Test framework analyzer module.

This module provides analysis tools for test framework results,
identifying optimal configurations and generating reports.
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from rvandroid.test_framework.config import ToolConfiguration, TestCase
from rvandroid.test_framework.executor import TestResult
from rvandroid.test_framework.plateau_analyzer import detect_plateau, find_optimal_timeout


@dataclass
class ConfigurationMetrics:
    """
    Metrics for evaluating a specific configuration.
    
    Captures comprehensive performance metrics for a configuration across 
    multiple test cases, enabling detailed comparison and ranking of different 
    configurations based on coverage, monitored operations, and efficiency.
    
    ### Key Metrics:
    - Execution metrics (success rate, execution time)
    - Coverage metrics (method, activity, MOP methods)
    - Monitored operations metrics
    - MOP error detection metrics
    - Component configuration details
    """
    config_id: str
    tool_name: str
    
    # Execution metrics
    total_tests: int = 0
    successful_tests: int = 0
    failed_tests: int = 0
    avg_execution_time: float = 0.0
    
    # Coverage metrics
    avg_method_coverage: float = 0.0
    avg_activity_coverage: float = 0.0
    avg_mop_method_coverage: float = 0.0
    
    # App-specific coverage
    app_coverage: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Error metrics
    total_errors: int = 0
    unique_errors: int = 0
    
    # MOP error metrics
    mop_error_count: int = 0
    mop_unique_errors: int = 0
    avg_mop_error_rate: float = 0.0
    
    # Monitored operations metrics
    monitored_operations_count: int = 0
    monitored_operations_triggered: int = 0
    avg_monitored_operations_ratio: float = 0.0
    
    # MOP error categories
    mop_error_categories: Dict[str, int] = field(default_factory=dict)
    
    # Component information
    llm_type: str = ""
    llm_model: str = ""
    strategy_type: str = ""
    parser_type: str = ""
    visitor_type: str = ""
    
    # Analysis settings
    use_static_analysis: bool = False
    static_analysis_level: str = ""
    use_screenshot_analysis: bool = False
    screenshot_analysis_level: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigurationMetrics':
        """Create metrics object from dictionary data."""
        return cls(**data)
    
    # This property stores the calculated score
    overall_score: float = 0.0
    
    def get_overall_score(self) -> float:
        """
        Calculate an overall score for this configuration.
        
        The score combines multiple factors:
        - Success rate: Percentage of tests completed successfully
        - Method coverage: Percentage of methods executed
        - Activity coverage: Percentage of activities visited
        - MOP coverage: Percentage of MOP methods executed
        - MOP detection: Ability to detect MOP violations
        - Execution time: Speed of execution (lower is better)
        
        Higher scores indicate better configurations.
        
        Returns:
            Score value between 0 and 100
        """
        # Weights for different factors
        weights = {
            "success_rate": 0.10,
            "method_coverage": 0.20,
            "activity_coverage": 0.20,
            "mop_coverage": 0.15,
            "mop_detection": 0.25,  # Higher weight for MOP error detection
            "execution_time": 0.10,
        }
        
        # Calculate success rate
        success_rate = self.successful_tests / self.total_tests if self.total_tests > 0 else 0
        
        # Calculate scores for each factor (0-100 scale)
        success_score = success_rate * 100
        method_score = self.avg_method_coverage
        activity_score = self.avg_activity_coverage
        mop_score = self.avg_mop_method_coverage
        
        # Calculate MOP detection score
        # Higher values of monitored_operations_ratio are better
        mop_detection_score = self.avg_monitored_operations_ratio
        
        # For execution time, lower is better
        # We'll use a formula that gives 100 for very fast tests (< 60s)
        # and decreases for longer times
        time_factor = min(1.0, 300 / max(60, self.avg_execution_time))
        time_score = time_factor * 100
        
        # Calculate weighted score
        overall_score = (
            weights["success_rate"] * success_score +
            weights["method_coverage"] * method_score +
            weights["activity_coverage"] * activity_score +
            weights["mop_coverage"] * mop_score +
            weights["mop_detection"] * mop_detection_score +
            weights["execution_time"] * time_score
        )
        
        return round(overall_score, 2)


class ResultAnalyzer:
    """
    Analyzer for test framework results.
    
    Processes test results to identify optimal configurations,
    calculate metrics, and generate reports and visualizations.
    
    ### Key Responsibilities:
    - Aggregates results across test cases
    - Calculates metrics for configurations
    - Identifies optimal configurations
    - Analyzes plateau in metrics over time
    - Generates reports and visualizations
    """
    
    def __init__(self, results: List[TestResult], output_dir: str = "analysis_results"):
        """
        Initialize the result analyzer.
        
        Args:
            results: List of test results
            output_dir: Directory for analysis output
        """
        self.results = results
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Metrics by configuration
        self.config_metrics: Dict[str, ConfigurationMetrics] = {}
        
        # App information
        self.apps: Set[str] = set()
        
        # Plateau analysis results
        self.plateau_analysis: Dict[str, Any] = {}
        
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze test results.
        
        Calculates metrics for each configuration and identifies
        optimal configurations for different criteria.
        Also performs plateau analysis when timeouts vary.
        
        Returns:
            Dictionary with analysis results
        """
        # Group results by configuration
        config_results = self._group_by_configuration()
        
        # Calculate metrics for each configuration
        for config_id, results in config_results.items():
            metrics = self._calculate_configuration_metrics(config_id, results)
            self.config_metrics[config_id] = metrics
        
        # Identify best configurations
        best_configs = self._identify_best_configurations()
        
        # Perform plateau analysis if timeout variations exist
        plateau_results = self._analyze_plateau()
        
        # Create analysis result
        analysis_result = {
            "timestamp": datetime.now().isoformat(),
            "total_configurations": len(self.config_metrics),
            "total_apps": len(self.apps),
            "best_configurations": best_configs,
            "configuration_metrics": {
                config_id: metrics.to_dict()
                for config_id, metrics in self.config_metrics.items()
            }
        }
        
        # Add plateau analysis results if available
        if plateau_results:
            analysis_result["plateau_analysis"] = plateau_results
            self.plateau_analysis = plateau_results
        
        return analysis_result
    
    def _group_by_configuration(self) -> Dict[str, List[TestResult]]:
        """
        Group test results by configuration.
        
        Returns:
            Dictionary mapping configuration IDs to lists of results
        """
        grouped_results = defaultdict(list)
        
        # Group results by configuration
        for result in self.results:
            config_id = result.test_case.tool_config.get_id()
            grouped_results[config_id].append(result)
            
            # Track apps
            app_path = result.test_case.app_path
            app_name = os.path.basename(app_path).split('.')[0]
            self.apps.add(app_name)
        
        return grouped_results
    
    def _calculate_configuration_metrics(self, config_id: str, results: List[TestResult]) -> ConfigurationMetrics:
        """
        Calculate comprehensive metrics for a configuration.
        
        This method aggregates metrics across all test results for a specific
        configuration, including execution metrics, coverage metrics, and
        monitored operations metrics.
        
        Args:
            config_id: Configuration identifier
            results: List of results for this configuration
            
        Returns:
            ConfigurationMetrics with calculated metrics
        """
        # Get configuration details from first result
        tool_config = results[0].test_case.tool_config
        
        # Create metrics object
        metrics = ConfigurationMetrics(
            config_id=config_id,
            tool_name=tool_config.tool_name,
            llm_type=tool_config.llm_type,
            llm_model=tool_config.llm_model,
            strategy_type=tool_config.strategy_type,
            parser_type=tool_config.parser_type,
            visitor_type=tool_config.visitor_type,
            use_static_analysis=tool_config.use_static_analysis,
            static_analysis_level=tool_config.static_analysis_level,
            use_screenshot_analysis=tool_config.use_screenshot_analysis,
            screenshot_analysis_level=tool_config.screenshot_analysis_level
        )
        
        # Count results
        metrics.total_tests = len(results)
        metrics.successful_tests = sum(1 for r in results if r.status == "completed")
        metrics.failed_tests = sum(1 for r in results if r.status == "error")
        
        # Calculate execution time
        execution_times = [r.execution_time for r in results if r.status == "completed"]
        metrics.avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Calculate coverage metrics
        method_coverage = []
        activity_coverage = []
        mop_coverage = []
        
        # App-specific coverage
        app_coverage = {}
        
        # Error tracking
        total_errors = 0
        unique_error_messages = set()
        
        # MOP error tracking
        mop_error_counts = []
        mop_unique_error_counts = []
        mop_error_rates = []
        monitored_operations_ratios = []
        mop_error_categories = {}
        monitored_operations_counts = []
        monitored_operations_triggered_counts = []
        
        # Process each result
        for result in results:
            # Get app name
            app_path = result.test_case.app_path
            app_name = os.path.basename(app_path).split('.')[0]
            
            # Process coverage data - even for failed tests we may have some coverage
            if hasattr(result, "coverage_data") and result.coverage_data:
                method_cov = result.coverage_data.get("method_coverage", 0.0)
                activity_cov = result.coverage_data.get("activity_coverage", 0.0)
                mop_cov = result.coverage_data.get("mop_method_coverage", 0.0)
                
                # Only add coverage for completed tests to avoid skewing averages
                if result.status == "completed":
                    method_coverage.append(method_cov)
                    activity_coverage.append(activity_cov)
                    mop_coverage.append(mop_cov)
                
                # Track app-specific coverage
                if app_name not in app_coverage:
                    app_coverage[app_name] = {
                        "method_coverage": 0.0,
                        "activity_coverage": 0.0,
                        "mop_coverage": 0.0,
                        "count": 0
                    }
                
                # Only count completed tests for app coverage
                if result.status == "completed":
                    app_data = app_coverage[app_name]
                    app_data["method_coverage"] += method_cov
                    app_data["activity_coverage"] += activity_cov
                    app_data["mop_coverage"] += mop_cov
                    app_data["count"] += 1
            
            # Process error data
            if hasattr(result, "error_data") and result.error_data:
                # General errors
                total_errors += result.error_data.get("total_errors", 0)
                
                # MOP specific errors
                mop_error_count = result.error_data.get("mop_error_count", 0)
                mop_error_counts.append(mop_error_count)
                
                mop_unique_errors = result.error_data.get("mop_unique_errors", 0)
                mop_unique_error_counts.append(mop_unique_errors)
                
                mop_error_rate = result.error_data.get("mop_error_rate", 0.0)
                if mop_error_rate > 0:
                    mop_error_rates.append(mop_error_rate)
                
                # Monitored operations metrics
                monitored_operations_count = result.error_data.get("monitored_operations_count", 0)
                monitored_operations_counts.append(monitored_operations_count)
                
                monitored_operations_triggered = result.error_data.get("monitored_operations_triggered", 0)
                monitored_operations_triggered_counts.append(monitored_operations_triggered)
                
                monitored_operations_ratio = result.error_data.get("monitored_operations_ratio", 0.0)
                if monitored_operations_ratio > 0:
                    monitored_operations_ratios.append(monitored_operations_ratio)
                
                # Aggregate MOP error categories
                if "mop_error_categories" in result.error_data:
                    categories = result.error_data.get("mop_error_categories", {})
                    for category, count in categories.items():
                        mop_error_categories[category] = mop_error_categories.get(category, 0) + count
                
                # Track unique general error messages
                if "errors" in result.error_data:
                    for error in result.error_data.get("errors", []):
                        message = error.get("message", "")
                        if message:
                            unique_error_messages.add(message)
        
        # Calculate average coverage
        metrics.avg_method_coverage = sum(method_coverage) / len(method_coverage) if method_coverage else 0.0
        metrics.avg_activity_coverage = sum(activity_coverage) / len(activity_coverage) if activity_coverage else 0.0
        metrics.avg_mop_method_coverage = sum(mop_coverage) / len(mop_coverage) if mop_coverage else 0.0
        
        # Calculate app-specific averages
        for app_name, app_data in app_coverage.items():
            count = app_data["count"]
            if count > 0:
                app_coverage[app_name] = {
                    "method_coverage": app_data["method_coverage"] / count,
                    "activity_coverage": app_data["activity_coverage"] / count,
                    "mop_coverage": app_data["mop_coverage"] / count
                }
        
        metrics.app_coverage = app_coverage
        
        # Set general error metrics
        metrics.total_errors = total_errors
        metrics.unique_errors = len(unique_error_messages)
        
        # Set MOP error metrics
        metrics.mop_error_count = sum(mop_error_counts)
        metrics.mop_unique_errors = sum(mop_unique_error_counts)  # Sum across apps as they may have different errors
        metrics.avg_mop_error_rate = sum(mop_error_rates) / len(mop_error_rates) if mop_error_rates else 0.0
        metrics.mop_error_categories = mop_error_categories
        
        # Set monitored operations metrics
        metrics.monitored_operations_count = sum(monitored_operations_counts)
        metrics.monitored_operations_triggered = sum(monitored_operations_triggered_counts)
        metrics.avg_monitored_operations_ratio = sum(monitored_operations_ratios) / len(monitored_operations_ratios) if monitored_operations_ratios else 0.0
        
        return metrics
    
    def _identify_best_configurations(self) -> Dict[str, List[str]]:
        """
        Identify the best configurations for different criteria.
        
        This method analyzes all configurations and ranks them based on various
        metrics, including overall score, coverage metrics, MOP error detection,
        and execution efficiency.
        
        Returns:
            Dictionary mapping criteria to lists of best configuration IDs
        """
        if not self.config_metrics:
            return {}
        
        # Calculate overall scores
        for config_id, metrics in self.config_metrics.items():
            metrics.overall_score = metrics.get_overall_score()
        
        # Sort configurations by overall score
        sorted_configs = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].get_overall_score(),
            reverse=True
        )
        
        # Group configurations by tool
        configs_by_tool = defaultdict(list)
        for config_id, metrics in self.config_metrics.items():
            configs_by_tool[metrics.tool_name].append((config_id, metrics))
        
        # Find best configurations for each tool
        best_by_tool = {}
        for tool_name, configs in configs_by_tool.items():
            sorted_tool_configs = sorted(
                configs,
                key=lambda x: x[1].get_overall_score(),
                reverse=True
            )
            best_by_tool[tool_name] = [config_id for config_id, _ in sorted_tool_configs[:3]]
        
        # Find best configurations by different coverage criteria
        best_by_method_coverage = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].avg_method_coverage,
            reverse=True
        )
        
        best_by_activity_coverage = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].avg_activity_coverage,
            reverse=True
        )
        
        best_by_mop_coverage = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].avg_mop_method_coverage,
            reverse=True
        )
        
        # Find best configurations by monitored operations metrics
        best_by_mop_error_count = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].mop_error_count,
            reverse=True
        )
        
        best_by_mop_unique_errors = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].mop_unique_errors,
            reverse=True
        )
        
        best_by_monitored_operations_ratio = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].avg_monitored_operations_ratio,
            reverse=True
        )
        
        # Find best configurations by efficiency
        best_by_speed = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].avg_execution_time  # Lower is better
        )
        
        # Find configurations with best balance of speed and detection
        # Higher score means better balance between speed and detection capability
        best_balanced = sorted(
            self.config_metrics.items(),
            key=lambda x: (x[1].avg_monitored_operations_ratio * 0.7 + 
                          (100 - min(100, x[1].avg_execution_time / 3)) * 0.3),
            reverse=True
        )
        
        # Return best configurations for all criteria
        return {
            # Overall best
            "overall": [config_id for config_id, _ in sorted_configs[:5]],
            
            # Best by tool
            "by_tool": best_by_tool,
            
            # Coverage metrics
            "method_coverage": [config_id for config_id, _ in best_by_method_coverage[:5]],
            "activity_coverage": [config_id for config_id, _ in best_by_activity_coverage[:5]],
            "mop_coverage": [config_id for config_id, _ in best_by_mop_coverage[:5]],
            
            # Monitored operations metrics
            "mop_error_detection": [config_id for config_id, _ in best_by_mop_error_count[:5]],
            "mop_unique_errors": [config_id for config_id, _ in best_by_mop_unique_errors[:5]],
            "monitored_operations_ratio": [config_id for config_id, _ in best_by_monitored_operations_ratio[:5]],
            
            # Efficiency metrics
            "speed": [config_id for config_id, _ in best_by_speed[:5]],
            "balanced_performance": [config_id for config_id, _ in best_balanced[:5]]
        }
    
    def generate_report(self) -> str:
        """
        Generate an HTML report of the analysis.
        
        Returns:
            Path to the generated report
        """
        # Run analysis
        analysis_result = self.analyze()
        
        # Create visualizations
        chart_files = self._create_visualizations()
        
        # Create report filename
        report_file = os.path.join(self.output_dir, "analysis_report.html")
        
        # Generate HTML content
        html_content = self._generate_html_report(analysis_result, chart_files)
        
        # Write to file
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        # Save analysis results as JSON
        analysis_file = os.path.join(self.output_dir, "analysis_results.json")
        with open(analysis_file, 'w') as f:
            json.dump(analysis_result, f, indent=2)
        
        return report_file
    
    def _analyze_plateau(self) -> Dict[str, Any]:
        """
        Analyze metrics for plateau detection when timeouts vary.
        
        Identifies if there are different timeout configurations and analyzes
        the progression of metrics over time to detect plateaus.
        
        Returns:
            Dictionary with plateau analysis results or empty dict if no timeout variations
        """
        # Group results by base configuration (excluding timeout from the ID)
        base_config_results = {}
        for result in self.results:
            # Extract configuration excluding timeout
            tool_config = result.test_case.tool_config
            base_id = (f"{tool_config.tool_name}_{tool_config.llm_type}_{tool_config.llm_model.replace(':', '-')}_"
                      f"{tool_config.strategy_type}_{tool_config.parser_type}_{tool_config.visitor_type}")
            
            if base_id not in base_config_results:
                base_config_results[base_id] = []
            
            base_config_results[base_id].append(result)
        
        plateau_results = {}
        
        # Analyze each base configuration
        for base_id, results in base_config_results.items():
            # Group by timeout
            timeout_results = {}
            for result in results:
                timeout = result.test_case.tool_config.timeout
                if timeout not in timeout_results:
                    timeout_results[timeout] = []
                
                timeout_results[timeout].append(result)
            
            # Only perform plateau analysis if multiple timeouts exist
            if len(timeout_results) <= 1:
                continue
            
            timeouts = sorted(timeout_results.keys())
            
            # Analyze key metrics
            metrics = ["method_coverage", "activity_coverage", "mop_method_coverage"]
            plateau_data = {
                "timeouts": timeouts,
                "metrics": {},
                "plateau_points": {},
                "optimal_timeouts": {}
            }
            
            for metric in metrics:
                metric_values = []
                
                # Calculate average metric value for each timeout
                for timeout in timeouts:
                    results_for_timeout = timeout_results[timeout]
                    values = []
                    
                    for result in results_for_timeout:
                        if result.status == "completed" and result.coverage_data and metric in result.coverage_data:
                            values.append(result.coverage_data[metric])
                    
                    avg_value = sum(values) / len(values) if values else 0.0
                    metric_values.append(avg_value)
                
                # Store metric values
                plateau_data["metrics"][metric] = metric_values
                
                # Detect plateau
                plateau_point = detect_plateau(timeouts, metric_values)
                plateau_data["plateau_points"][metric] = plateau_point
                
                # Find optimal timeout
                optimal_timeout = find_optimal_timeout(timeouts, metric_values)
                plateau_data["optimal_timeouts"][metric] = optimal_timeout
            
            # Create visualization
            self._create_plateau_visualization(base_id, timeouts, plateau_data)
            
            # Add to results
            plateau_results[base_id] = plateau_data
        
        return plateau_results
    
    def _create_plateau_visualization(self, base_id: str, timeouts: List[int], plateau_data: Dict[str, Any]) -> None:
        """
        Create visualization for plateau analysis.
        
        Args:
            base_id: Base configuration ID
            timeouts: List of timeouts
            plateau_data: Plateau analysis data
        """
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot each metric
        for metric, values in plateau_data["metrics"].items():
            # Format metric name for display
            display_name = metric.replace("_", " ").title()
            
            # Plot metric values
            ax.plot(timeouts, values, 'o-', label=f"{display_name}")
            
            # Mark plateau point if detected
            plateau_point = plateau_data["plateau_points"].get(metric)
            if plateau_point:
                plateau_index = timeouts.index(plateau_point)
                ax.axvline(x=plateau_point, color='gray', linestyle='--', alpha=0.5)
                ax.plot(plateau_point, values[plateau_index], 'rx', markersize=10)
            
            # Mark optimal timeout
            optimal_timeout = plateau_data["optimal_timeouts"].get(metric)
            if optimal_timeout:
                optimal_index = timeouts.index(optimal_timeout)
                ax.plot(optimal_timeout, values[optimal_index], 'go', markersize=10)
        
        # Set chart properties
        ax.set_xlabel('Timeout (seconds)')
        ax.set_ylabel('Metric Value (%)')
        ax.set_title(f'Metric Progression Over Time - {base_id}')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add annotation
        ax.text(
            0.02, 0.02,
            "Red X: Plateau point\nGreen Circle: Optimal timeout (90% of max)",
            transform=ax.transAxes,
            bbox=dict(facecolor='white', alpha=0.8)
        )
        
        # Save chart
        safe_id = base_id.replace("/", "_")
        output_file = os.path.join(self.output_dir, f"plateau_analysis_{safe_id}.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_visualizations(self) -> Dict[str, str]:
        """
        Create visualizations for the analysis.
        
        This method generates a comprehensive set of visualizations for analyzing
        test results, including overall scores, coverage metrics, MOP error metrics,
        and tool comparisons.
        
        Returns:
            Dictionary mapping chart names to file paths
        """
        chart_files = {}
        
        # Create overall scores chart
        scores_chart = os.path.join(self.output_dir, "overall_scores.png")
        self._create_overall_scores_chart(scores_chart)
        chart_files["overall_scores"] = scores_chart
        
        # Create coverage comparison chart
        coverage_chart = os.path.join(self.output_dir, "coverage_comparison.png")
        self._create_coverage_comparison_chart(coverage_chart)
        chart_files["coverage_comparison"] = coverage_chart
        
        # Create tools comparison chart
        tools_chart = os.path.join(self.output_dir, "tools_comparison.png")
        self._create_tools_comparison_chart(tools_chart)
        chart_files["tools_comparison"] = tools_chart
        
        # Create execution time chart
        time_chart = os.path.join(self.output_dir, "execution_times.png")
        self._create_execution_time_chart(time_chart)
        chart_files["execution_times"] = time_chart
        
        # Create MOP error metrics chart
        mop_error_chart = os.path.join(self.output_dir, "mop_error_metrics.png")
        self._create_mop_error_chart(mop_error_chart)
        chart_files["mop_error_metrics"] = mop_error_chart
        
        # Create monitored operations chart
        monitored_ops_chart = os.path.join(self.output_dir, "monitored_operations.png")
        self._create_monitored_operations_chart(monitored_ops_chart)
        chart_files["monitored_operations"] = monitored_ops_chart
        
        # Add plateau visualizations if available
        for base_id in self.plateau_analysis:
            safe_id = base_id.replace("/", "_")
            chart_path = os.path.join(self.output_dir, f"plateau_analysis_{safe_id}.png")
            if os.path.exists(chart_path):
                chart_files[f"plateau_{safe_id}"] = chart_path
        
        return chart_files
        
    def _create_mop_error_chart(self, output_file: str) -> None:
        """
        Create a chart visualizing MOP error metrics across configurations.
        
        Args:
            output_file: Path to save the chart
        """
        # Get configurations sorted by MOP error count
        sorted_configs = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].mop_error_count,
            reverse=True
        )
        
        # Limit to top 10 for readability
        top_configs = sorted_configs[:10]
        
        # Prepare data
        config_ids = [self._format_config_id(config_id) for config_id, _ in top_configs]
        mop_error_counts = [metrics.mop_error_count for _, metrics in top_configs]
        mop_unique_errors = [metrics.mop_unique_errors for _, metrics in top_configs]
        monitored_ratios = [metrics.avg_monitored_operations_ratio for _, metrics in top_configs]
        
        # Create the figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # First subplot: MOP error counts
        bars1 = ax1.bar(config_ids, mop_error_counts, color='navy', alpha=0.7, label='Total MOP Errors')
        bars2 = ax1.bar(config_ids, mop_unique_errors, color='cornflowerblue', alpha=0.7, label='Unique MOP Errors')
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax1.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom',
                    fontsize=9
                )
        
        # Set chart properties
        ax1.set_title('MOP Error Detection by Configuration')
        ax1.set_xlabel('Configuration')
        ax1.set_ylabel('Error Count')
        ax1.set_xticklabels(config_ids, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.5)
        
        # Second subplot: Monitored operations ratio
        bars3 = ax2.bar(config_ids, monitored_ratios, color='teal', alpha=0.7)
        
        # Add value labels
        for bar in bars3:
            height = bar.get_height()
            if height > 0:
                ax2.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{height:.1f}%',
                    ha='center', va='bottom',
                    fontsize=9
                )
        
        # Set chart properties
        ax2.set_title('Monitored Operations Ratio by Configuration')
        ax2.set_xlabel('Configuration')
        ax2.set_ylabel('Ratio (%)')
        ax2.set_xticklabels(config_ids, rotation=45, ha='right')
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
        
    def _create_monitored_operations_chart(self, output_file: str) -> None:
        """
        Create a chart visualizing monitored operations metrics.
        
        Args:
            output_file: Path to save the chart
        """
        # Get configurations with monitored operations data
        configs_with_data = [
            (config_id, metrics) for config_id, metrics in self.config_metrics.items()
            if metrics.monitored_operations_count > 0
        ]
        
        # If not enough data, create empty chart
        if len(configs_with_data) < 3:
            # Create empty figure
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "Insufficient data for monitored operations analysis", 
                   ha='center', va='center', fontsize=14)
            ax.axis('off')
            plt.savefig(output_file, dpi=100)
            plt.close(fig)
            return
        
        # Sort by monitored_operations_ratio
        sorted_configs = sorted(
            configs_with_data,
            key=lambda x: x[1].avg_monitored_operations_ratio,
            reverse=True
        )
        
        # Limit to top 8 for readability
        top_configs = sorted_configs[:8]
        
        # Prepare data
        config_ids = [self._format_config_id(config_id) for config_id, _ in top_configs]
        monitored_counts = [metrics.monitored_operations_count for _, metrics in top_configs]
        triggered_counts = [metrics.monitored_operations_triggered for _, metrics in top_configs]
        ratios = [metrics.avg_monitored_operations_ratio for _, metrics in top_configs]
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Set width of bars
        bar_width = 0.35
        x = np.arange(len(config_ids))
        
        # Create bars
        bars1 = ax.bar(x - bar_width/2, monitored_counts, bar_width, label='Monitored Operations', color='cadetblue')
        bars2 = ax.bar(x + bar_width/2, triggered_counts, bar_width, label='Triggered Operations', color='indianred')
        
        # Create ratio line (secondary y-axis)
        ax2 = ax.twinx()
        ratio_line = ax2.plot(x, ratios, 'o-', color='darkgreen', linewidth=2, label='Ratio (%)')
        
        # Add labels for bars
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom',
                    fontsize=9
                )
                
        for bar in bars2:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width()/2.,
                    height,
                    f'{int(height)}',
                    ha='center', va='bottom',
                    fontsize=9,
                    color='darkred'
                )
        
        # Add ratio labels
        for i, r in enumerate(ratios):
            ax2.text(
                x[i],
                r + 2,
                f'{r:.1f}%',
                ha='center', va='bottom',
                fontsize=9,
                color='darkgreen'
            )
        
        # Set chart properties
        ax.set_xlabel('Configuration')
        ax.set_ylabel('Operation Count')
        ax2.set_ylabel('Ratio (%)')
        ax.set_title('Monitored Operations Analysis by Configuration')
        ax.set_xticks(x)
        ax.set_xticklabels(config_ids, rotation=45, ha='right')
        
        # Add legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc='upper right')
        
        # Grid and layout
        ax.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_overall_scores_chart(self, output_file: str) -> None:
        """
        Create a chart of overall scores by configuration.
        
        Args:
            output_file: Path to save the chart
        """
        # Get configurations sorted by score
        sorted_configs = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].get_overall_score(),
            reverse=True
        )
        
        # Limit to top 20 for readability
        top_configs = sorted_configs[:20]
        
        # Prepare data
        config_ids = [self._format_config_id(config_id) for config_id, _ in top_configs]
        scores = [metrics.get_overall_score() for _, metrics in top_configs]
        tool_names = [metrics.tool_name for _, metrics in top_configs]
        
        # Create color mapping for tools
        tools = set(tool_names)
        colors = plt.cm.viridis(np.linspace(0, 1, len(tools)))
        tool_colors = {tool: colors[i] for i, tool in enumerate(tools)}
        
        # Create bar colors based on tool
        bar_colors = [tool_colors[tool] for tool in tool_names]
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create horizontal bar chart for better readability
        bars = ax.barh(config_ids, scores, color=bar_colors)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + 1,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.1f}',
                ha='left',
                va='center',
                fontsize=9
            )
        
        # Create a legend for tools
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=tool_colors[tool], label=tool)
            for tool in tools
        ]
        ax.legend(handles=legend_elements, loc='lower right')
        
        # Set chart properties
        ax.set_xlabel('Overall Score')
        ax.set_title('Overall Configuration Scores (Top 20)')
        ax.set_xlim(0, 105)  # Scores range from 0-100
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_coverage_comparison_chart(self, output_file: str) -> None:
        """
        Create a chart comparing coverage metrics across configurations.
        
        Args:
            output_file: Path to save the chart
        """
        # Get top 10 configurations by coverage
        sorted_configs = sorted(
            self.config_metrics.items(),
            key=lambda x: (x[1].avg_method_coverage + x[1].avg_activity_coverage + x[1].avg_mop_method_coverage) / 3,
            reverse=True
        )
        top_configs = sorted_configs[:10]
        
        # Prepare data
        config_ids = [self._format_config_id(config_id) for config_id, _ in top_configs]
        method_coverage = [metrics.avg_method_coverage for _, metrics in top_configs]
        activity_coverage = [metrics.avg_activity_coverage for _, metrics in top_configs]
        mop_coverage = [metrics.avg_mop_method_coverage for _, metrics in top_configs]
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Set width of bars
        barWidth = 0.25
        
        # Set positions of bars on X axis
        r1 = np.arange(len(config_ids))
        r2 = [x + barWidth for x in r1]
        r3 = [x + barWidth for x in r2]
        
        # Create bars
        ax.bar(r1, method_coverage, width=barWidth, label='Method Coverage')
        ax.bar(r2, activity_coverage, width=barWidth, label='Activity Coverage')
        ax.bar(r3, mop_coverage, width=barWidth, label='MOP Method Coverage')
        
        # Add labels and legend
        ax.set_xlabel('Configuration')
        ax.set_ylabel('Coverage (%)')
        ax.set_title('Coverage Metrics Comparison (Top 10)')
        ax.set_xticks([r + barWidth for r in range(len(config_ids))])
        ax.set_xticklabels(config_ids, rotation=45, ha='right')
        ax.set_ylim(0, 100)
        ax.legend()
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_tools_comparison_chart(self, output_file: str) -> None:
        """
        Create a chart comparing tool performance.
        
        Args:
            output_file: Path to save the chart
        """
        # Group metrics by tool
        tool_metrics = defaultdict(list)
        for metrics in self.config_metrics.values():
            tool_metrics[metrics.tool_name].append(metrics)
        
        # Calculate average metrics by tool
        tool_averages = {}
        for tool, metrics_list in tool_metrics.items():
            avg_method_coverage = sum(m.avg_method_coverage for m in metrics_list) / len(metrics_list)
            avg_activity_coverage = sum(m.avg_activity_coverage for m in metrics_list) / len(metrics_list)
            avg_mop_coverage = sum(m.avg_mop_method_coverage for m in metrics_list) / len(metrics_list)
            avg_time = sum(m.avg_execution_time for m in metrics_list) / len(metrics_list)
            success_rate = sum(m.successful_tests for m in metrics_list) / sum(m.total_tests for m in metrics_list) * 100
            
            tool_averages[tool] = {
                "method_coverage": avg_method_coverage,
                "activity_coverage": avg_activity_coverage,
                "mop_coverage": avg_mop_coverage,
                "execution_time": avg_time,
                "success_rate": success_rate
            }
        
        # Create the figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 7))
        
        # Prepare data for coverage plot
        tools = list(tool_averages.keys())
        method_coverage = [tool_averages[tool]["method_coverage"] for tool in tools]
        activity_coverage = [tool_averages[tool]["activity_coverage"] for tool in tools]
        mop_coverage = [tool_averages[tool]["mop_coverage"] for tool in tools]
        
        # Set width of bars
        barWidth = 0.25
        
        # Set positions of bars on X axis
        r1 = np.arange(len(tools))
        r2 = [x + barWidth for x in r1]
        r3 = [x + barWidth for x in r2]
        
        # Create coverage bars
        ax1.bar(r1, method_coverage, width=barWidth, label='Method Coverage')
        ax1.bar(r2, activity_coverage, width=barWidth, label='Activity Coverage')
        ax1.bar(r3, mop_coverage, width=barWidth, label='MOP Method Coverage')
        
        # Add coverage labels
        ax1.set_xlabel('Tool')
        ax1.set_ylabel('Coverage (%)')
        ax1.set_title('Average Coverage by Tool')
        ax1.set_xticks([r + barWidth for r in range(len(tools))])
        ax1.set_xticklabels(tools)
        ax1.set_ylim(0, 100)
        ax1.legend()
        
        # Prepare data for time/success plot
        execution_times = [tool_averages[tool]["execution_time"] for tool in tools]
        success_rates = [tool_averages[tool]["success_rate"] for tool in tools]
        
        # Create time series
        ax2_t = ax2.twinx()
        ax2.bar(tools, execution_times, color='salmon', alpha=0.7, label='Execution Time')
        ax2_t.plot(tools, success_rates, 'bo-', label='Success Rate')
        
        # Add time/success labels
        ax2.set_xlabel('Tool')
        ax2.set_ylabel('Execution Time (s)')
        ax2_t.set_ylabel('Success Rate (%)')
        ax2.set_title('Execution Time & Success Rate by Tool')
        ax2.legend(loc='upper left')
        ax2_t.legend(loc='upper right')
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _create_execution_time_chart(self, output_file: str) -> None:
        """
        Create a chart of execution times by configuration.
        
        Args:
            output_file: Path to save the chart
        """
        # Get configurations sorted by execution time
        sorted_configs = sorted(
            self.config_metrics.items(),
            key=lambda x: x[1].avg_execution_time
        )
        
        # Limit to top 20 for readability
        top_configs = sorted_configs[:20]
        
        # Prepare data
        config_ids = [self._format_config_id(config_id) for config_id, _ in top_configs]
        times = [metrics.avg_execution_time for _, metrics in top_configs]
        tool_names = [metrics.tool_name for _, metrics in top_configs]
        
        # Create color mapping for tools
        tools = set(tool_names)
        colors = plt.cm.viridis(np.linspace(0, 1, len(tools)))
        tool_colors = {tool: colors[i] for i, tool in enumerate(tools)}
        
        # Create bar colors based on tool
        bar_colors = [tool_colors[tool] for tool in tool_names]
        
        # Create the figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create horizontal bar chart for better readability
        bars = ax.barh(config_ids, times, color=bar_colors)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + 5,
                bar.get_y() + bar.get_height() / 2,
                f'{width:.1f}s',
                ha='left',
                va='center',
                fontsize=9
            )
        
        # Create a legend for tools
        legend_elements = [
            plt.Rectangle((0, 0), 1, 1, color=tool_colors[tool], label=tool)
            for tool in tools
        ]
        ax.legend(handles=legend_elements, loc='lower right')
        
        # Set chart properties
        ax.set_xlabel('Execution Time (s)')
        ax.set_title('Average Execution Time by Configuration (Fastest 20)')
        
        # Save chart
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
    
    def _format_config_id(self, config_id: str) -> str:
        """
        Format a configuration ID for display.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Formatted ID for display
        """
        # Get metrics for this configuration
        metrics = self.config_metrics[config_id]
        
        # Create shortened ID
        return f"{metrics.tool_name}/{metrics.llm_type}_{metrics.strategy_type}"
    
    def _generate_html_report(self, 
                             analysis_result: Dict[str, Any], 
                             chart_files: Dict[str, str]) -> str:
        """
        Generate HTML content for the analysis report.
        
        Args:
            analysis_result: Analysis result dictionary
            chart_files: Dictionary of chart paths
            
        Returns:
            HTML content for the report
        """
        # Get best configurations
        best_configs = analysis_result["best_configurations"]
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Framework Analysis Report</title>
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
        .section {{ margin: 30px 0; }}
        .tool-section {{ margin: 30px 0; border-left: 5px solid #0066cc; padding-left: 15px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Test Framework Analysis Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="section">
            <h2>Summary</h2>
            <div class="summary-card">
                <div class="metric-grid">
                    <div class="metric-item">
                        <div class="metric-value">{analysis_result["total_configurations"]}</div>
                        <div class="metric-label">Configurations</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-value">{analysis_result["total_apps"]}</div>
                        <div class="metric-label">Applications</div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        # Add visualizations section
        html_content += """
        <div class="section">
            <h2>Visualizations</h2>
        """
        
        # Add each standard chart first
        standard_charts = ["overall_scores", "coverage_comparison", "tools_comparison", "execution_times"]
        for chart_name in standard_charts:
            if chart_name in chart_files:
                # Convert to relative path for HTML
                rel_path = os.path.basename(chart_files[chart_name])
                
                # Format chart title
                title = chart_name.replace('_', ' ').title()
                
                html_content += f"""
                <div class="chart-container">
                    <h3>{title}</h3>
                    <img class="chart" src="{rel_path}" alt="{title}">
                </div>
                """
        
        # Add plateau analysis section if available
        plateau_charts = [name for name in chart_files if name.startswith("plateau_")]
        if plateau_charts:
            html_content += """
            <h2>Plateau Analysis</h2>
            <p>Analysis of metric progression over different timeouts showing when metrics reach a plateau.</p>
            """
            
            for chart_name in plateau_charts:
                # Convert to relative path for HTML
                rel_path = os.path.basename(chart_files[chart_name])
                
                # Extract configuration ID from chart name
                config_id = chart_name.replace("plateau_", "")
                title = f"Plateau Analysis - {config_id}"
                
                html_content += f"""
                <div class="chart-container">
                    <h3>{title}</h3>
                    <img class="chart" src="{rel_path}" alt="{title}">
                </div>
                """
        
        html_content += """
        </div>
        """
        
        # Add best configurations section
        html_content += """
        <div class="section">
            <h2>Best Configurations</h2>
        """
        
        # Add overall best configurations
        html_content += """
            <h3>Overall Best Configurations</h3>
            <table>
                <tr>
                    <th>Rank</th>
                    <th>Configuration</th>
                    <th>Tool</th>
                    <th>LLM</th>
                    <th>Strategy</th>
                    <th>Score</th>
                </tr>
        """
        
        for i, config_id in enumerate(best_configs["overall"]):
            metrics = self.config_metrics[config_id]
            html_content += f"""
                <tr>
                    <td>{i+1}</td>
                    <td>{config_id}</td>
                    <td>{metrics.tool_name}</td>
                    <td>{metrics.llm_type}/{metrics.llm_model}</td>
                    <td>{metrics.strategy_type}</td>
                    <td>{metrics.get_overall_score():.2f}</td>
                </tr>
            """
        
        html_content += """
            </table>
        """
        
        # Add tool-specific best configurations
        html_content += """
            <h3>Best Configurations by Tool</h3>
        """
        
        for tool, config_ids in best_configs["by_tool"].items():
            html_content += f"""
            <div class="tool-section">
                <h4>{tool}</h4>
                <table>
                    <tr>
                        <th>Rank</th>
                        <th>Configuration</th>
                        <th>LLM</th>
                        <th>Strategy</th>
                        <th>Score</th>
                    </tr>
            """
            
            for i, config_id in enumerate(config_ids):
                metrics = self.config_metrics[config_id]
                html_content += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td>{config_id}</td>
                        <td>{metrics.llm_type}/{metrics.llm_model}</td>
                        <td>{metrics.strategy_type}</td>
                        <td>{metrics.get_overall_score():.2f}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </div>
            """
        
        # Add category-specific best configurations
        categories = [
            ("Method Coverage", "method_coverage"),
            ("Activity Coverage", "activity_coverage"),
            ("MOP Coverage", "mop_coverage"),
            ("Execution Speed", "speed")
        ]
        
        html_content += """
            <h3>Best Configurations by Category</h3>
        """
        
        for title, key in categories:
            html_content += f"""
            <div class="tool-section">
                <h4>Best for {title}</h4>
                <table>
                    <tr>
                        <th>Rank</th>
                        <th>Configuration</th>
                        <th>Tool</th>
                        <th>Value</th>
                    </tr>
            """
            
            for i, config_id in enumerate(best_configs[key]):
                metrics = self.config_metrics[config_id]
                
                if key == "method_coverage":
                    value = f"{metrics.avg_method_coverage:.2f}%"
                elif key == "activity_coverage":
                    value = f"{metrics.avg_activity_coverage:.2f}%"
                elif key == "mop_coverage":
                    value = f"{metrics.avg_mop_method_coverage:.2f}%"
                elif key == "speed":
                    value = f"{metrics.avg_execution_time:.2f}s"
                else:
                    value = "N/A"
                
                html_content += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td>{config_id}</td>
                        <td>{metrics.tool_name}</td>
                        <td>{value}</td>
                    </tr>
                """
            
            html_content += """
                </table>
            </div>
            """
        
        # Close containers
        html_content += """
        </div>
    </div>
</body>
</html>
        """
        
        return html_content