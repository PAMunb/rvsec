from abc import ABC, abstractmethod
from typing import Dict, Any

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.visitor.base_visitor import ScreenDescription


class AbstractStateParser(ABC):
    """
    Abstract interface for parsing UI state data from different sources (DroidBot, UIAutomator2, etc.).
    Provides a common interface for extracting structured information from different formats.
    """

    @abstractmethod
    def parse(self, state_data: Dict[str, Any], static_data: StaticAnalysisData) -> ScreenDescription:
        """
        Parse state data into a standardized ScreenDescription.

        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application

        Returns:
            ScreenDescription object containing parsed UI elements
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
        """
        pass
