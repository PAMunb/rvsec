"""
LLMClient unit tests for SGLang backend.

Tests the LangChain-based client with mocked SGLang responses.
"""

import pytest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage


pytestmark = pytest.mark.unit


class TestLLMClientInit:
    """Test LLMClient initialization."""

    def test_initialization_sglang(self):
        """LLMClient initializes with SGLang config."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")

        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "You are an Android testing agent."
        prompt_module.build_user_message = MagicMock(return_value="Test user message")

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            client = LLMClient(config, prompt_module)

            assert client.config == config
            assert client.prompt_module == prompt_module
            assert client.total_calls == 0
            assert len(client.tools) == 8

    def test_tools_bound(self):
        """All 8 Android tools are bound to LLM."""
        from rv_agent.llm.llm_client import LLMClient, get_android_tools
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            client = LLMClient(config, prompt_module)

            mock_llm.bind_tools.assert_called_once()
            tools = get_android_tools()
            assert len(tools) == 8


class TestGetAndroidTools:
    """Test get_android_tools function."""

    def test_returns_8_tools(self):
        """get_android_tools returns 8 Android tools."""
        from rv_agent.llm.llm_client import get_android_tools

        tools = get_android_tools()
        assert len(tools) == 8

    def test_tool_names(self):
        """All expected tool names are present."""
        from rv_agent.llm.llm_client import get_android_tools

        tools = get_android_tools()
        tool_names = {t.name for t in tools}

        expected = {
            "android_click",
            "android_type_text",
            "android_long_click",
            "android_swipe",
            "android_drag",
            "android_scroll",
            "android_back",
            "android_home",
        }
        assert tool_names == expected

    def test_tools_have_callable_func(self):
        """All tools have callable functions."""
        from rv_agent.llm.llm_client import get_android_tools

        tools = get_android_tools()
        for tool in tools:
            # StructuredTool objects have a .func attribute that is callable
            assert hasattr(tool, 'func'), f"Tool {tool.name} missing func attribute"
            assert callable(tool.func), f"Tool {tool.name}.func is not callable"


class TestExtractToolCalls:
    """Test _extract_tool_calls method."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_native_tool_calls_extracted(self, client):
        """Native tool_calls are extracted from response."""
        response = AIMessage(content="Reasoning")
        response.tool_calls = [{"name": "android_click", "args": {"x": 100, "y": 200}, "id": "1"}]

        tool_calls, strategy = client._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "android_click"
        assert strategy == "native"

    def test_fallback_parsing_xml(self, client):
        """Tool calls are parsed from XML format in content."""
        response = AIMessage(
            content='<tool_call>{"name": "android_click", "arguments": {"x": 352, "y": 624}}</tool_call>'
        )
        response.tool_calls = []

        tool_calls, strategy = client._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "android_click"
        assert strategy == "xml"

    def test_fallback_parsing_json(self, client):
        """Tool calls are parsed from JSON format in content."""
        response = AIMessage(
            content='{"name": "android_back", "arguments": {}}'
        )
        response.tool_calls = []

        tool_calls, strategy = client._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "android_back"
        assert "json" in strategy.lower()

    def test_fallback_parsing_pythonic(self, client):
        """Tool calls are parsed from pythonic format in content."""
        response = AIMessage(
            content='android_click(x=352, y=624, element_description="OK")'
        )
        response.tool_calls = []

        tool_calls, strategy = client._extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "android_click"
        assert strategy == "pythonic"

    def test_no_tool_calls_found(self, client):
        """No tool_calls when content has no parseable actions."""
        response = AIMessage(content="I'll click the OK button for you.")
        response.tool_calls = []

        tool_calls, strategy = client._extract_tool_calls(response)

        assert len(tool_calls) == 0
        assert strategy == "none"


class TestTokenTracking:
    """Test token usage tracking."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_initial_counters_zero(self, client):
        """Token counters start at zero."""
        assert client.total_input_tokens == 0
        assert client.total_output_tokens == 0
        assert client.total_calls == 0
        assert client.total_latency_ms == 0

    def test_get_stats(self, client):
        """get_stats returns correct structure."""
        stats = client.get_stats()

        assert isinstance(stats, dict)
        assert "total_calls" in stats
        assert "total_input_tokens" in stats
        assert "total_output_tokens" in stats
        assert "avg_latency_ms" in stats


class TestBuildMessages:
    """Test _build_messages method."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "You are an Android testing agent."
        prompt_module.build_user_message = MagicMock(
            return_value="Test screen with OK button"
        )

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_messages_structure(self, client):
        """Messages have correct structure."""
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = client._build_messages(
            ui_elements_text="OK button",
            screenshot_b64="base64encodedimage",
            iteration=1,
            last_action_summary=None,
        )

        assert len(messages) == 2
        assert isinstance(messages[0], SystemMessage)
        assert isinstance(messages[1], HumanMessage)

    def test_system_message_content(self, client):
        """System message contains prompt."""
        messages = client._build_messages(
            ui_elements_text="OK button",
            screenshot_b64="base64encodedimage",
            iteration=1,
            last_action_summary=None,
        )

        assert messages[0].content == "You are an Android testing agent."

    def test_user_message_has_image(self, client):
        """User message contains image data."""
        messages = client._build_messages(
            ui_elements_text="OK button",
            screenshot_b64="base64encodedimage",
            iteration=1,
            last_action_summary=None,
        )

        content = messages[1].content
        assert isinstance(content, list)
        assert len(content) == 2  # text + image
        assert content[1]["type"] == "image_url"
        assert "base64encodedimage" in content[1]["image_url"]["url"]

    def test_prompt_module_called(self, client):
        """Prompt module build_user_message is called with state info."""
        client._build_messages(
            ui_elements_text="OK button",
            screenshot_b64="base64encodedimage",
            iteration=5,
            last_action_summary="Clicked button",
        )

        client.prompt_module.build_user_message.assert_called_once()
        call_args = client.prompt_module.build_user_message.call_args[0][0]
        assert "ui_elements" in call_args
        assert call_args["iteration"] == 5
        assert call_args["last_action"] == "Clicked button"


class TestAndroidTools:
    """Test Android tool functions from sglang_tools module."""

    def test_android_click(self):
        """android_click returns success with coordinates."""
        from rv_agent.llm.tools.sglang_tools import android_click

        result = android_click.invoke({"x": 100, "y": 200, "element_description": "OK button"})

        assert result["success"] is True
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["element_description"] == "OK button"

    def test_android_type_text(self):
        """android_type_text returns success with text."""
        from rv_agent.llm.tools.sglang_tools import android_type_text

        result = android_type_text.invoke({"x": 100, "y": 200, "text": "hello"})

        assert result["success"] is True
        assert result["text"] == "hello"

    def test_android_long_click(self):
        """android_long_click returns success."""
        from rv_agent.llm.tools.sglang_tools import android_long_click

        result = android_long_click.invoke({"x": 100, "y": 200})

        assert result["success"] is True

    def test_android_swipe(self):
        """android_swipe returns success with direction."""
        from rv_agent.llm.tools.sglang_tools import android_swipe

        result = android_swipe.invoke({"direction": "up", "distance": "long"})

        assert result["success"] is True
        assert result["direction"] == "up"
        assert result["distance"] == "long"

    def test_android_scroll(self):
        """android_scroll returns success with direction."""
        from rv_agent.llm.tools.sglang_tools import android_scroll

        result = android_scroll.invoke({"direction": "down"})

        assert result["success"] is True
        assert result["direction"] == "down"

    def test_android_back(self):
        """android_back returns success."""
        from rv_agent.llm.tools.sglang_tools import android_back

        result = android_back.invoke({})

        assert result["success"] is True
        assert result["action"] == "back"

    def test_android_home(self):
        """android_home returns success."""
        from rv_agent.llm.tools.sglang_tools import android_home

        result = android_home.invoke({})

        assert result["success"] is True
        assert result["action"] == "home"


class TestExtractTokenUsage:
    """Test _extract_token_usage method."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_extract_from_token_usage(self, client):
        """Extract tokens from token_usage metadata."""
        response = AIMessage(content="Test")
        response.response_metadata = {
            "token_usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50
            }
        }

        input_tokens, output_tokens = client._extract_token_usage(response)

        assert input_tokens == 100
        assert output_tokens == 50

    def test_extract_from_usage(self, client):
        """Extract tokens from usage metadata (alternative format)."""
        response = AIMessage(content="Test")
        response.response_metadata = {
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 75
            }
        }

        input_tokens, output_tokens = client._extract_token_usage(response)

        assert input_tokens == 200
        assert output_tokens == 75

    def test_no_metadata(self, client):
        """Returns zeros when no metadata."""
        response = AIMessage(content="Test")

        input_tokens, output_tokens = client._extract_token_usage(response)

        assert input_tokens == 0
        assert output_tokens == 0

    def test_empty_metadata(self, client):
        """Returns zeros when metadata is empty."""
        response = AIMessage(content="Test")
        response.response_metadata = {}

        input_tokens, output_tokens = client._extract_token_usage(response)

        assert input_tokens == 0
        assert output_tokens == 0


class TestGenerateAction:
    """Test generate_action method."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"
        prompt_module.build_user_message = MagicMock(return_value="User message")

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_generate_action_success(self, client):
        """generate_action returns success result."""
        from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

        response = AIMessage(content="Clicking button")
        response.tool_calls = [{"name": "android_click", "args": {"x": 100, "y": 200}, "id": "1"}]
        response.response_metadata = {
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        client.llm_with_tools.invoke = MagicMock(return_value=response)

        mock_screen_desc = MagicMock(spec=ScreenDescription)
        mock_screen_desc.items = []

        result = client.generate_action(
            screen_description=mock_screen_desc,
            ui_elements_text="OK button at (100, 200)",
            screenshot_b64="base64image",
            iteration=1
        )

        assert result["success"] is True
        assert result["response"] is not None
        assert result["tokens_input"] == 100
        assert result["tokens_output"] == 50
        assert "time_ms" in result
        assert client.total_calls == 1

    def test_generate_action_failure(self, client):
        """generate_action raises LLMError on exception."""
        from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
        from rv_agent.domain.exceptions import LLMError

        client.llm_with_tools.invoke = MagicMock(side_effect=Exception("Connection failed"))

        mock_screen_desc = MagicMock(spec=ScreenDescription)
        mock_screen_desc.items = []

        with pytest.raises(LLMError) as exc_info:
            client.generate_action(
                screen_description=mock_screen_desc,
                ui_elements_text="OK button",
                screenshot_b64="base64image",
                iteration=1
            )

        assert "Connection failed" in str(exc_info.value)


class TestResetStats:
    """Test reset_stats method."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_reset_stats_clears_counters(self, client):
        """reset_stats clears all counters."""
        client.total_input_tokens = 1000
        client.total_output_tokens = 500
        client.total_calls = 10
        client.total_latency_ms = 5000

        client.reset_stats()

        assert client.total_input_tokens == 0
        assert client.total_output_tokens == 0
        assert client.total_calls == 0
        assert client.total_latency_ms == 0


class TestCleanup:
    """Test cleanup method."""

    @pytest.fixture
    def client(self):
        """Create client with mocked LLM."""
        from rv_agent.llm.llm_client import LLMClient
        from rv_agent.config.agent_config import RVAgentConfig

        config = RVAgentConfig.create_default(package_name="com.test.app")
        prompt_module = MagicMock()
        prompt_module.SYSTEM_PROMPT = "Test"

        with patch("rv_agent.llm.llm_client.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            return LLMClient(config, prompt_module)

    def test_cleanup_logs_message(self, client):
        """cleanup logs completion message."""
        # Just verify it doesn't raise
        client.cleanup()
        # Method should complete without error
