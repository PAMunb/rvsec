# rv_platform/components/logcat.py
"""
Logcat component for RV-Platform.

Manages logcat capture and filtering during task execution.
"""

from typing import Dict, Any

from rv_android_core.util.error.exceptions import AnalysisError
from rv_android_core.util.android.logcat_manager import LogcatManager
from rv_android_core.util.logging.constants import (
    CONTEXT_TASK_ID, 
    CONTEXT_APP_NAME, 
    LOG_START,
    LOG_COMPLETE, 
    LOG_ERROR
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.domain.task import Task


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

    def __init__(self, task: Task):
        """Initialize with task."""
        self.name = "LogcatComponent"
        self.task = task
        self.error_handler = ErrorHandler.get_instance()
        
        # Get device_serial from task configuration for parallel execution
        device_serial = getattr(task.config, 'device_id', 'emulator-5554')
        if hasattr(task.config, 'tool_config') and hasattr(task.config.tool_config, 'additional_params'):
            device_serial = task.config.tool_config.additional_params.get('device_serial', device_serial)
        
        self.logcat_manager = LogcatManager(device_serial=device_serial)

        # Initialize logging with task context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_platform.components.logcat',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name
            }
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
        # LogcatComponent execution is handled by _run_emulator_session
        # This method just indicates the component is ready
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
                phase="start_capture"
        ):
            try:
                self.logger.info(LOG_START.format(
                    phase=f"logcat capture to {self.task.result.logcat_file}"
                ))

                result = self.logcat_manager.start_capture(
                    self.task.result.logcat_file,
                    clear_buffer=self.task.config.clean_logcat
                )

                if result:
                    self.logger.info(LOG_COMPLETE.format(
                        phase=f"starting logcat capture to {self.task.result.logcat_file}"
                    ))
                else:
                    self.logger.warning("Failed to start logcat capture")

                return result

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="starting logcat capture",
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
                self.logger.info(LOG_START.format(phase="stopping logcat capture"))
                result = self.logcat_manager.stop_capture()

                if result:
                    self.logger.info(LOG_COMPLETE.format(phase="stopping logcat capture"))
                else:
                    self.logger.warning("Issues stopping logcat capture")

                return result

            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    phase="stopping logcat capture",
                    error=str(e)
                ))
                return False