"""
Base module for screen parsers.

Provides a comprehensive framework for parsing Android screen state data from
multiple sources (DroidBot, UIAutomator) with standardized visitor pattern implementation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, TypeVar, Generic

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, Node

# Generic type for the return type of parsers
T = TypeVar('T', bound=ScreenDescription)


class BaseScreenParser(Generic[T], ABC):
    """
    Abstract base class for all screen parsers in the RV-Android framework.

    ### Architectural Decisions:
    - Implements a generic factory pattern for screen parsing across different input formats
    - Delegates specific parsing logic to concrete implementations while maintaining consistent interface
    - Uses visitor pattern for flexible element processing and data extraction
    - Provides comprehensive error handling through centralized ErrorHandler integration
    - Supports extensible logging through standardized LoggingManager framework

    ### Role in the System:
    - Serves as the foundation for all screen parsing operations within monitored operations
    - Facilitates standardized parsing of Android UI state from diverse sources
    - Enables consistent data transformation from various input formats to unified ScreenDescription
    - Provides extensible architecture for adding new parsing formats and visitor implementations
    - Supports integration with static analysis data for enhanced parsing context

    ### Design Note - Visitor Pattern:
    The parser framework uses visitor pattern to separate parsing logic from data traversal,
    enabling flexible processing strategies without modifying core parsing infrastructure.
    Default visitor implementations provide standard functionality while allowing custom
    visitor injection for specialized use cases.
    """

    def __init__(self, parser_name: str, visitor_class: Optional[Type[AbstractScreenVisitor]] = None):
        """
        Initialize the parser with standardized logging and error handling.
        
        Args:
            parser_name: Unique identifier for the parser implementation (used in logging and error tracking)
            visitor_class: Optional visitor class for custom element processing strategies
        """
        self.parser_name = parser_name
        self.visitor_class = visitor_class

        # Initialize standardized logging system
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            f"rv_screen_parser.parser.screen.{parser_name}",
            {
                CONTEXT_COMPONENT: f"screen_parser.{parser_name}"
            }
        )

        # Initialize centralized error handling
        self.error_handler = ErrorHandler.get_instance()

        # If no visitor_class is provided, use default visitor implementation
        if self.visitor_class is None:
            from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
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
        # Example: Using context manager for scoped error handling during parsing
        with self.error_handler.error_context(component="ScreenParser", phase="screen_parsing",
                                              parser_type=self.parser_name):
            # Common validation logic
            if not self.validate_state_data(state_data):
                self.logger.error(f"Invalid {self.parser_name} state data: missing required fields")
                from rv_android_core.util.error.exceptions import RVParsingError
                raise RVParsingError(f"Invalid {self.parser_name} state data: missing required fields",
                                     parser_type=self.parser_name)

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
