"""
LLM Component Factory for creating configured LLM components.

This module provides a modern factory implementation for creating LLM components
for monitored operations testing, with clean separation between configuration 
and object instantiation within the rv-llm module boundaries.

### Architectural Overview:
This factory implements the modern factory pattern for LLM component creation,
providing clear separation between configuration (LLMConfig) and object instantiation.
It handles the creation of LLM backends and prompt strategies within the rv-llm
module scope, without dependencies on external tools or services.

### Key Architectural Decisions:
- **Module Boundaries**: Stays within rv-llm module, no external tool dependencies
- **Component Focus**: Creates only LLM backends and prompt strategies
- **Static Methods**: Stateless factory operations for thread safety
- **Comprehensive Error Handling**: ErrorHandler integration for robust operation
- **Type Safety**: Full type annotations and validation

### Role in the System:
- Creates configured LLM backend instances from LLMConfig
- Handles prompt strategy creation and configuration
- Provides clean interface for LLM component creation
- Centralizes component creation logic within rv-llm module

### Design Patterns:
- **Factory Pattern**: Centralized component creation with configuration
- **Strategy Pattern**: Dynamic strategy creation based on configuration
- **Dependency Injection**: Clean parameter passing between components

### Integration Strategy:
- Used by external tools (rvandroid-tool, etc.) for component creation
- Integrates with LLMConfig for configuration data
- Works with existing strategy and LLM implementations
- Provides extension points for new LLM backends
"""

from typing import Any, Dict, List, Optional, Tuple

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError, RVLLMError
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from rv_llm.llm.language_model import LanguageModel


class LLMComponentFactory:
    """
    Factory for creating configured LLM components for monitored operations testing.
    
    ### Architectural Overview:
    This factory provides a clean, stateless interface for creating LLM components
    from LLMConfig instances. It handles the creation of LLM backends and prompt
    strategies within the rv-llm module boundaries, without external dependencies.
    
    ### Key Features:
    - Stateless factory operations for thread safety
    - Support for multiple LLM backends (Ollama, OpenAI, Anthropic, Google)
    - Dynamic strategy creation based on configuration
    - Comprehensive error handling and logging
    - Module boundary respect - no external tool dependencies
    
    ### Factory Methods:
    - **create_llm**: LLM backend instantiation
    - **create_strategy**: Prompt strategy creation and configuration
    
    ### Usage Examples:
    ```python
    # Create LLM components
    config = LLMConfig(llm_type="ollama", strategy_type="batch_action")
    llm = LLMComponentFactory.create_llm(config)
    strategy = LLMComponentFactory.create_strategy(config)
    
    # For parser/visitor creation, use rv-screen-parser factories:
    from rv_screen_parser.parser.screen.parser_factory import ParserFactory, ParserType
    from rv_screen_parser.parser.screen.visitor.visitor_factory import VisitorFactory
    
    parser = ParserFactory.create(ParserType.DROIDBOT, visitor_class)
    visitor = VisitorFactory.create("enhanced", static_data, activity)
    ```
    """
    
    # Class-level logger for factory operations
    _logger = None
    
    @classmethod
    def _get_logger(cls):
        """Get logger instance for factory operations."""
        if cls._logger is None:
            logging_manager = LoggingManager.get_instance()
            cls._logger = logging_manager.get_logger(
                "llm.factories.component_factory",
                {CONTEXT_COMPONENT: "LLMComponentFactory"}
            )
        return cls._logger
    
    
    @staticmethod
    @ErrorHandler.handle_errors(
        component="LLMComponentFactory",
        operation="create_llm"
    )
    def create_llm(config: LLMConfig) -> LanguageModel:
        """
        Create LLM backend instance based on configuration.
        
        ### LLM Backend Creation Strategy:
        This method handles the instantiation of different LLM backends based on
        the configuration type. Each backend has its own initialization parameters
        and requirements, which are extracted from the configuration.
        
        ### Supported Backends:
        - **Ollama**: Local model serving with configurable base URL
        - **OpenAI**: GPT models via OpenAI API
        - **Anthropic**: Claude models via Anthropic API
        - **Google**: Gemini models via Google API
        - **Hugging Face**: Local and remote models via Hugging Face
        
        Args:
            config: LLMConfig with backend configuration
            
        Returns:
            Configured LLM backend instance
            
        Raises:
            ConfigurationError: If LLM configuration is invalid
            RVLLMError: If LLM backend creation fails
            ImportError: If required backend module is not available
        """
        logger = LLMComponentFactory._get_logger()
        llm_params = config.get_llm_parameters()
        
        try:
            if config.llm_type == "ollama":
                from rv_llm.llm.ollama_llm import OllamaLLM
                
                llm = OllamaLLM(
                    model=config.model,
                    base_url=config.base_url,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    top_p=config.top_p,
                    top_k=config.top_k
                )
                logger.debug(f"Created Ollama LLM with model: {config.model}")
                return llm
                
            elif config.llm_type == "openai":
                from rv_llm.llm.frontier_models import FrontierModel
                
                if not config.api_key:
                    raise ConfigurationError("OpenAI API key is required for OpenAI backend")
                
                llm = FrontierModel.create_openai(
                    model=config.model,
                    api_key=config.api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens
                )
                logger.debug(f"Created OpenAI LLM with model: {config.model}")
                return llm
                
            elif config.llm_type == "anthropic":
                from rv_llm.llm.frontier_models import FrontierModel
                
                if not config.api_key:
                    raise ConfigurationError("Anthropic API key is required for Anthropic backend")
                
                llm = FrontierModel.create_anthropic(
                    model=config.model,
                    api_key=config.api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens
                )
                logger.debug(f"Created Anthropic LLM with model: {config.model}")
                return llm
                
            elif config.llm_type == "google":
                from rv_llm.llm.frontier_models import FrontierModel
                
                if not config.api_key:
                    raise ConfigurationError("Google API key is required for Google backend")
                
                llm = FrontierModel.create_google(
                    model=config.model,
                    api_key=config.api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens
                )
                logger.debug(f"Created Google LLM with model: {config.model}")
                return llm
                
            elif config.llm_type == "huggingface":
                from rv_llm.llm.huggingface_llm import HuggingFaceLLM
                
                llm = HuggingFaceLLM(
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    **{k: v for k, v in llm_params.items() if k.startswith("hf_")}
                )
                logger.debug(f"Created Hugging Face LLM with model: {config.model}")
                return llm
                
            else:
                raise ConfigurationError(f"Unsupported LLM type: {config.llm_type}")
                
        except ImportError as e:
            error_msg = f"Failed to import LLM backend '{config.llm_type}': {e}"
            logger.error(error_msg)
            raise ImportError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Failed to create LLM backend '{config.llm_type}': {e}"
            logger.error(error_msg)
            raise RVLLMError(error_msg, config.model) from e
    
    @staticmethod
    @ErrorHandler.handle_errors(
        component="LLMComponentFactory",
        operation="create_strategy"
    )
    def create_strategy(config: LLMConfig) -> PromptStrategy:
        """
        Create and configure prompt strategy based on configuration.
        
        ### Strategy Creation Strategy:
        This method creates the appropriate prompt strategy implementation based on
        the configured strategy type and applies the configuration parameters to it.
        The strategy is responsible for generating prompts for LLM interaction.
        
        ### Supported Strategies:
        - **standard**: Single action generation with balanced approach
        - **batch_action**: Multiple action generation in structured format
        - **frontier**: Advanced strategy for frontier model backends
        
        Args:
            config: LLMConfig with strategy configuration
            
        Returns:
            Configured prompt strategy instance
            
        Raises:
            ConfigurationError: If strategy configuration is invalid
            RVLLMError: If strategy creation fails
            ImportError: If strategy module is not available
        """
        logger = LLMComponentFactory._get_logger()
        strategy_params = config.get_strategy_parameters()
        
        try:
            if config.strategy_type == "batch_action":
                from rv_llm.llm.prompt.strategy.strategies.batch_action_strategy import BatchActionStrategy
                
                strategy = BatchActionStrategy()
                logger.debug("Created batch action strategy")
                
            elif config.strategy_type in ["standard", "single_action"]:
                from rv_llm.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
                
                strategy = StandardStrategy()
                logger.debug("Created standard strategy")
                
            elif config.strategy_type == "frontier":
                from rv_llm.llm.prompt.strategy.strategies.frontier_strategy import FrontierStrategy
                
                strategy = FrontierStrategy()
                logger.debug("Created frontier strategy")
                
            else:
                raise ConfigurationError(f"Unsupported strategy type: {config.strategy_type}")
            
            # Configure strategy with LLMConfig
            strategy.configure_from_config(config)
            logger.debug(f"Configured strategy with parameters: {list(strategy_params.keys())}")
            
            return strategy
            
        except ImportError as e:
            error_msg = f"Failed to import strategy '{config.strategy_type}': {e}"
            logger.error(error_msg)
            raise ImportError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Failed to create strategy '{config.strategy_type}': {e}"
            logger.error(error_msg)
            raise RVLLMError(error_msg, config.model) from e
    
    
    @staticmethod
    def get_supported_llm_types() -> List[str]:
        """
        Get list of supported LLM backend types.
        
        Returns:
            List of supported LLM type strings
        """
        return ["ollama", "openai", "anthropic", "google", "huggingface"]
    
    @staticmethod
    def get_supported_strategy_types() -> List[str]:
        """
        Get list of supported strategy types.
        
        Returns:
            List of supported strategy type strings
        """
        return ["standard", "batch_action", "frontier"]
    
    
    @staticmethod
    def validate_backend_availability(llm_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a specific LLM backend is available for use.
        
        ### Availability Check Strategy:
        This method attempts to import the required modules for a specific LLM
        backend to determine if it's available in the current environment.
        
        Args:
            llm_type: LLM backend type to validate
            
        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            if llm_type == "ollama":
                from rv_llm.llm.ollama_llm import OllamaLLM
            elif llm_type == "openai":
                from rv_llm.llm.frontier_models import FrontierModel
            elif llm_type == "anthropic":
                from rv_llm.llm.frontier_models import FrontierModel
            elif llm_type == "google":
                from rv_llm.llm.frontier_models import FrontierModel
            elif llm_type == "huggingface":
                from rv_llm.llm.huggingface_llm import HuggingFaceLLM
            else:
                return False, f"Unsupported LLM type: {llm_type}"
            
            return True, None
            
        except ImportError as e:
            return False, f"Backend '{llm_type}' not available: {e}"
        except Exception as e:
            return False, f"Error checking backend '{llm_type}': {e}"