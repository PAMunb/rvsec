# rvandroid/mcp/mcp_adapter.py
"""Model Context Protocol (MCP) Adapter Framework."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, Optional
import logging

from rvandroid.mcp.mcp_data_structures import MCPMessage, MCPConfiguration


class MCPAdapter(ABC):
    """Abstract base adapter for converting between MCP and model-specific formats."""

    def __init__(self):
        """Initialize the adapter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """Convert MCP messages to model-specific format."""
        pass

    @abstractmethod
    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """Convert MCP configuration to model-specific parameters."""
        pass

    @abstractmethod
    def parse_response(self, response: Any) -> MCPMessage:
        """Parse model response into MCP message."""
        pass

    @abstractmethod
    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """Validate that messages and config are compatible with this adapter."""
        pass


class AdapterRegistry:
    """Registry for MCP adapters."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize adapter registry."""
        self.adapters: Dict[str, Type[MCPAdapter]] = {}
        self.logger = logging.getLogger(__name__)

    def register_adapter(self, model_type: str, adapter_class: Type[MCPAdapter]) -> None:
        """Register an adapter for a model type."""
        self.adapters[model_type] = adapter_class
        self.logger.debug(f"Registered adapter for {model_type}: {adapter_class.__name__}")

    def get_adapter(self, model_type: str) -> Optional[Type[MCPAdapter]]:
        """Get adapter class for a model type."""
        return self.adapters.get(model_type)

    def create_adapter(self, model_type: str) -> Optional[MCPAdapter]:
        """Create adapter instance for a model type."""
        adapter_class = self.get_adapter(model_type)
        if adapter_class:
            return adapter_class()
        return None
