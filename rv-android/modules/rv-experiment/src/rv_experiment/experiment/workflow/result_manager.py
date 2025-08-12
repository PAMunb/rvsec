# rv_experiment/experiment/workflow/result_manager.py
"""
Simplified result manager for RV-Android experiments.

This module provides minimal result management functionality focused
on experiment metadata and instrumentation error tracking.
"""

import json
import os
from typing import Dict, Any, List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_START,
    LOG_COMPLETE
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus
from rv_android_core.domain.task import TaskState
from rv_platform.storage.task_storage import TaskStorage


class ResultManager:
    """
    Simplified result manager for RV-Android experiments.
    
    This module provides minimal result management functionality focused
    on experiment metadata and instrumentation error tracking. CSV and JSON
    result processing has been moved to rv-platform for better separation
    of concerns.
    
    ### Architectural Role:
    - Generates instrumentation errors JSON file for debugging purposes
    - Provides basic experiment metadata tracking for logging
    - Maintains minimal orchestration responsibilities
    - Delegates complex data processing to rv-platform
    
    ### Key Capabilities:
    - Generate instrumentation errors JSON file if errors occurred
    - Create basic experiment metadata for logging and tracking
    - Integrate with experiment workflow for error reporting
    - Provide simple result summary for experiment completion
    
    ### Integration Points:
    - Uses ErrorHandler decorator for error processing
    - Uses LoggingManager for consistent logging with context support
    - Works with TaskStorage for accessing completed experiment tasks
    - Publishes basic experiment events through EventBus
    """

    def __init__(self, results_dir: str, task_storage: TaskStorage, event_bus: Optional[EventBus] = None):
        """
        Initialize the simplified result manager.

        Args:
            results_dir: Directory for storing experiment results
            task_storage: Task storage containing completed tasks
            event_bus: Optional event bus for publishing events
        """
        self.results_dir = results_dir
        self.task_storage = task_storage
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Initialize logging with context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.workflow.result_manager',
            {CONTEXT_COMPONENT: 'ResultManager'}
        )

        # Result processing state
        self.experiment_metadata: Dict[str, Any] = {}

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    @ErrorHandler.handle_errors(component="ResultManager", phase="result_generation")
    def generate_reports(self) -> None:
        """
        Generate basic experiment reports focused on instrumentation errors.
        
        This method creates the instrumentation errors JSON file and basic
        experiment metadata. CSV and JSON result processing is handled by
        rv-platform's ResultProcessorComponent.
        """
        with self.logger.with_context(phase="result_generation"):
            self.logger.info(LOG_START.format(phase="experiment result generation"))

            # Load completed tasks
            completed_tasks = self._load_completed_tasks()
            if not completed_tasks:
                self.logger.warning("No completed tasks found for result generation")
                return

            # Generate instrumentation errors JSON
            self._generate_instrument_errors_json(completed_tasks)

            # Create basic experiment metadata
            self._generate_experiment_metadata(completed_tasks)

            self.logger.info(LOG_COMPLETE.format(phase="experiment result generation"))

    @ErrorHandler.handle_errors(component="ResultManager", phase="task_loading")
    def _load_completed_tasks(self) -> List[Any]:
        """
        Load completed tasks from storage.
        
        Returns:
            List of completed tasks ready for processing
        """
        # Get all tasks and filter for completed ones
        all_tasks = self.task_storage.get_tasks()
        completed_tasks = [
            task for task in all_tasks
            if hasattr(task, 'result') and
               getattr(task.result, 'state', None) == TaskState.COMPLETED
        ]
        
        self.logger.info(f"Loaded {len(completed_tasks)} completed tasks out of {len(all_tasks)} total tasks")
        return completed_tasks

    @ErrorHandler.handle_errors(component="ResultManager", phase="instrument_errors_json_generation")
    def _generate_instrument_errors_json(self, completed_tasks: List[Any]) -> None:
        """
        Generate instrumentation errors JSON file if any errors occurred.
        
        Args:
            completed_tasks: List of completed tasks to process
        """
        with self.logger.with_context(phase="instrument_errors_json_generation"):
            self.logger.info(LOG_START.format(phase="instrumentation errors JSON generation"))

            # Collect instrumentation errors
            instrument_errors = {}
            
            for task in completed_tasks:
                if hasattr(task.result, 'instrument_errors') and task.result.instrument_errors:
                    apk_name = task.config.apk_name
                    instrument_errors[apk_name] = task.result.instrument_errors

            # Create file with errors or empty object
            errors_file = os.path.join(self.results_dir, "instrument_errors.json")
            
            with open(errors_file, 'w', encoding='utf-8') as f:
                json.dump(instrument_errors, f, indent=2, ensure_ascii=False)

            if instrument_errors:
                self.logger.info(f"Instrumentation errors JSON generated: {errors_file}")
            else:
                self.logger.info("No instrumentation errors found - empty file created")

    def _generate_experiment_metadata(self, completed_tasks: List[Any]) -> None:
        """
        Create basic experiment metadata for logging and tracking.
        
        Args:
            completed_tasks: List of completed tasks to summarize
        """
        try:
            from datetime import datetime
            
            # Calculate basic statistics
            total_tasks = len(completed_tasks)
            unique_apks = len(set(task.config.apk_name for task in completed_tasks))
            unique_tools = len(set(task.config.tool_config.get_full_tool_name() for task in completed_tasks))
            
            # Store metadata for logging
            self.experiment_metadata = {
                "total_tasks": total_tasks,
                "unique_apks": unique_apks,
                "unique_tools": unique_tools,
                "completion_time": datetime.now().isoformat()
            }
            
            self.logger.info(f"Experiment metadata: {total_tasks} tasks, {unique_apks} APKs, {unique_tools} tools")

        except Exception as e:
            self.logger.warning(f"Failed to create experiment metadata: {e}")

    def get_experiment_metadata(self) -> Dict[str, Any]:
        """
        Get the current experiment metadata.
        
        Returns:
            Dictionary with experiment metadata
        """
        return self.experiment_metadata.copy()