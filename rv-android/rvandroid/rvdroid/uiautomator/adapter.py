"""
UIAutomator adapter for RVDroid.

This module provides a high-level interface for interacting with an Android device
using the uiautomator2 Python API, handling XML hierarchy retrieval, and UI interactions.
"""

import os
import time
from typing import Dict, Any, Optional, Tuple

import uiautomator2 as u2

from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.util.exceptions import ADBError, EmulatorError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class UIAutomator2Adapter:
    """
    Adapter for interacting with Android devices using the uiautomator2 Python API.

    Handles device connection, UI state retrieval, and interaction operations
    with robust error handling. Uses the RV-Android UIAutomator2 parser
    for screen state parsing.
    """

    def __init__(self, device_id: str = "emulator-5554"):
        """
        Initialize the UIAutomator adapter.

        Args:
            device_id: Device ID to connect to (defaults to emulator-5554)
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.uiautomator.adapter",
            {CONTEXT_COMPONENT: "UIAutomator2Adapter"}
        )

        self.device_id = device_id
        self.logger.info(f"Initializing UIAutomator adapter for device: {device_id}")

        # Initialize error handler
        from rvandroid.util.error.error_handler import ErrorHandler
        self.error_handler = ErrorHandler.get_instance()

        # Initialize parser
        self.parser = UIAutomator2Parser()

        # Try to stop any existing uiautomator services before connecting
        self._stop_existing_uiautomator()

        # Connect to the device
        try:
            self.device = u2.connect(device_id)
            self.logger.info(f"Connected to device: {device_id}")

            # Basic device info
            info = self.device.info
            self.logger.debug(f"Device info: {info}")
        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}")
            self.device = None

            # Fall back to a simpler connection method
            try:
                self.logger.info("Trying alternative connection method...")
                from rvandroid.commands.command import Command

                # Kill existing uiautomator processes
                kill_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "pkill -f uiautomator"
                ])
                kill_cmd.invoke()

                # Wait for processes to terminate
                time.sleep(2)

                # Connect again
                self.device = u2.connect(device_id)
                self.logger.info("Successfully connected using alternative method")
            except Exception as retry_error:
                self.logger.error(f"Alternative connection also failed: {retry_error}")
                raise ADBError(f"Failed to connect to device: {str(e)}", e)

        # Last state cache to avoid repeated fetches
        self._last_state = None
        self._last_state_time = 0
        self._state_cache_ttl = 0.5  # Cache state for 500ms

    def _stop_existing_uiautomator(self):
        """Stop any existing uiautomator services on the device."""
        try:
            from rvandroid.commands.command import Command

            # Check for running uiautomator processes
            ps_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "ps | grep uiautomator"
            ])
            result = ps_cmd.invoke()

            if result.stdout:
                self.logger.info("Found existing uiautomator processes, stopping them...")

                # Kill existing uiautomator processes
                kill_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "pkill -f uiautomator"
                ])
                kill_cmd.invoke()

                # Also try to kill the com.github.uiautomator process
                kill_app_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "am force-stop com.github.uiautomator"
                ])
                kill_app_cmd.invoke()

                # Wait for processes to terminate
                time.sleep(2)

        except Exception as e:
            self.logger.warning(f"Error stopping existing uiautomator services: {e}")

    def get_ui_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieve the current UI state from the device using uiautomator2.

        Args:
            force_refresh: Force a refresh regardless of cache status

        Returns:
            Dictionary containing UI state information including the XML hierarchy
        """
        # Check if we can use cached state
        current_time = time.time()
        if (not force_refresh and self._last_state and
                (current_time - self._last_state_time) < self._state_cache_ttl):
            return self._last_state

        try:
            if not self.device:
                raise ADBError("No connection to device")

            # Get current activity and package name
            current_app = self.device.app_current()
            package_name = current_app.get("package", "unknown")
            current_activity = current_app.get("activity", "unknown")

            self.logger.debug(f"Current package: {package_name}, activity: {current_activity}")

            # Get UI hierarchy as XML
            xml_content = self.device.dump_hierarchy(compressed=False)
            if not xml_content:
                raise ADBError("Failed to get UI hierarchy from device")

            self.logger.debug(f"Successfully retrieved UI hierarchy: {len(xml_content)} bytes")

            # Build state dictionary
            state = {
                "activity": current_activity,
                "package_name": package_name,
                "hierarchy": xml_content,
                "timestamp": current_time,
                "currentActivityName": current_activity
            }

            # Cache state
            self._last_state = state
            self._last_state_time = current_time

            return state

        except Exception as e:
            self.logger.error(f"Error getting UI state: {e}")
            raise ADBError(f"Failed to get UI state: {str(e)}", e)

    def ensure_app_in_foreground(self, package_name: str, max_attempts: int = 3) -> bool:
        """
        Ensure the target app is in the foreground, attempting to recover if it's not.

        Args:
            package_name: Package name of the app being tested
            max_attempts: Maximum number of recovery attempts

        Returns:
            True if app is in foreground, False if recovery failed
        """
        self.logger.debug(f"Ensuring app {package_name} is in foreground")

        # Check current foreground app
        current_package = self._get_foreground_package()

        if current_package == package_name:
            self.logger.debug(f"App {package_name} is already in foreground")
            return True

        # App is not in foreground, try to recover
        self.logger.warning(f"App {package_name} is not in foreground, current: {current_package}")

        for attempt in range(max_attempts):
            self.logger.info(f"Recovery attempt {attempt + 1}/{max_attempts}")

            # Try pressing back first (might be in a system dialog)
            if attempt == 0:
                self.logger.debug("Trying to press BACK to return to app")
                try:
                    self.press_key("BACK")
                    time.sleep(1)

                    # Check if we're back in the app
                    current_package = self._get_foreground_package()
                    if current_package == package_name:
                        self.logger.info(f"Successfully returned to app {package_name} after BACK press")
                        return True
                except Exception as e:
                    self.logger.warning(f"Error pressing BACK: {e}")

            # If BACK didn't work or this is a subsequent attempt, restart the app
            self.logger.debug(f"Trying to restart app {package_name}")
            try:
                # First stop the app
                self.stop_app(package_name)
                time.sleep(1)

                # Then start it again
                self.start_app(package_name)
                time.sleep(2)

                # Check if app is now in foreground
                current_package = self._get_foreground_package()
                if current_package == package_name:
                    self.logger.info(f"Successfully restarted app {package_name}")
                    return True
            except Exception as e:
                self.logger.error(f"Error restarting app: {e}")

        self.logger.error(f"Failed to bring app {package_name} to foreground after {max_attempts} attempts")
        return False

    def _get_foreground_package(self) -> str:
        """
        Get the package name of the foreground app.

        Returns:
            Package name or "unknown" if not determined
        """
        try:
            if self.device:
                current_app = self.device.app_current()
                return current_app.get("package", "unknown")

            # Fallback to ADB if uiautomator connection not available
            from rvandroid.commands.command import Command

            cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "dumpsys window windows | grep mCurrentFocus"
            ])
            result = cmd.invoke()
            output = result.stdout.decode('utf-8', errors='ignore')

            for line in output.splitlines():
                if "mCurrentFocus" in line and "/" in line:
                    parts = line.split(" ")
                    for part in parts:
                        if "/" in part:
                            return part.split("/")[0]

            return "unknown"
        except Exception as e:
            self.logger.warning(f"Error getting foreground package: {e}")
            return "unknown"

    def parse_screen(self, state: Dict[str, Any],
                     static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse the UI state into a structured screen description using RV-Android's parser.

        Args:
            state: UI state dictionary from get_ui_state()
            static_data: Optional static analysis data

        Returns:
            ScreenDescription object
        """
        # Extract the XML hierarchy from the state and pass it to the parser
        xml_data = state.get("hierarchy", "")
        if not xml_data:
            self.logger.error("No hierarchy XML found in state data")
            raise ValueError("No hierarchy XML found in state data")

        return self.parser.parse(xml_data, static_data)

    def click(self, x: int, y: int) -> bool:
        """
        Perform a click operation at the specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Clicking at coordinates: ({x}, {y})")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self.check_app_in_foreground()

            # Execute click operation via uiautomator2
            # self.device.click(x, y)
            # TODO voltar ao normal depois dos testes
            # Visual feedback for the click (draw a circle)
            try:
                # This shows a temporary red dot at the click location
                self.device.click(x, y, 0.1)  # The third parameter is duration
            except:
                # If visual feedback fails, perform normal click
                self.device.click(x, y)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error clicking at ({x}, {y}): {e}")
            raise ADBError(f"Failed to perform click: {str(e)}", e)

    def long_click(self, x: int, y: int, duration: int = 1000) -> bool:
        """
        Perform a long click operation at the specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of the long press in milliseconds

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Long clicking at coordinates: ({x}, {y}) for {duration}ms")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self.check_app_in_foreground()

            # Convert duration from milliseconds to seconds for uiautomator2
            duration_sec = duration / 1000.0

            # Execute long click operation via uiautomator2
            self.device.long_click(x, y, duration_sec)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error long clicking at ({x}, {y}): {e}")
            raise ADBError(f"Failed to perform long click: {str(e)}", e)

    def check_app_in_foreground(self):
        # Get the current state to check package name
        state = self.get_ui_state()
        package_name = state.get("package_name")
        # Verify app is in foreground before performing action
        if not self.ensure_app_in_foreground(package_name):
            raise ADBError(f"App {package_name} is not in foreground, cannot perform click")

    def input_text(self, text: str) -> bool:
        """
        Input text at the currently focused element.

        Args:
            text: Text to input

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Inputting text: {text}")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self.check_app_in_foreground()

            # Clear existing text and input new text using uiautomator2
            # First, try to find the focused element
            focused = self.device(focused=True)
            if focused.exists:
                focused.clear_text()
                focused.set_text(text)
            else:
                # If no focused element, use send_keys which types text at the current position
                self.device.clear_text()
                self.device.send_keys(text)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error inputting text: {e}")
            raise ADBError(f"Failed to input text: {str(e)}", e)

    def scroll(self, x: int, y: int, direction: str, distance: int = 400) -> bool:
        """
        Perform a scroll operation from the specified coordinates.

        Args:
            x: Starting X coordinate
            y: Starting Y coordinate
            direction: Direction to scroll (UP, DOWN, LEFT, RIGHT)
            distance: Distance to scroll in pixels

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Scrolling {direction} from coordinates: ({x}, {y}) for {distance}px")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self.check_app_in_foreground()

            # Calculate end coordinates based on direction
            if direction == "UP":
                end_x = x
                end_y = y - distance
            elif direction == "DOWN":
                end_x = x
                end_y = y + distance
            elif direction == "LEFT":
                end_x = x - distance
                end_y = y
            elif direction == "RIGHT":
                end_x = x + distance
                end_y = y
            else:
                self.logger.error(f"Invalid scroll direction: {direction}")
                return False

            # Execute swipe operation via uiautomator2
            self.device.swipe(x, y, end_x, end_y)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error scrolling {direction} from ({x}, {y}): {e}")
            raise ADBError(f"Failed to perform scroll: {str(e)}", e)

    def press_key(self, key_code: str) -> bool:
        """
        Press a key on the device.

        Args:
            key_code: Key code to press (e.g., BACK, HOME, MENU)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Pressing key: {key_code}")

            if not self.device:
                raise ADBError("No connection to device")

            # Map key names to uiautomator2 methods
            # Using the correct method names for uiautomator2
            if key_code.upper() == "BACK":
                self.device.press("back")  # This is the correct way to press back
            elif key_code.upper() == "HOME":
                self.device.press("home")
            elif key_code.upper() == "MENU":
                self.device.press("menu")
            elif key_code.upper() == "ENTER":
                self.device.press("enter")
            else:
                # For other keys, try to use the generic press method
                self.device.press(key_code.lower())

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error pressing key {key_code}: {e}")
            raise ADBError(f"Failed to press key: {str(e)}", e)

    def start_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        """
        Start an application on the device.

        Args:
            package_name: Application package name
            activity: Optional activity to start

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Starting app: {package_name}" + (f"/{activity}" if activity else ""))

            if not self.device:
                raise ADBError("No connection to device")

            # Start the app using uiautomator2
            if activity:
                self.device.app_start(package_name, activity)
                # # TODO remover gambiarra para teste
                # if self.device.app_start(package_name, activity):
                #     # Force a click in the middle of the screen after app launch
                #     print("************************* fica de olho")
                #     time.sleep(3)  # Wait for app to fully load
                #     screen_size = self.device.window_size()
                #     center_x = screen_size[0] // 2
                #     center_y = screen_size[1] // 2
                #     self.logger.info(f"Forcing test click at center: ({center_x}, {center_y})")
                #     self.device.click(center_x, center_y)
                #     return True
                # return False
            else:
                self.device.app_start(package_name)
                # TODO remover gambiarra para teste
                # if self.device.app_start(package_name):
                #     # Force a click in the middle of the screen after app launch
                #     print("************************* fica de olho 000000")
                #     time.sleep(3)  # Wait for app to fully load
                #     screen_size = self.device.window_size()
                #     center_x = screen_size[0] // 2
                #     center_y = screen_size[1] // 2
                #     self.logger.info(f"Forcing test click at center: ({center_x}, {center_y})")
                #     self.device.click(center_x, center_y)
                #     return True
                # return False

            # Wait for app to start
            time.sleep(2)

            return True

        except Exception as e:
            self.logger.error(f"Error starting app {package_name}: {e}")
            raise ADBError(f"Failed to start app: {str(e)}", e)

    def stop_app(self, package_name: str) -> bool:
        """
        Stop an application on the device.

        Args:
            package_name: Application package name

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Stopping app: {package_name}")

            if not self.device:
                raise ADBError("No connection to device")

            # Stop the app using uiautomator2
            self.device.app_stop(package_name)

            return True

        except Exception as e:
            self.logger.error(f"Error stopping app {package_name}: {e}")
            raise ADBError(f"Failed to stop app: {str(e)}", e)

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("Cleaning up UIAutomator adapter resources")

            # No specific cleanup needed for uiautomator2 connection
            # The device object doesn't need explicit disconnection
            self.device = None

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
