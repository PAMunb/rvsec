# rvandroid/mcp/mcp_data_structures.py
"""Core data structures for the Model Context Protocol (MCP)."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Union


class MCPRole(Enum):
    """Role of a message in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class MCPTextContent:
    """Text content in an MCP message."""
    text: str


@dataclass
class MCPImageContent:
    """Image content in an MCP message."""
    url: str
    detail: Optional[str] = "auto"


# Union type for different content types
MCPContentType = Union[MCPTextContent, MCPImageContent]


@dataclass
class MCPMessage:
    """Standard message format for MCP."""
    role: MCPRole
    content: List[MCPContentType]
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary representation."""
        content_list = []
        for item in self.content:
            if isinstance(item, MCPTextContent):
                content_list.append({"type": "text", "text": item.text})
            elif isinstance(item, MCPImageContent):
                content_list.append({"type": "image", "url": item.url, "detail": item.detail})

        result = {
            "role": self.role.value,
            "content": content_list
        }

        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Create message from dictionary representation."""
        role = MCPRole(data["role"])

        # Process content
        content = []
        raw_content = data.get("content", [])

        # Handle string content for backward compatibility
        if isinstance(raw_content, str):
            content = [MCPTextContent(text=raw_content)]
        else:
            for item in raw_content:
                if isinstance(item, str):
                    content.append(MCPTextContent(text=item))
                elif isinstance(item, dict):
                    if item.get("type") == "text":
                        content.append(MCPTextContent(text=item.get("text", "")))
                    elif item.get("type") == "image":
                        content.append(MCPImageContent(
                            url=item.get("url", ""),
                            detail=item.get("detail", "auto")
                        ))

        return cls(
            role=role,
            content=content,
            name=data.get("name"),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id")
        )

    def get_text_content(self) -> str:
        """Get combined text content from the message."""
        text_parts = []
        for item in self.content:
            if isinstance(item, MCPTextContent):
                text_parts.append(item.text)
        return "\n".join(text_parts)


@dataclass
class MCPConfiguration:
    """Configuration parameters for language models."""
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    model_type: str = "ollama"
    model_name: str = "llama3.2:3b"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "stop": self.stop,
            "model_type": self.model_type,
            "model_name": self.model_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPConfiguration':
        """Create configuration from dictionary."""
        return cls(
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            top_p=data.get("top_p", 1.0),
            frequency_penalty=data.get("frequency_penalty", 0.0),
            presence_penalty=data.get("presence_penalty", 0.0),
            stop=data.get("stop"),
            model_type=data.get("model_type", "ollama"),
            model_name=data.get("model_name", "llama3.2:3b")
        )
