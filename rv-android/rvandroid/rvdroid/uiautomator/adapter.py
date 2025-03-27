# rvandroid/rvdroid/uiautomator/adapter.py
"""
UIAutomator2 adapter for RVDroid.

This module provides a high-level interface for interacting with an Android device
using the UIAutomator2 Python API, with consistent error handling and efficient
UI hierarchy processing.
"""

import os
import random
import subprocess
import time
from typing import Dict, Any, Optional, Tuple

import uiautomator2 as u2

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.parser.screen.visitor.generic_visitor import GenericScreenVisitor
from rvandroid.util.decorators import task_phase
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import ADBError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class UIAutomator2Adapter:
    """
    Adapter for interacting with Android devices using the UIAutomator2 Python API.

    ### Architectural Decisions:
    - Implements a unified adapter with consistent error handling
    - Uses a single connection mechanism for all device interactions
    - Applies intelligent caching to minimize redundant state retrievals
    - Implements standardized device interaction methods with consistent signatures
    - Provides screenshot management with automatic error detection
    - Filters system navigation elements to prevent unwanted interactions

    ### Role in the System:
    - Serves as the primary interface between RVDroid and Android devices
    - Provides a reliable foundation for UI exploration and testing
    - Abstracts device-specific details from higher-level test components
    - Enables screenshot-based analysis and visual validation
    """

    def __init__(self, device_id: str = "emulator-5554"):
        """
        Initialize the UIAutomator2 adapter.

        Args:
            device_id: Device ID to connect to (defaults to emulator-5554)
        """
        # Configure logging with context adapter
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.uiautomator.adapter",
            {CONTEXT_COMPONENT: "UIAutomator2Adapter"}
        )

        self.device_id = device_id
        self.logger.info(f"Initializing UIAutomator adapter for device: {device_id}")

        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Initialize screenshot manager if available
        self.screenshot_manager = self._initialize_screenshot_manager()

        # Initialize parser
        self.parser = UIAutomator2Parser(GenericScreenVisitor)

        # Stop any existing UIAutomator processes before connecting
        self._stop_existing_uiautomator()

        # Connect to the device
        self.device = self._connect_to_device()

        # Get system navigation bounds for filtering
        self.system_navigation_bounds = self._get_system_navigation_bounds()
        self.logger.info(f"System navigation detected: {self.system_navigation_bounds}")

        # State cache
        self._last_state = None
        self._last_state_time = 0
        self._state_cache_ttl = 0.5  # 500ms cache TTL

    def _initialize_screenshot_manager(self) -> Optional[Any]:
        """
        Initialize screenshot manager if available.

        Returns:
            Screenshot manager instance or None
        """
        try:
            from rvandroid.analysis.screenshot.screenshot_manager import ScreenshotManager
            manager = ScreenshotManager()
            self.logger.info("Screenshot manager initialized")
            return manager
        except ImportError:
            self.logger.warning("ScreenshotManager not available")
            return None

    def _stop_existing_uiautomator(self) -> None:
        """Stop any existing UIAutomator services on the device."""
        try:
            from rvandroid.commands.command import Command

            # Check for running UIAutomator processes
            ps_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "ps | grep uiautomator"
            ])
            result = ps_cmd.invoke()

            if result.stdout:
                self.logger.info("Found existing UIAutomator processes, stopping them...")

                # Kill existing UIAutomator processes
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
            self.logger.warning(f"Error stopping existing UIAutomator services: {e}")

    def _connect_to_device(self) -> Any:
        """
        Connect to the Android device using UIAutomator2.

        Returns:
            UIAutomator2 device object

        Raises:
            ADBError: If connection fails
        """
        try:
            device = u2.connect(self.device_id)
            self.logger.info(f"Connected to device: {self.device_id}")

            # Get basic device info for validation
            info = device.info
            self.logger.debug(f"Device info: {info}")

            # Enable touch indicators for debugging
            subprocess.run(['adb', 'shell', 'settings', 'put', 'system', 'show_touches', '1'])

            return device

        except Exception as e:
            self.logger.error(f"Error connecting to device: {e}")

            # Try alternative connection method
            try:
                self.logger.info("Trying alternative connection method...")
                from rvandroid.commands.command import Command

                # Kill existing UIAutomator processes
                kill_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "pkill -f uiautomator"
                ])
                kill_cmd.invoke()

                # Wait for processes to terminate
                time.sleep(2)

                # Connect again
                device = u2.connect(self.device_id)
                self.logger.info("Successfully connected using alternative method")
                return device
            except Exception as retry_error:
                self.logger.error(f"Alternative connection also failed: {retry_error}")
                raise ADBError(f"Failed to connect to device: {str(e)}", e)

    @task_phase("get_ui_state", measure_performance=True)
    def get_ui_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieve the current UI state from the device.

        Args:
            force_refresh: Force a refresh regardless of cache status

        Returns:
            Dictionary containing UI state information including the XML hierarchy

        Raises:
            ADBError: If unable to obtain UI state
        """
        # Create operation context
        context = {"operation": "get_ui_state", "device_id": self.device_id}

        with self.logger.with_context(**context):
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
                    "timestamp": current_time,
                    "device_info": self.device.info,
                    "system_navigation_bounds": self.system_navigation_bounds
                }

                # Cache state
                self._last_state = state
                self._last_state_time = current_time

                return state

            except Exception as e:
                self.logger.error(f"Error getting UI state: {e}")
                raise ADBError(f"Failed to get UI state: {str(e)}", e)

    @task_phase("ensure_app_foreground", measure_performance=True)
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

            # Fallback to ADB if UIAutomator connection not available
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

    @task_phase("parse_screen", measure_performance=True)
    def parse_screen(self, state: Dict[str, Any],
                     static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse the UI state into a structured screen description.

        Args:
            state: UI state dictionary from get_ui_state()
            static_data: Optional static analysis data

        Returns:
            ScreenDescription object

        Raises:
            ValueError: If hierarchy data is missing or invalid
        """
        # Extract the XML hierarchy from the state
        xml_data = state.get("hierarchy", "")
        if not xml_data:
            self.logger.error("No hierarchy XML found in state data")
            raise ValueError("No hierarchy XML found in state data")

        activity = state.get("activity", "")

        # Parse the screen using the UIAutomator2Parser
        return self.parser.parse(xml_data, static_data, activity, state)

    @task_phase("perform_click", measure_performance=True)
    def click(self, x: int, y: int) -> bool:
        """
        Perform a click operation at the specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if successful, False otherwise

        Raises:
            ADBError: If click operation fails
        """
        try:
            self.logger.debug(f"Clicking at coordinates: ({x}, {y})")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self._check_app_in_foreground()

            # Execute click operation via UIAutomator2 with visual feedback
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

    @task_phase("perform_long_click", measure_performance=True)
    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """
        Perform a long click operation at the specified coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of the long press in seconds

        Returns:
            True if successful, False otherwise

        Raises:
            ADBError: If long click operation fails
        """
        try:
            self.logger.debug(f"Long clicking at coordinates: ({x}, {y}) for {duration}s")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self._check_app_in_foreground()

            # Execute long click operation via UIAutomator2
            self.device.long_click(x, y, duration)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error long clicking at ({x}, {y}): {e}")
            raise ADBError(f"Failed to perform long click: {str(e)}", e)

    def _check_app_in_foreground(self) -> None:
        """
        Check if the target app is in foreground.

        Raises:
            ADBError: If app is not in foreground
        """
        # Get the current state to check package name
        state = self.get_ui_state()
        package_name = state.get("package_name")

        # Verify app is in foreground before performing action
        if not self.ensure_app_in_foreground(package_name):
            raise ADBError(f"App {package_name} is not in foreground, cannot perform action")

    @task_phase("input_text", measure_performance=True)
    def input_text(self, text: str) -> bool:
        """
        Input text at the currently focused element.

        Args:
            text: Text to input

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Inputting text: '{text}'")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground
            self._check_app_in_foreground()

            # First approach: use set_text on focused element
            focused = self.device(focused=True)
            if focused.exists:
                self.logger.debug("Found focused element, clearing and setting text")
                focused.clear_text()
                time.sleep(0.3)
                focused.set_text(text)
                time.sleep(0.5)

                # Verify text was set
                after_text = focused.text
                if after_text == text or text in after_text:
                    self.logger.info(f"Successfully set text to: '{text}'")
                    self.hide_keyboard()
                    return True

            # Second approach: Find EditText elements
            edit_texts = self.device(className="android.widget.EditText")
            if edit_texts.exists and edit_texts.count > 0:
                self.logger.debug(f"Found {edit_texts.count} EditText elements, using first one")
                edit_text = edit_texts[0]

                edit_text.clear_text()
                time.sleep(0.3)
                edit_text.set_text(text)
                time.sleep(0.5)

                # Verify text was set
                after_text = edit_text.text
                if after_text == text or text in after_text:
                    self.logger.info(f"Successfully set text to: '{text}'")
                    self.hide_keyboard()
                    return True

            # Third approach: Use device-level send_keys
            self.logger.debug("Trying device-level text input")

            # Try to select all existing text first
            try:
                focused = self.device(focused=True)
                if focused.exists:
                    bounds = focused.bounds()
                    if bounds:
                        center_x = (bounds['left'] + bounds['right']) // 2
                        center_y = (bounds['top'] + bounds['bottom']) // 2
                        self.device.long_click(center_x, center_y, duration=1.0)
                        time.sleep(0.5)
                        self.device.press("delete")
                        time.sleep(0.5)
            except:
                pass

            # Send the text
            self.device.send_keys(text)
            time.sleep(0.5)
            self.hide_keyboard()

            # No easy way to verify this method, assume success
            return True

        except Exception as e:
            self.logger.error(f"Error inputting text: {e}")
            return False

    @task_phase("input_text_to_field", measure_performance=True)
    def input_text_to_field(self, resource_id: str, text: str, coordinates: Optional[Tuple[int, int]] = None) -> bool:
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
            self._check_app_in_foreground()

            # First try by resource ID
            if resource_id:
                element = self.device(resourceId=resource_id)
                if element.exists:
                    element.clear_text()
                    time.sleep(0.3)
                    element.set_text(text)
                    time.sleep(0.5)

                    # Verify text was set
                    after_text = element.text
                    if after_text == text or text in after_text:
                        self.logger.info(f"Successfully set text by resource ID to: '{text}'")
                        self.hide_keyboard()
                        return True

            # If that failed and we have coordinates, try clicking first
            if coordinates:
                x, y = coordinates
                self.click(x, y)
                time.sleep(0.5)

                focused = self.device(focused=True)
                if focused.exists:
                    focused.clear_text()
                    time.sleep(0.3)
                    focused.set_text(text)
                    time.sleep(0.5)

                    # Verify success
                    self.hide_keyboard()
                    return True

            # Fall back to regular text input
            return self.input_text(text)

        except Exception as e:
            self.logger.error(f"Error in input_text_to_field: {e}")
            return False

    @task_phase("click_spinner", measure_performance=True)
    def click_spinner(self, x: int, y: int) -> bool:
        """
        Click on a spinner and handle the dropdown that appears.

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
                self.logger.error("Failed to click spinner to open dropdown")
                return False

            # Wait for dropdown to appear
            time.sleep(1.5)  # Increased wait time for dropdown to fully appear

            # Try multiple approaches to find and interact with the dropdown
            success = False

            # Approach 1: Try to find ListView or AbsListView
            listview_classes = ["android.widget.ListView", "android.widget.AbsListView"]
            for list_class in listview_classes:
                listview = self.device(className=list_class)
                if listview.exists:
                    self.logger.debug(f"Found dropdown as {list_class}")
                    items = listview.child(className="android.widget.TextView") or listview.child(clickable=True)

                    if items.count > 0:
                        # Select a random item, but NOT the first one (which is usually the current selection)
                        if items.count > 1:
                            # Explicitly avoid index 0 to ensure we don't select the current item
                            index = random.randint(1, items.count - 1)
                            self.logger.info(f"Clicking random item {index} of {items.count} in ListView dropdown")
                        else:
                            index = 0  # Only one item available
                            self.logger.info("Only one item in ListView dropdown, selecting it")

                        try:
                            items[index].click()
                            time.sleep(0.5)
                            success = True
                            break
                        except Exception as e:
                            self.logger.error(f"Error clicking dropdown item: {e}")

            # Approach 2: Try to find popup window or dialog
            if not success:
                popup_classes = ["android.widget.PopupWindow", "android.app.AlertDialog",
                                 "android.widget.PopupMenu"]
                for popup_class in popup_classes:
                    popup = self.device(className=popup_class)
                    if popup.exists:
                        self.logger.debug(f"Found dropdown as {popup_class}")
                        items = popup.child(clickable=True)

                        if items.count > 0:
                            # Select a random item, avoiding the first one
                            if items.count > 1:
                                index = random.randint(1, items.count - 1)
                                self.logger.info(f"Clicking random item {index} of {items.count} in {popup_class}")
                            else:
                                index = 0  # Only one item
                                self.logger.info(f"Only one item in {popup_class}, selecting it")

                            try:
                                items[index].click()
                                time.sleep(0.5)
                                success = True
                                break
                            except Exception as e:
                                self.logger.error(f"Error clicking popup item: {e}")

            # Approach 3: Look for any new clickable items that might be part of dropdown
            if not success:
                self.logger.debug("Looking for any new clickable items")
                # Get screen dimensions
                screen_info = self.device.info
                screen_height = screen_info.get("displayHeight", 1000)
                screen_width = screen_info.get("displayWidth", 500)

                # Look below the spinner for clickable elements
                clickable_below = self.device(clickable=True,
                                              bounds=f"[0,{y + 10}][{screen_width},{screen_height}]")

                if clickable_below.count > 0:
                    # Select a random clickable element, but not the first one
                    if clickable_below.count > 1:
                        # Avoid index 0 which might be the spinner itself or header
                        index = random.randint(1, clickable_below.count - 1)
                        self.logger.info(
                            f"Clicking random item {index} of {clickable_below.count} clickable elements below spinner")
                    else:
                        index = 0  # Only one item
                        self.logger.info("Only one clickable item below spinner, selecting it")

                    try:
                        clickable_below[index].click()
                        time.sleep(0.5)
                        success = True
                    except Exception as e:
                        self.logger.error(f"Error clicking element below spinner: {e}")

            # Approach 4: If all else fails, click at random positions below the spinner
            if not success:
                # Generate random positions below the spinner to try different items
                positions = []
                base_y = y + 100  # Start well below the spinner

                # Create 4 random positions at different vertical offsets
                for i in range(4):
                    pos_y = base_y + random.randint(50, 150) + (i * 75)
                    if pos_y < screen_height - 50:  # Ensure we stay on screen
                        positions.append((x, pos_y))

                # Shuffle positions for more randomness
                random.shuffle(positions)

                for pos_x, pos_y in positions:
                    self.logger.info(f"Clicking random dropdown position at ({pos_x}, {pos_y})")
                    try:
                        self.click(pos_x, pos_y)
                        time.sleep(0.5)
                        # Consider successful since we made our best attempt
                        success = True
                        break
                    except Exception as e:
                        self.logger.error(f"Error clicking estimated position: {e}")

            return success

        except Exception as e:
            self.logger.error(f"Error interacting with spinner: {e}")
            return False

    @task_phase("scroll", measure_performance=True)
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

        Raises:
            ADBError: If scroll operation fails
        """
        try:
            self.logger.debug(f"Scrolling {direction} from coordinates: ({x}, {y}) for {distance}px")

            if not self.device:
                raise ADBError("No connection to device")

            # Verify app is in foreground before performing action
            self._check_app_in_foreground()

            # Calculate end coordinates based on direction
            if direction == "UP":
                end_x, end_y = x, y - distance
            elif direction == "DOWN":
                end_x, end_y = x, y + distance
            elif direction == "LEFT":
                end_x, end_y = x - distance, y
            elif direction == "RIGHT":
                end_x, end_y = x + distance, y
            else:
                self.logger.error(f"Invalid scroll direction: {direction}")
                return False

            # Execute swipe operation via UIAutomator2
            self.device.swipe(x, y, end_x, end_y)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error scrolling {direction} from ({x}, {y}): {e}")
            raise ADBError(f"Failed to perform scroll: {str(e)}", e)

    @task_phase("press_key", measure_performance=True)
    def press_key(self, key_code: str) -> bool:
        """
        Press a key on the device.

        Args:
            key_code: Key code to press (e.g., BACK, HOME, MENU)

        Returns:
            True if successful, False otherwise

        Raises:
            ADBError: If key press fails
        """
        try:
            self.logger.debug(f"Pressing key: {key_code}")

            if not self.device:
                raise ADBError("No connection to device")

            # Map key names to UIAutomator2 methods
            key_code = key_code.lower()

            # Known key codes
            if key_code == "back":
                self.device.press("back")
            elif key_code == "home":
                # Skip HOME key as it might navigate away from the app
                self.logger.warning("HOME key press requested but skipped to avoid leaving the app")
                return False
            elif key_code == "menu":
                self.device.press("menu")
            elif key_code == "enter":
                self.device.press("enter")
            else:
                # For other keys, try to use the generic press method
                self.device.press(key_code)

            # Short wait for UI to respond
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Error pressing key {key_code}: {e}")
            raise ADBError(f"Failed to press key: {str(e)}", e)

    @task_phase("hide_keyboard", measure_performance=True)
    def hide_keyboard(self) -> bool:
        """
        Hide the soft keyboard if it's visible.

        Returns:
            True if successful or keyboard wasn't visible, False if operation failed
        """
        try:
            if not self.device:
                return False

            # Check if keyboard is showing
            if self.is_keyboard_visible():
                self.logger.debug("Hiding keyboard")

                # Try pressing back to hide keyboard
                try:
                    self.device.press("back")
                    time.sleep(0.5)
                    return True
                except Exception as e:
                    self.logger.debug(f"Error hiding keyboard with back press: {e}")

                    # Try alternative method using keyevent
                    try:
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

                return False

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
            if hasattr(self.device, 'is_keyboard_shown'):
                return self.device.is_keyboard_shown()

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
            except:
                pass

            # Method 3: Use ADB command to check input method window
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
            except:
                pass

            # Default to False if all methods fail
            return False

        except Exception as e:
            self.logger.error(f"Error checking keyboard visibility: {e}")
            return False

    @task_phase("start_app", measure_performance=True)
    def start_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        """
        Start an application on the device.

        Args:
            package_name: Application package name
            activity: Optional activity to start

        Returns:
            True if successful, False otherwise

        Raises:
            ADBError: If app start fails
        """
        try:
            self.logger.debug(f"Starting app: {package_name}" + (f"/{activity}" if activity else ""))

            if not self.device:
                raise ADBError("No connection to device")

            # Start the app using UIAutomator2
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

    @task_phase("stop_app", measure_performance=True)
    def stop_app(self, package_name: str) -> bool:
        """
        Stop an application on the device.

        Args:
            package_name: Application package name

        Returns:
            True if successful, False otherwise

        Raises:
            ADBError: If app stop fails
        """
        try:
            self.logger.debug(f"Stopping app: {package_name}")

            if not self.device:
                raise ADBError("No connection to device")

            # Stop the app using UIAutomator2
            self.device.app_stop(package_name)

            return True

        except Exception as e:
            self.logger.error(f"Error stopping app {package_name}: {e}")
            raise ADBError(f"Failed to stop app: {str(e)}", e)

    @task_phase("take_screenshot", measure_performance=True)
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

    @task_phase("click_by_resource_id", measure_performance=True)
    def click_by_resource_id(self, resource_id: str) -> bool:
        """
        Click on an element identified by resource ID.

        Args:
            resource_id: Resource ID of the element to click

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Clicking element with resource ID: {resource_id}")

            if not self.device:
                raise ADBError("No connection to device")

            # Find the element by resource ID
            element = self.device(resourceId=resource_id)
            if not element.exists:
                self.logger.warning(f"Element with resource ID {resource_id} not found")
                return False

            # Get bounds and click in the center
            bounds = element.bounds()
            if not bounds:
                self.logger.warning(f"Could not determine bounds for element {resource_id}")
                return False

            # Calculate center coordinates
            x = (bounds["left"] + bounds["right"]) // 2
            y = (bounds["top"] + bounds["bottom"]) // 2

            # Click at the center of the element
            return self.click(x, y)

        except Exception as e:
            self.logger.error(f"Error clicking element with resource ID {resource_id}: {e}")
            return False

    @task_phase("input_text_to_field", measure_performance=True)
    def input_text_to_field(self, resource_id: str, text: str, coordinates: Optional[Tuple[int, int]] = None) -> bool:
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
            self._check_app_in_foreground()

            # First try by resource ID
            if resource_id:
                element = self.device(resourceId=resource_id)
                if element.exists:
                    element.clear_text()
                    time.sleep(0.3)
                    element.set_text(text)
                    time.sleep(0.5)

                    # Verify text was set
                    after_text = element.text
                    if after_text == text or text in after_text:
                        self.logger.info(f"Successfully set text by resource ID to: '{text}'")
                        self.hide_keyboard()
                        return True

            # If that failed and we have coordinates, try clicking first
            if coordinates:
                x, y = coordinates
                if self.click(x, y):
                    time.sleep(0.5)

                    focused = self.device(focused=True)
                    if focused.exists:
                        focused.clear_text()
                        time.sleep(0.3)
                        focused.set_text(text)
                        time.sleep(0.5)

                        # Verify success
                        self.hide_keyboard()
                        return True

            # Fall back to regular text input
            return self.input_text(text)

        except Exception as e:
            self.logger.error(f"Error in input_text_to_field: {e}")
            return False

    @task_phase("cleanup", measure_performance=True)
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("Cleaning up UIAutomator adapter resources")
            self.device = None
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

    def _get_system_navigation_bounds(self) -> Dict[str, Any]:
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

    def click_by_resource_id(self, resource_id: str) -> bool:
        """
        Click on an element identified by resource ID.

        Args:
            resource_id: Resource ID of the element to click

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug(f"Clicking element with resource ID: {resource_id}")

            if not self.device:
                raise ADBError("No connection to device")

            # Find the element by resource ID
            element = self.device(resourceId=resource_id)
            if not element.exists:
                self.logger.warning(f"Element with resource ID {resource_id} not found")
                return False

            # Get element information
            try:
                # Try to use element.click() directly first
                element.click()
                time.sleep(0.3)
                return True
            except Exception as e:
                self.logger.debug(f"Direct element click failed: {e}, trying with coordinates")

                # Fall back to getting bounds and clicking center
                try:
                    # Bounds in UIAutomator2 are usually returned as a dictionary with top, left, right, bottom
                    bounds = element.bounds()

                    # Calculate center coordinates - bounds format may vary depending on UIAutomator2 version
                    if isinstance(bounds, dict) and "left" in bounds:
                        # Dictionary format
                        x = (bounds["left"] + bounds["right"]) // 2
                        y = (bounds["top"] + bounds["bottom"]) // 2
                    elif isinstance(bounds, tuple) and len(bounds) == 4:
                        # Tuple format (left, top, right, bottom)
                        x = (bounds[0] + bounds[2]) // 2
                        y = (bounds[1] + bounds[3]) // 2
                    else:
                        self.logger.error(f"Unrecognized bounds format: {bounds}")
                        return False

                    # Click at the center of the element
                    return self.click(x, y)
                except Exception as e2:
                    self.logger.error(f"Error calculating bounds for click: {e2}")
                    return False

        except Exception as e:
            self.logger.error(f"Error clicking element with resource ID {resource_id}: {e}")
            return False
