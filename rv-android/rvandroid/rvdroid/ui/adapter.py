# rvandroid/rvdroid/ui/adapter.py
"""
UI Adapter interface for RVDroid.

This module defines the interface for UI adapters that interact with Android devices.
It enforces a common API for different implementations (UIAutomator2, ADB, etc.)
to ensure interchangeability and consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription
from rvandroid.rvdroid.core.component import Component


class UIAdapter(Component, ABC):
    """
    Base interface for UI adapters that interact with Android devices.
    
    ### Architectural Decisions:
    - Enforces a common interface for all UI adapters
    - Defines standardized methods for UI operations
    - Extends Component for lifecycle integration
    - Handles error management consistently
    - Provides methods for both low-level and high-level UI interactions
    - Includes state management and introspection capabilities
    
    ### Role in the System:
    - Provides the primary interface between RVDroid and Android devices
    - Abstracts away implementation details from testing strategies
    - Enables consistent behavior across different UI automation technologies
    - Supports recording and playback of UI interactions
    """
    
    @abstractmethod
    def get_ui_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Retrieve the current UI state from the device.
        
        Args:
            force_refresh: Force a refresh regardless of cache status
            
        Returns:
            Dictionary containing UI state information including the XML hierarchy
        """
        pass
        
    @abstractmethod
    def parse_screen(self, state: Dict[str, Any], 
                     static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse the UI state into a structured screen description.
        
        Args:
            state: UI state dictionary from get_ui_state()
            static_data: Optional static analysis data
            
        Returns:
            ScreenDescription object
        """
        pass
        
    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        """
        Perform a click operation at the specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """
        Perform a long click operation at the specified coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Duration of the long press in seconds
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def input_text(self, text: str) -> bool:
        """
        Input text at the currently focused element.
        
        Args:
            text: Text to input
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
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
        pass
        
    @abstractmethod
    def press_key(self, key_code: str) -> bool:
        """
        Press a key on the device.
        
        Args:
            key_code: Key code to press (e.g., BACK, HOME, MENU)
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def start_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        """
        Start an application on the device.
        
        Args:
            package_name: Application package name
            activity: Optional activity to start
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def stop_app(self, package_name: str) -> bool:
        """
        Stop an application on the device.
        
        Args:
            package_name: Application package name
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def take_screenshot(self, save_path: Optional[str] = None) -> Optional[str]:
        """
        Capture screenshot from the device.
        
        Args:
            save_path: Optional path to save the screenshot to
            
        Returns:
            Path to saved screenshot or None if failed
        """
        pass
        
    @abstractmethod
    def click_by_resource_id(self, resource_id: str) -> bool:
        """
        Click on an element identified by resource ID.
        
        Args:
            resource_id: Resource ID of the element to click
            
        Returns:
            True if successful, False otherwise
        """
        pass
        
    @abstractmethod
    def ensure_app_in_foreground(self, package_name: str, max_attempts: int = 3) -> bool:
        """
        Ensure the target app is in the foreground.
        
        Args:
            package_name: Package name of the app being tested
            max_attempts: Maximum attempts to get app in foreground
            
        Returns:
            True if app is in foreground, False if recovery failed
        """
        pass
        
    def is_supported_operation(self, operation_type: str) -> bool:
        """
        Check if a specific operation type is supported by this adapter.
        
        Args:
            operation_type: The operation type to check
            
        Returns:
            True if the operation is supported, False otherwise
        """
        # Default implementation - most adapters should support all operations
        return True