"""
Tool specification and metadata management.

This module provides simplified tool specification handling for monitored 
operations testing framework, focusing on essential metadata only.
"""

from typing import Dict, Any, Optional
from pydantic import Field

from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(['name', 'description', 'url', 'version'])
class ToolSpec(BaseValidatedModel):
    """
    Simplified specification for monitored operations testing tools.
    
    ### Architectural Decisions:
    - Focuses on essential metadata only (name, description, url, version, process_pattern)
    - Removed complex categorization and capability systems
    - Maintains compatibility with existing tool registration systems
    - Supports tool discovery and basic configuration
    
    ### Role in the System:
    - Describes basic tool identification and metadata
    - Supports tool registry and discovery systems
    - Provides information for tool execution and cleanup
    - Maintains version tracking for compatibility
    """
    
    name: str = Field(
        description="Tool name for identification and registry"
    )
    description: str = Field(
        description="Detailed description of tool capabilities and purpose"
    )
    url: str = Field(
        description="Tool repository, documentation, or download URL"
    )
    version: str = Field(
        description="Tool version string for compatibility tracking"
    )
    process_pattern: Optional[str] = Field(
        default=None,
        description="Process pattern for tool cleanup and management"
    )
    
    @classmethod
    def create_builtin_spec(
        cls,
        name: str,
        description: str,
        url: str,
        version: str = "1.0.0",
        process_pattern: Optional[str] = None
    ) -> "ToolSpec":
        """
        Create a specification for a built-in tool.
        
        Args:
            name: Tool name
            description: Tool description
            url: Tool URL (repository, documentation, etc.)
            version: Tool version
            process_pattern: Process pattern for cleanup
            
        Returns:
            ToolSpec instance for built-in tool
        """
        return cls(
            name=name,
            description=description,
            url=url,
            version=version,
            process_pattern=process_pattern
        )
    
    @classmethod
    def create_external_spec(
        cls,
        name: str,
        description: str,
        url: str,
        version: str = "1.0.0",
        process_pattern: Optional[str] = None
    ) -> "ToolSpec":
        """
        Create a specification for an external tool.
        
        Args:
            name: Tool name
            description: Tool description
            url: Tool URL (repository, documentation, etc.)
            version: Tool version
            process_pattern: Process pattern for cleanup
            
        Returns:
            ToolSpec instance for external tool
        """
        return cls(
            name=name,
            description=description,
            url=url,
            version=version,
            process_pattern=process_pattern
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert specification to dictionary representation.
        
        Returns:
            Dictionary representation of the tool specification
        """
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "process_pattern": self.process_pattern
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
            url=data["url"],
            version=data["version"],
            process_pattern=data.get("process_pattern")
        )