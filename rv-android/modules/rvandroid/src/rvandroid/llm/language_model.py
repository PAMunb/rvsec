# rvandroid/llm/language_model.py
"""Language Model interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.llm.data_structures import LLMMessage, LLMResponse
from rv_android_core.llm.llm_config import LLMConfiguration


class LanguageModel(ABC):
    """
    Base class for language model implementations.
    
    ### Architectural Decisions:
    - Defines a standardized interface for all language models
    - Provides consistent configuration and execution patterns
    - Implements unified error handling and performance tracking
    - Ensures consistent logging and monitoring capabilities
    - Enables interchangeable language model implementations
    
    ### Role in the System:
    - Acts as the central abstraction for all LLM integrations
    - Enables consistent interaction with diverse language models
    - Provides a unified API for prompt generation and response handling
    - Standardizes configuration and performance monitoring
    - Ensures clean separation between model specifics and system interface
    
    ### Key Considerations:
    - Balances flexibility and standardization for diverse models
    - Focuses on resource efficiency and prompt generation consistency
    - Implements robust error handling and resource cleanup
    - Provides standardized metrics collection for performance analysis
    - Enables easy extension with new model implementations
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize language model.
        
        Args:
            model_name: Name of the specific model to use
            **kwargs: Additional model-specific parameters
        """
        self.model_name = model_name
        self.kwargs = kwargs

        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.language_model",
            {CONTEXT_COMPONENT: "LanguageModel"}
        )

    @abstractmethod
    def generate(self,
                 messages: List[LLMMessage],
                 config: Optional[LLMConfiguration] = None) -> LLMResponse:
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

    @property
    def default_config(self) -> LLMConfiguration:
        """
        Returns the default configuration for this model.
        
        Returns:
            LLMConfiguration with default settings
        """
        return LLMConfiguration(
            model_type=self.__class__.NAME,
            model_name=self.model_name,
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
