# rvandroid/parser/screen/abstract_parser.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, BaseScreenVisitor, Node


class AbstractScreenParser(ABC):
    """
    Abstract interface for parsing UI state data from different sources (DroidBot, UIAutomator2, etc.).
    Provides a common interface for extracting structured information from different formats.
    """

    def __init__(self, visitor_class: Optional[Type[BaseScreenVisitor]] = None):
        """
        Initialize the parser.

        Args:
            visitor_class: Optional visitor class to use for parsing
        """
        self.visitor_class = visitor_class

        # If no visitor_class is provided, use default visitor
        if self.visitor_class is None:
            from rvandroid.parser.screen.visitor.generic_visitor import GenericScreenVisitor
            self.visitor_class = GenericScreenVisitor

    def create_visitor(self, static_data: Optional[StaticAnalysisData], activity: str) -> BaseScreenVisitor:
        """
        Create a visitor instance based on configured visitor class.

        Args:
            static_data: Static analysis data
            activity: Current activity name

        Returns:
            BaseScreenVisitor instance
        """
        return self.visitor_class(static_data, activity)

    @abstractmethod
    def parse(self, state_data: Dict[str, Any],
              static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
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

    @abstractmethod
    def create_node_tree(self, state_data: Dict[str, Any]) -> Optional[Node]:
        """
        Create a Node tree from the state data.

        Args:
            state_data: Dictionary containing UI state information

        Returns:
            Root Node of the UI hierarchy or None if invalid data

        Raises:
            ValueError: If node tree cannot be created from the state data
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
        # Subclasses should override this method to provide source-specific validation
        return True
