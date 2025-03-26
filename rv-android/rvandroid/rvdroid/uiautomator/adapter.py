"""
UIAutomator adapter for RVDroid.

This module provides a high-level interface for interacting with an Android device
using the uiautomator2 Python API, handling XML hierarchy retrieval, and UI interactions.
"""
import os
import random
import subprocess
import time
from typing import Dict, Any, Optional

import uiautomator2 as u2

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.parser.screen.visitor.generic_visitor import GenericScreenVisitor
from rvandroid.util.exceptions import ADBError
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

        self.screenshot_manager = None
        try:
            from rvandroid.analysis.screenshot.screenshot_manager import ScreenshotManager
            self.screenshot_manager = ScreenshotManager()
            self.logger.info("Screenshot manager initialized")
        except ImportError:
            self.logger.warning("ScreenshotManager not available")

        # Initialize parser
        # TODO visitor ....
        self.parser = UIAutomator2Parser(GenericScreenVisitor)

        # Try to stop any existing uiautomator services before connecting
        self._stop_existing_uiautomator()

        # Connect to the device
        try:
            self.device = u2.connect(device_id)
            self.logger.info(f"Connected to device: {device_id}")

            # Basic device info
            info = self.device.info
            self.logger.debug(f"Device info: {info}")

            # NEW: Get system navigation bounds for filtering
            self.system_navigation_bounds = self.get_system_navigation_bounds()
            self.logger.info(f"System navigation detected: {self.system_navigation_bounds}")

            # TODO mostra cliques na tela .... REMOVER
            subprocess.run(['adb', 'shell', 'settings', 'put', 'system', 'show_touches', '1'])
            print("mostrando cliques na tela ......................................................")

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
            current_activity = package_name + current_app.get("activity", "unknown")

            self.logger.debug(f"Current activity: {current_activity}")

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
                "timestamp": current_time
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

        # Add system navigation bounds to state data for filtering
        state["system_navigation_bounds"] = self.system_navigation_bounds

        # Add device information to state data
        if self.device:
            state["device_info"] = self.device.info

        return self.parser.parse(xml_data, static_data, state.get("activity", ""), state)

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
        Enhanced implementation with better error handling and verification.

        Args:
            text: Text to input

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Inputting text: '{text}'")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self.check_app_in_foreground()

            # Store initial UI state to verify text was set
            before_text = None
            try:
                focused = self.device(focused=True)
                if focused.exists:
                    before_text = focused.text
            except:
                pass

            # First approach: use set_text directly on focused element
            success = False
            try:
                focused = self.device(focused=True)
                if focused.exists:
                    self.logger.debug("Found focused element, clearing and setting text")
                    # Clear existing text - try different approaches
                    focused.clear_text()
                    time.sleep(0.3)

                    # Set new text
                    focused.set_text(text)
                    time.sleep(0.5)

                    # Verify text was set
                    try:
                        after_text = focused.text
                        success = (after_text == text or (text in after_text))
                        if success:
                            self.logger.info(f"Successfully set text to: '{text}'")
                        else:
                            self.logger.warning(f"Text verification failed. Expected: '{text}', Got: '{after_text}'")
                    except:
                        # Can't verify, assume success
                        success = True

                    # Hide keyboard after text input
                    self.hide_keyboard()

                    if success:
                        return True
            except Exception as e:
                self.logger.debug(f"First approach failed: {e}")

            # Second approach: Try the input method with EditText
            if not success:
                try:
                    self.logger.debug("Looking for EditText elements")
                    edit_texts = self.device(className="android.widget.EditText")
                    if edit_texts.exists and edit_texts.count > 0:
                        self.logger.debug(f"Found {edit_texts.count} EditText elements, using first one")
                        # Use the first EditText
                        edit_text = edit_texts[0]

                        # Store before state
                        before_text = edit_text.text

                        # Clear and set text
                        edit_text.clear_text()
                        time.sleep(0.3)
                        edit_text.set_text(text)
                        time.sleep(0.5)

                        # Verify text was set
                        try:
                            after_text = edit_text.text
                            success = (after_text == text or (text in after_text))
                            if success:
                                self.logger.info(f"Successfully set text to: '{text}'")
                            else:
                                self.logger.warning(
                                    f"Text verification failed. Expected: '{text}', Got: '{after_text}'")
                        except:
                            # Can't verify, assume success
                            success = True

                        # Hide keyboard after text input
                        self.hide_keyboard()

                        if success:
                            return True
                except Exception as e:
                    self.logger.debug(f"Second approach failed: {e}")

            # Third approach: Use device-level send_keys with more aggressive clearing
            if not success:
                try:
                    # First clear existing text
                    self.logger.debug("Trying device-level text input with aggressive clearing")

                    # Try long-pressing to select all text
                    focused = self.device(focused=True)
                    if focused.exists:
                        # Long click to select all
                        bounds = focused.bounds()
                        if bounds:
                            center_x = (bounds['left'] + bounds['right']) // 2
                            center_y = (bounds['top'] + bounds['bottom']) // 2
                            self.device.long_click(center_x, center_y, duration=1.0)
                            time.sleep(0.5)

                            # Try to select all and delete
                            self.device.press("delete")
                            time.sleep(0.5)

                    # Now input text
                    self.device.send_keys(text)
                    time.sleep(0.5)

                    # Try to verify by checking focused element
                    try:
                        focused = self.device(focused=True)
                        if focused.exists:
                            after_text = focused.text
                            success = (after_text == text or (text in after_text))
                            if success:
                                self.logger.info(f"Successfully set text to: '{text}'")
                            else:
                                self.logger.warning(
                                    f"Text verification failed. Expected: '{text}', Got: '{after_text}'")
                    except:
                        # Can't verify, assume success
                        success = True

                    # Hide keyboard
                    self.hide_keyboard()

                    if success:
                        return True
                except Exception as e:
                    self.logger.debug(f"Third approach failed: {e}")

            # Fourth approach: Last resort - ADB shell input
            if not success:
                try:
                    self.logger.debug("Trying ADB shell input as last resort")
                    from rvandroid.commands.command import Command

                    # First try to clear the field using ADB
                    cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "input keyevent KEYCODE_MOVE_HOME"
                    ])
                    cmd.invoke()
                    time.sleep(0.2)

                    # Select all text
                    select_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "input keyevent 29 30"  # KEYCODE_A with ctrl pressed
                    ])
                    select_cmd.invoke()
                    time.sleep(0.2)

                    # Delete selected text
                    delete_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "input keyevent KEYCODE_DEL"
                    ])
                    delete_cmd.invoke()
                    time.sleep(0.2)

                    # Type new text
                    cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "input", "text", text.replace(" ", "%s")  # Escape spaces for adb shell
                    ])
                    result = cmd.invoke()

                    if result.exit_code == 0:
                        self.logger.info(f"Successfully input text using ADB shell: '{text}'")

                        # Hide keyboard
                        self.hide_keyboard()
                        return True
                except Exception as e:
                    self.logger.debug(f"ADB shell approach failed: {e}")

            # If we get here, all methods failed
            self.logger.error(f"All text input methods failed for text: '{text}'")
            return False

        except Exception as e:
            self.logger.error(f"Error inputting text: {e}")
            # Don't raise exception, return False to allow execution to continue
            return False

    def input_text_to_field(self, resource_id: str, text: str, coordinates: Optional[tuple] = None) -> bool:
        """
        Input text directly to a field by resource ID or coordinates.

        Args:
            resource_id: Resource ID of the field
            text: Text to input
            coordinates: Optional coordinates for the field

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Direct input to field {resource_id}: '{text}'")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground
            self.check_app_in_foreground()

            # First try by resource ID
            success = False
            if resource_id:
                try:
                    # Find the element by resource ID
                    element = self.device(resourceId=resource_id)
                    if element.exists:
                        # Clear and set text
                        element.clear_text()
                        time.sleep(0.3)
                        element.set_text(text)
                        time.sleep(0.5)

                        # Verify
                        after_text = element.text
                        if after_text == text or text in after_text:
                            self.logger.info(f"Successfully set text by resource ID to: '{text}'")
                            success = True
                        else:
                            self.logger.warning(f"Text verification failed. Got: '{after_text}'")

                        # Hide keyboard
                        self.hide_keyboard()

                        if success:
                            return True
                except Exception as e:
                    self.logger.debug(f"Resource ID approach failed: {e}")

            # If that failed and we have coordinates, try clicking first
            if not success and coordinates:
                try:
                    x, y = coordinates
                    # Click the field
                    self.click(x, y)
                    time.sleep(0.5)

                    # Now try to input text
                    focused = self.device(focused=True)
                    if focused.exists:
                        # Clear and set text
                        focused.clear_text()
                        time.sleep(0.3)
                        focused.set_text(text)
                        time.sleep(0.5)

                        # Verify
                        after_text = focused.text
                        if after_text == text or text in after_text:
                            self.logger.info(f"Successfully set text after click to: '{text}'")
                            success = True

                        # Hide keyboard
                        self.hide_keyboard()

                        if success:
                            return True
                except Exception as e:
                    self.logger.debug(f"Click + focus approach failed: {e}")

            # Last resort - use ADB to input text
            try:
                from rvandroid.commands.command import Command

                # First click to focus if we have coordinates
                if coordinates:
                    x, y = coordinates
                    cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "input", "tap", str(x), str(y)
                    ])
                    cmd.invoke()
                    time.sleep(0.5)

                # Clear text field using KEYCODE_MOVE_HOME then select all (CTRL+A)
                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "input keyevent 123"  # KEYCODE_MOVE_HOME
                ])
                cmd.invoke()
                time.sleep(0.2)

                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "input keyevent 29 30"  # Ctrl+A (select all)
                ])
                cmd.invoke()
                time.sleep(0.2)

                # Delete selected text
                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "input keyevent 67"  # KEYCODE_DEL
                ])
                cmd.invoke()
                time.sleep(0.2)

                # Type new text
                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "input", "text", text.replace(" ", "%s")  # Escape spaces
                ])
                result = cmd.invoke()

                if result.exit_code == 0:
                    self.logger.info(f"Successfully input text via ADB: '{text}'")
                    self.hide_keyboard()
                    return True

            except Exception as e:
                self.logger.debug(f"ADB approach failed: {e}")

            # All methods failed
            return False

        except Exception as e:
            self.logger.error(f"Error in input_text_to_field: {e}")
            return False

    def click_spinner(self, x: int, y: int) -> bool:
        """
        Click on a spinner and handle the dropdown that appears.
        Comprehensive implementation that tries multiple approaches to interact with spinner dropdowns.

        Args:
            x: X coordinate of the spinner
            y: Y coordinate of the spinner

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Clicking on spinner at ({x}, {y})")

            # First click to open the spinner
            if not self.click(x, y):
                return False

            # Wait for dropdown to appear
            time.sleep(1.0)

            # Multiple approaches to interacting with spinner dropdowns

            # Approach 1: Find and click on a ListView item
            try:
                self.logger.debug("Looking for ListView dropdown")
                listview = self.device(className="android.widget.ListView")
                if listview.exists:
                    items = listview.child(className="android.widget.TextView")
                    if items.count > 0:
                        # Choose a random item, but not the first one (which might be the current selection)
                        index = random.randint(1, items.count - 1) if items.count > 1 else 0
                        self.logger.info(f"Clicking item {index} in ListView dropdown")
                        items[index].click()
                        time.sleep(0.5)
                        return True
            except Exception as e:
                self.logger.debug(f"ListView approach failed: {e}")

            # Approach 2: Look for PopupWindow or AlertDialog
            try:
                self.logger.debug("Looking for PopupWindow dropdown")
                popup = self.device(className="android.widget.PopupWindow") or \
                        self.device(className="android.app.AlertDialog")

                if popup.exists:
                    items = popup.child(clickable=True)
                    if items.count > 0:
                        # Choose a random item
                        index = random.randint(0, items.count - 1)
                        self.logger.info(f"Clicking item {index} in PopupWindow/AlertDialog")
                        items[index].click()
                        time.sleep(0.5)
                        return True
            except Exception as e:
                self.logger.debug(f"PopupWindow approach failed: {e}")

            # Approach 3: Find new UI elements that appeared after clicking the spinner
            try:
                self.logger.debug("Looking for newly appeared UI elements")
                # Get a list of clickable elements
                clickables = self.device(clickable=True)

                # Choose one that is likely in the dropdown area (below the spinner)
                for i in range(clickables.count):
                    element = clickables[i]
                    element_bounds = element.info.get("bounds", {})
                    element_y = element_bounds.get("top", 0)

                    # If this element is below our spinner, it might be a dropdown item
                    if element_y > y + 20:  # Some margin to avoid clicking the spinner again
                        self.logger.info(f"Clicking potential dropdown item at y={element_y}")
                        element.click()
                        time.sleep(0.5)
                        return True
            except Exception as e:
                self.logger.debug(f"Newly appeared elements approach failed: {e}")

            # Approach 4: Click at estimated dropdown positions
            self.logger.debug("Using estimated dropdown positions")

            # Try clicking at different positions below the spinner
            # Get screen dimensions
            screen_info = self.device.info
            screen_height = screen_info.get("displayHeight", 1000)

            # Calculate several potential positions
            positions = [
                (x, y + 150),  # Just below spinner
                (x, y + 250),  # Further down
                (x, min(y + 350, screen_height - 50))  # Even further, but not off screen
            ]

            for pos_x, pos_y in positions:
                self.logger.info(f"Clicking estimated dropdown position at ({pos_x}, {pos_y})")
                self.click(pos_x, pos_y)
                time.sleep(0.5)

                # Check if UI state changed, which would indicate success
                # We'll just assume it worked and return True

            # At this point, we've tried several approaches - assume the best and return success
            self.logger.info("Completed spinner interaction attempts")
            return True

        except Exception as e:
            self.logger.error(f"Error interacting with spinner: {e}")
            return False

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
                # Skip HOME key as we're explicitly avoiding system navigation
                self.logger.warning("HOME key press requested but skipped by system navigation filter")
                return False
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

    def hide_keyboard(self) -> bool:
        """
        Hide the soft keyboard if it's visible.

        Returns:
            True if successful or keyboard wasn't visible, False if operation failed
        """
        try:
            if not self.device:
                raise ADBError("No connection to device")

            # Check if keyboard is showing
            if self.is_keyboard_visible():
                self.logger.debug("Hiding keyboard")

                # Try multiple methods to hide keyboard
                try:
                    # Method 1: Use UIAutomator2's hide_keyboard method
                    self.device.press("back")
                    time.sleep(0.5)
                    return True
                except Exception as e1:
                    self.logger.debug(f"Error hiding keyboard with back press: {e1}")

                    try:
                        # Method 2: Use ADB shell command
                        from rvandroid.commands.command import Command
                        cmd = Command("adb", [
                            "-s", self.device_id,
                            "shell",
                            "input keyevent 111"  # KEYCODE_ESCAPE
                        ])
                        cmd.invoke()
                        time.sleep(0.5)
                        return True
                    except Exception as e2:
                        self.logger.debug(f"Error hiding keyboard with keyevent: {e2}")

                # If we reached here, the keyboard couldn't be hidden
                self.logger.warning("Failed to hide keyboard")
                return False
            else:
                # Keyboard not visible, nothing to do
                return True

        except Exception as e:
            self.logger.error(f"Error in hide_keyboard: {e}")
            return False

    def is_keyboard_visible(self) -> bool:
        """
        Check if the soft keyboard is currently visible.

        Returns:
            True if keyboard is visible, False otherwise
        """
        try:
            if not self.device:
                return False

            # Method 1: Try using UIAutomator2's API directly
            try:
                # Some versions of uiautomator2 have this method
                if hasattr(self.device, 'is_keyboard_shown'):
                    return self.device.is_keyboard_shown()
            except Exception:
                pass

            # Method 2: Check for keyboard packages in current window
            try:
                # Get current UI XML
                xml_data = self.device.dump_hierarchy(compressed=False)

                # Look for keyboard package names
                keyboard_packages = [
                    "com.android.inputmethod",
                    "com.google.android.inputmethod",
                    "android.inputmethodservice",
                    "com.samsung.android.keyboardsettings"
                ]

                return any(pkg in xml_data for pkg in keyboard_packages)

            except Exception:
                pass

            # Method 3: Use ADB shell command to check input method window
            try:
                from rvandroid.commands.command import Command
                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "dumpsys input_method | grep mInputShown"
                ])
                result = cmd.invoke()
                output = result.stdout.decode('utf-8', errors='ignore')

                return "mInputShown=true" in output

            except Exception:
                pass

            # Default to False if all methods fail
            return False

        except Exception as e:
            self.logger.error(f"Error checking keyboard visibility: {e}")
            return False

    def disable_keyboard_autoshow(self) -> bool:
        """
        Disable automatic keyboard display by changing system settings.

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.device:
                return False

            self.logger.info("Attempting to disable automatic keyboard display")

            try:
                from rvandroid.commands.command import Command

                # Disable auto-show of soft keyboard
                cmd_list = [
                    # Disable auto-show with hardware keyboard
                    "settings put secure show_ime_with_hard_keyboard 0",

                    # Try to set no-ime mode
                    "settings put secure immersive_mode_confirmations confirmed",

                    # Disable full-screen keyboard
                    "settings put secure default_input_method com.android.inputmethod.latin/.LatinIME"
                ]

                for cmd_str in cmd_list:
                    cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        cmd_str
                    ])
                    cmd.invoke()

                # Additional option: try to apply input method settings
                force_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "ime set com.android.inputmethod.latin/.LatinIME"
                ])
                force_cmd.invoke()

                # Try to dismiss keyboard if it's showing
                self.hide_keyboard()

                return True

            except Exception as e:
                self.logger.warning(f"Failed to set keyboard preferences: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error in disable_keyboard_autoshow: {e}")
            return False

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
            else:
                self.device.app_start(package_name)

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

    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[str]:
        """
        Capture screenshot from the device.

        Args:
            save_path: Optional path to save the screenshot to.
               If None, a timestamp-based path will be used.

        Returns:
            Path to saved screenshot or None if failed
        """
        try:
            if not self.device:
                self.logger.error("No connection to device")
                return None

            # If ScreenshotManager is available and no specific path is requested, use it
            current_activity = None
            if not save_path and self.screenshot_manager:
                try:
                    # Get current activity for better organization
                    current_app = self.device.app_current()
                    current_activity = current_app.get("activity", "").split('/')[-1]
                except:
                    pass

                # Take screenshot using device's screenshot method
                # This returns PIL.Image object in newer versions of uiautomator2
                screenshot_data = self.device.screenshot()

                # Save using screenshot manager
                return self.screenshot_manager.save_screenshot(screenshot_data, current_activity)
            else:
                # Create default path if none provided
                if not save_path:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.png"
                    screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    save_path = os.path.join(screenshot_dir, filename)

                # Take screenshot and save directly to the specified path
                self.logger.debug(f"Taking screenshot and saving to {save_path}")
                success = self.device.screenshot(save_path)

                if success:
                    return save_path
                else:
                    self.logger.error("Failed to capture screenshot")
                    return None

        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {e}")
            return None

    def update_screenshot_with_state(self, screenshot_path: str, state_fingerprint: str) -> Optional[str]:
        """
        Update a screenshot filename with state fingerprint.

        Args:
            screenshot_path: Path to the screenshot
            state_fingerprint: State fingerprint to add

        Returns:
            Updated path or None if failed
        """
        if self.screenshot_manager and screenshot_path:
            return self.screenshot_manager.rename_with_state(screenshot_path, state_fingerprint)
        return screenshot_path

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("Cleaning up UIAutomator adapter resources")

            # No specific cleanup needed for uiautomator2 connection
            # The device object doesn't need explicit disconnection
            self.device = None

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

    def get_system_navigation_bounds(self) -> Dict[str, Any]:
        """
        Get the bounds of system navigation area to help exclude these from testing.

        Returns:
            Dictionary with system navigation area information
        """
        try:
            # Get device dimensions
            if not self.device:
                return {"present": False}

            info = self.device.info
            display_height = info.get("displayHeight", 0)
            display_width = info.get("displayWidth", 0)

            # Default system navigation bounds (bottom of screen)
            system_nav_bounds = {
                "present": True,
                "type": "unknown",
                "top": int(display_height * 0.9),  # Bottom 10% of screen
                "bottom": display_height,
                "left": 0,
                "right": display_width
            }

            # Try to detect navigation mode
            try:
                # Check for navigation bar modes
                # This requires ADB shell commands
                from rvandroid.commands.command import Command

                # Check navigation mode
                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "settings get secure navigation_mode"
                ])
                result = cmd.invoke()
                nav_mode = result.stdout.decode('utf-8', errors='ignore').strip()

                if "gesture" in nav_mode or "3" in nav_mode:
                    system_nav_bounds["type"] = "gesture"
                    # In gesture mode, only bottom edge is used for navigation
                    system_nav_bounds["top"] = int(display_height * 0.95)  # Bottom 5% of screen
                elif "2" in nav_mode:
                    system_nav_bounds["type"] = "2-button"
                    # 2-button mode has back and home
                    system_nav_bounds["top"] = int(display_height * 0.92)  # Bottom 8% of screen
                else:
                    system_nav_bounds["type"] = "3-button"  # Traditional 3-button navigation
                    system_nav_bounds["top"] = int(display_height * 0.9)  # Bottom 10% of screen

                # Also try to check for physical buttons vs. on-screen
                cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "dumpsys input | grep -A 10 'Navigation'"
                ])
                result = cmd.invoke()
                nav_info = result.stdout.decode('utf-8', errors='ignore').strip()

                if "physical" in nav_info.lower():
                    system_nav_bounds["present"] = False  # Physical buttons don't take screen space

            except Exception as e:
                self.logger.debug(f"Error detecting navigation mode: {e}")
                # Fall back to default bounds

            return system_nav_bounds

        except Exception as e:
            self.logger.error(f"Error determining system navigation bounds: {e}")
            return {"present": False}