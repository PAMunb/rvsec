# rvandroid/experiment/workflow/result_manager.py
"""
Consolidated result manager for RV-Android experiments.

This module provides comprehensive result management functionality, including
data export to CSV and JSON formats, and basic reporting capabilities.
It consolidates the functionality from multiple result managers into a
unified, streamlined component.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_START,
    LOG_COMPLETE,
    LOG_ERROR
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus, EventType
# Import TaskState from rv-platform execution model (the one actually used in task serialization)
# Import TaskStorage from rv-platform where it now resides
from rv_android_core.domain.task import TaskState
from rv_platform.storage.task_storage import TaskStorage


class ResultManager:
    """
    Experiment coordination manager for rv-android experiments.
    
    Provides experiment-level coordination and interfaces for result analysis
    while delegating data processing responsibilities to rv-platform components.
    
    ### Architectural Role:
    - Coordinates experiment-level result management
    - Provides interfaces for result analysis capabilities
    - Manages experiment metadata and summaries
    - Maintains separation between experiment orchestration and data processing
    
    ### Capabilities:
    - Coordinate with rv-platform for data processing (CSV/JSON generation, logcat processing)
    - Generate experiment metadata and summaries
    - Provide interfaces for result analysis
    - Manage experiment completion events
    
    ### Integration Points:
    - Uses ErrorHandler decorator for error processing
    - Coordinates with rv-platform for data processing (CSV/JSON generation, logcat processing)
    - Uses TaskStorage from rv-platform for task coordination
    - Integrates with PostProcessor for experiment-level tasks
    - Integrates with LoggingManager for consistent logging
    - Uses EventBus for experiment completion notifications
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

        # Experiment coordination state
        self.coordinated_tasks: Dict[str, bool] = {}
        self.experiment_metadata: Dict[str, Any] = {}

        # Ensure results directory exists
        os.makedirs(results_dir, exist_ok=True)

    def generate_reports(self) -> None:
        """
        Generate experiment reports and coordinate with rv-platform for result processing.
        
        This method focuses on experiment-level coordination and delegates
        data processing responsibilities to rv-platform components.
        """
        with self.logger.with_context(phase="result_coordination"):
            self.logger.info(LOG_START.format(phase="experiment result coordination"))

            try:
                # Get experiment metadata (not processed task data)
                metadata = self._get_experiment_metadata()
                if metadata.get("completed_tasks", 0) == 0:
                    self.logger.warning("No completed tasks found for result coordination")
                    return

                # Handle experiment-level responsibilities
                self._generate_experiment_summary(metadata)
                
                # Coordinate with rv-platform for data processing
                # rv-platform handles CSV generation and logcat processing
                self._coordinate_result_processing(metadata)

                self.logger.info(LOG_COMPLETE.format(phase="experiment result coordination"))

                # Publish completion event
                self._publish_completion_event(metadata.get("completed_tasks", 0))

            except Exception as e:
                self.error_handler.handle_error(e, {"component": "ResultManager", "phase": "result_coordination"})
                self.logger.error(LOG_ERROR.format(
                    phase="coordinating experiment results",
                    error=str(e)
                ))


    def _get_experiment_metadata(self) -> Dict[str, Any]:
        """
        Get experiment-level metadata and summary information.
        
        Returns:
            Dictionary with experiment metadata (not processed task data)
        """
        try:
            # Get basic task count from storage (experiment-level info)
            all_tasks = self.task_storage.get_tasks()
            completed_count = sum(1 for task in all_tasks 
                                if hasattr(task, 'result') and 
                                   getattr(task.result, 'state', None) == TaskState.COMPLETED)

            self.logger.info(f"Experiment metadata: {completed_count} completed tasks out of {len(all_tasks)} total")
            
            return {
                "total_tasks": len(all_tasks),
                "completed_tasks": completed_count,
                "completion_rate": completed_count / len(all_tasks) if all_tasks else 0,
                "experiment_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(LOG_ERROR.format(
                phase="getting experiment metadata",
                error=str(e)
            ))
            return {}

    def _coordinate_result_processing(self, metadata: Dict[str, Any]) -> None:
        """
        Coordinate with rv-platform for data processing.
        
        Args:
            metadata: Experiment metadata for coordination
        """
        with self.logger.with_context(phase="result_processing_coordination"):
            self.logger.info(LOG_START.format(phase="rv-platform data processing coordination"))

            try:
                # Coordinate with rv-platform for data file generation
                # rv-platform handles logcat processing and CSV/JSON generation
                self.logger.info(f"Coordinating data processing for {metadata.get('total_tasks', 0)} tasks")
                
                # rv-platform generates:
                # - coverage.csv (detailed per-method coverage data from logcat processing)
                # - errors.csv (monitored operations violations from logcat processing)
                # - summary.csv (aggregate metrics per task)
                # - results.json (comprehensive structured data)
                
                # Note: instrument_errors.json is generated by PreProcessor during APK instrumentation phase
                
                self.logger.info("Data processing coordination completed - rv-platform handles logcat processing and CSV/JSON generation")

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="coordinating rv-platform data processing",
                    error=str(e)
                ))

    def _generate_experiment_summary(self, metadata: Dict[str, Any]) -> None:
        """
        Create a high-level experiment summary for logging and tracking.
        
        Args:
            metadata: Experiment metadata for summary generation
        """
        try:
            # Store experiment-level summary information
            self.experiment_metadata = {
                "total_tasks": metadata.get("total_tasks", 0),
                "completed_tasks": metadata.get("completed_tasks", 0),
                "completion_rate": metadata.get("completion_rate", 0),
                "experiment_timestamp": metadata.get("experiment_timestamp", datetime.now().isoformat())
            }

            self.logger.info(
                f"Experiment summary: {self.experiment_metadata['completed_tasks']} tasks completed, "
                f"{self.experiment_metadata['completion_rate']:.2%} completion rate"
            )

        except Exception as e:
            self.logger.warning(f"Failed to create experiment summary: {e}")











    def _publish_completion_event(self, task_count: int) -> None:
        """
        Publish experiment completion event with coordination information.
        
        Args:
            task_count: Number of tasks coordinated
        """
        try:
            summary_msg = f"Result coordination completed for {task_count} tasks"

            self.event_bus.publish_experiment_event(
                EventType.EXPERIMENT_COMPLETED,
                experiment_id=f"results-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                message=summary_msg,
                source="ResultManager"
            )
        except Exception as e:
            self.logger.warning(f"Failed to publish completion event: {e}")

    def get_experiment_metadata(self) -> Dict[str, Any]:
        """
        Get the current experiment metadata.
        
        Returns:
            Dictionary with experiment metadata and coordination information
        """
        return self.experiment_metadata.copy()
