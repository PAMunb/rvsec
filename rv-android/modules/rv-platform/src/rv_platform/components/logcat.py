# rv_platform/components/logcat.py
"""
Logcat component for RV-Platform.

Manages logcat capture and filtering during task execution.
"""

from typing import Any, Dict

from rv_android_core.domain.task import Task
from rv_android_core.util.android.logcat_manager import DIAGNOSTIC_TAGS, LogcatManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import AnalysisError
from rv_android_core.util.logging.constants import (
    CONTEXT_APP_NAME,
    CONTEXT_TASK_ID,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager


class LogcatComponent:
    """
    Component responsible for managing logcat operations in rv-platform.
    Handles logcat capture and filtering.

    ### Architectural Decisions:
    - Encapsulates logcat management functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for logcat operations

    ### Role in the System:
    - Manages logcat capture during task execution
    - Ensures proper logcat lifecycle management
    - Provides a clean interface for logcat operations
    """

    def __init__(self, task: Task, logcat_diagnostics: bool = False):
        """Initialize with task.

        Args:
            task: The task whose logcat is captured.
            logcat_diagnostics: When True, augment the capture tag filter with the
                diagnostic tags (crashes/VerifyError/ANR). Default False keeps the
                baseline RVSEC/RVSEC-COV command byte-identical (INV-PLT-21).
        """
        self.name = "LogcatComponent"
        self.task = task
        self.logcat_diagnostics = logcat_diagnostics
        self.error_handler = ErrorHandler.get_instance()

        # Resolve which emulator instance to capture logcat from. In parallel
        # execution, each container runs its own emulator on a unique port, so
        # device_serial is "emulator-5554", "emulator-5556", etc. LogcatManager
        # uses `adb -s <serial> logcat` to target the correct device.
        device_serial = getattr(task.config, "device_id", "emulator-5554")
        if hasattr(task.config, "tool_config") and hasattr(
            task.config.tool_config, "parameters"
        ):
            device_serial = task.config.tool_config.parameters.get(
                "device_serial", device_serial
            )

        self.logcat_manager = LogcatManager(device_serial=device_serial)

        # Initialize logging with task context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.components.logcat",
            {CONTEXT_TASK_ID: task.id, CONTEXT_APP_NAME: task.config.apk_name},
        )

    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize the logcat component.

        Args:
            context: Task execution context
        """
        self.logger.debug("Initializing LogcatComponent")

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute logcat setup for the task.
        This method is called during preparation phase, not during emulator session.

        Args:
            context: Task execution context

        Returns:
            True if logcat component is ready
        """
        # No-op during the generic component execution phase, same pattern as
        # EmulatorComponent. Actual logcat capture is controlled directly by
        # TaskExecutor._run_emulator_session() via start_capture()/stop_capture(),
        # because logcat must start AFTER the emulator boots and stop AFTER the
        # tool finishes. The captured logcat file is persisted in tasks.json and
        # serves as the reconstruction source for MOP violations on resume.
        self.logger.info("LogcatComponent prepared for execution")
        return True

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up logcat resources.

        Args:
            context: Task execution context
        """
        self.logger.debug("Cleaning up LogcatComponent")
        try:
            self.stop_capture()
        except Exception as e:
            self.logger.warning(f"Error during logcat cleanup: {e}")

    def start_capture(self) -> bool:
        """
        Start capturing logcat output.

        Returns:
            Success status
        """
        with self.logger.with_context(
            output_file=self.task.result.logcat_file,
            clear_buffer=self.task.config.clean_logcat,
            phase="start_capture",
        ):
            try:
                self.logger.info(
                    LOG_START.format(
                        phase=f"logcat capture to {self.task.result.logcat_file}"
                    )
                )

                # When diagnostics are enabled, append the diagnostic tags to the
                # baseline; otherwise pass nothing so LogcatManager emits the
                # byte-identical baseline command (INV-PLT-21).
                tags = None
                if self.logcat_diagnostics:
                    tags = self.logcat_manager.default_tags + DIAGNOSTIC_TAGS

                result = self.logcat_manager.start_capture(
                    self.task.result.logcat_file,
                    tags=tags,
                    clear_buffer=self.task.config.clean_logcat,
                )

                if result:
                    self.logger.info(
                        LOG_COMPLETE.format(
                            phase=f"starting logcat capture to {self.task.result.logcat_file}"
                        )
                    )
                else:
                    self.logger.warning("Failed to start logcat capture")

                return result

            except Exception as e:
                self.logger.error(
                    LOG_ERROR.format(phase="starting logcat capture", error=str(e))
                )
                self.error_handler.handle_error(
                    AnalysisError("Failed to start logcat capture", e),
                    {"task_id": self.task.id},
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
                self.logger.info(LOG_START.format(phase="stopping logcat capture"))
                result = self.logcat_manager.stop_capture()

                if result:
                    self.logger.info(
                        LOG_COMPLETE.format(phase="stopping logcat capture")
                    )
                else:
                    self.logger.warning("Issues stopping logcat capture")

                return result

            except Exception as e:
                self.logger.warning(
                    LOG_ERROR.format(phase="stopping logcat capture", error=str(e))
                )
                return False
