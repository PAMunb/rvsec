# rvandroid/parser/screen/abstract_parser.py
from typing import Dict, Any, Optional, Type

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.base_parser import BaseScreenParser
from rvandroid.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription


class AbstractScreenParser(BaseScreenParser[ScreenDescription]):
    """
    Abstract interface for parsing UI state data from different sources (DroidBot, UIAutomator2, etc.).
    Provides a common interface for extracting structured information from different formats.
    
    This class provides backward compatibility with existing code, extending the new BaseScreenParser.
    """

    def __init__(self, visitor_class: Optional[Type[AbstractScreenVisitor]] = None):
        """
        Initialize the parser.

        Args:
            visitor_class: Optional visitor class to use for parsing
        """
        super().__init__("abstract", visitor_class)

    def parse(self, state_data: Dict[str, Any],
             static_data: Optional[StaticAnalysisData] = None) -> ScreenDescription:
        """
        Parse state data into a standardized ScreenDescription.
        
        This method provides backward compatibility with existing code,
        delegating to the new parse_screen method.

        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application (optional)

        Returns:
            ScreenDescription object containing parsed UI elements

        Raises:
            ValueError: If state data is invalid or cannot be parsed
        """
        return self.parse_screen(state_data, static_data)
        
    def _parse_implementation(self, state_data: Dict[str, Any],
                             static_data: Optional[StaticAnalysisData],
                             activity: str) -> ScreenDescription:
        """
        Implementation-specific parsing logic.
        
        This is an abstract method that must be implemented by subclasses.
        
        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application
            activity: Current activity name
            
        Returns:
            ScreenDescription object containing parsed UI elements
        """
        raise NotImplementedError("Subclasses must implement _parse_implementation")