"""
Android device interface for RV-Agent.

This module provides a unified interface for interacting with Android emulators
through UIAutomator2, enabling screenshot capture, UI state retrieval, and action execution.
"""

import time
from pathlib import Path
from typing import Dict, Optional

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_uiautomator import UIAutomator2Adapter

from ..constants import RVAgentConstants
from ..domain.exceptions import DeviceError


class DeviceInterface:
    """
    Provides Android emulator interaction capabilities for agent actions.

    ### Architectural Decisions:
    - Integrates with rv-uiautomator for device control
    - Enforces emulator-only device connections
    - Provides high-level action methods (click, input, scroll, back)
    - Implements proper resource cleanup and error handling
    - Tracks action execution metrics for debugging

    ### Role in the System:
    - Serves as the bridge between agent decisions and Android device actions
    - Captures screenshots for vision model input
    - Extracts UI state for element identification
    - Executes touch, input, and navigation actions
    - Validates device state and app execution
    """

    def __init__(self, device_id: str = RVAgentConstants.DEFAULT_DEVICE_ID):
        """
        Initialize device interface with emulator connection.

        Args:
            device_id: Device identifier (must be emulator)

        Raises:
            ValueError: If device_id is not an emulator identifier
            RuntimeError: If device connection fails
        """
        # Validate emulator device ID
        if not self._is_emulator_device(device_id):
            raise ValueError(
                f"Only emulator devices supported, got: {device_id}. "
                f"Expected format: 'emulator-XXXX' or 'localhost:XXXX'"
            )

        self.device_id = device_id

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.device_interface", {CONTEXT_COMPONENT: "DeviceInterface"}
        )

        # Initialize UIAutomator2 adapter
        try:
            self.ui_adapter = UIAutomator2Adapter(device_id=device_id)

            # Connect to device
            if not self.ui_adapter.connect(device_id):
                raise RuntimeError(f"Failed to connect to device {device_id}")

            self.logger.info(f"Connected to emulator: {device_id}")

            # Disable soft keyboard to keep UI clean for screenshots
            self.disable_soft_keyboard()

        except Exception as e:
            raise DeviceError(f"Failed to connect to emulator {device_id}: {e}") from e

    def _is_emulator_device(self, device_id: str) -> bool:
        """
        Check if device ID represents an emulator.

        Args:
            device_id: Device identifier

        Returns:
            True if emulator, False otherwise
        """
        return (
            device_id.startswith("emulator-")
            or device_id.startswith("localhost:")
            or device_id.startswith("127.0.0.1:")
        )

    def take_screenshot(self, output_dir: str = "/tmp") -> Optional[str]:
        """
        Capture screenshot from device.

        Args:
            output_dir: Directory to save screenshot

        Returns:
            Path to saved screenshot, or None if failed
        """
        try:
            import shutil

            # Use UIAutomator2Adapter's take_screenshot() which saves to current dir
            screenshot_path = self.ui_adapter.take_screenshot()

            if screenshot_path and Path(screenshot_path).exists():
                # Move to desired output directory if different
                target_path = Path(output_dir) / Path(screenshot_path).name
                Path(output_dir).mkdir(parents=True, exist_ok=True)

                # Use shutil.move() to work across filesystems
                shutil.move(screenshot_path, target_path)

                self.logger.debug(f"Screenshot saved: {target_path}")
                return str(target_path)

            self.logger.error("Screenshot capture failed")
            return None

        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    def get_screen_size(self) -> tuple[int, int]:
        """
        Get device screen dimensions.

        Returns:
            Tuple of (width, height) in pixels
        """
        try:
            # Get device info which contains screen dimensions
            device_info = self.ui_adapter.device.info
            if device_info:
                width = device_info.get("displayWidth", 1080)
                height = device_info.get("displayHeight", 1920)
                self.logger.debug(f"Screen size: {width}x{height}")
                return (width, height)
            else:
                self.logger.warning(
                    "Could not get screen size, using default 1080x1920"
                )
                return (1080, 1920)
        except Exception as e:
            self.logger.error(f"Failed to get screen size: {e}")
            return (1080, 1920)  # Default Android resolution

    def get_current_ui_state(self) -> Optional[Dict]:
        """
        Get current UI state as XML dump.

        Returns:
            Dict with UI state information, or None if failed
        """
        try:
            return self.ui_adapter.get_ui_state()
        except Exception as e:
            self.logger.error(f"UI state retrieval failed: {e}")
            return None

    def launch_app(self, package_name: str) -> bool:
        """
        Launch application.

        Args:
            package_name: Package name to launch

        Returns:
            True if successful
        """
        try:
            self.logger.info(f"Launching app: {package_name}")
            success = self.ui_adapter.launch_app(package_name)
            if success:
                time.sleep(2)  # Wait for app to initialize
                return success
            else:
                self.logger.error("App launch failed")
                raise DeviceError(f"Failed to launch app {package_name}")
        except DeviceError:
            raise
        except Exception as e:
            self.logger.error(f"App launch failed: {e}")
            raise DeviceError(f"Failed to launch app {package_name}: {e}") from e

    def stop_app(self, package_name: str) -> bool:
        """Stop application."""
        return self.ui_adapter.stop_app(package_name)

    def start_app(self, package_name: str) -> bool:
        """Start application (alias for launch_app)."""
        return self.launch_app(package_name)

    def click(self, x: int, y: int) -> bool:
        """
        Click at screen coordinates.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if click successful
        """
        try:
            self.logger.debug(f"Clicking at ({x}, {y})")
            success = self.ui_adapter.click(x, y)
            if success:
                time.sleep(0.5)  # Allow UI to update
            return success
        except Exception as e:
            self.logger.error(f"Click failed: {e}")
            return False

    def input_text(self, text: str) -> bool:
        """
        Input text into focused field.

        Args:
            text: Text to input

        Returns:
            True if successful
        """
        try:
            self.logger.debug(f"Inputting text: '{text}'")
            success = self.ui_adapter.input_text(text)
            if success:
                time.sleep(0.3)  # Allow input to register
            return success
        except Exception as e:
            self.logger.error(f"Text input failed: {e}")
            return False

    def clear_text(self) -> bool:
        """
        Clear text in currently focused field.

        Uses UIAutomator2's clear_text if available, otherwise
        selects all text and deletes it via key events.

        Returns:
            True if successful
        """
        try:
            self.logger.debug("Clearing text in focused field")
            clear_method = getattr(self.ui_adapter, "clear_text", None)
            if clear_method:
                return clear_method()
            # Fallback: Ctrl+A then Delete via shell
            import subprocess

            subprocess.run(
                [
                    "adb",
                    "-s",
                    self.device_id,
                    "shell",
                    "input",
                    "keyevent",
                    "KEYCODE_MOVE_HOME",
                ],
                capture_output=True,
                timeout=5,
            )
            subprocess.run(
                [
                    "adb",
                    "-s",
                    self.device_id,
                    "shell",
                    "input",
                    "keyevent",
                    "--longpress",
                    "67",
                ],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception as e:
            self.logger.error(f"Clear text failed: {e}")
            return False

    def scroll(self, direction: str, distance: str = "medium") -> bool:
        """
        Scroll in specified direction.

        Args:
            direction: 'up', 'down', 'left', 'right'
            distance: 'short', 'medium', 'long'

        Returns:
            True if successful
        """
        try:
            self.logger.debug(f"Scrolling {direction} ({distance})")

            distance_map = {"short": 200, "medium": 400, "long": 600}
            pixels = distance_map.get(distance, 400)
            center_x, center_y = 540, 960

            # Calculate scroll coordinates
            direction_map = {
                "down": (
                    center_x,
                    center_y - pixels // 2,
                    center_x,
                    center_y + pixels // 2,
                ),
                "up": (
                    center_x,
                    center_y + pixels // 2,
                    center_x,
                    center_y - pixels // 2,
                ),
                "left": (
                    center_x + pixels // 2,
                    center_y,
                    center_x - pixels // 2,
                    center_y,
                ),
                "right": (
                    center_x - pixels // 2,
                    center_y,
                    center_x + pixels // 2,
                    center_y,
                ),
            }

            if direction not in direction_map:
                self.logger.error(f"Invalid scroll direction: {direction}")
                return False

            start_x, start_y, end_x, end_y = direction_map[direction]
            success = self.ui_adapter.swipe(
                start_x, start_y, end_x, end_y, duration=0.5
            )

            if success:
                time.sleep(0.5)  # Allow scroll to complete
            return success

        except Exception as e:
            self.logger.error(f"Scroll failed: {e}")
            return False

    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """
        Long click at screen coordinates.

        Args:
            x: X coordinate
            y: Y coordinate
            duration: Hold duration in seconds (default 1.0)

        Returns:
            True if long click successful
        """
        try:
            self.logger.debug(f"Long clicking at ({x}, {y}) for {duration}s")
            success = self.ui_adapter.long_click(x, y)
            if success:
                time.sleep(0.5)  # Allow UI to update
            return success
        except Exception as e:
            self.logger.error(f"Long click failed: {e}")
            return False

    def home(self) -> bool:
        """
        Press HOME button to go to launcher.

        Returns:
            True if successful
        """
        try:
            self.logger.debug("Pressing HOME button")
            success = self.ui_adapter.press_home()
            if success:
                time.sleep(1.0)  # Allow transition
            return success
        except Exception as e:
            self.logger.error(f"HOME button failed: {e}")
            return False

    def disable_soft_keyboard(self) -> bool:
        """
        Disable Android soft keyboard to prevent it from appearing.

        Uses ADB to disable the virtual keyboard, which prevents it from
        appearing when text fields are focused. This keeps the UI clean
        for screenshot analysis.

        Returns:
            True if successful
        """
        try:
            import subprocess

            self.logger.info("Disabling Android soft keyboard via ADB")

            # Disable IME (Input Method Editor) soft keyboard
            cmd = f"adb -s {self.device_id} shell settings put secure show_ime_with_hard_keyboard 0"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                self.logger.info("✅ Soft keyboard disabled successfully")
                return True
            else:
                self.logger.warning(f"Failed to disable keyboard: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Keyboard disable failed: {e}")
            return False

    def back(self) -> bool:
        """
        Press back button.

        Returns:
            True if successful
        """
        try:
            self.logger.debug("Pressing back button")
            success = self.ui_adapter.press_back()
            if success:
                time.sleep(0.5)  # Allow navigation to complete
            return success
        except Exception as e:
            self.logger.error(f"Back button failed: {e}")
            return False

    def press_keycode(self, keycode: int) -> bool:
        """
        Press Android keycode.

        Args:
            keycode: Android keycode (e.g., 66 for ENTER, 4 for BACK, 3 for HOME)

        Returns:
            True if successful
        """
        try:
            self.logger.debug(f"Pressing keycode {keycode}")
            success = self.ui_adapter.press_keycode(keycode)  # TODO(#22): implementar
            if success:
                time.sleep(0.3)  # Allow key press to register
            return success
        except Exception as e:
            self.logger.error(f"Keycode press failed: {e}")
            return False

    def swipe(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5
    ) -> bool:
        """
        Swipe from start to end coordinates.

        Args:
            start_x: Start X coordinate
            start_y: Start Y coordinate
            end_x: End X coordinate
            end_y: End Y coordinate
            duration: Swipe duration in seconds (default 0.5)

        Returns:
            True if swipe successful
        """
        try:
            self.logger.debug(
                f"Swiping from ({start_x}, {start_y}) to ({end_x}, {end_y}) "
                f"duration={duration}s"
            )
            success = self.ui_adapter.swipe(
                start_x, start_y, end_x, end_y, duration=duration
            )
            if success:
                time.sleep(0.5)  # Allow UI to settle after swipe
            return success
        except Exception as e:
            self.logger.error(f"Swipe failed: {e}")
            return False
