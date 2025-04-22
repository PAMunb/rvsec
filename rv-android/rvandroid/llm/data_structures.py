# rvandroid/llm/data_structures.py
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
    """
    Standard message format for Model Context Protocol.
    
    Represents a structured message in a conversation between the system,
    user, assistant, or tools. Messages can contain multiple content items
    of different types (text, images, etc.).
    """
    role: MCPRole
    content: List[MCPContentType]
    name: Optional[str] = None
    # TODO deprecated
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    def total_chars(self):
        cont = 0
        for item in self.content:
            if isinstance(item, MCPTextContent):
                cont += len(item.text)
        return cont

    def __str__(self):
        return f"MCPMessage(role={self.role}, content={self.content})"

    # # TODO deprecated
    # def to_dict(self) -> Dict[str, Any]:
    #     """
    #     Convert message to dictionary representation.
    #
    #     Returns:
    #         Dictionary representation of the message
    #     """
    #     content_list = []
    #     for item in self.content:
    #         if isinstance(item, MCPTextContent):
    #             content_list.append({"type": "text", "text": item.text})
    #         elif isinstance(item, MCPImageContent):
    #             content_list.append({"type": "image", "url": item.url, "detail": item.detail})
    #
    #     result = {
    #         "role": self.role.value,
    #         "content": content_list
    #     }
    #
    #     if self.name:
    #         result["name"] = self.name
    #     if self.tool_calls:
    #         result["tool_calls"] = self.tool_calls
    #     if self.tool_call_id:
    #         result["tool_call_id"] = self.tool_call_id
    #
    #     return result
    #
    # # TODO deprecated
    # @classmethod
    # def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
    #     """
    #     Create message from dictionary representation.
    #
    #     Args:
    #         data: Dictionary containing message data
    #
    #     Returns:
    #         MCPMessage instance
    #     """
    #     role = MCPRole(data["role"])
    #
    #     # Process content
    #     content = []
    #     raw_content = data.get("content", [])
    #
    #     # Handle string content for backward compatibility
    #     if isinstance(raw_content, str):
    #         content = [MCPTextContent(text=raw_content)]
    #     else:
    #         for item in raw_content:
    #             if isinstance(item, str):
    #                 content.append(MCPTextContent(text=item))
    #             elif isinstance(item, dict):
    #                 if item.get("type") == "text":
    #                     content.append(MCPTextContent(text=item.get("text", "")))
    #                 elif item.get("type") == "image":
    #                     content.append(MCPImageContent(
    #                         url=item.get("url", ""),
    #                         detail=item.get("detail", "auto")
    #                     ))
    #
    #     return cls(
    #         role=role,
    #         content=content,
    #         name=data.get("name"),
    #         tool_calls=data.get("tool_calls"),
    #         tool_call_id=data.get("tool_call_id")
    #     )

    def get_text_content(self) -> str:
        """
        Get combined text content from the message.
        
        Returns:
            String combining all text content items
        """
        text_parts = []
        for item in self.content:
            if isinstance(item, MCPTextContent):
                text_parts.append(item.text)
        return "\n".join(text_parts)


@dataclass
class MCPAction:
    id: int
    params: Dict[str, Any]
    explanation: Optional[str] = None


@dataclass
class MCPResponse:
    # actions: List[MCPAction]
    content: str
    role = MCPRole.ASSISTANT
    done = True
    done_reason = "stop"
    total_duration = 0
    load_duration = 0
    prompt_eval_count = 0
    prompt_eval_duration = 0
    eval_count = 0
    eval_duration = 0

    def total_chars(self):
        return len(self.content)

# deprecated
# @dataclass
# class MCPConfiguration_OLD:
#     """
#     Configuration parameters for language models using MCP.
#
#     Provides a standardized set of parameters for controlling
#     language model behavior, regardless of the specific model
#     implementation.
#     """
#     temperature: float = 0.7
#     max_tokens: Optional[int] = None
#     top_p: float = 1.0
#     frequency_penalty: float = 0.0
#     presence_penalty: float = 0.0
#     stop: Optional[List[str]] = None
#     model_type: str = "ollama"
#     model_name: str = "llama3.2:3b"
#
#     def to_dict(self) -> Dict[str, Any]:
#         """
#         Convert configuration to dictionary.
#
#         Returns:
#             Dictionary representation of configuration
#         """
#         return {
#             "temperature": self.temperature,
#             "max_tokens": self.max_tokens,
#             "top_p": self.top_p,
#             "frequency_penalty": self.frequency_penalty,
#             "presence_penalty": self.presence_penalty,
#             "stop": self.stop,
#             "model_type": self.model_type,
#             "model_name": self.model_name
#         }
#
#     @classmethod
#     def from_dict(cls, data: Dict[str, Any]) -> 'MCPConfiguration':
#         """
#         Create configuration from dictionary.
#
#         Args:
#             data: Dictionary containing configuration data
#
#         Returns:
#             MCPConfiguration instance
#         """
#         return cls(
#             temperature=data.get("temperature", 0.7),
#             max_tokens=data.get("max_tokens"),
#             top_p=data.get("top_p", 1.0),
#             frequency_penalty=data.get("frequency_penalty", 0.0),
#             presence_penalty=data.get("presence_penalty", 0.0),
#             stop=data.get("stop"),
#             model_type=data.get("model_type", "ollama"),
#             model_name=data.get("model_name", "llama3.2:3b")
#         )