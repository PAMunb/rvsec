# rvandroid/llm/adapters/huggingface_adapter.py
"""MCP adapter for HuggingFace models."""

from typing import Dict, Any, List

from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent
from rvandroid.llm.adapter import MCPAdapter


class HuggingFaceAdapter(MCPAdapter):
    """Adapter for HuggingFace models."""

    def __init__(self):
        """Initialize the HuggingFace adapter."""
        super().__init__()

    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """Convert MCP messages to HuggingFace format."""
        hf_messages = []

        for message in messages:
            content = message.get_text_content()
            
            # HuggingFace expects a list of dictionaries with 'role' and 'content'
            hf_messages.append({
                "role": message.role.value,
                "content": content
            })
            
        return {"messages": hf_messages}

    # def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
    #     """Convert MCP configuration to HuggingFace parameters."""
    #     hf_config = {
    #         "temperature": config.temperature,
    #         "do_sample": True,  # Enable sampling for temperature to take effect
    #     }
    #
    #     if config.max_tokens:
    #         hf_config["max_new_tokens"] = config.max_tokens
    #
    #     if config.top_p < 1.0:
    #         hf_config["top_p"] = config.top_p
    #
    #     # Add model-specific parameters for HuggingFace
    #     hf_config["device"] = config.kwargs.get("device", "cuda")
    #
    #     return hf_config

    def parse_response(self, response: Any) -> MCPMessage:
        """Parse HuggingFace response into MCP message."""
        # HuggingFace typically returns a string directly
        if isinstance(response, str):
            text = response
        else:
            text = str(response)

        return MCPMessage(
            role=MCPRole.ASSISTANT,
            content=[MCPTextContent(text=text)]
        )

    # def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
    #     """Validate that messages and config are compatible with HuggingFace."""
    #     # Basic validation
    #     if not messages:
    #         self.logger.warning("Empty message list")
    #         return False
    #
    #     # Check for unsupported content types (HuggingFace supports only text)
    #     for message in messages:
    #         for content in message.content:
    #             if not isinstance(content, MCPTextContent):
    #                 self.logger.warning(f"HuggingFace does not support content type: {type(content)}")
    #                 return False
    #
    #     return True