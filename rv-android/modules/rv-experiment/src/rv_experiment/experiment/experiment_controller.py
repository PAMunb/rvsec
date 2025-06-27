"""
Main experiment controller for RV-Android testing orchestration.

This module implements the central experiment coordination system that manages the complete
lifecycle of Android testing experiments, from configuration to execution and results processing.
"""
import json
import os
from typing import List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus, EventType
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.experiment.task.storage import TaskStorage
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor
from rv_experiment.experiment.workflow.pre_processor import PreProcessor
from rv_experiment.experiment.workflow.result_manager import ResultManager
from rv_experiment.config import ExperimentConfig
from rv_experiment.constants import EXPERIMENT_LOGS_DIR, EXPERIMENT_TASKS_FILE
import rv_android_core.util.utils as utils

class ExperimentController:
    """
    A comprehensive experiment controller that manages the lifecycle of Android testing experiments.

    ### Architectural Decisions:
    - Implements a modular, component-based approach to experiment management
    - Delegates specific responsibilities to specialized components
    - Provides a unified interface for experiment configuration and execution
    - Ensures proper coordination between workflow phases

    ### Role in the System:
    - Acts as the primary entry point for running experiments
    - Orchestrates the entire experiment workflow from setup to completion
    - Manages component lifecycle and configuration
    - Provides a consistent interface for experiment execution
    - Facilitates proper resource management and experiment tracking
    """

    def __init__(self, config: ExperimentConfig, event_bus: Optional[EventBus] = None):
        """
        Initialize the experiment controller with modular components.
        
        Args:
            config: Experiment configuration
            event_bus: Optional event bus for event handling. If not provided,
                      the default event bus will be used.
        """
        # Store configuration
        self.config = config
        
        # Set up event bus
        self.event_bus = event_bus or EventBus.get_instance()

        # Set up experiment identifier
        self.experiment_id = config.name

        # Configure logging and error handling
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.controller',
            {
                'experiment_id': self.experiment_id,
                CONTEXT_COMPONENT: 'ExperimentController'
            }
        )

        # Create experiment directory inside output directory
        self.results_dir = config.output_dir # os.path.join(config.output_dir, self.experiment_id)
        print(f"*** results_dir={self.results_dir}")
        utils.create_folder_if_not_exists(self.results_dir)
        # os.makedirs(self.results_dir, exist_ok=True)

        # Set up file logging for this experiment
        self.logging_manager.setup_file_logging(
            log_dir=os.path.join(self.results_dir, EXPERIMENT_LOGS_DIR),
            experiment_id=self.experiment_id
        )

        # Create task storage
        storage_file = os.path.join(self.results_dir, EXPERIMENT_TASKS_FILE)
        print(f"storage_file={storage_file}")
        self.task_storage = TaskStorage(storage_file)

        # exit(1)

        # Initialize workflow components directly (simplified approach)
        self.pre_processor = PreProcessor(config, self.event_bus)
        self.execution_controller = ExecutionController(self.task_storage, self.config, self.event_bus)
        self.post_processor = PostProcessor(self.results_dir, self.event_bus)
        self.result_manager = ResultManager(self.results_dir, self.task_storage, self.event_bus)

        # Register event handlers
        self._setup_event_handlers()

        # Log experiment initialization
        self.logger.info(f"Experiment {self.experiment_id} initialized")

    def _setup_event_handlers(self):
        """
        Set up event handlers for experiment coordination.
        
        ### Event Handling Strategy:
        - Registers handlers for key experiment events
        - Enables cross-component communication and coordination
        - Supports experiment state tracking and error handling
        """
        # Register handler for experiment lifecycle events
        self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            self._handle_experiment_started
        )
        
        self.event_bus.subscribe(
            EventType.EXPERIMENT_COMPLETED,
            self._handle_experiment_completed
        )
        
        # Register handler for task lifecycle events
        self.event_bus.subscribe(
            EventType.TASK_STARTED,
            self._handle_task_started
        )
        
        self.event_bus.subscribe(
            EventType.TASK_COMPLETED,
            self._handle_task_completed
        )

    def _handle_experiment_started(self, event_data):
        """Handle experiment started events."""
        self.logger.debug(f"Experiment started event: {event_data}")

    def _handle_experiment_completed(self, event_data):
        """Handle experiment completed events."""
        self.logger.debug(f"Experiment completed event: {event_data}")

    def _handle_task_started(self, event_data):
        """Handle task started events."""
        self.logger.debug(f"Task started event: {event_data}")

    def _handle_task_completed(self, event_data):
        """Handle task completed events."""
        self.logger.debug(f"Task completed event: {event_data}")

    def run_experiment(self, tools: List[str], apks: List[str], 
                      generate_monitors: bool = True, 
                      instrument: bool = True, 
                      static_analysis: bool = True) -> bool:
        """
        Execute a complete experiment workflow.

        Args:
            tools: List of tool names to use for testing
            apks: List of APK file paths to test
            generate_monitors: Whether to generate runtime verification monitors
            instrument: Whether to instrument APKs with monitors
            static_analysis: Whether to perform static analysis

        Returns:
            bool: True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(phase="experiment_execution"):
            self.logger.info(LOG_START.format(phase=f"experiment {self.experiment_id}"))

            try:
                # Publish experiment started event
                self.event_bus.publish_experiment_event(
                    EventType.EXPERIMENT_STARTED,
                    experiment_id=self.experiment_id,
                    message="Experiment execution started",
                    source="ExperimentController"
                )

                # Phase 1: Pre-processing
                self.logger.info("Starting pre-processing phase")
                self.pre_processor.process(generate_monitors, instrument, static_analysis)

                # Phase 2: Get instrumented APKs for execution
                instrumented_apks = self.pre_processor.get_instrumented_apks()
                if not instrumented_apks:
                    self.logger.error("No APKs available for execution after pre-processing")
                    return False

                # Phase 3: Execute experiments for each tool
                for tool_name in tools:
                    self.logger.info(f"Starting execution phase with tool: {tool_name}")
                    success = self.execution_controller.execute_experiments(
                        tool_name=tool_name,
                        apps=instrumented_apks,
                        repetitions=self.config.repetitions,
                        timeout=self.config.timeout
                    )
                    
                    if not success:
                        self.logger.warning(f"Execution failed for tool: {tool_name}")

                # Phase 4: Post-processing
                self.logger.info("Starting post-processing phase")
                self.post_processor.process()

                # Phase 5: Results management
                self.logger.info("Starting results management phase")
                self.result_manager.process()

                # Publish experiment completed event
                self.event_bus.publish_experiment_event(
                    EventType.EXPERIMENT_COMPLETED,
                    experiment_id=self.experiment_id,
                    message="Experiment execution completed successfully",
                    source="ExperimentController"
                )

                self.logger.info(LOG_COMPLETE.format(phase=f"experiment {self.experiment_id}"))
                return True

            except Exception as e:
                error_context = {
                    "component": "ExperimentController",
                    "operation": "experiment_execution",
                    "experiment_id": self.experiment_id,
                    "tools": tools,
                    "apks_count": len(apks)
                }
                self.error_handler.handle_error(e, error_context)
                
                self.logger.error(LOG_ERROR.format(
                    phase=f"experiment {self.experiment_id}",
                    error=str(e)
                ))
                
                # Publish experiment failed event
                self.event_bus.publish_experiment_event(
                    EventType.EXPERIMENT_FAILED,
                    experiment_id=self.experiment_id,
                    message=f"Experiment execution failed: {str(e)}",
                    source="ExperimentController"
                )
                
                return False

    def get_experiment_status(self) -> dict:
        """
        Get the current status of the experiment.

        Returns:
            dict: Dictionary containing experiment status information
        """
        completed_tasks = self.task_storage.get_completed_tasks()
        pending_tasks = self.task_storage.get_pending_tasks()
        
        return {
            "experiment_id": self.experiment_id,
            "results_dir": self.results_dir,
            "completed_tasks": len(completed_tasks),
            "pending_tasks": len(pending_tasks),
            "total_tasks": len(completed_tasks) + len(pending_tasks)
        }

    def save_experiment_config(self) -> None:
        """Save the experiment configuration to the results directory."""
        config_file = os.path.join(self.results_dir, "experiment_config.json")
        
        config_data = {
            "experiment_id": self.experiment_id,
            "timestamp": self.config.get_timestamp_string(),
            "configuration": self.config.to_dict()
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
            
        self.logger.debug(f"Experiment configuration saved to: {config_file}")

    def cleanup(self) -> None:
        """
        Clean up experiment resources.
        
        Performs cleanup operations for the experiment, including:
        - Finalizing task storage
        - Cleaning up temporary files
        - Closing logging handlers
        """
        try:
            # Save final task state
            self.task_storage.save()
            
            # Save experiment configuration
            self.save_experiment_config()
            
            self.logger.info(f"Experiment {self.experiment_id} cleanup completed")
            
        except Exception as e:
            error_context = {
                "component": "ExperimentController",
                "operation": "cleanup",
                "experiment_id": self.experiment_id
            }
            self.error_handler.handle_error(e, error_context)


def execute_with_config(config: ExperimentConfig) -> bool:
    """
    Execute experiment with given configuration.
    
    This function provides a simple interface for executing experiments
    compatible with the CLI and other external interfaces.
    
    Args:
        config: Experiment configuration
        
    Returns:
        bool: True if experiment completed successfully, False otherwise
    """
    # Create controller
    controller = ExperimentController(config)
    
    try:
        # Extract tools and APKs from config
        tools = [c.name for c in config.tool_configs]
        apks = config.get_apk_list()
        
        # Run experiment
        success = controller.run_experiment(
            tools=tools,
            apks=apks,
            generate_monitors=True,
            instrument=True, 
            static_analysis=True
        )
        
        return success
        
    finally:
        # Always cleanup
        controller.cleanup()