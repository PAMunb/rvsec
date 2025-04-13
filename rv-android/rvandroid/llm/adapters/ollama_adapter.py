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
        Convert MCP messages to Ollama format.
        
        Ollama uses a specific prompt format with special tokens to
        delimit different message roles and parts of the conversation.
        
        Args:
            messages: List of MCP messages to convert
            
        Returns:
            Dictionary with "prompt" key containing formatted prompt string
        """
        # Ollama uses a simple prompt format
        prompt = ""

        for message in messages:
            role_str = message.role.value.capitalize()
            content = message.get_text_content()

            # Format based on role
            if message.role == MCPRole.SYSTEM:
                prompt += f"<s>[INST] <<SYS>>\n{content}\n<</SYS>>\n\n"
            elif message.role == MCPRole.USER:
                if prompt:  # Not the first message
                    prompt += f"{content} [/INST]"
                else:
                    prompt += f"<s>[INST] {content} [/INST]"
            elif message.role == MCPRole.ASSISTANT:
                prompt += f" {content} </s><s>[INST] "

        # Complete the final formatting if needed
        if not prompt.endswith("[/INST] "):
            prompt += " [/INST] "

        return {"prompt": prompt}

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
        
        Handles different possible response formats from Ollama
        and converts them to a standardized MCP message.
        
        Args:
            response: Response from Ollama API
            
        Returns:
            MCPMessage with parsed response
        """
        if isinstance(response, dict):
            text = response.get("response", "")
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