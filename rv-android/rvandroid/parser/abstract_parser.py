# rvandroid/parser/abstract_parser.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.visitor.base_visitor import ScreenDescription


class AbstractScreenParser(ABC):
    """
    Abstract interface for parsing UI state data from different sources (DroidBot, UIAutomator2, etc.).
    Provides a common interface for extracting structured information from different formats.
    """

    def __init__(self):
        """Initialize the parser."""
        pass

    @abstractmethod
    def parse(self, state_data: Dict[str, Any], static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse state data into a standardized ScreenDescription.

        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application (optional)

        Returns:
            ScreenDescription object containing parsed UI elements

        Raises:
            ValueError: If state data is invalid or cannot be parsed
        """
        pass

    @abstractmethod
    def get_activity_name(self, state_data: Dict[str, Any]) -> str:
        """
        Extract the current activity name from the state data.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            Name of the current activity

        Raises:
            ValueError: If activity name cannot be determined
        """
        pass

    def get_package_name(self, state_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the package name from the state data.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            Package name if available, None otherwise
        """
        return state_data.get("package_name", None)

    def validate_state_data(self, state_data: Dict[str, Any]) -> bool:
        """
        Validate that state data contains required fields.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            True if valid, False otherwise
        """
        # Basic validation, can be overridden by subclasses
        required_fields = ["activity"]
        return all(field in state_data for field in required_fields)
