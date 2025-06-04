# rvandroid/experiment/processor/analysis.py
"""
Analysis processor for the unified execution framework.

This module provides the AnalysisProcessor class, which handles the
analysis phase of experiment execution, including coverage analysis,
error analysis, and result processing.
"""

import json
import os
from typing import List, Optional, Dict, Any, Set

from rvandroid.experiment.core.interfaces import (
    IExecutionContext,
    ExecutionPhase
)
from rvandroid.experiment.event import (
    EventBus,
    get_event_bus,
    EventType,
    Event
)
from rvandroid.experiment.processor.base import BasePhaseProcessor
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.experiment.task.models import TaskFactory, Task
from rvandroid.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.domain.coverage import LogcatRepository


class AnalysisProcessor(BasePhaseProcessor):
    """
    Processor for result analysis phase.
    
    ### Architectural Decisions:
    - Implements a focused processor for result analysis tasks
    - Provides clean separation of analysis concerns
    - Enables flexible result processing strategies
    - Supports comprehensive error handling
    
    ### Role in the System:
    - Processes experiment results after execution
    - Analyzes coverage and error data
    - Generates experiment metrics and statistics
    - Prepares data for reporting and visualization
    """
    
    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the analysis processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for event publishing
        """
        super().__init__(
            processor_name="AnalysisProcessor",
            supported_phases=[ExecutionPhase.ANALYSIS],
            context=context,
            event_bus=event_bus or get_event_bus()
        )
        
        # Create task factory and storage
        self.task_factory = TaskFactory(Task)
        storage_file = os.path.join(context.results_dir, "tasks.json")
        self.task_storage = TaskStorage(storage_file, self.task_factory)
        
    def _process_phase(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the analysis phase.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if phase != ExecutionPhase.ANALYSIS:
            self.logger.warning(f"Unsupported phase: {phase.name}")
            return False
            
        return self._analyze_results(context)
        
    def _analyze_results(self, context: IExecutionContext) -> bool:
        """
        Analyze experiment results.
        
        Args:
            context: Execution context
            
        Returns:
            True if analysis was successful, False otherwise
        """
        with self.logger.with_context(phase="results_analysis"):
            self.logger.info(LOG_START.format(operation="results analysis"))
            
            success = True
            
            # Process tasks
            if not self.task_storage.load():
                self.logger.error("Failed to load tasks for analysis")
                return False
                
            tasks = self.task_storage.get_tasks()
            
            if not tasks:
                self.logger.warning("No tasks found for analysis")
                return True
                
            # Analyze coverage data
            coverage_success = self._analyze_coverage(tasks, context)
            if not coverage_success:
                self.logger.error("Coverage analysis failed")
                success = False
                
            # Analyze errors
            error_success = self._analyze_errors(tasks, context)
            if not error_success:
                self.logger.error("Error analysis failed")
                success = False
                
            # Generate summary
            summary_success = self._generate_summary(tasks, context)
            if not summary_success:
                self.logger.error("Summary generation failed")
                success = False
                
            if success:
                self.logger.info(LOG_COMPLETE.format(operation="results analysis"))
            else:
                self.logger.error(LOG_ERROR.format(
                    operation="results analysis",
                    error="One or more analysis steps failed"
                ))
                
            return success
            
    def _analyze_coverage(self, tasks: List[Task], context: IExecutionContext) -> bool:
        """
        Analyze coverage data from tasks.
        
        Args:
            tasks: List of tasks to analyze
            context: Execution context
            
        Returns:
            True if analysis was successful, False otherwise
        """
        with self.logger.with_context(phase="coverage_analysis"):
            self.logger.info(LOG_START.format(operation="coverage analysis"))
            
            try:
                coverage_data = {
                    "overall": {
                        "method_coverage": 0,
                        "activity_coverage": 0,
                        "mop_coverage": 0,
                        "method_calls": 0
                    },
                    "by_app": {},
                    "by_tool": {},
                    "tasks": {}
                }
                
                # Track cumulative metrics
                total_method_coverage = 0
                total_activity_coverage = 0
                total_mop_coverage = 0
                total_method_calls = 0
                completed_tasks = 0
                
                # List of all called methods
                all_called_methods: Set[str] = set()
                
                # Process each task
                for task in tasks:
                    # Skip tasks that haven't been executed
                    if not task.completed:
                        continue
                        
                    completed_tasks += 1
                    metrics = task.result.coverage_metrics
                    
                    # Update metrics by app
                    app_name = task.config.apk_name
                    if app_name not in coverage_data["by_app"]:
                        coverage_data["by_app"][app_name] = {
                            "tasks": 0,
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "method_calls": 0
                        }
                        
                    app_data = coverage_data["by_app"][app_name]
                    app_data["tasks"] += 1
                    app_data["method_coverage"] += metrics.get("method_coverage", 0)
                    app_data["activity_coverage"] += metrics.get("activities_coverage", 0)
                    app_data["mop_coverage"] += metrics.get("methods_jca_reachable_coverage", 0)
                    app_data["method_calls"] += metrics.get("total_method_calls", 0)
                    
                    # Update metrics by tool
                    tool_name = task.config.tool_name
                    if tool_name not in coverage_data["by_tool"]:
                        coverage_data["by_tool"][tool_name] = {
                            "tasks": 0,
                            "method_coverage": 0,
                            "activity_coverage": 0,
                            "mop_coverage": 0,
                            "method_calls": 0
                        }
                        
                    tool_data = coverage_data["by_tool"][tool_name]
                    tool_data["tasks"] += 1
                    tool_data["method_coverage"] += metrics.get("method_coverage", 0)
                    tool_data["activity_coverage"] += metrics.get("activities_coverage", 0)
                    tool_data["mop_coverage"] += metrics.get("methods_jca_reachable_coverage", 0)
                    tool_data["method_calls"] += metrics.get("total_method_calls", 0)
                    
                    # Update individual task data
                    task_key = f"{task.id}"
                    coverage_data["tasks"][task_key] = {
                        "app_name": app_name,
                        "tool_name": tool_name,
                        "repetition": task.config.repetition,
                        "timeout": task.config.timeout,
                        "method_coverage": metrics.get("method_coverage", 0),
                        "activity_coverage": metrics.get("activities_coverage", 0),
                        "mop_coverage": metrics.get("methods_jca_reachable_coverage", 0),
                        "method_calls": metrics.get("total_method_calls", 0),
                        "execution_time": task.result.execution_time_seconds
                    }
                    
                    # Update cumulative metrics
                    total_method_coverage += metrics.get("method_coverage", 0)
                    total_activity_coverage += metrics.get("activities_coverage", 0)
                    total_mop_coverage += metrics.get("methods_jca_reachable_coverage", 0)
                    total_method_calls += metrics.get("total_method_calls", 0)
                    
                    # Update called methods
                    if task.repository:
                        for method in task.repository.get_called_methods():
                            all_called_methods.add(method)
                            
                # Calculate averages for all metrics
                if completed_tasks > 0:
                    # Overall averages
                    coverage_data["overall"]["method_coverage"] = total_method_coverage / completed_tasks
                    coverage_data["overall"]["activity_coverage"] = total_activity_coverage / completed_tasks
                    coverage_data["overall"]["mop_coverage"] = total_mop_coverage / completed_tasks
                    coverage_data["overall"]["method_calls"] = total_method_calls
                    coverage_data["overall"]["unique_methods"] = len(all_called_methods)
                    
                    # App averages
                    for app_name, app_data in coverage_data["by_app"].items():
                        if app_data["tasks"] > 0:
                            app_data["method_coverage"] /= app_data["tasks"]
                            app_data["activity_coverage"] /= app_data["tasks"]
                            app_data["mop_coverage"] /= app_data["tasks"]
                            
                    # Tool averages
                    for tool_name, tool_data in coverage_data["by_tool"].items():
                        if tool_data["tasks"] > 0:
                            tool_data["method_coverage"] /= tool_data["tasks"]
                            tool_data["activity_coverage"] /= tool_data["tasks"]
                            tool_data["mop_coverage"] /= tool_data["tasks"]
                            
                # Save coverage data to file
                coverage_file = os.path.join(context.results_dir, "coverage_report.json")
                with open(coverage_file, 'w') as f:
                    json.dump(coverage_data, f, indent=2)
                    
                # Store coverage data in context
                context.set("analysis.coverage", coverage_data)
                
                # Publish coverage updated event
                self._event_bus.publish_analysis_event(
                    event_type=EventType.COVERAGE_UPDATED,
                    data={"report_path": coverage_file},
                    source="AnalysisProcessor",
                    channel=EventBus.ANALYSIS_CHANNEL
                )
                
                self.logger.info(LOG_COMPLETE.format(operation="coverage analysis"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="coverage analysis",
                    error=str(e)
                ))
                return False
                
    def _analyze_errors(self, tasks: List[Task], context: IExecutionContext) -> bool:
        """
        Analyze error data from tasks.
        
        Args:
            tasks: List of tasks to analyze
            context: Execution context
            
        Returns:
            True if analysis was successful, False otherwise
        """
        with self.logger.with_context(phase="error_analysis"):
            self.logger.info(LOG_START.format(operation="error analysis"))
            
            try:
                error_data = {
                    "overall": {
                        "total_errors": 0,
                        "error_types": {}
                    },
                    "by_app": {},
                    "by_tool": {},
                    "tasks": {}
                }
                
                # List of all unique errors
                all_errors: Set[str] = set()
                
                # Process each task
                for task in tasks:
                    # Skip tasks that haven't been executed
                    if not task.completed and not task.failed:
                        continue
                        
                    app_name = task.config.apk_name
                    tool_name = task.config.tool_name
                    
                    # Initialize app and tool data if needed
                    if app_name not in error_data["by_app"]:
                        error_data["by_app"][app_name] = {
                            "total_errors": 0,
                            "error_types": {}
                        }
                        
                    if tool_name not in error_data["by_tool"]:
                        error_data["by_tool"][tool_name] = {
                            "total_errors": 0,
                            "error_types": {}
                        }
                        
                    # Initialize task data
                    task_key = f"{task.id}"
                    error_data["tasks"][task_key] = {
                        "app_name": app_name,
                        "tool_name": tool_name,
                        "repetition": task.config.repetition,
                        "timeout": task.config.timeout,
                        "total_errors": 0,
                        "error_types": {},
                        "execution_error": task.result.error_message
                    }
                    
                    # Get errors from task repository
                    if task.repository:
                        errors = task.repository.get_errors()
                        
                        # Update task error data
                        task_data = error_data["tasks"][task_key]
                        task_data["total_errors"] = len(errors)
                        
                        # Process each error
                        for error in errors:
                            error_type = error.error_type
                            error_msg = error.error_message
                            
                            # Add to unique errors
                            error_key = f"{error_type}: {error_msg}"
                            all_errors.add(error_key)
                            
                            # Update error counts
                            error_data["overall"]["total_errors"] += 1
                            error_data["by_app"][app_name]["total_errors"] += 1
                            error_data["by_tool"][tool_name]["total_errors"] += 1
                            
                            # Update error type counts
                            if error_type not in error_data["overall"]["error_types"]:
                                error_data["overall"]["error_types"][error_type] = 0
                            error_data["overall"]["error_types"][error_type] += 1
                            
                            if error_type not in error_data["by_app"][app_name]["error_types"]:
                                error_data["by_app"][app_name]["error_types"][error_type] = 0
                            error_data["by_app"][app_name]["error_types"][error_type] += 1
                            
                            if error_type not in error_data["by_tool"][tool_name]["error_types"]:
                                error_data["by_tool"][tool_name]["error_types"][error_type] = 0
                            error_data["by_tool"][tool_name]["error_types"][error_type] += 1
                            
                            if error_type not in task_data["error_types"]:
                                task_data["error_types"][error_type] = 0
                            task_data["error_types"][error_type] += 1
                            
                # Save error data to file
                error_file = os.path.join(context.results_dir, "error_report.json")
                with open(error_file, 'w') as f:
                    json.dump(error_data, f, indent=2)
                    
                # Store error data in context
                context.set("analysis.errors", error_data)
                
                self.logger.info(LOG_COMPLETE.format(operation="error analysis"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="error analysis",
                    error=str(e)
                ))
                return False
                
    def _generate_summary(self, tasks: List[Task], context: IExecutionContext) -> bool:
        """
        Generate experiment summary.
        
        Args:
            tasks: List of tasks to analyze
            context: Execution context
            
        Returns:
            True if summary generation was successful, False otherwise
        """
        with self.logger.with_context(phase="summary_generation"):
            self.logger.info(LOG_START.format(operation="summary generation"))
            
            try:
                # Get coverage and error data
                coverage_data = context.get("analysis.coverage", {})
                error_data = context.get("analysis.errors", {})
                
                # Generate summary
                summary = {
                    "experiment_id": context.experiment_id,
                    "results_dir": context.results_dir,
                    "tasks": {
                        "total": len(tasks),
                        "completed": len([t for t in tasks if t.completed]),
                        "failed": len([t for t in tasks if t.failed]),
                        "pending": len([t for t in tasks if not t.completed and not t.failed])
                    },
                    "coverage": coverage_data.get("overall", {}),
                    "errors": error_data.get("overall", {}),
                    "apps": list(coverage_data.get("by_app", {}).keys()),
                    "tools": list(coverage_data.get("by_tool", {}).keys())
                }
                
                # Save summary to file
                summary_file = os.path.join(context.results_dir, "summary.json")
                with open(summary_file, 'w') as f:
                    json.dump(summary, f, indent=2)
                    
                # Store summary in context
                context.set("analysis.summary", summary)
                
                self.logger.info(LOG_COMPLETE.format(operation="summary generation"))
                return True
                
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="summary generation",
                    error=str(e)
                ))
                return False