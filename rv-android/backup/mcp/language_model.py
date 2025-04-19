# rvandroid/mcp/language_model.py
"""MCP-based Language Model interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type
import logging

from rvandroid.mcp.mcp_data_structures import MCPMessage, MCPConfiguration
from rvandroid.mcp.mcp_adapter import MCPAdapter, AdapterRegistry


class LanguageModel(ABC):
    """Base class for language model implementations using MCP."""

    def __init__(self, model_name: str, **kwargs):
        """Initialize language model."""
        self.model_name = model_name
        self.adapter = self._get_adapter()
        self.config = MCPConfiguration(
            model_name=model_name,
            model_type=self._get_model_type()
        )

        # Update config with kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def _get_model_type(self) -> str:
        """Get model type string."""
        pass

    @abstractmethod
    def _get_adapter(self) -> MCPAdapter:
        """Get the appropriate MCP adapter for this model."""
        pass

    @abstractmethod
    async def generate(self,
                       messages: List[MCPMessage],
                       config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response using the language model."""
        pass

    @abstractmethod
    def generate_sync(self,
                      messages: List[MCPMessage],
                      config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response synchronously."""
        pass


class ModelFactory:
    """Factory for creating language model instances."""

    _model_registry: Dict[str, Type[LanguageModel]] = {}

    @classmethod
    def register_model(cls, model_type: str, model_class: Type[LanguageModel]) -> None:
        """Register a model class for a model type."""
        cls._model_registry[model_type] = model_class

    @classmethod
    def create(cls, model_type: str, model_name: str, **kwargs) -> LanguageModel:
        """Create a language model instance."""
        if model_type not in cls._model_registry:
            raise ValueError(f"Unknown model type: {model_type}")

        model_class = cls._model_registry[model_type]
        return model_class(model_name, **kwargs)
