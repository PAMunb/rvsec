# rvandroid/experiment/task_components.py
from typing import Dict, Any, Optional

from rvandroid.analysis.coverage_tracker import CoverageTracker
from rvandroid.app import App
from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.experiment.task_model import Task
from rvandroid.model.coverage import LogcatRepository
from rvandroid.parser.static import static_analysis_parser
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.emulator_manager import EmulatorManager
from rvandroid.util.error_handler import ErrorHandler
from rvandroid.util.exceptions import AnalysisError, EmulatorError, ToolError
from rvandroid.util.logcat_manager import LogcatManager
from rvandroid.util.logging_manager import LoggingManager


class StaticAnalysisComponent:
    """
    Component responsible for handling static analysis data loading.
    Separates this concern from the main TaskExecutor.
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.static_analysis',
            {
                LoggingManager.CONTEXT_TASK_ID: task.id,
                LoggingManager.CONTEXT_APP_NAME: task.config.apk_name,
                LoggingManager.CONTEXT_COMPONENT: 'StaticAnalysisComponent'
            }
        )

    def load_static_data(self, task_context: Dict[str, Any]) -> bool:
        """
        Load static analysis data for the task.

        Args:
            task_context: Context information about the task

        Returns:
            Success status
        """
        with self.logger.with_context(phase="load_static_data"):
            if self.task.static_data:
                self.logger.debug("Static data already loaded")
                return True

            try:
                self.logger.info(LoggingManager.LOG_START.format(operation="loading static analysis data"))

                self.task.static_data = static_analysis_parser.read_static_analysis_files(
                    self.task.results_dir,
                    self.task.config.apk_name,
                    self.task.app.package_name
                )

                if self.task.static_data:
                    self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="loading static analysis data"))

                    # Publish event
                    if self.event_bus:
                        self.event_bus.publish_analysis_event(
                            EventType.STATIC_ANALYSIS_COMPLETED,
                            data={"app_name": self.task.app.name},
                            related_task_id=self.task.id,
                            source="StaticAnalysisComponent"
                        )
                    return True
                else:
                    self.logger.warning(LoggingManager.LOG_SKIPPED.format(
                        operation="static analysis data loading",
                        reason="No data found, coverage tracking will be limited"
                    ))
                    return False

            except Exception as e:
                self.logger.warning(LoggingManager.LOG_ERROR.format(
                    operation="loading static data",
                    error=str(e)
                ))
                # Convert to AnalysisError but don't raise
                self.error_handler.handle_error(
                    AnalysisError("Failed to load static analysis data", e),
                    task_context
                )
                return False


class CoverageComponent:
    """
    Component responsible for managing coverage tracking and analysis.
    Handles coverage tracker lifecycle and result processing.
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.coverage_tracker = None

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.coverage',
            {
                LoggingManager.CONTEXT_TASK_ID: task.id,
                LoggingManager.CONTEXT_APP_NAME: task.config.apk_name,
                LoggingManager.CONTEXT_COMPONENT: 'CoverageComponent'
            }
        )

    def initialize_tracker(self) -> bool:
        """
        Initialize the coverage tracker.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="initialize_tracker"):
            try:
                self.logger.info(LoggingManager.LOG_START.format(operation="initializing coverage tracker"))
                self.coverage_tracker = CoverageTracker(
                    logcat_file=self.task.result.logcat_file,
                    static_data=self.task.static_data
                )
                self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="initializing coverage tracker"))
                return True
            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="initializing coverage tracker",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to initialize coverage tracker", e),
                    {"task_id": self.task.id}
                )
                return False

    def start_tracking(self) -> bool:
        """
        Start coverage tracking.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="start_tracking"):
            if not self.coverage_tracker:
                self.logger.error("Cannot start tracking: tracker not initialized")
                return False

            try:
                self.logger.info(LoggingManager.LOG_START.format(operation="coverage tracking"))
                self.coverage_tracker.start()

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_analysis_event(
                        EventType.COVERAGE_TRACKING_STARTED,
                        data={"logcat_file": self.task.result.logcat_file},
                        related_task_id=self.task.id,
                        source="CoverageComponent"
                    )
                return True
            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="starting coverage tracking",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to start coverage tracking", e),
                    {"task_id": self.task.id}
                )
                return False

    def stop_tracking(self) -> bool:
        """
        Stop coverage tracking.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="stop_tracking"):
            if not self.coverage_tracker:
                return True

            try:
                self.logger.info(LoggingManager.LOG_START.format(operation="stopping coverage tracking"))
                self.coverage_tracker.stop()
                self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="stopping coverage tracking"))

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_analysis_event(
                        EventType.COVERAGE_TRACKING_STOPPED,
                        related_task_id=self.task.id,
                        source="CoverageComponent"
                    )
                return True
            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="stopping coverage tracking",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to stop coverage tracking", e),
                    {"task_id": self.task.id}
                )
                return False

    def process_results(self) -> bool:
        """
        Process coverage results and update task metrics.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="process_results"):
            if not self.coverage_tracker:
                self.logger.warning(LoggingManager.LOG_SKIPPED.format(
                    operation="coverage data processing",
                    reason="No coverage tracker available"
                ))
                return False

            try:
                self.logger.info(LoggingManager.LOG_START.format(operation="processing coverage data"))

                # Get repository from coverage tracker
                repository = self.coverage_tracker.repository

                # Calculate metrics using the repository
                metrics = repository.calculate_metrics()
                metrics_dict = metrics.to_dict()

                # Update task result with metrics
                self.task.result.coverage_metrics.update({
                    "method_coverage": metrics_dict["method_coverage"],
                    "activities_coverage": metrics_dict["activity_coverage"],
                    "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
                    "total_errors": metrics_dict["unique_errors"],
                    "total_method_calls": metrics.called_methods
                })

                # Store the repository directly in the task
                self.task.repository = repository

                # Log coverage summary
                self.logger.info(
                    f"Final coverage: Methods: {metrics_dict['method_coverage']:.2f}%, "
                    f"Activities: {metrics_dict['activity_coverage']:.2f}%, "
                    f"MOP Methods: {metrics_dict['mop_method_coverage']:.2f}%, "
                    f"Errors: {metrics_dict['unique_errors']}"
                )

                # Publish coverage updated event
                if self.event_bus:
                    self.event_bus.publish_analysis_event(
                        EventType.COVERAGE_UPDATED,
                        data={"coverage_metrics": self.task.result.coverage_metrics},
                        related_task_id=self.task.id,
                        source="CoverageComponent"
                    )

                self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="processing coverage data"))
                return True

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="processing coverage data",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Coverage data processing failed", e),
                    {"task_id": self.task.id}
                )
                return False

    def get_repository(self) -> Optional[LogcatRepository]:
        """
        Get the coverage repository if available.

        Returns:
            LogcatRepository or None
        """
        if self.coverage_tracker:
            return self.coverage_tracker.repository
        return None


class EmulatorComponent:
    """
    Component responsible for managing emulator operations.
    Handles emulator lifecycle and app installation.
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.emulator_manager = EmulatorManager()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.emulator',
            {
                LoggingManager.CONTEXT_TASK_ID: task.id,
                LoggingManager.CONTEXT_APP_NAME: task.config.apk_name,
                LoggingManager.CONTEXT_COMPONENT: 'EmulatorComponent'
            }
        )

    def start_emulator(self, avd_name: str = "RVSec") -> Any:
        """
        Start the emulator and return a context manager.

        Args:
            avd_name: Name of the AVD to start

        Returns:
            Context manager for emulator session
        """
        with self.logger.with_context(avd_name=avd_name, phase="start_emulator"):
            try:
                self.logger.info(LoggingManager.LOG_START.format(operation=f"emulator {avd_name}"))

                # Get emulator context manager
                emulator_context = self.emulator_manager.start_emulator(
                    avd_name,
                    self.task.config.no_window
                )

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.EMULATOR_STARTED,
                        task_id=self.task.id,
                        details={"device_id": self.task.config.device_id},
                        source="EmulatorComponent"
                    )

                return emulator_context

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation=f"starting emulator {avd_name}",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    EmulatorError(f"Failed to start emulator {avd_name}", e),
                    {"task_id": self.task.id}
                )
                raise

    def install_app(self, android, app: App) -> bool:
        """
        Install the app on the emulator.

        Args:
            android: Android interface from emulator
            app: App to install

        Returns:
            Success status
        """
        with self.logger.with_context(phase="install_app"):
            if self.task.config.skip_installation:
                self.logger.info(LoggingManager.LOG_SKIPPED.format(
                    operation="app installation",
                    reason="skipped as requested in configuration"
                ))
                return True

            try:
                self.logger.info(LoggingManager.LOG_START.format(operation=f"installing app {app.name}"))
                self.emulator_manager.install_app(app)
                self.logger.info(LoggingManager.LOG_COMPLETE.format(operation=f"installing app {app.name}"))

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.APP_INSTALLED,
                        task_id=self.task.id,
                        details={"app_name": app.name},
                        source="EmulatorComponent"
                    )

                return True

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation=f"installing app {app.name}",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    EmulatorError(f"Failed to install app {app.name}", e),
                    {"task_id": self.task.id, "app_name": app.name}
                )
                return False

    def clean_logcat(self) -> bool:
        """
        Clear the logcat buffer.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="clean_logcat"):
            try:
                self.logger.debug(LoggingManager.LOG_START.format(operation="cleaning logcat buffer"))
                result = self.emulator_manager.clear_logcat()
                if result:
                    self.logger.debug(LoggingManager.LOG_COMPLETE.format(operation="cleaning logcat buffer"))
                return result
            except Exception as e:
                self.logger.warning(LoggingManager.LOG_ERROR.format(
                    operation="clearing logcat",
                    error=str(e)
                ))
                # Non-critical error, just log and continue
                return False


class LogcatComponent:
    """
    Component responsible for managing logcat operations.
    Handles logcat capture and filtering.
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logcat_manager = LogcatManager()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.logcat',
            {
                LoggingManager.CONTEXT_TASK_ID: task.id,
                LoggingManager.CONTEXT_APP_NAME: task.config.apk_name,
                LoggingManager.CONTEXT_COMPONENT: 'LogcatComponent'
            }
        )

    def start_capture(self) -> bool:
        """
        Start capturing logcat output.

        Returns:
            Success status
        """
        with self.logger.with_context(
                output_file=self.task.result.logcat_file,
                clear_buffer=self.task.config.clean_logcat,
                phase="start_capture"
        ):
            try:
                self.logger.info(LoggingManager.LOG_START.format(
                    operation=f"logcat capture to {self.task.result.logcat_file}"
                ))

                result = self.logcat_manager.start_capture(
                    self.task.result.logcat_file,
                    clear_buffer=self.task.config.clean_logcat
                )

                if result:
                    self.logger.info(LoggingManager.LOG_COMPLETE.format(
                        operation=f"starting logcat capture to {self.task.result.logcat_file}"
                    ))
                else:
                    self.logger.warning("Failed to start logcat capture")

                return result

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation="starting logcat capture",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to start logcat capture", e),
                    {"task_id": self.task.id}
                )
                return False

    def stop_capture(self) -> bool:
        """
        Stop logcat capture.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="stop_capture"):
            try:
                self.logger.info(LoggingManager.LOG_START.format(operation="stopping logcat capture"))
                result = self.logcat_manager.stop_capture()

                if result:
                    self.logger.info(LoggingManager.LOG_COMPLETE.format(operation="stopping logcat capture"))
                else:
                    self.logger.warning("Issues stopping logcat capture")

                return result

            except Exception as e:
                self.logger.warning(LoggingManager.LOG_ERROR.format(
                    operation="stopping logcat capture",
                    error=str(e)
                ))
                return False


class ToolExecutionComponent:
    """
    Component responsible for managing tool execution.
    Handles tool invocation and result processing.
    """

    def __init__(self, task: Task, tool: AbstractTool, event_bus: Optional[EventBus] = None):
        """Initialize with task, tool, and optional event bus."""
        self.task = task
        self.tool = tool
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.tool_execution',
            {
                LoggingManager.CONTEXT_TASK_ID: task.id,
                LoggingManager.CONTEXT_APP_NAME: task.config.apk_name,
                LoggingManager.CONTEXT_TOOL_NAME: tool.name,
                LoggingManager.CONTEXT_COMPONENT: 'ToolExecutionComponent'
            }
        )

    def execute_tool(self) -> bool:
        """
        Execute the tool on the current task.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="execute_tool"):
            try:
                self.logger.info(LoggingManager.LOG_START.format(operation=f"tool: {self.tool.name}"))

                # Publish tool started event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.TOOL_STARTED,
                        task_id=self.task.id,
                        details={"tool_name": self.tool.name},
                        source="ToolExecutionComponent"
                    )

                # Execute the tool
                self.tool.execute(self.task, self.task.app)
                self.logger.info(LoggingManager.LOG_COMPLETE.format(operation=f"tool: {self.tool.name}"))

                # Publish tool stopped event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.TOOL_STOPPED,
                        task_id=self.task.id,
                        details={"tool_name": self.tool.name},
                        source="ToolExecutionComponent"
                    )

                return True

            except Exception as e:
                self.logger.error(LoggingManager.LOG_ERROR.format(
                    operation=f"executing tool {self.tool.name}",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    ToolError(f"Error executing tool {self.tool.name}", self.tool.name, e),
                    {"task_id": self.task.id, "tool_name": self.tool.name}
                )

                # Publish tool failed event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.TASK_FAILED,
                        task_id=self.task.id,
                        details={
                            "tool_name": self.tool.name,
                            "error": str(e)
                        },
                        source="ToolExecutionComponent"
                    )

                return False

    def cleanup_processes(self) -> None:
        """Clean up any hanging processes related to the tool."""
        with self.logger.with_context(phase="cleanup_processes"):
            if hasattr(self.tool, 'process_pattern') and self.tool.process_pattern:
                try:
                    self.logger.debug(LoggingManager.LOG_START.format(
                        operation=f"cleaning up processes for tool: {self.tool.name}"
                    ))
                    self.tool.kill_related_processes(self.tool.process_pattern)
                    self.logger.debug(LoggingManager.LOG_COMPLETE.format(
                        operation=f"cleaning up processes for tool: {self.tool.name}"
                    ))
                except Exception as e:
                    self.logger.warning(LoggingManager.LOG_ERROR.format(
                        operation=f"cleaning up processes for tool: {self.tool.name}",
                        error=str(e)
                    ))
