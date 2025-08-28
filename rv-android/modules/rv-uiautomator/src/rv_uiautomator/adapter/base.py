"""
UI Adapter interface for Android device interaction.

This module defines the standard interface for UI adapters that interact with Android
devices through various automation frameworks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List


class UIAdapter(ABC):
    """
    Base interface for UI adapters that interact with Android devices.
    
    ### Architectural Decisions:
    - Defines standardized methods for UI operations across different frameworks
    - Provides consistent interface for action execution engines
    - Handles both low-level device operations and high-level state management
    - Supports screenshot capture and UI hierarchy retrieval
    
    ### Role in the System:
    - Primary interface between testing tools and Android devices
    - Abstracts implementation details from higher-level components
    - Enables framework-agnostic testing strategies
    - Provides unified API for both rvsmart and rvdroid tools
    """
    
    @abstractmethod
    def connect(self, device_id: str) -> bool:
        """Establish connection to Android device."""
        pass
        
    @abstractmethod
    def get_ui_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Retrieve current UI state from device."""
        pass
        
    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        """Perform click at specified coordinates."""
        pass
        
    @abstractmethod
    def input_text(self, text: str) -> bool:
        """Input text at currently focused element."""
        pass
        
    @abstractmethod
    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """Perform long click at specified coordinates."""
        pass
        
    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> bool:
        """Perform swipe gesture between two points."""
        pass
        
    @abstractmethod
    def press_back(self) -> bool:
        """Press device back button."""
        pass
        
    @abstractmethod
    def press_home(self) -> bool:
        """Press device home button."""
        pass
        
    @abstractmethod
    def take_screenshot(self) -> Optional[str]:
        """Capture and save device screenshot."""
        pass
        
    @abstractmethod
    def launch_app(self, package_name: str) -> bool:
        """Launch application by package name."""
        pass
        
    @abstractmethod
    def stop_app(self, package_name: str) -> bool:
        """Stop/kill application by package name."""
        pass