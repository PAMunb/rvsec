"""
Prompt Strategy Factory - Strategy Component Creation for Prompt Management

### Architectural Overview:
This module implements the factory pattern for creating prompt strategy instances
with DI-ready interfaces. The factory provides a clean abstraction for prompt strategy
creation while supporting multiple strategy types (standard, batch action, flow-based)
and comprehensive configuration management for monitored operations.

### Key Architectural Decisions:
- **Interface-Based Design**: IPromptStrategyFactory interface enables DI container integration
- **Strategy Abstraction**: Unified interface across different prompt generation strategies
- **Configuration-Driven**: All strategy creation based on configuration dictionaries
- **Error Handling**: Comprehensive error handling with detailed error context
- **Logging Integration**: Consistent logging throughout factory operations

### Role in the System:
- Primary factory for creating prompt strategy instances across the application
- Provides consistent interface for all prompt strategy types
- Manages strategy configuration validation and parameter handling
- Enables clean dependency injection and testing patterns
- Coordinates with monitored operations and LLM configurations

### Design Patterns:
- **Factory Pattern**: Clean creation interface for prompt strategy components
- **Strategy Pattern**: Different creation strategies for different prompt approaches
- **Interface Segregation**: Clear interfaces for DI container integration
- **Dependency Injection Ready**: All dependencies injected through constructor
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError

from rv_llm.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
from rv_llm.llm.prompt.strategy.strategies.batch_action_strategy import BatchActionStrategy
from rv_llm.llm.prompt.strategy.base_strategy import BasePromptStrategy


class IPromptStrategyFactory(ABC):
    """
    Interface for prompt strategy factory implementations.
    
    ### Architectural Decisions:
    This interface defines the contract for prompt strategy creation factories, enabling
    clean dependency injection and consistent strategy management across the system.
    The interface is designed to be strategy-agnostic while supporting comprehensive
    configuration and monitored operations integration.
    
    ### Role in the System:
    - Defines contract for DI container integration
    - Enables consistent strategy creation across different components
    - Supports testing through interface mocking
    - Provides clear abstraction for prompt strategy management
    """
    
    @abstractmethod
    def create_standard(self, **kwargs) -> BasePromptStrategy:
        """
        Create standard prompt strategy for single-action generation.
        
        Args:
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured standard prompt strategy instance
        """
        pass
    
    @abstractmethod
    def create_batch_action(self, batch_size: int = 3, **kwargs) -> BasePromptStrategy:
        """
        Create batch action strategy for multi-action generation.
        
        Args:
            batch_size: Number of actions to generate in batch (default: 3)
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured batch action strategy instance
        """
        pass
    
    @abstractmethod
    def create_flow_based_batch(self, **kwargs) -> BasePromptStrategy:
        """
        Create flow-based batch strategy for workflow-driven generation.
        
        Args:
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured flow-based batch strategy instance
        """
        pass
    
    @abstractmethod
    def create_from_config(self, config: Dict[str, Any]) -> BasePromptStrategy:
        """
        Create prompt strategy instance from configuration dictionary.
        
        Args:
            config: Strategy configuration dictionary
            
        Returns:
            Configured strategy instance based on configuration
        """
        pass


class PromptStrategyFactory(IPromptStrategyFactory):
    """
    Concrete implementation of prompt strategy factory with comprehensive strategy support.
    
    ### Architectural Overview:
    This factory implementation provides concrete prompt strategy creation capabilities
    for all supported strategy types. It includes comprehensive error handling,
    configuration validation, and logging integration. The factory is designed
    to be injected through DI containers while maintaining clean interfaces.
    
    ### Key Architectural Decisions:
    - **Strategy Support**: Comprehensive support for standard, batch, and flow-based strategies
    - **Configuration Validation**: Validates all strategy parameters before creation
    - **Error Recovery**: Graceful handling of strategy creation failures
    - **Logging Integration**: Detailed logging for debugging and monitoring
    - **DI Ready**: Constructor injection for all dependencies
    
    ### Role in the System:
    - Primary strategy creation implementation across the application
    - Provides consistent strategy configuration and validation
    - Manages strategy-specific creation logic and parameter handling
    - Enables monitoring and debugging of strategy creation
    - Supports experiment configuration coordination
    """
    
    def __init__(self, logger=None, error_handler=None):
        """
        Initialize prompt strategy factory with dependency injection support.
        
        ### Initialization Strategy:
        - Accepts optional logger and error handler for DI container injection
        - Falls back to singleton instances when dependencies not provided
        - Sets up factory context for consistent logging and error handling
        - Prepares factory for strategy creation operations
        
        Args:
            logger: Optional logger instance (falls back to LoggingManager)
            error_handler: Optional error handler (falls back to ErrorHandler)
        """
        # DI-ready dependency management
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_llm.factories.prompt_strategy_factory",
                {CONTEXT_COMPONENT: "PromptStrategyFactory"}
            )
        
        # Error handler setup (prepared for DI injection)
        self.error_handler = error_handler
        
        self.logger.info("PromptStrategyFactory initialized with DI-ready architecture")
    
    @ErrorHandler.handle_errors(
        component="PromptStrategyFactory",
        phase="create_standard"
    )
    def create_standard(self, **kwargs) -> StandardStrategy:
        """
        Create standard prompt strategy for single-action generation.
        
        ### Creation Strategy:
        - Creates StandardStrategy optimized for single-action prompt generation
        - Validates strategy-specific configuration parameters
        - Supports comprehensive prompt template and context management
        - Provides detailed logging for strategy creation and configuration
        
        Args:
            **kwargs: Additional configuration parameters for standard strategy
            
        Returns:
            Configured StandardStrategy instance ready for prompt generation
            
        Raises:
            ConfigurationError: If standard strategy configuration is invalid
        """
        self.logger.info("Creating standard prompt strategy for single-action generation")
        
        try:
            # Extract and validate standard strategy parameters
            use_context = kwargs.get('use_context', True)
            max_context_length = kwargs.get('max_context_length', 4000)
            include_history = kwargs.get('include_history', True)
            
            # Validate parameter ranges
            if max_context_length <= 0:
                raise ConfigurationError(f"max_context_length must be positive, got: {max_context_length}")
            
            # Create standard strategy instance
            strategy = StandardStrategy(
                use_context=use_context,
                max_context_length=max_context_length,
                include_history=include_history,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['use_context', 'max_context_length', 'include_history']}
            )
            
            self.logger.info("Successfully created standard prompt strategy")
            return strategy
            
        except Exception as e:
            error_msg = f"Failed to create standard prompt strategy: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @ErrorHandler.handle_errors(
        component="PromptStrategyFactory",
        phase="create_batch_action"
    )
    def create_batch_action(self, batch_size: int = 3, **kwargs) -> BatchActionStrategy:
        """
        Create batch action strategy for multi-action generation.
        
        ### Creation Strategy:
        - Creates BatchActionStrategy optimized for multi-action prompt generation
        - Validates batch size and strategy-specific configuration parameters
        - Supports comprehensive batch management and action coordination
        - Provides detailed logging for batch strategy creation and configuration
        
        Args:
            batch_size: Number of actions to generate in batch (default: 3)
            **kwargs: Additional configuration parameters for batch strategy
            
        Returns:
            Configured BatchActionStrategy instance ready for batch prompt generation
            
        Raises:
            ConfigurationError: If batch strategy configuration is invalid
        """
        self.logger.info(f"Creating batch action strategy: batch_size={batch_size}")
        
        # Validate batch size
        if batch_size <= 0:
            raise ConfigurationError(f"batch_size must be positive, got: {batch_size}")
        
        if batch_size > 10:
            self.logger.warning(f"Large batch size may impact performance: {batch_size}")
        
        try:
            # Extract and validate batch strategy parameters
            use_action_coordination = kwargs.get('use_action_coordination', True)
            max_batch_context = kwargs.get('max_batch_context', 6000)
            include_cross_action_context = kwargs.get('include_cross_action_context', True)
            
            # Validate parameter ranges
            if max_batch_context <= 0:
                raise ConfigurationError(f"max_batch_context must be positive, got: {max_batch_context}")
            
            # Create batch action strategy instance
            strategy = BatchActionStrategy(
                batch_size=batch_size,
                use_action_coordination=use_action_coordination,
                max_batch_context=max_batch_context,
                include_cross_action_context=include_cross_action_context,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['use_action_coordination', 'max_batch_context', 'include_cross_action_context']}
            )
            
            self.logger.info(f"Successfully created batch action strategy: batch_size={batch_size}")
            return strategy
            
        except Exception as e:
            error_msg = f"Failed to create batch action strategy: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @ErrorHandler.handle_errors(
        component="PromptStrategyFactory",
        phase="create_flow_based_batch"
    )
    def create_flow_based_batch(self, **kwargs) -> BasePromptStrategy:
        """
        Create flow-based batch strategy for workflow-driven generation.
        
        ### Creation Strategy:
        - Creates flow-based strategy optimized for workflow-driven prompt generation
        - Validates flow configuration and workflow-specific parameters
        - Supports comprehensive flow management and workflow coordination
        - Provides detailed logging for flow strategy creation and configuration
        
        Args:
            **kwargs: Additional configuration parameters for flow-based strategy
            
        Returns:
            Configured flow-based strategy instance ready for workflow prompt generation
            
        Raises:
            ConfigurationError: If flow-based strategy configuration is invalid
        """
        self.logger.info("Creating flow-based batch strategy for workflow-driven generation")
        
        try:
            # Extract and validate flow-based strategy parameters
            max_flow_depth = kwargs.get('max_flow_depth', 5)
            use_workflow_context = kwargs.get('use_workflow_context', True)
            enable_flow_optimization = kwargs.get('enable_flow_optimization', True)
            
            # Validate parameter ranges
            if max_flow_depth <= 0:
                raise ConfigurationError(f"max_flow_depth must be positive, got: {max_flow_depth}")
            
            # TODO: Implement FlowBasedBatchStrategy when available
            # For now, create batch action strategy with flow-optimized parameters
            from rv_llm.llm.prompt.strategy.strategies.batch_action_strategy import BatchActionStrategy
            
            strategy = BatchActionStrategy(
                batch_size=kwargs.get('batch_size', 3),
                use_action_coordination=use_workflow_context,
                max_batch_context=kwargs.get('max_batch_context', 6000),
                include_cross_action_context=enable_flow_optimization,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['max_flow_depth', 'use_workflow_context', 'enable_flow_optimization']}
            )
            
            self.logger.info("Successfully created flow-based batch strategy (using batch action implementation)")
            return strategy
            
        except Exception as e:
            error_msg = f"Failed to create flow-based batch strategy: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @ErrorHandler.handle_errors(
        component="PromptStrategyFactory",
        phase="create_from_config"
    )
    def create_from_config(self, config: Dict[str, Any]) -> BasePromptStrategy:
        """
        Create prompt strategy instance from configuration dictionary with intelligent type detection.
        
        ### Configuration-Driven Creation Strategy:
        - Analyzes configuration to determine appropriate strategy type
        - Validates configuration completeness and parameter correctness
        - Routes to appropriate strategy-specific creation method
        - Provides comprehensive error handling and validation feedback
        
        ### Supported Configuration Formats:
        
        **Standard Strategy Configuration:**
        ```python
        {
            "type": "standard",
            "use_context": true,
            "max_context_length": 4000,
            "include_history": true
        }
        ```
        
        **Batch Action Strategy Configuration:**
        ```python
        {
            "type": "batch_action",
            "batch_size": 3,
            "use_action_coordination": true,
            "max_batch_context": 6000
        }
        ```
        
        **Flow-Based Strategy Configuration:**
        ```python
        {
            "type": "flow_based_batch",
            "max_flow_depth": 5,
            "use_workflow_context": true,
            "enable_flow_optimization": true
        }
        ```
        
        Args:
            config: Strategy configuration dictionary with type and parameters
            
        Returns:
            Configured strategy instance based on type specified in configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
            ValueError: If strategy type is not supported
        """
        self.logger.info("Creating prompt strategy from configuration dictionary")
        
        # Validate configuration structure
        if not isinstance(config, dict):
            raise ConfigurationError("Strategy configuration must be a dictionary")
        
        if "type" not in config:
            raise ConfigurationError("Strategy configuration must specify 'type'")
        
        strategy_type = config["type"].lower()
        
        self.logger.info(f"Creating prompt strategy: type={strategy_type}")
        
        # Extract strategy-specific parameters
        strategy_params = {k: v for k, v in config.items() if k != "type"}
        
        # Route to appropriate strategy creation method
        if strategy_type == "standard":
            return self.create_standard(**strategy_params)
            
        elif strategy_type == "batch_action":
            batch_size = strategy_params.pop("batch_size", 3)
            return self.create_batch_action(batch_size=batch_size, **strategy_params)
            
        elif strategy_type == "flow_based_batch":
            return self.create_flow_based_batch(**strategy_params)
            
        else:
            raise ValueError(
                f"Unsupported strategy type: {strategy_type}. "
                f"Supported types: standard, batch_action, flow_based_batch"
            )