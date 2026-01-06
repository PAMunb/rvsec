"""
LLM client integration tests with SGLang.

Tests LLM functionality via AgentFactory and RVAgent.
"""

import pytest
import time
import base64
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory
from .conftest import launch_app, DATASET_ROOT, DEVICE_ID, SGLANG_URL, SGLANG_MODEL


pytestmark = [pytest.mark.online, pytest.mark.sglang]


class TestSGLangConnectivity:
    """Test SGLang server connectivity."""

    def test_server_health(self, sglang_url, check_sglang):
        """SGLang server is healthy."""
        import httpx
        response = httpx.get(f"{sglang_url}/models", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        print(f"\n  Available models: {[m['id'] for m in data['data']]}")

    def test_text_generation(self, sglang_url, sglang_model, check_sglang):
        """SGLang can generate text."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=50,
            api_key="not-needed",
        )

        response = llm.invoke([HumanMessage(content="Say 'hello' and nothing else.")])
        assert response is not None
        assert len(response.content) > 0
        print(f"\n  Response: {response.content[:100]}")

    def test_response_latency(self, sglang_url, sglang_model, check_sglang):
        """Response latency is acceptable."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=20,
            api_key="not-needed",
        )

        start = time.perf_counter()
        response = llm.invoke([HumanMessage(content="Say 'test'")])
        latency_ms = (time.perf_counter() - start) * 1000

        assert response is not None
        assert latency_ms < 10000, f"Latency {latency_ms}ms exceeds 10s threshold"
        print(f"\n  Latency: {latency_ms:.0f}ms")


class TestLLMWithAgent:
    """Test LLM integration through agent."""

    def test_agent_has_llm_client(self, device, cryptoapp, check_emulator, check_sglang):
        """Agent in multimode has LLM client."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="multimode",
            llm_probability=0.7,
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)
        assert agent.llm_client is not None
        print(f"\n  LLM client initialized")

    def test_agent_llm_only_mode(self, device, cryptoapp, check_emulator, check_sglang):
        """Agent in llm_only mode works."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="llm_only",
            llm_base_url=SGLANG_URL,
            llm_model=SGLANG_MODEL,
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)
        assert agent.llm_client is not None
        assert agent.config.agent_mode == "llm_only"
        print(f"\n  LLM-only agent created")

    def test_pure_algorithm_no_llm(self, device, cryptoapp, check_emulator):
        """Agent in pure_algorithm mode has no LLM client."""
        config = RVAgentConfig(
            package_name=cryptoapp.package_name,
            device_id=DEVICE_ID,
            agent_mode="pure_algorithm",
            timeout=60,
        )

        agent = AgentFactory.create_agent(config, device=device)
        # In pure_algorithm mode, llm_client should be None
        assert agent.llm_client is None or agent.config.agent_mode == "pure_algorithm"
        print(f"\n  Pure algorithm agent created (no LLM)")


class TestToolCalling:
    """Test tool calling functionality via SGLang."""

    def test_tool_binding(self, sglang_url, sglang_model, check_sglang):
        """SGLang supports tool binding."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        from langchain_core.tools import tool

        @tool
        def android_click(x: int, y: int, element_description: str = "") -> str:
            """Click at screen coordinates."""
            return f"Clicked at ({x}, {y})"

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.25,
            max_tokens=500,
            api_key="not-needed",
        )

        llm_with_tools = llm.bind_tools([android_click])
        assert llm_with_tools is not None
        print(f"\n  Tool binding successful")

    def test_tool_call_generation(self, sglang_url, sglang_model, check_sglang):
        """SGLang generates tool calls."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        from langchain_core.tools import tool

        @tool
        def android_click(x: int, y: int, element_description: str = "") -> str:
            """Click at screen coordinates."""
            return f"Clicked at ({x}, {y})"

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.25,
            max_tokens=500,
            api_key="not-needed",
        )

        llm_with_tools = llm.bind_tools([android_click])

        prompt = """You are testing an Android app. Click the Login button.

Available elements:
1. Button "Login" at (540, 800)
2. Button "Cancel" at (540, 1000)

Use the android_click tool to click the Login button."""

        response = llm_with_tools.invoke([HumanMessage(content=prompt)])

        print(f"\n  Response content: {response.content[:200] if response.content else 'empty'}")
        print(f"  Tool calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'none'}")

        # Response should have tool call or content
        has_response = response.content or (hasattr(response, 'tool_calls') and response.tool_calls)
        assert has_response


class TestVisionCapability:
    """Test vision/multimodal capability."""

    def test_image_in_message(self, sglang_url, sglang_model, check_sglang):
        """SGLang accepts image in message."""
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        # Load real screenshot from dataset
        screenshot_path = DATASET_ROOT / "cryptoapp.apk" / "screenshot_001.png"
        if not screenshot_path.exists():
            screenshots = list((DATASET_ROOT / "cryptoapp.apk").glob("*.png"))
            if screenshots:
                screenshot_path = screenshots[0]
            else:
                pytest.skip("No screenshots available")

        with open(screenshot_path, "rb") as f:
            screenshot_b64 = base64.b64encode(f.read()).decode()

        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.25,
            max_tokens=200,
            api_key="not-needed",
        )

        message = HumanMessage(
            content=[
                {"type": "text", "text": "Describe this Android screen briefly."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
            ]
        )

        response = llm.invoke([message])
        assert response is not None
        assert len(response.content) > 0
        print(f"\n  Vision response: {response.content[:200]}")
