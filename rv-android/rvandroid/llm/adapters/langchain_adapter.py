# rvandroid/llm/adapters/langchain_adapter.py
"""MCP adapter for Langchain models."""

from typing import Dict, Any, List

from rvandroid.llm.data_structures import MCPMessage, MCPConfiguration, MCPRole, MCPTextContent
from rvandroid.llm.adapter import MCPAdapter


class LangchainAdapter(MCPAdapter):
    """Adapter for Langchain models."""

    def __init__(self):
        """Initialize the Langchain adapter."""
        super().__init__()

    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """Convert MCP messages to Langchain format."""
        # Langchain with Ollama doesn't use message structure directly, 
        # but rather combines all messages into a single prompt
        system_content = ""
        user_content = ""
        
        # Extract system and user messages
        for message in messages:
            content = message.get_text_content()
            
            if message.role == MCPRole.SYSTEM:
                system_content = content
            elif message.role == MCPRole.USER:
                user_content = content
                
        # Combine them in a format Langchain can use
        combined_prompt = f"{system_content}\n\n{user_content}" if system_content else user_content
        
        return {"prompt": combined_prompt}

    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """Convert MCP configuration to Langchain parameters."""
        lc_config = {
            "temperature": config.temperature,
        }

        # Extract base_url if provided
        if "base_url" in config.kwargs:
            lc_config["base_url"] = config.kwargs["base_url"]
            
        # Langchain with Ollama doesn't directly support max_tokens
        # but we can add it for completeness
        if config.max_tokens:
            lc_config["max_tokens"] = config.max_tokens

        return lc_config

    def parse_response(self, response: Any) -> MCPMessage:
        """Parse Langchain response into MCP message."""
        # Langchain typically returns a string
        if isinstance(response, str):
            text = response
        else:
            text = str(response)

        return MCPMessage(
            role=MCPRole.ASSISTANT,
            content=[MCPTextContent(text=text)]
        )

    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """Validate that messages and config are compatible with Langchain."""
        # Basic validation
        if not messages:
            self.logger.warning("Empty message list")
            return False

        # Check that we have at least a user message
        has_user_message = any(message.role == MCPRole.USER for message in messages)
        if not has_user_message:
            self.logger.warning("No user message found")
            return False

        return True