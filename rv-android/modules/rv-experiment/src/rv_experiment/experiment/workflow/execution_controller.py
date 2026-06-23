"""
Execution controller for RV-Android experiments.

Coordinate experiment execution through rv-platform, translating experiment
configuration into platform configuration and delegating all task execution
and result processing to the platform layer.
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
    """Coordinate experiment execution through rv-platform.

    ### Role in the System:
    Bridge between rv-experiment orchestration and rv-platform execution.
    Translate ExperimentConfig parameters into PlatformConfig, initialize the
    Platform instance, and delegate all task execution and result processing.

    ### Architectural Decisions:
    - No data transfer back to rv-experiment. Results remain in rv-platform;
      this controller only tracks success/failure status.
    - Device port injection into tool parameters enables parallel execution
      across multiple emulator instances.
    - Falls back to original APK directory when instrumented directory is
      empty (supports skip-instrument workflows).

    ### Key Features:
    - Two-step lifecycle: setup() configures platform, run() executes tasks
    - Automatic device_port injection for parallel container execution
    - Execution statistics collection without cross-module data transfer

    ### Integration Points:
    - PlatformConfig: Configuration translation target for rv-platform
    - Platform: Execution engine handling tasks and result processing
    - ExperimentConfig: Source configuration from rv-experiment
    """

    @ErrorHandler.handle_errors(component="ExecutionController", phase="initialization")
    def __init__(self, config: ExperimentConfig):
        """Initialize execution controller for platform coordination.

        Args:
            config: Experiment configuration providing APK paths, tool configs,
                timeouts, device port, and processing flags

        State:
            config: Experiment configuration instance
            platform: Platform instance, set by setup()
            platform_config: PlatformConfig instance, set by setup()
            has_errors: True if any task failed during execution
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

        # Platform integration state — set by setup(), consumed by run().
        # This two-step lifecycle exists because setup() needs APK/tool info
        # that is only available after Phase 1 (pre-processing) completes.
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
        """Configure rv-platform for experiment execution.

        Create PlatformConfig from experiment parameters and initialize the
        Platform instance. Must be called before run().

        Args:
            apks: Application objects to test (instrumented or original)
            repetitions: Number of repetitions per APK/tool/timeout combination
            timeouts: Timeout values in seconds for task execution
            tools: Tool instances created by ToolFactory
            tool_configs: Original ToolConfig list with variant info. When
                provided, used instead of deriving configs from tool instances.
            no_window: Run emulator in headless mode
            results_dir: Directory for storing platform results
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
        """Execute experiment tasks through rv-platform.

        Delegate complete execution to Platform.run(), which handles emulator
        lifecycle, tool execution, and result processing. Only success/failure
        status is tracked locally.

        Returns:
            True if all tasks completed successfully, False if any task failed

        Raises:
            RVExperimentExecutionError: If setup() was not called or platform
                execution raises an unrecoverable error
        """
        if not self.platform or not self.platform_config:
            raise RVExperimentExecutionError(
                "Execution controller not properly set up. Call setup() first."
            )

        with self.logger.with_context(phase="execution"):
            self.logger.info(LOG_START.format(phase="platform execution"))

            try:
                # Execute through rv-platform. Platform.run() is the single point of control
                # for the entire execution lifecycle: task generation, emulator management,
                # tool execution, logcat capture, coverage tracking, and CSV/JSON results.
                # On resume, it loads tasks.json and skips already-completed tasks.
                results = self.platform.run()

                # Only success/failure status crosses the module boundary.
                # Detailed results (CSV, coverage, MOP violations) remain in rv-platform's
                # results directory — rv-experiment never reads or transforms them.
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
        """Translate experiment parameters into PlatformConfig.

        Build platform tool configurations by copying ToolConfig instances
        and injecting device_port for parallel execution. Determine APK
        directory with fallback from instrumented to original APKs.

        Args:
            apks: Application objects to test
            repetitions: Number of execution repetitions
            timeouts: Timeout values in seconds
            tools: Tool instances (used as fallback when tool_configs is None)
            tool_configs: Original ToolConfig list with variant info
            no_window: Headless emulator execution flag
            results_dir: Platform results directory path

        Returns:
            PlatformConfig configured for experiment execution
        """
        # Use the experiment results directory as the platform results directory.
        # Both rv-experiment and rv-platform write to the same flat directory
        # (e.g., results/my_exp/), so tasks.json, CSV reports, and experiment
        # config all coexist in one location for easy inspection.
        platform_results_dir = results_dir

        # Prefer instrumented APKs produced by Phase 1.
        # Falls back to original APKs when instrumentation was skipped (--skip-instrument
        # or resume mode). This fallback is critical: without it, the platform would
        # fail to find APKs when pre-processing is disabled.
        apks_dir = os.path.join(self.config.output_dir, INSTRUMENTED_APKS_DIR)
        if not os.path.exists(apks_dir) or not os.listdir(apks_dir):
            apks_dir = self.config.apks_dir

        # Build platform tool configurations from experiment tool configs.
        # Both rv-experiment and rv-platform use the same ToolConfig from rv-android-core,
        # so no conversion is needed — just inject device_port into a copy of parameters.
        #
        # Prefer tool_configs over tool instances because ToolConfig carries variant
        # metadata that tool instances may not expose. The fallback (deriving configs
        # from tool instances) exists for programmatic callers that skip the CLI layer.
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

            # Inject device_port into tool parameters for parallel container execution.
            # In Docker-based batch runs, each container gets a unique emulator port
            # (e.g., 5554, 5556, 5558). Tools need this to connect to the right
            # emulator instance via ADB. The three keys (device_port, device_serial,
            # device_id) cover different tool conventions for device addressing.
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
            logcat_diagnostics=self.config.logcat_diagnostics,
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
        """Get execution statistics from platform integration.

        Returns:
            Dictionary with keys:
                - status: "not_executed" if platform was never run
                - execution_method: Always "rv_platform_integration"
                - has_errors: Whether any task failed
                - platform_results_dir: Path to platform results directory
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
        """Get coverage report summary from platform execution.

        Returns:
            Dictionary with keys:
                - status: "no_execution_data" or "coverage_report_error"
                - coverage_source: Always "rv_platform_integration"
                - has_coverage_data: True if execution had no errors
                - results_location: Path to platform results directory
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
