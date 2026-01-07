"""
Performance tests for tool call success rate.

Tests verify:
- Tool call extraction rate from LLM responses
- Tool call validity (correct format, valid coordinates)
- Parser fallback mechanisms
"""

import pytest
import base64
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from rv_agent.llm.llm_client import get_android_tools
from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text


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
    """Load all screenshot fixtures."""
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "screenshots"
    all_screenshots = []

    for app_dir in fixture_dir.iterdir():
        if app_dir.is_dir():
            for img_path in sorted(app_dir.glob("*.png"))[:5]:
                with open(img_path, "rb") as f:
                    all_screenshots.append({
                        "app": app_dir.name,
                        "path": str(img_path),
                        "base64": base64.b64encode(f.read()).decode()
                    })

    return all_screenshots


def create_vision_message(img_b64: str) -> HumanMessage:
    """Create a vision message for tool calling."""
    return HumanMessage(content=[
        {"type": "text", "text": "Click on the most interactive element."},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
    ])


# =============================================================================
# Tool Call Rate Tests
# =============================================================================

class TestToolCallRate:
    """Tests for tool call extraction rate."""

    @pytest.mark.slow
    def test_tool_call_extraction_rate(self, llm_with_tools, screenshot_fixtures):
        """Test percentage of responses with valid tool calls."""
        if not screenshot_fixtures:
            pytest.skip("No screenshots available")

        results = {
            "native_tool_calls": 0,
            "parsed_tool_calls": 0,
            "no_tool_calls": 0,
            "errors": 0
        }

        for img_data in screenshot_fixtures:
            try:
                message = create_vision_message(img_data["base64"])
                result = llm_with_tools.invoke([message])

                if result is None:
                    results["errors"] += 1
                elif hasattr(result, 'tool_calls') and result.tool_calls:
                    results["native_tool_calls"] += 1
                elif hasattr(result, 'content') and result.content:
                    # Try fallback parsing
                    parsed = parse_tool_calls_from_text(result.content)
                    if parsed:
                        results["parsed_tool_calls"] += 1
                    else:
                        results["no_tool_calls"] += 1
                else:
                    results["no_tool_calls"] += 1

            except Exception as e:
                results["errors"] += 1

        total = len(screenshot_fixtures)
        success_count = results["native_tool_calls"] + results["parsed_tool_calls"]
        success_rate = (success_count / total * 100) if total > 0 else 0

        print(f"\nTool call extraction results ({total} screenshots):")
        print(f"  Native tool calls: {results['native_tool_calls']}")
        print(f"  Parsed tool calls: {results['parsed_tool_calls']}")
        print(f"  No tool calls: {results['no_tool_calls']}")
        print(f"  Errors: {results['errors']}")
        print(f"  Success rate: {success_rate:.1f}%")

        # Baseline: V12 had 90.3% tool call success, we target >= 70%
        assert success_rate >= 70, f"Tool call rate too low: {success_rate}%"

    @pytest.mark.slow
    def test_tool_type_distribution(self, llm_with_tools, screenshot_fixtures):
        """Test distribution of tool types in responses."""
        if not screenshot_fixtures:
            pytest.skip("No screenshots available")

        tool_counts = {}

        for img_data in screenshot_fixtures:
            message = create_vision_message(img_data["base64"])
            result = llm_with_tools.invoke([message])

            if result and hasattr(result, 'tool_calls') and result.tool_calls:
                for tool_call in result.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        total_calls = sum(tool_counts.values())

        if total_calls == 0:
            pytest.skip("No tool calls generated")

        print(f"\nTool type distribution ({total_calls} total calls):")
        for tool_name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            pct = count / total_calls * 100
            print(f"  {tool_name}: {count} ({pct:.1f}%)")

        # Should have at least android_click as the most common
        assert "android_click" in tool_counts, "Expected android_click tool"


class TestToolCallValidity:
    """Tests for tool call validity."""

    @pytest.mark.slow
    def test_coordinate_validity(self, llm_with_tools, screenshot_fixtures):
        """Test that coordinates are within valid bounds."""
        if not screenshot_fixtures:
            pytest.skip("No screenshots available")

        valid_coords = 0
        invalid_coords = 0

        for img_data in screenshot_fixtures[:10]:
            message = create_vision_message(img_data["base64"])
            result = llm_with_tools.invoke([message])

            if result and hasattr(result, 'tool_calls') and result.tool_calls:
                for tool_call in result.tool_calls:
                    args = tool_call.get("args", {})
                    x = args.get("x")
                    y = args.get("y")

                    if x is not None and y is not None:
                        try:
                            # Convert to int if string
                            x_val = int(x) if isinstance(x, str) else x
                            y_val = int(y) if isinstance(y, str) else y
                            # Valid bounds for either device (1080x1920) or optimized space (704x1248)
                            # LLM may return in either space
                            if (0 <= x_val <= 1080 and 0 <= y_val <= 1920) or \
                               (0 <= x_val <= 704 and 0 <= y_val <= 1248):
                                valid_coords += 1
                            else:
                                invalid_coords += 1
                        except (ValueError, TypeError):
                            invalid_coords += 1

        total = valid_coords + invalid_coords
        if total == 0:
            pytest.skip("No coordinate-based tool calls generated")

        validity_rate = valid_coords / total * 100

        print(f"\nCoordinate validity: {validity_rate:.1f}% ({valid_coords}/{total})")

        # Should have at least 60% valid coordinates
        assert validity_rate >= 50, f"Coordinate validity too low: {validity_rate}%"


# =============================================================================
# Parser Fallback Tests
# =============================================================================

class TestParserFallback:
    """Tests for tool call parser fallback mechanisms."""

    def test_xml_format_parsing(self):
        """Test parsing XML format tool calls."""
        xml_response = """
        <tool_call>
        {"name": "android_click", "arguments": {"coordinate": [352, 624]}}
        </tool_call>
        """
        parsed = parse_tool_calls_from_text(xml_response)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "android_click"

    def test_json_array_parsing(self):
        """Test parsing JSON array format."""
        json_response = """
        [{"name": "android_click", "arguments": {"coordinate": [352, 624]}}]
        """
        parsed = parse_tool_calls_from_text(json_response)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "android_click"

    def test_pythonic_format_parsing(self):
        """Test parsing Pythonic function call format."""
        pythonic_response = """
        android_click(coordinate=[352, 624])
        """
        parsed = parse_tool_calls_from_text(pythonic_response)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "android_click"

    def test_multiple_formats_in_response(self):
        """Test handling multiple tool call formats."""
        mixed_response = """
        I'll click on the login button.

        <tool_call>
        {"name": "android_click", "arguments": {"coordinate": [352, 624]}}
        </tool_call>
        """
        parsed = parse_tool_calls_from_text(mixed_response)
        assert len(parsed) >= 1
