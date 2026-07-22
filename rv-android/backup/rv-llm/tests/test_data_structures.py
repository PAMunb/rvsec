"""
Basic tests for LLM data structures.

Simple test to verify core data structures work correctly.
"""

import pytest
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent, LLMResponse


class TestLLMDataStructures:
    """Test core LLM data structures."""

    def test_llm_text_content_creation(self):
        """Test creating LLMTextContent."""
        content = LLMTextContent(text="Hello, world!")
        assert content.text == "Hello, world!"
        assert str(content) == "Hello, world!"

    def test_llm_message_creation(self):
        """Test creating LLMMessage with text content."""
        text_content = LLMTextContent(text="Test message")
        message = LLMMessage(role=LLMRole.USER, content=[text_content])
        
        assert message.role == LLMRole.USER
        assert len(message.content) == 1
        assert message.get_text_content() == "Test message"
        assert message.total_chars() == 12

    def test_llm_response_creation(self):
        """Test creating LLMResponse."""
        response = LLMResponse(content="Generated response")
        
        assert response.content == "Generated response"
        assert response.role == LLMRole.ASSISTANT
        assert response.done is True
        assert response.total_chars() == 18

    def test_llm_role_enum(self):
        """Test LLMRole enum values."""
        assert LLMRole.SYSTEM.value == "system"
        assert LLMRole.USER.value == "user"
        assert LLMRole.ASSISTANT.value == "assistant"
        assert LLMRole.TOOL.value == "tool"