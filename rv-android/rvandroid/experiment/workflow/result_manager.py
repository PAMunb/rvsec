# rvandroid/experiment/workflow/result_manager.py
"""
Consolidated result manager for RV-Android experiments.

This module provides comprehensive result management functionality, including
data export to CSV and JSON formats, and basic reporting capabilities.
It consolidates the functionality from multiple result managers into a
unified, streamlined component.
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from rvandroid.experiment.event import EventBus, EventType
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.experiment.task.interfaces import TaskState
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import (
    CONTEXT_COMPONENT, 
    LOG_START, 
    LOG_COMPLETE, 
    LOG_ERROR,
    LOG_SKIPPED
)
from rvandroid.util.logging.manager import LoggingManager


class ResultManager:
    """
    Consolidated result manager for handling experiment results and generating reports.

    ### Architectural Decisions:
    - Centralizes all result management functionality in a single component
    - Generates standardized CSV and JSON output formats for data analysis
    - Provides streamlined reporting without complex visualizations
    - Integrates with the experiment workflow for automated result processing
    - Supports both individual task results and aggregated experiment summaries

    ### Role in the System:
    - Processes completed experiment tasks to extract metrics and results
    - Generates standardized result files (CSV and JSON) for external analysis
    - Creates summary reports for quick experiment overview
    - Handles error reporting and monitored operations violations
    - Publishes experiment completion events with result summaries

    ### Key Considerations:
    - Focuses on essential data export without complex dashboard generation
    - Maintains compatibility with existing result analysis workflows
    - Provides robust error handling for result processing failures
    - Supports incremental result processing for large experiments
    - Ensures data consistency across different output formats

    ### Integration Strategy:
    - Seamlessly integrates with task storage for accessing completed tasks
    - Compatible with existing experiment controller and workflow systems
    - Supports event-driven result processing through the experiment event bus
    - Provides standardized interfaces for result data access
    - Enables flexible result processing through configuration options

    ### Performance and Scalability:
    - Designed for efficient processing of large experiment datasets
    - Implements streaming processing for memory-efficient operation
    - Supports parallel processing of independent result components
    - Optimized for batch processing of multiple experiment results
    - Provides configurable output options to balance detail and performance
    """

    def __init__(self, results_dir: str, task_storage: TaskStorage, event_bus: Optional[EventBus] = None):
        """
        Initialize the consolidated result manager.

        Args:
            results_dir: Directory for storing experiment results
            task_storage: Task storage containing completed tasks
            event_bus: Optional event bus for publishing events
        """
        self.results_dir = results_dir
        self.task_storage = task_storage
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Initialize logging with comprehensive context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.workflow.result_manager',
            {CONTEXT_COMPONENT: 'ResultManager'}
        )

        # Result processing state
        self.processed_tasks: Dict[str, bool] = {}
        self.result_summary: Dict[str, Any] = {}

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    def generate_reports(self) -> None:
        """
        Generate all experiment reports and result files.
        
        This method orchestrates the complete result generation process,
        creating standardized CSV and JSON files for experiment analysis.
        """
        with self.logger.with_context(phase="result_generation"):
            self.logger.info(LOG_START.format(operation="comprehensive result generation"))

            try:
                # Load and validate completed tasks
                completed_tasks = self._load_completed_tasks()
                if not completed_tasks:
                    self.logger.warning("No completed tasks found for result generation")
                    return

                # Generate core result files
                self._generate_coverage_csv(completed_tasks)
                self._generate_errors_csv(completed_tasks) 
                self._generate_summary_csv(completed_tasks)
                self._generate_results_json(completed_tasks)
                self._generate_instrument_errors_json(completed_tasks)

                # Create experiment summary
                self._create_experiment_summary(completed_tasks)

                self.logger.info(LOG_COMPLETE.format(operation="comprehensive result generation"))

                # Publish completion event
                self._publish_completion_event(len(completed_tasks))

            except Exception as e:
                self.error_handler.handle_error(e, {"component": "ResultManager", "phase": "result_generation"})
                self.logger.error(LOG_ERROR.format(
                    operation="generating experiment results",
                    error=str(e)
                ))

    def _load_completed_tasks(self) -> List[Any]:
        """
        Load completed tasks from storage with error handling.
        
        Returns:
            List of completed tasks ready for processing
        """
        try:
            # Get all tasks and filter for completed ones
            all_tasks = self.task_storage.get_tasks()
            completed_tasks = [
                task for task in all_tasks 
                if hasattr(task, 'result') and 
                getattr(task.result, 'state', None) == TaskState.COMPLETED
            ]
            
            self.logger.info(f"Loaded {len(completed_tasks)} completed tasks out of {len(all_tasks)} total tasks")
            return completed_tasks

        except Exception as e:
            self.logger.error(LOG_ERROR.format(
                operation="loading completed tasks",
                error=str(e)
            ))
            return []

    def _generate_coverage_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate detailed coverage CSV file with per-method coverage data.
        
        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="coverage_csv_generation"):
            self.logger.info(LOG_START.format(operation="coverage CSV generation"))

            try:
                coverage_file = os.path.join(self.results_dir, "coverage.csv")
                
                with open(coverage_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write header matching expected format
                    writer.writerow([
                        'apk', 'rep', 'timeout', 'tool', 'time', 'class', 'method', 
                        'signature', 'cov_class', 'cov_act', 'cov_method', 'cov_rv_method'
                    ])
                    
                    # Process each completed task
                    for task in completed_tasks:
                        self._write_task_coverage_data(writer, task)

                self.logger.info(f"Coverage CSV generated: {coverage_file}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating coverage CSV",
                    error=str(e)
                ))

    def _write_task_coverage_data(self, writer: csv.writer, task: Any) -> None:
        """
        Write coverage data for a single task to CSV.
        
        ### Critical Architecture Decision:
        This method generates the coverage.csv output by extracting timing data that has been
        preserved through the complete data flow: RvCoverageLog -> MethodCoverageData -> CSV.
        The timing data (time_since_task_start) calculated by CoverageTracker is essential
        for accurate analysis of when methods were called during task execution.
        
        Args:
            writer: CSV writer instance
            task: Task to process for coverage data
        """
        try:
            # Extract task configuration
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_name
            
            # Get repository data if available
            if hasattr(task, 'repository') and task.repository:
                repository = task.repository
                
                # Get method calls with coverage information - these are already sorted by time
                method_calls = repository.get_method_calls()
                
                # Calculate progressive coverage metrics
                total_methods = len(repository.get_static_methods()) if hasattr(repository, 'get_static_methods') else 0
                total_activities = len(repository.get_static_activities()) if hasattr(repository, 'get_static_activities') else 0
                total_mop_methods = len(repository.get_mop_methods()) if hasattr(repository, 'get_mop_methods') else 1
                
                # Track cumulative unique calls for progressive coverage calculation
                called_methods = set()
                called_activities = set()
                mop_methods = set()
                
                # Process each method call in chronological order (already sorted)
                for i, call in enumerate(method_calls, 1):
                    signature = call.get('signature', '')
                    
                    # Add to cumulative sets
                    called_methods.add(signature)
                    
                    # Track activities if available  
                    activity_name = call.get('activity')
                    if activity_name:
                        called_activities.add(activity_name)
                    
                    # Track monitored operations methods
                    if call.get('is_mop_method', False):
                        mop_methods.add(signature)
                    
                    # Calculate progressive coverage based on cumulative unique calls
                    method_coverage = (len(called_methods) / total_methods * 100) if total_methods > 0 else 0
                    activity_coverage = (len(called_activities) / total_activities * 100) if total_activities > 0 else 0
                    mop_coverage = (len(mop_methods) / total_mop_methods * 100) if total_mop_methods > 0 else 0
                    
                    # Write row for this method call
                    writer.writerow([
                        apk_name,
                        repetition,
                        timeout,
                        tool_name,
                        call.get('time', i),  # Uses preserved time_since_task_start from RvCoverageLog
                        call.get('class_name', ''),
                        call.get('method_name', ''),
                        signature,
                        round(method_coverage, 2),
                        round(activity_coverage, 2),
                        round(method_coverage, 2),  # Same as method coverage for now
                        round(mop_coverage, 2)
                    ])
            else:
                # Fallback: write single row with available metrics
                metrics = getattr(task.result, 'coverage_metrics', {})
                writer.writerow([
                    apk_name,
                    repetition,
                    timeout,
                    tool_name,
                    1,  # Default time
                    '',  # No specific class
                    '',  # No specific method
                    '',  # No signature
                    metrics.get('method_coverage', 0),
                    metrics.get('activities_coverage', 0),
                    metrics.get('method_coverage', 0),
                    metrics.get('mop_coverage', 0)
                ])

        except Exception as e:
            self.logger.warning(f"Failed to write coverage data for task {task.id}: {e}")

    def _generate_errors_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate detailed errors CSV file with monitored operations violations.
        
        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="errors_csv_generation"):
            self.logger.info(LOG_START.format(operation="errors CSV generation"))

            try:
                errors_file = os.path.join(self.results_dir, "errors.csv")
                
                with open(errors_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write header for monitored operations violations
                    writer.writerow([
                        'apk', 'rep', 'timeout', 'tool', 'time', 'spec', 'class', 
                        'method', 'message', 'unique_msg'
                    ])
                    
                    # Process each completed task
                    for task in completed_tasks:
                        self._write_task_error_data(writer, task)

                self.logger.info(f"Errors CSV generated: {errors_file}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating errors CSV",
                    error=str(e)
                ))

    def _write_task_error_data(self, writer: csv.writer, task: Any) -> None:
        """
        Write error data for a single task to CSV.
        
        ### Critical Architecture Decision:
        This method generates the errors.csv output by extracting timing data from
        RvErrorLog objects. The time_since_task_start calculated by CoverageTracker
        when processing monitored operations violations is preserved to provide
        accurate timing information for security analysis and research.
        
        Args:
            writer: CSV writer instance
            task: Task to process for error data
        """
        try:
            # Extract task configuration
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_name
            
            # Get repository data if available
            if hasattr(task, 'repository') and task.repository:
                repository = task.repository
                errors = repository.get_errors()
                
                # Process each monitored operations violation
                for i, error in enumerate(errors, 1):
                    # Extract fields using correct field names from RvErrorLog.to_dict()
                    class_full_name = error.get('class_full_name', '')
                    method = error.get('method', '')
                    spec = error.get('spec', '')
                    error_type = error.get('error_type', '')
                    message = error.get('message', '')
                    
                    # Use existing unique_msg if available, otherwise construct it
                    unique_msg = error.get('unique_msg', f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}")
                    
                    # CRITICAL: Use time_since_task_start directly - it's already in seconds from RvErrorLog
                    # This preserves the accurate timing calculated by CoverageTracker
                    time_value = error.get('time_since_task_start', i)
                    if time_value is None or time_value == 0:
                        time_value = i  # Fallback to sequence number only if no timing data
                    
                    writer.writerow([
                        apk_name,
                        repetition,
                        timeout,
                        tool_name,
                        time_value,
                        spec,
                        class_full_name,
                        method,
                        message,
                        unique_msg
                    ])

        except Exception as e:
            self.logger.warning(f"Failed to write error data for task {task.id}: {e}")

    def _generate_summary_csv(self, completed_tasks: List[Any]) -> None:
        """
        Generate summary CSV file with aggregate metrics per task.
        
        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="summary_csv_generation"):
            self.logger.info(LOG_START.format(operation="summary CSV generation"))

            try:
                summary_file = os.path.join(self.results_dir, "summary.csv")
                
                with open(summary_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write header for summary metrics
                    writer.writerow([
                        'apk', 'rep', 'timeout', 'tool', 'cov_act', 'cov_method', 'cov_rv_method', 'errors'
                    ])
                    
                    # Process each completed task
                    for task in completed_tasks:
                        self._write_task_summary_data(writer, task)

                self.logger.info(f"Summary CSV generated: {summary_file}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating summary CSV",
                    error=str(e)
                ))

    def _write_task_summary_data(self, writer: csv.writer, task: Any) -> None:
        """
        Write summary data for a single task to CSV.
        
        Args:
            writer: CSV writer instance
            task: Task to process for summary data
        """
        try:
            # Extract task configuration
            config = task.config
            apk_name = config.apk_name
            repetition = config.repetition
            timeout = config.timeout
            tool_name = config.tool_name
            
            # Get final metrics from task result (which contains the correct data from tasks.json)
            # The task.result.coverage_metrics contains the actual coverage data that exists in tasks.json
            if hasattr(task, 'result') and hasattr(task.result, 'coverage_metrics'):
                metrics = task.result.coverage_metrics
                activities_coverage = metrics.get('activities_coverage', 0)
                method_coverage = metrics.get('method_coverage', 0)
                # Use the correct field name for MOP coverage
                mop_coverage = metrics.get('methods_jca_reachable_coverage', 0)
                error_count = metrics.get('total_errors', 0)
            elif hasattr(task, 'repository') and task.repository:
                # Fallback to repository if task result metrics not available
                metrics = task.repository.calculate_metrics()
                activities_coverage = getattr(metrics, 'activity_coverage', 0)
                method_coverage = getattr(metrics, 'method_coverage', 0)
                mop_coverage = getattr(metrics, 'mop_method_coverage', 0)
                error_count = getattr(metrics, 'total_errors', 0)
            else:
                # Final fallback - use zeros
                activities_coverage = 0
                method_coverage = 0
                mop_coverage = 0
                error_count = 0
                self.logger.warning(f"No coverage metrics available for task {task.id}")
            
            writer.writerow([
                apk_name,
                repetition,
                timeout,
                tool_name,
                round(activities_coverage, 2),
                round(method_coverage, 2),
                round(mop_coverage, 2),
                error_count
            ])

        except Exception as e:
            self.logger.warning(f"Failed to write summary data for task {task.id}: {e}")

    def _generate_results_json(self, completed_tasks: List[Any]) -> None:
        """
        Generate comprehensive results JSON file with structured experiment data.
        
        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="results_json_generation"):
            self.logger.info(LOG_START.format(operation="results JSON generation"))

            try:
                results_file = os.path.join(self.results_dir, "results.json")
                
                # Build structured results data
                results_data = {}
                
                # Process tasks by APK for hierarchical structure
                for task in completed_tasks:
                    apk_name = task.config.apk_name
                    rep = task.config.repetition
                    timeout = task.config.timeout
                    tool_name = task.config.tool_name
                    
                    # Initialize nested structure
                    if apk_name not in results_data:
                        results_data[apk_name] = {"repetitions": {}}
                    
                    if str(rep) not in results_data[apk_name]["repetitions"]:
                        results_data[apk_name]["repetitions"][str(rep)] = {"timeouts": {}}
                    
                    if str(timeout) not in results_data[apk_name]["repetitions"][str(rep)]["timeouts"]:
                        results_data[apk_name]["repetitions"][str(rep)]["timeouts"][str(timeout)] = {"tools": {}}
                    
                    # Add tool-specific data
                    tool_data = self._extract_task_data(task)
                    results_data[apk_name]["repetitions"][str(rep)]["timeouts"][str(timeout)]["tools"][tool_name] = tool_data
                
                # Write JSON file
                with open(results_file, 'w', encoding='utf-8') as f:
                    json.dump(results_data, f, indent=2, ensure_ascii=False)

                self.logger.info(f"Results JSON generated: {results_file}")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating results JSON",
                    error=str(e)
                ))

    def _extract_task_data(self, task: Any) -> Dict[str, Any]:
        """
        Extract comprehensive data for a single task.
        
        Args:
            task: Task to extract data from
            
        Returns:
            Dictionary with task data
        """
        try:
            # Base task information
            task_data = {
                "start_time": getattr(task.result, 'start_time', datetime.now()).timestamp() if hasattr(task, 'result') else None,
                "summary": {},
                "monitored_operations_errors": {
                    "total": 0,
                    "messages": [],
                    "details": []
                }
            }
            
            # Get metrics from repository or result
            if hasattr(task, 'repository') and task.repository:
                metrics = task.repository.calculate_metrics()
                metrics_dict = metrics.to_dict()  # Convert to dict to get calculated percentages
                
                task_data["summary"] = {
                    "called_activities": metrics.called_activities,
                    "called_methods": metrics.called_methods,
                    "called_methods_mop_reachable": metrics.called_mop_methods,
                    "activities_coverage": metrics_dict["activity_coverage"],
                    "method_coverage": metrics_dict["method_coverage"],
                    "methods_mop_reachable_coverage": metrics_dict["mop_method_coverage"],
                    "monitored_operations_errors_count": metrics.total_errors
                }
                
                # Get error details
                errors = task.repository.get_errors()
                task_data["monitored_operations_errors"]["total"] = len(errors)
                
                # Fix: Create complete messages using correct field names from RvErrorLog.to_dict()
                # The unique_msg field already contains the complete format, but if not available, construct it correctly
                messages = []
                for error in errors:
                    # Try to use existing unique_msg first, otherwise construct from correct field names
                    if 'unique_msg' in error and error['unique_msg']:
                        messages.append(error['unique_msg'])
                    else:
                        # Construct using correct field names
                        class_full_name = error.get('class_full_name', '')
                        method = error.get('method', '')
                        spec = error.get('spec', '')
                        error_type = error.get('error_type', '')
                        message = error.get('message', '')
                        complete_msg = f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}"
                        messages.append(complete_msg)
                
                task_data["monitored_operations_errors"]["messages"] = messages
                task_data["monitored_operations_errors"]["details"] = errors
                
            else:
                # Fallback to task result metrics
                metrics = getattr(task.result, 'coverage_metrics', {})
                task_data["summary"] = {
                    "called_activities": metrics.get('called_activities', 0),
                    "called_methods": metrics.get('called_methods', 0),
                    "called_methods_mop_reachable": metrics.get('called_mop_methods', 0),
                    "activities_coverage": metrics.get('activities_coverage', 0),
                    "method_coverage": metrics.get('method_coverage', 0),
                    "methods_mop_reachable_coverage": metrics.get('mop_coverage', 0),
                    "monitored_operations_errors_count": metrics.get('total_errors', 0)
                }
            
            return task_data

        except Exception as e:
            self.logger.warning(f"Failed to extract data for task {task.id}: {e}")
            return {"summary": {}, "monitored_operations_errors": {"total": 0, "messages": [], "details": []}}

    def _generate_instrument_errors_json(self, completed_tasks: List[Any]) -> None:
        """
        Generate instrumentation errors JSON file if any errors occurred.
        
        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="instrument_errors_json_generation"):
            self.logger.info(LOG_START.format(operation="instrumentation errors JSON generation"))

            try:
                # Collect instrumentation errors
                instrument_errors = {}
                
                for task in completed_tasks:
                    if hasattr(task.result, 'instrument_errors') and task.result.instrument_errors:
                        apk_name = task.config.apk_name
                        instrument_errors[apk_name] = task.result.instrument_errors

                # Only create file if there are errors
                if instrument_errors:
                    errors_file = os.path.join(self.results_dir, "instrument_errors.json")
                    
                    with open(errors_file, 'w', encoding='utf-8') as f:
                        json.dump(instrument_errors, f, indent=2, ensure_ascii=False)

                    self.logger.info(f"Instrumentation errors JSON generated: {errors_file}")
                else:
                    # Create empty file for consistency
                    errors_file = os.path.join(self.results_dir, "instrument_errors.json")
                    with open(errors_file, 'w', encoding='utf-8') as f:
                        json.dump({}, f)
                    
                    self.logger.info("No instrumentation errors found - empty file created")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="generating instrumentation errors JSON",
                    error=str(e)
                ))

    def _create_experiment_summary(self, completed_tasks: List[Any]) -> None:
        """
        Create a high-level experiment summary for logging and tracking.
        
        Args:
            completed_tasks: List of completed tasks to summarize
        """
        try:
            # Calculate summary statistics
            total_tasks = len(completed_tasks)
            unique_apks = len(set(task.config.apk_name for task in completed_tasks))
            unique_tools = len(set(task.config.tool_name for task in completed_tasks))
            
            # Calculate average metrics
            total_method_coverage = sum(
                getattr(task.repository.calculate_metrics(), 'method_coverage', 0) 
                if hasattr(task, 'repository') and task.repository
                else getattr(task.result, 'coverage_metrics', {}).get('method_coverage', 0)
                for task in completed_tasks
            )
            
            total_errors = sum(
                getattr(task.repository.calculate_metrics(), 'total_errors', 0)
                if hasattr(task, 'repository') and task.repository  
                else getattr(task.result, 'coverage_metrics', {}).get('total_errors', 0)
                for task in completed_tasks
            )
            
            avg_method_coverage = total_method_coverage / total_tasks if total_tasks > 0 else 0
            
            # Store summary for later use
            self.result_summary = {
                "total_tasks": total_tasks,
                "unique_apks": unique_apks,
                "unique_tools": unique_tools,
                "avg_method_coverage": round(avg_method_coverage, 2),
                "total_monitored_operations_errors": total_errors,
                "completion_time": datetime.now().isoformat()
            }
            
            self.logger.info(f"Experiment summary: {total_tasks} tasks, {unique_apks} APKs, {unique_tools} tools, {avg_method_coverage:.2f}% avg coverage, {total_errors} total monitored operations errors")

        except Exception as e:
            self.logger.warning(f"Failed to create experiment summary: {e}")

    def _publish_completion_event(self, task_count: int) -> None:
        """
        Publish experiment completion event with result information.
        
        Args:
            task_count: Number of tasks processed
        """
        try:
            summary_msg = f"Result generation completed for {task_count} tasks"
            if self.result_summary:
                summary_msg += f" - {self.result_summary.get('avg_method_coverage', 0):.1f}% avg coverage, {self.result_summary.get('total_monitored_operations_errors', 0)} errors"
            
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_COMPLETED,
                experiment_id=f"results-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                message=summary_msg,
                source="ResultManager"
            )
        except Exception as e:
            self.logger.warning(f"Failed to publish completion event: {e}")

    def get_result_summary(self) -> Dict[str, Any]:
        """
        Get the current result summary.
        
        Returns:
            Dictionary with experiment result summary
        """
        return self.result_summary.copy()