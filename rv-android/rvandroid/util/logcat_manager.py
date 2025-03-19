# rvandroid/util/logcat_manager.py
import logging
import os
from typing import List

from rvandroid.commands.command import Command


class LogcatManager:
    """
    Manages logcat operations for Android devices.

    ### Architectural Decisions:
    - Separates logcat concerns from task execution logic
    - Improves resource management with proper cleanup
    - Provides structured access to logcat data

    ### Role in the System:
    - Captures logcat output during test execution
    - Provides filtering for relevant log entries
    - Manages logcat process lifecycle
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logcat_process = None
        self.logcat_file_handle = None

    def start_capture(self, output_file: str, tags: List[str] = None, clear_buffer: bool = True) -> bool:
        """
        Start capturing logcat output to a file.

        Args:
            output_file: Path to write logcat output
            tags: Optional list of tags to filter (default: RVSEC, RVSEC-COV)
            clear_buffer: Whether to clear logcat buffer first

        Returns:
            True if capture started successfully, False otherwise
        """
        try:
            # Create output directory if needed
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Clear logcat buffer if requested
            if clear_buffer:
                clear_cmd = Command("adb", ["logcat", "-c"])
                clear_cmd.invoke()
                self.logger.debug("Cleared logcat buffer")

            # Default tags if none provided
            if not tags:
                tags = ["RVSEC", "RVSEC-COV"]

            # Build command with tag filters
            cmd_args = ["logcat", "-v", "threadtime"]
            if tags:
                cmd_args.extend(["-s"] + tags)

            # Start logcat capture
            logcat_cmd = Command("adb", cmd_args)
            log_file = open(output_file, "wb")

            try:
                self.logcat_process = logcat_cmd.invoke_as_deamon(stdout=log_file)
                self.logcat_file_handle = log_file
                self.logger.info(f"Logcat capture started to {output_file}")
                return True

            except Exception as e:
                # Close file handle if command fails
                log_file.close()
                self.logger.error(f"Failed to start logcat capture: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting up logcat capture: {e}")
            return False

    def stop_capture(self) -> bool:
        """
        Stop logcat capture and clean up resources.

        Returns:
            True if cleanup succeeded, False otherwise
        """
        success = True

        # Kill logcat process
        if self.logcat_process:
            try:
                self.logger.debug("Stopping logcat process")
                self.logcat_process.kill()
                self.logcat_process = None
            except Exception as e:
                self.logger.warning(f"Error stopping logcat process: {e}")
                success = False

        # Close logcat file handle
        if self.logcat_file_handle:
            try:
                self.logger.debug("Closing logcat file")
                self.logcat_file_handle.close()
                self.logcat_file_handle = None
            except Exception as e:
                self.logger.warning(f"Error closing logcat file: {e}")
                success = False

        return success
