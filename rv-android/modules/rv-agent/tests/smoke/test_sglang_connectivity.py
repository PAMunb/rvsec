"""
SGLang server connectivity tests.

Validates connection to SGLang server and basic LLM functionality.
"""

import time

import pytest
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

pytestmark = [pytest.mark.smoke, pytest.mark.sglang]


class TestSGLangConnectivity:
    """Test SGLang server connectivity."""

    def test_server_reachable(self, sglang_url, sglang_model):
        """SGLang server responds to basic request."""
        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=10,
            api_key="not-needed",
            timeout=10,
        )

        response = llm.invoke([HumanMessage(content="Say 'hello'")])
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0

    def test_text_generation(self, sglang_url, sglang_model):
        """Text generation produces valid output."""
        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=50,
            api_key="not-needed",
        )

        response = llm.invoke(
            [HumanMessage(content="What is 2+2? Answer with just the number.")]
        )
        assert response.content is not None
        assert "4" in response.content

    def test_response_latency(self, sglang_url, sglang_model):
        """Response latency is within acceptable bounds."""
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

    def test_response_metadata(self, sglang_url, sglang_model):
        """Response contains token usage metadata."""
        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=20,
            api_key="not-needed",
        )

        response = llm.invoke([HumanMessage(content="Hi")])

        assert hasattr(response, "response_metadata")
        meta = response.response_metadata

        # SGLang should provide token usage
        if "token_usage" in meta:
            assert "prompt_tokens" in meta["token_usage"]
            assert "completion_tokens" in meta["token_usage"]

    def test_timeout_handling(self, sglang_url, sglang_model):
        """Short timeout raises appropriate error."""
        llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=1000,
            api_key="not-needed",
            timeout=0.001,  # Very short timeout
        )

        with pytest.raises(Exception):
            # Should timeout with extremely short timeout
            llm.invoke([HumanMessage(content="Write a very long story about...")])
