# rvandroid/mcp/adapters/dspy_adapter.py
"""MCP adapter for DSPy models."""

from typing import Dict, Any, List

from rvandroid.mcp.mcp_adapter import MCPAdapter
from rvandroid.mcp.mcp_data_structures import MCPMessage, MCPConfiguration, MCPRole, MCPTextContent


class DSPyAdapter(MCPAdapter):
    """Adapter for DSPy models."""

    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """Convert MCP messages to DSPy format."""
        dspy_messages = []

        for message in messages:
            content = message.get_text_content()

            if message.role == MCPRole.SYSTEM:
                dspy_messages.append({"role": "system", "content": content})
            elif message.role == MCPRole.USER:
                dspy_messages.append({"role": "user", "content": content})
            elif message.role == MCPRole.ASSISTANT:
                dspy_messages.append({"role": "assistant", "content": content})
            elif message.role == MCPRole.TOOL:
                dspy_messages.append({"role": "tool", "content": content, "tool_call_id": message.tool_call_id})

        return {"messages": dspy_messages}

    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """Convert MCP configuration to DSPy parameters."""
        dspy_config = {
            "model": config.model_name,
            "temperature": config.temperature,
        }

        if config.max_tokens:
            dspy_config["max_tokens"] = config.max_tokens

        if config.top_p < 1.0:
            dspy_config["top_p"] = config.top_p

        return dspy_config

    def parse_response(self, response: Any) -> MCPMessage:
        """Parse DSPy response into MCP message."""
        if isinstance(response, dict):
            if "content" in response:
                text = response["content"]
            else:
                text = str(response)
        else:
            text = str(response)

        return MCPMessage(
            role=MCPRole.ASSISTANT,
            content=[MCPTextContent(text=text)]
        )

    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """Validate that messages and config are compatible with DSPy."""
        # Basic validation
        if not messages:
            self.logger.warning("Empty message list")
            return False

        return True
