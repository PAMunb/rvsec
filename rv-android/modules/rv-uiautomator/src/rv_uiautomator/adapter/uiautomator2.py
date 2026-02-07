"""
UIAutomator2 adapter implementation for Android device interaction.

This module provides the concrete implementation of the UIAdapter interface
using the UIAutomator2 framework for device interaction.
"""

import time
import uiautomator2 as u2
from typing import Dict, Any, Optional
from pathlib import Path

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from .base import UIAdapter
from ..constants import (
    DEFAULT_CONNECTION_TIMEOUT,
    ACTION_EXECUTION_DELAY,
    SCREENSHOT_QUALITY,
    DEFAULT_SCREENSHOT_PATH,
    DEFAULT_SWIPE_DURATION,
    WAIT_FOR_IDLE_TIMEOUT,
    WAIT_FOR_SELECTOR_TIMEOUT,
)


class UIAutomator2Adapter(UIAdapter):
    """
    UIAutomator2 implementation of the UIAdapter interface.
    
    ### Architectural Decisions:
    - Uses UIAutomator2 library for direct device communication
    - Implements all UIAdapter methods with proper error handling
    - Provides screenshot capture and UI hierarchy retrieval
    - Uses PerformanceMonitor for operation timing
    - Handles connection management and device lifecycle
    
    ### Role in the System:
    - Primary device interaction layer for RVSmart tool
    - Abstracts UIAutomator2 specifics from higher-level components
    - Provides consistent device interaction across testing scenarios
    - Handles both coordinate-based and element-based actions
    """
    
    def __init__(self, device_id: str = "emulator-5554"):
        """
        Initialize UIAutomator2 adapter.
        
        Args:
            device_id: Device identifier for connection
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_uiautomator.adapter.uiautomator2",
            {CONTEXT_COMPONENT: "UIAutomator2Adapter"}
        )
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        self.device_id = device_id
        self.device = None
        self.connected = False
        
        self.logger.debug(f"UIAutomator2Adapter initialized for device: {device_id}")
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="connection"
    )
    def connect(self, device_id: str) -> bool:
        """
        Establish connection to Android device via UIAutomator2.

        Configures UIAutomator2 settings for optimal performance,
        especially in headless mode where UI idle detection can be slow.

        Args:
            device_id: Device identifier to connect to

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.performance_monitor.measure_time("device_connection"):
                self.device_id = device_id
                self.device = u2.connect(device_id)

                # Test connection with basic info call
                info = self.device.info
                if info:
                    self.connected = True

                    # Configure UIAutomator2 settings for performance optimization
                    # These settings reduce UI idle waiting time (critical for headless mode)
                    self._configure_uiautomator_settings()

                    self.logger.info(f"Connected to device {device_id}: {info.get('productName', 'Unknown')}")
                    return True
                else:
                    self.connected = False
                    self.logger.error(f"Failed to get device info for {device_id}")
                    return False

        except Exception as e:
            self.connected = False
            self.logger.error(f"Connection failed for device {device_id}: {e}")
            return False

    def _configure_uiautomator_settings(self) -> None:
        """
        Configure UIAutomator2 settings for optimal performance.

        Reduces wait timeouts to prevent long delays in headless mode
        where UI rendering is slower (SwiftShader software rendering).
        """
        if not self.device:
            return

        try:
            # Configure wait timeouts
            # wait_timeout: Max time to wait for UI to become idle
            # wait_for_selector_timeout: Max time to wait for element selector
            self.device.settings['wait_timeout'] = WAIT_FOR_IDLE_TIMEOUT

            self.logger.debug(
                f"UIAutomator2 settings configured: "
                f"wait_timeout={WAIT_FOR_IDLE_TIMEOUT}s"
            )
        except Exception as e:
            self.logger.warning(f"Failed to configure UIAutomator2 settings: {e}")
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter", 
        phase="state_capture",
        default_return={}
    )
    def get_ui_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Capture current UI state from device.
        
        Args:
            force_refresh: Whether to force refresh the UI state
            
        Returns:
            Dictionary containing UI state information
        """
        if not self.connected or not self.device:
            self.logger.warning("⚠️ DEBUG_STATE: Device not connected, cannot capture UI state")
            self.logger.warning(f"   Connected: {self.connected}, Device: {self.device is not None}")
            return {}
            
        try:
            with self.performance_monitor.measure_time("ui_state_capture"):
                # Get device info
                device_info = self.device.info
                
                # Get current app info
                app_current = self.device.app_current()
                
                # Get UI hierarchy
                xml_hierarchy = self.device.dump_hierarchy()
                
                self.logger.warning(f"🔍 DEBUG_STATE: UI state captured")
                self.logger.warning(f"   Package: {app_current.get('package', 'unknown')}")
                self.logger.warning(f"   Activity: {app_current.get('activity', 'unknown')}")
                self.logger.warning(f"   XML length: {len(xml_hierarchy) if xml_hierarchy else 0}")
                
                ui_state = {
                    "device_info": device_info,
                    "current_package": app_current.get("package", "unknown"),
                    "current_activity": app_current.get("activity", "unknown"),
                    "xml": xml_hierarchy,
                    "timestamp": time.time()
                }
                
                self.logger.debug(f"Captured UI state for {app_current.get('package', 'unknown')}")
                return ui_state
                
        except Exception as e:
            self.logger.error(f"Failed to capture UI state: {e}")
            return {}
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="click_action"
    )
    def click(self, x: int, y: int) -> bool:
        """
        Perform click at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if click executed successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot perform click")
            return False
            
        try:
            with self.performance_monitor.measure_time("click_action"):
                self.device.click(x, y)
                time.sleep(ACTION_EXECUTION_DELAY)
                self.logger.debug(f"Clicked at coordinates ({x}, {y})")
                return True
                
        except Exception as e:
            self.logger.error(f"Click failed at ({x}, {y}): {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="text_input"
    )
    def input_text(self, text: str) -> bool:
        """
        Input text at currently focused element.
        
        Args:
            text: Text to input
            
        Returns:
            True if text input successful
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot input text")
            return False
            
        try:
            with self.performance_monitor.measure_time("text_input"):
                # Clear existing text first
                self.device.send_keys("", clear=True)
                # Input new text
                self.device.send_keys(text)
                time.sleep(ACTION_EXECUTION_DELAY)
                self.logger.debug(f"Input text: {text}")
                return True
                
        except Exception as e:
            self.logger.error(f"Text input failed for '{text}': {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="long_click_action"
    )
    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """
        Perform long click at specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Long click duration in seconds
            
        Returns:
            True if long click executed successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot perform long click")
            return False
            
        try:
            with self.performance_monitor.measure_time("long_click_action"):
                self.device.long_click(x, y, duration)
                time.sleep(ACTION_EXECUTION_DELAY)
                self.logger.debug(f"Long clicked at ({x}, {y}) for {duration}s")
                return True
                
        except Exception as e:
            self.logger.error(f"Long click failed at ({x}, {y}): {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="swipe_action"
    )
    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = DEFAULT_SWIPE_DURATION
    ) -> bool:
        """
        Perform swipe gesture between two points.

        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            duration: Swipe duration in seconds (default: 0.25s for performance)

        Returns:
            True if swipe executed successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot perform swipe")
            return False

        try:
            with self.performance_monitor.measure_time("swipe_action"):
                self.device.swipe(x1, y1, x2, y2, duration)
                time.sleep(ACTION_EXECUTION_DELAY)
                self.logger.debug(f"Swiped from ({x1}, {y1}) to ({x2}, {y2}) in {duration}s")
                return True

        except Exception as e:
            self.logger.error(f"Swipe failed from ({x1}, {y1}) to ({x2}, {y2}): {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="back_press"
    )
    def press_back(self) -> bool:
        """
        Press device back button.
        
        Returns:
            True if back press executed successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot press back")
            return False
            
        try:
            with self.performance_monitor.measure_time("back_press"):
                self.device.press("back")
                time.sleep(ACTION_EXECUTION_DELAY)
                self.logger.debug("Pressed back button")
                return True
                
        except Exception as e:
            self.logger.error(f"Back press failed: {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="home_press"
    )
    def press_home(self) -> bool:
        """
        Press device home button.
        
        Returns:
            True if home press executed successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot press home")
            return False
            
        try:
            with self.performance_monitor.measure_time("home_press"):
                self.device.press("home")
                time.sleep(ACTION_EXECUTION_DELAY)
                self.logger.debug("Pressed home button")
                return True
                
        except Exception as e:
            self.logger.error(f"Home press failed: {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="screenshot_capture"
    )
    def take_screenshot(self) -> Optional[str]:
        """
        Capture and save device screenshot.
        
        Returns:
            Path to saved screenshot file, or None if failed
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot take screenshot")
            return None
            
        try:
            with self.performance_monitor.measure_time("screenshot_capture"):
                # Generate unique filename
                timestamp = int(time.time())
                screenshot_path = f"./screenshot_{timestamp}.png"
                
                # Capture screenshot
                self.device.screenshot(screenshot_path)
                
                # Verify file exists
                if Path(screenshot_path).exists():
                    self.logger.debug(f"Screenshot saved: {screenshot_path}")
                    return screenshot_path
                else:
                    self.logger.error("Screenshot file not created")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Screenshot capture failed: {e}")
            return None
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="app_launch"
    )
    def launch_app(self, package_name: str) -> bool:
        """
        Launch application by package name.
        
        Args:
            package_name: Application package name to launch
            
        Returns:
            True if app launched successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot launch app")
            return False
            
        try:
            with self.performance_monitor.measure_time("app_launch"):
                self.device.app_start(package_name)
                time.sleep(2.0)  # Wait for app to start
                
                # Verify app launched
                current_app = self.device.app_current()
                if current_app.get("package") == package_name:
                    self.logger.info(f"Successfully launched app: {package_name}")
                    return True
                else:
                    self.logger.warning(f"App launch verification failed for {package_name}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"App launch failed for {package_name}: {e}")
            return False
    
    @ErrorHandler.handle_errors(
        component="UIAutomator2Adapter",
        phase="app_stop"
    )
    def stop_app(self, package_name: str) -> bool:
        """
        Stop/kill application by package name.
        
        Args:
            package_name: Application package name to stop
            
        Returns:
            True if app stopped successfully
        """
        if not self.connected or not self.device:
            self.logger.warning("Device not connected, cannot stop app")
            return False
            
        try:
            with self.performance_monitor.measure_time("app_stop"):
                self.device.app_stop(package_name)
                time.sleep(1.0)  # Wait for app to stop
                self.logger.debug(f"Stopped app: {package_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"App stop failed for {package_name}: {e}")
            return False