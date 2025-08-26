"""
Plateau analysis for identifying optimal test execution duration.

This component analyzes the rate of diminishing returns in test metrics to determine
the point where continued execution provides minimal additional value, enabling
automatic timeout optimization.

### Architectural Decisions:
- **Post-Execution Analysis**: Analyzes completed test results without runtime interference
- **Metric-Based Detection**: Uses coverage progression and MOP discovery rates
- **Statistical Analysis**: Implements sliding window and trend analysis for plateau detection
- **Recommendation Engine**: Provides timeout optimization suggestions for future runs

### Analysis Metrics:
- **Coverage Progression**: Rate of new method/activity coverage discovery over time
- **MOP Discovery**: Rate of new monitored operation violations found
- **UI Exploration**: Rate of new UI element interactions
- **Cost-Benefit Analysis**: Execution time vs value gained analysis

### Reuse from Old Test Framework:
- Plateau detection patterns from plateau_analyzer.py
- Statistical analysis and trend detection methods
- Sliding window analysis for metric progression
- Timeout optimization recommendations
"""

import json
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE
from rv_android_core.util.logging.manager import LoggingManager

from rv_test_framework.core.models import TaskResult


class PlateauPoint:
    """Represents a detected plateau point in metric progression."""
    
    def __init__(
        self, 
        time_point: float, 
        metric_value: float, 
        confidence: float,
        metric_type: str
    ):
        self.time_point = time_point
        self.metric_value = metric_value
        self.confidence = confidence
        self.metric_type = metric_type


class PlateauAnalyzer:
    """
    Identifies plateau points in test execution metrics for timeout optimization.
    
    This class follows the plateau detection patterns from the old test framework,
    adapted for comprehensive timeout optimization across different metrics.
    
    ### Plateau Detection Strategy:
    - Sliding window analysis of metric improvements over time
    - Statistical significance testing for trend changes  
    - Cost-benefit analysis incorporating execution time and resource usage
    - Recommendation generation for optimal timeout values in future runs
    
    ### Integration Points:
    - **PerformanceMonitor**: Uses collected metrics for plateau analysis
    - **Coverage Data**: Analyzes coverage progression from logcat parsing
    - **MOP Violations**: Tracks monitored operation discovery rates
    - **Report Generation**: Provides optimization recommendations in analysis reports
    """
    
    @ErrorHandler.handle_errors(
        component="PlateauAnalyzer",
        phase="initialization"
    )
    def __init__(self, analysis_dir: str):
        """
        Initialize plateau analyzer.
        
        Args:
            analysis_dir: Directory for analysis results
        """
        self.analysis_dir = Path(analysis_dir)
        self.analysis_dir.mkdir(exist_ok=True)
        
        # Analysis parameters
        self.window_size = 5  # Points for sliding window analysis
        self.plateau_threshold = 0.02  # 2% improvement threshold
        self.min_confidence = 0.7  # Minimum confidence for plateau detection
        
        # Setup logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.analysis.plateau_analyzer',
            {CONTEXT_COMPONENT: 'PlateauAnalyzer'}
        )
        
        self.logger.info(f"PlateauAnalyzer initialized: {analysis_dir}")
    
    @ErrorHandler.handle_errors(
        component="PlateauAnalyzer",
        phase="plateau_analysis"
    )
    def analyze_plateaus(
        self, 
        task_results: List[TaskResult],
        include_detailed_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze plateau points across different metrics.
        
        Args:
            task_results: List of task execution results
            include_detailed_analysis: Whether to include detailed per-configuration analysis
            
        Returns:
            Dictionary containing plateau analysis results
        """
        with self.logger.with_context(
            total_tasks=len(task_results),
            phase="plateau_analysis"
        ):
            self.logger.info(LOG_START.format(phase="plateau analysis"))
            
            analysis_results = {
                "analysis_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tasks_analyzed": len(task_results),
                    "analysis_parameters": {
                        "window_size": self.window_size,
                        "plateau_threshold": self.plateau_threshold,
                        "min_confidence": self.min_confidence
                    }
                },
                "timeout_recommendations": self._analyze_timeout_optimization(task_results),
                "plateau_detection": {},
                "cost_benefit_analysis": self._perform_cost_benefit_analysis(task_results)
            }
            
            if include_detailed_analysis:
                # Analyze plateaus by configuration
                analysis_results["plateau_detection"] = self._detect_plateaus_by_configuration(task_results)
                
                # Analyze metric-specific plateaus
                analysis_results["metric_plateaus"] = self._analyze_metric_plateaus(task_results)
            
            # Generate optimization recommendations
            analysis_results["optimization_recommendations"] = self._generate_optimization_recommendations(
                analysis_results
            )
            
            # Save plateau analysis results
            plateau_file = self.analysis_dir / "plateau_analysis.json"
            with open(plateau_file, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            self.logger.info(LOG_COMPLETE.format(phase="plateau analysis"))
            return analysis_results
    
    def _analyze_timeout_optimization(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze optimal timeout values based on execution patterns.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Timeout optimization analysis
        """
        # Group results by configuration for timeout analysis
        config_groups = {}
        for result in task_results:
            config = result.config_name
            if config not in config_groups:
                config_groups[config] = []
            config_groups[config].append(result)
        
        timeout_analysis = {}
        
        for config_name, results in config_groups.items():
            successful_results = [r for r in results if r.success]
            
            if not successful_results:
                continue
            
            execution_times = [r.execution_time for r in successful_results if r.execution_time > 0]
            
            if not execution_times:
                continue
            
            # Calculate percentiles for timeout optimization
            sorted_times = sorted(execution_times)
            n = len(sorted_times)
            
            percentiles = {
                "p50": sorted_times[int(0.50 * n)] if n > 0 else 0,
                "p75": sorted_times[int(0.75 * n)] if n > 0 else 0,
                "p90": sorted_times[int(0.90 * n)] if n > 0 else 0,
                "p95": sorted_times[int(0.95 * n)] if n > 0 else 0
            }
            
            # Recommend timeouts based on percentiles with buffers
            recommended_timeouts = {
                "conservative": int(percentiles["p95"] * 1.2),  # 95th percentile + 20%
                "balanced": int(percentiles["p90"] * 1.15),     # 90th percentile + 15%
                "aggressive": int(percentiles["p75"] * 1.1)     # 75th percentile + 10%
            }
            
            timeout_analysis[config_name] = {
                "execution_time_percentiles": percentiles,
                "recommended_timeouts": recommended_timeouts,
                "current_success_rate": len(successful_results) / len(results) * 100,
                "sample_size": len(execution_times)
            }
        
        return timeout_analysis
    
    def _detect_plateaus_by_configuration(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Detect plateau points for each configuration.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Plateau detection results by configuration
        """
        # Group by configuration
        config_groups = {}
        for result in task_results:
            config = result.config_name
            if config not in config_groups:
                config_groups[config] = []
            config_groups[config].append(result)
        
        plateau_detection = {}
        
        for config_name, results in config_groups.items():
            # Sort results by execution time to create time series
            time_series_results = sorted(
                [r for r in results if r.success and r.execution_time > 0],
                key=lambda x: x.execution_time
            )
            
            if len(time_series_results) < self.window_size:
                plateau_detection[config_name] = {
                    "status": "insufficient_data",
                    "sample_size": len(time_series_results),
                    "required_size": self.window_size
                }
                continue
            
            # Analyze different metrics for plateau detection
            coverage_plateaus = self._detect_metric_plateau(
                time_series_results, "coverage", "method_coverage"
            )
            
            action_plateaus = self._detect_metric_plateau(
                time_series_results, "actions", "total_actions"
            )
            
            plateau_detection[config_name] = {
                "coverage_plateaus": coverage_plateaus,
                "action_plateaus": action_plateaus,
                "sample_size": len(time_series_results),
                "time_range": {
                    "min": min(r.execution_time for r in time_series_results),
                    "max": max(r.execution_time for r in time_series_results)
                }
            }
        
        return plateau_detection
    
    def _detect_metric_plateau(
        self, 
        time_series_results: List[TaskResult], 
        metric_category: str,
        specific_metric: str
    ) -> List[Dict[str, Any]]:
        """
        Detect plateau points for a specific metric using sliding window analysis.
        
        Args:
            time_series_results: Results sorted by execution time
            metric_category: Category of metric (e.g., "coverage", "actions")
            specific_metric: Specific metric name
            
        Returns:
            List of detected plateau points
        """
        if len(time_series_results) < self.window_size * 2:
            return []
        
        plateaus = []
        metric_values = []
        time_points = []
        
        # Extract metric values and time points
        for result in time_series_results:
            if result.metrics and metric_category in result.metrics:
                metric_data = result.metrics[metric_category]
                if specific_metric in metric_data:
                    metric_values.append(metric_data[specific_metric])
                    time_points.append(result.execution_time)
        
        if len(metric_values) < self.window_size * 2:
            return []
        
        # Sliding window analysis
        for i in range(self.window_size, len(metric_values) - self.window_size):
            window_before = metric_values[i-self.window_size:i]
            window_after = metric_values[i:i+self.window_size]
            
            # Calculate improvement rates
            before_avg = statistics.mean(window_before)
            after_avg = statistics.mean(window_after)
            
            improvement_rate = (after_avg - before_avg) / before_avg if before_avg > 0 else 0
            
            # Check if improvement rate is below threshold (plateau detected)
            if abs(improvement_rate) < self.plateau_threshold:
                confidence = 1 - abs(improvement_rate) / self.plateau_threshold
                
                if confidence >= self.min_confidence:
                    plateau_point = {
                        "time_point": time_points[i],
                        "metric_value": metric_values[i],
                        "confidence": confidence,
                        "improvement_rate": improvement_rate,
                        "window_before_avg": before_avg,
                        "window_after_avg": after_avg
                    }
                    plateaus.append(plateau_point)
        
        return plateaus
    
    def _analyze_metric_plateaus(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze plateau patterns across different metric types.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Metric-specific plateau analysis
        """
        metric_analysis = {
            "coverage_plateaus": self._analyze_coverage_plateaus(task_results),
            "action_plateaus": self._analyze_action_plateaus(task_results),
            "error_plateaus": self._analyze_error_plateaus(task_results)
        }
        
        return metric_analysis
    
    def _analyze_coverage_plateaus(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """Analyze coverage-based plateau patterns."""
        coverage_data = []
        
        for result in task_results:
            if (result.success and result.metrics and 
                'coverage' in result.metrics and result.execution_time > 0):
                coverage_info = result.metrics['coverage']
                coverage_data.append({
                    'time': result.execution_time,
                    'method_coverage': coverage_info.get('method_coverage', 0),
                    'activity_coverage': coverage_info.get('activity_coverage', 0),
                    'config': result.config_name
                })
        
        if not coverage_data:
            return {"status": "no_coverage_data"}
        
        # Sort by time
        coverage_data.sort(key=lambda x: x['time'])
        
        # Detect plateau in method coverage
        method_plateaus = self._find_plateau_points(
            [d['time'] for d in coverage_data],
            [d['method_coverage'] for d in coverage_data]
        )
        
        return {
            "method_coverage_plateaus": method_plateaus,
            "data_points": len(coverage_data),
            "time_range": {
                "min": min(d['time'] for d in coverage_data),
                "max": max(d['time'] for d in coverage_data)
            }
        }
    
    def _analyze_action_plateaus(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """Analyze action-based plateau patterns."""
        # Placeholder for action plateau analysis
        return {"status": "action_analysis_placeholder"}
    
    def _analyze_error_plateaus(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """Analyze error discovery plateau patterns."""
        # Placeholder for error plateau analysis
        return {"status": "error_analysis_placeholder"}
    
    def _find_plateau_points(
        self, 
        time_points: List[float], 
        metric_values: List[float]
    ) -> List[Dict[str, Any]]:
        """
        Find plateau points in a time series using statistical analysis.
        
        Args:
            time_points: List of time points
            metric_values: List of corresponding metric values
            
        Returns:
            List of detected plateau points
        """
        if len(time_points) < self.window_size * 2:
            return []
        
        plateaus = []
        
        # Use sliding window to detect plateaus
        for i in range(self.window_size, len(metric_values) - self.window_size):
            window_values = metric_values[i-self.window_size//2:i+self.window_size//2]
            
            # Check if values in window are relatively stable
            if len(window_values) > 1:
                std_dev = statistics.stdev(window_values)
                mean_val = statistics.mean(window_values)
                coefficient_variation = std_dev / mean_val if mean_val > 0 else float('inf')
                
                # Low coefficient of variation indicates plateau
                if coefficient_variation < 0.1:  # 10% variation threshold
                    confidence = max(0, 1 - coefficient_variation / 0.1)
                    
                    if confidence >= self.min_confidence:
                        plateaus.append({
                            "time_point": time_points[i],
                            "metric_value": metric_values[i],
                            "confidence": confidence,
                            "coefficient_variation": coefficient_variation,
                            "window_std_dev": std_dev,
                            "window_mean": mean_val
                        })
        
        return plateaus
    
    def _perform_cost_benefit_analysis(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Perform cost-benefit analysis for execution time vs. value gained.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Cost-benefit analysis results
        """
        # Group by configuration for cost-benefit analysis
        config_analysis = {}
        
        for result in task_results:
            config = result.config_name
            if config not in config_analysis:
                config_analysis[config] = {
                    "execution_times": [],
                    "coverage_values": [],
                    "success_count": 0,
                    "total_count": 0
                }
            
            config_analysis[config]["total_count"] += 1
            
            if result.success:
                config_analysis[config]["success_count"] += 1
                
                if result.execution_time > 0:
                    config_analysis[config]["execution_times"].append(result.execution_time)
                
                if result.metrics and 'coverage' in result.metrics:
                    coverage = result.metrics['coverage'].get('method_coverage', 0)
                    config_analysis[config]["coverage_values"].append(coverage)
        
        # Calculate cost-benefit metrics
        cost_benefit_results = {}
        
        for config, data in config_analysis.items():
            if data["execution_times"] and data["coverage_values"]:
                avg_time = statistics.mean(data["execution_times"])
                avg_coverage = statistics.mean(data["coverage_values"])
                
                # Cost-benefit ratio: coverage gained per unit time
                efficiency = avg_coverage / avg_time if avg_time > 0 else 0
                
                cost_benefit_results[config] = {
                    "average_execution_time": avg_time,
                    "average_coverage": avg_coverage,
                    "efficiency_score": efficiency,
                    "success_rate": data["success_count"] / data["total_count"] * 100,
                    "sample_size": len(data["execution_times"])
                }
        
        # Rank configurations by efficiency
        ranked_configs = sorted(
            cost_benefit_results.items(),
            key=lambda x: x[1]["efficiency_score"],
            reverse=True
        )
        
        return {
            "configuration_efficiency": cost_benefit_results,
            "efficiency_ranking": [
                {
                    "configuration": config,
                    "efficiency_score": data["efficiency_score"],
                    "average_time": data["average_execution_time"],
                    "average_coverage": data["average_coverage"]
                }
                for config, data in ranked_configs
            ]
        }
    
    def _generate_optimization_recommendations(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate optimization recommendations based on plateau analysis.
        
        Args:
            analysis_results: Complete plateau analysis results
            
        Returns:
            List of optimization recommendations
        """
        recommendations = []
        
        # Timeout optimization recommendations
        timeout_data = analysis_results.get("timeout_recommendations", {})
        for config, data in timeout_data.items():
            if data.get("sample_size", 0) >= 5:  # Require minimum sample size
                balanced_timeout = data["recommended_timeouts"]["balanced"]
                current_success_rate = data["current_success_rate"]
                
                recommendations.append({
                    "type": "timeout_optimization",
                    "configuration": config,
                    "recommended_timeout": balanced_timeout,
                    "current_success_rate": current_success_rate,
                    "reasoning": f"Based on 90th percentile execution time with 15% buffer",
                    "expected_coverage": "90% of successful executions"
                })
        
        # Cost-benefit recommendations
        cost_benefit_data = analysis_results.get("cost_benefit_analysis", {})
        efficiency_ranking = cost_benefit_data.get("efficiency_ranking", [])
        
        if efficiency_ranking:
            most_efficient = efficiency_ranking[0]
            recommendations.append({
                "type": "configuration_efficiency",
                "configuration": most_efficient["configuration"],
                "efficiency_score": most_efficient["efficiency_score"],
                "reasoning": "Most efficient configuration based on coverage gained per unit time",
                "average_execution_time": most_efficient["average_time"]
            })
        
        return recommendations