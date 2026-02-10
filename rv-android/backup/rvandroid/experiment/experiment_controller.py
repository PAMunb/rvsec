# rvandroid/experiment_workflow/experiment_controller.py
"""
Main experiment controller for RV-Android.
Coordinates the overall experiment workflow and lifecycle.
"""
import json
import os
from typing import List, Optional

from rvandroid.experiment.event import (
    EventBus,
    EventType,
    get_event_bus
)
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.experiment.workflow.execution_controller import ExecutionController
from rvandroid.experiment.workflow.post_processor import PostProcessor
from rvandroid.experiment.workflow.pre_processor import PreProcessor
from rvandroid.experiment.workflow.result_manager import ResultManager
from rvandroid.experiment.workflow.workflow_factory import WorkflowFactory
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager
from settings import TIMESTAMP, RESULTS_DIR


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

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the experiment controller with modular components.
        
        Args:
            event_bus: Optional event bus for event handling. If not provided,
                      the default event bus will be used.
        """
        # Set up event bus (using dependency injection)
        self.event_bus = event_bus or get_event_bus()

        # Set up experiment identifier
        self.experiment_id = f"experiment_{TIMESTAMP}"

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
        self.results_dir = os.path.join(RESULTS_DIR, self.experiment_id)
        os.makedirs(self.results_dir, exist_ok=True)

        # Set up file logging for this experiment
        self.logging_manager.setup_file_logging(
            log_dir=os.path.join(self.results_dir, "logs"),
            experiment_id=self.experiment_id
        )

        # Create task storage
        storage_file = os.path.join(self.results_dir, "tasks.json")
        self.task_storage = TaskStorage(storage_file)

        # Create workflow factory
        self.factory = WorkflowFactory(self.task_storage, self.event_bus)

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
                    operation=f"Experiment {experiment_id}"
                ))

        def on_experiment_completed(event):
            """Handle experiment completion events"""
            # Extract experiment_id from ExperimentEvent
            experiment_id = event.experiment_id if hasattr(event, 'experiment_id') else self.experiment_id

            with self.logger.with_context(phase="experiment_completion"):
                self.logger.info(LOG_COMPLETE.format(
                    operation=f"Experiment {experiment_id}"
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
                    operation=f"Task {task_id} ({task_config.get('apk_name', 'unknown')}, "
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
                    operation=f"Task {task_id}",
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
            self.logger.info(LOG_START.format(operation="Experiment"))

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
                # Configure execution parameters
                instrumented_apks = self.pre_processor.get_instrumented_apks()

                # Set up experiment execution
                self.execution_controller.setup(
                    apks=instrumented_apks,
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

            self.logger.info(LOG_COMPLETE.format(operation="Experiment"))

    def _resume_from_memory(self, memory_file: str):
        """
        Resume an experiment from a memory file with enhanced error handling.

        Args:
            memory_file: Path to the memory file
        """
        with self.logger.with_context(phase="resume_from_memory"):
            if not os.path.exists(memory_file):
                self.logger.error(LOG_ERROR.format(
                    operation="finding memory file",
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
                        operation="loading memory file",
                        error=f"Failed to load tasks from {memory_file}"
                    ))
                    return

                # Update components with new task storage
                self.execution_controller.update_storage(self.task_storage)

                self.logger.info(f"Successfully resumed experiment with {len(self.task_storage.get_tasks())} tasks")

            except json.JSONDecodeError as e:
                self.logger.error(LOG_ERROR.format(
                    operation="parsing memory file",
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
                    operation="resuming from memory file",
                    error=str(e)
                ))


def execute(tools: Optional[List[AbstractTool]] = None):
    """
    Execute experiment with configuration from the Configuration singleton.
    
    This function uses the Configuration singleton to configure and execute
    an experiment using the ExperimentController.

    Args:
        tools: Provided list of tool objects to use (THESE WILL OVERRIDE CONFIGURATION)
    """
    # Set up standardized logging for this function
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger('experiment_workflow.execute', {'function': 'execute'})

    from rvandroid.config.configuration import Configuration
    from rvandroid.tools.registry import ToolRegistry

    with logger.with_context(phase="configuration"):
        # Get configuration instance
        config = Configuration.get_instance()

        # Get experiment configuration
        repetitions = config.get_int("repetitions", 1)
        timeouts = config.get_list("timeouts", [60])
        memory_file = config.get_str("memory_file", "")
        generate_monitors = config.get_bool("generate_monitors", True)
        instrument = config.get_bool("instrument", True)
        static_analysis = config.get_bool("static_analysis", True)
        skip_experiment = config.get_bool("skip_experiment", False)
        no_window = config.get_bool("no_window", False)

        # Log configuration values
        logger.info(f"Configuration values from singleton:")
        logger.info(f"  - repetitions: {repetitions}")
        logger.info(f"  - timeouts: {timeouts}")
        logger.info(f"  - generate_monitors: {generate_monitors}")
        logger.info(f"  - instrument: {instrument}")
        logger.info(f"  - static_analysis: {static_analysis}")
        logger.info(f"  - skip_experiment: {skip_experiment}")
        logger.info(f"  - no_window: {no_window}")
        logger.info(f"  - memory_file: {memory_file}")

        # Handle tools configuration
        if tools is not None:
            logger.info(f"Using explicitly provided tools: {[tool.name for tool in tools]}")
        else:
            tool_names = config.get_list("tools", ["monkey"])
            logger.info(f"Using tools from configuration: {tool_names}")

            # Get the tool registry
            registry = ToolRegistry.get_instance()

            # Get tools by name
            tools = registry.get_tools(tool_names)
            logger.info(f"Loaded {len(tools)} tools from registry: {[tool.name for tool in tools]}")

    # Create experiment controller and execute
    with logger.with_context(phase="experiment_execution"):
        logger.info(LOG_START.format(operation="experiment execution"))
        experiment = ExperimentController()
        experiment.execute(
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools,
            memory_file=memory_file,
            generate_monitors=generate_monitors,
            instrument=instrument,
            static_analysis=static_analysis,
            skip_experiment=skip_experiment,
            no_window=no_window
        )
        logger.info(LOG_COMPLETE.format(operation="experiment execution"))
