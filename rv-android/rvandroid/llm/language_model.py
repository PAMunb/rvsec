# rvandroid/llm/language_model.py
"""Language Model interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from rvandroid.llm.adapter import MCPAdapter
from rvandroid.llm.data_structures import LLMMessage, LLMResponse
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class LanguageModel(ABC):
    """
    Base class for language model implementations.
    
    This abstract base class defines the standard interface for all language model
    implementations in the RV-Android system. All models must implement this interface
    to ensure consistent behavior and integration within the test framework.
    
    Key components:
    - Model-specific adapter selection
    - Standard configuration management
    - Consistent async and sync generation methods
    - Standardized error handling and logging
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize language model.
        
        Args:
            model_name: Name of the specific model to use
            **kwargs: Additional model-specific parameters
        """
        self.model_name = model_name
        self.adapter = self._get_adapter()
        self.kwargs = kwargs

        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.language_model",
            {CONTEXT_COMPONENT: "LanguageModel"}
        )

    @abstractmethod
    def _get_model_type(self) -> str:
        """
        Get model type string.
        
        Returns:
            String identifier for the model type
        """
        pass

    @abstractmethod
    def _get_adapter(self) -> MCPAdapter:
        """
        Get the appropriate MCP adapter for this model.
        
        Returns:
            MCPAdapter instance for this model type
        """
        pass

    @abstractmethod
    def generate(self,
                 messages: List[LLMMessage],
                 config: Optional[LLMConfiguration] = None) -> LLMResponse:
        """
        Generate a response synchronously.
        
        Args:
            messages: List of MCP messages representing the conversation
            config: Optional configuration parameters
            
        Returns:
            LLMMessage containing the generated response
        """
        pass

    @classmethod
    def models(cls) -> List[str]:
        """
        Get a list of available models for this type.
        
        Returns:
            List of available model names
        """
        # Default implementation - subclasses should override
        return getattr(cls, "MODELS", [])
