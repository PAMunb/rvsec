# rvandroid/llm/adapters/frontier_adapter.py
"""MCP adapter for Frontier models (Claude, GPT, etc)."""

from typing import Dict, Any, List

from rvandroid.llm.data_structures import LLMMessage, LLMRole, LLMTextContent
from rvandroid.llm.adapter import MCPAdapter


class FrontierAdapter(MCPAdapter):
    """Adapter for frontier LLM models (Claude, GPT, etc.)."""

    def __init__(self):
        """Initialize the frontier model adapter."""
        super().__init__()

    def prepare_messages(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """Convert MCP messages to frontier model format."""
        frontier_messages = []

        for message in messages:
            content = message.get_text_content()
            
            # Handle different provider-specific message formats
            frontier_messages.append({
                "role": message.role.value,
                "content": content
            })
            
        return {"messages": frontier_messages}

    # def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
    #     """Convert MCP configuration to frontier model parameters."""
    #     model_config = {
    #         "model": config.model_name,
    #         "temperature": config.temperature,
    #     }
    #
    #     if config.max_tokens:
    #         model_config["max_tokens"] = config.max_tokens
    #
    #     if config.top_p < 1.0:
    #         model_config["top_p"] = config.top_p
    #
    #     if config.frequency_penalty > 0:
    #         model_config["frequency_penalty"] = config.frequency_penalty
    #
    #     if config.presence_penalty > 0:
    #         model_config["presence_penalty"] = config.presence_penalty
    #
    #     if config.stop:
    #         model_config["stop"] = config.stop
    #
    #     return model_config

    def parse_response(self, response: Any) -> LLMMessage:
        """Parse frontier model response into MCP message."""
        if isinstance(response, str):
            text = response
        elif isinstance(response, dict):
            if "content" in response:
                text = response["content"]
            elif "choices" in response and len(response["choices"]) > 0:
                # Handle OpenAI-style responses
                text = response["choices"][0].get("message", {}).get("content", "")
            else:
                text = str(response)
        else:
            text = str(response)

        return LLMMessage(
            role=LLMRole.ASSISTANT,
            content=[LLMTextContent(text=text)]
        )

    # def validate_request(self, messages: List[LLMMessage], config: MCPConfiguration) -> bool:
    #     """Validate that messages and config are compatible with frontier models."""
    #     # Basic validation
    #     if not messages:
    #         self.logger.warning("Empty message list")
    #         return False
    #
    #     # Frontier models should have a provider
    #     provider = config.kwargs.get("provider")
    #     if not provider:
    #         self.logger.warning("No provider specified for frontier model")
    #         return False
    #
    #     return True