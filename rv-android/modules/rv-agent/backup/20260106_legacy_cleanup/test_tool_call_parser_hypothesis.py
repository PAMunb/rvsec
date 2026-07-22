"""
Property-based tests for the tool_call_parser using Hypothesis.
"""
import pytest
import json
from hypothesis import given, strategies as st
from rv_agent.llm.tools import tool_call_parser

# --- Strategies for generating tool call components ---

tool_names = st.sampled_from([
    "android_click", "android_type_text", "android_long_click", 
    "android_swipe", "android_scroll", "android_back", "android_home"
])

# A strategy for arguments, can be extended
# Use a more constrained character set for text to avoid breaking JSON
safe_text = st.text(alphabet=st.characters(blacklist_characters='{}'), max_size=50)

arguments_strategy = st.fixed_dictionaries({
    "x": st.integers(min_value=0, max_value=1080),
    "y": st.integers(min_value=0, max_value=1920),
    "text": safe_text,
    "direction": st.sampled_from(["up", "down", "left", "right"])
})

# A strategy for a single, valid tool call dictionary
tool_call_strategy = st.fixed_dictionaries({
    "name": tool_names,
    "arguments": arguments_strategy
})


@pytest.mark.hypothesis
class TestToolCallParserHypothesis:
    """Property-based tests for the tool call parser."""

    @given(tool_call=tool_call_strategy)
    def test_parsing_of_generated_xml_format(self, tool_call):
        """Tests that the parser can handle generated tool calls in XML format."""
        # Create a string in the <tool_call> format
        json_str = json.dumps(tool_call)
        xml_str = f"<tool_call>{json_str}</tool_call>"

        parsed_calls = tool_call_parser.parse_tool_calls_from_text(xml_str)

        assert len(parsed_calls) == 1
        parsed_call = parsed_calls[0]
        
        assert parsed_call["name"] == tool_call["name"]
        # We only check for a subset of keys because normalize_tool_args might add/remove some
        assert "x" in parsed_call["args"]
        assert "y" in parsed_call["args"]

    @given(tool_call=tool_call_strategy)
    def test_parsing_of_generated_json_object_format(self, tool_call):
        """Tests that the parser can handle generated tool calls in single JSON object format."""
        json_str = json.dumps(tool_call)

        parsed_calls = tool_call_parser.parse_tool_calls_from_text(json_str)

        assert len(parsed_calls) >= 1 # Can be more if the generated text contains {}
        # This test is tricky because a generated text might contain parts that look like JSON
        # A more robust test would be to check if the *first* parsed call matches
        if parsed_calls:
            assert parsed_calls[0]["name"] == tool_call["name"]

    @given(tool_calls=st.lists(tool_call_strategy, min_size=1, max_size=5))
    def test_parsing_of_generated_json_array_format(self, tool_calls):
        """Tests that the parser can handle generated tool calls in JSON array format."""
        json_str = json.dumps(tool_calls)

        parsed_calls = tool_call_parser.parse_tool_calls_from_text(json_str)

        assert len(parsed_calls) == len(tool_calls)
        for original, parsed in zip(tool_calls, parsed_calls):
            assert original["name"] == parsed["name"]

    @given(args=arguments_strategy)
    def test_normalize_tool_args_handles_various_formats(self, args):
        """Tests that normalize_tool_args correctly processes different generated formats."""
        # Test string conversion
        string_args = {k: str(v) for k, v in args.items()}
        normalized = tool_call_parser.normalize_tool_args(string_args)
        if "x" in normalized:
            assert isinstance(normalized["x"], int)

        # Test 'coordinates' key
        coord_args = {"coordinates": [args["x"], args["y"]], "text": args["text"]}
        normalized = tool_call_parser.normalize_tool_args(coord_args)
        assert normalized["x"] == args["x"]
        assert normalized["y"] == args["y"]
        assert normalized["text"] == args["text"]

        # Test 'bbox' key
        bbox_args = {"bbox": [args["x"], args["y"]]}
        normalized = tool_call_parser.normalize_tool_args(bbox_args)
        assert normalized["x"] == args["x"]
        assert normalized["y"] == args["y"]
        
    @given(x=st.integers(min_value=0, max_value=999), y=st.integers(min_value=0, max_value=999))
    def test_denormalize_qwen_coords_bounds(self, x, y):
        """Tests that denormalized coordinates are within image bounds."""
        width, height = 1080, 1920
        px, py = tool_call_parser.denormalize_qwen_coords(x, y, width, height)
        assert 0 <= px < width
        assert 0 <= py < height

    @given(x=st.integers(min_value=1000), y=st.integers(min_value=1000))
    def test_denormalize_qwen_coords_passthrough(self, x, y):
        """Tests that pixel coordinates are passed through."""
        px, py = tool_call_parser.denormalize_qwen_coords(x, y)
        assert px == x
        assert py == y
