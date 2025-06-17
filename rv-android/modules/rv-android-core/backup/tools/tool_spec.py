"""
Tool specification and metadata management.

This module provides utilities for tool specification parsing and metadata
handling in the monitored operations testing framework.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class ToolType(Enum):
    """Enumeration of supported tool types."""
    BUILTIN = "builtin"
    EXTERNAL = "external"
    PLUGIN = "plugin"
    GUI_TESTING = "gui_testing"
    MACHINE_LEARNING = "machine_learning"


class ToolCategory(Enum):
    """Enumeration of tool categories for monitored operations testing."""
    RANDOM_TESTING = "random_testing"
    MODEL_BASED = "model_based"
    AI_GUIDED = "ai_guided"
    SYSTEMATIC = "systematic"
    HYBRID = "hybrid"


@dataclass
class ToolSpec:
    """
    Specification and metadata for monitored operations testing tools.
    
    ### Architectural Decisions:
    - Provides structured metadata for tool discovery and management
    - Supports tool categorization and capability description
    - Enables version management and compatibility checking
    - Facilitates tool selection based on requirements
    
    ### Role in the System:
    - Describes tool capabilities and characteristics
    - Supports tool registry and discovery systems
    - Enables automated tool selection for experiments
    - Provides metadata for tool configuration and validation
    """
    
    name: str
    description: str
    version: str
    tool_type: ToolType
    category: ToolCategory
    process_pattern: Optional[str] = None
    dependencies: List[str] = None
    capabilities: List[str] = None
    configuration_schema: Dict[str, Any] = None
    author: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.dependencies is None:
            self.dependencies = []
        if self.capabilities is None:
            self.capabilities = []
        if self.configuration_schema is None:
            self.configuration_schema = {}
    
    @classmethod
    def create_builtin_spec(
        cls,
        name: str,
        description: str,
        category: ToolCategory,
        version: str = "1.0.0",
        process_pattern: Optional[str] = None,
        capabilities: List[str] = None
    ) -> "ToolSpec":
        """
        Create a specification for a built-in tool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            version: Tool version
            process_pattern: Process pattern for cleanup
            capabilities: List of tool capabilities
            
        Returns:
            ToolSpec instance for built-in tool
        """
        return cls(
            name=name,
            description=description,
            version=version,
            tool_type=ToolType.BUILTIN,
            category=category,
            process_pattern=process_pattern,
            capabilities=capabilities or []
        )
    
    @classmethod
    def create_external_spec(
        cls,
        name: str,
        description: str,
        category: ToolCategory,
        dependencies: List[str],
        version: str = "1.0.0",
        process_pattern: Optional[str] = None,
        capabilities: List[str] = None,
        author: Optional[str] = None
    ) -> "ToolSpec":
        """
        Create a specification for an external tool.
        
        Args:
            name: Tool name
            description: Tool description
            category: Tool category
            dependencies: List of required dependencies
            version: Tool version
            process_pattern: Process pattern for cleanup
            capabilities: List of tool capabilities
            author: Tool author
            
        Returns:
            ToolSpec instance for external tool
        """
        return cls(
            name=name,
            description=description,
            version=version,
            tool_type=ToolType.EXTERNAL,
            category=category,
            process_pattern=process_pattern,
            dependencies=dependencies,
            capabilities=capabilities or [],
            author=author
        )
    
    def has_capability(self, capability: str) -> bool:
        """
        Check if tool has specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            True if tool has the capability
        """
        return capability in self.capabilities
    
    def is_compatible_with(self, requirements: List[str]) -> bool:
        """
        Check if tool is compatible with given requirements.
        
        Args:
            requirements: List of required capabilities
            
        Returns:
            True if tool meets all requirements
        """
        return all(self.has_capability(req) for req in requirements)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert specification to dictionary representation.
        
        Returns:
            Dictionary representation of the tool specification
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tool_type": self.tool_type.value,
            "category": self.category.value,
            "process_pattern": self.process_pattern,
            "dependencies": self.dependencies,
            "capabilities": self.capabilities,
            "configuration_schema": self.configuration_schema,
            "author": self.author
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolSpec":
        """
        Create specification from dictionary representation.
        
        Args:
            data: Dictionary containing tool specification data
            
        Returns:
            ToolSpec instance created from dictionary
        """
        return cls(
            name=data["name"],
            description=data["description"],
            version=data["version"],
            tool_type=ToolType(data["tool_type"]),
            category=ToolCategory(data["category"]),
            process_pattern=data.get("process_pattern"),
            dependencies=data.get("dependencies", []),
            capabilities=data.get("capabilities", []),
            configuration_schema=data.get("configuration_schema", {}),
            author=data.get("author")
        )