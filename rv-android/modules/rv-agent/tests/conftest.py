"""
Shared pytest fixtures for rv-agent tests.

Provides fixtures for:
- SGLang LLM client configuration
- Mock device interface
- Sample screenshots and UI dumps
- Test app configurations
"""

import base64
import os
import sys
from functools import lru_cache
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
# Add the tests/ directory itself so the shared `support_config` factories are
# importable as a top-level module from any test file (conftest loads first).
sys.path.insert(0, str(Path(__file__).parent))


# =============================================================================
# Configuration Fixtures
# =============================================================================


@pytest.fixture
def sglang_url():
    """SGLang server URL."""
    return os.getenv("SGLANG_URL", "http://192.168.0.36:30000/v1")


@pytest.fixture
def sglang_model():
    """SGLang model name."""
    return os.getenv("SGLANG_MODEL", "Qwen/Qwen3-VL-4B-Instruct")


@lru_cache(maxsize=None)
def _sglang_reachable(url: str) -> bool:
    """Probe the SGLang server once per URL. Cached so a whole run pays the
    connection cost at most once. Any transport error means unreachable."""
    import httpx

    try:
        # /models is the OpenAI-compatible liveness endpoint (url already ends in /v1).
        response = httpx.get(f"{url}/models", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def require_sglang(sglang_url):
    """Skip the requesting test when the SGLang server is not reachable, so the
    offline suite stays green without a running LLM backend (gh77 task 1.3)."""
    if not _sglang_reachable(sglang_url):
        pytest.skip(f"SGLang server not reachable at {sglang_url}")


@pytest.fixture
def test_package():
    """Default test package name."""
    return "cryptoapp"


@pytest.fixture
def test_device_id():
    """Default test device ID."""
    return "emulator-5554"


@pytest.fixture
def device_dimensions():
    """Device screen dimensions."""
    return (1080, 1920)


@pytest.fixture
def optimized_dimensions():
    """Optimized image dimensions for Qwen3-VL."""
    return (704, 1248)


# =============================================================================
# Agent Config Fixtures
# =============================================================================


@pytest.fixture
def agent_config(test_package, test_device_id, sglang_url, sglang_model):
    """RVAgentConfig with SGLang settings."""
    from rv_agent.config.agent_config import RVAgentConfig

    return RVAgentConfig(
        package_name=test_package,
        device_id=test_device_id,
        llm_base_url=sglang_url,
        llm_model=sglang_model,
        agent_mode="multimode",
        llm_probability=0.7,
        llm_temperature=0.01,
        llm_top_p=0.6,
        llm_max_tokens=2048,
        timeout=300,
    )


@pytest.fixture
def pure_algorithm_config(agent_config):
    """Config for pure algorithm mode."""
    agent_config.agent_mode = "pure_algorithm"
    return agent_config


@pytest.fixture
def llm_only_config(agent_config):
    """Config for LLM only mode."""
    agent_config.agent_mode = "llm_only"
    return agent_config


# =============================================================================
# Mock Device Fixtures
# =============================================================================


@pytest.fixture
def mock_device():
    """Mock device interface for offline testing."""
    device = Mock()
    device.get_current_package.return_value = "cryptoapp"
    device.get_screenshot.return_value = b"fake_screenshot_bytes"
    device.get_ui_hierarchy.return_value = "<hierarchy></hierarchy>"
    device.click.return_value = True
    device.type_text.return_value = True
    device.swipe.return_value = True
    device.back.return_value = True
    device.home.return_value = True
    return device


@pytest.fixture
def mock_screen_processor():
    """Mock screen processor."""
    processor = Mock()
    processor.capture_and_process.return_value = {
        "screenshot_b64": "base64_encoded_image",
        "ui_elements_text": "Button: OK at (352, 624)",
        "screen_description": Mock(elements=[]),
    }
    return processor


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_screenshot_b64():
    """Sample base64 encoded screenshot (1x1 white pixel)."""
    # Minimal PNG: 1x1 white pixel
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    return base64.b64encode(png_bytes).decode()


@pytest.fixture
def sample_ui_elements_text():
    """Sample UI elements text for prompts."""
    return """
Available UI Elements:
1. Button "OK" at (352, 624) - bounds [[280, 580], [424, 668]]
2. EditText "Enter password" at (352, 400) - bounds [[100, 350], [604, 450]]
3. TextView "Welcome" at (352, 200) - bounds [[200, 150], [504, 250]]
"""


@pytest.fixture
def sample_tool_call_xml():
    """Sample Qwen XML format tool call."""
    return """<tool_call>
{"name": "android_click", "arguments": {"x": 352, "y": 624, "element_description": "OK button"}}
</tool_call>"""


@pytest.fixture
def sample_tool_call_json():
    """Sample JSON format tool call."""
    return '{"name": "android_click", "arguments": {"x": 352, "y": 624}}'


@pytest.fixture
def sample_tool_call_json_array():
    """Sample JSON array format tool calls."""
    return '[{"name": "android_click", "arguments": {"x": 352, "y": 624}}]'


# =============================================================================
# LLM Response Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_response():
    """Mock LangChain AIMessage response."""
    response = Mock()
    response.content = ""
    response.tool_calls = [
        {
            "name": "android_click",
            "args": {"x": 352, "y": 624, "element_description": "OK button"},
            "id": "call_123",
        }
    ]
    response.response_metadata = {
        "token_usage": {
            "prompt_tokens": 1500,
            "completion_tokens": 50,
        }
    }
    return response


@pytest.fixture
def mock_llm_response_text_only():
    """Mock AIMessage with tool call in text content."""
    response = Mock()
    response.content = """<tool_call>
{"name": "android_click", "arguments": {"x": 352, "y": 624}}
</tool_call>"""
    response.tool_calls = []
    response.response_metadata = {
        "token_usage": {
            "prompt_tokens": 1500,
            "completion_tokens": 80,
        }
    }
    return response


# =============================================================================
# Strategy Fixtures
# =============================================================================


@pytest.fixture
def mock_ui_elements():
    """Mock UI elements for strategy testing."""
    from rv_agent.strategies.base_strategy import ItemAction

    return [
        ItemAction(
            action_type="CLICK",
            resource_id="btn_ok",
            coordinates=(352, 624),
            text="OK",
            mop_priority=0,
        ),
        ItemAction(
            action_type="CLICK",
            resource_id="btn_cancel",
            coordinates=(200, 624),
            text="Cancel",
            mop_priority=0,
        ),
        ItemAction(
            action_type="SET_TEXT",
            resource_id="edit_password",
            coordinates=(352, 400),
            text="Enter password",
            mop_priority=1,  # Has MOP marker
        ),
    ]


# =============================================================================
# Dataset Fixtures
# =============================================================================


@pytest.fixture
def apks_base_path():
    """Path to APKs dataset."""
    return Path("/home/pedro/desenvolvimento/RV_ANDROID/apks")


@pytest.fixture
def tier1_apps():
    """Tier 1 core apps (10 apps) for smoke and baseline."""
    return [
        "cryptoapp",
        "com.android.keepass",
        "com.amnesica.kryptey",
        "org.cryptomator.lite",
        "com.amaze.filemanager",
        "org.mariotaku.twidere",
        "com.blogspot.e_kanivets.moneytracker",
        "com.alienpants.leafpicrevived",
        "asgardius.page.s3manager",
        "com.rafapps.simplenotes",
    ]


# =============================================================================
# Validation Fixtures
# =============================================================================


@pytest.fixture
def v10_baseline_path():
    """Path to V10 baseline results."""
    return Path(__file__).parent.parent / "test_v10_baseline_10apps_aggregate.json"


@pytest.fixture
def validation_thresholds():
    """Thresholds for validation metrics."""
    return {
        "valid_action_rate": 0.80,
        "tool_call_success": 0.85,
        "llm_percentage_min": 0.65,
        "llm_percentage_max": 0.75,
        "avg_latency_ms": 2000,
        "tokens_per_iteration": 3000,
    }


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "smoke: marks tests as smoke tests (fast, basic sanity)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (isolated, mocked)"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (component interaction)",
    )
    config.addinivalue_line(
        "markers", "system: marks tests as system tests (end-to-end)"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance benchmarks"
    )
    config.addinivalue_line("markers", "regression: marks tests as regression tests")
    config.addinivalue_line("markers", "online: marks tests requiring emulator (slow)")
    config.addinivalue_line("markers", "sglang: marks tests requiring SGLang server")
    config.addinivalue_line("markers", "slow: marks tests that take significant time")
    config.addinivalue_line(
        "markers", "dataset: marks tests that use the full app dataset"
    )
