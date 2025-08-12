"""
Clean experiment controller for RV-Android experiments.

This module provides experiment orchestration with clean separation of concerns
and no data transfer between modules.
"""
import os
from datetime import datetime
from typing import List

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.exceptions import RVExperimentExecutionError
from rv_android_core.event import EventBus, EventType
from rv_android_core.tools.abstract_tool import AbstractTool

from rv_experiment.config import ExperimentConfig
from rv_experiment.experiment.workflow.pre_processor import PreProcessor
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_experiment.experiment.workflow.post_processor import PostProcessor
import rv_experiment.constants as rv_cte

class ExperimentController:
    """
    Clean experiment controller with three-phase workflow.

    This controller orchestrates experiments with clear separation of concerns:
    - Pre-processing: APK instrumentation and static analysis
    - Execution: rv-platform coordination (includes automatic result processing)
    - Post-processing: Basic diagnostics only

    ### Architectural Principles:
    - No data transfer between rv-platform and rv-experiment
    - rv-platform handles all task execution and result processing
    - rv-experiment provides only orchestration and basic diagnostics
    - Clean three-phase workflow with minimal complexity

    ### Integration Points:
    - PreProcessor: APK instrumentation and static analysis
    - ExecutionController: Clean rv-platform coordination
    - PostProcessor: Basic completion diagnostics only
    """

    @ErrorHandler.handle_errors(
        component="ExperimentController",
        phase="initialization"
    )
    def __init__(self, config: ExperimentConfig, experiment_id: str = None):
        """
        Initialize the clean experiment controller.

        Args:
            config: Experiment configuration
            experiment_id: Optional experiment identifier
        """
        self.config = config
        self.experiment_id = experiment_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup results directory using proper naming logic
        # Use config.results_dir as base directory (defaults to "./results")
        results_base_dir = config.results_dir or f"./{rv_cte.RESULTS_DIR}"
        
        if config.name and config.name.strip():
            # Use experiment name if specified
            experiment_folder = config.name.strip()
        else:
            # Use timestamp-based name as fallback
            experiment_folder = f"experiment_{self.experiment_id}"
            self.config.name = self.experiment_id
        
        # Create full results directory path
        self.results_dir = os.path.join(results_base_dir, experiment_folder)
        os.makedirs(self.results_dir, exist_ok=True)

        # Initialize logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_experiment.experiment.controller',
            {CONTEXT_COMPONENT: 'ExperimentController'}
        )

        # Initialize event bus
        self.event_bus = EventBus.get_instance()

        # Initialize clean workflow components
        self.pre_processor = PreProcessor(config, self.event_bus)
        self.execution_controller = ExecutionController(config, self.event_bus)
        self.post_processor = PostProcessor(self.results_dir, self.event_bus)

        # Register event handlers
        self._setup_event_handlers()

        self.logger.info(f"Experiment '{self.config.name}' initialized: {self.results_dir}")

    def _setup_event_handlers(self):
        """
        Set up event handlers for experiment coordination.
        """
        # Basic event handling for coordination only
        pass

    @ErrorHandler.handle_errors(
        component="ExperimentController",
        phase="execution"
    )
    def run(self) -> bool:
        """
        Execute the complete experiment with clean three-phase workflow.

        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            experiment_id=self.experiment_id,
            phase="complete_experiment"
        ):
            self.logger.info(LOG_START.format(phase=f"experiment {self.experiment_id}"))

            try:
                success = True

                # Phase 1: Pre-processing (includes apk instrumentation for MOP error tracking)
                self.logger.info("Starting pre-processing phase")
                self._run_pre_processing()

                # Phase 2: Execution (rv-platform handles everything including result processing)
                self.logger.info("Starting execution phase")
                execution_success = self._run_execution()
                
                if not execution_success:
                    self.logger.warning("Execution phase completed with issues")
                    success = False

                # Phase 3: Post-processing (basic diagnostics only)
                self.logger.info("Starting post-processing phase")
                self.post_processor.process()

                # Publish experiment completed event
                self.event_bus.publish_experiment_event(
                    EventType.EXPERIMENT_COMPLETED,
                    experiment_id=self.experiment_id,
                    message="Experiment completed successfully" if success else "Experiment completed with issues",
                    source="ExperimentController"
                )

                self.logger.info(LOG_COMPLETE.format(phase=f"experiment {self.experiment_id}"))
                return success

            except Exception as e:
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

    def _run_pre_processing(self):
        """
        Execute pre-processing phase with instrumentation error tracking.
        """
        self.pre_processor.process(
            generate_monitors=self.config.generate_monitors,
            instrument=self.config.instrument_apks,
            static_analysis=self.config.run_static_analysis
        )

    def _run_execution(self) -> bool:
        """
        Execute tasks through rv-platform coordination.

        Returns:
            True if execution successful, False otherwise
        """
        try:
            # Get instrumented APKs
            apks = self.pre_processor.get_instrumented_apks()
            
            if not apks:
                self.logger.error("No APKs available for execution")
                return False

            # Get configured tools
            tools = self._get_configured_tools()
            if not tools:
                self.logger.error("No valid tools found for execution")
                return False

            # Setup execution controller
            self.execution_controller.setup(
                apks=apks,
                repetitions=self.config.repetitions,
                timeouts=self.config.timeouts,
                tools=tools,
                no_window=getattr(self.config, 'no_window', False),
                results_dir=self.results_dir
            )

            # Execute through rv-platform (includes automatic result processing)
            success = self.execution_controller.run()
            return success

        except Exception as e:
            self.logger.error(f"Execution phase failed: {e}")
            raise RVExperimentExecutionError(f"Execution failed: {e}") from e

    def _get_configured_tools(self) -> List[AbstractTool]:
        """
        Get configured tools for execution.

        Returns:
            List of configured tool instances
        """
        tools = []
        
        try:
            # Import tool factory
            from rv_tools import ToolFactory
            
            # Create ToolFactory instance
            tool_factory = ToolFactory()
            
            for tool_config in self.config.tool_configs:
                try:
                    # Create tool configuration and tool instance
                    from rv_android_core.domain.task import ToolConfig as TaskToolConfig
                    
                    # Use first variant for tool creation
                    variant = tool_config.variants[0] if tool_config.variants else "default"
                    task_tool_config = TaskToolConfig(
                        tool_name=tool_config.name,
                        variant=variant,
                        additional_params=tool_config.parameters
                    )
                    
                    tool = tool_factory.create_tool(task_tool_config)
                    tools.append(tool)
                    self.logger.debug(f"Configured tool: {tool_config.name}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to configure tool {tool_config.name}: {e}")
                    
        except ImportError:
            self.logger.error("Tool factory not available")
            
        return tools

    def get_experiment_status(self) -> dict:
        """
        Get the current status of the experiment.

        Returns:
            dict: Dictionary containing experiment status information
        """
        return {
            "experiment_id": self.experiment_id,
            "results_dir": self.results_dir,
            "execution_method": "clean_three_phase_workflow"
        }

    def save_experiment_config(self) -> None:
        """Save the experiment configuration to the results directory."""
        config_file = os.path.join(self.results_dir, "experiment_config.json")
        
        try:
            self.config.save_to_file(config_file)
            self.logger.info(f"Experiment configuration saved to {config_file}")
        except Exception as e:
            self.logger.warning(f"Failed to save experiment configuration: {e}")


def execute_with_config(config: ExperimentConfig) -> bool:
    """
    Execute experiment with provided configuration.

    Args:
        config: Experiment configuration

    Returns:
        True if experiment completed successfully, False otherwise
    """
    controller = ExperimentController(config)
    return controller.run()