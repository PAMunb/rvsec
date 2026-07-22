"""
UI Adapter interface for Android device interaction.

Defines the abstract interface that all UI automation adapters must implement.
Concrete implementations (e.g., UIAutomator2Adapter) translate these operations
into framework-specific device commands.

### Architectural Decisions:
    The interface covers the full spectrum of Android device interaction: connection
    management, UI state capture, touch/gesture actions, system navigation, screenshot
    capture, and application lifecycle. This breadth allows higher-level components
    (UIAutomatorActionExecutor, rv-agent) to remain framework-agnostic.

### Integration Points:
    - UIAutomatorActionExecutor dispatches GeneratedAction objects through this interface
    - rv-agent captures UI state and executes LLM-decided actions via adapters
    - rv-platform coordinates device lifecycle through adapter connect/disconnect
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class UIAdapter(ABC):
    """Abstract interface for UI adapters that interact with Android devices.

    ### Architectural Decisions:
    - Defines standardized methods for UI operations across different frameworks
    - Provides consistent interface for action execution engines
    - Handles both low-level device operations and high-level state management
    - Supports screenshot capture and UI hierarchy retrieval

    ### Role in the System:
    - Primary interface between testing tools and Android devices
    - Abstracts implementation details from higher-level components
    - Enables framework-agnostic testing strategies
    - Provides unified API for all testing tools

    ### Key Features:
    - Connection management with device identification
    - UI state capture including XML hierarchy, activity, and package info
    - Coordinate-based touch actions (click, long click, swipe)
    - Text input at focused elements
    - System navigation (back, home)
    - Screenshot capture with file persistence
    - Application lifecycle management (launch, stop)
    """

    @abstractmethod
    def connect(self, device_id: str) -> bool:
        """Establish connection to an Android device.

        Args:
            device_id: ADB device identifier (e.g., "emulator-5554").

        Returns:
            True if connection established successfully, False otherwise.
        """

    @abstractmethod
    def get_ui_state(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Retrieve current UI state from the device.

        Captures a snapshot of the device UI including XML hierarchy,
        current activity, current package, and device info.

        Args:
            force_refresh: Bypass any cached state and query device directly.

        Returns:
            Dictionary with keys: ``xml``, ``current_activity``,
            ``current_package``, ``device_info``, ``timestamp``.
            Empty dict on failure.
        """

    @abstractmethod
    def click(self, x: int, y: int) -> bool:
        """Perform click at specified coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.

        Returns:
            True if click executed successfully.
        """

    @abstractmethod
    def input_text(self, text: str) -> bool:
        """Input text at the currently focused element.

        Clears existing text before typing. Requires an input field
        to be focused (e.g., via a preceding click action).

        Args:
            text: Text string to input.

        Returns:
            True if text input completed successfully.
        """

    @abstractmethod
    def long_click(self, x: int, y: int, duration: float = 1.0) -> bool:
        """Perform long click at specified coordinates.

        Args:
            x: Horizontal pixel coordinate.
            y: Vertical pixel coordinate.
            duration: Hold duration in seconds.

        Returns:
            True if long click executed successfully.
        """

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> bool:
        """Perform swipe gesture between two points.

        Args:
            x1: Start horizontal coordinate.
            y1: Start vertical coordinate.
            x2: End horizontal coordinate.
            y2: End vertical coordinate.
            duration: Swipe duration in seconds.

        Returns:
            True if swipe executed successfully.
        """

    @abstractmethod
    def press_back(self) -> bool:
        """Press the device back button.

        Returns:
            True if back press executed successfully.
        """

    @abstractmethod
    def press_home(self) -> bool:
        """Press the device home button.

        Returns:
            True if home press executed successfully.
        """

    @abstractmethod
    def take_screenshot(self) -> Optional[str]:
        """Capture and save a device screenshot.

        Returns:
            File path to the saved screenshot, or None on failure.
        """

    @abstractmethod
    def launch_app(self, package_name: str) -> bool:
        """Launch an application by package name.

        Args:
            package_name: Android package identifier (e.g., "com.example.app").

        Returns:
            True if the app launched and is in the foreground.
        """

    @abstractmethod
    def stop_app(self, package_name: str) -> bool:
        """Stop an application by package name.

        Args:
            package_name: Android package identifier to stop.

        Returns:
            True if the app was stopped successfully.
        """
