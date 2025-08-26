"""
Metrics analysis and aggregation for test framework results.

This component processes collected metrics to generate insights and recommendations,
following the patterns established in the old test framework's analysis components.

### Analysis Capabilities:
- **Configuration Comparison**: Compare performance across different configurations
- **Trend Analysis**: Identify performance patterns and regressions
- **Resource Utilization**: Analyze execution efficiency and resource usage
- **Success Rate Analysis**: Identify configurations with highest success rates

### Reuse from Old Test Framework:
- Configuration analysis patterns from batch_analyzer.py
- Metrics aggregation from batch_metrics.py  
- Statistical analysis patterns and threshold detection
- Report generation patterns and data visualization preparation
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


class MetricsAnalyzer:
    """
    Analyzes collected metrics to generate insights and recommendations.
    
    This class follows the analysis patterns from the old test framework's
    batch analysis components, adapted for the new modular architecture.
    
    ### Analysis Areas:
    - **Performance Analysis**: Execution time, success rates, resource utilization
    - **Configuration Comparison**: Relative performance of different configurations  
    - **Quality Metrics**: Coverage, error rates, action effectiveness
    - **Optimization Recommendations**: Timeout tuning, configuration selection
    """
    
    @ErrorHandler.handle_errors(
        component="MetricsAnalyzer",
        phase="initialization"
    )
    def __init__(self, metrics_dir: str):
        """
        Initialize metrics analyzer.
        
        Args:
            metrics_dir: Directory containing collected metrics
        """
        self.metrics_dir = metrics_dir
        self.analysis_dir = Path(metrics_dir).parent / "analysis"
        self.analysis_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.metrics.analyzer',
            {CONTEXT_COMPONENT: 'MetricsAnalyzer'}
        )
        
        self.logger.info(f"MetricsAnalyzer initialized: {metrics_dir}")
    
    @ErrorHandler.handle_errors(
        component="MetricsAnalyzer", 
        phase="comprehensive_analysis"
    )
    def analyze_comprehensive(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of task results.
        
        Args:
            task_results: List of all task execution results
            
        Returns:
            Dictionary containing comprehensive analysis results
        """
        with self.logger.with_context(
            total_tasks=len(task_results),
            phase="comprehensive_analysis"
        ):
            self.logger.info(LOG_START.format(phase="comprehensive metrics analysis"))
            
            analysis_results = {
                "analysis_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_tasks_analyzed": len(task_results),
                    "analyzer_version": "1.0.0"
                },
                "configuration_analysis": self._analyze_configurations(task_results),
                "performance_analysis": self._analyze_performance(task_results),
                "success_pattern_analysis": self._analyze_success_patterns(task_results),
                "execution_efficiency": self._analyze_execution_efficiency(task_results),
                "recommendations": self._generate_recommendations(task_results)
            }
            
            # Save comprehensive analysis
            analysis_file = self.analysis_dir / "comprehensive_analysis.json"
            with open(analysis_file, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            
            self.logger.info(LOG_COMPLETE.format(phase="comprehensive metrics analysis"))
            return analysis_results
    
    def _analyze_configurations(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze performance by configuration following old test framework patterns.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Configuration analysis results
        """
        # Group results by configuration
        config_groups = {}
        for result in task_results:
            config = result.config_name
            if config not in config_groups:
                config_groups[config] = []
            config_groups[config].append(result)
        
        config_analysis = {}
        
        for config_name, results in config_groups.items():
            successful_results = [r for r in results if r.success]
            
            # Basic statistics
            total_tasks = len(results)
            successful_tasks = len(successful_results)
            success_rate = (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0
            
            # Execution time statistics
            execution_times = [r.execution_time for r in results if r.execution_time > 0]
            time_stats = self._calculate_time_statistics(execution_times)
            
            # Coverage statistics (if available)
            coverage_stats = self._calculate_coverage_statistics(successful_results)
            
            config_analysis[config_name] = {
                "task_statistics": {
                    "total_tasks": total_tasks,
                    "successful_tasks": successful_tasks,
                    "failed_tasks": total_tasks - successful_tasks,
                    "success_rate": success_rate
                },
                "execution_time_statistics": time_stats,
                "coverage_statistics": coverage_stats,
                "quality_score": self._calculate_quality_score(success_rate, time_stats, coverage_stats)
            }
        
        # Rank configurations by overall performance
        ranked_configs = self._rank_configurations(config_analysis)
        
        return {
            "individual_configurations": config_analysis,
            "configuration_ranking": ranked_configs,
            "total_configurations": len(config_groups)
        }
    
    def _calculate_time_statistics(self, execution_times: List[float]) -> Dict[str, float]:
        """
        Calculate execution time statistics.
        
        Args:
            execution_times: List of execution times
            
        Returns:
            Dictionary with time statistics
        """
        if not execution_times:
            return {
                "count": 0,
                "mean": 0,
                "median": 0,
                "std_dev": 0,
                "min": 0,
                "max": 0,
                "total": 0
            }
        
        return {
            "count": len(execution_times),
            "mean": statistics.mean(execution_times),
            "median": statistics.median(execution_times),
            "std_dev": statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            "min": min(execution_times),
            "max": max(execution_times),
            "total": sum(execution_times)
        }
    
    def _calculate_coverage_statistics(self, results: List[TaskResult]) -> Dict[str, float]:
        """
        Calculate coverage statistics from task results.
        
        Args:
            results: Successful task results
            
        Returns:
            Dictionary with coverage statistics
        """
        coverage_data = {
            "method_coverage": [],
            "activity_coverage": [],
            "class_coverage": []
        }
        
        for result in results:
            if result.metrics and 'coverage' in result.metrics:
                coverage = result.metrics['coverage']
                for metric_type in coverage_data.keys():
                    if metric_type in coverage:
                        coverage_data[metric_type].append(coverage[metric_type])
        
        # Calculate statistics for each coverage type
        coverage_stats = {}
        for metric_type, values in coverage_data.items():
            if values:
                coverage_stats[f"{metric_type}_mean"] = statistics.mean(values)
                coverage_stats[f"{metric_type}_max"] = max(values)
                coverage_stats[f"{metric_type}_count"] = len(values)
            else:
                coverage_stats[f"{metric_type}_mean"] = 0
                coverage_stats[f"{metric_type}_max"] = 0
                coverage_stats[f"{metric_type}_count"] = 0
        
        return coverage_stats
    
    def _calculate_quality_score(
        self, 
        success_rate: float, 
        time_stats: Dict[str, float], 
        coverage_stats: Dict[str, float]
    ) -> float:
        """
        Calculate overall quality score for configuration.
        
        Args:
            success_rate: Success rate percentage
            time_stats: Execution time statistics
            coverage_stats: Coverage statistics
            
        Returns:
            Quality score (0-100)
        """
        # Weighted quality score calculation
        success_weight = 0.4
        efficiency_weight = 0.3  # Lower execution time is better
        coverage_weight = 0.3
        
        # Success rate component (0-100)
        success_component = success_rate * success_weight
        
        # Efficiency component (normalize execution time)
        efficiency_component = 0
        if time_stats["mean"] > 0:
            # Inverse relationship - faster execution gets higher score
            normalized_time = min(100, 300 / time_stats["mean"])  # 300s as reference
            efficiency_component = normalized_time * efficiency_weight
        
        # Coverage component
        coverage_component = 0
        method_coverage = coverage_stats.get("method_coverage_mean", 0)
        if method_coverage > 0:
            coverage_component = method_coverage * coverage_weight
        
        quality_score = success_component + efficiency_component + coverage_component
        return min(100, max(0, quality_score))
    
    def _rank_configurations(self, config_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Rank configurations by quality score and other metrics.
        
        Args:
            config_analysis: Configuration analysis results
            
        Returns:
            List of configurations ranked by performance
        """
        ranked_configs = []
        
        for config_name, analysis in config_analysis.items():
            ranked_configs.append({
                "configuration": config_name,
                "quality_score": analysis["quality_score"],
                "success_rate": analysis["task_statistics"]["success_rate"],
                "average_execution_time": analysis["execution_time_statistics"]["mean"],
                "total_tasks": analysis["task_statistics"]["total_tasks"]
            })
        
        # Sort by quality score (descending)
        ranked_configs.sort(key=lambda x: x["quality_score"], reverse=True)
        
        return ranked_configs
    
    def _analyze_performance(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze overall performance patterns.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Performance analysis results
        """
        successful_results = [r for r in task_results if r.success]
        failed_results = [r for r in task_results if not r.success]
        
        # Overall statistics
        total_execution_time = sum(r.execution_time for r in task_results if r.execution_time > 0)
        execution_times = [r.execution_time for r in task_results if r.execution_time > 0]
        
        performance_analysis = {
            "overall_statistics": {
                "total_tasks": len(task_results),
                "successful_tasks": len(successful_results),
                "failed_tasks": len(failed_results),
                "overall_success_rate": (len(successful_results) / len(task_results)) * 100 if task_results else 0,
                "total_execution_time": total_execution_time,
                "average_task_time": statistics.mean(execution_times) if execution_times else 0
            },
            "execution_time_distribution": self._analyze_time_distribution(execution_times),
            "failure_analysis": self._analyze_failures(failed_results)
        }
        
        return performance_analysis
    
    def _analyze_time_distribution(self, execution_times: List[float]) -> Dict[str, Any]:
        """
        Analyze distribution of execution times.
        
        Args:
            execution_times: List of execution times
            
        Returns:
            Time distribution analysis
        """
        if not execution_times:
            return {"no_data": True}
        
        # Create time buckets for distribution analysis
        time_buckets = {
            "0-60s": 0,
            "60-120s": 0, 
            "120-180s": 0,
            "180-300s": 0,
            "300s+": 0
        }
        
        for time_val in execution_times:
            if time_val <= 60:
                time_buckets["0-60s"] += 1
            elif time_val <= 120:
                time_buckets["60-120s"] += 1
            elif time_val <= 180:
                time_buckets["120-180s"] += 1
            elif time_val <= 300:
                time_buckets["180-300s"] += 1
            else:
                time_buckets["300s+"] += 1
        
        return {
            "distribution_buckets": time_buckets,
            "statistics": self._calculate_time_statistics(execution_times)
        }
    
    def _analyze_failures(self, failed_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze failure patterns and causes.
        
        Args:
            failed_results: Failed task results
            
        Returns:
            Failure analysis results
        """
        if not failed_results:
            return {"no_failures": True}
        
        # Categorize failure reasons
        failure_categories = {}
        configuration_failures = {}
        
        for result in failed_results:
            # Categorize by error message
            error_category = self._categorize_error(result.error_message)
            failure_categories[error_category] = failure_categories.get(error_category, 0) + 1
            
            # Track failures by configuration
            config = result.config_name
            configuration_failures[config] = configuration_failures.get(config, 0) + 1
        
        return {
            "total_failures": len(failed_results),
            "failure_categories": failure_categories,
            "failures_by_configuration": configuration_failures,
            "failure_rate_by_config": {
                config: count for config, count in configuration_failures.items()
            }
        }
    
    def _categorize_error(self, error_message: str) -> str:
        """
        Categorize error message into general failure type.
        
        Args:
            error_message: Error message from task execution
            
        Returns:
            Error category string
        """
        if not error_message:
            return "unknown"
        
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "emulator" in error_lower:
            return "emulator_error"
        elif "installation" in error_lower or "install" in error_lower:
            return "app_installation"
        elif "connection" in error_lower or "adb" in error_lower:
            return "device_connection"
        elif "memory" in error_lower or "oom" in error_lower:
            return "memory_error"
        else:
            return "other"
    
    def _analyze_success_patterns(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze patterns in successful task execution.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Success pattern analysis
        """
        successful_results = [r for r in task_results if r.success]
        
        if not successful_results:
            return {"no_successful_tasks": True}
        
        # Analyze success by APK
        apk_success = {}
        for result in successful_results:
            apk = result.apk_name
            if apk not in apk_success:
                apk_success[apk] = {"successful": 0, "total": 0}
            apk_success[apk]["successful"] += 1
        
        # Count total tasks per APK
        for result in task_results:
            apk = result.apk_name
            if apk not in apk_success:
                apk_success[apk] = {"successful": 0, "total": 0}
            apk_success[apk]["total"] += 1
        
        # Calculate success rates per APK
        for apk_data in apk_success.values():
            apk_data["success_rate"] = (
                apk_data["successful"] / apk_data["total"] * 100
                if apk_data["total"] > 0 else 0
            )
        
        return {
            "success_by_apk": apk_success,
            "most_successful_apks": sorted(
                [(apk, data["success_rate"]) for apk, data in apk_success.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
        }
    
    def _analyze_execution_efficiency(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze execution efficiency and resource utilization.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Execution efficiency analysis
        """
        execution_times = [r.execution_time for r in task_results if r.execution_time > 0]
        
        if not execution_times:
            return {"no_timing_data": True}
        
        total_time = sum(execution_times)
        task_count = len(execution_times)
        
        efficiency_analysis = {
            "time_utilization": {
                "total_execution_time_hours": total_time / 3600,
                "average_task_time_minutes": (total_time / task_count) / 60 if task_count > 0 else 0,
                "time_per_task_efficiency": self._calculate_time_efficiency(execution_times)
            },
            "execution_consistency": {
                "coefficient_of_variation": (
                    statistics.stdev(execution_times) / statistics.mean(execution_times)
                    if len(execution_times) > 1 and statistics.mean(execution_times) > 0 else 0
                ),
                "time_variance": statistics.variance(execution_times) if len(execution_times) > 1 else 0
            }
        }
        
        return efficiency_analysis
    
    def _calculate_time_efficiency(self, execution_times: List[float]) -> Dict[str, float]:
        """
        Calculate time efficiency metrics.
        
        Args:
            execution_times: List of execution times
            
        Returns:
            Time efficiency metrics
        """
        if not execution_times:
            return {}
        
        # Calculate percentiles for efficiency analysis
        sorted_times = sorted(execution_times)
        n = len(sorted_times)
        
        return {
            "p25": sorted_times[int(0.25 * n)],
            "p50": sorted_times[int(0.50 * n)],
            "p75": sorted_times[int(0.75 * n)],
            "p90": sorted_times[int(0.90 * n)],
            "iqr": sorted_times[int(0.75 * n)] - sorted_times[int(0.25 * n)]
        }
    
    def _generate_recommendations(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Generate optimization recommendations based on analysis.
        
        Args:
            task_results: Task execution results
            
        Returns:
            Dictionary with recommendations
        """
        recommendations = {
            "configuration_recommendations": self._recommend_configurations(task_results),
            "timeout_recommendations": self._recommend_timeouts(task_results),
            "resource_recommendations": self._recommend_resources(task_results),
            "general_recommendations": []
        }
        
        # Add general recommendations based on patterns
        execution_times = [r.execution_time for r in task_results if r.execution_time > 0]
        success_rate = sum(1 for r in task_results if r.success) / len(task_results) * 100 if task_results else 0
        
        if success_rate < 80:
            recommendations["general_recommendations"].append(
                "Consider reviewing configuration parameters - success rate below 80%"
            )
        
        if execution_times and statistics.mean(execution_times) > 240:  # 4 minutes
            recommendations["general_recommendations"].append(
                "Consider reducing timeout values - average execution time is high"
            )
        
        return recommendations
    
    def _recommend_configurations(self, task_results: List[TaskResult]) -> List[Dict[str, Any]]:
        """Generate configuration recommendations."""
        config_analysis = self._analyze_configurations(task_results)
        ranked_configs = config_analysis["configuration_ranking"]
        
        recommendations = []
        
        if ranked_configs:
            top_config = ranked_configs[0]
            recommendations.append({
                "type": "best_configuration",
                "configuration": top_config["configuration"],
                "reason": f"Highest quality score: {top_config['quality_score']:.1f}",
                "success_rate": top_config["success_rate"]
            })
        
        return recommendations
    
    def _recommend_timeouts(self, task_results: List[TaskResult]) -> List[Dict[str, Any]]:
        """Generate timeout recommendations."""
        execution_times = [r.execution_time for r in task_results if r.execution_time > 0 and r.success]
        
        recommendations = []
        
        if execution_times:
            p90_time = sorted(execution_times)[int(0.90 * len(execution_times))]
            recommended_timeout = int(p90_time * 1.2)  # 20% buffer
            
            recommendations.append({
                "type": "optimal_timeout",
                "recommended_timeout": recommended_timeout,
                "reason": f"90th percentile execution time ({p90_time:.1f}s) + 20% buffer",
                "covers_percentage": 90
            })
        
        return recommendations
    
    def _recommend_resources(self, task_results: List[TaskResult]) -> List[Dict[str, Any]]:
        """Generate resource recommendations."""
        recommendations = []
        
        # Simple resource recommendations based on execution patterns
        avg_time = statistics.mean([r.execution_time for r in task_results if r.execution_time > 0])
        if avg_time and avg_time > 300:  # 5 minutes
            recommendations.append({
                "type": "parallel_workers",
                "recommendation": "Consider increasing parallel workers if system resources allow",
                "reason": "High average execution time suggests potential for more parallelization"
            })
        
        return recommendations