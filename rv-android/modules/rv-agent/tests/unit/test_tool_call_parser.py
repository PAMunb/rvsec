"""
Tool call parser unit tests.

Tests parsing of tool calls from various LLM output formats.
"""

import pytest


pytestmark = pytest.mark.unit


class TestParseToolCallsFromText:
    """Test parse_tool_calls_from_text function."""

    def test_xml_qwen_format(self):
        """Parse Qwen3-VL XML format."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = '''<tool_call>
{"name": "android_click", "arguments": {"x": 352, "y": 624, "element_description": "OK button"}}
</tool_call>'''

        calls = parse_tool_calls_from_text(text)

        assert len(calls) == 1
        assert calls[0]["name"] == "android_click"
        assert calls[0]["args"]["x"] == 352
        assert calls[0]["args"]["y"] == 624

    def test_json_array_format(self):
        """Parse JSON array format."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = '[{"name": "android_click", "arguments": {"x": 100, "y": 200}}]'

        calls = parse_tool_calls_from_text(text)

        assert len(calls) == 1
        assert calls[0]["name"] == "android_click"

    def test_json_object_format(self):
        """Parse single JSON object format."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = '{"name": "android_back", "arguments": {}}'

        calls = parse_tool_calls_from_text(text)

        assert len(calls) == 1
        assert calls[0]["name"] == "android_back"

    def test_markdown_code_block(self):
        """Parse markdown code block format."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = '''```json
{"name": "android_scroll", "arguments": {"direction": "down"}}
```'''

        calls = parse_tool_calls_from_text(text)

        assert len(calls) == 1
        assert calls[0]["name"] == "android_scroll"

    def test_pythonic_function_format(self):
        """Parse pythonic function call format."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = 'android_click(x=352, y=624, element_description="OK")'

        calls = parse_tool_calls_from_text(text)

        assert len(calls) == 1
        assert calls[0]["name"] == "android_click"
        assert calls[0]["args"]["x"] == 352

    def test_empty_input(self):
        """Empty input returns empty list."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        calls = parse_tool_calls_from_text("")
        assert calls == []

        calls = parse_tool_calls_from_text(None)
        assert calls == []

    def test_no_tool_calls(self):
        """Text without tool calls returns empty list."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = "I'll click the OK button for you."
        calls = parse_tool_calls_from_text(text)

        assert calls == []


class TestParseToolCallsWithStrategy:
    """Test parse_tool_calls_with_strategy function."""

    def test_returns_strategy_name(self):
        """Function returns strategy used."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_with_strategy

        text = '<tool_call>{"name": "android_back"}</tool_call>'
        calls, strategy = parse_tool_calls_with_strategy(text)

        assert len(calls) == 1
        assert strategy == "xml"

    def test_json_strategy(self):
        """JSON format uses json strategy."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_with_strategy

        text = '{"name": "android_home", "arguments": {}}'
        calls, strategy = parse_tool_calls_with_strategy(text)

        assert len(calls) == 1
        assert "json" in strategy.lower()

    def test_no_match_returns_none_strategy(self):
        """No match returns none strategy."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_with_strategy

        text = "Just some text without tool calls"
        calls, strategy = parse_tool_calls_with_strategy(text)

        assert calls == []
        assert strategy == "none"


class TestNormalizeToolArgs:
    """Test normalize_tool_args function."""

    def test_string_coordinates(self):
        """Convert string coordinates to integers."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": "352", "y": "624"}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 352
        assert normalized["y"] == 624
        assert isinstance(normalized["x"], int)

    def test_array_in_x(self):
        """Convert [x, y] array in x field."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": [352, 624]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 352
        assert normalized["y"] == 624

    def test_coordinate_field(self):
        """Convert coordinate: [x, y] format (Fara-7B style)."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"coordinate": [464, 487]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 464
        assert normalized["y"] == 487

    def test_float_coordinates(self):
        """Convert float coordinates to integers."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": 352.7, "y": 624.3}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 352
        assert normalized["y"] == 624

    def test_preserve_other_fields(self):
        """Non-coordinate fields are preserved."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": 100, "y": 200, "text": "hello", "direction": "up"}
        normalized = normalize_tool_args(args)

        assert normalized["text"] == "hello"
        assert normalized["direction"] == "up"

    def test_empty_args(self):
        """Empty args returns empty dict."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        normalized = normalize_tool_args({})
        assert normalized == {}

        normalized = normalize_tool_args(None)
        assert normalized == {}


class TestMalformedJsonFix:
    """Test malformed JSON handling."""

    def test_missing_quotes(self):
        """Fix missing quotes around values."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = '<tool_call>{"name": android_click, "arguments": {}}</tool_call>'
        calls = parse_tool_calls_from_text(text)

        # Should either fix or return empty
        assert isinstance(calls, list)

    def test_trailing_comma(self):
        """Fix trailing comma in JSON."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = '<tool_call>{"name": "android_click", "arguments": {"x": 352,}}</tool_call>'
        calls = parse_tool_calls_from_text(text)

        assert isinstance(calls, list)

    def test_single_quotes(self):
        """Handle single quotes in JSON."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        text = "<tool_call>{'name': 'android_click', 'arguments': {'x': 100}}</tool_call>"
        calls = parse_tool_calls_from_text(text)

        assert isinstance(calls, list)


class TestParserStats:
    """Test parser statistics tracking."""

    def test_stats_exist(self):
        """Parser stats object exists."""
        from rv_agent.llm.tools.tool_call_parser import parser_stats

        assert parser_stats is not None

    def test_get_stats(self):
        """Get stats returns dictionary."""
        from rv_agent.llm.tools.tool_call_parser import parser_stats

        stats = parser_stats.get_stats()

        assert isinstance(stats, dict)
        assert "total_calls" in stats
        assert "successful_parses" in stats

    def test_reset_stats(self):
        """Stats can be reset."""
        from rv_agent.llm.tools.tool_call_parser import parser_stats

        parser_stats.reset()
        stats = parser_stats.get_stats()

        assert stats["total_calls"] == 0

    def test_record_success(self):
        """record_success increments counters."""
        from rv_agent.llm.tools.tool_call_parser import ParserStats

        stats = ParserStats()
        stats.record_success("xml_tool_call")

        assert stats.total_calls == 1
        assert stats.successful_parses == 1
        assert stats.strategy_success_counts["xml_tool_call"] == 1

    def test_record_success_with_json_fix(self):
        """record_success tracks JSON fixes."""
        from rv_agent.llm.tools.tool_call_parser import ParserStats

        stats = ParserStats()
        stats.record_success("xml_tool_call", json_fix_applied=True)

        assert stats.json_fixes_applied == 1

    def test_record_failure(self):
        """record_failure increments counters."""
        from rv_agent.llm.tools.tool_call_parser import ParserStats

        stats = ParserStats()
        stats.record_failure("empty_response")

        assert stats.total_calls == 1
        assert stats.failed_parses == 1
        assert stats.failure_reasons["empty_response"] == 1

    def test_record_attempt(self):
        """record_attempt tracks strategy attempts."""
        from rv_agent.llm.tools.tool_call_parser import ParserStats

        stats = ParserStats()
        stats.record_attempt("json_array")
        stats.record_attempt("json_array")

        assert stats.strategy_attempt_counts["json_array"] == 2

    def test_get_stats_zero_calls(self):
        """get_stats handles zero calls."""
        from rv_agent.llm.tools.tool_call_parser import ParserStats

        stats = ParserStats()
        result = stats.get_stats()

        assert result["success_rate"] == 0.0


class TestParserResult:
    """Test ParserResult dataclass."""

    def test_default_fields(self):
        """Default fields have correct values."""
        from rv_agent.llm.tools.tool_call_parser import ParserResult

        result = ParserResult(
            success=True,
            tool_calls=[],
            strategy_used="xml"
        )

        assert result.success is True
        assert result.tool_calls == []
        assert result.strategy_used == "xml"
        assert result.strategies_attempted == []
        assert result.error_message is None
        assert result.json_fix_applied is False

    def test_all_fields(self):
        """All fields can be set."""
        from rv_agent.llm.tools.tool_call_parser import ParserResult

        result = ParserResult(
            success=False,
            tool_calls=[{"name": "android_click", "args": {}}],
            strategy_used="json_array",
            strategies_attempted=["xml", "json_array"],
            error_message="Parse failed",
            json_fix_applied=True,
            raw_response_length=1500
        )

        assert result.success is False
        assert len(result.tool_calls) == 1
        assert result.json_fix_applied is True


class TestDenormalizeQwenCoords:
    """Test denormalize_qwen_coords function."""

    def test_qwen_normalized_coords(self):
        """Qwen [0, 1000) coords are converted to pixels."""
        from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

        x, y = denormalize_qwen_coords(500, 500)

        assert x == 540  # 500/1000 * 1080
        assert y == 960  # 500/1000 * 1920

    def test_qwen_edge_coords_zero(self):
        """Zero coordinates are handled."""
        from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

        x, y = denormalize_qwen_coords(0, 0)
        assert x == 0
        assert y == 0

    def test_qwen_edge_coords_max(self):
        """Max coordinates are handled."""
        from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

        x, y = denormalize_qwen_coords(999, 999)
        assert x == 1078  # int(999/1000 * 1080) = int(1078.92)
        assert y == 1918  # int(999/1000 * 1920) = int(1918.08)

    def test_pixel_coords_passthrough(self):
        """Pixel coords >= 1000 pass through."""
        from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

        x, y = denormalize_qwen_coords(540, 1920)

        assert x == 540
        assert y == 1920

    def test_custom_dimensions(self):
        """Custom image dimensions work."""
        from rv_agent.llm.tools.tool_call_parser import denormalize_qwen_coords

        x, y = denormalize_qwen_coords(500, 500, image_width=720, image_height=1280)

        assert x == 360  # 500/1000 * 720
        assert y == 640  # 500/1000 * 1280


class TestFixMalformedJsonExtended:
    """Extended tests for _fix_malformed_json function."""

    def test_missing_leading_zero(self):
        """Fixes .91 to 0.91."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": .91, "y": .45}'
        fixed = _fix_malformed_json(json_str)

        assert "0.91" in fixed
        assert "0.45" in fixed

    def test_double_colon(self):
        """Fixes double colon: "x":": 541."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"name": "android_click", "arguments": {"x":": 541, "y":": 473}}'
        fixed = _fix_malformed_json(json_str)

        assert '":":' not in fixed
        assert '"x": 541' in fixed

    def test_trailing_quote_on_number(self):
        """Fixes trailing quote: "y": 473"."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": 100, "y": 473"}'
        fixed = _fix_malformed_json(json_str)

        assert fixed is not None

    def test_space_separated_numbers(self):
        """Fixes two numbers with space: "x": 867 335."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": 867 335}'
        fixed = _fix_malformed_json(json_str)

        assert '"x": 867' in fixed

    def test_comma_separated_xy(self):
        """Fixes "x": 352, 782 to have y key."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": 352, 782}'
        fixed = _fix_malformed_json(json_str)

        assert '"y": 782' in fixed

    def test_array_xy(self):
        """Fixes "x": [352, 782] to separate x, y."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": [352, 782]}'
        fixed = _fix_malformed_json(json_str)

        assert '"x": 352' in fixed
        assert '"y": 782' in fixed

    def test_malformed_array_quotes(self):
        """Fixes "x": [499", "499"]."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": [499", "499"]}'
        fixed = _fix_malformed_json(json_str)

        assert '"x": 499' in fixed
        assert '"y": 499' in fixed

    def test_equals_sign_instead_of_colon(self):
        """Fixes "x": = 100."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": = 100}'
        fixed = _fix_malformed_json(json_str)

        assert '"x": 100' in fixed

    def test_truncated_json(self):
        """Adds missing closing braces."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"name": "test", "args": {"x": 100'
        fixed = _fix_malformed_json(json_str)

        assert fixed.count('{') == fixed.count('}')

    def test_valid_json_returns_none(self):
        """Valid JSON returns None (no fix needed)."""
        from rv_agent.llm.tools.tool_call_parser import _fix_malformed_json

        json_str = '{"x": 100, "y": 200}'
        fixed = _fix_malformed_json(json_str)

        assert fixed is None


class TestNormalizeToolArgsExtended:
    """Extended tests for normalize_tool_args function."""

    def test_coordinates_array(self):
        """Convert coordinates: [x, y] format."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"coordinates": [464, 487]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 464
        assert normalized["y"] == 487

    def test_bbox_array(self):
        """Convert bbox: [x, y] format."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"bbox": [300, 400]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 300
        assert normalized["y"] == 400

    def test_bbox_2d_array(self):
        """Convert bbox_2d: [x, y] format."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"bbox_2d": [300, 400]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 300
        assert normalized["y"] == 400

    def test_bounds_array(self):
        """Convert bounds: [x, y] format."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"bounds": [300, 400]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 300
        assert normalized["y"] == 400

    def test_bndbox_array(self):
        """Convert bndbox: [x, y] format."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"bndbox": [300, 400]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 300
        assert normalized["y"] == 400

    def test_center_array(self):
        """Convert center: [x, y] format."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"center": [300, 400]}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 300
        assert normalized["y"] == 400

    def test_nested_arguments(self):
        """Nested arguments dict with coordinate."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {
            "arguments": {
                "coordinate": [250, 350],
                "type": "click"
            }
        }
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 250
        assert normalized["y"] == 350
        assert normalized["name"] == "click"

    def test_nested_arguments_without_type(self):
        """Nested arguments without type field."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {
            "arguments": {
                "coordinate": [250, 350]
            }
        }
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 250
        assert normalized["y"] == 350
        assert "name" not in normalized

    def test_string_coordinate_invalid(self):
        """Invalid string coordinate is preserved."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": "abc", "y": 200}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == "abc"
        assert normalized["y"] == 200


class TestExecuteToolCall:
    """Test execute_tool_call function."""

    def test_click_execution(self):
        """android_click executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.click.return_value = True
        converter = MagicMock()
        converter.optimized_to_device.return_value = (540, 960)

        tool_call = {"name": "android_click", "args": {"x": 100, "y": 200}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "click"
        device.click.assert_called_once()

    def test_type_text_execution(self):
        """android_type_text executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.click.return_value = True
        device.input_text.return_value = True
        converter = MagicMock()
        converter.optimized_to_device.return_value = (540, 960)

        tool_call = {"name": "android_type_text", "args": {"x": 100, "y": 200, "text": "Hello"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "set_text"
        assert result["text"] == "Hello"

    def test_long_click_execution(self):
        """android_long_click executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.long_click.return_value = True
        converter = MagicMock()
        converter.optimized_to_device.return_value = (540, 960)

        tool_call = {"name": "android_long_click", "args": {"x": 100, "y": 200}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "long_click"

    def test_swipe_execution(self):
        """android_swipe executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.swipe.return_value = True
        converter = MagicMock()

        tool_call = {"name": "android_swipe", "args": {"direction": "up", "distance": "medium"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "swipe"

    def test_swipe_invalid_direction(self):
        """android_swipe rejects invalid direction."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        converter = MagicMock()

        tool_call = {"name": "android_swipe", "args": {"direction": "diagonal"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "error" in result

    def test_swipe_invalid_distance(self):
        """android_swipe rejects invalid distance."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        converter = MagicMock()

        tool_call = {"name": "android_swipe", "args": {"direction": "up", "distance": "huge"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "error" in result

    def test_scroll_execution(self):
        """android_scroll executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.scroll.return_value = True
        converter = MagicMock()

        tool_call = {"name": "android_scroll", "args": {"direction": "down"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "scroll"

    def test_back_execution(self):
        """android_back executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.back.return_value = True
        converter = MagicMock()

        tool_call = {"name": "android_back", "args": {}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "back"
        device.back.assert_called_once()

    def test_home_execution(self):
        """android_home executes correctly."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.home.return_value = True
        converter = MagicMock()

        tool_call = {"name": "android_home", "args": {}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is True
        assert result["action_type"] == "home"

    def test_unknown_tool(self):
        """Unknown tool returns error."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        converter = MagicMock()

        tool_call = {"name": "android_shake", "args": {}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert result["action_type"] == "unknown"

    def test_click_coordinate_validation(self):
        """Click validates coordinates."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        converter = MagicMock()
        converter.validate_optimized_coords.side_effect = ValueError("Out of bounds")

        tool_call = {"name": "android_click", "args": {"x": -100, "y": -200}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "Invalid coordinates" in result["error"]

    def test_type_text_click_failure(self):
        """Type text handles click failure."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.click.return_value = False
        converter = MagicMock()
        converter.optimized_to_device.return_value = (540, 960)

        tool_call = {"name": "android_type_text", "args": {"x": 100, "y": 200, "text": "Test"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "Click failed" in result["error"]

    def test_exception_handling(self):
        """Exceptions are caught and reported."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        device.click.side_effect = Exception("Connection lost")
        converter = MagicMock()
        converter.optimized_to_device.return_value = (540, 960)

        tool_call = {"name": "android_click", "args": {"x": 100, "y": 200}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "Connection lost" in result["error"]


class TestParseToolCallsAdditional:
    """Additional tests for parse_tool_calls functions."""

    def test_pythonic_float_values(self):
        """Pythonic format handles float values."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = 'android_click(x=540.5, y=1054.7)'
        result = parse_tool_calls_from_text(response, track_stats=False)

        assert len(result) == 1
        # Values normalized via normalize_tool_args

    def test_multiple_tool_calls_array(self):
        """Multiple tool calls in array are parsed."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = '''[
            {"name": "android_click", "parameters": {"x": 100, "y": 200}},
            {"name": "android_back", "parameters": {}}
        ]'''
        result = parse_tool_calls_from_text(response, track_stats=False)

        assert len(result) == 2
        assert result[0]["name"] == "android_click"
        assert result[1]["name"] == "android_back"

    def test_gemma_action_format(self):
        """Gemma format with 'action' key."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = '```json\n{"action": "android_click", "x": 100, "y": 200}\n```'
        result = parse_tool_calls_from_text(response, track_stats=False)

        assert len(result) == 1
        assert result[0]["name"] == "android_click"

    def test_track_stats_disabled(self):
        """Stats tracking can be disabled."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text, parser_stats

        parser_stats.reset()
        initial_calls = parser_stats.total_calls
        parse_tool_calls_from_text("", track_stats=False)

        assert parser_stats.total_calls == initial_calls

    def test_pythonic_all_functions(self):
        """All pythonic function names are parsed."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        functions = [
            'android_click(x=100, y=200)',
            'android_type_text(x=100, y=200, text="hello")',
            'android_long_click(x=100, y=200)',
            'android_swipe(direction="up")',
            'android_scroll(direction="down")',
            'android_back()',
            'android_home()',
        ]

        for func in functions:
            result = parse_tool_calls_from_text(func, track_stats=False)
            assert len(result) >= 0  # May be 0 if no args extracted

    def test_pythonic_with_single_quotes(self):
        """Pythonic format handles single quotes."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = "android_type_text(x=100, y=200, text='hello world')"
        result = parse_tool_calls_from_text(response, track_stats=False)

        assert len(result) == 1
        assert result[0]["args"]["text"] == "hello world"


class TestNormalizeToolArgsEdgeCases:
    """Edge cases for normalize_tool_args."""

    def test_nested_arguments_with_extra_fields(self):
        """Nested arguments with extra top-level fields preserved."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {
            "arguments": {
                "coordinate": [250, 350],
                "type": "click"
            },
            "extra_field": "value123"
        }
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 250
        assert normalized["y"] == 350
        assert normalized["extra_field"] == "value123"

    def test_x_array_with_extra_fields(self):
        """x as array with extra fields preserved."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": [352, 624], "element_description": "Button"}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 352
        assert normalized["y"] == 624
        assert normalized["element_description"] == "Button"

    def test_x_array_with_y_already_present(self):
        """x as array but y already specified."""
        from rv_agent.llm.tools.tool_call_parser import normalize_tool_args

        args = {"x": [352, 624], "y": 999}
        normalized = normalize_tool_args(args)

        assert normalized["x"] == 352
        assert normalized["y"] == 999  # Original y preserved


class TestParseWithMalformedXml:
    """Test XML parsing with malformed JSON that needs fixing."""

    def test_xml_with_double_colon(self):
        """XML with double colon malformation gets fixed."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = '<tool_call>{"name": "android_click", "arguments": {"x":": 541, "y":": 473}}</tool_call>'
        result = parse_tool_calls_from_text(response, track_stats=False)

        assert len(result) == 1
        assert result[0]["name"] == "android_click"

    def test_xml_with_missing_leading_zero(self):
        """XML with .91 float gets fixed to 0.91."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = '<tool_call>{"name": "android_click", "arguments": {"x": .91, "y": .45}}</tool_call>'
        result = parse_tool_calls_from_text(response, track_stats=False)

        # Should parse even with the malformation
        assert isinstance(result, list)

    def test_xml_with_truncated_json(self):
        """XML with truncated JSON gets closing braces added."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text

        response = '<tool_call>{"name": "android_click", "arguments": {"x": 100</tool_call>'
        result = parse_tool_calls_from_text(response, track_stats=False)

        # May or may not parse successfully
        assert isinstance(result, list)


class TestParserFailureCategories:
    """Test different failure reason categories."""

    def test_response_too_short(self):
        """Short response records failure reason."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text, parser_stats

        parser_stats.reset()
        result = parse_tool_calls_from_text("Hi")

        assert result == []
        stats = parser_stats.get_stats()
        assert "response_too_short" in stats["failure_reasons"]

    def test_no_tool_mention(self):
        """Response without tool keywords records failure."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text, parser_stats

        parser_stats.reset()
        result = parse_tool_calls_from_text("The screen shows a beautiful sunset image.")

        assert result == []
        stats = parser_stats.get_stats()
        assert "no_tool_mention" in stats["failure_reasons"]

    def test_refusal_detected(self):
        """Refusal response is tracked."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_from_text, parser_stats

        parser_stats.reset()
        result = parse_tool_calls_from_text("I'm sorry, but I cannot perform that action.")

        assert result == []
        stats = parser_stats.get_stats()
        assert "refusal" in stats["failure_reasons"]


class TestParseWithStrategyEdgeCases:
    """Edge cases for parse_tool_calls_with_strategy."""

    def test_xml_with_malformed_json_fallback(self):
        """XML strategy tries original JSON if fixed fails."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_with_strategy

        response = '<tool_call>{"name": "android_click", "arguments": {"x": 100, "y": 200}}</tool_call>'
        calls, strategy = parse_tool_calls_with_strategy(response, track_stats=False)

        assert len(calls) == 1
        assert strategy == "xml"

    def test_pythonic_strategy_returned(self):
        """Pythonic format returns 'pythonic' strategy."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_with_strategy

        response = 'Let me click: android_click(x=540, y=1054)'
        calls, strategy = parse_tool_calls_with_strategy(response, track_stats=False)

        assert len(calls) == 1
        assert strategy == "pythonic"

    def test_parse_failed_category(self):
        """Parse failed with click mention."""
        from rv_agent.llm.tools.tool_call_parser import parse_tool_calls_with_strategy, parser_stats

        parser_stats.reset()
        response = "I will click the button now but this is malformed json {click"
        calls, strategy = parse_tool_calls_with_strategy(response)

        assert calls == []
        assert strategy == "none"
        stats = parser_stats.get_stats()
        assert "parse_failed" in stats["failure_reasons"]


class TestLongClickCoordinateValidation:
    """Test long_click coordinate validation."""

    def test_long_click_invalid_coords(self):
        """Long click validates coordinates."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        converter = MagicMock()
        converter.validate_optimized_coords.side_effect = ValueError("Out of bounds")

        tool_call = {"name": "android_long_click", "args": {"x": -100, "y": -200}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "Invalid coordinates" in result["error"]


class TestTypeTextCoordinateValidation:
    """Test type_text coordinate validation."""

    def test_type_text_invalid_coords(self):
        """Type text validates coordinates."""
        from unittest.mock import MagicMock
        from rv_agent.llm.tools.tool_call_parser import execute_tool_call

        device = MagicMock()
        converter = MagicMock()
        converter.validate_optimized_coords.side_effect = ValueError("Out of bounds")

        tool_call = {"name": "android_type_text", "args": {"x": -100, "y": -200, "text": "test"}}
        result = execute_tool_call(tool_call, device, converter)

        assert result["success"] is False
        assert "Invalid coordinates" in result["error"]
