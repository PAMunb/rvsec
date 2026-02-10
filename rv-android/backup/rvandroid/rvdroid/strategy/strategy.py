# rvandroid/rvdroid/strategy/strategy.py

"""
Strategy framework for RVDroid.

This module provides the base classes and interfaces for implementing
testing strategies that guide the exploration of Android applications.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenDescription
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class Strategy(ABC):
    """
    Abstract base class for all exploration strategies.
    
    ### Architectural Decisions:
    - Defines the core interface for all testing strategies
    - Establishes consistent method signatures for action generation
    - Provides standardized feedback processing functionality
    - Enables flexible implementation of specialized strategies
    - Integrates with monitoring and logging infrastructure
    
    ### Role in the System:
    - Serves as the base for all specialized exploration strategies
    - Enables modular and interchangeable testing approaches
    - Supports dynamic adaptation to application characteristics
    - Facilitates strategy implementation and evolution
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "BaseStrategy"):
        """
        Initialize the strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rvdroid.strategy.{name.lower()}",
            {CONTEXT_COMPONENT: name}
        )

        # Store static data
        self.static_data = static_data
        self.name = name
        
        # Strategy configuration
        self.config: Dict[str, Any] = {}
        
        # Strategy state
        self.execution_count = 0
        self.success_count = 0
        self.new_state_count = 0

        self.logger.info(f"Initialized {name} strategy")
        
    @handle_error(level="WARN")
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the strategy with specific parameters.
        
        Args:
            config: Configuration parameters
        """
        self.config.update(config)
        self.logger.debug(f"Updated configuration for {self.name}")

    @abstractmethod
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action based on the current state and history.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            ItemAction to execute, or None if no action is available
        """
        pass

    @abstractmethod
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Update statistics
        self.execution_count += 1
        
        if result.get("success", False):
            self.success_count += 1
            
        if result.get("new_state", False):
            self.new_state_count += 1

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the strategy for logging and analysis.

        Returns:
            Dictionary with strategy metadata
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "new_state_count": self.new_state_count,
            "success_rate": self.success_count / max(1, self.execution_count)
        }
        
    def reset_statistics(self) -> None:
        """Reset strategy statistics."""
        self.execution_count = 0
        self.success_count = 0
        self.new_state_count = 0


class StrategyRegistry:
    """
    Registry for available strategies.
    
    ### Architectural Decisions:
    - Implements a central registry for strategy class discovery
    - Provides efficient strategy resolution with fallback mechanisms
    - Enables dynamic strategy registration at runtime
    - Supports flexible instantiation with configuration parameters
    
    ### Role in the System:
    - Maintains a collection of registered strategy classes
    - Provides methods for strategy discovery and instantiation
    - Facilitates dynamic strategy selection
    - Supports the StrategyManager with strategy creation
    """

    _strategies: Dict[str, type] = {}

    @classmethod
    def register(cls, strategy_class: type) -> None:
        """
        Register a strategy class.

        Args:
            strategy_class: Strategy class to register
        """
        if not issubclass(strategy_class, Strategy):
            raise TypeError(f"Strategy class must inherit from Strategy base class")

        class_name = strategy_class.__name__
        cls._strategies[class_name] = strategy_class
        # Use logger instead of print
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger("rvdroid.strategy.registry")
        logger.info(f"Registered strategy: {class_name}")

    @classmethod
    def get_strategy(cls, strategy_name: str) -> Optional[type]:
        """
        Get a strategy class by name.

        Args:
            strategy_name: Name of the strategy class

        Returns:
            Strategy class or None if not found
        """
        # Try exact match first
        if strategy_name in cls._strategies:
            return cls._strategies[strategy_name]

        # Try case-insensitive match
        strategy_name_lower = strategy_name.lower()
        for name, strategy_class in cls._strategies.items():
            if name.lower() == strategy_name_lower:
                return strategy_class

        # Try prefix match
        for name, strategy_class in cls._strategies.items():
            if name.lower().startswith(strategy_name_lower):
                return strategy_class

        return None

    @classmethod
    @handle_error(level="WARN")
    def create_strategy(cls, strategy_name: str, static_data: Optional[StaticAnalysisData] = None,
                        **kwargs) -> Optional[Strategy]:
        """
        Create a strategy instance by name.

        Args:
            strategy_name: Name of the strategy class
            static_data: Optional static analysis data
            **kwargs: Additional arguments for the strategy constructor

        Returns:
            Strategy instance or None if strategy not found
        """
        strategy_class = cls.get_strategy(strategy_name)
        if not strategy_class:
            # Use logger instead of print
            logging_manager = LoggingManager.get_instance()
            logger = logging_manager.get_logger("rvdroid.strategy.registry")
            logger.warning(f"Strategy not found: {strategy_name}, available: {list(cls._strategies.keys())}")
            return None

        try:
            return strategy_class(static_data=static_data, **kwargs)
        except Exception as e:
            # Use logger instead of print
            logging_manager = LoggingManager.get_instance()
            logger = logging_manager.get_logger("rvdroid.strategy.registry")
            logger.error(f"Error creating strategy {strategy_name}: {e}")
            return None

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        Get a list of available strategy names.

        Returns:
            List of strategy names
        """
        return list(cls._strategies.keys())