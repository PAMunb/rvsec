"""
Core data structures for Language Model integration.

This module defines standardized data structures used throughout the LLM
integration system, providing type-safe representations for messages, content,
and responses in the Model Context Protocol (MCP) format.
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union

from pydantic import Field, field_validator

from rv_android_core.util.validation import BaseValidatedModel


class LLMRole(Enum):
    """Role of a message in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMTextContent(BaseValidatedModel):
    """
    Text content in an LLM message.
    
    ### Architectural Overview:
    This class encapsulates text-based content for LLM conversations,
    providing type safety and validation for text message components.
    
    ### Role in the System:
    - Primary content type for text-based LLM interactions
    - Provides string representation and validation
    - Supports serialization for API communication
    """
    text: str = Field(description="Text content of the message")

    def __str__(self) -> str:
        return self.text


class LLMImageContent(BaseValidatedModel):
    """
    Image content in an LLM message.
    
    ### Architectural Overview:
    This class encapsulates image-based content for multimodal LLM conversations
    
    ### Role in the System:
    - Handles image content for multimodal LLM interactions
    - Provides URL-based image reference system
    """
    url: str = Field(description="URL or path to the image")
    encoded_string: str = Field(description="Encoded string representation of the image")

    def __str__(self) -> str:
        return self.url


# Union type for different content types
LLMContentType = Union[LLMTextContent, LLMImageContent]


class LLMMessage(BaseValidatedModel):
    """
    Standard message format for Model Context Protocol.
    
    ### Architectural Overview:
    Represents a structured message in a conversation between the system,
    user, assistant, or tools. Messages can contain multiple content items
    of different types (text, images, etc.).
    
    ### Role in the System:
    - Primary communication structure for LLM interactions
    - Supports multimodal content (text and images)
    - Provides conversation context and role management
    - Handles serialization for API communication
    
    ### Key Features:
    - **Role Management**: Clear distinction between system, user, assistant, and tool messages
    - **Multimodal Support**: Text and image content in single messages
    - **Validation**: Automatic validation of message structure and content
    - **Serialization**: API-compatible message format generation
    """
    role: LLMRole = Field(description="Role of the message sender")
    content: List[LLMContentType] = Field(description="List of content items")
    name: Optional[str] = Field(default=None, description="Name of the message sender")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Tool calls (deprecated)")
    tool_call_id: Optional[str] = Field(default=None, description="Tool call ID (deprecated)")

    @field_validator('content')
    @classmethod
    def validate_content_not_empty(cls, v: List[LLMContentType]) -> List[LLMContentType]:
        """Validate that content list is not empty."""
        if not v:
            raise ValueError("content list cannot be empty")
        return v

    def total_chars(self) -> int:
        """
        Calculate total character count for text content.
        
        Returns:
            Total number of characters in text content
        """
        total = 0
        for item in self.content:
            if isinstance(item, LLMTextContent):
                total += len(item.text)
        return total

    def __str__(self) -> str:
        return f"LLMMessage(role={self.role}, content={self.content})"

    def get_text_content(self) -> str:
        """
        Get combined text content from the message.
        
        Returns:
            String combining all text content items
        """
        text_parts = []
        for item in self.content:
            if isinstance(item, LLMTextContent):
                text_parts.append(item.text)
        return "\n".join(text_parts)

    def get_image_content(self) -> List[str]:
        """
        Get image content items from the message.

        Returns:
            List of LLMImageContent objects
        """
        return [item.encoded_string for item in self.content if isinstance(item, LLMImageContent)]

    # def to_message_dict(self) -> Dict[str, Any]:
    #     """
    #     Convert message to API-compatible dictionary format.
    #
    #     ### Serialization Strategy:
    #     Creates a dictionary structure compatible with standard LLM APIs,
    #     handling both text and image content appropriately.
    #
    #     Returns:
    #         Dictionary representation for API communication
    #     """
    #     items = []
    #
    #     # Add text content
    #     text_content = self.get_text_content()
    #     if text_content:
    #         items.append({
    #             "type": "text",
    #             "text": text_content
    #         })
    #
    #     # Add image content
    #     for item in self.content:
    #         if isinstance(item, LLMImageContent):
    #             items.append({
    #                 "type": "image",
    #                 "url": item.url
    #             })
    #
    #     return {
    #         "role": self.role.value,
    #         "content": items
    #     }


class LLMResponse(BaseValidatedModel):
    """
    LLM response data structure with performance diagnostics.
    
    ### Architectural Overview:
    This class captures comprehensive information about LLM responses,
    including generated content and detailed performance metrics for
    monitoring and optimization purposes.
    
    ### Performance Metrics:
    - **content**: The generated text response from the model
    - **done_reason**: Explanation for generation termination
    - **total_duration**: Complete request-to-response time
    - **load_duration**: Model loading time (cold start detection)
    - **input_tokens**: Input prompt token count for cost estimation
    - **input_tokens_duration**: Prompt processing time
    - **output_tokens**: Generated response token count
    - **output_tokens_duration**: Token generation time (inference speed)
    
    ### Role in the System:
    - Standardized response format across all LLM providers
    - Performance monitoring and metrics collection
    - Cost estimation and resource usage tracking
    - Response quality and completion status reporting
    """
    content: str = Field(description="Generated response content")
    role: LLMRole = Field(default=LLMRole.ASSISTANT, description="Response role")
    done: bool = Field(default=True, description="Whether generation is complete")
    done_reason: str = Field(default="stop", description="Reason for generation completion")
    total_duration: int = Field(default=0, ge=0, description="Total request duration in milliseconds")
    load_duration: int = Field(default=0, ge=0, description="Model loading duration in milliseconds")
    input_tokens: int = Field(default=0, ge=0, description="Number of input tokens processed")
    input_tokens_duration: int = Field(default=0, ge=0, description="Input processing duration in milliseconds")
    output_tokens: int = Field(default=0, ge=0, description="Number of output tokens generated")
    output_tokens_duration: int = Field(default=0, ge=0, description="Output generation duration in milliseconds")

    # @field_validator('done_reason')
    # @classmethod
    # def validate_done_reason(cls, v: str) -> str:
    #     """Validate completion reason."""
    #     valid_reasons = {"stop", "length", "error", "interrupted", "timeout", "false"}
    #     if v not in valid_reasons:
    #         # Allow other reasons but log a warning
    #         pass
    #     return v

    def total_chars(self) -> int:
        """
        Calculate total character count in response content.
        
        Returns:
            Number of characters in the response content
        """
        return len(self.content)

    def get_tokens_per_second(self) -> float:
        """
        Calculate output tokens generation rate.
        
        Returns:
            Tokens per second generation rate, or 0 if duration is 0
        """
        if self.output_tokens_duration > 0:
            return (self.output_tokens * 1000.0) / self.output_tokens_duration
        return 0.0

    def get_total_tokens(self) -> int:
        """
        Get total token count (input + output).
        
        Returns:
            Sum of input and output tokens
        """
        return self.input_tokens + self.output_tokens

    def to_performance_dict(self) -> Dict[str, Any]:
        """
        Extract performance metrics as dictionary.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            "total_duration": self.total_duration,
            "load_duration": self.load_duration,
            "input_tokens": self.input_tokens,
            "input_tokens_duration": self.input_tokens_duration,
            "output_tokens": self.output_tokens,
            "output_tokens_duration": self.output_tokens_duration,
            "tokens_per_second": self.get_tokens_per_second(),
            "total_tokens": self.get_total_tokens(),
            "done_reason": self.done_reason
        }
