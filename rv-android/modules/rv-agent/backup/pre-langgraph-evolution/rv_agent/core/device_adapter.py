"""
Device Interface for RVAgent - Direct rv-uiautomator integration.

This module implements the EXACT integration strategy from the plan:
process isolation enables using rv-uiautomator directly without adaptation.

ARCHITECTURE: Process isolation resolved all singleton conflicts.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_uiautomator import UIAutomator2Adapter, UIAutomatorActionExecutor, StateConverter

from ..constants import RVAgentConstants
from .coordinate_extractor import extract_clickable_elements_with_coords
from .prompt_formatter import format_ui_elements_for_llm


class DeviceInterface:
    """
    RVAgent device interface using rv-uiautomator with DIRECT integration.

    PROCESS ISOLATION SUCCESS: Framework completo disponível no subprocess.
    - LoggingManager.get_instance() com instância própria do subprocess
    - ErrorHandler decorators disponíveis (instância própria)
    - rv-uiautomator integration direta (sem adaptação)

    Target app: br.unb.cic.cryptoapp (emulador já preparado)
    """

    def __init__(self, device_id: str = RVAgentConstants.DEFAULT_DEVICE_ID):
        """Initialize DeviceInterface com rv-uiautomator direto."""

        # Process isolation - LoggingManager com instância própria
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_agent.core.device_adapter",
            {"component": "DeviceInterface"}
        )

        # ErrorHandler decorators disponíveis no subprocess
        self.error_handler = ErrorHandler.get_instance()

        self.device_id = device_id
        self.logger.info(f"[RVAGENT_DEBUG] Initializing DeviceInterface for {device_id}")

        # Direct rv-uiautomator integration (NO ADAPTATION NEEDED)
        try:
            self.ui_adapter = UIAutomator2Adapter(device_id=device_id)
            self.action_executor = UIAutomatorActionExecutor()
            self.state_converter = StateConverter()

            self.logger.info("[RVAGENT_DEBUG] ✅ rv-uiautomator components initialized successfully")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] ❌ Failed to initialize rv-uiautomator: {e}")
            raise

    def connect_to_device(self) -> bool:
        """Connect to Android device/emulator."""
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Connecting to device {self.device_id}")

            # Test device connectivity with available method
            connected = self.ui_adapter.connect(self.device_id)

            if connected:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ Device connected successfully")

                # Configure device for optimal testing (like DroidBot)
                self._configure_device_for_testing()

                return True
            else:
                self.logger.error(f"[RVAGENT_DEBUG] ❌ Device connection failed")
                return False

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Device connection failed: {e}")
            return False

    def _configure_device_for_testing(self) -> None:
        """Configure device settings for optimal testing experience."""
        try:
            import subprocess

            self.logger.info(f"[RVAGENT_DEBUG] Configuring device for testing...")
            print(f"[DEVICE_CONFIG] 🔧 Starting device configuration...")

            # Commands to optimize device for testing
            commands = [
                # Enable visual touch feedback (so we can see clicks)
                f"adb -s {self.device_id} shell settings put global show_touches 1",

                # Enable pointer location visualization
                f"adb -s {self.device_id} shell settings put global pointer_location 1",

                # Disable virtual keyboard to reduce XML complexity (ENHANCED)
                f"adb -s {self.device_id} shell ime disable com.google.android.inputmethod.latin/.LatinIME",
                f"adb -s {self.device_id} shell settings put secure show_ime_with_hard_keyboard 0",
                f"adb -s {self.device_id} shell ime set null",

                # Keep screen awake during testing
                f"adb -s {self.device_id} shell settings put global stay_on_while_plugged_in 7",

                # Disable auto-rotate to maintain consistent coordinates
                f"adb -s {self.device_id} shell settings put global accelerometer_rotation 0"
            ]

            for cmd in commands:
                try:
                    result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        self.logger.debug(f"[RVAGENT_DEBUG] ✅ {cmd.split()[-2:]} configured")
                        print(f"[DEVICE_CONFIG] ✅ {cmd.split()[-2:]} configured")
                    else:
                        self.logger.warning(f"[RVAGENT_DEBUG] ⚠️ {cmd.split()[-2:]} failed: {result.stderr}")
                        print(f"[DEVICE_CONFIG] ❌ {cmd.split()[-2:]} failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"[RVAGENT_DEBUG] ⚠️ Command timeout: {cmd}")
                except Exception as e:
                    self.logger.warning(f"[RVAGENT_DEBUG] ⚠️ Command error: {e}")

            self.logger.info(f"[RVAGENT_DEBUG] ✅ Device configuration completed")
            print(f"[DEVICE_CONFIG] ✅ Device configuration completed")

        except Exception as e:
            self.logger.warning(f"[RVAGENT_DEBUG] ⚠️ Device configuration failed: {e}")
            # Not critical, continue anyway

    def launch_app(self, package_name: str) -> bool:
        """Launch target application."""
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Launching app: {package_name}")

            # Use UIAutomator2 to launch app (app_start method)
            import subprocess
            launch_command = f"adb -s {self.device_id} shell am start -n {package_name}/.MainActivity"
            result = subprocess.run(launch_command.split(), capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ App {package_name} launched successfully")
                time.sleep(3)  # Allow app to load
                return True
            else:
                self.logger.error(f"[RVAGENT_DEBUG] ❌ Failed to launch {package_name}: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] App launch error: {e}")
            return False

    def get_current_ui_state(self) -> Dict[str, Any]:
        """
        Get current UI state with coordinate enhancement.

        CRITICAL: Uses extract_clickable_elements_with_coords() for 100% success rate.
        """
        try:
            self.logger.debug("[RVAGENT_DEBUG] Capturing UI state...")

            # Get UI state via rv-uiautomator
            ui_state_data = self.ui_adapter.get_ui_state()

            if not ui_state_data or 'xml' not in ui_state_data:
                self.logger.warning("[RVAGENT_DEBUG] No UI state received")
                return {}

            ui_dump = ui_state_data['xml']
            current_activity = ui_state_data.get('current_activity', 'unknown')  # Fixed key mapping
            current_package = ui_state_data.get('current_package', 'unknown')    # Fixed key mapping

            # DEBUG: Log package detection issue
            self.logger.debug(f"[RVAGENT_DEBUG] 🔍 UI state data keys: {list(ui_state_data.keys())}")
            self.logger.debug(f"[RVAGENT_DEBUG] 📦 Package from adapter: '{current_package}'")
            self.logger.debug(f"[RVAGENT_DEBUG] 🎯 Activity from adapter: '{current_activity}'")

            # CRITICAL: Extract elements with coordinates (100% vs 30% success)
            clickable_elements = extract_clickable_elements_with_coords(ui_dump)

            # Format for LLM with coordinate enhancement
            formatted_elements = format_ui_elements_for_llm(ui_dump)

            ui_state = {
                "xml": ui_dump,
                "activity": current_activity,
                "current_package": current_package,
                "clickable_elements": clickable_elements,
                "formatted_elements": formatted_elements,
                "element_count": len(clickable_elements),
                "timestamp": time.time(),
                "hash_screen": self._generate_screen_hash(ui_dump)
            }

            self.logger.info(f"[RVAGENT_DEBUG] UI state captured: {len(clickable_elements)} elements")
            self.logger.debug(f"[RVAGENT_DEBUG] Activity: {current_activity}")

            return ui_state

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] UI state capture failed: {e}")
            return {}

    def take_screenshot(self, output_dir: str = "./screenshots") -> Optional[str]:
        """Take screenshot of current screen."""
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time())
            screenshot_path = f"{output_dir}/screenshot_{timestamp}.png"

            screenshot_path_actual = self.ui_adapter.take_screenshot()
            success = screenshot_path_actual is not None
            if success and screenshot_path_actual != screenshot_path:
                # Move to desired location
                import shutil
                shutil.move(screenshot_path_actual, screenshot_path)

            if success:
                self.logger.debug(f"[RVAGENT_DEBUG] Screenshot saved: {screenshot_path}")
                return screenshot_path
            else:
                self.logger.warning("[RVAGENT_DEBUG] Screenshot failed")
                return None

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Screenshot error: {e}")
            return None

    # ============================================================================
    # APP STATE MONITORING
    # ============================================================================

    def is_target_app_active(self, target_package: str) -> bool:
        """
        Check if target app is currently active.

        Args:
            target_package: Expected package name (e.g., 'br.unb.cic.cryptoapp')

        Returns:
            True if target app is active, False otherwise
        """
        try:
            ui_state_data = self.ui_adapter.get_ui_state()
            if not ui_state_data:
                return False

            current_package = ui_state_data.get('package', '')
            current_activity = ui_state_data.get('activity', '')

            # Check if we're in the target app
            # Activity starting with '.' means it's in the same package
            if current_activity.startswith('.'):
                full_activity = current_package + current_activity
            else:
                full_activity = current_activity

            # We're in target app if package matches
            is_active = current_package == target_package

            self.logger.debug(f"[RVAGENT_DEBUG] App check - Expected: {target_package}")
            self.logger.debug(f"[RVAGENT_DEBUG] Current: {current_package} / {current_activity}")
            self.logger.debug(f"[RVAGENT_DEBUG] Full activity: {full_activity}")
            self.logger.debug(f"[RVAGENT_DEBUG] Is active: {is_active}")

            return is_active

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] App state check failed: {e}")
            return False

    def get_current_package(self) -> str:
        """Get current active package name."""
        try:
            ui_state_data = self.ui_adapter.get_ui_state()
            return ui_state_data.get('current_package', 'unknown') if ui_state_data else 'unknown'  # Fixed key mapping
        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Package detection failed: {e}")
            return 'unknown'

    def restart_target_app(self, target_package: str) -> bool:
        """
        Restart target application.

        Args:
            target_package: Package to restart

        Returns:
            True if restart successful, False otherwise
        """
        try:
            self.logger.info(f"[RVAGENT_DEBUG] Restarting app: {target_package}")

            # Force stop the app first
            import subprocess
            stop_command = f"adb -s {self.device_id} shell am force-stop {target_package}"
            subprocess.run(stop_command.split(), capture_output=True)
            time.sleep(1)

            # Launch the app again
            success = self.launch_app(target_package)

            if success:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ App restart successful: {target_package}")
            else:
                self.logger.error(f"[RVAGENT_DEBUG] ❌ App restart failed: {target_package}")

            return success

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] App restart error: {e}")
            return False

    # ============================================================================
    # ACTION METRICS AND TRACKING
    # ============================================================================

    def _log_action_metrics(self, action_type: str, success: bool, coordinates: tuple = None,
                           element_description: str = "", additional_data: Dict[str, Any] = None):
        """
        Log action metrics for UI coverage and distribution analysis.

        Args:
            action_type: Type of action (click, input, scroll, back, screenshot)
            success: Whether action was successful
            coordinates: Click coordinates if applicable
            element_description: Description of target element
            additional_data: Additional metrics data
        """
        try:
            metrics = {
                "timestamp": time.time(),
                "action_type": action_type,
                "success": success,
                "coordinates": coordinates,
                "element_description": element_description
            }

            # Add additional data if provided
            if additional_data:
                metrics.update(additional_data)

            # Log for later analysis
            self.logger.info(f"[RVAGENT_METRICS] {metrics}")

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Metrics logging failed: {e}")

    def _generate_screen_hash(self, ui_dump: str) -> str:
        """Generate simple hash for screen state identification."""
        import hashlib
        return hashlib.md5(ui_dump.encode()).hexdigest()[:12]

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        try:
            return {
                "device_id": self.device_id,
                "status": "connected"
            }
        except Exception as e:
            self.logger.error(f"Device info error: {e}")
            return {"device_id": self.device_id, "status": "error", "error": str(e)}

    def validate_app_running(self, package_name: str) -> bool:
        """Validate that target app is running."""
        try:
            # Get current UI state to check package
            ui_state_data = self.ui_adapter.get_ui_state()
            current_package = ui_state_data.get('package', 'unknown') if ui_state_data else 'unknown'

            is_running = current_package == package_name

            self.logger.debug(f"[RVAGENT_DEBUG] App validation - Expected: {package_name}, Current: {current_package}")

            return is_running

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] App validation error: {e}")
            return False

    # ============================================================================
    # LANGCHAIN TOOLS INTEGRATION METHODS
    # ============================================================================

    def click(self, x: int, y: int) -> bool:
        """
        Click at specific coordinates - for LangChain AndroidClickTool.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            True if click successful, False otherwise
        """
        try:
            self.logger.debug(f"[RVAGENT_DEBUG] Clicking at ({x}, {y})")

            # Use UIAutomator2Adapter directly (bypassing ActionExecutor)
            success = self.ui_adapter.click(x, y)

            if success:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ Click successful at ({x}, {y})")
                time.sleep(0.5)  # Allow UI to update
            else:
                self.logger.warning(f"[RVAGENT_DEBUG] ❌ Click failed at ({x}, {y})")

            # Log metrics for analysis
            self._log_action_metrics("click", success, coordinates=(x, y))

            return success

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Click action failed: {e}")
            return False

    def input_text(self, text: str) -> bool:
        """
        Input text into focused field - for LangChain AndroidInputTool.

        Args:
            text: Text to input

        Returns:
            True if input successful, False otherwise
        """
        try:
            self.logger.debug(f"[RVAGENT_DEBUG] Inputting text: '{text}'")

            # Use UIAutomator2Adapter directly
            success = self.ui_adapter.input_text(text)

            if success:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ Text input successful: '{text}'")
                time.sleep(0.3)  # Allow input to register
            else:
                self.logger.warning(f"[RVAGENT_DEBUG] ❌ Text input failed: '{text}'")

            return success

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Input text action failed: {e}")
            return False

    def scroll(self, direction: str, distance: str = "medium") -> bool:
        """
        Scroll in specified direction - for LangChain AndroidScrollTool.

        Args:
            direction: 'up', 'down', 'left', 'right'
            distance: 'short', 'medium', 'long'

        Returns:
            True if scroll successful, False otherwise
        """
        try:
            self.logger.debug(f"[RVAGENT_DEBUG] Scrolling {direction} ({distance})")

            # Map distance to pixels
            distance_map = {"short": 200, "medium": 400, "long": 600}
            pixels = distance_map.get(distance, 400)

            # Use screen center as base point for scroll
            # TODO: Get actual screen dimensions from adapter
            center_x, center_y = 540, 960  # Typical phone screen center

            # Calculate scroll coordinates
            if direction == "down":
                start_x, start_y = center_x, center_y - pixels // 2
                end_x, end_y = center_x, center_y + pixels // 2
            elif direction == "up":
                start_x, start_y = center_x, center_y + pixels // 2
                end_x, end_y = center_x, center_y - pixels // 2
            elif direction == "left":
                start_x, start_y = center_x + pixels // 2, center_y
                end_x, end_y = center_x - pixels // 2, center_y
            elif direction == "right":
                start_x, start_y = center_x - pixels // 2, center_y
                end_x, end_y = center_x + pixels // 2, center_y
            else:
                self.logger.error(f"[RVAGENT_DEBUG] Invalid scroll direction: {direction}")
                return False

            # Execute swipe using UIAutomator2Adapter
            success = self.ui_adapter.swipe(start_x, start_y, end_x, end_y, duration=0.5)

            if success:
                self.logger.info(f"[RVAGENT_DEBUG] ✅ Scroll successful: {direction} ({distance})")
                time.sleep(0.5)  # Allow scroll to complete
            else:
                self.logger.warning(f"[RVAGENT_DEBUG] ❌ Scroll failed: {direction}")

            return success

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Scroll action failed: {e}")
            return False

    def back(self) -> bool:
        """
        Navigate back - for LangChain AndroidBackTool.

        Returns:
            True if back navigation successful, False otherwise
        """
        try:
            self.logger.debug("[RVAGENT_DEBUG] Navigating back")

            # Use UIAutomator2Adapter directly
            success = self.ui_adapter.press_back()

            if success:
                self.logger.info("[RVAGENT_DEBUG] ✅ Back navigation successful")
                time.sleep(0.5)  # Allow navigation to complete
            else:
                self.logger.warning("[RVAGENT_DEBUG] ❌ Back navigation failed")

            return success

        except Exception as e:
            self.logger.error(f"[RVAGENT_DEBUG] Back action failed: {e}")
            return False