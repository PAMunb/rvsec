# rvandroid/llm/adapters/ollama_adapter.py
"""MCP adapter for Ollama models."""

import json
from typing import Dict, Any, List

from rvandroid.llm.adapter import MCPAdapter
from rvandroid.llm.data_structures import MCPMessage, MCPConfiguration, MCPRole, MCPTextContent


class OllamaAdapter(MCPAdapter):
    """
    Adapter for Ollama language models.
    
    Converts between MCP messages and Ollama-specific formats.
    Handles the specific formatting requirements of Ollama models,
    including chat formatting, system prompts, and configuration
    parameters.
    """

    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """
        Convert MCP messages to Ollama format for chat API.
        
        This updated implementation formats messages for Ollama's chat API
        instead of the generate API, letting Ollama handle message formatting.
        
        Args:
            messages: List of MCP messages to convert
            
        Returns:
            Dictionary with "messages" key containing formatted message objects
        """
        ollama_messages = []
        
        for message in messages:
            content = message.get_text_content()
            
            ollama_messages.append({
                "role": message.role.value,
                "content": content
            })
            
        return {"messages": ollama_messages}

    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """
        Convert MCP configuration to Ollama parameters.
        
        Maps standardized MCP configuration parameters to
        Ollama-specific API parameters.
        
        Args:
            config: MCP configuration to convert
            
        Returns:
            Dictionary with Ollama-specific configuration
        """
        ollama_config = {
            "model": config.model_name,
            "temperature": config.temperature,
        }

        if config.max_tokens:
            ollama_config["num_predict"] = config.max_tokens

        if config.top_p < 1.0:
            ollama_config["top_p"] = config.top_p

        return ollama_config

    def parse_response(self, response: Any) -> MCPMessage:
        """
        Parse Ollama response into MCP message.
        
        Updated to handle both generate and chat API response formats.
        
        Args:
            response: Response from Ollama API
            
        Returns:
            MCPMessage with parsed response
        """
        if isinstance(response, dict):
            # Handle chat API format
            if "message" in response:
                content = response.get("message", {}).get("content", "")
                return MCPMessage(
                    role=MCPRole.ASSISTANT,
                    content=[MCPTextContent(text=content)]
                )
            # Handle generate API format (legacy)
            elif "response" in response:
                text = response.get("response", "")
            else:
                text = str(response)
        elif isinstance(response, str):
            text = response
        else:
            text = str(response)
            
        return MCPMessage(
            role=MCPRole.ASSISTANT,
            content=[MCPTextContent(text=text)]
        )

    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """
        Validate that messages and config are compatible with Ollama.
        
        Checks for incompatible features or configurations that
        would cause errors with Ollama models.
        
        Args:
            messages: MCP messages to validate
            config: Configuration to validate
            
        Returns:
            True if the request is valid for Ollama, False otherwise
        """
        # Basic validation
        if not messages:
            self.logger.warning("Empty message list")
            return False

        # Check for unsupported content types
        for message in messages:
            for content in message.content:
                if not isinstance(content, MCPTextContent):
                    self.logger.warning(f"Ollama does not support content type: {type(content)}")
                    return False

        return True