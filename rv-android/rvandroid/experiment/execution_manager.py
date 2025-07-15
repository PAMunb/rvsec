# rvandroid/experiment/execution_manager.py
"""
Execution manager for coordinating tasks.
Provides dependency injection and event-based execution coordination.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional

from rvandroid.app import App
from rvandroid.constants import EXTENSION_REACH, EXTENSION_GATOR, EXTENSION_GESDA, EXTENSION_METHODS
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.executor import TaskExecutor
from rvandroid.experiment.task.components import (
    StaticAnalysisComponent,
    CoverageComponent,
    EmulatorComponent,
    LogcatComponent,
    ToolExecutionComponent
)
from rvandroid.experiment.task.task_model import Task, TaskConfiguration
from rvandroid.experiment.task.interfaces import TaskState
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.error.error_handler import ErrorHandler
from settings import INSTRUMENTED_DIR


class ExecutionManager:
    """
    A sophisticated orchestration system for managing and coordinating the execution of complex experimental tasks.

    ### Architectural Decisions:
    - Implements a centralized task management and execution control mechanism
    - Supports flexible task scheduling and tracking
    - Provides comprehensive state management for experimental tasks
    - Enables dynamic task registration and execution strategies

    ### Role in the System:
    - Acts as the primary controller for experiment task lifecycle management
    - Coordinates the execution flow of multiple tasks across different applications and tools
    - Manages task storage, retrieval, and state tracking
    - Generates comprehensive coverage and performance reports
    - Supports experiment resumption and stateful execution

    ### Key Considerations:
    - Handles complex task configuration and execution scenarios
    - Provides robust error handling and task state management
    - Supports parallel and sequential task execution strategies
    - Enables detailed performance and coverage metrics collection
    - Manages task dependencies and execution constraints

    ### Integration Strategy:
    - Seamlessly integrates with task storage, event systems, and reporting mechanisms
    - Compatible with multiple testing tools and experimental configurations
    - Supports dynamic tool and application registration
    - Provides flexible configuration through dependency injection
    - Enables comprehensive experiment state tracking

    ### Performance and Scalability:
    - Designed for efficient task management across diverse experimental scenarios
    - Supports large-scale experiment execution with minimal overhead
    - Implements optimized task tracking and reporting mechanisms
    - Adaptable to different complexity levels of experimental workflows
    - Provides granular performance metrics and execution insights
    """

    def __init__(self, storage: TaskStorage, event_bus: Optional[EventBus] = None):
        """
        Initialize with storage.

        Args:
            storage: Task storage instance
            event_bus: Optional event bus for notifications
        """
        self.storage = storage
        self.event_bus = event_bus or EventBus.get_instance()
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler.get_instance()
        self.tools: Dict[str, AbstractTool] = {}
        self.apks: Dict[str, App] = {}
        self.base_results_dir = os.path.dirname(self.storage.storage_file)
        self.is_running = False
        self.current_task: Optional[Task] = None
        self.running_timestamp = None

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

    def setup_execution(self, apks: List[App],
                        repetitions: int,
                        timeouts: List[int],
                        tools: List[AbstractTool],
                        **kwargs) -> None:
        """
        Set up tasks for execution.
        Generate tasks for each combination of app, repetition, timeout, and tool.

        For each app, this method creates tasks with different configurations
        by iterating through repetitions, timeouts, and tools. Each task is
        initialized with a specific configuration, added to storage, and tracked.
        After creating all tasks, they are saved to storage and a log message
        is generated with the total number of tasks created.

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

        # Create tasks
        created_count = 0
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
                        task = Task(config)
                        task.initialize(self.base_results_dir)
                        task.set_app(app)

                        # Add to storage
                        self.storage.add_task(task)
                        created_count += 1

        # Save tasks to storage
        self.storage.save()
        self.logger.info(f"Created {created_count} tasks")

    def run_all_tasks(self) -> bool:
        """
        Execute all pending tasks in the experiment, tracking overall experiment status.

        Manages task execution lifecycle, including:
        - Preventing concurrent executions
        - Publishing experiment start and completion events
        - Tracking task execution errors
        - Logging execution progress

        Returns:
            bool: True if all tasks complete without errors, False otherwise
        """
        if self.is_running:
            self.logger.warning("Execution already in progress")
            return False

        self.is_running = True
        self.running_timestamp = datetime.now()
        has_errors = False

        # Publish experiment started event
        self.event_bus.publish_experiment_event(
            EventType.EXPERIMENT_STARTED,
            experiment_id=f"experiment-{self.running_timestamp.strftime('%Y%m%d%H%M%S')}",
            message=f"Starting execution of tasks",
            source="ExecutionManager"
        )

        try:
            # Get pending tasks
            tasks = self.storage.get_pending_tasks()
            completed_tasks = self.storage.get_completed_tasks()
            
            self.logger.info(f"EXPERIMENT STATUS: Starting execution of {len(tasks)} pending tasks")
            self.logger.info(f"EXPERIMENT STATUS: {len(completed_tasks)} tasks already completed")
            self.logger.info(f"EXPERIMENT STATUS: Total tasks in experiment: {len(tasks) + len(completed_tasks)}")

            # Execute each task with detailed status logging
            for i, task in enumerate(tasks, 1):
                self.logger.info(f"EXPERIMENT STATUS: Executing task {i}/{len(tasks)} (Total progress: {len(completed_tasks) + i - 1}/{len(tasks) + len(completed_tasks)})")
                self.logger.info(f"EXPERIMENT STATUS: Remaining tasks: {len(tasks) - i}")
                
                result = self.run_task(task)
                if not result:
                    has_errors = True
                    self.logger.error(f"EXPERIMENT STATUS: Task {i}/{len(tasks)} FAILED: {task.config}")
                else:
                    self.logger.info(f"EXPERIMENT STATUS: Task {i}/{len(tasks)} COMPLETED successfully: {task.config}")
                
                # Update completed count for progress tracking
                completed_count = len(completed_tasks) + i
                total_count = len(tasks) + len(completed_tasks)
                progress_pct = (completed_count / total_count) * 100
                self.logger.info(f"EXPERIMENT STATUS: Overall progress: {completed_count}/{total_count} ({progress_pct:.1f}%)")
                
                if i < len(tasks):  # Not the last task
                    self.logger.info(f"EXPERIMENT STATUS: Proceeding to next task...")
                    self.logger.info("=" * 80)

            # Publish experiment completed event
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_COMPLETED if not has_errors else EventType.EXPERIMENT_FAILED,
                experiment_id=f"experiment-{self.running_timestamp.strftime('%Y%m%d%H%M%S')}",
                message=f"Execution completed {'with errors' if has_errors else 'successfully'}",
                source="ExecutionManager"
            )

            self.logger.info("Execution completed")
            return not has_errors

        except Exception as e:
            # Create comprehensive error context for the error handler
            error_context = {
                "component": "ExecutionManager",
                "phase": "experiment_execution",
                "total_tasks": len(tasks) if 'tasks' in locals() else 0,
                "completed_tasks": len(completed_tasks) if 'completed_tasks' in locals() else 0,
                "current_task_index": i if 'i' in locals() else 0,
                "experiment_timestamp": self.running_timestamp.isoformat() if self.running_timestamp else None,
                "base_results_dir": self.base_results_dir
            }
            
            # Add current task info if available
            if self.current_task:
                error_context["current_task_id"] = self.current_task.id
                error_context["current_task_config"] = self.current_task.config.to_dict()
            
            # Use ErrorHandler for proper exception handling
            self.error_handler.handle_error(e, error_context)
            
            # Log experiment-level exception
            self.logger.error(f"EXPERIMENT EXCEPTION: Experiment execution failed with exception")
            self.logger.error(f"EXPERIMENT EXCEPTION: Exception type: {type(e).__name__}")
            self.logger.error(f"EXPERIMENT EXCEPTION: Exception message: {str(e)}")
            
            # Publish experiment failed event
            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_FAILED,
                experiment_id=f"experiment-{self.running_timestamp.strftime('%Y%m%d%H%M%S')}" if self.running_timestamp else "experiment-unknown",
                message=f"Experiment failed with exception: {str(e)}",
                source="ExecutionManager"
            )
            
            return False

        finally:
            self.is_running = False
            self.current_task = None

    def run_task(self, task: Task) -> bool:
        """
        Execute a single task by resolving its tool and app, copying static analysis files, and running the task.

        Attempts to retrieve the specified tool and app for the task. If either is not found,
        the task is marked with an error and not executed. If both are found, the task is set up
        with the app, static analysis files are copied, and the task is executed via a TaskExecutor.

        Args:
            task (Task): The task to be executed.

        Returns:
            bool: True if the task was executed successfully, False if the task failed due to
                  missing tool/app or encountered an error during execution.
        """
        # Detailed task start logging
        self.logger.info("=" * 80)
        self.logger.info(f"TASK START: {task.id}")
        self.logger.info(f"TASK CONFIG: APK={task.config.apk_name}, Tool={task.config.tool_name}")
        self.logger.info(f"TASK CONFIG: Repetition={task.config.repetition}, Timeout={task.config.timeout}s")
        self.logger.info(f"TASK CONFIG: Device={task.config.device_id}, No-window={task.config.no_window}")
        self.logger.info(f"TASK CONFIG: Clean-logcat={task.config.clean_logcat}, Skip-install={task.config.skip_installation}")
        self.logger.info(f"TASK STATE: Current state = {task.result.state.name}")
        
        # Log task timing info
        if task.result.start_time:
            self.logger.info(f"TASK TIMING: Task started at {task.result.start_time}")
        else:
            task.result.start_time = datetime.now()
            self.logger.info(f"TASK TIMING: Setting task start time to {task.result.start_time}")
        
        # Log results directory
        self.logger.info(f"TASK OUTPUT: Results will be saved to {task.results_dir}")
        self.logger.info(f"TASK OUTPUT: Logcat file: {task.result.logcat_file}")
        self.logger.info(f"TASK OUTPUT: Trace file: {task.result.trace_file}")
        
        self.logger.info("=" * 80)
        
        self.current_task = task

        # Get tool with detailed logging
        self.logger.info(f"TASK RESOLUTION: Looking for tool '{task.config.tool_name}'")
        tool = self.tools.get(task.config.tool_name)
        if not tool:
            available_tools = list(self.tools.keys())
            self.logger.error(f"TASK ERROR: Tool '{task.config.tool_name}' not found")
            self.logger.error(f"TASK ERROR: Available tools: {available_tools}")
            task.update_state(TaskState.ERROR, f"Tool not found: {task.config.tool_name}")
            self.storage.update_task(task)
            return False
        self.logger.info(f"TASK RESOLUTION: Tool '{task.config.tool_name}' found successfully")

        # Get app with detailed logging
        self.logger.info(f"TASK RESOLUTION: Looking for app '{task.config.apk_name}'")
        app = self.apks.get(task.config.apk_name)
        if not app:
            available_apps = list(self.apks.keys())
            self.logger.error(f"TASK ERROR: App '{task.config.apk_name}' not found")
            self.logger.error(f"TASK ERROR: Available apps: {available_apps}")
            task.update_state(TaskState.ERROR, f"App not found: {task.config.apk_name}")
            self.storage.update_task(task)
            return False
        self.logger.info(f"TASK RESOLUTION: App '{task.config.apk_name}' found successfully")
        self.logger.info(f"TASK RESOLUTION: App path: {app.instrumented_path if hasattr(app, 'instrumented_path') else 'N/A'}")
        self.logger.info(f"TASK RESOLUTION: App package: {app.package if hasattr(app, 'package') else 'N/A'}")
        self.logger.info(f"TASK RESOLUTION: App size: {app.size_mb if hasattr(app, 'size_mb') else 'N/A'} MB")

        # Ensure app is set
        self.logger.info(f"TASK SETUP: Setting app for task")
        task.set_app(app)

        # Copy static analysis files
        self.logger.info(f"TASK SETUP: Copying static analysis files to {task.results_dir}")
        self.copy_static_analysis_files(task.app.name, task.results_dir)

        try:
            # Create executor with required components
            self.logger.info(f"TASK EXECUTION: Creating TaskExecutor with tool '{tool.name}'")
            executor = TaskExecutor(task, tool, self.event_bus)
            
            # Register necessary components for task execution
            components = [
                ('StaticAnalysisComponent', StaticAnalysisComponent(task, self.event_bus)),
                ('CoverageComponent', CoverageComponent(task, self.event_bus)),
                ('EmulatorComponent', EmulatorComponent(task, self.event_bus)),
                ('LogcatComponent', LogcatComponent(task, self.event_bus)),
                ('ToolExecutionComponent', ToolExecutionComponent(task, tool, self.event_bus))
            ]
            
            self.logger.info(f"TASK EXECUTION: Registering {len(components)} components")
            for component_name, component in components:
                executor.register_component(component)
                self.logger.debug(f"TASK EXECUTION: Registered {component_name}")
            
            # Execute task
            self.logger.info(f"TASK EXECUTION: Starting task execution")
            task_start_time = datetime.now()
            success = executor.execute()
            task_end_time = datetime.now()
            
            execution_duration = (task_end_time - task_start_time).total_seconds()
            
            if success:
                self.logger.info(f"TASK RESULT: Task completed successfully in {execution_duration:.2f} seconds")
                if hasattr(task.result, 'coverage_metrics') and task.result.coverage_metrics:
                    metrics = task.result.coverage_metrics
                    self.logger.info(f"TASK METRICS: Method coverage: {metrics.get('method_coverage', 0):.2f}%")
                    self.logger.info(f"TASK METRICS: Activity coverage: {metrics.get('activities_coverage', 0):.2f}%")
                    self.logger.info(f"TASK METRICS: Total errors: {metrics.get('total_errors', 0)}")
            else:
                self.logger.error(f"TASK RESULT: Task failed after {execution_duration:.2f} seconds")
                if task.result.error_message:
                    self.logger.error(f"TASK ERROR: {task.result.error_message}")

            # Update task in storage
            self.logger.info(f"TASK FINALIZATION: Updating task in storage")
            self.storage.update_task(task)
            return success

        except Exception as e:
            execution_duration = (datetime.now() - task_start_time).total_seconds() if 'task_start_time' in locals() else 0
            
            # Create comprehensive error context for the error handler
            error_context = {
                "component": "ExecutionManager",
                "phase": "task_execution", 
                "task_id": task.id,
                "task_config": task.config.to_dict(),
                "execution_duration": execution_duration,
                "app_name": task.config.apk_name,
                "tool_name": task.config.tool_name,
                "current_state": task.result.state.name,
                "results_dir": task.results_dir
            }
            
            # Use ErrorHandler for proper exception handling
            self.error_handler.handle_error(e, error_context)
            
            # Log additional task-specific information
            self.logger.error(f"TASK EXCEPTION: Task {task.id} failed with exception after {execution_duration:.2f} seconds")
            self.logger.error(f"TASK EXCEPTION: Exception type: {type(e).__name__}")
            self.logger.error(f"TASK EXCEPTION: Exception message: {str(e)}")
            self.logger.error(f"TASK EXCEPTION: Task config: {task.config}")
            
            task.update_state(TaskState.ERROR, str(e))
            self.storage.update_task(task)
            return False
        
        finally:
            # Cleanup logging
            self.logger.info(f"TASK CLEANUP: Task {task.id} finished, setting current_task to None")
            self.current_task = None

    def copy_static_analysis_files(self, apk: str, app_results_dir: str) -> bool:
        """
        Copies static analysis files for an app to results directory.

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
            # Create error context for the error handler
            error_context = {
                "component": "ExecutionManager",
                "phase": "static_analysis_file_copy",
                "apk_name": apk,
                "target_directory": app_results_dir,
                "extensions_checked": extensions,
                "copied_files_count": copied_files
            }
            
            # Use ErrorHandler for proper exception handling
            self.error_handler.handle_error(e, error_context)
            
            # Log additional information
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
        Generate a coverage report for all executed tasks using standardized repository model.

        This method generates a comprehensive coverage report based on the
        LogcatRepository data stored in each task, ensuring consistent
        data representation across the system.

        Returns:
            Dictionary with coverage report data
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
        completed_tasks = [t for t in self.storage.get_tasks() if t.result.state == TaskState.COMPLETED]

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
            # Get standardized metrics from task's repository if available
            if hasattr(task, 'repository') and task.repository:
                # Get metrics directly from the repository - source of truth
                metrics = task.repository.calculate_metrics().to_dict()

                # Use these metrics instead of potentially inconsistent ones in result
                task.result.coverage_metrics.update({
                    "method_coverage": metrics["method_coverage"],
                    "activities_coverage": metrics["activity_coverage"],
                    "mop_coverage": metrics["mop_method_coverage"],
                    "total_errors": metrics["unique_errors"],
                    "total_method_calls": metrics["called_methods"]
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
