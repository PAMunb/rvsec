"""
Performance tests for LLM latency measurement.

Tests verify:
- Tool call generation latency with vision model
- Latency distribution across multiple requests
- Baseline comparison with acceptable thresholds
"""

import pytest
import time
import base64
import statistics
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from rv_agent.llm.llm_client import get_android_tools


pytestmark = [pytest.mark.performance]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def llm_with_tools(sglang_url, sglang_model):
    """Create LLM with tools bound."""
    llm = ChatOpenAI(
        base_url=sglang_url,
        model=sglang_model,
        temperature=0.01,
        max_tokens=512,
        api_key="not-needed",
    )
    return llm.bind_tools(get_android_tools())


@pytest.fixture
def screenshot_fixtures():
    """Load screenshot fixtures for testing."""
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "screenshots"
    screenshots = {}

    for app_dir in ["cryptoapp", "ludo", "hashpass"]:
        app_path = fixture_dir / app_dir
        if app_path.exists():
            screenshots[app_dir] = []
            for img_path in sorted(app_path.glob("*.png"))[:5]:
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                    screenshots[app_dir].append({
                        "path": str(img_path),
                        "base64": img_b64
                    })

    return screenshots


def create_vision_message(img_b64: str) -> HumanMessage:
    """Create a vision message for tool calling."""
    return HumanMessage(content=[
        {"type": "text", "text": "Click on the most interactive element."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
    ])


# =============================================================================
# Latency Tests
# =============================================================================

class TestLLMLatency:
    """Tests for LLM latency measurement."""

    @pytest.mark.slow
    def test_single_request_latency(self, llm_with_tools, screenshot_fixtures):
        """Test latency for a single tool call request."""
        if "cryptoapp" not in screenshot_fixtures or not screenshot_fixtures["cryptoapp"]:
            pytest.skip("No cryptoapp screenshots available")

        img_b64 = screenshot_fixtures["cryptoapp"][0]["base64"]
        message = create_vision_message(img_b64)

        start_time = time.time()
        result = llm_with_tools.invoke([message])
        latency_ms = (time.time() - start_time) * 1000

        assert result is not None
        assert latency_ms < 10000, f"Latency too high: {latency_ms}ms"

        print(f"\nSingle request latency: {latency_ms:.0f}ms")

    @pytest.mark.slow
    def test_multi_request_latency(self, llm_with_tools, screenshot_fixtures):
        """Test latency distribution across multiple requests."""
        if "cryptoapp" not in screenshot_fixtures:
            pytest.skip("No cryptoapp screenshots available")

        latencies = []
        screenshots = screenshot_fixtures["cryptoapp"]

        for img_data in screenshots:
            message = create_vision_message(img_data["base64"])

            start_time = time.time()
            result = llm_with_tools.invoke([message])
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)

        if len(latencies) < 2:
            pytest.skip("Not enough screenshots for statistics")

        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        max_latency = max(latencies)

        print(f"\nLatency statistics ({len(latencies)} requests):")
        print(f"  Average: {avg_latency:.0f}ms")
        print(f"  P95: {p95_latency:.0f}ms")
        print(f"  Max: {max_latency:.0f}ms")

        # Baseline thresholds
        assert avg_latency < 5000, f"Average latency too high: {avg_latency}ms"
        assert p95_latency < 8000, f"P95 latency too high: {p95_latency}ms"

    @pytest.mark.slow
    def test_cross_app_latency(self, llm_with_tools, screenshot_fixtures):
        """Test latency consistency across different apps."""
        app_latencies = {}

        for app_name, screenshots in screenshot_fixtures.items():
            if not screenshots:
                continue

            latencies = []
            for img_data in screenshots[:3]:
                message = create_vision_message(img_data["base64"])

                start_time = time.time()
                result = llm_with_tools.invoke([message])
                latency_ms = (time.time() - start_time) * 1000
                latencies.append(latency_ms)

            if latencies:
                app_latencies[app_name] = {
                    "avg": statistics.mean(latencies),
                    "max": max(latencies)
                }

        if not app_latencies:
            pytest.skip("No screenshots available for testing")

        print("\nLatency by app:")
        for app, metrics in app_latencies.items():
            print(f"  {app}: avg={metrics['avg']:.0f}ms, max={metrics['max']:.0f}ms")

        all_avgs = [m["avg"] for m in app_latencies.values()]
        overall_avg = statistics.mean(all_avgs)

        for app, metrics in app_latencies.items():
            assert metrics["avg"] < overall_avg * 2.5, \
                f"{app} latency ({metrics['avg']}ms) is too high compared to average ({overall_avg}ms)"


class TestToolCallLatency:
    """Tests for tool call generation latency."""

    @pytest.mark.slow
    def test_tool_call_success_rate(self, llm_with_tools, screenshot_fixtures):
        """Test tool call success rate across multiple requests."""
        if not screenshot_fixtures:
            pytest.skip("No screenshots available")

        successes = 0
        failures = 0

        for app_name, screenshots in screenshot_fixtures.items():
            for img_data in screenshots:
                message = create_vision_message(img_data["base64"])
                result = llm_with_tools.invoke([message])

                if result and hasattr(result, 'tool_calls') and result.tool_calls:
                    successes += 1
                else:
                    failures += 1

        total = successes + failures
        success_rate = (successes / total * 100) if total > 0 else 0

        print(f"\nTool call success rate: {success_rate:.1f}% ({successes}/{total})")

        # Baseline: V12 had 90.3% tool call success rate
        assert success_rate >= 70, f"Tool call success rate too low: {success_rate}%"


class TestWarmup:
    """Tests for model warmup behavior."""

    @pytest.mark.slow
    def test_cold_vs_warm_latency(self, sglang_url, sglang_model, screenshot_fixtures):
        """Test latency difference between cold and warm model."""
        if "cryptoapp" not in screenshot_fixtures or not screenshot_fixtures["cryptoapp"]:
            pytest.skip("No cryptoapp screenshots available")

        img_b64 = screenshot_fixtures["cryptoapp"][0]["base64"]
        message = create_vision_message(img_b64)

        # Create fresh client for cold start
        cold_llm = ChatOpenAI(
            base_url=sglang_url,
            model=sglang_model,
            temperature=0.01,
            max_tokens=512,
            api_key="not-needed",
        ).bind_tools(get_android_tools())

        # First request (cold)
        start_time = time.time()
        cold_llm.invoke([message])
        cold_latency = (time.time() - start_time) * 1000

        # Subsequent requests (warm)
        warm_latencies = []
        for _ in range(3):
            start_time = time.time()
            cold_llm.invoke([message])
            warm_latencies.append((time.time() - start_time) * 1000)

        avg_warm_latency = statistics.mean(warm_latencies)

        print(f"\nWarmup comparison:")
        print(f"  Cold start: {cold_latency:.0f}ms")
        print(f"  Warm average: {avg_warm_latency:.0f}ms")
        print(f"  Speedup: {cold_latency / avg_warm_latency:.1f}x")

        # Warm should be faster than cold (or at most equal)
        assert avg_warm_latency < cold_latency * 1.5, \
            "Warm latency should not be significantly worse than cold"
