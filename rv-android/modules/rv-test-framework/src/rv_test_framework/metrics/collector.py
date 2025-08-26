"""
Metrics collection system using post-execution parsing strategy.

This component collects comprehensive metrics from test execution results
through file parsing rather than real-time monitoring, ensuring data
consistency and reducing execution complexity.

### Collection Strategy:
- **Post-Execution Parsing**: Analyzes log files, trace files, and result files
- **Action Distribution**: Categorizes actions based on visitor implementation analysis
- **Coverage Metrics**: Extracts coverage data from analysis tools
- **Error Analysis**: Processes MOP violation logs and error reports
- **Performance Data**: Integrates with PerformanceMonitor data

### Architectural Decisions:
- **Parsing Over Real-Time**: Reduces execution complexity and ensures consistency
- **File-Based Analysis**: Uses existing log formats and trace files
- **Batch Processing**: Processes all results after execution completion
- **Data Aggregation**: Combines metrics from multiple sources into unified format

### Reuse from Old Test Framework:
- IntegratedMetricsCalculator patterns and coverage analysis
- CSV export patterns and data structure
- Logcat parsing and action categorization
- Static analysis integration and caching
- Error metrics collection and MOP analysis
"""

import os
import json
import csv
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_coverage.analysis.coverage.analyzer import CoverageAnalyzer

from rv_test_framework.core.models import TaskResult


# Action type mapping based on visitor analysis (from old test framework)
ACTION_TYPE_MAPPING = {
    # Primary action categories based on visitor analysis
    "click": ["CLICK", "LONG_CLICK", "CHECK", "UNCHECK"],
    "set_text": ["SET_TEXT"],
    "scroll": ["SCROLL", "SCROLL_UP", "SCROLL_DOWN", "SCROLL_LEFT", "SCROLL_RIGHT", "SET_SLIDER"],
    "coordinate": ["COORDINATE"],
    "key_event": ["BACK", "KEY_EVENT", "SYSTEM_BACK"],
    "system": ["RESTART"]
}

# Coverage metrics definitions (from old test framework)
COVERAGE_METRICS = {
    "activity_coverage": "Percentage of application activities visited",
    "method_coverage": "Percentage of application methods executed", 
    "class_coverage": "Percentage of application classes instantiated",
    "mop_method_coverage": "Percentage of monitored operation methods reached"
}


class MetricsCollector:
    """
    Collects and processes metrics from test execution results.
    
    This class reuses the metrics collection patterns from the old test framework's
    TestRunner.export_results_to_csv() and IntegratedMetricsCalculator integration.
    
    ### Data Sources:
    - **Logcat Files**: Action sequences and application behavior
    - **Trace Files**: Coverage data and method execution
    - **Error Logs**: MOP violations and runtime errors
    - **Performance Logs**: LLM response times and token usage
    - **Static Analysis**: Application structure and reachability
    
    ### Reuse from Old Test Framework:
    - TestRunner CSV export patterns and data structures
    - IntegratedMetricsCalculator analysis integration
    - Action categorization and distribution analysis
    - Coverage metrics extraction and calculation
    - Error analysis and MOP violation processing
    """
    
    @ErrorHandler.handle_errors(
        component="MetricsCollector",
        phase="initialization"
    )
    def __init__(self, results_dir: str):
        """
        Initialize metrics collector with results directory.
        
        Args:
            results_dir: Directory containing execution results
        """
        self.results_dir = results_dir
        self.metrics_dir = os.path.join(results_dir, "metrics")
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Setup logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_test_framework.metrics.collector',
            {CONTEXT_COMPONENT: 'MetricsCollector'}
        )
        
        # Error handler integration
        self.error_handler = ErrorHandler.get_instance()
        
        # Coverage analyzer for metrics extraction
        self.coverage_analyzer = CoverageAnalyzer()
        
        self.logger.info(f"MetricsCollector initialized: {results_dir}")
    
    @ErrorHandler.handle_errors(
        component="MetricsCollector",
        phase="metrics_collection"
    )
    def collect_all_metrics(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Collect comprehensive metrics from all task results.
        
        This method follows the old test framework's TestRunner.export_results_to_csv()
        patterns, collecting metrics from logcat files, trace files, and execution data.
        
        Args:
            task_results: List of task execution results
            
        Returns:
            Dictionary containing aggregated metrics
        """
        with self.logger.with_context(
            total_tasks=len(task_results),
            phase="comprehensive_metrics_collection"
        ):
            self.logger.info(LOG_START.format(phase=f"metrics collection for {len(task_results)} tasks"))
            
            # Aggregate metrics containers
            all_metrics = {
                "execution_summary": self._collect_execution_summary(task_results),
                "action_metrics": {},
                "coverage_metrics": {},
                "error_metrics": {},
                "performance_metrics": {},
                "configuration_analysis": {}
            }
            
            # Process each task result
            successful_tasks = [r for r in task_results if r.success]
            
            if successful_tasks:
                # Collect action distribution metrics
                all_metrics["action_metrics"] = self._collect_action_metrics(successful_tasks)
                
                # Collect coverage metrics
                all_metrics["coverage_metrics"] = self._collect_coverage_metrics(successful_tasks)
                
                # Collect error and MOP metrics
                all_metrics["error_metrics"] = self._collect_error_metrics(successful_tasks)
                
                # Collect performance metrics
                all_metrics["performance_metrics"] = self._collect_performance_metrics(task_results)
                
                # Analyze configuration performance
                all_metrics["configuration_analysis"] = self._analyze_configuration_performance(task_results)
            
            # Save raw metrics
            raw_metrics_file = os.path.join(self.metrics_dir, "raw_metrics.json")
            with open(raw_metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2, default=str)
            
            # Export to CSV files (following old test framework patterns)
            self._export_to_csv_files(task_results)
            
            self.logger.info(LOG_COMPLETE.format(phase="metrics collection"))
            return all_metrics
    
    def _collect_execution_summary(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Collect basic execution statistics.
        
        Args:
            task_results: List of task results
            
        Returns:
            Dictionary with execution summary
        """
        total_tasks = len(task_results)
        successful_tasks = sum(1 for r in task_results if r.success)
        failed_tasks = total_tasks - successful_tasks
        
        # Calculate timing statistics
        execution_times = [r.execution_time for r in task_results if r.execution_time > 0]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "average_execution_time": avg_execution_time,
            "total_execution_time": sum(execution_times),
            "collection_timestamp": datetime.now().isoformat()
        }
    
    def _collect_action_metrics(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Collect action distribution metrics from logcat files.
        
        Following old test framework's action categorization patterns.
        
        Args:
            task_results: Successful task results
            
        Returns:
            Dictionary with action distribution metrics
        """
        action_counts = {action_type: 0 for action_type in ACTION_TYPE_MAPPING.keys()}
        total_actions = 0
        files_processed = 0
        
        for result in task_results:
            if result.logcat_file and os.path.exists(result.logcat_file):
                try:
                    # Parse logcat file using existing infrastructure
                    logcat_data = parse_logcat_file(result.logcat_file)
                    
                    # Extract actions (simplified - real implementation would parse DroidBot actions)
                    if hasattr(logcat_data, 'actions'):
                        for action in logcat_data.actions:
                            action_type = action.get('action_type', 'UNKNOWN')
                            
                            # Categorize action
                            categorized = False
                            for category, action_types in ACTION_TYPE_MAPPING.items():
                                if action_type in action_types:
                                    action_counts[category] += 1
                                    categorized = True
                                    break
                            
                            if not categorized:
                                action_counts.setdefault('other', 0)
                                action_counts['other'] += 1
                            
                            total_actions += 1
                    
                    files_processed += 1
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process logcat file {result.logcat_file}: {e}")
        
        # Calculate percentages
        action_percentages = {}
        if total_actions > 0:
            for action_type, count in action_counts.items():
                action_percentages[f"{action_type}_percentage"] = (count / total_actions) * 100
        
        return {
            "action_counts": action_counts,
            "action_percentages": action_percentages,
            "total_actions": total_actions,
            "files_processed": files_processed
        }
    
    def _collect_coverage_metrics(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Collect coverage metrics using existing analysis infrastructure.
        
        Args:
            task_results: Successful task results
            
        Returns:
            Dictionary with coverage metrics
        """
        coverage_data = {
            "method_coverage": [],
            "activity_coverage": [], 
            "class_coverage": [],
            "mop_method_coverage": []
        }
        
        for result in task_results:
            if result.logcat_file and os.path.exists(result.logcat_file):
                try:
                    # Extract coverage metrics from task results or logcat analysis
                    # This would integrate with existing coverage analysis tools
                    if result.metrics:
                        coverage_info = result.metrics.get('coverage', {})
                        
                        for metric_type in coverage_data.keys():
                            if metric_type in coverage_info:
                                coverage_data[metric_type].append(coverage_info[metric_type])
                
                except Exception as e:
                    self.logger.warning(f"Failed to extract coverage from {result.task_id}: {e}")
        
        # Calculate aggregate statistics
        aggregated_coverage = {}
        for metric_type, values in coverage_data.items():
            if values:
                aggregated_coverage[f"{metric_type}_avg"] = sum(values) / len(values)
                aggregated_coverage[f"{metric_type}_max"] = max(values)
                aggregated_coverage[f"{metric_type}_min"] = min(values)
                aggregated_coverage[f"{metric_type}_count"] = len(values)
            else:
                aggregated_coverage[f"{metric_type}_avg"] = 0
                aggregated_coverage[f"{metric_type}_max"] = 0
                aggregated_coverage[f"{metric_type}_min"] = 0
                aggregated_coverage[f"{metric_type}_count"] = 0
        
        return aggregated_coverage
    
    def _collect_error_metrics(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Collect error and MOP violation metrics.
        
        Args:
            task_results: Successful task results
            
        Returns:
            Dictionary with error metrics
        """
        error_data = {
            "total_errors": 0,
            "mop_violations": 0,
            "runtime_errors": 0,
            "error_categories": {},
            "mop_categories": {}
        }
        
        for result in task_results:
            if result.error_message:
                error_data["total_errors"] += 1
                error_data["runtime_errors"] += 1
            
            # Extract MOP violations from logcat if available
            if result.logcat_file and os.path.exists(result.logcat_file):
                try:
                    # This would use existing MOP violation detection
                    mop_violations = self._extract_mop_violations(result.logcat_file)
                    error_data["mop_violations"] += len(mop_violations)
                    
                    # Categorize MOP violations
                    for violation in mop_violations:
                        category = violation.get('category', 'unknown')
                        error_data["mop_categories"][category] = error_data["mop_categories"].get(category, 0) + 1
                
                except Exception as e:
                    self.logger.warning(f"Failed to extract MOP violations from {result.logcat_file}: {e}")
        
        return error_data
    
    def _extract_mop_violations(self, logcat_file: str) -> List[Dict[str, Any]]:
        """
        Extract MOP violations from logcat file.
        
        This would integrate with existing MOP violation detection logic.
        
        Args:
            logcat_file: Path to logcat file
            
        Returns:
            List of MOP violation events
        """
        # Placeholder - real implementation would parse MOP violation patterns
        return []
    
    def _collect_performance_metrics(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Collect performance metrics from task execution.
        
        Args:
            task_results: All task results
            
        Returns:
            Dictionary with performance metrics
        """
        execution_times = [r.execution_time for r in task_results if r.execution_time > 0]
        
        performance_data = {
            "execution_times": {
                "average": sum(execution_times) / len(execution_times) if execution_times else 0,
                "median": sorted(execution_times)[len(execution_times)//2] if execution_times else 0,
                "max": max(execution_times) if execution_times else 0,
                "min": min(execution_times) if execution_times else 0,
                "total": sum(execution_times)
            },
            "success_rates": {
                "overall": sum(1 for r in task_results if r.success) / len(task_results) * 100 if task_results else 0
            }
        }
        
        return performance_data
    
    def _analyze_configuration_performance(self, task_results: List[TaskResult]) -> Dict[str, Any]:
        """
        Analyze performance by configuration.
        
        Args:
            task_results: All task results
            
        Returns:
            Dictionary with configuration performance analysis
        """
        config_performance = {}
        
        # Group results by configuration
        for result in task_results:
            config_name = result.config_name
            if config_name not in config_performance:
                config_performance[config_name] = {
                    "total_tasks": 0,
                    "successful_tasks": 0,
                    "execution_times": [],
                    "success_rate": 0
                }
            
            config_performance[config_name]["total_tasks"] += 1
            if result.success:
                config_performance[config_name]["successful_tasks"] += 1
            if result.execution_time > 0:
                config_performance[config_name]["execution_times"].append(result.execution_time)
        
        # Calculate derived metrics
        for config_name, data in config_performance.items():
            if data["total_tasks"] > 0:
                data["success_rate"] = (data["successful_tasks"] / data["total_tasks"]) * 100
            
            if data["execution_times"]:
                data["average_execution_time"] = sum(data["execution_times"]) / len(data["execution_times"])
            else:
                data["average_execution_time"] = 0
        
        return config_performance
    
    def _export_to_csv_files(self, task_results: List[TaskResult]) -> None:
        """
        Export metrics to CSV files following old test framework patterns.
        
        This method reuses the CSV export patterns from TestRunner.export_results_to_csv().
        
        Args:
            task_results: List of all task results
        """
        # Coverage data CSV (following old test framework structure)
        coverage_file = os.path.join(self.metrics_dir, "coverage_data.csv")
        with open(coverage_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "task_id", "config_name", "apk_name", "repetition",
                "method_coverage", "activity_coverage", "mop_method_coverage",
                "execution_time", "success", "timestamp"
            ])
            
            for result in task_results:
                # Extract coverage data from result metrics
                coverage = result.metrics.get('coverage', {}) if result.metrics else {}
                
                writer.writerow([
                    result.task_id,
                    result.config_name,
                    result.apk_name,
                    result.repetition,
                    coverage.get('method_coverage', 0),
                    coverage.get('activity_coverage', 0),
                    coverage.get('mop_method_coverage', 0),
                    result.execution_time,
                    result.success,
                    datetime.now().isoformat()
                ])
        
        # Performance summary CSV
        summary_file = os.path.join(self.metrics_dir, "performance_summary.csv")
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "config_name", "total_tasks", "successful_tasks", "success_rate",
                "average_execution_time", "total_execution_time"
            ])
            
            # Group by configuration
            config_stats = {}
            for result in task_results:
                config = result.config_name
                if config not in config_stats:
                    config_stats[config] = {
                        "total": 0, "successful": 0, "times": []
                    }
                
                config_stats[config]["total"] += 1
                if result.success:
                    config_stats[config]["successful"] += 1
                if result.execution_time > 0:
                    config_stats[config]["times"].append(result.execution_time)
            
            # Write configuration statistics
            for config_name, stats in config_stats.items():
                success_rate = (stats["successful"] / stats["total"]) * 100 if stats["total"] > 0 else 0
                avg_time = sum(stats["times"]) / len(stats["times"]) if stats["times"] else 0
                total_time = sum(stats["times"])
                
                writer.writerow([
                    config_name, stats["total"], stats["successful"],
                    success_rate, avg_time, total_time
                ])
        
        self.logger.info(f"Metrics exported to CSV files: {self.metrics_dir}")