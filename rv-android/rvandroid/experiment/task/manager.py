# rvandroid/experiment/task/manager.py
"""
Task execution manager for coordinating and executing tasks.

This module provides a high-level manager for task execution, handling task
creation, scheduling, and execution tracking. It integrates with the task
storage system for persistence and the event system for notifications.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from rvandroid.app import App
from rvandroid.constants import EXTENSION_REACH, EXTENSION_GATOR, EXTENSION_GESDA, EXTENSION_METHODS
from rvandroid.experiment.event import (
    EventBus,
    get_event_bus,
    EventType
)
from rvandroid.experiment.task.component import ComponentRegistry
from rvandroid.experiment.task.components.adapter import create_legacy_component_adapters
from rvandroid.experiment.task.executor import TaskExecutor
from rvandroid.experiment.task.interfaces import TaskState, ITask
from rvandroid.experiment.task.task_model import Task, TaskConfiguration, TaskFactory
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.logging.manager import LoggingManager
from settings import INSTRUMENTED_DIR


class TaskManager:
    """
    Manages task creation, coordination, and execution tracking.
    
    ### Architectural Decisions:
    - Implements a centralized task management system
    - Supports flexible task scheduling and execution
    - Integrates with the event system for notifications
    - Provides comprehensive tracking and reporting
    
    ### Role in the System:
    - Coordinates the creation and execution of tasks
    - Manages task dependencies and execution order
    - Tracks task execution progress and results
    - Provides reporting and analysis of task outcomes
    """
    
    def __init__(self, 
                storage: TaskStorage, 
                event_bus: Optional[EventBus] = None,
                base_results_dir: Optional[str] = None):
        """
        Initialize the task manager.
        
        Args:
            storage: Task storage for persistence
            event_bus: Optional event bus for notifications
            base_results_dir: Optional base directory for results
        """
        self.storage = storage
        self.event_bus = event_bus or get_event_bus()
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger('experiment.task_manager')
        
        # Tool and app registries
        self.tools: Dict[str, AbstractTool] = {}
        self.apks: Dict[str, App] = {}
        
        # Results directory
        self.base_results_dir = base_results_dir or os.path.dirname(self.storage.storage_file)
        
        # Execution state
        self.is_running = False
        self.current_task: Optional[ITask] = None
        self.running_timestamp: Optional[datetime] = None
        
        # Track executed and failed tasks
        self.executed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
    def register_tool(self, tool: AbstractTool) -> None:
        """
        Register a tool with the manager.
        
        Args:
            tool: Tool implementation
        """
        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")
        
    def register_app(self, app: App) -> None:
        """
        Register an app with the manager.
        
        Args:
            app: App instance
        """
        self.apks[app.name] = app
        self.logger.debug(f"Registered app: {app.name}")
        
    def setup_execution(self, 
                       apks: List[App],
                       repetitions: int,
                       timeouts: List[int],
                       tools: List[AbstractTool],
                       **kwargs) -> None:
        """
        Set up tasks for execution.
        
        Generate tasks for each combination of app, repetition, timeout, and tool.
        
        Args:
            apks: List of apps to test
            repetitions: Number of repetitions
            timeouts: List of timeout values
            tools: List of tools to use
            **kwargs: Additional task configuration options
        """
        self.logger.info("Setting up execution")
        
        # Register apps and tools
        for app in apks:
            self.register_app(app)
            
        for tool in tools:
            self.register_tool(tool)
            
        # Begin transaction for batch updates
        self.storage.begin_transaction()
        
        try:
            # Create tasks
            created_count = 0
            factory = TaskFactory(Task)
            
            for app in apks:
                for rep in range(1, repetitions + 1):
                    for timeout in timeouts:
                        for tool in tools:
                            # Create task configuration
                            config = TaskConfiguration(
                                apk_name=app.name,
                                repetition=rep,
                                timeout=timeout,
                                tool_name=tool.name,
                                **kwargs
                            )
                            
                            # Create and register task
                            task = factory.create_task(config)
                            task.initialize(self.base_results_dir)
                            task.set_app(app)
                            
                            # Add to storage
                            self.storage.add_task(task)
                            created_count += 1
                            
            # Commit transaction
            self.storage.commit_transaction()
            self.logger.info(f"Created {created_count} tasks")
            
        except Exception as e:
            self.logger.error(f"Error creating tasks: {e}")
            self.storage.rollback_transaction()
            raise
            
    def run_all_tasks(self) -> bool:
        """
        Execute all pending tasks.
        
        Returns:
            True if all tasks completed successfully, False otherwise
        """
        if self.is_running:
            self.logger.warning("Execution already in progress")
            return False
            
        self.is_running = True
        self.running_timestamp = datetime.now()
        has_errors = False
        
        # Reset tracking sets
        self.executed_tasks = set()
        self.failed_tasks = set()
        
        # Publish experiment started event
        experiment_id = f"experiment-{self.running_timestamp.strftime('%Y%m%d%H%M%S')}"
        self.event_bus.publish_experiment_event(
            event_type=EventType.EXPERIMENT_STARTED,
            experiment_id=experiment_id,
            details={"message": "Starting execution of tasks"},
            source="TaskManager",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
        try:
            # Get pending tasks
            tasks = self.storage.get_pending_tasks()
            ready_tasks = [t for t in tasks if t.can_execute]
            self.logger.info(f"Starting execution of {len(ready_tasks)} tasks")
            
            # Execute each task
            for task in ready_tasks:
                result = self.run_task(task)
                if not result:
                    has_errors = True
                    
            # Publish experiment completed event
            event_type = EventType.EXPERIMENT_COMPLETED if not has_errors else EventType.EXPERIMENT_FAILED
            self.event_bus.publish_experiment_event(
                event_type=event_type,
                experiment_id=experiment_id,
                details={
                    "message": f"Execution completed {'with errors' if has_errors else 'successfully'}",
                    "completed_tasks": len(self.executed_tasks),
                    "failed_tasks": len(self.failed_tasks)
                },
                source="TaskManager",
                channel=EventBus.LIFECYCLE_CHANNEL
            )
            
            self.logger.info("Execution completed")
            return not has_errors
            
        finally:
            self.is_running = False
            self.current_task = None
            
    def run_task(self, task: ITask) -> bool:
        """
        Execute a single task.
        
        Args:
            task: Task to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        self.logger.info(f"Running task {task.id}: {task.config}")
        self.current_task = task
        
        # Get tool
        tool = self.tools.get(task.config.tool_name)
        if not tool:
            self.logger.error(f"Tool not found: {task.config.tool_name}")
            task.update_state(TaskState.ERROR, f"Tool not found: {task.config.tool_name}")
            self.storage.update_task(task)
            self.failed_tasks.add(task.id)
            return False
            
        # Get app
        app = self.apks.get(task.config.apk_name)
        if not app:
            self.logger.error(f"App not found: {task.config.apk_name}")
            task.update_state(TaskState.ERROR, f"App not found: {task.config.apk_name}")
            self.storage.update_task(task)
            self.failed_tasks.add(task.id)
            return False
            
        # Ensure app is set
        task.set_app(app)
        
        # Copy static analysis files
        self.copy_static_analysis_files(task.app.name, task.results_dir)
        
        try:
            # Create executor
            executor = TaskExecutor(task, tool, self.event_bus)
            
            # Create and register legacy component adapters
            adapters = create_legacy_component_adapters(task, tool, self.event_bus)
            for adapter in adapters.values():
                executor.register_component(adapter)
                
            # Execute task
            success = executor.execute()
            
            # Update tracking
            if success:
                self.executed_tasks.add(task.id)
            else:
                self.failed_tasks.add(task.id)
                
            # Update task in storage
            self.storage.update_task(task)
            return success
            
        except Exception as e:
            self.logger.error(f"Error executing task {task.id}: {e}")
            task.update_state(TaskState.ERROR, str(e))
            self.storage.update_task(task)
            self.failed_tasks.add(task.id)
            return False
            
    def copy_static_analysis_files(self, apk: str, app_results_dir: str) -> bool:
        """
        Copy static analysis files for an app to results directory.
        
        Args:
            apk: App identifier
            app_results_dir: Target directory for files
            
        Returns:
            True if at least one file was copied, False otherwise
        """
        self.logger.info(f"Copying static analysis files for {apk} to {app_results_dir}")
        extensions = [EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]
        copied_files = 0
        
        try:
            # Ensure the target directory exists
            os.makedirs(app_results_dir, exist_ok=True)
            
            for extension in extensions:
                file_name = f"{apk}{extension}"
                file_path = os.path.join(INSTRUMENTED_DIR, file_name)
                self.logger.debug(f"Checking file: {file_path}")
                
                if os.path.exists(file_path):
                    self.logger.debug(f"Copying {file_path} to {app_results_dir}")
                    shutil.copy(file_path, app_results_dir)
                    copied_files += 1
                    
            if copied_files == 0:
                self.logger.warning(f"No static analysis files found for {apk}")
                return False
                
            self.logger.info(f"Successfully copied {copied_files} static analysis files for {apk}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error copying static analysis files for {apk}: {e}")
            return False
            
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Returns:
            Statistics dictionary
        """
        tasks = self.storage.get_tasks()
        total = len(tasks)
        
        completed = len([t for t in tasks if t.result.state == TaskState.COMPLETED])
        failed = len([t for t in tasks if t.result.state == TaskState.ERROR])
        pending = total - completed - failed
        
        pct_complete = (completed * 100 / total) if total > 0 else 0
        
        if self.running_timestamp:
            elapsed = (datetime.now() - self.running_timestamp).total_seconds()
            elapsed_str = self._format_time(elapsed)
        else:
            elapsed_str = "0s"
            
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "pct_complete": round(pct_complete, 2),
            "current_task": str(self.current_task) if self.current_task else None,
            "running": self.is_running,
            "elapsed": elapsed_str
        }
        
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Generate a coverage report for all executed tasks.
        
        Returns:
            Coverage report dictionary
        """
        report = {
            "tasks": {},
            "summary": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "avg_method_coverage": 0,
                "avg_activities_coverage": 0,
                "avg_mop_coverage": 0,
                "total_errors": 0
            }
        }
        
        # Get completed tasks
        completed_tasks = self.storage.get_tasks_by_state(TaskState.COMPLETED)
        
        if not completed_tasks:
            return report
            
        # Update summary counts
        report["summary"]["total_tasks"] = len(self.storage.get_tasks())
        report["summary"]["completed_tasks"] = len(completed_tasks)
        
        # Calculate totals for averages
        total_method_coverage = 0
        total_activities_coverage = 0
        total_mop_coverage = 0
        total_errors = 0
        
        # Process each task
        for task in completed_tasks:
            # Refresh repository data if available
            if hasattr(task, 'repository') and task.repository:
                # Get metrics directly from the repository
                metrics = task.repository.calculate_metrics()
                metrics_dict = metrics.to_dict()
                
                # Ensure result metrics are up to date
                task.result.coverage_metrics.update({
                    "method_coverage": metrics_dict["method_coverage"],
                    "activities_coverage": metrics_dict["activity_coverage"],
                    "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
                    "total_errors": metrics_dict["unique_errors"],
                    "total_method_calls": metrics_dict["called_methods"]
                })
                
            # Use metrics from task.result
            metrics = task.result.coverage_metrics
            
            # Add to task report
            key = f"{task.config.apk_name}_{task.config.tool_name}_{task.config.repetition}_{task.config.timeout}"
            report["tasks"][key] = {
                "apk_name": task.config.apk_name,
                "tool_name": task.config.tool_name,
                "repetition": task.config.repetition,
                "timeout": task.config.timeout,
                "method_coverage": metrics.get("method_coverage", 0),
                "activities_coverage": metrics.get("activities_coverage", 0),
                "mop_coverage": metrics.get("methods_jca_reachable_coverage", 0),
                "errors": metrics.get("total_errors", 0),
                "method_calls": metrics.get("total_method_calls", 0),
                "execution_time": task.result.execution_time_seconds
            }
            
            # Update totals
            total_method_coverage += metrics.get("method_coverage", 0)
            total_activities_coverage += metrics.get("activities_coverage", 0)
            total_mop_coverage += metrics.get("methods_jca_reachable_coverage", 0)
            total_errors += metrics.get("total_errors", 0)
            
        # Calculate averages
        task_count = len(report["tasks"])
        if task_count > 0:
            report["summary"]["avg_method_coverage"] = total_method_coverage / task_count
            report["summary"]["avg_activities_coverage"] = total_activities_coverage / task_count
            report["summary"]["avg_mop_coverage"] = total_mop_coverage / task_count
            report["summary"]["total_errors"] = total_errors
            
        return report
        
    @staticmethod
    def _format_time(seconds: int) -> str:
        """
        Format time in seconds to human-readable string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds}s"
            
        minutes = seconds // 60
        seconds = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {seconds}s"
            
        hours = minutes // 60
        minutes = minutes % 60
        
        return f"{hours}h {minutes}m {seconds}s"