# rvandroid/llm/adapters/dspy_adapter.py
"""MCP adapter for DSPy models."""

from typing import Dict, Any, List

from rvandroid.llm.adapter import MCPAdapter
from rvandroid.llm.data_structures import LLMMessage, LLMRole, LLMTextContent


class DSPyAdapter(MCPAdapter):
    """
    Adapter for DSPy language models.
    
    Converts between MCP messages and DSPy-specific formats.
    Handles the specific formatting requirements of DSPy, including
    message conversions and configuration parameters.
    """

    def prepare_messages(self, messages: List[LLMMessage]) -> Dict[str, Any]:
        """
        Convert MCP messages to DSPy format.
        
        Args:
            messages: List of MCP messages to convert
            
        Returns:
            Dictionary with "messages" key containing formatted messages
        """
        dspy_messages = []

        for message in messages:
            content = message.get_text_content()

            if message.role == LLMRole.SYSTEM:
                dspy_messages.append({"role": "system", "content": content})
            elif message.role == LLMRole.USER:
                dspy_messages.append({"role": "user", "content": content})
            elif message.role == LLMRole.ASSISTANT:
                dspy_messages.append({"role": "assistant", "content": content})
            elif message.role == LLMRole.TOOL:
                dspy_messages.append({"role": "tool", "content": content, "tool_call_id": message.tool_call_id})

        return {"messages": dspy_messages}

    # def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
    #     """
    #     Convert MCP configuration to DSPy parameters.
    #
    #     Args:
    #         config: MCP configuration to convert
    #
    #     Returns:
    #         Dictionary with DSPy-specific configuration
    #     """
    #     dspy_config = {
    #         "model": config.model_name,
    #         "temperature": config.temperature,
    #     }
    #
    #     if config.max_tokens:
    #         dspy_config["max_tokens"] = config.max_tokens
    #
    #     if config.top_p < 1.0:
    #         dspy_config["top_p"] = config.top_p
    #
    #     return dspy_config

    def parse_response(self, response: Any) -> LLMMessage:
        """
        Parse DSPy response into MCP message.
        
        Args:
            response: Response from DSPy
            
        Returns:
            LLMMessage with parsed response
        """
        if isinstance(response, dict):
            if "content" in response:
                text = response["content"]
            else:
                text = str(response)
        else:
            text = str(response)

        return LLMMessage(
            role=LLMRole.ASSISTANT,
            content=[LLMTextContent(text=text)]
        )

    # def validate_request(self, messages: List[LLMMessage], config: MCPConfiguration) -> bool:
    #     """
    #     Validate that messages and config are compatible with DSPy.
    #
    #     Args:
    #         messages: MCP messages to validate
    #         config: Configuration to validate
    #
    #     Returns:
    #         True if the request is valid for DSPy, False otherwise
    #     """
    #     # Basic validation
    #     if not messages:
    #         self.logger.warning("Empty message list")
    #         return False
    #
    #     return True