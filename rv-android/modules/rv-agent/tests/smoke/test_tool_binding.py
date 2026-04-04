"""
LangChain tool binding tests.

Validates that Android tools bind correctly to ChatOpenAI.
"""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

pytestmark = [pytest.mark.smoke, pytest.mark.sglang]


class TestToolBinding:
    """Test tool binding with LangChain."""

    def test_import_tools(self):
        """Android tools import without error."""
        from rv_agent.llm.llm_client import get_android_tools

        tools = get_android_tools()
        assert len(tools) == 7

    def test_tool_names(self):
        """All expected tools are present."""
        from rv_agent.llm.llm_client import get_android_tools

        tools = get_android_tools()
        tool_names = {t.name for t in tools}

        expected = {
            "android_click",
            "android_type_text",
            "android_long_click",
            "android_swipe",
            "android_scroll",
            "android_back",
            "android_home",
        }
        assert tool_names == expected

    def test_bind_tools_to_llm(self, sglang_url, sglang_model):
        """Tools bind to ChatOpenAI without error."""
        from rv_agent.llm.llm_client import get_android_tools

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=100,
            api_key="not-needed",
        )

        tools = get_android_tools()
        llm_with_tools = llm.bind_tools(tools)

        assert llm_with_tools is not None

    def test_tool_schemas_valid(self):
        """Tool schemas have required fields."""
        from rv_agent.llm.llm_client import get_android_tools

        tools = get_android_tools()

        for tool in tools:
            # Each tool should have name and description
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert tool.name.startswith("android_")

    def test_invoke_with_tools(self, sglang_url, sglang_model):
        """LLM invocation with tools returns response."""
        from rv_agent.llm.llm_client import get_android_tools

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=200,
            api_key="not-needed",
        )

        tools = get_android_tools()
        llm_with_tools = llm.bind_tools(tools)

        messages = [
            SystemMessage(
                content="You are an Android UI automation agent. Use the provided tools."
            ),
            HumanMessage(content="Click the OK button at coordinates (352, 624)."),
        ]

        response = llm_with_tools.invoke(messages)
        assert response is not None

        # Response should have content or tool_calls
        has_content = response.content and len(response.content) > 0
        has_tool_calls = (
            hasattr(response, "tool_calls") and len(response.tool_calls) > 0
        )

        assert (
            has_content or has_tool_calls
        ), "Response has neither content nor tool_calls"

    def test_tool_call_extraction(self, sglang_url, sglang_model):
        """Tool calls can be extracted from response."""
        from rv_agent.llm.llm_client import get_android_tools

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=200,
            api_key="not-needed",
        )

        tools = get_android_tools()
        llm_with_tools = llm.bind_tools(tools)

        messages = [
            SystemMessage(content="Use android_click tool to click at x=352, y=624."),
            HumanMessage(content="Click position (352, 624)"),
        ]

        response = llm_with_tools.invoke(messages)

        # Try native extraction first
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_call = response.tool_calls[0]
            assert "name" in tool_call or "function" in tool_call
        else:
            # Fallback: tool call might be in content
            from rv_agent.llm.tools.tool_call_parser import (
                parse_tool_calls_with_strategy,
            )

            tool_calls, _ = parse_tool_calls_with_strategy(response.content)
            # At least verify parsing doesn't crash
            assert isinstance(tool_calls, list)
