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
from rv_android_core.event import (
    EventBus,
    EventType
)
from rv_experiment.experiment.task.storage import TaskStorage
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor
from rv_experiment.experiment.workflow.pre_processor import PreProcessor
from rv_experiment.experiment.workflow.result_manager import ResultManager
from rv_experiment.experiment.workflow.workflow_factory import WorkflowFactory
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.config import ExperimentConfig
from rv_experiment.constants import EXPERIMENT_LOGS_DIR, EXPERIMENT_TASKS_FILE


class ExperimentController:
    """
    Experiment controller that manages the lifecycle of Android testing experiments.

    ### Architectural Decisions:
    - Implements a modular, component-based approach to experiment management
    - Delegates specific responsibilities to specialized workflow components
    - Provides a unified interface for experiment configuration and execution
    - Ensures proper coordination between pre-processing, execution, and post-processing phases

    ### Role in the System:
    - Acts as the primary entry point for running experiments
    - Orchestrates the entire experiment workflow from setup to completion
    - Manages component lifecycle and configuration coordination
    - Provides consistent interface for experiment execution across different tool types
    - Facilitates proper resource management and experiment state tracking

    ### Component Integration:
    - Pre-processor: Handles monitor generation, APK instrumentation, and static analysis
    - Execution Controller: Manages task execution and tool coordination
    - Post-processor: Handles results analysis and report generation
    - Result Manager: Coordinates comprehensive result collection and storage
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
        
        # Set up event bus (using dependency injection)
        self.event_bus = event_bus or EventBus.get_instance()

        # Set up experiment identifier
        self.experiment_id = self.config.experiment_id or f"experiment_{self.config.get_timestamp_string()}"

        # Configure logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.controller',
            {
                'experiment_id': self.experiment_id,
                CONTEXT_COMPONENT: 'ExperimentController'
            }
        )

        # Create experiment directory
        self.results_dir = self.config.output_dir
        os.makedirs(self.results_dir, exist_ok=True)

        # Set up file logging for this experiment
        self.logging_manager.setup_file_logging(
            log_dir=os.path.join(self.results_dir, EXPERIMENT_LOGS_DIR),
            experiment_id=self.experiment_id
        )

        # Create task storage
        storage_file = os.path.join(self.results_dir, EXPERIMENT_TASKS_FILE)
        self.task_storage = TaskStorage(storage_file)

        # Create workflow factory
        self.factory = WorkflowFactory(self.task_storage, self.event_bus, self.config)

        # Initialize workflow components
        self.pre_processor: PreProcessor = self.factory.create_pre_processor(self.results_dir)
        self.execution_controller: ExecutionController = self.factory.create_execution_controller()
        self.post_processor: PostProcessor = self.factory.create_post_processor(self.results_dir)
        self.result_manager: ResultManager = self.factory.create_result_manager(self.results_dir)

        # Register event handlers
        self._setup_event_handlers()

        # Log experiment initialization
        self.logger.experiment_start(f"Experiment {self.experiment_id} initialized")

    def _setup_event_handlers(self):
        """
        Set up event handlers for the experiment.

        Registers callback functions for various event types that may occur during
        experiment execution, ensuring proper logging and coordination.
        """

        def on_experiment_started(event):
            """Handle experiment start events"""
            # Extract experiment_id from ExperimentEvent
            experiment_id = event.experiment_id if hasattr(event, 'experiment_id') else self.experiment_id

            with self.logger.with_context(phase="experiment_start"):
                self.logger.info(LOG_START.format(
                    phase=f"Experiment {experiment_id}"
                ))

        def on_experiment_completed(event):
            """Handle experiment completion events"""
            # Extract experiment_id from ExperimentEvent
            experiment_id = event.experiment_id if hasattr(event, 'experiment_id') else self.experiment_id

            with self.logger.with_context(phase="experiment_completion"):
                self.logger.info(LOG_COMPLETE.format(
                    phase=f"Experiment {experiment_id}"
                ))

        def on_task_started(event):
            """Handle task start events"""
            # Extract data from TaskEvent
            task_id = event.task_id if hasattr(event, 'task_id') else "unknown"
            task_config = event.task_config if hasattr(event, 'task_config') else {}

            with self.logger.with_context(
                    task_id=task_id,
                    phase="task_start",
                    **task_config
            ):
                self.logger.info(LOG_START.format(
                    phase=f"Task {task_id} ({task_config.get('apk_name', 'unknown')}, "
                              f"{task_config.get('tool_name', 'unknown')})"
                ))

        def on_task_failed(event):
            """Handle task failure events"""
            # Extract data from TaskEvent
            task_id = event.task_id if hasattr(event, 'task_id') else "unknown"
            details = event.details if hasattr(event, 'details') else {}
            error = details.get('error', 'Unknown error')

            with self.logger.with_context(
                    task_id=task_id,
                    phase="task_failure",
                    error=error
            ):
                self.logger.error(LOG_ERROR.format(
                    phase=f"Task {task_id}",
                    error=error
                ))

        # Register handlers using new API with appropriate channels
        self.event_bus.subscribe(
            event_type=EventType.EXPERIMENT_STARTED,
            callback=on_experiment_started,
            channel=EventBus.LIFECYCLE_CHANNEL
        )

        self.event_bus.subscribe(
            event_type=EventType.EXPERIMENT_COMPLETED,
            callback=on_experiment_completed,
            channel=EventBus.LIFECYCLE_CHANNEL
        )

        self.event_bus.subscribe(
            event_type=EventType.TASK_STARTED,
            callback=on_task_started,
            channel=EventBus.LIFECYCLE_CHANNEL
        )

        self.event_bus.subscribe(
            event_type=EventType.TASK_FAILED,
            callback=on_task_failed,
            channel=EventBus.LIFECYCLE_CHANNEL
        )

    def execute(self, repetitions: int, timeouts: List[int], tools: List[AbstractTool],
                memory_file: str = "", generate_monitors: bool = True, instrument: bool = True,
                static_analysis: bool = True, skip_experiment: bool = False, no_window: bool = False):
        """
        Execute the entire experiment workflow with configurable phases.

        Manages the full experiment lifecycle including optional monitor generation, APK instrumentation,
        static analysis, experiment execution, and result processing.

        Args:
            repetitions: Number of times each task should be repeated
            timeouts: List of timeout durations to apply during experiment
            tools: Collection of testing tools to be used in the experiment
            memory_file: Path to a previous execution state file for resuming an experiment
            generate_monitors: Flag to enable automatic monitor generation
            instrument: Flag to enable APK instrumentation
            static_analysis: Flag to enable static code analysis
            skip_experiment: Flag to bypass experiment execution
            no_window: Flag to run emulator in headless mode without visual display
        """
        with self.logger.with_context(
                repetitions=repetitions,
                timeouts=timeouts,
                tools=[tool.name for tool in tools],
                memory_file=memory_file,
                generate_monitors=generate_monitors,
                instrument=instrument,
                static_analysis=static_analysis,
                skip_experiment=skip_experiment,
                no_window=no_window,
                phase="execute"
        ):
            self.logger.info(LOG_START.format(phase="Experiment"))

            # Publish experiment started event
            self.event_bus.publish_experiment_event(
                event_type=EventType.EXPERIMENT_STARTED,
                experiment_id=self.experiment_id,
                message="Starting experiment execution",
                source="ExperimentController",
                channel=EventBus.LIFECYCLE_CHANNEL
            )

            # Handle memory file for experiment resumption
            if memory_file:
                # TODO verificar se esta funcionando
                self._resume_from_memory(memory_file)
            else:
                # Pre-process APKs if not resuming
                if generate_monitors or instrument or static_analysis:
                    self.pre_processor.process(generate_monitors, instrument, static_analysis)

            # Run experiment if not skipped
            if not skip_experiment:
                # Configure execution parameters - use instrumented APKs if instrumentation was performed,
                # otherwise use original APKs from application configuration
                if instrument:
                    apks = self.pre_processor.get_instrumented_apks()
                else:
                    # Use original APKs from application configuration
                    from rv_android_core.app import App
                    application_paths = self.config.applications.get_applications()
                    apks = [App(app_path) for app_path in application_paths]

                # Set up experiment execution
                self.execution_controller.setup(
                    apks=apks,
                    repetitions=repetitions,
                    timeouts=timeouts,
                    tools=tools,
                    no_window=no_window
                )

                # Run the experiment tasks
                self.execution_controller.run()

                # Process results (includes report generation through integrated ResultManager)
                self.post_processor.process()

            # Publish experiment completed event
            self.event_bus.publish_experiment_event(
                event_type=EventType.EXPERIMENT_COMPLETED,
                experiment_id=self.experiment_id,
                message="Experiment execution completed",
                source="ExperimentController",
                channel=EventBus.LIFECYCLE_CHANNEL
            )

            self.logger.info(LOG_COMPLETE.format(phase="Experiment"))

    def _resume_from_memory(self, memory_file: str):
        """
        Resume an experiment from a memory file with enhanced error handling.

        Args:
            memory_file: Path to the memory file
        """
        with self.logger.with_context(phase="resume_from_memory"):
            if not os.path.exists(memory_file):
                self.logger.error(LOG_ERROR.format(
                    phase="finding memory file",
                    error=f"Memory file not found: {memory_file}"
                ))
                return

            # Copy task storage to our results directory
            self.logger.info(f"Resuming experiment from memory file: {memory_file}")

            try:
                # Create a new task storage instance with the memory file
                self.task_storage = TaskStorage(memory_file)

                # Attempt to load tasks, handling potential errors
                load_success = self.task_storage.load()

                if not load_success:
                    self.logger.error(LOG_ERROR.format(
                        phase="loading memory file",
                        error=f"Failed to load tasks from {memory_file}"
                    ))
                    return

                # Update components with new task storage
                self.execution_controller.update_storage(self.task_storage)

                self.logger.info(f"Successfully resumed experiment with {len(self.task_storage.get_tasks())} tasks")

            except json.JSONDecodeError as e:
                self.logger.error(LOG_ERROR.format(
                    phase="parsing memory file",
                    error=f"Memory file contains invalid JSON: {e}"
                ))
            except Exception as e:
                # Create error context for the error handler
                error_context = {
                    "component": "ExperimentController",
                    "phase": "resume_from_memory",
                    "memory_file": memory_file,
                    "experiment_id": self.experiment_id,
                    "results_dir": self.results_dir
                }

                # Use ErrorHandler for proper exception handling
                self.error_handler.handle_error(e, error_context)

                # Log additional information
                self.logger.error(LOG_ERROR.format(
                    phase="resuming from memory file",
                    error=str(e)
                ))


def execute_with_config(config: ExperimentConfig, tools: Optional[List[AbstractTool]] = None):
    """
    Execute experiment with provided configuration.
    
    This function configures and executes an experiment using the ExperimentController
    with the provided ExperimentConfig instance.

    Args:
        config: Experiment configuration instance
        tools: Optional list of tool objects to use
    """
    # Set up logging for this function
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger('experiment_controller.execute', {'function': 'execute_with_config'})

    from rv_tools.registry.registry import ToolRegistry

    with logger.with_context(phase="configuration"):
        # Get experiment parameters from config
        repetitions = config.repetitions
        timeouts = config.timeouts
        generate_monitors = config.generate_monitors
        instrument = config.instrument_apks
        static_analysis = config.run_static_analysis
        no_window = config.no_window

        # Log configuration values
        logger.info(f"Configuration values:")
        logger.info(f"  - repetitions: {repetitions}")
        logger.info(f"  - timeouts: {timeouts}")
        logger.info(f"  - generate_monitors: {generate_monitors}")
        logger.info(f"  - instrument: {instrument}")
        logger.info(f"  - static_analysis: {static_analysis}")
        logger.info(f"  - no_window: {no_window}")

        # Handle tools configuration
        if tools is not None:
            logger.info(f"Using explicitly provided tools: {[tool.name for tool in tools]}")
        else:
            # Get tools from configuration
            tool_names = [tc.name for tc in config.tool_configs]
            logger.info(f"Using tools from configuration: {tool_names}")

            # Get the tool registry
            registry = ToolRegistry.get_instance()

            # Get tools by name
            tools = registry.get_tools(tool_names)
            logger.info(f"Loaded {len(tools)} tools from registry: {[tool.name for tool in tools]}")

    # Create experiment controller and execute
    with logger.with_context(phase="experiment_execution"):
        logger.info(LOG_START.format(phase="experiment execution"))
        experiment = ExperimentController(config)
        experiment.execute(
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools,
            generate_monitors=generate_monitors,
            instrument=instrument,
            static_analysis=static_analysis,
            no_window=no_window
        )
        logger.info(LOG_COMPLETE.format(phase="experiment execution"))
