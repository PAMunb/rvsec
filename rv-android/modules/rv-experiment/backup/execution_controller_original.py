# rvandroid/experiment/workflow/execution_controller.py
"""
Execution controller for RV-Android experiments.
Manages task setup and execution during experiments.
"""
import os
import shutil
from typing import List, Dict, Any

from rv_android_core.app import App
from rv_android_core.constants import EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus
from rv_experiment.experiment.execution_manager import ExecutionManager
from rv_experiment.experiment.task.storage import TaskStorage
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.config import ExperimentConfig


class ExecutionController:
    """
    A focused controller for managing the execution phase of experiments.

    ### Architectural Decisions:
    - Separates execution concerns from the main experiment controller
    - Leverages the existing ExecutionManager for task management
    - Provides a clean interface for execution configuration and control
    - Encapsulates the logic for task setup and execution

    ### Role in the System:
    - Coordinates task execution during experiments
    - Manages tool and application registration
    - Ensures proper task configuration and execution
    - Handles static analysis file management for tasks
    """

    def __init__(self, task_storage: TaskStorage, config: ExperimentConfig, event_bus: EventBus):
        """
        Initialize the execution controller.

        Args:
            task_storage: Storage for experiment tasks
            config: Experiment configuration
            event_bus: Event bus for publishing events
        """
        self.task_storage = task_storage
        self.config = config
        self.event_bus = event_bus

        # Create execution manager
        self.execution_manager = ExecutionManager(task_storage, config, event_bus)

        # Configure logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.execution_controller',
            {
                CONTEXT_COMPONENT: 'ExecutionController'
            }
        )

        # Result tracking
        self.base_results_dir = os.path.dirname(self.task_storage.storage_file)
        self.has_errors = False

    def update_storage(self, task_storage: TaskStorage):
        """
        Update the task storage used by the execution controller.

        Args:
            task_storage: New task storage instance
        """
        self.task_storage = task_storage
        self.execution_manager = ExecutionManager(task_storage, self.event_bus)
        self.base_results_dir = os.path.dirname(self.task_storage.storage_file)

    def setup(self, apks: List[App], repetitions: int, timeouts: List[int],
              tools: List[AbstractTool], no_window: bool = False):
        """
        Set up experiment execution with the specified parameters.

        Args:
            apks: List of app objects to test
            repetitions: Number of repetitions for each task
            timeouts: List of timeout values
            tools: List of testing tools
            no_window: Whether to run without a window
        """
        with self.logger.with_context(
                repetitions=repetitions,
                timeouts=timeouts,
                tools=[tool.name for tool in tools],
                no_window=no_window,
                phase="setup"
        ):
            self.logger.info(LOG_START.format(phase="execution setup"))

            # Register apps and tools
            for app in apks:
                self.execution_manager.register_app(app)

            for tool in tools:
                self.execution_manager.register_tool(tool)

            # Set up tasks if needed
            if len(self.task_storage.get_tasks()) == 0:
                self.logger.info("Setting up new tasks for execution")
                self.execution_manager.setup_execution(
                    apks=apks,
                    repetitions=repetitions,
                    timeouts=timeouts,
                    tools=tools,
                    no_window=no_window
                )

            self.logger.info(LOG_COMPLETE.format(phase="execution setup"))

    def run(self) -> bool:
        """
        Run all experiment tasks.

        Returns:
            True if all tasks completed successfully, False if there were errors
        """
        with self.logger.with_context(phase="execution"):
            self.logger.info(LOG_START.format(phase="task execution"))

            # Run all tasks
            result = self.execution_manager.run_all_tasks()
            self.has_errors = not result

            # Log statistics
            stats = self.execution_manager.get_statistics()
            self.logger.info(f"Execution statistics: {stats}")

            self.logger.info(LOG_COMPLETE.format(phase="task execution"))
            return result

    def copy_static_analysis_files(self, apk: str, app_results_dir: str) -> bool:
        """
        Copy static analysis files for an app to its results directory.

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
                file_path = os.path.join(self.config.get_instrumented_dir(), file_name)

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
                "component": "ExecutionController",
                "phase": "static_analysis_file_copy",
                "apk_name": apk,
                "target_directory": app_results_dir,
                "extensions_checked": extensions,
                "copied_files_count": copied_files
            }

            # Use ErrorHandler for proper exception handling
            self.error_handler.handle_error(e, error_context)

            # Log additional information
            self.logger.error(LOG_ERROR.format(
                phase=f"copying static analysis files for {apk}",
                error=str(e)
            ))
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution statistics
        """
        return self.execution_manager.get_statistics()

    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get a coverage report for the executed tasks.

        Returns:
            Dictionary with coverage report
        """
        return self.execution_manager.get_coverage_report()
