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

    def __init__(self, config: LLMConfig):
        """
        Initialize language model with standardized infrastructure integration.
        
        Args:
            config: LLMConfig object containing model-specific parameters
        """
        self.config = config

        # Configure logging with contextual information
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("rv_llm.llm.language_model")

        # Initialize error handler for error management
        self.error_handler = ErrorHandler.get_instance()

    @abstractmethod
    def generate(self, messages: List[LLMMessage], config: Optional[LLMConfig] = None) -> LLMResponse:
        """
        Generate a response synchronously.
        
        Args:
            messages: List of LLMMessage objects representing the conversation
            config: optional LLMConfig object
            
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

    def supports_multimodal(self) -> bool:
        """
        Check if this language model supports multimodal input (text + images).
        
        ### Multimodal Support Detection Strategy:
        - Checks if model configuration enables vision capabilities
        - Provides base implementation for multimodal capability detection
        - Can be overridden by subclasses for provider-specific detection
        
        Returns:
            True if model supports text and image input, False otherwise
        """
        return hasattr(self.config, 'vision') and self.config.vision

    def extract_image_data_for_provider(self, messages: List[LLMMessage]) -> List[str]:
        """
        Extract encoded image data from messages for provider-specific formatting.
        
        ### Image Extraction Strategy:
        - Iterates through all messages to find image content
        - Extracts base64 encoded image strings for LLM transmission
        - Provides standardized image data extraction across providers
        - Returns empty list if no images found or multimodal not supported
        
        Args:
            messages: List of LLMMessage objects potentially containing images
            
        Returns:
            List of base64 encoded image strings ready for provider APIs
        """
        if not self.supports_multimodal():
            return []
        
        image_data = []
        for message in messages:
            images = message.get_image_content()
            if images:
                image_data.extend(images)
        
        return image_data

    def format_message_with_multimodal_support(self, message: LLMMessage, provider_format: str = "ollama") -> dict:
        """
        Format a message with multimodal content for provider-specific APIs.
        
        ### Provider Format Support:
        - "ollama": Ollama API format with "images" field
        - "anthropic": Anthropic Claude format with content array
        - "openai": OpenAI GPT-4 Vision format
        - "huggingface": Hugging Face transformers format
        
        ### Multimodal Message Formatting Strategy:
        - Extracts text content from message
        - Adds image content in provider-specific format
        - Maintains message role information
        - Provides fallback for text-only content
        
        Args:
            message: LLMMessage object with potential multimodal content
            provider_format: Target provider format specification
            
        Returns:
            Dictionary formatted for specific provider API
        """
        base_formatted = {
            "role": message.role.value,
            "content": message.get_text_content()
        }
        
        # Add images if this is a user message and multimodal is supported
        if message.role.value == "user" and self.supports_multimodal():
            images = message.get_image_content()
            if images:
                if provider_format.lower() == "ollama":
                    base_formatted["images"] = images
                elif provider_format.lower() == "anthropic":
                    # Anthropic Claude format: content is array of text and image objects
                    content_array = [{"type": "text", "text": message.get_text_content()}]
                    for img in images:
                        content_array.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img
                            }
                        })
                    base_formatted["content"] = content_array
                elif provider_format.lower() == "openai":
                    # OpenAI GPT-4 Vision format: content is array with text and image_url
                    content_array = [{"type": "text", "text": message.get_text_content()}]
                    for img in images:
                        content_array.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img}"
                            }
                        })
                    base_formatted["content"] = content_array
                elif provider_format.lower() == "huggingface":
                    # Hugging Face format: separate images field
                    base_formatted["images"] = images
        
        return base_formatted
