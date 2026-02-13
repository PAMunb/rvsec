# modules/rvdroid-tool/src/rvdroid_tool/ui/uiautomator.py
"""
UIAutomator2 adapter for RVDroid tool using shared rv-uiautomator components.

This module provides a wrapper that adapts the shared UIAutomator components
for use within the RVDroid tool architecture.
"""

from typing import Dict, Any, Optional, Tuple

from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rvdroid_tool.core.component import Component
from rvdroid_tool.ui.adapter import UIAdapter
from rv_android_core.util.error.decorators import handle_error
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

# Import shared UIAutomator components
from rv_uiautomator import UIAutomator2Adapter as SharedUIAutomator2Adapter
from rv_uiautomator import UIAutomatorActionExecutor
from rv_uiautomator.utils import DeviceManager, ScreenshotManager


class UIAutomator2Adapter(UIAdapter):
    """
    RVDroid-specific wrapper for shared UIAutomator components.
    
    ### Architectural Decisions:
    - Uses shared rv-uiautomator components for device interaction
    - Adapts shared components to RVDroid's Component interface
    - Maintains compatibility with existing RVDroid architecture
    - Provides seamless integration without breaking changes
    
    ### Role in the System:
    - Bridge between RVDroid and shared UIAutomator functionality
    - Preserves RVDroid's Component lifecycle and error handling
    - Enables code reuse while maintaining tool-specific behavior
    - Provides unified device interaction across RV-Android tools
    """
    
    def __init__(self, name: str, device_id: str = "emulator-5554"):
        """
        Initialize the UIAutomator2 adapter with shared components.
        
        Args:
            name: Component name for RVDroid integration
            device_id: Device ID to connect to
        """
        super().__init__(name)
        
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.uiautomator.adapter",
            {CONTEXT_COMPONENT: "UIAutomator2Adapter"}
        )
        
        self.device_id = device_id
        self.logger.info(f"Initializing shared UIAutomator adapter for device: {device_id}")
        
        # Initialize shared components
        self.shared_adapter = SharedUIAutomator2Adapter(device_id)
        self.action_executor = UIAutomatorActionExecutor()
        self.device_manager = DeviceManager()
        self.screenshot_manager = ScreenshotManager()
        
        # Initialize parser (RVDroid-specific)
        self.parser = UIAutomator2Parser(DefaultTextVisitor)
        
        # Connection state
        self.is_connected = False
    
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """Initialize the component using shared adapter."""
        try:
            self.logger.info(f"Initializing shared UIAutomator2Adapter for device: {self.device_id}")
            
            # Validate device availability using shared device manager
            if not self.device_manager.validate_device(self.device_id):
                self.logger.error(f"Device {self.device_id} is not available")
                return False
            
            # Connect using shared adapter
            if not self.shared_adapter.connect(self.device_id):
                self.logger.error("Failed to connect to device via shared adapter")
                return False
            
            self.is_connected = True
            self.logger.info("UIAutomator2Adapter initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing UIAutomator2Adapter: {e}")
            return False
    
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """Start the component."""
        self.logger.info("Starting UIAutomator2Adapter")
        return True
    
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """Stop the component."""
        self.logger.info("Stopping UIAutomator2Adapter")
        return True
    
    @handle_error(level="ERROR")
    def cleanup(self) -> bool:
        """Clean up resources."""
        try:
            self.logger.info("Cleaning up UIAutomator adapter resources")
            self.is_connected = False
            return True
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
            return False
    
    @handle_error(level="ERROR")
    def get_ui_state(self, force_refresh: bool = False, retry_on_failure: bool = True) -> Dict[str, Any]:
        """
        Retrieve UI state using shared adapter.
        
        Args:
            force_refresh: Force refresh regardless of cache
            retry_on_failure: Whether to retry on failure
            
        Returns:
            Dictionary containing UI state information
        """
        try:
            if not self.is_connected:
                raise Exception("Adapter not connected - call initialize() first")
            
            # Get state from shared adapter
            state = self.shared_adapter.get_ui_state(force_refresh)
            
            # Adapt format for RVDroid compatibility
            # Shared adapter returns UIAutomator format, convert to RVDroid expected format
            adapted_state = {
                "activity": state.get("current_activity", "unknown"),
                "package_name": state.get("current_package", "unknown"), 
                "hierarchy": state.get("xml", ""),
                "timestamp": state.get("timestamp", 0),
                "device_info": state.get("device_info", {}),
                "system_navigation_bounds": state.get("system_navigation_bounds", {})
            }
            
            # Add screenshot if available
            if "screenshot_path" in state:
                adapted_state["screenshot"] = state["screenshot_path"]
            
            return adapted_state
            
        except Exception as e:
            self.logger.error(f"Error getting UI state: {e}")
            raise
    
    @handle_error(level="ERROR")
    def parse_screen(self, state: Dict[str, Any], 
                     static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse the UI state into a structured screen description.
        
        Args:
            state: UI state dictionary
            static_data: Optional static analysis data
            
        Returns:
            ScreenDescription object
        """
        xml_data = state.get("hierarchy", "")
        if not xml_data:
            raise ValueError("No hierarchy XML found in state data")
        
        activity = state.get("activity", "")
        return self.parser.parse(xml_data, static_data, activity, state)
    
    @handle_error(level="ERROR")
    def click(self, x: int, y: int) -> bool:
        """Perform click using shared adapter."""
        try:
            return self.shared_adapter.click(x, y)
        except Exception as e:
            self.logger.error(f"Click failed at ({x}, {y}): {e}")
            return False
    
    @handle_error(level="ERROR")
    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """Perform long click using shared adapter."""
        try:
            return self.shared_adapter.long_click(x, y, duration)
        except Exception as e:
            self.logger.error(f"Long click failed at ({x}, {y}): {e}")
            return False
    
    @handle_error(level="ERROR")
    def input_text(self, text: str) -> bool:
        """Input text using shared adapter."""
        try:
            return self.shared_adapter.input_text(text)
        except Exception as e:
            self.logger.error(f"Text input failed: {e}")
            return False
    
    @handle_error(level="ERROR")
    def scroll(self, x: int, y: int, direction: str, distance: int = 400) -> bool:
        """Perform scroll using shared adapter."""
        try:
            return self.shared_adapter.swipe(
                x, y,
                x + (distance if direction == "RIGHT" else (-distance if direction == "LEFT" else 0)),
                y + (distance if direction == "DOWN" else (-distance if direction == "UP" else 0)),
                0.5
            )
        except Exception as e:
            self.logger.error(f"Scroll failed: {e}")
            return False
    
    @handle_error(level="ERROR")
    def press_key(self, key_code: str) -> bool:
        """Press key using shared adapter."""
        try:
            if key_code.lower() == "back":
                return self.shared_adapter.press_back()
            elif key_code.lower() == "home":
                return self.shared_adapter.press_home()
            else:
                self.logger.warning(f"Unsupported key code: {key_code}")
                return False
        except Exception as e:
            self.logger.error(f"Key press failed: {e}")
            return False
    
    @handle_error(level="ERROR")
    def start_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        """Start app using shared adapter."""
        try:
            return self.shared_adapter.launch_app(package_name)
        except Exception as e:
            self.logger.error(f"App start failed: {e}")
            return False
    
    @handle_error(level="ERROR")
    def stop_app(self, package_name: str) -> bool:
        """Stop app using shared adapter."""
        try:
            return self.shared_adapter.stop_app(package_name)
        except Exception as e:
            self.logger.error(f"App stop failed: {e}")
            return False
    
    @handle_error(level="ERROR")
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[str]:
        """Take screenshot using shared adapter."""
        try:
            return self.shared_adapter.take_screenshot()
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None
    
    @handle_error(level="ERROR")
    def ensure_app_in_foreground(self, package_name: str, max_attempts: int = 3) -> bool:
        """Ensure app is in foreground."""
        try:
            for attempt in range(max_attempts):
                # Get current state to check package
                state = self.get_ui_state()
                current_package = state.get("package_name")
                
                if current_package == package_name:
                    return True
                
                # Try to bring app to foreground
                if not self.start_app(package_name):
                    self.logger.warning(f"Failed to start app {package_name} (attempt {attempt + 1})")
                    continue
                
                # Wait and check again
                import time
                time.sleep(2)
            
            return False
        except Exception as e:
            self.logger.error(f"Error ensuring app in foreground: {e}")
            return False