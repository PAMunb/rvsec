"""
Execution controller for RV-Android experiments using rv-platform integration.

This module implements the execution coordination system that orchestrates experiment
execution through rv-platform while maintaining backward compatibility with the
existing rv-experiment interface.
"""
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any

from rv_android_core.app import App
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.exceptions import RVExperimentExecutionError
from rv_android_core.event import EventBus
from rv_android_core.tools.abstract_tool import AbstractTool

# Import rv-platform components
from rv_platform.platform import Platform
from rv_platform.config.platform_config import PlatformConfig, ToolConfig

from rv_platform.storage.task_storage import TaskStorage
from rv_experiment.config import ExperimentConfig


class ExecutionController:
    """
    Controller that orchestrates experiment execution through rv-platform integration.

    ### Architectural Overview:
    This controller acts as a bridge between rv-experiment's orchestration layer
    and rv-platform's execution engine. It translates experiment configurations
    into platform configurations and coordinates the execution flow while
    maintaining compatibility with existing experiment workflows.

    ### Architectural Decisions:
    - Delegates task execution to rv-platform for centralized execution management
    - Maintains backward compatibility with existing rv-experiment interfaces
    - Provides translation layer between experiment and platform configurations
    - Ensures proper event coordination between experiment and platform layers

    ### Role in the System:
    - Translates experiment configurations to platform configurations
    - Orchestrates experiment execution through rv-platform
    - Coordinates event flow between experiment and platform layers
    - Maintains experiment-level task tracking and storage integration
    - Provides unified interface for execution statistics and reporting

    ### Integration Points:
    - rv-platform: Primary execution engine for task coordination
    - rv-experiment: Configuration and workflow orchestration
    - TaskStorage: Experiment-level task tracking and persistence
    - EventBus: Event coordination between layers
    """

    @ErrorHandler.handle_errors(
        component="ExecutionController",
        phase="initialization"
    )
    def __init__(self, task_storage: TaskStorage, config: ExperimentConfig, event_bus: EventBus):
        """
        Initialize the execution controller with rv-platform integration.

        ### Initialization Strategy:
        - Sets up platform integration components
        - Configures event coordination between experiment and platform layers
        - Establishes translation layer for configuration management
        - Prepares execution environment for platform delegation

        Args:
            task_storage: Storage for experiment tasks and state management
            config: Experiment configuration with orchestration parameters
            event_bus: Event bus for coordinated event publishing across layers
        """
        self.task_storage = task_storage
        self.config = config
        self.event_bus = event_bus

        # Configure logging and error handling using rv-android-core infrastructure
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rv_experiment.execution_controller',
            {CONTEXT_COMPONENT: 'ExecutionController'}
        )

        # Platform integration state
        self.platform = None
        self.platform_config = None
        self.has_errors = False
        
        # Result tracking
        self.base_results_dir = os.path.dirname(self.task_storage.storage_file)
        
        self.logger.info("ExecutionController initialized with rv-platform integration")

    @ErrorHandler.handle_errors(
        component="ExecutionController", 
        phase="storage_update"
    )
    def update_storage(self, task_storage: TaskStorage):
        """
        Update the task storage used by the execution controller.

        Args:
            task_storage: New task storage instance for updated experiment state
        """
        self.task_storage = task_storage
        self.base_results_dir = os.path.dirname(self.task_storage.storage_file)
        self.logger.info("Task storage updated for execution controller")

    @ErrorHandler.handle_errors(
        component="ExecutionController",
        phase="setup"
    )
    def setup(self, apks: List[App], repetitions: int, timeouts: List[int],
              tools: List[AbstractTool], no_window: bool = False):
        """
        Set up experiment execution by configuring rv-platform integration.

        ### Setup Strategy:
        - Translates experiment parameters to platform configuration
        - Creates temporary execution directory for platform results
        - Configures tool mappings between experiment and platform layers
        - Establishes proper directory structure for execution coordination

        Args:
            apks: List of application objects to test
            repetitions: Number of repetitions for each task
            timeouts: List of timeout values for task execution
            tools: List of testing tools for experiment execution
            no_window: Whether to run emulator in headless mode
        """
        with self.logger.with_context(
                apks=[app.name for app in apks],
                repetitions=repetitions,
                timeouts=timeouts,
                tools=[tool.name for tool in tools],
                no_window=no_window,
                phase="setup"
        ):
            self.logger.info(LOG_START.format(phase="execution setup"))

            # Create platform configuration from experiment parameters
            self.platform_config = self._create_platform_config(
                apks, repetitions, timeouts, tools, no_window
            )

            # Initialize platform with event bus coordination
            self.platform = Platform(self.platform_config, self.event_bus)

            self.logger.info(LOG_COMPLETE.format(phase="execution setup"))

    @ErrorHandler.handle_errors(
        component="ExecutionController",
        phase="execution"
    )
    def run(self) -> bool:
        """
        Execute experiment tasks through rv-platform coordination.

        ### Execution Strategy:
        - Delegates task execution to rv-platform engine
        - Coordinates event flow between experiment and platform layers
        - Tracks execution results and error conditions
        - Maintains experiment-level statistics and reporting

        Returns:
            True if all tasks completed successfully, False if errors occurred
        """
        if not self.platform or not self.platform_config:
            raise RVExperimentExecutionError(
                "Execution controller not properly set up. Call setup() first."
            )

        with self.logger.with_context(phase="execution"):
            self.logger.info(LOG_START.format(phase="platform execution"))

            try:
                # Execute through rv-platform
                results = self.platform.run()
                
                # Track execution results
                self.has_errors = results.get('failed_tasks', 0) > 0
                
                # Log execution statistics
                self.logger.info(f"Platform execution completed: {results}")
                
                success = not self.has_errors
                self.logger.info(LOG_COMPLETE.format(phase="platform execution"))
                
                return success

            except Exception as e:
                self.has_errors = True
                self.logger.error(LOG_ERROR.format(
                    phase="platform execution",
                    error=str(e)
                ))
                raise RVExperimentExecutionError(f"Platform execution failed: {e}") from e

    @ErrorHandler.handle_errors(
        component="ExecutionController",
        phase="platform_config_creation"
    )
    def _create_platform_config(self, apks: List[App], repetitions: int, 
                               timeouts: List[int], tools: List[AbstractTool], 
                               no_window: bool) -> PlatformConfig:
        """
        Create platform configuration from experiment parameters.

        ### Configuration Translation Strategy:
        - Maps experiment tools to platform tool configurations
        - Establishes proper directory structure for platform execution
        - Configures execution parameters for platform coordination
        - Ensures compatibility between experiment and platform data models

        Args:
            apks: List of application objects
            repetitions: Number of execution repetitions
            timeouts: List of timeout values
            tools: List of testing tools
            no_window: Headless execution flag

        Returns:
            PlatformConfig configured for experiment execution
        """
        # Create temporary directory for platform execution within experiment results
        platform_results_dir = os.path.join(self.base_results_dir, "platform_execution")
        os.makedirs(platform_results_dir, exist_ok=True)

        # Determine APKs directory from experiment configuration
        if hasattr(self.config, 'get_instrumented_dir'):
            apks_dir = self.config.get_instrumented_dir()
        else:
            # Fallback to current working directory if instrumented dir not available
            apks_dir = os.getcwd()

        # Convert experiment tools to platform tool configurations
        platform_tools = []
        for tool in tools:
            tool_config = ToolConfig(
                name=tool.name,
                variants=getattr(tool, 'variants', []),
                parameters=getattr(tool, 'parameters', {})
            )
            platform_tools.append(tool_config)

        # Create platform configuration
        platform_config = PlatformConfig(
            apks_dir=apks_dir,
            tools=platform_tools,
            repetitions=repetitions,
            timeouts=timeouts,
            results_dir=platform_results_dir,
            no_window=no_window,
            log_level="INFO"
        )

        self.logger.info(f"Created platform configuration: {len(platform_tools)} tools, "
                        f"{repetitions} repetitions, {len(timeouts)} timeouts")

        return platform_config

    @ErrorHandler.handle_errors(
        component="ExecutionController",
        phase="statistics_collection"
    )
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics from platform integration.

        Returns:
            Dictionary containing execution statistics and metrics
        """
        if not self.platform:
            return {
                "status": "not_executed",
                "tasks_completed": 0,
                "tasks_failed": 0,
                "has_errors": self.has_errors
            }

        # Get platform statistics
        platform_stats = self.platform.get_execution_summary()
        
        # Add experiment-level metadata
        experiment_stats = {
            "execution_method": "rv_platform_integration",
            "has_errors": self.has_errors,
            "base_results_dir": self.base_results_dir,
            **platform_stats
        }

        return experiment_stats

    @ErrorHandler.handle_errors(
        component="ExecutionController",
        phase="coverage_report_generation"
    )
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get coverage report from platform execution results.

        Returns:
            Dictionary containing coverage analysis and metrics
        """
        if not self.platform:
            return {"status": "no_execution_data"}

        # Platform handles coverage reporting through its components
        # Delegate to platform for coverage analysis
        try:
            platform_stats = self.platform.get_execution_summary()
            
            coverage_report = {
                "coverage_source": "rv_platform_integration",
                "execution_summary": platform_stats,
                "has_coverage_data": platform_stats.get('total_tasks', 0) > 0
            }

            return coverage_report

        except Exception as e:
            self.logger.warning(f"Failed to generate coverage report: {e}")
            return {
                "status": "coverage_report_error",
                "error": str(e)
            }