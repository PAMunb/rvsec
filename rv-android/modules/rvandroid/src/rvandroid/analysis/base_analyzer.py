# rvandroid/analysis/base_analyzer.py
"""
Base analyzer module for dynamic analysis components.
Provides common functionality and interfaces for different analyzers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Generic, TypeVar

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

# Generic type for analysis result
T = TypeVar('T')


class BaseAnalyzer(Generic[T], ABC):
    """
    Abstract base class for all dynamic analysis components.
    
    This class defines a common interface and provides shared functionality
    for all analyzers that process runtime data and provide insights.
    Each specific analyzer should implement the abstract methods.
    
    ### Architectural Decisions:
    - Provides a consistent interface for all analyzers
    - Supports both static data initialization and runtime data processing
    - Implements standard logging and configuration patterns
    - Enables standardized result formatting and metrics calculation
    
    ### Role in the System:
    - Serves as a foundation for all dynamic analysis components
    - Ensures consistent behavior across different analyzers
    - Simplifies integration of new analysis capabilities
    - Standardizes logging and error handling
    """

    def __init__(self, analyzer_name: str, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the analyzer with a name and optional static data.
        
        Args:
            analyzer_name: Unique name for the analyzer (used in logging)
            static_data: Static analysis data for initializing the analyzer
        """
        self.analyzer_name = analyzer_name
        self.static_data = static_data

        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            f"analysis.{analyzer_name}",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )

        # Initialize with static data if available
        if static_data:
            self._initialize_from_static_data()

    @abstractmethod
    def _initialize_from_static_data(self) -> None:
        """
        Initialize the analyzer with static analysis data.
        
        Each analyzer should implement this method to initialize
        its internal state based on the provided static data.
        """
        pass

    @abstractmethod
    def analyze(self, data: Any) -> T:
        """
        Analyze data and return results.
        
        Args:
            data: The data to analyze
            
        Returns:
            Analysis result of type T
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the analyzer.
        
        Returns:
            Dictionary containing metrics and their values
        """
        pass

    def log_processing_summary(self, data_type: str, count: int) -> None:
        """
        Log a summary of processed data.
        
        Args:
            data_type: Type of data processed
            count: Number of items processed
        """
        self.logger.info(f"Processed {count} {data_type}")


class BaseRepository:
    """
    Base class for repositories used by analyzers.
    
    Repositories are responsible for storing and managing data
    processed by analyzers, providing a consistent interface for
    data storage, retrieval, and manipulation.
    
    ### Architectural Decisions:
    - Separates data storage from analysis logic
    - Provides a consistent interface for data operations
    - Supports both generic and specialized operations
    
    ### Role in the System:
    - Acts as a data storage layer for analyzers
    - Provides optimized access to analysis data
    - Enables consistent data operations across analyzers
    """

    def __init__(self, repository_name: str):
        """
        Initialize the repository.
        
        Args:
            repository_name: Unique name for the repository (used in logging)
        """
        self.repository_name = repository_name

        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            f"analysis.{repository_name}",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )

    def log_storage_summary(self, data_type: str, count: int) -> None:
        """
        Log a summary of stored data.
        
        Args:
            data_type: Type of data stored
            count: Number of items stored
        """
        self.logger.info(f"Storing {count} {data_type}")
