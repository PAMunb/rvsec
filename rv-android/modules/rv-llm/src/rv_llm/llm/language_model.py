"""
Language Model abstraction layer for RV-Android LLM integration.

This module provides the base interface for all language model implementations,
ensuring consistent interaction patterns and standardized configuration management
across different model providers and deployment types.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.llm_config import LLMConfig
from .data_structures import LLMMessage, LLMResponse


class LanguageModel(ABC):
    """
    Base class for language model implementations.
    
    The LanguageModel class provides a standardized interface for all language model
    integrations within the RV-Android system, ensuring consistent behavior across
    different model providers while maintaining flexibility for provider-specific features.

    ### Architectural Decisions:
    - **Standardized Interface**: Defines a unified API for all language model interactions,
      enabling seamless switching between different model implementations
    - **Configuration Management**: Provides consistent configuration patterns using
      LLMConfig for all model-specific parameters
    - **Error Handling Integration**: Implements centralized error handling through
      ErrorHandler for failure management and recovery
    - **Performance Monitoring**: Standardizes metrics collection for model performance
      analysis and optimization
    - **Resource Management**: Ensures proper cleanup and resource deallocation through
      explicit lifecycle management
    - **Provider Agnostic**: Abstracts away provider-specific details while allowing
      customization through configuration parameters

    ### Role in the System:
    - **Central Abstraction**: Primary interface for all LLM operations within RV-Android
    - **Provider Bridge**: Connects the system to diverse language model providers
    - **Configuration Controller**: Manages model-specific parameters and behavior
    - **Performance Monitor**: Tracks and reports model usage and performance metrics
    - **Resource Manager**: Handles model lifecycle and resource cleanup
    - **Error Boundary**: Provides error handling across all model operations

    ### Integration Points:
    - **ErrorHandler**: Centralized error handling and recovery strategies
    - **LoggingManager**: Standardized logging with contextual information
    - **LLMConfig**: Type-safe configuration management
    - **PromptFramework**: Integration with structured prompt generation

    ### Performance Considerations:
    - **Lazy Loading**: Models loaded on-demand to optimize memory usage
    - **Resource Pooling**: Efficient reuse of model instances across requests
    - **Streaming Support**: Foundation for streaming response implementations
    - **Metrics Collection**: Comprehensive performance tracking without overhead
    - **Memory Management**: Explicit cleanup patterns for large model weights

    ### Usage Patterns:
    ```python
    # Basic usage
    model = OllamaLanguageModel("llama3.2:3b")
    response = model.generate(messages, config)
    
    # With custom configuration
    config = LLMConfig(temperature=0.1, max_tokens=500)
    response = model.generate(messages, config)
    
    # Resource cleanup
    model.cleanup()
    ```

    ### Thread Safety:
    Implementations should be thread-safe for concurrent usage within the
    experiment framework. Instance variables should be immutable or properly
    synchronized for concurrent access.
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize language model with standardized infrastructure integration.
        
        Args:
            model_name: Name of the specific model to use
            **kwargs: Additional model-specific parameters
        """
        self.model_name = model_name
        self.kwargs = kwargs

        # Configure logging with contextual information
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_llm.llm.language_model",
            {CONTEXT_COMPONENT: f"LanguageModel-{model_name}"}
        )

        # Initialize error handler for error management
        self.error_handler = ErrorHandler.get_instance()

    @abstractmethod
    def generate(self,
                 messages: List[LLMMessage],
                 config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate a response synchronously.
        
        Args:
            messages: List of LLMMessage objects representing the conversation
            config: Optional configuration parameters
            
        Returns:
            LLMResponse containing the generated text and performance metrics
        """
        pass

    @abstractmethod
    def cleanup(self):
        """
        Clean up resources.

        Releases model resources, unloads model weights, and frees memory.
        This method should be called when the model is no longer needed to
        ensure proper resource management.
        """
        pass

    def _get_component_name(self) -> str:
        """
        Get the component name for error handling context.
        
        Returns:
            Component name including the actual subclass name
        """
        return f"LanguageModel.{self.__class__.__name__}"

    def _handle_generation_errors(self, func):
        """
        Decorator helper for subclasses to handle generation errors with correct component name.
        
        Usage in subclasses:
        ```python
        def generate(self, messages, config=None):
            @self._handle_generation_errors
            def _generate_impl():
                # Implementation here
                return response
            return _generate_impl()
        ```
        """
        return self.error_handler.handle_errors(
            component=self._get_component_name(),
            phase="response_generation"
        )(func)

    def _handle_cleanup_errors(self, func):
        """
        Decorator helper for subclasses to handle cleanup errors with correct component name.
        """
        return self.error_handler.handle_errors(
            component=self._get_component_name(),
            phase="resource_cleanup"
        )(func)

    @property
    def default_config(self) -> LLMConfig:
        """
        Returns the default configuration for this model.
        
        Returns:
            LLMConfig with default settings
        """
        return LLMConfig(
            llm_type=self.__class__.NAME,
            model=self.model_name,
            max_tokens=800,
            temperature=0.2
        )

    @classmethod
    def models(cls) -> List[str]:
        """
        Get a list of available models for this type.
        
        Returns:
            List of available model names
        """
        # Default implementation - subclasses should override
        return getattr(cls, "MODELS", [])
