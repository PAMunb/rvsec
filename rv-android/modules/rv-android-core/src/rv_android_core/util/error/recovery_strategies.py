import logging
import os
import signal
from typing import Dict, Optional, Any

from rv_android_core.commands.command import Command
from rv_android_core.util.exceptions import ADBError, EmulatorError, RvTimeoutError


class RecoveryStrategies:
    """
    Standard recovery strategies for common error types.
    Provides reusable error recovery implementations.

    ### Architectural Decisions:
    - Centralizes recovery logic for common error types
    - Separates recovery implementation from error processing logic
    - Enables reuse of recovery strategies across the system
    """

    @staticmethod
    def handle_adb_error(error: ADBError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle ADB-related errors with retry mechanism.

        Args:
            error: The ADB error
            context: Optional context information

        Returns:
            True if handled successfully, False otherwise
        """
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Attempting to recover from ADB error: {error}")

            # Try to restart ADB server
            kill_cmd = Command("adb", ["kill-server"])
            start_cmd = Command("adb", ["start-server"])
            devices_cmd = Command("adb", ["devices"])

            # Execute commands with appropriate error handling
            kill_result = kill_cmd.invoke()
            start_result = start_cmd.invoke()
            devices_result = devices_cmd.invoke()

            # Log results
            logger.debug(f"ADB kill-server result: {kill_result.code}")
            logger.debug(f"ADB start-server result: {start_result.code}")
            logger.debug(f"ADB devices result: {devices_result.code}")

            # Consider recovery successful if commands execute without throwing an exception
            return True

        except Exception as e:
            logger.error(f"Error during ADB recovery: {e}", exc_info=True)
            return False

    @staticmethod
    def handle_emulator_error(error: EmulatorError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle emulator-related errors.

        Args:
            error: The emulator error
            context: Optional context information

        Returns:
            True if handled successfully, False otherwise
        """
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Handling emulator error: {error}")

            # Check if we have a device ID in the context
            device_id = context.get('device_id') if context else None

            if device_id:
                # Kill specific emulator instance
                kill_cmd = Command("adb", ["-s", device_id, "emu", "kill"])
                logger.debug(f"Killing emulator with device ID: {device_id}")
            else:
                # General emulator cleanup
                kill_cmd = Command("pkill", ["-f", "emulator"])
                logger.debug("Terminating all emulator processes")

            # Execute kill command
            kill_result = kill_cmd.invoke()
            logger.debug(f"Emulator kill command result: {kill_result.code}")

            return True

        except Exception as e:
            logger.error(f"Error during emulator recovery: {e}", exc_info=True)
            return False

    @staticmethod
    def handle_timeout_error(error: RvTimeoutError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle timeout errors.

        Args:
            error: The timeout error
            context: Optional context information

        Returns:
            True if handled successfully, False otherwise
        """
        logger = logging.getLogger(__name__)
        try:
            logger.info(f"Handling timeout error: {error}")

            # Check if we have a process in the context
            process = context.get('process') if context else None

            if process and hasattr(process, 'pid'):
                # Attempt to terminate the process
                os.kill(process.pid, signal.SIGTERM)
                logger.debug(f"Terminated process with PID: {process.pid}")
                return True

            logger.warning("No process found for timeout termination")
            return False

        except Exception as e:
            logger.error(f"Error during timeout error recovery: {e}", exc_info=True)
            return False
