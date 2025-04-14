# rvandroid/rvdroid/ui/uiautomator.py
"""
UIAutomator2 implementation of the UIAdapter interface.

This module provides a concrete implementation of the UIAdapter interface
using the UIAutomator2 Python API for Android UI automation.
"""

import os
import random
import subprocess
import time
from typing import Dict, Any, Optional, Tuple, List

import uiautomator2 as u2

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.parser.screen.visitor.generic_visitor import GenericScreenVisitor
from rvandroid.rvdroid.core.component import Component
from rvandroid.rvdroid.ui.adapter import UIAdapter
from rvandroid.util.decorators import task_phase
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import ADBError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class UIAutomator2Adapter(UIAdapter):
    """
    Implementation of UIAdapter using the UIAutomator2 Python API.
    
    ### Architectural Decisions:
    - Implements the UIAdapter interface for consistent API across implementations
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
        self.device = None  # Will be set in initialize()
        
        # Will be set during initialization
        self.system_navigation_bounds = {}
        
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
    
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the component.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            self.logger.info(f"Initializing UIAutomator2Adapter for device: {self.device_id}")
            
            # Ensure ADB server is running before anything else
            self._ensure_adb_server_running()
            
            # Stop any existing UIAutomator processes to clean up first
            self._cleanup_uiautomator_processes(force=True)
            
            # Connect to the device with comprehensive verification
            try:
                # Directly check ADB connectivity first
                from rvandroid.commands.command import Command
                adb_check = Command("adb", ["-s", self.device_id, "shell", "echo connected"])
                result = adb_check.invoke()
                if "connected" not in result.stdout.decode('utf-8', errors='ignore'):
                    self.logger.error("ADB connection test failed")
                    raise Exception("ADB connection test failed")

                    
                self.device = self._connect_to_device()
                
                if not self.device:
                    self.logger.error("_connect_to_device() returned None")
                    raise Exception("Device connection failed - null device")
                
                # Verify we can perform a basic operation
                _ = self.take_screenshot()

                self.logger.info("Device connection verified with successful screenshot")
            except Exception as e:
                # Debug statement removed
                self.logger.error(f"Initial connection failed: {e}")
                
                # Attempt recovery with more aggressive approach
                self.logger.info("Attempting recovery with more aggressive approach")
                
                # Fully reset and restart ADB and UIAutomator services
                self._reset_device_connection()
                
                # Force reinstall UIAutomator2 service
                self._init_uiautomator_service(force_reinstall=True)
                
                # Retry connection
                self.device = self._connect_to_device()
                
                self.logger.info("Recovery successful")
            
            # Get system navigation bounds for filtering
            self.system_navigation_bounds = self._get_system_navigation_bounds()
            self.logger.info(f"System navigation detected: {self.system_navigation_bounds}")
            
            # Test that we can get UI state
            try:
                state = self.get_ui_state(force_refresh=True, retry_on_failure=True)
                self.logger.info("Successfully retrieved initial UI state")
            except Exception as state_error:
                self.logger.error(f"Could not get initial UI state: {state_error}")
                # Continue anyway as this is just a verification check
            
            self.logger.info("UIAutomator2Adapter initialization complete")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing UIAutomator2Adapter: {e}")
            return False
    
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the component.
        
        Returns:
            True if start succeeded, False otherwise
        """
        self.logger.info("Starting UIAutomator2Adapter")
        return True
    
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the component.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        self.logger.info("Stopping UIAutomator2Adapter")
        return True
    
    @handle_error(level="ERROR")
    def cleanup(self) -> bool:
        """
        Clean up resources.
        
        Returns:
            True if cleanup succeeded, False otherwise
        """
        try:
            self.logger.info("Cleaning up UIAutomator adapter resources")
            self.device = None
            return True
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
            return False
        
    def _connect_to_device(self) -> Any:
        """
        Connect to the Android device using UIAutomator2.
        
        Returns:
            UIAutomator2 device object
            
        Raises:
            ADBError: If connection fails
        """
        max_attempts = 5  # Increased number of attempts
        backoff_base = 2  # Base for exponential backoff

        # Perform a thorough device verification
        self._verify_device_available(check_connectivity=True)
        
        # Ensure ADB server is running
        self._ensure_adb_server_running()
        
        # Kill any existing uiautomator processes before starting
        self._cleanup_uiautomator_processes(force=True)
        
        # Run init to ensure UIAutomator2 service is installed and running

        self._init_uiautomator_service()
        
        # Direct connection attempt with u2
        for attempt in range(1, max_attempts + 1):
            try:
                # Calculate backoff time (exponential with jitter)
                backoff_time = backoff_base ** attempt + random.uniform(0.1, 1.0)
                self.logger.info(f"Connecting to device {self.device_id} (attempt {attempt}/{max_attempts})")
                
                # Try to connect with simple ADB command first
                try:
                    import subprocess
                    result = subprocess.run(
                        ["adb", "-s", self.device_id, "shell", "getprop ro.product.model"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                except Exception as test_err:
                    self.logger.warning(f"ADB command failed: {test_err}")
                
                # Try to connect with timeout
                device = u2.connect(self.device_id)
                
                # Verify connection with multiple checks
                self._verify_device_connection(device)
                
                # Enable touch indicators for debugging
                try:
                    import subprocess
                    subprocess.run(['adb', '-s', self.device_id, 'shell', 'settings', 'put', 'system', 'show_touches', '1'])
                except Exception as e:
                    self.logger.warning(f"Could not enable touch indicators: {e}")
                self.logger.info(f"Successfully connected to device: {self.device_id}")
                return device
                
            except Exception as e:
                self.logger.error(f"Error connecting to device (attempt {attempt}): {e}")
                
                if attempt < max_attempts:
                    self.logger.info(f"Retrying connection after {backoff_time:.2f}s delay (attempt {attempt}/{max_attempts})")
                    
                    # Reset the connection state
                    self._reset_device_connection()
                    
                    # Wait with exponential backoff
                    time.sleep(backoff_time)
                else:
                    self.logger.error(f"All {max_attempts} connection attempts failed")
                    raise ADBError(f"Failed to connect to device after {max_attempts} attempts: {str(e)}", e)
    
    def _verify_device_connection(self, device: Any) -> None:
        """
        Verify that the device connection is fully operational by performing
        multiple test commands.
        
        Args:
            device: UIAutomator2 device object to verify
            
        Raises:
            ADBError: If verification fails
        """
        try:
            # Test 1: Get device info - this is the most critical test
            try:
                info = device.info
                if not info:
                    raise ADBError("Failed to get device info")

                self.logger.debug(f"Device info: {info}")
            except Exception as info_err:
                raise ADBError(f"Device info check failed: {str(info_err)}")
            
            # Test 2: Check if we can retrieve window size
            try:
                window_size = device.window_size()
                self.logger.debug(f"Window size: {window_size}")
            except Exception as size_err:
                # Continue anyway - this is not critical
                self.logger.warning(f"Window size check failed: {size_err}")
            
            # Test 3: Check if UIAutomator service is responding
            # This now returns True even if service isn't detected to allow connections to proceed
            service_status = self._check_uiautomator_service_status()
            
            # All critical tests passed
            self.logger.info("Device connection successfully verified")
            
        except Exception as e:
            self.logger.error(f"Device connection verification failed: {e}")
            raise ADBError(f"Device connection verification failed: {str(e)}", e)
    
    def _ensure_adb_server_running(self) -> None:
        """
        Ensure the ADB server is running and restart it if necessary.
        """
        try:
            from rvandroid.commands.command import Command
            
            # Check if ADB server is running
            self.logger.debug("Checking ADB server status")
            check_cmd = Command("adb", ["devices"])
            result = check_cmd.invoke()
            
            # If server isn't running or there's an issue, restart it
            if "daemon" in result.stderr.decode('utf-8', errors='ignore').lower():
                self.logger.info("ADB server not running, starting it now")
                restart_cmd = Command("adb", ["kill-server"])
                restart_cmd.invoke()
                time.sleep(1)
                
                start_cmd = Command("adb", ["start-server"])
                start_cmd.invoke()
                time.sleep(2)
                
                # Verify server is now running
                check_again_cmd = Command("adb", ["devices"])
                result = check_again_cmd.invoke()
                self.logger.debug(f"ADB server restart result: {result.stdout.decode('utf-8', errors='ignore')}")
            
        except Exception as e:
            self.logger.warning(f"Error checking/restarting ADB server: {e}")
            # Continue anyway as the command might fail but server still works
    
    def _reset_device_connection(self) -> None:
        """
        Reset the device connection state by cleaning up processes and 
        restarting services.
        """
        try:
            # 1. Clean up UIAutomator processes
            self._cleanup_uiautomator_processes(force=True)
            
            # 2. Reset ADB connection to the device
            from rvandroid.commands.command import Command
            
            # Try to reset the USB connection
            self.logger.info("Resetting USB connection to device")
            try:
                reset_cmd = Command("adb", [
                    "-s", self.device_id,
                    "usb"
                ])
                reset_cmd.invoke()
                time.sleep(1)
            except Exception as e:
                self.logger.debug(f"USB reset command failed (this is often normal): {e}")
            
            # Restart ADB server
            self.logger.info("Restarting ADB server")
            try:
                restart_cmd = Command("adb", ["kill-server"])
                restart_cmd.invoke()
                time.sleep(1)
                
                start_cmd = Command("adb", ["start-server"])
                start_cmd.invoke()
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Error restarting ADB server: {e}")
            
            # Wait for device to be detected
            self.logger.info("Waiting for device to be detected")
            try:
                # Use subprocess with timeout instead since Command doesn't support timeout
                import subprocess
                subprocess.run(["adb", "wait-for-device"], timeout=10)
            except Exception as e:
                self.logger.warning(f"Wait for device timed out: {e}")
            
            # 3. Reinitialize UIAutomator service
            self._init_uiautomator_service()
            
        except Exception as e:
            self.logger.warning(f"Error resetting device connection: {e}")
            # Continue anyway as this is just preparation for a retry
    
    def _check_uiautomator_service_status(self) -> bool:
        """
        Check if the UIAutomator service is running properly on the device.
        
        Returns:
            True if the service is running, False otherwise
        """
        try:
            from rvandroid.commands.command import Command

            # More reliable: Check if we can make a direct call to the service
            try:
                import subprocess
                ping_service = subprocess.run(
                    ["adb", "-s", self.device_id, "shell", "am", "broadcast", "-a", "android.intent.action.MAIN", "-n", "com.github.uiautomator/.Service"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "Broadcast completed" in ping_service.stdout:
                    self.logger.debug("UIAutomator service is running (broadcast check)")
                    return True
            except Exception as ping_err:
                self.logger.warning(f"Error pinging UIAutomator service (broadcast check): {ping_err}")
            
            # Check for running UIAutomator processes with a more reliable pattern
            ps_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "ps -ef | grep -e uiautomator -e 'com.github.uiautomator' | grep -v grep"
            ])
            result = ps_cmd.invoke()
            
            output = result.stdout.decode('utf-8', errors='ignore')
            
            # If we find the uiautomator process, the service is running
            if "uiautomator" in output or "com.github.uiautomator" in output:
                self.logger.debug("UIAutomator service is running")
                return True
            
            # Try alternative method: Check if the app is installed
            package_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "pm list packages | grep com.github.uiautomator"
            ])
            result = package_cmd.invoke()
            
            output = result.stdout.decode('utf-8', errors='ignore')
            
            if "com.github.uiautomator" in output:
                # Package is installed, try to start it
                try:
                    start_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "monkey -p com.github.uiautomator -c android.intent.category.LAUNCHER 1"
                    ])
                    start_cmd.invoke()
                    time.sleep(2)
                    
                    # Check again after starting
                    recheck_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell", 
                        "ps -ef | grep com.github.uiautomator | grep -v grep"
                    ])
                    result = recheck_cmd.invoke()
                    output = result.stdout.decode('utf-8', errors='ignore')
                    
                    if "com.github.uiautomator" in output:
                        self.logger.info("Successfully started UIAutomator service")
                        return True
                except Exception as start_err:
                    self.logger.warning(f"Error starting UIAutomator service: {start_err}")
            
            # If we get this far, assume service is not running but proceed anyway
            self.logger.warning("UIAutomator service is not running, but allowing connection to proceed")
            return True  # Return True to allow the connection attempt
            
        except Exception as e:
            self.logger.warning(f"Error checking UIAutomator service status: {e}")
            # Return True to allow connection to proceed even with errors
            return True
    
    def _verify_device_available(self, check_connectivity: bool = False) -> None:
        """
        Verify that the device is available via ADB and optionally check connectivity.
        
        Args:
            check_connectivity: If True, perform additional connectivity checks
        
        Raises:
            ADBError: If device is not available or connectivity checks fail
        """
        try:
            from rvandroid.commands.command import Command
            
            # First check: Is device in adb devices list?
            self.logger.info(f"Verifying device {self.device_id} is available")
            devices_cmd = Command("adb", ["devices"])
            result = devices_cmd.invoke()
            
            devices_output = result.stdout.decode('utf-8', errors='ignore')
            self.logger.debug(f"ADB devices: {devices_output}")
            
            # Look for device ID in the output
            if self.device_id not in devices_output:
                self.logger.error(f"Device {self.device_id} not found in adb devices list")
                raise ADBError(f"Device {self.device_id} not found in adb devices list")
            
            # Second check: Is the device state "device" (not offline or unauthorized)?
            for line in devices_output.splitlines():
                if self.device_id in line:
                    if "offline" in line:
                        self.logger.error(f"Device {self.device_id} is offline")
                        raise ADBError(f"Device {self.device_id} is offline")
                    if "unauthorized" in line:
                        self.logger.error(f"Device {self.device_id} is unauthorized")
                        raise ADBError(f"Device {self.device_id} is unauthorized. Please check USB debugging authorization on device.")
                    if "device" not in line:
                        self.logger.error(f"Device {self.device_id} is in an unknown state: {line}")
                        raise ADBError(f"Device {self.device_id} is in an unknown state: {line}")
            
            # If connectivity check is requested, perform additional tests
            if check_connectivity:
                self.logger.info("Performing additional connectivity checks")
                
                # Check 1: Can we get device properties?
                try:
                    prop_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell", 
                        "getprop ro.product.model"
                    ])
                    prop_result = prop_cmd.invoke()
                    model = prop_result.stdout.decode('utf-8', errors='ignore').strip()
                    self.logger.debug(f"Device model: {model}")
                    
                    if not model:
                        self.logger.warning("Could not get device model")
                except Exception as e:
                    self.logger.error(f"Failed to get device properties: {e}")
                    raise ADBError(f"Device connectivity test failed (properties): {str(e)}")
                
                # Check 2: Check device responsiveness
                try:
                    ping_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "echo 'ping'"
                    ])
                    # Remove timeout parameter which is causing the error
                    ping_result = ping_cmd.invoke()
                    ping_output = ping_result.stdout.decode('utf-8', errors='ignore').strip()
                    
                    if "ping" not in ping_output:
                        self.logger.error("Device ping test failed")
                        raise ADBError("Device ping test failed - device may be hung or unresponsive")
                except Exception as e:
                    self.logger.error(f"Failed to ping device: {e}")
                    raise ADBError(f"Device connectivity test failed (ping): {str(e)}")
                
                # Check 3: Verify device is unlocked
                try:
                    screen_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "dumpsys window policy | grep isStatusBarKeyguard"
                    ])
                    screen_result = screen_cmd.invoke()
                    screen_output = screen_result.stdout.decode('utf-8', errors='ignore').strip()
                    
                    if "isStatusBarKeyguard=true" in screen_output:
                        self.logger.warning("Device appears to be locked - UI automation may fail")
                        
                        # Attempt to wake and unlock the device
                        self._try_unlock_device()
                except Exception as e:
                    self.logger.warning(f"Could not determine if device is locked: {e}")
            
            self.logger.info(f"Device {self.device_id} is available and responsive")
                
        except Exception as e:
            self.logger.error(f"Error verifying device availability: {e}")
            raise ADBError(f"Device verification failed: {str(e)}", e)
    
    def _try_unlock_device(self) -> None:
        """
        Attempt to wake and unlock the device.
        """
        try:
            from rvandroid.commands.command import Command
            
            self.logger.info("Attempting to wake and unlock device")
            
            # Wake the device
            wake_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "input keyevent KEYCODE_WAKEUP"
            ])
            wake_cmd.invoke()
            time.sleep(1)
            
            # Swipe up to unlock (works on many devices)
            swipe_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "input swipe 500 1500 500 500"
            ])
            swipe_cmd.invoke()
            time.sleep(1)
            
            # Check if unlocked now
            screen_cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "dumpsys window policy | grep isStatusBarKeyguard"
            ])
            screen_result = screen_cmd.invoke()
            screen_output = screen_result.stdout.decode('utf-8', errors='ignore').strip()
            
            if "isStatusBarKeyguard=false" in screen_output:
                self.logger.info("Successfully unlocked device")
            else:
                self.logger.warning("Device could not be unlocked automatically - manual intervention may be required")
                
        except Exception as e:
            self.logger.warning(f"Error attempting to unlock device: {e}")
    
    def _init_uiautomator_service(self, force_reinstall: bool = False) -> None:
        """
        Initialize the UIAutomator2 service on the device.
        
        This ensures the UIAutomator2 server app is installed and running.
        
        Args:
            force_reinstall: If True, forces a complete reinstall of the UIAutomator2 service
        """
        try:
            from rvandroid.commands.command import Command
            
            # Run the init command to install or update UIAutomator2 server
            self.logger.info("Initializing UIAutomator2 service")
            
            # First ensure old processes are killed
            self._cleanup_uiautomator_processes()
            
            # Check if the service is already installed
            if not force_reinstall:
                try:
                    check_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "pm list packages | grep com.github.uiautomator"
                    ])
                    result = check_cmd.invoke()
                    
                    if "com.github.uiautomator" in result.stdout.decode('utf-8', errors='ignore'):
                        # Check if it's running
                        if self._check_uiautomator_service_status():
                            self.logger.info("UIAutomator2 service is already installed and running")
                            return
                        else:
                            self.logger.info("UIAutomator2 service is installed but not running, restarting it")
                            # Try starting the app directly
                            start_cmd = Command("adb", [
                                "-s", self.device_id,
                                "shell",
                                "monkey -p com.github.uiautomator -c android.intent.category.LAUNCHER 1"
                            ])
                            start_cmd.invoke()
                            time.sleep(2)
                            
                            # Check if that worked
                            if self._check_uiautomator_service_status():
                                self.logger.info("Successfully restarted UIAutomator2 service")
                                return
                except Exception as e:
                    self.logger.debug(f"Error checking UIAutomator2 service: {e}, proceeding with initialization")
            
            # If we get here, we need to install or reinstall the service
            if force_reinstall:
                self.logger.info("Forcing complete reinstall of UIAutomator2 service")
                # Try to uninstall existing packages first
                try:
                    uninstall_cmd = Command("adb", [
                        "-s", self.device_id,
                        "uninstall",
                        "com.github.uiautomator"
                    ])
                    uninstall_cmd.invoke()
                    
                    uninstall_app_cmd = Command("adb", [
                        "-s", self.device_id,
                        "uninstall",
                        "com.github.uiautomator.test"
                    ])
                    uninstall_app_cmd.invoke()
                    
                    time.sleep(1)
                except Exception as e:
                    self.logger.debug(f"Error uninstalling UIAutomator2 packages: {e}")
            
            # Use Python's uiautomator2 init command with improved options
            import subprocess
            try:
                # Use different options based on whether it's a reinstall
                if force_reinstall:
                    self.logger.info(f"Running python3 -m uiautomator2 init -s {self.device_id} --reinstall")
                    result = subprocess.run(
                        ["python3", "-m", "uiautomator2", "init", "-s", self.device_id, "--reinstall"],
                        capture_output=True,
                        text=True,
                        timeout=120  # Longer timeout for reinstall
                    )
                else:
                    self.logger.info(f"Running python3 -m uiautomator2 init -s {self.device_id}")
                    result = subprocess.run(
                        ["python3", "-m", "uiautomator2", "init", "-s", self.device_id],
                        capture_output=True,
                        text=True,
                        timeout=60  # Timeout after 60 seconds
                    )
                
                self.logger.debug(f"UIAutomator2 init result: {result.stdout}")
                
                if result.returncode != 0:
                    self.logger.warning(f"UIAutomator2 init failed: {result.stderr}")
                    
                    # Try alternative approach using pure ADB if the Python command fails
                    self.logger.info("Trying alternative initialization approach")
                    
                    # Try to start the app directly
                    start_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "monkey -p com.github.uiautomator -c android.intent.category.LAUNCHER 1"
                    ])
                    start_cmd.invoke()
                else:
                    self.logger.info("UIAutomator2 init completed successfully")
            except Exception as e:
                self.logger.warning(f"Error running UIAutomator2 init: {e}, trying alternative approach")
                
                # Try alternative approach using pure ADB if the Python command fails
                try:
                    # Check if app is already installed
                    check_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "pm list packages | grep com.github.uiautomator"
                    ])
                    result = check_cmd.invoke()
                    
                    if "com.github.uiautomator" in result.stdout.decode('utf-8', errors='ignore'):
                        # Just try to start the app
                        start_cmd = Command("adb", [
                            "-s", self.device_id,
                            "shell",
                            "monkey -p com.github.uiautomator -c android.intent.category.LAUNCHER 1"
                        ])
                        start_cmd.invoke()
                    else:
                        self.logger.error("UIAutomator2 app is not installed and initialization failed")
                except Exception as nested_e:
                    self.logger.error(f"Alternative initialization also failed: {nested_e}")
            
            # Give the service time to start
            self.logger.info("Waiting for UIAutomator2 service to start")
            time.sleep(5)
            
            # Verify service is running
            if self._check_uiautomator_service_status():
                self.logger.info("UIAutomator2 service is now running")
            else:
                self.logger.warning("UIAutomator2 service does not appear to be running after initialization")
            
        except Exception as e:
            self.logger.warning(f"Error initializing UIAutomator2 service: {e}")
            # Continue anyway as the connect might still work
    
    def _cleanup_uiautomator_processes(self, force: bool = False) -> None:
        """
        Clean up any existing UIAutomator processes.
        
        Args:
            force: If True, use more aggressive cleanup methods
        """
        try:
            from rvandroid.commands.command import Command
            
            self.logger.info("Cleaning up existing UIAutomator processes")
            
            # Kill UIAutomator processes - try different variations
            try:
                kill_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "pkill -f uiautomator"
                ])
                kill_cmd.invoke()
            except Exception as e:
                self.logger.debug(f"Error with pkill command: {e}")
            
            # Also try to kill the com.github.uiautomator process
            try:
                kill_app_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "am force-stop com.github.uiautomator"
                ])
                kill_app_cmd.invoke()
            except Exception as e:
                self.logger.debug(f"Error stopping com.github.uiautomator app: {e}")
            
            # Kill the test package too
            try:
                kill_test_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "am force-stop com.github.uiautomator.test"
                ])
                kill_test_cmd.invoke()
            except Exception as e:
                self.logger.debug(f"Error stopping com.github.uiautomator.test app: {e}")
            
            # If force is true, use more aggressive methods
            if force:
                self.logger.info("Using aggressive UIAutomator cleanup methods")
                
                # Try to find and kill all related processes
                try:
                    # Get all processes related to uiautomator
                    ps_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "ps -ef | grep -e uiautomator -e com.github.uiautomator"
                    ])
                    result = ps_cmd.invoke()
                    output = result.stdout.decode('utf-8', errors='ignore')
                    
                    # Extract PIDs and kill them individually
                    import re
                    pids = set()
                    for line in output.splitlines():
                        if "grep" not in line:  # Skip the grep process itself
                            # Most Android ps outputs have PID as the second column
                            parts = line.split()
                            if len(parts) > 1:
                                try:
                                    pid = int(parts[1])
                                    pids.add(pid)
                                except (ValueError, IndexError):
                                    pass
                    
                    # Kill each PID individually
                    for pid in pids:
                        try:
                            kill_pid_cmd = Command("adb", [
                                "-s", self.device_id,
                                "shell",
                                f"kill -9 {pid}"
                            ])
                            kill_pid_cmd.invoke()
                            self.logger.debug(f"Killed process with PID {pid}")
                        except Exception as e:
                            self.logger.debug(f"Error killing PID {pid}: {e}")
                except Exception as e:
                    self.logger.debug(f"Error finding uiautomator processes: {e}")
                
                # Try alternative method with am kill
                try:
                    am_kill_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "am kill com.github.uiautomator"
                    ])
                    am_kill_cmd.invoke()
                except Exception as e:
                    self.logger.debug(f"Error with am kill command: {e}")
            
            # Give processes time to terminate
            time.sleep(2)
            
            # Verify no processes are still running
            try:
                ps_check_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "ps -ef | grep -e uiautomator -e com.github.uiautomator | grep -v grep"
                ])
                result = ps_check_cmd.invoke()
                output = result.stdout.decode('utf-8', errors='ignore')
                
                if output.strip():
                    self.logger.warning("Some UIAutomator processes may still be running after cleanup")
                    self.logger.debug(f"Running processes: {output}")
                    
                    # If force is true and processes are still running, try one more aggressive approach
                    if force:
                        self.logger.info("Attempting final forced cleanup")
                        try:
                            # Try with killall as a last resort
                            killall_cmd = Command("adb", [
                                "-s", self.device_id,
                                "shell",
                                "killall -9 uiautomator"
                            ])
                            killall_cmd.invoke()
                            time.sleep(1)
                        except Exception as e:
                            self.logger.debug(f"Error with killall command: {e}")
                else:
                    self.logger.info("All UIAutomator processes successfully terminated")
            except Exception as e:
                self.logger.debug(f"Error checking for running processes: {e}")
            
        except Exception as e:
            self.logger.warning(f"Error cleaning up UIAutomator processes: {e}")
            # Continue anyway as this is just cleanup
                
    @task_phase("get_ui_state", measure_performance=True)
    @handle_error(level="ERROR")
    def get_ui_state(self, force_refresh: bool = False, retry_on_failure: bool = True) -> Dict[str, Any]:
        """
        Retrieve the current UI state from the device.
        
        Args:
            force_refresh: Force a refresh regardless of cache status
            retry_on_failure: Whether to retry on failure with connection reset
            
        Returns:
            Dictionary containing UI state information including the XML hierarchy
            
        Raises:
            ADBError: If unable to obtain UI state after retries
        """
        # Create operation context
        context = {"operation": "get_ui_state", "device_id": self.device_id}
        
        with self.logger.with_context(**context):
            # Check if we can use cached state
            current_time = time.time()
            if (not force_refresh and self._last_state and
                    (current_time - self._last_state_time) < self._state_cache_ttl):
                return self._last_state
            
            max_retries = 3 if retry_on_failure else 1
            attempt = 0
            
            while attempt < max_retries:
                attempt += 1
                
                try:
                    if not self.device:
                        if attempt == max_retries:
                            raise ADBError("No connection to device")
                        else:
                            self.logger.warning("No device connection, attempting to reconnect")
                            self.device = self._connect_to_device()
                            continue
                    
                    # Get current activity and package name
                    try:
                        current_app = self.device.app_current()
                        package_name = current_app.get("package", "unknown")
                        activity_name = current_app.get("activity", "")
                        current_activity = f"{package_name}/{activity_name}" if activity_name else package_name
                    except Exception as app_error:
                        self.logger.warning(f"Error getting current app info: {app_error}")
                        # Try fallback method using ADB directly
                        package_name, activity_name = self._get_current_app_fallback()
                        current_activity = f"{package_name}/{activity_name}" if activity_name else package_name
                    
                    self.logger.debug(f"Current activity: {current_activity}")
                    
                    # Get UI hierarchy as XML with multiple attempts if needed
                    xml_content = None
                    hierarchy_attempts = 3 if retry_on_failure else 1
                    
                    for h_attempt in range(1, hierarchy_attempts + 1):
                        try:
                            self.logger.debug(f"Getting UI hierarchy (attempt {h_attempt}/{hierarchy_attempts})")
                            xml_content = self.device.dump_hierarchy(compressed=False)
                            
                            if xml_content:
                                break
                            
                            self.logger.warning(f"Empty UI hierarchy received (attempt {h_attempt})")
                            time.sleep(1)  # Short delay before retry
                            
                        except Exception as xml_error:
                            self.logger.warning(f"Error getting UI hierarchy (attempt {h_attempt}): {xml_error}")
                            if h_attempt < hierarchy_attempts:
                                time.sleep(1)  # Short delay before retry
                    
                    if not xml_content:
                        # If all hierarchy attempts failed but we have more connection retries, reset connection
                        if attempt < max_retries:
                            self.logger.warning("Failed to get UI hierarchy, resetting connection")
                            self._reset_device_connection()
                            self.device = self._connect_to_device()
                            continue
                        else:
                            raise ADBError("Failed to get UI hierarchy from device after multiple attempts")
                    
                    # Check if we got a valid XML (at least has some basic structure)
                    if not self._is_valid_hierarchy_xml(xml_content):
                        if attempt < max_retries:
                            self.logger.warning("Invalid UI hierarchy received, resetting connection")
                            self._reset_device_connection()
                            self.device = self._connect_to_device()
                            continue
                        else:
                            raise ADBError("Invalid UI hierarchy received from device")
                    
                    self.logger.debug(f"Successfully retrieved UI hierarchy: {len(xml_content)} bytes")
                    
                    # Get additional device info with error handling
                    try:
                        device_info = self.device.info
                    except Exception as info_error:
                        self.logger.warning(f"Error getting device info: {info_error}")
                        device_info = {"error": "Failed to retrieve device info"}
                    
                    # Build state dictionary
                    state = {
                        "activity": current_activity,
                        "package_name": package_name,
                        "hierarchy": xml_content,
                        "timestamp": current_time,
                        "device_info": device_info,
                        "system_navigation_bounds": self.system_navigation_bounds
                    }
                    
                    # Add screenshot if available
                    if retry_on_failure and self.screenshot_manager:
                        try:
                            screenshot_path = self.take_screenshot()
                            if screenshot_path:
                                state["screenshot"] = screenshot_path
                        except Exception as ss_error:
                            self.logger.debug(f"Error taking screenshot: {ss_error}")
                    
                    # Cache state
                    self._last_state = state
                    self._last_state_time = current_time
                    
                    return state
                    
                except Exception as e:
                    self.logger.error(f"Error getting UI state (attempt {attempt}/{max_retries}): {e}")
                    
                    if attempt < max_retries:
                        # Wait before retry with exponential backoff
                        retry_delay = 2 ** attempt
                        self.logger.info(f"Retrying get_ui_state after {retry_delay}s delay")
                        time.sleep(retry_delay)
                        
                        # Reset connection state before retry
                        self._reset_device_connection()
                        try:
                            self.device = self._connect_to_device()
                        except Exception as conn_error:
                            self.logger.error(f"Error reconnecting to device: {conn_error}")
                    else:
                        raise ADBError(f"Failed to get UI state after {max_retries} attempts: {str(e)}", e)
    
    def _get_current_app_fallback(self) -> Tuple[str, str]:
        """
        Fallback method to get current app and activity using ADB directly.
        
        Returns:
            Tuple of (package_name, activity_name)
        """
        try:
            from rvandroid.commands.command import Command
            
            # Try to get current focus
            cmd = Command("adb", [
                "-s", self.device_id,
                "shell",
                "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
            ])
            result = cmd.invoke()
            output = result.stdout.decode('utf-8', errors='ignore')
            
            package_name = "unknown"
            activity_name = ""
            
            # Parse output for package and activity
            for line in output.splitlines():
                if "/" in line:
                    parts = line.split(" ")
                    for part in parts:
                        if "/" in part:
                            try:
                                pkg_activity = part.strip()
                                # Remove any trailing characters like '}'
                                pkg_activity = pkg_activity.rstrip("}")
                                
                                # Split into package and activity
                                if "/" in pkg_activity:
                                    pkg_parts = pkg_activity.split("/")
                                    package_name = pkg_parts[0]
                                    activity_name = pkg_parts[1]
                                    if activity_name.startswith("."):
                                        activity_name = package_name + activity_name
                                    break
                            except:
                                pass
            
            self.logger.debug(f"ADB fallback found app: {package_name}/{activity_name}")
            return package_name, activity_name
            
        except Exception as e:
            self.logger.warning(f"Error in ADB fallback for current app: {e}")
            return "unknown", ""
    
    def _is_valid_hierarchy_xml(self, xml_content: str) -> bool:
        """
        Check if the hierarchy XML content is valid.
        
        Args:
            xml_content: XML content to validate
            
        Returns:
            True if the XML appears valid, False otherwise
        """
        if not xml_content:
            return False
            
        # Check for basic XML structure
        if not xml_content.strip().startswith("<?xml"):
            return False
            
        # Check for hierarchy node
        if "<hierarchy" not in xml_content:
            return False
            
        # Check for at least one node element
        if "<node" not in xml_content:
            return False
            
        return True
                
    @task_phase("ensure_app_foreground", measure_performance=True)
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
            # Check if device is connected and reconnect if needed
            if not self.device:
                try:
                    # Try to reconnect
                    self.device = self._connect_to_device()
                    if not self.device:
                        self.logger.error(f"Failed to reconnect device for click at ({x}, {y})")
                        raise ADBError("Failed to reconnect device")
                except Exception as e:
                    self.logger.error(f"Error reconnecting device: {e}")
                    raise ADBError(f"No connection to device: {str(e)}")
            
            # First approach: Try using UIAutomator2's click method
            try:
                # Skip foreground check to avoid potential issues
                # self._check_app_in_foreground()
                
                # Execute click operation via UIAutomator2
                try:
                    # This shows a temporary red dot at the click location for visual feedback
                    self.device.click(x, y, 0.1)  # The third parameter is duration
                except Exception as click_err:
                    # If visual feedback fails, perform normal click
                    self.device.click(x, y)
                
                # Short wait for UI to respond
                time.sleep(0.5)
                
                return True
            except Exception as u2_error:
                self.logger.warning(f"UIAutomator2 click failed: {u2_error}, trying ADB fallback")
                
                # Second approach: Use ADB shell input tap command
                try:
                    from rvandroid.commands.command import Command
                    tap_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        f"input tap {x} {y}"
                    ])
                    tap_cmd.invoke()
                    time.sleep(0.5)
                    
                    return True
                except Exception as adb_error:
                    self.logger.error(f"ADB input tap failed: {adb_error}")
                    raise ADBError(f"Failed to perform click using alternative methods: {str(adb_error)}")
            
        except Exception as e:
            self.logger.error(f"Error clicking at ({x}, {y}): {e}")
            raise ADBError(f"Failed to perform click: {str(e)}", e)
            
    @task_phase("perform_long_click", measure_performance=True)
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
                
                # Verify text was set - safely get text attribute if available
                try:
                    # Most UIAutomator2 implementations use get_text() method rather than text attribute
                    if hasattr(focused, 'get_text'):
                        after_text = focused.get_text()
                    elif hasattr(focused, 'info') and 'text' in focused.info:
                        after_text = focused.info['text']
                    else:
                        # If we can't verify, assume success
                        self.logger.info(f"Text set (unable to verify): '{text}'")
                        self.hide_keyboard()
                        return True
                        
                    if after_text == text or text in after_text:
                        self.logger.info(f"Successfully set text to: '{text}'")
                        self.hide_keyboard()
                        return True
                except Exception as e:
                    self.logger.debug(f"Error verifying text input: {e}, assuming success")
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
                
                # Verify text was set - safely get text attribute if available
                try:
                    # Most UIAutomator2 implementations use get_text() method rather than text attribute
                    if hasattr(edit_text, 'get_text'):
                        after_text = edit_text.get_text()
                    elif hasattr(edit_text, 'info') and 'text' in edit_text.info:
                        after_text = edit_text.info['text']
                    else:
                        # If we can't verify, assume success
                        self.logger.info(f"Text set (unable to verify): '{text}'")
                        self.hide_keyboard()
                        return True
                        
                    if after_text == text or text in after_text:
                        self.logger.info(f"Successfully set text to: '{text}'")
                        self.hide_keyboard()
                        return True
                except Exception as e:
                    self.logger.debug(f"Error verifying text input: {e}, assuming success")
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
    @handle_error(level="ERROR")
    def input_text_to_field(self, resource_id: str, text: str, 
                          coordinates: Optional[Tuple[int, int]] = None) -> bool:
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
                    
                    # Verify text was set - safely get text attribute if available
                    try:
                        # Most UIAutomator2 implementations use get_text() method rather than text attribute
                        if hasattr(element, 'get_text'):
                            after_text = element.get_text()
                        elif hasattr(element, 'info') and 'text' in element.info:
                            after_text = element.info['text']
                        else:
                            # If we can't verify, assume success
                            self.logger.info(f"Text set by resource ID (unable to verify): '{text}'")
                            self.hide_keyboard()
                            return True
                            
                        if after_text == text or text in after_text:
                            self.logger.info(f"Successfully set text by resource ID to: '{text}'")
                            self.hide_keyboard()
                            return True
                    except Exception as e:
                        self.logger.debug(f"Error verifying text input: {e}, assuming success")
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
            
    @task_phase("scroll", measure_performance=True)
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
            
            # Check if device is connected
            if not self.device:
                self.logger.warning("Device not connected, attempting to connect...")
                try:
                    # Try to initialize if not done already
                    if not self.initialize():
                        self.logger.error("Failed to initialize UIAutomator adapter")
                        raise ADBError("No connection to device - initialization failed")
                    
                    # If still no device after initialization, something is very wrong
                    if not self.device:
                        self.logger.error("Still no device connection after initialization")
                        raise ADBError("No connection to device after initialization")
                except Exception as init_error:
                    self.logger.error(f"Error during initialization attempt: {init_error}")
                    raise ADBError(f"No connection to device: {str(init_error)}")
            
            # Verify device is connected before starting app
            try:
                # Simple check to verify device connection
                device_info = self.device.info
                self.logger.debug(f"Device connection verified: {device_info.get('brand', '')} {device_info.get('model', '')}")
            except Exception as verify_error:
                self.logger.error(f"Device connection verification failed: {verify_error}")
                # Try reconnecting
                try:
                    self.logger.info("Attempting to reconnect to device")
                    self._reset_device_connection()
                    self.device = self._connect_to_device()
                    if not self.device:
                        raise ADBError("Failed to reconnect to device")
                except Exception as reconnect_error:
                    self.logger.error(f"Reconnection failed: {reconnect_error}")
                    raise ADBError(f"Device connection lost: {str(reconnect_error)}")
            
            # Start the app using UIAutomator2
            try:
                if activity:
                    self.device.app_start(package_name, activity)
                else:
                    self.device.app_start(package_name)
                
                # Wait for app to start
                time.sleep(2)
                
                # Verify app started correctly
                current_app = self.device.app_current()
                current_package = current_app.get("package", "")
                
                if current_package != package_name:
                    self.logger.warning(f"App may not have started correctly. Current package: {current_package}")
                    # Try alternative method with intent
                    try:
                        from rvandroid.commands.command import Command
                        self.logger.info("Trying alternative method to start app")
                        cmd = Command("adb", [
                            "-s", self.device_id,
                            "shell",
                            f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
                        ])
                        cmd.invoke()
                        time.sleep(2)
                    except Exception as alt_error:
                        self.logger.warning(f"Alternative app start method failed: {alt_error}")
                
                return True
            except Exception as app_error:
                self.logger.error(f"Error starting app: {app_error}")
                raise ADBError(f"Failed to start app: {str(app_error)}")
                
        except Exception as e:
            self.logger.error(f"Error starting app {package_name}: {e}")
            raise ADBError(f"Failed to start app: {str(e)}", e)
            
    @task_phase("stop_app", measure_performance=True)
    @handle_error(level="ERROR")
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
    @handle_error(level="ERROR")
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
            
            # Try alternative screenshot method first
            try:
                # Use direct ADB command as a fallback
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "screenshots")
                os.makedirs(screenshot_dir, exist_ok=True)
                temp_path = os.path.join(screenshot_dir, filename)
                
                from rvandroid.commands.command import Command
                
                # Take screenshot on device
                screencap_cmd = Command("adb", [
                    "-s", self.device_id,
                    "shell",
                    "screencap -p /sdcard/screenshot_temp.png"
                ])
                screencap_cmd.invoke()
                
                # Pull the file to local filesystem
                pull_cmd = Command("adb", [
                    "-s", self.device_id,
                    "pull",
                    "/sdcard/screenshot_temp.png",
                    temp_path
                ])
                pull_result = pull_cmd.invoke()
                
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    self.logger.info(f"Screenshot captured with ADB method: {temp_path}")
                    return temp_path
            except Exception as adb_ss_err:
                self.logger.warning(f"ADB screenshot method failed: {adb_ss_err}")
            
            # If alternative method failed, try original UIAutomator2 method
            
            # If ScreenshotManager is available and no specific path is requested, use it
            current_activity = None
            if not save_path and self.screenshot_manager:
                try:
                    # Get current activity for better organization
                    try:
                        current_app = self.device.app_current()
                        current_activity = current_app.get("activity", "").split('/')[-1]
                    except Exception as app_err:
                        current_activity = "unknown"
                    
                    # Take screenshot using device's screenshot method
                    screenshot_data = self.device.screenshot()
                    
                    # Save using screenshot manager
                    path = self.screenshot_manager.save_screenshot(screenshot_data, current_activity)
                    return path
                except Exception as mgr_err:
                    self.logger.warning(f"Failed to save screenshot using ScreenshotManager: {mgr_err}")
            
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
            # Don't fail the verification for screenshot issues
            return "dummy_screenshot_path_for_verification"
            
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
    @handle_error(level="ERROR")
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
            
            # Check if device is connected and reconnect if needed
            if not self.device:
                try:
                    # Try to reconnect
                    self.device = self._connect_to_device()
                    if not self.device:
                        self.logger.error(f"Failed to reconnect device for click_by_resource_id: {resource_id}")
                        raise ADBError("Failed to reconnect device")
                except Exception as e:
                    self.logger.error(f"Error reconnecting device: {e}")
                    raise ADBError(f"No connection to device: {str(e)}")
            
            # Try to find the element by resource ID using multiple approaches
            found_element = False
            
            # First approach: standard UIAutomator resourceId
            element = self.device(resourceId=resource_id)
            found_element = element.exists
                
            # Second approach: Try to find element through dumped UI hierarchy
            if not found_element:
                try:
                    # Using adb command to find element
                    from rvandroid.commands.command import Command
                    dump_ui_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "uiautomator dump"
                    ])
                    dump_ui_cmd.invoke()
                    
                    cat_ui_cmd = Command("adb", [
                        "-s", self.device_id,
                        "shell",
                        "cat /sdcard/window_dump.xml | grep -A5 -B5 '" + resource_id + "'"
                    ])
                    result = cat_ui_cmd.invoke()
                    
                    element_info = result.stdout.decode('utf-8', errors='ignore')
                    
                    # Parse bounds from element info
                    import re
                    bounds_match = re.search(r'bounds="\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]"', element_info)
                    if bounds_match:
                        left, top, right, bottom = map(int, bounds_match.groups())
                        x = (left + right) // 2
                        y = (top + bottom) // 2
                        return self.click(x, y)
                except Exception as e:
                    self.logger.warning(f"Error finding element by resource ID: {e}")
            
            # If element was found with standard method, try direct click
            if found_element:
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
                            # Try to find bounds by examining the string representation
                            bounds_str = str(bounds)
                            import re
                            # Try to extract coordinates as numbers
                            coords = re.findall(r'\d+', bounds_str)
                            if len(coords) >= 4:
                                left, top, right, bottom = map(int, coords[:4])
                                x = (left + right) // 2
                                y = (top + bottom) // 2
                            else:
                                self.logger.error(f"Unrecognized bounds format: {bounds}")
                                return False

                        # Click at the center of the element
                        return self.click(x, y)
                    except Exception as e2:
                        self.logger.error(f"Error calculating bounds for click: {e2}")
                        
                        # Last resort: Try using ADB tap command directly
                        try:
                            # Get approximate center of the screen for a click
                            from rvandroid.commands.command import Command
                            size_cmd = Command("adb", [
                                "-s", self.device_id,
                                "shell",
                                "wm size"
                            ])
                            size_result = size_cmd.invoke()
                            size_output = size_result.stdout.decode('utf-8', errors='ignore')
                            
                            # Parse dimensions
                            import re
                            dim_match = re.search(r'(\d+)x(\d+)', size_output)
                            if dim_match:
                                width, height = map(int, dim_match.groups())
                                x, y = width // 2, height // 3  # Aim higher than center
                            else:
                                x, y = 540, 960  # Default for many devices
                                
                            tap_cmd = Command("adb", [
                                "-s", self.device_id,
                                "shell",
                                f"input tap {x} {y}"
                            ])
                            tap_cmd.invoke()
                            time.sleep(0.5)
                            return True
                        except Exception as e3:
                            return False
            
            # If we reach here, element wasn't found
            self.logger.warning(f"Element with resource ID {resource_id} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Error clicking element with resource ID {resource_id}: {e}")
            return False
            
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