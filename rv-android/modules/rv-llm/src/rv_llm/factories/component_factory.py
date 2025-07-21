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
from rv_android_core.util.error.exceptions import (
    ConfigurationError, RVPromptError, RVLLMConnectionError,
    RVLLMModelError, RVLLMConfigurationError
)
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.language_model import LanguageModel
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository


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
    - Internal registry for extensibility
    - Comprehensive error handling and logging
    - Module boundary respect - no external tool dependencies
    
    ### Factory Methods:
    - **create_llm**: LLM backend instantiation
    - **create_strategy**: Prompt strategy creation and configuration
    - **register_llm_backend**: Register custom LLM backend
    
    ### Usage Examples:
    ```python
    # Create LLM components
    config = LLMConfig(llm_type="ollama", strategy_type="batch_action")
    llm = LLMComponentFactory.create_llm(config)
    strategy = LLMComponentFactory.create_strategy(config)
    
    # Register custom backend
    LLMComponentFactory.register_llm_backend("custom", CustomLLMClass)
    
    # For parser/visitor creation, use rv-screen-parser factories:
    from rv_screen_parser.parser.screen.parser_factory import ParserFactory, ParserType
    from rv_screen_parser.parser.screen.visitor.visitor_factory import VisitorFactory
    
    parser = ParserFactory.create(ParserType.DROIDBOT, visitor_class)
    visitor = VisitorFactory.create("enhanced", static_data, activity)
    ```
    """

    # Class-level logger for factory operations
    _logger = None

    # Internal registry for LLM backends - Phase 5 enhancement
    _llm_registry = {}
    _strategy_registry = {}

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
            RVLLMConfigurationError: If LLM configuration is invalid
            RVLLMConnectionError: If connection to LLM service fails
            RVLLMModelError: If LLM model creation fails
            ImportError: If required backend module is not available
        """
        logger = LLMComponentFactory._get_logger()
        llm_params = config.get_llm_parameters()

        try:
            # Check registry first for custom backends
            if config.llm_type in LLMComponentFactory._llm_registry:
                backend_class = LLMComponentFactory._llm_registry[config.llm_type]
                llm = backend_class(**llm_params)
                logger.info(f"Created LLM backend '{config.llm_type}' with model: {config.model}")
                return llm

            # Standard backend creation
            if config.llm_type == "ollama":
                from rv_llm.llm.ollama_llm import OllamaLLM

                llm = OllamaLLM(
                    model_name=config.model,
                    base_url=config.base_url,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    top_p=config.top_p,
                    top_k=config.top_k
                )
                logger.info(f"Created Ollama LLM with model: {config.model}")
                return llm

            elif config.llm_type == "openai":
                from rv_llm.llm.frontier_models import FrontierModel

                if not config.api_key:
                    raise RVLLMConfigurationError(
                        "OpenAI API key is required for OpenAI backend",
                        model_name=config.model,
                        config_field="api_key"
                    )

                llm = FrontierModel.create_openai(
                    model_name=config.model,
                    api_key=config.api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens
                )
                logger.info(f"Created OpenAI LLM with model: {config.model}")
                return llm

            elif config.llm_type == "anthropic":
                from rv_llm.llm.frontier_models import FrontierModel

                if not config.api_key:
                    raise RVLLMConfigurationError(
                        "Anthropic API key is required for Anthropic backend",
                        model_name=config.model,
                        config_field="api_key"
                    )

                llm = FrontierModel.create_anthropic(
                    model_name=config.model,
                    api_key=config.api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens
                )
                logger.info(f"Created Anthropic LLM with model: {config.model}")
                return llm

            elif config.llm_type == "google":
                from rv_llm.llm.frontier_models import FrontierModel

                if not config.api_key:
                    raise RVLLMConfigurationError(
                        "Google API key is required for Google backend",
                        model_name=config.model,
                        config_field="api_key"
                    )

                llm = FrontierModel.create_google(
                    model_name=config.model,
                    api_key=config.api_key,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens
                )
                logger.info(f"Created Google LLM with model: {config.model}")
                return llm

            elif config.llm_type == "huggingface":
                from rv_llm.llm.huggingface_llm import HuggingFaceLLM

                llm = HuggingFaceLLM(
                    model=config.model,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    **{k: v for k, v in llm_params.items() if k.startswith("hf_")}
                )
                logger.info(f"Created Hugging Face LLM with model: {config.model}")
                return llm

            else:
                raise RVLLMConfigurationError(
                    f"Unsupported LLM type: {config.llm_type}",
                    model_name=config.model,
                    config_field="llm_type"
                )

        except ImportError as e:
            error_msg = f"Failed to import LLM backend '{config.llm_type}': {e}"
            logger.error(error_msg)
            raise RVLLMModelError(error_msg, model_name=config.model, operation="import") from e

        except (RVLLMConfigurationError, RVLLMConnectionError, RVLLMModelError):
            # Re-raise specific LLM errors
            raise

        except Exception as e:
            error_msg = f"Failed to create LLM backend '{config.llm_type}': {e}"
            logger.error(error_msg)
            raise RVLLMModelError(error_msg, model_name=config.model, operation="creation") from e

    @staticmethod
    def register_strategy(strategy_type: str, strategy_class) -> None:
        """Register a strategy class with the factory.
        
        ### Strategy Registration:
        This method allows external modules to register strategy implementations
        with the factory. This enables the factory to create strategy instances
        without having hardcoded imports, supporting extensibility.
        
        Args:
            strategy_type: String identifier for the strategy type
            strategy_class: Strategy class that implements PromptStrategy interface
            
        Raises:
            TypeError: If strategy_class doesn't implement required interface
        """
        if not hasattr(strategy_class, 'generate_prompt'):
            raise TypeError("Strategy class must implement PromptStrategy interface")

        LLMComponentFactory._strategy_registry[strategy_type] = strategy_class
        logger = LLMComponentFactory._get_logger()
        logger.debug(f"Registered strategy: {strategy_type}")

    @staticmethod
    @ErrorHandler.handle_errors(
        component="LLMComponentFactory",
        operation="create_strategy"
    )
    def create_strategy(config: PromptConfig,
                        information_manager: Optional[InformationManager] = None,
                        template_repository: Optional[Jinja2TemplateRepository] = None) -> PromptStrategy:
        """Create strategy instance using registered strategy classes.
        
        ### Strategy Creation Process:
        1. Look up strategy class in registry using strategy type
        2. Instantiate strategy with provided dependencies
        3. Configure strategy using PromptConfig
        
        This method eliminates hardcoded imports by using a registry pattern,
        allowing external modules to register their strategy implementations.
        
        Args:
            config: Configuration containing strategy type and parameters
            information_manager: Optional information manager for strategy
            template_repository: Optional template repository for strategy
            
        Returns:
            Configured strategy instance
            
        Raises:
            ConfigurationError: If strategy type is not registered or configuration fails
            RVPromptError: If strategy creation or configuration fails
        """
        logger = LLMComponentFactory._get_logger()
        strategy_params = config.get_strategy_parameters()

        try:
            # Look up strategy class in registry
            strategy_class = LLMComponentFactory._strategy_registry.get(config.strategy_type)

            if strategy_class is None:
                available_strategies = list(LLMComponentFactory._strategy_registry.keys())
                raise ConfigurationError(
                    f"Strategy type '{config.strategy_type}' not registered. "
                    f"Available strategies: {available_strategies}"
                )

            # Create strategy instance
            strategy = strategy_class(
                name=config.strategy_type,
                information_manager=information_manager,
                template_repository=template_repository
            )
            logger.info(f"Created '{config.strategy_type}' strategy")

            # Configure strategy with PromptConfig
            if hasattr(strategy, 'configure_from_config'):
                strategy.configure_from_config(config)
                logger.debug(f"Configured strategy with parameters: {list(strategy_params.keys())}")

            return strategy

        except ConfigurationError:
            # Re-raise configuration errors
            raise

        except Exception as e:
            error_msg = f"Failed to create strategy '{config.strategy_type}': {e}"
            logger.error(error_msg)
            raise RVPromptError(error_msg, config.strategy_type, e) from e

    @staticmethod
    def register_llm_backend(llm_type: str, backend_class) -> None:
        """
        Register a custom LLM backend for extensibility.
        
        ### Registration Strategy:
        This method allows external modules to register custom LLM backends
        with the factory, enabling extensibility without modifying core code.
        
        Args:
            llm_type: String identifier for the LLM backend type
            backend_class: LLM backend class implementing LanguageModel interface
            
        Raises:
            TypeError: If backend_class doesn't implement LanguageModel interface
        """
        if not hasattr(backend_class, 'generate') or not hasattr(backend_class, 'models'):
            raise TypeError("Backend class must implement LanguageModel interface")

        LLMComponentFactory._llm_registry[llm_type] = backend_class
        logger = LLMComponentFactory._get_logger()
        logger.debug(f"Registered custom LLM backend: {llm_type}")

    @staticmethod
    def get_supported_llm_types() -> List[str]:
        """
        Get list of supported LLM backend types.
        
        Returns:
            List of supported LLM type strings (built-in + registered)
        """
        built_in = ["ollama", "openai", "anthropic", "google", "huggingface"]
        registered = list(LLMComponentFactory._llm_registry.keys())
        return built_in + registered

    @staticmethod
    def get_supported_strategy_types() -> List[str]:
        """Get list of supported strategy types.
        
        ### Strategy Type Resolution:
        Returns all strategy types that have been registered with the factory,
        providing a dynamic list based on actual registrations rather than
        hardcoded constants.
        
        Returns:
            List of registered strategy type strings
        """
        return list(LLMComponentFactory._strategy_registry.keys())

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

    @staticmethod
    def get_registry_info() -> Dict[str, Any]:
        """Get information about registered components for debugging.
        
        ### Registry Information:
        Provides comprehensive information about all registered components,
        including both LLM backends and strategy types. This is useful for
        debugging registration issues and understanding component availability.
        
        Returns:
            Dictionary with complete registry information
        """
        return {
            "llm_backends": {
                "registered": list(LLMComponentFactory._llm_registry.keys()),
                "built_in": ["ollama", "openai", "anthropic", "google", "huggingface"]
            },
            "strategies": {
                "registered": list(LLMComponentFactory._strategy_registry.keys()),
                "total_count": len(LLMComponentFactory._strategy_registry)
            },
            "registry_status": {
                "llm_registry_size": len(LLMComponentFactory._llm_registry),
                "strategy_registry_size": len(LLMComponentFactory._strategy_registry)
            }
        }
