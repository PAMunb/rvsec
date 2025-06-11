"""
LLM Factory - Language Model Component Creation

### Architectural Overview:
This module implements the factory pattern for creating language model instances
with DI-ready interfaces. The factory provides a clean abstraction for LLM creation
while supporting multiple providers (Ollama, HuggingFace, Frontier models) and
comprehensive configuration management.

### Key Architectural Decisions:
- **Interface-Based Design**: ILLMFactory interface enables DI container integration
- **Provider Abstraction**: Unified interface across different LLM providers
- **Configuration-Driven**: All LLM creation based on configuration dictionaries
- **Error Handling**: Comprehensive error handling with detailed error context
- **Logging Integration**: Consistent logging throughout factory operations

### Role in the System:
- Primary factory for creating LLM instances across the application
- Provides consistent interface for all LLM providers
- Manages LLM configuration validation and parameter handling
- Enables clean dependency injection and testing patterns
- Coordinates with monitored operations and experiment configurations

### Design Patterns:
- **Factory Pattern**: Clean creation interface for LLM components
- **Strategy Pattern**: Different creation strategies for different providers
- **Interface Segregation**: Clear interfaces for DI container integration
- **Dependency Injection Ready**: All dependencies injected through constructor
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError

from rv_llm.llm.ollama_llm import OllamaLLM
from rv_llm.llm.huggingface_llm import HuggingFaceLLM
from rv_llm.llm.frontier_models import FrontierModel


class ILLMFactory(ABC):
    """
    Interface for LLM factory implementations.
    
    ### Architectural Decisions:
    This interface defines the contract for LLM creation factories, enabling
    clean dependency injection and consistent LLM management across the system.
    The interface is designed to be provider-agnostic while supporting
    comprehensive configuration and error handling.
    
    ### Role in the System:
    - Defines contract for DI container integration
    - Enables consistent LLM creation across different components
    - Supports testing through interface mocking
    - Provides clear abstraction for LLM provider management
    """
    
    @abstractmethod
    def create_ollama(self, model: str = "llama3", base_url: str = "http://localhost:11434", 
                      **kwargs) -> Any:
        """
        Create Ollama LLM instance with specified configuration.
        
        Args:
            model: Ollama model name (default: llama3)
            base_url: Ollama server URL (default: localhost:11434)
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured Ollama LLM instance
        """
        pass
    
    @abstractmethod
    def create_huggingface(self, model: str, device: str = "auto", **kwargs) -> Any:
        """
        Create HuggingFace LLM instance with specified configuration.
        
        Args:
            model: HuggingFace model identifier
            device: Device for model execution (default: auto)
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured HuggingFace LLM instance
        """
        pass
    
    @abstractmethod
    def create_frontier(self, model: str, provider: str, api_key: str, **kwargs) -> Any:
        """
        Create Frontier model instance with specified configuration.
        
        Args:
            model: Frontier model name
            provider: Frontier model provider
            api_key: API key for frontier model access
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured Frontier model instance
        """
        pass
    
    @abstractmethod
    def create_from_config(self, config: Dict[str, Any]) -> Any:
        """
        Create LLM instance from configuration dictionary.
        
        Args:
            config: LLM configuration dictionary
            
        Returns:
            Configured LLM instance based on configuration
        """
        pass


class LLMFactory(ILLMFactory):
    """
    Concrete implementation of LLM factory with comprehensive provider support.
    
    ### Architectural Overview:
    This factory implementation provides concrete LLM creation capabilities
    for all supported providers. It includes comprehensive error handling,
    configuration validation, and logging integration. The factory is designed
    to be injected through DI containers while maintaining clean interfaces.
    
    ### Key Architectural Decisions:
    - **Provider Support**: Comprehensive support for Ollama, HuggingFace, and Frontier models
    - **Configuration Validation**: Validates all LLM parameters before creation
    - **Error Recovery**: Graceful handling of LLM creation failures
    - **Logging Integration**: Detailed logging for debugging and monitoring
    - **DI Ready**: Constructor injection for all dependencies
    
    ### Role in the System:
    - Primary LLM creation implementation across the application
    - Provides consistent LLM configuration and validation
    - Manages LLM provider-specific creation logic
    - Enables monitoring and debugging of LLM creation
    - Supports experiment configuration coordination
    """
    
    def __init__(self, logger=None, error_handler=None):
        """
        Initialize LLM factory with dependency injection support.
        
        ### Initialization Strategy:
        - Accepts optional logger and error handler for DI container injection
        - Falls back to singleton instances when dependencies not provided
        - Sets up factory context for consistent logging and error handling
        - Prepares factory for LLM creation operations
        
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
                "rv_llm.factories.llm_factory",
                {CONTEXT_COMPONENT: "LLMFactory"}
            )
        
        # Error handler setup (prepared for DI injection)
        self.error_handler = error_handler
        
        self.logger.info("LLMFactory initialized with DI-ready architecture")
    
    @ErrorHandler.handle_errors(
        component="LLMFactory",
        phase="create_ollama"
    )
    def create_ollama(self, model: str = "llama3", base_url: str = "http://localhost:11434", 
                      **kwargs) -> OllamaLLM:
        """
        Create Ollama LLM instance with comprehensive configuration support.
        
        ### Creation Strategy:
        - Validates Ollama-specific configuration parameters
        - Creates OllamaLLM instance with proper error handling
        - Supports all Ollama configuration options through kwargs
        - Provides detailed logging for debugging and monitoring
        
        Args:
            model: Ollama model name (supports all Ollama models)
            base_url: Ollama server URL for connection
            **kwargs: Additional Ollama configuration (temperature, max_tokens, etc.)
            
        Returns:
            Configured OllamaLLM instance ready for use
            
        Raises:
            ConfigurationError: If Ollama configuration is invalid
            ConnectionError: If Ollama server is not accessible
        """
        self.logger.info(f"Creating Ollama LLM: model={model}, base_url={base_url}")
        
        # Validate Ollama configuration
        if not model:
            raise ConfigurationError("Ollama model name cannot be empty")
        
        if not base_url:
            raise ConfigurationError("Ollama base_url cannot be empty")
        
        # Extract common LLM parameters
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 2048)
        timeout = kwargs.get('timeout', 30)
        
        # Validate parameter ranges
        if not (0.0 <= temperature <= 2.0):
            raise ConfigurationError(f"Temperature must be between 0.0 and 2.0, got: {temperature}")
        
        if max_tokens <= 0:
            raise ConfigurationError(f"max_tokens must be positive, got: {max_tokens}")
        
        if timeout <= 0:
            raise ConfigurationError(f"timeout must be positive, got: {timeout}")
        
        try:
            # Create Ollama LLM instance
            ollama_llm = OllamaLLM(
                model=model,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'max_tokens', 'timeout']}
            )
            
            self.logger.info(f"Successfully created Ollama LLM: {model}")
            return ollama_llm
            
        except Exception as e:
            error_msg = f"Failed to create Ollama LLM {model}: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @ErrorHandler.handle_errors(
        component="LLMFactory",
        phase="create_huggingface"
    )
    def create_huggingface(self, model: str, device: str = "auto", **kwargs) -> HuggingFaceLLM:
        """
        Create HuggingFace LLM instance with comprehensive configuration support.
        
        ### Creation Strategy:
        - Validates HuggingFace model identifier and device configuration
        - Creates HuggingFaceLLM instance with proper device management
        - Supports all HuggingFace transformers configuration options
        - Provides detailed logging for model loading and device allocation
        
        Args:
            model: HuggingFace model identifier (e.g., "microsoft/DialoGPT-large")
            device: Device for model execution ("auto", "cpu", "cuda", "cuda:0", etc.)
            **kwargs: Additional HuggingFace configuration parameters
            
        Returns:
            Configured HuggingFaceLLM instance ready for use
            
        Raises:
            ConfigurationError: If HuggingFace configuration is invalid
            RuntimeError: If model loading fails or device is not available
        """
        self.logger.info(f"Creating HuggingFace LLM: model={model}, device={device}")
        
        # Validate HuggingFace configuration
        if not model:
            raise ConfigurationError("HuggingFace model identifier cannot be empty")
        
        # Validate device specification
        valid_devices = ["auto", "cpu"]
        if device not in valid_devices and not device.startswith("cuda"):
            self.logger.warning(f"Unusual device specification: {device}")
        
        try:
            # Create HuggingFace LLM instance
            hf_llm = HuggingFaceLLM(
                model=model,
                device=device,
                **kwargs
            )
            
            self.logger.info(f"Successfully created HuggingFace LLM: {model} on {device}")
            return hf_llm
            
        except Exception as e:
            error_msg = f"Failed to create HuggingFace LLM {model}: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @ErrorHandler.handle_errors(
        component="LLMFactory",
        phase="create_frontier"
    )
    def create_frontier(self, model: str, provider: str, api_key: str, **kwargs) -> FrontierModel:
        """
        Create Frontier model instance with comprehensive configuration support.
        
        ### Creation Strategy:
        - Validates Frontier model configuration and API credentials
        - Creates FrontierModel instance with provider-specific settings
        - Supports multiple frontier providers (OpenAI, Anthropic, etc.)
        - Provides secure handling of API keys and credentials
        
        Args:
            model: Frontier model name (e.g., "gpt-4", "claude-3-sonnet")
            provider: Frontier model provider (e.g., "openai", "anthropic")
            api_key: API key for frontier model access
            **kwargs: Additional provider-specific configuration parameters
            
        Returns:
            Configured FrontierModel instance ready for use
            
        Raises:
            ConfigurationError: If Frontier model configuration is invalid
            AuthenticationError: If API key is invalid or expired
        """
        self.logger.info(f"Creating Frontier model: model={model}, provider={provider}")
        
        # Validate Frontier configuration
        if not model:
            raise ConfigurationError("Frontier model name cannot be empty")
        
        if not provider:
            raise ConfigurationError("Frontier provider cannot be empty")
        
        if not api_key:
            raise ConfigurationError("Frontier API key cannot be empty")
        
        # Validate provider
        supported_providers = ["openai", "anthropic", "google", "cohere"]
        if provider.lower() not in supported_providers:
            self.logger.warning(f"Unsupported provider '{provider}', proceeding anyway")
        
        try:
            # Create Frontier model instance
            frontier_model = FrontierModel(
                model=model,
                provider=provider,
                api_key=api_key,
                **kwargs
            )
            
            self.logger.info(f"Successfully created Frontier model: {model} via {provider}")
            return frontier_model
            
        except Exception as e:
            error_msg = f"Failed to create Frontier model {model}: {e}"
            self.logger.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @ErrorHandler.handle_errors(
        component="LLMFactory",
        phase="create_from_config"
    )
    def create_from_config(self, config: Dict[str, Any]) -> Union[OllamaLLM, HuggingFaceLLM, FrontierModel]:
        """
        Create LLM instance from configuration dictionary with intelligent provider detection.
        
        ### Configuration-Driven Creation Strategy:
        - Analyzes configuration to determine appropriate LLM provider
        - Validates configuration completeness and parameter correctness
        - Routes to appropriate provider-specific creation method
        - Provides comprehensive error handling and validation feedback
        
        ### Supported Configuration Formats:
        
        **Ollama Configuration:**
        ```python
        {
            "provider": "ollama",
            "model": "llama3",
            "base_url": "http://localhost:11434",
            "temperature": 0.3,
            "max_tokens": 2048
        }
        ```
        
        **HuggingFace Configuration:**
        ```python
        {
            "provider": "huggingface",
            "model": "microsoft/DialoGPT-large",
            "device": "auto"
        }
        ```
        
        **Frontier Configuration:**
        ```python
        {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "sk-...",
            "temperature": 0.2
        }
        ```
        
        Args:
            config: LLM configuration dictionary with provider and model specifications
            
        Returns:
            Configured LLM instance based on provider specified in configuration
            
        Raises:
            ConfigurationError: If configuration is invalid or incomplete
            ValueError: If provider is not supported
        """
        self.logger.info("Creating LLM from configuration dictionary")
        
        # Validate configuration structure
        if not isinstance(config, dict):
            raise ConfigurationError("LLM configuration must be a dictionary")
        
        if "provider" not in config:
            raise ConfigurationError("LLM configuration must specify 'provider'")
        
        if "model" not in config:
            raise ConfigurationError("LLM configuration must specify 'model'")
        
        provider = config["provider"].lower()
        model = config["model"]
        
        self.logger.info(f"Creating LLM: provider={provider}, model={model}")
        
        # Route to appropriate provider creation method
        if provider == "ollama":
            base_url = config.get("base_url", "http://localhost:11434")
            
            # Extract Ollama-specific parameters
            ollama_params = {k: v for k, v in config.items() 
                           if k not in ["provider", "model", "base_url"]}
            
            return self.create_ollama(
                model=model,
                base_url=base_url,
                **ollama_params
            )
            
        elif provider == "huggingface":
            device = config.get("device", "auto")
            
            # Extract HuggingFace-specific parameters
            hf_params = {k: v for k, v in config.items() 
                        if k not in ["provider", "model", "device"]}
            
            return self.create_huggingface(
                model=model,
                device=device,
                **hf_params
            )
            
        elif provider in ["openai", "anthropic", "google", "cohere"]:
            if "api_key" not in config:
                raise ConfigurationError(f"Frontier provider '{provider}' requires 'api_key'")
            
            api_key = config["api_key"]
            
            # Extract frontier-specific parameters
            frontier_params = {k: v for k, v in config.items() 
                             if k not in ["provider", "model", "api_key"]}
            
            return self.create_frontier(
                model=model,
                provider=provider,
                api_key=api_key,
                **frontier_params
            )
            
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: ollama, huggingface, openai, anthropic, google, cohere"
            )