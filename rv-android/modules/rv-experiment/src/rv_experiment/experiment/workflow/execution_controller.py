"""
Execution controller for RV-Android experiments using rv-platform integration.

This module implements the execution coordination system that orchestrates experiment
execution through rv-platform with clean separation of concerns.
"""

import os
from typing import Any, Dict, List

from rv_android_core.domain.app import App
from rv_android_core.domain.task import ToolConfig
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVExperimentExecutionError
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig
from rv_experiment.constants import INSTRUMENTED_APKS_DIR
from rv_platform.config.platform_config import PlatformConfig

# Import rv-platform components
from rv_platform.platform import Platform


class ExecutionController:
    """
    Clean execution controller that coordinates experiment execution through rv-platform.

    This controller provides a clean interface between rv-experiment's orchestration
    and rv-platform's execution engine. It eliminates data transfer between modules
    and maintains clear separation of concerns.

    ### Architectural Role:
    - Translates experiment configurations to platform configurations
    - Coordinates experiment execution through rv-platform
    - Provides execution statistics without data transfer

    ### Key Principles:
    - No data transfer between rv-platform and rv-experiment
    - rv-platform handles all task execution and result processing
    - rv-experiment provides only orchestration and coordination
    - Clean separation of concerns with no architectural compromises
    """

    @ErrorHandler.handle_errors(component="ExecutionController", phase="initialization")
    def __init__(self, config: ExperimentConfig):
        """
        Initialize the execution controller with clean platform integration.

        Args:
            config: Experiment configuration with orchestration parameters
        """
        self.config = config

        # Configure logging and error handling using unified rv-android-core infrastructure
        # Ensures consistent logging context across experiment and platform layers
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.experiment.workflow.execution_controller",
            {CONTEXT_COMPONENT: "ExecutionController"},
        )

        # Platform integration state for clean coordination
        # Platform instance handles all task execution and result processing
        self.platform = None
        self.platform_config = None
        self.has_errors = False

        self.logger.info("ExecutionController initialized")

    @ErrorHandler.handle_errors(component="ExecutionController", phase="setup")
    def setup(
        self,
        apks: List[App],
        repetitions: int,
        timeouts: List[int],
        tools: List[AbstractTool],
        tool_configs: List = None,
        no_window: bool = False,
        results_dir: str = None,
    ):
        """
        Set up experiment execution by configuring rv-platform integration.

        Args:
            apks: List of application objects to test
            repetitions: Number of repetitions for each task
            timeouts: List of timeout values for task execution
            tools: List of testing tools for experiment execution
            tool_configs: List of original tool configurations with variant info
            no_window: Whether to run emulator in headless mode
            results_dir: Directory for storing results
        """
        with self.logger.with_context(
            apks=[app.name for app in apks],
            repetitions=repetitions,
            timeouts=timeouts,
            tools=[tool.name for tool in tools],
            no_window=no_window,
            phase="setup",
        ):
            self.logger.info(LOG_START.format(phase="execution setup"))

            # Create platform configuration from experiment parameters
            self.platform_config = self._create_platform_config(
                apks, repetitions, timeouts, tools, tool_configs, no_window, results_dir
            )

            # Initialize platform
            self.platform = Platform(self.platform_config)

            self.logger.info(LOG_COMPLETE.format(phase="execution setup"))

    @ErrorHandler.handle_errors(component="ExecutionController", phase="execution")
    def run(self) -> bool:
        """
        Execute experiment tasks through rv-platform coordination.

        This method delegates complete execution to rv-platform including
        task execution and result processing. No data is transferred back
        to rv-experiment.

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
                # Execute through rv-platform (includes automatic result processing)
                results = self.platform.run()

                # Track execution results (no data transfer)
                self.has_errors = results.get("failed_tasks", 0) > 0

                # Log execution statistics
                self.logger.info(
                    f"Platform execution completed: {results['total_tasks']} tasks, "
                    f"{results['successful_tasks']} successful, "
                    f"{results['failed_tasks']} failed"
                )

                success = not self.has_errors
                self.logger.info(LOG_COMPLETE.format(phase="platform execution"))

                return success

            except Exception as e:
                self.has_errors = True
                self.logger.error(
                    LOG_ERROR.format(phase="platform execution", error=str(e))
                )
                raise RVExperimentExecutionError(
                    f"Platform execution failed: {e}"
                ) from e

    @ErrorHandler.handle_errors(
        component="ExecutionController", phase="platform_config_creation"
    )
    def _create_platform_config(
        self,
        apks: List[App],
        repetitions: int,
        timeouts: List[int],
        tools: List[AbstractTool],
        tool_configs: List = None,
        no_window: bool = False,
        results_dir: str = None,
    ) -> PlatformConfig:
        """
        Create platform configuration from experiment parameters.

        Args:
            apks: List of application objects
            repetitions: Number of execution repetitions
            timeouts: List of timeout values
            tools: List of testing tools
            tool_configs: List of original tool configurations with variant info
            no_window: Headless execution flag
            results_dir: Directory for storing results

        Returns:
            PlatformConfig configured for experiment execution
        """
        # Use provided results directory (should be the experiment results directory)
        platform_results_dir = results_dir

        # Use instrumented APKs directory from experiment output_dir
        apks_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)

        # Fallback to original APKs if instrumented directory doesn't exist
        if not os.path.exists(apks_dir) or not os.listdir(apks_dir):
            apks_dir = self.config.apks_dir

        # Build platform tool configurations from experiment tool configs.
        # Both rv-experiment and rv-platform use the same ToolConfig class from rv-android-core,
        # so no conversion is needed — just inject device_port into a copy of parameters.
        platform_tools = []

        source_configs = (
            tool_configs
            if tool_configs
            else [
                ToolConfig(
                    name=tool.name,
                    variant=getattr(tool, "variant", "default"),
                    parameters=getattr(tool, "parameters", {}),
                )
                for tool in tools
            ]
        )

        for original_config in source_configs:
            params = dict(original_config.parameters)

            # Inject device_port into tool parameters for parallel execution
            if self.config.device_port is not None:
                params["device_port"] = self.config.device_port
                params["device_serial"] = f"emulator-{self.config.device_port}"
                params["device_id"] = f"emulator-{self.config.device_port}"

            platform_tools.append(
                ToolConfig(
                    name=original_config.name,
                    variant=original_config.variant,
                    parameters=params,
                )
            )

        # Create platform configuration
        platform_config = PlatformConfig(
            apks_dir=apks_dir,
            tools=platform_tools,
            repetitions=repetitions,
            timeouts=timeouts,
            results_dir=platform_results_dir,
            no_window=no_window,
            log_level="INFO",
            apks_filter_file=self.config.apks_filter,
        )

        self.logger.info(
            f"Created platform configuration: {len(platform_tools)} tools, "
            f"{repetitions} repetitions, {len(timeouts)} timeouts"
        )

        return platform_config

    @ErrorHandler.handle_errors(
        component="ExecutionController", phase="statistics_collection"
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
                "has_errors": self.has_errors,
            }

        # Get basic execution statistics (no detailed data)
        stats = {
            "execution_method": "rv_platform_integration",
            "has_errors": self.has_errors,
            "platform_results_dir": (
                self.platform_config.results_dir if self.platform_config else None
            ),
        }

        return stats

    @ErrorHandler.handle_errors(
        component="ExecutionController", phase="coverage_report_generation"
    )
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get coverage report summary from platform execution.

        Returns:
            Dictionary containing coverage summary information
        """
        if not self.platform:
            return {"status": "no_execution_data"}

        try:
            coverage_report = {
                "coverage_source": "rv_platform_integration",
                "has_coverage_data": not self.has_errors,
                "results_location": (
                    self.platform_config.results_dir if self.platform_config else None
                ),
            }

            return coverage_report

        except Exception as e:
            self.logger.warning(f"Failed to generate coverage report: {e}")
            return {"status": "coverage_report_error", "error": str(e)}
