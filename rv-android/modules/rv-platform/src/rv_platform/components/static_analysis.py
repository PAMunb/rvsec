# rv_platform/components/static_analysis.py
"""
Static analysis component for RV-Platform.

Handles static analysis data loading during task execution.
"""

import os
import shutil
from typing import Dict, Any, Optional

from rv_android_core.util.error.exceptions import AnalysisError
from rv_android_core.util.logging.constants import (
    CONTEXT_TASK_ID, 
    CONTEXT_APP_NAME, 
    LOG_START,
    LOG_COMPLETE, 
    LOG_SKIPPED, 
    LOG_ERROR
)
from rv_android_core.constants import EXTENSION_REACH, EXTENSION_GATOR, EXTENSION_GESDA, EXTENSION_METHODS
from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import EventType, EventChannel
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.domain.task import Task
from rv_static_analysis.parser.static import static_analysis_parser


class StaticAnalysisComponent:
    """
    Component responsible for handling static analysis data loading in rv-platform.
    Separates this concern from the main TaskExecutor.

    ### Architectural Decisions:
    - Encapsulates static analysis loading functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for analysis operations

    ### Role in the System:
    - Manages static analysis data loading for tasks
    - Reports analysis events to the event system
    - Provides a clean interface for static data operations
    """

    def __init__(self, task: Task, apks_dir: str, event_bus: Optional[EventBus] = None):
        """Initialize with task, APKs directory, and optional event bus."""
        self.name = "StaticAnalysisComponent"
        self.task = task
        self.apks_dir = apks_dir
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Initialize logging with task context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_platform.components.static_analysis',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name
            }
        )

    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize the static analysis component.
        
        Args:
            context: Task execution context
        """
        self.logger.debug("Initializing StaticAnalysisComponent")

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute static analysis data loading for the task.
        
        Args:
            context: Task execution context
            
        Returns:
            True if static analysis data was loaded successfully
        """
        try:
            # First copy static analysis files from instrumented directory
            self.copy_static_analysis_files()
            
            if not self.load_static_data(context):
                # Static analysis failure is not critical for basic execution
                self.logger.warning("Static analysis data loading failed, continuing without static data")
            
            self.logger.info("Static analysis component completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Static analysis component execution failed: {e}")
            self.error_handler.handle_error(e, context)
            # Return True as static analysis is not critical
            return True

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up static analysis resources.
        
        Args:
            context: Task execution context
        """
        self.logger.debug("Cleaning up StaticAnalysisComponent")

    def load_static_data(self, task_context: Dict[str, Any]) -> bool:
        """
        Load static analysis data for the task.

        Args:
            task_context: Context information about the task

        Returns:
            Success status
        """
        with self.logger.with_context(phase="load_static_data"):
            if hasattr(self.task, 'static_data') and self.task.static_data:
                self.logger.debug("Static data already loaded")
                return True

            try:
                self.logger.info(LOG_START.format(phase="loading static analysis data"))

                # Load static analysis data
                static_data = static_analysis_parser.read_static_analysis_files(
                    self.task.results_dir,
                    self.task.config.apk_name,
                    self.task.app.code_package if self.task.app else None
                )

                # Store static data in task
                self.task.static_data = static_data

                if static_data:
                    self.logger.info(LOG_COMPLETE.format(phase="loading static analysis data"))

                    # Publish event
                    if self.event_bus:
                        self.event_bus.publish_task_event(
                            EventType.STATIC_ANALYSIS_COMPLETED,
                            task_id=self.task.id,
                            details={"app_name": self.task.app.name if self.task.app else self.task.config.apk_name},
                            source="StaticAnalysisComponent",
                            channel=EventChannel.ANALYSIS
                        )
                    return True
                else:
                    self.logger.warning(LOG_SKIPPED.format(
                        phase="static analysis data loading",
                        reason="No data found, coverage tracking will be limited"
                    ))
                    return False

            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    phase="loading static data",
                    error=str(e)
                ))
                # Convert to AnalysisError but don't raise
                self.error_handler.handle_error(
                    AnalysisError("Failed to load static analysis data", e),
                    task_context
                )
                return False

    def copy_static_analysis_files(self) -> bool:
        """
        Copies static analysis files for current APK from APKs directory to results directory.
        
        Based on the original ExecutionManager.copy_static_analysis_files method.
        Copies files from the same directory where APKs are located to the task's results directory.
        This ensures APKs and their static analysis files are kept together.
        
        Returns:
            True if at least one file was copied, False otherwise
        """
        # Get the APKs directory (source) - where APKs and their static analysis files are located
        instrumented_dir = self.apks_dir
        apk_name = self.task.config.apk_name
        target_dir = self.task.results_dir
        
        self.logger.info(f"Copying static analysis files for {apk_name} to {target_dir}")
        
        # Extensions to copy, matching original ExecutionManager implementation
        extensions = [EXTENSION_METHODS, EXTENSION_GESDA, EXTENSION_GATOR, EXTENSION_REACH]
        copied_files = 0

        try:
            # Ensure the target directory exists
            os.makedirs(target_dir, exist_ok=True)

            for extension in extensions:
                file_name = f"{apk_name}{extension}"
                source_file_path = os.path.join(instrumented_dir, file_name)
                self.logger.debug(f"Checking file: {source_file_path}")

                if os.path.exists(source_file_path):
                    self.logger.debug(f"Copying {source_file_path} to {target_dir}")
                    shutil.copy(source_file_path, target_dir)
                    copied_files += 1
                else:
                    self.logger.debug(f"Static analysis file not found: {source_file_path}")

            if copied_files == 0:
                self.logger.warning(f"No static analysis files found for {apk_name} in {instrumented_dir}")
                return False

            self.logger.info(f"Successfully copied {copied_files} static analysis files for {apk_name}")
            return True

        except Exception as e:
            # Create error context for the error handler
            error_context = {
                "component": "StaticAnalysisComponent",
                "phase": "static_analysis_file_copy",
                "apk_name": apk_name,
                "source_directory": instrumented_dir,
                "target_directory": target_dir,
                "extensions_checked": extensions,
                "copied_files_count": copied_files
            }
            
            # Use ErrorHandler for proper exception handling
            self.error_handler.handle_error(e, error_context)
            
            # Log additional information
            self.logger.error(f"Error copying static analysis files for {apk_name}: {e}")
            return False