# rvandroid/experiment/task_components.py
import logging
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


class StaticAnalysisComponent:
    """
    Component responsible for handling static analysis data loading.
    Separates this concern from the main TaskExecutor.
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

    def load_static_data(self, task_context: Dict[str, Any]) -> bool:
        """
        Load static analysis data for the task.

        Args:
            task_context: Context information about the task

        Returns:
            Success status
        """
        if self.task.static_data:
            self.logger.debug("Static data already loaded")
            return True

        try:
            self.logger.info("Loading static analysis data")

            self.task.static_data = static_analysis_parser.read_static_analysis_files(
                self.task.results_dir,
                self.task.config.apk_name,
                self.task.app.package_name
            )

            if self.task.static_data:
                self.logger.info("Static analysis data loaded successfully")

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
                self.logger.warning("No static analysis data found, coverage tracking will be limited")
                return False

        except Exception as e:
            self.logger.warning(f"Error loading static data: {e}")
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
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.coverage_tracker = None

    def initialize_tracker(self) -> bool:
        """
        Initialize the coverage tracker.

        Returns:
            Success status
        """
        try:
            self.coverage_tracker = CoverageTracker(
                logcat_file=self.task.result.logcat_file,
                static_data=self.task.static_data
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize coverage tracker: {e}")
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
        if not self.coverage_tracker:
            self.logger.error("Cannot start tracking: tracker not initialized")
            return False

        try:
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
            self.logger.error(f"Failed to start coverage tracking: {e}")
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
        if not self.coverage_tracker:
            return True

        try:
            self.coverage_tracker.stop()

            # Publish event
            if self.event_bus:
                self.event_bus.publish_analysis_event(
                    EventType.COVERAGE_TRACKING_STOPPED,
                    related_task_id=self.task.id,
                    source="CoverageComponent"
                )
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop coverage tracking: {e}")
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
        if not self.coverage_tracker:
            self.logger.warning("No coverage tracker available to process coverage data")
            return False

        try:
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

            return True

        except Exception as e:
            self.logger.error(f"Error processing coverage data: {e}")
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
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.emulator_manager = EmulatorManager()

    def start_emulator(self, avd_name: str = "RVSec") -> Any:
        """
        Start the emulator and return a context manager.

        Args:
            avd_name: Name of the AVD to start

        Returns:
            Context manager for emulator session
        """
        try:
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
            self.logger.error(f"Failed to start emulator: {e}")
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
        if self.task.config.skip_installation:
            self.logger.info("Skipping app installation as requested")
            return True

        try:
            self.emulator_manager.install_app(app)

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
            self.logger.error(f"Failed to install app {app.name}: {e}")
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
        try:
            return self.emulator_manager.clear_logcat()
        except Exception as e:
            self.logger.warning(f"Error clearing logcat: {e}")
            # Non-critical error, just log
            return False


class LogcatComponent:
    """
    Component responsible for managing logcat operations.
    Handles logcat capture and filtering.
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logcat_manager = LogcatManager()

    def start_capture(self) -> bool:
        """
        Start capturing logcat output.

        Returns:
            Success status
        """
        try:
            result = self.logcat_manager.start_capture(
                self.task.result.logcat_file,
                clear_buffer=self.task.config.clean_logcat
            )

            if result:
                self.logger.info(f"Logcat capture started to {self.task.result.logcat_file}")
            else:
                self.logger.warning("Failed to start logcat capture")

            return result
        except Exception as e:
            self.logger.error(f"Error starting logcat capture: {e}")
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
        try:
            result = self.logcat_manager.stop_capture()
            if result:
                self.logger.info("Logcat capture stopped")
            else:
                self.logger.warning("Issues stopping logcat capture")
            return result
        except Exception as e:
            self.logger.warning(f"Error stopping logcat capture: {e}")
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
        self.logger = logging.getLogger(__name__)
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

    def execute_tool(self) -> bool:
        """
        Execute the tool on the current task.

        Returns:
            Success status
        """
        try:
            self.logger.info(f"Executing tool: {self.tool.name}")

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
            self.logger.error(f"Error executing tool {self.tool.name}: {e}")
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
        if hasattr(self.tool, 'process_pattern') and self.tool.process_pattern:
            try:
                self.tool.kill_related_processes(self.tool.process_pattern)
                self.logger.debug(f"Cleaned up processes for tool: {self.tool.name}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up tool processes: {e}")
