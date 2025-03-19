from abc import ABC, abstractmethod
from typing import List, Dict


class LanguageModel(ABC):
    """
    An abstract base class defining the core interface for language model integrations in the RV-Android framework.

    ### Architectural Decisions:
    - Implements an abstract, provider-agnostic interface for language models
    - Defines a standardized contract for text generation across different AI providers
    - Enables flexible language model integration through a common abstraction
    - Supports multiple model types and generation strategies

    ### Role in the System:
    - Serves as the foundational abstraction for language model interactions
    - Provides a uniform interface for text generation across different AI backends
    - Enables easy swapping and integration of various language model implementations
    - Supports consistent method signatures for model generation and resource management
    - Acts as a critical component in AI-driven testing and analysis workflows

    ### Key Considerations:
    - Defines essential methods for text generation and resource cleanup
    - Supports flexible text generation with configurable parameters
    - Provides a mechanism for model-specific implementations
    - Enables standardized error handling and resource management
    - Supports runtime model selection and configuration

    ### Integration Strategy:
    - Compatible with multiple language model providers (Ollama, HuggingFace, OpenAI, etc.)
    - Supports dependency injection and factory-based model creation
    - Allows easy extension for new language model backends
    - Provides a consistent interface for model interaction across the framework
    - Facilitates seamless integration with prompt strategies and action generation

    ### Performance and Scalability:
    - Designed for minimal overhead in model generation (inference)
    - Supports various model sizes and complexity levels
    - Enables efficient resource management through cleanup methods
    - Adaptable to different computational resources and model constraints
    - Provides a flexible foundation for scaling AI-driven testing capabilities
    """

    def __init__(self, model_name: str):
        """
        Initialize the language model with a model name.

        Args:
            model_name: Name or identifier of the model
        """
        self.model_name = model_name

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generate text based on the given messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text response

        Raises:
            Exception: If text generation fails
        """
        pass

    @abstractmethod
    def clean(self) -> None:
        """
        Clean up resources used by the model.
        This should release memory, close connections, etc.
        """
        pass

    @staticmethod
    @abstractmethod
    def models() -> List[str]:
        """
        Returns a list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def __str__(self) -> str:
        """
        String representation of the language model.

        Returns:
            String representation
        """
        return f"{self.__class__.__name__}: {self.model_name}"
