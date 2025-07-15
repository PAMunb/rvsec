# base_parser.py
"""
Base parser module for static analysis parsers.

Provides a common interface for all static analysis parsers,
ensuring consistency and interoperability.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict

from rvandroid.domain.classes import Classes
from rvandroid.domain.window import Windows
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class BaseStaticAnalysisParser(ABC):
    """
    Abstract base class for all static analysis parsers.
    
    This class defines a common interface and provides shared functionality
    for all parsers that process static analysis output files and extract
    structured information.
    
    ### Architectural Decisions:
    - Provides a consistent interface for all parsers
    - Implements standard logging and error handling patterns
    - Separates parser initialization from file parsing logic
    - Supports creating singleton instances for performance
    
    ### Role in the System:
    - Serves as a foundation for all static analysis parsers
    - Ensures consistent behavior across different parsers
    - Simplifies integration of new parsers
    - Standardizes error handling and recovery
    """
    
    def __init__(self, parser_name: str):
        """
        Initialize the parser with a name.
        
        Args:
            parser_name: Unique name identifier for the parser (used in logging)
        """
        self.parser_name = parser_name
        
        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            f"parser.static.{parser_name}",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
    
    @abstractmethod
    def parse_file(self, file_path: str, package: Optional[str], classes: Optional[Classes], windows: Optional[Windows]) -> Any:
        """
        Parse a static analysis file.
        
        Args:
            file_path: Path to the file to parse
            package: Package name of the application (optional)
            classes: Classes object to populate with parsed data (optional)
            windows: Windows object to populate with parsed data (optional)
            
        Returns:
            Parsed data in an appropriate format for the specific parser
        """
        pass

    def validate_package(self, class_name, package):
        return package in class_name

    def log_parse_start(self, file_path: str):
        """
        Log the start of file parsing.
        
        Args:
            file_path: Path to the file being parsed
        """
        self.logger.info(f"Starting to parse file: {file_path}")
    
    def log_parse_complete(self, file_path: str, stats: Dict[str, Any]):
        """
        Log the completion of file parsing with statistics.
        
        Args:
            file_path: Path to the file that was parsed
            stats: Dictionary of parsing statistics
        """
        self.logger.debug(f"Completed parsing file: {file_path}")
        for key, value in stats.items():
            self.logger.debug(f"  {key}: {value}")
    
    def log_parse_error(self, file_path: str, error: Exception):
        """
        Log an error that occurred during parsing.
        
        Args:
            file_path: Path to the file that was being parsed
            error: The exception that occurred
        """
        self.logger.error(f"Error parsing file {file_path}: {str(error)}")


# deprecated
def create_parser_factory(parser_class):
    """
    Factory function for creating parser singletons.
    
    Args:
        parser_class: The parser class to instantiate
        
    Returns:
        Function that creates or returns a singleton instance of the parser
    """
    _instance = None
    
    def get_instance():
        nonlocal _instance
        if _instance is None:
            _instance = parser_class()
        return _instance
    
    return get_instance