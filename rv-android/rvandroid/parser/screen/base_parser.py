"""
Base module for screen parsers.
Provides a common interface and shared functionality for all screen parsers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, TypeVar, Generic

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rvandroid.parser.screen.visitor.model import ScreenDescription, Node
from rvandroid.util.logging.manager import LoggingManager

# Generic type for the return type of parsers
T = TypeVar('T', bound=ScreenDescription)


class BaseScreenParser(Generic[T], ABC):
    """
    Abstract base class for all screen parsers.
    
    This class defines a common interface and provides shared functionality
    for all parsers that process screen state data from various sources.
    Each specific parser should implement the abstract methods.
    """

    def __init__(self, parser_name: str, visitor_class: Optional[Type[AbstractScreenVisitor]] = None):
        """
        Initialize the parser with a name for logging purposes.
        
        Args:
            parser_name: Unique name for the parser (used in logging)
            visitor_class: Optional visitor class to use for parsing
        """
        self.parser_name = parser_name
        self.visitor_class = visitor_class
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(f"parser.screen.{parser_name}")

        # If no visitor_class is provided, use default visitor
        if self.visitor_class is None:
            from rvandroid.parser.screen.visitor.default_visitor import DefaultTextVisitor
            self.visitor_class = DefaultTextVisitor

    def parse_screen(self, state_data: Dict[str, Any],
                    static_data: Optional[StaticAnalysisData] = None) -> T:
        """
        Parse screen state data into a standardized ScreenDescription.
        
        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application (optional)
            
        Returns:
            ScreenDescription object containing parsed UI elements
            
        Raises:
            ValueError: If state data is invalid or cannot be parsed
        """
        # Common validation logic
        if not self.validate_state_data(state_data):
            self.logger.error(f"Invalid {self.parser_name} state data: missing required fields")
            raise ValueError(f"Invalid {self.parser_name} state data: missing required fields")
            
        activity = self.get_activity_name(state_data)
        self.logger.info(f"Parsing {self.parser_name} state for activity: {activity}")
        
        # Delegate to implementation-specific parsing
        screen_description = self._parse_implementation(state_data, static_data, activity)
        
        # Log summary
        self.logger.info(f"Parsed {len(screen_description.items)} UI elements")
        return screen_description
        
    @abstractmethod
    def _parse_implementation(self, state_data: Dict[str, Any],
                             static_data: Optional[StaticAnalysisData],
                             activity: str) -> T:
        """
        Implementation-specific parsing logic.
        
        Args:
            state_data: Dictionary containing UI state information
            static_data: Static analysis data for the application
            activity: Current activity name
            
        Returns:
            ScreenDescription object containing parsed UI elements
        """
        pass

    def create_visitor(self, static_data: Optional[StaticAnalysisData], activity: str) -> AbstractScreenVisitor:
        """
        Create a visitor instance based on configured visitor class.
        
        Args:
            static_data: Static analysis data
            activity: Current activity name
            
        Returns:
            AbstractScreenVisitor instance
        """
        self.logger.debug(f"Creating visitor: class={self.visitor_class.__name__}, activity={activity}")
        print(f"Creating visitor: class={self.visitor_class.__name__}, activity={activity}")
        return self.visitor_class(static_data, activity)
        
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
        
    def log_processing_summary(self, data_type: str, item_count: int) -> None:
        """
        Log a summary of processed data.
        
        Args:
            data_type: Type of data processed (e.g., "elements", "widgets")
            item_count: Number of items processed
        """
        self.logger.info(f"Processed {item_count} {data_type} from {self.parser_name} data")