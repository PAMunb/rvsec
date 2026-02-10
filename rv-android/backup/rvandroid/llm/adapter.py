# rvandroid/llm/adapter.py


from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, Optional
import logging

from rvandroid.llm.data_structures import LLMMessage
from rvandroid.util.error.error_handler import ErrorHandler


class MCPAdapter(ABC):
    """
    Abstract base adapter for converting between LLM and model-specific formats.
    
    The adapter pattern provides a standardized interface for communicating with
    different language model APIs. Each model type has its own adapter implementation
    that handles the conversion between the LLM format and the model-specific format.
    
    This abstraction enables the system to work with multiple model providers while
    maintaining a consistent interface for message handling and configuration.
    """

    def __init__(self):
        """Initialize the adapter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.error_handler = ErrorHandler.get_instance()

    @abstractmethod
    def prepare_messages(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """
        Convert LLM messages to model-specific format.
        
        Args:
            messages: List of messages representing the conversation
            
        Returns:
            Model-specific message format
        """
        pass

    @abstractmethod
    def parse_response(self, response: Any) -> LLMMessage:
        """
        Parse model response into MCP message.
        
        Args:
            response: Raw response from the model
            
        Returns:
            Parsed response as an LLMMessage
        """
        pass

    # @abstractmethod
    # def validate_request(self, messages: List[LLMMessage], config: MCPConfiguration) -> bool:
    #     """
    #     Validate that messages and config are compatible with this adapter.
    #
    #     Args:
    #         messages: List of MCP messages to validate
    #         config: Configuration parameters to validate
    #
    #     Returns:
    #         True if the request is valid, False otherwise
    #     """
    #     pass


class AdapterRegistry:
    """
    Registry for MCP adapters.
    
    Provides a centralized registry for adapter classes, enabling dynamic
    discovery and instantiation of appropriate adapters for different model types.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        Get singleton instance.
        
        Returns:
            AdapterRegistry singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize adapter registry."""
        self.adapters: Dict[str, Type[MCPAdapter]] = {}
        self.logger = logging.getLogger(__name__)

    def register_adapter(self, model_type: str, adapter_class: Type[MCPAdapter]) -> None:
        """
        Register an adapter for a model type.
        
        Args:
            model_type: Type of model this adapter supports
            adapter_class: Adapter class to register
        """
        self.adapters[model_type] = adapter_class
        self.logger.debug(f"Registered adapter for {model_type}: {adapter_class.__name__}")

    def get_adapter(self, model_type: str) -> Optional[Type[MCPAdapter]]:
        """
        Get adapter class for a model type.
        
        Args:
            model_type: Type of model to get adapter for
            
        Returns:
            Adapter class or None if not found
        """
        return self.adapters.get(model_type)

    def create_adapter(self, model_type: str) -> Optional[MCPAdapter]:
        """
        Create adapter instance for a model type.
        
        Args:
            model_type: Type of model to create adapter for
            
        Returns:
            Adapter instance or None if not found
        """
        adapter_class = self.get_adapter(model_type)
        if adapter_class:
            return adapter_class()
        
        self.logger.warning(f"No adapter registered for model type: {model_type}")
        return None
        
    def get_available_types(self) -> List[str]:
        """
        Get a list of available model types with registered adapters.
        
        Returns:
            List of model type names
        """
        return list(self.adapters.keys())