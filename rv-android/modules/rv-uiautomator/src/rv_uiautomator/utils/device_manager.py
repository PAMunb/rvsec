"""
Device connection and management utilities.

Provide ADB-based device discovery, connection verification, and property
retrieval. All ADB commands use subprocess with timeouts to prevent hangs
from unresponsive devices or disconnected emulators.

### Integration Points:
    - rv-platform uses DeviceManager for device discovery before task execution
    - UIAutomator2Adapter relies on ADB connectivity managed here
    - restart_adb_server() provides recovery from stale ADB connections
"""

import subprocess
import time
from typing import Any, Dict, List

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from ..constants import DEFAULT_CONNECTION_TIMEOUT


class DeviceManager:
    """
    Manages Android device connections and state monitoring.

    ### Architectural Decisions:
    - Provides device discovery and connection management
    - Handles ADB server communication
    - Monitors device availability and health
    - Supports both emulator and physical devices

    ### Role in the System:
    - Central device management for UIAutomator operations
    - Provides reliable device connection establishment
    - Handles device lifecycle and error recovery
    - Abstracts ADB complexity from higher-level components
    """

    def __init__(self):
        """Initialize device manager.

        State:
            logger: Component logger with DeviceManager context.
        """
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_uiautomator.utils.device_manager", {CONTEXT_COMPONENT: "DeviceManager"}
        )

        self.logger.debug("DeviceManager initialized")

    @ErrorHandler.handle_errors(
        component="DeviceManager", phase="device_discovery", default_return=[]
    )
    def get_available_devices(self) -> List[str]:
        """
        Get list of available Android devices.

        Returns:
            List of device IDs that are available for connection
        """
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=DEFAULT_CONNECTION_TIMEOUT,
            )

            if result.returncode != 0:
                self.logger.error(f"ADB devices command failed: {result.stderr}")
                return []

            devices = []
            lines = result.stdout.strip().split("\n")[1:]  # Skip header

            for line in lines:
                if line.strip() and "\t" in line:
                    device_id, status = line.strip().split("\t")
                    if status == "device":  # Only include connected devices
                        devices.append(device_id)

            self.logger.info(f"Found {len(devices)} available devices: {devices}")
            return devices

        except Exception as e:
            self.logger.error(f"Device discovery failed: {e}")
            return []

    @ErrorHandler.handle_errors(component="DeviceManager", phase="device_verification")
    def verify_device_connection(self, device_id: str) -> bool:
        """
        Verify that a device is connected and responsive.

        Args:
            device_id: Device identifier to verify

        Returns:
            True if device is connected and responsive
        """
        try:
            # Check if device is listed in connected devices
            available_devices = self.get_available_devices()
            if device_id not in available_devices:
                self.logger.warning(f"Device {device_id} not in available devices list")
                return False

            # Test device responsiveness with simple command
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "echo", "test"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and "test" in result.stdout:
                self.logger.debug(f"Device {device_id} is responsive")
                return True
            else:
                self.logger.warning(f"Device {device_id} is not responsive")
                return False

        except Exception as e:
            self.logger.error(f"Device verification failed for {device_id}: {e}")
            return False

    @ErrorHandler.handle_errors(
        component="DeviceManager", phase="device_info_retrieval", default_return={}
    )
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a device.

        Args:
            device_id: Device identifier

        Returns:
            Dictionary containing device information
        """
        try:
            info = {}

            # Get device properties
            properties = [
                ("ro.product.model", "model"),
                ("ro.product.manufacturer", "manufacturer"),
                ("ro.build.version.release", "android_version"),
                ("ro.build.version.sdk", "api_level"),
                ("ro.product.cpu.abi", "cpu_abi"),
            ]

            for prop, key in properties:
                result = subprocess.run(
                    ["adb", "-s", device_id, "shell", "getprop", prop],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    info[key] = result.stdout.strip()

            # Get screen resolution
            result = subprocess.run(
                ["adb", "-s", device_id, "shell", "wm", "size"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and "Physical size:" in result.stdout:
                size_line = result.stdout.strip()
                if "x" in size_line:
                    resolution = size_line.split(":")[-1].strip()
                    info["resolution"] = resolution

            self.logger.debug(f"Retrieved device info for {device_id}: {info}")
            return info

        except Exception as e:
            self.logger.error(f"Failed to get device info for {device_id}: {e}")
            return {}

    @ErrorHandler.handle_errors(component="DeviceManager", phase="adb_restart")
    def restart_adb_server(self) -> bool:
        """
        Restart ADB server to recover from connection issues.

        Returns:
            True if ADB server restarted successfully
        """
        try:
            self.logger.info("Restarting ADB server")

            # Kill ADB server
            subprocess.run(["adb", "kill-server"], timeout=30)
            time.sleep(2)

            # Start ADB server
            result = subprocess.run(
                ["adb", "start-server"], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                self.logger.info("ADB server restarted successfully")
                return True
            else:
                self.logger.error(f"Failed to restart ADB server: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"ADB server restart failed: {e}")
            return False
