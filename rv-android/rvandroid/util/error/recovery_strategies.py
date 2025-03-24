# rvandroid/util/error/recovery_strategies.py
import logging
import os
import signal
import time
from typing import Dict, Optional, Any

from rvandroid.commands.command import Command
from rvandroid.util.exceptions import ADBError, EmulatorError, RvTimeoutError
from rvandroid.util.logging.manager import LoggingManager


class RecoveryStrategies:
    """
    Standard recovery strategies for common error types.
    Provides reusable error recovery implementations.

    ### Architectural Decisions:
    - Centralizes recovery logic for common error types
    - Separates recovery implementation from error processing logic
    - Enables reuse of recovery strategies across the system

    ### Role in the System:
    - Implements standard recovery procedures for common errors
    - Provides consistent error recovery behavior
    - Enables centralized improvement of recovery strategies
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
        with LoggingManager.get_instance().get_logger(
                'util.error.recovery_strategies'
        ).with_context(phase="adb_error_recovery"):
            logger.info(f"Attempting to recover from ADB error: {error.message}")

            # Try to restart ADB server
            try:
                # Kill ADB server
                kill_cmd = Command("adb", ["kill-server"])
                kill_cmd.invoke()
                logger.info("ADB server killed")

                # Wait a moment
                time.sleep(2)

                # Start ADB server
                start_cmd = Command("adb", ["start-server"])
                start_cmd.invoke()
                logger.info("ADB server restarted")

                # Wait for devices
                devices_cmd = Command("adb", ["devices"])
                devices_cmd.invoke()

                logger.info("ADB recovery successful")
                return True

            except Exception as e:
                logger.error(f"Error during ADB recovery: {e}")
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
        with LoggingManager.get_instance().get_logger(
                'util.error.recovery_strategies'
        ).with_context(phase="emulator_error_recovery"):
            logger.info(f"Handling emulator error: {error.message}")

            # Check if we have a device ID in the context
            device_id = None
            if context and "device_id" in context:
                device_id = context["device_id"]

            try:
                # Try to kill any existing emulator processes

                # Kill running emulator instance if we have a device ID
                if device_id:
                    kill_cmd = Command("adb", ["-s", device_id, "emu", "kill"])
                    kill_cmd.invoke()
                    logger.info(f"Emulator {device_id} killed")
                else:
                    # General emulator cleanup
                    kill_all_cmd = Command("pkill", ["-f", "emulator"])
                    kill_all_cmd.invoke()
                    logger.info("All emulator processes terminated")

                return True
            except Exception as e:
                logger.error(f"Error during emulator recovery: {e}")
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
        with LoggingManager.get_instance().get_logger(
                'util.error.recovery_strategies'
        ).with_context(phase="timeout_error_recovery"):
            logger.info(f"Handling timeout error: {error.message}")

            # Examine context to determine timeout type
            if context and "process" in context:
                # Handle process timeout
                process = context["process"]
                try:
                    # Try to terminate the process
                    if hasattr(process, "pid"):
                        os.kill(process.pid, signal.SIGTERM)
                        logger.info(f"Process {process.pid} terminated due to timeout")
                        return True
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")

            # Log unhandled timeout
            logger.warning(f"No specific handling for timeout error: {error.message}")
            return False
       